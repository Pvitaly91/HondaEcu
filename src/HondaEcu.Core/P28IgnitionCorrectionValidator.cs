using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28IgnitionCorrectionCheckpoint(int Index, string Disposition, int Status,
    int? SelectedOrigin, int? Lookup, int? Data0248, int? NativeRead0248,
    int? CorrectedRaw, int? BoundedRaw, int? Result035b, int? Result024a,
    IReadOnlyList<string> Differences, JsonElement Actual);
public sealed record P28IgnitionCorrectionSequence(int ImageIndex, int ScratchPattern,
    int CompletedCalls, int StopCallIndex, IReadOnlyList<P28IgnitionCorrectionCheckpoint> Checkpoints);
public sealed record P28IgnitionCorrectionComparison(int ScratchPattern, int Index,
    bool? CellRead, bool? ControlValid, bool? LookupChanged, bool? BaseChanged,
    bool? CorrectedChanged, string Effect);
public sealed record P28IgnitionCorrectionValidationReport(int FormatVersion, string Purpose,
    RomHash OriginalHash, RomHash? MutatedHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28IgnitionMapMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28IgnitionCorrectionSequence> Sequences,
    IReadOnlyList<P28IgnitionCorrectionComparison> Comparisons)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints)
        .Any(c => c.Disposition is not ("StrictMatch" or "ConditionalMatch")) ||
        Comparisons.Any(c => c.ControlValid == false);
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw / physical degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; optional B is one-cell memory-only comparison";
}

public static class P28IgnitionCorrectionValidator
{
    public const string Operation = "ignitionCorrectionChain";
    private static readonly int[] Patterns = [0, 85, 170];

    public static object CreateRequest(RomImage original, RomImage? mutated,
        P28IgnitionCorrectionScenario scenario) => new
        {
            protocolVersion = 1,
            operation = Operation,
            images = mutated is null
            ? [new { id = "baseline", rom = original.ToArray().Select(b => (int)b).ToArray() }]
            : new[] { new { id = "baseline", rom = original.ToArray().Select(b => (int)b).ToArray() },
                new { id = "mutated", rom = mutated.ToArray().Select(b => (int)b).ToArray() } },
            scratchPatterns = Patterns,
            allowAssumptions = scenario.PermitAddEr3Assumption ? ["oki.add-er3-a"] : Array.Empty<string>(),
            ignitionCorrectionChain = new { formatVersion = 1, scenario.Initial, scenario.Calls, scenario.TraceCallIndexes },
        };

    public static async Task<P28IgnitionCorrectionValidationReport> ExecuteAsync(RomImage original,
        RomProfile profile, P28ExactBaselineBinding binding, bool confirmed, string runner,
        P28IgnitionCorrectionScenario scenario, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28IgnitionMapInspector.LayoutGuard(original);
        var mutated = scenario.Mutation is null ? null : P28IgnitionMapInspector.Mutate(original, scenario.Mutation);
        if (mutated is not null)
            P28IgnitionMapInspector.AdmitMutation(original, mutated, scenario.Mutation!);
        var response = await SeededSliceProcess.ExchangeAsync(runner,
            CreateRequest(original, mutated, scenario), options, cancellationToken).ConfigureAwait(false);
        try { return Analyze(original, mutated, profile, scenario, response.Response); }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or
            KeyNotFoundException or FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2i correction-chain response.", exception); }
    }

    internal static P28IgnitionCorrectionValidationReport Analyze(RomImage original, RomImage? mutated,
        RomProfile profile, P28IgnitionCorrectionScenario scenario, JsonElement root)
    {
        _ = SliceRunnerIdentity.Validate(root, Operation);
        var contracts = root.GetProperty("entryContracts");
        Require(contracts.GetArrayLength() == 1 && contracts[0].GetProperty("id").GetString() == Operation &&
            contracts[0].GetProperty("producer").GetProperty("entry").GetInt32() == 0x5F93 &&
            contracts[0].GetProperty("correction").GetProperty("entry").GetInt32() == 0x0F85 &&
            contracts[0].GetProperty("correction").GetProperty("exit").GetInt32() == 0x1076 &&
            contracts[0].GetProperty("nativeReader0248").GetInt32() == 0x0FF4 &&
            contracts[0].GetProperty("assumptions").GetArrayLength() == 0,
            "M2i runner capability/entry contract differs.");
        var rows = root.GetProperty("ignitionCorrectionSequences");
        Require(rows.GetArrayLength() == (mutated is null ? 3 : 6), "M2i image/scratch count differs.");
        var sequences = new List<P28IgnitionCorrectionSequence>();
        var seen = new HashSet<(int, int)>();
        foreach (var sequence in rows.EnumerateArray())
        {
            var imageIndex = sequence.GetProperty("imageIndex").GetInt32();
            var pattern = sequence.GetProperty("scratchPattern").GetInt32();
            Require(imageIndex is 0 or 1 && (imageIndex == 0 || mutated is not null) &&
                Patterns.Contains(pattern) && seen.Add((imageIndex, pattern)), "Unknown or duplicate M2i sequence.");
            var model = new P28IgnitionCorrectionModel(imageIndex == 0 ? original : mutated!, scenario.Initial);
            var checkpoints = sequence.GetProperty("checkpoints");
            Require(checkpoints.GetArrayLength() == scenario.Calls.Count, "M2i terminal suffix incomplete.");
            var reports = new List<P28IgnitionCorrectionCheckpoint>();
            var previous = scenario.Initial.Ignition;
            var retained = (scenario.Initial.Retained035b, scenario.Initial.Retained024a);
            var stopped = false;
            foreach (var cp in checkpoints.EnumerateArray())
            {
                var index = reports.Count; var status = cp.GetProperty("status").GetInt32();
                Require(cp.GetProperty("index").GetInt32() == index && status is >= 0 and <= 4,
                    "M2i index/status differs.");
                var differences = new List<string>();
                void Check(bool condition, string label) { if (!condition) differences.Add(label); }
                int? Number(string field) => cp.GetProperty(field).ValueKind == JsonValueKind.Null
                    ? null : cp.GetProperty(field).GetInt32();
                var before = cp.GetProperty("stateBefore").Deserialize<P28IgnitionMapState>(P28StatefulScenario.Options)!;
                var after = cp.GetProperty("stateAfter").Deserialize<P28IgnitionMapState>(P28StatefulScenario.Options)!;
                Check(before == previous && cp.GetProperty("retained035bBefore").GetByte() == retained.Item1 &&
                    cp.GetProperty("retained024aBefore").GetByte() == retained.Item2,
                    "Persistent state or retained-result history discontinuity");
                var producer = cp.GetProperty("producer"); var axes = cp.GetProperty("axes");
                var selection = cp.GetProperty("selection"); var lookup = cp.GetProperty("lookup");
                var consumer = cp.GetProperty("consumer"); var correction = cp.GetProperty("correction");
                var origin = Number("selectedOrigin"); var lookupValue = Number("lookupResult");
                var base0248 = Number("data0248"); var reader0248 = Number("nativeRead0248");
                var corrected = Number("correctedRaw"); var bounded = Number("boundedRaw");
                var next = Number("result035b"); var result = Number("result024a");
                if (stopped)
                {
                    Require(status == 4 && cp.GetProperty("input").ValueKind == JsonValueKind.Null &&
                        producer.ValueKind == JsonValueKind.Null && axes.ValueKind == JsonValueKind.Null &&
                        selection.ValueKind == JsonValueKind.Null && lookup.ValueKind == JsonValueKind.Null &&
                        consumer.ValueKind == JsonValueKind.Null && correction.ValueKind == JsonValueKind.Null &&
                        origin is null && lookupValue is null && base0248 is null && reader0248 is null &&
                        corrected is null && bounded is null && next is null && result is null && before == after,
                        "M2i terminal suffix applied inputs or fabricated result.");
                }
                else
                {
                    Require(cp.GetProperty("input").ValueKind != JsonValueKind.Null &&
                        producer.ValueKind != JsonValueKind.Null, "M2i applied input/producer missing.");
                    foreach (var stage in new[] { producer, axes, selection, lookup, consumer })
                        if (stage.ValueKind != JsonValueKind.Null)
                            Check(stage.GetProperty("result").GetProperty("status").GetInt32() == 0,
                                "Prefix stage did not complete strictly");
                    if (consumer.ValueKind != JsonValueKind.Null && base0248 is not null)
                    {
                        var expected = model.Step(scenario.Calls[index]);
                        var e = expected.Correction;
                        Check(before == expected.Prefix.Before && after == expected.Prefix.Ignition.After &&
                            origin == expected.Prefix.Ignition.SelectedOrigin &&
                            lookupValue == expected.Prefix.Ignition.Operands.LookupResult &&
                            base0248 == e.Base0248,
                            "Independent selector/axes/lookup/base history");
                        Check(Writes(consumer).Any(w => w[0] == 0x248 && w[1] == 8 && w[2] == e.Base0248),
                            "DATA0248 was not natively stored by consumer");
                        Check(cp.GetProperty("consumerExit").GetProperty("pc").GetInt32() == 0x0BD4 &&
                            cp.GetProperty("correctionEntry").GetProperty("pc").GetInt32() == 0x0F85 &&
                            cp.GetProperty("consumerExit").GetProperty("ssp").GetInt32() ==
                            cp.GetProperty("correctionEntry").GetProperty("ssp").GetInt32(),
                            "Scripted prefix-to-correction entry or stack context");
                        if (correction.ValueKind != JsonValueKind.Null)
                        {
                            var observed = Events(correction);
                            Check(Writes(correction).All(w => w[0] != 0x248),
                                "Host or correction overwrote DATA0248 after consumer");
                            if (status == 0)
                            {
                                Check(reader0248 == e.Base0248 &&
                                    HandoffMatches(consumer, correction, e.Base0248),
                                    "Native 0FF4 read differs from native 0248 store");
                                Check(cp.GetProperty("correctionMode0207Bit7").GetBoolean() == e.Mode0207Bit7 &&
                                    corrected == e.CorrectedRaw && bounded == e.BoundedRaw &&
                                    next == e.Result035b && result == e.Result024a,
                                    "Independent word arithmetic, bound, floor or stored result");
                                Check(observed.Any(v => v[0] == 0x0FF9 && v[3] == e.CorrectedRaw) &&
                                    observed.Any(v => v[0] == 0x0FFA && v[1] ==
                                        (e.Mode0207Bit7 ? 0x0FFD : 0x1002)) &&
                                    observed.Any(v => v[0] == 0x104D && (v[3] & 255) == e.BoundedRaw),
                                    "Correction intermediate or ordered branch path");
                                Check(Writes(correction).Where(w => w[0] == 0x206 && w[1] == 16)
                                    .Select(w => w[2]).SequenceEqual(new[] { 0,
                                        (int)unchecked((ushort)e.SignedCorrection0245),
                                        (int)e.CorrectionAccumulator }) &&
                                    observed.Any(v => v[0] == 0x0F87 && v[1] == 0x0FE9) &&
                                    observed.Any(v => v[0] == 0x0FE9 && (v[3] & 255) ==
                                        scenario.Calls[index].Correction0245) &&
                                    observed.Any(v => v[0] == 0x0FEF && (v[3] & 255) == e.Subtrahend0246),
                                    "Native er3 initialization/sign-extension/subtraction or operands");
                                Check(observed.Any(v => v[0] == 0x104F && v[1] ==
                                        (e.BoundedRaw >= e.Floor024c ? 0x1052 : 0x1051)) &&
                                    observed.Any(v => v[0] == 0x1061 && v[1] ==
                                        (scenario.Initial.Gate021eBit0 ? 0x1067 : 0x1064)) &&
                                    (scenario.Initial.Gate021eBit0 || observed.Any(v => v[0] == 0x1064 &&
                                        v[1] == (e.Gate0217Bit1 ? 0x1067 : 0x106D))) &&
                                    (e.ClearedByGate || observed.Any(v => v[0] == 0x1070 &&
                                        v[1] == (e.BiasOverflow ? 0x1072 : 0x1074))),
                                    "Native floor, clear and bias-carry branches");
                                Check(Writes(correction).Any(w => w[0] == 0x234 &&
                                        ((w[2] & 0x20) != 0) == e.Gate0234Bit5After) &&
                                    Writes(correction).Any(w => w[0] == 0x217 &&
                                        ((w[2] & 0x02) != 0) == e.Gate0217Bit1) &&
                                    Writes(correction).Any(w => w[0] == 0x221 && (w[2] & 0x80) != 0),
                                    "Persistent gate writes or neighboring-bit state");
                                Check(Writes(correction).Any(w => w[0] == 0x35B && w[2] == e.Result035b) &&
                                    Writes(correction).Any(w => w[0] == 0x24A && w[2] == e.Result024a) &&
                                    correction.GetProperty("result").GetProperty("stopPc").GetInt32() == 0x1076,
                                    "Native software-result stores or exit");
                                Check(cp.GetProperty("conditionalDependency").GetBoolean() &&
                                    correction.GetProperty("result").GetProperty("usedAssumptions")
                                        .EnumerateArray().Any(x => x.GetString() == "oki.add-er3-a"),
                                    "Reached er3 form was not disclosed as conditional");
                            }
                            else if (!scenario.PermitAddEr3Assumption)
                            {
                                Check(status == 1 && correction.GetProperty("result").GetProperty("stopPc")
                                    .GetInt32() == 0x0FEC && reader0248 is null && corrected is null &&
                                    bounded is null && next is null && result is null &&
                                    cp.GetProperty("error").GetString()!.Contains("oki.add-er3-a", StringComparison.Ordinal),
                                    "Strict unresolved boundary or partial-output nulls");
                            }
                        }
                        if (status == 0) retained = model.Retained;
                    }
                }
                var disposition = differences.Count != 0 ? "Mismatch" : status switch
                {
                    0 => cp.GetProperty("conditionalDependency").GetBoolean() ? "ConditionalMatch" : "StrictMatch",
                    1 => "Unresolved",
                    2 => "ExecutionError",
                    3 => "BudgetExceeded",
                    _ => "NotRun"
                };
                reports.Add(new(index, disposition, status, origin, lookupValue, base0248, reader0248,
                    corrected, bounded, next, result, differences.AsReadOnly(), cp.Clone()));
                previous = after; stopped |= status != 0;
            }
            Require(sequence.GetProperty("completedCalls").GetInt32() == reports.Count(c => c.Status == 0) &&
                sequence.GetProperty("stopCallIndex").GetInt32() == reports.FindIndex(c => c.Status != 0),
                "M2i completed count or terminal index differs.");
            sequences.Add(new(imageIndex, pattern, sequence.GetProperty("completedCalls").GetInt32(),
                sequence.GetProperty("stopCallIndex").GetInt32(), reports.AsReadOnly()));
        }
        var comparisons = Compare(sequences, scenario);
        var changed = scenario.Mutation is null ? Array.Empty<int>() :
            new[] { P28IgnitionMapContract.CellOffset(scenario.Mutation.MapId,
                scenario.Mutation.Row, scenario.Mutation.Column) };
        return new(1, "native-ignition-correction-chain", original.Hash, mutated?.Hash, profile.Id,
            scenario.Digest, root.GetProperty("runnerVersion").GetString()!, scenario.Mutation,
            changed, sequences.AsReadOnly(), comparisons);
    }

    private static int[][] Writes(JsonElement stage) => Matrix(stage, "writes", 3);
    private static int[][] Events(JsonElement stage) => Matrix(stage, "events", 8);
    internal static bool HandoffMatches(JsonElement consumer, JsonElement correction, int expectedBase) =>
        Writes(consumer).Any(w => w[0] == 0x248 && w[1] == 8 && w[2] == expectedBase) &&
        Writes(correction).All(w => w[0] != 0x248) &&
        Events(correction).Any(e => e[0] == 0x0FF4 && (e[3] & 255) == expectedBase);
    private static int[][] Matrix(JsonElement stage, string field, int width)
    {
        var rows = stage.GetProperty(field);
        Require(rows.GetArrayLength() <= 512, "M2i stage journal unbounded.");
        return rows.EnumerateArray().Select(row =>
        {
            var values = row.EnumerateArray().Select(x => x.GetInt32()).ToArray();
            Require(values.Length == width && values.All(x => x is >= 0 and <= 65536),
                "Malformed M2i stage journal.");
            return values;
        }).ToArray();
    }

    private static IReadOnlyList<P28IgnitionCorrectionComparison> Compare(
        IReadOnlyList<P28IgnitionCorrectionSequence> sequences, P28IgnitionCorrectionScenario scenario)
    {
        if (scenario.Mutation is null) return [];
        var offset = P28IgnitionMapContract.CellOffset(scenario.Mutation.MapId,
            scenario.Mutation.Row, scenario.Mutation.Column);
        var result = new List<P28IgnitionCorrectionComparison>();
        foreach (var pattern in Patterns)
        {
            var a = sequences.Single(s => s.ImageIndex == 0 && s.ScratchPattern == pattern).Checkpoints;
            var b = sequences.Single(s => s.ImageIndex == 1 && s.ScratchPattern == pattern).Checkpoints;
            for (var i = 0; i < a.Count; i++)
            {
                var x = a[i]; var y = b[i];
                if (x.Disposition is not ("ConditionalMatch" or "StrictMatch") ||
                    y.Disposition is not ("ConditionalMatch" or "StrictMatch"))
                { result.Add(new(pattern, i, null, null, null, null, null, "NotComparable")); continue; }
                var read = y.Actual.GetProperty("lookup").GetProperty("result").GetProperty("programReads")
                    .EnumerateArray().Any(item => item.GetInt32() == offset);
                var controls = new[] { "producer", "axes", "selection" }.All(stage =>
                    x.Actual.GetProperty(stage).GetProperty("result").GetProperty("programReads").GetRawText() ==
                    y.Actual.GetProperty(stage).GetProperty("result").GetProperty("programReads").GetRawText()) &&
                    x.SelectedOrigin == y.SelectedOrigin;
                var effect = !controls ? "ControlFailure" : !read ? "CellNotRead" :
                    x.Lookup == y.Lookup ? "ReadMaskedByWeightOrTruncation" :
                    x.Data0248 == y.Data0248 ? "LookupChangedConsumerMasked" :
                    x.Result024a == y.Result024a ? "BaseChangedCorrectionOrClampMasked" :
                    "LookupBaseAndCorrectionChanged";
                result.Add(new(pattern, i, read, controls, x.Lookup != y.Lookup,
                    x.Data0248 != y.Data0248, x.Result024a != y.Result024a, effect));
            }
        }
        return result.AsReadOnly();
    }
}
