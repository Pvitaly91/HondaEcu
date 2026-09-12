using System.Text;

namespace HondaEcu.Core;

public sealed record P28FuelMapExportReceipt(int FormatVersion, string Purpose, string PlanDigest,
    RomHash OriginalHash, RomHash OutputHash, string ProfileDigest, string BindingDigest, string LocationDigest,
    IReadOnlyList<P28FuelMapExportGroup> Maps, IReadOnlyList<P28RawByteDiff> Diff,
    P28FuelMapExportEvidence HistoricalExecution, string ExecutionScope, string Readiness)
{
    public const int MaximumJsonBytes = 64 * 1024 * 1024;
    public const string ReceiptPurpose = "fuel-map-pc-only-export-receipt";
    public string ToJson(bool indented = false) => P28RawEditJson.Serialize(this, indented);
    public static P28FuelMapExportReceipt Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumJsonBytes) throw new InvalidDataException("Fuel-map receipt exceeds 64 MiB.");
        var receipt = P28RawEditJson.Parse<P28FuelMapExportReceipt>(json);
        if (receipt.FormatVersion != 1 || receipt.Purpose != ReceiptPurpose ||
            receipt.ExecutionScope != P28FixedLimiterReceipt.HistoricalScope || receipt.Readiness != P28FuelMapExportEditor.Readiness)
            throw new InvalidDataException("Unsupported fuel-map receipt.");
        return receipt;
    }
    public static P28FuelMapExportReceipt Load(string path) => Parse(P28IdleTablePlan.ReadJson(path, MaximumJsonBytes));
}

public sealed record P28FuelMapExportVerification(bool IsValid, RomHash OriginalHash, RomHash OutputHash, int Size,
    string PlanDigest, IReadOnlyList<P28FuelMapExportGroup> Maps, IReadOnlyList<P28RawByteDiff> Diff,
    byte ResidueA, byte ResidueB, byte ResidueC, bool ReverseRestoresOriginal, bool AllOtherBytesUnchanged,
    bool ImmutableRangesMatch, string Lineage, string FreshExecution, string ReceiptMeaning, string Readiness,
    bool PhysicalUnitsAvailable, string GuiR3, string D1InteractiveGuiAcceptance, string HardwareAndFullBoot);
public sealed record P28FuelMapExportInspection(string Title, P28FuelMapExportVerification Verification, string BindingStatus);

public static class P28FuelMapExportWriter
{
    private static P28FuelMapExportReceipt Receipt(P28FuelMapExportPlan plan, P28FuelMapExportEvidence evidence) =>
        new(1, P28FuelMapExportReceipt.ReceiptPurpose, plan.Digest(), plan.OriginalHash, plan.OutputHash,
            plan.ProfileDigest, plan.BindingDigest, plan.LocationDigest, plan.Maps, plan.ExpectedDiff, evidence,
            P28FixedLimiterReceipt.HistoricalScope, plan.Readiness);

    public static P28FuelMapExportVerification Save(P28VerifiedFuelMapExport token, string outputPath,
        string savedPlanPath, string receiptPath, IEnumerable<string>? protectedPaths = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ArgumentNullException.ThrowIfNull(token);
        var preview = token.Preview;
        preview = P28FuelMapExportEditor.Reproduce(preview.Original, preview.Profile, preview.Binding, true, preview.Location, preview.Plan);
        var plan = preview.Plan; var evidence = token.Evidence;
        P28FuelMapExportExecution.RequireEvidence(preview, evidence);
        var receipt = Receipt(plan, evidence); var json = receipt.ToJson();
        if (Encoding.UTF8.GetByteCount(json) > P28FuelMapExportReceipt.MaximumJsonBytes)
            throw new InvalidDataException("Fuel-map receipt exceeds its readback bound; no publication attempted.");
        var (sources, recheck) = ResearchOutputGroup.CaptureInputs(preview.Original, preview.Profile, plan.ProfileDigest, protectedPaths);
        return ResearchOutputGroup.Write(preview.Output, plan.ToJson(), json, outputPath, savedPlanPath, receiptPath,
            sources, recheck, paths =>
            {
                recheck(); var saved = P28FuelMapExportPlan.Load(paths[1]); var recorded = P28FuelMapExportReceipt.Load(paths[2]);
                if (saved.ToJson(false) != plan.ToJson(false) || recorded.ToJson() != json)
                    throw new InvalidDataException("Fuel-map readback differs from the live capability; diagnostic files retained.");
                return Verify(RomImage.Load(paths[0]), preview.Original, preview.Profile, preview.Binding, preview.Location, saved, recorded);
            }, cancellationToken);
    }

    public static P28FuelMapExportVerification Verify(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28FuelMapExportPlan plan,
        P28FuelMapExportReceipt receipt)
    {
        var preview = P28FuelMapExportEditor.Reproduce(original, profile, binding, true, location, plan); plan = preview.Plan;
        var recorded = P28FuelMapExportReceipt.Parse(receipt.ToJson());
        if (!child.Span.SequenceEqual(preview.Output.Span) || child.Hash != plan.OutputHash ||
            recorded.ToJson() != Receipt(plan, recorded.HistoricalExecution).ToJson())
            throw new InvalidDataException("Fuel-map child, receipt, full bytes or lineage mismatch.");
        P28FuelMapExportExecution.RequireEvidence(preview, recorded.HistoricalExecution);
        var diff = P28FixedLimiterEditor.Diff(original, child); var reverse = child.ToArray();
        foreach (var item in diff) reverse[item.Offset] = item.OldByte;
        var immutable = P28FuelMapExportEditor.Immutable(child);
        var immutableMatch = immutable.SequenceEqual(plan.ImmutableRanges);
        var residue = P28NativeChecksumArithmetic.Calculate(child).ComputedResult;
        if (!diff.SequenceEqual(plan.ExpectedDiff) || !reverse.AsSpan().SequenceEqual(original.Span) || residue != 0 || !immutableMatch)
            throw new InvalidDataException("Fuel-map full diff, reverse restoration, immutable range or checksum mismatch.");
        return new(true, original.Hash, child.Hash, child.Size, plan.Digest(), plan.Maps, diff, plan.ResidueA,
            plan.ResidueB, residue, true, true, true, "OriginalBaseline -> FuelMapChild; no child binding or chains",
            "NotRun (historical consistency only)", P28FixedLimiterReceipt.HistoricalScope, plan.Readiness, false,
            "paused/NotRun", "NotRun", "NotRun");
    }

    public static P28FuelMapExportInspection InspectDerived(RomImage child, RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, VerifiedCompensationLocation location, P28FuelMapExportPlan plan,
        P28FuelMapExportReceipt receipt) =>
        new("P28 fuel-map research edit", Verify(child, original, profile, binding, location, plan, receipt),
            "VerifiedFuelMapChildOfExactOriginal; not a new original");
}
