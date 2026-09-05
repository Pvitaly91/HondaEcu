using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28VtecProducerCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "output", "allow-assumption", "derived", "plan", "patch-report", "scaling");
        command.RequirePositionals(1,
            "hondaecu research p28-vtec producer-check <baseline> --profile p28-304 --confirm-profile --baseline-binding <private-json> --runner <rust-executable> --output <private-json> [--allow-assumption oki.add-er1-a] [--allow-assumption oki.add-er3-a] [--derived <M1c-child> --plan <private-json> --patch-report <private-json>] [--scaling <private-json>]");
        if (!command.HasFlag("confirm-profile"))
        {
            throw new CliUsageException("Producer execution requires --confirm-profile.");
        }
        IReadOnlyList<string> assumptions;
        try
        {
            assumptions = P28ProducerValidator.ValidateAssumptions(command.Many("allow-assumption"));
        }
        catch (ArgumentException)
        {
            throw new CliUsageException("Each explicit --allow-assumption may name oki.add-er1-a or oki.add-er3-a once; no other or global unknown permission is supported.");
        }
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner"));
        var outputPath = ResolvePath(command.Required("output"));
        var derivedOption = command.Optional("derived");
        var planOption = command.Optional("plan");
        var patchReportOption = command.Optional("patch-report");
        var scalingOption = command.Optional("scaling");
        var lineageCount = new[] { derivedOption, planOption, patchReportOption }.Count(value => value is not null);
        if (lineageCount is not (0 or 3))
        {
            throw new CliUsageException("Producer child comparison requires --derived, --plan and --patch-report together.");
        }
        var derivedPath = derivedOption is null ? null : ResolvePath(derivedOption);
        var planPath = planOption is null ? null : ResolvePath(planOption);
        var patchReportPath = patchReportOption is null ? null : ResolvePath(patchReportOption);
        var scalingPath = scalingOption is null ? null : ResolvePath(scalingOption);
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        ProtectNewResearchDestination(outputPath, baselinePath, bindingPath, runnerPath, derivedPath, planPath, patchReportPath, scalingPath, profile.SourcePath);
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var binding = await Task.Run(() => P28ExactBaselineBinding.Load(bindingPath), cancellationToken).ConfigureAwait(false);
        var derived = derivedPath is null ? null : await Task.Run(() => RomImage.Load(derivedPath), cancellationToken).ConfigureAwait(false);
        var plan = planPath is null ? null : await Task.Run(() => P28RawThresholdPlan.Load(planPath), cancellationToken).ConfigureAwait(false);
        var patchReport = patchReportPath is null ? null : await Task.Run(() => P28RawThresholdPatchReport.Load(patchReportPath), cancellationToken).ConfigureAwait(false);
        var scaling = JsonSerializer.SerializeToElement(P28PhysicalScaling.Analyze(scalingPath), JsonDefaults.Create(false));
        P28ProducerExecutionReport report;
        try
        {
            report = await P28ProducerValidator.ExecuteAsync(baseline, profile, binding, true, runnerPath, assumptions,
                derived, plan, patchReport, scaling, cancellationToken: cancellationToken).ConfigureAwait(false);
        }
        catch (SliceProcessException exception)
        {
            await _error.WriteLineAsync($"error: producer runner {exception.Failure}: {exception.Message}").ConfigureAwait(false);
            return OperationError;
        }
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"Producer byte execution: {report.Mode}; private producer/composition report written.").ConfigureAwait(false);
        await _output.WriteLineAsync($"G: {report.Producer.MatchesWithoutAssumptions} matches; {report.Producer.ConditionalMatches} conditional; {report.Producer.StoppedUnresolved} unresolved (not passed); {report.Producer.Mismatches} mismatches; {report.Producer.ExecutionErrors} errors; {report.Producer.BudgetExceeded} budget exceeded.").ConfigureAwait(false);
        await _output.WriteLineAsync($"G→F: {report.ProducerToCompact.MatchesWithoutAssumptions} matches; {report.ProducerToCompact.ConditionalMatches} conditional; {report.ProducerToCompact.StoppedUnresolved} unresolved; {report.ProducerToCompact.NotRun} not run.").ConfigureAwait(false);
        await _output.WriteLineAsync("Physical scaling has no implicit hardware defaults; any preview is conditional, not measured RPM.").ConfigureAwait(false);
        await WriteP28PcOnlyWarningsAsync().ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
