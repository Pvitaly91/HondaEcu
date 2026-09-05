namespace HondaEcu.Core;

public static partial class P28AcquisitionValidator
{
    private static P28AcquisitionDerivedComparison CompareDerived(IReadOnlyList<P28AcquisitionSequenceComparison> sequences,
        RomImage baseline, RomImage derived, P28AcquisitionScenario scenario, P28VerifiedChecksumComposition composition,
        List<P28AcquisitionComparisonIssue> issues)
    {
        var acquisitionEqual = true;
        var producerCompactEqual = true;
        var changesEqual = true;
        var noCompensationAccess = true;
        var paired = 0;
        var eligible = 0;
        var expectedChanges = 0;
        var actualChanges = 0;
        var compensation = composition.Plan.Compensation.Offset;
        foreach (var pattern in ScratchPatterns)
        {
            var original = sequences.Single(item => item.ImageIndex == 0 && item.ScratchPattern == pattern);
            var child = sequences.Single(item => item.ImageIndex == 1 && item.ScratchPattern == pattern);
            acquisitionEqual &= original.CompletedObservations == child.CompletedObservations && original.StopObservationIndex == child.StopObservationIndex;
            for (var index = 0; index < scenario.Observations.Count; index++)
            {
                var a = original.Checkpoints[index];
                var c = child.Checkpoints[index];
                paired++;
                // Traces and irrelevant accumulator flags are diagnostics, not the scoped G/F outputs.
                var acquisitionStepEqual = a.SelectedTimestamp == c.SelectedTimestamp && a.SlotIndex == c.SlotIndex &&
                    SameAcquisition(a.Acquisition, c.Acquisition) && a.EverWrittenMask == c.EverWrittenMask && a.SlotWriteCounts.SequenceEqual(c.SlotWriteCounts);
                var producerCompactStepEqual = SameStage(a.G, c.G, true) && SameStage(a.F, c.F, false) &&
                    JsonEqual(a.StateAfterComposition, c.StateAfterComposition) && a.CumulativeAssumptions.SequenceEqual(c.CumulativeAssumptions);
                acquisitionEqual &= acquisitionStepEqual;
                producerCompactEqual &= producerCompactStepEqual;
                if ((!acquisitionStepEqual || !producerCompactStepEqual) && issues.Count < 64)
                    issues.Add(new(1, pattern, index, "Derived", "Mismatch",
                        "Independent baseline and verified-child execution differ in acquisition or scoped G/F history."));
                foreach (var checkpoint in new[] { a, c })
                {
                    noCompensationAccess &= !checkpoint.Acquisition.ProgramReads.Contains(compensation) && !checkpoint.Acquisition.ExecutedInstructionBytes.Contains(compensation);
                    foreach (var stage in new[] { checkpoint.G, checkpoint.F, checkpoint.Threshold }.OfType<P28AcquisitionStageResult>())
                        noCompensationAccess &= !stage.ProgramReads.Contains(compensation) && !stage.ExecutedInstructionBytes.Contains(compensation);
                }
                if (a.Threshold?.Status != 0 || c.Threshold?.Status != 0 || a.F?.Status != 0 || c.F?.Status != 0) continue;
                eligible++;
                var observation = scenario.Observations[index];
                var expectedCode = P28CompactModel.EvaluateHypothesis(original.IndependentExpectedStates[index].PreviousT,
                    (original.IndependentExpectedStates[index].Data0217 & 16) != 0).Code;
                var expectedA = ThresholdBits(baseline, observation, expectedCode);
                var expectedC = ThresholdBits(derived, observation, expectedCode);
                var actualA = (a.Threshold.Outputs[0] >> 1) & 3;
                var actualC = (c.Threshold.Outputs[0] >> 1) & 3;
                for (var pair = 0; pair < 2; pair++)
                {
                    var expectedChange = ((expectedA ^ expectedC) & (1 << pair)) != 0;
                    var actualChange = ((actualA ^ actualC) & (1 << pair)) != 0;
                    if (expectedChange) expectedChanges++;
                    if (actualChange) actualChanges++;
                    changesEqual &= expectedChange == actualChange;
                    if (expectedChange != actualChange && issues.Count < 64)
                        issues.Add(new(1, pattern, index, "DerivedThreshold", "Mismatch",
                            "Observed baseline/child predicate-change membership differs from the independent expected set."));
                }
            }
        }
        return new(true, paired, acquisitionEqual, producerCompactEqual, eligible, expectedChanges, actualChanges, changesEqual,
            noCompensationAccess,
            "Only actual admitted instruction extents and program-data read bytes for these finite sequences, including both bytes of word reads; not arbitrary PC/RAM or complete ECU/hardware behavior.");
    }

    private static bool SameAcquisition(P28AcquisitionObservedStep first, P28AcquisitionObservedStep second) =>
        first.Status == second.Status && first.Disposition == second.Disposition && first.Steps == second.Steps && first.StopPc == second.StopPc &&
        RowsEqual(first.PeripheralAccesses, second.PeripheralAccesses) && RowsEqual(first.SampleWrites, second.SampleWrites) &&
        JsonEqual(first.StateAfter, second.StateAfter) && first.ProgramReads.SequenceEqual(second.ProgramReads) &&
        first.ExecutedInstructionBytes.SequenceEqual(second.ExecutedInstructionBytes) && first.UsedAssumptions.SequenceEqual(second.UsedAssumptions);

    private static bool SameStage(P28AcquisitionStageResult? first, P28AcquisitionStageResult? second, bool allOutputs)
    {
        if (first is null || second is null) return first is null && second is null;
        var outputsEqual = allOutputs || first.Status != 0 ? first.Outputs.SequenceEqual(second.Outputs) :
            first.Outputs[0] == second.Outputs[0] && (first.Outputs[1] & 16) == (second.Outputs[1] & 16);
        return first.Status == second.Status && first.Steps == second.Steps && first.StopPc == second.StopPc && outputsEqual &&
            first.ProgramReads.SequenceEqual(second.ProgramReads) && first.ExecutedInstructionBytes.SequenceEqual(second.ExecutedInstructionBytes) &&
            first.UsedAssumptions.SequenceEqual(second.UsedAssumptions);
    }

    private static bool SameReplayPrefix(IReadOnlyList<P28AcquisitionSequenceComparison> original,
        IReadOnlyList<P28AcquisitionSequenceComparison> replay, int index)
    {
        if (original.Count != replay.Count) return false;
        foreach (var first in original)
        {
            var second = replay.SingleOrDefault(item => item.ImageIndex == first.ImageIndex && item.ScratchPattern == first.ScratchPattern);
            if (second is null || second.Checkpoints.Count != index + 1) return false;
            for (var item = 0; item <= index; item++)
            {
                var a = first.Checkpoints[item];
                var b = second.Checkpoints[item];
                if (!SameAcquisition(a.Acquisition, b.Acquisition) || !SameStage(a.G, b.G, true) || !SameStage(a.F, b.F, false) ||
                    !JsonEqual(a.Threshold is null ? null : a.Threshold with { Trace = [] }, b.Threshold is null ? null : b.Threshold with { Trace = [] }) ||
                    a.SelectedTimestamp != b.SelectedTimestamp || a.SlotIndex != b.SlotIndex ||
                    !JsonEqual(a.StateAfterComposition, b.StateAfterComposition) || !a.CumulativeAssumptions.SequenceEqual(b.CumulativeAssumptions) ||
                    a.EverWrittenMask != b.EverWrittenMask || !a.SlotWriteCounts.SequenceEqual(b.SlotWriteCounts)) return false;
            }
        }
        return true;
    }
}
