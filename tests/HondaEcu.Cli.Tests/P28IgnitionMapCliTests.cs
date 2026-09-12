using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28IgnitionMapCliTests
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
        Assert.Equal(CliApplication.UsageError,
            (await workspace.RunAsync(workspace.LookupArguments().Where(value => value != "--confirm-profile").ToArray())).Code);
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
        var result = await workspace.RunAsync(["research", "p28-ignition", "maps-inspect", workspace.Baseline,
            "--profile", "p28-304", "--confirm-profile", "--output", workspace.Output]);
        Assert.Equal(CliApplication.Success, result.Code);
        var node = JsonNode.Parse(File.ReadAllText(workspace.Output))!;
        Assert.False(node["interpretationApplied"]!.GetValue<bool>()); Assert.Empty(node["maps"]!.AsArray());
        workspace.AssertUnchanged(before);
    }

    [Fact]
    public async Task ExactInventedBindingProducesBoundedGeometryWithoutFirmwareOutput()
    {
        using var workspace = new Workspace();
        var result = await workspace.RunAsync(["research", "p28-ignition", "maps-inspect", workspace.Baseline,
            "--profile", "p28-304", "--confirm-profile", "--baseline-binding", workspace.Binding, "--output", workspace.Output]);
        Assert.Equal(CliApplication.Success, result.Code);
        var node = JsonNode.Parse(File.ReadAllText(workspace.Output))!;
        Assert.True(node["interpretationApplied"]!.GetValue<bool>()); Assert.Equal(2, node["maps"]!.AsArray().Count);
        Assert.Equal(3, node["axes"]!.AsArray().Count); Assert.Equal("None", node["firmwareOutput"]!.GetValue<string>());
        Assert.False(File.Exists(Path.Combine(workspace.Root, "output.bin")));
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
            Assert.NotNull(directory); var repository = directory!.FullName; _definitions = Path.Combine(repository, "definitions");
            var profile = RomProfile.Load(Path.Combine(_definitions, "p28", "p28-304.experimental.json"));
            File.WriteAllBytes(Baseline, Image());
            File.WriteAllText(Binding, new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768,
                RomImage.Load(Baseline).Hash, P28VtecInspector.ComputeProfileDigest(profile)).ToJson());
            File.WriteAllText(Scenario, P28IgnitionMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 0, 0),
                [new(0, "ignition_map_0", 0, 0, 0)], "Invented CLI test.").ToJson());
            Runner = Path.Combine(repository, "rust", "p28-slice-runner", "target", "release",
                OperatingSystem.IsWindows() ? "p28-slice-runner.exe" : "p28-slice-runner");
        }
        public string Root { get; } = Path.Combine(Path.GetTempPath(), $"hondaecu-ignition-cli-{Guid.NewGuid():N}");
        public string Baseline => Path.Combine(Root, "invented-parent.bin");
        public string Binding => Path.Combine(Root, "invented-binding.json");
        public string Scenario => Path.Combine(Root, "invented-scenario.json");
        public string Output => Path.Combine(Root, "new-report.json");
        public string Runner { get; }
        public string[] LookupArguments() => ["research", "p28-ignition", "lookup-check", Baseline, "--profile", "p28-304",
            "--confirm-profile", "--baseline-binding", Binding, "--runner", Runner, "--scenario", Scenario, "--output", Output];
        public Dictionary<string, byte[]> Snapshot() => new[] { Baseline, Binding, Scenario }.ToDictionary(path => path, File.ReadAllBytes);
        public void AssertUnchanged(Dictionary<string, byte[]> snapshot)
        { foreach (var pair in snapshot) Assert.Equal(pair.Value, File.ReadAllBytes(pair.Key)); }
        public async Task<(int Code, string Output, string Error)> RunAsync(string[] args, CancellationToken token = default)
        {
            using var output = new StringWriter(); using var error = new StringWriter();
            var code = await new CliApplication(output, error, Root, _definitions).RunAsync(args, token);
            return (code, output.ToString(), error.ToString());
        }
        public void Dispose() => Directory.Delete(Root, true);

        private static byte[] Image()
        {
            var bytes = new byte[32768];
            new byte[] { 0, 20, 40, 60, 80, 100, 120, 140, 240, 0 }.CopyTo(bytes, P28IgnitionMapContract.LoadAxisOrigin);
            Enumerable.Range(0, 19).Select(i => (byte)(i * 10)).Append((byte)0).ToArray().CopyTo(bytes, P28IgnitionMapContract.Map0RpmAxisOrigin);
            Enumerable.Range(0, 19).Select(i => (byte)(i * 10)).Append((byte)0).ToArray().CopyTo(bytes, P28IgnitionMapContract.Map1RpmAxisOrigin);
            foreach (var map in P28IgnitionMapContract.Maps)
                for (var index = 0; index < 200; index++) bytes[map.Origin + index] = (byte)(1 + index % 200);
            bytes[0x0A0C] = 0x60; bytes[0x0A0D] = 0x14; bytes[0x0A0E] = 0x70;
            bytes[0x0A24] = 0x60; bytes[0x0A25] = 0x28; bytes[0x0A26] = 0x70;
            bytes[0x0A50] = 0x60; bytes[0x0A51] = 0; bytes[0x0A52] = 0x70;
            bytes[0x0B67] = 0x98; bytes[0x0B68] = 10; bytes[0x0B69] = 0x99; bytes[0x0B6A] = 20;
            bytes[0x0B71] = 0xED; bytes[0x0B72] = 0x27;
            bytes[0x0B7A] = 0x60; bytes[0x0B7B] = 0xE4; bytes[0x0B7C] = 0x72;
            bytes[0x0B91] = 0x60; bytes[0x0B92] = 0xAC; bytes[0x0B93] = 0x73;
            bytes[0x0BAF] = 0xA3; bytes[0x0BB0] = 0x0D; bytes[0x0BB1] = 0x32; bytes[0x0BB2] = 0xE4; bytes[0x0BB3] = 0x59;
            bytes[0x0BD2] = 0xD4; bytes[0x0BD3] = 0x48;
            return bytes;
        }
    }
}
