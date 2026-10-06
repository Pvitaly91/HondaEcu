using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28PostReturnSelectorTests
{
    internal static P28PostReturnSelectorScenario Scenario(byte selector = 0)
    {
        var old = P28CalRtRoundTripTests.Scenario();
        return P28PostReturnSelectorScenario.Create(old.InitialState, selector, old.Calls.Select(c => new P28PostReturnSelectorCall(c.Prefix)).ToArray(), old.P2OutputLatch, old.Tcon0ArchitecturalSnapshot, old.TrnsitArchitecturalFlags, old.Provenance, old.TraceEventIndexes);
    }
    [Fact]
    public void ClosedScenarioAndRequestHaveOnlyOnceInitialSelectorAndPrefixOnlyCalls()
    {
        var s = Scenario(3); Assert.Equal(s.Digest, P28PostReturnSelectorScenario.Parse(s.ToJson()).Digest);
        var r = JsonSerializer.SerializeToElement(P28PostReturnSelectorValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal("postReturnSelectorHandoff", r.GetProperty("operation").GetString());
        Assert.Equal(3, r.GetProperty("postReturnSelectorHandoff").GetProperty("initialSelector013c").GetInt32());
        foreach (var c in r.GetProperty("postReturnSelectorHandoff").GetProperty("calls").EnumerateArray()) Assert.Equal(new[] { "prefix" }, c.EnumerateObject().Select(p => p.Name));
        Assert.False(r.TryGetProperty("calRtRoundTripHandoff", out _));
    }
    [Theory]
    [InlineData("selector013c")]
    [InlineData("initialSelector013c")]
    [InlineData("expectedSelector")]
    [InlineData("nextSelector")]
    [InlineData("selectedSlot")]
    [InlineData("selectedAddress")]
    [InlineData("x1")]
    [InlineData("pc063e")]
    [InlineData("pc064a")]
    [InlineData("pc0584")]
    [InlineData("branch064c")]
    [InlineData("ready0196")]
    [InlineData("timer")]
    [InlineData("irq")]
    [InlineData("ram")]
    public void PerEventSelectorOrReadyStateIsNotAcceptedOrIgnored(string field)
    {
        var n = JsonNode.Parse(Scenario().ToJson())!; n["calls"]![0]![field] = 1;
        Assert.ThrowsAny<Exception>(() => P28PostReturnSelectorScenario.Parse(n.ToJsonString()));
        if (field == "initialSelector013c") return;
        n = JsonNode.Parse(Scenario().ToJson())!; n[field] = 1;
        Assert.ThrowsAny<Exception>(() => P28PostReturnSelectorScenario.Parse(n.ToJsonString()));
    }
    [Theory]
    [InlineData(4)]
    [InlineData(255)]
    public void OutsideInitialSelectorDomainIsRefused(int value) => Assert.ThrowsAny<Exception>(() => Scenario((byte)value));
    [Theory]
    [InlineData("0.37.0")]
    [InlineData("0.36.0")]
    public void HistoricalIdentityCannotClaimM2ae(string version) => Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(new { runnerVersion = version }), P28PostReturnSelectorValidator.Operation));
    [Fact]
    public void HistoricalM2xStillAcceptsPerEventSelectorSnapshot()
    {
        var old = P28CalRtRoundTripTests.Scenario();
        var s = P28QuartetHandoffScenario.Create(old.InitialState.QuartetPrefix, old.Calls.Select(c => c with { Selector013c = 3 }).ToArray(), old.Provenance, old.TraceEventIndexes);
        Assert.All(P28QuartetHandoffScenario.Parse(s.ToJson()).Calls, c => Assert.Equal(3, c.Selector013c));
    }
    internal static JsonElement Before() => JsonSerializer.SerializeToElement(new { pc = 0x063E, accumulator = 0xBE0F, psw = 0xADCA, dd = false, lrb = 0x21, x1 = 6, x2 = 0, dp = 0xA5A5, usp = 0x5555, ssp = 0x7FE, registers = new[] { 231, 85, 191, 0, 85, 85, 85, 85 } });
    internal static JsonNode Fixture(int selector, int gate = 0xA5, int steps = 8)
    {
        var before = Before(); var own = P28PostReturnSelectorModel.Build(selector, 0xBE0F, 0xADCA, gate, 231);
        var events = own.Events.Take(steps).ToArray(); var accesses = own.Accesses.Take(steps == 0 ? 0 : own.AccessEnds[steps - 1]).ToArray();
        var after = JsonNode.Parse(before.GetRawText())!; var psw = steps == 0 ? 0xADCA : events[^1][5]; var stop = steps == 0 ? 0x063E : events[^1][1];
        after["pc"] = stop; after["accumulator"] = steps == 0 ? 0xBE0F : events[^1][3]; after["psw"] = psw; after["dd"] = false;
        foreach (var w in accesses.Where(v => v[3] == 1 && v[1] == 0x108)) after["registers"]![0] = w[4];
        return JsonSerializer.SerializeToNode(new
        {
            entry = before,
            exit = after,
            accesses,
            stage = new
            {
                sspAfter = 0x7FE,
                writes = accesses.Where(v => v[3] == 1).Select(v => new[] { v[1], v[2], v[4] }),
                events,
                result = new
                {
                    status = steps == 8 ? 0 : 1,
                    steps,
                    stopPc = stop,
                    outputs = Array.Empty<int>(),
                    programReads = Array.Empty<int>(),
                    usedAssumptions = Array.Empty<string>(),
                    error = steps == 8 ? null : "invented partial",
                    executedInstructionBytes = events.SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).ToArray(),
                    trace = events.Select((e, i) => new { pc = e[0], nextPc = e[1], instruction = P28PostReturnSelectorModel.Mnemonics[i], accumulator = e[3], psw = e[5] }).ToArray()
                }
            }
        })!;
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void IndependentProducerFormulaGateNeighborsAndUnmaskedR0AreExact(int selector)
    {
        foreach (var gate in new[] { 4, 0x55, 0xAE })
        {
            var r = P28PostReturnSelectorModel.Validate(JsonSerializer.SerializeToElement(Fixture(selector, gate)), Before(), selector, gate);
            Assert.Equal(0, r.Status); Assert.Equal(0x064C, r.After.GetProperty("pc").GetInt32()); Assert.Equal(0xBE00 | ((selector + 1) % 4), r.After.GetProperty("accumulator").GetInt32());
            Assert.Equal(selector + 1, r.After.GetProperty("registers")[0].GetInt32()); Assert.Equal(0x7FE, r.After.GetProperty("ssp").GetInt32());
            Assert.Equal(gate | (1 << (selector % 2)), r.Ram.Single(v => v[1] == 0x128 && v[3] == 1)[4]);
            Assert.Equal(gate & 4, r.Ram.Single(v => v[1] == 0x128 && v[3] == 1)[4] & 4); Assert.Equal(0, r.After.GetProperty("psw").GetInt32() & 0x2000);
        }
    }
    [Theory]
    [InlineData("pc")]
    [InlineData("old")]
    [InlineData("new")]
    [InlineData("width")]
    [InlineData("address")]
    [InlineData("r0")]
    [InlineData("gate")]
    [InlineData("hc")]
    [InlineData("zf")]
    [InlineData("cf")]
    [InlineData("dd")]
    [InlineData("ah")]
    [InlineData("ssp")]
    [InlineData("lrb")]
    [InlineData("pointer")]
    [InlineData("skip")]
    [InlineData("trace")]
    [InlineData("branch064c")]
    public void CorrectNextSelectorDoesNotExcuseForgedNativeEvidence(string fault)
    {
        var n = Fixture(3); var s = n["stage"]!;
        switch (fault)
        {
            case "pc": n["entry"]!["pc"] = 0x064A; break;
            case "old": n["accesses"]![0]![4] = 2; break;
            case "new": n["accesses"]!.AsArray()[^1]![4] = 4; break;
            case "width": n["accesses"]![0]![2] = 16; break;
            case "address": n["accesses"]![0]![1] = 0x13D; break;
            case "r0": n["exit"]!["registers"]![0] = 0; break;
            case "gate": n["accesses"]![2]![1] = 0x12A; break;
            case "hc": s["events"]![4]![5] = s["events"]![4]![5]!.GetValue<int>() ^ 8192; break;
            case "zf": n["exit"]!["psw"] = n["exit"]!["psw"]!.GetValue<int>() ^ 16384; break;
            case "cf": n["exit"]!["psw"] = n["exit"]!["psw"]!.GetValue<int>() ^ 32768; break;
            case "dd": n["exit"]!["dd"] = true; break;
            case "ah": n["exit"]!["accumulator"] = 0; break;
            case "ssp": n["exit"]!["ssp"] = 0x7FC; break;
            case "lrb": n["exit"]!["lrb"] = 0x20; break;
            case "pointer": n["exit"]!["x1"] = 99; break;
            case "skip": s["events"]!.AsArray().RemoveAt(0); break;
            case "trace": s["result"]!["trace"]![0]!["instruction"] = "RTI"; break;
            case "branch064c": s["result"]!["executedInstructionBytes"]!.AsArray().Add(0x064C); break;
        }
        Assert.ThrowsAny<Exception>(() => P28PostReturnSelectorModel.Validate(JsonSerializer.SerializeToElement(n), Before(), 3, 0xA5));
    }
    [Fact]
    public void PartialBeforeStoreRetainsR0AndGateWritesWithoutClaimingSelectorProducer()
    {
        var r = P28PostReturnSelectorModel.Validate(JsonSerializer.SerializeToElement(Fixture(3, 4, 7)), Before(), 3, 4);
        Assert.Equal(1, r.Status); Assert.Equal(0x064A, r.After.GetProperty("pc").GetInt32());
        Assert.Equal(4, r.After.GetProperty("registers")[0].GetInt32()); Assert.Contains(r.Ram, v => v[1] == 0x128 && v[3] == 1 && v[4] == 6);
        Assert.DoesNotContain(r.Ram, v => v[1] == 0x13C && v[3] == 1);
    }
    private static P28QuartetHandoffCheckpoint Prefix(int index, int selector, int[][] journal) => new(index, "QuartetHandoffStrict", "StrictMatch", selector, 0x3B6 + 2 * selector,
        new(0x22A5 + 3 * selector, index, 0, 17), 17, new(0x05EB, index, 1, 17), 17, [], JsonSerializer.SerializeToElement(new { continuityJournal = journal }));
    private static P28PostReturnSelectorValidation CompletedModelProducer()
    {
        // Model-only verified-caller boundary; not native ROM or RT evidence.
        var own = new P28PostReturnSelectorValidation(0);
        var g = new P28QuartetGeneration(0x064A, 0, 6, 1);
        var row = JsonSerializer.SerializeToElement(new
        {
            selectorBefore = 0,
            selectorAfter = 1,
            incomingSelectorGeneration = (object?)null,
            reader0584Generation = (object?)null,
            reader063eGeneration = (object?)null,
            selectorGeneration = g,
            selectorHandoff = "InitialSelectorControl",
            postReturn = Fixture(0),
            nativeRt = new { suffix = new { stage = new { result = new { steps = 1 } } } }
        }, JsonDefaults.Create());
        var prefix = Prefix(0, 0, [[1, 0x0584, 0x13C, 8, 0, 0]]);
        own.Start(0, 0, row, prefix);
        List<int[]> all = [[0, 0x063B, 0x7FE, 16, 1, 0x063E], [1, 0x5682, 0x24, 8, 1, 0xAF], [2, 0x55D5, 0x40, 8, 1, 0x83]];
        var ram = new Dictionary<int, int> { [0x128] = 0xA5 }; var retained = new Dictionary<int, int> { [0x13C] = 0 };
        var r = own.Finish(0, 0, row, Before(), "CallReturnStrict", ram, retained, [231, 85, 191, 0, 85, 85, 85, 85], all, prefix);
        Assert.Equal("PostReturnSelectorStrict", r.Disposition); Assert.Equal(g, own.Rows[0][0].SelectorGeneration);
        Assert.Equal(1, retained[0x13C]); Assert.Equal(6, g.WriteOrder); Assert.Equal("InitialSelectorControl", own.Rows[0][0].SelectorHandoff);
        return own;
    }
    [Fact]
    public void VerifiedProducerGenerationFeedsNextReaderWithAllNativeWritesOrdinal()
    {
        var own = CompletedModelProducer(); var g = own.Rows[0][0].SelectorGeneration;
        var row = JsonSerializer.SerializeToElement(new { selectorBefore = 1, incomingSelectorGeneration = g, reader0584Generation = g, selectorHandoff = "NativeSelectorHandoffStrict" }, JsonDefaults.Create());
        own.Start(0, 1, row, Prefix(1, 1, [[1, 0x0584, 0x13C, 8, 0, 1]]));
    }
    [Theory]
    [InlineData("event")]
    [InlineData("writer")]
    [InlineData("ordinal")]
    [InlineData("value")]
    [InlineData("hostWrite")]
    public void CorrectValueWrongGenerationOrEqualValueHostWriteIsRejected(string fault)
    {
        var own = CompletedModelProducer(); var g = own.Rows[0][0].SelectorGeneration!;
        var forged = fault switch { "event" => g with { EventIndex = 1 }, "writer" => g with { WriterPc = 0x0551 }, "ordinal" => g with { WriteOrder = 3 }, "value" => g with { Value = 2 }, _ => g };
        var row = JsonSerializer.SerializeToElement(new { selectorBefore = 1, incomingSelectorGeneration = forged, reader0584Generation = forged, selectorHandoff = "NativeSelectorHandoffStrict" }, JsonDefaults.Create());
        int[][] journal = fault == "hostWrite" ? [[0, 65536, 0x13C, 8, 1, 1], [1, 0x0584, 0x13C, 8, 0, 1]] : [[1, 0x0584, 0x13C, 8, 0, 1]];
        Assert.ThrowsAny<Exception>(() => own.Start(0, 1, row, Prefix(1, 1, journal)));
    }
}
