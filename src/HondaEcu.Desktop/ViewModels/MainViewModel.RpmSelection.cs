using System.Globalization;
using System.IO;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.ViewModels;

public sealed partial class MainViewModel
{
    private sealed record RpmSelectionSnapshot(DesktopRpmJob Inputs, P28RpmSelectionReport Selection,
        P28ChecksumPreservingPlan Plan, string? SavedPath);

    private P28RpmSelectionReport? _rpmSelection;
    private string? _rpmSelectionPath;
    public AsyncCommand UseRpmCandidateCommand { get; private set; } = null!;
    public AsyncCommand SaveRpmSelectionCommand { get; private set; } = null!;
    public string RpmPlanStatus { get; private set; } = "Selection ще не передано в M1g. Новий BIN не створюється під час preview.";
    public string? RpmSelectionJson => _rpmSelection?.ToJson();
    public bool CanUseRpmCandidate => !IsBusy && Mode == Models.DesktopAccessMode.BoundBaseline &&
        _compensationLocation is not null && _rpmReport is not null && SelectedRpmCandidate is { IsBest: true, SimpleSelectable: true };
    public bool CanSaveRpmSelection => !IsBusy && _rpmSelection is not null && _checksumPreview is not null;

    private void InitializeRpmSelectionCommands()
    {
        UseRpmCandidateCommand = new(UseRpmCandidateAsync, () => CanUseRpmCandidate);
        SaveRpmSelectionCommand = new(async () =>
        {
            var path = _dialogs.SaveFile("Новий умовний selection provenance JSON — без BIN", JsonFilter, "conditional-rpm.selection.json");
            if (path is not null) await SaveRpmSelectionAsync(path);
        }, () => CanSaveRpmSelection);
    }

    public Task UseRpmCandidateAsync()
    {
        if (!CanUseRpmCandidate) { SetError("Потрібні bound original, reviewed CompensationLocation та явно обраний eligible Best-кандидат. Demo не надає authority."); return Task.CompletedTask; }
        var chosenRaw = SelectedRpmCandidate!.RawValue;
        if (!_dialogs.Confirm("Підтвердити саме raw " + chosenRaw + " для M1g?",
            $"Умовний математичний вибір, НЕ фізичні RPM.\n{SelectedSlot!.Id}\nОбраний і підтверджуваний raw: {chosenRaw} (0x{chosenRaw:X2}).\n" +
            RpmCandidateSummary + "\n\nВикористати лише цей raw в існуючому M1g plan? Жодного BIN зараз не буде записано. PcInspectionOnly / NotFlashReady.")) return Task.CompletedTask;
        var query = CurrentRpmQuery(); var report = _rpmReport!; var document = _document!; var location = _compensationLocation!;
        var inputs = CaptureRpmInputs(document, query);
        var definition = CaptureDefinition();
        BeginJob();
        _activeTask = UseRpmCandidateCoreAsync(inputs, definition, report, location, chosenRaw, _cancellation!.Token);
        return _activeTask;
    }

    private async Task UseRpmCandidateCoreAsync(DesktopRpmJob inputs, DefinitionSnapshot definition,
        P28RpmPlanningReport report, VerifiedCompensationLocation location, byte raw, CancellationToken token)
    {
        var document = inputs.Document; var query = inputs.Query; var session = inputs.SessionId;
        try
        {
            var result = await Task.Run(() =>
            {
                RequireRpmJobInputs(inputs); RequireDefinition(definition);
                var selected = P28RpmSelectionBridge.UseCandidate(document.Image, document.Profile!, document.Binding!, true,
                    query, report, raw, raw, true, location, token);
                token.ThrowIfCancellationRequested();
                RequireRpmJobInputs(inputs); RequireDefinition(definition);
                return selected;
            }, token);
            if (session != SessionId || inputs.JobId != JobId || token.IsCancellationRequested || _disposed) return;
            if (CurrentRpmQuery().QueryDigest != query.QueryDigest) throw new InvalidDataException("RPM query змінився під час планування.");
            ClearPending();
            ClearChecksumPreview();
            _proposedRaw = raw.ToString(CultureInfo.InvariantCulture);
            _checksumPreview = result.CompositionPreview;
            _checksumComposition = P28ChecksumPreservingEditor.Admit(_checksumPreview.Image, document.Image,
                document.Profile!, document.Binding!, _checksumPreview.Plan, _checksumPreview.Report, location);
            _rpmSelection = result.SelectionReport;
            _rpmSelectionPath = null;
            ChecksumExportPreview = DescribeChecksumPreview(_checksumPreview, false) + RpmExportQualification;
            RpmPlanStatus = $"Умовний raw {raw} передано в чинний M1g plan. Збережіть provenance JSON перед BIN export. Composed plan digest: {_rpmSelection.ComposedPlanDigest}.";
            _resultJson = _rpmSelection.ToJson();
            UpdatePlot(raw);
        }
        catch (OperationCanceledException) { if (session == SessionId && !_disposed) StatusText = "RPM → M1g planning скасовано."; }
        catch (Exception exception) { SetError(exception, session); }
        finally { EndJob(); }
    }

    public Task SaveRpmSelectionAsync(string path)
    {
        if (!CanSaveRpmSelection) { SetError("Спочатку явно передайте кандидата в M1g plan."); return Task.CompletedTask; }
        var query = CurrentRpmQuery(); var selection = _rpmSelection!; var plan = _checksumPreview!.Plan;
        var document = _document!;
        var snapshot = new RpmSelectionSnapshot(CaptureRpmInputs(document, query), selection, plan, _rpmSelectionPath);
        var definition = CaptureDefinition();
        var protectedPaths = Array.AsReadOnly(Protected(document).Concat(RpmProtectedPaths()).Append(definition.Path).Append(RunnerPath).ToArray());
        var fullPath = Path.GetFullPath(path);
        BeginJob();
        _activeTask = SaveRpmSelectionCoreAsync(fullPath, snapshot, definition, protectedPaths, _cancellation!.Token);
        return _activeTask;
    }

    private async Task SaveRpmSelectionCoreAsync(string path, RpmSelectionSnapshot snapshot,
        DefinitionSnapshot definition, IReadOnlyList<string> protectedPaths, CancellationToken token)
    {
        var selection = snapshot.Selection; var session = snapshot.Inputs.SessionId;
        try
        {
            await Task.Run(() =>
            {
                RequireDefinition(definition);
                RequireRpmSelection(snapshot, false, token);
                foreach (var source in protectedPaths)
                    AtomicFile.EnsureDifferentPath(path, source);
                RequireRpmJobInputs(snapshot.Inputs); RequireDefinition(definition);
                token.ThrowIfCancellationRequested();
                AtomicFile.WriteAllText(path, selection.ToJson());
                if (ReadRpmSelection(path).ComputeDigest() != selection.ComputeDigest())
                    throw new InvalidDataException("Selection provenance readback не збігається; новий JSON залишено для перевірки.");
                RequireRpmJobInputs(snapshot.Inputs); RequireDefinition(definition);
            }, token);
            if (session != SessionId || snapshot.Inputs.JobId != JobId || token.IsCancellationRequested || _disposed) return;
            if (CurrentRpmQuery().QueryDigest != snapshot.Inputs.Query.QueryDigest)
                throw new InvalidDataException("RPM query змінився під час збереження provenance.");
            _rpmSelectionPath = path;
            RpmPlanStatus = "Selection provenance збережено й перечитано. RPM залишається conditional; M1g strict checksum/export — окремі дії. Новий BIN не створено.";
            _resultJson = selection.ToJson();
        }
        catch (OperationCanceledException) { if (session == SessionId && !_disposed) StatusText = "Збереження provenance скасовано до публікації або результат не приєднано."; }
        catch (Exception exception) { SetError(exception, session); }
        finally { EndJob(); }
    }

    private string RpmExportQualification => _rpmSelection is null ? "" :
        $"\nRPM selection: {_rpmSelection.RpmStatus}; requested {_rpmSelection.RequestedRpm.Numerator}/{_rpmSelection.RequestedRpm.Denominator}; raw {_rpmSelection.ChosenRaw}.\n" +
        "Strict checksum не змінює conditional RPM / unverified hardware claims. PhysicalRpmAvailable=false; hardware NotRun.";

    private RpmSelectionSnapshot? CaptureRpmSelection(DesktopDocument document)
    {
        if (_rpmSelection is null) return null;
        if (_checksumPreview is null) throw new InvalidDataException("RPM selection втратив відповідний M1g preview.");
        return new(CaptureRpmInputs(document, CurrentRpmQuery()), _rpmSelection, _checksumPreview.Plan, _rpmSelectionPath);
    }

    private static void RequireRpmSelection(RpmSelectionSnapshot? snapshot, bool requireSaved, CancellationToken token)
    {
        if (snapshot is null) return;
        token.ThrowIfCancellationRequested();
        RequireRpmJobInputs(snapshot.Inputs);
        P28RpmSelectionBridge.ValidateSelectionAgainstPlan(snapshot.Inputs.Query, snapshot.Selection, snapshot.Plan, token);
        if (requireSaved && (snapshot.SavedPath is null || !File.Exists(snapshot.SavedPath) ||
            ReadRpmSelection(snapshot.SavedPath).ComputeDigest() != snapshot.Selection.ComputeDigest()))
            throw new InvalidDataException("Перед M1g BIN export збережіть поточний selection provenance JSON; відсутній або змінений звіт не допускається.");
    }

    private IEnumerable<string> RpmProtectedPaths() => new[] { _rpmScenarioPath, _rpmSelectionPath }.OfType<string>();
    private static P28RpmSelectionReport ReadRpmSelection(string path) =>
        P28RpmSelectionReport.Parse(new System.Text.UTF8Encoding(false, true).GetString(ReadBoundedRpmFile(path, 262144)));
    private void ClearRpmSelection()
    {
        _rpmSelection = null; _rpmSelectionPath = null;
        RpmPlanStatus = "Немає поточного RPM → M1g selection. Старий preview/report не допускає новий export.";
    }
    private void RefreshRpmSelectionCommands() { UseRpmCandidateCommand?.Refresh(); SaveRpmSelectionCommand?.Refresh(); }
}
