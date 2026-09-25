using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28IgnitionTimingChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-ignition timing-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <v0.17.0-rust-executable> --scenario <m2i-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile"))
            throw new CliUsageException("M2i requires explicit profile confirmation and exact baseline binding.");
        var originalPath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner"));
        var scenarioPath = ResolvePath(command.Required("scenario"));
        var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false))
            .Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase)
            .ToDictionary(path => path, path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase)
                ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path),
                StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) !=
            P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2i inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28IgnitionCorrectionScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28IgnitionCorrectionValidator.ExecuteAsync(original, profile, binding, true,
            runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2i image={sequence.ImageIndex} scratch={sequence.ScratchPattern:X2}: " +
                $"completed={sequence.CompletedCalls}, stop={sequence.StopCallIndex}.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
            {
                var input = row.Status == 4 ? null : scenario.Calls[row.Index];
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} " +
                    $"map={row.SelectedOrigin?.ToString() ?? "NotRun"} lookup={row.Lookup?.ToString() ?? "NotRun"} " +
                    $"DATA0248={row.Data0248?.ToString() ?? "NotRun"} read0248={row.NativeRead0248?.ToString() ?? "NotRun"} " +
                    $"correction={input?.Correction0245.ToString() ?? "NotRun"}/{input?.Correction0246.ToString() ?? "NotRun"} " +
                    $"bounded={row.BoundedRaw?.ToString() ?? "NotRun"} result035B={row.Result035b?.ToString() ?? "NotRun"} " +
                    $"result024A={row.Result024a?.ToString() ?? "NotRun"}.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("M2i read-only raw software boundary; 0BD4→0F85 is scripted. " +
            "ConditionalMatch depends on oki.add-er3-a, not strict instruction confirmation. " +
            "PcInspectionOnly / NotFlashReady; physical RPM/degrees unavailable; GUI/hardware NotRun. No BIN written.")
            .ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
