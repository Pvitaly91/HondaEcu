using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28BasicVtecSetting(string Slot, int RawValue);
public sealed class P28BasicCalibrationSettings
{
    public P28BasicVtecSetting? Vtec { get; }
    public P28CombinedLimiterSettings Limiter { get; }
    public P28IdleTableSettings Idle { get; }
    public P28BasicCalibrationSettings(P28BasicVtecSetting? vtec, P28FixedLimiterPair? fixedPair,
        P28CombinedBankPair? bank0, P28CombinedBankPair? bank1, IReadOnlyList<int>? baseTable, IReadOnlyList<int>? lateTable)
    {
        if (vtec is not null)
        {
            _ = P28ThresholdLogic.ResolveSlot(vtec.Slot);
            if (vtec.RawValue is < 0 or > 255) throw new ArgumentException("VTEC requires one unsigned raw threshold byte.");
        }
        Vtec = vtec; Limiter = new(fixedPair, bank0, bank1); Limiter.ValidatePairs(); Idle = new(baseTable, lateTable);
    }
    public static P28BasicCalibrationSettings Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 4096) throw new InvalidDataException("Basic settings exceed 4 KiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 4 }); var r = document.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "vtec", "fixed", "bank0", "bank1", "baseTable", "lateTable");
        static int Integer(JsonElement e)
        {
            if (e.ValueKind != JsonValueKind.Number || !e.GetRawText().All(char.IsAsciiDigit) || !e.TryGetInt32(out var n))
                throw new InvalidDataException("Unsigned decimal integer required; no rounding or clamp.");
            return n;
        }
        if (Integer(r.GetProperty("formatVersion")) != 1 || r.GetProperty("purpose").GetString() != "explicit-basic-calibration-selection")
            throw new InvalidDataException("Unsupported basic settings.");
        P28BasicVtecSetting? vtec = null; P28FixedLimiterPair? fixedPair = null;
        var v = r.GetProperty("vtec");
        if (v.ValueKind != JsonValueKind.Null) { P28LimiterScenario.Shape(v, "slot", "rawValue"); vtec = new(v.GetProperty("slot").GetString()!, Integer(v.GetProperty("rawValue"))); }
        var f = r.GetProperty("fixed");
        if (f.ValueKind != JsonValueKind.Null) { P28LimiterScenario.Shape(f, "cutRaw", "resumeRaw"); fixedPair = new(Integer(f.GetProperty("cutRaw")), Integer(f.GetProperty("resumeRaw"))); }
        P28CombinedBankPair? Bank(string key)
        {
            var b = r.GetProperty(key); if (b.ValueKind == JsonValueKind.Null) return null;
            P28LimiterScenario.Shape(b, "baseCutRaw", "baseResumeRaw"); return new(Integer(b.GetProperty("baseCutRaw")), Integer(b.GetProperty("baseResumeRaw")));
        }
        int[]? Table(string key) => r.GetProperty(key).ValueKind == JsonValueKind.Null ? null : r.GetProperty(key).EnumerateArray().Select(Integer).ToArray();
        return new(vtec, fixedPair, Bank("bank0"), Bank("bank1"), Table("baseTable"), Table("lateTable"));
    }
}
public sealed record P28BasicVtecGroup(P28ThresholdSlot? Slot, IReadOnlyList<byte> OriginalBytes, IReadOnlyList<byte> NewBytes);
public sealed record P28BasicCalibrationGroup(string Id, bool Requested, bool EffectivelyChanged,
    P28BasicVtecGroup? Vtec, P28CombinedLimiterGroup? Limiter, P28IdleTableGroup? Idle);
public sealed record P28BasicSuiteScope(string Id, string Scope);
public sealed record P28BasicCalibrationPlan(int FormatVersion, string Purpose, string ContractId, RomHash OriginalHash, int Size,
    string ProfileId, string ProfileDigest, string BindingDigest, IReadOnlyList<P28BasicCalibrationGroup> Groups,
    string LocationId, string LocationDigest, string LocationEvidenceIdentity, string LocationScope, string EditAudit,
    P28ComputedCompensation Compensation, byte ResidueA, byte ResidueB, byte ResidueC, RomHash IntermediateHash, RomHash OutputHash,
    IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp, IReadOnlyList<P28BasicSuiteScope> Suites, string ChecksumContractId,
    bool PhysicalRpmAvailable, string Readiness)
{
    public const int MaximumBytes = 131072;
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28BasicCalibrationPlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes) throw new InvalidDataException("Basic plan exceeds 128 KiB.");
        var p = P28RawEditJson.Parse<P28BasicCalibrationPlan>(json, OptionalProperty); P28BasicCalibrationEditor.Shape(p); return p;
    }
    // Explicit new-contract property nulls only. Old formats and all array elements stay strict.
    internal static bool OptionalProperty(Type type, string name) =>
        type == typeof(P28BasicCalibrationGroup) && name is "vtec" or "limiter" or "idle" || type == typeof(P28BasicVtecGroup) && name == "slot";
    public static P28BasicCalibrationPlan Load(string path) => Parse(P28IdleTablePlan.ReadJson(path, MaximumBytes));
}
public sealed class P28BasicCalibrationPreview
{
    private readonly string _plan;
    internal P28BasicCalibrationPreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, RomImage intermediate, RomImage output, P28BasicCalibrationPlan plan)
    { Original = original; Profile = profile; Binding = binding; Location = location; Intermediate = intermediate; Output = output; _plan = plan.ToJson(false); }
    internal RomImage Original { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal VerifiedCompensationLocation Location { get; }
    public RomImage Intermediate { get; }
    public RomImage Output { get; }
    public P28BasicCalibrationPlan Plan => P28BasicCalibrationPlan.Parse(_plan);
    internal (string Id, RomImage Image)[] Images => [("A", Original), ("B", Intermediate), ("C", Output)];
    internal void RequireImage(RomImage image)
    {
        if (!Images.Any(i => i.Image.Span.SequenceEqual(image.Span))) throw new InvalidDataException("Foreign image in typed basic composition.");
    }
}
public static class P28BasicCalibrationEditor
{
    public const string Purpose = "pc-only-basic-calibration-checksum-preserving-export";
    public const string ContractId = "p28-basic-calibration-composition-v1";
    public const string EditAudit = "Simultaneous source-listed numeric comparison, limiter reset/floor/targets and idle interpolation/downstream numeric flows preserve all pointer literals, axes, strides, stopping keys, bounds, instruction widths, vectors and encoded destinations under ordinary intact-state and valid-stack scope. Disjoint fields do not establish behavioral independence. Unchanged signed compensation location; no arbitrary-PC, corrupt-state or full-boot extension.";
    internal static P28BasicSuiteScope[] Scopes =>
    [
        new("VtecThresholdPrefix", "M1d strict raw-code prefix only; fresh isolated CPU per case; no G/F, P1 or M1k assumptions"),
        new("LimiterAdaptive", "M1p independent seeded native histories and source/threshold/request witnesses"),
        new("Idle", "M1s independent seeded source/target/error histories; no downstream regulator feedback"),
        new("Checksum", "M1f ordered full-ROM 512-invocation histories once per A/B/C/scratch"),
        new("VtecFullChain/P1/PhysicalOutput", "NotRun"), new("GUI r3", "paused/NotRun"), new("Hardware/FullBoot/JointEcuScheduler", "NotRun")
    ];
    internal static P28BasicCalibrationGroup[] Describe(RomImage original, P28BasicCalibrationSettings settings)
    {
        original.ValidateExactSize(32768);
        var old = original.Span.Slice(P28ThresholdLogic.BlockOffset, P28ThresholdLogic.BlockLength).ToArray(); var next = old.ToArray();
        var slot = settings.Vtec is null ? null : P28ThresholdLogic.ResolveSlot(settings.Vtec.Slot);
        if (slot is not null) next[slot.Offset - P28ThresholdLogic.BlockOffset] = (byte)settings.Vtec!.RawValue;
        var limiter = P28CombinedLimiterEditor.DescribeGroups(original, settings.Limiter); var idle = P28IdleTableEditor.Describe(original, settings.Idle);
        return [new("vtec", slot is not null, !old.SequenceEqual(next), new(slot, old, next), null, null),
            .. limiter.Select(g => new P28BasicCalibrationGroup(g.Id, g.Requested, g.EffectivelyChanged, null, g, null)),
            .. idle.Select(g => new P28BasicCalibrationGroup(g.Id == "base" ? "baseTable" : "lateTable", g.Requested, g.EffectivelyChanged, null, null, g))];
    }
    internal static P28CombinedLimiterGroup[] LimiterGroups(P28BasicCalibrationPlan p) => p.Groups.Skip(1).Take(3).Select(g => g.Limiter!).ToArray();
    internal static P28IdleTableGroup[] IdleGroups(P28BasicCalibrationPlan p) => p.Groups.Skip(4).Select(g => g.Idle!).ToArray();
    internal static P28BasicCalibrationSettings Settings(P28BasicCalibrationPlan p)
    {
        var v = p.Groups[0].Vtec!; var f = p.Groups[1].Limiter!;
        P28CombinedBankPair? Bank(int index) => p.Groups[index].Requested ? new(p.Groups[index].Limiter!.AdaptiveWords[0].NewWord, p.Groups[index].Limiter!.AdaptiveWords[1].NewWord) : null;
        int[]? Table(int index) => p.Groups[index].Requested ? p.Groups[index].Idle!.Cells.Select(c => c.NewValue).ToArray() : null;
        return new(v.Slot is null ? null : new(v.Slot.Id, v.NewBytes[v.Slot.Offset - P28ThresholdLogic.BlockOffset]),
            f.Requested ? new(f.FixedOperands[0].NewWord, f.FixedOperands[1].NewWord) : null, Bank(2), Bank(3), Table(4), Table(5));
    }
    internal static IEnumerable<P28RawByteDiff> FieldBytes(IReadOnlyList<P28BasicCalibrationGroup> groups)
    {
        var v = groups[0].Vtec!;
        if (v.Slot is { } s) yield return new(s.Offset, v.OriginalBytes[s.Offset - P28ThresholdLogic.BlockOffset], v.NewBytes[s.Offset - P28ThresholdLogic.BlockOffset]);
        foreach (var d in P28CombinedLimiterEditor.WordBytes(groups.Skip(1).Take(3).Select(g => g.Limiter!))) yield return d;
        foreach (var d in P28IdleTableEditor.CellBytes(groups.Skip(4).Select(g => g.Idle!))) yield return d;
    }
    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) Compose(RomImage original, P28BasicCalibrationSettings settings)
    {
        var groups = Describe(original, settings);
        var b = original.CreateModifiedCopy(FieldBytes(groups).Select(d => new BytePatch(d.Offset, [d.NewByte])));
        var old = original.Span[0x7FFF]; var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult;
        var compensation = new P28ComputedCompensation(0x7FFF, old, P28ChecksumPreservingEditor.ComputeCompensation(old, residue), P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(0x7FFF, [compensation.NewByte])]), compensation);
    }
    public static P28BasicCalibrationPreview Preview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        VerifiedCompensationLocation location, P28BasicCalibrationSettings settings)
    {
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28AdaptiveBaseEditor.MappingGuard(original); P28IdleContextsInspector.TableGuard(original);
        if (location.Offset != 0x7FFF) throw new InvalidDataException("Existing reviewed location required.");
        var (b, c, compensation) = Compose(original, settings); var diff = P28FixedLimiterEditor.Diff(original, c);
        var p = new P28BasicCalibrationPlan(1, Purpose, ContractId, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), Describe(original, settings),
            location.DefinitionId, location.DefinitionDigest, location.EvidenceIdentity, location.EvidenceScope, EditAudit, compensation,
            P28NativeChecksumArithmetic.Calculate(original).ComputedResult, P28NativeChecksumArithmetic.Calculate(b).ComputedResult,
            P28NativeChecksumArithmetic.Calculate(c).ComputedResult, b.Hash, c.Hash, diff, diff.Length == 0, Scopes,
            P28NativeChecksumArithmetic.Contract.Id, false, P28IdleTableEditor.Readiness);
        Shape(p); return new(original, profile, binding, location, b, c, p);
    }
    public static P28BasicCalibrationPreview Reproduce(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        VerifiedCompensationLocation location, P28BasicCalibrationPlan plan)
    {
        var frozen = P28BasicCalibrationPlan.Parse(plan.ToJson(false)); var expected = Preview(original, profile, binding, confirmed, location, Settings(frozen));
        if (frozen.ToJson(false) != expected.Plan.ToJson(false)) throw new InvalidDataException("Basic plan does not reproduce from exact original and code-owned contract.");
        return expected;
    }
    internal static void Shape(P28BasicCalibrationPlan p)
    {
        P28RawEditJson.ValidateObject(p, P28BasicCalibrationPlan.OptionalProperty);
        if (p.FormatVersion != 1 || p.Purpose != Purpose || p.ContractId != ContractId || p.Size != 32768 || p.EditAudit != EditAudit ||
            p.PhysicalRpmAvailable || p.Readiness != P28IdleTableEditor.Readiness || p.ResidueA != 0 || p.ResidueC != 0 ||
            p.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id || !P28LimiterValidator.Equal(p.Suites, Scopes) ||
            !p.Groups.Select(g => g.Id).SequenceEqual(new[] { "vtec", "fixed", "bank0", "bank1", "baseTable", "lateTable" }) ||
            p.Compensation.Offset != 0x7FFF || p.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId ||
            p.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(p.Compensation.OldByte, p.ResidueB)) throw new InvalidDataException("Unsupported basic plan metadata.");
        for (var i = 0; i < 6; i++)
        {
            var g = p.Groups[i];
            if ((g.Vtec is not null) != (i == 0) || (g.Limiter is not null) != (i is >= 1 and <= 3) || (g.Idle is not null) != (i >= 4) ||
                g.EffectivelyChanged && !g.Requested) throw new InvalidDataException("Invalid group union or selection.");
            if (g.Limiter is { } l && (l.Id != g.Id || l.Requested != g.Requested || l.EffectivelyChanged != g.EffectivelyChanged ||
                l.FixedOperands.Count != (i == 1 ? 2 : 0) || l.AdaptiveWords.Count != (i == 1 ? 0 : 2))) throw new InvalidDataException("Contradictory limiter selection.");
            if (g.Idle is { } t && (t.Id != P28IdleTableFields.TableId(i - 4) || t.Cells.Count != 7 || t.Requested != g.Requested || t.EffectivelyChanged != g.EffectivelyChanged))
                throw new InvalidDataException("Contradictory idle selection.");
        }
        var v = p.Groups[0].Vtec!;
        if (v.OriginalBytes.Count != 8 || v.NewBytes.Count != 8 || p.Groups[0].Requested != (v.Slot is not null) ||
            p.Groups[0].EffectivelyChanged != !v.OriginalBytes.SequenceEqual(v.NewBytes) ||
            v.Slot is { } slot && slot != P28ThresholdLogic.ResolveSlot(slot.Id)) throw new InvalidDataException("Invalid VTEC mapping or selection.");
        for (var i = 0; i < 8; i++)
            if (P28ThresholdLogic.BlockOffset + i != v.Slot?.Offset && v.OriginalBytes[i] != v.NewBytes[i]) throw new InvalidDataException("Multiple VTEC slots are forbidden.");
        _ = Settings(p);
        var diff = FieldBytes(p.Groups).Append(new(p.Compensation.Offset, p.Compensation.OldByte, p.Compensation.NewByte)).Where(d => d.OldByte != d.NewByte).OrderBy(d => d.Offset).ToArray();
        if (diff.Length > 42 || !p.ExpectedDiff.SequenceEqual(diff) || p.IsNoOp != (diff.Length == 0)) throw new InvalidDataException("Contradictory exact basic diff.");
    }
}
