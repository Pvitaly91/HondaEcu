namespace HondaEcu.Core;

public sealed record P28FixedLimiterReceipt(int FormatVersion, string Purpose, string PlanDigest,
    RomHash OriginalHash, RomHash OutputHash, string ProfileDigest, string BindingDigest,
    string LocationDigest, int OutputSize, IReadOnlyList<P28RawByteDiff> Diff,
    P28FixedLimiterEvidence HistoricalExecution, string ExecutionScope, string Scope, string Readiness)
{
    public const string ReceiptPurpose = "fixed-limiter-pc-only-export-receipt";
    public const string HistoricalScope = "Historical execution for this original/output/plan only; readback is not fresh execution, authentication of historical claims, or reusable publication authority.";
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public static P28FixedLimiterReceipt Parse(string json)
    {
        if (System.Text.Encoding.UTF8.GetByteCount(json) > 8 * 1024 * 1024) throw new InvalidDataException("Receipt exceeds 8 MiB.");
        var r = P28RawEditJson.Parse<P28FixedLimiterReceipt>(json);
        if (r.FormatVersion != 1 || r.Purpose != ReceiptPurpose || r.ExecutionScope != HistoricalScope ||
            r.Scope != P28FixedLimiterEditor.Scope || r.Readiness != P28FixedLimiterEditor.Readiness || r.OutputSize != 32768)
            throw new InvalidDataException("Unsupported limiter receipt.");
        return r;
    }
    public static P28FixedLimiterReceipt Load(string path) => Parse(File.ReadAllText(path));
    internal static P28FixedLimiterReceipt Create(P28VerifiedFixedLimiterExport token)
    {
        var p = token.Preview.Plan;
        return new(1, ReceiptPurpose, p.Digest(), p.OriginalHash, p.OutputHash, p.ProfileDigest, p.BindingDigest,
            p.CompensationDefinitionDigest, p.Size, p.ExpectedDiff, token.Evidence, HistoricalScope, p.Scope, p.Readiness);
    }
}
public sealed record P28FixedLimiterVerification(bool IsValid, RomHash OriginalHash, RomHash OutputHash,
    string PlanDigest, int Size, P28FixedLimiterPair Pair, IReadOnlyList<P28RawByteDiff> Diff,
    byte ResidueA, byte ResidueB, byte ResidueC, bool ReverseRestoresOriginal, bool AdaptiveTablesUnchanged,
    string Lineage, string FreshExecution, string ReceiptMeaning, string Scope, string Readiness,
    bool PhysicalRpmAvailable, string GuiR3, string HardwareAndFullBoot);
public sealed record P28FixedLimiterDerivedInspection(P28FixedLimiterVerification Verification,
    P28FixedLimiterPair OriginalPair, P28FixedLimiterPair DerivedPair, string BindingStatus);

public static class P28FixedLimiterWriter
{
    internal static void Revalidate(P28VerifiedFixedLimiterExport token)
    {
        ArgumentNullException.ThrowIfNull(token);
        var p = token.Preview;
        _ = P28FixedLimiterEditor.Reproduce(p.Original, p.Profile, p.Binding, true, p.Location, p.Plan);
        if (p.Plan.IsNoOp) throw new InvalidDataException("No-op cannot publish firmware.");
        P28FixedLimiterExecution.RequireEvidence(p, token.Evidence);
    }
    public static P28FixedLimiterVerification Save(P28VerifiedFixedLimiterExport token, string outputPath, string savedPlanPath,
        string receiptPath, IEnumerable<string>? protectedPaths = null, CancellationToken cancellationToken = default)
    {
        Revalidate(token); var p = token.Preview;
        var (sources, Inputs) = ResearchOutputGroup.CaptureInputs(p.Original, p.Profile, p.Plan.ProfileDigest, protectedPaths);
        var receipt = P28FixedLimiterReceipt.Create(token);
        return ResearchOutputGroup.Write(p.Output, p.Plan.ToJson(), receipt.ToJson(), outputPath, savedPlanPath, receiptPath,
            sources, Inputs, paths =>
            {
                Inputs(); var savedPlan = P28FixedLimiterPlan.Load(paths[1]); var savedReceipt = P28FixedLimiterReceipt.Load(paths[2]);
                if (savedPlan.ToJson(false) != p.Plan.ToJson(false) || savedReceipt.ToJson(false) != receipt.ToJson(false))
                    throw new InvalidDataException("Saved plan/receipt differs from live validation. Files retained for inspection.");
                return Verify(RomImage.Load(paths[0]), p.Original, p.Profile, p.Binding, p.Location, savedPlan, savedReceipt);
            }, cancellationToken);
    }
    public static P28FixedLimiterVerification Verify(RomImage output, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28FixedLimiterPlan plan, P28FixedLimiterReceipt receipt)
    {
        var p = P28FixedLimiterEditor.Reproduce(original, profile, binding, true, location, plan);
        var r = P28FixedLimiterReceipt.Parse(receipt.ToJson(false));
        if (p.Plan.IsNoOp) throw new InvalidDataException("No-op has no export receipt.");
        if (!output.Span.SequenceEqual(p.Output.Span) || output.Hash != p.Plan.OutputHash)
            throw new InvalidDataException("Full output bytes differ from exact original-parent composition.");
        P28FixedLimiterEditor.RequireFootprint(original, output, location.Offset);
        var diff = P28FixedLimiterEditor.Diff(original, output);
        if (r.PlanDigest != p.Plan.Digest() || r.OriginalHash != original.Hash || r.OutputHash != output.Hash ||
            r.ProfileDigest != p.Plan.ProfileDigest || r.BindingDigest != p.Plan.BindingDigest || r.LocationDigest != location.DefinitionDigest ||
            !r.Diff.SequenceEqual(diff)) throw new InvalidDataException("Receipt identity/lineage/diff mismatch.");
        P28FixedLimiterExecution.RequireEvidence(p, r.HistoricalExecution);
        var reverse = output.ToArray(); foreach (var d in diff) reverse[d.Offset] = d.OldByte;
        if (!reverse.AsSpan().SequenceEqual(original.Span)) throw new InvalidDataException("Reverse does not restore exact original.");
        var residue = P28NativeChecksumArithmetic.Calculate(output).ComputedResult;
        if (residue != 0) throw new InvalidDataException("Output checksum arithmetic differs.");
        return new(true, original.Hash, output.Hash, p.Plan.Digest(), output.Size, P28FixedLimiterEditor.ReadPair(output), diff,
            p.Plan.ResidueA, p.Plan.ResidueB, residue, true, true, "OriginalBaseline -> FixedLimiterChild; no child binding or patch chain",
            "NotRun (readback/lineage verification only)", P28FixedLimiterReceipt.HistoricalScope, P28FixedLimiterEditor.Scope,
            P28FixedLimiterEditor.Readiness, false, "paused/NotRun", "NotRun");
    }
    public static P28FixedLimiterDerivedInspection InspectDerived(RomImage output, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28FixedLimiterPlan plan, P28FixedLimiterReceipt receipt) =>
        new(Verify(output, original, profile, binding, location, plan, receipt), P28FixedLimiterEditor.ReadPair(original),
            P28FixedLimiterEditor.ReadPair(output), "VerifiedLimiterChildOfExactOriginal; not matched as a new original");
}
