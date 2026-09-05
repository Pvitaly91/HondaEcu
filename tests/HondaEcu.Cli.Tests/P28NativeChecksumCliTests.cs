using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28NativeChecksumCliTests
{
    [Fact]
    public async Task UnknownSyntheticRomRetainsArithmeticWithoutRunnerButNeverBecomesValid()
    {
        using var workspace = new Workspace();
        var before = File.ReadAllBytes(workspace.Baseline);
        var result = await workspace.RunAsync(workspace.Arguments());
        Assert.Equal(CliApplication.Success, result.Code);
        using var document = JsonDocument.Parse(File.ReadAllText(workspace.Output));
        var report = document.RootElement;
        var item = Assert.Single(report.GetProperty("cases").EnumerateArray());
        Assert.Equal("unknown", item.GetProperty("checksumStatus").GetString());
        Assert.Equal("unsupported-revision", item.GetProperty("disposition").GetString());
        Assert.Equal(0, item.GetProperty("arithmetic").GetProperty("computedResult").GetInt32());
        Assert.Equal(3, report.GetProperty("counts").GetProperty("notRun").GetInt32());
        Assert.False(report.GetProperty("repairPerformed").GetBoolean());
        Assert.Contains("NotFlashReady", result.Output, StringComparison.Ordinal);
        Assert.Equal(before, File.ReadAllBytes(workspace.Baseline));
    }

    [Theory]
    [InlineData("oki.add-er1-a")]
    [InlineData("oki.add-er3-a")]
    [InlineData("unknown")]
    public async Task NoInstructionAssumptionCanBeAppliedToChecksum(string assumption)
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync([.. workspace.Arguments(), "--allow-assumption", assumption]);
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.Contains("not applicable", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task AdmissionAndCompleteLineageAreRequiredWithoutStartingAProcess()
    {
        using var workspace = new Workspace();
        var missingAck = await workspace.RunAsync(workspace.Arguments().Where(value => value != "--confirm-profile").ToArray());
        Assert.Equal(CliApplication.UsageError, missingAck.Code);
        var partial = await workspace.RunAsync([.. workspace.Arguments(), "--derived", workspace.Baseline]);
        Assert.Equal(CliApplication.UsageError, partial.Code);
        Assert.Contains("together", partial.Error, StringComparison.Ordinal);
        var bytes = File.ReadAllBytes(workspace.Baseline); bytes[7] = 1;
        File.WriteAllBytes(workspace.Baseline, bytes);
        var badBinding = await workspace.RunAsync(workspace.Arguments());
        Assert.Equal(CliApplication.OperationError, badBinding.Code);
        Assert.Contains("matching research binding", badBinding.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task NewReportCannotOverwriteAnyInputAndMissingNamedRunnerStillProducesNotRun()
    {
        using var workspace = new Workspace();
        foreach (var path in new[] { workspace.Baseline, workspace.Binding, workspace.Profile.SourcePath!, workspace.Runner })
        {
            var arguments = workspace.Arguments();
            arguments[^1] = path;
            var before = File.Exists(path) ? File.ReadAllBytes(path) : null;
            var result = await workspace.RunAsync([.. arguments, "--runner", workspace.Runner]);
            Assert.Equal(CliApplication.OperationError, result.Code);
            if (before is not null) Assert.Equal(before, File.ReadAllBytes(path));
        }
        var missing = await workspace.RunAsync([.. workspace.Arguments(), "--runner", workspace.Runner]);
        Assert.Equal(CliApplication.Success, missing.Code);
        Assert.Contains("3 not-run", missing.Output, StringComparison.Ordinal);
        var existing = File.ReadAllBytes(workspace.Output);
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(workspace.Arguments())).Code);
        Assert.Equal(existing, File.ReadAllBytes(workspace.Output));
    }

    private sealed class Workspace : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-checksum-cli-{Guid.NewGuid():N}");
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
        public string Baseline => Path.Combine(_root, "synthetic-baseline.dat");
        public string Binding => Path.Combine(_root, "synthetic-binding.json");
        public string Runner => Path.Combine(_root, "missing-runner.exe");
        public string Output => Path.Combine(_root, "private-report.json");
        public string[] Arguments() => ["research", "p28-vtec", "checksum-check", Baseline, "--profile", "p28-304", "--confirm-profile",
            "--baseline-binding", Binding, "--output", Output];

        public async Task<(int Code, string Output, string Error)> RunAsync(string[] args)
        {
            using var output = new StringWriter(); using var error = new StringWriter();
            var code = await new CliApplication(output, error, _root, _definitions).RunAsync(args);
            return (code, output.ToString(), error.ToString());
        }

        public void Dispose() => Directory.Delete(_root, recursive: true);
    }
}
