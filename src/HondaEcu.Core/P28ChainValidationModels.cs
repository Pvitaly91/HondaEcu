namespace HondaEcu.Core;

public sealed record P28ChainArchitecture(ushort Pc, ushort Accumulator, ushort Lrb, ushort Psw, ushort Ssp,
    IReadOnlyList<byte> Banks, IReadOnlyList<byte> Pointing, ushort StackWord);
public sealed record P28ChainObservedStage(string Id, int Status, P28ChainState StateBefore, P28ChainState StateAtEntry, P28ChainState StateAfter,
    P28ChainArchitecture ArchitectureBefore, P28ChainArchitecture ArchitectureAtEntry, P28ChainArchitecture ArchitectureAfter,
    P28AcquisitionStageResult? Execution, IReadOnlyList<int[]> NativeWrites, IReadOnlyList<int[]> PeripheralAccesses,
    IReadOnlyList<int[]> GateEvents, IReadOnlyList<int[]> TickRuns, IReadOnlyList<string> CumulativeAssumptions);
public sealed record P28ChainStageComparison(P28ChainObservedStage Actual, P28ChainExpectedStage Expected, string Validation,
    IReadOnlyList<P28VtecGate> ActualGates, IReadOnlyList<P28VtecThresholdSelection> ActualThresholds, IReadOnlyList<string> Differences);
public sealed record P28ChainCheckpoint(int Index, P28ChainEvent Input, P28ChainState StateBefore, P28ChainState StateAfterInputs,
    IReadOnlyList<int[]> CallerWrites, IReadOnlyList<P28ChainStageComparison> Stages, P28ChainState StateAfter,
    bool? SoftwareRequest, bool? RequestMirror, bool? SelectionStatus, int EverWrittenMask, IReadOnlyList<int> SlotWriteCounts,
    IReadOnlyList<string> CumulativeAssumptions, IReadOnlyList<string> Differences);
public sealed record P28ChainStageCounts(int Requested, int Executed, int StrictMatch, int ConditionalMatch, int Unresolved,
    int Unsupported, int NotRun, int Mismatch, int ExecutionError, int BudgetExceeded);
public sealed record P28ChainSequence(int ImageIndex, string ImageId, int ScratchPattern, int RequestedEvents, int CompletedEvents,
    int CompletedDecisions, int StopEventIndex, int SampleStores, IReadOnlyDictionary<string, P28ChainStageCounts> StageCounts,
    IReadOnlyList<P28ChainCheckpoint> Checkpoints);
public sealed record P28ChainPairedCheckpoint(int Index, string Comparison, bool? StateEqual, bool? SideEffectsEqual, bool? RequestEqual);
public sealed record P28ChainImageComparison(string Pair, int ScratchPattern, int ComparableEvents, int ComparableDecisions,
    int? FirstStateDifference, int StateDifferences, int RequestDifferences, int? FirstRejoinedAfterDifference,
    int ComparableStageBoundaries, bool ObservedExecutionPrefixesEqual, IReadOnlyList<P28ChainPairedCheckpoint> Checkpoints);
public sealed record P28ChainReport(string FormatVersion, string Purpose, RomHash BaselineHash, RomHash? IntermediateHash, RomHash? DerivedHash,
    string ScenarioDigest, string RunnerVersion, IReadOnlyList<string> LocalSemanticFixes, IReadOnlyList<string> AllowedAssumptions,
    IReadOnlyList<P28ChainSequence> Sequences, IReadOnlyList<P28ChainImageComparison> ImageComparisons,
    bool? CompensationNotAccessed, bool HasFailure, IReadOnlyList<System.Text.Json.JsonElement> ReplayDiagnostics)
{
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string Claim => "Bounded byte-execution/model agreement on independently evolved histories; not physical ECU validation.";
    public string SoftwareBoundary => "Before 0x12FC; software P1 output-data only, all-output/no-external-bus precondition.";
    public string IntermediateScope => "Threshold-only comparison image in memory from verified M1g plan; not a trusted baseline or export.";
}
