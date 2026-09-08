using System.Text.Json;
using static HondaEcu.Core.P28BasicCalibrationEditor;
using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

public sealed record P28BasicLimiterEvidence(string CorpusId, IReadOnlyList<P28FixedLimiterRun> FixedRuns,
    IReadOnlyList<P28AdaptiveBaseRun> AdaptiveRuns, IReadOnlyList<P28CombinedLimiterWitness> Witnesses);
public sealed record P28BasicIdleEvidence(string CorpusId, IReadOnlyList<P28IdleTableRun> Runs,
    IReadOnlyList<P28IdleTableWitness> Witnesses, IReadOnlyList<P28IdleCellEffect> CellEffects);
public sealed record P28BasicCalibrationEvidence(string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string PlanDigest, P28BasicVtecEvidence VtecThresholdPrefix, P28BasicLimiterEvidence LimiterAdaptive,
    P28BasicIdleEvidence Idle, IReadOnlyList<P28ChecksumExportObservation> Checksum,
    string VtecFullChainP1PhysicalOutput, string JointEcuExecution);
public sealed class P28VerifiedBasicCalibrationExport
{
    private readonly string _evidence;
    internal P28VerifiedBasicCalibrationExport(P28BasicCalibrationPreview preview, P28BasicCalibrationEvidence evidence)
    { Preview = preview; _evidence = P28RawEditJson.Serialize(evidence, false); }
    public P28BasicCalibrationPreview Preview { get; }
    public P28BasicCalibrationEvidence Evidence => P28RawEditJson.Parse<P28BasicCalibrationEvidence>(_evidence);
}
internal static class P28BasicCalibrationCorpus
{
    internal const string LimiterControl = "basic-unchanged-limiter-source-and-state-controls-v1";
    internal const string IdleControl = "basic-unchanged-idle-selectors-and-target-controls-v1";
    internal static bool LimiterChanged(P28BasicCalibrationPlan p) => LimiterGroups(p).Any(g => g.EffectivelyChanged);
    internal static bool IdleChanged(P28BasicCalibrationPlan p) => IdleGroups(p).Any(g => g.EffectivelyChanged);
    internal static string LimiterId(P28BasicCalibrationPlan p) => LimiterChanged(p) ? P28CombinedLimiterCorpus.Id : LimiterControl;
    internal static string IdleId(P28BasicCalibrationPlan p) => IdleChanged(p) ? P28IdleTableCorpus.Id : IdleControl;
    internal static IReadOnlyList<(string Id, P28LimiterScenario Scenario)> Fixed(P28BasicCalibrationPlan p) => P28CombinedLimiterCorpus.Fixed(LimiterGroups(p));
    internal static IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> Adaptive(P28BasicCalibrationPlan p)
    {
        var all = P28CombinedLimiterCorpus.Create(LimiterGroups(p));
        if (LimiterChanged(p)) return all;
        // Retain both banks' reset/update/hold/decrease/inhibit plus persistent context switches.
        return all.Where(s => s.Id is "bases0/edited-ram-prior0-inhibit0" or "bases1/edited-ram-prior32-inhibit128" ||
            s.Id.StartsWith("cross-context-", StringComparison.Ordinal)).ToArray();
    }
    internal static IReadOnlyList<(string Id, P28IdleContextsScenario Scenario)> Idle(P28BasicCalibrationPreview p)
    {
        if (IdleChanged(p.Plan)) return P28IdleTableCorpus.Create(p.Original, p.Output, IdleGroups(p.Plan));
        // Code-owned unchanged source controls, not a reduced corpus for edited tables.
        var calls = new[] { 0, 40, 135, 255 }.SelectMany(x => new[] { 9, 8, 1, 25, 73, 15 }.Select(f =>
            new P28IdleContextsCall(0, (byte)x, 1450, P28IdleTableCorpus.Selectors(f)))).Select((c, i) => c with { Index = i }).ToArray();
        return [("unchanged-idle-controls", P28IdleContextsScenario.Create(P28IdleTableCorpus.Initial, calls, IdleControl))];
    }
}
public static class P28BasicCalibrationExecution
{
    public static async Task<P28VerifiedBasicCalibrationExport> ValidateAsync(P28BasicCalibrationPreview preview, string runner,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = Reproduce(preview.Original, preview.Profile, preview.Binding, true, preview.Location, preview.Plan);
        if (preview.Plan.IsNoOp) throw new InvalidDataException("No-op cannot publish a new BIN.");
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("Existing native runner is mandatory.");
        var runnerSnapshot = File.ReadAllBytes(runner); var images = preview.Images; var plan = preview.Plan;
        var (_, recheck) = ResearchOutputGroup.CaptureInputs(preview.Original, preview.Profile, plan.ProfileDigest, [runner]);
        string? version = null, upstream = null; string[]? fixes = null;
        void Identity(SliceProcessResponse response, string operation)
        {
            var r = response.Response; var f = SliceRunnerIdentity.Validate(r, operation);
            var v = r.GetProperty("runnerVersion").GetString()!; var u = r.GetProperty("upstreamCommit").GetString()!;
            if (version is not null && (version != v || upstream != u || !fixes!.SequenceEqual(f))) throw new InvalidDataException("Runner identity changed between suites.");
            version = v; upstream = u; fixes = f;
        }
        var prefix = await SeededSliceProcess.ExchangeAsync(runner, P28BasicVtecBatch.Request(preview), options, cancellationToken).ConfigureAwait(false);
        Identity(prefix, P28BasicVtecBatch.Operation(plan.Groups[0].EffectivelyChanged)); var vtec = P28BasicVtecBatch.Analyze(preview, prefix);
        var fixedScenarios = P28BasicCalibrationCorpus.Fixed(plan); var adaptiveScenarios = P28BasicCalibrationCorpus.Adaptive(plan);
        var fixedRuns = await P28FixedExportBatch.RunAsync(images, fixedScenarios, runner, preview.Location.Offset,
            (image, scenario, response) => P28LimiterValidator.AnalyzeExportImage(preview, image, scenario, response), Identity, options, cancellationToken).ConfigureAwait(false);
        var adaptiveRuns = await P28AdaptiveExportBatch.RunAsync(images, adaptiveScenarios, runner,
            (image, scenario, response) => P28AdaptiveValidator.AnalyzeExportImage(preview, image, scenario, response), Identity, true, options, cancellationToken).ConfigureAwait(false);
        var idleScenarios = P28BasicCalibrationCorpus.Idle(preview);
        var idleRuns = await P28IdleExportBatch.RunAsync(images, idleScenarios, runner, (image, scenario, response, id) =>
        {
            preview.RequireImage(image);
            if (scenario.Mutation is not null) throw new InvalidDataException("Mutation in basic idle suite.");
            return P28IdleContextsValidator.AnalyzeImage(image, scenario, response, id);
        }, Identity, options, cancellationToken).ConfigureAwait(false);
        // Exactly one native checksum batch for the three final composition images.
        var checksum = await SeededSliceProcess.ExchangeAsync(runner, P28NativeChecksumVerifier.CreateRequest(images), options, cancellationToken).ConfigureAwait(false);
        Identity(checksum, "checksumBatch"); var checks = CompareChecksum(images, checksum);
        var limiter = new P28BasicLimiterEvidence(P28BasicCalibrationCorpus.LimiterId(plan), fixedRuns, adaptiveRuns,
            P28CombinedLimiterExecution.Witnesses(LimiterGroups(plan), adaptiveScenarios, adaptiveRuns));
        var idle = new P28BasicIdleEvidence(P28BasicCalibrationCorpus.IdleId(plan), idleRuns, P28IdleTableExecution.Witnesses(IdleGroups(plan), idleRuns),
            P28IdleTableExecution.Effects(preview.Original, IdleGroups(plan), idleScenarios, idleRuns));
        var evidence = new P28BasicCalibrationEvidence(version!, upstream!, fixes!, plan.Digest(), vtec, limiter, idle, checks, "NotRun", "NotRun");
        RequireEvidence(preview, evidence);
        cancellationToken.ThrowIfCancellationRequested(); recheck();
        if (!runnerSnapshot.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during fresh validation.");
        return new(preview, evidence);
    }
    internal static void RequireEvidence(P28BasicCalibrationPreview p, P28BasicCalibrationEvidence e)
    {
        P28RawEditJson.ValidateObject(e); var plan = p.Plan;
        if (plan.IsNoOp || e.PlanDigest != plan.Digest() || e.VtecFullChainP1PhysicalOutput != "NotRun" || e.JointEcuExecution != "NotRun")
            throw new InvalidDataException("Stale, no-op or scope-promoted basic evidence.");
        foreach (var operation in new[] { P28BasicVtecBatch.Operation(plan.Groups[0].EffectivelyChanged), "limiterSequence", "adaptiveLimiter", "idleContexts", "checksumBatch" })
            _ = SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new
            { protocolVersion = 1, operation, runnerVersion = e.RunnerVersion, upstreamCommit = e.UpstreamCommit, localSemanticFixes = e.LocalSemanticFixes }), operation);
        P28BasicVtecBatch.Require(p, e.VtecThresholdPrefix);
        var adaptive = P28BasicCalibrationCorpus.Adaptive(plan); var idle = P28BasicCalibrationCorpus.Idle(p);
        if (e.LimiterAdaptive.CorpusId != P28BasicCalibrationCorpus.LimiterId(plan) || e.Idle.CorpusId != P28BasicCalibrationCorpus.IdleId(plan))
            throw new InvalidDataException("Wrong mandatory family corpus.");
        P28FixedExportBatch.RequireRuns(p.Images, P28BasicCalibrationCorpus.Fixed(plan), e.LimiterAdaptive.FixedRuns);
        P28AdaptiveExportBatch.RequireRuns(p.Images, adaptive, e.LimiterAdaptive.AdaptiveRuns);
        P28CombinedLimiterExecution.Relations(LimiterGroups(plan), adaptive, e.LimiterAdaptive.AdaptiveRuns);
        P28IdleExportBatch.RequireRuns(p.Images, idle, e.Idle.Runs); P28IdleTableExecution.Relations(e.Idle.Runs);
        if (!P28BasicCalibrationCorpus.IdleChanged(plan))
            foreach (var group in e.Idle.Runs.GroupBy(r => (r.ScenarioId, r.ScratchPattern)))
                if (!P28LimiterValidator.Equal(group.Single(r => r.ImageKind == "A").Outcomes, group.Single(r => r.ImageKind == "C").Outcomes))
                    throw new InvalidDataException("Unedited idle semantic outputs changed.");
        RequireChecksumEvidence(p.Images, e.Checksum);
        if (!e.LimiterAdaptive.Witnesses.SequenceEqual(P28CombinedLimiterExecution.Witnesses(LimiterGroups(plan), adaptive, e.LimiterAdaptive.AdaptiveRuns)) ||
            !e.Idle.Witnesses.SequenceEqual(P28IdleTableExecution.Witnesses(IdleGroups(plan), e.Idle.Runs)) ||
            !P28LimiterValidator.Equal(e.Idle.CellEffects, P28IdleTableExecution.Effects(p.Original, IdleGroups(plan), idle, e.Idle.Runs)))
            throw new InvalidDataException("Missing/forged basic family witness or cell effect.");
    }
}
