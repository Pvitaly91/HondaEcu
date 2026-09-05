using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28ChecksumCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "output", "allow-assumption", "derived", "plan", "patch-report");
        command.RequirePositionals(1,
            "hondaecu research p28-vtec checksum-check <baseline> --profile p28-304 --confirm-profile --baseline-binding <private-json> --output <private-json> [--runner <rust-executable>] [--derived <M1c-child> --plan <private-json> --patch-report <private-json>]");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("Scoped native checksum requires --confirm-profile and the original research binding.");
        try { _ = P28NativeChecksumVerifier.ValidateAssumptions(command.Many("allow-assumption")); }
        catch (ArgumentException) { throw new CliUsageException("Checksum execution defines no instruction assumptions. er1/er3 permissions are not applicable."); }
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var outputPath = ResolvePath(command.Required("output"));
        var runnerOption = command.Optional("runner");
        var runnerPath = runnerOption is null ? null : ResolvePath(runnerOption);
        var childOption = command.Optional("derived");
        var planOption = command.Optional("plan");
        var patchOption = command.Optional("patch-report");
        var lineageCount = new[] { childOption, planOption, patchOption }.Count(value => value is not null);
        if (lineageCount is not (0 or 3)) throw new CliUsageException("Checksum child comparison requires --derived, --plan and --patch-report together.");
        var childPath = childOption is null ? null : ResolvePath(childOption);
        var planPath = planOption is null ? null : ResolvePath(planOption);
        var patchPath = patchOption is null ? null : ResolvePath(patchOption);
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        ProtectNewResearchDestination(outputPath, baselinePath, bindingPath, runnerPath, childPath, planPath, patchPath, profile.SourcePath);
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);
        var child = childPath is null ? null : await Task.Run(() => RomImage.Load(childPath), cancellationToken).ConfigureAwait(false);
        var plan = planPath is null ? null : await Task.Run(() => P28RawThresholdPlan.Load(planPath), cancellationToken).ConfigureAwait(false);
        var patch = patchPath is null ? null : await Task.Run(() => P28RawThresholdPatchReport.Load(patchPath), cancellationToken).ConfigureAwait(false);
        var report = await Task.Run(() => P28NativeChecksumVerifier.CheckAsync(baseline, profile, binding, true,
            runnerPath, derived: child, plan: plan, patchReport: patch, cancellationToken: cancellationToken), cancellationToken).ConfigureAwait(false);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync("Scoped native ROM checksum research; not a VTEC-only checksum. Private report written.").ConfigureAwait(false);
        foreach (var item in report.Cases)
            await _output.WriteLineAsync($"{item.Id}: {item.Disposition}; arithmetic residue {(item.Arithmetic.ResidueMatches ? "zero" : "nonzero")}; coverage {item.Arithmetic.CoveredByteCount} bytes.").ConfigureAwait(false);
        await _output.WriteLineAsync($"Byte execution: {report.Counts.MatchesWithoutAssumptions} matches; {report.Counts.ConditionalMatches} conditional; {report.Counts.Unresolved} unresolved; {report.Counts.Mismatches} mismatches; {report.Counts.ExecutionErrors} errors; {report.Counts.BudgetExceeded} budget; {report.Counts.NotRun} not-run.").ConfigureAwait(false);
        await _output.WriteLineAsync("No repair or bypass. No full ECU boot/hardware proof. PcInspectionOnly / NotFlashReady.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
