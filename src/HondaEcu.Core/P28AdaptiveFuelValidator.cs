using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28AdaptiveFuelCheckpoint(int Index, string Disposition, string ThresholdProvenance, int? Generation,
    int? Bank, string? ProducerPath, IReadOnlyList<int[]> TableReads, ushort RamCutBefore, ushort RamResumeBefore,
    ushort RamCutAfter, ushort RamResumeAfter, int NativeTicks, string? ThresholdSource, ushort? SelectedThreshold,
    bool? Request, bool? GateTaken, P28LimiterFuelCheckpoint? Continuation, JsonElement Actual);
public sealed record P28AdaptiveFuelSequence(string Image, int ScratchPattern, IReadOnlyList<P28AdaptiveFuelCheckpoint> Checkpoints);
public sealed record P28AdaptiveFuelComparison(int ScratchPattern, int Index, bool? Controls, bool? NativeBaseReadChanged,
    bool? RamDiverged, bool? RequestDiverged, bool? GateDiverged, int? Store03a2A, int? Store03a2B,
    int? Store03b4A, int? Store03b4B, bool? Witness);
public sealed record P28AdaptiveFuelReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, P28AdaptiveFuelMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28AdaptiveFuelSequence> Sequences, IReadOnlyList<P28AdaptiveFuelComparison> Comparisons,
    JsonElement EntryContract, IReadOnlyList<object> ChecksumArithmetic)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        NativeTickInvocations = Sequences.SelectMany(s => s.Checkpoints).Sum(c => c.NativeTicks),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        ThresholdProvenances = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.ThresholdProvenance).ToDictionary(g => g.Key, g => g.Count()),
        Witnesses = Comparisons.Count(c => c.Witness == true)
    };
    public string Schedule => "Snapshots->native01D5/01CE ticks->487B..48F5->1966..1A38->native0140/0158->217A/21F5->03A2/03B4; scripted ABI, not recovered ECU scheduler";
    public string Ownership => "One CPU/RAM; base words/current RAM/selected threshold distinct; no producer outputs fed into independent C# model; mask5585/P2 NotRun";
    public string InitialThresholdHistory => "Declared initial history only; Held retains last actual writer generation, including across bank changes; same-value stores are Written";
    public string IeScope => "Word-only software IE storage and native MIE transitions; IRQ/preemption/reserved-bit hardware unavailable";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time/degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; one-word B in memory, no compensation/binding/export/receipt/token";
}

public static class P28AdaptiveFuelValidator
{
    public const string Operation = "adaptiveLimiterFuelGateChain";
    private static readonly int[][] Masks = [[0x21F, 2], [0x217, 32], [0x214, 1], [0x212, 32], [0x223, 4], [0x11B, 128]];
    public static object CreateRequest(RomImage image, P28AdaptiveFuelScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28LimiterFuelValidator.CreateRequest(image, scenario.JointScenario(scenario.Calls.Count)), JsonDefaults.Create());
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
            scratchPatterns = new[] { 0, 85, 170 },
            allowAssumptions = Array.Empty<string>(),
            adaptiveLimiterFuelGateChain = new
            {
                formatVersion = 1,
                initialState = new
                {
                    joint = old.GetProperty("limiterFuelGateChain").GetProperty("initialState"),
                    scenario.InitialState.RamCut,
                    scenario.InitialState.RamResume,
                    scenario.InitialState.Timer,
                    scenario.InitialState.Counter,
                    scenario.InitialState.Ie,
                    scenario.InitialState.RestoreIe
                },
                scenario.Calls,
                scenario.TraceCallIndexes
            }
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, adaptiveContract = P28AdaptiveValidator.ExpectedContracts()[0],
        continuationContract = P28LimiterFuelValidator.ExpectedContracts()[0], sourceMasks = Masks,
        context = "Frozen P4.0=0; masked011B.7 selects fixed/RAM;0121=80 once",
        schedule = "Snapshots->ticks01D5->ticks01CE->487B..48F5->1966..1A38->lookup0140->factor0158->217A->21F5->03A2/03B4; scripted ABI, not ECU scheduler",
        ownership = "One CPU/RAM; thresholds native Written or retained InitialHistory/Held; no mask5585/P2",
        assumptions = Array.Empty<string>(), physicalRpmAvailable = false, stop = "BeforeInstruction2204" } });
    internal static (int Bank, bool Cut, int Offset) Mapping(P28AdaptiveFuelMutationKind kind)
    {
        if (!Enum.IsDefined(kind)) throw new ArgumentException("Unknown adaptive base word.");
        var bank = kind is P28AdaptiveFuelMutationKind.Bank1Cut or P28AdaptiveFuelMutationKind.Bank1Resume ? 1 : 0;
        var cut = kind is P28AdaptiveFuelMutationKind.Bank0Cut or P28AdaptiveFuelMutationKind.Bank1Cut;
        return (bank, cut, P28LimiterInspector.AdaptiveBaseOffset(bank, cut));
    }
    internal static RomImage Mutate(RomImage original, P28AdaptiveFuelMutation mutation)
    {
        var m = Mapping(mutation.Kind); var old = P28LimiterInspector.Word(original.Span, m.Offset);
        if (Math.Abs(mutation.Value - old) is < 1 or > 8) throw new ArgumentException("Require a nonzero small one-word change of at most8 raw counts.");
        var child = original.CreateModifiedCopy([new BytePatch(m.Offset, [(byte)mutation.Value, (byte)(mutation.Value >> 8)])]);
        AdmitMutation(original, child, mutation); return child;
    }
    internal static void AdmitMutation(RomImage original, RomImage child, P28AdaptiveFuelMutation mutation)
    {
        P28LimiterInspector.OperandGuard(original); P28LimiterInspector.OperandGuard(child);
        P28FuelMapInspector.LayoutGuard(original); P28FuelMapInspector.LayoutGuard(child);
        var m = Mapping(mutation.Kind); var old = P28LimiterInspector.Word(original.Span, m.Offset);
        Require(Math.Abs(mutation.Value - old) is >= 1 and <= 8 && P28LimiterInspector.Word(child.Span, m.Offset) == mutation.Value, "Incorrect adaptive one-word B.");
        var cut = P28LimiterInspector.Word(child.Span, P28LimiterInspector.AdaptiveBaseOffset(m.Bank, true));
        var resume = P28LimiterInspector.Word(child.Span, P28LimiterInspector.AdaptiveBaseOffset(m.Bank, false));
        Require(cut > 0 && cut < resume && resume < 65535, "Small B must retain an ordered non-endpoint base pair.");
        for (var i = 0; i < original.Size; i++) Require(i >= m.Offset && i < m.Offset + 2 || original.Span[i] == child.Span[i], "Extra byte outside selected adaptive word, including64A9 coefficient.");
    }
    public static async Task<P28AdaptiveFuelReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28AdaptiveFuelScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original fuel configuration required.");
        var child = scenario.Mutation is null ? null : Mutate(original, scenario.Mutation);
        var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28AdaptiveFuelSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try
            {
                sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B"));
                contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!;
            }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2o native evidence.", e); }
        }
        var comparisons = new List<P28AdaptiveFuelComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i];
                    var ok = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    var af = a.Continuation?.Fuel; var bf = b.Continuation?.Fuel;
                    bool? controls = !ok ? null : af!.Data0140 == bf!.Data0140 && af.NativeFactor0158 == bf.NativeFactor0158 && af.Component == bf.Component &&
                        af.Correction == bf.Correction && af.Corrected == bf.Corrected && af.Store03b4 == bf.Store03b4 && P28LimiterFuelValidator.NumericControlHistory(af.Actual, bf.Actual);
                    bool? read = !ok ? null : !Equal(a.TableReads, b.TableReads);
                    bool? ram = !ok ? null : a.RamCutAfter != b.RamCutAfter || a.RamResumeAfter != b.RamResumeAfter;
                    bool? request = !ok ? null : a.Request != b.Request; bool? gate = !ok ? null : a.GateTaken != b.GateTaken;
                    // Held generations can carry a prior changed read; the generation's actual Written event is independently validated.
                    var generationRead = ok && a.Generation.HasValue && b.Generation.HasValue &&
                        !Equal(sequences[p].Checkpoints[a.Generation.Value].TableReads, sequences[p + 3].Checkpoints[b.Generation.Value].TableReads);
                    bool? witness = !ok ? null : controls == true && (read == true || generationRead) && ram == true && request == true && gate == true && af!.Corrected > 0 && af.Store03a2 != bf!.Store03a2;
                    comparisons.Add(new(sequences[p].ScratchPattern, i, controls, read, ram, request, gate, af?.Store03a2, bf?.Store03a2, af?.Store03b4, bf?.Store03b4, witness));
                }
        IReadOnlyList<int> diff = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        var sums = images.Select((im, i) => (object)new { image = i == 0 ? "A" : "B", arithmetic = P28NativeChecksumArithmetic.Calculate(im), scope = "Diagnostic only; no compensation/export" }).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, diff, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract, sums);
    }
    internal static IReadOnlyList<P28AdaptiveFuelSequence> Analyze(RomImage image, P28AdaptiveFuelScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "adaptiveFuelSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2o native/scripted contracts differ.");
        foreach (var k in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(k).GetArrayLength() == 0, "Foreign rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        return AnalyzeEvidence(image, scenario, root, id);
    }
    // Composition only: outer task validates its own identity/schema before using this prefix oracle.
    internal static IReadOnlyList<P28AdaptiveFuelSequence> AnalyzeEvidence(RomImage image, P28AdaptiveFuelScenario scenario,
        JsonElement root, string id, ushort? initialPrevious03b4 = null, Func<int, int, bool>? terminalAfter = null)
    {
        var sequences = root.GetProperty("adaptiveFuelSequences"); Require(sequences.GetArrayLength() == 3, "M2o scratch count differs.");
        var models = Enumerable.Range(0, 3).Select(_ => new P28AdaptiveModel(image.Span, scenario.ModelInitial)).ToArray();
        var production = new P28AdaptiveProductionStep?[3, scenario.Calls.Count];
        var count = sequences[0].GetProperty("checkpoints").EnumerateArray().Count(r => r.GetProperty("joint").GetProperty("decision").ValueKind == JsonValueKind.Object);
        Require(sequences.EnumerateArray().All(s => s.GetProperty("checkpoints").EnumerateArray().Count(r => r.GetProperty("joint").GetProperty("decision").ValueKind == JsonValueKind.Object) == count), "Scratch-dependent native attempt count.");
        IReadOnlyList<P28LimiterFuelSequence>? continuations = null;
        if (count > 0)
        {
            var view = JsonSerializer.SerializeToElement(sequences.EnumerateArray().Select(s => new
            {
                scratchPattern = s.GetProperty("scratchPattern").GetInt32(),
                checkpoints = s.GetProperty("checkpoints").EnumerateArray().Take(count).Select(c => c.GetProperty("joint")).ToArray()
            }).ToArray());
            continuations = P28LimiterFuelValidator.AnalyzeShared(image, scenario.JointScenario(count), root, view, id,
                (p, i, mode) =>
                {
                    models[p].AcceptModeledFuelByte(mode); production[p, i] = models[p].StepProduction(scenario.Calls[i].Adaptive);
                    return models[p].StepDecision(scenario.Calls[i].Fuel.RawPeriod, scenario.Calls[i].FixedSource);
                },
                (p, _, mode) => models[p].AcceptModeledFuelByte(mode),
                (p, i) => ProductionAccumulator(production[p, i]!),
                (_, i) => scenario.Calls[i].FixedSource ? (byte)128 : (byte)0, initialPrevious03b4);
        }
        var reports = new List<P28AdaptiveFuelSequence>();
        for (var p = 0; p < 3; p++)
        {
            var seq = sequences[p]; P28LimiterScenario.Shape(seq, "scratchPattern", "checkpoints"); var pattern = new[] { 0, 85, 170 }[p];
            Require(seq.GetProperty("scratchPattern").GetInt32() == pattern, "Scratch order differs."); var rows = seq.GetProperty("checkpoints");
            Require(rows.GetArrayLength() == scenario.Calls.Count, "Dense M2o rows required.");
            JsonElement prior = default; var stopped = false; int? generation = null; var list = new List<P28AdaptiveFuelCheckpoint>();
            var priorJoint = JsonSerializer.SerializeToElement(new { scenario.InitialState.Joint.Data0124, scenario.InitialState.Joint.Data012b, scenario.InitialState.Joint.Data01d7 }, JsonDefaults.Create());
            for (var i = 0; i < rows.GetArrayLength(); i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "input", "snapshotWrites", "stateBefore", "stateAfterProducer", "stateAfter", "ticks", "producer", "joint");
                Require(row.GetProperty("index").GetInt32() == i, "M2o event order differs."); var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Invalid M2o status.");
                var before = row.GetProperty("stateBefore"); var after = row.GetProperty("stateAfter"); StateShape(before); StateShape(after);
                if (i > 0) Require(Equal(before, prior), "Threshold/timer/IE/source history was reseeded.");
                else Require(Word(before, "ramCut") == scenario.InitialState.RamCut && Word(before, "ramResume") == scenario.InitialState.RamResume &&
                    Word(before, "ie") == scenario.InitialState.Ie && Word(before, "restoreIe") == scenario.InitialState.RestoreIe &&
                    Word(before, "timer") == scenario.InitialState.Timer && Word(before, "counter") == scenario.InitialState.Counter &&
                    before.GetProperty("sources").EnumerateArray().Select(x => x.GetInt32()).SequenceEqual(new[] { pattern, pattern, pattern, pattern, pattern, 0 }), "Authoritative initial history differs.");
                var producer = row.GetProperty("producer"); var ticks = row.GetProperty("ticks"); var joint = row.GetProperty("joint");
                foreach (var key in new[] { "stateBefore", "stateAfterDecision", "stateAfter" })
                    P28LimiterScenario.Shape(joint.GetProperty(key), "data0124", "data012b", "data01d7");
                Require(Equal(joint.GetProperty("stateBefore"), priorJoint), "Shared decision/fuel history was reseeded before producer or terminal suffix.");
                P28LimiterFuelCheckpoint? continuation = i < count ? continuations![p].Checkpoints[i] : null;
                var provenance = "NotRun"; int? bank = null; string? path = null; int[][] reads = [];
                if (stopped)
                {
                    Require(status == 4 && row.GetProperty("input").ValueKind == JsonValueKind.Null && row.GetProperty("snapshotWrites").GetArrayLength() == 0 &&
                        producer.ValueKind == JsonValueKind.Null && ticks.GetArrayLength() == 0 && row.GetProperty("stateAfterProducer").ValueKind == JsonValueKind.Null && Equal(before, after), "Terminal M2o suffix ran inputs/stages.");
                    ValidateUnattemptedJoint(joint, false, scenario.Calls[i].Fuel);
                }
                else
                {
                    Require(status != 4 && Equal(row.GetProperty("input"), JsonSerializer.SerializeToElement(scenario.Calls[i], JsonDefaults.Create())), "Missing/different M2o raw snapshot.");
                    ValidateSnapshot(row, scenario.Calls[i]);
                    var expected = production[p, i] ?? models[p].StepProduction(scenario.Calls[i].Adaptive);
                    var parsedTicks = new List<P28AdaptiveValidator.Stage>(); JsonElement boundary = default; var tickFailed = false;
                    Require(ticks.GetArrayLength() <= expected.Ticks.Count, "Extra tick invocations.");
                    for (var t = 0; t < ticks.GetArrayLength(); t++)
                    {
                        Require(!tickFailed, "Tick after native failure."); var f = ticks[t]; var own = expected.Ticks[t];
                        var parsed = ValidateFragment(f, own.Address, boundary);
                        Require(Equal(parsed.Writes, own.Writes.Take(parsed.Writes.Length)) && parsed.Writes.Length <= own.Writes.Count,
                            "Native tick stores differ from independent decrement/zero model.");
                        Require(parsed.Events.Length == 0 || parsed.Events[0][3] % 256 == own.Before, "Wrong native tick target value.");
                        Require(parsed.Result.Status != 0 || Equal(parsed.Writes, own.Writes) && Equal(parsed.Events.Where(e => e[0] == 0x5BD3).Select(e => new[] { e[0], e[1] }).ToArray(), own.Branches), "Native zero tick branch differs.");
                        parsedTicks.Add(parsed); boundary = f.GetProperty("exit"); tickFailed = parsed.Result.Status != 0;
                    }
                    if (tickFailed) Require(producer.ValueKind == JsonValueKind.Null && row.GetProperty("stateAfterProducer").ValueKind == JsonValueKind.Null && status == parsedTicks[^1].Result.Status && continuation is null, "Execution after incomplete tick.");
                    else
                    {
                        Require(parsedTicks.Count == expected.Ticks.Count && producer.ValueKind == JsonValueKind.Object, "Missing native producer/ticks; final numbers cannot replace evidence.");
                        var stage = ValidateFragment(producer, null, boundary); reads = P28AdaptiveValidator.TableReads(stage);
                        Require(stage.Result.Status != 0 || Equal(stage.Writes, expected.ProducerWrites) && Equal(reads, expected.TableReads) &&
                            Equal(stage.Events.Where(e => P28AdaptiveValidator.ProducerBranches.Contains(e[0])).Select(e => new[] { e[0], e[1] }).ToArray(), expected.Branches), "Adaptive arithmetic/bank/branch/store provenance differs.");
                        if (stage.Result.Status == 0)
                        {
                            bank = expected.Bank; path = expected.Path;
                            var produced = row.GetProperty("stateAfterProducer"); StateShape(produced);
                            Require(Word(produced, "ramCut") == expected.After.Limiter.RamCut && Word(produced, "ramResume") == expected.After.Limiter.RamResume &&
                                Word(produced, "timer") == expected.After.Timer && Word(produced, "counter") == expected.After.Counter &&
                                Word(produced, "ie") == expected.After.Ie && Word(produced, "restoreIe") == expected.After.RestoreIe, "Actual RAM/counters/IE differ from independent production.");
                            ValidateCritical(stage, expected.Path); ValidateCalls(stage, Matrix(producer.GetProperty("accesses"), 5, 1024));
                            Require(producer.GetProperty("exit").GetProperty("accumulator").GetInt32() == ProductionAccumulator(expected) &&
                                producer.GetProperty("exit").GetProperty("dp").GetInt32() == (expected.Path == "TimerHold" ? expected.TableReads[0][2] : expected.After.Limiter.RamResume), "Producer carrier value differs.");
                            if (expected.Path != "TimerHold") { generation = i; provenance = "Written"; } else provenance = generation.HasValue ? "Held" : "InitialHistory";
                            Require(continuation is not null && status == joint.GetProperty("status").GetInt32() &&
                                Equal(producer.GetProperty("exit"), joint.GetProperty("handoffToDecision")), "Producer->limiter scripted seam reset or missing downstream.");
                            Require(Equal(produced, after), "Downstream overwrote adaptive thresholds/counters/IE/source bytes.");
                            ValidateRamHandoff(row, expected);
                        }
                        else Require(continuation is null && status == stage.Result.Status, "Downstream ran after partial producer.");
                    }
                    if (continuation is null) ValidateUnattemptedJoint(joint, true, scenario.Calls[i].Fuel);
                    ValidatePartialState(row, parsedTicks);
                    stopped = status != 0;
                }
                var disposition = status == 0 ? continuation?.Disposition ?? "Mismatch" : Status(status);
                var source = continuation?.ExpectedDecision?.Context == "Fixed" ? "FixedImmediate" : continuation?.ExpectedDecision is null ? null : "AdaptiveRam";
                list.Add(new(i, disposition, provenance, provenance == "NotRun" ? null : generation, bank, path, reads,
                    (ushort)Word(before, "ramCut"), (ushort)Word(before, "ramResume"), (ushort)Word(after, "ramCut"), (ushort)Word(after, "ramResume"), ticks.GetArrayLength(),
                    source, continuation?.SelectedThreshold, continuation?.Request, continuation?.GateTaken, continuation, row.Clone())); prior = after.Clone();
                priorJoint = joint.GetProperty("stateAfter").Clone();
                stopped |= terminalAfter?.Invoke(p, i) == true;
            }
            reports.Add(new(id, pattern, list.AsReadOnly()));
        }
        return reports.AsReadOnly();
    }
    private static string Status(int s) => s switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
    private static int Word(JsonElement e, string key) => e.GetProperty(key).GetInt32();
    private static int ProductionAccumulator(P28AdaptiveProductionStep p) => p.Path == "TimerHold" ? (p.TableReads[1][2] & 0xFF00) | p.After.Timer : p.After.RestoreIe;
    private static void StateShape(JsonElement e)
    {
        P28LimiterScenario.Shape(e, "ramCut", "ramResume", "timer", "counter", "ie", "restoreIe", "sources");
        foreach (var k in new[] { "ramCut", "ramResume", "ie", "restoreIe" }) Require(Word(e, k) is >= 0 and <= 65535, "Invalid word history.");
        foreach (var k in new[] { "timer", "counter" }) Require(Word(e, k) is >= 0 and <= 255, "Invalid byte history.");
        Require(e.GetProperty("sources").GetArrayLength() == 6 && e.GetProperty("sources").EnumerateArray().All(v => v.GetInt32() is >= 0 and <= 255), "Invalid source-byte history.");
    }
    private static void ValidateSnapshot(JsonElement row, P28AdaptiveFuelCall c)
    {
        var before = row.GetProperty("stateBefore").GetProperty("sources").EnumerateArray().Select(x => x.GetInt32()).ToArray();
        bool[] bits = [c.Bank1, c.Reset217, c.Reset214, c.Mode212, c.Enable223, c.FixedSource];
        var expected = Masks.Select((m, i) => new[] { m[0], 8, (before[i] & ~m[1]) | (bits[i] ? m[1] : 0) }).Concat(new[] { new[] { 0xCE, 16, (int)c.Raw00ce }, new[] { 0xD9, 8, (int)c.RawD9 } }).ToArray();
        Require(Equal(row.GetProperty("snapshotWrites"), JsonSerializer.SerializeToElement(expected)), "Snapshot overwrote neighboring bits or ready thresholds.");
        Require(row.GetProperty("stateAfter").GetProperty("sources").EnumerateArray().Select(x => x.GetInt32()).SequenceEqual(expected.Take(6).Select(x => x[2])), "Source mask preservation differs.");
    }
    private static P28AdaptiveValidator.Stage ValidateFragment(JsonElement f, int? target, JsonElement prior)
    {
        P28LimiterScenario.Shape(f, "before", "entry", "exit", "transitionWrites", "stage", "accesses", "tickTarget");
        Require(target.HasValue ? f.GetProperty("tickTarget").GetInt32() == target : f.GetProperty("tickTarget").ValueKind == JsonValueKind.Null, "Unowned tick target.");
        var before = f.GetProperty("before"); var entry = f.GetProperty("entry"); var exit = f.GetProperty("exit");
        foreach (var b in new[] { before, entry, exit }) P28FuelFactorValidator.ValidateBoundary(b);
        if (prior.ValueKind != JsonValueKind.Undefined) Require(Equal(before, prior), "Native fragment continuity reset.");
        var writes = new List<int[]> { new[] { 2, 16, 0x41 }, new[] { 4, 16, target.HasValue ? 1 : 0x1101 }, new[] { 0x8E, 16, 0x180 } };
        if (target.HasValue) writes.Add([0x88, 16, target.Value]);
        Require(Equal(f.GetProperty("transitionWrites"), JsonSerializer.SerializeToElement(writes)) && Word(entry, "pc") == (target.HasValue ? 0x5BD0 : 0x487B) &&
            Word(entry, "psw") == (target.HasValue ? 0x0CC9 : 0x1DC9) &&
            Word(entry, "lrb") == 0x41 && Word(entry, "usp") == 0x180 && Word(entry, "ssp") == 0x7FE &&
            Word(entry, "accumulator") == Word(before, "accumulator") && Word(entry, "x2") == Word(before, "x2") && Word(entry, "dp") == Word(before, "dp") &&
            Word(entry, "x1") == (target ?? Word(before, "x1")), "ABI copied/reseeded native carrier/stack/bank.");
        if (Word(before, "lrb") == 0x41) Require(Equal(before.GetProperty("registers"), entry.GetProperty("registers")), "Register-bank contents copied/reset.");
        var stage = P28AdaptiveValidator.ParseStage(f.GetProperty("stage"), target.HasValue)!;
        Require(Word(exit, "pc") == stage.Result.StopPc && Word(exit, "ssp") == stage.Ssp, "Native exit disagrees with stage.");
        P28FuelCalculationValidator.ValidateEventContinuity(stage.Events, Word(entry, "accumulator"), Word(entry, "psw"), Word(exit, "accumulator"), Word(exit, "psw"));
        var accesses = Matrix(f.GetProperty("accesses"), 5, 1024);
        Require(accesses.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).SelectMany(x => x).SequenceEqual(stage.Writes.SelectMany(x => x)), "Adaptive native writes missing from access ledger.");
        Require(accesses.All(a => a[0] is >= 0x487B and < 0x48F5 or >= 0x5AB8 and < 0x5AE6 or >= 0x5BD0 and < 0x5BD9), "Foreign native fragment.");
        return stage;
    }
    private static void ValidateCritical(P28AdaptiveValidator.Stage stage, string path)
    {
        var critical = stage.Events.Where(e => e[0] is 0x48E6 or 0x48E9 or 0x48EC or 0x48EE).ToArray();
        Require(path == "TimerHold" ? critical.Length == 0 && stage.Writes.All(w => w[0] is not (0x1A or 0x1A4 or 0x1A6)) :
            critical.Length == 4 && (critical[0][5] & 256) == 0 && (critical[1][4] & 256) == 0 && (critical[2][4] & 256) == 0 && (critical[3][5] & 256) != 0,
            "Native MIE/ordered critical section differs.");
    }
    private static void ValidateCalls(P28AdaptiveValidator.Stage stage, int[][] accesses)
    {
        var calls = stage.Events.Where(e => e[0] is 0x48BA or 0x48C2 or 0x48D3 or 0x48DE).ToArray();
        var returns = stage.Events.Where(e => e[0] is 0x5AC1 or 0x5AE5).ToArray();
        Require(calls.Length == returns.Length && calls.Select(e => e[0] + 3).SequenceEqual(returns.Select(e => e[1])) &&
            stage.Writes.Where(w => w[0] == 0x7FE).Select(w => w[2]).SequenceEqual(calls.Select(e => e[0] + 3)) && stage.Ssp == 0x7FE,
            "CAL/RT/return PCs/stack slot order differs.");
        var stack = accesses.Where(a => a[1] == 0x7FE).ToArray();
        Require(stack.Length == calls.Length * 2 && stack.Select((a, i) => a.SequenceEqual(new[] { i % 2 == 0 ? calls[i / 2][0] : returns[i / 2][0], 0x7FE, 16, i % 2 == 0 ? 1 : 0, calls[i / 2][0] + 3 })).All(v => v), "Native stack accesses substituted.");
    }
    private static void ValidateRamHandoff(JsonElement row, P28AdaptiveProductionStep expected)
    {
        var joint = row.GetProperty("joint"); var accesses = Matrix(joint.GetProperty("decisionAccesses"), 5, 384);
        var writes = Matrix(row.GetProperty("producer").GetProperty("stage").GetProperty("writes"), 3, 160);
        Require(expected.Path == "TimerHold" ? writes.All(w => w[0] is not (0x1A4 or 0x1A6)) : writes.Count(w => w[0] is 0x1A4 or 0x1A6 && w[1] == 16) == 2, "Missing/partial pair generation.");
        var ramReads = accesses.Where(a => a[3] == 0 && a[1] is 0x1A4 or 0x1A6).ToArray();
        if (row.GetProperty("input").GetProperty("fixedSource").GetBoolean()) Require(ramReads.Length == 0, "Fixed-control secretly consumed RAM.");
        else Require(Equal(ramReads, new[] { new[] { 0x1974, 0x1A6, 16, 0, (int)expected.After.Limiter.RamResume }, new[] { 0x1977, 0x1A4, 16, 0, (int)expected.After.Limiter.RamCut } }), "Native current RAM pair not actually read by limiter.");
    }
    private static void ValidatePartialState(JsonElement row, IReadOnlyList<P28AdaptiveValidator.Stage> ticks)
    {
        var state = row.GetProperty("stateBefore"); var cut = Word(state, "ramCut"); var resume = Word(state, "ramResume"); var timer = Word(state, "timer"); var counter = Word(state, "counter"); var ie = Word(state, "ie");
        var writes = ticks.SelectMany(t => t.Writes).ToList();
        if (row.GetProperty("producer").ValueKind == JsonValueKind.Object) writes.AddRange(Matrix(row.GetProperty("producer").GetProperty("stage").GetProperty("writes"), 3, 160));
        foreach (var w in writes) switch (w[0]) { case 0x1A4: cut = w[2]; break; case 0x1A6: resume = w[2]; break; case 0x1D5: timer = w[2]; break; case 0x1CE: counter = w[2]; break; case 0x1A: ie = w[2]; break; }
        var after = row.GetProperty("stateAfter"); Require(Word(after, "ramCut") == cut && Word(after, "ramResume") == resume && Word(after, "timer") == timer && Word(after, "counter") == counter &&
            Word(after, "ie") == ie && Word(after, "restoreIe") == Word(state, "restoreIe"), "Partial/complete RAM history contradicts native write prefix.");
        if (row.GetProperty("producer").ValueKind == JsonValueKind.Object)
            Require(Equal(row.GetProperty("stateAfterProducer"), after), "Partial producer state differs from preserved state; no downstream adaptive writes are permitted.");
    }
    private static void ValidateUnattemptedJoint(JsonElement joint, bool snapshots, P28LimiterFuelCall c)
    {
        Require(joint.GetProperty("status").GetInt32() == 4 && joint.GetProperty("input").ValueKind == JsonValueKind.Null && joint.GetProperty("decision").ValueKind == JsonValueKind.Null &&
            joint.GetProperty("decisionAccesses").GetArrayLength() == 0 && joint.GetProperty("transitionToDecisionWrites").GetArrayLength() == 0 &&
            Equal(joint.GetProperty("stateBefore"), joint.GetProperty("stateAfterDecision")) && Equal(joint.GetProperty("stateBefore"), joint.GetProperty("stateAfter")), "Downstream executed without completed producer.");
        foreach (var k in new[] { "decisionEntry", "decisionExit", "handoffToDecision" }) Require(joint.GetProperty(k).ValueKind == JsonValueKind.Null, "Unexecuted decision boundary fabricated.");
        P28LimiterFuelValidator.ValidateFuelNotRun(joint.GetProperty("fuel"));
        var inputs = Matrix(joint.GetProperty("inputWrites"), 3, 32); Require(inputs.Length == (snapshots ? 23 : 0), "Unexpected downstream host snapshots.");
        P28FuelFactorValidator.ValidateCheckpointShape(joint.GetProperty("fuel"), true, false);
        P28FuelFactorValidator.ValidateInputWrites(joint.GetProperty("fuel").GetProperty("inputWrites"), c.Fuel, snapshots);
        Require(Equal(joint.GetProperty("fuel").GetProperty("inputWrites"), JsonSerializer.SerializeToElement(inputs.Take(snapshots ? 22 : 0))), "Joint/fuel raw input ledger differs.");
        if (snapshots) Require(inputs[^1].SequenceEqual(new[] { 0xC4, 16, (int)c.RawPeriod }) && Equal(joint.GetProperty("fuel").GetProperty("sourcesAfter"), JsonSerializer.SerializeToElement(c.Sources, JsonDefaults.Create())), "Raw snapshot missing after partial adaptive stage.");
        else Require(Equal(joint.GetProperty("fuel").GetProperty("sourcesBefore"), joint.GetProperty("fuel").GetProperty("sourcesAfter")), "Terminal raw snapshot applied.");
    }
}
