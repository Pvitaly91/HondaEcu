using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28Word0196AlternateTests
{
    internal static P28Word0196AlternateScenario Scenario()
    {
        var old = P28QuartetHandoffTests.Scenario();
        return P28Word0196AlternateScenario.Create(new(old.InitialState, true, 14), old.Calls, "Invented-only storage-domain test;no OEM byte fixture", [0]);
    }
    [Fact]
    public void ClosedVersionOneScenarioReusesUpstreamSourcesWithoutReadyInputs()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28Word0196AlternateScenario.Parse(s.ToJson()).Digest);
        var r = JsonSerializer.SerializeToElement(P28Word0196AlternateValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal(P28Word0196AlternateValidator.Operation, r.GetProperty("operation").GetString());
        Assert.False(r.TryGetProperty("word0196ConsumerHandoff", out _));
        Assert.Equal(new[] { "quartetPrefix", "bit0128_2", "byte0117" }, r.GetProperty("word0196SoftwareAlternateChain").GetProperty("initialState").EnumerateObject().Select(p => p.Name));
    }
    [Theory]
    [InlineData("ready0196")]
    [InlineData("word0196")]
    [InlineData("word00c0")]
    [InlineData("data00c0")]
    [InlineData("threshold00c0")]
    [InlineData("cmpLeft")]
    [InlineData("cmpResult")]
    [InlineData("cf")]
    [InlineData("zf")]
    [InlineData("branchOutcome")]
    [InlineData("immediateOverride")]
    [InlineData("p2")]
    [InlineData("timer")]
    [InlineData("pc556f")]
    [InlineData("ram")]
    [InlineData("formula")]
    [InlineData("irqFrame")]
    [InlineData("elapsedTime")]
    [InlineData("byte018e")]
    [InlineData("byte018f")]
    [InlineData("word0197")]
    public void EveryHiddenSourceIsRefusedAtInitialAndCall(string name)
    {
        foreach (var where in new[] { "initialState", "calls" })
        {
            var n = JsonNode.Parse(Scenario().ToJson())!; var target = where == "calls" ? n[where]![0]! : n[where]!; target[name] = 1;
            Assert.ThrowsAny<Exception>(() => P28Word0196AlternateScenario.Parse(n.ToJsonString()));
        }
    }
    [Theory]
    [InlineData("0.32.0")]
    [InlineData("0.31.0")]
    [InlineData("0.30.0")]
    [InlineData("0.29.0")]
    public void HistoricalIdentityCannotClaimM2z(string version) =>
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28Word0196AlternateValidator.Operation));
    private static Dictionary<int, int> History(int pattern = 85, int control = 0, int bit5 = 0) => new()
    { [0x18E] = pattern, [0x18F] = pattern, [0x117] = 14, [0x128] = 4, [0x12A] = control, [0x124] = bit5, [0x108] = 255, [0x109] = pattern };
    [Theory]
    [InlineData(0)]
    [InlineData(191)]
    [InlineData(192)]
    [InlineData(193)]
    [InlineData(65535)]
    public void StorageDomainUnsignedCompareUsesWordAndPreservesHcDd(int value)
    {
        var h = History(); var m = P28Word0196AlternateModel.Build(value, value, 0xBDCA, h);
        var cmp = m.Events.Single(e => e[0] == 0x5578); Assert.Equal(value, cmp[6]); Assert.Equal(192, cmp[7]);
        Assert.Equal(value < 192, (cmp[5] & 0x8000) != 0); Assert.Equal(value == 192, (cmp[5] & 0x4000) != 0);
        Assert.Equal(cmp[4] & 0x3000, cmp[5] & 0x3000); Assert.Equal(0, cmp[5] & 0x1000); Assert.Equal(0x2000, cmp[5] & 0x2000);
        Assert.Equal(value < 192 ? 0x55BF : 0x557F, m.Events.Single(e => e[0] == 0x557D)[1]);
        Assert.Equal(value < 192 ? 0x55C5 : 0x5596, m.Stop); Assert.Equal(value, m.Accesses.Single(a => a[0] == 0x5578)[4]);
        Assert.DoesNotContain(m.Accesses, a => a[1] < 128 || a[1] is 0x196 && a[3] == 1);
        Assert.Equal(85, h[0x18E]); // Building expected history must not mutate the live independent history.
    }
    [Theory]
    [InlineData(0, 0, true)]
    [InlineData(128, 0, false)]
    [InlineData(0, 32, false)]
    public void BothSoftwareGatesHaveExactPersistentOwnership(int control, int bit5, bool writes)
    {
        var m = P28Word0196AlternateModel.Build(193, 193, 0x9DCA, History(85, control, bit5));
        Assert.Equal(writes, m.Accesses.Any(a => a[0] == 0x558E && a[3] == 1));
        if (writes) Assert.Equal(control | 1, m.Accesses.Single(a => a[0] == 0x558E && a[3] == 1)[4]);
        Assert.Contains(m.Accesses, a => a[0] == 0x5582 && a[3] == 1 && a[1] == 0x117);
    }
    [Fact]
    public void BelowPathWrites0117AndNextPrefixTakesExcludedTimerBoundaryWithoutReseed()
    {
        var h = History(); var m = P28Word0196AlternateModel.Build(191, 191, 0x9DCA, h);
        foreach (var w in m.Accesses.Where(a => a[3] == 1)) h[w[1]] = w[4];
        Assert.Equal(15, h[0x117]); Assert.Equal(15, h[0x18F]);
        Assert.Equal(0x5503, P28Word0196HandoffModel.Build(191, 0x1DCA, 4, (byte)h[0x117]).Stop);
    }
    private static JsonElement Before(int value = 193) => JsonSerializer.SerializeToElement(new
    { pc = 0x556F, accumulator = value, psw = 0x9DCA, dd = true, lrb = 0x21, x1 = 2, x2 = 0, dp = 85 * 257, usp = 85 * 257, ssp = 0x7FE, registers = new[] { 255, 85, value & 255, value >> 8, 85, 85, 85, 85 } });
    private static JsonNode Fixture(int value = 193, int? count = null)
    {
        var own = P28Word0196AlternateModel.Build(value, value, 0x9DCA, History()); var n = count ?? own.Events.Count;
        var e = own.Events.Take(n).ToArray(); var accesses = own.Accesses.Take(n == 0 ? 0 : own.AccessEnds[n - 1]).ToArray();
        var entry = JsonNode.Parse(Before(value).GetRawText())!; var exit = entry.DeepClone(); var psw = n == 0 ? 0x9DCA : e[^1][5];
        exit["pc"] = n == 0 ? 0x556F : e[^1][1]; exit["accumulator"] = n == 0 ? value : e[^1][3]; exit["psw"] = psw; exit["dd"] = (psw & 0x1000) != 0;
        var registers = Before(value).GetProperty("registers").EnumerateArray().Select(e => e.GetInt32()).ToArray();
        foreach (var w in accesses.Where(a => a[3] == 1 && a[1] is >= 0x108 and < 0x110)) registers[w[1] - 0x108] = w[4]; exit["registers"] = JsonSerializer.SerializeToNode(registers);
        return JsonSerializer.SerializeToNode(new
        {
            entry,
            exit,
            accesses,
            stage = new
            {
                events = e,
                writes = accesses.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray(),
                sspAfter = 0x7FE,
                result = new
                {
                    status = n == own.Events.Count ? 0 : 1,
                    usedAssumptions = Array.Empty<string>(),
                    steps = n,
                    stopPc = n == 0 ? 0x556F : e[^1][1],
                    outputs = Array.Empty<int>(),
                    programReads = Array.Empty<int>(),
                    trace = e.Select(e => new { pc = e[0], nextPc = e[1], instruction = "invented model-only observation", psw = e[5], accumulator = e[3] }).ToArray(),
                    error = n == own.Events.Count ? null : "invented partial",
                    executedInstructionBytes = e.SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).Order().ToArray()
                }
            }
        })!;
    }
    private static void Check(JsonNode n, int value = 193) => P28Word0196AlternateValidator.ValidateAlternate(JsonSerializer.SerializeToElement(n), Before(value),
        P28Word0196AlternateModel.Build(value, value, 0x9DCA, History()), Before(value).GetProperty("registers").EnumerateArray().Select(e => e.GetInt32()).ToArray());
    [Theory]
    [InlineData("hidden-A")]
    [InlineData("hidden-pointer")]
    [InlineData("fake-frame")]
    [InlineData("pc-jump")]
    [InlineData("skip-instruction")]
    [InlineData("wrong-width")]
    [InlineData("wrong-address")]
    [InlineData("ram00c0")]
    [InlineData("wrong-immediate")]
    [InlineData("forged-CF")]
    [InlineData("forged-ZF")]
    [InlineData("forced-branch")]
    [InlineData("timer")]
    [InlineData("p2")]
    [InlineData("second-machine")]
    [InlineData("wrong-compare-right-final-branch")]
    [InlineData("partial-complete")]
    public void ModelOnlySuffixRejectsAllBoundaryAndCompareForgeries(string fault)
    {
        var n = Fixture(); Check(n);
        var events = n["stage"]!["events"]!.AsArray(); var cmp = events.Single(e => e![0]!.GetValue<int>() == 0x5578)!;
        var read = n["accesses"]!.AsArray().Single(e => e![0]!.GetValue<int>() == 0x5578)!;
        switch (fault)
        {
            case "hidden-A": n["entry"]!["accumulator"] = 1; break;
            case "hidden-pointer": n["entry"]!["dp"] = 0; break;
            case "fake-frame": n["entry"]!["ssp"] = 0x7F6; break;
            case "pc-jump": n["entry"]!["pc"] = 0x5578; break;
            case "skip-instruction": events.RemoveAt(2); break;
            case "wrong-width": read[2] = 8; break;
            case "wrong-address": read[1] = 0x198; break;
            case "ram00c0": n["accesses"]!.AsArray().Add(new JsonArray(0x5578, 0xC0, 16, 0, 192)); break;
            case "wrong-immediate": cmp[7] = 193; break;
            case "forged-CF": cmp[5] = cmp[5]!.GetValue<int>() ^ 0x8000; break;
            case "forged-ZF": cmp[5] = cmp[5]!.GetValue<int>() ^ 0x4000; break;
            case "forced-branch": events.Single(e => e![0]!.GetValue<int>() == 0x557D)![1] = 0x55BF; break;
            case "timer": n["accesses"]!.AsArray().Add(new JsonArray(0x5503, 0x30, 16, 0, 0)); break;
            case "p2": n["accesses"]!.AsArray().Add(new JsonArray(0x5596, 0x24, 8, 1, 0)); break;
            case "second-machine": n["entry"]!["registers"]![0] = 85; break;
            case "wrong-compare-right-final-branch": cmp[6] = 194; break;
            case "partial-complete": n = Fixture(count: 5); n["stage"]!["result"]!["status"] = 0; break;
        }
        Assert.ThrowsAny<Exception>(() => Check(n));
    }
    [Fact]
    public void ModelOnlyPartialRetainsCompletedWritesWithoutClaimingSecondReader()
    { for (var n = 0; n < P28Word0196AlternateModel.Build(193, 193, 0x9DCA, History()).Events.Count; n++) Check(Fixture(count: n)); }
    [Fact]
    public void InventedLedgerRequiresBothReadersToConsumeSameFreshUnoverwrittenGeneration()
    {
        int[][] j = [[1, 0x111, 0x268, 16, 1, 291], [1, 0x221, 0x268, 16, 0, 291], [1, 0x331, 0x268, 16, 0, 291]];
        var g = new P28QuartetGeneration(0x111, 3, 0, 291);
        foreach (var reader in new[] { 0x221, 0x331 }) P28Word0196HandoffValidator.ValidateGeneration(j, g, 3, 0x268, reader);
        Assert.ThrowsAny<Exception>(() => P28Word0196HandoffValidator.ValidateGeneration(j, g with { EventIndex = 2 }, 3, 0x268, 0x331));
        int[][] overlap = [j[0], j[1], [1, 0x222, 0x269, 8, 1, 1], j[2]];
        Assert.ThrowsAny<Exception>(() => P28Word0196HandoffValidator.ValidateGeneration(overlap, g, 3, 0x268, 0x331));
        int[][] host = [j[0], j[1], [0, 65536, 0x268, 16, 1, 291], j[2]];
        Assert.ThrowsAny<Exception>(() => P28Word0196HandoffValidator.ValidateGeneration(host, g, 3, 0x268, 0x331));
        Assert.ThrowsAny<Exception>(() => P28Word0196HandoffValidator.ValidateGeneration([j[1], j[2]], g, 3, 0x268, 0x331));
    }
}
