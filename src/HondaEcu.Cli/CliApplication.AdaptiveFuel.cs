using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28AdaptiveFuelChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel adaptive-limiter-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.23.0> --scenario <m2o-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2o requires explicit confirmation and exact baseline binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2o inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28AdaptiveFuelScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28AdaptiveFuelValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2o image={sequence.Image} scratch={sequence.ScratchPattern:X2}; native adaptive/ticks->limiter->217A/21F5.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} bank={row.Bank} producer={row.ProducerPath ?? "NotRun"} thresholds={row.RamCutBefore}/{row.RamResumeBefore}->{row.RamCutAfter}/{row.RamResumeAfter} provenance={row.ThresholdProvenance} generation={row.Generation?.ToString() ?? "None"} ticks={row.NativeTicks} source={row.ThresholdSource ?? "NotRun"} selected={row.SelectedThreshold?.ToString() ?? "NotRun"} request={row.Request?.ToString() ?? "NotRun"} gate={row.GateTaken?.ToString() ?? "NotRun"} 0140={row.Continuation?.Fuel?.Data0140} 0158={row.Continuation?.Fuel?.NativeFactor0158} corrected={row.Continuation?.Fuel?.Corrected} stores03A2/03B4={row.Continuation?.Fuel?.Store03a2}/{row.Continuation?.Fuel?.Store03b4}.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync("Read-only adaptive producer/current RAM/limiter/fuel gate on one CPU. Raw software stimuli and native call counts; no physical cadence/RPM/injector claim. PcInspectionOnly / NotFlashReady; M2i Blocked; GUI/hardware/full boot NotRun; new firmware BIN0.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
