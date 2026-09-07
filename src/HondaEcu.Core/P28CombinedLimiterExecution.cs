using System.Text.Json;
using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

public sealed record P28CombinedLimiterWitness(string Group, string ScenarioId, int ScratchPattern, int Index,
    int OldThreshold, int NewThreshold, bool OldRequest, bool NewRequest, string Evidence);
public sealed record P28CombinedLimiterEvidence(string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string PlanDigest, string CorpusId, IReadOnlyList<P28AdaptiveBaseRun> Runs, IReadOnlyList<P28FixedLimiterRun> LimiterRuns, IReadOnlyList<P28ChecksumExportObservation> ChecksumRuns,
    IReadOnlyList<P28CombinedLimiterWitness> Witnesses, bool IntermediateAndOutputAgree, bool SemanticControlsAgree, bool NativeValidationComplete);
public sealed class P28VerifiedCombinedLimiterExport
{
    private readonly string _evidence;
    internal P28VerifiedCombinedLimiterExport(P28CombinedLimiterPreview preview, P28CombinedLimiterEvidence evidence)
    { Preview = preview; _evidence = P28RawEditJson.Serialize(evidence, false); }
    public P28CombinedLimiterPreview Preview { get; }
    public P28CombinedLimiterEvidence Evidence => P28RawEditJson.Parse<P28CombinedLimiterEvidence>(_evidence);
}

public static class P28CombinedLimiterExecution
{
    public static async Task<P28VerifiedCombinedLimiterExport> ValidateAsync(P28CombinedLimiterPreview preview, string runner,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = P28CombinedLimiterEditor.Reproduce(preview.Original, preview.Profile, preview.Binding, true, preview.Location, preview.Plan);
        if (preview.Plan.IsNoOp) throw new InvalidDataException("No-op cannot publish a new firmware BIN.");
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("Existing native runner is mandatory.");
        var snapshot = File.ReadAllBytes(runner); var images = Images(preview); var scenarios = P28CombinedLimiterCorpus.Create(preview.Plan);
        string? version = null, upstream = null; string[]? fixes = null;
        void Identity(SliceProcessResponse response, string operation)
        {
            var r = response.Response; var f = SliceRunnerIdentity.Validate(r, operation);
            var v = r.GetProperty("runnerVersion").GetString()!; var u = r.GetProperty("upstreamCommit").GetString()!;
            if (version is not null && (version != v || upstream != u || !fixes!.SequenceEqual(f))) throw new InvalidDataException("Runner identity changed.");
            version = v; upstream = u; fixes = f;
        }
        var limiterRuns = await P28FixedExportBatch.RunAsync(images, P28CombinedLimiterCorpus.Fixed(preview.Plan), runner, preview.Location.Offset,
            (image, scenario, response) => P28LimiterValidator.AnalyzeExportImage(preview, image, scenario, response), Identity, options, cancellationToken).ConfigureAwait(false);
        var runs = await P28AdaptiveExportBatch.RunAsync(images, scenarios, runner,
            (image, scenario, response) => P28AdaptiveValidator.AnalyzeExportImage(preview, image, scenario, response),
            Identity, true, options, cancellationToken).ConfigureAwait(false);
        var checksum = await SeededSliceProcess.ExchangeAsync(runner, P28NativeChecksumVerifier.CreateRequest(images), options, cancellationToken).ConfigureAwait(false);
        Identity(checksum, "checksumBatch"); var checks = CompareChecksum(images, checksum);
        Relations(preview.Plan, scenarios, runs);
        var witnesses = Witnesses(preview.Plan, scenarios, runs);
        cancellationToken.ThrowIfCancellationRequested();
        if (!snapshot.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during execution.");
        var e = new P28CombinedLimiterEvidence(version!, upstream!, fixes!, preview.Plan.Digest(), P28CombinedLimiterCorpus.Id,
            runs, limiterRuns, checks, witnesses, true, true, true);
        RequireEvidence(preview, e); return new(preview, e);
    }
    private static (string Id, RomImage Image)[] Images(P28CombinedLimiterPreview p) => [("A", p.Original), ("B", p.Intermediate), ("C", p.Output)];
    internal static void RequireEvidence(P28CombinedLimiterPreview p, P28CombinedLimiterEvidence e)
    {
        if (p.Plan.IsNoOp || e.PlanDigest != p.Plan.Digest() || e.CorpusId != P28CombinedLimiterCorpus.Id ||
            !e.IntermediateAndOutputAgree || !e.SemanticControlsAgree || !e.NativeValidationComplete)
            throw new InvalidDataException("Stale/incomplete combined execution evidence.");
        _ = SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = P28AdaptiveValidator.Operation,
            runnerVersion = e.RunnerVersion,
            upstreamCommit = e.UpstreamCommit,
            localSemanticFixes = e.LocalSemanticFixes
        }), P28AdaptiveValidator.Operation);
        var scenarios = P28CombinedLimiterCorpus.Create(p.Plan); var images = Images(p);
        P28AdaptiveExportBatch.RequireRuns(images, scenarios, e.Runs);
        P28FixedExportBatch.RequireRuns(images, P28CombinedLimiterCorpus.Fixed(p.Plan), e.LimiterRuns);
        RequireChecksumEvidence(images, e.ChecksumRuns); Relations(p.Plan, scenarios, e.Runs);
        if (!e.Witnesses.SequenceEqual(Witnesses(p.Plan, scenarios, e.Runs))) throw new InvalidDataException("Forged or missing group witness.");
    }
    internal static void Relations(P28CombinedLimiterPlan plan, IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> scenarios,
        IReadOnlyList<P28AdaptiveBaseRun> runs)
    {
        foreach (var group in runs.GroupBy(r => (r.ScenarioId, r.ScratchPattern)))
        {
            var a = group.Single(r => r.ImageKind == "A"); var b = group.Single(r => r.ImageKind == "B"); var c = group.Single(r => r.ImageKind == "C");
            if (b.ObservationDigest != c.ObservationDigest || !P28LimiterValidator.Equal(b.Outcomes, c.Outcomes))
                throw new InvalidDataException("Combined B/C full non-checksum histories differ.");
            var calls = scenarios.Single(s => s.Id == a.ScenarioId).Scenario.Calls;
            var bank = calls[0].Bank1 ? 1 : 0;
            if (!plan.Groups[bank + 1].EffectivelyChanged && calls.All(c => c.Bank1 == (bank == 1) && !c.Limiter.P4Bit0 && !c.Limiter.Snapshot011bBit7) &&
                !P28LimiterValidator.Equal(a.Outcomes, c.Outcomes))
                throw new InvalidDataException("Clean never-edited-bank relevant history differs.");
            if (!plan.Groups[0].EffectivelyChanged && calls.All(c => c.Limiter.P4Bit0 || c.Limiter.Snapshot011bBit7))
                for (var i = 0; i < a.Outcomes.Count; i++)
                    if (a.Outcomes[i].Limiter with { RamCut = 0, RamResume = 0 } != c.Outcomes[i].Limiter with { RamCut = 0, RamResume = 0 })
                        throw new InvalidDataException("Unedited fixed consumer differs; adaptive RAM is intentionally not equated.");
        }
    }
    internal static IReadOnlyList<P28CombinedLimiterWitness> Witnesses(P28CombinedLimiterPlan plan,
        IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> scenarios, IReadOnlyList<P28AdaptiveBaseRun> runs)
    {
        var result = new List<P28CombinedLimiterWitness>();
        foreach (var group in plan.Groups.Where(g => g.EffectivelyChanged))
        {
            P28CombinedLimiterWitness? witness = null;
            foreach (var a in runs.Where(r => r.ImageKind == "A"))
            {
                var calls = scenarios.Single(s => s.Id == a.ScenarioId).Scenario.Calls;
                // Isolated SOURCE control, still executing the actual combined B/C images.
                var fixedOnly = group.Id == "fixed";
                if (fixedOnly ? !calls.All(c => c.Limiter.P4Bit0 || c.Limiter.Snapshot011bBit7) :
                    !calls.All(c => !c.Limiter.P4Bit0 && !c.Limiter.Snapshot011bBit7 && c.Bank1 == (group.Id == "bank1"))) continue;
                var c = runs.Single(r => r.ImageKind == "C" && r.ScenarioId == a.ScenarioId && r.ScratchPattern == a.ScratchPattern);
                for (var i = 0; i < a.Outcomes.Count; i++)
                {
                    var x = a.Outcomes[i]; var y = c.Outcomes[i];
                    if (x.Limiter.OverspeedRequest == y.Limiter.OverspeedRequest || x.Limiter.SelectedThreshold == y.Limiter.SelectedThreshold) continue;
                    if (!fixedOnly && (!group.AdaptiveWords.Where(w => w.OldWord != w.NewWord).Any(w =>
                            x.TableReads.Any(r => r.Address == w.Offset && r.Word == w.OldWord) && y.TableReads.Any(r => r.Address == w.Offset && r.Word == w.NewWord)) ||
                        x.Produced.Limiter.RamCut == y.Produced.Limiter.RamCut && x.Produced.Limiter.RamResume == y.Produced.Limiter.RamResume)) continue;
                    witness = new(group.Id, a.ScenarioId, a.ScratchPattern, i, x.Limiter.SelectedThreshold, y.Limiter.SelectedThreshold,
                        x.Limiter.OverspeedRequest, y.Limiter.OverspeedRequest, fixedOnly ? "Actual immediate fetch -> selected fixed threshold -> request" : "Actual LC base read -> native produced RAM -> selected threshold -> request");
                    break;
                }
                if (witness is not null) break;
            }
            result.Add(witness ?? throw new InvalidDataException($"No native decision witness for effectively changed {group.Id}."));
        }
        return result.AsReadOnly();
    }
}
