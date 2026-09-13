using System.Text.Json;
using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

public sealed record P28UnifiedCalibrationEvidence(string RunnerVersion, string UpstreamCommit,
    IReadOnlyList<string> LocalSemanticFixes, string PlanDigest, P28BasicCalibrationEvidence Basic,
    P28FuelMapExportEvidence Fuel, P28IgnitionMapExportEvidence Ignition,
    IReadOnlyList<P28ChecksumExportObservation> Checksum, bool SameCompleteImagesForEverySuite,
    bool OneChecksumBatch, string JointEcuExecution);

public sealed class P28VerifiedUnifiedCalibrationExport
{
    private readonly string _evidence;
    internal P28VerifiedUnifiedCalibrationExport(P28UnifiedCalibrationPreview preview,
        P28UnifiedCalibrationEvidence evidence)
    {
        Preview = preview;
        _evidence = P28RawEditJson.Serialize(evidence, false);
    }
    public P28UnifiedCalibrationPreview Preview { get; }
    public P28UnifiedCalibrationEvidence Evidence =>
        P28RawEditJson.Parse<P28UnifiedCalibrationEvidence>(_evidence);
}

public enum P28UnifiedCalibrationStage
{
    VtecLimiterIdle,
    Fuel,
    Ignition,
    Checksum,
    EvidenceVerification,
    Publication,
    Readback
}

public static class P28UnifiedCalibrationExecution
{
    public static async Task<P28VerifiedUnifiedCalibrationExport> ValidateAsync(
        P28UnifiedCalibrationPreview preview, string runner,
        IProgress<P28UnifiedCalibrationStage>? progress = null, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = P28UnifiedCalibrationEditor.Reproduce(preview.Original, preview.Profile,
            preview.Binding, true, preview.Location, preview.Plan);
        if (preview.Plan.IsNoOp)
            throw new InvalidDataException("A no-op unified calibration plan cannot publish a firmware BIN.");
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner))
            throw new InvalidDataException("The existing compatible native runner is mandatory.");
        var runnerBytes = File.ReadAllBytes(runner);
        var (_, recheck) = ResearchOutputGroup.CaptureInputs(preview.Original, preview.Profile,
            preview.Plan.ProfileDigest, [runner]);
        var views = P28UnifiedCalibrationEditor.FamilyViews(preview);

        progress?.Report(P28UnifiedCalibrationStage.VtecLimiterIdle);
        var basic = await P28BasicCalibrationExecution.ValidateSuitesAsync(views.Basic, preview, runner,
            options: options, cancellationToken: cancellationToken).ConfigureAwait(false);
        progress?.Report(P28UnifiedCalibrationStage.Fuel);
        var fuel = await P28FuelMapExportExecution.ValidateSuitesAsync(views.Fuel, preview, runner,
            options, cancellationToken).ConfigureAwait(false);
        progress?.Report(P28UnifiedCalibrationStage.Ignition);
        var ignition = await P28IgnitionMapExportExecution.ValidateSuitesAsync(views.Ignition,
            preview, runner, options, cancellationToken).ConfigureAwait(false);

        RequireSameIdentity(basic.RunnerVersion, basic.UpstreamCommit, basic.LocalSemanticFixes,
            fuel.RunnerVersion, fuel.UpstreamCommit, fuel.LocalSemanticFixes);
        RequireSameIdentity(basic.RunnerVersion, basic.UpstreamCommit, basic.LocalSemanticFixes,
            ignition.RunnerVersion, ignition.UpstreamCommit, ignition.LocalSemanticFixes);

        progress?.Report(P28UnifiedCalibrationStage.Checksum);
        var checksumResponse = await SeededSliceProcess.ExchangeAsync(runner,
            P28NativeChecksumVerifier.CreateRequest(preview.Images), options, cancellationToken)
            .ConfigureAwait(false);
        var checksumFixes = SliceRunnerIdentity.Validate(checksumResponse.Response, "checksumBatch");
        RequireSameIdentity(basic.RunnerVersion, basic.UpstreamCommit, basic.LocalSemanticFixes,
            checksumResponse.Response.GetProperty("runnerVersion").GetString()!,
            checksumResponse.Response.GetProperty("upstreamCommit").GetString()!, checksumFixes);
        var checksum = CompareChecksum(preview.Images, checksumResponse);
        var evidence = new P28UnifiedCalibrationEvidence(basic.RunnerVersion, basic.UpstreamCommit,
            basic.LocalSemanticFixes, preview.Plan.Digest(), basic, fuel, ignition, checksum,
            true, true, "NotRun");

        progress?.Report(P28UnifiedCalibrationStage.EvidenceVerification);
        RequireEvidence(preview, evidence);
        cancellationToken.ThrowIfCancellationRequested();
        recheck();
        if (!runnerBytes.AsSpan().SequenceEqual(File.ReadAllBytes(runner)))
            throw new InvalidDataException("Runner changed during unified fresh validation.");
        return new(preview, evidence);
    }

    private static void RequireSameIdentity(string version, string upstream,
        IReadOnlyList<string> fixes, string otherVersion, string otherUpstream,
        IReadOnlyList<string> otherFixes)
    {
        if (version != otherVersion || upstream != otherUpstream || !fixes.SequenceEqual(otherFixes))
            throw new InvalidDataException("Runner identity changed between mandatory unified suites.");
    }

    internal static void RequireEvidence(P28UnifiedCalibrationPreview preview,
        P28UnifiedCalibrationEvidence evidence)
    {
        P28RawEditJson.ValidateObject(evidence);
        var plan = preview.Plan;
        if (plan.IsNoOp || evidence.PlanDigest != plan.Digest() ||
            !evidence.SameCompleteImagesForEverySuite || !evidence.OneChecksumBatch ||
            evidence.JointEcuExecution != "NotRun" || evidence.Basic.Checksum.Count != 0 ||
            evidence.Fuel.ChecksumRuns.Count != 0 || evidence.Ignition.ChecksumRuns.Count != 0)
            throw new InvalidDataException("Stale, duplicated-checksum or scope-promoted unified evidence.");
        foreach (var operation in new[] { "checksumBatch", P28FuelMapValidator.Operation,
            P28IgnitionMapValidator.Operation })
            _ = SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new
            {
                protocolVersion = 1,
                operation,
                runnerVersion = evidence.RunnerVersion,
                upstreamCommit = evidence.UpstreamCommit,
                localSemanticFixes = evidence.LocalSemanticFixes
            }), operation);
        RequireSameIdentity(evidence.RunnerVersion, evidence.UpstreamCommit,
            evidence.LocalSemanticFixes, evidence.Basic.RunnerVersion,
            evidence.Basic.UpstreamCommit, evidence.Basic.LocalSemanticFixes);
        RequireSameIdentity(evidence.RunnerVersion, evidence.UpstreamCommit,
            evidence.LocalSemanticFixes, evidence.Fuel.RunnerVersion,
            evidence.Fuel.UpstreamCommit, evidence.Fuel.LocalSemanticFixes);
        RequireSameIdentity(evidence.RunnerVersion, evidence.UpstreamCommit,
            evidence.LocalSemanticFixes, evidence.Ignition.RunnerVersion,
            evidence.Ignition.UpstreamCommit, evidence.Ignition.LocalSemanticFixes);

        var views = P28UnifiedCalibrationEditor.FamilyViews(preview);
        P28BasicCalibrationExecution.RequireEvidence(views.Basic, preview,
            evidence.Basic with { Checksum = evidence.Checksum });
        P28FuelMapExportExecution.RequireEvidence(views.Fuel, preview,
            evidence.Fuel with { ChecksumRuns = evidence.Checksum });
        P28IgnitionMapExportExecution.RequireEvidence(views.Ignition, preview,
            evidence.Ignition with { ChecksumRuns = evidence.Checksum });
        RequireCanonicalChecksumOrder(preview.Images, evidence.Checksum);
        RequireChecksumEvidence(preview.Images, evidence.Checksum);
    }

    internal static void RequireCanonicalChecksumOrder((string Id, RomImage Image)[] images,
        IReadOnlyList<P28ChecksumExportObservation> checks)
    {
        var expected = images.SelectMany(image => new[] { 0, 85, 170 }
            .Select(pattern => (image.Id, Pattern: pattern))).ToArray();
        var actual = checks.Select(check => (check.ImageKind, Pattern: check.ScratchPattern)).ToArray();
        if (!actual.SequenceEqual(expected))
            throw new InvalidDataException("Unified checksum evidence is not in canonical A/B/C and 00/55/AA order.");
    }
}
