using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28CombinedBankPair(int BaseCutRaw, int BaseResumeRaw);
public sealed record P28CombinedLimiterSettings(P28FixedLimiterPair? Fixed, P28CombinedBankPair? Bank0, P28CombinedBankPair? Bank1)
{
    public static P28CombinedLimiterSettings Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 4096) throw new InvalidDataException("Combined settings exceed 4 KiB.");
        using var d = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 4 });
        var r = d.RootElement;
        static void Shape(JsonElement e, params string[] names)
        {
            if (e.ValueKind != JsonValueKind.Object || !e.EnumerateObject().Select(p => p.Name).Order().SequenceEqual(names.Order()))
                throw new InvalidDataException("Unknown, duplicate or missing combined setting; every group must be explicit.");
        }
        static int Raw(JsonElement e, string name)
        {
            var v = e.GetProperty(name);
            if (v.ValueKind != JsonValueKind.Number || !v.GetRawText().All(char.IsAsciiDigit) || !v.TryGetInt32(out var n))
                throw new InvalidDataException("Only unsigned integer raw values are accepted.");
            return n;
        }
        Shape(r, "formatVersion", "purpose", "fixed", "bank0", "bank1");
        if (Raw(r, "formatVersion") != 1 || r.GetProperty("purpose").GetString() != "explicit-limiter-group-selection")
            throw new InvalidDataException("Unsupported combined settings contract.");
        P28FixedLimiterPair? fixedPair = null;
        var f = r.GetProperty("fixed");
        if (f.ValueKind != JsonValueKind.Null) { Shape(f, "cutRaw", "resumeRaw"); fixedPair = new(Raw(f, "cutRaw"), Raw(f, "resumeRaw")); }
        P28CombinedBankPair? Bank(string name)
        {
            var b = r.GetProperty(name); if (b.ValueKind == JsonValueKind.Null) return null;
            Shape(b, "baseCutRaw", "baseResumeRaw"); return new(Raw(b, "baseCutRaw"), Raw(b, "baseResumeRaw"));
        }
        var settings = new P28CombinedLimiterSettings(fixedPair, Bank("bank0"), Bank("bank1"));
        settings.Validate(); return settings;
    }
    internal void Validate()
    {
        if (Fixed is null && Bank0 is null && Bank1 is null) throw new ArgumentException("At least one explicit group is required.");
        ValidatePairs();
    }
    internal void ValidatePairs()
    {
        if (Fixed is { } f) P28FixedLimiterEditor.ValidatePair(f);
        if (Bank0 is { } a) P28AdaptiveBaseEditor.PairPolicy(new(0, a.BaseCutRaw, a.BaseResumeRaw));
        if (Bank1 is { } b) P28AdaptiveBaseEditor.PairPolicy(new(1, b.BaseCutRaw, b.BaseResumeRaw));
    }
}

public sealed record P28CombinedLimiterGroup(string Id, bool Requested, bool EffectivelyChanged,
    IReadOnlyList<P28FixedLimiterOperand> FixedOperands, IReadOnlyList<P28AdaptiveBaseWord> AdaptiveWords,
    IReadOnlyList<P28AdaptiveDomainCheck> DomainChecks, string PolicyResult);
public sealed record P28CombinedLimiterPlan(int FormatVersion, string Purpose, string ContractId,
    RomHash OriginalHash, int Size, string ProfileId, string ProfileDigest, string BindingDigest,
    IReadOnlyList<P28CombinedLimiterGroup> Groups, string LocationId, string LocationDigest,
    string LocationEvidenceIdentity, string LocationScope, string EditAudit, P28ComputedCompensation Compensation,
    byte ResidueA, byte ResidueB, byte ResidueC, RomHash IntermediateHash, RomHash OutputHash,
    IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp, string Scope, string ChecksumContractId,
    bool PhysicalRpmAvailable, string Readiness)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28CombinedLimiterPlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 65536) throw new InvalidDataException("Combined plan exceeds 64 KiB.");
        var p = P28RawEditJson.Parse<P28CombinedLimiterPlan>(json);
        P28CombinedLimiterEditor.Shape(p); return p;
    }
    public static P28CombinedLimiterPlan Load(string path) => Parse(File.ReadAllText(path));
}

public sealed class P28CombinedLimiterPreview
{
    private readonly string _plan;
    internal P28CombinedLimiterPreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, RomImage intermediate, RomImage output, P28CombinedLimiterPlan plan)
    { Original = original; Profile = profile; Binding = binding; Location = location; Intermediate = intermediate; Output = output; _plan = plan.ToJson(false); }
    internal RomImage Original { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal VerifiedCompensationLocation Location { get; }
    public RomImage Intermediate { get; }
    public RomImage Output { get; }
    public P28CombinedLimiterPlan Plan => P28CombinedLimiterPlan.Parse(_plan);
}

public static class P28CombinedLimiterEditor
{
    public const string Purpose = "pc-only-combined-limiter-checksum-preserving-export";
    public const string ContractId = "p28-combined-limiter-groups-v1";
    public const string Scope = "Combined limiter research edit; one original, explicit fixed/bank0/bank1 pairs, one final-byte-sum compensation; no synchronization or child chains";
    public const string EditAudit = "Simultaneous M1n numeric comparison and M1o numeric reset/floor/target flows preserve pointer literals, strides, stopping keys, index bounds, instruction widths and encoded destinations under the original intact-state/source-listed location scope. Stateful source selection may change histories, not turn thresholds into program pointers. Old signed location payload unchanged; bounded non-reading is supplemental, not global proof.";
    internal static P28CombinedLimiterGroup[] Describe(RomImage original, P28CombinedLimiterSettings settings)
    {
        settings.Validate(); return DescribeGroups(original, settings);
    }
    // Pure descriptions also allow an unchanged family in a separately admitted composition.
    internal static P28CombinedLimiterGroup[] DescribeGroups(RomImage original, P28CombinedLimiterSettings settings)
    {
        settings.ValidatePairs(); original.ValidateExactSize(32768);
        var oldFixed = P28FixedLimiterEditor.ReadPair(original); var f = settings.Fixed ?? oldFixed;
        var operands = new[] { P28LimiterInspector.CutId, P28LimiterInspector.ResumeId }.Select((id, i) =>
        {
            var offset = P28LimiterInspector.FieldOffset(id); var old = P28LimiterInspector.Word(original.Span, offset); var value = i == 0 ? f.CutRaw : f.ResumeRaw;
            return new P28FixedLimiterOperand(id, offset, 2, "LittleEndianUnsignedWordImmediate", old, value, P28FixedLimiterEditor.Encode(old), P28FixedLimiterEditor.Encode(value));
        }).ToArray();
        var groups = new List<P28CombinedLimiterGroup> { new("fixed", settings.Fixed is not null, f != oldFixed, operands, [], [], settings.Fixed is null ? "NotRequested" : "PairPolicyPassed") };
        for (var bank = 0; bank < 2; bank++)
        {
            var requested = bank == 0 ? settings.Bank0 : settings.Bank1; var old = P28AdaptiveBaseEditor.ReadPair(original, bank);
            var pair = requested is null ? old : new P28AdaptiveBasePair(bank, requested.BaseCutRaw, requested.BaseResumeRaw);
            var words = P28AdaptiveBaseEditor.Describe(original, pair);
            var checks = requested is null ? Array.Empty<P28AdaptiveDomainCheck>() : new[] { P28AdaptiveBaseEditor.CheckDomain(words) };
            if (checks.Any(c => !c.NoTargetWrap || !c.StrictTargetOrder)) throw new ArgumentException(P28AdaptiveBaseEditor.Policy);
            groups.Add(new("bank" + bank, requested is not null, pair != old, [], words, checks, requested is null ? "NotRequested" : "PairAndFullTargetDomainPassed"));
        }
        return groups.ToArray();
    }
    internal static P28CombinedLimiterSettings Settings(P28CombinedLimiterPlan p)
    {
        var f = p.Groups[0];
        P28CombinedBankPair? Bank(int index) => p.Groups[index].Requested ? new(p.Groups[index].AdaptiveWords[0].NewWord, p.Groups[index].AdaptiveWords[1].NewWord) : null;
        return new(f.Requested ? new(f.FixedOperands[0].NewWord, f.FixedOperands[1].NewWord) : null, Bank(1), Bank(2));
    }
    internal static IEnumerable<P28RawByteDiff> WordBytes(IEnumerable<P28CombinedLimiterGroup> groups) => groups.SelectMany(g =>
        g.FixedOperands.SelectMany(w => Enumerable.Range(0, 2).Select(i => new P28RawByteDiff(w.Offset + i, w.OriginalBytes[i], w.NewBytes[i])))
        .Concat(g.AdaptiveWords.SelectMany(w => Enumerable.Range(0, 2).Select(i => new P28RawByteDiff(w.Offset + i, w.OldBytes[i], w.NewBytes[i])))));
    // Pure arithmetic seam: no signatures, binding, execution or publication authority.
    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) Compose(RomImage original, P28CombinedLimiterSettings settings)
    {
        var groups = Describe(original, settings);
        var b = original.CreateModifiedCopy(WordBytes(groups.Where(g => g.Requested)).Select(d => new BytePatch(d.Offset, [d.NewByte])));
        var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult; var old = original.Span[0x7FFF];
        var compensation = new P28ComputedCompensation(0x7FFF, old, P28ChecksumPreservingEditor.ComputeCompensation(old, residue), P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(0x7FFF, [compensation.NewByte])]), compensation);
    }
    public static P28CombinedLimiterPreview Preview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28CombinedLimiterSettings settings)
    {
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        P28LimiterInspector.OperandGuard(original); P28AdaptiveBaseEditor.MappingGuard(original);
        if (location.Offset != 0x7FFF) throw new InvalidDataException("Existing location audit is not applicable.");
        var (b, c, compensation) = Compose(original, settings); var diff = P28FixedLimiterEditor.Diff(original, c);
        var p = new P28CombinedLimiterPlan(1, Purpose, ContractId, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), Describe(original, settings),
            location.DefinitionId, location.DefinitionDigest, location.EvidenceIdentity, location.EvidenceScope, EditAudit, compensation,
            P28NativeChecksumArithmetic.Calculate(original).ComputedResult, P28NativeChecksumArithmetic.Calculate(b).ComputedResult,
            P28NativeChecksumArithmetic.Calculate(c).ComputedResult, b.Hash, c.Hash, diff, diff.Length == 0,
            Scope, P28NativeChecksumArithmetic.Contract.Id, false, P28AdaptiveBaseEditor.Readiness);
        Shape(p); return new(original, profile, binding, location, b, c, p);
    }
    public static P28CombinedLimiterPreview Reproduce(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28CombinedLimiterPlan plan)
    {
        var frozen = P28CombinedLimiterPlan.Parse(plan.ToJson(false));
        var expected = Preview(original, profile, binding, confirmed, location, Settings(frozen));
        if (frozen.ToJson(false) != expected.Plan.ToJson(false)) throw new InvalidDataException("Combined plan does not reproduce from exact original and code-owned contract.");
        return expected;
    }
    internal static void Shape(P28CombinedLimiterPlan p)
    {
        P28RawEditJson.ValidateObject(p);
        if (p.FormatVersion != 1 || p.Purpose != Purpose || p.ContractId != ContractId || p.Size != 32768 || p.Scope != Scope ||
            p.EditAudit != EditAudit || p.Readiness != P28AdaptiveBaseEditor.Readiness || p.PhysicalRpmAvailable || p.ResidueA != 0 || p.ResidueC != 0 ||
            p.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id || p.Groups.Count != 3 ||
            !p.Groups.Select(g => g.Id).SequenceEqual(new[] { "fixed", "bank0", "bank1" }) ||
            p.Compensation.Offset != 0x7FFF || p.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId ||
            p.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(p.Compensation.OldByte, p.ResidueB))
            throw new InvalidDataException("Unsupported combined metadata.");
        for (var n = 0; n < 3; n++)
        {
            var g = p.Groups[n];
            if (g.FixedOperands.Count != (n == 0 ? 2 : 0) || g.AdaptiveWords.Count != (n == 0 ? 0 : 2) ||
                g.DomainChecks.Count != (n != 0 && g.Requested ? 1 : 0)) throw new InvalidDataException("Invalid combined group fields.");
            for (var i = 0; i < 2; i++)
            {
                var offset = n == 0 ? P28LimiterInspector.FieldOffset(i == 0 ? P28LimiterInspector.CutId : P28LimiterInspector.ResumeId) : P28LimiterInspector.AdaptiveBaseOffset(n - 1, i == 0);
                var field = n == 0 ? (i == 0 ? P28LimiterInspector.CutId : P28LimiterInspector.ResumeId) : P28LimiterInspector.AdaptiveBaseId(n - 1, i == 0);
                var w = n == 0 ? g.FixedOperands[i] : null; var a = n == 0 ? null : g.AdaptiveWords[i];
                var old = w?.OriginalWord ?? a!.OldWord; var value = w?.NewWord ?? a!.NewWord;
                if ((w?.Offset ?? a!.Offset) != offset || (w?.FieldId ?? a!.FieldId) != field || (w?.Width ?? a!.Width) != 2 ||
                    old is < 0 or > 65535 || value is < 0 or > 65535 ||
                    !(w?.OriginalBytes ?? a!.OldBytes).SequenceEqual(P28FixedLimiterEditor.Encode(old)) ||
                    !(w?.NewBytes ?? a!.NewBytes).SequenceEqual(P28FixedLimiterEditor.Encode(value)) ||
                    (w?.Encoding ?? a!.Encoding) != (n == 0 ? "LittleEndianUnsignedWordImmediate" : "LittleEndianUnsignedProgramData") ||
                    a is not null && (a.OriginOffset != offset - 2 || a.CoefficientOffset != offset + 2 || a.Origin is < 0 or > 65535 || a.Coefficient is < 0 or > 65535))
                    throw new InvalidDataException("Invalid code-owned field encoding/context.");
            }
            var changed = WordBytes([g]).Any(d => d.OldByte != d.NewByte);
            if (g.EffectivelyChanged != changed || !g.Requested && changed ||
                g.PolicyResult != (!g.Requested ? "NotRequested" : n == 0 ? "PairPolicyPassed" : "PairAndFullTargetDomainPassed"))
                throw new InvalidDataException("Contradictory group selection/effect.");
            if (g.DomainChecks.Count == 1 && (g.DomainChecks[0] != P28AdaptiveBaseEditor.CheckDomain(g.AdaptiveWords) || !g.DomainChecks[0].NoTargetWrap || !g.DomainChecks[0].StrictTargetOrder))
                throw new InvalidDataException("Invalid combined target domain.");
        }
        Settings(p).Validate();
        var expected = WordBytes(p.Groups).Append(new(p.Compensation.Offset, p.Compensation.OldByte, p.Compensation.NewByte)).Where(d => d.OldByte != d.NewByte).OrderBy(d => d.Offset).ToArray();
        if (p.ExpectedDiff.Count > 13 || !p.ExpectedDiff.SequenceEqual(expected) || p.IsNoOp != (expected.Length == 0)) throw new InvalidDataException("Combined exact diff contradiction.");
        foreach (var h in new[] { p.OriginalHash, p.IntermediateHash, p.OutputHash })
            if (h.Sha256.Length != 64 || !h.Sha256.All(Uri.IsHexDigit) || h.Crc32.Length != 8 || !h.Crc32.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed image identity.");
        foreach (var d in new[] { p.ProfileDigest, p.BindingDigest, p.LocationDigest })
            if (d.Length != 64 || !d.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed input identity.");
    }
}
