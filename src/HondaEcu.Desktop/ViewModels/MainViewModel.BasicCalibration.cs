using HondaEcu.Core;
using HondaEcu.Desktop.Models;
using HondaEcu.Desktop.Services;

namespace HondaEcu.Desktop.ViewModels;

public sealed partial class MainViewModel
{
    private bool _basicJobActive;
    internal DesktopDocument? BasicDocument => _document;
    internal VerifiedCompensationLocation? BasicLocation => _compensationLocation;
    internal string? BasicLocationPath => _compensationPath;
    internal void BasicDraftChanged() { Unified?.RecordDraftChange(); InvalidateSession(); NotifyAll(); }
    internal void AttachBasicDocument(DesktopDocument document) => SetDocument(document);
    internal void ClearBasicLocation()
    {
        InvalidateSession(); _compensationLocation = null; _compensationPath = null;
        CompensationStatus = "Reviewed definition не підтверджено; оберіть чинний файл."; NotifyAll();
    }
    internal void SetBasicLocation(VerifiedCompensationLocation location, string path)
    {
        InvalidateSession(); _compensationLocation = location; _compensationPath = path;
        CompensationStatus = $"Reviewed location перевірено: {location.DefinitionId}. {location.EvidenceScope}"; NotifyAll();
    }
    // The same cancellation, session/job identity and close-wait task as all legacy tabs.
    internal Task RunBasicJobAsync(Func<CancellationToken, long, long, Task> work)
    {
        if (IsBusy || _disposed) return Task.CompletedTask;
        _basicJobActive = true;
        BeginJob(); var token = _cancellation!.Token; var session = SessionId; var job = JobId;
        _activeTask = Run(); return _activeTask;
        async Task Run()
        {
            try { await work(token, session, job); }
            catch (OperationCanceledException) { if (session == SessionId) Basic.Fail("Скасовано до publication; завершений результат не заявляється."); }
            catch (Exception e) { if (session == SessionId) { Basic.Fail(e.Message); SetError(e, session); } }
            finally { _basicJobActive = false; EndJob(); }
        }
    }
    internal Task RunUnifiedJobAsync(Func<CancellationToken, long, long, Task> work)
    {
        if (IsBusy || _disposed) return Task.CompletedTask;
        _basicJobActive = true;
        BeginJob(); var token = _cancellation!.Token; var session = SessionId; var job = JobId;
        _activeTask = Run(); return _activeTask;
        async Task Run()
        {
            try { await work(token, session, job); }
            catch (OperationCanceledException) { if (session == SessionId) Unified.Fail("Скасовано до publication або завершено штатний readback/rollback."); }
            catch (Exception e) { if (session == SessionId) { Unified.Fail(e.Message); SetError(e, session); } }
            finally { _basicJobActive = false; EndJob(); }
        }
    }
    internal bool BasicCurrent(long session, long job) => !_disposed && SessionId == session && JobId == job;
    // Dialog-driven legacy document loads also hold the shared busy/close task.
    // Direct legacy APIs retain their established cancellation/invalidation behavior.
    internal Task RunDocumentLoadAsync(Func<Task> load)
    {
        if (IsBusy || _disposed) return Task.CompletedTask;
        BeginJob(); _activeTask = Run(); return _activeTask;
        async Task Run()
        {
            try { await load(); }
            finally { EndJob(); }
        }
    }
}
