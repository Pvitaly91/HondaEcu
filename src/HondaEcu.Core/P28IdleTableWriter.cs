using System.Text;

namespace HondaEcu.Core;

public sealed record P28IdleTableReceipt(int FormatVersion, string Purpose, string PlanDigest,
    RomHash OriginalHash, RomHash OutputHash, string ProfileDigest, string BindingDigest, string LocationDigest,
    IReadOnlyList<P28IdleTableGroup> Tables, IReadOnlyList<P28RawByteDiff> Diff,
    P28IdleTableEvidence HistoricalExecution, string ExecutionScope, string Readiness)
{
    public const int MaximumJsonBytes = 64 * 1024 * 1024;
    public const string ReceiptPurpose = "idle-table-pc-only-export-receipt";
    public string ToJson(bool indented = false) => P28RawEditJson.Serialize(this, indented);
    public static P28IdleTableReceipt Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumJsonBytes) throw new InvalidDataException("Idle receipt exceeds 64 MiB.");
        var r = P28RawEditJson.Parse<P28IdleTableReceipt>(json);
        if (r.FormatVersion != 1 || r.Purpose != ReceiptPurpose || r.ExecutionScope != P28FixedLimiterReceipt.HistoricalScope ||
            r.Readiness != P28IdleTableEditor.Readiness) throw new InvalidDataException("Unsupported idle receipt.");
        return r;
    }
    public static P28IdleTableReceipt Load(string path) => Parse(P28IdleTablePlan.ReadJson(path, MaximumJsonBytes));
}
public sealed record P28IdleTableVerification(bool IsValid, RomHash OriginalHash, RomHash OutputHash, int Size,
    string PlanDigest, IReadOnlyList<P28IdleTableGroup> Tables, IReadOnlyList<P28RawByteDiff> Diff,
    byte ResidueA, byte ResidueB, byte ResidueC, bool ReverseRestoresOriginal, bool AllOtherBytesUnchanged,
    string Lineage, string FreshExecution, string ReceiptMeaning, string Readiness, bool PhysicalRpmAvailable,
    string GuiR3, string HardwareAndFullBoot);
public sealed record P28IdleTableInspection(string Title, P28IdleTableVerification Verification, string BindingStatus);

public static class P28IdleTableWriter
{
    private static P28IdleTableReceipt Receipt(P28IdleTablePlan p, P28IdleTableEvidence evidence) =>
        new(1, P28IdleTableReceipt.ReceiptPurpose, p.Digest(), p.OriginalHash, p.OutputHash, p.ProfileDigest,
            p.BindingDigest, p.LocationDigest, p.Tables, p.ExpectedDiff, evidence, P28FixedLimiterReceipt.HistoricalScope, p.Readiness);
    public static P28IdleTableVerification Save(P28VerifiedIdleTableExport token, string outputPath,
        string savedPlanPath, string receiptPath, IEnumerable<string>? protectedPaths = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ArgumentNullException.ThrowIfNull(token);
        var p = token.Preview;
        p = P28IdleTableEditor.Reproduce(p.Original, p.Profile, p.Binding, true, p.Location, p.Plan);
        var plan = p.Plan; var evidence = token.Evidence;
        P28IdleTableExecution.RequireEvidence(p, evidence);
        var receipt = Receipt(plan, evidence); var json = receipt.ToJson();
        if (Encoding.UTF8.GetByteCount(json) > P28IdleTableReceipt.MaximumJsonBytes) throw new InvalidDataException("Receipt exceeds readback bound; no publication attempted.");
        var (sources, recheck) = ResearchOutputGroup.CaptureInputs(p.Original, p.Profile, plan.ProfileDigest, protectedPaths);
        return ResearchOutputGroup.Write(p.Output, plan.ToJson(), json, outputPath, savedPlanPath, receiptPath, sources, recheck, paths =>
        {
            recheck(); var saved = P28IdleTablePlan.Load(paths[1]); var recorded = P28IdleTableReceipt.Load(paths[2]);
            if (saved.ToJson(false) != plan.ToJson(false) || recorded.ToJson() != json)
                throw new InvalidDataException("Idle readback differs from live capability; diagnostic files retained.");
            return Verify(RomImage.Load(paths[0]), p.Original, p.Profile, p.Binding, p.Location, saved, recorded);
        }, cancellationToken);
    }
    public static P28IdleTableVerification Verify(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28IdleTablePlan plan, P28IdleTableReceipt receipt)
    {
        var p = P28IdleTableEditor.Reproduce(original, profile, binding, true, location, plan); plan = p.Plan;
        var r = P28IdleTableReceipt.Parse(receipt.ToJson());
        if (!child.Span.SequenceEqual(p.Output.Span) || child.Hash != plan.OutputHash || r.ToJson() != Receipt(plan, r.HistoricalExecution).ToJson())
            throw new InvalidDataException("Idle child/receipt identity, fields, full bytes or lineage mismatch.");
        P28IdleTableExecution.RequireEvidence(p, r.HistoricalExecution); // no-op also refused
        var diff = P28FixedLimiterEditor.Diff(original, child); var reverse = child.ToArray();
        foreach (var d in diff) reverse[d.Offset] = d.OldByte;
        var residue = P28NativeChecksumArithmetic.Calculate(child).ComputedResult;
        if (!diff.SequenceEqual(plan.ExpectedDiff) || !reverse.AsSpan().SequenceEqual(original.Span) || residue != 0)
            throw new InvalidDataException("Full diff, reverse restoration or checksum mismatch.");
        return new(true, original.Hash, child.Hash, child.Size, plan.Digest(), plan.Tables, diff, plan.ResidueA, plan.ResidueB, residue,
            true, true, "OriginalBaseline -> IdleTableChild; no child binding or chains", "NotRun (historical consistency only)",
            P28FixedLimiterReceipt.HistoricalScope, plan.Readiness, false, "paused/NotRun", "NotRun");
    }
    public static P28IdleTableInspection InspectDerived(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28IdleTablePlan plan, P28IdleTableReceipt receipt) =>
        new("Idle table research edit", Verify(child, original, profile, binding, location, plan, receipt), "VerifiedIdleChildOfExactOriginal; not a new original");
}
