using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28CompensationCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "compensation-definition", "output");
        command.RequirePositionals(1,
            "hondaecu research p28-vtec compensation-check <original> --profile p28-304 --confirm-profile --baseline-binding <private-json> [--compensation-definition <reviewed-signed-private-json>] --output <new-private-json>");
        RequireChecksumProfileConfirmation(command);
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var definitionPath = ChecksumDefinitionPath(command);
        var outputPath = ResolvePath(command.Required("output"));
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        ProtectNewResearchDestination(outputPath, baselinePath, bindingPath, definitionPath, profile.SourcePath);
        var availability = await Task.Run(() => P28ChecksumPreservingEditor.GetAvailability(
            RomImage.Load(baselinePath), profile, P28ExactBaselineBinding.Load(bindingPath), true,
            definitionPath is null ? null : P28ChecksumPreservingEditor.LoadLocation(definitionPath)), cancellationToken).ConfigureAwait(false);
        await WriteJsonFileAsync(outputPath, availability, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"CompensationLocation: {availability.Status}; available={availability.IsAvailable}.").ConfigureAwait(false);
        await _output.WriteLineAsync(availability.Reason).ConfigureAwait(false);
        await _output.WriteLineAsync(availability.EvidenceScope).ConfigureAwait(false);
        await WriteChecksumExportWarningsAsync().ConfigureAwait(false);
        return availability.IsAvailable ? Success : VerificationFailed;
    }

    private async Task<int> P28ChecksumExportPlanAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "compensation-definition", "slot", "raw-value",
            "derived", "plan", "patch-report", "output");
        command.RequirePositionals(1,
            "hondaecu research p28-vtec checksum-export-plan <original> --profile p28-304 --confirm-profile --baseline-binding <private-json> --compensation-definition <reviewed-signed-private-json> --output <new-plan> (--slot <slot-id> --raw-value <0..255> OR --derived <M1c-child> --plan <M1c-plan> --patch-report <M1c-report>)");
        RequireChecksumProfileConfirmation(command);
        var slot = command.Optional("slot");
        var rawText = command.Optional("raw-value");
        var childOption = command.Optional("derived");
        var legacyPlanOption = command.Optional("plan");
        var legacyReportOption = command.Optional("patch-report");
        var lineageCount = new[] { childOption, legacyPlanOption, legacyReportOption }.Count(value => value is not null);
        if (lineageCount is not (0 or 3))
            throw new CliUsageException("Existing M1c lineage requires --derived, --plan and --patch-report together; the positional BIN remains its original parent.");
        if (lineageCount == 3 && (slot is not null || rawText is not null))
            throw new CliUsageException("Choose the existing M1c threshold operation or --slot/--raw-value, not both.");
        if (lineageCount == 0 && (slot is null || rawText is null))
            throw new CliUsageException("A new threshold operation requires both --slot and --raw-value.");
        var raw = rawText is null ? 0 : ParseStrictRawByte(rawText);
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var definitionPath = ChecksumDefinitionPath(command);
        var childPath = childOption is null ? null : ResolvePath(childOption);
        var legacyPlanPath = legacyPlanOption is null ? null : ResolvePath(legacyPlanOption);
        var legacyReportPath = legacyReportOption is null ? null : ResolvePath(legacyReportOption);
        var outputPath = ResolvePath(command.Required("output"));
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(command.Required("profile"));
        ProtectNewResearchDestination(outputPath, baselinePath, bindingPath, definitionPath, childPath,
            legacyPlanPath, legacyReportPath, profile.SourcePath);
        var plan = await Task.Run(() =>
        {
            var baseline = RomImage.Load(baselinePath);
            var binding = P28ExactBaselineBinding.Load(bindingPath);
            if (lineageCount == 3)
            {
                var legacyPlan = P28RawThresholdPlan.Load(legacyPlanPath!);
                P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true,
                    RomImage.Load(childPath!), legacyPlan, P28RawThresholdPatchReport.Load(legacyReportPath!));
                slot = legacyPlan.SlotId;
                raw = legacyPlan.NewByte;
            }
            var location = definitionPath is null ? null : P28ChecksumPreservingEditor.LoadLocation(definitionPath);
            return P28ChecksumPreservingEditor.CreatePlan(baseline, profile, binding, true, slot!, raw, location);
        }, cancellationToken).ConfigureAwait(false);
        await WriteJsonFileAsync(outputPath, plan, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync("Private composed research plan written; no ROM saved and native execution has not run.").ConfigureAwait(false);
        await WriteChecksumCompositionSummaryAsync(plan).ConfigureAwait(false);
        return Success;
    }

    private async Task<int> P28ChecksumExportApplyAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-pc-only", "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "confirm-pc-only", "baseline-binding", "compensation-definition",
            "plan", "runner", "output", "saved-plan", "report");
        command.RequirePositionals(1,
            "hondaecu research p28-vtec checksum-export-apply <original> --baseline-binding <private-json> --compensation-definition <reviewed-signed-private-json> --plan <reviewed-composed-plan> --runner <rust-executable> --confirm-pc-only --output <new-BIN> --saved-plan <new-plan-copy> --report <new-export-report>");
        if (!command.HasFlag("confirm-pc-only"))
            throw new CliUsageException("Checksum-preserving publication requires explicit --confirm-pc-only after reviewing both changes.");
        _ = command.HasFlag("confirm-profile");
        var runnerPath = ResolvePath(command.Required("runner"));
        if (!File.Exists(runnerPath))
            throw new InvalidDataException("A local runner is required for strict complete native validation; no verified export was written.");
        var baselinePath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var planPath = ResolvePath(command.Required("plan"));
        var definitionPath = ChecksumDefinitionPath(command);
        var outputPath = ResolvePath(command.Required("output"));
        var savedPlanPath = ResolvePath(command.Required("saved-plan"));
        var reportPath = ResolvePath(command.Required("report"));
        var inputs = await LoadChecksumCompositionInputsAsync(baselinePath, bindingPath, planPath, definitionPath,
            command.Optional("profile"), cancellationToken).ConfigureAwait(false);
        var protectedPaths = inputs.FileSnapshot.Keys.Append(runnerPath).ToArray();
        ProtectNewResearchDestination(outputPath, [.. protectedPaths, savedPlanPath, reportPath]);
        ProtectNewResearchDestination(savedPlanPath, [.. protectedPaths, outputPath, reportPath]);
        ProtectNewResearchDestination(reportPath, [.. protectedPaths, outputPath, savedPlanPath]);
        var composition = await Task.Run(() =>
        {
            var location = inputs.Location ?? throw new InvalidDataException("A reviewed signed CompensationLocation is required for publication.");
            var preview = P28ChecksumPreservingEditor.Apply(inputs.Baseline, inputs.Profile, inputs.Binding, inputs.Plan, inputs.Location);
            return P28ChecksumPreservingEditor.Admit(preview.Image, inputs.Baseline, inputs.Profile, inputs.Binding,
                inputs.Plan, preview.Report, location);
        }, cancellationToken).ConfigureAwait(false);
        await WriteChecksumCompositionSummaryAsync(inputs.Plan).ConfigureAwait(false);
        var validated = await P28ChecksumPreservingExecution.ValidateForExportAsync(composition, runnerPath,
            cancellationToken: cancellationToken).ConfigureAwait(false);
        var verification = await Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            RequireChecksumInputSnapshot(inputs.FileSnapshot);
            return P28ChecksumPreservingCopyWriter.Save(validated, outputPath, savedPlanPath, reportPath,
                protectedPaths, cancellationToken);
        }, cancellationToken).ConfigureAwait(false);
        if (!verification.IsValid)
            throw new InvalidDataException("The newly published composition failed independent readback verification; it is not a verified export.");
        await _output.WriteLineAsync("New PC-only BIN, composed-plan copy and export report published and independently re-read.").ConfigureAwait(false);
        await _output.WriteLineAsync("Strict native checksum completed with actual zero residue and normal pass path; no assumptions or bypass.").ConfigureAwait(false);
        await _output.WriteLineAsync("This result is not full ECU boot, physical hardware validation, or permission to flash.").ConfigureAwait(false);
        await WriteChecksumExportWarningsAsync().ConfigureAwait(false);
        return Success;
    }

    private Task<int> P28ChecksumExportVerifyAsync(string[] args, CancellationToken cancellationToken) =>
        P28ChecksumCompositionReadAsync(args, inspect: false, cancellationToken);

    private Task<int> P28ChecksumExportInspectAsync(string[] args, CancellationToken cancellationToken) =>
        P28ChecksumCompositionReadAsync(args, inspect: true, cancellationToken);

    private async Task<int> P28ChecksumCompositionReadAsync(string[] args, bool inspect, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("baseline", "baseline-binding", "compensation-definition", "plan", "report", "output", "profile");
        command.RequirePositionals(1,
            $"hondaecu research p28-vtec checksum-export-{(inspect ? "inspect" : "verify")} <output-BIN> --baseline <original> --baseline-binding <private-json> --compensation-definition <reviewed-signed-private-json> --plan <composed-plan> --report <export-report> [--output <new-private-report>]");
        var imagePath = ResolvePath(command.Positionals[0]);
        var baselinePath = ResolvePath(command.Required("baseline"));
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var planPath = ResolvePath(command.Required("plan"));
        var reportPath = ResolvePath(command.Required("report"));
        var definitionPath = ChecksumDefinitionPath(command);
        var resultOption = inspect ? command.Required("output") : command.Optional("output");
        var resultPath = resultOption is null ? null : ResolvePath(resultOption);
        var inputs = await LoadChecksumCompositionInputsAsync(baselinePath, bindingPath, planPath, definitionPath,
            command.Optional("profile"), cancellationToken).ConfigureAwait(false);
        if (resultPath is not null)
            ProtectNewResearchDestination(resultPath, [.. inputs.FileSnapshot.Keys, imagePath, reportPath]);
        var readbackSnapshot = await Task.Run(() => new[] { imagePath, reportPath }.Distinct(StringComparer.OrdinalIgnoreCase)
            .ToDictionary(path => path, File.ReadAllBytes, StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var receipt = await Task.Run(() => P28ChecksumPreservingExportReport.Load(reportPath), cancellationToken).ConfigureAwait(false);
        var report = receipt.CompositionReport;
        var image = await Task.Run(() => RomImage.Load(imagePath), cancellationToken).ConfigureAwait(false);
        var verification = await Task.Run(() => P28ChecksumPreservingEditor.Verify(image, inputs.Baseline, inputs.Profile,
            inputs.Binding, inputs.Plan, report, inputs.Location), cancellationToken).ConfigureAwait(false);
        object? inspection = null;
        if (inspect && verification.IsValid)
        {
            inspection = await Task.Run(() => P28ChecksumPreservingEditor.InspectDerived(
                P28ChecksumPreservingEditor.Admit(image, inputs.Baseline, inputs.Profile, inputs.Binding,
                    inputs.Plan, report, inputs.Location ?? throw new InvalidDataException("A reviewed signed CompensationLocation is required for derived interpretation."))), cancellationToken).ConfigureAwait(false);
        }
        RequireChecksumInputSnapshot(inputs.FileSnapshot);
        RequireChecksumInputSnapshot(readbackSnapshot);
        var result = new
        {
            Verification = verification,
            Inspection = inspection,
            HistoricalExportReceipt = receipt,
            CurrentExecutionStatus = NativeChecksumExecutionStatus.NotRun,
            ExecutionQualification = "Saved observations are historical; this command verifies original-parent composition without creating execution or publication authority.",
            FlashReadiness = FlashReadinessStatus.PcInspectionOnly,
            FlashSafety = FlashSafetyStatus.NotFlashReady,
        };
        if (resultPath is not null)
            await WriteJsonFileAsync(resultPath, result, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync($"Original-parent checksum composition lineage: {(verification.IsValid ? "verified" : "rejected")}.").ConfigureAwait(false);
        if (inspect)
            await _output.WriteLineAsync($"Derived threshold contexts: {(verification.IsValid ? "admitted through shared composition verification" : "not applied")}.").ConfigureAwait(false);
        await _output.WriteLineAsync("This readback verifies bytes, arithmetic and lineage; it is not a new native execution.").ConfigureAwait(false);
        await WriteChecksumExportWarningsAsync().ConfigureAwait(false);
        if (!verification.IsValid)
        {
            foreach (var issue in verification.Issues)
                await _error.WriteLineAsync($"  [{issue.Code}] composition verification failed.").ConfigureAwait(false);
            return VerificationFailed;
        }
        return Success;
    }

    private async Task<ChecksumCompositionInputs> LoadChecksumCompositionInputsAsync(string baselinePath,
        string bindingPath, string planPath, string? definitionPath, string? requestedProfile, CancellationToken cancellationToken)
    {
        var plan = await Task.Run(() => P28ChecksumPreservingPlan.Load(planPath), cancellationToken).ConfigureAwait(false);
        if (requestedProfile is not null && !string.Equals(requestedProfile, plan.ThresholdPlan.ProfileId, StringComparison.Ordinal))
            throw new CliUsageException("Option '--profile' must match the original profile recorded in the composed plan.");
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(plan.ThresholdPlan.ProfileId);
        return await Task.Run(() =>
        {
            var paths = new[] { baselinePath, bindingPath, planPath, definitionPath, profile.SourcePath }
                .OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase);
            var snapshot = paths.ToDictionary(path => path, File.ReadAllBytes, StringComparer.OrdinalIgnoreCase);
            var baseline = RomImage.Load(baselinePath);
            var binding = P28ExactBaselineBinding.Load(bindingPath);
            var location = definitionPath is null ? null : P28ChecksumPreservingEditor.LoadLocation(definitionPath);
            if (P28ChecksumPreservingPlan.Load(planPath).ToJson(false) != plan.ToJson(false) ||
                profile.SourcePath is { } path && P28VtecInspector.ComputeProfileDigest(RomProfile.Load(path)) != P28VtecInspector.ComputeProfileDigest(profile))
                throw new InvalidDataException("The reviewed composed plan or profile changed while loading; no export is admitted.");
            RequireChecksumInputSnapshot(snapshot);
            return new ChecksumCompositionInputs(baseline, profile, binding, plan, location, snapshot);
        }, cancellationToken).ConfigureAwait(false);
    }

    private static void RequireChecksumInputSnapshot(IReadOnlyDictionary<string, byte[]> snapshot)
    {
        foreach (var entry in snapshot)
            if (!File.ReadAllBytes(entry.Key).AsSpan().SequenceEqual(entry.Value))
                throw new InvalidDataException("An original input, profile, binding, reviewed plan or compensation definition changed during the operation; no export is admitted.");
    }

    private sealed record ChecksumCompositionInputs(RomImage Baseline, RomProfile Profile,
        P28ExactBaselineBinding Binding, P28ChecksumPreservingPlan Plan, VerifiedCompensationLocation? Location,
        IReadOnlyDictionary<string, byte[]> FileSnapshot);

    private static void RequireChecksumProfileConfirmation(CommandLine command)
    {
        if (!command.HasFlag("confirm-profile"))
            throw new CliUsageException("Checksum-preserving research requires --confirm-profile and the exact original parent binding.");
    }

    private string? ChecksumDefinitionPath(CommandLine command)
    {
        var option = command.Optional("compensation-definition");
        return option is null ? null : ResolvePath(option);
    }

    private async Task WriteChecksumCompositionSummaryAsync(P28ChecksumPreservingPlan plan)
    {
        await _output.WriteLineAsync($"Requested threshold: {plan.ThresholdPlan.SlotId}, 0x{plan.ThresholdPlan.Offset:X4}: " +
            $"{plan.ThresholdPlan.ExpectedOldByte} -> {plan.ThresholdPlan.NewByte}.").ConfigureAwait(false);
        await _output.WriteLineAsync($"Computed compensation: 0x{plan.Compensation.Offset:X4}: " +
            $"{plan.Compensation.OldByte} -> {plan.Compensation.NewByte}; definition {plan.CompensationDefinitionId}.").ConfigureAwait(false);
        await _output.WriteLineAsync($"Full diff: {plan.ExpectedDiff.Count} changed offsets; no-op={plan.IsNoOp}. " +
            $"Residues baseline/intermediate/final: {plan.BaselineResidue}/{plan.IntermediateResidue}/{plan.FinalResidue}.").ConfigureAwait(false);
        await _output.WriteLineAsync($"Plan execution: {plan.ExecutionStatus}. {plan.EvidenceScope}").ConfigureAwait(false);
        await WriteChecksumExportWarningsAsync().ConfigureAwait(false);
    }

    private async Task WriteChecksumExportWarningsAsync()
    {
        await _output.WriteLineAsync("Scoped CompensationLocation, not FactoryChecksumStorage. Zero residue is not behavior equivalence or ECU safety.").ConfigureAwait(false);
        await _output.WriteLineAsync("No checksum bypass, gate change, arbitrary-offset repair or ADD permission. PcInspectionOnly / NotFlashReady.").ConfigureAwait(false);
    }
}
