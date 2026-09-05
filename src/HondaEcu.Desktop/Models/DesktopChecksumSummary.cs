using HondaEcu.Core;

namespace HondaEcu.Desktop.Models;

/// <summary>Presentation only: a matched execution is not the checksum's pass decision.</summary>
public sealed record DesktopChecksumSummary(string Arithmetic, string Execution, string Coverage,
    string Evidence, string Assumptions, string Reason)
{
    public static DesktopChecksumSummary From(P28NativeChecksumReport report) => new(
        string.Join("\n", report.Cases.Select(item => $"{item.Id}: C# result 0x{item.Arithmetic.ComputedResult:X2}; " +
            $"residue 0x{item.Arithmetic.ExpectedResidue:X2}; " +
            (item.Arithmetic.ResidueMatches ? "арифметична рівність" : "арифметична нерівність") +
            $". Scoped status: {item.Disposition} / {item.ChecksumStatus}.")),
        string.Join("\n", report.Cases.SelectMany(item => item.Execution.Select(run =>
            $"{item.Id}, scratch 0x{run.ScratchPattern:X2}: {run.Status}; decision={run.Decision ?? "не отримано"}; " +
            $"complete={run.Complete}; calls={run.Invocations}; instructions={run.Steps}. {run.Reason}"))),
        string.Join("\n", report.Cases.Select(item => $"{item.Id}: C# {Ranges(item.Arithmetic.Coverage)}, " +
            $"{item.Arithmetic.CoveredByteCount} bytes; " + string.Join("; ", item.Execution.Select(run =>
                $"byte execution {Ranges(run.ActualCoverage)}; reads={run.ProgramReadCount}; " +
                $"coverage match={run.CoverageMatches}; intermediate state match={run.IntermediateStateMatches}")))) +
            $"\nExcluded: {Ranges(report.Contract.ExcludedRanges)}; stored offset: " +
            (report.Contract.StoredChecksumOffset is int offset ? $"0x{offset:X4}" : "відсутній — fixed residue"),
        $"{report.Evidence}\nМодель: {report.Contract.Qualification}\n" +
            string.Join("\n", report.Cases.Select(item => $"{item.Id}: recognized={item.CodeAssessment.ContractRecognized}; " +
                $"gate enabled={item.CodeAssessment.GateEnabled}. {item.CodeAssessment.Qualification}")),
        $"Дозволено: {string.Join(", ", report.PermittedAssumptions.DefaultIfEmpty("немає (strict)"))}; " +
            $"використано: {string.Join(", ", report.UsedAssumptions.DefaultIfEmpty("немає"))}.",
        string.Join("\n", report.Cases.Select(item => $"{item.Id}: {item.Reason} " + string.Join("; ", item.CodeAssessment.Issues))) +
            "\nPcInspectionOnly / NotFlashReady. Read-only: без repair або bypass. Це не дозвіл запису в ECU.");

    private static string Ranges(IEnumerable<ByteRange> ranges) =>
        string.Join(", ", ranges.Select(range => $"[0x{range.Offset:X4},0x{range.EndExclusive:X4})").DefaultIfEmpty("немає"));
}
