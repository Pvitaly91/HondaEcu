using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28LimiterFuelCheckpoint(int Index, string Disposition, string DecisionDisposition, ushort? SelectedThreshold,
    bool? Request, bool? GateTaken, P28LimiterDecisionStep? ExpectedDecision, P28FuelFactorCheckpoint? Fuel, JsonElement Actual);
public sealed record P28LimiterFuelSequence(string Image, int ScratchPattern, IReadOnlyList<P28LimiterFuelCheckpoint> Checkpoints);
public sealed record P28LimiterFuelComparison(int ScratchPattern, int Index, bool? Controls, bool? RequestDiverged,
    bool? GateDiverged, int? Store03a2A, int? Store03a2B, int? Store03b4A, int? Store03b4B, bool? Witness, string Effect);
public sealed record P28LimiterFuelReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28LimiterFuelMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28LimiterFuelSequence> Sequences,
    IReadOnlyList<P28LimiterFuelComparison> Comparisons, JsonElement EntryContract, IReadOnlyList<object> ChecksumArithmetic)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        NativeBitHandoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        Witnesses = Comparisons.Count(c => c.Witness == true)
    };
    public string Schedule => "Snapshots->1966..1A38->native axes/lookup->1F43..1FB7->217A->2194..2204; scripted routine entries only; no reset at21DB/21F2";
    public string FixedContext => "011B.7=1 once; frozen P4.0=0 byte read;0121=80 once; adaptive/ticks/RAM threshold inputs NotRun";
    public string Ownership => "One initial0124/012B; native decision writes pass through fuel to217A/21F5; no host bit substitution or mask-consumer simulation";
    public string Unevaluated => "Earlier cut causes, adaptive/ticks,5585/P2, timer/IRQ/electrical delivery, full scheduler/boot/engine NotRun;217D..2193 unreachable after this limiter bit4 clear";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time/degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; B only in memory, no compensation/binding/export";
}

public static class P28LimiterFuelValidator
{
    public const string Operation = "limiterFuelGateChain";
    public static object CreateRequest(RomImage image, P28LimiterFuelScenario s) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        limiterFuelGateChain = new
        {
            formatVersion = 1,
            initialState = new
            {
                fuel = s.InitialState.Fuel.Fuel,
                s.InitialState.Data0124,
                s.InitialState.Data012b,
                s.InitialState.Data01d7,
                s.InitialState.ProducerMode012c,
                s.InitialState.ProducerSelector012f,
                s.InitialState.Hysteresis0130
            },
            s.Calls,
            s.TraceCallIndexes
        }
    };
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, decisionEntry = 0x1966, decisionExit = 0x1A38, decisionBudget = 96,
        fixedContext = new { data011b = 128, data0121 = 128, p4Bit0 = false }, fixedOperands = new[] { new[] { 0x1967, 16 }, new[] { 0x196A, 16 } },
        callerGate = new[] { 0x217A, 0x2194 }, gateReader = new[] { 0x21F5, 0x124, 5 }, gateWriter = new[] { 0x1A23, 0x124, 5 }, bit4Writer = 0x1A28,
        hostTransitionWrites = new[] { new[] { 2, 16, 0x20 }, new[] { 4, 16, 0x0101 }, new[] { 0x8E, 16, 0x280 } },
        fuelContract = P28FuelFactorValidator.ExpectedContracts()[0], sharedState = new[] { 0x124, 0x12B, 0x1D7, 0x130, 0x140, 0x158, 0x3A2, 0x3B4 },
        maskConsumer = "5585..5596 NotRun;018F/012A/P2 not accessed", adaptive = "487B..48F5/ticks NotRun; RAM thresholds not inputs",
        schedule = "Snapshots->decision->fuel prefix->factor->217A->2194..2204; scripted routine ABI, not recovered scheduler",
        assumptions = Array.Empty<string>(), physicalRpmAvailable = false, stop = "BeforeInstruction2204" } });

    internal static RomImage Mutate(RomImage original, P28LimiterFuelMutation mutation)
    {
        RomImage child = mutation.Kind switch
        {
            P28LimiterFuelMutationKind.FixedCut => P28LimiterInspector.Mutate(original, new("fixed-context-cut", mutation.Value)),
            P28LimiterFuelMutationKind.FixedResume => P28LimiterInspector.Mutate(original, new("fixed-context-resume", mutation.Value)),
            P28LimiterFuelMutationKind.FuelCell => P28FuelMapInspector.Mutate(original, new(mutation.MapId!, mutation.Row!.Value, mutation.Column!.Value, checked((byte)mutation.Value))),
            _ => throw new ArgumentException("Closed mutation kind required.")
        };
        AdmitMutation(original, child, mutation); return child;
    }
    // Joint-image authority is internal and one-field-only; old public guards unchanged.
    internal static void AdmitMutation(RomImage original, RomImage child, P28LimiterFuelMutation mutation)
    {
        P28LimiterInspector.OperandGuard(original); P28LimiterInspector.OperandGuard(child);
        P28FuelMapInspector.LayoutGuard(original); P28FuelMapInspector.LayoutGuard(child);
        if (mutation.Kind == P28LimiterFuelMutationKind.FuelCell)
            P28FuelMapInspector.AdmitMutation(original, child, new(mutation.MapId!, mutation.Row!.Value, mutation.Column!.Value, checked((byte)mutation.Value)));
        else if (mutation.Kind is P28LimiterFuelMutationKind.FixedCut or P28LimiterFuelMutationKind.FixedResume)
            P28LimiterInspector.AdmitMutation(original, child, new(mutation.Kind == P28LimiterFuelMutationKind.FixedCut ? "fixed-context-cut" : "fixed-context-resume", mutation.Value));
        else throw new InvalidDataException("Foreign combined image.");
    }
    public static async Task<P28LimiterFuelReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28LimiterFuelScenario s, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        if (original.Span[0x60E5] != 0 || original.Span[0x60F8] != 0) throw new InvalidDataException("Require unchanged original fuel configuration.");
        var child = s.Mutation is null ? null : Mutate(original, s.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28LimiterFuelSequence>(); JsonElement contract = default; string version = "";
        foreach (var image in images)
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, s), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, s, response.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2n native evidence.", e); }
        }
        var comparisons = new List<P28LimiterFuelComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < s.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var ok = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    var thresholdEdit = s.Mutation!.Kind != P28LimiterFuelMutationKind.FuelCell;
                    bool? controls = !ok ? null : thresholdEdit ? a.Fuel!.Data0140 == b.Fuel!.Data0140 && a.Fuel.NativeFactor0158 == b.Fuel.NativeFactor0158 &&
                        a.Fuel.Correction == b.Fuel.Correction && a.Fuel.Component == b.Fuel.Component && a.Fuel.Corrected == b.Fuel.Corrected && a.Fuel.Store03b4 == b.Fuel.Store03b4 :
                        a.Request == b.Request && a.SelectedThreshold == b.SelectedThreshold && a.GateTaken == b.GateTaken && a.Fuel!.NativeFactor0158 == b.Fuel!.NativeFactor0158 && a.Fuel.Correction == b.Fuel.Correction;
                    if (ok) controls = controls == true && NumericControlHistory(a.Fuel!.Actual, b.Fuel!.Actual) &&
                        (thresholdEdit || Equal(a.Actual.GetProperty("stateAfterDecision"), b.Actual.GetProperty("stateAfterDecision")));
                    bool? rd = ok ? a.Request != b.Request : null; bool? gd = ok ? a.GateTaken != b.GateTaken : null;
                    bool? witness = !ok ? null : thresholdEdit ? controls == true && rd == true && gd == true && a.Fuel!.Corrected > 0 && a.Fuel.Store03a2 != b.Fuel!.Store03a2 :
                        controls == true && a.Fuel!.Data0140 != b.Fuel!.Data0140 && a.Fuel.Component != b.Fuel.Component && a.Fuel.Store03b4 != b.Fuel.Store03b4;
                    var effect = !ok ? "NotComparable" : controls == false ? "ControlMismatch" : witness == true ? thresholdEdit ? "ThresholdRequestGate03A2Changed" : a.GateTaken == true ? "FuelEffect03B4GateMasked03A2" : "FuelEffectBothStores" : "NoUnmaskedWitness";
                    comparisons.Add(new(sequences[p].ScratchPattern, i, controls, rd, gd, a.Fuel?.Store03a2, b.Fuel?.Store03a2, a.Fuel?.Store03b4, b.Fuel?.Store03b4, witness, effect));
                }
        IReadOnlyList<int> changed = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        var checksums = images.Select((image, i) => (object)new { image = i == 0 ? "A" : "B", arithmetic = P28NativeChecksumArithmetic.Calculate(image), scope = "Diagnostic only; no compensation/export" }).ToArray();
        return new(1, s.Purpose, original.Hash, profile.Id, s.Digest, version, s.Mutation, changed, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract, checksums);
    }

    internal static IReadOnlyList<P28LimiterFuelSequence> Analyze(RomImage image, P28LimiterFuelScenario s, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "limiterFuelSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2n execution/ownership contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign M2n rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        return AnalyzeShared(image, s, root, root.GetProperty("limiterFuelSequences"), id);
    }
    // Internal composition seam; no second CPU, no old top-level operation or relaxed public admission.
    internal static IReadOnlyList<P28LimiterFuelSequence> AnalyzeShared(RomImage image, P28LimiterFuelScenario s, JsonElement root, JsonElement sequences, string id,
        Func<int, int, byte, P28LimiterDecisionStep>? decisionModel = null, Action<int, int, byte>? finishModel = null,
        Func<int, int, int>? decisionEntryA = null, Func<int, int, byte>? source011b = null, ushort? initialPrevious03b4 = null,
        Func<int, int, byte>? producerMode012c = null, Func<int, int, byte>? mode012bBefore = null)
    {
        Require(sequences.GetArrayLength() == 3, "Joint scratch count differs.");
        var expected = new P28LimiterDecisionStep?[3, s.Calls.Count];
        var models = Enumerable.Range(0, 3).Select(_ => new P28LimiterModel(image.Span, new(s.InitialState.Data0124, s.InitialState.Data012b, 0, 0, s.InitialState.Data01d7, 0, 0))).ToArray();
        var fuelCount = sequences[0].GetProperty("checkpoints").EnumerateArray().Count(r => r.GetProperty("fuel").GetProperty("prefix").GetProperty("status").GetInt32() != 4);
        Require(sequences.EnumerateArray().All(seq => seq.GetProperty("checkpoints").EnumerateArray().Count(r => r.GetProperty("fuel").GetProperty("prefix").GetProperty("status").GetInt32() != 4) == fuelCount), "Scratch-dependent stage attempt counts differ.");
        IReadOnlyList<P28FuelFactorSequence>? fuels = null;
        if (fuelCount > 0)
        {
            var numeric = s.NumericScenario(fuelCount);
            var view = JsonSerializer.SerializeToElement(sequences.EnumerateArray().Select(seq => new
            {
                scratchPattern = seq.GetProperty("scratchPattern").GetInt32(),
                callerGate0124 = numeric.InitialState.CallerGate0124,
                producerMode012c = s.InitialState.ProducerMode012c,
                producerSelector012f = s.InitialState.ProducerSelector012f,
                checkpoints = seq.GetProperty("checkpoints").EnumerateArray().Take(fuelCount).Select(r => r.GetProperty("fuel")).ToArray()
            }).ToArray());
            fuels = P28FuelFactorValidator.AnalyzeFuelEvidence(image, numeric, root, view, id, (p, i, mode) =>
            {
                models[p].AcceptModeledFuelByte(mode); var decision = decisionModel is null ? models[p].StepDecision(s.Calls[i].RawPeriod, false, true) : decisionModel(p, i, mode); expected[p, i] = decision;
                return (decision.After.Data0124, decision.After.Data012B);
            }, (p, i, mode) => { models[p].AcceptModeledFuelByte(mode); finishModel?.Invoke(p, i, mode); }, initialPrevious03b4, producerMode012c, mode012bBefore);
        }
        var reports = new List<P28LimiterFuelSequence>();
        for (var p = 0; p < 3; p++)
        {
            var seq = sequences[p]; P28LimiterScenario.Shape(seq, "scratchPattern", "checkpoints"); var pattern = new[] { 0, 85, 170 }[p];
            Require(seq.GetProperty("scratchPattern").GetInt32() == pattern, "M2n scratch order differs."); var rows = seq.GetProperty("checkpoints"); Require(rows.GetArrayLength() == s.Calls.Count, "M2n call count differs.");
            var list = new List<P28LimiterFuelCheckpoint>(); var stopped = false;
            var previous = JsonSerializer.SerializeToElement(new { s.InitialState.Data0124, s.InitialState.Data012b, s.InitialState.Data01d7 }, JsonDefaults.Create());
            for (var i = 0; i < rows.GetArrayLength(); i++)
            {
                var r = rows[i]; P28LimiterScenario.Shape(r, "index", "status", "input", "inputWrites", "stateBefore", "stateAfterDecision", "stateAfter", "decisionEntry", "decisionExit", "transitionToDecisionWrites", "handoffToDecision", "decision", "decisionAccesses", "fuel");
                foreach (var key in new[] { "stateBefore", "stateAfterDecision", "stateAfter" }) P28LimiterScenario.Shape(r.GetProperty(key), "data0124", "data012b", "data01d7");
                if (mode012bBefore is not null) { var retained = JsonNode.Parse(previous.GetRawText())!; retained["data012b"] = mode012bBefore(p, i); previous = JsonSerializer.SerializeToElement(retained); }
                Require(r.GetProperty("index").GetInt32() == i && Equal(r.GetProperty("stateBefore"), previous), "M2n initial/shared history differs.");
                var status = r.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "M2n status differs."); var f = r.GetProperty("fuel");
                P28FuelFactorValidator.ValidateCheckpointShape(f, true, f.GetProperty("prefix").GetProperty("status").GetInt32() != 4);
                var decision = r.GetProperty("decision"); var access = Matrix(r.GetProperty("decisionAccesses"), 5, 384);
                P28FuelFactorCheckpoint? fuel = i < fuelCount ? fuels![p].Checkpoints[i] : null;
                P28LimiterDecisionStep? own = expected[p, i]; bool? request = null; bool? gate = null; ushort? threshold = null; var decisionDisposition = "NotRun";
                if (stopped)
                {
                    Require(status == 4 && r.GetProperty("input").ValueKind == JsonValueKind.Null && decision.ValueKind == JsonValueKind.Null && access.Length == 0 &&
                        r.GetProperty("inputWrites").GetArrayLength() == 0 && r.GetProperty("transitionToDecisionWrites").GetArrayLength() == 0 &&
                        r.GetProperty("handoffToDecision").ValueKind == JsonValueKind.Null && r.GetProperty("decisionEntry").ValueKind == JsonValueKind.Null && r.GetProperty("decisionExit").ValueKind == JsonValueKind.Null &&
                        Equal(r.GetProperty("stateBefore"), r.GetProperty("stateAfterDecision")) && Equal(r.GetProperty("stateBefore"), r.GetProperty("stateAfter")), "Terminal M2n suffix executed.");
                    ValidateFuelNotRun(f);
                    Require(f.GetProperty("inputWrites").GetArrayLength() == 0 && Equal(f.GetProperty("sourcesBefore"), f.GetProperty("sourcesAfter")), "Terminal suffix applied source snapshots.");
                }
                else
                {
                    Require(Equal(r.GetProperty("input"), JsonSerializer.SerializeToElement(s.Calls[i], JsonDefaults.Create())) && decision.ValueKind == JsonValueKind.Object, "Missing/native input differs.");
                    var input = Matrix(r.GetProperty("inputWrites"), 3, 32);
                    Require(input.Length == 23 && input[^1].SequenceEqual(new[] { 0xC4, 16, (int)s.Calls[i].RawPeriod }), "Raw-period snapshot differs.");
                    P28FuelFactorValidator.ValidateInputWrites(JsonSerializer.SerializeToElement(input.Take(22)), s.Calls[i].Fuel, true);
                    Require(Equal(r.GetProperty("transitionToDecisionWrites"), ExpectedContracts()[0].GetProperty("hostTransitionWrites")), "Hidden shared-bit initializer or decision ABI write.");
                    ValidateTransition(r.GetProperty("handoffToDecision"), r.GetProperty("decisionEntry"), r.GetProperty("transitionToDecisionWrites"), 0x1966, 0x20, 0x280);
                    if (own is null)
                    {
                        own = decisionModel is null ? models[p].StepDecision(s.Calls[i].RawPeriod, false, true) : decisionModel(p, i, r.GetProperty("stateBefore").GetProperty("data012b").GetByte());
                    }
                    var parsed = P28AcquisitionValidator.ParseStage(decision.GetProperty("result"), 96, 0, [], null)!;
                    var events = P28LimiterValidator.Matrix(decision, "events", 8); P28LimiterValidator.ValidateTrace(parsed, events, false);
                    decisionDisposition = Status(parsed.Status);
                    ValidateDecisionBoundary(r.GetProperty("decisionEntry"), r.GetProperty("decisionExit"), decision, parsed);
                    var entryA = decisionEntryA is not null ? decisionEntryA(p, i) : i == 0 ? pattern * 257 : fuels![p].Checkpoints[i - 1].Corrected!.Value;
                    Require(r.GetProperty("decisionEntry").GetProperty("accumulator").GetInt32() == entryA, "Host reloaded prior numeric result at decision entry.");
                    ValidateDecisionOracle(image, own!.Before, s.Calls[i].RawPeriod, entryA, r, parsed, own.Context == "Fixed", source011b?.Invoke(p, i));
                    Require(access.All(a => a[0] is >= 0x1966 and < 0x1A38 && a[1] is not (0x12A or 0x18F) && (decisionModel is not null || a[1] is not (0x1A4 or 0x1A6))), "Foreign mask/RAM/adaptive decision access.");
                    Require(access.Where(a => a[3] == 1).SelectMany(a => new[] { a[1], a[2], a[4] }).SequenceEqual(Matrix(decision.GetProperty("writes"), 3, 96).SelectMany(a => a)), "Decision native writes unjournaled.");
                    if (parsed.Status == 0)
                    {
                        Require(own is not null && fuel is not null, "Completed decision lacks modeled state or fuel attempt.");
                        ValidateDecision(image, s.Calls[i], r, own!); threshold = own!.Threshold; request = own.OverspeedRequest;
                        ValidatePrefixTransitions(r);
                        Require(status == f.GetProperty("status").GetInt32(), "M2n fuel/status differs.");
                        var after = r.GetProperty("stateAfter"); Require(after.GetProperty("data0124").GetByte() == own.After.Data0124 && after.GetProperty("data01d7").GetByte() == own.After.Data01D7 &&
                            after.GetProperty("data012b").GetByte() == f.GetProperty("modeAfter").GetByte(), "Fuel overwrote limiter gates/counter or split012B history.");
                        var fa = Matrix(f.GetProperty("accesses"), 5, 4096);
                        if (status == 0) { Require(SharedBitHandoffMatches(access.Concat(fa).ToArray(), own.After.Data0124), "Missing/stale native limiter bit generation to fuel gate."); gate = request; }
                    }
                    else
                    {
                        Require(status == parsed.Status && fuel is null, "Fuel executed after incomplete limiter decision."); ValidateFuelNotRun(f);
                        Require(Equal(f.GetProperty("sourcesAfter"), JsonSerializer.SerializeToElement(s.Calls[i].Sources, JsonDefaults.Create())) &&
                            Equal(f.GetProperty("inputWrites"), JsonSerializer.SerializeToElement(input.Take(22))) && f.GetProperty("modeAfter").GetByte() == r.GetProperty("stateAfterDecision").GetProperty("data012b").GetByte(), "Partial decision lost snapshots or combined mode history.");
                        Require(Equal(r.GetProperty("stateAfterDecision"), r.GetProperty("stateAfter")), "Shared state changed after incomplete decision.");
                    }
                    stopped = status != 0;
                }
                var disposition = status == 0 ? fuel?.Disposition ?? "Mismatch" : Status(status);
                list.Add(new(i, disposition, decisionDisposition, threshold, request, gate, decisionDisposition == "StrictMatch" ? own : null, fuel, r.Clone())); previous = r.GetProperty("stateAfter").Clone();
            }
            reports.Add(new(id, pattern, list.AsReadOnly()));
        }
        return reports.AsReadOnly();
    }

    private static string Status(int s) => s switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
    internal static bool NumericControlHistory(JsonElement a, JsonElement b)
    {
        foreach (var key in new[] { "sourcesBefore", "sourcesAfter", "hysteresisBefore", "hysteresisAfter", "modeBefore", "modeAfter" })
            if (!Equal(a.GetProperty(key), b.GetProperty(key))) return false;
        foreach (var key in new[] { "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "selector0127", "consumerFactor013f" })
            if (!Equal(a.GetProperty("prefix").GetProperty("stateAfter").GetProperty(key), b.GetProperty("prefix").GetProperty("stateAfter").GetProperty(key))) return false;
        return true;
    }
    internal static void ValidateFuelNotRun(JsonElement f)
    {
        Require(f.GetProperty("status").GetInt32() == 4 && f.GetProperty("input").ValueKind == JsonValueKind.Null && f.GetProperty("accesses").GetArrayLength() == 0 &&
            f.GetProperty("prefix").GetProperty("status").GetInt32() == 4 && f.GetProperty("factorStage").ValueKind == JsonValueKind.Null && f.GetProperty("stages").GetArrayLength() == 0, "Fuel suffix executed.");
        foreach (var key in new[] { "tailBoundaries", "boundaries", "transitionToFactorWrites", "transitionToAdditiveWrites" }) Require(f.GetProperty(key).GetArrayLength() == 0, "NotRun fuel has scripted execution.");
        foreach (var key in new[] { "handoff1350", "factorEntry", "factorExit", "callerEntry", "callerExit", "callerGate" }) Require(!f.TryGetProperty(key, out var value) || value.ValueKind == JsonValueKind.Null, "NotRun fuel has native boundary.");
        foreach (var key in new[] { "rpmAxes", "loadAxis", "selection", "lookup", "consumer" }) Require(f.GetProperty("prefix").GetProperty(key).ValueKind == JsonValueKind.Null, "NotRun prefix has native stage.");
        Require(Equal(f.GetProperty("prefix").GetProperty("stateBefore"), f.GetProperty("prefix").GetProperty("stateAfter")) && Equal(f.GetProperty("storesBefore"), f.GetProperty("storesAfter")) &&
            Equal(f.GetProperty("factor0158Before"), f.GetProperty("factor0158After")) && Equal(f.GetProperty("hysteresisBefore"), f.GetProperty("hysteresisAfter")), "NotRun fuel changed retained history.");
        Require(f.GetProperty("prefix").GetProperty("stateAfterInputs").ValueKind == JsonValueKind.Null && Equal(f.GetProperty("modeBefore"), f.GetProperty("modeAfter")), "NotRun fuel applied inputs or additive mode update.");
        foreach (var key in new[] { "nativeFactor0158", "correction", "component", "corrected", "store03a2", "store03b4" }) Require(f.GetProperty(key).ValueKind == JsonValueKind.Null, "Retained stores issued as new suffix outputs.");
    }
    private static void ValidateDecisionBoundary(JsonElement entry, JsonElement exit, JsonElement stage, P28AcquisitionStageResult parsed)
    {
        P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        Require(entry.GetProperty("pc").GetInt32() == 0x1966 && entry.GetProperty("psw").GetInt32() == 0x0DC9 && entry.GetProperty("lrb").GetInt32() == 0x20 &&
            entry.GetProperty("usp").GetInt32() == 0x280 && entry.GetProperty("ssp").GetInt32() == 0x7FE && exit.GetProperty("ssp").GetInt32() == 0x7FE && stage.GetProperty("sspAfter").GetInt32() == 0x7FE &&
            exit.GetProperty("pc").GetInt32() == parsed.StopPc && (parsed.Status != 0 || parsed.StopPc == 0x1A38), "Decision entry/bank/stack/exit differs.");
        P28FuelCalculationValidator.ValidateEventContinuity(Matrix(stage.GetProperty("events"), 8, 96), entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(), exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
    }
    private static void ValidateDecision(RomImage image, P28LimiterFuelCall call, JsonElement row, P28LimiterDecisionStep own)
    {
        var before = row.GetProperty("stateBefore"); var after = row.GetProperty("stateAfterDecision");
        Require(before.GetProperty("data0124").GetByte() == own.Before.Data0124 && before.GetProperty("data012b").GetByte() == own.Before.Data012B && before.GetProperty("data01d7").GetByte() == own.Before.Data01D7 &&
            after.GetProperty("data0124").GetByte() == own.After.Data0124 && after.GetProperty("data012b").GetByte() == own.After.Data012B && after.GetProperty("data01d7").GetByte() == own.After.Data01D7, "Independent shared decision state/counter differs.");
        var stage = row.GetProperty("decision"); var e = Matrix(stage.GetProperty("events"), 8, 96);
        Require(Equal(Matrix(stage.GetProperty("writes"), 3, 96), own.DecisionWrites), "Decision-only native writes differ.");
        var cmp = e.Where(v => v[0] == 0x197D).ToArray(); Require(cmp.Length == 1 && cmp[0][6] == call.RawPeriod && cmp[0][7] == own.Threshold &&
            ((cmp[0][5] & 0x8000) != 0) == own.OverspeedRequest && ((cmp[0][5] & 0x4000) != 0) == (call.RawPeriod == own.Threshold), "Wrong previous-state threshold/comparison/flags.");
        Require(e.Any(v => v[0] == 0x197C) == ((own.Before.Data0124 & 32) != 0) && e.Any(v => v[0] == 0x1974) == (own.Context != "Fixed") && e.Any(v => v[0] == 0x1977) == (own.Context != "Fixed") &&
            e.Any(v => v[0] == 0x1969 && v[3] == P28LimiterInspector.Word(image.Span, 0x196A)) && row.GetProperty("decisionExit").GetProperty("dp").GetInt32() == (own.Context == "Fixed" ? P28LimiterInspector.Word(image.Span, 0x1967) : own.Before.RamResume) &&
            e.Any(v => v[0] == 0x1980 && v[1] == (own.OverspeedRequest ? 0x19AC : 0x1982)), "Fixed immediate fetch/context/decision branch differs.");
        Require(e.Any(v => v[0] == 0x1A28) && (own.After.Data0124 & 16) == 0, "Missing native bit4 clearing.");
    }
    private static void ValidateDecisionOracle(RomImage image, P28LimiterState state, ushort raw, int entryA, JsonElement row, P28AcquisitionStageResult parsed, bool fixedSource = true, byte? source011b = null)
    {
        var own = P28LimiterDecisionEvidence.Build(image, state, raw, entryA, fixedSource, source011b); var stage = row.GetProperty("decision"); var exit = row.GetProperty("decisionExit");
        var events = Matrix(stage.GetProperty("events"), 8, 96); Require(events.Length <= own.Events.Count && events.SelectMany(e => e).SequenceEqual(own.Events.Take(events.Length).SelectMany(e => e)), "Independent limiter source/branch/flag journal differs.");
        var ac = events.Length == 0 ? 0 : own.AccessEnds[events.Length - 1]; var wc = events.Length == 0 ? 0 : own.WriteEnds[events.Length - 1];
        Require(Matrix(row.GetProperty("decisionAccesses"), 5, 384).SelectMany(a => a).SequenceEqual(own.Accesses.Take(ac).SelectMany(a => a)) &&
            Matrix(stage.GetProperty("writes"), 3, 96).SelectMany(w => w).SequenceEqual(own.Writes.Take(wc).SelectMany(w => w)), "Independent full limiter read/write footprint differs.");
        var extents = own.Events.Take(events.Length).SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).Distinct().Order().ToArray();
        Require(parsed.ExecutedInstructionBytes.SequenceEqual(extents) && (parsed.Status != 0 || events.Length == own.Events.Count), "Missing/skipped immediate fetch or decision instruction extent.");
        var after = row.GetProperty("stateAfterDecision"); var st = events.Length == 0 ? new[] { (int)state.Data0124, state.Data012B, state.Data01D7 } : own.StateEnds[events.Length - 1];
        Require(exit.GetProperty("dp").GetInt32() == (events.Length == 0 ? row.GetProperty("decisionEntry").GetProperty("dp").GetInt32() : own.DpEnds[events.Length - 1]), "Partial decision DP contradicts its native threshold load.");
        Require(after.GetProperty("data0124").GetInt32() == st[0] && after.GetProperty("data012b").GetInt32() == st[1] && after.GetProperty("data01d7").GetInt32() == st[2], "Partial decision state is not its completed native prefix.");
        foreach (var key in new[] { "x1", "x2", "registers", "lrb", "usp", "ssp" }) Require(Equal(row.GetProperty("decisionEntry").GetProperty(key), exit.GetProperty(key)), "Decision changed unused bank/pointer/stack carriers.");
    }
    internal static bool SharedBitHandoffMatches(int[][] a, byte gate)
    {
        var writes = a.Select((v, i) => (v, i)).Where(x => x.v[3] == 1 && x.v[1] == 0x124).ToArray();
        var read4 = a.Select((v, i) => (v, i)).Where(x => x.v[0] == 0x217A && x.v[3] == 0).ToArray();
        var read5 = a.Select((v, i) => (v, i)).Where(x => x.v[0] == 0x21F5 && x.v[3] == 0).ToArray();
        return writes.Any(x => x.v[0] == 0x1A23 && x.v[2] == 8 && (x.v[4] & 32) == (gate & 32)) && writes.Any(x => x.v[0] == 0x1A28 && x.v[2] == 8 && (x.v[4] & 16) == 0) &&
            writes.All(x => x.v[0] is 0x1A1E or 0x19C6 or 0x1A23 or 0x1A28 or 0x1A35) && writes.Length > 0 && writes[^1].v[4] == gate &&
            read4.Length == 1 && read5.Length == 1 && read4[0].i > writes[^1].i && read5[0].i > read4[0].i &&
            read4[0].v.SequenceEqual(new[] { 0x217A, 0x124, 8, 0, (int)gate }) && read5[0].v.SequenceEqual(new[] { 0x21F5, 0x124, 8, 0, (int)gate });
    }
    internal static void ValidateCaller(JsonElement row)
    {
        var entry = row.GetProperty("callerEntry"); var exit = row.GetProperty("callerExit"); var stage = row.GetProperty("callerGate");
        P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 1, 0, [], null)!;
        var e = Matrix(stage.GetProperty("events"), 8, 1); Require(r.Status == 0 && r.Error is null && r.Steps == 1 && r.StopPc == 0x2194 && r.ProgramReads.Count == 0 && r.UsedAssumptions.Count == 0 &&
            r.ExecutedInstructionBytes.SequenceEqual(new[] { 0x217A, 0x217B, 0x217C }) && e.Length == 1 && e[0][0] == 0x217A && e[0][1] == 0x2194 && e[0][2] == e[0][3] && e[0][4] == e[0][5] &&
            stage.GetProperty("writes").GetArrayLength() == 0 && Equal(exit, row.GetProperty("boundaries")[0]), "Caller217A was substituted/reset/bypassed.");
        P28FuelCalculationValidator.ValidateEventContinuity(e, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(), exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        foreach (var k in new[] { "accumulator", "psw", "lrb", "x1", "x2", "dp", "usp", "ssp", "registers" }) Require(Equal(entry.GetProperty(k), exit.GetProperty(k)), "Caller gate changed carriers.");
    }
    internal static void ValidateIncompleteCaller(JsonElement row, int status)
    {
        var stage = row.GetProperty("callerGate"); var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 1, 0, [], null)!;
        Require(status == r.Status && r.Status != 0 && r.Steps == 0 && r.StopPc == 0x217A && stage.GetProperty("events").GetArrayLength() == 0 &&
            stage.GetProperty("writes").GetArrayLength() == 0 && row.GetProperty("stages").GetArrayLength() == 0 && row.GetProperty("boundaries").GetArrayLength() == 0 &&
            Equal(row.GetProperty("callerEntry"), row.GetProperty("callerExit")), "Incomplete caller fabricated execution/output.");
        foreach (var key in new[] { "correction", "component", "corrected", "store03a2", "store03b4" }) Require(row.GetProperty(key).ValueKind == JsonValueKind.Null, "Caller suffix issued stale numeric outputs.");
    }
    private static void ValidateTransition(JsonElement before, JsonElement after, JsonElement writes, int pc, int lrb, int usp)
    {
        P28FuelFactorValidator.ValidateBoundary(before); P28FuelFactorValidator.ValidateBoundary(after);
        Require(after.GetProperty("pc").GetInt32() == pc && after.GetProperty("lrb").GetInt32() == lrb && after.GetProperty("psw").GetInt32() == 0x0DC9 &&
            after.GetProperty("usp").GetInt32() == usp && after.GetProperty("ssp").GetInt32() == 0x7FE && Equal(writes, JsonSerializer.SerializeToElement(new[] { new[] { 2, 16, lrb }, new[] { 4, 16, 0x0101 }, new[] { 0x8E, 16, usp } })), "Scripted ABI footprint/context differs.");
        foreach (var key in new[] { "accumulator", "x1", "x2", "dp", "ssp" }) Require(Equal(before.GetProperty(key), after.GetProperty(key)), "Scripted transition repaired native numeric/pointer state.");
        if (before.GetProperty("lrb").GetInt32() == lrb) Require(Equal(before.GetProperty("registers"), after.GetProperty("registers")), "Scripted bank words reset.");
    }
    private static void ValidatePrefixTransitions(JsonElement row)
    {
        var f = row.GetProperty("fuel"); var t = f.GetProperty("prefixTransitions"); var prefix = f.GetProperty("prefix");
        var entries = new[] { 0x0A0C, 0x0A62, 0x12FC }; var names = new[] { "rpmAxes", "loadAxis", "selection" };
        var count = names.Count(n => prefix.GetProperty(n).ValueKind == JsonValueKind.Object); Require(t.GetArrayLength() == count, "Unobserved scripted prefix transition.");
        for (var n = 0; n < count; n++)
        {
            P28LimiterScenario.Shape(t[n], "before", "after", "writes");
            ValidateTransition(t[n].GetProperty("before"), t[n].GetProperty("after"), t[n].GetProperty("writes"), entries[n], n == 2 ? 0x20 : 0x40, n == 2 ? 0x280 : 0x180);
            if (n == 0) Require(Equal(t[n].GetProperty("before"), row.GetProperty("decisionExit")), "Limiter-to-prefix continuity reset.");
            else
            {
                var prior = prefix.GetProperty(names[n - 1]); var e = Matrix(prior.GetProperty("events"), 8, 384);
                Require(t[n].GetProperty("before").GetProperty("pc").GetInt32() == prior.GetProperty("result").GetProperty("stopPc").GetInt32() &&
                    t[n].GetProperty("before").GetProperty("accumulator").GetInt32() == e[^1][3] && t[n].GetProperty("before").GetProperty("psw").GetInt32() == e[^1][5], "Prefix transition contradicts preceding native event.");
            }
        }
    }
}
