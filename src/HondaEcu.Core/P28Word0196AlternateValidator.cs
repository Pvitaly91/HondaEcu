using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28Word0196SoftwareWrite(int Address, int Width, int WriterPc, int OldValue, int NewValue,
    P28QuartetGeneration Generation, string BranchProvenance);
public sealed record P28Word0196AlternateCheckpoint(int Index, string Disposition, string Provenance, P28QuartetHandoffCheckpoint Prefix,
    P28QuartetGeneration? ProducerGeneration0196, P28QuartetGeneration? ReaderGeneration0196, P28QuartetGeneration? CompareGeneration0196,
    int? CmpLeft, int? CmpRightImmediate, bool? CmpCf, bool? CmpZf, string CompareDomain, int? BranchPc, bool? BranchTaken,
    int? BranchTarget, IReadOnlyList<P28Word0196SoftwareWrite> SoftwareWrites, int StopPc, JsonElement Actual);
public sealed record P28Word0196AlternateSequence(string Image, int ScratchPattern, IReadOnlyList<P28Word0196AlternateCheckpoint> Checkpoints);
public sealed record P28Word0196AlternateComparison(int ScratchPattern, int Index, int? ValueA, int? ValueB, bool? Diverged, string Effect);
public sealed record P28Word0196AlternateReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28Word0196AlternateSequence> Sequences,
    IReadOnlyList<P28Word0196AlternateComparison> Comparisons, JsonElement EntryContract)
{
    private IEnumerable<P28Word0196AlternateCheckpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    public bool HasFailure => Rows.Any(c => c.Disposition is not ("QuartetDerived0196AlternateStrict" or "GateBypass0196AlternateStrict"));
    public string Word0196AlternateSoftwareChain => !HasFailure && Rows.Any(c => c.Disposition == "QuartetDerived0196AlternateStrict") ? "Validated" : "Partial";
    public string Cmp5578 => !HasFailure && Rows.Any(c => c.CompareGeneration0196 is not null) ? "Validated" : "Partial";
    public object Summary => new
    {
        Events = Rows.Count(),
        Native0196Writes = Rows.Count(c => c.ProducerGeneration0196 is not null),
        SameGeneration54faReads = Rows.Count(c => c.ReaderGeneration0196 is not null),
        SameGeneration5578Reads = Rows.Count(c => c.CompareGeneration0196 is not null),
        QuartetDerivedHandoffs = Rows.Count(c => c.Disposition == "QuartetDerived0196AlternateStrict"),
        GateBypassHandoffs = Rows.Count(c => c.Disposition == "GateBypass0196AlternateStrict"),
        BelowImmediate = Rows.Count(c => c.CompareDomain == "BelowImmediate"),
        EqualImmediate = Rows.Count(c => c.CompareDomain == "EqualImmediate"),
        AboveImmediate = Rows.Count(c => c.CompareDomain == "AboveImmediate"),
        BranchTaken = Rows.Count(c => c.BranchTaken == true),
        BranchNotTaken = Rows.Count(c => c.BranchTaken == false),
        SoftwareBoundaryCompletions = Rows.Count(c => c.Disposition.EndsWith("AlternateStrict", StringComparison.Ordinal)),
        StopBefore5596 = Rows.Count(c => c.Disposition.EndsWith("AlternateStrict", StringComparison.Ordinal) && c.StopPc == 0x5596),
        StopBefore55c5 = Rows.Count(c => c.Disposition.EndsWith("AlternateStrict", StringComparison.Ordinal) && c.StopPc == 0x55C5),
        SoftwareWrites = Rows.Sum(c => c.SoftwareWrites.Count),
        PerSlotHandoffs = Enumerable.Range(0, 4).ToDictionary(i => $"slot{i}", i => Rows.Count(c => c.Disposition == "QuartetDerived0196AlternateStrict" && c.Prefix.SelectedSlot == i)),
        AbWitnesses = Comparisons.Count(c => c.Diverged == true),
        CompareBoundaryCrossings = Comparisons.Count(c => c.Effect == "CompareBoundaryCrossing"),
        Dispositions = Rows.GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        TimerExecutions = 0,
        P2Executions = 0
    };
    public string InterStageScheduleTo54F5 => "ExplicitHarnessSchedule";
    public string SoftwareAlternate5501To556F => "NativeContinuousControlFlow";
    public string TimerContinuation => "NotRun";
    public string P2 => "NotRun";
    public string PhysicalOutput => "NotRun";
    public string GateFalseAlternate => "StaticOnly/NotRun;stop-before5533";
    public string OtherConsumer157E => "StaticOther0196Consumer/NotRun";
    public string Recovered0196Scheduler => "NotEstablished";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string Physical0196Role => "Unknown";
    public string Immediate00C0 => "CodeOwnedConstant;NotCalibration;NoRAMSource";
    public string M2yWord0196ScheduledHandoff => "Validated;unchanged";
    public string M2xQuartetScheduledHandoff => "Validated;unchanged";
    public string M2wTechnicalScheduledHandoff => "Validated;unchanged";
    public string M2tJgt => "Blocked/Unresolved";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public int FirmwareBin => 0;
}
public static class P28Word0196AlternateValidator
{
    public const string Operation = "word0196SoftwareAlternateChain";
    public static object CreateRequest(RomImage image, P28Word0196AlternateScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28QuartetHandoffValidator.CreateRequest(image, scenario.PrefixScenario), JsonDefaults.Create());
        var wire = old.GetProperty("quartetConsumerHandoff");
        return new { protocolVersion = 1, operation = Operation, images = old.GetProperty("images"), scratchPatterns = new[] { 0, 85, 170 }, allowAssumptions = Array.Empty<string>(), word0196SoftwareAlternateChain = new { formatVersion = 1, initialState = new { quartetPrefix = wire.GetProperty("initialState"), scenario.InitialState.Bit0128_2, scenario.InitialState.Byte0117 }, calls = wire.GetProperty("calls"), scenario.TraceEventIndexes } };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28Word0196HandoffValidator.ExpectedContracts()[0],
        entryPc = 0x54F5, alternateEntry = "ActualJNE5501Taken;NoHostPC556F", suffixRanges = new[] { new[] { 0x556F, 0x5596 }, new[] { 0x55BF, 0x55C5 } }, suffixBudget = 18,
        stopBefore = new[] { 0x5596, 0x55C5 }, excludedStops = new[] { 0x5503, 0x5533 }, secondReader = new[] { 0x5578, 0x196, 16 }, rightOperand = "Immediate00C0;CodeOwnedConstant",
        compareFlags = "CF=unsignedBorrow;ZF=equality;HC/DDretained", branch = new[] { 0x557D, 0x55BF, 0x557F }, branchPredicate = "CF1;Producer5578;NoInterveningFlagWriter",
        initial018E018F = "AutomaticScratchInitialHistory;NativePersistentOwnership;NoExternalSource", native0117 = "5582And/55C1Store;RetainedNextEvent",
        interStageScheduleTo54F5 = "ExplicitHarnessSchedule", softwareAlternate5501To556F = "NativeContinuousControlFlow", machine = "OneCpuOneBusPerSequence;NoSerializationHandoff",
        timerContinuation = "NotRun", p2 = "NotRun", partial = "Terminal;RetainPriorNativeWrites;LaterNotRun;NoSourceApplication",
        recovered0196Scheduler = "NotEstablished", irqDelivery = "NotInjected", elapsedTime = "None", physical0196Role = "Unknown" } });
    public static async Task<P28Word0196AlternateReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28Word0196AlternateScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28Word0196AlternateSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2z current-generation software alternate evidence.", e); }
        }
        var comparisons = new List<P28Word0196AlternateComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var complete = a.Disposition == "QuartetDerived0196AlternateStrict" && b.Disposition == "QuartetDerived0196AlternateStrict";
                    bool? changed = complete ? a.CmpLeft != b.CmpLeft : null;
                    comparisons.Add(new(sequences[p].ScratchPattern, i, a.CmpLeft, b.CmpLeft, changed, !complete ? "IncompleteOrUpstreamGateBypass" : a.CompareDomain != b.CompareDomain ? "CompareBoundaryCrossing" : changed == true ? "ValueDivergenceSameBranch" : "EqualValue;GenerationIdentityStillRequired"));
                }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, offsets, sequences, comparisons, contract);
    }
    internal static IReadOnlyList<P28Word0196AlternateSequence> Analyze(RomImage image, P28Word0196AlternateScenario scenario, JsonElement root, string id, P28P2LatchValidation? p2 = null, P28PostP2ControlValidation? control = null)
    {
        var key = control is not null ? "postP2ControlSequences" : p2 is null ? "word0196AlternateSequences" : "p2LatchSequences";
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", key);
        _ = SliceRunnerIdentity.Validate(root, control is not null ? P28PostP2ControlValidator.Operation : p2 is null ? Operation : P28P2LatchValidator.Operation); Require(Equal(root.GetProperty("entryContracts"), control is not null ? P28PostP2ControlValidator.ExpectedContracts() : p2 is null ? ExpectedContracts() : P28P2LatchValidator.ExpectedContracts()), "Software/latch/control contract differs.");
        foreach (var k in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(k).GetArrayLength() == 0, "Foreign rows."); Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty(key); Require(seq.GetArrayLength() == 3, "Three scratch histories required.");
        JsonElement Row(int p, int i) => seq[p].GetProperty("checkpoints")[i];
        bool Terminal(int p, int i) => control is not null ? Row(p, i).GetProperty("disposition").GetString() is not ("PostP2ControlStrict" or "PostP2ControlGateBypass") : p2 is null ? Row(p, i).GetProperty("disposition").GetString() is not ("QuartetDerived0196AlternateStrict" or "GateBypass0196AlternateStrict") : Row(p, i).GetProperty("disposition").GetString() is not ("QuartetDerivedP2LatchStrict" or "GateBypassP2LatchControl");
        var reports = Enumerable.Range(0, 3).Select(_ => new List<P28Word0196AlternateCheckpoint>()).ToArray();
        var owned = new Dictionary<int, int>[3]; var ownPsw = new int[3]; var ram = new Dictionary<int, int>[3];
        for (var p = 0; p < 3; p++) { var pattern = new[] { 0, 85, 170 }[p]; ram[p] = new() { [0x128] = (pattern & ~4) | (scenario.InitialState.Bit0128_2 ? 4 : 0), [0x117] = scenario.InitialState.Byte0117, [0x18E] = pattern, [0x18F] = pattern, [0x12A] = (pattern & ~2) | (scenario.InitialState.QuartetPrefix.Bit012a1 ? 2 : 0), [0x124] = scenario.InitialState.QuartetPrefix.FuelPrefix.Adaptive.Joint.Data0124, [0x108] = pattern, [0x109] = pattern }; }
        JsonElement State(Dictionary<int, int> h) => JsonSerializer.SerializeToElement(new { byte0128 = h[0x128], byte0117 = h[0x117], byte018e = h[0x18E], byte018f = h[0x18F], byte012a = h[0x12A], byte0124 = h[0x124] });
        // Validation projection only; no Rust observation is copied into an execution machine.
        var view = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = P28QuartetHandoffValidator.Operation,
            runnerVersion = root.GetProperty("runnerVersion"),
            upstreamCommit = root.GetProperty("upstreamCommit"),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            entryContracts = P28QuartetHandoffValidator.ExpectedContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            quartetHandoffSequences = seq.EnumerateArray().Select(s => new { scratchPattern = s.GetProperty("scratchPattern"), machineInstances = s.GetProperty("machineInstances"), checkpoints = s.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("prefix")).ToArray() }).ToArray()
        });
        _ = P28QuartetHandoffValidator.Analyze(image, scenario.PrefixScenario, view, id, new((p, i) => Row(p, i).GetProperty("after"), Terminal, (p, i, prefix, registers) =>
        {
            var pattern = new[] { 0, 85, 170 }[p]; var s = seq[p]; P28LimiterScenario.Shape(s, "scratchPattern", "machineInstances", "checkpoints");
            Require(N(s, "scratchPattern") == pattern && N(s, "machineInstances") == 1 && s.GetProperty("checkpoints").GetArrayLength() == scenario.Calls.Count, "Second machine or missing event.");
            var r = Row(p, i); string[] fields = ["index", "machineId", "prefix", "consumer", "alternate", "disposition", "provenance", "producerGeneration0196", "readerGeneration0196", "compareGeneration0196", "abiWrites", "after", "stateBefore", "stateAfter", "continuityJournal", "canaries"];
            if (p2 is not null) fields = [.. fields, "p2", "p2Before", "p2After", "incomingP2Generation", "p2Generation"];
            if (control is not null) fields = [.. fields, "control", "controlBefore", "controlAfter", "incomingTcon0Generation", "tcon0Generation", "incomingTrnsitGeneration", "trnsitGeneration"];
            P28LimiterScenario.Shape(r, fields);
            Require(N(r, "index") == i && N(r, "machineId") == 1 && Equal(r.GetProperty("canaries"), JsonSerializer.SerializeToElement(new[] { pattern, pattern, pattern })), "Wrong machine/index/canary.");
            var h = ram[p]; Require(Equal(r.GetProperty("stateBefore"), State(h)), "Hidden initial/source/history reseed.");
            // Independently owned M2x RAM and ISA-computed final PSW, not compare observations.
            h[0x124] = owned[p][0x124]; h[0x12A] = owned[p][0x12A];
            var c = r.GetProperty("consumer"); var a = r.GetProperty("alternate"); var disposition = prefix.Disposition == "NotRun" ? "NotRun" : "NoFresh0196"; var provenance = "NoFresh0196";
            P28QuartetGeneration? reader = null, compare = null; int? left = null, right = null, branchPc = null, branchTarget = null; bool? cf = null, zf = null, taken = null; var domain = "NotRun";
            var native = new List<int[]>(); var writes = new List<P28Word0196SoftwareWrite>(); var after = prefix.Actual.GetProperty("after");
            if (prefix.ResultGeneration is { } g)
            {
                Require(c.ValueKind == JsonValueKind.Object && Equal(r.GetProperty("abiWrites"), JsonSerializer.SerializeToElement(new[] { new[] { 0, 0x5ED, 0x54F5 } })), "Missing native prefix or hidden A/pointer/frame/PC556F entry.");
                provenance = prefix.SelectedGeneration is null ? "ConsumerGateBypass0196" : "QuartetDerived0196";
                var first = P28Word0196HandoffModel.Build(g.Value, ownPsw[p], (byte)h[0x128], (byte)h[0x117]);
                var accesses = P28Word0196HandoffValidator.ValidateConsumer(c, after, first, registers, rawPrefix: true); native.AddRange(accesses);
                foreach (var w in accesses.Where(v => v[3] == 1)) for (var b = 0; b < w[2] / 8; b++) h[w[1] + b] = w[4] >> (8 * b) & 255;
                if (accesses.Any(v => v[0] == 0x54FA)) reader = g;
                after = c.GetProperty("exit"); var status = N(c.GetProperty("stage").GetProperty("result"), "status");
                if (status == 0 && first.Stop == 0x556F)
                {
                    Require(a.ValueKind == JsonValueKind.Object, "Actual5501 taken branch lacks continuous alternate.");
                    var next = P28Word0196AlternateModel.Build(g.Value, first.A, first.Psw, h);
                    var ownNative = ValidateAlternate(a, after, next, registers);
                    var order = Matrix(prefix.Actual.GetProperty("continuityJournal"), 6, 32768).Count(j => j[0] == 1 && j[4] == 1) + native.Count(v => v[3] == 1);
                    foreach (var w in ownNative.Where(v => v[3] == 1))
                    {
                        var old = h[w[1]]; var d = w[0] < 0x5578 ? "Before5578" : g.Value < 192 ? "BelowImmediate" : g.Value == 192 ? "EqualImmediate" : "AboveImmediate";
                        writes.Add(new(w[1], w[2], w[0], old, w[4], new(w[0], i, order++, w[4]), d)); h[w[1]] = w[4];
                    }
                    native.AddRange(ownNative);
                    if (ownNative.Any(v => v[0] == 0x5578)) { compare = g; left = g.Value; right = 192; cf = g.Value < 192; zf = g.Value == 192; domain = cf == true ? "BelowImmediate" : zf == true ? "EqualImmediate" : "AboveImmediate"; }
                    var n = a.GetProperty("stage").GetProperty("events").GetArrayLength(); if (next.Events.Take(n).Any(v => v[0] == 0x557D)) { branchPc = 0x557D; taken = g.Value < 192; branchTarget = taken == true ? 0x55BF : 0x557F; }
                    after = a.GetProperty("exit"); status = N(a.GetProperty("stage").GetProperty("result"), "status");
                    disposition = status == 0 && reader is not null && compare is not null ? provenance == "QuartetDerived0196" ? "QuartetDerived0196AlternateStrict" : "GateBypass0196AlternateStrict" : Status(status);
                }
                else { Require(a.ValueKind == JsonValueKind.Null, "Alternate executed without native5501 taken branch."); disposition = Status(status); }
            }
            else Require(c.ValueKind == JsonValueKind.Null && a.ValueKind == JsonValueKind.Null && r.GetProperty("abiWrites").GetArrayLength() == 0, "Suffix/source ran after terminal or without fresh0196.");
            if (p2 is not null) (after, disposition) = p2.Finish(p, i, r, after, compare, disposition);
            if (control is not null)
            {
                var next = control.Finish(p, i, r, after, compare, disposition, h[0x18E], p2!.Rows[p][i]);
                after = next.After; disposition = next.Disposition; native.AddRange(next.Ram);
            }
            owned[p][0x12A] = h[0x12A]; // Only independently modeled suffix writes affect next M2x history.
            Require(Equal(r.GetProperty("stateAfter"), State(h)) && Equal(r.GetProperty("after"), after), "Persistent software state/exit forged.");
            Require(r.GetProperty("disposition").GetString() == disposition && r.GetProperty("provenance").GetString() == provenance, "False strict/gate/partial classification.");
            foreach (var (name, expected) in new[] { ("producerGeneration0196", prefix.ResultGeneration), ("readerGeneration0196", reader), ("compareGeneration0196", compare) })
                Require(Equal(r.GetProperty(name), JsonSerializer.SerializeToElement(expected, JsonDefaults.Create())), "Stale equal-value generation substituted.");
            P28Word0196HandoffValidator.ValidateJournal(r, prefix.Actual.GetProperty("continuityJournal"), native.ToArray(), prefix.ResultGeneration, reader);
            if (compare is not null) { Require(compare == reader, "Second reader is not the first reader generation."); P28Word0196HandoffValidator.ValidateGeneration(Matrix(r.GetProperty("continuityJournal"), 6, 32768), compare, i, 0x196, 0x5578); }
            reports[p].Add(new(i, disposition, provenance, prefix, prefix.ResultGeneration, reader, compare, left, right, cf, zf, domain, branchPc, taken, branchTarget, writes, N(after, "pc"), r.Clone()));
        }, (p, i, psw, history) => { owned[p] = history; ownPsw[p] = psw; }));
        return Enumerable.Range(0, 3).Select(p => new P28Word0196AlternateSequence(id, new[] { 0, 85, 170 }[p], reports[p])).ToArray();
    }
    private static string Status(int status) => status switch { 3 => "BudgetExceeded", 2 => "ExecutionError", _ => "0196AlternatePartial" };
    private static int N(JsonElement e, string k) => e.GetProperty(k).GetInt32();
    internal static int[][] ValidateAlternate(JsonElement suffix, JsonElement prefixExit, P28Word0196Oracle own, int[] registers)
    {
        P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses"); var entry = suffix.GetProperty("entry"); var exit = suffix.GetProperty("exit"); P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        Require(N(prefixExit, "pc") == 0x556F && Equal(entry, prefixExit) && entry.GetProperty("registers").EnumerateArray().Select(v => v.GetInt32()).SequenceEqual(registers), "Detached556F entry;PC shortcut/second machine/hidden seed.");
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter"); var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 18, 0, [], null)!;
        var events = Matrix(stage.GetProperty("events"), 8, 18); Require(events.Length == result.Steps && events.Length <= own.Events.Count && events.Select(v => string.Join(',', v)).SequenceEqual(own.Events.Take(events.Length).Select(v => string.Join(',', v))), "Wrong5578 operands/CF/ZF/HC/DD or forced/skipped branch.");
        Require(result.Trace.Count == events.Length, "Missing mandatory trace."); for (var n = 0; n < events.Length; n++) Require(N(result.Trace[n], "pc") == events[n][0] && N(result.Trace[n], "nextPc") == events[n][1] && N(result.Trace[n], "accumulator") == events[n][3] && N(result.Trace[n], "psw") == events[n][5], "Detached native trace.");
        var count = events.Length == 0 ? 0 : own.AccessEnds[events.Length - 1]; var accesses = own.Accesses.Take(count).ToArray();
        Require(Equal(suffix.GetProperty("accesses"), JsonSerializer.SerializeToElement(accesses)) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(accesses.Where(v => v[3] == 1).Select(v => new[] { v[1], v[2], v[4] }).ToArray())), "Wrong word0196 address/width or RAM00C0/hidden write/peripheral access.");
        var stop = events.Length == 0 ? 0x556F : events[^1][1]; Require(result.StopPc == stop && (result.Status != 0 || events.Length == own.Events.Count && stop is 0x5596 or 0x55C5), "Incomplete execution claimed software boundary.");
        Require(result.UsedAssumptions.Count == 0 && result.ProgramReads.Count == 0 && result.ExecutedInstructionBytes.SequenceEqual(own.Events.Take(events.Length).SelectMany((e, n) => Enumerable.Range(e[0], own.Lengths[n])).Distinct().Order()), "Unadmitted code/assumption/P2/timer/RTI.");
        foreach (var w in accesses.Where(v => v[3] == 1 && v[1] is >= 0x108 and < 0x110)) registers[w[1] - 0x108] = w[4];
        var expected = JsonNode.Parse(prefixExit.GetRawText())!; var psw = events.Length == 0 ? own.Events[0][4] : events[^1][5]; expected["pc"] = stop; expected["accumulator"] = events.Length == 0 ? own.Events[0][2] : events[^1][3]; expected["psw"] = psw; expected["dd"] = (psw & 0x1000) != 0; expected["registers"] = JsonSerializer.SerializeToNode(registers);
        Require(Equal(exit, JsonSerializer.SerializeToElement(expected)) && N(stage, "sspAfter") == N(entry, "ssp"), "Forged final carrier/pointer/frame/register."); return accesses;
    }
}
