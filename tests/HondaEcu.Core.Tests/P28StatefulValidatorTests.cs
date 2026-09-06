using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28StatefulValidatorTests
{
    internal static readonly string[] Fixes = [.. P28AcquisitionValidatorTests.Fixes,
        "byte-clear-accumulator-zero-flag", "stateful-exact-byte-add-sub-half-carry", "increment-dp-half-carry", "decrement-indexed-x1-byte-half-borrow"];
    internal static P28StatefulScenario Scenario() => P28StatefulScenario.Create(P28StatefulModelTests.Initial(),
        [P28StatefulModelTests.Call(), P28StatefulModelTests.Call(35, 1) with { Index = 1 }, P28StatefulModelTests.Call() with { Index = 2, Enabled = false }], "Public comparator mock; not ROM execution");
    internal static JsonObject Mock(P28StatefulScenario scenario, bool conditional)
    {
        var sequences = new List<object>();
        foreach (var pattern in new[] { 0, 85, 170 })
        {
            var model = new P28StatefulModel(P28StatefulModelTests.Data(), scenario.InitialState);
            var checkpoints = new List<object>(); var cumulative = new HashSet<string>(); var completed = 0; var stop = -1; var notRun = 0;
            foreach (var input in scenario.Calls)
            {
                var expected = model.Step(input, conditional);
                cumulative.UnionWith(expected.UsedAssumptions);
                if (expected.Status == 0) completed++; else if (expected.Status == 4) notRun++; else stop = input.Index;
                var events = expected.ExecutedGatePcs.Select(pc =>
                {
                    var g = expected.Gates.Single(g => g.Pc == pc); var d = P28StatefulModel.GateDefinitions.Single(g => g.Pc == pc);
                    return new[] { pc, pc + Math.Max(d.Length, 2) + (d.Length != 0 && g.Outcome == true ? 1 : 0), 0, 0, 0,
                        g.Outcome == true ? 0x8000 : 0, g.Left ?? 65536, g.Right ?? 65536 };
                }).ToArray();
                checkpoints.Add(new
                {
                    input.Index,
                    status = expected.Status,
                    input,
                    stateBefore = expected.Before,
                    stateAtEntry = expected.AtEntry,
                    stateAfter = expected.After,
                    expected.SoftwareRequest,
                    expected.SelectionStatus,
                    tickRuns = Array.Empty<int[]>(),
                    tickWrites = expected.TickWrites,
                    decisionWrites = expected.DecisionWrites,
                    gateEvents = events,
                    execution = expected.Status == 4 ? null : new P28AcquisitionStageResult(expected.Status, expected.UsedAssumptions, 2,
                        expected.StopPc, [], [], [0x122C], [], expected.Unresolved),
                    tickFailure = (object?)null,
                    cumulativeAssumptions = cumulative.Order(StringComparer.Ordinal).ToArray()
                });
            }
            sequences.Add(new { imageIndex = 0, scratchPattern = pattern, checkpoints, completedCalls = completed, stopCallIndex = stop, remainingNotRun = notRun });
        }
        return JsonSerializer.SerializeToNode(new
        {
            protocolVersion = 1,
            operation = "statefulVtec",
            runnerVersion = "0.5.0",
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = Fixes,
            entryContracts = P28StatefulValidator.EntryContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            statefulSequences = sequences
        }, JsonDefaults.Create(false))!.AsObject();
    }
    private static P28StatefulValidationReport Analyze(P28StatefulScenario scenario, JsonObject mock, bool conditional = true)
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28StatefulModelTests.Data());
        return P28StatefulValidator.Analyze(image, profile, binding, scenario, new(JsonSerializer.SerializeToElement(mock), ""),
            conditional ? [P28StatefulModel.SubbOffAssumption] : []);
    }
    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void ComparatorMockAccountsForEveryCheckpointAndTerminalSuffix(bool conditional)
    {
        var scenario = Scenario(); var report = Analyze(scenario, Mock(scenario, conditional), conditional);
        Assert.False(report.HasFailure); Assert.False(report.PhysicalRpmAvailable);
        Assert.All(report.Sequences, s =>
        {
            Assert.Equal(conditional ? 3 : 0, s.CompletedCalls); Assert.Equal(conditional ? 0 : 1, s.Unresolved);
            Assert.Equal(conditional ? 0 : 2, s.NotRun); Assert.Equal(conditional ? 3 : 0, s.ConditionalMatches);
        });
    }
    [Fact]
    public void ActualMutationNeverFeedsIndependentModelHistoryEvenWhenActualContinuityIsConsistent()
    {
        var scenario = Scenario(); var mock = Mock(scenario, true);
        var cps = mock["statefulSequences"]![0]!["checkpoints"]!;
        cps[0]!["stateAfter"]!["data0131"] = 0;
        cps[1]!["stateBefore"]!["data0131"] = 0;
        var report = Analyze(scenario, mock);
        Assert.True(report.HasFailure);
        Assert.NotEqual(0, report.Sequences[0].Checkpoints[1].Expected!.Before.Data0131);
        Assert.Contains("Independent state before", report.Sequences[0].Checkpoints[1].Differences);
    }
    [Fact]
    public void ComparatorDetectsGateOrderSameValueStoreAndActualOperandTampering()
    {
        var scenario = Scenario();
        foreach (var mutation in new[] { "order", "store", "operand" })
        {
            var mock = Mock(scenario, true); var cp = mock["statefulSequences"]![0]!["checkpoints"]![0]!;
            if (mutation == "order") { var events = cp["gateEvents"]!.AsArray(); var first = events[0]!.DeepClone(); events.RemoveAt(0); events.Add(first); }
            else if (mutation == "store") cp["decisionWrites"]!.AsArray().RemoveAt(0);
            else { var cmp = cp["gateEvents"]!.AsArray().Single(e => e![0]!.GetValue<int>() == 0x125C)!; cmp[6] = 222; }
            Assert.True(Analyze(scenario, mock).HasFailure);
        }
    }
    [Fact]
    public void ThresholdSubresultRequiresActualPrefixGatesStoresAndPersistentState()
    {
        foreach (var mutation in new[] { "disabled-gate", "prefix-bit", "prefix-store" })
        {
            var scenario = Scenario(); var mock = Mock(scenario, true);
            var index = mutation == "disabled-gate" ? 2 : 0;
            var cp = mock["statefulSequences"]![0]!["checkpoints"]![index]!;
            if (mutation == "disabled-gate") cp["gateEvents"]!.AsArray().RemoveAt(0);
            else if (mutation == "prefix-bit") cp["stateAfter"]!["data0131"] = cp["stateAfter"]!["data0131"]!.GetValue<int>() ^ 1;
            else cp["decisionWrites"]!.AsArray().RemoveAt(0);
            var report = Analyze(scenario, mock);
            Assert.True(report.HasFailure);
            Assert.Equal("MismatchOrUnresolved", report.Sequences[0].Checkpoints[index].ThresholdValidation);
        }
    }
    [Fact]
    public void ProtocolRejectsUnknownFieldsInventedNotRunOutputsOversizedArraysAndLostVersionInventory()
    {
        var scenario = Scenario();
        foreach (var mutation in new[] { "unknown", "resume", "count", "version", "fixes" })
        {
            var mock = Mock(scenario, false);
            if (mutation == "unknown") mock["statefulSequences"]![0]!["checkpoints"]![0]!["fake"] = 0;
            if (mutation == "resume") mock["statefulSequences"]![0]!["checkpoints"]![1]!["softwareRequest"] = false;
            if (mutation == "count") mock["statefulSequences"]![0]!["remainingNotRun"] = 0;
            if (mutation == "version") mock["runnerVersion"] = "0.4.0";
            if (mutation == "fixes") mock["localSemanticFixes"]!.AsArray().RemoveAt(0);
            Assert.Throws<SliceProcessException>(() => Analyze(scenario, mock, false));
        }
        Assert.Throws<ArgumentException>(() => P28StatefulValidator.ValidateAssumptions(["oki.add-er1-a"]));
        Assert.Throws<ArgumentException>(() => P28StatefulValidator.ValidateAssumptions([P28StatefulModel.SubbOffAssumption, P28StatefulModel.SubbOffAssumption]));
    }
    [Fact]
    public async Task CancellationBeforeExecutionAndUnadmittedChildDoNotStartRunner()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28StatefulModelTests.Data());
        using var c = new CancellationTokenSource(); c.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28StatefulValidator.ExecuteAsync(image, profile, binding, true,
            "not-an-executable", Scenario(), cancellationToken: c.Token));
        await Assert.ThrowsAsync<InvalidDataException>(() => P28StatefulValidator.ExecuteAsync(image, profile, binding, true,
            "not-an-executable", Scenario(), derived: image));
    }
    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualSubprocessKeepsOwnHistoryAndDoesNotLaunderDifferentToyProgramAsModelPass()
    {
        var program = P28StatefulModelTests.Data();
        byte[] toy = [0xF4, 0x31, 0x86, 1, 0xD4, 0x31, 0x03, 0xFC, 0x12]; // Invented whole-byte increment, no VTEC algorithm.
        toy.CopyTo(program, 0x122C);
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(program);
        var saved = image.ToArray(); var scenario = Scenario(); var json = scenario.ToJson();
        var report = await P28StatefulValidator.ExecuteAsync(image, profile, binding, true, ExecutionTestPaths.RustRunner, scenario,
            [P28StatefulModel.SubbOffAssumption]);
        Assert.True(report.HasFailure); Assert.Single(report.ReplayDiagnostics);
        Assert.All(report.Sequences, s =>
        {
            Assert.Equal(scenario.InitialState.Data0131 + 3, s.Checkpoints[2].Actual.StateAfter.Data0131);
            Assert.NotEqual(s.Checkpoints[1].Actual.StateBefore.Data0131, s.Checkpoints[1].Expected!.Before.Data0131);
        });
        Assert.Equal(saved, image.ToArray()); Assert.Equal(json, scenario.ToJson());
    }
}
