using System.IO;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.Tests;

public sealed class NativeChecksumDesktopTests
{
    [Fact]
    public async Task UnknownAndDemoDoNotExposeNativeHondaChecksum()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations();
        using var model = fixture.CreateModel(operations);
        Assert.False(model.CanCheckChecksum);
        model.EnterDemo();
        Assert.False(model.ChecksumCommand.CanExecute(null));
        await model.RunValidationAsync(DesktopValidationKind.Checksum);
        await model.OpenBinAsync(fixture.ParentPath);
        Assert.False(model.CanCheckChecksum);
        await model.RunValidationAsync(DesktopValidationKind.Checksum);
        Assert.Equal(0, operations.ValidationCount);
        Assert.False(model.HasChecksumResult);
    }

    [Fact]
    public async Task MissingRunnerStillAllowsSeparateArithmeticAndNeverInheritsAddPermissions()
    {
        using var fixture = new DesktopFixture();
        var report = SyntheticReport(fixture, NativeChecksumExecutionStatus.NotRun, NativeChecksumDisposition.Unknown);
        var operations = new FakeOperations { ChecksumReport = report };
        using var model = await fixture.CreateBoundModel(operations);
        Assert.False(model.CanExecute);
        Assert.True(model.CanCheckChecksum);
        model.AllowAddEr1 = true;
        model.AllowAddEr3 = true;
        await model.RunValidationAsync(DesktopValidationKind.Checksum);
        Assert.Empty(operations.LastJob!.Assumptions);
        Assert.Equal(0, fixture.Dialogs.ConfirmationCount);
        Assert.True(model.HasChecksumResult);
        Assert.Contains("C# result 0x01", model.ChecksumSummary!.Arithmetic);
        Assert.Contains("NotRun", model.ChecksumSummary.Execution);
        Assert.Equal(1, model.Counters.NotRun);
        Assert.Contains("NotFlashReady", model.ChecksumSummary.Reason);
        Assert.Equal(fixture.Bytes, File.ReadAllBytes(fixture.ParentPath));
        Assert.False(File.Exists(fixture.OutputPaths.OutputPath));
    }

    [Theory]
    [InlineData(NativeChecksumExecutionStatus.Match, NativeChecksumDisposition.Invalid)]
    [InlineData(NativeChecksumExecutionStatus.ConditionalMatch, NativeChecksumDisposition.Unknown)]
    [InlineData(NativeChecksumExecutionStatus.UnresolvedInstruction, NativeChecksumDisposition.Unresolved)]
    [InlineData(NativeChecksumExecutionStatus.ExecutionError, NativeChecksumDisposition.Unknown)]
    [InlineData(NativeChecksumExecutionStatus.Match, NativeChecksumDisposition.DisabledOrAltered)]
    [InlineData(NativeChecksumExecutionStatus.NotRun, NativeChecksumDisposition.UnsupportedRevision)]
    public void ArithmeticDecisionExecutionAndEvidenceStaySeparate(NativeChecksumExecutionStatus execution,
        NativeChecksumDisposition disposition)
    {
        using var fixture = new DesktopFixture();
        var report = SyntheticReport(fixture, execution, disposition);
        var summary = DesktopChecksumSummary.From(report);
        Assert.Contains("арифметична нерівність", summary.Arithmetic);
        Assert.Contains(disposition.ToString(), summary.Arithmetic);
        Assert.Contains(execution.ToString(), summary.Execution);
        Assert.Contains("[0x0000,0x0004)", summary.Coverage);
        Assert.Contains("fixed residue", summary.Coverage);
        Assert.Contains("synthetic evidence", summary.Evidence);
        Assert.Contains("scoped test reason", summary.Reason);
        Assert.DoesNotContain("Прошивка безпечна", summary.Reason);
        if (execution == NativeChecksumExecutionStatus.ConditionalMatch)
            Assert.Contains("synthetic.unconfirmed-form", summary.Assumptions);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CanceledOrStaleChecksumCannotAttachEvenIfWorkerIgnoresCancellation(bool changeFile)
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations
        {
            Block = true,
            IgnoreCancellation = true,
            ChecksumReport = SyntheticReport(fixture, NativeChecksumExecutionStatus.Match, NativeChecksumDisposition.Invalid)
        };
        using var model = await fixture.CreateBoundModel(operations);
        var running = model.RunValidationAsync(DesktopValidationKind.Checksum);
        await operations.Started.Task;
        if (changeFile) model.EnterDemo(); else model.Cancel();
        operations.Release.TrySetResult();
        await running;
        Assert.True(operations.Token.IsCancellationRequested);
        Assert.False(model.IsBusy);
        Assert.False(model.HasChecksumResult);
        Assert.False(model.OpenResultsCommand.CanExecute(null));
        Assert.Equal(DesktopCounters.Empty, model.Counters);
    }

    [Fact]
    public async Task ChecksumUsesVerifiedPendingLineageWithoutSavingOrRepairing()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations
        {
            ChecksumReport = SyntheticReport(fixture,
            NativeChecksumExecutionStatus.Match, NativeChecksumDisposition.Invalid)
        };
        using var model = await fixture.CreateBoundModel(operations);
        model.ProposedRaw = "45";
        model.PreviewChange();
        await model.RunValidationAsync(DesktopValidationKind.Checksum);
        var document = operations.LastJob!.Document;
        Assert.NotNull(document.Plan);
        Assert.Equal(document.Parent!.Hash, document.Binding!.RomHash);
        Assert.True(P28RawThresholdEditor.Verify(document.Image, document.Parent, document.Profile!,
            document.Binding, document.Plan!, document.PatchReport!).IsValid);
        Assert.Equal(ChecksumStatus.Unknown, document.PatchReport!.ChecksumStatus);
        Assert.Equal(1, model.ChangedByteCount);
        Assert.True(model.CanSave);
        Assert.Equal(fixture.Bytes, File.ReadAllBytes(fixture.ParentPath));
        Assert.False(File.Exists(fixture.OutputPaths.OutputPath));
        model.RevertChange();
        Assert.False(model.HasChecksumResult);
    }

    private static P28NativeChecksumReport SyntheticReport(DesktopFixture fixture,
        NativeChecksumExecutionStatus status, NativeChecksumDisposition disposition)
    {
        var assumptions = status == NativeChecksumExecutionStatus.ConditionalMatch ? new[] { "synthetic.unconfirmed-form" } : [];
        var coverage = new[] { new ByteRange(0, 4) };
        var complete = status is NativeChecksumExecutionStatus.Match or NativeChecksumExecutionStatus.ConditionalMatch;
        var execution = new P28ChecksumExecution(0, status, complete, complete ? 1 : null,
            complete ? "invalid" : null, complete ? 2 : 0, complete ? 12 : 0, null, complete ? 4 : 0,
            complete ? coverage : [], complete, complete, assumptions, [], "synthetic execution reason");
        var counts = new P28ChecksumExecutionCounts(1, status == NativeChecksumExecutionStatus.Match ? 1 : 0,
            assumptions.Length, status == NativeChecksumExecutionStatus.UnresolvedInstruction ? 1 : 0, 0,
            status == NativeChecksumExecutionStatus.ExecutionError ? 1 : 0, 0,
            status == NativeChecksumExecutionStatus.NotRun ? 1 : 0);
        var contract = new P28NativeChecksumContract("synthetic-contract", "invented four bytes, not Honda",
            "invented sum", 8, 0, 0, null, coverage, [], "ascending", "little", 2, 2,
            "two calls", "synthetic evidence", "not native Honda evidence");
        var item = new P28NativeChecksumCaseReport("invented-case", "synthetic", fixture.Binding.RomHash, [],
            new(true, disposition != NativeChecksumDisposition.DisabledOrAltered, disposition, [], "synthetic"),
            new(1, 0, false, 4, coverage, [], "synthetic arithmetic"), [execution], disposition,
            disposition == NativeChecksumDisposition.Invalid ? ChecksumStatus.Invalid : ChecksumStatus.Unknown, "scoped test reason");
        return new(1, "synthetic-desktop-test", contract, fixture.Profile.Id, fixture.Binding.RomHash, null,
            "synthetic-profile", "synthetic-binding", null, false, "strict", assumptions, assumptions, null, null,
            [], [], [item], counts, false, "synthetic evidence", "", false, false, false,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady, []);
    }
}
