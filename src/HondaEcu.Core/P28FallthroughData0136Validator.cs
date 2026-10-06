using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28FallthroughData0136Sequence(string Image, int ScratchPattern,
    IReadOnlyList<P28Word0196AlternateCheckpoint> SoftwareCheckpoints,
    IReadOnlyList<P28PostReturnSelectorCheckpoint> SelectorCheckpoints,
    IReadOnlyList<P28FallthroughData0136Checkpoint> Checkpoints);
public sealed record P28FallthroughData0136Report(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, IReadOnlyList<P28FallthroughData0136Sequence> Sequences, JsonElement EntryContract)
{
    private IEnumerable<P28FallthroughData0136Checkpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    public bool HasFailure => !Rows.Any(c => c.Disposition == "NativeFallthroughCallerProducerNoWriteStrict") || Rows.Any(c => c.Disposition is not ("NativeFallthroughCallerProducerNoWriteStrict" or "GateBypassFallthroughProducerControl" or "CallerTrnsitBoundaryControl" or "CallerCalSkippedControl" or "ProducerEntryBlockedControl" or "NotRun"));
    public string M2afPrimaryTakenRoute => "Blocked;unchanged";
    public string Entry064C => Rows.Any(c => c.NativeEntry064c) ? "NativeContinuationFromM2ae" : "NotRun";
    public string Branch064C => Rows.Any(c => c.Disposition == "NativeFallthroughCallerProducerNoWriteStrict") ? "ValidatedFallthroughOnStrictCore;TakenAAControlSeparate" : "NotEstablished";
    public string FallthroughCallerRoute => Rows.Any(c => c.Disposition == "NativeFallthroughCallerProducerNoWriteStrict") ? "Validated;ActualPathsReportedSeparately" : "NotEstablished";
    public string FallthroughTrnsitAccess => "NotRunOnStrictCore;ControlsStopBefore0657";
    public string ProducerMode => "Retained011F.2Mode0OnStrictCore;NoSeparateModeInput";
    public string NativeCal0664To56BE => Rows.Any(c => c.Disposition == "NativeFallthroughCallerProducerNoWriteStrict") ? "Validated" : "NotEstablished";
    public string ProducerEntry56BE => NativeCal0664To56BE == "Validated" ? "ViaNativeCAL0664" : "NotEstablished";
    public string TechnicalSeededEntry56BE => "NotUsedInM2ag";
    public string NativeProducerCallFrame => Rows.Any(c => c.NativeCalExecuted) ? "EstablishedPendingReturn" : "NotEstablished";
    public string NativeProducerReturnTo0667 => "NotRun";
    public string ProducerBoundedStopBefore5719 => Rows.Any(c => c.ProducerCompleted) ? "Validated" : "NotRun";
    public string ProducerFirstObservationNoWrite => Rows.Any(c => c.Disposition == "NativeFallthroughCallerProducerNoWriteStrict") ? "Validated" : "NotEstablished";
    public string Data0136FreshGeneration => "NotCreated;NotReachedUnderRetained0128.3Clear";
    public string Data0136Writer5707 => "NotRun";
    public string Data0136Writer56F3 => "NotRun";
    public string Data0136Reader570E => "NotRun";
    public string Slot00A2 => "RetainedHistory0OnStrictCore;ControlsNotNormalized";
    public int HostSlotWrites => 0;
    public string FrozenTmr2Observation => "ExplicitReadOnlyFrozenWord;NoTimeAdvance";
    public string FrozenIrqhObservation => "ExplicitReadOnlyFrozenByteOnlyWhenConsumed";
    public string Tcon2 => "UnprovidedDisabled;NativeReads0";
    public string TimerEvolution => "NotModeled";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string PhysicalTimestamp => "NotEstablished";
    public string RecoveredCallerScheduler => "NotEstablished";
    public string Recovered0196Scheduler => "NotEstablished";
    public string RecoveredEcuScheduler => "NotEstablished";
    public string ProducerTo2330SchedulerSeam => "NotEstablished";
    public string EnclosingIrqFrame => "NotEstablished";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public int FirmwareBin => 0;
    public object Summary => new
    {
        Events = Rows.Count(),
        Entry064cNative = Rows.Count(c => c.NativeEntry064c),
        Branch064cFallthrough = Rows.Count(c => c.Actual.GetProperty("caller").ValueKind == JsonValueKind.Object && c.Actual.GetProperty("caller").GetProperty("suffix").GetProperty("stage").GetProperty("events").EnumerateArray().Any(e => e[0].GetInt32() == 0x064C && e[1].GetInt32() == 0x064F)),
        Via011b7 = Rows.Count(c => c.CallerRoute == "FallthroughDirectVia011B7"),
        Via012a0 = Rows.Count(c => c.CallerRoute == "FallthroughVia012A0"),
        Executions0652 = Rows.Count(c => c.Actual.GetProperty("caller").ValueKind == JsonValueKind.Object && c.Actual.GetProperty("caller").GetProperty("suffix").GetProperty("stage").GetProperty("events").EnumerateArray().Any(e => e[0].GetInt32() == 0x0652)),
        Taken0655 = Rows.Count(c => c.Actual.GetProperty("caller").ValueKind == JsonValueKind.Object && c.Actual.GetProperty("caller").GetProperty("suffix").GetProperty("stage").GetProperty("events").EnumerateArray().Any(e => e[0].GetInt32() == 0x0655 && e[1].GetInt32() == 0x065F)),
        Executions065f = Rows.Count(c => c.Actual.GetProperty("caller").ValueKind == JsonValueKind.Object && c.Actual.GetProperty("caller").GetProperty("suffix").GetProperty("stage").GetProperty("events").EnumerateArray().Any(e => e[0].GetInt32() == 0x065F)),
        TrnsitBoundaryControls = Rows.Count(c => c.Disposition == "CallerTrnsitBoundaryControl"),
        CalSkippedControls = Rows.Count(c => c.Disposition == "CallerCalSkippedControl"),
        NativeCal0664 = Rows.Count(c => c.NativeCalExecuted),
        Native56beEntries = Rows.Count(c => c.NativeCalExecuted),
        NativeFrames0667 = Rows.Count(c => c.NativeCalExecuted),
        Tmr2Reads = Rows.Sum(c => c.Tmr2Reads),
        IrqhReads = Rows.Sum(c => c.IrqhReads),
        Tcon2Reads = Rows.Sum(c => c.Tcon2Reads),
        NoWriteCompletions = Rows.Count(c => c.ProducerCompleted),
        StrictNoWriteCompletions = Rows.Count(c => c.Disposition == "NativeFallthroughCallerProducerNoWriteStrict"),
        Writes00ee = Rows.Sum(c => c.NativeWrites.Count(w => w.WriterPc == 0x5714)),
        Clears00ae = Rows.Sum(c => c.NativeWrites.Count(w => w.WriterPc == 0x5716)),
        Writes0128Bit3 = Rows.Sum(c => c.NativeWrites.Count(w => w.WriterPc == 0x56D4)),
        Fresh0136Writers = 0,
        Writer5707 = 0,
        Writer56f3 = 0,
        Reader570e = 0,
        CoreStrictTrnsitAccesses = 0,
        Partials = Rows.Count(c => c.Disposition is "CallerSuffixPartial" or "ProducerBodyPartial" or "CallerFramePartial" or "UpstreamPartial"),
        NotRun = Rows.Count(c => c.Disposition == "NotRun"),
        Dispositions = Rows.GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count())
    };
}
public static class P28FallthroughData0136Validator
{
    public const string Operation = "fallthroughData0136CallerHandoff";
    public static object CreateRequest(RomImage image, P28FallthroughData0136Scenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28PostReturnSelectorValidator.CreateRequest(image, scenario.SelectorReference), JsonDefaults.Create());
        var wire = old.GetProperty("postReturnSelectorHandoff");
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = old.GetProperty("images"),
            scratchPatterns = new[] { 0, 85, 170 },
            allowAssumptions = Array.Empty<string>(),
            fallthroughData0136CallerHandoff = new
            {
                formatVersion = 1,
                initialState = wire.GetProperty("initialState"),
                scenario.InitialSelector013c,
                calls = wire.GetProperty("calls").EnumerateArray().Select((c, i) => new { prefix = c.GetProperty("prefix"), producerObservation = scenario.Calls[i].ProducerObservation }).ToArray(),
                scenario.TraceEventIndexes,
                scenario.P2OutputLatch,
                scenario.Tcon0ArchitecturalSnapshot,
                scenario.TrnsitArchitecturalFlags
            }
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, reusedBodyReference = P28PostReturnSelectorValidator.ExpectedContracts()[0],
        entry = 0x064C, entrySource = "NativeContinuationFromM2ae;NoHostPcOrABIWrite", callerCodeRanges = new[] { new[] { 0x064C, 0x0657 }, new[] { 0x065F, 0x0667 } }, callerBudget = 7,
        callerExits = new[] { 0x56BE, 0x0657, 0x0667 }, cal = new[] { 0x0664, 3, 0x56BE, 0x0667 }, callerGates = "OneRetained011FByte;Existing011B7;Old012A0/3ZF;NoRepair",
        producerCodeRanges = new[] { new[] { 0x56BE, 0x56C3 }, new[] { 0x56C5, 0x56D9 }, new[] { 0x5713, 0x5719 } }, producerBudget = 128, stopBefore = 0x5719,
        producerAdmission = "Mode0;RetainedSlot0;Old0128Bit3Clear;NoTechnicalEntry", frozenSources = "TMR2WordAlways;IRQHByteIffTMR2Bit15Clear;TCON2Unavailable",
        chronology = "0RAM/1P2/2Control/3FrozenCapture,PC,address,width,write,value;AllNativeWritesOrdinal", frame = "Native0664AtOldSSP;Return0667;PendingAt5719;NoPopOrReseed",
        sequenceTerminal = "AfterCallerBoundary;LaterEventsNotRunNoInputsApplied", m2afPrimaryTakenRoute = "BlockedUnchanged;AAControlNotCallerSuccess",
        timerEvolution = "NotModeled", irqDelivery = "NotInjected", elapsedTime = "None", producerTo2330SchedulerSeam = "NotEstablished", physicalRpmAvailable = false } });
    public static async Task<P28FallthroughData0136Report> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28FallthroughData0136Scenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28FallthroughData0136Sequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2ag native caller/NoWrite evidence.", e); }
        }
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, sequences, contract);
    }
    internal static IReadOnlyList<P28FallthroughData0136Sequence> Analyze(RomImage image, P28FallthroughData0136Scenario scenario, JsonElement root, string id)
    {
        var body = scenario.SelectorReference.BodyReference; var p2 = new P28P2LatchValidation(body.P2OutputLatch);
        var control = new P28PostP2ControlValidation(P28PostP2ControlScenario.Create(body.P2, body.Tcon0ArchitecturalSnapshot, body.TrnsitArchitecturalFlags));
        var below = new P28BelowSecondP2Validation(); var roundTrip = new P28CalRtRoundTripValidation(); var selector = new P28PostReturnSelectorValidation(scenario.InitialSelector013c);
        var caller = new P28FallthroughData0136Validation(scenario);
        var software = P28Word0196AlternateValidator.Analyze(image, body.P2.Software, root, id, p2, control, below, roundTrip, selector, caller);
        return software.Select((s, p) => new P28FallthroughData0136Sequence(id, s.ScratchPattern, s.Checkpoints, selector.Rows[p], caller.Rows[p])).ToArray();
    }
}
