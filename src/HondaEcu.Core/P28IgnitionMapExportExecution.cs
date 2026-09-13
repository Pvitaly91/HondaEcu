using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

public sealed record P28IgnitionMapExportOutcome(int Index, string MapId, int RawLoad, int RawMap0Rpm,
    int RawMap1Rpm, int LoadIndex, int RpmIndex, int LookupResult, int ConsumerFactor, long ConsumerProduct,
    int ConsumerOutput, IReadOnlyList<int> CellAddresses);
public sealed record P28IgnitionMapExportRun(string ImageKind, RomHash ImageHash, string ScenarioKind,
    string ScenarioDigest, int ScratchPattern, int ConsumerFactor, int Requested, int StrictMatches,
    string ObservationDigest, string ModelDigest, string IndependentControlDigest,
    IReadOnlyList<P28IgnitionMapExportOutcome> Outcomes);
public sealed record P28IgnitionMapCellEffect(string MapId, int Row, int Column, int Offset, int OldRawValue,
    int NewRawValue, int CorpusReadCount, int CombinedLookupChangeCount, int IsolatedLookupChangeCount,
    int IsolatedMaskedCount, string Effect, int FirstIsolatedWitnessIndex);
public sealed record P28IgnitionMapExportWitness(string MapId, int Index, int ScratchPattern, int RawLoad,
    int RawRpm, int OldLookup, int NewLookup, int OldConsumerOutput, int NewConsumerOutput, string Meaning);
public sealed record P28IgnitionConsumerFactorEvidence(int Factor, int ScenarioCalls, int ChangedLookupPairs,
    int PreservedOutputEffects, int MaskedOutputEffects, bool OnceSeededInitialState, bool NativeAbcStrict);
public sealed record P28IgnitionMapExportEvidence(string RunnerVersion, string UpstreamCommit,
    IReadOnlyList<string> LocalSemanticFixes, string PlanDigest, string CorpusId, string ScenarioDigest,
    int ScenarioCalls, int RectangleCorners, IReadOnlyList<P28IgnitionMapExportRun> MainRuns,
    IReadOnlyList<P28IgnitionMapExportRun> FactorRuns, IReadOnlyList<P28IgnitionConsumerFactorEvidence> FactorEvidence,
    IReadOnlyList<P28ChecksumExportObservation> ChecksumRuns, IReadOnlyList<P28IgnitionMapCellEffect> CellEffects,
    IReadOnlyList<P28IgnitionMapExportWitness> Witnesses, bool AllRequestedCellsRead,
    bool IntermediateAndOutputAgree, bool AxisCacheSelectorControlsAgree, bool FactorOnceSeeded,
    bool NativeValidationComplete);

public sealed class P28VerifiedIgnitionMapExport
{
    private readonly string _evidence;
    internal P28VerifiedIgnitionMapExport(P28IgnitionMapExportPreview preview,
        P28IgnitionMapExportEvidence evidence)
    { Preview = preview; _evidence = P28RawEditJson.Serialize(evidence, false); }
    public P28IgnitionMapExportPreview Preview { get; }
    public P28IgnitionMapExportEvidence Evidence => P28RawEditJson.Parse<P28IgnitionMapExportEvidence>(_evidence);
}

public static class P28IgnitionMapExportCorpus
{
    public const string Id = "ignition-map-export-abc-all-rectangles-history-effects-factor0-v1";
    public const int RectangleCorners = 342;
    public static IReadOnlyList<int> RequiredFactors { get; } = Array.AsReadOnly(new[] { 1, 127, 128, 173, 255 });

    private static P28IgnitionMapCall Call(int index, string mapId, int load, int rpm) =>
        new(index, mapId, (byte)load, (byte)rpm, (byte)((index * 37 + 19) & 255));

    public static P28IgnitionMapScenario Create(P28IgnitionMapExportPreview preview) =>
        Create(preview, preview.Output);

    internal static P28IgnitionMapScenario Create(P28IgnitionMapExportPreview preview, RomImage output)
    {
        var image = preview.Original; var calls = new List<(string MapId, int Load, int Rpm)>();
        int Axis(int origin, int index) => image.Span[origin + index];
        int Mid(int origin, int index) => (Axis(origin, index) + (Axis(origin, index + 1) == 0 ? 256 : Axis(origin, index + 1))) / 2;
        int NearUpper(int origin, int index) => (Axis(origin, index + 1) == 0 ? 256 : Axis(origin, index + 1)) - 1;
        foreach (var mapId in new[] { "ignition_map_0", "ignition_map_1" })
        {
            var rpmOrigin = mapId == "ignition_map_0" ? P28IgnitionMapContract.Map0RpmAxisOrigin : P28IgnitionMapContract.Map1RpmAxisOrigin;
            for (var row = 0; row < 19; row++) for (var column = 0; column < 9; column++)
                    calls.Add((mapId, Axis(P28IgnitionMapContract.LoadAxisOrigin, column), Axis(rpmOrigin, row)));
        }
        foreach (var mapId in new[] { "ignition_map_0", "ignition_map_1" })
        {
            var rpmOrigin = mapId == "ignition_map_0" ? P28IgnitionMapContract.Map0RpmAxisOrigin : P28IgnitionMapContract.Map1RpmAxisOrigin;
            for (var row = 0; row < 19; row++) calls.Add((mapId, Mid(P28IgnitionMapContract.LoadAxisOrigin, row % 9), Mid(rpmOrigin, row)));
            for (var row = 0; row < 19; row++) calls.Add((mapId, Axis(P28IgnitionMapContract.LoadAxisOrigin, row % 9), NearUpper(rpmOrigin, row)));
            for (var column = 0; column < 9; column++) calls.Add((mapId, NearUpper(P28IgnitionMapContract.LoadAxisOrigin, column), Axis(rpmOrigin, column % 19)));
            calls.Add((mapId, 0, 0)); calls.Add((mapId, 255, 0)); calls.Add((mapId, 0, 255)); calls.Add((mapId, 255, 255));
        }
        foreach (var map in preview.Plan.Maps.Where(group => group.DomainAudit.ChangedResults > 0))
        {
            var found = false;
            for (var rpm = 0; rpm <= 255 && !found; rpm++) for (var load = 0; load <= 255 && !found; load++)
                    if (P28IgnitionMapModel.ProjectNumeric(preview.Original.Span, map.MapId, rpm, load).LookupResult !=
                        P28IgnitionMapModel.ProjectNumeric(output.Span, map.MapId, rpm, load).LookupResult)
                    { calls.Add((map.MapId, load, rpm)); found = true; }
            if (!found) throw new InvalidDataException("Domain audit predicts a changed ignition result but no witness input exists.");
        }
        calls.AddRange(new[]
        {
            ("ignition_map_0", 255, 255), ("ignition_map_1", 0, 0), ("ignition_map_0", 127, 193),
            ("ignition_map_1", 127, 193), ("ignition_map_0", 127, 193), ("ignition_map_1", 254, 254),
            ("ignition_map_0", 1, 1), ("ignition_map_1", 1, 1), ("ignition_map_0", 255, 0),
            ("ignition_map_1", 0, 255), ("ignition_map_0", 0, 0), ("ignition_map_1", 255, 255)
        });
        if (calls.Count > 512) throw new InvalidDataException("Mandatory ignition-map corpus exceeds the runner bound.");
        var dense = calls.Select((call, index) => Call(index, call.MapId, call.Load, call.Rpm)).ToArray();
        return P28IgnitionMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 0, 0), dense,
            Id + "; mandatory/internal/not-externally-shortenable", null);
    }

    public static P28IgnitionMapScenario CreateFactor(P28IgnitionMapExportPreview preview, int factor) =>
        CreateFactor(preview, preview.Output, factor);

    internal static P28IgnitionMapScenario CreateFactor(P28IgnitionMapExportPreview preview,
        RomImage output, int factor)
    {
        if (!RequiredFactors.Contains(factor)) throw new ArgumentOutOfRangeException(nameof(factor));
        var selected = new List<(string MapId, int Load, int Rpm)>
        {
            ("ignition_map_0", 0, 0), ("ignition_map_0", 255, 255),
            ("ignition_map_1", 0, 0), ("ignition_map_1", 255, 255),
            ("ignition_map_0", 127, 193), ("ignition_map_1", 127, 193)
        };
        foreach (var map in preview.Plan.Maps.Where(group => group.DomainAudit.ChangedResults > 0))
        {
            (int Load, int Rpm)? effect = null; (int Load, int Rpm)? masked = null;
            for (var rpm = 0; rpm <= 255 && (effect is null || masked is null); rpm++)
                for (var load = 0; load <= 255 && (effect is null || masked is null); load++)
                {
                    var a = P28IgnitionMapModel.ProjectNumeric(preview.Original.Span, map.MapId, rpm, load).LookupResult;
                    var c = P28IgnitionMapModel.ProjectNumeric(output.Span, map.MapId, rpm, load).LookupResult;
                    if (a == c) continue;
                    var outputA = P28IgnitionMapModel.Consume(a, factor).Output;
                    var outputC = P28IgnitionMapModel.Consume(c, factor).Output;
                    if (outputA == outputC) masked ??= (load, rpm); else effect ??= (load, rpm);
                }
            if (effect is { } e) selected.Add((map.MapId, e.Load, e.Rpm));
            if (masked is { } m) selected.Add((map.MapId, m.Load, m.Rpm));
        }
        var calls = selected.Select((call, index) => Call(index, call.MapId, call.Load, call.Rpm)).ToArray();
        return P28IgnitionMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, (byte)factor, 0), calls,
            $"ignition-map-export-factor-{factor}; once-seeded initial state; no per-call factor writes", null);
    }
}

public static class P28IgnitionMapExportExecution
{
    internal static (string Id, RomImage Image)[] Images(P28IgnitionMapExportPreview preview) =>
        [("A", preview.Original), ("B", preview.Intermediate), ("C", preview.Output)];

    private static P28IgnitionMapExportOutcome Outcome(P28IgnitionMapCheckpoint checkpoint)
    {
        var expected = checkpoint.Expected ?? throw new InvalidDataException("Strict ignition outcome lacks its independent model.");
        var rpmPosition = checkpoint.Inputs.MapId == "ignition_map_0" ? expected.Map0Rpm : expected.Map1Rpm;
        return new(checkpoint.Index, checkpoint.Inputs.MapId, checkpoint.Inputs.RawLoad, checkpoint.Inputs.RawMap0Rpm,
            checkpoint.Inputs.RawMap1Rpm, expected.Load.Index, rpmPosition.Index, checkpoint.ActualLookupResult!.Value,
            expected.Consumer.RawFactor, expected.Consumer.Product, checkpoint.ActualConsumerOutput!.Value,
            expected.Operands.CellAddresses);
    }

    private static string Controls(IEnumerable<P28IgnitionMapCheckpoint> checkpoints) => Digest(checkpoints.Select(checkpoint =>
    {
        var expected = checkpoint.Expected!;
        return new
        {
            expected.SelectedMap,
            expected.SelectedOrigin,
            Map0 = new { expected.Map0Rpm.Index, expected.Map0Rpm.Fraction, expected.Map0Rpm.OrderedProgramReads },
            Map1 = new { expected.Map1Rpm.Index, expected.Map1Rpm.Fraction, expected.Map1Rpm.OrderedProgramReads },
            Load = new { expected.Load.Index, expected.Load.Fraction, expected.Load.OrderedProgramReads },
            State = expected.After with { ConsumerOutput0248 = (byte)0 }
        };
    }).ToArray());

    public static async Task<P28VerifiedIgnitionMapExport> ValidateAsync(P28IgnitionMapExportPreview preview,
        string runner, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = P28IgnitionMapExportEditor.Reproduce(preview.Original, preview.Profile, preview.Binding, true,
            preview.Location, preview.Plan);
        if (preview.Plan.IsNoOp) throw new InvalidDataException("A no-op ignition-map plan cannot export a firmware BIN.");
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("The existing Rust runner is mandatory.");
        var runnerBytes = File.ReadAllBytes(runner);
        var local = await ValidateSuitesAsync(preview, runner, options, cancellationToken).ConfigureAwait(false);
        var checksumResponse = await SeededSliceProcess.ExchangeAsync(runner,
            P28NativeChecksumVerifier.CreateRequest(Images(preview).Select(image => (image.Id, image.Image)).ToArray()),
            options, cancellationToken).ConfigureAwait(false);
        var checksumFixes = SliceRunnerIdentity.Validate(checksumResponse.Response, "checksumBatch");
        if (local.RunnerVersion != checksumResponse.Response.GetProperty("runnerVersion").GetString() ||
            local.UpstreamCommit != checksumResponse.Response.GetProperty("upstreamCommit").GetString() ||
            !local.LocalSemanticFixes.SequenceEqual(checksumFixes))
            throw new InvalidDataException("Runner identity changed before checksum validation.");
        var evidence = local with { ChecksumRuns = CompareChecksum(Images(preview), checksumResponse) };
        if (!runnerBytes.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during validation.");
        RequireEvidence(preview, evidence);
        return new(preview, evidence);
    }

    internal static async Task<P28IgnitionMapExportEvidence> ValidateSuitesAsync(
        P28IgnitionMapExportPreview preview, string runner, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
        => await ValidateSuitesCoreAsync(preview, Images(preview), runner, options,
            cancellationToken).ConfigureAwait(false);

    internal static async Task<P28IgnitionMapExportEvidence> ValidateSuitesAsync(
        P28IgnitionMapExportPreview family, P28UnifiedCalibrationPreview combined, string runner,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
        => await ValidateSuitesCoreAsync(family, combined.Images, runner, options,
            cancellationToken).ConfigureAwait(false);

    private static async Task<P28IgnitionMapExportEvidence> ValidateSuitesCoreAsync(
        P28IgnitionMapExportPreview preview, (string Id, RomImage Image)[] images, string runner,
        SliceProcessOptions? options, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("The existing Rust runner is mandatory.");
        var output = images.Single(image => image.Id == "C").Image;
        var mainScenario = P28IgnitionMapExportCorpus.Create(preview, output);
        var mainRuns = new List<P28IgnitionMapExportRun>(); var factorRuns = new List<P28IgnitionMapExportRun>();
        string? version = null, upstream = null; string[]? fixes = null;
        void Identity(SliceProcessResponse response)
        {
            var found = SliceRunnerIdentity.Validate(response.Response, P28IgnitionMapValidator.Operation);
            var nextVersion = response.Response.GetProperty("runnerVersion").GetString()!;
            var nextUpstream = response.Response.GetProperty("upstreamCommit").GetString()!;
            if (version is not null && (version != nextVersion || upstream != nextUpstream || !fixes!.SequenceEqual(found)))
                throw new InvalidDataException("Runner identity changed during ignition-map export validation.");
            version = nextVersion; upstream = nextUpstream; fixes = found;
        }
        async Task RunScenario(P28IgnitionMapScenario scenario, string kind, ICollection<P28IgnitionMapExportRun> target)
        {
            foreach (var image in images)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var response = await SeededSliceProcess.ExchangeAsync(runner,
                    P28IgnitionMapValidator.CreateRequest(image.Image, scenario), options, cancellationToken).ConfigureAwait(false);
                Identity(response); var report = P28IgnitionMapValidator.AnalyzeImage(image.Image, scenario, response, image.Id);
                foreach (var sequence in report.Sequences)
                {
                    if (sequence.Checkpoints.Any(checkpoint => checkpoint.Disposition != "StrictMatch"))
                        throw new InvalidDataException("Mandatory ignition-map corpus did not strictly complete.");
                    var outcomes = sequence.Checkpoints.Select(Outcome).ToArray();
                    target.Add(new(image.Id, image.Image.Hash, kind, scenario.Digest, sequence.ScratchPattern,
                        scenario.InitialState.ConsumerFactor0247, outcomes.Length, outcomes.Length,
                        Digest(sequence.Checkpoints.Select(checkpoint => checkpoint.Actual).ToArray()), Digest(outcomes),
                        Controls(sequence.Checkpoints), outcomes));
                }
            }
        }
        await RunScenario(mainScenario, "factor0-main", mainRuns).ConfigureAwait(false);
        foreach (var factor in P28IgnitionMapExportCorpus.RequiredFactors)
            await RunScenario(P28IgnitionMapExportCorpus.CreateFactor(preview, output, factor), $"factor-{factor}", factorRuns).ConfigureAwait(false);
        ValidateRelations(mainRuns); ValidateFactorRelations(factorRuns);
        var effects = Effects(preview, mainScenario, mainRuns); var witnesses = Witnesses(preview, mainRuns);
        var factorEvidence = FactorEvidence(preview, factorRuns);
        return new P28IgnitionMapExportEvidence(version!, upstream!, fixes!, preview.Plan.Digest(),
            P28IgnitionMapExportCorpus.Id, mainScenario.Digest, mainScenario.Calls.Count,
            P28IgnitionMapExportCorpus.RectangleCorners, mainRuns, factorRuns, factorEvidence, [], effects,
            witnesses, AllRequestedCellsRead(preview, mainRuns), true, true, true, true);
    }

    internal static P28IgnitionMapCellEffect[] Effects(P28IgnitionMapExportPreview preview,
        P28IgnitionMapScenario scenario, IReadOnlyList<P28IgnitionMapExportRun> runs)
    {
        var a = runs.Single(run => run.ImageKind == "A" && run.ScratchPattern == 0);
        var c = runs.Single(run => run.ImageKind == "C" && run.ScratchPattern == 0);
        return preview.Plan.Maps.SelectMany(group => group.Cells).Where(cell => cell.OldRawValue != cell.NewRawValue)
            .Select(cell =>
            {
                var reads = a.Outcomes.Count(outcome => outcome.CellAddresses.Contains(cell.Offset));
                var combined = a.Outcomes.Zip(c.Outcomes).Count(pair => pair.First.MapId == cell.MapId &&
                    pair.First.LookupResult != pair.Second.LookupResult && pair.First.CellAddresses.Contains(cell.Offset));
                var isolated = preview.Original.CreateModifiedCopy([new(cell.Offset, [(byte)cell.NewRawValue])]);
                var isolatedChanges = 0; var first = -1;
                foreach (var call in scenario.Calls.Where(call => call.MapId == cell.MapId))
                {
                    var before = P28IgnitionMapModel.ProjectNumeric(preview.Original.Span, call.MapId,
                        call.RawMap0Rpm, call.RawLoad);
                    var after = P28IgnitionMapModel.ProjectNumeric(isolated.Span, call.MapId,
                        call.RawMap0Rpm, call.RawLoad);
                    if (before.LookupResult != after.LookupResult) { isolatedChanges++; if (first < 0) first = call.Index; }
                }
                var effect = isolatedChanges > 0 ? "IsolatedLookupEffect" : reads > 0 ?
                    "ReadMaskedByWeightOrSequentialTruncation" : "NotRead";
                return new P28IgnitionMapCellEffect(cell.MapId, cell.Row, cell.Column, cell.Offset,
                    cell.OldRawValue, cell.NewRawValue, reads, combined, isolatedChanges, reads - isolatedChanges,
                    effect, first);
            }).ToArray();
    }

    internal static bool AllRequestedCellsRead(P28IgnitionMapExportPreview preview,
        IReadOnlyList<P28IgnitionMapExportRun> runs)
    {
        var baseline = runs.Single(run => run.ImageKind == "A" && run.ScratchPattern == 0);
        return preview.Plan.Maps.SelectMany(group => group.Cells).All(cell =>
            baseline.Outcomes.Any(outcome => outcome.MapId == cell.MapId &&
                outcome.CellAddresses.Contains(cell.Offset)));
    }

    internal static P28IgnitionMapExportWitness[] Witnesses(P28IgnitionMapExportPreview preview,
        IReadOnlyList<P28IgnitionMapExportRun> runs)
    {
        var result = new List<P28IgnitionMapExportWitness>();
        foreach (var map in preview.Plan.Maps.Where(group => group.DomainAudit.ChangedResults > 0))
        {
            var a = runs.Single(run => run.ImageKind == "A" && run.ScratchPattern == 0);
            var c = runs.Single(run => run.ImageKind == "C" && run.ScratchPattern == 0);
            var pair = a.Outcomes.Zip(c.Outcomes).FirstOrDefault(rows => rows.First.MapId == map.MapId &&
                rows.First.LookupResult != rows.Second.LookupResult);
            if (pair.First is null) throw new InvalidDataException($"No native A/C witness for changed {map.MapId}.");
            result.Add(new(map.MapId, pair.First.Index, 0, pair.First.RawLoad, pair.First.RawMap0Rpm,
                pair.First.LookupResult, pair.Second.LookupResult, pair.First.ConsumerOutput,
                pair.Second.ConsumerOutput, "Native factor-0 lookup/consumer witness; raw values, not physical timing units."));
        }
        return result.ToArray();
    }

    internal static P28IgnitionConsumerFactorEvidence[] FactorEvidence(P28IgnitionMapExportPreview preview,
        IReadOnlyList<P28IgnitionMapExportRun> runs) => P28IgnitionMapExportCorpus.RequiredFactors.Select(factor =>
    {
        var a = runs.Single(run => run.ConsumerFactor == factor && run.ImageKind == "A" && run.ScratchPattern == 0);
        var c = runs.Single(run => run.ConsumerFactor == factor && run.ImageKind == "C" && run.ScratchPattern == 0);
        var changed = a.Outcomes.Zip(c.Outcomes).Where(pair => pair.First.LookupResult != pair.Second.LookupResult).ToArray();
        return new P28IgnitionConsumerFactorEvidence(factor, a.Outcomes.Count, changed.Length,
            changed.Count(pair => pair.First.ConsumerOutput != pair.Second.ConsumerOutput),
            changed.Count(pair => pair.First.ConsumerOutput == pair.Second.ConsumerOutput), true, true);
    }).ToArray();

    internal static void ValidateRelations(IReadOnlyList<P28IgnitionMapExportRun> runs)
    {
        foreach (var pattern in new[] { 0, 85, 170 })
        {
            var a = runs.Single(run => run.ImageKind == "A" && run.ScratchPattern == pattern);
            var b = runs.Single(run => run.ImageKind == "B" && run.ScratchPattern == pattern);
            var c = runs.Single(run => run.ImageKind == "C" && run.ScratchPattern == pattern);
            if (b.ModelDigest != c.ModelDigest || !P28LimiterValidator.Equal(b.Outcomes, c.Outcomes))
                throw new InvalidDataException("Ignition-map B/C non-checksum behavior differs.");
            if (a.IndependentControlDigest != c.IndependentControlDigest)
                throw new InvalidDataException("Ignition-map A/C axis, cache, selector or history controls differ.");
        }
    }

    internal static void ValidateFactorRelations(IReadOnlyList<P28IgnitionMapExportRun> runs)
    {
        foreach (var factor in P28IgnitionMapExportCorpus.RequiredFactors)
        {
            var subset = runs.Where(run => run.ConsumerFactor == factor).ToArray();
            if (subset.Length != 9) throw new InvalidDataException("Missing or duplicate once-seeded factor A/B/C runs.");
            ValidateRelations(subset);
        }
    }

    private static P28IgnitionMapExportOutcome[] Expected(RomImage image, P28IgnitionMapScenario scenario)
    {
        var model = new P28IgnitionMapModel(image, scenario.InitialState);
        return scenario.Calls.Select(call =>
        {
            var step = model.Step(call); var position = call.MapId == "ignition_map_0" ? step.Map0Rpm : step.Map1Rpm;
            return new P28IgnitionMapExportOutcome(call.Index, call.MapId, call.RawLoad, call.RawMap0Rpm,
                call.RawMap1Rpm, step.Load.Index, position.Index, step.Operands.LookupResult,
                step.Consumer.RawFactor, step.Consumer.Product, step.Consumer.Output, step.Operands.CellAddresses);
        }).ToArray();
    }

    private static void RequireRuns(P28IgnitionMapExportPreview preview,
        (string Id, RomImage Image)[] images, P28IgnitionMapScenario scenario,
        IReadOnlyList<P28IgnitionMapExportRun> runs, string kind)
    {
        foreach (var image in images) foreach (var pattern in new[] { 0, 85, 170 })
            {
                var found = runs.Where(run => run.ImageKind == image.Id && run.ScratchPattern == pattern).ToArray();
                if (found.Length != 1) throw new InvalidDataException("Missing or duplicate ignition-map run.");
                var run = found[0]; var expected = Expected(image.Image, scenario);
                if (run.ImageHash != image.Image.Hash || run.ScenarioKind != kind || run.ScenarioDigest != scenario.Digest ||
                    run.ConsumerFactor != scenario.InitialState.ConsumerFactor0247 || run.Requested != scenario.Calls.Count ||
                    run.StrictMatches != run.Requested || run.Outcomes.Count != run.Requested ||
                    !P28LimiterValidator.Equal(run.Outcomes, expected) || run.ModelDigest != Digest(expected) ||
                    run.ObservationDigest.Length != 64 || !run.ObservationDigest.All(Uri.IsHexDigit))
                    throw new InvalidDataException("Forged, stale or contradictory ignition-map history.");
            }
    }

    internal static void RequireEvidence(P28IgnitionMapExportPreview preview,
        P28IgnitionMapExportEvidence evidence) => RequireEvidenceCore(preview, Images(preview), evidence);

    internal static void RequireEvidence(P28IgnitionMapExportPreview family,
        P28UnifiedCalibrationPreview combined, P28IgnitionMapExportEvidence evidence) =>
        RequireEvidenceCore(family, combined.Images, evidence);

    private static void RequireEvidenceCore(P28IgnitionMapExportPreview preview,
        (string Id, RomImage Image)[] images, P28IgnitionMapExportEvidence evidence)
    {
        var output = images.Single(image => image.Id == "C").Image;
        var main = P28IgnitionMapExportCorpus.Create(preview, output);
        if (evidence.PlanDigest != preview.Plan.Digest() || evidence.CorpusId != P28IgnitionMapExportCorpus.Id ||
            evidence.ScenarioDigest != main.Digest || evidence.ScenarioCalls != main.Calls.Count ||
            evidence.RectangleCorners != P28IgnitionMapExportCorpus.RectangleCorners || evidence.MainRuns.Count != 9 ||
            evidence.FactorRuns.Count != 45 || !evidence.AllRequestedCellsRead || !evidence.IntermediateAndOutputAgree ||
            !evidence.AxisCacheSelectorControlsAgree || !evidence.FactorOnceSeeded || !evidence.NativeValidationComplete)
            throw new InvalidDataException("Stale or incomplete ignition-map execution evidence.");
        RequireRuns(preview, images, main, evidence.MainRuns, "factor0-main"); ValidateRelations(evidence.MainRuns);
        foreach (var factor in P28IgnitionMapExportCorpus.RequiredFactors)
        {
            var scenario = P28IgnitionMapExportCorpus.CreateFactor(preview, output, factor);
            RequireRuns(preview, images, scenario, evidence.FactorRuns.Where(run => run.ConsumerFactor == factor).ToArray(),
                $"factor-{factor}");
        }
        ValidateFactorRelations(evidence.FactorRuns);
        var factorEvidence = FactorEvidence(preview, evidence.FactorRuns);
        if (!P28LimiterValidator.Equal(evidence.FactorEvidence, factorEvidence) ||
            evidence.FactorEvidence.Any(row => !row.OnceSeededInitialState || !row.NativeAbcStrict))
            throw new InvalidDataException("Ignition factor evidence differs.");
        if (evidence.AllRequestedCellsRead != AllRequestedCellsRead(preview, evidence.MainRuns))
            throw new InvalidDataException("Ignition requested-cell read coverage differs.");
        var effects = Effects(preview, main, evidence.MainRuns);
        if (!P28LimiterValidator.Equal(evidence.CellEffects, effects) || evidence.CellEffects.Any(effect => effect.CorpusReadCount == 0))
            throw new InvalidDataException("Ignition-map per-cell effect evidence is incomplete.");
        var witnesses = Witnesses(preview, evidence.MainRuns);
        if (!P28LimiterValidator.Equal(evidence.Witnesses, witnesses)) throw new InvalidDataException("Ignition-map witness evidence differs.");
        P28FixedLimiterExecution.RequireChecksumEvidence(images.Select(image => (image.Id, image.Image)).ToArray(),
            evidence.ChecksumRuns);
    }
}
