using System.Globalization;
using System.IO;
using System.Text.Json;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.ViewModels;

public sealed partial class MainViewModel
{
    private P28RpmScenario? _rpmScenario;
    private string? _rpmScenarioPath;
    private string? _rpmScenarioFileDigest;
    private string _requestedRpm = "";
    private string _rpmQueryProvenance = "";
    private bool _rpmAllowAddEr1;
    private bool _rpmAllowAddEr3;
    private P28RpmPlanningReport? _rpmReport;

    public RelayCommand LoadRpmScenarioCommand { get; private set; } = null!;
    public RelayCommand LoadDemoRpmScenarioCommand { get; private set; } = null!;
    public RelayCommand ClearRpmScenarioCommand { get; private set; } = null!;
    public AsyncCommand PreviewRpmCommand { get; private set; } = null!;
    public RelayCommand OpenRpmReportCommand { get; private set; } = null!;
    public string RpmScenarioSummary { get; private set; } = MissingRpmInputs;
    public string RpmPreviewSummary { get; private set; } = "Числовий RPM preview недоступний без явного сценарію. Byte execution / checksum / hardware: NotRun.";
    public bool CanPreviewRpm => !IsBusy && SelectedSlot is not null && Mode is DesktopAccessMode.BoundBaseline or DesktopAccessMode.Demo;
    public bool CanSelectRpmCandidate => !IsBusy && _rpmReport is not null;
    public string RequestedRpm
    {
        get => _requestedRpm;
        set { if (_requestedRpm == value) return; InvalidateSession(); _requestedRpm = value; NotifyAll(); }
    }
    public string RpmQueryProvenance
    {
        get => _rpmQueryProvenance;
        set { if (_rpmQueryProvenance == value) return; InvalidateSession(); _rpmQueryProvenance = value; NotifyAll(); }
    }
    public bool RpmAllowAddEr1
    {
        get => _rpmAllowAddEr1;
        set { if (_rpmAllowAddEr1 == value) return; InvalidateSession(); _rpmAllowAddEr1 = value; NotifyAll(); }
    }
    public bool RpmAllowAddEr3
    {
        get => _rpmAllowAddEr3;
        set { if (_rpmAllowAddEr3 == value) return; InvalidateSession(); _rpmAllowAddEr3 = value; NotifyAll(); }
    }

    private const string MissingRpmInputs = "Числові RPM: unavailable. Потрібні clockHz [Hz], timerClockDivisor [1], eventsPerCrankRev [events/crank-revolution], eventsPerSample [events/sample], requested RPM [crank-revolutions/minute], точні додатні N/D та provenance. Жодних фізичних defaults.";

    private void InitializeRpmCommands()
    {
        LoadRpmScenarioCommand = new(() =>
        {
            var path = _dialogs.OpenFile("Явний M1e scaling JSON — лише unverified analyst inputs", JsonFilter);
            if (path is not null) LoadRpmScenario(path);
        }, () => CanPreviewRpm);
        LoadDemoRpmScenarioCommand = new(LoadDemoRpmScenario, () => !IsBusy && Mode == DesktopAccessMode.Demo);
        ClearRpmScenarioCommand = new(() => { InvalidateSession(); ResetRpmScenario(); NotifyAll(); }, () => !IsBusy && _rpmScenario is not null);
        PreviewRpmCommand = new(PreviewRpmAsync, () => CanPreviewRpm);
        OpenRpmReportCommand = new(() => _dialogs.ShowStructuredResult("Умовний математичний RPM preview — не виконання", RpmReportJson!),
            () => !IsBusy && _rpmReport is not null);
        InitializeRpmSelectionCommands();
    }

    public string? RpmReportJson => _rpmReport is null ? null : JsonSerializer.Serialize(_rpmReport, JsonDefaults.Create());

    public void LoadRpmScenario(string path)
    {
        InvalidateSession();
        ResetRpmScenario();
        try
        {
            if (!CanPreviewRpm) throw new InvalidOperationException("Потрібен bound original або явний Demo; child не є новим baseline.");
            var fullPath = Path.GetFullPath(path);
            var before = RpmScenarioFileDigest(fullPath);
            var scenario = P28RpmScenario.Load(fullPath);
            if (RpmScenarioFileDigest(fullPath) != before) throw new InvalidDataException("Scaling JSON змінився під час читання.");
            _rpmScenario = scenario;
            _rpmScenarioPath = fullPath;
            _rpmScenarioFileDigest = before;
            RpmScenarioSummary = DescribeRpmScenario(scenario, Mode == DesktopAccessMode.Demo);
        }
        catch (Exception exception) { SetError(exception.Message); }
        NotifyAll();
    }

    public void LoadDemoRpmScenario()
    {
        if (IsBusy || Mode != DesktopAccessMode.Demo) { SetError("Вигаданий сценарій доступний лише після явного вибору Demo."); return; }
        InvalidateSession();
        ResetRpmScenario();
        _rpmScenario = P28RpmScenario.Parse(DemoRpmScenarioJson);
        RpmScenarioSummary = DescribeRpmScenario(_rpmScenario, true);
        NotifyAll();
    }

    private static string DescribeRpmScenario(P28RpmScenario scenario, bool demo)
    {
        var rows = scenario.Quantities.Select(item => $"{item.Key}: {item.Value.Numerator}/{item.Value.Denominator} {item.Value.Unit}; {item.Value.Provenance}; label={item.Value.Evidence} (unverified claim)");
        var legacy = scenario.LegacyRequestedRpm;
        return (demo ? "DEMO / ВИГАДАНИЙ СЦЕНАРІЙ — не апаратна конфігурація Honda.\n" : "Analyst-supplied scenario — не виміряна конфігурація baseline.\n") +
            string.Join("\n", rows) + "\nLegacy запит: " + (legacy is null ? "не заданий" : $"{legacy.Numerator}/{legacy.Denominator} {legacy.Unit}; {legacy.Provenance}; {legacy.Evidence}") +
            $"\nConfiguration compatibility: {scenario.ConfigurationCompatibility}.\nScenario digest: {scenario.Digest}. Hardware claims не перевірені. PhysicalRpmAvailable=false.";
    }

    private P28RpmQuery CurrentRpmQuery()
    {
        var slot = SelectedSlot ?? throw new InvalidOperationException("Оберіть нейтральний слот.");
        var assumptions = new List<string>();
        if (RpmAllowAddEr1) assumptions.Add(P28ProducerModel.AddEr1Assumption);
        if (RpmAllowAddEr3) assumptions.Add(P28ByteExecutionValidator.AddAssumption);
        return P28RpmQuery.Create(_rpmScenario, slot.Id, slot.CurrentRaw,
            string.IsNullOrEmpty(RequestedRpm) ? null : RequestedRpm,
            string.IsNullOrEmpty(RpmQueryProvenance) ? null : RpmQueryProvenance, assumptions);
    }

    public Task PreviewRpmAsync()
    {
        if (!CanPreviewRpm) { SetError("RPM planning потребує bound original або явного Demo; без scaling залишається unavailable."); return Task.CompletedTask; }
        try
        {
            var query = CurrentRpmQuery();
            InvalidateSession();
            BeginJob();
            var job = new DesktopRpmJob(SessionId, JobId, _document!, query, _rpmScenarioPath, _rpmScenarioFileDigest);
            _activeTask = PreviewRpmCoreAsync(job, _cancellation!.Token);
            return _activeTask;
        }
        catch (Exception exception) { SetError(exception.Message); return Task.CompletedTask; }
    }

    private async Task PreviewRpmCoreAsync(DesktopRpmJob job, CancellationToken token)
    {
        try
        {
            var report = await Task.Run(async () =>
            {
                RequireRpmJobInputs(job);
                var result = await _operations.PreviewRpmAsync(job, token).ConfigureAwait(false);
                token.ThrowIfCancellationRequested();
                RequireRpmJobInputs(job);
                return result;
            }, token);
            if (job.SessionId != SessionId || job.JobId != JobId || token.IsCancellationRequested || _disposed) return;
            if (CurrentRpmQuery().QueryDigest != job.Query.QueryDigest || report.Query.QueryDigest != job.Query.QueryDigest)
                throw new InvalidDataException("Query/scenario/model result не відповідає поточному snapshot.");
            _rpmReport = report;
            _resultJson = RpmReportJson;
            UpdateRpmDisplays();
            ResultSummary = "M1h: лише умовна математика. Byte execution / checksum / hardware: NotRun. PhysicalRpmAvailable=false. NotFlashReady.";
        }
        catch (OperationCanceledException) { if (job.SessionId == SessionId && !_disposed) StatusText = "RPM preview скасовано; неповний результат не приєднано."; }
        catch (Exception exception) { SetError(exception, job.SessionId); }
        finally { EndJob(); }
    }

    private static void RequireRpmJobInputs(DesktopRpmJob job)
    {
        if (job.Document.Mode != DesktopAccessMode.Demo) RequireCurrentInputFiles(job.Document);
        if (job.ScenarioPath is not null && RpmScenarioFileDigest(job.ScenarioPath) != job.ScenarioFileDigest)
            throw new InvalidDataException("Scaling JSON змінився після завантаження. Завантажте сценарій знову; старий preview не застосовується.");
    }

    // Called on the UI thread immediately before BeginJob. Workers only receive
    // this immutable snapshot, never callbacks that read live ViewModel fields.
    private DesktopRpmJob CaptureRpmInputs(DesktopDocument document, P28RpmQuery query) =>
        new(SessionId, checked(JobId + 1), document, query, _rpmScenarioPath, _rpmScenarioFileDigest);

    private static string RpmScenarioFileDigest(string path) => HashUtilities.Sha256(ReadBoundedRpmFile(path, 65536));

    private static byte[] ReadBoundedRpmFile(string path, int maximumBytes)
    {
        using var stream = File.OpenRead(path);
        if (stream.Length > maximumBytes) throw new InvalidDataException("RPM scenario/provenance file перевищує дозволений розмір.");
        var bytes = new byte[maximumBytes + 1];
        var count = 0;
        while (count < bytes.Length)
        {
            var read = stream.Read(bytes, count, bytes.Length - count);
            if (read == 0) break;
            count += read;
        }
        if (count > maximumBytes) throw new InvalidDataException("RPM scenario/provenance file виріс понад дозволений розмір.");
        return bytes[..count];
    }

    private void ResetRpmScenario()
    {
        _rpmScenario = null; _rpmScenarioPath = null; _rpmScenarioFileDigest = null;
        _requestedRpm = ""; _rpmQueryProvenance = ""; _rpmAllowAddEr1 = false; _rpmAllowAddEr3 = false;
        RpmScenarioSummary = MissingRpmInputs;
    }

    private void ClearRpmPreview()
    {
        _rpmReport = null;
        RpmPreviewSummary = "Попередній RPM preview не застосовується до поточного стану. Byte execution / checksum / hardware: NotRun.";
        ClearRpmSelection();
        ClearRpmDisplays();
    }

    private void RefreshRpmCommands()
    {
        LoadRpmScenarioCommand?.Refresh(); LoadDemoRpmScenarioCommand?.Refresh(); ClearRpmScenarioCommand?.Refresh();
        PreviewRpmCommand?.Refresh(); OpenRpmReportCommand?.Refresh(); RefreshRpmSelectionCommands();
    }

    // Never loaded implicitly, and never available for a real BIN. Every quantity is explicitly invented or claimed.
    internal const string DemoRpmScenarioJson = """
        {"formatVersion":1,"scope":"uniform-normal-intervals","quantities":{
          "clockHz":{"numerator":"1000000","denominator":"1","unit":"Hz","provenance":"Invented demonstration clock; NOT measured hardware","evidence":"analyst-supplied"},
          "timerClockDivisor":{"numerator":"32","denominator":"1","unit":"1","provenance":"Explicit selector scenario; not hardware authentication","evidence":"source-derived-claim"},
          "eventsPerCrankRev":{"numerator":"3","denominator":"1","unit":"events/crank-revolution","provenance":"Invented demonstration geometry; NOT established Honda sensor","evidence":"analyst-supplied"},
          "eventsPerSample":{"numerator":"1","denominator":"1","unit":"events/sample","provenance":"Explicit uniform normal interval assumption","evidence":"analyst-supplied"},
          "rpm":{"numerator":"3000","denominator":"1","unit":"crank-revolutions/minute","provenance":"Invented demonstration query, not an engine recommendation","evidence":"analyst-supplied"}
        }}
        """;
}
