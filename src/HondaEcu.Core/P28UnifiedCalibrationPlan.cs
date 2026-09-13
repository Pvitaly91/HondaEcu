using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed class P28UnifiedCalibrationSettings
{
    public const int MaximumBytes = 256 * 1024;
    public const string SettingsPurpose = "explicit-p28-calibration-set";

    public P28BasicCalibrationSettings Basic { get; }
    public P28FuelMapExportSettings Fuel { get; }
    public P28IgnitionMapExportSettings Ignition { get; }

    public P28UnifiedCalibrationSettings(P28BasicCalibrationSettings basic,
        P28FuelMapExportSettings fuel, P28IgnitionMapExportSettings ignition)
    {
        Basic = basic ?? throw new ArgumentNullException(nameof(basic));
        Fuel = fuel ?? throw new ArgumentNullException(nameof(fuel));
        Ignition = ignition ?? throw new ArgumentNullException(nameof(ignition));
    }

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(new
    {
        formatVersion = 1,
        purpose = SettingsPurpose,
        basic = new
        {
            vtec = Basic.Vtec,
            @fixed = Basic.Limiter.Fixed,
            bank0 = Basic.Limiter.Bank0,
            bank1 = Basic.Limiter.Bank1,
            baseTable = Basic.Idle.BaseTable,
            lateTable = Basic.Idle.LateTable
        },
        fuel = new { map_0 = Fuel.Map0, map_1 = Fuel.Map1 },
        ignition = new { ignition_map_0 = Ignition.IgnitionMap0, ignition_map_1 = Ignition.IgnitionMap1 }
    }, new JsonSerializerOptions
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = indented
    });

    public static P28UnifiedCalibrationSettings Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes)
            throw new InvalidDataException("Unified calibration settings exceed 256 KiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 10 });
        var root = document.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "basic", "fuel", "ignition");
        if (!Unsigned(root.GetProperty("formatVersion"), out var version) || version != 1 ||
            root.GetProperty("purpose").GetString() != SettingsPurpose)
            throw new InvalidDataException("Unsupported unified calibration settings version or purpose.");

        var basic = root.GetProperty("basic");
        var fuel = root.GetProperty("fuel");
        var ignition = root.GetProperty("ignition");
        P28LimiterScenario.Shape(basic, "vtec", "fixed", "bank0", "bank1", "baseTable", "lateTable");
        P28LimiterScenario.Shape(fuel, "map_0", "map_1");
        P28LimiterScenario.Shape(ignition, "ignition_map_0", "ignition_map_1");

        string Wrap(string purpose, IEnumerable<(string Name, JsonElement Value)> properties)
        {
            var fields = properties.Select(item => JsonSerializer.Serialize(item.Name) + ":" + item.Value.GetRawText());
            return "{\"formatVersion\":1,\"purpose\":" + JsonSerializer.Serialize(purpose) + "," +
                string.Join(',', fields) + "}";
        }

        var basicSettings = P28BasicCalibrationSettings.Parse(Wrap("explicit-basic-calibration-selection",
            new[] { "vtec", "fixed", "bank0", "bank1", "baseTable", "lateTable" }
                .Select(name => (name, basic.GetProperty(name)))));
        var fuelSettings = P28FuelMapExportSettings.Parse(Wrap("explicit-fuel-map-cell-values",
            new[] { "map_0", "map_1" }.Select(name => (name, fuel.GetProperty(name)))));
        var ignitionSettings = P28IgnitionMapExportSettings.Parse(Wrap("explicit-ignition-map-cell-values",
            new[] { "ignition_map_0", "ignition_map_1" }.Select(name => (name, ignition.GetProperty(name)))));
        return new(basicSettings, fuelSettings, ignitionSettings);
    }

    private static bool Unsigned(JsonElement value, out int result)
    {
        result = 0;
        return value.ValueKind == JsonValueKind.Number && value.GetRawText().All(char.IsAsciiDigit) &&
            value.TryGetInt32(out result);
    }
}

public sealed record P28UnifiedCalibrationGroup(string Family, string Id, bool Requested,
    bool ByteChanged, bool BehaviorChanged, int RequestedValueCount, int ChangedValueCount);
public sealed record P28UnifiedImmutableRange(string Family, string Id, int Start, int EndInclusive, string Sha256);
public sealed record P28UnifiedSuiteScope(string Id, string Scope);

public sealed record P28UnifiedCalibrationPlan(int FormatVersion, string Purpose, string ContractId,
    RomHash OriginalHash, int Size, string ProfileId, string ProfileDigest, string BindingDigest,
    IReadOnlyList<P28UnifiedCalibrationGroup> Groups, IReadOnlyList<P28BasicCalibrationGroup> BasicGroups,
    IReadOnlyList<P28FuelMapExportGroup> FuelMaps, IReadOnlyList<P28IgnitionMapExportGroup> IgnitionMaps,
    P28IgnitionConsumerDomainAudit IgnitionConsumerAudit, IReadOnlyList<P28UnifiedImmutableRange> ImmutableRanges,
    string LocationId, string LocationDigest, string LocationEvidenceIdentity, string LocationScope,
    string EditAudit, P28ComputedCompensation Compensation, byte ResidueA, byte ResidueB, byte ResidueC,
    RomHash IntermediateHash, RomHash OutputHash, IReadOnlyList<P28RawByteDiff> ExpectedDiff, bool IsNoOp,
    int RequestedGroupCount, int ChangedGroupCount, int RequestedMapCellCount, int ChangedMapCellCount,
    IReadOnlyList<P28UnifiedSuiteScope> Suites, string ChecksumContractId, bool PhysicalRpmAvailable,
    bool PhysicalDegreesAvailable, string Readiness)
{
    public const int MaximumBytes = 4 * 1024 * 1024;
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string Digest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));
    public static P28UnifiedCalibrationPlan Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes)
            throw new InvalidDataException("Unified calibration plan exceeds 4 MiB.");
        var plan = P28RawEditJson.Parse<P28UnifiedCalibrationPlan>(json, P28BasicCalibrationPlan.OptionalProperty);
        P28UnifiedCalibrationEditor.Shape(plan);
        return plan;
    }
    public static P28UnifiedCalibrationPlan Load(string path) =>
        Parse(P28IdleTablePlan.ReadJson(path, MaximumBytes));
}

public sealed class P28UnifiedCalibrationPreview
{
    private readonly string _plan;
    internal P28UnifiedCalibrationPreview(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        VerifiedCompensationLocation location, RomImage intermediate, RomImage output,
        P28UnifiedCalibrationPlan plan)
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
    public P28UnifiedCalibrationPlan Plan => P28UnifiedCalibrationPlan.Parse(_plan);
    internal (string Id, RomImage Image)[] Images => [("A", Original), ("B", Intermediate), ("C", Output)];
}

public static class P28UnifiedCalibrationEditor
{
    public const string Purpose = "pc-only-unified-known-calibration-checksum-preserving-export";
    public const string ContractId = "p28-known-calibration-set-v1";
    public const string Readiness = "PcInspectionOnly / NotFlashReady";
    public const string EditAudit = "Combined admission retains the established source-listed numeric scopes for one VTEC slot, fixed/adaptive limiter operands, idle interpolation values, primary fuel cells and primary ignition cells. All pointer origins, axes, multipliers, alternate maps, selectors, gates, vectors, instruction bytes and destinations remain immutable. Suites execute independently on the same complete A/B/C images; this is not a shared ECU main loop, scheduler, corrupt-state proof or hardware authority.";

    internal static P28UnifiedSuiteScope[] Scopes =>
    [
        new("VtecThresholdPrefix", "M1t strict changed/control prefix on complete A/B/C; no G/F, P1 or physical output"),
        new("LimiterAdaptive", "M1t changed full corpus or deterministic unchanged controls on complete A/B/C"),
        new("Idle", "M1t changed full corpus or deterministic unchanged controls on complete A/B/C"),
        new("Fuel", "M2b native lookup/consumer corpus on complete A/B/C; distinct DATA0127.1 selector semantics"),
        new("Ignition", "M2d factor0 plus once-seeded factors 1/127/128/173/255 on complete A/B/C; distinct DATA0227.5 selector semantics"),
        new("Checksum", "One M1f checksumBatch for A/B/C x scratch 00/55/AA x 512 ordered invocations"),
        new("JointEcuScheduler/GUI/Hardware/FullBoot", "NotRun")
    ];

    internal static P28UnifiedCalibrationGroup[] Summaries(IReadOnlyList<P28BasicCalibrationGroup> basic,
        IReadOnlyList<P28FuelMapExportGroup> fuel, IReadOnlyList<P28IgnitionMapExportGroup> ignition)
    {
        static (int Requested, int Changed) BasicCounts(P28BasicCalibrationGroup group)
        {
            if (!group.Requested) return (0, 0);
            if (group.Vtec is { } vtec)
            {
                var changed = vtec.Slot is { } slot && vtec.OriginalBytes[slot.Offset - P28ThresholdLogic.BlockOffset] !=
                    vtec.NewBytes[slot.Offset - P28ThresholdLogic.BlockOffset] ? 1 : 0;
                return (1, changed);
            }
            if (group.Limiter is { } limiter)
            {
                var fields = limiter.FixedOperands.Select(word => word.OriginalWord != word.NewWord)
                    .Concat(limiter.AdaptiveWords.Select(word => word.OldWord != word.NewWord)).ToArray();
                return (fields.Length, fields.Count(changed => changed));
            }
            var cells = group.Idle!.Cells;
            return (cells.Count, cells.Count(cell => cell.OldValue != cell.NewValue));
        }
        var result = basic.Select(group =>
        {
            var counts = BasicCounts(group);
            return new P28UnifiedCalibrationGroup("basic", group.Id, group.Requested,
                group.EffectivelyChanged, group.EffectivelyChanged, counts.Requested, counts.Changed);
        }).ToList();
        result.AddRange(fuel.Select(map => new P28UnifiedCalibrationGroup("fuel", map.MapId, map.Requested,
            map.EffectivelyChanged, map.DomainAudit.ChangedResults != 0, map.RequestedCellCount,
            map.ChangedCellCount)));
        result.AddRange(ignition.Select(map => new P28UnifiedCalibrationGroup("ignition", map.MapId,
            map.Requested, map.EffectivelyChanged, map.DomainAudit.ChangedResults != 0,
            map.RequestedCellCount, map.ChangedCellCount)));
        return result.ToArray();
    }

    internal static P28UnifiedCalibrationSettings Settings(P28UnifiedCalibrationPlan plan)
    {
        var vtec = plan.BasicGroups[0].Vtec!;
        var fixedGroup = plan.BasicGroups[1].Limiter!;
        P28CombinedBankPair? Bank(int index) => plan.BasicGroups[index].Requested
            ? new(plan.BasicGroups[index].Limiter!.AdaptiveWords[0].NewWord,
                plan.BasicGroups[index].Limiter!.AdaptiveWords[1].NewWord) : null;
        int[]? Table(int index) => plan.BasicGroups[index].Requested
            ? plan.BasicGroups[index].Idle!.Cells.Select(cell => cell.NewValue).ToArray() : null;
        var basic = new P28BasicCalibrationSettings(vtec.Slot is null ? null :
            new(vtec.Slot.Id, vtec.NewBytes[vtec.Slot.Offset - P28ThresholdLogic.BlockOffset]),
            fixedGroup.Requested ? new(fixedGroup.FixedOperands[0].NewWord, fixedGroup.FixedOperands[1].NewWord) : null,
            Bank(2), Bank(3), Table(4), Table(5));
        var fuel = new P28FuelMapExportSettings(
            plan.FuelMaps[0].Requested ? plan.FuelMaps[0].Cells.Select(cell => new P28FuelMapCellSetting(cell.Row, cell.Column, cell.NewRawValue)).ToArray() : null,
            plan.FuelMaps[1].Requested ? plan.FuelMaps[1].Cells.Select(cell => new P28FuelMapCellSetting(cell.Row, cell.Column, cell.NewRawValue)).ToArray() : null);
        var ignition = new P28IgnitionMapExportSettings(
            plan.IgnitionMaps[0].Requested ? plan.IgnitionMaps[0].Cells.Select(cell => new P28IgnitionMapCellSetting(cell.Row, cell.Column, cell.NewRawValue)).ToArray() : null,
            plan.IgnitionMaps[1].Requested ? plan.IgnitionMaps[1].Cells.Select(cell => new P28IgnitionMapCellSetting(cell.Row, cell.Column, cell.NewRawValue)).ToArray() : null);
        return new(basic, fuel, ignition);
    }

    internal static (RomImage B, RomImage C, P28ComputedCompensation Compensation) Compose(
        RomImage original, P28UnifiedCalibrationSettings settings)
    {
        var basic = P28BasicCalibrationEditor.Describe(original, settings.Basic);
        var patches = P28BasicCalibrationEditor.FieldBytes(basic)
            .Select(diff => new BytePatch(diff.Offset, [diff.NewByte])).ToList();
        foreach (var item in new[] { ("map_0", settings.Fuel.Map0), ("map_1", settings.Fuel.Map1) })
            foreach (var value in item.Item2 ?? [])
                patches.Add(new(P28FuelMapContract.CellOffset(item.Item1, value.Row, value.Column), [(byte)value.RawValue]));
        foreach (var item in new[] { ("ignition_map_0", settings.Ignition.IgnitionMap0),
            ("ignition_map_1", settings.Ignition.IgnitionMap1) })
            foreach (var value in item.Item2 ?? [])
                patches.Add(new(P28IgnitionMapContract.CellOffset(item.Item1, value.Row, value.Column), [(byte)value.RawValue]));
        if (patches.GroupBy(patch => patch.Offset).Any(group => group.Count() != 1))
            throw new InvalidDataException("Unified code-owned fields overlap unexpectedly.");
        var b = original.CreateModifiedCopy(patches);
        var residue = P28NativeChecksumArithmetic.Calculate(b).ComputedResult;
        var oldByte = original.Span[0x7FFF];
        var compensation = new P28ComputedCompensation(0x7FFF, oldByte,
            P28ChecksumPreservingEditor.ComputeCompensation(oldByte, residue),
            P28ChecksumPreservingEditor.FormulaId);
        return (b, b.CreateModifiedCopy([new(0x7FFF, [compensation.NewByte])]), compensation);
    }

    internal static P28UnifiedImmutableRange[] Immutable(RomImage image) =>
        P28FuelMapExportEditor.Immutable(image)
            .Select(range => new P28UnifiedImmutableRange("fuel", range.Id, range.Start, range.EndInclusive, range.Sha256))
            .Concat(P28IgnitionMapExportEditor.Immutable(image)
                .Select(range => new P28UnifiedImmutableRange("ignition", range.Id, range.Start, range.EndInclusive, range.Sha256)))
            .OrderBy(range => range.Family).ThenBy(range => range.Start).ThenBy(range => range.Id).ToArray();

    public static P28UnifiedCalibrationPreview Preview(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, VerifiedCompensationLocation location,
        P28UnifiedCalibrationSettings settings)
    {
        _ = P28ChecksumPreservingDefinitions.Resolve(original, profile, binding, confirmed, location);
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28AdaptiveBaseEditor.MappingGuard(original);
        P28IdleContextsInspector.TableGuard(original); P28FuelMapInspector.LayoutGuard(original);
        P28IgnitionMapInspector.LayoutGuard(original);
        if (location.Offset != 0x7FFF) throw new InvalidDataException("Existing reviewed compensation location 0x7FFF is required.");
        var originalGuard = P28ChecksumCodeGuard.Assess(original);
        if (!originalGuard.ContractRecognized || !originalGuard.GateEnabled ||
            P28NativeChecksumArithmetic.Calculate(original).ComputedResult != 0)
            throw new InvalidDataException("Original native checksum code/gate/residue is not admissible.");
        var (b, c, compensation) = Compose(original, settings);
        foreach (var image in new[] { b, c })
        {
            var guard = P28ChecksumCodeGuard.Assess(image);
            if (!guard.ContractRecognized || !guard.GateEnabled)
                throw new InvalidDataException("Unified composition changed checksum code or gate.");
        }
        if (P28NativeChecksumArithmetic.Calculate(c).ComputedResult != 0)
            throw new InvalidDataException("Unified checksum compensation failed.");

        var basic = P28BasicCalibrationEditor.Describe(original, settings.Basic);
        var fuel = P28FuelMapExportEditor.Describe(original, settings.Fuel, b);
        var ignition = P28IgnitionMapExportEditor.Describe(original, settings.Ignition, b);
        var groups = Summaries(basic, fuel, ignition); var immutable = Immutable(original);
        foreach (var range in immutable) foreach (var image in new[] { b, c })
                if (range.Sha256 != HashUtilities.Sha256(image.Span[range.Start..(range.EndInclusive + 1)]))
                    throw new InvalidDataException($"Immutable {range.Family}/{range.Id} range changed.");
        var diff = P28FixedLimiterEditor.Diff(original, c);
        var plan = new P28UnifiedCalibrationPlan(1, Purpose, ContractId, original.Hash, original.Size,
            profile.Id, P28VtecInspector.ComputeProfileDigest(profile),
            P28RawThresholdEditor.ComputeBindingDigest(binding), groups, basic, fuel, ignition,
            P28IgnitionMapExportEditor.AuditConsumer(), immutable, location.DefinitionId,
            location.DefinitionDigest, location.EvidenceIdentity, location.EvidenceScope, EditAudit,
            compensation, 0, P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash,
            diff, diff.Length == 0, groups.Count(group => group.Requested),
            groups.Count(group => group.ByteChanged), fuel.Sum(group => group.RequestedCellCount) +
            ignition.Sum(group => group.RequestedCellCount), fuel.Sum(group => group.ChangedCellCount) +
            ignition.Sum(group => group.ChangedCellCount), Scopes, P28NativeChecksumArithmetic.Contract.Id,
            false, false, Readiness);
        Shape(plan);
        return new(original, profile, binding, location, b, c, plan);
    }

    public static P28UnifiedCalibrationPreview Reproduce(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, VerifiedCompensationLocation location,
        P28UnifiedCalibrationPlan plan)
    {
        var frozen = P28UnifiedCalibrationPlan.Parse(plan.ToJson(false));
        var expected = Preview(original, profile, binding, confirmed, location, Settings(frozen));
        if (frozen.ToJson(false) != expected.Plan.ToJson(false))
            throw new InvalidDataException("Unified plan does not reproduce from the exact original and code-owned contracts.");
        return expected;
    }

    internal static void Shape(P28UnifiedCalibrationPlan plan)
    {
        P28RawEditJson.ValidateObject(plan, P28BasicCalibrationPlan.OptionalProperty);
        var ids = new[] { "vtec", "fixed", "bank0", "bank1", "baseTable", "lateTable",
            "map_0", "map_1", "ignition_map_0", "ignition_map_1" };
        if (plan.FormatVersion != 1 || plan.Purpose != Purpose || plan.ContractId != ContractId ||
            plan.Size != 32768 || plan.EditAudit != EditAudit || plan.ResidueA != 0 || plan.ResidueC != 0 ||
            plan.ChecksumContractId != P28NativeChecksumArithmetic.Contract.Id || plan.PhysicalRpmAvailable ||
            plan.PhysicalDegreesAvailable || plan.Readiness != Readiness || plan.Groups.Count != 10 ||
            !plan.Groups.Select(group => group.Id).SequenceEqual(ids) || plan.BasicGroups.Count != 6 ||
            plan.FuelMaps.Count != 2 || plan.IgnitionMaps.Count != 2 ||
            !plan.Suites.SequenceEqual(Scopes) || plan.Compensation.Offset != 0x7FFF ||
            plan.Compensation.FormulaId != P28ChecksumPreservingEditor.FormulaId ||
            plan.Compensation.NewByte != P28ChecksumPreservingEditor.ComputeCompensation(
                plan.Compensation.OldByte, plan.ResidueB))
            throw new InvalidDataException("Unsupported unified calibration plan metadata.");
        if (plan.RequestedGroupCount != plan.Groups.Count(group => group.Requested) ||
            plan.ChangedGroupCount != plan.Groups.Count(group => group.ByteChanged) ||
            plan.Groups.Any(group => group.ByteChanged && !group.Requested || group.BehaviorChanged && !group.ByteChanged))
            throw new InvalidDataException("Contradictory unified group summary.");
        var summaries = Summaries(plan.BasicGroups, plan.FuelMaps, plan.IgnitionMaps);
        if (!plan.Groups.SequenceEqual(summaries))
            throw new InvalidDataException("Unified group summaries differ from their closed family selections.");
        var basicDiff = P28BasicCalibrationEditor.FieldBytes(plan.BasicGroups)
            .Append(new(plan.Compensation.Offset, plan.Compensation.OldByte, plan.Compensation.NewByte))
            .Where(diff => diff.OldByte != diff.NewByte).OrderBy(diff => diff.Offset).ToArray();
        P28BasicCalibrationEditor.Shape(new P28BasicCalibrationPlan(1,
            P28BasicCalibrationEditor.Purpose, P28BasicCalibrationEditor.ContractId, plan.OriginalHash,
            plan.Size, plan.ProfileId, plan.ProfileDigest, plan.BindingDigest, plan.BasicGroups,
            plan.LocationId, plan.LocationDigest, plan.LocationEvidenceIdentity, plan.LocationScope,
            P28BasicCalibrationEditor.EditAudit, plan.Compensation, plan.ResidueA, plan.ResidueB,
            plan.ResidueC, plan.IntermediateHash, plan.OutputHash, basicDiff, basicDiff.Length == 0,
            P28BasicCalibrationEditor.Scopes, plan.ChecksumContractId, false, plan.Readiness));
        var fuelDiff = plan.FuelMaps.SelectMany(group => group.Cells)
            .Select(cell => new P28RawByteDiff(cell.Offset, (byte)cell.OldRawValue, (byte)cell.NewRawValue))
            .Append(new(plan.Compensation.Offset, plan.Compensation.OldByte, plan.Compensation.NewByte))
            .Where(diff => diff.OldByte != diff.NewByte).OrderBy(diff => diff.Offset).ToArray();
        P28FuelMapExportEditor.Shape(new P28FuelMapExportPlan(1, P28FuelMapExportEditor.Purpose,
            P28FuelMapExportEditor.ContractId, plan.OriginalHash, plan.Size, plan.ProfileId,
            plan.ProfileDigest, plan.BindingDigest, plan.FuelMaps,
            plan.ImmutableRanges.Where(range => range.Family == "fuel")
                .Select(range => new P28FuelMapImmutableRange(range.Id, range.Start, range.EndInclusive, range.Sha256)).ToArray(),
            plan.LocationId, plan.LocationDigest, plan.LocationEvidenceIdentity, plan.LocationScope,
            P28FuelMapExportEditor.EditAudit, plan.Compensation, plan.ResidueA, plan.ResidueB,
            plan.ResidueC, plan.IntermediateHash, plan.OutputHash, fuelDiff, fuelDiff.Length == 0,
            P28FuelMapExportEditor.Scope, plan.ChecksumContractId, false, plan.Readiness));
        var ignitionDiff = plan.IgnitionMaps.SelectMany(group => group.Cells)
            .Select(cell => new P28RawByteDiff(cell.Offset, (byte)cell.OldRawValue, (byte)cell.NewRawValue))
            .Append(new(plan.Compensation.Offset, plan.Compensation.OldByte, plan.Compensation.NewByte))
            .Where(diff => diff.OldByte != diff.NewByte).OrderBy(diff => diff.Offset).ToArray();
        P28IgnitionMapExportEditor.Shape(new P28IgnitionMapExportPlan(1,
            P28IgnitionMapExportEditor.Purpose, P28IgnitionMapExportEditor.ContractId,
            plan.OriginalHash, plan.Size, plan.ProfileId, plan.ProfileDigest, plan.BindingDigest,
            plan.IgnitionMaps, plan.IgnitionConsumerAudit,
            plan.ImmutableRanges.Where(range => range.Family == "ignition")
                .Select(range => new P28IgnitionMapImmutableRange(range.Id, range.Start, range.EndInclusive, range.Sha256)).ToArray(),
            plan.LocationId, plan.LocationDigest, plan.LocationEvidenceIdentity, plan.LocationScope,
            P28IgnitionMapExportEditor.EditAudit, plan.Compensation, plan.ResidueA, plan.ResidueB,
            plan.ResidueC, plan.IntermediateHash, plan.OutputHash, ignitionDiff,
            ignitionDiff.Length == 0, P28IgnitionMapExportEditor.Scope, plan.ChecksumContractId,
            false, plan.Readiness));
        var settings = Settings(plan);
        _ = settings;
        var expected = P28BasicCalibrationEditor.FieldBytes(plan.BasicGroups)
            .Concat(plan.FuelMaps.SelectMany(group => group.Cells)
                .Select(cell => new P28RawByteDiff(cell.Offset, (byte)cell.OldRawValue, (byte)cell.NewRawValue)))
            .Concat(plan.IgnitionMaps.SelectMany(group => group.Cells)
                .Select(cell => new P28RawByteDiff(cell.Offset, (byte)cell.OldRawValue, (byte)cell.NewRawValue)))
            .Append(new(plan.Compensation.Offset, plan.Compensation.OldByte, plan.Compensation.NewByte))
            .Where(diff => diff.OldByte != diff.NewByte).OrderBy(diff => diff.Offset).ToArray();
        if (expected.Length > 842 || !expected.SequenceEqual(plan.ExpectedDiff) ||
            plan.IsNoOp != (expected.Length == 0) ||
            plan.RequestedMapCellCount != plan.FuelMaps.Sum(group => group.RequestedCellCount) +
                plan.IgnitionMaps.Sum(group => group.RequestedCellCount) ||
            plan.ChangedMapCellCount != plan.FuelMaps.Sum(group => group.ChangedCellCount) +
                plan.IgnitionMaps.Sum(group => group.ChangedCellCount) ||
            plan.RequestedMapCellCount is < 0 or > 800 || plan.ChangedMapCellCount is < 0 or > 800 ||
            plan.ImmutableRanges.Count == 0 || plan.ImmutableRanges.Any(range => range.Start < 0 ||
                range.EndInclusive < range.Start || range.EndInclusive >= 32768 || range.Sha256.Length != 64 ||
                !range.Sha256.All(Uri.IsHexDigit)))
            throw new InvalidDataException("Unified exact diff, counts or immutable ranges are contradictory.");
    }

    internal static (P28BasicCalibrationPreview Basic, P28FuelMapExportPreview Fuel,
        P28IgnitionMapExportPreview Ignition) FamilyViews(P28UnifiedCalibrationPreview preview)
    {
        var settings = Settings(preview.Plan);
        var basicPlan = P28BasicCalibrationEditor.Preview(preview.Original, preview.Profile, preview.Binding,
            true, preview.Location, settings.Basic).Plan;
        var fuelPlan = P28FuelMapExportEditor.Preview(preview.Original, preview.Profile, preview.Binding,
            true, preview.Location, settings.Fuel).Plan;
        var ignitionPlan = P28IgnitionMapExportEditor.Preview(preview.Original, preview.Profile, preview.Binding,
            true, preview.Location, settings.Ignition).Plan;
        return (P28BasicCalibrationEditor.Reproduce(preview.Original, preview.Profile,
                preview.Binding, true, preview.Location, basicPlan),
            P28FuelMapExportEditor.Reproduce(preview.Original, preview.Profile,
                preview.Binding, true, preview.Location, fuelPlan),
            P28IgnitionMapExportEditor.Reproduce(preview.Original, preview.Profile,
                preview.Binding, true, preview.Location, ignitionPlan));
    }
}
