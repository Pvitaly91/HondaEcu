using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28FuelAdditiveCheckpoint(int Index, string Disposition, string PrefixDisposition, int? SelectedOrigin,
    int? Data0140, int? Correction, int? Component, int? Corrected, int? Store03a2, int? Store03b4,
    P28FuelAdditiveProjection? Expected, IReadOnlyList<string> Differences, JsonElement Actual);
public sealed record P28FuelAdditiveSequence(string Image, int ScratchPattern, IReadOnlyList<P28FuelAdditiveCheckpoint> Checkpoints);
public sealed record P28FuelAdditiveComparison(int ScratchPattern, int Index, bool? CellRead, bool? Controls,
    int? Data0140A, int? Data0140B, int? ComponentA, int? ComponentB, int? CorrectedA, int? CorrectedB, bool? Witness, string Effect);
public sealed record P28FuelAdditiveReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, P28FuelMapMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28FuelAdditiveSequence> Sequences, IReadOnlyList<P28FuelAdditiveComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Corrected is not null),
        Witnesses = Comparisons.Count(c => c.Witness == true),
        Effects = Comparisons.GroupBy(c => c.Effect).ToDictionary(g => g.Key, g => g.Count())
    };
    public string SoftwareRole => "Native signed word correction in er3/X2; separately saturated component; corrected A/er3 and stores03A2/03B4";
    public string CallerBoundary => "1350->2194 scripted; 2194->2204 native with near calls; stop-before2204";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time units and degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; optional one-cell B exists in memory only";
}

public static class P28FuelAdditiveValidator
{
    public const string Operation = "fuelAdditiveCorrectionChain";
    public static object CreateRequest(RomImage image, P28FuelAdditiveScenario s) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        fuelAdditiveCorrectionChain = new { formatVersion = 1, initialState = s.InitialState.Fuel.Fuel, s.InitialState.CallerGate0124, s.InitialState.Mode012b, s.Calls, s.TraceCallIndexes }
    };
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixEntries = new[] { 0x0A0C, 0x0A62, 0x12FC }, continuousFuelTail = new[] { 0x12FC, 0x1350 },
        scriptedHandoff = new[] { 0x1350, 0x2194 }, nativeTail = new[] { 0x2194, 0x2204 }, checkpoints = new[] { 0x21DB, 0x21F2 }, lrb = 0x20, psw = 0x0101, usp = 0x280, ssp = 0x7FE,
        hostTransitionWrites = new[] { new[] { 2, 16, 0x20 }, new[] { 4, 16, 0x0101 }, new[] { 0x8E, 16, 0x280 } },
        helpers = new[] { new[] { 0x596C, 0x5991 }, new[] { 0x5958, 0x596B } }, vector4 = new[] { 0x30, 0x5958, 0x21F5 }, stackRange = new[] { 0x7FE, 0x800 },
        nativeSource = new[] { 0x134E, 0x140, 16 }, nativeReader = new[] { 0x21DB, 0x140, 16 }, softwareStores = new[] { 0x3A2, 0x3B4 }, initialSelectorOnly = true,
        gate217A = "StaticPrecondition; bypass NotEvaluated", sourceWords = new[] { 0x142, 0x144, 0x146, 0x14A, 0x14C, 0x158 }, sourceBytes = new[] { 0x148, 0x149, 0xF2 },
        source0144Mask = 255, upper0145 = "CodeOwnedZero; no recovered high-byte producer",
        nativeModeMask = new[] { 0x12B, 8 }, traceLimit = 8, assumptions = Array.Empty<string>(), units = "raw; physical units unknown" } });

    public static async Task<P28FuelAdditiveReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28FuelAdditiveScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28FuelMapInspector.LayoutGuard(original);
        if (original.Span[0x60E5] != 0 || original.Span[0x60F8] != 0) throw new InvalidDataException("M2l requires unchanged exact-original helper/reader configuration.");
        var child = scenario.Mutation is null ? null : P28FuelMapInspector.Mutate(original, scenario.Mutation);
        if (child is not null) P28FuelMapInspector.AdmitMutation(original, child, scenario.Mutation!);
        var sequences = new List<P28FuelAdditiveSequence>(); JsonElement contract = default; string version = "";
        foreach (var image in child is null ? new[] { original } : new[] { original, child })
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2l native evidence.", e); }
        }
        var comparisons = new List<P28FuelAdditiveComparison>();
        if (child is not null)
        {
            var offset = P28FuelMapContract.CellOffset(scenario.Mutation!.MapId, scenario.Mutation.Row, scenario.Mutation.Column);
            for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var comparable = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    bool? read = comparable ? b.Actual.GetProperty("prefix").GetProperty("lookup").GetProperty("result").GetProperty("programReads").EnumerateArray().Any(n => n.GetInt32() == offset) : null;
                    bool? controls = comparable ? a.SelectedOrigin == b.SelectedOrigin && a.Correction == b.Correction &&
                        Equal(a.Actual.GetProperty("sourcesAfter"), b.Actual.GetProperty("sourcesAfter")) && a.Actual.GetProperty("modeAfter").GetByte() == b.Actual.GetProperty("modeAfter").GetByte() &&
                        Equal(a.Actual.GetProperty("prefix").GetProperty("position"), b.Actual.GetProperty("prefix").GetProperty("position")) : null;
                    bool? witness = comparable ? read == true && controls == true && a.Data0140 != b.Data0140 && a.Component != b.Component && a.Corrected != b.Corrected && a.Store03b4 != b.Store03b4 : null;
                    var effect = !comparable ? "NotComparable" : controls == false ? "ControlMismatch" : read != true ? "CellNotRead" : a.Data0140 == b.Data0140 ? "ReadMaskedBefore0140" : a.Component == b.Component ?
                        (scenario.Calls[i].Sources.Factor0158 == 0 ? "M2kZeroFactor" : a.Expected!.Scaling.Saturated && b.Expected!.Scaling.Saturated ? "M2kSaturation" : "M2kTruncation") :
                        a.Corrected == b.Corrected ? (a.Corrected == 0 ? "ApplicationLowerClamp" : "ApplicationUpperClamp") : "NativeCorrectedStoresChanged";
                    comparisons.Add(new(sequences[p].ScratchPattern, i, read, controls, a.Data0140, b.Data0140, a.Component, b.Component, a.Corrected, b.Corrected, witness, effect));
                }
        }
        IReadOnlyList<int> changed = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, "fuel-additive-native-software-test", original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, changed, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }

    internal static IReadOnlyList<P28FuelAdditiveSequence> Analyze(RomImage image, P28FuelAdditiveScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "fuelAdditiveSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2l entry/ownership contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign M2l rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty("fuelAdditiveSequences"); Require(seq.GetArrayLength() == 3, "M2l scratch count differs.");
        var count = seq[0].GetProperty("checkpoints").EnumerateArray().Count(r => r.GetProperty("prefix").GetProperty("status").GetInt32() != 4);
        Require(count > 0, "Missing attempted native prefix.");
        var map = (scenario.InitialState.Fuel.Selector0127 & 2) == 0 ? "map_0" : "map_1";
        // Numeric/history analysis adapter only; never runs the old top-level task.
        var prefixScenario = P28FuelMapScenario.FixedSelectorPrefix(scenario.InitialState.Fuel.Fuel,
            scenario.Calls.Take(count).Select(c => new P28FuelMapCall(c.Index, map, c.RawLoad, c.RawMap0Rpm, c.RawMap1Rpm)).ToArray());
        var view = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = P28FuelMapValidator.Operation,
            runnerVersion = root.GetProperty("runnerVersion").GetString(),
            upstreamCommit = root.GetProperty("upstreamCommit").GetString(),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            entryContracts = P28FuelMapValidator.ExpectedContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            fuelMapSequences = seq.EnumerateArray().Select(s => new { scratchPattern = s.GetProperty("scratchPattern").GetInt32(), checkpoints = s.GetProperty("checkpoints").EnumerateArray().Take(count).Select(r => r.GetProperty("prefix")).ToArray() }).ToArray()
        });
        var prefixes = P28FuelMapValidator.AnalyzeImage(image, prefixScenario, new(view, ""), id);
        var result = new List<P28FuelAdditiveSequence>();
        for (var p = 0; p < 3; p++)
        {
            var s = seq[p]; P28LimiterScenario.Shape(s, "scratchPattern", "callerGate0124", "checkpoints"); var pattern = new[] { 0, 85, 170 }[p];
            Require(s.GetProperty("scratchPattern").GetInt32() == pattern && s.GetProperty("callerGate0124").GetByte() == scenario.InitialState.CallerGate0124, "M2l scratch/gate differs.");
            var rows = s.GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "M2l event count differs.");
            var reports = new List<P28FuelAdditiveCheckpoint>(); var stopped = false; var mode = scenario.InitialState.Mode012b; var sources = new P28FuelAdditiveSources(0, 0, 0, 0, 0, 0, 0, 0, 0);
            int[] stores = [pattern * 257, pattern * 257]; JsonElement previous = default;
            for (var i = 0; i < rows.GetArrayLength(); i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "input", "prefix", "handoff1350", "hostTransitionWrites", "tailBoundaries", "boundaries", "stages", "accesses", "sourcesBefore", "sourcesAfter", "modeBefore", "modeAfter", "storesBefore", "storesAfter", "correction", "component", "corrected", "store03a2", "store03b4");
                var prefix = row.GetProperty("prefix"); var stages = row.GetProperty("stages"); var boundaries = row.GetProperty("boundaries");
                var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4 && row.GetProperty("index").GetInt32() == i, "M2l index/status differs.");
                Require(Equal(row.GetProperty("sourcesBefore"), JsonSerializer.SerializeToElement(sources, JsonDefaults.Create())) && row.GetProperty("modeBefore").GetByte() == mode &&
                    row.GetProperty("storesBefore").EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(stores), "M2l history was reseeded.");
                if (previous.ValueKind != JsonValueKind.Undefined) Require(Equal(prefix.GetProperty("stateBefore"), previous), "M2l retained fuel history reset.");
                var differences = new List<string>(); P28FuelAdditiveProjection? expected = null; int? origin = null; int? lookup = null; var disposition = "NotRun";
                var accesses = Matrix(row.GetProperty("accesses"), 5, 4096); Require(accesses.All(a => a[0] <= 65535 && a[1] < 4096 && a[2] is 8 or 16 && a[3] is 0 or 1 && a[4] < (a[2] == 8 ? 256 : 65536)), "Malformed native M2l access.");
                if (stopped)
                {
                    Require(status == 4 && row.GetProperty("input").ValueKind == JsonValueKind.Null && prefix.GetProperty("status").GetInt32() == 4 && stages.GetArrayLength() == 0 && boundaries.GetArrayLength() == 0 && accesses.Length == 0 &&
                        row.GetProperty("hostTransitionWrites").GetArrayLength() == 0 && row.GetProperty("tailBoundaries").GetArrayLength() == 0 && row.GetProperty("handoff1350").ValueKind == JsonValueKind.Null && Equal(prefix.GetProperty("stateBefore"), prefix.GetProperty("stateAfter")), "M2l terminal suffix executed.");
                    foreach (var key in new[] { "stateAfterInputs", "rpmAxes", "loadAxis", "selection", "lookup", "consumer", "selectedOrigin", "position", "lookupResult", "consumerOutput" }) Require(prefix.GetProperty(key).ValueKind == JsonValueKind.Null, "Terminal prefix executed.");
                    Require(Equal(row.GetProperty("sourcesBefore"), row.GetProperty("sourcesAfter")) && Equal(row.GetProperty("storesBefore"), row.GetProperty("storesAfter")) && row.GetProperty("modeAfter").GetByte() == mode, "Terminal state changed.");
                }
                else
                {
                    Require(i < count && Equal(row.GetProperty("input"), JsonSerializer.SerializeToElement(scenario.Calls[i], JsonDefaults.Create())), "M2l input differs.");
                    sources = scenario.Calls[i].Sources; Require(Equal(row.GetProperty("sourcesAfter"), JsonSerializer.SerializeToElement(sources, JsonDefaults.Create())), "External source overlap/overwrite.");
                    var ownPrefix = prefixes.Sequences[p].Checkpoints[i]; differences.AddRange(ownPrefix.Differences); disposition = ownPrefix.Disposition; origin = ownPrefix.ActualSelectedOrigin; lookup = ownPrefix.ActualConsumerOutput;
                    if (ownPrefix.Disposition == "StrictMatch")
                    {
                        Require(stages.GetArrayLength() is >= 1 and <= 3 && boundaries.GetArrayLength() == stages.GetArrayLength() * 2, "Missing/unbounded M2l stages."); ValidateSeams(row);
                        var ownLookup = (ushort)ownPrefix.Expected!.Consumer.Output; expected = P28FuelAdditiveModel.Project(ownLookup, sources, mode, scenario.InitialState.CallerGate0124);
                        var b = boundaries[0]; Require(b.GetProperty("accumulator").GetInt32() == ownLookup, "Native prefix A not its own lookup.");
                        // Untouched initial registers are canaries, not expected operands.
                        var oracle = P28FuelAdditiveEvidence.Build(0, ownLookup, sources, mode, scenario.InitialState.CallerGate0124, ownLookup, 0x0DC9, Word(b, 0), Word(b, 1), Word(b, 2), Word(b, 3), stores[1]);
                        var nextMode = mode; var nextStores = stores.ToArray();
                        for (var n = 0; n < stages.GetArrayLength(); n++)
                        {
                            if (n > 0) oracle = P28FuelAdditiveEvidence.Build(n, ownLookup, sources, mode, scenario.InitialState.CallerGate0124,
                                oracle.Accumulator, oracle.Psw, oracle.Er0, oracle.Er1, oracle.Er2, oracle.Er3, stores[1]);
                            var stageResult = ValidateStage(stages[n], boundaries[n * 2], boundaries[n * 2 + 1], n, oracle, accesses);
                            var accessCount = stageResult.Steps == 0 ? 0 : oracle.AccessEnds[stageResult.Steps - 1];
                            foreach (var write in oracle.Accesses.Take(accessCount).Where(a => a[3] == 1))
                            { if (write[1] == 0x12B) nextMode = (byte)write[4]; if (write[1] == 0x3A2) nextStores[0] = write[4]; if (write[1] == 0x3B4) nextStores[1] = write[4]; }
                            Require(stageResult.Status == 0 || n == stages.GetArrayLength() - 1, "Suffix executed after unresolved M2l stage.");
                            if (stageResult.Status == 0)
                            {
                                var exit = boundaries[n * 2 + 1]; Require(exit.GetProperty("accumulator").GetInt32() == oracle.Accumulator && exit.GetProperty("psw").GetInt32() == oracle.Psw &&
                                    Word(exit, 0) == oracle.Er0 && Word(exit, 1) == oracle.Er1 && Word(exit, 2) == oracle.Er2 && Word(exit, 3) == oracle.Er3, "M2l aliases/native registers differ from independent path.");
                                Require(exit.GetProperty("x1").GetInt32() == b.GetProperty("x1").GetInt32() && exit.GetProperty("x2").GetInt32() == expected.CorrectionWord, "M2l correction X2 lifetime or untouched X1 differs.");
                                Require(exit.GetProperty("dp").GetInt32() == (n == 2 ? 0x3B4 : b.GetProperty("dp").GetInt32()), "M2l DP lifetime differs.");
                                if (n == 0) Require(oracle.Er3 == expected.CorrectionWord && row.GetProperty("correction").GetInt32() == expected.CorrectionWord && oracle.Mode == expected.ModeAfter, "Correction producer differs.");
                                if (n == 1) { P28FuelCalculationValidator.ValidateNumbers(stages[n], accesses, exit, expected.Scaling, Nullable(row, "component"), oracle.Psw & 0x2000); Require(oracle.Er3 == expected.CorrectionWord, "Scaling destroyed correction."); }
                                if (n == 2) Require(Nullable(row, "corrected") == expected.Corrected && Nullable(row, "store03a2") == expected.Store03a2 && Nullable(row, "store03b4") == expected.Store03b4 && oracle.Er2 == expected.Scaling.Output, "Application/stores or er2 lifetime differ.");
                            }
                        }
                        var last = stages[stages.GetArrayLength() - 1].GetProperty("result"); Require(status == last.GetProperty("status").GetInt32() && (status != 0 || stages.GetArrayLength() == 3), "M2l overall status differs.");
                        var reader = stages.GetArrayLength() > 1 && stages[1].GetProperty("events").GetArrayLength() > 0;
                        Require(P28FuelCalculationValidator.HandoffMatches(accesses, ownLookup, reader), "M2l lookup generation/word provenance differs.");
                        mode = nextMode; stores = nextStores;
                    }
                    else Require(status == prefix.GetProperty("status").GetInt32() && stages.GetArrayLength() == 0 && boundaries.GetArrayLength() == 0 && row.GetProperty("handoff1350").ValueKind == JsonValueKind.Null && row.GetProperty("hostTransitionWrites").GetArrayLength() == 0 && row.GetProperty("modeAfter").GetByte() == mode && row.GetProperty("storesAfter").EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(stores), "M2l tail executed after incomplete prefix.");
                }
                for (var n = 0; n < 3; n++) if (stages.GetArrayLength() <= n || stages[n].GetProperty("result").GetProperty("status").GetInt32() != 0)
                        foreach (var key in n == 0 ? new[] { "correction" } : n == 1 ? new[] { "component" } : new[] { "corrected", "store03a2", "store03b4" }) Require(Nullable(row, key) is null, "M2l stale/nonexecuted output.");
                Require(row.GetProperty("modeAfter").GetByte() == mode && row.GetProperty("storesAfter").EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(stores), "M2l retained mode/stores differ.");
                var final = differences.Count > 0 ? "Mismatch" : status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                reports.Add(new(i, final, disposition, origin, lookup, Nullable(row, "correction"), Nullable(row, "component"), Nullable(row, "corrected"), Nullable(row, "store03a2"), Nullable(row, "store03b4"), expected, differences.AsReadOnly(), ReportRow(row, scenario.TraceCallIndexes.Contains(i))));
                stopped |= status != 0; previous = prefix.GetProperty("stateAfter");
            }
            result.Add(new(id, pattern, reports.AsReadOnly()));
        }
        return result.AsReadOnly();
    }
    internal static void ValidateSeams(JsonElement row)
    {
        var b = row.GetProperty("boundaries"); var h = row.GetProperty("handoff1350"); var tails = row.GetProperty("tailBoundaries");
        Require(tails.GetArrayLength() == 5 && Equal(tails[0], tails[1]) && Equal(tails[2], tails[3]) && Equal(tails[4], h), "Native12FC..1350 tail reset.");
        Require(h.GetProperty("pc").GetInt32() == 0x1350 && b[0].GetProperty("pc").GetInt32() == 0x2194 && b[0].GetProperty("psw").GetInt32() == 0x0DC9 &&
            b[0].GetProperty("lrb").GetInt32() == 0x20 && b[0].GetProperty("usp").GetInt32() == 0x280 && b[0].GetProperty("ssp").GetInt32() == 0x7FE, "M2l scripted entry differs.");
        foreach (var k in new[] { "accumulator", "x1", "x2", "dp", "ssp", "registers" }) Require(Equal(h.GetProperty(k), b[0].GetProperty(k)), "Host injected/reset native operands.");
        Require(Equal(row.GetProperty("hostTransitionWrites"), ExpectedContracts()[0].GetProperty("hostTransitionWrites")), "Hidden host transition writes.");
        for (var n = 2; n < b.GetArrayLength(); n += 2) Require(Equal(b[n - 1], b[n]), "Producer/scaling/application seam reset.");
        foreach (var boundary in b.EnumerateArray())
        {
            P28LimiterScenario.Shape(boundary, "pc", "accumulator", "psw", "dd", "lrb", "x1", "x2", "dp", "usp", "ssp", "registers");
            Require(boundary.GetProperty("dd").GetBoolean() == ((boundary.GetProperty("psw").GetInt32() & 0x1000) != 0), "M2l boundary DD contradicts PSW.");
        }
    }
    private static P28AcquisitionStageResult ValidateStage(JsonElement stage, JsonElement entry, JsonElement exit, int n, P28FuelAdditiveOracle own, int[][] accesses)
    {
        P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter"); var budget = new[] { 96, 32, 48 }[n];
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), budget, 0, [], null)!; var events = Matrix(stage.GetProperty("events"), 8, budget); var writes = Matrix(stage.GetProperty("writes"), 3, budget);
        P28FuelAdditiveEvidence.RequireEventPrefix(stage, own); Require(events.Length == r.Steps && r.Trace.Count == r.Steps && (r.Status != 0 || events.Length == own.Events.Count), "M2l missing execution events.");
        P28FuelCalculationValidator.ValidateEventContinuity(events, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(), exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        for (var i = 0; i < events.Length; i++) Require(r.Trace[i].GetProperty("pc").GetInt32() == events[i][0] && r.Trace[i].GetProperty("nextPc").GetInt32() == events[i][1] && r.Trace[i].GetProperty("accumulator").GetInt32() == events[i][3] && r.Trace[i].GetProperty("psw").GetInt32() == events[i][5], "M2l trace contradicts journal.");
        var extents = own.Events.Take(events.Length).SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).Distinct().Order().ToArray();
        Require(r.ExecutedInstructionBytes.SequenceEqual(extents) && r.StopPc == (events.Length == 0 ? entry.GetProperty("pc").GetInt32() : events[^1][1]) && exit.GetProperty("pc").GetInt32() == r.StopPc, "M2l exact path extent/exit differs.");
        Require(writes.Length <= own.Writes.Count && writes.SelectMany(v => v).SequenceEqual(own.Writes.Take(writes.Length).SelectMany(v => v)) && (r.Status != 0 || writes.Length == own.Writes.Count), "M2l ordered native writes differ.");
        Require(r.UsedAssumptions.Count == 0 && r.ProgramReads.All(a => n == 2 && a is 0x30 or 0x31) && (r.Status != 0 || r.ProgramReads.SequenceEqual(n == 2 ? new[] { 0x30, 0x31 } : [])), "M2l vector/foreign program read differs.");
        var pcs = events.Select(e => e[0]).ToHashSet(); var sourceReads = accesses.Where(a => pcs.Contains(a[0]) && a[3] == 0 && a[1] is 0x140 or 0x142 or 0x144 or 0x146 or 0x148 or 0x149 or 0x14A or 0x14C or 0x158 or 0xF2).ToArray();
        var native = accesses.Where(a => pcs.Contains(a[0])).ToArray(); var accessCount = events.Length == 0 ? 0 : own.AccessEnds[events.Length - 1];
        Require(native.SelectMany(v => v).SequenceEqual(own.Accesses.Take(accessCount).SelectMany(v => v)), "M2l full native register/stack/data journal differs.");
        var registerEnd = events.Length == 0 ? Enumerable.Range(0, 4).Select(i => Word(entry, i)).ToArray() : own.RegisterEnds[events.Length - 1];
        Require(Enumerable.Range(0, 4).All(i => Word(exit, i) == registerEnd[i]) && exit.GetProperty("ssp").GetInt32() == (events.Length == 0 ? 0x7FE : own.StackEnds[events.Length - 1]), "M2l partial/completed aliases or stack were forged.");
        Require(sourceReads.SelectMany(v => v).SequenceEqual(own.SourceReads.Where(v => pcs.Contains(v[0])).SelectMany(v => v)), "M2l source footprint/value differs.");
        Require(exit.GetProperty("lrb").GetInt32() == 0x20 && exit.GetProperty("usp").GetInt32() == 0x280 && exit.GetProperty("dd").GetBoolean() == ((exit.GetProperty("psw").GetInt32() & 0x1000) != 0) &&
            stage.GetProperty("sspAfter").GetInt32() == exit.GetProperty("ssp").GetInt32() && exit.GetProperty("ssp").GetInt32() is 0x7FC or 0x7FE && (r.Status != 0 || exit.GetProperty("ssp").GetInt32() == 0x7FE), "M2l stack/bank/DD differs.");
        if (r.Status == 0)
        {
            foreach (var ret in n == 0 ? new[] { 0x21BE, 0x21C4 } : n == 2 ? new[] { 0x21F5 } : []) Require(accesses.Count(a => a[1] == 0x7FE && a[2] == 16 && a[3] == 1 && a[4] == ret) == 1 && accesses.Count(a => a[1] == 0x7FE && a[2] == 16 && a[3] == 0 && a[4] == ret) == 1, "M2l native near-call return footprint differs.");
            if (n == 2) Require(accesses.Any(a => a.SequenceEqual(new[] { 0x2201, 0x3B4, 16, 0, own.Er0 })), "M2l actual previous-store reader missing.");
        }
        return r;
    }
    private static int Word(JsonElement b, int n) { var r = b.GetProperty("registers"); Require(r.GetArrayLength() == 8, "M2l register bank shape."); return r[n * 2].GetByte() | r[n * 2 + 1].GetByte() << 8; }
    private static int? Nullable(JsonElement r, string key) => r.GetProperty(key).ValueKind == JsonValueKind.Null ? null : r.GetProperty(key).GetInt32();
    private static int[][] Matrix(JsonElement v, int width, int limit) { Require(v.GetArrayLength() <= limit, "Unbounded M2l journal."); return v.EnumerateArray().Select(r => { var a = r.EnumerateArray().Select(n => n.GetInt32()).ToArray(); Require(a.Length == width && a.All(n => n is >= 0 and <= 65536), "Malformed M2l journal."); return a; }).ToArray(); }
    private static JsonElement ReportRow(JsonElement row, bool trace)
    {
        if (trace) return row.Clone(); var node = JsonNode.Parse(row.GetRawText())!;
        foreach (var name in new[] { "rpmAxes", "loadAxis", "selection", "lookup", "consumer" }) if (node["prefix"]?[name]?["result"] is JsonObject p) p["trace"] = new JsonArray();
        foreach (var stage in node["stages"]!.AsArray()) stage!["result"]!["trace"] = new JsonArray();
        return JsonSerializer.SerializeToElement(node);
    }
}
