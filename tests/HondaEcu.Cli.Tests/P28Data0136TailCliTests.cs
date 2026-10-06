using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28Data0136TailCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var args = P28Word0196AlternateCliTests.Arguments(w); var old = P28Word0196AlternateScenario.Parse(File.ReadAllText(w.Scenario));
        var selector = P28PostReturnSelectorScenario.Create(old.InitialState, 0, old.Calls.Select(c => new P28PostReturnSelectorCall(c.Prefix)).ToArray(), 0xA5, 0x8B, 15, old.Provenance, old.TraceEventIndexes);
        var caller = P28FallthroughData0136Scenario.Create(selector, selector.Calls.Select(_ => new P28FrozenNoWriteObservation(0x8123, null)).ToArray());
        File.WriteAllText(w.Scenario, P28Data0136TailScenario.Create(caller).ToJson()); args[2] = "data0136-tail-check"; return args;
    }
    [Theory]
    [InlineData("--tm3")]
    [InlineData("--tmr3")]
    [InlineData("--timer-ticks")]
    [InlineData("--tail-branch")]
    [InlineData("--jle-result")]
    [InlineData("--mul-result")]
    [InlineData("--data0136")]
    [InlineData("--pointer")]
    [InlineData("--pc5719")]
    [InlineData("--pc5782")]
    [InlineData("--pc5787")]
    [InlineData("--pc5793")]
    [InlineData("--ssp")]
    [InlineData("--return0667")]
    [InlineData("--output-bin")]
    [InlineData("--initial019b2")]
    public async Task NoTailRepairTimerOrOutputOptions(string option)
    { using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task ConfirmationAndNoOutputAliasRemainRequired()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.Where(s => s != "--confirm-profile").ToArray())).Code);
        var before = File.ReadAllBytes(w.Baseline); args[Array.IndexOf(args, "--output") + 1] = w.Baseline;
        Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); Assert.Equal(before, File.ReadAllBytes(w.Baseline));
    }
}
