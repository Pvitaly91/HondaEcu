using System.IO;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Tests;

public sealed class MainViewModelTests
{
    [Fact]
    public async Task EmptyAndArbitraryRawFileNeverGrantSlotInterpretationOrWrite()
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        Assert.Equal(DesktopAccessMode.Empty, model.Mode);
        Assert.Empty(model.Slots);
        await model.OpenBinAsync(fixture.SmallRaw);
        Assert.Equal(DesktopAccessMode.RawOnly, model.Mode);
        Assert.Equal(3, model.FileSize);
        Assert.Contains("00 7F FF", model.HexPreview);
        Assert.Empty(model.Slots);
        Assert.False(model.CanEdit);
        model.ProposedRaw = "20";
        model.PreviewChange();
        await model.SaveCopyAsync(fixture.OutputPaths);
        Assert.False(File.Exists(fixture.OutputPaths.OutputPath));
        Assert.Contains("binding", model.ErrorText);
    }

    [Fact]
    public async Task OnlyMatchingBindingAndExplicitAcknowledgementEnableBaseline()
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        await model.OpenBinAsync(fixture.ParentPath);
        await model.BindBaselineAsync(fixture.ProfilePath, fixture.BindingPath, false);
        Assert.Equal(DesktopAccessMode.RawOnly, model.Mode);
        await model.BindBaselineAsync(fixture.ProfilePath, fixture.BindingPath, true);
        Assert.Equal(DesktopAccessMode.BoundBaseline, model.Mode);
        Assert.True(model.CanEdit);
        Assert.Equal(8, model.Slots.Count);
        Assert.Equal((byte)40, model.Slots[0].CurrentRaw);
        Assert.False(model.AllowAddEr1);
        Assert.False(model.AllowAddEr3);
    }

    [Fact]
    public async Task MismatchedBindingCannotBePromotedByAcknowledgement()
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        var other = fixture.Bytes.ToArray(); other[100] = 99;
        var path = fixture.Write("different.dat", other);
        await model.OpenBinAsync(path);
        await model.BindBaselineAsync(fixture.ProfilePath, fixture.BindingPath, true);
        Assert.Equal(DesktopAccessMode.RawOnly, model.Mode);
        Assert.False(model.CanEdit);
        Assert.Empty(model.Slots);
        Assert.NotEmpty(model.ErrorText);
    }

    [Fact]
    public void DemoHasInventedInMemorySlotsButNoBindingOrRomExecution()
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        model.EnterDemo();
        Assert.Equal(DesktopAccessMode.Demo, model.Mode);
        Assert.Contains("не прошивка Honda", model.ModeLabel);
        Assert.Contains("не створює binding", model.BindingStatus);
        Assert.Equal(8, model.FileSize);
        Assert.True(model.CanEdit);
        Assert.False(model.CanExecute);
        model.ProposedRaw = "45";
        model.PreviewChange();
        Assert.False(model.CanSave);
        Assert.Equal(1, model.ChangedByteCount);
        Assert.Equal(256, model.PlotRows.Count);
        Assert.False(model.PlotRows[40].Before);
        Assert.True(model.PlotRows[41].Before);
        Assert.False(model.PlotRows[45].After);
        Assert.True(model.PlotRows[46].After);
        Assert.Equal(new[] { 41, 42, 43, 44, 45 }, model.PlotRows.Where(row => row.Before != row.After).Select(row => (int)row.CompactCode));
    }

    [Theory]
    [InlineData("0", true)]
    [InlineData("255", true)]
    [InlineData("256", false)]
    [InlineData("-1", false)]
    [InlineData("+1", false)]
    [InlineData("0x80", false)]
    [InlineData("1.5", false)]
    [InlineData("1,5", false)]
    [InlineData(" 1", false)]
    [InlineData("1 ", false)]
    [InlineData("", false)]
    [InlineData("1000", false)]
    public void RawEntryIsUnambiguousDecimalByte(string input, bool expected) =>
        Assert.Equal(expected, MainViewModel.TryParseRaw(input, out _));

    [Fact]
    public async Task OnePendingSlotExactPreviewAndRevertPreserveInput()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        var originalHash = RomImage.Load(fixture.ParentPath).Hash;
        var chosen = model.SelectedSlot!;
        model.ProposedRaw = "45";
        model.PreviewChange();
        Assert.Equal(chosen.Id, model.PendingSlotId);
        Assert.Contains("0x6542: 28 → 2D", model.PreviewText);
        Assert.Equal(1, model.ChangedByteCount);
        Assert.True(model.CanSave);
        model.SelectedSlot = model.Slots[1];
        Assert.Equal(chosen.Id, model.SelectedSlot!.Id);
        Assert.Equal(chosen.Id, model.PendingSlotId);
        Assert.Contains("рівно один", model.ErrorText);
        model.RevertChange();
        Assert.Null(model.PendingSlotId);
        Assert.False(model.CanSave);
        Assert.All(model.PlotRows, row => Assert.Equal(row.Before, row.After));
        Assert.Equal(originalHash, RomImage.Load(fixture.ParentPath).Hash);
    }

    [Fact]
    public async Task NoOpIsExplicitAndEditingTextInvalidatesReviewedPlan()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        model.PreviewChange();
        Assert.Equal(0, model.ChangedByteCount);
        Assert.Contains("no-op", model.PreviewText);
        Assert.All(model.PlotRows, row => Assert.Equal(row.Before, row.After));
        model.ProposedRaw = "300";
        Assert.False(model.CanSave);
        model.PreviewChange();
        Assert.Contains("0–255", model.ErrorText);
        Assert.Null(model.PendingSlotId);
    }

    [Fact]
    public async Task SaveRequiresConfirmationAndTransitionsOnlyToVerifiedChild()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        model.ProposedRaw = "45";
        model.PreviewChange();
        fixture.Dialogs.Confirmation = false;
        await model.SaveCopyAsync(fixture.OutputPaths);
        Assert.False(File.Exists(fixture.OutputPaths.OutputPath));
        fixture.Dialogs.Confirmation = true;
        await model.SaveCopyAsync(fixture.OutputPaths);
        Assert.Equal("", model.ErrorText);
        Assert.True(File.Exists(fixture.OutputPaths.PlanPath));
        Assert.True(File.Exists(fixture.OutputPaths.ReportPath));
        Assert.Equal(DesktopAccessMode.VerifiedDerived, model.Mode);
        Assert.False(model.CanEdit);
        Assert.False(model.CanSave);
        Assert.Equal((byte)45, model.Slots[0].CurrentRaw);
        Assert.Equal(fixture.Bytes, File.ReadAllBytes(fixture.ParentPath));
        Assert.Contains("Незалежне повторне читання", model.ResultSummary);
        Assert.Contains("Unknown", fixture.Dialogs.LastConfirmation);
        Assert.Contains("NotFlashReady", fixture.Dialogs.LastConfirmation);
    }

    [Fact]
    public async Task DerivedRequiresAllOriginalLineageFilesAndNeverAllowsPatchChain()
    {
        using var fixture = new DesktopFixture();
        fixture.SaveChild();
        using var model = fixture.CreateModel();
        await model.OpenBinAsync(fixture.OutputPaths.OutputPath);
        Assert.Equal(DesktopAccessMode.RawOnly, model.Mode);
        await model.BindBaselineAsync(fixture.ProfilePath, fixture.BindingPath, true);
        Assert.Equal(DesktopAccessMode.RawOnly, model.Mode);
        await model.OpenDerivedAsync(fixture.OutputPaths.OutputPath, fixture.ParentPath, fixture.ProfilePath,
            fixture.BindingPath, fixture.OutputPaths.PlanPath, fixture.OutputPaths.ReportPath, true);
        Assert.Equal(DesktopAccessMode.VerifiedDerived, model.Mode);
        Assert.False(model.CanEdit);
        await model.VerifyChangeAsync();
        Assert.Contains("підтверджено", model.ResultSummary);
        var altered = File.ReadAllBytes(fixture.OutputPaths.OutputPath); altered[123] = 1;
        var badChild = fixture.Write("bad-child.dat", altered);
        using var other = fixture.CreateModel();
        await other.OpenDerivedAsync(badChild, fixture.ParentPath, fixture.ProfilePath,
            fixture.BindingPath, fixture.OutputPaths.PlanPath, fixture.OutputPaths.ReportPath, true);
        Assert.Equal(DesktopAccessMode.Empty, other.Mode);
        Assert.NotEmpty(other.ErrorText);
    }

    [Fact]
    public async Task SaveVerificationErrorRemainsVisibleAndDoesNotPromoteState()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations { SaveFailure = true };
        using var model = await fixture.CreateBoundModel(operations);
        model.ProposedRaw = "45";
        model.PreviewChange();
        await model.SaveCopyAsync(fixture.OutputPaths);
        Assert.Equal(DesktopAccessMode.BoundBaseline, model.Mode);
        Assert.Contains("readback", model.ErrorText);
        Assert.True(model.CanSave);
        Assert.False(model.IsBusy);
    }

    [Fact]
    public async Task SaveRejectsBindingChangedSinceOpeningBeforeCreatingArtifacts()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        model.ProposedRaw = "45";
        model.PreviewChange();
        var different = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, fixture.Profile.Id, 32768,
            RomImage.FromBytes(new byte[32768]).Hash, P28VtecInspector.ComputeProfileDigest(fixture.Profile));
        File.WriteAllText(fixture.BindingPath, different.ToJson());
        await model.SaveCopyAsync(fixture.OutputPaths);
        Assert.Equal(DesktopAccessMode.BoundBaseline, model.Mode);
        Assert.Contains("змінився", model.ErrorText);
        Assert.False(File.Exists(fixture.OutputPaths.OutputPath));
    }

    [Fact]
    public async Task SaveReadbackCannotSubstituteAnotherValidButUnconfirmedOneSlotEdit()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations
        {
            SaveReplacement = paths =>
            {
                var parent = RomImage.Load(fixture.ParentPath);
                var otherPlan = P28RawThresholdEditor.CreatePlan(parent, fixture.Profile, fixture.Binding, true,
                    P28ThresholdLogic.GetSlots()[0].Id, 55);
                var replacement = P28RawThresholdEditor.Apply(parent, fixture.Profile, fixture.Binding, otherPlan);
                return P28DesktopCopyWriter.Save(replacement, paths.OutputPath, paths.PlanPath, paths.ReportPath);
            },
        };
        using var model = await fixture.CreateBoundModel(operations);
        model.ProposedRaw = "45";
        model.PreviewChange();
        await model.SaveCopyAsync(fixture.OutputPaths);
        Assert.Equal(DesktopAccessMode.BoundBaseline, model.Mode);
        Assert.Contains("підтвердженій", model.ErrorText);
        Assert.False(model.OpenResultsCommand.CanExecute(null));
    }

    [Fact]
    public async Task FileVerificationRereadsDiskInsteadOfTrustingCachedChild()
    {
        using var fixture = new DesktopFixture();
        fixture.SaveChild();
        using var model = fixture.CreateModel();
        await model.OpenDerivedAsync(fixture.OutputPaths.OutputPath, fixture.ParentPath, fixture.ProfilePath,
            fixture.BindingPath, fixture.OutputPaths.PlanPath, fixture.OutputPaths.ReportPath, true);
        var bytes = File.ReadAllBytes(fixture.OutputPaths.OutputPath);
        bytes[200] = 123;
        File.WriteAllBytes(fixture.OutputPaths.OutputPath, bytes);
        await model.VerifyChangeAsync();
        Assert.Contains("змінився", model.ErrorText);
        Assert.False(model.OpenResultsCommand.CanExecute(null));
    }

    [Fact]
    public void CoreStageCountsRemainDistinctAndIncompleteResultsAreNotSuccess()
    {
        var execution = DesktopCounters.FromExecutionStages(new[]
        {
            new P28ExecutionCounts(28, 1, 2, 3, 4, 5, 6, 7),
            new P28ExecutionCounts(1, 1, 0, 0, 0, 0, 0, 0),
        });
        Assert.Equal(new DesktopCounters(2, 2, 7, 5, 6, 7, 0), execution);
        Assert.True(execution.HasFailure);
        var producer = DesktopCounters.FromProducerStages(new[]
        {
            new P28ProducerStageCounts(28, 1, 2, 3, 4, 5, 6, 7, 8),
            new P28ProducerStageCounts(1, 1, 0, 0, 0, 0, 0, 0, 0),
        });
        Assert.Equal(new DesktopCounters(2, 2, 11, 4, 5, 6, 7), producer);
        var incomplete = new DesktopCounters(100, 1, 5, 0, 0, 0, 10);
        Assert.False(incomplete.HasFailure);
        Assert.True(incomplete.HasIncompleteOrConditional);
    }

    [Fact]
    public void PreviewKeepsSelectedSlotIdentityStableForWpfBinding()
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        model.EnterDemo();
        var selected = model.SelectedSlot;
        var collection = model.Slots;
        model.ProposedRaw = "45";
        model.PreviewChange();
        Assert.Same(selected, model.SelectedSlot);
        Assert.Same(collection, model.Slots);
        Assert.Same(selected, model.Slots[0]);
        Assert.Equal("45", selected!.ProposedRaw);
        model.RevertChange();
        Assert.Same(selected, model.SelectedSlot);
        Assert.Equal("", selected.ProposedRaw);
    }

    [Fact]
    public async Task MissingRunnerDisablesExecutionButNotReadPreviewOrSave()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        Assert.False(model.CanExecute);
        Assert.Contains("відсутній", model.RunnerStatus);
        model.ProposedRaw = "45";
        model.PreviewChange();
        Assert.True(model.CanSave);
        await model.RunValidationAsync(DesktopValidationKind.Execute);
        Assert.Contains("відсутній", model.ErrorText);
    }

    [Fact]
    public async Task StrictDefaultAndOperationSpecificAssumptionConfirmationAreEnforced()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations();
        using var model = await fixture.CreateBoundModel(operations);
        model.SelectRunner(fixture.RunnerPath);
        await model.RunValidationAsync(DesktopValidationKind.Execute);
        Assert.Empty(operations.LastJob!.Assumptions);
        Assert.Equal(0, fixture.Dialogs.ConfirmationCount);
        model.AllowAddEr1 = true;
        Assert.False(model.CanExecuteM1d);
        await model.RunValidationAsync(DesktopValidationKind.Execute);
        Assert.Equal(1, operations.ValidationCount);
        fixture.Dialogs.Confirmation = false;
        await model.RunValidationAsync(DesktopValidationKind.Producer);
        Assert.Equal(1, operations.ValidationCount);
        fixture.Dialogs.Confirmation = true;
        model.AllowAddEr3 = true;
        await model.RunValidationAsync(DesktopValidationKind.Producer);
        Assert.Equal(2, operations.ValidationCount);
        Assert.Equal(new[] { P28ProducerModel.AddEr1Assumption, P28ByteExecutionValidator.AddAssumption }, operations.LastJob!.Assumptions);
        Assert.Contains("умовні", model.ResultSummary);
        Assert.Contains("Фізичні оберти не підтверджені", model.ResultSummary);
        Assert.Equal(3, model.Counters.Unresolved);
        Assert.Equal(4, model.Counters.NotRun);
    }

    [Fact]
    public async Task CancellationIsAwaitedAndNeverPublishesIncompleteResult()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations { Block = true };
        using var model = await fixture.CreateBoundModel(operations);
        model.SelectRunner(fixture.RunnerPath);
        var job = model.RunValidationAsync(DesktopValidationKind.Execute);
        await operations.Started.Task;
        Assert.True(model.IsBusy);
        model.Cancel();
        await job;
        Assert.False(model.IsBusy);
        Assert.True(operations.Token.IsCancellationRequested);
        Assert.Equal(DesktopCounters.Empty, model.Counters);
        Assert.False(model.OpenResultsCommand.CanExecute(null));
    }

    [Theory]
    [InlineData("file")]
    [InlineData("slot")]
    [InlineData("assumption")]
    [InlineData("runner")]
    public async Task StaleResultCannotAttachToChangedSessionEvenIfOperationIgnoresCancellation(string change)
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations { Block = true, IgnoreCancellation = true };
        using var model = await fixture.CreateBoundModel(operations);
        model.SelectRunner(fixture.RunnerPath);
        var initial = model.SessionId;
        var job = model.RunValidationAsync(DesktopValidationKind.Execute);
        await operations.Started.Task;
        if (change == "file") model.EnterDemo();
        if (change == "slot") model.SelectedSlot = model.Slots[1];
        if (change == "assumption") model.AllowAddEr3 = true;
        if (change == "runner") model.SelectRunner(fixture.RunnerPath + ".other");
        operations.Release.TrySetResult();
        await job;
        Assert.True(model.SessionId > initial);
        Assert.Equal(DesktopCounters.Empty, model.Counters);
        Assert.False(model.OpenResultsCommand.CanExecute(null));
        Assert.True(operations.Token.IsCancellationRequested);
    }

    [Fact]
    public async Task ClosingAwaitsCancellationCleanup()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations { Block = true };
        using var model = await fixture.CreateBoundModel(operations);
        model.SelectRunner(fixture.RunnerPath);
        var running = model.RunValidationAsync(DesktopValidationKind.Execute);
        await operations.Started.Task;
        await model.RequestCloseAsync();
        Assert.True(running.IsCompleted);
        Assert.True(operations.Token.IsCancellationRequested);
        Assert.False(model.IsBusy);
    }

    [Theory]
    [InlineData("original")]
    [InlineData("binding")]
    public async Task ExternalInputChangeDuringJobCannotPublishStaleResult(string target)
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations { Block = true };
        using var model = await fixture.CreateBoundModel(operations);
        model.SelectRunner(fixture.RunnerPath);
        var running = model.RunValidationAsync(DesktopValidationKind.Execute);
        await operations.Started.Task;
        if (target == "original")
        {
            var changed = fixture.Bytes.ToArray(); changed[99] = 7;
            File.WriteAllBytes(fixture.ParentPath, changed);
        }
        else
        {
            var changed = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, fixture.Profile.Id, 32768,
                RomImage.FromBytes(new byte[32768]).Hash, P28VtecInspector.ComputeProfileDigest(fixture.Profile));
            File.WriteAllText(fixture.BindingPath, changed.ToJson());
        }
        operations.Release.TrySetResult();
        await running;
        Assert.Contains("змінився", model.ErrorText);
        Assert.Equal(DesktopCounters.Empty, model.Counters);
        Assert.False(model.OpenResultsCommand.CanExecute(null));
    }

    [Fact]
    public async Task PendingImageJobSnapshotUsesOriginalBindingAndVerifiedInMemoryChild()
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations();
        using var model = await fixture.CreateBoundModel(operations);
        model.SelectRunner(fixture.RunnerPath);
        model.ProposedRaw = "45";
        model.PreviewChange();
        await model.RunValidationAsync(DesktopValidationKind.Execute);
        var document = operations.LastJob!.Document;
        Assert.Equal(DesktopAccessMode.VerifiedDerived, document.Mode);
        Assert.Equal(document.Parent!.Hash, document.Binding!.RomHash);
        Assert.NotEqual(document.Image.Hash, document.Binding.RomHash);
        Assert.True(P28RawThresholdEditor.Verify(document.Image, document.Parent, document.Profile!, document.Binding, document.Plan!, document.PatchReport!).IsValid);
    }

    [Fact]
    public void ResourcesAreRootedAtApplicationDirectoryWithNoCwdOrRepositorySearch()
    {
        using var fixture = new DesktopFixture();
        var resources = new DesktopResources(Path.Combine(fixture.DirectoryPath, "Портативна копія з пробілами"));
        Assert.Equal(Path.Combine(resources.ApplicationDirectory, "tools", "p28-slice-runner.exe"), resources.BundledRunnerPath);
        Assert.Equal(Path.Combine(resources.ApplicationDirectory, "definitions", "p28", "p28-304.experimental.json"), resources.DefaultProfilePath);
        Assert.Equal(Path.GetFullPath(AppContext.BaseDirectory), new DesktopResources().ApplicationDirectory);
        Assert.DoesNotContain(System.IO.Directory.GetCurrentDirectory(), resources.BundledRunnerPath);
    }
}

internal sealed class DesktopFixture : IDisposable
{
    public DesktopFixture()
    {
        DirectoryPath = Path.Combine(Path.GetTempPath(), "HondaEcu.Desktop.Tests", Guid.NewGuid().ToString("N"));
        System.IO.Directory.CreateDirectory(DirectoryPath);
        Bytes = new byte[32768];
        new byte[] { 40, 55, 80, 95, 120, 135, 160, 175 }.CopyTo(Bytes, P28ThresholdLogic.BlockOffset);
        ParentPath = Write("synthetic-parent.dat", Bytes);
        SmallRaw = Write("arbitrary.dat", new byte[] { 0, 127, 255 });
        ProfilePath = Path.Combine(AppContext.BaseDirectory, "test-resources", "p28-304.experimental.json");
        Profile = RomProfile.Load(ProfilePath);
        var image = RomImage.Load(ParentPath);
        Binding = new(1, P28CompactModel.ModelId, Profile.Id, image.Size, image.Hash, P28VtecInspector.ComputeProfileDigest(Profile));
        BindingPath = Path.Combine(DirectoryPath, "synthetic-test-binding.json");
        File.WriteAllText(BindingPath, Binding.ToJson());
        RunnerPath = Write("injected-test-runner.dat", new byte[] { 1 });
        OutputPaths = new(Path.Combine(DirectoryPath, "child.dat"), Path.Combine(DirectoryPath, "child.plan.json"), Path.Combine(DirectoryPath, "child.report.json"));
    }
    public string DirectoryPath { get; }
    public byte[] Bytes { get; }
    public string ParentPath { get; }
    public string SmallRaw { get; }
    public string ProfilePath { get; }
    public RomProfile Profile { get; }
    public P28ExactBaselineBinding Binding { get; }
    public string BindingPath { get; }
    public string RunnerPath { get; }
    public DesktopSavePaths OutputPaths { get; }
    public FakeDialogs Dialogs { get; } = new();
    public MainViewModel CreateModel(IDesktopOperations? operations = null) => new(Dialogs, operations, new DesktopResources(DirectoryPath));
    public async Task<MainViewModel> CreateBoundModel(IDesktopOperations? operations = null)
    {
        var model = CreateModel(operations);
        await model.OpenBinAsync(ParentPath);
        await model.BindBaselineAsync(ProfilePath, BindingPath, true);
        Assert.Equal(DesktopAccessMode.BoundBaseline, model.Mode);
        return model;
    }
    public string Write(string name, byte[] data) { var path = Path.Combine(DirectoryPath, name); File.WriteAllBytes(path, data); return path; }
    public void SaveChild()
    {
        var parent = RomImage.Load(ParentPath);
        var plan = P28RawThresholdEditor.CreatePlan(parent, Profile, Binding, true, P28ThresholdLogic.GetSlots()[0].Id, 45);
        var result = P28RawThresholdEditor.Apply(parent, Profile, Binding, plan);
        P28DesktopCopyWriter.Save(result, OutputPaths.OutputPath, OutputPaths.PlanPath, OutputPaths.ReportPath, new[] { BindingPath });
    }
    public void Dispose() => System.IO.Directory.Delete(DirectoryPath, true);
}

internal sealed class FakeDialogs : IDialogService
{
    public bool Confirmation { get; set; } = true;
    public int ConfirmationCount { get; private set; }
    public string LastConfirmation { get; private set; } = "";
    public string? OpenFile(string title, string filter) => null;
    public string? SaveFile(string title, string filter, string suggestedName) => null;
    public bool Confirm(string title, string message) { ConfirmationCount++; LastConfirmation = message; return Confirmation; }
    public void ShowMessage(string title, string message) { }
    public void ShowStructuredResult(string title, string json) { }
}

internal sealed class FakeOperations : IDesktopOperations
{
    public P28NativeChecksumReport? ChecksumReport { get; init; }
    public bool Block { get; init; }
    public bool IgnoreCancellation { get; init; }
    public bool SaveFailure { get; init; }
    public Func<DesktopSavePaths, P28RawThresholdVerificationReport>? SaveReplacement { get; init; }
    public int ValidationCount { get; private set; }
    public DesktopValidationJob? LastJob { get; private set; }
    public CancellationToken Token { get; private set; }
    public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public TaskCompletionSource Release { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public async Task<DesktopValidationResult> ValidateAsync(DesktopValidationJob job, CancellationToken cancellationToken)
    {
        ValidationCount++;
        LastJob = job;
        Token = cancellationToken;
        Started.TrySetResult();
        if (Block) await Release.Task.WaitAsync(IgnoreCancellation ? CancellationToken.None : cancellationToken);
        if (ChecksumReport is not null)
            return new(DesktopCounters.From(ChecksumReport.Counts), ChecksumReport.ToJson(), ChecksumReport.HasFailure,
                ChecksumReport.PermittedAssumptions, ChecksumReport.UsedAssumptions, "NotFlashReady", ChecksumReport);
        return new(new(2, 1, 3, 0, 0, 0, 4), "{\"syntheticTestReport\":true}", false, job.Assumptions, job.Assumptions,
            "Фізичні оберти не підтверджені");
    }
    public Task<P28RawThresholdVerificationReport> SaveAsync(P28RawThresholdPatchResult result, DesktopSavePaths paths,
        IReadOnlyList<string> protectedPaths, CancellationToken cancellationToken) => SaveFailure
        ? Task.FromException<P28RawThresholdVerificationReport>(new IOException("Synthetic readback verification failure"))
        : SaveReplacement is not null ? Task.FromResult(SaveReplacement(paths))
            : new DesktopOperations().SaveAsync(result, paths, protectedPaths, cancellationToken);
}
