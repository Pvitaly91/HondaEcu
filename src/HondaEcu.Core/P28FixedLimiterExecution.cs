using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28FixedLimiterOutcome(int Index, int RawPeriod, string ThresholdSource, int SelectedThreshold,
    bool OverspeedRequest, bool IndependentInhibit, bool MaskUpdateSkipped, int Mask, int State0124, int RamCut, int RamResume);
public sealed record P28FixedLimiterRun(string ImageKind, RomHash ImageHash, string ScenarioId, string ScenarioDigest,
    int ScratchPattern, int Requested, int StrictMatches, string ObservationDigest, string PersistentStateDigest,
    bool OperandFetchVerified, bool CompensationNotRead, IReadOnlyList<P28FixedLimiterOutcome> Outcomes);
public sealed record P28FixedLimiterEvidence(string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string PlanDigest, string CorpusId, IReadOnlyList<P28FixedLimiterRun> LimiterRuns,
    IReadOnlyList<P28FixedLimiterRun> AdaptiveRuns, IReadOnlyList<P28ChecksumExportObservation> ChecksumRuns,
    bool IntermediateAndOutputAgree, bool RamOnlyControlsAgree, bool NativeValidationComplete);

/// <summary>Only live validation constructs this token. Every exposed collection is a defensive snapshot.</summary>
public sealed class P28VerifiedFixedLimiterExport
{
    private readonly string _evidence;
    internal P28VerifiedFixedLimiterExport(P28FixedLimiterPreview preview, P28FixedLimiterEvidence evidence)
    { Preview = preview; _evidence = P28RawEditJson.Serialize(evidence, false); }
    public P28FixedLimiterPreview Preview { get; }
    public P28FixedLimiterEvidence Evidence => P28RawEditJson.Parse<P28FixedLimiterEvidence>(_evidence);
}

public static class P28FixedLimiterExecution
{
    public const string CorpusId = "fixed-limiter-abc-boundaries-and-adaptive-controls-v1";
    internal static int[] Boundaries(P28FixedLimiterPlan plan) => plan.Operands.SelectMany(o => new[] { o.OriginalWord, o.NewWord })
        .SelectMany(w => new[] { w - 1, w, w + 1 }).Where(w => w is >= 0 and <= 65535).Distinct().Order().ToArray();
    internal static IReadOnlyList<(string Id, P28LimiterScenario Scenario)> LimiterScenarios(P28FixedLimiterPlan plan)
    {
        var result = new List<(string, P28LimiterScenario)>(); var edges = Boundaries(plan);
        foreach (var prior in new byte[] { 0, 32 })
            foreach (var inhibit in new byte[] { 0, 128 })
                foreach (var context in new[] { "fixed-p4", "fixed-011b", "ram-only", "fixed-ram-fixed" })
                {
                    var id = $"{context}-prior{prior}-inhibit{inhibit}";
                    var values = edges.Reverse().Concat(edges).ToArray();
                    var calls = values.Select((raw, i) => new P28LimiterCall(i, (ushort)raw,
                        context == "fixed-p4" || context == "fixed-ram-fixed" && (i < edges.Length / 2 || i >= edges.Length + edges.Length / 2),
                        context == "fixed-011b", (byte)(0xFE - i % 4))).ToArray();
                    result.Add((id, P28LimiterScenario.Create(new(prior, 128, inhibit, 255, 7, 300, 320), calls, CorpusId + "/" + id)));
                }
        return result;
    }
    internal static IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> AdaptiveScenarios()
    {
        var result = new List<(string, P28AdaptiveScenario)>();
        foreach (var prior in new byte[] { 0, 32 })
            foreach (var inhibit in new byte[] { 0, 128 })
                foreach (var transition in new[] { false, true })
                {
                    var id = $"adaptive-{(transition ? "fixed-ram" : "ram-only")}-prior{prior}-inhibit{inhibit}";
                    var calls = Enumerable.Range(0, 10).Select(i => new P28AdaptiveCall(
                        new(i, (ushort)(i == 0 ? 539 : i == 1 ? 552 : 300 + i % 2), transition && i < 2, false, 254),
                        (ushort)(i < 8 ? 50000 : 11037), i >= 4, i == 7, false, false, true, 0,
                        (byte)(i is 0 or 3 ? 0 : 20), (byte)(i == 8 ? 12 : 0))).ToArray();
                    result.Add((id, P28AdaptiveScenario.Create(new(new(prior, 128, inhibit, 255, 7, 290, 310), 0, 0, 65535, 43690), calls, CorpusId + "/" + id)));
                }
        return result;
    }
    public static async Task<P28VerifiedFixedLimiterExport> ValidateAsync(P28FixedLimiterPreview preview, string runner,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = P28FixedLimiterEditor.Reproduce(preview.Original, preview.Profile, preview.Binding, true, preview.Location, preview.Plan);
        if (preview.Plan.IsNoOp) throw new InvalidDataException("No-op preview does not authorize a new firmware BIN.");
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("An existing Rust runner is mandatory for export.");
        var runnerBytes = File.ReadAllBytes(runner);
        var images = new[] { (Id: "A", Image: preview.Original), (Id: "B", Image: preview.Intermediate), (Id: "C", Image: preview.Output) };
        var limiter = new List<P28FixedLimiterRun>(); var adaptive = new List<P28FixedLimiterRun>();
        string? version = null, upstream = null; string[]? fixes = null;
        void Identity(SliceProcessResponse response, string operation)
        {
            var root = response.Response; var f = SliceRunnerIdentity.Validate(root, operation);
            var v = root.GetProperty("runnerVersion").GetString()!; var u = root.GetProperty("upstreamCommit").GetString()!;
            if (version is not null && (version != v || upstream != u || !fixes!.SequenceEqual(f))) throw new InvalidDataException("Runner identity changed during export validation.");
            version = v; upstream = u; fixes = f;
        }
        foreach (var item in LimiterScenarios(preview.Plan))
            foreach (var image in images)
            {
                var response = await SeededSliceProcess.ExchangeAsync(runner, P28LimiterValidator.CreateRequest(image.Image, item.Scenario), options, cancellationToken).ConfigureAwait(false);
                Identity(response, P28LimiterValidator.Operation);
                var report = P28LimiterValidator.AnalyzeExportImage(preview, image.Image, item.Scenario, response);
                if (report.HasFailure) throw new InvalidDataException("Mandatory limiter execution did not strictly complete.");
                foreach (var s in report.Sequences)
                {
                    var outcomes = new List<P28FixedLimiterOutcome>();
                    foreach (var row in s.Checkpoints)
                    {
                        var decision = P28AcquisitionValidator.ParseStage(row.Actual.GetProperty("decision"), 96, 0, [], null)!;
                        if (!P28FixedLimiterEditor.Footprint.All(decision.ExecutedInstructionBytes.Contains) || decision.ProgramReads.Contains(preview.Location.Offset))
                            throw new InvalidDataException("Actual immediate fetch is incomplete or compensation was read.");
                        var expected = row.Expected!;
                        outcomes.Add(new(row.Index, item.Scenario.Calls[row.Index].RawPeriod, expected.Context, expected.Threshold,
                            row.Actual.GetProperty("overspeedRequest").GetBoolean(), (expected.Before.Data012A & 128) != 0,
                            row.Actual.GetProperty("inhibitBranch").GetBoolean(), expected.After.Data018F, expected.After.Data0124, expected.After.RamCut, expected.After.RamResume));
                    }
                    limiter.Add(new(image.Id, image.Image.Hash, item.Id, item.Scenario.Digest, s.ScratchPattern,
                        s.Counts.RequestedCalls, s.Counts.StrictMatches, Digest(s.Checkpoints.Select(c => c.Actual).ToArray()),
                        Digest(s.Checkpoints.Select(c => c.Actual.GetProperty("stateAfter")).ToArray()), true, true, outcomes.AsReadOnly()));
                }
            }
        foreach (var item in AdaptiveScenarios())
            foreach (var image in images)
            {
                var response = await SeededSliceProcess.ExchangeAsync(runner, P28AdaptiveValidator.CreateRequest(image.Image, item.Scenario), options, cancellationToken).ConfigureAwait(false);
                Identity(response, P28AdaptiveValidator.Operation);
                var report = P28AdaptiveValidator.AnalyzeExportImage(preview, image.Image, item.Scenario, response);
                if (report.HasFailure) throw new InvalidDataException("Mandatory adaptive control did not strictly complete.");
                foreach (var s in report.Sequences)
                {
                    var outcomes = s.Checkpoints.Select(row => new P28FixedLimiterOutcome(row.Index, row.Inputs.Limiter.RawPeriod,
                        row.ThresholdSource!, row.SelectedThreshold!.Value, row.OverspeedRequest!.Value,
                        row.IndependentInhibit!.Value, row.MaskUpdateSkipped!.Value,
                        row.Expected!.After.Limiter.Data018F, row.Expected.After.Limiter.Data0124,
                        row.Expected.AfterProducer.Limiter.RamCut, row.Expected.AfterProducer.Limiter.RamResume)).ToArray();
                    // M1m's parser verifies every producer program read is in the unchanged bank range,
                    // and every instruction fetch is in the explicit producer/limiter/tick code ranges.
                    adaptive.Add(new(image.Id, image.Image.Hash, item.Id, item.Scenario.Digest, s.ScratchPattern,
                        s.Counts.RequestedCalls, s.Counts.StrictMatches, Digest(s.Checkpoints.Select(c => c.Actual).ToArray()),
                        Digest(s.Checkpoints.Select(c => c.Actual.GetProperty("stateAfter")).ToArray()), true, true, outcomes));
                }
            }
        var checksumResponse = await SeededSliceProcess.ExchangeAsync(runner, P28NativeChecksumVerifier.CreateRequest(images.Select(i => (i.Id, i.Image)).ToArray()), options, cancellationToken).ConfigureAwait(false);
        Identity(checksumResponse, "checksumBatch");
        var checks = CompareChecksum(images, checksumResponse);
        // Full trace equality includes ordered stores and history, not only final requests.
        // RAM controls intentionally exclude incidental immediate-load register values:
        // those are overwritten by RAM selection even when the selected threshold is unchanged.
        ValidateRelations(limiter, adaptive);
        cancellationToken.ThrowIfCancellationRequested();
        if (!runnerBytes.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during validation.");
        var evidence = new P28FixedLimiterEvidence(version!, upstream!, fixes!, preview.Plan.Digest(), CorpusId,
            limiter.AsReadOnly(), adaptive.AsReadOnly(), checks, true, true, true);
        RequireEvidence(preview, evidence);
        return new(preview, evidence);
    }
    internal static P28ChecksumExportObservation[] CompareChecksum((string Id, RomImage Image)[] images, SliceProcessResponse response)
    {
        _ = SliceRunnerIdentity.Validate(response.Response, "checksumBatch");
        _ = P28NativeChecksumVerifier.ValidateEntryContract(response.Response);
        var rows = response.Response.GetProperty("checksumCases").EnumerateArray().ToArray();
        if (rows.Length != 9) throw new InvalidDataException("Exactly three A/B/C checksum scratch cases required.");
        var result = new List<P28ChecksumExportObservation>();
        for (var i = 0; i < 3; i++)
            foreach (var pattern in new[] { 0, 85, 170 })
            {
                var found = rows.Where(r => r.GetProperty("imageIndex").GetInt32() == i && r.GetProperty("scratchPattern").GetInt32() == pattern).ToArray();
                if (found.Length != 1) throw new InvalidDataException("Missing/duplicate checksum image identity.");
                var run = P28NativeChecksumVerifier.CompareExecution(images[i].Image, found[0]);
                var residue = P28NativeChecksumArithmetic.Calculate(images[i].Image).ComputedResult;
                if (run.Status != NativeChecksumExecutionStatus.Match || !run.Complete || run.Invocations != 512 ||
                    !run.CoverageMatches || !run.IntermediateStateMatches || run.UsedAssumptions.Count != 0 ||
                    run.ComputedResult != residue || run.Decision != (residue == 0 ? "ResidueZero" : "NonzeroResidueFailure") ||
                    i != 1 && residue != 0) throw new InvalidDataException("Incomplete, conditional or mismatched native checksum execution.");
                result.Add(new(images[i].Id, images[i].Image.Hash, pattern, run.Status, run.Complete, run.ComputedResult.Value,
                    run.Decision!, run.Invocations, run.Steps, run.ProgramReadCount, run.CoverageMatches, run.IntermediateStateMatches, run.UsedAssumptions));
            }
        return result.ToArray();
    }
    internal static void ValidateRelations(IReadOnlyList<P28FixedLimiterRun> limiter, IReadOnlyList<P28FixedLimiterRun> adaptive)
    {
        foreach (var group in limiter.Concat(adaptive).GroupBy(r => (r.ScenarioId, r.ScratchPattern)))
        {
            var a = group.Single(r => r.ImageKind == "A"); var b = group.Single(r => r.ImageKind == "B"); var c = group.Single(r => r.ImageKind == "C");
            if (b.ObservationDigest != c.ObservationDigest || !P28LimiterValidator.Equal(b.Outcomes, c.Outcomes)) throw new InvalidDataException("B and C behavior differs.");
            if (a.ScenarioId.Contains("ram-only", StringComparison.Ordinal) && (a.PersistentStateDigest != c.PersistentStateDigest || !P28LimiterValidator.Equal(a.Outcomes, c.Outcomes)))
                throw new InvalidDataException("RAM-only control differs.");
        }
    }
    internal static string Digest<T>(T value) => HashUtilities.Sha256(System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value, JsonDefaults.Create(false))));
    internal static void RequireEvidence(P28FixedLimiterPreview p, P28FixedLimiterEvidence e)
    {
        if (e.PlanDigest != p.Plan.Digest() || e.CorpusId != CorpusId || !e.NativeValidationComplete || !e.IntermediateAndOutputAgree || !e.RamOnlyControlsAgree)
            throw new InvalidDataException("Stale or incomplete limiter execution evidence.");
        _ = SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { protocolVersion = 1, operation = "adaptiveLimiter", runnerVersion = e.RunnerVersion, upstreamCommit = e.UpstreamCommit, localSemanticFixes = e.LocalSemanticFixes }), "adaptiveLimiter");
        var images = new[] { ("A", p.Original), ("B", p.Intermediate), ("C", p.Output) };
        void Runs(IReadOnlyList<P28FixedLimiterRun> runs, (string Id, string Digest, int Count)[] scenarios, bool isAdaptive)
        {
            if (runs.Count != scenarios.Length * 9) throw new InvalidDataException("Incomplete mandatory corpus.");
            foreach (var scenario in scenarios)
                foreach (var (kind, image) in images)
                    foreach (var pattern in new[] { 0, 85, 170 })
                    {
                        var found = runs.Where(r => r.ImageKind == kind && r.ScenarioId == scenario.Id && r.ScratchPattern == pattern).ToArray();
                        if (found.Length != 1) throw new InvalidDataException("Missing/duplicate limiter evidence row.");
                        var r = found[0];
                        if (r.ImageHash != image.Hash || r.ScenarioDigest != scenario.Digest || r.Requested != scenario.Count ||
                            r.StrictMatches != r.Requested || r.Outcomes.Count != r.Requested || !r.OperandFetchVerified || !r.CompensationNotRead ||
                            r.ObservationDigest.Length != 64 || !r.ObservationDigest.All(Uri.IsHexDigit) || r.Outcomes.Where((o, i) => o.Index != i).Any())
                            throw new InvalidDataException("Forged, stale or incomplete limiter history.");
                        // Receipt verification re-derives descriptive outcomes; it still cannot
                        // authenticate that execution happened, nor mint the live export token.
                        P28FixedLimiterOutcome[] expected; var expectedStates = new List<object>();
                        if (isAdaptive)
                        {
                            var s = AdaptiveScenarios().Single(s => s.Id == scenario.Id).Scenario;
                            var model = new P28AdaptiveModel(image.Span, s.InitialState);
                            expected = s.Calls.Select((call, index) =>
                            {
                                var step = model.Step(call); var l = step.Limiter; expectedStates.Add(step.After);
                                return new P28FixedLimiterOutcome(index, call.Limiter.RawPeriod, l.Context, l.Threshold,
                                    l.OverspeedRequest, (l.Before.Data012A & 128) != 0, l.InhibitBranch, l.After.Data018F, l.After.Data0124, step.AfterProducer.Limiter.RamCut, step.AfterProducer.Limiter.RamResume);
                            }).ToArray();
                        }
                        else
                        {
                            var s = LimiterScenarios(p.Plan).Single(s => s.Id == scenario.Id).Scenario;
                            var model = new P28LimiterModel(image.Span, s.InitialState);
                            expected = s.Calls.Select((call, index) =>
                            {
                                var l = model.Step(call); expectedStates.Add(l.After);
                                return new P28FixedLimiterOutcome(index, call.RawPeriod, l.Context, l.Threshold, l.OverspeedRequest,
                                    (l.Before.Data012A & 128) != 0, l.InhibitBranch, l.After.Data018F, l.After.Data0124, l.After.RamCut, l.After.RamResume);
                            }).ToArray();
                        }
                        if (!P28LimiterValidator.Equal(r.Outcomes, expected) || r.PersistentStateDigest != Digest(expectedStates))
                            throw new InvalidDataException("Receipt outcomes/states disagree with independent original-parent history.");
                    }
        }
        Runs(e.LimiterRuns, LimiterScenarios(p.Plan).Select(s => (s.Id, s.Scenario.Digest, s.Scenario.Calls.Count)).ToArray(), false);
        Runs(e.AdaptiveRuns, AdaptiveScenarios().Select(s => (s.Id, s.Scenario.Digest, s.Scenario.Calls.Count)).ToArray(), true);
        if (e.ChecksumRuns.Count != 9) throw new InvalidDataException("Missing native checksum evidence.");
        foreach (var (kind, image) in images)
            foreach (var pattern in new[] { 0, 85, 170 })
            {
                var found = e.ChecksumRuns.Where(r => r.ImageKind == kind && r.ScratchPattern == pattern).ToArray();
                var residue = P28NativeChecksumArithmetic.Calculate(image).ComputedResult;
                if (found.Length != 1) throw new InvalidDataException("Missing/duplicate checksum receipt row.");
                var r = found[0];
                if (r.Hash != image.Hash || r.Status != NativeChecksumExecutionStatus.Match || !r.Complete || r.ComputedResult != residue ||
                    r.Decision != (residue == 0 ? "ResidueZero" : "NonzeroResidueFailure") || r.Invocations != 512 ||
                    r.Steps != (residue == 0 ? 104963 : 104968) || r.ProgramReadCount != (residue == 0 ? 32768 : 32769) ||
                    !r.CoverageMatches || !r.IntermediateStateMatches || r.UsedAssumptions.Count != 0)
                    throw new InvalidDataException("Invalid checksum receipt accounting.");
            }
        ValidateRelations(e.LimiterRuns, e.AdaptiveRuns);
    }
}
