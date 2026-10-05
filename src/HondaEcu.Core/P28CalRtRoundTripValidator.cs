using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28CalRtRoundTripSequence(string Image, int ScratchPattern,
    IReadOnlyList<P28Word0196AlternateCheckpoint> SoftwareCheckpoints,
    IReadOnlyList<P28P2LatchCheckpoint> FirstP2Checkpoints, IReadOnlyList<P28PostP2ControlCheckpoint> ControlCheckpoints,
    IReadOnlyList<P28BelowSecondP2Checkpoint> BelowCheckpoints, IReadOnlyList<P28CalRtRoundTripCheckpoint> Checkpoints);
public sealed record P28CalRtRoundTripReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28CalRtRoundTripSequence> Sequences, JsonElement EntryContract)
{
    private IEnumerable<P28CalRtRoundTripCheckpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    public bool HasFailure => !Rows.Any(c => c.Disposition == "CallReturnStrict") || Rows.Any(c => c.Disposition is not ("CallReturnStrict" or "CallReturnGateBypass"));
    public string NativeCallReturnRoundTrip => HasFailure ? "Partial" : "Validated";
    public string FrameSource => Rows.Any(c => c.Frame is not null) ? "NativeCAL063B" : "NotEstablished";
    public string NativeCallsite063B => Rows.Any(c => c.Frame is not null) ? "Validated" : "NotRun";
    public string NativeCal063BTo54F5 => NativeCallsite063B;
    public string NativeReturnFrame => Rows.Any(c => c.Frame is not null) ? "Validated" : "NotEstablished";
    public string NativeRt5688To063E => Rows.Any(c => c.SameFrame) ? "Validated" : "NotRun";
    public string SspBalance => Rows.Any(c => c.SameFrame) && Rows.Where(c => c.SameFrame).All(c => c.SspBalanced) ? "Validated" : "NotEstablished";
    public string SecondP2ArchitecturalHandoff => Rows.Any(c => c.Disposition == "CallReturnStrict") ? "Validated" : "Partial";
    public string InterStageScheduleTo063B => "ExplicitHarnessSchedule";
    public string DirectTechnical54F5Schedule => "NotUsedInM2ad";
    public string NativeSubroutineEntry => Rows.Any(c => c.Frame is not null) ? "ViaCAL063B" : "NotRun";
    public string NativeSubroutineReturn => Rows.Any(c => c.SameFrame) ? "ViaRT5688To063E;STOP BEFORE063E" : "NotRun";
    public string EntryClassification => "TechnicalSeededRealCallsiteEntry";
    public string EnclosingCallerPath => "NotRun";
    public string EnclosingIRQFrame => "NotEstablished";
    public string RecoveredCallerScheduler => "NotEstablished";
    public string RecoveredEcuScheduler => "NotEstablished";
    public string Recovered0196Scheduler => "NotEstablished";
    public string TimerEvolution => "NotModeled";
    public string TimerContinuation => "NotRun";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string P2ElectricalPins => "NotModeled";
    public string PhysicalOutput => "NotRun";
    public string HardwareValidation => "NotRun";
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
        CalExecutions = Rows.Count(c => c.Frame is not null),
        NativeFrames = Rows.Count(c => c.Frame is not null),
        StrictRoundTrips = Rows.Count(c => c.Disposition == "CallReturnStrict"),
        GateControls = Rows.Count(c => c.Disposition == "CallReturnGateBypass"),
        RtExecutions = Rows.Count(c => c.SameFrame),
        NativeFrameReads = Rows.Count(c => c.SameFrame),
        Returns063e = Rows.Count(c => c.SameFrame),
        SspBalanced = Rows.Count(c => c.SspBalanced),
        SameFrame = Rows.Count(c => c.SameFrame),
        PerSlotStrict = Enumerable.Range(0, 4).ToDictionary(i => $"slot{i}", i => Sequences.Sum(s => s.Checkpoints.Count(c => c.Disposition == "CallReturnStrict" && s.SoftwareCheckpoints[c.Index].Prefix.SelectedSlot == i))),
        RolbExecutions = Sequences.Sum(s => s.BelowCheckpoints.Count(c => c.NativeSteps > 0)),
        SecondP2Writes = Sequences.Sum(s => s.BelowCheckpoints.Sum(c => c.SecondP2Writes)),
        SameValueSecondP2Writes = Sequences.Sum(s => s.BelowCheckpoints.Count(c => c.SecondP2Writes == 1 && c.SecondP2Old == c.SecondP2New)),
        Dispositions = Rows.GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count())
    };
}
public static class P28CalRtRoundTripValidator
{
    public const string Operation = "calRtRoundTripHandoff";
    public static object CreateRequest(RomImage image, P28CalRtRoundTripScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28Word0196AlternateValidator.CreateRequest(image, scenario.P2.Software), JsonDefaults.Create());
        var wire = old.GetProperty("word0196SoftwareAlternateChain");
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = old.GetProperty("images"),
            scratchPatterns = new[] { 0, 85, 170 },
            allowAssumptions = Array.Empty<string>(),
            calRtRoundTripHandoff = new
            {
                formatVersion = 1,
                initialState = wire.GetProperty("initialState"),
                calls = wire.GetProperty("calls"),
                scenario.TraceEventIndexes,
                scenario.P2OutputLatch,
                scenario.Tcon0ArchitecturalSnapshot,
                scenario.TrnsitArchitecturalFlags
            }
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28BelowSecondP2Validator.ExpectedContracts()[0],
        schedule = new[] { 0x05ED, 0x063B }, scheduleKind = "ExplicitHarnessSchedule;PCOnly", cal = new[] { 0x063B, 3, 0x54F5, 0x063E }, rt = new[] { 0x5688, 1, 0x063E },
        stack = "WordAtOldSSP;ThenSSPMinus2;RTPlus2ThenRead;Even;Retained;NoWrap", frameSource = "NativeCAL063B",
        frameIdentity = "writerPC,eventIndex,stackAddress,width,returnPC,zeroBasedAllNativeEventWriteOrder", flags = "CAL/RT:PSWUnchanged;SF0InternalAMode;NotPSW;RTDoesNotRestoreA/LRB",
        stopBefore = 0x063E, budgetPerCallReturnInstruction = 1, entry = "TechnicalSeededRealCallsiteEntry", enclosingCallerPath = "NotRun", enclosingIRQFrame = "NotEstablished",
        irqDelivery = "NotInjected", recoveredCallerScheduler = "NotEstablished", directTechnical54F5Schedule = "NotUsedInM2ad" } });
    public static async Task<P28CalRtRoundTripReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28CalRtRoundTripScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28CalRtRoundTripSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2ad native caller-frame evidence.", e); }
        }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, offsets, sequences, contract);
    }
    internal static IReadOnlyList<P28CalRtRoundTripSequence> Analyze(RomImage image, P28CalRtRoundTripScenario scenario, JsonElement root, string id)
    {
        var p2 = new P28P2LatchValidation(scenario.P2OutputLatch);
        var control = new P28PostP2ControlValidation(P28PostP2ControlScenario.Create(scenario.P2, scenario.Tcon0ArchitecturalSnapshot, scenario.TrnsitArchitecturalFlags));
        var below = new P28BelowSecondP2Validation(); var roundTrip = new P28CalRtRoundTripValidation();
        var software = P28Word0196AlternateValidator.Analyze(image, scenario.P2.Software, root, id, p2, control, below, roundTrip);
        return software.Select((s, p) => new P28CalRtRoundTripSequence(id, s.ScratchPattern, s.Checkpoints, p2.Rows[p], control.Rows[p], below.Rows[p], roundTrip.Rows[p])).ToArray();
    }
}
