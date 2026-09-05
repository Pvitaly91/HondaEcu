using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28AcquisitionStageCounts(
    int Total, int MatchesWithoutAssumptions, int ConditionalMatches, int StoppedUnresolved,
    int UnsupportedMode, int ExecutionErrors, int BudgetExceeded, int Mismatches, int NotRun)
{
    public bool HasFailure => ExecutionErrors + BudgetExceeded + Mismatches != 0;
}

public sealed record P28AcquisitionComparisonIssue(int ImageIndex, int ScratchPattern, int ObservationIndex,
    string Stage, string Category, string Message);

public sealed record P28AcquisitionStageResult(int Status, IReadOnlyList<string> UsedAssumptions, int Steps,
    int StopPc, IReadOnlyList<int> Outputs, IReadOnlyList<int> ProgramReads,
    IReadOnlyList<int> ExecutedInstructionBytes, IReadOnlyList<JsonElement> Trace, string? Error);

public sealed record P28AcquisitionObservedStep(int Status, string Disposition, int Steps, int StopPc,
    IReadOnlyList<int[]> PeripheralAccesses, IReadOnlyList<int[]> SampleWrites,
    P28AcquisitionState StateAfter,
    IReadOnlyList<int> ProgramReads, IReadOnlyList<string> UsedAssumptions,
    IReadOnlyList<int> ExecutedInstructionBytes, IReadOnlyList<JsonElement> Trace, string? Error);

public sealed record P28AcquisitionCheckpoint(int ObservationIndex, ushort? SelectedTimestamp, int? SlotIndex, P28AcquisitionObservedStep Acquisition,
    P28AcquisitionStageResult? G, P28AcquisitionStageResult? F, P28AcquisitionStageResult? Threshold,
    P28AcquisitionState StateAfterComposition, IReadOnlyList<string> CumulativeAssumptions,
    int EverWrittenMask, IReadOnlyList<int> SlotWriteCounts);

public sealed record P28AcquisitionSequenceComparison(int ImageIndex, string ImageId, int ScratchPattern,
    int RequestedObservations, int CompletedObservations, int RemainingNotRun, int StopObservationIndex,
    int ActualSampleWrites, int EverWrittenMask, IReadOnlyList<int> SlotWriteCounts, bool WarmUpComplete,
    P28AcquisitionStageCounts Acquisition, P28AcquisitionStageCounts Producer,
    P28AcquisitionStageCounts Compact, P28AcquisitionStageCounts Threshold,
    IReadOnlyList<P28AcquisitionCheckpoint> Checkpoints,
    IReadOnlyList<P28AcquisitionState> IndependentExpectedStates,
    IReadOnlyList<string> UsedAssumptions, bool HasFailure);

public sealed record P28AcquisitionDerivedComparison(bool VerifiedCompositionLineage,
    int PairedObservations, bool ExactAcquisitionEquality, bool ExactProducerCompactEquality,
    int EligibleThresholdComparisons, int ExpectedChangedPredicates, int ActualChangedPredicates,
    bool ExactChangedPredicateSet, bool CompensationByteNotReadOrFetched,
    string AccessScope);

public sealed record P28AcquisitionValidationReport(
    string FormatVersion, string Purpose, int ProtocolVersion, string RunnerVersion, string UpstreamCommit,
    IReadOnlyList<string> LocalSemanticFixes, string AcquisitionModelId, string ProducerModelId, string CompactModelId,
    string Composition, string ScenarioDigest, JsonElement ScenarioSnapshot,
    string ProfileId, RomHash BaselineHash, RomHash? DerivedHash, string ProfileDigest, string BindingDigest,
    string? ComposedPlanDigest, IReadOnlyList<JsonElement> EntryContracts,
    IReadOnlyList<string> PermittedAssumptions, IReadOnlyList<string> UsedAssumptions,
    IReadOnlyList<P28AcquisitionSequenceComparison> Sequences,
    P28AcquisitionDerivedComparison? DerivedComparison, IReadOnlyList<P28AcquisitionComparisonIssue> Issues,
    IReadOnlyList<JsonElement> ReplayDiagnostics, bool HasFailure, bool HasIncompleteOrConditional,
    bool PhysicalRpmAvailable, bool HardwareExecutionPerformed, bool FullEcuBootPerformed,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety, IReadOnlyList<string> Limitations)
{
    public P28AcquisitionEnvelopeReport? EnvelopeComparison { get; init; }
    public IReadOnlyList<P28CaptureTimelinePoint>? TimelineObservations { get; init; }
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));
}
