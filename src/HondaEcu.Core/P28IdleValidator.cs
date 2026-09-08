using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28IdleCheckpoint(int Index, string Disposition, P28IdleCall Inputs, JsonElement Actual, P28IdleModelStep? Expected,
    int? ActualFinalTarget, int? ActualError, bool? CurrentBelowTarget, IReadOnlyList<string> Differences);
public sealed record P28IdleSequenceReport(int ScratchPattern, IReadOnlyList<P28IdleCheckpoint> Checkpoints);
public sealed record P28IdleImageReport(string Image, int ArithmeticChecksum, IReadOnlyList<P28IdleSequenceReport> Sequences);
public sealed record P28IdleDifference(int ScratchPattern, int Index, string Comparison, int? TargetA, int? TargetB, int? ErrorA, int? ErrorB,
    bool? DecisionA, bool? DecisionB, bool? MutatedCellRead, bool? Witness);
public sealed record P28IdleValidationReport(int FormatVersion, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    P28IdleMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28IdleImageReport> Images, IReadOnlyList<P28IdleDifference> Comparisons)
{
    public bool HasFailure => Images.SelectMany(i => i.Sequences).SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch");
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string DownstreamRegulatorAndElectricalOutput => "NotRun; static consumer linkage only beyond 09F4";
    public string OtherTargetContexts => "NotEvaluated; rawD9 < 52 and 021A.0 clear unsupported";
    public string ConditionalPermissions => "None. Existing ADD/SUBB permissions remain unchanged and are not accepted here.";
    public string FirmwareOutput => "None; B remains in memory, without checksum repair, child binding or export authority";
}
public static class P28IdleValidator
{
    public const string Operation = "idleTarget";
    public static object CreateRequest(RomImage image, P28IdleScenario scenario) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        idleTarget = new { formatVersion = 1, scenario.InitialState, scenario.Calls }
    };
    public static async Task<P28IdleValidationReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28IdleScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28IdleInspector.TableGuard(original);
        var images = new List<P28IdleImageReport>(); var changed = new List<int>();
        var b = scenario.Mutation is null ? null : P28IdleInspector.Mutate(original, scenario.Mutation);
        if (b is not null) for (var i = 0; i < original.Size; i++) if (original.Span[i] != b.Span[i]) changed.Add(i);
        foreach (var image in b is null ? new[] { original } : new[] { original, b })
        {
            if (image != original) P28IdleInspector.AdmitMutation(original, image, scenario.Mutation!);
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            images.Add(AnalyzeImage(image, scenario, response, images.Count == 0 ? "A" : "B"));
        }
        var comparisons = new List<P28IdleDifference>();
        if (b is not null) for (var s = 0; s < 3; s++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = images[0].Sequences[s].Checkpoints[i]; var other = images[1].Sequences[s].Checkpoints[i];
                    var comparable = a.Disposition == "StrictMatch" && other.Disposition == "StrictMatch";
                    var field = P28IdleInspector.FieldOffset(scenario.Mutation!.Field);
                    bool? read = comparable ? other.Actual.GetProperty("producer").GetProperty("result").GetProperty("programReads").EnumerateArray().Any(v => v.GetInt32() == field) : null;
                    bool? witness = comparable ? read == true && a.ActualFinalTarget != other.ActualFinalTarget && (a.CurrentBelowTarget != other.CurrentBelowTarget || a.ActualError != other.ActualError) : null;
                    comparisons.Add(new(new[] { 0, 85, 170 }[s], i, comparable ? "Comparable" : "NotComparable", a.ActualFinalTarget, other.ActualFinalTarget, a.ActualError, other.ActualError, a.CurrentBelowTarget, other.CurrentBelowTarget, read, witness));
                }
        return new(1, original.Hash, profile.Id, scenario.Digest, scenario.Mutation, changed.AsReadOnly(), images.AsReadOnly(), comparisons.AsReadOnly());
    }
    internal static P28IdleImageReport AnalyzeImage(RomImage image, P28IdleScenario scenario, SliceProcessResponse response, string id)
    {
        try { return AnalyzeCore(image, scenario, response.Response, id); }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentOutOfRangeException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed idle response.", e); }
    }
    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events);
    private static Stage? ParseStage(JsonElement e, bool consumer)
    {
        if (e.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(e, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(e.GetProperty("result"), 128, 0, [], null); Require(result is not null, "Missing idle stage.");
        var writes = Matrix(e, "writes", 3); var events = Matrix(e, "events", 8);
        Require(writes.Length <= 256 && events.Length <= 128 && result!.Trace.Count == result.Steps && events.Length == result.Steps && result.UsedAssumptions.Count == 0, "Incomplete or unbounded idle journals.");
        bool InCode(int pc) => Code(consumer).Any(r => pc >= r[0] && pc < r[1]);
        var pc = consumer ? 0x9DC : 0x2FD1;
        for (var i = 0; i < events.Length; i++)
        {
            var row = events[i]; var t = result!.Trace[i];
            Require(row[0] == pc && InCode(pc) && t.GetProperty("pc").GetInt32() == pc && t.GetProperty("nextPc").GetInt32() == row[1] && t.GetProperty("accumulator").GetInt32() == row[3] && t.GetProperty("psw").GetInt32() == row[5], "Contradictory idle trace."); pc = row[1];
        }
        Require(result!.StopPc == pc && result.ExecutedInstructionBytes.All(InCode), "Idle escape/extents.");
        Require(result.Status != 0 || result.Error is null && pc == (consumer ? 0x9F4 : 0x30AB) && e.GetProperty("sspAfter").GetInt32() == 0x7FE, "Incorrect successful idle exit/stack.");
        Require(result.ProgramReads.All(a => consumer ? a is >= 0x36 and < 0x38 : a is >= 0x28 and < 0x2A or >= 0x68CB and < 0x68E0), "Foreign idle program data.");
        return new(result, writes, events);
    }
    private static P28IdleState State(JsonElement e) { P28IdleScenario.StateShape(e); return e.Deserialize<P28IdleState>(P28StatefulScenario.Options)!; }
    private static int? Number(JsonElement e) => e.ValueKind == JsonValueKind.Null ? null : e.GetInt32();
    private static readonly int[] Branches = [0x7D8F, 0x2FDE, 0x2FED, 0x5898, 0x58BB, 0x3074, 0x309D];
    private static P28IdleImageReport AnalyzeCore(RomImage image, P28IdleScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "idleSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation);
        Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "Idle entry contract mismatch.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign result rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Unexpected synthetic result.");
        var sequences = root.GetProperty("idleSequences"); Require(sequences.GetArrayLength() == 3, "Idle scratch count."); var reports = new List<P28IdleSequenceReport>();
        for (var s = 0; s < 3; s++)
        {
            var seq = sequences[s]; P28LimiterScenario.Shape(seq, "scratchPattern", "checkpoints"); var pattern = new[] { 0, 85, 170 }[s];
            Require(seq.GetProperty("scratchPattern").GetInt32() == pattern, "Idle scratch order."); var rows = seq.GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "Idle call count.");
            var model = new P28IdleModel(image, scenario.InitialState); var previous = scenario.InitialState; var stopped = false; var checkpoints = new List<P28IdleCheckpoint>();
            for (var i = 0; i < rows.GetArrayLength(); i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "stateBefore", "stateAfterProducer", "stateAfter", "producer", "consumer", "actualTarget", "actualError", "currentBelowTarget");
                Require(row.GetProperty("index").GetInt32() == i, "Idle call order."); var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Unknown idle status.");
                var before = State(row.GetProperty("stateBefore")); var after = State(row.GetProperty("stateAfter"));
                var produced = row.GetProperty("stateAfterProducer").ValueKind == JsonValueKind.Null ? null : State(row.GetProperty("stateAfterProducer"));
                var p = ParseStage(row.GetProperty("producer"), false); var c = ParseStage(row.GetProperty("consumer"), true);
                var target = Number(row.GetProperty("actualTarget")); var error = Number(row.GetProperty("actualError")); var decision = NullableBool(row.GetProperty("currentBelowTarget"));
                var diff = new List<string>(); void Check(bool ok, string why) { if (!ok) diff.Add(why); }
                Check(before == previous, "Actual history discontinuity/reseed"); P28IdleModelStep? expected = null;
                if (stopped) Require(status == 4 && p is null && c is null && produced is null && target is null && error is null && decision is null && before == after, "Execution/output in terminal suffix.");
                else
                {
                    Require(p is not null && produced is not null && status == (c?.Result.Status ?? p!.Result.Status), "Missing/contradictory producer.");
                    Require(p!.Result.Status == 0 ? c is not null && target == produced!.Target : c is null && target is null, "Fabricated target/consumer handoff.");
                    Require(c?.Result.Status == 0 ? error == after.ErrorMagnitude && decision == ((after.Data021a & 16) != 0) : error is null && decision is null, "Fabricated consumer output.");
                    if (status == 0)
                    {
                        expected = model.Step(scenario.Calls[i]); Check(before == expected.Before && produced == expected.AfterProducer && after == expected.After, "Independent state/target history");
                        Check(Equal(p.Writes, expected.ProducerWrites) && Equal(c!.Writes, expected.ConsumerWrites), "Ordered stores (including same-value and stack stores)");
                        Check(Equal(p.Result.ProgramReads, expected.ProducerReads) && Equal(c!.Result.ProgramReads, expected.ConsumerReads), "Ordered program reads/selected source");
                        Check(Equal(p.Events.Where(e => Branches.Contains(e[0])).Select(e => new[] { e[0], e[1] }).ToArray(), expected.ProducerBranches), "Producer branch order/selection");
                        Check(Equal(c!.Events.Where(e => e[0] is 0x9E7 or 0x9EF).Select(e => new[] { e[0], e[1] }).ToArray(), expected.ConsumerBranches), "Consumer branch order/clamp");
                        // Observe the arithmetic intermediates in the native accumulator too,
                        // not only the final target and the bank-register write journal.
                        bool AccumulatorAt(int pc, int beforeValue, int afterValue)
                        {
                            var observations = p.Events.Where(e => e[0] == pc).ToArray();
                            return observations.Length == 1 && observations[0][2] == beforeValue && observations[0][3] == afterValue;
                        }
                        var negative = expected.UpperValue < expected.LowerValue;
                        var distanceValue = Math.Abs(expected.UpperValue - expected.LowerValue);
                        var productLow = (distanceValue * expected.FractionNumerator) & 65535;
                        Check(AccumulatorAt(0x58BA, expected.UpperValue, (expected.UpperValue - expected.LowerValue) & 65535), "Native upper-minus-lower target component");
                        Check(AccumulatorAt(negative ? 0x58C0 : 0x58CA, distanceValue, productLow), "Native target interpolation product");
                        Check(AccumulatorAt(negative ? 0x58C4 : 0x58CE, productLow, expected.TruncatedDelta), "Native target interpolation quotient/truncation");
                        Check(AccumulatorAt(0x309C, 0, expected.FinalTarget), "Native zero correction and final target forwarding");
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
    internal static int[][] Code(bool consumer) => consumer ? [[0x9DC, 0x9F4], [0x59A6, 0x59AD]] : [[0x2FD1, 0x2FE0], [0x2FEC, 0x2FEF], [0x306E, 0x3076], [0x309A, 0x30A0], [0x30A9, 0x30AB], [0x7D8A, 0x7D98], [0x5894, 0x58D3]];
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[]{new{
        id="idleTarget",producerEntry=0x2FD1,producerExit=0x30AB,consumerEntry=0x9DC,consumerExit=0x9F4,
        producerCode=Code(false),consumerCode=Code(true),dataRanges=new[]{new[]{0,8},[0x88,0x90],[0xC4,0xC6],[0xCA,0xCC],[0xD9,0xDA],[0x200,0x210],[0x216,0x217],[0x21A,0x21B],[0x25C,0x25E],[0x27A,0x27C],[0x7FE,0x800]},
        producerProgramData=new[]{new[]{0x28,0x2A},[0x68CB,0x68E0]},consumerProgramData=new[]{new[]{0x36,0x38}},
        psw=0x1101,producerLrb=0x41,consumerLrb=0x40,scb=1,usp=0x180,ssp=0x7FE,budget=128,stop="BeforeInstruction",
        context="rawD9 >= 52; persistent 021A.0 set; caller snapshot 0216.3 clear",
        state="Seed once; native target/correction/error/sign stores; no counter/filter in this selected target path",physicalRpmAvailable=false,assumptions=Array.Empty<string>()
    }});
}
