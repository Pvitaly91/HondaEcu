using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28LimiterFuelCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var b = File.ReadAllBytes(w.Baseline); new byte[] { 0x62, 129, 0, 0x67, 90, 0, 0x47, 0x81 }.CopyTo(b, 0x1966); File.WriteAllBytes(w.Baseline, b);
        var binding = P28ExactBaselineBinding.Parse(File.ReadAllText(w.Binding)); File.WriteAllText(w.Binding, new P28ExactBaselineBinding(binding.FormatVersion, binding.ModelId, binding.ProfileId, binding.ExpectedSize, RomImage.Load(w.Baseline).Hash, binding.ProfileDigest).ToJson());
        var src = new P28FuelFactorSources(12345, 65535, 255, 65535, 65535, 255, 255, 0, 0, 255, 107, 0, 0, 0, 0, 0, 0, 0, 0);
        File.WriteAllText(w.Scenario, P28LimiterFuelScenario.Create(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0xF1, 0xAD, 7, 16, 128, 0xA5),
            [new(0, 89, 0, 0, 0, src), new(1, 129, 255, 255, 255, src with { Source015a = 0 })], "Invented partial CLI fixture; no OEM routine bytes", [0]).ToJson());
        var args = w.LookupArguments(); args[2] = "limiter-chain-check"; return args;
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
        Assert.Equal(CliApplication.VerificationFailed, r.Code); var report = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.Equal("0.26.0", report["runnerVersion"]!.GetValue<string>());
        foreach (var sequence in report["sequences"]!.AsArray())
        { var c = sequence!["checkpoints"]!; Assert.Equal("Unresolved", c[0]!["disposition"]!.GetValue<string>()); Assert.Null(c[0]!["request"]); Assert.Null(c[0]!["fuel"]); Assert.Equal("NotRun", c[1]!["disposition"]!.GetValue<string>()); Assert.Null(c[1]!["actual"]!["input"]); Assert.Empty(c[1]!["actual"]!["inputWrites"]!.AsArray()); }
        Assert.Contains("request=NotRun", r.Output); w.AssertUnchanged(before);
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
