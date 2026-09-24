using System.Text.Json;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28IgnitionSelectorTests
{
    private static P28IgnitionSelectorScenario Scenario() => P28IgnitionSelectorScenario.Create(
        new(new(0, 0, 0, 0, 0, 0, 0xA5, 0, 77), 0),
        [new(0, 0, 0, 0, 0), new(1, 0x40, 255, 255, 1), new(2, 0x80, 57, 92, 16)],
        [0, 2], "Invented closed M2g software-input test.");

    [Fact]
    public void ScenarioRejectsPerEventMapSelectorRamAndExpectedResult()
    {
        var scenario = Scenario();
        Assert.Equal(scenario.Digest, P28IgnitionSelectorScenario.Parse(scenario.ToJson()).Digest);
        foreach (var inject in new Action<JsonNode>[]
        {
            node => node["calls"]![0]!["mapId"] = "ignition_map_1",
            node => node["calls"]![0]!["selector0227"] = 32,
            node => node["calls"]![0]!["ram"] = new JsonObject(),
            node => node["calls"]![0]!["expectedLookup"] = 1,
            node => node["calls"]![0]!["loadFraction"] = 123,
            node => node["calls"]![0]!["index"] = 99,
        })
        {
            var node = JsonNode.Parse(scenario.ToJson())!; inject(node);
            Assert.Throws<InvalidDataException>(() => P28IgnitionSelectorScenario.Parse(node.ToJsonString()));
        }
    }

    [Fact]
    public void IndependentModelOverwritesInitialOneAndPreservesNeighborsAndCaches()
    {
        var model = new P28IgnitionSelectorModel(P28IgnitionMapTests.InventedImage(), Scenario().Initial);
        var scenario = Scenario();
        var first = model.Step(scenario.Calls[0]);
        Assert.Equal(0xA5, first.Before.Selector0227);
        Assert.Equal(0x85, first.SelectorAfterProducer);
        Assert.Equal("ignition_map_0", first.Ignition.SelectedMap);
        Assert.Equal([0x60FB, 0x60EA], first.ProducerProgramReads);
        var second = model.Step(scenario.Calls[1]);
        Assert.Equal(first.Ignition.After, second.Before);
        Assert.Equal(0x85, second.Ignition.After.Selector0227);
        Assert.Equal(18, second.Ignition.Map0Rpm.Index);
        Assert.Equal(0, second.Ignition.Map1Rpm.Index);
    }

    [Theory]
    [InlineData("0.14.0", "ignitionSelectorChain")]
    [InlineData("0.15.0", "ignitionMapLookup")]
    public void NewTaskRequiresItsOwnRunnerVersionAndOperation(string version, string operation)
    {
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(new
        {
            protocolVersion = 1,
            operation,
            runnerVersion = version,
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = Array.Empty<string>(),
        }));
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(document.RootElement,
            P28IgnitionSelectorValidator.Operation));
    }

    [Fact]
    public async Task ActualRustSubprocessRunsInventedSourceWriterAndSelectedReader()
    {
        var bytes = new byte[32768];
        // Fully invented program. It does not reproduce the OEM producer or helpers.
        new byte[] { 0x62, 0xC7, 0x03, 0xF2, 0x53, 0xC4, 0x27, 0x3D,
            0x03, 0xAF, 0x5F }.CopyTo(bytes, 0x5F93);
        new byte[] { 0xCB, 0x54 }.CopyTo(bytes, 0x0A0C);
        new byte[] { 0xED, 0x27, 0x05, 0x60, 0xE4, 0x72, 0xCB, 0x43,
            0x60, 0xAC, 0x73, 0xCB, 0x3E }.CopyTo(bytes, 0x0B64);
        new byte[] { 0x90, 0xAA, 0xCB, 0x01 }.CopyTo(bytes, 0x0BAF);
        new byte[] { 0xD4, 0x48, 0xCB, 0x1C }.CopyTo(bytes, 0x0BB4);
        bytes[0x72E4] = 0x11; bytes[0x73AC] = 0x22;
        var scenario = P28IgnitionSelectorScenario.Create(
            new(new(0, 0, 0, 0, 0, 0, 0x20, 0, 0), 0),
            [new(0, 0, 0, 0, 0), new(1, 0x80, 0, 0, 0)], [0, 1], "Invented native writer-reader Rust subprocess.");
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner,
            P28IgnitionSelectorValidator.CreateRequest(RomImage.FromBytes(bytes), null, scenario));
        var root = response.Response;
        Assert.Equal("0.16.0", root.GetProperty("runnerVersion").GetString());
        var cps = root.GetProperty("ignitionSelectorSequences")[0].GetProperty("checkpoints");
        Assert.Equal(2, cps.GetArrayLength());
        Assert.True(cps[0].GetProperty("status").GetInt32() == 0,
            cps[0].GetProperty("error").ToString() + " " + cps[0].GetProperty("producer").GetProperty("result").GetProperty("error"));
        Assert.True(cps[1].GetProperty("status").GetInt32() == 0,
            cps[1].GetProperty("error").ToString());
        Assert.Equal(0, cps[0].GetProperty("stateAfter").GetProperty("selector0227").GetByte() & 0x20);
        Assert.Equal(0x20, cps[1].GetProperty("stateAfter").GetProperty("selector0227").GetByte() & 0x20);
        Assert.Equal(0x72E4, cps[0].GetProperty("selectedOrigin").GetInt32());
        Assert.Equal(0x73AC, cps[1].GetProperty("selectedOrigin").GetInt32());
        Assert.Equal(0x11, cps[0].GetProperty("consumerOutput").GetInt32());
        Assert.Equal(0x22, cps[1].GetProperty("consumerOutput").GetInt32());
    }

    [Fact]
    public async Task UnresolvedProducerLeavesLaterEventInputAndOutputsNotRun()
    {
        var bytes = new byte[32768];
        bytes[0x5F93] = 0xFF; // Invented unsupported producer instruction, not an OEM byte.
        var scenario = P28IgnitionSelectorScenario.Create(
            new(new(0, 0, 0, 0, 0, 0, 0xA5, 0, 19), 0),
            [new(0, 7, 0, 0, 0), new(1, 0x80, 255, 255, 255)], [], "Invented terminal suffix.");
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner,
            P28IgnitionSelectorValidator.CreateRequest(RomImage.FromBytes(bytes), null, scenario));
        var cps = response.Response.GetProperty("ignitionSelectorSequences")[0].GetProperty("checkpoints");
        Assert.Equal(1, cps[0].GetProperty("status").GetInt32());
        Assert.Equal(4, cps[1].GetProperty("status").GetInt32());
        Assert.Equal(JsonValueKind.Null, cps[1].GetProperty("input").ValueKind);
        Assert.Equal(JsonValueKind.Null, cps[1].GetProperty("sourceAfterInputs").ValueKind);
        Assert.Equal(JsonValueKind.Null, cps[1].GetProperty("lookup").ValueKind);
        Assert.Equal(JsonValueKind.Null, cps[1].GetProperty("consumerOutput").ValueKind);
        Assert.Equal(19, cps[1].GetProperty("stateAfter").GetProperty("consumerOutput0248").GetByte());
    }

    [Fact]
    public async Task TimeoutAndCancellationDoNotProduceAnM2gResult()
    {
        var invented = P28IgnitionMapTests.InventedImage(true).ToArray();
        invented[0x5F93] = 0x62; invented[0x5F98] = 0x95; invented[0x5F99] = 0x90;
        invented[0x5FA0] = 0x90; invented[0x5FA4] = 0xC9; invented[0x5FAC] = 0xC4;
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(invented);
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin",
            new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        Assert.True(File.Exists(host));
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(500) };
        var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => P28IgnitionSelectorValidator.ExecuteAsync(
            image, profile, binding, true, "dotnet", Scenario(), options));
        Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
        using var cancellation = new CancellationTokenSource(500);
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28IgnitionSelectorValidator.ExecuteAsync(
            image, profile, binding, true, "dotnet", Scenario(), options with { Timeout = TimeSpan.FromSeconds(15) },
            cancellation.Token));
    }
}
