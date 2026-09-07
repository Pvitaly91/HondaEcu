using System.Text;

namespace HondaEcu.Core;

public sealed record P28CombinedLimiterReceipt(int FormatVersion, string Purpose, string PlanDigest,
    RomHash OriginalHash, RomHash OutputHash, string ProfileDigest, string BindingDigest, string LocationDigest,
    IReadOnlyList<P28CombinedLimiterGroup> Groups, IReadOnlyList<P28RawByteDiff> Diff,
    P28CombinedLimiterEvidence HistoricalExecution, string ExecutionScope, string Readiness)
{
    public const int MaximumJsonBytes = 64 * 1024 * 1024;
    public const string ReceiptPurpose = "combined-limiter-pc-only-export-receipt";
    public string ToJson(bool indented = false) => P28RawEditJson.Serialize(this, indented);
    public static P28CombinedLimiterReceipt Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumJsonBytes) throw new InvalidDataException("Combined receipt exceeds 64 MiB.");
        var r = P28RawEditJson.Parse<P28CombinedLimiterReceipt>(json);
        if (r.FormatVersion != 1 || r.Purpose != ReceiptPurpose || r.ExecutionScope != P28FixedLimiterReceipt.HistoricalScope ||
            r.Readiness != P28AdaptiveBaseEditor.Readiness) throw new InvalidDataException("Unsupported combined receipt.");
        return r;
    }
    public static P28CombinedLimiterReceipt Load(string path) => Parse(File.ReadAllText(path));
}
public sealed record P28CombinedLimiterVerification(bool IsValid, RomHash OriginalHash, RomHash OutputHash, int Size,
    string PlanDigest, IReadOnlyList<P28CombinedLimiterGroup> Groups, IReadOnlyList<P28RawByteDiff> Diff,
    byte ResidueA, byte ResidueB, byte ResidueC, bool ReverseRestoresOriginal, bool AllOtherBytesUnchanged,
    string Lineage, string FreshExecution, string ReceiptMeaning, string Readiness, bool PhysicalRpmAvailable,
    string GuiR3, string HardwareAndFullBoot);
public sealed record P28CombinedLimiterInspection(string Title, P28CombinedLimiterVerification Verification, string BindingStatus);

public static class P28CombinedLimiterWriter
{
    private static P28CombinedLimiterReceipt Receipt(P28CombinedLimiterPlan p, P28CombinedLimiterEvidence evidence) =>
        new(1, P28CombinedLimiterReceipt.ReceiptPurpose, p.Digest(), p.OriginalHash, p.OutputHash, p.ProfileDigest,
            p.BindingDigest, p.LocationDigest, p.Groups, p.ExpectedDiff, evidence, P28FixedLimiterReceipt.HistoricalScope, p.Readiness);
    public static P28CombinedLimiterVerification Save(P28VerifiedCombinedLimiterExport token, string outputPath,
        string savedPlanPath, string receiptPath, IEnumerable<string>? protectedPaths = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ArgumentNullException.ThrowIfNull(token);
        var p = token.Preview;
        p = P28CombinedLimiterEditor.Reproduce(p.Original, p.Profile, p.Binding, true, p.Location, p.Plan);
        var plan = p.Plan; var evidence = token.Evidence;
        P28CombinedLimiterExecution.RequireEvidence(p, evidence);
        var receipt = Receipt(plan, evidence); var json = receipt.ToJson();
        if (Encoding.UTF8.GetByteCount(json) > P28CombinedLimiterReceipt.MaximumJsonBytes) throw new InvalidDataException("Receipt exceeds readback bound; no publication attempted.");
        var (sources, recheck) = ResearchOutputGroup.CaptureInputs(p.Original, p.Profile, plan.ProfileDigest, protectedPaths);
        return ResearchOutputGroup.Write(p.Output, plan.ToJson(), json, outputPath, savedPlanPath, receiptPath, sources, recheck, paths =>
        {
            recheck(); var saved = P28CombinedLimiterPlan.Load(paths[1]); var recorded = P28CombinedLimiterReceipt.Load(paths[2]);
            if (saved.ToJson(false) != plan.ToJson(false) || recorded.ToJson() != json)
                throw new InvalidDataException("Combined readback differs from live capability; diagnostic files retained.");
            return Verify(RomImage.Load(paths[0]), p.Original, p.Profile, p.Binding, p.Location, saved, recorded);
        }, cancellationToken);
    }
    public static P28CombinedLimiterVerification Verify(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28CombinedLimiterPlan plan, P28CombinedLimiterReceipt receipt)
    {
        var p = P28CombinedLimiterEditor.Reproduce(original, profile, binding, true, location, plan); plan = p.Plan;
        var r = P28CombinedLimiterReceipt.Parse(receipt.ToJson());
        if (!child.Span.SequenceEqual(p.Output.Span) || child.Hash != plan.OutputHash || r.ToJson() != Receipt(plan, r.HistoricalExecution).ToJson())
            throw new InvalidDataException("Combined child/receipt identity, fields, full bytes or lineage mismatch.");
        P28CombinedLimiterExecution.RequireEvidence(p, r.HistoricalExecution); // no-op also refused
        var diff = P28FixedLimiterEditor.Diff(original, child); var reverse = child.ToArray();
        foreach (var d in diff) reverse[d.Offset] = d.OldByte;
        var residue = P28NativeChecksumArithmetic.Calculate(child).ComputedResult;
        if (!diff.SequenceEqual(plan.ExpectedDiff) || !reverse.AsSpan().SequenceEqual(original.Span) || residue != 0)
            throw new InvalidDataException("Full diff, reverse restoration or checksum mismatch.");
        return new(true, original.Hash, child.Hash, child.Size, plan.Digest(), plan.Groups, diff, plan.ResidueA, plan.ResidueB, residue,
            true, true, "OriginalBaseline -> CombinedLimiterChild; no child binding or chains", "NotRun (historical consistency only)",
            P28FixedLimiterReceipt.HistoricalScope, plan.Readiness, false, "paused/NotRun", "NotRun");
    }
    public static P28CombinedLimiterInspection InspectDerived(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28CombinedLimiterPlan plan, P28CombinedLimiterReceipt receipt) =>
        new("Combined limiter research edit", Verify(child, original, profile, binding, location, plan, receipt), "VerifiedCombinedChildOfExactOriginal; not a new original");
}
