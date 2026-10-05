using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28PostP2ControlTests
{
    internal static P28PostP2ControlScenario Scenario(byte tcon0 = 0x8B, byte flags = 15) => P28PostP2ControlScenario.Create(P28P2LatchTests.Scenario(), tcon0, flags);
    [Fact]
    public void ClosedOnceInitialSnapshotsReuseUpstreamAndNeverProvideReadyControlResults()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28PostP2ControlScenario.Parse(s.ToJson()).Digest);
        var r = JsonSerializer.SerializeToElement(P28PostP2ControlValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal(P28PostP2ControlValidator.Operation, r.GetProperty("operation").GetString()); Assert.False(r.TryGetProperty("p2OutputLatchHandoff", out _));
        Assert.Equal(139, r.GetProperty("postP2ControlHandoff").GetProperty("tcon0ArchitecturalSnapshot").GetInt32());
    }
    [Theory]
    [InlineData("timerTicks")]
    [InlineData("tm0")]
    [InlineData("tmr0")]
    [InlineData("elapsedTime")]
    [InlineData("irq")]
    [InlineData("physicalPins")]
    [InlineData("commandResult")]
    [InlineData("expectedControl")]
    [InlineData("branchResult")]
    [InlineData("ready0196")]
    [InlineData("ram")]
    [InlineData("pc5599")]
    [InlineData("pc55c8")]
    [InlineData("controlMap")]
    [InlineData("trnsitArchitecturalFlags")]
    [InlineData("tcon0ArchitecturalSnapshot")]
    public void ReadyResultsAndPerEventReseedsCannotEnterTheClosedSchema(string field)
    {
        foreach (var place in new[] { "initialState", "calls" }) { var n = JsonNode.Parse(Scenario().ToJson())!; (place == "calls" ? n[place]![0]! : n[place]!)[field] = 1; Assert.ThrowsAny<Exception>(() => P28PostP2ControlScenario.Parse(n.ToJsonString())); }
        if (field is not ("trnsitArchitecturalFlags" or "tcon0ArchitecturalSnapshot")) { var n = JsonNode.Parse(Scenario().ToJson())!; n[field] = 1; Assert.ThrowsAny<Exception>(() => P28PostP2ControlScenario.Parse(n.ToJsonString())); }
    }
    [Fact]
    public void OnlyExplicitStoppedRealtimeOutputDomainAndImplementedFlagsAreAdmitted()
    {
        for (var t = 0; t <= 255; t++) if ((t & ~12) == 131) Assert.Equal(t, Scenario((byte)t).Tcon0ArchitecturalSnapshot); else Assert.Throws<InvalidDataException>(() => Scenario((byte)t));
        for (var f = 16; f <= 255; f++) Assert.Throws<InvalidDataException>(() => Scenario(flags: (byte)f));
    }
    [Theory]
    [InlineData("0.34.0")]
    [InlineData("0.33.0")]
    [InlineData("0.32.0")]
    public void HistoricalRunnerCannotClaimNewControlOperation(string version) => Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28PostP2ControlValidator.Operation));
    [Fact]
    public void IndependentEffectsPreserveAllUnwrittenBitsAndFlagsAndNeverEvolveTimer()
    {
        foreach (var t in new[] { 131, 135, 139, 143 }) for (var f = 0; f < 16; f++) foreach (var psw in new[] { 0x2DCA, 0xADCA, 0xEDCA })
                {
                    var a = P28PostP2ControlModel.Build(0x5599, 0xBE91, psw, t, f, 0x77);
                    Assert.Equal(f & ~4, a.TrnsitFlagsAfter); Assert.Equal(t, a.Tcon0After); Assert.Equal(psw & ~0x4000, a.Events[0][5]); Assert.Equal(0xBE91, a.Events[0][3]); Assert.Equal(0xF0 | f, a.ControlAccesses[0][4]);
                    var b = P28PostP2ControlModel.Build(0x55C8, 0xBE91, psw, t, f, 0x7F);
                    Assert.Equal(t | 4, b.Tcon0After); Assert.Equal(f, b.TrnsitFlagsAfter); Assert.Equal((t & 4) == 0, (b.Events[0][5] & 0x4000) != 0);
                    Assert.Equal(0xBE80, b.Events[^1][3]); Assert.Equal(0, b.Events[^1][5] & 0x1000); Assert.NotEqual(0, b.Events[^1][5] & 0x8000);
                    Assert.Equal(psw & ~0xD000, b.Events[^1][5] & ~0xD000); Assert.Single(b.RamAccesses); Assert.Equal(0x18E, b.RamAccesses[0][1]);
                }
    }
    internal static JsonElement Before(int pc) => JsonSerializer.SerializeToElement(new { pc, accumulator = 0xBE91, psw = 0xADCA, dd = false, lrb = 0x21, x1 = 2, x2 = 0, dp = 0, usp = 0x280, ssp = 0x7FE, registers = new[] { 255, 85, 193, 0, 85, 85, 85, 85 } });
    internal static JsonNode Fixture(int pc = 0x5599, int count = -1, int flags = 15)
    {
        var before = Before(pc); var own = P28PostP2ControlModel.Build(pc, 0xBE91, 0xADCA, 139, flags, 0x7F); var n = count < 0 ? own.Events.Count : count; var events = own.Events.Take(n).ToArray();
        var exit = JsonNode.Parse(before.GetRawText())!; exit["pc"] = n == 0 ? pc : events[^1][1]; exit["accumulator"] = n == 0 ? 0xBE91 : events[^1][3]; exit["psw"] = n == 0 ? 0xADCA : events[^1][5]; exit["dd"] = ((n == 0 ? 0xADCA : events[^1][5]) & 0x1000) != 0;
        var controls = n == 0 ? Array.Empty<int[]>() : own.ControlAccesses; var ram = pc == 0x55C8 && n >= 2 ? own.RamAccesses : [];
        return JsonSerializer.SerializeToNode(new { suffix = new { entry = before, exit, accesses = ram, stage = new { writes = controls.Where(v => v[3] == 1).Select(v => new[] { v[1], v[2], v[4] }).ToArray(), sspAfter = 0x7FE, events, result = new { status = n == own.Events.Count ? 0 : 1, steps = n, stopPc = exit["pc"]!.GetValue<int>(), usedAssumptions = Array.Empty<string>(), outputs = Array.Empty<int>(), programReads = Array.Empty<int>(), trace = events.Select(e => new { pc = e[0], nextPc = e[1], instruction = "invented model-only evidence", accumulator = e[3], psw = e[5] }).ToArray(), error = n == own.Events.Count ? null : "invented partial", executedInstructionBytes = events.SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).ToArray() } } }, controlAccesses = controls })!;
    }
    [Theory]
    [InlineData("old")]
    [InlineData("new")]
    [InlineData("width")]
    [InlineData("neighbor")]
    [InlineData("reserved")]
    [InlineData("missing-read")]
    [InlineData("missing-write")]
    [InlineData("order")]
    [InlineData("wrong-pc")]
    [InlineData("host-pc")]
    [InlineData("hidden-a")]
    [InlineData("frame")]
    [InlineData("flags")]
    [InlineData("ram")]
    [InlineData("timer")]
    [InlineData("command")]
    [InlineData("extent")]
    public void ModelOnlyForgeriesAreRejectedEvenWithCorrectFinalStorage(string fault)
    {
        var n = Fixture(); var s = n["suffix"]!; var c = n["controlAccesses"]!.AsArray();
        switch (fault)
        {
            case "old": c[0]![4] = 15; break;
            case "new": c[1]![4] = 15; break;
            case "width": c[0]![2] = 16; break;
            case "neighbor": c[0]![1] = 0x47; break;
            case "reserved": c[1]![4] = 11; break;
            case "missing-read": c.RemoveAt(0); break;
            case "missing-write": c.RemoveAt(1); break;
            case "order": var first = c[0]!.DeepClone(); c.RemoveAt(0); c.Add(first); break;
            case "wrong-pc": c[0]![0] = 0x55C8; break;
            case "host-pc": s["entry"]!["pc"] = 0x55C8; break;
            case "hidden-a": s["entry"]!["accumulator"] = 0; break;
            case "frame": s["exit"]!["ssp"] = 0x7FC; break;
            case "flags": s["stage"]!["events"]![0]![5] = 0; break;
            case "ram": s["accesses"]!.AsArray().Add(c[0]!.DeepClone()); break;
            case "timer": s["stage"]!["result"]!["programReads"]!.AsArray().Add(0x30); break;
            case "command": n["commandInvocation"] = 1; break;
            case "extent": s["stage"]!["result"]!["executedInstructionBytes"]!.AsArray().Add(0x559D); break;
        }
        Assert.ThrowsAny<Exception>(() => P28PostP2ControlModel.ValidateOutput(JsonSerializer.SerializeToElement(n), Before(0x5599), 139, 15, 0x7F));
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    public void PartialPrefixRetainsOnlyActuallyExecutedControlAndRamReads(int steps)
    {
        var v = P28PostP2ControlModel.ValidateOutput(JsonSerializer.SerializeToElement(Fixture(0x55C8, steps)), Before(0x55C8), 139, 15, 0x7F);
        Assert.Equal(steps == 0 ? 0 : 3, v.Control.Length); Assert.Equal(steps < 2 ? 0 : 1, v.Ram.Length); Assert.Equal(steps == 4 ? 0 : 1, v.Status);
    }
    [Fact]
    public void SameValueWriteStillHasFreshGenerationAndNotRunRetainsItWithoutReseed()
    {
        var own = new P28PostP2ControlValidation(Scenario(flags: 11)); var p2g = new P28QuartetGeneration(0x5596, 0, 5, 160); var g = new P28QuartetGeneration(0x5EB, 0, 2, 193);
        var p2 = new P28P2LatchCheckpoint(0, "QuartetDerivedP2LatchStrict", 165, 160, 0x5596, 240, null, p2g, g, "InitialArchitecturalSnapshot", "NotModeled");
        var row = JsonSerializer.SerializeToNode(new { controlBefore = new[] { 139, 11 }, controlAfter = new[] { 139, 11 }, incomingTcon0Generation = (object?)null, tcon0Generation = (object?)null, incomingTrnsitGeneration = (object?)null, trnsitGeneration = new P28QuartetGeneration(0x5599, 0, 6, 251), control = Fixture(flags: 11) }, JsonDefaults.Create())!;
        own.Finish(0, 0, JsonSerializer.SerializeToElement(row), Before(0x5599), g, "QuartetDerivedP2LatchStrict", 127, p2);
        row["incomingTrnsitGeneration"] = row["trnsitGeneration"]!.DeepClone(); row["trnsitGeneration"]!["eventIndex"] = 1;
        var nextP2 = p2 with { Index = 1, Generation = p2g with { EventIndex = 1 } };
        own.Finish(0, 1, JsonSerializer.SerializeToElement(row), Before(0x5599), g with { EventIndex = 1 }, "QuartetDerivedP2LatchStrict", 127, nextP2);
        Assert.NotEqual(own.Rows[0][0].TrnsitGeneration, own.Rows[0][1].TrnsitGeneration); Assert.Equal(11, own.Rows[0][1].TrnsitFlagsAfter);
        var after = row["control"]!["suffix"]!["exit"]!.DeepClone(); row["control"] = null; row["incomingTrnsitGeneration"] = row["trnsitGeneration"]!.DeepClone();
        own.Finish(0, 2, JsonSerializer.SerializeToElement(row), JsonSerializer.SerializeToElement(after), null, "NotRun", 127, nextP2);
        row["incomingTrnsitGeneration"]!["eventIndex"] = 2;
        Assert.ThrowsAny<Exception>(() => own.Finish(0, 3, JsonSerializer.SerializeToElement(row), JsonSerializer.SerializeToElement(after), null, "NotRun", 127, nextP2));
    }
}
