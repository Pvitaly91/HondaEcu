using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

[Collection(TimingSensitiveTestCollection.Name)]
public sealed class P28CommonResultConsumerTests
{
    internal static P28CommonResultConsumerScenario Scenario()
    {
        var old = P28PostSelectionCriticalTests.Scenario();
        return P28CommonResultConsumerScenario.Create(new(old.InitialState, new(0, false, false, 0, false, 1, 0, 2)), old.Calls,
            "Invented M2s bounded software stimuli; no physical or scheduler claims", [0]);
    }

    [Fact]
    public void ClosedSourcesAreOnceInitialAndCannotSetQuartetOrConsumers()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28CommonResultConsumerScenario.Parse(s.ToJson()).Digest);
        foreach (var field in new[] { "word03b6", "word03b8", "word03ba", "word03bc", "word0190", "word0192", "word0194", "word0150", "word03b4", "x1", "accumulator", "loopIndex", "consumerResult", "p2", "pc", "ram", "formula", "branch", "softwareSources" })
        {
            var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]![field] = 1;
            Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerScenario.Parse(n.ToJsonString()));
        }
        foreach (var mask in new[] { 1, 0x80, 0x8000, 65535 }) Assert.Throws<ArgumentException>(() => P28CommonResultConsumerScenario.Create(s.InitialState with { SoftwareSources = s.InitialState.SoftwareSources with { Word011aMask1034 = (ushort)mask } }, s.Calls, "Invalid neighboring word source"));
        foreach (var mask in new[] { 0, 4, 0x10, 0x20, 0x1000, 0x1034 }) _ = P28CommonResultConsumerScenario.Create(s.InitialState with { SoftwareSources = s.InitialState.SoftwareSources with { Word011aMask1034 = (ushort)mask } }, s.Calls, "Valid masked source");
        var request = JsonSerializer.SerializeToElement(P28CommonResultConsumerValidator.CreateRequest(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), s), JsonDefaults.Create());
        Assert.Equal("fuelCommonResultConsumerChain", request.GetProperty("operation").GetString()); Assert.False(request.TryGetProperty("fuelPostSelectionCriticalChain", out _));
        var n2 = JsonNode.Parse(s.ToJson())!; n2["formatVersion"] = 2; Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerScenario.Parse(n2.ToJsonString()));
        Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerScenario.Parse(s.ToJson().Replace("\"history013d\": 2", "\"history013d\": 2, \"history013d\": 3", StringComparison.Ordinal)));
    }

    [Theory]
    [InlineData(1, false, 0, 11)]
    [InlineData(4, false, 3, 11)]
    [InlineData(2, true, 4, 11)]
    [InlineData(0, false, 0, 5)]
    public void CounterAndDisablePathsCloseLocalOutputWithoutQuartetRead(int historyD, bool b7, int afterD, int result)
    {
        var (own, fixture) = Oracle(historyD, historyD == 0, b7: b7);
        Assert.Equal(0, own.Status); Assert.Equal(0x236C, own.StopPc); Assert.Equal(afterD, own.HistoryEnds[^1][1]); Assert.Equal(result, own.HistoryEnds[^1][0]);
        Assert.DoesNotContain(own.Machine.Accesses, a => a[1] is >= 0x3B6 and < 0x3BE);
        Assert.Contains(own.Machine.Accesses, a => a.SequenceEqual(new[] { 0x236A, 0x13B, 8, 1, result }));
        Assert.Equal(0, P28CommonResultConsumerValidator.ValidateSuffix(fixture, fixture.GetProperty("entry"), own).Status);
    }

    [Theory]
    [InlineData(0, 0x2333)]
    [InlineData(1, 0x233A)]
    [InlineData(65535, 0x233A)]
    public void UndefinedDivideAndPrimaryJgtConflictStopBeforeMandatoryInstruction(int divisor, int stop)
    {
        var (own, fixture) = Oracle(0, false, divisor);
        Assert.Equal(1, own.Status); Assert.Equal(stop, own.StopPc); Assert.DoesNotContain(own.Machine.Events, e => e[0] == stop);
        Assert.DoesNotContain(own.Machine.Accesses, a => a[0] == 0x236A);
        Assert.Equal(1, P28CommonResultConsumerValidator.ValidateSuffix(fixture, fixture.GetProperty("entry"), own).Status);
        var forged = JsonNode.Parse(fixture.GetRawText())!; forged["stage"]!["result"]!["status"] = 0;
        Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerValidator.ValidateSuffix(JsonSerializer.SerializeToElement(forged), fixture.GetProperty("entry"), own));
    }

    [Theory]
    [InlineData(0, 2)]
    [InlineData(48, 1)]
    [InlineData(112, 0)]
    [InlineData(0, 5)]
    [InlineData(48, 4)]
    [InlineData(112, 3)]
    public void ModeledNativePointerTableIndexHasExactSixSoftwareAddresses(int byteBe, int index)
    {
        var d9 = index >= 3 ? 174 : 46;
        var (own, fixture) = Oracle(0, false, byteBe: byteBe, d9: d9);
        Assert.Equal(new[] { 0x6106 + index }, own.ProgramReads); Assert.Equal(0x233A, own.StopPc);
        Assert.Equal(1, P28CommonResultConsumerValidator.ValidateSuffix(fixture, fixture.GetProperty("entry"), own).Status);
        Assert.Equal(0, own.Machine.Events.Single(e => e[0] == 0x22CA)[5] & 0x8000); // Own prior CF was zero and AND preserves it.
    }

    [Fact]
    public void WordMaskAndPreservesPriorCarryRatherThanInventingClearedCarry()
    {
        var (own, fixture) = Oracle(0, false, source133: 250);
        var logical = own.Machine.Events.Single(e => e[0] == 0x22CA);
        Assert.Equal(0x8000, logical[4] & 0x8000); Assert.Equal(0x8000, logical[5] & 0x8000);
        Assert.Equal(1, P28CommonResultConsumerValidator.ValidateSuffix(fixture, fixture.GetProperty("entry"), own).Status);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(700)]
    [InlineData(52428)]
    [InlineData(52429)]
    [InlineData(65535)]
    public void SyntheticModelOnlyCommonClampBoundaryDoesNotClaimActualSourceReachability(int currentWord)
    {
        var (own, fixture) = Oracle(2, false, currentWord: currentWord);
        var expected = Math.Min((long)currentWord * 5 / 4, 65535);
        Assert.Equal(expected, own.Machine.Events[0][2]);
        Assert.Equal(11, own.HistoryEnds[^1][0]);
        Assert.Equal(0, P28CommonResultConsumerValidator.ValidateSuffix(fixture, fixture.GetProperty("entry"), own).Status);
    }

    [Fact]
    public void CorrectFinalNumbersCannotHideEntryReloadBankWidthPointerOrForgedBranch()
    {
        var (own, good) = Oracle(3, false); var modeWrite = own.Machine.Accesses.ToList().FindIndex(a => a[0] == 0x22BA && a[3] == 1);
        foreach (var edit in new Action<JsonNode>[] {
            n => n["entry"]!["pc"] = 0x1550, n => n["entry"]!["accumulator"] = 1,
            n => n["entry"]!["psw"] = 0x0101, n => n["entry"]!["lrb"] = 0x40,
            n => n["entry"]!["x1"] = 2, n => n["entry"]!["dp"] = 0x3B6,
            n => n["entry"]!["usp"] = 0x180, n => n["entry"]!["ssp"] = 0x7FC,
            n => n["accesses"]![modeWrite]![2] = 16, n => n["accesses"]![modeWrite]![1] = 0x3B8,
            n => n["stage"]!["events"]![1]![1] = 0x1550,
            n => n["exit"]!["dp"] = 0x3B6, n => n["exit"]!["registers"]![0] = 77,
            n => n["hostWrites"] = new JsonArray(new JsonArray(0x3B8, 16, 0)),
            n => n["stage"]!["result"]!["error"] = "hidden completed execution failure",
            n => n["entry"]!["registers"]![0] = 77
        })
        {
            var n = JsonNode.Parse(good.GetRawText())!; edit(n);
            Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerValidator.ValidateSuffix(JsonSerializer.SerializeToElement(n), good.GetProperty("entry"), own));
        }
    }

    [Fact]
    public void PartialNativeCounterStorePersistsWithoutCompleted13bOutput()
    {
        var (own, _) = Oracle(3, false); var count = own.Machine.Events.ToList().FindIndex(e => e[0] == 0x2321) + 1;
        var fixture = Fixture(own, count, 1); Assert.Equal(1, P28CommonResultConsumerValidator.ValidateSuffix(fixture, fixture.GetProperty("entry"), own).Status);
        Assert.Equal(2, own.HistoryEnds[count - 1][1]); Assert.Equal(17, own.HistoryEnds[count - 1][0]);
        Assert.DoesNotContain(fixture.GetProperty("accesses").EnumerateArray(), a => a[0].GetInt32() == 0x236A);
    }

    [Fact]
    public void IndependentHistoryCarriesNativeCounterAndModeIntoFuturePrefixWithoutReseeding()
    {
        var scenario = Scenario();
        var call = scenario.Calls[0] with
        {
            Adaptive = scenario.Calls[0].Adaptive with
            {
                Fuel = scenario.Calls[0].Adaptive.Fuel with
                {
                    Sources = scenario.Calls[0].Adaptive.Fuel.Sources with { Source0133 = 250 }
                }
            }
        };
        scenario = P28CommonResultConsumerScenario.Create(scenario.InitialState with
        {
            Prefix = scenario.InitialState.Prefix with { Adaptive = scenario.InitialState.Prefix.Adaptive with { Joint = scenario.InitialState.Prefix.Adaptive.Joint with { Data012b = (byte)(scenario.InitialState.Prefix.Adaptive.Joint.Data012b & ~4) } } },
            SoftwareSources = scenario.InitialState.SoftwareSources with { History013d = 3, History013b = 17 }
        },
            Enumerable.Range(0, 3).Select(i => call with { Adaptive = call.Adaptive with { Fuel = call.Adaptive.Fuel with { Index = i } } }).ToArray(), "Invented independent persistent software history");
        var history = new P28CommonResultConsumerHistory(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), scenario, 85);
        var first = history.Step(scenario.Calls[0]); var second = history.Step(scenario.Calls[1]); var third = history.Step(scenario.Calls[2]);
        Assert.Equal(new[] { 2, 1, 0 }, new[] { (int)first.After.Byte013d, second.After.Byte013d, third.After.Byte013d });
        Assert.Equal(17, first.Before.Byte013b); Assert.Equal(11, second.Before.Byte013b); Assert.Equal(11, third.Before.Byte013b);
        Assert.Equal(first.After, second.Before); Assert.Equal(second.After, third.Before);
        Assert.Equal(4, first.After.Mode012b & 4); Assert.Equal(4, second.Entry.Mode012b & 4);
        Assert.Contains(first.Oracle.Machine.Events, e => e[0] == 0x22B6);
        Assert.DoesNotContain(second.Oracle.Machine.Events, e => e[0] == 0x22B6);
        foreach (var step in new[] { first, second, third })
        {
            Assert.Equal(0, step.Oracle.Status);
            Assert.Contains(step.Oracle.Machine.Accesses, a => a.SequenceEqual(new[] { 0x22BD, 0x13D, 8, 0, (int)step.Before.Byte013d }));
            Assert.Contains(step.Oracle.Machine.Accesses, a => a.SequenceEqual(new[] { 0x2321, 0x13D, 8, 1, (int)step.After.Byte013d }));
            Assert.Equal(first.Before.Word011a & 0x7FFF, step.Before.Word011a & 0x7FFF);
            Assert.Equal(first.Before.Byte011f, step.Before.Byte011f); Assert.Equal(first.Before.Byte0120, step.Before.Byte0120);
        }
    }

    [Fact]
    public void NextEventRequiresLiteralFull236cBoundaryBeforeEarlyScriptedAbi()
    {
        var (_, fixture) = Oracle(3, false); var exit = fixture.GetProperty("exit"); P28CommonResultConsumerValidator.RequireEventContinuation(exit, exit);
        foreach (var field in new[] { "pc", "accumulator", "psw", "lrb", "x1", "x2", "dp", "usp", "ssp" })
        {
            var n = JsonNode.Parse(exit.GetRawText())!; n[field] = n[field]!.GetValue<int>() ^ 1;
            Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerValidator.RequireEventContinuation(exit, JsonSerializer.SerializeToElement(n)));
        }
    }

    [Theory]
    [InlineData(0, 0, 0, 0)]
    [InlineData(7, 7, 7, 7)]
    [InlineData(1, 2, 3, 4)]
    [InlineData(65535, 0, 65535, 1)]
    public void StorageDomainFourReadLoopChecksDistinctGenerationsEvenEqualValues(int a, int b, int c, int d)
    {
        var own = P28CommonResultStorageModel.Build(4, [a, b, c, d]); P28CommonResultStorageModel.Validate(own, own);
        Assert.Equal(4, own.Generations.Select(g => (g.Address, g.WriterPc, g.WriteOrder)).Distinct().Count());
        Assert.Equal(new[] { 0x300, 0x302, 0x304, 0x306 }, own.Reads.Select(r => r.Address)); Assert.Equal((a + b + c + d) & 65535, own.Result);
    }

    [Theory]
    [InlineData("wrong-slot")]
    [InlineData("stale-generation")]
    [InlineData("byte-width")]
    [InlineData("swapped-order")]
    [InlineData("host-overwrite")]
    [InlineData("reseed")]
    [InlineData("wrong-loop-count")]
    [InlineData("missing-iteration")]
    [InlineData("duplicate-read")]
    [InlineData("forged-branch")]
    [InlineData("wrong-bank")]
    [InlineData("wrong-scale")]
    [InlineData("fake-scheduler-jump")]
    public void EqualSyntheticFinalResultCannotHideThirteenLineageForgeries(string forgery)
    {
        var own = P28CommonResultStorageModel.Build(4, [7, 7, 7, 7]); var reads = own.Reads.ToArray(); var generations = own.Generations.ToArray(); var observed = own;
        switch (forgery)
        {
            case "wrong-slot": reads[0] = reads[1]; observed = own with { Reads = reads }; break;
            case "stale-generation": reads[0] = reads[0] with { EventIndex = 3 }; observed = own with { Reads = reads }; break;
            case "byte-width": reads[0] = reads[0] with { Width = 8 }; observed = own with { Reads = reads }; break;
            case "swapped-order": (reads[0], reads[1]) = (reads[1], reads[0]); observed = own with { Reads = reads }; break;
            case "host-overwrite": observed = own with { InterveningWrites = new[] { new[] { 0x302, 16, 7 } } }; break;
            case "reseed": generations[1] = generations[1] with { WriterPc = 0 }; observed = own with { Generations = generations }; break;
            case "wrong-loop-count": observed = own with { LoopCount = 3 }; break;
            case "missing-iteration": observed = own with { Reads = reads.Take(3).ToArray() }; break;
            case "duplicate-read": reads[2] = reads[1]; observed = own with { Reads = reads }; break;
            case "forged-branch": observed = own with { Branches = new[] { new[] { 0x88, 0x90 }, new[] { 0x88, 0x80 }, new[] { 0x88, 0x80 }, new[] { 0x88, 0x90 } } }; break;
            case "wrong-bank": observed = own with { Bank = 0x40 }; break;
            case "wrong-scale": reads[2] = reads[2] with { Pointer = 2, Scale = 1 }; observed = own with { Reads = reads }; break;
            case "fake-scheduler-jump": observed = own with { EntryPc = 0x1550 }; break;
        }
        Assert.Equal(own.Result, observed.Result); Assert.Throws<InvalidDataException>(() => P28CommonResultStorageModel.Validate(own, observed));
    }

    [Theory]
    [InlineData("wrong-slot")]
    [InlineData("stale-generation")]
    [InlineData("byte-width")]
    [InlineData("swapped-order")]
    [InlineData("host-overwrite")]
    [InlineData("reseed")]
    [InlineData("wrong-loop-count")]
    [InlineData("missing-iteration")]
    [InlineData("duplicate-read")]
    [InlineData("forged-branch")]
    [InlineData("wrong-bank")]
    [InlineData("wrong-scale")]
    [InlineData("fake-scheduler-jump")]
    public void BoundedPartARejectsInventedQuartetConsumerEvidenceEvenWithSameSoftwareOutput(string forgery)
    {
        var (own, good) = Oracle(2, false); var n = JsonNode.Parse(good.GetRawText())!;
        switch (forgery)
        {
            case "wrong-slot": n["accesses"]![0]![1] = 0x3B8; break;
            case "stale-generation": n["generation"] = 0; break;
            case "byte-width": n["accesses"]![0]![2] = 16; break;
            case "swapped-order": n["accesses"]![0] = n["accesses"]![1]!.DeepClone(); break;
            case "host-overwrite": n["hostWrites"] = new JsonArray(new JsonArray(0x3B6, 16, 875)); break;
            case "reseed": n["initialSeeds"] = new JsonArray(new JsonArray(0x3B6, 16, 875)); break;
            case "wrong-loop-count": n["loopCount"] = 4; break;
            case "missing-iteration": n["consumerReads"] = new JsonArray(new JsonArray(0x3B6, 16, 875)); break;
            case "duplicate-read": n["accesses"]!.AsArray().Add(new JsonArray(0x1550, 0x3B6, 16, 0, 875)); break;
            case "forged-branch": n["stage"]!["events"]![0]![1] = 0x1550; break;
            case "wrong-bank": n["entry"]!["lrb"] = 0x40; break;
            case "wrong-scale": n["exit"]!["dp"] = 0x3B6; break;
            case "fake-scheduler-jump": n["exit"]!["pc"] = 0x05DF; break;
        }
        Assert.Equal(good.GetProperty("exit").GetProperty("accumulator").GetInt32(), n["exit"]!["accumulator"]!.GetValue<int>());
        Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerValidator.ValidateSuffix(JsonSerializer.SerializeToElement(n), good.GetProperty("entry"), own));
    }

    [Fact]
    public void StorageBranchesRequireTwoColumnTuplesNotOnlyEqualFlattenedNumbers()
    {
        var own = P28CommonResultStorageModel.Build(4, [7, 7, 7, 7]);
        var malformed = own with { Branches = new[] { new[] { 0x88 }, new[] { 0x80, 0x88, 0x80 }, new[] { 0x88, 0x80 }, new[] { 0x88, 0x90 } } };
        Assert.Equal(own.Branches.SelectMany(b => b), malformed.Branches.SelectMany(b => b));
        Assert.Throws<InvalidDataException>(() => P28CommonResultStorageModel.Validate(own, malformed));
    }

    [Fact]
    public async Task RealNewOperationKeepsPrefixPartialAndTerminalRefusesTaskVersionAndRetainedResult()
    {
        var scenario = Scenario(); var image = RomImage.FromBytes(P28AdaptiveFuelTests.Image());
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28CommonResultConsumerValidator.CreateRequest(image, scenario));
        var sequences = P28CommonResultConsumerValidator.Analyze(image, scenario, response.Response, "A");
        foreach (var sequence in sequences) { Assert.Equal("Unresolved", sequence.Checkpoints[0].Disposition); Assert.Equal("NotRun", sequence.Checkpoints[1].Disposition); Assert.Null(sequence.Checkpoints[0].SoftwareResult13b); Assert.Equal(4, sequence.Checkpoints[0].QuartetGenerations.Count); }
        foreach (var edit in new Action<JsonNode>[] {
            n => n["runnerVersion"] = "0.26.0", n => n["operation"] = "fuelPostSelectionCriticalChain",
            n => n["commonResultSequences"]![0]!["checkpoints"]![0]!["softwareResult13b"] = 17,
            n => n["commonResultSequences"]![0]!["checkpoints"]![1]!["stateAfter"]!["byte013d"] = 99,
            n => n["commonResultSequences"]![0]!["checkpoints"]![1]!["commonConsumer"] = new JsonObject(),
            n => n["commonResultSequences"]![0]!["checkpoints"]![1]!["stateBefore"]!["prefix"]!["commonWords03b6"]![1] = 321
        }) { var n = JsonNode.Parse(response.Response.GetRawText())!; edit(n); Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerValidator.Analyze(image, scenario, JsonSerializer.SerializeToElement(n), "A")); }
        var wrongTask = JsonNode.Parse(JsonSerializer.Serialize(P28CommonResultConsumerValidator.CreateRequest(image, scenario), JsonDefaults.Create()))!; wrongTask["operation"] = "fuelPostSelectionCriticalChain";
        await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, wrongTask));
    }

    [Fact]
    public async Task NewValidatorExecuteSeparatesTimeoutAndActiveCancellationWithoutOutput()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28AdaptiveFuelTests.Image());
        var options = new SliceProcessOptions { Arguments = [ProcessHandshake.HostPath, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) };
        var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => P28CommonResultConsumerValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options));
        Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
        using var cancelled = new CancellationTokenSource(); cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28CommonResultConsumerValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options, cancelled.Token));
        await ProcessHandshake.AssertActiveCancellationAsync((activeOptions, token) => P28CommonResultConsumerValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), activeOptions, token));
    }

    internal static (P28CommonResultConsumerOracle Own, JsonElement Fixture) Oracle(int historyD, bool disable, int divisor = 1, bool b7 = false, int byteBe = 0, int d9 = 46, int source133 = 100, int currentWord = 700)
    {
        var machine = new P28FuelAdditiveOracle([], [], [], [], [], [], [], [], 0, 0x9DC9, 5, 7, 88, 99, 0);
        var r = P28PostSelectionCriticalEvidence.Build(new(machine, [], [], 0, 0), (ushort)currentWord, 0xBA98, 0x5AA5, 0);
        var common = (int)Math.Min((long)currentWord * 5 / 4, 65535);
        var state = new P28CommonResultConsumerState(new(0x5AA5, 0x5AA5, [0, 0, 0], (ushort)currentWord, [common, common, common, common], 0, 0), 0, 0, 0, 0, (byte)byteBe, (byte)(b7 ? 1 : 0), (ushort)divisor, 17, (byte)historyD);
        var call = Scenario().Calls[0] with { Disable125 = disable, Adaptive = Scenario().Calls[0].Adaptive with { RawD9 = (byte)d9, Fuel = Scenario().Calls[0].Adaptive.Fuel with { Sources = Scenario().Calls[0].Adaptive.Fuel.Sources with { Source0133 = (byte)source133 } } } };
        var bytes = P28AdaptiveFuelTests.Image(); for (var i = 0; i < 6; i++) bytes[0x6106 + i] = (byte)(i + 1);
        var own = P28CommonResultConsumerEvidence.Build(RomImage.FromBytes(bytes), r, state, call, disable ? 16 : 0);
        return (own, Fixture(own));
    }
    private static JsonElement Fixture(P28CommonResultConsumerOracle own, int? stepCount = null, int? status = null)
    {
        var machine = own.Machine; var count = stepCount ?? machine.Events.Count; var events = machine.Events.Take(count).ToArray();
        // First instructions leave the modeled bank unchanged, so its first end is the entry bank.
        var entryRegisters = machine.RegisterEnds[0]; var registers = machine.RegisterEnds[count - 1]; var accesses = machine.Accesses.Take(machine.AccessEnds[count - 1]).ToArray();
        object Boundary(int pc, int a, int psw, int[] regs, int dp, int ssp) => new { pc, accumulator = a, psw, dd = (psw & 0x1000) != 0, lrb = 0x20, x1 = 0, x2 = 234, dp, usp = 0x280, ssp, registers = regs.SelectMany(w => new[] { w & 255, w >> 8 }).ToArray() };
        var resultStatus = status ?? own.Status;
        return JsonSerializer.SerializeToElement(new
        {
            entry = Boundary(0x22B1, events[0][2], events[0][4], entryRegisters, 0x3B4, 0x7FE),
            exit = Boundary(events[^1][1], events[^1][3], events[^1][5], registers, own.DpEnds[count - 1], machine.StackEnds[count - 1]),
            accesses,
            stage = new
            {
                result = new
                {
                    status = resultStatus,
                    usedAssumptions = Array.Empty<string>(),
                    steps = count,
                    stopPc = events[^1][1],
                    outputs = Array.Empty<int>(),
                    programReads = own.ProgramReads.Take(own.ProgramReadEnds[count - 1]).ToArray(),
                    trace = events.Select(e => new { pc = e[0], nextPc = e[1], instruction = "invented observation", accumulator = e[3], psw = e[5] }).ToArray(),
                    error = resultStatus == 0 ? null : "strict invented unresolved stop",
                    executedInstructionBytes = events.SelectMany((e, i) => Enumerable.Range(e[0], machine.Lengths[i])).Distinct().Order().ToArray()
                },
                writes = accesses.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray(),
                events,
                sspAfter = machine.StackEnds[count - 1]
            }
        });
    }
}
