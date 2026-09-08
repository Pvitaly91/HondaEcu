using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28IdleContextsCliTests
{
    private static string[] Args(P28AcquisitionCliTests.Workspace w) => ["research", "p28-idle", "contexts-check", w.Baseline, "--profile", "p28-304", "--confirm-profile", "--baseline-binding", w.Binding, "--runner", w.Runner, "--scenario", w.Scenario, "--output", w.Output];
    [Theory]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--profile")]
    public async Task RequiredInputsAndExplicitConfirmation(string missing)
    { using var w = new P28AcquisitionCliTests.Workspace(); var args = Args(w).ToList(); var ix = args.IndexOf(missing); args.RemoveRange(ix, 2); Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code); Assert.Equal(CliApplication.UsageError, (await w.RunAsync(Args(w).Where(x => x != "--confirm-profile").ToArray())).Code); Assert.False(File.Exists(w.Output)); }
    [Theory]
    [InlineData("--set-idle-rpm")]
    [InlineData("--offset")]
    [InlineData("--derived")]
    [InlineData("--allow-assumption")]
    [InlineData("--expected-target")]
    public async Task EditingAndExpectedInjectionOptionsAreUnavailable(string extra)
    { using var w = new P28AcquisitionCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Args(w), extra, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task InputAliasesAndMalformedInputsNeverOverwritePriorReports()
    { using var w = new P28AcquisitionCliTests.Workspace(); var before = w.InputSnapshot(); foreach (var p in new[] { w.Baseline, w.Binding, w.Runner, w.Scenario, w.Profile.SourcePath! }) { var args = Args(w); args[^1] = p; Assert.NotEqual(CliApplication.Success, (await w.RunAsync(args)).Code); } Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w))).Code); Assert.False(File.Exists(w.Output)); File.WriteAllText(w.Output, "reserved"); Assert.NotEqual(CliApplication.Success, (await w.RunAsync(Args(w))).Code); Assert.Equal("reserved", File.ReadAllText(w.Output)); w.AssertUnchanged(before); }
    [Fact]
    public async Task UnknownImageInspectIsGeneralOnlyEvenWhenConfirmed()
    { using var w = new P28AcquisitionCliTests.Workspace(); var r = await w.RunAsync(["research", "p28-idle", "contexts-inspect", w.Baseline, "--profile", "p28-304", "--confirm-profile", "--output", w.Output]); Assert.Equal(CliApplication.Success, r.Code); var n = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.False(n["interpretationApplied"]!.GetValue<bool>()); Assert.Empty(n["cells"]!.AsArray()); }
    [Fact]
    public async Task ActualRustCliEndToEndWritesHonestUnresolvedAndNotRunWithoutBin()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var b = new byte[32768]; b[0x2FD1] = 0x45; b[0x2FD2] = 0x81; b[0x2FD5] = 0xCB; b[0x2FD6] = 0x68; b[0x3077] = 0xCB; b[0x3078] = 0x68; b[0x30A3] = 0xE0; b[0x30A4] = 0x68;
        int[] axis = [255, 200, 150, 100, 52, 20, 0]; for (var i = 0; i < 7; i++) { b[0x68CB + 3 * i] = (byte)axis[i]; b[0x68CC + 3 * i] = 123; b[0x68CD + 3 * i] = 1; b[0x68E0 + 3 * i] = (byte)axis[i]; b[0x68E1 + 3 * i] = 211; }
        File.WriteAllBytes(w.Baseline, b); File.WriteAllText(w.Binding, new P28ExactBaselineBinding(1, P28CompactModel.ModelId, w.Profile.Id, 32768, RomImage.Load(w.Baseline).Hash, P28VtecInspector.ComputeProfileDigest(w.Profile)).ToJson());
        File.WriteAllText(w.Scenario, P28IdleContextsScenario.Create(new(9, 8, 7, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), [new(0, 100, 300, null), new(1, 100, 300, null)], "Invented CLI native stop").ToJson());
        var runner = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(w.Profile.SourcePath)!, "../../rust/p28-slice-runner/target/release", OperatingSystem.IsWindows() ? "p28-slice-runner.exe" : "p28-slice-runner")); Assert.True(File.Exists(runner));
        var args = Args(w); args[Array.IndexOf(args, "--runner") + 1] = runner; var before = w.InputSnapshot(); var r = await w.RunAsync(args); Assert.Equal(CliApplication.VerificationFailed, r.Code);
        var n = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.True(n["hasFailure"]!.GetValue<bool>()); foreach (var s in n["images"]![0]!["sequences"]!.AsArray()) { Assert.Equal("Unresolved", s!["checkpoints"]![0]!["disposition"]!.GetValue<string>()); Assert.Equal("NotRun", s["checkpoints"]![1]!["disposition"]!.GetValue<string>()); Assert.Null(s["checkpoints"]![1]!["actualFinalTarget"]); }
        w.AssertUnchanged(before);
    }
}
