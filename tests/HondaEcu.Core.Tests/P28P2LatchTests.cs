using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28P2LatchTests
{
    internal static P28P2LatchScenario Scenario(byte latch = 0xA5) => P28P2LatchScenario.Create(P28Word0196AlternateTests.Scenario(), latch);
    [Fact]
    public void ClosedOnceInitialArchitecturalSnapshotReusesUpstreamWithoutReadyP2Mask()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28P2LatchScenario.Parse(s.ToJson()).Digest);
        var r = JsonSerializer.SerializeToElement(P28P2LatchValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal(P28P2LatchValidator.Operation, r.GetProperty("operation").GetString()); Assert.False(r.TryGetProperty("word0196SoftwareAlternateChain", out _));
        Assert.Equal(0xA5, r.GetProperty("p2OutputLatchHandoff").GetProperty("p2OutputLatch").GetInt32());
    }
    [Theory]
    [InlineData("expectedP2")]
    [InlineData("p2Pins")]
    [InlineData("p2IoMode")]
    [InlineData("outputMask")]
    [InlineData("finalA")]
    [InlineData("p2Mask")]
    [InlineData("timer")]
    [InlineData("pc5596")]
    [InlineData("pc55c5")]
    [InlineData("physicalPolarity")]
    [InlineData("injector")]
    [InlineData("branchResult")]
    [InlineData("word0196")]
    [InlineData("irqFrame")]
    [InlineData("ram")]
    [InlineData("p2OutputLatch")]
    public void HiddenOrPerEventSourceCannotForcePeripheralProof(string name)
    {
        foreach (var where in new[] { "initialState", "calls" }) { var n = JsonNode.Parse(Scenario().ToJson())!; (where == "calls" ? n[where]![0]! : n[where]!)[name] = 1; Assert.ThrowsAny<Exception>(() => P28P2LatchScenario.Parse(n.ToJsonString())); }
        if (name != "p2OutputLatch") { var n = JsonNode.Parse(Scenario().ToJson())!; n[name] = 1; Assert.ThrowsAny<Exception>(() => P28P2LatchScenario.Parse(n.ToJsonString())); }
    }
    [Theory]
    [InlineData(-1)]
    [InlineData(256)]
    public void LatchIsByteNotWordOrImplicitReset(int v) { var n = JsonNode.Parse(Scenario().ToJson())!; n["p2OutputLatch"] = v; Assert.ThrowsAny<Exception>(() => P28P2LatchScenario.Parse(n.ToJsonString())); }
    [Theory]
    [InlineData("0.33.0")]
    [InlineData("0.32.0")]
    [InlineData("0.31.0")]
    public void HistoricalRunnerCannotClaimM2aa(string version) => Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28P2LatchValidator.Operation));
    [Theory]
    [InlineData(0x5596, 0xFF, 0xF0, 0xF0)]
    [InlineData(0x5596, 0, 0xFF, 0)]
    [InlineData(0x5596, 0xA5, 0xFA, 0xA0)]
    [InlineData(0x55C5, 0, 15, 15)]
    [InlineData(0x55C5, 0xFF, 15, 0xFF)]
    [InlineData(0x55C5, 0xA0, 15, 0xAF)]
    public void IndependentArchitecturalByteAndOrUsesAlAndOnlyChangesZf(int pc, int old, int al, int expected)
    {
        foreach (var psw in new[] { 0xADCA, 0xBDCA, 0xEDCA, 0xFDCA }) { var m = P28P2LatchModel.Compute(pc, old, 0xAB00 | al, psw); Assert.Equal(expected, m.Value); Assert.Equal(psw & ~0x4000, m.Psw & ~0x4000); Assert.Equal(expected == 0, (m.Psw & 0x4000) != 0); }
    }
    private static JsonElement Before(int pc = 0x5596) => JsonSerializer.SerializeToElement(new { pc, accumulator = 0xABF0, psw = 0x9DCA, dd = true, lrb = 0x21, x1 = 2, x2 = 0, dp = 0, usp = 0x280, ssp = 0x7FE, registers = new[] { 255, 85, 193, 0, 85, 85, 85, 85 } });
    private static JsonNode Fixture(int pc = 0x5596, int old = 0xA5, bool partial = false)
    {
        var before = Before(pc); var m = P28P2LatchModel.Compute(pc, old, 0xABF0, 0x9DCA); var n = partial ? 0 : 1;
        var exit = JsonNode.Parse(before.GetRawText())!; exit["pc"] = pc + 3 * n; exit["psw"] = partial ? 0x9DCA : m.Psw;
        return JsonSerializer.SerializeToNode(new
        {
            suffix = new
            {
                entry = before,
                exit,
                accesses = Array.Empty<int[]>(),
                stage = new
                {
                    writes = partial ? Array.Empty<int[]>() : new[] { new[] { 0x24, 8, m.Value } },
                    sspAfter = 0x7FE,
                    events = partial ? Array.Empty<int[]>() : new[] { new[] { pc, pc + 3, 0xABF0, 0xABF0, 0x9DCA, m.Psw, 65536, 65536 } },
                    result = new
                    {
                        status = partial ? 1 : 0,
                        steps = n,
                        stopPc = pc + 3 * n,
                        usedAssumptions = Array.Empty<string>(),
                        outputs = Array.Empty<int>(),
                        programReads = Array.Empty<int>(),
                        trace = partial ? [] : new[] { new { pc, nextPc = pc + 3, instruction = "invented model-only observation", accumulator = 0xABF0, psw = m.Psw } },
                        error = partial ? "invented partial" : null,
                        executedInstructionBytes = partial ? [] : Enumerable.Range(pc, 3).ToArray()
                    }
                }
            },
            peripheralAccesses = partial ? Array.Empty<int[]>() : new[] { new[] { pc, 0x24, 8, 0, old }, new[] { pc, 0x24, 8, 1, m.Value } }
        })!;
    }
    [Theory]
    [InlineData("old")]
    [InlineData("new")]
    [InlineData("width")]
    [InlineData("neighbor")]
    [InlineData("direction")]
    [InlineData("order")]
    [InlineData("missing-write")]
    [InlineData("missing-read")]
    [InlineData("pc-shortcut")]
    [InlineData("hidden-a")]
    [InlineData("fake-frame")]
    [InlineData("wrong-op")]
    [InlineData("flags")]
    [InlineData("timer")]
    [InlineData("ram")]
    [InlineData("extent")]
    public void ModelOnlyEvidenceRejectsForgedPeripheralAccessesAndBoundary(string fault)
    {
        var n = Fixture(); var s = n["suffix"]!; var accesses = n["peripheralAccesses"]!.AsArray();
        switch (fault)
        {
            case "old": accesses[0]![4] = 0; break;
            case "new": accesses[1]![4] = 1; break;
            case "width": accesses[0]![2] = 16; break;
            case "neighbor": accesses[1]![1] = 0x25; break;
            case "direction": accesses[1]![1] = 0x26; break;
            case "order": var first = accesses[0]!.DeepClone(); accesses.RemoveAt(0); accesses.Add(first); break;
            case "missing-write": accesses.RemoveAt(1); break;
            case "missing-read": accesses.RemoveAt(0); break;
            case "pc-shortcut": s["entry"]!["pc"] = 0x55C5; break;
            case "hidden-a": s["entry"]!["accumulator"] = 15; break;
            case "fake-frame": s["entry"]!["ssp"] = 0x7FC; break;
            case "wrong-op": s["stage"]!["events"]![0]![3] = 0; break;
            case "flags": s["stage"]!["events"]![0]![5] = 0; break;
            case "timer": s["stage"]!["result"]!["programReads"]!.AsArray().Add(0x30); break;
            case "ram": s["accesses"]!.AsArray().Add(JsonSerializer.SerializeToNode(new[] { 0x5596, 0x24, 8, 0, 0xA5 })); break;
            case "extent": s["stage"]!["result"]!["executedInstructionBytes"]!.AsArray().Add(0x5599); break;
        }
        Assert.ThrowsAny<Exception>(() => P28P2LatchModel.ValidateOutput(JsonSerializer.SerializeToElement(n), Before(), 0xA5, out _));
    }
    [Fact]
    public void PartialP2HasNoReadWriteAndNoInventedLatch()
    { P28P2LatchModel.ValidateOutput(JsonSerializer.SerializeToElement(Fixture(partial: true)), Before(), 0xA5, out var v); Assert.Null(v); }
    [Fact]
    public void FreshSameValueGenerationIsRetainedAndStaleOrHostOverwrittenHistoryRejected()
    {
        var own = new P28P2LatchValidation(0xFF); var g = new P28QuartetGeneration(0x5EB, 0, 3, 193);
        var row = JsonSerializer.SerializeToNode(new { p2Before = 255, p2After = 255, incomingP2Generation = (object?)null, p2Generation = new P28QuartetGeneration(0x55C5, 0, 0, 255), p2 = Fixture(0x55C5, 255), continuityJournal = Array.Empty<int[]>() }, JsonDefaults.Create())!;
        own.Finish(0, 0, JsonSerializer.SerializeToElement(row), Before(0x55C5), g, "QuartetDerived0196AlternateStrict");
        var after = row["p2"]!["suffix"]!["exit"]!.DeepClone(); var next = row.DeepClone(); next["p2"] = null; next["incomingP2Generation"] = row["p2Generation"]!.DeepClone();
        own.Finish(0, 1, JsonSerializer.SerializeToElement(next), JsonSerializer.SerializeToElement(after), null, "NotRun");
        next["incomingP2Generation"]!["eventIndex"] = 1;
        Assert.ThrowsAny<Exception>(() => own.Finish(0, 2, JsonSerializer.SerializeToElement(next), JsonSerializer.SerializeToElement(after), null, "NotRun"));
    }
}
