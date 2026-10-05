using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28CalRtRoundTripCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel cal-rt-roundtrip-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.37.0> --scenario <m2ad-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2ad requires explicit confirmation and exact original binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath }; ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath])))) throw new InvalidDataException("Profile changed while loading M2ad inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath); var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath])); var scenario = P28CalRtRoundTripScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28CalRtRoundTripValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot); await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"NativeCallReturnRoundTrip={report.NativeCallReturnRoundTrip};FrameSource={report.FrameSource};STOP BEFORE063E;ExplicitHarnessScheduleTo063B;EnclosingCallerPath=NotRun;EnclosingIRQFrame=NotEstablished;RecoveredEcuScheduler=NotEstablished;TimerEvolution=NotModeled;IRQDelivery=NotInjected;PhysicalOutput/GUI/hardwareNotRun;PcInspectionOnly/NotFlashReady;BIN0.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
