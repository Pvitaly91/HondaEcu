using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28BelowSecondP2Tests
{
    internal static P28BelowSecondP2Scenario Scenario() => P28BelowSecondP2Scenario.Create(P28P2LatchTests.Scenario(), 139, 15);
    [Fact]
    public void ClosedScenarioReusesOnlyEstablishedSourcesAndNewOperation()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28BelowSecondP2Scenario.Parse(s.ToJson()).Digest);
        var request = JsonSerializer.SerializeToElement(P28BelowSecondP2Validator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal("belowSecondP2Handoff", request.GetProperty("operation").GetString()); Assert.False(request.TryGetProperty("postP2ControlHandoff", out _));
        Assert.Equal(139, request.GetProperty("belowSecondP2Handoff").GetProperty("tcon0ArchitecturalSnapshot").GetInt32());
    }
    [Theory]
    [InlineData("ready0196")]
    [InlineData("secondP2")]
    [InlineData("rolResult")]
    [InlineData("cfAfter")]
    [InlineData("pc55d2")]
    [InlineData("pc5682")]
    [InlineData("returnAddress")]
    [InlineData("timer")]
    [InlineData("irq")]
    [InlineData("physicalPins")]
    [InlineData("ram")]
    [InlineData("branchResult")]
    [InlineData("p2OutputLatch")]
    [InlineData("tcon0ArchitecturalSnapshot")]
    public void ReadyFieldsAndPerEventReseedsAreRefused(string field)
    {
        foreach (var place in new[] { "initialState", "calls" }) { var n = JsonNode.Parse(Scenario().ToJson())!; (place == "calls" ? n[place]![0]! : n[place]!)[field] = 1; Assert.ThrowsAny<Exception>(() => P28BelowSecondP2Scenario.Parse(n.ToJsonString())); }
    }
    [Theory]
    [InlineData("0.35.0")]
    [InlineData("0.34.0")]
    [InlineData("0.33.0")]
    public void HistoricalRunnerCannotClaimNewOperation(string version) => Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28BelowSecondP2Validator.Operation));
    [Fact]
    public void IndependentRolFormulaCoversBothCarryValuesZeroAndNonzeroWithNonzeroAhAndFullPsw()
    {
        foreach (var al in new[] { 0, 127, 128, 255 }) foreach (var cf in new[] { 0, 0x8000 }) foreach (var flags in new[] { 0x2DCA, 0x6DCA })
                {
                    var psw = flags | cf; var own = P28BelowSecondP2Model.Build(0xBE00 | al, psw, 0xA5, 143, 0xAA); var e = own.Events[0];
                    Assert.Equal(0xBE00 | ((al * 2 + (cf == 0 ? 0 : 1)) & 255), e[3]);
                    Assert.Equal((psw & ~0x8000) | ((al & 128) == 0 ? 0 : 0x8000), e[5]);
                    Assert.Equal(18, own.Events.Count); Assert.Equal(0x5688, own.Events[^1][1]);
                    Assert.Equal(new[] { 0, 0x565F, 0x110, 16, 0, 1 }, own.All.Single(v => v[1] == 0x565F));
                }
    }
    internal static JsonElement Before() => JsonSerializer.SerializeToElement(new { pc = 0x55D2, accumulator = 0xBE80, psw = 0xADCA, dd = false, lrb = 0x21, x1 = 2, x2 = 0, dp = 0, usp = 0x280, ssp = 0x7FE, registers = new[] { 255, 85, 191, 0, 85, 85, 85, 85 } });
    internal static JsonNode Fixture(int n = 18)
    {
        var own = P28BelowSecondP2Model.Build(0xBE80, 0xADCA, 0xAF, 143, 0xAA); var events = own.Events.Take(n).ToArray(); var all = own.All.Take(n == 0 ? 0 : own.AccessEnds[n - 1]).ToArray();
        var exit = JsonNode.Parse(Before().GetRawText())!; exit["pc"] = n == 0 ? 0x55D2 : events[^1][1]; exit["accumulator"] = n == 0 ? 0xBE80 : events[^1][3]; exit["psw"] = n == 0 ? 0xADCA : events[^1][5]; exit["dd"] = ((n == 0 ? 0xADCA : events[^1][5]) & 4096) != 0;
        return JsonSerializer.SerializeToNode(new
        {
            suffix = new
            {
                entry = Before(),
                exit,
                accesses = all.Where(v => v[0] == 0).Select(v => v[1..]),
                stage = new
                {
                    writes = all.Where(v => v[4] == 1).Select(v => new[] { v[2], v[3], v[5] }),
                    sspAfter = 0x7FE,
                    events,
                    result = new
                    {
                        status = n == 18 ? 0 : 1,
                        steps = n,
                        stopPc = exit["pc"]!.GetValue<int>(),
                        usedAssumptions = Array.Empty<string>(),
                        outputs = Array.Empty<int>(),
                        programReads = Array.Empty<int>(),
                        trace = events.Select((e, j) => new { pc = e[0], nextPc = e[1], instruction = P28BelowSecondP2Model.Mnemonics[j], accumulator = e[3], psw = e[5] }),
                        error = n == 18 ? null : "invented partial",
                        executedInstructionBytes = events.SelectMany((e, j) => Enumerable.Range(e[0], own.Lengths[j])).Distinct().Order()
                    }
                }
            },
            peripheralAccesses = all.Where(v => v[0] == 1).Select(v => v[1..]),
            controlAccesses = all.Where(v => v[0] == 2).Select(v => v[1..])
        })!;
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(10)]
    [InlineData(16)]
    [InlineData(17)]
    [InlineData(18)]
    public void InventedPartialRetainsOnlyExecutedNativeEffectsAndNeverRunsReturn(int n)
    {
        var v = P28BelowSecondP2Model.ValidateOutput(JsonSerializer.SerializeToElement(Fixture(n)), Before(), 0xAF, 143, 0xAA);
        Assert.Equal(n, v.Steps); Assert.Equal(n == 18 ? 0 : 1, v.Status); Assert.Equal(n >= 17 ? 2 : 0, v.All.Count(a => a[0] == 1));
        Assert.Equal(n >= 3 ? 3 : 0, v.All.Count(a => a[0] == 2));
    }
    [Theory]
    [InlineData("rol-a")]
    [InlineData("rol-cf")]
    [InlineData("rol-zf")]
    [InlineData("dd")]
    [InlineData("ah")]
    [InlineData("pc55d2")]
    [InlineData("pc5682")]
    [InlineData("skip-rol")]
    [InlineData("frame")]
    [InlineData("machine")]
    [InlineData("width")]
    [InlineData("old-latch")]
    [InlineData("second-write")]
    [InlineData("timer")]
    [InlineData("irq")]
    [InlineData("physical")]
    [InlineData("trace-form")]
    public void ModelOnlyForgeriesFailEvenWithSameFinalLatch(string fault)
    {
        var n = Fixture(); var s = n["suffix"]!; var e = s["stage"]!["events"]!; var p = n["peripheralAccesses"]!;
        switch (fault)
        {
            case "rol-a": e[0]![3] = 0; break;
            case "rol-cf": e[0]![5] = 0x2DCA; break;
            case "rol-zf": e[0]![5] = 0xEDCA; break;
            case "dd": e[0]![5] = 0xBDCA; break;
            case "ah": e[0]![3] = 1; break;
            case "pc55d2": s["entry"]!["pc"] = 0x5682; break;
            case "pc5682": p[0]![0] = 0x55C5; break;
            case "skip-rol": e.AsArray().RemoveAt(0); break;
            case "frame": s["exit"]!["ssp"] = 0x7FC; break;
            case "machine": s["entry"]!["dp"] = 1; break;
            case "width": p[0]![2] = 16; break;
            case "old-latch": p[0]![4] = 0xA5; break;
            case "second-write": p.AsArray().RemoveAt(1); break;
            case "timer": s["accesses"]!.AsArray().Add(JsonSerializer.SerializeToNode(new[] { 0x5680, 0x30, 16, 0, 0 })); break;
            case "irq": n["irq"] = 1; break;
            case "physical": n["physicalOutput"] = "injector"; break;
            case "trace-form": s["stage"]!["result"]!["trace"]![0]!["instruction"] = "ROL A"; break;
        }
        Assert.ThrowsAny<Exception>(() => P28BelowSecondP2Model.ValidateOutput(JsonSerializer.SerializeToElement(n), Before(), 0xAF, 143, 0xAA));
    }
}
