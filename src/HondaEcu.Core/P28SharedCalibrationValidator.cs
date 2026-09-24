using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed record P28SharedStageEvidence(string Name, int Status, int StopPc, int Steps,
    IReadOnlyList<int> ProgramReads, IReadOnlyList<int[]> Writes, IReadOnlyList<string> UsedAssumptions);
public sealed record P28SharedCheckpoint(int Index, string Disposition, int Status, bool ConditionalDependency,
    bool IgnitionCompleted, bool WholeEventCompleted, byte SelectorBefore0227, byte SelectorAfter0227,
    bool? RequestP1, bool? RequestMirror0127, bool? FuelSelector0127,
    int? IgnitionOrigin, int? IgnitionLookup, int? Data0248,
    int? FuelOrigin, int? FuelLookup, int? Data0140, bool? ChangedByteRead,
    P28SharedState StateAfter, IReadOnlyList<P28SharedStageEvidence> Stages,
    IReadOnlyList<string> Differences, JsonElement? Witness);
public sealed record P28SharedSequence(int ImageIndex, int ScratchPattern, int CompletedCalls,
    int StopCallIndex, IReadOnlyList<P28SharedCheckpoint> Checkpoints);
public sealed record P28SharedComparison(int ScratchPattern, int Index, bool? ChangedByteRead,
    bool? ControlValid, bool? IgnitionChanged, bool? VtecChanged, bool? FuelChanged, string Effect);
public sealed record P28SharedValidationReport(int FormatVersion, string Purpose, RomHash OriginalHash,
    RomHash? MutatedHash, string ProfileId, string ScenarioDigest, string RunnerVersion,
    IReadOnlyList<string> AllowedAssumptions, P28SharedMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28SharedSequence> Sequences, IReadOnlyList<P28SharedComparison> Comparisons)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c =>
        c.Disposition is "Mismatch" or "ExecutionError" or "BudgetExceeded") || Comparisons.Any(c => c.ControlValid == false);
    public bool HasIncomplete => Sequences.SelectMany(s => s.Checkpoints).Any(c =>
        !c.WholeEventCompleted && c.Disposition != "NotRun");
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw / physical degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; optional B is a single in-memory code-owned byte.";
}

/// <summary>Independent combined history against a single native CPU/RAM sequence.</summary>
public static class P28SharedCalibrationValidator
{
    public const string Operation = "vtecFuelIgnitionChain";
    private static readonly int[] Patterns = [0, 85, 170];
    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events, int Ssp);

    public static IReadOnlyList<string> ValidateAssumptions(IEnumerable<string> assumptions)
    {
        var values = assumptions.ToArray();
        if (values.Length > 1 || values.Distinct(StringComparer.Ordinal).Count() != values.Length ||
            values.Any(x => x != P28StatefulModel.SubbOffAssumption))
            throw new ArgumentException("M2h permits only the exact SUBB encoding hypothesis.");
        return Array.AsReadOnly(values);
    }

    public static object CreateRequest(RomImage original, RomImage? mutated,
        P28SharedCalibrationScenario scenario, IEnumerable<string>? assumptions = null) => new
        {
            protocolVersion = 1,
            operation = Operation,
            images = mutated is null ? [new { id = "baseline", rom = original.ToArray().Select(x => (int)x).ToArray() }] :
                new[] { new { id = "baseline", rom = original.ToArray().Select(x => (int)x).ToArray() },
                    new { id = "mutated", rom = mutated.ToArray().Select(x => (int)x).ToArray() } },
            scratchPatterns = Patterns,
            allowAssumptions = ValidateAssumptions(assumptions ?? []),
            sharedCalibrationChain = new { formatVersion = 1, scenario.Initial, scenario.Calls, scenario.TraceCallIndexes },
        };

    public static async Task<P28SharedValidationReport> ExecuteAsync(RomImage original, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, string runner, P28SharedCalibrationScenario scenario,
        IEnumerable<string>? assumptions = null, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28FuelMapInspector.LayoutGuard(original);
        P28IgnitionMapInspector.LayoutGuard(original);
        RequireProducer(original);
        var allowed = ValidateAssumptions(assumptions ?? []);
        RomImage? mutated = null;
        if (scenario.Mutation is { } edit)
        {
            if (original.Span[edit.Offset] == edit.Value)
                throw new InvalidDataException("M2h B must actually change its one code-owned byte.");
            mutated = edit.Kind switch
            {
                "fuelCell" => P28FuelMapInspector.Mutate(original,
                    new P28FuelMapMutation(edit.MapId!, edit.Row!.Value, edit.Column!.Value, edit.Value)),
                "ignitionCell" => P28IgnitionMapInspector.Mutate(original,
                    new P28IgnitionMapMutation(edit.MapId!, edit.Row!.Value, edit.Column!.Value, edit.Value)),
                _ => MutateThreshold(original, edit),
            };
            RequireProducer(mutated);
            P28FuelMapInspector.LayoutGuard(mutated);
            P28IgnitionMapInspector.LayoutGuard(mutated);
        }
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(original, mutated, scenario, allowed),
            options, cancellationToken).ConfigureAwait(false);
        try { return Analyze(original, mutated, profile, scenario, allowed, response.Response); }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or KeyNotFoundException or
            FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2h shared-chain response.", ex); }
    }

    private static RomImage MutateThreshold(RomImage original, P28SharedMutation edit)
    {
        var bytes = original.ToArray(); bytes[edit.Offset] = edit.Value;
        return RomImage.FromBytes(bytes);
    }

    private static void RequireProducer(RomImage image)
    {
        var b = image.Span;
        Require(b[0x5F93] == 0x62 && b[0x5F98] == 0x95 && b[0x5F99] == 0x90 &&
            b[0x5FA0] == 0x90 && b[0x5FA4] == 0xC9 && b[0x5FAC] == 0xC4 &&
            b[0x60FB] == 0 && b[0x60EA] == 0 && b[0x7E02] == 0,
            "M2h producer/configuration differs from exact bound original.");
    }

    internal static P28SharedValidationReport Analyze(RomImage original, RomImage? mutated, RomProfile profile,
        P28SharedCalibrationScenario scenario, IReadOnlyList<string> allowed, JsonElement root)
    {
        _ = SliceRunnerIdentity.Validate(root, Operation);
        var contract = root.GetProperty("entryContracts");
        Require(contract.GetArrayLength() == 1 && contract[0].GetProperty("id").GetString() == Operation &&
            !contract[0].GetProperty("perCallMapId").GetBoolean(),
            "M2h runner capability differs.");
        Require(contract[0].GetProperty("continuousAxis").EnumerateArray().Select(x => x.GetInt32())
            .SequenceEqual(new[] { 0x0A0C, 0x0A77 }) &&
            contract[0].GetProperty("ignitionTail").EnumerateArray().Select(x => x.GetInt32())
                .SequenceEqual(new[] { 0x0B64, 0x0BD4 }) &&
            contract[0].GetProperty("fuelTail").EnumerateArray().Select(x => x.GetInt32())
                .SequenceEqual(new[] { 0x122C, 0x1350 }), "M2h continuous-stage declaration differs.");
        var rows = root.GetProperty("sharedCalibrationSequences");
        Require(rows.GetArrayLength() == (mutated is null ? 3 : 6), "M2h image/scratch count differs.");
        var sequences = new List<P28SharedSequence>(); var seen = new HashSet<(int, int)>();
        foreach (var sequence in rows.EnumerateArray())
        {
            var imageIndex = sequence.GetProperty("imageIndex").GetInt32();
            var pattern = sequence.GetProperty("scratchPattern").GetInt32();
            Require(imageIndex is 0 or 1 && (imageIndex == 0 || mutated is not null) &&
                Patterns.Contains(pattern) && seen.Add((imageIndex, pattern)), "M2h duplicate/unknown sequence.");
            var model = new P28SharedCalibrationModel(imageIndex == 0 ? original : mutated!, scenario.Initial);
            var cps = sequence.GetProperty("checkpoints");
            Require(cps.GetArrayLength() == scenario.Calls.Count, "M2h missing terminal suffix.");
            var result = new List<P28SharedCheckpoint>(); var prior = scenario.Initial; var stopped = false;
            var conditional = false; var firstErrorWitness = false;
            foreach (var cp in cps.EnumerateArray())
            {
                var index = result.Count; var status = cp.GetProperty("status").GetInt32();
                Require(cp.GetProperty("index").GetInt32() == index && status is >= 0 and <= 4,
                    "M2h checkpoint index/status differs.");
                var before = State(cp, "stateBefore"); var after = State(cp, "stateAfter");
                var differences = new List<string>();
                void Check(bool okay, string why) { if (!okay) differences.Add(why); }
                Check(before == prior, "Single shared RAM history discontinuity");
                var stages = new List<P28SharedStageEvidence>();
                Stage? Get(string field, int entry, int budget, bool permission = false)
                {
                    var stage = ParseStage(cp.GetProperty(field), entry, budget,
                        permission ? allowed : [], permission ? P28StatefulModel.SubbOffAssumption : null,
                        scenario.TraceCallIndexes.Contains(index) || field.StartsWith("ignition", StringComparison.Ordinal));
                    if (stage is not null) stages.Add(new(field, stage.Result.Status, stage.Result.StopPc,
                        stage.Result.Steps, stage.Result.ProgramReads, stage.Writes, stage.Result.UsedAssumptions));
                    return stage;
                }
                var producer = Get("producer", 0x5F93, 32);
                var axis = Get("axis", 0x0A0C, 768);
                var ignitionSelection = Get("ignitionSelection", 0x0B64, 64);
                var ignitionLookup = Get("ignitionLookup", 0x0BAF, 192);
                var ignitionConsumer = Get("ignitionConsumer", 0x0BB4, 32);
                var decision = Get("decision", 0x122C, 512, true);
                var fuelSelection = Get("fuelSelection", 0x12FC, 64);
                var fuelLookup = Get("fuelLookup", 0x1340, 192);
                var fuelConsumer = Get("fuelConsumer", 0x1347, 64);
                var ignitionDone = cp.GetProperty("ignitionCompleted").GetBoolean();
                var originI = Number(cp, "ignitionOrigin"); var valueI = Number(cp, "ignitionValue");
                var outputI = Number(cp, "ignitionOutput");
                var originF = Number(cp, "fuelOrigin"); var valueF = Number(cp, "fuelValue");
                var outputF = Number(cp, "fuelOutput");
                var tickRuns = Matrix(cp.GetProperty("tickRuns"), 5, 128);
                var tickWrites = Matrix(cp.GetProperty("tickWrites"), 3, 128);
                if (stopped)
                {
                    Require(status == 4 && cp.GetProperty("input").ValueKind == JsonValueKind.Null &&
                        cp.GetProperty("stateAfterInputs").ValueKind == JsonValueKind.Null &&
                        stages.Count == 0 && tickRuns.Length == 0 && tickWrites.Length == 0 &&
                        !ignitionDone && originI is null && valueI is null && outputI is null &&
                        originF is null && valueF is null && outputF is null && before == after,
                        "Terminal M2h suffix applied inputs, reset RAM or invented results.");
                }
                else
                {
                    var input = scenario.Calls[index];
                    Check(Equal(cp.GetProperty("input"), input), "M2h raw input echo differs");
                    Check(State(cp, "stateAfterInputs") == before with { Source03c7 = input.Source03c7 },
                        "Host wrote a native-owned selector/cache/factor/output");
                    if (ignitionDone)
                    {
                        Require(producer is not null && axis is not null && ignitionSelection is not null &&
                            ignitionLookup is not null && ignitionConsumer is not null &&
                            originI is not null && valueI is not null && outputI is not null,
                            "Completed ignition missing a native stage/result.");
                        var expected = model.Step(input, allowed.Contains(P28StatefulModel.SubbOffAssumption));
                        Check(before == expected.Before && State(cp, "stateAfterTicks") == expected.AfterTicks &&
                            State(cp, "stateAfterProducer") == expected.AfterProducer &&
                            State(cp, "stateAfterAxis") == expected.AfterAxis &&
                            State(cp, "stateAfterIgnition") == expected.AfterIgnition &&
                            after == expected.After, "Independent combined single-cache history/boundaries");
                        Check(Equal(tickWrites, expected.TickWrites) &&
                            tickRuns.Length == 2 * (input.Decision.FastTicks + input.Decision.SlowTicks) &&
                            tickRuns.All(t => t[3] == 0 && t[2] == (t[0] == 0x5BD0 ? 0x5BD9 : 0x3CF3)),
                            "Native counter bodies and writes");
                        Check(producer!.Result.ProgramReads.SequenceEqual(expected.ProducerProgramReads) &&
                            producer.Events.Select(e => e[0]).SequenceEqual(expected.ProducerPath) &&
                            producer.Events.Any(e => e[0] == 0x5F96 && (e[3] & 255) == input.Source03c7) &&
                            producer.Events.Any(e => e[0] == 0x5F98 && (e[5] & 0x8000) == 0) &&
                            producer.Writes.Where(w => w[0] is 0x209 or 0x208 or 0x227)
                                .Select(w => (w[0], w[1], w[2])).SequenceEqual(new[] {
                                    (0x209, 8, (int)input.Source03c7), (0x208, 8, 0),
                                    (0x227, 8, (int)expected.AfterProducer.Selector0227) }),
                            "Actual producer source/carry/branch/store");
                        Check((before.Selector0227 & ~0x20) == (expected.AfterProducer.Selector0227 & ~0x20) &&
                            (expected.AfterProducer.Selector0227 & 0x20) == 0 &&
                            Boundary(cp, "producerExit", 0x5FAF)?.GetProperty("lrb").GetInt32() == 0x41,
                            "Native selector overwrite/neighbor preservation/ABI");
                        var axisReads = expected.Map0Rpm.ProgramReads.Concat(expected.Map1Rpm.ProgramReads)
                            .Concat(expected.IgnitionLoad.ProgramReads).Concat(expected.FuelLoad.ProgramReads);
                        Check(axis!.Result.ProgramReads.SequenceEqual(axisReads) &&
                            axis.Events.Any(e => e[0] == 0x0A45) && axis.Events.Any(e => e[0] == 0x0A62) &&
                            axis.Result.StopPc == 0x0A77 && axis.Ssp == 0x7FE &&
                            Boundary(cp, "axisEntry", 0x0A0C) is not null &&
                            Boundary(cp, "axisExit", 0x0A77) is not null,
                            "One continuous shared axis pass and ordered reads");
                        Check(originI == expected.IgnitionOrigin && valueI == expected.IgnitionLookup &&
                            outputI == expected.IgnitionConsumer.Output &&
                            ignitionLookup!.Result.ProgramReads.SequenceEqual(expected.IgnitionCellAddresses) &&
                            ignitionConsumer!.Writes.Any(w => w[0] == 0x248 && w[1] == 8 && w[2] == outputI) &&
                            SameBoundary(cp, "ignitionSelectionExit", "ignitionLookupEntry") &&
                            SameBoundary(cp, "ignitionLookupExit", "ignitionConsumerEntry") &&
                            (Boundary(cp, "ignitionLookupEntry", 0x0BAF)?.GetProperty("psw").GetInt32() & 0x20) == 0,
                            "Native ignition origin/cells/Q16/consumer/unbroken tail/unity mode");
                        Check(decision is not null && decision.Result.Status == expected.Decision.Status &&
                            State(cp, "stateAfterDecision").Vtec == expected.Decision.After &&
                            Equal(FilterPersistent(decision.Writes), expected.Decision.DecisionWrites) &&
                            decision.Events.Where(e => P28StatefulModel.GateDefinitions.Any(g => g.Pc == e[0]))
                                .Select(e => e[0]).SequenceEqual(expected.Decision.ExecutedGatePcs) &&
                            decision.Result.UsedAssumptions.SequenceEqual(expected.Decision.UsedAssumptions),
                            "Independent native VTEC gates/selector/counters/assumption");
                        conditional |= decision!.Result.UsedAssumptions.Count != 0;
                        Check(cp.GetProperty("conditionalDependency").GetBoolean() == conditional,
                            "Cumulative conditional dependency was dropped or fabricated");
                        if (decision.Result.Status == 0)
                        {
                            Require(fuelSelection is not null && fuelLookup is not null && fuelConsumer is not null &&
                                originF is not null && valueF is not null && outputF is not null,
                                "Completed decision lacks continuous fuel suffix.");
                            Check(status == 0 && originF == expected.FuelOrigin && valueF == expected.FuelLookup &&
                                outputF == expected.FuelConsumer?.Output &&
                                fuelLookup!.Result.ProgramReads.SequenceEqual(expected.FuelProgramReads ?? []) &&
                                fuelConsumer!.Writes.Any(w => w[0] == 0x140 && w[1] == 16 && w[2] == outputF) &&
                                SameBoundary(cp, "boundary12fc", "fuelSelectionEntry") &&
                                SameBoundary(cp, "fuelSelectionExit", "fuelLookupEntry") &&
                                SameBoundary(cp, "fuelLookupExit", "fuelConsumerEntry") &&
                                (fuelLookup.Events[0][4] & 0x20) != 0 &&
                                cp.GetProperty("requestP1").GetBoolean() == ((expected.After.Vtec.P1OutputData & 1) != 0) &&
                                cp.GetProperty("requestMirror0127").GetBoolean() == ((expected.After.Vtec.Data0127 & 4) != 0) &&
                                cp.GetProperty("fuelSelector0127").GetBoolean() == ((expected.After.Vtec.Data0127 & 2) != 0),
                                "Fuel origin/cell metadata/Q16/consumer/continuous tail/native lookup mode and selectors");
                        }
                        else
                        {
                            Check(status == expected.Decision.Status && fuelSelection is null && fuelLookup is null &&
                                fuelConsumer is null && originF is null && valueF is null && outputF is null,
                                "Partial event hid ignition or executed fuel after VTEC stop");
                        }
                    }
                    else
                    {
                        Check(decision is null && fuelSelection is null && fuelLookup is null && fuelConsumer is null,
                            "Downstream ran after ignition failure");
                    }
                }
                var disposition = differences.Count != 0 ? "Mismatch" : status switch
                { 0 when conditional => "ConditionalMatch", 0 => "StrictMatch", 1 => "Unresolved",
                    2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                bool? read = null;
                if (scenario.Mutation is { } mutation && ignitionDone)
                {
                    var source = mutation.Kind switch
                    { "vtecThreshold" => decision, "fuelCell" => fuelLookup, _ => ignitionLookup };
                    read = source?.Result.ProgramReads.Contains(mutation.Offset);
                }
                var witness = scenario.TraceCallIndexes.Contains(index) || differences.Count != 0 && !firstErrorWitness ?
                    cp.Clone() : (JsonElement?)null;
                firstErrorWitness |= differences.Count != 0;
                result.Add(new(index, disposition, status, conditional, ignitionDone, status == 0,
                    before.Selector0227, after.Selector0227,
                    status == 0 ? cp.GetProperty("requestP1").GetBoolean() : null,
                    status == 0 ? cp.GetProperty("requestMirror0127").GetBoolean() : null,
                    status == 0 ? cp.GetProperty("fuelSelector0127").GetBoolean() : null,
                    originI, valueI, outputI, originF, valueF, outputF, read, after,
                    stages.AsReadOnly(), differences.AsReadOnly(), witness));
                prior = after; stopped |= status != 0;
            }
            Require(sequence.GetProperty("completedCalls").GetInt32() == result.Count(c => c.Status == 0) &&
                sequence.GetProperty("stopCallIndex").GetInt32() == result.FindIndex(c => c.Status != 0),
                "M2h completed/stop count differs.");
            sequences.Add(new(imageIndex, pattern, sequence.GetProperty("completedCalls").GetInt32(),
                sequence.GetProperty("stopCallIndex").GetInt32(), result.AsReadOnly()));
        }
        return new(1, "shared-axis-vtec-fuel-ignition-chain", original.Hash, mutated?.Hash, profile.Id,
            scenario.Digest, root.GetProperty("runnerVersion").GetString()!, allowed, scenario.Mutation,
            scenario.Mutation is null ? [] : [scenario.Mutation.Offset], sequences.AsReadOnly(),
            Compare(scenario, sequences));
    }

    private static IReadOnlyList<P28SharedComparison> Compare(P28SharedCalibrationScenario scenario,
        IReadOnlyList<P28SharedSequence> sequences)
    {
        if (scenario.Mutation is null) return [];
        var rows = new List<P28SharedComparison>();
        foreach (var pattern in Patterns)
        {
            var a = sequences.Single(s => s.ImageIndex == 0 && s.ScratchPattern == pattern).Checkpoints;
            var b = sequences.Single(s => s.ImageIndex == 1 && s.ScratchPattern == pattern).Checkpoints;
            for (var i = 0; i < a.Count; i++)
            {
                var x = a[i]; var y = b[i];
                if (!x.WholeEventCompleted || !y.WholeEventCompleted || x.Differences.Count != 0 || y.Differences.Count != 0)
                { rows.Add(new(pattern, i, null, null, null, null, null, "NotComparable")); continue; }
                var axesSame = x.StateAfter.Axes == y.StateAfter.Axes;
                var selectorSame = x.SelectorAfter0227 == y.SelectorAfter0227;
                var ignitionSame = x.IgnitionOrigin == y.IgnitionOrigin && x.IgnitionLookup == y.IgnitionLookup && x.Data0248 == y.Data0248;
                var vtecSame = x.StateAfter.Vtec == y.StateAfter.Vtec;
                var fuelSame = x.FuelOrigin == y.FuelOrigin && x.FuelLookup == y.FuelLookup && x.Data0140 == y.Data0140;
                var control = axesSame && selectorSame && (scenario.Mutation.Kind switch
                { "vtecThreshold" => ignitionSame, "fuelCell" => ignitionSame && vtecSame,
                    _ => vtecSame && fuelSame });
                var effect = !control ? "ControlFailure" : y.ChangedByteRead != true ? "ByteNotRead" :
                    ignitionSame && vtecSame && fuelSame ? "ReadNoEffectOrMasked" :
                    "NativeReadAndDownstreamEffect";
                rows.Add(new(pattern, i, y.ChangedByteRead, control, !ignitionSame, !vtecSame, !fuelSame, effect));
            }
        }
        return rows.AsReadOnly();
    }

    private static Stage? ParseStage(JsonElement element, int entry, int budget, IReadOnlyList<string> allowed,
        string? permission, bool traced)
    {
        if (element.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(element, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(element.GetProperty("result"), budget, 0, allowed, permission)!;
        var writes = Matrix(element.GetProperty("writes"), 3, 1024);
        var events = Matrix(element.GetProperty("events"), 8, budget);
        var ssp = element.GetProperty("sspAfter").GetInt32();
        Require(events.Length == result.Steps && result.Trace.Count == (traced ? Math.Min(128, result.Steps) : 0) &&
            ssp is >= 0 and <= 65535, "M2h incomplete stage journal/trace/stack.");
        var pc = entry;
        foreach (var e in events) { Require(e[0] == pc, "M2h native stage PC path discontinuity."); pc = e[1]; }
        Require(result.StopPc == pc, "M2h native stop PC contradicts ordered events.");
        return new(result, writes, events, ssp);
    }

    private static JsonElement? Boundary(JsonElement cp, string field, int pc)
    {
        var value = cp.GetProperty(field);
        return value.ValueKind != JsonValueKind.Null && value.GetProperty("pc").GetInt32() == pc ? value : null;
    }
    private static bool SameBoundary(JsonElement cp, string left, string right) =>
        cp.GetProperty(left).ValueKind != JsonValueKind.Null &&
        cp.GetProperty(left).GetRawText() == cp.GetProperty(right).GetRawText();
    private static int? Number(JsonElement row, string field) => row.GetProperty(field).ValueKind == JsonValueKind.Null ?
        null : row.GetProperty(field).GetInt32();
    private static P28SharedState State(JsonElement row, string field) =>
        row.GetProperty(field).Deserialize<P28SharedState>(P28StatefulScenario.Options)!;
    private static int[][] Matrix(JsonElement element, int width, int maximum)
    {
        Require(element.GetArrayLength() <= maximum, "Unbounded M2h journal.");
        return element.EnumerateArray().Select(row =>
        {
            var values = row.EnumerateArray().Select(x => x.GetInt32()).ToArray();
            Require(values.Length == width && values.All(x => x is >= 0 and <= 65536), "Malformed M2h journal row.");
            return values;
        }).ToArray();
    }
    private static int[][] FilterPersistent(int[][] writes) => writes.Where(w =>
        new[] { 0x131, 0x127, 0x198, 0x1D8, 0x1D9, 0x1DF, 0xF3, 0x22 }.Contains(w[0])).ToArray();
    private static bool Equal<T>(JsonElement actual, T expected) => JsonNode.DeepEquals(
        JsonNode.Parse(actual.GetRawText()), JsonSerializer.SerializeToNode(expected, JsonDefaults.Create(false)));
    private static bool Equal<T>(IReadOnlyList<int[]> actual, IReadOnlyList<T> expected) =>
        JsonNode.DeepEquals(JsonSerializer.SerializeToNode(actual), JsonSerializer.SerializeToNode(expected));
    private static void Require(bool value, string message)
    { if (!value) throw new SliceProcessException(SliceProcessFailure.Protocol, message); }
}
