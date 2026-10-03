using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28DivisionDecisionCliTests
{
    private static void AssertInputsUnchanged(Dictionary<string, byte[]> before)
    {
        foreach (var pair in before)
            Assert.True(pair.Value.AsSpan().SequenceEqual(File.ReadAllBytes(pair.Key)), $"Input bytes changed: {Path.GetFileName(pair.Key)}.");
    }

    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var bytes = File.ReadAllBytes(w.Baseline);
        // Invented early partial producer, not an OEM routine or consumer fixture.
        new byte[] { 0x62, 129, 0, 0x67, 90, 0 }.CopyTo(bytes, 0x1966);
        new byte[] { 0x03, 0xE1, 0x48 }.CopyTo(bytes, 0x487B);
        new byte[] { 0x67, 88, 0, 0xD3, 0x24, 0x47, 0x81 }.CopyTo(bytes, 0x48E1);
        bytes[0x487E] = 0x64; bytes[0x4880] = 0x99; bytes[0x4881] = 0x64; bytes[0x4886] = 0x9F; bytes[0x4887] = 0x64; bytes[0x4889] = 0xA5; bytes[0x488A] = 0x64;
        File.WriteAllBytes(w.Baseline, bytes);
        var binding = P28ExactBaselineBinding.Parse(File.ReadAllText(w.Binding));
        File.WriteAllText(w.Binding, new P28ExactBaselineBinding(binding.FormatVersion, binding.ModelId, binding.ProfileId, binding.ExpectedSize,
            RomImage.Load(w.Baseline).Hash, binding.ProfileDigest).ToJson());
        var sources = new P28FuelFactorSources(12345, 65535, 255, 65535, 65535, 255, 255, 0, 0, 255, 107, 0, 0, 0, 0, 0, 0, 0, 0);
        var first = new P28AdaptiveFuelCall(new(0, 89, 0, 0, 0, sources), 1100, 0, false, false, true, true, true, false, 0, 0);
        var prefix = new P28PostStoreInitial(new(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0xF1, 0xAD, 7, 16, 128, 0xA5), 100, 110, 0, 0, 0xA55A, 0x5AA5), 321);
        var initial = new P28CommonResultConsumerInitial(prefix, new(0, false, false, 0, false, 1, 0, 0));
        File.WriteAllText(w.Scenario, P28DivisionDecisionScenario.Create(initial,
            [new(first, false, false), new(first with { Fuel = first.Fuel with { Index = 1 } }, false, false)],
            "Invented M2t partial CLI fixture; no recovered scheduler or quartet consumer", [0]).ToJson());
        var args = w.LookupArguments(); args[2] = "division-decision-check"; return args;
    }

    [Theory]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--baseline-binding")]
    [InlineData("--profile")]
    public async Task ClosedRequiredInputs(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w).ToList(); args.RemoveRange(args.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code); Assert.False(File.Exists(w.Output));
    }

    [Theory]
    [InlineData("--word03b6")]
    [InlineData("--word03b8")]
    [InlineData("--word03ba")]
    [InlineData("--word03bc")]
    [InlineData("--word0190")]
    [InlineData("--word0192")]
    [InlineData("--word0194")]
    [InlineData("--word0150")]
    [InlineData("--word03b4")]
    [InlineData("--x1")]
    [InlineData("--accumulator")]
    [InlineData("--loop-index")]
    [InlineData("--consumer-result")]
    [InlineData("--p2")]
    [InlineData("--pc")]
    [InlineData("--ram")]
    [InlineData("--formula")]
    [InlineData("--branch")]
    [InlineData("--scheduler-jump")]
    [InlineData("--allow-assumption")]
    [InlineData("--output-bin")]
    [InlineData("--timeout")]
    public async Task NoProducedValueIndexSchedulerInterruptOrExportOption(string option)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. args, option, "1"])).Code);
        Assert.False(File.Exists(w.Output)); AssertInputsUnchanged(before);
    }

    [Fact]
    public async Task RealNewTaskPublishesOnlyObservedPartialAndTerminalNotRunRows()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot(); Assert.True(File.Exists(w.Runner));
        var result = await w.RunAsync(args); Assert.True(result.Code == CliApplication.VerificationFailed, result.Error + result.Output);
        var report = JsonNode.Parse(File.ReadAllText(w.Output))!;
        Assert.Equal("0.30.0", report["runnerVersion"]!.GetValue<string>());
        Assert.Equal("division-decision-native-software-test", report["purpose"]!.GetValue<string>());
        foreach (var sequence in report["sequences"]!.AsArray())
        {
            var rows = sequence!["checkpoints"]!;
            Assert.Equal("PrefixUnresolved", rows[0]!["disposition"]!.GetValue<string>());
            Assert.Null(rows[0]!["native"]!["softwareResult13b"]); Assert.Null(rows[0]!["native"]!["actual"]!["commonConsumer"]);
            Assert.Equal("NotRun", rows[1]!["disposition"]!.GetValue<string>());
            Assert.Null(rows[1]!["native"]!["softwareResult13b"]); Assert.Null(rows[1]!["native"]!["actual"]!["commonConsumer"]);
            Assert.Empty(rows[1]!["native"]!["actual"]!["prefix"]!["prefix"]!["prefix"]!["prefix"]!["snapshotWrites"]!.AsArray());
        }
        Assert.Contains("prefix=Unresolved", result.Output); Assert.Contains("JGT Blocked/Partial before233A", result.Output);
        Assert.Contains("quartet reader invocations0", result.Output); Assert.Contains("ScriptedConsumerEntry NotEstablished/NotRun", result.Output);
        Assert.Contains("IRQ NotInjected", result.Output); Assert.Contains("elapsed time None", result.Output);
        Assert.Contains("overall consumer chain Partial", result.Output); Assert.Contains("new firmware BIN0", result.Output);
        AssertInputsUnchanged(before);
    }

    [Fact]
    public async Task AlreadyCancelledInputAliasesAndWrongBindingNeverPublishOrOverwrite()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, cancellation.Token)).Code); Assert.False(File.Exists(w.Output));
        foreach (var path in before.Keys) { args[^1] = path; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); }
        args[^1] = w.Output; AssertInputsUnchanged(before);
        var bytes = File.ReadAllBytes(w.Baseline); bytes[0] ^= 1; File.WriteAllBytes(w.Baseline, bytes);
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output));
        Assert.Equal(before[w.Binding], File.ReadAllBytes(w.Binding)); Assert.Equal(before[w.Scenario], File.ReadAllBytes(w.Scenario)); Assert.Equal(before[w.Runner], File.ReadAllBytes(w.Runner));
    }

    [Theory]
    [InlineData("word03b6")]
    [InlineData("word03b8")]
    [InlineData("word03ba")]
    [InlineData("word03bc")]
    [InlineData("word0190")]
    [InlineData("word0150")]
    [InlineData("word03b4")]
    [InlineData("loopIndex")]
    [InlineData("consumerResult")]
    [InlineData("p2Value")]
    [InlineData("pc")]
    [InlineData("softwareSources")]
    public async Task PerEventResultOrConsumerSourceInjectionIsRejected(string field)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var node = JsonNode.Parse(File.ReadAllText(w.Scenario))!;
        node["calls"]![0]![field] = 1; File.WriteAllText(w.Scenario, node.ToJsonString()); var before = w.Snapshot();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output)); AssertInputsUnchanged(before);
    }

    [Theory]
    [InlineData("historical-purpose")]
    [InlineData("version")]
    [InlineData("mask-overlap")]
    [InlineData("too-many-ticks")]
    [InlineData("non-dense-index")]
    [InlineData("duplicate-trace")]
    [InlineData("combined-mutation")]
    public async Task ClosedSchemaVersionBoundsAndSingleMutationAreEnforced(string fault)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var node = JsonNode.Parse(File.ReadAllText(w.Scenario))!;
        switch (fault)
        {
            case "historical-purpose": node["purpose"] = "post-selection-critical-native-software-test"; break;
            case "version": node["formatVersion"] = 2; break;
            case "mask-overlap": node["initialState"]!["softwareSources"]!["word011aMask1034"] = 0x8000; break;
            case "too-many-ticks": node["calls"]![0]!["adaptive"]!["timerTicks"] = 33; break;
            case "non-dense-index": node["calls"]![1]!["adaptive"]!["fuel"]!["index"] = 0; break;
            case "duplicate-trace": node["traceCallIndexes"] = new JsonArray(0, 0); break;
            case "combined-mutation": node["mutation"] = new JsonArray(new JsonObject { ["kind"] = "FuelCell" }, new JsonObject { ["kind"] = "Bank0Cut" }); break;
        }
        File.WriteAllText(w.Scenario, node.ToJsonString()); var before = w.Snapshot();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output)); AssertInputsUnchanged(before);
    }

    [Fact]
    public async Task ConfirmationExistingDestinationAndOversizedInputAreRefused()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.Where(arg => arg != "--confirm-profile").ToArray())).Code);
        File.WriteAllText(w.Output, "Existing report must remain untouched."); var output = File.ReadAllBytes(w.Output);
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.Equal(output, File.ReadAllBytes(w.Output)); AssertInputsUnchanged(before);
        var next = Path.Combine(w.Root, "another-new-report.json"); args[^1] = next;
        File.WriteAllText(w.Scenario, new string(' ', 262_145));
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(next)); Assert.Equal(output, File.ReadAllBytes(w.Output));
    }

    [Fact]
    public async Task HelpPreservesHistoricalAndNewTaskIdentitiesAndTheirDifferentScope()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var result = await w.RunAsync(["help"]);
        Assert.Equal(CliApplication.Success, result.Code); Assert.Contains("post-store-consumer-check", result.Output);
        Assert.Contains("runner-0.25.0", result.Output); Assert.Contains("post-selection-critical-check", result.Output);
        Assert.Contains("runner-0.26.0", result.Output); Assert.Contains("division-decision-check", result.Output);
        Assert.Contains("runner-0.28.0", result.Output); Assert.Contains("quartet consumers static/NotRun", result.Output);
    }
}
