using System.IO;
using System.Text;
using System.Text.Json;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;

namespace HondaEcu.Desktop.Tests;

public sealed class RpmPlanningDesktopTests
{
    [Fact]
    public async Task NoScenarioHasNoRpmAndLeavesTheCompactCodePlotAvailable()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        Assert.Contains("clockHz", model.RpmScenarioSummary);
        Assert.Contains("eventsPerCrankRev", model.RpmScenarioSummary);
        await model.PreviewRpmAsync();
        using var json = JsonDocument.Parse(model.RpmReportJson!);
        Assert.Equal("Unavailable", json.RootElement.GetProperty("status").GetString());
        Assert.Equal(JsonValueKind.Null, json.RootElement.GetProperty("forward").ValueKind);
        Assert.Empty(model.RpmCandidates);
        Assert.False(model.HasRpmPlot);
        Assert.Equal(256, model.PlotRows.Count);
        Assert.False(model.CanUseRpmCandidate);
        Assert.False(model.RpmAllowAddEr1);
        Assert.False(model.RpmAllowAddEr3);
    }

    [Fact]
    public async Task DemoScenarioIsExplicitAndCannotBecomeARealBinDefault()
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        model.EnterDemo();
        Assert.Contains("unavailable", model.RpmScenarioSummary);
        model.LoadDemoRpmScenario();
        Assert.Contains("ВИГАДАНИЙ", model.RpmScenarioSummary);
        await model.OpenBinAsync(fixture.ParentPath);
        Assert.Contains("unavailable", model.RpmScenarioSummary);
        model.LoadDemoRpmScenario();
        Assert.Contains("лише", model.ErrorText);
        Assert.Contains("unavailable", model.RpmScenarioSummary);
        Assert.False(model.CanPreviewRpm);
    }

    [Fact]
    public async Task ExplicitOverrideKeepsOriginalScenarioAndExecutionPermissionsUnchanged()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel(new RpmOperations());
        var path = WriteScenario(fixture);
        var before = File.ReadAllBytes(path);
        model.LoadRpmScenario(path);
        model.RequestedRpm = "6001/2";
        model.RpmQueryProvenance = "Separate synthetic analyst query";
        model.RpmAllowAddEr1 = true;
        model.RpmAllowAddEr3 = true;
        await model.PreviewRpmAsync();
        using var json = JsonDocument.Parse(model.RpmReportJson!);
        var query = json.RootElement.GetProperty("query");
        Assert.Equal("ExplicitQueryOverride", query.GetProperty("querySource").GetString());
        Assert.Equal("6001", query.GetProperty("requestedRpm").GetProperty("numerator").GetString());
        Assert.Equal("3000", query.GetProperty("scenario").GetProperty("legacyRequestedRpm").GetProperty("numerator").GetString());
        Assert.False(model.AllowAddEr1);
        Assert.False(model.AllowAddEr3);
        Assert.Equal(before, File.ReadAllBytes(path));
    }

    [Fact]
    public async Task FullCandidatePreviewHasNoHiddenSelectionAndUsesCoreForwardResults()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        model.LoadRpmScenario(WriteScenario(fixture));
        model.RpmAllowAddEr1 = true;
        model.RpmAllowAddEr3 = true;
        await model.PreviewRpmAsync();
        Assert.Equal("", model.ErrorText);
        Assert.Equal(256, model.RpmCandidates.Count);
        Assert.Null(model.SelectedRpmCandidate);
        Assert.False(model.HasRpmPlot);
        Assert.Equal(64, model.RpmForwardRows.Count);
        Assert.All(model.RpmForwardRows, row => Assert.Contains("oki.add-er1-a", row.Evidence));
        // The test caller explicitly selects a row. The ViewModel never selects a winner itself.
        model.SelectedRpmCandidate = model.RpmCandidates.First(candidate => candidate.IsBest);
        Assert.True(model.HasRpmPlot);
        Assert.Contains(model.RpmPlotRows, row => row.Classification == "Mixed");
        Assert.Contains("PhysicalRpmAvailable=false", model.RpmScenarioSummary);
        Assert.False(model.CanUseRpmCandidate); // No authenticated M1g definition on this synthetic bound input.
        await model.UseRpmCandidateAsync();
        Assert.Null(model.RpmSelectionJson);
        Assert.False(model.CanSaveChecksumExport);
        model.RequestedRpm = "3001";
        Assert.Null(model.RpmReportJson);
        Assert.Null(model.SelectedRpmCandidate);
        Assert.Empty(model.RpmCandidates);
        Assert.False(model.HasRpmPlot);
    }

    [Theory]
    [InlineData("request")]
    [InlineData("scenario")]
    [InlineData("slot")]
    [InlineData("permission")]
    [InlineData("file")]
    public async Task StaleImmutableRpmJobsDoNotAttachEvenWhenServiceIgnoresCancellation(string change)
    {
        using var fixture = new DesktopFixture();
        var operations = new RpmOperations { Block = true, IgnoreCancellation = true };
        using var model = await fixture.CreateBoundModel(operations);
        var scenario = WriteScenario(fixture);
        model.LoadRpmScenario(scenario);
        var task = model.PreviewRpmAsync();
        await operations.Started.Task;
        var originalQuery = operations.Job!.Query;
        if (change == "request") model.RequestedRpm = "3001";
        if (change == "scenario") model.LoadRpmScenario(scenario);
        if (change == "slot") model.SelectedSlot = model.Slots[1];
        if (change == "permission") model.RpmAllowAddEr1 = true;
        if (change == "file") model.EnterDemo();
        operations.Release.TrySetResult();
        await task;
        Assert.True(operations.Token.IsCancellationRequested);
        Assert.Equal("3000", originalQuery.RequestedRpm!.Numerator);
        Assert.Empty(originalQuery.PermittedAssumptions);
        Assert.Equal(originalQuery.Scenario!.Digest, originalQuery.ScenarioDigest);
        Assert.Null(model.RpmReportJson);
        Assert.Null(model.RpmSelectionJson);
        Assert.Empty(model.RpmCandidates);
    }

    [Fact]
    public async Task ExternalScenarioChangeAndCancellationAreNotCountedAsCompletedPreview()
    {
        using var fixture = new DesktopFixture();
        var operations = new RpmOperations { Block = true };
        using var model = await fixture.CreateBoundModel(operations);
        var scenario = WriteScenario(fixture);
        model.LoadRpmScenario(scenario);
        var task = model.PreviewRpmAsync();
        await operations.Started.Task;
        File.AppendAllText(scenario, " ");
        operations.Release.TrySetResult();
        await task;
        Assert.Null(model.RpmReportJson);
        Assert.Contains("змінився", model.ErrorText);
        model.LoadRpmScenario(scenario);
        using var cancelModel = await fixture.CreateBoundModel(new RpmOperations { Block = true });
        var canceled = cancelModel.PreviewRpmAsync();
        cancelModel.Cancel();
        await canceled;
        Assert.Null(cancelModel.RpmReportJson);
        Assert.False(cancelModel.IsBusy);
    }

    [Fact]
    public async Task InvalidOverrideOrUnitsNeverReusesPreviousResults()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        var path = WriteScenario(fixture);
        model.LoadRpmScenario(path);
        model.RequestedRpm = "3000.5";
        model.RpmQueryProvenance = "Explicit invalid decimal input";
        await model.PreviewRpmAsync();
        Assert.Null(model.RpmReportJson);
        Assert.NotEmpty(model.ErrorText);
        File.WriteAllText(path, File.ReadAllText(path).Replace("\"Hz\"", "\"MHz\"", StringComparison.Ordinal));
        model.LoadRpmScenario(path);
        Assert.NotEmpty(model.ErrorText);
        Assert.Contains("unavailable", model.RpmScenarioSummary);
        Assert.Null(model.RpmReportJson);
    }

    [Fact]
    public async Task OversizedScenarioClearsPreviousStateAndDoesNotReachPlanningService()
    {
        using var fixture = new DesktopFixture();
        var operations = new RpmOperations();
        using var model = await fixture.CreateBoundModel(operations);
        var path = WriteScenario(fixture);
        model.LoadRpmScenario(path);
        Assert.DoesNotContain("unavailable", model.RpmScenarioSummary);
        File.WriteAllBytes(path, new byte[65537]);
        model.LoadRpmScenario(path);
        Assert.Contains("розмір", model.ErrorText);
        Assert.Contains("unavailable", model.RpmScenarioSummary);
        Assert.Null(model.RpmReportJson);
        Assert.Null(operations.Job);
        Assert.False(model.CanUseRpmCandidate);
        Assert.False(model.CanSaveRpmSelection);
    }

    [Fact]
    public async Task GrowingScenarioIsBoundedOnWorkerRecheckAndGettersDoNotReadFiles()
    {
        using var fixture = new DesktopFixture();
        var operations = new RpmOperations { Block = true };
        using var model = await fixture.CreateBoundModel(operations);
        var path = WriteScenario(fixture);
        model.LoadRpmScenario(path);
        var task = model.PreviewRpmAsync();
        await operations.Started.Task;
        var job = operations.Job!;
        var snapshot = job.Query.Scenario!.ToJson();
        File.WriteAllBytes(path, new byte[65537]);
        operations.Release.TrySetResult();
        await task;
        Assert.Contains("розмір", model.ErrorText);
        Assert.Null(model.RpmReportJson);
        Assert.Equal(snapshot, job.Query.Scenario.ToJson());
        File.Delete(path);
        var error = model.ErrorText;
        for (var index = 0; index < 20; index++)
        {
            Assert.True(model.CanPreviewRpm);
            Assert.False(model.CanUseRpmCandidate);
            Assert.False(model.CanSaveRpmSelection);
            Assert.False(model.CanSaveChecksumExport);
        }
        Assert.Equal(error, model.ErrorText);
    }

    private static string WriteScenario(DesktopFixture fixture)
    {
        P28ScalingQuantity Quantity(string value, string unit) => new(value, "1", unit, "Invented test only; not measured Honda hardware", "analyst-supplied");
        return fixture.Write("explicit-synthetic-scenario.json", Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new
        {
            formatVersion = 1,
            scope = "uniform-normal-intervals",
            quantities = new
            {
                clockHz = Quantity("1000000", "Hz"),
                timerClockDivisor = Quantity("32", "1"),
                eventsPerCrankRev = Quantity("3", "events/crank-revolution"),
                eventsPerSample = Quantity("1", "events/sample"),
                rpm = Quantity("3000", "crank-revolutions/minute"),
            },
        }, JsonDefaults.Create())));
    }

    private sealed class RpmOperations : IDesktopOperations
    {
        public bool Block { get; init; }
        public bool IgnoreCancellation { get; init; }
        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Release { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public DesktopRpmJob? Job { get; private set; }
        public CancellationToken Token { get; private set; }
        public async Task<P28RpmPlanningReport> PreviewRpmAsync(DesktopRpmJob job, CancellationToken token)
        {
            Job = job; Token = token; Started.TrySetResult();
            if (Block) await Release.Task.WaitAsync(IgnoreCancellation ? CancellationToken.None : token);
            // Transport/session test only; this mock is not model or native-execution evidence.
            return new("SyntheticTransportOnly", [], job.Query, null, [], [], [], "NotEstablished", null);
        }
        public Task<DesktopValidationResult> ValidateAsync(DesktopValidationJob job, CancellationToken cancellationToken) => throw new NotSupportedException();
        public Task<P28RawThresholdVerificationReport> SaveAsync(P28RawThresholdPatchResult result, DesktopSavePaths paths,
            IReadOnlyList<string> protectedPaths, CancellationToken cancellationToken) => throw new NotSupportedException();
    }
}
