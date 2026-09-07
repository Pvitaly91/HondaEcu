using System.Text.Json;
using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

public sealed record P28AdaptiveBaseRead(int Pc, int Address, int Word);
public sealed record P28AdaptiveBaseOutcome(int Index, int Bank, string Path, IReadOnlyList<P28AdaptiveBaseRead> TableReads,
    P28AdaptiveState Before, P28AdaptiveState Produced, P28AdaptiveState After, P28FixedLimiterOutcome Limiter);
public sealed record P28AdaptiveBaseRun(string ImageKind, RomHash ImageHash, string ScenarioId, string ScenarioDigest,
    int ScratchPattern, int Requested, int StrictMatches, string ObservationDigest, IReadOnlyList<P28AdaptiveBaseOutcome> Outcomes);
public sealed record P28AdaptiveBaseEvidence(string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string PlanDigest, string CorpusId, IReadOnlyList<P28AdaptiveBaseRun> Runs, IReadOnlyList<P28ChecksumExportObservation> ChecksumRuns,
    bool IntermediateAndOutputAgree, bool UntouchedBankControlsAgree, bool FixedConsumerControlsAgree, bool NativeValidationComplete);
public sealed class P28VerifiedAdaptiveBaseExport
{
    private readonly string _evidence;
    internal P28VerifiedAdaptiveBaseExport(P28AdaptiveBasePreview preview, P28AdaptiveBaseEvidence evidence)
    { Preview = preview; _evidence = P28RawEditJson.Serialize(evidence, false); }
    public P28AdaptiveBasePreview Preview { get; }
    public P28AdaptiveBaseEvidence Evidence => P28RawEditJson.Parse<P28AdaptiveBaseEvidence>(_evidence);
}

public static class P28AdaptiveBaseExecution
{
    internal static P28AdaptiveBaseOutcome Outcome(P28AdaptiveCall input, P28AdaptiveModelStep s)
    {
        var l = s.Limiter;
        return new(input.Limiter.Index, s.Bank, s.Path, s.TableReads.Select(r => new P28AdaptiveBaseRead(r[0], r[1], r[2])).ToArray(), s.Before, s.AfterProducer, s.After,
            new(input.Limiter.Index, input.Limiter.RawPeriod, l.Context, l.Threshold, l.OverspeedRequest,
                (l.Before.Data012A & 128) != 0, l.InhibitBranch, l.After.Data018F, l.After.Data0124,
                s.AfterProducer.Limiter.RamCut, s.AfterProducer.Limiter.RamResume));
    }
    internal static void Relations(IReadOnlyList<P28AdaptiveBaseRun> runs)
    {
        foreach (var group in runs.GroupBy(r => (r.ScenarioId, r.ScratchPattern)))
        {
            var a = group.Single(r => r.ImageKind == "A"); var b = group.Single(r => r.ImageKind == "B"); var c = group.Single(r => r.ImageKind == "C");
            if (b.ObservationDigest != c.ObservationDigest || !P28LimiterValidator.Equal(b.Outcomes, c.Outcomes))
                throw new InvalidDataException("B/C producer-limiter-consumer history differs.");
            if (a.ScenarioId.StartsWith("untouched-", StringComparison.Ordinal) &&
                (a.ObservationDigest != c.ObservationDigest || !P28LimiterValidator.Equal(a.Outcomes, c.Outcomes)))
                throw new InvalidDataException("Never-edited-bank control differs.");
            if (a.ScenarioId.Contains("-fixed-", StringComparison.Ordinal))
                for (var i = 0; i < a.Outcomes.Count; i++)
                {
                    var x = a.Outcomes[i].Limiter; var y = c.Outcomes[i].Limiter;
                    // Producer RAM/working registers may differ; these are not fixed-consumer inputs.
                    if (x.ThresholdSource != "Fixed" || y.ThresholdSource != "Fixed" ||
                        x with { RamCut = 0, RamResume = 0 } != y with { RamCut = 0, RamResume = 0 })
                        throw new InvalidDataException("Fixed-only consumer control differs.");
                }
        }
    }
    public static async Task<P28VerifiedAdaptiveBaseExport> ValidateAsync(P28AdaptiveBasePreview preview, string runner,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = P28AdaptiveBaseEditor.Reproduce(preview.Original, preview.Profile, preview.Binding, true, preview.Location, preview.Plan);
        var plan = preview.Plan;
        if (plan.IsNoOp) throw new InvalidDataException("No-op does not authorize a new firmware BIN.");
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("Existing native runner is mandatory.");
        var snapshot = File.ReadAllBytes(runner);
        var images = new[] { (Id: "A", Image: preview.Original), (Id: "B", Image: preview.Intermediate), (Id: "C", Image: preview.Output) };
        string? version = null, upstream = null; string[]? fixes = null;
        void Identity(SliceProcessResponse response, string operation)
        {
            var root = response.Response; var f = SliceRunnerIdentity.Validate(root, operation);
            var v = root.GetProperty("runnerVersion").GetString()!; var u = root.GetProperty("upstreamCommit").GetString()!;
            if (version is not null && (version != v || upstream != u || !fixes!.SequenceEqual(f))) throw new InvalidDataException("Runner identity changed.");
            version = v; upstream = u; fixes = f;
        }
        var runs = await P28AdaptiveExportBatch.RunAsync(images, P28AdaptiveBaseCorpus.Create(plan), runner,
            (image, scenario, response) => P28AdaptiveValidator.AnalyzeExportImage(preview, image, scenario, response),
            Identity, false, options, cancellationToken).ConfigureAwait(false);
        var checksum = await SeededSliceProcess.ExchangeAsync(runner, P28NativeChecksumVerifier.CreateRequest(images.Select(i => (i.Id, i.Image)).ToArray()), options, cancellationToken).ConfigureAwait(false);
        Identity(checksum, "checksumBatch");
        var checks = CompareChecksum(images, checksum); // unchanged M1n/M1f ordered 512-call parser
        Relations(runs);
        cancellationToken.ThrowIfCancellationRequested();
        if (!snapshot.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during execution.");
        var evidence = new P28AdaptiveBaseEvidence(version!, upstream!, fixes!, plan.Digest(), P28AdaptiveBaseCorpus.Id,
            runs, checks, true, true, true, true);
        RequireEvidence(preview, evidence);
        return new(preview, evidence);
    }
    internal static void RequireEvidence(P28AdaptiveBasePreview p, P28AdaptiveBaseEvidence e)
    {
        var plan = p.Plan;
        if (e.PlanDigest != plan.Digest() || e.CorpusId != P28AdaptiveBaseCorpus.Id || !e.NativeValidationComplete ||
            !e.IntermediateAndOutputAgree || !e.UntouchedBankControlsAgree || !e.FixedConsumerControlsAgree)
            throw new InvalidDataException("Stale/incomplete adaptive execution evidence.");
        _ = SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = P28AdaptiveValidator.Operation,
            runnerVersion = e.RunnerVersion,
            upstreamCommit = e.UpstreamCommit,
            localSemanticFixes = e.LocalSemanticFixes
        }), P28AdaptiveValidator.Operation);
        var scenarios = P28AdaptiveBaseCorpus.Create(plan);
        var images = new[] { (Id: "A", Image: p.Original), (Id: "B", Image: p.Intermediate), (Id: "C", Image: p.Output) };
        P28AdaptiveExportBatch.RequireRuns(images, scenarios, e.Runs);
        RequireChecksumEvidence(images, e.ChecksumRuns);
        Relations(e.Runs);
        if (!HasWitness(plan, e.Runs)) throw new InvalidDataException("No actual base-read -> produced RAM -> changed limiter decision witness.");
    }
    internal static bool HasWitness(P28AdaptiveBasePlan plan, IReadOnlyList<P28AdaptiveBaseRun> runs)
    {
        foreach (var a in runs.Where(r => r.ImageKind == "A"))
        {
            var c = runs.Single(r => r.ImageKind == "C" && r.ScenarioId == a.ScenarioId && r.ScratchPattern == a.ScratchPattern);
            for (var i = 0; i < a.Outcomes.Count; i++)
            {
                var before = a.Outcomes[i]; var after = c.Outcomes[i];
                if (before.Bank != plan.RequestedPair.Bank || before.Limiter.ThresholdSource != "AdaptiveRam" ||
                    before.Limiter.OverspeedRequest == after.Limiter.OverspeedRequest) continue;
                foreach (var w in plan.Words.Where(w => w.OldWord != w.NewWord))
                    if (before.TableReads.Any(r => r.Address == w.Offset && r.Word == w.OldWord) && after.TableReads.Any(r => r.Address == w.Offset && r.Word == w.NewWord) &&
                        (before.Produced.Limiter.RamCut != after.Produced.Limiter.RamCut || before.Produced.Limiter.RamResume != after.Produced.Limiter.RamResume)) return true;
            }
        }
        return false;
    }
}
