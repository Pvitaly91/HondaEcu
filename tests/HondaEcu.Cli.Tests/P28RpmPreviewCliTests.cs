using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28RpmPreviewCliTests
{
    [Fact]
    public async Task MissingScalingWritesAnExplicitUnavailableReportWithoutRpmDefaults()
    {
        using var workspace = new Workspace();
        var original = File.ReadAllBytes(workspace.Baseline);
        var result = await workspace.RunAsync(workspace.Arguments());
        Assert.Equal(CliApplication.VerificationFailed, result.Code);
        using var json = JsonDocument.Parse(File.ReadAllText(workspace.Output));
        var root = json.RootElement;
        var planning = root.GetProperty("planning");
        Assert.Equal("bound-baseline-conditional-rpm-preview", root.GetProperty("purpose").GetString());
        Assert.False(planning.GetProperty("physicalRpmAvailable").GetBoolean());
        Assert.Equal("NotRun", planning.GetProperty("executionStatus").GetString());
        Assert.Equal("NotRun", planning.GetProperty("hardwareStatus").GetString());
        Assert.Equal(JsonValueKind.Null, planning.GetProperty("forward").ValueKind);
        Assert.Equal(0, planning.GetProperty("bestCandidates").GetArrayLength());
        Assert.Equal(0, planning.GetProperty("inverse").GetArrayLength());
        var reasons = planning.GetProperty("unavailableReasons").GetRawText();
        Assert.Contains("clockHz", reasons, StringComparison.Ordinal);
        Assert.Contains("eventsPerCrankRev", reasons, StringComparison.Ordinal);
        Assert.Contains("eventsPerSample", reasons, StringComparison.Ordinal);
        Assert.Equal(original, File.ReadAllBytes(workspace.Baseline));
        Assert.Contains("did not run Rust", result.Output, StringComparison.Ordinal);
    }

    [Fact]
    public async Task StrictDefaultDoesNotTurnExplicitScalingIntoConditionalSelection()
    {
        using var workspace = new Workspace();
        workspace.CreateScaling();
        var result = await workspace.RunAsync([.. workspace.Arguments(), "--scaling", workspace.Scaling]);
        Assert.Equal(CliApplication.VerificationFailed, result.Code);
        using var json = JsonDocument.Parse(File.ReadAllText(workspace.Output));
        var planning = json.RootElement.GetProperty("planning");
        Assert.Empty(planning.GetProperty("query").GetProperty("permittedAssumptions").EnumerateArray());
        Assert.Equal(0, planning.GetProperty("bestCandidates").GetArrayLength());
        Assert.Contains("unresolved", planning.GetRawText(), StringComparison.OrdinalIgnoreCase);
        Assert.False(planning.GetProperty("physicalRpmAvailable").GetBoolean());
    }

    [Fact]
    public async Task ExactOverrideIsRecordedSeparatelyAndNeverRewritesTheLegacyScenario()
    {
        using var workspace = new Workspace();
        workspace.CreateScaling();
        var scenario = File.ReadAllBytes(workspace.Scaling);
        var baseline = File.ReadAllBytes(workspace.Baseline);
        var result = await workspace.RunAsync([.. workspace.Arguments(), "--scaling", workspace.Scaling,
            "--rpm", "6001/2", "--rpm-provenance", "New exact CLI request; no hardware measurement",
            "--allow-assumption", "oki.add-er1-a", "--allow-assumption", "oki.add-er3-a"]);
        Assert.Equal(CliApplication.Success, result.Code);
        var reportText = File.ReadAllText(workspace.Output);
        using var json = JsonDocument.Parse(reportText);
        var planning = json.RootElement.GetProperty("planning");
        var query = planning.GetProperty("query");
        var requested = query.GetProperty("requestedRpm");
        Assert.Equal("6001", requested.GetProperty("numerator").GetString());
        Assert.Equal("2", requested.GetProperty("denominator").GetString());
        Assert.Equal("crank-revolutions/minute", requested.GetProperty("unit").GetString());
        Assert.Equal("New exact CLI request; no hardware measurement", requested.GetProperty("provenance").GetString());
        Assert.Contains("Original fixture query", reportText, StringComparison.Ordinal);
        Assert.Equal(256, planning.GetProperty("inverse").GetArrayLength());
        Assert.True(planning.GetProperty("bestCandidates").GetArrayLength() > 0);
        Assert.Equal(2, query.GetProperty("permittedAssumptions").GetArrayLength());
        var candidateForwards = json.RootElement.GetProperty("bestCandidateForwardPreviews").EnumerateArray().ToArray();
        Assert.Equal(planning.GetProperty("bestCandidates").GetArrayLength(), candidateForwards.Length);
        Assert.All(candidateForwards, candidate =>
        {
            var raw = candidate.GetProperty("rawValue").GetByte();
            var forward = candidate.GetProperty("forward");
            Assert.Equal(raw, forward.GetProperty("proposedRaw").GetByte());
            Assert.All(forward.GetProperty("variants").EnumerateArray(), variant =>
            {
                Assert.Contains(variant.GetProperty("oldPredicate").ValueKind, new[] { JsonValueKind.True, JsonValueKind.False });
                Assert.Contains(variant.GetProperty("newPredicate").ValueKind, new[] { JsonValueKind.True, JsonValueKind.False });
            });
        });
        Assert.Equal("NotRun", planning.GetProperty("executionStatus").GetString());
        Assert.False(planning.GetProperty("physicalRpmAvailable").GetBoolean());
        Assert.Equal(scenario, File.ReadAllBytes(workspace.Scaling));
        Assert.Equal(baseline, File.ReadAllBytes(workspace.Baseline));
    }

    [Theory]
    [InlineData("1")]
    [InlineData("900000")]
    public async Task InvalidRequestedEnvelopeCannotSelectAnAutomaticRawEvenWithBothPermissions(string rpm)
    {
        using var workspace = new Workspace();
        workspace.CreateScaling();
        var result = await workspace.RunAsync([.. workspace.Arguments(), "--scaling", workspace.Scaling,
            "--rpm", rpm, "--rpm-provenance", "Explicit invalid-domain test query",
            "--allow-assumption", "oki.add-er1-a", "--allow-assumption", "oki.add-er3-a"]);
        Assert.Equal(CliApplication.VerificationFailed, result.Code);
        using var json = JsonDocument.Parse(File.ReadAllText(workspace.Output));
        var planning = json.RootElement.GetProperty("planning");
        Assert.Equal("InvalidRequestedDomain", planning.GetProperty("status").GetString());
        Assert.Equal(0, planning.GetProperty("bestCandidates").GetArrayLength());
        Assert.Equal(256, planning.GetProperty("inverse").GetArrayLength());
        Assert.False(planning.GetProperty("forward").GetProperty("allVariantsNormal").GetBoolean());
        Assert.False(planning.GetProperty("physicalRpmAvailable").GetBoolean());
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    [InlineData("1/0")]
    [InlineData("1.5")]
    [InlineData("1e3")]
    [InlineData("1/2/3")]
    [InlineData("1000000000001/1")]
    public async Task RpmInputMustBeAnExactPositiveBoundedRational(string rpm)
    {
        using var workspace = new Workspace();
        workspace.CreateScaling();
        var result = await workspace.RunAsync([.. workspace.Arguments(), "--scaling", workspace.Scaling,
            "--rpm", rpm, "--rpm-provenance", "Invalid input test"]);
        Assert.NotEqual(CliApplication.Success, result.Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("--allow-all-unknown", "true")]
    [InlineData("--runner", "not-started.exe")]
    [InlineData("--compensation-definition", "not-loaded.json")]
    [InlineData("--raw-value", "50")]
    [InlineData("--offset", "25923")]
    [InlineData("--plan", "not-written.json")]
    public async Task PreviewHasNoExecutionPatchOrGlobalPermissionOptions(string option, string value)
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync([.. workspace.Arguments(), option, value]);
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.Contains("Unknown option", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task ProfileAcknowledgementSlotAndExactBindingAreMandatory()
    {
        using var workspace = new Workspace();
        foreach (var option in new[] { "--confirm-profile", "--slot", "--baseline-binding", "--profile" })
        {
            var args = workspace.Arguments().ToList();
            var position = args.IndexOf(option);
            args.RemoveRange(position, option == "--confirm-profile" ? 1 : 2);
            var result = await workspace.RunAsync(args.ToArray());
            Assert.Equal(CliApplication.UsageError, result.Code);
            Assert.Contains(option, result.Error, StringComparison.Ordinal);
            Assert.False(File.Exists(workspace.Output));
        }
    }

    [Fact]
    public async Task RepeatedAndUnknownAssumptionsCannotBroadenPermission()
    {
        using var workspace = new Workspace();
        foreach (var permissions in new[]
        {
            new[] { "oki.add-er1-a", "oki.add-er1-a" },
            new[] { "oki.add-er3-a", "oki.add-er3-a" },
            new[] { "all" },
            new[] { "oki.add-any" },
        })
        {
            var args = workspace.Arguments().Concat(permissions.SelectMany(value => new[] { "--allow-assumption", value })).ToArray();
            var result = await workspace.RunAsync(args);
            Assert.Equal(CliApplication.UsageError, result.Code);
            Assert.Contains("allow-assumption", result.Error, StringComparison.Ordinal);
            Assert.False(File.Exists(workspace.Output));
        }
    }

    [Fact]
    public async Task RpmOverrideAndItsProvenanceAreAnExplicitPair()
    {
        using var workspace = new Workspace();
        var noProvenance = await workspace.RunAsync([.. workspace.Arguments(), "--rpm", "3000/1"]);
        Assert.Equal(CliApplication.UsageError, noProvenance.Code);
        Assert.Contains("--rpm-provenance", noProvenance.Error, StringComparison.Ordinal);
        var noRpm = await workspace.RunAsync([.. workspace.Arguments(), "--rpm-provenance", "Analyst request"]);
        Assert.Equal(CliApplication.UsageError, noRpm.Code);
        Assert.Contains("--rpm", noRpm.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task SingleValueOptionsAndAcknowledgementCannotBeRepeated()
    {
        using var workspace = new Workspace();
        foreach (var extra in new[]
        {
            new[] { "--confirm-profile" },
            new[] { "--slot", P28ThresholdLogic.GetSlots()[1].Id },
            new[] { "--scaling", workspace.Scaling, "--scaling", workspace.Scaling },
            new[] { "--rpm", "3000", "--rpm", "4000", "--rpm-provenance", "Explicit query" },
        })
        {
            var result = await workspace.RunAsync([.. workspace.Arguments(), .. extra]);
            Assert.Equal(CliApplication.UsageError, result.Code);
            Assert.Contains("must", result.Error, StringComparison.OrdinalIgnoreCase);
            Assert.False(File.Exists(workspace.Output));
        }
    }

    [Fact]
    public async Task CancelledPreviewCannotPublishAReport()
    {
        using var workspace = new Workspace();
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var result = await workspace.RunAsync(workspace.Arguments(), cancellation.Token);
        Assert.Equal(CliApplication.OperationError, result.Code);
        Assert.Contains("cancelled", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task BaselineBindingProfileScalingAndExistingOutputAreProtected()
    {
        using var workspace = new Workspace();
        workspace.CreateScaling();
        foreach (var destination in new[] { workspace.Baseline, workspace.Binding, workspace.Profile.SourcePath!, workspace.Scaling })
        {
            var before = File.ReadAllBytes(destination);
            var args = workspace.Arguments();
            args[Array.IndexOf(args, "--output") + 1] = destination;
            var result = await workspace.RunAsync([.. args, "--scaling", workspace.Scaling]);
            Assert.Equal(CliApplication.OperationError, result.Code);
            Assert.Equal(before, File.ReadAllBytes(destination));
        }
        File.WriteAllText(workspace.Output, "preserved existing output");
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(workspace.Arguments())).Code);
        Assert.Equal("preserved existing output", File.ReadAllText(workspace.Output));
    }

    [Fact]
    public async Task MismatchedOriginalCannotAcquireRpmInterpretation()
    {
        using var workspace = new Workspace();
        var altered = File.ReadAllBytes(workspace.Baseline);
        altered[21] = 1;
        File.WriteAllBytes(workspace.Baseline, altered);
        var result = await workspace.RunAsync(workspace.Arguments());
        Assert.NotEqual(CliApplication.Success, result.Code);
        Assert.Contains("binding", result.Error + result.Output, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(altered, File.ReadAllBytes(workspace.Baseline));
    }

    private sealed class Workspace : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-rpm-cli-{Guid.NewGuid():N}");
        private readonly string _definitions;

        public Workspace()
        {
            Directory.CreateDirectory(_root);
            var repository = new DirectoryInfo(AppContext.BaseDirectory);
            while (repository is not null && !File.Exists(Path.Combine(repository.FullName, "Directory.Build.props"))) repository = repository.Parent;
            Assert.NotNull(repository);
            _definitions = Path.Combine(repository.FullName, "definitions");
            Profile = RomProfile.Load(Path.Combine(_definitions, "p28", "p28-304.experimental.json"));
            var invented = new byte[32768];
            invented.AsSpan(P28ThresholdLogic.BlockOffset, 8).Fill(80);
            File.WriteAllBytes(Baseline, invented);
            File.WriteAllText(Binding, new P28ExactBaselineBinding(1, P28CompactModel.ModelId, Profile.Id,
                invented.Length, RomImage.Load(Baseline).Hash, P28VtecInspector.ComputeProfileDigest(Profile)).ToJson());
        }

        public RomProfile Profile { get; }
        public string Baseline => Path.Combine(_root, "invented-parent.dat");
        public string Binding => Path.Combine(_root, "invented-binding.json");
        public string Scaling => Path.Combine(_root, "invented-scenario.json");
        public string Output => Path.Combine(_root, "new-rpm-report.json");
        public string[] Arguments() => ["research", "p28-vtec", "rpm-preview", Baseline,
            "--profile", "p28-304", "--confirm-profile", "--baseline-binding", Binding,
            "--slot", P28ThresholdLogic.GetSlots()[0].Id, "--output", Output];

        public void CreateScaling() => File.WriteAllText(Scaling, """
            {
              "formatVersion": 1, "scope": "uniform-normal-intervals",
              "quantities": {
                "clockHz": {"numerator":"960000","denominator":"1","unit":"Hz","provenance":"Invented mathematical fixture; not Honda hardware","evidence":"analyst-supplied"},
                "timerClockDivisor": {"numerator":"32","denominator":"1","unit":"1","provenance":"Explicit fixture divisor","evidence":"analyst-supplied"},
                "eventsPerCrankRev": {"numerator":"4","denominator":"1","unit":"events/crank-revolution","provenance":"Invented event geometry","evidence":"analyst-supplied"},
                "eventsPerSample": {"numerator":"1","denominator":"1","unit":"events/sample","provenance":"Invented normal sample","evidence":"analyst-supplied"},
                "rpm": {"numerator":"3000","denominator":"1","unit":"crank-revolutions/minute","provenance":"Original fixture query","evidence":"analyst-supplied"}
              }
            }
            """);

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
