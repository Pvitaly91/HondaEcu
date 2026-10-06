using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

[Collection(TimingSensitiveTestCollection.Name)]
public sealed class P28AdaptiveFuelTests
{
    internal static P28AdaptiveFuelScenario Scenario() => P28AdaptiveFuelScenario.Create(
        new(P28LimiterFuelTests.Scenario().InitialState, 100, 110, 0, 0, 0xA55A, 0x5AA5),
        [new(P28LimiterFuelTests.Scenario().Calls[0], 1100, 0, false, false, true, true, true, false, 0, 0),
         new(P28LimiterFuelTests.Scenario().Calls[1], 1100, 0, true, false, false, true, true, false, 0, 0)],
        "Invented joint software stimuli; no physical scheduling", [0]);
    internal static byte[] Image()
    {
        var b = P28FuelMapExportTests.Image(); var numeric = P28AdaptiveTests.Image();
        foreach (var (a, n) in new[] { (0x1966, 6), (0x487D, 2), (0x4880, 2), (0x4886, 2), (0x4889, 2), (0x6493, 24), (0x5AB9, 2), (0x5AC3, 2), (0x48E4, 2) })
            Array.Copy(numeric, a, b, a, n);
        foreach (var a in new[] { 0x489A, 0x48A7, 0x48CA, 0x48AE }) b[a] = numeric[a];
        // Independently composed partial producer, no OEM helper/function fixture.
        new byte[] { 0x03, 0xE1, 0x48 }.CopyTo(b, 0x487B);
        new byte[] { 0x67, 88, 0, 0xD3, 0x24, 0x47, 0x81 }.CopyTo(b, 0x48E1);
        return b;
    }
    [Fact]
    public void ClosedScenarioHasOneHistoryAndRefusesProducedValuesConflictingMasksAndUnboundedTicks()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28AdaptiveFuelScenario.Parse(s.ToJson()).Digest);
        foreach (var kind in Enum.GetValues<P28AdaptiveFuelMutationKind>())
        { var ab = P28AdaptiveFuelScenario.Create(s.InitialState, s.Calls, s.Provenance, mutation: new(kind, 101)); Assert.Equal(ab.Digest, P28AdaptiveFuelScenario.Parse(ab.ToJson()).Digest); }
        foreach (var field in new[] { "ramCut", "ramResume", "timer", "request", "gate", "data0124", "data012b", "factor0158", "channelMask", "p4Bit0", "context", "pc", "formula", "data021f" })
        { var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]![field] = 1; Assert.ThrowsAny<Exception>(() => P28AdaptiveFuelScenario.Parse(n.ToJsonString())); }
        foreach (var edit in new Action<JsonNode>[] {
            n=>n["calls"]![0]!["timerTicks"]=33, n=>n["calls"]![0]!["counterTicks"]=255,
            n=>n["calls"]![1]!["fuel"]!["index"]=0, n=>n["calls"]![0]!["fuel"]!["sources"]!["factor0158"]=1,
            n=>n["initialState"]!["joint"]!["fuel"]!["consumerOutput0140"]=1, n=>n["formatVersion"]=2,
            n=>n["purpose"]="adaptive-limiter-software-test", n=>n["traceCallIndexes"]=new JsonArray(0,0),
            n=>n["mutation"]=new JsonObject{["kind"]=0,["value"]=1}, n=>n["mutation"]=new JsonObject{["kind"]="offset",["value"]=1},
            n=>n["calls"]![0]=null })
        { var n = JsonNode.Parse(s.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28AdaptiveFuelScenario.Parse(n.ToJsonString())); }
        Assert.Throws<ArgumentException>(() => P28AdaptiveFuelScenario.Create(s.InitialState, Enumerable.Range(0, 65).Select(i => s.Calls[0] with { Fuel = s.Calls[0].Fuel with { Index = i } }).ToArray(), "bounded"));
        Assert.Throws<InvalidDataException>(() => P28AdaptiveFuelScenario.Parse(s.ToJson().Replace("\"bank1\": false", "\"bank1\": false, \"bank1\": true", StringComparison.Ordinal)));
        var request = JsonSerializer.SerializeToElement(P28AdaptiveFuelValidator.CreateRequest(RomImage.FromBytes(Image()), s), JsonDefaults.Create());
        Assert.Equal(P28AdaptiveFuelValidator.Operation, request.GetProperty("operation").GetString());
        Assert.False(request.TryGetProperty("adaptiveLimiter", out _)); Assert.False(request.TryGetProperty("limiterFuelGateChain", out _));
    }
    [Fact]
    public void ProductionOnlyKeepsMasksAndCombinedFuelHistoryAndRetainedBankGeneration()
    {
        var initial = P28AdaptiveTests.Initial() with { Limiter = P28AdaptiveTests.Initial().Limiter with { Data012A = 130, Data018F = 254, Data012B = 173 } };
        var m = new P28AdaptiveModel(P28AdaptiveTests.Image(), initial);
        var reset = m.StepProduction(P28AdaptiveTests.Call() with { Reset214 = true });
        Assert.Equal(initial.Limiter.Data012A, reset.After.Limiter.Data012A); Assert.Equal(initial.Limiter.Data018F, reset.After.Limiter.Data018F);
        Assert.Equal(initial.Limiter.Data0124, reset.After.Limiter.Data0124);
        var d = m.StepDecision(100, false); Assert.Equal(100, d.Threshold); Assert.False(d.OverspeedRequest);
        m.AcceptModeledFuelByte((byte)(d.After.Data012B & ~8));
        var update = m.StepProduction(P28AdaptiveTests.Call(1)); Assert.Equal(37, update.Before.Limiter.Data012B);
        var held = m.StepProduction(P28AdaptiveTests.Call(2) with { Bank1 = true });
        Assert.Equal("TimerHold", held.Path); Assert.Equal(update.After.Limiter.RamCut, held.After.Limiter.RamCut);
        Assert.Equal(0x64A1, held.TableReads[0][1]); Assert.DoesNotContain(held.ProducerWrites, w => w[0] is 0x1A4 or 0x1A6 or 0x12A or 0x18F);
        var fixedDecision = m.StepDecision(499, true); Assert.Equal("Fixed", fixedDecision.Context);
        Assert.Equal(500, fixedDecision.Threshold); Assert.Equal(held.After.Limiter.RamCut, fixedDecision.Before.RamCut);
    }
    [Fact]
    public void OneWordAdmissionProtectsCoefficientsOtherBankFixedAndFuelAndDoesNotIssueExport()
    {
        var b = Image(); b[0x1966] = 0x62; b[0x1969] = 0x67; var original = RomImage.FromBytes(b);
        foreach (var kind in Enum.GetValues<P28AdaptiveFuelMutationKind>())
        {
            var mapping = P28AdaptiveFuelValidator.Mapping(kind); var old = P28LimiterInspector.Word(original.Span, mapping.Offset);
            var mutation = new P28AdaptiveFuelMutation(kind, (ushort)(old + 1)); var child = P28AdaptiveFuelValidator.Mutate(original, mutation);
            Assert.Equal(old + 1, P28LimiterInspector.Word(child.Span, mapping.Offset));
            foreach (var offset in new[] { 0x64A9, 0x64AA, 0x196A, 0x1967, 0x7050, 0x487B })
                Assert.Throws<SliceProcessException>(() => P28AdaptiveFuelValidator.AdmitMutation(original, child.CreateModifiedCopy([new BytePatch(offset, [(byte)(child.Span[offset] ^ 1)])]), mutation));
            Assert.Throws<ArgumentException>(() => P28AdaptiveFuelValidator.Mutate(original, new(kind, (ushort)(old + 9))));
            Assert.Throws<ArgumentException>(() => P28AdaptiveFuelValidator.Mutate(original, new(kind, old)));
        }
    }
    [Fact]
    public void OwnRomRamOracleDistinguishesFixedFetchFromRamComparisonAndPriorResume()
    {
        var image = RomImage.FromBytes(P28LimiterTests.Image(500, 510));
        foreach (var prior in new byte[] { 0, 32 })
        {
            var state = new P28LimiterState(prior, 173, 130, 254, 7, 100, 110);
            var ram = P28LimiterDecisionEvidence.Build(image, state, 105, 99, false, 5);
            Assert.Equal(prior == 0 ? 100 : 110, ram.Events.Single(e => e[0] == 0x197D)[7]);
            Assert.Equal(500, ram.Events.Single(e => e[0] == 0x1969)[3]);
            Assert.Equal(510, ram.DpEnds[0]); Assert.Equal(110, ram.Dp);
            Assert.Equal(new[] { 0x1A6, 0x1A4 }, ram.Accesses.Where(a => a[1] is 0x1A4 or 0x1A6).Select(a => a[1]));
            Assert.DoesNotContain(ram.Accesses, a => a[1] is 0x12A or 0x18F);
            var fixedControl = P28LimiterDecisionEvidence.Build(image, state, 105, 99);
            Assert.DoesNotContain(fixedControl.Accesses, a => a[1] is 0x1A4 or 0x1A6);
        }
    }
    [Fact]
    public async Task PartialPairStopsDownstreamAndRejectsCorrectFinalNumbersWithoutProducer()
    {
        var scenario = Scenario(); var image = RomImage.FromBytes(Image());
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28AdaptiveFuelValidator.CreateRequest(image, scenario));
        var report = P28AdaptiveFuelValidator.Analyze(image, scenario, response.Response, "A");
        foreach (var seq in report)
        {
            var c = seq.Checkpoints; Assert.Equal("Unresolved", c[0].Disposition); Assert.Equal("NotRun", c[0].ThresholdProvenance); Assert.Null(c[0].Request); Assert.Null(c[0].Continuation);
            Assert.Equal(88, c[0].RamCutAfter); Assert.Equal(110, c[0].RamResumeAfter); Assert.Equal("NotRun", c[1].Disposition);
            Assert.Equal(c[0].RamCutAfter, c[1].RamCutBefore); Assert.Null(c[1].Actual.GetProperty("input").Deserialize<object>());
        }
        foreach (var edit in new Action<JsonNode>[] {
            n=>n["runnerVersion"]="0.22.0", n=>n["operation"]="adaptiveLimiter",
            n=>n["entryContracts"]![0]!["formatVersion"]=2,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![0]!["producer"]=null,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![0]!["stateAfter"]!["ramCut"]=100,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![0]!["snapshotWrites"]![0]![2]=2,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![0]!["producer"]!["transitionWrites"]![0]![2]=32,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![0]!["producer"]!["entry"]!["ssp"]=0,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![0]!["joint"]!["fuel"]!["store03a2"]=0,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![0]!["stateAfterProducer"]!["ramCut"]=100,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![1]!["joint"]!["stateBefore"]!["data0124"]=0,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![1]!["status"]=0,
            n=>n["adaptiveFuelSequences"]![0]!["checkpoints"]![1]!["snapshotWrites"]=new JsonArray(new JsonArray(0x1A4,16,100)) })
        { var n = JsonNode.Parse(response.Response.GetRawText())!; edit(n); Assert.ThrowsAny<Exception>(() => P28AdaptiveFuelValidator.Analyze(image, scenario, JsonSerializer.SerializeToElement(n), "A")); }
    }
    [Fact]
    public async Task JointTransportKeepsAlreadyCancelledTimeoutAndActiveChildCancellationDistinct()
    {
        var host = ProcessHandshake.HostPath;
        var request = P28AdaptiveFuelValidator.CreateRequest(RomImage.FromBytes(Image()), Scenario());
        var marker = Path.Combine(Path.GetTempPath(), $"never-started-{Guid.NewGuid():N}.pid");
        using var cancelled = new CancellationTokenSource(); cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => SeededSliceProcess.ExchangeAsync("dotnet", request,
            new SliceProcessOptions { Arguments = [host, "pid-sleep", marker] }, cancelled.Token));
        Assert.False(File.Exists(marker));
        var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync("dotnet", request,
            new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) }));
        Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
        await ProcessHandshake.AssertActiveCancellationAsync((options, token) => SeededSliceProcess.ExchangeAsync("dotnet", request, options, token));
    }
    [Theory]
    [InlineData(99, 12, 0, 12)]
    [InlineData(100, 12, 12, 12)]
    [InlineData(101, 0, 0, 0)]
    public async Task InventedOddTableToRamComparisonBitGateAndSeparateStores(ushort raw, byte numeric, int a, int b)
    {
        // A new linear program at address0, not an OEM helper or routine copy.
        byte[] code = [0x91, 0xA9, 1, 0, 0xD4, 0xA4, 0xE4, 0xA4, 0xB5, 0xC4, 0xC1, 0xC4, 0x24, 0x3D, 0x67, numeric, 0, 0x8B, 0xDD, 0x24, 1, 0xF9, 0x62, 0xA2, 3, 0xD2, 0x37, 0x62, 0xB4, 3, 0xD2];
        var rom = new byte[0x103]; code.CopyTo(rom, 0); rom[0x101] = 100;
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "invented", rom = rom.Select(v => (int)v).ToArray() } },
            scratchPatterns = new[] { 170 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { code.Length },
                allowedCodeRanges = new[] { new[] { 0, code.Length } },
                psw = 0x1101,
                lrb = 0x20,
                usp = 0x280,
                instructionBudget = 32,
                dataSeeds = new[] { new[] { 0x8A, 0 }, new[] { 0x8B, 1 }, new[] { 0xC4, raw & 255 }, new[] { 0xC5, raw >> 8 }, new[] { 0x124, 0xD5 } },
                outputAddresses = new[] { 0x1A4, 0x1A5, 0x124, 0x3A2, 0x3A3, 0x3B4, 0x3B5 }
            }
        });
        var r = response.Response.GetProperty("syntheticResult"); Assert.Equal(0, r.GetProperty("status").GetInt32());
        Assert.Equal(new[] { 100, 0, raw < 100 ? 0xF5 : 0xD5, a, 0, b, 0 }, r.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        Assert.Equal(new[] { 0x101, 0x102 }, r.GetProperty("programReads").EnumerateArray().Select(v => v.GetInt32()));
    }
}
