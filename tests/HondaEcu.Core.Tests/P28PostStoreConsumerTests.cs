using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

[Collection(TimingSensitiveTestCollection.Name)]
public sealed class P28PostStoreConsumerTests
{
    internal static P28PostStoreConsumerScenario Scenario()
    {
        var old = P28PostStoreTests.Scenario();
        return P28PostStoreConsumerScenario.Create(old.InitialState, old.Calls,
            "Invented bounded DATA0150 consumer stimuli; not a physical schedule", [0]);
    }

    [Fact]
    public void ClosedSchemaReusesOneInitialStateAndCannotSetNativeSourcesOrResults()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28PostStoreConsumerScenario.Parse(s.ToJson()).Digest);
        foreach (var field in new[] { "data0150", "word0150", "selected", "selectedScaledWordX1", "helperInput", "helperResult", "branch", "sourceBit5", "data012c", "mode012c", "rom60f8", "pc", "ram", "formula" })
        {
            var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]![field] = 1;
            Assert.ThrowsAny<Exception>(() => P28PostStoreConsumerScenario.Parse(n.ToJsonString()));
        }
        foreach (var edit in new Action<JsonNode>[] {
            n => n["initialState"]!["data0150"] = 7,
            n => n["initialState"]!["mode012c"] = 32,
            n => n["calls"]![0]!["adaptive"]!["fuel"]!["sources"]!["data0150"] = 1,
            n => n["calls"]![0]!["adaptive"]!["fuel"]!["sources"]!["sourceBit5"] = true,
            n => n["calls"]![0]!["adaptive"]!["timerTicks"] = 33,
            n => n["calls"]![1]!["adaptive"]!["fuel"]!["index"] = 0,
            n => n["formatVersion"] = 2,
            n => n["purpose"] = "post-store-fuel-native-software-test",
            n => n["traceCallIndexes"] = new JsonArray(0, 0),
            n => n["mutation"] = new JsonObject { ["kind"] = "rom60f8", ["mapId"] = null, ["row"] = null, ["column"] = null, ["value"] = 1 }
        }) { var n = JsonNode.Parse(s.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28PostStoreConsumerScenario.Parse(n.ToJsonString())); }
        Assert.Throws<InvalidDataException>(() => P28PostStoreConsumerScenario.Parse(s.ToJson().Replace("\"disable125\": false", "\"disable125\": false, \"disable125\": true", StringComparison.Ordinal)));
        var request = JsonSerializer.SerializeToElement(P28PostStoreConsumerValidator.CreateRequest(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), s), JsonDefaults.Create());
        Assert.Equal("fuelPostStoreConsumerChain", request.GetProperty("operation").GetString());
        Assert.False(request.TryGetProperty("fuelPostStoreChain", out _));
    }

    [Theory]
    [InlineData(0, 0, 0, 0, 0, false)]
    [InlineData(250, 0, 0, 312, 0, true)]
    [InlineData(1999, 0, 0, 2498, 0, true)]
    [InlineData(2000, 0, 0, 2500, 0, true)]
    [InlineData(0, 1, 0, 1, 1, false)]
    [InlineData(0, 52428, 0, 65535, 65535, false)]
    [InlineData(0, 52429, 0, 65535, 65535, false)]
    [InlineData(0, 65535, 255, 65535, 65535, false)]
    [InlineData(17, 17, 3, 25, 25, false)]
    public void StorageProjectionHasExactEqualityBorrowTruncationAndSaturation(int word, int operand, int add, int x1, int a, bool borrow)
    {
        var p = P28PostStoreConsumerModel.Project((ushort)word, (ushort)operand, (ushort)add, 0xB5);
        Assert.Equal(x1, p.SelectedScaledWordX1); Assert.Equal(a, p.RetainedOrZeroA);
        Assert.Equal((0xB5 & ~32) | (borrow ? 32 : 0), p.ModeAfter);
        Assert.Equal(0xB5 & ~32, p.ModeAfter & ~32); // shared bit4 and all neighbors retained.
        var own = Oracle(word, operand, add, 0xB5);
        Assert.Equal(x1, own.X1); Assert.Equal(a, own.Machine.Accumulator);
        Assert.Equal(p.ModeAfter, own.Mode);
        var compare = Assert.Single(own.Machine.Events.Where(e => e[0] == 0x223D));
        Assert.Equal(operand, compare[6]); Assert.Equal(word, compare[7]);
        Assert.Equal(borrow, (compare[5] & 0x8000) != 0); Assert.Equal(word == operand, (compare[5] & 0x4000) != 0);
        Assert.Equal(compare[4] & 0x2000, compare[5] & 0x2000);
        Assert.Contains(own.Machine.Accesses, r => r[0] == 0x223D && r[1] == 0x150 && r[2] == 16 && r[3] == 0 && r[4] == word);
        Assert.Equal(word == operand ? 0x2246 : borrow ? 0x2244 : 0x2246, own.Machine.Events.Single(e => e[0] == 0x2242)[1]);
    }

    [Fact]
    public void FiniteStorageAuditIsIndependentAndNativeReachabilityIsNarrower()
    {
        foreach (var word in new ushort[] { 0, 249, 250, 1999, 2000, 65535 })
            for (var operand = 0; operand <= 65535; operand++)
            {
                var p = P28PostStoreConsumerModel.Project(word, (ushort)operand, 17, 0xB5);
                var selected = Math.Max(word, operand);
                var helperInput = Math.Min(selected + 17L, 65535);
                var expected = selected == 0 ? 0 : (int)Math.Min(helperInput * 5 / 4, 65535);
                Assert.Equal(expected, p.SelectedScaledWordX1);
                Assert.Equal(word > operand ? 0 : expected, p.RetainedOrZeroA);
            }
        for (var input = 0; input <= 65535; input++)
        {
            var p = P28PostStoreConsumerModel.Project(0, (ushort)input, 0, 0);
            Assert.Equal((int)Math.Min(input * 5L / 4, 65535), p.SelectedScaledWordX1);
        }
        // Actual prefix makes nonzero equality impossible: nonzero014C always gates0150 tozero.
        foreach (var operand in new ushort[] { 1, 250, 2000, 65535 })
            Assert.Equal(0, P28PostStoreModel.Project(0, 2000, false, false, 107, operand).Result);
        foreach (var word in new ushort[] { 250, 251, 1999, 2000 })
        {
            var native = P28PostStoreModel.Project(0, word, false, false, 107, 0);
            Assert.Equal(word, native.Result);
            var p = P28PostStoreConsumerModel.Project((ushort)native.Result, 0, 0, 0);
            Assert.Equal(0, p.RetainedOrZeroA); Assert.NotEqual(0, p.SelectedScaledWordX1);
        }
    }

    [Fact]
    public void NativeBit5MasksNeighborsZeroSkipsHelperAndHelperUsesNativeCallReturn()
    {
        foreach (var mode in new byte[] { 0, 16, 32, 0x55, 0xAA, 0xFF })
            foreach (var pair in new[] { (Word: 0, Operand: 0), (Word: 250, Operand: 0), (Word: 0, Operand: 250) })
            {
                var own = Oracle(pair.Word, pair.Operand, 17, mode);
                Assert.Equal(mode & ~32, own.Mode & ~32);
                Assert.Equal(pair.Word > pair.Operand, (own.Mode & 32) != 0);
                Assert.Single(own.Machine.Accesses.Where(r => r[0] == 0x223F && r[1] == 0x12C && r[2] == 8 && r[3] == 1));
                Assert.DoesNotContain(own.Machine.Writes, r => r[0] == 0x150);
                Assert.Contains(own.Machine.Accesses, r => r[0] == 0x2255 && r[1] == 0x12C && r[2] == 8 && r[3] == 0 && r[4] == own.Mode);
                if (pair.Word == 0 && pair.Operand == 0)
                {
                    Assert.DoesNotContain(own.Machine.Events, e => e[0] is 0x224A or 0x2251 or 0x5991);
                    Assert.Equal(0, own.X1);
                }
                else
                {
                    Assert.Contains(own.Machine.Events, e => e[0] == 0x2251 && e[1] == 0x5991);
                    Assert.Contains(own.Machine.Accesses, r => r[0] == 0x2251 && r[1] == 0x7FE && r[2] == 16 && r[3] == 1 && r[4] == 0x2254);
                    Assert.Contains(own.Machine.Events, e => e[0] == 0x59A5 && e[1] == 0x2254);
                    Assert.Equal(0x7FE, own.Machine.StackEnds[^1]);
                }
                Assert.DoesNotContain(own.Machine.Events, e => e[0] is 0x2259 or 0x226F or 0x2273 or 0x227A or 0x229F);
                Assert.DoesNotContain(own.Machine.Accesses, r => r[1] is 0x3A2 or 0x3B4 or 0x60F8);
            }
    }

    [Fact]
    public void IndependentModeHistoryIsNativeOwnedAcrossEventsAndDoesNotResetNeighbors()
    {
        var s = Scenario(); var mode = s.InitialState.Adaptive.Joint.ProducerMode012c;
        var history = new P28PostStoreConsumerHistory(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), s);
        var first = history.Step(s.Calls[0]); var second = history.Step(s.Calls[1]);
        Assert.Equal(mode, first.Consumer.ModeBefore); Assert.Equal(first.Consumer.ModeAfter, second.Consumer.ModeBefore);
        Assert.Equal(mode & ~32, first.Consumer.ModeAfter & ~32); Assert.Equal(mode & ~32, second.Consumer.ModeAfter & ~32);
        Assert.Equal(first.PostStore.Current, second.PostStore.Previous);
        Assert.Equal(P28PostStoreConsumerModel.Project((ushort)second.PostStore.Result, s.Calls[1].Adaptive.Fuel.Sources.Source014c,
            s.Calls[1].Adaptive.Fuel.Sources.Source0144, (byte)first.Consumer.ModeAfter), second.Consumer);
    }

    [Fact]
    public void NextEventMustObservePriorNativeExitBeforeItsScriptedEntry()
    {
        var prior = Fixture(Oracle(250, 0, 17, 0xB5), 250).GetProperty("exit");
        P28PostStoreConsumerValidator.RequireEventContinuation(prior, prior);
        foreach (var edit in new Action<JsonNode>[] {
            n => n["pc"] = 0x223B,
            n => n["accumulator"] = 321,
            n => n["psw"] = 0x0101,
            n => n["lrb"] = 0x40,
            n => n["x1"] = 123,
            n => n["x2"] = 0,
            n => n["dp"] = 0,
            n => n["usp"] = 0x180,
            n => n["ssp"] = 0x7FC,
            n => n["registers"]![0] = 99
        })
        {
            var n = JsonNode.Parse(prior.GetRawText())!; edit(n);
            Assert.ThrowsAny<Exception>(() => P28PostStoreConsumerValidator.RequireEventContinuation(prior, JsonSerializer.SerializeToElement(n)));
        }
    }

    [Fact]
    public async Task NewOperationKeepsPartialPrefixAndRefusesOldTaskVersionOrInventedTerminalState()
    {
        var s = Scenario(); var image = RomImage.FromBytes(P28AdaptiveFuelTests.Image());
        var r = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28PostStoreConsumerValidator.CreateRequest(image, s));
        var reports = P28PostStoreConsumerValidator.Analyze(image, s, r.Response, "A");
        foreach (var sequence in reports)
        {
            var first = sequence.Checkpoints[0]; var terminal = sequence.Checkpoints[1];
            Assert.Equal("Unresolved", first.Disposition); Assert.Equal("Unresolved", first.PrefixDisposition);
            Assert.Null(first.SelectedScaledWordX1); Assert.Null(first.RetainedOrZeroA); Assert.Null(first.Expected);
            Assert.Equal(88, first.Prefix.Prefix.RamCutAfter); Assert.Equal("NotRun", terminal.Disposition);
            Assert.Equal(JsonValueKind.Null, terminal.Actual.GetProperty("consumer").ValueKind);
            Assert.Empty(terminal.Actual.GetProperty("prefix").GetProperty("snapshotWrites").EnumerateArray());
        }
        foreach (var edit in new Action<JsonNode>[] {
            n => n["runnerVersion"] = "0.24.0",
            n => n["operation"] = "fuelPostStoreChain",
            n => n["entryContracts"]![0]!["stop"] = "BeforeInstruction223B",
            n => n["consumerSequences"]![0]!["checkpoints"]![1]!["word0150Before"] = 250,
            n => n["consumerSequences"]![0]!["checkpoints"]![1]!["mode012cBefore"] = 0,
            n => n["consumerSequences"]![0]!["checkpoints"]![0]!["selectedScaledWordX1"] = 0,
            n => n["consumerSequences"]![0]!["checkpoints"]![1]!["prefix"]!["snapshotWrites"] = new JsonArray(new JsonArray(0x150, 16, 250)),
            n => n["consumerSequences"]![0]!["checkpoints"]![0]!["extraHostWrites"] = new JsonArray()
        })
        {
            var n = JsonNode.Parse(r.Response.GetRawText())!; edit(n);
            Assert.ThrowsAny<Exception>(() => P28PostStoreConsumerValidator.Analyze(image, s, JsonSerializer.SerializeToElement(n), "A"));
        }
        var wrongTask = JsonNode.Parse(JsonSerializer.Serialize(P28PostStoreConsumerValidator.CreateRequest(image, s), JsonDefaults.Create()))!;
        wrongTask["operation"] = "fuelPostStoreChain";
        await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, wrongTask));
    }

    [Fact]
    public void ForgedSameResultCannotHideWrongGenerationWidthBranchResetBankOrReturn()
    {
        var own = Oracle(250, 0, 17, 0xB5); var good = Fixture(own, 250);
        P28PostStoreConsumerValidator.ValidateConsumer(good, good.GetProperty("entry"), own);
        var compare = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x223D);
        var branch = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x2242);
        var ret = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x59A5);
        var read = own.Machine.Accesses.ToList().FindIndex(r => r[0] == 0x223D && r[1] == 0x150);
        foreach (var edit in new Action<JsonNode>[] {
            n => n["entry"]!["accumulator"] = 0,
            n => n["entry"]!["psw"] = 0x0101,
            n => n["entry"]!["lrb"] = 0x40,
            n => n["entry"]!["x1"] = 0,
            n => n["accesses"]![read]![2] = 8,
            n => n["accesses"]![read]![4] = 249,
            n => n["stage"]!["events"]![compare]![6] = 250,
            n => n["stage"]!["events"]![compare]![7] = 0,
            n => n["stage"]!["events"]![branch]![1] = 0x2246,
            n => n["stage"]!["events"]![ret]![1] = 0x2255,
            n => n["exit"]!["ssp"] = 0x7FC,
            n => n["exit"]!["registers"]![4] = 0,
            n => n["extraHostWrites"] = new JsonArray(new JsonArray(0x150, 16, 250))
        })
        {
            var n = JsonNode.Parse(good.GetRawText())!; edit(n);
            Assert.ThrowsAny<Exception>(() => P28PostStoreConsumerValidator.ValidateConsumer(JsonSerializer.SerializeToElement(n), good.GetProperty("entry"), own));
        }
        var equality = Oracle(0, 0, 17, 0xB5); var equalFixture = Fixture(equality, 0);
        P28PostStoreConsumerValidator.ValidateConsumer(equalFixture, equalFixture.GetProperty("entry"), equality);
        var zeroBranch = equality.Machine.Events.ToList().FindIndex(e => e[0] == 0x2242);
        var forged = JsonNode.Parse(equalFixture.GetRawText())!; forged["stage"]!["events"]![zeroBranch]![1] = 0x2244;
        Assert.ThrowsAny<Exception>(() => P28PostStoreConsumerValidator.ValidateConsumer(JsonSerializer.SerializeToElement(forged), equalFixture.GetProperty("entry"), equality));
        // Different stale storage values both yield final A0, but the reader must match the current generation.
        var stale = Fixture(Oracle(249, 0, 17, 0xB5), 250);
        Assert.Equal(good.GetProperty("exit").GetProperty("accumulator").GetInt32(), stale.GetProperty("exit").GetProperty("accumulator").GetInt32());
        Assert.ThrowsAny<Exception>(() => P28PostStoreConsumerValidator.ValidateConsumer(stale, good.GetProperty("entry"), own));
        var partial = Fixture(own, 250, ret, 1);
        Assert.Equal(1, P28PostStoreConsumerValidator.ValidateConsumer(partial, partial.GetProperty("entry"), own).Status);
        Assert.Equal(0x7FC, partial.GetProperty("exit").GetProperty("ssp").GetInt32());
    }

    [Theory]
    [InlineData(100, 960)]
    [InlineData(320, 960)]
    [InlineData(321, 963)]
    public async Task InventedRealProcessProducesFreshWordThenSelectsCallsReturnsAndStores(int other, int expected)
    {
        var rom = new byte[0x48];
        // Newly composed low-address program: repeated same-value native store, word comparison,
        // multiplication by three in an invented helper. This is not the OEM routine or its bytes.
        new byte[] { 0x67, 0x40, 1, 0xD4, 0x50, 0xD4, 0x50, 0xE4, 0x4C, 0xC7, 0x50, 0xCD, 2, 0xE4, 0x50, 0x32, 0x40, 0, 0xD4, 0x60 }.CopyTo(rom, 0);
        new byte[] { 0x44, 0x98, 3, 0, 0x90, 0x35, 0x01 }.CopyTo(rom, 0x40);
        var response = await Synthetic(rom, 20, [[0x14C, other & 255], [0x14D, other >> 8]], [0x150, 0x151, 0x160, 0x161]);
        var result = response.Response.GetProperty("syntheticResult"); Assert.True(result.GetProperty("status").GetInt32() == 0, result.GetRawText());
        Assert.Equal(new[] { 64, 1, expected & 255, expected >> 8 }, result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        var trace = result.GetProperty("trace").EnumerateArray().ToArray();
        Assert.Contains(trace, t => t.GetProperty("pc").GetInt32() == 3 && t.GetProperty("nextPc").GetInt32() == 5);
        Assert.Contains(trace, t => t.GetProperty("pc").GetInt32() == 5 && t.GetProperty("nextPc").GetInt32() == 7);
        Assert.Contains(trace, t => t.GetProperty("pc").GetInt32() == 9 && t.GetProperty("accumulator").GetInt32() == other);
        Assert.Contains(trace, t => t.GetProperty("pc").GetInt32() == 15 && t.GetProperty("nextPc").GetInt32() == 0x40);
        Assert.Contains(trace, t => t.GetProperty("pc").GetInt32() == 0x46 && t.GetProperty("nextPc").GetInt32() == 18);
    }

    [Fact]
    public async Task InventedZeroConfigurationBranchBypassesOptionalStoreWithoutActualRomClaim()
    {
        var rom = new byte[0x41];
        // Invented zero-config program with different addresses: a native ROM-byte test skips an optional store.
        new byte[] { 0x62, 0x40, 0, 0x92, 0xAA, 0xC6, 0, 0xC9, 4, 0x77, 99, 0xD5, 0xC4, 0x77, 7, 0xD5, 0xC5 }.CopyTo(rom, 0);
        var response = await Synthetic(rom, 17, [[0xC4, 44]], [0xC4, 0xC5]);
        var result = response.Response.GetProperty("syntheticResult"); Assert.True(result.GetProperty("status").GetInt32() == 0, result.GetRawText());
        Assert.Equal(new[] { 44, 7 }, result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        Assert.DoesNotContain(result.GetProperty("trace").EnumerateArray(), t => t.GetProperty("pc").GetInt32() is 9 or 11);
    }

    [Fact]
    public async Task ConsumerTransportSeparatesAlreadyCancelledTimeoutAndObservedActiveChildCancellation()
    {
        var host = ProcessHandshake.HostPath;
        var request = P28PostStoreConsumerValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), Scenario());
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

    private static Task<SliceProcessResponse> Synthetic(byte[] rom, int exit, int[][] seeds, int[] outputs) => SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
    {
        protocolVersion = 1,
        operation = "synthetic",
        images = new[] { new { id = "synthetic", rom = rom.Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 170 },
        allowAssumptions = Array.Empty<string>(),
        synthetic = new { entryPc = 0, exitPcs = new[] { exit }, allowedCodeRanges = new[] { new[] { 0, rom.Length } }, psw = 0x0101, lrb = 0x20, usp = 0x280, instructionBudget = 32, dataSeeds = seeds, outputAddresses = outputs }
    });

    private static P28PostStoreConsumerOracle Oracle(int word, int operand, int add, byte mode) => P28PostStoreConsumerEvidence.Build(
        new([], [], [], [], [], [], [], [], word, 0x1DC9, 1000, 77, 88, 99, mode), (ushort)word, (ushort)operand, (ushort)add, mode, 123);

    private static JsonElement Fixture(P28PostStoreConsumerOracle own, int entryWord, int? steps = null, int status = 0)
    {
        var o = own.Machine; var count = steps ?? o.Events.Count; var e = o.Events.Take(count).ToArray(); var regs = o.RegisterEnds[count - 1];
        object Boundary(int pc, int a, int psw, int[] words, int x1, int ssp) => new
        {
            pc,
            accumulator = a,
            psw,
            dd = (psw & 0x1000) != 0,
            lrb = 0x20,
            x1,
            x2 = 234,
            dp = 0x3B4,
            usp = 0x280,
            ssp,
            registers = words.SelectMany(w => new[] { w & 255, w >> 8 }).ToArray()
        };
        var accesses = o.Accesses.Take(o.AccessEnds[count - 1]).ToArray();
        return JsonSerializer.SerializeToElement(new
        {
            entry = Boundary(0x223B, entryWord, 0x1DC9, [1000, 77, 88, 99], 123, 0x7FE),
            exit = Boundary(e[^1][1], e[^1][3], e[^1][5], regs, own.X1Ends[count - 1], o.StackEnds[count - 1]),
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
                    executedInstructionBytes = e.SelectMany((v, i) => Enumerable.Range(v[0], o.Lengths[i])).Distinct().Order().ToArray()
                },
                writes = accesses.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray(),
                events = e,
                sspAfter = o.StackEnds[count - 1]
            }
        });
    }
}
