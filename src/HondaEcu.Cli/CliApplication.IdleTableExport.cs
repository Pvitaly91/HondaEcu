using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28IdleTableExportAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0 || args[0] is not ("plan" or "apply" or "verify" or "inspect"))
            throw new CliUsageException("Usage: research p28-idle export <plan|apply|verify|inspect> <image> --profile p28-304 ...");
        var operation = args[0]; var planning = operation == "plan"; var apply = operation == "apply";
        var c = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile", "confirm-pc-only" });
        c.EnsureOnly(planning ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "settings", "output"] :
            apply ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "plan", "runner", "confirm-pc-only", "output", "saved-plan", "report"] :
            ["baseline", "profile", "baseline-binding", "compensation-definition", "plan", "report", "output"]);
        c.RequirePositionals(1, "research p28-idle export <operation> <image>");
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
            new[] { settingsPath }.OfType<string>().ToArray(), P28IdleTableReceipt.MaximumJsonBytes, cancellationToken).ConfigureAwait(false);
        P28IdleTablePlan plan;
        if (planning)
        {
            var settings = P28IdleTableSettings.Parse(input.Text(settingsPath!).TrimStart('\uFEFF'));
            plan = P28IdleTableEditor.Preview(input.Original, input.Profile, input.Binding, true, input.Location, settings).Plan;
            input.Recheck(); await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            plan = P28IdleTablePlan.Parse(input.Text(planPath!));
            if (apply)
            {
                var preview = P28IdleTableEditor.Reproduce(input.Original, input.Profile, input.Binding, true, input.Location, plan);
                var token = await P28IdleTableExecution.ValidateAsync(preview, runnerPath!, cancellationToken: cancellationToken).ConfigureAwait(false);
                input.Recheck();
                var verification = P28IdleTableWriter.Save(token, outputPath, savedPlan!, outputReceipt!, input.Paths, cancellationToken);
                if (!verification.IsValid) return VerificationFailed;
                await _output.WriteLineAsync($"Fresh idle A/B/C: {token.Evidence.Runs.Sum(r => r.StrictMatches)} strict image/scratch calls; 9 full 512-invocation checksum sequences. BIN/plan/receipt readback passed.").ConfigureAwait(false);
                foreach (var w in token.Evidence.Witnesses) await _output.WriteLineAsync($"Witness {w.Table}: {w.ScenarioId}, scratch {w.ScratchPattern}, call {w.Index}, target {w.OldTarget}->{w.NewTarget}, error {w.OldError}->{w.NewError}, sign {w.OldSign}->{w.NewSign}.").ConfigureAwait(false);
                foreach (var effect in token.Evidence.CellEffects) await _output.WriteLineAsync($"Cell {effect.FieldId}: {effect.Effect}={effect.Count}; combined observations, not individual-cell causal attribution.").ConfigureAwait(false);
            }
            else
            {
                var child = RomImage.FromBytes(input.Snapshot[imagePath], imagePath); var receipt = P28IdleTableReceipt.Parse(input.Text(inputReceipt!));
                object result = operation == "inspect" ? P28IdleTableWriter.InspectDerived(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt) :
                    P28IdleTableWriter.Verify(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt);
                input.Recheck(); await WriteJsonFileAsync(outputPath, result, cancellationToken).ConfigureAwait(false);
                await _output.WriteLineAsync("Full original-parent tuple verified; receipt consistency is historical, fresh execution NotRun.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("Idle table research edit: numeric raw periods, not physical RPM").ConfigureAwait(false);
        foreach (var t in plan.Tables)
        {
            await _output.WriteLineAsync($"{(t.Id == "base" ? "Base table" : "Late replacement table")}: requested={t.Requested}, effectivelyChanged={t.EffectivelyChanged}.").ConfigureAwait(false);
            foreach (var cell in t.Cells) await _output.WriteLineAsync($"  {cell.FieldId}: axis={cell.Axis} unchanged; raw period {cell.OldValue}->{cell.NewValue}; changed={cell.OldValue != cell.NewValue}.").ConfigureAwait(false);
            foreach (var d in t.DomainChecks) await _output.WriteLineAsync($"  Arithmetic domain={d.CheckedInputs}, result range={d.Minimum}..{d.Maximum}, max product={d.MaximumProduct}, bounds/nodes={d.BoundsAndNodesVerified}; {string.Join(", ", d.SegmentDirections)}.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync("Base lookup may be bypassed by original immediate overrides or replaced by late lookup. DATA027A is separate; axes/pointers/overrides/peaks unchanged. Native consumer uses actual final025C.").ConfigureAwait(false);
        await _output.WriteLineAsync($"Residues A/B/C={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; changed bytes={plan.ExpectedDiff.Count}; one compensation 0x{plan.Compensation.OldByte:X2}->0x{plan.Compensation.NewByte:X2}.").ConfigureAwait(false);
        foreach (var d in plan.ExpectedDiff) await _output.WriteLineAsync($"0x{d.Offset:X4}: 0x{d.OldByte:X2} -> 0x{d.NewByte:X2}").ConfigureAwait(false);
        await _output.WriteLineAsync($"{plan.Readiness}; physicalRpmAvailable=false. GUI r3 paused/NotRun; hardware/full boot NotRun. {(planning ? "Preview only; no firmware written or native execution claimed." : "")}").ConfigureAwait(false);
        return Success;
    }
}
