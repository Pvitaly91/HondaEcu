using System.Text;

namespace HondaEcu.Core;

public sealed record P28FixedLimiterPair(int CutRaw, int ResumeRaw);
public sealed record P28FixedLimiterOperand(string FieldId, int Offset, int Width, string Encoding,
    int OriginalWord, int NewWord, IReadOnlyList<byte> OriginalBytes, IReadOnlyList<byte> NewBytes);
public sealed record P28FixedLimiterPlan(int FormatVersion, string Purpose, string ContractId, int ContractVersion,
    RomHash OriginalHash, int Size, string ProfileId, string ProfileDigest, string BindingDigest,
    P28FixedLimiterPair RequestedPair, IReadOnlyList<P28FixedLimiterOperand> Operands,
    string CompensationDefinitionId, string CompensationDefinitionDigest, string CompensationEvidenceIdentity,
    string LocationScope, string LocationApplicability, P28ComputedCompensation Compensation,
    byte ResidueA, byte ResidueB, byte ResidueC, RomHash IntermediateHash, RomHash OutputHash,
    IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp, string PairPolicy, string Scope,
    string ChecksumContractId, bool PhysicalRpmAvailable, string Readiness)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28FixedLimiterPlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 65536) throw new InvalidDataException("Limiter plan exceeds 64 KiB.");
        var p = P28RawEditJson.Parse<P28FixedLimiterPlan>(json);
        P28FixedLimiterEditor.ValidateShape(p); return p;
    }
    public static P28FixedLimiterPlan Load(string path) => Parse(File.ReadAllText(path));
}

/// <summary>Immutable preview, not a publication capability or a child baseline binding.</summary>
public sealed class P28FixedLimiterPreview
{
    private readonly string _plan;
    internal P28FixedLimiterPreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, RomImage intermediate, RomImage output, P28FixedLimiterPlan plan)
    { Original = original; Profile = profile; Binding = binding; Location = location; Intermediate = intermediate; Output = output; _plan = plan.ToJson(false); }
    internal RomImage Original { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal VerifiedCompensationLocation Location { get; }
    public RomImage Intermediate { get; }
    public RomImage Output { get; }
    public P28FixedLimiterPlan Plan => P28FixedLimiterPlan.Parse(_plan);
}

public static class P28FixedLimiterEditor
{
    public const string Purpose = "pc-only-fixed-limiter-checksum-preserving-export";
    public const string ContractId = "p28-fixed-limiter-operands-v1";
    public const string Scope = "Fixed context only; adaptive tables unchanged";
    public const string PairPolicy = "0 < cutRaw < resumeRaw < 65535; exporter policy, not factory or engine-safety bounds";
    public const string Readiness = "PcInspectionOnly / NotFlashReady";
    public const string LocationApplicability = "Separate operand admission: numeric MOV DP/L A word immediates only; unchanged opcodes, encoded control targets, vectors, pointer origins, scanner barriers and cache bounds. Both branch outcomes already in the reviewed location scope; normal RAM/stack restrictions remain. Not a general code-edit permission.";
    internal static int[] Footprint => new[] { P28LimiterInspector.ResumeOffset, P28LimiterInspector.ResumeOffset + 1, P28LimiterInspector.CutOffset, P28LimiterInspector.CutOffset + 1 };
    internal static void ValidatePair(P28FixedLimiterPair pair)
    {
        ArgumentNullException.ThrowIfNull(pair);
        if (pair.CutRaw <= 0 || pair.ResumeRaw >= 65535 || pair.CutRaw >= pair.ResumeRaw)
            throw new ArgumentException(PairPolicy);
    }
    internal static P28FixedLimiterPair ReadPair(RomImage image) => new(
        P28LimiterInspector.Word(image.Span, P28LimiterInspector.FieldOffset(P28LimiterInspector.CutId)),
        P28LimiterInspector.Word(image.Span, P28LimiterInspector.FieldOffset(P28LimiterInspector.ResumeId)));
    internal static byte[] Encode(int value) => [(byte)(value & 255), (byte)(value >> 8)];
    internal static RomImage EncodePair(RomImage original, P28FixedLimiterPair pair)
    {
        ValidatePair(pair); P28LimiterInspector.OperandGuard(original);
        return original.CreateModifiedCopy([
            new(P28LimiterInspector.FieldOffset(P28LimiterInspector.CutId), Encode(pair.CutRaw)),
            new(P28LimiterInspector.FieldOffset(P28LimiterInspector.ResumeId), Encode(pair.ResumeRaw))]);
    }
    internal static P28RawByteDiff[] Diff(RomImage original, RomImage output)
    {
        output.ValidateExactSize(original.Size);
        return Enumerable.Range(0, original.Size).Where(i => original.Span[i] != output.Span[i])
            .Select(i => new P28RawByteDiff(i, original.Span[i], output.Span[i])).ToArray();
    }
    // Pure in-memory arithmetic seam; no binding, location or publication authority.
    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) ComposeOperands(
        RomImage original, P28FixedLimiterPair pair, int compensationOffset)
    {
        if (compensationOffset != 0x7FFF) throw new ArgumentException("Only the code-owned candidate location is supported.");
        var b = EncodePair(original, pair);
        var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult;
        var old = original.Span[compensationOffset];
        var compensation = new P28ComputedCompensation(compensationOffset, old,
            P28ChecksumPreservingEditor.ComputeCompensation(old, residue), P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(compensationOffset, new[] { compensation.NewByte })]), compensation);
    }
    public static P28FixedLimiterPreview Preview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28FixedLimiterPair pair)
    {
        // The old verifier authenticates only the location. No VTEC slot/child is fabricated.
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        P28LimiterInspector.OperandGuard(original); ValidatePair(pair);
        if (location.Offset != 0x7FFF || Footprint.Contains(location.Offset)) throw new InvalidDataException("Location contract is not applicable.");
        var (b, c, compensation) = ComposeOperands(original, pair, location.Offset);
        var residueB = P28NativeChecksumArithmetic.Calculate(b).ComputedResult;
        var diff = Diff(original, c); RequireFootprint(original, c, location.Offset);
        var residueA = P28NativeChecksumArithmetic.Calculate(original).ComputedResult;
        var residueC = P28NativeChecksumArithmetic.Calculate(c).ComputedResult;
        if (residueA != 0 || residueC != 0) throw new InvalidDataException("Full original/output arithmetic must have zero residue.");
        var old = ReadPair(original);
        P28FixedLimiterOperand Operand(string id, int before, int after) => new(id, P28LimiterInspector.FieldOffset(id), 2,
            "LittleEndianUnsignedWordImmediate", before, after, Array.AsReadOnly(Encode(before)), Array.AsReadOnly(Encode(after)));
        var plan = new P28FixedLimiterPlan(1, Purpose, ContractId, 1, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), pair,
            Array.AsReadOnly(new[] { Operand(P28LimiterInspector.CutId, old.CutRaw, pair.CutRaw), Operand(P28LimiterInspector.ResumeId, old.ResumeRaw, pair.ResumeRaw) }),
            location.DefinitionId, location.DefinitionDigest, location.EvidenceIdentity, location.EvidenceScope, LocationApplicability,
            compensation, residueA, residueB, residueC, b.Hash, c.Hash, Array.AsReadOnly(diff), diff.Length == 0,
            PairPolicy, Scope, P28NativeChecksumArithmetic.Contract.Id, false, Readiness);
        return new(original, profile, binding, location, b, c, plan);
    }
    public static P28FixedLimiterPreview Reproduce(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28FixedLimiterPlan plan)
    {
        // Snapshot every serialized collection before awaiting or comparing.
        var frozen = P28FixedLimiterPlan.Parse(plan.ToJson(false));
        var expected = Preview(original, profile, binding, confirmed, location, frozen.RequestedPair);
        if (frozen.ToJson(false) != expected.Plan.ToJson(false)) throw new InvalidDataException("Limiter plan does not reproduce exactly from the admitted original and code-owned contract.");
        return expected;
    }
    internal static void RequireFootprint(RomImage original, RomImage output, int compensationOffset)
    {
        P28LimiterInspector.OperandGuard(original); P28LimiterInspector.OperandGuard(output);
        if (Diff(original, output).Any(d => !Footprint.Contains(d.Offset) && d.Offset != compensationOffset))
            throw new InvalidDataException("Extra byte outside the four separate operands and admitted compensation byte.");
    }
    internal static void ValidateShape(P28FixedLimiterPlan p)
    {
        P28RawEditJson.ValidateObject(p); ValidatePair(p.RequestedPair);
        if (p.FormatVersion != 1 || p.Purpose != Purpose || p.ContractId != ContractId || p.ContractVersion != 1 ||
            p.Size != 32768 || p.Scope != Scope || p.PairPolicy != PairPolicy || p.LocationApplicability != LocationApplicability ||
            p.Readiness != Readiness || p.PhysicalRpmAvailable || p.ResidueA != 0 || p.ResidueC != 0 ||
            p.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id || p.Operands.Count != 2 ||
            p.ExpectedDiff.Count > 5 || p.IsNoOp != (p.ExpectedDiff.Count == 0) || p.Compensation.Offset != 0x7FFF ||
            p.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId ||
            p.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(p.Compensation.OldByte, p.ResidueB))
            throw new InvalidDataException("Unsupported limiter plan metadata.");
        foreach (var digest in new[] { p.OriginalHash.Sha256, p.IntermediateHash.Sha256, p.OutputHash.Sha256, p.ProfileDigest, p.BindingDigest, p.CompensationDefinitionDigest })
            if (digest.Length != 64 || !digest.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed limiter identity.");
        foreach (var hash in new[] { p.OriginalHash, p.IntermediateHash, p.OutputHash })
            if (hash.Crc32.Length != 8 || !hash.Crc32.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed CRC identity.");
        var ids = new[] { P28LimiterInspector.CutId, P28LimiterInspector.ResumeId };
        for (var i = 0; i < 2; i++)
        {
            var o = p.Operands[i];
            if (o.FieldId != ids[i] || o.Offset != P28LimiterInspector.FieldOffset(ids[i]) || o.Width != 2 ||
                o.Encoding != "LittleEndianUnsignedWordImmediate" || o.OriginalWord is < 0 or > 65535 ||
                o.NewWord != (i == 0 ? p.RequestedPair.CutRaw : p.RequestedPair.ResumeRaw) ||
                !o.OriginalBytes.SequenceEqual(Encode(o.OriginalWord)) || !o.NewBytes.SequenceEqual(Encode(o.NewWord)))
                throw new InvalidDataException("Invalid limiter operand metadata.");
        }
        var expectedDiff = p.Operands.SelectMany(o => Enumerable.Range(0, 2).Select(i => new P28RawByteDiff(o.Offset + i, o.OriginalBytes[i], o.NewBytes[i])))
            .Append(new(p.Compensation.Offset, p.Compensation.OldByte, p.Compensation.NewByte)).Where(d => d.OldByte != d.NewByte).OrderBy(d => d.Offset);
        if (!p.ExpectedDiff.SequenceEqual(expectedDiff)) throw new InvalidDataException("Actual variable-size diff differs from encoded operands/compensation.");
    }
}
