using System.IO;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.ViewModels;

public sealed partial class MainViewModel
{
    private sealed record DefinitionSnapshot(string Path, string Digest);
    private VerifiedCompensationLocation? _compensationLocation;
    private string? _compensationPath;
    private P28ChecksumPreservingPreview? _checksumPreview;
    private P28VerifiedChecksumComposition? _checksumComposition;
    private P28VerifiedChecksumExport? _checksumExport;
    private string? _validatedRunnerDigest;

    public RelayCommand SelectCompensationCommand { get; private set; } = null!;
    public RelayCommand PreviewChecksumExportCommand { get; private set; } = null!;
    public AsyncCommand ValidateChecksumExportCommand { get; private set; } = null!;
    public AsyncCommand SaveChecksumExportCommand { get; private set; } = null!;
    public AsyncCommand OpenChecksumChildCommand { get; private set; } = null!;
    public string CompensationStatus { get; private set; } = "Потрібні original baseline binding та окремий reviewed CompensationLocation. Довільний offset не допускається.";
    public string ChecksumExportPreview { get; private set; } = "Окремий режим M1g. Звичайне Save не додає компенсацію. Actual execution: NotRun. NotFlashReady.";
    public bool CanPreviewChecksumExport => !IsBusy && SelectedSlot is not null &&
        (Mode == DesktopAccessMode.Demo || _compensationLocation is not null && Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.VerifiedDerived);
    public bool CanValidateChecksumExport => !IsBusy && _checksumComposition is not null && File.Exists(RunnerPath);
    public bool CanSaveChecksumExport => !IsBusy && _checksumExport is not null && File.Exists(RunnerPath) &&
        (_rpmSelection is null || _rpmSelectionPath is not null);

    private void InitializeChecksumExportCommands()
    {
        SelectCompensationCommand = new(() =>
        {
            var path = _dialogs.OpenFile("Оберіть приватний reviewed CompensationLocation із перевірюваним підписом", JsonFilter);
            if (path is not null) SelectCompensationDefinition(path);
        }, () => !IsBusy && Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.VerifiedDerived);
        PreviewChecksumExportCommand = new(PreviewChecksumExport, () => CanPreviewChecksumExport);
        ValidateChecksumExportCommand = new(ValidateChecksumExportAsync, () => CanValidateChecksumExport);
        SaveChecksumExportCommand = new(SaveChecksumFromDialogsAsync, () => CanSaveChecksumExport);
        OpenChecksumChildCommand = new(OpenChecksumFromDialogsAsync, () => !IsBusy);
    }

    public void SelectCompensationDefinition(string path)
    {
        InvalidateSession();
        _compensationLocation = null;
        _compensationPath = null;
        try
        {
            if (_document?.Profile is null || _document.Binding is null || Mode is not (DesktopAccessMode.BoundBaseline or DesktopAccessMode.VerifiedDerived))
                throw new InvalidOperationException("Спочатку перевірте original binding або повний M1c lineage.");
            RequireCurrentInputFiles(_document);
            var location = P28ChecksumPreservingEditor.LoadLocation(path);
            var availability = P28ChecksumPreservingEditor.GetAvailability(_document.Parent ?? _document.Image,
                _document.Profile, _document.Binding, true, location);
            CompensationStatus = availability.Reason + "\n" + availability.EvidenceScope;
            if (!availability.IsAvailable) throw new InvalidDataException(availability.Reason);
            _compensationLocation = location;
            _compensationPath = Path.GetFullPath(path);
            CompensationStatus = $"Доступне: {location.DefinitionId}, offset 0x{location.Offset:X4}.\n{location.EvidenceScope}\n" + string.Join("\n", location.Limitations);
        }
        catch (Exception exception) { CompensationStatus = "Недоступне: " + exception.Message; SetError(exception.Message); }
        NotifyAll();
    }

    public void PreviewChecksumExport()
    {
        InvalidateSession();
        try
        {
            if (!CanPreviewChecksumExport) throw new InvalidOperationException(CompensationStatus);
            if (Mode == DesktopAccessMode.Demo)
            {
                if (!TryParseRaw(ProposedRaw, out var raw)) throw new ArgumentException("Введіть ціле raw 0–255.");
                _checksumPreview = P28ChecksumPreservingEditor.CreateSyntheticPreview(SelectedSlot!.Id, raw);
                ChecksumExportPreview = "ОКРЕМИЙ вигаданий fixture: усі 8 порогів = 40, compensation 0x7000. Не поточні 8 байтів D0 demo, не Honda ROM.\n" + DescribeChecksumPreview(_checksumPreview, false);
            }
            else
            {
                RequireCurrentInputFiles(_document!);
                RequireCurrentDefinition();
                var parent = _document!.Parent ?? _document.Image;
                P28ChecksumPreservingPlan plan;
                if (Mode == DesktopAccessMode.VerifiedDerived)
                {
                    // Rebuild the existing verified M1c request from its original parent, never from the child bytes.
                    var threshold = _document.Plan!;
                    plan = P28ChecksumPreservingEditor.CreatePlan(parent, _document.Profile!, _document.Binding!, true,
                        threshold.SlotId, threshold.NewByte, _compensationLocation);
                }
                else
                {
                    if (!TryParseRaw(ProposedRaw, out var raw)) throw new ArgumentException("Введіть ціле raw 0–255.");
                    plan = P28ChecksumPreservingEditor.CreatePlan(parent, _document.Profile!, _document.Binding!, true,
                        SelectedSlot!.Id, raw, _compensationLocation);
                }
                _checksumPreview = P28ChecksumPreservingEditor.Apply(parent, _document.Profile!, _document.Binding!, plan, _compensationLocation);
                _checksumComposition = P28ChecksumPreservingEditor.Admit(_checksumPreview.Image, parent, _document.Profile!,
                    _document.Binding!, plan, _checksumPreview.Report, _compensationLocation!);
                ChecksumExportPreview = DescribeChecksumPreview(_checksumPreview, false);
            }
            ErrorText = "";
        }
        catch (Exception exception) { ClearChecksumPreview(); SetError(exception.Message); }
        NotifyAll();
    }

    private static string DescribeChecksumPreview(P28ChecksumPreservingPreview preview, bool executed)
    {
        var plan = preview.Plan;
        var threshold = plan.ThresholdPlan;
        return $"1. Запитаний поріг {threshold.SlotId}: 0x{threshold.Offset:X4}, {threshold.ExpectedOldByte} (0x{threshold.ExpectedOldByte:X2}) → {threshold.NewByte} (0x{threshold.NewByte:X2}).\n" +
            $"2. Обчислена компенсація: 0x{plan.Compensation.Offset:X4}, {plan.Compensation.OldByte} (0x{plan.Compensation.OldByte:X2}) → {plan.Compensation.NewByte} (0x{plan.Compensation.NewByte:X2}).\n" +
            $"Фактичний diff: {preview.Report.ChangedByteCount}; no-op: {plan.IsNoOp}. Residue A/B/C: {plan.BaselineResidue}/{plan.IntermediateResidue}/{plan.FinalResidue}.\n" +
            $"Actual execution: {(executed ? "Match · strict · A і C Valid · 6 запусків × 512 викликів · без assumptions" : "NotRun — арифметика й preview не є виконанням")}.\n" +
            $"Threshold-only B/C: модель збережена; native checksum не підтверджує VTEC/RPM.\n{plan.EvidenceScope}\nPcInspectionOnly / NotFlashReady.";
    }

    public Task ValidateChecksumExportAsync()
    {
        if (!CanValidateChecksumExport) { SetError(!File.Exists(RunnerPath) ? RunnerStatus : "Потрібен допущений складений preview, не demo."); return Task.CompletedTask; }
        var document = _document!;
        var composition = _checksumComposition!;
        var session = SessionId;
        var runner = RunnerPath;
        var definition = CaptureDefinition();
        var rpm = CaptureRpmSelection(document);
        BeginJob();
        _activeTask = ValidateChecksumCoreAsync(document, composition, runner, definition, rpm, session, JobId, _cancellation!.Token);
        return _activeTask;
    }

    private async Task ValidateChecksumCoreAsync(DesktopDocument document, P28VerifiedChecksumComposition composition,
        string runner, DefinitionSnapshot definition, RpmSelectionSnapshot? rpm, long session, long job, CancellationToken token)
    {
        try
        {
            var digest = await Task.Run(() =>
            {
                RequireCurrentInputFiles(document); RequireDefinition(definition); RequireRpmSelection(rpm, false, token);
                return RunnerDigest(runner);
            }, token);
            var validated = await Task.Run(async () =>
            {
                var result = await _operations.ValidateChecksumExportAsync(composition, runner, token).ConfigureAwait(false);
                token.ThrowIfCancellationRequested();
                RequireCurrentInputFiles(document); RequireDefinition(definition); RequireRpmSelection(rpm, false, token);
                if (RunnerDigest(runner) != digest) throw new InvalidDataException("Runner змінився під час виконання.");
                return result;
            }, token);
            token.ThrowIfCancellationRequested();
            if (session != SessionId || job != JobId || _disposed) return;
            if (validated.Composition.Plan.ToJson(false) != composition.Plan.ToJson(false) || validated.Composition.Image.Hash != composition.Image.Hash)
                throw new InvalidDataException("Виконання повернуло іншу композицію.");
            P28ChecksumPreservingExecution.ValidateForPublication(validated);
            _checksumExport = validated;
            _validatedRunnerDigest = digest;
            ChecksumExportPreview = DescribeChecksumPreview(_checksumPreview!, true) + RpmExportQualification;
            _resultJson = validated.ChecksumReport.ToJson();
            Counters = DesktopCounters.From(validated.ChecksumReport.Counts);
            ResultSummary = "M1g actual strict checksum завершено. Окрема кнопка експорту доступна для цього стану; NotFlashReady.";
        }
        catch (OperationCanceledException) { if (session == SessionId && !_disposed) { _checksumExport = null; StatusText = "Виконання скасовано; експорт не допущено."; } }
        catch (Exception exception) { _checksumExport = null; SetError(exception, session); }
        finally { EndJob(); }
    }

    public Task SaveChecksumExportAsync(DesktopSavePaths paths)
    {
        if (!CanSaveChecksumExport) { SetError("Експорт потребує actual strict execution поточного стану. Preview / demo / старий receipt не є дозволом."); return Task.CompletedTask; }
        if (!_dialogs.Confirm("Явно зберегти нову M1g PC-only копію?", ChecksumExportPreview + "\n\nНові BIN, composed plan і receipt. Без перезапису. Група не є атомарною при втраті живлення.")) return Task.CompletedTask;
        _activeTask = SaveChecksumCoreAsync(paths);
        return _activeTask;
    }

    private async Task SaveChecksumCoreAsync(DesktopSavePaths paths)
    {
        var document = _document!;
        var validated = _checksumExport!;
        var locationPath = _compensationPath!;
        var definition = CaptureDefinition();
        var rpm = CaptureRpmSelection(document);
        var runner = RunnerPath;
        var runnerDigest = _validatedRunnerDigest;
        var protectedPaths = Array.AsReadOnly(Protected(document).Concat(new[] { locationPath, runner }).Concat(RpmProtectedPaths()).ToArray());
        var rpmQualification = RpmExportQualification;
        var session = SessionId;
        BeginJob();
        var job = JobId;
        var token = _cancellation!.Token;
        try
        {
            await Task.Run(() =>
            {
                RequireCurrentInputFiles(document); RequireDefinition(definition); RequireRpmSelection(rpm, true, token);
                if (RunnerDigest(runner) != runnerDigest) throw new InvalidDataException("Runner змінився після actual execution. Повторіть перевірку.");
            }, token);
            token.ThrowIfCancellationRequested();
            if (session != SessionId || job != JobId || _disposed) return;
            var verification = await _operations.SaveChecksumExportAsync(validated, paths, protectedPaths, token);
            if (!verification.IsValid) throw new InvalidDataException("Нові файли не пройшли readback; залишено для дослідження.");
            // Never trust only a service-returned success or its chosen bytes.
            verification = P28ChecksumPreservingCopyWriter.VerifySavedCopy(validated, paths.OutputPath, paths.PlanPath, paths.ReportPath);
            if (!verification.IsValid) throw new InvalidDataException("Незалежна перевірка складеного lineage не пройшла.");
            RequireCurrentInputFiles(document); RequireDefinition(definition);
            if (session != SessionId || job != JobId || token.IsCancellationRequested || _disposed) return;
            var child = LoadChecksumDocument(paths.OutputPath, (document.Parent ?? document.Image).SourcePath!,
                document.Profile!.SourcePath!, document.BindingPath!, paths.PlanPath, paths.ReportPath, locationPath, true);
            SetDocument(child);
            _resultJson = verification.ToJson();
            ResultSummary = "Новий M1g child original parent перечитано; повний diff та reverse restoration підтверджені. Receipt — історичний запуск, не дозвіл на новий export. NotFlashReady." + rpmQualification;
        }
        catch (OperationCanceledException) { if (session == SessionId && !_disposed) StatusText = "Скасовано до публікації."; }
        catch (Exception exception) { SetError(exception, session); }
        finally { EndJob(); }
    }

    public async Task OpenChecksumChildAsync(string output, string parent, string profile, string binding,
        string plan, string report, string location, bool acknowledged)
    {
        var session = InvalidateSession();
        try
        {
            var document = await Task.Run(() => LoadChecksumDocument(output, parent, profile, binding, plan, report, location, acknowledged));
            if (session == SessionId && !_disposed) SetDocument(document);
        }
        catch (Exception exception) { SetError(exception, session); }
    }

    private static DesktopDocument LoadChecksumDocument(string outputPath, string parentPath, string profilePath,
        string bindingPath, string planPath, string reportPath, string locationPath, bool acknowledged)
    {
        if (!acknowledged) throw new InvalidDataException("Потрібне явне підтвердження research profile; воно не заміняє перевірку.");
        var image = RomImage.Load(outputPath); var parent = RomImage.Load(parentPath);
        var profile = RomProfile.Load(profilePath); var binding = P28ExactBaselineBinding.Load(bindingPath);
        var plan = P28ChecksumPreservingPlan.Load(planPath); var receipt = P28ChecksumPreservingExportReport.Load(reportPath);
        var location = P28ChecksumPreservingEditor.LoadLocation(locationPath);
        var composition = P28ChecksumPreservingEditor.Admit(image, parent, profile, binding, plan, receipt.CompositionReport, location);
        return new(DesktopAccessMode.VerifiedChecksumDerived, image, parent, profile, binding,
            InputPaths: Array.AsReadOnly(new[] { outputPath, parentPath, profilePath, bindingPath, planPath, reportPath, locationPath }.Select(Path.GetFullPath).ToArray()),
            LineagePaths: new(Path.GetFullPath(outputPath), Path.GetFullPath(parentPath), Path.GetFullPath(profilePath), Path.GetFullPath(bindingPath), Path.GetFullPath(planPath), Path.GetFullPath(reportPath)),
            BindingPath: Path.GetFullPath(bindingPath), ChecksumComposition: composition,
            CompensationDefinitionPath: Path.GetFullPath(locationPath), ChecksumExportReport: receipt);
    }

    private Task VerifyChecksumChildAsync()
    {
        BeginJob();
        var document = _document!; var session = SessionId; var token = _cancellation!.Token;
        _activeTask = VerifyChecksumCoreAsync(document, session, token);
        return _activeTask;
    }

    private async Task VerifyChecksumCoreAsync(DesktopDocument document, long session, CancellationToken token)
    {
        try
        {
            await Task.Run(() => { token.ThrowIfCancellationRequested(); RequireCurrentInputFiles(document); }, token);
            if (session != SessionId || token.IsCancellationRequested || _disposed) return;
            _resultJson = document.ChecksumExportReport!.ToJson();
            ResultSummary = "M1g lineage перечитано й підтверджено. Історичний receipt не є новим actual execution. NotFlashReady.";
        }
        catch (OperationCanceledException) { if (session == SessionId && !_disposed) StatusText = "Перевірку скасовано."; }
        catch (Exception exception) { SetError(exception, session); }
        finally { EndJob(); }
    }

    private static void RequireCurrentChecksumFiles(DesktopDocument document)
    {
        var paths = document.LineagePaths ?? throw new InvalidDataException("Потрібні original lineage paths.");
        var current = LoadChecksumDocument(paths.OutputPath, paths.ParentPath, paths.ProfilePath, paths.BindingPath,
            paths.PlanPath, paths.ReportPath, document.CompensationDefinitionPath!, true);
        if (current.Image.Hash != document.Image.Hash ||
            current.ChecksumComposition!.Plan.ToJson(false) != document.ChecksumComposition!.Plan.ToJson(false) ||
            current.ChecksumExportReport!.ToJson(false) != document.ChecksumExportReport!.ToJson(false))
            throw new InvalidDataException("M1g child / plan / receipt / definition змінився після відкриття.");
    }

    private void RequireCurrentDefinition()
    {
        RequireDefinition(CaptureDefinition());
    }
    private DefinitionSnapshot CaptureDefinition()
    {
        if (_compensationLocation is null || _compensationPath is null)
            throw new InvalidDataException("Reviewed CompensationLocation відсутній або змінився; оберіть і перевірте знову.");
        return new(_compensationPath, _compensationLocation.DefinitionDigest);
    }
    private static void RequireDefinition(DefinitionSnapshot snapshot)
    {
        if (P28ChecksumPreservingEditor.LoadLocation(snapshot.Path).DefinitionDigest != snapshot.Digest)
            throw new InvalidDataException("Reviewed CompensationLocation відсутній або змінився; оберіть і перевірте знову.");
    }
    private static string RunnerDigest(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(path)));
    private void ClearChecksumPreview()
    {
        _checksumPreview = null; _checksumComposition = null; _checksumExport = null; _validatedRunnerDigest = null;
        ChecksumExportPreview = "Preview поточного стану ще не створено. Actual execution: NotRun. NotFlashReady.";
    }
    private void ResetCompensationDefinition(DesktopDocument document)
    {
        _compensationLocation = null; _compensationPath = null;
        CompensationStatus = document.Mode == DesktopAccessMode.VerifiedChecksumDerived
            ? "Перевірений M1g lineage. Receipt історичний; child не можна використати як baseline."
            : document.Mode == DesktopAccessMode.Demo ? "Лише окремий вигаданий arithmetic fixture. Немає Honda definition, execution чи export."
            : "Недоступне: reviewed CompensationLocation не обрано. Потрібен exact original binding та перевірений опис; довільний offset заборонений.";
    }
    private void RefreshChecksumExportCommands()
    {
        SelectCompensationCommand?.Refresh(); PreviewChecksumExportCommand?.Refresh(); ValidateChecksumExportCommand?.Refresh();
        SaveChecksumExportCommand?.Refresh(); OpenChecksumChildCommand?.Refresh();
    }
    private async Task SaveChecksumFromDialogsAsync()
    {
        var output = _dialogs.SaveFile("Новий M1g PC-only BIN", BinFilter, "research-m1g.bin"); if (output is null) return;
        var plan = _dialogs.SaveFile("Новий складений M1g plan", JsonFilter, "research-m1g.plan.json"); if (plan is null) return;
        var report = _dialogs.SaveFile("Новий M1g export receipt", JsonFilter, "research-m1g.receipt.json"); if (report is null) return;
        await SaveChecksumExportAsync(new(output, plan, report));
    }
    private async Task OpenChecksumFromDialogsAsync()
    {
        var output = _dialogs.OpenFile("M1g child BIN", BinFilter); if (output is null) return;
        var parent = _dialogs.OpenFile("Незмінений original parent BIN", BinFilter); if (parent is null) return;
        var profile = _dialogs.OpenFile("Original research profile", JsonFilter); if (profile is null) return;
        var binding = _dialogs.OpenFile("Original binding", JsonFilter); if (binding is null) return;
        var plan = _dialogs.OpenFile("Складений M1g plan", JsonFilter); if (plan is null) return;
        var report = _dialogs.OpenFile("M1g export receipt", JsonFilter); if (report is null) return;
        var location = _dialogs.OpenFile("Reviewed CompensationLocation", JsonFilter); if (location is null) return;
        if (_dialogs.Confirm("Відкрити M1g lineage?", "Перевірити повний original-parent lineage та reviewed CompensationLocation? Це не запуск ECU і не дозвіл на прошивання."))
            await OpenChecksumChildAsync(output, parent, profile, binding, plan, report, location, true);
    }
}
