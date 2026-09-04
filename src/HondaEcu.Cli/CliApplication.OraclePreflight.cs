using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> OraclePreflightAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("manifest", "output");
        command.RequirePositionals(0, "hondaecu oracle preflight --manifest <json> --output <preflight.json>");
        var manifestPath = ResolvePath(command.Required("manifest"));
        var outputPath = ResolvePath(command.Required("output"));
        RomProfile? profile = null;
        OracleManifest? manifest = null;
        try
        {
            manifest = OracleManifest.Load(manifestPath);
            profile = LoadProfileCatalog().Get(manifest.ProfileId);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or InvalidDataException or
            System.Text.Json.JsonException or InvalidOperationException or KeyNotFoundException or ArgumentException)
        {
            // Preflight reports unavailable collection/profile data instead of requiring a complete collection.
            await _error.WriteLineAsync($"Preflight input: {exception.Message}").ConfigureAwait(false);
        }

        var protectedPaths = new List<string> { manifestPath };
        if (manifest is not null)
        {
            protectedPaths.Add(manifest.BaselinePath);
            protectedPaths.Add(manifest.NoOpPath);
            protectedPaths.AddRange(manifest.Cases.Select(item => item.RomPath));
            if (manifest.IndependentNoOp is not null)
            {
                protectedPaths.Add(manifest.IndependentNoOp.RomPath);
            }
            if (manifest.ResavedNoOp is not null)
            {
                protectedPaths.Add(manifest.ResavedNoOp.RomPath);
            }
        }

        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (protectedPaths.Any(path => string.Equals(ResolvePath(path), outputPath, comparison)))
        {
            throw new CliUsageException("Preflight output must be distinct from the manifest and every recorded ROM path.");
        }

        var report = await Task.Run(() => OraclePreflight.Check(manifestPath, profile), cancellationToken).ConfigureAwait(false);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await WriteJsonAsync(report).ConfigureAwait(false);
        await _output.WriteLineAsync($"Preflight report: {outputPath}").ConfigureAwait(false);
        return Success;
    }
}
