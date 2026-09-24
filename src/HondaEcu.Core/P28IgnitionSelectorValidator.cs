using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28IgnitionSelectorCheckpoint(int Index, string Disposition, int Status,
    byte SelectorBefore, byte SelectorAfter, string? ActualMap, int? SelectedOrigin,
    int? Lookup, int? Data0248, IReadOnlyList<string> Differences, JsonElement Actual);
public sealed record P28IgnitionSelectorSequence(int ImageIndex, int ScratchPattern,
    int CompletedCalls, int StopCallIndex, IReadOnlyList<P28IgnitionSelectorCheckpoint> Checkpoints);
public sealed record P28IgnitionSelectorComparison(int ScratchPattern, int Index,
    bool? CellRead, bool? ControlValid, bool? LookupChanged, bool? ConsumerChanged, string Effect);
public sealed record P28IgnitionSelectorValidationReport(int FormatVersion, string Purpose, RomHash OriginalHash,
    RomHash? MutatedHash, string ProfileId, string ScenarioDigest, string RunnerVersion,
    P28IgnitionMapMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28IgnitionSelectorSequence> Sequences, IReadOnlyList<P28IgnitionSelectorComparison> Comparisons)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") ||
        Comparisons.Any(c => c.ControlValid == false);
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw / physical degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; optional B is a one-cell memory-only comparison";
}

/// <summary>Strict native producer and lookup verification against an independent persistent model.</summary>
public static class P28IgnitionSelectorValidator
{
    public const string Operation = "ignitionSelectorChain";
    private static readonly int[] Patterns = [0, 85, 170];
    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events, int Ssp);

    public static object CreateRequest(RomImage original, RomImage? mutated, P28IgnitionSelectorScenario scenario) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = mutated is null ? [new { id = "baseline", rom = original.ToArray().Select(b => (int)b).ToArray() }] :
            new[] { new { id = "baseline", rom = original.ToArray().Select(b => (int)b).ToArray() },
                new { id = "mutated", rom = mutated.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = Patterns,
        allowAssumptions = Array.Empty<string>(),
        ignitionSelectorChain = new { formatVersion = 1, scenario.Initial, scenario.Calls, scenario.TraceCallIndexes },
    };

    public static async Task<P28IgnitionSelectorValidationReport> ExecuteAsync(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, string runner, P28IgnitionSelectorScenario scenario,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28IgnitionMapInspector.LayoutGuard(original);
        ProducerLayoutGuard(original);
        var mutated = scenario.Mutation is null ? null : P28IgnitionMapInspector.Mutate(original, scenario.Mutation);
        if (mutated is not null) { P28IgnitionMapInspector.AdmitMutation(original, mutated, scenario.Mutation!); ProducerLayoutGuard(mutated); }
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(original, mutated, scenario), options,
            cancellationToken).ConfigureAwait(false);
        try { return Analyze(original, mutated, profile, scenario, response.Response); }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or KeyNotFoundException or
            FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2g selector-chain response.", exception); }
    }

    private static void ProducerLayoutGuard(RomImage image)
    {
        var b = image.Span;
        Require(b[0x5F93] == 0x62 && b[0x5F98] == 0x95 && b[0x5F99] == 0x90 &&
            b[0x5FA0] == 0x90 && b[0x5FA4] == 0xC9 && b[0x5FAC] == 0xC4 &&
            b[0x60FB] == 0 && b[0x60EA] == 0 && b[0x7E02] == 0,
            "M2g native selector producer/configuration differs from the bound original.");
    }

    internal static P28IgnitionSelectorValidationReport Analyze(RomImage original, RomImage? mutated,
        RomProfile profile, P28IgnitionSelectorScenario scenario, JsonElement root)
    {
        _ = SliceRunnerIdentity.Validate(root, Operation);
        var contracts = root.GetProperty("entryContracts");
        Require(contracts.GetArrayLength() == 1 && contracts[0].GetProperty("id").GetString() == Operation &&
            contracts[0].GetProperty("producer").GetProperty("entry").GetInt32() == 0x5F93 &&
            contracts[0].GetProperty("producer").GetProperty("exit").GetInt32() == 0x5FAF &&
            contracts[0].GetProperty("producer").GetProperty("lrb").GetInt32() == 0x41 &&
            contracts[0].GetProperty("sourceInputs").GetArrayLength() == 1 &&
            contracts[0].GetProperty("sourceInputs")[0].GetString() == "DATA03C7" &&
            !contracts[0].GetProperty("perCallMapId").GetBoolean() &&
            contracts[0].GetProperty("assumptions").GetArrayLength() == 0,
            "M2g runner capability/producer contract differs.");
        var rows = root.GetProperty("ignitionSelectorSequences");
        Require(rows.GetArrayLength() == (mutated is null ? 3 : 6), "M2g image/scratch sequence count differs.");
        var sequences = new List<P28IgnitionSelectorSequence>();
        var seen = new HashSet<(int, int)>();
        foreach (var sequence in rows.EnumerateArray())
        {
            var imageIndex = sequence.GetProperty("imageIndex").GetInt32();
            var pattern = sequence.GetProperty("scratchPattern").GetInt32();
            Require(imageIndex is 0 or 1 && (imageIndex == 0 || mutated is not null) && Patterns.Contains(pattern) &&
                seen.Add((imageIndex, pattern)), "Duplicate or unknown M2g sequence.");
            var image = imageIndex == 0 ? original : mutated!;
            var model = new P28IgnitionSelectorModel(image, scenario.Initial);
            var cps = sequence.GetProperty("checkpoints");
            Require(cps.GetArrayLength() == scenario.Calls.Count, "Missing M2g terminal suffix.");
            var reports = new List<P28IgnitionSelectorCheckpoint>();
            var previous = scenario.Initial.Ignition;
            var previousSource = scenario.Initial.Source03c7;
            var stopped = false;
            foreach (var cp in cps.EnumerateArray())
            {
                var index = reports.Count; var status = cp.GetProperty("status").GetInt32();
                Require(cp.GetProperty("index").GetInt32() == index && status is >= 0 and <= 4,
                    "M2g event index/status differs.");
                var before = State(cp, "stateBefore"); var after = State(cp, "stateAfter");
                var sourceBefore = cp.GetProperty("sourceBefore").GetByte();
                var differences = new List<string>();
                void Check(bool value, string why) { if (!value) differences.Add(why); }
                Check(before == previous && sourceBefore == previousSource, "Persistent state/source history discontinuity");
                var producer = ParseStage(cp.GetProperty("producer"), "producer", scenario.TraceCallIndexes.Contains(index));
                var axes = ParseStage(cp.GetProperty("axes"), "axes", true);
                var selection = ParseStage(cp.GetProperty("selection"), "selection", true);
                var lookup = ParseStage(cp.GetProperty("lookup"), "lookup", true);
                var consumer = ParseStage(cp.GetProperty("consumer"), "consumer", true);
                int? Number(string field) => cp.GetProperty(field).ValueKind == JsonValueKind.Null ? null : cp.GetProperty(field).GetInt32();
                var origin = Number("selectedOrigin"); var value = Number("lookupResult"); var output = Number("consumerOutput");
                var map = origin switch { 0x72E4 => "ignition_map_0", 0x73AC => "ignition_map_1", _ => null };
                if (stopped)
                {
                    Require(status == 4 && cp.GetProperty("input").ValueKind == JsonValueKind.Null &&
                        cp.GetProperty("stateAfterInputs").ValueKind == JsonValueKind.Null &&
                        cp.GetProperty("sourceAfterInputs").ValueKind == JsonValueKind.Null &&
                        producer is null && axes is null && selection is null && lookup is null && consumer is null &&
                        origin is null && value is null && output is null && before == after,
                        "Terminal M2g suffix applied inputs or fabricated output.");
                }
                else
                {
                    Require(cp.GetProperty("input").ValueKind != JsonValueKind.Null &&
                        cp.GetProperty("sourceAfterInputs").GetByte() == scenario.Calls[index].Source03c7 &&
                        producer is not null, "M2g raw input/producer observation missing.");
                    Check(State(cp, "stateAfterInputs") == before, "Host wrote selector/cache/factor before producer");
                    Check(producer!.Result.Status == 0 || axes is null, "Downstream ran after producer failure");
                    Check(status == (consumer?.Result.Status ?? lookup?.Result.Status ?? selection?.Result.Status ??
                        axes?.Result.Status ?? producer.Result.Status) || status == 1 && producer.Result.Status == 0 && axes is null,
                        "M2g status contradicts last executed stage.");
                    if (status == 0)
                    {
                        Require(axes is not null && selection is not null && lookup is not null && consumer is not null &&
                            origin is not null && value is not null && output is not null,
                            "Completed M2g event lacks downstream native stage/output.");
                        var expected = model.Step(scenario.Calls[index]);
                        Check(sourceBefore == expected.SourceBefore &&
                            producer.Result.ProgramReads.SequenceEqual(expected.ProducerProgramReads) &&
                            producer.Events.Select(e => e[0]).SequenceEqual(expected.ProducerPath),
                            "Native producer source/program reads and exact branch path");
                        Check(producer.Events.Any(e => e[0] == 0x5F96 && (e[3] & 255) == scenario.Calls[index].Source03c7) &&
                            producer.Events.Any(e => e[0] == 0x5F98 && (e[5] & 0x8000) == 0) &&
                            producer.Events.Any(e => e[0] == 0x5FA4 && e[1] == 0x5FAC) &&
                            producer.Writes.Where(w => w[0] is 0x209 or 0x208 or 0x227)
                                .Select(w => (w[0], w[1], w[2]))
                                .SequenceEqual(new[] { (0x209, 8, (int)scenario.Calls[index].Source03c7),
                                    (0x208, 8, 0), (0x227, 8, (int)expected.SelectorAfterProducer) }),
                            "Native source value, carry reset, config branch and DATA0227.5 store");
                        Check((before.Selector0227 & ~0x20) == (after.Selector0227 & ~0x20) &&
                            (after.Selector0227 & 0x20) == 0,
                            "Selector overwrite/whole-byte neighboring-bit preservation");
                        Check(before == expected.Before && after == expected.Ignition.After &&
                            expected.Ignition.AfterInputs.Selector0227 == expected.SelectorAfterProducer,
                            "Independent selector/axis/cache/consumer history");
                        Check(origin == expected.Ignition.SelectedOrigin && map == expected.Ignition.SelectedMap &&
                            origin == 0x72E4, "Observed native map origin differs from independent model");
                        var position = cp.GetProperty("position");
                        var rpm = expected.Ignition.Map0Rpm;
                        Check(position.GetProperty("loadIndex").GetInt32() == expected.Ignition.Load.Index &&
                            position.GetProperty("loadFraction").GetInt32() == expected.Ignition.Load.Fraction &&
                            position.GetProperty("rpmIndex").GetInt32() == rpm.Index &&
                            position.GetProperty("rpmFraction").GetInt32() == rpm.Fraction,
                            "Native index/fraction observation");
                        Check(axes!.Result.ProgramReads.SequenceEqual(expected.Ignition.Map0Rpm.OrderedProgramReads
                            .Concat(expected.Ignition.Map1Rpm.OrderedProgramReads).Concat(expected.Ignition.Load.OrderedProgramReads)) &&
                            lookup!.Result.ProgramReads.SequenceEqual(expected.Ignition.Operands.OrderedProgramReads),
                            "Ordered axis and four-cell program reads");
                        Check(value == expected.Ignition.Operands.LookupResult && output == expected.Ignition.Consumer.Output,
                            "Independent Q16 lookup and factor consumer");
                        Check(lookup!.Events.Any(e => e[0] == 0x5A0C && e[3] == expected.Ignition.Operands.CellValues[0]) &&
                            lookup.Events.Any(e => e[0] == 0x5A13 && e[3] == expected.Ignition.Operands.CellValues[1]) &&
                            lookup.Events.Any(e => e[0] == 0x5A18 && e[3] == expected.Ignition.Operands.CellValues[3]) &&
                            lookup.Events.Any(e => e[0] == 0x5A1E && e[3] == expected.Ignition.Operands.CellValues[2]) &&
                            lookup.Events.Any(e => e[1] == 0x5A29 && e[3] == expected.Ignition.Operands.BottomColumnResult) &&
                            lookup.Events.Any(e => e[1] == 0x5A30 && e[3] == expected.Ignition.Operands.TopColumnResult),
                            "Four native cells and independently truncated column intermediates");
                        Check(consumer!.Writes.Any(w => w[0] == 0x248 && w[1] == 8 && w[2] == output) &&
                            (expected.Ignition.Consumer.ScalingExecuted
                                ? consumer.Events.Any(e => e[0] == 0x0BBA && e[3] == expected.Ignition.Consumer.Product)
                                : consumer.Events.All(e => e[0] != 0x0BBA)),
                            "Native DATA0248 store/consumer branch/product");
                        Check(SameBoundary(cp, "selectionExit", "lookupEntry") &&
                            SameBoundary(cp, "lookupExit", "consumerEntry") &&
                            cp.GetProperty("producerExit").GetProperty("pc").GetInt32() == 0x5FAF &&
                            cp.GetProperty("producerExit").GetProperty("lrb").GetInt32() == 0x41 &&
                            cp.GetProperty("axesEntry").GetProperty("pc").GetInt32() == 0x0A0C &&
                            cp.GetProperty("selectionEntry").GetProperty("pc").GetInt32() == 0x0B64,
                            "Scripted caller boundaries or unbroken selection-to-consumer tail");
                        foreach (var stage in new[] { (producer!, 0x5FAF), (axes!, 0x0A62), (selection!, 0x0BAF),
                            (lookup!, 0x0BB4), (consumer!, 0x0BD4) })
                            Check(stage.Item1.Result.StopPc == stage.Item2 && stage.Item1.Ssp == 0x7FE,
                                "Native stage exit or stack balance");
                    }
                }
                var disposition = differences.Count != 0 ? "Mismatch" : status switch
                { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                reports.Add(new(index, disposition, status, before.Selector0227, after.Selector0227,
                    map, origin, value, output, differences.AsReadOnly(), cp.Clone()));
                previous = after;
                previousSource = cp.GetProperty("sourceAfterInputs").ValueKind == JsonValueKind.Null ? sourceBefore :
                    cp.GetProperty("sourceAfterInputs").GetByte();
                stopped |= status != 0;
            }
            Require(sequence.GetProperty("completedCalls").GetInt32() == reports.Count(r => r.Status == 0) &&
                sequence.GetProperty("stopCallIndex").GetInt32() == (reports.FindIndex(r => r.Status != 0) is var stop && stop < 0 ? -1 : stop),
                "M2g sequence completion/terminal index differs.");
            sequences.Add(new(imageIndex, pattern, sequence.GetProperty("completedCalls").GetInt32(),
                sequence.GetProperty("stopCallIndex").GetInt32(), reports.AsReadOnly()));
        }
        var comparisons = Compare(sequences, scenario);
        var changed = scenario.Mutation is null ? Array.Empty<int>() :
            new[] { P28IgnitionMapContract.CellOffset(scenario.Mutation.MapId, scenario.Mutation.Row, scenario.Mutation.Column) };
        return new(1, "native-ignition-selector-chain", original.Hash, mutated?.Hash, profile.Id, scenario.Digest,
            root.GetProperty("runnerVersion").GetString()!, scenario.Mutation, changed, sequences.AsReadOnly(), comparisons);
    }

    private static IReadOnlyList<P28IgnitionSelectorComparison> Compare(
        IReadOnlyList<P28IgnitionSelectorSequence> sequences, P28IgnitionSelectorScenario scenario)
    {
        if (scenario.Mutation is null) return [];
        var offset = P28IgnitionMapContract.CellOffset(scenario.Mutation.MapId, scenario.Mutation.Row, scenario.Mutation.Column);
        var rows = new List<P28IgnitionSelectorComparison>();
        foreach (var pattern in Patterns)
        {
            var a = sequences.Single(s => s.ImageIndex == 0 && s.ScratchPattern == pattern).Checkpoints;
            var b = sequences.Single(s => s.ImageIndex == 1 && s.ScratchPattern == pattern).Checkpoints;
            for (var i = 0; i < a.Count; i++)
            {
                var x = a[i]; var y = b[i];
                if (x.Disposition != "StrictMatch" || y.Disposition != "StrictMatch")
                { rows.Add(new(pattern, i, null, null, null, null, "NotComparable")); continue; }
                var read = y.Actual.GetProperty("lookup").GetProperty("result").GetProperty("programReads")
                    .EnumerateArray().Any(item => item.GetInt32() == offset);
                var control = x.SelectorBefore == y.SelectorBefore && x.SelectorAfter == y.SelectorAfter &&
                    x.SelectedOrigin == y.SelectedOrigin &&
                    x.Actual.GetProperty("producer").GetProperty("result").GetProperty("programReads").GetRawText() ==
                    y.Actual.GetProperty("producer").GetProperty("result").GetProperty("programReads").GetRawText() &&
                    x.Actual.GetProperty("axes").GetProperty("result").GetProperty("programReads").GetRawText() ==
                    y.Actual.GetProperty("axes").GetProperty("result").GetProperty("programReads").GetRawText();
                var effect = !control ? "ControlFailure" : !read ? "CellNotRead" : x.Lookup == y.Lookup ?
                    "ReadMaskedByWeightOrTruncation" : x.Data0248 == y.Data0248 ?
                    "LookupChangedConsumerMasked" : "LookupAndConsumerChanged";
                rows.Add(new(pattern, i, read, control, x.Lookup != y.Lookup, x.Data0248 != y.Data0248, effect));
            }
        }
        return rows.AsReadOnly();
    }

    private static bool SameBoundary(JsonElement cp, string left, string right) =>
        cp.GetProperty(left).GetRawText() == cp.GetProperty(right).GetRawText();

    private static P28IgnitionMapState State(JsonElement cp, string field) =>
        cp.GetProperty(field).Deserialize<P28IgnitionMapState>(P28StatefulScenario.Options)!;

    private static Stage? ParseStage(JsonElement element, string name, bool traced)
    {
        if (element.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(element, "result", "writes", "events", "sspAfter");
        var budget = name switch
        {
            "producer" => 32,
            "axes" => 576,
            "selection" => 64,
            "lookup" => 192,
            "consumer" => 32,
            _ => throw new InvalidDataException("Unknown M2g stage.")
        };
        var result = P28AcquisitionValidator.ParseStage(element.GetProperty("result"), budget, 0, [], null)!;
        int[][] Matrix(string field, int width)
        {
            var arr = element.GetProperty(field);
            Require(arr.GetArrayLength() <= 1024, "M2g stage journal is unbounded.");
            return arr.EnumerateArray().Select(row =>
            {
                var values = row.EnumerateArray().Select(item => item.GetInt32()).ToArray();
                Require(values.Length == width && values.All(value => value is >= 0 and <= 65536),
                    "Malformed M2g stage journal.");
                return values;
            }).ToArray();
        }
        var writes = Matrix("writes", 3); var events = Matrix("events", 8);
        var ssp = element.GetProperty("sspAfter").GetInt32();
        Require(ssp is >= 0 and <= 65535 && events.Length == result.Steps &&
            result.Trace.Count == (traced ? Math.Min(128, result.Steps) : 0),
            "M2g stage events/trace/stack are incomplete.");
        var pc = name switch
        {
            "producer" => 0x5F93,
            "axes" => 0x0A0C,
            "selection" => 0x0B64,
            "lookup" => 0x0BAF,
            _ => 0x0BB4
        };
        foreach (var e in events) { Require(e[0] == pc, "M2g native event path is discontinuous."); pc = e[1]; }
        Require(result.StopPc == pc, "M2g stage stop PC contradicts ordered events.");
        return new(result, writes, events, ssp);
    }
}
