using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28PostStoreConsumerCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var b = File.ReadAllBytes(w.Baseline);
        // Invented partial adaptive producer, not an OEM routine fixture.
        new byte[] { 0x62, 129, 0, 0x67, 90, 0 }.CopyTo(b, 0x1966);
        new byte[] { 0x03, 0xE1, 0x48 }.CopyTo(b, 0x487B);
        new byte[] { 0x67, 88, 0, 0xD3, 0x24, 0x47, 0x81 }.CopyTo(b, 0x48E1);
        b[0x487E] = 0x64; b[0x4880] = 0x99; b[0x4881] = 0x64; b[0x4886] = 0x9F; b[0x4887] = 0x64; b[0x4889] = 0xA5; b[0x488A] = 0x64;
        File.WriteAllBytes(w.Baseline, b);
        var binding = P28ExactBaselineBinding.Parse(File.ReadAllText(w.Binding));
        File.WriteAllText(w.Binding, new P28ExactBaselineBinding(binding.FormatVersion, binding.ModelId, binding.ProfileId, binding.ExpectedSize, RomImage.Load(w.Baseline).Hash, binding.ProfileDigest).ToJson());
        var sources = new P28FuelFactorSources(12345, 65535, 255, 65535, 65535, 255, 255, 0, 0, 255, 107, 0, 0, 0, 0, 0, 0, 0, 0);
        var first = new P28AdaptiveFuelCall(new(0, 89, 0, 0, 0, sources), 1100, 0, false, false, true, true, true, false, 0, 0);
        var initial = new P28PostStoreInitial(new(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0xF1, 0xAD, 7, 16, 128, 0xA5), 100, 110, 0, 0, 0xA55A, 0x5AA5), 321);
        File.WriteAllText(w.Scenario, P28PostStoreConsumerScenario.Create(initial,
            [new(first, false, false), new(first with { Fuel = first.Fuel with { Index = 1 } }, false, false)],
            "Invented bounded M2q partial CLI fixture", [0]).ToJson());
        var args = w.LookupArguments(); args[2] = "post-store-consumer-check"; return args;
    }

    [Theory]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--baseline-binding")]
    [InlineData("--profile")]
    public async Task ClosedRequiredInputs(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var a = Arguments(w).ToList(); a.RemoveRange(a.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(a.ToArray())).Code); Assert.False(File.Exists(w.Output));
    }

    [Theory]
    [InlineData("--data0150")]
    [InlineData("--selected")]
    [InlineData("--helper-result")]
    [InlineData("--source-bit5")]
    [InlineData("--data012c")]
    [InlineData("--rom60f8")]
    [InlineData("--pc")]
    [InlineData("--allow-assumption")]
    [InlineData("--channel-mask")]
    [InlineData("--output-bin")]
    public async Task NoProducedValueSnapshotBranchOrExportOption(string option)
    {
        using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code);
        Assert.False(File.Exists(w.Output));
    }

    [Fact]
    public async Task RealPartialTaskRetainsPrefixAndNullConsumerWithLaterEventsNotRun()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot(); Assert.True(File.Exists(w.Runner));
        var r = await w.RunAsync(args); Assert.Equal(CliApplication.VerificationFailed, r.Code);
        var report = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.Equal("0.40.0", report["runnerVersion"]!.GetValue<string>());
        Assert.Equal("post-store-consumer-native-software-test", report["purpose"]!.GetValue<string>());
        foreach (var sequence in report["sequences"]!.AsArray())
        {
            var c = sequence!["checkpoints"]!;
            Assert.Equal("Unresolved", c[0]!["disposition"]!.GetValue<string>());
            Assert.Null(c[0]!["selectedScaledWordX1"]); Assert.Null(c[0]!["retainedOrZeroA"]); Assert.Null(c[0]!["expected"]);
            Assert.Null(c[0]!["actual"]!["consumer"]);
            Assert.Equal("NotRun", c[1]!["disposition"]!.GetValue<string>()); Assert.Null(c[1]!["actual"]!["consumer"]);
            Assert.Empty(c[1]!["actual"]!["prefix"]!["snapshotWrites"]!.AsArray());
        }
        Assert.Contains("helper=NotRun", r.Output); Assert.Contains("prefix=Unresolved", r.Output); Assert.Contains("StaticOnly/NotEvaluated", r.Output);
        w.AssertUnchanged(before);
    }

    [Fact]
    public async Task CancelAliasesMalformedAndWrongBindingNeverOverwriteAnInput()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot(); using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, cancellation.Token)).Code); Assert.False(File.Exists(w.Output));
        foreach (var path in before.Keys) { args[^1] = path; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); }
        args[^1] = w.Output; w.AssertUnchanged(before);
        var n = JsonNode.Parse(File.ReadAllText(w.Scenario))!; n["calls"]![0]!["data0150"] = 250;
        File.WriteAllText(w.Scenario, n.ToJsonString()); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code);
        File.WriteAllBytes(w.Scenario, before[w.Scenario]); var bytes = File.ReadAllBytes(w.Baseline); bytes[0] ^= 1; File.WriteAllBytes(w.Baseline, bytes);
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output));
    }

    [Fact]
    public async Task HistoricalTaskPurposeMissingConfirmationAndExistingDestinationAreRefused()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        var old = JsonNode.Parse(File.ReadAllText(w.Scenario))!; old["purpose"] = "post-store-fuel-native-software-test";
        File.WriteAllText(w.Scenario, old.ToJsonString()); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code);
        File.WriteAllBytes(w.Scenario, before[w.Scenario]);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.Where(a => a != "--confirm-profile").ToArray())).Code);
        File.WriteAllText(w.Output, "Existing report must remain untouched."); var output = File.ReadAllBytes(w.Output);
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.Equal(output, File.ReadAllBytes(w.Output)); w.AssertUnchanged(before);
    }
}
