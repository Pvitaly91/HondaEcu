using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class P28ProducerRustIntegrationTests
{
    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualProducerToCompactTransfersMeasuredRamAndDoesNotReseedOldT()
    {
        var firstInput = P28ProducerModelTests.Input([42, 2, 3, 4, 5, 6]);
        var secondInput = firstInput with { CaseId = 1, ScratchPattern = 170, Samples = new ushort[] { 7, 2, 3, 4, 5, 6 }, PreviousT = 456 };
        var response = await RunAsync(Program(false, false), [firstInput, secondInput], []);
        var rows = response.GetProperty("producerRows");
        Assert.Equal(0, rows[0][2].GetInt32());
        Assert.Equal(42, rows[0][5].GetInt32());
        Assert.Equal(123, rows[0][21].GetInt32());
        Assert.Equal(42, rows[0][18].GetInt32());
        Assert.Equal(7, rows[1][5].GetInt32());
        Assert.Equal(7, rows[1][18].GetInt32());
        Assert.Equal(456, rows[1][21].GetInt32());
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualProducerAndCompactAssumptionsAreSeparateAndCumulativeThroughThreshold()
    {
        var input = P28ProducerModelTests.Input([42, 2, 3, 4, 5, 6]);
        var program = Program(true, true);
        var unrelated = await RunAsync(program, [input], [P28ByteExecutionValidator.AddAssumption]);
        Assert.Equal(1, unrelated.GetProperty("producerRows")[0][2].GetInt32());
        Assert.Equal(4, unrelated.GetProperty("producerRows")[0][15].GetInt32());
        var onlyG = await RunAsync(program, [input], [P28ProducerModel.AddEr1Assumption]);
        Assert.Equal(0, onlyG.GetProperty("producerRows")[0][2].GetInt32());
        Assert.Equal(1, onlyG.GetProperty("producerRows")[0][14].GetInt32());
        Assert.Equal(1, onlyG.GetProperty("producerRows")[0][15].GetInt32());
        Assert.Equal(4, onlyG.GetProperty("producerThresholdRows")[0][2].GetInt32());
        var both = await RunAsync(program, [input], [P28ProducerModel.AddEr1Assumption, P28ByteExecutionValidator.AddAssumption]);
        Assert.Equal(0, both.GetProperty("producerRows")[0][15].GetInt32());
        Assert.Equal(3, both.GetProperty("producerRows")[0][20].GetInt32());
        Assert.Equal(3, both.GetProperty("producerThresholdRows")[0][8].GetInt32());
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task SameMnemonicDifferentProducerFormIsUnresolvedBeforeExecution()
    {
        var program = Program(false, false);
        program[0x0772] = 0x47;
        program[0x0773] = 0x15; // CLR er3 is not admitted by the audited CLR A form.
        var response = await RunAsync(program, [P28ProducerModelTests.Input([42, 2, 3, 4, 5, 6])],
            [P28ProducerModel.AddEr1Assumption, P28ByteExecutionValidator.AddAssumption]);
        Assert.Equal(1, response.GetProperty("producerRows")[0][2].GetInt32());
        Assert.Equal(0, response.GetProperty("producerRows")[0][4].GetInt32());
        Assert.Equal(4, response.GetProperty("producerRows")[0][15].GetInt32());
    }

    private static async Task<JsonElement> RunAsync(byte[] program, P28ProducerInput[] cases, string[] assumptions)
    {
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner,
            P28ProducerValidator.CreateRequest(RomImage.FromBytes(program), null, cases, assumptions));
        return response.Response;
    }

    private static byte[] Program(bool producerAdd, bool compactAdd)
    {
        // Newly authored independent composition probe, not a translation of the OEM producer.
        var program = new byte[32768];
        var g = new List<byte> { 0xF9, 0x50, 0xE0, 0x60, 0x03 };
        if (producerAdd) { g.AddRange([0x45, 0x81]); }
        g.AddRange([0xB5, 0xC4, 0x10, 0x03, 0xA5, 0x07]);
        g.CopyTo(program, 0x0772);
        var f = new List<byte>();
        if (compactAdd) { f.AddRange([0x47, 0x81]); }
        f.AddRange([0xF5, 0xC4, 0xD3, 0xB3, 0xCB, compactAdd ? (byte)0x53 : (byte)0x55]);
        f.CopyTo(program, 0x07C7);
        program[0x122C] = 0xCB;
        program[0x122D] = 0x3F;
        return program;
    }
}
