using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28Data0136Generation(int WriterPc, int EventIndex, int WriteOrder, int Value);
public sealed record P28Data0136NativeWriter(int WriterPc, IReadOnlyList<int> InstructionBytes, string Form, int Address, int Width,
    int OldValue, int NewValue, int WriteOrder, int EventIndex, P28Data0136Generation Generation);
public sealed record P28Data0136TechnicalCheckpoint(int Index, string Validation, string Disposition, string GenerationDisposition,
    string SourceMode, int? NativeWord0136, int RetainedWord0136, P28Data0136Generation? Generation, P28Data0136NativeWriter? Writer,
    string ZeroCause, IReadOnlyList<int[]> PeripheralReads, IReadOnlyList<int> SameRoutineReaders, JsonElement Actual);
public sealed record P28Data0136TechnicalSequence(int ScratchPattern, IReadOnlyList<P28Data0136TechnicalCheckpoint> Checkpoints);
public sealed record P28Data0136TechnicalProducerReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, IReadOnlyList<P28Data0136TechnicalSequence> Sequences, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Validation != "StrictMatch");
    public string OverallStage => HasFailure ? "Partial" : "NativeTechnicalProducerValidated";
    public string ProducerTo2330SchedulerSeam => "NotEstablished";
    public string EntryClassification => "TechnicalSeededEntry56BE;NotRecoveredCallerOrISR";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string LaterReaders => "5782/5787 NotRun;outside stop-before5719";
    public string NativeWriterThenHeld => "NotReachableWithinBoundedSlice;0128.3 set and never cleared;no hidden reseeding";
    public string Historical => "M1i mode0-only;M2u ProducerNotRun;M2s Partial;M2t Blocked/Partial;JGT unresolved;strict M2i Blocked";
    public string Acceptance => "quartet consumer NotRun;GUI r3 paused/NotRun;D1/D2 interactive NotRun;hardware/full boot NotRun";
    public string FirmwareOutput => "BIN0;bindings0;compensation0;export plans/receipts/tokens0";
    public object Summary => new
    {
        NativeObservations = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Validation == "StrictMatch"),
        Writers56f3 = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Writer?.WriterPc == 0x56F3),
        Writers5707 = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Writer?.WriterPc == 0x5707),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        ModelOnlyObservations = 0,
        Categories = new[] { "NativeTechnicalExecution", "StorageDomainSynthetic" }
    };
}

public static class P28Data0136TechnicalProducerValidator
{
    public const string Operation = "data0136TechnicalProducer";
    public static object CreateRequest(RomImage image, P28Data0136TechnicalProducerScenario s) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        data0136TechnicalProducer = new { s.FormatVersion, s.InitialState, s.Observations, s.TraceObservationIndexes }
    };
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new
    {
        id=Operation,entryClassification="TechnicalSeededEntry56BE",entryPc=0x56BE,exitPcs=new[]{0x5719},stop="BeforeInstruction",
        allowedCodeRanges=new[]{new[]{0x56BE,0x5719}},psw=0x1102,lrb=0x21,scb=2,usp=0x280,ssp=0x7FE,instructionBudget=128,
        mandatoryFirstRead=new[]{0x3A,16},conditionalPeripheralReads=new[]{new[]{0x19,8},new[]{0x42,8}},peripheralWrites=Array.Empty<int>(),
        readEffects="NondestructiveFrozenSnapshotNoNewEventNoInterrupt",mode="OnceInitialDATA011F.2",
        source00f0="WordRawSoftwareSnapshotUpstreamProducerNotRun",generation="writerPC,eventIndex,writeOrder,value",programDataReads=Array.Empty<int>(),
        state="OneCpuRamPerSequence",irqDelivery="NotInjected",elapsedTime="None",producerTo2330SchedulerSeam="NotEstablished",physicalRpmAvailable=false
    } });
    public static async Task<P28Data0136TechnicalProducerReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28Data0136TechnicalProducerScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(original, scenario), options, cancellationToken).ConfigureAwait(false);
        try { return Analyze(original, profile.Id, scenario, response.Response); }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
        { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2v native evidence.", e); }
    }
    internal static P28Data0136TechnicalProducerReport Analyze(RomImage image, string profileId, P28Data0136TechnicalProducerScenario scenario, JsonElement root,
        Func<int, P28Data0136TechnicalProducerModel>? modelFactory = null, Action<int, int, P28Data0136TechnicalProducerModel>? beforeObservation = null,
        Func<int, int, bool>? terminalAfter = null)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "data0136Sequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2v entry contract differs.");
        foreach (var name in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(name).GetArrayLength() == 0, "Foreign M2v output.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic output.");
        var rows = root.GetProperty("data0136Sequences"); Require(rows.GetArrayLength() == 3, "M2v requires exactly3 scratch sequences.");
        var sequences = new List<P28Data0136TechnicalSequence>();
        for (var p = 0; p < 3; p++)
        {
            var sequence = rows[p]; P28LimiterScenario.Shape(sequence, "imageIndex", "scratchPattern", "completedObservations", "checkpoints");
            var pattern = new[] { 0, 85, 170 }[p]; Require(sequence.GetProperty("imageIndex").GetInt32() == 0 && sequence.GetProperty("scratchPattern").GetInt32() == pattern, "Wrong M2v image/scratch.");
            var own = modelFactory?.Invoke(p) ?? new P28Data0136TechnicalProducerModel(scenario.InitialState, pattern); var terminal = false; var completed = 0;
            P28Data0136Generation? generation = null; var checkpoints = new List<P28Data0136TechnicalCheckpoint>();
            var calls = sequence.GetProperty("checkpoints"); Require(calls.GetArrayLength() == scenario.Observations.Count, "Missing/extra M2v observations.");
            for (var i = 0; i < scenario.Observations.Count; i++)
            {
                beforeObservation?.Invoke(p, i, own);
                var c = calls[i]; P28LimiterScenario.Shape(c, "index", "result", "sourceApplications", "entry", "exit", "ramBefore", "ramAfter", "events", "accesses", "writes", "peripheralAccesses");
                Require(c.GetProperty("index").GetInt32() == i, "Non-dense M2v evidence.");
                var before = own.Snapshot(); Require(Numbers(c.GetProperty("ramBefore")).SequenceEqual(before), "Persistent M2v RAM was host-overwritten/reseeded.");
                var result = c.GetProperty("result"); var mode = (scenario.InitialState.Data011f & 4) != 0 ? "RawSoftwareSnapshot00F0;UpstreamProducerNotRun" : "FrozenTMR2";
                if (terminal)
                {
                    Require(result.ValueKind == JsonValueKind.Null && c.GetProperty("entry").ValueKind == JsonValueKind.Null && c.GetProperty("exit").ValueKind == JsonValueKind.Null, "Execution after terminal M2v boundary.");
                    foreach (var n in new[] { "sourceApplications", "events", "accesses", "writes", "peripheralAccesses" }) Require(c.GetProperty(n).GetArrayLength() == 0, "NotRun applied a source or native effect.");
                    Require(Numbers(c.GetProperty("ramAfter")).SequenceEqual(before), "NotRun changed M2v RAM.");
                    checkpoints.Add(new(i, "NotRun", "NotRun", generation is null ? "NotRun;InitialHistory0136" : "NotRun;RetainedPartialNativeWritten", mode, null, own.Word(0x136), generation, null, "None", [], [], c.Clone())); continue;
                }
                var status = result.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 3, "Invalid M2v status.");
                var steps = result.GetProperty("steps").GetInt32(); Require(steps is >= 0 and <= 128, "M2v budget exceeded.");
                Require(status != 3 || steps == 128, "BudgetExceeded before the declared instruction budget.");
                var oldWord = own.Word(0x136); var oracle = own.Run(scenario.Observations[i], steps);
                Require(oracle.Steps.Count == steps, "Native M2v path extends beyond natural stop.");
                Require(status != 0 || own.Pc == 0x5719, "Premature completed M2v path.");
                Require(status == 0 || own.Pc != 0x5719, "Terminal result at a completed M2v boundary.");
                Require(result.GetProperty("stopPc").GetInt32() == own.Pc, "M2v stop differs from native path.");
                Require(result.GetProperty("outputs").GetArrayLength() == 0 && result.GetProperty("programReads").GetArrayLength() == 0 && result.GetProperty("usedAssumptions").GetArrayLength() == 0, "Foreign outputs/program reads/assumptions.");
                Require(status != 0 || result.GetProperty("error").ValueKind == JsonValueKind.Null, "Completed path with error.");
                Require(status == 0 || result.GetProperty("error").ValueKind == JsonValueKind.String, "Terminal path lacks its fault/unresolved reason.");
                Match(c.GetProperty("sourceApplications"), oracle.SourceApplications.Chunk(3).Select(a => a.ToArray()).ToArray(), 3, "Source application outside closed contract.");
                Match(c.GetProperty("events"), oracle.Steps.Select(s => s.Event).ToArray(), 8, "Independent native PC/flags/arithmetic oracle differs.");
                Match(c.GetProperty("accesses"), oracle.Accesses, 5, "Native RAM access width/order/source/provenance differs.");
                Match(c.GetProperty("writes"), oracle.Writes, 3, "Native RAM write journal differs.");
                Match(c.GetProperty("peripheralAccesses"), oracle.PeripheralReads, 4, "Mandatory/conditional frozen SFR read width/order/value differs.");
                Require(Numbers(c.GetProperty("ramAfter")).SequenceEqual(own.Snapshot()), "Final M2v RAM differs from own state.");
                Boundary(c.GetProperty("entry"), 0x56BE, oracle.EntryA, 0x1DCA, oracle.EntryRam);
                Boundary(c.GetProperty("exit"), own.Pc, own.A, own.Psw, own.Snapshot());
                var trace = result.GetProperty("trace"); Require(trace.GetArrayLength() == steps, "Missing exact-form trace.");
                var extents = new SortedSet<int>();
                for (var j = 0; j < steps; j++)
                {
                    var s = oracle.Steps[j]; var t = trace[j]; var e = s.Event;
                    Require(t.GetProperty("pc").GetInt32() == e[0] && t.GetProperty("nextPc").GetInt32() == e[1] && t.GetProperty("instruction").GetString() == s.Form && t.GetProperty("accumulator").GetInt32() == e[3] && t.GetProperty("psw").GetInt32() == e[5], "Exact native instruction form differs.");
                    for (var b = 0; b < s.Length; b++) extents.Add(e[0] + b);
                }
                Require(Numbers(result.GetProperty("executedInstructionBytes")).SequenceEqual(extents), "Executed instruction extent mismatch.");
                var stores = oracle.Accesses.Where(a => a[1] == 0x136 && a[3] == 1).ToArray(); Require(stores.Length <= 1, "Both producer writers executed.");
                P28Data0136NativeWriter? writer = null;
                if (stores.Length == 1)
                {
                    var w = stores[0]; var expectedPc = (scenario.InitialState.Data011f & 4) != 0 ? 0x56F3 : 0x5707;
                    Require(w[0] == expectedPc && w[2] == 16, "Wrong writer provenance/width.");
                    var order = oracle.Accesses.TakeWhile(a => !ReferenceEquals(a, w)).Count(a => a[3] == 1);
                    generation = new(w[0], i, order, w[4]);
                    writer = new(w[0], Array.AsReadOnly(new[] { (int)image.Span[w[0]], (int)image.Span[w[0] + 1] }), "ST A, off N8", 0x136, 16, oldWord, w[4], order, i, generation);
                }
                var readers = oracle.Accesses.Where(a => a[1] == 0x136 && a[3] == 0).Select(a => a[0]).ToArray();
                Require(readers.All(pc => pc == 0x570E) && (readers.Length == 0 || writer?.WriterPc == 0x5707), "Unproved same-generation reader.");
                if (status == 0) { completed++; Require(oracle.PeripheralReads.Count > 0 && oracle.PeripheralReads[0].SequenceEqual(new[] { 0x3A, 16, 0, (int)scenario.Observations[i].Tmr2 }), "Missing first TMR2 read."); } else terminal = true;
                var disposition = status switch { 1 => "UnresolvedInstruction", 2 => "ExecutionError", 3 => "BudgetExceeded", _ when writer is null => i == 0 ? "FirstObservationNoWrite" : "Held", _ when oracle.ZeroCause == "OverflowToZero" => "OverflowToZeroWrite", _ when writer.NewValue == 0 => "NativeZeroWrite", _ => writer.WriterPc == 0x5707 ? "DirectNativeWrite" : "DividedNativeWrite" };
                checkpoints.Add(new(i, status == 0 ? "StrictMatch" : "Partial", disposition, writer is null ? "Held" : status == 0 ? "NativeWritten" : "PartialNativeWritten",
                    mode, status == 0 ? writer?.NewValue : null, own.Word(0x136), generation, writer, oracle.ZeroCause, oracle.PeripheralReads, readers, c.Clone()));
                terminal |= terminalAfter?.Invoke(p, i) == true;
            }
            Require(sequence.GetProperty("completedObservations").GetInt32() == completed, "M2v completion count differs.");
            sequences.Add(new(pattern, checkpoints.AsReadOnly()));
        }
        return new(1, scenario.Purpose, image.Hash, profileId, scenario.Digest, root.GetProperty("runnerVersion").GetString()!, sequences.AsReadOnly(), root.GetProperty("entryContracts").Clone());
    }
    private static int[] Numbers(JsonElement e) => e.EnumerateArray().Select(n => n.GetInt32()).ToArray();
    private static void Match(JsonElement e, IReadOnlyList<int[]> expected, int width, string message)
    {
        Require(e.GetArrayLength() == expected.Count, message);
        for (var i = 0; i < expected.Count; i++) Require(e[i].GetArrayLength() == width && Numbers(e[i]).SequenceEqual(expected[i]), $"{message} row{i}: expected[{string.Join(',', expected[i])}], observed[{string.Join(',', Numbers(e[i]))}].");
    }
    private static void Boundary(JsonElement b, int pc, int a, int psw, int[] ram)
    {
        P28LimiterScenario.Shape(b, "pc", "accumulator", "psw", "dd", "lrb", "x1", "x2", "dp", "usp", "ssp", "registers");
        int Byte(int address) => ram[Array.IndexOf(P28Data0136TechnicalProducerModel.RamAddresses, address)];
        int Word(int address) => Byte(address) | (Byte(address + 1) << 8);
        Require(b.GetProperty("pc").GetInt32() == pc && b.GetProperty("accumulator").GetInt32() == a && b.GetProperty("psw").GetInt32() == psw && b.GetProperty("dd").GetBoolean() == ((psw & 0x1000) != 0) && b.GetProperty("lrb").GetInt32() == 0x21 && b.GetProperty("ssp").GetInt32() == 0x7FE, "M2v CPU boundary differs.");
        foreach (var (n, address) in new[] { ("x1", 0x90), ("x2", 0x92), ("dp", 0x94), ("usp", 0x96) }) Require(b.GetProperty(n).GetInt32() == Word(address), "M2v persistent pointer differs.");
        Require(Numbers(b.GetProperty("registers")).SequenceEqual(Enumerable.Range(0x108, 8).Select(Byte)), "M2v persistent local bank differs.");
    }
}
