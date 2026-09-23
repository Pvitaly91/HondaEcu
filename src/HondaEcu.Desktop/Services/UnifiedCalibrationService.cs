using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.Services;

public sealed record UnifiedPreviewResult(P28UnifiedCalibrationPreview Preview, P28UnifiedCalibrationPlan Plan);
public sealed record UnifiedEvidenceSummary(string Suite, int Completed, int Required, string Unit);
public sealed record UnifiedExportResult(P28UnifiedCalibrationVerification Readback,
    IReadOnlyList<UnifiedEvidenceSummary> Fresh, DesktopSavePaths Paths, string PlanDigest,
    TimeSpan ValidationTime, TimeSpan PublicationAndReadbackTime, long PeakWorkingSet);

public sealed class UnifiedCalibrationInput
{
    private readonly Dictionary<string, (long Bound, long Length, string Hash)> _files;
    private UnifiedCalibrationInput(DesktopDocument document, VerifiedCompensationLocation location,
        Dictionary<string, (long Bound, long Length, string Hash)> files)
    { Document = document; Location = location; _files = files; }
    public DesktopDocument Document { get; }
    public VerifiedCompensationLocation Location { get; }
    public IEnumerable<string> Paths => _files.Keys;

    private static (long Length, string Hash) Fingerprint(string path, long bound)
    {
        using var stream = File.OpenRead(path);
        if (stream.Length > bound) throw new InvalidDataException($"Input {Path.GetFileName(path)} exceeds its typed bound.");
        return (stream.Length, Convert.ToHexString(SHA256.HashData(stream)));
    }
    public void Recheck()
    {
        foreach (var (path, expected) in _files)
            if (Fingerprint(path, expected.Bound) != (expected.Length, expected.Hash))
                throw new InvalidDataException("Input змінився після snapshot: " + Path.GetFileName(path));
    }
    private static long Bound(string path, DesktopDocument document, string locationPath,
        string? runnerPath, ISet<string> imported)
    {
        static bool Same(string path, string? other) => other is not null &&
            Path.GetFullPath(path).Equals(Path.GetFullPath(other), StringComparison.OrdinalIgnoreCase);
        if (document.UnifiedLineagePaths is { } tuple)
        {
            if (Same(path, tuple.PlanPath)) return P28UnifiedCalibrationPlan.MaximumBytes;
            if (Same(path, tuple.ReceiptPath)) return P28UnifiedCalibrationReceipt.MaximumBytes;
            if (Same(path, tuple.ChildPath) || Same(path, tuple.OriginalPath)) return P28NativeChecksumArithmetic.RomSize;
        }
        if (Same(path, document.Image.SourcePath) || Same(path, document.Parent?.SourcePath)) return P28NativeChecksumArithmetic.RomSize;
        if (Same(path, runnerPath)) return 64L * 1024 * 1024;
        if (imported.Contains(path)) return P28UnifiedCalibrationSettings.MaximumBytes;
        if (Same(path, document.Profile?.SourcePath) || Same(path, document.BindingPath) || Same(path, locationPath)) return 1024L * 1024;
        // Earlier lineage input remains protected; it cannot silently become a typed M2e receipt.
        return 1024L * 1024;
    }
    public static UnifiedCalibrationInput Capture(DesktopDocument document, string locationPath,
        VerifiedCompensationLocation expected, string? runner = null, IEnumerable<string>? imported = null)
    {
        if (document.Mode != DesktopAccessMode.BoundBaseline || document.Profile is null || document.Binding is null)
            throw new InvalidDataException("Потрібен bound original; demo, unknown BIN і child не є export baseline.");
        var importedPaths = (imported ?? []).Select(Path.GetFullPath).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var paths = (document.InputPaths ?? []).Concat(new[] { document.Image.SourcePath!, document.Profile.SourcePath!, document.BindingPath!, locationPath })
            .Concat(runner is null ? [] : [runner]).Concat(importedPaths).Select(Path.GetFullPath)
            .Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        var files = paths.ToDictionary(path => path, path =>
        {
            var bound = Bound(path, document, locationPath, runner, importedPaths);
            var fingerprint = Fingerprint(path, bound);
            return (bound, fingerprint.Length, fingerprint.Hash);
        }, StringComparer.OrdinalIgnoreCase);
        if (RomImage.Load(document.Image.SourcePath!).Hash != document.Image.Hash ||
            P28VtecInspector.ComputeProfileDigest(RomProfile.Load(document.Profile.SourcePath!)) != P28VtecInspector.ComputeProfileDigest(document.Profile) ||
            P28RawThresholdEditor.ComputeBindingDigest(P28ExactBaselineBinding.Load(document.BindingPath!)) != P28RawThresholdEditor.ComputeBindingDigest(document.Binding))
            throw new InvalidDataException("Original/profile/binding змінився після відкриття.");
        var location = P28ChecksumPreservingEditor.LoadLocation(locationPath);
        if (location.DefinitionDigest != expected.DefinitionDigest)
            throw new InvalidDataException("Reviewed compensation definition змінилася.");
        var result = new UnifiedCalibrationInput(document, location, files); result.Recheck(); return result;
    }
    public static byte[] ReadSettings(string path) => BasicCalibrationInput.ReadBounded(path, P28UnifiedCalibrationSettings.MaximumBytes);
    public static DesktopDocument Inspect(string childPath, string originalPath, string profilePath,
        string bindingPath, string locationPath, string planPath, string receiptPath)
    {
        var tuple = new UnifiedLineagePaths(Path.GetFullPath(childPath), Path.GetFullPath(originalPath),
            Path.GetFullPath(profilePath), Path.GetFullPath(bindingPath), Path.GetFullPath(locationPath),
            Path.GetFullPath(planPath), Path.GetFullPath(receiptPath));
        var paths = tuple.All.ToArray();
        long BoundByRole(string path) => path == tuple.PlanPath ? P28UnifiedCalibrationPlan.MaximumBytes :
            path == tuple.ReceiptPath ? P28UnifiedCalibrationReceipt.MaximumBytes :
            path == tuple.ChildPath || path == tuple.OriginalPath ? P28NativeChecksumArithmetic.RomSize :
            P28UnifiedCalibrationSettings.MaximumBytes;
        var before = paths.ToDictionary(path => path, path => Fingerprint(path, BoundByRole(path)), StringComparer.OrdinalIgnoreCase);
        var child = RomImage.Load(tuple.ChildPath); var original = RomImage.Load(tuple.OriginalPath);
        var profile = RomProfile.Load(tuple.ProfilePath); var binding = P28ExactBaselineBinding.Load(tuple.BindingPath);
        var location = P28ChecksumPreservingEditor.LoadLocation(tuple.LocationPath);
        var plan = P28UnifiedCalibrationPlan.Load(tuple.PlanPath); var receipt = P28UnifiedCalibrationReceipt.Load(tuple.ReceiptPath);
        var inspection = P28UnifiedCalibrationWriter.InspectDerived(child, original, profile, binding, location, plan, receipt);
        foreach (var path in paths) if (before[path] != Fingerprint(path, BoundByRole(path)))
                throw new InvalidDataException("M2e lineage tuple змінився під час independent readback.");
        return new(DesktopAccessMode.VerifiedUnifiedDerived, child, original, profile, binding,
            InputPaths: paths, BindingPath: tuple.BindingPath, CompensationDefinitionPath: tuple.LocationPath,
            UnifiedPlan: plan, UnifiedInspection: inspection, UnifiedLineagePaths: tuple);
    }
}

public interface IUnifiedCalibrationOperations
{
    Task<UnifiedPreviewResult> PreviewAsync(UnifiedCalibrationInput input, P28UnifiedCalibrationSettings settings, CancellationToken token);
    Task<UnifiedExportResult> ExportAsync(UnifiedCalibrationInput input, UnifiedPreviewResult preview,
        string runner, DesktopSavePaths paths, IProgress<P28UnifiedCalibrationStage> progress, CancellationToken token);
}

public sealed class UnifiedCalibrationService : IUnifiedCalibrationOperations
{
    public Task<UnifiedPreviewResult> PreviewAsync(UnifiedCalibrationInput input,
        P28UnifiedCalibrationSettings settings, CancellationToken token) => Task.Run(() =>
    {
        token.ThrowIfCancellationRequested(); input.Recheck(); var d = input.Document;
        var preview = P28UnifiedCalibrationEditor.Preview(d.Image, d.Profile!, d.Binding!, true, input.Location, settings);
        var plan = preview.Plan; // The expensive defensive parse is taken exactly once for presentation.
        token.ThrowIfCancellationRequested(); input.Recheck(); return new UnifiedPreviewResult(preview, plan);
    }, token);

    public Task<UnifiedExportResult> ExportAsync(UnifiedCalibrationInput input, UnifiedPreviewResult preview,
        string runner, DesktopSavePaths paths, IProgress<P28UnifiedCalibrationStage> progress, CancellationToken token) => Task.Run(async () =>
    {
        BasicCalibrationInput.ProtectDestinations([paths.OutputPath, paths.PlanPath, paths.ReportPath], input.Paths.Append(runner));
        input.Recheck(); var d = input.Document;
        var reproduced = P28UnifiedCalibrationEditor.Reproduce(d.Image, d.Profile!, d.Binding!, true, input.Location, preview.Plan);
        if (reproduced.Plan.Digest() != preview.Plan.Digest()) throw new InvalidDataException("Stale unified plan.");
        var timer = Stopwatch.StartNew();
        var capability = await P28UnifiedCalibrationExecution.ValidateAsync(reproduced, runner, progress,
            cancellationToken: token).ConfigureAwait(false);
        var validation = timer.Elapsed;
        input.Recheck(); token.ThrowIfCancellationRequested();
        var evidence = capability.Evidence; // Do not bind the defensive heavy getter to XAML.
        UnifiedEvidenceSummary[] suites =
        [
            new("VTEC", evidence.Basic.VtecThresholdPrefix.Rows.Count,
                evidence.Basic.VtecThresholdPrefix.ComparedCasesPerImage * 3, "cases A/B/C"),
            new("Fixed limiter", evidence.Basic.LimiterAdaptive.FixedRuns.Sum(run => run.StrictMatches),
                evidence.Basic.LimiterAdaptive.FixedRuns.Sum(run => run.Requested), "calls"),
            new("Adaptive limiter", evidence.Basic.LimiterAdaptive.AdaptiveRuns.Sum(run => run.StrictMatches),
                evidence.Basic.LimiterAdaptive.AdaptiveRuns.Sum(run => run.Requested), "calls"),
            new("Idle", evidence.Basic.Idle.Runs.Sum(run => run.StrictMatches),
                evidence.Basic.Idle.Runs.Sum(run => run.Requested), "calls"),
            new("Fuel", evidence.Fuel.Runs.Sum(run => run.StrictMatches),
                evidence.Fuel.Runs.Sum(run => run.Requested), "calls"),
            new("Ignition main", evidence.Ignition.MainRuns.Sum(run => run.StrictMatches),
                evidence.Ignition.MainRuns.Sum(run => run.Requested), "calls"),
            new("Ignition factors", evidence.Ignition.FactorRuns.Sum(run => run.StrictMatches),
                evidence.Ignition.FactorRuns.Sum(run => run.Requested), "calls"),
            new("Checksum", evidence.Checksum.Sum(run => run.Invocations),
                evidence.Checksum.Count * 512, "invocations")
        ];
        timer.Restart();
        var readback = P28UnifiedCalibrationWriter.Save(capability, paths.OutputPath, paths.PlanPath,
            paths.ReportPath, progress, input.Paths.Append(runner), token);
        if (!readback.IsValid || readback.PlanDigest != preview.Plan.Digest())
            throw new InvalidDataException("Unified publication/readback did not match the live plan.");
        return new UnifiedExportResult(readback, suites, paths, readback.PlanDigest,
            validation, timer.Elapsed, Process.GetCurrentProcess().PeakWorkingSet64);
    }, token);
}
