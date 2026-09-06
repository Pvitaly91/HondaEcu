using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28VtecChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output", "allow-assumption",
            "derived", "plan", "export-report", "compensation-definition");
        command.RequirePositionals(1, "hondaecu research p28-vtec chain-check <baseline> --profile p28-304 --confirm-profile --baseline-binding <private-json> --runner <rust-executable> --scenario <private-json> --output <new-private-json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("Integrated execution requires --confirm-profile.");
        IReadOnlyList<string> assumptions;
        try { assumptions = P28ChainValidator.ValidateAssumptions(command.Many("allow-assumption")); }
        catch (ArgumentException e) { throw new CliUsageException(e.Message); }
        var baselinePath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario"));
        var outputPath = ResolvePath(command.Required("output"));
        string? OptionPath(string option) => command.Optional(option) is { } value ? ResolvePath(value) : null;
        var derivedPath = OptionPath("derived"); var planPath = OptionPath("plan"); var receiptPath = OptionPath("export-report");
        var definitionPath = OptionPath("compensation-definition");
        var lineageCount = new[] { derivedPath, planPath, receiptPath, definitionPath }.Count(p => p is not null);
        if (lineageCount is not (0 or 4)) throw new CliUsageException("Verified child requires --derived, --plan, --export-report and --compensation-definition together.");
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        var inputPaths = new[] { baselinePath, bindingPath, runnerPath, scenarioPath, derivedPath, planPath, receiptPath, definitionPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, inputPaths);
        var snapshot = await Task.Run(() => inputPaths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(p => p,
            p => string.Equals(p, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(p, 1_048_576) : File.ReadAllBytes(p),
            StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        var scenario = P28ChainScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) !=
            P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Selected profile changed while loading integrated inputs.");
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);
        RomImage? derived = null; P28VerifiedChecksumComposition? verified = null;
        if (lineageCount == 4)
        {
            var inputs = await LoadChecksumCompositionInputsAsync(baselinePath, bindingPath, planPath!, definitionPath, profile.Id, cancellationToken).ConfigureAwait(false);
            var receipt = await Task.Run(() => P28ChecksumPreservingExportReport.Load(receiptPath!), cancellationToken).ConfigureAwait(false);
            derived = await Task.Run(() => RomImage.Load(derivedPath!), cancellationToken).ConfigureAwait(false);
            verified = P28ChecksumPreservingEditor.Admit(derived, baseline, profile, binding, inputs.Plan, receipt.CompositionReport,
                inputs.Location ?? throw new InvalidDataException("Missing reviewed compensation definition."));
            RequireChecksumInputSnapshot(inputs.FileSnapshot);
        }
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28ChainValidator.ExecuteAsync(baseline, profile, binding, true, runnerPath, scenario, assumptions, derived,
            cancellationToken: cancellationToken, verifiedComposition: verified).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var s in report.Sequences)
            await _output.WriteLineAsync($"{s.ImageId}/{s.ScratchPattern}: {s.RequestedEvents} requested events; {s.CompletedEvents} completed events; {s.CompletedDecisions} completed decisions; stop event={s.StopEventIndex}.").ConfigureAwait(false);
        await _output.WriteLineAsync("Integrated Acquire -> G -> F -> persistent decision before 0x12FC; native samples/T/Code, explicit test schedule, no physical RPM/time or actuator claim.").ConfigureAwait(false);
        await _output.WriteLineAsync("PcInspectionOnly / NotFlashReady. GUI r3 paused/NotRun; hardware/full boot NotRun. No BIN written.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
