using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28AdaptiveCheckpoint(int Index, string Disposition, P28AdaptiveCall Inputs, JsonElement Actual,
    int? ActualBank, string? ActualProducerPath, IReadOnlyList<int[]> ActualTableReads, string? ThresholdSource, int? SelectedThreshold,
    bool? OverspeedRequest, bool? IndependentInhibit, bool? MaskUpdateSkipped, P28AdaptiveModelStep? Expected, IReadOnlyList<string> Differences);
public sealed record P28AdaptiveSequenceReport(int ScratchPattern, P28LimiterCounts Counts, IReadOnlyList<P28AdaptiveCheckpoint> Checkpoints);
public sealed record P28AdaptiveValidationReport(int FormatVersion, RomHash BaselineHash, string ProfileId, string ProfileDigest, string ScenarioDigest, JsonElement EntryContracts, IReadOnlyList<P28AdaptiveSequenceReport> Sequences)
{
    public bool HasFailure => Sequences.Any(s => s.Counts.StrictMatches != s.Counts.RequestedCalls);
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string UnevaluatedDependencies => "Raw software snapshots; no acquisition, physical tick period, surrounding counter scheduler, earlier limiter gates, P2 write or electrical pulses. No conditional permissions.";
}

public static class P28AdaptiveValidator
{
    public const string Operation = "adaptiveLimiter";
    public static object CreateRequest(RomImage baseline, P28AdaptiveScenario scenario) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = baseline.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        adaptiveLimiter = new { formatVersion = 1, scenario.InitialState, scenario.Calls }
    };
    public static async Task<P28AdaptiveValidationReport> ExecuteAsync(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28AdaptiveScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, confirmed, null);
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(baseline, scenario), options, cancellationToken).ConfigureAwait(false);
        return Analyze(baseline, profile, binding, scenario, response);
    }
    public static P28AdaptiveValidationReport Analyze(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, P28AdaptiveScenario scenario, SliceProcessResponse response)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, null);
        try { return AnalyzeCore(baseline, profile, scenario, response.Response); }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentOutOfRangeException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed adaptive response.", e); }
    }
    private sealed record Stage(P28AcquisitionStageResult Result, int[][] Writes, int[][] Events, int Ssp);
    internal static P28AdaptiveValidationReport AnalyzeExportImage(P28FixedLimiterPreview preview, RomImage image,
        P28AdaptiveScenario scenario, SliceProcessResponse response)
    {
        if (!new[] { preview.Original.Hash, preview.Intermediate.Hash, preview.Output.Hash }.Contains(image.Hash))
            throw new InvalidDataException("Foreign adaptive export-control image.");
        return AnalyzeCore(image, preview.Profile, scenario, response.Response);
    }
    private static Stage? ParseStage(JsonElement e, bool tick)
    {
        if (e.ValueKind == JsonValueKind.Null) return null;
        P28LimiterScenario.Shape(e, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(e.GetProperty("result"), tick ? 3 : 160, 0, [], null);
        Require(result is not null, "Stage result missing.");
        int[][] Rows(string name, int width)
        {
            var values = e.GetProperty(name); Require(values.GetArrayLength() <= 160, "Unbounded adaptive journal.");
            return values.EnumerateArray().Select(row => { var v = row.EnumerateArray().Select(x => x.GetInt32()).ToArray(); Require(v.Length == width && v.All(x => x is >= 0 and <= 65536), "Invalid journal shape/value."); return v; }).ToArray();
        }
        var writes = Rows("writes", 3); var events = Rows("events", 8); var ssp = e.GetProperty("sspAfter").GetInt32();
        Require(ssp is >= 0 and <= 65535, "Invalid SSP.");
        Require(result!.UsedAssumptions.Count == 0 && result.Trace.Count == result.Steps && events.Length == result.Steps, "Unexpected assumptions/incomplete trace.");
        var pc = tick ? 0x5BD0 : 0x487B;
        bool InCode(int a) => tick ? a is >= 0x5BD0 and < 0x5BD9 : a is >= 0x487B and < 0x48F5 or >= 0x5AB8 and < 0x5AE6;
        for (var i = 0; i < events.Length; i++)
        {
            var row = events[i]; var t = result.Trace[i];
            Require(row[0] == pc && InCode(pc) && t.GetProperty("pc").GetInt32() == pc && t.GetProperty("nextPc").GetInt32() == row[1] && t.GetProperty("accumulator").GetInt32() == row[3] && t.GetProperty("psw").GetInt32() == row[5], "Trace continuity/observation contradiction.");
            pc = row[1];
        }
        Require(result.StopPc == pc && result.ExecutedInstructionBytes.All(InCode), "Invalid adaptive stop/extents.");
        Require(result.Status != 0 || result.Error is null && pc == (tick ? 0x5BD9 : 0x48F5) && ssp == 0x7FE, "Incorrect successful exit/stack.");
        Require(tick ? result.ProgramReads.Count == 0 : result.ProgramReads.All(a => a is >= 0x6493 and < 0x64AB), "Unexpected program reads.");
        return new(result, writes, events, ssp);
    }
    private static P28AdaptiveState State(JsonElement e)
    { P28AdaptiveScenario.StateShape(e); return e.Deserialize<P28AdaptiveState>(P28StatefulScenario.Options)!; }
    private static readonly int[] ProducerBranches = [0x4882, 0x4894, 0x489D, 0x48A2, 0x48A8, 0x48AF, 0x48B1, 0x48B6, 0x5ABB, 0x5ABE, 0x5AC5, 0x5AD3, 0x5AE2];
    private static int[][] TableReads(Stage? p)
    {
        if (p is null) return [];
        var loads = p.Result.Trace.Select((t, i) => (t, i)).Where(x => x.t.GetProperty("instruction").GetString()!.StartsWith("LC A,", StringComparison.Ordinal)).ToArray();
        // LC logs little-endian byte addresses in execution order, including repeats.
        Require(p.Result.ProgramReads.Count == loads.Length * 2, "LC/read cardinality differs.");
        return loads.Select((x, i) => { var a = p.Result.ProgramReads[2 * i]; Require(p.Result.ProgramReads[2 * i + 1] == a + 1, "Noncontiguous table word."); return new[] { p.Events[x.i][0], a, p.Events[x.i][3] }; }).ToArray();
    }
    private static P28AdaptiveValidationReport AnalyzeCore(RomImage baseline, RomProfile profile, P28AdaptiveScenario scenario, JsonElement root)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "adaptiveSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation);
        foreach (var name in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(name).GetArrayLength() == 0, "Foreign rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null && Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "Unexpected synthetic result/contracts.");
        var sequences = root.GetProperty("adaptiveSequences"); Require(sequences.GetArrayLength() == 3, "Sequence cardinality.");
        var reports = new List<P28AdaptiveSequenceReport>();
        for (var si = 0; si < 3; si++)
        {
            var sequence = sequences[si]; P28LimiterScenario.Shape(sequence, "scratchPattern", "checkpoints");
            var pattern = new[] { 0, 85, 170 }[si]; Require(sequence.GetProperty("scratchPattern").GetInt32() == pattern, "Scratch identity/order.");
            var checkpoints = sequence.GetProperty("checkpoints"); Require(checkpoints.GetArrayLength() == scenario.Calls.Count, "Checkpoint count.");
            var model = new P28AdaptiveModel(baseline.Span, scenario.InitialState); var previous = scenario.InitialState; var stopped = false;
            int complete = 0, matches = 0, unresolved = 0, notRun = 0, mismatches = 0, errors = 0;
            var rows = new List<P28AdaptiveCheckpoint>();
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                var c = checkpoints[i]; P28LimiterScenario.Shape(c, "index", "status", "stateBefore", "stateAfterProducer", "stateAfter", "ticks", "producer", "limiter");
                Require(c.GetProperty("index").GetInt32() == i, "Call order."); var status = c.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Unknown status.");
                var before = State(c.GetProperty("stateBefore")); var after = State(c.GetProperty("stateAfter"));
                var produced = c.GetProperty("stateAfterProducer").ValueKind == JsonValueKind.Null ? null : State(c.GetProperty("stateAfterProducer"));
                var p = ParseStage(c.GetProperty("producer"), false); var actualTables = TableReads(p);
                var ticks = c.GetProperty("ticks"); var input = scenario.Calls[i]; var scheduled = Enumerable.Repeat(0x1D5, input.TimerTicks).Concat(Enumerable.Repeat(0x1CE, input.CounterTicks)).ToArray();
                Require(ticks.GetArrayLength() <= scheduled.Length, "Extra native ticks."); var tickStages = new List<Stage>();
                foreach (var t in ticks.EnumerateArray())
                {
                    P28LimiterScenario.Shape(t, "address", "stage"); Require(t.GetProperty("address").GetInt32() == scheduled[tickStages.Count], "Native tick target/order.");
                    tickStages.Add(ParseStage(t.GetProperty("stage"), true) ?? throw new InvalidDataException("Missing tick stage."));
                }
                var l = c.GetProperty("limiter"); var hasLimiter = l.ValueKind != JsonValueKind.Null;
                var diff = new List<string>(); void Check(bool ok, string why) { if (!ok) diff.Add(why); }
                Check(before == previous, "Actual history discontinuity/reseed"); P28AdaptiveModelStep? expected = null;
                if (stopped)
                {
                    Require(status == 4 && p is null && !hasLimiter && produced is null && ticks.GetArrayLength() == 0 && before == after, "Terminal suffix executed/fabricated state."); notRun++;
                }
                else
                {
                    Require(status != 4, "Unexplained initial NotRun."); var tickFailure = tickStages.FindIndex(t => t.Result.Status != 0);
                    if (tickFailure >= 0) Require(tickFailure == tickStages.Count - 1 && p is null && produced is null && !hasLimiter && status == tickStages[^1].Result.Status, "Execution after tick failure.");
                    else
                    {
                        Require(tickStages.Count == scheduled.Length && p is not null && produced is not null, "Missing producer/ticks.");
                        Require((p!.Result.Status == 0) == hasLimiter, "Incorrect producer/limiter handoff.");
                        Require(status == (hasLimiter ? l.GetProperty("status").GetInt32() : p.Result.Status), "Contradictory row status.");
                    }
                    if (hasLimiter)
                    {
                        Require(l.GetProperty("index").GetInt32() == i, "Limiter call identity differs.");
                        ValidateLimiter(l, produced!.Limiter, after.Limiter, null, Check);
                    }
                    if (status == 0)
                    {
                        complete++; expected = model.Step(input);
                        Check(before == expected.Before && produced == expected.AfterProducer && after == expected.After, "Independent persistent state/counters/IE");
                        Check(Equal(p!.Writes, expected.ProducerWrites), "Ordered producer stores including same-value writes");
                        Check(Equal(actualTables, expected.TableReads), "Actual ordered table addresses/words");
                        Check(Equal(p.Events.Where(e => ProducerBranches.Contains(e[0])).Select(e => new[] { e[0], e[1] }).ToArray(), expected.Branches), "Actual producer branch decisions");
                        for (var ti = 0; ti < tickStages.Count; ti++)
                        {
                            Check(Equal(tickStages[ti].Writes, expected.Ticks[ti].Writes), "Native counter stores");
                            Check(Equal(tickStages[ti].Events.Where(e => e[0] == 0x5BD3).Select(e => new[] { e[0], e[1] }).ToArray(), expected.Ticks[ti].Branches), "Native counter zero gate");
                            Check(tickStages[ti].Events[0][3] % 256 == expected.Ticks[ti].Before, "Native counter read");
                        }
                        ValidateLimiter(l, produced!.Limiter, after.Limiter, expected.Limiter, Check);
                        var critical = p.Events.Where(e => e[0] is 0x48E6 or 0x48E9 or 0x48EC or 0x48EE).ToArray();
                        Check(expected.Path == "TimerHold" ? critical.Length == 0 : critical.Length == 4 && (critical[0][5] & 256) == 0 && (critical[1][4] & 256) == 0 && (critical[2][4] & 256) == 0 && (critical[3][5] & 256) != 0, "Actual MIE critical section");
                    }
                    else if (status == 1) unresolved++; else errors++;
                    stopped = status != 0;
                }
                if (diff.Count > 0) mismatches++; else if (status == 0) matches++;
                int? bank = p?.Events.FirstOrDefault(e => e[0] == 0x4882) is { } bankEvent ? bankEvent[1] == 0x4885 ? 1 : 0 : null;
                string? path = p?.Result.Status != 0 ? null : p.Events.Any(e => e[0] == 0x4897) ? "Reset217" :
                    p.Events.Any(e => e[0] == 0x489D && e[1] == 0x48E1) ? "Reset214" :
                    p.Events.Any(e => e[0] == 0x48A2 && e[1] == 0x48F5) ? "TimerHold" :
                    p.Events.Any(e => e[0] == 0x5AC2) ? "AdaptiveBound" : p.Events.Any(e => e[0] == 0x48C7) ? "CounterResetDecrease" : "CounterPendingDecrease";
                var decided = hasLimiter && l.GetProperty("decision").GetProperty("status").GetInt32() == 0;
                var actualComparisons = decided ? Matrix(l, "decisionEvents", 8).Where(e => e[0] == 0x197D).ToArray() : [];
                var actualSource = !decided || actualComparisons.Length != 1 ? null : Matrix(l, "decisionEvents", 8).Any(e => e[0] == 0x1974) ? "AdaptiveRam" : "Fixed";
                rows.Add(new(i, status switch { 0 => diff.Count == 0 ? "StrictMatch" : "Mismatch", 1 => "Unresolved", 4 => "NotRun", _ => "ExecutionError" }, input, c.Clone(), bank, path, actualTables,
                    actualSource, actualComparisons.Length == 1 ? actualComparisons[0][7] : null,
                    decided ? NullableBool(l.GetProperty("overspeedRequest")) : null, decided ? (produced!.Limiter.Data012A & 128) != 0 : null,
                    hasLimiter ? NullableBool(l.GetProperty("inhibitBranch")) : null, expected, diff.AsReadOnly())); previous = after;
            }
            reports.Add(new(pattern, new(scenario.Calls.Count, complete, matches, 0, unresolved, 0, notRun, mismatches, errors, complete), rows.AsReadOnly()));
        }
        return new(1, baseline.Hash, profile.Id, P28VtecInspector.ComputeProfileDigest(profile), scenario.Digest, root.GetProperty("entryContracts").Clone(), reports.AsReadOnly());
    }
    private static void ValidateLimiter(JsonElement l, P28LimiterState produced, P28LimiterState after, P28LimiterModelStep? expected, Action<bool, string> check)
    {
        P28LimiterScenario.Shape(l, "index", "status", "stateBefore", "stateAfter", "decision", "consumer", "decisionWrites", "consumerWrites", "decisionEvents", "consumerEvents", "overspeedRequest", "inhibitBranch");
        var before = P28LimiterValidator.State(l.GetProperty("stateBefore"));
        check(before == produced && P28LimiterValidator.State(l.GetProperty("stateAfter")) == after, "Direct RAM handoff / downstream state");
        var d = P28AcquisitionValidator.ParseStage(l.GetProperty("decision"), 96, 0, [], null); var c = P28AcquisitionValidator.ParseStage(l.GetProperty("consumer"), 96, 0, [], null);
        var dw = Matrix(l, "decisionWrites", 3); var cw = Matrix(l, "consumerWrites", 3); var de = Matrix(l, "decisionEvents", 8); var ce = Matrix(l, "consumerEvents", 8);
        var request = NullableBool(l.GetProperty("overspeedRequest")); var inhibit = NullableBool(l.GetProperty("inhibitBranch"));
        Require(d is not null && l.GetProperty("status").GetInt32() == (c?.Status ?? d.Status), "Missing/contradictory limiter stage.");
        ValidateTrace(d, de, false); ValidateTrace(c, ce, true);
        Require(d!.Status != 0 ? c is null && request is null && inhibit is null && cw.Length + ce.Length == 0 : c is not null && request.HasValue, "Execution/fabricated output after decision stop.");
        Require((c?.Status == 0) == inhibit.HasValue, "Unavailable consumer must be null.");
        if (expected is null) return;
        check(before == expected.Before && after == expected.After, "Independent limiter state");
        check(request == expected.OverspeedRequest && inhibit == expected.InhibitBranch, "Limiter request / independent inhibit");
        check(Equal(dw, expected.DecisionWrites) && Equal(cw, expected.ConsumerWrites), "Ordered limiter/consumer stores");
        check(d.StopPc == 0x1A38 && c!.StopPc == 0x5596, "Limiter/consumer exits");
        var cmp = de.Where(e => e[0] == 0x197D).ToArray();
        check(cmp.Length == 1 && cmp[0][6] == expected.ComparisonLeft && cmp[0][7] == expected.Threshold && ((cmp[0][5] & 0x8000) != 0) == expected.OverspeedRequest && ((cmp[0][5] & 0x4000) != 0) == (expected.ComparisonLeft == expected.Threshold), "Actual threshold operand / CF / ZF");
        check(de.Any(e => e[0] == 0x1974) == (expected.Context != "Fixed") && de.Any(e => e[0] == 0x197C) == ((before.Data0124 & 32) != 0), "Fixed versus actual adaptive RAM / prior-state selection");
        check(de.Any(e => e[0] == 0x1980 && e[1] == (expected.OverspeedRequest ? 0x19AC : 0x1982)), "Limiter branch");
        check(ce.Any(e => e[0] == 0x558B) == !expected.InhibitBranch && ce.Length > 0 && (ce[^1][3] & 255) == expected.ConsumerAccumulator, "Native consumer branch/accumulator");
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id="adaptiveLimiter",producerEntry=0x487B,producerExit=0x48F5,codeRanges=new[]{new[]{0x487B,0x48F5},new[]{0x5AB8,0x5AE6}},tableRange=new[]{0x6493,0x64AB},
        tickEntry=0x5BD0,tickExit=0x5BD9,tickTargets=new[]{0x1D5,0x1CE},producerPsw=0x1101,tickPsw=1,lrb=0x41,scb=1,usp=0x180,ssp=0x7FE,stackRange=new[]{0x7FE,0x800},producerBudget=160,tickBudget=3,
        dataRanges=new[]{new[]{0,8},new[]{0x1A,0x1C},new[]{0x88,0x90},new[]{0xCE,0xD0},new[]{0xD9,0xDA},new[]{0xF8,0xFA},new[]{0x124,0x125},new[]{0x12A,0x12C},new[]{0x18F,0x190},new[]{0x1A4,0x1A8},new[]{0x1CE,0x1CF},new[]{0x1D5,0x1D6},new[]{0x1D7,0x1D8},new[]{0x208,0x210},new[]{0x212,0x213},new[]{0x214,0x215},new[]{0x217,0x218},new[]{0x21F,0x220},new[]{0x223,0x224},new[]{0x7FE,0x800}},
        limiterDecisionEntry=0x1966,limiterDecisionExit=0x1A38,consumerEntry=0x5585,consumerExit=0x5596,stop="BeforeInstruction",ie="Word-only software storage; no IRQ delivery",state="Once-only thresholds/counters; native stores thereafter",ticks="Explicit native single-element service schedule, not elapsed time",physicalRpmAvailable=false,assumptions=Array.Empty<string>() } });
}
