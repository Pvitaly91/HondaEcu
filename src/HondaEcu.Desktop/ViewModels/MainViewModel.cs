using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Runtime.CompilerServices;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;

namespace HondaEcu.Desktop.ViewModels;

public sealed partial class MainViewModel : INotifyPropertyChanged, IDisposable
{
    private const string BinFilter = "BIN файли (*.bin)|*.bin|Усі файли (*.*)|*.*";
    private const string JsonFilter = "JSON (*.json)|*.json|Усі файли (*.*)|*.*";
    private readonly IDialogService _dialogs;
    private readonly IDesktopOperations _operations;
    private readonly DesktopResources _resources;
    private DesktopDocument? _document;
    private ThresholdSlotView? _selectedSlot;
    private string _proposedRaw = "";
    private string? _pendingSlot;
    private P28RawThresholdPlan? _pendingPlan;
    private P28RawThresholdPatchResult? _pendingResult;
    private CancellationTokenSource? _cancellation;
    private Task _activeTask = Task.CompletedTask;
    private string? _resultJson;
    private bool _disposed;
    private bool _allowAddEr1;
    private bool _allowAddEr3;

    public MainViewModel(IDialogService dialogs, IDesktopOperations? operations = null, DesktopResources? resources = null)
    {
        _dialogs = dialogs;
        _operations = operations ?? new DesktopOperations();
        _resources = resources ?? new DesktopResources();
        RunnerPath = _resources.BundledRunnerPath;
        OpenBinCommand = new(async () =>
        {
            var path = _dialogs.OpenFile("Відкрити BIN для огляду", BinFilter);
            if (path is not null) await OpenBinAsync(path);
        }, () => !IsBusy);
        DemoCommand = new(EnterDemo, () => !IsBusy);
        BindBaselineCommand = new(BindFromDialogsAsync, () => Mode == DesktopAccessMode.RawOnly && !IsBusy);
        OpenDerivedCommand = new(DerivedFromDialogsAsync, () => !IsBusy);
        PreviewCommand = new(PreviewChange, () => CanEdit && SelectedSlot is not null);
        RevertCommand = new(RevertChange, () => _pendingSlot is not null && !IsBusy);
        SaveCopyCommand = new(SaveFromDialogsAsync, () => CanSave);
        VerifyCommand = new(VerifyChangeAsync, () => !IsBusy && (_pendingResult is not null || Mode is DesktopAccessMode.VerifiedDerived or DesktopAccessMode.VerifiedChecksumDerived));
        ExecuteCommand = new(() => RunValidationAsync(DesktopValidationKind.Execute), () => CanExecuteM1d);
        ProducerCommand = new(() => RunValidationAsync(DesktopValidationKind.Producer), () => CanExecute);
        ChecksumCommand = new(() => RunValidationAsync(DesktopValidationKind.Checksum), () => CanCheckChecksum);
        CancelCommand = new(Cancel, () => IsBusy);
        SelectRunnerCommand = new(() =>
        {
            var path = _dialogs.OpenFile("Вибрати локальний p28-slice-runner", "Програми (*.exe)|*.exe|Усі файли (*.*)|*.*");
            if (path is not null) SelectRunner(path);
        }, () => !IsBusy);
        OpenResultsCommand = new(() => _dialogs.ShowStructuredResult("Структурований результат поточного запуску", _resultJson!),
            () => _resultJson is not null && !IsBusy);
        InitializeChecksumExportCommands();
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    public AsyncCommand OpenBinCommand { get; }
    public RelayCommand DemoCommand { get; }
    public AsyncCommand BindBaselineCommand { get; }
    public AsyncCommand OpenDerivedCommand { get; }
    public RelayCommand PreviewCommand { get; }
    public RelayCommand RevertCommand { get; }
    public AsyncCommand SaveCopyCommand { get; }
    public AsyncCommand VerifyCommand { get; }
    public AsyncCommand ExecuteCommand { get; }
    public AsyncCommand ProducerCommand { get; }
    public AsyncCommand ChecksumCommand { get; }
    public RelayCommand CancelCommand { get; }
    public RelayCommand SelectRunnerCommand { get; }
    public RelayCommand OpenResultsCommand { get; }

    public DesktopAccessMode Mode => _document?.Mode ?? DesktopAccessMode.Empty;
    public string ModeLabel => Mode switch
    {
        DesktopAccessMode.RawOnly => "Unknown / raw-only — інтерпретацію не підтверджено",
        DesktopAccessMode.BoundBaseline => "Оригінальний baseline — приватний research binding перевірено",
        DesktopAccessMode.VerifiedDerived => "Перевірений похідний файл — редагування заборонено",
        DesktopAccessMode.VerifiedChecksumDerived => "Перевірений M1g child original parent — PcInspectionOnly / NotFlashReady",
        DesktopAccessMode.Demo => "Синтетичний приклад — не прошивка Honda",
        _ => "Відкрийте BIN або демонстраційний режим",
    };
    public string FileName => Mode == DesktopAccessMode.Demo ? "Синтетичні пороги (лише пам’ять)" :
        _document?.Image.SourcePath is { } path ? Path.GetFileName(path) : "Файл не відкрито";
    public int FileSize => _document?.Image.Size ?? 0;
    public string HashText => Mode == DesktopAccessMode.Demo ? "Не застосовується до синтетичного прикладу" :
        _document is null ? "" : $"SHA-256: {_document.Image.Hash.Sha256}\nCRC32: {_document.Image.Hash.Crc32}";
    public string ProfileName => _document?.Profile?.Id ?? "Не обрано";
    public string BindingStatus => Mode switch
    {
        DesktopAccessMode.BoundBaseline => "Matched — analyst-declared, не автентифікація ECU",
        DesktopAccessMode.VerifiedDerived => "Original parent binding + перевірені plan/report; child не є новим baseline",
        DesktopAccessMode.VerifiedChecksumDerived => "Original parent + складений план + reviewed CompensationLocation; не новий baseline",
        DesktopAccessMode.Demo => "Binding відсутній; демонстрація не створює binding",
        _ => "NotProvided — лише нейтральні байти",
    };
    public string HexPreview { get; private set; } = "";
    public IReadOnlyList<ThresholdSlotView> Slots { get; private set; } = [];
    public ThresholdSlotView? SelectedSlot
    {
        get => _selectedSlot;
        set
        {
            if (_selectedSlot?.Id == value?.Id) return;
            if (_pendingSlot is not null && value?.Id != _pendingSlot)
            {
                ErrorText = "Дозволений рівно один pending slot. Спочатку скасуйте поточну зміну.";
                NotifyAll();
                return;
            }
            if (value is not null && !Slots.Any(slot => slot.Id == value.Id)) return;
            InvalidateSession();
            _selectedSlot = value;
            _proposedRaw = value?.CurrentRaw.ToString(CultureInfo.InvariantCulture) ?? "";
            UpdatePlot(value?.CurrentRaw);
            NotifyAll();
        }
    }
    public string ProposedRaw
    {
        get => _proposedRaw;
        set
        {
            if (_proposedRaw == value) return;
            InvalidateSession();
            _proposedRaw = value;
            // A previously reviewed plan must not be saved after the input text changes.
            ClearPending();
            UpdatePlot(SelectedSlot?.CurrentRaw);
            NotifyAll();
        }
    }
    public string PreviewText { get; private set; } = "Оберіть слот. Зміни існують тільки в пам’яті.";
    public IReadOnlyList<P28PredicateRow> PlotRows { get; private set; } = [];
    public string StatusText { get; private set; } = "Дослідницький режим. Не для запису в ECU";
    public string ErrorText { get; private set; } = "";
    public bool IsBusy { get; private set; }
    public bool CanEdit => !IsBusy && Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.Demo;
    public bool CanSave => !IsBusy && Mode == DesktopAccessMode.BoundBaseline && _pendingResult is not null;
    public bool CanExecute => !IsBusy && File.Exists(RunnerPath) && Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.VerifiedDerived or DesktopAccessMode.VerifiedChecksumDerived;
    public bool CanExecuteM1d => CanExecute && !AllowAddEr1;
    public bool CanCheckChecksum => !IsBusy && Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.VerifiedDerived or DesktopAccessMode.VerifiedChecksumDerived;
    public string RunnerPath { get; private set; }
    public string RunnerStatus => File.Exists(RunnerPath) ? "Локальний runner доступний" :
        "Runner відсутній. Огляд і preview працюють; явно виберіть локальний runner для виконання.";
    public bool AllowAddEr1 { get => _allowAddEr1; set { if (_allowAddEr1 != value) { InvalidateSession(); _allowAddEr1 = value; NotifyAll(); } } }
    public bool AllowAddEr3 { get => _allowAddEr3; set { if (_allowAddEr3 != value) { InvalidateSession(); _allowAddEr3 = value; NotifyAll(); } } }
    public DesktopCounters Counters { get; private set; } = DesktopCounters.Empty;
    public DesktopChecksumSummary? ChecksumSummary { get; private set; }
    public bool HasChecksumResult => ChecksumSummary is not null;
    public string ResultSummary { get; private set; } = "Перевірки ще не виконувалися. Фізичні оберти не підтверджені.";
    public long SessionId { get; private set; }
    public long JobId { get; private set; }
    public string? PendingSlotId => _pendingSlot;
    public int ChangedByteCount => _pendingResult?.Report.ChangedByteCount ??
        (Mode == DesktopAccessMode.Demo && _pendingSlot is not null && PlotRows.Any(row => row.Before != row.After) ? 1 : 0);

    public async Task OpenBinAsync(string path)
    {
        var session = InvalidateSession();
        try
        {
            var image = await Task.Run(() => RomImage.Load(path));
            if (session != SessionId || _disposed) return;
            SetDocument(new(DesktopAccessMode.RawOnly, image, InputPaths: Array.AsReadOnly(new[] { Path.GetFullPath(path) })));
        }
        catch (Exception exception) { SetError(exception, session); }
    }

    public async Task BindBaselineAsync(string profilePath, string bindingPath, bool acknowledged)
    {
        if (_document is null || Mode != DesktopAccessMode.RawOnly) { SetError("Спочатку відкрийте оригінальний BIN у raw-only режимі."); return; }
        var snapshot = _document;
        var session = InvalidateSession();
        try
        {
            var document = await Task.Run(() =>
            {
                var profile = RomProfile.Load(profilePath);
                var binding = P28ExactBaselineBinding.Load(bindingPath);
                P28ByteExecutionValidator.ValidateAdmission(snapshot.Image, profile, binding, acknowledged);
                return snapshot with
                {
                    Mode = DesktopAccessMode.BoundBaseline,
                    Profile = profile,
                    Binding = binding,
                    BindingPath = Path.GetFullPath(bindingPath),
                    InputPaths = Array.AsReadOnly(Protected(snapshot).Concat(new[] { Path.GetFullPath(profilePath), Path.GetFullPath(bindingPath) }).ToArray())
                };
            });
            if (session == SessionId && !_disposed) SetDocument(document);
        }
        catch (Exception exception) { SetError(exception, session); }
    }

    public async Task OpenDerivedAsync(string outputPath, string parentPath, string profilePath,
        string bindingPath, string planPath, string reportPath, bool acknowledged)
    {
        var session = InvalidateSession();
        try
        {
            var document = await Task.Run(() =>
            {
                var image = RomImage.Load(outputPath);
                var parent = RomImage.Load(parentPath);
                var profile = RomProfile.Load(profilePath);
                var binding = P28ExactBaselineBinding.Load(bindingPath);
                var plan = P28RawThresholdPlan.Load(planPath);
                var report = P28RawThresholdPatchReport.Load(reportPath);
                P28ByteExecutionValidator.ValidateAdmission(parent, profile, binding, acknowledged, image, plan, report);
                return new DesktopDocument(DesktopAccessMode.VerifiedDerived, image, parent, profile, binding, plan, report,
                    Array.AsReadOnly(new[] { outputPath, parentPath, profilePath, bindingPath, planPath, reportPath }.Select(Path.GetFullPath).ToArray()),
                    new(Path.GetFullPath(outputPath), Path.GetFullPath(parentPath), Path.GetFullPath(profilePath),
                        Path.GetFullPath(bindingPath), Path.GetFullPath(planPath), Path.GetFullPath(reportPath)), Path.GetFullPath(bindingPath));
            });
            if (session == SessionId && !_disposed) SetDocument(document);
        }
        catch (Exception exception) { SetError(exception, session); }
    }

    public void EnterDemo()
    {
        InvalidateSession();
        // Exactly eight invented values, not an OEM-sized image or a trusted research binding.
        SetDocument(new(DesktopAccessMode.Demo, RomImage.FromBytes(new byte[] { 40, 55, 80, 95, 120, 135, 160, 175 })));
    }

    public void PreviewChange()
    {
        try
        {
            if (!CanEdit || SelectedSlot is null) throw new InvalidOperationException("Редагування доступне лише bound baseline або синтетичному прикладу.");
            if (_pendingSlot is not null && _pendingSlot != SelectedSlot.Id) throw new InvalidOperationException("Спочатку скасуйте pending slot.");
            if (!TryParseRaw(ProposedRaw, out var value)) throw new ArgumentException("Введіть лише десяткове ціле число 0–255, без знаку, hex або округлення.");
            InvalidateSession();
            if (Mode == DesktopAccessMode.BoundBaseline)
            {
                _pendingPlan = P28RawThresholdEditor.CreatePlan(_document!.Image, _document.Profile!, _document.Binding!, true, SelectedSlot.Id, value);
                _pendingResult = P28RawThresholdEditor.Apply(_document.Image, _document.Profile!, _document.Binding!, _pendingPlan);
            }
            _pendingSlot = SelectedSlot.Id;
            UpdatePlot(value);
            if (_pendingPlan is not null) PlotRows = _pendingPlan.PredicateImpact.Rows;
            var count = _pendingResult?.Report.ChangedByteCount ?? (value == SelectedSlot.CurrentRaw ? 0 : 1);
            var diff = _pendingResult is null ? $"{SelectedSlot.OffsetHex}: {SelectedSlot.CurrentRaw:X2} → {value:X2}" :
                string.Join("; ", _pendingResult.Report.Diff.Select(item => $"0x{item.Offset:X4}: {item.OldByte:X2} → {item.NewByte:X2}"));
            PreviewText = $"{SelectedSlot.Id}\n{SelectedSlot.OffsetHex}: {SelectedSlot.CurrentRaw} (0x{SelectedSlot.CurrentRaw:X2}) → {value} (0x{value:X2})\n" +
                $"Точний diff: {(count == 0 ? "немає (no-op)" : diff)}\n" +
                $"Змінено байтів: {count}. Інші слоти не змінено.\nChecksum: Unknown; PcInspectionOnly / NotFlashReady.\n" +
                $"Prior state: {SelectedSlot.PriorState}; equality: false. Модель, не виконання ROM.";
            foreach (var slot in Slots) slot.ProposedRaw = slot.Id == _pendingSlot ? value.ToString(CultureInfo.InvariantCulture) : "";
            NotifyAll();
        }
        catch (Exception exception) { SetError(exception.Message); }
    }

    public static bool TryParseRaw(string text, out byte value) => byte.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out value);

    public void RevertChange()
    {
        InvalidateSession();
        ClearPending();
        _proposedRaw = SelectedSlot?.CurrentRaw.ToString(CultureInfo.InvariantCulture) ?? "";
        UpdatePlot(SelectedSlot?.CurrentRaw);
        NotifyAll();
    }

    public Task VerifyChangeAsync()
    {
        if (IsBusy || _document is null) return Task.CompletedTask;
        if (Mode == DesktopAccessMode.VerifiedChecksumDerived) return VerifyChecksumChildAsync();
        BeginJob();
        _activeTask = VerifyCoreAsync(ValidationDocument(), _pendingResult is not null, SessionId, _cancellation!.Token);
        return _activeTask;
    }

    private async Task VerifyCoreAsync(DesktopDocument document, bool inMemory, long session, CancellationToken token)
    {
        try
        {
            var report = await Task.Run(() =>
            {
                token.ThrowIfCancellationRequested();
                if (document.Mode != DesktopAccessMode.VerifiedDerived) throw new InvalidOperationException("Немає зміни з plan/report для перевірки.");
                if (inMemory) return P28RawThresholdEditor.Verify(document.Image, document.Parent!, document.Profile!, document.Binding!, document.Plan!, document.PatchReport!);
                var paths = document.LineagePaths ?? throw new InvalidDataException("Для повторного читання потрібні всі original lineage paths.");
                var current = RomImage.Load(paths.OutputPath);
                var parent = RomImage.Load(paths.ParentPath);
                var profile = RomProfile.Load(paths.ProfilePath);
                var binding = P28ExactBaselineBinding.Load(paths.BindingPath);
                var plan = P28RawThresholdPlan.Load(paths.PlanPath);
                var patch = P28RawThresholdPatchReport.Load(paths.ReportPath);
                if (current.Hash != document.Image.Hash || parent.Hash != document.Parent!.Hash ||
                    P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(document.Profile!) ||
                    P28RawThresholdEditor.ComputeBindingDigest(binding) != P28RawThresholdEditor.ComputeBindingDigest(document.Binding!) ||
                    plan.ToJson(false) != document.Plan!.ToJson(false) || patch.ToJson(false) != document.PatchReport!.ToJson(false))
                    throw new InvalidDataException("Один із файлів lineage змінився після відкриття. Відкрийте і перевірте набір знову.");
                return P28RawThresholdEditor.Verify(current, parent, profile, binding, plan, patch);
            }, token);
            if (session != SessionId || token.IsCancellationRequested || _disposed) return;
            _resultJson = report.ToJson();
            ResultSummary = report.IsValid ? "Core verification: точний diff та lineage підтверджено " +
                (inMemory ? "у пам’яті" : "незалежним повторним читанням файлів") + ". NotFlashReady." : "Core verification: помилка lineage.";
        }
        catch (OperationCanceledException) { if (session == SessionId) StatusText = "Перевірку скасовано."; }
        catch (Exception exception) { SetError(exception, session); }
        finally { EndJob(); }
    }

    public Task SaveCopyAsync(DesktopSavePaths paths)
    {
        if (!CanSave) { SetError("Запис без перевіреного original binding і reviewed plan заборонено. Demo не зберігається як Honda BIN."); return Task.CompletedTask; }
        if (!_dialogs.Confirm("Зберегти нову PC-only копію?", PreviewText + "\n\nБуде створено нові BIN, plan і report. Не для ECU. Група файлів не є OS-транзакцією.")) return Task.CompletedTask;
        _activeTask = SaveCoreAsync(paths);
        return _activeTask;
    }

    private async Task SaveCoreAsync(DesktopSavePaths paths)
    {
        var document = _document!;
        var result = _pendingResult!;
        var session = SessionId;
        BeginJob();
        try
        {
            await Task.Run(() => RequireCurrentInputFiles(document), _cancellation!.Token);
            var verification = await _operations.SaveAsync(result, paths, Protected(document).Append(RunnerPath).ToArray(), _cancellation!.Token);
            if (!verification.IsValid) throw new InvalidDataException("Незалежне повторне читання збереженої копії не пройшло verification.");
            // A successful injected writer is not sufficient authority: reopen all three artifacts.
            var child = RomImage.Load(paths.OutputPath);
            var plan = P28RawThresholdPlan.Load(paths.PlanPath);
            var patchReport = P28RawThresholdPatchReport.Load(paths.ReportPath);
            if (child.Hash != result.Image.Hash || P28RawThresholdEditor.ComputePlanDigest(plan) != result.Report.PlanDigest ||
                patchReport.ToJson(false) != result.Report.ToJson(false))
                throw new InvalidDataException("Повторно прочитані файли не відповідають точній підтвердженій зміні. Нові файли залишено для перевірки.");
            P28ByteExecutionValidator.ValidateAdmission(document.Image, document.Profile!, document.Binding!, true, child, plan, patchReport);
            RequireCurrentInputFiles(document);
            if (session != SessionId || _disposed) return;
            InvalidateSession();
            SetDocument(new(DesktopAccessMode.VerifiedDerived, child, document.Image, document.Profile, document.Binding, plan, patchReport,
                Array.AsReadOnly(Protected(document).Concat(new[] { paths.OutputPath, paths.PlanPath, paths.ReportPath }.Select(Path.GetFullPath)).ToArray()),
                new(Path.GetFullPath(paths.OutputPath), document.Image.SourcePath!, document.Profile!.SourcePath!,
                    document.BindingPath!, Path.GetFullPath(paths.PlanPath), Path.GetFullPath(paths.ReportPath)), document.BindingPath));
            _resultJson = verification.ToJson();
            ResultSummary = "Незалежне повторне читання BIN, plan і report успішне. Child оригіналу; patch chains заборонено. NotFlashReady.";
        }
        catch (OperationCanceledException) { if (session == SessionId) StatusText = "Скасовано до початку запису."; }
        catch (Exception exception) { SetError(exception, session); }
        finally { EndJob(); }
    }

    public Task RunValidationAsync(DesktopValidationKind kind)
    {
        if ((kind == DesktopValidationKind.Checksum ? !CanCheckChecksum : !CanExecute) ||
            kind == DesktopValidationKind.Execute && AllowAddEr1)
        {
            SetError(!File.Exists(RunnerPath) ? RunnerStatus : "Потрібен bound baseline / verified child; oki.add-er1-a дозволений лише для M1e.");
            return Task.CompletedTask;
        }
        var assumptions = new List<string>();
        if (kind != DesktopValidationKind.Checksum)
        {
            if (AllowAddEr1) assumptions.Add(P28ProducerModel.AddEr1Assumption);
            if (AllowAddEr3) assumptions.Add(P28ByteExecutionValidator.AddAssumption);
        }
        if (assumptions.Count != 0 && !_dialogs.Confirm("Непідтверджені assumptions", string.Join("\n", assumptions) +
            "\n\nЦі дозволи не підтверджують інструкції. Умовні результати залишаться окремими. Продовжити?")) return Task.CompletedTask;
        BeginJob();
        var job = new DesktopValidationJob(SessionId, JobId, kind, ValidationDocument(), RunnerPath,
            Array.AsReadOnly(assumptions.ToArray()), SelectedSlot?.Id);
        _activeTask = ValidateCoreAsync(job, _cancellation!.Token);
        return _activeTask;
    }

    private async Task ValidateCoreAsync(DesktopValidationJob job, CancellationToken token)
    {
        try
        {
            // Include serialization/model comparison on a worker, not only the subprocess wait.
            var result = await Task.Run(async () =>
            {
                RequireCurrentInputFiles(job.Document);
                var measured = await _operations.ValidateAsync(job, token).ConfigureAwait(false);
                token.ThrowIfCancellationRequested();
                RequireCurrentInputFiles(job.Document);
                return measured;
            }, token);
            if (job.SessionId != SessionId || job.JobId != JobId || token.IsCancellationRequested || _disposed) return;
            Counters = result.Counters;
            _resultJson = result.Json;
            ChecksumSummary = result.Checksum is null ? null : DesktopChecksumSummary.From(result.Checksum);
            var state = result.HasFailure || Counters.HasFailure ? "Виявлені помилки або mismatch" :
                Counters.HasIncompleteOrConditional ? "Є умовні / unresolved / not-run результати; це не повне підтвердження" : "Виконані порівняння збігаються в межах контракту";
            ResultSummary = $"{job.Kind} · session {job.SessionId} / job {job.JobId}. {state}.\nДозволено: {string.Join(", ", result.PermittedAssumptions.DefaultIfEmpty("немає (strict)"))}. " +
                $"Використано: {string.Join(", ", result.UsedAssumptions.DefaultIfEmpty("немає"))}.\n{result.PhysicalScalingStatus}. NotFlashReady.";
            if (ChecksumSummary is not null)
                ResultSummary = "Штатна checksum — окремий scoped research результат нижче. Match означає збіг C# з виконанням, а не обов’язково Valid. NotFlashReady.";
        }
        catch (OperationCanceledException) { if (job.SessionId == SessionId) StatusText = "Перевірку скасовано; неповний результат не приєднано."; }
        catch (Exception exception) { SetError(exception, job.SessionId); }
        finally { EndJob(); }
    }

    public void SelectRunner(string path)
    {
        InvalidateSession();
        RunnerPath = Path.GetFullPath(path);
        NotifyAll();
    }

    public void Cancel() => _cancellation?.Cancel();
    public async Task RequestCloseAsync()
    {
        _disposed = true;
        Cancel();
        await _activeTask;
        Dispose();
    }
    public void Dispose() { _disposed = true; Cancel(); }

    private DesktopDocument ValidationDocument() => _pendingResult is null ? _document! :
        _document! with
        {
            Mode = DesktopAccessMode.VerifiedDerived,
            Parent = _document.Image,
            Image = _pendingResult.Image,
            Plan = _pendingPlan,
            PatchReport = _pendingResult.Report
        };

    private static void RequireCurrentInputFiles(DesktopDocument document)
    {
        var parent = document.Parent ?? document.Image;
        if (RomImage.Load(parent.SourcePath!).Hash != parent.Hash ||
            P28VtecInspector.ComputeProfileDigest(RomProfile.Load(document.Profile!.SourcePath!)) != P28VtecInspector.ComputeProfileDigest(document.Profile) ||
            P28RawThresholdEditor.ComputeBindingDigest(P28ExactBaselineBinding.Load(document.BindingPath!)) != P28RawThresholdEditor.ComputeBindingDigest(document.Binding!))
            throw new InvalidDataException("Original BIN, profile або binding змінився на диску. Результат не приєднано; відкрийте й перевірте файли знову.");
        if (document.ChecksumComposition is not null)
        {
            RequireCurrentChecksumFiles(document);
            return;
        }
        if (document.LineagePaths is { } paths &&
            (RomImage.Load(paths.OutputPath).Hash != document.Image.Hash ||
             P28RawThresholdPlan.Load(paths.PlanPath).ToJson(false) != document.Plan!.ToJson(false) ||
             P28RawThresholdPatchReport.Load(paths.ReportPath).ToJson(false) != document.PatchReport!.ToJson(false)))
            throw new InvalidDataException("Child, plan або patch report змінився на диску. Результат не приєднано.");
    }

    private static IReadOnlyList<string> Protected(DesktopDocument document) =>
        (document.InputPaths ?? []).Concat(new[] { document.Image.SourcePath, document.Parent?.SourcePath, document.Profile?.SourcePath }.OfType<string>()).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();

    private void SetDocument(DesktopDocument document)
    {
        // Publication advances the session too: a reader can finish after a job was
        // started against the previously displayed document during asynchronous I/O.
        InvalidateSession();
        _document = document;
        ResetCompensationDefinition(document);
        ClearPending();
        _allowAddEr1 = false;
        _allowAddEr3 = false;
        var bytes = document.Image.ToArray();
        HexPreview = string.Join(Environment.NewLine, bytes.Take(128).Chunk(16).Select((row, index) =>
            $"{index * 16:X4}: {string.Join(" ", row.Select(value => value.ToString("X2", CultureInfo.InvariantCulture)))}"));
        Slots = document.Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.VerifiedDerived or DesktopAccessMode.VerifiedChecksumDerived or DesktopAccessMode.Demo
            ? P28ThresholdLogic.GetSlots().Select((slot, index) => new ThresholdSlotView(slot.Id, slot.Context, slot.Pair,
                slot.PriorState, slot.Offset, bytes[document.Mode == DesktopAccessMode.Demo ? index : slot.Offset],
                document.Mode == DesktopAccessMode.Demo ? "Синтетична модель" : "Дослідницька модель; RPM не підтверджені")).ToArray() : [];
        _selectedSlot = Slots.FirstOrDefault();
        _proposedRaw = _selectedSlot?.CurrentRaw.ToString(CultureInfo.InvariantCulture) ?? "";
        UpdatePlot(_selectedSlot?.CurrentRaw);
        StatusText = "Дослідницький режим. Не для запису в ECU";
        NotifyAll();
    }

    private void UpdatePlot(byte? proposed)
    {
        PlotRows = SelectedSlot is null || proposed is null ? [] :
            Enumerable.Range(0, 256).Select(code => new P28PredicateRow((byte)code,
                P28ThresholdLogic.Evaluate(SelectedSlot.CurrentRaw, (byte)code), P28ThresholdLogic.Evaluate(proposed.Value, (byte)code))).ToArray();
    }
    private void ClearPending()
    {
        _pendingSlot = null;
        _pendingPlan = null;
        _pendingResult = null;
        foreach (var slot in Slots) slot.ProposedRaw = "";
        PreviewText = "Оберіть слот. Зміни існують тільки в пам’яті.";
    }
    private long InvalidateSession()
    {
        SessionId++;
        Cancel();
        ClearChecksumPreview();
        _resultJson = null;
        Counters = DesktopCounters.Empty;
        ChecksumSummary = null;
        ResultSummary = "Результати попереднього стану не застосовуються. Фізичні оберти не підтверджені.";
        ErrorText = "";
        return SessionId;
    }
    private void BeginJob()
    {
        _cancellation = new CancellationTokenSource();
        JobId++;
        IsBusy = true;
        _resultJson = null;
        Counters = DesktopCounters.Empty;
        ChecksumSummary = null;
        ErrorText = "";
        ResultSummary = "Поточний запуск ще не має завершеного результату. Фізичні оберти не підтверджені.";
        StatusText = "Виконується… Прогрес невідомий; можна скасувати.";
        NotifyAll();
    }
    private void EndJob()
    {
        _cancellation?.Dispose();
        _cancellation = null;
        IsBusy = false;
        if (_resultJson is null) ResultSummary = "Завершений результат не приєднано: перевірте повідомлення або повторіть запуск для поточного стану.";
        if (StatusText.StartsWith("Виконується", StringComparison.Ordinal)) StatusText = "Операцію завершено. Дослідницький режим. Не для запису в ECU";
        NotifyAll();
    }
    private void SetError(Exception exception, long session) { if (session == SessionId && !_disposed) SetError(exception.Message); }
    private void SetError(string message) { ErrorText = message; NotifyAll(); }
    private void Notify([CallerMemberName] string? property = null) => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(property));
    private void NotifyAll()
    {
        Notify("");
        OpenBinCommand.Refresh(); DemoCommand.Refresh(); BindBaselineCommand.Refresh(); OpenDerivedCommand.Refresh();
        PreviewCommand.Refresh(); RevertCommand.Refresh(); SaveCopyCommand.Refresh(); VerifyCommand.Refresh();
        ExecuteCommand.Refresh(); ProducerCommand.Refresh(); ChecksumCommand.Refresh(); CancelCommand.Refresh(); SelectRunnerCommand.Refresh(); OpenResultsCommand.Refresh();
        RefreshChecksumExportCommands();
    }

    private async Task BindFromDialogsAsync()
    {
        var profile = _dialogs.OpenFile("Оберіть research profile (bundled: " + _resources.DefaultProfilePath + ")", JsonFilter);
        if (profile is null) return;
        var binding = _dialogs.OpenFile("Оберіть чинний приватний original baseline binding", JsonFilter);
        if (binding is null) return;
        var acknowledged = _dialogs.Confirm("Підтвердити research profile", "Явно застосувати обраний profile лише якщо Core перевірить точний original binding? Це не автентифікація ECU.");
        if (acknowledged) await BindBaselineAsync(profile, binding, true);
    }
    private async Task DerivedFromDialogsAsync()
    {
        var output = _dialogs.OpenFile("Оберіть похідний BIN", BinFilter); if (output is null) return;
        var parent = _dialogs.OpenFile("Оберіть незмінений original parent BIN", BinFilter); if (parent is null) return;
        var profile = _dialogs.OpenFile("Оберіть original research profile", JsonFilter); if (profile is null) return;
        var binding = _dialogs.OpenFile("Оберіть original baseline binding", JsonFilter); if (binding is null) return;
        var plan = _dialogs.OpenFile("Оберіть M1c plan", JsonFilter); if (plan is null) return;
        var report = _dialogs.OpenFile("Оберіть M1c patch report", JsonFilter); if (report is null) return;
        if (_dialogs.Confirm("Підтвердити research profile", "Перевірити original binding та повний M1c lineage? Child не стане новим baseline."))
            await OpenDerivedAsync(output, parent, profile, binding, plan, report, true);
    }
    private async Task SaveFromDialogsAsync()
    {
        var output = _dialogs.SaveFile("Новий PC-only BIN (без перезапису)", BinFilter, "research-copy.bin"); if (output is null) return;
        var plan = _dialogs.SaveFile("Новий M1c plan", JsonFilter, "research-copy.plan.json"); if (plan is null) return;
        var report = _dialogs.SaveFile("Новий M1c patch report", JsonFilter, "research-copy.patch.json"); if (report is null) return;
        await SaveCopyAsync(new(output, plan, report));
    }
}
