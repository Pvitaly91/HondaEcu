using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28ChecksumExportCliTests
{
    [Fact]
    public async Task AvailabilityReportsUnrecognizedSyntheticCodeWithoutGrantingALocation()
    {
        using var workspace = new Workspace();
        var original = File.ReadAllBytes(workspace.Baseline);
        var result = await workspace.RunAsync(workspace.AvailabilityArguments());
        Assert.Equal(CliApplication.VerificationFailed, result.Code);
        using var json = JsonDocument.Parse(File.ReadAllText(workspace.Output));
        Assert.False(json.RootElement.GetProperty("isAvailable").GetBoolean());
        Assert.Equal("rejected-checksum-contract", json.RootElement.GetProperty("status").GetString());
        Assert.Equal(JsonValueKind.Null, json.RootElement.GetProperty("offset").ValueKind);
        Assert.Contains("NotFlashReady", result.Output, StringComparison.Ordinal);
        Assert.Equal(original, File.ReadAllBytes(workspace.Baseline));
        Assert.False(File.Exists(workspace.OutputRom));
    }

    [Theory]
    [InlineData("--force-compensation-offset", "32767")]
    [InlineData("--compensation-offset", "32767")]
    [InlineData("--allow-assumption", "oki.add-er1-a")]
    [InlineData("--allow-assumption", "oki.add-er3-a")]
    [InlineData("--issuer-public-key", "untrusted-key")]
    [InlineData("--sign-definition", "untrusted-document")]
    public async Task NoOffsetPermissionOrIssuerBypassIsAccepted(string option, string value)
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync([.. workspace.PlanArguments(), option, value]);
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.Contains("Unknown option", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
        Assert.False(File.Exists(workspace.OutputRom));
    }

    [Theory]
    [InlineData("-1")]
    [InlineData("256")]
    [InlineData("1.5")]
    [InlineData("0x10")]
    [InlineData("")]
    public async Task RawInputRejectsSignsOverflowFractionsAndHex(string value)
    {
        using var workspace = new Workspace();
        var arguments = workspace.PlanArguments();
        arguments[Array.IndexOf(arguments, "--raw-value") + 1] = value;
        var result = await workspace.RunAsync(arguments);
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.Contains("decimal digits", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task MissingOrRepeatedAcknowledgementAndDefinitionOptionsAreRejected()
    {
        using var workspace = new Workspace();
        var noAcknowledgement = workspace.PlanArguments().Where(value => value != "--confirm-profile").ToArray();
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(noAcknowledgement)).Code);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync([.. workspace.PlanArguments(), "--confirm-profile"])).Code);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync([.. workspace.PlanArguments(),
            "--compensation-definition", workspace.Definition, "--compensation-definition", workspace.Definition])).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task AnArbitraryJsonDeclarationCannotAuthorizeACompensationByte()
    {
        using var workspace = new Workspace();
        File.WriteAllText(workspace.Definition, "{\"status\":\"eligible\",\"candidateUnused\":true,\"offset\":32767,\"originalByte\":0}");
        var result = await workspace.RunAsync([.. workspace.PlanArguments(), "--compensation-definition", workspace.Definition]);
        Assert.Equal(CliApplication.OperationError, result.Code);
        Assert.False(File.Exists(workspace.Output));
        Assert.False(File.Exists(workspace.OutputRom));
    }

    [Fact]
    public async Task ExistingChildRequiresOriginalFullTupleAndCannotCombineAnotherThresholdRequest()
    {
        using var workspace = new Workspace();
        var partial = await workspace.RunAsync([.. workspace.BasePlanArguments(), "--derived", workspace.Child]);
        Assert.Equal(CliApplication.UsageError, partial.Code);
        Assert.Contains("together", partial.Error, StringComparison.Ordinal);
        workspace.CreateLegacyChild();
        var conflict = await workspace.RunAsync([.. workspace.PlanArguments(), .. workspace.LegacyArguments()]);
        Assert.Equal(CliApplication.UsageError, conflict.Code);
        Assert.Contains("not both", conflict.Error, StringComparison.Ordinal);

        var tampered = File.ReadAllBytes(workspace.Child);
        tampered[9] = 7;
        File.WriteAllBytes(workspace.Child, tampered);
        var invalid = await workspace.RunAsync([.. workspace.BasePlanArguments(), .. workspace.LegacyArguments()]);
        Assert.Equal(CliApplication.OperationError, invalid.Code);
        Assert.Contains("M1c original-parent/plan/report verification failed", invalid.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task ReportsCannotOverwriteTheOriginalBindingProfileDefinitionOrExistingOutput()
    {
        using var workspace = new Workspace();
        File.WriteAllText(workspace.Definition, "private test document, not an eligible definition");
        foreach (var path in new[] { workspace.Baseline, workspace.Binding, workspace.Profile.SourcePath!, workspace.Definition })
        {
            var before = File.ReadAllBytes(path);
            var args = workspace.AvailabilityArguments();
            args[^1] = path;
            var result = await workspace.RunAsync([.. args, "--compensation-definition", workspace.Definition]);
            Assert.Equal(CliApplication.OperationError, result.Code);
            Assert.Equal(before, File.ReadAllBytes(path));
        }
        File.WriteAllText(workspace.Output, "do not overwrite");
        var existing = await workspace.RunAsync(workspace.AvailabilityArguments());
        Assert.Equal(CliApplication.OperationError, existing.Code);
        Assert.Equal("do not overwrite", File.ReadAllText(workspace.Output));
    }

    [Fact]
    public async Task CancellationBeforeWorkCannotPublishAPlanOrReport()
    {
        using var workspace = new Workspace();
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var result = await workspace.RunAsync(workspace.AvailabilityArguments(), cancellation.Token);
        Assert.Equal(CliApplication.OperationError, result.Code);
        Assert.Contains("cancelled", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
        Assert.False(File.Exists(workspace.OutputRom));
    }

    [Fact]
    public async Task PublicationRequiresExplicitConsentAndAnExistingStrictRunner()
    {
        using var workspace = new Workspace();
        workspace.CreateSyntheticCompositionPlan();
        var arguments = workspace.ApplyArguments();
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(arguments.Where(value => value != "--confirm-pc-only").ToArray())).Code);
        var missingRunner = await workspace.RunAsync(arguments);
        Assert.Equal(CliApplication.OperationError, missingRunner.Code);
        Assert.Contains("strict complete native validation", missingRunner.Error, StringComparison.Ordinal);
        var permission = await workspace.RunAsync([.. arguments, "--allow-assumption", "oki.add-er3-a"]);
        Assert.Equal(CliApplication.UsageError, permission.Code);
        Assert.False(File.Exists(workspace.OutputRom));
        Assert.False(File.Exists(workspace.SavedPlan));
        Assert.False(File.Exists(workspace.ExportReport));
    }

    [Fact]
    public async Task PublicationCannotReuseReviewedPlanOrAnyExistingDestination()
    {
        using var workspace = new Workspace();
        workspace.CreateSyntheticCompositionPlan();
        // This is merely an existing protected path. No test launches this file.
        File.WriteAllText(workspace.Runner, "not an executable; path-protection test");
        foreach (var destination in new[] { workspace.Baseline, workspace.Binding, workspace.ComposedPlan, workspace.Runner })
        {
            var original = File.ReadAllBytes(destination);
            var arguments = workspace.ApplyArguments();
            arguments[Array.IndexOf(arguments, "--output") + 1] = destination;
            Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(arguments)).Code);
            Assert.Equal(original, File.ReadAllBytes(destination));
        }
        var samePlan = workspace.ApplyArguments();
        samePlan[Array.IndexOf(samePlan, "--saved-plan") + 1] = workspace.ComposedPlan;
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(samePlan)).Code);
        Assert.False(File.Exists(workspace.OutputRom));
        Assert.False(File.Exists(workspace.ExportReport));
    }

    [Fact]
    public async Task ReadbackRequiresCompleteOriginalLineageAndAClosedPlanVersion()
    {
        using var workspace = new Workspace();
        var missing = await workspace.RunAsync(["research", "p28-vtec", "checksum-export-verify", workspace.OutputRom]);
        Assert.Equal(CliApplication.UsageError, missing.Code);
        var invented = P28ChecksumPreservingEditor.CreateSyntheticPreview(P28ThresholdLogic.GetSlots()[0].Id, 41);
        File.WriteAllText(workspace.ComposedPlan, (invented.Plan with { FormatVersion = "999" }).ToJson());
        var unknown = await workspace.RunAsync(["research", "p28-vtec", "checksum-export-verify", workspace.OutputRom,
            "--baseline", workspace.Baseline, "--baseline-binding", workspace.Binding,
            "--plan", workspace.ComposedPlan, "--report", workspace.ExportReport, "--output", workspace.Output]);
        Assert.Equal(CliApplication.OperationError, unknown.Code);
        Assert.False(File.Exists(workspace.Output));
        Assert.False(File.Exists(workspace.OutputRom));
        var inspect = await workspace.RunAsync(["research", "p28-vtec", "checksum-export-inspect", workspace.OutputRom,
            "--baseline", workspace.Baseline, "--baseline-binding", workspace.Binding,
            "--plan", workspace.ComposedPlan, "--report", workspace.ExportReport]);
        Assert.Equal(CliApplication.UsageError, inspect.Code);
    }

    private sealed class Workspace : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-composition-cli-{Guid.NewGuid():N}");
        private readonly string _definitions;

        public Workspace()
        {
            Directory.CreateDirectory(_root);
            var repository = new DirectoryInfo(AppContext.BaseDirectory);
            while (repository is not null && !File.Exists(Path.Combine(repository.FullName, "Directory.Build.props"))) repository = repository.Parent;
            Assert.NotNull(repository);
            _definitions = Path.Combine(repository.FullName, "definitions");
            Profile = RomProfile.Load(Path.Combine(_definitions, "p28", "p28-304.experimental.json"));
            File.WriteAllBytes(Baseline, new byte[32768]);
            var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, Profile.Id, 32768,
                RomImage.Load(Baseline).Hash, P28VtecInspector.ComputeProfileDigest(Profile));
            File.WriteAllText(Binding, binding.ToJson());
        }

        public RomProfile Profile { get; }
        public string Baseline => Path.Combine(_root, "invented-parent.dat");
        public string Binding => Path.Combine(_root, "invented-binding.json");
        public string Definition => Path.Combine(_root, "untrusted-definition.json");
        public string Output => Path.Combine(_root, "new-report.json");
        public string OutputRom => Path.Combine(_root, "new-output.dat");
        public string Child => Path.Combine(_root, "invented-child.dat");
        public string LegacyPlan => Path.Combine(_root, "legacy-plan.json");
        public string LegacyReport => Path.Combine(_root, "legacy-report.json");
        public string ComposedPlan => Path.Combine(_root, "reviewed-composed-plan.json");
        public string SavedPlan => Path.Combine(_root, "new-plan-copy.json");
        public string ExportReport => Path.Combine(_root, "new-export-report.json");
        public string Runner => Path.Combine(_root, "missing-runner.dat");
        public string[] AvailabilityArguments() => ["research", "p28-vtec", "compensation-check", Baseline,
            "--profile", "p28-304", "--confirm-profile", "--baseline-binding", Binding, "--output", Output];
        public string[] BasePlanArguments() => ["research", "p28-vtec", "checksum-export-plan", Baseline,
            "--profile", "p28-304", "--confirm-profile", "--baseline-binding", Binding, "--output", Output];
        public string[] PlanArguments() => [.. BasePlanArguments(), "--slot", P28ThresholdLogic.GetSlots()[0].Id, "--raw-value", "1"];
        public string[] LegacyArguments() => ["--derived", Child, "--plan", LegacyPlan, "--patch-report", LegacyReport];
        public string[] ApplyArguments() => ["research", "p28-vtec", "checksum-export-apply", Baseline,
            "--baseline-binding", Binding, "--plan", ComposedPlan, "--runner", Runner, "--confirm-pc-only",
            "--output", OutputRom, "--saved-plan", SavedPlan, "--report", ExportReport];

        public void CreateSyntheticCompositionPlan() => File.WriteAllText(ComposedPlan,
            P28ChecksumPreservingEditor.CreateSyntheticPreview(P28ThresholdLogic.GetSlots()[0].Id, 41).Plan.ToJson());

        public void CreateLegacyChild()
        {
            var baseline = RomImage.Load(Baseline);
            var binding = P28ExactBaselineBinding.Load(Binding);
            var plan = P28RawThresholdEditor.CreatePlan(baseline, Profile, binding, true, P28ThresholdLogic.GetSlots()[0].Id, 1);
            var child = P28RawThresholdEditor.Apply(baseline, Profile, binding, plan);
            File.WriteAllBytes(Child, child.Image.ToArray());
            File.WriteAllText(LegacyPlan, plan.ToJson());
            File.WriteAllText(LegacyReport, child.Report.ToJson());
        }

        public async Task<(int Code, string Output, string Error)> RunAsync(string[] args, CancellationToken cancellationToken = default)
        {
            using var output = new StringWriter();
            using var error = new StringWriter();
            var code = await new CliApplication(output, error, _root, _definitions).RunAsync(args, cancellationToken);
            return (code, output.ToString(), error.ToString());
        }

        public void Dispose() => Directory.Delete(_root, recursive: true);
    }
}
