namespace HondaEcu.Cli.Tests;

public sealed class P28BasicCalibrationExportCliTests
{
    private static string[] Args(P28AcquisitionCliTests.Workspace w, string operation)
    {
        w.WriteLineagePlaceholders(); var settings = Path.Combine(w.Root, "basic-settings.json");
        File.WriteAllText(settings, """{"formatVersion":1,"purpose":"explicit-basic-calibration-selection","vtec":null,"fixed":null,"bank0":null,"bank1":null,"baseTable":[1,2,3,4,5,6,7],"lateTable":null}""");
        var common = new[] { "research", "p28-calibration", "export", operation, w.Baseline, "--profile", "p28-304", "--baseline-binding", w.Binding,
            "--compensation-definition", w.Definition, "--output", w.Output };
        return operation switch
        {
            "plan" => [.. common, "--confirm-profile", "--settings", settings],
            "apply" => [.. common, "--confirm-profile", "--confirm-pc-only", "--plan", w.Plan, "--runner", w.Runner, "--saved-plan", Path.Combine(w.Root, "new-plan.json"), "--report", Path.Combine(w.Root, "new-receipt.json")],
            _ => [.. common, "--baseline", w.Baseline, "--plan", w.Plan, "--report", w.Receipt]
        };
    }
    [Theory]
    [InlineData("plan", "--settings")]
    [InlineData("plan", "--profile")]
    [InlineData("plan", "--baseline-binding")]
    [InlineData("plan", "--compensation-definition")]
    [InlineData("plan", "--output")]
    [InlineData("apply", "--runner")]
    [InlineData("apply", "--plan")]
    [InlineData("apply", "--saved-plan")]
    [InlineData("apply", "--report")]
    [InlineData("verify", "--baseline")]
    [InlineData("verify", "--report")]
    [InlineData("inspect", "--plan")]
    public async Task RequiredInputs(string operation, string option)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w, operation).ToList(); args.RemoveRange(args.IndexOf(option), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("plan", "--confirm-profile")]
    [InlineData("apply", "--confirm-profile")]
    [InlineData("apply", "--confirm-pc-only")]
    public async Task ConfirmationsRequired(string operation, string flag)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync(Args(w, operation).Where(a => a != flag).ToArray())).Code);
    }
    [Theory]
    [InlineData("--offset")]
    [InlineData("--rpm")]
    [InlineData("--force")]
    [InlineData("--allow-assumption")]
    [InlineData("--scenario")]
    [InlineData("--slot")]
    [InlineData("--bank")]
    [InlineData("--cut-raw")]
    public async Task NoEscapeHatches(string option)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Args(w, "apply"), option, "1"])).Code);
    }
    [Theory]
    [InlineData("plan")]
    [InlineData("apply")]
    [InlineData("verify")]
    [InlineData("inspect")]
    public async Task ForeignAdmissionNeverPublishes(string operation)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w, operation); var before = w.InputSnapshot();
        Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); w.AssertUnchanged(before); Assert.False(File.Exists(w.Output));
        Assert.False(File.Exists(Path.Combine(w.Root, "new-plan.json"))); Assert.False(File.Exists(Path.Combine(w.Root, "new-receipt.json")));
    }
    [Fact]
    public async Task AliasExistingAndCancellationRefusals()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w, "apply"); args[Array.IndexOf(args, "--saved-plan") + 1] = w.Output;
        Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code);
        args = Args(w, "plan"); var settings = args[Array.IndexOf(args, "--settings") + 1]; var text = File.ReadAllText(settings);
        args[Array.IndexOf(args, "--output") + 1] = settings; Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); Assert.Equal(text, File.ReadAllText(settings));
        File.WriteAllText(w.Output, "preserve"); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w, "plan"))).Code); Assert.Equal("preserve", File.ReadAllText(w.Output));
        using var ct = new CancellationTokenSource(); ct.Cancel(); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w, "apply"), ct.Token)).Code);
    }
}
