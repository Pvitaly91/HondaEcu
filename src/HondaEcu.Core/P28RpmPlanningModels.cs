using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

[JsonConverter(typeof(JsonStringEnumConverter))]
public enum P28RpmRegionState { AllFalse, AllTrue, Mixed, Unknown, Invalid }

/// <summary>Exact reduced RPM endpoints. A null upper bound denotes positive infinity.</summary>
public sealed record P28RpmInterval(string Lower, string? Upper, bool LowerInclusive, bool UpperInclusive);
public sealed record P28RpmRegion(P28RpmInterval Interval, P28RpmRegionState State, string Reason);

public sealed record P28RpmForwardVariant(
    int Configuration, IReadOnlyList<string> Samples, string Status, bool NormalEligible,
    P28ProducerModelResult? Producer, P28CompactResult? Compact,
    bool? OldPredicate, bool? NewPredicate, IReadOnlyList<string> UsedAssumptions,
    IReadOnlyList<string> Reasons);

public sealed record P28RpmForwardPreview(
    string RequestedRpm, string TimerHz, string TicksRpmProduct, string IdealTicksPerSample,
    string FloorTicks, string CeilingTicks, bool IntegralTicks, bool AllVariantsNormal,
    byte OriginalRaw, byte? ProposedRaw, IReadOnlyList<P28RpmForwardVariant> Variants,
    IReadOnlyList<string> UsedAssumptions, IReadOnlyList<string> Reasons,
    string EnvelopeQualification);

public sealed record P28RpmCandidate(
    byte RawValue, IReadOnlyList<P28RpmRegion> Regions, bool SimpleSelectable,
    IReadOnlyList<string> IneligibilityReasons, P28RpmInterval? TransitionBand,
    string? MinimaxError, bool IsBest, IReadOnlyList<string> UsedAssumptions)
{
    public string BandQualification => "Closed hull of the finite transition region; endpoint membership is retained separately in Regions. Minimax is max(abs(target-lower),abs(target-upper)), not an engine-safety recommendation.";
}

public sealed record P28RpmPlanningReport(
    string Status, IReadOnlyList<string> UnavailableReasons, P28RpmQuery Query,
    P28RpmForwardPreview? Forward, IReadOnlyList<P28RpmCandidate> Inverse,
    IReadOnlyList<P28RpmCandidate> BestCandidates, IReadOnlyList<string> UsedAssumptions,
    string MonotonicityStatus, P28RpmInterval? SupportedNormalDomain)
{
    public string FormatVersion => "1.0";
    public string ModelId => P28RpmPlanner.ModelId;
    public string ProducerModelId => P28ProducerModel.ModelId;
    public string CompactModelId => P28CompactModel.ModelId;
    public string PolicyId => P28RpmPlanner.PolicyId;
    public bool PhysicalRpmAvailable => false;
    public string ModelEvidence => "ConditionalMathematicsNotByteExecutionOrHardwareMeasurement";
    public string ExecutionStatus => "NotRun";
    public string HardwareStatus => "NotRun";
    public string PcSafety => "PcInspectionOnly";
    public string FlashReadiness => "NotFlashReady";
    public string SelectionQualification => "One enabled threshold predicate at the selected prior state, not full hysteresis, all gates or physical switching. All exact minimax ties are retained; selecting or applying a raw candidate requires a separate explicit action.";
    public string MonotonicityQualification => "When established, this checks every exact integer-sample point and both conservative envelope bounds across the supported domain. An arbitrary sequence of phase choices inside a set-valued envelope is not asserted to be a single monotone physical trajectory.";
    public string UsedAssumptionsQualification => "Report/candidate assumptions were actually used by mathematical G/F evaluations over the complete inverse domain, not by byte execution. Forward lists the assumptions used for the requested sample vectors separately.";
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this,
        new JsonSerializerOptions(P28RpmSerialization.Options) { WriteIndented = indented });
    public string ComputeDigest() => P28RpmSerialization.Digest(this);
}
