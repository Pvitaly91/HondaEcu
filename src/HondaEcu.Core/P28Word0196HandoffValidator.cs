using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28Word0196HandoffCheckpoint(int Index, string Disposition, string Provenance, P28QuartetHandoffCheckpoint Prefix,
    P28QuartetGeneration? ProducerGeneration0196, P28QuartetGeneration? ReaderGeneration0196, int? ReaderValue, int? SoftwareEr1, int StopPc, JsonElement Actual);
public sealed record P28Word0196HandoffSequence(string Image, int ScratchPattern, IReadOnlyList<P28Word0196HandoffCheckpoint> Checkpoints);
public sealed record P28Word0196HandoffComparison(int ScratchPattern, int Index, int? ValueA, int? ValueB, bool? Diverged, bool? SoftwareEr1Diverged, string Effect);
public sealed record P28Word0196HandoffReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28Word0196HandoffSequence> Sequences,
    IReadOnlyList<P28Word0196HandoffComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition is not ("QuartetDerived0196ConsumerStrict" or "GateBypass0196ConsumerStrict"));
    public string Word0196TechnicalConsumer => !HasFailure && Sequences.SelectMany(s => s.Checkpoints).Any(c => c.ReaderGeneration0196 is not null) ? "Validated" : "Partial";
    public string Word0196ScheduledHandoff => !HasFailure && Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition == "QuartetDerived0196ConsumerStrict") ? "Validated" : "Partial";
    public object Summary => new { Events = Sequences.Sum(s => s.Checkpoints.Count), Native0196Writes = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.ProducerGeneration0196 is not null), SameGeneration54faReads = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.ReaderGeneration0196 is not null), QuartetDerivedHandoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "QuartetDerived0196ConsumerStrict"), GateBypassHandoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "GateBypass0196ConsumerStrict"), SoftwareCompletions = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition.EndsWith("ConsumerStrict", StringComparison.Ordinal)), TimerBoundaryStops = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition.EndsWith("ConsumerStrict", StringComparison.Ordinal) && c.StopPc == 0x5503), PerSlotHandoffs = Enumerable.Range(0, 4).ToDictionary(i => $"slot{i}", i => Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "QuartetDerived0196ConsumerStrict" && c.Prefix.SelectedSlot == i)), AbWitnesses = Comparisons.Count(c => c.Diverged == true), SoftwareEr1Witnesses = Comparisons.Count(c => c.SoftwareEr1Diverged == true), Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()), FrozenTimerExecutions = 0, Cmp5578Executions = 0 };
    public string TimerContinuation => "NotRun";
    public string TimerEvidence => "PrimaryPeripheralEvidenceMissing;5508WordWriteNotReadOnly";
    public string InterStageScheduling => "ExplicitHarnessSchedule";
    public string Recovered0196Scheduler => "NotEstablished";
    public string EntryClassification => "TechnicalSeeded0196ConsumerEntry";
    public string EntryAbi => "PC only;all other CPU/RAM retained";
    public string CallFrame => "TechnicalEntryDoesNotClaimCallFrame";
    public string IrqDelivery => "NotInjected";
    public string PendingInterrupt => "NotModeled";
    public string ElapsedTime => "None";
    public string Physical0196Role => "Unknown";
    public string P2 => "NotRun";
    public string PhysicalOutput => "NotRun";
    public string OtherConsumer157E => "StaticOther0196Consumer/NotRun";
    public string Cmp5578 => "StaticOnly;0196WordVsImmediate00C0";
    public string Data00C0 => "NotAnOperand;NoRAMSource";
    public string M2xQuartetScheduledHandoff => "Validated;unchanged";
    public string M2wTechnicalScheduledHandoff => "Validated;DATA0136 only;unchanged";
    public string M2tJgt => "Blocked/Unresolved";
    public string SkippedCode => "NotExecuted";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public int FirmwareBin => 0;
}
public static class P28Word0196HandoffValidator
{
    public const string Operation = "word0196ConsumerHandoff";
    public static object CreateRequest(RomImage image, P28Word0196HandoffScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28QuartetHandoffValidator.CreateRequest(image, scenario.PrefixScenario), JsonDefaults.Create());
        var wire = old.GetProperty("quartetConsumerHandoff");
        return new { protocolVersion = 1, operation = Operation, images = old.GetProperty("images"), scratchPatterns = new[] { 0, 85, 170 }, allowAssumptions = Array.Empty<string>(), word0196ConsumerHandoff = new { formatVersion = 1, initialState = new { quartetPrefix = wire.GetProperty("initialState"), scenario.InitialState.Bit0128_2, scenario.InitialState.Byte0117 }, calls = wire.GetProperty("calls"), scenario.TraceEventIndexes } };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28QuartetHandoffValidator.ExpectedContracts()[0],
        entryPc = 0x54F5, stopBefore = 0x5503, alternateStopBefore = new[] { 0x5533, 0x556F }, codeRanges = new[] { new[] { 0x54F5, 0x5503 } }, instructionBudget = 6,
        entryClassification = "TechnicalSeeded0196ConsumerEntry", abiWrites = "PC only;A/PSW/LRB/SCB/pointers/USP/SSP/locals retained", callFrame = "TechnicalEntryDoesNotClaimCallFrame",
        sourcePolicy = "OnceInitialSoftwareSnapshot;NoEventOrBoundaryReseed", sourceMasks = new[] { new[] { 0x128, 4 } }, sourceBytes = new[] { 0x117 }, reader = new[] { 0x54FA, 0x196, 16 }, nativeSoftwareStores = new[] { new[] { 0x54F8, 0x108, 8 }, new[] { 0x54FC, 0x10A, 16 } },
        generation = "writerPC,eventIndex,zeroBasedAllNativeWriteOrder,value;NoOverlap0196/0197", machine = "OneCpuOneBusPerSequence;NoSerializationHandoff", interStageScheduling = "ExplicitHarnessSchedule", recovered0196Scheduler = "NotEstablished",
        firstHardwareAccess = new[] { 0x5503, 0x30, 16, 0 }, laterTimerWrite = new[] { 0x5508, 0x32, 16, 1 }, timerContinuation = "NotRun;PrimaryPeripheralEvidenceMissing;WriteNotReadOnly", cmp5578 = "StaticOnly;0196WordVsImmediate00C0;NotRAM00C0", p2 = "NotRun", otherConsumer157E = "StaticOther0196Consumer/NotRun",
        partial = "Terminal;UnadmittedPureAlternateNotHardwareBoundary;LaterNotRun", irqDelivery = "NotInjected", elapsedTime = "None", skippedCode = "NotExecuted", physical0196Role = "Unknown", physicalRpmAvailable = false, canaryAddresses = new[] { 0x300, 0x350, 0x3E0 } } });
    public static async Task<P28Word0196HandoffReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28Word0196HandoffScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28Word0196HandoffSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2y same-generation software consumer evidence.", e); }
        }
        var comparisons = new List<P28Word0196HandoffComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var complete = a.Disposition == "QuartetDerived0196ConsumerStrict" && b.Disposition == "QuartetDerived0196ConsumerStrict";
                    bool? changed = complete ? a.ReaderValue != b.ReaderValue : null; bool? softwareChanged = complete ? a.SoftwareEr1 != b.SoftwareEr1 : null;
                    comparisons.Add(new(sequences[p].ScratchPattern, i, a.ReaderValue, b.ReaderValue, changed, softwareChanged, !complete ? "IncompleteOrUpstreamGateBypass" : changed == true ? "FuelCellToQuartetToNative0196To54FAWitness" : "EqualValue;GenerationIdentityStillRequired"));
                }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, offsets, sequences, comparisons, contract);
    }
    internal static IReadOnlyList<P28Word0196HandoffSequence> Analyze(RomImage image, P28Word0196HandoffScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "word0196HandoffSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2y contract differs.");
        foreach (var k in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(k).GetArrayLength() == 0, "Foreign rows."); Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty("word0196HandoffSequences"); Require(seq.GetArrayLength() == 3, "Three scratch histories required.");
        JsonElement Row(int p, int i) => seq[p].GetProperty("checkpoints")[i];
        bool Terminal(int p, int i) { var c = Row(p, i).GetProperty("consumer"); return c.ValueKind == JsonValueKind.Object && N(c.GetProperty("stage").GetProperty("result"), "status") != 0; }
        var reports = Enumerable.Range(0, 3).Select(_ => new List<P28Word0196HandoffCheckpoint>()).ToArray();
        // Validation projection only. Execution has no JSON/RAM transfer or second machine.
        var view = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = P28QuartetHandoffValidator.Operation,
            runnerVersion = root.GetProperty("runnerVersion"),
            upstreamCommit = root.GetProperty("upstreamCommit"),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            entryContracts = P28QuartetHandoffValidator.ExpectedContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            quartetHandoffSequences = seq.EnumerateArray().Select(s => new { scratchPattern = s.GetProperty("scratchPattern"), machineInstances = s.GetProperty("machineInstances"), checkpoints = s.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("prefix")).ToArray() }).ToArray()
        });
        _ = P28QuartetHandoffValidator.Analyze(image, scenario.PrefixScenario, view, id, new((p, i) => Row(p, i).GetProperty("after"), Terminal, (p, i, ownPrefix, registers) =>
        {
            var pattern = new[] { 0, 85, 170 }[p]; var s = seq[p]; P28LimiterScenario.Shape(s, "scratchPattern", "machineInstances", "checkpoints");
            Require(N(s, "scratchPattern") == pattern && N(s, "machineInstances") == 1 && s.GetProperty("checkpoints").GetArrayLength() == scenario.Calls.Count, "Second machine or missing event.");
            var r = Row(p, i); P28LimiterScenario.Shape(r, "index", "machineId", "prefix", "consumer", "disposition", "provenance", "producerGeneration0196", "readerGeneration0196", "abiWrites", "after", "stateBefore", "stateAfter", "continuityJournal", "canaries");
            Require(N(r, "index") == i && N(r, "machineId") == 1 && Equal(r.GetProperty("canaries"), JsonSerializer.SerializeToElement(new[] { pattern, pattern, pattern })), "Index/machine/canary mismatch.");
            var ownState = JsonSerializer.SerializeToElement(new { byte0128 = (pattern & ~4) | (scenario.InitialState.Bit0128_2 ? 4 : 0), byte0117 = (int)scenario.InitialState.Byte0117 });
            Require(Equal(r.GetProperty("stateBefore"), ownState) && Equal(r.GetProperty("stateAfter"), ownState), "Hidden source reseed or owner overlap.");
            var consumer = r.GetProperty("consumer"); var disposition = ownPrefix.Disposition == "NotRun" ? "NotRun" : "NoFresh0196"; var provenance = "NoFresh0196"; P28QuartetGeneration? reader = null; int? value = null, er1 = null;
            var actualNative = Array.Empty<int[]>();
            if (ownPrefix.ResultGeneration is { } g)
            {
                Require(consumer.ValueKind == JsonValueKind.Object && Equal(r.GetProperty("abiWrites"), JsonSerializer.SerializeToElement(new[] { new[] { 0, 0x5ED, 0x54F5 } })), "Missing consumer or hidden A/pointer/PSW/frame seed.");
                provenance = ownPrefix.SelectedGeneration is null ? "ConsumerGateBypass0196" : "QuartetDerived0196";
                var own = P28Word0196HandoffModel.Build(g.Value, N(ownPrefix.Actual.GetProperty("after"), "psw"), (byte)N(ownState, "byte0128"), scenario.InitialState.Byte0117);
                actualNative = ValidateConsumer(consumer, ownPrefix.Actual.GetProperty("after"), own, registers);
                if (actualNative.Any(a => a[0] == 0x54FA)) { reader = g; value = g.Value; }
                if (actualNative.Any(a => a[0] == 0x54FC)) er1 = g.Value;
                var status = N(consumer.GetProperty("stage").GetProperty("result"), "status");
                disposition = status == 0 && reader is not null ? provenance == "QuartetDerived0196" ? "QuartetDerived0196ConsumerStrict" : "GateBypass0196ConsumerStrict" : status switch { 3 => "BudgetExceeded", 2 => "ExecutionError", _ => "0196ConsumerPartial" };
            }
            else Require(consumer.ValueKind == JsonValueKind.Null && r.GetProperty("abiWrites").GetArrayLength() == 0, "Consumer ran without fresh current0196.");
            Require(r.GetProperty("disposition").GetString() == disposition && r.GetProperty("provenance").GetString() == provenance, "False strict/gate provenance classification.");
            Require(Equal(r.GetProperty("producerGeneration0196"), JsonSerializer.SerializeToElement(ownPrefix.ResultGeneration, JsonDefaults.Create())) && Equal(r.GetProperty("readerGeneration0196"), JsonSerializer.SerializeToElement(reader, JsonDefaults.Create())), "Stale equal-value generation substituted.");
            ValidateJournal(r, ownPrefix.Actual.GetProperty("continuityJournal"), actualNative, ownPrefix.ResultGeneration, reader);
            var after = consumer.ValueKind == JsonValueKind.Object ? consumer.GetProperty("exit") : ownPrefix.Actual.GetProperty("after"); Require(Equal(r.GetProperty("after"), after), "Detached exit or NotRun mutation.");
            reports[p].Add(new(i, disposition, provenance, ownPrefix, ownPrefix.ResultGeneration, reader, value, er1, N(after, "pc"), r.Clone()));
        }));
        return Enumerable.Range(0, 3).Select(p => new P28Word0196HandoffSequence(id, new[] { 0, 85, 170 }[p], reports[p])).ToArray();
    }
    private static int N(JsonElement e, string k) => e.GetProperty(k).GetInt32();
    internal static int[][] ValidateConsumer(JsonElement suffix, JsonElement prefixExit, P28Word0196Oracle own, int[] registers, bool rawPrefix = false)
    {
        P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses"); var entry = suffix.GetProperty("entry"); var exit = suffix.GetProperty("exit"); P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        var expectedEntry = JsonNode.Parse(prefixExit.GetRawText())!; expectedEntry["pc"] = 0x54F5;
        Require(N(prefixExit, "pc") == 0x5ED && Equal(entry, JsonSerializer.SerializeToElement(expectedEntry)) && entry.GetProperty("registers").EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(registers), "PC-only retained entry violated;fake frame or seed.");
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter"); var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 6, 0, [], null)!;
        var events = Matrix(stage.GetProperty("events"), 8, 6); Require(events.Length == result.Steps && events.Length <= own.Events.Count && events.Select(a => string.Join(',', a)).SequenceEqual(own.Events.Take(events.Length).Select(a => string.Join(',', a))), "Wrong software instruction/compare/flags/branch.");
        Require(result.Trace.Count == events.Length, "Missing mandatory trace."); for (var n = 0; n < events.Length; n++) Require(N(result.Trace[n], "pc") == events[n][0] && N(result.Trace[n], "nextPc") == events[n][1] && N(result.Trace[n], "accumulator") == events[n][3] && N(result.Trace[n], "psw") == events[n][5], "Detached trace.");
        var count = events.Length == 0 ? 0 : own.AccessEnds[events.Length - 1]; var accesses = own.Accesses.Take(count).ToArray();
        Require(Equal(suffix.GetProperty("accesses"), JsonSerializer.SerializeToElement(accesses)) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(accesses.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray())), "Wrong0196width/value/address or hardware/P2 access.");
        var stop = events.Length == 0 ? 0x54F5 : events[^1][1]; Require(result.StopPc == stop && (result.Status != 0 || (rawPrefix || stop == 0x5503) && events.Length == own.Events.Count) && (rawPrefix || stop is not (0x5533 or 0x556F) || result.Status == 1), "Partial/pure alternate claimed hardware boundary.");
        Require(result.UsedAssumptions.Count == 0 && result.ProgramReads.Count == 0 && result.ExecutedInstructionBytes.SequenceEqual(own.Events.Take(events.Length).SelectMany((e, n) => Enumerable.Range(e[0], own.Lengths[n])).Distinct().Order()), "Unadmitted extra code/assumption/peripheral.");
        foreach (var a in accesses.Where(a => a[3] == 1)) for (var b = 0; b < a[2] / 8; b++) registers[a[1] + b - 0x108] = (a[4] >> (8 * b)) & 255;
        var expectedExit = expectedEntry.DeepClone(); expectedExit["pc"] = stop; expectedExit["accumulator"] = events.Length == 0 ? own.Events[0][2] : events[^1][3]; var psw = events.Length == 0 ? own.Events[0][4] : events[^1][5]; expectedExit["psw"] = psw; expectedExit["dd"] = (psw & 0x1000) != 0; expectedExit["registers"] = JsonSerializer.SerializeToNode(registers);
        Require(Equal(exit, JsonSerializer.SerializeToElement(expectedExit)) && N(stage, "sspAfter") == N(entry, "ssp"), "Native software carrier/register/stack continuity forged."); return accesses;
    }
    internal static void ValidateJournal(JsonElement row, JsonElement prefixJournal, int[][] consumerNative, P28QuartetGeneration? producer, P28QuartetGeneration? reader)
    {
        Require(N(row, "machineId") == 1, "Second machine."); var prior = Matrix(prefixJournal, 6, 32768); var actual = Matrix(row.GetProperty("continuityJournal"), 6, 32768);
        var expected = prior.Concat(consumerNative.Select(a => new[] { 1 }.Concat(a).ToArray())).ToArray(); Require(Equal(JsonSerializer.SerializeToElement(actual), JsonSerializer.SerializeToElement(expected)), "Hidden host copy/reseed/overlap/timer access or reordered journal.");
        if (reader is null) return; Require(producer == reader && reader.EventIndex == N(row, "index"), "Stale generation.");
        ValidateGeneration(actual, reader, N(row, "index"), 0x196, 0x54FA);
    }
    internal static void ValidateGeneration(int[][] journal, P28QuartetGeneration g, int index, int address, int readerPc)
    {
        Require(g.EventIndex == index, "Stale generation event."); var w = Array.FindIndex(journal, a => a.SequenceEqual(new[] { 1, g.WriterPc, address, 16, 1, g.Value })); var reads = journal.Select((a, n) => (a, n)).Where(t => t.a[0] == 1 && t.a[1] == readerPc).ToArray();
        Require(w >= 0 && reads.Length == 1 && reads[0].n > w && reads[0].a.SequenceEqual(new[] { 1, readerPc, address, 16, 0, g.Value }), "Wrong native writer/reader/width/address/value.");
        Require(journal.Take(w).Count(a => a[0] == 1 && a[4] == 1) == g.WriteOrder && !journal.Skip(w + 1).Take(reads[0].n - w - 1).Any(a => a[4] == 1 && a[2] < address + 2 && a[2] + a[3] / 8 > address), "Native generation ordinal/overlap invalid.");
    }
}
