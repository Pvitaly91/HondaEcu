using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class P28AcquisitionRustIntegrationTests
{
    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualProcessUsesFrozenWordObservationAndPreservesEarlierNativeStores()
    {
        var scenario = P28AcquisitionScenario.Create(P28AcquisitionValidatorTests.State(),
            [new(0, 10, 0, 0, 0, false, 0, 0, false), new(1, 73, 0, 0, 4, false, 0, 0, false)],
            "Invented verbatim-copy probe, not the native interval procedure", [0]);
        var program = ToyProgram();
        var response = await Run(program, scenario);
        Assert.Equal("0.6.0", response.Response.GetProperty("runnerVersion").GetString());
        foreach (var sequence in response.Response.GetProperty("acquisitionSequences").EnumerateArray())
        {
            var first = sequence.GetProperty("checkpoints")[0];
            Assert.Equal(16, first.GetProperty("acquisition").GetProperty("peripheralAccesses")[0][1].GetInt32());
            Assert.Equal(10, first.GetProperty("acquisition").GetProperty("sampleWrites")[0][2].GetInt32());
            Assert.Equal(1, first.GetProperty("slotWriteCounts")[0].GetInt32()); // Same value is still an actual store.
            var last = sequence.GetProperty("checkpoints")[1].GetProperty("acquisition").GetProperty("stateAfter");
            Assert.Equal(10, last.GetProperty("samples")[0].GetInt32());
            Assert.Equal(73, last.GetProperty("samples")[4].GetInt32());
            Assert.Equal(73, last.GetProperty("previousTimestamp").GetInt32());
        }
        // The host must NOT mistake this different instruction program for model agreement.
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(program);
        var compared = P28AcquisitionValidator.Analyze(image, profile, binding, scenario, response);
        Assert.True(compared.HasFailure);
        Assert.Contains(compared.Issues, issue => issue.Stage == "Acquisition");
        Assert.Equal(65536 - 90, compared.Sequences[0].IndependentExpectedStates[0].Samples[0]);
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualChangedObservationAndOpcodeAffectActualResultAndAbortSuffix()
    {
        var scenario = P28AcquisitionValidatorTests.Scenario();
        var program = ToyProgram();
        var first = await Run(program, scenario);
        var observations = scenario.Observations.ToArray();
        observations[0] = observations[0] with { Tmr2 = 4321 };
        var changed = await Run(program, P28AcquisitionScenario.Create(scenario.InitialState, observations, "Changed explicit observation"));
        Assert.NotEqual(first.Response.GetProperty("acquisitionSequences")[0].GetProperty("checkpoints")[0].GetProperty("selectedTimestamp").GetInt32(),
            changed.Response.GetProperty("acquisitionSequences")[0].GetProperty("checkpoints")[0].GetProperty("selectedTimestamp").GetInt32());
        program[0x56BE] = 0x47;
        program[0x56BF] = 0xFF; // Independently undefined two-byte decode, not a substituted NOP.
        var failed = await Run(program, scenario);
        var sequence = failed.Response.GetProperty("acquisitionSequences")[0];
        Assert.Equal(2, sequence.GetProperty("checkpoints")[0].GetProperty("acquisition").GetProperty("status").GetInt32());
        Assert.Equal(4, sequence.GetProperty("checkpoints")[1].GetProperty("acquisition").GetProperty("status").GetInt32());
        Assert.Equal(0, sequence.GetProperty("completedObservations").GetInt32());
        Assert.Equal(1, sequence.GetProperty("remainingNotRun").GetInt32());
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualUnsupportedModeDoesNotReadPeripheralsOrWriteSamples()
    {
        var response = await Run(ToyProgram(), P28AcquisitionValidatorTests.Scenario(unsupported: true));
        foreach (var sequence in response.Response.GetProperty("acquisitionSequences").EnumerateArray())
        {
            var first = sequence.GetProperty("checkpoints")[0];
            Assert.Equal(JsonValueKind.Null, first.GetProperty("selectedTimestamp").ValueKind);
            Assert.Equal("UnsupportedMode", first.GetProperty("acquisition").GetProperty("disposition").GetString());
            Assert.Empty(first.GetProperty("acquisition").GetProperty("sampleWrites").EnumerateArray());
            Assert.Empty(first.GetProperty("acquisition").GetProperty("peripheralAccesses").EnumerateArray());
        }
    }

    private static Task<SliceProcessResponse> Run(byte[] program, P28AcquisitionScenario scenario) =>
        SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner,
            P28AcquisitionValidator.CreateRequest(RomImage.FromBytes(program), null, scenario));

    private static byte[] ToyProgram()
    {
        // Independently invented slot-select + copy probe shared with Rust's public tests.
        // It copies a timestamp VERBATIM, not the OEM interval algorithm: no IRQ/error/initialization path.
        var program = new byte[32768];
        byte[] copy = [0xF5, 0xA2, 0x53, 0xF8, 0x50, 0xE5, 0x3A, 0x8B, 0xD5, 0xEE, 0xD0, 0x60, 0x03, 0xF9, 0xC9, 0x4B];
        copy.CopyTo(program, 0x56BE);
        return program;
    }
}
