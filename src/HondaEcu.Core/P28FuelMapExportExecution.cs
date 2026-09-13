using System.Text.Json;
using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

public sealed record P28FuelMapExportOutcome(int Index, string MapId, int RawLoad, int RawRpm, int LoadIndex,
    int RpmIndex, int LookupResult, int ConsumerOutput, IReadOnlyList<int> CellAddresses);
public sealed record P28FuelMapExportRun(string ImageKind, RomHash ImageHash, string ScenarioDigest, int ScratchPattern,
    int Requested, int StrictMatches, string ObservationDigest, string ModelDigest, string IndependentControlDigest,
    IReadOnlyList<P28FuelMapExportOutcome> Outcomes);
public sealed record P28FuelMapCellEffect(string MapId, int Row, int Column, int Offset, int OldRawValue, int NewRawValue,
    int CorpusReadCount, int CombinedLookupChangeCount, int IsolatedLookupChangeCount, int IsolatedMaskedCount,
    string Effect, int FirstIsolatedWitnessIndex);
public sealed record P28FuelMapExportWitness(string MapId, int Index, int ScratchPattern, int RawLoad, int RawRpm,
    int OldLookup, int NewLookup, int OldConsumerOutput, int NewConsumerOutput, string Meaning);
public sealed record P28FuelMapExportEvidence(string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string PlanDigest, string CorpusId, string ScenarioDigest, int ScenarioCalls, int RectangleCorners,
    IReadOnlyList<P28FuelMapExportRun> Runs, IReadOnlyList<P28ChecksumExportObservation> ChecksumRuns,
    IReadOnlyList<P28FuelMapCellEffect> CellEffects, IReadOnlyList<P28FuelMapExportWitness> Witnesses,
    bool AllRequestedCellsRead, bool IntermediateAndOutputAgree, bool AxisCacheSelectorControlsAgree,
    bool NativeValidationComplete);

public sealed class P28VerifiedFuelMapExport
{
    private readonly string _evidence;
    internal P28VerifiedFuelMapExport(P28FuelMapExportPreview preview, P28FuelMapExportEvidence evidence)
    { Preview = preview; _evidence = P28RawEditJson.Serialize(evidence, false); }
    public P28FuelMapExportPreview Preview { get; }
    public P28FuelMapExportEvidence Evidence => P28RawEditJson.Parse<P28FuelMapExportEvidence>(_evidence);
}

public static class P28FuelMapExportCorpus
{
    public const string Id = "fuel-map-export-abc-all-rectangles-history-effects-v1";
    public const int RectangleCorners = 342;

    public static P28FuelMapScenario Create(P28FuelMapExportPreview preview) =>
        Create(preview, preview.Output);

    internal static P28FuelMapScenario Create(P28FuelMapExportPreview preview, RomImage output)
    {
        var image = preview.Original; var calls = new List<(string MapId, int Load, int Rpm)>();
        int Axis(int origin, int index) => image.Span[origin + index];
        int Mid(int origin, int index) => (Axis(origin, index) + (Axis(origin, index + 1) == 0 ? 256 : Axis(origin, index + 1))) / 2;
        int NearUpper(int origin, int index) => (Axis(origin, index + 1) == 0 ? 256 : Axis(origin, index + 1)) - 1;
        foreach (var mapId in new[] { "map_0", "map_1" })
        {
            var rpmOrigin = mapId == "map_0" ? P28FuelMapContract.Map0RpmAxisOrigin : P28FuelMapContract.Map1RpmAxisOrigin;
            for (var row = 0; row < 19; row++) for (var column = 0; column < 9; column++)
                    calls.Add((mapId, Axis(P28FuelMapContract.LoadAxisOrigin, column), Axis(rpmOrigin, row)));
        }
        foreach (var mapId in new[] { "map_0", "map_1" })
        {
            var rpmOrigin = mapId == "map_0" ? P28FuelMapContract.Map0RpmAxisOrigin : P28FuelMapContract.Map1RpmAxisOrigin;
            for (var row = 0; row < 19; row++) calls.Add((mapId, Mid(P28FuelMapContract.LoadAxisOrigin, row % 9), Mid(rpmOrigin, row)));
            for (var row = 0; row < 19; row++) calls.Add((mapId, Axis(P28FuelMapContract.LoadAxisOrigin, row % 9), NearUpper(rpmOrigin, row)));
            for (var column = 0; column < 9; column++) calls.Add((mapId, NearUpper(P28FuelMapContract.LoadAxisOrigin, column), Axis(rpmOrigin, column % 19)));
            calls.Add((mapId, 0, 0)); calls.Add((mapId, 255, 0)); calls.Add((mapId, 0, 255)); calls.Add((mapId, 255, 255));
        }
        // Ensure a native A/C witness for each changed map whenever the exhaustive arithmetic audit predicts one.
        foreach (var map in preview.Plan.Maps.Where(group => group.DomainAudit.ChangedResults > 0))
        {
            var found = false;
            for (var rpm = 0; rpm <= 255 && !found; rpm++) for (var load = 0; load <= 255 && !found; load++)
                    if (P28FuelMapModel.ProjectNumeric(preview.Original.Span, map.MapId, rpm, load).LookupResult !=
                        P28FuelMapModel.ProjectNumeric(output.Span, map.MapId, rpm, load).LookupResult)
                    { calls.Add((map.MapId, load, rpm)); found = true; }
            if (!found) throw new InvalidDataException("Domain audit predicts a changed result but no witness input exists.");
        }
        // Deliberate reversals, repeats and map alternation exercise persistent axis-cache history.
        var history = new[]
        {
            ("map_0", 255, 255), ("map_1", 0, 0), ("map_0", 127, 193), ("map_1", 127, 193),
            ("map_0", 127, 193), ("map_1", 254, 254), ("map_0", 1, 1), ("map_1", 1, 1),
            ("map_0", 255, 0), ("map_1", 0, 255), ("map_0", 0, 0), ("map_1", 255, 255)
        };
        calls.AddRange(history);
        if (calls.Count > 512) throw new InvalidDataException("Mandatory fuel-map corpus exceeds the runner bound.");
        var dense = calls.Select((call, index) => new P28FuelMapCall(index, call.MapId, (byte)call.Load,
            (byte)(call.MapId == "map_0" ? call.Rpm : (index * 37) & 255),
            (byte)(call.MapId == "map_1" ? call.Rpm : (index * 53) & 255))).ToArray();
        return P28FuelMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 17, 0), dense,
            Id + "; mandatory/internal/not-externally-shortenable", null);
    }
}

public static class P28FuelMapExportExecution
{
    internal static (string Id, RomImage Image)[] Images(P28FuelMapExportPreview preview) =>
        [("A", preview.Original), ("B", preview.Intermediate), ("C", preview.Output)];

    private static P28FuelMapExportOutcome Outcome(P28FuelMapCheckpoint checkpoint)
    {
        var expected = checkpoint.Expected ?? throw new InvalidDataException("Strict fuel outcome lacks its independent model.");
        var rpm = checkpoint.Inputs.MapId == "map_0" ? checkpoint.Inputs.RawMap0Rpm : checkpoint.Inputs.RawMap1Rpm;
        var rpmPosition = checkpoint.Inputs.MapId == "map_0" ? expected.Map0Rpm : expected.Map1Rpm;
        return new(checkpoint.Index, checkpoint.Inputs.MapId, checkpoint.Inputs.RawLoad, rpm,
            expected.Load.Index, rpmPosition.Index, checkpoint.ActualLookupResult!.Value, checkpoint.ActualConsumerOutput!.Value,
            expected.Operands.CellAddresses);
    }

    private static string Controls(IEnumerable<P28FuelMapCheckpoint> checkpoints) => Digest(checkpoints.Select(checkpoint =>
    {
        var expected = checkpoint.Expected!;
        return new
        {
            expected.SelectedMap,
            expected.SelectedOrigin,
            Map0 = new { expected.Map0Rpm.Index, expected.Map0Rpm.Fraction, expected.Map0Rpm.OrderedProgramReads },
            Map1 = new { expected.Map1Rpm.Index, expected.Map1Rpm.Fraction, expected.Map1Rpm.OrderedProgramReads },
            Load = new { expected.Load.Index, expected.Load.Fraction, expected.Load.OrderedProgramReads },
            State = expected.After with { ConsumerOutput0140 = 0 }
        };
    }).ToArray());

    public static async Task<P28VerifiedFuelMapExport> ValidateAsync(P28FuelMapExportPreview preview, string runner,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        preview = P28FuelMapExportEditor.Reproduce(preview.Original, preview.Profile, preview.Binding, true, preview.Location, preview.Plan);
        if (preview.Plan.IsNoOp) throw new InvalidDataException("A no-op fuel-map plan cannot export a firmware BIN.");
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
        cancellationToken.ThrowIfCancellationRequested();
        if (!runnerBytes.AsSpan().SequenceEqual(File.ReadAllBytes(runner))) throw new InvalidDataException("Runner changed during validation.");
        RequireEvidence(preview, evidence);
        return new(preview, evidence);
    }

    internal static async Task<P28FuelMapExportEvidence> ValidateSuitesAsync(P28FuelMapExportPreview preview,
        string runner, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
        => await ValidateSuitesCoreAsync(preview, Images(preview), runner, options,
            cancellationToken).ConfigureAwait(false);

    internal static async Task<P28FuelMapExportEvidence> ValidateSuitesAsync(P28FuelMapExportPreview family,
        P28UnifiedCalibrationPreview combined, string runner, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
        => await ValidateSuitesCoreAsync(family, combined.Images, runner, options,
            cancellationToken).ConfigureAwait(false);

    private static async Task<P28FuelMapExportEvidence> ValidateSuitesCoreAsync(
        P28FuelMapExportPreview preview, (string Id, RomImage Image)[] images, string runner,
        SliceProcessOptions? options, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (string.IsNullOrWhiteSpace(runner) || !File.Exists(runner)) throw new InvalidDataException("The existing Rust runner is mandatory.");
        var scenario = P28FuelMapExportCorpus.Create(preview, images.Single(image => image.Id == "C").Image);
        var runs = new List<P28FuelMapExportRun>();
        string? version = null, upstream = null; string[]? fixes = null;
        void Identity(SliceProcessResponse response, string operation)
        {
            var found = SliceRunnerIdentity.Validate(response.Response, operation);
            var nextVersion = response.Response.GetProperty("runnerVersion").GetString()!;
            var nextUpstream = response.Response.GetProperty("upstreamCommit").GetString()!;
            if (version is not null && (version != nextVersion || upstream != nextUpstream || !fixes!.SequenceEqual(found)))
                throw new InvalidDataException("Runner identity changed during fuel-map export validation.");
            version = nextVersion; upstream = nextUpstream; fixes = found;
        }
        foreach (var image in images)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var response = await SeededSliceProcess.ExchangeAsync(runner, P28FuelMapValidator.CreateRequest(image.Image, scenario), options, cancellationToken).ConfigureAwait(false);
            Identity(response, P28FuelMapValidator.Operation);
            var report = P28FuelMapValidator.AnalyzeImage(image.Image, scenario, response, image.Id);
            foreach (var sequence in report.Sequences)
            {
                if (sequence.Checkpoints.Any(checkpoint => checkpoint.Disposition != "StrictMatch"))
                    throw new InvalidDataException("Mandatory fuel-map corpus did not strictly complete.");
                var outcomes = sequence.Checkpoints.Select(Outcome).ToArray();
                runs.Add(new(image.Id, image.Image.Hash, scenario.Digest, sequence.ScratchPattern, outcomes.Length, outcomes.Length,
                    Digest(sequence.Checkpoints.Select(checkpoint => checkpoint.Actual).ToArray()), Digest(outcomes),
                    Controls(sequence.Checkpoints), outcomes));
            }
        }
        ValidateRelations(runs);
        var effects = Effects(preview, scenario, runs); var witnesses = Witnesses(preview, runs);
        return new P28FuelMapExportEvidence(version!, upstream!, fixes!, preview.Plan.Digest(), P28FuelMapExportCorpus.Id,
            scenario.Digest, scenario.Calls.Count, P28FuelMapExportCorpus.RectangleCorners, runs, [], effects, witnesses,
            effects.All(effect => effect.CorpusReadCount > 0), true, true, true);
    }

    internal static P28FuelMapCellEffect[] Effects(P28FuelMapExportPreview preview, P28FuelMapScenario scenario,
        IReadOnlyList<P28FuelMapExportRun> runs)
    {
        var a = runs.Single(run => run.ImageKind == "A" && run.ScratchPattern == 0);
        var c = runs.Single(run => run.ImageKind == "C" && run.ScratchPattern == 0);
        return preview.Plan.Maps.SelectMany(group => group.Cells).Where(cell => cell.OldRawValue != cell.NewRawValue).Select(cell =>
        {
            var reads = a.Outcomes.Count(outcome => outcome.CellAddresses.Contains(cell.Offset));
            var combined = a.Outcomes.Zip(c.Outcomes).Count(pair => pair.First.MapId == cell.MapId && pair.First.LookupResult != pair.Second.LookupResult && pair.First.CellAddresses.Contains(cell.Offset));
            var isolated = preview.Original.CreateModifiedCopy([new(cell.Offset, [(byte)cell.NewRawValue])]);
            var isolatedChanges = 0; var first = -1;
            foreach (var call in scenario.Calls.Where(call => call.MapId == cell.MapId))
            {
                var rpm = call.MapId == "map_0" ? call.RawMap0Rpm : call.RawMap1Rpm;
                var before = P28FuelMapModel.ProjectNumeric(preview.Original.Span, call.MapId, rpm, call.RawLoad);
                var after = P28FuelMapModel.ProjectNumeric(isolated.Span, call.MapId, rpm, call.RawLoad);
                if (before.LookupResult != after.LookupResult) { isolatedChanges++; if (first < 0) first = call.Index; }
            }
            var effect = isolatedChanges > 0 ? "IsolatedLookupEffect" : reads > 0 ? "ReadMaskedByWeightOrSequentialTruncation" : "NotRead";
            return new P28FuelMapCellEffect(cell.MapId, cell.Row, cell.Column, cell.Offset, cell.OldRawValue, cell.NewRawValue,
                reads, combined, isolatedChanges, reads - isolatedChanges, effect, first);
        }).ToArray();
    }

    internal static P28FuelMapExportWitness[] Witnesses(P28FuelMapExportPreview preview, IReadOnlyList<P28FuelMapExportRun> runs)
    {
        var result = new List<P28FuelMapExportWitness>();
        foreach (var map in preview.Plan.Maps.Where(group => group.DomainAudit.ChangedResults > 0))
            foreach (var pattern in new[] { 0 })
            {
                var a = runs.Single(run => run.ImageKind == "A" && run.ScratchPattern == pattern);
                var c = runs.Single(run => run.ImageKind == "C" && run.ScratchPattern == pattern);
                var pair = a.Outcomes.Zip(c.Outcomes).FirstOrDefault(rows => rows.First.MapId == map.MapId && rows.First.LookupResult != rows.Second.LookupResult);
                if (pair.First is null) throw new InvalidDataException($"No native A/C witness for changed {map.MapId}.");
                result.Add(new(map.MapId, pair.First.Index, pattern, pair.First.RawLoad, pair.First.RawRpm,
                    pair.First.LookupResult, pair.Second.LookupResult, pair.First.ConsumerOutput, pair.Second.ConsumerOutput,
                    "Native combined-image numeric lookup witness; not physical fuel, pulse width or AFR."));
            }
        return result.ToArray();
    }

    internal static void ValidateRelations(IReadOnlyList<P28FuelMapExportRun> runs)
    {
        foreach (var pattern in new[] { 0, 85, 170 })
        {
            var a = runs.Single(run => run.ImageKind == "A" && run.ScratchPattern == pattern);
            var b = runs.Single(run => run.ImageKind == "B" && run.ScratchPattern == pattern);
            var c = runs.Single(run => run.ImageKind == "C" && run.ScratchPattern == pattern);
            if (b.ModelDigest != c.ModelDigest || !P28LimiterValidator.Equal(b.Outcomes, c.Outcomes))
                throw new InvalidDataException("Fuel-map B/C non-checksum behavior differs.");
            if (a.IndependentControlDigest != c.IndependentControlDigest)
                throw new InvalidDataException("Fuel-map A/C axis, cache, selector or history controls differ.");
        }
    }

    internal static void RequireEvidence(P28FuelMapExportPreview preview, P28FuelMapExportEvidence evidence) =>
        RequireEvidenceCore(preview, Images(preview), evidence);

    internal static void RequireEvidence(P28FuelMapExportPreview family,
        P28UnifiedCalibrationPreview combined, P28FuelMapExportEvidence evidence) =>
        RequireEvidenceCore(family, combined.Images, evidence);

    private static void RequireEvidenceCore(P28FuelMapExportPreview preview,
        (string Id, RomImage Image)[] images, P28FuelMapExportEvidence evidence)
    {
        var scenario = P28FuelMapExportCorpus.Create(preview, images.Single(image => image.Id == "C").Image);
        if (evidence.PlanDigest != preview.Plan.Digest() || evidence.CorpusId != P28FuelMapExportCorpus.Id ||
            evidence.ScenarioDigest != scenario.Digest || evidence.ScenarioCalls != scenario.Calls.Count ||
            evidence.RectangleCorners != P28FuelMapExportCorpus.RectangleCorners || evidence.Runs.Count != 9 ||
            !evidence.AllRequestedCellsRead || !evidence.IntermediateAndOutputAgree || !evidence.AxisCacheSelectorControlsAgree ||
            !evidence.NativeValidationComplete)
            throw new InvalidDataException("Stale or incomplete fuel-map execution evidence.");
        foreach (var image in images) foreach (var pattern in new[] { 0, 85, 170 })
            {
                var found = evidence.Runs.Where(run => run.ImageKind == image.Id && run.ScratchPattern == pattern).ToArray();
                if (found.Length != 1) throw new InvalidDataException("Missing or duplicate fuel-map run.");
                var run = found[0]; var model = new P28FuelMapModel(image.Image, scenario.InitialState);
                var expected = scenario.Calls.Select(call =>
                {
                    var step = model.Step(call); var rpm = call.MapId == "map_0" ? call.RawMap0Rpm : call.RawMap1Rpm;
                    var position = call.MapId == "map_0" ? step.Map0Rpm : step.Map1Rpm;
                    return new P28FuelMapExportOutcome(call.Index, call.MapId, call.RawLoad, rpm, step.Load.Index, position.Index,
                        step.Operands.LookupResult, step.Consumer.Output, step.Operands.CellAddresses);
                }).ToArray();
                if (run.ImageHash != image.Image.Hash || run.ScenarioDigest != scenario.Digest || run.Requested != scenario.Calls.Count ||
                    run.StrictMatches != run.Requested || run.Outcomes.Count != run.Requested || !P28LimiterValidator.Equal(run.Outcomes, expected) ||
                    run.ModelDigest != Digest(expected) || run.ObservationDigest.Length != 64 || !run.ObservationDigest.All(Uri.IsHexDigit))
                    throw new InvalidDataException("Forged, stale or contradictory fuel-map history.");
            }
        ValidateRelations(evidence.Runs);
        var effects = Effects(preview, scenario, evidence.Runs);
        if (!P28LimiterValidator.Equal(evidence.CellEffects, effects) || evidence.CellEffects.Any(effect => effect.CorpusReadCount == 0))
            throw new InvalidDataException("Fuel-map per-cell effect evidence is incomplete.");
        var witnesses = Witnesses(preview, evidence.Runs);
        if (!P28LimiterValidator.Equal(evidence.Witnesses, witnesses)) throw new InvalidDataException("Fuel-map witness evidence differs.");
        P28FixedLimiterExecution.RequireChecksumEvidence(images.Select(image => (image.Id, image.Image)).ToArray(), evidence.ChecksumRuns);
    }
}
