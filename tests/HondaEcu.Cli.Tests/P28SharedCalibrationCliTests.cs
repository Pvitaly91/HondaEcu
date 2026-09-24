using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28SharedCalibrationCliTests
{
    private static string[] Arguments(P28AcquisitionCliTests.Workspace workspace)
    {
        var args = workspace.Arguments();
        args[1] = "p28-calibration";
        args[2] = "shared-chain-check";
        return args;
    }

    private static void WriteScenario(P28AcquisitionCliTests.Workspace workspace)
    {
        var initial = new P28SharedState(new(0, 0x80, 0, 0, 0, 0, 0, 68),
            new(0, 0, 0, 0, 0, 0, 0, 0), 0xA5, 0, 90, 0, 16, 0);
        var decision = new P28VtecCall(0, 30, 0, false, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        var scenario = P28SharedCalibrationScenario.Create(initial,
            [new(0, 0, 1, 2, 3, decision)], [0], "Invented CLI preflight scenario.");
        File.WriteAllText(workspace.Scenario, scenario.ToJson());
    }

    [Theory]
    [InlineData("--profile")]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    public async Task RequiresEveryExplicitAdmissionOption(string missing)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        WriteScenario(workspace);
        var args = Arguments(workspace);
        var index = Array.IndexOf(args, missing);
        var result = await workspace.RunAsync(args.Where((_, i) => i != index && i != index + 1).ToArray());
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.Contains(missing, result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task ForbidsSelectorInjectionForeignAssumptionsAndUnconfirmedProfile()
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        WriteScenario(workspace);
        var args = Arguments(workspace);
        Assert.Equal(CliApplication.UsageError,
            (await workspace.RunAsync(args.Where(x => x != "--confirm-profile").ToArray())).Code);
        foreach (var option in new[] { "--map-id", "--selector0227", "--prepared-rpm", "--force" })
            Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync([.. args, option, "1"])).Code);
        Assert.Equal(CliApplication.UsageError,
            (await workspace.RunAsync([.. args, "--allow-assumption", "oki.add-er3-a"])).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task MalformedScenarioAndOutputAliasesNeverPublish()
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        WriteScenario(workspace);
        var args = Arguments(workspace);
        var node = JsonNode.Parse(File.ReadAllText(workspace.Scenario))!;
        node["calls"]![0]!["selector0227"] = 0;
        File.WriteAllText(workspace.Scenario, node.ToJsonString());
        var before = workspace.InputSnapshot();
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args)).Code);
        workspace.AssertUnchanged(before);
        foreach (var target in new[] { workspace.Baseline, workspace.Binding, workspace.Runner, workspace.Scenario })
        {
            var alias = args.ToArray();
            alias[Array.IndexOf(alias, "--output") + 1] = target;
            Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(alias)).Code);
        }
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task AlreadyCancelledCliRequestDoesNotCreateReport()
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        WriteScenario(workspace);
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var before = workspace.InputSnapshot();
        Assert.Equal(CliApplication.OperationError,
            (await workspace.RunAsync(Arguments(workspace), cancellation.Token)).Code);
        workspace.AssertUnchanged(before);
        Assert.False(File.Exists(workspace.Output));
    }
}
