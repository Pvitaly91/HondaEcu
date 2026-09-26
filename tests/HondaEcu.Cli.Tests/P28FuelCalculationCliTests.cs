using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28FuelCalculationCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        File.WriteAllText(w.Scenario, P28FuelCalculationScenario.Create(new(0, 0, 0, 0, 0, 0, 0xA7, 0),
            [new(0, 0, 0, 0, 513), new(1, 255, 255, 255, 65535)], "Invented CLI fixture; no OEM program.", [0]).ToJson());
        var args = w.LookupArguments(); args[2] = "calculation-chain-check"; return args;
    }

    [Theory]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--profile")]
    public async Task RequiresClosedInputsAndConfirmation(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var complete = Arguments(w);
        var args = complete.ToList(); args.RemoveRange(args.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(complete.Where(v => v != "--confirm-profile").ToArray())).Code);
        Assert.False(File.Exists(w.Output));
    }

    [Theory]
    [InlineData("--map-id")]
    [InlineData("--data0140")]
    [InlineData("--expected-product")]
    [InlineData("--allow-assumption")]
    [InlineData("--output-bin")]
    public async Task InjectionAndEditingOptionsAreRejected(string option)
    {
        using var w = new P28FuelMapCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code);
        Assert.False(File.Exists(w.Output));
    }

    [Fact]
    public async Task RequiredRealRunnerRetainsIncompletePrefixWithoutDownstreamOrSuffixInputs()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        Assert.True(File.Exists(w.Runner));
        var result = await w.RunAsync(args);
        Assert.Equal(CliApplication.VerificationFailed, result.Code);
        var report = JsonNode.Parse(File.ReadAllText(w.Output))!;
        Assert.Equal("Blocked; M2k does not resolve 47 81", report["strictM2i"]!.GetValue<string>());
        Assert.Equal(0, report["er2ReaderGate60f8"]!.GetValue<int>());
        Assert.Contains("bypasses", report["er2Reader227a"]!.GetValue<string>());
        Assert.Contains("21F2", report["softwareRole"]!.GetValue<string>());
        foreach (var sequence in report["sequences"]!.AsArray())
        {
            var first = sequence!["checkpoints"]![0]!; var next = sequence["checkpoints"]![1]!;
            Assert.Equal("Unresolved", first["disposition"]!.GetValue<string>());
            Assert.Null(first["output"]); Assert.Null(first["actual"]!["downstream"]);
            Assert.Equal("NotRun", next["disposition"]!.GetValue<string>());
            Assert.Null(next["output"]); Assert.Null(next["actual"]!["input"]);
            Assert.Equal(513, next["actual"]!["factor0158After"]!.GetValue<int>());
            Assert.Equal(0xA7, next["actual"]!["prefix"]!["stateAfter"]!["selector0127"]!.GetValue<int>());
        }
        var stop = report["sequences"]![0]!["checkpoints"]![0]!["actual"]!["prefix"]!["rpmAxes"]!["result"]!["stopPc"]!.GetValue<int>();
        Assert.Contains($"stop={stop:X4}", result.Output);
        w.AssertUnchanged(before);
    }

    [Fact]
    public async Task AlreadyCancelledDoesNotCreateReport()
    {
        using var w = new P28FuelMapCliTests.Workspace(); using var c = new CancellationTokenSource(); c.Cancel();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(Arguments(w), c.Token)).Code);
        Assert.False(File.Exists(w.Output));
    }

    [Fact]
    public async Task DestinationCannotAliasAnyInputOrOverwriteExistingReport()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        foreach (var path in before.Keys)
        {
            args[^1] = path;
            Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code);
        }
        File.WriteAllText(w.Output, "preserve me"); args[^1] = w.Output;
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code);
        Assert.Equal("preserve me", File.ReadAllText(w.Output)); w.AssertUnchanged(before);
    }
}
