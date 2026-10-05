using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28FuelAdditiveCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        File.WriteAllText(w.Scenario, P28FuelAdditiveScenario.Create(new(new(0, 0, 0, 0, 0, 0, 0xA7, 0), 0xA5, 8),
            [new(0, 0, 0, 0, new(513, 0, 0, 65436, 0, 0, 0, 0, 4)), new(1, 255, 255, 255, new(65535, 0, 0, 0, 0, 0, 0, 0, 0))], "Invented CLI fixture; no OEM routine.", [0]).ToJson());
        var args = w.LookupArguments(); args[2] = "additive-chain-check"; return args;
    }
    [Theory]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--profile")]
    public async Task RequiresInputsAndConfirmation(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var complete = Arguments(w); var args = complete.ToList(); args.RemoveRange(args.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(complete.Where(v => v != "--confirm-profile").ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("--correction")]
    [InlineData("--x2")]
    [InlineData("--data0140")]
    [InlineData("--expected-result")]
    [InlineData("--allow-assumption")]
    [InlineData("--output-bin")]
    public async Task InjectionAndForeignOptionsRejected(string option)
    {
        using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code); Assert.False(File.Exists(w.Output));
    }
    [Fact]
    public async Task RealRunnerPartialPrefixRetainsCompletedEvidenceAndTerminalHistory()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot(); var result = await w.RunAsync(args);
        Assert.Equal(CliApplication.VerificationFailed, result.Code); var report = JsonNode.Parse(File.ReadAllText(w.Output))!;
        Assert.Equal("0.35.0", report["runnerVersion"]!.GetValue<string>()); Assert.Contains("Blocked", report["strictM2i"]!.GetValue<string>());
        foreach (var sequence in report["sequences"]!.AsArray())
        {
            var first = sequence!["checkpoints"]![0]!; var next = sequence["checkpoints"]![1]!;
            Assert.Equal("Unresolved", first["disposition"]!.GetValue<string>()); Assert.Empty(first["actual"]!["stages"]!.AsArray()); Assert.Null(first["corrected"]);
            Assert.Equal("NotRun", next["disposition"]!.GetValue<string>()); Assert.Null(next["actual"]!["input"]); Assert.Null(next["correction"]);
            Assert.Equal(513, next["actual"]!["sourcesAfter"]!["factor0158"]!.GetValue<int>()); Assert.Equal(8, next["actual"]!["modeAfter"]!.GetValue<int>());
            Assert.Equal(0xA7, next["actual"]!["prefix"]!["stateAfter"]!["selector0127"]!.GetValue<int>());
        }
        w.AssertUnchanged(before);
    }
    [Fact]
    public async Task CancellationAndDestinationAliasesDoNotWrite()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        using var c = new CancellationTokenSource(); c.Cancel(); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, c.Token)).Code); Assert.False(File.Exists(w.Output));
        foreach (var path in before.Keys) { args[^1] = path; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); }
        File.WriteAllText(w.Output, "preserve"); args[^1] = w.Output; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.Equal("preserve", File.ReadAllText(w.Output)); w.AssertUnchanged(before);
    }
}
