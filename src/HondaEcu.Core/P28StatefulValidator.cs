using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed record P28StatefulObservedStep(int Index, int Status, P28VtecCall Input,
    P28VtecPersistentState StateBefore, P28VtecPersistentState StateAtEntry, P28VtecPersistentState StateAfter,
    bool? SoftwareRequest, bool? SelectionStatus, IReadOnlyList<int[]> TickRuns, IReadOnlyList<int[]> TickWrites,
    IReadOnlyList<int[]> DecisionWrites, IReadOnlyList<int[]> GateEvents, P28AcquisitionStageResult? Execution,
    P28AcquisitionStageResult? TickFailure, IReadOnlyList<string> CumulativeAssumptions);
public sealed record P28StatefulCheckpoint(P28StatefulObservedStep Actual, P28StatefulModelStep? Expected,
    IReadOnlyList<P28VtecGate> ActualGates, IReadOnlyList<P28VtecThresholdSelection> ActualThresholds,
    string ThresholdValidation, string DownstreamValidation, IReadOnlyList<string> Differences);
public sealed record P28StatefulSequence(int ImageIndex, string ImageId, int ScratchPattern, int CompletedCalls, int StopCallIndex,
    int StrictMatches, int ConditionalMatches, int Unresolved, int NotRun, IReadOnlyList<P28StatefulCheckpoint> Checkpoints);
public sealed record P28StatefulChildComparison(int ScratchPattern, int PairedCalls, int? FirstStateDifference,
    int StateDifferences, int RequestDifferences, int? FirstRejoinedAfterDifference, bool CompensationNotAccessed);
public sealed record P28StatefulValidationReport(string FormatVersion, string Purpose, RomHash BaselineHash, RomHash? DerivedHash,
    string ScenarioDigest, string RunnerVersion, IReadOnlyList<string> LocalSemanticFixes, IReadOnlyList<string> AllowedAssumptions,
    IReadOnlyList<P28StatefulSequence> Sequences, IReadOnlyList<P28StatefulChildComparison> ChildComparison,
    bool HasFailure, IReadOnlyList<JsonElement> ReplayDiagnostics)
{
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string ActualComposedAcquisition => "NotRun: this task isolates explicit raw compactCode; existing M1i remains available separately.";
    public string SoftwareBoundary => "Before 0x12FC; P1 output-data-register only under all-output/no-external-bus precondition; no physical actuator claim.";
}

public static class P28StatefulValidator
{
    public const string Operation = "statefulVtec";
    private static readonly int[] Patterns = [0, 85, 170];
    public static IReadOnlyList<string> ValidateAssumptions(IEnumerable<string> values)
    {
        var result = values.ToArray();
        if (result.Length > 1 || result.Any(a => a != P28StatefulModel.SubbOffAssumption))
            throw new ArgumentException("VTEC-only permits only one explicit oki.subb-a-off-n8-encoding assumption; no ADD permissions.");
        return Array.AsReadOnly(result);
    }
    public static object CreateRequest(RomImage baseline, RomImage? derived, P28StatefulScenario scenario, IEnumerable<string>? assumptions = null)
    {
        ArgumentNullException.ThrowIfNull(scenario); baseline.ValidateExactSize(32768); derived?.ValidateExactSize(32768);
        var images = new List<object> { new { id = "baseline", rom = baseline.ToArray().Select(b => (int)b).ToArray() } };
        if (derived is not null) images.Add(new { id = "derived", rom = derived.ToArray().Select(b => (int)b).ToArray() });
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images,
            scratchPatterns = Patterns.ToArray(),
            allowAssumptions = ValidateAssumptions(assumptions ?? []),
            statefulVtec = new { formatVersion = 1, initialState = scenario.InitialState, calls = scenario.Calls, traceCallIndexes = scenario.TraceCallIndexes }
        };
    }
    public static async Task<P28StatefulValidationReport> ExecuteAsync(RomImage baseline, RomProfile profile,
        P28ExactBaselineBinding binding, bool confirmed, string runner, P28StatefulScenario scenario,
        IEnumerable<string>? assumptions = null, RomImage? derived = null, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default, P28VerifiedChecksumComposition? verifiedComposition = null)
    {
        cancellationToken.ThrowIfCancellationRequested();
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, confirmed, derived, composition: verifiedComposition);
        var allowed = ValidateAssumptions(assumptions ?? []);
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(baseline, derived, scenario, allowed), options, cancellationToken).ConfigureAwait(false);
        var report = Analyze(baseline, profile, binding, scenario, response, allowed, derived, verifiedComposition);
        var first = report.Sequences.SelectMany(s => s.Checkpoints).Where(c => c.Differences.Count != 0).Select(c => (int?)c.Actual.Index).Min();
        if (first is null) return report;
        var replay = scenario.ForReplay(first.Value);
        var diagnostics = new List<JsonElement>();
        try
        {
            var repeated = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(baseline, derived, replay, allowed), options, cancellationToken).ConfigureAwait(false);
            var analyzed = Analyze(baseline, profile, binding, replay, repeated, allowed, derived, verifiedComposition);
            diagnostics.Add(JsonSerializer.SerializeToElement(new
            {
                purpose = "Original initial state and whole prefix; no observed-state reseeding",
                index = first.Value,
                witnesses = analyzed.Sequences.Select(s => new { s.ImageIndex, s.ScratchPattern, checkpoint = s.Checkpoints.Last() })
            }, JsonDefaults.Create(false)));
        }
        catch (SliceProcessException e)
        { diagnostics.Add(JsonSerializer.SerializeToElement(new { purpose = "Prefix replay unavailable; original failure retained", failure = e.Failure })); }
        return report with { ReplayDiagnostics = diagnostics.AsReadOnly() };
    }

    public static P28StatefulValidationReport Analyze(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28StatefulScenario scenario, SliceProcessResponse response, IEnumerable<string>? assumptions = null,
        RomImage? derived = null, P28VerifiedChecksumComposition? verifiedComposition = null)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, derived, composition: verifiedComposition);
        var allowed = ValidateAssumptions(assumptions ?? []);
        try { return AnalyzeCore(baseline, derived, scenario, response.Response, allowed, verifiedComposition); }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed bounded stateful response.", e); }
    }

    private static P28StatefulValidationReport AnalyzeCore(RomImage baseline, RomImage? derived, P28StatefulScenario scenario,
        JsonElement root, IReadOnlyList<string> allowed, P28VerifiedChecksumComposition? composition)
    {
        var fixes = SliceRunnerIdentity.Validate(root, Operation);
        if (!Equal(root.GetProperty("entryContracts"), EntryContracts())) throw Protocol("Stateful entry contract differs.");
        foreach (var name in new[] { "compactRows", "thresholdRows", "diagnostics" })
            if (root.GetProperty(name).GetArrayLength() != 0) throw Protocol("Unrelated task results present.");
        var rows = root.GetProperty("statefulSequences");
        if (rows.GetArrayLength() != (derived is null ? 3 : 6)) throw Protocol("Missing or extra independent sequences.");
        var sequences = new List<P28StatefulSequence>();
        var seen = new HashSet<(int, int)>(); var hasFailure = false;
        foreach (var row in rows.EnumerateArray())
        {
            Shape(row, "imageIndex", "scratchPattern", "checkpoints", "completedCalls", "stopCallIndex", "remainingNotRun");
            var image = Int(row, "imageIndex", 0, derived is null ? 0 : 1); var pattern = Int(row, "scratchPattern", 0, 255);
            if (!Patterns.Contains(pattern) || !seen.Add((image, pattern))) throw Protocol("Duplicate or unknown independent sequence.");
            var model = new P28StatefulModel((image == 0 ? baseline : derived!).Span, scenario.InitialState);
            var checkpoints = row.GetProperty("checkpoints");
            if (checkpoints.GetArrayLength() != scenario.Calls.Count) throw Protocol("Incomplete sequence, including NotRun suffix.");
            var compared = new List<P28StatefulCheckpoint>(); var stop = -1; var complete = 0; var strict = 0; var conditional = 0; var unresolved = 0; var notRun = 0;
            var cumulative = new HashSet<string>(StringComparer.Ordinal); var previous = scenario.InitialState;
            foreach (var element in checkpoints.EnumerateArray())
            {
                var actual = ParseStep(element, allowed);
                if (actual.Index != compared.Count || !Equal(actual.Input, scenario.Calls[actual.Index])) throw Protocol("Input schedule echo differs.");
                var differences = new List<string>();
                void Check(bool match, string name) { if (!match) differences.Add(name); }
                Check(actual.StateBefore == previous, "Actual persistent continuity");
                var gates = ProjectGates(actual.GateEvents);
                var selections = ProjectThresholds(gates);
                P28StatefulModelStep? expected = null;
                if (stop >= 0)
                {
                    if (actual.Status != 4 || actual.Execution is not null || actual.TickFailure is not null || actual.TickRuns.Count != 0 ||
                        actual.TickWrites.Count != 0 || actual.DecisionWrites.Count != 0 || actual.GateEvents.Count != 0 || actual.SoftwareRequest is not null ||
                        actual.SelectionStatus is not null || actual.StateAtEntry != previous || actual.StateAfter != previous)
                        throw Protocol("Terminal sequence resumed or NotRun output was fabricated.");
                    notRun++;
                }
                else
                {
                    if (actual.Status == 4) throw Protocol("Unexplained NotRun before terminal stop.");
                    expected = model.Step(actual.Input, allowed.Contains(P28StatefulModel.SubbOffAssumption));
                    Check(actual.StateBefore == expected.Before, "Independent state before");
                    Check(actual.StateAtEntry == expected.AtEntry, "Independent counters at entry");
                    Check(actual.StateAfter == expected.After, "Independent persistent state after");
                    Check(Equal(actual.TickWrites, expected.TickWrites), "Ordered native counter writes");
                    Check(Equal(actual.DecisionWrites, expected.DecisionWrites), "Ordered persistent decision writes");
                    Check(Equal(gates, expected.Gates), "Executed gate outcomes/operands and NotEvaluated");
                    Check(actual.GateEvents.Select(e => e[0]).SequenceEqual(expected.ExecutedGatePcs), "Executed gate order");
                    Check(Equal(selections, expected.Thresholds), "Selected context/threshold and old/new bits");
                    Check(actual.Status == expected.Status, "Execution disposition");
                    Check(actual.Execution?.StopPc == expected.StopPc, "Decision exit/boundary PC");
                    Check(actual.SoftwareRequest == expected.SoftwareRequest && actual.SelectionStatus == expected.SelectionStatus, "Software outputs");
                    Check(actual.TickFailure is null, "Native counter fragment completion");
                    Check(ValidTickRuns(actual), "Native tick schedule/exits");
                    foreach (var a in actual.Execution?.UsedAssumptions ?? []) cumulative.Add(a);
                    Check(Equal(actual.Execution?.UsedAssumptions ?? [], expected.UsedAssumptions), "Per-call instruction assumptions");
                    if (actual.Status == 0)
                    { complete++; if (differences.Count == 0) { if (cumulative.Count == 0) strict++; else conditional++; } }
                    else { stop = actual.Index; if (actual.Status == 1) unresolved++; }
                }
                Check(actual.CumulativeAssumptions.SequenceEqual(cumulative.Order(StringComparer.Ordinal)), "Cumulative assumptions");
                previous = actual.StateAfter;
                var thresholdOk = expected is not null && actual.Execution is not null && actual.TickFailure is null &&
                    actual.StateBefore.Data0131 == expected.Before.Data0131 && actual.StateAtEntry.Data0131 == expected.AtEntry.Data0131 &&
                    actual.StateAfter.Data0131 == expected.After.Data0131 && Equal(selections, expected.Thresholds) &&
                    Equal(gates.Where(g => g.Pc < 0x126D), expected.Gates.Where(g => g.Pc < 0x126D)) &&
                    actual.GateEvents.Select(e => e[0]).Where(pc => pc < 0x126D).SequenceEqual(expected.ExecutedGatePcs.Where(pc => pc < 0x126D)) &&
                    Equal(actual.DecisionWrites.Where(w => w[0] == 0x131), expected.DecisionWrites.Where(w => w[0] == 0x131));
                var thresholdStatus = actual.Status == 4 ? "NotRun" : thresholdOk ? actual.Input.Enabled ? "MatchedStatefulThresholds" : "MatchedDisabledPersistence" : "MismatchOrUnresolved";
                var downstream = actual.Status == 4 ? "NotRun" : actual.Status == 1 ? "Unresolved" : actual.Status != 0 || differences.Count != 0 ? "Failed" : cumulative.Count == 0 ? "StrictMatch" : "ConditionalMatch";
                hasFailure |= differences.Count != 0 || actual.Status is 2 or 3;
                compared.Add(new(actual, expected, gates, selections, thresholdStatus, downstream, differences.AsReadOnly()));
            }
            if (Int(row, "completedCalls", 0, 256) != complete || Int(row, "stopCallIndex", -1, 255) != stop || Int(row, "remainingNotRun", 0, 255) != notRun)
                throw Protocol("Sequence totals differ from checkpoints.");
            sequences.Add(new(image, image == 0 ? "baseline" : "derived", pattern, complete, stop, strict, conditional, unresolved, notRun, compared.AsReadOnly()));
        }
        var child = new List<P28StatefulChildComparison>();
        if (derived is not null)
        {
            var compensation = composition!.Plan.Compensation.Offset;
            foreach (var pattern in Patterns)
            {
                var a = sequences.Single(s => s.ImageIndex == 0 && s.ScratchPattern == pattern);
                var c = sequences.Single(s => s.ImageIndex == 1 && s.ScratchPattern == pattern);
                int? first = null, rejoined = null; var changed = 0; var requests = 0; var paired = 0; var unaccessed = true;
                for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var x = a.Checkpoints[i].Actual; var y = c.Checkpoints[i].Actual;
                    foreach (var cp in new[] { x, y })
                        if (cp.Execution is { } run) unaccessed &= !run.ProgramReads.Contains(compensation) && !run.ExecutedInstructionBytes.Contains(compensation);
                    if (x.Status != 0 || y.Status != 0) continue;
                    paired++;
                    if (x.StateAfter != y.StateAfter) { changed++; first ??= i; }
                    else if (first is not null) rejoined ??= i;
                    if (x.SoftwareRequest != y.SoftwareRequest) requests++;
                }
                child.Add(new(pattern, paired, first, changed, requests, rejoined, unaccessed));
                hasFailure |= !unaccessed;
            }
        }
        return new("1.0", "stateful-vtec-software-decision-validation", baseline.Hash, derived?.Hash, scenario.Digest,
            root.GetProperty("runnerVersion").GetString()!, fixes, allowed, sequences.AsReadOnly(), child.AsReadOnly(), hasFailure, []);
    }

    private static bool ValidTickRuns(P28StatefulObservedStep step)
    {
        var expected = new List<(int Entry, int Target, int Exit)>();
        for (var i = 0; i < step.Input.FastTicks; i++) { expected.Add((0x5BD0, 0x1D8, 0x5BD9)); expected.Add((0x5BD0, 0x1D9, 0x5BD9)); }
        for (var i = 0; i < step.Input.SlowTicks; i++) { expected.Add((0x5BD0, 0x1DF, 0x5BD9)); expected.Add((0x3CEB, 0xF3, 0x3CF3)); }
        return step.TickRuns.Count == expected.Count && step.TickRuns.Zip(expected).All(p =>
            p.First[0] == p.Second.Entry && p.First[1] == p.Second.Target && p.First[2] == p.Second.Exit && p.First[3] == 0 && p.First[4] is >= 2 and <= 4);
    }
    internal static IReadOnlyList<P28VtecThresholdSelection> ProjectThresholds(IReadOnlyList<P28VtecGate> gates)
    {
        var result = new List<P28VtecThresholdSelection>();
        for (var pair = 0; pair < 2; pair++)
        {
            var compare = gates.Single(g => g.Pc == (pair == 0 ? 0x125C : 0x1268));
            var prior = gates.Single(g => g.Pc == (pair == 0 ? 0x1257 : 0x1263));
            var context = gates.Single(g => g.Pc == 0x124A);
            if (compare.Outcome is null || prior.Outcome is null || context.Outcome is null) continue;
            var selectedContext = context.Outcome.Value ? 0 : 1;
            result.Add(new(pair, selectedContext, P28ThresholdLogic.ThresholdOffset(selectedContext, pair, prior.Outcome.Value),
                checked((byte)compare.Left!.Value), prior.Outcome.Value, compare.Outcome.Value));
        }
        return result.AsReadOnly();
    }
    internal static IReadOnlyList<P28VtecGate> ProjectGates(IReadOnlyList<int[]> events)
    {
        var seen = new HashSet<int>();
        foreach (var e in events) if (!seen.Add(e[0]) || !P28StatefulModel.GateDefinitions.Any(g => g.Pc == e[0])) throw Protocol("Unknown or repeated decision gate event.");
        return Array.AsReadOnly(P28StatefulModel.GateDefinitions.Select(g =>
        {
            var e = events.SingleOrDefault(e => e[0] == g.Pc);
            if (e is null) return new P28VtecGate(g.Pc, g.Id, null);
            if (g.Length == 0)
            {
                if (e[6] > 255 || e[7] > 255) throw Protocol("Missing actual byte comparison operands.");
                return new P28VtecGate(g.Pc, g.Id, (e[5] & 0x8000) != 0, e[6], e[7]);
            }
            return new P28VtecGate(g.Pc, g.Id, e[1] != g.Pc + g.Length);
        }).ToArray());
    }

    private static P28StatefulObservedStep ParseStep(JsonElement e, IReadOnlyList<string> allowed)
    {
        Shape(e, "index", "status", "input", "stateBefore", "stateAtEntry", "stateAfter", "softwareRequest", "selectionStatus",
            "tickRuns", "tickWrites", "decisionWrites", "gateEvents", "execution", "tickFailure", "cumulativeAssumptions");
        P28StatefulScenario.CallShape(e.GetProperty("input"));
        P28VtecPersistentState State(string name)
        { var item = e.GetProperty(name); P28StatefulScenario.StateShape(item); return item.Deserialize<P28VtecPersistentState>(P28StatefulScenario.Options)!; }
        var cumulative = e.GetProperty("cumulativeAssumptions").Deserialize<string[]>()!;
        if (cumulative.Length > 1 || cumulative.Any(a => !allowed.Contains(a))) throw Protocol("Unknown cumulative assumption.");
        return new(Int(e, "index", 0, 255), Int(e, "status", 0, 4), e.GetProperty("input").Deserialize<P28VtecCall>(P28StatefulScenario.Options)!,
            State("stateBefore"), State("stateAtEntry"), State("stateAfter"), e.GetProperty("softwareRequest").Deserialize<bool?>(), e.GetProperty("selectionStatus").Deserialize<bool?>(),
            Matrix(e, "tickRuns", 5, 128), Matrix(e, "tickWrites", 3, 128), Matrix(e, "decisionWrites", 3, 512), Matrix(e, "gateEvents", 8, 32),
            P28AcquisitionValidator.ParseStage(e.GetProperty("execution"), 512, 0, allowed, P28StatefulModel.SubbOffAssumption),
            P28AcquisitionValidator.ParseStage(e.GetProperty("tickFailure"), 4, 0, [], null), Array.AsReadOnly(cumulative));
    }
    private static IReadOnlyList<int[]> Matrix(JsonElement e, string name, int width, int maximum)
    {
        var a = e.GetProperty(name); if (a.GetArrayLength() > maximum) throw Protocol("Bounded journal exceeded.");
        return Array.AsReadOnly(a.EnumerateArray().Select(row =>
        {
            if (row.GetArrayLength() != width) throw Protocol("Incorrect journal row width.");
            var values = row.EnumerateArray().Select(v => v.GetInt32()).ToArray();
            if (values.Any(v => v is < 0 or > 65536)) throw Protocol("Journal value out of bounds."); return values;
        }).ToArray());
    }
    private static void Shape(JsonElement e, params string[] names)
    {
        if (e.ValueKind != JsonValueKind.Object || !e.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal).SequenceEqual(names.Order(StringComparer.Ordinal)))
            throw Protocol("Missing, duplicate or unknown response fields.");
    }
    private static int Int(JsonElement e, string name, int min, int max)
    { var v = e.GetProperty(name).GetInt32(); if (v < min || v > max) throw Protocol("Response integer out of bounds."); return v; }
    private static bool Equal<T, U>(T a, U b) => JsonNode.DeepEquals(JsonSerializer.SerializeToNode(a, JsonDefaults.Create(false)), JsonSerializer.SerializeToNode(b, JsonDefaults.Create(false)));
    private static SliceProcessException Protocol(string message) => new(SliceProcessFailure.Protocol, message);
    internal static JsonElement EntryContracts() => JsonSerializer.SerializeToElement(new object[] { new {
        id = "statefulVtec", entryPc = 0x122C, exitPc = 0x12FC, stop = "BeforeInstruction", codeRanges = new[] { new[] { 0x122C, 0x12FC }, new[] { 0x5839, 0x586E } },
        psw = 0x0101, lrb = 0x20, usp = 0x280, ssp = 0x7FE, instructionBudget = 512, initialState = "OncePerImageAndScratchSequence",
        callEntryReset = new[] { "PC", "PSW", "LRB", "USP" }, compactCode = "ExplicitRawSoftwareInput", p1Mode = "AllOutputDataRegisterOnlyNoExternalBus",
        physicalRpmAvailable = false, fullBoot = "NotRun", interrupts = "NotInjected", decrementBody = new[] { 0x5BD0, 0x5BD9 }, incrementBody = new[] { 0x3CEB, 0x3CF3 },
        fastTickTargets = new[] { 0x1D8, 0x1D9 }, slowTickTargets = new[] { 0x1DF, 0xF3 }, tickUnits = "ExplicitNativeBodyCallsNotMilliseconds",
        stateAddresses = new[] { 0x131, 0x127, 0x198, 0x1D8, 0x1D9, 0x1DF, 0xF3, 0x22 }, gateEventPcs = P28StatefulModel.GateDefinitions.Select(g => g.Pc).ToArray(),
        traceLimit = 128, allowedAssumptions = new[] { P28StatefulModel.SubbOffAssumption },
    } }, JsonDefaults.Create(false));
}
