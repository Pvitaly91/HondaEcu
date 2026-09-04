using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class DiffAndPatchTests
{
    [Fact]
    public void MergesContiguousDiffsAndReportsPageStatistics()
    {
        var baseline = new byte[512];
        var modified = (byte[])baseline.Clone();
        modified[1] = 1;
        modified[2] = 2;
        modified[4] = 4;
        modified[300] = 3;

        var report = DiffEngine.Compare(RomImage.FromBytes(baseline), RomImage.FromBytes(modified));

        Assert.Equal(4, report.DifferentByteCount);
        Assert.Equal(1, report.FirstDifferentOffset);
        Assert.Equal(300, report.LastDifferentOffset);
        Assert.Collection(report.Ranges,
            range => Assert.Equal((1, 2, "0000", "0102"), (range.Offset, range.Length, range.OldHex, range.NewHex)),
            range => Assert.Equal((4, 1), (range.Offset, range.Length)),
            range => Assert.Equal((300, 1), (range.Offset, range.Length)));
        Assert.Collection(report.Pages,
            page => Assert.Equal((0, 3), (page.Page, page.ChangedByteCount)),
            page => Assert.Equal((1, 1), (page.Page, page.ChangedByteCount)));
    }

    [Fact]
    public void DiffJsonRoundTripsAsStructuredReport()
    {
        var report = DiffEngine.Compare(RomImage.FromBytes(new byte[4]), RomImage.FromBytes(new byte[] { 0, 1, 0, 2 }));
        using var json = JsonDocument.Parse(report.ToJson());

        Assert.Equal(2, json.RootElement.GetProperty("differentByteCount").GetInt32());
        Assert.Equal(2, json.RootElement.GetProperty("ranges").GetArrayLength());
    }

    [Fact]
    public void PatchRefusesUnknownRomUntilExplicitProfileConfirmation()
    {
        var profile = SyntheticFixture.Profile();
        var input = RomImage.FromBytes(SyntheticFixture.Bytes());
        var plan = PatchPlan.Create(profile.Id, new[] { new ParameterAssignment("raw_u8", 200) });

        Assert.Throws<UnknownRomException>(() => PatchEngine.Apply(input, profile, plan, RomIdentity.Unknown()));

        var identity = RomIdentifier.Identify(input, new[] { profile }, profile.Id);
        var result = PatchEngine.Apply(input, profile, plan, identity);
        Assert.Equal(200, result.Image.ToArray()[100]);
    }

    [Fact]
    public void PatchRequiresSeparateUnverifiedOverrideAndRejectsReadOnly()
    {
        var profile = SyntheticFixture.Profile();
        var input = RomImage.FromBytes(SyntheticFixture.Bytes());
        var identity = RomIdentifier.Identify(input, new[] { profile }, profile.Id);
        var unverified = PatchPlan.Create(profile.Id, new[] { new ParameterAssignment("unverified", 20) });

        Assert.Throws<UnverifiedParameterException>(() => PatchEngine.Apply(input, profile, unverified, identity));
        var allowed = PatchEngine.Apply(input, profile, unverified with { AllowUnverified = true }, identity);
        Assert.Equal(20, allowed.Image.ToArray()[113]);
        Assert.Throws<ParameterNotWritableException>(() => PatchEngine.Apply(input, profile,
            PatchPlan.Create(profile.Id, new[] { new ParameterAssignment("read_only", 1) }), identity));
    }

    [Fact]
    public void CandidateStatusRequiresUnverifiedOverrideEvenWithCrossEditorEvidence()
    {
        var parameter = new ScalarParameterDefinition("candidate", "Candidate", "Synthetic", 10, 1,
            Endianness.NotApplicable, new ParameterEncoding(ParameterEncodingType.RawU8), rawMinimum: 0, rawMaximum: 255,
            engineeringMinimum: 0, engineeringMaximum: 255, writable: true,
            validationLevel: ValidationLevel.CrossEditorConfirmed, revisionScope: "synthetic", status: ParameterStatus.Candidate);
        var profile = new RomProfile("candidate-profile", "Candidate", "Synthetic", 32768, "synthetic", true, true,
            parameters: new[] { parameter });
        var input = RomImage.FromBytes(SyntheticFixture.Bytes());
        var identity = RomIdentifier.Identify(input, new[] { profile }, profile.Id);
        var plan = PatchPlan.Create(profile.Id, new[] { new ParameterAssignment("candidate", 20) });

        Assert.Throws<UnverifiedParameterException>(() => PatchEngine.Apply(input, profile, plan, identity));
        Assert.Equal(20, PatchEngine.Apply(input, profile, plan with { AllowUnverified = true }, identity).Image.ToArray()[10]);
    }

    [Fact]
    public void PatchTracksExactOffsetsAndProducesJsonReport()
    {
        var (input, profile, result) = CreatePatch();

        Assert.Equal(new[] { 100 }, result.Report.ChangedOffsets);
        var change = Assert.Single(result.Report.Changes);
        Assert.Equal("7F", change.OldHex);
        Assert.Equal("C8", change.NewHex);
        Assert.Equal(input.Hash, result.Report.InputHash);
        Assert.Equal(result.Image.Hash, result.Report.OutputHash);
        Assert.Equal(ChecksumStatus.Unknown, result.Report.ChecksumStatusAfter);
        Assert.Equal(FlashReadinessStatus.PcInspectionOnly, result.Report.FlashReadiness);
        var parsed = PatchReport.Parse(result.Report.ToJson());
        Assert.Equal(result.Report.OutputHash, parsed.OutputHash);
        Assert.Equal(result.Report.Changes, parsed.Changes);
        Assert.Equal(result.Report.ChangedOffsets, parsed.ChangedOffsets);
        Assert.Equal(result.Report.DiffRanges, parsed.DiffRanges);
    }

    [Fact]
    public void WritesRomAndMandatoryReportAsAnAtomicPair()
    {
        using var fixture = new SyntheticFixture();
        var inputPath = fixture.WriteRom("input.dat", SyntheticFixture.Bytes());
        var input = RomImage.Load(inputPath);
        var profile = SyntheticFixture.Profile();
        var identity = RomIdentifier.Identify(input, new[] { profile }, profile.Id);
        var result = PatchEngine.Apply(input, profile,
            PatchPlan.Create(profile.Id, new[] { new ParameterAssignment("raw_u8", 200) }), identity);
        var outputPath = fixture.PathFor("output.dat");
        var reportPath = fixture.PathFor("output.patch.json");

        PatchEngine.WriteAtomic(result, outputPath, reportPath);

        Assert.Equal(result.Image.Hash, RomImage.Load(outputPath).Hash);
        Assert.Equal(result.Report.OutputHash, PatchReport.Load(reportPath).OutputHash);
        Assert.DoesNotContain(Directory.EnumerateFiles(fixture.DirectoryPath), path => path.EndsWith(".tmp", StringComparison.Ordinal));
    }

    [Fact]
    public void AtomicPairFailureLeavesNoPartialRom()
    {
        using var fixture = new SyntheticFixture();
        var (_, _, result) = CreatePatch();
        var output = fixture.PathFor("output.dat");
        var report = fixture.WriteRom("exists.json", new byte[] { 1 });

        Assert.Throws<IOException>(() => PatchEngine.WriteAtomic(result, output, report));
        Assert.False(File.Exists(output));
        Assert.Equal(new byte[] { 1 }, File.ReadAllBytes(report));
    }

    [Fact]
    public void VerificationAcceptsDeclaredPatchAndDetectsUndeclaredByte()
    {
        var (input, profile, result) = CreatePatch();
        var valid = PatchVerifier.Verify(result.Image, profile, result.Report, input);
        var tampered = result.Image.CreateModifiedCopy(new[] { new BytePatch(500, new byte[] { 42 }) });
        var invalid = PatchVerifier.Verify(tampered, profile, result.Report, input);

        Assert.True(valid.IsValid);
        Assert.Empty(valid.Issues);
        Assert.False(invalid.IsValid);
        Assert.Contains(invalid.Issues, issue => issue.Code == "undeclared-change" && issue.Offset == 500);
    }

    [Fact]
    public void VerificationNeedsBaselineForIndependentUndeclaredChangeCheck()
    {
        var (_, profile, result) = CreatePatch();
        var reportWithoutPath = result.Report with { InputPath = null };

        var verification = PatchVerifier.Verify(result.Image, profile, reportWithoutPath);

        Assert.False(verification.IsValid);
        Assert.Contains(verification.Issues, issue => issue.Code == "baseline-unavailable");
    }

    [Fact]
    public void VerificationRejectsForgedDeclaredOffsetAndElevatedReadiness()
    {
        var (input, profile, result) = CreatePatch();
        var tampered = result.Image.CreateModifiedCopy(new[] { new BytePatch(500, new byte[] { 42 }) });
        var actualDiff = DiffEngine.Compare(input, tampered);
        var forged = result.Report with
        {
            OutputHash = tampered.Hash,
            ChangedOffsets = actualDiff.Ranges.SelectMany(range => Enumerable.Range(range.Offset, range.Length)).ToArray(),
            DiffRanges = actualDiff.Ranges,
            FlashReadiness = FlashReadinessStatus.BenchValidated,
        };

        var verification = PatchVerifier.Verify(tampered, profile, forged, input);

        Assert.False(verification.IsValid);
        Assert.Contains(verification.Issues, issue => issue.Code == "unowned-declared-change" && issue.Offset == 500);
        Assert.Contains(verification.Issues, issue => issue.Code == "invalid-flash-readiness");
        Assert.Equal(FlashReadinessStatus.PcInspectionOnly, verification.FlashReadiness);
        Assert.False(verification.IsFlashReady);
    }

    [Fact]
    public void VerificationRejectsForgedRequestedValueAndReadOnlyChange()
    {
        var (input, profile, result) = CreatePatch();
        var badRequested = result.Report with
        {
            Changes = result.Report.Changes.Select(change => change with { RequestedValue = 1 }).ToArray(),
        };
        var requestedVerification = PatchVerifier.Verify(result.Image, profile, badRequested, input);

        var definition = profile.GetParameter("read_only");
        var readOnlyOutput = input.CreateModifiedCopy(new[] { new BytePatch(definition.Offset, new byte[] { 1 }) });
        var before = ParameterCodec.Decode(definition, input.Bytes.Span);
        var after = ParameterCodec.Decode(definition, readOnlyOutput.Bytes.Span);
        var change = new ParameterChange(definition.Id, 1, before, after, definition.Offset, before.RawHex, after.RawHex);
        var diff = DiffEngine.Compare(input, readOnlyOutput);
        var forgedReadOnly = result.Report with
        {
            OutputHash = readOnlyOutput.Hash,
            Changes = new[] { change },
            ChangedOffsets = new[] { definition.Offset },
            DiffRanges = diff.Ranges,
        };
        var readOnlyVerification = PatchVerifier.Verify(readOnlyOutput, profile, forgedReadOnly, input);

        Assert.Contains(requestedVerification.Issues, issue => issue.Code == "requested-value-mismatch");
        Assert.Contains(readOnlyVerification.Issues, issue => issue.Code == "parameter-not-writable");
    }

    [Fact]
    public void VerificationReturnsIssuesForNullNestedMetadataAndDuplicateChanges()
    {
        var (input, profile, result) = CreatePatch();
        var original = Assert.Single(result.Report.Changes);
        var malformed = result.Report with
        {
            Changes = new[] { original with { Before = null! } },
        };
        var duplicate = result.Report with
        {
            Changes = new[] { original, original },
        };

        var malformedResult = PatchVerifier.Verify(result.Image, profile, malformed, input);
        var duplicateResult = PatchVerifier.Verify(result.Image, profile, duplicate, input);

        Assert.False(malformedResult.IsValid);
        Assert.Contains(malformedResult.Issues, issue => issue.Code == "malformed-change");
        Assert.False(duplicateResult.IsValid);
        Assert.Contains(duplicateResult.Issues, issue => issue.Code == "duplicate-parameter-change");
    }

    [Fact]
    public void UndefinedIdentificationMethodsFailClosedInPatchAndVerification()
    {
        var (input, profile, result) = CreatePatch();
        var undefined = (RomIdentificationMethod)999;

        Assert.Throws<UnknownRomException>(() => PatchEngine.Apply(input, profile,
            PatchPlan.Create(profile.Id, new[] { new ParameterAssignment("raw_u8", 200) }),
            new RomIdentity(true, profile.Id, undefined, "forged")));

        var verification = PatchVerifier.Verify(result.Image, profile,
            result.Report with { IdentificationMethod = undefined }, input);
        Assert.Contains(verification.Issues, issue => issue.Code == "invalid-identification-method");

        var numericJson = result.Report.ToJson().Replace(
            "\"identificationMethod\": \"explicit-override\"",
            "\"identificationMethod\": 999",
            StringComparison.Ordinal);
        Assert.Throws<System.Text.Json.JsonException>(() => PatchReport.Parse(numericJson));
    }

    private static (RomImage Input, RomProfile Profile, PatchResult Result) CreatePatch()
    {
        var input = RomImage.FromBytes(SyntheticFixture.Bytes());
        var profile = SyntheticFixture.Profile();
        var identity = RomIdentifier.Identify(input, new[] { profile }, profile.Id);
        var result = PatchEngine.Apply(input, profile,
            PatchPlan.Create(profile.Id, new[] { new ParameterAssignment("raw_u8", 200) }), identity);
        return (input, profile, result);
    }
}
