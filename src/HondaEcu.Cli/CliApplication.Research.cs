using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> ResearchAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0)
        {
            throw new CliUsageException("Usage: hondaecu research p28-vtec inspect ...");
        }

        return args[0] switch
        {
            "p28-vtec" => await P28VtecResearchAsync(args[1..], cancellationToken).ConfigureAwait(false),
            _ => throw new CliUsageException($"Unknown research command '{args[0]}'."),
        };
    }

    private async Task<int> P28VtecResearchAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0)
        {
            throw new CliUsageException("Usage: hondaecu research p28-vtec inspect ...");
        }

        return args[0] switch
        {
            "inspect" => await P28VtecInspectAsync(args[1..], cancellationToken).ConfigureAwait(false),
            _ => throw new CliUsageException($"Unknown p28-vtec research command '{args[0]}'."),
        };
    }

    private async Task<int> P28VtecInspectAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly("profile", "baseline-binding", "output", "confirm-profile");
        command.RequirePositionals(
            1,
            "hondaecu research p28-vtec inspect <input.bin> --profile p28-304 --output <private-report.json> [--baseline-binding <private-binding.json>] [--confirm-profile]");

        var inputPath = ResolvePath(command.Positionals[0]);
        var outputPath = ResolvePath(command.Required("output"));
        var bindingOption = command.Optional("baseline-binding");
        var bindingPath = bindingOption is null ? null : ResolvePath(bindingOption);
        AtomicFile.EnsureDifferentPath(outputPath, inputPath);
        if (bindingPath is not null)
        {
            AtomicFile.EnsureDifferentPath(outputPath, bindingPath);
        }

        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        var image = await Task.Run(() => RomImage.Load(inputPath), cancellationToken).ConfigureAwait(false);
        var binding = bindingPath is null
            ? null
            : await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);

        var report = await Task.Run(
            () => P28VtecInspector.Inspect(
                image,
                profile,
                catalog.Profiles,
                command.HasFlag("confirm-profile"),
                binding),
            cancellationToken).ConfigureAwait(false);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync($"Research scope: {report.Scope}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Exact baseline binding: {Kebab(report.BaselineBinding.Status)}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync(
            $"Revision-specific interpretation: {(report.InterpretationApplied ? "applied" : "not applied")}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync("Private research report written.").ConfigureAwait(false);

        await _error.WriteLineAsync(
            "warning: a private exact-byte binding is analyst-declared research evidence, not factory authentication or a trusted public ROM identity.")
            .ConfigureAwait(false);
        if (!report.InterpretationApplied)
        {
            await _error.WriteLineAsync(
                "warning: revision-specific interpretation was not applied; the report contains only the neutral raw byte window.")
                .ConfigureAwait(false);
        }

        await _error.WriteLineAsync(
            "warning: this inspection is read-only, PC-inspection-only, and not flash-ready.")
            .ConfigureAwait(false);

        return report.BaselineBinding.Status == P28BaselineBindingStatus.Mismatched
            ? VerificationFailed
            : Success;
    }
}
