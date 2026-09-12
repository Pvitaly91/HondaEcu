namespace HondaEcu.Cli.Tests;

public sealed class P28FuelMapExportCliTests
{
    private static string[] Arguments(P28AcquisitionCliTests.Workspace workspace, string operation)
    {
        workspace.WriteLineagePlaceholders();
        var settings = Path.Combine(workspace.Root, "fuel-settings.json");
        File.WriteAllText(settings, """{"formatVersion":1,"purpose":"explicit-fuel-map-cell-values","map_0":[{"row":0,"column":0,"rawValue":17}],"map_1":null}""");
        var common = new[] { "research", "p28-fuel", "export", operation, workspace.Baseline, "--profile", "p28-304",
            "--baseline-binding", workspace.Binding, "--compensation-definition", workspace.Definition, "--output", workspace.Output };
        return operation switch
        {
            "plan" => [.. common, "--confirm-profile", "--settings", settings],
            "apply" => [.. common, "--confirm-profile", "--confirm-pc-only", "--plan", workspace.Plan, "--runner", workspace.Runner,
                "--saved-plan", Path.Combine(workspace.Root, "new-fuel-plan.json"), "--report", Path.Combine(workspace.Root, "new-fuel-receipt.json")],
            _ => [.. common, "--baseline", workspace.Baseline, "--plan", workspace.Plan, "--report", workspace.Receipt]
        };
    }

    [Theory]
    [InlineData("plan", "--settings")]
    [InlineData("plan", "--profile")]
    [InlineData("plan", "--baseline-binding")]
    [InlineData("plan", "--compensation-definition")]
    [InlineData("apply", "--runner")]
    [InlineData("apply", "--saved-plan")]
    [InlineData("verify", "--baseline")]
    [InlineData("inspect", "--report")]
    public async Task EveryRouteRequiresItsClosedInputs(string operation, string missing)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace(); var arguments = Arguments(workspace, operation).ToList();
        arguments.RemoveRange(arguments.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(arguments.ToArray())).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("plan", "--confirm-profile")]
    [InlineData("apply", "--confirm-profile")]
    [InlineData("apply", "--confirm-pc-only")]
    public async Task ConfirmationsStayExplicit(string operation, string flag)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync(Arguments(workspace, operation).Where(value => value != flag).ToArray())).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("--offset")]
    [InlineData("--force")]
    [InlineData("--percent")]
    [InlineData("--clamp")]
    [InlineData("--allow-assumption")]
    [InlineData("--scenario")]
    public async Task NoArbitraryPatchOrValidationEscapeHatch(string option)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace();
        Assert.Equal(CliApplication.UsageError, (await workspace.RunAsync([.. Arguments(workspace, "apply"), option, "1"])).Code);
        Assert.False(File.Exists(workspace.Output));
    }

    [Theory]
    [InlineData("plan")]
    [InlineData("apply")]
    [InlineData("verify")]
    [InlineData("inspect")]
    public async Task ForgedAdmissionNeverPublishes(string operation)
    {
        using var workspace = new P28AcquisitionCliTests.Workspace(); var before = workspace.InputSnapshot();
        Assert.NotEqual(CliApplication.Success, (await workspace.RunAsync(Arguments(workspace, operation))).Code);
        workspace.AssertUnchanged(before); Assert.False(File.Exists(workspace.Output));
        Assert.False(File.Exists(Path.Combine(workspace.Root, "new-fuel-plan.json")));
        Assert.False(File.Exists(Path.Combine(workspace.Root, "new-fuel-receipt.json")));
    }

    [Fact]
    public async Task DestinationAliasingAndCancellationLeaveInputsIntact()
    {
        using var workspace = new P28AcquisitionCliTests.Workspace(); var arguments = Arguments(workspace, "plan");
        arguments[Array.IndexOf(arguments, "--output") + 1] = arguments[Array.IndexOf(arguments, "--settings") + 1];
        var settings = File.ReadAllText(arguments[Array.IndexOf(arguments, "--settings") + 1]);
        Assert.NotEqual(CliApplication.Success, (await workspace.RunAsync(arguments)).Code);
        Assert.Equal(settings, File.ReadAllText(arguments[Array.IndexOf(arguments, "--settings") + 1]));
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        Assert.NotEqual(CliApplication.Success, (await workspace.RunAsync(Arguments(workspace, "apply"), cancellation.Token)).Code);
        Assert.False(File.Exists(workspace.Output));
    }
}
