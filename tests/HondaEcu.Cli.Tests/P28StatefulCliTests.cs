using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28StatefulCliTests
{
    private static string[] Arguments(P28AcquisitionCliTests.Workspace w)
    {
        var a = w.Arguments(); a[2] = "state-check";
        File.WriteAllText(w.Scenario, P28StatefulScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 0),
            [new(0, 0, 0, false, 0, 0, 0, 0, 0, 0, 0, 0, 0)], "Synthetic stateful CLI preflight").ToJson());
        return a;
    }
    [Fact]
    public async Task HelpDocumentsStatefulModeAndSpecificPermissionWithoutPhysicalClaims()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var r = await w.RunAsync(["help"]);
        Assert.Equal(CliApplication.Success, r.Code); Assert.Contains("state-check", r.Output, StringComparison.Ordinal);
        Assert.Contains(P28StatefulModel.SubbOffAssumption, r.Output, StringComparison.Ordinal);
    }
    [Theory]
    [InlineData("--profile")]
    [InlineData("--baseline-binding")]
    [InlineData("--runner")]
    [InlineData("--scenario")]
    [InlineData("--output")]
    public async Task RequiredOptionsAndConfirmationCannotBeSkipped(string missing)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); var at = Array.IndexOf(a, missing);
        var r = await w.RunAsync(a.Where((_, i) => i != at && i != at + 1).ToArray()); Assert.Equal(CliApplication.UsageError, r.Code);
        var noConfirm = await w.RunAsync(a.Where(v => v != "--confirm-profile").ToArray()); Assert.Equal(CliApplication.UsageError, noConfirm.Code);
        Assert.False(File.Exists(w.Output));
    }
    [Theory]
    [InlineData("all")]
    [InlineData("oki.add-er1-a")]
    [InlineData("oki.add-er3-a")]
    [InlineData("unknown")]
    public async Task ExistingAddAndGlobalPermissionsCannotLeakIntoVtecOnly(string permission)
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var r = await w.RunAsync([.. Arguments(w), "--allow-assumption", permission]);
        Assert.Equal(CliApplication.UsageError, r.Code); Assert.False(File.Exists(w.Output));
    }
    [Fact]
    public async Task EveryIncompleteChildTupleIsRejectedAndCompleteTupleStillNeedsRealLineage()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); var lineage = w.LineageArguments();
        for (var mask = 1; mask < 15; mask++)
        {
            var tuple = Enumerable.Range(0, 4).Where(i => (mask & 1 << i) != 0).SelectMany(i => lineage.Skip(2 * i).Take(2));
            Assert.Equal(CliApplication.UsageError, (await w.RunAsync([.. a, .. tuple])).Code);
        }
        w.WriteLineagePlaceholders(); Assert.Equal(CliApplication.OperationError, (await w.RunAsync([.. a, .. lineage])).Code);
        Assert.False(File.Exists(w.Output));
    }
    [Fact]
    public async Task ExistingOutputEveryInputAliasAndCancellationPreserveAllInputs()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); var snapshot = w.InputSnapshot();
        foreach (var path in snapshot.Keys)
        {
            var alias = a.ToArray(); alias[Array.IndexOf(alias, "--output") + 1] = path;
            Assert.Equal(CliApplication.OperationError, (await w.RunAsync(alias)).Code); w.AssertUnchanged(snapshot);
        }
        File.WriteAllText(w.Output, "previous result must survive");
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(a)).Code);
        Assert.Equal("previous result must survive", File.ReadAllText(w.Output));
        var cancelArgs = a.ToArray(); cancelArgs[Array.IndexOf(cancelArgs, "--output") + 1] = Path.Combine(w.Root, "cancelled-report.json");
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        Assert.Equal(CliApplication.OperationError, (await w.RunAsync(cancelArgs, cancellation.Token)).Code);
        Assert.False(File.Exists(cancelArgs[^1])); w.AssertUnchanged(snapshot);
    }
    [Fact]
    public async Task InvalidScenarioCannotCreateOutputParentOrStartTheSentinelRunner()
    {
        using var w = new P28AcquisitionCliTests.Workspace(); var a = Arguments(w); w.WriteMalformedScenario();
        var parent = Path.Combine(w.Root, "must-not-exist"); a[Array.IndexOf(a, "--output") + 1] = Path.Combine(parent, "report.json");
        var r = await w.RunAsync([.. a, "--allow-assumption", P28StatefulModel.SubbOffAssumption]);
        Assert.Equal(CliApplication.OperationError, r.Code); Assert.Contains("Missing required", r.Error, StringComparison.Ordinal);
        Assert.False(Directory.Exists(parent));
    }
}
