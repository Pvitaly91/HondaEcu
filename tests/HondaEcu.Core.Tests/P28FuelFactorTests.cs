using System.Diagnostics;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

[Collection(TimingSensitiveTestCollection.Name)]
public sealed class P28FuelFactorTests
{
    internal static P28FuelFactorSources Sources() => new(65535, 65535, 255, 65535, 65535, 255, 255, 0, 0, 255, 107, 0, 0, 0, 0, 0, 0, 0, 0);
    internal static P28FuelFactorScenario Scenario() => P28FuelFactorScenario.Create(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0, 8, 16, 128, 0),
        [new(0, 0, 0, 0, Sources()), new(1, 255, 255, 255, Sources() with { Source015a = 12345 })], "Invented upstream software snapshots", [0]);

    [Fact]
    public void ClosedScenarioHasNoReadyFactorOrSourceCarrierInjection()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28FuelFactorScenario.Parse(s.ToJson()).Digest);
        foreach (var change in new Action<JsonNode>[] {
            n=>n["calls"]![0]!["sources"]!["factor0158"]=0,n=>n["initialState"]!["factor0158"]=512,
            n=>n["calls"]![0]!["sources"]!["source015f"]=1,n=>n["calls"]![0]!["sources"]!["source015e"]=256,
            n=>n["calls"]![0]!["sources"]!["source0144"]=256,n=>n["calls"]![0]!["sources"]!["data0140"]=1,
            n=>n["calls"]![0]!["mapId"]="map_1",n=>n["calls"]![0]!["selector0127"]=0,n=>n["calls"]![0]!["producerMode012c"]=0,
            n=>n["calls"]![0]!["expectedFactor"]=9,n=>n["calls"]![0]!["pc"]=0x7A99,n=>n["calls"]![0]!["ram"]=new JsonObject(),
            n=>n["calls"]![0]!["sources"]!["er1"]=9,n=>n["calls"]![0]!["sources"]=null,n=>n["calls"]![1]!["index"]=0,
            n=>n["initialState"]!["callerGate0124"]=16,n=>n["initialState"]!["fuel"]!["consumerOutput0140"]=1,
            n=>n["formatVersion"]=2,n=>n["purpose"]="fuel-additive-native-software-test",n=>n["traceCallIndexes"]=new JsonArray(0,0) })
        { var n = JsonNode.Parse(s.ToJson())!; change(n); Assert.ThrowsAny<Exception>(() => P28FuelFactorScenario.Parse(n.ToJsonString())); }
        Assert.Throws<ArgumentException>(() => P28FuelFactorScenario.Create(s.InitialState, Enumerable.Range(0, 65).Select(i => s.Calls[0] with { Index = i }).ToArray(), "too many"));
        var request = JsonSerializer.SerializeToElement(P28FuelFactorValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.False(request.GetProperty("fuelFactorProductionChain").GetProperty("calls")[0].GetProperty("sources").TryGetProperty("factor0158", out _));
        Assert.Empty(request.GetProperty("allowAssumptions").EnumerateArray());
    }

    [Fact]
    public void FiniteFinalSourceDomainAuditIsModelOnlyAndEveryLegalFactorIsReachable()
    {
        var count = 0;
        foreach (var mode in new byte[] { 0, 16 })
        {
            var domain = new HashSet<int>();
            for (var raw = 0; raw <= 65535; raw++)
            { var p = P28FuelFactorModel.Project(Sources() with { Source015a = (ushort)raw }, mode, 128, 0); domain.Add(p.NativeFactor0158); count++; }
            Assert.Equal(Enumerable.Range(0, mode == 0 ? 254 : 2038), domain.Order());
        }
        Assert.Equal(131072, count); // Model-only projections, not native ROM executions.
        var max = P28FuelFactorModel.Project(Sources(), 16, 128, 0);
        Assert.Equal(65152, max.After0168); Assert.Equal(65151, max.After0162); Assert.True(max.Saturated0160);
        Assert.Equal(65535, max.Narrowed0160); Assert.Equal(2039, max.AfterMode); Assert.Equal(2038, max.After015c); Assert.Equal(2037, max.NativeFactor0158);
        Assert.Equal(253, P28FuelFactorModel.Project(Sources(), 0, 128, 0).NativeFactor0158);
    }

    [Fact]
    public void IndependentOrderedPathPreservesCanariesAndNativeHysteresisHistory()
    {
        foreach (var b in new byte[] { 0, 1, 127, 255 }) foreach (var optional in new byte[] { 0, 1, 255 }) foreach (var gain in new ushort[] { 0, 1, 1024, 65535 })
                    foreach (var mode in new byte[] { 0, 16 }) foreach (var selector in new byte[] { 0, 128 }) foreach (var hysteresis in new byte[] { 0xA5, 0xE5 })
                            {
                                var s = Sources() with { Source0164 = b, Source0165 = (byte)(255 - b), Source0166 = optional, Source0167 = optional, Source0160 = gain };
                                var p = P28FuelFactorModel.Project(s, mode, selector, hysteresis); var own = P28FuelFactorEvidence.Build(s, mode, selector, hysteresis, 0xBEEF, 0x0DC9, 111, 222, 333, 444);
                                Assert.Equal(p.NativeFactor0158, own.Er1); Assert.Equal(p.HysteresisAfter, own.Hysteresis); Assert.Equal(333, own.Er2); Assert.Equal(444, own.Er3);
                                Assert.Contains(own.Accesses, a => a.SequenceEqual(new[] { 0x7A99, 0x158, 16, 1, p.NativeFactor0158 })); Assert.DoesNotContain(own.Events, e => e[0] == 0x1FA6);
                            }
        var clear = P28FuelFactorModel.Project(Sources() with { Source0133 = 106 }, 0, 128, 0xA5); Assert.Equal(0xA5, clear.HysteresisAfter);
        var set = P28FuelFactorModel.Project(Sources() with { Source0133 = 107 }, 0, 128, clear.HysteresisAfter); Assert.Equal(0xE5, set.HysteresisAfter);
        var retained = P28FuelFactorModel.Project(Sources() with { Source0133 = 103 }, 0, 128, set.HysteresisAfter); Assert.Equal(0xE5, retained.HysteresisAfter);
        var equal = P28FuelFactorModel.Project(Sources() with { Source0133 = 102 }, 0, 128, retained.HysteresisAfter); Assert.Equal(0xA5, equal.HysteresisAfter);
    }

    [Fact]
    public void SeparateFactorGenerationRejectsStaleSwappedWidthAndOverlappingWrites()
    {
        int[][] good = [[0x7A99, 0x158, 16, 1, 12], [0x21DD, 0x158, 16, 0, 12]];
        Assert.True(P28FuelFactorValidator.FactorHandoffMatches(good, 12, true));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([good[1]], 12, true));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([good[1], good[0]], 12, true));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([good[0], [0x21DD, 0x158, 8, 0, 12]], 12, true));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([[0x7A99, 0x258, 16, 1, 12], good[1]], 12, true));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([good[0], [0, 0x158, 8, 1, 12], good[1]], 12, true));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([good[0], [0, 0x159, 8, 1, 0], good[1]], 12, true));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([good[0], [0x21DD, 0x158, 16, 0, 40]], 12, true));
        Assert.True(P28FuelFactorValidator.FactorHandoffMatches([good[0]], 12, false));
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches([], 12, false)); // An initial/stale seed is not produced or Held.
    }

    [Fact]
    public void ExecutedHostInputWritesCannotHideTheOldFactorSetter()
    {
        var call = Scenario().Calls[0]; var s = call.Sources;
        int[][] good = [[0x238,8,call.RawMap0Rpm],[0xC2,8,call.RawMap1Rpm],[0xBF,8,call.RawLoad],
            [0x15A,16,s.Source015a],[0x15C,16,s.Source015c],[0x160,16,s.Source0160],[0x162,16,s.Source0162],
            [0x15E,8,s.Source015e],[0x164,8,s.Source0164],[0x165,8,s.Source0165],[0x166,8,s.Source0166],[0x167,8,s.Source0167],[0x168,8,s.Source0168],[0x133,8,s.Source0133],
            [0x142,16,s.Source0142],[0x144,16,s.Source0144],[0x146,16,s.Source0146],[0x14A,16,s.Source014a],[0x14C,16,s.Source014c],
            [0x148,8,s.Source0148],[0x149,8,s.Source0149],[0xF2,8,s.Counter00f2]];
        P28FuelFactorValidator.ValidateInputWrites(JsonSerializer.SerializeToElement(good), call, true);
        foreach (var wrong in new int[][] { [0x158, 16, 0], [0x158, 8, 0], [0x159, 8, 0], [0x15F, 8, 0], [0x12C, 8, 16] })
            Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateInputWrites(JsonSerializer.SerializeToElement(good.Append(wrong)), call, true));
        P28FuelFactorValidator.ValidateInputWrites(JsonSerializer.SerializeToElement(Array.Empty<int[]>()), call, false);
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateInputWrites(JsonSerializer.SerializeToElement(good), call, false));
    }

    [Fact]
    public void EqualFinalFactorCannotHideWrongBranchesFlagsAliasesOrStore()
    {
        var own = P28FuelFactorEvidence.Build(Sources(), 16, 128, 0, 1234, 0x0DC9, 111, 222, 333, 444); var fixture = Fixture(own);
        P28FuelFactorValidator.ValidateFactorStage(fixture.Stage, fixture.Entry, fixture.Exit, own, own.Accesses.ToArray());
        foreach (var (index, field) in new[] { (0, 3), (1, 1), (2, 4), (own.Events.Count - 1, 1) })
        {
            var forged = JsonNode.Parse(fixture.Stage.GetRawText())!; forged["events"]![index]![field] = forged["events"]![index]![field]!.GetValue<int>() ^ 1;
            Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateFactorStage(JsonSerializer.SerializeToElement(forged), fixture.Entry, fixture.Exit, own, own.Accesses.ToArray()));
        }
        foreach (var field in new[] { 1, 2, 4 })
        {
            var forged = own.Accesses.Select(a => a.ToArray()).ToArray(); var index = Array.FindIndex(forged, a => a[0] == 0x7A99 && a[3] == 1); forged[index][field] ^= 1;
            Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateFactorStage(fixture.Stage, fixture.Entry, fixture.Exit, own, forged));
        }
        var bank = JsonNode.Parse(fixture.Exit.GetRawText())!; bank["lrb"] = 0x40;
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateFactorStage(fixture.Stage, fixture.Entry, JsonSerializer.SerializeToElement(bank), own, own.Accesses.ToArray()));
        var contradictory = JsonNode.Parse(fixture.Stage.GetRawText())!; contradictory["result"]!["error"] = "producer failed despite forged successful status";
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateFactorStage(JsonSerializer.SerializeToElement(contradictory), fixture.Entry, fixture.Exit, own, own.Accesses.ToArray()));
    }

    [Fact]
    public void PreciseLowByteStoreFaultRetainsPartialEvidenceWithoutWordGeneration()
    {
        var own = P28FuelFactorEvidence.Build(Sources(), 16, 128, 0, 1234, 0x0DC9, 111, 222, 333, 444);
        var count = own.Events.ToList().FindIndex(e => e[0] == 0x7A99) + 1; var last = count - 1;
        var accesses = own.Accesses.Take(own.AccessEnds[last - 1]).Concat(new[] { new[] { 0x7A99, 0x102, 16, 0, own.Er1 }, new[] { 0x7A99, 0x158, 8, 1, own.Er1 & 255 } }).ToArray();
        var writes = own.Writes.Take(own.WriteEnds[last - 1]).Append(new[] { 0x158, 8, own.Er1 & 255 }).ToArray();
        var fixture = Fixture(own, count, 2, writes);
        var result = P28FuelFactorValidator.ValidateFactorStage(fixture.Stage, fixture.Entry, fixture.Exit, own, accesses); Assert.Equal(2, result.Status);
        Assert.False(P28FuelFactorValidator.FactorHandoffMatches(accesses, own.Er1, false));
        var claimedWord = accesses.Select(a => a.ToArray()).ToArray(); claimedWord[^1] = [0x7A99, 0x158, 16, 1, own.Er1];
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateFactorStage(fixture.Stage, fixture.Entry, fixture.Exit, own, claimedWord));
    }

    [Fact]
    public void CombinedNativeScheduleRejectsForeignPcReorderedBlocksAndUnjournaledByteOverwrite()
    {
        int[] Event(int pc) => [pc, pc + 1, 0, 0, 0, 0, 65536, 65536];
        var prefix = JsonSerializer.SerializeToElement(new
        {
            rpmAxes = (object?)null,
            loadAxis = (object?)null,
            selection = (object?)null,
            lookup = (object?)null,
            consumer = new { events = new[] { Event(0x40) }, writes = new[] { new[] { 0x140, 16, 40 } } }
        });
        var producer = JsonSerializer.SerializeToElement(new { events = new[] { Event(0x50) }, writes = new[] { new[] { 0x158, 16, 12 } } });
        var stages = JsonSerializer.SerializeToElement(new[] { new { events = new[] { Event(0x60), Event(0x61), Event(0x62) }, writes = new[] { new[] { 0x3B4, 16, 480 } } } });
        int[][] accesses = [[0x40, 0x140, 16, 1, 40], [0x50, 0x158, 16, 1, 12], [0x60, 0x140, 16, 0, 40], [0x61, 0x158, 16, 0, 12], [0x62, 0x3B4, 16, 1, 480]];
        P28FuelFactorValidator.ValidateCombinedAccesses(prefix, producer, stages, accesses);
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateCombinedAccesses(prefix, producer, stages, accesses.Append(new[] { 0x4000, 0x12C, 8, 1, 0 }).ToArray()));
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateCombinedAccesses(prefix, producer, stages, [accesses[1], accesses[0], .. accesses.Skip(2)]));
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateCombinedAccesses(prefix, producer, stages, [accesses[0], accesses[1], [0x50, 0x159, 8, 1, 0], .. accesses.Skip(2)]));
        Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateCombinedAccesses(prefix, producer, stages, [accesses[0], .. accesses.Skip(2)]));
    }

    [Fact]
    public void UntouchedPointerEqualityCannotAdmitNonArchitecturalBoundaryValues()
    {
        var own = P28FuelFactorEvidence.Build(Sources(), 16, 128, 0, 1234, 0x0DC9, 111, 222, 333, 444); var fixture = Fixture(own);
        foreach (var key in new[] { "x1", "x2", "dp" }) foreach (var invalid in new[] { -1, 65536 })
            {
                var entry = JsonNode.Parse(fixture.Entry.GetRawText())!; var exit = JsonNode.Parse(fixture.Exit.GetRawText())!; entry[key] = invalid; exit[key] = invalid;
                Assert.Throws<SliceProcessException>(() => P28FuelFactorValidator.ValidateFactorStage(fixture.Stage, JsonSerializer.SerializeToElement(entry), JsonSerializer.SerializeToElement(exit), own, own.Accesses.ToArray()));
            }
    }

    [Fact]
    public void HistoricalAdditiveIdentityAndNewFactorCapabilityHaveDistinctVersionRules()
    {
        var baseFixes = (string[])typeof(SliceRunnerIdentity).GetField("CurrentFixes", BindingFlags.NonPublic | BindingFlags.Static)!.GetValue(null)!;
        var oldFixes = baseFixes.Concat(new[] { "adaptive-exact-word-add-sub-half-carry", "idle-exact-arithmetic-half-carry", "word-rol-accumulator-through-carry-preserves-noncarry-flags", "word-add-accumulator-er0-offpage-half-carry" }).ToArray();
        JsonElement Identity(string version, string operation, string[] fixes) => JsonSerializer.SerializeToElement(new { protocolVersion = 1, operation, runnerVersion = version, upstreamCommit = P28ByteExecutionValidator.UpstreamCommit, localSemanticFixes = fixes });
        SliceRunnerIdentity.Validate(Identity("0.20.0", P28FuelAdditiveValidator.Operation, oldFixes), P28FuelAdditiveValidator.Operation);
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(Identity("0.20.0", P28FuelFactorValidator.Operation, oldFixes), P28FuelFactorValidator.Operation));
        var newFixes = oldFixes.Concat(new[] { "word-rol-er0-through-carry-preserves-noncarry-flags", "word-sll-accumulator-preserves-noncarry-flags" }).ToArray();
        SliceRunnerIdentity.Validate(Identity("0.21.0", P28FuelFactorValidator.Operation, newFixes), P28FuelFactorValidator.Operation);
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(Identity("0.21.0", P28FuelFactorValidator.Operation, oldFixes), P28FuelFactorValidator.Operation));
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(Identity("0.21.0", P28FuelAdditiveValidator.Operation, newFixes), P28FuelFactorValidator.Operation));
    }

    [Fact]
    public async Task InventedNativeFactorRamProductionAndWordConsumptionUseRealRustSubprocess()
    {
        // Independently composed4*3 factor producer, then40*produced factor consumer. No OEM routine bytes.
        var program = new byte[] { 0x67, 3, 0, 0x88, 0x67, 4, 0, 0x90, 0x35, 0xD4, 0x58, 0x67, 40, 0, 0xB4, 0x58, 0x48, 0x90, 0x35, 0x62, 0x60, 3, 0xD2 };
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "synthetic", rom = program.Select(v => (int)v).ToArray() } },
            scratchPatterns = new[] { 170 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new { entryPc = 0, exitPcs = new[] { program.Length }, allowedCodeRanges = new[] { new[] { 0, program.Length } }, psw = 0x0101, lrb = 0x20, usp = 0x280, instructionBudget = 32, dataSeeds = Array.Empty<int[]>(), outputAddresses = new[] { 0x158, 0x159, 0x360, 0x361 } }
        });
        Assert.Equal("0.32.0", response.Response.GetProperty("runnerVersion").GetString()); var result = response.Response.GetProperty("syntheticResult"); Assert.Equal(0, result.GetProperty("status").GetInt32());
        Assert.Equal(new[] { 12, 0, 224, 1 }, result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        var traces = result.GetProperty("trace").EnumerateArray().ToArray(); Assert.Contains(traces, t => t.GetProperty("pc").GetInt32() == 9 && t.GetProperty("accumulator").GetInt32() == 12);
        Assert.Contains(traces, t => t.GetProperty("pc").GetInt32() == 17 && t.GetProperty("accumulator").GetInt32() == 480);
    }

    [Fact]
    public async Task FactorTransportSeparatesAlreadyCancelledTimeoutAndActiveChildCancellation()
    {
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var marker = Path.Combine(Path.GetTempPath(), $"hondaecu-m2m-active-{Guid.NewGuid():N}.pid"); var request = P28FuelFactorValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), Scenario());
        using var active = new CancellationTokenSource(); Process? child = null;
        try
        {
            using (var cancelled = new CancellationTokenSource()) { cancelled.Cancel(); await Assert.ThrowsAnyAsync<OperationCanceledException>(() => SeededSliceProcess.ExchangeAsync("dotnet", request, new SliceProcessOptions { Arguments = [host, "pid-sleep", marker] }, cancelled.Token)); Assert.False(File.Exists(marker)); }
            var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync("dotnet", request, new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) })); Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
            var running = SeededSliceProcess.ExchangeAsync("dotnet", request, new SliceProcessOptions { Arguments = [host, "pid-sleep", marker], Timeout = TimeSpan.FromSeconds(15) }, active.Token);
            int? pid = null; var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(10);
            while (DateTime.UtcNow < deadline) { if (File.Exists(marker)) { try { if (int.TryParse(await File.ReadAllTextAsync(marker), out var value) && value > 0) { pid = value; break; } } catch (IOException) { } } await Task.Delay(20); }
            Assert.True(pid.HasValue, "Active child must publish its PID before cancellation."); child = Process.GetProcessById(pid.Value); Assert.False(child.HasExited); Assert.False(running.IsCompleted); active.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => running); child.Refresh(); Assert.True(child.HasExited);
        }
        finally { active.Cancel(); child?.Dispose(); for (var i = 0; File.Exists(marker) && i < 10; i++) { try { File.Delete(marker); } catch (IOException) when (i < 9) { await Task.Delay(50); } } }
    }

    private static (JsonElement Stage, JsonElement Entry, JsonElement Exit) Fixture(P28FuelFactorOracle own, int? steps = null, int status = 0, int[][]? writes = null)
    {
        var count = steps ?? own.Events.Count; var events = own.Events.Take(count).ToArray(); var regs = count == 0 ? new[] { 111, 222, 333, 444 } : own.RegisterEnds[count - 1];
        JsonElement Boundary(int pc, int a, int psw, int[] words) => JsonSerializer.SerializeToElement(new { pc, accumulator = a, psw, dd = (psw & 0x1000) != 0, lrb = 0x20, x1 = 123, x2 = 234, dp = 345, usp = 0x280, ssp = 0x7FE, registers = words.SelectMany(w => new[] { w & 255, w >> 8 }).ToArray() });
        var entry = Boundary(0x1F43, 1234, 0x0DC9, [111, 222, 333, 444]); var exit = Boundary(events[^1][1], events[^1][3], events[^1][5], regs);
        var stage = JsonSerializer.SerializeToElement(new { result = new { status, usedAssumptions = Array.Empty<string>(), steps = count, stopPc = events[^1][1], outputs = Array.Empty<int>(), programReads = Array.Empty<int>(), trace = events.Select(e => new { pc = e[0], nextPc = e[1], instruction = "invented observation", accumulator = e[3], psw = e[5] }).ToArray(), error = status == 0 ? null : "data write outside modeled memory at 0x0159", executedInstructionBytes = events.SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).Distinct().Order().ToArray() }, writes = writes ?? own.Writes.ToArray(), events, sspAfter = 0x7FE });
        return (stage, entry, exit);
    }
}
