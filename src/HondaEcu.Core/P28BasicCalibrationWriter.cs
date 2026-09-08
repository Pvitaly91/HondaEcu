using System.Text;

namespace HondaEcu.Core;

public sealed record P28BasicCalibrationReceipt(int FormatVersion, string Purpose, string ContractId, string PlanDigest,
    RomHash OriginalHash, RomHash OutputHash, string LocationDigest, P28BasicCalibrationEvidence HistoricalExecution, string ExecutionScope, string Readiness)
{
    public const int MaximumBytes = 128 * 1024 * 1024;
    public const string ReceiptPurpose = "basic-calibration-pc-only-export-receipt";
    public string ToJson() => P28RawEditJson.Serialize(this, false);
    public static P28BasicCalibrationReceipt Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes) throw new InvalidDataException("Basic receipt exceeds 128 MiB.");
        var r = P28RawEditJson.Parse<P28BasicCalibrationReceipt>(json);
        if (r.FormatVersion != 1 || r.Purpose != ReceiptPurpose || r.ContractId != P28BasicCalibrationEditor.ContractId ||
            r.ExecutionScope != P28FixedLimiterReceipt.HistoricalScope || r.Readiness != P28IdleTableEditor.Readiness) throw new InvalidDataException("Unsupported basic receipt.");
        return r;
    }
    public static P28BasicCalibrationReceipt Load(string path) => Parse(P28IdleTablePlan.ReadJson(path, MaximumBytes));
}
public sealed record P28BasicCalibrationVerification(bool IsValid, RomHash OriginalHash, RomHash OutputHash, int Size, string PlanDigest,
    IReadOnlyList<P28BasicCalibrationGroup> Groups, IReadOnlyList<P28RawByteDiff> Diff, byte ResidueA, byte ResidueB, byte ResidueC,
    bool ReverseRestoresOriginal, bool AllOtherBytesUnchanged, string FreshExecution, string ReceiptMeaning,
    IReadOnlyList<P28BasicSuiteScope> Suites, bool PhysicalRpmAvailable, string Readiness);
public sealed record P28BasicCalibrationInspection(string Title, P28BasicCalibrationVerification Verification, string BindingStatus);
public static class P28BasicCalibrationWriter
{
    private static P28BasicCalibrationReceipt Receipt(P28BasicCalibrationPlan p, P28BasicCalibrationEvidence e) =>
        new(1, P28BasicCalibrationReceipt.ReceiptPurpose, p.ContractId, p.Digest(), p.OriginalHash, p.OutputHash, p.LocationDigest, e,
            P28FixedLimiterReceipt.HistoricalScope, p.Readiness);
    public static P28BasicCalibrationVerification Save(P28VerifiedBasicCalibrationExport token, string outputPath, string savedPlanPath,
        string receiptPath, IEnumerable<string>? protectedPaths = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ArgumentNullException.ThrowIfNull(token);
        var p = token.Preview; p = P28BasicCalibrationEditor.Reproduce(p.Original, p.Profile, p.Binding, true, p.Location, p.Plan);
        var plan = p.Plan; var evidence = token.Evidence; P28BasicCalibrationExecution.RequireEvidence(p, evidence);
        var planJson = plan.ToJson(); var receiptJson = Receipt(plan, evidence).ToJson();
        if (Encoding.UTF8.GetByteCount(planJson) > P28BasicCalibrationPlan.MaximumBytes || Encoding.UTF8.GetByteCount(receiptJson) > P28BasicCalibrationReceipt.MaximumBytes)
            throw new InvalidDataException("Basic artifact exceeds bound; publication not attempted.");
        var (sources, recheck) = ResearchOutputGroup.CaptureInputs(p.Original, p.Profile, plan.ProfileDigest, protectedPaths);
        // Shared staged new-path publisher owns alias checks, cancellation, rollback and independent readback.
        return ResearchOutputGroup.Write(p.Output, planJson, receiptJson, outputPath, savedPlanPath, receiptPath, sources, recheck, paths =>
        {
            recheck(); var saved = P28BasicCalibrationPlan.Load(paths[1]); var recorded = P28BasicCalibrationReceipt.Load(paths[2]);
            if (saved.ToJson() != planJson || recorded.ToJson() != receiptJson) throw new InvalidDataException("Basic readback differs from live capability.");
            return Verify(RomImage.Load(paths[0]), p.Original, p.Profile, p.Binding, p.Location, saved, recorded);
        }, cancellationToken);
    }
    public static P28BasicCalibrationVerification Verify(RomImage child, RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, P28BasicCalibrationPlan plan, P28BasicCalibrationReceipt receipt)
    {
        var p = P28BasicCalibrationEditor.Reproduce(original, profile, binding, true, location, plan); plan = p.Plan;
        var r = P28BasicCalibrationReceipt.Parse(receipt.ToJson());
        if (!child.Span.SequenceEqual(p.Output.Span) || child.Hash != plan.OutputHash || r.ToJson() != Receipt(plan, r.HistoricalExecution).ToJson())
            throw new InvalidDataException("Basic full-image/tuple identity mismatch.");
        P28BasicCalibrationExecution.RequireEvidence(p, r.HistoricalExecution);
        var diff = P28FixedLimiterEditor.Diff(original, child); var reverse = child.ToArray();
        foreach (var d in diff) reverse[d.Offset] = d.OldByte;
        var residue = P28NativeChecksumArithmetic.Calculate(child).ComputedResult;
        if (!diff.SequenceEqual(plan.ExpectedDiff) || !reverse.AsSpan().SequenceEqual(original.Span) || residue != 0) throw new InvalidDataException("Basic diff/reverse/checksum mismatch.");
        return new(true, original.Hash, child.Hash, child.Size, plan.Digest(), plan.Groups, diff, plan.ResidueA, plan.ResidueB, residue,
            true, true, "NotRun (historical consistency only)", P28FixedLimiterReceipt.HistoricalScope, plan.Suites, false, plan.Readiness);
    }
    public static P28BasicCalibrationInspection InspectDerived(RomImage child, RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, P28BasicCalibrationPlan plan, P28BasicCalibrationReceipt receipt) =>
        new("Basic calibration research composition", Verify(child, original, profile, binding, location, plan, receipt),
            "VerifiedBasicChildOfExactOriginal; not a new original, fresh execution or past-execution authentication");
}
