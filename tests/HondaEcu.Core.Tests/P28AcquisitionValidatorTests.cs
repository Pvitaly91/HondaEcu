using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28AcquisitionValidatorTests
{
    [Fact]
    public void MockEveryObservationAndSameValueWritesAreComparedNotOnlyFinalT()
    {
        var scenario = Scenario(count: 7, first: true);
        var report = Analyze(scenario, Mock(scenario));
        Assert.False(report.HasFailure);
        Assert.Equal(3, report.Sequences.Count);
        Assert.All(report.Sequences, sequence =>
        {
            Assert.Equal(7, sequence.CompletedObservations);
            Assert.Equal(6, sequence.ActualSampleWrites);
            Assert.Equal(63, sequence.EverWrittenMask);
            Assert.True(sequence.WarmUpComplete);
            Assert.Equal(7, sequence.Acquisition.MatchesWithoutAssumptions);
            Assert.Equal(7, sequence.Producer.NotRun);
            Assert.Empty(sequence.Checkpoints[0].Acquisition.SampleWrites);
            Assert.Single(sequence.Checkpoints[1].Acquisition.SampleWrites);
        });
        var changed = Mock(scenario);
        Checkpoint(changed, 1)["acquisition"]!["stateAfter"]!["samples"]![4] = 999;
        var mismatch = Analyze(scenario, changed);
        Assert.True(mismatch.HasFailure);
        Assert.Contains(mismatch.Issues, issue => issue.ObservationIndex == 1 && issue.Stage == "Acquisition");
        Assert.Equal(10, mismatch.Sequences[0].IndependentExpectedStates[1].Samples[4]);
    }

    [Fact]
    public void StrictGStopRetainsPartialStateAndAbortsWholeSuffixWithoutFeedingActualRam()
    {
        var scenario = Scenario(count: 3, compose: true);
        var report = Analyze(scenario, Mock(scenario), composed: true);
        Assert.False(report.HasFailure);
        Assert.True(report.HasIncompleteOrConditional);
        Assert.All(report.Sequences, sequence =>
        {
            Assert.Equal(0, sequence.CompletedObservations);
            Assert.Equal(0, sequence.StopObservationIndex);
            Assert.Equal(2, sequence.RemainingNotRun);
            Assert.Equal(1, sequence.Producer.StoppedUnresolved);
            Assert.Equal(3, sequence.Compact.NotRun);
            Assert.Equal(2, sequence.Acquisition.NotRun);
            Assert.Empty(sequence.UsedAssumptions);
        });
        var changed = Mock(scenario);
        Checkpoint(changed, 1)["stateAfterComposition"]!["previousT"] = 44;
        Assert.Throws<SliceProcessException>(() => Analyze(scenario, changed, composed: true));
    }

    [Fact]
    public void Er1AndEr3AreIndependentAndUsedHistorySurvivesLaterUnscheduledObservation()
    {
        var seed = State() with { Samples = new ushort[] { 1000, 1000, 1000, 1000, 1000, 1000 }, Data0128 = 0 };
        var scenario = P28AcquisitionScenario.Create(seed,
            [new(0, 100, 0, 0, 0, true, 0, 0, true), new(1, 1100, 0, 0, 1, false, 1, 3, false)], "Mock accounting fixture");
        var er1 = new[] { P28ProducerModel.AddEr1Assumption };
        var onlyEr3 = new[] { P28ByteExecutionValidator.AddAssumption };
        var strictG = Analyze(scenario, Mock(scenario, onlyEr3), composed: true, allowed: onlyEr3);
        Assert.All(strictG.Sequences, sequence =>
        {
            Assert.Equal(1, sequence.Producer.StoppedUnresolved);
            Assert.Equal(2, sequence.Compact.NotRun);
            Assert.Empty(sequence.UsedAssumptions);
        });
        var strictF = Analyze(scenario, Mock(scenario, er1), composed: true, allowed: er1);
        Assert.False(strictF.HasFailure);
        Assert.All(strictF.Sequences, sequence => Assert.Equal(1, sequence.Compact.StoppedUnresolved));
        var both = new[] { P28ProducerModel.AddEr1Assumption, P28ByteExecutionValidator.AddAssumption };
        var report = Analyze(scenario, Mock(scenario, both), composed: true, allowed: both);
        Assert.False(report.HasFailure);
        Assert.All(report.Sequences, sequence =>
        {
            Assert.Equal(2, sequence.CompletedObservations);
            Assert.Equal(1, sequence.Acquisition.MatchesWithoutAssumptions);
            Assert.Equal(1, sequence.Acquisition.ConditionalMatches);
            Assert.Equal(1, sequence.Producer.ConditionalMatches);
            Assert.Equal(both, sequence.Checkpoints[1].CumulativeAssumptions);
            Assert.Empty(sequence.Checkpoints[1].Acquisition.UsedAssumptions);
        });
        var lost = Mock(scenario, both);
        Checkpoint(lost, 1)["cumulativeAssumptions"] = new JsonArray();
        Assert.Throws<SliceProcessException>(() => Analyze(scenario, lost, composed: true, allowed: both));
    }

    [Fact]
    public void UnsupportedModeIsNotRunNotAMatchedNativeStepAndNoInjectedSnapshot()
    {
        var scenario = Scenario(count: 2, unsupported: true);
        var report = Analyze(scenario, Mock(scenario));
        Assert.False(report.HasFailure);
        Assert.True(report.HasIncompleteOrConditional);
        Assert.All(report.Sequences, sequence =>
        {
            Assert.Equal(1, sequence.Acquisition.UnsupportedMode);
            Assert.Equal(1, sequence.Acquisition.NotRun);
            Assert.Equal(0, sequence.Acquisition.MatchesWithoutAssumptions);
            Assert.Null(sequence.Checkpoints[0].SelectedTimestamp);
        });
        var changed = Mock(scenario);
        Checkpoint(changed, 0)["selectedTimestamp"] = 0;
        Assert.Throws<SliceProcessException>(() => Analyze(scenario, changed));
    }

    [Fact]
    public void CompleteCardinalityContractsAndActualWriteCountsCannotBeFabricated()
    {
        var scenario = Scenario();
        var missing = Mock(scenario);
        missing["acquisitionSequences"]!.AsArray().RemoveAt(0);
        Assert.Throws<SliceProcessException>(() => Analyze(scenario, missing));
        var counts = Mock(scenario);
        Checkpoint(counts, 0)["slotWriteCounts"]![0] = 99;
        Assert.Throws<SliceProcessException>(() => Analyze(scenario, counts));
        var contract = Mock(scenario);
        contract["entryContracts"]![0]!["psw"] = 0;
        Assert.Throws<SliceProcessException>(() => Analyze(scenario, contract));
        var unknown = Mock(scenario);
        Checkpoint(unknown, 0)["acquisition"]!["stateAfter"]!["injected"] = true;
        Assert.Throws<SliceProcessException>(() => Analyze(scenario, unknown));
    }

    [Fact]
    public void ThresholdReadAddressAndUnexpectedUnresolvedAreFailuresNotConditionalSuccess()
    {
        var scenario = Scenario(count: 1, compose: true, first: true, zeroSamples: true);
        var report = Analyze(scenario, Mock(scenario), composed: true);
        Assert.False(report.HasFailure); // Leading zero bypasses G ADD; high-T F also requires no ADD.
        var changed = Mock(scenario);
        Checkpoint(changed, 0)["threshold"]!["programReads"] = new JsonArray(0x6543, 0x6542, 0x6544, 0x6545);
        Assert.True(Analyze(scenario, changed, composed: true).HasFailure);
        var unresolved = Mock(scenario);
        Checkpoint(unresolved, 0)["threshold"]!["status"] = 1;
        Checkpoint(unresolved, 0)["threshold"]!["stopPc"] = 0x1230;
        unresolved["acquisitionSequences"]![0]!["completedObservations"] = 0;
        unresolved["acquisitionSequences"]![0]!["stopObservationIndex"] = 0;
        var stopped = Analyze(scenario, unresolved, composed: true);
        Assert.True(stopped.HasFailure);
        Assert.Equal(1, stopped.Sequences[0].Threshold.StoppedUnresolved);
    }

    [Fact]
    public void NewIdentityKeepsLegacyChecksumReceiptAndRejectsWrongOperationOrFixSet()
    {
        var identity = Mock(Scenario());
        identity["operation"] = "checksumBatch";
        Assert.Equal(16, SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(identity), "checksumBatch").Length);
        identity["runnerVersion"] = "0.3.0";
        identity["localSemanticFixes"] = JsonSerializer.SerializeToNode(Fixes.Take(13));
        Assert.Equal(13, SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(identity), "checksumBatch").Length);
        identity["operation"] = "acquisitionSequence";
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(identity), "acquisitionSequence"));
        identity["runnerVersion"] = "0.4.0";
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(JsonSerializer.SerializeToElement(identity), "acquisitionSequence"));
    }

    [Fact]
    public void UnadmittedChildAndComposeInAcquisitionOnlyAreRejectedBeforeExecution()
    {
        var (baseline, profile, binding) = Fixture();
        var scenario = Scenario();
        Assert.Throws<InvalidDataException>(() => P28AcquisitionValidator.Analyze(baseline, profile, binding, scenario,
            new(JsonSerializer.SerializeToElement(Mock(scenario)), ""), derived: baseline));
        Assert.Throws<ArgumentException>(() => P28AcquisitionValidator.CreateRequest(baseline, null, Scenario(compose: true)));
    }

    internal static readonly string[] Fixes =
    [
        "word-ror-through-carry-preserves-noncarry-flags", "load-zero-flag-and-dd-contract", "word-srl-preserves-noncarry-flags", "bit-operands-use-byte-access",
        "clr-accumulator-zero-flag", "jrnz-dpl-byte-count", "adcb-r0-immediate-half-carry", "inc-x1-half-carry",
        "indexed-alternate-immediate-displacement", "word-data-access-alignment", "byte-add-direct-accumulator-half-carry",
        "byte-add-r0-accumulator-half-carry", "inc-indexed-x2-half-carry", "word-sub-direct-updates-half-borrow",
        "byte-inc-direct-updates-half-carry", "byte-sll-accumulator-preserves-noncarry-flags",
    ];
    internal static P28AcquisitionState State() => new(100, new ushort[] { 10, 10, 10, 10, 10, 10 }, 8, 77, 32, 0, 321, 0, 0, 222);
    internal static P28AcquisitionScenario Scenario(int count = 2, bool first = false, bool compose = false, bool unsupported = false, bool zeroSamples = false) =>
        P28AcquisitionScenario.Create(State() with
        {
            Data0128 = first ? (byte)0 : (byte)8,
            Data011F = unsupported ? (byte)4 : (byte)0,
            Samples = zeroSamples ? new ushort[6] : State().Samples
        },
            Enumerable.Range(0, count).Select(index => new P28CaptureObservation(index, (ushort)(110 + 10 * index), 0, 0,
                (index + 5) % 6, compose, 0, 0, true)).ToArray(), "Synthetic protocol accounting fixture");
    internal static (RomImage, RomProfile, P28ExactBaselineBinding) Fixture(byte[]? bytes = null)
    {
        var baseline = RomImage.FromBytes(bytes ?? new byte[32768]);
        var profile = new RomProfile("p28-304", "Synthetic sequence binding", "No OEM data", 32768, "synthetic-only", true, true,
            checksum: new ChecksumDefinition("unknown", ChecksumStatus.Unknown, 0, 0, ValidationLevel.PublicDocumentation));
        return (baseline, profile, new(1, P28CompactModel.ModelId, profile.Id, baseline.Size, baseline.Hash, P28VtecInspector.ComputeProfileDigest(profile)));
    }
    private static P28AcquisitionValidationReport Analyze(P28AcquisitionScenario scenario, JsonObject response, bool composed = false, string[]? allowed = null)
    {
        var (baseline, profile, binding) = Fixture();
        return P28AcquisitionValidator.Analyze(baseline, profile, binding, scenario, new(JsonSerializer.SerializeToElement(response), ""),
            composed ? P28AcquisitionValidator.ScheduledComposition : P28AcquisitionValidator.AcquisitionOnly, allowed);
    }
    private static JsonNode Checkpoint(JsonObject response, int index) => response["acquisitionSequences"]![0]!["checkpoints"]![index]!;

    internal static JsonObject Mock(P28AcquisitionScenario scenario, string[]? allowed = null)
    {
        // Explicitly a comparator mock, not proof that the native program agrees with its model.
        allowed ??= [];
        var sequences = new List<object>();
        foreach (var pattern in new[] { 0, 85, 170 })
        {
            var state = scenario.InitialState;
            var cumulative = new HashSet<string>();
            var checkpoints = new List<P28AcquisitionCheckpoint>();
            var stop = -1; var pc = 0x56BE; var completed = 0; var mask = 0; var counts = new int[6];
            foreach (var observation in scenario.Observations)
            {
                if (stop >= 0 || (state.Data011F & 4) != 0)
                {
                    var unsupported = stop < 0;
                    if (unsupported) stop = observation.Index;
                    var notRun = new P28AcquisitionObservedStep(4, unsupported ? "UnsupportedMode" : "NotRun", 0, pc,
                        [], [], state, [], [], [], [], unsupported ? "Unsupported mode" : null);
                    checkpoints.Add(new(observation.Index, null, null, notRun, null, null, null, state, cumulative.ToArray(), mask, counts.ToArray()));
                    continue;
                }
                var model = P28AcquisitionModel.Evaluate(state, observation);
                state = model.State;
                foreach (var write in model.SampleWrites) { var slot = (write[0] - 0x360) / 2; counts[slot]++; mask |= 1 << slot; }
                var acquisition = new P28AcquisitionObservedStep(0, model.Disposition.ToString(), 2, model.StopPc,
                    model.PeripheralAccesses, model.SampleWrites, state, [], [], [0x56BE], [], null);
                P28AcquisitionStageResult? g = null, f = null, threshold = null;
                if (observation.Compose)
                {
                    var produced = P28ProducerModel.Evaluate(new(observation.Index, "Mock", pattern, state.Samples, state.PreviousT,
                        state.Data0217, state.Data0231, observation.ThresholdContext, observation.ThresholdPriorBits, observation.ThresholdEnabled),
                        allowed.Contains(P28ProducerModel.AddEr1Assumption));
                    state = state with { PreviousT = produced.T, Data0217 = produced.Flags0217, Data0231 = produced.Flags0231, Samples = produced.Samples };
                    var outputs = new List<int> { produced.T & 255, produced.T >> 8, produced.Flags0217, produced.Flags0231 };
                    foreach (var sample in produced.Samples) outputs.AddRange([sample & 255, sample >> 8]);
                    g = new(produced.Resolved ? 0 : 1, produced.UsedAssumptions, 3, produced.Resolved ? 0x07A5 : 0x077E, outputs, [],
                        produced.UsedAssumptions.Count > 0 ? [0x0772, 0x077E, 0x077F] : [0x0772], [], produced.Resolved ? null : "Unresolved");
                    cumulative.UnionWith(g.UsedAssumptions);
                    if (g.Status == 0)
                    {
                        var needs = !P28CompactModel.Evaluate(produced.T, produced.S).Resolved;
                        var resolved = !needs || allowed.Contains(P28ByteExecutionValidator.AddAssumption);
                        var compact = P28CompactModel.EvaluateHypothesis(produced.T, produced.S);
                        f = new(resolved ? 0 : 1, needs && resolved ? [P28ByteExecutionValidator.AddAssumption] : [], 3,
                            resolved ? 0x0822 : 0x07F8, [compact.Code, compact.ExtraBit ? 16 : 0], [],
                            needs && resolved ? [0x07C7, 0x07F8, 0x07F9] : [0x07C7], [], resolved ? null : "Unresolved");
                        cumulative.UnionWith(f.UsedAssumptions);
                        if (resolved)
                        {
                            var bits = observation.ThresholdEnabled ? compact.Code > 0 ? 3 : 0 : observation.ThresholdPriorBits;
                            threshold = new(0, [], 2, observation.ThresholdEnabled ? 0x126D : 0x1281, [bits << 1],
                                observation.ThresholdEnabled ? Enumerable.Range(0x6542 + observation.ThresholdContext * 4, 4).ToArray() : [], [0x122C], [], null);
                        }
                    }
                }
                if (observation.Compose && threshold is null) { stop = observation.Index; pc = f?.StopPc ?? g!.StopPc; }
                else { completed++; pc = threshold?.StopPc ?? model.StopPc; }
                checkpoints.Add(new(observation.Index, model.SelectedTimestamp, model.SlotIndex, acquisition, g, f, threshold,
                    state, cumulative.ToArray(), mask, counts.ToArray()));
            }
            sequences.Add(new
            {
                imageIndex = 0,
                scratchPattern = pattern,
                stopObservationIndex = stop,
                completedObservations = completed,
                remainingNotRun = stop < 0 ? 0 : scenario.Observations.Count - stop - 1,
                checkpoints
            });
        }
        return JsonSerializer.SerializeToNode(new
        {
            protocolVersion = 1,
            operation = "acquisitionSequence",
            runnerVersion = "0.4.0",
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = Fixes,
            entryContracts = P28AcquisitionValidator.ExpectedEntryContracts(),
            diagnostics = Array.Empty<object>(),
            acquisitionSequences = sequences
        },
            JsonDefaults.Create(false))!.AsObject();
    }
}
