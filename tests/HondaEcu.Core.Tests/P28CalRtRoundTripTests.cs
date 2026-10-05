using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28CalRtRoundTripTests
{
    internal static P28CalRtRoundTripScenario Scenario() => P28CalRtRoundTripScenario.Create(P28P2LatchTests.Scenario(), 139, 15);
    [Fact]
    public void NewClosedOperationDoesNotSupplyAFrameOrReturnTarget()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28CalRtRoundTripScenario.Parse(s.ToJson()).Digest);
        var request = JsonSerializer.SerializeToElement(P28CalRtRoundTripValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal("calRtRoundTripHandoff", request.GetProperty("operation").GetString());
        Assert.False(request.TryGetProperty("belowSecondP2Handoff", out _));
        Assert.False(request.GetProperty("calRtRoundTripHandoff").TryGetProperty("callerFrame", out _));
    }
    [Theory]
    [InlineData("returnPc")]
    [InlineData("returnAddress")]
    [InlineData("stackWord")]
    [InlineData("callerFrame")]
    [InlineData("sspAfterCal")]
    [InlineData("expectedRtTarget")]
    [InlineData("pc54f5")]
    [InlineData("pc5688")]
    [InlineData("pc063e")]
    [InlineData("ssp")]
    [InlineData("ready0196")]
    [InlineData("irq")]
    [InlineData("timer")]
    public void AllFrameAndReadyStateFieldsAreRefused(string field)
    {
        foreach (var place in new[] { "root", "initialState", "calls" })
        {
            var n = JsonNode.Parse(Scenario().ToJson())!; (place == "root" ? n : place == "calls" ? n[place]![0]! : n[place]!)[field] = 1598;
            Assert.ThrowsAny<Exception>(() => P28CalRtRoundTripScenario.Parse(n.ToJsonString()));
        }
    }
    [Theory]
    [InlineData("0.36.0")]
    [InlineData("0.35.0")]
    [InlineData("0.34.0")]
    public void OldIdentityCannotClaimCallerRoundTrip(string version) => Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28CalRtRoundTripValidator.Operation));
    private static P28NativeCallFrame Frame => new(0x063B, 0, 0x7FE, 16, 0x063E, 0);
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void PriorHelperStackUseIsOverwrittenButOverlapAfterNewCalIsRejected(bool overlap)
    {
        var own = new P28CalRtRoundTripValidation(); var frame = Frame with { WriteOrder = 1 };
        var row = JsonSerializer.SerializeToElement(new
        {
            nativeCal = Fixture(true),
            nativeRt = Fixture(false),
            callFrame = frame,
            stackJournal = new[] { new[] { 0x063B, 0x7FE, 16, 1, 0x063E }, new[] { 0x5688, 0x7FE, 16, 0, 0x063E } }
        }, JsonDefaults.Create());
        var prefix = new P28QuartetHandoffCheckpoint(0, "invented", "invented", null, null, null, null, null, null, [],
            JsonSerializer.SerializeToElement(new { continuityJournal = new[] { new[] { 1, 0x100, 0x7FE, 16, 1, 0x1234 }, new[] { 1, 0x108, 0x7FE, 16, 0, 0x1234 } } }));
        var before = JsonNode.Parse(Before(true).GetRawText())!; before["pc"] = 0x05ED;
        var native = new List<int[]>(); _ = own.Start(0, 0, row, JsonSerializer.SerializeToElement(before), prefix, native);
        List<int[]> all = [[0, 0x100, 0x7FE, 16, 1, 0x1234], [0, 0x108, 0x7FE, 16, 0, 0x1234], [0, 0x063B, 0x7FE, 16, 1, 0x063E]];
        if (overlap) { all.Add([0, 0x200, 0x7FE, 16, 1, 0x063E]); Assert.ThrowsAny<Exception>(() => own.Finish(0, 0, row, Before(false), "BelowSecondP2Strict", all)); }
        else { var r = own.Finish(0, 0, row, Before(false), "BelowSecondP2Strict", all); Assert.Equal("CallReturnStrict", r.Disposition); Assert.True(own.Rows[0][0].SameFrame); }
    }
    private static JsonElement Before(bool call) => JsonSerializer.SerializeToElement(new
    {
        pc = call ? 0x063B : 0x5688,
        accumulator = 0xBE80,
        psw = 0xADCA,
        dd = false,
        lrb = 0x21,
        x1 = 2,
        x2 = 0,
        dp = 0,
        usp = 0x280,
        ssp = call ? 0x7FE : 0x7FC,
        registers = new[] { 255, 85, 191, 0, 85, 85, 85, 85 }
    });
    private static JsonNode Fixture(bool call, int n = 1)
    {
        var before = Before(call); var pc = call ? 0x063B : 0x5688; var target = call ? 0x54F5 : 0x063E;
        var after = JsonNode.Parse(before.GetRawText())!; after["pc"] = n == 0 ? pc : target; after["ssp"] = n == 0 ? before.GetProperty("ssp").GetInt32() : call ? 0x7FC : 0x7FE;
        int[][] accesses = n == 0 ? [] : [[pc, 0x7FE, 16, call ? 1 : 0, 0x063E]];
        return JsonSerializer.SerializeToNode(new
        {
            sfBefore = false,
            sfAfter = false,
            suffix = new
            {
                entry = before,
                exit = after,
                accesses,
                stage = new
                {
                    sspAfter = after["ssp"]!.GetValue<int>(),
                    writes = accesses.Where(v => v[3] == 1).Select(v => new[] { v[1], v[2], v[4] }),
                    events = n == 0 ? Array.Empty<int[]>() : new[] { new[] { pc, target, 0xBE80, 0xBE80, 0xADCA, 0xADCA, 65536, 65536 } },
                    result = new
                    {
                        status = n == 0 ? 1 : 0,
                        steps = n,
                        stopPc = n == 0 ? pc : target,
                        outputs = Array.Empty<int>(),
                        programReads = Array.Empty<int>(),
                        usedAssumptions = Array.Empty<string>(),
                        error = n == 0 ? "invented partial" : null,
                        trace = n == 0 ? Array.Empty<object>() : new object[] { new { pc, nextPc = target, instruction = call ? "CAL addr16" : "RT", accumulator = 0xBE80, psw = 0xADCA } },
                        executedInstructionBytes = n == 0 ? Array.Empty<int>() : Enumerable.Range(pc, call ? 3 : 1).ToArray()
                    }
                }
            }
        })!;
    }
    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void IndependentCallReturnPreservesFullCalleeStateAndChangesOnlyPcSsp(bool call)
    {
        var result = P28CalRtRoundTripValidation.ValidateInstruction(JsonSerializer.SerializeToElement(Fixture(call)), Before(call), Frame, call);
        Assert.Equal(0, result.Status); Assert.Equal(call ? 0x7FC : 0x7FE, result.After.GetProperty("ssp").GetInt32());
        Assert.Equal(0xBE80, result.After.GetProperty("accumulator").GetInt32()); Assert.Equal(0xADCA, result.After.GetProperty("psw").GetInt32());
    }
    [Theory]
    [InlineData("pc")]
    [InlineData("ssp")]
    [InlineData("a")]
    [InlineData("psw")]
    [InlineData("lrb")]
    [InlineData("width")]
    [InlineData("address")]
    [InlineData("value")]
    [InlineData("stale")]
    [InlineData("sf")]
    [InlineData("trace")]
    [InlineData("length")]
    [InlineData("rti")]
    [InlineData("skip")]
    [InlineData("pointer")]
    public void NumericallyCorrectReturnDoesNotExcuseForgedNativeEvidence(string fault)
    {
        foreach (var call in new[] { true, false })
        {
            var n = Fixture(call); var s = n["suffix"]!; var stage = s["stage"]!;
            switch (fault)
            {
                case "pc": s["entry"]!["pc"] = 0x54F5; break;
                case "ssp": s["exit"]!["ssp"] = 0x7FA; break;
                case "a": s["exit"]!["accumulator"] = 0x063E; break;
                case "psw": s["exit"]!["psw"] = 0xEDCA; break;
                case "lrb": s["exit"]!["lrb"] = 0x20; break;
                case "pointer": s["exit"]!["usp"] = 0; break;
                case "width": s["accesses"]![0]![2] = 8; break;
                case "address": s["accesses"]![0]![1] = 0x7FC; break;
                case "value": s["accesses"]![0]![4] = 0x0640; break;
                case "stale": s["accesses"] = new JsonArray(); break;
                case "sf": n["sfAfter"] = true; break;
                case "trace": stage["result"]!["trace"]![0]!["nextPc"] = 0x0640; break;
                case "length": stage["result"]!["executedInstructionBytes"] = new JsonArray(); break;
                case "rti": stage["result"]!["trace"]![0]!["instruction"] = "RTI"; break;
                case "skip": stage["events"] = new JsonArray(); break;
            }
            Assert.ThrowsAny<Exception>(() => P28CalRtRoundTripValidation.ValidateInstruction(JsonSerializer.SerializeToElement(n), Before(call), Frame, call));
        }
    }
    [Fact]
    public void RtWithoutNativeCalIsRejectedEvenWithCorrectReturnWord()
    {
        var row = JsonSerializer.SerializeToElement(new { nativeCal = (object?)null, nativeRt = Fixture(false), callFrame = (object?)null, stackJournal = new[] { new[] { 0x5688, 0x7FE, 16, 0, 0x063E } } });
        Assert.ThrowsAny<Exception>(() => new P28CalRtRoundTripValidation().Finish(0, 0, row, Before(false), "BelowSecondP2Strict", []));
    }
    [Fact]
    public void PartialReturnDoesNotClaimBalancedStackOrExecute063e()
    {
        var r = P28CalRtRoundTripValidation.ValidateInstruction(JsonSerializer.SerializeToElement(Fixture(false, 0)), Before(false), Frame, false);
        Assert.Equal(1, r.Status); Assert.Equal(0x5688, r.After.GetProperty("pc").GetInt32()); Assert.Equal(0x7FC, r.After.GetProperty("ssp").GetInt32());
    }
}
