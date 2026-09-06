using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28ChainValidatorTests
{
    // Comparator fixture only: model-shaped state/journals and deliberately schematic CPU traces.
    // Never used as evidence of native ROM execution; the subprocess tests use different toy programs.
    internal static JsonObject Mock(P28ChainScenario scenario, int permissionCount = 3)
    {
        var sequences = new List<object>();
        foreach (var pattern in new[] { 0, 85, 170 })
        {
            var model = new P28ChainModel(P28StatefulModelTests.Data(), scenario.InitialState, P28ChainValidator.Permissions.Take(permissionCount));
            var pointing = Enumerable.Repeat((byte)pattern, 16).ToArray(); pointing[14] = 0x80; pointing[15] = 2;
            var architecture = new P28ChainArchitecture(0x56BE, (ushort)(pattern * 257), 0x21, 0x1DCA, 0x7FE, Enumerable.Repeat((byte)pattern, 24).ToArray(), pointing, (ushort)(pattern * 257));
            var checkpoints = new List<object>(); var completed = 0; var decisions = 0; var stop = -1; var mask = 0; var counts = new int[6];
            foreach (var input in scenario.Events)
            {
                var expected = model.Step(input); var stages = new List<P28ChainObservedStage>();
                foreach (var s in expected.Stages)
                {
                    var before = architecture; var entry = architecture; P28AcquisitionStageResult? execution = null;
                    if (s.Status is not (4 or 5))
                    {
                        Assert.NotEqual("NativeCounterBodies", s.Id); // Native counters have their own real subprocess regression.
                        var (pc, lrb, psw, usp, scb) = s.Id switch
                        { "Acquisition" => (0x56BE, 0x21, 0x1DCA, 0x280, 8), "G" => (0x0772, 0x40, 0x1DC9, 0x180, 0), "F" => (0x07C7, 0x40, 0x1DC9, 0x180, 0), _ => (0x122C, 0x20, 0x0DC9, 0x280, 0) };
                        pointing = architecture.Pointing.ToArray(); pointing[scb + 6] = (byte)usp; pointing[scb + 7] = (byte)(usp >> 8);
                        entry = architecture with { Pc = (ushort)pc, Lrb = (ushort)lrb, Psw = (ushort)psw, Pointing = pointing };
                        architecture = entry with { Pc = (ushort)s.StopPc!.Value };
                        var extents = new List<int> { pc };
                        foreach (var p in s.UsedAssumptions)
                        {
                            var location = p == P28ProducerModel.AddEr1Assumption ? 0x077E : p == P28ByteExecutionValidator.AddAssumption ? 0x07F8 : 0x12B4;
                            extents.Add(location); extents.Add(location + 1);
                        }
                        execution = new(s.Status, s.UsedAssumptions, 2, s.StopPc.Value, [], [], extents.Distinct().Order().ToArray(), [], s.Status == 0 ? null : "Comparator unresolved fixture");
                    }
                    var gates = s.Decision?.ExecutedGatePcs.Select(pc =>
                    {
                        var g = s.Decision.Gates.Single(g => g.Pc == pc); var d = P28StatefulModel.GateDefinitions.Single(g => g.Pc == pc);
                        return new[] { pc, pc + Math.Max(d.Length, 2) + (d.Length != 0 && g.Outcome == true ? 1 : 0), 0, 0, 0,
                            g.Outcome == true ? 0x8000 : 0, g.Left ?? 65536, g.Right ?? 65536 };
                    }).ToArray() ?? [];
                    stages.Add(new(s.Id, s.Status, s.Before, s.Before, s.After, before, entry, architecture, execution,
                        s.PersistentWrites, s.PeripheralAccesses, gates, [], s.CumulativeAssumptions));
                    if (s.Id == "Acquisition") foreach (var w in s.PersistentWrites.Where(w => w[0] >= 0x360)) { var slot = (w[0] - 0x360) / 2; counts[slot]++; mask |= 1 << slot; }
                    if (s.Status is 1 or 2 or 3 or 5 && stop < 0) stop = input.Index;
                }
                if (stop < 0) completed++; if (stages[^1].Status == 0) decisions++;
                checkpoints.Add(new
                {
                    input.Index,
                    input,
                    stateBefore = expected.Before,
                    stateAfterInputs = expected.AfterInputs,
                    expected.CallerWrites,
                    stages,
                    stateAfter = expected.After,
                    expected.SoftwareRequest,
                    expected.RequestMirror,
                    expected.SelectionStatus,
                    everWrittenMask = mask,
                    slotWriteCounts = counts.ToArray(),
                    cumulativeAssumptions = stages[^1].CumulativeAssumptions
                });
            }
            sequences.Add(new { imageIndex = 0, scratchPattern = pattern, checkpoints, completedEvents = completed, completedDecisions = decisions, stopEventIndex = stop });
        }
        return JsonSerializer.SerializeToNode(new
        {
            protocolVersion = 1,
            operation = P28ChainValidator.Operation,
            runnerVersion = "0.6.0",
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = P28StatefulValidatorTests.Fixes,
            entryContracts = P28ChainValidator.EntryContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            chainSequences = sequences
        }, JsonDefaults.Create(false))!.AsObject();
    }
    private static P28ChainReport Analyze(P28ChainScenario s, JsonObject response, int permissions = 3)
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28StatefulModelTests.Data());
        return P28ChainValidator.Analyze(image, profile, binding, s, new(JsonSerializer.SerializeToElement(response), ""), P28ChainValidator.Permissions.Take(permissions));
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void ModelShapedMockAccountsForPermissionsAndNullTerminalSuffix(int permissions)
    {
        var s = P28ChainModelTests.Scenario(); var report = Analyze(s, Mock(s, permissions), permissions);
        Assert.False(report.HasFailure); Assert.False(report.PhysicalRpmAvailable);
        Assert.All(report.Sequences, r =>
        {
            Assert.Equal(9, r.RequestedEvents); Assert.Equal(permissions < 3 ? 6 : 9, r.CompletedEvents);
            Assert.Equal(permissions < 3 ? 0 : 3, r.CompletedDecisions);
            if (permissions < 3) { Assert.Null(r.Checkpoints[7].SoftwareRequest); Assert.All(r.Checkpoints[7].Stages, stage => Assert.Equal("NotRun", stage.Validation)); }
            else Assert.Equal("ConditionalMatch", r.Checkpoints[7].Stages[0].Validation);
        });
    }
    [Fact]
    public void ObservedHistoryNeverFeedsCSharpEvenWithConsistentActualContinuity()
    {
        var s = P28ChainModelTests.Scenario(); var response = Mock(s); var cps = response["chainSequences"]![0]!["checkpoints"]!;
        // Actual history is self-consistent from event 7 onward but contradicts the independent model.
        cps[6]!["stateAfter"]!["decision"]!["data0131"] = 0;
        cps[7]!["stateBefore"]!["decision"]!["data0131"] = 0;
        var report = Analyze(s, response); Assert.True(report.HasFailure);
        Assert.Contains("Independent event state before", report.Sequences[0].Checkpoints[7].Differences);
        Assert.NotEqual(0, report.Sequences[0].Checkpoints[7].Stages[0].Expected.Before.Decision.Data0131);
    }
    [Theory]
    [InlineData("code-entry")]
    [InlineData("prior-entry")]
    [InlineData("p1-capture")]
    [InlineData("word-clobber")]
    [InlineData("counter-reset")]
    [InlineData("bank")]
    [InlineData("scb")]
    [InlineData("ssp")]
    [InlineData("same-value-store")]
    [InlineData("gate-order")]
    [InlineData("operand")]
    public void HiddenSubstitutionsAndWrongSideEffectsCannotBeLaundered(string mutation)
    {
        var s = P28ChainModelTests.Scenario(); var response = Mock(s); var stages = response["chainSequences"]![0]!["checkpoints"]![6]!["stages"]!;
        switch (mutation)
        {
            case "code-entry": stages[4]!["stateAtEntry"]!["code"] = 99; break;
            case "prior-entry": stages[4]!["stateAtEntry"]!["decision"]!["data0131"] = 0; break;
            case "p1-capture": stages[0]!["stateAfter"]!["decision"]!["p1OutputData"] = 0; break;
            case "word-clobber": stages[3]!["nativeWrites"]![1]![0] = 0x132; stages[3]!["nativeWrites"]![1]![1] = 16; break;
            case "counter-reset": stages[4]!["stateAtEntry"]!["decision"]!["data01D8"] = 0; break;
            case "bank": stages[2]!["architectureAtEntry"]!["banks"]![8] = 37; break;
            case "scb": stages[3]!["architectureAfter"]!["pointing"]![14] = 0; break;
            case "ssp": stages[4]!["architectureAfter"]!["ssp"] = 0x800; break;
            case "same-value-store": stages[0]!["nativeWrites"]!.AsArray().RemoveAt(0); break;
            case "gate-order": var gs = stages[4]!["gateEvents"]!.AsArray(); var first = gs[0]!.DeepClone(); gs.RemoveAt(0); gs.Add(first); break;
            case "operand": stages[4]!["gateEvents"]!.AsArray().Single(g => g![0]!.GetValue<int>() == 0x125C)![6] = 99; break;
        }
        Assert.True(Analyze(s, response).HasFailure);
    }
    [Theory]
    [InlineData("unknown")]
    [InlineData("suffix-request")]
    [InlineData("suffix-inputs")]
    [InlineData("count")]
    [InlineData("assumptions")]
    [InlineData("foreign-assumption")]
    [InlineData("extent")]
    [InlineData("zero-step")]
    [InlineData("missing-error")]
    [InlineData("version")]
    public void MalformedResponseIsRefusedInsteadOfBecomingAnAgreement(string mutation)
    {
        var s = P28ChainModelTests.Scenario(); var response = Mock(s, 1); var seq = response["chainSequences"]![0]!; var cp = seq["checkpoints"]![6]!;
        switch (mutation)
        {
            case "unknown": cp["overrides"] = 0; break;
            case "suffix-request": seq["checkpoints"]![7]!["softwareRequest"] = false; break;
            case "suffix-inputs": seq["checkpoints"]![7]!["stateAfterInputs"]!["raw"]!["raw00CC"] = 99; break;
            case "count": seq["completedEvents"] = 9; break;
            case "assumptions": seq["checkpoints"]![7]!["cumulativeAssumptions"] = new JsonArray(); break;
            case "foreign-assumption": cp["stages"]![0]!["execution"]!["usedAssumptions"] = new JsonArray(P28ProducerModel.AddEr1Assumption); break;
            case "extent": cp["stages"]![0]!["execution"]!["executedInstructionBytes"] = new JsonArray(0x7FFF); break;
            case "zero-step": cp["stages"]![0]!["execution"]!["steps"] = 0; break;
            case "missing-error": cp["stages"]![3]!["execution"]!["error"] = null; break;
            case "version": response["runnerVersion"] = "0.5.0"; break;
        }
        Assert.Throws<SliceProcessException>(() => Analyze(s, response, 1));
    }
    [Fact]
    public async Task CancellationAndMissingLineageNeverStartRunner()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28StatefulModelTests.Data()); var s = P28ChainModelTests.Scenario();
        using var c = new CancellationTokenSource(); c.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28ChainValidator.ExecuteAsync(image, profile, binding, true, "sentinel-not-executable", s, cancellationToken: c.Token));
        await Assert.ThrowsAsync<InvalidDataException>(() => P28ChainValidator.ExecuteAsync(image, profile, binding, true, "sentinel-not-executable", s, derived: image));
        Assert.Throws<ArgumentException>(() => P28ChainValidator.ValidateAssumptions(["allow-all-unknown"]));
        Assert.Throws<ArgumentException>(() => P28ChainValidator.ValidateAssumptions([P28ProducerModel.AddEr1Assumption, P28ProducerModel.AddEr1Assumption]));
    }

    [Fact]
    public void PairingNeverTreatsStoppedSuffixAsComparableOrIgnoresEqualStateWrongStores()
    {
        var scenario = P28ChainModelTests.Scenario();
        var stopped = Analyze(scenario, Mock(scenario, 0), 0).Sequences;
        var full = Analyze(scenario, Mock(scenario)).Sequences;
        // Already-analyzed comparator fixtures only, not child admission or OEM evidence.
        var sequences = stopped.Concat(full.Select(s => s with { ImageIndex = 1, ImageId = "intermediate" }))
            .Concat(full.Select(s => s with { ImageIndex = 2, ImageId = "derived" })).ToArray();
        var pairs = P28ChainValidator.CompareImages(sequences, 3);
        Assert.All(pairs.Where(p => p.Pair == "A/B"), p =>
        {
            Assert.Equal(6, p.ComparableEvents); Assert.Equal(0, p.ComparableDecisions);
            Assert.All(p.Checkpoints.Skip(6), c => { Assert.Equal("NotComparable", c.Comparison); Assert.Null(c.StateEqual); Assert.Null(c.RequestEqual); });
        });
        Assert.All(pairs.Where(p => p.Pair == "B/C"), p => Assert.True(p.ObservedExecutionPrefixesEqual));
        var child = sequences[6]; var checkpoints = child.Checkpoints.ToArray(); var stages = checkpoints[6].Stages.ToArray();
        stages[3] = stages[3] with { Actual = stages[3].Actual with { NativeWrites = [] } }; // Same state/request, missing native F stores.
        checkpoints[6] = checkpoints[6] with { Stages = stages }; sequences[6] = child with { Checkpoints = checkpoints };
        var changed = P28ChainValidator.CompareImages(sequences, 3).Single(p => p.Pair == "B/C" && p.ScratchPattern == 0);
        Assert.False(changed.ObservedExecutionPrefixesEqual); Assert.True(changed.Checkpoints[6].StateEqual); Assert.False(changed.Checkpoints[6].SideEffectsEqual);
    }
}
