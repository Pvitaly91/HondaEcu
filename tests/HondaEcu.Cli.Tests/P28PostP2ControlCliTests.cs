using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28PostP2ControlCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var args = P28Word0196AlternateCliTests.Arguments(w); var old = P28Word0196AlternateScenario.Parse(File.ReadAllText(w.Scenario));
        File.WriteAllText(w.Scenario, P28PostP2ControlScenario.Create(P28P2LatchScenario.Create(old, 0xA5), 0x8B, 15).ToJson()); args[2] = "post-p2-control-check"; return args;
    }
    [Theory]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--baseline-binding")]
    [InlineData("--profile")]
    public async Task RequiredClosedInputsAndConfirmation(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var complete = Arguments(w); var a = complete.ToList(); a.RemoveRange(a.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(a.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(complete.Where(a => a != "--confirm-profile").ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("--p2-pins")]
    [InlineData("--p2-io")]
    [InlineData("--timer")]
    [InlineData("--elapsed-time")]
    [InlineData("--tm0")]
    [InlineData("--tmr0")]
    [InlineData("--irq")]
    [InlineData("--control-result")]
    [InlineData("--output-mask")]
    [InlineData("--physical-polarity")]
    [InlineData("--injector")]
    [InlineData("--pc5599")]
    [InlineData("--pc55c8")]
    [InlineData("--word0196")]
    [InlineData("--branch-result")]
    [InlineData("--irq-frame")]
    [InlineData("--output-bin")]
    [InlineData("--allow-assumption")]
    public async Task NoReadyOutputModeShortcutOrExportOptions(string option)
    { using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task PartialInventedUpstreamDoesNotAccessOrReseedP2AndLaterIsNotRun()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var snapshot = w.Snapshot(); var r = await w.RunAsync(args);
        Assert.True(r.Code == CliApplication.VerificationFailed, r.Output + r.Error); w.AssertUnchanged(snapshot);
        var n = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.Equal("0.43.0", n["runnerVersion"]!.GetValue<string>());
        Assert.Equal("Partial", n["postP2ControlRegisterHandoff"]!.GetValue<string>()); Assert.Equal("NotModeled", n["p2ElectricalPins"]!.GetValue<string>());
        foreach (var s in n["sequences"]!.AsArray()) { Assert.Equal("NoFresh0196", s!["checkpoints"]![0]!["disposition"]!.GetValue<string>()); Assert.Equal("NotRun", s["checkpoints"]![1]!["disposition"]!.GetValue<string>()); foreach (var c in s["checkpoints"]!.AsArray()) { Assert.Equal(139, c!["tcon0Before"]!.GetValue<int>()); Assert.Equal(139, c["tcon0After"]!.GetValue<int>()); Assert.Equal(15, c["trnsitFlagsBefore"]!.GetValue<int>()); Assert.Equal(15, c["trnsitFlagsAfter"]!.GetValue<int>()); Assert.Null(c["tcon0Generation"]); Assert.Null(c["trnsitGeneration"]); } }
    }
    [Fact]
    public async Task AliasesCancellationSchemaAndExistingReportPreserveInputs()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var snapshot = w.Snapshot(); foreach (var path in snapshot.Keys) { args[^1] = path; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); }
        w.AssertUnchanged(snapshot); args[^1] = w.Output; using var cancel = new CancellationTokenSource(); cancel.Cancel();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, cancel.Token)).Code); Assert.False(File.Exists(w.Output));
        var n = JsonNode.Parse(File.ReadAllText(w.Scenario))!; n["calls"]![0]!["p2OutputLatch"] = 0; File.WriteAllText(w.Scenario, n.ToJsonString());
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output));
        File.WriteAllText(w.Output, "canary"); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(Arguments(w))).Code); Assert.Equal("canary", File.ReadAllText(w.Output));
    }
}
