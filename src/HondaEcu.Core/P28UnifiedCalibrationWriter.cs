using System.Text;

namespace HondaEcu.Core;

public sealed record P28UnifiedCalibrationReceipt(int FormatVersion, string Purpose,
    string ContractId, string PlanDigest, RomHash OriginalHash, RomHash OutputHash,
    string ProfileDigest, string BindingDigest, string LocationDigest,
    IReadOnlyList<P28UnifiedCalibrationGroup> Groups, IReadOnlyList<P28RawByteDiff> Diff,
    P28UnifiedCalibrationEvidence HistoricalExecution, string ExecutionScope, string Readiness)
{
    public const int MaximumBytes = 256 * 1024 * 1024;
    public const string ReceiptPurpose = "unified-calibration-pc-only-export-receipt";
    public string ToJson(bool indented = false) => P28RawEditJson.Serialize(this, indented);
    public static P28UnifiedCalibrationReceipt Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes)
            throw new InvalidDataException("Unified calibration receipt exceeds 256 MiB.");
        var receipt = P28RawEditJson.Parse<P28UnifiedCalibrationReceipt>(json);
        if (receipt.FormatVersion != 1 || receipt.Purpose != ReceiptPurpose ||
            receipt.ContractId != P28UnifiedCalibrationEditor.ContractId ||
            receipt.ExecutionScope != P28FixedLimiterReceipt.HistoricalScope ||
            receipt.Readiness != P28UnifiedCalibrationEditor.Readiness)
            throw new InvalidDataException("Unsupported unified calibration receipt.");
        return receipt;
    }
    public static P28UnifiedCalibrationReceipt Load(string path) =>
        Parse(P28IdleTablePlan.ReadJson(path, MaximumBytes));
}

public sealed record P28UnifiedCalibrationVerification(bool IsValid, RomHash OriginalHash,
    RomHash OutputHash, int Size, string PlanDigest, IReadOnlyList<P28UnifiedCalibrationGroup> Groups,
    int RequestedGroupCount, int ChangedGroupCount, int RequestedMapCellCount,
    int ChangedMapCellCount, IReadOnlyList<P28RawByteDiff> Diff, byte ResidueA, byte ResidueB,
    byte ResidueC, bool ReverseRestoresOriginal, bool AllOtherBytesUnchanged,
    bool ImmutableRangesMatch, string Lineage, string FreshExecution, string ReceiptMeaning,
    IReadOnlyList<P28UnifiedSuiteScope> Suites, bool PhysicalRpmAvailable,
    bool PhysicalDegreesAvailable, string Readiness, string GuiR3,
    string D1InteractiveGuiAcceptance, string D2Status, string HardwareAndFullBoot);
public sealed record P28UnifiedCalibrationInspection(string Title,
    P28UnifiedCalibrationVerification Verification, string BindingStatus,
    P28UnifiedCalibrationSettings RequestedSettings);

public static class P28UnifiedCalibrationWriter
{
    private static P28UnifiedCalibrationReceipt Receipt(P28UnifiedCalibrationPlan plan,
        P28UnifiedCalibrationEvidence evidence) => new(1,
            P28UnifiedCalibrationReceipt.ReceiptPurpose, plan.ContractId, plan.Digest(),
            plan.OriginalHash, plan.OutputHash, plan.ProfileDigest, plan.BindingDigest,
            plan.LocationDigest, plan.Groups, plan.ExpectedDiff, evidence,
            P28FixedLimiterReceipt.HistoricalScope, plan.Readiness);

    public static P28UnifiedCalibrationVerification Save(P28VerifiedUnifiedCalibrationExport token,
        string outputPath, string savedPlanPath, string receiptPath,
        IProgress<P28UnifiedCalibrationStage>? progress = null,
        IEnumerable<string>? protectedPaths = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ArgumentNullException.ThrowIfNull(token);
        var preview = token.Preview;
        preview = P28UnifiedCalibrationEditor.Reproduce(preview.Original, preview.Profile,
            preview.Binding, true, preview.Location, preview.Plan);
        var plan = preview.Plan; var evidence = token.Evidence;
        P28UnifiedCalibrationExecution.RequireEvidence(preview, evidence);
        var planJson = plan.ToJson(); var receiptJson = Receipt(plan, evidence).ToJson();
        if (Encoding.UTF8.GetByteCount(planJson) > P28UnifiedCalibrationPlan.MaximumBytes ||
            Encoding.UTF8.GetByteCount(receiptJson) > P28UnifiedCalibrationReceipt.MaximumBytes)
            throw new InvalidDataException("Unified artifact exceeds its readback bound; publication not attempted.");
        var (sources, recheck) = ResearchOutputGroup.CaptureInputs(preview.Original,
            preview.Profile, plan.ProfileDigest, protectedPaths);
        progress?.Report(P28UnifiedCalibrationStage.Publication);
        return ResearchOutputGroup.Write(preview.Output, planJson, receiptJson, outputPath,
            savedPlanPath, receiptPath, sources, recheck, paths =>
            {
                progress?.Report(P28UnifiedCalibrationStage.Readback);
                recheck();
                var saved = P28UnifiedCalibrationPlan.Load(paths[1]);
                var recorded = P28UnifiedCalibrationReceipt.Load(paths[2]);
                if (saved.ToJson(false) != plan.ToJson(false) || recorded.ToJson() != receiptJson)
                    throw new InvalidDataException("Unified readback differs from the live capability; diagnostic files retained.");
                return Verify(RomImage.Load(paths[0]), preview.Original, preview.Profile,
                    preview.Binding, preview.Location, saved, recorded);
            }, cancellationToken);
    }

    public static P28UnifiedCalibrationVerification Verify(RomImage child, RomImage original,
        RomProfile profile, P28ExactBaselineBinding binding, VerifiedCompensationLocation location,
        P28UnifiedCalibrationPlan plan, P28UnifiedCalibrationReceipt receipt)
    {
        var preview = P28UnifiedCalibrationEditor.Reproduce(original, profile, binding, true,
            location, plan); plan = preview.Plan;
        var recorded = P28UnifiedCalibrationReceipt.Parse(receipt.ToJson());
        if (!child.Span.SequenceEqual(preview.Output.Span) || child.Hash != plan.OutputHash ||
            recorded.ToJson() != Receipt(plan, recorded.HistoricalExecution).ToJson())
            throw new InvalidDataException("Unified child, receipt, full bytes or lineage mismatch.");
        P28UnifiedCalibrationExecution.RequireEvidence(preview, recorded.HistoricalExecution);
        var diff = P28FixedLimiterEditor.Diff(original, child); var reverse = child.ToArray();
        foreach (var item in diff) reverse[item.Offset] = item.OldByte;
        var residue = P28NativeChecksumArithmetic.Calculate(child).ComputedResult;
        var immutableMatch = plan.ImmutableRanges.All(range =>
            range.Sha256 == HashUtilities.Sha256(child.Span[range.Start..(range.EndInclusive + 1)]));
        if (!diff.SequenceEqual(plan.ExpectedDiff) || !reverse.AsSpan().SequenceEqual(original.Span) ||
            residue != 0 || !immutableMatch)
            throw new InvalidDataException("Unified full diff, reverse restoration, immutable range or checksum mismatch.");
        return new(true, original.Hash, child.Hash, child.Size, plan.Digest(), plan.Groups,
            plan.RequestedGroupCount, plan.ChangedGroupCount, plan.RequestedMapCellCount,
            plan.ChangedMapCellCount, diff, plan.ResidueA, plan.ResidueB, residue, true, true,
            true, "OriginalBaseline -> UnifiedCalibrationChild; child is never a new original",
            "NotRun (historical consistency only)", P28FixedLimiterReceipt.HistoricalScope,
            plan.Suites, false, false, plan.Readiness, "paused/NotRun", "NotRun",
            "NotStarted", "NotRun");
    }

    public static P28UnifiedCalibrationInspection InspectDerived(RomImage child,
        RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, P28UnifiedCalibrationPlan plan,
        P28UnifiedCalibrationReceipt receipt) => new(
            "P28 unified known-calibration research composition",
            Verify(child, original, profile, binding, location, plan, receipt),
            "VerifiedUnifiedCalibrationChildOfExactOriginal; not a new original or fresh capability",
            P28UnifiedCalibrationEditor.Settings(plan));
}
