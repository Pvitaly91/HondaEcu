using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28IdleResearchAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length > 0 && args[0] == "export") return await P28IdleTableExportAsync(args[1..], cancellationToken).ConfigureAwait(false);
        if (args.Length == 0 || args[0] is not ("inspect" or "target-check" or "contexts-inspect" or "contexts-check")) throw new CliUsageException("Usage: research p28-idle <inspect|target-check|contexts-inspect|contexts-check> <baseline> --profile p28-304 --output <new-private-json> ...");
        var contexts = args[0].StartsWith("contexts-", StringComparison.Ordinal);
        var check = args[0] is "target-check" or "contexts-check"; var command = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly(check ? ["profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output"] : ["profile", "confirm-profile", "baseline-binding", "output"]);
        command.RequirePositionals(1, "research p28-idle inspect|target-check <baseline>");
        if (check && !command.HasFlag("confirm-profile")) throw new CliUsageException("Idle execution requires --confirm-profile and exact binding.");
        var baselinePath = ResolvePath(command.Positionals[0]); var outputPath = ResolvePath(command.Required("output"));
        string? OptionPath(string name) => command.Optional(name) is { } value ? ResolvePath(value) : null;
        var bindingPath = check ? ResolvePath(command.Required("baseline-binding")) : OptionPath("baseline-binding");
        var runnerPath = check ? ResolvePath(command.Required("runner")) : null; var scenarioPath = check ? ResolvePath(command.Required("scenario")) : null;
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var inputPaths = new[] { baselinePath, bindingPath, runnerPath, scenarioPath, profile.SourcePath }; ProtectNewResearchDestination(outputPath, inputPaths);
        var snapshot = await Task.Run(() => inputPaths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(p => p,
            p => string.Equals(p, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(p, 1_048_576) : File.ReadAllBytes(p), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } pp && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[pp])))) throw new InvalidDataException("Profile changed while loading idle inputs.");
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = bindingPath is null ? null : await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot); object report; var failure = false;
        if (check && contexts)
        {
            var scenario = P28IdleContextsScenario.Parse(utf8.GetString(snapshot[scenarioPath!]));
            var validation = await P28IdleContextsValidator.ExecuteAsync(baseline, profile, binding!, true, runnerPath!, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
            report = validation; failure = validation.HasFailure;
            await _output.WriteLineAsync("image scratch source | complete calls | rawD9 range").ConfigureAwait(false);
            foreach (var image in validation.Images) foreach (var sequence in image.Sequences)
                {
                    foreach (var group in sequence.Checkpoints.Where(c => c.Disposition == "StrictMatch").GroupBy(c => c.Expected!.FinalSource))
                        await _output.WriteLineAsync($"{image.Image} {sequence.ScratchPattern} {group.Key} | {group.Count()} | {group.Min(c => c.Inputs.RawD9)}..{group.Max(c => c.Inputs.RawD9)}").ConfigureAwait(false);
                    foreach (var group in sequence.Checkpoints.GroupBy(c => c.Disposition))
                        await _output.WriteLineAsync($"contexts image={image.Image}, scratch={sequence.ScratchPattern}: {group.Key}={group.Count()}").ConfigureAwait(false);
                }
            await _output.WriteLineAsync($"A/B witnesses={validation.Comparisons.Count(c => c.Witness == true)}, read-but-same-target={validation.Comparisons.Count(c => c.MutatedCellRead == true && c.TargetA == c.TargetB)}; physical reachability unknown.").ConfigureAwait(false);
        }
        else if (check)
        {
            var scenario = P28IdleScenario.Parse(utf8.GetString(snapshot[scenarioPath!]));
            var validation = await P28IdleValidator.ExecuteAsync(baseline, profile, binding!, true, runnerPath!, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
            report = validation; failure = validation.HasFailure;
            foreach (var image in validation.Images) foreach (var sequence in image.Sequences)
                    await _output.WriteLineAsync($"idle image={image.Image}, scratch={sequence.ScratchPattern}: calls={sequence.Checkpoints.Count}, strict={sequence.Checkpoints.Count(c => c.Disposition == "StrictMatch")}, other={sequence.Checkpoints.Count(c => c.Disposition != "StrictMatch")}.").ConfigureAwait(false);
        }
        else if (contexts)
        {
            var inspection = P28IdleContextsInspector.Inspect(baseline, profile, binding, command.HasFlag("confirm-profile")); report = inspection;
            failure = binding is not null && !inspection.InterpretationApplied;
        }
        else
        {
            var inspection = P28IdleInspector.Inspect(baseline, profile, binding, command.HasFlag("confirm-profile")); report = inspection;
            failure = binding is not null && !inspection.InterpretationApplied;
        }
        RequireCaptureInputSnapshot(snapshot); await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync("Raw idle target/error software boundary only. PcInspectionOnly / NotFlashReady. Physical RPM unavailable; GUI r3 paused/NotRun; hardware/full boot NotRun. No BIN written.").ConfigureAwait(false);
        return failure ? VerificationFailed : Success;
    }
}
