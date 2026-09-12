using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28IgnitionMapCellSetting(int Row, int Column, int RawValue);

public sealed class P28IgnitionMapExportSettings
{
    public IReadOnlyList<P28IgnitionMapCellSetting>? IgnitionMap0 { get; }
    public IReadOnlyList<P28IgnitionMapCellSetting>? IgnitionMap1 { get; }

    public P28IgnitionMapExportSettings(IReadOnlyList<P28IgnitionMapCellSetting>? map0,
        IReadOnlyList<P28IgnitionMapCellSetting>? map1)
    {
        IgnitionMap0 = Freeze(map0, "ignition_map_0");
        IgnitionMap1 = Freeze(map1, "ignition_map_1");
        if ((IgnitionMap0?.Count ?? 0) + (IgnitionMap1?.Count ?? 0) > 400)
            throw new ArgumentException("At most 400 explicit ignition-map cells may be requested.");
    }

    private static IReadOnlyList<P28IgnitionMapCellSetting>? Freeze(
        IReadOnlyList<P28IgnitionMapCellSetting>? values, string mapId)
    {
        if (values is null) return null;
        if (values.Count > P28IgnitionMapContract.CellCount)
            throw new ArgumentException($"{mapId} has more than 200 cells.");
        foreach (var value in values)
        {
            _ = P28IgnitionMapContract.CellOffset(mapId, value.Row, value.Column);
            if (value.RawValue is < 0 or > 255)
                throw new ArgumentException("Ignition-map values must be unsigned bytes; no conversion, rounding or clamping.");
        }
        if (values.GroupBy(value => (value.Row, value.Column)).Any(group => group.Count() != 1))
            throw new ArgumentException($"Duplicate {mapId} cell coordinates are forbidden.");
        return Array.AsReadOnly(values.OrderBy(value => value.Row).ThenBy(value => value.Column).ToArray());
    }

    public static P28IgnitionMapExportSettings Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 65536) throw new InvalidDataException("Ignition-map settings exceed 64 KiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
        var root = document.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "ignition_map_0", "ignition_map_1");
        static int Integer(JsonElement value)
        {
            if (value.ValueKind != JsonValueKind.Number || !value.GetRawText().All(char.IsAsciiDigit) || !value.TryGetInt32(out var result))
                throw new InvalidDataException("Unsigned decimal integers are required; strings, units, rounding and clamping are forbidden.");
            return result;
        }
        if (Integer(root.GetProperty("formatVersion")) != 1 ||
            root.GetProperty("purpose").GetString() != "explicit-ignition-map-cell-values")
            throw new InvalidDataException("Unsupported ignition-map settings version or purpose.");
        static P28IgnitionMapCellSetting[]? Cells(JsonElement value)
        {
            if (value.ValueKind == JsonValueKind.Null) return null;
            if (value.ValueKind != JsonValueKind.Array) throw new InvalidDataException("Each ignition map must be null or an explicit array.");
            return value.EnumerateArray().Select(cell =>
            {
                P28LimiterScenario.Shape(cell, "row", "column", "rawValue");
                return new P28IgnitionMapCellSetting(Integer(cell.GetProperty("row")),
                    Integer(cell.GetProperty("column")), Integer(cell.GetProperty("rawValue")));
            }).ToArray();
        }
        try { return new(Cells(root.GetProperty("ignition_map_0")), Cells(root.GetProperty("ignition_map_1"))); }
        catch (ArgumentException exception) { throw new InvalidDataException("Invalid ignition-map cell selection.", exception); }
    }
}

public sealed record P28IgnitionMapExportCell(string MapId, int Row, int Column, int Offset,
    int OldRawValue, int NewRawValue);
public sealed record P28IgnitionMapDomainAudit(string MapId, int CheckedInputPairs, int OldMinimum, int OldMaximum,
    int NewMinimum, int NewMaximum, long MaximumInterpolationProduct, int IncreasedResults, int DecreasedResults,
    int EqualResults, int ChangedResults, bool SequentialFixedPointVerified, bool WideIntermediatesVerified,
    bool Sentinel256Verified);
public sealed record P28IgnitionConsumerDomainAudit(int CheckedInputPairs, int BypassPairs, int ScalingPairs,
    long MaximumProduct, int MinimumOutput, int MaximumOutput, bool ZeroFactorBypassVerified,
    bool UnsignedHighByteVerified, bool FullByteDomainVerified);
public sealed record P28IgnitionMapExportGroup(string MapId, bool Requested, bool EffectivelyChanged,
    int RequestedCellCount, int ChangedCellCount, IReadOnlyList<P28IgnitionMapExportCell> Cells,
    P28IgnitionMapDomainAudit DomainAudit);
public sealed record P28IgnitionMapImmutableRange(string Id, int Start, int EndInclusive, string Sha256);

public sealed record P28IgnitionMapExportPlan(int FormatVersion, string Purpose, string ContractId,
    RomHash OriginalHash, int Size, string ProfileId, string ProfileDigest, string BindingDigest,
    IReadOnlyList<P28IgnitionMapExportGroup> Maps, P28IgnitionConsumerDomainAudit ConsumerAudit,
    IReadOnlyList<P28IgnitionMapImmutableRange> ImmutableRanges, string LocationId, string LocationDigest,
    string LocationEvidenceIdentity, string LocationScope, string EditAudit, P28ComputedCompensation Compensation,
    byte ResidueA, byte ResidueB, byte ResidueC, RomHash IntermediateHash, RomHash OutputHash,
    IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp, string Scope, string ChecksumContractId,
    bool PhysicalUnitsAvailable, string Readiness)
{
    public const int MaximumBytes = 1_048_576;
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28IgnitionMapExportPlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes) throw new InvalidDataException("Ignition-map plan exceeds 1 MiB.");
        var plan = P28RawEditJson.Parse<P28IgnitionMapExportPlan>(json);
        P28IgnitionMapExportEditor.Shape(plan);
        return plan;
    }
    public static P28IgnitionMapExportPlan Load(string path) => Parse(P28IdleTablePlan.ReadJson(path, MaximumBytes));
}

public sealed class P28IgnitionMapExportPreview
{
    private readonly string _plan;
    internal P28IgnitionMapExportPreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, RomImage intermediate, RomImage output, P28IgnitionMapExportPlan plan)
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
    public P28IgnitionMapExportPlan Plan => P28IgnitionMapExportPlan.Parse(_plan);
}

public static class P28IgnitionMapExportEditor
{
    public const string Purpose = "pc-only-ignition-map-checksum-preserving-export";
    public const string ContractId = "p28-primary-ignition-map-numeric-cells-v1";
    public const string Scope = "Exact P28-304 original; explicit row-major ignition_map_0/ignition_map_1 unsigned numeric cells; one reviewed checksum compensation byte; all other bytes immutable";
    public const string EditAudit = "Exact M2c source audit establishes the two 20x10 primary regions as direct unsigned numeric lookup operands at 59E4..5A45 through 0B64..0BD3. They are not axes, pointers, selector/gate bytes, metadata, code, consumer state or the distinct 7474/74E2 alternate 11-row targets. The existing signed 0x7FFF compensation definition remains limited to its reviewed intact-source scope.";
    public const string Readiness = "PcInspectionOnly / NotFlashReady";

    internal static P28IgnitionMapExportGroup[] Describe(RomImage original, P28IgnitionMapExportSettings settings,
        RomImage? intermediate = null)
    {
        P28IgnitionMapInspector.LayoutGuard(original);
        intermediate ??= ComposeIntermediate(original, settings);
        return new[] { (Id: "ignition_map_0", Values: settings.IgnitionMap0),
            (Id: "ignition_map_1", Values: settings.IgnitionMap1) }.Select(item =>
        {
            var cells = (item.Values ?? []).Select(value =>
            {
                var offset = P28IgnitionMapContract.CellOffset(item.Id, value.Row, value.Column);
                return new P28IgnitionMapExportCell(item.Id, value.Row, value.Column, offset,
                    original.Span[offset], value.RawValue);
            }).ToArray();
            return new P28IgnitionMapExportGroup(item.Id, item.Values is not null,
                cells.Any(cell => cell.OldRawValue != cell.NewRawValue), cells.Length,
                cells.Count(cell => cell.OldRawValue != cell.NewRawValue), cells,
                AuditDomain(original, intermediate, P28IgnitionMapContract.Map(item.Id)));
        }).ToArray();
    }

    private static RomImage ComposeIntermediate(RomImage original, P28IgnitionMapExportSettings settings)
    {
        var patches = new List<BytePatch>();
        foreach (var item in new[] { (Id: "ignition_map_0", Values: settings.IgnitionMap0),
            (Id: "ignition_map_1", Values: settings.IgnitionMap1) })
            foreach (var value in item.Values ?? [])
                patches.Add(new(P28IgnitionMapContract.CellOffset(item.Id, value.Row, value.Column), [(byte)value.RawValue]));
        return original.CreateModifiedCopy(patches);
    }

    internal static P28IgnitionMapDomainAudit AuditDomain(RomImage original, RomImage next,
        P28IgnitionMapContractRow map)
    {
        var oldMin = int.MaxValue; var oldMax = int.MinValue; var newMin = int.MaxValue; var newMax = int.MinValue;
        long maxProduct = 0; var increase = 0; var decrease = 0; var equal = 0;
        for (var rpm = 0; rpm <= 255; rpm++) for (var load = 0; load <= 255; load++)
            {
                var a = P28IgnitionMapModel.ProjectNumeric(original.Span, map.Id, rpm, load);
                var b = P28IgnitionMapModel.ProjectNumeric(next.Span, map.Id, rpm, load);
                oldMin = Math.Min(oldMin, a.LookupResult); oldMax = Math.Max(oldMax, a.LookupResult);
                newMin = Math.Min(newMin, b.LookupResult); newMax = Math.Max(newMax, b.LookupResult);
                maxProduct = Math.Max(maxProduct, new[] { a.TopInterpolationProduct, a.BottomInterpolationProduct,
                a.FinalInterpolationProduct, b.TopInterpolationProduct, b.BottomInterpolationProduct,
                b.FinalInterpolationProduct }.Max());
                if (b.LookupResult > a.LookupResult) increase++; else if (b.LookupResult < a.LookupResult) decrease++; else equal++;
                static void Bounds(P28IgnitionNumericProjection value)
                {
                    var low = new[] { value.TopLeft, value.TopRight, value.BottomLeft, value.BottomRight }.Min();
                    var high = new[] { value.TopLeft, value.TopRight, value.BottomLeft, value.BottomRight }.Max();
                    if (value.LookupResult < low || value.LookupResult > high)
                        throw new InvalidDataException("Sequential ignition interpolation escaped its four numeric cells.");
                }
                Bounds(a); Bounds(b);
            }
        var rpmOrigin = map.Id == "ignition_map_0" ? P28IgnitionMapContract.Map0RpmAxisOrigin : P28IgnitionMapContract.Map1RpmAxisOrigin;
        var sentinel = original.Span[P28IgnitionMapContract.LoadAxisOrigin + 9] == 0 && original.Span[rpmOrigin + 19] == 0;
        if (!sentinel || maxProduct > (long)255 * ushort.MaxValue || increase + decrease + equal != 65536)
            throw new InvalidDataException("Ignition-map full finite arithmetic audit failed.");
        return new(map.Id, 65536, oldMin, oldMax, newMin, newMax, maxProduct, increase, decrease, equal,
            increase + decrease, true, true, true);
    }

    internal static P28IgnitionConsumerDomainAudit AuditConsumer()
    {
        long maxProduct = 0; var min = int.MaxValue; var max = int.MinValue; var bypass = 0; var scaling = 0;
        for (var lookup = 0; lookup <= 255; lookup++) for (var factor = 0; factor <= 255; factor++)
            {
                var value = P28IgnitionMapModel.Consume(lookup, factor);
                if (value.Product != (long)lookup * factor || value.Output != (factor == 0 ? lookup : lookup * factor >> 8) ||
                    value.ScalingExecuted != (factor != 0)) throw new InvalidDataException("Ignition consumer full-domain audit failed.");
                maxProduct = Math.Max(maxProduct, value.Product); min = Math.Min(min, value.Output); max = Math.Max(max, value.Output);
                if (factor == 0) bypass++; else scaling++;
            }
        return new(65536, bypass, scaling, maxProduct, min, max, true, true, true);
    }

    internal static P28IgnitionMapImmutableRange[] Immutable(RomImage image)
    {
        var ranges = new[]
        {
            ("vectors", 0x0000, 0x002F), ("selector-byte", 0x0227, 0x0227),
            ("axis-producer", 0x0A0C, 0x0A61), ("primary-selector-consumer", 0x0B64, 0x0BD3),
            ("checksum-code", 0x2B70, 0x2BB6), ("axis-helper", 0x59B2, 0x59E3),
            ("lookup-helper", 0x59E4, 0x5A45), ("selector-writer", 0x5FA0, 0x5FAC),
            ("selector-writer-gate", 0x60EA, 0x60EA), ("load-axis", 0x7000, 0x7009),
            ("candidate-700A", 0x700A, 0x700A), ("rpm-axes", 0x7014, 0x703B),
            ("alternate-map-0", 0x7474, 0x74E1), ("alternate-map-1", 0x74E2, 0x754F)
        };
        return ranges.Select(range => new P28IgnitionMapImmutableRange(range.Item1, range.Item2, range.Item3,
            HashUtilities.Sha256(image.Span[range.Item2..(range.Item3 + 1)]))).ToArray();
    }

    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) Compose(RomImage original,
        P28IgnitionMapExportSettings settings)
    {
        var b = ComposeIntermediate(original, settings); var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult;
        var oldByte = original.Span[0x7FFF];
        var compensation = new P28ComputedCompensation(0x7FFF, oldByte,
            P28ChecksumPreservingEditor.ComputeCompensation(oldByte, residue), P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(0x7FFF, [compensation.NewByte])]), compensation);
    }

    public static P28IgnitionMapExportPreview Preview(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, VerifiedCompensationLocation location,
        P28IgnitionMapExportSettings settings)
    {
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28IgnitionMapInspector.LayoutGuard(original);
        if (location.Offset != 0x7FFF) throw new InvalidDataException("Existing reviewed compensation location 0x7FFF is required.");
        var guardA = P28ChecksumCodeGuard.Assess(original);
        if (!guardA.ContractRecognized || !guardA.GateEnabled || P28NativeChecksumArithmetic.Calculate(original).ComputedResult != 0)
            throw new InvalidDataException("Original native checksum code/gate/residue is not admissible.");
        var (b, c, compensation) = Compose(original, settings);
        foreach (var image in new[] { b, c })
        {
            var guard = P28ChecksumCodeGuard.Assess(image);
            if (!guard.ContractRecognized || !guard.GateEnabled) throw new InvalidDataException("Composed image changed checksum code/gate.");
        }
        if (P28NativeChecksumArithmetic.Calculate(c).ComputedResult != 0)
            throw new InvalidDataException("Ignition-map checksum compensation failed.");
        var groups = Describe(original, settings, b); var immutable = Immutable(original);
        foreach (var range in immutable) foreach (var image in new[] { b, c })
                if (range.Sha256 != HashUtilities.Sha256(image.Span[range.Start..(range.EndInclusive + 1)]))
                    throw new InvalidDataException($"Immutable range {range.Id} changed.");
        var diff = P28FixedLimiterEditor.Diff(original, c);
        var plan = new P28IgnitionMapExportPlan(1, Purpose, ContractId, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), groups,
            AuditConsumer(), immutable, location.DefinitionId, location.DefinitionDigest, location.EvidenceIdentity,
            location.EvidenceScope, EditAudit, compensation, 0, P28NativeChecksumArithmetic.Calculate(b).ComputedResult,
            0, b.Hash, c.Hash, diff, diff.Length == 0, Scope, P28NativeChecksumArithmetic.Contract.Id, false, Readiness);
        Shape(plan);
        return new(original, profile, binding, location, b, c, plan);
    }

    internal static P28IgnitionMapExportSettings Settings(P28IgnitionMapExportPlan plan)
    {
        var map0 = plan.Maps[0]; var map1 = plan.Maps[1];
        return new(map0.Requested ? map0.Cells.Select(cell => new P28IgnitionMapCellSetting(cell.Row, cell.Column, cell.NewRawValue)).ToArray() : null,
            map1.Requested ? map1.Cells.Select(cell => new P28IgnitionMapCellSetting(cell.Row, cell.Column, cell.NewRawValue)).ToArray() : null);
    }

    public static P28IgnitionMapExportPreview Reproduce(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, VerifiedCompensationLocation location,
        P28IgnitionMapExportPlan plan)
    {
        var frozen = P28IgnitionMapExportPlan.Parse(plan.ToJson(false));
        var expected = Preview(original, profile, binding, confirmed, location, Settings(frozen));
        if (frozen.ToJson(false) != expected.Plan.ToJson(false))
            throw new InvalidDataException("Ignition-map plan does not reproduce from the exact original and code-owned contract.");
        return expected;
    }

    internal static void Shape(P28IgnitionMapExportPlan plan)
    {
        P28RawEditJson.ValidateObject(plan);
        if (plan.FormatVersion != 1 || plan.Purpose != Purpose || plan.ContractId != ContractId || plan.Size != 32768 ||
            plan.Scope != Scope || plan.EditAudit != EditAudit || plan.Readiness != Readiness || plan.PhysicalUnitsAvailable ||
            plan.ResidueA != 0 || plan.ResidueC != 0 || plan.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id ||
            plan.Maps.Count != 2 || plan.Maps[0].MapId != "ignition_map_0" || plan.Maps[1].MapId != "ignition_map_1" ||
            plan.Compensation.Offset != 0x7FFF || plan.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId ||
            plan.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(plan.Compensation.OldByte, plan.ResidueB))
            throw new InvalidDataException("Unsupported ignition-map plan metadata.");
        foreach (var group in plan.Maps)
        {
            if (group.RequestedCellCount != group.Cells.Count || group.ChangedCellCount != group.Cells.Count(cell => cell.OldRawValue != cell.NewRawValue) ||
                group.EffectivelyChanged != (group.ChangedCellCount != 0) || !group.Requested && group.Cells.Count != 0 ||
                group.Cells.Count > 200 || !group.Cells.SequenceEqual(group.Cells.OrderBy(cell => cell.Row).ThenBy(cell => cell.Column)) ||
                group.Cells.GroupBy(cell => (cell.Row, cell.Column)).Any(values => values.Count() != 1))
                throw new InvalidDataException("Contradictory ignition-map group.");
            foreach (var cell in group.Cells)
                if (cell.MapId != group.MapId || cell.Offset != P28IgnitionMapContract.CellOffset(group.MapId, cell.Row, cell.Column) ||
                    cell.OldRawValue is < 0 or > 255 || cell.NewRawValue is < 0 or > 255)
                    throw new InvalidDataException("Invalid code-owned ignition-map cell.");
            var audit = group.DomainAudit;
            if (audit.MapId != group.MapId || audit.CheckedInputPairs != 65536 ||
                audit.IncreasedResults + audit.DecreasedResults + audit.EqualResults != 65536 ||
                audit.ChangedResults != audit.IncreasedResults + audit.DecreasedResults || audit.MaximumInterpolationProduct < 0 ||
                audit.MaximumInterpolationProduct > (long)255 * ushort.MaxValue || !audit.SequentialFixedPointVerified ||
                !audit.WideIntermediatesVerified || !audit.Sentinel256Verified)
                throw new InvalidDataException("Invalid full-domain ignition-map audit.");
        }
        var consumer = plan.ConsumerAudit;
        if (consumer.CheckedInputPairs != 65536 || consumer.BypassPairs != 256 || consumer.ScalingPairs != 65280 ||
            consumer.MaximumProduct != 65025 || consumer.MinimumOutput != 0 || consumer.MaximumOutput != 255 ||
            !consumer.ZeroFactorBypassVerified || !consumer.UnsignedHighByteVerified || !consumer.FullByteDomainVerified)
            throw new InvalidDataException("Invalid full-domain ignition consumer audit.");
        _ = Settings(plan);
        var expected = plan.Maps.SelectMany(group => group.Cells)
            .Select(cell => new P28RawByteDiff(cell.Offset, (byte)cell.OldRawValue, (byte)cell.NewRawValue))
            .Append(new(plan.Compensation.Offset, plan.Compensation.OldByte, plan.Compensation.NewByte))
            .Where(diff => diff.OldByte != diff.NewByte).OrderBy(diff => diff.Offset).ToArray();
        if (expected.Length > 401 || !plan.ExpectedDiff.SequenceEqual(expected) || plan.IsNoOp != (expected.Length == 0) ||
            plan.ImmutableRanges.Count != 14 || plan.ImmutableRanges.Any(range => range.Start < 0 ||
                range.EndInclusive < range.Start || range.EndInclusive >= 32768 || range.Sha256.Length != 64 ||
                !range.Sha256.All(Uri.IsHexDigit)))
            throw new InvalidDataException("Ignition-map exact diff or immutable ranges are contradictory.");
    }
}
