using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28Data0136HandoffCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var bytes = File.ReadAllBytes(w.Baseline);
        new byte[] { 0x62, 129, 0, 0x67, 90, 0 }.CopyTo(bytes, 0x1966); // Invented isolated operand-guard footprints, not an OEM routine.
        File.WriteAllBytes(w.Baseline, bytes);
        var binding = P28ExactBaselineBinding.Parse(File.ReadAllText(w.Binding));
        File.WriteAllText(w.Binding, new P28ExactBaselineBinding(binding.FormatVersion, binding.ModelId, binding.ProfileId, binding.ExpectedSize, RomImage.Load(w.Baseline).Hash, binding.ProfileDigest).ToJson());
        var src = new P28FuelFactorSources(12345, 65535, 255, 65535, 65535, 255, 255, 0, 0, 255, 107, 0, 0, 0, 0, 0, 0, 0, 0);
        var first = new P28AdaptiveFuelCall(new(0, 89, 0, 0, 0, src), 1100, 0, false, false, true, true, true, false, 0, 0);
        var prefix = new P28PostStoreInitial(new(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0xF1, 0xAD, 7, 16, 128, 0xA5), 100, 110, 0, 0, 0xA55A, 0x5AA5), 321);
        var s = P28Data0136HandoffScenario.Create(new(new(0, 0, 164, 8, [1, 2, 3, 4, 5, 6]), 160, prefix, new(0, false, 200, false, 91, 0)),
            [new(0, 12, 0, 0, 0), new(1, 24, 0, 0, 5)], [new(first, false, false), new(first with { Fuel = first.Fuel with { Index = 1 } }, false, false)], "Invented unsupported producer; no OEM program", [0]);
        File.WriteAllText(w.Scenario, s.ToJson()); var args = w.LookupArguments(); args[2] = "data0136-handoff-check"; return args;
    }
    [Theory]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--baseline-binding")]
    [InlineData("--profile")]
    public async Task RequiredClosedInputsAndConfirmation(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var complete = Arguments(w); var args = complete.ToList(); args.RemoveRange(args.IndexOf(missing), 2);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(args.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(complete.Where(a => a != "--confirm-profile").ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("--word0136")]
    [InlineData("--ready0136")]
    [InlineData("--er2")]
    [InlineData("--quotient")]
    [InlineData("--jgt")]
    [InlineData("--writer-pc")]
    [InlineData("--generation")]
    [InlineData("--allow-assumption")]
    [InlineData("--output-bin")]
    public async Task NoInjectedOutputsOrMutationOptions(string option) { using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task NativePartialProducerThenNotRunPreservesInputsAndIsNotValidated()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot(); var r = await w.RunAsync(args);
        Assert.True(r.Code == CliApplication.VerificationFailed, r.Output + r.Error); w.AssertUnchanged(before); var report = JsonNode.Parse(File.ReadAllText(w.Output))!;
        Assert.Equal("0.34.0", report["runnerVersion"]!.GetValue<string>()); Assert.Equal("Partial", report["technicalScheduledHandoff"]!.GetValue<string>());
        foreach (var seq in report["sequences"]!.AsArray()) { Assert.Equal("ProducerPartial", seq!["checkpoints"]![0]!["disposition"]!.GetValue<string>()); Assert.Equal("NotRun", seq["checkpoints"]![1]!["disposition"]!.GetValue<string>()); Assert.Null(seq["checkpoints"]![0]!["readerGeneration"]); }
        Assert.Equal("NotEstablished", report["recoveredEcuScheduler"]!.GetValue<string>());
    }
    [Fact]
    public async Task AliasesExistingOutputClosedSchemaAndCancellationCannotPublishOrOverwrite()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var before = w.Snapshot();
        foreach (var path in before.Keys) { args[^1] = path; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); }
        w.AssertUnchanged(before); args[^1] = w.Output;
        using var cancel = new CancellationTokenSource(); cancel.Cancel(); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, cancel.Token)).Code); Assert.False(File.Exists(w.Output));
        var n = JsonNode.Parse(File.ReadAllText(w.Scenario))!; n["unifiedInitialState"]!["softwareSources"]!["word0136"] = 12; File.WriteAllText(w.Scenario, n.ToJsonString());
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output));
        File.WriteAllText(w.Output, "canary"); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(Arguments(w))).Code); Assert.Equal("canary", File.ReadAllText(w.Output));
    }
}
