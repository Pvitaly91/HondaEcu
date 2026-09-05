using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28ProducerCliTests
{
    [Fact]
    public async Task NamedAssumptionsAreRepeatableButDuplicatesAndGlobalPermissionsAreRefused()
    {
        using var workspace = new Workspace();
        var both = await workspace.RunAsync([.. workspace.Arguments, "--allow-assumption", "oki.add-er1-a", "--allow-assumption", "oki.add-er3-a"]);
        Assert.Equal(CliApplication.OperationError, both.Code);
        Assert.Contains("Start", both.Error, StringComparison.Ordinal);
        var duplicate = await workspace.RunAsync([.. workspace.Arguments, "--allow-assumption", "oki.add-er1-a", "--allow-assumption", "oki.add-er1-a"]);
        Assert.Equal(CliApplication.UsageError, duplicate.Code);
        var all = await workspace.RunAsync([.. workspace.Arguments, "--allow-assumption", "all"]);
        Assert.Equal(CliApplication.UsageError, all.Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task BindingAcknowledgementAndCompleteOriginalLineageRemainRequired()
    {
        using var workspace = new Workspace();
        var missing = await workspace.RunAsync(workspace.Arguments.Where(value => value != "--confirm-profile").ToArray());
        Assert.Equal(CliApplication.UsageError, missing.Code);
        var partial = await workspace.RunAsync([.. workspace.Arguments, "--derived", workspace.Baseline]);
        Assert.Equal(CliApplication.UsageError, partial.Code);
        var changed = File.ReadAllBytes(workspace.Baseline);
        changed[1] = 1;
        File.WriteAllBytes(workspace.Baseline, changed);
        var wrong = await workspace.RunAsync(workspace.Arguments);
        Assert.Equal(CliApplication.OperationError, wrong.Code);
        Assert.Contains("matching research binding", wrong.Error, StringComparison.Ordinal);
        Assert.DoesNotContain("could not be started", wrong.Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task MalformedScalingAndOverwritingItsSourceAreRejectedWithoutProducingAReport()
    {
        using var workspace = new Workspace();
        var scaling = workspace.PathOf("bad-scaling.json");
        File.WriteAllText(scaling, "{}");
        var malformed = await workspace.RunAsync([.. workspace.Arguments, "--scaling", scaling]);
        Assert.Equal(CliApplication.OperationError, malformed.Code);
        Assert.DoesNotContain("could not be started", malformed.Error, StringComparison.Ordinal);
        var args = workspace.Arguments;
        args[^1] = scaling;
        var overwrite = await workspace.RunAsync([.. args, "--scaling", scaling]);
        Assert.Equal(CliApplication.OperationError, overwrite.Code);
        Assert.Equal("{}", File.ReadAllText(scaling));
        Assert.False(File.Exists(workspace.Output));
    }

    private sealed class Workspace : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-producer-cli-{Guid.NewGuid():N}");
        private readonly string _definitions;

        public Workspace()
        {
            Directory.CreateDirectory(_root);
            var directory = new DirectoryInfo(AppContext.BaseDirectory);
            while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "Directory.Build.props"))) { directory = directory.Parent; }
            Assert.NotNull(directory);
            _definitions = Path.Combine(directory.FullName, "definitions");
            var profile = RomProfile.Load(Path.Combine(_definitions, "p28", "p28-304.experimental.json"));
            File.WriteAllBytes(Baseline, new byte[32768]);
            var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768, RomImage.Load(Baseline).Hash,
                P28VtecInspector.ComputeProfileDigest(profile));
            File.WriteAllText(Binding, binding.ToJson());
        }
        public string Baseline => PathOf("baseline.dat");
        public string Binding => PathOf("binding.json");
        public string Output => PathOf("report.json");
        public string PathOf(string name) => Path.Combine(_root, name);
        public string[] Arguments => ["research", "p28-vtec", "producer-check", Baseline, "--profile", "p28-304", "--confirm-profile",
            "--baseline-binding", Binding, "--runner", PathOf("absent-runner"), "--output", Output];
        public async Task<(int Code, string Error)> RunAsync(string[] args)
        {
            using var output = new StringWriter();
            using var error = new StringWriter();
            var code = await new CliApplication(output, error, _root, _definitions).RunAsync(args);
            return (code, error.ToString());
        }
        public void Dispose() => Directory.Delete(_root, recursive: true);
    }
}
