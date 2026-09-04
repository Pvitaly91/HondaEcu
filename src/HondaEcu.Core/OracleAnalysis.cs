using System.Buffers.Binary;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record OracleCase(
    string ParameterId,
    double EngineeringValue,
    string RomPath,
    RomHash RomHash,
    DateTimeOffset CreatedAt,
    IReadOnlyList<DiffRange> DiffRanges,
    string? UserNotes = null,
    double? DisplayedValue = null);

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
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));

    public static OracleManifest Parse(string json)
    {
        var manifest = JsonSerializer.Deserialize<OracleManifest>(json, JsonDefaults.Options) ??
            throw new JsonException("Oracle manifest is empty.");
        OracleManifestService.Validate(manifest);
        return manifest;
    }

    public static OracleManifest Load(string path) => Parse(File.ReadAllText(path));
}

public static class OracleManifestService
{
    public static void Validate(OracleManifest manifest)
    {
        ArgumentNullException.ThrowIfNull(manifest);
        if (!string.Equals(manifest.FormatVersion, "1.0", StringComparison.Ordinal) ||
            string.IsNullOrWhiteSpace(manifest.ReferenceTool) || string.IsNullOrWhiteSpace(manifest.ToolVersion) ||
            string.IsNullOrWhiteSpace(manifest.ProfileId) || string.IsNullOrWhiteSpace(manifest.BaselinePath) ||
            string.IsNullOrWhiteSpace(manifest.NoOpPath) || manifest.BaselineHash is null || manifest.NoOpHash is null ||
            manifest.Plugins is null || manifest.NoOpNormalizationRanges is null || manifest.Cases is null ||
            manifest.CreatedAt == default)
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
        foreach (var oracleCase in manifest.Cases)
        {
            if (oracleCase is null || string.IsNullOrWhiteSpace(oracleCase.ParameterId) ||
                string.IsNullOrWhiteSpace(oracleCase.RomPath) || oracleCase.RomHash is null ||
                oracleCase.DiffRanges is null || !double.IsFinite(oracleCase.EngineeringValue) ||
                (oracleCase.DisplayedValue is { } displayed && !double.IsFinite(displayed)) ||
                oracleCase.CreatedAt == default)
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
        string? userNotes = null)
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
            "1.0",
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
            userNotes);
        Validate(manifest);
        return manifest;
    }

    public static OracleManifest AddCase(
        OracleManifest manifest,
        string parameterId,
        double engineeringValue,
        string romPath,
        string? userNotes = null,
        double? displayedValue = null)
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
            DateTimeOffset.UtcNow, DiffEngine.Compare(baseline, rom).Ranges, userNotes, displayedValue);
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

    private static void ValidateHash(RomHash hash, string role)
    {
        if (string.IsNullOrWhiteSpace(hash.Sha256) || hash.Sha256.Length != 64 || !hash.Sha256.All(Uri.IsHexDigit) ||
            string.IsNullOrWhiteSpace(hash.Crc32) || hash.Crc32.Length != 8 || !hash.Crc32.All(Uri.IsHexDigit))
        {
            throw new InvalidDataException($"Oracle {role} hash is malformed.");
        }
    }

    private static void ValidateRanges(IReadOnlyList<DiffRange> ranges, string role)
    {
        foreach (var range in ranges)
        {
            if (range is null || range.Offset < 0 || range.Length <= 0 || range.OldHex is null || range.NewHex is null)
            {
                throw new InvalidDataException($"Oracle {role} contains an invalid diff range.");
            }

            try
            {
                if (HexUtilities.Parse(range.OldHex).Length > range.Length || HexUtilities.Parse(range.NewHex).Length > range.Length)
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

public sealed record OracleCandidate(
    string ParameterId,
    int Offset,
    int Width,
    ParameterEncodingType EncodingType,
    Endianness Endianness,
    double Scale,
    double OffsetConstant,
    double Numerator,
    double DenominatorOffset,
    RoundingPolicy RoundingPolicy,
    IReadOnlyList<RoundingPolicy> CompatibleRoundingPolicies,
    double MeanAbsoluteError,
    double MaximumAbsoluteError,
    double Confidence,
    IReadOnlyList<long> RawValues,
    IReadOnlyList<double> EngineeringValues,
    ValidationLevel ValidationLevel = ValidationLevel.OracleObserved);

public sealed record OracleParameterAnalysis(
    string ParameterId,
    int CaseCount,
    IReadOnlyList<OracleCandidate> Candidates,
    IReadOnlyList<string> Warnings);

public sealed record OracleAnalysis(
    string FormatVersion,
    string ReferenceTool,
    string ToolVersion,
    string ProfileId,
    RomHash BaselineHash,
    RomHash NoOpHash,
    DateTimeOffset AnalyzedAt,
    IReadOnlyList<DiffRange> NoOpNormalizationRanges,
    IReadOnlyList<ByteRange> ExcludedChecksumRegions,
    IReadOnlyList<DiffRange> AdditionalChangedRanges,
    IReadOnlyList<OracleParameterAnalysis> Parameters,
    ValidationLevel ValidationLevel = ValidationLevel.OracleObserved)
{
    /// <summary>
    /// Case-specific bytes inside declared checksum regions, observed relative to the no-op save.
    /// These are reported separately from both inferred parameters and unexplained residuals.
    /// </summary>
    public IReadOnlyList<DiffRange> ObservedChecksumChangedRanges { get; init; } = Array.Empty<DiffRange>();

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));

    public static OracleAnalysis Parse(string json)
    {
        var analysis = JsonSerializer.Deserialize<OracleAnalysis>(json, JsonDefaults.Options) ??
            throw new JsonException("Oracle analysis is empty.");
        OracleAnalyzer.ValidateAnalysis(analysis);
        return analysis;
    }

    public static OracleAnalysis Load(string path) => Parse(File.ReadAllText(path));

    public void Save(string path, bool overwrite = false)
    {
        OracleAnalyzer.ValidateAnalysis(this);
        AtomicDocument.WriteAllText(path, ToJson(), overwrite);
    }
}

public static class OracleAnalyzer
{
    public static OracleAnalysis Analyze(OracleManifest manifest, RomProfile profile)
    {
        ArgumentNullException.ThrowIfNull(manifest);
        ArgumentNullException.ThrowIfNull(profile);
        OracleManifestService.Validate(manifest);
        if (!string.Equals(manifest.ProfileId, profile.Id, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"Manifest profile '{manifest.ProfileId}' does not match '{profile.Id}'.");
        }

        if (!manifest.PluginsDisabled)
        {
            throw new InvalidOperationException(
                "Oracle candidate analysis requires pluginsDisabled=true; unknown plugin regions must never be inferred as calibration parameters.");
        }

        var baseline = OracleManifestService.LoadAndVerify(manifest.BaselinePath, manifest.BaselineHash, "baseline");
        var noOp = OracleManifestService.LoadAndVerify(manifest.NoOpPath, manifest.NoOpHash, "no-op");
        baseline.ValidateExactSize(profile.ExpectedSize, profile.Id);
        noOp.ValidateExactSize(profile.ExpectedSize, profile.Id);
        var actualNormalization = DiffEngine.Compare(baseline, noOp).Ranges;
        if (!actualNormalization.SequenceEqual(manifest.NoOpNormalizationRanges))
        {
            throw new InvalidDataException("Oracle no-op normalization ranges do not match the current baseline/no-op files.");
        }

        var checksumRegions = GetChecksumRegions(profile.Checksum);
        var excludedOffsets = checksumRegions.SelectMany(range => Enumerable.Range(range.Offset, range.Length)).ToHashSet();

        var analyses = new List<OracleParameterAnalysis>();
        var allObservedOffsets = new HashSet<int>();
        var candidateOffsets = new HashSet<int>();
        foreach (var group in manifest.Cases.GroupBy(item => item.ParameterId, StringComparer.OrdinalIgnoreCase))
        {
            var warnings = new List<string>();
            var cases = group.ToArray();
            var images = cases.Select((item, index) =>
                OracleManifestService.LoadAndVerify(item.RomPath, item.RomHash, $"case {index + 1}")).ToArray();
            if (images.Any(image => image.Size != baseline.Size))
            {
                throw new RomSizeException($"One or more oracle cases for '{group.Key}' have a different size.");
            }

            for (var index = 0; index < cases.Length; index++)
            {
                var actualCaseRanges = DiffEngine.Compare(baseline, images[index]).Ranges;
                if (!actualCaseRanges.SequenceEqual(cases[index].DiffRanges))
                {
                    throw new InvalidDataException($"Oracle case '{cases[index].RomPath}' diff ranges do not match its current file.");
                }

                // Compare cases to the editor-produced no-op image for residual accounting. A
                // baseline-to-case comparison cannot distinguish a fixed normalization from a
                // case-specific value written at that same address.
                var caseVersusNoOp = DiffEngine.Compare(noOp, images[index]).Ranges;
                allObservedOffsets.UnionWith(ExpandOffsets(caseVersusNoOp));
            }

            if (cases.Select(item => item.DisplayedValue ?? item.EngineeringValue).Distinct().Count() < 3)
            {
                warnings.Add("At least three distinct engineering values are required for candidate analysis.");
                analyses.Add(new OracleParameterAnalysis(group.Key, cases.Length, Array.Empty<OracleCandidate>(), warnings));
                continue;
            }

            var changedOffsets = images.SelectMany(image => ExpandOffsets(DiffEngine.Compare(noOp, image).Ranges)).ToHashSet();
            changedOffsets.ExceptWith(excludedOffsets);
            var candidates = FindCandidates(group.Key, cases, images, noOp, changedOffsets, excludedOffsets);
            if (candidates.Count == 0)
            {
                warnings.Add("No supported raw, linear, or inverse encoding candidate fit all cases.");
            }

            foreach (var candidate in candidates)
            {
                candidateOffsets.UnionWith(Enumerable.Range(candidate.Offset, candidate.Width));
            }

            analyses.Add(new OracleParameterAnalysis(group.Key, cases.Length, candidates, warnings));
        }

        var residualOffsets = allObservedOffsets
            .Except(candidateOffsets)
            .Except(excludedOffsets);
        var additional = ToRanges(residualOffsets);
        var observedChecksum = ToRanges(allObservedOffsets.Intersect(excludedOffsets));
        return new OracleAnalysis("1.0", manifest.ReferenceTool, manifest.ToolVersion, profile.Id,
            baseline.Hash, noOp.Hash, DateTimeOffset.UtcNow, actualNormalization,
            checksumRegions, additional, analyses)
        {
            ObservedChecksumChangedRanges = observedChecksum,
        };
    }

    internal static void ValidateAnalysis(OracleAnalysis analysis)
    {
        ArgumentNullException.ThrowIfNull(analysis);
        if (!string.Equals(analysis.FormatVersion, "1.0", StringComparison.Ordinal) ||
            string.IsNullOrWhiteSpace(analysis.ReferenceTool) || string.IsNullOrWhiteSpace(analysis.ToolVersion) ||
            string.IsNullOrWhiteSpace(analysis.ProfileId) || analysis.BaselineHash is null || analysis.NoOpHash is null ||
            analysis.NoOpNormalizationRanges is null || analysis.ExcludedChecksumRegions is null ||
            analysis.AdditionalChangedRanges is null || analysis.ObservedChecksumChangedRanges is null ||
            analysis.Parameters is null)
        {
            throw new InvalidDataException("Oracle analysis is missing required tool provenance, hashes, or collections.");
        }

        if (analysis.Parameters.Any(parameter => parameter is null || string.IsNullOrWhiteSpace(parameter.ParameterId) ||
            parameter.Candidates is null || parameter.Warnings is null))
        {
            throw new InvalidDataException("Oracle analysis contains malformed parameter results.");
        }
    }

    public static string ExportCandidate(OracleAnalysis analysis, string parameterId, int offset, ParameterEncodingType type)
    {
        ArgumentNullException.ThrowIfNull(analysis);
        var candidate = analysis.Parameters
            .FirstOrDefault(parameter => string.Equals(parameter.ParameterId, parameterId, StringComparison.OrdinalIgnoreCase))?
            .Candidates.FirstOrDefault(item => item.Offset == offset && item.EncodingType == type) ??
            throw new KeyNotFoundException("Requested oracle candidate was not found.");
        if (candidate.CompatibleRoundingPolicies.Count != 1)
        {
            throw new InvalidOperationException(
                "Candidate rounding is ambiguous. Add boundary oracle cases until exactly one rounding policy remains before export.");
        }

        var establishedRounding = candidate.CompatibleRoundingPolicies[0];
        var roundingEvidence = $"Rounding policy {establishedRounding} was uniquely compatible with the supplied cases.";
        var fragment = new
        {
            id = candidate.ParameterId,
            displayName = $"{candidate.ParameterId} (oracle candidate)",
            description = "Generated from editor observations; requires independent review and must not be promoted automatically.",
            offset = candidate.Offset,
            width = candidate.Width,
            endianness = candidate.Endianness,
            encoding = new
            {
                type = candidate.EncodingType,
                scale = candidate.Scale,
                offset = candidate.OffsetConstant,
                numerator = candidate.Numerator,
                denominatorOffset = candidate.DenominatorOffset,
            },
            units = "unknown",
            rawRange = new { minimum = candidate.RawValues.Min(), maximum = candidate.RawValues.Max() },
            engineeringRange = new { minimum = candidate.EngineeringValues.Min(), maximum = candidate.EngineeringValues.Max() },
            roundingPolicy = establishedRounding,
            writable = false,
            validationLevel = ValidationLevel.OracleObserved,
            revisionScope = $"{analysis.ProfileId}; oracle candidate only",
            sources = new[] { "oracle-manifest-review-required" },
            notes = $"{roundingEvidence} Review the manifest provenance, add a matching EvidenceReference, and validate boundary cases across editors before profile inclusion.",
            status = ParameterStatus.Candidate,
        };
        return JsonSerializer.Serialize(fragment, JsonDefaults.Options);
    }

    private static IReadOnlyList<OracleCandidate> FindCandidates(
        string parameterId,
        IReadOnlyList<OracleCase> cases,
        IReadOnlyList<RomImage> images,
        RomImage noOp,
        IReadOnlySet<int> changedOffsets,
        IReadOnlySet<int> excludedOffsets)
    {
        var displayedEngineering = cases.Select(item => item.DisplayedValue ?? item.EngineeringValue).ToArray();
        var requestedEngineering = cases.Select(item => item.EngineeringValue).ToArray();
        var result = new List<OracleCandidate>();
        var tested = new HashSet<(int Offset, int Width, bool Signed, Endianness Endianness)>();
        foreach (var changedOffset in changedOffsets.Order())
        {
            AddForWidth(changedOffset, 1, signed: false, Endianness.NotApplicable);
            AddForWidth(changedOffset, 1, signed: true, Endianness.NotApplicable);
            if (changedOffset < noOp.Size - 1)
            {
                AddForWidth(changedOffset, 2, signed: false, Endianness.Little);
                AddForWidth(changedOffset, 2, signed: false, Endianness.Big);
            }

            if (changedOffset > 0)
            {
                AddForWidth(changedOffset - 1, 2, signed: false, Endianness.Little);
                AddForWidth(changedOffset - 1, 2, signed: false, Endianness.Big);
            }
        }

        return result
            .OrderByDescending(candidate => candidate.Confidence)
            .ThenBy(candidate => candidate.Offset)
            .ThenBy(candidate => candidate.EncodingType)
            .ToArray();

        void AddForWidth(int offset, int width, bool signed, Endianness endianness)
        {
            if (offset < 0 || offset > noOp.Size - width || Enumerable.Range(offset, width).Any(excludedOffsets.Contains) ||
                !tested.Add((offset, width, signed, endianness)))
            {
                return;
            }

            var raws = images.Select(image => ReadRaw(image.Span, offset, width, signed, endianness)).ToArray();
            if (raws.Distinct().Count() < 3 || !IsMonotonic(raws, displayedEngineering))
            {
                return;
            }

            var rawType = width == 1
                ? signed ? ParameterEncodingType.RawS8 : ParameterEncodingType.RawU8
                : endianness == Endianness.Little ? ParameterEncodingType.RawU16LittleEndian : ParameterEncodingType.RawU16BigEndian;
            AddRawCandidate(rawType, offset, width, endianness, raws, displayedEngineering, requestedEngineering, result, parameterId);
            if (!signed)
            {
                AddLinearCandidate(width == 1 ? ParameterEncodingType.LinearU8 : ParameterEncodingType.LinearU16,
                    offset, width, endianness, raws, displayedEngineering, requestedEngineering, result, parameterId);
                AddInverseCandidate(width == 1 ? ParameterEncodingType.InverseU8 : ParameterEncodingType.InverseU16,
                    offset, width, endianness, raws, displayedEngineering, requestedEngineering, result, parameterId);
            }
        }
    }

    private static void AddRawCandidate(
        ParameterEncodingType type,
        int offset,
        int width,
        Endianness endianness,
        long[] raw,
        double[] displayedEngineering,
        double[] requestedEngineering,
        ICollection<OracleCandidate> output,
        string parameterId)
    {
        var errors = displayedEngineering.Zip(raw, (value, encoded) => Math.Abs(value - encoded)).ToArray();
        if (errors.All(error => error <= 1e-9))
        {
            var compatible = CompatibleRounding(raw, requestedEngineering);
            if (compatible.Count == 0)
            {
                return;
            }

            output.Add(CreateCandidate(parameterId, offset, width, type, endianness, 1, 0, 1, 0,
                raw, displayedEngineering, errors, compatible));
        }
    }

    private static void AddLinearCandidate(
        ParameterEncodingType type,
        int offset,
        int width,
        Endianness endianness,
        long[] raw,
        double[] displayedEngineering,
        double[] requestedEngineering,
        ICollection<OracleCandidate> output,
        string parameterId)
    {
        if (!TryFitLine(raw.Select(value => (double)value).ToArray(), displayedEngineering, out var scale, out var addend) ||
            Math.Abs(scale) < 1e-12)
        {
            return;
        }

        var predicted = raw.Select(value => (value * scale) + addend).ToArray();
        var errors = predicted.Zip(displayedEngineering, (left, right) => Math.Abs(left - right)).ToArray();
        if (!Accept(errors, displayedEngineering))
        {
            return;
        }

        var compatible = CompatibleRounding(raw, requestedEngineering.Select(value => (value - addend) / scale).ToArray());
        if (compatible.Count == 0)
        {
            return;
        }

        output.Add(CreateCandidate(parameterId, offset, width, type, endianness, scale, addend, 1, 0,
            raw, displayedEngineering, errors, compatible));
    }

    private static void AddInverseCandidate(
        ParameterEncodingType type,
        int offset,
        int width,
        Endianness endianness,
        long[] raw,
        double[] displayedEngineering,
        double[] requestedEngineering,
        ICollection<OracleCandidate> output,
        string parameterId)
    {
        if (!TryFitInverse(raw, displayedEngineering, out var numerator, out var denominatorOffset, out var engineeringOffset) ||
            Math.Abs(numerator) < 1e-12 || raw.Any(value => Math.Abs(value + denominatorOffset) < 1e-12))
        {
            return;
        }

        var predicted = raw.Select(value => numerator / (value + denominatorOffset) + engineeringOffset).ToArray();
        var errors = predicted.Zip(displayedEngineering, (left, right) => Math.Abs(left - right)).ToArray();
        if (!Accept(errors, displayedEngineering))
        {
            return;
        }

        var rawPredictions = requestedEngineering.Select(value => numerator / (value - engineeringOffset) - denominatorOffset).ToArray();
        var compatible = CompatibleRounding(raw, rawPredictions);
        if (compatible.Count == 0)
        {
            return;
        }

        output.Add(CreateCandidate(parameterId, offset, width, type, endianness, 1, engineeringOffset,
            numerator, denominatorOffset, raw, displayedEngineering, errors, compatible));
    }

    private static OracleCandidate CreateCandidate(
        string parameterId,
        int offset,
        int width,
        ParameterEncodingType type,
        Endianness endianness,
        double scale,
        double offsetConstant,
        double numerator,
        double denominatorOffset,
        long[] raw,
        double[] engineering,
        double[] errors,
        IReadOnlyList<RoundingPolicy> compatible)
    {
        var mean = errors.Average();
        var maximum = errors.Max();
        var range = Math.Max(1, engineering.Max() - engineering.Min());
        var fit = Math.Clamp(1 - (maximum / range), 0, 1);
        var confidence = Math.Round(fit * Math.Min(1, raw.Length / 3.0), 6);
        return new OracleCandidate(parameterId, offset, width, type, endianness, scale, offsetConstant,
            numerator, denominatorOffset, compatible.FirstOrDefault(RoundingPolicy.Nearest), compatible,
            mean, maximum, confidence, raw, engineering);
    }

    private static bool Accept(IReadOnlyList<double> errors, IReadOnlyList<double> engineering)
    {
        var range = engineering.Max() - engineering.Min();
        var tolerance = Math.Max(0.51, range * 0.005);
        return errors.All(double.IsFinite) && errors.Max() <= tolerance;
    }

    private static IReadOnlyList<RoundingPolicy> CompatibleRounding(IReadOnlyList<long> actual, IReadOnlyList<double> predicted)
    {
        var policies = new List<RoundingPolicy>();
        if (actual.Zip(predicted, (raw, value) => Math.Abs(raw - value) <= 1e-7).All(value => value))
        {
            policies.Add(RoundingPolicy.Exact);
        }

        AddIf(RoundingPolicy.Nearest, value => Math.Round(value, MidpointRounding.AwayFromZero));
        AddIf(RoundingPolicy.ToEven, value => Math.Round(value, MidpointRounding.ToEven));
        AddIf(RoundingPolicy.Floor, Math.Floor);
        AddIf(RoundingPolicy.Ceiling, Math.Ceiling);
        AddIf(RoundingPolicy.Truncate, Math.Truncate);
        return policies;

        void AddIf(RoundingPolicy policy, Func<double, double> round)
        {
            if (actual.Zip(predicted, (raw, value) => raw == (long)round(value)).All(value => value))
            {
                policies.Add(policy);
            }
        }
    }

    private static bool TryFitLine(double[] x, double[] y, out double slope, out double intercept)
    {
        var meanX = x.Average();
        var meanY = y.Average();
        var denominator = x.Sum(value => (value - meanX) * (value - meanX));
        if (Math.Abs(denominator) < 1e-12)
        {
            slope = 0;
            intercept = 0;
            return false;
        }

        slope = x.Zip(y, (left, right) => (left - meanX) * (right - meanY)).Sum() / denominator;
        intercept = meanY - (slope * meanX);
        return double.IsFinite(slope) && double.IsFinite(intercept);
    }

    private static bool TryFitInverse(long[] raw, double[] engineering, out double numerator, out double denominatorOffset, out double offset)
    {
        // y = N/(x + D) + O  =>  x*O + C - y*D = x*y, where C = O*D + N.
        var matrix = new double[3, 3];
        var vector = new double[3];
        for (var index = 0; index < raw.Length; index++)
        {
            var features = new[] { (double)raw[index], 1d, -engineering[index] };
            var target = raw[index] * engineering[index];
            for (var row = 0; row < 3; row++)
            {
                vector[row] += features[row] * target;
                for (var column = 0; column < 3; column++)
                {
                    matrix[row, column] += features[row] * features[column];
                }
            }
        }

        if (!TrySolve3(matrix, vector, out var solution))
        {
            numerator = 0;
            denominatorOffset = 0;
            offset = 0;
            return false;
        }

        offset = solution[0];
        var c = solution[1];
        denominatorOffset = solution[2];
        numerator = c - (offset * denominatorOffset);
        return double.IsFinite(numerator) && double.IsFinite(denominatorOffset) && double.IsFinite(offset);
    }

    private static bool TrySolve3(double[,] input, double[] right, out double[] solution)
    {
        var augmented = new double[3, 4];
        for (var row = 0; row < 3; row++)
        {
            for (var column = 0; column < 3; column++)
            {
                augmented[row, column] = input[row, column];
            }

            augmented[row, 3] = right[row];
        }

        for (var pivot = 0; pivot < 3; pivot++)
        {
            var best = pivot;
            for (var row = pivot + 1; row < 3; row++)
            {
                if (Math.Abs(augmented[row, pivot]) > Math.Abs(augmented[best, pivot]))
                {
                    best = row;
                }
            }

            if (Math.Abs(augmented[best, pivot]) < 1e-12)
            {
                solution = Array.Empty<double>();
                return false;
            }

            for (var column = pivot; column < 4; column++)
            {
                (augmented[pivot, column], augmented[best, column]) = (augmented[best, column], augmented[pivot, column]);
            }

            var divisor = augmented[pivot, pivot];
            for (var column = pivot; column < 4; column++)
            {
                augmented[pivot, column] /= divisor;
            }

            for (var row = 0; row < 3; row++)
            {
                if (row == pivot)
                {
                    continue;
                }

                var factor = augmented[row, pivot];
                for (var column = pivot; column < 4; column++)
                {
                    augmented[row, column] -= factor * augmented[pivot, column];
                }
            }
        }

        solution = new[] { augmented[0, 3], augmented[1, 3], augmented[2, 3] };
        return true;
    }

    private static long ReadRaw(ReadOnlySpan<byte> bytes, int offset, int width, bool signed, Endianness endianness)
    {
        if (width == 1)
        {
            return signed ? unchecked((sbyte)bytes[offset]) : bytes[offset];
        }

        return endianness == Endianness.Little
            ? BinaryPrimitives.ReadUInt16LittleEndian(bytes.Slice(offset, 2))
            : BinaryPrimitives.ReadUInt16BigEndian(bytes.Slice(offset, 2));
    }

    private static bool IsMonotonic(IReadOnlyList<long> raw, IReadOnlyList<double> engineering)
    {
        var pairs = engineering.Select((value, index) => (Engineering: value, Raw: raw[index])).OrderBy(pair => pair.Engineering).ToArray();
        var increasing = true;
        var decreasing = true;
        for (var index = 1; index < pairs.Length; index++)
        {
            increasing &= pairs[index].Raw > pairs[index - 1].Raw;
            decreasing &= pairs[index].Raw < pairs[index - 1].Raw;
        }

        return increasing || decreasing;
    }

    private static IReadOnlyList<ByteRange> GetChecksumRegions(ChecksumDefinition? checksum)
    {
        if (checksum is null)
        {
            return Array.Empty<ByteRange>();
        }

        var ranges = new List<ByteRange>();
        if (checksum.Length > 0)
        {
            ranges.Add(new ByteRange(checksum.Offset, checksum.Length));
        }

        ranges.AddRange(checksum.Regions);
        return ranges;
    }

    private static IEnumerable<int> ExpandOffsets(IEnumerable<DiffRange> ranges)
    {
        foreach (var range in ranges)
        {
            for (var offset = range.Offset; offset <= range.EndOffset; offset++)
            {
                yield return offset;
            }
        }
    }

    private static IReadOnlyList<DiffRange> ToRanges(IEnumerable<int> offsets)
    {
        var sorted = offsets.Distinct().Order().ToArray();
        if (sorted.Length == 0)
        {
            return Array.Empty<DiffRange>();
        }

        var ranges = new List<DiffRange>();
        var start = sorted[0];
        var previous = start;
        for (var index = 1; index < sorted.Length; index++)
        {
            if (sorted[index] == previous + 1)
            {
                previous = sorted[index];
                continue;
            }

            ranges.Add(new DiffRange(start, previous - start + 1, string.Empty, string.Empty));
            start = previous = sorted[index];
        }

        ranges.Add(new DiffRange(start, previous - start + 1, string.Empty, string.Empty));
        return ranges;
    }
}

public sealed record CrossEditorParameterComparison(
    string ParameterId,
    bool SameOffset,
    bool SameWidth,
    bool SameEndianness,
    bool SameConversion,
    bool SameRounding,
    bool HasCommonCandidate,
    ValidationLevel ValidationLevel,
    IReadOnlyList<string> ConflictReasons,
    IReadOnlyList<OracleCandidate> CommonCandidates);

public sealed record CrossEditorReport(
    string FormatVersion,
    bool SameBaseline,
    string ProfileId,
    string CromeTool,
    string CromeToolVersion,
    string HtsTool,
    string HtsToolVersion,
    DateTimeOffset ComparedAt,
    IReadOnlyList<CrossEditorParameterComparison> Parameters,
    IReadOnlyList<DiffRange> CromeAdditionalRanges,
    IReadOnlyList<DiffRange> HtsAdditionalRanges)
{
    public IReadOnlyList<DiffRange> CromeObservedChecksumRanges { get; init; } = Array.Empty<DiffRange>();

    public IReadOnlyList<DiffRange> HtsObservedChecksumRanges { get; init; } = Array.Empty<DiffRange>();

    public bool IsCrossEditorConfirmed =>
        SameBaseline && Parameters.Any(parameter => parameter.ValidationLevel == ValidationLevel.CrossEditorConfirmed);

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));

    public void Save(string path, bool overwrite = false) => AtomicDocument.WriteAllText(path, ToJson(), overwrite);
}

internal static class AtomicDocument
{
    public static void WriteAllText(string path, string contents, bool overwrite)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        ArgumentNullException.ThrowIfNull(contents);
        var destination = Path.GetFullPath(path);
        var directory = Path.GetDirectoryName(destination) ?? Directory.GetCurrentDirectory();
        Directory.CreateDirectory(directory);
        if (!overwrite && File.Exists(destination))
        {
            throw new IOException($"Document already exists: {destination}");
        }

        var temporary = Path.Combine(directory, $".{Path.GetFileName(destination)}.{Guid.NewGuid():N}.tmp");
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
            using (var writer = new StreamWriter(stream, new System.Text.UTF8Encoding(encoderShouldEmitUTF8Identifier: false)))
            {
                writer.Write(contents);
                writer.Flush();
                stream.Flush(flushToDisk: true);
            }

            File.Move(temporary, destination, overwrite);
        }
        finally
        {
            if (File.Exists(temporary))
            {
                File.Delete(temporary);
            }
        }
    }
}

public static class CrossEditorComparer
{
    public static CrossEditorReport Compare(OracleAnalysis crome, OracleAnalysis hts, double conversionTolerance = 1e-6)
    {
        ArgumentNullException.ThrowIfNull(crome);
        ArgumentNullException.ThrowIfNull(hts);
        OracleAnalyzer.ValidateAnalysis(crome);
        OracleAnalyzer.ValidateAnalysis(hts);
        if (!string.Equals(crome.ProfileId, hts.ProfileId, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("Oracle analyses use different ROM profiles.");
        }

        var sameBaseline = crome.BaselineHash == hts.BaselineHash;
        var parameterIds = crome.Parameters.Select(item => item.ParameterId)
            .Union(hts.Parameters.Select(item => item.ParameterId), StringComparer.OrdinalIgnoreCase);
        var comparisons = new List<CrossEditorParameterComparison>();
        foreach (var parameterId in parameterIds)
        {
            var left = crome.Parameters.FirstOrDefault(item => string.Equals(item.ParameterId, parameterId, StringComparison.OrdinalIgnoreCase));
            var right = hts.Parameters.FirstOrDefault(item => string.Equals(item.ParameterId, parameterId, StringComparison.OrdinalIgnoreCase));
            var leftCandidates = left?.Candidates ?? Array.Empty<OracleCandidate>();
            var rightCandidates = right?.Candidates ?? Array.Empty<OracleCandidate>();
            var common = (from first in leftCandidates
                          from second in rightCandidates
                          where Equivalent(first, second, conversionTolerance)
                          select first).Distinct().ToArray();
            var reasons = new List<string>();
            if (!sameBaseline)
            {
                reasons.Add("Crome and HTS did not use the same baseline ROM hash.");
            }

            if (crome.AdditionalChangedRanges.Count > 0)
            {
                reasons.Add("Crome has unexplained additional changed ranges.");
            }

            if (hts.AdditionalChangedRanges.Count > 0)
            {
                reasons.Add("Honda Tuning Suite has unexplained additional changed ranges.");
            }

            if (left is null || right is null)
            {
                reasons.Add("Parameter is missing from one editor analysis.");
            }
            else if (common.Length == 0)
            {
                reasons.Add("No candidate has the same offset, width, endianness, conversion, and compatible rounding.");
                if (AnyMatch(leftCandidates, rightCandidates, (a, b) =>
                    a.Offset == b.Offset && a.Width == b.Width && a.Endianness == b.Endianness &&
                    a.EncodingType == b.EncodingType && SameConversion(a, b, conversionTolerance) &&
                    (a.CompatibleRoundingPolicies.Count != 1 || b.CompatibleRoundingPolicies.Count != 1)))
                {
                    reasons.Add("Rounding evidence is ambiguous; both editors must establish the same single policy.");
                }
            }

            var sameOffset = AnyMatch(leftCandidates, rightCandidates, (a, b) => a.Offset == b.Offset);
            var sameWidth = AnyMatch(leftCandidates, rightCandidates, (a, b) => a.Offset == b.Offset && a.Width == b.Width);
            var sameEndian = AnyMatch(leftCandidates, rightCandidates,
                (a, b) => a.Offset == b.Offset && a.Width == b.Width && a.Endianness == b.Endianness);
            var sameConversion = AnyMatch(leftCandidates, rightCandidates,
                (a, b) => a.Offset == b.Offset && a.Width == b.Width && a.Endianness == b.Endianness &&
                    a.EncodingType == b.EncodingType && SameConversion(a, b, conversionTolerance));
            var sameRounding = common.Length > 0;
            var hasCommon = common.Length > 0 && sameRounding;
            var confirmed = sameBaseline && hasCommon &&
                crome.AdditionalChangedRanges.Count == 0 && hts.AdditionalChangedRanges.Count == 0;
            comparisons.Add(new CrossEditorParameterComparison(parameterId, sameOffset, sameWidth, sameEndian,
                sameConversion, sameRounding, hasCommon,
                confirmed ? ValidationLevel.CrossEditorConfirmed : ValidationLevel.OracleObserved, reasons, common));
        }

        return new CrossEditorReport("1.0", sameBaseline, crome.ProfileId,
            crome.ReferenceTool, crome.ToolVersion, hts.ReferenceTool, hts.ToolVersion,
            DateTimeOffset.UtcNow, comparisons,
            crome.AdditionalChangedRanges, hts.AdditionalChangedRanges)
        {
            CromeObservedChecksumRanges = crome.ObservedChecksumChangedRanges,
            HtsObservedChecksumRanges = hts.ObservedChecksumChangedRanges,
        };
    }

    private static bool Equivalent(OracleCandidate left, OracleCandidate right, double tolerance) =>
        left.Offset == right.Offset && left.Width == right.Width && left.Endianness == right.Endianness &&
        left.EncodingType == right.EncodingType && SameConversion(left, right, tolerance) &&
        HasSameEstablishedRounding(left, right);

    private static bool HasSameEstablishedRounding(OracleCandidate left, OracleCandidate right) =>
        left.CompatibleRoundingPolicies.Count == 1 && right.CompatibleRoundingPolicies.Count == 1 &&
        left.CompatibleRoundingPolicies[0] == right.CompatibleRoundingPolicies[0];

    private static bool SameConversion(OracleCandidate left, OracleCandidate right, double tolerance) =>
        Close(left.Scale, right.Scale, tolerance) && Close(left.OffsetConstant, right.OffsetConstant, tolerance) &&
        Close(left.Numerator, right.Numerator, tolerance) && Close(left.DenominatorOffset, right.DenominatorOffset, tolerance);

    private static bool Close(double left, double right, double tolerance) =>
        Math.Abs(left - right) <= tolerance * Math.Max(1, Math.Max(Math.Abs(left), Math.Abs(right)));

    private static bool AnyMatch(
        IReadOnlyList<OracleCandidate> left,
        IReadOnlyList<OracleCandidate> right,
        Func<OracleCandidate, OracleCandidate, bool> predicate) =>
        left.Any(first => right.Any(second => predicate(first, second)));
}
