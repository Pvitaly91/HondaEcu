using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28UnifiedCalibrationExportAsync(string[] args,
        CancellationToken cancellationToken)
    {
        if (args.Length == 0 || args[0] is not ("plan" or "apply" or "verify" or "inspect"))
            throw new CliUsageException("Usage: research p28-calibration combined-export <plan|apply|verify|inspect> <image> --profile p28-304 ...");
        var operation = args[0]; var planning = operation == "plan"; var apply = operation == "apply";
        var command = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal)
            { "confirm-profile", "confirm-pc-only" });
        command.EnsureOnly(planning
            ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "settings", "output"]
            : apply
                ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "plan", "runner",
                    "confirm-pc-only", "output", "saved-plan", "report"]
                : ["baseline", "profile", "baseline-binding", "compensation-definition", "plan", "report", "output"]);
        command.RequirePositionals(1, "research p28-calibration combined-export <operation> <image>");
        if ((planning || apply) && !command.HasFlag("confirm-profile"))
            throw new CliUsageException("--confirm-profile is required with the exact original binding.");
        if (apply && !command.HasFlag("confirm-pc-only"))
            throw new CliUsageException("Unified calibration export requires --confirm-pc-only; this never grants hardware authorization.");

        string PathFor(string name) => ResolvePath(command.Required(name));
        var imagePath = ResolvePath(command.Positionals[0]);
        var originalPath = planning || apply ? imagePath : PathFor("baseline");
        var bindingPath = PathFor("baseline-binding");
        var locationPath = PathFor("compensation-definition");
        var settingsPath = planning ? PathFor("settings") : null;
        var planPath = planning ? null : PathFor("plan");
        var runnerPath = apply ? PathFor("runner") : null;
        var inputReceipt = planning || apply ? null : PathFor("report");
        var outputPath = PathFor("output");
        var savedPlan = apply ? PathFor("saved-plan") : null;
        var outputReceipt = apply ? PathFor("report") : null;
        var input = await CaptureResearchExportAsync(command.Required("profile"), originalPath,
            imagePath, bindingPath, locationPath, planPath, runnerPath, inputReceipt,
            new[] { outputPath, savedPlan, outputReceipt }.OfType<string>().ToArray(),
            new[] { settingsPath }.OfType<string>().ToArray(),
            P28UnifiedCalibrationReceipt.MaximumBytes, cancellationToken).ConfigureAwait(false);

        P28UnifiedCalibrationPlan plan;
        if (planning)
        {
            var settings = P28UnifiedCalibrationSettings.Parse(input.Text(settingsPath!).TrimStart('\uFEFF'));
            plan = P28UnifiedCalibrationEditor.Preview(input.Original, input.Profile, input.Binding,
                true, input.Location, settings).Plan;
            input.Recheck();
            await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            plan = P28UnifiedCalibrationPlan.Parse(input.Text(planPath!));
            if (apply)
            {
                var preview = P28UnifiedCalibrationEditor.Reproduce(input.Original, input.Profile,
                    input.Binding, true, input.Location, plan);
                var token = await P28UnifiedCalibrationExecution.ValidateAsync(preview, runnerPath!,
                    cancellationToken: cancellationToken).ConfigureAwait(false);
                input.Recheck();
                var verification = P28UnifiedCalibrationWriter.Save(token, outputPath, savedPlan!,
                    outputReceipt!, protectedPaths: input.Paths, cancellationToken: cancellationToken);
                if (!verification.IsValid) return VerificationFailed;
                var evidence = token.Evidence;
                await _output.WriteLineAsync($"Fresh unified A/B/C: VTEC={evidence.Basic.VtecThresholdPrefix.Rows.Count}; fixed={evidence.Basic.LimiterAdaptive.FixedRuns.Sum(run => run.StrictMatches)}; adaptive={evidence.Basic.LimiterAdaptive.AdaptiveRuns.Sum(run => run.StrictMatches)}; idle={evidence.Basic.Idle.Runs.Sum(run => run.StrictMatches)}; fuel={evidence.Fuel.Runs.Sum(run => run.StrictMatches)}; ignition-factor0={evidence.Ignition.MainRuns.Sum(run => run.StrictMatches)}; ignition-factors={evidence.Ignition.FactorRuns.Sum(run => run.StrictMatches)}; one checksumBatch={evidence.Checksum.Count} x 512 invocations.").ConfigureAwait(false);
                await _output.WriteLineAsync("One BIN/plan/receipt publication and independent readback passed.").ConfigureAwait(false);
            }
            else
            {
                var child = RomImage.FromBytes(input.Snapshot[imagePath], imagePath);
                var receipt = P28UnifiedCalibrationReceipt.Parse(input.Text(inputReceipt!));
                object result = operation == "inspect"
                    ? P28UnifiedCalibrationWriter.InspectDerived(child, input.Original, input.Profile,
                        input.Binding, input.Location, plan, receipt)
                    : P28UnifiedCalibrationWriter.Verify(child, input.Original, input.Profile,
                        input.Binding, input.Location, plan, receipt);
                input.Recheck();
                await WriteJsonFileAsync(outputPath, result, cancellationToken).ConfigureAwait(false);
                await _output.WriteLineAsync("Full original-parent tuple is consistent; historical evidence only, fresh execution NotRun.").ConfigureAwait(false);
            }
        }

        await _output.WriteLineAsync($"Groups requested/changed={plan.RequestedGroupCount}/{plan.ChangedGroupCount}; map cells requested/changed={plan.RequestedMapCellCount}/{plan.ChangedMapCellCount}.").ConfigureAwait(false);
        foreach (var group in plan.Groups)
            await _output.WriteLineAsync($"{group.Family}/{group.Id}: requested={group.Requested}, byteChanged={group.ByteChanged}, behaviorChanged={group.BehaviorChanged}, values={group.RequestedValueCount}, changed={group.ChangedValueCount}.").ConfigureAwait(false);
        await _output.WriteLineAsync($"Residues A/B/C={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; actual diff={plan.ExpectedDiff.Count}; one compensation 0x{plan.Compensation.Offset:X4} {plan.Compensation.OldByte:X2}->{plan.Compensation.NewByte:X2}.").ConfigureAwait(false);
        foreach (var diff in plan.ExpectedDiff)
            await _output.WriteLineAsync($"0x{diff.Offset:X4}: 0x{diff.OldByte:X2} -> 0x{diff.NewByte:X2}").ConfigureAwait(false);
        foreach (var suite in plan.Suites)
            await _output.WriteLineAsync($"{suite.Id}: {suite.Scope}.").ConfigureAwait(false);
        await _output.WriteLineAsync($"{plan.Readiness}; physicalRpmAvailable=false; physical degrees unavailable; GUI r3 paused/NotRun; D1 GUI NotRun; D2 NotStarted; hardware/full boot NotRun. {(planning ? "Preview only; native execution NotRun and no firmware written." : string.Empty)}").ConfigureAwait(false);
        return Success;
    }
}
