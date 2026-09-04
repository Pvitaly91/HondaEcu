using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> ProfileAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0)
        {
            throw new CliUsageException("Usage: hondaecu profile <list|show|validate> ...");
        }

        return args[0] switch
        {
            "list" => await ProfileListAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "show" => await ProfileShowAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "validate" => await ProfileValidateAsync(args[1..], cancellationToken).ConfigureAwait(false),
            _ => throw new CliUsageException($"Unknown profile command '{args[0]}'."),
        };
    }

    private async Task<int> ProfileListAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly();
        command.RequirePositionals(0, "hondaecu profile list");
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);

        foreach (var profile in catalog.Profiles.OrderBy(profile => profile.Id, StringComparer.Ordinal))
        {
            await _output.WriteLineAsync(
                $"{profile.Id}\t{profile.DisplayName}\t{(profile.Experimental ? "experimental" : "stable")}")
                .ConfigureAwait(false);
        }

        return Success;
    }

    private async Task<int> ProfileShowAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly();
        command.RequirePositionals(1, "hondaecu profile show <id>");
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        await WriteJsonAsync(catalog.Get(command.Positionals[0])).ConfigureAwait(false);
        return Success;
    }

    private async Task<int> ProfileValidateAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly();
        command.RequirePositionals(1, "hondaecu profile validate <profile.json>");
        var path = ResolvePath(command.Positionals[0]);
        var result = await Task.Run(
            () => ProfileDocumentValidator.ValidateFile(path),
            cancellationToken).ConfigureAwait(false);

        if (!result.IsValid)
        {
            foreach (var error in result.Errors)
            {
                await _error.WriteLineAsync($"error: {error}").ConfigureAwait(false);
            }

            return VerificationFailed;
        }

        var profile = await Task.Run(() => RomProfile.Load(path), cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"Profile '{profile.Id}' is valid.").ConfigureAwait(false);
        foreach (var warning in result.Warnings)
        {
            await _error.WriteLineAsync($"warning: {warning}").ConfigureAwait(false);
        }

        return Success;
    }
}
