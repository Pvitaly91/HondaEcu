using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28AcquisitionModelTests
{
    [Fact]
    public void FirstObservationUpdatesTimestampAndGuardWithoutReadingTconOrWritingSamples()
    {
        var initial = State() with { Data0128 = 0xA1, Data00AE = 255, Data00B6 = 0xB4 };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: 0x0012, irqh: 0x81, tcon2: 0x96));

        Assert.Equal(P28AcquisitionDisposition.FirstObservationNoWrite, result.Disposition);
        Assert.Equal(P28AcquisitionModel.StopPc, result.StopPc);
        Assert.Equal((ushort)0x0012, result.SelectedTimestamp);
        Assert.Equal((ushort)0x0012, result.State.PreviousTimestamp);
        Assert.Equal((byte)0xA9, result.State.Data0128);
        Assert.Equal((byte)0, result.State.Data00AE);
        Assert.Equal((byte)0xB5, result.State.Data00B6);
        Assert.Equal(initial.Data0136, result.State.Data0136);
        Assert.Equal(initial.Samples, result.State.Samples);
        Assert.Empty(result.SampleWrites);
        AssertReads(result, [0x003A, 16, 0, 0x0012], [0x0019, 8, 0, 0x81]);
        AssertUnchangedNonAcquisitionState(initial, result.State);
        Assert.Equal((byte)255, initial.Data00AE);
        Assert.Equal((byte)0xA1, initial.Data0128);
    }

    [Theory]
    [InlineData(0x8000)]
    [InlineData(0xFFFF)]
    public void FirstHighHalfTimestampDoesNotReadIrqOrTcon(int timestamp)
    {
        var initial = State() with { Data0128 = 0, Data00B6 = 0xA4 };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: (ushort)timestamp, irqh: 255, tcon2: 255));
        AssertReads(result, [0x003A, 16, 0, timestamp]);
        Assert.Equal((byte)0xA4, result.State.Data00B6);
        Assert.Empty(result.SampleWrites);
        Assert.Equal(initial.Samples, result.State.Samples);
    }

    [Fact]
    public void CounterWrapUsesUnsignedLowWordDifferenceAndDoesNotInferIrqFromWrap()
    {
        var initial = State() with { PreviousTimestamp = 0xFFF8, Data0128 = 8, Data00B6 = 0xA4 };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: 0x0008, slot: 2, irqh: 0, tcon2: 0x92));
        Assert.Equal(P28AcquisitionDisposition.IntervalWrite, result.Disposition);
        Assert.Equal((ushort)16, result.State.Samples[2]);
        Assert.Equal((ushort)16, result.State.Data0136);
        Assert.Equal((byte)0xA4, result.State.Data00B6);
        Assert.Equal(new[] { 0x0364, 16, 16 }, Assert.Single(result.SampleWrites));
        AssertReads(result, [0x003A, 16, 0, 8], [0x0019, 8, 0, 0], [0x0042, 8, 0, 0x92]);
    }

    [Theory]
    [InlineData(0x4000, 0x4000, 0x92)]
    [InlineData(0x4000, 0x4234, 0x96)]
    [InlineData(0xFFFE, 0x0001, 0x96)]
    public void ZeroDifferenceAndObservedTcErrBothWriteExplicitZero(int previous, int timestamp, int tcon)
    {
        var initial = State() with { PreviousTimestamp = (ushort)previous, Data0128 = 8 };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: (ushort)timestamp, slot: 4, tcon2: (byte)tcon));
        Assert.Equal(P28AcquisitionDisposition.InvalidZeroWrite, result.Disposition);
        Assert.Equal((ushort)0, result.State.Samples[4]);
        Assert.Equal((ushort)0, result.State.Data0136);
        Assert.Equal(new[] { 0x0368, 16, 0 }, Assert.Single(result.SampleWrites));
        Assert.Equal((ushort)timestamp, result.State.PreviousTimestamp);
        Assert.Equal(new[] { 0x0042, 8, 0, tcon }, result.PeripheralAccesses[^1]);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    public void EveryExplicitCallerIndexSelectsExactlyOneWordAndDoesNotScheduleTheNextIndex(int slot)
    {
        var initial = State() with { PreviousTimestamp = 0x3000, Data0128 = 0xF8 };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: 0x3234, slot: slot));
        Assert.Equal(slot, result.SlotIndex);
        Assert.Equal(new[] { 0x0360 + 2 * slot, 16, 0x0234 }, Assert.Single(result.SampleWrites));
        for (var index = 0; index < 6; index++)
        {
            Assert.Equal(index == slot ? (ushort)0x0234 : initial.Samples[index], result.State.Samples[index]);
        }
        AssertUnchangedNonAcquisitionState(initial, result.State);
        Assert.Equal((byte)0xF8, result.State.Data0128);
    }

    [Fact]
    public void SameValueStoreIsNotClassifiedAsNoWrite()
    {
        var initial = State() with { PreviousTimestamp = 1000, Samples = new ushort[] { 9, 8, 7, 50, 5, 4 }, Data0128 = 8 };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: 1050, slot: 3));
        Assert.Equal(initial.Samples, result.State.Samples);
        Assert.Equal(P28AcquisitionDisposition.IntervalWrite, result.Disposition);
        Assert.Equal(new[] { 0x0366, 16, 50 }, Assert.Single(result.SampleWrites));
    }

    [Theory]
    [InlineData(0x7FFF, 0x01, 0xA4, 0xA5, true)]
    [InlineData(0x7FFF, 0xFE, 0xA4, 0xA4, true)]
    [InlineData(0x8000, 0xFF, 0xA4, 0xA4, false)]
    [InlineData(0x0000, 0x00, 0xA5, 0xA5, true)]
    public void OverflowGuardDependsOnFreshTimestampHighAliasAndIrqBitZeroOnly(int timestamp, int irq, int guard, int expectedGuard, bool irqRead)
    {
        var initial = State() with { PreviousTimestamp = 0xFFFF, Data0128 = 8, Data00AE = 255, Data00B6 = (byte)guard };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: (ushort)timestamp, irqh: (byte)irq));
        Assert.Equal((ushort)timestamp, result.SelectedTimestamp);
        Assert.Equal((byte)expectedGuard, result.State.Data00B6);
        Assert.Equal((byte)0, result.State.Data00AE);
        Assert.Equal(irqRead, result.PeripheralAccesses.Any(read => read[0] == 0x0019));
        Assert.DoesNotContain(result.PeripheralAccesses, read => read[0] == 0x010F);
    }

    [Fact]
    public void RepeatedTransitionsConsumePriorStateInsteadOfReseedingEachObservation()
    {
        var initial = State() with { PreviousTimestamp = 9999, Data0128 = 0 };
        var first = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: 1000, slot: 2));
        var second = P28AcquisitionModel.Evaluate(first.State, Observation(index: 1, tmr2: 1040, slot: 2));
        var third = P28AcquisitionModel.Evaluate(second.State, Observation(index: 2, tmr2: 1100, slot: 2));
        Assert.Empty(first.SampleWrites);
        Assert.Equal((ushort)40, second.State.Samples[2]);
        Assert.Equal((ushort)60, third.State.Samples[2]);
        Assert.Equal((ushort)1040, second.State.PreviousTimestamp);
        Assert.Equal((ushort)1100, third.State.PreviousTimestamp);
        Assert.Equal((ushort)9999, initial.PreviousTimestamp);
        Assert.Equal(initial.Samples[2], first.State.Samples[2]);
    }

    [Fact]
    public void IndependentBranchesAndSnapshotsDoNotShareMutableInputSamples()
    {
        ushort[] samples = [1, 2, 3, 4, 5, 6];
        var initial = State() with { PreviousTimestamp = 100, Samples = samples, Data0128 = 8 };
        var snapshot = P28AcquisitionModel.Snapshot(initial);
        var left = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: 150, slot: 0));
        var right = P28AcquisitionModel.Evaluate(initial, Observation(tmr2: 170, slot: 1));
        samples[5] = 999;
        Assert.Equal(new ushort[] { 1, 2, 3, 4, 5, 6 }, snapshot.Samples);
        Assert.Equal(new ushort[] { 50, 2, 3, 4, 5, 6 }, left.State.Samples);
        Assert.Equal(new ushort[] { 1, 70, 3, 4, 5, 6 }, right.State.Samples);
        Assert.NotSame(initial.Samples, snapshot.Samples);
        Assert.NotSame(left.State.Samples, right.State.Samples);
        Assert.Throws<NotSupportedException>(() => ((IList<ushort>)snapshot.Samples)[0] = 88);
        Assert.Throws<NotSupportedException>(() => ((IList<ushort>)left.State.Samples)[0] = 88);
    }

    [Theory]
    [InlineData(0x04)]
    [InlineData(0xFF)]
    public void AlternativeModeStopsAtEntryWithoutPretendingToObservePeripherals(int mode)
    {
        var initial = State() with { Data011F = (byte)mode };
        var result = P28AcquisitionModel.Evaluate(initial, Observation(irqh: 255, tcon2: 255));
        Assert.Equal(P28AcquisitionDisposition.UnsupportedMode, result.Disposition);
        Assert.Equal(P28AcquisitionModel.EntryPc, result.StopPc);
        Assert.Null(result.SelectedTimestamp);
        Assert.Empty(result.PeripheralAccesses);
        Assert.Empty(result.SampleWrites);
        Assert.Equal(initial with { Samples = result.State.Samples }, result.State);
        Assert.Equal(initial.Samples, result.State.Samples);
        Assert.NotSame(initial.Samples, result.State.Samples);
    }

    [Fact]
    public void InvalidStateAndObservationDomainsAreRejectedBeforeEvaluation()
    {
        Assert.Throws<ArgumentNullException>(() => P28AcquisitionModel.Snapshot(null!));
        Assert.Throws<ArgumentException>(() => P28AcquisitionModel.Snapshot(State() with { Samples = null! }));
        foreach (var count in new[] { 0, 5, 7 })
        {
            Assert.Throws<ArgumentException>(() => P28AcquisitionModel.Snapshot(State() with { Samples = new ushort[count] }));
        }
        Assert.Throws<ArgumentNullException>(() => P28AcquisitionModel.ValidateObservation(null!));
        foreach (var observation in new[]
        {
            Observation() with { Index = -1 }, Observation() with { Index = 1024 },
            Observation() with { Slot = -1 }, Observation() with { Slot = 6 },
            Observation() with { ThresholdContext = -1 }, Observation() with { ThresholdContext = 2 },
            Observation() with { ThresholdPriorBits = -1 }, Observation() with { ThresholdPriorBits = 4 },
        })
        {
            Assert.Throws<ArgumentException>(() => P28AcquisitionModel.Evaluate(State(), observation));
        }
    }

    [Fact]
    public void ScenarioRoundTripIsVersionedDeterministicAndOwnsItsInputSnapshots()
    {
        ushort[] samples = [1, 2, 3, 4, 5, 6];
        var observations = new[] { Observation(), Observation(index: 1, tmr2: 1300, slot: 5) };
        var traces = new[] { 1 };
        var scenario = P28AcquisitionScenario.Create(State() with { Samples = samples }, observations, "Invented bounded test observations; not hardware evidence.", traces);
        var json = scenario.ToJson();
        var parsed = P28AcquisitionScenario.Parse(json);
        samples[0] = 65535;
        observations[0] = Observation(tmr2: 65535);
        traces[0] = 0;
        Assert.Equal(1, scenario.FormatVersion);
        Assert.Equal("explicit-capture-observation-stimulus", scenario.Purpose);
        Assert.Equal(json, scenario.ToJson());
        Assert.Equal(scenario.Digest, parsed.Digest);
        Assert.Equal(scenario.ToJson(false), parsed.ToJson(false));
        Assert.Equal((ushort)1, scenario.InitialState.Samples[0]);
        Assert.Equal((ushort)1200, scenario.Observations[0].Tmr2);
        Assert.Equal(new[] { 1 }, scenario.TraceObservationIndexes);
        Assert.Null(scenario.Timeline);
        Assert.Equal(scenario.Digest, P28AcquisitionScenario.Parse(scenario.ToJson(false)).Digest);
    }

    [Fact]
    public void ReplayRetainsOriginalInitialStateAndCompletePrefixWithOneRequestedTrace()
    {
        var observations = Enumerable.Range(0, 4).Select(index => Observation(index, (ushort)(1000 + index * 75), slot: index)).ToArray();
        var scenario = P28AcquisitionScenario.Create(State(), observations, "Synthetic replay", [0, 3]);
        var replay = scenario.ForReplay(2);
        Assert.Equal(scenario.InitialState.Samples, replay.InitialState.Samples);
        Assert.Equal(scenario.InitialState.PreviousTimestamp, replay.InitialState.PreviousTimestamp);
        Assert.Equal(observations.Take(3), replay.Observations);
        Assert.Equal(new[] { 2 }, replay.TraceObservationIndexes);
        Assert.Equal(scenario.Provenance, replay.Provenance);
        Assert.NotEqual(scenario.Digest, replay.Digest);
        Assert.Equal(4, scenario.Observations.Count);
        Assert.Throws<ArgumentOutOfRangeException>(() => scenario.ForReplay(-1));
        Assert.Throws<ArgumentOutOfRangeException>(() => scenario.ForReplay(4));
    }

    [Fact]
    public void ScenarioRequiresDenseBoundedObservationsExplicitProvenanceAndBoundedUniqueTraces()
    {
        Assert.Throws<ArgumentNullException>(() => P28AcquisitionScenario.Create(State(), null!, "test"));
        Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), [], "test"));
        Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), [Observation(index: 1)], "test"));
        Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), [Observation(), Observation()], "test"));
        Assert.Throws<ArgumentNullException>(() => P28AcquisitionScenario.Create(State(), [null!], "test"));
        foreach (var provenance in new[] { "", "   ", new string('x', 513) })
        {
            Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), [Observation()], provenance));
        }
        var observations = Enumerable.Range(0, 1024).Select(index => Observation(index)).ToArray();
        Assert.Equal(1024, P28AcquisitionScenario.Create(State(), observations, new string('x', 512), Enumerable.Range(0, 8).ToArray()).Observations.Count);
        Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), observations.Append(Observation()).ToArray(), "test"));
        foreach (var traces in new[] { new[] { -1 }, new[] { 1024 }, new[] { 0, 0 }, Enumerable.Range(0, 9).ToArray() })
        {
            Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), observations, "test", traces));
        }
    }

    [Theory]
    [InlineData("root")]
    [InlineData("initialState")]
    [InlineData("observation")]
    public void ScenarioRejectsUnknownMissingNullAndDuplicateFieldsAtEveryObjectLevel(string level)
    {
        var valid = ScenarioJson();
        var key = level == "root" ? "purpose" : level == "initialState" ? "previousTimestamp" : "tmr2";
        foreach (var mutation in new[] { "unknown", "missing", "null" })
        {
            var root = JsonNode.Parse(valid)!.AsObject();
            var target = level == "root" ? root : level == "initialState" ? root["initialState"]!.AsObject() : root["observations"]![0]!.AsObject();
            if (mutation == "unknown") { target["unreviewedPeripheralWrite"] = 1; }
            else if (mutation == "missing") { target.Remove(key); }
            else { target[key] = null; }
            Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse(root.ToJsonString()));
        }
        var duplicate = valid.Replace($"\"{key}\":", $"\"{key}\":0,\"{key}\":", StringComparison.Ordinal);
        Assert.NotEqual(valid, duplicate);
        Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse(duplicate));
    }

    [Fact]
    public void ScenarioRejectsWrongIdentityBadScalarDomainsAndOversizedUtf8()
    {
        foreach (var field in new[] { "formatVersion", "purpose" })
        {
            var root = JsonNode.Parse(ScenarioJson())!;
            if (field == "formatVersion") { root[field] = 2; }
            else { root[field] = "authoritative-hardware-calibration"; }
            Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse(root.ToJsonString()));
        }
        foreach (var (field, value) in new[] { ("tmr2", -1), ("tmr2", 65536), ("irqh", 256), ("tcon2", -1) })
        {
            var root = JsonNode.Parse(ScenarioJson())!;
            root["observations"]![0]![field] = value;
            Assert.Throws<JsonException>(() => P28AcquisitionScenario.Parse(root.ToJsonString()));
        }
        var wrongType = JsonNode.Parse(ScenarioJson())!;
        wrongType["observations"]![0]!["compose"] = "true";
        Assert.Throws<JsonException>(() => P28AcquisitionScenario.Parse(wrongType.ToJsonString()));
        Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse("[]"));
        Assert.ThrowsAny<JsonException>(() => P28AcquisitionScenario.Parse("{"));
        Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse(new string('x', 1_048_577)));
        Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse(new string('\u044f', 524_289)));
    }

    [Fact]
    public void ScenarioLoadUsesStrictUtf8AndRefusesOversizedFiles()
    {
        var path = Path.Combine(Path.GetTempPath(), $"hondaecu-acquisition-scenario-{Guid.NewGuid():N}.json");
        try
        {
            File.WriteAllText(path, ScenarioJson(), new UTF8Encoding(false, true));
            Assert.Equal(P28AcquisitionScenario.Parse(ScenarioJson()).Digest, P28AcquisitionScenario.Load(path).Digest);
            File.WriteAllBytes(path, [0xC3, 0x28]);
            Assert.Throws<DecoderFallbackException>(() => P28AcquisitionScenario.Load(path));
            File.WriteAllBytes(path, new byte[1_048_577]);
            Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Load(path));
        }
        finally { File.Delete(path); }
    }

    [Theory]
    [InlineData(0, 1, "65534,65536,65539,65541")]
    [InlineData(1, 2, "65534,65537,65539,65542")]
    public void RationalFiveHalvesAccumulatesBeforeFlooringAndPreservesOneSharedPhase(long numerator, long denominator, string expected)
    {
        var timeline = Timeline("65534", new(numerator, denominator), [new(5, 2), new(5, 2), new(5, 2)]);
        Assert.Equal(expected.Split(','), timeline.ExtendedTicks());
        var observations = timeline.Generate((index, capture) => Observation(index, capture, slot: 5 - index));
        Assert.Equal(expected.Split(',').Select(value => (ushort)(long.Parse(value, System.Globalization.CultureInfo.InvariantCulture) % 65536)), observations.Select(observation => observation.Tmr2));
        Assert.Equal(new[] { 5, 4, 3, 2 }, observations.Select(observation => observation.Slot));
        Assert.All(observations, observation => Assert.Equal((byte)0, observation.Irqh));
        Assert.All(observations, observation => Assert.Equal((byte)0x92, observation.Tcon2));
        var points = timeline.Describe(observations);
        Assert.True(points[1].LowWordWrapped);
        Assert.False(points[2].LowWordWrapped);
        Assert.Equal("NoExtendedPrehistory", points[0].IntervalScope);
        Assert.Null(points[0].ElapsedTicks);
        Assert.All(points.Skip(1), point => Assert.Equal("ShortPositiveInterval", point.IntervalScope));
    }

    [Fact]
    public void LowWordWrapIsDistinctFromLongIntervalAndDoesNotSynthesizeSuppliedFlags()
    {
        var timeline = Timeline("65534", new(0, 1), [new(2, 1), new(65535, 1), new(65536, 1)]);
        var observations = timeline.Generate((index, capture) => Observation(index, capture,
            irqh: index == 2 ? (byte)0xA1 : (byte)0xA0, tcon2: index == 3 ? (byte)0x96 : (byte)0x92));
        var points = timeline.Describe(observations);
        Assert.True(points[1].LowWordWrapped);
        Assert.Equal("2", points[1].ElapsedTicks);
        Assert.Equal("ShortPositiveInterval", points[1].IntervalScope);
        Assert.False(points[1].SuppliedTcerr);
        Assert.False(points[1].SuppliedOverflowPending);
        Assert.False(points[2].LowWordWrapped);
        Assert.Equal("65535", points[2].ElapsedTicks);
        Assert.Equal("LongIntervalAtLeastFFFF", points[2].IntervalScope);
        Assert.False(points[2].SuppliedTcerr);
        Assert.True(points[2].SuppliedOverflowPending);
        Assert.Contains("forced/unverified", points[2].FlagQualification, StringComparison.Ordinal);
        Assert.True(points[3].LowWordWrapped);
        Assert.Equal("LongIntervalAtLeastFFFF", points[3].IntervalScope);
        Assert.True(points[3].SuppliedTcerr);
        Assert.Contains("agrees", points[3].FlagQualification, StringComparison.Ordinal);
        Assert.Equal(observations[2].Tmr2, observations[3].Tmr2);
    }

    [Fact]
    public void ZeroAndSubtickPeriodsRemainExplicitZeroTickIntervals()
    {
        var timeline = Timeline("100", new(0, 1), [new(0, 1), new(1, 3), new(2, 3)]);
        Assert.Equal(new[] { "100", "100", "100", "101" }, timeline.ExtendedTicks());
        var observations = timeline.Generate((index, capture) => Observation(index, capture));
        var points = timeline.Describe(observations);
        Assert.Equal("ZeroTickInterval", points[1].IntervalScope);
        Assert.Equal("ZeroTickInterval", points[2].IntervalScope);
        Assert.Equal("ShortPositiveInterval", points[3].IntervalScope);
        Assert.Equal("0", points[1].ElapsedTicks);
        Assert.All(points, point => Assert.False(point.LowWordWrapped));
    }

    [Fact]
    public void TimelineRoundTripAndReplayPrefixPreserveSourceWithoutChangingCaptureSchedule()
    {
        var periods = new[] { new P28CaptureRational(5, 2), new P28CaptureRational(7, 3), new P28CaptureRational(1, 6) };
        var timeline = Timeline("98765", new(1, 2), periods);
        var observations = timeline.Generate((index, capture) => Observation(index, capture, slot: index) with { Compose = index % 2 == 0 });
        var scenario = P28AcquisitionScenario.Create(State(), observations, "Synthetic rational sequence", [1, 3], timeline);
        var replay = scenario.ForReplay(2);
        var parsed = P28AcquisitionScenario.Parse(scenario.ToJson());
        periods[0] = new(999, 1);
        Assert.NotNull(scenario.Timeline);
        Assert.NotNull(replay.Timeline);
        Assert.Equal(3, scenario.Timeline!.Periods.Count);
        Assert.Equal(new P28CaptureRational(5, 2), scenario.Timeline.Periods[0]);
        Assert.Equal(2, replay.Timeline!.Periods.Count);
        Assert.Equal(scenario.Timeline.ExtendedTicks().Take(3), replay.Timeline.ExtendedTicks());
        Assert.Equal(scenario.Observations.Take(3), replay.Observations);
        Assert.Equal(scenario.Timeline.Phase, replay.Timeline.Phase);
        Assert.Equal(scenario.Timeline.OriginTicks, replay.Timeline.OriginTicks);
        Assert.Equal(scenario.Timeline.Provenance, replay.Timeline.Provenance);
        Assert.Equal(scenario.Digest, parsed.Digest);
        Assert.Equal(scenario.ToJson(false), parsed.ToJson(false));
    }

    [Fact]
    public void TimelineRejectsCaptureMismatchWrongPeriodCountAndChangedScheduleIndexes()
    {
        var timeline = Timeline("100", new(0, 1), [new(5, 2)]);
        var correct = timeline.Generate((index, capture) => Observation(index, capture));
        var wrongCapture = correct.ToArray();
        wrongCapture[1] = wrongCapture[1] with { Tmr2 = (ushort)(wrongCapture[1].Tmr2 + 1) };
        Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), wrongCapture, "test", timeline: timeline));
        Assert.Throws<ArgumentException>(() => timeline.Describe(wrongCapture));
        Assert.Throws<ArgumentException>(() => P28AcquisitionScenario.Create(State(), [correct[0]], "test", timeline: timeline));
        Assert.Throws<ArgumentException>(() => timeline.Generate((index, capture) => Observation(index + 1, capture)));
        Assert.Throws<ArgumentException>(() => timeline.Generate((index, capture) => Observation(index, (ushort)(capture + 1))));
        Assert.Throws<ArgumentException>(() => timeline.Generate((index, capture) => Observation(index, capture, slot: 6)));
        Assert.Throws<ArgumentNullException>(() => timeline.Generate(null!));
    }

    [Fact]
    public void TimelineRejectsUnboundedOriginPhasePeriodsAndUnsupportedQuantization()
    {
        var valid = Timeline("0", new(0, 1), []);
        var invalid = new[]
        {
            valid with { OriginTicks = "-1" }, valid with { OriginTicks = "+1" },
            valid with { OriginTicks = "1.5" }, valid with { OriginTicks = "1e3" },
            valid with { OriginTicks = "1000000000001" }, valid with { OriginTicks = "00000000000000" },
            valid with { OriginTicks = null! }, valid with { Phase = null! },
            valid with { Phase = new(-1, 2) }, valid with { Phase = new(1, 0) },
            valid with { Phase = new(1, 1) }, valid with { Phase = new(2, 1) },
            valid with { Phase = new(1, 1_000_001) },
            valid with { Quantization = "round-nearest" }, valid with { Provenance = " " },
            valid with { Provenance = new string('x', 513) }, valid with { Periods = null! },
            valid with { Periods = Enumerable.Repeat(new P28CaptureRational(0, 1), 1024).ToArray() },
            valid with { Periods = new[] { new P28CaptureRational(-1, 1) } },
            valid with { Periods = new[] { new P28CaptureRational(1_000_000_000_001, 1) } },
            valid with { Periods = new[] { new P28CaptureRational(1, 0) } },
            valid with { Periods = new[] { new P28CaptureRational(1, 1_000_001) } },
        };
        foreach (var timeline in invalid) { Assert.Throws<ArgumentException>(() => timeline.ExtendedTicks()); }
        Assert.Throws<ArgumentNullException>(() => (valid with { Periods = new P28CaptureRational[] { null! } }).ExtendedTicks());
        Assert.Equal(new[] { "1000000000000", "2000000000000" },
            (valid with { OriginTicks = "1000000000000", Periods = new[] { new P28CaptureRational(1_000_000_000_000, 1) } }).ExtendedTicks());
    }

    [Fact]
    public void TimelineRejectsExcessiveCombinedRationalDenominator()
    {
        static bool IsPrime(int number)
        {
            for (var divisor = 2; divisor * divisor <= number; divisor++)
            {
                if (number % divisor == 0) { return false; }
            }
            return true;
        }
        var periods = Enumerable.Range(990_000, 10_000).Where(IsPrime).Take(260)
            .Select(prime => new P28CaptureRational(1, prime)).ToArray();
        Assert.Equal(260, periods.Length);
        var timeline = Timeline("0", new(0, 1), periods);
        Assert.Throws<ArgumentException>(() => timeline.ExtendedTicks());
    }

    [Theory]
    [InlineData("timeline")]
    [InlineData("phase")]
    [InlineData("period")]
    public void ScenarioTimelineRejectsUnknownMissingNullAndDuplicateFields(string level)
    {
        var timeline = Timeline("100", new(0, 1), [new(5, 2)]);
        var observations = timeline.Generate((index, capture) => Observation(index, capture));
        var valid = P28AcquisitionScenario.Create(State(), observations, "test", timeline: timeline).ToJson(false);
        var key = level == "timeline" ? "originTicks" : "numerator";
        foreach (var mutation in new[] { "unknown", "missing", "null" })
        {
            var root = JsonNode.Parse(valid)!.AsObject();
            var target = level == "timeline" ? root["timeline"]!.AsObject() : level == "phase" ? root["timeline"]!["phase"]!.AsObject() : root["timeline"]!["periods"]![0]!.AsObject();
            if (mutation == "unknown") { target["hardwareAuthority"] = true; }
            else if (mutation == "missing") { target.Remove(key); }
            else { target[key] = null; }
            Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse(root.ToJsonString()));
        }
        var duplicate = valid.Replace($"\"{key}\":", $"\"{key}\":0,\"{key}\":", StringComparison.Ordinal);
        Assert.Throws<InvalidDataException>(() => P28AcquisitionScenario.Parse(duplicate));
    }

    private static P28AcquisitionState State() => new(0x1234, new ushort[] { 11, 22, 33, 44, 55, 66 },
        0xA8, 0xFE, 0xB4, 0xA1, 0x7654, 0x62, 0xA7, 0xCAFE);

    private static P28CaptureObservation Observation(int index = 0, ushort tmr2 = 1200, byte irqh = 0,
        byte tcon2 = 0x92, int slot = 0) => new(index, tmr2, irqh, tcon2, slot, true, 1, 3, true);

    private static string ScenarioJson() => P28AcquisitionScenario.Create(State(), [Observation()], "Invented unit-test observations.").ToJson(false);

    private static P28CaptureTimeline Timeline(string origin, P28CaptureRational phase, IReadOnlyList<P28CaptureRational> periods) =>
        new(origin, phase, periods, P28CaptureTimeline.FloorQuantization, "Exact invented mathematical source; not a hardware capture.");

    private static void AssertReads(P28AcquisitionModelResult result, params int[][] expected)
    {
        Assert.Equal(expected.Length, result.PeripheralAccesses.Count);
        for (var index = 0; index < expected.Length; index++) { Assert.Equal(expected[index], result.PeripheralAccesses[index]); }
    }

    private static void AssertUnchangedNonAcquisitionState(P28AcquisitionState before, P28AcquisitionState after)
    {
        Assert.Equal(before.Data011F, after.Data011F);
        Assert.Equal(before.PreviousT, after.PreviousT);
        Assert.Equal(before.Data0217, after.Data0217);
        Assert.Equal(before.Data0231, after.Data0231);
    }
}
