using System.Reflection;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28ChainCliTests
{
    private static string[] Arguments(P28AcquisitionCliTests.Workspace w)
    {
        var a = w.Arguments(); a[2] = "chain-check";
        var raw = new P28ChainRawInputs(30, 0, 2, 0, 0, 255, 0);
        File.WriteAllText(w.Scenario, P28ChainScenario.Create(new(new(0, new ushort[6], 0, 0, 0, 0, 0, 0, 0, 0),
            new(0, 0, 0, 0, 0, 0, 0, 0), 0, 0, 0, raw), [new(0, 10, 0, 0, 0, true, 0, true, raw, 0, 0)], "Synthetic integrated CLI preflight").ToJson());
        return a;
    }
    [Fact]
    public async Task HelpIncludesClosedChainCommandAndThreeSeparatePermissions()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var r = await w.RunAsync(["help"]);
        Assert.Equal(CliApplication.Success, r.Code); Assert.Contains("chain-check", r.Output, StringComparison.Ordinal);
        foreach (var p in new[] { P28ProducerModel.AddEr1Assumption, P28ByteExecutionValidator.AddAssumption, P28StatefulModel.SubbOffAssumption }) Assert.Contains(p, r.Output, StringComparison.Ordinal);
    }
    [Theory]
    [InlineData("--profile")]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    public async Task MissingRequiredOptionAndConfirmationDoNotLaunchRunner(string missing)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); var index = Array.IndexOf(a, missing);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(a.Where((_, i) => i != index && i != index + 1).ToArray())).Code);
        Assert.Equal(CliApplication.UsageError, (await w.RunAsync(a.Where(v => v != "--confirm-profile").ToArray())).Code); Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("all")]
    [InlineData("unknown")]
    [InlineData("allow-all-unknown")]
    public async Task GlobalOrUnknownPermissionsAreNotSupported(string p)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. Arguments(w), "--allow-assumption", p])).Code); Assert.False(File.Exists(w.Output));
    }
    [Fact]
    public async Task FullChildTupleRequiredAndFakeCompleteLineageStillRefused()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); var lineage = w.LineageArguments();
        for (var mask = 1; mask < 15; mask++)
        {
            var tuple = Enumerable.Range(0, 4).Where(i => (mask & 1 << i) != 0).SelectMany(i => lineage.Skip(2 * i).Take(2));
            Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. a, .. tuple])).Code);
        }
        w.WriteLineagePlaceholders(); Assert.Equal(CliApplication.OperationError, (await w.RunAsync([.. a, .. lineage])).Code); Assert.False(File.Exists(w.Output));
    }
    [Fact]
    public async Task OutputsCannotAliasInputsOrReplaceEarlierResultAndCancellationPublishesNothing()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); var snapshot = w.InputSnapshot();
        foreach (var path in snapshot.Keys)
        {
            var alias = a.ToArray(); alias[Array.IndexOf(alias, "--output") + 1] = path;
            Assert.Equal(CliApplication.OperationError, (await w.RunAsync(alias)).Code); w.AssertUnchanged(snapshot);
        }
        File.WriteAllText(w.Output, "existing report"); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(a)).Code); Assert.Equal("existing report", File.ReadAllText(w.Output));
        var cancelled = a.ToArray(); cancelled[Array.IndexOf(cancelled, "--output") + 1] = Path.Combine(w.Root, "cancelled.json");
        using var c = new CancellationTokenSource(); c.Cancel(); Assert.Equal(CliApplication.OperationError, (await w.RunAsync(cancelled, c.Token)).Code);
        Assert.False(File.Exists(cancelled[^1])); w.AssertUnchanged(snapshot);
    }
    [Theory]
    [InlineData("compactCode")]
    [InlineData("samples")]
    [InlineData("T")]
    [InlineData("thresholdPriorBits")]
    public async Task PerEventProducedValueOverrideIsRejectedBeforeAnyOutputParentIsCreated(string field)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); var node = JsonNode.Parse(File.ReadAllText(w.Scenario))!;
        node["events"]![0]![field] = 0; File.WriteAllText(w.Scenario, node.ToJsonString());
        var parent = Path.Combine(w.Root, "never-created"); a[Array.IndexOf(a, "--output") + 1] = Path.Combine(parent, "report.json");
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(a)).Code); Assert.False(Directory.Exists(parent));
    }
    [Fact]
    public void SharedPreAndPostExecutionInputGuardRefusesStaleBytesForEveryCapturedInput()
    {
        // Exercise the exact guard called before AND after chain-check execution, without a timing race or a second framework.
        using var w = new P28AcquisitionCliTests.Workspace(); _ = Arguments(w);
        var guard = typeof(CliApplication).GetMethod("RequireCaptureInputSnapshot", BindingFlags.NonPublic | BindingFlags.Static)!; Assert.NotNull(guard);
        var snapshot = w.InputSnapshot(); guard.Invoke(null, [snapshot]);
        foreach (var path in snapshot.Keys)
        {
            File.WriteAllText(path, "changed after input snapshot");
            var error = Assert.Throws<TargetInvocationException>(() => guard.Invoke(null, [snapshot])); Assert.IsType<InvalidDataException>(error.InnerException);
            File.WriteAllBytes(path, snapshot[path]);
        }
        w.AssertUnchanged(snapshot); Assert.False(File.Exists(w.Output));
    }
}
