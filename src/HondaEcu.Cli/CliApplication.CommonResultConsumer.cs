using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28CommonResultConsumerCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly(["profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output"]);
        command.RequirePositionals(1, "hondaecu research p28-fuel common-result-consumer-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.27.0> --scenario <m2s-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2s read-only native research requires exact baseline binding and --confirm-profile.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2s inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28CommonResultConsumerScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28CommonResultConsumerValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2s image={sequence.Image} scratch={sequence.ScratchPattern:X2}; Part A same-machine22B1 continuation; Part B static quartet audit.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} prefix={row.PrefixDisposition} softwareResult13b={row.SoftwareResult13b}.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync("Read-only Part A software13B result or strict partial observations; quartet reader invocations0, ScriptedConsumerEntry NotEstablished/NotRun, overall consumer chain Partial. JGT source/executor ambiguity remains Unresolved; no disputed-form promotion. IRQ NotInjected, pending NoneInjected/NotModeled, elapsed time None. Physical role/units unknown; PcInspectionOnly / NotFlashReady; M2i Blocked; GUI r3 paused/NotRun; D1/D2 interactive, P2/timer/hardware/full boot NotRun; new firmware BIN0.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
