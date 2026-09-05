using System.Text.Json;

namespace HondaEcu.Core;

public enum NativeChecksumDisposition { Valid, Invalid, Unknown, UnsupportedRevision, DisabledOrAltered, Unresolved }
public enum NativeChecksumExecutionStatus { NotRun, Match, ConditionalMatch, UnresolvedInstruction, Mismatch, ExecutionError, BudgetExceeded, Incomplete }

public sealed record P28NativeChecksumContract(
    string Id, string Scope, string Algorithm, int AccumulatorBits, int InitialAccumulator,
    int ExpectedResidue, int? StoredChecksumOffset, IReadOnlyList<ByteRange> Coverage,
    IReadOnlyList<ByteRange> ExcludedRanges, string ReadOrder, string ReadEndianness,
    int BytesPerInvocation, int RequiredInvocations, string CompletionCriterion,
    string Evidence, string Qualification);

public sealed record P28ChecksumCheckpoint(int Invocation, int CounterBefore, int CounterAfter,
    byte SumBefore, byte SumAfter, byte ComputedByte);

/// <summary>Integer calculation under a declared contract, not revision identification or native-code execution.</summary>
public sealed record P28ChecksumArithmetic(
    byte ComputedResult, byte ExpectedResidue, bool ResidueMatches, int CoveredByteCount,
    IReadOnlyList<ByteRange> Coverage, IReadOnlyList<P28ChecksumCheckpoint> Checkpoints, string Reason);

public sealed record P28ChecksumCodeAssessment(bool ContractRecognized, bool GateEnabled,
    NativeChecksumDisposition Disposition, IReadOnlyList<string> Issues, string Qualification);

public sealed record P28ChecksumExecution(
    int ScratchPattern, NativeChecksumExecutionStatus Status, bool Complete,
    int? ComputedResult, string? Decision, int Invocations, int Steps, int? StopPc,
    int ProgramReadCount, IReadOnlyList<ByteRange> ActualCoverage, bool CoverageMatches,
    bool IntermediateStateMatches, IReadOnlyList<string> UsedAssumptions,
    IReadOnlyList<JsonElement> Diagnostics, string Reason);

public sealed record P28NativeChecksumCaseReport(
    string Id, string Kind, RomHash Hash, IReadOnlyList<int> MutatedOffsets,
    P28ChecksumCodeAssessment CodeAssessment, P28ChecksumArithmetic Arithmetic,
    IReadOnlyList<P28ChecksumExecution> Execution, NativeChecksumDisposition Disposition,
    ChecksumStatus ChecksumStatus, string Reason);

public sealed record P28ChecksumExecutionCounts(int Total, int MatchesWithoutAssumptions,
    int ConditionalMatches, int Unresolved, int Mismatches, int ExecutionErrors,
    int BudgetExceeded, int NotRun);

public sealed record P28NativeChecksumReport(
    int FormatVersion, string ReportKind, P28NativeChecksumContract Contract,
    string ProfileId, RomHash BaselineHash, RomHash? DerivedHash, string ProfileDigest,
    string BindingDigest, string? PlanDigest, bool VerifiedDerivedLineage,
    string Mode, IReadOnlyList<string> PermittedAssumptions, IReadOnlyList<string> UsedAssumptions,
    string? RunnerVersion, string? UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    IReadOnlyList<JsonElement> EntryContracts, IReadOnlyList<P28NativeChecksumCaseReport> Cases,
    P28ChecksumExecutionCounts Counts, bool HasFailure, string Evidence, string RunnerDiagnostics,
    bool FullEcuBootPerformed, bool HardwareExecutionPerformed, bool RepairPerformed,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety, IReadOnlyList<string> Limitations)
{
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));
}
