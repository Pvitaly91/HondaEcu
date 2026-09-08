using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28IdleContextsCheckpoint(int Index, string Disposition, P28IdleContextsCall Inputs, JsonElement Actual, P28IdleContextsModelStep? Expected,
    int? ActualFinalTarget, int? ActualError, bool? CurrentBelowTarget, IReadOnlyList<string> Differences);
public sealed record P28IdleContextsSequenceReport(int ScratchPattern, IReadOnlyList<P28IdleContextsCheckpoint> Checkpoints);
public sealed record P28IdleContextsImageReport(string Image, int ArithmeticChecksum, IReadOnlyList<P28IdleContextsSequenceReport> Sequences);
public sealed record P28IdleContextsDifference(int ScratchPattern, int Index, string Comparison, int? TargetA, int? TargetB, int? ErrorA, int? ErrorB,
    bool? DecisionA, bool? DecisionB, bool? MutatedCellRead, bool? Witness, string Effect);
public sealed record P28IdleContextsValidationReport(int FormatVersion, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    P28IdleMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28IdleContextsImageReport> Images, IReadOnlyList<P28IdleContextsDifference> Comparisons)
{
    public object Summary => new
    {
        CompleteCalls = Images.SelectMany(i => i.Sequences).SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        Dispositions = Images.SelectMany(i => i.Sequences).SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        Sources = Images.SelectMany(i => i.Sequences).SelectMany(s => s.Checkpoints).Where(c => c.Disposition == "StrictMatch")
            .GroupBy(c => c.Expected!.FinalSource).Select(g => new { Source = g.Key, Count = g.Count(), RawMin = g.Min(c => c.Inputs.RawD9), RawMax = g.Max(c => c.Inputs.RawD9) }).ToArray(),
        Branches = Images.SelectMany(i => i.Sequences).SelectMany(s => s.Checkpoints).Where(c => c.Disposition == "StrictMatch")
            .SelectMany(c => c.Expected!.ProducerBranches).Select(b => $"{b[0]:X4}->{b[1]:X4}").Distinct().Order().ToArray(),
        AbWitnesses = Comparisons.Count(c => c.Witness == true),
        AbReadButSameTarget = Comparisons.Count(c => c.Comparison == "Comparable" && c.MutatedCellRead == true && c.TargetA == c.TargetB),
        AbUnread = Comparisons.Count(c => c.Comparison == "Comparable" && c.MutatedCellRead == false),
        AbEffects = Comparisons.GroupBy(c => c.Effect).ToDictionary(g => g.Key, g => g.Count())
    };
    public bool HasFailure => Images.SelectMany(i => i.Sequences).SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch");
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string DownstreamRegulatorAndElectricalOutput => "NotRun; static consumer linkage only beyond 09F4";
    public string OtherTargetContexts => "Explicit software snapshots only; physical reachability unknown. No counter service or native selector writer is executed.";
    public string ConditionalPermissions => "None. Existing ADD/SUBB permissions remain unchanged and are not accepted here.";
    public string FirmwareOutput => "None; B remains in memory, without checksum repair, child binding or export authority";
}
public static class P28IdleContextsValidator
{
    public const string Operation = "idleContexts";
    public static object CreateRequest(RomImage image, P28IdleContextsScenario scenario) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        idleContexts = new { formatVersion = 1, scenario.InitialState, scenario.Calls }
    };
    public static async Task<P28IdleContextsValidationReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28IdleContextsScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28IdleContextsInspector.TableGuard(original);
        var images = new List<P28IdleContextsImageReport>(); var changed = new List<int>();
        var b = scenario.Mutation is null ? null : P28IdleInspector.Mutate(original, scenario.Mutation);
        if (b is not null) for (var i = 0; i < original.Size; i++) if (original.Span[i] != b.Span[i]) changed.Add(i);
        foreach (var image in b is null ? new[] { original } : new[] { original, b })
        {
            if (image != original) P28IdleInspector.AdmitMutation(original, image, scenario.Mutation!);
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            images.Add(AnalyzeImage(image, scenario, response, images.Count == 0 ? "A" : "B"));
        }
        var comparisons = new List<P28IdleContextsDifference>();
        if (b is not null) for (var s = 0; s < 3; s++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = images[0].Sequences[s].Checkpoints[i]; var other = images[1].Sequences[s].Checkpoints[i];
                    var comparable = a.Disposition == "StrictMatch" && other.Disposition == "StrictMatch";
                    var field = P28IdleInspector.FieldOffset(scenario.Mutation!.Field);
                    bool? read = comparable ? other.Actual.GetProperty("producer").GetProperty("result").GetProperty("programReads").EnumerateArray().Any(v => v.GetInt32() == field) : null;
                    bool? witness = comparable ? read == true && a.ActualFinalTarget != other.ActualFinalTarget && (a.CurrentBelowTarget != other.CurrentBelowTarget || a.ActualError != other.ActualError) : null;
                    var effect = !comparable ? "NotComparable" : ClassifyEffect(a.Expected!, other.Expected!, read == true, witness == true);
                    comparisons.Add(new(new[] { 0, 85, 170 }[s], i, comparable ? "Comparable" : "NotComparable", a.ActualFinalTarget, other.ActualFinalTarget, a.ActualError, other.ActualError, a.CurrentBelowTarget, other.CurrentBelowTarget, read, witness, effect));
                }
        return new(1, original.Hash, profile.Id, scenario.Digest, scenario.Mutation, changed.AsReadOnly(), images.AsReadOnly(), comparisons.AsReadOnly());
    }
    internal static string ClassifyEffect(P28IdleContextsModelStep a, P28IdleContextsModelStep b, bool read, bool witness)
    {
        var lookup = b.Lookups.FirstOrDefault(l => l.Table == 0x68CB);
        var zeroWeight = lookup is not null && (lookup.UpperCell == 2 && lookup.Distance == 0 || lookup.LowerCell == 2 && lookup.Distance == lookup.Denominator);
        return !read ? (lookup is not null ? "CellNotRead" : "BaseLookupNotExecuted") :
            a.FinalTarget != b.FinalTarget ? (witness ? "TargetAndConsumerChange" : "TargetChangeConsumerClamp") :
            b.FinalSource == "table-68e0" && a.BaseResult != b.BaseResult ? "ReadThenLateSourceReplacement" :
            zeroWeight ? "CellReadZeroWeight" : "IntegerTruncation";
    }
    internal static P28IdleContextsImageReport AnalyzeImage(RomImage image, P28IdleContextsScenario scenario, SliceProcessResponse response, string id)
    {
        try { return AnalyzeCore(image, scenario, response.Response, id); }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentOutOfRangeException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed idle response.", e); }
    }
    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events);
    private static int[][] Matrix(JsonElement e, string name, int width)
    {
        var array = e.GetProperty(name); Require(array.GetArrayLength() <= (name == "writes" ? 1024 : 256), "Contexts journal bound.");
        return array.EnumerateArray().Select(row =>
        {
            Require(row.GetArrayLength() == width, "Contexts journal width.");
            var values = row.EnumerateArray().Select(n => n.GetInt32()).ToArray(); Require(values.All(n => n is >= 0 and <= 65536), "Contexts journal value."); return values;
        }).ToArray();
    }
    private static Stage? ParseStage(JsonElement e, bool consumer)
    {
        if (e.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(e, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(e.GetProperty("result"), 256, 0, [], null); Require(result is not null, "Missing idle stage.");
        var writes = Matrix(e, "writes", 3); var events = Matrix(e, "events", 8);
        Require(writes.Length <= 1024 && events.Length <= 256 && result!.Trace.Count == Math.Min(128, result.Steps) && events.Length == result.Steps && result.UsedAssumptions.Count == 0, "Incomplete or unbounded idle journals.");
        bool InCode(int pc) => Code(consumer).Any(r => pc >= r[0] && pc < r[1]);
        var pc = consumer ? 0x9DC : 0x2FD1;
        for (var i = 0; i < events.Length; i++)
        {
            var row = events[i];
            Require(row.Length == 8 && row.All(n => n is >= 0 and <= 65536), "Invalid contexts event.");
            Require(row[0] == pc && InCode(pc), "Discontinuous contexts events.");
            if (i < result!.Trace.Count)
            {
                var t = result.Trace[i];
                Require(row[0] == pc && InCode(pc) && t.GetProperty("pc").GetInt32() == pc && t.GetProperty("nextPc").GetInt32() == row[1] && t.GetProperty("accumulator").GetInt32() == row[3] && t.GetProperty("psw").GetInt32() == row[5], "Contradictory idle trace.");
            }
            pc = row[1];
        }
        Require(result!.StopPc == pc && result.ExecutedInstructionBytes.All(InCode), "Idle escape/extents.");
        Require(result.Status != 0 || result.Error is null && pc == (consumer ? 0x9F4 : 0x30AB) && e.GetProperty("sspAfter").GetInt32() == 0x7FE, "Incorrect successful idle exit/stack.");
        Require(result.ProgramReads.All(a => consumer ? a is >= 0x36 and < 0x38 : a is >= 0x28 and < 0x2A or >= 0x68CB and < 0x68F5), "Foreign idle program data.");
        return new(result, writes, events);
    }
    private static P28IdleContextsState State(JsonElement e) { P28IdleContextsScenario.StateShape(e); return e.Deserialize<P28IdleContextsState>(P28StatefulScenario.Options)!; }
    private static int? Number(JsonElement e) => e.ValueKind == JsonValueKind.Null ? null : e.GetInt32();
    private static readonly int[] Branches = [0x7D8F, 0x7D98, 0x2FDE, 0x2FED, 0x2FF1, 0x2FF9, 0x3000, 0x3008, 0x300B, 0x3016, 0x3023, 0x302A, 0x302D, 0x3031, 0x3039, 0x303B, 0x3044, 0x3049, 0x304B, 0x3052, 0x305B, 0x3062, 0x306B, 0x3082, 0x308B, 0x3091, 0x5898, 0x58BB, 0x3074, 0x309D];
    private static P28IdleContextsImageReport AnalyzeCore(RomImage image, P28IdleContextsScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "idleContextSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation);
        Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "Idle entry contract mismatch.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign result rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Unexpected synthetic result.");
        var sequences = root.GetProperty("idleContextSequences"); Require(sequences.GetArrayLength() == 3, "Idle scratch count."); var reports = new List<P28IdleContextsSequenceReport>();
        for (var s = 0; s < 3; s++)
        {
            var seq = sequences[s]; P28LimiterScenario.Shape(seq, "scratchPattern", "checkpoints"); var pattern = new[] { 0, 85, 170 }[s];
            Require(seq.GetProperty("scratchPattern").GetInt32() == pattern, "Idle scratch order."); var rows = seq.GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "Idle call count.");
            var model = new P28IdleContextsModel(image, scenario.InitialState); var previous = scenario.InitialState; var stopped = false; var checkpoints = new List<P28IdleContextsCheckpoint>();
            for (var i = 0; i < rows.GetArrayLength(); i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "stateBefore", "stateAfterInputs", "stateAfterProducer", "stateAfter", "producer", "consumer", "actualTarget", "actualError", "currentBelowTarget");
                Require(row.GetProperty("index").GetInt32() == i, "Idle call order."); var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Unknown idle status.");
                var before = State(row.GetProperty("stateBefore")); var after = State(row.GetProperty("stateAfter"));
                var produced = row.GetProperty("stateAfterProducer").ValueKind == JsonValueKind.Null ? null : State(row.GetProperty("stateAfterProducer"));
                var inputs = row.GetProperty("stateAfterInputs").ValueKind == JsonValueKind.Null ? null : State(row.GetProperty("stateAfterInputs"));
                var p = ParseStage(row.GetProperty("producer"), false); var c = ParseStage(row.GetProperty("consumer"), true);
                var target = Number(row.GetProperty("actualTarget")); var error = Number(row.GetProperty("actualError")); var decision = NullableBool(row.GetProperty("currentBelowTarget"));
                var diff = new List<string>(); void Check(bool ok, string why) { if (!ok) diff.Add(why); }
                Check(before == previous, "Actual history discontinuity/reseed"); P28IdleContextsModelStep? expected = null;
                if (stopped) Require(status == 4 && p is null && c is null && produced is null && inputs is null && target is null && error is null && decision is null && before == after, "Execution/output in terminal suffix.");
                else
                {
                    Check(inputs == P28IdleContextsScenario.ApplySelectors(before, scenario.Calls[i].Selectors), "Masked inputs changed native state");
                    Require(inputs is not null && p is not null && produced is not null && status == (c?.Result.Status ?? p!.Result.Status), "Missing/contradictory producer.");
                    Require(p!.Result.Status == 0 ? c is not null && target == produced!.Target : c is null && target is null, "Fabricated target/consumer handoff.");
                    Require(c?.Result.Status == 0 ? error == after.ErrorMagnitude && decision == ((after.Data021a & 16) != 0) : error is null && decision is null, "Fabricated consumer output.");
                    if (status == 0)
                    {
                        expected = model.Step(scenario.Calls[i]); Check(before == expected.Before && inputs == expected.AfterInputs && produced == expected.AfterProducer && after == expected.After, "Independent state/target history");
                        Check(Equal(p.Writes, expected.ProducerWrites) && Equal(c!.Writes, expected.ConsumerWrites), "Ordered stores (including same-value and stack stores)");
                        Check(Equal(p.Result.ProgramReads, expected.ProducerReads) && Equal(c!.Result.ProgramReads, expected.ConsumerReads), "Ordered program reads/selected source");
                        Check(Equal(p.Events.Where(e => Branches.Contains(e[0])).Select(e => new[] { e[0], e[1] }).ToArray(), expected.ProducerBranches), "Producer branch order/selection");
                        Check(Equal(c!.Events.Where(e => e[0] is 0x9E7 or 0x9EF).Select(e => new[] { e[0], e[1] }).ToArray(), expected.ConsumerBranches), "Consumer branch order/clamp");
                        var relevant = expected.ProducerAccumulators.Select(a => a[0]).ToHashSet();
                        var actualAcc = p.Events.Where(e => relevant.Contains(e[0])).ToArray();
                        Check(actualAcc.Length == expected.ProducerAccumulators.Count && actualAcc.Zip(expected.ProducerAccumulators)
                            .All(pair => pair.First[0] == pair.Second[0] && (pair.Second[1] < 0 || pair.First[2] == pair.Second[1]) && pair.First[3] == pair.Second[2]), "Native lookup/override/component arithmetic");
                        Check(Equal(p.Events.Where(e => e[6] != 65536).Select(e => new[] { e[0], e[6], e[7] }).ToArray(), expected.ProducerComparisons), "Actual compared source/context operands");
                        var sub = c.Events.Where(e => e[0] == 0x9DE).ToArray();
                        Check(sub.Length == 1 && sub[0][2] == scenario.Calls[i].RawPeriod && sub[0][3] == expected.DifferenceModuloWord && ((sub[0][5] & 0x8000) != 0) == expected.CurrentBelowTarget && ((sub[0][5] & 0x4000) != 0) == (expected.AbsoluteError == 0), "Native current-minus-actual-target operands/CF/ZF");
                        var store = p.Events.Where(e => e[0] == 0x30A9).ToArray(); Check(store.Length == 1 && (store[0][4] & 0x1000) != 0 && store[0][3] == expected.FinalTarget, "DD=1 target word store, not byte duty");
                        Check(target == expected.FinalTarget && error == expected.ClampedError && decision == expected.CurrentBelowTarget, "Actual target/error/sign");
                    }
                }
                var disposition = diff.Count > 0 ? "Mismatch" : status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                checkpoints.Add(new(i, disposition, scenario.Calls[i], row.Clone(), expected, target, error, decision, diff.AsReadOnly())); previous = after; stopped |= status != 0;
            }
            reports.Add(new(pattern, checkpoints.AsReadOnly()));
        }
        return new(id, P28NativeChecksumArithmetic.Calculate(image).ComputedResult, reports.AsReadOnly());
    }
    internal static int[][] Code(bool consumer) => consumer ? P28IdleValidator.Code(true) : [[0x2FD1, 0x30AB], [0x7D8A, 0x7DA5], [0x5894, 0x58D3]];
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[]{new{
        id="idleContexts",producerEntry=0x2FD1,producerExit=0x30AB,consumerEntry=0x9DC,consumerExit=0x9F4,
        producerCode=Code(false),consumerCode=Code(true),dataRanges=new[]{new[]{0,8},[0x88,0x90],[0xC4,0xC6],[0xCA,0xCC],[0xD9,0xDA],[0x200,0x210],
            [0x211,0x212],[0x216,0x218],[0x21A,0x21B],[0x225,0x226],[0x22A,0x22B],[0x25C,0x25E],[0x274,0x276],[0x27A,0x27E],[0x2E5,0x2E6],[0x2E8,0x2EA],[0x7FE,0x800]},
        producerProgramData=new[]{new[]{0x28,0x2A},[0x68CB,0x68F5]},consumerProgramData=new[]{new[]{0x36,0x38}},
        psw=0x1101,producerLrb=0x41,consumerLrb=0x40,scb=1,usp=0x180,ssp=0x7FE,budget=256,tracePrefix=128,stop="BeforeInstruction",
        selectorMasks=new[]{new[]{0x21A,1},[0x211,32],[0x216,8],[0x217,64],[0x225,2],[0x22A,48]},
        state="Seed once; masked scripted upstream selector updates only; no counter service, scheduler or target/component reseed",physicalRpmAvailable=false,assumptions=Array.Empty<string>()
    }});
}
