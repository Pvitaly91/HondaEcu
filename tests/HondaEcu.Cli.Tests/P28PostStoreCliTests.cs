using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28PostStoreCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var b = File.ReadAllBytes(w.Baseline);
        new byte[] { 0x62, 129, 0, 0x67, 90, 0 }.CopyTo(b, 0x1966);
        new byte[] { 0x03, 0xE1, 0x48 }.CopyTo(b, 0x487B);
        new byte[] { 0x67, 88, 0, 0xD3, 0x24, 0x47, 0x81 }.CopyTo(b, 0x48E1);
        b[0x487E] = 0x64; b[0x4880] = 0x99; b[0x4881] = 0x64; b[0x4886] = 0x9F; b[0x4887] = 0x64; b[0x4889] = 0xA5; b[0x488A] = 0x64;
        File.WriteAllBytes(w.Baseline, b);
        var binding = P28ExactBaselineBinding.Parse(File.ReadAllText(w.Binding));
        File.WriteAllText(w.Binding, new P28ExactBaselineBinding(binding.FormatVersion, binding.ModelId, binding.ProfileId, binding.ExpectedSize, RomImage.Load(w.Baseline).Hash, binding.ProfileDigest).ToJson());
        var src = new P28FuelFactorSources(12345, 65535, 255, 65535, 65535, 255, 255, 0, 0, 255, 107, 0, 0, 0, 0, 0, 0, 0, 0);
        var first = new P28AdaptiveFuelCall(new(0, 89, 0, 0, 0, src), 1100, 0, false, false, true, true, true, false, 0, 0);
        File.WriteAllText(w.Scenario, P28AdaptiveFuelScenario.Create(new(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0xF1, 0xAD, 7, 16, 128, 0xA5), 100, 110, 0, 0, 0xA55A, 0x5AA5),
            [first, first with { Fuel = first.Fuel with { Index = 1 } }], "Invented partial CLI fixture; no OEM routine", [0]).ToJson());
        var old = P28AdaptiveFuelScenario.Parse(File.ReadAllText(w.Scenario));
        File.WriteAllText(w.Scenario, P28PostStoreScenario.Create(new(old.InitialState, 321), old.Calls.Select(c => new P28PostStoreCall(c, false, false)).ToArray(), "Invented M2p partial CLI fixture", [0]).ToJson());
        var args = w.LookupArguments(); args[2] = "post-store-chain-check"; return args;
    }
    [Theory]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--baseline-binding")]
    [InlineData("--profile")]
    public async Task ClosedRequiredInputs(string missing)
    { using var w = new P28FuelMapCliTests.Workspace(); var a = Arguments(w).ToList(); a.RemoveRange(a.IndexOf(missing), 2); Assert.Equal(CliApplication.UsageError, (await w.RunAsync(a.ToArray())).Code); Assert.False(File.Exists(w.Output)); }
    [Theory]
    [InlineData("--request")]
    [InlineData("--caller-gate0124")]
    [InlineData("--factor0158")]
    [InlineData("--channel-mask")]
    [InlineData("--ram-cut")]
    [InlineData("--offset")]
    [InlineData("--allow-assumption")]
    [InlineData("--output-bin")]
    public async Task NoInjectedResultOrExportOption(string option)
    { using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task ActualPartialNativeDecisionReportsNullFuelAndTerminalSuffixWithoutChangingInputs()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot(); Assert.True(File.Exists(w.Runner)); var r = await w.RunAsync(args);
        Assert.Equal(CliApplication.VerificationFailed, r.Code); var report = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.Equal("0.28.0", report["runnerVersion"]!.GetValue<string>());
        foreach (var sequence in report["sequences"]!.AsArray())
        { var c = sequence!["checkpoints"]!; Assert.Equal("Unresolved", c[0]!["disposition"]!.GetValue<string>()); Assert.Null(c[0]!["result0150"]); Assert.Null(c[0]!["expected"]); Assert.Equal("NotRun", c[1]!["disposition"]!.GetValue<string>()); Assert.Null(c[1]!["actual"]!["suffix"]); Assert.Empty(c[1]!["actual"]!["snapshotWrites"]!.AsArray()); }
        Assert.Contains("reason=NotRun", r.Output); Assert.Contains("prefix=Unresolved", r.Output); w.AssertUnchanged(before);
    }
    [Fact]
    public async Task CancelAliasMalformedAndWrongBindingDoNotWriteReport()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot(); using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, cancellation.Token)).Code); Assert.False(File.Exists(w.Output));
        foreach (var path in before.Keys) { args[^1] = path; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); }
        args[^1] = w.Output; w.AssertUnchanged(before);
        var n = JsonNode.Parse(File.ReadAllText(w.Scenario))!; n["calls"]![0]!["callerGate0124"] = 0; File.WriteAllText(w.Scenario, n.ToJsonString()); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code);
        File.WriteAllBytes(w.Scenario, before[w.Scenario]); var bytes = File.ReadAllBytes(w.Baseline); bytes[0] ^= 1; File.WriteAllBytes(w.Baseline, bytes); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output));
    }
}
