using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28Data0136ProducerCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel data0136-producer-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.29.0> --scenario <m2v-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2v requires explicit confirmation and exact original binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2v inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28Data0136TechnicalProducerScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28Data0136TechnicalProducerValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
            foreach (var c in sequence.Checkpoints)
                await _output.WriteLineAsync($"M2v scratch={sequence.ScratchPattern:X2} event={c.Index} {c.Validation}/{c.Disposition} writer={c.Writer?.WriterPc.ToString("X4") ?? "None"} native0136={c.NativeWord0136?.ToString() ?? "null"} retained={c.RetainedWord0136} generation={c.GenerationDisposition} cause={c.ZeroCause}.").ConfigureAwait(false);
        await _output.WriteLineAsync("Read-only TechnicalSeededEntry56BE->stop-before5719; frozen read-only SFRs, no time/IRQ delivery. Mode1 word00F0 is RawSoftwareSnapshot/UpstreamProducerNotRun. ProducerTo2330SchedulerSeam=NotEstablished; historical M1i mode1 Unsupported; M2u ProducerNotRun; M2s Partial; M2t Blocked/Partial; JGT unresolved. PcInspectionOnly / NotFlashReady; physical units unavailable; GUI/hardware NotRun; BIN0.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
