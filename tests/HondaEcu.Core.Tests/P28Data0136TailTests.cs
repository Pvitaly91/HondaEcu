using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28Data0136TailTests
{
    internal static P28Data0136TailScenario Scenario() => P28Data0136TailScenario.Create(P28FallthroughData0136Tests.Scenario());
    [Fact]
    public void ReusesExactSourcesWithSeparatePurposeAndOperation()
    {
        var scenario = Scenario(); Assert.Equal(scenario.Digest, P28Data0136TailScenario.Parse(scenario.ToJson()).Digest);
        var node = JsonNode.Parse(scenario.ToJson())!; node["purpose"] = P28FallthroughData0136Scenario.PurposeName;
        Assert.Equal(JsonNode.Parse(scenario.Reference.ToJson())!.ToJsonString(), node.ToJsonString());
        var request = JsonSerializer.SerializeToElement(P28Data0136TailValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), scenario), JsonDefaults.Create());
        Assert.Equal(P28Data0136TailValidator.Operation, request.GetProperty("operation").GetString());
        Assert.False(request.TryGetProperty("fallthroughData0136CallerHandoff", out _));
        Assert.Equal(new[] { "prefix", "producerObservation" }, request.GetProperty("data0136TailToTimerBoundary").GetProperty("calls")[0].EnumerateObject().Select(p => p.Name));
    }
    [Theory]
    [InlineData("tm3")]
    [InlineData("tmr3")]
    [InlineData("timerTicks")]
    [InlineData("tailBranch")]
    [InlineData("jleResult")]
    [InlineData("mulResult")]
    [InlineData("PSWL4")]
    [InlineData("data0136")]
    [InlineData("readerValue")]
    [InlineData("pointer")]
    [InlineData("PC")]
    [InlineData("SSP")]
    [InlineData("return0667")]
    [InlineData("expectedOutput")]
    [InlineData("arbitraryRAM")]
    [InlineData("initial019b2")]
    public void NoNewSemanticInput(string field)
    {
        var n = JsonNode.Parse(Scenario().ToJson())!; n["calls"]![0]![field] = 0;
        Assert.ThrowsAny<Exception>(() => P28Data0136TailScenario.Parse(n.ToJsonString()));
        n = JsonNode.Parse(Scenario().ToJson())!; n["initialState"]![field] = 0;
        Assert.ThrowsAny<Exception>(() => P28Data0136TailScenario.Parse(n.ToJsonString()));
    }
    [Fact]
    public void DuplicateNestedFieldsAreNotLostInPurposeProjection()
    {
        var json = Scenario().ToJson(); Assert.Contains("\"tmr2\":", json);
        Assert.ThrowsAny<Exception>(() => P28Data0136TailScenario.Parse(json.Replace("\"tmr2\":", "\"tmr2\": 1, \"tmr2\":")));
        Assert.ThrowsAny<Exception>(() => P28Data0136TailScenario.Parse(json.Replace("\"purpose\":", "\"purpose\": \"x\", \"purpose\":")));
    }
    [Theory]
    [InlineData(0)]
    [InlineData(0x4000)]
    [InlineData(0x8000)]
    [InlineData(0xC000)]
    [InlineData(0x2000)]
    public void IndependentPrefixOverwritesOnlyCompareFlagsAndNeverUses019bBranch(int flags)
    {
        // Fabricated model-only boundary, not an OEM execution or byte fixture.
        var before = JsonSerializer.SerializeToElement(new
        {
            pc = 0x5719,
            accumulator = 0xACED,
            psw = 0x1DCA | flags,
            dd = true,
            lrb = 0x21,
            x1 = 6,
            x2 = 0,
            dp = 0,
            usp = 0,
            ssp = 0x7FC,
            registers = new[] { 4, 0, 19, 0, 0, 0, 1, 2 }
        });
        var own = P28Data0136TailModel.Prefix(before);
        Assert.Equal(0x5722, own.After.GetProperty("pc").GetInt32());
        Assert.Equal((before.GetProperty("psw").GetInt32() & ~0xC000) | 0x8000, own.After.GetProperty("psw").GetInt32());
        Assert.Equal(0xACED, own.After.GetProperty("accumulator").GetInt32());
        Assert.Equal(0x7FC, own.After.GetProperty("ssp").GetInt32());
        Assert.Equal(new[] { 0, 0x5719, 0xA2, 8, 0, 0 }, Assert.Single(own.All));
        Assert.Equal(2, own.Steps.Count); Assert.Equal(0, own.All.Count(v => v[4] == 1));
    }
    [Fact]
    public void NoHistoricalM2agExtensionInContract()
    {
        var old = P28FallthroughData0136Validator.ExpectedContracts()[0]; Assert.Equal(0x5719, old.GetProperty("stopBefore").GetInt32());
        var next = P28Data0136TailValidator.ExpectedContracts()[0]; Assert.Equal(0x5722, next.GetProperty("liveInBoundary")[0].GetInt32());
        Assert.Equal(0x5793, next.GetProperty("goalBoundary").GetInt32()); Assert.Empty(next.GetProperty("newPeripheralSources").EnumerateArray());
    }
    [Fact]
    public void Historical039IdentityCannotClaimNewTail()
    {
        var root = JsonSerializer.SerializeToElement(new { runnerVersion = "0.39.0" });
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(root, P28Data0136TailValidator.Operation));
    }
}
