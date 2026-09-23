using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28VtecFuelCliTests
{
    private static string[] Arguments(P28AcquisitionCliTests.Workspace workspace)
    {
        var args = workspace.Arguments();
        args[1] = "p28-fuel";
        args[2] = "vtec-chain-check";
        return args;
    }

    private static void WriteScenario(P28AcquisitionCliTests.Workspace workspace)
    {
        var initial = new P28VtecPersistentState(0, 0x80, 0, 0, 0, 0, 0, 0);
        var decision = new P28VtecCall(0, 30, 0, true, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        var scenario = P28VtecFuelScenario.Create(initial, new(0, 0, 0, 0, 0, 0, 0, 0),
            [new(0, 30, 30, 30, decision)], "Invented CLI preflight test.");
        File.WriteAllText(workspace.Scenario, scenario.ToJson(false));
    }

    [Theory]
    [InlineData("--profile")]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    public async Task RequiresCompleteExplicitAdmission(string missing)
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
    public async Task RejectsUnconfirmedOrAuthorityExpandingOptions()
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        WriteScenario(workspace);
        var args = Arguments(workspace);
        var noConfirmation = await workspace.RunAsync(args.Where(a => a != "--confirm-profile").ToArray());
        Assert.Equal(CliApplication.UsageError, noConfirmation.Code);
        foreach (var option in new[] { "--map-id", "--selector0127", "--sfr-write", "--force" })
        {
            var result = await workspace.RunAsync([.. args, option, "1"]);
            Assert.Equal(CliApplication.UsageError, result.Code);
        }
        var permission = await workspace.RunAsync([.. args, "--allow-assumption", "oki.add-er3-a"]);
        Assert.Equal(CliApplication.UsageError, permission.Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("unknown")]
    [InlineData("host-selector")]
    [InlineData("bad-gate")]
    public async Task MalformedScenarioFailsBeforeRunnerAndPreservesInputs(string invalid)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        WriteScenario(workspace);
        var node = JsonNode.Parse(File.ReadAllText(workspace.Scenario))!;
        switch (invalid)
        {
            case "missing": node.AsObject().Remove("initialVtec"); break;
            case "unknown": node["arbitraryWrites"] = new JsonArray(); break;
            case "host-selector": node["calls"]![0]!["selector0127"] = 2; break;
            case "bad-gate": node["calls"]![0]!["decision"]!["snapshot011C"] = 32; break;
        }
        File.WriteAllText(workspace.Scenario, node.ToJsonString());
        var before = workspace.InputSnapshot();
        var result = await workspace.RunAsync(Arguments(workspace));
        Assert.Equal(CliApplication.OperationError, result.Code);
        Assert.NotEmpty(result.Error);
        workspace.AssertUnchanged(before);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task ExistingOrAliasedOutputAndCancellationNeverWriteInputs()
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        WriteScenario(workspace);
        var args = Arguments(workspace);
        var before = workspace.InputSnapshot();
        foreach (var target in new[] { workspace.Baseline, workspace.Binding, workspace.Runner, workspace.Scenario })
        {
            var copy = args.ToArray();
            copy[Array.IndexOf(copy, "--output") + 1] = target;
            Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(copy)).Code);
        }
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args, cancellation.Token)).Code);
        workspace.AssertUnchanged(before);
        Assert.False(File.Exists(workspace.Output));
    }
}
