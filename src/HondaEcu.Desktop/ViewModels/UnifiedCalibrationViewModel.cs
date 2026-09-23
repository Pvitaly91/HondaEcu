using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Windows;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;

namespace HondaEcu.Desktop.ViewModels;

public interface IClipboardTextProvider { string GetText(); }
public sealed class DesktopClipboardTextProvider : IClipboardTextProvider
{
    public string GetText() => Clipboard.GetText(); // Only called by the explicit Paste command.
}
public sealed record UnifiedRequestedValueRow(string Group, string Field, string Offset, int Original, int Requested);

/// <summary>One M2e draft: the six basic groups are the existing D1 draft, with four additional map groups.</summary>
public sealed class UnifiedCalibrationViewModel : INotifyPropertyChanged
{
    private const string JsonFilter = "JSON (*.json)|*.json";
    private const string BinFilter = "BIN (*.bin)|*.bin";
    private readonly MainViewModel _host;
    private readonly IDialogService _dialogs;
    private readonly IUnifiedCalibrationOperations _operations;
    private readonly IClipboardTextProvider _clipboard;
    private readonly Dictionary<string, byte[]> _imported = new(StringComparer.OrdinalIgnoreCase);
    private readonly Stack<UnifiedDraftRawState> _undo = new();
    private readonly Stack<UnifiedDraftRawState> _redo = new();
    private UnifiedDraftRawState? _lastState;
    private bool _restoring;
    private sealed record UnifiedDraftRawState(string Signature, BasicDraftRawState Basic, UnifiedMapRawState[] Maps);
    private UnifiedPreviewResult? _preview;
    private string? _previewSettings;
    private RomImage? _mapOriginal;
    private int _selectedMapIndex;
    private int _selectedRow;
    private int _selectedColumn;
    private (int Top, int Left, int Bottom, int Right) _selection;
    private string _fillRaw = "0";
    private string _probeRpm = "0", _probeLoad = "0", _probeFactor = "0";
    private MapDisplayMode _displayMode;

    public UnifiedCalibrationViewModel(MainViewModel host, IDialogService dialogs,
        IUnifiedCalibrationOperations operations, IClipboardTextProvider? clipboard = null)
    {
        _host = host; _dialogs = dialogs; _operations = operations; _clipboard = clipboard ?? new DesktopClipboardTextProvider();
        SelectLocationCommand = new(async () =>
        { var path = dialogs.OpenFile("Reviewed compensation definition", JsonFilter); if (path is not null) await SelectLocationAsync(path); }, () => CanEdit && _host.Mode == DesktopAccessMode.BoundBaseline);
        ImportCommand = new(async () => { var path = dialogs.OpenFile("M2e settings", JsonFilter); if (path is not null) await ImportAsync(path); }, () => CanEdit);
        SaveSettingsCommand = new(async () => { var path = dialogs.SaveFile("Новий M2e settings", JsonFilter, "unified-settings.json"); if (path is not null) await SaveSettingsAsync(path); }, () => CanEdit);
        PreviewCommand = new(PreviewAsync, () => CanEdit);
        SaveCommand = new(SaveFromDialogsAsync, () => CanExport);
        OpenChildCommand = new(OpenChildFromDialogsAsync, () => !_host.IsBusy);
        ReuseCommand = new(ReuseOriginalAsync, () => !_host.IsBusy && _host.Mode == DesktopAccessMode.VerifiedUnifiedDerived);
        PasteCommand = new(() => Do(() => SelectedMap.ApplyRect(_selection.Top, _selection.Left, _clipboard.GetText())), () => CanEdit && Maps.Count == 4);
        FillCommand = new(() => Do(() => SelectedMap.Fill(_selection.Top, _selection.Left, _selection.Bottom, _selection.Right, FillRaw)), () => CanEdit && Maps.Count == 4);
        ResetCellsCommand = new(() => Do(() => SelectedMap.Reset(_selection.Top, _selection.Left, _selection.Bottom, _selection.Right)), () => CanEdit && Maps.Count == 4);
        ResetMapCommand = new(() => Do(() => SelectedMap.Reset()), () => CanEdit && Maps.Count == 4);
        UndoCommand = new(() => Do(UndoDraft), () => CanEdit && _undo.Count != 0);
        RedoCommand = new(() => Do(RedoDraft), () => CanEdit && _redo.Count != 0);
        ProbeCommand = new(() => Do(UpdateProbe), () => Maps.Count == 4 && !_host.IsBusy);
    }
    public IReadOnlyList<UnifiedMapDraft> Maps { get; private set; } = [];
    public UnifiedMapDraft SelectedMap => Maps[_selectedMapIndex];
    public int SelectedMapIndex { get => _selectedMapIndex; set { if (value < 0 || value >= Maps.Count || value == _selectedMapIndex) return; _ = CommitEdits?.Invoke(); _selectedMapIndex = value; _selection = (0, 0, 0, 0); _selectedRow = 0; _selectedColumn = 0; Raise(); UpdateGraph(); } }
    public UnifiedMapCell? SelectedCell => Maps.Count == 4 ? SelectedMap.Cell(_selectedRow, _selectedColumn) : null;
    public bool CanEdit => !_host.IsBusy && (_host.Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.Demo) &&
        Maps.Count == 4 && _host.Basic.Draft is not null;
    public bool CanExport => CanEdit && _host.Mode == DesktopAccessMode.BoundBaseline &&
        _preview is not null && !_preview.Plan.IsNoOp && File.Exists(_host.RunnerPath);
    public bool IsBusy => _host.IsBusy;
    public string Status => _host.Mode switch
    {
        DesktopAccessMode.Empty => "Немає файла. Native / interactive acceptance: NotRun.",
        DesktopAccessMode.Demo => "Вигадані дані; не прошивка Honda. Publication заборонено.",
        DesktopAccessMode.RawOnly => "Unknown BIN — лише загальні дані; map editing недоступне.",
        DesktopAccessMode.BoundBaseline when Maps.Count != 4 => "Bound original, але M2e mapping неповний: " + Error,
        DesktopAccessMode.BoundBaseline => "Bound original — scoped editing. PcInspectionOnly / NotFlashReady.",
        DesktopAccessMode.VerifiedUnifiedDerived => "Verified M2e child — read-only; historical consistency, не fresh execution.",
        _ => "Неповний або інший lineage: M2e editing відмовлено."
    };
    public string BasicDraftNote => "Базові шість груп редагуються у вкладці «Базові налаштування»; це той самий draft для M2e export.";
    public string FillRaw { get => _fillRaw; set { _fillRaw = value; Raise(nameof(FillRaw)); } }
    public string ProbeRpm { get => _probeRpm; set { _probeRpm = value; Raise(nameof(ProbeRpm)); } }
    public string ProbeLoad { get => _probeLoad; set { _probeLoad = value; Raise(nameof(ProbeLoad)); } }
    public string ProbeFactor { get => _probeFactor; set { _probeFactor = value; Raise(nameof(ProbeFactor)); } }
    public MapDisplayMode DisplayMode { get => _displayMode; set { _displayMode = value; foreach (var map in Maps) map.DisplayMode = value; Raise(nameof(DisplayMode)); } }
    public IReadOnlyList<MapDisplayMode> DisplayModes { get; } = Enum.GetValues<MapDisplayMode>();
    public string PreviewText { get; private set; } = "Preview: NotRun; native: NotRun.";
    public string ProbeText { get; private set; } = "Модель lookup, не виконання ROM і не фізичні одиниці.";
    public string Error { get; private set; } = "";
    public string ProgressText { get; private set; } = "NotRun";
    public string ResultText { get; private set; } = "Fresh execution / publication / readback: NotRun. D2 interactive acceptance: NotRun.";
    public IReadOnlyList<BasicDiffRow> Diff { get; private set; } = [];
    public IReadOnlyList<UnifiedRequestedValueRow> RequestedRows { get; private set; } = [];
    public IReadOnlyList<UnifiedEvidenceSummary> Evidence { get; private set; } = [];
    public P28UnifiedCalibrationPlan? CurrentPlan => _preview?.Plan;
    public P28UnifiedCalibrationInspection? CurrentInspection => _host.BasicDocument?.UnifiedInspection;
    public UnifiedExportResult? LastExport { get; private set; }
    public BasicLookupPlot? MapPlot { get; private set; }
    public AsyncCommand SelectLocationCommand { get; }
    public AsyncCommand ImportCommand { get; }
    public AsyncCommand SaveSettingsCommand { get; }
    public AsyncCommand PreviewCommand { get; }
    public AsyncCommand SaveCommand { get; }
    public AsyncCommand OpenChildCommand { get; }
    public AsyncCommand ReuseCommand { get; }
    public RelayCommand PasteCommand { get; }
    public RelayCommand FillCommand { get; }
    public RelayCommand ResetCellsCommand { get; }
    public RelayCommand ResetMapCommand { get; }
    public RelayCommand UndoCommand { get; }
    public RelayCommand RedoCommand { get; }
    public RelayCommand ProbeCommand { get; }
    public Func<bool>? CommitEdits { get; set; }
    public event PropertyChangedEventHandler? PropertyChanged;
    private void Raise(string property = "") => PropertyChanged?.Invoke(this, new(property));
    public void Refresh()
    {
        Raise(); SelectLocationCommand.Refresh(); ImportCommand.Refresh(); SaveSettingsCommand.Refresh();
        PreviewCommand.Refresh(); SaveCommand.Refresh(); OpenChildCommand.Refresh(); ReuseCommand.Refresh();
        PasteCommand.Refresh(); FillCommand.Refresh(); ResetCellsCommand.Refresh(); ResetMapCommand.Refresh();
        UndoCommand.Refresh(); RedoCommand.Refresh(); ProbeCommand.Refresh();
    }
    public void Fail(string message) { Error = message; ProgressText = "Помилка / незавершено"; Refresh(); }
    internal void Invalidate()
    {
        _preview = null; _previewSettings = null; Diff = []; RequestedRows = []; Evidence = []; LastExport = null;
        PreviewText = "Preview застарів або відсутній. Native execution: NotRun.";
        ResultText = "Fresh execution / publication / readback: NotRun для поточного draft.";
        Error = ""; Refresh();
    }
    internal void ResetDocument(DesktopDocument document)
    {
        Invalidate(); _imported.Clear(); _undo.Clear(); _redo.Clear(); _lastState = null;
        Maps = []; _mapOriginal = null; _selectedMapIndex = 0;
        try
        {
            if (document.Mode == DesktopAccessMode.BoundBaseline)
            {
                P28FuelMapInspector.LayoutGuard(document.Image); P28IgnitionMapInspector.LayoutGuard(document.Image);
                _mapOriginal = document.Image;
            }
            else if (document.Mode == DesktopAccessMode.Demo) _mapOriginal = InventedMapImage();
            if (_mapOriginal is not null)
            {
                if (_host.Basic.Draft is null) throw new InvalidDataException("Шість basic-груп недоступні для цього original.");
                string[] ids = ["map_0", "map_1", "ignition_map_0", "ignition_map_1"];
                Maps = ids.Select(id => NewMap(id)).ToArray();
                DisplayMode = MapDisplayMode.Requested; UpdateGraph();
                _lastState = CaptureRaw();
            }
            if (document.Mode == DesktopAccessMode.VerifiedUnifiedDerived && document.UnifiedInspection is { } inspection)
            {
                ResultText = $"M2e child: historical consistency={inspection.Verification.IsValid}; FreshExecution={inspection.Verification.FreshExecution}. " +
                    "Legacy M2e D2Status=NotStarted; D2 delivery визначається поточною збіркою, interactive acceptance=NotRun.";
            }
        }
        catch (Exception e) { Maps = []; _mapOriginal = null; Error = "M2e map layout недоступний: " + e.Message; }
        Refresh();
    }
    private UnifiedDraftRawState CaptureRaw()
    {
        var basic = _host.Basic.CaptureRaw();
        var maps = Maps.Select(map => map.CaptureRaw()).ToArray();
        return new(JsonSerializer.Serialize(new { basic, maps }), basic, maps);
    }
    internal void RecordDraftChange()
    {
        if (_restoring || Maps.Count != 4 || _host.Basic.Draft is null) return;
        var next = CaptureRaw();
        if (_lastState is { } prior && prior.Signature != next.Signature)
        {
            _undo.Push(prior);
            if (_undo.Count > 100)
            {
                var newest = _undo.ToArray().Take(100).Reverse().ToArray();
                _undo.Clear(); foreach (var item in newest) _undo.Push(item);
            }
            _redo.Clear();
        }
        _lastState = next; Refresh();
    }
    private void RestoreDraft(UnifiedDraftRawState state)
    {
        _restoring = true;
        try
        {
            _host.Basic.RestoreRaw(state.Basic);
            var ids = new[] { "map_0", "map_1", "ignition_map_0", "ignition_map_1" };
            var maps = ids.Select(NewMap).ToArray();
            for (var i = 0; i < maps.Length; i++) maps[i].RestoreRaw(state.Maps[i]);
            Maps = maps; _lastState = state;
            _host.BasicDraftChanged(); UpdateGraph(); Refresh();
        }
        finally { _restoring = false; }
    }
    private void UndoDraft()
    {
        if (_undo.Count == 0) return;
        _redo.Push(CaptureRaw()); RestoreDraft(_undo.Pop());
    }
    private void RedoDraft()
    {
        if (_redo.Count == 0) return;
        _undo.Push(CaptureRaw()); RestoreDraft(_redo.Pop());
    }
    private static RomImage InventedMapImage()
    {
        var bytes = new byte[P28NativeChecksumArithmetic.RomSize];
        for (var i = 0; i < 10; i++) bytes[P28FuelMapContract.LoadAxisOrigin + i] = (byte)(i == 9 ? 0 : i * 25);
        for (var i = 0; i < 20; i++)
        {
            bytes[P28FuelMapContract.Map0RpmAxisOrigin + i] = (byte)(i == 19 ? 0 : i * 13);
            bytes[P28FuelMapContract.Map1RpmAxisOrigin + i] = (byte)(i == 19 ? 0 : i * 12);
        }
        foreach (var map in P28FuelMapContract.Maps)
        {
            for (var c = 0; c < 10; c++) bytes[P28FuelMapContract.MetadataOffset(map.Id, c)] = (byte)(2 + c);
            for (var r = 0; r < 20; r++) for (var c = 0; c < 10; c++)
                    bytes[P28FuelMapContract.CellOffset(map.Id, r, c)] = (byte)((r * 7 + c * 11 + (map.Id == "map_1" ? 31 : 0)) & 255);
        }
        foreach (var map in P28IgnitionMapContract.Maps)
            for (var r = 0; r < 20; r++) for (var c = 0; c < 10; c++)
                    bytes[P28IgnitionMapContract.CellOffset(map.Id, r, c)] = (byte)((r * 9 + c * 3 + (map.Id.EndsWith("_1", StringComparison.Ordinal) ? 41 : 0)) & 255);
        return RomImage.FromBytes(bytes);
    }
    private UnifiedMapDraft NewMap(string id)
    {
        UnifiedMapDraft? draft = null;
        bool Active() => Maps.Contains(draft);
        draft = new UnifiedMapDraft(id, _mapOriginal!, () => { if (Active()) { _host.BasicDraftChanged(); UpdateGraph(); Refresh(); } },
            () => !Active() || CanEdit);
        return draft;
    }
    private void Do(Action action)
    {
        try { _ = CommitEdits?.Invoke(); action(); Error = ""; Refresh(); }
        catch (Exception e) { Fail(e.Message); }
    }
    public void SelectRectangle(int top, int left, int bottom, int right)
    {
        if (Maps.Count != 4 || top < 0 || left < 0 || bottom >= 20 || right >= 10 || bottom < top || right < left) return;
        _selection = (top, left, bottom, right); _selectedRow = top; _selectedColumn = left;
        Raise(nameof(SelectedCell)); UpdateGraph();
    }
    public void RejectNonRectangularSelection()
    {
        _selection = (-1, -1, -1, -1);
        Fail("Виділіть суцільний прямокутний блок cells для bulk-операції.");
    }
    private P28UnifiedCalibrationSettings Snapshot()
    {
        if (CommitEdits?.Invoke() == false || _host.Basic.CommitEdits?.Invoke() == false)
            throw new ArgumentException("Активна cell/row не пройшла binding validation.");
        var basic = _host.Basic.Draft?.Snapshot() ?? throw new InvalidOperationException("Basic draft недоступний.");
        var fuel = new P28FuelMapExportSettings(Maps[0].Snapshot()?.Select(x => new P28FuelMapCellSetting(x.Row, x.Column, x.Value)).ToArray(),
            Maps[1].Snapshot()?.Select(x => new P28FuelMapCellSetting(x.Row, x.Column, x.Value)).ToArray());
        var ignition = new P28IgnitionMapExportSettings(Maps[2].Snapshot()?.Select(x => new P28IgnitionMapCellSetting(x.Row, x.Column, x.Value)).ToArray(),
            Maps[3].Snapshot()?.Select(x => new P28IgnitionMapCellSetting(x.Row, x.Column, x.Value)).ToArray());
        return P28UnifiedCalibrationSettings.Parse(new P28UnifiedCalibrationSettings(basic, fuel, ignition).ToJson(false));
    }
    private UnifiedCalibrationInput Capture(bool includeRunner = false) => UnifiedCalibrationInput.Capture(_host.BasicDocument!,
        _host.BasicLocationPath ?? throw new InvalidDataException("Reviewed compensation definition не обрано."),
        _host.BasicLocation ?? throw new InvalidDataException("Reviewed compensation definition не підтверджено."),
        includeRunner ? _host.RunnerPath : null, _imported.Keys);
    public Task SelectLocationAsync(string path)
    {
        if (_host.IsBusy || _host.Mode != DesktopAccessMode.BoundBaseline) return Task.CompletedTask;
        _host.ClearBasicLocation();
        return _host.RunUnifiedJobAsync(async (token, session, job) =>
        {
            var location = await Task.Run(() =>
            {
                var d = _host.BasicDocument!;
                var loaded = P28ChecksumPreservingEditor.LoadLocation(path);
                var availability = P28ChecksumPreservingEditor.GetAvailability(d.Image, d.Profile!, d.Binding!, true, loaded);
                if (!availability.IsAvailable) throw new InvalidDataException(availability.Reason);
                _ = UnifiedCalibrationInput.Capture(d, Path.GetFullPath(path), loaded);
                return loaded;
            }, token);
            if (_host.BasicCurrent(session, job)) _host.SetBasicLocation(location, Path.GetFullPath(path));
        });
    }
    public Task ImportAsync(string path)
    {
        if (!CanEdit) return Task.CompletedTask;
        return _host.RunUnifiedJobAsync(async (token, session, job) =>
        {
            var parsed = await Task.Run(() =>
            {
                var bytes = UnifiedCalibrationInput.ReadSettings(path);
                var settings = P28UnifiedCalibrationSettings.Parse(new UTF8Encoding(false, true).GetString(bytes).TrimStart('\uFEFF'));
                if (_host.Mode == DesktopAccessMode.BoundBaseline)
                    _ = P28BasicCalibrationEditor.InspectFields(_host.BasicDocument!.Image, _host.BasicDocument.Profile!, _host.BasicDocument.Binding!, true, settings.Basic);
                if (!bytes.AsSpan().SequenceEqual(UnifiedCalibrationInput.ReadSettings(path))) throw new InvalidDataException("Settings змінилися під час імпорту.");
                return (bytes, settings);
            }, token);
            if (!_host.BasicCurrent(session, job) || token.IsCancellationRequested) return;
            var replacement = new[] { "map_0", "map_1", "ignition_map_0", "ignition_map_1" }
                .Select(NewMap).ToArray();
            replacement[0].Apply(parsed.settings.Fuel.Map0?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray());
            replacement[1].Apply(parsed.settings.Fuel.Map1?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray());
            replacement[2].Apply(parsed.settings.Ignition.IgnitionMap0?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray());
            replacement[3].Apply(parsed.settings.Ignition.IgnitionMap1?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray());
            _host.Basic.ApplyUnifiedBasicSettings(parsed.settings.Basic, notify: false);
            Maps = replacement; _selectedMapIndex = 0; _imported[Path.GetFullPath(path)] = parsed.bytes;
            _host.BasicDraftChanged(); UpdateGraph(); Refresh();
        });
    }
    public Task SaveSettingsAsync(string path)
    {
        if (!CanEdit) return Task.CompletedTask;
        string json;
        try { json = Snapshot().ToJson(); } catch (Exception e) { Fail(e.Message); return Task.CompletedTask; }
        return _host.RunUnifiedJobAsync(async (token, session, job) =>
        {
            await Task.Run(() =>
            {
                var sources = (_host.BasicDocument?.InputPaths ?? []).Concat(_imported.Keys)
                    .Concat(new[] { _host.BasicLocationPath, _host.RunnerPath }.OfType<string>());
                BasicCalibrationInput.ProtectDestinations([path], sources); token.ThrowIfCancellationRequested();
                AtomicFile.WriteAllText(path, json);
            }, token);
            if (_host.BasicCurrent(session, job)) { ResultText = "M2e settings збережено: " + path + ". Не firmware/evidence."; Refresh(); }
        });
    }
    public Task PreviewAsync()
    {
        if (!CanEdit) return Task.CompletedTask;
        P28UnifiedCalibrationSettings settings;
        try { settings = Snapshot(); } catch (Exception e) { Invalidate(); Fail(e.Message); return Task.CompletedTask; }
        Invalidate();
        if (_host.Mode == DesktopAccessMode.Demo)
        {
            PreviewText = "Вигадані дані; не прошивка Honda. Model-only probe доступний; Core publication/native Pass недоступні.";
            Refresh(); return Task.CompletedTask;
        }
        return _host.RunUnifiedJobAsync(async (token, session, job) =>
        {
            ProgressText = "Combined preview/domain audit; native NotRun"; Refresh();
            var input = await Task.Run(() => Capture(), token);
            var result = await _operations.PreviewAsync(input, settings, token);
            if (!_host.BasicCurrent(session, job) || token.IsCancellationRequested) return;
            await Task.Run(input.Recheck, token);
            if (!_host.BasicCurrent(session, job) || token.IsCancellationRequested) return;
            _preview = result; _previewSettings = settings.ToJson(false);
            Present(result.Plan); ProgressText = "Combined preview готовий; native NotRun"; Refresh();
        });
    }
    private void Present(P28UnifiedCalibrationPlan plan)
    {
        var lines = plan.Groups.Select(g => $"{g.Family}.{g.Id}: requested={g.Requested}; byteChanged={g.ByteChanged}; values={g.RequestedValueCount}/{g.ChangedValueCount}").ToList();
        lines.Add($"Map cells requested/changed={plan.RequestedMapCellCount}/{plan.ChangedMapCellCount}; diff={plan.ExpectedDiff.Count}; no-op={plan.IsNoOp}.");
        lines.Add($"A/B/C residues={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; compensation 0x{plan.Compensation.Offset:X4}: {plan.Compensation.OldByte}→{plan.Compensation.NewByte}.");
        foreach (var group in plan.FuelMaps) lines.Add($"fuel.{group.MapId}: arithmetic model changed pairs={group.DomainAudit.ChangedResults}; native NotRun");
        foreach (var group in plan.IgnitionMaps) lines.Add($"ignition.{group.MapId}: arithmetic model changed pairs={group.DomainAudit.ChangedResults}; native NotRun");
        lines.Add("Exact full diff нижче. Arithmetic pass ≠ native execution pass. PcInspectionOnly / NotFlashReady.");
        PreviewText = string.Join("\n", lines);
        Diff = plan.ExpectedDiff.Select(d => new BasicDiffRow($"0x{d.Offset:X4}", $"{d.OldByte:X2}", $"{d.NewByte:X2}", "Core complete diff")).ToArray();
        var values = new List<UnifiedRequestedValueRow>();
        foreach (var group in plan.BasicGroups.Where(group => group.Requested))
        {
            if (group.Vtec?.Slot is { } slot)
            {
                var index = slot.Offset - P28ThresholdLogic.BlockOffset;
                values.Add(new("basic.vtec", slot.Id, $"0x{slot.Offset:X4}", group.Vtec.OriginalBytes[index], group.Vtec.NewBytes[index]));
            }
            if (group.Limiter is { } limiter)
            {
                values.AddRange(limiter.FixedOperands.Select(word => new UnifiedRequestedValueRow("basic." + group.Id, word.FieldId,
                    $"0x{word.Offset:X4}", word.OriginalWord, word.NewWord)));
                values.AddRange(limiter.AdaptiveWords.Select(word => new UnifiedRequestedValueRow("basic." + group.Id, word.FieldId,
                    $"0x{word.Offset:X4}", word.OldWord, word.NewWord)));
            }
            if (group.Idle is { } idle)
                values.AddRange(idle.Cells.Select(cell => new UnifiedRequestedValueRow("basic." + group.Id, cell.FieldId,
                    $"0x{cell.ValueOffset:X4}", cell.OldValue, cell.NewValue)));
        }
        values.AddRange(plan.FuelMaps.SelectMany(map => map.Cells.Select(cell => new UnifiedRequestedValueRow("fuel." + map.MapId,
            $"r{cell.Row}/c{cell.Column}", $"0x{cell.Offset:X4}", cell.OldRawValue, cell.NewRawValue))));
        values.AddRange(plan.IgnitionMaps.SelectMany(map => map.Cells.Select(cell => new UnifiedRequestedValueRow("ignition." + map.MapId,
            $"r{cell.Row}/c{cell.Column}", $"0x{cell.Offset:X4}", cell.OldRawValue, cell.NewRawValue))));
        RequestedRows = values.AsReadOnly();
    }
    public Task SaveAsync(DesktopSavePaths paths)
    {
        if (!CanExport) { Fail("Export заблоковано: потрібні bound original, reviewed definition, current non-no-op preview і runner; demo/child заборонені."); return Task.CompletedTask; }
        try
        {
            if (Snapshot().ToJson(false) != _previewSettings) throw new InvalidDataException("Draft змінився: повторіть combined preview.");
            var summary = string.Join("\n", _preview!.Plan.Groups.Where(g => g.Requested).Select(g => $"{g.Family}.{g.Id}: {g.RequestedValueCount} requested; {g.ChangedValueCount} changed"));
            if (!_dialogs.Confirm("Перевірити та зберегти всі вибрані зміни — PC-only",
                summary + $"\nBIN: {paths.OutputPath}\nPlan: {paths.PlanPath}\nReceipt: {paths.ReportPath}\nЦе не firmware для ECU. Native validation буде fresh; publication не power-loss atomic.")) return Task.CompletedTask;
        }
        catch (Exception e) { Invalidate(); Fail(e.Message); return Task.CompletedTask; }
        var preview = _preview!; var runner = _host.RunnerPath;
        return _host.RunUnifiedJobAsync(async (token, session, job) =>
        {
            ResultText = "Fresh native execution виконується; publication/readback NotRun."; Evidence = [];
            var progress = new Progress<P28UnifiedCalibrationStage>(stage =>
            {
                if (!_host.BasicCurrent(session, job)) return;
                ProgressText = stage switch
                {
                    P28UnifiedCalibrationStage.VtecLimiterIdle => "VTEC / limiter / idle",
                    P28UnifiedCalibrationStage.Fuel => "Fuel",
                    P28UnifiedCalibrationStage.Ignition => "Ignition",
                    P28UnifiedCalibrationStage.Checksum => "Checksum A/B/C",
                    P28UnifiedCalibrationStage.EvidenceVerification => "Evidence verification",
                    P28UnifiedCalibrationStage.Publication => "Publication — очікуйте readback/rollback; пізній Cancel не скасовує завершений успіх",
                    _ => "Independent readback"
                }; Refresh();
            });
            var input = await Task.Run(() => Capture(true), token);
            await Task.Run(() => BasicCalibrationInput.ProtectDestinations([paths.OutputPath, paths.PlanPath, paths.ReportPath], input.Paths), token);
            var result = await _operations.ExportAsync(input, preview, runner, paths, progress, token);
            if (result.Paths != paths || result.PlanDigest != preview.Plan.Digest()) throw new InvalidDataException("Service result має інший plan/job.");
            var d = input.Document;
            var child = await Task.Run(() => UnifiedCalibrationInput.Inspect(paths.OutputPath, d.Image.SourcePath!, d.Profile!.SourcePath!,
                d.BindingPath!, _host.BasicLocationPath!, paths.PlanPath, paths.ReportPath));
            if (child.UnifiedPlan!.Digest() != preview.Plan.Digest()) throw new InvalidDataException("Independent child reopen має інший plan.");
            if (!_host.BasicCurrent(session, job)) return;
            _host.AttachBasicDocument(child); Evidence = result.Fresh; LastExport = result;
            ResultText = $"Fresh native execution: strict Pass цього job. Publication: success. Independent readback/reopen: success.\n{paths.OutputPath}\n{paths.PlanPath}\n{paths.ReportPath}\nValidation {result.ValidationTime}; publication/readback {result.PublicationAndReadbackTime}; peak working set {result.PeakWorkingSet:N0} bytes.\nHistorical FreshExecution=NotRun — це не стирає fresh result. D2 interactive acceptance=NotRun. NotFlashReady.";
            ProgressText = "Завершено"; Refresh();
        });
    }
    public Task OpenChildAsync(string child, string original, string profile, string binding, string location, string plan, string receipt) =>
        _host.RunUnifiedJobAsync(async (token, session, job) =>
        {
            var document = await Task.Run(() => UnifiedCalibrationInput.Inspect(child, original, profile, binding, location, plan, receipt), token);
            if (_host.BasicCurrent(session, job) && !token.IsCancellationRequested) _host.AttachBasicDocument(document);
        });
    public Task ReuseOriginalAsync()
    {
        if (_host.IsBusy || _host.Mode != DesktopAccessMode.VerifiedUnifiedDerived) return Task.CompletedTask;
        var d = _host.BasicDocument!; var settings = d.UnifiedInspection!.RequestedSettings;
        return _host.RunUnifiedJobAsync(async (token, session, job) =>
        {
            var location = await Task.Run(() => P28ChecksumPreservingEditor.LoadLocation(d.CompensationDefinitionPath!), token);
            if (!_host.BasicCurrent(session, job)) return;
            _host.AttachBasicDocument(d with
            {
                Mode = DesktopAccessMode.BoundBaseline,
                Image = d.Parent!,
                Parent = null,
                UnifiedInspection = null,
                UnifiedPlan = null
            });
            _host.SetBasicLocation(location, d.CompensationDefinitionPath!);
            _host.Basic.ApplyUnifiedBasicSettings(settings.Basic, notify: false);
            Maps[0].Apply(settings.Fuel.Map0?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray(), notify: false);
            Maps[1].Apply(settings.Fuel.Map1?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray(), notify: false);
            Maps[2].Apply(settings.Ignition.IgnitionMap0?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray(), notify: false);
            Maps[3].Apply(settings.Ignition.IgnitionMap1?.Select(x => (x.Row, x.Column, x.RawValue)).ToArray(), notify: false);
            _host.BasicDraftChanged(); UpdateGraph();
            Refresh();
        });
    }
    private async Task SaveFromDialogsAsync()
    {
        var bin = _dialogs.SaveFile("Новий M2e PC-only BIN", BinFilter, "unified-copy.bin"); if (bin is null) return;
        var plan = _dialogs.SaveFile("Новий M2e saved plan", JsonFilter, "unified-copy.plan.json"); if (plan is null) return;
        var receipt = _dialogs.SaveFile("Новий M2e receipt", JsonFilter, "unified-copy.receipt.json"); if (receipt is null) return;
        await SaveAsync(new(bin, plan, receipt));
    }
    private async Task OpenChildFromDialogsAsync()
    {
        var child = _dialogs.OpenFile("M2e child BIN", BinFilter); if (child is null) return;
        var original = _dialogs.OpenFile("Exact original BIN", BinFilter); if (original is null) return;
        var profile = _dialogs.OpenFile("Original profile", JsonFilter); if (profile is null) return;
        var binding = _dialogs.OpenFile("Original binding", JsonFilter); if (binding is null) return;
        var location = _dialogs.OpenFile("Reviewed compensation definition", JsonFilter); if (location is null) return;
        var plan = _dialogs.OpenFile("M2e saved plan", JsonFilter); if (plan is null) return;
        var receipt = _dialogs.OpenFile("M2e receipt", JsonFilter); if (receipt is null) return;
        if (_dialogs.Confirm("Відкрити M2e child?", "Historical consistency над exact original; child не стає новим original."))
            await OpenChildAsync(child, original, profile, binding, location, plan, receipt);
    }
    private void UpdateProbe()
    {
        if (_mapOriginal is null || Maps.Count != 4) return;
        var rpm = UnifiedMapCell.Parse(ProbeRpm); var load = UnifiedMapCell.Parse(ProbeLoad);
        var factor = UnifiedMapCell.Parse(ProbeFactor);
        var map = SelectedMap; var original = _mapOriginal.ToArray(); var requested = (byte[])original.Clone();
        if (map.Included) foreach (var cell in map.Cells) if (cell.Explicit) requested[cell.Offset] = (byte)cell.Requested;
        var excluded = !map.Included ? " Ці зміни не включені у збереження; effective requested = original." : "";
        if (map.IsFuel)
        {
            var a = P28FuelMapModel.ProjectNumeric(original, map.Id, rpm, load);
            var b = P28FuelMapModel.ProjectNumeric(requested, map.Id, rpm, load);
            ProbeText = $"Модель lookup, не виконання ROM і не фізичні одиниці.{excluded}\n" +
                $"{map.Id} raw RPM={rpm}, load={load}; interval row/col={b.RpmIndex}/{b.LoadIndex}; Q16={b.RpmFraction}/{b.LoadFraction}; corners={b.TopLeft},{b.TopRight},{b.BottomLeft},{b.BottomRight}; multipliers={b.MultiplierLeft},{b.MultiplierRight}; scaled corners={b.ScaledTopLeft},{b.ScaledTopRight},{b.ScaledBottomLeft},{b.ScaledBottomRight}; column intermediates={b.TopColumnResult}/{b.BottomColumnResult}; model original/requested={a.LookupResult}/{b.LookupResult}. Raw-cell plot is not final fuel surface. Native selector/cache history NotRun.";
        }
        else
        {
            var a = P28IgnitionMapModel.ProjectNumeric(original, map.Id, rpm, load);
            var b = P28IgnitionMapModel.ProjectNumeric(requested, map.Id, rpm, load);
            var consumer = P28IgnitionMapModel.Consume(b.LookupResult, factor);
            ProbeText = $"Модель lookup, не виконання ROM і не фізичні одиниці.{excluded}\n" +
                $"{map.Id} raw RPM={rpm}, load={load}; interval row/col={b.RpmIndex}/{b.LoadIndex}; Q16={b.RpmFraction}/{b.LoadFraction}; corners={b.TopLeft},{b.TopRight},{b.BottomLeft},{b.BottomRight}; column intermediates={b.TopColumnResult}/{b.BottomColumnResult}; model original/requested={a.LookupResult}/{b.LookupResult}; factor={factor}; consumer output={consumer.Output}; factor0 bypass, nonzero highByte(lookup×factor). Raw cell is not a confirmed physical angle. Native selector/cache history NotRun.";
        }
        Refresh();
    }
    private void UpdateGraph()
    {
        if (Maps.Count != 4) { MapPlot = null; return; }
        var map = SelectedMap;
        var row = Math.Clamp(_selectedRow, 0, 19);
        var cells = Enumerable.Range(0, 10).Select(col => map.Cell(row, col)).ToArray();
        if (cells.Any(cell => !UnifiedMapCell.TryParse(cell.Text, out _)))
        {
            MapPlot = null; Raise(nameof(MapPlot)); return;
        }
        MapPlot = new($"{map.Id} row {row} — raw cells, не фінальна fuel surface/physical angle",
            cells.Select(cell => (int)cell.Original).ToArray(),
            cells.Select(cell => cell.Requested).ToArray(),
            Enumerable.Range(0, 10).ToArray());
        Raise(nameof(MapPlot));
    }
}
