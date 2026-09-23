using System.IO;
using System.Text;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Tests;

public sealed class UnifiedCalibrationDesktopTests
{
    [Fact]
    public void FourAsymmetricMatricesCoverAllEightHundredCoreCoordinates()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var maps = model.Unified.Maps;
        Assert.Equal(new[] { "map_0", "map_1", "ignition_map_0", "ignition_map_1" }, maps.Select(map => map.Id));
        Assert.Equal(800, maps.Sum(map => map.Cells.Count));
        foreach (var map in maps)
        {
            Assert.Equal(20, map.Rows.Count); Assert.All(map.Rows, row => Assert.Equal(10, row.Cells.Count));
            Assert.Equal("256 — кінцева межа; збережений byte 0", map.LoadAxes[9]);
            Assert.Equal("256 — кінцева межа; збережений byte 0", map.Rows[19].Axis);
            foreach (var cell in map.Cells)
                Assert.Equal(map.IsFuel ? P28FuelMapContract.CellOffset(map.Id, cell.Row, cell.Column) :
                    P28IgnitionMapContract.CellOffset(map.Id, cell.Row, cell.Column), cell.Offset);
            Assert.Equal(map.IsFuel ? 10 : 0, map.Multipliers.Count);
        }
        Assert.NotEqual(maps[0].Cell(3, 7).Original, maps[1].Cell(3, 7).Original);
        Assert.NotEqual(maps[2].Cell(19, 9).Original, maps[3].Cell(19, 9).Original);
        Assert.Null(typeof(UnifiedMapCell).GetProperty(nameof(UnifiedMapCell.Original))!.SetMethod);
        Assert.Null(typeof(UnifiedMapCell).GetProperty(nameof(UnifiedMapCell.Offset))!.SetMethod);
    }

    [Fact]
    public void NullEmptyExplicitUnchangedAndResetProvenanceRemainDistinct()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var map = model.Unified.Maps[0]; Assert.Null(map.Snapshot());
        map.Included = true; Assert.Empty(map.Snapshot()!);
        var old = map.Cell(19, 9).Original;
        map.Cell(19, 9).Text = old.ToString(System.Globalization.CultureInfo.InvariantCulture);
        // Re-entering an unchanged value is explicit via bulk operation.
        map.Fill(19, 9, 19, 9, old.ToString(System.Globalization.CultureInfo.InvariantCulture));
        Assert.Single(map.Snapshot()!); Assert.True(map.Cell(19, 9).Explicit); Assert.False(map.Cell(19, 9).ByteChanged);
        map.Reset(19, 9, 19, 9); Assert.Empty(map.Snapshot()!); Assert.False(map.Cell(19, 9).Explicit);
        map.Undo(); Assert.Single(map.Snapshot()!);
        map.Included = false; Assert.Null(map.Snapshot());
    }

    [Fact]
    public void PasteFillResetAreAtomicAndUndoRedoAreSessionBound()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var map = model.Unified.Maps[1]; map.Included = true;
        map.ApplyRect(18, 8, "1\t2\n3\t4");
        Assert.Equal(4, map.Snapshot()!.Count); Assert.Equal(4, map.Cell(19, 9).Requested);
        var before = map.Snapshot()!.ToArray();
        foreach (var bad in new[] { "5\t6\n7", "5\t", "5\t256", "5\t=1+1", "5\t6\n7\t8\n9\t10" })
        {
            Assert.ThrowsAny<Exception>(() => map.ApplyRect(18, 8, bad));
            Assert.Equal(before, map.Snapshot()!);
        }
        map.Fill(18, 8, 19, 9, "255"); Assert.All(map.Snapshot()!, cell => Assert.Equal(255, cell.Value));
        map.Undo(); Assert.Equal(before, map.Snapshot()!);
        map.Redo(); Assert.All(map.Snapshot()!, cell => Assert.Equal(255, cell.Value));
        map.Undo(); map.Fill(18, 8, 18, 8, "9"); Assert.False(map.CanRedo);
        model.EnterDemo(); Assert.False(model.Unified.Maps[1].CanUndo); Assert.False(model.Unified.Maps[1].Included);
    }

    [Fact]
    public void HiddenInvalidIncludedCellBlocksSnapshotButExcludedGroupIsNull()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var map = model.Unified.Maps[2]; map.Included = true; map.Cell(19, 9).Text = "";
        model.Unified.SelectedMapIndex = 0;
        Assert.ThrowsAny<Exception>(() => map.Snapshot());
        map.Included = false; Assert.Null(map.Snapshot()); Assert.Equal("", map.Cell(19, 9).Text);
        map.Included = true; Assert.ThrowsAny<Exception>(() => map.Snapshot());
    }

    [Fact]
    public async Task CoreSettingsRoundtripAndDemoCannotPublish()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        model.Unified.Maps[0].Included = true;
        model.Unified.Maps[0].Fill(0, 0, 0, 0, "42");
        model.Unified.Maps[2].Included = true;
        var path = Path.Combine(f.DirectoryPath, "d2-settings.json");
        await model.Unified.SaveSettingsAsync(path);
        var parsed = P28UnifiedCalibrationSettings.Parse(File.ReadAllText(path));
        Assert.Equal(42, Assert.Single(parsed.Fuel.Map0!).RawValue);
        Assert.Empty(parsed.Ignition.IgnitionMap0!);
        Assert.Null(parsed.Fuel.Map1);
        await model.Unified.PreviewAsync(); Assert.Contains("Вигадані дані", model.Unified.PreviewText);
        await model.Unified.SaveAsync(f.OutputPaths); Assert.False(File.Exists(f.OutputPaths.OutputPath));
        var malformed = f.Write("d2-bad.json", Encoding.UTF8.GetBytes(File.ReadAllText(path).Replace("\"row\": 0", "\"row\": 20", StringComparison.Ordinal)));
        var prior = model.Unified.Maps[0];
        await model.Unified.ImportAsync(malformed); Assert.Same(prior, model.Unified.Maps[0]);
    }

    [Fact]
    public async Task AllTenExplicitGroupsAndEightHundredMapCoordinatesRoundtrip()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        foreach (var group in model.Basic.Draft!.Groups) group.Included = true;
        foreach (var map in model.Unified.Maps) { map.Included = true; map.Fill(0, 0, 19, 9, "100"); }
        var path = Path.Combine(f.DirectoryPath, "d2-all-ten.json"); await model.Unified.SaveSettingsAsync(path);
        var settings = P28UnifiedCalibrationSettings.Parse(File.ReadAllText(path));
        Assert.NotNull(settings.Basic.Vtec); Assert.NotNull(settings.Basic.Limiter.Fixed);
        Assert.NotNull(settings.Basic.Limiter.Bank0); Assert.NotNull(settings.Basic.Limiter.Bank1);
        Assert.NotNull(settings.Basic.Idle.BaseTable); Assert.NotNull(settings.Basic.Idle.LateTable);
        Assert.Equal(200, settings.Fuel.Map0!.Count); Assert.Equal(200, settings.Fuel.Map1!.Count);
        Assert.Equal(200, settings.Ignition.IgnitionMap0!.Count); Assert.Equal(200, settings.Ignition.IgnitionMap1!.Count);
        Assert.Equal(800, new[] { settings.Fuel.Map0.Count, settings.Fuel.Map1.Count,
            settings.Ignition.IgnitionMap0.Count, settings.Ignition.IgnitionMap1.Count }.Sum());
        Assert.Equal(settings.ToJson(false), P28UnifiedCalibrationSettings.Parse(settings.ToJson(false)).ToJson(false));
    }

    [Fact]
    public void IndependentKnownValueModelProbeUsesCoreArithmeticAndFactorBypass()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        model.Unified.Maps[0].Included = true; model.Unified.Maps[0].Fill(0, 0, 0, 0, "10");
        model.Unified.ProbeRpm = "0"; model.Unified.ProbeLoad = "0"; model.Unified.ProbeFactor = "0";
        model.Unified.ProbeCommand.Execute(null);
        Assert.Contains("original/requested=0/20", model.Unified.ProbeText); // 10 × readonly multiplier 2.
        model.Unified.SelectedMapIndex = 2; model.Unified.Maps[2].Included = true;
        model.Unified.Maps[2].Fill(0, 0, 0, 0, "100"); model.Unified.ProbeFactor = "255";
        model.Unified.ProbeCommand.Execute(null);
        Assert.Contains("consumer output=99", model.Unified.ProbeText); // high byte of 100 × 255.
    }

    [Fact]
    public void ClipboardIsReadOnlyByExplicitPasteAndExcludedProbeUsesOriginal()
    {
        using var f = new DesktopFixture(); var clipboard = new CountingClipboard("7\t8\n9\t10");
        using var model = new MainViewModel(f.Dialogs, resources: new DesktopResources(f.DirectoryPath), clipboard: clipboard);
        model.EnterDemo(); Assert.Equal(0, clipboard.Reads);
        model.Unified.SelectRectangle(18, 8, 19, 9);
        model.Unified.PasteCommand.Execute(null);
        Assert.Equal(1, clipboard.Reads); Assert.Equal(10, model.Unified.Maps[0].Cell(19, 9).Requested);
        Assert.Null(model.Unified.Maps[0].Snapshot());
        model.Unified.ProbeRpm = "0"; model.Unified.ProbeLoad = "0";
        model.Unified.ProbeCommand.Execute(null);
        Assert.Contains("Ці зміни не включені у збереження", model.Unified.ProbeText);
    }

    [Fact]
    public async Task ImportedUnchangedCoordinateSurvivesMapSwitchAndPreview()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var original = model.Unified.Maps[0].Cell(19, 9).Original;
        var settings = new P28UnifiedCalibrationSettings(model.Basic.Draft!.Snapshot(),
            new P28FuelMapExportSettings([new(19, 9, original)], null),
            new P28IgnitionMapExportSettings(null, null));
        var source = f.Write("d2-explicit-unchanged.json", Encoding.UTF8.GetBytes(settings.ToJson()));
        await model.Unified.ImportAsync(source);
        Assert.True(model.Unified.Maps[0].Cell(19, 9).Explicit);
        model.Unified.SelectedMapIndex = 3; model.Unified.SelectedMapIndex = 0;
        await model.Unified.PreviewAsync();
        var destination = Path.Combine(f.DirectoryPath, "d2-roundtrip.json");
        await model.Unified.SaveSettingsAsync(destination);
        var imported = P28UnifiedCalibrationSettings.Parse(File.ReadAllText(destination));
        Assert.Equal(original, Assert.Single(imported.Fuel.Map0!).RawValue);
    }

    [Fact]
    public async Task ImportIsOneUnifiedUndoRedoOperationAcrossBasicAndMaps()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        model.Basic.Draft!.Groups[1].Included = true;
        model.Basic.Draft.Groups[1].Fields[0].Text = "405";
        model.Unified.Maps[0].Included = true;
        model.Unified.Maps[0].Fill(0, 0, 0, 0, "17");
        var beforeBasic = model.Basic.Draft.Groups[1].Fields[0].Text;
        var beforeMap = model.Unified.Maps[0].Cell(0, 0).Text;
        var importSettings = new P28UnifiedCalibrationSettings(
            BasicCalibrationDraft.Demo(() => { }, () => true).Snapshot(),
            new P28FuelMapExportSettings(null, [new(19, 9, 88)]),
            new P28IgnitionMapExportSettings([new(3, 4, 77)], null));
        var source = f.Write("d2-history-import.json", Encoding.UTF8.GetBytes(importSettings.ToJson()));
        await model.Unified.ImportAsync(source);
        Assert.False(model.Basic.Draft!.Groups[1].Included);
        Assert.Equal(88, model.Unified.Maps[1].Cell(19, 9).Requested);
        model.Unified.UndoCommand.Execute(null);
        Assert.Equal(beforeBasic, model.Basic.Draft.Groups[1].Fields[0].Text);
        Assert.Equal(beforeMap, model.Unified.Maps[0].Cell(0, 0).Text);
        Assert.False(model.Unified.Maps[1].Included);
        model.Unified.RedoCommand.Execute(null);
        Assert.False(model.Basic.Draft.Groups[1].Included);
        Assert.Equal(88, model.Unified.Maps[1].Cell(19, 9).Requested);
        model.Unified.UndoCommand.Execute(null);
        model.Unified.Maps[0].Fill(0, 0, 0, 0, "18");
        Assert.False(model.Unified.RedoCommand.CanExecute(null));
    }

    [Fact]
    public async Task UnifiedJobSharesTheLegacyGateAndRejectsLateSessionAttachment()
    {
        using var f = new DesktopFixture(); using var model = f.CreateModel(); model.EnterDemo();
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var current = true;
        var running = model.RunUnifiedJobAsync(async (_, session, job) => { await release.Task; current = model.BasicCurrent(session, job); });
        Assert.False(model.OpenBinCommand.CanExecute(null)); Assert.False(model.Basic.PreviewCommand.CanExecute(null));
        Assert.False(model.Unified.PreviewCommand.CanExecute(null)); Assert.False(model.CanUseLegacyWorkspace);
        var close = model.RequestCloseAsync(); Assert.False(close.IsCompleted);
        release.TrySetResult(); await running; await close; Assert.False(current);
    }

    [Fact]
    public void TypedM2eBoundsExceedLegacyD1ReaderWithoutChangingIt()
    {
        Assert.Equal(256 * 1024, P28UnifiedCalibrationSettings.MaximumBytes);
        Assert.Equal(4 * 1024 * 1024, P28UnifiedCalibrationPlan.MaximumBytes);
        Assert.Equal(256 * 1024 * 1024, P28UnifiedCalibrationReceipt.MaximumBytes);
        Assert.True(P28UnifiedCalibrationReceipt.MaximumBytes > P28BasicCalibrationReceipt.MaximumBytes);
    }

    private sealed class CountingClipboard(string text) : IClipboardTextProvider
    {
        public int Reads { get; private set; }
        public string GetText() { Reads++; return text; }
    }
}
