using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed class RomProfile
{
    public RomProfile(
        string id,
        string displayName,
        string description,
        int expectedSize,
        string revisionScope,
        bool experimental,
        bool requiresExplicitConfirmation,
        IReadOnlyList<RomHash>? hashes = null,
        IReadOnlyList<RomSignature>? signatures = null,
        IReadOnlyList<ScalarParameterDefinition>? parameters = null,
        IReadOnlyList<TableParameterDefinition>? tables = null,
        IReadOnlyList<EvidenceReference>? sources = null,
        ChecksumDefinition? checksum = null,
        string schemaVersion = "1.0")
    {
        Id = id;
        DisplayName = displayName;
        Description = description;
        ExpectedSize = expectedSize;
        RevisionScope = revisionScope;
        Experimental = experimental;
        RequiresExplicitConfirmation = requiresExplicitConfirmation;
        Hashes = Array.AsReadOnly(hashes?.ToArray() ?? Array.Empty<RomHash>());
        Signatures = Array.AsReadOnly(signatures?.ToArray() ?? Array.Empty<RomSignature>());
        Parameters = Array.AsReadOnly(parameters?.ToArray() ?? Array.Empty<ScalarParameterDefinition>());
        Tables = Array.AsReadOnly(tables?.ToArray() ?? Array.Empty<TableParameterDefinition>());
        Sources = Array.AsReadOnly(sources?.ToArray() ?? Array.Empty<EvidenceReference>());
        Checksum = checksum;
        SchemaVersion = schemaVersion;
    }

    public string SchemaVersion { get; }

    [JsonIgnore]
    public string? SourcePath { get; private set; }

    public string Id { get; }

    public string DisplayName { get; }

    public string Description { get; }

    public int ExpectedSize { get; }

    public string RevisionScope { get; }

    public bool Experimental { get; }

    public bool RequiresExplicitConfirmation { get; }

    public IReadOnlyList<RomHash> Hashes { get; }

    public IReadOnlyList<RomSignature> Signatures { get; }

    public IReadOnlyList<ScalarParameterDefinition> Parameters { get; }

    public IReadOnlyList<ScalarParameterDefinition> ScalarParameters => Parameters;

    public IReadOnlyList<TableParameterDefinition> Tables { get; }

    public IReadOnlyList<TableParameterDefinition> TableParameters => Tables;

    public IReadOnlyList<EvidenceReference> Sources { get; }

    public ChecksumDefinition? Checksum { get; }

    public static RomProfile Load(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        var profile = Parse(File.ReadAllText(path));
        profile.SourcePath = Path.GetFullPath(path);
        return profile;
    }

    public static RomProfile Parse(string json)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(json);
        try
        {
            using var document = JsonDocument.Parse(json);
            var profile = ProfileParser.Parse(document.RootElement);
            var validation = profile.Validate();
            if (!validation.IsValid)
            {
                throw new ProfileValidationException(validation.Errors);
            }

            return profile;
        }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException)
        {
            throw new ProfileValidationException(new[] { $"Invalid profile JSON: {exception.Message}" }, exception);
        }
    }

    public ProfileValidationResult Validate()
    {
        var errors = new List<string>();
        var warnings = new List<string>();
        if (string.IsNullOrWhiteSpace(Id))
        {
            errors.Add("Profile id is required.");
        }

        if (string.IsNullOrWhiteSpace(DisplayName))
        {
            errors.Add("Profile displayName is required.");
        }

        if (string.IsNullOrWhiteSpace(RevisionScope))
        {
            errors.Add("Profile revisionScope is required.");
        }

        if (ExpectedSize <= 0)
        {
            errors.Add("Raw-binary profile format.exactSize must be greater than zero.");
        }

        foreach (var hash in Hashes)
        {
            if (hash.Sha256.Length != 64 || !hash.Sha256.All(Uri.IsHexDigit))
            {
                errors.Add($"Profile SHA-256 '{hash.Sha256}' is not 64 hexadecimal characters.");
            }

            if (!string.IsNullOrEmpty(hash.Crc32) && (hash.Crc32.Length != 8 || !hash.Crc32.All(Uri.IsHexDigit)))
            {
                errors.Add($"Profile CRC32 '{hash.Crc32}' is not 8 hexadecimal characters.");
            }
        }

        foreach (var signature in Signatures)
        {
            try
            {
                var bytes = HexUtilities.Parse(signature.HexBytes);
                if (signature.Offset < 0 || signature.Offset > ExpectedSize - bytes.Length)
                {
                    errors.Add($"Signature '{signature.Id}' is outside the ROM bounds.");
                }

                if (signature.Mask is not null && HexUtilities.Parse(signature.Mask).Length != bytes.Length)
                {
                    errors.Add($"Signature '{signature.Id}' mask length does not match its bytes.");
                }
            }
            catch (FormatException exception)
            {
                errors.Add($"Signature '{signature.Id}' is invalid: {exception.Message}");
            }
        }

        var ids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var sourceIds = Sources.Select(source => source.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);
        if (sourceIds.Count != Sources.Count)
        {
            errors.Add("Evidence source ids must be unique.");
        }

        foreach (var parameter in Parameters.Cast<ParameterDefinition>().Concat(Tables))
        {
            ValidateParameter(parameter, errors, warnings);
            if (!ids.Add(parameter.Id))
            {
                errors.Add($"Duplicate parameter id '{parameter.Id}'.");
            }

            foreach (var source in parameter.Sources.Where(source => !sourceIds.Contains(source)))
            {
                errors.Add($"Parameter '{parameter.Id}' references unknown evidence source '{source}'.");
            }
        }

        foreach (var table in Tables)
        {
            if (table.Rows <= 0 || table.Columns <= 0 || table.CellWidth <= 0)
            {
                errors.Add($"Table '{table.Id}' dimensions and cellWidth must be positive.");
            }
            else if ((long)table.Rows * table.Columns * table.CellWidth != table.Width)
            {
                errors.Add($"Table '{table.Id}' width does not equal rows * columns * cellWidth.");
            }
        }

        if (Checksum is not null &&
            (Checksum.Offset < 0 || Checksum.Length < 0 || Checksum.Offset > ExpectedSize - Checksum.Length))
        {
            errors.Add("Checksum byte range is outside the ROM bounds.");
        }

        if (Checksum is not null)
        {
            var checksumRanges = Checksum.Regions
                .Concat(Checksum.Length > 0 ? new[] { new ByteRange(Checksum.Offset, Checksum.Length) } : Array.Empty<ByteRange>())
                .ToArray();
            foreach (var range in checksumRanges)
            {
                if (range.Offset < 0 || range.Length <= 0 || range.Offset > ExpectedSize - range.Length)
                {
                    errors.Add("A checksum/excluded byte range is invalid or outside the ROM bounds.");
                    continue;
                }

                foreach (var parameter in Parameters.Cast<ParameterDefinition>().Concat(Tables)
                    .Where(parameter => parameter.Offset < range.EndExclusive && range.Offset < parameter.Offset + parameter.Width))
                {
                    errors.Add($"Calibration parameter '{parameter.Id}' overlaps checksum region at 0x{range.Offset:X}.");
                }
            }
        }

        return new ProfileValidationResult(errors.Count == 0, errors, warnings);
    }

    public ScalarParameterDefinition GetParameter(string id) =>
        Parameters.FirstOrDefault(parameter => string.Equals(parameter.Id, id, StringComparison.OrdinalIgnoreCase)) ??
        throw new KeyNotFoundException($"Profile '{Id}' does not contain scalar parameter '{id}'.");

    private void ValidateParameter(ParameterDefinition parameter, ICollection<string> errors, ICollection<string> warnings)
    {
        if (string.IsNullOrWhiteSpace(parameter.Id) || string.IsNullOrWhiteSpace(parameter.DisplayName) ||
            string.IsNullOrWhiteSpace(parameter.Description) || string.IsNullOrWhiteSpace(parameter.RevisionScope))
        {
            errors.Add("Every parameter requires id, displayName, description, and revisionScope.");
        }

        if (parameter.Offset < 0 || parameter.Width <= 0 || parameter.Offset > ExpectedSize - parameter.Width)
        {
            errors.Add($"Parameter '{parameter.Id}' byte range is outside the ROM bounds.");
        }

        if (parameter.RawMinimum > parameter.RawMaximum)
        {
            errors.Add($"Parameter '{parameter.Id}' raw minimum exceeds maximum.");
        }

        if (parameter.EngineeringMinimum > parameter.EngineeringMaximum)
        {
            errors.Add($"Parameter '{parameter.Id}' engineering minimum exceeds maximum.");
        }

        if (parameter.Writable && parameter.Encoding.Type == ParameterEncodingType.Unsupported)
        {
            errors.Add($"Parameter '{parameter.Id}' cannot be writable with Unsupported encoding.");
        }

        if (parameter.Writable && parameter.ValidationLevel == ValidationLevel.Disproved)
        {
            errors.Add($"Disproved parameter '{parameter.Id}' cannot be writable.");
        }

        if (parameter.Writable && !Experimental)
        {
            errors.Add($"Writable parameter '{parameter.Id}' is allowed only in an explicitly experimental profile at M0.");
        }

        if (parameter.Writable && parameter.RequiresUnverifiedWriteOverride)
        {
            warnings.Add($"Writable parameter '{parameter.Id}' requires an explicit unverified-write override.");
        }

        var requiredWidth = ParameterCodec.RequiredWidth(parameter.Encoding.Type);
        if (requiredWidth is not null && parameter is ScalarParameterDefinition && parameter.Width != requiredWidth)
        {
            errors.Add($"Parameter '{parameter.Id}' width {parameter.Width} is incompatible with {parameter.Encoding.Type}.");
        }
        if (requiredWidth is not null && parameter is TableParameterDefinition table && table.CellWidth != requiredWidth)
        {
            errors.Add($"Table '{parameter.Id}' cellWidth {table.CellWidth} is incompatible with {parameter.Encoding.Type}.");
        }

        var endiannessValid = parameter.Encoding.Type switch
        {
            ParameterEncodingType.RawU8 or ParameterEncodingType.RawS8 or
                ParameterEncodingType.LinearU8 or ParameterEncodingType.InverseU8 => parameter.Endianness == Endianness.NotApplicable,
            ParameterEncodingType.RawU16LittleEndian => parameter.Endianness == Endianness.Little,
            ParameterEncodingType.RawU16BigEndian => parameter.Endianness == Endianness.Big,
            ParameterEncodingType.LinearU16 or ParameterEncodingType.InverseU16 =>
                parameter.Endianness is Endianness.Little or Endianness.Big,
            ParameterEncodingType.LookupTable when parameter.Width == 1 || parameter is TableParameterDefinition { CellWidth: 1 } =>
                parameter.Endianness == Endianness.NotApplicable,
            ParameterEncodingType.LookupTable => parameter.Endianness is Endianness.Little or Endianness.Big,
            ParameterEncodingType.Unsupported => true,
            _ => false,
        };
        if (!endiannessValid)
        {
            errors.Add($"Parameter '{parameter.Id}' endianness {parameter.Endianness} is incompatible with {parameter.Encoding.Type}.");
        }

        if (parameter.Encoding.Type is ParameterEncodingType.LinearU8 or ParameterEncodingType.LinearU16 &&
            (!double.IsFinite(parameter.Encoding.Scale) || parameter.Encoding.Scale == 0))
        {
            errors.Add($"Parameter '{parameter.Id}' linear scale must be finite and non-zero.");
        }

        if (!double.IsFinite(parameter.Encoding.Scale) || !double.IsFinite(parameter.Encoding.Offset) ||
            !double.IsFinite(parameter.Encoding.Numerator) || !double.IsFinite(parameter.Encoding.DenominatorOffset) ||
            parameter.Encoding.Values.Any(value => !double.IsFinite(value)))
        {
            errors.Add($"Parameter '{parameter.Id}' encoding constants must all be finite.");
        }

        if (parameter.Encoding.Type is ParameterEncodingType.InverseU8 or ParameterEncodingType.InverseU16 &&
            (!double.IsFinite(parameter.Encoding.Numerator) || parameter.Encoding.Numerator == 0))
        {
            errors.Add($"Parameter '{parameter.Id}' inverse numerator must be finite and non-zero.");
        }

        if (parameter.Encoding.Type == ParameterEncodingType.LookupTable && parameter.Encoding.Values.Count == 0)
        {
            errors.Add($"Parameter '{parameter.Id}' lookup-table encoding requires values.");
        }
        if (parameter.Encoding.Type == ParameterEncodingType.LookupTable &&
            parameter.RoundingPolicy is not (RoundingPolicy.Exact or RoundingPolicy.Nearest))
        {
            errors.Add($"Parameter '{parameter.Id}' lookup-table encoding supports only Exact or Nearest rounding.");
        }
    }
}

public static class ProfileDocumentValidator
{
    public static ProfileValidationResult Validate(string json)
    {
        try
        {
            var profile = RomProfile.Parse(json);
            return profile.Validate();
        }
        catch (ProfileValidationException exception)
        {
            return new ProfileValidationResult(false, new[] { exception.Message }, Array.Empty<string>());
        }
    }

    public static ProfileValidationResult ValidateFile(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        return Validate(File.ReadAllText(path));
    }
}

public sealed record ProfileValidationResult(bool IsValid, IReadOnlyList<string> Errors, IReadOnlyList<string> Warnings);

public sealed class ProfileValidationException : IOException
{
    public ProfileValidationException(IEnumerable<string> errors, Exception? innerException = null)
        : base(string.Join(Environment.NewLine, errors), innerException)
    {
    }
}

public sealed class ProfileCatalog
{
    private readonly IReadOnlyList<RomProfile> _profiles;

    public ProfileCatalog(IEnumerable<RomProfile> profiles)
    {
        ArgumentNullException.ThrowIfNull(profiles);
        _profiles = Array.AsReadOnly(profiles.ToArray());
        if (_profiles.Select(profile => profile.Id).Distinct(StringComparer.OrdinalIgnoreCase).Count() != _profiles.Count)
        {
            throw new ArgumentException("Profile ids must be unique.", nameof(profiles));
        }
    }

    public IReadOnlyList<RomProfile> Profiles => _profiles;

    public static ProfileCatalog LoadDirectory(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        var files = Directory.EnumerateFiles(path, "*.json", SearchOption.AllDirectories)
            .Where(file => !file.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                .Any(segment => string.Equals(segment, "schemas", StringComparison.OrdinalIgnoreCase)));
        return new ProfileCatalog(files.Select(RomProfile.Load));
    }

    public RomProfile Get(string id) =>
        _profiles.FirstOrDefault(profile => string.Equals(profile.Id, id, StringComparison.OrdinalIgnoreCase)) ??
        throw new KeyNotFoundException($"Unknown ROM profile '{id}'.");
}

public static class RomIdentifier
{
    public static RomIdentity Identify(RomImage image, IEnumerable<RomProfile> profiles, string? explicitProfileId = null)
    {
        ArgumentNullException.ThrowIfNull(image);
        ArgumentNullException.ThrowIfNull(profiles);
        var profileList = profiles.ToArray();
        if (explicitProfileId is not null)
        {
            var selected = profileList.FirstOrDefault(profile => string.Equals(profile.Id, explicitProfileId, StringComparison.OrdinalIgnoreCase)) ??
                throw new KeyNotFoundException($"Unknown ROM profile '{explicitProfileId}'.");
            image.ValidateExactSize(selected.ExpectedSize, selected.Id);
            return new RomIdentity(true, selected.Id, RomIdentificationMethod.ExplicitOverride,
                "Profile explicitly selected by the user; identity was not inferred from file size.");
        }

        foreach (var profile in profileList)
        {
            if (profile.ExpectedSize == image.Size && profile.Hashes.Any(hash =>
                !string.IsNullOrWhiteSpace(hash.Sha256) && string.Equals(hash.Sha256, image.Hash.Sha256, StringComparison.OrdinalIgnoreCase)))
            {
                return new RomIdentity(true, profile.Id, RomIdentificationMethod.Sha256, "ROM SHA-256 matches the profile.");
            }
        }

        foreach (var profile in profileList)
        {
            if (profile.ExpectedSize == image.Size && profile.Signatures.Count > 0 &&
                profile.Signatures.All(signature => SignatureMatches(image.Span, signature)))
            {
                return new RomIdentity(true, profile.Id, RomIdentificationMethod.Signature, "All required profile signatures match.");
            }
        }

        return RomIdentity.Unknown();
    }

    public static IReadOnlyList<RomProfile> FindPossibleProfiles(RomImage image, IEnumerable<RomProfile> profiles) =>
        profiles.Where(profile => profile.ExpectedSize == image.Size &&
            (profile.Hashes.Any(hash => string.Equals(hash.Sha256, image.Hash.Sha256, StringComparison.OrdinalIgnoreCase)) ||
             (profile.Signatures.Count > 0 && profile.Signatures.All(signature => SignatureMatches(image.Span, signature)))))
            .ToArray();

    private static bool SignatureMatches(ReadOnlySpan<byte> bytes, RomSignature signature)
    {
        var expected = HexUtilities.Parse(signature.HexBytes);
        var mask = signature.Mask is null ? null : HexUtilities.Parse(signature.Mask);
        if (signature.Offset < 0 || signature.Offset > bytes.Length - expected.Length)
        {
            return false;
        }

        for (var index = 0; index < expected.Length; index++)
        {
            var maskByte = mask?[index] ?? byte.MaxValue;
            if ((bytes[signature.Offset + index] & maskByte) != (expected[index] & maskByte))
            {
                return false;
            }
        }

        return true;
    }
}

internal static class ProfileParser
{
    public static RomProfile Parse(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException("Profile root must be an object.");
        }

        root.EnsureOnlyProperties("$schema", "schemaVersion", "id", "displayName", "description", "status", "format",
            "identity", "revisionScope", "sources", "parameters", "tables", "checksum");
        _ = root.OptionalString("$schema");
        if (!string.Equals(root.RequiredString("schemaVersion"), "1.0", StringComparison.Ordinal))
        {
            throw new JsonException("Only ROM profile schemaVersion '1.0' is supported.");
        }

        var format = root.RequiredObject("format");
        format.EnsureOnlyProperties("kind", "exactSize", "headerBytes", "paddingAllowed", "truncationAllowed");
        if (format.ValueKind == JsonValueKind.Object)
        {
            var kind = format.RequiredString("kind");
            if (!string.Equals(kind, "raw-binary", StringComparison.Ordinal))
            {
                throw new JsonException("M0 supports only raw-binary profile formats.");
            }

            if (format.RequiredInt32("headerBytes") != 0 ||
                format.RequiredBoolean("paddingAllowed") ||
                format.RequiredBoolean("truncationAllowed"))
            {
                throw new JsonException("Raw M0 profiles cannot use headers, padding, or truncation.");
            }
        }

        var identity = root.RequiredObject("identity");
        identity.EnsureOnlyProperties("hashes", "signatures", "requiresExplicitConfirmation");
        var hashesElement = identity.RequiredArray("hashes");
        var signaturesElement = identity.RequiredArray("signatures");
        var status = ParseEnumStrict<ParameterStatus>(root.RequiredString("status"));
        if (status != ParameterStatus.Experimental)
        {
            throw new JsonException("M0 ROM profiles must have top-level status 'experimental'.");
        }
        return new RomProfile(
            root.RequiredString("id"),
            root.RequiredString("displayName"),
            root.RequiredString("description"),
            format.RequiredInt32("exactSize"),
            root.RequiredString("revisionScope"),
            status == ParameterStatus.Experimental,
            identity.RequiredBoolean("requiresExplicitConfirmation"),
            ParseHashes(hashesElement),
            ParseSignatures(signaturesElement),
            ParseParameters(root.RequiredArray("parameters")),
            ParseTables(root.RequiredArray("tables")),
            ParseSources(root.RequiredArray("sources")),
            ParseChecksum(root.RequiredObject("checksum")),
            root.RequiredString("schemaVersion"));
    }

    private static IReadOnlyList<RomHash> ParseHashes(JsonElement? array)
    {
        if (array is null)
        {
            return Array.Empty<RomHash>();
        }

        var results = new List<RomHash>();
        foreach (var element in array.Value.EnumerateArray())
        {
            if (element.ValueKind is not (JsonValueKind.String or JsonValueKind.Object))
            {
                throw new JsonException("Identity hashes must be SHA-256 strings or hash objects.");
            }

            if (element.ValueKind == JsonValueKind.Object)
            {
                element.EnsureOnlyProperties("sha256", "crc32");
            }

            if (element.ValueKind == JsonValueKind.String)
            {
                results.Add(new RomHash(element.GetString() ?? string.Empty, string.Empty));
            }
            else
            {
                var crc32 = element.OptionalString("crc32");
                if (crc32 is not null && (crc32.Length != 8 || !crc32.All(Uri.IsHexDigit)))
                {
                    throw new JsonException("Identity crc32 must contain exactly 8 hexadecimal characters when present.");
                }

                results.Add(new RomHash(element.RequiredString("sha256"), crc32 ?? string.Empty));
            }
        }

        return results;
    }

    private static IReadOnlyList<RomSignature> ParseSignatures(JsonElement? array)
    {
        if (array is null)
        {
            return Array.Empty<RomSignature>();
        }

        return array.Value.EnumerateArray().Select(element =>
        {
            if (element.ValueKind != JsonValueKind.Object)
            {
                throw new JsonException("ROM signatures must be objects.");
            }

            element.EnsureOnlyProperties("id", "offset", "hexBytes", "mask", "description");
            return new RomSignature(
                element.RequiredString("id"),
                element.RequiredInt32("offset"),
                element.RequiredString("hexBytes"),
                element.OptionalString("mask"),
                element.OptionalString("description"));
        }).ToArray();
    }

    private static IReadOnlyList<ScalarParameterDefinition> ParseParameters(JsonElement? array) =>
        array is null
            ? Array.Empty<ScalarParameterDefinition>()
            : array.Value.EnumerateArray().Select(ParseScalar).ToArray();

    private static ScalarParameterDefinition ParseScalar(JsonElement element)
    {
        element.EnsureOnlyProperties("id", "displayName", "description", "offset", "width", "endianness", "encoding",
            "units", "rawRange", "engineeringRange", "roundingPolicy", "writable", "validationLevel", "revisionScope",
            "sources", "notes", "status");
        var common = ParseCommon(element);
        return new ScalarParameterDefinition(common.Id, common.DisplayName, common.Description, common.Offset, common.Width,
            common.Endianness, common.Encoding, common.Units, common.RawMinimum, common.RawMaximum,
            common.EngineeringMinimum, common.EngineeringMaximum, common.RoundingPolicy, common.Writable,
            common.ValidationLevel, common.RevisionScope, common.Sources, common.Notes, common.Status);
    }

    private static IReadOnlyList<TableParameterDefinition> ParseTables(JsonElement? array)
    {
        if (array is null)
        {
            return Array.Empty<TableParameterDefinition>();
        }

        return array.Value.EnumerateArray().Select(element =>
        {
            element.EnsureOnlyProperties("id", "displayName", "description", "offset", "width", "rows", "columns", "cellWidth",
                "endianness", "encoding", "units", "rawRange", "engineeringRange", "roundingPolicy", "writable",
                "validationLevel", "revisionScope", "sources", "notes", "status");
            var common = ParseCommon(element);
            var rows = element.RequiredInt32("rows");
            var columns = element.RequiredInt32("columns");
            var cellWidth = element.RequiredInt32("cellWidth");
            return new TableParameterDefinition(common.Id, common.DisplayName, common.Description, common.Offset, common.Width,
                rows, columns, cellWidth, common.Endianness, common.Encoding, common.Units, common.RawMinimum,
                common.RawMaximum, common.EngineeringMinimum, common.EngineeringMaximum, common.RoundingPolicy,
                common.Writable, common.ValidationLevel, common.RevisionScope, common.Sources, common.Notes, common.Status);
        }).ToArray();
    }

    private static ParsedParameter ParseCommon(JsonElement element)
    {
        var rawRange = element.RequiredObject("rawRange");
        var engineeringRange = element.RequiredObject("engineeringRange");
        rawRange.EnsureOnlyProperties("minimum", "maximum");
        engineeringRange.EnsureOnlyProperties("minimum", "maximum");
        if (!element.TryGetProperty("encoding", out var encodingElement))
        {
            throw new JsonException("Required property 'encoding' is missing.");
        }
        var sources = element.RequiredArray("sources").EnumerateArray().Select(item =>
        {
            if (item.ValueKind != JsonValueKind.String)
            {
                throw new JsonException("Parameter source references must be string ids.");
            }

            return item.GetString() ?? string.Empty;
        }).ToArray();
        if (sources.Length == 0 || sources.Any(string.IsNullOrWhiteSpace))
        {
            throw new JsonException($"Parameter '{element.RequiredString("id")}' requires at least one non-empty evidence source id.");
        }
        return new ParsedParameter(
            element.RequiredString("id"),
            element.RequiredString("displayName"),
            element.RequiredString("description"),
            element.RequiredInt32("offset"),
            element.RequiredInt32("width"),
            ParseEnumStrict<Endianness>(element.RequiredString("endianness")),
            ParseEncoding(encodingElement),
            element.RequiredString("units"),
            rawRange.RequiredDouble("minimum"),
            rawRange.RequiredDouble("maximum"),
            engineeringRange.RequiredDouble("minimum"),
            engineeringRange.RequiredDouble("maximum"),
            ParseEnumStrict<RoundingPolicy>(element.RequiredString("roundingPolicy")),
            element.RequiredBoolean("writable"),
            ParseEnumStrict<ValidationLevel>(element.RequiredString("validationLevel")),
            element.RequiredString("revisionScope"),
            sources,
            element.RequiredString("notes"),
            ParseEnumStrict<ParameterStatus>(element.RequiredString("status")));
    }

    private static ParameterEncoding ParseEncoding(JsonElement element)
    {
        var typeText = element.ValueKind == JsonValueKind.String ? element.GetString() : element.OptionalString("type");
        if (string.IsNullOrWhiteSpace(typeText))
        {
            throw new JsonException("Parameter encoding.type is required.");
        }

        if (element.ValueKind == JsonValueKind.Object)
        {
            element.EnsureOnlyProperties("type", "scale", "offset", "numerator", "denominatorOffset", "values");
        }
        else if (element.ValueKind != JsonValueKind.String)
        {
            throw new JsonException("Parameter encoding must be a string or object.");
        }

        double[]? values = null;
        if (element.ValueKind == JsonValueKind.Object && element.OptionalArray("values") is { } valuesElement)
        {
            values = valuesElement.EnumerateArray().Select(item =>
            {
                if (!item.TryGetDouble(out var value) || !double.IsFinite(value))
                {
                    throw new JsonException("Encoding lookup values must be finite numbers.");
                }

                return value;
            }).ToArray();
            if (values.Length == 0)
            {
                throw new JsonException("Encoding values must contain at least one number when present.");
            }
        }
        return new ParameterEncoding(
            ParseEnumStrict<ParameterEncodingType>(typeText),
            element.ValueKind == JsonValueKind.Object ? element.OptionalDouble("scale") ?? 1 : 1,
            element.ValueKind == JsonValueKind.Object ? element.OptionalDouble("offset") ?? 0 : 0,
            element.ValueKind == JsonValueKind.Object ? element.OptionalDouble("numerator") ?? 1 : 1,
            element.ValueKind == JsonValueKind.Object ? element.OptionalDouble("denominatorOffset") ?? 0 : 0,
            values);
    }

    private static IReadOnlyList<EvidenceReference> ParseSources(JsonElement? array)
    {
        if (array is null)
        {
            return Array.Empty<EvidenceReference>();
        }

        return array.Value.EnumerateArray().Select(element =>
        {
            if (element.ValueKind != JsonValueKind.Object)
            {
                throw new JsonException("Evidence references must be objects.");
            }

            element.EnsureOnlyProperties("id", "title", "url", "commitSha", "accessedOn", "scope", "notes");
            var dateText = element.RequiredString("accessedOn");
            if (!DateOnly.TryParseExact(dateText, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var date))
            {
                throw new JsonException($"Evidence accessedOn '{dateText}' is not an ISO date.");
            }

            var url = element.RequiredString("url");
            if (!Uri.TryCreate(url, UriKind.Absolute, out _))
            {
                throw new JsonException($"Evidence URL '{url}' is not absolute.");
            }

            var commitSha = element.OptionalString("commitSha");
            if (commitSha is not null && (commitSha.Length != 40 || !commitSha.All(Uri.IsHexDigit)))
            {
                throw new JsonException("Evidence commitSha must contain exactly 40 hexadecimal characters.");
            }

            return new EvidenceReference(
                element.RequiredString("id"),
                element.RequiredString("title"),
                url,
                commitSha,
                date,
                element.OptionalString("scope"),
                element.OptionalString("notes"));
        }).ToArray();
    }

    private static ChecksumDefinition? ParseChecksum(JsonElement? element)
    {
        if (element is null)
        {
            return null;
        }

        element.Value.EnsureOnlyProperties("algorithmId", "status", "offset", "length", "evidenceLevel", "excludedRegions", "notes");

        var regions = element.Value.OptionalArray("excludedRegions")?.EnumerateArray()
            .Select(region =>
            {
                region.EnsureOnlyProperties("offset", "length");
                return new ByteRange(region.RequiredInt32("offset"), region.RequiredInt32("length"));
            }).ToArray();
        return new ChecksumDefinition(
            element.Value.RequiredString("algorithmId"),
            ParseEnumStrict<ChecksumStatus>(element.Value.RequiredString("status")),
            element.Value.RequiredInt32("offset"),
            element.Value.RequiredInt32("length"),
            ParseEnumStrict<ValidationLevel>(element.Value.RequiredString("evidenceLevel")),
            regions ?? throw new JsonException("Checksum excludedRegions array is required."),
            element.Value.RequiredString("notes"));
    }

    private static T ParseEnumStrict<T>(string text)
        where T : struct, Enum
    {
        foreach (var value in Enum.GetValues<T>())
        {
            if (string.Equals(JsonNamingPolicy.KebabCaseLower.ConvertName(value.ToString()), text, StringComparison.Ordinal))
            {
                return value;
            }
        }

        throw new JsonException($"Unsupported {typeof(T).Name} value '{text}'.");
    }

    private sealed record ParsedParameter(
        string Id,
        string DisplayName,
        string Description,
        int Offset,
        int Width,
        Endianness Endianness,
        ParameterEncoding Encoding,
        string Units,
        double RawMinimum,
        double RawMaximum,
        double EngineeringMinimum,
        double EngineeringMaximum,
        RoundingPolicy RoundingPolicy,
        bool Writable,
        ValidationLevel ValidationLevel,
        string RevisionScope,
        IReadOnlyList<string> Sources,
        string? Notes,
        ParameterStatus Status);
}

internal static class JsonElementExtensions
{
    public static string RequiredString(this JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var property) || property.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(property.GetString()))
        {
            throw new JsonException($"Required string property '{name}' is missing or empty.");
        }

        return property.GetString()!;
    }

    public static int RequiredInt32(this JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var property) || !property.TryGetInt32(out var value))
        {
            throw new JsonException($"Required integer property '{name}' is missing or invalid.");
        }

        return value;
    }

    public static double RequiredDouble(this JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var property) || !property.TryGetDouble(out var value) || !double.IsFinite(value))
        {
            throw new JsonException($"Required finite numeric property '{name}' is missing or invalid.");
        }

        return value;
    }

    public static bool RequiredBoolean(this JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var property) || property.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
        {
            throw new JsonException($"Required Boolean property '{name}' is missing or invalid.");
        }

        return property.GetBoolean();
    }

    public static JsonElement RequiredObject(this JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var property) || property.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException($"Required object property '{name}' is missing or invalid.");
        }

        return property;
    }

    public static JsonElement RequiredArray(this JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var property) || property.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException($"Required array property '{name}' is missing or invalid.");
        }

        return property;
    }

    public static string? OptionalString(this JsonElement element, string name) =>
        !element.TryGetProperty(name, out var property)
            ? null
            : property.ValueKind == JsonValueKind.String
                ? property.GetString()
                : throw new JsonException($"Optional property '{name}' must be a string when present.");

    public static int? OptionalInt32(this JsonElement element, string name) =>
        !element.TryGetProperty(name, out var property)
            ? null
            : property.TryGetInt32(out var value)
                ? value
                : throw new JsonException($"Optional property '{name}' must be an integer when present.");

    public static double? OptionalDouble(this JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var property))
        {
            return null;
        }

        if (!property.TryGetDouble(out var value) || !double.IsFinite(value))
        {
            throw new JsonException($"Optional property '{name}' must be a finite number when present.");
        }

        return value;
    }

    public static bool? OptionalBoolean(this JsonElement element, string name) =>
        !element.TryGetProperty(name, out var property)
            ? null
            : property.ValueKind is JsonValueKind.True or JsonValueKind.False
                ? property.GetBoolean()
                : throw new JsonException($"Optional property '{name}' must be Boolean when present.");

    public static JsonElement? OptionalObject(this JsonElement element, string name) =>
        !element.TryGetProperty(name, out var property)
            ? null
            : property.ValueKind == JsonValueKind.Object
                ? property
                : throw new JsonException($"Optional property '{name}' must be an object when present.");

    public static JsonElement? OptionalArray(this JsonElement element, string name) =>
        !element.TryGetProperty(name, out var property)
            ? null
            : property.ValueKind == JsonValueKind.Array
                ? property
                : throw new JsonException($"Optional property '{name}' must be an array when present.");

    public static void EnsureOnlyProperties(this JsonElement element, params string[] allowed)
    {
        if (element.ValueKind != JsonValueKind.Object)
        {
            throw new JsonException("Expected an object.");
        }

        var names = allowed.ToHashSet(StringComparer.Ordinal);
        foreach (var property in element.EnumerateObject())
        {
            if (!names.Contains(property.Name))
            {
                throw new JsonException($"Unknown property '{property.Name}' is not allowed.");
            }
        }
    }
}

internal static class HexUtilities
{
    public static byte[] Parse(string hex)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(hex);
        var bytes = new List<byte>();
        var index = 0;
        while (index < hex.Length)
        {
            if (IsSeparator(hex[index]))
            {
                if (bytes.Count == 0)
                {
                    throw new FormatException("Hexadecimal byte strings cannot start with a separator.");
                }

                index++;
                continue;
            }

            if (!Uri.IsHexDigit(hex[index]) || index + 1 >= hex.Length || !Uri.IsHexDigit(hex[index + 1]))
            {
                throw new FormatException("Hexadecimal strings must contain adjacent, complete byte pairs.");
            }

            bytes.Add(Convert.ToByte(hex.Substring(index, 2), 16));
            index += 2;
        }

        if (bytes.Count == 0)
        {
            throw new FormatException("Hexadecimal strings must contain at least one complete byte.");
        }

        return bytes.ToArray();

        static bool IsSeparator(char character) => character is ' ' or '\t' or ':' or '-';
    }

    public static string Format(ReadOnlySpan<byte> bytes) => Convert.ToHexString(bytes);
}
