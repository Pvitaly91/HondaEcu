using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class OracleFitRegressionTests
{
    [Theory]
    [InlineData(0, 255, OracleRoundingStatus.EquivalentOnDomain)]
    [InlineData(-128, 127, OracleRoundingStatus.Ambiguous)]
    [InlineData(-128, -1, OracleRoundingStatus.Ambiguous)]
    public void FloorAndTruncateEquivalenceRequiresDocumentedNonnegativeDomain(double minimum, double maximum, OracleRoundingStatus expected)
    {
        var result = OracleRoundingBehavior.Assess(new[] { RoundingPolicy.Floor, RoundingPolicy.Truncate },
            new OracleRoundingDomain(minimum, maximum, "Synthetic admissible unrounded-raw interval."));

        Assert.Equal(expected, result.Status);
        Assert.Equal(2, result.Policies.Count);
    }

    [Theory]
    [InlineData(2.5)]
    [InlineData(-2.5)]
    public void NearestAndToEvenDifferAtPositiveAndNegativeMidpoints(double midpoint)
    {
        var result = OracleRoundingBehavior.Assess(new[] { RoundingPolicy.Nearest, RoundingPolicy.ToEven },
            new OracleRoundingDomain(midpoint, midpoint, "Synthetic exact midpoint boundary."));

        Assert.Equal(OracleRoundingStatus.Ambiguous, result.Status);
    }

    [Fact]
    public void NearestAndToEvenCanBeProvenOnlyOnAnExplicitMidpointFreeInterval()
    {
        var policies = new[] { RoundingPolicy.Nearest, RoundingPolicy.ToEven };
        Assert.Equal(OracleRoundingStatus.Ambiguous, OracleRoundingBehavior.Assess(policies, null).Status);
        Assert.Equal(OracleRoundingStatus.EquivalentOnDomain, OracleRoundingBehavior.Assess(policies,
            new OracleRoundingDomain(2.1, 2.4, "Synthetic admissible interval excludes every midpoint.")).Status);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void MidpointObservationsEstablishAwayFromZeroForSignedAndUnsignedValues(bool negative)
    {
        using var fixture = new SyntheticFixture();
        var sign = negative ? -1 : 1;
        var requested = new[] { 10.5 * sign, 20.6 * sign, 30.2 * sign };
        var displayed = new[] { 11d * sign, 21d * sign, 30d * sign };
        var raw = displayed.Select(value => unchecked((byte)(sbyte)value)).ToArray();
        var (manifest, profile) = Create(fixture, requested, raw, displayedValues: displayed);

        var candidate = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single().Candidates.Single(item =>
            item.Offset == 100 && item.EncodingType == (negative ? ParameterEncodingType.RawS8 : ParameterEncodingType.RawU8));

        Assert.Equal(RoundingPolicy.Nearest, candidate.SelectedRoundingPolicy);
        Assert.Equal(new[] { RoundingPolicy.Nearest }, candidate.CompatibleRoundingPolicies);
    }

    [Fact]
    public void IdenticalRepeatedMeasurementRetainsCandidate()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d, 20d }, new byte[] { 10, 20, 30, 20 });

        var parameter = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single();

        Assert.Contains(parameter.Candidates, item => item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);
        var candidate = parameter.Candidates.Single(item => item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);
        Assert.Equal(3, candidate.IndependentTrainingPointCount);
        Assert.Equal(4, candidate.Observations.Count);
        Assert.Equal(1, parameter.RepeatedObservationCount);
        Assert.Equal(4, candidate.Observations.Select(item => item.ObservationId).Distinct().Count());
    }

    [Fact]
    public void QuantizedRequestsRetainCandidate()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10.8, 10.9, 20.7, 30.6 }, new byte[] { 10, 10, 20, 30 });

        var parameter = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single();

        Assert.Contains(parameter.Candidates, item => item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);
        Assert.Empty(parameter.Conflicts);
        var candidate = parameter.Candidates.Single(item => item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);
        Assert.Equal(3, candidate.IndependentTrainingPointCount);
        Assert.Equal(4, candidate.Observations.Count);
        Assert.Equal(new[] { RoundingPolicy.Floor, RoundingPolicy.Truncate }, candidate.CompatibleRoundingPolicies);
        Assert.Null(candidate.SelectedRoundingPolicy);
        Assert.Equal(OracleRoundingStatus.Ambiguous, candidate.RoundingAssessment.Status);
    }

    [Fact]
    public void AmbiguousReadOnlyExportPreservesPoliciesWithoutSelectingFirst()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 });
        var analysis = OracleAnalyzer.Analyze(manifest, profile);

        using var exported = JsonDocument.Parse(OracleAnalyzer.ExportCandidate(analysis, "test", 100, ParameterEncodingType.RawU8));

        Assert.Equal(JsonValueKind.Null, exported.RootElement.GetProperty("roundingPolicy").ValueKind);
        Assert.True(exported.RootElement.GetProperty("compatibleRoundingPolicies").GetArrayLength() > 1);
        Assert.False(exported.RootElement.GetProperty("writable").GetBoolean());
        Assert.All(analysis.Parameters.Single().Candidates, candidate => Assert.Null(candidate.SelectedRoundingPolicy));
        Assert.All(analysis.Parameters.Single().Candidates, candidate => Assert.Equal(OracleRoundingStatus.Ambiguous, candidate.RoundingAssessment.Status));
    }

    [Fact]
    public void CorrelatedSideEffectRemainsUnexplainedDespiteCandidateFit()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 }, correlatedSideEffect: true);

        var analysis = OracleAnalyzer.Analyze(manifest, profile);

        Assert.Contains(analysis.Parameters.Single().Candidates, item => item.Offset == 200);
        Assert.Contains(analysis.AdditionalChangedRanges, range => range.ContainsOffset(200));
        Assert.Contains(analysis.CandidateHypothesisRanges, range => range.ContainsOffset(200));
        Assert.Contains(analysis.UnexplainedChangedRanges, range => range.ContainsOffset(200));
        Assert.Empty(analysis.ExplainedChangedRanges);
    }

    [Fact]
    public void DeclaredDomainProvesFloorTruncateWithoutSelectingOneName()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10.9, 20.8, 30.7 }, new byte[] { 10, 20, 30 });
        manifest = manifest with
        {
            RoundingDomains = new Dictionary<string, OracleRoundingDomain>
            {
                ["test"] = new(0, 255, "Synthetic editor only accepts nonnegative unrounded raw values."),
            },
        };

        var candidate = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single().Candidates.Single(item =>
            item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);

        Assert.Equal(OracleRoundingStatus.EquivalentOnDomain, candidate.RoundingAssessment.Status);
        Assert.Null(candidate.SelectedRoundingPolicy);
        Assert.Equal(2, candidate.CompatibleRoundingPolicies.Count);
    }

    [Fact]
    public void NearIntegerBoundaryIsNotSilentlySnappedBeforeFloorEncoding()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 9.9999999999, 20.9, 30.9 }, new byte[] { 9, 20, 30 });

        var candidate = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single().Candidates.Single(item =>
            item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);

        Assert.Contains(RoundingPolicy.Floor, candidate.CompatibleRoundingPolicies);
        Assert.DoesNotContain(RoundingPolicy.Nearest, candidate.CompatibleRoundingPolicies);
        Assert.True(candidate.TrainingExactByteMatch);
    }

    [Fact]
    public void IntegerOnlySamplesDoNotProveFractionalRoundingEvenOnKnownPositiveDomain()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 });
        manifest = manifest with { RoundingDomains = new Dictionary<string, OracleRoundingDomain> { ["test"] = new(0, 255, "Synthetic interval") } };

        var candidate = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single().Candidates.Single(item =>
            item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);

        Assert.Equal(6, candidate.CompatibleRoundingPolicies.Count);
        Assert.Equal(OracleRoundingStatus.Ambiguous, candidate.RoundingAssessment.Status);
        Assert.Null(candidate.SelectedRoundingPolicy);
    }

    [Fact]
    public void ConflictingRepeatedRequestRetainsBothProvenances()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d, 20d }, new byte[] { 10, 20, 30, 21 });

        var parameter = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single();

        var conflict = Assert.Single(parameter.Conflicts);
        Assert.Equal(20, conflict.RequestedValue);
        Assert.Equal(2, conflict.RomPaths.Count);
        Assert.Equal(2, conflict.RomHashes.Distinct().Count());
        Assert.Equal(2, conflict.ObservationIds.Distinct().Count());
    }

    [Fact]
    public void InverseThreePointOverfitIsRetainedButFailsIndependentHoldoutWithoutRefitting()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 600d, 300d, 150d, 250d }, new byte[] { 10, 20, 40, 30 },
            displayedValues: new[] { 600d, 300d, 150d, 250d });
        manifest = manifest with { Cases = manifest.Cases.Select((item, index) => index == 3 ? item with { Role = OracleObservationRole.Holdout } : item).ToArray() };
        var trainingOnly = manifest with { Cases = manifest.Cases.Take(3).ToArray() };
        OracleCandidate Inverse(OracleManifest input) => OracleAnalyzer.Analyze(input, profile).Parameters.Single().Candidates.Single(item =>
            item.Offset == 100 && item.EncodingType == ParameterEncodingType.InverseU8);

        var discovery = Inverse(trainingOnly);
        var validated = Inverse(manifest);

        Assert.Equal(discovery.Numerator, validated.Numerator);
        Assert.Equal(discovery.OffsetConstant, validated.OffsetConstant);
        Assert.Equal(discovery.DenominatorOffset, validated.DenominatorOffset);
        Assert.Equal(3, validated.IndependentTrainingPointCount);
        Assert.Equal(3, validated.FreeCoefficientCount);
        Assert.Equal(1, validated.HoldoutPointCount);
        Assert.True(validated.FitScore > 0.999);
        Assert.True(validated.HoldoutMaximumAbsoluteError > 49);
        Assert.False(validated.HoldoutExactByteMatch);
        Assert.Equal(ValidationLevel.OracleObserved, validated.ValidationLevel);
        Assert.Contains("interpolate", validated.ExtrapolationWarning, StringComparison.OrdinalIgnoreCase);
        Assert.Empty(validated.Observations.Last().ExactBytePolicies);
    }

    [Fact]
    public void HoldoutDuplicateOfTrainingDoesNotBecomeIndependentValidation()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d, 20d }, new byte[] { 10, 20, 30, 20 });
        manifest = manifest with { Cases = manifest.Cases.Select((item, index) => index == 3 ? item with { Role = OracleObservationRole.Holdout } : item).ToArray() };

        var candidate = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single().Candidates.Single(item =>
            item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8);

        Assert.Equal(0, candidate.HoldoutPointCount);
        Assert.False(candidate.HoldoutExactByteMatch);
        Assert.False(candidate.Observations.Last().IndependentPoint);
        Assert.Equal(4, candidate.Observations.Count);
    }

    [Fact]
    public void VaryingU8BesideZeroPreservesWidthAndEndianAlternatives()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 });

        var parameter = OracleAnalyzer.Analyze(manifest, profile).Parameters.Single();

        Assert.Contains(parameter.Candidates, item => item.Offset == 100 && item.Width == 1);
        Assert.Contains(parameter.Candidates, item => item.Offset == 100 && item.Width == 2 && item.Endianness == Endianness.Little);
        Assert.Contains(parameter.Candidates, item => item.Offset == 100 && item.Width == 2 && item.Endianness == Endianness.Big);
        Assert.Equal(parameter.Candidates.Count, parameter.Candidates.Select(item => item.CandidateId).Distinct().Count());
    }

    [Fact]
    public void ManualSelectionRetainsAlternativesAndDoesNotExplainTheirBytes()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 }, correlatedSideEffect: true);
        var original = OracleAnalyzer.Analyze(manifest, profile);
        var id = original.Parameters.Single().Candidates.Single(item => item.Offset == 100 && item.EncodingType == ParameterEncodingType.RawU8).CandidateId;

        var selected = OracleAnalyzer.SelectCandidate(original, "test", id, "Manual review hypothesis, not independent evidence.");

        Assert.Equal(original.Parameters.Single().Candidates.Count, selected.Parameters.Single().Candidates.Count);
        Assert.Equal(id, selected.Parameters.Single().SelectedCandidateId);
        Assert.Empty(selected.ExplainedChangedRanges);
        Assert.Equal(original.UnexplainedChangedRanges, selected.UnexplainedChangedRanges);
    }

    [Fact]
    public void FitScoreAliasSupportsNewNameAndRejectsContradictoryLegacyValue()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 });
        var analysis = OracleAnalyzer.Analyze(manifest, profile);
        var node = JsonNode.Parse(analysis.ToJson())!;
        var candidate = node["parameters"]![0]!["candidates"]![0]!.AsObject();
        var score = candidate["fitScore"]!.GetValue<double>();
        candidate.Remove("confidence");

        Assert.Equal(score, OracleAnalysis.Parse(node.ToJsonString()).Parameters[0].Candidates[0].FitScore);
        candidate["confidence"] = 0.25;
        Assert.Throws<InvalidDataException>(() => OracleAnalysis.Parse(node.ToJsonString()));
    }

    [Fact]
    public void LegacyAnalysisRemainsReadableButDoesNotRetainImplicitRoundingChoice()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, profile) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 });
        var analysis = OracleAnalyzer.Analyze(manifest, profile);
        var legacy = analysis with { FormatVersion = "1.0", EvidenceBinding = null };

        var parsed = OracleAnalysis.Parse(legacy.ToJson());

        Assert.NotEmpty(parsed.MigrationWarnings);
        Assert.All(parsed.Parameters.Single().Candidates, candidate => Assert.Null(candidate.SelectedRoundingPolicy));
        Assert.Throws<InvalidDataException>(() => OracleAnalyzer.ExportCandidate(parsed, parsed.Parameters[0].Candidates[0].CandidateId));
    }

    [Fact]
    public void DirectCoreAnalyzeRejectsOutOfBoundsProfileChecksumRegion()
    {
        using var fixture = new SyntheticFixture();
        var (manifest, _) = Create(fixture, new[] { 10d, 20d, 30d }, new byte[] { 10, 20, 30 });
        var malformedProfile = new RomProfile("synthetic-fit", "Synthetic malformed profile", "Generated test", 32768,
            "synthetic-v1", experimental: true, requiresExplicitConfirmation: true,
            checksum: new ChecksumDefinition("unknown", ChecksumStatus.Unknown, 32768, 1, ValidationLevel.PublicDocumentation));

        Assert.Throws<ProfileValidationException>(() => OracleAnalyzer.Analyze(manifest, malformedProfile));
    }

    internal static (OracleManifest Manifest, RomProfile Profile) Create(SyntheticFixture fixture,
        IReadOnlyList<double> requested, IReadOnlyList<byte> raw, bool correlatedSideEffect = false,
        IReadOnlyList<double>? displayedValues = null)
    {
        var baseline = fixture.WriteRom("baseline.dat", new byte[32768]);
        var noOp = fixture.WriteRom("noop.dat", new byte[32768]);
        var profile = new RomProfile("synthetic-fit", "Synthetic fit fixture", "Generated algorithm test bytes",
            32768, "synthetic-v1", experimental: true, requiresExplicitConfirmation: true);
        var manifest = OracleManifestService.Create("Crome", "synthetic-unit-test", profile.Id, baseline, noOp, true);
        for (var index = 0; index < raw.Count; index++)
        {
            var bytes = new byte[32768];
            bytes[100] = raw[index];
            if (correlatedSideEffect)
            {
                bytes[200] = (byte)(raw[index] * 2);
            }

            manifest = OracleManifestService.AddCase(manifest, "test", requested[index], fixture.WriteRom($"case-{index}.dat", bytes),
                displayedValue: displayedValues?[index] ?? raw[index]);
        }

        return (manifest, profile);
    }
}
