using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28LimiterCliTests
{
    private static string[] Args(P28AcquisitionCliTests.Workspace w) => ["research", "p28-limiter", "check", w.Baseline, "--profile", "p28-304", "--confirm-profile", "--baseline-binding", w.Binding, "--runner", w.Runner, "--scenario", w.Scenario, "--output", w.Output];
    [Theory]
    [InlineData("--profile")]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    public async Task RequiredOptionsAndConfirmation(string missing)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w).ToList(); var ix = args.IndexOf(missing); args.RemoveRange(ix, 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(Args(w).Where(a => a != "--confirm-profile").ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("--allow-assumption")]
    [InlineData("--derived")]
    [InlineData("--enabled")]
    [InlineData("--offset")]
    public async Task NoPermissionsLineageOrArbitraryMutationOptions(string extra)
    { using var w = new P28AcquisitionCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Args(w), extra, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task InspectWithoutBindingIsGeneralAndNeverWritesInput()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var snapshot = w.InputSnapshot();
        var result = await w.RunAsync(["research", "p28-limiter", "inspect", w.Baseline, "--profile", "p28-304", "--confirm-profile", "--output", w.Output]);
        Assert.Equal(CliApplication.Success, result.Code); var report = JsonNode.Parse(File.ReadAllText(w.Output))!;
        Assert.False(report["interpretationApplied"]!.GetValue<bool>()); Assert.Empty(report["fields"]!.AsArray()); Assert.False(report["physicalRpmAvailable"]!.GetValue<bool>()); w.AssertUnchanged(snapshot);
    }
    [Fact]
    public async Task InputAliasesExistingOutputAndMalformedScenarioAreRefused()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var snapshot = w.InputSnapshot();
        foreach (var path in new[] { w.Baseline, w.Binding, w.Runner, w.Scenario }) { var args = Args(w); args[^1] = path; Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); }
        Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w))).Code); Assert.False(File.Exists(w.Output));
        File.WriteAllText(w.Output, "reserved"); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w))).Code); Assert.Equal("reserved", File.ReadAllText(w.Output)); w.AssertUnchanged(snapshot);
    }
    [Fact]
    public async Task CancellationDoesNotCreateReport()
    { using var w = new P28AcquisitionCliTests.Workspace(); using var c = new CancellationTokenSource(); c.Cancel(); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w), c.Token)).Code); Assert.False(File.Exists(w.Output)); }
}
