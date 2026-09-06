using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28LimiterResearchAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0 || args[0] is not ("inspect" or "check"))
            throw new CliUsageException("Usage: hondaecu research p28-limiter <inspect|check> <baseline> --profile p28-304 --output <new-private-json> ...");
        var check = args[0] == "check";
        var command = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly(check ? ["profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output"] : ["profile", "confirm-profile", "baseline-binding", "output"]);
        command.RequirePositionals(1, "research p28-limiter inspect|check <baseline> --profile p28-304 --output <new-private-json>");
        if (check && !command.HasFlag("confirm-profile")) throw new CliUsageException("Limiter execution requires --confirm-profile and exact baseline binding.");
        var baselinePath = ResolvePath(command.Positionals[0]); var outputPath = ResolvePath(command.Required("output"));
        string? OptionPath(string name) => command.Optional(name) is { } value ? ResolvePath(value) : null;
        var bindingPath = check ? ResolvePath(command.Required("baseline-binding")) : OptionPath("baseline-binding");
        var runnerPath = check ? ResolvePath(command.Required("runner")) : null;
        var scenarioPath = check ? ResolvePath(command.Required("scenario")) : null;
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var inputPaths = new[] { baselinePath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, inputPaths);
        var snapshot = await Task.Run(() => inputPaths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(p => p,
            p => string.Equals(p, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(p, 1_048_576) : File.ReadAllBytes(p), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } pp && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[pp]))))
            throw new InvalidDataException("Profile changed while loading limiter inputs.");
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = bindingPath is null ? null : await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        object report; var failure = false;
        if (check)
        {
            var scenario = P28LimiterScenario.Parse(utf8.GetString(snapshot[scenarioPath!]));
            var validation = await P28LimiterValidator.ExecuteAsync(baseline, profile, binding!, true, runnerPath!, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
            report = validation; failure = validation.HasFailure;
            foreach (var sequence in validation.Sequences)
                await _output.WriteLineAsync($"image={sequence.ImageIndex}, scratch={sequence.ScratchPattern}: requested={sequence.Counts.RequestedCalls}, completed={sequence.Counts.CompletedCalls}, strict={sequence.Counts.StrictMatches}, unresolved={sequence.Counts.Unresolved}, NotRun={sequence.Counts.NotRun}, mismatches={sequence.Counts.Mismatches}, errors={sequence.Counts.ExecutionErrors}.").ConfigureAwait(false);
        }
        else report = P28LimiterInspector.Inspect(baseline, profile, binding, command.HasFlag("confirm-profile"));
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync("Isolated period limiter / software mask boundary only. PcInspectionOnly / NotFlashReady. Physical RPM unavailable; GUI r3 paused/NotRun; hardware/full boot NotRun. No BIN written.").ConfigureAwait(false);
        return failure ? VerificationFailed : Success;
    }
}
