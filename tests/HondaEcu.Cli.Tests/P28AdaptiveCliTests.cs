using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28AdaptiveCliTests
{
    private static string[] Args(P28AcquisitionCliTests.Workspace w) => ["research", "p28-limiter", "adaptive-check", w.Baseline, "--profile", "p28-304", "--confirm-profile", "--baseline-binding", w.Binding, "--runner", w.Runner, "--scenario", w.Scenario, "--output", w.Output];
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
    [InlineData("--ram-cut")]
    [InlineData("--offset")]
    public async Task NoPermissionsOrPerCallInjectionOptions(string extra)
    { using var w = new P28AcquisitionCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Args(w), extra, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task InputAliasesExistingOutputAndMalformedScenarioAreRefused()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var snapshot = w.InputSnapshot();
        foreach (var path in new[] { w.Baseline, w.Binding, w.Runner, w.Scenario, w.Profile.SourcePath! }) { var args = Args(w); args[^1] = path; Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); }
        Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w))).Code); Assert.False(File.Exists(w.Output));
        File.WriteAllText(w.Output, "reserved"); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w))).Code); Assert.Equal("reserved", File.ReadAllText(w.Output)); w.AssertUnchanged(snapshot);
    }
    [Fact]
    public async Task CancellationDoesNotCreateReport()
    { using var w = new P28AcquisitionCliTests.Workspace(); using var c = new CancellationTokenSource(); c.Cancel(); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w), c.Token)).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task ActualRustCliE2ePublishesHonestStrictStopAndProtectsInputs()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var bytes = new byte[32768]; bytes[0x487B] = 0x45; bytes[0x487C] = 0x81;
        File.WriteAllBytes(w.Baseline, bytes);
        File.WriteAllText(w.Binding, new P28ExactBaselineBinding(1, P28CompactModel.ModelId, w.Profile.Id, 32768, RomImage.Load(w.Baseline).Hash, P28VtecInspector.ComputeProfileDigest(w.Profile)).ToJson());
        var initial = new P28AdaptiveState(new(0, 0, 0, 255, 7, 100, 110), 0, 0, 0, 0);
        var calls = Enumerable.Range(0, 2).Select(i => new P28AdaptiveCall(new(i, 101, false, false, 254), 1000, false, false, false, false, true, 0, 0, 0)).ToArray();
        File.WriteAllText(w.Scenario, P28AdaptiveScenario.Create(initial, calls, "Invented headless CLI E2E").ToJson());
        var runner = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(w.Profile.SourcePath)!, "../../rust/p28-slice-runner/target/release", OperatingSystem.IsWindows() ? "p28-slice-runner.exe" : "p28-slice-runner"));
        Assert.True(File.Exists(runner), "Pinned Rust runner is required, not an optional skipped test.");
        var args = Args(w); args[Array.IndexOf(args, "--runner") + 1] = runner;
        var snapshot = w.InputSnapshot(); var runnerBefore = File.ReadAllBytes(runner);
        var result = await w.RunAsync(args); Assert.Equal(CliApplication.VerificationFailed, result.Code);
        var r = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.True(r["hasFailure"]!.GetValue<bool>()); Assert.False(r["physicalRpmAvailable"]!.GetValue<bool>());
        foreach (var s in r["sequences"]!.AsArray()) { Assert.Equal(1, s!["counts"]!["unresolved"]!.GetValue<int>()); Assert.Equal(1, s["counts"]!["notRun"]!.GetValue<int>()); Assert.Null(s["checkpoints"]![1]!["overspeedRequest"]); }
        Assert.Equal(runnerBefore, File.ReadAllBytes(runner)); w.AssertUnchanged(snapshot);
    }
}
