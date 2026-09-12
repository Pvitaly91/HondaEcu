using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28IgnitionMapCheckpoint(int Index, string Disposition, P28IgnitionMapCall Inputs,
    JsonElement Actual, P28IgnitionMapModelStep? Expected, int? ActualSelectedOrigin, int? ActualLookupResult,
    int? ActualConsumerOutput, IReadOnlyList<string> Differences);
public sealed record P28IgnitionMapSequenceReport(int ScratchPattern, IReadOnlyList<P28IgnitionMapCheckpoint> Checkpoints);
public sealed record P28IgnitionMapImageReport(string Image, int ArithmeticChecksum,
    IReadOnlyList<P28IgnitionMapSequenceReport> Sequences);
public sealed record P28IgnitionMapDifference(int ScratchPattern, int Index, string Comparison,
    bool? MutatedCellRead, int? LookupA, int? LookupB, int? ConsumerA, int? ConsumerB, bool? Witness, string Effect);
public sealed record P28IgnitionMapValidationReport(int FormatVersion, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, P28IgnitionMapMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28IgnitionMapImageReport> Images, IReadOnlyList<P28IgnitionMapDifference> Comparisons)
{
    public object Summary => new
    {
        StrictMatches = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints)
            .Count(row => row.Disposition == "StrictMatch"),
        ConditionalMatches = 0,
        Dispositions = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints)
            .GroupBy(row => row.Disposition).ToDictionary(group => group.Key, group => group.Count()),
        Contexts = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints)
            .Where(row => row.Expected is not null).GroupBy(row => row.Expected!.SelectedMap)
            .ToDictionary(group => group.Key, group => group.Count()),
        AxisIntervals = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints)
            .Where(row => row.Expected is not null).SelectMany(row => new[] { $"load:{row.Expected!.Load.Index}",
                $"ignition_map_0_rpm:{row.Expected.Map0Rpm.Index}", $"ignition_map_1_rpm:{row.Expected.Map1Rpm.Index}" })
            .Distinct().Order().ToArray(),
        CellsRead = Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints)
            .Where(row => row.Expected is not null).SelectMany(row => row.Expected!.Operands.CellAddresses).Distinct().Count(),
        AbWitnesses = Comparisons.Count(row => row.Witness == true),
        AbEffects = Comparisons.GroupBy(row => row.Effect).ToDictionary(group => group.Key, group => group.Count()),
    };
    public bool HasFailure => Images.SelectMany(image => image.Sequences).SelectMany(sequence => sequence.Checkpoints)
        .Any(row => row.Disposition != "StrictMatch");
    public bool PhysicalRpmAvailable => false;
    public string AngleUnits => "raw / physical degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1InteractiveGuiAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string ConditionalPermissions => "None";
    public string FirmwareOutput => "None; B exists in memory only, without binding, checksum repair, export, receipt or capability";
}

public static class P28IgnitionMapValidator
{
    public const string Operation = "ignitionMapLookup";

    public static object CreateRequest(RomImage image, P28IgnitionMapScenario scenario) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(value => (int)value).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        ignitionMapLookup = new { formatVersion = 1, scenario.InitialState, scenario.Calls },
    };

    public static async Task<P28IgnitionMapValidationReport> ExecuteAsync(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, string runner, P28IgnitionMapScenario scenario,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28IgnitionMapInspector.LayoutGuard(original);
        var images = new List<P28IgnitionMapImageReport>(); var changed = new List<int>();
        var child = scenario.Mutation is null ? null : P28IgnitionMapInspector.Mutate(original, scenario.Mutation);
        if (child is not null) for (var i = 0; i < original.Size; i++) if (original.Span[i] != child.Span[i]) changed.Add(i);
        foreach (var image in child is null ? new[] { original } : new[] { original, child })
        {
            if (!ReferenceEquals(image, original)) P28IgnitionMapInspector.AdmitMutation(original, image, scenario.Mutation!);
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            images.Add(AnalyzeImage(image, scenario, response, images.Count == 0 ? "A" : "B"));
        }
        var comparisons = new List<P28IgnitionMapDifference>();
        if (child is not null)
        {
            var offset = P28IgnitionMapContract.CellOffset(scenario.Mutation!.MapId, scenario.Mutation.Row, scenario.Mutation.Column);
            for (var sequence = 0; sequence < 3; sequence++) for (var index = 0; index < scenario.Calls.Count; index++)
                {
                    var a = images[0].Sequences[sequence].Checkpoints[index]; var b = images[1].Sequences[sequence].Checkpoints[index];
                    var comparable = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    bool? read = comparable ? ProgramReads(b.Actual.GetProperty("lookup")).Contains(offset) : null;
                    bool? witness = comparable ? read == true && a.ActualLookupResult != b.ActualLookupResult &&
                        a.ActualConsumerOutput != b.ActualConsumerOutput : null;
                    var effect = !comparable ? "NotComparable" : read != true ? "CellNotRead" :
                        a.ActualLookupResult == b.ActualLookupResult ? "ReadMaskedByWeightOrTruncation" :
                        a.ActualConsumerOutput == b.ActualConsumerOutput ? "LookupChangedConsumerMasked" : "LookupAndConsumerChanged";
                    comparisons.Add(new(new[] { 0, 85, 170 }[sequence], index, comparable ? "Comparable" : "NotComparable",
                        read, a.ActualLookupResult, b.ActualLookupResult, a.ActualConsumerOutput, b.ActualConsumerOutput, witness, effect));
                }
        }
        return new(1, original.Hash, profile.Id, scenario.Digest, scenario.Mutation, changed.AsReadOnly(), images.AsReadOnly(), comparisons.AsReadOnly());
    }

    internal static P28IgnitionMapImageReport AnalyzeImage(RomImage image, P28IgnitionMapScenario scenario,
        SliceProcessResponse response, string id)
    {
        try { return AnalyzeCore(image, scenario, response.Response, id); }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or KeyNotFoundException or
            FormatException or OverflowException or ArgumentOutOfRangeException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed ignition-map response.", exception); }
    }

    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events, int Ssp);

    private static Stage? ParseStage(JsonElement element, string id)
    {
        if (element.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(element, "result", "writes", "events", "sspAfter");
        var budget = id switch { "axes" => 576, "selection" => 64, "lookup" => 192, "consumer" => 32, _ => throw new InvalidOperationException() };
        var result = P28AcquisitionValidator.ParseStage(element.GetProperty("result"), budget, 0, [], null);
        Require(result is not null, "Ignition stage result missing."); var parsed = result!;
        int[][] Matrix(string name, int width)
        {
            var rows = element.GetProperty(name); Require(rows.GetArrayLength() <= 1024, "Unbounded ignition journal.");
            return rows.EnumerateArray().Select(row =>
            {
                var values = row.EnumerateArray().Select(value => value.GetInt32()).ToArray();
                Require(values.Length == width && values.All(value => value is >= 0 and <= 65536), "Invalid ignition journal.");
                return values;
            }).ToArray();
        }
        var writes = Matrix("writes", 3); var events = Matrix("events", 8); var ssp = element.GetProperty("sspAfter").GetInt32();
        Require(ssp is >= 0 and <= 65535 && parsed.UsedAssumptions.Count == 0 && events.Length == parsed.Steps &&
            parsed.Trace.Count == Math.Min(128, parsed.Steps), "Ignition stage observation is incomplete.");
        var entry = id switch { "axes" => 0x0A0C, "selection" => 0x0B64, "lookup" => 0x0BAF, "consumer" => 0x0BB4, _ => 0 };
        var exit = id switch { "axes" => 0x0A62, "selection" => 0x0BAF, "lookup" => 0x0BB4, "consumer" => 0x0BD4, _ => 0 };
        bool InCode(int pc) => id switch
        {
            "axes" => pc is >= 0x0A0C and < 0x0A62 or >= 0x59B2 and < 0x59E4,
            "selection" => pc is >= 0x0B64 and < 0x0BAF,
            "lookup" => pc is >= 0x0BAF and < 0x0BB4 or >= 0x59E4 and < 0x5A46,
            "consumer" => pc is >= 0x0BB4 and < 0x0BD4,
            _ => false,
        };
        var pc = entry;
        for (var i = 0; i < events.Length; i++)
        {
            var row = events[i]; Require(row[0] == pc && InCode(pc), "Ignition event path escaped/discontinued.");
            if (i < parsed.Trace.Count)
            {
                var trace = parsed.Trace[i];
                Require(trace.GetProperty("pc").GetInt32() == row[0] && trace.GetProperty("nextPc").GetInt32() == row[1] &&
                    trace.GetProperty("accumulator").GetInt32() == row[3] && trace.GetProperty("psw").GetInt32() == row[5],
                    "Ignition trace contradicts event journal.");
            }
            pc = row[1];
        }
        Require(parsed.StopPc == pc && parsed.ExecutedInstructionBytes.All(address => InCode(address)),
            "Ignition stop/extents differ from contract.");
        Require(parsed.Status != 0 || parsed.Error is null && pc == exit && ssp == 0x7FE, "Ignition successful exit/stack differs.");
        Require(parsed.ProgramReads.All(address => ProgramAllowed(id, address)), "Foreign ignition program-data read.");
        return new(parsed, writes, events, ssp);
    }

    private static bool ProgramAllowed(string stage, int address) => stage switch
    {
        "axes" => address is >= 0x7000 and < 0x700A or >= 0x7014 and < 0x703C,
        "lookup" => address is >= 0x72E4 and < 0x7474,
        _ => false,
    };

    private static int[] ProgramReads(JsonElement stage) => stage.ValueKind == JsonValueKind.Null ? [] :
        stage.GetProperty("result").GetProperty("programReads").EnumerateArray().Select(value => value.GetInt32()).ToArray();

    private static P28IgnitionMapState State(JsonElement element)
    {
        P28LimiterScenario.Shape(element, "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction",
            "map0RpmFraction", "map1RpmFraction", "selector0227", "consumerFactor0247", "consumerOutput0248");
        return element.Deserialize<P28IgnitionMapState>(P28StatefulScenario.Options)!;
    }

    private static P28IgnitionMapImageReport AnalyzeCore(RomImage image, P28IgnitionMapScenario scenario,
        JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes",
            "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "ignitionMapSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation);
        Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "Ignition entry contract mismatch.");
        foreach (var name in new[] { "compactRows", "thresholdRows", "diagnostics" })
            Require(root.GetProperty(name).GetArrayLength() == 0, "Foreign response rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Unexpected synthetic result.");
        var sequences = root.GetProperty("ignitionMapSequences"); Require(sequences.GetArrayLength() == 3, "Ignition scratch count differs.");
        var reports = new List<P28IgnitionMapSequenceReport>();
        for (var sequenceIndex = 0; sequenceIndex < 3; sequenceIndex++)
        {
            var sequence = sequences[sequenceIndex]; P28LimiterScenario.Shape(sequence, "scratchPattern", "checkpoints");
            var pattern = new[] { 0, 85, 170 }[sequenceIndex];
            Require(sequence.GetProperty("scratchPattern").GetInt32() == pattern, "Ignition scratch order differs.");
            var rows = sequence.GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "Ignition call count differs.");
            var model = new P28IgnitionMapModel(image, scenario.InitialState); var previous = scenario.InitialState; var stopped = false;
            var checkpoints = new List<P28IgnitionMapCheckpoint>();
            for (var index = 0; index < rows.GetArrayLength(); index++)
            {
                var row = rows[index];
                P28LimiterScenario.Shape(row, "index", "status", "stateBefore", "stateAfterInputs", "stateAfter", "axes",
                    "selection", "lookup", "consumer", "selectedOrigin", "position", "lookupResult", "consumerOutput");
                Require(row.GetProperty("index").GetInt32() == index, "Ignition call order differs.");
                var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Unknown ignition status.");
                var before = State(row.GetProperty("stateBefore")); var after = State(row.GetProperty("stateAfter"));
                var afterInputs = row.GetProperty("stateAfterInputs").ValueKind == JsonValueKind.Null ? null : State(row.GetProperty("stateAfterInputs"));
                var axes = ParseStage(row.GetProperty("axes"), "axes"); var selection = ParseStage(row.GetProperty("selection"), "selection");
                var lookupStage = ParseStage(row.GetProperty("lookup"), "lookup"); var consumerStage = ParseStage(row.GetProperty("consumer"), "consumer");
                int? Number(string name) => row.GetProperty(name).ValueKind == JsonValueKind.Null ? null : row.GetProperty(name).GetInt32();
                var origin = Number("selectedOrigin"); var lookup = Number("lookupResult"); var consumer = Number("consumerOutput");
                var differences = new List<string>(); void Check(bool condition, string message) { if (!condition) differences.Add(message); }
                Check(before == previous, "Actual persistent history discontinuity/reseed"); P28IgnitionMapModelStep? expected = null;
                if (stopped)
                {
                    Require(status == 4 && afterInputs is null && axes is null && selection is null && lookupStage is null &&
                        consumerStage is null && origin is null && lookup is null && consumer is null && before == after,
                        "Execution/output exists in terminal ignition suffix.");
                }
                else
                {
                    Require(afterInputs is not null && axes is not null, "First ignition stage was not represented.");
                    Require(status == (consumerStage?.Result.Status ?? lookupStage?.Result.Status ?? selection?.Result.Status ?? axes!.Result.Status),
                        "Ignition status contradicts last executed stage.");
                    if (status == 0)
                    {
                        Require(selection is not null && lookupStage is not null && consumerStage is not null && origin is not null &&
                            lookup is not null && consumer is not null, "Completed ignition call has missing stage/output.");
                        expected = model.Step(scenario.Calls[index]);
                        Check(before == expected.Before && afterInputs == expected.AfterInputs && after == expected.After,
                            "Independent state/cache/fraction history");
                        Check(origin == expected.SelectedOrigin, "ROM-selected ignition map origin/context");
                        var position = row.GetProperty("position");
                        P28LimiterScenario.Shape(position, "loadIndex", "loadFraction", "rpmIndex", "rpmFraction");
                        var expectedRpm = expected.SelectedMap == "ignition_map_0" ? expected.Map0Rpm : expected.Map1Rpm;
                        Check(position.GetProperty("loadIndex").GetInt32() == expected.Load.Index &&
                            position.GetProperty("loadFraction").GetInt32() == expected.Load.Fraction &&
                            position.GetProperty("rpmIndex").GetInt32() == expectedRpm.Index &&
                            position.GetProperty("rpmFraction").GetInt32() == expectedRpm.Fraction, "Native selected indices/fractions");
                        Check(ProgramReads(row.GetProperty("axes")).SequenceEqual(expected.Map0Rpm.OrderedProgramReads
                            .Concat(expected.Map1Rpm.OrderedProgramReads).Concat(expected.Load.OrderedProgramReads)),
                            "Ordered native axis program reads");
                        Check(ProgramReads(row.GetProperty("selection")).Length == 0 &&
                            ProgramReads(row.GetProperty("lookup")).SequenceEqual(expected.Operands.OrderedProgramReads) &&
                            ProgramReads(row.GetProperty("consumer")).Length == 0, "Ordered direct cell reads / no metadata reads");
                        Check(lookup == expected.Operands.LookupResult && consumer == expected.Consumer.Output,
                            "Ignition lookup/consumer numeric result");
                        Check(lookupStage!.Events.Any(e => e[0] == 0x5A0C && e[3] == expected.Operands.CellValues[0]) &&
                            lookupStage.Events.Any(e => e[0] == 0x5A13 && e[3] == expected.Operands.CellValues[1]) &&
                            lookupStage.Events.Any(e => e[0] == 0x5A18 && e[3] == expected.Operands.CellValues[3]) &&
                            lookupStage.Events.Any(e => e[0] == 0x5A1E && e[3] == expected.Operands.CellValues[2]),
                            "Native unity-scaled cell intermediates");
                        Check(lookupStage.Events.Any(e => e[1] == 0x0BB4 && (e[3] & 0xFF) == expected.Operands.LookupResult),
                            "Native final sequential interpolation return");
                        Check(lookupStage.Events.Any(e => e[1] == 0x5A29 && e[3] == expected.Operands.BottomColumnResult) &&
                            lookupStage.Events.Any(e => e[1] == 0x5A30 && e[3] == expected.Operands.TopColumnResult),
                            "Native independently truncated column intermediates");
                        Check(axes!.Writes.Any(w => w[0] == 0x1C2 && w[1] == 16 && w[2] == expected.Map0Rpm.Fraction) &&
                            axes.Writes.Any(w => w[0] == 0x1C6 && w[1] == 8 && w[2] == expected.Map0Rpm.Index) &&
                            axes.Writes.Any(w => w[0] == 0x1C4 && w[1] == 16 && w[2] == expected.Map1Rpm.Fraction) &&
                            axes.Writes.Any(w => w[0] == 0x1C7 && w[1] == 8 && w[2] == expected.Map1Rpm.Index) &&
                            axes.Writes.Any(w => w[0] == 0x1BE && w[1] == 16 && w[2] == expected.Load.Fraction) &&
                            axes.Writes.Any(w => w[0] == 0x1BB && w[1] == 8 && w[2] == expected.Load.Index),
                            "Native persistent axis writes and live-DD widths");
                        Check(consumerStage!.Events.Any(e => e[0] == 0x0BD2 && (e[2] & 0xFF) == expected.Consumer.Output) &&
                            consumerStage.Writes.Any(w => w[0] == 0x248 && w[1] == 8 && w[2] == expected.Consumer.Output),
                            "Immediate DATA0248 consumer store");
                        Check(expected.Consumer.ScalingExecuted
                                ? consumerStage.Events.Any(e => e[0] == 0x0BBA && e[3] == expected.Consumer.Product)
                                : consumerStage.Events.All(e => e[0] != 0x0BBA),
                            "Immediate consumer branch and unsigned product");
                        foreach (var pair in new[] { (axes!, 0x0A62), (selection!, 0x0BAF), (lookupStage!, 0x0BB4), (consumerStage!, 0x0BD4) })
                            Check(pair.Item1.Result.StopPc == pair.Item2 && pair.Item1.Ssp == 0x7FE, "Stage exit/stack balance");
                    }
                }
                var disposition = differences.Count > 0 ? "Mismatch" : status switch
                { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                checkpoints.Add(new(index, disposition, scenario.Calls[index], row.Clone(), expected, origin, lookup, consumer,
                    differences.AsReadOnly()));
                previous = after; stopped |= status != 0;
            }
            reports.Add(new(pattern, checkpoints.AsReadOnly()));
        }
        return new(id, P28NativeChecksumArithmetic.Calculate(image).ComputedResult, reports.AsReadOnly());
    }

    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new
    {
        id = "ignitionMapLookup",
        stages = new object[]
        {
            new { id="axes", entry=0x0A0C, exit=0x0A62, code=new[]{new[]{0x0A0C,0x0A62},new[]{0x59B2,0x59E4}}, programData=new[]{new[]{0x7000,0x700A},new[]{0x7014,0x703C}}, lrb=0x40, usp=0x180, budget=576 },
            new { id="selection", entry=0x0B64, exit=0x0BAF, code=new[]{new[]{0x0B64,0x0BAF}}, programData=Array.Empty<int[]>(), lrb=0x40, usp=0x180, budget=64 },
            new { id="lookup", entry=0x0BAF, exit=0x0BB4, code=new[]{new[]{0x0BAF,0x0BB4},new[]{0x59E4,0x5A46}}, programData=new[]{new[]{0x72E4,0x7474}}, lrb=0x40, usp=0x180, budget=192 },
            new { id="consumer", entry=0x0BB4, exit=0x0BD4, code=new[]{new[]{0x0BB4,0x0BD4}}, programData=Array.Empty<int[]>(), lrb=0x40, usp=0x180, budget=32 },
        },
        dataRanges = new[]{new[]{0,8},new[]{0x88,0x90},new[]{0xB8,0xB9},new[]{0xBC,0xBD},new[]{0xBF,0xC0},new[]{0xC2,0xC3},
            new[]{0x1BB,0x1C8},new[]{0x200,0x208},new[]{0x212,0x220},new[]{0x227,0x228},new[]{0x238,0x239},new[]{0x247,0x249},new[]{0x7E0,0x800}},
        psw=0x0101, scb=1, ssp=0x7FE, tracePrefix=128, stop="BeforeInstruction",
        fixedCallerState = new { data00b8Mask18=0, data0212Bits2And4=false, data021dBit4=false, data0214Bit5=false,
            data0218Bit5=false, data021fBit1=false, data0219Bit6=false },
        scriptedPerCall = new[]{"DATA0238 raw primary RPM input","DATA00C2 secondary RPM input (natively shadowed by DATA0238 in context 1)",
            "DATA00BF raw ignition load input","DATA0227.5 software map selector (masked)"},
        state="Seed once; native caches/fraction words/DATA0248 persist; stages are a scripted direct-caller schedule, not the ECU main loop",
        physicalUnitsAvailable=false, assumptions=Array.Empty<string>(),
    }});
}
