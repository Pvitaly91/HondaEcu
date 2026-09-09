using System.IO;
using System.Text;
using System.Text.Json;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Tests;

public sealed class BasicCalibrationDesktopTests
{
    public static IEnumerable<object[]> Selections => Enumerable.Range(1, 63).Select(m => new object[] { m });
    [Theory, MemberData(nameof(Selections))]
    public void AllSelectionsUseExactSixKeyCoreSettings(int mask)
    {
        var d = BasicCalibrationDraft.Demo(() => { }, () => true);
        for (var i = 0; i < 6; i++) d.Groups[i].Included = (mask & (1 << i)) != 0;
        var json = d.Snapshot().ToJson(); var settings = P28BasicCalibrationSettings.Parse(json);
        Assert.Equal(json, settings.ToJson());
        using var doc = JsonDocument.Parse(json);
        Assert.Equal(8, doc.RootElement.EnumerateObject().Count());
        for (var i = 0; i < 6; i++) Assert.Equal((mask & (1 << i)) == 0, doc.RootElement.GetProperty(d.Groups[i].Id).ValueKind == JsonValueKind.Null);
        var copy = BasicCalibrationDraft.Demo(() => { }, () => true); copy.Apply(settings); Assert.Equal(json, copy.Snapshot().ToJson());
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    [InlineData(6)]
    [InlineData(7)]
    public void SlotSelectionDoesNotAccumulateOrMirror(int slot)
    {
        var d = BasicCalibrationDraft.Demo(() => { }, () => true); d.Vtec.Included = true; d.Vtec.Fields[0].Text = "254";
        d.SelectedSlot = d.Slots[slot].Id; d.Vtec.Fields[0].Text = "100";
        Assert.Equal(d.Slots[slot].Id, d.Snapshot().Vtec!.Slot); Assert.Equal(100, d.Snapshot().Vtec!.RawValue);
        Assert.Null(d.Snapshot().Limiter.Fixed); Assert.Single(d.Vtec.Fields);
    }
    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    [InlineData("12.5")]
    [InlineData("-1")]
    [InlineData("0x20")]
    [InlineData("99999999999")]
    [InlineData("256")]
    public void InvalidTextNeverExportsPreviousNumericValue(string text)
    {
        var d = BasicCalibrationDraft.Demo(() => { }, () => true); d.Vtec.Included = true; d.Vtec.Fields[0].Text = "100";
        d.Vtec.Fields[0].Text = text; Assert.ThrowsAny<Exception>(() => d.Snapshot()); Assert.Equal(text, d.Vtec.Fields[0].Text);
        d.Vtec.Included = false; Assert.Null(d.Snapshot().Vtec); // excluded draft stays local
    }
    [Fact]
    public void ResetNoopAxesAndIndependentBanks()
    {
        var d = BasicCalibrationDraft.Demo(() => { }, () => true);
        Assert.All(d.Groups, g => Assert.False(g.Included));
        d.Groups[2].Included = true; d.Groups[2].Fields[0].Text = "201";
        Assert.Null(d.Snapshot().Limiter.Bank1); Assert.Equal("240", d.Groups[3].Fields[0].Text);
        d.Groups[2].Reset(); Assert.False(d.Groups[2].Included); Assert.Equal("200", d.Groups[2].Fields[0].Text);
        Assert.Null(typeof(BasicRawField).GetProperty(nameof(BasicRawField.Axis))!.SetMethod);
        d.Vtec.Included = true; Assert.Equal(d.Vtec.Fields[0].Original, d.Snapshot().Vtec!.RawValue);
    }
    [Fact]
    public async Task AtomicImportRoundtripAndDemoPublicationRefusal()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var d = model.Basic.Draft!; d.Groups[4].Included = true; d.Groups[4].Fields[6].Text = "1700";
        var json = d.Snapshot().ToJson(); var good = f.Write("settings.json", Encoding.UTF8.GetBytes(json));
        await model.Basic.ImportAsync(good); Assert.Equal(json, model.Basic.Draft!.Snapshot().ToJson());
        var before = model.Basic.Draft;
        var bad = f.Write("bad.json", Encoding.UTF8.GetBytes(json.Replace("1700", "0", StringComparison.Ordinal)));
        await model.Basic.ImportAsync(bad); Assert.Same(before, model.Basic.Draft); Assert.Equal(json, model.Basic.Draft.Snapshot().ToJson());
        var output = Path.Combine(f.DirectoryPath, "new-settings.json"); await model.Basic.SaveSettingsAsync(output);
        Assert.Equal(json, File.ReadAllText(output));
        await model.Basic.PreviewAsync(); Assert.Null(model.Basic.CurrentPlan); Assert.Empty(model.Basic.Evidence);
        Assert.Equal(2, model.Basic.IdlePlots.Count); Assert.Equal(256, model.Basic.VtecPlot.Count);
        Assert.Contains("Не прошивка Honda", model.Basic.PreviewText);
        await model.Basic.SaveAsync(f.OutputPaths); Assert.False(File.Exists(f.OutputPaths.OutputPath)); Assert.Null(model.Basic.LastExport);
    }
    [Fact]
    public async Task InvalidCommitBlocksSnapshotAndEditingInvalidatesPreview()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        await model.Basic.PreviewAsync(); Assert.NotEmpty(model.Basic.IdlePlots);
        model.Basic.Draft!.Groups[4].Included = true; Assert.Empty(model.Basic.IdlePlots);
        model.Basic.CommitEdits = () => false; await model.Basic.PreviewAsync(); Assert.Contains("cell/row", model.Basic.Error);
        model.Basic.CommitEdits = null; await model.Basic.PreviewAsync(); Assert.NotEmpty(model.Basic.IdlePlots);
        model.SelectRunner(f.RunnerPath); Assert.Empty(model.Basic.IdlePlots);
        await model.OpenBinAsync(f.SmallRaw); Assert.Null(model.Basic.Draft); Assert.False(model.Basic.CanEdit);
    }
    [Fact]
    public async Task UnknownAndMismatchedOriginalCannotExposeM1tFields()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); await model.OpenBinAsync(f.SmallRaw);
        Assert.Null(model.Basic.Draft); await model.Basic.SelectLocationAsync(f.BindingPath); Assert.False(model.Basic.CanExport);
        await model.BindBaselineAsync(f.ProfilePath, f.BindingPath, true); Assert.Equal(DesktopAccessMode.RawOnly, model.Mode);
        await model.OpenBinAsync(f.ParentPath); await model.BindBaselineAsync(f.ProfilePath, f.BindingPath, true);
        // Legacy invented threshold-only image does not become an admitted combined calibration image.
        Assert.True(model.CanEdit); Assert.Null(model.Basic.Draft); Assert.Contains("M1t", model.Basic.Error);
    }
    [Fact]
    public async Task LegacyJobBlocksNewCommandsAndDocumentSwitchUntilCancellationCompletes()
    {
        using var f = new DesktopFixture(); var operations = new FakeOperations { Block = true, IgnoreCancellation = true };
        using var model = await f.CreateBoundModel(operations); model.SelectRunner(f.RunnerPath);
        var running = model.RunValidationAsync(DesktopValidationKind.Execute); await operations.Started.Task;
        Assert.True(model.Basic.IsBusy); Assert.False(model.Basic.OpenChildCommand.CanExecute(null));
        Assert.False(model.OpenBinCommand.CanExecute(null)); Assert.False(model.DemoCommand.CanExecute(null));
        var close = model.RequestCloseAsync(); Assert.False(close.IsCompleted); operations.Release.TrySetResult(); await running; await close;
        Assert.True(operations.Token.IsCancellationRequested); Assert.Null(model.Basic.LastExport);
    }
    [Fact]
    public void InputBoundsNewPathsAndAliasesAreRefused()
    {
        using var f = new DesktopFixture();
        Assert.Throws<InvalidDataException>(() => BasicCalibrationInput.ReadBounded(f.ParentPath, 4096));
        Assert.ThrowsAny<Exception>(() => BasicCalibrationInput.ProtectDestinations([f.ParentPath], [f.ParentPath]));
        Assert.ThrowsAny<Exception>(() => BasicCalibrationInput.ProtectDestinations([f.OutputPaths.OutputPath, f.OutputPaths.OutputPath], []));
        Assert.ThrowsAny<Exception>(() => BasicCalibrationService.Inspect(f.ParentPath, f.ParentPath, f.ProfilePath, f.BindingPath,
            f.BindingPath, f.BindingPath, f.BindingPath));
    }
    [Fact]
    public async Task NewWorkspaceUsesSharedGateAndCloseWaitsForIgnoringWorker()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var cancelled = false; var currentAfterClose = true;
        var task = model.RunBasicJobAsync(async (token, session, job) =>
        {
            await release.Task; cancelled = token.IsCancellationRequested; currentAfterClose = model.BasicCurrent(session, job);
        });
        Assert.True(model.IsBusy); Assert.False(model.PreviewCommand.CanExecute(null)); Assert.False(model.Basic.ImportCommand.CanExecute(null));
        Assert.False(model.CanUseLegacyWorkspace);
        var session = model.SessionId; var raw = model.Basic.Draft!.Vtec.Fields[0].Text;
        model.Basic.Draft.Vtec.Fields[0].Text = "99"; model.SelectedSlot = model.Slots[1]; model.SelectRunner(f.RunnerPath);
        await model.OpenBinAsync(f.SmallRaw); model.EnterDemo();
        Assert.Equal(session, model.SessionId); Assert.Equal(raw, model.Basic.Draft.Vtec.Fields[0].Text);
        Assert.Equal(DesktopAccessMode.Demo, model.Mode);
        var close = model.RequestCloseAsync(); Assert.False(close.IsCompleted); release.TrySetResult(); await task; await close;
        Assert.True(cancelled); Assert.False(currentAfterClose); Assert.Null(model.Basic.LastExport);
    }
    [Fact]
    public async Task EveryDraftInputInvalidatesPriorPresentationAndCoreResultCannotBeDeserialized()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        foreach (var group in model.Basic.Draft!.Groups)
        {
            await model.Basic.PreviewAsync(); Assert.NotEmpty(model.Basic.IdlePlots);
            group.Included = true; Assert.Empty(model.Basic.IdlePlots);
            await model.Basic.PreviewAsync(); Assert.NotEmpty(model.Basic.IdlePlots);
            group.Fields[0].Text = (group.Fields[0].Original + 1).ToString(System.Globalization.CultureInfo.InvariantCulture);
            Assert.Empty(model.Basic.IdlePlots);
        }
        await model.Basic.PreviewAsync(); model.Basic.Draft.SelectedSlot = model.Basic.Draft.Slots[1].Id; Assert.Empty(model.Basic.IdlePlots);
        Assert.Empty(typeof(BasicExportResult).GetConstructors());
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<BasicExportResult>("{}"));
    }
    [Fact]
    public async Task PendingDialogDrivenDocumentLoadBlocksBasicJobAndIsAwaitedOnClose()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var loading = model.RunDocumentLoadAsync(() => release.Task);
        Assert.True(model.IsBusy); Assert.False(model.Basic.PreviewCommand.CanExecute(null));
        var entered = false; await model.RunBasicJobAsync((_, _, _) => { entered = true; return Task.CompletedTask; });
        Assert.False(entered); var close = model.RequestCloseAsync(); Assert.False(close.IsCompleted);
        release.TrySetResult(); await loading; await close;
    }
}
