using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28QuartetHandoffCliTests
{
    private static string[] Arguments(P28FuelMapCliTests.Workspace w)
    {
        var bytes = File.ReadAllBytes(w.Baseline); new byte[] { 0x62, 129, 0, 0x67, 90, 0 }.CopyTo(bytes, 0x1966); // Invented isolated guard footprints only.
        File.WriteAllBytes(w.Baseline, bytes); var binding = P28ExactBaselineBinding.Parse(File.ReadAllText(w.Binding));
        File.WriteAllText(w.Binding, new P28ExactBaselineBinding(binding.FormatVersion, binding.ModelId, binding.ProfileId, binding.ExpectedSize, RomImage.Load(w.Baseline).Hash, binding.ProfileDigest).ToJson());
        var src = new P28FuelFactorSources(12345, 65535, 255, 65535, 65535, 255, 255, 0, 0, 255, 107, 0, 0, 0, 0, 0, 0, 0, 0);
        var call = new P28AdaptiveFuelCall(new(0, 89, 0, 0, 0, src), 1100, 0, false, false, true, true, true, false, 0, 0);
        var initial = new P28PostStoreInitial(new(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0xF1, 0xAD, 7, 16, 128, 0xA5), 100, 110, 0, 0, 0xA55A, 0x5AA5), 321);
        var s = P28QuartetHandoffScenario.Create(new(initial, false), [new(new(call, false, false), 0), new(new(call with { Fuel = call.Fuel with { Index = 1 } }, false, false), 1)], "Invented unsupported prefix;no OEM code", [0]);
        File.WriteAllText(w.Scenario, s.ToJson()); var args = w.LookupArguments(); args[2] = "quartet-consumer-check"; return args;
    }
    [Theory]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    [InlineData("--baseline-binding")]
    [InlineData("--profile")]
    public async Task RequiredClosedInputsAndConfirmation(string missing)
    {
        using var w = new P28FuelMapCliTests.Workspace(); var complete = Arguments(w); var a = complete.ToList(); a.RemoveRange(a.IndexOf(missing), 2); Assert.Equal(CliApplication.UsageError, (await w.RunAsync(a.ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(complete.Where(a => a != "--confirm-profile").ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("--quartet")]
    [InlineData("--word0196")]
    [InlineData("--x1")]
    [InlineData("--selected-address")]
    [InlineData("--irq-frame")]
    [InlineData("--output-bin")]
    [InlineData("--allow-assumption")]
    public async Task NoReadyResultOrExportOptions(string option) { using var w = new P28FuelMapCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), option, "1"])).Code); Assert.False(File.Exists(w.Output)); }
    [Fact]
    public async Task PartialPrefixConsumerNotRunThenTerminalNotRunDoesNotPublishFresh0196()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var snapshot = w.Snapshot(); var r = await w.RunAsync(args); Assert.True(r.Code == CliApplication.VerificationFailed, r.Output + r.Error); w.AssertUnchanged(snapshot);
        var n = JsonNode.Parse(File.ReadAllText(w.Output))!; Assert.Equal("0.39.0", n["runnerVersion"]!.GetValue<string>()); Assert.Equal("Partial", n["quartetScheduledHandoff"]!.GetValue<string>());
        foreach (var s in n["sequences"]!.AsArray()) { Assert.Equal("ConsumerNotRun", s!["checkpoints"]![0]!["disposition"]!.GetValue<string>()); Assert.Equal("NotRun", s["checkpoints"]![1]!["disposition"]!.GetValue<string>()); Assert.Null(s["checkpoints"]![0]!["resultGeneration"]); }
    }
    [Fact]
    public async Task AliasesExistingOutputClosedSchemaAndCancellationPreserveInputs()
    {
        using var w = new P28FuelMapCliTests.Workspace(); var args = Arguments(w); var snapshot = w.Snapshot(); foreach (var path in snapshot.Keys) { args[^1] = path; Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); }
        w.AssertUnchanged(snapshot); args[^1] = w.Output;
        using var cancel = new CancellationTokenSource(); cancel.Cancel(); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args, cancel.Token)).Code); Assert.False(File.Exists(w.Output));
        var n = JsonNode.Parse(File.ReadAllText(w.Scenario))!; n["initialState"]!["word0196"] = 321; File.WriteAllText(w.Scenario, n.ToJsonString()); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(args)).Code); Assert.False(File.Exists(w.Output));
        File.WriteAllText(w.Output, "canary"); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(Arguments(w))).Code); Assert.Equal("canary", File.ReadAllText(w.Output));
    }
}
