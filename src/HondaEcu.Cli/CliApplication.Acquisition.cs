using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28VtecAcquisitionCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output", "composition",
            "allow-assumption", "derived", "plan", "export-report", "compensation-definition",
            "envelope-scaling", "envelope-slot", "envelope-rpm", "envelope-rpm-provenance");
        command.RequirePositionals(1, "hondaecu research p28-vtec acquisition-check <baseline> --profile p28-304 --confirm-profile --baseline-binding <private-json> --runner <rust-executable> --scenario <private-json> --output <new-private-json>");
        if (!command.HasFlag("confirm-profile")) { throw new CliUsageException("Acquisition execution requires --confirm-profile."); }
        var composition = command.Optional("composition") ?? P28AcquisitionValidator.AcquisitionOnly;
        if (composition is not (P28AcquisitionValidator.AcquisitionOnly or P28AcquisitionValidator.ScheduledComposition))
        { throw new CliUsageException("--composition must be acquisition-only or scheduled-g-f-threshold."); }
        IReadOnlyList<string> assumptions;
        try { assumptions = P28ProducerValidator.ValidateAssumptions(command.Many("allow-assumption")); }
        catch (ArgumentException) { throw new CliUsageException("Only distinct explicit oki.add-er1-a and oki.add-er3-a permissions are supported."); }
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner"));
        var scenarioPath = ResolvePath(command.Required("scenario"));
        var outputPath = ResolvePath(command.Required("output"));
        string? OptionPath(string option) => command.Optional(option) is { } value ? ResolvePath(value) : null;
        var derivedPath = OptionPath("derived");
        var planPath = OptionPath("plan");
        var receiptPath = OptionPath("export-report");
        var definitionPath = OptionPath("compensation-definition");
        var lineageCount = new[] { derivedPath, planPath, receiptPath, definitionPath }.Count(value => value is not null);
        if (lineageCount is not (0 or 4))
        { throw new CliUsageException("Verified child requires --derived, --plan, --export-report and --compensation-definition together."); }
        var scalingPath = OptionPath("envelope-scaling");
        var envelopeSlot = command.Optional("envelope-slot");
        var envelopeRpm = command.Optional("envelope-rpm");
        var envelopeProvenance = command.Optional("envelope-rpm-provenance");
        if ((scalingPath is null) != (envelopeSlot is null) || (envelopeRpm is null) != (envelopeProvenance is null) ||
            scalingPath is null && (envelopeRpm is not null || envelopeProvenance is not null))
        { throw new CliUsageException("Envelope comparison requires explicit --envelope-scaling and --envelope-slot; RPM override requires its provenance."); }
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        var inputPaths = new[] { baselinePath, bindingPath, runnerPath, scenarioPath, derivedPath, planPath, receiptPath, definitionPath, scalingPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, inputPaths);
        // Reject changed inputs rather than publishing a report against a moving scenario/lineage.
        var snapshot = await Task.Run(() => inputPaths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase)
            .ToDictionary(path => path, path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase)
                ? ReadBoundedCaptureInput(path, 1_048_576) : string.Equals(path, scalingPath, StringComparison.OrdinalIgnoreCase)
                    ? ReadBoundedCaptureInput(path, 65536) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var strictUtf8 = new System.Text.UTF8Encoding(false, true);
        var scenario = P28AcquisitionScenario.Parse(strictUtf8.GetString(snapshot[scenarioPath]));
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) !=
            P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(strictUtf8.GetString(snapshot[profilePath]))))
        { throw new InvalidDataException("The selected profile changed while loading acquisition inputs."); }
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);
        RomImage? derived = null;
        P28VerifiedChecksumComposition? verified = null;
        if (lineageCount == 4)
        {
            var inputs = await LoadChecksumCompositionInputsAsync(baselinePath, bindingPath, planPath!, definitionPath,
                profile.Id, cancellationToken).ConfigureAwait(false);
            var receipt = await Task.Run(() => P28ChecksumPreservingExportReport.Load(receiptPath!), cancellationToken).ConfigureAwait(false);
            derived = await Task.Run(() => RomImage.Load(derivedPath!), cancellationToken).ConfigureAwait(false);
            verified = P28ChecksumPreservingEditor.Admit(derived, baseline, profile, binding, inputs.Plan,
                receipt.CompositionReport, inputs.Location ?? throw new InvalidDataException("Missing reviewed compensation definition."));
            RequireChecksumInputSnapshot(inputs.FileSnapshot);
        }
        P28RpmQuery? envelopeQuery = null;
        if (scalingPath is not null)
        {
            var scaling = P28RpmScenario.Parse(strictUtf8.GetString(snapshot[scalingPath]));
            var slot = P28ThresholdLogic.ResolveSlot(envelopeSlot!);
            envelopeQuery = P28RpmQuery.Create(scaling, slot.Id, baseline.ToArray()[slot.Offset], envelopeRpm, envelopeProvenance, assumptions);
        }
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28AcquisitionValidator.ExecuteAsync(baseline, profile, binding, true, runnerPath,
            scenario, composition, assumptions, derived, cancellationToken: cancellationToken, verifiedComposition: verified).ConfigureAwait(false);
        if (envelopeQuery is not null) { report = report with { EnvelopeComparison = P28AcquisitionEnvelope.Compare(report, scenario, envelopeQuery) }; }
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"Stateful capture execution: {composition}; {scenario.Observations.Count} supplied observations per independent image/scratch sequence.").ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"{sequence.ImageId}/{sequence.ScratchPattern}: acquisition {sequence.Acquisition.MatchesWithoutAssumptions} strict matches, {sequence.ActualSampleWrites} actual sample writes; warm-up={sequence.WarmUpComplete}; G {sequence.Producer.ConditionalMatches} conditional/{sequence.Producer.StoppedUnresolved} unresolved; F {sequence.Compact.ConditionalMatches} conditional/{sequence.Compact.NotRun} not run; threshold {sequence.Threshold.ConditionalMatches} conditional/{sequence.Threshold.NotRun} not run; remaining captures not run={sequence.RemainingNotRun}.").ConfigureAwait(false);
        }
        if (report.EnvelopeComparison is { } envelope)
        { await _output.WriteLineAsync($"Unchanged M1h envelope: {envelope.SteadyCheckpoints} fresh steady checkpoints; {envelope.OutOfScopeCheckpoints} outside scope; failure={envelope.HasFailure}.").ConfigureAwait(false); }
        await _output.WriteLineAsync("Explicit frozen SFR snapshots and caller schedule; full boot, IRQ timing, hardware RPM and GUI acceptance: NotRun. No BIN written.").ConfigureAwait(false);
        await _output.WriteLineAsync("PcInspectionOnly / NotFlashReady. Existing verified M1g lineage is retained; this sequence does not rerun native checksum or establish hardware validity.").ConfigureAwait(false);
        return report.HasFailure || report.EnvelopeComparison?.HasFailure == true ? VerificationFailed : Success;
    }

    private static byte[] ReadBoundedCaptureInput(string path, int maximum)
    {
        using var stream = File.OpenRead(path);
        if (stream.Length > maximum) { throw new InvalidDataException("Capture input exceeds its bounded size."); }
        var bytes = new byte[checked(maximum + 1)];
        var count = 0;
        while (count < bytes.Length)
        {
            var read = stream.Read(bytes, count, bytes.Length - count);
            if (read == 0) { break; }
            count += read;
        }
        if (count > maximum) { throw new InvalidDataException("Capture input grew beyond its bounded size."); }
        return bytes.AsSpan(0, count).ToArray();
    }

    private static void RequireCaptureInputSnapshot(IReadOnlyDictionary<string, byte[]> snapshot)
    {
        foreach (var input in snapshot)
        {
            if (!ReadBoundedCaptureInput(input.Key, input.Value.Length).AsSpan().SequenceEqual(input.Value))
            { throw new InvalidDataException("An acquisition input changed during execution; no report is published."); }
        }
    }
}
