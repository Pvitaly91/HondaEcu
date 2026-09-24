using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28SharedChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output", "allow-assumption");
        command.RequirePositionals(1, "hondaecu research p28-calibration shared-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner> --scenario <m2h-scenario.json> --output <new-private-report.json> [--allow-assumption oki.subb-a-off-n8-encoding]");
        if (!command.HasFlag("confirm-profile"))
            throw new CliUsageException("M2h requires explicit profile confirmation and exact baseline binding.");
        var assumption = command.Optional("allow-assumption");
        IReadOnlyList<string> allowed;
        try { allowed = P28SharedCalibrationValidator.ValidateAssumptions(assumption is null ? [] : [assumption]); }
        catch (ArgumentException exception) { throw new CliUsageException(exception.Message); }
        var originalPath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner"));
        var scenarioPath = ResolvePath(command.Required("scenario"));
        var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path),
            StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) !=
            P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2h inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28SharedCalibrationScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28SharedCalibrationValidator.ExecuteAsync(original, profile, binding, true, runnerPath,
            scenario, allowed, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2h image={sequence.ImageIndex} scratch={sequence.ScratchPattern:X2}: " +
                $"completed={sequence.CompletedCalls}, strict={sequence.Checkpoints.Count(c => c.Disposition == "StrictMatch")}, " +
                $"conditional={sequence.Checkpoints.Count(c => c.Disposition == "ConditionalMatch")}, " +
                $"partial={sequence.Checkpoints.Count(c => c.IgnitionCompleted && !c.WholeEventCompleted)}.").ConfigureAwait(false);
            foreach (var cp in sequence.Checkpoints)
            {
                if (cp.Disposition == "NotRun")
                {
                    await _output.WriteLineAsync($"  event={cp.Index}: NotRun; no input applied; retained DATA0248={cp.StateAfter.Output0248}, DATA0140={cp.StateAfter.Output0140}.").ConfigureAwait(false);
                    continue;
                }
                await _output.WriteLineAsync($"  event={cp.Index}: {cp.Disposition}; ignition selector={cp.SelectorBefore0227:X2}->{cp.SelectorAfter0227:X2}, origin={cp.IgnitionOrigin?.ToString() ?? "NotRun"}, lookup={cp.IgnitionLookup?.ToString() ?? "NotRun"}, DATA0248={cp.Data0248?.ToString() ?? "NotRun"}; " +
                    $"VTEC request={cp.RequestP1?.ToString() ?? "NotRun"}, fuel selector={cp.FuelSelector0127?.ToString() ?? "NotRun"}, origin={cp.FuelOrigin?.ToString() ?? "NotRun"}, lookup={cp.FuelLookup?.ToString() ?? "NotRun"}, DATA0140={cp.Data0140?.ToString() ?? "NotRun"}; " +
                    $"ignitionCompleted={cp.IgnitionCompleted}, wholeEventCompleted={cp.WholeEventCompleted}, cumulativeConditional={cp.ConditionalDependency}, reason={cp.StopReason ?? "none"}.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("M2h scripted caller schedule, one native axis pass, two continuous tails. PcInspectionOnly / NotFlashReady; raw units only; GUI/hardware NotRun. No BIN written.").ConfigureAwait(false);
        return report.HasFailure || report.HasIncomplete ? VerificationFailed : Success;
    }
}
