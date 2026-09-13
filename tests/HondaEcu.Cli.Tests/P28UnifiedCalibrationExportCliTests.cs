namespace HondaEcu.Cli.Tests;

public sealed class P28UnifiedCalibrationExportCliTests
{
    private static string[] Args(P28AcquisitionCliTests.Workspace workspace, string operation)
    {
        workspace.WriteLineagePlaceholders();
        var settings = Path.Combine(workspace.Root, "unified-settings.json");
        File.WriteAllText(settings, """{"formatVersion":1,"purpose":"explicit-p28-calibration-set","basic":{"vtec":null,"fixed":null,"bank0":null,"bank1":null,"baseTable":[1,2,3,4,5,6,7],"lateTable":null},"fuel":{"map_0":[],"map_1":null},"ignition":{"ignition_map_0":null,"ignition_map_1":[]}}""");
        var common = new[] { "research", "p28-calibration", "combined-export", operation,
            workspace.Baseline, "--profile", "p28-304", "--baseline-binding", workspace.Binding,
            "--compensation-definition", workspace.Definition, "--output", workspace.Output };
        return operation switch
        {
            "plan" => [.. common, "--confirm-profile", "--settings", settings],
            "apply" => [.. common, "--confirm-profile", "--confirm-pc-only", "--plan", workspace.Plan,
                "--runner", workspace.Runner, "--saved-plan", Path.Combine(workspace.Root, "new-plan.json"),
                "--report", Path.Combine(workspace.Root, "new-receipt.json")],
            _ => [.. common, "--baseline", workspace.Baseline, "--plan", workspace.Plan,
                "--report", workspace.Receipt]
        };
    }

    [Theory]
    [InlineData("plan", "--settings")]
    [InlineData("plan", "--baseline-binding")]
    [InlineData("apply", "--runner")]
    [InlineData("apply", "--saved-plan")]
    [InlineData("apply", "--report")]
    [InlineData("verify", "--baseline")]
    [InlineData("verify", "--plan")]
    [InlineData("inspect", "--report")]
    public async Task RequiredInputs(string operation, string option)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        var args = Args(workspace, operation).ToList();
        args.RemoveRange(args.IndexOf(option), 2);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(args.ToArray())).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("plan", "--confirm-profile")]
    [InlineData("apply", "--confirm-profile")]
    [InlineData("apply", "--confirm-pc-only")]
    public async Task ExplicitConfirmationsAreRequired(string operation, string flag)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError,
            (await workspace.RunAsync(Args(workspace, operation).Where(value => value != flag).ToArray())).Code);
    }

    [Theory]
    [InlineData("--offset")]
    [InlineData("--force")]
    [InlineData("--scenario")]
    [InlineData("--allow-assumption")]
    [InlineData("--physical-rpm")]
    [InlineData("--factor")]
    public async Task NoEscapeHatches(string option)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError,
            (await workspace.RunAsync([.. Args(workspace, "apply"), option, "1"])).Code);
    }

    [Theory]
    [InlineData("plan")]
    [InlineData("apply")]
    [InlineData("verify")]
    [InlineData("inspect")]
    public async Task ForeignAdmissionNeverPublishes(string operation)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        var before = workspace.InputSnapshot();
        Assert.NotEqual(CliApplication.Success, (await workspace.RunAsync(Args(workspace, operation))).Code);
        workspace.AssertUnchanged(before);
        Assert.False(File.Exists(workspace.Output));
        Assert.False(File.Exists(Path.Combine(workspace.Root, "new-plan.json")));
        Assert.False(File.Exists(Path.Combine(workspace.Root, "new-receipt.json")));
    }

    [Fact]
    public async Task ExistingBasicCalibrationRouteRemainsDistinct()
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        var result = await workspace.RunAsync([
            "research", "p28-calibration", "combined-export", "unknown"
        ]);
        Assert.Equal(CliApplication.UsageError, result.Code);
        Assert.Contains("combined-export", result.Error);
        var basic = await workspace.RunAsync(["research", "p28-calibration", "unknown"]);
        Assert.Equal(CliApplication.UsageError, basic.Code);
        Assert.Contains("p28-calibration export", basic.Error);
    }
}
