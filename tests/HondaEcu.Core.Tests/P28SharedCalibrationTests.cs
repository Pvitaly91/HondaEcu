using System.Text.Json;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28SharedCalibrationTests
{
    private static P28SharedCalibrationScenario Scenario(P28SharedMutation? mutation = null)
    {
        var vtec = P28StatefulModelTests.Initial();
        var first = P28StatefulModelTests.Call() with { Enabled = false, FastTicks = 1, SlowTicks = 1 };
        return P28SharedCalibrationScenario.Create(
            new(vtec, new(7, 6, 16, 3, 123, 456, 789, 200), 0xA5, 0, 77, 0, 90, 85),
            [new(0, 0, 60, 80, 33, first),
                new(1, 0xC0, 255, 255, 0, first with { Index = 1, FastTicks = 0, SlowTicks = 0 }),
                new(2, 0, 60, 80, 33, first with { Index = 2, FastTicks = 0, SlowTicks = 0 })],
            [0, 2], "Invented shared-axis software snapshots.", mutation);
    }

    private static RomImage Image()
    {
        var bytes = P28StatefulModelTests.Data();
        for (var c = 0; c < 10; c++) bytes[P28FuelMapContract.LoadAxisOrigin + c] = (byte)(c == 9 ? 0 : c * 25);
        for (var r = 0; r < 20; r++)
        {
            bytes[P28FuelMapContract.Map0RpmAxisOrigin + r] = (byte)(r == 19 ? 0 : r * 13);
            bytes[P28FuelMapContract.Map1RpmAxisOrigin + r] = (byte)(r == 19 ? 0 : r * 12);
        }
        foreach (var map in P28FuelMapContract.Maps)
        {
            for (var c = 0; c < 10; c++) bytes[map.MetadataOrigin + c] = (byte)(c + 2);
            for (var r = 0; r < 20; r++) for (var c = 0; c < 10; c++)
                    bytes[map.Origin + r * 10 + c] = (byte)(1 + r * 2 + c + (map.Id == "map_1" ? 50 : 0));
        }
        foreach (var map in P28IgnitionMapContract.Maps)
            for (var r = 0; r < 20; r++) for (var c = 0; c < 10; c++)
                    bytes[map.Origin + r * 10 + c] = (byte)(11 + r + c + (map.Id == "ignition_map_1" ? 25 : 0));
        bytes[0x60FB] = 0; bytes[0x60EA] = 0; bytes[0x7E02] = 0;
        return RomImage.FromBytes(bytes);
    }

    [Fact]
    public void OneModelOwnsSharedRpmCachesAndBothLoadCachesAcrossEvents()
    {
        var scenario = Scenario(); var model = new P28SharedCalibrationModel(Image(), scenario.Initial);
        var first = model.Step(scenario.Calls[0], false);
        Assert.Equal(0xA5, first.Before.Selector0227);
        Assert.Equal(0x85, first.AfterProducer.Selector0227);
        Assert.Equal(first.Map0Rpm.Index, first.AfterAxis.Axes.Map0RpmIndex);
        Assert.Equal(first.Map0Rpm.Fraction, first.AfterAxis.Axes.Map0RpmFraction);
        Assert.Equal(first.IgnitionLoad.Index, first.AfterAxis.Axes.IgnitionLoadIndex);
        Assert.Equal(first.FuelLoad.Index, first.AfterAxis.Axes.FuelLoadIndex);
        Assert.NotEqual(first.IgnitionLoad.IndexBefore, first.FuelLoad.IndexBefore);
        Assert.Equal(first.IgnitionLoad.Fraction, first.FuelLoad.Fraction);
        Assert.Equal(0, first.Decision.Status);
        Assert.Equal(P28IgnitionMapContract.Map0Origin, first.IgnitionOrigin);
        Assert.Equal(P28FuelMapContract.Map0Origin, first.FuelOrigin);
        var second = model.Step(scenario.Calls[1], false);
        Assert.Equal(first.After, second.Before);
        Assert.Equal(18, second.After.Axes.Map0RpmIndex);
        Assert.Equal(8, second.After.Axes.IgnitionLoadIndex);
        Assert.Equal(8, second.After.Axes.FuelLoadIndex);
        var third = model.Step(scenario.Calls[2], false);
        Assert.Equal(second.After, third.Before);
        Assert.Equal(first.After.Axes.Map0RpmIndex, third.After.Axes.Map0RpmIndex);
        Assert.Equal(0x85, third.After.Selector0227);
    }

    [Fact]
    public void ScenarioIsClosedAndNeverAcceptsPreparedSharedStatePerEvent()
    {
        var scenario = Scenario(new("ignitionCell", null, "ignition_map_0", 0, 0, 55));
        Assert.Equal(scenario.Digest, P28SharedCalibrationScenario.Parse(scenario.ToJson()).Digest);
        Assert.Equal(P28IgnitionMapContract.Map0Origin, scenario.Mutation!.Offset);
        var request = JsonSerializer.SerializeToNode(P28SharedCalibrationValidator.CreateRequest(Image(), null, scenario),
            JsonDefaults.Create(false))!;
        Assert.Equal("vtecFuelIgnitionChain", request["operation"]!.GetValue<string>());
        Assert.Null(request["sharedCalibrationChain"]!["calls"]![0]!["mapId"]);
        foreach (var field in new[] { "mapId", "selector0227", "selector0127", "p1", "rpmIndex", "fuelRawLoad",
            "expectedLookup", "pc" })
        {
            var node = JsonNode.Parse(scenario.ToJson())!;
            node["calls"]![0]![field] = 1;
            Assert.Throws<InvalidDataException>(() => P28SharedCalibrationScenario.Parse(node.ToJsonString()));
        }
        Assert.Throws<ArgumentException>(() => P28SharedCalibrationValidator.ValidateAssumptions(["oki.add-er3-a"]));
        Assert.ThrowsAny<Exception>(() => P28SharedCalibrationScenario.Create(scenario.Initial,
            scenario.Calls, [], "invented", new("ignitionCell", null, "ignition_map_1", 0, 0, 55)));
    }

    [Theory]
    [InlineData("0.14.0")]
    [InlineData("0.15.0")]
    public void OlderRunnerCannotClaimNewOperation(string version)
    {
        using var doc = JsonDocument.Parse(JsonSerializer.Serialize(new
        {
            protocolVersion = 1,
            operation = P28SharedCalibrationValidator.Operation,
            runnerVersion = version,
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = Array.Empty<string>(),
        }));
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(doc.RootElement,
            P28SharedCalibrationValidator.Operation));
    }

    [Fact]
    public void EqualOutputsCannotHideAnInsertedHostResetAtContinuousTailBoundary()
    {
        using var valid = JsonDocument.Parse("""
            {"ignitionSelectionExit":{"pc":2991,"psw":257,"lrb":64,"ssp":2046,"registers":[1,2,3]},
             "ignitionLookupEntry":{"pc":2991,"psw":257,"lrb":64,"ssp":2046,"registers":[1,2,3]},
             "ignitionOutput":90,"fuelOutput":16}
            """);
        Assert.True(P28SharedCalibrationValidator.SameBoundary(valid.RootElement,
            "ignitionSelectionExit", "ignitionLookupEntry"));
        using var reset = JsonDocument.Parse("""
            {"ignitionSelectionExit":{"pc":2991,"psw":257,"lrb":64,"ssp":2046,"registers":[1,2,3]},
             "ignitionLookupEntry":{"pc":2991,"psw":257,"lrb":64,"ssp":2046,"registers":[0,0,0]},
             "ignitionOutput":90,"fuelOutput":16}
            """);
        Assert.False(P28SharedCalibrationValidator.SameBoundary(reset.RootElement,
            "ignitionSelectionExit", "ignitionLookupEntry"));
        Assert.Equal(valid.RootElement.GetProperty("ignitionOutput").GetInt32(),
            reset.RootElement.GetProperty("ignitionOutput").GetInt32());
        Assert.Equal(valid.RootElement.GetProperty("fuelOutput").GetInt32(),
            reset.RootElement.GetProperty("fuelOutput").GetInt32());
    }
}
