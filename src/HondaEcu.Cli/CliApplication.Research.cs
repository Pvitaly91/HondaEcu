using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> ResearchAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0)
        {
            throw new CliUsageException("Usage: hondaecu research p28-vtec <inspect|plan|apply|verify> ...");
        }

        return args[0] switch
        {
            "p28-vtec" => await P28VtecResearchAsync(args[1..], cancellationToken).ConfigureAwait(false),
            _ => throw new CliUsageException($"Unknown research command '{args[0]}'."),
        };
    }

    private async Task<int> P28VtecResearchAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0)
        {
            throw new CliUsageException("Usage: hondaecu research p28-vtec <inspect|plan|apply|verify> ...");
        }

        return args[0] switch
        {
            "inspect" => await P28VtecInspectAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "plan" => await P28VtecPlanAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "apply" => await P28VtecApplyAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "verify" => await P28VtecVerifyAsync(args[1..], cancellationToken).ConfigureAwait(false),
            _ => throw new CliUsageException($"Unknown p28-vtec research command '{args[0]}'."),
        };
    }

    private async Task<int> P28VtecInspectAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly(
            "profile",
            "baseline-binding",
            "output",
            "confirm-profile",
            "baseline",
            "plan",
            "patch-report");
        command.RequirePositionals(
            1,
            "hondaecu research p28-vtec inspect <input.bin> --profile p28-304 --output <private-report.json> [--baseline-binding <private-binding.json>] [--confirm-profile] [--baseline <original.bin> --plan <private-plan.json> --patch-report <private-patch-report.json>]");

        var inputPath = ResolvePath(command.Positionals[0]);
        var outputPath = ResolvePath(command.Required("output"));
        var bindingOption = command.Optional("baseline-binding");
        var bindingPath = bindingOption is null ? null : ResolvePath(bindingOption);
        var baselineOption = command.Optional("baseline");
        var planOption = command.Optional("plan");
        var patchReportOption = command.Optional("patch-report");
        var lineageCount = new[] { baselineOption, planOption, patchReportOption }.Count(value => value is not null);
        if (lineageCount is not (0 or 3))
        {
            throw new CliUsageException(
                "Derived inspection requires --baseline, --plan, and --patch-report together.");
        }

        var confirmed = command.HasFlag("confirm-profile");
        if (lineageCount == 3 && (bindingPath is null || !confirmed))
        {
            throw new CliUsageException(
                "Derived inspection requires --baseline-binding and --confirm-profile.");
        }

        var baselinePath = baselineOption is null ? null : ResolvePath(baselineOption);
        var planPath = planOption is null ? null : ResolvePath(planOption);
        var patchReportPath = patchReportOption is null ? null : ResolvePath(patchReportOption);

        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        ProtectNewResearchDestination(
            outputPath,
            inputPath,
            bindingPath,
            baselinePath,
            planPath,
            patchReportPath,
            profile.SourcePath);
        var image = await Task.Run(() => RomImage.Load(inputPath), cancellationToken).ConfigureAwait(false);
        var binding = bindingPath is null
            ? null
            : await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);

        if (lineageCount == 3)
        {
            var baseline = await Task.Run(() => RomImage.Load(baselinePath!), cancellationToken).ConfigureAwait(false);
            var plan = await Task.Run(() => P28RawThresholdPlan.Load(planPath!), cancellationToken).ConfigureAwait(false);
            var patchReport = await Task.Run(
                () => P28RawThresholdPatchReport.Load(patchReportPath!),
                cancellationToken).ConfigureAwait(false);
            var derivedReport = await Task.Run(
                () => P28RawThresholdEditor.InspectDerived(
                    image,
                    baseline,
                    profile,
                    binding!,
                    plan,
                    patchReport),
                cancellationToken).ConfigureAwait(false);
            await WriteJsonFileAsync(outputPath, derivedReport, cancellationToken).ConfigureAwait(false);

            await _output.WriteLineAsync(
                $"One-step derived lineage: {(derivedReport.VerifiedLineage ? "verified" : "not verified")}")
                .ConfigureAwait(false);
            await _output.WriteLineAsync(
                $"Derived threshold interpretation: {(derivedReport.VerifiedLineage ? "applied" : "not applied")}")
                .ConfigureAwait(false);
            await _output.WriteLineAsync("Private derived inspection report written.").ConfigureAwait(false);
            await WriteP28PcOnlyWarningsAsync().ConfigureAwait(false);
            if (!derivedReport.VerifiedLineage)
            {
                await WriteP28VerificationIssuesAsync(derivedReport.Verification.Issues).ConfigureAwait(false);
                return VerificationFailed;
            }

            return Success;
        }

        var report = await Task.Run(
            () => P28VtecInspector.Inspect(image, profile, catalog.Profiles, confirmed, binding),
            cancellationToken).ConfigureAwait(false);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync($"Research scope: {report.Scope}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Exact baseline binding: {Kebab(report.BaselineBinding.Status)}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync(
            $"Revision-specific interpretation: {(report.InterpretationApplied ? "applied" : "not applied")}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync("Private research report written.").ConfigureAwait(false);

        await _error.WriteLineAsync(
            "warning: a private exact-byte binding is analyst-declared research evidence, not factory authentication or a trusted public ROM identity.")
            .ConfigureAwait(false);
        if (!report.InterpretationApplied)
        {
            await _error.WriteLineAsync(
                "warning: revision-specific interpretation was not applied; the report contains only the neutral raw byte window.")
                .ConfigureAwait(false);
        }

        await _error.WriteLineAsync(
            "warning: this inspection is read-only, PC-inspection-only, and not flash-ready.")
            .ConfigureAwait(false);

        return report.BaselineBinding.Status == P28BaselineBindingStatus.Mismatched
            ? VerificationFailed
            : Success;
    }

    private async Task<int> P28VtecPlanAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly("profile", "baseline-binding", "slot", "raw-value", "output", "confirm-profile");
        command.RequirePositionals(
            1,
            "hondaecu research p28-vtec plan <input.bin> --profile p28-304 --confirm-profile --baseline-binding <private-binding.json> --slot <slot-id> --raw-value <0..255> --output <private-plan.json>");
        if (!command.HasFlag("confirm-profile"))
        {
            throw new CliUsageException("P28 raw-threshold planning requires --confirm-profile.");
        }

        var inputPath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var outputPath = ResolvePath(command.Required("output"));
        var slotId = command.Required("slot");
        var rawValue = ParseStrictRawByte(command.Required("raw-value"));
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        ProtectNewResearchDestination(outputPath, inputPath, bindingPath, profile.SourcePath);

        var input = await Task.Run(() => RomImage.Load(inputPath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(
            () => P28ExactBaselineBinding.Load(bindingPath),
            cancellationToken).ConfigureAwait(false);
        var plan = await Task.Run(
            () => P28RawThresholdEditor.CreatePlan(
                input,
                profile,
                binding,
                true,
                slotId,
                rawValue),
            cancellationToken).ConfigureAwait(false);
        await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync("Private one-slot raw-threshold plan written.").ConfigureAwait(false);
        await WriteP28PcOnlyWarningsAsync().ConfigureAwait(false);
        return Success;
    }

    private async Task<int> P28VtecApplyAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal) { "confirm-pc-only", "confirm-profile" };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly(
            "profile",
            "baseline-binding",
            "plan",
            "output",
            "report",
            "confirm-pc-only",
            "confirm-profile");
        command.RequirePositionals(
            1,
            "hondaecu research p28-vtec apply <baseline.bin> --plan <private-plan.json> --baseline-binding <private-binding.json> --confirm-pc-only --output <new-private-output.bin> --report <private-patch-report.json> [--profile p28-304] [--confirm-profile]");
        if (!command.HasFlag("confirm-pc-only"))
        {
            throw new CliUsageException("P28 raw-threshold application requires --confirm-pc-only.");
        }
        _ = command.HasFlag("confirm-profile");

        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var planPath = ResolvePath(command.Required("plan"));
        var outputPath = ResolvePath(command.Required("output"));
        var reportPath = ResolvePath(command.Required("report"));
        var plan = await Task.Run(() => P28RawThresholdPlan.Load(planPath), cancellationToken).ConfigureAwait(false);
        var requestedProfile = command.Optional("profile");
        if (requestedProfile is not null &&
            !string.Equals(requestedProfile, plan.ProfileId, StringComparison.Ordinal))
        {
            throw new CliUsageException("Option '--profile' must match the profile recorded in the validated plan.");
        }

        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(plan.ProfileId);
        var protectedPaths = new[] { baselinePath, bindingPath, planPath, profile.SourcePath! };
        ProtectNewResearchDestination(outputPath, protectedPaths.Append(reportPath).ToArray());
        ProtectNewResearchDestination(reportPath, protectedPaths.Append(outputPath).ToArray());

        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(
            () => P28ExactBaselineBinding.Load(bindingPath),
            cancellationToken).ConfigureAwait(false);
        var result = await Task.Run(
            () => P28RawThresholdEditor.Apply(baseline, profile, binding, plan),
            cancellationToken).ConfigureAwait(false);
        await Task.Run(
            () => P28RawThresholdEditor.WriteAtomic(
                result,
                outputPath,
                reportPath,
                protectedPaths),
            cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync("PC-only derived ROM and private patch report written.").ConfigureAwait(false);
        await WriteP28PcOnlyWarningsAsync().ConfigureAwait(false);
        return Success;
    }

    private async Task<int> P28VtecVerifyAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("baseline", "baseline-binding", "plan", "report", "output");
        command.RequirePositionals(
            1,
            "hondaecu research p28-vtec verify <output.bin> --baseline <original.bin> --baseline-binding <private-binding.json> --plan <private-plan.json> --report <private-patch-report.json> [--output <private-verification.json>]");

        var outputRomPath = ResolvePath(command.Positionals[0]);
        var baselinePath = ResolvePath(command.Required("baseline"));
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var planPath = ResolvePath(command.Required("plan"));
        var patchReportPath = ResolvePath(command.Required("report"));
        var verificationOutputOption = command.Optional("output");
        var verificationOutputPath = verificationOutputOption is null
            ? null
            : ResolvePath(verificationOutputOption);

        var plan = await Task.Run(() => P28RawThresholdPlan.Load(planPath), cancellationToken).ConfigureAwait(false);
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(plan.ProfileId);
        if (verificationOutputPath is not null)
        {
            ProtectNewResearchDestination(
                verificationOutputPath,
                outputRomPath,
                baselinePath,
                bindingPath,
                planPath,
                patchReportPath,
                profile.SourcePath);
        }

        var output = await Task.Run(() => RomImage.Load(outputRomPath), cancellationToken).ConfigureAwait(false);
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(
            () => P28ExactBaselineBinding.Load(bindingPath),
            cancellationToken).ConfigureAwait(false);
        var patchReport = await Task.Run(
            () => P28RawThresholdPatchReport.Load(patchReportPath),
            cancellationToken).ConfigureAwait(false);
        var verification = await Task.Run(
            () => P28RawThresholdEditor.Verify(output, baseline, profile, binding, plan, patchReport),
            cancellationToken).ConfigureAwait(false);
        if (verificationOutputPath is not null)
        {
            await WriteJsonFileAsync(verificationOutputPath, verification, cancellationToken).ConfigureAwait(false);
        }

        await _output.WriteLineAsync(
            $"One-step raw-threshold lineage verification: {(verification.IsValid ? "passed" : "failed")}")
            .ConfigureAwait(false);
        await WriteP28PcOnlyWarningsAsync().ConfigureAwait(false);
        if (verification.IsValid)
        {
            return Success;
        }

        await WriteP28VerificationIssuesAsync(verification.Issues).ConfigureAwait(false);
        return VerificationFailed;
    }

    private static int ParseStrictRawByte(string value)
    {
        if (value.Length == 0 || value.Any(character => character is < '0' or > '9') ||
            !byte.TryParse(
                value,
                System.Globalization.NumberStyles.None,
                System.Globalization.CultureInfo.InvariantCulture,
                out var parsed))
        {
            throw new CliUsageException("Option '--raw-value' must be decimal digits representing an integer from 0 through 255.");
        }

        return parsed;
    }

    private static void ProtectNewResearchDestination(string destination, params string?[] protectedPaths)
    {
        foreach (var protectedPath in protectedPaths)
        {
            AtomicFile.EnsureDifferentPath(destination, protectedPath);
        }

        if (File.Exists(destination))
        {
            throw new IOException("Research output already exists; overwriting is not supported.");
        }
    }

    private async Task WriteP28PcOnlyWarningsAsync()
    {
        await _error.WriteLineAsync(
            "warning: the private exact-byte binding is an analyst declaration, not factory provenance or a trusted public identity.")
            .ConfigureAwait(false);
        await _error.WriteLineAsync(
            "warning: raw threshold bytes and compact-code predicates are not physical RPM or confirmed VTEC behavior.")
            .ConfigureAwait(false);
        await _error.WriteLineAsync(
            "warning: checksum remains unknown and is not repaired or bypassed; the derived file may fail the ECU's native integrity check. All artifacts are PC-inspection-only and not flash-ready.")
            .ConfigureAwait(false);
    }

    private async Task WriteP28VerificationIssuesAsync(IEnumerable<VerificationIssue> issues)
    {
        await _error.WriteLineAsync("verification failed: private one-step lineage did not match.")
            .ConfigureAwait(false);
        foreach (var issue in issues)
        {
            await _error.WriteLineAsync($"  [{issue.Code}] lineage check failed.").ConfigureAwait(false);
        }
    }
}
