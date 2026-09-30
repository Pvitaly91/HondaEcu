using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28PostStoreTests
{
    internal static P28PostStoreScenario Scenario()
    {
        var old = P28AdaptiveFuelTests.Scenario();
        return P28PostStoreScenario.Create(new(old.InitialState, 321), old.Calls.Select(c => new P28PostStoreCall(c, false, false)).ToArray(),
            "Invented bounded M2p software stimuli; no physical schedule", [0]);
    }
    [Fact]
    public void ClosedSchemaHasOneInitialHistoryAndOnlyTwoNewMaskedSources()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28PostStoreScenario.Parse(s.ToJson()).Digest);
        foreach (var field in new[] { "previous03b4", "current03b4", "postStoreWord0150", "difference", "correction", "pc", "ram", "formula", "request", "factor0158" })
        {
            var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]![field] = 1;
            Assert.ThrowsAny<Exception>(() => P28PostStoreScenario.Parse(n.ToJsonString()));
        }
        foreach (var edit in new Action<JsonNode>[] {
            n => n["formatVersion"] = 2, n => n["purpose"] = "adaptive-limiter-fuel-native-software-test",
            n => n["calls"]![0]!["adaptive"]!["fuel"]!["sources"]!["factor0158"] = 1,
            n => n["calls"]![0]!["adaptive"]!["timerTicks"] = 33,
            n => n["calls"]![1]!["adaptive"]!["fuel"]!["index"] = 0,
            n => n["initialState"]!["output0150"] = 7,
            n => n["traceCallIndexes"] = new JsonArray(0, 0),
            n => n["mutation"] = new JsonObject { ["kind"] = 0, ["mapId"] = null, ["row"] = null, ["column"] = null, ["value"] = 1 }
        }) { var n = JsonNode.Parse(s.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28PostStoreScenario.Parse(n.ToJsonString())); }
        Assert.Throws<InvalidDataException>(() => P28PostStoreScenario.Parse(s.ToJson().Replace("\"disable125\": false", "\"disable125\": false, \"disable125\": true", StringComparison.Ordinal)));
        var request = JsonSerializer.SerializeToElement(P28PostStoreValidator.CreateRequest(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), s), JsonDefaults.Create());
        Assert.Equal("fuelPostStoreChain", request.GetProperty("operation").GetString());
        Assert.False(request.TryGetProperty("adaptiveLimiterFuelGateChain", out _));
    }
    [Theory]
    [InlineData(1000, 1000, 0, "Below250")]
    [InlineData(1000, 1249, 0, "Below250")]
    [InlineData(1000, 1250, 250, "Rise")]
    [InlineData(1000, 2999, 1999, "Rise")]
    [InlineData(1000, 3000, 2000, "Clamp2000")]
    [InlineData(1000, 3001, 2000, "Clamp2000")]
    [InlineData(1000, 999, 0, "UnsignedBorrow")]
    [InlineData(65535, 0, 0, "UnsignedBorrow")]
    public void ExactUnsignedBoundaries(int old, int current, int expected, string reason)
    {
        var p = P28PostStoreModel.Project((ushort)old, (ushort)current, false, false, 107, 0);
        Assert.Equal(expected, p.Result); Assert.Equal(reason, p.Reason);
        var o = Oracle(old, current);
        Assert.Equal(expected, o.Accumulator);
        Assert.DoesNotContain(o.Events, e => e[0] == 0x2236);
    }
    [Fact]
    public void FiniteStorageAuditIsSeparateFromNativeReachability()
    {
        foreach (var old in new ushort[] { 0, 249, 250, 2000, 32768, 65535 })
            for (var current = 0; current <= 65535; current++)
            {
                var p = P28PostStoreModel.Project(old, (ushort)current, false, false, 107, 0);
                var wide = current - old; var expected = wide < 250 ? 0 : Math.Min(wide, 2000);
                Assert.Equal(expected, p.Result);
            }
        for (var rise = 250; rise <= 2000; rise++)
        {
            var own = Oracle(0, rise); Assert.Equal(rise, own.Accumulator);
            Assert.Equal(rise, own.Er0); Assert.DoesNotContain(own.Events, e => e[0] == 0x2236);
        }
    }
    [Fact]
    public void ClosedOneFieldChildrenAreIndependentAndOldWordGuardRemainsClosed()
    {
        var bytes = P28AdaptiveFuelTests.Image(); bytes[0x1966] = 0x62; bytes[0x1969] = 0x67;
        var original = RomImage.FromBytes(bytes); var offset = P28FuelMapContract.CellOffset("map_0", 0, 0);
        var cellValue = (ushort)(original.Span[offset] == 255 ? 254 : original.Span[offset] + 1);
        var cell = P28PostStoreValidator.Mutate(original, new(P28PostStoreMutationKind.FuelCell, "map_0", 0, 0, cellValue));
        var old = P28LimiterInspector.Word(original.Span, 0x649B);
        var word = P28PostStoreValidator.Mutate(original, new(P28PostStoreMutationKind.Bank0Cut, null, null, null, (ushort)(old + 1)));
        Assert.Equal(old, P28LimiterInspector.Word(cell.Span, 0x649B));
        Assert.Equal(original.Span[offset], word.Span[offset]);
        Assert.Throws<SliceProcessException>(() => P28AdaptiveFuelValidator.AdmitMutation(original, cell, new(P28AdaptiveFuelMutationKind.Bank0Cut, (ushort)(old + 1))));
        Assert.Throws<SliceProcessException>(() => P28PostStoreValidator.Mutate(original, new(P28PostStoreMutationKind.FuelCell, "map_0", 0, 0, (ushort)(cellValue + 9))));
        var s = Scenario();
        Assert.Throws<ArgumentException>(() => P28PostStoreScenario.Create(s.InitialState, s.Calls, s.Provenance,
            mutation: new(P28PostStoreMutationKind.Bank0Cut, "map_0", 0, 0, (ushort)(old + 1))));
    }
    [Fact]
    public void NewGatesDoNotInventDependenceOn03A2OrUnusedCarriers()
    {
        var prefix = Prefix(100, 1000);
        var own = P28PostStoreEvidence.Build(prefix, 0, 0, 107, 0);
        var other = P28PostStoreEvidence.Build(prefix with { Er2 = 7, Er3 = 9 }, 0, 0, 107, 0);
        Assert.Equal(own.Accumulator, other.Accumulator);
        Assert.DoesNotContain(own.Accesses, a => a[1] is 0x3A2 or 0x3B4 or 0x104 or 0x106 or 0x8A);
        Assert.Equal("Disabled125", P28PostStoreModel.Project(100, 1000, true, false, 107, 0).Reason);
        Assert.Equal("Disabled12e", P28PostStoreModel.Project(100, 1000, false, true, 107, 0).Reason);
        Assert.Equal("Source0133", P28PostStoreModel.Project(100, 1000, false, false, 160, 0).Reason);
        Assert.Equal("Source014c", P28PostStoreModel.Project(100, 1000, false, false, 107, 1).Reason);
        Assert.Equal(0, P28PostStoreEvidence.Build(prefix, 16, 0, 107, 0).Accumulator);
    }
    [Fact]
    public void ForgedSameFinalNumberOldGenerationResetWidthsFlagsAndClobbersAreRejected()
    {
        var o = Oracle(333, 333); var good = Fixture(o);
        P28PostStoreValidator.ValidateSuffix(good, good.GetProperty("entry"), o);
        foreach (var edit in new Action<JsonNode>[] {
            n => n["entry"]!["registers"]![0] = 0,
            n => n["entry"]!["psw"] = 0x0101,
            n => n["entry"]!["dp"] = 0x150,
            n => n["exit"]!["registers"]![4] = 0,
            n => n["stage"]!["events"]![0]![1] = 0x2239,
            n => n["stage"]!["events"]![0]![5] = 0,
            n => n["accesses"]![4]![2] = 8,
            n => n["accesses"]![4]![4] = 0,
            n => n["stage"]!["writes"] = new JsonArray(),
            n => n["exit"]!["ssp"] = 0x7FC,
            n => n["extraHostWrites"] = new JsonArray()
        })
        {
            var n = JsonNode.Parse(good.GetRawText())!; edit(n);
            Assert.ThrowsAny<Exception>(() => P28PostStoreValidator.ValidateSuffix(JsonSerializer.SerializeToElement(n), good.GetProperty("entry"), o));
        }
        // Different previous values both return zero; a forged substituted previous is still rejected by the read/flags oracle.
        var substituted = Fixture(Oracle(334, 333));
        Assert.Equal(good.GetProperty("exit").GetProperty("accumulator").GetInt32(), substituted.GetProperty("exit").GetProperty("accumulator").GetInt32());
        Assert.ThrowsAny<Exception>(() => P28PostStoreValidator.ValidateSuffix(substituted, good.GetProperty("entry"), o));
        var rise = Oracle(0, 333); Assert.Equal(333, rise.Accumulator); Assert.Equal(333, rise.Er0);
        Assert.NotEqual(0, rise.Er1); // MUL clobber is intentional, not retention.
        var partial = Fixture(rise, rise.Events.Count - 1, 1);
        var result = P28PostStoreValidator.ValidateSuffix(partial, partial.GetProperty("entry"), rise);
        Assert.Equal(1, result.Status); Assert.DoesNotContain(P28FuelAdditiveValidator.Matrix(partial.GetProperty("stage").GetProperty("writes"), 3, 48), w => w[0] == 0x150);
    }
    [Fact]
    public async Task NewOperationRetainsPartialPrefixAndDoesNotRunLaterInputsOrSuffix()
    {
        var s = Scenario(); var image = RomImage.FromBytes(P28AdaptiveFuelTests.Image());
        var r = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28PostStoreValidator.CreateRequest(image, s));
        var reports = P28PostStoreValidator.Analyze(image, s, r.Response, "A");
        foreach (var p in reports)
        {
            Assert.Equal("Unresolved", p.Checkpoints[0].Disposition); Assert.Null(p.Checkpoints[0].Result0150);
            Assert.Equal(88, p.Checkpoints[0].Prefix.RamCutAfter);
            Assert.Equal("NotRun", p.Checkpoints[1].Disposition);
            Assert.Null(p.Checkpoints[1].Actual.GetProperty("suffix").Deserialize<object>());
            Assert.Empty(p.Checkpoints[1].Actual.GetProperty("snapshotWrites").EnumerateArray());
        }
        foreach (var edit in new Action<JsonNode>[] {
            n => n["runnerVersion"] = "0.23.0", n => n["operation"] = "adaptiveLimiterFuelGateChain",
            n => n["entryContracts"]![0]!["stop"] = "BeforeInstruction2204",
            n => n["postStoreSequences"]![0]!["checkpoints"]![1]!["word0150Before"] = 1,
            n => n["postStoreSequences"]![0]!["checkpoints"]![0]!["postStoreWord0150"] = 0,
            n => n["postStoreSequences"]![0]!["checkpoints"]![1]!["snapshotWrites"] = new JsonArray(new JsonArray(0x125, 8, 0))
        }) { var n = JsonNode.Parse(r.Response.GetRawText())!; edit(n); Assert.ThrowsAny<Exception>(() => P28PostStoreValidator.Analyze(image, s, JsonSerializer.SerializeToElement(n), "A")); }
    }
    [Fact]
    public async Task InventedRealSubprocessReadsOldStoresNewAndContinuesNativeCarriers()
    {
        var rom = new byte[0x223B];
        // Invented ADD carrier calculation, not the OEM subtract/gate/clamp sequence.
        new byte[] { 0x62, 0xB4, 3, 0xB2, 0x48, 0x67, 0x4D, 1, 0xD2, 0x08, 0xD4, 0x50, 0xCB, 0x32 }.CopyTo(rom, 0x21FB);
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "synthetic", rom = rom.Select(b => (int)b).ToArray() } },
            scratchPatterns = new[] { 170 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0x21FB,
                exitPcs = new[] { 0x223B },
                allowedCodeRanges = new[] { new[] { 0x21FB, 0x223B } },
                psw = 0x0101,
                lrb = 0x20,
                usp = 0x280,
                instructionBudget = 16,
                dataSeeds = new[] { new[] { 0x3B4, 111 }, new[] { 0x3B5, 0 } },
                outputAddresses = new[] { 0x3B4, 0x3B5, 0x150, 0x151 }
            }
        });
        var result = response.Response.GetProperty("syntheticResult"); Assert.True(result.GetProperty("status").GetInt32() == 0, result.GetRawText());
        Assert.Equal(new[] { 77, 1, 188, 1 }, result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        var trace = result.GetProperty("trace").EnumerateArray().ToArray();
        Assert.Contains(trace, t => t.GetProperty("pc").GetInt32() == 0x2204 && t.GetProperty("accumulator").GetInt32() == 444);
        Assert.Contains(trace, t => t.GetProperty("pc").GetInt32() == 0x2203 && t.GetProperty("nextPc").GetInt32() == 0x2204);
    }
    [Fact]
    public async Task PostStoreTransportSeparatesAlreadyCancelledTimeoutAndActiveChildCancellation()
    {
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var marker = Path.Combine(Path.GetTempPath(), $"hondaecu-m2p-active-{Guid.NewGuid():N}.pid"); var request = P28PostStoreValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), Scenario());
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

    private static P28FuelAdditiveOracle Prefix(int old, int current) => new([], [], [], [], [], [], [], [], current, 0x1DC9, old, 77, 88, current, 0);
    private static P28FuelAdditiveOracle Oracle(int old, int current) => P28PostStoreEvidence.Build(Prefix(old, current), 0, 0, 107, 0);
    private static JsonElement Fixture(P28FuelAdditiveOracle own, int? steps = null, int status = 0)
    {
        var count = steps ?? own.Events.Count; var e = own.Events.Take(count).ToArray(); var regs = own.RegisterEnds[count - 1];
        object Boundary(int pc, int a, int psw, int[] words) => new
        {
            pc,
            accumulator = a,
            psw,
            dd = (psw & 0x1000) != 0,
            lrb = 0x20,
            x1 = 123,
            x2 = 234,
            dp = 0x3B4,
            usp = 0x280,
            ssp = 0x7FE,
            registers = words.SelectMany(w => new[] { w & 255, w >> 8 }).ToArray()
        };
        var old = own.Accesses.FirstOrDefault(a => a[1] == 0x100 && a[3] == 0)?[4] ?? 333;
        var accesses = own.Accesses.Take(own.AccessEnds[count - 1]).ToArray();
        return JsonSerializer.SerializeToElement(new
        {
            entry = Boundary(0x2204, e[0][2], e[0][4], [old, 77, 88, e[0][2]]),
            exit = Boundary(e[^1][1], e[^1][3], e[^1][5], regs),
            accesses,
            stage = new
            {
                result = new
                {
                    status,
                    usedAssumptions = Array.Empty<string>(),
                    steps = count,
                    stopPc = e[^1][1],
                    outputs = Array.Empty<int>(),
                    programReads = Array.Empty<int>(),
                    trace = e.Select(v => new { pc = v[0], nextPc = v[1], instruction = "invented observation", accumulator = v[3], psw = v[5] }).ToArray(),
                    error = status == 0 ? null : "unresolved invented boundary",
                    executedInstructionBytes = e.SelectMany((v, i) => Enumerable.Range(v[0], own.Lengths[i])).Distinct().Order().ToArray()
                },
                writes = accesses.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray(),
                events = e,
                sspAfter = 0x7FE
            }
        });
    }
}
