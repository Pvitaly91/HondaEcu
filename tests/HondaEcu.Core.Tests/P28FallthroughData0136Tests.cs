using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28FallthroughData0136Tests
{
    internal static P28FallthroughData0136Scenario Scenario() => P28FallthroughData0136Scenario.Create(P28PostReturnSelectorTests.Scenario(), P28PostReturnSelectorTests.Scenario().Calls.Select(_ => new P28FrozenNoWriteObservation(0x8123, null)).ToArray());
    [Fact]
    public void ClosedScenarioUsesExistingSourcesAndOnlyConditionalFrozenObservation()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28FallthroughData0136Scenario.Parse(s.ToJson()).Digest);
        var r = JsonSerializer.SerializeToElement(P28FallthroughData0136Validator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal("fallthroughData0136CallerHandoff", r.GetProperty("operation").GetString());
        Assert.False(r.TryGetProperty("postReturnSelectorHandoff", out _));
        foreach (var c in r.GetProperty("fallthroughData0136CallerHandoff").GetProperty("calls").EnumerateArray())
        { Assert.Equal(new[] { "prefix", "producerObservation" }, c.EnumerateObject().Select(p => p.Name)); Assert.Equal(new[] { "tmr2" }, c.GetProperty("producerObservation").EnumerateObject().Select(p => p.Name)); }
    }
    [Theory]
    [InlineData("slot")]
    [InlineData("initial011f")]
    [InlineData("initial012a0")]
    [InlineData("initial012a3")]
    [InlineData("bit011b7")]
    [InlineData("branch064c")]
    [InlineData("branch064f")]
    [InlineData("forceCal")]
    [InlineData("pc064c")]
    [InlineData("pc065f")]
    [InlineData("pc0664")]
    [InlineData("pc56be")]
    [InlineData("ssp")]
    [InlineData("returnPc")]
    [InlineData("expected0136")]
    [InlineData("ready0136")]
    [InlineData("writer")]
    [InlineData("ram")]
    [InlineData("irqTrigger")]
    [InlineData("elapsedTime")]
    public void NoCallerGateSlotAbiOrReadyResultInput(string field)
    {
        var n = JsonNode.Parse(Scenario().ToJson())!; n["calls"]![0]![field] = 1;
        Assert.ThrowsAny<Exception>(() => P28FallthroughData0136Scenario.Parse(n.ToJsonString()));
        n = JsonNode.Parse(Scenario().ToJson())!; n["initialState"]![field] = 1;
        Assert.ThrowsAny<Exception>(() => P28FallthroughData0136Scenario.Parse(n.ToJsonString()));
    }
    [Fact]
    public void NoDefaultIrqhOrTcon2Source()
    {
        Assert.ThrowsAny<Exception>(() => new P28FrozenNoWriteObservation(0x8123, 0).Validate());
        Assert.ThrowsAny<Exception>(() => new P28FrozenNoWriteObservation(123, null).Validate());
        var n = JsonNode.Parse(Scenario().ToJson())!; n["calls"]![0]!["producerObservation"]!["tcon2"] = 0;
        Assert.ThrowsAny<Exception>(() => P28FallthroughData0136Scenario.Parse(n.ToJsonString()));
    }
    [Theory]
    [InlineData("0.38.0")]
    [InlineData("0.37.0")]
    public void HistoricalRunnerCannotClaimNewCaller(string version) => Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28FallthroughData0136Validator.Operation));
    internal static JsonElement Before() => JsonSerializer.SerializeToElement(new { pc = 0x064C, accumulator = 0x2341, psw = 0x8DCA, dd = false, lrb = 0x21, x1 = 4, x2 = 0, dp = 0, usp = 0, ssp = 0x7E0, registers = new[] { 3, 0, 19, 0, 0, 0, 0, 0 } });
    internal static int[] Memory(bool direct = false) => P28FallthroughData0136Model.RetainedMemory(0, Before(), new() { [0x128] = 6, [0x12A] = 2 }, direct);
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void IndependentCallerDerivesRouteAndPendingNativeFrame(bool direct)
    {
        var own = P28FallthroughData0136Model.Caller(Before(), Memory(direct));
        Assert.Equal(direct ? "FallthroughDirectVia011B7" : "FallthroughVia012A0", own.Route);
        Assert.Equal(0x56BE, own.After.GetProperty("pc").GetInt32()); Assert.Equal(0x7DE, own.After.GetProperty("ssp").GetInt32());
        Assert.Equal(0x0667, P28FallthroughData0136Model.Word(own.Memory, 0x7E0));
        Assert.Equal(2, own.Memory[0x12A]); Assert.DoesNotContain(own.All, a => a[2] == 0x46);
        Assert.Equal(0x2341, own.After.GetProperty("accumulator").GetInt32()); Assert.Equal(0, own.After.GetProperty("usp").GetInt32());
    }
    [Theory]
    [InlineData(0x8000, -1)]
    [InlineData(123, 0)]
    [InlineData(456, 1)]
    [InlineData(0, 0)]
    public void IndependentNoWriteUsesFrozenReadsButPreservesSamplesAnd0136(int timer, int irq)
    {
        var caller = P28FallthroughData0136Model.Caller(Before(), Memory()); var memory = caller.Memory;
        P28FallthroughData0136Model.WriteWord(memory, 0x136, 0x6B29); P28FallthroughData0136Model.WriteWord(memory, 0x360, 0x7C31);
        var o = new P28FrozenNoWriteObservation((ushort)timer, irq < 0 ? null : (byte)irq);
        var body = P28FallthroughData0136Model.NoWrite(caller.After, memory, o);
        Assert.Equal(0x5719, body.After.GetProperty("pc").GetInt32()); Assert.Equal(0x7DE, body.After.GetProperty("ssp").GetInt32());
        Assert.Equal(0, body.After.GetProperty("usp").GetInt32()); Assert.Equal(0x0667, P28FallthroughData0136Model.Word(body.Memory, 0x7E0));
        Assert.Equal(timer, P28FallthroughData0136Model.Word(body.Memory, 0xEE)); Assert.Equal(0, body.Memory[0xAE]); Assert.Equal(14, body.Memory[0x128]);
        Assert.Equal(irq == 1 ? 1 : 0, body.Memory[0xB6]); Assert.Equal(0x6B29, P28FallthroughData0136Model.Word(body.Memory, 0x136)); Assert.Equal(0x7C31, P28FallthroughData0136Model.Word(body.Memory, 0x360));
        Assert.Single(body.All.Where(v => v[0] == 3 && v[2] == 0x3A)); Assert.Equal(irq < 0 ? 0 : 1, body.All.Count(v => v[0] == 3 && v[2] == 0x19)); Assert.DoesNotContain(body.All, v => v[2] == 0x42 || v[2] == 0x46 || v[2] == 0x136 || v[1] == 0x5719);
    }
    internal static JsonNode Fixture(JsonElement before, P28CallerOracle own)
    {
        var steps = own.Steps.ToArray(); var all = own.All;
        return JsonSerializer.SerializeToNode(new
        {
            entry = before,
            exit = own.After,
            accesses = all.Where(v => v[0] == 0).Select(v => v[1..]),
            stage = new
            {
                sspAfter = own.After.GetProperty("ssp").GetInt32(),
                writes = all.Where(v => v[4] == 1).Select(v => new[] { v[2], v[3], v[5] }),
                events = steps.Select(s => s.Event),
                result = new
                {
                    status = 0,
                    steps = steps.Length,
                    stopPc = own.After.GetProperty("pc").GetInt32(),
                    outputs = Array.Empty<int>(),
                    programReads = Array.Empty<int>(),
                    usedAssumptions = Array.Empty<string>(),
                    error = (string?)null,
                    executedInstructionBytes = steps.SelectMany(s => Enumerable.Range(s.Event[0], s.Length)).Distinct().Order(),
                    trace = steps.Select(s => new { pc = s.Event[0], nextPc = s.Event[1], instruction = s.Form, accumulator = s.Event[3], psw = s.Event[5] })
                }
            }
        })!;
    }
    [Theory]
    [InlineData("pc")]
    [InlineData("psw")]
    [InlineData("usp")]
    [InlineData("ssp")]
    [InlineData("frame")]
    [InlineData("branch")]
    [InlineData("width")]
    [InlineData("skip")]
    [InlineData("trnsit")]
    [InlineData("tail")]
    public void ForgedCallerOrTechnicalReseedIsRejected(string fault)
    {
        var own = P28FallthroughData0136Model.Caller(Before(), Memory()); var n = Fixture(Before(), own);
        switch (fault)
        {
            case "pc": n["entry"]!["pc"] = 0x56BE; break;
            case "psw": n["exit"]!["psw"] = 0x1DCA; break;
            case "usp": n["exit"]!["usp"] = 0x280; break;
            case "ssp": n["exit"]!["ssp"] = 0x7E0; break;
            case "frame": n["accesses"]!.AsArray()[^1]![4] = 0x063E; break;
            case "branch": n["stage"]!["events"]![0]![1] = 0x065F; break;
            case "width": n["accesses"]![0]![2] = 16; break;
            case "skip": n["stage"]!["events"]!.AsArray().RemoveAt(0); break;
            case "trnsit": n["accesses"]!.AsArray().Add(JsonSerializer.SerializeToNode(new[] { 0x0657, 0x46, 8, 0, 0 })); break;
            case "tail": n["stage"]!["result"]!["executedInstructionBytes"]!.AsArray().Add(0x5719); break;
        }
        Assert.ThrowsAny<Exception>(() => P28FallthroughData0136Model.ValidateSuffix(JsonSerializer.SerializeToElement(n), Before(), own, 7));
    }
}
