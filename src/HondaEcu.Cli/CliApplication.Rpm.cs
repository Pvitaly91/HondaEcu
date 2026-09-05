using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28RpmPreviewAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "slot", "scaling", "rpm", "rpm-provenance",
            "allow-assumption", "output");
        command.RequirePositionals(1,
            "hondaecu research p28-vtec rpm-preview <original> --profile p28-304 --confirm-profile --baseline-binding <private-json> --slot <slot-id> --output <new-private-json> [--scaling <explicit-scenario>] [--rpm <N/D> --rpm-provenance <text>] [--allow-assumption oki.add-er1-a] [--allow-assumption oki.add-er3-a]");
        if (!command.HasFlag("confirm-profile"))
            throw new CliUsageException("Conditional RPM research requires --confirm-profile and the unchanged original baseline binding.");
        var profileId = command.Required("profile");
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var slotId = command.Required("slot");
        var outputPath = ResolvePath(command.Required("output"));
        var scalingOption = command.Optional("scaling");
        var scalingPath = scalingOption is null ? null : ResolvePath(scalingOption);
        var rpm = command.Optional("rpm");
        var rpmProvenance = command.Optional("rpm-provenance");
        if ((rpm is null) != (rpmProvenance is null))
            throw new CliUsageException("An explicit --rpm override requires --rpm-provenance; provenance without --rpm is not a new query.");
        IReadOnlyList<string> assumptions;
        try
        {
            assumptions = P28ProducerValidator.ValidateAssumptions(command.Many("allow-assumption"));
        }
        catch (ArgumentException)
        {
            throw new CliUsageException("Each --allow-assumption may independently name oki.add-er1-a or oki.add-er3-a once; no global permission is supported.");
        }
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(profileId);
        ProtectNewResearchDestination(outputPath, baselinePath, bindingPath, scalingPath, profile.SourcePath);
        var result = await Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            var paths = new[] { baselinePath, bindingPath, scalingPath, profile.SourcePath }
                .OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
            // Preserve the reviewed file snapshot across the bounded mathematical work.
            var snapshot = paths.ToDictionary(path => path,
                path => string.Equals(path, scalingPath, StringComparison.OrdinalIgnoreCase)
                    ? ReadRpmScenarioSnapshot(path) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase);
            var baseline = RomImage.Load(baselinePath);
            var binding = P28ExactBaselineBinding.Load(bindingPath);
            P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true);
            if (profile.SourcePath is { } source &&
                P28VtecInspector.ComputeProfileDigest(RomProfile.Load(source)) != P28VtecInspector.ComputeProfileDigest(profile))
                throw new InvalidDataException("The research profile changed while preparing the RPM query.");
            var slot = P28ThresholdLogic.ResolveSlot(slotId);
            var scenario = scalingPath is null ? null : P28RpmScenario.Load(scalingPath);
            var query = P28RpmQuery.Create(scenario, slot.Id, baseline.Bytes.Span[slot.Offset], rpm, rpmProvenance, assumptions);
            var planning = P28RpmPlanner.Analyze(query, cancellationToken);
            RequireRpmInputSnapshot(snapshot, scalingPath);
            var report = new
            {
                FormatVersion = "1.0",
                Purpose = "bound-baseline-conditional-rpm-preview",
                BaselineHash = baseline.Hash,
                ProfileId = profile.Id,
                ProfileDigest = P28VtecInspector.ComputeProfileDigest(profile),
                BindingDigest = P28RawThresholdEditor.ComputeBindingDigest(binding),
                Planning = planning,
                BestCandidateForwardPreviews = planning.BestCandidates.Select(candidate => new
                {
                    candidate.RawValue,
                    Forward = P28RpmPlanner.EvaluateForward(query, candidate.RawValue),
                }).ToArray(),
                FlashReadiness = FlashReadinessStatus.PcInspectionOnly,
                FlashSafety = FlashSafetyStatus.NotFlashReady,
                Scope = "Conditional mathematical preview for one neutral slot/prior-state predicate; not byte execution, full hysteresis, physical RPM or authority to publish a ROM.",
            };
            return (Report: report, Planning: planning, Snapshot: snapshot);
        }, cancellationToken).ConfigureAwait(false);
        cancellationToken.ThrowIfCancellationRequested();
        RequireRpmInputSnapshot(result.Snapshot, scalingPath);
        await WriteJsonFileAsync(outputPath, result.Report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"Conditional RPM model preview: {result.Planning.Status}; {result.Planning.BestCandidates.Count} equally best eligible raw candidate(s).").ConfigureAwait(false);
        foreach (var reason in result.Planning.UnavailableReasons)
            await _output.WriteLineAsync(reason).ConfigureAwait(false);
        await _output.WriteLineAsync("Scenario and query provenance are retained separately; source files are unchanged.").ConfigureAwait(false);
        await _output.WriteLineAsync("This command did not run Rust, verify a native checksum, create an export plan or save a BIN.").ConfigureAwait(false);
        await _output.WriteLineAsync("Conditional RPM is not measured hardware speed. PcInspectionOnly / NotFlashReady.").ConfigureAwait(false);
        return result.Planning.BestCandidates.Count == 0 ? VerificationFailed : Success;
    }

    private static void RequireRpmInputSnapshot(IReadOnlyDictionary<string, byte[]> snapshot, string? scalingPath)
    {
        foreach (var entry in snapshot)
        {
            var current = string.Equals(entry.Key, scalingPath, StringComparison.OrdinalIgnoreCase)
                ? ReadRpmScenarioSnapshot(entry.Key) : File.ReadAllBytes(entry.Key);
            if (!current.AsSpan().SequenceEqual(entry.Value))
                throw new InvalidDataException("An original input, binding, profile or scenario changed during RPM preview; no report was published.");
        }
    }

    private static byte[] ReadRpmScenarioSnapshot(string path)
    {
        using var stream = File.OpenRead(path);
        if (stream.Length > 65536) throw new InvalidDataException("Scaling assumptions exceed 64 KiB.");
        var bytes = new byte[65537];
        var count = 0;
        while (count < bytes.Length)
        {
            var read = stream.Read(bytes, count, bytes.Length - count);
            if (read == 0) break;
            count += read;
        }
        if (count > 65536) throw new InvalidDataException("Scaling assumptions exceed 64 KiB.");
        return bytes[..count];
    }
}
