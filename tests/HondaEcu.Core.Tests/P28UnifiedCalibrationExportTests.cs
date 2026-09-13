using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28UnifiedCalibrationExportTests
{
    private static RomImage Original()
    {
        var bytes = P28BasicCalibrationExportTests.Preview().Original.ToArray();
        var fuel = P28FuelMapExportTests.Image();
        var ignition = P28IgnitionMapTests.InventedImage(true).ToArray();
        static void Copy(byte[] source, byte[] target, int start, int count) =>
            Array.Copy(source, start, target, start, count);
        foreach (var (start, count) in new[]
        {
            (0x0A0C, 3), (0x0A24, 3), (0x0A65, 3), (0x12DF, 3), (0x12F9, 7),
            (0x130C, 3), (0x131A, 2), (0x1323, 3), (0x7000, 10), (0x7014, 40),
            (0x7050, 200), (0x7118, 10), (0x7122, 200), (0x71EA, 10)
        }) Copy(fuel, bytes, start, count);
        foreach (var (start, count) in new[]
        {
            (0x0A50, 3), (0x0B67, 4), (0x0B71, 2), (0x0B7A, 3), (0x0B91, 3),
            (0x0BAF, 5), (0x0BD2, 2), (0x72E4, 400), (0x7474, 220)
        }) Copy(ignition, bytes, start, count);
        bytes[0x6000] = 0;
        bytes[0x6000] = unchecked((byte)-bytes.Sum(value => (int)value));
        return RomImage.FromBytes(bytes);
    }

    private static P28UnifiedCalibrationSettings Settings(RomImage original, int mask = 1023,
        int slot = 0, bool allMapCells = false)
    {
        var basicAll = P28BasicCalibrationExportTests.Settings(63, slot);
        var basic = new P28BasicCalibrationSettings(
            (mask & 1) != 0 ? basicAll.Vtec : null,
            (mask & 2) != 0 ? basicAll.Limiter.Fixed : null,
            (mask & 4) != 0 ? basicAll.Limiter.Bank0 : null,
            (mask & 8) != 0 ? basicAll.Limiter.Bank1 : null,
            (mask & 16) != 0 ? basicAll.Idle.BaseTable : null,
            (mask & 32) != 0 ? basicAll.Idle.LateTable : null);
        P28FuelMapCellSetting[] FuelCells(string id) => Enumerable.Range(0, allMapCells ? 200 : 1)
            .Select(index => new P28FuelMapCellSetting(index / 10, index % 10,
                (original.Span[P28FuelMapContract.CellOffset(id, index / 10, index % 10)] + 1) & 255)).ToArray();
        P28IgnitionMapCellSetting[] IgnitionCells(string id) => Enumerable.Range(0, allMapCells ? 200 : 1)
            .Select(index => new P28IgnitionMapCellSetting(index / 10, index % 10,
                (original.Span[P28IgnitionMapContract.CellOffset(id, index / 10, index % 10)] + 1) & 255)).ToArray();
        return new(basic,
            new((mask & 64) != 0 ? FuelCells("map_0") : null,
                (mask & 128) != 0 ? FuelCells("map_1") : null),
            new((mask & 256) != 0 ? IgnitionCells("ignition_map_0") : null,
                (mask & 512) != 0 ? IgnitionCells("ignition_map_1") : null));
    }

    internal static P28UnifiedCalibrationPreview Preview(P28UnifiedCalibrationSettings? settings = null)
    {
        var original = Original(); settings ??= Settings(original);
        var profile = new RomProfile("p28-304", "Invented unified metadata", "Not admission",
            32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id,
            32768, original.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        var (b, c, compensation) = P28UnifiedCalibrationEditor.Compose(original, settings);
        var basic = P28BasicCalibrationEditor.Describe(original, settings.Basic);
        var fuel = P28FuelMapExportEditor.Describe(original, settings.Fuel, b);
        var ignition = P28IgnitionMapExportEditor.Describe(original, settings.Ignition, b);
        var groups = P28UnifiedCalibrationEditor.Summaries(basic, fuel, ignition);
        var diff = P28FixedLimiterEditor.Diff(original, c);
        var plan = new P28UnifiedCalibrationPlan(1, P28UnifiedCalibrationEditor.Purpose,
            P28UnifiedCalibrationEditor.ContractId, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding),
            groups, basic, fuel, ignition, P28IgnitionMapExportEditor.AuditConsumer(),
            P28UnifiedCalibrationEditor.Immutable(original), "invented-not-authority", new string('a', 64),
            "invented", "invented bounded scope", P28UnifiedCalibrationEditor.EditAudit, compensation,
            0, P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash, diff,
            diff.Length == 0, groups.Count(group => group.Requested), groups.Count(group => group.ByteChanged),
            fuel.Sum(group => group.RequestedCellCount) + ignition.Sum(group => group.RequestedCellCount),
            fuel.Sum(group => group.ChangedCellCount) + ignition.Sum(group => group.ChangedCellCount),
            P28UnifiedCalibrationEditor.Scopes, P28NativeChecksumArithmetic.Contract.Id, false, false,
            P28UnifiedCalibrationEditor.Readiness);
        P28UnifiedCalibrationEditor.Shape(plan);
        return new(original, profile, binding, null!, b, c, plan);
    }

    [Fact]
    public void ClosedSettingsPreserveAllTenNullEmptyAndCanonicalSelections()
    {
        const string json = """{"formatVersion":1,"purpose":"explicit-p28-calibration-set","basic":{"vtec":null,"fixed":null,"bank0":null,"bank1":null,"baseTable":null,"lateTable":null},"fuel":{"map_0":[{"row":2,"column":3,"rawValue":9},{"row":0,"column":1,"rawValue":8}],"map_1":[]},"ignition":{"ignition_map_0":null,"ignition_map_1":[]}}""";
        var settings = P28UnifiedCalibrationSettings.Parse(json);
        Assert.Equal([(0, 1, 8), (2, 3, 9)], settings.Fuel.Map0!.Select(cell => (cell.Row, cell.Column, cell.RawValue)));
        Assert.NotNull(settings.Fuel.Map1); Assert.Empty(settings.Fuel.Map1!);
        Assert.Null(settings.Ignition.IgnitionMap0); Assert.NotNull(settings.Ignition.IgnitionMap1);
        Assert.Equal(settings.ToJson(false), P28UnifiedCalibrationSettings.Parse(settings.ToJson()).ToJson(false));
        foreach (var invalid in new[]
        {
            json.Replace("," + "\"ignition\":{\"ignition_map_0\":null,\"ignition_map_1\":[]}", ""),
            json.Replace("\"rawValue\":9", "\"rawValue\":9.0"),
            json.Replace("\"row\":2", "\"row\":20"),
            json.Replace("\"rawValue\":9", "\"rawValue\":9,\"offset\":1"),
            json.Replace("\"purpose\":\"explicit-p28-calibration-set\"", "\"purpose\":\"raw-patch\"")
        }) Assert.ThrowsAny<Exception>(() => P28UnifiedCalibrationSettings.Parse(invalid));

        var reordered = "{\"ignition\":" + JsonNode.Parse(json)!["ignition"]!.ToJsonString() +
            ",\"purpose\":\"explicit-p28-calibration-set\",\"fuel\":" +
            JsonNode.Parse(json)!["fuel"]!.ToJsonString() + ",\"formatVersion\":1,\"basic\":" +
            JsonNode.Parse(json)!["basic"]!.ToJsonString() + "}";
        Assert.Equal(settings.ToJson(false), P28UnifiedCalibrationSettings.Parse(reordered).ToJson(false));
        Assert.ThrowsAny<Exception>(() => P28UnifiedCalibrationSettings.Parse(
            json.Replace("\"formatVersion\":1", "\"formatVersion\":1,\"formatVersion\":1")));
        Assert.ThrowsAny<Exception>(() => P28UnifiedCalibrationSettings.Parse(
            json.Replace("\"map_0\":[", "\"map_0\":null,\"map_0\":[")));
    }

    [Fact]
    public void AllOneThousandTwentyThreeSelectionsAndEightVtecSlotsRoundTrip()
    {
        var original = Original();
        for (var mask = 1; mask < 1024; mask++)
        {
            var parsed = P28UnifiedCalibrationSettings.Parse(Settings(original, mask).ToJson(false));
            var selected = new[]
            {
                parsed.Basic.Vtec is not null, parsed.Basic.Limiter.Fixed is not null,
                parsed.Basic.Limiter.Bank0 is not null, parsed.Basic.Limiter.Bank1 is not null,
                parsed.Basic.Idle.BaseTable is not null, parsed.Basic.Idle.LateTable is not null,
                parsed.Fuel.Map0 is not null, parsed.Fuel.Map1 is not null,
                parsed.Ignition.IgnitionMap0 is not null, parsed.Ignition.IgnitionMap1 is not null
            };
            for (var bit = 0; bit < 10; bit++) Assert.Equal((mask & 1 << bit) != 0, selected[bit]);
        }
        for (var slot = 0; slot < 8; slot++)
        {
            var parsed = P28UnifiedCalibrationSettings.Parse(Settings(original, 1, slot).ToJson(false));
            Assert.Equal(P28ThresholdLogic.GetSlots()[slot].Id, parsed.Basic.Vtec!.Slot);
        }
    }

    [Fact]
    public void MaximumEightHundredMapCellsHaveExactProtectedFootprint()
    {
        var original = Original(); var preview = Preview(Settings(original, 1023, allMapCells: true));
        Assert.Equal(800, preview.Plan.RequestedMapCellCount);
        Assert.Equal(800, preview.Plan.ChangedMapCellCount);
        Assert.Equal(10, preview.Plan.RequestedGroupCount); Assert.Equal(10, preview.Plan.ChangedGroupCount);
        Assert.InRange(preview.Plan.ExpectedDiff.Count, 841, 842);
        Assert.Equal(0, P28NativeChecksumArithmetic.Calculate(preview.Output).ComputedResult);
        var allowed = P28BasicCalibrationEditor.FieldBytes(preview.Plan.BasicGroups).Select(diff => diff.Offset)
            .Concat(Enumerable.Range(P28FuelMapContract.Map0Origin, 200))
            .Concat(Enumerable.Range(P28FuelMapContract.Map1Origin, 200))
            .Concat(Enumerable.Range(P28IgnitionMapContract.Map0Origin, 200))
            .Concat(Enumerable.Range(P28IgnitionMapContract.Map1Origin, 200)).Append(0x7FFF).ToHashSet();
        for (var offset = 0; offset < original.Size; offset++) if (!allowed.Contains(offset))
                Assert.Equal(original.Span[offset], preview.Output.Span[offset]);
    }

    [Fact]
    public void FamilyOnlyFirmwareIsByteEquivalentToClosedExporters()
    {
        var original = Original();
        foreach (var mask in new[] { 63, 192, 768 })
        {
            var settings = Settings(original, mask); var unified = Preview(settings).Output;
            RomImage expected = mask switch
            {
                63 => P28BasicCalibrationEditor.Compose(original, settings.Basic).C,
                192 => P28FuelMapExportEditor.Compose(original, settings.Fuel).C,
                _ => P28IgnitionMapExportEditor.Compose(original, settings.Ignition).C
            };
            Assert.Equal(expected.ToArray(), unified.ToArray());
        }
    }

    [Fact]
    public void ExplicitUnchangedEntriesRetainSelectionWithoutByteAuthority()
    {
        var original = Original(); var bytes = original.ToArray();
        var slot = P28ThresholdLogic.GetSlots()[0];
        var settings = new P28UnifiedCalibrationSettings(
            new(new(slot.Id, bytes[slot.Offset]), null, null, null, null, null),
            new([new(0, 0, bytes[P28FuelMapContract.Map0Origin])], null),
            new(null, [new(19, 9, bytes[P28IgnitionMapContract.Map1Origin + P28IgnitionMapContract.CellCount - 1])]));
        var preview = Preview(settings);
        Assert.True(preview.Plan.IsNoOp); Assert.Empty(preview.Plan.ExpectedDiff);
        Assert.Equal(3, preview.Plan.RequestedGroupCount); Assert.Equal(0, preview.Plan.ChangedGroupCount);
        Assert.Equal(2, preview.Plan.RequestedMapCellCount); Assert.Equal(0, preview.Plan.ChangedMapCellCount);
        Assert.All(preview.Plan.Groups.Where(group => group.Requested), group =>
        {
            Assert.False(group.ByteChanged); Assert.False(group.BehaviorChanged);
        });
    }

    [Fact]
    public void CrossFamilyZeroResidueDoesNotInventCompensationChange()
    {
        var original = Original();
        var bytes = original.ToArray();
        var fuel = bytes[P28FuelMapContract.Map0Origin];
        var ignition = bytes[P28IgnitionMapContract.Map0Origin];
        var delta = fuel == 255 ? -1 : 1;
        var settings = new P28UnifiedCalibrationSettings(
            new(null, null, null, null, null, null),
            new([new(0, 0, fuel + delta)], null),
            new([new(0, 0, ignition - delta)], null));
        var preview = Preview(settings);
        Assert.Equal(0, preview.Plan.ResidueB);
        Assert.Equal(preview.Plan.Compensation.OldByte, preview.Plan.Compensation.NewByte);
        Assert.Equal(2, preview.Plan.ExpectedDiff.Count);
        Assert.Equal(preview.Intermediate.ToArray(), preview.Output.ToArray());
    }

    [Fact]
    public void NoOpTamperingAndSerializedCapabilitiesAreRejected()
    {
        var original = Original(); var noOp = Preview(Settings(original, 0));
        Assert.True(noOp.Plan.IsNoOp); Assert.Empty(noOp.Plan.ExpectedDiff);
        var plan = Preview().Plan;
        foreach (var edit in new Action<JsonNode>[]
        {
            node => node["contractId"] = "raw-patch",
            node => node["groups"]![6]!["id"] = "axis",
            node => node["fuelMaps"]![0]!["cells"]![0]!["offset"] = 0x7000,
            node => node["compensation"]!["offset"] = 0x6000,
            node => node["residueC"] = 1,
            node => node["requestedMapCellCount"] = 799,
            node => node["physicalDegreesAvailable"] = true
        })
        {
            var node = JsonNode.Parse(plan.ToJson())!; edit(node);
            Assert.ThrowsAny<Exception>(() => P28UnifiedCalibrationPlan.Parse(node.ToJsonString()));
        }
        Assert.Empty(typeof(P28VerifiedUnifiedCalibrationExport).GetConstructors());
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedUnifiedCalibrationExport>("{}"));
        Assert.Throws<InvalidDataException>(() => P28UnifiedCalibrationPlan.Parse(new string(' ',
            P28UnifiedCalibrationPlan.MaximumBytes + 1)));
        Assert.Throws<InvalidDataException>(() => P28UnifiedCalibrationReceipt.Parse(new string(' ',
            P28UnifiedCalibrationReceipt.MaximumBytes + 1)));

        var snapshot = Preview();
        var exposed = Assert.IsAssignableFrom<IList<P28UnifiedCalibrationGroup>>(snapshot.Plan.Groups);
        exposed[0] = exposed[0] with { Family = "forged" };
        Assert.Equal("basic", snapshot.Plan.Groups[0].Family);
        var extraZeroSum = JsonNode.Parse(plan.ToJson())!;
        extraZeroSum["expectedDiff"]!.AsArray().Add(new JsonObject
        {
            ["offset"] = 0x6001,
            ["oldByte"] = 0,
            ["newByte"] = 1
        });
        Assert.ThrowsAny<Exception>(() => P28UnifiedCalibrationPlan.Parse(extraZeroSum.ToJsonString()));
    }

    [Fact]
    public async Task CancellationPrecedesRunnerAndNoOpPublicationChecks()
    {
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            P28UnifiedCalibrationExecution.ValidateAsync(Preview(), "missing", cancellationToken: cancellation.Token));
    }
}
