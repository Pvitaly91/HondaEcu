using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28PostReturnSelectorSequence(string Image, int ScratchPattern,
    IReadOnlyList<P28Word0196AlternateCheckpoint> SoftwareCheckpoints, IReadOnlyList<P28P2LatchCheckpoint> FirstP2Checkpoints,
    IReadOnlyList<P28PostP2ControlCheckpoint> ControlCheckpoints, IReadOnlyList<P28BelowSecondP2Checkpoint> BelowCheckpoints,
    IReadOnlyList<P28CalRtRoundTripCheckpoint> CallReturnCheckpoints, IReadOnlyList<P28PostReturnSelectorCheckpoint> Checkpoints);
public sealed record P28PostReturnSelectorReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, byte InitialSelector013c, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28PostReturnSelectorSequence> Sequences, JsonElement EntryContract)
{
    private IEnumerable<P28PostReturnSelectorCheckpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    public bool HasFailure => !Rows.Any(c => c.ProducerDisposition == "PostReturnSelectorStrict") || Rows.Any(c => c.ProducerDisposition is not ("PostReturnSelectorStrict" or "PostReturnSelectorGateBypass"));
    public string NativePostReturnEntry => Rows.Any(c => c.NativeSteps > 0) ? "ViaRT5688" : "NotRun";
    public string NativePostReturn063ETo064A => Rows.Any(c => c.ProducerCompleted) ? "NativeContinuousControlFlow" : "NotCompleted";
    public string Selector013CProducer => Rows.Any(c => c.ProducerDisposition == "PostReturnSelectorStrict") ? "Validated" : "Partial";
    public string Selector013CInitialSource => "RawSoftwareSnapshot0..3;OnceOnly;InitialGenerationNone";
    public string PerEventSelector013CSource => "None";
    public int Selector013CHostWritesAfterInitialization => 0;
    public int HostPostReturnPcWrite => 0;
    public string Selector013CReader063E => Rows.Any(c => c.NativeSteps > 0) ? "Validated;InitialAndRetainedSourcesCountedSeparately" : "NotRun";
    public string Selector013CWriter064A => Rows.Any(c => c.ProducerWriteObserved) ? "ValidatedNativeByteWriter" : "NotRun";
    public string Selector013CFormula => "((oldSelector+1)&255)&3;AuditedDomain0..3";
    public string Selector013CNextEventHandoff => Rows.Any(c => c.SelectorHandoff == "NativeSelectorHandoffStrict") ? "Validated" : "NotEstablished";
    public string NativeSelectorReader0584 => Rows.Any(c => c.Reader0584Generation is not null) ? "ValidatedRetainedNativeGeneration" : "InitialControlOnlyOrNotRun";
    public string Selector013CWrap3To0 => Rows.Any(c => c.Wrap3To0) ? "Validated" : "NotCovered";
    public string PostReturnStopBefore064C => Rows.Any(c => c.ProducerCompleted) ? "Validated" : "NotReached";
    public string Branch064C => "NotRun";
    public string InterEventScheduling => "ExplicitHarnessSchedule";
    public string RecoveredQuartetScheduler => "NotEstablished";
    public string RecoveredCallerScheduler => "NotEstablished";
    public string Recovered0196Scheduler => "NotEstablished";
    public string RecoveredEcuScheduler => "NotEstablished";
    public string M2adNativeCallReturnRoundTrip => Sequences.Any(s => s.CallReturnCheckpoints.Any(c => c.Disposition == "CallReturnStrict")) ? "Validated" : "Partial";
    public string TimerEvolution => "NotModeled";
    public string TimerContinuation => "NotRun";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string P2ElectricalPins => "NotModeled";
    public string PhysicalOutput => "NotRun";
    public string PhysicalP2Role => "Unknown";
    public string PhysicalPolarity => "Unknown";
    public string ChannelAssignment => "Unknown";
    public string M2tJgt => "Blocked/Unresolved";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public int FirmwareBin => 0;
    public object Summary => new
    {
        Events = Rows.Count(),
        Native063eEntries = Rows.Count(c => c.NativeSteps > 0),
        Native063eReads = Rows.Count(c => c.NativeSteps > 0),
        Native064aWrites = Rows.Count(c => c.ProducerWriteObserved),
        PostReturnCompletions = Rows.Count(c => c.ProducerCompleted),
        InitialSelectorControls = Rows.Count(c => c.SelectorHandoff == "InitialSelectorControl"),
        NativeSelectorGenerations = Rows.Count(c => c.ProducerWriteObserved),
        NextEvent0584NativeGenerationReads = Rows.Count(c => c.Reader0584Generation is not null),
        SameEvent063eNativeGenerationReads = Rows.Count(c => c.Reader063eGeneration is not null),
        StrictGenerationHandoffs = Rows.Count(c => c.SelectorHandoff == "NativeSelectorHandoffStrict"),
        Wrap3To0 = Rows.Count(c => c.Wrap3To0),
        PerSlotStrictHandoffs = Enumerable.Range(0, 4).ToDictionary(i => $"slot{i}", i => Rows.Count(c => c.SelectorHandoff == "NativeSelectorHandoffStrict" && c.SelectedSlot == i)),
        Byte0128Reads = Rows.Count(c => c.NativeSteps >= 4),
        Byte0128Writes = Rows.Count(c => c.NativeSteps >= 4),
        R0Accesses = Rows.Sum(c => (c.NativeSteps >= 2 ? 1 : 0) + (c.NativeSteps >= 5 ? 2 : 0) + (c.NativeSteps >= 6 ? 1 : 0)),
        GateBypass = Rows.Count(c => c.ProducerDisposition == "PostReturnSelectorGateBypass"),
        Partials = Rows.Count(c => c.ProducerDisposition is not ("PostReturnSelectorStrict" or "PostReturnSelectorGateBypass" or "NotRun")),
        NotRun = Rows.Count(c => c.ProducerDisposition == "NotRun"),
        ProducerDispositions = Rows.GroupBy(c => c.ProducerDisposition).ToDictionary(g => g.Key, g => g.Count()),
        HandoffDispositions = Rows.GroupBy(c => c.SelectorHandoff).ToDictionary(g => g.Key, g => g.Count()),
        NativeCompletedWholeCycles = Sequences.Count(s => s.Checkpoints.Count >= 5 && s.Checkpoints.Take(5).All(c => c.ProducerCompleted)),
        PerEventSelectorSourceWrites = 0,
        HostPostReturnPcWrites = 0
    };
}
public static class P28PostReturnSelectorValidator
{
    public const string Operation = "postReturnSelectorHandoff";
    public static object CreateRequest(RomImage image, P28PostReturnSelectorScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28CalRtRoundTripValidator.CreateRequest(image, scenario.BodyReference), JsonDefaults.Create());
        var wire = old.GetProperty("calRtRoundTripHandoff");
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = old.GetProperty("images"),
            scratchPatterns = new[] { 0, 85, 170 },
            allowAssumptions = Array.Empty<string>(),
            postReturnSelectorHandoff = new
            {
                formatVersion = 1,
                initialState = wire.GetProperty("initialState"),
                scenario.InitialSelector013c,
                calls = wire.GetProperty("calls").EnumerateArray().Select(c => new { prefix = c.GetProperty("prefix") }).ToArray(),
                scenario.TraceEventIndexes,
                scenario.P2OutputLatch,
                scenario.Tcon0ArchitecturalSnapshot,
                scenario.TrnsitArchitecturalFlags
            }
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, reusedBodyReference = P28CalRtRoundTripValidator.ExpectedContracts()[0],
        selectorPolicyOverridesHistoricalM2xSourceOnly = "Initial0..3Once;NoPerEventSelector;NoHost013CAfterInit",
        entry = 0x063E, entrySource = "ActualRT5688;NoHostPcWrite", stopBefore = 0x064C, budget = 8,
        codeRanges = new[] { new[] { 0x063E, 0x064C } }, pcs = new[] { 0x063E, 0x0640, 0x0641, 0x0643, 0x0646, 0x0647, 0x0648, 0x064A },
        selector = "RAM013CByte;Read063E;Write064A;Next0584Read;InitialGenerationNone",
        formula = "((old+1)&255)&3;domain0..3", localR0 = "LRB0021/0108;Overwritten0640BeforeUse;FinalOldPlus1",
        history0128 = "OldOR(1<<(oldSelector&1));Bit2AndNeighborsRetained;NoRepair",
        generation = "writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value;IncludesRAMStackP2Control",
        interEventScheduling = "ExplicitHarnessSchedule;RAMProvenanceNotFirmwarePcContinuity",
        partial = "RetainAllNativeWrites;LaterInputsNotRun;No0117Or0128Repair", branch064C = "NotRun",
        otherSelectorWriters = "03D7/0551/15A0NotRun;GenericAliasesUnknown", timerEvolution = "NotModeled", timerContinuation = "NotRun", irqDelivery = "NotInjected", elapsedTime = "None" } });
    public static async Task<P28PostReturnSelectorReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28PostReturnSelectorScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28PostReturnSelectorSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2ae retained selector evidence.", e); }
        }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.InitialSelector013c, scenario.Mutation, offsets, sequences, contract);
    }
    internal static IReadOnlyList<P28PostReturnSelectorSequence> Analyze(RomImage image, P28PostReturnSelectorScenario scenario, JsonElement root, string id)
    {
        var body = scenario.BodyReference; var p2 = new P28P2LatchValidation(body.P2OutputLatch);
        var control = new P28PostP2ControlValidation(P28PostP2ControlScenario.Create(body.P2, body.Tcon0ArchitecturalSnapshot, body.TrnsitArchitecturalFlags));
        var below = new P28BelowSecondP2Validation(); var roundTrip = new P28CalRtRoundTripValidation(); var selector = new P28PostReturnSelectorValidation(scenario.InitialSelector013c);
        var software = P28Word0196AlternateValidator.Analyze(image, body.P2.Software, root, id, p2, control, below, roundTrip, selector);
        return software.Select((s, p) => new P28PostReturnSelectorSequence(id, s.ScratchPattern, s.Checkpoints, p2.Rows[p], control.Rows[p], below.Rows[p], roundTrip.Rows[p], selector.Rows[p])).ToArray();
    }
}
