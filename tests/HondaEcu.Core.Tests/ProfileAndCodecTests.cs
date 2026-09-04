namespace HondaEcu.Core.Tests;

public sealed class ProfileAndCodecTests
{
    [Fact]
    public void ParsesAndValidatesSyntheticProfileJson()
    {
        var profile = RomProfile.Parse(ValidProfileJson);

        Assert.Equal("synthetic-json-profile", profile.Id);
        Assert.Equal(32768, profile.ExpectedSize);
        Assert.True(profile.Experimental);
        Assert.Single(profile.Parameters);
        Assert.True(profile.Validate().IsValid);
    }

    [Fact]
    public void LoadsRepositoryP28ExperimentalProfile()
    {
        var root = FindRepositoryRoot();
        var profile = RomProfile.Load(Path.Combine(root, "definitions", "p28", "p28-304.experimental.json"));

        Assert.Equal("p28-304", profile.Id);
        Assert.Equal(32768, profile.ExpectedSize);
        Assert.All(profile.Parameters, parameter =>
        {
            Assert.False(parameter.Writable);
            Assert.Equal(ParameterEncodingType.Unsupported, parameter.Encoding.Type);
        });
        Assert.All(profile.Tables, table => Assert.Equal(ParameterEncodingType.Unsupported, table.Encoding.Type));
    }

    [Fact]
    public void RejectsMissingRequiredParameterField()
    {
        var invalid = ValidProfileJson.Replace("\"units\": \"raw\",", string.Empty, StringComparison.Ordinal);
        var missingEncoding = ValidProfileJson.Replace("\"encoding\": { \"type\": \"raw-u8\" },", string.Empty, StringComparison.Ordinal);

        var exception = Assert.Throws<ProfileValidationException>(() => RomProfile.Parse(invalid));
        Assert.Contains("units", exception.Message, StringComparison.OrdinalIgnoreCase);
        Assert.False(ProfileDocumentValidator.Validate(missingEncoding).IsValid);
    }

    [Fact]
    public void RejectsUnknownEncodingInsteadOfExecutingOrDowngradingIt()
    {
        var invalid = ValidProfileJson.Replace("raw-u8", "javascript-eval", StringComparison.Ordinal);

        var exception = Assert.Throws<ProfileValidationException>(() => RomProfile.Parse(invalid));
        Assert.Contains("Unsupported ParameterEncodingType", exception.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("\"schemaVersion\": \"1.0\",", "\"schemaVersion\": \"2.0\",")]
    [InlineData("\"schemaVersion\": \"1.0\",", "\"schemaVersion\": \"1.0\", \"unexpected\": true,")]
    public void StrictDocumentValidationRejectsUnsupportedVersionAndUnknownProperties(string oldText, string newText)
    {
        var result = ProfileDocumentValidator.Validate(ValidProfileJson.Replace(oldText, newText, StringComparison.Ordinal));

        Assert.False(result.IsValid);
        Assert.NotEmpty(result.Errors);
    }

    [Theory]
    [InlineData("")]
    [InlineData("GG")]
    [InlineData("A")]
    public void RejectsEmptyOrMalformedSignatures(string signature)
    {
        var identity = $"\"identity\": {{ \"hashes\": [], \"signatures\": [{{ \"id\": \"bad\", \"offset\": 0, \"hexBytes\": \"{signature}\" }}], \"requiresExplicitConfirmation\": true }}";
        var invalid = ValidProfileJson.Replace(
            "\"identity\": { \"hashes\": [], \"signatures\": [], \"requiresExplicitConfirmation\": true }",
            identity,
            StringComparison.Ordinal);

        Assert.False(ProfileDocumentValidator.Validate(invalid).IsValid);
    }

    [Fact]
    public void RejectsIncompatibleEndiannessAndUnknownSourceReference()
    {
        var endian = ValidProfileJson.Replace("\"endianness\": \"not-applicable\"", "\"endianness\": \"big\"", StringComparison.Ordinal);
        var source = ValidProfileJson.Replace("[\"synthetic-source\"]", "[\"missing-source\"]", StringComparison.Ordinal);

        Assert.False(ProfileDocumentValidator.Validate(endian).IsValid);
        Assert.False(ProfileDocumentValidator.Validate(source).IsValid);
    }

    [Fact]
    public void RejectsWrongTypesForOptionalFieldsAndObjectParameterSources()
    {
        var badScale = ValidProfileJson.Replace("{ \"type\": \"raw-u8\" }", "{ \"type\": \"raw-u8\", \"scale\": \"one\" }", StringComparison.Ordinal);
        var objectSource = ValidProfileJson.Replace("[\"synthetic-source\"]", "[{ \"id\": \"synthetic-source\" }]", StringComparison.Ordinal);
        var badSchema = ValidProfileJson.Replace("{\n  \"schemaVersion\"", "{\n  \"$schema\": 42,\n  \"schemaVersion\"", StringComparison.Ordinal);

        Assert.False(ProfileDocumentValidator.Validate(badScale).IsValid);
        Assert.False(ProfileDocumentValidator.Validate(objectSource).IsValid);
        Assert.False(ProfileDocumentValidator.Validate(badSchema).IsValid);
    }

    [Fact]
    public void RejectsNonObjectParameterArrayItemsAndSchemaInvalidEnumSpelling()
    {
        var numericParameter = ValidProfileJson.Replace(
            "\"parameters\": [\n    {",
            "\"parameters\": [\n    42,\n    {",
            StringComparison.Ordinal);
        var misspelledEncoding = ValidProfileJson.Replace("raw-u8", "Raw_U8", StringComparison.Ordinal);

        Assert.False(ProfileDocumentValidator.Validate(numericParameter).IsValid);
        Assert.False(ProfileDocumentValidator.Validate(misspelledEncoding).IsValid);
    }

    [Fact]
    public void RejectsEmptyOrNonNumericEncodingValues()
    {
        var empty = ValidProfileJson.Replace(
            "{ \"type\": \"raw-u8\" }",
            "{ \"type\": \"raw-u8\", \"values\": [] }",
            StringComparison.Ordinal);
        var nonNumeric = ValidProfileJson.Replace(
            "{ \"type\": \"raw-u8\" }",
            "{ \"type\": \"raw-u8\", \"values\": [\"one\"] }",
            StringComparison.Ordinal);

        Assert.False(ProfileDocumentValidator.Validate(empty).IsValid);
        Assert.False(ProfileDocumentValidator.Validate(nonNumeric).IsValid);
    }

    [Fact]
    public void RejectsJsonExtensionsAndInvalidOptionalCrc32()
    {
        var trailingComma = ValidProfileJson.Replace("\"notes\": \"No algorithm\" }", "\"notes\": \"No algorithm\", }", StringComparison.Ordinal);
        var comment = ValidProfileJson.Replace("\"schemaVersion\": \"1.0\",", "\"schemaVersion\": \"1.0\", // not JSON Schema data", StringComparison.Ordinal);
        var emptyCrc = ValidProfileJson.Replace(
            "\"hashes\": []",
            "\"hashes\": [{ \"sha256\": \"0000000000000000000000000000000000000000000000000000000000000000\", \"crc32\": \"\" }]",
            StringComparison.Ordinal);

        Assert.False(ProfileDocumentValidator.Validate(trailingComma).IsValid);
        Assert.False(ProfileDocumentValidator.Validate(comment).IsValid);
        Assert.False(ProfileDocumentValidator.Validate(emptyCrc).IsValid);
    }

    [Fact]
    public void DoesNotIdentifyProfileBySizeAlone()
    {
        var image = RomImage.FromBytes(SyntheticFixture.Bytes());
        var profile = SyntheticFixture.Profile();

        var identity = RomIdentifier.Identify(image, new[] { profile });

        Assert.False(identity.IsIdentified);
        Assert.Equal(RomIdentificationMethod.None, identity.Method);
    }

    [Fact]
    public void ExplicitProfileSelectionIsRecordedAndStillChecksSize()
    {
        var profile = SyntheticFixture.Profile();
        var identity = RomIdentifier.Identify(RomImage.FromBytes(SyntheticFixture.Bytes()), new[] { profile }, profile.Id);

        Assert.True(identity.IsIdentified);
        Assert.Equal(RomIdentificationMethod.ExplicitOverride, identity.Method);
        Assert.Throws<RomSizeException>(() =>
            RomIdentifier.Identify(RomImage.FromBytes(new byte[10]), new[] { profile }, profile.Id));
    }

    [Fact]
    public void IdentifiesKnownHashAndSignature()
    {
        var bytes = SyntheticFixture.Bytes();
        var image = RomImage.FromBytes(bytes);
        var byHash = new RomProfile("hash", "Hash", "Synthetic", bytes.Length, "synthetic", true, false,
            hashes: new[] { image.Hash });
        var bySignature = new RomProfile("signature", "Signature", "Synthetic", bytes.Length, "synthetic", true, false,
            signatures: new[] { new RomSignature("marker", 4, Convert.ToHexString(bytes.AsSpan(4, 4))) });

        Assert.Equal(RomIdentificationMethod.Sha256, RomIdentifier.Identify(image, new[] { byHash }).Method);
        Assert.Equal(RomIdentificationMethod.Signature, RomIdentifier.Identify(image, new[] { bySignature }).Method);
    }

    [Fact]
    public void EncodesAndDecodesU8SignedAndU16Endianness()
    {
        var rom = new byte[16];
        AssertRoundTrip(Definition("u8", 0, 1, Endianness.NotApplicable, ParameterEncodingType.RawU8, -1, 0, 255), 240, "F0", rom);
        AssertRoundTrip(Definition("s8", 1, 1, Endianness.NotApplicable, ParameterEncodingType.RawS8, -1, -128, 127), -12, "F4", rom);
        AssertRoundTrip(Definition("le", 2, 2, Endianness.Little, ParameterEncodingType.RawU16LittleEndian, -1, 0, 65535), 0x1234, "3412", rom);
        AssertRoundTrip(Definition("be", 4, 2, Endianness.Big, ParameterEncodingType.RawU16BigEndian, -1, 0, 65535), 0x1234, "1234", rom);
    }

    [Fact]
    public void AppliesLinearAndInverseConversions()
    {
        var linear = Definition("linear", 0, 1, Endianness.NotApplicable, ParameterEncodingType.LinearU8, 2.5, 0, 255, 100, 737.5, 100);
        var inverse = new ScalarParameterDefinition("inverse", "Inverse", "Synthetic", 0, 1, Endianness.NotApplicable,
            new ParameterEncoding(ParameterEncodingType.InverseU8, offset: 5, numerator: 60000, denominatorOffset: 1),
            rawMinimum: 0, rawMaximum: 255, engineeringMinimum: 239.375, engineeringMaximum: 60005,
            writable: true, validationLevel: ValidationLevel.CrossEditorConfirmed, revisionScope: "synthetic");

        Assert.Equal(new byte[] { 40 }, ParameterCodec.Encode(linear, 200));
        Assert.Equal(200, ParameterCodec.Decode(linear, new byte[] { 40 }).EngineeringValue, 8);
        Assert.Equal(new byte[] { 19 }, ParameterCodec.Encode(inverse, 3005));
        Assert.Equal(3005, ParameterCodec.Decode(inverse, new byte[] { 19 }).EngineeringValue, 8);
    }

    [Fact]
    public void AppliesLinearAndInverseU16ConversionsWithDeclaredEndianness()
    {
        var linear = new ScalarParameterDefinition("linear16", "Linear16", "Synthetic", 0, 2, Endianness.Little,
            new ParameterEncoding(ParameterEncodingType.LinearU16, scale: 0.5, offset: -10), rawMinimum: 0, rawMaximum: 65535,
            engineeringMinimum: -10, engineeringMaximum: 32757.5, writable: true,
            validationLevel: ValidationLevel.CrossEditorConfirmed, revisionScope: "synthetic");
        var inverse = new ScalarParameterDefinition("inverse16", "Inverse16", "Synthetic", 0, 2, Endianness.Big,
            new ParameterEncoding(ParameterEncodingType.InverseU16, numerator: 6_000_000, denominatorOffset: 1),
            rawMinimum: 0, rawMaximum: 65535, engineeringMinimum: 91, engineeringMaximum: 6_000_000,
            writable: true, validationLevel: ValidationLevel.CrossEditorConfirmed, revisionScope: "synthetic");

        Assert.Equal(new byte[] { 0xC8, 0x00 }, ParameterCodec.Encode(linear, 90));
        Assert.Equal(90, ParameterCodec.Decode(linear, new byte[] { 0xC8, 0x00 }).EngineeringValue, 8);
        Assert.Equal(new byte[] { 0x00, 0xC7 }, ParameterCodec.Encode(inverse, 30_000));
        Assert.Equal(30_000, ParameterCodec.Decode(inverse, new byte[] { 0x00, 0xC7 }).EngineeringValue, 8);
    }

    [Fact]
    public void LookupTableIsControlledAndUnsupportedEncodingCannotExecute()
    {
        var lookup = new ScalarParameterDefinition("lookup", "Lookup", "Synthetic", 0, 1,
            Endianness.NotApplicable, new ParameterEncoding(ParameterEncodingType.LookupTable, values: new[] { 10d, 20d, 40d }),
            rawMinimum: 0, rawMaximum: 2, engineeringMinimum: 10, engineeringMaximum: 40,
            writable: true, validationLevel: ValidationLevel.CrossEditorConfirmed, revisionScope: "synthetic");
        var unsupported = new ScalarParameterDefinition("unsupported", "Unsupported", "Synthetic", 0, 1,
            Endianness.NotApplicable, new ParameterEncoding(ParameterEncodingType.Unsupported), revisionScope: "synthetic");

        Assert.Equal(new byte[] { 1 }, ParameterCodec.Encode(lookup, 18));
        Assert.Equal(40, ParameterCodec.Decode(lookup, new byte[] { 2 }).EngineeringValue);
        Assert.Throws<NotSupportedException>(() => ParameterCodec.Decode(unsupported, new byte[] { 1 }));
        Assert.Throws<NotSupportedException>(() => ParameterCodec.Encode(unsupported, 1));
    }

    [Theory]
    [InlineData(RoundingPolicy.Nearest, 1.5, 2)]
    [InlineData(RoundingPolicy.ToEven, 2.5, 2)]
    [InlineData(RoundingPolicy.Floor, 1.9, 1)]
    [InlineData(RoundingPolicy.Ceiling, 1.1, 2)]
    [InlineData(RoundingPolicy.Truncate, 1.9, 1)]
    public void HonorsRoundingPolicy(RoundingPolicy policy, double value, byte expected)
    {
        var definition = new ScalarParameterDefinition("round", "Round", "Synthetic", 0, 1,
            Endianness.NotApplicable, new ParameterEncoding(ParameterEncodingType.RawU8), rawMinimum: 0, rawMaximum: 255,
            engineeringMinimum: 0, engineeringMaximum: 255, roundingPolicy: policy, writable: true,
            validationLevel: ValidationLevel.CrossEditorConfirmed, revisionScope: "synthetic");

        Assert.Equal(new[] { expected }, ParameterCodec.Encode(definition, value));
    }

    [Fact]
    public void ExactRoundingAndRangesRejectInvalidValues()
    {
        var exact = new ScalarParameterDefinition("exact", "Exact", "Synthetic", 0, 1,
            Endianness.NotApplicable, new ParameterEncoding(ParameterEncodingType.RawU8), rawMinimum: 0, rawMaximum: 10,
            engineeringMinimum: 0, engineeringMaximum: 10, roundingPolicy: RoundingPolicy.Exact, writable: true,
            validationLevel: ValidationLevel.CrossEditorConfirmed, revisionScope: "synthetic");

        Assert.Throws<ParameterEncodingException>(() => ParameterCodec.Encode(exact, 1.5));
        Assert.Throws<ParameterValueOutOfRangeException>(() => ParameterCodec.Encode(exact, 11));
    }

    [Fact]
    public void RoundTripIncludesScalarAndTableCellsAndIsByteIdentical()
    {
        var bytes = SyntheticFixture.Bytes();
        bytes[111] = 1;
        var image = RomImage.FromBytes(bytes);
        var profile = SyntheticFixture.Profile();

        var values = RomParameterReader.ReadAll(image, profile);
        var output = RomRoundTripEngine.RoundTrip(image, profile);

        Assert.Equal(profile.Parameters.Count + 4, values.Count);
        Assert.Equal(image.Hash, output.Hash);
        Assert.Equal(bytes, output.ToArray());
    }

    private static void AssertRoundTrip(
        ScalarParameterDefinition definition,
        double engineering,
        string expectedHex,
        byte[] rom)
    {
        var encoded = ParameterCodec.Encode(definition, engineering);
        encoded.CopyTo(rom, definition.Offset);
        var decoded = ParameterCodec.Decode(definition, rom);
        Assert.Equal(expectedHex, decoded.RawHex);
        Assert.Equal(engineering, decoded.EngineeringValue, 8);
    }

    private static ScalarParameterDefinition Definition(
        string id,
        int offset,
        int width,
        Endianness endianness,
        ParameterEncodingType type,
        double scale,
        double rawMinimum,
        double rawMaximum,
        double engineeringMinimum = double.MinValue,
        double engineeringMaximum = double.MaxValue,
        double engineeringOffset = 0) =>
        new(id, id, "Synthetic", offset, width, endianness, new ParameterEncoding(type, scale, engineeringOffset),
            rawMinimum: rawMinimum, rawMaximum: rawMaximum, engineeringMinimum: engineeringMinimum,
            engineeringMaximum: engineeringMaximum, writable: true, validationLevel: ValidationLevel.CrossEditorConfirmed,
            revisionScope: "synthetic");

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "HondaEcu.sln")))
        {
            directory = directory.Parent;
        }

        return directory?.FullName ?? throw new DirectoryNotFoundException("Repository root not found.");
    }

    private static readonly string ValidProfileJson = """
        {
          "schemaVersion": "1.0",
          "id": "synthetic-json-profile",
          "displayName": "Synthetic JSON profile",
          "description": "Contains no OEM data",
          "status": "experimental",
          "format": { "kind": "raw-binary", "exactSize": 32768, "headerBytes": 0, "paddingAllowed": false, "truncationAllowed": false },
          "identity": { "hashes": [], "signatures": [], "requiresExplicitConfirmation": true },
          "revisionScope": "synthetic-v1",
          "sources": [
            { "id": "synthetic-source", "title": "Synthetic source", "url": "https://example.invalid/synthetic",
              "accessedOn": "2026-09-04", "scope": "Tests only", "notes": "No OEM data" }
          ],
          "parameters": [
            {
              "id": "value", "displayName": "Value", "description": "Synthetic value", "offset": 16, "width": 1,
              "endianness": "not-applicable", "encoding": { "type": "raw-u8" }, "units": "raw",
              "rawRange": { "minimum": 0, "maximum": 255 },
              "engineeringRange": { "minimum": 0, "maximum": 255 },
              "roundingPolicy": "exact", "writable": true, "validationLevel": "cross-editor-confirmed",
              "revisionScope": "synthetic-v1", "sources": ["synthetic-source"], "notes": "Synthetic only", "status": "experimental"
            }
          ],
          "tables": [],
          "checksum": { "algorithmId": "unknown", "status": "unknown", "offset": 0, "length": 0,
            "evidenceLevel": "public-documentation", "excludedRegions": [], "notes": "No algorithm" }
        }
        """.ReplaceLineEndings("\n");
}
