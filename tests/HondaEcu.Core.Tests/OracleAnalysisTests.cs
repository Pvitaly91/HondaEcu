using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class OracleAnalysisTests
{
    [Fact]
    public void ManifestSeparatesNoOpNormalizationAndUpdatesAtomically()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false);
        var manifestPath = fixture.PathFor("oracle.json");

        OracleManifestService.Save(setup.Manifest, manifestPath);
        var loaded = OracleManifest.Load(manifestPath);
        var updated = OracleManifestService.AddCase(loaded, "other", 1, setup.CasePaths[0]);
        OracleManifestService.Save(updated, manifestPath, overwrite: true);

        Assert.Contains(loaded.NoOpNormalizationRanges, range => range.Offset == 50 && range.Length == 1);
        Assert.Equal(setup.Manifest.Cases.Count + 1, OracleManifest.Load(manifestPath).Cases.Count);
        Assert.DoesNotContain(Directory.EnumerateFiles(fixture.DirectoryPath), path => path.EndsWith(".tmp", StringComparison.Ordinal));
    }

    [Fact]
    public void FindsAllSupportedLinearCandidatesFromThreeCases()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false);

        var analysis = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile);
        var parameter = Assert.Single(analysis.Parameters);
        var candidate = Assert.Single(parameter.Candidates.Where(item =>
            item.Offset == 100 && item.Width == 1 && item.EncodingType == ParameterEncodingType.LinearU8));

        Assert.Equal(10, candidate.Scale, 6);
        Assert.Equal(0, candidate.OffsetConstant, 6);
        Assert.Equal(0, candidate.MaximumAbsoluteError, 6);
        Assert.Equal(ValidationLevel.OracleObserved, candidate.ValidationLevel);
    }

    [Fact]
    public void UsesReopenedDisplayedValueForFitAndRoundingEvidence()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false, requestedValues: new[] { 505d, 1006d, 1503d },
            displayedValues: new double?[] { 510d, 1010d, 1500d },
            caseRawValues: new byte[] { 51, 101, 150 });

        var candidate = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile).Parameters.Single().Candidates.Single(item =>
            item.Offset == 100 && item.EncodingType == ParameterEncodingType.LinearU8);

        Assert.Equal(10, candidate.Scale, 6);
        Assert.Equal(new[] { 510d, 1010d, 1500d }, candidate.EngineeringValues);
    }

    [Fact]
    public void FindsInversePeriodCandidateFromThreeCases()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: true);

        var candidates = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile).Parameters.Single().Candidates;
        var candidate = Assert.Single(candidates.Where(item =>
            item.Offset == 100 && item.Width == 1 && item.EncodingType == ParameterEncodingType.InverseU8));

        Assert.Equal(6000, candidate.Numerator, 4);
        Assert.Equal(0, candidate.DenominatorOffset, 4);
        Assert.Equal(0, candidate.OffsetConstant, 4);
        Assert.True(candidate.Confidence > 0.99);
    }

    [Fact]
    public void ExcludesNoOpAndChecksumBytesFromCandidatesAndKeepsThemOutOfResidualRanges()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false);

        var analysis = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile);
        var candidates = analysis.Parameters.Single().Candidates;

        Assert.DoesNotContain(candidates, candidate => candidate.Offset == 50 || candidate.Offset == 60);
        Assert.DoesNotContain(analysis.AdditionalChangedRanges, range => range.ContainsOffset(50));
        Assert.DoesNotContain(analysis.AdditionalChangedRanges, range => range.ContainsOffset(60));
        Assert.Contains(analysis.AdditionalChangedRanges, range => range.ContainsOffset(70));
        Assert.Contains(analysis.ExcludedChecksumRegions, range => range.Contains(60));
        Assert.Contains(analysis.ObservedChecksumChangedRanges, range => range.ContainsOffset(60));
    }

    [Fact]
    public void ParameterCanStillBeFoundWhenItsByteAlsoAppearsInNoOpNormalization()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false, parameterOffset: 50);

        var candidates = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile).Parameters.Single().Candidates;

        Assert.Contains(candidates, candidate => candidate.Offset == 50 && candidate.EncodingType == ParameterEncodingType.LinearU8);
    }

    [Fact]
    public void ReportsUnexplainedCaseValueAtNoOpNormalizedAddressAsResidual()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false, normalizedAddressCaseValue: 0xBB);

        var analysis = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile);

        Assert.DoesNotContain(analysis.Parameters.Single().Candidates, candidate => candidate.Offset == 50);
        Assert.Contains(analysis.AdditionalChangedRanges, range => range.ContainsOffset(50));
    }

    [Fact]
    public void RecomputesAndRejectsStaleManifestDiffRanges()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false);
        var staleNoOp = setup.Manifest with { NoOpNormalizationRanges = Array.Empty<DiffRange>() };
        var firstCase = setup.Manifest.Cases[0] with { DiffRanges = Array.Empty<DiffRange>() };
        var staleCase = setup.Manifest with { Cases = setup.Manifest.Cases.Select((item, index) => index == 0 ? firstCase : item).ToArray() };

        Assert.Throws<InvalidDataException>(() => OracleAnalyzer.Analyze(staleNoOp, setup.Profile));
        Assert.Throws<InvalidDataException>(() => OracleAnalyzer.Analyze(staleCase, setup.Profile));
    }

    [Fact]
    public void RefusesCandidateInferenceWhenPluginsWereNotDisabled()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateCases(fixture, inverse: false);

        var exception = Assert.Throws<InvalidOperationException>(() =>
            OracleAnalyzer.Analyze(setup.Manifest with { PluginsDisabled = false }, setup.Profile));

        Assert.Contains("pluginsDisabled=true", exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void ExportCandidateIsExplicitAndContainsReviewableDefinitionFields()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateUniqueRoundingCases(fixture);
        var analysis = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile);

        var json = OracleAnalyzer.ExportCandidate(analysis, "test_parameter", 100, ParameterEncodingType.LinearU8);
        using var document = JsonDocument.Parse(json);

        Assert.Equal("test_parameter", document.RootElement.GetProperty("id").GetString());
        Assert.False(document.RootElement.GetProperty("writable").GetBoolean());
        Assert.Equal("oracle-observed", document.RootElement.GetProperty("validationLevel").GetString());
        Assert.True(document.RootElement.TryGetProperty("description", out _));
        Assert.True(document.RootElement.TryGetProperty("rawRange", out _));
        Assert.True(document.RootElement.TryGetProperty("engineeringRange", out _));
        Assert.True(document.RootElement.TryGetProperty("revisionScope", out _));
        Assert.True(document.RootElement.TryGetProperty("sources", out _));
        Assert.True(document.RootElement.TryGetProperty("notes", out _));
    }

    [Fact]
    public void CrossEditorRequiresSameBaselineAndCommonCandidate()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateUniqueRoundingCases(fixture);
        var crome = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile);
        var hts = crome with { ReferenceTool = "Honda Tuning Suite" };
        var ambiguousCrome = crome with
        {
            Parameters = crome.Parameters.Select(parameter => parameter with
            {
                Candidates = parameter.Candidates.Select(candidate => candidate with
                {
                    CompatibleRoundingPolicies = new[] { RoundingPolicy.Nearest, RoundingPolicy.Ceiling },
                }).ToArray(),
            }).ToArray(),
        };
        var ambiguous = CrossEditorComparer.Compare(ambiguousCrome,
            ambiguousCrome with { ReferenceTool = "Honda Tuning Suite" });

        var confirmed = CrossEditorComparer.Compare(crome, hts);
        var conflict = CrossEditorComparer.Compare(crome, hts with
        {
            BaselineHash = new RomHash(new string('0', 64), "00000000"),
        });
        var residualConflict = CrossEditorComparer.Compare(crome with
        {
            AdditionalChangedRanges = new[] { new DiffRange(70, 1, string.Empty, string.Empty) },
        }, hts);

        Assert.True(confirmed.SameBaseline);
        Assert.True(confirmed.Parameters.Single().HasCommonCandidate);
        Assert.Equal(ValidationLevel.CrossEditorConfirmed, confirmed.Parameters.Single().ValidationLevel);
        Assert.False(conflict.SameBaseline);
        Assert.True(conflict.Parameters.Single().HasCommonCandidate);
        Assert.False(conflict.IsCrossEditorConfirmed);
        Assert.Equal(ValidationLevel.OracleObserved, conflict.Parameters.Single().ValidationLevel);
        Assert.Contains(conflict.Parameters.Single().ConflictReasons, reason => reason.Contains("same baseline", StringComparison.OrdinalIgnoreCase));
        Assert.Equal(crome.AdditionalChangedRanges, confirmed.CromeAdditionalRanges);
        Assert.Equal(hts.AdditionalChangedRanges, confirmed.HtsAdditionalRanges);
        Assert.Equal(crome.ObservedChecksumChangedRanges, confirmed.CromeObservedChecksumRanges);
        Assert.Equal(hts.ObservedChecksumChangedRanges, confirmed.HtsObservedChecksumRanges);
        Assert.False(ambiguous.Parameters.Single().SameRounding);
        Assert.False(ambiguous.IsCrossEditorConfirmed);
        Assert.False(residualConflict.IsCrossEditorConfirmed);
        Assert.Contains(residualConflict.Parameters.Single().ConflictReasons,
            reason => reason.Contains("unexplained", StringComparison.OrdinalIgnoreCase));
    }

    private static OracleSetup CreateCases(
        SyntheticFixture fixture,
        bool inverse,
        int parameterOffset = 100,
        IReadOnlyList<double>? requestedValues = null,
        IReadOnlyList<double?>? displayedValues = null,
        IReadOnlyList<byte>? caseRawValues = null,
        bool includeResidual = true,
        byte? normalizedAddressCaseValue = null)
    {
        var baselineBytes = new byte[32768];
        var noOpBytes = (byte[])baselineBytes.Clone();
        noOpBytes[50] = 0xAA;
        var baselinePath = fixture.WriteRom("baseline.dat", baselineBytes);
        var noOpPath = fixture.WriteRom("noop.dat", noOpBytes);
        var profile = new RomProfile("synthetic-oracle-profile", "Synthetic oracle profile", "Generated test bytes",
            32768, "synthetic-v1", experimental: true, requiresExplicitConfirmation: true,
            checksum: new ChecksumDefinition("simulated-unknown", ChecksumStatus.Unknown, 60, 1,
                ValidationLevel.PublicDocumentation));
        var manifest = OracleManifestService.Create("Crome", "synthetic-1", profile.Id, baselinePath, noOpPath,
            pluginsDisabled: true);
        var rawValues = caseRawValues ?? (inverse ? new byte[] { 10, 20, 40 } : new byte[] { 50, 100, 150 });
        var defaults = inverse ? new[] { 600d, 300d, 150d } : new[] { 500d, 1000d, 1500d };
        var engineeringValues = requestedValues ?? defaults;
        var casePaths = new List<string>();
        for (var index = 0; index < rawValues.Count; index++)
        {
            var bytes = (byte[])noOpBytes.Clone();
            bytes[parameterOffset] = rawValues[index];
            if (normalizedAddressCaseValue is not null)
            {
                bytes[50] = normalizedAddressCaseValue.Value;
            }

            bytes[60] = (byte)(index + 1); // Synthetic stand-in for an editor checksum side effect.
            if (includeResidual)
            {
                bytes[70] = 0x77; // Editor-specific side effect that is neither normalization nor checksum.
            }
            var path = fixture.WriteRom($"case-{index}.dat", bytes);
            casePaths.Add(path);
            manifest = OracleManifestService.AddCase(manifest, "test_parameter", engineeringValues[index], path,
                displayedValue: displayedValues?[index]);
        }

        return new OracleSetup(profile, manifest, casePaths);
    }

    private static OracleSetup CreateUniqueRoundingCases(SyntheticFixture fixture) =>
        CreateCases(
            fixture,
            inverse: false,
            requestedValues: new[] { 505d, 1006d, 1503d },
            displayedValues: new double?[] { 510d, 1010d, 1500d },
            caseRawValues: new byte[] { 51, 101, 150 },
            includeResidual: false);

    private sealed record OracleSetup(RomProfile Profile, OracleManifest Manifest, IReadOnlyList<string> CasePaths);
}

internal static class ByteRangeTestExtensions
{
    public static bool ContainsOffset(this DiffRange range, int offset) =>
        offset >= range.Offset && offset <= range.EndOffset;
}
