using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28LimiterFuelChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel limiter-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.22.0> --scenario <m2n-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2n requires explicit confirmation and exact baseline binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2n inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28LimiterFuelScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28LimiterFuelValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2n image={sequence.Image} scratch={sequence.ScratchPattern:X2}; fixed context; native217A->2194.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} decision={row.DecisionDisposition} selected-threshold={row.SelectedThreshold?.ToString() ?? "NotRun"} request={row.Request?.ToString() ?? "NotRun"} gate-taken={row.GateTaken?.ToString() ?? "NotRun"} " +
                    $"native0140={row.Fuel?.Data0140?.ToString() ?? "NotRun"} native0158={row.Fuel?.NativeFactor0158?.ToString() ?? "NotRun"} component={row.Fuel?.Component?.ToString() ?? "NotRun"} correction={row.Fuel?.Correction?.ToString() ?? "NotRun"} corrected={row.Fuel?.Corrected?.ToString() ?? "NotRun"} stores03A2/03B4={row.Fuel?.Store03a2?.ToString() ?? "NotRun"}/{row.Fuel?.Store03b4?.ToString() ?? "NotRun"}.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync("Read-only native fixed limiter to native217A/21F5 fuel gate on one CPU/RAM. Routine transitions scripted, bodies native. No mask5585/P2/adaptive/ticks/physical injector interpretation; PcInspectionOnly / NotFlashReady; M2i Blocked; GUI/hardware/full boot NotRun; new firmware BIN0.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
