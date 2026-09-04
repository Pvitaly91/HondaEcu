using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public enum ValidationLevel
{
    PublicDocumentation,
    OracleObserved,
    CromeObserved,
    HtsObserved,
    CrossEditorConfirmed,
    StaticAnalysisConfirmed,
    EmulatorObserved,
    BenchConfirmed,
    VehicleConfirmed,
    Disproved,
}

public enum ParameterEncodingType
{
    RawU8,
    RawS8,
    RawU16LittleEndian,
    RawU16BigEndian,
    LinearU8,
    LinearU16,
    InverseU8,
    InverseU16,
    LookupTable,
    Unsupported,
}

public enum Endianness
{
    NotApplicable,
    Little,
    Big,
}

public enum RoundingPolicy
{
    Exact,
    Nearest,
    ToEven,
    Floor,
    Ceiling,
    Truncate,
}

public enum ParameterStatus
{
    Candidate,
    Documented,
    Experimental,
    Verified,
}

public enum ChecksumStatus
{
    Unknown,
    Valid,
    Invalid,
    NotApplicable,
}

public enum FlashReadinessStatus
{
    PcInspectionOnly,
    CrossEditorValidated,
    StaticAnalysisValidated,
    BenchCandidate,
    BenchValidated,
    VehicleValidated,
}

public enum FlashSafetyStatus
{
    NotFlashReady,
    FlashReady,
}

public enum RomIdentificationMethod
{
    None,
    Sha256,
    Signature,
    ExplicitOverride,
}

public sealed record EvidenceReference(
    string Id,
    string Title,
    string Url,
    string? CommitSha = null,
    DateOnly? AccessedOn = null,
    string? Scope = null,
    string? Notes = null);

public sealed record RomHash(string Sha256, string Crc32)
{
    public static RomHash Compute(ReadOnlySpan<byte> bytes) =>
        new(HashUtilities.Sha256(bytes), HashUtilities.Crc32(bytes));
}

public sealed record RomSignature(
    string Id,
    int Offset,
    string HexBytes,
    string? Mask = null,
    string? Description = null);

public sealed record RomIdentity(
    bool IsIdentified,
    string? ProfileId,
    RomIdentificationMethod Method,
    string Description)
{
    public static RomIdentity Unknown(string description = "ROM is not identified by a trusted hash or signature.") =>
        new(false, null, RomIdentificationMethod.None, description);
}

public sealed record ParameterEncoding
{
    public ParameterEncoding(
        ParameterEncodingType type,
        double scale = 1,
        double offset = 0,
        double numerator = 1,
        double denominatorOffset = 0,
        IReadOnlyList<double>? values = null)
    {
        Type = type;
        Scale = scale;
        Offset = offset;
        Numerator = numerator;
        DenominatorOffset = denominatorOffset;
        Values = Array.AsReadOnly(values?.ToArray() ?? Array.Empty<double>());
    }

    public ParameterEncodingType Type { get; }

    public double Scale { get; }

    public double Offset { get; }

    public double Numerator { get; }

    public double DenominatorOffset { get; }

    public IReadOnlyList<double> Values { get; }
}

public abstract record ParameterDefinition
{
    protected ParameterDefinition(
        string id,
        string displayName,
        string description,
        int offset,
        int width,
        Endianness endianness,
        ParameterEncoding encoding,
        string units,
        double rawMinimum,
        double rawMaximum,
        double engineeringMinimum,
        double engineeringMaximum,
        RoundingPolicy roundingPolicy,
        bool writable,
        ValidationLevel validationLevel,
        string revisionScope,
        IReadOnlyList<string>? sources,
        string? notes,
        ParameterStatus status)
    {
        Id = id;
        DisplayName = displayName;
        Description = description;
        Offset = offset;
        Width = width;
        Endianness = endianness;
        Encoding = encoding;
        Units = units;
        RawMinimum = rawMinimum;
        RawMaximum = rawMaximum;
        EngineeringMinimum = engineeringMinimum;
        EngineeringMaximum = engineeringMaximum;
        RoundingPolicy = roundingPolicy;
        Writable = writable;
        ValidationLevel = validationLevel;
        RevisionScope = revisionScope;
        Sources = Array.AsReadOnly(sources?.ToArray() ?? Array.Empty<string>());
        Notes = notes;
        Status = status;
    }

    public string Id { get; }

    public string DisplayName { get; }

    public string Description { get; }

    public int Offset { get; }

    public int Width { get; }

    public Endianness Endianness { get; }

    public ParameterEncoding Encoding { get; }

    public string Units { get; }

    public double RawMinimum { get; }

    public double RawMaximum { get; }

    public double EngineeringMinimum { get; }

    public double EngineeringMaximum { get; }

    public RoundingPolicy RoundingPolicy { get; }

    public bool Writable { get; }

    public ValidationLevel ValidationLevel { get; }

    public string RevisionScope { get; }

    public IReadOnlyList<string> Sources { get; }

    public string? Notes { get; }

    public ParameterStatus Status { get; }

    public bool RequiresUnverifiedWriteOverride =>
        Status == ParameterStatus.Candidate ||
        ValidationLevel is ValidationLevel.PublicDocumentation or
            ValidationLevel.OracleObserved or
            ValidationLevel.CromeObserved or
            ValidationLevel.HtsObserved;
}

public sealed record ScalarParameterDefinition : ParameterDefinition
{
    public ScalarParameterDefinition(
        string id,
        string displayName,
        string description,
        int offset,
        int width,
        Endianness endianness,
        ParameterEncoding encoding,
        string units = "raw",
        double rawMinimum = double.MinValue,
        double rawMaximum = double.MaxValue,
        double engineeringMinimum = double.MinValue,
        double engineeringMaximum = double.MaxValue,
        RoundingPolicy roundingPolicy = RoundingPolicy.Nearest,
        bool writable = false,
        ValidationLevel validationLevel = ValidationLevel.PublicDocumentation,
        string revisionScope = "unspecified",
        IReadOnlyList<string>? sources = null,
        string? notes = null,
        ParameterStatus status = ParameterStatus.Candidate)
        : base(id, displayName, description, offset, width, endianness, encoding, units, rawMinimum, rawMaximum,
            engineeringMinimum, engineeringMaximum, roundingPolicy, writable, validationLevel, revisionScope, sources, notes, status)
    {
    }
}

public sealed record TableParameterDefinition : ParameterDefinition
{
    public TableParameterDefinition(
        string id,
        string displayName,
        string description,
        int offset,
        int width,
        int rows,
        int columns,
        int cellWidth,
        Endianness endianness,
        ParameterEncoding encoding,
        string units = "raw",
        double rawMinimum = double.MinValue,
        double rawMaximum = double.MaxValue,
        double engineeringMinimum = double.MinValue,
        double engineeringMaximum = double.MaxValue,
        RoundingPolicy roundingPolicy = RoundingPolicy.Nearest,
        bool writable = false,
        ValidationLevel validationLevel = ValidationLevel.PublicDocumentation,
        string revisionScope = "unspecified",
        IReadOnlyList<string>? sources = null,
        string? notes = null,
        ParameterStatus status = ParameterStatus.Candidate)
        : base(id, displayName, description, offset, width, endianness, encoding, units, rawMinimum, rawMaximum,
            engineeringMinimum, engineeringMaximum, roundingPolicy, writable, validationLevel, revisionScope, sources, notes, status)
    {
        Rows = rows;
        Columns = columns;
        CellWidth = cellWidth;
    }

    public int Rows { get; }

    public int Columns { get; }

    public int CellWidth { get; }
}

public sealed record ParameterValue(
    string ParameterId,
    double EngineeringValue,
    long RawValue,
    string RawHex,
    int Offset,
    ValidationLevel ValidationLevel,
    bool Writable);

public sealed record ParameterChange(
    string ParameterId,
    double RequestedValue,
    ParameterValue Before,
    ParameterValue After,
    int Offset,
    string OldHex,
    string NewHex);

public sealed record ByteRange(int Offset, int Length)
{
    public int EndExclusive => checked(Offset + Length);

    public bool Contains(int offset) => offset >= Offset && offset < EndExclusive;
}

public sealed record ChecksumDefinition
{
    public ChecksumDefinition(
        string algorithmId,
        ChecksumStatus status,
        int offset,
        int length,
        ValidationLevel evidenceLevel,
        IReadOnlyList<ByteRange>? excludedRegions = null,
        string? notes = null)
    {
        AlgorithmId = algorithmId;
        Status = status;
        Offset = offset;
        Length = length;
        EvidenceLevel = evidenceLevel;
        ExcludedRegions = Array.AsReadOnly(excludedRegions?.ToArray() ?? Array.Empty<ByteRange>());
        Notes = notes;
    }

    public string AlgorithmId { get; }

    public ChecksumStatus Status { get; }

    public int Offset { get; }

    public int Length { get; }

    public ValidationLevel EvidenceLevel { get; }

    public IReadOnlyList<ByteRange> ExcludedRegions { get; }

    public string? Notes { get; }

    [JsonIgnore]
    public IReadOnlyList<ByteRange> Regions => ExcludedRegions;
}

public sealed record ChecksumEvaluation(
    ChecksumStatus Status,
    string Bytes,
    string AlgorithmId,
    ValidationLevel EvidenceLevel);

public static class JsonDefaults
{
    public static JsonSerializerOptions Create(bool writeIndented = true)
    {
        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DictionaryKeyPolicy = JsonNamingPolicy.CamelCase,
            PropertyNameCaseInsensitive = true,
            WriteIndented = writeIndented,
        };
        options.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.KebabCaseLower, allowIntegerValues: false));
        options.Converters.Add(new DateOnlyJsonConverter());
        return options;
    }

    public static JsonSerializerOptions Options { get; } = Create();

    private sealed class DateOnlyJsonConverter : JsonConverter<DateOnly>
    {
        public override DateOnly Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options) =>
            DateOnly.Parse(reader.GetString() ?? throw new JsonException("Expected a date string."), System.Globalization.CultureInfo.InvariantCulture);

        public override void Write(Utf8JsonWriter writer, DateOnly value, JsonSerializerOptions options) =>
            writer.WriteStringValue(value.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture));
    }
}
