using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28PostStoreConsumerCheckpoint(int Index, string Disposition, string PrefixDisposition, int? Generation0150,
    string Provenance0150, P28PostStoreConsumerProjection? Expected, int? SelectedScaledWordX1, int? RetainedOrZeroA,
    P28PostStoreCheckpoint Prefix, JsonElement Actual)
{
    public string HelperDisposition
    {
        get
        {
            var consumer = Actual.GetProperty("consumer");
            if (consumer.ValueKind != JsonValueKind.Object) return "NotRun";
            var events = consumer.GetProperty("stage").GetProperty("events").EnumerateArray().ToArray();
            if (!events.Any(e => e[0].GetInt32() == 0x2251)) return Disposition == "StrictMatch" ? "NotRunZeroSelection" : "NotRunBeforeCall";
            return events.Any(e => e[0].GetInt32() == 0x59A5 && e[1].GetInt32() == 0x2254) ? "NativeReturned" : "PartialNativeCall";
        }
    }
}
public sealed record P28PostStoreConsumerSequence(string Image, int ScratchPattern, IReadOnlyList<P28PostStoreConsumerCheckpoint> Checkpoints);
public sealed record P28PostStoreConsumerComparison(int ScratchPattern, int Index, int? Word0150A, int? Word0150B,
    int? SelectedA, int? SelectedB, int? ResultX1A, int? ResultX1B, int? ResultAccumulatorA, int? ResultAccumulatorB,
    bool? PrefixGateDiverged, bool? ConsumerDiverged, bool? Controls, string Effect);
public sealed record P28PostStoreConsumerReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28PostStoreConsumerSequence> Sequences, IReadOnlyList<P28PostStoreConsumerComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        NativeTickInvocations = Sequences.SelectMany(s => s.Checkpoints).Sum(c => c.Prefix.Prefix.NativeTicks),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        Relations = Sequences.SelectMany(s => s.Checkpoints).Where(c => c.Expected is not null).GroupBy(c => c.Expected!.Comparison).ToDictionary(g => g.Key, g => g.Count()),
        NativeHelperInvocations = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch" && c.Expected!.HelperStatus == "NativeCall"),
        NumericalWitnesses = Comparisons.Count(c => c.ConsumerDiverged == true)
    };
    public string Scope => "Native2239 generation0150 ->223B/223D comparison ->selection/native5991 helper/return ->2254X1 and2255bit5 consumer; same CPU/RAM; stop-before2259 IRQ control. Earlier entries scripted, not ECU scheduler.";
    public string Configuration60f8 => "UnchangedZero;NotReachedBefore2259;226F/2273 bypass and227A StaticOnly/NotEvaluated";
    public string NearestStaticReaders => "2261 X1;2264/2266 A; after excluded2259 IE boundary";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; independent one-field B in memory; no BIN/export/compensation/binding/receipt/token";
}
public static class P28PostStoreConsumerValidator
{
    public const string Operation = "fuelPostStoreConsumerChain";
    public static object CreateRequest(RomImage image, P28PostStoreConsumerScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28PostStoreValidator.CreateRequest(image, scenario.PrefixScenario), JsonDefaults.Create());
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = old.GetProperty("images"),
            scratchPatterns = old.GetProperty("scratchPatterns"),
            allowAssumptions = Array.Empty<string>(),
            fuelPostStoreConsumerChain = old.GetProperty("fuelPostStoreChain")
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28PostStoreValidator.ExpectedContracts()[0],
        nativeContinuation = new[] { 0x223B, 0x2259 }, helperRange = new[] { 0x5991, 0x59A6 },
        nativeGeneration = new[] { 0x2239, 0x150, 16 }, comparison = new[] { 0x223D, 0x14C, 0x150, 16 },
        nativeBitGeneration = new[] { 0x223F, 0x12C, 32 }, softwareResult = new[] { 0x2254, 0x88, 16 },
        nextReaders = new[] { 0x2261, 0x2264, 0x2266 }, assumptions = Array.Empty<string>(),
        physicalRpmAvailable = false, stop = "BeforeInstruction2259", configuration60f8 = "UnchangedZero;NotReachedBefore2259" } });
    public static async Task<P28PostStoreConsumerReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28PostStoreConsumerScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation);
        var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28PostStoreConsumerSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try
            {
                sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B"));
                contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!;
            }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2q native evidence.", e); }
        }
        var comparisons = new List<P28PostStoreConsumerComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i];
                    var ok = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    var adaptive = scenario.Mutation!.Kind != P28PostStoreMutationKind.FuelCell;
                    var af = a.Prefix.Prefix.Continuation?.Fuel; var bf = b.Prefix.Prefix.Continuation?.Fuel;
                    bool? controls = !ok ? null : !adaptive || af!.Data0140 == bf!.Data0140 && af.NativeFactor0158 == bf.NativeFactor0158 &&
                        af.Component == bf.Component && af.Correction == bf.Correction && af.Corrected == bf.Corrected && af.Store03b4 == bf.Store03b4 &&
                        a.Prefix.Expected!.Previous == b.Prefix.Expected!.Previous && a.Expected == b.Expected &&
                        a.SelectedScaledWordX1 == b.SelectedScaledWordX1 && a.RetainedOrZeroA == b.RetainedOrZeroA &&
                        P28LimiterFuelValidator.NumericControlHistory(af.Actual, bf.Actual);
                    bool? gate = !ok ? null : a.Prefix.Prefix.GateTaken != b.Prefix.Prefix.GateTaken;
                    bool? changed = !ok ? null : a.SelectedScaledWordX1 != b.SelectedScaledWordX1 || a.RetainedOrZeroA != b.RetainedOrZeroA;
                    var effect = !ok ? "Incomplete" : changed == true ? "NativeConsumerNumericalWitness" : gate == true ? "03A2GateOnly; consumer independent" :
                        a.Prefix.Result0150 != b.Prefix.Result0150 ? "DownstreamSelectionOrIntegerScaleMasked" : "EqualOutput; inspect cell reads/lookup/250threshold/2000clamp";
                    comparisons.Add(new(sequences[p].ScratchPattern, i, a.Prefix.Result0150, b.Prefix.Result0150, a.Expected?.Selected, b.Expected?.Selected,
                        a.SelectedScaledWordX1, b.SelectedScaledWordX1, a.RetainedOrZeroA, b.RetainedOrZeroA, gate, changed, controls, effect));
                }
        IReadOnlyList<int> diff = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, diff, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }
    internal static IReadOnlyList<P28PostStoreConsumerSequence> Analyze(RomImage image, P28PostStoreConsumerScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts",
            "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "consumerSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2q contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        return AnalyzeEvidence(image, scenario, root, id);
    }
    // A new outer task owns its identity and may retain a native suffix after2259.
    internal static IReadOnlyList<P28PostStoreConsumerSequence> AnalyzeEvidence(RomImage image, P28PostStoreConsumerScenario scenario,
        JsonElement root, string id, Func<int, int, bool>? terminalAfter = null, Func<int, int, ushort>? ieBefore = null,
        Action<int, int, JsonElement>? continuationBefore = null, Func<int, int, byte>? mode012bBefore = null, byte source011bLow7 = 0)
    {
        var seq = root.GetProperty("consumerSequences"); Require(seq.GetArrayLength() == 3, "M2q scratch count differs.");
        var own = new P28PostStoreConsumerOwn[3, scenario.Calls.Count];
        for (var p = 0; p < 3; p++)
        {
            var model = new P28PostStoreConsumerHistory(image, scenario);
            for (var i = 0; i < scenario.Calls.Count; i++) own[p, i] = model.Step(scenario.Calls[i], ieBefore?.Invoke(p, i), mode012bBefore?.Invoke(p, i));
        }
        var prefixView = JsonSerializer.SerializeToElement(new
        {
            runnerVersion = root.GetProperty("runnerVersion"),
            upstreamCommit = root.GetProperty("upstreamCommit"),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            postStoreSequences = seq.EnumerateArray().Select(s => new
            {
                scratchPattern = s.GetProperty("scratchPattern"),
                checkpoints = s.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("prefix")).ToArray()
            }).ToArray()
        });
        var prefixes = P28PostStoreValidator.AnalyzeEvidence(image, scenario.PrefixScenario, prefixView, id,
            (p, i) => (byte)own[p, i].Consumer.ModeBefore,
            (p, i) => seq[p].GetProperty("checkpoints")[i].GetProperty("status").GetInt32() != 0 || terminalAfter?.Invoke(p, i) == true, ieBefore, mode012bBefore, source011bLow7);
        var reports = new List<P28PostStoreConsumerSequence>();
        for (var p = 0; p < 3; p++)
        {
            P28LimiterScenario.Shape(seq[p], "scratchPattern", "checkpoints"); var pattern = new[] { 0, 85, 170 }[p];
            Require(seq[p].GetProperty("scratchPattern").GetInt32() == pattern, "M2q scratch order differs.");
            var rows = seq[p].GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "Dense M2q rows required.");
            var mode = scenario.InitialState.Adaptive.Joint.ProducerMode012c; var word0150 = 0; int? generation = null;
            var stopped = false; JsonElement previousExit = default; var checkpoints = new List<P28PostStoreConsumerCheckpoint>();
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "prefix", "mode012cBefore", "mode012cAfter", "word0150Before", "word0150After",
                    "consumer", "selectedScaledWordX1", "retainedOrZeroA");
                Require(row.GetProperty("index").GetInt32() == i && row.GetProperty("mode012cBefore").GetByte() == mode &&
                    row.GetProperty("word0150Before").GetInt32() == word0150, "M2q native mode/0150 history reset.");
                var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Invalid whole M2q status.");
                var prefix = prefixes[p].Checkpoints[i]; var consumer = row.GetProperty("consumer"); P28PostStoreConsumerProjection? projection = null;
                if (stopped) Require(status == 4 && consumer.ValueKind == JsonValueKind.Null && prefix.Disposition == "NotRun", "Terminal M2q event executed.");
                else
                {
                    // Raw source snapshots cannot change CPU/pointing registers. The first scripted ABI must observe the prior native exit before enter.
                    var adaptive = row.GetProperty("prefix").GetProperty("prefix");
                    var ticks = adaptive.GetProperty("ticks"); var producer = adaptive.GetProperty("producer");
                    var firstFragment = ticks.GetArrayLength() > 0 ? ticks[0] : producer;
                    Require(firstFragment.ValueKind == JsonValueKind.Object, "Missing first native fragment boundary.");
                    if (continuationBefore is null) RequireEventContinuation(previousExit, firstFragment.GetProperty("before"));
                    else continuationBefore(p, i, firstFragment.GetProperty("before"));
                    // Prefix evidence independently proves all partial native writes; only2239 may change0150.
                    word0150 = row.GetProperty("prefix").GetProperty("word0150After").GetInt32();
                    var suffix = row.GetProperty("prefix").GetProperty("suffix");
                    if (suffix.ValueKind == JsonValueKind.Object && Matrix(suffix.GetProperty("stage").GetProperty("writes"), 3, 48).Any(w => w[0] == 0x150)) generation = i;
                    if (prefix.Disposition == "StrictMatch")
                    {
                        Require(consumer.ValueKind == JsonValueKind.Object && generation == i && word0150 == own[p, i].PostStore.Result, "Fresh native2239 generation missing before consumer.");
                        var prefixExit = suffix.GetProperty("exit"); var expected = own[p, i]; projection = expected.Consumer;
                        var sources = scenario.Calls[i].Adaptive.Fuel.Sources;
                        var oracle = P28PostStoreConsumerEvidence.Build(expected.PostStoreExit, (ushort)expected.PostStore.Result,
                            sources.Source014c, sources.Source0144, mode, prefixExit.GetProperty("x1").GetInt32());
                        var native = ValidateConsumer(consumer, prefixExit, oracle);
                        Require(status == native.Status && (native.Status != 0 || oracle.X1 == projection.SelectedScaledWordX1 &&
                            oracle.Machine.Accumulator == projection.RetainedOrZeroA && oracle.Mode == projection.ModeAfter), "M2q whole-event/independent projection differs.");
                        mode = native.Steps == 0 ? mode : (byte)oracle.ModeEnds[native.Steps - 1];
                        previousExit = consumer.GetProperty("exit").Clone();
                        if (status == 0) Require(row.GetProperty("selectedScaledWordX1").GetInt32() == oracle.X1 &&
                            row.GetProperty("retainedOrZeroA").GetInt32() == oracle.Machine.Accumulator, "Wrong M2q final result.");
                    }
                    else Require(consumer.ValueKind == JsonValueKind.Null && status == row.GetProperty("prefix").GetProperty("status").GetInt32(), "Consumer executed after partial M2p prefix.");
                }
                Require(row.GetProperty("mode012cAfter").GetByte() == mode && row.GetProperty("word0150After").GetInt32() == word0150,
                    "Downstream mode neighbour/0150 overwrite or partial state rollback.");
                if (status != 0) Require(row.GetProperty("selectedScaledWordX1").ValueKind == JsonValueKind.Null && row.GetProperty("retainedOrZeroA").ValueKind == JsonValueKind.Null,
                    "Partial result presented as completed native result.");
                var disposition = status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                checkpoints.Add(new(i, disposition, prefix.Disposition, generation, generation == i ? prefix.Disposition == "StrictMatch" ? "NativeWritten2239" : "PartialNativeWritten2239" :
                    generation.HasValue ? "RetainedNativeGeneration" : "InitialDiagnosticStorage", projection, status == 0 ? row.GetProperty("selectedScaledWordX1").GetInt32() : null,
                    status == 0 ? row.GetProperty("retainedOrZeroA").GetInt32() : null, prefix, ReportRow(row, scenario.TraceCallIndexes.Contains(i))));
                stopped |= status != 0;
                stopped |= terminalAfter?.Invoke(p, i) == true;
            }
            reports.Add(new(id, pattern, checkpoints.AsReadOnly()));
        }
        return reports.AsReadOnly();
    }
    internal static void RequireEventContinuation(JsonElement previousExit, JsonElement firstBefore)
    {
        P28FuelFactorValidator.ValidateBoundary(firstBefore);
        if (previousExit.ValueKind == JsonValueKind.Undefined) return;
        P28FuelFactorValidator.ValidateBoundary(previousExit);
        Require(previousExit.GetProperty("pc").GetInt32() == 0x2259 && Equal(firstBefore, previousExit), "CPU reset/reload between native consumer and next event.");
    }
    internal static P28AcquisitionStageResult ValidateConsumer(JsonElement consumer, JsonElement prefixExit, P28PostStoreConsumerOracle own)
    {
        P28LimiterScenario.Shape(consumer, "entry", "exit", "stage", "accesses"); var entry = consumer.GetProperty("entry"); var exit = consumer.GetProperty("exit");
        P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        Require(Equal(entry, prefixExit) && entry.GetProperty("pc").GetInt32() == 0x223B && entry.GetProperty("lrb").GetInt32() == 0x20 &&
            entry.GetProperty("ssp").GetInt32() == 0x7FE && (entry.GetProperty("psw").GetInt32() & 7) == 1, "Reset/fresh entry or wrong bank on223B.");
        var stage = consumer.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 48, 0, [], null)!;
        Require(result.Status != 0 || result.Error is null, "Completed consumer reports an execution error.");
        var machine = own.Machine; var events = Matrix(stage.GetProperty("events"), 8, 48); var accesses = Matrix(consumer.GetProperty("accesses"), 5, 192);
        P28FuelAdditiveEvidence.RequireEventPrefix(stage, machine);
        Require(events.Length == result.Steps && result.Trace.Count == result.Steps && (result.Status != 0 || events.Length == machine.Events.Count), "Missing actual consumer instructions.");
        P28FuelCalculationValidator.ValidateEventContinuity(events, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(),
            exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        for (var n = 0; n < events.Length; n++) Require(result.Trace[n].GetProperty("pc").GetInt32() == events[n][0] && result.Trace[n].GetProperty("nextPc").GetInt32() == events[n][1] &&
            result.Trace[n].GetProperty("accumulator").GetInt32() == events[n][3] && result.Trace[n].GetProperty("psw").GetInt32() == events[n][5], "Trace contradicts consumer flags/branch.");
        var count = events.Length == 0 ? 0 : machine.AccessEnds[events.Length - 1];
        Require(Equal(accesses, machine.Accesses.Take(count).ToArray()) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(machine.Accesses.Take(count)
            .Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray())), "Wrong consumer native width/operand order/generation/stack/aliases.");
        var extents = machine.Events.Take(events.Length).SelectMany((e, n) => Enumerable.Range(e[0], machine.Lengths[n])).Distinct().Order().ToArray();
        Require(result.ExecutedInstructionBytes.SequenceEqual(extents) && result.StopPc == (events.Length == 0 ? 0x223B : events[^1][1]) &&
            exit.GetProperty("pc").GetInt32() == result.StopPc && (result.Status != 0 || result.StopPc == 0x2259), "Wrong consumer executed extent/exit.");
        Require(result.UsedAssumptions.Count == 0 && result.ProgramReads.Count == 0, "Foreign assumption/program read/60F8 bypass claim.");
        var regs = events.Length == 0 ? Enumerable.Range(0, 4).Select(n => Word(entry, n)).ToArray() : machine.RegisterEnds[events.Length - 1];
        Require(Enumerable.Range(0, 4).All(n => Word(exit, n) == regs[n]), "Helper register-bank aliases/clobbers differ.");
        foreach (var key in new[] { "lrb", "x2", "dp", "usp" }) Require(Equal(entry.GetProperty(key), exit.GetProperty(key)), "Consumer changed retained pointer/bank.");
        var ssp = events.Length == 0 ? 0x7FE : machine.StackEnds[events.Length - 1];
        var x1 = events.Length == 0 ? entry.GetProperty("x1").GetInt32() : own.X1Ends[events.Length - 1];
        Require(stage.GetProperty("sspAfter").GetInt32() == ssp && exit.GetProperty("ssp").GetInt32() == ssp && exit.GetProperty("x1").GetInt32() == x1,
            "Native helper return/partial stack/new X1 result differs.");
        return result;
    }
    private static JsonElement ReportRow(JsonElement row, bool trace)
    {
        if (trace) return row.Clone(); var node = JsonNode.Parse(row.GetRawText())!;
        void Strip(JsonNode? value)
        {
            if (value is JsonObject o) foreach (var item in o.ToArray()) { if (item.Key == "trace") o[item.Key] = new JsonArray(); else Strip(item.Value); }
            else if (value is JsonArray a) foreach (var child in a) Strip(child);
        }
        Strip(node); return JsonSerializer.SerializeToElement(node);
    }
}
