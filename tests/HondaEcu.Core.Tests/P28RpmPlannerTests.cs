using System.Numerics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28RpmPlannerFixture
{
    public P28RpmQuery Query { get; } = P28RpmPlannerTests.Query("60/1000");
    public P28RpmPlanningReport Report { get; }
    public P28RpmPlannerFixture() => Report = P28RpmPlanner.Analyze(Query);
}

public sealed class P28RpmPlannerTests : IClassFixture<P28RpmPlannerFixture>
{
    private const string Slot = "context_0.pair_0.state_0_threshold";
    private readonly P28RpmPlannerFixture fixture;
    public P28RpmPlannerTests(P28RpmPlannerFixture fixture) => this.fixture = fixture;

    internal static string ScenarioJson(bool legacyRpm = false)
    {
        var quantities = new JsonObject();
        void Add(string key, string value, string unit) => quantities.Add(key, new JsonObject
        {
            ["numerator"] = value,
            ["denominator"] = "1",
            ["unit"] = unit,
            ["provenance"] = "Invented mathematical test, not measured hardware",
            ["evidence"] = "analyst-supplied",
        });
        Add("clockHz", "1", "Hz");
        Add("timerClockDivisor", "1", "1");
        Add("eventsPerCrankRev", "1", "events/crank-revolution");
        Add("eventsPerSample", "1", "events/sample");
        if (legacyRpm) { Add("rpm", "3", "crank-revolutions/minute"); }
        return new JsonObject { ["formatVersion"] = 1, ["scope"] = "uniform-normal-intervals", ["quantities"] = quantities }.ToJsonString();
    }

    internal static P28RpmQuery Query(string rpm, IReadOnlyList<string>? permissions = null, string slot = Slot) =>
        P28RpmQuery.Create(P28RpmScenario.Parse(ScenarioJson()), slot, 128, rpm, "Invented target query",
            permissions ?? [P28ProducerModel.AddEr1Assumption, P28RpmPlanner.AddEr3Assumption]);

    [Fact]
    public void MissingScenarioHasNoNumericResultsOrDefaults()
    {
        var report = P28RpmPlanner.Analyze(P28RpmQuery.Create(null, Slot, 128));
        Assert.Equal("Unavailable", report.Status);
        Assert.Null(report.Forward);
        Assert.Null(report.SupportedNormalDomain);
        Assert.Empty(report.Inverse);
        Assert.Empty(report.BestCandidates);
        Assert.Contains(report.UnavailableReasons, reason => reason.Contains("clockHz", StringComparison.Ordinal));
        Assert.False(report.PhysicalRpmAvailable);
        Assert.Equal("NotRun", report.HardwareStatus);
    }

    [Fact]
    public void LegacyScalingAndExplicitQueryRemainSeparateImmutableSnapshots()
    {
        var scenario = P28RpmScenario.Parse(ScenarioJson(legacyRpm: true));
        var legacy = P28RpmQuery.Create(scenario, Slot, 128);
        var changed = P28RpmQuery.Create(scenario, Slot, 128, "6/2", "Separate analyst request");
        Assert.Equal("3", legacy.RequestedRpm!.Numerator);
        Assert.Equal("3", changed.RequestedRpm!.Numerator);
        Assert.Equal("ExplicitSnapshotOfLegacyScalingRpm", legacy.QuerySource);
        Assert.Equal("ExplicitQueryOverride", changed.QuerySource);
        Assert.NotEqual(legacy.QueryDigest, changed.QueryDigest);
        Assert.Equal(scenario.Digest, P28RpmScenario.Parse(ScenarioJson()).Digest);
        Assert.Equal(scenario.Digest, P28RpmScenario.Parse(scenario.ToJson()).Digest);
        using var oldDocument = JsonDocument.Parse(ScenarioJson(legacyRpm: true));
        Assert.NotNull(P28PhysicalScaling.AnalyzeDocument(oldDocument.RootElement).Preview);
        using var newDocument = JsonDocument.Parse(ScenarioJson());
        Assert.Throws<InvalidDataException>(() => P28PhysicalScaling.AnalyzeDocument(newDocument.RootElement));
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    [InlineData("1.5")]
    [InlineData("1/0")]
    [InlineData("1/2/3")]
    [InlineData("1000000000001")]
    public void QueryRejectsInvalidExactRationals(string value) => Assert.Throws<ArgumentException>(() => Query(value));

    [Fact]
    public void ScenarioUnitsDuplicatesUnknownFieldsAndMissingProvenanceAreRejected()
    {
        var input = JsonNode.Parse(ScenarioJson())!;
        input["quantities"]!["clockHz"]!["unit"] = "MHz";
        Assert.Throws<InvalidDataException>(() => P28RpmScenario.Parse(input.ToJsonString()));
        input = JsonNode.Parse(ScenarioJson())!;
        input["quantities"]!["eventsPerSample"]!["provenance"] = "";
        Assert.Throws<InvalidDataException>(() => P28RpmScenario.Parse(input.ToJsonString()));
        Assert.Throws<InvalidDataException>(() => P28RpmScenario.Parse(ScenarioJson().Replace("\"formatVersion\":1", "\"formatVersion\":1,\"formatVersion\":1", StringComparison.Ordinal)));
        Assert.Throws<ArgumentException>(() => P28RpmQuery.Create(P28RpmScenario.Parse(ScenarioJson()), Slot, 1, "1"));
        Assert.Throws<ArgumentException>(() => Query("1", ["allow-everything"]));
        Assert.Throws<InvalidDataException>(() => P28RpmScenario.Parse("{\"formatVersion\":1,\"scope\":\"uniform-normal-intervals\",\"quantities\":[]}"));
    }

    [Fact]
    public void CounterfactualConfigurationIsExplicitWithoutRejectingMathematics()
    {
        var scenario = P28RpmScenario.Parse(ScenarioJson());
        Assert.Contains("Counterfactual", scenario.ConfigurationCompatibility);
        Assert.False(scenario.PhysicalRpmAvailable);
        Assert.NotEmpty(scenario.UnverifiedHardwareDependencies);
        var input = JsonNode.Parse(ScenarioJson())!;
        input["quantities"]!["timerClockDivisor"]!["numerator"] = "64";
        input["quantities"]!["timerClockDivisor"]!["denominator"] = "2";
        Assert.DoesNotContain("Counterfactual", P28RpmScenario.Parse(input.ToJsonString()).ConfigurationCompatibility);
    }

    [Theory]
    [InlineData("3", "20/1", "20", "20", 1)]
    [InlineData("6/5", "50/1", "50", "50", 1)]
    [InlineData("120/41", "41/2", "20", "21", 64)]
    public void ExactTickAndQuantizationBoundaries(string rpm, string ticks, string floor, string ceiling, int configurations)
    {
        var preview = P28RpmPlanner.EvaluateForward(Query(rpm), 100)!;
        Assert.Equal(ticks, preview.IdealTicksPerSample);
        Assert.Equal(floor, preview.FloorTicks);
        Assert.Equal(ceiling, preview.CeilingTicks);
        Assert.Equal(configurations, preview.Variants.Count);
        Assert.Equal(configurations == 1, preview.IntegralTicks);
        Assert.Contains("not a probability", preview.EnvelopeQualification);
        Assert.All(preview.Variants, variant => Assert.False(variant.Producer!.S));
    }

    [Fact]
    public void NontrivialRationalQuantitiesUseExactDimensionalConversion()
    {
        var input = JsonNode.Parse(ScenarioJson())!;
        void Set(string key, string numerator, string denominator)
        {
            input["quantities"]![key]!["numerator"] = numerator;
            input["quantities"]![key]!["denominator"] = denominator;
        }
        Set("clockHz", "1001", "7");
        Set("timerClockDivisor", "32", "3");
        Set("eventsPerCrankRev", "7", "2");
        Set("eventsPerSample", "5", "3");
        var query = P28RpmQuery.Create(P28RpmScenario.Parse(input.ToJsonString()), Slot, 128, "13/11", "Invented fractional dimensional check",
            [P28ProducerModel.AddEr1Assumption, P28RpmPlanner.AddEr3Assumption]);
        var preview = P28RpmPlanner.EvaluateForward(query)!;
        Assert.Equal("429/32", preview.TimerHz);
        Assert.Equal("9075/28", preview.IdealTicksPerSample);
        Assert.Equal("324", preview.FloorTicks);
        Assert.Equal("325", preview.CeilingTicks);
        Assert.Equal(new ushort[] { 388, 389, 390 }, preview.Variants.Select(variant => variant.Producer!.T).Distinct().Order());
    }

    [Fact]
    public void ValidMaximalTIsNotFallbackAndMixedFallbackIsNotDropped()
    {
        var exact = P28RpmPlanner.EvaluateForward(Query("60/54613"))!;
        Assert.True(exact.AllVariantsNormal);
        Assert.Equal(ushort.MaxValue, exact.Variants[0].Producer!.T);
        Assert.Equal(P28ProducerDisposition.NewValue, exact.Variants[0].Producer!.Disposition);
        Assert.False(exact.Variants[0].Producer!.FallbackFlag);
        var mixed = P28RpmPlanner.EvaluateForward(Query("120/109227"))!;
        Assert.False(mixed.AllVariantsNormal);
        Assert.Equal(64, mixed.Variants.Count);
        Assert.Equal(7, mixed.Variants.Count(value => value.Producer!.Disposition == P28ProducerDisposition.NewValue));
        Assert.Equal(57, mixed.Variants.Count(value => value.Producer!.Disposition == P28ProducerDisposition.QuotientOverflowFallback));
        var invalid = P28RpmPlanner.EvaluateForward(Query("60/65535"))!;
        Assert.Single(invalid.Variants);
        Assert.Equal("InvalidCapture", invalid.Variants[0].Status);
        Assert.Null(invalid.Variants[0].Producer);
    }

    [Fact]
    public void ZeroSampleEnvelopeAndStrictAssumptionsAreExplicit()
    {
        var zero = P28RpmPlanner.EvaluateForward(Query("120", []))!;
        Assert.Equal(64, zero.Variants.Count);
        Assert.Equal(32, zero.Variants.Count(value => value.Producer!.Disposition == P28ProducerDisposition.ZeroSampleFallback));
        Assert.Equal(32, zero.Variants.Count(value => !value.Producer!.Resolved));
        Assert.Empty(zero.UsedAssumptions);
        var strict = P28RpmPlanner.EvaluateForward(Query("60/1000", [P28RpmPlanner.AddEr3Assumption]))!;
        Assert.False(strict.Variants[0].Producer!.Resolved);
        Assert.Null(strict.Variants[0].Compact);
        Assert.Empty(strict.UsedAssumptions);
        var er1 = P28RpmPlanner.EvaluateForward(Query("60/1000", [P28ProducerModel.AddEr1Assumption]))!;
        Assert.True(er1.Variants[0].Producer!.Resolved);
        Assert.False(er1.Variants[0].Compact!.Value.Resolved);
        Assert.Equal(new[] { P28ProducerModel.AddEr1Assumption }, er1.UsedAssumptions);
        Assert.Equal(2, fixture.Report.Forward!.UsedAssumptions.Count);
    }

    [Fact]
    public void ThresholdStrictEqualityAndProducerSDoNotBorrowPriorState()
    {
        var preview = P28RpmPlanner.EvaluateForward(Query("60/1000", slot: "context_1.pair_1.state_1_threshold"))!;
        var code = preview.Variants[0].Compact!.Value.Code!.Value;
        var equal = P28RpmPlanner.EvaluateForward(Query("60/1000"), code)!;
        Assert.False(equal.Variants[0].NewPredicate);
        Assert.False(preview.Variants[0].Producer!.S);
        Assert.Equal(P28RpmPlanner.EvaluateForward(Query("60/1000"))!.Variants[0].Compact, preview.Variants[0].Compact);
    }

    [Fact]
    public void EveryRawCandidateHasExactRegionsAndAllTiesAreRetained()
    {
        var report = fixture.Report;
        Assert.Equal(256, report.Inverse.Count);
        Assert.Equal(Enumerable.Range(0, 256).Select(value => (byte)value), report.Inverse.Select(value => value.RawValue));
        Assert.False(report.Inverse[0].SimpleSelectable);
        Assert.Contains(report.Inverse[0].IneligibilityReasons, reason => reason.Contains("AlwaysTrue", StringComparison.Ordinal));
        Assert.False(report.Inverse[255].SimpleSelectable);
        Assert.Contains(report.Inverse[255].IneligibilityReasons, reason => reason.Contains("AlwaysFalse", StringComparison.Ordinal));
        Assert.All(report.Inverse.Skip(1).Take(254), candidate => Assert.True(candidate.SimpleSelectable));
        Assert.Equal("NondecreasingCodeWithRpmWithinSupportedDomain", report.MonotonicityStatus);
        var errors = report.Inverse.Where(candidate => candidate.SimpleSelectable).Select(candidate => Number.Parse(candidate.MinimaxError!)).ToArray();
        var minimum = errors.Aggregate((left, right) => left.CompareTo(right) < 0 ? left : right);
        Assert.Equal(report.Inverse.Where(candidate => candidate.SimpleSelectable && Number.Parse(candidate.MinimaxError!).CompareTo(minimum) == 0).Select(candidate => candidate.RawValue),
            report.BestCandidates.Select(candidate => candidate.RawValue));
        Assert.All(report.Inverse.Where(candidate => candidate.SimpleSelectable), candidate =>
        {
            var mixed = Assert.Single(candidate.Regions.Where(region => region.State == P28RpmRegionState.Mixed));
            Assert.False(mixed.Interval.LowerInclusive);
            Assert.False(mixed.Interval.UpperInclusive);
            Assert.True(candidate.TransitionBand!.LowerInclusive);
            Assert.True(candidate.TransitionBand.UpperInclusive);
        });
    }

    [Fact]
    public void ExactMinimaxTieKeepsBothCandidatesWithoutDisplayOrFirstRawTieBreak()
    {
        // Independently calculated witnesses: uniform155 -> T186 -> Code255;
        // uniform156 -> T187 -> Code254; uniform199 -> T238 -> Code254;
        // uniform200 -> T240 -> Code253. Thus the two outer RPM endpoints
        // are 60/200 and60/155. Their midpoint is213/620, error27/620.
        var report = P28RpmPlanner.Analyze(Query("213/620"));
        Assert.Equal(new byte[] { 253, 254 }, report.BestCandidates.Select(candidate => candidate.RawValue));
        Assert.All(report.BestCandidates, candidate => Assert.Equal("27/620", candidate.MinimaxError));
        Assert.Equal(new P28RpmInterval("3/10", "60/199", true, true), report.Inverse[253].TransitionBand);
        Assert.Equal(new P28RpmInterval("5/13", "12/31", true, true), report.Inverse[254].TransitionBand);
        Assert.All(report.BestCandidates, candidate => Assert.True(candidate.IsBest));
        Assert.Equal(report.ComputeDigest(), report.ComputeDigest());
    }

    [Fact]
    public void InverseAgreesWithIndependentForwardEnumerationOnSmallDomainAndLargeBoundaries()
    {
        // Expected classifications use only the public forward path, never the inverse
        // partition helper. Include all raw thresholds at points and open-cell interiors.
        var values = Enumerable.Range(1, 32).Concat(new[] { 154, 155, 194, 195, 390, 781, 1000, 1562, 3124, 3125, 10000, 54612, 54613 }).Distinct();
        foreach (var ticks in values)
        {
            Check($"60/{ticks}");
            if (ticks < 54613) { Check($"120/{2 * ticks + 1}"); }
        }
        void Check(string rpm)
        {
            var preview = P28RpmPlanner.EvaluateForward(Query(rpm))!;
            var value = Number.Parse(rpm);
            foreach (var candidate in fixture.Report.Inverse)
            {
                var predicates = preview.Variants.Select(variant => variant.Compact!.Value.Code!.Value > candidate.RawValue).Distinct().ToArray();
                var expected = predicates.Length == 2 ? P28RpmRegionState.Mixed : predicates[0] ? P28RpmRegionState.AllTrue : P28RpmRegionState.AllFalse;
                var region = Assert.Single(candidate.Regions.Where(item => Contains(item.Interval, value)));
                Assert.Equal(expected, region.State);
            }
        }
    }

    [Fact]
    public void EveryTransitionEndpointMatchesForwardAndNoDisplayRoundingAffectsChoice()
    {
        foreach (var band in fixture.Report.Inverse.Where(candidate => candidate.SimpleSelectable).Select(candidate => candidate.TransitionBand!).Distinct())
        {
            var low = P28RpmPlanner.EvaluateForward(Query(band.Lower))!;
            var high = P28RpmPlanner.EvaluateForward(Query(band.Upper!))!;
            Assert.Single(low.Variants);
            Assert.Single(high.Variants);
            foreach (var candidate in fixture.Report.Inverse.Where(candidate => candidate.TransitionBand == band))
            {
                Assert.True(low.Variants[0].Compact!.Value.Code <= candidate.RawValue);
                Assert.True(high.Variants[0].Compact!.Value.Code > candidate.RawValue);
            }
        }
        var before = fixture.Report.ComputeDigest();
        foreach (var candidate in fixture.Report.Inverse.Where(candidate => candidate.SimpleSelectable))
        {
            // Formatting is intentionally outside the mathematics and cannot mutate it.
            _ = double.Parse(candidate.MinimaxError!.Split('/')[0], System.Globalization.CultureInfo.InvariantCulture).ToString("F0", System.Globalization.CultureInfo.InvariantCulture);
        }
        Assert.Equal(before, fixture.Report.ComputeDigest());
    }

    [Fact]
    public void UnresolvedFullDomainCannotSelectEvenKnownLocalBand()
    {
        var strict = P28RpmPlanner.Analyze(Query("3", []));
        Assert.Empty(strict.BestCandidates);
        Assert.Equal("Unresolved", strict.Status);
        Assert.Empty(strict.UsedAssumptions);
        var er1 = P28RpmPlanner.Analyze(Query("3", [P28ProducerModel.AddEr1Assumption]));
        Assert.Empty(er1.BestCandidates);
        Assert.All(er1.Inverse, candidate => Assert.False(candidate.SimpleSelectable));
        Assert.Contains(er1.Inverse[254].Regions, region => region.State == P28RpmRegionState.Unknown);
        foreach (var raw in new[] { 0, 255 })
        {
            Assert.Contains(er1.Inverse[raw].Regions, region => region.State == P28RpmRegionState.Unknown);
            Assert.DoesNotContain(er1.Inverse[raw].IneligibilityReasons, reason => reason.Contains("AlwaysTrueInSupportedDomain", StringComparison.Ordinal) || reason.Contains("AlwaysFalseInSupportedDomain", StringComparison.Ordinal));
            Assert.Contains(er1.Inverse[raw].IneligibilityReasons, reason => reason.Contains("unresolved regions prevent", StringComparison.Ordinal));
        }
    }

    [Fact]
    public void InvalidRequestedEnvelopeCannotBecomeNearestAutomaticCandidate()
    {
        var report = P28RpmPlanner.Analyze(Query("120/109227"));
        Assert.Equal("InvalidRequestedDomain", report.Status);
        Assert.Empty(report.BestCandidates);
        Assert.Equal(256, report.Inverse.Count);
        Assert.All(report.Inverse, candidate => Assert.False(candidate.SimpleSelectable));
    }

    [Fact]
    public async Task CancellationIsObservedBeforeAndDuringPartition()
    {
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        Assert.Throws<OperationCanceledException>(() => P28RpmPlanner.Analyze(fixture.Query, cancelled.Token));
        using var during = new CancellationTokenSource();
        during.CancelAfter(TimeSpan.FromMilliseconds(10));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => Task.Run(() => P28RpmPlanner.Analyze(fixture.Query, during.Token)));
    }

    private static bool Contains(P28RpmInterval interval, Number value)
    {
        var lower = value.CompareTo(Number.Parse(interval.Lower));
        if (lower < 0 || lower == 0 && !interval.LowerInclusive) { return false; }
        if (interval.Upper is null) { return true; }
        var upper = value.CompareTo(Number.Parse(interval.Upper));
        return upper < 0 || upper == 0 && interval.UpperInclusive;
    }

    private readonly record struct Number(BigInteger Numerator, BigInteger Denominator) : IComparable<Number>
    {
        public static Number Parse(string text)
        {
            var fields = text.Split('/');
            return new(BigInteger.Parse(fields[0], System.Globalization.CultureInfo.InvariantCulture), fields.Length == 1 ? BigInteger.One : BigInteger.Parse(fields[1], System.Globalization.CultureInfo.InvariantCulture));
        }
        public int CompareTo(Number other) => (Numerator * other.Denominator).CompareTo(other.Numerator * Denominator);
    }
}
