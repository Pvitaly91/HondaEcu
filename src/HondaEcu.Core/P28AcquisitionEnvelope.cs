using System.Globalization;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28AcquisitionEnvelopeCheckpoint(int ImageIndex, int ScratchPattern, int ObservationIndex,
    string Scope, bool? SamplesInsideEnvelope, bool? ProducerInsideEnvelope, bool? CompactInsideEnvelope);

public sealed record P28AcquisitionEnvelopeReport(string PlannerModelId, string UnchangedPolicyId,
    string ScenarioDigest, JsonElement ScenarioSnapshot, string QueryDigest, P28ScalingQuantity? RequestedRpm,
    string QuerySource, IReadOnlyList<string> PermittedAssumptions, P28RpmForwardPreview? ConservativeEnvelope,
    IReadOnlyList<P28AcquisitionEnvelopeCheckpoint> Checkpoints, int SteadyCheckpoints, int OutOfScopeCheckpoints,
    bool HasFailure, bool PhysicalRpmAvailable, string Qualification);

/// <summary>Checks only explicitly evidenced fresh uniform history; never changes the M1h envelope.</summary>
public static class P28AcquisitionEnvelope
{
    public static P28AcquisitionEnvelopeReport Compare(P28AcquisitionValidationReport execution,
        P28AcquisitionScenario stimulus, P28RpmQuery query)
    {
        ArgumentNullException.ThrowIfNull(execution);
        ArgumentNullException.ThrowIfNull(stimulus);
        ArgumentNullException.ThrowIfNull(query);
        if (execution.ScenarioDigest != stimulus.Digest || query.Scenario is null)
        { throw new ArgumentException("Envelope comparison requires the matching execution stimulus and an explicit M1h scenario."); }
        if (!execution.PermittedAssumptions.SequenceEqual(query.PermittedAssumptions))
        { throw new ArgumentException("Envelope and execution must use the same exact ADD permissions."); }
        var forward = P28RpmPlanner.EvaluateForward(query);
        var targetPeriod = forward is null ? (P28ExactNumber?)null : Parse(forward.IdealTicksPerSample);
        var checkpoints = new List<P28AcquisitionEnvelopeCheckpoint>();
        foreach (var sequence in execution.Sequences)
        {
            var slotPeriods = new P28ExactNumber?[6];
            foreach (var checkpoint in sequence.Checkpoints)
            {
                var index = checkpoint.ObservationIndex;
                var observation = stimulus.Observations[index];
                var actual = checkpoint.Acquisition;
                if (actual.Status == 0)
                {
                    foreach (var write in actual.SampleWrites)
                    {
                        if (write.Length != 3 || write[1] != 16 || write[0] < 0x360 || write[0] > 0x36A || (write[0] & 1) != 0)
                        { continue; }
                        slotPeriods[(write[0] - 0x360) / 2] = index > 0 && stimulus.Timeline is not null &&
                            actual.Disposition == nameof(P28AcquisitionDisposition.IntervalWrite) && (observation.Tcon2 & 4) == 0
                            ? stimulus.Timeline.Periods[index - 1].Exact() : null;
                    }
                }
                var scope = actual.Status != 0 ? "AcquisitionNotCompleted" :
                    forward is null || targetPeriod is null ? "MissingM1hQuery" :
                    stimulus.Timeline is null ? "NoExplicitExtendedTimeline" :
                    (actual.StateAfter.Data0217 & 0x80) != 0 || (actual.StateAfter.Data011F & 4) != 0 ? "AlternativeModeOutsideScope" :
                    slotPeriods.Any(period => period is null || period.Value.CompareTo(targetPeriod.Value) != 0) ? "WarmUpStaleOrTransientHistory" :
                    !forward.AllVariantsNormal ? "OutsideM1hNormalDomain" : "FreshUniformSteadyHistory";
                bool? samplesMatch = null;
                bool? producerMatch = null;
                bool? compactMatch = null;
                if (scope == "FreshUniformSteadyHistory")
                {
                    var textSamples = actual.StateAfter.Samples.Select(value => value.ToString(CultureInfo.InvariantCulture)).ToArray();
                    var variant = forward!.Variants.SingleOrDefault(candidate => candidate.Samples.SequenceEqual(textSamples));
                    samplesMatch = variant is not null;
                    if (checkpoint.G is { Status: 0 } g && variant?.Producer is { Resolved: true } producer)
                    {
                        producerMatch = g.Outputs.Count >= 3 && g.Outputs[0] + 256 * g.Outputs[1] == producer.T &&
                            ((g.Outputs[2] & 0x10) != 0) == producer.S;
                    }
                    if (checkpoint.F is { Status: 0 } f && variant?.Compact is { Resolved: true } compact)
                    {
                        compactMatch = f.Outputs.Count == 2 && f.Outputs[0] == compact.Code && ((f.Outputs[1] & 0x10) != 0) == compact.ExtraBit;
                    }
                }
                checkpoints.Add(new(sequence.ImageIndex, sequence.ScratchPattern, index, scope, samplesMatch, producerMatch, compactMatch));
                // Alternative G rewrites samples independently of acquisition; discard source-period provenance.
                if ((actual.StateAfter.Data0217 & 0x80) != 0 && checkpoint.G is { Status: 0 }) { Array.Clear(slotPeriods); }
            }
        }
        var steady = checkpoints.Count(item => item.Scope == "FreshUniformSteadyHistory");
        return new(P28RpmPlanner.ModelId, P28RpmPlanner.PolicyId, query.Scenario.Digest,
            JsonDocument.Parse(query.Scenario.ToJson(false)).RootElement.Clone(), query.QueryDigest, query.RequestedRpm,
            query.QuerySource, query.PermittedAssumptions, forward, checkpoints.AsReadOnly(), steady, checkpoints.Count - steady,
            checkpoints.Any(item => item.SamplesInsideEnvelope == false || item.ProducerInsideEnvelope == false || item.CompactInsideEnvelope == false),
            false, "Selected exact synthetic phases are checked against the unchanged conservative M1h envelope. Every slot must have an actual valid write from the same explicit period; stale/startup/transient histories are outside scope. Null G/F comparisons mean not completed or unresolved, not passed. No physical reachability, envelope narrowing or minimax-policy change.");
    }

    private static P28ExactNumber Parse(string value)
    {
        var fields = value.Split('/');
        return new(System.Numerics.BigInteger.Parse(fields[0], CultureInfo.InvariantCulture),
            System.Numerics.BigInteger.Parse(fields[1], CultureInfo.InvariantCulture));
    }
}
