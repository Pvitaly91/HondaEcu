using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28Data0136HandoffCheckpoint(int Index, string Validation, string Disposition, string ProducerDisposition,
    int? ProducerWriterPc, P28Data0136Generation? ProducerGeneration, int? ProducerValue, string ScheduleClassification,
    int Writes0136BetweenStages, int? Reader2330Value, P28Data0136Generation? ReaderGeneration, int? Er2Value,
    int? DivisorReadValue, string CalculationDisposition, int FinalStop, JsonElement Actual);
public sealed record P28Data0136HandoffSequence(int ScratchPattern, IReadOnlyList<P28Data0136HandoffCheckpoint> Checkpoints);
public sealed record P28Data0136HandoffReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, IReadOnlyList<P28Data0136HandoffSequence> Sequences, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Validation is not ("StrictMatch" or "StrictNoFreshGeneration"));
    public string TechnicalScheduledHandoff => HasFailure || !Sequences.SelectMany(s => s.Checkpoints).Any(c => c.ReaderGeneration is not null) ? "Partial" : "Validated";
    public string RecoveredEcuScheduler => "NotEstablished";
    public string ProducerTo2330SchedulerSeam => "HarnessScheduled / NotRecovered";
    public string InterStageScheduling => "ExplicitHarnessSchedule";
    public string SkippedCode => "NotExecuted";
    public string MainLoopRecovery => "NotEstablished";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string M2tJgt => "Blocked/Unresolved";
    public string StrictCalculationCompletion => "NotEstablished;PositiveJgtBlocked;ZeroDivisorUnresolved";
    public string QuartetConsumer => "NotRun";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string Acceptance => "strict M2i Blocked;GUI r3 paused/NotRun;D1/D2 interactive acceptance NotRun;hardware/full boot NotRun";
    public string FirmwareOutput => "BIN0;bindings0;compensation0;export plans/receipts/tokens0";
    public object Summary => new
    {
        Mode0Handoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.ReaderGeneration?.WriterPc == 0x5707),
        Mode1Handoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.ReaderGeneration?.WriterPc == 0x56F3),
        PositiveHandoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "NativeProducerPositiveToJgtBlock"),
        ZeroHandoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "NativeProducerZeroToDivBoundary"),
        SameValueNewGenerations = Sequences.Sum(s => s.Checkpoints.Zip(s.Checkpoints.Skip(1)).Count(pair => pair.First.ReaderGeneration is not null && pair.Second.ReaderGeneration is not null && pair.First.ProducerValue == pair.Second.ProducerValue && pair.First.ProducerGeneration != pair.Second.ProducerGeneration)),
        Intermediate0136Writers = Sequences.SelectMany(s => s.Checkpoints).Sum(c => c.Writes0136BetweenStages),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        FirmwareAb = 0,
        ModelOnlyNativeCoverage = 0
    };
}

public static class P28Data0136HandoffValidator
{
    public const string Operation = "data0136DivisionHandoff";
    public static object CreateRequest(RomImage image, P28Data0136HandoffScenario s)
    {
        var historical = JsonSerializer.SerializeToElement(P28PostSelectionCriticalValidator.CreateRequest(image, s.ModelScenario(0).PrefixScenario), JsonDefaults.Create());
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
            scratchPatterns = new[] { 0, 85, 170 },
            allowAssumptions = Array.Empty<string>(),
            data0136DivisionHandoff = new
            {
                s.FormatVersion,
                unifiedInitialState = new
                {
                    s.UnifiedInitialState.Producer,
                    s.UnifiedInitialState.Data011f,
                    fuelPrefix = historical.GetProperty("fuelPostSelectionCriticalChain").GetProperty("initialState"),
                    s.UnifiedInitialState.SoftwareSources
                },
                s.ProducerObservations,
                s.FuelCalls,
                s.TraceEventIndexes
            }
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[]{new {
        id=Operation,formatVersion=1,producerContract=P28Data0136TechnicalProducerValidator.ExpectedContracts()[0],
        fuelPrefixContract=P28PostSelectionCriticalValidator.ExpectedContracts()[0],calculationContract=P28CommonResultConsumerValidator.ExpectedContracts()[0],
        initialization="OnceBeforeSequence;0136CanaryFromScratch;OneAuthoritative011FByte",state="OneCpuBusPerSequence;NoSerializationHandoff",
        pairing="ProducerObservation[N]->FreshNativeGeneration->FuelCall[N]",interStageScheduling="ExplicitHarnessSchedule",skippedCode="NotExecuted",mainLoopRecovery="NotEstablished",
        producerTo2330SchedulerSeam="HarnessScheduled / NotRecovered",recoveredEcuScheduler="NotEstablished",positiveStopBefore=0x233A,zeroStopBefore=0x2333,
        generation="writerPC,eventIndex,writeOrder,value",continuityJournal="native,pc,address,width,write,value;hostPc65536;CPU_ABI_fields_in_nested_boundaries",
        noFreshGeneration="DownstreamNotRun;ContinueIfProducerComplete",partial="Terminal;RetainCompletedStores",handoffBoundary="MayContinueNextEvent;NotStrictCalculationCompletion",
        canaryAddresses=new[]{0x300,0x350,0x3E0},irqDelivery="NotInjected",elapsedTime="None",quartetConsumer="NotRun",physicalRpmAvailable=false
    }});
    public static async Task<P28Data0136HandoffReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28Data0136HandoffScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "M2w requires unchanged original configuration.");
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(original, scenario), options, cancellationToken).ConfigureAwait(false);
        try { return Analyze(original, profile.Id, scenario, response.Response); }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2w same-machine evidence.", e); }
    }
    internal static P28Data0136HandoffReport Analyze(RomImage image, string profile, P28Data0136HandoffScenario scenario, JsonElement root)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "data0136HandoffSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2w contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign M2w rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic output.");
        var seq = root.GetProperty("data0136HandoffSequences"); Require(seq.GetArrayLength() == 3, "Exactly3 scratch histories required.");
        var fuelOwn = new P28CommonResultConsumerOwn?[3, scenario.FuelCalls.Count]; var models = new P28CommonResultConsumerHistory[3];
        for (var p = 0; p < 3; p++) { models[p] = new(image, scenario.ModelScenario(new[] { 0, 85, 170 }[p]), new[] { 0, 85, 170 }[p]); models[p].AcceptModeledProducerGeneration((ushort)(new[] { 0, 85, 170 }[p] * 257), scenario.UnifiedInitialState.Data011f); }
        JsonElement Row(int p, int i) => seq[p].GetProperty("checkpoints")[i];
        bool FuelTerminal(int p, int i) { var r = Row(p, i); var f = r.GetProperty("fuelPrefix"); var c = r.GetProperty("calculation"); return f.ValueKind == JsonValueKind.Object && (f.GetProperty("status").GetInt32() != 0 || c.ValueKind != JsonValueKind.Object || c.GetProperty("stage").GetProperty("result").GetProperty("stopPc").GetInt32() is not (0x233A or 0x2333)); }
        void AdvanceFuel(int p, int i, P28Data0136TechnicalProducerModel producer)
        {
            var r = Row(p, i); if (r.GetProperty("fuelPrefix").ValueKind != JsonValueKind.Object) return;
            models[p].AcceptModeledProducerGeneration((ushort)producer.Word(0x136), scenario.UnifiedInitialState.Data011f);
            var own = models[p].Step(scenario.FuelCalls[i]); fuelOwn[p, i] = own;
            var c = r.GetProperty("calculation"); if (c.ValueKind == JsonValueKind.Object)
            {
                var steps = c.GetProperty("stage").GetProperty("result").GetProperty("steps").GetInt32();
                Require(steps >= 0 && steps <= own.Oracle.Machine.Events.Count, "Calculation extends past independently modeled boundary.");
                producer.AcceptModeledAccumulator(steps == 0 ? own.Oracle.Machine.Events[0][2] : own.Oracle.Machine.Events[steps - 1][3]);
            }
        }
        var producerModels = new P28Data0136TechnicalProducerModel[3];
        var producerView = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = P28Data0136TechnicalProducerValidator.Operation,
            runnerVersion = root.GetProperty("runnerVersion"),
            upstreamCommit = root.GetProperty("upstreamCommit"),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            entryContracts = P28Data0136TechnicalProducerValidator.ExpectedContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            data0136Sequences = seq.EnumerateArray().Select(s => new
            {
                imageIndex = 0,
                scratchPattern = s.GetProperty("scratchPattern"),
                completedObservations = s.GetProperty("checkpoints").EnumerateArray().Count(c => c.GetProperty("producer").ValueKind == JsonValueKind.Object && c.GetProperty("producer").GetProperty("result").GetProperty("status").GetInt32() == 0),
                checkpoints = s.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("producer").ValueKind == JsonValueKind.Object ? c.GetProperty("producer") : JsonSerializer.SerializeToElement(new
                {
                    index = c.GetProperty("index"),
                    result = (object?)null,
                    sourceApplications = Array.Empty<int>(),
                    entry = (object?)null,
                    exit = (object?)null,
                    ramBefore = c.GetProperty("producerRamAfterSchedule"),
                    ramAfter = c.GetProperty("producerRamAfterSchedule"),
                    events = Array.Empty<int>(),
                    accesses = Array.Empty<int>(),
                    writes = Array.Empty<int>(),
                    peripheralAccesses = Array.Empty<int>()
                })).ToArray()
            }).ToArray()
        });
        var technical = P28Data0136TechnicalProducerScenario.Create(P28Data0136HandoffScenario.TechnicalInitial(scenario.UnifiedInitialState, 0), scenario.ProducerObservations, scenario.Provenance);
        var producers = P28Data0136TechnicalProducerValidator.Analyze(image, profile, technical, producerView,
            p => producerModels[p] = new(P28Data0136HandoffScenario.TechnicalInitial(scenario.UnifiedInitialState, new[] { 0, 85, 170 }[p]), new[] { 0, 85, 170 }[p]),
            (p, i, m) => { if (i > 0) AdvanceFuel(p, i - 1, m); }, FuelTerminal);
        for (var p = 0; p < 3; p++) AdvanceFuel(p, scenario.FuelCalls.Count - 1, producerModels[p]);
        var active = Enumerable.Range(0, scenario.FuelCalls.Count).Where(i => Row(0, i).GetProperty("fuelPrefix").ValueKind == JsonValueKind.Object).ToArray();
        for (var p = 0; p < 3; p++) Require(active.SequenceEqual(Enumerable.Range(0, scenario.FuelCalls.Count).Where(i => Row(p, i).GetProperty("fuelPrefix").ValueKind == JsonValueKind.Object)), "Scratch schedules differ.");
        IReadOnlyList<P28PostSelectionCriticalSequence>? prefixes = null;
        if (active.Length > 0)
        {
            var calls = active.Select((i, n) => scenario.FuelCalls[i] with { Adaptive = scenario.FuelCalls[i].Adaptive with { Fuel = scenario.FuelCalls[i].Adaptive.Fuel with { Index = n } } }).ToArray();
            var prefixScenario = P28PostSelectionCriticalScenario.Create(scenario.UnifiedInitialState.FuelPrefix, calls, scenario.Provenance);
            var prefixView = JsonSerializer.SerializeToElement(new
            {
                runnerVersion = root.GetProperty("runnerVersion"),
                upstreamCommit = root.GetProperty("upstreamCommit"),
                localSemanticFixes = root.GetProperty("localSemanticFixes"),
                criticalSequences = Enumerable.Range(0, 3).Select(p => new { scratchPattern = new[] { 0, 85, 170 }[p], checkpoints = active.Select((i, n) => Reindex(Row(p, i).GetProperty("fuelPrefix"), n)).ToArray() }).ToArray()
            });
            prefixes = P28PostSelectionCriticalValidator.AnalyzeEvidence(image, prefixScenario, prefixView, "Original",
                (p, n) => FuelTerminal(p, active[n]), (p, n) => fuelOwn[p, active[n]]!.Before.Mode012b, (byte)(scenario.UnifiedInitialState.SoftwareSources.Word011aMask1034 >> 8),
                (p, n, before) => Require(Equal(before, Row(p, active[n]).GetProperty("producer").GetProperty("exit")), "Producer->first fuel ABI seam changed CPU before its disclosed transition."), true);
        }
        var reports = new List<P28Data0136HandoffSequence>();
        for (var p = 0; p < 3; p++)
        {
            var pattern = new[] { 0, 85, 170 }[p]; var sequence = seq[p]; P28LimiterScenario.Shape(sequence, "scratchPattern", "machineInstances", "checkpoints");
            Require(sequence.GetProperty("scratchPattern").GetInt32() == pattern && sequence.GetProperty("machineInstances").GetInt32() == 1 && sequence.GetProperty("checkpoints").GetArrayLength() == scenario.FuelCalls.Count, "Second machine/missing events.");
            var list = new List<P28Data0136HandoffCheckpoint>(); JsonElement prior = default; var terminal = false;
            var scb1 = Enumerable.Repeat(pattern, 8).ToArray(); scb1[6] = 0x80; scb1[7] = 2;
            var initialOwn = new P28CommonResultConsumerHistory(image, scenario.ModelScenario(pattern), pattern); initialOwn.AcceptModeledProducerGeneration((ushort)(pattern * 257), scenario.UnifiedInitialState.Data011f);
            for (var i = 0; i < scenario.FuelCalls.Count; i++)
            {
                var r = Row(p, i); P28LimiterScenario.Shape(r, "index", "machineId", "producer", "fuelPrefix", "calculation", "producerGeneration", "consumerGeneration", "disposition", "before", "after", "stateBefore", "stateAtFuelEntry", "stateAtCalculationEntry", "stateAfter", "producerRamAfterSchedule", "continuityJournal", "canaries");
                Require(r.GetProperty("index").GetInt32() == i && r.GetProperty("machineId").GetInt32() == 1, "Wrong event/machine identity.");
                Require(Numbers(r.GetProperty("canaries")).SequenceEqual(new[] { pattern, pattern, pattern }), "Persistent canaries reseeded.");
                var before = r.GetProperty("stateBefore"); var after = r.GetProperty("stateAfter");
                if (i == 0) Require(Equal(before, JsonSerializer.SerializeToElement(initialOwn.ModeledState, JsonDefaults.Create())), "Unified initial RAM differs from independent model.");
                else Require(Equal(before, prior.GetProperty("stateAfter")) && Equal(r.GetProperty("before"), prior.GetProperty("after")), "CPU/RAM reset between events.");
                Require(before.GetProperty("byte011f").GetInt32() == scenario.UnifiedInitialState.Data011f && after.GetProperty("byte011f").GetInt32() == scenario.UnifiedInitialState.Data011f, "011F mode/source neighbors changed.");
                var prod = producers.Sequences[p].Checkpoints[i]; var f = r.GetProperty("fuelPrefix"); var calc = r.GetProperty("calculation"); var expectedGeneration = prod.Writer?.Generation;
                if (f.ValueKind == JsonValueKind.Object)
                {
                    var adaptive = f.GetProperty("prefix").GetProperty("prefix").GetProperty("prefix"); var ticks = adaptive.GetProperty("ticks");
                    var first = ticks.GetArrayLength() > 0 ? ticks[0] : adaptive.GetProperty("producer");
                    if (first.ValueKind == JsonValueKind.Object)
                    {
                        var entry = first.GetProperty("entry"); var target = first.GetProperty("tickTarget");
                        Require(entry.GetProperty("x1").GetInt32() == (target.ValueKind == JsonValueKind.Number ? target.GetInt32() : scb1[0] | scb1[1] << 8) &&
                            entry.GetProperty("x2").GetInt32() == (scb1[2] | scb1[3] << 8) && entry.GetProperty("dp").GetInt32() == (scb1[4] | scb1[5] << 8), "SCB1 pointer storage reset/copied during disclosed SCB2->SCB1 selection.");
                    }
                }
                Require(Equal(r.GetProperty("producerGeneration"), JsonSerializer.SerializeToElement(expectedGeneration, JsonDefaults.Create())), "Forged producer generation.");
                string disposition; string validation; string calculation; int? readValue = null; int? er2 = null; int? divisor = null; P28Data0136Generation? consumed = null;
                if (terminal) { Require(prod.Disposition == "NotRun" && f.ValueKind == JsonValueKind.Null && calc.ValueKind == JsonValueKind.Null && Equal(before, after) && Equal(r.GetProperty("before"), r.GetProperty("after")), "Execution/initializer after terminal."); disposition = "NotRun"; validation = "NotRun"; calculation = "NotRun"; }
                else if (prod.Validation != "StrictMatch") { Require(f.ValueKind == JsonValueKind.Null && calc.ValueKind == JsonValueKind.Null, "Fuel executed after partial producer."); disposition = "ProducerPartial"; validation = "Partial"; calculation = "NotRun"; terminal = true; }
                else if (expectedGeneration is null) { Require(f.ValueKind == JsonValueKind.Null && calc.ValueKind == JsonValueKind.Null && Equal(before, after), "No-writer event ran consumer or changed fuel RAM."); disposition = "NoFreshProducerGeneration"; validation = "StrictNoFreshGeneration"; calculation = "DownstreamNotRun"; }
                else
                {
                    var own = fuelOwn[p, i]!; Require(f.ValueKind == JsonValueKind.Object, "Fresh generation lacks declared fuel call.");
                    Require(Equal(r.GetProperty("stateAtFuelEntry"), JsonSerializer.SerializeToElement(own.Before, JsonDefaults.Create())), "Producer generation not current at fuel entry.");
                    Require(Equal(before.GetProperty("prefix"), f.GetProperty("stateBefore")) && Equal(after.GetProperty("prefix"), f.GetProperty("stateAfter")), "Fuel state split/reseeded.");
                    var prefix = prefixes![p].Checkpoints[Array.IndexOf(active, i)];
                    if (prefix.Disposition != "StrictMatch")
                    {
                        Require(calc.ValueKind == JsonValueKind.Null, "Calculation after partial prefix.");
                        P28CommonResultConsumerValidator.RequireStateSources(after, own.Before with { Mode012b = P28CommonResultConsumerValidator.PrefixModeAfterPartial(f, own.Before.Mode012b, scenario.FuelCalls[i]), Word011a = (ushort)((own.Before.Word011a & ~0x8000) | (scenario.FuelCalls[i].Adaptive.FixedSource ? 0x8000 : 0)) });
                        disposition = "FuelPrefixPartial"; validation = "Partial"; calculation = "NotRun"; terminal = true;
                    }
                    else
                    {
                        Require(Equal(r.GetProperty("stateAtCalculationEntry"), JsonSerializer.SerializeToElement(own.Entry, JsonDefaults.Create())), "Generation/source/03B4 overwritten before calculation.");
                        var native = P28CommonResultConsumerValidator.ValidateSuffix(calc, f.GetProperty("critical").GetProperty("exit"), own.Oracle);
                        var retained = own.Entry with { Mode012b = (byte)(native.Steps == 0 ? own.Entry.Mode012b : own.Oracle.ModeEnds[native.Steps - 1]), Byte013b = (byte)(native.Steps == 0 ? own.Entry.Byte013b : own.Oracle.HistoryEnds[native.Steps - 1][0]), Byte013d = (byte)(native.Steps == 0 ? own.Entry.Byte013d : own.Oracle.HistoryEnds[native.Steps - 1][1]) };
                        Require(Equal(after, JsonSerializer.SerializeToElement(retained, JsonDefaults.Create())), "Final native state differs.");
                        if (native.StopPc == 0x233A || native.StopPc == 0x2333)
                        {
                            var a = Matrix(calc.GetProperty("accesses"), 5, 4096); readValue = One(a, 0x2330, 0x136, 16, 0); er2 = One(a, 0x2330, 0x104, 16, 1);
                            Require(readValue == expectedGeneration.Value && er2 == readValue, "2330 failed same-generation word transfer.");
                            if (expectedGeneration.Value > 0) { divisor = One(a, 0x2333, 0x104, 16, 0); Require(divisor == readValue && native.StopPc == 0x233A, "Injected divisor or positive stop differs."); disposition = "NativeProducerPositiveToJgtBlock"; calculation = "PositiveDivCmp;JgtBlocked/Unresolved"; }
                            else { Require(native.StopPc == 0x2333 && !a.Any(x => x[0] == 0x2333), "Zero DIV executed."); disposition = "NativeProducerZeroToDivBoundary"; calculation = "ZeroDivisorUnresolved;DIVNotRun"; }
                            consumed = expectedGeneration; validation = "StrictMatch";
                        }
                        else { disposition = native.Status == 0 ? "CalculationBypassNotHandoff" : "ExecutionError"; validation = "Partial"; calculation = disposition; terminal = true; }
                    }
                }
                Require(r.GetProperty("disposition").GetString() == disposition, "Wrong handoff disposition.");
                Require(Equal(r.GetProperty("consumerGeneration"), JsonSerializer.SerializeToElement(consumed, JsonDefaults.Create())), "Stale same-value consumer generation.");
                if (prod.Actual.GetProperty("exit").ValueKind == JsonValueKind.Object)
                {
                    Require(Equal(r.GetProperty("producerRamAfterSchedule"), prod.Actual.GetProperty("ramAfter")), "Fuel initializer changed producer RAM/history.");
                    Require(Equal(r.GetProperty("before"), i == 0 ? r.GetProperty("producer").GetProperty("entry") : prior.GetProperty("after")), "Initial technical ABI differs.");
                    Require(Equal(r.GetProperty("after"), calc.ValueKind == JsonValueKind.Object ? calc.GetProperty("exit") : f.ValueKind == JsonValueKind.Object ? LastFuelBoundary(f) : r.GetProperty("producer").GetProperty("exit")), "Final CPU boundary detached from actual execution.");
                }
                ValidateContinuity(r, expectedGeneration, consumed, scenario.ProducerObservations[i], terminal && prod.Disposition == "NotRun");
                foreach (var a in Matrix(r.GetProperty("continuityJournal"), 6, 32768).Where(a => a[4] == 1)) for (var b = 0; b < a[3] / 8; b++) if (a[2] + b is >= 0x88 and < 0x90) scb1[a[2] + b - 0x88] = (a[5] >> (8 * b)) & 255;
                if (f.ValueKind == JsonValueKind.Null) Require(r.GetProperty("stateAtFuelEntry").ValueKind == JsonValueKind.Null && r.GetProperty("stateAtCalculationEntry").ValueKind == JsonValueKind.Null, "NotRun fabricated stage entry.");
                else if (calc.ValueKind == JsonValueKind.Null) Require(r.GetProperty("stateAtCalculationEntry").ValueKind == JsonValueKind.Null, "Partial prefix fabricated calculation entry.");
                list.Add(new(i, validation, disposition, prod.Disposition, prod.Writer?.WriterPc, expectedGeneration, prod.Writer?.NewValue, "HarnessScheduledSameCpuRam", 0, readValue, consumed, er2, divisor, calculation, r.GetProperty("after").GetProperty("pc").GetInt32(), r.Clone())); prior = r;
            }
            reports.Add(new(pattern, list.AsReadOnly()));
        }
        return new(1, scenario.Purpose, image.Hash, profile, scenario.Digest, root.GetProperty("runnerVersion").GetString()!, reports.AsReadOnly(), root.GetProperty("entryContracts").Clone());
    }
    private static int[] Numbers(JsonElement e) => e.EnumerateArray().Select(v => v.GetInt32()).ToArray();
    private static int One(int[][] a, int pc, int address, int width, int write) { var rows = a.Where(x => x[0] == pc && x[1] == address && x[2] == width && x[3] == write).ToArray(); Require(rows.Length == 1, "Missing/duplicate word provenance."); return rows[0][4]; }
    private static JsonElement Reindex(JsonElement e, int index) { var n = JsonNode.Parse(e.GetRawText())!; void Visit(JsonNode? v) { if (v is JsonObject o) { foreach (var item in o.ToArray()) { if (item.Key == "index") o[item.Key] = index; else Visit(item.Value); } } else if (v is JsonArray a) foreach (var c in a) Visit(c); } Visit(n); return JsonSerializer.SerializeToElement(n); }
    private static JsonElement LastFuelBoundary(JsonElement f)
    {
        foreach (var key in new[] { "critical", "consumer", "suffix" }) if (f.TryGetProperty(key, out var s) && s.ValueKind == JsonValueKind.Object) return s.GetProperty("exit");
        if (f.TryGetProperty("prefix", out var p)) return LastFuelBoundary(p);
        if (f.TryGetProperty("joint", out var j)) { var fuel = j.GetProperty("fuel"); if (fuel.GetProperty("status").GetInt32() != 4) { var boundaries = fuel.GetProperty("boundaries"); if (boundaries.GetArrayLength() > 0) return boundaries[boundaries.GetArrayLength() - 1]; if (fuel.GetProperty("factorExit").ValueKind == JsonValueKind.Object) return fuel.GetProperty("factorExit"); var tails = fuel.GetProperty("tailBoundaries"); if (tails.GetArrayLength() > 0) return tails[tails.GetArrayLength() - 1]; } if (j.GetProperty("decisionExit").ValueKind == JsonValueKind.Object) return j.GetProperty("decisionExit"); }
        if (f.TryGetProperty("producer", out var prod) && prod.ValueKind == JsonValueKind.Object) return prod.GetProperty("exit");
        var ticks = f.GetProperty("ticks"); return ticks[ticks.GetArrayLength() - 1].GetProperty("exit");
    }
    internal static void ValidateContinuity(JsonElement r, P28Data0136Generation? generation, P28Data0136Generation? consumed, P28Data0136TechnicalObservation observation, bool notRun)
    {
        var journal = Matrix(r.GetProperty("continuityJournal"), 6, 32768); var expectedNative = new List<int[]>(); var expectedHost = new List<int[]>();
        Require(r.GetProperty("machineId").GetInt32() == 1, "Second Cpu/Bus.");
        Require(!journal.Any(j => j[0] == 1 && j[1] == 0x233A), "Positive JGT executed past strict blocker.");
        if (generation is not null)
        {
            Require(generation.EventIndex == r.GetProperty("index").GetInt32(), "Stale event generation.");
            if (generation.Value == 0) Require(!journal.Any(j => j[0] == 1 && j[1] == 0x2333), "Zero DIV executed.");
        }
        // Concatenate executed leaves in schedule order, never JSON property order or a sorted multiset.
        void Accesses(JsonElement node)
        {
            if (node.ValueKind != JsonValueKind.Object) return;
            if (node.TryGetProperty("accesses", out var ledger)) { expectedNative.AddRange(Matrix(ledger, 5, 8192)); return; }
            if (node.TryGetProperty("ticks", out var ticks))
            {
                foreach (var tick in ticks.EnumerateArray()) Accesses(tick);
                Accesses(node.GetProperty("producer")); Accesses(node.GetProperty("joint")); return;
            }
            if (node.TryGetProperty("decisionAccesses", out ledger)) { expectedNative.AddRange(Matrix(ledger, 5, 8192)); Accesses(node.GetProperty("fuel")); return; }
            if (node.TryGetProperty("prefix", out var prefix)) Accesses(prefix);
            foreach (var key in new[] { "suffix", "consumer", "critical" }) if (node.TryGetProperty(key, out var stage)) Accesses(stage);
        }
        void Host(JsonElement node)
        {
            if (node.ValueKind == JsonValueKind.Object) foreach (var item in node.EnumerateObject())
                {
                    if (item.Name == "inputWrites" && node.TryGetProperty("factorStage", out _)) continue; // Joint ledger already includes these same source applications.
                    if (item.Name is "snapshotWrites" or "inputWrites" or "transitionWrites" or "transitionToDecisionWrites" or "transitionToFactorWrites" or "transitionToAdditiveWrites") expectedHost.AddRange(Matrix(item.Value, 3, 512).Where(w => w[0] >= 0x80));
                    else if (item.Name == "prefixTransitions" && item.Value.ValueKind == JsonValueKind.Array) foreach (var t in item.Value.EnumerateArray()) expectedHost.AddRange(Matrix(t.GetProperty("writes"), 3, 32).Where(w => w[0] >= 0x80)); else Host(item.Value);
                }
            else if (node.ValueKind == JsonValueKind.Array) foreach (var c in node.EnumerateArray()) Host(c);
        }
        var prod = r.GetProperty("producer"); if (prod.ValueKind == JsonValueKind.Object) { Accesses(prod); expectedHost.Add([0x96, 16, 0x280]); expectedHost.Add([0xA2, 8, observation.Slot]); if (observation.Source00f0.HasValue) expectedHost.Add([0xF0, 16, observation.Source00f0.Value]); }
        var fuel = r.GetProperty("fuelPrefix"); if (fuel.ValueKind == JsonValueKind.Object) { Accesses(fuel); Host(fuel); }
        var calc = r.GetProperty("calculation"); if (calc.ValueKind == JsonValueKind.Object) Accesses(calc);
        // Nested native ledgers are independently checked first. Global chronology cannot drop an access.
        Require(journal.All(j => j[0] is 0 or 1 && j[3] is 8 or 16 && j[4] is 0 or 1) &&
            journal.Where(j => j[0] == 1).Select(j => string.Join(',', j.Skip(1))).SequenceEqual(expectedNative.Select(a => string.Join(',', a))), "Missing/foreign/reordered global native access journal.");
        Require(journal.Where(j => j[0] == 0).All(j => j[1] == 65536 && j[4] == 1) && journal.Where(j => j[0] == 0).Select(j => string.Join(',', new[] { j[2], j[3], j[5] })).Order().SequenceEqual(expectedHost.Select(w => string.Join(',', w)).Order()), "Hidden RAM initializer/host setter or missing ABI journal.");
        Require(!journal.Any(j => j[4] == 1 && j[2] < 0x120 && j[2] + j[3] / 8 > 0x11F), "Full-byte011F rewrite/mode change.");
        if (notRun) Require(journal.Length == 0, "NotRun performed accesses.");
        if (generation is not null)
        {
            var w = Array.FindIndex(journal, j => j[0] == 1 && j[1] == generation.WriterPc && j[2] == 0x136 && j[3] == 16 && j[4] == 1 && j[5] == generation.Value); Require(w >= 0, "Producer writer missing from continuity journal.");
            var read = Array.FindIndex(journal, j => j[0] == 1 && j[1] == 0x2330 && j[2] == 0x136 && j[3] == 16 && j[4] == 0);
            var end = read >= 0 ? read : journal.Length;
            Require(!journal.Skip(w + 1).Take(end - w - 1).Any(j => j[4] == 1 && j[2] < 0x138 && j[2] + j[3] / 8 > 0x136), "Generation overwritten by native/host0136/0137 writer.");
            if (consumed is not null)
            {
                Require(read > w && journal[read][5] == generation.Value && consumed == generation, "Stale or split-machine consumer generation.");
                var er2 = Array.FindIndex(journal, read + 1, j => j[0] == 1 && j[1] == 0x2330 && j[2] == 0x104 && j[3] == 16 && j[4] == 1 && j[5] == generation.Value); Require(er2 == read + 1, "Missing word er2 transfer.");
                if (generation.Value > 0) { var div = Array.FindIndex(journal, er2 + 1, j => j[0] == 1 && j[1] == 0x2333 && j[2] == 0x104 && j[3] == 16 && j[4] == 0 && j[5] == generation.Value); Require(div > er2 && !journal.Skip(er2 + 1).Take(div - er2 - 1).Any(j => j[4] == 1 && j[2] < 0x106 && j[2] + j[3] / 8 > 0x104), "er2 overwritten/injected before DIV."); }
            }
        }
    }
}
