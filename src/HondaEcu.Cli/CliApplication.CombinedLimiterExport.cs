using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28CombinedLimiterExportAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0 || args[0] is not ("plan" or "apply" or "verify" or "inspect"))
            throw new CliUsageException("Usage: research p28-limiter combined-export <plan|apply|verify|inspect> <image> --profile p28-304 ...");
        var operation = args[0]; var planning = operation == "plan"; var apply = operation == "apply";
        var c = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile", "confirm-pc-only" });
        c.EnsureOnly(planning ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "settings", "output"] :
            apply ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "plan", "runner", "confirm-pc-only", "output", "saved-plan", "report"] :
            ["baseline", "profile", "baseline-binding", "compensation-definition", "plan", "report", "output"]);
        c.RequirePositionals(1, "research p28-limiter combined-export <operation> <image>");
        if ((planning || apply) && !c.HasFlag("confirm-profile")) throw new CliUsageException("--confirm-profile is required with exact original binding.");
        if (apply && !c.HasFlag("confirm-pc-only")) throw new CliUsageException("Export requires --confirm-pc-only; never hardware authorization.");
        string Path(string name) => ResolvePath(c.Required(name));
        var imagePath = ResolvePath(c.Positionals[0]); var originalPath = planning || apply ? imagePath : Path("baseline");
        var bindingPath = Path("baseline-binding"); var locationPath = Path("compensation-definition");
        var settingsPath = planning ? Path("settings") : null; var planPath = planning ? null : Path("plan");
        var runnerPath = apply ? Path("runner") : null; var inputReceipt = planning || apply ? null : Path("report");
        var outputPath = Path("output"); var savedPlan = apply ? Path("saved-plan") : null; var outputReceipt = apply ? Path("report") : null;
        var input = await CaptureResearchExportAsync(c.Required("profile"), originalPath, imagePath, bindingPath, locationPath,
            planPath, runnerPath, inputReceipt, new[] { outputPath, savedPlan, outputReceipt }.OfType<string>().ToArray(),
            new[] { settingsPath }.OfType<string>().ToArray(), P28CombinedLimiterReceipt.MaximumJsonBytes, cancellationToken).ConfigureAwait(false);
        P28CombinedLimiterPlan plan;
        if (planning)
        {
            var settings = P28CombinedLimiterSettings.Parse(input.Text(settingsPath!).TrimStart('\uFEFF'));
            plan = P28CombinedLimiterEditor.Preview(input.Original, input.Profile, input.Binding, true, input.Location, settings).Plan;
            input.Recheck(); await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            plan = P28CombinedLimiterPlan.Parse(input.Text(planPath!));
            if (apply)
            {
                var preview = P28CombinedLimiterEditor.Reproduce(input.Original, input.Profile, input.Binding, true, input.Location, plan);
                var token = await P28CombinedLimiterExecution.ValidateAsync(preview, runnerPath!, cancellationToken: cancellationToken).ConfigureAwait(false);
                input.Recheck();
                var verification = P28CombinedLimiterWriter.Save(token, outputPath, savedPlan!, outputReceipt!, input.Paths, cancellationToken);
                if (!verification.IsValid) return VerificationFailed;
                await _output.WriteLineAsync($"Fresh combined A/B/C: {token.Evidence.Runs.Sum(r => r.StrictMatches)} adaptive and {token.Evidence.LimiterRuns.Sum(r => r.StrictMatches)} fixed strict image/scratch calls; 9 full 512-invocation checksum sequences. BIN/plan/receipt readback passed.").ConfigureAwait(false);
                foreach (var w in token.Evidence.Witnesses) await _output.WriteLineAsync($"Witness {w.Group}: {w.ScenarioId}, scratch {w.ScratchPattern}, call {w.Index}, threshold {w.OldThreshold}->{w.NewThreshold}, request {w.OldRequest}->{w.NewRequest}.").ConfigureAwait(false);
            }
            else
            {
                var child = RomImage.FromBytes(input.Snapshot[imagePath], imagePath); var receipt = P28CombinedLimiterReceipt.Parse(input.Text(inputReceipt!));
                object result = operation == "inspect" ? P28CombinedLimiterWriter.InspectDerived(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt) :
                    P28CombinedLimiterWriter.Verify(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt);
                input.Recheck(); await WriteJsonFileAsync(outputPath, result, cancellationToken).ConfigureAwait(false);
                await _output.WriteLineAsync("Full original-parent tuple verified; receipt consistency is historical, fresh execution NotRun.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("Combined limiter research edit").ConfigureAwait(false);
        foreach (var g in plan.Groups)
        {
            await _output.WriteLineAsync($"{g.Id}: requested={g.Requested}, effectivelyChanged={g.EffectivelyChanged}, {g.PolicyResult}.").ConfigureAwait(false);
            foreach (var w in g.FixedOperands) await _output.WriteLineAsync($"  {w.FieldId}: {w.OriginalWord}->{w.NewWord}").ConfigureAwait(false);
            foreach (var w in g.AdaptiveWords) await _output.WriteLineAsync($"  {w.FieldId}: {w.OldWord}->{w.NewWord}; origin/coefficient unchanged.").ConfigureAwait(false);
            foreach (var d in g.DomainChecks) await _output.WriteLineAsync($"  Domain={d.CheckedInputs}, max targets={d.MaximumCutTarget}/{d.MaximumResumeTarget}, minimum gap={d.MinimumTargetGap}, no wrap={d.NoTargetWrap}, ordered={d.StrictTargetOrder}.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync($"Residues A/B/C={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; changed bytes={plan.ExpectedDiff.Count}; one compensation 0x{plan.Compensation.OldByte:X2}->0x{plan.Compensation.NewByte:X2}.").ConfigureAwait(false);
        foreach (var d in plan.ExpectedDiff) await _output.WriteLineAsync($"0x{d.Offset:X4}: 0x{d.OldByte:X2} -> 0x{d.NewByte:X2}").ConfigureAwait(false);
        await _output.WriteLineAsync($"{plan.Readiness}; physicalRpmAvailable=false. GUI r3 paused/NotRun; hardware/full boot NotRun. {(planning ? "Preview only; no firmware written or native execution claimed." : "")}").ConfigureAwait(false);
        return Success;
    }
}
