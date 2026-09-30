using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28PostStoreChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel post-store-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.24.0> --scenario <m2p-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2p requires explicit confirmation and exact baseline binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2p inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28PostStoreScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28PostStoreValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2p image={sequence.Image} scratch={sequence.ScratchPattern:X2}; same-machine2204..223B.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} prefix={row.PrefixDisposition} previous={row.Expected?.Previous} generation={row.PreviousGeneration} current={row.Expected?.Current} 0150={row.Result0150} reason={row.Expected?.Reason ?? "NotRun"}.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync("Read-only native post-store software result; next reader223D static/NotEvaluated. Units unknown; PcInspectionOnly / NotFlashReady; M2i Blocked; GUI/hardware/full boot NotRun; new firmware BIN0.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
