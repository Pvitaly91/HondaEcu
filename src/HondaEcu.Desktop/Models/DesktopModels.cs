using System.ComponentModel;
using HondaEcu.Core;

namespace HondaEcu.Desktop.Models;

public enum DesktopAccessMode { Empty, RawOnly, BoundBaseline, VerifiedDerived, Demo }
public enum DesktopValidationKind { Execute, Producer, Checksum }

public sealed class ThresholdSlotView(string id, int context, int pair, bool priorState,
    int offset, byte currentRaw, string evidence) : INotifyPropertyChanged
{
    private string _proposedRaw = "";
    public string Id { get; } = id;
    public int Context { get; } = context;
    public int Pair { get; } = pair;
    public bool PriorState { get; } = priorState;
    public int Offset { get; } = offset;
    public byte CurrentRaw { get; } = currentRaw;
    public string Evidence { get; } = evidence;
    public string ProposedRaw
    {
        get => _proposedRaw;
        internal set { _proposedRaw = value; PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(ProposedRaw))); }
    }
    public event PropertyChangedEventHandler? PropertyChanged;
    public string OffsetHex => $"0x{Offset:X4}";
    public string CurrentHex => $"0x{CurrentRaw:X2}";
}

public sealed record DesktopCounters(int CompletedWithoutAssumptions, int ConditionalMatches,
    int Unresolved, int Mismatches, int ExecutionErrors, int BudgetExceeded, int NotRun)
{
    public static DesktopCounters Empty { get; } = new(0, 0, 0, 0, 0, 0, 0);
    public bool HasIncompleteOrConditional => ConditionalMatches + Unresolved + NotRun != 0;
    public bool HasFailure => Mismatches + ExecutionErrors + BudgetExceeded != 0;

    public static DesktopCounters From(P28ExecutionReport report)
    {
        return FromExecutionStages(report.Threshold.Select(item => item.Counts).Prepend(report.Compact));
    }

    public static DesktopCounters FromExecutionStages(IEnumerable<P28ExecutionCounts> stages)
    {
        var rows = stages.ToArray();
        return new(rows.Sum(item => item.CompletedWithoutAssumptions), rows.Sum(item => item.ConditionalMatches),
            rows.Sum(item => item.StoppedUnresolved + item.UnresolvedModel), rows.Sum(item => item.Mismatches),
            rows.Sum(item => item.ExecutionErrors), rows.Sum(item => item.BudgetExceeded), 0);
    }

    public static DesktopCounters From(P28ProducerExecutionReport report)
    {
        return FromProducerStages(report.Threshold.Select(item => item.Counts).Prepend(report.ProducerToCompact).Prepend(report.Producer));
    }

    public static DesktopCounters From(P28ChecksumExecutionCounts counts) =>
        new(counts.MatchesWithoutAssumptions, counts.ConditionalMatches, counts.Unresolved,
            counts.Mismatches, counts.ExecutionErrors, counts.BudgetExceeded, counts.NotRun);

    public static DesktopCounters FromProducerStages(IEnumerable<P28ProducerStageCounts> stages)
    {
        var rows = stages.ToArray();
        return new(rows.Sum(item => item.MatchesWithoutAssumptions), rows.Sum(item => item.ConditionalMatches),
            rows.Sum(item => item.StoppedUnresolved + item.UnresolvedModel), rows.Sum(item => item.Mismatches),
            rows.Sum(item => item.ExecutionErrors), rows.Sum(item => item.BudgetExceeded), rows.Sum(item => item.NotRun));
    }
}

/// <summary>Immutable input snapshots; no path in a report can select a different input.</summary>
public sealed record DesktopDocument(DesktopAccessMode Mode, RomImage Image, RomImage? Parent = null,
    RomProfile? Profile = null, P28ExactBaselineBinding? Binding = null,
    P28RawThresholdPlan? Plan = null, P28RawThresholdPatchReport? PatchReport = null,
    IReadOnlyList<string>? InputPaths = null, DesktopLineagePaths? LineagePaths = null, string? BindingPath = null);

public sealed record DesktopLineagePaths(string OutputPath, string ParentPath, string ProfilePath,
    string BindingPath, string PlanPath, string ReportPath);

public sealed record DesktopValidationJob(long SessionId, long JobId, DesktopValidationKind Kind,
    DesktopDocument Document, string RunnerPath, IReadOnlyList<string> Assumptions, string? SelectedSlotId);

public sealed record DesktopValidationResult(DesktopCounters Counters, string Json, bool HasFailure,
    IReadOnlyList<string> PermittedAssumptions, IReadOnlyList<string> UsedAssumptions, string PhysicalScalingStatus,
    P28NativeChecksumReport? Checksum = null);

public sealed record DesktopSavePaths(string OutputPath, string PlanPath, string ReportPath);
