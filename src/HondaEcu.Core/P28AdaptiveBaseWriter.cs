namespace HondaEcu.Core;

public sealed record P28AdaptiveBaseReceipt(int FormatVersion, string Purpose, string PlanDigest,
    RomHash OriginalHash, RomHash OutputHash, string ProfileDigest, string BindingDigest, string LocationDigest,
    int Size, int Bank, IReadOnlyList<P28RawByteDiff> Diff, P28AdaptiveBaseEvidence HistoricalExecution,
    string ExecutionScope, string Readiness)
{
    public const string ReceiptPurpose = "adaptive-base-pc-only-export-receipt";
    public const int MaximumJsonBytes = 64 * 1024 * 1024;
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public static P28AdaptiveBaseReceipt Parse(string json)
    {
        if (System.Text.Encoding.UTF8.GetByteCount(json) > MaximumJsonBytes) throw new InvalidDataException("Adaptive receipt exceeds 64 MiB.");
        var r = P28RawEditJson.Parse<P28AdaptiveBaseReceipt>(json);
        if (r.FormatVersion != 1 || r.Purpose != ReceiptPurpose || r.Size != 32768 || r.Bank is < 0 or > 1 ||
            r.ExecutionScope != P28FixedLimiterReceipt.HistoricalScope || r.Readiness != P28AdaptiveBaseEditor.Readiness)
            throw new InvalidDataException("Unsupported adaptive receipt.");
        return r;
    }
    public static P28AdaptiveBaseReceipt Load(string path) => Parse(File.ReadAllText(path));
}
public sealed record P28AdaptiveBaseVerification(bool IsValid, RomHash OriginalHash, RomHash OutputHash,
    string PlanDigest, int Size, P28AdaptiveBasePair Pair, IReadOnlyList<P28AdaptiveBaseWord> Fields,
    IReadOnlyList<P28RawByteDiff> Diff, P28AdaptiveDomainCheck Domain, byte ResidueA, byte ResidueB, byte ResidueC,
    bool ReverseRestoresOriginal, bool OtherBankOriginsCoefficientsAndFixedPairUnchanged,
    string Lineage, string FreshExecution, string ReceiptMeaning, string Readiness,
    bool PhysicalRpmAvailable, string GuiR3, string HardwareAndFullBoot);
public sealed record P28AdaptiveBaseInspection(P28AdaptiveBaseVerification Verification,
    P28AdaptiveBasePair OriginalPair, P28AdaptiveBasePair DerivedPair, string Scope, string BindingStatus);

public static class P28AdaptiveBaseWriter
{
    internal static void Revalidate(P28VerifiedAdaptiveBaseExport token)
    {
        ArgumentNullException.ThrowIfNull(token); var p = token.Preview;
        _ = P28AdaptiveBaseEditor.Reproduce(p.Original, p.Profile, p.Binding, true, p.Location, p.Plan);
        if (p.Plan.IsNoOp) throw new InvalidDataException("No-op cannot publish firmware.");
        P28AdaptiveBaseExecution.RequireEvidence(p, token.Evidence);
    }
    public static P28AdaptiveBaseVerification Save(P28VerifiedAdaptiveBaseExport token, string outputPath, string savedPlanPath,
        string receiptPath, IEnumerable<string>? protectedPaths = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); Revalidate(token); var p = token.Preview; var plan = p.Plan;
        var (sources, recheck) = ResearchOutputGroup.CaptureInputs(p.Original, p.Profile, plan.ProfileDigest, protectedPaths);
        var receipt = new P28AdaptiveBaseReceipt(1, P28AdaptiveBaseReceipt.ReceiptPurpose, plan.Digest(), plan.OriginalHash,
            plan.OutputHash, plan.ProfileDigest, plan.BindingDigest, plan.LocationDigest, plan.Size, plan.RequestedPair.Bank,
            plan.ExpectedDiff, token.Evidence, P28FixedLimiterReceipt.HistoricalScope, plan.Readiness);
        var receiptJson = receipt.ToJson();
        if (System.Text.Encoding.UTF8.GetByteCount(receiptJson) > P28AdaptiveBaseReceipt.MaximumJsonBytes)
            throw new InvalidDataException("Receipt exceeds readback bound; no publication attempted.");
        return ResearchOutputGroup.Write(p.Output, plan.ToJson(), receiptJson, outputPath, savedPlanPath, receiptPath, sources,
            recheck, paths =>
            {
                recheck(); var saved = P28AdaptiveBasePlan.Load(paths[1]); var recorded = P28AdaptiveBaseReceipt.Load(paths[2]);
                if (saved.ToJson(false) != plan.ToJson(false) || recorded.ToJson(false) != receipt.ToJson(false)) throw new InvalidDataException("Readback plan/receipt differs from live capability; files retained for inspection.");
                return Verify(RomImage.Load(paths[0]), p.Original, p.Profile, p.Binding, p.Location, saved, recorded);
            }, cancellationToken);
    }
    public static P28AdaptiveBaseVerification Verify(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28AdaptiveBasePlan plan, P28AdaptiveBaseReceipt receipt)
    {
        var p = P28AdaptiveBaseEditor.Reproduce(original, profile, binding, true, location, plan); plan = p.Plan;
        var r = P28AdaptiveBaseReceipt.Parse(receipt.ToJson(false));
        if (plan.IsNoOp || !child.Span.SequenceEqual(p.Output.Span) || child.Hash != plan.OutputHash) throw new InvalidDataException("Child differs from exact original-parent adaptive composition.");
        P28AdaptiveBaseEditor.RequireFootprint(original, child, plan.RequestedPair.Bank);
        var diff = P28FixedLimiterEditor.Diff(original, child);
        if (r.PlanDigest != plan.Digest() || r.OriginalHash != original.Hash || r.OutputHash != child.Hash || r.Size != child.Size ||
            r.Bank != plan.RequestedPair.Bank || r.ProfileDigest != plan.ProfileDigest || r.BindingDigest != plan.BindingDigest ||
            r.LocationDigest != plan.LocationDigest || !r.Diff.SequenceEqual(diff)) throw new InvalidDataException("Receipt identity/lineage/diff mismatch.");
        P28AdaptiveBaseExecution.RequireEvidence(p, r.HistoricalExecution);
        var reverse = child.ToArray(); foreach (var d in diff) reverse[d.Offset] = d.OldByte;
        if (!reverse.AsSpan().SequenceEqual(original.Span)) throw new InvalidDataException("Reverse does not restore the entire original.");
        var residue = P28NativeChecksumArithmetic.Calculate(child).ComputedResult;
        if (residue != 0) throw new InvalidDataException("Child checksum arithmetic is nonzero.");
        return new(true, original.Hash, child.Hash, plan.Digest(), child.Size, P28AdaptiveBaseEditor.ReadPair(child, r.Bank), plan.Words,
            diff, plan.Domain, plan.ResidueA, plan.ResidueB, residue, true, true, "OriginalBaseline -> AdaptiveBaseChild; no child binding or patch chains",
            "NotRun (historical consistency/readback only)", P28FixedLimiterReceipt.HistoricalScope, plan.Readiness, false, "paused/NotRun", "NotRun");
    }
    public static P28AdaptiveBaseInspection InspectDerived(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28AdaptiveBasePlan plan, P28AdaptiveBaseReceipt receipt) =>
        new(Verify(child, original, profile, binding, location, plan, receipt), P28AdaptiveBaseEditor.ReadPair(original, plan.RequestedPair.Bank),
            P28AdaptiveBaseEditor.ReadPair(child, plan.RequestedPair.Bank), P28AdaptiveBaseEditor.Scope, "VerifiedAdaptiveBaseChildOfExactOriginal; not a new original");
}
