using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28Data0136TailSequence(string Image, int ScratchPattern,
    IReadOnlyList<P28Word0196AlternateCheckpoint> SoftwareCheckpoints,
    IReadOnlyList<P28FallthroughData0136Checkpoint> CallerCheckpoints,
    IReadOnlyList<P28Data0136TailCheckpoint> Checkpoints);
public sealed record P28Data0136TailReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, IReadOnlyList<P28Data0136TailSequence> Sequences, JsonElement EntryContract)
{
    private IEnumerable<P28Data0136TailCheckpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    public bool HasFailure => !Rows.Any(c => c.Disposition == "TailToTimerBoundaryStrict");
    public string Entry5719 => Rows.Any(c => c.NativeEntry5719) ? "NativeContinuationFromM2ag" : "NotRun";
    public string NativeData0136Tail => Rows.Any(c => c.Disposition == "TailLiveInBlocked") ? "PrefixValidated;BlockedBefore5722OnUnowned019BBit2" : "NotEstablished";
    public string SoftwareTailBoundary => Rows.Any(c => c.NativeEntry5719) ? "StopBefore5722;019B.2SemanticOwnerNotEstablished" : "NoTailEntry;ActualUpstreamStopsReported";
    public string Jle574A => "NotRun;EarlierLiveInBlocked";
    public string Jle5750 => "NotRun;EarlierLiveInBlocked";
    public string JleExactSemantics => "PrimaryLE_CF_OR_ZFEstablished;StaticOnlyNotDynamicallyAdmitted";
    public string M2tJgt233A => "Blocked/Unresolved;unchanged";
    public string Data0136FreshGeneration => "NotCreated";
    public string Data0136RetainedContinuity => Rows.Any(c => c.NativeEntry5719) ? "ValidatedAcrossNativePrefix;ReadersNotReached" : "NotRun";
    public string Data0136Reader5782 => "NotRun";
    public string Data0136Reader5787 => "NotRun";
    public string PendingReturnFrame0667 => Rows.Any(c => c.PendingFrame is not null) ? "EstablishedPendingReturn" : "NotEstablished";
    public string NativeProducerReturnTo0667 => "NotRun";
    public string TM3At5793 => "NotRun;NotReached";
    public int NewFrozenPeripheralTailReads => 0;
    public int HostSlotWrites => 0;
    public string TimerEvolution => "NotModeled";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string PhysicalTimestamp => "NotEstablished";
    public string ProducerTo2330SchedulerSeam => "NotEstablished";
    public string RecoveredCallerScheduler => "NotEstablished";
    public string Recovered0196Scheduler => "NotEstablished";
    public string RecoveredEcuScheduler => "NotEstablished";
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
        Entry5719 = Rows.Count(c => c.NativeEntry5719),
        Instructions = Rows.Sum(c => c.TailSteps),
        Cmp5719 = Rows.Count(c => c.TailSteps > 0),
        LiveInBlocked = Rows.Count(c => c.Disposition == "TailLiveInBlocked"),
        GateControls = Rows.Count(c => c.Disposition == "TailLiveInBlockedGateControl"),
        FramePreserved = Rows.Count(c => c.NativeEntry5719 && c.PendingFrame is not null),
        StopBefore5793 = 0,
        JleBlocked = 0,
        Mulb = 0,
        WordMul = 0,
        PsWLBitOperations = 0,
        Jle574a = 0,
        Jle5750 = 0,
        Reader5782 = 0,
        Reader5787 = 0,
        Retained0136Reads = 0,
        Fresh0136Reads = 0,
        TailRamWrites = 0,
        TailPeripheralReads = 0,
        Partials = Rows.Count(c => c.Disposition is "TailExecutionPartial" or "CallerFramePartial" or "CallerSuffixPartial" or "ProducerBodyPartial"),
        NotRun = Rows.Count(c => c.Disposition == "NotRun"),
        Dispositions = Rows.GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count())
    };
}
public static class P28Data0136TailValidator
{
    public const string Operation = "data0136TailToTimerBoundary";
    public static object CreateRequest(RomImage image, P28Data0136TailScenario scenario)
    {
        var n = JsonNode.Parse(JsonSerializer.Serialize(P28FallthroughData0136Validator.CreateRequest(image, scenario.Reference), JsonDefaults.Create()))!;
        var wire = n["fallthroughData0136CallerHandoff"]!.DeepClone(); n.AsObject().Remove("fallthroughData0136CallerHandoff");
        n["operation"] = Operation; n["data0136TailToTimerBoundary"] = wire; return n;
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, reusedBodyReference = P28FallthroughData0136Validator.ExpectedContracts()[0],
        entry = 0x5719, entrySource = "NativeContinuationFromM2ag;NoHostStateChange", codeRanges = new[] { new[] { 0x5719, 0x571F } }, instructionBudget = 2,
        exits = new[] { 0x5722, 0x571F }, liveInBoundary = new[] { 0x5722, 0x19B, 2 }, ownership = "RB05D5OwnsBit0Only;ScratchBit2NotSemanticSource;NoNewFields",
        goalBoundary = 0x5793, timerBoundary = "TM3At5793;NotReached", fresh0136 = "None;RetainedHistory;ReadersNotRun", frame = "Native0664FramePending;NoPopRewriteOrSSPRepair",
        newPeripheralSources = Array.Empty<int>(), tailPeripheralReads = 0, sequenceTerminal = "AllBoundaries;LaterEventsNotRunNoInputsApplied",
        jle = "PrimaryLE_CF_OR_ZF;StaticOnlyPastLiveInBoundary", jgt233a = "BlockedUnchanged", timerEvolution = "NotModeled", irqDelivery = "NotInjected", elapsedTime = "None", physicalRpmAvailable = false } });
    public static async Task<P28Data0136TailReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28Data0136TailScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var source = scenario.Reference; var child = source.Mutation is null ? null : P28PostStoreValidator.Mutate(original, source.Mutation);
        var images = child is null ? new[] { original } : new[] { original, child }; var sequences = new List<P28Data0136TailSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException) { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2ah tail evidence.", e); }
        }
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, sequences, contract);
    }
    internal static IReadOnlyList<P28Data0136TailSequence> Analyze(RomImage image, P28Data0136TailScenario scenario, JsonElement root, string id)
    {
        var body = scenario.Reference.SelectorReference.BodyReference; var p2 = new P28P2LatchValidation(body.P2OutputLatch);
        var control = new P28PostP2ControlValidation(P28PostP2ControlScenario.Create(body.P2, body.Tcon0ArchitecturalSnapshot, body.TrnsitArchitecturalFlags));
        var below = new P28BelowSecondP2Validation(); var roundTrip = new P28CalRtRoundTripValidation(); var selector = new P28PostReturnSelectorValidation(scenario.Reference.InitialSelector013c);
        var caller = new P28FallthroughData0136Validation(scenario.Reference); var tail = new P28Data0136TailValidation();
        var software = P28Word0196AlternateValidator.Analyze(image, body.P2.Software, root, id, p2, control, below, roundTrip, selector, caller, tail);
        return software.Select((s, p) => new P28Data0136TailSequence(id, s.ScratchPattern, s.Checkpoints, caller.Rows[p], tail.Rows[p])).ToArray();
    }
}
