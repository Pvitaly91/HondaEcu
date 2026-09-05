using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28VtecExecuteCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "output", "allow-assumption", "derived", "plan", "patch-report");
        command.RequirePositionals(1,
            "hondaecu research p28-vtec execute-check <baseline> --profile p28-304 --confirm-profile --baseline-binding <private-json> --runner <rust-executable> --output <private-json> [--allow-assumption oki.add-er3-a] [--derived <output> --plan <private-json> --patch-report <private-json>]");
        if (!command.HasFlag("confirm-profile"))
        {
            throw new CliUsageException("Byte execution requires --confirm-profile.");
        }
        var assumption = command.Optional("allow-assumption");
        if (assumption is not null && assumption != P28ByteExecutionValidator.AddAssumption)
        {
            throw new CliUsageException("The only supported explicit assumption is oki.add-er3-a.");
        }
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner"));
        var outputPath = ResolvePath(command.Required("output"));
        var derivedOption = command.Optional("derived");
        var planOption = command.Optional("plan");
        var patchReportOption = command.Optional("patch-report");
        var lineageCount = new[] { derivedOption, planOption, patchReportOption }.Count(value => value is not null);
        if (lineageCount is not (0 or 3))
        {
            throw new CliUsageException("Derived execution requires --derived, --plan and --patch-report together.");
        }
        var derivedPath = derivedOption is null ? null : ResolvePath(derivedOption);
        var planPath = planOption is null ? null : ResolvePath(planOption);
        var patchReportPath = patchReportOption is null ? null : ResolvePath(patchReportOption);
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        ProtectNewResearchDestination(outputPath, baselinePath, bindingPath, runnerPath, derivedPath, planPath, patchReportPath, profile.SourcePath);
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);
        var derived = derivedPath is null ? null : await Task.Run(() => RomImage.Load(derivedPath), cancellationToken).ConfigureAwait(false);
        var plan = planPath is null ? null : await Task.Run(() => P28RawThresholdPlan.Load(planPath), cancellationToken).ConfigureAwait(false);
        var patchReport = patchReportPath is null ? null : await Task.Run(() => P28RawThresholdPatchReport.Load(patchReportPath), cancellationToken).ConfigureAwait(false);
        P28ExecutionReport report;
        try
        {
            report = await P28ByteExecutionValidator.ExecuteAsync(baseline, profile, binding, true, runnerPath,
                assumption is not null, derived, plan, patchReport, cancellationToken: cancellationToken).ConfigureAwait(false);
        }
        catch (SliceProcessException exception)
        {
            await _error.WriteLineAsync($"error: slice runner {exception.Failure}: {exception.Message}").ConfigureAwait(false);
            return OperationError;
        }
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"Seeded ROM slice execution: {report.Mode}; private report written.").ConfigureAwait(false);
        await _output.WriteLineAsync(
            $"Compact: {report.Compact.CompletedWithoutAssumptions} matches; {report.Compact.ConditionalMatches} conditional matches; {report.Compact.StoppedUnresolved} unresolved (not passed); {report.Compact.Mismatches} mismatches; {report.Compact.ExecutionErrors} execution errors; {report.Compact.BudgetExceeded} budget exceeded.").ConfigureAwait(false);
        await _output.WriteLineAsync("Software byte execution only; full ECU boot and hardware execution were not performed.").ConfigureAwait(false);
        await WriteP28PcOnlyWarningsAsync().ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
