using System.Text.Json;
using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

public sealed record P28IdleTableOutcome(int Index, int RawD9, int RawPeriod, string FinalSource, int BaseResult, int FinalTarget,
    int Error, bool Sign, P28IdleContextsState State, IReadOnlyList<P28IdleLookupObservation> Lookups, IReadOnlyList<int> ProgramReads);
public sealed record P28IdleTableRun(string ImageKind, RomHash ImageHash, string ScenarioId, string ScenarioDigest, int ScratchPattern,
    int Requested, int StrictMatches, string ObservationDigest, string ModelDigest, string IndependentControlDigest, IReadOnlyList<P28IdleTableOutcome> Outcomes);
public sealed record P28IdleTableWitness(string Table, string ScenarioId, int ScratchPattern, int Index, int RawD9, int RawPeriod,
    int OldTarget, int NewTarget, int OldError, int NewError, bool OldSign, bool NewSign, string Meaning);
public sealed record P28IdleCellEffect(string FieldId, string Effect, int Count, string ScenarioId, int Index, int ScratchPattern,
    int WeightNumerator, int WeightDenominator, IReadOnlyList<int> OldLookup, IReadOnlyList<int> NewLookup, int OldTarget, int NewTarget,
    int OldError, int NewError, bool OldSign, bool NewSign, string Attribution);
public sealed record P28IdleTableEvidence(string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string PlanDigest, string CorpusId, IReadOnlyList<P28IdleTableRun> Runs, IReadOnlyList<P28ChecksumExportObservation> ChecksumRuns,
    IReadOnlyList<P28IdleTableWitness> Witnesses, IReadOnlyList<P28IdleCellEffect> CellEffects,
    bool IntermediateAndOutputAgree, bool IndependentControlsAgree, bool NativeValidationComplete);
public sealed class P28VerifiedIdleTableExport
{
    private readonly string _evidence;
    internal P28VerifiedIdleTableExport(P28IdleTablePreview preview, P28IdleTableEvidence evidence)
    { Preview = preview; _evidence = P28RawEditJson.Serialize(evidence, false); }
    public P28IdleTablePreview Preview { get; }
    public P28IdleTableEvidence Evidence => P28RawEditJson.Parse<P28IdleTableEvidence>(_evidence);
}
public static class P28IdleTableExecution
{
    internal static (string Id, RomImage Image)[] Images(P28IdleTablePreview p) => [("A", p.Original), ("B", p.Intermediate), ("C", p.Output)];
    internal static P28IdleTableOutcome Outcome(P28IdleContextsCall call, P28IdleContextsModelStep m) => new(call.Index, call.RawD9, call.RawPeriod,
        m.FinalSource, m.BaseResult, m.FinalTarget, m.ClampedError, m.CurrentBelowTarget, m.After, m.Lookups, m.ProducerReads);
    internal static string Controls(IEnumerable<P28IdleContextsModelStep> steps) => Digest(steps.Select(s => new
    {
        s.FinalSource,
        State = s.After with { Target = 0, ErrorMagnitude = 0, Data021a = (byte)(s.After.Data021a & ~16) },
        Branches = s.ProducerBranches.Where(b => b[0] != 0x58BB).ToArray()
    }).ToArray());
    public static async Task<P28VerifiedIdleTableExport> ValidateAsync(P28IdleTablePreview preview, string runner,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = P28IdleTableEditor.Reproduce(preview.Original, preview.Profile, preview.Binding, true, preview.Location, preview.Plan);
        if (preview.Plan.IsNoOp) throw new InvalidDataException("No-op cannot publish a new firmware BIN.");
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("Existing native runner is mandatory.");
        var snapshot = File.ReadAllBytes(runner); var images = Images(preview); var scenarios = P28IdleTableCorpus.Create(preview);
        string? version = null, upstream = null; string[]? fixes = null;
        void Identity(SliceProcessResponse response, string operation)
        {
            var r = response.Response; var f = SliceRunnerIdentity.Validate(r, operation);
            var v = r.GetProperty("runnerVersion").GetString()!; var u = r.GetProperty("upstreamCommit").GetString()!;
            if (version is not null && (version != v || upstream != u || !fixes!.SequenceEqual(f))) throw new InvalidDataException("Runner identity changed.");
            version = v; upstream = u; fixes = f;
        }
        var runs = await P28IdleExportBatch.RunAsync(images, scenarios, runner,
            (image, scenario, response, id) => AnalyzeCompositionImage(preview, image, scenario, response, id), Identity, options, cancellationToken).ConfigureAwait(false);
        var checksum = await SeededSliceProcess.ExchangeAsync(runner, P28NativeChecksumVerifier.CreateRequest(images), options, cancellationToken).ConfigureAwait(false);
        Identity(checksum, "checksumBatch"); var checks = CompareChecksum(images, checksum);
        Relations(runs); var witnesses = Witnesses(preview.Plan, runs); var effects = Effects(preview, scenarios, runs);
        cancellationToken.ThrowIfCancellationRequested();
        if (!snapshot.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during execution.");
        var evidence = new P28IdleTableEvidence(version!, upstream!, fixes!, preview.Plan.Digest(), P28IdleTableCorpus.Id, runs, checks,
            witnesses, effects, true, true, true);
        RequireEvidence(preview, evidence); return new(preview, evidence);
    }
    // Only the reproduced composition enters this route. Old public M1q/M1r admission/mutation guards are unchanged.
    internal static P28IdleContextsImageReport AnalyzeCompositionImage(P28IdleTablePreview p, RomImage image, P28IdleContextsScenario scenario,
        SliceProcessResponse response, string id)
    {
        if (scenario.Mutation is not null || !Images(p).Any(i => i.Id == id && i.Image.Span.SequenceEqual(image.Span))) throw new InvalidDataException("Foreign image or mutation in idle composition validation.");
        return P28IdleContextsValidator.AnalyzeImage(image, scenario, response, id);
    }
    internal static void RequireEvidence(P28IdleTablePreview p, P28IdleTableEvidence e)
    {
        if (p.Plan.IsNoOp || e.PlanDigest != p.Plan.Digest() || e.CorpusId != P28IdleTableCorpus.Id || !e.IntermediateAndOutputAgree || !e.IndependentControlsAgree || !e.NativeValidationComplete)
            throw new InvalidDataException("Stale/incomplete idle execution evidence.");
        _ = SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = "idleContexts",
            runnerVersion = e.RunnerVersion,
            upstreamCommit = e.UpstreamCommit,
            localSemanticFixes = e.LocalSemanticFixes
        }), "idleContexts");
        var scenarios = P28IdleTableCorpus.Create(p); var images = Images(p);
        P28IdleExportBatch.RequireRuns(images, scenarios, e.Runs);
        RequireChecksumEvidence(images, e.ChecksumRuns); Relations(e.Runs);
        if (!P28LimiterValidator.Equal(e.Witnesses, Witnesses(p.Plan, e.Runs)) || !P28LimiterValidator.Equal(e.CellEffects, Effects(p, scenarios, e.Runs))) throw new InvalidDataException("Missing/forged idle witness or cell effect.");
    }
    internal static void Relations(IReadOnlyList<P28IdleTableRun> runs)
    {
        foreach (var group in runs.GroupBy(r => (r.ScenarioId, r.ScratchPattern)))
        {
            var a = group.Single(r => r.ImageKind == "A"); var b = group.Single(r => r.ImageKind == "B"); var c = group.Single(r => r.ImageKind == "C");
            if (b.ObservationDigest != c.ObservationDigest || b.ModelDigest != c.ModelDigest || !P28LimiterValidator.Equal(b.Outcomes, c.Outcomes)) throw new InvalidDataException("B/C non-checksum histories differ.");
            if (a.IndependentControlDigest != c.IndependentControlDigest) throw new InvalidDataException("Table-independent source/component/counter decisions changed.");
            // A/C scratch is intentionally not equated: a changed base may be replaced later.
            foreach (var pair in a.Outcomes.Zip(c.Outcomes))
                if (!pair.First.Lookups.Any(l => l.FinalContribution) && (pair.First.FinalTarget != pair.Second.FinalTarget || pair.First.Error != pair.Second.Error || pair.First.Sign != pair.Second.Sign))
                    throw new InvalidDataException("Unchanged immediate final control differs.");
        }
    }
    internal static IReadOnlyList<P28IdleTableWitness> Witnesses(P28IdleTablePlan plan, IReadOnlyList<P28IdleTableRun> runs)
        => Witnesses(plan.Tables, runs);
    internal static IReadOnlyList<P28IdleTableWitness> Witnesses(IReadOnlyList<P28IdleTableGroup> tables, IReadOnlyList<P28IdleTableRun> runs)
    {
        var result = new List<P28IdleTableWitness>();
        foreach (var t in tables.Where(t => t.EffectivelyChanged))
        {
            var table = P28IdleTableFields.Table(t.Id == "base" ? 0 : 1); P28IdleTableWitness? witness = null;
            foreach (var a in runs.Where(r => r.ImageKind == "A"))
            {
                var c = runs.Single(r => r.ImageKind == "C" && r.ScenarioId == a.ScenarioId && r.ScratchPattern == a.ScratchPattern);
                foreach (var pair in a.Outcomes.Zip(c.Outcomes))
                {
                    var x = pair.First; var y = pair.Second;
                    if (x.FinalTarget == y.FinalTarget || x.Error == y.Error && x.Sign == y.Sign || !y.Lookups.Any(l => l.Table == table && l.FinalContribution) ||
                        !t.Cells.Where(cell => cell.OldValue != cell.NewValue).Any(cell => x.ProgramReads.Contains(cell.ValueOffset) && y.ProgramReads.Contains(cell.ValueOffset))) continue;
                    witness = new(t.Id, a.ScenarioId, a.ScratchPattern, x.Index, x.RawD9, x.RawPeriod, x.FinalTarget, y.FinalTarget, x.Error, y.Error, x.Sign, y.Sign,
                        "Combined-image native numeric read -> changed final target -> changed native error/sign; not individual-cell causal attribution"); break;
                }
                if (witness is not null) break;
            }
            result.Add(witness ?? throw new InvalidDataException($"No representative combined-image consumer witness for changed {t.Id} table."));
        }
        return result.AsReadOnly();
    }
    internal static IReadOnlyList<P28IdleCellEffect> Effects(P28IdleTablePreview p, IReadOnlyList<(string Id, P28IdleContextsScenario Scenario)> scenarios, IReadOnlyList<P28IdleTableRun> runs)
        => Effects(p.Original, p.Plan.Tables, scenarios, runs);
    internal static IReadOnlyList<P28IdleCellEffect> Effects(RomImage original, IReadOnlyList<P28IdleTableGroup> tables,
        IReadOnlyList<(string Id, P28IdleContextsScenario Scenario)> scenarios, IReadOnlyList<P28IdleTableRun> runs)
    {
        var result = new Dictionary<(string, string), P28IdleCellEffect>();
        foreach (var t in tables)
            foreach (var cell in t.Cells.Where(c => c.OldValue != c.NewValue))
            {
                var table = P28IdleTableFields.Table(t.Id == "base" ? 0 : 1);
                // Separate one-cell MODEL diagnostic images only for distinguishing quantization from joint-cell masking.
                // These are not native witnesses, not publications and never substitute for mandatory combined B/C.
                var diagnosticImage = original.CreateModifiedCopy([new BytePatch(cell.ValueOffset, cell.NewBytes.ToArray())]);
                foreach (var a in runs.Where(r => r.ImageKind == "A"))
                {
                    var scenario = scenarios.Single(s => s.Id == a.ScenarioId).Scenario; var diagnostic = new P28IdleContextsModel(diagnosticImage, scenario.InitialState);
                    var c = runs.Single(r => r.ImageKind == "C" && r.ScenarioId == a.ScenarioId && r.ScratchPattern == a.ScratchPattern);
                    for (var i = 0; i < a.Outcomes.Count; i++)
                    {
                        var x = a.Outcomes[i]; var y = c.Outcomes[i]; var one = diagnostic.Step(scenario.Calls[i]);
                        var old = x.Lookups.SingleOrDefault(l => l.Table == table); var edited = y.Lookups.SingleOrDefault(l => l.Table == table);
                        var weight = edited is null ? 0 : edited.UpperCell == cell.Index ? edited.Distance : edited.LowerCell == cell.Index ? edited.Denominator - edited.Distance : 0;
                        var effect = edited is null ? "LookupNotExecuted" : !y.ProgramReads.Contains(cell.ValueOffset) ? "CellNotRead" : weight == 0 ? "ZeroWeight" :
                            old!.Value == edited.Value ? (one.Lookups.Single(l => l.Table == table).Value != old.Value ? "MultipleCellMasking" : "IntegerTruncation") :
                            !edited.FinalContribution ? "LateReplacement" : x.FinalTarget != y.FinalTarget && x.Error == y.Error && x.Sign == y.Sign ? "ConsumerMagnitudeClamp" : "CombinedLookupTargetConsumerEffect";
                        var key = (cell.FieldId, effect);
                        if (result.TryGetValue(key, out var prior)) result[key] = prior with { Count = prior.Count + 1 };
                        else result.Add(key, new(cell.FieldId, effect, 1, a.ScenarioId, i, a.ScratchPattern, weight, edited?.Denominator ?? 0,
                            old is null ? [] : [old.Value], edited is null ? [] : [edited.Value], x.FinalTarget, y.FinalTarget, x.Error, y.Error, x.Sign, y.Sign,
                            "Read/weight and combined observations; joint effect is not attributed to one cell. Empty lookup collection means absent; one-cell diagnostics are model-only."));
                    }
                }
            }
        return result.Values.OrderBy(r => r.FieldId, StringComparer.Ordinal).ThenBy(r => r.Effect, StringComparer.Ordinal).ToArray();
    }
}
