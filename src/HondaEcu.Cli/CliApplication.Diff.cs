using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> DiffAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal) { "json" };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly("json", "output", "max-ranges");
        command.RequirePositionals(2, "hondaecu diff <base> <modified> [--json] [--output <report.json>] [--max-ranges <N>]");

        var maxRangesText = command.Optional("max-ranges");
        int? maxRanges = maxRangesText is null ? null : ParsePositiveInt(maxRangesText, "max-ranges");
        var baselinePath = ResolvePath(command.Positionals[0]);
        var modifiedPath = ResolvePath(command.Positionals[1]);
        var report = await Task.Run(
            () => DiffEngine.CompareFiles(baselinePath, modifiedPath, maxRanges),
            cancellationToken).ConfigureAwait(false);

        var reportPath = command.Optional("output");
        if (reportPath is not null)
        {
            await WriteJsonFileAsync(ResolvePath(reportPath), report, cancellationToken).ConfigureAwait(false);
        }

        if (command.HasFlag("json"))
        {
            await WriteJsonAsync(report).ConfigureAwait(false);
            return Success;
        }

        await WriteHumanDiffAsync(report).ConfigureAwait(false);
        if (reportPath is not null)
        {
            await _output.WriteLineAsync($"JSON report: {ResolvePath(reportPath)}").ConfigureAwait(false);
        }

        return Success;
    }

    private async Task WriteHumanDiffAsync(DiffReport report)
    {
        await _output.WriteLineAsync($"Base SHA-256: {report.BaseHash.Sha256}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Modified SHA-256: {report.ModifiedHash.Sha256}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Different bytes: {report.DifferentByteCount}").ConfigureAwait(false);
        await _output.WriteLineAsync($"First offset: {FormatOffset(report.FirstDifferentOffset)}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Last offset: {FormatOffset(report.LastDifferentOffset)}").ConfigureAwait(false);
        await _output.WriteLineAsync("Ranges:").ConfigureAwait(false);
        foreach (var range in report.Ranges)
        {
            await _output.WriteLineAsync(
                $"  0x{range.Offset:X4}-0x{range.EndOffset:X4} ({range.Length}): {range.OldHex} -> {range.NewHex}")
                .ConfigureAwait(false);
        }

        if (report.RangesTruncated)
        {
            await _output.WriteLineAsync("  ... additional ranges omitted by --max-ranges").ConfigureAwait(false);
        }

        await _output.WriteLineAsync("Changed 0x100-byte pages:").ConfigureAwait(false);
        foreach (var page in report.Pages)
        {
            await _output.WriteLineAsync(
                $"  page 0x{page.Page:X2} (0x{page.Offset:X4}): {page.ChangedByteCount} byte(s)")
                .ConfigureAwait(false);
        }
    }

    private static string FormatOffset(int? offset) => offset is null ? "none" : $"0x{offset.Value:X4}";
}
