namespace HondaEcu.Core;

public sealed record P28CompensationAvailability(
    string Status, bool IsAvailable, string? DefinitionId, int? Offset, string Reason,
    string EvidenceScope, FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety);

public sealed record P28ComputedCompensation(int Offset, byte OldByte, byte NewByte, string FormulaId);

/// <summary>Descriptive composition, not authority to select a writable byte.</summary>
public sealed record P28ChecksumPreservingPlan(
    string FormatVersion, string Purpose, bool SyntheticOnly, RomHash BaselineHash,
    string ProfileDigest, string BindingDigest, P28RawThresholdPlan ThresholdPlan,
    string CompensationDefinitionId, string CompensationDefinitionDigest, string CompensationEvidenceIdentity, string EvidenceScope,
    P28ComputedCompensation Compensation, IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp,
    byte BaselineResidue, byte IntermediateResidue, byte FinalResidue, string ChecksumContractId,
    ChecksumStatus NativeChecksumStatus, NativeChecksumExecutionStatus ExecutionStatus,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public static P28ChecksumPreservingPlan Parse(string json)
    {
        var plan = P28RawEditJson.Parse<P28ChecksumPreservingPlan>(json);
        P28ChecksumPreservingEditor.ValidatePlanShape(plan);
        return plan;
    }
    public static P28ChecksumPreservingPlan Load(string path) => Parse(File.ReadAllText(path));
}

public sealed record P28ChecksumPreservingReport(
    string FormatVersion, string Purpose, bool SyntheticOnly, RomHash BaselineHash,
    RomHash IntermediateHash, RomHash OutputHash, string ProfileDigest, string BindingDigest,
    string PlanDigest, string CompensationDefinitionId, string CompensationDefinitionDigest, string CompensationEvidenceIdentity,
    string EvidenceScope, IReadOnlyList<P28RawByteDiff> Diff, int ChangedByteCount, bool IsNoOp,
    byte BaselineResidue, byte IntermediateResidue, byte FinalResidue,
    bool ReverseRestoresBaseline, bool ThresholdOnlyBehaviorPreserved, P28PredicateImpact PredicateImpact,
    string ChecksumContractId, ChecksumStatus NativeChecksumStatus, NativeChecksumExecutionStatus ExecutionStatus,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public static P28ChecksumPreservingReport Parse(string json)
    {
        var report = P28RawEditJson.Parse<P28ChecksumPreservingReport>(json);
        P28ChecksumPreservingEditor.ValidateReportShape(report);
        return report;
    }
    public static P28ChecksumPreservingReport Load(string path) => Parse(File.ReadAllText(path));
}

/// <summary>In-memory preview only. It is not a verified native-execution or publication capability.</summary>
public sealed class P28ChecksumPreservingPreview
{
    internal P28ChecksumPreservingPreview(P28ChecksumPreservingPlan plan, RomImage intermediate,
        RomImage image, P28ChecksumPreservingReport report)
    {
        Plan = plan;
        Intermediate = intermediate;
        Image = image;
        Report = report;
    }
    public P28ChecksumPreservingPlan Plan { get; }
    public RomImage Intermediate { get; }
    public RomImage Image { get; }
    public P28ChecksumPreservingReport Report { get; }
}

public sealed record P28ChecksumPreservingVerification(
    bool IsValid, IReadOnlyList<VerificationIssue> Issues, RomHash BaselineHash, RomHash OutputHash,
    bool ReverseRestoresBaseline, bool ThresholdOnlyBehaviorPreserved, string EvidenceScope,
    ChecksumStatus NativeChecksumStatus, NativeChecksumExecutionStatus ExecutionStatus,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
}
