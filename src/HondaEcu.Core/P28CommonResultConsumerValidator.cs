using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28CommonResultQuartetGeneration(int EventIndex, int WriterPc, int Address, int Width, int Value, string Provenance, int? Generation, int? WriteOrder);
public sealed record P28CommonResultConsumerCheckpoint(int Index, string Disposition, string PrefixDisposition, int? SoftwareResult13b,
    int Retained013b, int Retained013d, int Mode012b, IReadOnlyList<P28CommonResultQuartetGeneration> QuartetGenerations,
    P28PostSelectionCriticalCheckpoint Prefix, JsonElement Actual);
public sealed record P28CommonResultConsumerSequence(string Image, int ScratchPattern, IReadOnlyList<P28CommonResultConsumerCheckpoint> Checkpoints);
public sealed record P28CommonResultConsumerComparison(int ScratchPattern, int Index, bool? Controls, bool? CommonDiverged,
    int? CommonWordA, int? CommonWordB, int? SoftwareResult13bA, int? SoftwareResult13bB, string Effect);
public sealed record P28CommonResultConsumerReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28CommonResultConsumerSequence> Sequences, IReadOnlyList<P28CommonResultConsumerComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        CompletedM2rPrefixes = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.PrefixDisposition == "StrictMatch"),
        NativeTickInvocations = Sequences.SelectMany(s => s.Checkpoints).Sum(c => c.Prefix.Prefix.Prefix.Prefix.NativeTicks),
        NewReaderInvocations = 0,
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        AbComparisons = Comparisons.Count,
        NativeCommonWitnesses = Comparisons.Count(c => c.CommonDiverged == true),
        NativeQuartetConsumerWitnesses = 0
    };
    public string OverallStage => "Partial;PartA bounded software prefix,PartB static quartet-consumer audit only";
    public string Scope => "Same-machine completed M2r22B1 -> bounded local013B/013D software work ->stop-before236C. DIV0 unresolved2333; primary JGT ambiguity unresolved233A. No quartet read and no recovered scheduler connection.";
    public string QuartetConsumer => "05DF/1550 StaticOnly/NotRun; no ScriptedConsumerEntry; no native quartet reader loop";
    public string FirstExternalBoundary => "2394 LB[DP=0F00] StaticOnly/NotReached;236C is a local software-subsystem boundary,not a peripheral boundary";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string TimerIrqP2 => "NotRun; no IRQ injection or elapsed-time simulation";
    public string FirmwareOutput => "None; in-memory closed one-field B only; no BIN/export/compensation/binding/receipt/token";
}

public static class P28CommonResultConsumerValidator
{
    public const string Operation = "fuelCommonResultConsumerChain";
    public static object CreateRequest(RomImage image, P28CommonResultConsumerScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28PostSelectionCriticalValidator.CreateRequest(image, scenario.PrefixScenario), JsonDefaults.Create());
        var stimulus = old.GetProperty("fuelPostSelectionCriticalChain");
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = old.GetProperty("images"),
            scratchPatterns = old.GetProperty("scratchPatterns"),
            allowAssumptions = Array.Empty<string>(),
            fuelCommonResultConsumerChain = new
            {
                formatVersion = 1,
                initialState = new { prefix = stimulus.GetProperty("initialState"), scenario.InitialState.SoftwareSources },
                scenario.Calls,
                scenario.TraceCallIndexes
            }
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28PostSelectionCriticalValidator.ExpectedContracts()[0],
        nativeContinuation = new[] { 0x22B1, 0x236C }, codeRanges = new[] { new[] { 0x22B1, 0x233C }, new[] { 0x2369, 0x236C }, new[] { 0x5991, 0x59A6 } },
        instructionBudget = 192, programDataRange = new[] { 0x6106, 0x610C }, sourcePolicy = "OnceInitialSoftwareSnapshot;NoEventOrBoundaryReseed",
        sourceMasks = new[] { new[] { 0x11A, 0x1034 }, new[] { 0x11F, 32 }, new[] { 0x120, 1 }, new[] { 0xB7, 1 } },
        sourceWords = new[] { 0x136 }, sourceBytes = new[] { 0xBE }, initialHistoryBytes = new[] { 0x13B, 0x13D },
        nativeOutput = new[] { 0x236A, 0x13B, 8 }, nativeCounterWriter = new[] { 0x2321, 0x13D, 8 },
        quartetWriters = new[] { new[] { 0x22A5, 0x3B6, 16 }, new[] { 0x22A8, 0x3B8, 16 }, new[] { 0x22AB, 0x3BA, 16 }, new[] { 0x22AE, 0x3BC, 16 } },
        dynamicQuartetReaders = Array.Empty<int>(), scriptedConsumerEntry = "NotEstablished;NotRun", overallConsumerChain = "Partial;StaticConsumersNotRun",
        unresolvedBoundaries = new object[][] { [0x2333, "ZeroDivisorUndefined"], [0x233A, "PrimaryJgtConditionConflict"] },
        laterStaticBoundaries = new object[][] { [0x2394, "Unknown0F00"], [0x239E, "P1AccessNotRun"], [0x06A5, "IRQDependentRtiNotRun"] },
        irqDelivery = "NotInjected", pendingInterrupt = "NoneInjected;NotModeled", elapsedTime = "None", p2 = "NotRun",
        physicalRpmAvailable = false, assumptions = Array.Empty<string>(), stop = "BeforeInstruction236C" } });

    public static async Task<P28CommonResultConsumerReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28CommonResultConsumerScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation);
        var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28CommonResultConsumerSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try
            {
                sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B"));
                contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!;
            }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2s native evidence.", e); }
        }
        var comparisons = new List<P28CommonResultConsumerComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i];
                    var ok = a.PrefixDisposition == "StrictMatch" && b.PrefixDisposition == "StrictMatch";
                    var adaptive = scenario.Mutation!.Kind != P28PostStoreMutationKind.FuelCell;
                    var af = a.Prefix.Prefix.Prefix.Prefix.Continuation?.Fuel; var bf = b.Prefix.Prefix.Prefix.Prefix.Continuation?.Fuel;
                    bool? controls = !ok ? null : !adaptive || af!.Data0140 == bf!.Data0140 && af.NativeFactor0158 == bf.NativeFactor0158 &&
                        af.Component == bf.Component && af.Correction == bf.Correction && af.Corrected == bf.Corrected && af.Store03b4 == bf.Store03b4 &&
                        a.Prefix.Expected == b.Prefix.Expected && P28LimiterFuelValidator.NumericControlHistory(af.Actual, bf.Actual);
                    bool? common = !ok ? null : a.Prefix.CommonPathWord != b.Prefix.CommonPathWord;
                    comparisons.Add(new(sequences[p].ScratchPattern, i, controls, common, a.Prefix.CommonPathWord, b.Prefix.CommonPathWord,
                        a.SoftwareResult13b, b.SoftwareResult13b, !ok ? "IncompleteM2rPrefix" : "NoQuartetReaderInContinuousPrefix;ConsumerChainNotRun"));
                }
        IReadOnlyList<int> diff = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, diff, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }

    internal static IReadOnlyList<P28CommonResultConsumerSequence> Analyze(RomImage image, P28CommonResultConsumerScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "commonResultSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2s contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty("commonResultSequences"); Require(seq.GetArrayLength() == 3, "M2s scratch count differs.");
        var owns = new P28CommonResultConsumerOwn?[3, scenario.Calls.Count]; var modesBefore = new byte[3, scenario.Calls.Count];
        for (var p = 0; p < 3; p++)
        {
            var model = new P28CommonResultConsumerHistory(image, scenario, new[] { 0, 85, 170 }[p]); var mode = scenario.InitialState.Prefix.Adaptive.Joint.Data012b; var stopped = false;
            var rows = seq[p].GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "Dense M2s rows required.");
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                modesBefore[p, i] = mode; if (stopped) continue;
                var expected = model.Step(scenario.Calls[i]); owns[p, i] = expected;
                var suffix = rows[i].GetProperty("commonConsumer");
                if (suffix.ValueKind == JsonValueKind.Object)
                {
                    var steps = suffix.GetProperty("stage").GetProperty("result").GetProperty("steps").GetInt32();
                    Require(steps >= 0 && steps <= expected.Oracle.Machine.Events.Count, "Suffix step count exceeds independent software path.");
                    mode = (byte)(steps == 0 ? expected.Entry.Mode012b : expected.Oracle.ModeEnds[steps - 1]);
                }
                else mode = PrefixModeAfterPartial(rows[i].GetProperty("prefix"), mode, scenario.Calls[i]);
                stopped = rows[i].GetProperty("status").GetInt32() != 0;
            }
        }
        var prefixView = JsonSerializer.SerializeToElement(new
        {
            runnerVersion = root.GetProperty("runnerVersion"),
            upstreamCommit = root.GetProperty("upstreamCommit"),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            criticalSequences = seq.EnumerateArray().Select(s => new { scratchPattern = s.GetProperty("scratchPattern"), checkpoints = s.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("prefix")).ToArray() }).ToArray()
        });
        var prefixes = P28PostSelectionCriticalValidator.AnalyzeEvidence(image, scenario.PrefixScenario, prefixView, id,
            (p, i) => seq[p].GetProperty("checkpoints")[i].GetProperty("status").GetInt32() != 0, (p, i) => modesBefore[p, i],
            (byte)(scenario.InitialState.SoftwareSources.Word011aMask1034 >> 8), (p, i, before) =>
            {
                P28FuelFactorValidator.ValidateBoundary(before);
                if (i > 0) RequireEventContinuation(seq[p].GetProperty("checkpoints")[i - 1].GetProperty("commonConsumer").GetProperty("exit"), before);
            });
        var results = new List<P28CommonResultConsumerSequence>();
        for (var p = 0; p < 3; p++)
        {
            P28LimiterScenario.Shape(seq[p], "scratchPattern", "checkpoints"); var pattern = new[] { 0, 85, 170 }[p]; Require(seq[p].GetProperty("scratchPattern").GetInt32() == pattern, "M2s scratch order differs.");
            var rows = seq[p].GetProperty("checkpoints"); var stopped = false; JsonElement prior = default; var list = new List<P28CommonResultConsumerCheckpoint>();
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "prefix", "stateBefore", "stateAtEntry", "stateAfter", "commonConsumer", "softwareResult13b");
                var status = row.GetProperty("status").GetInt32(); Require(row.GetProperty("index").GetInt32() == i && status is >= 0 and <= 4, "M2s index/status differs.");
                var before = row.GetProperty("stateBefore"); var after = row.GetProperty("stateAfter"); StateShape(before); StateShape(after);
                if (prior.ValueKind != JsonValueKind.Undefined) Require(Equal(before, prior), "Outer native history/source/quartet reseeded between events.");
                Require(before.GetProperty("mode012b").GetByte() == modesBefore[p, i], "Independent012B before history differs.");
                var prefixRow = row.GetProperty("prefix"); var prefix = prefixes[p].Checkpoints[i]; var suffix = row.GetProperty("commonConsumer"); var entry = row.GetProperty("stateAtEntry");
                Require(Equal(before.GetProperty("prefix"), prefixRow.GetProperty("stateBefore")) && Equal(after.GetProperty("prefix"), prefixRow.GetProperty("stateAfter")), "Same quartet/019x/IE/mode/03B4 history split or host overwritten by suffix.");
                if (stopped)
                {
                    Require(status == 4 && prefix.Disposition == "NotRun" && suffix.ValueKind == JsonValueKind.Null && entry.ValueKind == JsonValueKind.Null && Equal(before, after), "Terminal M2s ran inputs/ticks/suffix or rolled back RAM.");
                }
                else
                {
                    var expected = owns[p, i]!; RequireStateSources(before, expected.Before);
                    if (prefix.Disposition == "StrictMatch")
                    {
                        Require(entry.ValueKind == JsonValueKind.Object && suffix.ValueKind == JsonValueKind.Object, "Completed M2r lacks literal22B1 native continuation.");
                        RequireState(entry, expected.Entry);
                        var native = ValidateSuffix(suffix, prefixRow.GetProperty("critical").GetProperty("exit"), expected.Oracle);
                        Require(status == native.Status, "Whole M2s status contradicts native suffix.");
                        var retained = expected.Entry with
                        {
                            Mode012b = (byte)(native.Steps == 0 ? expected.Entry.Mode012b : expected.Oracle.ModeEnds[native.Steps - 1]),
                            Byte013b = (byte)(native.Steps == 0 ? expected.Entry.Byte013b : expected.Oracle.HistoryEnds[native.Steps - 1][0]),
                            Byte013d = (byte)(native.Steps == 0 ? expected.Entry.Byte013d : expected.Oracle.HistoryEnds[native.Steps - 1][1])
                        };
                        RequireState(after, retained);
                        if (status == 0) Require(row.GetProperty("softwareResult13b").GetByte() == retained.Byte013b && expected.Oracle.Machine.Accesses.Any(a => a[0] == 0x236A && a[1] == 0x13B && a[2] == 8 && a[3] == 1), "Retained013B is not fresh native output236A.");
                    }
                    else
                    {
                        Require(suffix.ValueKind == JsonValueKind.Null && entry.ValueKind == JsonValueKind.Null && status == prefixRow.GetProperty("status").GetInt32(), "M2s ran after incomplete M2r.");
                        var retained = expected.Before with
                        {
                            Mode012b = PrefixModeAfterPartial(prefixRow, expected.Before.Mode012b, scenario.Calls[i]),
                            Word011a = (ushort)((expected.Before.Word011a & ~0x8000) | (scenario.Calls[i].Adaptive.FixedSource ? 0x8000 : 0))
                        };
                        RequireStateSources(after, retained);
                    }
                }
                if (status != 0) Require(row.GetProperty("softwareResult13b").ValueKind == JsonValueKind.Null, "Partial/retained013B presented as completed fresh output.");
                var generations = prefix.Generations.Where(g => g.Address >= 0x3B6).Select((g, slot) => new P28CommonResultQuartetGeneration(i, 0x22A5 + slot * 3, g.Address, 16, g.Value,
                    g.Generation == i ? prefix.Disposition == "StrictMatch" ? "NativeWritten" : "PartialNativeWritten" : g.Generation.HasValue ? "RetainedNativeGeneration" : "InitialDiagnosticCanary", g.Generation, g.WriteOrder)).ToArray();
                Require(generations.Length == 4 && generations.Select(g => g.Address).SequenceEqual(new[] { 0x3B6, 0x3B8, 0x3BA, 0x3BC }), "Four separate quartet generations required even when values equal.");
                var disposition = status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                list.Add(new(i, disposition, prefix.Disposition, status == 0 ? after.GetProperty("byte013b").GetByte() : null,
                    after.GetProperty("byte013b").GetByte(), after.GetProperty("byte013d").GetByte(), after.GetProperty("mode012b").GetByte(), generations, prefix, ReportRow(row, scenario.TraceCallIndexes.Contains(i))));
                prior = after.Clone(); stopped |= status != 0;
            }
            results.Add(new(id, pattern, list.AsReadOnly()));
        }
        return results.AsReadOnly();
    }

    internal static void RequireEventContinuation(JsonElement previousExit, JsonElement firstBefore)
    {
        P28FuelFactorValidator.ValidateBoundary(previousExit); P28FuelFactorValidator.ValidateBoundary(firstBefore);
        Require(previousExit.GetProperty("pc").GetInt32() == 0x236C && Equal(previousExit, firstBefore), "CPU reset/reload/fake scheduler jump after M2s exit.");
    }
    internal static P28AcquisitionStageResult ValidateSuffix(JsonElement suffix, JsonElement prefixExit, P28CommonResultConsumerOracle own)
    {
        P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses"); var entry = suffix.GetProperty("entry"); var exit = suffix.GetProperty("exit");
        P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        Require(Equal(entry, prefixExit) && entry.GetProperty("pc").GetInt32() == 0x22B1 && entry.GetProperty("lrb").GetInt32() == 0x20 && entry.GetProperty("ssp").GetInt32() == 0x7FE && entry.GetProperty("dp").GetInt32() == 0x3B4 && entry.GetProperty("x1").GetInt32() == 0, "Fresh22B1 entry/host reload/wrong bank or pointer.");
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 192, 0, [], null)!;
        Require(result.Status != 0 || result.Error is null, "Completed software suffix carries an error.");
        var machine = own.Machine; var events = Matrix(stage.GetProperty("events"), 8, 192); var accesses = Matrix(suffix.GetProperty("accesses"), 5, 768);
        P28FuelAdditiveEvidence.RequireEventPrefix(stage, machine);
        Require(events.Length == result.Steps && result.Trace.Count == result.Steps && (result.Status != 0 || own.Status == 0 && events.Length == machine.Events.Count), "Missing software work or unresolved JGT promoted to completed path.");
        Require(entry.GetProperty("accumulator").GetInt32() == machine.Events[0][2] && entry.GetProperty("psw").GetInt32() == machine.Events[0][4], "Independent native M2r carrier differs.");
        Require(Enumerable.Range(0, 4).All(n => Word(entry, n) == machine.RegisterEnds[0][n]), "Independent entry register bank was reloaded.");
        P28FuelCalculationValidator.ValidateEventContinuity(events, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(), exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        for (var n = 0; n < events.Length; n++) Require(result.Trace[n].GetProperty("pc").GetInt32() == events[n][0] && result.Trace[n].GetProperty("nextPc").GetInt32() == events[n][1] &&
            result.Trace[n].GetProperty("accumulator").GetInt32() == events[n][3] && result.Trace[n].GetProperty("psw").GetInt32() == events[n][5], "Trace contradicts own byte/word flags/control flow.");
        var count = events.Length == 0 ? 0 : machine.AccessEnds[events.Length - 1];
        Require(Equal(accesses, machine.Accesses.Take(count).ToArray()) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(machine.Accesses.Take(count).Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray())), "Wrong source/direction/width/native index/order or hidden host write.");
        Require(accesses.All(a => a[1] is < 0x3B6 or >= 0x3BE), "Invented quartet read/write connection.");
        var readCount = events.Length == 0 ? 0 : own.ProgramReadEnds[events.Length - 1];
        Require(result.ProgramReads.SequenceEqual(own.ProgramReads.Take(readCount)) && result.UsedAssumptions.Count == 0, "Wrong table index or assumption.");
        var extents = machine.Events.Take(events.Length).SelectMany((e, n) => Enumerable.Range(e[0], machine.Lengths[n])).Distinct().Order().ToArray();
        Require(result.ExecutedInstructionBytes.SequenceEqual(extents) && result.StopPc == (events.Length == 0 ? 0x22B1 : events[^1][1]) && exit.GetProperty("pc").GetInt32() == result.StopPc &&
            (result.Status != 0 || result.StopPc == 0x236C), "Wrong software extent/exit/fake scheduler jump.");
        if (events.Length == machine.Events.Count) Require(result.Status == own.Status && result.StopPc == own.StopPc, "Mandatory strict JGT/DIV precondition stop differs.");
        var registers = events.Length == 0 ? Enumerable.Range(0, 4).Select(n => Word(entry, n)).ToArray() : machine.RegisterEnds[events.Length - 1];
        Require(Enumerable.Range(0, 4).All(n => Word(exit, n) == registers[n]), "Wrong retained/clobbered native register bank.");
        foreach (var key in new[] { "lrb", "x1", "x2", "usp" }) Require(Equal(entry.GetProperty(key), exit.GetProperty(key)), "Native pointer/bank changed without instruction.");
        var ssp = events.Length == 0 ? 0x7FE : machine.StackEnds[events.Length - 1]; var dp = events.Length == 0 ? 0x3B4 : own.DpEnds[events.Length - 1];
        Require(stage.GetProperty("sspAfter").GetInt32() == ssp && exit.GetProperty("ssp").GetInt32() == ssp && exit.GetProperty("dp").GetInt32() == dp, "Native DP scale/call/return lifetime differs.");
        return result;
    }
    private static byte PrefixModeAfterPartial(JsonElement r, byte before, P28PostStoreCall call)
    {
        var joint = r.GetProperty("prefix").GetProperty("prefix").GetProperty("prefix").GetProperty("joint"); var mode = before;
        // Select only a independently validated native journal prefix. Observed numeric values are never operands.
        if (joint.GetProperty("decisionAccesses").EnumerateArray().Any(a => a[0].GetInt32() == 0x1A2C && a[1].GetInt32() == 0x12B && a[3].GetInt32() == 1)) mode &= 127;
        if (joint.GetProperty("fuel").GetProperty("accesses").EnumerateArray().Any(a => a[0].GetInt32() == 0x219D && a[1].GetInt32() == 0x12B && a[3].GetInt32() == 1)) mode = (byte)((mode & ~8) | (call.Adaptive.Fuel.Sources.Counter00f2 < 4 ? 8 : 0));
        return mode;
    }
    private static void StateShape(JsonElement state)
    {
        P28LimiterScenario.Shape(state, "prefix", "mode012b", "word011a", "byte011f", "byte0120", "byte00be", "byte00b7", "word0136", "byte013b", "byte013d");
        foreach (var key in new[] { "word011a", "word0136" }) Require(state.GetProperty(key).GetInt32() is >= 0 and <= 65535, "Invalid software word.");
        foreach (var key in new[] { "mode012b", "byte011f", "byte0120", "byte00be", "byte00b7", "byte013b", "byte013d" }) Require(state.GetProperty(key).GetInt32() is >= 0 and <= 255, "Invalid software byte.");
    }
    private static void RequireState(JsonElement actual, P28CommonResultConsumerState expected)
    { StateShape(actual); Require(Equal(actual, JsonSerializer.SerializeToElement(expected, JsonDefaults.Create())), "Independent shared software state differs."); }
    private static void RequireStateSources(JsonElement actual, P28CommonResultConsumerState expected)
    {
        StateShape(actual); var own = JsonSerializer.SerializeToElement(expected, JsonDefaults.Create());
        foreach (var key in new[] { "mode012b", "word011a", "byte011f", "byte0120", "byte00be", "byte00b7", "word0136", "byte013b", "byte013d" }) Require(Equal(actual.GetProperty(key), own.GetProperty(key)), "Native/source history reseed or masked-neighbor overwrite.");
    }
    private static JsonElement ReportRow(JsonElement row, bool trace)
    {
        if (trace) return row.Clone(); var node = JsonNode.Parse(row.GetRawText())!;
        void Strip(JsonNode? value) { if (value is JsonObject o) foreach (var item in o.ToArray()) { if (item.Key == "trace") o[item.Key] = new JsonArray(); else Strip(item.Value); } else if (value is JsonArray a) foreach (var child in a) Strip(child); }
        Strip(node); return JsonSerializer.SerializeToElement(node);
    }
}
