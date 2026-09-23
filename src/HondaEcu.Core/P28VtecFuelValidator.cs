using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed record P28VtecFuelCheckpoint(int Index, string Disposition, int Status, bool ConditionalDependency,
    bool? RequestP1, bool? RequestMirror0127, bool? Selector0127, bool? SelectorBefore,
    int? SelectedOrigin, string? SelectedMap, int? Lookup, int? Data0140, bool? ConsumerChanged,
    string SelectorCause, bool? ChangedByteRead, P28VtecPersistentState VtecState,
    IReadOnlyList<string> Differences, JsonElement? Witness);
public sealed record P28VtecFuelSequence(int ImageIndex, int ScratchPattern, int CompletedCalls, int StopCallIndex,
    IReadOnlyList<P28VtecFuelCheckpoint> Checkpoints);
public sealed record P28VtecFuelComparison(int ScratchPattern, int Index, string Comparison,
    bool? ChangedByteRead, bool? RequestChanged, bool? SelectorChanged, bool? MapChanged,
    bool? LookupChanged, bool? ConsumerChanged, bool? ControlValid, string Effect);
public sealed record P28VtecFuelValidationReport(int FormatVersion, string Purpose, RomHash OriginalHash,
    RomHash? MutatedHash, string ProfileId, string ScenarioDigest, string RunnerVersion,
    IReadOnlyList<string> AllowedAssumptions, P28VtecFuelMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28VtecFuelSequence> Sequences, IReadOnlyList<P28VtecFuelComparison> Comparisons)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition is "Mismatch" or "ExecutionError" or "BudgetExceeded") ||
        Comparisons.Any(c => c.ControlValid == false);
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1InteractiveAcceptance => "NotRun";
    public string D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string CompleteCaptureToFuel => "NotRun: scripted caller fragments precede the unbroken decision-to-fuel tail.";
    public string FirmwareOutput => "None; mutation B is in memory only.";
}

/// <summary>Independent decision and fuel histories; native checkpoints never feed the expected model.</summary>
public static class P28VtecFuelValidator
{
    public const string Operation = "vtecFuelChain";
    private static readonly int[] Patterns = [0, 85, 170];
    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events, int Ssp);

    public static IReadOnlyList<string> ValidateAssumptions(IEnumerable<string> assumptions)
    {
        var values = assumptions.ToArray();
        if (values.Length > 1 || values.Distinct(StringComparer.Ordinal).Count() != values.Length ||
            values.Any(value => value != P28StatefulModel.SubbOffAssumption))
            throw new ArgumentException("Only the exact conditional SUBB encoding permission is available to M2f.");
        return Array.AsReadOnly(values);
    }

    public static object CreateRequest(RomImage original, RomImage? mutated, P28VtecFuelScenario scenario,
        IEnumerable<string>? assumptions = null) => new
        {
            protocolVersion = 1,
            operation = Operation,
            images = (mutated is null ? [new { id = "baseline", rom = original.ToArray().Select(b => (int)b).ToArray() }]
                : new[] { new { id = "baseline", rom = original.ToArray().Select(b => (int)b).ToArray() },
                    new { id = "mutated", rom = mutated.ToArray().Select(b => (int)b).ToArray() } }),
            scratchPatterns = Patterns,
            allowAssumptions = ValidateAssumptions(assumptions ?? []),
            vtecFuelChain = new { formatVersion = 1, scenario.InitialVtec, scenario.InitialFuel, scenario.Calls, scenario.TraceCallIndexes },
        };

    public static async Task<P28VtecFuelValidationReport> ExecuteAsync(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, string runner, P28VtecFuelScenario scenario,
        IEnumerable<string>? assumptions = null, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28FuelMapInspector.LayoutGuard(original);
        var allowed = ValidateAssumptions(assumptions ?? []);
        RomImage? mutated = null;
        if (scenario.Mutation is { } edit)
        {
            if (original.Span[edit.Offset] == edit.Value)
                throw new InvalidDataException("M2f in-memory B edit must change its one code-owned byte.");
            var bytes = original.ToArray();
            bytes[edit.Offset] = edit.Value;
            mutated = RomImage.FromBytes(bytes);
        }
        var changed = scenario.Mutation is null || mutated is null || original.Span[scenario.Mutation.Offset] == mutated.Span[scenario.Mutation.Offset]
            ? Array.Empty<int>() : new[] { scenario.Mutation.Offset };
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(original, mutated, scenario, allowed), options, cancellationToken).ConfigureAwait(false);
        try { return Analyze(original, mutated, profile, scenario, allowed, changed, response.Response); }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2f shared-state runner response.", ex); }
    }

    internal static P28VtecFuelValidationReport Analyze(RomImage original, RomImage? mutated, RomProfile profile,
        P28VtecFuelScenario scenario, IReadOnlyList<string> allowed, IReadOnlyList<int> changed, JsonElement root)
    {
        _ = SliceRunnerIdentity.Validate(root, Operation);
        var contracts = root.GetProperty("entryContracts");
        Require(contracts.GetArrayLength() == 1 && contracts[0].GetProperty("id").GetString() == Operation &&
            contracts[0].GetProperty("hostWritesAfterDecisionEntry").GetArrayLength() == 0 &&
            !contracts[0].GetProperty("perCallMapId").GetBoolean() &&
            Equal(contracts[0].GetProperty("unbrokenTail"), new[] { new[] { 0x122C, 0x12FC }, new[] { 0x12FC, 0x1340 },
                new[] { 0x1340, 0x1347 }, new[] { 0x1347, 0x1350 } }) &&
            contracts[0].GetProperty("fixedCallerGates").GetProperty("snapshot011CBit5").GetBoolean() == false &&
            contracts[0].GetProperty("physicalRpmAvailable").GetBoolean() == false,
            "M2f runner contract is not the reviewed shared-state chain.");
        foreach (var name in new[] { "compactRows", "thresholdRows", "diagnostics" })
            Require(root.GetProperty(name).GetArrayLength() == 0, "Foreign task observations present.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result present.");
        var sequenceRows = root.GetProperty("vtecFuelSequences");
        Require(sequenceRows.GetArrayLength() == (mutated is null ? 3 : 6), "Missing independent image/scratch sequences.");
        var sequences = new List<P28VtecFuelSequence>();
        var seen = new HashSet<(int, int)>();
        foreach (var sequenceRow in sequenceRows.EnumerateArray())
        {
            var imageIndex = sequenceRow.GetProperty("imageIndex").GetInt32();
            var pattern = sequenceRow.GetProperty("scratchPattern").GetInt32();
            Require(imageIndex is 0 or 1 && (imageIndex == 0 || mutated is not null) && Patterns.Contains(pattern) &&
                seen.Add((imageIndex, pattern)), "Duplicate/unknown M2f sequence.");
            var image = imageIndex == 0 ? original : mutated!;
            var decisionModel = new P28StatefulModel(image.Span, scenario.InitialVtec);
            var f = scenario.InitialFuel;
            var fuelInitial = new P28FuelMapState(f.LoadIndex, f.Map0RpmIndex, f.Map1RpmIndex,
                f.LoadFraction, f.Map0RpmFraction, f.Map1RpmFraction, scenario.InitialVtec.Data0127,
                f.ConsumerFactor013f, f.ConsumerOutput0140);
            var fuelModel = new P28FuelMapModel(image, fuelInitial);
            var rows = sequenceRow.GetProperty("checkpoints");
            Require(rows.GetArrayLength() == scenario.Calls.Count, "Incomplete M2f sequence/NotRun suffix.");
            var checkpoints = new List<P28VtecFuelCheckpoint>();
            var previousVtec = scenario.InitialVtec; var previousFuel = fuelInitial;
            var stopped = false; var stopIndex = -1; var complete = 0; var conditional = false; var firstErrorWitness = false;
            foreach (var row in rows.EnumerateArray())
            {
                var index = checkpoints.Count;
                Require(row.GetProperty("index").GetInt32() == index, "M2f event order differs.");
                var status = row.GetProperty("status").GetInt32();
                Require(status is >= 0 and <= 4, "Unknown M2f status.");
                var beforeVtec = State<P28VtecPersistentState>(row, "vtecBefore");
                var afterVtec = State<P28VtecPersistentState>(row, "vtecAfter");
                var beforeFuel = State<P28FuelMapState>(row, "fuelBefore");
                var afterFuel = State<P28FuelMapState>(row, "fuelAfter");
                var differences = new List<string>();
                void Check(bool okay, string reason) { if (!okay) differences.Add(reason); }
                Check(beforeVtec == previousVtec && beforeFuel == previousFuel &&
                    beforeVtec.Data0127 == beforeFuel.Selector0127, "Shared state/history continuity");
                var inputElement = row.GetProperty("input");
                var decision = ParseStage(row.GetProperty("decision"), "decision", allowed, scenario.TraceCallIndexes.Contains(index));
                var tickWrites = Matrix(row.GetProperty("tickWrites"), 3, 128);
                var tickRuns = Matrix(row.GetProperty("tickRuns"), 5, 128);
                var rpm = ParseStage(row.GetProperty("rpmAxes"), "rpmAxes", [], scenario.TraceCallIndexes.Contains(index));
                var load = ParseStage(row.GetProperty("loadAxis"), "loadAxis", [], scenario.TraceCallIndexes.Contains(index));
                var selection = ParseStage(row.GetProperty("selection"), "selection", [], scenario.TraceCallIndexes.Contains(index));
                var lookup = ParseStage(row.GetProperty("lookup"), "lookup", [], scenario.TraceCallIndexes.Contains(index));
                var consumer = ParseStage(row.GetProperty("consumer"), "consumer", [], scenario.TraceCallIndexes.Contains(index));
                if (stopped)
                {
                    Require(status == 4 && inputElement.ValueKind == JsonValueKind.Null && decision is null && rpm is null &&
                        load is null && selection is null && lookup is null && consumer is null &&
                        tickWrites.Length == 0 && tickRuns.Length == 0 &&
                        row.GetProperty("selectedOrigin").ValueKind == JsonValueKind.Null &&
                        row.GetProperty("consumerOutput0140").ValueKind == JsonValueKind.Null &&
                        beforeVtec == afterVtec && beforeFuel == afterFuel, "Terminal suffix applied inputs or fabricated fuel output.");
                }
                else
                {
                    Require(inputElement.ValueKind != JsonValueKind.Null &&
                        Equal(inputElement, scenario.Calls[index]), "M2f raw input echo differs.");
                    var input = scenario.Calls[index];
                    if (decision is not null)
                    {
                        var expectedDecision = decisionModel.Step(input.Decision, allowed.Contains(P28StatefulModel.SubbOffAssumption));
                        conditional |= decision.Result.UsedAssumptions.Count > 0;
                        Check(expectedDecision.Before == beforeVtec && expectedDecision.After == afterVtec,
                            "Independent VTEC state/request/selector history");
                        Check(Equal(tickWrites, expectedDecision.TickWrites) &&
                            tickRuns.Length == 2 * (input.Decision.FastTicks + input.Decision.SlowTicks) &&
                            tickRuns.All(t => t[3] == 0 && t[2] == (t[0] == 0x5BD0 ? 0x5BD9 : 0x3CF3)),
                            "Native counter bodies/writes and independent counter history");
                        Check(Equal(FilterPersistent(decision.Writes), expectedDecision.DecisionWrites), "Ordered native decision stores");
                        var gateEvents = decision.Events.Where(e => P28StatefulModel.GateDefinitions.Any(g => g.Pc == e[0])).ToArray();
                        var gates = P28StatefulValidator.ProjectGates(gateEvents);
                        Check(Equal(gates, expectedDecision.Gates) && gateEvents.Select(e => e[0]).SequenceEqual(expectedDecision.ExecutedGatePcs),
                            "Decision gates/thresholds and order");
                        Check(Equal(P28StatefulValidator.ProjectThresholds(gates), expectedDecision.Thresholds),
                            "Code-owned threshold reads");
                        Check(decision.Result.Status == expectedDecision.Status && decision.Result.StopPc == expectedDecision.StopPc &&
                            Equal(decision.Result.UsedAssumptions, expectedDecision.UsedAssumptions), "Decision status/assumption/exit");
                    }
                    Check(row.GetProperty("conditionalDependency").GetBoolean() == conditional,
                        "Cumulative conditional dependency was cleared or fabricated");
                    Check(status == (consumer?.Result.Status ?? lookup?.Result.Status ?? selection?.Result.Status ??
                        decision?.Result.Status ?? load?.Result.Status ?? rpm?.Result.Status ?? status),
                        "Chain status contradicts its last executed native stage");
                    if (status == 0)
                    {
                        Require(rpm is not null && load is not null && decision is not null && selection is not null && lookup is not null && consumer is not null,
                            "Completed M2f chain lacks a stage.");
                        var expectedFuel = fuelModel.StepFromNativeSelector(new(index, input.RawLoad, input.RawMap0Rpm, input.RawMap1Rpm),
                            decisionModel.State.Data0127);
                        Check(expectedFuel.Before == beforeFuel && expectedFuel.After == afterFuel && afterFuel.Selector0127 == afterVtec.Data0127,
                            "Independent fuel caches/fractions and shared selector");
                        Check(Reads(rpm!).SequenceEqual(expectedFuel.Map0Rpm.OrderedProgramReads.Concat(expectedFuel.Map1Rpm.OrderedProgramReads)) &&
                            Reads(load!).SequenceEqual(expectedFuel.Load.OrderedProgramReads), "Native axis reads/positions");
                        Check(Reads(selection!).Count == 0 && Reads(lookup!).SequenceEqual(expectedFuel.Operands.OrderedProgramReads) &&
                            Reads(consumer!).Count == 0, "Ordered native map-cell/multiplier reads");
                        var origin = Number(row, "selectedOrigin"); var result = Number(row, "lookupResult");
                        var output = Number(row, "consumerOutput0140");
                        Check(origin == expectedFuel.SelectedOrigin && result == expectedFuel.Operands.LookupResult &&
                            output == expectedFuel.Consumer.Output, "ROM-selected origin, lookup and DATA0140");
                        Check(lookup!.Events.Any(e => e[0] == 0x5A0C && e[3] == expectedFuel.Operands.ScaledCells[0]) &&
                            lookup.Events.Any(e => e[0] == 0x5A13 && e[3] == expectedFuel.Operands.ScaledCells[1]) &&
                            lookup.Events.Any(e => e[0] == 0x5A18 && e[3] == expectedFuel.Operands.ScaledCells[3]) &&
                            lookup.Events.Any(e => e[0] == 0x5A1E && e[3] == expectedFuel.Operands.ScaledCells[2]),
                            "Native cell × multiplier intermediates");
                        Check(consumer!.Writes.Any(w => w[0] == 0x140 && w[1] == 16 && w[2] == expectedFuel.Consumer.Output),
                            "Actual DATA0140 store");
                        var boundary = row.GetProperty("boundary12fc"); var entry = row.GetProperty("selectionEntry");
                        Check(boundary.ValueKind != JsonValueKind.Null && Equal(boundary, entry) &&
                            boundary.GetProperty("pc").GetInt32() == 0x12FC && decision!.Events.Length > 0 && selection!.Events.Length > 0 &&
                            decision.Events[^1][1] == 0x12FC && decision.Events[^1][3] == boundary.GetProperty("accumulator").GetInt32() &&
                            decision.Events[^1][5] == boundary.GetProperty("psw").GetInt32() &&
                            selection.Events[0][0] == 0x12FC && selection.Events[0][2] == boundary.GetProperty("accumulator").GetInt32() &&
                            selection.Events[0][4] == boundary.GetProperty("psw").GetInt32(),
                            "Unbroken PC/accumulator/PSW/LRB/USP/register/stack boundary 12FC");
                        Check(Number(row, "selectorBeforeReader131a") == afterVtec.Data0127 &&
                            selection!.Events.Any(e => e[0] == 0x131A) &&
                            selection.Writes.All(w => w[0] != 0x127) &&
                            row.GetProperty("requestP1").GetBoolean() == expectedDecisionRequest() &&
                            row.GetProperty("requestMirror0127").GetBoolean() == ((afterVtec.Data0127 & 4) != 0) &&
                            row.GetProperty("selector0127").GetBoolean() == ((afterVtec.Data0127 & 2) != 0),
                            "Producer DATA0127 → reader131A; request/mirror/selector distinction");
                        Check(new[] { rpm!, load!, decision!, selection!, lookup!, consumer! }.All(s => s.Result.Status == 0 && s.Ssp == 0x7FE) &&
                            selection!.Result.StopPc == 0x1340 && lookup!.Result.StopPc == 0x1347 && consumer!.Result.StopPc == 0x1350,
                            "Local stage exits and stack balance");
                        complete++;
                        bool expectedDecisionRequest() => (decisionModel.State.P1OutputData & 1) != 0;
                    }
                    else
                    {
                        Require(selection is null || status != 1 || decision?.Result.Status != 1,
                            "Fuel suffix executed after strict unresolved decision.");
                        stopIndex = index; stopped = true;
                    }
                }
                var selectorBefore = (beforeVtec.Data0127 & 2) != 0;
                var selectorAfter = status == 0 ? (afterVtec.Data0127 & 2) != 0 : (bool?)null;
                var priorSelector = selectorBefore;
                int[]? transitionWriter = null;
                foreach (var write in decision?.Writes.Where(w => w[0] == 0x127) ?? [])
                {
                    var nextSelector = (write[2] & 2) != 0;
                    if (nextSelector != priorSelector) transitionWriter = write;
                    priorSelector = nextSelector;
                }
                var nativeBranch = decision?.Events.Any(e => e[0] == 0x12F9) == true ? "12F9 set-path" :
                    decision?.Events.Any(e => e[0] == 0x12DF) == true ? "12DF clear-path" : "decision path";
                var cause = status != 0 ? "NotRun/unresolved" : transitionWriter is not null ?
                    $"native {nativeBranch} changed DATA0127.1 at store value {transitionWriter[2]}" :
                    decision?.Writes.Any(w => w[0] == 0x127) == true ? $"native {nativeBranch} stored but retained DATA0127.1" :
                    $"native {nativeBranch} retained selector from prior native/initial state";
                var disposition = differences.Count > 0 ? "Mismatch" : status switch
                {
                    0 when conditional => "ConditionalMatch",
                    0 => "StrictMatch",
                    1 => "Unresolved",
                    2 => "ExecutionError",
                    3 => "BudgetExceeded",
                    _ => "NotRun",
                };
                bool? changedByteRead = null;
                if (scenario.Mutation is { } mutation && status == 0)
                    changedByteRead = (mutation.Kind == "fuelCell" ? lookup?.Result.ProgramReads : decision?.Result.ProgramReads)?.Contains(mutation.Offset);
                var witness = scenario.TraceCallIndexes.Contains(index) || (differences.Count > 0 && !firstErrorWitness) ? row.Clone() : (JsonElement?)null;
                firstErrorWitness |= differences.Count > 0;
                checkpoints.Add(new(index, disposition, status, conditional,
                    status == 0 ? (afterVtec.P1OutputData & 1) != 0 : null,
                    status == 0 ? (afterVtec.Data0127 & 4) != 0 : null,
                    selectorAfter, status == 0 ? selectorBefore : null,
                    Number(row, "selectedOrigin"), status == 0 ? (afterVtec.Data0127 & 2) == 0 ? "map_0" : "map_1" : null,
                    Number(row, "lookupResult"), Number(row, "consumerOutput0140"),
                    status == 0 ? beforeFuel.ConsumerOutput0140 != afterFuel.ConsumerOutput0140 : null,
                    cause, changedByteRead, afterVtec,
                    differences.AsReadOnly(), witness));
                previousVtec = afterVtec; previousFuel = afterFuel;
            }
            Require(sequenceRow.GetProperty("completedCalls").GetInt32() == complete &&
                sequenceRow.GetProperty("stopCallIndex").GetInt32() == stopIndex,
                "M2f sequence counts/stop differ from completed checkpoints.");
            sequences.Add(new(imageIndex, pattern, complete, stopIndex, checkpoints.AsReadOnly()));
        }
        var comparisons = Compare(scenario, sequences);
        return new(1, "native-vtec-to-fuel-map-selection-chain", original.Hash, mutated?.Hash, profile.Id,
            scenario.Digest, root.GetProperty("runnerVersion").GetString()!, allowed, scenario.Mutation,
            changed, sequences.AsReadOnly(), comparisons);
    }

    private static IReadOnlyList<P28VtecFuelComparison> Compare(P28VtecFuelScenario scenario, IReadOnlyList<P28VtecFuelSequence> sequences)
    {
        if (scenario.Mutation is null) return [];
        var rows = new List<P28VtecFuelComparison>();
        foreach (var pattern in Patterns)
        {
            var a = sequences.Single(s => s.ImageIndex == 0 && s.ScratchPattern == pattern);
            var b = sequences.Single(s => s.ImageIndex == 1 && s.ScratchPattern == pattern);
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                var x = a.Checkpoints[i]; var y = b.Checkpoints[i];
                var comparable = x.Status == 0 && y.Status == 0 && x.Differences.Count == 0 && y.Differences.Count == 0;
                bool? changedRead = comparable ? y.ChangedByteRead : null;
                bool? controlValid = !comparable ? null : scenario.Mutation.Kind == "fuelCell" ?
                    x.VtecState == y.VtecState && x.RequestP1 == y.RequestP1 &&
                    x.RequestMirror0127 == y.RequestMirror0127 && x.Selector0127 == y.Selector0127 &&
                    x.SelectedMap == y.SelectedMap && x.SelectedOrigin == y.SelectedOrigin &&
                    (changedRead == true || (x.Lookup == y.Lookup && x.Data0140 == y.Data0140)) : true;
                var effect = !comparable ? "NotComparable" : controlValid == false ? "ControlFailure" : x.Selector0127 != y.Selector0127 ? "NativeSelectionChanged" :
                    x.Data0140 != y.Data0140 ? "ConsumerChangedWithoutSelectionChange" : "MaskedOrControl";
                rows.Add(new(pattern, i, comparable ? "Comparable" : "NotComparable", changedRead,
                    comparable ? x.RequestP1 != y.RequestP1 : null, comparable ? x.Selector0127 != y.Selector0127 : null,
                    comparable ? x.SelectedMap != y.SelectedMap : null, comparable ? x.Lookup != y.Lookup : null,
                    comparable ? x.Data0140 != y.Data0140 : null, controlValid, effect));
            }
        }
        return rows.AsReadOnly();
    }

    private static Stage? ParseStage(JsonElement element, string name, IReadOnlyList<string> allowed, bool traced)
    {
        if (element.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(element, "result", "writes", "events", "sspAfter");
        var budget = name switch
        {
            "decision" => 512,
            "rpmAxes" => 384,
            "loadAxis" or "lookup" => 192,
            "selection" or "consumer" => 64,
            _ => throw new InvalidDataException("Unknown M2f stage.")
        };
        var result = P28AcquisitionValidator.ParseStage(element.GetProperty("result"), budget, 0, allowed,
            name == "decision" ? P28StatefulModel.SubbOffAssumption : null)!;
        var writes = Matrix(element.GetProperty("writes"), 3, 1024);
        var events = Matrix(element.GetProperty("events"), 8, budget);
        var ssp = element.GetProperty("sspAfter").GetInt32();
        Require(ssp is >= 0 and <= 65535 && events.Length == result.Steps &&
            result.Trace.Count == (traced ? Math.Min(128, result.Steps) : 0), "M2f stage journal/trace is incomplete.");
        var pc = name switch
        {
            "decision" => 0x122C,
            "rpmAxes" => 0x0A0C,
            "loadAxis" => 0x0A62,
            "selection" => 0x12FC,
            "lookup" => 0x1340,
            _ => 0x1347
        };
        foreach (var e in events) { Require(e[0] == pc, "M2f stage event path is discontinuous."); pc = e[1]; }
        Require(result.StopPc == pc, "M2f stage stop PC contradicts journal.");
        return new(result, writes, events, ssp);
    }
    private static int[][] FilterPersistent(int[][] writes) => writes.Where(w => new[] { 0x131, 0x127, 0x198, 0x1D8, 0x1D9, 0x1DF, 0xF3, 0x22 }.Contains(w[0])).ToArray();
    private static int[][] Matrix(JsonElement e, int width, int maximum)
    {
        Require(e.GetArrayLength() <= maximum, "Unbounded M2f journal.");
        return e.EnumerateArray().Select(row =>
        {
            var values = row.EnumerateArray().Select(value => value.GetInt32()).ToArray();
            Require(values.Length == width && values.All(value => value is >= 0 and <= 65536), "Malformed M2f journal row.");
            return values;
        }).ToArray();
    }
    private static T State<T>(JsonElement row, string field) => row.GetProperty(field).Deserialize<T>(P28StatefulScenario.Options)!;
    private static int? Number(JsonElement row, string field) => row.GetProperty(field).ValueKind == JsonValueKind.Null ? null : row.GetProperty(field).GetInt32();
    private static IReadOnlyList<int> Reads(Stage stage) => stage.Result.ProgramReads;
    private static bool Equal<T>(T a, object b) => JsonNode.DeepEquals(JsonSerializer.SerializeToNode(a, JsonDefaults.Create(false)), JsonSerializer.SerializeToNode(b, JsonDefaults.Create(false)));
    private static void Require(bool value, string message) { if (!value) throw new SliceProcessException(SliceProcessFailure.Protocol, message); }
}
