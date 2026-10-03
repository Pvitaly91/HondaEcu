using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28LimiterFuelTests
{
    internal static P28LimiterFuelScenario Scenario() => P28LimiterFuelScenario.Create(
        new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0xF1, 0xAD, 7, 16, 128, 0xA5),
        [new(0, 89, 0, 0, 0, P28FuelFactorTests.Sources()), new(1, 129, 255, 255, 255, P28FuelFactorTests.Sources() with { Source015a = 0 })],
        "Invented software stimuli, not physical RPM", [0]);

    [Fact]
    public void ClosedScenarioAcceptsInitialBit4ButRejectsPerEventResultsAndForeignMutations()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28LimiterFuelScenario.Parse(s.ToJson()).Digest);
        foreach (var mutation in new P28LimiterFuelMutation[] { new(P28LimiterFuelMutationKind.FixedCut, 91, null, null, null), new(P28LimiterFuelMutationKind.FixedResume, 130, null, null, null), new(P28LimiterFuelMutationKind.FuelCell, 3, "map_0", 0, 0) })
        { var ab = P28LimiterFuelScenario.Create(s.InitialState, s.Calls, s.Provenance, mutation: mutation); Assert.Equal(ab.Digest, P28LimiterFuelScenario.Parse(ab.ToJson()).Digest); }
        foreach (var edit in new Action<JsonNode>[] {
            n=>n["calls"]![0]!["callerGate0124"]=0, n=>n["calls"]![0]!["request"]=true,
            n=>n["calls"]![0]!["data012b"]=0, n=>n["calls"]![0]!["channelMask"]=255,
            n=>n["calls"]![0]!["p4Bit0"]=false, n=>n["calls"]![0]!["fixedCut"]=100,
            n=>n["calls"]![0]!["sources"]!["factor0158"]=512, n=>n["calls"]![0]!["sources"]!["source0144"]=256,
            n=>n["initialState"]!["data0121"]=128, n=>n["initialState"]!["fuel"]!["consumerOutput0140"]=1,
            n=>n["calls"]![0]=null, n=>n["calls"]![1]!["index"]=0, n=>n["formatVersion"]=2,
            n=>n["purpose"]="fuel-factor-native-software-test", n=>n["traceCallIndexes"]=new JsonArray(0,0),
            n=>n["mutation"]=new JsonObject { ["kind"]="offset",["value"]=1,["mapId"]=null,["row"]=null,["column"]=null },
            n=>n["mutation"]=new JsonObject { ["kind"]=0,["value"]=1,["mapId"]=null,["row"]=null,["column"]=null } })
        { var n = JsonNode.Parse(s.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28LimiterFuelScenario.Parse(n.ToJsonString())); }
        Assert.Throws<ArgumentException>(() => P28LimiterFuelScenario.Create(s.InitialState, new P28LimiterFuelCall[] { null! }, "null"));
        Assert.Throws<ArgumentException>(() => P28LimiterFuelScenario.Create(s.InitialState, s.Calls, "bad", mutation: new(P28LimiterFuelMutationKind.FixedCut, 90, "map_0", 0, 0)));
        var r = JsonSerializer.SerializeToElement(P28LimiterFuelValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal(0xF1, r.GetProperty("limiterFuelGateChain").GetProperty("initialState").GetProperty("data0124").GetInt32());
        Assert.False(r.GetProperty("limiterFuelGateChain").GetProperty("initialState").TryGetProperty("callerGate0124", out _));
    }

    [Fact]
    public void DecisionOnlyPreservesMaskAndOwnCombinedByteAcrossHysteresis()
    {
        var initial = new P28LimiterState(0xD1, 0xAD, 0x82, 0xFE, 7, 1, 2);
        var model = new P28LimiterModel(P28LimiterTests.Image(90, 129), initial);
        var a = model.StepDecision(89, false, true); Assert.True(a.OverspeedRequest); Assert.Equal(90, a.Threshold);
        Assert.Equal(0, a.After.Data0124 & 16); Assert.Equal(0x2D, a.After.Data012B);
        var ownAdditive = (byte)(a.After.Data012B & ~8); model.AcceptModeledFuelByte(ownAdditive);
        var b = model.StepDecision(90, false, true); Assert.Equal(129, b.Threshold); Assert.True(b.OverspeedRequest);
        Assert.Equal(ownAdditive, b.Before.Data012B); Assert.Equal(initial.Data012A, b.After.Data012A); Assert.Equal(initial.Data018F, b.After.Data018F);
        var equal = model.StepDecision(129, false, true); Assert.False(equal.OverspeedRequest); Assert.Equal(20, equal.After.Data01D7);
        Assert.Equal(90, model.StepDecision(100, false, true).Threshold);
        Assert.DoesNotContain(a.DecisionWrites, w => w[0] is 0x18F or 0x12A);
        // The legacy wrapper retains its separate mask-consumer behavior.
        var legacy = new P28LimiterModel(P28LimiterTests.Image(90, 129), initial with { Data012A = 0 }).Step(new(0, 129, false, true, 0xF1));
        Assert.NotEmpty(legacy.ConsumerWrites); Assert.Equal(0xF0, legacy.After.Data018F);
    }

    [Fact]
    public void ModelOnlyFullRawDomainUsesOwnPreviousThresholdNotSwappedOrPhysicalUnits()
    {
        var count = 0;
        var inventedRom = P28LimiterTests.Image(90, 129);
        foreach (var prior in new byte[] { 0, 32 }) for (var raw = 0; raw <= 65535; raw++)
            {
                var step = new P28LimiterModel(inventedRom, P28LimiterTests.Initial(prior)).StepDecision((ushort)raw, false, true);
                Assert.Equal(raw < (prior == 0 ? 90 : 129), step.OverspeedRequest); Assert.Equal(prior == 0 ? 90 : 129, step.Threshold); count++;
            }
        Assert.Equal(131072, count); // Independent projections only; zero native corpus events.
    }

    [Fact]
    public void NativeGenerationRequiresOrderedByteWritersAndTwoReadersNotInitialOrHostSeed()
    {
        int[][] good = [[0x1A23, 0x124, 8, 1, 52], [0x1A28, 0x124, 8, 1, 36], [0x1A35, 0x124, 8, 1, 44], [0x217A, 0x124, 8, 0, 44], [0x21F5, 0x124, 8, 0, 44]];
        Assert.True(P28LimiterFuelValidator.SharedBitHandoffMatches(good, 44));
        Assert.False(P28LimiterFuelValidator.SharedBitHandoffMatches(good.Skip(3).ToArray(), 44));
        Assert.False(P28LimiterFuelValidator.SharedBitHandoffMatches([good[3], .. good.Take(3), good[4]], 44));
        foreach (var bad in new int[][] { [0, 0x124, 8, 1, 44], [0x1A23, 0x124, 16, 1, 52], [0x21F5, 0x124, 8, 0, 12] })
        {
            var copy = good.Select(w => w.ToArray()).ToArray(); if (bad[0] == 0) copy = [.. copy.Take(3), bad, .. copy.Skip(3)]; else copy[bad[0] == 0x1A23 ? 0 : 4] = bad;
            Assert.False(P28LimiterFuelValidator.SharedBitHandoffMatches(copy, 44));
        }
    }

    [Fact]
    public void JointAdmissionIsOneExistingFieldAndDoesNotLoosenOldFuelGuard()
    {
        var bytes = P28FuelMapExportTests.Image(); var thresholds = P28LimiterTests.Image(90, 129); Array.Copy(thresholds, 0x1966, bytes, 0x1966, 6);
        var image = RomImage.FromBytes(bytes); var mutation = new P28LimiterFuelMutation(P28LimiterFuelMutationKind.FixedCut, 0xABCD, null, null, null);
        var child = P28LimiterFuelValidator.Mutate(image, mutation); Assert.Equal(0xABCD, P28LimiterInspector.Word(child.Span, 0x196A)); Assert.Equal(0x67, child.Span[0x1969]);
        Assert.Throws<InvalidDataException>(() => P28LimiterFuelValidator.AdmitMutation(image, child.CreateModifiedCopy([new BytePatch(0x1969, [0])]), mutation));
        Assert.Throws<InvalidDataException>(() => P28FuelMapInspector.AdmitMutation(image, child, new("map_0", 0, 0, 3)));
    }

    [Theory]
    [InlineData(99, 12, 0, 12)]
    [InlineData(100, 12, 12, 12)]
    [InlineData(100, 0, 0, 0)]
    public async Task RealRustInventedCompareBitStoreGateReadAndTwoNativeStores(ushort raw, byte numeric, int a, int b)
    {
        // Independently composed probe, NOT an OEM limiter/helper copy.
        var program = new byte[] { 0x67, 100, 0, 0xB5, 0xC4, 0xC1, 0xC4, 0x24, 0x3D, 0x67, numeric, 0, 0x8B, 0xDD, 0x24, 1, 0xF9, 0x62, 0xA2, 3, 0xD2, 0x37, 0x62, 0xB4, 3, 0xD2 };
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "synthetic", rom = program.Select(v => (int)v).ToArray() } },
            scratchPatterns = new[] { 170 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { program.Length },
                allowedCodeRanges = new[] { new[] { 0, program.Length } },
                psw = 0x0101,
                lrb = 0x20,
                usp = 0x280,
                instructionBudget = 32,
                dataSeeds = new[] { new[] { 0xC4, raw & 255 }, new[] { 0xC5, raw >> 8 }, new[] { 0x124, 0xD5 } },
                outputAddresses = new[] { 0x124, 0x3A2, 0x3A3, 0x3B4, 0x3B5 }
            }
        });
        Assert.Equal("0.30.0", response.Response.GetProperty("runnerVersion").GetString()); var r = response.Response.GetProperty("syntheticResult"); Assert.Equal(0, r.GetProperty("status").GetInt32());
        Assert.Equal(new[] { raw < 100 ? 0xF5 : 0xD5, a, 0, b, 0 }, r.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        var trace = r.GetProperty("trace").EnumerateArray().ToArray(); Assert.Contains(trace, e => e.GetProperty("pc").GetInt32() == 6);
        Assert.Contains(trace, e => e.GetProperty("pc").GetInt32() == 13 && e.GetProperty("nextPc").GetInt32() == (raw < 100 ? 16 : 17));
    }

    [Fact]
    public async Task RealPartialDecisionKeepsExecutedPrefixThenRefusesForgedSuffixAndWrongIdentity()
    {
        var image = RomImage.FromBytes(PartialImage()); var s = Scenario(); var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28LimiterFuelValidator.CreateRequest(image, s));
        var reports = P28LimiterFuelValidator.Analyze(image, s, response.Response, "A");
        foreach (var seq in reports) { Assert.Equal("Unresolved", seq.Checkpoints[0].Disposition); Assert.Null(seq.Checkpoints[0].Request); Assert.Equal("NotRun", seq.Checkpoints[1].Disposition); }
        foreach (var change in new Action<JsonNode>[] {
            n=>n["runnerVersion"]="0.21.0", n=>n["operation"]="fuelFactorProductionChain",
            n=>n["limiterFuelSequences"]![0]!["checkpoints"]![0]!["decisionEntry"]!["lrb"]=0x40,
            n=>n["limiterFuelSequences"]![0]!["checkpoints"]![0]!["transitionToDecisionWrites"]![0]![0]=0x124,
            n=>n["limiterFuelSequences"]![0]!["checkpoints"]![0]!["decision"]!["events"]![1]![3]=91,
            n=>n["limiterFuelSequences"]![0]!["checkpoints"]![1]!["fuel"]!["store03a2"]=0,
            n=>n["limiterFuelSequences"]![0]!["checkpoints"]![1]!["decisionEntry"]=n["limiterFuelSequences"]![0]!["checkpoints"]![0]!["decisionEntry"]!.DeepClone(),
            n=>n["limiterFuelSequences"]![0]!["checkpoints"]![1]!["fuel"]!["sourcesAfter"]!["source015a"]=1,
            n=>n["limiterFuelSequences"]![0]!["checkpoints"]![0]!["stateAfterDecision"]!["data012b"]=0 })
        { var forged = JsonNode.Parse(response.Response.GetRawText())!; change(forged); Assert.ThrowsAny<Exception>(() => P28LimiterFuelValidator.Analyze(image, s, JsonSerializer.SerializeToElement(forged), "A")); }
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => SeededSliceProcess.ExchangeAsync("dotnet", P28LimiterFuelValidator.CreateRequest(image, s), new SliceProcessOptions { Arguments = [host, "timeout"] }, cancellation.Token));
        var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync("dotnet", P28LimiterFuelValidator.CreateRequest(image, s), new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) })); Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
    }
    internal static byte[] PartialImage()
    { var b = P28LimiterTests.Image(90, 129); b[0x196C] = 0x47; b[0x196D] = 0x81; return b; }

    [Fact]
    public void CallerEvidenceCannotReplaceNativeBranchWithResetOrIssuedStaleOutputs()
    {
        JsonElement Boundary(int pc) => JsonSerializer.SerializeToElement(new { pc, accumulator = 1234, psw = 0x0DC9, dd = false, lrb = 0x20, x1 = 12, x2 = 34, dp = 129, usp = 0x280, ssp = 0x7FE, registers = new int[8] });
        var entry = Boundary(0x217A); var exit = Boundary(0x2194);
        JsonElement Result(bool complete) => JsonSerializer.SerializeToElement(new
        {
            status = complete ? 0 : 1,
            usedAssumptions = Array.Empty<string>(),
            steps = complete ? 1 : 0,
            stopPc = complete ? 0x2194 : 0x217A,
            outputs = Array.Empty<int>(),
            programReads = Array.Empty<int>(),
            trace = complete ? new[] { new { pc = 0x217A, nextPc = 0x2194, instruction = "invented gate observation", accumulator = 1234, psw = 0x0DC9 } } : [],
            error = complete ? null : "Unsupported exact form",
            executedInstructionBytes = complete ? new[] { 0x217A, 0x217B, 0x217C } : []
        });
        var stage = JsonSerializer.SerializeToElement(new { result = Result(true), writes = Array.Empty<int[]>(), events = new[] { new[] { 0x217A, 0x2194, 1234, 1234, 0x0DC9, 0x0DC9, 65536, 65536 } }, sspAfter = 0x7FE });
        var row = JsonSerializer.SerializeToElement(new { callerEntry = entry, callerExit = exit, callerGate = stage, boundaries = new[] { exit } });
        P28LimiterFuelValidator.ValidateCaller(row);
        foreach (var edit in new Action<JsonNode>[] { n => n["callerExit"]!["lrb"] = 0x40, n => n["callerExit"]!["dp"] = 0, n => n["callerGate"]!["events"]![0]![1] = 0x2193, n => n["callerGate"]!["result"]!["executedInstructionBytes"] = new JsonArray() })
        { var n = JsonNode.Parse(row.GetRawText())!; edit(n); Assert.Throws<SliceProcessException>(() => P28LimiterFuelValidator.ValidateCaller(JsonSerializer.SerializeToElement(n))); }
        var failed = JsonSerializer.SerializeToElement(new
        {
            callerEntry = entry,
            callerExit = entry,
            callerGate = new { result = Result(false), writes = Array.Empty<int[]>(), events = Array.Empty<int[]>(), sspAfter = 0x7FE },
            stages = Array.Empty<int>(),
            boundaries = Array.Empty<int>(),
            correction = (int?)null,
            component = (int?)null,
            corrected = (int?)null,
            store03a2 = (int?)null,
            store03b4 = (int?)null
        });
        P28LimiterFuelValidator.ValidateIncompleteCaller(failed, 1);
        var forged = JsonNode.Parse(failed.GetRawText())!; forged["store03a2"] = 0; Assert.Throws<SliceProcessException>(() => P28LimiterFuelValidator.ValidateIncompleteCaller(JsonSerializer.SerializeToElement(forged), 1));
    }
}
