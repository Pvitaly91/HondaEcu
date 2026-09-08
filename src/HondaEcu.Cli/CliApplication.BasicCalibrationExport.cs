using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28BasicCalibrationExportAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length < 2 || args[0] != "export" || args[1] is not ("plan" or "apply" or "verify" or "inspect"))
            throw new CliUsageException("Usage: research p28-calibration export <plan|apply|verify|inspect> <image> --profile p28-304 ...");
        var operation = args[1]; var planning = operation == "plan"; var apply = operation == "apply";
        var c = CommandLine.Parse(args[2..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile", "confirm-pc-only" });
        c.EnsureOnly(planning ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "settings", "output"] :
            apply ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "plan", "runner", "confirm-pc-only", "output", "saved-plan", "report"] :
            ["baseline", "profile", "baseline-binding", "compensation-definition", "plan", "report", "output"]);
        c.RequirePositionals(1, "research p28-calibration export <operation> <image>");
        if ((planning || apply) && !c.HasFlag("confirm-profile")) throw new CliUsageException("--confirm-profile required.");
        if (apply && !c.HasFlag("confirm-pc-only")) throw new CliUsageException("--confirm-pc-only required; never hardware authorization.");
        string Path(string name) => ResolvePath(c.Required(name));
        var imagePath = ResolvePath(c.Positionals[0]); var originalPath = planning || apply ? imagePath : Path("baseline");
        var bindingPath = Path("baseline-binding"); var locationPath = Path("compensation-definition");
        var settingsPath = planning ? Path("settings") : null; var planPath = planning ? null : Path("plan");
        var runnerPath = apply ? Path("runner") : null; var inputReceipt = planning || apply ? null : Path("report");
        var outputPath = Path("output"); var savedPlan = apply ? Path("saved-plan") : null; var outputReceipt = apply ? Path("report") : null;
        var input = await CaptureResearchExportAsync(c.Required("profile"), originalPath, imagePath, bindingPath, locationPath,
            planPath, runnerPath, inputReceipt, new[] { outputPath, savedPlan, outputReceipt }.OfType<string>().ToArray(),
            new[] { settingsPath }.OfType<string>().ToArray(), P28BasicCalibrationReceipt.MaximumBytes, cancellationToken).ConfigureAwait(false);
        P28BasicCalibrationPlan plan;
        if (planning)
        {
            var settings = P28BasicCalibrationSettings.Parse(input.Text(settingsPath!).TrimStart('\uFEFF'));
            plan = P28BasicCalibrationEditor.Preview(input.Original, input.Profile, input.Binding, true, input.Location, settings).Plan;
            input.Recheck(); await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            plan = P28BasicCalibrationPlan.Parse(input.Text(planPath!));
            if (apply)
            {
                var preview = P28BasicCalibrationEditor.Reproduce(input.Original, input.Profile, input.Binding, true, input.Location, plan);
                var token = await P28BasicCalibrationExecution.ValidateAsync(preview, runnerPath!, cancellationToken: cancellationToken).ConfigureAwait(false);
                input.Recheck(); var verification = P28BasicCalibrationWriter.Save(token, outputPath, savedPlan!, outputReceipt!, input.Paths, cancellationToken);
                if (!verification.IsValid) return VerificationFailed;
                var e = token.Evidence;
                await _output.WriteLineAsync($"Fresh strict A/B/C: VtecThresholdPrefix={e.VtecThresholdPrefix.Rows.Count}; fixed={e.LimiterAdaptive.FixedRuns.Sum(r => r.StrictMatches)}; adaptive={e.LimiterAdaptive.AdaptiveRuns.Sum(r => r.StrictMatches)}; idle={e.Idle.Runs.Sum(r => r.StrictMatches)}; checksum={e.Checksum.Count} x 512 invocations. Independent BIN/plan/receipt readback passed.").ConfigureAwait(false);
                foreach (var w in e.VtecThresholdPrefix.Witnesses) await _output.WriteLineAsync($"VTEC witness {w.SlotId}: code={w.Code}, bits={w.OldBits}->{w.NewBits}.").ConfigureAwait(false);
                foreach (var w in e.LimiterAdaptive.Witnesses) await _output.WriteLineAsync($"Limiter witness {w.Group}: threshold={w.OldThreshold}->{w.NewThreshold}, request={w.OldRequest}->{w.NewRequest}.").ConfigureAwait(false);
                foreach (var w in e.Idle.Witnesses) await _output.WriteLineAsync($"Idle witness {w.Table}: target={w.OldTarget}->{w.NewTarget}, error={w.OldError}->{w.NewError}, sign={w.OldSign}->{w.NewSign}.").ConfigureAwait(false);
            }
            else
            {
                var child = RomImage.FromBytes(input.Snapshot[imagePath], imagePath); var receipt = P28BasicCalibrationReceipt.Parse(input.Text(inputReceipt!));
                object result = operation == "inspect" ? P28BasicCalibrationWriter.InspectDerived(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt) :
                    P28BasicCalibrationWriter.Verify(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt);
                input.Recheck(); await WriteJsonFileAsync(outputPath, result, cancellationToken).ConfigureAwait(false);
                await _output.WriteLineAsync("Full original-parent tuple consistent; historical evidence only, fresh execution NotRun.").ConfigureAwait(false);
            }
        }
        foreach (var g in plan.Groups)
        {
            await _output.WriteLineAsync($"{g.Id}: requested={g.Requested}, effectivelyChanged={g.EffectivelyChanged}.").ConfigureAwait(false);
            if (g.Vtec is { } v) foreach (var slot in P28ThresholdLogic.GetSlots())
                    await _output.WriteLineAsync($"  {slot.Id}: raw code {v.OriginalBytes[slot.Offset - P28ThresholdLogic.BlockOffset]}->{v.NewBytes[slot.Offset - P28ThresholdLogic.BlockOffset]}.").ConfigureAwait(false);
            if (g.Limiter is { } l)
            {
                foreach (var w in l.FixedOperands) await _output.WriteLineAsync($"  {w.FieldId}: raw period {w.OriginalWord}->{w.NewWord}.").ConfigureAwait(false);
                foreach (var w in l.AdaptiveWords) await _output.WriteLineAsync($"  {w.FieldId}: raw base {w.OldWord}->{w.NewWord}.").ConfigureAwait(false);
            }
            if (g.Idle is { } t) foreach (var cell in t.Cells)
                    await _output.WriteLineAsync($"  {cell.FieldId}: raw period {cell.OldValue}->{cell.NewValue}; axis={cell.Axis} unchanged.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync($"Residues A/B/C={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; diff={plan.ExpectedDiff.Count}; one compensation {plan.Compensation.OldByte}->{plan.Compensation.NewByte}.").ConfigureAwait(false);
        foreach (var d in plan.ExpectedDiff) await _output.WriteLineAsync($"0x{d.Offset:X4}: {d.OldByte:X2}->{d.NewByte:X2}").ConfigureAwait(false);
        foreach (var suite in plan.Suites) await _output.WriteLineAsync($"{suite.Id}: {suite.Scope}.").ConfigureAwait(false);
        await _output.WriteLineAsync($"{plan.Readiness}; physicalRpmAvailable=false. Independent local software suites, not one ECU main loop. {(planning ? "Preview only; native execution NotRun; no BIN written." : "")}").ConfigureAwait(false);
        return Success;
    }
}
