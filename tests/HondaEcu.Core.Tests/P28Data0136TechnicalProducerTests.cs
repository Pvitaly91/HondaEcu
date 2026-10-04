using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28Data0136TechnicalProducerTests
{
    internal static P28Data0136TechnicalInitialState State(bool divided = false, byte gate = 8) => new(0, 0, 0xA4, divided ? (byte)4 : (byte)0, gate, 999, [11, 22, 33, 44, 55, 66]);
    internal static P28Data0136TechnicalProducerScenario Scenario(bool divided = false) => P28Data0136TechnicalProducerScenario.Create(State(divided),
        [new(0, 12, 0, 0, 0, divided ? (ushort)12 : null), new(1, 24, 0, 0, 5, divided ? (ushort)24 : null)], "Model-only diagnostic fixture;no OEM bytes", [0]);

    [Theory]
    [InlineData(5, 0, 0, 0)]
    [InlineData(6, 0, 0, 1)]
    [InlineData(504, 0, 0, 84)]
    [InlineData(32770, 33000, 1, 10884)]
    [InlineData(32769, 32770, 0, 0)]
    [InlineData(32768, 32750, 2, 21848)]
    [InlineData(65535, 5, 5, 65535)]
    [InlineData(50000, 50000, 6, 0)]
    public void ModelOnlyBoundariesUseOwnSourcesAndExactByteBorrow(int source, int previous, int counter, int expected)
    {
        var own = new P28Data0136TechnicalProducerModel(State(true) with { Previous00ee = (ushort)previous, Counter00ae = (byte)counter }, 85);
        var oracle = own.Run(new(0, 123, 0, 0, 0, (ushort)source));
        Assert.Equal(expected, own.Word(0x136)); Assert.Equal(0x5719, own.Pc);
        Assert.Equal(new[] { 0x3A, 16, 0, 123 }, oracle.PeripheralReads[0]); Assert.DoesNotContain(oracle.PeripheralReads, r => r[0] == 0x42);
        Assert.Contains(oracle.Accesses, r => r[0] == 0x56F3 && r[1] == 0x136 && r[2] == 16 && r[3] == 1);
        Assert.DoesNotContain(oracle.Steps, s => s.Event[0] == 0x5707 || s.Event[0] == 0x570E);
        Assert.Equal(6, oracle.Writes.Count(r => r[0] >= 0x360 && r[0] < 0x36C));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void ModelOnlyPersistentGateMakesWriterThenHeldUnreachableWithoutForbiddenReseeding(bool divided)
    {
        var own = new P28Data0136TechnicalProducerModel(State(divided, 0), 0);
        for (var i = 0; i < 6; i++)
        {
            var s = (ushort)(12 * i); var oracle = own.Run(new(i, s, 0, 0, (byte)i, divided ? s : null));
            Assert.Equal(i == 0 ? 0 : 1, oracle.Writes.Count(w => w[0] == 0x136));
            Assert.True((own.Snapshot()[Array.IndexOf(P28Data0136TechnicalProducerModel.RamAddresses, 0x128)] & 8) != 0);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void SyntheticEvidenceGuardTracksSameValueAsNewIdentityAndNoOtherWriter(bool divided)
    {
        var scenario = Scenario(divided); var report = Analyze(scenario, Mock(scenario));
        Assert.False(report.HasFailure);
        foreach (var sequence in report.Sequences)
        {
            var a = sequence.Checkpoints[0]; var b = sequence.Checkpoints[1];
            Assert.Equal(a.NativeWord0136, b.NativeWord0136); Assert.NotEqual(a.Generation, b.Generation);
            Assert.Equal(divided ? 0x56F3 : 0x5707, a.Writer!.WriterPc); Assert.Equal(a.Generation, b.Generation! with { EventIndex = 0 });
            Assert.Equal(divided ? 0 : 1, a.SameRoutineReaders.Count);
        }
        // Fabricated guard evidence is NOT an executed original program/native corpus.
    }

    [Theory]
    [InlineData("wrong-writer")]
    [InlineData("wrong-width")]
    [InlineData("host0136-overwrite")]
    [InlineData("missing-tmr2")]
    [InlineData("unknown-sfr")]
    [InlineData("wrong-sfr-width")]
    [InlineData("snapshot-change")]
    [InlineData("ram-reseed")]
    [InlineData("source-in-journal")]
    [InlineData("extra-source")]
    [InlineData("wrong-form")]
    [InlineData("missing-read")]
    [InlineData("wrong-flags")]
    [InlineData("both-writers")]
    [InlineData("wrong-order")]
    [InlineData("missing-store")]
    [InlineData("wrong-generation-value")]
    [InlineData("missing-extent")]
    public void SyntheticJournalForgeriesRejectEvenWithCorrectFinalWord(string fault)
    {
        var s = Scenario(); var n = Mock(s); var c = n["data0136Sequences"]![0]!["checkpoints"]![0]!;
        Assert.False(Analyze(s, n).HasFailure); // Refusal must reach the intended guard, not a bad fixture identity.
        var accesses = c["accesses"]!.AsArray(); var writer = accesses.Single(a => a![1]!.GetValue<int>() == 0x136 && a[3]!.GetValue<int>() == 1)!;
        switch (fault)
        {
            case "wrong-writer": writer[0] = 0x56F3; break;
            case "wrong-width": writer[2] = 8; break;
            case "host0136-overwrite": c["ramBefore"]![Array.IndexOf(P28Data0136TechnicalProducerModel.RamAddresses, 0x136)] = 7; break;
            case "missing-tmr2": c["peripheralAccesses"]!.AsArray().RemoveAt(0); break;
            case "unknown-sfr": c["peripheralAccesses"]!.AsArray().Add(new JsonArray(0x22, 8, 0, 0)); break;
            case "wrong-sfr-width": c["peripheralAccesses"]![0]![1] = 8; break;
            case "snapshot-change": c["peripheralAccesses"]![0]![3] = 13; break;
            case "ram-reseed": n["data0136Sequences"]![0]!["checkpoints"]![1]!["ramBefore"]![Array.IndexOf(P28Data0136TechnicalProducerModel.RamAddresses, 0x136)] = 9; break;
            case "source-in-journal": c["writes"]!.AsArray().Insert(0, new JsonArray(0xF0, 16, 12)); break;
            case "extra-source": c["sourceApplications"]!.AsArray().Add(new JsonArray(0x136, 16, 12)); break;
            case "wrong-form": c["result"]!["trace"]![0]!["instruction"] = "LB A, N8"; break;
            case "missing-read": accesses.Remove(accesses.Single(a => a![0]!.GetValue<int>() == 0x570E)); break;
            case "wrong-flags": c["events"]![0]![5] = 0; break;
            case "both-writers": accesses.Add(new JsonArray(0x56F3, 0x136, 16, 1, 12)); break;
            case "wrong-order": (accesses[0], accesses[1]) = (accesses[1]!.DeepClone(), accesses[0]!.DeepClone()); break;
            case "missing-store": accesses.Remove(writer); break;
            case "wrong-generation-value": writer[4] = 13; break;
            case "missing-extent": c["result"]!["executedInstructionBytes"]!.AsArray().RemoveAt(0); break;
        }
        Assert.Throws<SliceProcessException>(() => Analyze(s, n));
    }

    [Fact]
    public void SyntheticPartialWriterRetainedAndTerminalObservationsNeverApplyInputs()
    {
        var s = Scenario(); var n = Mock(s, partial: true); var report = Analyze(s, n);
        foreach (var seq in report.Sequences)
        {
            var first = seq.Checkpoints[0]; var next = seq.Checkpoints[1];
            Assert.Null(first.NativeWord0136); Assert.Equal("PartialNativeWritten", first.GenerationDisposition);
            Assert.Equal(12, first.RetainedWord0136); Assert.Equal(first.Generation, next.Generation);
            Assert.Equal("NotRun", next.Disposition); Assert.Null(next.NativeWord0136);
        }
        n["data0136Sequences"]![0]!["checkpoints"]![1]!["sourceApplications"]!.AsArray().Add(new JsonArray(0xF0, 16, 24));
        Assert.Throws<SliceProcessException>(() => Analyze(s, n));
    }

    [Theory]
    [InlineData("data0136")]
    [InlineData("expected0136")]
    [InlineData("dividend")]
    [InlineData("quotient")]
    [InlineData("writerPc")]
    [InlineData("flags")]
    [InlineData("pc")]
    [InlineData("ram")]
    [InlineData("data011f")]
    public void ClosedSchemaRefusesReadyOutputAndPerEventControl(string name)
    {
        var n = JsonNode.Parse(Scenario().ToJson())!; n["observations"]![0]![name] = 1;
        Assert.Throws<InvalidDataException>(() => P28Data0136TechnicalProducerScenario.Parse(n.ToJsonString()));
    }

    [Fact]
    public void SchemaModeWidthsBoundsOwnershipAndDuplicateChecks()
    {
        Assert.Equal(Scenario(true).Digest, P28Data0136TechnicalProducerScenario.Parse(Scenario(true).ToJson()).Digest);
        Assert.Throws<ArgumentException>(() => P28Data0136TechnicalProducerScenario.Create(State(true), [new(0, 1, 0, 0, 0)], "missing00F0"));
        Assert.Throws<ArgumentException>(() => P28Data0136TechnicalProducerScenario.Create(State(), [new(0, 1, 0, 0, 0, 1)], "extra00F0"));
        Assert.Throws<ArgumentException>(() => P28Data0136TechnicalProducerScenario.Create(State(), Enumerable.Range(0, 257).Select(i => new P28Data0136TechnicalObservation(i, 0, 0, 0, 0)).ToArray(), "too many"));
        var text = Scenario().ToJson(false);
        Assert.Throws<InvalidDataException>(() => P28Data0136TechnicalProducerScenario.Parse(text.Replace("\"index\":0", "\"index\":0,\"index\":0", StringComparison.Ordinal)));
        var n = JsonNode.Parse(text)!; n["observations"]![0]!["source00f0"] = 65536;
        Assert.ThrowsAny<Exception>(() => P28Data0136TechnicalProducerScenario.Parse(n.ToJsonString()));
        var samples = new ushort[] { 1, 2, 3, 4, 5, 6 }; var s = P28Data0136TechnicalProducerScenario.Create(State() with { Samples = samples }, [new(0, 1, 0, 0, 0)], "freeze"); samples[0] = 999;
        Assert.Equal((ushort)1, s.InitialState.Samples[0]);
    }

    [Fact]
    public void HistoricalRunnerCannotClaimNewCapabilityOrInventory()
    {
        var s = Scenario(); var n = Mock(s); n["runnerVersion"] = "0.28.0";
        Assert.Throws<SliceProcessException>(() => Analyze(s, n));
        n = Mock(s); n["localSemanticFixes"]!.AsArray().RemoveAt(0);
        Assert.Throws<SliceProcessException>(() => Analyze(s, n));
        Assert.Equal("ProducerNotRun_IRQDependent", P28Data0136ProducerModel.Current.Status);
    }

    [Fact]
    public async Task InventedUnsupportedEntryIsPartialAndTimeoutCancellationPublishNoNativeResult()
    {
        var s = Scenario(); var image = RomImage.FromBytes(new byte[32768]);
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28Data0136TechnicalProducerValidator.CreateRequest(image, s));
        var report = P28Data0136TechnicalProducerValidator.Analyze(image, "invented", s, response.Response);
        Assert.True(report.HasFailure); Assert.All(report.Sequences, q => { Assert.Null(q.Checkpoints[0].NativeWord0136); Assert.Equal("NotRun", q.Checkpoints[1].Disposition); });
        using var cancel = new CancellationTokenSource(); cancel.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28Data0136TechnicalProducerValidator.CreateRequest(image, s), cancellationToken: cancel.Token));
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync("dotnet", P28Data0136TechnicalProducerValidator.CreateRequest(image, s), new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) }));
        Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
    }

    private static P28Data0136TechnicalProducerReport Analyze(P28Data0136TechnicalProducerScenario s, JsonNode n) =>
        P28Data0136TechnicalProducerValidator.Analyze(RomImage.FromBytes(new byte[32768]), "model-only", s, JsonSerializer.SerializeToElement(n));
    private static JsonNode Mock(P28Data0136TechnicalProducerScenario s, bool partial = false)
    {
        // Pure fabricated protocol evidence from own sources, not a firmware program.
        var sequences = new List<object>();
        foreach (var pattern in new[] { 0, 85, 170 })
        {
            var own = new P28Data0136TechnicalProducerModel(s.InitialState, pattern); var checkpoints = new List<object>(); var terminal = false;
            object Boundary(int pc, int a, int psw, int[] ram)
            {
                int B(int address) => ram[Array.IndexOf(P28Data0136TechnicalProducerModel.RamAddresses, address)]; int W(int address) => B(address) | (B(address + 1) << 8);
                return new { pc, accumulator = a, psw, dd = (psw & 0x1000) != 0, lrb = 0x21, x1 = W(0x90), x2 = W(0x92), dp = W(0x94), usp = W(0x96), ssp = 0x7FE, registers = Enumerable.Range(0x108, 8).Select(B).ToArray() };
            }
            foreach (var o in s.Observations)
            {
                var before = own.Snapshot();
                if (terminal) { checkpoints.Add(new { o.Index, result = (object?)null, sourceApplications = Array.Empty<int[]>(), entry = (object?)null, exit = (object?)null, ramBefore = before, ramAfter = before, events = Array.Empty<int[]>(), accesses = Array.Empty<int[]>(), writes = Array.Empty<int[]>(), peripheralAccesses = Array.Empty<int[]>() }); continue; }
                var limit = partial ? new P28Data0136TechnicalProducerModel(s.InitialState, pattern).Run(o).Steps.TakeWhile(x => x.Event[0] != 0x5709).Count() : 128;
                var r = own.Run(o, limit); terminal = partial;
                checkpoints.Add(new
                {
                    o.Index,
                    result = new
                    {
                        status = partial ? 1 : 0,
                        usedAssumptions = Array.Empty<string>(),
                        steps = r.Steps.Count,
                        stopPc = own.Pc,
                        outputs = Array.Empty<int>(),
                        programReads = Array.Empty<int>(),
                        trace = r.Steps.Select(x => new { pc = x.Event[0], nextPc = x.Event[1], instruction = x.Form, psw = x.Event[5], accumulator = x.Event[3] }).ToArray(),
                        error = partial ? "Invented unresolved suffix" : null,
                        executedInstructionBytes = r.Steps.SelectMany(x => Enumerable.Range(x.Event[0], x.Length)).Distinct().Order().ToArray()
                    },
                    sourceApplications = r.SourceApplications.Chunk(3).ToArray(),
                    entry = Boundary(0x56BE, r.EntryA, 0x1DCA, r.EntryRam),
                    exit = Boundary(own.Pc, own.A, own.Psw, own.Snapshot()),
                    ramBefore = before,
                    ramAfter = own.Snapshot(),
                    events = r.Steps.Select(x => x.Event).ToArray(),
                    accesses = r.Accesses,
                    writes = r.Writes,
                    peripheralAccesses = r.PeripheralReads
                });
            }
            sequences.Add(new { imageIndex = 0, scratchPattern = pattern, completedObservations = partial ? 0 : s.Observations.Count, checkpoints });
        }
        var baseFixes = (string[])typeof(SliceRunnerIdentity).GetField("CurrentFixes", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)!.GetValue(null)!;
        string[] fixes = [..baseFixes,"adaptive-exact-word-add-sub-half-carry","idle-exact-arithmetic-half-carry",
            "word-rol-accumulator-through-carry-preserves-noncarry-flags","word-add-accumulator-er0-offpage-half-carry",
            "word-rol-er0-through-carry-preserves-noncarry-flags","word-sll-accumulator-preserves-noncarry-flags",
            "word-add-dp-immediate-half-carry","byte-sbc-r0-immediate-half-borrow","word-decrement-x1-half-borrow"];
        return JsonSerializer.SerializeToNode(new
        {
            protocolVersion = 1,
            operation = P28Data0136TechnicalProducerValidator.Operation,
            runnerVersion = SliceRunnerIdentity.HandoffVersion,
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = fixes,
            entryContracts = P28Data0136TechnicalProducerValidator.ExpectedContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            data0136Sequences = sequences
        }, JsonDefaults.Create())!;
    }
}
