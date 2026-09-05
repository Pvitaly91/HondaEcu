using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28ByteExecutionCliTests
{
    [Fact]
    public async Task ExecutionRequiresExplicitAcknowledgementAndOnlyTheNamedAssumption()
    {
        using var workspace = new Workspace();
        var missing = await workspace.RunAsync(workspace.Arguments().Where(arg => arg != "--confirm-profile").ToArray());
        Assert.Equal(CliApplication.UsageError, missing.Code);
        Assert.Contains("confirm-profile", missing.Error, StringComparison.Ordinal);
        var unknown = await workspace.RunAsync([.. workspace.Arguments(), "--allow-assumption", "any-unknown-opcode"]);
        Assert.Equal(CliApplication.UsageError, unknown.Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task WrongOriginalBindingAndPartialDerivedLineageAreRefusedBeforeStartingAnyProcess()
    {
        using var workspace = new Workspace();
        var changed = File.ReadAllBytes(workspace.Baseline);
        changed[1] = 1;
        File.WriteAllBytes(workspace.Baseline, changed);
        var mismatch = await workspace.RunAsync(workspace.Arguments());
        Assert.Equal(CliApplication.OperationError, mismatch.Code);
        Assert.Contains("matching research binding", mismatch.Error, StringComparison.Ordinal);
        Assert.DoesNotContain("could not be started", mismatch.Error, StringComparison.Ordinal);
        var partial = await workspace.RunAsync([.. workspace.Arguments(), "--derived", workspace.Baseline]);
        Assert.Equal(CliApplication.UsageError, partial.Code);
        Assert.Contains("together", partial.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task TamperedDerivedLineageFailsAndVerifiedLineageReachesTheExplicitRunnerStartCheck()
    {
        using var workspace = new Workspace();
        var baseline = RomImage.Load(workspace.Baseline);
        var profile = workspace.Profile;
        var binding = P28ExactBaselineBinding.Load(workspace.Binding);
        var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, P28ThresholdLogic.GetSlotId(0, 0, false), 1);
        var patch = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
        var derivedPath = workspace.PathOf("derived.dat");
        var planPath = workspace.PathOf("plan.json");
        var reportPath = workspace.PathOf("patch-report.json");
        File.WriteAllBytes(derivedPath, patch.Image.ToArray());
        File.WriteAllText(planPath, plan.ToJson());
        File.WriteAllText(reportPath, patch.Report.ToJson());
        string[] args = [.. workspace.Arguments(), "--derived", derivedPath, "--plan", planPath, "--patch-report", reportPath];
        var verified = await workspace.RunAsync(args);
        Assert.Equal(CliApplication.OperationError, verified.Code);
        Assert.Contains("Start", verified.Error, StringComparison.Ordinal);
        var tampered = patch.Image.ToArray();
        tampered[9] = 1;
        File.WriteAllBytes(derivedPath, tampered);
        var refused = await workspace.RunAsync(args);
        Assert.Equal(CliApplication.OperationError, refused.Code);
        Assert.Contains("M1c original-parent/plan/report verification failed", refused.Error, StringComparison.Ordinal);
        Assert.DoesNotContain("could not be started", refused.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
        Assert.Equal(binding.RomHash, RomImage.Load(workspace.Baseline).Hash);
    }

    [Fact]
    public async Task ReportCannotOverwriteAnInputBindingProfileOrRunnerPath()
    {
        using var workspace = new Workspace();
        foreach (var path in new[] { workspace.Baseline, workspace.Binding, workspace.Profile.SourcePath!, workspace.Runner })
        {
            var args = workspace.Arguments();
            args[^1] = path;
            var before = File.Exists(path) ? File.ReadAllBytes(path) : null;
            var result = await workspace.RunAsync(args);
            Assert.Equal(CliApplication.OperationError, result.Code);
            if (before is not null)
            {
                Assert.Equal(before, File.ReadAllBytes(path));
            }
        }
        Assert.False(File.Exists(workspace.Output));
    }

    private sealed class Workspace : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-execute-cli-{Guid.NewGuid():N}");
        private readonly string _definitions;

        public Workspace()
        {
            Directory.CreateDirectory(_root);
            var repository = new DirectoryInfo(AppContext.BaseDirectory);
            while (repository is not null && !File.Exists(Path.Combine(repository.FullName, "Directory.Build.props")))
            {
                repository = repository.Parent;
            }
            Assert.NotNull(repository);
            _definitions = Path.Combine(repository.FullName, "definitions");
            Profile = RomProfile.Load(Path.Combine(_definitions, "p28", "p28-304.experimental.json"));
            File.WriteAllBytes(Baseline, new byte[32768]);
            var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, Profile.Id, 32768,
                RomImage.Load(Baseline).Hash, P28VtecInspector.ComputeProfileDigest(Profile));
            File.WriteAllText(Binding, binding.ToJson());
        }

        public RomProfile Profile { get; }
        public string Baseline => PathOf("synthetic-baseline.dat");
        public string Binding => PathOf("synthetic-binding.json");
        public string Runner => PathOf("absent-runner");
        public string Output => PathOf("report.json");
        public string PathOf(string name) => Path.Combine(_root, name);
        public string[] Arguments() => ["research", "p28-vtec", "execute-check", Baseline, "--profile", "p28-304", "--confirm-profile",
            "--baseline-binding", Binding, "--runner", Runner, "--output", Output];

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
