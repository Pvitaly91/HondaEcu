using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28FuelCalculationCheckpoint(int Index, string Disposition, string PrefixDisposition,
    int? SelectedOrigin, int? Lookup, int? Data0140, int? NativeRead0140, int? Factor0158,
    ulong? Product, int? Output, P28FuelCalculationProjection? Expected, IReadOnlyList<string> Differences, JsonElement Actual);
public sealed record P28FuelCalculationSequence(string Image, int ScratchPattern, int CallerGate0124, IReadOnlyList<P28FuelCalculationCheckpoint> Checkpoints);
public sealed record P28FuelCalculationComparison(int ScratchPattern, int Index, bool? CellRead, bool? Controls,
    int? Data0140A, int? Data0140B, int? OutputA, int? OutputB, bool? Witness, string Effect);
public sealed record P28FuelCalculationReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, P28FuelMapMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28FuelCalculationSequence> Sequences, IReadOnlyList<P28FuelCalculationComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        NativeRuns = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Output is not null),
        Witnesses = Comparisons.Count(c => c.Witness == true),
        Effects = Comparisons.GroupBy(c => c.Effect).ToDictionary(g => g.Key, g => g.Count())
    };
    public string SoftwareRole => "Raw scaled/saturated fuel component in er2; static reader 227A; not final electrical pulse width";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time units and degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; optional one-cell B exists in memory only";
    public string StrictM2i => "Blocked; M2k does not resolve 47 81";
}

public static class P28FuelCalculationValidator
{
    public const string Operation = "fuelCalculationChain";
    public static object CreateRequest(RomImage image, P28FuelCalculationScenario scenario) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        fuelCalculationChain = new { formatVersion = 1, initialState = scenario.InitialState.Fuel, scenario.Calls, scenario.TraceCallIndexes }
    };
    public static async Task<P28FuelCalculationReport> ExecuteAsync(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, string runner, P28FuelCalculationScenario scenario,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28FuelMapInspector.LayoutGuard(original);
        if (original.Span[0x60E5] != 0) throw new InvalidDataException("M2k requires the exact-original optional-helper bypass.");
        var child = scenario.Mutation is null ? null : P28FuelMapInspector.Mutate(original, scenario.Mutation);
        if (child is not null) P28FuelMapInspector.AdmitMutation(original, child, scenario.Mutation!);
        var sequences = new List<P28FuelCalculationSequence>();
        JsonElement contract = default;
        foreach (var image in child is null ? new[] { original } : new[] { original, child })
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = response.Response.GetProperty("entryContracts").Clone(); }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2k fuel calculation evidence.", e); }
        }
        var comparisons = new List<P28FuelCalculationComparison>();
        if (child is not null)
        {
            var offset = P28FuelMapContract.CellOffset(scenario.Mutation!.MapId, scenario.Mutation.Row, scenario.Mutation.Column);
            for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i];
                    var comparable = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    bool? read = comparable ? b.Actual.GetProperty("prefix").GetProperty("lookup").GetProperty("result").GetProperty("programReads").EnumerateArray().Any(n => n.GetInt32() == offset) : null;
                    // Produced outputs may diverge; axes, selector and the external operand must remain controlled.
                    bool? controls = comparable ? a.SelectedOrigin == b.SelectedOrigin && a.Factor0158 == b.Factor0158 &&
                        Equal(a.Actual.GetProperty("prefix").GetProperty("position"), b.Actual.GetProperty("prefix").GetProperty("position")) &&
                        a.Actual.GetProperty("prefix").GetProperty("stateAfter").GetProperty("selector0127").GetByte() == b.Actual.GetProperty("prefix").GetProperty("stateAfter").GetProperty("selector0127").GetByte() : null;
                    bool? witness = comparable ? read == true && controls == true && a.Lookup != b.Lookup && a.Data0140 != b.Data0140 && a.Product != b.Product && a.Output != b.Output : null;
                    var effect = !comparable ? "NotComparable" : controls == false ? "ControlMismatch" : read != true ? "CellNotRead" : a.Data0140 == b.Data0140 ? "ReadMaskedBefore0140" :
                        a.Output == b.Output ? (a.Factor0158 == 0 ? "DownstreamZeroFactor" : a.Expected!.Saturated && b.Expected!.Saturated ? "DownstreamSaturation" : "DownstreamTruncation") : "NativeOutputChanged";
                    comparisons.Add(new(sequences[p].ScratchPattern, i, read, controls, a.Data0140, b.Data0140, a.Output, b.Output, witness, effect));
                }
        }
        IReadOnlyList<int> changed = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, "fuel-calculation-native-software-test", original.Hash, profile.Id, scenario.Digest,
            SliceRunnerIdentity.CurrentVersion, scenario.Mutation, changed, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixEntries = new[] { 0x0A0C, 0x0A62, 0x12FC }, continuousFuelTail = new[] { 0x12FC, 0x1350 },
        scriptedHandoff = new[] { 0x1350, 0x21DB }, downstreamExit = 0x21F2, lrb = 0x20, psw = 0x0101, usp = 0x280, ssp = 0x7FE,
        hostTransitionWrites = new[] { new[] { 2, 16, 0x20 }, new[] { 4, 16, 0x0101 }, new[] { 0x8E, 16, 0x280 } },
        nativeSource = new[] { 0x134E, 0x140, 16 }, nativeReader = new[] { 0x21DB, 0x140, 16 }, externalOperand = new[] { 0x158, 16 },
        nativeResult = new[] { 0x21F1, 0x104, 16 }, staticReader = 0x227A, initialSelectorOnly = true,
        fixedInitialCallerGate = new { address = 0x124, clearMask = 0x10, execution = "StaticCompatibilityOnly" },
        perEventInputs = new[] { 0x238, 0xC2, 0xBF, 0x158 }, traceLimit = 8, assumptions = Array.Empty<string>(),
        state = "OneCpuRamPerImageScratchSequence", units = "raw; physical fuel/time units unknown" } });

    internal static IReadOnlyList<P28FuelCalculationSequence> Analyze(RomImage image, P28FuelCalculationScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "fuelCalculationSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation);
        Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2k entry/ownership contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign M2k rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty("fuelCalculationSequences"); Require(seq.GetArrayLength() == 3, "M2k scratch count differs.");
        // Reuse the complete M2a numeric/history/journal validator on a view of
        // actually attempted prefixes. This is an analysis adapter, NOT a second
        // native run, not a DATA0140 input and not the old per-event selector task.
        var prefixCount = seq[0].GetProperty("checkpoints").EnumerateArray().Count(r => r.GetProperty("prefix").GetProperty("status").GetInt32() != 4);
        Require(prefixCount > 0, "M2k has no attempted prefix.");
        var fixedMap = (scenario.InitialState.Selector0127 & 2) == 0 ? "map_0" : "map_1";
        var prefixScenario = P28FuelMapScenario.FixedSelectorPrefix(scenario.InitialState.Fuel,
            scenario.Calls.Take(prefixCount).Select(c => new P28FuelMapCall(c.Index, fixedMap, c.RawLoad, c.RawMap0Rpm, c.RawMap1Rpm)).ToArray());
        var prefixResponse = JsonSerializer.SerializeToElement(new
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
            fuelMapSequences = seq.EnumerateArray().Select(s => new
            {
                scratchPattern = s.GetProperty("scratchPattern").GetInt32(),
                checkpoints = s.GetProperty("checkpoints").EnumerateArray().Take(prefixCount).Select(r => r.GetProperty("prefix").Clone()).ToArray()
            }).ToArray()
        });
        var prefixReport = P28FuelMapValidator.AnalyzeImage(image, prefixScenario, new(prefixResponse, ""), id);
        var reports = new List<P28FuelCalculationSequence>();
        for (var p = 0; p < 3; p++)
        {
            var sequence = seq[p]; P28LimiterScenario.Shape(sequence, "scratchPattern", "callerGate0124", "checkpoints");
            Require(sequence.GetProperty("callerGate0124").GetInt32() == (new[] { 0, 85, 170 }[p] & ~0x10), "M2k once-only caller gate mask differs.");
            Require(sequence.GetProperty("scratchPattern").GetInt32() == new[] { 0, 85, 170 }[p], "M2k scratch order differs.");
            var rows = sequence.GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "M2k event count differs.");
            var results = new List<P28FuelCalculationCheckpoint>(); var stopped = false; var previousFactor = 0; JsonElement previousState = default;
            for (var i = 0; i < rows.GetArrayLength(); i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "input", "prefix", "handoff1350", "downstreamEntry", "downstream", "downstreamExit", "accesses", "hostTransitionWrites", "tailBoundaries", "factor0158Before", "factor0158After", "output");
                Require(row.GetProperty("index").GetInt32() == i && row.GetProperty("factor0158Before").GetInt32() == previousFactor, "M2k event/factor history discontinuity.");
                var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Unknown M2k status.");
                var prefix = row.GetProperty("prefix"); var after = prefix.GetProperty("stateAfter");
                int? output = NullableInt(row, "output"); P28FuelCalculationProjection? expected = null;
                int? source = null; int? read = null; int? factor = null; int? origin = null; int? lookup = null;
                var differences = new List<string>(); string prefixDisposition = "NotRun";
                if (previousState.ValueKind != JsonValueKind.Undefined) Require(Equal(prefix.GetProperty("stateBefore"), previousState), "M2k retained RAM history reset.");
                if (stopped)
                {
                    Require(status == 4 && row.GetProperty("input").ValueKind == JsonValueKind.Null && prefix.GetProperty("status").GetInt32() == 4 &&
                        output is null && row.GetProperty("downstream").ValueKind == JsonValueKind.Null && row.GetProperty("handoff1350").ValueKind == JsonValueKind.Null &&
                        row.GetProperty("downstreamEntry").ValueKind == JsonValueKind.Null && row.GetProperty("downstreamExit").ValueKind == JsonValueKind.Null &&
                        row.GetProperty("hostTransitionWrites").GetArrayLength() == 0 && row.GetProperty("accesses").GetArrayLength() == 0 &&
                        row.GetProperty("tailBoundaries").GetArrayLength() == 0 && row.GetProperty("factor0158After").GetInt32() == previousFactor && Equal(prefix.GetProperty("stateBefore"), after), "M2k terminal suffix applied inputs or claimed stale output.");
                    foreach (var name in new[] { "stateAfterInputs", "rpmAxes", "loadAxis", "selection", "lookup", "consumer", "selectedOrigin", "position", "lookupResult", "consumerOutput" })
                        Require(prefix.GetProperty(name).ValueKind == JsonValueKind.Null, "Executed prefix in M2k terminal suffix.");
                }
                else
                {
                    Require(i < prefixCount && Equal(row.GetProperty("input"), JsonSerializer.SerializeToElement(scenario.Calls[i], JsonDefaults.Create())), "M2k actual inputs differ.");
                    Require(row.GetProperty("factor0158After").GetInt32() == scenario.Calls[i].Factor0158, "External word operand was changed natively or overridden.");
                    var prefixRow = prefixReport.Sequences[p].Checkpoints[i]; prefixDisposition = prefixRow.Disposition; differences.AddRange(prefixRow.Differences);
                    origin = prefixRow.ActualSelectedOrigin; lookup = prefixRow.ActualLookupResult; source = prefixRow.ActualConsumerOutput;
                    var accesses = Matrix(row.GetProperty("accesses"), 5, 4096);
                    Require(accesses.All(a => a[0] <= ushort.MaxValue && a[1] < 4096 && a[2] is 8 or 16 &&
                        a[3] is 0 or 1 && a[4] < (a[2] == 8 ? 256 : 65536)), "Invalid native access width/address/value.");
                    var downstream = row.GetProperty("downstream");
                    if (prefixRow.Disposition == "StrictMatch")
                    {
                        Require(downstream.ValueKind == JsonValueKind.Object && source is not null, "Completed prefix has no attempted downstream.");
                        ValidateSeams(row);
                        expected = P28FuelCalculationModel.Project((ushort)prefixRow.Expected!.Consumer.Output, scenario.Calls[i].Factor0158);
                        var result = ValidateDownstream(downstream, row.GetProperty("downstreamEntry"), row.GetProperty("downstreamExit"));
                        Require(status == result.Status, "M2k status differs from downstream.");
                        var nativeRead = accesses.SingleOrDefault(a => a[0] == 0x21DB && a[1] == 0x140 && a[2] == 16 && a[3] == 0);
                        if (nativeRead is not null) read = nativeRead[4];
                        factor = scenario.Calls[i].Factor0158;
                        Require(HandoffMatches(accesses, source!.Value, result.Steps > 0), "DATA0140 generation/word store/read or intervening write differs.");
                        if (status == 0) ValidateNumbers(downstream, accesses, row.GetProperty("downstreamExit"), expected, output);
                        else Require(output is null, "Unexecuted M2k output was not null.");
                    }
                    else
                    {
                        Require(status == prefix.GetProperty("status").GetInt32() && downstream.ValueKind == JsonValueKind.Null && output is null &&
                            row.GetProperty("handoff1350").ValueKind == JsonValueKind.Null && row.GetProperty("hostTransitionWrites").GetArrayLength() == 0, "Downstream ran after incomplete prefix.");
                    }
                }
                var disposition = differences.Count > 0 ? "Mismatch" : status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                results.Add(new(i, disposition, prefixDisposition, origin, lookup, source, read, factor, status == 0 ? expected?.Product : null,
                    output, expected, differences.AsReadOnly(), ReportRow(row, scenario.TraceCallIndexes.Contains(i))));
                stopped |= status != 0; previousFactor = row.GetProperty("factor0158After").GetInt32(); previousState = after;
            }
            reports.Add(new(id, new[] { 0, 85, 170 }[p], sequence.GetProperty("callerGate0124").GetInt32(), results.AsReadOnly()));
        }
        return reports.AsReadOnly();
    }
    private static int? NullableInt(JsonElement r, string name) => r.GetProperty(name).ValueKind == JsonValueKind.Null ? null : r.GetProperty(name).GetInt32();
    private static int[][] Matrix(JsonElement value, int width, int limit)
    {
        Require(value.ValueKind == JsonValueKind.Array && value.GetArrayLength() <= limit, "Unbounded M2k journal.");
        return value.EnumerateArray().Select(r =>
        {
            var v = r.EnumerateArray().Select(n => n.GetInt32()).ToArray();
            Require(v.Length == width && v.All(n => n is >= 0 and <= 65536), "Malformed M2k journal row."); return v;
        }).ToArray();
    }
    internal static bool HandoffMatches(int[][] accesses, int source, bool readerExecuted)
    {
        var stores = accesses.Select((a, i) => (a, i)).Where(x => x.a[0] == 0x134E && x.a[1] == 0x140 && x.a[2] == 16 && x.a[3] == 1 && x.a[4] == source).ToArray();
        var reads = accesses.Select((a, i) => (a, i)).Where(x => x.a[0] == 0x21DB && x.a[1] == 0x140 && x.a[2] == 16 && x.a[3] == 0 && x.a[4] == source).ToArray();
        if (stores.Length != 1 || reads.Length != (readerExecuted ? 1 : 0)) return false;
        var end = readerExecuted ? reads[0].i : accesses.Length;
        return end > stores[0].i && !accesses.Skip(stores[0].i + 1).Take(end - stores[0].i - 1).Any(a => a[3] == 1 && a[1] < 0x142 && a[1] + a[2] / 8 > 0x140);
    }
    internal static void ValidateSeams(JsonElement row)
    {
        var tails = row.GetProperty("tailBoundaries"); Require(tails.GetArrayLength() == 5 && Equal(tails[0], tails[1]) && Equal(tails[2], tails[3]) && Equal(tails[4], row.GetProperty("handoff1350")), "Continuous selection/lookup/consumer boundary was reseeded.");
        var before = row.GetProperty("handoff1350"); var entry = row.GetProperty("downstreamEntry");
        Require(before.GetProperty("pc").GetInt32() == 0x1350 && entry.GetProperty("pc").GetInt32() == 0x21DB &&
            entry.GetProperty("lrb").GetInt32() == 0x20 && entry.GetProperty("psw").GetInt32() == 0x0DC9 &&
            entry.GetProperty("usp").GetInt32() == 0x280 && entry.GetProperty("ssp").GetInt32() == 0x7FE, "M2k scripted ABI differs.");
        foreach (var k in new[] { "accumulator", "x1", "x2", "dp", "ssp", "registers" }) Require(Equal(before.GetProperty(k), entry.GetProperty(k)), "M2k handoff reset native-produced machine state.");
        Require(Equal(row.GetProperty("hostTransitionWrites"), ExpectedContracts()[0].GetProperty("hostTransitionWrites")), "Hidden host transition writes.");
    }
    internal static void ValidateEventContinuity(int[][] events, int entryA, int entryPsw, int exitA, int exitPsw)
    {
        var a = entryA; var psw = entryPsw;
        foreach (var e in events)
        {
            Require(e.Length == 8 && e[2] == a && e[4] == psw, "M2k accumulator/flags history was reset or forged.");
            a = e[3]; psw = e[5];
        }
        Require(a == exitA && psw == exitPsw, "M2k exit contradicts executed register/flags history.");
    }
    private static P28AcquisitionStageResult ValidateDownstream(JsonElement stage, JsonElement entry, JsonElement exit)
    {
        P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 32, 0, [], null) ?? throw new InvalidOperationException("M2k stage result missing.");
        Require(result.UsedAssumptions.Count == 0 && result.ProgramReads.Count == 0, "M2k foreign reads or assumptions.");
        var events = Matrix(stage.GetProperty("events"), 8, 32); _ = Matrix(stage.GetProperty("writes"), 3, 32);
        ValidateEventContinuity(events, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(),
            exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        Require(events.Length == result.Steps && result.Trace.Count == events.Length, "Incomplete M2k execution journal.");
        var pc = 0x21DB;
        for (var i = 0; i < events.Length; i++)
        {
            var e = events[i]; var t = result.Trace[i];
            Require(e[0] == pc && pc is >= 0x21DB and < 0x21F2 && t.GetProperty("pc").GetInt32() == pc &&
                t.GetProperty("nextPc").GetInt32() == e[1] && t.GetProperty("accumulator").GetInt32() == e[3] && t.GetProperty("psw").GetInt32() == e[5], "M2k path/trace contradiction."); pc = e[1];
        }
        Require(result.StopPc == pc && exit.GetProperty("pc").GetInt32() == pc && result.ExecutedInstructionBytes.All(a => a is >= 0x21DB and < 0x21F2), "M2k instruction extent/exit differs.");
        Require(stage.GetProperty("sspAfter").GetInt32() == 0x7FE && exit.GetProperty("ssp").GetInt32() == 0x7FE && exit.GetProperty("lrb").GetInt32() == 0x20, "M2k stack/bank differs.");
        Require(result.Status != 0 || pc == 0x21F2, "M2k successful exit differs."); return result;
    }
    internal static void ValidateNumbers(JsonElement stage, int[][] accesses, JsonElement exit, P28FuelCalculationProjection e, int? output)
    {
        var events = Matrix(stage.GetProperty("events"), 8, 32); var writes = Matrix(stage.GetProperty("writes"), 3, 32);
        int[] At(int pc) => events.Single(v => v[0] == pc);
        Require(At(0x21DB)[3] == e.Source0140 && At(0x21DD)[2] == e.Source0140 && At(0x21E0)[2] == e.Source0140 &&
            At(0x21E0)[3] == e.LowWord && At(0x21E4)[3] == e.ShiftedLowWord && At(0x21E8)[3] == e.NarrowedWord, "M2k operand order, product layout or narrowing differs.");
        Require(At(0x21E9)[6] == e.ShiftedHighWord >> 8 && At(0x21E9)[7] == 0 && At(0x21EC)[1] == (e.Saturated ? 0x21EE : 0x21F1), "M2k saturation equality/branch differs.");
        Require((At(0x21E2)[5] & 0x8000) != 0 == ((e.HighWord & 1) != 0) &&
            (At(0x21E4)[5] & 0x8000) != 0 == ((e.LowWord & 1) != 0) &&
            (At(0x21E9)[5] & 0x4000) != 0 == !e.Saturated && (At(0x21E9)[5] & 0xA000) == 0,
            "M2k consumed carry/comparison flags differ.");
        foreach (var pc in new[] { 0x21DB, 0x21E0, 0x21E2, 0x21E4, 0x21E6, 0x21E8, 0x21E9, 0x21EC, 0x21F1 })
            Require((At(pc)[5] & 0x1000) != 0, "M2k word DD mode differs.");
        Require((At(0x21E5)[5] & 0x1000) == 0, "M2k byte load did not reset DD.");
        Require(accesses.Count(a => a.SequenceEqual(new[] { 0x21DD, 0x158, 16, 0, e.Factor0158 })) == 1, "M2k second operand provenance differs.");
        Require(writes.SelectMany(v => v).SequenceEqual(new[] { 0x100, 16, e.Factor0158, 0x102, 16, e.HighWord, 0x102, 16, e.ShiftedHighWord, 0x104, 16, e.Output }), "M2k ordered banked word writes differ.");
        var registers = exit.GetProperty("registers").EnumerateArray().Select(v => v.GetInt32()).ToArray();
        Require(registers.Length == 8 && (registers[4] | registers[5] << 8) == e.Output && output == e.Output && At(0x21F1)[2] == e.Output, "M2k native result/word aliases differ.");
    }
    private static JsonElement ReportRow(JsonElement row, bool trace)
    {
        if (trace) return row.Clone();
        var node = JsonNode.Parse(row.GetRawText())!;
        foreach (var name in new[] { "rpmAxes", "loadAxis", "selection", "lookup", "consumer" })
            if (node["prefix"]?[name]?["result"] is JsonObject result) result["trace"] = new JsonArray();
        if (node["downstream"]?["result"] is JsonObject downstream) downstream["trace"] = new JsonArray();
        return JsonSerializer.SerializeToElement(node);
    }
}
