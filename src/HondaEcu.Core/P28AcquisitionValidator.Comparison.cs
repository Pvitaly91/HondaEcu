using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public static partial class P28AcquisitionValidator
{
    private sealed record ExpectedStep(P28AcquisitionModelResult? Acquisition, P28ProducerModelResult? G,
        int? FStatus, byte? Code, bool? ExtraBit, P28AcquisitionState State, IReadOnlyList<string> Cumulative);

    private static IReadOnlyList<ExpectedStep> ExpectedHistory(P28AcquisitionScenario scenario, string composition,
        IReadOnlyList<string> allowed, int pattern)
    {
        var state = P28AcquisitionModel.Snapshot(scenario.InitialState);
        var stopped = false;
        var cumulative = new HashSet<string>(StringComparer.Ordinal);
        var result = new List<ExpectedStep>();
        foreach (var observation in scenario.Observations)
        {
            if (stopped) { result.Add(new(null, null, null, null, null, state, Freeze(cumulative.Order()))); continue; }
            var acquisition = P28AcquisitionModel.Evaluate(state, observation);
            state = acquisition.State;
            P28ProducerModelResult? g = null;
            int? fStatus = null;
            byte? code = null;
            bool? extra = null;
            stopped = acquisition.Disposition == P28AcquisitionDisposition.UnsupportedMode;
            if (!stopped && composition == ScheduledComposition && observation.Compose)
            {
                g = P28ProducerModel.Evaluate(new(observation.Index, "AcquisitionHistory", pattern, state.Samples,
                    state.PreviousT, state.Data0217, state.Data0231, observation.ThresholdContext,
                    observation.ThresholdPriorBits, observation.ThresholdEnabled), allowed.Contains(P28ProducerModel.AddEr1Assumption));
                state = P28AcquisitionModel.Snapshot(state with
                { PreviousT = g.T, Data0217 = g.Flags0217, Data0231 = g.Flags0231, Samples = g.Samples });
                cumulative.UnionWith(g.UsedAssumptions);
                stopped = !g.Resolved;
                if (!stopped)
                {
                    var strict = P28CompactModel.Evaluate(g.T, g.S);
                    if (strict.Resolved) { fStatus = 0; code = strict.Code; extra = strict.ExtraBit; }
                    else if (allowed.Contains(P28ByteExecutionValidator.AddAssumption))
                    {
                        var conditional = P28CompactModel.EvaluateHypothesis(g.T, g.S);
                        fStatus = 0; code = conditional.Code; extra = conditional.ExtraBit;
                        cumulative.Add(P28ByteExecutionValidator.AddAssumption);
                    }
                    else { fStatus = 1; stopped = true; }
                }
            }
            result.Add(new(acquisition, g, fStatus, code, extra, state, Freeze(cumulative.Order())));
        }
        return Freeze(result);
    }

    private static P28AcquisitionValidationReport AnalyzeCore(RomImage baseline, RomProfile profile,
        P28ExactBaselineBinding binding, P28AcquisitionScenario scenario, SliceProcessResponse response,
        string composition, IReadOnlyList<string> allowed, RomImage? derived, P28VerifiedChecksumComposition? verifiedComposition)
    {
        var root = response.Response;
        var fixes = SliceRunnerIdentity.Validate(root, Operation);
        var contracts = root.GetProperty("entryContracts");
        if (!JsonNode.DeepEquals(JsonNode.Parse(ExpectedEntryContracts().GetRawText()), JsonNode.Parse(contracts.GetRawText())))
            throw Protocol("Acquisition or staged-call contract differs from the reviewed boundaries.");
        if (root.GetProperty("diagnostics").GetArrayLength() != 0) throw Protocol("Acquisition traces belong to bounded checkpoints only.");
        var images = derived is null ? new[] { baseline } : new[] { baseline, derived };
        var arrays = root.GetProperty("acquisitionSequences");
        if (arrays.GetArrayLength() != images.Length * ScratchPatterns.Length) throw Protocol("Missing or extra image/scratch sequences.");
        var sequences = new List<P28AcquisitionSequenceComparison>();
        var issues = new List<P28AcquisitionComparisonIssue>();
        var seen = new HashSet<(int, int)>();
        foreach (var sequence in arrays.EnumerateArray())
        {
            Shape(sequence, "imageIndex", "scratchPattern", "stopObservationIndex", "completedObservations", "remainingNotRun", "checkpoints");
            var imageIndex = Int(sequence, "imageIndex", 0, images.Length - 1);
            var pattern = Int(sequence, "scratchPattern", 0, 255);
            if (!ScratchPatterns.Contains(pattern) || !seen.Add((imageIndex, pattern))) throw Protocol("Duplicate or unexpected sequence identity.");
            var checkpoints = sequence.GetProperty("checkpoints");
            if (checkpoints.GetArrayLength() != scenario.Observations.Count) throw Protocol("Every requested observation, including NotRun suffix, must be represented.");
            var parsed = Freeze(checkpoints.EnumerateArray().Select((item, index) => ParseCheckpoint(item, index, allowed)));
            var expected = ExpectedHistory(scenario, composition, allowed, pattern);
            sequences.Add(CompareSequence(sequence, imageIndex, pattern, images[imageIndex], scenario, composition, parsed, expected, issues));
        }
        var ordered = Freeze(sequences.OrderBy(item => item.ImageIndex).ThenBy(item => item.ScratchPattern));
        var derivedComparison = derived is null ? null : CompareDerived(ordered, baseline, derived, scenario, verifiedComposition!, issues);
        var used = Freeze(ordered.SelectMany(item => item.UsedAssumptions).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal));
        var failed = ordered.Any(item => item.HasFailure) || derivedComparison is
        { ExactAcquisitionEquality: false } or { ExactProducerCompactEquality: false } or
        { ExactChangedPredicateSet: false } or { CompensationByteNotReadOrFetched: false };
        return new("1.0", "StatefulCaptureSequenceValidation", 1, root.GetProperty("runnerVersion").GetString()!,
            P28ByteExecutionValidator.UpstreamCommit, Freeze(fixes), P28AcquisitionModel.ModelId, P28ProducerModel.ModelId,
            P28CompactModel.ModelId, composition, scenario.Digest, JsonSerializer.SerializeToElement(JsonNode.Parse(scenario.ToJson())),
            profile.Id, baseline.Hash, derived?.Hash, P28VtecInspector.ComputeProfileDigest(profile),
            P28RawThresholdEditor.ComputeBindingDigest(binding), verifiedComposition is null ? null : P28ChecksumPreservingEditor.ComputePlanDigest(verifiedComposition.Plan),
            Freeze(contracts.EnumerateArray().Select(item => item.Clone())), Freeze(allowed), used, ordered, derivedComparison,
            Freeze(issues), [], failed, used.Count != 0 || ordered.Any(item => item.StopObservationIndex >= 0),
            false, false, false, FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady,
            Freeze(new[]
            {
                "Each image/scratch run owns a persistent CPU/RAM history; expected states are independently progressed from original scenario inputs.",
                "Frozen TMR2/IRQH/TCON2 observations are explicit stimuli, not a timer clock, IRQ scheduler, peripheral hardware or full ECU boot.",
                "Caller slot and G/F/threshold scheduling are explicit harness choices; acquisition mode DATA011F.2 set is refused before fetch.",
                "Actual sample stores include same-value writes. Seeded samples are not acquisition writes; all six written bits alone do not prove physically valid warm-up.",
                "Scheduled calls preserve sample/history RAM and reset only the declared caller context; G to F skips the separately disclosed history bridge.",
                "Local ADD permissions and cumulative actually-used history are separate; subsequent observations do not erase earlier conditional execution.",
                "A stop aborts the full remaining sequence. Diagnostic replay restarts the original state and prefix and is excluded from primary counts.",
                "Threshold prior bits/context/enable are explicit stimuli, not measured main-loop hysteresis or physical output activation.",
                scenario.Timeline is null ? "No extended timeline supplied: wrap count, elapsed time and missed captures cannot be inferred from 16-bit observations."
                    : "The supplied exact extended timeline is declared stimulus provenance, not an independently measured physical clock.",
                "No native checksum run or flash-safety promotion is implied by this acquisition report; physical RPM and hardware execution remain unavailable.",
            }))
        { TimelineObservations = scenario.Timeline?.Describe(scenario.Observations) };
    }

    private static P28AcquisitionSequenceComparison CompareSequence(JsonElement sequence, int imageIndex, int pattern, RomImage image,
        P28AcquisitionScenario scenario, string composition, IReadOnlyList<P28AcquisitionCheckpoint> checkpoints,
        IReadOnlyList<ExpectedStep> expected, List<P28AcquisitionComparisonIssue> issues)
    {
        var counters = Enumerable.Range(0, 4).Select(_ => new StageCounter()).ToArray();
        var actualHistory = P28AcquisitionModel.Snapshot(scenario.InitialState);
        var used = new HashSet<string>(StringComparer.Ordinal);
        var writes = new int[6];
        var mask = 0;
        var completed = 0;
        var stop = -1;
        var stopPc = P28AcquisitionModel.EntryPc;
        var failed = false;
        for (var index = 0; index < checkpoints.Count; index++)
        {
            var checkpoint = checkpoints[index];
            var observation = scenario.Observations[index];
            var target = expected[index];
            var acquisition = checkpoint.Acquisition;
            var suffix = stop >= 0;
            var conditionalBeforeAcquisition = used.Count > 0;
            if (suffix)
            {
                if (acquisition.Status != 4 || acquisition.Disposition != "NotRun" || acquisition.StopPc != stopPc ||
                    !JsonEqual(acquisition.StateAfter, actualHistory) || !JsonEqual(checkpoint.StateAfterComposition, actualHistory))
                    throw Protocol("Stopped history was resumed or reseeded in the NotRun suffix.");
                RequireNotRun(checkpoint);
            }
            else
            {
                if (acquisition.Status == 4)
                {
                    if (acquisition.Disposition != "UnsupportedMode" || acquisition.StopPc != P28AcquisitionModel.EntryPc ||
                        !JsonEqual(acquisition.StateAfter, actualHistory) || !JsonEqual(checkpoint.StateAfterComposition, actualHistory))
                        throw Protocol("Unsupported mode must be refused without state mutation before native fetch.");
                    RequireNotRun(checkpoint);
                }
                else
                {
                    ValidateExecution(acquisition.Status, acquisition.Steps, acquisition.ExecutedInstructionBytes, acquisition.Trace,
                        [[0x56BE, 0x56DF], [0x5701, 0x5719]], 128, acquisition.Error);
                    if (acquisition.ProgramReads.Count != 0) throw Protocol("Acquisition unexpectedly read program data.");
                    if (checkpoint.SelectedTimestamp is null || checkpoint.SlotIndex is null) throw Protocol("Attempted acquisition must retain its actual timestamp and slot.");
                    foreach (var read in acquisition.PeripheralAccesses)
                        if (read[2] != 0 || !(read[0] == 0x3A && read[1] == 16 || (read[0] is 0x19 or 0x42) && read[1] == 8) ||
                            read[1] == 8 && read[3] > 255) throw Protocol("Peripheral access violates the frozen read-only allowlist.");
                    foreach (var write in acquisition.SampleWrites)
                    {
                        if (write[1] != 16 || write[0] is < 0x360 or >= 0x36C || (write[0] & 1) != 0)
                            throw Protocol("Unexpected sample store cannot count as a fresh word.");
                        var slot = (write[0] - 0x360) / 2;
                        writes[slot]++; mask |= 1 << slot;
                    }
                }
                var scheduled = composition == ScheduledComposition && observation.Compose;
                if ((checkpoint.G is not null) != (acquisition.Status == 0 && scheduled) ||
                    (checkpoint.F is not null) != (checkpoint.G?.Status == 0) ||
                    (checkpoint.Threshold is not null) != (checkpoint.F?.Status == 0))
                    throw Protocol("Downstream stages were omitted, invented or run after an upstream stop.");
                ValidateStage(checkpoint.G, [[0x0772, 0x07A5], [0x7AEC, 0x7AFE]], 192, P28ProducerModel.AddEr1Assumption, 0x077E);
                ValidateStage(checkpoint.F, [[0x07C7, 0x0822]], 128, P28ByteExecutionValidator.AddAssumption, 0x07F8);
                ValidateStage(checkpoint.Threshold, [[0x122C, 0x126D]], 128, null, 0);
                if (checkpoint.G is not null) used.UnionWith(checkpoint.G.UsedAssumptions);
                if (checkpoint.F is not null) used.UnionWith(checkpoint.F.UsedAssumptions);
                var terminal = acquisition.Status != 0 || scheduled && checkpoint.Threshold?.Status != 0;
                if (terminal)
                {
                    stop = index;
                    stopPc = checkpoint.Threshold?.StopPc ?? checkpoint.F?.StopPc ?? checkpoint.G?.StopPc ?? acquisition.StopPc;
                }
                else completed++;
            }
            if (!checkpoint.CumulativeAssumptions.Order(StringComparer.Ordinal).SequenceEqual(used.Order(StringComparer.Ordinal)))
                throw Protocol("Cumulative assumption history was lost or promoted from unused permission.");
            if (checkpoint.EverWrittenMask != mask || !checkpoint.SlotWriteCounts.SequenceEqual(writes))
                throw Protocol("Sample write accounting differs from actual architectural stores.");
            actualHistory = checkpoint.StateAfterComposition;

            var acqMatch = target.Acquisition is null ? suffix :
                acquisition.Status == (target.Acquisition.Disposition == P28AcquisitionDisposition.UnsupportedMode ? 4 : 0) &&
                acquisition.Disposition == target.Acquisition.Disposition.ToString() && acquisition.StopPc == target.Acquisition.StopPc &&
                JsonEqual(acquisition.StateAfter, target.Acquisition.State) && RowsEqual(acquisition.PeripheralAccesses, target.Acquisition.PeripheralAccesses) &&
                RowsEqual(acquisition.SampleWrites, target.Acquisition.SampleWrites) && checkpoint.SelectedTimestamp == target.Acquisition.SelectedTimestamp &&
                (acquisition.Status == 4 ? checkpoint.SlotIndex is null : checkpoint.SlotIndex == target.Acquisition.SlotIndex);
            var gMatch = checkpoint.G is null || CompareG(checkpoint.G, target.G);
            var fMatch = checkpoint.F is null || CompareF(checkpoint.F, target);
            var thresholdExpected = target.FStatus == 0;
            var thresholdMatch = checkpoint.Threshold is null || thresholdExpected &&
                checkpoint.Threshold.Status == 0 && checkpoint.Threshold.StopPc == (observation.ThresholdEnabled ? 0x126D : 0x1281) &&
                ((checkpoint.Threshold.Outputs[0] >> 1) & 3) == ThresholdBits(image, observation, target.Code!.Value) &&
                checkpoint.Threshold.ProgramReads.SequenceEqual(observation.ThresholdEnabled ? Enumerable.Range(0x6542 + observation.ThresholdContext * 4, 4) : []);
            if (!scenario.TraceObservationIndexes.Contains(index) && stop != index &&
                (acquisition.Trace.Count != 0 || new[] { checkpoint.G, checkpoint.F, checkpoint.Threshold }.OfType<P28AcquisitionStageResult>().Any(stage => stage.Trace.Count != 0)))
                throw Protocol("Unselected successful observation includes an unbounded diagnostic witness.");
            var stateMatch = JsonEqual(checkpoint.StateAfterComposition, target.State);
            if (!stateMatch && checkpoint.G is not null) gMatch = false;
            if (!stateMatch && checkpoint.G is null) acqMatch = false;
            // Expected histories stop on their own unresolved instruction, never on Rust's reported RAM.
            // An unexpected actual stop is already a failure; its untouched suffix remains NotRun.
            if (suffix) { acqMatch = gMatch = fMatch = thresholdMatch = true; }
            failed |= Record(counters[0], acquisition.Status, acqMatch, acquisition.Disposition == "UnsupportedMode", conditionalBeforeAcquisition,
                imageIndex, pattern, index, "Acquisition", issues, suffix);
            failed |= Record(counters[1], checkpoint.G?.Status, gMatch, false, conditionalBeforeAcquisition || checkpoint.G?.UsedAssumptions.Count > 0, imageIndex, pattern, index, "G", issues);
            failed |= Record(counters[2], checkpoint.F?.Status, fMatch, false, used.Count > 0, imageIndex, pattern, index, "F", issues);
            failed |= Record(counters[3], checkpoint.Threshold?.Status, thresholdMatch, false, used.Count > 0, imageIndex, pattern, index, "Threshold", issues);
        }
        if (Int(sequence, "stopObservationIndex", -1, checkpoints.Count - 1) != stop ||
            Int(sequence, "completedObservations", 0, checkpoints.Count) != completed ||
            Int(sequence, "remainingNotRun", 0, checkpoints.Count) != (stop < 0 ? 0 : checkpoints.Count - stop - 1))
            throw Protocol("Sequence completion/stop/suffix accounting is inconsistent.");
        return new(imageIndex, imageIndex == 0 ? "baseline" : "derived", pattern, checkpoints.Count, completed,
            stop < 0 ? 0 : checkpoints.Count - stop - 1, stop, writes.Sum(), mask, Freeze(writes),
            mask == 63 && actualHistory.Samples.All(value => value != 0), counters[0].Build(), counters[1].Build(), counters[2].Build(), counters[3].Build(),
            checkpoints, Freeze(expected.Select(item => item.State)), Freeze(used.Order()), failed);
    }

    private static bool CompareG(P28AcquisitionStageResult? actual, P28ProducerModelResult? expected)
    {
        if (actual is null || expected is null) return actual is null && expected is null;
        var outputs = new List<int> { expected.T & 255, expected.T >> 8, expected.Flags0217, expected.Flags0231 };
        foreach (var sample in expected.Samples) { outputs.Add(sample & 255); outputs.Add(sample >> 8); }
        return actual.Status == (expected.Resolved ? 0 : 1) && actual.StopPc == (expected.Resolved ? 0x07A5 : 0x077E) &&
            actual.Outputs.SequenceEqual(outputs) && actual.UsedAssumptions.SequenceEqual(expected.UsedAssumptions) && actual.ProgramReads.Count == 0;
    }
    private static bool CompareF(P28AcquisitionStageResult? actual, ExpectedStep expected)
    {
        if (actual is null || expected.FStatus is null) return actual is null && expected.FStatus is null;
        var usesAdd = expected.G!.T is >= 234 and < 3750 && expected.FStatus == 0;
        return actual.Status == expected.FStatus && actual.StopPc == (expected.FStatus == 0 ? 0x0822 : 0x07F8) &&
            actual.UsedAssumptions.SequenceEqual(usesAdd ? new[] { P28ByteExecutionValidator.AddAssumption } : []) && actual.ProgramReads.Count == 0 &&
            (expected.FStatus != 0 || actual.Outputs[0] == expected.Code && ((actual.Outputs[1] & 16) != 0) == expected.ExtraBit);
    }
    private static int ThresholdBits(RomImage image, P28CaptureObservation observation, byte code)
    {
        if (!observation.ThresholdEnabled) return observation.ThresholdPriorBits;
        var bits = 0;
        for (var pair = 0; pair < 2; pair++)
            if (P28ThresholdLogic.EvaluatePair(image.Span.Slice(0x6542, 8), observation.ThresholdContext, pair,
                (observation.ThresholdPriorBits & (1 << pair)) != 0, code).NewState) bits |= 1 << pair;
        return bits;
    }
    private static bool RowsEqual(IReadOnlyList<int[]> first, IReadOnlyList<int[]> second) =>
        first.Count == second.Count && first.Zip(second).All(pair => pair.First.SequenceEqual(pair.Second));
    private static void RequireNotRun(P28AcquisitionCheckpoint checkpoint)
    {
        var step = checkpoint.Acquisition;
        if (step.Steps != 0 || step.PeripheralAccesses.Count != 0 || step.SampleWrites.Count != 0 || step.ProgramReads.Count != 0 ||
            step.ExecutedInstructionBytes.Count != 0 || step.Trace.Count != 0 || checkpoint.SelectedTimestamp is not null || checkpoint.SlotIndex is not null ||
            checkpoint.G is not null || checkpoint.F is not null || checkpoint.Threshold is not null)
            throw Protocol("NotRun contains execution, observation injection or downstream results.");
    }
    private static void ValidateStage(P28AcquisitionStageResult? stage, int[][] ranges, int budget, string? assumption, int addPc)
    {
        if (stage is null) return;
        ValidateExecution(stage.Status, stage.Steps, stage.ExecutedInstructionBytes, stage.Trace, ranges, budget, stage.Error);
        if (assumption is not null && stage.UsedAssumptions.Contains(assumption) !=
            (stage.ExecutedInstructionBytes.Contains(addPc) && stage.ExecutedInstructionBytes.Contains(addPc + 1)))
            throw Protocol("Claimed local assumption use does not match actually executed conditional instruction extents.");
        if (assumption is not null && stage.ProgramReads.Count != 0) throw Protocol("G/F unexpectedly read program data.");
        if (assumption is null && stage.ProgramReads.Any(address => address is < 0x6542 or >= 0x654A))
            throw Protocol("Threshold read outside its reviewed program-data block.");
    }
    private static void ValidateExecution(int status, int steps, IReadOnlyList<int> extents, IReadOnlyList<JsonElement> trace,
        int[][] ranges, int budget, string? error)
    {
        if (status == 0 && (steps == 0 || extents.Count == 0 || error is not null) || status == 3 && steps != budget ||
            steps == 0 && extents.Count != 0 || extents.Any(address => !ranges.Any(range => address >= range[0] && address < range[1])) ||
            trace.Count > Math.Min(steps + (status == 0 ? 0 : 1), 128))
            throw Protocol("Execution status, instruction budget or byte extents violate the slice contract.");
    }
    private sealed class StageCounter
    {
        public readonly int[] Values = new int[8];
        public P28AcquisitionStageCounts Build() => new(Values.Sum(), Values[0], Values[1], Values[2], Values[3], Values[4], Values[5], Values[6], Values[7]);
    }
    private static bool Record(StageCounter counter, int? status, bool matches, bool unsupported, bool conditional,
        int image, int pattern, int index, string stage, List<P28AcquisitionComparisonIssue> issues, bool suffix = false)
    {
        var category = status switch { null => 7, 4 when suffix => 7, 4 when unsupported => 3, 4 => 7, 1 => 2, 2 => 4, 3 => 5, _ => conditional ? 1 : 0 };
        var failure = !matches || status is 2 or 3;
        if (!matches && status is not (1 or 2 or 3)) category = 6;
        counter.Values[category]++;
        if (failure && issues.Count < 64)
            issues.Add(new(image, pattern, index, stage, status switch { 1 => "UnexpectedUnresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "Mismatch" },
                "Observed stage differs from the independently progressed expected sequence or stopped with an execution failure."));
        return failure;
    }
}
