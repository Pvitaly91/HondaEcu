using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28BelowSecondP2CheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel below-second-p2-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.36.0> --scenario <m2ac-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2ac requires explicit confirmation and exact original binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath }; ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath])))) throw new InvalidDataException("Profile changed while loading M2ac inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath); var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath])); var scenario = P28BelowSecondP2Scenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28BelowSecondP2Validator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot); await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"SecondP2ArchitecturalHandoff={report.SecondP2ArchitecturalHandoff};BelowContinuation={report.BelowContinuation};TimerEvolution=NotModeled;FirstP2ArchitecturalHandoff=Validated;ReturnFrame=NotEstablished;RT5688NotRun;P2ElectricalPins=NotModeled;PhysicalOutput=NotRun;ReviewedStartupPrecondition;ONE CPU/RAM;TimerContinuation=NotRun;ExplicitHarnessSchedule;Recovered0196Scheduler=NotEstablished;IRQDelivery=NotInjected;ElapsedTime=None;PhysicalP2Role/Polarity=Unknown;PcInspectionOnly/NotFlashReady;GUI/hardwareNotRun;BIN0.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
