using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28PostSelectionCriticalGeneration(int Address, string Provenance, int? Generation, int? WriteOrder, int Value);
public sealed record P28PostSelectionCriticalCheckpoint(int Index, string Disposition, string PrefixDisposition,
    P28PostSelectionCriticalProjection? Expected, int? Word0190, int? Word0192, int? Word0194, int? CommonPathWord,
    IReadOnlyList<P28PostSelectionCriticalGeneration> Generations, P28PostStoreConsumerCheckpoint Prefix, JsonElement Actual);
public sealed record P28PostSelectionCriticalSequence(string Image, int ScratchPattern, IReadOnlyList<P28PostSelectionCriticalCheckpoint> Checkpoints);
public sealed record P28PostSelectionCriticalComparison(int ScratchPattern, int Index, bool? Controls,
    bool? PrefixGateDiverged, bool? HandoffDiverged, bool? CommonDiverged, int? Word0194A, int? Word0194B,
    int? Word0190A, int? Word0190B, int? CommonPathWordA, int? CommonPathWordB, string Effect);
public sealed record P28PostSelectionCriticalReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28PostSelectionCriticalSequence> Sequences, IReadOnlyList<P28PostSelectionCriticalComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        NativeTickInvocations = Sequences.SelectMany(s => s.Checkpoints).Sum(c => c.Prefix.Prefix.Prefix.NativeTicks),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        DynamicZeroBypasses = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        HandoffWitnesses = Comparisons.Count(c => c.HandoffDiverged == true),
        CommonPathWitnesses = Comparisons.Count(c => c.CommonDiverged == true)
    };
    public string Scope => "Native M2q exit2259 -> synchronous shared software IE/PSWH -> X1/A stores019x -> actual unchanged60F8 zero bypass -> current03B4/helper -> ordered03B6/8/A/C stores; stop-before22B1. Earlier entries scripted, not ECU scheduler.";
    public string IeScope => "One word-only software IE storage;2259 mask02A0;226D native write from00F8, not necessarily pre-mask value";
    public string PswhScope => "Bounded coherent PSWH operand RMW:225E clears bit0,2268 sets bit0; other represented bits retained; no physical IRQ/priority claim";
    public string IrqDelivery => "NotInjected";
    public string PendingInterrupt => "NoneInjected / NotModeled";
    public string ElapsedTime => "None";
    public string Configuration60f8 => "OriginalZero;DynamicRead226F/JEQ2273To229FRequiredForStrictMatch";
    public string OptionalPerChannelPath => "2275..229F including227A NotReachableInOriginalScope; synthetic alternate branch is not actual-ROM evidence";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; in-memory one-field B only; no BIN/export/compensation/binding/receipt/token";
}

public static class P28PostSelectionCriticalValidator
{
    public const string Operation = "fuelPostSelectionCriticalChain";
    private static readonly int[] Addresses = [0x190, 0x192, 0x194, 0x3B6, 0x3B8, 0x3BA, 0x3BC];
    public static object CreateRequest(RomImage image, P28PostSelectionCriticalScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28PostStoreConsumerValidator.CreateRequest(image, scenario.PrefixScenario), JsonDefaults.Create());
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = old.GetProperty("images"),
            scratchPatterns = old.GetProperty("scratchPatterns"),
            allowAssumptions = Array.Empty<string>(),
            fuelPostSelectionCriticalChain = old.GetProperty("fuelPostStoreConsumerChain")
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28PostStoreConsumerValidator.ExpectedContracts()[0],
        nativeContinuation = new[] { 0x2259, 0x22B1 }, codeRanges = new[] { new[] { 0x2259, 0x2275 }, new[] { 0x229F, 0x22B1 }, new[] { 0x5991, 0x59A6 } },
        helperRange = new[] { 0x5991, 0x59A6 }, softwareIe = new { address = 0x1A, width = 16, mask = 0x02A0, maskPc = 0x2259, restoreSource = 0xF8, restorePc = 0x226D },
        pswh = new { clear = new[] { 0x225E, 1 }, set = new[] { 0x2268, 1 } },
        nativeStores = new[] { new[] { 0x2261, 0x194, 16 }, new[] { 0x2264, 0x190, 16 }, new[] { 0x2266, 0x192, 16 },
            new[] { 0x22A5, 0x3B6, 16 }, new[] { 0x22A8, 0x3B8, 16 }, new[] { 0x22AB, 0x3BA, 16 }, new[] { 0x22AE, 0x3BC, 16 } },
        configurationRead = new[] { 0x226F, 0x60F8, 8 }, bypass = new[] { 0x2273, 0x229F }, excludedOptionalCode = new[] { 0x2275, 0x229F },
        irqDelivery = "NotInjected", pendingInterrupt = "NoneInjected;NotModeled", elapsedTime = "None",
        initialHistory = "DiagnosticScratchOnce;NoSourceInputs", physicalRpmAvailable = false, assumptions = Array.Empty<string>(), stop = "BeforeInstruction22B1" } });

    public static async Task<P28PostSelectionCriticalReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28PostSelectionCriticalScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation);
        var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28PostSelectionCriticalSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try
            {
                sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B"));
                contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!;
            }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2r native evidence.", e); }
        }
        var comparisons = new List<P28PostSelectionCriticalComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i];
                    var ok = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    var adaptive = scenario.Mutation!.Kind != P28PostStoreMutationKind.FuelCell;
                    var af = a.Prefix.Prefix.Prefix.Continuation?.Fuel; var bf = b.Prefix.Prefix.Prefix.Continuation?.Fuel;
                    bool? controls = !ok ? null : !adaptive || af!.Data0140 == bf!.Data0140 && af.NativeFactor0158 == bf.NativeFactor0158 &&
                        af.Component == bf.Component && af.Correction == bf.Correction && af.Corrected == bf.Corrected && af.Store03b4 == bf.Store03b4 &&
                        a.Prefix.Expected == b.Prefix.Expected && a.Expected == b.Expected && P28LimiterFuelValidator.NumericControlHistory(af.Actual, bf.Actual);
                    bool? gate = !ok ? null : a.Prefix.Prefix.Prefix.GateTaken != b.Prefix.Prefix.Prefix.GateTaken;
                    bool? handoff = !ok ? null : a.Word0194 != b.Word0194 || a.Word0190 != b.Word0190 || a.Word0192 != b.Word0192;
                    bool? common = !ok ? null : a.CommonPathWord != b.CommonPathWord;
                    comparisons.Add(new(sequences[p].ScratchPattern, i, controls, gate, handoff, common, a.Word0194, b.Word0194, a.Word0190, b.Word0190,
                        a.CommonPathWord, b.CommonPathWord, !ok ? "Incomplete" : handoff == true ? "Native019xHandoffWitness" : common == true ? "Current03B4CommonPathWitness;M2qCarrierClobberedBeforeCommon" :
                        gate == true ? "03A2GateOnly;M2rDoesNotReadGateResult" : "EqualOutput;inspect lookup/history/selection/truncation/clamp"));
                }
        IReadOnlyList<int> diff = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, diff, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }

    internal static IReadOnlyList<P28PostSelectionCriticalSequence> Analyze(RomImage image, P28PostSelectionCriticalScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts",
            "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "criticalSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2r contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty("criticalSequences"); Require(seq.GetArrayLength() == 3, "M2r scratch count differs.");
        var own = new P28PostSelectionCriticalOwn?[3, scenario.Calls.Count]; var ieBefore = new ushort[3, scenario.Calls.Count];
        for (var p = 0; p < 3; p++)
        {
            var model = new P28PostSelectionCriticalHistory(image, scenario, new[] { 0, 85, 170 }[p]);
            var currentIe = scenario.InitialState.Adaptive.Ie; var stopped = false;
            var rows = seq[p].GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "Dense M2r rows required.");
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                ieBefore[p, i] = currentIe;
                if (stopped) continue;
                var expected = model.Step(scenario.Calls[i]); own[p, i] = expected;
                var critical = rows[i].GetProperty("critical");
                if (critical.ValueKind == JsonValueKind.Object)
                {
                    var steps = critical.GetProperty("stage").GetProperty("result").GetProperty("steps").GetInt32();
                    Require(steps >= 0 && steps <= expected.Oracle.Machine.Events.Count, "Critical step count exceeds expected path.");
                    currentIe = (ushort)(steps == 0 ? expected.Entry.Ie : expected.Oracle.IeEnds[steps - 1]);
                }
                else currentIe = PrefixIeAfterPartial(image, rows[i].GetProperty("prefix"), currentIe, scenario.InitialState.Adaptive.RestoreIe);
                stopped = rows[i].GetProperty("status").GetInt32() != 0;
            }
        }
        var prefixView = JsonSerializer.SerializeToElement(new
        {
            runnerVersion = root.GetProperty("runnerVersion"),
            upstreamCommit = root.GetProperty("upstreamCommit"),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            consumerSequences = seq.EnumerateArray().Select(s => new
            {
                scratchPattern = s.GetProperty("scratchPattern"),
                checkpoints = s.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("prefix")).ToArray()
            }).ToArray()
        });
        var prefixes = P28PostStoreConsumerValidator.AnalyzeEvidence(image, scenario.PrefixScenario, prefixView, id,
            (p, i) => seq[p].GetProperty("checkpoints")[i].GetProperty("status").GetInt32() != 0, (p, i) => ieBefore[p, i],
            (p, i, before) =>
            {
                P28FuelFactorValidator.ValidateBoundary(before);
                if (i > 0) RequireEventContinuation(seq[p].GetProperty("checkpoints")[i - 1].GetProperty("critical").GetProperty("exit"), before);
            });
        var reports = new List<P28PostSelectionCriticalSequence>();
        for (var p = 0; p < 3; p++)
        {
            P28LimiterScenario.Shape(seq[p], "scratchPattern", "checkpoints"); var pattern = new[] { 0, 85, 170 }[p];
            Require(seq[p].GetProperty("scratchPattern").GetInt32() == pattern, "M2r scratch order differs.");
            var rows = seq[p].GetProperty("checkpoints"); var stopped = false; JsonElement prior = default;
            var generations = new int?[7]; var orders = new int?[7]; var words = Enumerable.Repeat(pattern * 257, 7).ToArray();
            var checkpoints = new List<P28PostSelectionCriticalCheckpoint>();
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "prefix", "stateBefore", "stateAtEntry", "stateAfter", "critical", "words019x", "commonWords03b6");
                Require(row.GetProperty("index").GetInt32() == i, "M2r event index differs."); var status = row.GetProperty("status").GetInt32();
                Require(status is >= 0 and <= 4, "Invalid M2r whole status.");
                var before = row.GetProperty("stateBefore"); var after = row.GetProperty("stateAfter"); StateShape(before); StateShape(after);
                if (prior.ValueKind != JsonValueKind.Undefined) Require(Equal(before, prior), "Shared IE/RAM/native generations reseeded between events.");
                Require(before.GetProperty("ie").GetInt32() == ieBefore[p, i], "Initial/native IE history differs from own synchronous model.");
                Require(StateWords(before).SequenceEqual(words), "019x/common native history overwritten before event.");
                var prefix = prefixes[p].Checkpoints[i]; var critical = row.GetProperty("critical"); var entry = row.GetProperty("stateAtEntry");
                P28PostSelectionCriticalProjection? projection = null;
                if (stopped)
                {
                    Require(status == 4 && prefix.Disposition == "NotRun" && critical.ValueKind == JsonValueKind.Null && entry.ValueKind == JsonValueKind.Null && Equal(before, after), "Terminal M2r executed or rolled back state.");
                }
                else
                {
                    var expected = own[p, i]!;
                    RequireState(before, expected.Before);
                    if (prefix.Disposition == "StrictMatch")
                    {
                        Require(entry.ValueKind == JsonValueKind.Object && critical.ValueKind == JsonValueKind.Object, "Successful M2q lacks actual2259 continuation.");
                        RequireState(entry, expected.Entry); projection = expected.Projection;
                        var prefixExit = row.GetProperty("prefix").GetProperty("consumer").GetProperty("exit");
                        var native = ValidateSuffix(critical, prefixExit, expected.Oracle);
                        Require(status == native.Status, "Whole M2r status contradicts suffix.");
                        var count = native.Steps == 0 ? 0 : expected.Oracle.Machine.AccessEnds[native.Steps - 1]; var order = 0;
                        foreach (var write in expected.Oracle.Machine.Accesses.Take(count).Where(a => a[3] == 1))
                        {
                            var slot = Array.IndexOf(Addresses, write[1]);
                            if (slot < 0) continue; words[slot] = write[4]; generations[slot] = i; orders[slot] = order++;
                        }
                        var retained = expected.Entry with
                        {
                            Ie = (ushort)(native.Steps == 0 ? expected.Entry.Ie : expected.Oracle.IeEnds[native.Steps - 1]),
                            Words019x = words.Take(3).ToArray(),
                            CommonWords03b6 = words.Skip(3).ToArray()
                        };
                        RequireState(after, retained);
                        if (status == 0)
                        {
                            Require(words.SequenceEqual(new[] { projection.Word0190, projection.Word0192, projection.Word0194,
                                projection.CommonPathWord, projection.CommonPathWord, projection.CommonPathWord, projection.CommonPathWord }), "Independent completed software results differ.");
                            Require(row.GetProperty("words019x").EnumerateArray().Select(v => v.GetInt32()).SequenceEqual(words.Take(3)) &&
                                row.GetProperty("commonWords03b6").EnumerateArray().Select(v => v.GetInt32()).SequenceEqual(words.Skip(3)), "Forged completed outputs.");
                        }
                    }
                    else
                    {
                        Require(critical.ValueKind == JsonValueKind.Null && entry.ValueKind == JsonValueKind.Null && status == row.GetProperty("prefix").GetProperty("status").GetInt32(), "M2r ran after incomplete M2q.");
                        Require(StateWords(after).SequenceEqual(words), "Unattempted M2r changed word histories.");
                        RequirePrefixStorage(row.GetProperty("prefix"), after, ieBefore[p, i], image, scenario.InitialState.Adaptive.RestoreIe);
                    }
                }
                if (status != 0) Require(row.GetProperty("words019x").ValueKind == JsonValueKind.Null && row.GetProperty("commonWords03b6").ValueKind == JsonValueKind.Null, "Partial/retained RAM presented as completed result.");
                var disposition = status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                var history = Addresses.Select((address, n) => new P28PostSelectionCriticalGeneration(address,
                    generations[n] == i ? status == 0 ? "Written" : "PartialNativeWritten" : status != 0 ? "NotRun" : generations[n].HasValue ? "Held" : "InitialHistory",
                    generations[n], orders[n], words[n])).ToArray();
                checkpoints.Add(new(i, disposition, prefix.Disposition, projection, status == 0 ? words[0] : null, status == 0 ? words[1] : null,
                    status == 0 ? words[2] : null, status == 0 ? words[3] : null, history, prefix, ReportRow(row, scenario.TraceCallIndexes.Contains(i))));
                prior = after.Clone(); stopped |= status != 0;
            }
            reports.Add(new(id, pattern, checkpoints.AsReadOnly()));
        }
        return reports.AsReadOnly();
    }

    internal static void RequireEventContinuation(JsonElement previousExit, JsonElement firstBefore)
    {
        P28FuelFactorValidator.ValidateBoundary(previousExit); P28FuelFactorValidator.ValidateBoundary(firstBefore);
        Require(previousExit.GetProperty("pc").GetInt32() == 0x22B1 && Equal(previousExit, firstBefore), "CPU reset/reload after native M2r exit.");
    }
    internal static P28AcquisitionStageResult ValidateSuffix(JsonElement suffix, JsonElement prefixExit, P28PostSelectionCriticalOracle own)
    {
        P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses"); var entry = suffix.GetProperty("entry"); var exit = suffix.GetProperty("exit");
        P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        Require(Equal(entry, prefixExit) && entry.GetProperty("pc").GetInt32() == 0x2259 && entry.GetProperty("lrb").GetInt32() == 0x20 &&
            entry.GetProperty("ssp").GetInt32() == 0x7FE && entry.GetProperty("dp").GetInt32() == 0x3B4 && (entry.GetProperty("psw").GetInt32() & 7) == 1, "Fresh2259 entry/reset/wrong native bank or DP.");
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 48, 0, [], null)!;
        Require(result.Status != 0 || result.Error is null, "Completed M2r reports execution error.");
        var machine = own.Machine; var events = Matrix(stage.GetProperty("events"), 8, 48); var accesses = Matrix(suffix.GetProperty("accesses"), 5, 192);
        P28FuelAdditiveEvidence.RequireEventPrefix(stage, machine);
        Require(events.Length == result.Steps && result.Trace.Count == result.Steps && (result.Status != 0 || events.Length == machine.Events.Count), "Missing mandatory M2r instructions.");
        Require(entry.GetProperty("accumulator").GetInt32() == machine.Events[0][2] && entry.GetProperty("psw").GetInt32() == machine.Events[0][4] &&
            entry.GetProperty("x1").GetInt32() == own.X1Ends[0] && Enumerable.Range(0, 4).All(n => Word(entry, n) == machine.RegisterEnds[0][n]), "Independent M2q native carriers differ.");
        P28FuelCalculationValidator.ValidateEventContinuity(events, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(), exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        for (var n = 0; n < events.Length; n++) Require(result.Trace[n].GetProperty("pc").GetInt32() == events[n][0] && result.Trace[n].GetProperty("nextPc").GetInt32() == events[n][1] &&
            result.Trace[n].GetProperty("accumulator").GetInt32() == events[n][3] && result.Trace[n].GetProperty("psw").GetInt32() == events[n][5], "Trace contradicts synchronous IE/PSWH/branch flags.");
        var count = events.Length == 0 ? 0 : machine.AccessEnds[events.Length - 1];
        Require(Equal(accesses, machine.Accesses.Take(count).ToArray()) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(machine.Accesses.Take(count)
            .Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray())), "Wrong IE width/restore/source/native RAM order/stack/pointer provenance.");
        var reads = events.Length == 0 ? 0 : own.ProgramReadEnds[events.Length - 1];
        Require(result.ProgramReads.SequenceEqual(own.ProgramReads.Take(reads)) && result.UsedAssumptions.Count == 0, "Missing/foreign configuration read or assumption.");
        var extents = machine.Events.Take(events.Length).SelectMany((e, n) => Enumerable.Range(e[0], machine.Lengths[n])).Distinct().Order().ToArray();
        Require(result.ExecutedInstructionBytes.SequenceEqual(extents) && result.ExecutedInstructionBytes.All(a => a is < 0x2275 or >= 0x229F) &&
            result.StopPc == (events.Length == 0 ? 0x2259 : events[^1][1]) && exit.GetProperty("pc").GetInt32() == result.StopPc &&
            (result.Status != 0 || result.StopPc == 0x22B1), "Wrong dynamic bypass/optional227A execution/native extent/exit.");
        var regs = events.Length == 0 ? Enumerable.Range(0, 4).Select(n => Word(entry, n)).ToArray() : machine.RegisterEnds[events.Length - 1];
        Require(Enumerable.Range(0, 4).All(n => Word(exit, n) == regs[n]), "M2r helper bank/clobbers forged.");
        foreach (var key in new[] { "lrb", "x2", "dp", "usp" }) Require(Equal(entry.GetProperty(key), exit.GetProperty(key)), "M2r changed retained pointer/bank.");
        var ssp = events.Length == 0 ? 0x7FE : machine.StackEnds[events.Length - 1]; var x1 = events.Length == 0 ? entry.GetProperty("x1").GetInt32() : own.X1Ends[events.Length - 1];
        Require(stage.GetProperty("sspAfter").GetInt32() == ssp && exit.GetProperty("ssp").GetInt32() == ssp && exit.GetProperty("x1").GetInt32() == x1, "Native call/return/X1 lifetime differs.");
        return result;
    }
    private static void StateShape(JsonElement state)
    {
        P28LimiterScenario.Shape(state, "ie", "restoreIe", "words019x", "word03b4", "commonWords03b6", "mode012c", "word0150");
        foreach (var key in new[] { "ie", "restoreIe", "word03b4", "word0150" }) Require(state.GetProperty(key).GetInt32() is >= 0 and <= 65535, "Invalid native software word.");
        Require(state.GetProperty("mode012c").GetInt32() is >= 0 and <= 255 && state.GetProperty("words019x").GetArrayLength() == 3 && state.GetProperty("commonWords03b6").GetArrayLength() == 4 &&
            StateWords(state).All(v => v is >= 0 and <= 65535), "Invalid native word/byte history shape.");
    }
    private static int[] StateWords(JsonElement state) => state.GetProperty("words019x").EnumerateArray().Concat(state.GetProperty("commonWords03b6").EnumerateArray()).Select(v => v.GetInt32()).ToArray();
    private static void RequireState(JsonElement actual, P28PostSelectionCriticalState expected)
    {
        StateShape(actual); Require(Equal(actual, JsonSerializer.SerializeToElement(expected, JsonDefaults.Create())), "Independent IE/shared native word history differs.");
    }
    private static ushort PrefixIeAfterPartial(RomImage image, JsonElement prefix, ushort ie, ushort restore)
    {
        var producer = prefix.GetProperty("prefix").GetProperty("prefix").GetProperty("producer");
        if (producer.ValueKind != JsonValueKind.Object) return ie;
        var events = Matrix(producer.GetProperty("stage").GetProperty("events"), 8, 512);
        // PC alone is not a semantic form: invented partial fixtures may load A at this PC.
        if (image.Span[0x48E1] == 0xB5 && image.Span[0x48E2] == 0x1A && image.Span[0x48E3] == 0xD0 && events.Any(e => e[0] == 0x48E1))
            ie = (ushort)(ie & P28LimiterInspector.Word(image.Span, 0x48E4));
        if (image.Span[0x48F3] == 0xD5 && image.Span[0x48F4] == 0x1A && events.Any(e => e[0] == 0x48F3)) ie = restore;
        return ie;
    }
    private static void RequirePrefixStorage(JsonElement prefix, JsonElement after, ushort ieBefore, RomImage image, ushort restore)
    {
        var adaptive = prefix.GetProperty("prefix").GetProperty("prefix");
        var fuel = adaptive.GetProperty("joint").GetProperty("fuel");
        Require(after.GetProperty("ie").GetInt32() == PrefixIeAfterPartial(image, prefix, ieBefore, restore) && after.GetProperty("restoreIe").GetInt32() == restore &&
            after.GetProperty("word03b4").GetInt32() == fuel.GetProperty("storesAfter")[1].GetInt32() &&
            after.GetProperty("mode012c").GetInt32() == prefix.GetProperty("mode012cAfter").GetInt32() && after.GetProperty("word0150").GetInt32() == prefix.GetProperty("word0150After").GetInt32() &&
            after.GetProperty("ie").GetInt32() == adaptive.GetProperty("stateAfter").GetProperty("ie").GetInt32(), "Partial prefix storage/IE observations contradict native evidence.");
    }
    private static JsonElement ReportRow(JsonElement row, bool trace)
    {
        if (trace) return row.Clone(); var node = JsonNode.Parse(row.GetRawText())!;
        void Strip(JsonNode? value)
        {
            if (value is JsonObject o) foreach (var item in o.ToArray()) { if (item.Key == "trace") o[item.Key] = new JsonArray(); else Strip(item.Value); }
            else if (value is JsonArray a) foreach (var child in a) Strip(child);
        }
        Strip(node); return JsonSerializer.SerializeToElement(node);
    }
}
