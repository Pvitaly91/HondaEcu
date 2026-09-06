using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public static partial class P28ChainValidator
{
    public const string Operation = "integratedCaptureVtec";
    internal static readonly string[] StageIds = ["Acquisition", "NativeCounterBodies", "G", "F", "Decision"];
    internal static readonly string[] Permissions = [P28ProducerModel.AddEr1Assumption, P28ByteExecutionValidator.AddAssumption, P28StatefulModel.SubbOffAssumption];
    private static readonly int[] Patterns = [0, 85, 170];
    public static IReadOnlyList<string> ValidateAssumptions(IEnumerable<string> values)
    {
        var a = values.ToArray();
        if (a.Length > 3 || a.Distinct(StringComparer.Ordinal).Count() != a.Length || a.Any(v => !Permissions.Contains(v)))
            throw new ArgumentException("Only the three separate er1, er3 and SUBB form permissions are accepted.");
        return Array.AsReadOnly(a.Order(StringComparer.Ordinal).ToArray());
    }
    private static RomImage[] Images(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        RomImage? derived, P28VerifiedChecksumComposition? verified)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, confirmed, derived, composition: verified);
        if (derived is null) return [baseline];
        if (verified is null) throw new InvalidDataException("Full verified M1g lineage required.");
        // Comparison-only B, derived from the already admitted one-slot plan.
        // No new raw plan, compensation, trusted binding, signing or export.
        var p = verified.Plan.ThresholdPlan;
        var intermediate = baseline.CreateModifiedCopy([new BytePatch(p.Offset, [p.NewByte])]);
        return [baseline, intermediate, derived];
    }
    internal static object Request(IReadOnlyList<RomImage> images, P28ChainScenario scenario, IReadOnlyList<string> allowed) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = images.Select((image, i) => new { id = ImageId(i), rom = image.ToArray().Select(b => (int)b).ToArray() }).ToArray(),
        scratchPatterns = Patterns,
        allowAssumptions = allowed,
        integratedChain = new { formatVersion = 1, initialState = scenario.InitialState, events = scenario.Events, traceEventIndexes = scenario.TraceEventIndexes }
    };
    public static async Task<P28ChainReport> ExecuteAsync(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28ChainScenario scenario, IEnumerable<string>? assumptions = null, RomImage? derived = null,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default, P28VerifiedChecksumComposition? verifiedComposition = null)
    {
        cancellationToken.ThrowIfCancellationRequested(); var allowed = ValidateAssumptions(assumptions ?? []);
        var images = Images(baseline, profile, binding, confirmed, derived, verifiedComposition);
        var response = await SeededSliceProcess.ExchangeAsync(runner, Request(images, scenario, allowed), options, cancellationToken).ConfigureAwait(false);
        var report = Analyze(baseline, profile, binding, scenario, response, allowed, derived, verifiedComposition);
        var first = report.Sequences.SelectMany(s => s.Checkpoints).Where(c => c.Differences.Count > 0 || c.Stages.Any(s => s.Differences.Count > 0)).Select(c => (int?)c.Index).Min();
        if (first is null) return report;
        var replay = scenario.ForReplay(first.Value); var diagnostics = new List<JsonElement>();
        try
        {
            var response2 = await SeededSliceProcess.ExchangeAsync(runner, Request(images, replay, allowed), options, cancellationToken).ConfigureAwait(false);
            var repeated = Analyze(baseline, profile, binding, replay, response2, allowed, derived, verifiedComposition);
            diagnostics.Add(JsonSerializer.SerializeToElement(new
            {
                purpose = "Original initial state and entire prefix; no observed-state reseeding",
                index = first.Value,
                witnesses = repeated.Sequences.Select(s => new { s.ImageId, s.ScratchPattern, checkpoint = s.Checkpoints.Last() })
            }, JsonDefaults.Create(false)));
        }
        catch (SliceProcessException e) { diagnostics.Add(JsonSerializer.SerializeToElement(new { purpose = "Replay unavailable; original failure retained", failure = e.Failure })); }
        return report with { ReplayDiagnostics = diagnostics.AsReadOnly() };
    }
    public static P28ChainReport Analyze(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28ChainScenario scenario, SliceProcessResponse response, IEnumerable<string>? assumptions = null,
        RomImage? derived = null, P28VerifiedChecksumComposition? verifiedComposition = null)
    {
        var images = Images(baseline, profile, binding, true, derived, verifiedComposition); var allowed = ValidateAssumptions(assumptions ?? []);
        try { return AnalyzeCore(images, scenario, response.Response, allowed, verifiedComposition?.Plan.Compensation.Offset); }
        catch (Exception e) when (e is JsonException or InvalidDataException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed bounded integrated response.", e); }
    }
    private static string ImageId(int i) => i switch { 0 => "baseline", 1 => "intermediate", _ => "derived" };
    private static P28ChainReport AnalyzeCore(RomImage[] images, P28ChainScenario scenario, JsonElement root, IReadOnlyList<string> allowed, int? compensation)
    {
        Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts",
            "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "chainSequences");
        var fixes = SliceRunnerIdentity.Validate(root, Operation);
        if (!Equal(root.GetProperty("entryContracts"), EntryContracts())) throw Protocol("Integrated stage contract differs.");
        if (root.GetProperty("syntheticResult").ValueKind != JsonValueKind.Null || new[] { "compactRows", "thresholdRows", "diagnostics" }.Any(n => root.GetProperty(n).GetArrayLength() != 0))
            throw Protocol("Unrelated task result present.");
        var rows = root.GetProperty("chainSequences"); if (rows.GetArrayLength() != images.Length * 3) throw Protocol("Missing image/scratch sequences.");
        var seen = new HashSet<(int, int)>(); var sequences = new List<P28ChainSequence>(); var failed = false; var compensationClear = true;
        foreach (var row in rows.EnumerateArray())
        {
            Shape(row, "imageIndex", "scratchPattern", "checkpoints", "completedEvents", "completedDecisions", "stopEventIndex");
            var image = Int(row, "imageIndex", 0, images.Length - 1); var pattern = Int(row, "scratchPattern", 0, 255);
            if (!Patterns.Contains(pattern) || !seen.Add((image, pattern))) throw Protocol("Duplicate or unknown sequence.");
            var entries = row.GetProperty("checkpoints"); if (entries.GetArrayLength() != scenario.Events.Count) throw Protocol("Incomplete event/suffix inventory.");
            var model = new P28ChainModel(images[image].Span, scenario.InitialState, allowed); var previous = scenario.InitialState;
            P28ChainArchitecture? previousArchitecture = InitialArchitecture(pattern);
            var cumulative = new HashSet<string>(StringComparer.Ordinal); var checkpoints = new List<P28ChainCheckpoint>();
            var counts = new int[6]; var mask = 0; var stop = -1; var complete = 0; var decisions = 0;
            foreach (var element in entries.EnumerateArray())
            {
                Shape(element, "index", "input", "stateBefore", "stateAfterInputs", "callerWrites", "stages", "stateAfter",
                    "softwareRequest", "requestMirror", "selectionStatus", "everWrittenMask", "slotWriteCounts", "cumulativeAssumptions");
                var index = Int(element, "index", 0, scenario.Events.Count - 1); if (index != checkpoints.Count) throw Protocol("Non-dense event indexes.");
                var input = scenario.Events[index]; P28ChainScenario.EventShape(element.GetProperty("input"));
                if (!Equal(element.GetProperty("input"), input)) throw Protocol("Event schedule echo differs.");
                var expected = model.Step(input); // Only its own previous state; never actual checkpoints.
                var suffix = stop >= 0; var differences = new List<string>();
                void Check(bool value, string message) { if (!value) differences.Add(message); }
                var before = State(element.GetProperty("stateBefore")); var afterInputs = State(element.GetProperty("stateAfterInputs"));
                var after = State(element.GetProperty("stateAfter")); var caller = Matrix(element, "callerWrites", 3, 8);
                Check(Equal(before, previous), "Actual event continuity");
                Check(Equal(before, expected.Before), "Independent event state before");
                Check(Equal(afterInputs, expected.AfterInputs), "Independent scripted input state");
                Check(Equal(caller, suffix ? Array.Empty<int[]>() : P28ChainModel.CallerWrites(before, input)), "Only documented masked caller writes");
                if (suffix && (!Equal(before, afterInputs) || !Equal(before, after) || caller.Count != 0)) throw Protocol("Terminal suffix reapplied inputs or mutated state.");
                var stages = element.GetProperty("stages"); if (stages.GetArrayLength() != 5) throw Protocol("Fixed five-stage inventory required.");
                var comparisons = new List<P28ChainStageComparison>(); var stagePrevious = afterInputs; var live = !suffix;
                foreach (var stageElement in stages.EnumerateArray())
                {
                    var position = comparisons.Count; var actual = ParseStage(stageElement, allowed); var target = expected.Stages[position];
                    if (actual.Id != StageIds[position]) throw Protocol("Stage order differs.");
                    var scheduled = position < 2 || input.RunDecision;
                    var emptyTicks = position == 1 && input.FastTicks + input.SlowTicks == 0;
                    if ((!live || !scheduled || emptyTicks) && actual.Status != 4 || live && scheduled && !emptyTicks && actual.Status == 4)
                        throw Protocol("Missing, invented or resumed stage.");
                    var diffs = new List<string>(); void StageCheck(bool value, string message) { if (!value) diffs.Add(message); }
                    StageCheck(Equal(actual.StateBefore, stagePrevious), "Actual stage state continuity");
                    StageCheck(Equal(actual.ArchitectureBefore, previousArchitecture), "Actual architecture continuity");
                    StageCheck(Equal(actual.StateAtEntry, actual.StateBefore), "Stage entry did not reseed persistent/produced inputs");
                    StageCheck(Equal(actual.StateBefore, target.Before) && Equal(actual.StateAfter, target.After), "Independent complete shared state");
                    StageCheck(actual.Status == target.Status, "Stage disposition");
                    StageCheck(actual.Execution?.StopPc == target.StopPc, "Stage exit/boundary");
                    StageCheck(Equal(actual.NativeWrites.Where(TouchesPersistent), target.PersistentWrites), "Ordered persistent byte/word side effects");
                    StageCheck(Equal(actual.PeripheralAccesses, target.PeripheralAccesses), "Frozen acquisition read sequence/scope");
                    StageCheck(Equal(actual.Execution?.UsedAssumptions ?? [], target.UsedAssumptions), "Exact stage-local assumption use");
                    foreach (var used in actual.Execution?.UsedAssumptions ?? []) cumulative.Add(used);
                    if (!actual.CumulativeAssumptions.SequenceEqual(cumulative.Order(StringComparer.Ordinal))) throw Protocol("Lost/invented cumulative assumptions.");
                    StageCheck(Equal(actual.CumulativeAssumptions, target.CumulativeAssumptions), "Independent conditional history");
                    CheckArchitecture(actual, input, StageCheck);
                    ValidateExecution(actual, input, scenario.TraceEventIndexes.Contains(index) || index == row.GetProperty("stopEventIndex").GetInt32());
                    var gates = P28StatefulValidator.ProjectGates(actual.GateEvents);
                    var thresholds = P28StatefulValidator.ProjectThresholds(gates);
                    if (target.Decision is { } d)
                    {
                        StageCheck(Equal(gates, d.Gates), "Actual gates/operands and NotEvaluated");
                        StageCheck(Equal(thresholds, d.Thresholds), "Selected context/threshold/prior bits");
                        StageCheck(actual.GateEvents.Select(g => g[0]).SequenceEqual(d.ExecutedGatePcs), "Executed gate order");
                    }
                    else if (actual.GateEvents.Count != 0) StageCheck(false, "Unexpected decision gate execution");
                    if (compensation is int offset && actual.Execution is { } execution)
                        compensationClear &= !execution.ProgramReads.Contains(offset) && !execution.ExecutedInstructionBytes.Contains(offset);
                    if (position == 0)
                        foreach (var write in actual.NativeWrites.Where(w => w[0] < 0x36C && w[0] + w[1] / 8 > 0x360))
                        {
                            if (write[1] != 16 || write[0] < 0x360 || (write[0] & 1) != 0) throw Protocol("Malformed sample store.");
                            var slot = (write[0] - 0x360) / 2; counts[slot]++; mask |= 1 << slot;
                        }
                    if (live && scheduled && actual.Status is 1 or 2 or 3 or 5) { live = false; stop = index; }
                    var validation = actual.Status switch
                    {
                        1 => "Unresolved",
                        2 => "ExecutionError",
                        3 => "BudgetExceeded",
                        4 => "NotRun",
                        5 => "Unsupported",
                        _ => diffs.Count != 0 ? "Mismatch" : cumulative.Count == 0 ? "StrictMatch" : "ConditionalMatch"
                    };
                    failed |= diffs.Count != 0 || actual.Status is 2 or 3;
                    comparisons.Add(new(actual, target, validation, position == 4 ? gates : [], thresholds, diffs.AsReadOnly()));
                    stagePrevious = actual.StateAfter; previousArchitecture = actual.ArchitectureAfter;
                }
                if (live) complete++;
                var decisionComplete = comparisons[4].Actual.Status == 0; if (decisionComplete) decisions++;
                var request = Bool(element, "softwareRequest"); var mirror = Bool(element, "requestMirror"); var selection = Bool(element, "selectionStatus");
                if (!decisionComplete && (request is not null || mirror is not null || selection is not null)) throw Protocol("Stale latch was presented as a new request.");
                Check(request == expected.SoftwareRequest && mirror == expected.RequestMirror && selection == expected.SelectionStatus, "Independent request/mirror/status");
                if (decisionComplete) Check(request == ((after.Decision.P1OutputData & 1) != 0) && mirror == ((after.Decision.Data0127 & 4) != 0) && selection == ((after.Decision.Data0127 & 2) != 0), "Outputs from native decision state");
                Check(Equal(after, stagePrevious) && Equal(after, expected.After), "Final event shared state");
                var observedCounts = Integers(element, "slotWriteCounts", 0, 256, 6, true);
                if (Int(element, "everWrittenMask", 0, 63) != mask || !observedCounts.SequenceEqual(counts) ||
                    !Assumptions(element, "cumulativeAssumptions", allowed).SequenceEqual(cumulative.Order(StringComparer.Ordinal))) throw Protocol("Event write/assumption accounting differs.");
                failed |= differences.Count != 0; previous = after;
                checkpoints.Add(new(index, input, before, afterInputs, caller, comparisons.AsReadOnly(), after, request, mirror, selection, mask,
                    observedCounts, cumulative.Order(StringComparer.Ordinal).ToArray(), differences.AsReadOnly()));
            }
            if (Int(row, "completedEvents", 0, 256) != complete || Int(row, "completedDecisions", 0, 256) != decisions || Int(row, "stopEventIndex", -1, 255) != stop)
                throw Protocol("Sequence denominators do not match execution.");
            var stageCounts = StageIds.ToDictionary(id => id, id => Counts(checkpoints, id));
            sequences.Add(new(image, ImageId(image), pattern, scenario.Events.Count, complete, decisions, stop, counts.Sum(), stageCounts, checkpoints.AsReadOnly()));
        }
        var pairs = CompareImages(sequences, images.Length);
        failed |= !compensationClear || pairs.Where(p => p.Pair == "B/C").Any(p => !p.ObservedExecutionPrefixesEqual);
        return new("1.0", "integrated-capture-to-vtec-byte-execution-agreement", images[0].Hash, images.Length == 3 ? images[1].Hash : null,
            images.Length == 3 ? images[2].Hash : null, scenario.Digest, root.GetProperty("runnerVersion").GetString()!, fixes, allowed,
            sequences.AsReadOnly(), pairs, compensation is null ? null : compensationClear, failed, []);
    }
    private static P28ChainStageCounts Counts(IReadOnlyList<P28ChainCheckpoint> checkpoints, string id)
    {
        var stages = checkpoints.Select(c => c.Stages.Single(s => s.Actual.Id == id)).ToArray();
        int Count(string value) => stages.Count(s => s.Validation == value);
        var requested = checkpoints.Count(c => id == "Acquisition" || id == "NativeCounterBodies" && c.Input.FastTicks + c.Input.SlowTicks > 0 || id is "G" or "F" or "Decision" && c.Input.RunDecision);
        return new(requested, stages.Count(s => s.Actual.Execution?.Steps > 0), Count("StrictMatch"), Count("ConditionalMatch"), Count("Unresolved"),
            Count("Unsupported"), Count("NotRun"), Count("Mismatch"), Count("ExecutionError"), Count("BudgetExceeded"));
    }
    internal static bool Equal<T, U>(T a, U b) => JsonNode.DeepEquals(JsonSerializer.SerializeToNode(a, JsonDefaults.Create(false)), JsonSerializer.SerializeToNode(b, JsonDefaults.Create(false)));
    private static SliceProcessException Protocol(string message) => new(SliceProcessFailure.Protocol, message);
}
