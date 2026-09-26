using System.Text.Json;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28FuelCalculationTests
{
    [Fact]
    public void ForgedIntermediateAccumulatorFlagsOrExitCannotHideBehindEqualOutput()
    {
        int[][] events = [[42, 43, 123, 456, 0x0DC9, 0x1DC9, 65536, 65536],
            [43, 44, 456, 789, 0x1DC9, 0x5DC9, 65536, 65536]];
        P28FuelCalculationValidator.ValidateEventContinuity(events, 123, 0x0DC9, 789, 0x5DC9);
        foreach (var field in new[] { 2, 4 })
        {
            var forged = events.Select(e => e.ToArray()).ToArray(); forged[1][field] ^= 1;
            Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateEventContinuity(forged, 123, 0x0DC9, 789, 0x5DC9));
        }
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateEventContinuity(events, 123, 0x0DC9, 789, 0x1DC9));
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateEventContinuity(events, 123, 0x0DC9, 788, 0x5DC9));
    }
    internal static P28FuelCalculationScenario Scenario() => P28FuelCalculationScenario.Create(new(0, 0, 0, 0, 0, 0, 0xA5, 0),
        [new(0, 0, 0, 0, 513), new(1, 255, 255, 255, 65535)], "Invented raw software snapshot", [0]);
    [Fact]
    public void ScenarioIsClosedAndCannotInjectSelectorSourceOrExpectedResult()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28FuelCalculationScenario.Parse(s.ToJson()).Digest);
        foreach (var change in new Action<JsonNode>[] {
            n => n["calls"]![0]!["mapId"] = "map_1", n => n["calls"]![0]!["selector0127"] = 2,
            n => n["calls"]![0]!["data0140"] = 99, n => n["calls"]![0]!["loadFraction"] = 65535,
            n => n["calls"]![0]!["expectedProduct"] = 18, n => n["calls"]![0]!["pc"] = 0x21E0,
            n => n["calls"]![0]!["ram"] = new JsonObject(), n => n["initialState"]!["consumerOutput0140"] = 19,
            n => n["traceCallIndexes"] = new JsonArray(0, 0), n => n["formatVersion"] = 2,
            n => n["calls"]![0]!["index"] = 1, n => n["calls"]![0]!["factor0158"] = 65536 })
        {
            var node = JsonNode.Parse(s.ToJson())!; change(node);
            Assert.ThrowsAny<Exception>(() => P28FuelCalculationScenario.Parse(node.ToJsonString()));
        }
        Assert.Throws<ArgumentException>(() => P28FuelCalculationScenario.Create(s.InitialState,
            Enumerable.Range(0, 65).Select(i => new P28FuelCalculationCall(i, 0, 0, 0, 0)).ToArray(), "too many"));
        var request = JsonSerializer.SerializeToElement(P28FuelCalculationValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Empty(request.GetProperty("allowAssumptions").EnumerateArray());
        Assert.False(request.GetProperty("fuelCalculationChain").GetProperty("calls")[0].TryGetProperty("mapId", out _));
    }
    [Theory]
    [InlineData(0, 65535, 0, false)]
    [InlineData(511, 1, 0, false)]
    [InlineData(512, 1, 1, false)]
    [InlineData(65535, 512, 65535, false)]
    [InlineData(32768, 1023, 65472, false)]
    [InlineData(32768, 1024, 65535, true)]
    [InlineData(65535, 65535, 65535, true)]
    public void ExactIntegerNarrowingAndEquality(int source, int factor, int expected, bool saturated)
    {
        var p = P28FuelCalculationModel.Project((ushort)source, (ushort)factor);
        Assert.Equal(expected, p.Output); Assert.Equal(saturated, p.Saturated);
    }
    [Fact]
    public void FiniteWidthAuditIsSeparateFromNativeExecution()
    {
        var cases = 0;
        for (var source = 0; source <= 65025; source++) foreach (var factor in new ushort[] { 0, 1, 511, 512, 513, 1023, 1024, 32768, 65535 })
            {
                var p = P28FuelCalculationModel.Project((ushort)source, factor);
                var expected = Math.Min((ulong)source * factor / 512, ushort.MaxValue);
                Assert.Equal((int)expected, p.Output); Assert.Equal((ulong)p.HighWord * 65536 + (uint)p.LowWord, p.Product); cases++;
            }
        Assert.Equal(585234, cases); // width-bound model audit, NOT native executions
    }
    [Fact]
    public void NativeWordGenerationRejectsSubstitutionByteReadAndInterveningHostStore()
    {
        int[][] valid = [[0x134E, 0x140, 16, 1, 0x1234], [0x21DB, 0x140, 16, 0, 0x1234]];
        Assert.True(P28FuelCalculationValidator.HandoffMatches(valid, 0x1234, true));
        Assert.False(P28FuelCalculationValidator.HandoffMatches([[0x21DB, 0x140, 16, 0, 0x1234]], 0x1234, true));
        Assert.False(P28FuelCalculationValidator.HandoffMatches([valid[0], [0x21DB, 0x140, 8, 0, 0x34]], 0x1234, true));
        Assert.False(P28FuelCalculationValidator.HandoffMatches([valid[0], [0, 0x141, 8, 1, 0x12], valid[1]], 0x1234, true));
        Assert.False(P28FuelCalculationValidator.HandoffMatches([valid[1], valid[0]], 0x1234, true));
    }
    [Fact]
    public void EqualFinalProductDoesNotHideSwappedOperandsStaleResultOrWrongBank()
    {
        var e = P28FuelCalculationModel.Project(600, 513);
        var events = new[] { Row(0x21DB, 0x21DD, 0, 600), Row(0x21DD, 0x21E0, 600, 600), Row(0x21E0, 0x21E2, 600, 45656),
            Row(0x21E2, 0x21E4, 45656, 45656), Row(0x21E4, 0x21E5, 45656, 22828),
            new[] { 0x21E5, 0x21E6, 22828, 22786, 0x1DC9, 0x0DC9, 65536, 65536 }, Row(0x21E6, 0x21E8, 22786, 22786), Row(0x21E8, 0x21E9, 22786, 601),
            new[] { 0x21E9, 0x21EC, 601, 601, 0x1DC9, 0x5DC9, 0, 0 }, Row(0x21EC, 0x21F1, 601, 601), Row(0x21F1, 0x21F2, 601, 601) };
        var writes = new[] { new[] { 0x100, 16, 513 }, new[] { 0x102, 16, 4 }, new[] { 0x102, 16, 2 }, new[] { 0x104, 16, 601 } };
        int[][] accesses = [[0x21DD, 0x158, 16, 0, 513]];
        var stage = JsonSerializer.SerializeToElement(new { events, writes });
        var exit = JsonSerializer.SerializeToElement(new { registers = new[] { 1, 2, 2, 0, 89, 2, 165, 165 } });
        P28FuelCalculationValidator.ValidateNumbers(stage, accesses, exit, e, 601);
        var swapped = JsonNode.Parse(stage.GetRawText())!; swapped["events"]![0]![3] = 513;
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateNumbers(JsonSerializer.SerializeToElement(swapped), accesses, exit, e, 601));
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateNumbers(stage, [[0x21DD, 0x158, 16, 0, 600]], exit, e, 601));
        var bank = JsonNode.Parse(stage.GetRawText())!; bank["writes"]![3]![0] = 0x204;
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateNumbers(JsonSerializer.SerializeToElement(bank), accesses, exit, e, 601));
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateNumbers(stage, accesses, exit, e, 600));
        var wrongFlags = JsonNode.Parse(stage.GetRawText())!; wrongFlags["events"]![4]![5] = 0x9DC9;
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateNumbers(JsonSerializer.SerializeToElement(wrongFlags), accesses, exit, e, 601));
    }
    private static int[] Row(int pc, int next, int before, int after) => [pc, next, before, after, 0x1DC9, 0x1DC9, 65536, 65536];
    [Fact]
    public void ScriptedHandoffCannotResetNativeRegistersEvenForEqualOutput()
    {
        var b = JsonSerializer.SerializeToNode(new
        {
            pc = 0x1350,
            accumulator = 123,
            lrb = 0x20,
            psw = 0x5DC9,
            usp = 0x280,
            ssp = 0x7FE,
            x1 = 42,
            x2 = 0,
            dp = 357,
            registers = new[] { 1, 2, 3, 4, 5, 6, 7, 8 }
        })!;
        var entry = b.DeepClone(); entry["pc"] = 0x21DB; entry["psw"] = 0x0DC9;
        var row = new JsonObject
        {
            ["handoff1350"] = b.DeepClone(),
            ["downstreamEntry"] = entry.DeepClone(),
            ["tailBoundaries"] = new JsonArray(b.DeepClone(), b.DeepClone(), b.DeepClone(), b.DeepClone(), b.DeepClone()),
            ["hostTransitionWrites"] = JsonNode.Parse(P28FuelCalculationValidator.ExpectedContracts()[0].GetProperty("hostTransitionWrites").GetRawText())
        };
        P28FuelCalculationValidator.ValidateSeams(JsonSerializer.SerializeToElement(row));
        row["downstreamEntry"]!["x1"] = 0;
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.ValidateSeams(JsonSerializer.SerializeToElement(row)));
    }
    [Theory]
    [InlineData("0.18.0", "fuelCalculationChain")]
    [InlineData("0.17.0", "fuelCalculationChain")]
    [InlineData("0.19.0", "fuelMapLookup")]
    public void CapabilityRejectsWrongTaskVersionAndForgedResponse(string version, string operation)
    {
        var root = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation,
            runnerVersion = version,
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = Array.Empty<string>(),
            entryContracts = P28FuelCalculationValidator.ExpectedContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            fuelCalculationSequences = Array.Empty<int>()
        });
        Assert.Throws<SliceProcessException>(() => P28FuelCalculationValidator.Analyze(RomImage.FromBytes(new byte[32768]), Scenario(), root, "A"));
    }
    [Fact]
    public async Task RealRustNumericStoreReaderSubprocessIsRequired()
    {
        // Newly composed native producer/load/product/store program; no OEM fixture.
        var bytes = new byte[] { 0x67, 0x34, 0x12, 0xD5, 0xD0, 0x67, 0x78, 0x56, 0xD5, 0xD2,
            0xE5, 0xD0, 0xB5, 0xD2, 0x48, 0x90, 0x35, 0xD5, 0xD4, 0x35, 0xD5, 0xD6 };
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "synthetic", rom = bytes.Select(v => (int)v).ToArray() } },
            scratchPatterns = new[] { 170 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { 22 },
                allowedCodeRanges = new[] { new[] { 0, 22 } },
                psw = 0x0101,
                lrb = 0x40,
                usp = 0x180,
                instructionBudget = 16,
                dataSeeds = Array.Empty<int[]>(),
                outputAddresses = new[] { 0xD0, 0xD1, 0xD4, 0xD5, 0xD6, 0xD7 }
            }
        });
        Assert.Equal(SliceRunnerIdentity.CurrentVersion, response.Response.GetProperty("runnerVersion").GetString());
        var r = response.Response.GetProperty("syntheticResult"); Assert.Equal(0, r.GetProperty("status").GetInt32());
        Assert.Equal(new[] { 0x34, 0x12, 0x60, 0, 0x26, 6 }, r.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
    }
}
