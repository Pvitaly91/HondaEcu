namespace HondaEcu.Core.Tests;

public sealed class OracleEvidenceTests
{
    [Fact]
    public void CoreRejectsSameEditorEvenWhenEveryCandidateMatches()
    {
        var analysis = SyntheticAnalysisFixture("Crome");
        Assert.Throws<InvalidOperationException>(() => CrossEditorComparer.Compare(analysis, analysis));
    }

    [Theory]
    [InlineData(double.NaN)]
    [InlineData(double.PositiveInfinity)]
    public void CoreRejectsNonFiniteCandidateMetadata(double scale)
    {
        var left = SyntheticAnalysisFixture("Crome");
        var candidate = left.Parameters[0].Candidates[0] with { Scale = scale };
        left = left with { Parameters = new[] { left.Parameters[0] with { Candidates = new[] { candidate } } } };
        Assert.Throws<InvalidDataException>(() => CrossEditorComparer.Compare(left, SyntheticAnalysisFixture("HTS")));
    }

    [Fact]
    public void CoreRejectsInvalidCandidateBounds()
    {
        var left = SyntheticAnalysisFixture("Crome");
        var candidate = left.Parameters[0].Candidates[0] with { Offset = 32768, Width = 2 };
        left = left with { Parameters = new[] { left.Parameters[0] with { Candidates = new[] { candidate } } } };
        Assert.Throws<InvalidDataException>(() => CrossEditorComparer.Compare(left, SyntheticAnalysisFixture("HTS")));
    }

    [Fact]
    public void UnknownNoOpTransformationCannotProduceConfirmation()
    {
        var left = SyntheticAnalysisFixture("Crome") with
        {
            NoOpNormalizationRanges = new[] { new DiffRange(50, 1, "00", "AA") },
        };
        var right = SyntheticAnalysisFixture("HTS") with { NoOpNormalizationRanges = left.NoOpNormalizationRanges };
        Assert.False(CrossEditorComparer.Compare(left, right).IsCrossEditorConfirmed);
    }

    [Theory]
    [InlineData(-1d)]
    [InlineData(double.NaN)]
    [InlineData(double.PositiveInfinity)]
    [InlineData(0.1d)]
    public void CoreRejectsInvalidComparisonTolerance(double tolerance) =>
        Assert.Throws<ArgumentOutOfRangeException>(() => CrossEditorComparer.Compare(
            SyntheticAnalysisFixture("Crome"), SyntheticAnalysisFixture("HTS"), tolerance));

    [Fact]
    public void ToolAliasesShareCoreNormalization()
    {
        Assert.True(OracleProvenance.IsExpectedTool("Honda Tuning Suite", "HTS"));
        Assert.True(OracleProvenance.IsExpectedTool(" CROME ", "crome"));
        Assert.Throws<InvalidOperationException>(() => CrossEditorComparer.Compare(
            SyntheticAnalysisFixture("HTS"), SyntheticAnalysisFixture("Honda Tuning Suite")));
    }

    [Fact]
    public void NoOpRequiresIndependentDeterminismAndResaveStability()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateBoundFixture(fixture, "crome", changedNoOp: true);
        var stableUnknown = OracleEvidence.InspectNoOp(setup.Manifest);
        Assert.True(stableUnknown.IsDeterministic);
        Assert.True(stableUnknown.IsStable);
        Assert.True(stableUnknown.HasTransformation);
        Assert.False(stableUnknown.IsReadyForComparison);
        var different = setup.Manifest with
        {
            IndependentNoOp = new OracleFileEvidence(setup.Manifest.IndependentNoOp!.RomPath,
                new RomHash(new string('b', 64), "87654321")),
            ResavedNoOp = new OracleFileEvidence(setup.Manifest.ResavedNoOp!.RomPath,
                new RomHash(new string('c', 64), "11111111")),
        };
        var unstable = OracleEvidence.InspectNoOp(different);
        Assert.False(unstable.IsDeterministic);
        Assert.False(unstable.IsStable);
        Assert.Contains(unstable.Blockers, reason => reason.Contains("nondeterministic", StringComparison.Ordinal));
        Assert.Contains(unstable.Blockers, reason => reason.Contains("stabilize", StringComparison.Ordinal));
    }

    [Fact]
    public void NoOpEvidenceCannotReuseBaselineOrEachOthersPaths()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateBoundFixture(fixture, "crome");
        var reused = setup.Manifest with { IndependentNoOp = new OracleFileEvidence(setup.Manifest.BaselinePath, setup.Manifest.BaselineHash) };
        Assert.Contains(OracleEvidence.InspectNoOp(reused).Blockers, reason => reason.Contains("distinct output paths", StringComparison.Ordinal));
        reused = setup.Manifest with { ResavedNoOp = setup.Manifest.IndependentNoOp };
        Assert.Contains(OracleEvidence.InspectNoOp(reused).Blockers, reason => reason.Contains("distinct output paths", StringComparison.Ordinal));
    }

    [Fact]
    public void PreflightReportsMissingManifestAndPrivateFilesWithoutGeneratingRoms()
    {
        using var fixture = new SyntheticFixture();
        var report = OraclePreflight.Check(fixture.PathFor("missing.json"));
        Assert.Equal(OracleCollectionStatus.CollectionIncomplete, report.Status);
        Assert.Equal("AwaitingUserFiles", report.M1DataStatus);
        Assert.NotEmpty(report.Blockers);
        report.Save(fixture.PathFor("preflight.json"));
        Assert.True(File.Exists(fixture.PathFor("preflight.json")));

        var hash = new RomHash(new string('a', 64), "12345678");
        var manifest = new OracleManifest("1.0", "Crome", "unit-test-fixture", Array.Empty<string>(), true,
            "synthetic", fixture.PathFor("private-base.dat"), hash, fixture.PathFor("private-noop.dat"), hash,
            DateTimeOffset.UtcNow, Array.Empty<DiffRange>(), Array.Empty<OracleCase>());
        var path = fixture.PathFor("legacy.json");
        OracleManifestService.Save(manifest, path);
        var missingFiles = OraclePreflight.Check(path);
        Assert.Equal("AwaitingUserFiles", missingFiles.M1DataStatus);
        Assert.Contains(missingFiles.Files, file => file.Role == "baseline" && !file.Present);
        Assert.Contains(missingFiles.Warnings, warning => warning.Contains("Legacy", StringComparison.Ordinal));
        Assert.False(File.Exists(manifest.BaselinePath));
    }

    [Fact]
    public void PreflightReportsInvalidManifestAsCollectionBlocker()
    {
        using var fixture = new SyntheticFixture();
        var path = fixture.PathFor("invalid.json");
        File.WriteAllText(path, "{\"formatVersion\":\"unsupported\"}");
        var report = OraclePreflight.Check(path);
        Assert.Equal(OracleCollectionStatus.CollectionIncomplete, report.Status);
        Assert.NotEmpty(report.Blockers);
    }

    [Fact]
    public void AnalysisBindsSourceManifestAndRejectsLaterEdits()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateBoundFixture(fixture, "crome");
        var path = fixture.PathFor("manifest.json");
        OracleManifestService.Save(setup.Manifest, path);
        var analysis = OracleAnalyzer.Analyze(OracleManifest.Load(path), setup.Profile);
        Assert.Empty(OracleEvidence.ValidateBinding(analysis));
        OracleManifestService.Save(setup.Manifest with { ToolEdition = "edited-after-analysis" }, path, overwrite: true);
        Assert.Throws<InvalidDataException>(() => OracleEvidence.ValidateBinding(analysis));
    }

    [Fact]
    public void AnalysisRejectsForgedToolCandidateAndProfileDigest()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateBoundFixture(fixture, "crome");
        var analysis = OracleAnalyzer.Analyze(setup.Manifest, setup.Profile);
        Assert.Throws<InvalidDataException>(() => OracleEvidence.ValidateBinding(analysis with { ReferenceTool = "HTS" }));
        Assert.Throws<InvalidDataException>(() => OracleEvidence.ValidateBinding(analysis with
        {
            EvidenceBinding = analysis.EvidenceBinding! with { ProfileDigest = new string('0', 64) },
        }));
        var candidate = analysis.Parameters[0].Candidates[0] with { HoldoutPointCount = 999 };
        var forged = analysis with { Parameters = new[] { analysis.Parameters[0] with { Candidates = new[] { candidate } } } };
        Assert.Throws<InvalidDataException>(() => OracleEvidence.ValidateBinding(forged));
    }

    [Fact]
    public void AnalysisRejectsStaleSourceProfileBytesEvenWhenSemanticJsonIsUnchanged()
    {
        using var fixture = new SyntheticFixture();
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "HondaEcu.sln"))) directory = directory.Parent;
        Assert.NotNull(directory);
        var original = Path.Combine(directory.FullName, "definitions", "p28", "p28-304.experimental.json");
        var profilePath = fixture.PathFor("profile.json");
        File.Copy(original, profilePath);
        var profile = RomProfile.Load(profilePath);
        var setup = CreateBoundFixture(fixture, "crome");
        var analysis = OracleAnalyzer.Analyze(setup.Manifest with { ProfileId = profile.Id }, profile);
        File.AppendAllText(profilePath, Environment.NewLine);
        Assert.Throws<InvalidDataException>(() => OracleEvidence.ValidateBinding(analysis));
    }

    [Fact]
    public void PreflightReportsHashMismatchAndUnknownStableTransformation()
    {
        using var fixture = new SyntheticFixture();
        var setup = CreateBoundFixture(fixture, "crome", changedNoOp: true);
        var path = fixture.PathFor("manifest.json");
        OracleManifestService.Save(setup.Manifest, path);
        var report = OraclePreflight.Check(path, setup.Profile);
        Assert.Contains(report.Blockers, reason => reason.Contains("Unknown no-op transformation", StringComparison.Ordinal));
        var bytes = File.ReadAllBytes(setup.Manifest.BaselinePath);
        bytes[0] = 1;
        File.WriteAllBytes(setup.Manifest.BaselinePath, bytes);
        var stale = OraclePreflight.Check(path, setup.Profile);
        Assert.Contains(stale.Files, file => file.Role == "baseline" && file.HashMatches == false);
        Assert.Equal(OracleCollectionStatus.CollectionIncomplete, stale.Status);
    }

    [Fact]
    public void IndependentSyntheticFixtureCanConfirmOneDefinitionButNotAnUnresolvedRequestedSet()
    {
        using var fixture = new SyntheticFixture();
        var left = CreateBoundFixture(fixture, "crome", includeAmbiguousParameter: true);
        var right = CreateBoundFixture(fixture, "hts", includeAmbiguousParameter: true);
        var report = CrossEditorComparer.Compare(OracleAnalyzer.Analyze(left.Manifest, left.Profile),
            OracleAnalyzer.Analyze(right.Manifest, right.Profile));
        var unique = report.Parameters.Single(item => item.ParameterId == "unique");
        var ambiguous = report.Parameters.Single(item => item.ParameterId == "ambiguous");
        Assert.True(unique.UniqueValidatedDefinition);
        Assert.False(unique.IsAmbiguous);
        Assert.Empty(unique.ConflictReasons);
        Assert.Equal(ValidationLevel.CrossEditorConfirmed, unique.ValidationLevel);
        Assert.True(ambiguous.HasCommonCandidate);
        Assert.False(ambiguous.UniqueValidatedDefinition);
        Assert.True(ambiguous.IsAmbiguous);
        Assert.True(report.HasAnyConfirmedParameter);
        Assert.False(report.AllRequestedParametersConfirmed);
        Assert.False(report.IsCrossEditorConfirmed);
        Assert.True(report.HasUnresolvedParameters);
        Assert.True(report.HasConflicts);
    }

    [Fact]
    public void CoincidentallyCorrelatedSideByteRemainsUnexplainedDespiteCandidateFit()
    {
        using var fixture = new SyntheticFixture();
        var left = CreateBoundFixture(fixture, "crome", correlatedSideByte: true);
        var right = CreateBoundFixture(fixture, "hts", correlatedSideByte: true);
        var report = CrossEditorComparer.Compare(OracleAnalyzer.Analyze(left.Manifest, left.Profile),
            OracleAnalyzer.Analyze(right.Manifest, right.Profile));
        Assert.False(report.IsCrossEditorConfirmed);
        var comparison = Assert.Single(report.Parameters);
        Assert.Contains(comparison.CromeAlternatives, candidate => candidate.Offset == 300);
        Assert.Contains(comparison.CromeUnexplainedRanges, range => range.ContainsOffset(300));
        Assert.Contains(comparison.CromeUnexplainedRanges, range => range.ContainsOffset(32767));
    }

    private static (OracleManifest Manifest, RomProfile Profile) CreateBoundFixture(
        SyntheticFixture fixture, string tool, bool changedNoOp = false, bool includeAmbiguousParameter = false,
        bool correlatedSideByte = false)
    {
        var baseline = new byte[32768];
        var noOp = (byte[])baseline.Clone();
        if (changedNoOp) noOp[50] = 0xAA;
        var baselinePath = fixture.WriteRom($"{tool}-baseline.dat", baseline);
        var noOpPath = fixture.WriteRom($"{tool}-noop.dat", noOp);
        var independentPath = fixture.WriteRom($"{tool}-independent.dat", noOp);
        var resavedPath = fixture.WriteRom($"{tool}-resaved.dat", noOp);
        var profile = new RomProfile("synthetic-bound", "Synthetic evidence fixture", "Generated bytes; no actual editor output",
            32768, "synthetic", true, true,
            checksum: new ChecksumDefinition("synthetic-exclusion", ChecksumStatus.Unknown, 32766, 1, ValidationLevel.PublicDocumentation));
        var manifest = OracleManifestService.Create(tool, "algorithm-unit-test-fixture", profile.Id, baselinePath, noOpPath, true,
            toolEdition: "synthetic fixture", independentNoOpPath: independentPath, resavedNoOpPath: resavedPath);
        var requested = new[] { 505d, 1006d, 1503d, 2004d };
        var raw = new byte[] { 51, 101, 150, 200 };
        foreach (var parameter in includeAmbiguousParameter ? new[] { "unique", "ambiguous" } : new[] { "unique" })
        {
            for (var index = 0; index < requested.Length; index++)
            {
                var bytes = (byte[])noOp.Clone();
                bytes[parameter == "unique" ? 32767 : 100] = raw[index];
                if (correlatedSideByte) bytes[300] = raw[index];
                var casePath = fixture.WriteRom($"{tool}-{parameter}-{index}.dat", bytes);
                manifest = OracleManifestService.AddCase(manifest, parameter, requested[index], casePath,
                    displayedValue: raw[index] * 10d, role: index == 3 ? OracleObservationRole.Holdout : OracleObservationRole.Training,
                    observationId: $"{tool}-{parameter}-{index}");
            }
        }
        return (manifest, profile);
    }

    // Fabricated algorithm unit-test objects. These are not outputs from either named editor.
    private static OracleAnalysis SyntheticAnalysisFixture(string tool)
    {
        var candidate = new OracleCandidate("test", 100, 1, ParameterEncodingType.LinearU8,
            Endianness.NotApplicable, 10, 0, 1, 0, RoundingPolicy.Nearest,
            new[] { RoundingPolicy.Nearest }, 0, 0, 1, new long[] { 51, 101, 150 },
            new double[] { 510, 1010, 1500 });
        var hash = new RomHash(new string('a', 64), "12345678");
        return new OracleAnalysis("1.0", tool, "synthetic-unit-test-fixture", "synthetic", hash, hash,
            DateTimeOffset.UtcNow, Array.Empty<DiffRange>(), Array.Empty<ByteRange>(), Array.Empty<DiffRange>(),
            new[] { new OracleParameterAnalysis("test", 3, new[] { candidate }, Array.Empty<string>()) });
    }
}
