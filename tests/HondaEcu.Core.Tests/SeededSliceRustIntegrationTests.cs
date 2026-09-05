using System.Text.Json;

namespace HondaEcu.Core.Tests;

/// <summary>These tests always launch the actual Rust executable and only invented tiny programs.</summary>
public sealed class SeededSliceRustIntegrationTests
{
    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualExecutedImmediateAndOpcodeChangesAlterTheResultOrStatus()
    {
        // Newly authored: LB A,#42; STB A,DATA00C4. No firmware fixture is used.
        var first = await RunAsync([0x77, 42, 0xD5, 0xC4], 4, []);
        var changedImmediate = await RunAsync([0x77, 43, 0xD5, 0xC4], 4, []);
        var changedOpcode = await RunAsync([0x77, 42, 0x00, 0xC4], 4, []);
        Assert.Equal(0, first.GetProperty("status").GetInt32());
        Assert.Equal(42, first.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(43, changedImmediate.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(2, changedOpcode.GetProperty("status").GetInt32());
        Assert.Equal(2, changedOpcode.GetProperty("stopPc").GetInt32());
        Assert.Equal(4, first.GetProperty("stopPc").GetInt32());
        Assert.Equal(2, first.GetProperty("steps").GetInt32());
        Assert.Equal(2, first.GetProperty("trace").GetArrayLength());
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualLcReadsProgramConstantNotSeededRamAndChangedRomConstantChangesOutput()
    {
        var program = new int[0x102];
        // Newly authored: MOV DP,#0x100; LC A,[DP]; STB A,DATA00C4.
        new[] { 0x62, 0x00, 0x01, 0x92, 0xA8, 0xD5, 0xC4 }.CopyTo(program, 0);
        program[0x100] = 42;
        var first = await RunAsync(program, 7, [[0x100, 99], [0x101, 88], [0xC4, 77]]);
        program[0x100] = 43;
        var changed = await RunAsync(program, 7, [[0x100, 99], [0x101, 88], [0xC4, 77]]);
        Assert.Equal(0, first.GetProperty("status").GetInt32());
        Assert.Equal(42, first.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(43, changed.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(new[] { 256, 257 }, first.GetProperty("programReads").EnumerateArray().Select(item => item.GetInt32()));
        Assert.Equal(7, first.GetProperty("stopPc").GetInt32());
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualWordAddStopsBeforeExecutionUnlessExplicitlyPermittedAndDoesNotPermitOtherOperations()
    {
        int[][] seeds = [[0x206, 1], [0x207, 0], [6, 2], [7, 0]];
        var strict = await RunAsync([0x47, 0x81], 2, seeds, psw: 0x1101, outputs: [0x206, 0x207]);
        var conditional = await RunAsync([0x47, 0x81], 2, seeds, true, 0x1101, [0x206, 0x207]);
        var unknown = await RunAsync([0x47, 0x81, 0x00], 3, seeds, true, 0x1101, [0x206, 0x207]);
        Assert.Equal(1, strict.GetProperty("status").GetInt32());
        Assert.Equal(0, strict.GetProperty("steps").GetInt32());
        Assert.Equal(0, strict.GetProperty("stopPc").GetInt32());
        Assert.Empty(strict.GetProperty("usedAssumptions").EnumerateArray());
        Assert.Equal(1, strict.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(0, conditional.GetProperty("status").GetInt32());
        Assert.Equal(3, conditional.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(P28ByteExecutionValidator.AddAssumption, conditional.GetProperty("usedAssumptions")[0].GetString());
        Assert.Equal(2, unknown.GetProperty("status").GetInt32());
        Assert.Equal(2, unknown.GetProperty("stopPc").GetInt32());
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualRorUsesIncomingCarryAndWritesTheBankAliasesWithoutChangingOtherFlags()
    {
        // er3 is r6/r7 in the full LRB-selected bank, not a disconnected CPU shadow.
        var result = await RunAsync([0x47, 0xC7], 2, [[0x206, 0], [0x207, 0]],
            psw: 0xF331, outputs: [0x206, 0x207, 4, 5]);
        Assert.Equal(0, result.GetProperty("status").GetInt32());
        var output = result.GetProperty("outputs").EnumerateArray().Select(item => item.GetInt32()).ToArray();
        Assert.Equal(new[] { 0, 128 }, output[..2]);
        // Reserved PSW bits have fixed read values; compare the documented mutable flags and SCB.
        Assert.Equal(0x7331, (output[2] | output[3] << 8) & 0xF337);
    }

    private static async Task<JsonElement> RunAsync(
        int[] program, int exit, int[][] seeds, bool allow = false, int psw = 0x0101, int[]? outputs = null)
    {
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "newly-authored-public-test", rom = program } },
            allowAssumptions = allow ? new[] { P28ByteExecutionValidator.AddAssumption } : [],
            scratchPatterns = new[] { 85 },
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { exit },
                allowedCodeRanges = new[] { new[] { 0, exit } },
                psw,
                lrb = 0x40,
                usp = 0x180,
                instructionBudget = 8,
                dataSeeds = seeds,
                outputAddresses = outputs ?? [0xC4],
            },
        });
        Assert.Equal("synthetic", response.Response.GetProperty("operation").GetString());
        Assert.Equal(P28ByteExecutionValidator.UpstreamCommit, response.Response.GetProperty("upstreamCommit").GetString());
        return response.Response.GetProperty("syntheticResult").Clone();
    }
}
