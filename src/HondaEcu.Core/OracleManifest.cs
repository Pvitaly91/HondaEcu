using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public enum OracleObservationRole { Training, Holdout }

public sealed record OracleFileEvidence(string RomPath, RomHash RomHash);

public sealed record OracleCase(
    string ParameterId,
    double EngineeringValue,
    string RomPath,
    RomHash RomHash,
    DateTimeOffset CreatedAt,
    IReadOnlyList<DiffRange> DiffRanges,
    string? UserNotes = null,
    double? DisplayedValue = null)
{
    public OracleObservationRole Role { get; init; } = OracleObservationRole.Training;
    public string? ObservationId { get; init; }
}

public sealed record OracleManifest(
    string FormatVersion,
    string ReferenceTool,
    string ToolVersion,
    IReadOnlyList<string> Plugins,
    bool PluginsDisabled,
    string ProfileId,
    string BaselinePath,
    RomHash BaselineHash,
    string NoOpPath,
    RomHash NoOpHash,
    DateTimeOffset CreatedAt,
    IReadOnlyList<DiffRange> NoOpNormalizationRanges,
    IReadOnlyList<OracleCase> Cases,
    string? UserNotes = null)
{
    public string? ToolEdition { get; init; }
    public OracleFileEvidence? IndependentNoOp { get; init; }
    public OracleFileEvidence? ResavedNoOp { get; init; }
    public string? TransformationProfileId { get; init; }
    public IReadOnlyDictionary<string, OracleRoundingDomain> RoundingDomains { get; init; } =
        new Dictionary<string, OracleRoundingDomain>();
    [JsonIgnore]
    public string? SourcePath { get; init; }
    [JsonIgnore]
    public IReadOnlyList<string> MigrationWarnings => FormatVersion == "1.0"
        ? new[] { "Legacy manifest 1.0: cases default to discovery/training; editor edition, independent no-op, resave and holdout evidence must be collected before confirmation." }
        : Array.Empty<string>();

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));

    public static OracleManifest Parse(string json)
    {
        var manifest = JsonSerializer.Deserialize<OracleManifest>(json, JsonDefaults.Options) ??
            throw new JsonException("Oracle manifest is empty.");
        OracleManifestService.Validate(manifest);
        return manifest;
    }

    public static OracleManifest Load(string path) => Parse(File.ReadAllText(path)) with { SourcePath = Path.GetFullPath(path) };
}

public static class OracleManifestService
{
    public static void Validate(OracleManifest manifest)
    {
        ArgumentNullException.ThrowIfNull(manifest);
        if (manifest.FormatVersion is not ("1.0" or "2.0") ||
            string.IsNullOrWhiteSpace(manifest.ReferenceTool) || string.IsNullOrWhiteSpace(manifest.ToolVersion) ||
            string.IsNullOrWhiteSpace(manifest.ProfileId) || string.IsNullOrWhiteSpace(manifest.BaselinePath) ||
            string.IsNullOrWhiteSpace(manifest.NoOpPath) || manifest.BaselineHash is null || manifest.NoOpHash is null ||
            manifest.Plugins is null || manifest.NoOpNormalizationRanges is null || manifest.Cases is null ||
            manifest.CreatedAt == default || manifest.RoundingDomains is null)
        {
            throw new InvalidDataException("Oracle manifest is missing required version, tool provenance, paths, hashes, dates, or collections.");
        }

        ValidateHash(manifest.BaselineHash, "baseline");
        ValidateHash(manifest.NoOpHash, "no-op");
        if (manifest.Plugins.Any(string.IsNullOrWhiteSpace))
        {
            throw new InvalidDataException("Oracle plugin names cannot be empty.");
        }

        ValidateRanges(manifest.NoOpNormalizationRanges, "no-op normalization");
        foreach (var item in new[] { manifest.IndependentNoOp, manifest.ResavedNoOp }.OfType<OracleFileEvidence>())
        {
            if (string.IsNullOrWhiteSpace(item.RomPath) || item.RomHash is null)
                throw new InvalidDataException("No-op evidence requires a path and hash.");
            ValidateHash(item.RomHash, "additional no-op");
        }
        foreach (var domain in manifest.RoundingDomains)
        {
            if (string.IsNullOrWhiteSpace(domain.Key) || domain.Value is null ||
                !double.IsFinite(domain.Value.Minimum) || !double.IsFinite(domain.Value.Maximum) ||
                domain.Value.Minimum > domain.Value.Maximum || string.IsNullOrWhiteSpace(domain.Value.Documentation))
                throw new InvalidDataException("Rounding domains require finite ordered bounds and documentation.");
        }
        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var oracleCase in manifest.Cases)
        {
            if (oracleCase is null || string.IsNullOrWhiteSpace(oracleCase.ParameterId) ||
                string.IsNullOrWhiteSpace(oracleCase.RomPath) || oracleCase.RomHash is null ||
                oracleCase.DiffRanges is null || !double.IsFinite(oracleCase.EngineeringValue) ||
                (oracleCase.DisplayedValue is { } displayed && !double.IsFinite(displayed)) ||
                oracleCase.CreatedAt == default || !Enum.IsDefined(oracleCase.Role) ||
                (oracleCase.ObservationId is not null && (string.IsNullOrWhiteSpace(oracleCase.ObservationId) || !ids.Add(oracleCase.ObservationId))))
            {
                throw new InvalidDataException("Oracle case is missing required provenance or contains a non-finite value.");
            }

            ValidateHash(oracleCase.RomHash, $"case '{oracleCase.ParameterId}'");
            ValidateRanges(oracleCase.DiffRanges, $"case '{oracleCase.ParameterId}'");
        }
    }

    public static OracleManifest Create(
        string referenceTool,
        string toolVersion,
        string profileId,
        string baselinePath,
        string noOpPath,
        bool pluginsDisabled,
        IReadOnlyList<string>? plugins = null,
        string? userNotes = null,
        string? toolEdition = null,
        string? independentNoOpPath = null,
        string? resavedNoOpPath = null,
        string? transformationProfileId = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(referenceTool);
        ArgumentException.ThrowIfNullOrWhiteSpace(toolVersion);
        ArgumentException.ThrowIfNullOrWhiteSpace(profileId);
        var baseline = RomImage.Load(baselinePath);
        var noOp = RomImage.Load(noOpPath);
        if (baseline.Size != noOp.Size)
        {
            throw new RomSizeException("Oracle baseline and no-op ROM sizes differ.");
        }

        var normalization = DiffEngine.Compare(baseline, noOp).Ranges;
        var manifest = new OracleManifest(
            "2.0",
            referenceTool,
            toolVersion,
            Array.AsReadOnly(plugins?.ToArray() ?? Array.Empty<string>()),
            pluginsDisabled,
            profileId,
            Path.GetFullPath(baselinePath),
            baseline.Hash,
            Path.GetFullPath(noOpPath),
            noOp.Hash,
            DateTimeOffset.UtcNow,
            normalization,
            Array.Empty<OracleCase>(),
            userNotes)
        {
            ToolEdition = toolEdition,
            IndependentNoOp = FileEvidence(independentNoOpPath),
            ResavedNoOp = FileEvidence(resavedNoOpPath),
            TransformationProfileId = transformationProfileId,
        };
        Validate(manifest);
        return manifest;
    }

    public static OracleManifest AddCase(
        OracleManifest manifest,
        string parameterId,
        double engineeringValue,
        string romPath,
        string? userNotes = null,
        double? displayedValue = null,
        OracleObservationRole role = OracleObservationRole.Training,
        string? observationId = null)
    {
        ArgumentNullException.ThrowIfNull(manifest);
        ArgumentException.ThrowIfNullOrWhiteSpace(parameterId);
        Validate(manifest);
        if (!double.IsFinite(engineeringValue) || (displayedValue is { } displayed && !double.IsFinite(displayed)))
        {
            throw new ArgumentOutOfRangeException(nameof(engineeringValue), "Oracle values must be finite.");
        }

        var baseline = LoadAndVerify(manifest.BaselinePath, manifest.BaselineHash, "baseline");
        var rom = RomImage.Load(romPath);
        if (rom.Size != baseline.Size)
        {
            throw new RomSizeException("Oracle case size differs from its baseline.");
        }

        var oracleCase = new OracleCase(parameterId, engineeringValue, Path.GetFullPath(romPath), rom.Hash,
            DateTimeOffset.UtcNow, DiffEngine.Compare(baseline, rom).Ranges, userNotes, displayedValue)
        {
            Role = role,
            ObservationId = observationId ?? Guid.NewGuid().ToString("N"),
        };
        var cases = manifest.Cases.Append(oracleCase).ToArray();
        var updated = manifest with { Cases = cases };
        Validate(updated);
        return updated;
    }

    public static void Save(OracleManifest manifest, string outputPath, bool overwrite = false)
    {
        ArgumentNullException.ThrowIfNull(manifest);
        Validate(manifest);
        AtomicDocument.WriteAllText(outputPath, manifest.ToJson(), overwrite);
    }

    internal static RomImage LoadAndVerify(string path, RomHash expected, string role)
    {
        var image = RomImage.Load(path);
        if (image.Hash != expected)
        {
            throw new InvalidDataException($"Oracle {role} hash no longer matches its manifest.");
        }

        return image;
    }

    private static OracleFileEvidence? FileEvidence(string? path) => path is null ? null :
        new OracleFileEvidence(Path.GetFullPath(path), RomImage.Load(path).Hash);

    internal static void ValidateHash(RomHash hash, string role)
    {
        if (string.IsNullOrWhiteSpace(hash.Sha256) || hash.Sha256.Length != 64 || !hash.Sha256.All(Uri.IsHexDigit) ||
            string.IsNullOrWhiteSpace(hash.Crc32) || hash.Crc32.Length != 8 || !hash.Crc32.All(Uri.IsHexDigit))
        {
            throw new InvalidDataException($"Oracle {role} hash is malformed.");
        }
    }

    internal static void ValidateRanges(IReadOnlyList<DiffRange> ranges, string role, bool requireBytes = true)
    {
        foreach (var range in ranges)
        {
            if (range is null || range.Offset < 0 || range.Length <= 0 || range.Offset > 32768 - (long)range.Length ||
                range.OldHex is null || range.NewHex is null)
            {
                throw new InvalidDataException($"Oracle {role} contains an invalid diff range.");
            }

            try
            {
                if (!requireBytes && range.OldHex.Length == 0 && range.NewHex.Length == 0) continue;
                if (HexUtilities.Parse(range.OldHex).Length != range.Length || HexUtilities.Parse(range.NewHex).Length != range.Length)
                {
                    throw new InvalidDataException($"Oracle {role} diff-range bytes exceed its declared length.");
                }
            }
            catch (Exception exception) when (exception is ArgumentException or FormatException)
            {
                throw new InvalidDataException($"Oracle {role} contains malformed diff-range bytes.", exception);
            }
        }
    }
}
