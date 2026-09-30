using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28PostSelectionCriticalTests
{
    internal static P28PostSelectionCriticalScenario Scenario()
    {
        var old = P28PostStoreConsumerTests.Scenario();
        return P28PostSelectionCriticalScenario.Create(old.InitialState, old.Calls,
            "Invented bounded M2r synchronous software stimuli; not a physical schedule", [0]);
    }

    [Fact]
    public void ClosedSchemaReusesOnlyExistingSourcesAndCannotSetProducedOrInterruptOutcomes()
    {
        var scenario = Scenario(); Assert.Equal(scenario.Digest, P28PostSelectionCriticalScenario.Parse(scenario.ToJson()).Digest);
        foreach (var field in new[] { "ie", "mie", "pswh", "interrupt", "word0190", "word0192", "word0194", "words019x", "commonWords03b6",
            "x1", "accumulator", "data0150", "sourceBit5", "rom60f8", "branch", "pc", "ram", "formula" })
        {
            var n = JsonNode.Parse(scenario.ToJson())!; n["calls"]![0]![field] = 1;
            Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalScenario.Parse(n.ToJsonString()));
        }
        foreach (var edit in new Action<JsonNode>[] {
            n => n["initialState"]!["word0190"] = 7,
            n => n["initialState"]!["x1"] = 321,
            n => n["calls"]![0]!["adaptive"]!["fuel"]!["sources"]!["ie"] = 0,
            n => n["calls"]![0]!["adaptive"]!["timerTicks"] = 33,
            n => n["calls"]![1]!["adaptive"]!["fuel"]!["index"] = 0,
            n => n["formatVersion"] = 2,
            n => n["purpose"] = "post-store-consumer-native-software-test",
            n => n["traceCallIndexes"] = new JsonArray(0, 0),
            n => n["mutation"] = new JsonObject { ["kind"] = "rom60f8", ["mapId"] = null, ["row"] = null, ["column"] = null, ["value"] = 1 }
        }) { var n = JsonNode.Parse(scenario.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalScenario.Parse(n.ToJsonString())); }
        Assert.Throws<InvalidDataException>(() => P28PostSelectionCriticalScenario.Parse(scenario.ToJson().Replace("\"disable125\": false", "\"disable125\": false, \"disable125\": true", StringComparison.Ordinal)));
        var request = JsonSerializer.SerializeToElement(P28PostSelectionCriticalValidator.CreateRequest(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), scenario), JsonDefaults.Create());
        Assert.Equal("fuelPostSelectionCriticalChain", request.GetProperty("operation").GetString());
        Assert.False(request.TryGetProperty("fuelPostStoreConsumerChain", out _));
        Assert.False(request.TryGetProperty("synthetic", out _));
    }

    [Fact]
    public void ScenarioKeepsDenseCallCombinedTickAndSelectedTraceBounds()
    {
        var scenario = Scenario();
        Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalScenario.Create(scenario.InitialState, [], "Empty calls are invalid"));
        var calls = Enumerable.Range(0, 65).Select(i => scenario.Calls[0] with
        {
            Adaptive = scenario.Calls[0].Adaptive with { Fuel = scenario.Calls[0].Adaptive.Fuel with { Index = i } }
        }).ToArray();
        Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalScenario.Create(scenario.InitialState, calls, "Too many calls"));
        Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalScenario.Create(scenario.InitialState, calls.Take(9).ToArray(), "Too many traces", Enumerable.Range(0, 9).ToArray()));
        var n = JsonNode.Parse(scenario.ToJson())!; n["calls"]![0]!["adaptive"]!["timerTicks"] = 17; n["calls"]![0]!["adaptive"]!["counterTicks"] = 16;
        Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalScenario.Parse(n.ToJsonString()));
    }

    [Theory]
    [InlineData(0, 0, 0, 0)]
    [InlineData(312, 0, 250, 312)]
    [InlineData(320, 320, 3, 3)]
    [InlineData(65535, 65535, 52428, 65535)]
    [InlineData(65535, 0, 52429, 65535)]
    [InlineData(7, 5, 65535, 65535)]
    public void StorageProjectionSeparatesM2qTransfersFromCurrent03b4CommonResult(int x1, int a, int current, int common)
    {
        var projection = P28PostSelectionCriticalModel.Project((ushort)x1, (ushort)a, (ushort)current, 0xBA98, 0x5AA5);
        Assert.Equal(x1, projection.Word0194); Assert.Equal(a, projection.Word0190); Assert.Equal(a, projection.Word0192);
        Assert.Equal(common, projection.CommonPathWord); Assert.Equal(0xBA98, projection.IeBefore);
        Assert.Equal(0x0280, projection.IeMasked); Assert.Equal(0x5AA5, projection.IeAfter);
        var oracle = Oracle(x1, a, current);
        Assert.Equal(new[] { a, a, x1, common, common, common, common }, oracle.WordEnds[^1]);
        Assert.Equal(0, oracle.X1Ends[^1]); Assert.Equal(common, oracle.Machine.Accumulator);
        Assert.Equal(0x5AA5, oracle.IeEnds[^1]);
        Assert.DoesNotContain(oracle.Machine.Accesses, r => r[1] is 0x3A2 or 0x14C or 0x150 or 0x12C);
    }

    [Fact]
    public void ModelOnlyFiniteCurrentWordAuditDoesNotInventM2qInfluenceAfterClobber()
    {
        for (var current = 0; current <= 65535; current++)
        {
            var a = P28PostSelectionCriticalModel.Project(321, 0, (ushort)current, 65535, 0x5AA5);
            var b = P28PostSelectionCriticalModel.Project(654, 654, (ushort)current, 65535, 0x5AA5);
            Assert.Equal((int)Math.Min(current * 5L / 4, 65535), a.CommonPathWord);
            Assert.Equal(a.CommonPathWord, b.CommonPathWord);
            Assert.NotEqual(a.Word0194, b.Word0194); Assert.NotEqual(a.Word0190, b.Word0190);
        }
    }

    [Fact]
    public void IndependentHistoryRetainsNativeIeAndWordsAndRejectsAlternateOwnRomConfiguration()
    {
        var scenario = Scenario(); var bytes = P28AdaptiveFuelTests.Image(); var model = new P28PostSelectionCriticalHistory(RomImage.FromBytes(bytes), scenario, 85);
        var first = model.Step(scenario.Calls[0]); var second = model.Step(scenario.Calls[1]);
        Assert.Equal(scenario.InitialState.Adaptive.Ie, first.Before.Ie);
        Assert.Equal(new[] { 0x5555, 0x5555, 0x5555 }, first.Before.Words019x);
        Assert.Equal(first.After.Ie, second.Before.Ie); Assert.Equal(first.After.RestoreIe, second.Before.RestoreIe);
        Assert.Equal(first.After.Words019x, second.Before.Words019x); Assert.Equal(first.After.CommonWords03b6, second.Before.CommonWords03b6);
        Assert.Equal(first.After.Word03b4, second.Before.Word03b4); Assert.Equal(first.After.Mode012c, second.Before.Mode012c);
        Assert.Equal(first.After.Word0150, second.Before.Word0150);
        bytes[0x60F8] = 1;
        Assert.Throws<InvalidDataException>(() => new P28PostSelectionCriticalHistory(RomImage.FromBytes(bytes), scenario, 85));
    }

    [Fact]
    public void ModelOnlyTimerHoldKeepsInitialIeThenRetainsActualNewSuffixRestoreAcrossEvents()
    {
        var source = Scenario(); var initial = source.InitialState with { Adaptive = source.InitialState.Adaptive with { Timer = 1 } };
        var calls = source.Calls.Select(c => c with { Adaptive = c.Adaptive with { Reset217 = false, Reset214 = false, TimerTicks = 0, CounterTicks = 0 } }).ToArray();
        var scenario = P28PostSelectionCriticalScenario.Create(initial, calls, "Model-only IE ownership through two timer holds");
        Assert.NotEqual(initial.Adaptive.Ie, initial.Adaptive.RestoreIe);
        var model = new P28PostSelectionCriticalHistory(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), scenario, 0);
        var first = model.Step(calls[0]); var second = model.Step(calls[1]);
        Assert.Equal(initial.Adaptive.Ie, first.Entry.Ie); Assert.Equal(initial.Adaptive.RestoreIe, first.After.Ie);
        Assert.Equal(first.After.Ie, second.Before.Ie); Assert.Equal(initial.Adaptive.RestoreIe, second.Entry.Ie);
        Assert.Equal(first.After.Words019x, second.Before.Words019x);
    }

    [Fact]
    public void NextEventRequiresCompletePriorBoundaryBeforeItsScriptedEntry()
    {
        var prior = Fixture(Oracle()).GetProperty("exit");
        P28PostSelectionCriticalValidator.RequireEventContinuation(prior, prior);
        foreach (var edit in new Action<JsonNode>[] {
            n => n["pc"] = 0x2259, n => n["accumulator"] = 321, n => n["psw"] = 0x0101,
            n => n["lrb"] = 0x40, n => n["x1"] = 123, n => n["x2"] = 0, n => n["dp"] = 0,
            n => n["usp"] = 0x180, n => n["ssp"] = 0x7FC, n => n["registers"]![0] = 99
        })
        {
            var n = JsonNode.Parse(prior.GetRawText())!; edit(n);
            Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalValidator.RequireEventContinuation(prior, JsonSerializer.SerializeToElement(n)));
        }
    }

    [Fact]
    public void SynchronousMaskBitEditsNativeRestoreAndSameValueStoresHaveExactOrderedProof()
    {
        foreach (var initialIe in new[] { 0, 0xA55A, 0xBA98, 65535 })
            foreach (var restore in new[] { 0, 0x5AA5, 65535 })
            {
                var own = Oracle(321, 0, 700, initialIe, restore, 0xBDF9, [0, 0, 321, 875, 875, 875, 875]);
                var events = own.Machine.Events;
                var mask = events.Single(e => e[0] == 0x2259);
                Assert.Equal(initialIe & 0x02A0, own.IeEnds[0]); Assert.Equal(mask[4] & ~0x4000, mask[5] & ~0x4000);
                Assert.Equal((initialIe & 0x02A0) == 0, (mask[5] & 0x4000) != 0);
                var clear = events.Single(e => e[0] == 0x225E); var set = events.Single(e => e[0] == 0x2268);
                Assert.Equal(clear[4] & ~0x0100, clear[5]); Assert.Equal(set[4] | 0x0100, set[5]);
                Assert.Contains(own.Machine.Accesses, r => r.SequenceEqual(new[] { 0x2259, 0x1A, 16, 0, initialIe }));
                Assert.Contains(own.Machine.Accesses, r => r.SequenceEqual(new[] { 0x2259, 0x1A, 16, 1, initialIe & 0x02A0 }));
                Assert.Contains(own.Machine.Accesses, r => r.SequenceEqual(new[] { 0x226B, 0xF8, 16, 0, restore }));
                Assert.Contains(own.Machine.Accesses, r => r.SequenceEqual(new[] { 0x226D, 0x1A, 16, 1, restore }));
                Assert.Equal(new[] { 0x194, 0x190, 0x192 }, own.Machine.Accesses.Where(r => r[3] == 1 && r[1] is >= 0x190 and <= 0x194).Select(r => r[1]));
                Assert.Equal(new[] { 0x3B6, 0x3B8, 0x3BA, 0x3BC }, own.Machine.Accesses.Where(r => r[3] == 1 && r[1] is >= 0x3B6 and <= 0x3BC).Select(r => r[1]));
                Assert.DoesNotContain(own.Machine.Accesses, r => r[3] == 0 && r[1] is >= 0x190 and <= 0x194);
                Assert.Equal(restore, own.IeEnds[^1]); // Not a host restore to initialIe.
                var good = Fixture(own, 321, 0, 0xBDF9); P28PostSelectionCriticalValidator.ValidateSuffix(good, good.GetProperty("entry"), own);
            }
    }

    [Fact]
    public void NativeConfigProofRequiresCorrectAddressValueZeroBranchAndExcludedInstructionExtent()
    {
        var own = Oracle(321, 0, 700); var good = Fixture(own);
        P28PostSelectionCriticalValidator.ValidateSuffix(good, good.GetProperty("entry"), own);
        Assert.Equal(new[] { 0x60F8 }, own.ProgramReads);
        var load = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x226F);
        var branch = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x2273);
        Assert.Equal(0x229F, own.Machine.Events[branch][1]); Assert.True((own.Machine.Events[load][5] & 0x4000) != 0);
        Assert.DoesNotContain(own.Machine.Events, e => e[0] is >= 0x2275 and < 0x229F);
        Assert.Equal(own.Machine.Events[load][2] & 0xFF00, own.Machine.Events[load][3] & 0xFF00);
        foreach (var edit in new Action<JsonNode>[] {
            n => n["stage"]!["result"]!["programReads"] = new JsonArray(),
            n => n["stage"]!["result"]!["programReads"]![0] = 0x60F9,
            n => n["stage"]!["events"]![load]![3] = own.Machine.Events[load][3] | 1,
            n => n["stage"]!["events"]![load]![5] = own.Machine.Events[load][5] & ~0x4000,
            n => n["stage"]!["events"]![branch]![1] = 0x2275,
            n => n["stage"]!["result"]!["executedInstructionBytes"]!.AsArray().Add(0x227A),
            n => n["stage"]!["events"]![branch]![0] = 0x227A
        }) Reject(edit, good, own);
    }

    [Fact]
    public void CorrectFinalNumbersCannotHideResetWrongIeWidthWrongPswBitMissingRestoreOrTransfer()
    {
        var own = Oracle(321, 0, 700); var good = Fixture(own);
        var maskRead = own.Machine.Accesses.ToList().FindIndex(r => r[0] == 0x2259 && r[3] == 0);
        var restoreStore = own.Machine.Accesses.ToList().FindIndex(r => r[0] == 0x226D && r[3] == 1);
        var wordStore = own.Machine.Accesses.ToList().FindIndex(r => r[0] == 0x2261 && r[3] == 1);
        var pswh = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x225E);
        var restore = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x226D);
        foreach (var edit in new Action<JsonNode>[] {
            n => n["entry"]!["pc"] = 0x223B,
            n => n["entry"]!["x1"] = 0,
            n => n["entry"]!["accumulator"] = 123,
            n => n["entry"]!["psw"] = 0x0101,
            n => n["entry"]!["lrb"] = 0x40,
            n => n["accesses"]![maskRead]![2] = 8,
            n => n["accesses"]![maskRead]![4] = 0,
            n => n["stage"]!["events"]![pswh]![5] = own.Machine.Events[pswh][5] ^ 0x0200,
            n => n["accesses"]![restoreStore]![4] = 0xBA98,
            n => n["stage"]!["events"]!.AsArray().RemoveAt(restore),
            n => n["accesses"]![wordStore]![4] = 320,
            n => n["exit"]!["x1"] = 321,
            n => n["exit"]!["ssp"] = 0x7FC,
            n => n["extraHostWrites"] = new JsonArray(new JsonArray(0x1A, 16, 0x5AA5))
        }) Reject(edit, good, own);
    }

    [Fact]
    public void PartialSuffixKeepsEarlierNativeWriteWithoutInventingLaterStoresOrReturn()
    {
        var own = Oracle(321, 17, 700, 0xBA98, 0x5AA5, 0x9DC9, [55, 66, 77, 88, 99, 111, 222]);
        var count = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x2264) + 1;
        var partial = Fixture(own, 321, 17, steps: count, status: 1);
        Assert.Equal(1, P28PostSelectionCriticalValidator.ValidateSuffix(partial, partial.GetProperty("entry"), own).Status);
        Assert.Equal(new[] { 17, 66, 321, 88, 99, 111, 222 }, own.WordEnds[count - 1]);
        Assert.Equal(0x0280, own.IeEnds[count - 1]);
        Assert.DoesNotContain(partial.GetProperty("accesses").EnumerateArray(), r => r[0].GetInt32() is 0x2266 or 0x226D or 0x22A5);
        Assert.Empty(partial.GetProperty("stage").GetProperty("result").GetProperty("programReads").EnumerateArray());
        var claimed = JsonNode.Parse(partial.GetRawText())!; claimed["stage"]!["result"]!["status"] = 0;
        Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalValidator.ValidateSuffix(JsonSerializer.SerializeToElement(claimed), partial.GetProperty("entry"), own));
    }

    [Fact]
    public async Task NewOperationRealPartialPrefixIsTerminalAndRefusesHistoricalTaskVersionOrForgedResult()
    {
        var scenario = Scenario(); var image = RomImage.FromBytes(P28AdaptiveFuelTests.Image());
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28PostSelectionCriticalValidator.CreateRequest(image, scenario));
        var sequences = P28PostSelectionCriticalValidator.Analyze(image, scenario, response.Response, "A");
        foreach (var sequence in sequences)
        {
            Assert.Equal("Unresolved", sequence.Checkpoints[0].Disposition);
            Assert.Equal("NotRun", sequence.Checkpoints[1].Disposition);
            Assert.Equal(JsonValueKind.Null, sequence.Checkpoints[0].Actual.GetProperty("critical").ValueKind);
            Assert.Equal(JsonValueKind.Null, sequence.Checkpoints[1].Actual.GetProperty("words019x").ValueKind);
        }
        foreach (var edit in new Action<JsonNode>[] {
            n => n["runnerVersion"] = "0.25.0",
            n => n["operation"] = "fuelPostStoreConsumerChain",
            n => n["entryContracts"]![0]!["stop"] = "BeforeInstruction2259",
            n => n["criticalSequences"]![0]!["checkpoints"]![0]!["words019x"] = new JsonArray(0, 0, 0),
            n => n["criticalSequences"]![0]!["checkpoints"]![1]!["stateAfter"]!["ie"] = 0,
            n => n["criticalSequences"]![0]!["checkpoints"]![1]!["stateAtEntry"] = new JsonObject(),
            n => n["criticalSequences"]![0]!["checkpoints"]![1]!["prefix"]!["prefix"]!["snapshotWrites"] = new JsonArray(new JsonArray(0x190, 16, 0)),
            n => n["criticalSequences"]![0]!["checkpoints"]![0]!["extraHostWrites"] = new JsonArray()
        })
        {
            var forged = JsonNode.Parse(response.Response.GetRawText())!; edit(forged);
            Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalValidator.Analyze(image, scenario, JsonSerializer.SerializeToElement(forged), "A"));
        }
        var wrongTask = JsonNode.Parse(JsonSerializer.Serialize(P28PostSelectionCriticalValidator.CreateRequest(image, scenario), JsonDefaults.Create()))!;
        wrongTask["operation"] = "fuelPostStoreConsumerChain";
        await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, wrongTask));
    }

    [Theory]
    [InlineData(0, 17)]
    [InlineData(1, 99)]
    public async Task InventedAlternateConfigAndRamClobberProgramIsSyntheticNotOriginalProof(int config, int expectedOptional)
    {
        var rom = new byte[0x51]; rom[0x50] = (byte)config;
        // Independent low-address program: store X1, overwrite A from unrelated RAM,
        // then read config and conditionally skip an optional store. No OEM sequence.
        new byte[] { 0x60, 0x41, 1, 0x90, 0x7C, 0xA0, 0xE4, 0xA2, 0xD4, 0xA4, 0x62, 0x50, 0,
            0x92, 0xAA, 0xC9, 4, 0x77, 99, 0xD5, 0xA6, 0x77, 17, 0xD5, 0xA7 }.CopyTo(rom, 0);
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "synthetic", rom = rom.Select(b => (int)b).ToArray() } },
            scratchPatterns = new[] { 170 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { 25 },
                allowedCodeRanges = new[] { new[] { 0, rom.Length } },
                psw = 0x1101,
                lrb = 0x20,
                usp = 0x280,
                instructionBudget = 32,
                dataSeeds = new[] { new[] { 0x1A2, 7 }, new[] { 0x1A3, 0 }, new[] { 0xA6, 17 } },
                outputAddresses = new[] { 0x1A0, 0x1A1, 0x1A4, 0x1A5, 0xA6, 0xA7 }
            }
        });
        var result = response.Response.GetProperty("syntheticResult"); Assert.True(result.GetProperty("status").GetInt32() == 0, result.GetRawText());
        Assert.Equal(new[] { 65, 1, 7, 0, expectedOptional, 17 }, result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        var trace = result.GetProperty("trace").EnumerateArray().ToArray();
        Assert.Equal(config == 0, !trace.Any(t => t.GetProperty("pc").GetInt32() == 17));
    }

    private static void Reject(Action<JsonNode> edit, JsonElement good, P28PostSelectionCriticalOracle own)
    {
        var n = JsonNode.Parse(good.GetRawText())!; edit(n);
        Assert.ThrowsAny<Exception>(() => P28PostSelectionCriticalValidator.ValidateSuffix(JsonSerializer.SerializeToElement(n), good.GetProperty("entry"), own));
    }

    private static P28PostSelectionCriticalOracle Oracle(int x1 = 321, int a = 0, int current = 700, int ie = 0xBA98,
        int restoreIe = 0x5AA5, int psw = 0x9DC9, int[]? words = null)
    {
        var machine = new P28FuelAdditiveOracle([], [], [], [], [], [], [], [], a, psw, 5, 7, 88, 99, 0xB5);
        var prefix = new P28PostStoreConsumerOracle(machine, [], [], x1, 0xB5);
        return P28PostSelectionCriticalEvidence.Build(prefix, (ushort)current, (ushort)ie, (ushort)restoreIe, 0, words);
    }

    private static JsonElement Fixture(P28PostSelectionCriticalOracle own, int x1 = 321, int a = 0, int psw = 0x9DC9, int? steps = null, int status = 0)
    {
        var machine = own.Machine; var count = steps ?? machine.Events.Count; var events = machine.Events.Take(count).ToArray(); var registers = machine.RegisterEnds[count - 1];
        object Boundary(int pc, int value, int flags, int[] words, int pointer, int ssp) => new
        {
            pc,
            accumulator = value,
            psw = flags,
            dd = (flags & 0x1000) != 0,
            lrb = 0x20,
            x1 = pointer,
            x2 = 234,
            dp = 0x3B4,
            usp = 0x280,
            ssp,
            registers = words.SelectMany(word => new[] { word & 255, word >> 8 }).ToArray()
        };
        var accesses = machine.Accesses.Take(machine.AccessEnds[count - 1]).ToArray();
        return JsonSerializer.SerializeToElement(new
        {
            entry = Boundary(0x2259, a, psw, [5, 7, 88, 99], x1, 0x7FE),
            exit = Boundary(events[^1][1], events[^1][3], events[^1][5], registers, own.X1Ends[count - 1], machine.StackEnds[count - 1]),
            accesses,
            stage = new
            {
                result = new
                {
                    status,
                    usedAssumptions = Array.Empty<string>(),
                    steps = count,
                    stopPc = events[^1][1],
                    outputs = Array.Empty<int>(),
                    programReads = own.ProgramReads.Take(own.ProgramReadEnds[count - 1]).ToArray(),
                    trace = events.Select(e => new { pc = e[0], nextPc = e[1], instruction = "invented observation", accumulator = e[3], psw = e[5] }).ToArray(),
                    error = status == 0 ? null : "unresolved invented suffix",
                    executedInstructionBytes = events.SelectMany((e, i) => Enumerable.Range(e[0], machine.Lengths[i])).Distinct().Order().ToArray()
                },
                writes = accesses.Where(r => r[3] == 1).Select(r => new[] { r[1], r[2], r[4] }).ToArray(),
                events,
                sspAfter = machine.StackEnds[count - 1]
            }
        });
    }
}
