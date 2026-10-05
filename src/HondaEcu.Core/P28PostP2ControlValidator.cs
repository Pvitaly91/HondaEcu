using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28PostP2ControlSequence(string Image, int ScratchPattern, IReadOnlyList<P28Word0196AlternateCheckpoint> SoftwareCheckpoints, IReadOnlyList<P28P2LatchCheckpoint> P2Checkpoints, IReadOnlyList<P28PostP2ControlCheckpoint> Checkpoints);
public sealed record P28PostP2ControlComparison(int ScratchPattern, int Index, int? Value0196A, int? Value0196B, int Tcon0A, int Tcon0B, int TrnsitFlagsA, int TrnsitFlagsB, string Effect);
public sealed record P28PostP2ControlReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28PostP2ControlSequence> Sequences,
    IReadOnlyList<P28PostP2ControlComparison> Comparisons, JsonElement EntryContract)
{
    private IEnumerable<P28PostP2ControlCheckpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    private IEnumerable<P28Word0196AlternateCheckpoint> Software => Sequences.SelectMany(s => s.SoftwareCheckpoints);
    public bool HasFailure => Rows.Any(c => c.Disposition is not ("PostP2ControlStrict" or "PostP2ControlGateBypass"));
    public string PostP2ControlRegisterHandoff => !HasFailure && Rows.Any(c => c.Disposition == "PostP2ControlStrict") ? "Validated" : "Partial";
    public string TrnsitArchitecturalSemantics => "EstablishedForFourReadableWritableFlags;NonexistentHighBitsRead1;ExternalEdgesNotInjected";
    public string Tcon0ArchitecturalSemantics => "EstablishedForStoppedRealtimeOutputSnapshot83/87/8B/8F;TR0OUTBit2Only";
    public string P2LatchStatus => Sequences.SelectMany(s => s.P2Checkpoints).All(c => c.Disposition is "QuartetDerivedP2LatchStrict" or "GateBypassP2LatchControl") ? "Validated" : "Partial";
    public string P2ArchitecturalLatchHandoff => P2LatchStatus;
    public string ControlRegisterStatus => PostP2ControlRegisterHandoff;
    public string TimerEvolutionStatus => "NotModeled";
    public string PhysicalStatus => "NotRun";
    public object Summary => new
    {
        Events = Rows.Count(),
        Strict = Rows.Count(c => c.Disposition == "PostP2ControlStrict"),
        GateBypassControls = Rows.Count(c => c.Disposition == "PostP2ControlGateBypass"),
        TrnsitInstructions = Rows.Count(c => c.NativeControlWrites != 0 && c.InstructionPc == 0x5599),
        Tcon0Instructions = Rows.Count(c => c.NativeControlWrites != 0 && c.InstructionPc == 0x55C8),
        ControlReads = Rows.Sum(c => c.NativeControlReads),
        ControlWrites = Rows.Sum(c => c.NativeControlWrites),
        CommandInvocations = 0,
        SameValueWrites = Rows.Count(c => c.NativeControlWrites != 0 && (c.InstructionPc == 0x5599 ? c.TrnsitFlagsBefore == c.TrnsitFlagsAfter : c.Tcon0Before == c.Tcon0After)),
        Below = Software.Count(c => c.CompareDomain == "BelowImmediate"),
        Equal = Software.Count(c => c.CompareDomain == "EqualImmediate"),
        Above = Software.Count(c => c.CompareDomain == "AboveImmediate"),
        PerSlot = Enumerable.Range(0, 4).ToDictionary(i => $"slot{i}", i => Software.Count(c => c.Disposition == "PostP2ControlStrict" && c.Prefix.SelectedSlot == i)),
        AbComparisons = Comparisons.Count,
        ArchitecturalControlDivergences = Comparisons.Count(c => c.Effect == "ArchitecturalControlDivergence"),
        Dispositions = Rows.GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count())
    };
    public string TimerEvolution => "NotModeled";
    public string TimerContinuation => "NotRun";
    public string IrqDelivery => "NotInjected";
    public string PendingInterrupt => "NotModeled";
    public string ElapsedTime => "None";
    public string PhysicalOutput => "NotRun";
    public string HardwareValidation => "NotRun";
    public string P2ElectricalPins => "NotModeled";
    public string PhysicalP2Role => "Unknown";
    public string PhysicalPolarity => "Unknown";
    public string ChannelAssignment => "Unknown";
    public string Recovered0196Scheduler => "NotEstablished";
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
}
public static class P28PostP2ControlValidator
{
    public const string Operation = "postP2ControlHandoff";
    public static object CreateRequest(RomImage image, P28PostP2ControlScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28P2LatchValidator.CreateRequest(image, scenario.P2), JsonDefaults.Create()); var wire = old.GetProperty("p2OutputLatchHandoff");
        return new { protocolVersion = 1, operation = Operation, images = old.GetProperty("images"), scratchPatterns = new[] { 0, 85, 170 }, allowAssumptions = Array.Empty<string>(), postP2ControlHandoff = new { formatVersion = 1, initialState = wire.GetProperty("initialState"), calls = wire.GetProperty("calls"), scenario.TraceEventIndexes, scenario.P2OutputLatch, scenario.Tcon0ArchitecturalSnapshot, scenario.TrnsitArchitecturalFlags } };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28P2LatchValidator.ExpectedContracts()[0],
        controlAddresses = new[] { 0x40, 0x46 }, width = 8, entryPcs = new[] { 0x5599, 0x55C8 }, stopBefore = new[] { 0x559D, 0x55D2 }, budget = 4,
        tcon0Domain = "83,87,8B,8F;RealtimeOutput;RUN0;Clock100;NoCompareTransfer", trnsitDomain = "Flags0..15;NonexistentBitsRead1;NoExternalEdges",
        initialSource = "RawArchitecturalSnapshot;OnceOnly;NotResetOrBoot", scope = "ExactControlInstructionPCAndAddress;NativeOnly;NoHostWrite",
        journal = "SeparateControl;PC,address,width,write,value;NotRAMOrP2", generation = "writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value;SameValueFresh",
        timerEvolution = "NotModeled", timerContinuation = "NotRun", irqDelivery = "NotInjected", elapsedTime = "None", physicalOutput = "NotRun" } });
    public static async Task<P28PostP2ControlReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28PostP2ControlScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28PostP2ControlSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2ab post-P2 architectural control evidence.", e); }
        }
        var comparisons = new List<P28PostP2ControlComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var sa = sequences[p].SoftwareCheckpoints[i]; var sb = sequences[p + 3].SoftwareCheckpoints[i];
                    var complete = a.Disposition == "PostP2ControlStrict" && b.Disposition == "PostP2ControlStrict";
                    comparisons.Add(new(sequences[p].ScratchPattern, i, sa.CmpLeft, sb.CmpLeft, a.Tcon0After, b.Tcon0After, a.TrnsitFlagsAfter, b.TrnsitFlagsAfter,
                        !complete ? "IncompleteOrGateBypass" : a.Tcon0After != b.Tcon0After || a.TrnsitFlagsAfter != b.TrnsitFlagsAfter ? "ArchitecturalControlDivergence" : $"EqualControl;0196A={sa.CmpLeft};0196B={sb.CmpLeft};PcA={a.InstructionPc:X4};PcB={b.InstructionPc:X4};SameBranchAndBitOperation;NoPhysicalDivergenceClaim"));
                }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, offsets, sequences, comparisons, contract);
    }
    internal static IReadOnlyList<P28PostP2ControlSequence> Analyze(RomImage image, P28PostP2ControlScenario scenario, JsonElement root, string id)
    {
        var p2 = new P28P2LatchValidation(scenario.P2OutputLatch); var control = new P28PostP2ControlValidation(scenario);
        var software = P28Word0196AlternateValidator.Analyze(image, scenario.P2.Software, root, id, p2, control);
        return software.Select((s, p) => new P28PostP2ControlSequence(id, s.ScratchPattern, s.Checkpoints, p2.Rows[p], control.Rows[p])).ToArray();
    }
}
