using System.Text.Json;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28IgnitionMapExportTests
{
    internal static P28IgnitionMapExportPreview Preview(P28IgnitionMapExportSettings? settings = null,
        byte[]? source = null)
    {
        var bytes = source ?? P28IgnitionMapTests.InventedImage(true).ToArray();
        bytes[0x6000] = 0; bytes[0x6000] = unchecked((byte)-bytes.Sum(value => (int)value));
        var original = RomImage.FromBytes(bytes); var profile = new RomProfile("p28-304", "Invented ignition map",
            "Synthetic arithmetic only", 32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768,
            original.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        settings ??= new([new(0, 0, (original.Span[P28IgnitionMapContract.Map0Origin] + 1) & 255)], null);
        var (b, c, compensation) = P28IgnitionMapExportEditor.Compose(original, settings);
        var diff = P28FixedLimiterEditor.Diff(original, c);
        var plan = new P28IgnitionMapExportPlan(1, P28IgnitionMapExportEditor.Purpose,
            P28IgnitionMapExportEditor.ContractId, original.Hash, original.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding),
            P28IgnitionMapExportEditor.Describe(original, settings, b), P28IgnitionMapExportEditor.AuditConsumer(),
            P28IgnitionMapExportEditor.Immutable(original), "invented-not-authority", new string('a', 64),
            "invented", "invented bounded scope", P28IgnitionMapExportEditor.EditAudit, compensation, 0,
            P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash, diff, diff.Length == 0,
            P28IgnitionMapExportEditor.Scope, P28NativeChecksumArithmetic.Contract.Id, false,
            P28IgnitionMapExportEditor.Readiness);
        P28IgnitionMapExportEditor.Shape(plan);
        return new(original, profile, binding, null!, b, c, plan);
    }

    [Fact]
    public void SettingsAreClosedCanonicalAndPreserveNullVersusEmpty()
    {
        const string json = """{"formatVersion":1,"purpose":"explicit-ignition-map-cell-values","ignition_map_0":[{"row":2,"column":3,"rawValue":9},{"row":0,"column":1,"rawValue":8}],"ignition_map_1":[]}""";
        var settings = P28IgnitionMapExportSettings.Parse(json);
        Assert.Equal([(0, 1, 8), (2, 3, 9)], settings.IgnitionMap0!.Select(cell => (cell.Row, cell.Column, cell.RawValue)));
        Assert.NotNull(settings.IgnitionMap1); Assert.Empty(settings.IgnitionMap1!);
        Assert.Null(P28IgnitionMapExportSettings.Parse(json.Replace("\"ignition_map_1\":[]", "\"ignition_map_1\":null")).IgnitionMap1);
        foreach (var invalid in new[]
        {
            json.Replace(",\"ignition_map_1\":[]", ""),
            json.Replace("\"rawValue\":9", "\"rawValue\":9.0"),
            json.Replace("\"rawValue\":9", "\"rawValue\":256"),
            json.Replace("\"row\":2", "\"row\":20"),
            json.Replace("{\"row\":0,\"column\":1,\"rawValue\":8}", "{\"row\":2,\"column\":3,\"rawValue\":8}"),
            json.Replace("\"rawValue\":9", "\"rawValue\":9,\"offset\":29435"),
            json.Replace("\"purpose\":\"explicit-ignition-map-cell-values\"", "\"purpose\":\"degrees\"")
        }) Assert.ThrowsAny<Exception>(() => P28IgnitionMapExportSettings.Parse(invalid));
    }

    [Fact]
    public void AllFourHundredCoordinatesHaveExactPrimaryRowMajorFootprint()
    {
        var bytes = P28IgnitionMapTests.InventedImage(true).ToArray();
        var map0 = Enumerable.Range(0, 200).Select(index => new P28IgnitionMapCellSetting(index / 10,
            index % 10, (bytes[P28IgnitionMapContract.Map0Origin + index] + 1) & 255)).ToArray();
        var map1 = Enumerable.Range(0, 200).Select(index => new P28IgnitionMapCellSetting(index / 10,
            index % 10, (bytes[P28IgnitionMapContract.Map1Origin + index] + 1) & 255)).ToArray();
        var preview = Preview(new(map0, map1), bytes);
        Assert.Equal(400, preview.Plan.Maps.Sum(map => map.RequestedCellCount));
        Assert.Equal(400, preview.Plan.Maps.Sum(map => map.ChangedCellCount));
        Assert.InRange(preview.Plan.ExpectedDiff.Count, 400, 401);
        Assert.Equal(0, P28NativeChecksumArithmetic.Calculate(preview.Output).ComputedResult);
        var allowed = Enumerable.Range(P28IgnitionMapContract.Map0Origin, 200)
            .Concat(Enumerable.Range(P28IgnitionMapContract.Map1Origin, 200)).Append(0x7FFF).ToHashSet();
        for (var offset = 0; offset < 32768; offset++) if (!allowed.Contains(offset))
                Assert.Equal(preview.Original.Span[offset], preview.Output.Span[offset]);
    }

    [Fact]
    public void FullFiniteAuditsCoverMapsAndImmediateConsumer()
    {
        var bytes = P28IgnitionMapTests.InventedImage(true).ToArray();
        for (var index = 0; index < 200; index++) bytes[P28IgnitionMapContract.Map0Origin + index] =
            (byte)(index % 2 == 0 ? 0 : 255);
        bytes[0x6000] = 0; bytes[0x6000] = unchecked((byte)-bytes.Sum(value => (int)value));
        var image = RomImage.FromBytes(bytes);
        var audit = P28IgnitionMapExportEditor.AuditDomain(image, image,
            P28IgnitionMapContract.Map("ignition_map_0"));
        Assert.Equal(65536, audit.CheckedInputPairs); Assert.Equal(65536, audit.EqualResults);
        Assert.InRange(audit.MaximumInterpolationProduct, 1, (long)255 * ushort.MaxValue);
        Assert.True(audit.SequentialFixedPointVerified && audit.WideIntermediatesVerified && audit.Sentinel256Verified);
        var consumer = P28IgnitionMapExportEditor.AuditConsumer();
        Assert.Equal(65536, consumer.CheckedInputPairs); Assert.Equal(65025, consumer.MaximumProduct);
        Assert.Equal(256, consumer.BypassPairs); Assert.Equal(65280, consumer.ScalingPairs);
        Assert.Equal(255, consumer.MaximumOutput);
    }

    [Fact]
    public void ZeroSumAndExplicitEmptySelectionsDoNotInventAuthorityOrCompensation()
    {
        var zeroSum = Preview(new([new(0, 0, 2)], [new(0, 0, 30)]));
        Assert.Equal(0, zeroSum.Plan.ResidueB);
        Assert.Equal(zeroSum.Plan.Compensation.OldByte, zeroSum.Plan.Compensation.NewByte);
        Assert.Equal(2, zeroSum.Plan.ExpectedDiff.Count);
        Assert.Equal(zeroSum.Intermediate.ToArray(), zeroSum.Output.ToArray());

        var empty = Preview(new([], null));
        Assert.True(empty.Plan.Maps[0].Requested); Assert.False(empty.Plan.Maps[0].EffectivelyChanged);
        Assert.False(empty.Plan.Maps[1].Requested); Assert.True(empty.Plan.IsNoOp);
        Assert.Empty(empty.Plan.ExpectedDiff);
    }

    [Fact]
    public void MandatoryCorporaCoverAllCellsHistoryAndOnceSeededFactors()
    {
        var preview = Preview(new([new(0, 0, 9), new(19, 9, 7)], [new(8, 4, 201)]));
        var scenario = P28IgnitionMapExportCorpus.Create(preview);
        Assert.InRange(scenario.Calls.Count, 400, 512); Assert.Equal(0, scenario.InitialState.ConsumerFactor0247);
        foreach (var mapId in new[] { "ignition_map_0", "ignition_map_1" })
        {
            var read = new HashSet<int>(); var model = new P28IgnitionMapModel(preview.Original, scenario.InitialState);
            foreach (var call in scenario.Calls)
            {
                var step = model.Step(call); if (call.MapId == mapId) read.UnionWith(step.Operands.CellAddresses);
            }
            var map = P28IgnitionMapContract.Map(mapId);
            Assert.Equal(200, read.Count(address => address >= map.Origin && address <= map.EndInclusive));
        }
        foreach (var factor in new[] { 1, 127, 128, 173, 255 })
        {
            var factorScenario = P28IgnitionMapExportCorpus.CreateFactor(preview, factor);
            Assert.Equal(factor, factorScenario.InitialState.ConsumerFactor0247);
            Assert.Contains("once-seeded", factorScenario.Provenance);
            Assert.InRange(factorScenario.Calls.Count, 6, 10);
        }
    }

    [Fact]
    public void ForgedPlansAndCapabilityConstructionAreRejected()
    {
        var plan = Preview().Plan;
        foreach (var edit in new Action<JsonNode>[]
        {
            node => node["contractId"] = "raw-patch",
            node => node["maps"]![0]!["cells"]![0]!["offset"] = 0x7000,
            node => node["maps"]![0]!["domainAudit"]!["checkedInputPairs"] = 255,
            node => node["consumerAudit"]!["checkedInputPairs"] = 255,
            node => node["maps"]![0]!["requested"] = false,
            node => node["compensation"]!["offset"] = 0x60FB,
            node => node["residueC"] = 1,
            node => node["physicalUnitsAvailable"] = true,
            node => node["expectedDiff"]![0]!["offset"] = 0x7474,
            node => node["isNoOp"] = true
        })
        {
            var node = JsonNode.Parse(plan.ToJson())!; edit(node);
            Assert.ThrowsAny<Exception>(() => P28IgnitionMapExportPlan.Parse(node.ToJsonString()));
        }
        Assert.Empty(typeof(P28VerifiedIgnitionMapExport).GetConstructors());
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedIgnitionMapExport>("{\"nativeValidationComplete\":true}"));
    }
}
