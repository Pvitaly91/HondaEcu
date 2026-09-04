using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> PatchAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal)
        {
            "allow-unverified",
            "confirm-profile",
        };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly(
            "profile",
            "set",
            "output",
            "report",
            "allow-unverified",
            "confirm-profile");
        command.RequirePositionals(
            1,
            "hondaecu patch <input> --profile <id> --set <parameter=value> --output <rom> --report <json> [--allow-unverified] [--confirm-profile]");

        var profileId = command.Required("profile");
        var assignments = command.Many("set").Select(ParseAssignment).ToArray();
        if (assignments.Length == 0)
        {
            throw new CliUsageException("At least one '--set parameter=value' assignment is required.");
        }

        var inputPath = ResolvePath(command.Positionals[0]);
        var outputPath = ResolvePath(command.Required("output"));
        var reportPath = ResolvePath(command.Required("report"));
        AtomicFile.EnsureDifferentPath(outputPath, inputPath);
        AtomicFile.EnsureDifferentPath(reportPath, inputPath);

        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(profileId);
        var input = await Task.Run(() => RomImage.Load(inputPath), cancellationToken).ConfigureAwait(false);
        input.ValidateExactSize(profile.ExpectedSize, profile.Id);

        var identity = RomIdentifier.Identify(input, catalog.Profiles);
        if (!identity.IsIdentified)
        {
            if (!command.HasFlag("confirm-profile"))
            {
                throw new UnknownRomException(
                    $"Input ROM is not identified as '{profile.Id}' by a trusted hash or signature. " +
                    "Inspect it first and pass --confirm-profile to explicitly acknowledge the selected profile.");
            }

            identity = RomIdentifier.Identify(input, catalog.Profiles, profile.Id);
        }
        else if (!string.Equals(identity.ProfileId, profile.Id, StringComparison.OrdinalIgnoreCase))
        {
            throw new UnknownRomException(
                $"Input ROM identifies as '{identity.ProfileId}', not requested profile '{profile.Id}'.");
        }

        var plan = PatchPlan.Create(
            profile.Id,
            assignments.Select(assignment => new ParameterAssignment(assignment.Id, assignment.Value)),
            command.HasFlag("allow-unverified"));
        var result = PatchEngine.Apply(input, profile, plan, identity);

        await _output.WriteLineAsync("Patch preview:").ConfigureAwait(false);
        foreach (var change in result.Report.Changes)
        {
            await _output.WriteLineAsync(
                $"  {change.ParameterId} @ 0x{change.Offset:X4}: {change.OldHex} -> {change.NewHex}")
                .ConfigureAwait(false);
        }

        if (result.Report.Changes.Count == 0)
        {
            await _output.WriteLineAsync("  no byte changes (the requested values already match)").ConfigureAwait(false);
        }

        await Task.Run(
            () => PatchEngine.WriteAtomic(result, outputPath, reportPath),
            cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync($"Output SHA-256: {result.Report.OutputHash.Sha256}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Patch report: {reportPath}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Checksum: {Kebab(result.Report.ChecksumStatusAfter)}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Flash readiness: {Kebab(result.Report.FlashReadiness)}").ConfigureAwait(false);
        if (result.Report.FlashReadiness == FlashReadinessStatus.PcInspectionOnly)
        {
            await _error.WriteLineAsync(
                "warning: output is for PC inspection only and is not validated as flash-ready.")
                .ConfigureAwait(false);
        }

        return Success;
    }

    private async Task<int> VerifyAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("profile", "patch-report", "baseline");
        command.RequirePositionals(
            1,
            "hondaecu verify <output> --profile <id> --patch-report <json> [--baseline <input-rom>]");

        var profileId = command.Required("profile");
        var reportPath = ResolvePath(command.Required("patch-report"));
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(profileId);
        var output = await Task.Run(
            () => RomImage.Load(ResolvePath(command.Positionals[0])),
            cancellationToken).ConfigureAwait(false);
        var report = await Task.Run(() => PatchReport.Load(reportPath), cancellationToken).ConfigureAwait(false);
        var baselinePath = command.Optional("baseline");
        var baseline = baselinePath is null
            ? null
            : await Task.Run(() => RomImage.Load(ResolvePath(baselinePath)), cancellationToken).ConfigureAwait(false);

        var verification = PatchVerifier.Verify(output, profile, report, baseline);
        await _output.WriteLineAsync($"Output SHA-256: {verification.OutputHash.Sha256}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Profile: {verification.ProfileId}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Flash readiness: {Kebab(verification.FlashReadiness)}").ConfigureAwait(false);
        if (verification.IsValid)
        {
            await _output.WriteLineAsync("Verification passed: declared and actual changes match.").ConfigureAwait(false);
            return Success;
        }

        await _error.WriteLineAsync("Verification failed:").ConfigureAwait(false);
        foreach (var issue in verification.Issues)
        {
            var location = issue.Offset is null ? string.Empty : $" at 0x{issue.Offset.Value:X4}";
            await _error.WriteLineAsync($"  [{issue.Code}]{location} {issue.Message}").ConfigureAwait(false);
        }

        return VerificationFailed;
    }
}
