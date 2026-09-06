using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class P28ChainRustIntegrationTests
{
    internal static byte[] Toy()
    {
        // Independently assembled non-firmware probe. It intentionally disagrees with the model:
        // acquisition copies the timestamp, G copies slot zero, F writes a constant, decision increments prior.
        var p = P28StatefulModelTests.Data();
        byte[] acquisition = [0xF5, 0xA2, 0x53, 0xF8, 0x50, 0xE5, 0x3A, 0xD0, 0x60, 0x03, 0xF9, 0xC9, 0x4E];
        byte[] g = [0x90, 0x15, 0xE0, 0x60, 0x03, 0xB5, 0xC4, 0x10, 0x03, 0xA5, 0x07];
        byte[] f = [0x77, 77, 0xD3, 0xB3, 0xCB, 0x55];
        byte[] decision = [0xF4, 0x31, 0x86, 1, 0xD4, 0x31, 0xF5, 0x22, 0x86, 1, 0xD5, 0x22, 0x03, 0xFC, 0x12];
        acquisition.CopyTo(p, 0x56BE); g.CopyTo(p, 0x0772); f.CopyTo(p, 0x07C7); decision.CopyTo(p, 0x122C); return p;
    }
    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualSubprocessCarriesNativeCodeRegistersAndPriorHistoryButDoesNotBecomeAModelPass()
    {
        var program = Toy(); var saved = program.ToArray();
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(program);
        var events = Enumerable.Range(0, 3).Select(i => P28ChainModelTests.Event(i) with { RunDecision = true, Slot = 0 }).ToArray();
        var s = P28ChainScenario.Create(P28ChainModelTests.Initial(), events, "Actual invented-program subprocess; must not be called actual-ROM model agreement");
        var json = s.ToJson(); var report = await P28ChainValidator.ExecuteAsync(image, profile, binding, true, ExecutionTestPaths.RustRunner, s, P28ChainValidator.Permissions);
        Assert.True(report.HasFailure); Assert.Single(report.ReplayDiagnostics);
        Assert.All(report.Sequences, sequence =>
        {
            Assert.Equal(3, sequence.CompletedDecisions);
            for (var i = 0; i < 3; i++)
            {
                var cp = sequence.Checkpoints[i]; Assert.Equal(77, cp.Stages[4].Actual.StateAtEntry.Code);
                Assert.Equal(0xA1 + i, cp.StateAfter.Decision.Data0131); Assert.Equal(0xA5 + i, cp.StateAfter.Decision.P1OutputData);
                Assert.Equal(0xA4 + i, cp.Stages[0].Actual.StateAfter.Decision.P1OutputData);
                Assert.Equal(s.Events[i].Tmr2, cp.Stages[2].Actual.StateAfter.Acquisition.PreviousT);
                Assert.Equal(2, cp.StateAfter.Decision.Data01D8);
                Assert.DoesNotContain(cp.Stages.SelectMany(stage => stage.Differences), d => d.Contains("reseeding", StringComparison.Ordinal) || d.Contains("aliases", StringComparison.Ordinal));
            }
        });
        Assert.Equal(saved, image.ToArray()); Assert.Equal(json, s.ToJson());
        Assert.Equal(s.InitialState.Decision.Data0131, report.Sequences[0].Checkpoints[1].Stages[0].Expected.Before.Decision.Data0131 & 0xF8);
    }
    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task UnsupportedAcquisitionRefusesBeforeExecutionAndDoesNotApplySuffixInputs()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(Toy());
        var initial = P28ChainModelTests.Initial(); initial = initial with { Acquisition = initial.Acquisition with { Data011F = 4 } };
        var s = P28ChainScenario.Create(initial, [P28ChainModelTests.Event(), P28ChainModelTests.Event(1)], "Unsupported mode probe");
        var r = await P28ChainValidator.ExecuteAsync(image, profile, binding, true, ExecutionTestPaths.RustRunner, s);
        Assert.False(r.HasFailure); Assert.Empty(r.ReplayDiagnostics);
        Assert.All(r.Sequences, seq =>
        {
            Assert.Equal(0, seq.StageCounts["Acquisition"].Executed); Assert.Equal(1, seq.StageCounts["Acquisition"].Unsupported);
            Assert.Equal("Unsupported", seq.Checkpoints[0].Stages[0].Validation); Assert.Null(seq.Checkpoints[0].SoftwareRequest);
            Assert.Equal("NotRun", seq.Checkpoints[1].Stages[0].Validation); Assert.Empty(seq.Checkpoints[1].CallerWrites);
        });
    }
    [Theory]
    [InlineData("timeout", SliceProcessFailure.Timeout)]
    [InlineData("duplicate", SliceProcessFailure.Protocol)]
    [InlineData("stdout-limit", SliceProcessFailure.ResponseLimit)]
    public async Task IntegratedCommandUsesExistingBoundedProcessAdapter(string failure, SliceProcessFailure expected)
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(Toy());
        var configuration = new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", configuration, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var options = new SliceProcessOptions { Arguments = [host, failure], Timeout = TimeSpan.FromSeconds(failure == "timeout" ? 1 : 15), MaximumResponseBytes = 1024 };
        var ex = await Assert.ThrowsAsync<SliceProcessException>(() => P28ChainValidator.ExecuteAsync(image, profile, binding, true, "dotnet", P28ChainModelTests.Scenario(), options: options));
        Assert.Equal(expected, ex.Failure);
    }
}
