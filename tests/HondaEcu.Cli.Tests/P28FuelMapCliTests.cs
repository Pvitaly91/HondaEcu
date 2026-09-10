using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28FuelMapCliTests
{
    [Theory]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--profile")]
    public async Task LookupRequiresClosedInputsAndConfirmation(string missing)
    {
        using var workspace = new Workspace(); var arguments = workspace.LookupArguments().ToList();
        var index = arguments.IndexOf(missing); arguments.RemoveRange(index, 2);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(arguments.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(workspace.LookupArguments().Where(value => value != "--confirm-profile").ToArray())).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("--offset")]
    [InlineData("--expected-index")]
    [InlineData("--ram")]
    [InlineData("--allow-assumption")]
    [InlineData("--output-bin")]
    public async Task EditingAndExpectedInjectionOptionsAreUnavailable(string option)
    {
        using var workspace = new Workspace();
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync([.. workspace.LookupArguments(), option, "1"])).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task InspectorIsReadOnlyAndUnknownImageStaysGeneral()
    {
        using var workspace = new Workspace(); var before = workspace.Snapshot();
        var result = await workspace.RunAsync(["research", "p28-fuel", "maps-inspect", workspace.Baseline, "--profile", "p28-304", "--confirm-profile", "--output", workspace.Output]);
        Assert.Equal(CliApplication.Success, result.Code);
        var node = JsonNode.Parse(File.ReadAllText(workspace.Output))!;
        Assert.False(node["interpretationApplied"]!.GetValue<bool>()); Assert.Empty(node["maps"]!.AsArray());
        workspace.AssertUnchanged(before);
    }

    [Fact]
    public async Task ExactInventedBindingProducesBoundedGeometryWithoutFirmwareOutput()
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync(["research", "p28-fuel", "maps-inspect", workspace.Baseline, "--profile", "p28-304", "--confirm-profile",
            "--baseline-binding", workspace.Binding, "--output", workspace.Output]);
        Assert.Equal(CliApplication.Success, result.Code);
        var node = JsonNode.Parse(File.ReadAllText(workspace.Output))!;
        Assert.True(node["interpretationApplied"]!.GetValue<bool>()); Assert.Equal(2, node["maps"]!.AsArray().Count); Assert.Equal(3, node["axes"]!.AsArray().Count);
        Assert.Equal("None", node["firmwareOutput"]!.GetValue<string>()); Assert.False(File.Exists(Path.Combine(workspace.Root, "output.bin")));
    }

    [Fact]
    public async Task ActualRustSubprocessReportsUnresolvedThenNullSuffixForInventedProgram()
    {
        using var workspace = new Workspace();
        Assert.True(File.Exists(workspace.Runner), "Pinned release runner is required; this integration test never silently skips.");
        var before = workspace.Snapshot(); var result = await workspace.RunAsync(workspace.LookupArguments());
        Assert.Equal(CliApplication.VerificationFailed, result.Code);
        var node = JsonNode.Parse(File.ReadAllText(workspace.Output))!;
        foreach (var sequence in node["images"]![0]!["sequences"]!.AsArray())
        {
            Assert.Equal("Unresolved", sequence!["checkpoints"]![0]!["disposition"]!.GetValue<string>());
            Assert.Equal("NotRun", sequence["checkpoints"]![1]!["disposition"]!.GetValue<string>());
            Assert.Null(sequence["checkpoints"]![1]!["actualLookupResult"]);
        }
        workspace.AssertUnchanged(before);
    }

    [Fact]
    public async Task CancellationLeavesNoReport()
    {
        using var workspace = new Workspace(); using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        var result = await workspace.RunAsync(workspace.LookupArguments(), cancellation.Token);
        Assert.Equal(CliApplication.OperationError, result.Code); Assert.False(File.Exists(workspace.Output));
    }

    private sealed class Workspace : IDisposable
    {
        private readonly string _definitions;
        public Workspace()
        {
            Directory.CreateDirectory(Root);
            var directory = new DirectoryInfo(AppContext.BaseDirectory);
            while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "Directory.Build.props"))) directory = directory.Parent;
            Assert.NotNull(directory); var repository = directory!.FullName;
            _definitions = Path.Combine(repository, "definitions");
            var profile = RomProfile.Load(Path.Combine(_definitions, "p28", "p28-304.experimental.json"));
            File.WriteAllBytes(Baseline, Image());
            File.WriteAllText(Binding, new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768,
                RomImage.Load(Baseline).Hash, P28VtecInspector.ComputeProfileDigest(profile)).ToJson());
            File.WriteAllText(Scenario, P28FuelMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 9, 0),
                [new(0, "map_0", 0, 0, 0), new(1, "map_1", 255, 255, 255)], "Invented CLI subprocess test.").ToJson());
            Runner = Path.Combine(repository, "rust", "p28-slice-runner", "target", "release", OperatingSystem.IsWindows() ? "p28-slice-runner.exe" : "p28-slice-runner");
        }

        public string Root { get; } = Path.Combine(Path.GetTempPath(), $"hondaecu-fuel-cli-{Guid.NewGuid():N}");
        public string Baseline => Path.Combine(Root, "invented-parent.bin");
        public string Binding => Path.Combine(Root, "invented-binding.json");
        public string Scenario => Path.Combine(Root, "invented-scenario.json");
        public string Output => Path.Combine(Root, "new-report.json");
        public string Runner { get; }
        public string[] LookupArguments() => ["research", "p28-fuel", "lookup-check", Baseline, "--profile", "p28-304", "--confirm-profile",
            "--baseline-binding", Binding, "--runner", Runner, "--scenario", Scenario, "--output", Output];
        public Dictionary<string, byte[]> Snapshot() => new[] { Baseline, Binding, Scenario, Runner }.ToDictionary(path => path, File.ReadAllBytes);
        public void AssertUnchanged(Dictionary<string, byte[]> snapshot) { foreach (var pair in snapshot) Assert.Equal(pair.Value, File.ReadAllBytes(pair.Key)); }
        public async Task<(int Code, string Output, string Error)> RunAsync(string[] args, CancellationToken cancellationToken = default)
        {
            using var output = new StringWriter(); using var error = new StringWriter();
            var code = await new CliApplication(output, error, Root, _definitions).RunAsync(args, cancellationToken);
            return (code, output.ToString(), error.ToString());
        }
        public void Dispose() => Directory.Delete(Root, true);

        private static byte[] Image()
        {
            var bytes = new byte[32768];
            new byte[] { 0, 20, 40, 60, 80, 100, 120, 140, 240, 0 }.CopyTo(bytes, P28FuelMapContract.LoadAxisOrigin);
            Enumerable.Range(0, 19).Select(index => (byte)(index * 10)).Append((byte)0).ToArray().CopyTo(bytes, P28FuelMapContract.Map0RpmAxisOrigin);
            Enumerable.Range(0, 19).Select(index => (byte)(index * 11)).Append((byte)0).ToArray().CopyTo(bytes, P28FuelMapContract.Map1RpmAxisOrigin);
            foreach (var map in P28FuelMapContract.Maps)
            {
                for (var index = 0; index < 200; index++) bytes[map.Origin + index] = (byte)(1 + index % 200);
                for (var column = 0; column < 10; column++) bytes[map.MetadataOrigin + column] = (byte)(column + 1);
            }
            bytes[0x0A0C] = 0x60; bytes[0x0A0D] = 0x14; bytes[0x0A0E] = 0x70;
            bytes[0x0A24] = 0x60; bytes[0x0A25] = 0x28; bytes[0x0A26] = 0x70;
            bytes[0x0A65] = 0x60; bytes[0x0A66] = 0x00; bytes[0x0A67] = 0x70;
            bytes[0x12FC] = 0x98; bytes[0x12FD] = 10; bytes[0x12FE] = 0x99; bytes[0x12FF] = 20;
            bytes[0x130C] = 0x60; bytes[0x130D] = 0x22; bytes[0x130E] = 0x71;
            bytes[0x1323] = 0x60; bytes[0x1324] = 0x50; bytes[0x1325] = 0x70;
            bytes[0x131A] = 0xE9; bytes[0x131B] = 0x27;
            bytes[0x12DF] = 0xC4; bytes[0x12E0] = 0x27; bytes[0x12E1] = 0x09;
            bytes[0x12F9] = 0xC4; bytes[0x12FA] = 0x27; bytes[0x12FB] = 0x19;
            return bytes;
        }
    }
}
