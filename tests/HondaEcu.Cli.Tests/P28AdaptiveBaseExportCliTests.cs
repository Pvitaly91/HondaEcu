using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28AdaptiveBaseExportCliTests
{
    private static string[] Args(P28AcquisitionCliTests.Workspace w, string operation)
    {
        w.WriteLineagePlaceholders();
        var common = new[] { "research", "p28-limiter", "adaptive-export", operation, w.Baseline, "--profile", "p28-304", "--baseline-binding", w.Binding,
            "--compensation-definition", w.Definition, "--output", w.Output };
        return operation switch
        {
            "plan" => [.. common, "--confirm-profile", "--bank", "0", "--base-cut-raw", "257", "--base-resume-raw", "261"],
            "apply" => [.. common, "--confirm-profile", "--confirm-pc-only", "--plan", w.Plan, "--runner", w.Runner, "--saved-plan", Path.Combine(w.Root, "new-plan.json"), "--report", Path.Combine(w.Root, "new-receipt.json")],
            _ => [.. common, "--baseline", w.Baseline, "--plan", w.Plan, "--report", w.Receipt],
        };
    }
    [Theory]
    [InlineData("plan", "--bank")]
    [InlineData("plan", "--profile")]
    [InlineData("plan", "--baseline-binding")]
    [InlineData("plan", "--compensation-definition")]
    [InlineData("plan", "--base-cut-raw")]
    [InlineData("plan", "--base-resume-raw")]
    [InlineData("plan", "--output")]
    [InlineData("apply", "--runner")]
    [InlineData("apply", "--plan")]
    [InlineData("apply", "--saved-plan")]
    [InlineData("apply", "--report")]
    [InlineData("verify", "--baseline")]
    [InlineData("verify", "--report")]
    public async Task MissingRequiredOptionRefusedBeforePublication(string operation, string missing)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w, operation).ToList(); var i = args.IndexOf(missing); args.RemoveRange(i, 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("plan", "--confirm-profile")]
    [InlineData("apply", "--confirm-profile")]
    [InlineData("apply", "--confirm-pc-only")]
    public async Task ExplicitConfirmationsRequired(string operation, string flag)
    {
        using var w = new P28AcquisitionCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(Args(w, operation).Where(a => a != flag).ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("540.5")]
    [InlineData("540rpm")]
    [InlineData("0x21C")]
    [InlineData("+540")]
    [InlineData("-5")]
    [InlineData("99999999999999")]
    public async Task RawSyntaxIsIntegerOnly(string raw)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w, "plan"); args[Array.IndexOf(args, "--base-cut-raw") + 1] = raw;
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("--offset")]
    [InlineData("--force-offset")]
    [InlineData("--rpm")]
    [InlineData("--slot")]
    [InlineData("--scenario")]
    [InlineData("--allow-assumption")]
    public async Task NoArbitraryOffsetLegacySlotOrScenarioCanReplaceRequiredCorpus(string option)
    {
        using var w = new P28AcquisitionCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Args(w, "apply"), option, "1"])).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("plan")]
    [InlineData("apply")]
    [InlineData("verify")]
    [InlineData("inspect")]
    public async Task UnauthenticatedInputsRefuseEveryRouteAndRemainImmutable(string operation)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w, operation); var before = w.InputSnapshot();
        Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); w.AssertUnchanged(before); Assert.False(File.Exists(w.Output));
        Assert.False(File.Exists(Path.Combine(w.Root, "new-plan.json"))); Assert.False(File.Exists(Path.Combine(w.Root, "new-receipt.json")));
    }
    [Fact]
    public async Task ExistingDestinationAliasesAndCancellationCannotPublish()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w, "apply");
        args[Array.IndexOf(args, "--saved-plan") + 1] = w.Output;
        Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code);
        args = Args(w, "plan"); args[Array.IndexOf(args, "--output") + 1] = w.Baseline;
        var before = w.InputSnapshot(); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); w.AssertUnchanged(before);
        File.WriteAllText(w.Output, "preserved"); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w, "plan"))).Code); Assert.Equal("preserved", File.ReadAllText(w.Output));
        using var c = new CancellationTokenSource(); c.Cancel(); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w, "apply"), c.Token)).Code);
    }
}
