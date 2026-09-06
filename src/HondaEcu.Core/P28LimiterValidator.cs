using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed record P28LimiterCounts(int RequestedCalls, int CompletedCalls, int StrictMatches, int ConditionalMatches,
    int Unresolved, int Unsupported, int NotRun, int Mismatches, int ExecutionErrors, int DownstreamAvailable);
public sealed record P28LimiterCheckpoint(int Index, string Disposition, JsonElement Actual, P28LimiterModelStep? Expected,
    IReadOnlyList<string> Differences);
public sealed record P28LimiterSequenceReport(int ImageIndex, int ScratchPattern, P28LimiterCounts Counts,
    IReadOnlyList<P28LimiterCheckpoint> Checkpoints);
public sealed record P28LimiterMutationEvidence(string Field, int Offset, int Width, ushort Before, ushort After,
    IReadOnlyList<int> ChangedOffsets, RomHash InMemoryHash, int? FirstExpectedRequestDivergence,
    int? FirstActualRequestDivergence, bool HistoriesAgree);
public sealed record P28LimiterValidationReport(int FormatVersion, P28LimiterInspection Inspection, string ScenarioDigest,
    JsonElement EntryContracts, IReadOnlyList<P28LimiterSequenceReport> Sequences, P28LimiterMutationEvidence? Mutation,
    IReadOnlyList<object> ChecksumArithmetic)
{
    public bool HasFailure => Sequences.Any(s => s.Counts.Mismatches + s.Counts.ExecutionErrors + s.Counts.Unresolved + s.Counts.Unsupported + s.Counts.NotRun > 0)
        || Mutation is { HistoriesAgree: false };
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string UnevaluatedDependencies => "Earlier gates, adaptive threshold production/timers, scheduler and electrical pulses NotRun; no limiter enable switch established within this contract.";
}

/// <summary>Bounded transport, independent model history, actual operands/branches/writes and terminal suffix checks.</summary>
public static class P28LimiterValidator
{
    public const string Operation = "limiterSequence";
    public static object CreateRequest(RomImage baseline, P28LimiterScenario scenario)
    {
        baseline.ValidateExactSize(32768);
        var images = Images(baseline, scenario).Select((r, i) => new { id = i == 0 ? "baseline" : "operandMutation", rom = r.ToArray().Select(b => (int)b).ToArray() }).ToArray();
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images,
            allowAssumptions = Array.Empty<string>(),
            scratchPatterns = new[] { 0, 85, 170 },
            limiterSequence = new { formatVersion = 1, scenario.InitialState, scenario.Calls }
        };
    }
    private static RomImage[] Images(RomImage baseline, P28LimiterScenario scenario) => scenario.Mutation is null ? [baseline] : [baseline, P28LimiterInspector.Mutate(baseline, scenario.Mutation)];

    public static async Task<P28LimiterValidationReport> ExecuteAsync(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28LimiterScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(baseline);
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(baseline, scenario), options, cancellationToken).ConfigureAwait(false);
        return Analyze(baseline, profile, binding, scenario, response);
    }
    public static P28LimiterValidationReport Analyze(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28LimiterScenario scenario, SliceProcessResponse response)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, null);
        P28LimiterInspector.OperandGuard(baseline);
        try { return AnalyzeCore(baseline, profile, binding, scenario, response.Response); }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentOutOfRangeException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed limiter response.", e); }
    }
    private static P28LimiterValidationReport AnalyzeCore(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28LimiterScenario scenario, JsonElement root)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts",
            "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "limiterSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation);
        foreach (var name in new[] { "compactRows", "thresholdRows", "diagnostics" })
            Require(root.GetProperty(name).GetArrayLength() == 0, "Unexpected foreign rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Unexpected synthetic result.");
        Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "Entry contracts differ.");
        var images = Images(baseline, scenario); var rows = root.GetProperty("limiterSequences");
        Require(rows.GetArrayLength() == images.Length * 3, "Sequence count differs.");
        var reports = new List<P28LimiterSequenceReport>();
        for (var si = 0; si < rows.GetArrayLength(); si++)
        {
            var sequence = rows[si]; var imageIndex = si / 3; var pattern = new[] { 0, 85, 170 }[si % 3];
            P28LimiterScenario.Shape(sequence, "imageIndex", "scratchPattern", "checkpoints");
            Require(sequence.GetProperty("imageIndex").GetInt32() == imageIndex && sequence.GetProperty("scratchPattern").GetInt32() == pattern, "Sequence identity/order differs.");
            var checkpoints = sequence.GetProperty("checkpoints"); Require(checkpoints.GetArrayLength() == scenario.Calls.Count, "Missing or extra calls.");
            var model = new P28LimiterModel(images[imageIndex].Span, scenario.InitialState);
            var actualPrevious = scenario.InitialState; var stopped = false; var reportRows = new List<P28LimiterCheckpoint>();
            int complete = 0, matches = 0, unresolved = 0, notRun = 0, mismatches = 0, errors = 0, downstream = 0;
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                var c = checkpoints[i]; P28LimiterScenario.Shape(c, "index", "status", "stateBefore", "stateAfter", "decision", "consumer", "decisionWrites", "consumerWrites", "decisionEvents", "consumerEvents", "overspeedRequest", "inhibitBranch");
                Require(c.GetProperty("index").GetInt32() == i, "Non-dense call indexes.");
                var status = c.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Unknown status.");
                var before = State(c.GetProperty("stateBefore")); var after = State(c.GetProperty("stateAfter"));
                var decision = P28AcquisitionValidator.ParseStage(c.GetProperty("decision"), 96, 0, [], null);
                var consumer = P28AcquisitionValidator.ParseStage(c.GetProperty("consumer"), 96, 0, [], null);
                var dw = Matrix(c, "decisionWrites", 3); var cw = Matrix(c, "consumerWrites", 3);
                var de = Matrix(c, "decisionEvents", 8); var ce = Matrix(c, "consumerEvents", 8);
                var request = NullableBool(c.GetProperty("overspeedRequest")); var inhibit = NullableBool(c.GetProperty("inhibitBranch"));
                var diff = new List<string>(); void Check(bool ok, string reason) { if (!ok) diff.Add(reason); }
                Check(before == actualPrevious, "Actual persistent history discontinuity / reseed");
                P28LimiterModelStep? expected = null;
                if (stopped)
                {
                    Require(status == 4 && decision is null && consumer is null && request is null && inhibit is null && dw.Length + cw.Length + de.Length + ce.Length == 0 && after == before,
                        "Terminal suffix executed or fabricated outputs."); notRun++;
                }
                else
                {
                    Require(status != 4 && decision is not null, "Initial unexplained NotRun.");
                    ValidateTrace(decision!, de, false); ValidateTrace(consumer, ce, true);
                    Require(status == (consumer?.Status ?? decision!.Status), "Stage/row status contradiction.");
                    if (decision!.Status != 0)
                        Require(consumer is null && request is null && inhibit is null && cw.Length + ce.Length == 0, "Downstream ran after decision failure.");
                    else Require(consumer is not null && request is not null, "Missing completed decision output/consumer attempt.");
                    Require((consumer?.Status == 0) == inhibit.HasValue, "Unavailable inhibit must be null.");
                    if (status == 0)
                    {
                        complete++; downstream++;
                        expected = model.Step(scenario.Calls[i]);
                        Check(before == expected.Before, "Independent expected old state"); Check(after == expected.After, "Independent new state/counter/masks");
                        Check(request == expected.OverspeedRequest, "Overspeed request"); Check(inhibit == expected.InhibitBranch, "Independent inhibit branch");
                        Check(Equal(dw, expected.DecisionWrites), "Ordered decision writes"); Check(Equal(cw, expected.ConsumerWrites), "Ordered consumer writes");
                        Check(decision.StopPc == expected.DecisionExit && consumer!.StopPc == expected.ConsumerExit, "Exit PC");
                        var cmp = de.Where(e => e[0] == 0x197D).ToArray();
                        Check(cmp.Length == 1 && cmp[0][6] == expected.ComparisonLeft && cmp[0][7] == expected.ComparisonRight &&
                            ((cmp[0][5] & 0x8000) != 0) == expected.OverspeedRequest && ((cmp[0][5] & 0x4000) != 0) == (expected.ComparisonLeft == expected.Threshold), "Actual comparison operands/CF/ZF");
                        Check(de.Any(e => e[0] == 0x1969 && e[3] == P28LimiterInspector.Word(images[imageIndex].Span, 0x196A)), "Actual cut immediate load");
                        Check(de.Any(e => e[0] == 0x1974) == (expected.Context == "InitialRamSnapshot"), "Actual context selection");
                        Check(de.Any(e => e[0] == 0x197C) == ((before.Data0124 & 32) != 0), "Actual prior-state threshold selection");
                        Check(de.Any(e => e[0] == 0x1980 && e[1] == (expected.OverspeedRequest ? 0x19AC : 0x1982)), "Actual limiter branch");
                        Check(ce.Any(e => e[0] == 0x558B) == !expected.InhibitBranch && ce.Length > 0 && (ce[^1][3] & 255) == expected.ConsumerAccumulator, "Actual mask consumer execution/accumulator");
                        Check(inhibit == ce.Any(e => (e[0] == 0x5585 || e[0] == 0x5588) && e[1] == 0x5592), "Inhibit observation disagrees with trace");
                    }
                    else if (status == 1) unresolved++; else errors++;
                    stopped = status != 0;
                }
                if (diff.Count > 0) mismatches++; else if (status == 0) matches++;
                reportRows.Add(new(i, status switch { 0 => diff.Count == 0 ? "StrictMatch" : "Mismatch", 1 => "Unresolved", 4 => "NotRun", _ => "ExecutionError" }, c.Clone(), expected, diff.AsReadOnly()));
                actualPrevious = after;
            }
            reports.Add(new(imageIndex, pattern, new(scenario.Calls.Count, complete, matches, 0, unresolved, 0, notRun, mismatches, errors, downstream), reportRows.AsReadOnly()));
        }
        P28LimiterMutationEvidence? mutation = null;
        if (scenario.Mutation is { } m)
        {
            var offset = P28LimiterInspector.FieldOffset(m.Field);
            int? First(bool actual, int pattern)
            {
                var a = reports[pattern].Checkpoints; var b = reports[pattern + 3].Checkpoints;
                for (var i = 0; i < a.Count; i++)
                {
                    bool? av = actual ? NullableBool(a[i].Actual.GetProperty("overspeedRequest")) : a[i].Expected?.OverspeedRequest;
                    bool? bv = actual ? NullableBool(b[i].Actual.GetProperty("overspeedRequest")) : b[i].Expected?.OverspeedRequest;
                    if (av.HasValue && bv.HasValue && av != bv) return i;
                }
                return null;
            }
            mutation = new(m.Field, offset, 2, P28LimiterInspector.Word(baseline.Span, offset), m.Value,
                Enumerable.Range(0, baseline.Size).Where(i => baseline.Span[i] != images[1].Span[i]).ToArray(), images[1].Hash,
                First(false, 0), First(true, 0), Enumerable.Range(0, 3).All(p => First(false, p) == First(true, p)) && reports.All(r => r.Counts.StrictMatches == scenario.Calls.Count));
        }
        var sums = images.Select((im, i) => { var sum = P28NativeChecksumArithmetic.Calculate(im); return (object)new { imageIndex = i, sum.ComputedResult, sum.ResidueMatches, scope = "Independent arithmetic only; no compensation/bypass/export" }; }).ToArray();
        return new(1, P28LimiterInspector.Inspect(baseline, profile, binding, true), scenario.Digest, root.GetProperty("entryContracts").Clone(), reports.AsReadOnly(), mutation, sums);
    }
    private static P28LimiterState State(JsonElement e) { P28LimiterScenario.StateShape(e); return e.Deserialize<P28LimiterState>(P28StatefulScenario.Options)!; }
    private static bool? NullableBool(JsonElement e) => e.ValueKind == JsonValueKind.Null ? null : e.GetBoolean();
    private static int[][] Matrix(JsonElement c, string name, int width)
    {
        var a = c.GetProperty(name); Require(a.GetArrayLength() <= 96, "Journal exceeds budget.");
        return a.EnumerateArray().Select(row => { Require(row.GetArrayLength() == width, "Journal width."); var v = row.EnumerateArray().Select(x => x.GetInt32()).ToArray(); Require(v.All(x => x is >= 0 and <= 65536), "Journal value."); return v; }).ToArray();
    }
    private static void ValidateTrace(P28AcquisitionStageResult? stage, int[][] events, bool consumer)
    {
        if (stage is null) { Require(events.Length == 0, "Events without execution."); return; }
        Require(stage.UsedAssumptions.Count == 0 && stage.ProgramReads.Count == 0 && stage.Trace.Count == stage.Steps && events.Length == stage.Steps, "Unexpected permissions/reads/incomplete trace.");
        var pc = consumer ? 0x5585 : 0x1966;
        for (var i = 0; i < events.Length; i++)
        {
            var e = events[i]; var t = stage.Trace[i];
            Require(e[0] == pc && InCode(pc, consumer), "Trace outside admitted code/continuity.");
            Require(t.GetProperty("pc").GetInt32() == pc && t.GetProperty("nextPc").GetInt32() == e[1] && t.GetProperty("accumulator").GetInt32() == e[3] && t.GetProperty("psw").GetInt32() == e[5], "Event/trace contradiction.");
            pc = e[1];
        }
        Require(stage.StopPc == pc && stage.ExecutedInstructionBytes.All(x => InCode(x, consumer)), "Invalid stop/extents.");
        Require(stage.Status != 0 || stage.Error is null, "Completed stage with error.");
    }
    private static bool InCode(int pc, bool consumer) => consumer ? pc is >= 0x5585 and < 0x5596 : pc is >= 0x1966 and < 0x1985 or >= 0x19AC and < 0x19B0 or >= 0x19C2 and < 0x19CB or >= 0x1A1E and < 0x1A38;
    private static bool Equal<T, U>(T a, U b) => JsonNode.DeepEquals(JsonSerializer.SerializeToNode(a, JsonDefaults.Create(false)), JsonSerializer.SerializeToNode(b, JsonDefaults.Create(false)));
    private static void Require(bool condition, string message) { if (!condition) throw new SliceProcessException(SliceProcessFailure.Protocol, message); }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id="isolatedLimiter",decisionEntry=0x1966,decisionExit=0x1A38,consumerEntry=0x5585,consumerExit=0x5596,stop="BeforeInstruction",
        precondition="Earlier decision gates have selected 1966; 0121.7=1; PSWL.4/5=0",
        ramThresholds="Initial software snapshot only; adaptive 487B..48F5 NotRun",p4="Frozen bit0 software observation; no pins",p2="Not accessed",
        state="Initialized once; no per-call internal stores",budget=96,physicalRpmAvailable=false,
        decisionCodeRanges=new[]{new[]{0x1966,0x1985},new[]{0x19AC,0x19B0},new[]{0x19C2,0x19CB},new[]{0x1A1E,0x1A38}},consumerCodeRanges=new[]{new[]{0x5585,0x5596}},
        dataRanges=new[]{new[]{0,8},new[]{0x2C,0x2D},new[]{0x88,0x98},new[]{0xC4,0xC6},new[]{0x11B,0x11C},new[]{0x121,0x122},new[]{0x124,0x125},new[]{0x12A,0x12C},new[]{0x18F,0x190},new[]{0x1A4,0x1A8},new[]{0x1D7,0x1D8}},
        decisionPsw=0x0101,consumerPsw=0x0102,decisionLrb=0x20,consumerLrb=0x21,scb=1,usp=0x280,
        stack="No stack instructions admitted on established path; technical SSP unused",
        callerActions=new[]{"PC/PSW/LRB/USP entry reset","00C4 word","011B.7 snapshot","P4.0 frozen observation","consumer accumulator mask high nibble F"},
        programDataReads=Array.Empty<int>(),assumptions=Array.Empty<string>(),interrupts="NotInjected",timeAdvancement="None" } });
}
