using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28RawThresholdEditingCliTests
{
    [Fact]
    public async Task PlanAcceptsDecimalEndpointsAndRejectsInvalidValuesDuplicateOptionsAndWrongBinding()
    {
        using var workspace = new EditingWorkspace();
        var baseline = workspace.CreateRom("baseline.dat");
        var binding = workspace.CreateBinding("binding.json", baseline);
        var originalBaseline = File.ReadAllBytes(baseline);
        var originalBinding = File.ReadAllBytes(binding);
        var slot = P28ThresholdLogic.GetSlotId(0, 0, false);

        var invalidValues = new[] { "", "-1", "+1", "256", "1.0", "0x10", "one", " 1", "1 " };
        for (var index = 0; index < invalidValues.Length; index++)
        {
            var output = workspace.PathOf($"invalid-{index}.json");
            var result = await workspace.RunAsync(
                "research", "p28-vtec", "plan", baseline,
                "--profile", P28ExactBaselineBinding.RequiredProfileId,
                "--confirm-profile",
                "--baseline-binding", binding,
                "--slot", slot,
                "--raw-value", invalidValues[index],
                "--output", output);

            Assert.Equal(CliApplication.UsageError, result.ExitCode);
            Assert.False(File.Exists(output));
        }

        foreach (var endpoint in new[] { "0", "255" })
        {
            var output = workspace.PathOf($"endpoint-{endpoint}.json");
            var result = await workspace.RunAsync(
                "research", "p28-vtec", "plan", baseline,
                "--profile", P28ExactBaselineBinding.RequiredProfileId,
                "--confirm-profile",
                "--baseline-binding", binding,
                "--slot", slot,
                "--raw-value", endpoint,
                "--output", output);

            Assert.Equal(CliApplication.Success, result.ExitCode);
            Assert.True(File.Exists(output));
        }

        var duplicateOutput = workspace.PathOf("duplicate.json");
        var duplicate = await workspace.RunAsync(
            "research", "p28-vtec", "plan", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--slot", slot,
            "--raw-value", "1",
            "--raw-value", "2",
            "--output", duplicateOutput);
        Assert.Equal(CliApplication.UsageError, duplicate.ExitCode);
        Assert.False(File.Exists(duplicateOutput));

        var noConfirmationOutput = workspace.PathOf("no-confirmation.json");
        var noConfirmation = await workspace.RunAsync(
            "research", "p28-vtec", "plan", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", binding,
            "--slot", slot,
            "--raw-value", "1",
            "--output", noConfirmationOutput);
        Assert.Equal(CliApplication.UsageError, noConfirmation.ExitCode);
        Assert.False(File.Exists(noConfirmationOutput));

        var other = workspace.CreateRom("other.dat", bytes => bytes[0] ^= 0xFF);
        var wrongBinding = workspace.CreateBinding("wrong-binding.json", other);
        var wrongBindingOutput = workspace.PathOf("wrong-binding-plan.json");
        var wrongBindingResult = await workspace.RunAsync(
            "research", "p28-vtec", "plan", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", wrongBinding,
            "--slot", slot,
            "--raw-value", "1",
            "--output", wrongBindingOutput);
        Assert.Equal(CliApplication.OperationError, wrongBindingResult.ExitCode);
        Assert.False(File.Exists(wrongBindingOutput));

        var forbiddenOutput = workspace.PathOf("forbidden-rpm-plan.json");
        var forbidden = await workspace.RunAsync(
            "research", "p28-vtec", "plan", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--slot", slot,
            "--raw-value", "1",
            "--rpm", "5000",
            "--output", forbiddenOutput);
        Assert.Equal(CliApplication.UsageError, forbidden.ExitCode);
        Assert.False(File.Exists(forbiddenOutput));

        var incompleteLineageOutput = workspace.PathOf("incomplete-lineage.json");
        var incompleteLineage = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--baseline", baseline,
            "--output", incompleteLineageOutput);
        Assert.Equal(CliApplication.UsageError, incompleteLineage.ExitCode);
        Assert.False(File.Exists(incompleteLineageOutput));

        var missingPcOutput = workspace.PathOf("missing-pc-confirmation.dat");
        var missingPcReport = workspace.PathOf("missing-pc-confirmation.json");
        var missingPcConfirmation = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", workspace.PathOf("endpoint-0.json"),
            "--output", missingPcOutput,
            "--report", missingPcReport);
        Assert.Equal(CliApplication.UsageError, missingPcConfirmation.ExitCode);
        Assert.False(File.Exists(missingPcOutput));
        Assert.False(File.Exists(missingPcReport));

        var duplicatePcOutput = workspace.PathOf("duplicate-pc-confirmation.dat");
        var duplicatePcReport = workspace.PathOf("duplicate-pc-confirmation.json");
        var duplicatePcConfirmation = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", workspace.PathOf("endpoint-0.json"),
            "--confirm-pc-only",
            "--confirm-pc-only",
            "--output", duplicatePcOutput,
            "--report", duplicatePcReport);
        Assert.Equal(CliApplication.UsageError, duplicatePcConfirmation.ExitCode);
        Assert.False(File.Exists(duplicatePcOutput));
        Assert.False(File.Exists(duplicatePcReport));

        var duplicateProfileOutput = workspace.PathOf("duplicate-profile-confirmation.dat");
        var duplicateProfileReport = workspace.PathOf("duplicate-profile-confirmation.json");
        var duplicateProfileConfirmation = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", workspace.PathOf("endpoint-0.json"),
            "--confirm-pc-only",
            "--confirm-profile",
            "--confirm-profile",
            "--output", duplicateProfileOutput,
            "--report", duplicateProfileReport);
        Assert.Equal(CliApplication.UsageError, duplicateProfileConfirmation.ExitCode);
        Assert.False(File.Exists(duplicateProfileOutput));
        Assert.False(File.Exists(duplicateProfileReport));

        Assert.Equal(originalBaseline, File.ReadAllBytes(baseline));
        Assert.Equal(originalBinding, File.ReadAllBytes(binding));
    }

    [Fact]
    public async Task PlanApplyVerifyAndDerivedInspectFormDeterministicOneByteRoundTrip()
    {
        using var workspace = new EditingWorkspace();
        var baseline = workspace.CreateRom("baseline.dat");
        var binding = workspace.CreateBinding("binding.json", baseline);
        var originalBaseline = File.ReadAllBytes(baseline);
        var originalBinding = File.ReadAllBytes(binding);
        var slot = P28ThresholdLogic.GetSlotId(0, 0, false);
        var planOnePath = workspace.PathOf("plan-one.json");
        var planTwoPath = workspace.PathOf("plan-two.json");

        var planOne = await workspace.RunAsync(
            "research", "p28-vtec", "plan", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--slot", slot,
            "--raw-value", "173",
            "--output", planOnePath);
        var planTwo = await workspace.RunAsync(
            "research", "p28-vtec", "plan", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--slot", slot,
            "--raw-value", "173",
            "--output", planTwoPath);

        Assert.Equal(CliApplication.Success, planOne.ExitCode);
        Assert.Equal(CliApplication.Success, planTwo.ExitCode);
        Assert.Equal(File.ReadAllText(planOnePath), File.ReadAllText(planTwoPath));
        var plan = P28RawThresholdPlan.Load(planOnePath);
        Assert.Equal(P28ThresholdLogic.ThresholdOffset(0, 0, false), plan.Offset);
        Assert.Equal(173, plan.NewByte);
        Assert.False(plan.IsNoOp);
        Assert.Equal(new[] { plan.Offset }, plan.ExpectedChangedOffsets);
        Assert.Equal(256, plan.PredicateImpact.ComparedCodeCount);

        var outputOnePath = workspace.PathOf("output-one.dat");
        var outputTwoPath = workspace.PathOf("output-two.dat");
        var reportOnePath = workspace.PathOf("report-one.json");
        var reportTwoPath = workspace.PathOf("report-two.json");
        var applyOne = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", planOnePath,
            "--confirm-pc-only",
            "--output", outputOnePath,
            "--report", reportOnePath);
        var applyTwo = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--plan", planTwoPath,
            "--confirm-pc-only",
            "--output", outputTwoPath,
            "--report", reportTwoPath);

        Assert.Equal(CliApplication.Success, applyOne.ExitCode);
        Assert.Equal(CliApplication.Success, applyTwo.ExitCode);
        Assert.Equal(File.ReadAllBytes(outputOnePath), File.ReadAllBytes(outputTwoPath));
        Assert.Equal(File.ReadAllText(reportOnePath), File.ReadAllText(reportTwoPath));
        var output = File.ReadAllBytes(outputOnePath);
        var changed = Enumerable.Range(0, output.Length)
            .Where(offset => output[offset] != originalBaseline[offset])
            .ToArray();
        Assert.Equal(new[] { plan.Offset }, changed);
        Assert.Equal(173, output[plan.Offset]);
        var report = P28RawThresholdPatchReport.Load(reportOnePath);
        Assert.Equal(1, report.ChangedByteCount);
        Assert.True(report.ReverseRestoresBaseline);
        Assert.Equal(ChecksumStatus.Unknown, report.ChecksumStatus);
        Assert.Equal(FlashSafetyStatus.NotFlashReady, report.FlashSafety);

        var verificationOnePath = workspace.PathOf("verification-one.json");
        var verificationTwoPath = workspace.PathOf("verification-two.json");
        var verifyOne = await workspace.RunAsync(
            "research", "p28-vtec", "verify", outputOnePath,
            "--baseline", baseline,
            "--baseline-binding", binding,
            "--plan", planOnePath,
            "--report", reportOnePath,
            "--output", verificationOnePath);
        var verifyTwo = await workspace.RunAsync(
            "research", "p28-vtec", "verify", outputTwoPath,
            "--baseline", baseline,
            "--baseline-binding", binding,
            "--plan", planTwoPath,
            "--report", reportTwoPath,
            "--output", verificationTwoPath);
        Assert.Equal(CliApplication.Success, verifyOne.ExitCode);
        Assert.Equal(CliApplication.Success, verifyTwo.ExitCode);
        Assert.Equal(File.ReadAllText(verificationOnePath), File.ReadAllText(verificationTwoPath));

        var inspectOnePath = workspace.PathOf("derived-inspection-one.json");
        var inspectTwoPath = workspace.PathOf("derived-inspection-two.json");
        var inspectOne = await RunDerivedInspectAsync(
            workspace, outputOnePath, baseline, binding, planOnePath, reportOnePath, inspectOnePath);
        var inspectTwo = await RunDerivedInspectAsync(
            workspace, outputTwoPath, baseline, binding, planTwoPath, reportTwoPath, inspectTwoPath);
        Assert.Equal(CliApplication.Success, inspectOne.ExitCode);
        Assert.Equal(CliApplication.Success, inspectTwo.ExitCode);
        Assert.Equal(File.ReadAllText(inspectOnePath), File.ReadAllText(inspectTwoPath));
        using (var inspection = JsonDocument.Parse(File.ReadAllText(inspectOnePath)))
        {
            var root = inspection.RootElement;
            Assert.True(root.GetProperty("verifiedLineage").GetBoolean());
            Assert.Equal(2, root.GetProperty("derivedContexts").GetArrayLength());
            Assert.False(root.GetProperty("physicalRpmAvailable").GetBoolean());
            Assert.Equal(
                "mismatched",
                root.GetProperty("outputInspection").GetProperty("baselineBinding").GetProperty("status").GetString());
            Assert.False(root.GetProperty("outputInspection").GetProperty("interpretationApplied").GetBoolean());
        }

        var console = string.Concat(planOne.Output, applyOne.Output, verifyOne.Output, inspectOne.Output);
        Assert.DoesNotContain(RomImage.Load(baseline).Hash.Sha256, console, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(baseline, console, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(binding, console, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(outputOnePath, console, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("173", console, StringComparison.Ordinal);
        Assert.Contains("checksum", applyOne.Error, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("not flash-ready", applyOne.Error, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(originalBaseline, File.ReadAllBytes(baseline));
        Assert.Equal(originalBinding, File.ReadAllBytes(binding));
        Assert.DoesNotContain(
            Directory.EnumerateFiles(workspace.RootPath),
            path => path.EndsWith(".tmp", StringComparison.Ordinal));
    }

    [Fact]
    public async Task NoOpPlanProducesASeparateIdenticalPcOnlyCopyAndVerifies()
    {
        using var workspace = new EditingWorkspace();
        var baseline = workspace.CreateRom("baseline.dat");
        var binding = workspace.CreateBinding("binding.json", baseline);
        var slot = P28ThresholdLogic.GetSlotId(0, 0, true);
        var offset = P28ThresholdLogic.ThresholdOffset(0, 0, true);
        var currentValue = File.ReadAllBytes(baseline)[offset];
        var planPath = workspace.PathOf("noop-plan.json");
        var outputPath = workspace.PathOf("noop-output.dat");
        var reportPath = workspace.PathOf("noop-report.json");

        var planResult = await workspace.RunAsync(
            "research", "p28-vtec", "plan", baseline,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--slot", slot,
            "--raw-value", currentValue.ToString(System.Globalization.CultureInfo.InvariantCulture),
            "--output", planPath);
        var applyResult = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", planPath,
            "--confirm-pc-only",
            "--output", outputPath,
            "--report", reportPath);
        var verifyResult = await workspace.RunAsync(
            "research", "p28-vtec", "verify", outputPath,
            "--baseline", baseline,
            "--baseline-binding", binding,
            "--plan", planPath,
            "--report", reportPath);

        Assert.Equal(CliApplication.Success, planResult.ExitCode);
        Assert.Equal(CliApplication.Success, applyResult.ExitCode);
        Assert.Equal(CliApplication.Success, verifyResult.ExitCode);
        Assert.Equal(File.ReadAllBytes(baseline), File.ReadAllBytes(outputPath));
        var plan = P28RawThresholdPlan.Load(planPath);
        var report = P28RawThresholdPatchReport.Load(reportPath);
        Assert.True(plan.IsNoOp);
        Assert.Empty(plan.ExpectedChangedOffsets);
        Assert.Empty(plan.PredicateImpact.ChangedCompactCodes);
        Assert.True(report.IsNoOp);
        Assert.Equal(0, report.ChangedByteCount);
        Assert.Empty(report.Diff);
        Assert.True(report.ReverseRestoresBaseline);
    }

    [Fact]
    public async Task TamperingAndEveryOverwriteAttemptAreRejectedWithoutChangingProtectedFiles()
    {
        using var workspace = new EditingWorkspace();
        var baseline = workspace.CreateRom("baseline.dat");
        var binding = workspace.CreateBinding("binding.json", baseline);
        var planPath = workspace.PathOf("plan.json");
        var outputPath = workspace.PathOf("output.dat");
        var reportPath = workspace.PathOf("report.json");
        var slot = P28ThresholdLogic.GetSlotId(1, 1, false);
        Assert.Equal(
            CliApplication.Success,
            (await workspace.RunAsync(
                "research", "p28-vtec", "plan", baseline,
                "--profile", P28ExactBaselineBinding.RequiredProfileId,
                "--confirm-profile",
                "--baseline-binding", binding,
                "--slot", slot,
                "--raw-value", "201",
                "--output", planPath)).ExitCode);
        Assert.Equal(
            CliApplication.Success,
            (await workspace.RunAsync(
                "research", "p28-vtec", "apply", baseline,
                "--baseline-binding", binding,
                "--plan", planPath,
                "--confirm-pc-only",
                "--output", outputPath,
                "--report", reportPath)).ExitCode);

        var originalBaseline = File.ReadAllBytes(baseline);
        var originalBinding = File.ReadAllBytes(binding);
        var originalPlan = File.ReadAllBytes(planPath);
        var originalOutput = File.ReadAllBytes(outputPath);
        var originalReport = File.ReadAllBytes(reportPath);

        var existing = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", planPath,
            "--confirm-pc-only",
            "--output", outputPath,
            "--report", reportPath);
        Assert.Equal(CliApplication.OperationError, existing.ExitCode);

        var reportOverPlan = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", planPath,
            "--confirm-pc-only",
            "--output", workspace.PathOf("must-not-exist.dat"),
            "--report", planPath);
        Assert.Equal(CliApplication.OperationError, reportOverPlan.ExitCode);
        Assert.False(File.Exists(workspace.PathOf("must-not-exist.dat")));

        var outputOverBaseline = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", planPath,
            "--confirm-pc-only",
            "--output", baseline,
            "--report", workspace.PathOf("must-not-exist.json"));
        Assert.Equal(CliApplication.OperationError, outputOverBaseline.ExitCode);
        Assert.False(File.Exists(workspace.PathOf("must-not-exist.json")));

        var tamperedOutputPath = workspace.PathOf("tampered-output.dat");
        var tampered = (byte[])originalOutput.Clone();
        tampered[100] ^= 0xFF;
        File.WriteAllBytes(tamperedOutputPath, tampered);
        var failedVerificationPath = workspace.PathOf("failed-verification.json");
        var verifyTampered = await workspace.RunAsync(
            "research", "p28-vtec", "verify", tamperedOutputPath,
            "--baseline", baseline,
            "--baseline-binding", binding,
            "--plan", planPath,
            "--report", reportPath,
            "--output", failedVerificationPath);
        Assert.Equal(CliApplication.VerificationFailed, verifyTampered.ExitCode);
        using (var verification = JsonDocument.Parse(File.ReadAllText(failedVerificationPath)))
        {
            Assert.False(verification.RootElement.GetProperty("isValid").GetBoolean());
            Assert.True(verification.RootElement.GetProperty("issues").GetArrayLength() > 0);
        }

        var failedInspectionPath = workspace.PathOf("failed-derived-inspection.json");
        var inspectTampered = await RunDerivedInspectAsync(
            workspace,
            tamperedOutputPath,
            baseline,
            binding,
            planPath,
            reportPath,
            failedInspectionPath);
        Assert.Equal(CliApplication.VerificationFailed, inspectTampered.ExitCode);
        using (var inspection = JsonDocument.Parse(File.ReadAllText(failedInspectionPath)))
        {
            Assert.False(inspection.RootElement.GetProperty("verifiedLineage").GetBoolean());
            Assert.Equal(0, inspection.RootElement.GetProperty("derivedContexts").GetArrayLength());
        }

        var parsedPlan = P28RawThresholdPlan.Load(planPath);
        var tamperedPlanPath = workspace.PathOf("tampered-plan.json");
        var planJson = File.ReadAllText(planPath);
        var tamperedPlanJson = planJson.Replace(
            $"\"offset\": {parsedPlan.Offset}",
            "\"offset\": 0",
            StringComparison.Ordinal);
        Assert.NotEqual(planJson, tamperedPlanJson);
        File.WriteAllText(tamperedPlanPath, tamperedPlanJson);
        var tamperedPlanOutput = workspace.PathOf("tampered-plan-output.dat");
        var tamperedPlanReport = workspace.PathOf("tampered-plan-report.json");
        var applyTamperedPlan = await workspace.RunAsync(
            "research", "p28-vtec", "apply", baseline,
            "--baseline-binding", binding,
            "--plan", tamperedPlanPath,
            "--confirm-pc-only",
            "--output", tamperedPlanOutput,
            "--report", tamperedPlanReport);
        Assert.Equal(CliApplication.OperationError, applyTamperedPlan.ExitCode);
        Assert.False(File.Exists(tamperedPlanOutput));
        Assert.False(File.Exists(tamperedPlanReport));

        Assert.Equal(originalBaseline, File.ReadAllBytes(baseline));
        Assert.Equal(originalBinding, File.ReadAllBytes(binding));
        Assert.Equal(originalPlan, File.ReadAllBytes(planPath));
        Assert.Equal(originalOutput, File.ReadAllBytes(outputPath));
        Assert.Equal(originalReport, File.ReadAllBytes(reportPath));
    }

    private static Task<CliResult> RunDerivedInspectAsync(
        EditingWorkspace workspace,
        string output,
        string baseline,
        string binding,
        string plan,
        string report,
        string inspectionOutput) =>
        workspace.RunAsync(
            "research", "p28-vtec", "inspect", output,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--baseline-binding", binding,
            "--baseline", baseline,
            "--plan", plan,
            "--patch-report", report,
            "--output", inspectionOutput);

    private sealed class EditingWorkspace : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-p28-edit-cli-{Guid.NewGuid():N}");

        public EditingWorkspace()
        {
            Directory.CreateDirectory(_root);
            var definitionsPath = Path.Combine(_root, "definitions", "p28");
            Directory.CreateDirectory(definitionsPath);
            ProfilePath = Path.Combine(definitionsPath, "p28-304.experimental.json");
            File.WriteAllText(ProfilePath, SyntheticProfileJson);
            DefinitionsPath = Path.Combine(_root, "definitions");
        }

        public string RootPath => _root;

        public string DefinitionsPath { get; }

        public string ProfilePath { get; }

        public string PathOf(string name) => Path.Combine(_root, name);

        public string CreateRom(string name, Action<byte[]>? mutate = null)
        {
            var bytes = new byte[P28ExactBaselineBinding.RequiredSize];
            for (var index = 0; index < P28ThresholdLogic.BlockLength; index++)
            {
                bytes[P28ThresholdLogic.BlockOffset + index] = (byte)(20 + (index * 10));
            }

            mutate?.Invoke(bytes);
            var path = PathOf(name);
            File.WriteAllBytes(path, bytes);
            return path;
        }

        public string CreateBinding(string name, string romPath)
        {
            var profile = RomProfile.Load(ProfilePath);
            var binding = new P28ExactBaselineBinding(
                P28ExactBaselineBinding.CurrentFormatVersion,
                P28CompactModel.ModelId,
                P28ExactBaselineBinding.RequiredProfileId,
                P28ExactBaselineBinding.RequiredSize,
                RomImage.Load(romPath).Hash,
                P28VtecInspector.ComputeProfileDigest(profile));
            var path = PathOf(name);
            File.WriteAllText(path, binding.ToJson());
            return path;
        }

        public async Task<CliResult> RunAsync(params string[] args)
        {
            using var output = new StringWriter();
            using var error = new StringWriter();
            var application = new CliApplication(output, error, _root, DefinitionsPath);
            var exitCode = await application.RunAsync(args);
            return new CliResult(exitCode, output.ToString(), error.ToString());
        }

        public void Dispose()
        {
            if (Directory.Exists(_root))
            {
                Directory.Delete(_root, recursive: true);
            }
        }

        private const string SyntheticProfileJson = """
            {
              "schemaVersion": "1.0",
              "id": "p28-304",
              "displayName": "Synthetic P28 raw-threshold CLI fixture",
              "description": "Generated test-only profile containing no OEM data.",
              "revisionScope": "synthetic-test-only",
              "status": "experimental",
              "format": {
                "kind": "raw-binary",
                "exactSize": 32768,
                "headerBytes": 0,
                "paddingAllowed": false,
                "truncationAllowed": false
              },
              "identity": {
                "requiresExplicitConfirmation": true,
                "hashes": [],
                "signatures": []
              },
              "parameters": [],
              "tables": [],
              "sources": [],
              "checksum": {
                "algorithmId": "unknown",
                "status": "unknown",
                "offset": 0,
                "length": 0,
                "evidenceLevel": "public-documentation",
                "excludedRegions": [],
                "notes": "No checksum algorithm is asserted by this synthetic fixture."
              }
            }
            """;
    }

    private sealed record CliResult(int ExitCode, string Output, string Error);
}
