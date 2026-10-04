using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28Word0196HandoffTests
{
    internal static P28Word0196HandoffScenario Scenario()
    {
        var old = P28QuartetHandoffTests.Scenario();
        return P28Word0196HandoffScenario.Create(new(old.InitialState, true, 15), old.Calls, "Invented model-only software inputs;no OEM byte fixture", [0]);
    }
    [Fact]
    public void ClosedScenarioReusesPrefixAndHasNoReadyResult()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28Word0196HandoffScenario.Parse(s.ToJson()).Digest);
        var r = JsonSerializer.SerializeToElement(P28Word0196HandoffValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal(P28Word0196HandoffValidator.Operation, r.GetProperty("operation").GetString()); Assert.False(r.TryGetProperty("quartetConsumerHandoff", out _));
        Assert.False(r.GetProperty("word0196ConsumerHandoff").GetProperty("initialState").TryGetProperty("word0196", out _));
    }
    [Theory]
    [InlineData("word0196")]
    [InlineData("consumerWord0196")]
    [InlineData("expected0196")]
    [InlineData("ready0196")]
    [InlineData("value54fa")]
    [InlineData("cf")]
    [InlineData("zf")]
    [InlineData("branch")]
    [InlineData("p2")]
    [InlineData("pc")]
    [InlineData("ram")]
    [InlineData("formula")]
    [InlineData("timer")]
    [InlineData("tm0")]
    [InlineData("tmr0")]
    [InlineData("softwareWord00c0")]
    [InlineData("irqFrame")]
    [InlineData("elapsedMicroseconds")]
    public void ReadyValuesTimersPhysicalConversionsAndHiddenSourcesRefused(string field)
    {
        foreach (var key in new[] { "initialState", "calls" })
        {
            var n = JsonNode.Parse(Scenario().ToJson())!; var target = key == "calls" ? n[key]![0]! : n[key]!; target[field] = 1;
            Assert.ThrowsAny<Exception>(() => P28Word0196HandoffScenario.Parse(n.ToJsonString()));
        }
    }
    [Theory]
    [InlineData("0.31.0")]
    [InlineData("0.30.0")]
    [InlineData("0.29.0")]
    public void HistoricalRunnerCannotExecuteNewOperation(string version)
    { Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28Word0196HandoffValidator.Operation)); }
    [Fact]
    public void ModelOnlySoftwareCompletionRetainsHcAndDdAndStoresReaderWord()
    {
        foreach (var value in new[] { 0, 321, 65535 })
        {
            var m = P28Word0196HandoffModel.Build(value, 0xBDCA, 4, 15); Assert.Equal(6, m.Events.Count); Assert.Equal(0x5503, m.Stop);
            Assert.Equal(value, m.Accesses.Single(a => a[0] == 0x54FA)[4]); Assert.Equal(value, m.Accesses.Single(a => a[0] == 0x54FC)[4]);
            Assert.Equal(0x7DCA, m.Psw); Assert.DoesNotContain(m.Accesses, a => a[1] < 128); // no timer/port
        }
        var gate = P28Word0196HandoffModel.Build(321, 0x1DCA, 0, 15); Assert.Equal(0x5533, gate.Stop); Assert.Single(gate.Events); Assert.DoesNotContain(gate.Accesses, a => a[1] == 0x196);
        var alternate = P28Word0196HandoffModel.Build(321, 0x1DCA, 4, 14); Assert.Equal(0x556F, alternate.Stop); Assert.Equal(0x9DCA, alternate.Psw);
    }
    private static int[][] Ledger() => [[1, 0x103, 0x268, 16, 1, 321], [1, 0x220, 0x268, 16, 0, 321]];
    private static void Check(int[][] j, P28QuartetGeneration? g = null) => P28Word0196HandoffValidator.ValidateGeneration(j, g ?? new(0x103, 2, 0, 321), 2, 0x268, 0x220);
    [Fact]
    public void InventedSameValueFreshEventIsNotStaleIdentity()
    {
        var j = Ledger(); Check(j); var first = new P28QuartetGeneration(0x103, 1, 0, 321); var second = first with { EventIndex = 2 }; Assert.NotEqual(first, second); Check(j, second); Assert.ThrowsAny<Exception>(() => Check(j, first));
    }
    [Theory]
    [InlineData("wrong-width")]
    [InlineData("wrong-address")]
    [InlineData("fake-value")]
    [InlineData("overlap-high-byte")]
    [InlineData("host-copy")]
    [InlineData("json-second-machine")]
    [InlineData("reordered")]
    [InlineData("extra-reader")]
    [InlineData("wrong-generation-order")]
    public void InventedProvenanceForgeriesAreRejected(string fault)
    {
        var j = Ledger(); Check(j);
        switch (fault)
        {
            case "wrong-width": j[1][3] = 8; break;
            case "wrong-address": j[1][2]++; break;
            case "fake-value": j[1][5]++; break;
            case "overlap-high-byte": j = [j[0], [1, 0x150, 0x269, 8, 1, 1], j[1]]; break;
            case "host-copy": j = [j[0], [0, 65536, 0x268, 16, 1, 321], j[1]]; break;
            case "json-second-machine": j = [j[1]]; break;
            case "reordered": j = [j[1], j[0]]; break;
            case "extra-reader": j = [.. j, j[1]]; break;
            case "wrong-generation-order": Assert.ThrowsAny<Exception>(() => Check(j, new(0x103, 2, 1, 321))); return;
        }
        Assert.ThrowsAny<Exception>(() => Check(j));
    }
    private static JsonElement Before() => JsonSerializer.SerializeToElement(new { pc = 0x5ED, accumulator = 321, psw = 0x1DCA, dd = true, lrb = 0x21, x1 = 2, x2 = 0, dp = 85 * 257, usp = 85 * 257, ssp = 0x7FE, registers = Enumerable.Repeat(85, 8).ToArray() });
    private static JsonNode Fixture(int count = 6)
    {
        var own = P28Word0196HandoffModel.Build(321, 0x1DCA, 4, 15); var e = own.Events.Take(count).ToArray(); var a = own.Accesses.Take(own.AccessEnds[count - 1]).ToArray();
        var entry = JsonNode.Parse(Before().GetRawText())!; entry["pc"] = 0x54F5; var exit = entry.DeepClone(); exit["pc"] = e[^1][1]; exit["psw"] = e[^1][5]; var registers = Enumerable.Repeat(85, 8).ToArray();
        foreach (var w in a.Where(a => a[3] == 1)) for (var b = 0; b < w[2] / 8; b++) registers[w[1] + b - 0x108] = w[4] >> (8 * b) & 255; exit["registers"] = JsonSerializer.SerializeToNode(registers);
        return JsonSerializer.SerializeToNode(new
        {
            entry,
            exit,
            accesses = a,
            stage = new
            {
                events = e,
                writes = a.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray(),
                sspAfter = 0x7FE,
                result = new { status = count == 6 ? 0 : 1, usedAssumptions = Array.Empty<string>(), steps = count, stopPc = e[^1][1], outputs = Array.Empty<int>(), programReads = Array.Empty<int>(), trace = e.Select(e => new { pc = e[0], nextPc = e[1], instruction = "invented model-only observation", psw = e[5], accumulator = e[3] }).ToArray(), error = count == 6 ? null : "invented partial", executedInstructionBytes = e.SelectMany((e, n) => Enumerable.Range(e[0], own.Lengths[n])).Order().ToArray() }
            }
        })!;
    }
    private static void Consumer(JsonNode n) => P28Word0196HandoffValidator.ValidateConsumer(JsonSerializer.SerializeToElement(n), Before(), P28Word0196HandoffModel.Build(321, 0x1DCA, 4, 15), Enumerable.Repeat(85, 8).ToArray());
    [Theory]
    [InlineData("hidden-A")]
    [InlineData("hidden-pointer")]
    [InlineData("fake-frame")]
    [InlineData("skip-instruction")]
    [InlineData("wrong-width")]
    [InlineData("fake-read")]
    [InlineData("timer-read")]
    [InlineData("default-zero-timer")]
    [InlineData("timer-changed")]
    [InlineData("p2")]
    [InlineData("physical-time")]
    [InlineData("partial-complete")]
    [InlineData("forged-er1")]
    [InlineData("flags")]
    public void ModelOnlyConsumerCannotHideSeedsSkippedCodeOrHardware(string fault)
    {
        var n = Fixture(); Consumer(n);
        switch (fault)
        {
            case "hidden-A": n["entry"]!["accumulator"] = 320; break;
            case "hidden-pointer": n["entry"]!["dp"] = 0; break;
            case "fake-frame": n["entry"]!["ssp"] = 0x7F6; break;
            case "skip-instruction": n["stage"]!["events"]!.AsArray().RemoveAt(3); break;
            case "wrong-width": n["accesses"]![2]![2] = 8; break;
            case "fake-read": n["accesses"]![2]![4] = 320; break;
            case "timer-read": case "default-zero-timer": n["accesses"]!.AsArray().Add(new JsonArray(0x5503, 0x30, 16, 0, 0)); break;
            case "timer-changed": n["tm0"] = 1; break;
            case "p2": n["accesses"]!.AsArray().Add(new JsonArray(0x5596, 0x24, 8, 1, 0)); break;
            case "physical-time": n["elapsedMicroseconds"] = 321; break;
            case "partial-complete": n = Fixture(5); n["stage"]!["result"]!["status"] = 0; break;
            case "forged-er1": n["exit"]!["registers"]![2] = 0; break;
            case "flags": n["stage"]!["events"]![4]![5] = 0x7DCA; break;
        }
        Assert.ThrowsAny<Exception>(() => Consumer(n));
    }
    [Fact]
    public void ModelOnlyPartialPreservesOnlyCompletedSoftwareWrites()
    { foreach (var count in new[] { 1, 2, 3, 4, 5 }) Consumer(Fixture(count)); }
}
