using System.Text;

namespace HondaEcu.Core;

public sealed record P28IgnitionMapExportReceipt(int FormatVersion, string Purpose, string PlanDigest,
    RomHash OriginalHash, RomHash OutputHash, string ProfileDigest, string BindingDigest, string LocationDigest,
    IReadOnlyList<P28IgnitionMapExportGroup> Maps, P28IgnitionConsumerDomainAudit ConsumerAudit,
    IReadOnlyList<P28RawByteDiff> Diff, P28IgnitionMapExportEvidence HistoricalExecution,
    string ExecutionScope, string Readiness)
{
    public const int MaximumJsonBytes = 64 * 1024 * 1024;
    public const string ReceiptPurpose = "ignition-map-pc-only-export-receipt";
    public string ToJson(bool indented = false) => P28RawEditJson.Serialize(this, indented);
    public static P28IgnitionMapExportReceipt Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumJsonBytes) throw new InvalidDataException("Ignition-map receipt exceeds 64 MiB.");
        var receipt = P28RawEditJson.Parse<P28IgnitionMapExportReceipt>(json);
        if (receipt.FormatVersion != 1 || receipt.Purpose != ReceiptPurpose ||
            receipt.ExecutionScope != P28FixedLimiterReceipt.HistoricalScope ||
            receipt.Readiness != P28IgnitionMapExportEditor.Readiness)
            throw new InvalidDataException("Unsupported ignition-map receipt.");
        return receipt;
    }
    public static P28IgnitionMapExportReceipt Load(string path) => Parse(P28IdleTablePlan.ReadJson(path, MaximumJsonBytes));
}

public sealed record P28IgnitionMapExportVerification(bool IsValid, RomHash OriginalHash, RomHash OutputHash,
    int Size, string PlanDigest, IReadOnlyList<P28IgnitionMapExportGroup> Maps,
    P28IgnitionConsumerDomainAudit ConsumerAudit, IReadOnlyList<P28RawByteDiff> Diff, byte ResidueA,
    byte ResidueB, byte ResidueC, bool ReverseRestoresOriginal, bool AllOtherBytesUnchanged,
    bool ImmutableRangesMatch, string Lineage, string FreshExecution, string ReceiptMeaning, string Readiness,
    bool PhysicalUnitsAvailable, string GuiR3, string D1InteractiveGuiAcceptance, string HardwareAndFullBoot);
public sealed record P28IgnitionMapExportInspection(string Title,
    P28IgnitionMapExportVerification Verification, string BindingStatus);

public static class P28IgnitionMapExportWriter
{
    private static P28IgnitionMapExportReceipt Receipt(P28IgnitionMapExportPlan plan,
        P28IgnitionMapExportEvidence evidence) => new(1, P28IgnitionMapExportReceipt.ReceiptPurpose,
            plan.Digest(), plan.OriginalHash, plan.OutputHash, plan.ProfileDigest, plan.BindingDigest,
            plan.LocationDigest, plan.Maps, plan.ConsumerAudit, plan.ExpectedDiff, evidence,
            P28FixedLimiterReceipt.HistoricalScope, plan.Readiness);

    public static P28IgnitionMapExportVerification Save(P28VerifiedIgnitionMapExport token, string outputPath,
        string savedPlanPath, string receiptPath, IEnumerable<string>? protectedPaths = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ArgumentNullException.ThrowIfNull(token);
        var preview = token.Preview;
        preview = P28IgnitionMapExportEditor.Reproduce(preview.Original, preview.Profile, preview.Binding,
            true, preview.Location, preview.Plan);
        var plan = preview.Plan; var evidence = token.Evidence;
        P28IgnitionMapExportExecution.RequireEvidence(preview, evidence);
        var receipt = Receipt(plan, evidence); var json = receipt.ToJson();
        if (Encoding.UTF8.GetByteCount(json) > P28IgnitionMapExportReceipt.MaximumJsonBytes)
            throw new InvalidDataException("Ignition-map receipt exceeds its readback bound; no publication attempted.");
        var (sources, recheck) = ResearchOutputGroup.CaptureInputs(preview.Original, preview.Profile,
            plan.ProfileDigest, protectedPaths);
        return ResearchOutputGroup.Write(preview.Output, plan.ToJson(), json, outputPath, savedPlanPath,
            receiptPath, sources, recheck, paths =>
            {
                recheck(); var saved = P28IgnitionMapExportPlan.Load(paths[1]);
                var recorded = P28IgnitionMapExportReceipt.Load(paths[2]);
                if (saved.ToJson(false) != plan.ToJson(false) || recorded.ToJson() != json)
                    throw new InvalidDataException("Ignition-map readback differs from the live capability; diagnostic files retained.");
                return Verify(RomImage.Load(paths[0]), preview.Original, preview.Profile, preview.Binding,
                    preview.Location, saved, recorded);
            }, cancellationToken);
    }

    public static P28IgnitionMapExportVerification Verify(RomImage child, RomImage original,
        RomProfile profile, P28ExactBaselineBinding binding, VerifiedCompensationLocation location,
        P28IgnitionMapExportPlan plan, P28IgnitionMapExportReceipt receipt)
    {
        var preview = P28IgnitionMapExportEditor.Reproduce(original, profile, binding, true, location, plan);
        plan = preview.Plan; var recorded = P28IgnitionMapExportReceipt.Parse(receipt.ToJson());
        if (!child.Span.SequenceEqual(preview.Output.Span) || child.Hash != plan.OutputHash ||
            recorded.ToJson() != Receipt(plan, recorded.HistoricalExecution).ToJson())
            throw new InvalidDataException("Ignition-map child, receipt, full bytes or lineage mismatch.");
        P28IgnitionMapExportExecution.RequireEvidence(preview, recorded.HistoricalExecution);
        var diff = P28FixedLimiterEditor.Diff(original, child); var reverse = child.ToArray();
        foreach (var item in diff) reverse[item.Offset] = item.OldByte;
        var immutableMatch = P28IgnitionMapExportEditor.Immutable(child).SequenceEqual(plan.ImmutableRanges);
        var residue = P28NativeChecksumArithmetic.Calculate(child).ComputedResult;
        if (!diff.SequenceEqual(plan.ExpectedDiff) || !reverse.AsSpan().SequenceEqual(original.Span) ||
            residue != 0 || !immutableMatch)
            throw new InvalidDataException("Ignition-map full diff, reverse restoration, immutable range or checksum mismatch.");
        return new(true, original.Hash, child.Hash, child.Size, plan.Digest(), plan.Maps, plan.ConsumerAudit,
            diff, plan.ResidueA, plan.ResidueB, residue, true, true, true,
            "OriginalBaseline -> IgnitionMapChild; no child binding or chains",
            "NotRun (historical consistency only)", P28FixedLimiterReceipt.HistoricalScope, plan.Readiness,
            false, "paused/NotRun", "NotRun", "NotRun");
    }

    public static P28IgnitionMapExportInspection InspectDerived(RomImage child, RomImage original,
        RomProfile profile, P28ExactBaselineBinding binding, VerifiedCompensationLocation location,
        P28IgnitionMapExportPlan plan, P28IgnitionMapExportReceipt receipt) =>
        new("P28 primary ignition-map research edit",
            Verify(child, original, profile, binding, location, plan, receipt),
            "VerifiedIgnitionMapChildOfExactOriginal; not a new original");
}
