using System.Text;

namespace HondaEcu.Core;

public sealed record P28AdaptiveBasePair(int Bank, int BaseCutRaw, int BaseResumeRaw);
public sealed record P28AdaptiveBaseWord(string FieldId, int Offset, int Width, string Encoding,
    int OldWord, int NewWord, IReadOnlyList<byte> OldBytes, IReadOnlyList<byte> NewBytes,
    int OriginOffset, int Origin, int CoefficientOffset, int Coefficient);
public sealed record P28AdaptiveDomainCheck(int MinimumRaw, int MaximumRaw, int CheckedInputs,
    int MaximumCutTarget, int MaximumResumeTarget, int MinimumTargetGap, bool NoTargetWrap, bool StrictTargetOrder);
public sealed record P28AdaptiveBasePlan(int FormatVersion, string Purpose, string ContractId,
    RomHash OriginalHash, int Size, string ProfileId, string ProfileDigest, string BindingDigest,
    P28AdaptiveBasePair RequestedPair, IReadOnlyList<P28AdaptiveBaseWord> Words, P28AdaptiveDomainCheck Domain,
    string LocationId, string LocationDigest, string LocationEvidenceIdentity, string LocationScope, string EditAudit,
    P28ComputedCompensation Compensation, byte ResidueA, byte ResidueB, byte ResidueC,
    RomHash IntermediateHash, RomHash OutputHash, IReadOnlyList<P28RawByteDiff> ExpectedDiff,
    bool IsNoOp, string Policy, string Scope, string ChecksumContractId, bool PhysicalRpmAvailable, string Readiness)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28AdaptiveBasePlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 65536) throw new InvalidDataException("Adaptive plan exceeds 64 KiB.");
        var p = P28RawEditJson.Parse<P28AdaptiveBasePlan>(json);
        P28AdaptiveBaseEditor.Shape(p); return p;
    }
    public static P28AdaptiveBasePlan Load(string path) => Parse(File.ReadAllText(path));
}

/// <summary>Exact original-parent preview, never a reusable publication capability.</summary>
public sealed class P28AdaptiveBasePreview
{
    private readonly string _plan;
    internal P28AdaptiveBasePreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, RomImage intermediate, RomImage output, P28AdaptiveBasePlan plan)
    { Original = original; Profile = profile; Binding = binding; Location = location; Intermediate = intermediate; Output = output; _plan = plan.ToJson(false); }
    internal RomImage Original { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal VerifiedCompensationLocation Location { get; }
    public RomImage Intermediate { get; }
    public RomImage Output { get; }
    public P28AdaptiveBasePlan Plan => P28AdaptiveBasePlan.Parse(_plan);
}

public static class P28AdaptiveBaseEditor
{
    public const string Purpose = "pc-only-adaptive-base-checksum-preserving-export";
    public const string ContractId = "p28-single-adaptive-bank-base-pair-v1";
    public const string Policy = "0 < baseCutRaw < baseResumeRaw < 65535; no target wrap and strictly ordered targets for every raw00CE in 0..65535; exporter policy, not all RAM histories or engine safety";
    public const string Scope = "One explicitly selected adaptive bank base pair; origins/coefficients, other bank, fixed pair and code unchanged. Base pair, not a constant RPM limiter";
    public const string EditAudit = "Separate numeric-base admission; producer LC +2 reads are numeric floors/targets, never pointer origins, lengths or control destinations. Normal source-listed consumer scope retains unchanged pointer literals/strides, scanner stopping keys, axis bounds and intact RAM/stacks. Historical location signature is unchanged; no general calibration-edit authority.";
    public const string Readiness = "PcInspectionOnly / NotFlashReady";
    internal static int[] Footprint(int bank) => new[] { false, true }.SelectMany(c => new[] { P28LimiterInspector.AdaptiveBaseOffset(bank, c), P28LimiterInspector.AdaptiveBaseOffset(bank, c) + 1 }).ToArray();
    internal static void PairPolicy(P28AdaptiveBasePair p)
    {
        ArgumentNullException.ThrowIfNull(p); _ = Footprint(p.Bank);
        if (p.BaseCutRaw <= 0 || p.BaseCutRaw >= p.BaseResumeRaw || p.BaseResumeRaw >= 65535) throw new ArgumentException(Policy);
    }
    internal static P28AdaptiveBasePair ReadPair(RomImage image, int bank) => new(bank,
        P28LimiterInspector.Word(image.Span, P28LimiterInspector.AdaptiveBaseOffset(bank, true)),
        P28LimiterInspector.Word(image.Span, P28LimiterInspector.AdaptiveBaseOffset(bank, false)));
    internal static P28AdaptiveBaseWord[] Describe(RomImage original, P28AdaptiveBasePair p)
    {
        PairPolicy(p); original.ValidateExactSize(32768);
        return new[] { true, false }.Select(c =>
        {
            var a = P28LimiterInspector.AdaptiveBaseOffset(p.Bank, c); var old = P28LimiterInspector.Word(original.Span, a);
            var value = c ? p.BaseCutRaw : p.BaseResumeRaw;
            return new P28AdaptiveBaseWord(P28LimiterInspector.AdaptiveBaseId(p.Bank, c), a, 2, "LittleEndianUnsignedProgramData",
                old, value, P28FixedLimiterEditor.Encode(old), P28FixedLimiterEditor.Encode(value), a - 2,
                P28LimiterInspector.Word(original.Span, a - 2), a + 2, P28LimiterInspector.Word(original.Span, a + 2));
        }).ToArray();
    }
    internal static P28AdaptiveDomainCheck CheckDomain(IReadOnlyList<P28AdaptiveBaseWord> words)
    {
        if (words.Count != 2) throw new InvalidDataException("Exactly two numeric base words required.");
        var maxCut = 0; var maxResume = 0; var gap = int.MaxValue;
        for (var x = 0; x <= 65535; x++)
        {
            int Target(P28AdaptiveBaseWord w) => w.NewWord + (int)((long)Math.Max(0, x - w.Origin) * w.Coefficient / 65536);
            var cut = Target(words[0]); var resume = Target(words[1]);
            maxCut = Math.Max(maxCut, cut); maxResume = Math.Max(maxResume, resume); gap = Math.Min(gap, resume - cut);
        }
        return new(0, 65535, 65536, maxCut, maxResume, gap, maxCut <= 65535 && maxResume <= 65535, gap > 0);
    }
    // Pure arithmetic test seam. Does not create admission or a publication token.
    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) Compose(RomImage original, P28AdaptiveBasePair pair)
    {
        var words = Describe(original, pair); var domain = CheckDomain(words);
        if (!domain.NoTargetWrap || !domain.StrictTargetOrder) throw new ArgumentException(Policy);
        var b = original.CreateModifiedCopy(words.Select(w => new BytePatch(w.Offset, w.NewBytes.ToArray())));
        var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult;
        var old = original.Span[0x7FFF];
        var compensation = new P28ComputedCompensation(0x7FFF, old, P28ChecksumPreservingEditor.ComputeCompensation(old, residue), P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(0x7FFF, new[] { compensation.NewByte })]), compensation);
    }
    internal static void RequireFootprint(RomImage original, RomImage child, int bank)
    {
        if (P28FixedLimiterEditor.Diff(original, child).Any(d => !Footprint(bank).Contains(d.Offset) && d.Offset != 0x7FFF))
            throw new InvalidDataException("Extra byte outside the selected two separate base words and reviewed compensation.");
    }
    internal static void MappingGuard(RomImage original)
    {
        original.ValidateExactSize(32768);
        foreach (var (bank, cut, operand) in new[] { (0, false, 0x487D), (0, true, 0x4880), (1, false, 0x4886), (1, true, 0x4889) })
            if (P28LimiterInspector.Word(original.Span, operand) + 2 != P28LimiterInspector.AdaptiveBaseOffset(bank, cut))
                throw new InvalidDataException("Producer pointer does not match the code-owned program-word mapping.");
    }
    public static P28AdaptiveBasePreview Preview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28AdaptiveBasePair pair)
    {
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        MappingGuard(original);
        if (location.Offset != 0x7FFF) throw new InvalidDataException("Existing location audit is not applicable.");
        var (b, c, compensation) = Compose(original, pair); RequireFootprint(original, c, pair.Bank);
        var words = Describe(original, pair); var diff = P28FixedLimiterEditor.Diff(original, c);
        var aSum = P28NativeChecksumArithmetic.Calculate(original).ComputedResult; var cSum = P28NativeChecksumArithmetic.Calculate(c).ComputedResult;
        if (aSum != 0 || cSum != 0) throw new InvalidDataException("Original/output require zero residue.");
        var p = new P28AdaptiveBasePlan(1, Purpose, ContractId, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), pair, words, CheckDomain(words),
            location.DefinitionId, location.DefinitionDigest, location.EvidenceIdentity, location.EvidenceScope, EditAudit, compensation,
            aSum, P28NativeChecksumArithmetic.Calculate(b).ComputedResult, cSum, b.Hash, c.Hash, diff, diff.Length == 0,
            Policy, Scope, P28NativeChecksumArithmetic.Contract.Id, false, Readiness);
        return new(original, profile, binding, location, b, c, p);
    }
    public static P28AdaptiveBasePreview Reproduce(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28AdaptiveBasePlan plan)
    {
        var frozen = P28AdaptiveBasePlan.Parse(plan.ToJson(false));
        var p = Preview(original, profile, binding, confirmed, location, frozen.RequestedPair);
        if (frozen.ToJson(false) != p.Plan.ToJson(false)) throw new InvalidDataException("Adaptive plan does not reproduce from exact original and code-owned contract.");
        return p;
    }
    internal static void Shape(P28AdaptiveBasePlan p)
    {
        P28RawEditJson.ValidateObject(p); PairPolicy(p.RequestedPair);
        if (p.FormatVersion != 1 || p.Purpose != Purpose || p.ContractId != ContractId || p.Policy != Policy || p.Scope != Scope ||
            p.EditAudit != EditAudit || p.Size != 32768 || p.PhysicalRpmAvailable || p.Readiness != Readiness || p.ResidueA != 0 || p.ResidueC != 0 ||
            p.Words.Count != 2 || p.ExpectedDiff.Count > 5 || p.IsNoOp != (p.ExpectedDiff.Count == 0) ||
            p.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id || p.Compensation.Offset != 0x7FFF ||
            p.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId || p.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(p.Compensation.OldByte, p.ResidueB))
            throw new InvalidDataException("Unsupported adaptive-base metadata.");
        for (var i = 0; i < 2; i++)
        {
            var w = p.Words[i]; var a = P28LimiterInspector.AdaptiveBaseOffset(p.RequestedPair.Bank, i == 0);
            if (w.FieldId != P28LimiterInspector.AdaptiveBaseId(p.RequestedPair.Bank, i == 0) || w.Offset != a || w.Width != 2 ||
                w.Encoding != "LittleEndianUnsignedProgramData" || w.OriginOffset != a - 2 || w.CoefficientOffset != a + 2 ||
                w.OldWord is < 0 or > 65535 || w.Origin is < 0 or > 65535 || w.Coefficient is < 0 or > 65535 ||
                w.NewWord != (i == 0 ? p.RequestedPair.BaseCutRaw : p.RequestedPair.BaseResumeRaw) ||
                !w.OldBytes.SequenceEqual(P28FixedLimiterEditor.Encode(w.OldWord)) || !w.NewBytes.SequenceEqual(P28FixedLimiterEditor.Encode(w.NewWord)))
                throw new InvalidDataException("Invalid adaptive program-word encoding/context.");
        }
        if (!p.Domain.NoTargetWrap || !p.Domain.StrictTargetOrder || p.Domain != CheckDomain(p.Words)) throw new InvalidDataException("Invalid arithmetic domain evidence.");
        var diff = p.Words.SelectMany(w => Enumerable.Range(0, 2).Select(i => new P28RawByteDiff(w.Offset + i, w.OldBytes[i], w.NewBytes[i])))
            .Append(new(p.Compensation.Offset, p.Compensation.OldByte, p.Compensation.NewByte)).Where(d => d.OldByte != d.NewByte).OrderBy(d => d.Offset);
        if (!p.ExpectedDiff.SequenceEqual(diff)) throw new InvalidDataException("Encoded adaptive pair/diff contradiction.");
        foreach (var d in new[] { p.OriginalHash.Sha256, p.IntermediateHash.Sha256, p.OutputHash.Sha256, p.ProfileDigest, p.BindingDigest, p.LocationDigest })
            if (d.Length != 64 || !d.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed adaptive identity.");
        foreach (var h in new[] { p.OriginalHash, p.IntermediateHash, p.OutputHash })
            if (h.Crc32.Length != 8 || !h.Crc32.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed CRC identity.");
    }
}
