using System.ComponentModel;
using System.IO;
using System.Text;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;

namespace HondaEcu.Desktop.ViewModels;

public sealed record BasicDiffRow(string Offset, string Old, string New, string Purpose);
public sealed record BasicLookupPlot(string Title, IReadOnlyList<int> Original, IReadOnlyList<int> Requested, IReadOnlyList<int> Axes);

public sealed class BasicCalibrationViewModel : INotifyPropertyChanged
{
    private readonly MainViewModel _host;
    private readonly IDialogService _dialogs;
    private readonly IBasicCalibrationOperations _operations;
    private readonly Dictionary<string, byte[]> _imported = new(StringComparer.OrdinalIgnoreCase);
    private IReadOnlyList<P28BasicCalibrationGroup>? _originalFields;
    private P28BasicCalibrationPreview? _preview;
    private string? _previewSettings;
    private const string JsonFilter = "JSON (*.json)|*.json";
    private const string BinFilter = "BIN (*.bin)|*.bin";
    public BasicCalibrationViewModel(MainViewModel host, IDialogService dialogs, IBasicCalibrationOperations operations)
    {
        _host = host; _dialogs = dialogs; _operations = operations;
        SelectLocationCommand = new(async () => { var p = dialogs.OpenFile("Reviewed compensation definition", JsonFilter); if (p is not null) await SelectLocationAsync(p); }, () => !host.IsBusy && host.Mode == DesktopAccessMode.BoundBaseline);
        PreviewCommand = new(PreviewAsync, () => CanEdit);
        SaveCommand = new(SaveFromDialogsAsync, () => CanExport);
        ImportCommand = new(async () => { var p = dialogs.OpenFile("Імпорт M1t settings", JsonFilter); if (p is not null) await ImportAsync(p); }, () => CanEdit);
        ExportSettingsCommand = new(async () => { var p = dialogs.SaveFile("Новий M1t settings", JsonFilter, "basic-settings.json"); if (p is not null) await SaveSettingsAsync(p); }, () => CanEdit);
        ResetCommand = new(() => { if (CanEdit) { Draft = NewDraft(); _host.BasicDraftChanged(); Refresh(); } }, () => CanEdit);
        OpenChildCommand = new(OpenChildFromDialogsAsync, () => !host.IsBusy);
        ReuseCommand = new(ReuseOriginalAsync, () => !host.IsBusy && host.Mode == DesktopAccessMode.VerifiedBasicDerived);
    }
    public BasicCalibrationDraft? Draft { get; private set; }
    public bool CanEdit => !_host.IsBusy && Draft is not null && _host.Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.Demo;
    public bool CanExport => CanEdit && _host.Mode == DesktopAccessMode.BoundBaseline && _preview is not null && !_preview.Plan.IsNoOp && File.Exists(_host.RunnerPath);
    public bool IsBusy => _host.IsBusy;
    public string Prerequisites => $"{_host.FileName}\n{_host.ModeLabel}\nProfile: {_host.ProfileName}. Binding: {_host.BindingStatus}\n" +
        $"Compensation: {_host.CompensationStatus}\nRunner: {_host.RunnerStatus}\n" +
        (Draft is null ? "M1t поля недоступні: потрібні exact original admission та сумісний mapping. " : "") +
        "PcInspectionOnly / NotFlashReady. Physical RPM unavailable. GUI acceptance / hardware / full boot: NotRun.";
    public string Error { get; private set; } = "";
    public string PreviewText { get; private set; } = "Preview ще не створено. Native execution: NotRun.";
    public string ProgressText { get; private set; } = "NotRun";
    public string ResultText { get; private set; } = "Fresh execution, publication, readback: NotRun.";
    public IReadOnlyList<BasicDiffRow> Diff { get; private set; } = [];
    public IReadOnlyList<P28PredicateRow> VtecPlot { get; private set; } = [];
    public IReadOnlyList<BasicLookupPlot> IdlePlots { get; private set; } = [];
    public IReadOnlyList<BasicEvidenceSummary> Evidence { get; private set; } = [];
    public IReadOnlyList<string> Witnesses { get; private set; } = [];
    public BasicExportResult? LastExport { get; private set; }
    public P28BasicCalibrationPlan? CurrentPlan => _preview?.Plan;
    public AsyncCommand SelectLocationCommand { get; }
    public AsyncCommand PreviewCommand { get; }
    public AsyncCommand SaveCommand { get; }
    public AsyncCommand ImportCommand { get; }
    public AsyncCommand ExportSettingsCommand { get; }
    public RelayCommand ResetCommand { get; }
    public AsyncCommand OpenChildCommand { get; }
    public AsyncCommand ReuseCommand { get; }
    // The WPF view supplies only edit commit/validation; headless callers validate the same text snapshot.
    public Func<bool>? CommitEdits { get; set; }
    public event PropertyChangedEventHandler? PropertyChanged;
    public void Refresh()
    {
        PropertyChanged?.Invoke(this, new(""));
        SelectLocationCommand.Refresh(); PreviewCommand.Refresh(); SaveCommand.Refresh(); ImportCommand.Refresh();
        ExportSettingsCommand.Refresh(); ResetCommand.Refresh(); OpenChildCommand.Refresh(); ReuseCommand.Refresh();
        if (Draft is not null) foreach (var g in Draft.Groups) g.ResetCommand.Refresh();
    }
    public void Fail(string message) { Error = message; ProgressText = "Помилка / незавершено"; Refresh(); }
    internal void Invalidate()
    {
        _preview = null; _previewSettings = null; Diff = []; VtecPlot = []; IdlePlots = []; Evidence = []; Witnesses = []; LastExport = null;
        PreviewText = "Preview відсутній або застарів: побудуйте для поточного draft. Native execution: NotRun.";
        ResultText = "Попередній результат не застосовується до поточного стану. Fresh execution: NotRun."; Error = "";
    }
    internal void ResetDocument(DesktopDocument document)
    {
        Invalidate(); _imported.Clear(); _originalFields = null; Draft = null;
        try
        {
            if (document.Mode == DesktopAccessMode.BoundBaseline)
                _originalFields = P28BasicCalibrationEditor.InspectFields(document.Image, document.Profile!, document.Binding!, true);
            if (document.Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.Demo) Draft = NewDraft();
            if (document.BasicInspection is { } inspection && document.Mode == DesktopAccessMode.VerifiedBasicDerived)
            {
                ShowPlan(document.BasicPlan!);
                ResultText = $"Read-only M1t child. Historical consistency: {inspection.Verification.IsValid}.\nFresh execution: {inspection.Verification.FreshExecution}. Не автентифікація минулого запуску.";
            }
        }
        catch (Exception e) { Error = "M1t поля недоступні: " + e.Message; }
    }
    private BasicCalibrationDraft NewDraft()
    {
        BasicCalibrationDraft? draft = null;
        bool Editable() => !ReferenceEquals(Draft, draft) || CanEdit;
        void Changed() { if (ReferenceEquals(Draft, draft)) _host.BasicDraftChanged(); }
        draft = _host.Mode == DesktopAccessMode.Demo ? BasicCalibrationDraft.Demo(Changed, Editable) :
            BasicCalibrationDraft.FromFields(_originalFields ?? throw new InvalidOperationException("Поля original недоступні."), Changed, Editable);
        return draft;
    }
    private P28BasicCalibrationSettings Snapshot()
    {
        if (CommitEdits?.Invoke() == false) throw new ArgumentException("Активна cell/row не пройшла validation; snapshot не створено.");
        return Draft?.Snapshot() ?? throw new InvalidOperationException("Немає draft над original.");
    }
    public Task SelectLocationAsync(string path)
    {
        if (_host.IsBusy || _host.Mode != DesktopAccessMode.BoundBaseline) return Task.CompletedTask;
        _host.ClearBasicLocation();
        return _host.RunBasicJobAsync(async (token, session, job) =>
        {
            var d = _host.BasicDocument!;
            var location = await Task.Run(() =>
            {
                var l = P28ChecksumPreservingEditor.LoadLocation(path);
                var a = P28ChecksumPreservingEditor.GetAvailability(d.Image, d.Profile!, d.Binding!, true, l);
                if (!a.IsAvailable) throw new InvalidDataException(a.Reason);
                _ = BasicCalibrationInput.Capture(d, Path.GetFullPath(path), l); return l;
            }, token);
            if (_host.BasicCurrent(session, job)) _host.SetBasicLocation(location, Path.GetFullPath(path));
        });
    }
    private BasicCalibrationInput Capture(bool runner = false) => BasicCalibrationInput.Capture(_host.BasicDocument!,
        _host.BasicLocationPath ?? throw new InvalidDataException("Reviewed compensation definition не обрано."),
        _host.BasicLocation ?? throw new InvalidDataException("Reviewed compensation definition не підтверджено."),
        runner ? _host.RunnerPath : null, _imported);
    public Task PreviewAsync()
    {
        if (!CanEdit) return Task.CompletedTask;
        P28BasicCalibrationSettings settings;
        try { settings = Snapshot(); } catch (Exception e) { Invalidate(); Fail(e.Message); return Task.CompletedTask; }
        Invalidate();
        return _host.RunBasicJobAsync(async (token, session, job) =>
        {
            ProgressText = "Побудова плану та arithmetic-domain checks; native NotRun"; Refresh();
            if (_host.Mode == DesktopAccessMode.Demo)
            {
                var graphs = await Task.Run(() => DemoGraphs(settings), token);
                if (!_host.BasicCurrent(session, job)) return;
                PreviewText = "Синтетична демонстрація — Не прошивка Honda. Навчальний preview, без BIN/compensation authority; native NotRun.\n" +
                    string.Join("\n", Draft!.Groups.Select(g => $"{g.Id}: requested={g.Included}; " + string.Join("; ", g.Fields.Select(f => $"{f.Id}: {f.Original} → {(g.Included ? f.Number() : f.Original)}"))));
                IdlePlots = graphs; ShowVtec(settings); ProgressText = "Навчальна lookup-модель, не виконання"; Refresh(); return;
            }
            var input = await Task.Run(() => Capture(), token);
            var preview = await _operations.PreviewAsync(input, settings, token);
            // An injected service-returned preview is not authority for a different request.
            var checkedPreview = await Task.Run(() =>
            {
                input.Recheck(); var d = input.Document;
                var expected = P28BasicCalibrationEditor.Preview(d.Image, d.Profile!, d.Binding!, true, input.Location, settings);
                if (expected.Plan.ToJson(false) != preview.Plan.ToJson(false)) throw new InvalidDataException("Service повернув інший preview.");
                return expected;
            }, token);
            if (!_host.BasicCurrent(session, job) || token.IsCancellationRequested) return;
            _preview = checkedPreview; _previewSettings = settings.ToJson(); ShowPlan(checkedPreview.Plan); ShowVtec(settings);
            ProgressText = "Preview готовий; усі native suites ще NotRun"; Refresh();
        });
    }
    public Task ImportAsync(string path)
    {
        if (!CanEdit) return Task.CompletedTask;
        return _host.RunBasicJobAsync(async (token, session, job) =>
        {
            var result = await Task.Run(() =>
            {
                var bytes = BasicCalibrationInput.ReadBounded(path, 4096);
                var settings = P28BasicCalibrationSettings.Parse(new UTF8Encoding(false, true).GetString(bytes).TrimStart('\uFEFF'));
                if (_host.Mode == DesktopAccessMode.BoundBaseline)
                { var d = _host.BasicDocument!; _ = P28BasicCalibrationEditor.InspectFields(d.Image, d.Profile!, d.Binding!, true, settings); }
                else _ = DemoGraphs(settings);
                if (!bytes.AsSpan().SequenceEqual(BasicCalibrationInput.ReadBounded(path, 4096))) throw new InvalidDataException("Settings змінився під час імпорту.");
                return (bytes, settings);
            }, token);
            if (!_host.BasicCurrent(session, job) || token.IsCancellationRequested) return;
            var replacement = NewDraft(); replacement.Apply(result.settings);
            Draft = replacement; _imported[Path.GetFullPath(path)] = result.bytes; _host.BasicDraftChanged(); Refresh();
        });
    }
    public Task SaveSettingsAsync(string path)
    {
        if (!CanEdit) return Task.CompletedTask;
        string json;
        try { json = Snapshot().ToJson(); } catch (Exception e) { Fail(e.Message); return Task.CompletedTask; }
        return _host.RunBasicJobAsync(async (token, session, job) =>
        {
            await Task.Run(() =>
            {
                var sources = (_host.BasicDocument?.InputPaths ?? []).Concat(_imported.Keys)
                    .Concat(new[] { _host.BasicLocationPath, _host.RunnerPath }.OfType<string>());
                BasicCalibrationInput.ProtectDestinations([path], sources); token.ThrowIfCancellationRequested(); AtomicFile.WriteAllText(path, json);
            }, token);
            if (_host.BasicCurrent(session, job)) { ResultText = "Settings збережено: " + path + ". Це не firmware або execution evidence."; Refresh(); }
        });
    }
    public Task SaveAsync(DesktopSavePaths paths)
    {
        if (!CanExport) { Fail("Export заблоковано: потрібні exact original, location, актуальний non-no-op preview та сумісний локальний runner. Demo/child не експортуються."); return Task.CompletedTask; }
        try
        {
            if (Snapshot().ToJson() != _previewSettings) throw new InvalidDataException("Draft змінився: повторіть preview.");
            if (!_dialogs.Confirm("Перевірити та зберегти PC-only копію?", PreviewText + $"\nBIN: {paths.OutputPath}\nPlan: {paths.PlanPath}\nReceipt: {paths.ReportPath}\nНе для запису в ECU. Група не є power-loss atomic.")) return Task.CompletedTask;
        }
        catch (Exception e) { Invalidate(); Fail(e.Message); return Task.CompletedTask; }
        var preview = _preview!; var runner = _host.RunnerPath;
        return _host.RunBasicJobAsync(async (token, session, job) =>
        {
            Evidence = []; LastExport = null; ResultText = "Fresh validation виконується; publication/readback: NotRun.";
            var progress = new Progress<P28BasicCalibrationStage>(stage =>
            {
                if (!_host.BasicCurrent(session, job) || !_host.IsBusy) return;
                ProgressText = stage switch
                {
                    P28BasicCalibrationStage.VtecPrefix => "VTEC threshold prefix",
                    P28BasicCalibrationStage.LimiterAdaptive => "Limiter / adaptive",
                    P28BasicCalibrationStage.Idle => "Idle source / target / error",
                    P28BasicCalibrationStage.Checksum => "Native checksum A/B/C",
                    P28BasicCalibrationStage.EvidenceVerification => "Перевірка повноти observations / witnesses",
                    P28BasicCalibrationStage.Publication => "Збереження нових файлів; writer завершує publication contract",
                    _ => "Незалежне повторне читання BIN / plan / receipt"
                }; Refresh();
            });
            var input = await Task.Run(() => Capture(true), token);
            await Task.Run(() => BasicCalibrationInput.ProtectDestinations([paths.OutputPath, paths.PlanPath, paths.ReportPath], input.Paths), token);
            var result = await _operations.ExportAsync(input, preview, runner, paths, progress, token);
            if (result.Paths != paths || result.Readback.PlanDigest != preview.Plan.Digest()) throw new InvalidDataException("Live service result належить іншому job/plan.");
            // Trust only the production Core inspector on the actually saved tuple, not a mocked success.
            var d = input.Document;
            var child = await Task.Run(() => BasicCalibrationService.Inspect(paths.OutputPath, d.Image.SourcePath!, d.Profile!.SourcePath!,
                d.BindingPath!, _host.BasicLocationPath!, paths.PlanPath, paths.ReportPath));
            if (child.BasicPlan!.ToJson(false) != preview.Plan.ToJson(false)) throw new InvalidDataException("Published tuple не відповідає підтвердженому preview.");
            if (!_host.BasicCurrent(session, job)) return;
            _host.AttachBasicDocument(child);
            LastExport = result; Evidence = result.FreshExecution; Witnesses = result.Witnesses;
            ResultText = $"Fresh validation цього job: strict Pass. Publication: success. Independent readback: success.\n{paths.OutputPath}\n{paths.PlanPath}\n{paths.ReportPath}\n" +
                "Окрема historical verification не стирає fresh результат цього job. VtecFullChain/P1, joint ECU, hardware/full boot: NotRun. NotFlashReady.";
            ProgressText = "Завершено"; Refresh();
        });
    }
    public Task OpenChildAsync(string child, string original, string profile, string binding, string location, string plan, string receipt) =>
        _host.RunBasicJobAsync(async (token, session, job) =>
        {
            var document = await Task.Run(() => BasicCalibrationService.Inspect(child, original, profile, binding, location, plan, receipt), token);
            if (_host.BasicCurrent(session, job) && !token.IsCancellationRequested) _host.AttachBasicDocument(document);
        });
    public Task ReuseOriginalAsync()
    {
        if (_host.IsBusy || _host.Mode != DesktopAccessMode.VerifiedBasicDerived) return Task.CompletedTask;
        var d = _host.BasicDocument!; var settings = P28BasicCalibrationEditor.GetSettings(d.BasicPlan!);
        return _host.RunBasicJobAsync(async (token, session, job) =>
        {
            var location = await Task.Run(() => P28ChecksumPreservingEditor.LoadLocation(d.CompensationDefinitionPath!), token);
            if (!_host.BasicCurrent(session, job)) return;
            _host.AttachBasicDocument(d with { Mode = DesktopAccessMode.BoundBaseline, Image = d.Parent!, Parent = null, BasicInspection = null });
            _host.SetBasicLocation(location, d.CompensationDefinitionPath!);
            var replacement = NewDraft(); replacement.Apply(settings); Draft = replacement; Refresh();
        });
    }
    private async Task SaveFromDialogsAsync()
    {
        var b = _dialogs.SaveFile("Новий M1t PC-only BIN", BinFilter, "basic-copy.bin"); if (b is null) return;
        var p = _dialogs.SaveFile("Новий M1t saved plan", JsonFilter, "basic-copy.plan.json"); if (p is null) return;
        var r = _dialogs.SaveFile("Новий M1t receipt", JsonFilter, "basic-copy.receipt.json"); if (r is null) return;
        await SaveAsync(new(b, p, r));
    }
    private async Task OpenChildFromDialogsAsync()
    {
        var c = _dialogs.OpenFile("M1t child BIN", BinFilter); if (c is null) return;
        var o = _dialogs.OpenFile("Exact original BIN", BinFilter); if (o is null) return;
        var p = _dialogs.OpenFile("Original profile", JsonFilter); if (p is null) return;
        var b = _dialogs.OpenFile("Original binding", JsonFilter); if (b is null) return;
        var l = _dialogs.OpenFile("Reviewed compensation definition", JsonFilter); if (l is null) return;
        var plan = _dialogs.OpenFile("M1t saved plan", JsonFilter); if (plan is null) return;
        var r = _dialogs.OpenFile("M1t receipt", JsonFilter); if (r is null) return;
        if (_dialogs.Confirm("Перевірити M1t child?", "Явно обрані original/profile/binding/location; historical consistency, не новий baseline.")) await OpenChildAsync(c, o, p, b, l, plan, r);
    }
    private void ShowVtec(P28BasicCalibrationSettings settings)
    {
        var original = (byte)Draft!.Vtec.Fields[0].Original; var requested = (byte)(settings.Vtec?.RawValue ?? original);
        VtecPlot = Enumerable.Range(0, 256).Select(x => new P28PredicateRow((byte)x, P28ThresholdLogic.Evaluate(original, (byte)x), P28ThresholdLogic.Evaluate(requested, (byte)x))).ToArray();
    }
    private BasicLookupPlot[] DemoGraphs(P28BasicCalibrationSettings settings) => Enumerable.Range(0, 2).Select(i =>
    {
        var values = i == 0 ? settings.Idle.BaseTable : settings.Idle.LateTable;
        var cells = Draft!.Groups[i + 4].Fields.Select((f, n) => new P28IdleTableCell(f.Id, n, 0, f.Axis!.Value, 0, f.Original, values?[n] ?? f.Original, [], [])).ToArray();
        return Graph(i == 0 ? "Base lookup" : "Late lookup", cells);
    }).ToArray();
    private static BasicLookupPlot Graph(string title, IReadOnlyList<P28IdleTableCell> cells) => new(title,
        P28IdleTableEditor.ProjectLookup(cells.Select(c => c with { NewValue = c.OldValue }).ToArray()),
        P28IdleTableEditor.ProjectLookup(cells), cells.Select(c => c.Axis).ToArray());
    private void ShowPlan(P28BasicCalibrationPlan p)
    {
        var lines = new List<string>();
        foreach (var g in p.Groups)
        {
            lines.Add($"{g.Id}: requested={g.Requested}; unchanged={!g.EffectivelyChanged}; effectivelyChanged={g.EffectivelyChanged}");
            if (g.Vtec is { } v && v.Slot is { } slot) { var i = slot.Offset - P28ThresholdLogic.BlockOffset; lines.Add($"  {slot.Id}: {v.OriginalBytes[i]} → {v.NewBytes[i]} raw"); }
            if (g.Limiter is { } l)
            {
                lines.AddRange(l.FixedOperands.Select(w => $"  {w.FieldId}: {w.OriginalWord} → {w.NewWord} raw period"));
                lines.AddRange(l.AdaptiveWords.Select(w => $"  {w.FieldId}: {w.OldWord} → {w.NewWord} raw base; origin={w.Origin}, coefficient={w.Coefficient} unchanged"));
                lines.Add("  " + l.PolicyResult);
                lines.AddRange(l.DomainChecks.Select(d => $"  Domain: {d.CheckedInputs} inputs; noWrap={d.NoTargetWrap}; order={d.StrictTargetOrder}; gap={d.MinimumTargetGap}"));
            }
            if (g.Idle is { } t)
            {
                lines.AddRange(t.Cells.Select(c => $"  {c.FieldId}: {c.OldValue} → {c.NewValue}, axis={c.Axis} readonly"));
                lines.AddRange(t.DomainChecks.Select(d => $"  Domain: {d.CheckedInputs} inputs, min/max={d.Minimum}/{d.Maximum}; bounds={d.BoundsAndNodesVerified}"));
            }
        }
        lines.Add($"Одна compensation: 0x{p.Compensation.Offset:X4}: {p.Compensation.OldByte:X2} → {p.Compensation.NewByte:X2}. Diff={p.ExpectedDiff.Count}; A/B/C={p.ResidueA}/{p.ResidueB}/{p.ResidueC}; no-op={p.IsNoOp}.");
        lines.Add("Arithmetic preview ≠ native checksum Pass. Native execution: NotRun до fresh job. PcInspectionOnly / NotFlashReady.");
        PreviewText = string.Join("\n", lines);
        Diff = p.ExpectedDiff.Select(d => new BasicDiffRow($"0x{d.Offset:X4}", $"{d.OldByte:X2}", $"{d.NewByte:X2}",
            d.Offset == p.Compensation.Offset ? "checksum compensation" : Purpose(d.Offset))).ToArray();
        IdlePlots = p.Groups.Where(g => g.Idle is not null).Select(g => Graph(g.Id, g.Idle!.Cells)).ToArray();
        string Purpose(int offset)
        {
            foreach (var g in p.Groups)
            {
                if (g.Vtec?.Slot?.Offset == offset) return "vtec";
                if (g.Limiter is { } l && (l.FixedOperands.Any(w => offset >= w.Offset && offset < w.Offset + w.Width) || l.AdaptiveWords.Any(w => offset >= w.Offset && offset < w.Offset + w.Width))) return g.Id;
                if (g.Idle is { } t && t.Cells.Any(c => offset == c.ValueOffset || offset == c.ValueOffset + 1)) return g.Id;
            }
            throw new InvalidDataException("Unclassified diff offset.");
        }
    }
}
