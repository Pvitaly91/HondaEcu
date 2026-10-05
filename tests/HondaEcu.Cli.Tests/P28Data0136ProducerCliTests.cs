using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28Data0136ProducerCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        File.WriteAllText(w.Scenario, P28Data0136TechnicalProducerScenario.Create(new(7, 9, 0, 0, 8, 321, [1, 2, 3, 4, 5, 6]),
            [new(0, 10, 0, 0, 0), new(1, 20, 0, 0, 1)], "Invented unsupported entry fixture;no OEM program").ToJson());
        var args = w.LookupArguments(); args[2] = "data0136-producer-check"; return args;
    }
    [Theory]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--profile")]
    public async Task RequiresClosedInputsAndExplicitConfirmation(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var complete = Arguments(w); var args = complete.ToList(); args.RemoveRange(args.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(complete.Where(a => a != "--confirm-profile").ToArray())).Code);
        Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("--ready0136")]
    [InlineData("--quotient")]
    [InlineData("--writer-pc")]
    [InlineData("--flags")]
    [InlineData("--output-bin")]
    public async Task CannotInjectResultOrMutateFirmware(string option)
    {
        using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code); Assert.False(File.Exists(w.Output));
    }
    [Fact]
    public async Task ActualUnsupportedProgramReportsPartialThenNotRunAndPreservesEveryInput()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        Assert.Equal(CliApplication.VerificationFailed, (await w.RunAsync(args)).Code); w.AssertUnchanged(before);
        var report = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.Equal("0.37.0", report["runnerVersion"]!.GetValue<string>());
        foreach (var seq in report["sequences"]!.AsArray()) { Assert.Null(seq!["checkpoints"]![0]!["nativeWord0136"]); Assert.Equal("NotRun", seq["checkpoints"]![1]!["disposition"]!.GetValue<string>()); }
        Assert.Equal("NotEstablished", report["producerTo2330SchedulerSeam"]!.GetValue<string>());
    }
    [Fact]
    public async Task CannotOverwriteAnInputExistingOutputOrPublishAfterCancellation()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); args[^1] = w.Scenario;
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code);
        args = Arguments(w); File.WriteAllText(w.Output, "canary"); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.Equal("canary", File.ReadAllText(w.Output));
        using var cancel = new CancellationTokenSource(); cancel.Cancel(); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, cancel.Token)).Code); Assert.Equal("canary", File.ReadAllText(w.Output));
    }
}
