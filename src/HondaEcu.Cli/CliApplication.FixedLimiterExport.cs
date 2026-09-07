using System.Globalization;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28FixedLimiterExportAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0 || args[0] is not ("plan" or "apply" or "verify" or "inspect"))
            throw new CliUsageException("Usage: research p28-limiter export <plan|apply|verify|inspect> <image> --profile p28-304 ...");
        var operation = args[0]; var apply = operation == "apply"; var planOnly = operation == "plan";
        var c = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile", "confirm-pc-only" });
        c.EnsureOnly(planOnly ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "cut-raw", "resume-raw", "output"] :
            apply ? ["profile", "confirm-profile", "baseline-binding", "compensation-definition", "plan", "runner", "confirm-pc-only", "output", "saved-plan", "report"] :
            ["baseline", "profile", "baseline-binding", "compensation-definition", "plan", "report", "output"]);
        c.RequirePositionals(1, "research p28-limiter export <operation> <image>");
        if ((apply || planOnly) && !c.HasFlag("confirm-profile")) throw new CliUsageException("--confirm-profile is required with exact original binding.");
        if (apply && !c.HasFlag("confirm-pc-only")) throw new CliUsageException("Export requires --confirm-pc-only; never hardware authorization.");
        P28FixedLimiterPair? requestedPair = null;
        if (planOnly)
        {
            int Raw(string name)
            {
                var value = c.Required(name);
                if (value.Length == 0 || !value.All(char.IsAsciiDigit) || !int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var raw))
                    throw new CliUsageException($"--{name} accepts an integer raw value only; no RPM, rounding or clamp.");
                return raw;
            }
            requestedPair = new(Raw("cut-raw"), Raw("resume-raw"));
        }
        var imagePath = ResolvePath(c.Positionals[0]);
        var originalPath = apply || planOnly ? imagePath : ResolvePath(c.Required("baseline"));
        var bindingPath = ResolvePath(c.Required("baseline-binding")); var locationPath = ResolvePath(c.Required("compensation-definition"));
        var planPath = planOnly ? null : ResolvePath(c.Required("plan"));
        var runnerPath = apply ? ResolvePath(c.Required("runner")) : null;
        var inputReceipt = apply || planOnly ? null : ResolvePath(c.Required("report"));
        var outputPath = ResolvePath(c.Required("output"));
        var savedPlanPath = apply ? ResolvePath(c.Required("saved-plan")) : null;
        var receiptPath = apply ? ResolvePath(c.Required("report")) : null;
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(c.Required("profile"));
        var inputs = new[] { originalPath, imagePath, bindingPath, locationPath, planPath, runnerPath, inputReceipt, profile.SourcePath }.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        var destinations = new[] { outputPath, savedPlanPath, receiptPath }.OfType<string>().ToArray();
        foreach (var destination in destinations) ProtectNewResearchDestination(destination, inputs);
        for (var i = 0; i < destinations.Length; i++)
            foreach (var other in destinations.Skip(i + 1)) AtomicFile.EnsureDifferentPath(destinations[i], other);
        var snapshot = await Task.Run(() => inputs.ToDictionary(p => p, p => ReadBoundedCaptureInput(p, p == inputReceipt ? 8 * 1024 * 1024 : p == runnerPath ? 64 * 1024 * 1024 : 1024 * 1024), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } pp && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[pp]))))
            throw new InvalidDataException("Profile changed while loading export inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Load(bindingPath);
        var location = P28ChecksumPreservingEditor.ParseLocation(utf8.GetString(snapshot[locationPath]).TrimStart('\uFEFF'));
        RequireCaptureInputSnapshot(snapshot);
        P28FixedLimiterPlan plan;
        if (planOnly)
        {
            plan = P28FixedLimiterEditor.Preview(original, profile, binding, true, location, requestedPair!).Plan;
            RequireCaptureInputSnapshot(snapshot);
            await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        }
        else
        {
            plan = P28FixedLimiterPlan.Parse(utf8.GetString(snapshot[planPath!]));
            if (apply)
            {
                var preview = P28FixedLimiterEditor.Reproduce(original, profile, binding, true, location, plan);
                var token = await P28FixedLimiterExecution.ValidateAsync(preview, runnerPath!, cancellationToken: cancellationToken).ConfigureAwait(false);
                RequireCaptureInputSnapshot(snapshot);
                var verification = P28FixedLimiterWriter.Save(token, outputPath, savedPlanPath!, receiptPath!, inputs, cancellationToken);
                if (!verification.IsValid) return VerificationFailed;
                await _output.WriteLineAsync($"Fresh native A/B/C validation passed; limiter={token.Evidence.LimiterRuns.Sum(r => r.StrictMatches)}, adaptive={token.Evidence.AdaptiveRuns.Sum(r => r.StrictMatches)} strict calls; checksum=9 strict 512-invocation sequences. BIN/plan/receipt independently read back.").ConfigureAwait(false);
            }
            else
            {
                var output = RomImage.FromBytes(snapshot[imagePath], imagePath);
                var receipt = P28FixedLimiterReceipt.Parse(utf8.GetString(snapshot[inputReceipt!]));
                object result = operation == "inspect" ? P28FixedLimiterWriter.InspectDerived(output, original, profile, binding, location, plan, receipt) :
                    P28FixedLimiterWriter.Verify(output, original, profile, binding, location, plan, receipt);
                RequireCaptureInputSnapshot(snapshot);
                await WriteJsonFileAsync(outputPath, result, cancellationToken).ConfigureAwait(false);
                await _output.WriteLineAsync("Full bytes and original-parent lineage verified. Receipt is historical evidence; fresh execution NotRun.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync($"{P28FixedLimiterEditor.Scope}. cut {plan.Operands[0].OriginalWord}->{plan.RequestedPair.CutRaw}; resume {plan.Operands[1].OriginalWord}->{plan.RequestedPair.ResumeRaw}. Arithmetic residues A/B/C={plan.ResidueA}/{plan.ResidueB}/{plan.ResidueC}; changed bytes={plan.ExpectedDiff.Count}.").ConfigureAwait(false);
        foreach (var d in plan.ExpectedDiff) await _output.WriteLineAsync($"0x{d.Offset:X4}: 0x{d.OldByte:X2} -> 0x{d.NewByte:X2}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Compensation {(plan.Compensation.OldByte == plan.Compensation.NewByte ? "unchanged (zero intermediate residue)" : "applied from actual byte sum")}. {P28FixedLimiterEditor.Readiness}; physicalRpmAvailable=false. GUI r3 paused/NotRun; hardware/full boot NotRun. {(planOnly ? "Preview only; no firmware written or native execution claimed." : "")}").ConfigureAwait(false);
        return Success;
    }
}
