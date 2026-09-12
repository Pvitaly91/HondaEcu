using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28IgnitionMapExportAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0 || args[0] is not ("plan" or "apply" or "verify" or "inspect"))
            throw new CliUsageException("Usage: research p28-ignition export <plan|apply|verify|inspect> <image> --profile p28-304 ...");
        var operation = args[0]; var planning = operation == "plan"; var apply = operation == "apply";
        var command = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal)
            { "confirm-profile", "confirm-pc-only" });
        command.EnsureOnly(planning
            ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "settings", "output"]
            : apply
                ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "plan", "runner",
                    "confirm-pc-only", "output", "saved-plan", "report"]
                : ["baseline", "profile", "baseline-binding", "compensation-definition", "plan", "report", "output"]);
        command.RequirePositionals(1, "research p28-ignition export <operation> <image>");
        if ((planning || apply) && !command.HasFlag("confirm-profile"))
            throw new CliUsageException("--confirm-profile is required with the exact original binding.");
        if (apply && !command.HasFlag("confirm-pc-only"))
            throw new CliUsageException("Ignition-map export requires --confirm-pc-only; this never grants hardware authorization.");
        string PathFor(string name) => ResolvePath(command.Required(name));
        var imagePath = ResolvePath(command.Positionals[0]);
        var originalPath = planning || apply ? imagePath : PathFor("baseline");
        var bindingPath = PathFor("baseline-binding"); var locationPath = PathFor("compensation-definition");
        var settingsPath = planning ? PathFor("settings") : null; var planPath = planning ? null : PathFor("plan");
        var runnerPath = apply ? PathFor("runner") : null; var inputReceipt = planning || apply ? null : PathFor("report");
        var outputPath = PathFor("output"); var savedPlan = apply ? PathFor("saved-plan") : null;
        var outputReceipt = apply ? PathFor("report") : null;
        var input = await CaptureResearchExportAsync(command.Required("profile"), originalPath, imagePath,
            bindingPath, locationPath, planPath, runnerPath, inputReceipt,
            new[] { outputPath, savedPlan, outputReceipt }.OfType<string>().ToArray(),
            new[] { settingsPath }.OfType<string>().ToArray(), P28IgnitionMapExportReceipt.MaximumJsonBytes,
            cancellationToken).ConfigureAwait(false);
        P28IgnitionMapExportPlan plan;
        if (planning)
        {
            var settings = P28IgnitionMapExportSettings.Parse(input.Text(settingsPath!).TrimStart('\uFEFF'));
            plan = P28IgnitionMapExportEditor.Preview(input.Original, input.Profile, input.Binding, true,
                input.Location, settings).Plan;
            input.Recheck(); await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            plan = P28IgnitionMapExportPlan.Parse(input.Text(planPath!));
            if (apply)
            {
                var preview = P28IgnitionMapExportEditor.Reproduce(input.Original, input.Profile, input.Binding,
                    true, input.Location, plan);
                var verified = await P28IgnitionMapExportExecution.ValidateAsync(preview, runnerPath!,
                    cancellationToken: cancellationToken).ConfigureAwait(false);
                input.Recheck();
                var verification = P28IgnitionMapExportWriter.Save(verified, outputPath, savedPlan!,
                    outputReceipt!, input.Paths, cancellationToken);
                if (!verification.IsValid) return VerificationFailed;
                await _output.WriteLineAsync($"Ignition native A/B/C: factor0 runs={verified.Evidence.MainRuns.Count}, once-seeded factor runs={verified.Evidence.FactorRuns.Count}; checksum A/B/C complete.").ConfigureAwait(false);
                foreach (var witness in verified.Evidence.Witnesses)
                    await _output.WriteLineAsync($"witness {witness.MapId}: raw load/rpm={witness.RawLoad}/{witness.RawRpm}; lookup {witness.OldLookup}->{witness.NewLookup}").ConfigureAwait(false);
            }
            else
            {
                var receipt = P28IgnitionMapExportReceipt.Parse(input.Text(inputReceipt!));
                var child = RomImage.FromBytes(input.Snapshot[imagePath], imagePath);
                object result = operation == "inspect"
                    ? P28IgnitionMapExportWriter.InspectDerived(child, input.Original, input.Profile, input.Binding,
                        input.Location, plan, receipt)
                    : P28IgnitionMapExportWriter.Verify(child, input.Original, input.Profile, input.Binding,
                        input.Location, plan, receipt);
                input.Recheck(); await WriteJsonFileAsync(outputPath, result, cancellationToken).ConfigureAwait(false);
                await _output.WriteLineAsync("Verification/inspection is historical receipt consistency only; fresh native execution NotRun.").ConfigureAwait(false);
            }
        }
        foreach (var map in plan.Maps)
            await _output.WriteLineAsync($"{map.MapId}: requested={map.RequestedCellCount}, changed={map.ChangedCellCount}, exhaustive pairs={map.DomainAudit.CheckedInputPairs}, result changes={map.DomainAudit.ChangedResults}").ConfigureAwait(false);
        await _output.WriteLineAsync($"consumer exhaustive pairs={plan.ConsumerAudit.CheckedInputPairs}; residue A/B/C={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; diff bytes={plan.ExpectedDiff.Count}").ConfigureAwait(false);
        await _output.WriteLineAsync($"{plan.Readiness}; raw unsigned cells only; physical RPM/degrees unavailable; GUI r3 paused/NotRun; D1 GUI NotRun; hardware/full boot NotRun.{(planning ? " No BIN written." : string.Empty)}").ConfigureAwait(false);
        return Success;
    }
}
