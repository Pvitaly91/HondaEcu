using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28VtecFuelModelTests
{
    private static RomImage InventedImage(bool layoutGuard = false)
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
        if (layoutGuard)
        {
            bytes[0x0A0C] = 0x60; bytes[0x0A0D] = 0x14; bytes[0x0A0E] = 0x70;
            bytes[0x0A24] = 0x60; bytes[0x0A25] = 0x28; bytes[0x0A26] = 0x70;
            bytes[0x0A65] = 0x60; bytes[0x0A66] = 0x00; bytes[0x0A67] = 0x70;
            bytes[0x12FC] = 0x98; bytes[0x12FD] = 10; bytes[0x12FE] = 0x99; bytes[0x12FF] = 20;
            bytes[0x130C] = 0x60; bytes[0x130D] = 0x22; bytes[0x130E] = 0x71;
            bytes[0x1323] = 0x60; bytes[0x1324] = 0x50; bytes[0x1325] = 0x70;
            bytes[0x131A] = 0xE9; bytes[0x131B] = 0x27;
            bytes[0x12DF] = 0xC4; bytes[0x12E0] = 0x27; bytes[0x12E1] = 0x09;
            bytes[0x12F9] = 0xC4; bytes[0x12FA] = 0x27; bytes[0x12FB] = 0x19;
        }
        return RomImage.FromBytes(bytes);
    }
    private static P28VtecFuelScenario Scenario(P28VtecFuelMutation? mutation = null)
    {
        var first = P28StatefulModelTests.Call();
        return P28VtecFuelScenario.Create(P28StatefulModelTests.Initial(), new(0, 0, 0, 0, 0, 0, 0, 0),
            [new(0, 60, 80, 80, first), new(1, 60, 80, 80, first with { Index = 1, FastTicks = 2, SlowTicks = 1 })],
            "Invented software-only M2f test", mutation, [1]);
    }

    [Fact]
    public void DecisionOwnedSelectorFeedsFuelModelWithoutRequestOrMapIdSubstitution()
    {
        var image = InventedImage(); var scenario = Scenario();
        var vtec = new P28StatefulModel(image.Span, scenario.InitialVtec);
        var fuel = new P28FuelMapModel(image, new(0, 0, 0, 0, 0, 0, scenario.InitialVtec.Data0127, 0, 0));
        var firstDecision = vtec.Step(scenario.Calls[0].Decision, true);
        Assert.True(firstDecision.SoftwareRequest); Assert.False(firstDecision.SelectionStatus);
        Assert.Equal(4, firstDecision.After.Data0127 & 4);
        var firstFuel = fuel.StepFromNativeSelector(new(0, 60, 80, 80), firstDecision.After.Data0127);
        Assert.Equal("map_0", firstFuel.SelectedMap);
        Assert.Equal(firstDecision.After.Data0127, firstFuel.After.Selector0127);
        var secondDecision = vtec.Step(scenario.Calls[1].Decision, true);
        Assert.True(secondDecision.SoftwareRequest); Assert.True(secondDecision.SelectionStatus);
        var secondFuel = fuel.StepFromNativeSelector(new(1, 60, 80, 80), secondDecision.After.Data0127);
        Assert.Equal("map_1", secondFuel.SelectedMap);
        Assert.Equal(firstFuel.After, secondFuel.Before);
        Assert.NotEqual(firstFuel.Operands.LookupResult, secondFuel.Operands.LookupResult);
        Assert.Equal(firstFuel.Load.Index, secondFuel.Load.Index);
        Assert.Equal(firstFuel.Map0Rpm.Index, secondFuel.Map0Rpm.Index);
        Assert.Equal(firstFuel.Map1Rpm.Index, secondFuel.Map1Rpm.Index);
    }

    [Fact]
    public void ScenarioIsClosedBoundedAndNeverCarriesPerEventSelectorOrMapId()
    {
        var scenario = Scenario(new("fuelCell", null, "map_1", 19, 9, 201));
        Assert.Equal(P28FuelMapContract.CellOffset("map_1", 19, 9), scenario.Mutation!.Offset);
        Assert.Equal(scenario.Digest, P28VtecFuelScenario.Parse(scenario.ToJson()).Digest);
        var request = JsonSerializer.SerializeToNode(P28VtecFuelValidator.CreateRequest(InventedImage(), null, scenario), JsonDefaults.Create(false))!;
        Assert.Equal("vtecFuelChain", request["operation"]!.GetValue<string>());
        Assert.Null(request["vtecFuelChain"]!["calls"]![0]!["mapId"]);
        Assert.Null(request["vtecFuelChain"]!["calls"]![0]!["selector0127"]);
        Assert.Equal(0x80, request["vtecFuelChain"]!["initialVtec"]!["data0127"]!.GetValue<int>());
        foreach (var extra in new[] { "mapId", "selector0127", "expectedResult", "rpmIndex", "pc" })
        {
            var node = JsonNode.Parse(scenario.ToJson())!;
            node["calls"]![0]![extra] = 1;
            Assert.ThrowsAny<Exception>(() => P28VtecFuelScenario.Parse(node.ToJsonString()));
        }
        var invalid = JsonNode.Parse(scenario.ToJson())!;
        invalid["calls"]![0]!["decision"]!["snapshot011C"] = 32;
        Assert.Throws<InvalidDataException>(() => P28VtecFuelScenario.Parse(invalid.ToJsonString()));
        Assert.Throws<ArgumentException>(() => P28VtecFuelValidator.ValidateAssumptions(["oki.add-er3-a"]));
        Assert.ThrowsAny<Exception>(() => P28VtecFuelScenario.Create(scenario.InitialVtec, scenario.InitialFuel,
            scenario.Calls, "test", new("fuelCell", null, "map_0", 20, 0, 1)));
        var offset = JsonNode.Parse(scenario.ToJson())!;
        offset["mutation"]!["offset"] = P28FuelMapContract.Map1Origin;
        Assert.Throws<InvalidDataException>(() => P28VtecFuelScenario.Parse(offset.ToJsonString()));
        var version = JsonNode.Parse(scenario.ToJson())!;
        version["formatVersion"] = 2;
        Assert.Throws<InvalidDataException>(() => P28VtecFuelScenario.Parse(version.ToJsonString()));
    }

    [Fact]
    public void TwoIndependentInMemoryEditsAreCodeOwnedAndNeverChained()
    {
        var image = InventedImage(); var threshold = new P28VtecFuelMutation("vtecThreshold",
            P28ThresholdLogic.GetSlotId(0, 0, false), null, null, null, 99);
        var cell = new P28VtecFuelMutation("fuelCell", null, "map_1", 0, 0, 99);
        Assert.InRange(threshold.Offset, P28ThresholdLogic.BlockOffset, P28ThresholdLogic.BlockOffset + 7);
        Assert.Equal(P28FuelMapContract.Map1Origin, cell.Offset);
        var a = image.ToArray(); var b1 = image.ToArray(); var b2 = image.ToArray();
        b1[threshold.Offset] = threshold.Value; b2[cell.Offset] = cell.Value;
        Assert.Equal([threshold.Offset], Enumerable.Range(0, a.Length).Where(i => a[i] != b1[i]));
        Assert.Equal([cell.Offset], Enumerable.Range(0, a.Length).Where(i => a[i] != b2[i]));
        Assert.Equal(a[cell.Offset], b1[cell.Offset]);
        Assert.Equal(a[threshold.Offset], b2[threshold.Offset]);
    }

    [Fact]
    public void OldD2RunnerCannotClaimTheNewCompiledM2fOperation()
    {
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(new
        {
            protocolVersion = 1, operation = P28VtecFuelValidator.Operation, runnerVersion = "0.13.0",
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit, localSemanticFixes = Array.Empty<string>(),
        }));
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(document.RootElement, P28VtecFuelValidator.Operation));
    }

    [Fact]
    public async Task M2fReusesBoundedProcessTimeoutAndCancellation()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(InventedImage(true).ToArray());
        var configuration = new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin",
            configuration, "net8.0", "HondaEcu.Slice.TestHost.dll");
        Assert.True(File.Exists(host));
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(500) };
        var failure = await Assert.ThrowsAsync<SliceProcessException>(() => P28VtecFuelValidator.ExecuteAsync(
            image, profile, binding, true, "dotnet", Scenario(), options: options));
        Assert.Equal(SliceProcessFailure.Timeout, failure.Failure);
        using var cancellation = new CancellationTokenSource(500);
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28VtecFuelValidator.ExecuteAsync(
            image, profile, binding, true, "dotnet", Scenario(), options: options with { Timeout = TimeSpan.FromSeconds(15) },
            cancellationToken: cancellation.Token));
    }
}
