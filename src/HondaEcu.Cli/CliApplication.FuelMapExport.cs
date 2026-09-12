using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28FuelMapExportAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0 || args[0] is not ("plan" or "apply" or "verify" or "inspect"))
            throw new CliUsageException("Usage: research p28-fuel export <plan|apply|verify|inspect> <image> --profile p28-304 ...");
        var operation = args[0]; var planning = operation == "plan"; var apply = operation == "apply";
        var command = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile", "confirm-pc-only" });
        command.EnsureOnly(planning ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "settings", "output"] :
            apply ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "plan", "runner", "confirm-pc-only", "output", "saved-plan", "report"] :
            ["baseline", "profile", "baseline-binding", "compensation-definition", "plan", "report", "output"]);
        command.RequirePositionals(1, "research p28-fuel export <operation> <image>");
        if ((planning || apply) && !command.HasFlag("confirm-profile"))
            throw new CliUsageException("--confirm-profile is required with the exact original binding.");
        if (apply && !command.HasFlag("confirm-pc-only"))
            throw new CliUsageException("Fuel-map export requires --confirm-pc-only; this never grants hardware authorization.");
        string PathFor(string name) => ResolvePath(command.Required(name));
        var imagePath = ResolvePath(command.Positionals[0]); var originalPath = planning || apply ? imagePath : PathFor("baseline");
        var bindingPath = PathFor("baseline-binding"); var locationPath = PathFor("compensation-definition");
        var settingsPath = planning ? PathFor("settings") : null; var planPath = planning ? null : PathFor("plan");
        var runnerPath = apply ? PathFor("runner") : null; var inputReceipt = planning || apply ? null : PathFor("report");
        var outputPath = PathFor("output"); var savedPlan = apply ? PathFor("saved-plan") : null; var outputReceipt = apply ? PathFor("report") : null;
        var input = await CaptureResearchExportAsync(command.Required("profile"), originalPath, imagePath, bindingPath, locationPath,
            planPath, runnerPath, inputReceipt, new[] { outputPath, savedPlan, outputReceipt }.OfType<string>().ToArray(),
            new[] { settingsPath }.OfType<string>().ToArray(), P28FuelMapExportReceipt.MaximumJsonBytes, cancellationToken).ConfigureAwait(false);
        P28FuelMapExportPlan plan;
        if (planning)
        {
            var settings = P28FuelMapExportSettings.Parse(input.Text(settingsPath!).TrimStart('\uFEFF'));
            plan = P28FuelMapExportEditor.Preview(input.Original, input.Profile, input.Binding, true, input.Location, settings).Plan;
            input.Recheck(); await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            plan = P28FuelMapExportPlan.Parse(input.Text(planPath!));
            if (apply)
            {
                var preview = P28FuelMapExportEditor.Reproduce(input.Original, input.Profile, input.Binding, true, input.Location, plan);
                var token = await P28FuelMapExportExecution.ValidateAsync(preview, runnerPath!, cancellationToken: cancellationToken).ConfigureAwait(false);
                input.Recheck();
                var verification = P28FuelMapExportWriter.Save(token, outputPath, savedPlan!, outputReceipt!, input.Paths, cancellationToken);
                if (!verification.IsValid) return VerificationFailed;
                await _output.WriteLineAsync($"Fresh fuel-map A/B/C: {token.Evidence.Runs.Sum(run => run.StrictMatches)} strict image/scratch calls; 9 full 512-invocation checksum sequences. BIN/plan/receipt readback passed.").ConfigureAwait(false);
                foreach (var witness in token.Evidence.Witnesses)
                    await _output.WriteLineAsync($"Witness {witness.MapId}: scratch {witness.ScratchPattern}, call {witness.Index}, raw load/rpm {witness.RawLoad}/{witness.RawRpm}, lookup {witness.OldLookup}->{witness.NewLookup}.").ConfigureAwait(false);
            }
            else
            {
                var child = RomImage.FromBytes(input.Snapshot[imagePath], imagePath);
                var receipt = P28FuelMapExportReceipt.Parse(input.Text(inputReceipt!));
                object result = operation == "inspect" ?
                    P28FuelMapExportWriter.InspectDerived(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt) :
                    P28FuelMapExportWriter.Verify(child, input.Original, input.Profile, input.Binding, input.Location, plan, receipt);
                input.Recheck(); await WriteJsonFileAsync(outputPath, result, cancellationToken).ConfigureAwait(false);
                await _output.WriteLineAsync("Full original-parent tuple verified; receipt consistency is historical, fresh execution NotRun.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("P28 fuel-map research edit: explicit unsigned numeric cells; no percentages, physical units or inferred tuning semantics.").ConfigureAwait(false);
        foreach (var map in plan.Maps)
        {
            await _output.WriteLineAsync($"{map.MapId}: requested={map.Requested}, cells={map.RequestedCellCount}, changed={map.ChangedCellCount}; full raw domain={map.DomainAudit.CheckedInputPairs}, changed results={map.DomainAudit.ChangedResults} (+{map.DomainAudit.IncreasedResults}/-{map.DomainAudit.DecreasedResults}/={map.DomainAudit.EqualResults}).").ConfigureAwait(false);
            foreach (var cell in map.Cells)
                await _output.WriteLineAsync($"  [{cell.Row},{cell.Column}] 0x{cell.Offset:X4}: raw {cell.OldRawValue}->{cell.NewRawValue}; readonly multiplier 0x{cell.MultiplierOffset:X4}={cell.Multiplier}; scaled {cell.OldScaledValue}->{cell.NewScaledValue}.").ConfigureAwait(false);
        }
        await _output.WriteLineAsync($"Residues A/B/C={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; changed bytes={plan.ExpectedDiff.Count}; compensation 0x{plan.Compensation.Offset:X4} {plan.Compensation.OldByte:X2}->{plan.Compensation.NewByte:X2}.").ConfigureAwait(false);
        foreach (var diff in plan.ExpectedDiff)
            await _output.WriteLineAsync($"0x{diff.Offset:X4}: 0x{diff.OldByte:X2} -> 0x{diff.NewByte:X2}").ConfigureAwait(false);
        await _output.WriteLineAsync($"{plan.Readiness}; physical units unavailable. GUI r3 paused/NotRun; D1 GUI NotRun; hardware/full boot NotRun. {(planning ? "Preview only; no firmware written and no native execution claimed." : string.Empty)}").ConfigureAwait(false);
        return Success;
    }
}
