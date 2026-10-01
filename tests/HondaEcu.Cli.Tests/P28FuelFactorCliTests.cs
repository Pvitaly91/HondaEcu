using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28FuelFactorCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace workspace)
    {
        var first = new P28FuelFactorSources(12345, 54321, 127, 65535, 65535, 255, 254, 128, 129, 130, 105,
            0, 0, 65436, 0, 0, 0, 0, 4);
        var second = new P28FuelFactorSources(65535, 0, 255, 0, 0, 0, 0, 0, 0, 0, 106,
            65535, 255, 0, 255, 255, 65535, 65535, 0);
        File.WriteAllText(workspace.Scenario, P28FuelFactorScenario.Create(
            new(new(0, 0, 0, 0, 0, 0, 0xA7, 0), 0xA5, 8, 0xA0, 0xB1, 0xD3),
            [new(0, 0, 0, 0, first), new(1, 255, 255, 255, second)],
            "Invented CLI fixture; no OEM producer or helper bytes.", [0]).ToJson());
        var args = workspace.LookupArguments(); args[2] = "factor-chain-check"; return args;
    }

    [Theory]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--profile")]
    public async Task RequiresClosedInputsAndConfirmation(string missing)
    {
        using var workspace = new P28FuelMapCliTests.Workspace(); var complete = Arguments(workspace);
        var args = complete.ToList(); args.RemoveRange(args.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(args.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(complete.Where(value => value != "--confirm-profile").ToArray())).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("--factor0158")]
    [InlineData("--factor")]
    [InlineData("--data0140")]
    [InlineData("--correction")]
    [InlineData("--expected-result")]
    [InlineData("--pc")]
    [InlineData("--ram")]
    [InlineData("--allow-assumption")]
    [InlineData("--output-bin")]
    public async Task SuppliedResultsScriptsAndForeignOptionsRejected(string option)
    {
        using var workspace = new P28FuelMapCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync([.. Arguments(workspace), option, "1"])).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("sources", "factor0158")]
    [InlineData("sources", "data0140")]
    [InlineData("sources", "scaled")]
    [InlineData("sources", "finalResult")]
    [InlineData("call", "mapId")]
    [InlineData("call", "ram")]
    [InlineData("initial", "factor0158")]
    [InlineData("initial", "pc")]
    [InlineData("fuel", "data0140")]
    public async Task ScenarioCannotHideReadyFactorOrOtherInjectedState(string location, string name)
    {
        using var workspace = new P28FuelMapCliTests.Workspace(); var args = Arguments(workspace);
        var scenario = JsonNode.Parse(File.ReadAllText(workspace.Scenario))!;
        var target = location switch
        {
            "sources" => scenario["calls"]![0]!["sources"]!,
            "call" => scenario["calls"]![0]!,
            "initial" => scenario["initialState"]!,
            _ => scenario["initialState"]!["fuel"]!
        };
        target[name] = 512; File.WriteAllText(workspace.Scenario, scenario.ToJsonString());
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args)).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task VersionPurposeAndOversizedScenarioAreRejectedBeforeExecution()
    {
        using var workspace = new P28FuelMapCliTests.Workspace(); var args = Arguments(workspace);
        var text = File.ReadAllText(workspace.Scenario); var scenario = JsonNode.Parse(text)!;
        scenario["formatVersion"] = 2; File.WriteAllText(workspace.Scenario, scenario.ToJsonString());
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args)).Code);
        scenario = JsonNode.Parse(text)!; scenario["purpose"] = "fuel-additive-native-software-test";
        File.WriteAllText(workspace.Scenario, scenario.ToJsonString());
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args)).Code);
        File.WriteAllText(workspace.Scenario, text + new string(' ', 262_145));
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args)).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Fact]
    public async Task RealRunnerPartialPrefixRetainsSourcesWithoutProducingOrConsumingFactor()
    {
        using var workspace = new P28FuelMapCliTests.Workspace(); var args = Arguments(workspace);
        Assert.True(File.Exists(workspace.Runner), "Pinned release runner with M2m operation is required; this test never silently skips.");
        var before = workspace.Snapshot(); var result = await workspace.RunAsync(args);
        Assert.Equal(CliApplication.VerificationFailed, result.Code);
        var report = JsonNode.Parse(File.ReadAllText(workspace.Output))!;
        Assert.Equal("0.27.0", report["runnerVersion"]!.GetValue<string>());
        Assert.Contains("Blocked", report["strictM2i"]!.GetValue<string>());
        foreach (var sequence in report["sequences"]!.AsArray())
        {
            var first = sequence!["checkpoints"]![0]!; var next = sequence["checkpoints"]![1]!;
            Assert.Equal("Unresolved", first["disposition"]!.GetValue<string>());
            Assert.Null(first["actual"]!["factorStage"]);
            Assert.Empty(first["actual"]!["stages"]!.AsArray());
            Assert.Null(first["nativeFactor0158"]); Assert.Null(first["component"]); Assert.Null(first["corrected"]);
            Assert.Equal("NotRun", first["factorProvenance"]!.GetValue<string>());
            Assert.Equal("NotRun", next["disposition"]!.GetValue<string>());
            Assert.Null(next["actual"]!["input"]); Assert.Null(next["nativeFactor0158"]); Assert.Null(next["correction"]);
            Assert.Equal("NotRun", next["factorProvenance"]!.GetValue<string>());
            Assert.Equal(12345, next["actual"]!["sourcesAfter"]!["source015a"]!.GetValue<int>());
            Assert.Equal(0xA7, next["actual"]!["prefix"]!["stateAfter"]!["selector0127"]!.GetValue<int>());
            Assert.Equal(first["factor0158After"]!.GetValue<int>(), next["factor0158After"]!.GetValue<int>());
        }
        Assert.Contains("native0158=NotRun", result.Output);
        Assert.Contains("provenance=NotRun", result.Output);
        Assert.Contains("factor-native-stop=NotRun", result.Output);
        Assert.Contains("\"source015a\":12345", result.Output);
        Assert.DoesNotContain("\"source015a\":65535", result.Output);
        workspace.AssertUnchanged(before);
    }

    [Fact]
    public async Task AlreadyCancelledAndDestinationAliasesLeaveInputsUntouched()
    {
        using var workspace = new P28FuelMapCliTests.Workspace(); var args = Arguments(workspace); var before = workspace.Snapshot();
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args, cancellation.Token)).Code);
        Assert.False(File.Exists(workspace.Output));
        foreach (var path in before.Keys)
        {
            args[^1] = path;
            Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args)).Code);
        }
        File.WriteAllText(workspace.Output, "preserve-existing-report"); args[^1] = workspace.Output;
        Assert.Equal(CliApplication.OperationError, (await workspace.RunAsync(args)).Code);
        Assert.Equal("preserve-existing-report", File.ReadAllText(workspace.Output)); workspace.AssertUnchanged(before);
    }
}
