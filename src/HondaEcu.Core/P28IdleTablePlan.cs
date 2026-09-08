using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed class P28IdleTableSettings
{
    public IReadOnlyList<int>? BaseTable { get; }
    public IReadOnlyList<int>? LateTable { get; }
    public P28IdleTableSettings(IReadOnlyList<int>? baseTable, IReadOnlyList<int>? lateTable)
    {
        static IReadOnlyList<int>? Freeze(IReadOnlyList<int>? values)
        {
            if (values is null) return null;
            if (values.Count != 7 || values.Any(v => v is < 1 or > 65534)) throw new ArgumentException("Each requested table requires exactly seven integer raw periods in 1..65534; exporter policy, not engine-safety limits.");
            return Array.AsReadOnly(values.ToArray());
        }
        BaseTable = Freeze(baseTable); LateTable = Freeze(lateTable);
    }
    public static P28IdleTableSettings Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 4096) throw new InvalidDataException("Idle settings exceed 4 KiB.");
        using var d = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 4 }); var r = d.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "baseTable", "lateTable");
        static int Integer(JsonElement v)
        {
            if (v.ValueKind != JsonValueKind.Number || !v.GetRawText().All(char.IsAsciiDigit) || !v.TryGetInt32(out var n)) throw new InvalidDataException("Unsigned decimal integers required; no rounding/clamp.");
            return n;
        }
        if (Integer(r.GetProperty("formatVersion")) != 1 || r.GetProperty("purpose").GetString() != "explicit-idle-table-values") throw new InvalidDataException("Unsupported idle settings.");
        int[]? Values(string name) => r.GetProperty(name).ValueKind == JsonValueKind.Null ? null : r.GetProperty(name).EnumerateArray().Select(Integer).ToArray();
        return new(Values("baseTable"), Values("lateTable"));
    }
}
public sealed record P28IdleTableCell(string FieldId, int Index, int AxisOffset, int Axis, int ValueOffset, int OldValue, int NewValue,
    IReadOnlyList<byte> OldBytes, IReadOnlyList<byte> NewBytes);
public sealed record P28IdleTableDomain(int CheckedInputs, int Minimum, int Maximum, int MaximumProduct, bool BoundsAndNodesVerified,
    IReadOnlyList<string> SegmentDirections);
public sealed record P28IdleTableGroup(string Id, bool Requested, bool EffectivelyChanged, IReadOnlyList<P28IdleTableCell> Cells,
    IReadOnlyList<P28IdleTableDomain> DomainChecks);
public sealed record P28IdleTablePlan(int FormatVersion, string Purpose, string ContractId, RomHash OriginalHash, int Size,
    string ProfileId, string ProfileDigest, string BindingDigest, IReadOnlyList<P28IdleTableGroup> Tables,
    string LocationId, string LocationDigest, string LocationEvidenceIdentity, string LocationScope, string EditAudit,
    P28ComputedCompensation Compensation, byte ResidueA, byte ResidueB, byte ResidueC, RomHash IntermediateHash, RomHash OutputHash,
    IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp, string Scope, string ChecksumContractId, bool PhysicalRpmAvailable, string Readiness)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28IdleTablePlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 65536) throw new InvalidDataException("Idle plan exceeds 64 KiB.");
        var p = P28RawEditJson.Parse<P28IdleTablePlan>(json); P28IdleTableEditor.Shape(p); return p;
    }
    public static P28IdleTablePlan Load(string path) => Parse(ReadJson(path, 65536));
    internal static string ReadJson(string path, int maximum)
    {
        using var stream = File.OpenRead(path);
        if (stream.Length > maximum) throw new InvalidDataException("Idle artifact exceeds its explicit byte bound.");
        var bytes = new byte[(int)stream.Length]; stream.ReadExactly(bytes);
        if (stream.ReadByte() != -1) throw new InvalidDataException("Idle artifact grew while reading.");
        return new UTF8Encoding(false, true).GetString(bytes).TrimStart('\uFEFF');
    }
}
public sealed class P28IdleTablePreview
{
    private readonly string _plan;
    internal P28IdleTablePreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, VerifiedCompensationLocation location,
        RomImage intermediate, RomImage output, P28IdleTablePlan plan)
    { Original = original; Profile = profile; Binding = binding; Location = location; Intermediate = intermediate; Output = output; _plan = plan.ToJson(false); }
    internal RomImage Original { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal VerifiedCompensationLocation Location { get; }
    public RomImage Intermediate { get; }
    public RomImage Output { get; }
    public P28IdleTablePlan Plan => P28IdleTablePlan.Parse(_plan);
}
public static class P28IdleTableEditor
{
    public const string Purpose = "pc-only-idle-table-checksum-preserving-export";
    public const string ContractId = "p28-idle-table-numeric-values-v1";
    public const string Scope = "One original; explicit base/late numeric period tables; unchanged axes, overrides and component peaks; target/error boundary only";
    public const string EditAudit = "Packed value bytes flow through byte exchanges to numeric interpolation, final025C and numeric downstream comparisons/gain lookups; not pointer literals, lengths, scanner keys or encoded destinations. All axes, including68DA/68F2, strides, zero barriers, vector/code and valid-stack conditions remain original. Existing signed compensation scope applies under ordinary intact-state/source-listed paths; bounded slice non-reading is supplemental, not global proof.";
    public const string Readiness = "PcInspectionOnly / NotFlashReady";
    internal static P28IdleTableGroup[] Describe(RomImage original, P28IdleTableSettings settings)
    {
        P28IdleContextsInspector.TableGuard(original); var groups = new List<P28IdleTableGroup>();
        for (var table = 0; table < 2; table++)
        {
            var values = table == 0 ? settings.BaseTable : settings.LateTable;
            var cells = Enumerable.Range(0, 7).Select(i =>
            {
                var offset = P28IdleTableFields.ValueOffset(table, i); var old = P28LimiterInspector.Word(original.Span, offset); var value = values?[i] ?? old;
                return new P28IdleTableCell(P28IdleTableFields.FieldId(table, i), i, offset - 1, original.Span[offset - 1], offset,
                    old, value, P28FixedLimiterEditor.Encode(old), P28FixedLimiterEditor.Encode(value));
            }).ToArray();
            groups.Add(new(P28IdleTableFields.TableId(table), values is not null, cells.Any(c => c.OldValue != c.NewValue), cells,
                values is null ? [] : [CheckDomain(cells)]));
        }
        return groups.ToArray();
    }
    // Wide-integer arithmetic audit, separate from native producer reachability and the stateful M1r model.
    internal static P28IdleTableDomain CheckDomain(IReadOnlyList<P28IdleTableCell> cells)
    {
        if (cells.Count != 7 || cells[0].Axis != 255 || cells[6].Axis != 0 || cells.Any(c => c.NewValue is < 1 or > 65534) ||
            cells.Zip(cells.Skip(1)).Any(p => p.First.Axis <= p.Second.Axis)) throw new ArgumentException("Invalid descending axes or exporter raw policy.");
        var minimum = 65535; var maximum = 0; var maxProduct = 0;
        for (var x = 0; x <= 255; x++)
        {
            var index = 0; while (index < 5 && x < cells[index + 1].Axis) index++;
            var upper = cells[index]; var lower = cells[index + 1]; var distance = x - lower.Axis; var denominator = upper.Axis - lower.Axis;
            var product = (long)Math.Abs(upper.NewValue - lower.NewValue) * distance; var delta = product / denominator;
            var value = lower.NewValue + (upper.NewValue < lower.NewValue ? -delta : delta);
            if (distance < 0 || distance > denominator || denominator <= 0 || product > uint.MaxValue || delta > 65535 ||
                value < Math.Min(upper.NewValue, lower.NewValue) || value > Math.Max(upper.NewValue, lower.NewValue) ||
                value is < 1 or > 65534 || cells.Any(c => c.Axis == x && c.NewValue != value) ||
                lower.ValueOffset + 1 > cells[6].ValueOffset + 1) throw new InvalidDataException("Full table arithmetic domain failed.");
            minimum = Math.Min(minimum, (int)value); maximum = Math.Max(maximum, (int)value); maxProduct = Math.Max(maxProduct, (int)product);
        }
        return new(256, minimum, maximum, maxProduct, true, cells.Zip(cells.Skip(1)).Select(p => p.First.NewValue == p.Second.NewValue ? "Plateau" : p.First.NewValue < p.Second.NewValue ? "RisesWithDescendingAxis" : "FallsWithDescendingAxis").ToArray());
    }
    internal static P28IdleTableSettings Settings(P28IdleTablePlan p) => new(p.Tables[0].Requested ? p.Tables[0].Cells.Select(c => c.NewValue).ToArray() : null,
        p.Tables[1].Requested ? p.Tables[1].Cells.Select(c => c.NewValue).ToArray() : null);
    internal static IEnumerable<P28RawByteDiff> CellBytes(IEnumerable<P28IdleTableGroup> tables) => tables.SelectMany(t => t.Cells)
        .SelectMany(c => Enumerable.Range(0, 2).Select(i => new P28RawByteDiff(c.ValueOffset + i, c.OldBytes[i], c.NewBytes[i])));
    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) Compose(RomImage original, P28IdleTableSettings settings)
    {
        var groups = Describe(original, settings);
        var b = original.CreateModifiedCopy(CellBytes(groups.Where(g => g.Requested)).Select(d => new BytePatch(d.Offset, [d.NewByte])));
        var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult; var old = original.Span[0x7FFF];
        var compensation = new P28ComputedCompensation(0x7FFF, old, P28ChecksumPreservingEditor.ComputeCompensation(old, residue), P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(0x7FFF, [compensation.NewByte])]), compensation);
    }
    public static P28IdleTablePreview Preview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        VerifiedCompensationLocation location, P28IdleTableSettings settings)
    {
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28IdleContextsInspector.TableGuard(original);
        if (location.Offset != 0x7FFF) throw new InvalidDataException("Existing reviewed location scope required.");
        var (b, c, compensation) = Compose(original, settings); var diff = P28FixedLimiterEditor.Diff(original, c);
        var p = new P28IdleTablePlan(1, Purpose, ContractId, original.Hash, original.Size, profile.Id, P28VtecInspector.ComputeProfileDigest(profile),
            P28RawThresholdEditor.ComputeBindingDigest(binding), Describe(original, settings), location.DefinitionId, location.DefinitionDigest,
            location.EvidenceIdentity, location.EvidenceScope, EditAudit, compensation, P28NativeChecksumArithmetic.Calculate(original).ComputedResult,
            P28NativeChecksumArithmetic.Calculate(b).ComputedResult, P28NativeChecksumArithmetic.Calculate(c).ComputedResult, b.Hash, c.Hash,
            diff, diff.Length == 0, Scope, P28NativeChecksumArithmetic.Contract.Id, false, Readiness);
        Shape(p); return new(original, profile, binding, location, b, c, p);
    }
    public static P28IdleTablePreview Reproduce(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        VerifiedCompensationLocation location, P28IdleTablePlan plan)
    {
        var frozen = P28IdleTablePlan.Parse(plan.ToJson(false)); var expected = Preview(original, profile, binding, confirmed, location, Settings(frozen));
        if (frozen.ToJson(false) != expected.Plan.ToJson(false)) throw new InvalidDataException("Idle plan does not reproduce from exact original and code-owned contract.");
        return expected;
    }
    internal static void Shape(P28IdleTablePlan p)
    {
        P28RawEditJson.ValidateObject(p);
        if (p.FormatVersion != 1 || p.Purpose != Purpose || p.ContractId != ContractId || p.Size != 32768 || p.Scope != Scope || p.EditAudit != EditAudit ||
            p.Readiness != Readiness || p.PhysicalRpmAvailable || p.ResidueA != 0 || p.ResidueC != 0 || p.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id ||
            p.Tables.Count != 2 || p.Compensation.Offset != 0x7FFF || p.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId ||
            p.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(p.Compensation.OldByte, p.ResidueB)) throw new InvalidDataException("Unsupported idle plan metadata.");
        for (var t = 0; t < 2; t++)
        {
            var g = p.Tables[t];
            if (g.Id != P28IdleTableFields.TableId(t) || g.Cells.Count != 7 || g.DomainChecks.Count != (g.Requested ? 1 : 0)) throw new InvalidDataException("Invalid table selection.");
            for (var i = 0; i < 7; i++)
            {
                var c = g.Cells[i];
                if (c.Index != i || c.FieldId != P28IdleTableFields.FieldId(t, i) || c.ValueOffset != P28IdleTableFields.ValueOffset(t, i) ||
                    c.AxisOffset != P28IdleTableFields.AxisOffset(t, i) || c.Axis is < 0 or > 255 || c.OldValue is < 0 or > 65535 || c.NewValue is < 0 or > 65535 ||
                    !c.OldBytes.SequenceEqual(P28FixedLimiterEditor.Encode(c.OldValue)) || !c.NewBytes.SequenceEqual(P28FixedLimiterEditor.Encode(c.NewValue))) throw new InvalidDataException("Invalid code-owned idle cell.");
            }
            if (g.EffectivelyChanged != g.Cells.Any(c => c.OldValue != c.NewValue) || !g.Requested && g.EffectivelyChanged ||
                g.Requested && !P28LimiterValidator.Equal(g.DomainChecks[0], CheckDomain(g.Cells))) throw new InvalidDataException("Contradictory idle request/domain.");
        }
        _ = Settings(p);
        var diff = CellBytes(p.Tables).Append(new(p.Compensation.Offset, p.Compensation.OldByte, p.Compensation.NewByte)).Where(d => d.OldByte != d.NewByte).OrderBy(d => d.Offset).ToArray();
        if (diff.Length > 29 || !p.ExpectedDiff.SequenceEqual(diff) || p.IsNoOp != (diff.Length == 0)) throw new InvalidDataException("Idle exact diff contradiction.");
        foreach (var h in new[] { p.OriginalHash, p.IntermediateHash, p.OutputHash })
            if (h.Sha256.Length != 64 || !h.Sha256.All(Uri.IsHexDigit) || h.Crc32.Length != 8 || !h.Crc32.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed image identity.");
        foreach (var d in new[] { p.ProfileDigest, p.BindingDigest, p.LocationDigest }) if (d.Length != 64 || !d.All(Uri.IsHexDigit)) throw new InvalidDataException("Malformed input identity.");
    }
}
