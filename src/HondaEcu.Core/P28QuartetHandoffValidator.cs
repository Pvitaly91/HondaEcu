using System.Text.Json;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28QuartetGeneration(int WriterPc, int EventIndex, int WriteOrder, int Value);
public sealed record P28QuartetHandoffCheckpoint(int Index, string Disposition, string PrefixDisposition, int? SelectedSlot, int? SelectedAddress,
    P28QuartetGeneration? SelectedGeneration, int? ReaderValue, P28QuartetGeneration? ResultGeneration, int? ConsumerWord0196, IReadOnlyList<P28QuartetGeneration> QuartetGenerations, JsonElement Actual);
public sealed record P28QuartetHandoffSequence(string Image, int ScratchPattern, IReadOnlyList<P28QuartetHandoffCheckpoint> Checkpoints);
public sealed record P28QuartetHandoffComparison(int ScratchPattern, int Index, int? ValueA, int? ValueB, bool? Diverged, string Effect);
public sealed record P28QuartetHandoffReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28QuartetHandoffSequence> Sequences,
    IReadOnlyList<P28QuartetHandoffComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition is not ("QuartetHandoffStrict" or "ConsumerGateBypassNotHandoff"));
    public string QuartetTechnicalConsumer => HasFailure || !Sequences.SelectMany(s => s.Checkpoints).Any(c => c.ResultGeneration is not null) ? "Partial" : "Validated";
    public string QuartetScheduledHandoff => HasFailure || !Sequences.SelectMany(s => s.Checkpoints).Any(c => c.SelectedGeneration is not null) ? "Partial" : "Validated";
    public object Summary => new { Events = Sequences.Sum(s => s.Checkpoints.Count), Handoffs = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "QuartetHandoffStrict"), ResultWrites = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.ResultGeneration is not null), PerSlotReaders = Enumerable.Range(0, 4).ToDictionary(s => $"{0x3B6 + 2 * s:X4}", s => Sequences.SelectMany(q => q.Checkpoints).Count(c => c.SelectedSlot == s)), AbWitnesses = Comparisons.Count(c => c.Diverged == true), Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()) };
    public string InterStageScheduling => "ExplicitHarnessSchedule";
    public string RecoveredQuartetScheduler => "NotEstablished";
    public string IrqDelivery => "NotInjected";
    public string PendingInterrupt => "NotModeled";
    public string ElapsedTime => "None";
    public string SelectorProducer => "NotRun;RawSoftwareSnapshot0..3";
    public string CompanionProducer => "NativeFourWordResetBeforeRead";
    public string EntryClassification => "TechnicalSeededQuartetConsumerEntry";
    public string OtherConsumer1550 => "StaticOtherConsumer/NotRun";
    public string PhysicalQuartetRole => "Unknown";
    public string PhysicalChannelRole => "Unknown";
    public string M2wTechnicalScheduledHandoff => "Validated;DATA0136 only;unchanged";
    public string M2tJgt => "Blocked/Unresolved";
    public string SkippedCode => "NotExecuted";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public int FirmwareBin => 0;
}
public static class P28QuartetHandoffValidator
{
    internal sealed record Continuation(Func<int, int, JsonElement> PreviousAfter, Func<int, int, bool> Terminal,
        Action<int, int, P28QuartetHandoffCheckpoint, int[]> Observe);
    public const string Operation = "quartetConsumerHandoff";
    public static object CreateRequest(RomImage image, P28QuartetHandoffScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28PostSelectionCriticalValidator.CreateRequest(image, scenario.PrefixScenario), JsonDefaults.Create());
        var wire = old.GetProperty("fuelPostSelectionCriticalChain");
        return new { protocolVersion = 1, operation = Operation, images = old.GetProperty("images"), scratchPatterns = new[] { 0, 85, 170 }, allowAssumptions = Array.Empty<string>(), quartetConsumerHandoff = new { formatVersion = 1, initialState = new { fuelPrefix = wire.GetProperty("initialState"), scenario.InitialState.Bit012a1 }, calls = scenario.Calls.Select((c, i) => new { prefix = wire.GetProperty("calls")[i], c.Selector013c }).ToArray(), scenario.TraceEventIndexes } };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28PostSelectionCriticalValidator.ExpectedContracts()[0], entryPc = 0x584, stopBefore = 0x5ED, alternateStopBefore = 0x5AF,
        codeRanges = new[] { new[] { 0x584, 0x5A0 }, new[] { 0x5D5, 0x5ED }, new[] { 0x7DEF, 0x7DF4 } }, instructionBudget = 40,
        entryClassification = "TechnicalSeededQuartetConsumerEntry", abiWrites = "PC,PSW1DCA,LRB0021 only;USP/SSP/A/pointers/locals retained;no IRQ frame",
        selectorSource = "RawSoftwareSnapshot0..3;OnceBeforeExecutedConsumer;SelectorProducerNotRun", companionSource = "NativeResetFourWords03BE/03C0/03C2/03C4;X2NativeZero",
        reader = new[] { 0x5DF, 16 }, resultWriter = new[] { 0x5EB, 0x196, 16 }, generation = "writerPC,eventIndex,zeroBasedAllNativeWriteOrder,value",
        machine = "OneCpuOneBusPerSequence;NoSerializationHandoff", interStageScheduling = "ExplicitHarnessSchedule", recoveredQuartetScheduler = "NotEstablished", skippedCode = "NotExecuted", irqDelivery = "NotInjected", pendingInterrupt = "NotModeled", elapsedTime = "None", physicalChannelRole = "Unknown", canaryAddresses = new[] { 0x300, 0x350, 0x3E0 }, initial012A = "MaskedBit1Once;NeighborsRetained;UpstreamNotRun", initial0196 = "DiagnosticScratchOnly", partial = "Terminal;RetainNativeStores;LaterNotRun", otherConsumer1550 = "StaticOtherConsumer/NotRun", physicalRpmAvailable = false } });
    public static async Task<P28QuartetHandoffReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28QuartetHandoffScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28QuartetHandoffSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2x quartet provenance evidence.", e); }
        }
        var comparisons = new List<P28QuartetHandoffComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var complete = a.Disposition == "QuartetHandoffStrict" && b.Disposition == "QuartetHandoffStrict";
                    bool? changed = complete ? a.ConsumerWord0196 != b.ConsumerWord0196 : null;
                    comparisons.Add(new(sequences[p].ScratchPattern, i, a.ConsumerWord0196, b.ConsumerWord0196, changed, !complete ? "IncompleteOrNativeGateBypass" : changed == true ? "FuelCellToCurrentQuartetToNative0196Witness" : "EqualOutput;NativeResetCompanionZero"));
                }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, offsets, sequences, comparisons, contract);
    }
    internal static IReadOnlyList<P28QuartetHandoffSequence> Analyze(RomImage image, P28QuartetHandoffScenario scenario, JsonElement root, string id, Continuation? continuation = null)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "quartetHandoffSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2x contract differs.");
        foreach (var k in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(k).GetArrayLength() == 0, "Foreign M2x rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result."); var seq = root.GetProperty("quartetHandoffSequences"); Require(seq.GetArrayLength() == 3, "Three scratch histories required.");
        JsonElement Row(int p, int i) => seq[p].GetProperty("checkpoints")[i];
        var view = JsonSerializer.SerializeToElement(new { runnerVersion = root.GetProperty("runnerVersion"), upstreamCommit = root.GetProperty("upstreamCommit"), localSemanticFixes = root.GetProperty("localSemanticFixes"), criticalSequences = seq.EnumerateArray().Select(s => new { scratchPattern = s.GetProperty("scratchPattern"), checkpoints = s.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("fuelPrefix")).ToArray() }).ToArray() });
        var prefixes = P28PostSelectionCriticalValidator.AnalyzeEvidence(image, scenario.PrefixScenario, view, id,
            (p, i) => continuation?.Terminal(p, i) == true || Row(p, i).GetProperty("consumer").ValueKind == JsonValueKind.Object && Row(p, i).GetProperty("consumer").GetProperty("stage").GetProperty("result").GetProperty("status").GetInt32() != 0,
            continuationBefore: (p, i, before) => { if (i > 0) Require(Equal(before, continuation?.PreviousAfter(p, i - 1) ?? Row(p, i - 1).GetProperty("after")), "CPU reseeded before next prefix."); }, incomingScbSwitch: true);
        var reports = new List<P28QuartetHandoffSequence>();
        for (var p = 0; p < 3; p++)
        {
            var pattern = new[] { 0, 85, 170 }[p]; var s = seq[p]; P28LimiterScenario.Shape(s, "scratchPattern", "machineInstances", "checkpoints");
            Require(N(s, "scratchPattern") == pattern && N(s, "machineInstances") == 1 && s.GetProperty("checkpoints").GetArrayLength() == scenario.Calls.Count, "Second machine/missing events.");
            var ownPrefix = new P28PostSelectionCriticalHistory(image, scenario.PrefixScenario, pattern); var ram = InitialRam(pattern, scenario); var scb1 = Enumerable.Repeat(pattern, 8).ToArray(); scb1[6] = 0x80; scb1[7] = 2;
            var scb2 = Enumerable.Repeat(pattern, 8).ToArray();
            var stopped = false; JsonElement prior = default; var rows = new List<P28QuartetHandoffCheckpoint>();
            for (var i = 0; i < scenario.Calls.Count; i++)
            {
                var r = Row(p, i); P28LimiterScenario.Shape(r, "index", "machineId", "fuelPrefix", "consumer", "disposition", "before", "after", "stateBefore", "stateAfter", "abiWrites", "sourceWrites", "quartetGenerations", "selectedSlot", "selectedAddress", "selectedGeneration", "resultGeneration", "continuityJournal", "canaries");
                Require(N(r, "index") == i && N(r, "machineId") == 1 && Equal(r.GetProperty("canaries"), JsonSerializer.SerializeToElement(new[] { pattern, pattern, pattern })), "Wrong index/machine/canary.");
                Require(Equal(r.GetProperty("stateBefore"), State(ram)), "Initial/retained RAM overwritten."); if (i > 0) Require(Equal(r.GetProperty("before"), continuation?.PreviousAfter(p, i - 1) ?? prior.GetProperty("after")), "CPU reset between events.");
                else
                {
                    var b = r.GetProperty("before"); P28FuelFactorValidator.ValidateBoundary(b);
                    Require(N(b, "pc") == 0x1966 && N(b, "accumulator") == pattern * 257 && N(b, "psw") == 0x0DC9 && N(b, "lrb") == 0x20 && N(b, "ssp") == 0x7FE && N(b, "usp") == 0x280 && new[] { "x1", "x2", "dp" }.All(k => N(b, k) == pattern * 257) && b.GetProperty("registers").EnumerateArray().All(v => v.GetInt32() == pattern), "Once-only initial Cpu ABI differs.");
                }
                var f = r.GetProperty("fuelPrefix"); var consumer = r.GetProperty("consumer"); var prefix = prefixes[p].Checkpoints[i]; var actualNative = new List<int[]>(); var host = new List<int[]>(); NativeLeaves(f, actualNative); HostLeaves(f, host);
                var adaptive = f.GetProperty("prefix").GetProperty("prefix").GetProperty("prefix"); var ticks = adaptive.GetProperty("ticks"); var first = ticks.GetArrayLength() > 0 ? ticks[0] : adaptive.GetProperty("producer");
                if (first.ValueKind == JsonValueKind.Object) { Require(Equal(first.GetProperty("before"), r.GetProperty("before")), "Detached initial/persistent Cpu."); var entry = first.GetProperty("entry"); var target = first.GetProperty("tickTarget"); Require(N(entry, "x1") == (target.ValueKind == JsonValueKind.Number ? target.GetInt32() : scb1[0] | scb1[1] << 8) && N(entry, "x2") == (scb1[2] | scb1[3] << 8) && N(entry, "dp") == (scb1[4] | scb1[5] << 8), "SCB1 pointer bank copied/reseeded."); }
                foreach (var write in actualNative.Where(a => a[3] == 1)) if (write[1] is 0x124 or 0x125) ram[write[1]] = write[4];
                foreach (var write in host) if (write[0] is 0x124 or 0x125) ram[write[0]] = write[2]; // already independently validated old source ownership
                var disposition = stopped ? "NotRun" : prefix.Disposition == "StrictMatch" ? "" : "ConsumerNotRun"; var generations = new List<P28QuartetGeneration>(); P28QuartetGeneration? selected = null, resultGeneration = null; int? selectedSlot = null, selectedAddress = null, readerValue = null, output = null;
                if (!stopped && prefix.Disposition == "StrictMatch")
                {
                    var own = ownPrefix.Step(scenario.Calls[i].Prefix); var mapping = P28QuartetHandoffModel.Select(scenario.Calls[i].Selector013c);
                    var expectedSource = new[] { new[] { 0x13C, 8, (int)scenario.Calls[i].Selector013c } }; Require(Equal(r.GetProperty("sourceWrites"), JsonSerializer.SerializeToElement(expectedSource)), "Hidden selector source."); host.AddRange(expectedSource); ram[0x13C] = mapping.Selector013c;
                    Require(Equal(r.GetProperty("abiWrites"), JsonSerializer.SerializeToElement(new[] { new[] { 0, 0x22B1, 0x584 }, new[] { 1, own.Oracle.Machine.Psw, 0x1DCA }, new[] { 2, 0x20, 0x21 } })), "Hidden X1/A/USP/frame ABI seed.");
                    Require(consumer.ValueKind == JsonValueKind.Object, "Completed prefix lacks consumer.");
                    var model = P28QuartetHandoffEvidence.Build(own.Oracle.Machine.Accumulator, scenario.Calls[i].Selector013c, (byte)ram[0x124], (byte)ram[0x125], (byte)ram[0x12A], own.After.CommonWords03b6, new(ram));
                    var count = ValidateConsumer(consumer, f.GetProperty("critical").GetProperty("exit"), model, ram, pattern, scb2);
                    var accesses = model.Accesses.Take(count).ToArray(); actualNative.AddRange(accesses); foreach (var a in accesses.Where(a => a[3] == 1)) ram[a[1]] = a[4];
                    var stageResult = consumer.GetProperty("stage").GetProperty("result"); var complete = N(stageResult, "status") == 0; var read = accesses.SingleOrDefault(a => a[0] == 0x5DF && a[1] >= 0x3B6);
                    disposition = !complete ? N(stageResult, "status") switch { 3 => "BudgetExceeded", 2 => "ExecutionError", _ => "ConsumerPartial" } : read is null ? "ConsumerGateBypassNotHandoff" : "QuartetHandoffStrict";
                    var order = 0; foreach (var a in actualNative.Where(a => a[3] == 1)) { if (a[0] is 0x22A5 or 0x22A8 or 0x22AB or 0x22AE) generations.Add(new(a[0], i, order, own.Projection.CommonPathWord)); if (a[0] == 0x5EB) resultGeneration = new(0x5EB, i, order, model.A); order++; }
                    Require(generations.Count == 4 && generations.Select(g => g.WriterPc).SequenceEqual(new[] { 0x22A5, 0x22A8, 0x22AB, 0x22AE }), "Missing/merged quartet generations.");
                    if (read is not null) { selectedSlot = mapping.SelectedSlot; selectedAddress = mapping.SelectedAddress; selected = generations[mapping.SelectedSlot]; readerValue = selected.Value; }
                    if (resultGeneration is not null) output = resultGeneration.Value;
                }
                else
                {
                    Require(consumer.ValueKind == JsonValueKind.Null && r.GetProperty("abiWrites").GetArrayLength() == 0 && r.GetProperty("sourceWrites").GetArrayLength() == 0, "Consumer/source ran after incomplete prefix.");
                    var order = 0; foreach (var a in actualNative.Where(a => a[3] == 1))
                    {
                        if (a[0] is 0x22A5 or 0x22A8 or 0x22AB or 0x22AE) { var g = prefix.Generations.Single(g => g.Address == a[1] && g.Generation == i); Require(g.Value == a[4], "Partial generation is not the independently validated native writer."); generations.Add(new(a[0], i, order, g.Value)); }
                        order++;
                    }
                }
                Require(r.GetProperty("disposition").GetString() == disposition, "False completion/disposition.");
                Require(Equal(r.GetProperty("quartetGenerations"), JsonSerializer.SerializeToElement(generations, JsonDefaults.Create())) && Equal(r.GetProperty("selectedGeneration"), JsonSerializer.SerializeToElement(selected, JsonDefaults.Create())) && Equal(r.GetProperty("resultGeneration"), JsonSerializer.SerializeToElement(resultGeneration, JsonDefaults.Create())), "Stale/neighbor/same-value generation substituted.");
                Require(Equal(r.GetProperty("selectedSlot"), JsonSerializer.SerializeToElement(selectedSlot)) && Equal(r.GetProperty("selectedAddress"), JsonSerializer.SerializeToElement(selectedAddress)), "Correct value from wrong slot.");
                ValidateJournal(r, actualNative, host, selectedAddress, selected);
                foreach (var a in Matrix(r.GetProperty("continuityJournal"), 6, 32768).Where(a => a[4] == 1)) for (var b = 0; b < a[3] / 8; b++) if (a[2] + b is >= 0x88 and < 0x90) scb1[a[2] + b - 0x88] = (a[5] >> (8 * b)) & 255;
                Require(Equal(r.GetProperty("stateAfter"), State(ram)), "Retained/fresh0196 or companion history forged.");
                if (consumer.ValueKind == JsonValueKind.Object) Require(Equal(r.GetProperty("after"), consumer.GetProperty("exit")), "Detached consumer exit.");
                if (stopped) Require(Equal(r.GetProperty("before"), r.GetProperty("after")) && actualNative.Count == 0 && host.Count == 0, "NotRun changed machine.");
                var checkpoint = new P28QuartetHandoffCheckpoint(i, disposition, prefix.Disposition, selectedSlot, selectedAddress, selected, readerValue, resultGeneration, output, generations, r.Clone());
                continuation?.Observe(p, i, checkpoint, scb2); rows.Add(checkpoint); prior = r; stopped |= continuation?.Terminal(p, i) == true || disposition is "ConsumerPartial" or "ConsumerNotRun" or "ExecutionError" or "BudgetExceeded";
            }
            reports.Add(new(id, pattern, rows));
        }
        return reports;
    }
    private static Dictionary<int, int> InitialRam(int pattern, P28QuartetHandoffScenario s) => new() { [0x13C] = pattern, [0x12A] = (pattern & ~2) | (s.InitialState.Bit012a1 ? 2 : 0), [0x124] = s.InitialState.FuelPrefix.Adaptive.Joint.Data0124, [0x125] = pattern, [0x196] = pattern * 257, [0x3BE] = pattern * 257, [0x3C0] = pattern * 257, [0x3C2] = pattern * 257, [0x3C4] = pattern * 257, [0x19B] = pattern, [0x19D] = pattern, [0x19F] = pattern, [0x90] = pattern * 257, [0x92] = pattern * 257 };
    private static JsonElement State(Dictionary<int, int> r) => JsonSerializer.SerializeToElement(new { selector013c = r[0x13C], byte012a = r[0x12A], byte0124 = r[0x124], byte0125 = r[0x125], word0196 = r[0x196], companions03be = new[] { r[0x3BE], r[0x3C0], r[0x3C2], r[0x3C4] }, byte019b = r[0x19B], byte019d = r[0x19D], byte019f = r[0x19F] });
    private static int N(JsonElement e, string k) => e.GetProperty(k).GetInt32();
    internal static int ValidateConsumer(JsonElement suffix, JsonElement prefixExit, P28QuartetOracle own, Dictionary<int, int> ram, int pattern, int[]? registers = null)
    {
        P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses"); var entry = suffix.GetProperty("entry"); var exit = suffix.GetProperty("exit"); P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        Require(N(prefixExit, "pc") == 0x22B1 && N(entry, "pc") == 0x584 && N(entry, "psw") == 0x1DCA && N(entry, "lrb") == 0x21 && N(entry, "accumulator") == own.Events[0][2] && N(entry, "accumulator") == N(prefixExit, "accumulator") && N(entry, "ssp") == 0x7FE && N(entry, "x1") == ram[0x90] && N(entry, "x2") == ram[0x92] && N(entry, "dp") == pattern * 257 && N(entry, "usp") == pattern * 257 && entry.GetProperty("registers").EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(registers ?? Enumerable.Repeat(pattern, 8).ToArray()), "Wrong technical ABI/pointer seed/fake IRQ frame.");
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter"); var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 40, 0, [], null)!;
        var events = Matrix(stage.GetProperty("events"), 8, 40); Require(events.Length == result.Steps && events.Length <= own.Events.Count && events.Select(a => string.Join(',', a)).SequenceEqual(own.Events.Take(events.Length).Select(a => string.Join(',', a))), "Wrong selector/index/arithmetic/flags/events.");
        Require(result.Trace.Count == events.Length, "Missing mandatory trace."); for (var n = 0; n < events.Length; n++) Require(N(result.Trace[n], "pc") == events[n][0] && N(result.Trace[n], "nextPc") == events[n][1] && N(result.Trace[n], "accumulator") == events[n][3] && N(result.Trace[n], "psw") == events[n][5], "Trace detached from native arithmetic.");
        var count = events.Length == 0 ? 0 : own.AccessEnds[events.Length - 1]; var a = own.Accesses.Take(count).ToArray(); Require(Equal(suffix.GetProperty("accesses"), JsonSerializer.SerializeToElement(a)) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(a.Where(r => r[3] == 1).Select(r => new[] { r[1], r[2], r[4] }).ToArray())), "Wrong width/slot/companion/hidden rewrite/provenance.");
        var stop = events.Length == 0 ? 0x584 : events[^1][1]; Require(result.StopPc == stop && N(exit, "pc") == stop && (result.Status != 0 || events.Length == own.Events.Count && stop == 0x5ED) && (stop != 0x5AF || result.Status == 1), "Partial claimed fresh completion.");
        Require(result.UsedAssumptions.Count == 0 && result.ProgramReads.Count == 0 && result.ExecutedInstructionBytes.SequenceEqual(own.Events.Take(events.Length).SelectMany((e, n) => Enumerable.Range(e[0], own.Lengths[n])).Distinct().Order()), "Extra code/read/assumption/RTI.");
        Require(N(exit, "accumulator") == (events.Length == 0 ? N(entry, "accumulator") : events[^1][3]) && N(exit, "psw") == (events.Length == 0 ? 0x1DCA : events[^1][5]), "Forged final carriers.");
        var pointer = events.Length == 0 ? new[] { ram[0x90], ram[0x92] } : own.PointerEnds[events.Length - 1]; Require(N(exit, "x1") == pointer[0] && N(exit, "x2") == pointer[1], "Native index mismatch.");
        foreach (var k in new[] { "lrb", "ssp", "dp", "usp", "registers" }) Require(Equal(entry.GetProperty(k), exit.GetProperty(k)), "Undisclosed bank/stack/caller mutation."); Require(N(stage, "sspAfter") == 0x7FE, "Fake IRQ frame."); return count;
    }
    internal static void ValidateJournal(JsonElement r, IReadOnlyList<int[]> native, IReadOnlyList<int[]> host, int? address, P28QuartetGeneration? selected)
    {
        Require(N(r, "machineId") == 1, "Second machine."); var journal = Matrix(r.GetProperty("continuityJournal"), 6, 32768);
        Require(journal.All(j => j[0] is 0 or 1 && j[3] is 8 or 16 && j[4] is 0 or 1) && journal.Where(j => j[0] == 1).Select(j => string.Join(',', j.Skip(1))).SequenceEqual(native.Select(j => string.Join(',', j))), "Missing/reordered/foreign native journal.");
        Require(journal.Where(j => j[0] == 0).All(j => j[1] == 65536 && j[4] == 1) && journal.Where(j => j[0] == 0).Select(j => string.Join(',', new[] { j[2], j[3], j[5] })).Order().SequenceEqual(host.Select(j => string.Join(',', j)).Order()), "Hidden host initializer/X1/quartet/0196 setter.");
        Require(!journal.Any(j => j[0] == 0 && j[4] == 1 && j[2] < 0x3BE && j[2] + j[3] / 8 > 0x3B6), "Host quartet copy.");
        if (r.TryGetProperty("consumer", out var consumer) && consumer.ValueKind == JsonValueKind.Object)
        {
            var source = Array.FindIndex(journal, j => j[0] == 0 && j[2] == 0x13C); var lastPrefix = Array.FindLastIndex(journal, j => j[0] == 1 && j[1] >= 0x2200 && j[1] < 0x22B1); var firstConsumer = Array.FindIndex(journal, j => j[0] == 1 && j[1] == 0x584);
            Require(source > lastPrefix && source < firstConsumer, "Selector applied outside disclosed stage schedule.");
        }
        if (selected is null) return; Require(selected.EventIndex == N(r, "index") && address is >= 0x3B6 and <= 0x3BC, "Stale/wrong generation.");
        var w = Array.FindIndex(journal, j => j[0] == 1 && j[1] == selected.WriterPc && j[2] == address && j[3] == 16 && j[4] == 1 && j[5] == selected.Value); var reads = journal.Select((j, n) => (j, n)).Where(t => t.j[0] == 1 && t.j[1] == 0x5DF).ToArray();
        Require(reads.Length == 2 && reads[0].j[2] == 0x90 && reads[0].j[3] == 16 && reads[0].j[4] == 0 && reads[1].j[2] == address && reads[1].j[3] == 16 && reads[1].j[4] == 0 && reads[1].j[5] == selected.Value && w >= 0 && w < reads[1].n, "Wrong selected reader provenance.");
        Require(journal.Take(w).Count(j => j[0] == 1 && j[4] == 1) == selected.WriteOrder && !journal.Skip(w + 1).Take(reads[1].n - w - 1).Any(j => j[4] == 1 && j[2] < address + 2 && j[2] + j[3] / 8 > address), "Selected generation overwritten or ordinal forged.");
    }
    private static void NativeLeaves(JsonElement node, List<int[]> result)
    {
        if (node.ValueKind != JsonValueKind.Object) return; if (node.TryGetProperty("accesses", out var a)) { result.AddRange(Matrix(a, 5, 8192)); return; }
        if (node.TryGetProperty("ticks", out var ticks)) { foreach (var t in ticks.EnumerateArray()) NativeLeaves(t, result); NativeLeaves(node.GetProperty("producer"), result); NativeLeaves(node.GetProperty("joint"), result); return; }
        if (node.TryGetProperty("decisionAccesses", out a)) { result.AddRange(Matrix(a, 5, 8192)); NativeLeaves(node.GetProperty("fuel"), result); return; }
        if (node.TryGetProperty("prefix", out var prefix)) NativeLeaves(prefix, result); foreach (var k in new[] { "suffix", "consumer", "critical" }) if (node.TryGetProperty(k, out var s)) NativeLeaves(s, result);
    }
    private static void HostLeaves(JsonElement node, List<int[]> result)
    {
        if (node.ValueKind == JsonValueKind.Object) foreach (var item in node.EnumerateObject())
            {
                if (item.Name == "inputWrites" && node.TryGetProperty("factorStage", out _)) continue;
                if (item.Name is "snapshotWrites" or "inputWrites" or "transitionWrites" or "transitionToDecisionWrites" or "transitionToFactorWrites" or "transitionToAdditiveWrites") result.AddRange(Matrix(item.Value, 3, 512).Where(w => w[0] >= 0x80));
                else if (item.Name == "prefixTransitions" && item.Value.ValueKind == JsonValueKind.Array) foreach (var t in item.Value.EnumerateArray()) result.AddRange(Matrix(t.GetProperty("writes"), 3, 32).Where(w => w[0] >= 0x80)); else HostLeaves(item.Value, result);
            }
        else if (node.ValueKind == JsonValueKind.Array) foreach (var c in node.EnumerateArray()) HostLeaves(c, result);
    }
}
