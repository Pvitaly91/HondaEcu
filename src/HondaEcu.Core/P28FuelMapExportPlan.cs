using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28FuelMapCellSetting(int Row, int Column, int RawValue);

public sealed class P28FuelMapExportSettings
{
    public IReadOnlyList<P28FuelMapCellSetting>? Map0 { get; }
    public IReadOnlyList<P28FuelMapCellSetting>? Map1 { get; }

    public P28FuelMapExportSettings(IReadOnlyList<P28FuelMapCellSetting>? map0, IReadOnlyList<P28FuelMapCellSetting>? map1)
    {
        Map0 = Freeze(map0, "map_0");
        Map1 = Freeze(map1, "map_1");
        if ((Map0?.Count ?? 0) + (Map1?.Count ?? 0) > 400)
            throw new ArgumentException("At most 400 explicit fuel-map cells may be requested.");
    }

    private static IReadOnlyList<P28FuelMapCellSetting>? Freeze(IReadOnlyList<P28FuelMapCellSetting>? values, string mapId)
    {
        if (values is null) return null;
        if (values.Count > P28FuelMapContract.CellCount) throw new ArgumentException($"{mapId} has more than 200 cells.");
        foreach (var value in values)
        {
            _ = P28FuelMapContract.CellOffset(mapId, value.Row, value.Column);
            if (value.RawValue is < 0 or > 255) throw new ArgumentException("Fuel-map values must be unsigned bytes; no rounding, clamping or force mode.");
        }
        if (values.GroupBy(v => (v.Row, v.Column)).Any(group => group.Count() != 1))
            throw new ArgumentException($"Duplicate {mapId} cell coordinates are forbidden.");
        return Array.AsReadOnly(values.OrderBy(v => v.Row).ThenBy(v => v.Column).ToArray());
    }

    public static P28FuelMapExportSettings Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 65536) throw new InvalidDataException("Fuel-map settings exceed 64 KiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
        var root = document.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "map_0", "map_1");
        static int Integer(JsonElement value)
        {
            if (value.ValueKind != JsonValueKind.Number || !value.GetRawText().All(char.IsAsciiDigit) || !value.TryGetInt32(out var result))
                throw new InvalidDataException("Unsigned decimal integers are required; percentages, strings, rounding and clamping are forbidden.");
            return result;
        }
        if (Integer(root.GetProperty("formatVersion")) != 1 || root.GetProperty("purpose").GetString() != "explicit-fuel-map-cell-values")
            throw new InvalidDataException("Unsupported fuel-map settings version or purpose.");
        static P28FuelMapCellSetting[]? Cells(JsonElement value)
        {
            if (value.ValueKind == JsonValueKind.Null) return null;
            if (value.ValueKind != JsonValueKind.Array) throw new InvalidDataException("Each map must be null or an explicit array.");
            return value.EnumerateArray().Select(cell =>
            {
                P28LimiterScenario.Shape(cell, "row", "column", "rawValue");
                return new P28FuelMapCellSetting(Integer(cell.GetProperty("row")), Integer(cell.GetProperty("column")), Integer(cell.GetProperty("rawValue")));
            }).ToArray();
        }
        try { return new(Cells(root.GetProperty("map_0")), Cells(root.GetProperty("map_1"))); }
        catch (ArgumentException exception) { throw new InvalidDataException("Invalid fuel-map cell selection.", exception); }
    }
}

public sealed record P28FuelMapExportCell(string MapId, int Row, int Column, int Offset, int OldRawValue, int NewRawValue,
    int MultiplierOffset, int Multiplier, int OldScaledValue, int NewScaledValue);
public sealed record P28FuelMapDomainAudit(string MapId, int CheckedInputPairs, int OldMinimum, int OldMaximum,
    int NewMinimum, int NewMaximum, int MaximumScaledCell, long MaximumInterpolationProduct,
    int IncreasedResults, int DecreasedResults, int EqualResults, int ChangedResults,
    bool SequentialFixedPointVerified, bool WideIntermediatesVerified, bool Sentinel256Verified);
public sealed record P28FuelMapExportGroup(string MapId, bool Requested, bool EffectivelyChanged,
    int RequestedCellCount, int ChangedCellCount, IReadOnlyList<P28FuelMapExportCell> Cells, P28FuelMapDomainAudit DomainAudit);
public sealed record P28FuelMapImmutableRange(string Id, int Start, int EndInclusive, string Sha256);

public sealed record P28FuelMapExportPlan(int FormatVersion, string Purpose, string ContractId, RomHash OriginalHash, int Size,
    string ProfileId, string ProfileDigest, string BindingDigest, IReadOnlyList<P28FuelMapExportGroup> Maps,
    IReadOnlyList<P28FuelMapImmutableRange> ImmutableRanges, string LocationId, string LocationDigest,
    string LocationEvidenceIdentity, string LocationScope, string EditAudit, P28ComputedCompensation Compensation,
    byte ResidueA, byte ResidueB, byte ResidueC, RomHash IntermediateHash, RomHash OutputHash,
    IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp, string Scope, string ChecksumContractId,
    bool PhysicalUnitsAvailable, string Readiness)
{
    public const int MaximumBytes = 1_048_576;
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28FuelMapExportPlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes) throw new InvalidDataException("Fuel-map plan exceeds 1 MiB.");
        var plan = P28RawEditJson.Parse<P28FuelMapExportPlan>(json);
        P28FuelMapExportEditor.Shape(plan);
        return plan;
    }
    public static P28FuelMapExportPlan Load(string path) => Parse(P28IdleTablePlan.ReadJson(path, MaximumBytes));
}

public sealed class P28FuelMapExportPreview
{
    private readonly string _plan;
    internal P28FuelMapExportPreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, RomImage intermediate, RomImage output, P28FuelMapExportPlan plan)
    {
        Original = original; Profile = profile; Binding = binding; Location = location;
        Intermediate = intermediate; Output = output; _plan = plan.ToJson(false);
    }
    internal RomImage Original { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal VerifiedCompensationLocation Location { get; }
    public RomImage Intermediate { get; }
    public RomImage Output { get; }
    public P28FuelMapExportPlan Plan => P28FuelMapExportPlan.Parse(_plan);
}

public static class P28FuelMapExportEditor
{
    public const string Purpose = "pc-only-fuel-map-checksum-preserving-export";
    public const string ContractId = "p28-fuel-map-numeric-cells-v1";
    public const string Scope = "Exact P28-304 original; explicit row-major map_0/map_1 unsigned numeric cells; one reviewed checksum compensation byte; all other bytes immutable";
    public const string EditAudit = "Actual source listing establishes 20x10 byte cells read as numeric operands by the native lookup at 59E4..5A45 through callers 130C/1323/1340; entries are not pointers, axes, lengths, strides, selector/gate bytes, metadata multipliers, code or encoded destinations. Existing reviewed compensation applicability remains limited to its signed ordinary intact-state/source-listed scope.";
    public const string Readiness = "PcInspectionOnly / NotFlashReady";

    internal static P28FuelMapExportGroup[] Describe(RomImage original, P28FuelMapExportSettings settings, RomImage? intermediate = null)
    {
        P28FuelMapInspector.LayoutGuard(original);
        intermediate ??= ComposeIntermediate(original, settings);
        return new[] { (Id: "map_0", Values: settings.Map0), (Id: "map_1", Values: settings.Map1) }.Select(item =>
        {
            var map = P28FuelMapContract.Map(item.Id);
            var cells = (item.Values ?? []).Select(value =>
            {
                var offset = P28FuelMapContract.CellOffset(item.Id, value.Row, value.Column);
                var multiplierOffset = P28FuelMapContract.MetadataOffset(item.Id, value.Column);
                var multiplier = original.Span[multiplierOffset];
                return new P28FuelMapExportCell(item.Id, value.Row, value.Column, offset, original.Span[offset], value.RawValue,
                    multiplierOffset, multiplier, original.Span[offset] * multiplier, value.RawValue * multiplier);
            }).ToArray();
            return new P28FuelMapExportGroup(item.Id, item.Values is not null, cells.Any(c => c.OldRawValue != c.NewRawValue),
                cells.Length, cells.Count(c => c.OldRawValue != c.NewRawValue), cells, AuditDomain(original, intermediate, map));
        }).ToArray();
    }

    private static RomImage ComposeIntermediate(RomImage original, P28FuelMapExportSettings settings)
    {
        var patches = new List<BytePatch>();
        foreach (var item in new[] { (Id: "map_0", Values: settings.Map0), (Id: "map_1", Values: settings.Map1) })
            foreach (var value in item.Values ?? [])
                patches.Add(new(P28FuelMapContract.CellOffset(item.Id, value.Row, value.Column), [(byte)value.RawValue]));
        return original.CreateModifiedCopy(patches);
    }

    internal static P28FuelMapDomainAudit AuditDomain(RomImage original, RomImage next, P28FuelMapContractRow map)
    {
        var oldMin = int.MaxValue; var oldMax = int.MinValue; var newMin = int.MaxValue; var newMax = int.MinValue;
        var maxScaled = 0; long maxProduct = 0; var increase = 0; var decrease = 0; var equal = 0;
        for (var rpm = 0; rpm <= 255; rpm++)
            for (var load = 0; load <= 255; load++)
            {
                var a = P28FuelMapModel.ProjectNumeric(original.Span, map.Id, rpm, load);
                var b = P28FuelMapModel.ProjectNumeric(next.Span, map.Id, rpm, load);
                oldMin = Math.Min(oldMin, a.LookupResult); oldMax = Math.Max(oldMax, a.LookupResult);
                newMin = Math.Min(newMin, b.LookupResult); newMax = Math.Max(newMax, b.LookupResult);
                maxScaled = Math.Max(maxScaled, new[] { a.ScaledTopLeft, a.ScaledTopRight, a.ScaledBottomLeft, a.ScaledBottomRight,
                    b.ScaledTopLeft, b.ScaledTopRight, b.ScaledBottomLeft, b.ScaledBottomRight }.Max());
                maxProduct = Math.Max(maxProduct, new[] { a.TopInterpolationProduct, a.BottomInterpolationProduct, a.FinalInterpolationProduct,
                    b.TopInterpolationProduct, b.BottomInterpolationProduct, b.FinalInterpolationProduct }.Max());
                if (b.LookupResult > a.LookupResult) increase++; else if (b.LookupResult < a.LookupResult) decrease++; else equal++;
                static void Bounds(P28FuelNumericProjection p)
                {
                    var low = new[] { p.ScaledTopLeft, p.ScaledTopRight, p.ScaledBottomLeft, p.ScaledBottomRight }.Min();
                    var high = new[] { p.ScaledTopLeft, p.ScaledTopRight, p.ScaledBottomLeft, p.ScaledBottomRight }.Max();
                    if (p.LookupResult < low || p.LookupResult > high) throw new InvalidDataException("Sequential fuel-map interpolation escaped its four scaled cells.");
                }
                Bounds(a); Bounds(b);
            }
        var sentinel = original.Span[P28FuelMapContract.LoadAxisOrigin + 9] == 0 &&
            original.Span[(map.Id == "map_0" ? P28FuelMapContract.Map0RpmAxisOrigin : P28FuelMapContract.Map1RpmAxisOrigin) + 19] == 0;
        if (!sentinel || maxScaled > 65025 || maxProduct > (long)65025 * ushort.MaxValue || increase + decrease + equal != 65536)
            throw new InvalidDataException("Fuel-map full finite arithmetic audit failed.");
        return new(map.Id, 65536, oldMin, oldMax, newMin, newMax, maxScaled, maxProduct, increase, decrease, equal,
            increase + decrease, true, true, true);
    }

    internal static P28FuelMapImmutableRange[] Immutable(RomImage image)
    {
        var ranges = new[]
        {
            ("vectors", 0x0000, 0x002F), ("selector", 0x0127, 0x0127), ("checksum-code", 0x2B70, 0x2BB6),
            ("consumer-gate", 0x60E5, 0x60E5), ("load-axis", 0x7000, 0x7009), ("candidate-700A", 0x700A, 0x700A),
            ("rpm-axes", 0x7014, 0x703B), ("map0-multipliers", 0x7118, 0x7121), ("map1-multipliers", 0x71EA, 0x71F3)
        };
        return ranges.Select(range => new P28FuelMapImmutableRange(range.Item1, range.Item2, range.Item3,
            HashUtilities.Sha256(image.Span[range.Item2..(range.Item3 + 1)]))).ToArray();
    }

    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) Compose(RomImage original, P28FuelMapExportSettings settings)
    {
        var b = ComposeIntermediate(original, settings);
        var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult;
        var oldByte = original.Span[0x7FFF];
        var compensation = new P28ComputedCompensation(0x7FFF, oldByte,
            P28ChecksumPreservingEditor.ComputeCompensation(oldByte, residue), P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(0x7FFF, [compensation.NewByte])]), compensation);
    }

    public static P28FuelMapExportPreview Preview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28FuelMapExportSettings settings)
    {
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28FuelMapInspector.LayoutGuard(original);
        if (location.Offset != 0x7FFF) throw new InvalidDataException("Existing reviewed compensation location 0x7FFF is required.");
        var aGuard = P28ChecksumCodeGuard.Assess(original);
        if (!aGuard.ContractRecognized || !aGuard.GateEnabled || P28NativeChecksumArithmetic.Calculate(original).ComputedResult != 0)
            throw new InvalidDataException("Original native checksum code/gate/residue is not admissible.");
        var (b, c, compensation) = Compose(original, settings);
        var bGuard = P28ChecksumCodeGuard.Assess(b); var cGuard = P28ChecksumCodeGuard.Assess(c);
        if (!bGuard.ContractRecognized || !bGuard.GateEnabled || !cGuard.ContractRecognized || !cGuard.GateEnabled ||
            P28NativeChecksumArithmetic.Calculate(c).ComputedResult != 0)
            throw new InvalidDataException("Composed images changed checksum code/gate or failed compensation.");
        var groups = Describe(original, settings, b); var immutable = Immutable(original);
        foreach (var range in immutable)
            foreach (var image in new[] { b, c })
                if (range.Sha256 != HashUtilities.Sha256(image.Span[range.Start..(range.EndInclusive + 1)]))
                    throw new InvalidDataException($"Immutable range {range.Id} changed.");
        var diff = P28FixedLimiterEditor.Diff(original, c);
        var plan = new P28FuelMapExportPlan(1, Purpose, ContractId, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), groups, immutable,
            location.DefinitionId, location.DefinitionDigest, location.EvidenceIdentity, location.EvidenceScope, EditAudit, compensation,
            0, P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash, diff, diff.Length == 0, Scope,
            P28NativeChecksumArithmetic.Contract.Id, false, Readiness);
        Shape(plan);
        return new(original, profile, binding, location, b, c, plan);
    }

    internal static P28FuelMapExportSettings Settings(P28FuelMapExportPlan plan)
    {
        var map0 = plan.Maps[0]; var map1 = plan.Maps[1];
        return new(map0.Requested ? map0.Cells.Select(c => new P28FuelMapCellSetting(c.Row, c.Column, c.NewRawValue)).ToArray() : null,
            map1.Requested ? map1.Cells.Select(c => new P28FuelMapCellSetting(c.Row, c.Column, c.NewRawValue)).ToArray() : null);
    }

    public static P28FuelMapExportPreview Reproduce(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, VerifiedCompensationLocation location, P28FuelMapExportPlan plan)
    {
        var frozen = P28FuelMapExportPlan.Parse(plan.ToJson(false));
        var expected = Preview(original, profile, binding, confirmed, location, Settings(frozen));
        if (frozen.ToJson(false) != expected.Plan.ToJson(false))
            throw new InvalidDataException("Fuel-map plan does not reproduce from the exact original and code-owned contract.");
        return expected;
    }

    internal static void Shape(P28FuelMapExportPlan plan)
    {
        P28RawEditJson.ValidateObject(plan);
        if (plan.FormatVersion != 1 || plan.Purpose != Purpose || plan.ContractId != ContractId || plan.Size != 32768 ||
            plan.Scope != Scope || plan.EditAudit != EditAudit || plan.Readiness != Readiness || plan.PhysicalUnitsAvailable ||
            plan.ResidueA != 0 || plan.ResidueC != 0 || plan.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id ||
            plan.Maps.Count != 2 || plan.Maps[0].MapId != "map_0" || plan.Maps[1].MapId != "map_1" ||
            plan.Compensation.Offset != 0x7FFF || plan.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId ||
            plan.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(plan.Compensation.OldByte, plan.ResidueB))
            throw new InvalidDataException("Unsupported fuel-map plan metadata.");
        foreach (var group in plan.Maps)
        {
            if (group.RequestedCellCount != group.Cells.Count || group.ChangedCellCount != group.Cells.Count(c => c.OldRawValue != c.NewRawValue) ||
                group.EffectivelyChanged != (group.ChangedCellCount != 0) || !group.Requested && group.Cells.Count != 0 || group.Cells.Count > 200 ||
                !group.Cells.SequenceEqual(group.Cells.OrderBy(c => c.Row).ThenBy(c => c.Column)) ||
                group.Cells.GroupBy(c => (c.Row, c.Column)).Any(g => g.Count() != 1))
                throw new InvalidDataException("Contradictory fuel-map group.");
            foreach (var cell in group.Cells)
                if (cell.MapId != group.MapId || cell.Offset != P28FuelMapContract.CellOffset(group.MapId, cell.Row, cell.Column) ||
                    cell.MultiplierOffset != P28FuelMapContract.MetadataOffset(group.MapId, cell.Column) ||
                    cell.OldRawValue is < 0 or > 255 || cell.NewRawValue is < 0 or > 255 || cell.Multiplier is < 0 or > 255 ||
                    cell.OldScaledValue != cell.OldRawValue * cell.Multiplier || cell.NewScaledValue != cell.NewRawValue * cell.Multiplier)
                    throw new InvalidDataException("Invalid code-owned fuel-map cell.");
            var audit = group.DomainAudit;
            if (audit.MapId != group.MapId || audit.CheckedInputPairs != 65536 ||
                audit.IncreasedResults + audit.DecreasedResults + audit.EqualResults != 65536 ||
                audit.ChangedResults != audit.IncreasedResults + audit.DecreasedResults || audit.MaximumScaledCell is < 0 or > 65025 ||
                audit.MaximumInterpolationProduct is < 0 or > (long)65025 * ushort.MaxValue ||
                !audit.SequentialFixedPointVerified || !audit.WideIntermediatesVerified || !audit.Sentinel256Verified)
                throw new InvalidDataException("Invalid full-domain fuel-map audit.");
        }
        _ = Settings(plan);
        var expected = plan.Maps.SelectMany(group => group.Cells)
            .Select(cell => new P28RawByteDiff(cell.Offset, (byte)cell.OldRawValue, (byte)cell.NewRawValue))
            .Append(new(plan.Compensation.Offset, plan.Compensation.OldByte, plan.Compensation.NewByte))
            .Where(diff => diff.OldByte != diff.NewByte).OrderBy(diff => diff.Offset).ToArray();
        if (expected.Length > 401 || !plan.ExpectedDiff.SequenceEqual(expected) || plan.IsNoOp != (expected.Length == 0) ||
            plan.ImmutableRanges.Count != 9 || plan.ImmutableRanges.Any(r => r.Start < 0 || r.EndInclusive < r.Start || r.EndInclusive >= 32768 ||
                r.Sha256.Length != 64 || !r.Sha256.All(Uri.IsHexDigit)))
            throw new InvalidDataException("Fuel-map exact diff or immutable ranges are contradictory.");
    }
}
