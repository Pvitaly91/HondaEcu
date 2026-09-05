using System.Text.Json;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.Services;

public interface IDesktopOperations
{
    Task<DesktopValidationResult> ValidateAsync(DesktopValidationJob job, CancellationToken cancellationToken);
    Task<P28RawThresholdVerificationReport> SaveAsync(P28RawThresholdPatchResult result,
        DesktopSavePaths paths, IReadOnlyList<string> protectedPaths, CancellationToken cancellationToken);
}

public sealed class DesktopOperations : IDesktopOperations
{
    public async Task<DesktopValidationResult> ValidateAsync(DesktopValidationJob job, CancellationToken cancellationToken)
    {
        var document = job.Document;
        var parent = document.Parent ?? document.Image;
        var child = document.Mode == DesktopAccessMode.VerifiedDerived ? document.Image : null;
        if (job.Kind == DesktopValidationKind.Execute)
        {
            if (job.Assumptions.Any(item => item != P28ByteExecutionValidator.AddAssumption))
                throw new ArgumentException("M1d does not permit oki.add-er1-a.");
            var report = await P28ByteExecutionValidator.ExecuteAsync(parent, document.Profile!, document.Binding!, true,
                job.RunnerPath, job.Assumptions.Contains(P28ByteExecutionValidator.AddAssumption), child,
                document.Plan, document.PatchReport, cancellationToken: cancellationToken).ConfigureAwait(false);
            return new(DesktopCounters.From(report), JsonSerializer.Serialize(report, JsonDefaults.Create()),
                report.HasFailure, report.PermittedAssumptions, report.UsedAssumptions, "Фізичні оберти не підтверджені");
        }
        else
        {
            var scaling = JsonSerializer.SerializeToElement(P28PhysicalScaling.Analyze(null), JsonDefaults.Create());
            var report = await P28ProducerValidator.ExecuteAsync(parent, document.Profile!, document.Binding!, true,
                job.RunnerPath, job.Assumptions, child, document.Plan, document.PatchReport, scaling,
                cancellationToken: cancellationToken).ConfigureAwait(false);
            return new(DesktopCounters.From(report), JsonSerializer.Serialize(report, JsonDefaults.Create()),
                report.HasFailure, report.PermittedAssumptions, report.UsedAssumptions, "Фізичні оберти не підтверджені — symbolic/unavailable");
        }
    }

    public Task<P28RawThresholdVerificationReport> SaveAsync(P28RawThresholdPatchResult result,
        DesktopSavePaths paths, IReadOnlyList<string> protectedPaths, CancellationToken cancellationToken) =>
        Task.Run(() =>
        {
            // Cancellation is honored before publication. Once staging/publication starts,
            // finish the existing writer's rollback/readback contract rather than interrupting it.
            cancellationToken.ThrowIfCancellationRequested();
            return P28DesktopCopyWriter.Save(result, paths.OutputPath, paths.PlanPath, paths.ReportPath, protectedPaths);
        }, cancellationToken);
}
