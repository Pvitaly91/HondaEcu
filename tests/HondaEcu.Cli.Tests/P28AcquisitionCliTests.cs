using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28AcquisitionCliTests
{
    [Fact]
    public async Task HelpDocumentsExplicitSequenceCompositionPermissionsAndCompleteM1gLineage()
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync(["help"]);
        Assert.Equal(CliApplication.Success, result.Code);
        Assert.Contains("acquisition-check", result.Output, StringComparison.Ordinal);
        Assert.Contains("--scenario", result.Output, StringComparison.Ordinal);
        Assert.Contains("acquisition-only|scheduled-g-f-threshold", result.Output, StringComparison.Ordinal);
        Assert.Contains("oki.add-er1-a", result.Output, StringComparison.Ordinal);
        Assert.Contains("oki.add-er3-a", result.Output, StringComparison.Ordinal);
        Assert.Contains("--export-report", result.Output, StringComparison.Ordinal);
        Assert.Contains("--compensation-definition", result.Output, StringComparison.Ordinal);
        Assert.Contains("--envelope-scaling", result.Output, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("--profile")]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    public async Task EveryRequiredOptionAndProfileConfirmationAreMandatory(string missingOption)
    {
        using var workspace = new Workspace();
        var missing = await workspace.RunAsync(RemoveOption(workspace.Arguments(), missingOption));
        Assert.Equal(CliApplication.UsageError, missing.Code);
        Assert.Contains(missingOption, missing.Error, StringComparison.Ordinal);
        var unconfirmed = await workspace.RunAsync(workspace.Arguments().Where(value => value != "--confirm-profile").ToArray());
        Assert.Equal(CliApplication.UsageError, unconfirmed.Code);
        Assert.Contains("confirm-profile", unconfirmed.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("full-boot")]
    [InlineData("scheduled")]
    [InlineData("ACQUISITION-ONLY")]
    public async Task UnknownCompositionCannotBroadenTheExecutionScope(string composition)
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync([.. workspace.Arguments(), "--composition", composition]);
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.Contains("--composition", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("oki.add-er1-a")]
    [InlineData("oki.add-er3-a")]
    public async Task EachSpecificPermissionIsAcceptedIndependentlyButDoesNotBypassMalformedScenario(string assumption)
    {
        using var workspace = new Workspace();
        workspace.WriteMalformedScenario();
        foreach (var composition in new[] { "acquisition-only", "scheduled-g-f-threshold" })
        {
            var result = await workspace.RunAsync([.. workspace.Arguments(), "--composition", composition, "--allow-assumption", assumption]);
            Assert.Equal(CliApplication.OperationError, result.Code);
            Assert.Contains("Missing required capture scenario field", result.Error, StringComparison.Ordinal);
            Assert.False(File.Exists(workspace.Output));
        }
    }

    [Fact]
    public async Task BothPermissionsStillRequireValidInputAndDuplicatesOrGlobalPermissionsAreRejected()
    {
        using var workspace = new Workspace();
        workspace.WriteMalformedScenario();
        var both = await workspace.RunAsync([.. workspace.Arguments(), "--allow-assumption", "oki.add-er1-a", "--allow-assumption", "oki.add-er3-a"]);
        Assert.Equal(CliApplication.OperationError, both.Code);
        Assert.Contains("Missing required capture scenario field", both.Error, StringComparison.Ordinal);
        foreach (var permissions in new[]
        {
            new[] { "all" }, new[] { "unknown" }, new[] { "oki.add-er1-a", "oki.add-er1-a" }, new[] { "oki.add-er3-a", "oki.add-er3-a" },
        })
        {
            var args = workspace.Arguments().Concat(permissions.SelectMany(permission => new[] { "--allow-assumption", permission })).ToArray();
            var result = await workspace.RunAsync(args);
            Assert.Equal(CliApplication.UsageError, result.Code);
            Assert.Contains("distinct explicit", result.Error, StringComparison.Ordinal);
        }
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task EveryIncompleteM1gTupleIsRefusedBeforeReadingOrExecutingItsMembers()
    {
        using var workspace = new Workspace();
        var tuple = new[] { ("--derived", workspace.Derived), ("--plan", workspace.Plan), ("--export-report", workspace.Receipt), ("--compensation-definition", workspace.Definition) };
        for (var mask = 1; mask < 15; mask++)
        {
            var args = workspace.Arguments().Concat(tuple.Where((_, index) => (mask & (1 << index)) != 0).SelectMany(item => new[] { item.Item1, item.Item2 })).ToArray();
            var result = await workspace.RunAsync(args);
            Assert.Equal(CliApplication.UsageError, result.Code);
            Assert.Contains("together", result.Error, StringComparison.Ordinal);
        }
        // Complete spelling is not a signature, lineage or executor authority.
        workspace.WriteLineagePlaceholders();
        workspace.WriteMalformedScenario();
        var complete = await workspace.RunAsync([.. workspace.Arguments(), .. workspace.LineageArguments()]);
        Assert.Equal(CliApplication.OperationError, complete.Code);
        Assert.Contains("Missing required capture scenario field", complete.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("--patch-report")]
    [InlineData("--allow-unverified")]
    [InlineData("--force")]
    [InlineData("--sfr-write")]
    public async Task LegacyOrAuthorityExpandingOptionsAreNotAccepted(string option)
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync([.. workspace.Arguments(), option, "untrusted"]);
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task EnvelopeParametersRequireTheirExplicitScenarioAndSlotPair()
    {
        using var workspace = new Workspace();
        foreach (var options in new[]
        {
            new[] { "--envelope-slot", "context_0.pair_0.state_0" },
            new[] { "--envelope-scaling", workspace.Scaling },
            new[] { "--envelope-rpm", "3000/1" },
            new[] { "--envelope-rpm-provenance", "invented" },
        })
        {
            var result = await workspace.RunAsync([.. workspace.Arguments(), .. options]);
            Assert.Equal(CliApplication.UsageError, result.Code);
            Assert.Contains("Envelope comparison requires", result.Error, StringComparison.Ordinal);
        }
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("null")]
    [InlineData("duplicate")]
    [InlineData("unknown")]
    [InlineData("malformed")]
    public async Task ScenarioSchemaFailuresHappenBeforeRunnerStartAndPreserveInputs(string failure)
    {
        using var workspace = new Workspace();
        var json = File.ReadAllText(workspace.Scenario);
        var root = JsonNode.Parse(json)!.AsObject();
        if (failure == "missing") { root.Remove("initialState"); }
        if (failure == "null") { root["observations"] = null; }
        if (failure == "unknown") { root["sfrWrites"] = new JsonArray(); }
        var invalid = failure == "duplicate" ? json.Replace("\"formatVersion\":", "\"formatVersion\":1,\"formatVersion\":", StringComparison.Ordinal) :
            failure == "malformed" ? "{" : root.ToJsonString();
        File.WriteAllText(workspace.Scenario, invalid);
        var snapshot = workspace.InputSnapshot();
        var result = await workspace.RunAsync(workspace.Arguments());
        Assert.Equal(CliApplication.OperationError, result.Code);
        Assert.NotEmpty(result.Error);
        if (failure != "malformed") { Assert.Contains("capture scenario field", result.Error, StringComparison.Ordinal); }
        Assert.False(File.Exists(workspace.Output));
        workspace.AssertUnchanged(snapshot);
    }

    [Fact]
    public async Task MissingScenarioAndRunnerPathsCannotPublishOrModifyAnyInput()
    {
        using var workspace = new Workspace();
        var snapshot = workspace.InputSnapshot();
        foreach (var option in new[] { "--scenario", "--runner" })
        {
            var args = ReplaceOption(workspace.Arguments(), option, Path.Combine(workspace.Root, "absent-file"));
            var result = await workspace.RunAsync(args);
            Assert.Equal(CliApplication.OperationError, result.Code);
            Assert.False(File.Exists(workspace.Output));
            workspace.AssertUnchanged(snapshot);
        }
    }

    [Fact]
    public async Task OutputCannotAliasAnyOriginalScenarioRunnerProfileOrLineageInput()
    {
        using var workspace = new Workspace();
        workspace.WriteLineagePlaceholders();
        File.WriteAllText(workspace.Scaling, "untrusted mathematical scenario");
        foreach (var path in new[] { workspace.Baseline, workspace.Binding, workspace.Runner, workspace.Scenario, workspace.Profile.SourcePath!, workspace.Derived, workspace.Plan, workspace.Receipt, workspace.Definition, workspace.Scaling })
        {
            var before = File.ReadAllBytes(path);
            var args = ReplaceOption(workspace.Arguments(), "--output", path);
            var result = await workspace.RunAsync([.. args, .. workspace.LineageArguments(), "--envelope-scaling", workspace.Scaling, "--envelope-slot", P28ThresholdLogic.GetSlots()[0].Id]);
            Assert.Equal(CliApplication.OperationError, result.Code);
            Assert.Equal(before, File.ReadAllBytes(path));
        }
        var normalizedAlias = Path.Combine(workspace.Root, "unused", "..", Path.GetFileName(workspace.Scenario));
        var alias = await workspace.RunAsync(ReplaceOption(workspace.Arguments(), "--output", normalizedAlias));
        Assert.Equal(CliApplication.OperationError, alias.Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task ExistingOutputIsImmutableAndRejectedNewPathDoesNotCreateParentDirectories()
    {
        using var workspace = new Workspace();
        File.WriteAllText(workspace.Output, "preserve prior report");
        var existing = await workspace.RunAsync(workspace.Arguments());
        Assert.Equal(CliApplication.OperationError, existing.Code);
        Assert.Contains("already exists", existing.Error, StringComparison.Ordinal);
        Assert.Equal("preserve prior report", File.ReadAllText(workspace.Output));
        workspace.WriteMalformedScenario();
        var parent = Path.Combine(workspace.Root, "not-created");
        var failed = await workspace.RunAsync(ReplaceOption(workspace.Arguments(), "--output", Path.Combine(parent, "new.json")));
        Assert.Equal(CliApplication.OperationError, failed.Code);
        Assert.False(Directory.Exists(parent));
    }

    [Fact]
    public async Task CancellationBeforeAdmissionDoesNotPublishAnything()
    {
        using var workspace = new Workspace();
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var snapshot = workspace.InputSnapshot();
        var result = await workspace.RunAsync(workspace.Arguments(), cancellation.Token);
        Assert.Equal(CliApplication.OperationError, result.Code);
        Assert.Contains("cancelled", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
        workspace.AssertUnchanged(snapshot);
    }

    private static string[] RemoveOption(string[] arguments, string option)
    {
        var index = Array.IndexOf(arguments, option);
        Assert.True(index >= 0);
        return arguments.Where((_, position) => position != index && position != index + 1).ToArray();
    }

    private static string[] ReplaceOption(string[] arguments, string option, string value)
    {
        arguments[Array.IndexOf(arguments, option) + 1] = value;
        return arguments;
    }

    internal sealed class Workspace : IDisposable
    {
        private readonly string _definitions;
        public Workspace()
        {
            Directory.CreateDirectory(Root);
            var repository = new DirectoryInfo(AppContext.BaseDirectory);
            while (repository is not null && !File.Exists(Path.Combine(repository.FullName, "Directory.Build.props"))) { repository = repository.Parent; }
            Assert.NotNull(repository);
            _definitions = Path.Combine(repository.FullName, "definitions");
            Profile = RomProfile.Load(Path.Combine(_definitions, "p28", "p28-304.experimental.json"));
            File.WriteAllBytes(Baseline, new byte[32768]);
            File.WriteAllText(Binding, new P28ExactBaselineBinding(1, P28CompactModel.ModelId, Profile.Id, 32768,
                RomImage.Load(Baseline).Hash, P28VtecInspector.ComputeProfileDigest(Profile)).ToJson());
            // Harmless non-executable input permits preflight snapshot reads. Every test
            // stops before execution; this is never an external runner implementation.
            File.WriteAllText(Runner, "This is a synthetic text sentinel, not an executable.");
            var state = new P28AcquisitionState(100, new ushort[] { 11, 22, 33, 44, 55, 66 }, 0, 0, 0, 0, 0xFFFF, 0, 0, 0);
            var observation = new P28CaptureObservation(0, 120, 0, 0x92, 0, false, 0, 0, false);
            File.WriteAllText(Scenario, P28AcquisitionScenario.Create(state, [observation], "Invented CLI preflight test.").ToJson(false));
        }

        public string Root { get; } = Path.Combine(Path.GetTempPath(), $"hondaecu-acquisition-cli-{Guid.NewGuid():N}");
        public RomProfile Profile { get; }
        public string Baseline => Path.Combine(Root, "invented-parent.dat");
        public string Binding => Path.Combine(Root, "invented-binding.json");
        public string Runner => Path.Combine(Root, "non-executable-runner.txt");
        public string Scenario => Path.Combine(Root, "invented-capture-scenario.json");
        public string Output => Path.Combine(Root, "new-acquisition-report.json");
        public string Derived => Path.Combine(Root, "untrusted-child.dat");
        public string Plan => Path.Combine(Root, "untrusted-composed-plan.json");
        public string Receipt => Path.Combine(Root, "untrusted-export-receipt.json");
        public string Definition => Path.Combine(Root, "untrusted-compensation-definition.json");
        public string Scaling => Path.Combine(Root, "untrusted-envelope-scenario.json");

        public string[] Arguments() => ["research", "p28-vtec", "acquisition-check", Baseline, "--profile", "p28-304", "--confirm-profile",
            "--baseline-binding", Binding, "--runner", Runner, "--scenario", Scenario, "--output", Output];
        public string[] LineageArguments() => ["--derived", Derived, "--plan", Plan, "--export-report", Receipt, "--compensation-definition", Definition];
        public void WriteMalformedScenario() => File.WriteAllText(Scenario, "{}");
        public void WriteLineagePlaceholders()
        {
            foreach (var path in new[] { Derived, Plan, Receipt, Definition }) { File.WriteAllText(path, "Untrusted placeholder; no signature or lineage authority."); }
        }

        public Dictionary<string, byte[]> InputSnapshot() => new[] { Baseline, Binding, Runner, Scenario }.ToDictionary(path => path, File.ReadAllBytes);
        public void AssertUnchanged(Dictionary<string, byte[]> snapshot)
        {
            foreach (var (path, bytes) in snapshot) { Assert.Equal(bytes, File.ReadAllBytes(path)); }
        }

        public async Task<(int Code, string Output, string Error)> RunAsync(string[] args, CancellationToken cancellationToken = default)
        {
            using var output = new StringWriter();
            using var error = new StringWriter();
            var code = await new CliApplication(output, error, Root, _definitions).RunAsync(args, cancellationToken);
            return (code, output.ToString(), error.ToString());
        }

        public void Dispose() => Directory.Delete(Root, recursive: true);
    }
}
