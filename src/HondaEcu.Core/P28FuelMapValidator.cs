using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28FuelMapCheckpoint(int Index, string Disposition, P28FuelMapCall Inputs, JsonElement Actual,
    P28FuelMapModelStep? Expected, int? ActualSelectedOrigin, int? ActualLookupResult, int? ActualConsumerOutput,
    IReadOnlyList<string> Differences);
public sealed record P28FuelMapSequenceReport(int ScratchPattern, IReadOnlyList<P28FuelMapCheckpoint> Checkpoints);
public sealed record P28FuelMapImageReport(string Image, int ArithmeticChecksum, IReadOnlyList<P28FuelMapSequenceReport> Sequences);
public sealed record P28FuelMapDifference(int ScratchPattern, int Index, string Comparison, bool? MutatedCellRead,
    int? LookupA, int? LookupB, int? ConsumerA, int? ConsumerB, bool? Witness, string Effect);
public sealed record P28FuelMapValidationReport(int FormatVersion, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    P28FuelMapMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28FuelMapImageReport> Images,
    IReadOnlyList<P28FuelMapDifference> Comparisons)
{
    public object Summary => new
    {
        StrictMatches = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints).Count(row => row.Disposition == "StrictMatch"),
        ConditionalMatches = 0,
        Dispositions = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints).GroupBy(row => row.Disposition).ToDictionary(group => group.Key, group => group.Count()),
        Contexts = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints).Where(row => row.Expected is not null)
            .GroupBy(row => row.Expected!.SelectedMap).ToDictionary(group => group.Key, group => group.Count()),
        AxisIntervals = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints).Where(row => row.Expected is not null)
            .SelectMany(row => new[] { $"load:{row.Expected!.Load.Index}", $"map_0_rpm:{row.Expected.Map0Rpm.Index}", $"map_1_rpm:{row.Expected.Map1Rpm.Index}" }).Distinct().Order().ToArray(),
        CellsRead = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints).Where(row => row.Expected is not null)
            .SelectMany(row => row.Expected!.Operands.CellAddresses).Distinct().Count(),
        AbWitnesses = Comparisons.Count(row => row.Witness == true),
        AbEffects = Comparisons.GroupBy(row => row.Effect).ToDictionary(group => group.Key, group => group.Count()),
    };
    public bool HasFailure => Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints).Any(row => row.Disposition != "StrictMatch");
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1InteractiveGuiAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string ConditionalPermissions => "None";
    public string FirmwareOutput => "None; B exists in memory only, with no binding, checksum repair, export, receipt or capability";
}

public static class P28FuelMapValidator
{
    public const string Operation = "fuelMapLookup";

    public static object CreateRequest(RomImage image, P28FuelMapScenario scenario) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(value => (int)value).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        fuelMapLookup = new { formatVersion = 1, scenario.InitialState, scenario.Calls },
    };

    public static async Task<P28FuelMapValidationReport> ExecuteAsync(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, string runner, P28FuelMapScenario scenario,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28FuelMapInspector.LayoutGuard(original);
        var images = new List<P28FuelMapImageReport>();
        var changed = new List<int>();
        var child = scenario.Mutation is null ? null : P28FuelMapInspector.Mutate(original, scenario.Mutation);
        if (child is not null) for (var i = 0; i < original.Size; i++) if (original.Span[i] != child.Span[i]) changed.Add(i);
        foreach (var image in child is null ? new[] { original } : new[] { original, child })
        {
            if (!ReferenceEquals(image, original)) P28FuelMapInspector.AdmitMutation(original, image, scenario.Mutation!);
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            images.Add(AnalyzeImage(image, scenario, response, images.Count == 0 ? "A" : "B"));
        }
        var comparisons = new List<P28FuelMapDifference>();
        if (child is not null)
        {
            var offset = P28FuelMapContract.CellOffset(scenario.Mutation!.MapId, scenario.Mutation.Row, scenario.Mutation.Column);
            for (var sequence = 0; sequence < 3; sequence++) for (var index = 0; index < scenario.Calls.Count; index++)
                {
                    var a = images[0].Sequences[sequence].Checkpoints[index];
                    var b = images[1].Sequences[sequence].Checkpoints[index];
                    var comparable = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    bool? read = comparable ? ProgramReads(b.Actual.GetProperty("lookup")).Contains(offset) : null;
                    bool? witness = comparable ? read == true && a.ActualLookupResult != b.ActualLookupResult && a.ActualConsumerOutput != b.ActualConsumerOutput : null;
                    var effect = !comparable ? "NotComparable" : read != true ? "CellNotRead" : a.ActualLookupResult == b.ActualLookupResult ? "ReadMaskedByWeightOrTruncation" :
                        a.ActualConsumerOutput == b.ActualConsumerOutput ? "LookupChangedConsumerMasked" : "LookupAndConsumerChanged";
                    comparisons.Add(new(new[] { 0, 85, 170 }[sequence], index, comparable ? "Comparable" : "NotComparable", read,
                        a.ActualLookupResult, b.ActualLookupResult, a.ActualConsumerOutput, b.ActualConsumerOutput, witness, effect));
                }
        }
        return new(1, original.Hash, profile.Id, scenario.Digest, scenario.Mutation, changed.AsReadOnly(), images.AsReadOnly(), comparisons.AsReadOnly());
    }

    internal static P28FuelMapImageReport AnalyzeImage(RomImage image, P28FuelMapScenario scenario, SliceProcessResponse response, string id)
    {
        try { return AnalyzeCore(image, scenario, response.Response, id); }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentOutOfRangeException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed fuel-map response.", exception); }
    }

    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events, int Ssp);

    private static Stage? ParseStage(JsonElement element, string id)
    {
        if (element.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(element, "result", "writes", "events", "sspAfter");
        var budget = id switch { "rpmAxes" => 384, "loadAxis" => 192, "selection" => 64, "lookup" => 192, "consumer" => 64, _ => throw new InvalidOperationException() };
        var result = P28AcquisitionValidator.ParseStage(element.GetProperty("result"), budget, 0, [], null);
        Require(result is not null, "Fuel stage result missing.");
        var parsedResult = result!;
        int[][] Matrix(string name, int width)
        {
            var rows = element.GetProperty(name); Require(rows.GetArrayLength() <= 1024, "Unbounded fuel journal.");
            return rows.EnumerateArray().Select(row =>
            {
                var values = row.EnumerateArray().Select(value => value.GetInt32()).ToArray();
                Require(values.Length == width && values.All(value => value is >= 0 and <= 65536), "Invalid fuel journal.");
                return values;
            }).ToArray();
        }
        var writes = Matrix("writes", 3); var events = Matrix("events", 8); var ssp = element.GetProperty("sspAfter").GetInt32();
        Require(ssp is >= 0 and <= 65535 && parsedResult.UsedAssumptions.Count == 0 && events.Length == parsedResult.Steps && parsedResult.Trace.Count == Math.Min(128, parsedResult.Steps), "Fuel stage observation is incomplete.");
        var entry = id switch { "rpmAxes" => 0x0A0C, "loadAxis" => 0x0A62, "selection" => 0x12FC, "lookup" => 0x1340, "consumer" => 0x1347, _ => 0 };
        var exit = id switch { "rpmAxes" => 0x0A45, "loadAxis" => 0x0A77, "selection" => 0x1340, "lookup" => 0x1347, "consumer" => 0x1350, _ => 0 };
        bool InCode(int pc) => id switch
        {
            "rpmAxes" => pc is >= 0x0A0C and < 0x0A45 or >= 0x59B2 and < 0x59E4,
            "loadAxis" => pc is >= 0x0A62 and < 0x0A77 or >= 0x59B2 and < 0x59E4,
            "selection" => pc is >= 0x12FC and < 0x1340,
            "lookup" => pc is >= 0x1340 and < 0x1347 or >= 0x59E4 and < 0x5A46,
            "consumer" => pc is >= 0x1347 and < 0x1350 or >= 0x5A55 and < 0x5A72,
            _ => false,
        };
        var pc = entry;
        for (var i = 0; i < events.Length; i++)
        {
            var row = events[i]; Require(row[0] == pc && InCode(pc), "Fuel event path escaped/discontinued.");
            if (i < parsedResult.Trace.Count)
            {
                var trace = parsedResult.Trace[i];
                Require(trace.GetProperty("pc").GetInt32() == row[0] && trace.GetProperty("nextPc").GetInt32() == row[1] &&
                    trace.GetProperty("accumulator").GetInt32() == row[3] && trace.GetProperty("psw").GetInt32() == row[5], "Fuel trace contradicts event journal.");
            }
            pc = row[1];
        }
        Require(parsedResult.StopPc == pc && parsedResult.ExecutedInstructionBytes.All(address => InCode(address)), "Fuel stop/extents differ from contract.");
        Require(parsedResult.Status != 0 || parsedResult.Error is null && pc == exit && ssp == 0x7FE, "Fuel successful exit/stack differs.");
        Require(parsedResult.ProgramReads.All(address => ProgramAllowed(id, address)), "Foreign fuel program-data read.");
        return new(parsedResult, writes, events, ssp);
    }

    private static bool ProgramAllowed(string stage, int address) => stage switch
    {
        "rpmAxes" => address is >= 0x7014 and < 0x703C,
        "loadAxis" => address is >= 0x7000 and < 0x700A,
        "lookup" => address == 0x60E5 || address is >= 0x7050 and < 0x71F4,
        _ => false,
    };

    private static int[] ProgramReads(JsonElement stage) => stage.ValueKind == JsonValueKind.Null ? [] :
        stage.GetProperty("result").GetProperty("programReads").EnumerateArray().Select(value => value.GetInt32()).ToArray();

    private static P28FuelMapState State(JsonElement element)
    {
        P28LimiterScenario.Shape(element, "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction", "map0RpmFraction",
            "map1RpmFraction", "selector0127", "consumerFactor013f", "consumerOutput0140");
        return element.Deserialize<P28FuelMapState>(P28StatefulScenario.Options)!;
    }

    private static P28FuelMapImageReport AnalyzeCore(RomImage image, P28FuelMapScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts",
            "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "fuelMapSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation);
        Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "Fuel entry contract mismatch.");
        foreach (var name in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(name).GetArrayLength() == 0, "Foreign response rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Unexpected synthetic result.");
        var sequences = root.GetProperty("fuelMapSequences"); Require(sequences.GetArrayLength() == 3, "Fuel scratch count differs.");
        var reports = new List<P28FuelMapSequenceReport>();
        for (var sequenceIndex = 0; sequenceIndex < 3; sequenceIndex++)
        {
            var sequence = sequences[sequenceIndex]; P28LimiterScenario.Shape(sequence, "scratchPattern", "checkpoints");
            var pattern = new[] { 0, 85, 170 }[sequenceIndex]; Require(sequence.GetProperty("scratchPattern").GetInt32() == pattern, "Fuel scratch order differs.");
            var rows = sequence.GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "Fuel call count differs.");
            var model = new P28FuelMapModel(image, scenario.InitialState); var previous = scenario.InitialState; var stopped = false;
            var checkpoints = new List<P28FuelMapCheckpoint>();
            for (var index = 0; index < rows.GetArrayLength(); index++)
            {
                var row = rows[index];
                P28LimiterScenario.Shape(row, "index", "status", "stateBefore", "stateAfterInputs", "stateAfter", "rpmAxes", "loadAxis", "selection", "lookup", "consumer",
                    "selectedOrigin", "position", "lookupResult", "consumerOutput");
                Require(row.GetProperty("index").GetInt32() == index, "Fuel call order differs.");
                var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Unknown fuel status.");
                var before = State(row.GetProperty("stateBefore")); var after = State(row.GetProperty("stateAfter"));
                var afterInputs = row.GetProperty("stateAfterInputs").ValueKind == JsonValueKind.Null ? null : State(row.GetProperty("stateAfterInputs"));
                var rpmStage = ParseStage(row.GetProperty("rpmAxes"), "rpmAxes"); var loadStage = ParseStage(row.GetProperty("loadAxis"), "loadAxis");
                var selectionStage = ParseStage(row.GetProperty("selection"), "selection"); var lookupStage = ParseStage(row.GetProperty("lookup"), "lookup");
                var consumerStage = ParseStage(row.GetProperty("consumer"), "consumer");
                int? Number(string name) => row.GetProperty(name).ValueKind == JsonValueKind.Null ? null : row.GetProperty(name).GetInt32();
                var origin = Number("selectedOrigin"); var lookup = Number("lookupResult"); var consumer = Number("consumerOutput");
                var differences = new List<string>(); void Check(bool condition, string message) { if (!condition) differences.Add(message); }
                Check(before == previous, "Actual persistent history discontinuity/reseed"); P28FuelMapModelStep? expected = null;
                if (stopped)
                {
                    Require(status == 4 && afterInputs is null && rpmStage is null && loadStage is null && selectionStage is null && lookupStage is null && consumerStage is null &&
                        origin is null && lookup is null && consumer is null && before == after, "Execution/output exists in terminal suffix.");
                }
                else
                {
                    Require(afterInputs is not null && rpmStage is not null, "First fuel stage was not represented.");
                    Require(status == (consumerStage?.Result.Status ?? lookupStage?.Result.Status ?? selectionStage?.Result.Status ?? loadStage?.Result.Status ?? rpmStage!.Result.Status), "Fuel status contradicts last executed stage.");
                    if (status == 0)
                    {
                        Require(loadStage is not null && selectionStage is not null && lookupStage is not null && consumerStage is not null && origin is not null && lookup is not null && consumer is not null,
                            "Completed fuel call has missing stage/output.");
                        expected = model.Step(scenario.Calls[index]);
                        Check(before == expected.Before && afterInputs == expected.AfterInputs && after == expected.After, "Independent state/cache/fraction history");
                        Check(origin == expected.SelectedOrigin, "ROM-selected map origin/context");
                        var positionElement = row.GetProperty("position");
                        P28LimiterScenario.Shape(positionElement, "loadIndex", "loadFraction", "rpmIndex", "rpmFraction");
                        Check(positionElement.GetProperty("loadIndex").GetInt32() == expected.Load.Index && positionElement.GetProperty("loadFraction").GetInt32() == expected.Load.Fraction &&
                            positionElement.GetProperty("rpmIndex").GetInt32() == (expected.SelectedMap == "map_0" ? expected.Map0Rpm.Index : expected.Map1Rpm.Index) &&
                            positionElement.GetProperty("rpmFraction").GetInt32() == (expected.SelectedMap == "map_0" ? expected.Map0Rpm.Fraction : expected.Map1Rpm.Fraction), "Native selected indices/fractions");
                        Check(ProgramReads(row.GetProperty("rpmAxes")).SequenceEqual(expected.Map0Rpm.OrderedProgramReads.Concat(expected.Map1Rpm.OrderedProgramReads)), "Ordered RPM-axis program reads");
                        Check(ProgramReads(row.GetProperty("loadAxis")).SequenceEqual(expected.Load.OrderedProgramReads), "Ordered load-axis program reads");
                        Check(ProgramReads(row.GetProperty("selection")).Length == 0 && ProgramReads(row.GetProperty("lookup")).SequenceEqual(expected.Operands.OrderedProgramReads) && ProgramReads(row.GetProperty("consumer")).Length == 0,
                            "Ordered selected metadata/cell/consumer program reads");
                        Check(lookup == expected.Operands.LookupResult && consumer == expected.Consumer.Output, "Lookup/consumer numeric result");
                        Check(lookupStage!.Events.Any(e => e[0] == 0x5A0C && e[3] == expected.Operands.ScaledCells[0]) &&
                            lookupStage.Events.Any(e => e[0] == 0x5A13 && e[3] == expected.Operands.ScaledCells[1]) &&
                            lookupStage.Events.Any(e => e[0] == 0x5A18 && e[3] == expected.Operands.ScaledCells[3]) &&
                            lookupStage.Events.Any(e => e[0] == 0x5A1E && e[3] == expected.Operands.ScaledCells[2]), "Native cell*column-multiplier intermediates");
                        Check(lookupStage.Events.Any(e => e[1] == 0x1343 && e[3] == expected.Operands.LookupResult), "Native final sequential interpolation return");
                        Check(consumerStage!.Events.Any(e => e[0] == 0x134E && e[2] == expected.Consumer.Output) && consumerStage.Writes.Any(w => w[0] == 0x140 && w[1] == 16 && w[2] == expected.Consumer.Output) &&
                            (expected.Consumer.CorrectionExecuted ? consumerStage.Events.Any(e => e[0] == 0x5A55) : consumerStage.Events.All(e => e[0] != 0x5A55)),
                            "Immediate consumer operand/output store");
                        foreach (var pair in new[] { (rpmStage!, 0x0A45), (loadStage!, 0x0A77), (selectionStage!, 0x1340), (lookupStage!, 0x1347), (consumerStage!, 0x1350) })
                            Check(pair.Item1.Result.StopPc == pair.Item2 && pair.Item1.Ssp == 0x7FE, "Stage exit/stack balance");
                    }
                }
                var disposition = differences.Count > 0 ? "Mismatch" : status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                checkpoints.Add(new(index, disposition, scenario.Calls[index], row.Clone(), expected, origin, lookup, consumer, differences.AsReadOnly()));
                previous = after; stopped |= status != 0;
            }
            reports.Add(new(pattern, checkpoints.AsReadOnly()));
        }
        return new(id, P28NativeChecksumArithmetic.Calculate(image).ComputedResult, reports.AsReadOnly());
    }

    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new
    {
        id = "fuelMapLookup",
        stages = new object[]
        {
            new { id="rpmAxes", entry=0x0A0C, exit=0x0A45, code=new[]{new[]{0x0A0C,0x0A45},new[]{0x59B2,0x59E4}}, programData=new[]{new[]{0x7014,0x703C}}, lrb=0x40, usp=0x180, budget=384 },
            new { id="loadAxis", entry=0x0A62, exit=0x0A77, code=new[]{new[]{0x0A62,0x0A77},new[]{0x59B2,0x59E4}}, programData=new[]{new[]{0x7000,0x700A}}, lrb=0x40, usp=0x180, budget=192 },
            new { id="selection", entry=0x12FC, exit=0x1340, code=new[]{new[]{0x12FC,0x1340}}, programData=Array.Empty<int[]>(), lrb=0x20, usp=0x280, budget=64 },
            new { id="lookup", entry=0x1340, exit=0x1347, code=new[]{new[]{0x1340,0x1347},new[]{0x59E4,0x5A46}}, programData=new[]{new[]{0x60E5,0x60E6},new[]{0x7050,0x71F4}}, lrb=0x20, usp=0x280, budget=192 },
            new { id="consumer", entry=0x1347, exit=0x1350, code=new[]{new[]{0x1347,0x1350},new[]{0x5A55,0x5A72}}, programData=Array.Empty<int[]>(), lrb=0x20, usp=0x280, budget=64 },
        },
        dataRanges = new[]{new[]{0,8},new[]{0x88,0x90},new[]{0xB8,0xB9},new[]{0xBF,0xC0},new[]{0xC2,0xC3},new[]{0x100,0x108},new[]{0x11C,0x11D},new[]{0x120,0x122},new[]{0x127,0x128},new[]{0x13F,0x142},new[]{0x1BC,0x1BD},new[]{0x1C0,0x1C8},new[]{0x200,0x208},new[]{0x227,0x228},new[]{0x238,0x239},new[]{0x7E0,0x800}},
        psw=0x0101, scb=1, ssp=0x7FE, tracePrefix=128, stop="BeforeInstruction",
        fixedCallerState = new { data00b8Mask18=0, data0227Bit5=false, data011cBit5=false, data0120Bit5=false, data0121Bit6=false },
        scriptedPerCall = new[]{"DATA0238 raw map_0 axis input","DATA00C2 raw map_1 axis input","DATA00BF raw load input","DATA0127.1 software map selector"},
        state="Seed once; native caches/fraction words/results persist; stages are a scripted schedule, not the ECU main loop",
        physicalUnitsAvailable=false, assumptions=Array.Empty<string>(),
    }});
}
