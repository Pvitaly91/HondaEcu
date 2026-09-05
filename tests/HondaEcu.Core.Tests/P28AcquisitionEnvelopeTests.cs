using System.Text.Json;

namespace HondaEcu.Core.Tests;

/// <summary>Constructed report fixtures only; no executable/OEM procedure or ROM authority.</summary>
public sealed class P28AcquisitionEnvelopeTests
{
    [Fact]
    public void AllSixActualFreshWritesAreRequiredBeforeAUniformCheckpointCanMatch()
    {
        var fixture = Fixture();
        var comparison = P28AcquisitionEnvelope.Compare(fixture.Report, fixture.Stimulus, fixture.Query);
        Assert.Equal(1, comparison.SteadyCheckpoints);
        Assert.Equal(6, comparison.OutOfScopeCheckpoints);
        Assert.All(comparison.Checkpoints.Take(6), checkpoint =>
        {
            Assert.Equal("WarmUpStaleOrTransientHistory", checkpoint.Scope);
            Assert.Null(checkpoint.SamplesInsideEnvelope);
            Assert.Null(checkpoint.ProducerInsideEnvelope);
            Assert.Null(checkpoint.CompactInsideEnvelope);
        });
        var final = comparison.Checkpoints[^1];
        Assert.Equal("FreshUniformSteadyHistory", final.Scope);
        Assert.True(final.SamplesInsideEnvelope);
        Assert.True(final.ProducerInsideEnvelope);
        Assert.True(final.CompactInsideEnvelope);
        Assert.False(comparison.HasFailure);
        Assert.False(comparison.PhysicalRpmAvailable);
    }

    [Fact]
    public void EqualStartupValuesWithoutActualStoresNeverProvideFreshnessEvidence()
    {
        var fixture = Fixture(period: new(2, 1));
        var checkpoints = fixture.Report.Sequences[0].Checkpoints.Select(checkpoint => checkpoint with
        {
            Acquisition = checkpoint.Acquisition with { SampleWrites = [] },
        }).ToArray();
        var comparison = Compare(fixture, checkpoints);
        Assert.Equal(0, comparison.SteadyCheckpoints);
        Assert.All(comparison.Checkpoints, checkpoint => Assert.Equal("WarmUpStaleOrTransientHistory", checkpoint.Scope));
        Assert.False(comparison.HasFailure);
    }

    [Fact]
    public void RealSameValueStoresDoProvideFreshnessEvidence()
    {
        var fixture = Fixture(period: new(2, 1));
        Assert.All(fixture.Report.Sequences[0].Checkpoints, checkpoint =>
            Assert.Equal(new ushort[] { 2, 2, 2, 2, 2, 2 }, checkpoint.Acquisition.StateAfter.Samples));
        Assert.All(fixture.Report.Sequences[0].Checkpoints.Skip(1), checkpoint => Assert.Single(checkpoint.Acquisition.SampleWrites));
        var comparison = P28AcquisitionEnvelope.Compare(fixture.Report, fixture.Stimulus, fixture.Query);
        Assert.Equal(1, comparison.SteadyCheckpoints);
        Assert.True(comparison.Checkpoints[^1].SamplesInsideEnvelope);
    }

    [Fact]
    public void OneStaleSlotOrRepeatedWritesToOneSlotCannotMasqueradeAsSixFreshSlots()
    {
        var fixture = Fixture(period: new(2, 1));
        var missingSlot = fixture.Report.Sequences[0].Checkpoints.Select(checkpoint => checkpoint.ObservationIndex == 3
            ? checkpoint with { Acquisition = checkpoint.Acquisition with { SampleWrites = [] } } : checkpoint).ToArray();
        Assert.Equal(0, Compare(fixture, missingSlot).SteadyCheckpoints);
        var repeated = fixture.Report.Sequences[0].Checkpoints.Select(checkpoint => checkpoint.ObservationIndex == 0 ? checkpoint : checkpoint with
        {
            Acquisition = checkpoint.Acquisition with { SampleWrites = new[] { new[] { 0x360, 16, 2 } } },
        }).ToArray();
        Assert.Equal(0, Compare(fixture, repeated).SteadyCheckpoints);
    }

    [Theory]
    [InlineData(0x361, 16)]
    [InlineData(0x35E, 16)]
    [InlineData(0x36C, 16)]
    [InlineData(0x360, 8)]
    public void WrongAddressOrWidthCannotSupplyMissingWordWriteEvidence(int address, int width)
    {
        var fixture = Fixture(period: new(2, 1));
        var checkpoints = fixture.Report.Sequences[0].Checkpoints.ToArray();
        checkpoints[1] = checkpoints[1] with
        {
            Acquisition = checkpoints[1].Acquisition with { SampleWrites = new[] { new[] { address, width, 2 } } },
        };
        Assert.Equal(0, Compare(fixture, checkpoints).SteadyCheckpoints);
    }

    [Fact]
    public void FreshnessIsIndependentForEachImageAndScratchSequence()
    {
        var fixture = Fixture();
        var first = fixture.Report.Sequences[0];
        var second = first with
        {
            ImageIndex = 1,
            ImageId = "constructed-independent-child",
            ScratchPattern = 85,
            Checkpoints = first.Checkpoints.Select(checkpoint => checkpoint with
            { Acquisition = checkpoint.Acquisition with { SampleWrites = [] } }).ToArray(),
        };
        var report = fixture.Report with { Sequences = new[] { first, second } };
        var comparison = P28AcquisitionEnvelope.Compare(report, fixture.Stimulus, fixture.Query);
        Assert.Equal(1, comparison.SteadyCheckpoints);
        Assert.All(comparison.Checkpoints.Where(checkpoint => checkpoint.ImageIndex == 1), checkpoint =>
        {
            Assert.Equal(85, checkpoint.ScratchPattern);
            Assert.Equal("WarmUpStaleOrTransientHistory", checkpoint.Scope);
        });
    }

    [Fact]
    public void DifferentPeriodAndInvalidZeroReplacementInvalidatePreviouslyFreshHistory()
    {
        var periods = Enumerable.Repeat(new P28CaptureRational(5, 2), 6).Append(new(7, 2)).ToArray();
        var transient = Fixture(periods: periods);
        var transientResult = P28AcquisitionEnvelope.Compare(transient.Report, transient.Stimulus, transient.Query);
        Assert.Equal("FreshUniformSteadyHistory", transientResult.Checkpoints[6].Scope);
        Assert.Equal("WarmUpStaleOrTransientHistory", transientResult.Checkpoints[7].Scope);

        var invalid = Fixture(periods: Enumerable.Repeat(new P28CaptureRational(5, 2), 7).ToArray(), tcerrIndex: 7);
        Assert.Equal(nameof(P28AcquisitionDisposition.InvalidZeroWrite), invalid.Report.Sequences[0].Checkpoints[7].Acquisition.Disposition);
        var invalidResult = P28AcquisitionEnvelope.Compare(invalid.Report, invalid.Stimulus, invalid.Query);
        Assert.Equal("FreshUniformSteadyHistory", invalidResult.Checkpoints[6].Scope);
        Assert.Equal("WarmUpStaleOrTransientHistory", invalidResult.Checkpoints[7].Scope);
        Assert.Null(invalidResult.Checkpoints[7].SamplesInsideEnvelope);
        Assert.False(invalidResult.HasFailure);
    }

    [Theory]
    [InlineData("samples")]
    [InlineData("g-value")]
    [InlineData("g-bit4")]
    [InlineData("f-code")]
    [InlineData("f-bit4")]
    public void FreshOutOfEnvelopeSamplesOrCompletedGfOutputsProduceARealFailure(string defect)
    {
        var fixture = Fixture();
        var checkpoints = fixture.Report.Sequences[0].Checkpoints.ToArray();
        var final = checkpoints[^1];
        if (defect == "samples")
        {
            var samples = final.Acquisition.StateAfter.Samples.ToArray(); samples[0] = 999;
            final = final with { Acquisition = final.Acquisition with { StateAfter = final.Acquisition.StateAfter with { Samples = samples } } };
        }
        else if (defect.StartsWith("g-", StringComparison.Ordinal))
        {
            var outputs = final.G!.Outputs.ToArray();
            if (defect == "g-value") { outputs[0] ^= 1; } else { outputs[2] ^= 0x10; }
            final = final with { G = final.G with { Outputs = outputs } };
        }
        else
        {
            var outputs = final.F!.Outputs.ToArray();
            if (defect == "f-code") { outputs[0] ^= 1; } else { outputs[1] ^= 0x10; }
            final = final with { F = final.F with { Outputs = outputs } };
        }
        checkpoints[^1] = final;
        var comparison = Compare(fixture, checkpoints);
        Assert.True(comparison.HasFailure);
        Assert.Equal("FreshUniformSteadyHistory", comparison.Checkpoints[^1].Scope);
    }

    [Fact]
    public void GfComparisonUsesBitFourNotWholeStatusByteAndDoesNotInventCompletedStages()
    {
        var fixture = Fixture();
        var checkpoints = fixture.Report.Sequences[0].Checkpoints.ToArray();
        var final = checkpoints[^1];
        var g = final.G!.Outputs.ToArray(); g[2] ^= 0xEF;
        var f = final.F!.Outputs.ToArray(); f[1] ^= 0xEF;
        checkpoints[^1] = final with { G = final.G with { Outputs = g }, F = final.F with { Outputs = f } };
        Assert.False(Compare(fixture, checkpoints).HasFailure);
        checkpoints[^1] = final with { G = final.G with { Status = 1 }, F = null };
        var unavailable = Compare(fixture, checkpoints);
        Assert.True(unavailable.Checkpoints[^1].SamplesInsideEnvelope);
        Assert.Null(unavailable.Checkpoints[^1].ProducerInsideEnvelope);
        Assert.Null(unavailable.Checkpoints[^1].CompactInsideEnvelope);
        Assert.False(unavailable.HasFailure);
    }

    [Fact]
    public void StrictUnresolvedModelComparisonsStayNullRatherThanPassed()
    {
        var fixture = Fixture(permissions: []);
        var comparison = P28AcquisitionEnvelope.Compare(fixture.Report, fixture.Stimulus, fixture.Query);
        Assert.Equal("OutsideM1hNormalDomain", comparison.Checkpoints[^1].Scope);
        Assert.Null(comparison.Checkpoints[^1].SamplesInsideEnvelope);
        Assert.Null(comparison.Checkpoints[^1].ProducerInsideEnvelope);
        Assert.Null(comparison.Checkpoints[^1].CompactInsideEnvelope);
        Assert.Empty(comparison.PermittedAssumptions);
    }

    [Fact]
    public void MissingTimelineAlternativeModeAndIncompleteAcquisitionRemainOutsideScope()
    {
        var fixture = Fixture();
        var withoutTimeline = P28AcquisitionScenario.Create(fixture.Stimulus.InitialState, fixture.Stimulus.Observations, fixture.Stimulus.Provenance);
        var report = fixture.Report with { ScenarioDigest = withoutTimeline.Digest };
        Assert.All(P28AcquisitionEnvelope.Compare(report, withoutTimeline, fixture.Query).Checkpoints,
            checkpoint => Assert.Equal("NoExplicitExtendedTimeline", checkpoint.Scope));
        var checkpoints = fixture.Report.Sequences[0].Checkpoints.ToArray();
        var last = checkpoints[^1];
        checkpoints[^1] = last with { Acquisition = last.Acquisition with { Status = 1 } };
        Assert.Equal("AcquisitionNotCompleted", Compare(fixture, checkpoints).Checkpoints[^1].Scope);
        checkpoints[^1] = last with { Acquisition = last.Acquisition with { StateAfter = last.Acquisition.StateAfter with { Data0217 = 0x80 } } };
        Assert.Equal("AlternativeModeOutsideScope", Compare(fixture, checkpoints).Checkpoints[^1].Scope);
    }

    [Fact]
    public void ComparisonPreservesOriginalM1hScenarioQueryProvenancePolicyAndConservativeVariants()
    {
        var fixture = Fixture();
        var scenarioBefore = fixture.Query.Scenario!.ToJson(false);
        var forwardBefore = JsonSerializer.Serialize(P28RpmPlanner.EvaluateForward(fixture.Query));
        var reportBefore = fixture.Report.ToJson(false);
        var comparison = P28AcquisitionEnvelope.Compare(fixture.Report, fixture.Stimulus, fixture.Query);
        Assert.Equal(P28RpmPlanner.ModelId, comparison.PlannerModelId);
        Assert.Equal(P28RpmPlanner.PolicyId, comparison.UnchangedPolicyId);
        Assert.Equal(fixture.Query.Scenario.Digest, comparison.ScenarioDigest);
        Assert.Equal(fixture.Query.QueryDigest, comparison.QueryDigest);
        Assert.Equal(fixture.Query.QuerySource, comparison.QuerySource);
        Assert.Equal(fixture.Query.RequestedRpm, comparison.RequestedRpm);
        Assert.Equal(fixture.Query.PermittedAssumptions, comparison.PermittedAssumptions);
        Assert.Equal(scenarioBefore, comparison.ScenarioSnapshot.GetRawText());
        Assert.Equal(forwardBefore, JsonSerializer.Serialize(comparison.ConservativeEnvelope));
        Assert.Equal(scenarioBefore, fixture.Query.Scenario.ToJson(false));
        Assert.Equal(reportBefore, fixture.Report.ToJson(false));
        Assert.Contains("No physical reachability", comparison.Qualification, StringComparison.Ordinal);
        Assert.False(comparison.PhysicalRpmAvailable);
    }

    [Fact]
    public void MismatchedStimulusOrPermissionsAndMissingM1hScenarioAreRejected()
    {
        var fixture = Fixture();
        Assert.Throws<ArgumentException>(() => P28AcquisitionEnvelope.Compare(fixture.Report with { ScenarioDigest = "different" }, fixture.Stimulus, fixture.Query));
        Assert.Throws<ArgumentException>(() => P28AcquisitionEnvelope.Compare(fixture.Report with { PermittedAssumptions = [] }, fixture.Stimulus, fixture.Query));
        var noScenario = P28RpmQuery.Create(null, fixture.Query.Slot.Id, 128, permittedAssumptions: fixture.Query.PermittedAssumptions);
        Assert.Throws<ArgumentException>(() => P28AcquisitionEnvelope.Compare(fixture.Report, fixture.Stimulus, noScenario));
    }

    private static P28AcquisitionEnvelopeReport Compare(TestFixture fixture, IReadOnlyList<P28AcquisitionCheckpoint> checkpoints) =>
        P28AcquisitionEnvelope.Compare(fixture.Report with { Sequences = new[] { fixture.Report.Sequences[0] with { Checkpoints = checkpoints } } }, fixture.Stimulus, fixture.Query);

    private static TestFixture Fixture(P28CaptureRational? period = null, IReadOnlyList<P28CaptureRational>? periods = null,
        int? tcerrIndex = null, IReadOnlyList<string>? permissions = null)
    {
        period ??= new(5, 2);
        var timeline = new P28CaptureTimeline("100", new(0, 1), periods ?? Enumerable.Repeat(period, 6).ToArray(),
            P28CaptureTimeline.FloorQuantization, "Constructed exact source for envelope unit tests only.");
        var observations = timeline.Generate((index, capture) => new(index, capture, 0,
            index == tcerrIndex ? (byte)0x96 : (byte)0x92, index == 0 ? 0 : (index - 1) % 6, true, 0, 0, true));
        var initial = new P28AcquisitionState(42, new ushort[] { 2, 2, 2, 2, 2, 2 }, 0, 0, 0, 0, 99, 0, 0, 77);
        var stimulus = P28AcquisitionScenario.Create(initial, observations, "Synthetic report checkpoint fixture.", timeline: timeline);
        var query = P28RpmPlannerTests.Query($"{60 * period.Denominator}/{period.Numerator}", permissions);
        var state = initial;
        var checkpoints = new List<P28AcquisitionCheckpoint>();
        var counts = new int[6];
        var mask = 0;
        foreach (var observation in observations)
        {
            var acquisition = P28AcquisitionModel.Evaluate(state, observation);
            state = acquisition.State;
            if (acquisition.SampleWrites.Count != 0) { counts[observation.Slot]++; mask |= 1 << observation.Slot; }
            var sum = state.Samples.Sum(value => (int)value);
            var produced = (ushort)(sum / 5);
            var compact = P28CompactModel.EvaluateHypothesis(produced, false);
            var observed = new P28AcquisitionObservedStep(0, acquisition.Disposition.ToString(), 20, P28AcquisitionModel.StopPc,
                acquisition.PeripheralAccesses, acquisition.SampleWrites, state, [], [], [], [], null);
            var g = Stage([produced & 255, produced >> 8, 0xA0]);
            var f = Stage([compact.Code, compact.ExtraBit ? 0xB0 : 0xA0]);
            checkpoints.Add(new(observation.Index, acquisition.SelectedTimestamp, observation.Slot, observed, g, f, null,
                state, query.PermittedAssumptions, mask, counts.ToArray()));
        }
        var emptyCounts = new P28AcquisitionStageCounts(0, 0, 0, 0, 0, 0, 0, 0, 0);
        var sequence = new P28AcquisitionSequenceComparison(0, "constructed-baseline", 0, observations.Count, observations.Count, 0, -1,
            counts.Sum(), mask, counts, mask == 63, emptyCounts, emptyCounts, emptyCounts, emptyCounts, checkpoints, [], query.PermittedAssumptions, false);
        var report = new P28AcquisitionValidationReport("1", "constructed-unit-test-report", 1, "constructed", "not-upstream-evidence", [],
            P28AcquisitionModel.ModelId, P28ProducerModel.ModelId, P28CompactModel.ModelId, P28AcquisitionValidator.ScheduledComposition,
            stimulus.Digest, JsonDocument.Parse(stimulus.ToJson(false)).RootElement.Clone(), "synthetic", RomImage.FromBytes(new byte[32768]).Hash,
            null, "synthetic-profile", "synthetic-binding", null, [], query.PermittedAssumptions, query.PermittedAssumptions, [sequence], null, [], [],
            false, true, false, false, false, FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady, []);
        return new(stimulus, query, report);
    }

    private static P28AcquisitionStageResult Stage(IReadOnlyList<int> outputs) => new(0, [], 1, 0, outputs, [], [], [], null);
    private sealed record TestFixture(P28AcquisitionScenario Stimulus, P28RpmQuery Query, P28AcquisitionValidationReport Report);
}
