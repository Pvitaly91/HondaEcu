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
        var runs = new List<P28AdaptiveBaseRun>();
        foreach (var item in P28AdaptiveBaseCorpus.Create(plan))
            foreach (var image in images)
            {
                var response = await SeededSliceProcess.ExchangeAsync(runner, P28AdaptiveValidator.CreateRequest(image.Image, item.Scenario), options, cancellationToken).ConfigureAwait(false);
                Identity(response, P28AdaptiveValidator.Operation);
                var report = P28AdaptiveValidator.AnalyzeExportImage(preview, image.Image, item.Scenario, response);
                if (report.HasFailure) throw new InvalidDataException($"Mandatory adaptive batch did not strictly complete: {item.Id}/{image.Id}.");
                foreach (var s in report.Sequences)
                {
                    // M1m validates actual LC addresses/values, state, ordered writes, tick effects,
                    // branches, exits, stack and critical section against each image's own model.
                    // Its exact code/data ranges exclude the compensation byte; no permissions added.
                    var outcomes = s.Checkpoints.Select(r => Outcome(r.Inputs, r.Expected!)).ToArray();
                    runs.Add(new(image.Id, image.Image.Hash, item.Id, item.Scenario.Digest, s.ScratchPattern,
                        s.Counts.RequestedCalls, s.Counts.StrictMatches, Digest(s.Checkpoints.Select(c => c.Actual).ToArray()), outcomes));
                }
            }
        var checksum = await SeededSliceProcess.ExchangeAsync(runner, P28NativeChecksumVerifier.CreateRequest(images.Select(i => (i.Id, i.Image)).ToArray()), options, cancellationToken).ConfigureAwait(false);
        Identity(checksum, "checksumBatch");
        var checks = CompareChecksum(images, checksum); // unchanged M1n/M1f ordered 512-call parser
        Relations(runs);
        cancellationToken.ThrowIfCancellationRequested();
        if (!snapshot.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during execution.");
        var evidence = new P28AdaptiveBaseEvidence(version!, upstream!, fixes!, plan.Digest(), P28AdaptiveBaseCorpus.Id,
            runs.AsReadOnly(), checks, true, true, true, true);
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
        if (e.Runs.Count != scenarios.Count * 9) throw new InvalidDataException("Missing/extra mandatory adaptive runs.");
        var images = new[] { (Id: "A", Image: p.Original), (Id: "B", Image: p.Intermediate), (Id: "C", Image: p.Output) };
        foreach (var scenario in scenarios)
            foreach (var image in images)
                foreach (var pattern in new[] { 0, 85, 170 })
                {
                    var found = e.Runs.Where(r => r.ScenarioId == scenario.Id && r.ImageKind == image.Id && r.ScratchPattern == pattern).ToArray();
                    if (found.Length != 1) throw new InvalidDataException("Duplicate/missing adaptive evidence identity.");
                    var r = found[0];
                    if (r.ImageHash != image.Image.Hash || r.ScenarioDigest != scenario.Scenario.Digest || r.Requested != scenario.Scenario.Calls.Count ||
                        r.StrictMatches != r.Requested || r.Outcomes.Count != r.Requested || r.ObservationDigest.Length != 64 || !r.ObservationDigest.All(Uri.IsHexDigit))
                        throw new InvalidDataException("Invalid adaptive execution accounting.");
                    var model = new P28AdaptiveModel(image.Image.Span, scenario.Scenario.InitialState);
                    var expected = scenario.Scenario.Calls.Select(call => Outcome(call, model.Step(call))).ToArray();
                    if (!P28LimiterValidator.Equal(r.Outcomes, expected)) throw new InvalidDataException("Receipt history disagrees with independently rederived state machine.");
                }
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
