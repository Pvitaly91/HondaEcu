using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28BelowSecondP2Sequence(string Image, int ScratchPattern, IReadOnlyList<P28Word0196AlternateCheckpoint> SoftwareCheckpoints,
    IReadOnlyList<P28P2LatchCheckpoint> FirstP2Checkpoints, IReadOnlyList<P28PostP2ControlCheckpoint> ControlCheckpoints, IReadOnlyList<P28BelowSecondP2Checkpoint> Checkpoints);
public sealed record P28BelowSecondP2Report(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28BelowSecondP2Sequence> Sequences, JsonElement EntryContract)
{
    private IEnumerable<P28BelowSecondP2Checkpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    public bool HasFailure => !Rows.Any(c => c.Disposition == "BelowSecondP2Strict") || Rows.Any(c => c.Disposition is not ("BelowSecondP2Strict" or "BelowSecondP2GateBypass" or "PostP2ControlStrict" or "PostP2ControlGateBypass"));
    public string SecondP2ArchitecturalHandoff => !HasFailure && Rows.Any(c => c.Disposition == "BelowSecondP2Strict") ? "Validated" : "Partial";
    public string RolbAExactSemantics => "Established;33/DD0;Primary3-119;CFOnly;AHRetained";
    public string BelowContinuation => Rows.Any(c => c.NativeSteps == 18) ? "NativeContinuousControlFlow" : "NotCompleted";
    public object Summary => new
    {
        Events = Rows.Count(),
        Strict = Rows.Count(c => c.Disposition == "BelowSecondP2Strict"),
        GateBypassControls = Rows.Count(c => c.Disposition == "BelowSecondP2GateBypass"),
        RolbExecutions = Rows.Count(c => c.NativeSteps > 0),
        Cf0 = Rows.Count(c => c.NativeSteps > 0 && (c.IncomingPsw & 0x8000) == 0),
        Cf1 = Rows.Count(c => c.NativeSteps > 0 && (c.IncomingPsw & 0x8000) != 0),
        ZeroRolResults = Rows.Count(c => c.OutgoingRolA is { } a && (a & 255) == 0),
        NonzeroRolResults = Rows.Count(c => c.OutgoingRolA is { } a && (a & 255) != 0),
        SoftwareCompletions = Rows.Count(c => c.NativeSteps == 18),
        SecondP2Reads = Rows.Sum(c => c.SecondP2Reads),
        SecondP2Writes = Rows.Sum(c => c.SecondP2Writes),
        SameValueSecondP2Writes = Rows.Count(c => c.SecondP2Writes == 1 && c.SecondP2Old == c.SecondP2New),
        RetainedG1ToG2 = Rows.Count(c => c.OutgoingP2Generation is not null),
        RamWrites = Rows.Sum(c => c.RamWrites),
        Tcon0RetainedReads = Rows.Sum(c => c.Tcon0Reads),
        PerSlotStrict = Enumerable.Range(0, 4).ToDictionary(i => $"slot{i}", i => Rows.Count(c => c.Disposition == "BelowSecondP2Strict" && c.SelectedSlot == i)),
        Dispositions = Rows.GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count())
    };
    public string FirstP2ArchitecturalHandoff => "Validated;M2aaBoundedDomain";
    public string Tcon0ArchitecturalSemantics => "ValidatedInM2abBoundedDomain";
    public string TimerEvolution => "NotModeled";
    public string TimerContinuation => "NotRun";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string ReturnFrame => "NotEstablished;NotNeededForBoundedResult;RT5688NotRun";
    public string P2ElectricalPins => "NotModeled";
    public string PhysicalOutput => "NotRun";
    public string HardwareValidation => "NotRun";
    public string PhysicalP2Role => "Unknown";
    public string PhysicalPolarity => "Unknown";
    public string ChannelAssignment => "Unknown";
    public string Recovered0196Scheduler => "NotEstablished";
    public string RecoveredEcuScheduler => "NotEstablished";
    public string InterStageScheduleTo54F5 => "ExplicitHarnessSchedule";
    public string M2abPostP2ControlRegisterHandoff => "Validated;bounded contract unchanged";
    public string M2aaP2ArchitecturalLatchHandoff => "Validated;bounded contract unchanged";
    public string M2zWord0196AlternateSoftwareChain => "Validated;bounded contract unchanged";
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
    public int Binding => 0;
    public int Compensation => 0;
    public int Exportplan => 0;
    public int Receipt => 0;
    public int Token => 0;
}
public static class P28BelowSecondP2Validator
{
    public const string Operation = "belowSecondP2Handoff";
    public static object CreateRequest(RomImage image, P28BelowSecondP2Scenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28PostP2ControlValidator.CreateRequest(image, P28PostP2ControlScenario.Create(scenario.P2, scenario.Tcon0ArchitecturalSnapshot, scenario.TrnsitArchitecturalFlags)), JsonDefaults.Create());
        return new { protocolVersion = 1, operation = Operation, images = old.GetProperty("images"), scratchPatterns = new[] { 0, 85, 170 }, allowAssumptions = Array.Empty<string>(), belowSecondP2Handoff = old.GetProperty("postP2ControlHandoff") };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28PostP2ControlValidator.ExpectedContracts()[0],
        entry = "Actual55CFNext55D2;NoHostJump", stopBefore = 0x5688, budget = 18,
        codeRanges = new[] { new[] { 0x55D2, 0x55DD }, new[] { 0x562C, 0x5636 }, new[] { 0x565D, 0x5663 }, new[] { 0x5671, 0x5675 }, new[] { 0x567E, 0x5688 } },
        rolbA = "33/DD0;AL=(AL<<1)|incomingCF;AHretained;CF=oldAL7;OtherPSWRetained", p2InstructionPc = 0x5682, tcon0InstructionPc = 0x55D5, newExternalSources = 0,
        belowContinuation = "NativeContinuousControlFlow", returnFrame = "NotEstablished;RTNotRun", chronology = "0RAM/1P2/2Control,PC,address,width,write,value;NativeOnly;AllWritesOrdinal",
        timerEvolution = "NotModeled", timerContinuation = "NotRun", irqDelivery = "NotInjected", elapsedTime = "None", physicalOutput = "NotRun" } });
    public static async Task<P28BelowSecondP2Report> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28BelowSecondP2Scenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28BelowSecondP2Sequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2ac below continuation evidence.", e); }
        }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, offsets, sequences, contract);
    }
    internal static IReadOnlyList<P28BelowSecondP2Sequence> Analyze(RomImage image, P28BelowSecondP2Scenario scenario, JsonElement root, string id)
    {
        var p2 = new P28P2LatchValidation(scenario.P2OutputLatch);
        var control = new P28PostP2ControlValidation(P28PostP2ControlScenario.Create(scenario.P2, scenario.Tcon0ArchitecturalSnapshot, scenario.TrnsitArchitecturalFlags));
        var below = new P28BelowSecondP2Validation();
        var software = P28Word0196AlternateValidator.Analyze(image, scenario.P2.Software, root, id, p2, control, below);
        return software.Select((s, p) => new P28BelowSecondP2Sequence(id, s.ScratchPattern, s.Checkpoints, p2.Rows[p], control.Rows[p], below.Rows[p])).ToArray();
    }
}
