using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28P2LatchSequence(string Image, int ScratchPattern, IReadOnlyList<P28Word0196AlternateCheckpoint> SoftwareCheckpoints, IReadOnlyList<P28P2LatchCheckpoint> Checkpoints);
public sealed record P28P2LatchComparison(int ScratchPattern, int Index, int? Value0196A, int? Value0196B, int LatchA, int LatchB, string Effect);
public sealed record P28P2LatchReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28P2LatchSequence> Sequences,
    IReadOnlyList<P28P2LatchComparison> Comparisons, JsonElement EntryContract)
{
    private IEnumerable<P28P2LatchCheckpoint> Rows => Sequences.SelectMany(s => s.Checkpoints);
    private IEnumerable<P28Word0196AlternateCheckpoint> Software => Sequences.SelectMany(s => s.SoftwareCheckpoints);
    public bool HasFailure => Rows.Any(c => c.Disposition is not ("QuartetDerivedP2LatchStrict" or "GateBypassP2LatchControl"));
    public string P2ArchitecturalSemantics => "EstablishedForReviewedAllOutputPrimaryPortPrecondition";
    public string P2ArchitecturalLatchHandoff => !HasFailure && Rows.Any(c => c.Disposition == "QuartetDerivedP2LatchStrict") ? "Validated" : "Partial";
    public object Summary => new
    {
        Events = Rows.Count(),
        ArchitecturalReads = Rows.Count(c => c.InstructionPc is not null && c.Generation?.EventIndex == c.Index),
        ArchitecturalWrites = Rows.Count(c => c.InstructionPc is not null && c.Generation?.EventIndex == c.Index),
        Instruction5596 = Rows.Count(c => c.Generation?.EventIndex == c.Index && c.InstructionPc == 0x5596),
        Instruction55c5 = Rows.Count(c => c.Generation?.EventIndex == c.Index && c.InstructionPc == 0x55C5),
        SameValueWrites = Rows.Count(c => c.InstructionPc is not null && c.Generation?.EventIndex == c.Index && c.NewLatch == c.OldLatch),
        RetainedLatchEvents = Rows.Count(c => c.InstructionPc is not null && c.IncomingGeneration is not null),
        Strict = Rows.Count(c => c.Disposition == "QuartetDerivedP2LatchStrict"),
        GateBypassControls = Rows.Count(c => c.Disposition == "GateBypassP2LatchControl"),
        Below = Software.Count(c => c.CompareDomain == "BelowImmediate"),
        Equal = Software.Count(c => c.CompareDomain == "EqualImmediate"),
        Above = Software.Count(c => c.CompareDomain == "AboveImmediate"),
        PerSlot = Enumerable.Range(0, 4).ToDictionary(i => $"slot{i}", i => Software.Count(c => c.Disposition == "QuartetDerivedP2LatchStrict" && c.Prefix.SelectedSlot == i)),
        AbComparisons = Comparisons.Count,
        P2LatchDivergences = Comparisons.Count(c => c.Effect == "P2LatchDivergence"),
        Dispositions = Rows.GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count())
    };
    public string InitialLatchPolicy => "RawArchitecturalP2LatchSnapshot;StartupProducerNotRun;OnceOnly";
    public string Configuration => "ReviewedStartupPrecondition;P2IO=FF;P2SFImplementedBits=0;NotFullBoot";
    public string P2ElectricalPins => "NotModeled";
    public string PhysicalOutput => "NotRun";
    public string HardwareValidation => "NotRun";
    public string PhysicalP2Role => "Unknown";
    public string PhysicalPolarity => "Unknown";
    public string ChannelAssignment => "Unknown";
    public string TimerContinuation => "NotRun";
    public string Recovered0196Scheduler => "NotEstablished";
    public string IrqDelivery => "NotInjected";
    public string ElapsedTime => "None";
    public string M2zWord0196AlternateSoftwareChain => "Validated;bounded software contract unchanged";
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
public static class P28P2LatchValidator
{
    public const string Operation = "p2OutputLatchHandoff";
    public static object CreateRequest(RomImage image, P28P2LatchScenario scenario)
    {
        var old = JsonSerializer.SerializeToElement(P28Word0196AlternateValidator.CreateRequest(image, scenario.Software), JsonDefaults.Create());
        var wire = old.GetProperty("word0196SoftwareAlternateChain");
        return new { protocolVersion = 1, operation = Operation, images = old.GetProperty("images"), scratchPatterns = new[] { 0, 85, 170 }, allowAssumptions = Array.Empty<string>(), p2OutputLatchHandoff = new { formatVersion = 1, initialState = wire.GetProperty("initialState"), calls = wire.GetProperty("calls"), scenario.TraceEventIndexes, scenario.P2OutputLatch } };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28Word0196AlternateValidator.ExpectedContracts()[0],
        p2Address = 0x24, width = 8, p2InstructionPcs = new[] { 0x5596, 0x55C5 }, stopBefore = new[] { 0x5599, 0x55C8 }, budget = 1,
        mode = "ReviewedStartupPrecondition;P2IO=FF;P2SFImplementedBits=0", initialLatch = "RawArchitecturalP2LatchSnapshot;StartupProducerNotRun;OnceOnly",
        journal = "SeparatePeripheral;PC,address,width,write,value;ReadBeforeWrite", generation = "writerPC,eventIndex,zeroBasedAllNativeEventWriteOrder,value;SameValueFresh",
        electricalPins = "NotModeled", physicalOutput = "NotRun", timerContinuation = "NotRun" } });
    public static async Task<P28P2LatchReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28P2LatchScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation); var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28P2LatchSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var result = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, result.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = result.Response.GetProperty("entryContracts").Clone(); version = result.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2aa architectural latch evidence.", e); }
        }
        var comparisons = new List<P28P2LatchComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var sa = sequences[p].SoftwareCheckpoints[i]; var sb = sequences[p + 3].SoftwareCheckpoints[i];
                    var complete = a.Disposition == "QuartetDerivedP2LatchStrict" && b.Disposition == "QuartetDerivedP2LatchStrict";
                    comparisons.Add(new(sequences[p].ScratchPattern, i, sa.CmpLeft, sb.CmpLeft, a.NewLatch, b.NewLatch,
                        !complete ? "IncompleteOrGateBypass" : a.NewLatch != b.NewLatch ? "P2LatchDivergence" : $"EqualLatch;0196A={sa.CmpLeft};0196B={sb.CmpLeft};Pc={a.InstructionPc:X4};AlA={a.SourceAl:X2};AlB={b.SourceAl:X2};OldA={a.OldLatch:X2};OldB={b.OldLatch:X2};ByteANDORModelExplainsMasking"));
                }
        IReadOnlyList<int> offsets = child is null ? [] : Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, offsets, sequences, comparisons, contract);
    }
    internal static IReadOnlyList<P28P2LatchSequence> Analyze(RomImage image, P28P2LatchScenario scenario, JsonElement root, string id)
    {
        var own = new P28P2LatchValidation(scenario.P2OutputLatch);
        var software = P28Word0196AlternateValidator.Analyze(image, scenario.Software, root, id, own);
        return software.Select((s, p) => new P28P2LatchSequence(id, s.ScratchPattern, s.Checkpoints, own.Rows[p])).ToArray();
    }
}
