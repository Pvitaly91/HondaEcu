using System.IO;
using System.Text;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.Services;

public sealed record BasicEvidenceSummary(string Suite, int Completed, int Required, string Unit);
public sealed class BasicExportResult
{
    internal BasicExportResult(P28VerifiedBasicCalibrationExport live, P28BasicCalibrationVerification readback,
        IReadOnlyList<BasicEvidenceSummary> freshExecution, IReadOnlyList<string> witnesses, DesktopSavePaths paths)
    {
        if (!readback.IsValid || readback.PlanDigest != live.Preview.Plan.Digest()) throw new InvalidDataException("Live/readback identity mismatch.");
        Readback = readback; FreshExecution = Array.AsReadOnly(freshExecution.ToArray());
        Witnesses = Array.AsReadOnly(witnesses.ToArray()); Paths = paths;
    }
    public P28BasicCalibrationVerification Readback { get; }
    public IReadOnlyList<BasicEvidenceSummary> FreshExecution { get; }
    public IReadOnlyList<string> Witnesses { get; }
    public DesktopSavePaths Paths { get; }
}

/// <summary>Exact disk snapshots, not serialized authority. Only explicitly supplied paths are read.</summary>
public sealed class BasicCalibrationInput
{
    private readonly IReadOnlyDictionary<string, byte[]> _files;
    private BasicCalibrationInput(DesktopDocument document, VerifiedCompensationLocation location, IReadOnlyDictionary<string, byte[]> files)
    { Document = document; Location = location; _files = files; }
    public DesktopDocument Document { get; }
    public VerifiedCompensationLocation Location { get; }
    public IEnumerable<string> Paths => _files.Keys;
    public void Recheck()
    {
        foreach (var (path, bytes) in _files)
            if (!bytes.AsSpan().SequenceEqual(ReadBounded(path, bytes.Length))) throw new InvalidDataException("Input змінився: відкрийте матеріали та побудуйте preview заново.");
    }
    public static byte[] ReadBounded(string path, int bound)
    {
        using var stream = File.OpenRead(path);
        if (stream.Length > bound) throw new InvalidDataException("Input перевищує явний розмір контракту.");
        var bytes = new byte[(int)stream.Length]; stream.ReadExactly(bytes);
        if (stream.ReadByte() != -1) throw new InvalidDataException("Input змінив розмір під час читання.");
        return bytes;
    }
    public static BasicCalibrationInput Capture(DesktopDocument doc, string locationPath, VerifiedCompensationLocation expected,
        string? runner = null, IReadOnlyDictionary<string, byte[]>? imported = null)
    {
        if (doc.Mode != DesktopAccessMode.BoundBaseline || doc.Profile is null || doc.Binding is null)
            throw new InvalidDataException("Потрібен підтверджений original, не child/demo/unknown BIN.");
        var paths = (doc.InputPaths ?? []).Concat(new[] { doc.Image.SourcePath!, doc.Profile.SourcePath!, doc.BindingPath!, locationPath })
            .Concat(runner is null ? [] : new[] { runner }).Concat(imported?.Keys ?? []).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        var files = paths.ToDictionary(p => p, p => ReadBounded(p, p == runner ? 64 * 1024 * 1024 :
            doc.BasicPlan is not null && p == doc.InputPaths?.LastOrDefault() ? P28BasicCalibrationReceipt.MaximumBytes : 1024 * 1024), StringComparer.OrdinalIgnoreCase);
        if (imported is not null) foreach (var pair in imported)
                if (!files[pair.Key].AsSpan().SequenceEqual(pair.Value)) throw new InvalidDataException("Імпортований settings input змінився.");
        var location = P28ChecksumPreservingEditor.ParseLocation(new UTF8Encoding(false, true).GetString(files[locationPath]).TrimStart('\uFEFF'));
        if (!files[doc.Image.SourcePath!].AsSpan().SequenceEqual(doc.Image.ToArray()) ||
            P28VtecInspector.ComputeProfileDigest(RomProfile.Load(doc.Profile.SourcePath!)) != P28VtecInspector.ComputeProfileDigest(doc.Profile) ||
            P28RawThresholdEditor.ComputeBindingDigest(P28ExactBaselineBinding.Load(doc.BindingPath!)) != P28RawThresholdEditor.ComputeBindingDigest(doc.Binding) ||
            location.DefinitionDigest != expected.DefinitionDigest)
            throw new InvalidDataException("Original/profile/binding/location змінився після вибору.");
        var input = new BasicCalibrationInput(doc, location, files); input.Recheck(); return input;
    }
    public static void ProtectDestinations(IEnumerable<string> destinations, IEnumerable<string> sources)
    {
        var paths = destinations.Select(Path.GetFullPath).ToArray();
        for (var i = 0; i < paths.Length; i++)
        {
            foreach (var other in paths.Skip(i + 1).Concat(sources)) AtomicFile.EnsureDifferentPath(paths[i], other);
            if (File.Exists(paths[i]) || Directory.Exists(paths[i])) throw new IOException("Потрібні нові різні output paths, без перезапису.");
            for (string? parent = paths[i]; parent is not null; parent = Path.GetDirectoryName(parent))
                if ((File.Exists(parent) || Directory.Exists(parent)) && File.GetAttributes(parent).HasFlag(FileAttributes.ReparsePoint))
                    throw new IOException("Output paths не можуть проходити через links/junctions.");
        }
    }
}

public interface IBasicCalibrationOperations
{
    Task<P28BasicCalibrationPreview> PreviewAsync(BasicCalibrationInput input, P28BasicCalibrationSettings settings, CancellationToken token);
    Task<BasicExportResult> ExportAsync(BasicCalibrationInput input, P28BasicCalibrationPreview preview, string runner,
        DesktopSavePaths paths, IProgress<P28BasicCalibrationStage> progress, CancellationToken token);
}

public sealed class BasicCalibrationService : IBasicCalibrationOperations
{
    public Task<P28BasicCalibrationPreview> PreviewAsync(BasicCalibrationInput input, P28BasicCalibrationSettings settings, CancellationToken token) =>
        Task.Run(() =>
        {
            token.ThrowIfCancellationRequested(); input.Recheck(); var d = input.Document;
            var p = P28BasicCalibrationEditor.Preview(d.Image, d.Profile!, d.Binding!, true, input.Location, settings);
            token.ThrowIfCancellationRequested(); input.Recheck(); return p;
        }, token);
    public Task<BasicExportResult> ExportAsync(BasicCalibrationInput input, P28BasicCalibrationPreview preview, string runner,
        DesktopSavePaths paths, IProgress<P28BasicCalibrationStage> progress, CancellationToken token) => Task.Run(async () =>
    {
        BasicCalibrationInput.ProtectDestinations([paths.OutputPath, paths.PlanPath, paths.ReportPath], input.Paths.Append(runner));
        input.Recheck(); var d = input.Document;
        var reproduced = P28BasicCalibrationEditor.Reproduce(d.Image, d.Profile!, d.Binding!, true, input.Location, preview.Plan);
        var capability = await P28BasicCalibrationExecution.ValidateAsync(reproduced, runner, cancellationToken: token, progress: progress).ConfigureAwait(false);
        input.Recheck(); token.ThrowIfCancellationRequested();
        var evidence = capability.Evidence;
        BasicEvidenceSummary[] summaries = [new("VTEC threshold prefix", evidence.VtecThresholdPrefix.Rows.Count,
            evidence.VtecThresholdPrefix.ComparedCasesPerImage * 3, "cases A/B/C"),
            new("Fixed limiter", evidence.LimiterAdaptive.FixedRuns.Sum(r => r.StrictMatches), evidence.LimiterAdaptive.FixedRuns.Sum(r => r.Requested), "image/scratch calls"),
            new("Adaptive limiter", evidence.LimiterAdaptive.AdaptiveRuns.Sum(r => r.StrictMatches), evidence.LimiterAdaptive.AdaptiveRuns.Sum(r => r.Requested), "image/scratch calls"),
            new("Idle target/error", evidence.Idle.Runs.Sum(r => r.StrictMatches), evidence.Idle.Runs.Sum(r => r.Requested), "image/scratch calls"),
            new("Checksum", evidence.Checksum.Sum(r => r.Invocations), evidence.Checksum.Count * 512, "invocations; 512/sequence")];
        var witnesses = evidence.VtecThresholdPrefix.Witnesses.Select(w => $"VTEC {w.SlotId}: code {w.Code}, bits {w.OldBits} → {w.NewBits}")
            .Concat(evidence.LimiterAdaptive.Witnesses.Select(w => $"{w.Group}: threshold {w.OldThreshold} → {w.NewThreshold}; request {w.OldRequest} → {w.NewRequest}"))
            .Concat(evidence.Idle.Witnesses.Select(w => $"Idle {w.Table}: target {w.OldTarget} → {w.NewTarget}; error {w.OldError} → {w.NewError}; sign {w.OldSign} → {w.NewSign}")).ToArray();
        var readback = P28BasicCalibrationWriter.Save(capability, paths.OutputPath, paths.PlanPath, paths.ReportPath, progress, input.Paths.Append(runner), token);
        if (!readback.IsValid) throw new InvalidDataException("Publication/readback не підтверджені.");
        // Do not convert successful publication into cancellation because Cancel arrived after publication began.
        return new BasicExportResult(capability, readback, summaries, witnesses, paths);
    }, token);

    public static DesktopDocument Inspect(string childPath, string originalPath, string profilePath, string bindingPath,
        string locationPath, string planPath, string receiptPath)
    {
        string[] paths = [childPath, originalPath, profilePath, bindingPath, locationPath, planPath, receiptPath];
        var snapshots = paths.Distinct().ToDictionary(p => p, p => BasicCalibrationInput.ReadBounded(p,
            p == receiptPath ? P28BasicCalibrationReceipt.MaximumBytes : p == planPath ? P28BasicCalibrationPlan.MaximumBytes : 1024 * 1024));
        var child = RomImage.FromBytes(snapshots[childPath], Path.GetFullPath(childPath));
        var original = RomImage.FromBytes(snapshots[originalPath], Path.GetFullPath(originalPath));
        var profile = RomProfile.Load(profilePath); var binding = P28ExactBaselineBinding.Load(bindingPath);
        var location = P28ChecksumPreservingEditor.LoadLocation(locationPath);
        var plan = P28BasicCalibrationPlan.Load(planPath); var receipt = P28BasicCalibrationReceipt.Load(receiptPath);
        var inspected = P28BasicCalibrationWriter.InspectDerived(child, original, profile, binding, location, plan, receipt);
        foreach (var (path, bytes) in snapshots)
            if (!bytes.AsSpan().SequenceEqual(BasicCalibrationInput.ReadBounded(path, bytes.Length))) throw new InvalidDataException("Inspection inputs змінилися.");
        return new(DesktopAccessMode.VerifiedBasicDerived, child, original, profile, binding,
            InputPaths: paths.Select(Path.GetFullPath).ToArray(), BindingPath: Path.GetFullPath(bindingPath),
            CompensationDefinitionPath: Path.GetFullPath(locationPath), BasicPlan: plan, BasicInspection: inspected);
    }
}
