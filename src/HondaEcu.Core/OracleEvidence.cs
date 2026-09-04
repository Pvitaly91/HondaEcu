using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public static class OracleProvenance
{
    public static string NormalizeTool(string tool)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(tool);
        var normalized = new string(tool.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());
        return normalized switch { "crome" => "crome", "hts" or "hondatuningsuite" => "hts", _ => normalized };
    }

    public static bool IsExpectedTool(string tool, string expected) =>
        !string.IsNullOrWhiteSpace(tool) && !string.IsNullOrWhiteSpace(expected) &&
        NormalizeTool(expected) is "crome" or "hts" && NormalizeTool(tool) == NormalizeTool(expected);

    public static IReadOnlyList<string> GetBlockers(OracleManifest manifest)
    {
        var blockers = new List<string>();
        if (NormalizeTool(manifest.ReferenceTool) is not ("crome" or "hts")) blockers.Add("Reference tool is not a supported Crome/HTS provenance label.");
        if (string.IsNullOrWhiteSpace(manifest.ToolEdition)) blockers.Add("Editor edition/variant has not been recorded.");
        if (!manifest.PluginsDisabled) blockers.Add("pluginsDisabled=true has not been recorded.");
        if (manifest.FormatVersion != "2.0") blockers.Add("Legacy manifest requires explicit M0.1 provenance and observation roles before confirmation.");
        if (manifest.Cases.Any(item => string.IsNullOrWhiteSpace(item.ObservationId))) blockers.Add("Some observations have no provenance id.");
        if (manifest.Cases.Any(item => item.DisplayedValue is null)) blockers.Add("Some observations lack displayed values after reopening.");
        return blockers;
    }
}

public sealed record OracleBoundFile(string Role, string Path, RomHash Hash);

public sealed record OracleEvidenceBinding(
    string ManifestDigest,
    string ProfileDigest,
    string AnalyzerVersion,
    string ManifestJson,
    string ProfileJson,
    string? ManifestPath,
    string? ProfilePath,
    IReadOnlyList<OracleBoundFile> Files)
{
    public string? SourceManifestDigest { get; init; }
    public string? SourceProfileDigest { get; init; }
    public string? ResultDigest { get; init; }
    public IReadOnlyDictionary<string, string> SelectedDefinitionIds { get; init; } = new Dictionary<string, string>();
}

public sealed record OracleNoOpEvidence(
    bool IndependentSavePresent,
    bool ResavePresent,
    bool? IsDeterministic,
    bool? IsStable,
    bool HasTransformation,
    bool TransformationApproved,
    IReadOnlyList<string> Blockers)
{
    public bool IsReadyForComparison => Blockers.Count == 0;
}

/// <summary>
/// Integrity links for local evidence. Hashes detect stale or edited reports; editor attribution
/// remains a user declaration, not a signature proving that an editor produced a file.
/// </summary>
public static class OracleEvidence
{
    public const string AnalyzerVersion = "hondaecu-oracle/2.0";

    public static OracleEvidenceBinding Bind(OracleManifest manifest, RomProfile profile)
    {
        foreach (var file in BoundFiles(manifest)) OracleManifestService.LoadAndVerify(file.Path, file.Hash, file.Role);
        var manifestJson = manifest.ToJson(false);
        var profileJson = JsonSerializer.Serialize(profile, JsonDefaults.Options);
        return new OracleEvidenceBinding(Digest(manifestJson), Digest(profileJson), AnalyzerVersion,
            manifestJson, profileJson, manifest.SourcePath, profile.SourcePath, BoundFiles(manifest))
        {
            SourceManifestDigest = FileDigest(manifest.SourcePath),
            SourceProfileDigest = FileDigest(profile.SourcePath),
        };
    }

    internal static OracleAnalysis Seal(OracleAnalysis analysis)
    {
        if (analysis.EvidenceBinding is null) throw new InvalidDataException("Cannot seal analysis without source evidence.");
        return analysis with
        {
            EvidenceBinding = analysis.EvidenceBinding with
            {
                ResultDigest = ResultDigest(analysis),
                SelectedDefinitionIds = analysis.Parameters.Where(item => item.SelectedCandidateId is not null)
                    .ToDictionary(item => item.ParameterId, item => item.SelectedCandidateId!, StringComparer.OrdinalIgnoreCase),
            },
        };
    }

    public static OracleNoOpEvidence InspectNoOp(OracleManifest manifest)
    {
        var blockers = new List<string>();
        var paths = new[] { manifest.BaselinePath, manifest.NoOpPath, manifest.IndependentNoOp?.RomPath, manifest.ResavedNoOp?.RomPath }
            .OfType<string>().ToArray();
        for (var first = 0; first < paths.Length; first++)
        {
            for (var second = first + 1; second < paths.Length; second++)
                if (SamePath(paths[first], paths[second])) blockers.Add("Baseline, primary no-op, independent no-op and resaved no-op require distinct output paths.");
        }
        bool? deterministic = null;
        bool? stable = null;
        if (manifest.IndependentNoOp is null) blockers.Add("Second independent no-op save of the baseline is missing.");
        else
        {
            deterministic = manifest.IndependentNoOp.RomHash == manifest.NoOpHash;
            if (SamePath(manifest.IndependentNoOp.RomPath, manifest.NoOpPath)) blockers.Add("Independent no-op must be a separate recorded output file.");
            if (deterministic != true) blockers.Add("Independent no-op results are nondeterministic (different hashes).");
        }
        if (manifest.ResavedNoOp is null) blockers.Add("Resave of the already saved no-op is missing.");
        else
        {
            stable = manifest.ResavedNoOp.RomHash == manifest.NoOpHash;
            if (SamePath(manifest.ResavedNoOp.RomPath, manifest.NoOpPath)) blockers.Add("No-op resave must be a separate recorded output file.");
            if (stable != true) blockers.Add("No-op transformation did not stabilize on resave.");
        }
        var transformed = manifest.BaselineHash != manifest.NoOpHash || manifest.NoOpNormalizationRanges.Count > 0;
        if (transformed) blockers.Add("Unknown no-op transformation: stability and plugins-disabled do not authorize code/layout changes. A documented, independently verified transformation profile is required; M0.1 does not approve transformation profiles by id alone.");
        return new OracleNoOpEvidence(manifest.IndependentNoOp is not null, manifest.ResavedNoOp is not null,
            deterministic, stable, transformed, false, blockers);
    }

    public static IReadOnlyList<string> ValidateBinding(OracleAnalysis analysis)
    {
        var binding = analysis.EvidenceBinding;
        if (binding is null) return new[] { "Legacy/unbound analysis cannot establish provenance; reanalyze the source manifest with M0.1." };
        if (binding.AnalyzerVersion != AnalyzerVersion || binding.ManifestJson is null || binding.ProfileJson is null ||
            Digest(binding.ManifestJson) != binding.ManifestDigest || Digest(binding.ProfileJson) != binding.ProfileDigest ||
            binding.ResultDigest != ResultDigest(analysis) || binding.Files is null || binding.SelectedDefinitionIds is null)
            throw new InvalidDataException("Analysis evidence binding is forged, stale, or from a different analyzer version.");
        var manifest = OracleManifest.Parse(binding.ManifestJson);
        if (manifest.ReferenceTool != analysis.ReferenceTool || manifest.ToolVersion != analysis.ToolVersion ||
            manifest.ToolEdition != analysis.ToolEdition || manifest.ProfileId != analysis.ProfileId ||
            manifest.BaselineHash != analysis.BaselineHash || manifest.NoOpHash != analysis.NoOpHash ||
            !BoundFiles(manifest).SequenceEqual(binding.Files))
            throw new InvalidDataException("Analysis provenance no longer matches the bound source manifest.");
        var selected = analysis.Parameters.Where(item => item.SelectedCandidateId is not null)
            .ToDictionary(item => item.ParameterId, item => item.SelectedCandidateId!, StringComparer.OrdinalIgnoreCase);
        if (selected.Count != binding.SelectedDefinitionIds.Count || selected.Any(item =>
                !binding.SelectedDefinitionIds.TryGetValue(item.Key, out var value) || value != item.Value))
            throw new InvalidDataException("Selected definition ids no longer match the evidence binding.");
        var blockers = new List<string>(OracleProvenance.GetBlockers(manifest));
        CheckSource(binding.ManifestPath, binding.SourceManifestDigest, "manifest", blockers);
        CheckSource(binding.ProfilePath, binding.SourceProfileDigest, "profile", blockers);
        if (binding.ManifestPath is not null && File.Exists(binding.ManifestPath) &&
            Digest(OracleManifest.Load(binding.ManifestPath).ToJson(false)) != binding.ManifestDigest)
            throw new InvalidDataException("Source manifest digest is stale.");
        if (binding.ProfilePath is not null && File.Exists(binding.ProfilePath) &&
            Digest(JsonSerializer.Serialize(RomProfile.Load(binding.ProfilePath), JsonDefaults.Options)) != binding.ProfileDigest)
            throw new InvalidDataException("Source profile digest is stale.");
        foreach (var file in binding.Files)
        {
            if (!File.Exists(file.Path)) blockers.Add($"Bound {file.Role} file is missing: {file.Path}");
            else OracleManifestService.LoadAndVerify(file.Path, file.Hash, file.Role);
        }
        var expectedNoOp = InspectNoOp(manifest);
        if (analysis.NoOpEvidence is null || JsonSerializer.Serialize(analysis.NoOpEvidence) != JsonSerializer.Serialize(expectedNoOp))
            throw new InvalidDataException("Analysis no-op assessment differs from its bound manifest.");
        blockers.AddRange(expectedNoOp.Blockers);
        return blockers;
    }

    public static void ValidateAnalysisMetadata(OracleAnalysis analysis)
    {
        if (!Enum.IsDefined(analysis.ValidationLevel) || !Enum.IsDefined(analysis.ChecksumEvidenceLevel))
            throw new InvalidDataException("Analysis contains an invalid evidence level.");
        OracleManifestService.ValidateHash(analysis.BaselineHash, "analysis baseline");
        OracleManifestService.ValidateHash(analysis.NoOpHash, "analysis no-op");
        foreach (var ranges in new[] { analysis.NoOpNormalizationRanges, analysis.AdditionalChangedRanges,
                     analysis.ObservedChecksumChangedRanges, analysis.ActualChangedRanges, analysis.CandidateHypothesisRanges,
                     analysis.ExplainedChangedRanges, analysis.UnexplainedChangedRanges })
        {
            if (ranges is null) throw new InvalidDataException("Analysis changed ranges are missing.");
            OracleManifestService.ValidateRanges(ranges, "analysis", requireBytes: false);
        }
        if (analysis.ExcludedChecksumRegions.Any(range => range is null || range.Offset < 0 || range.Length <= 0 ||
                range.Offset > 32768 - (long)range.Length)) throw new InvalidDataException("Analysis checksum region is invalid.");
        if (analysis.Parameters.Select(item => item.ParameterId).Distinct(StringComparer.OrdinalIgnoreCase).Count() != analysis.Parameters.Count)
            throw new InvalidDataException("Analysis contains duplicate parameter ids.");
        foreach (var parameter in analysis.Parameters)
        {
            if (parameter.CaseCount < 0 || parameter.IndependentTrainingPointCount < 0 || parameter.IndependentHoldoutPointCount < 0 ||
                parameter.RepeatedObservationCount < 0 || parameter.Conflicts is null ||
                parameter.IndependentTrainingPointCount + parameter.IndependentHoldoutPointCount > parameter.CaseCount ||
                parameter.RepeatedObservationCount > parameter.CaseCount || parameter.ActualChangedRanges is null)
                throw new InvalidDataException("Invalid parameter observation counts or conflicts.");
            OracleManifestService.ValidateRanges(parameter.ActualChangedRanges, "parameter changes", requireBytes: false);
            foreach (var candidate in parameter.Candidates)
            {
                if (candidate is null || candidate.ParameterId != parameter.ParameterId || candidate.Offset < 0 ||
                    candidate.Width is not (1 or 2) || candidate.Offset > 32768 - candidate.Width ||
                    !Enum.IsDefined(candidate.EncodingType) || !Enum.IsDefined(candidate.Endianness) ||
                    (candidate.Width == 1 && candidate.Endianness != Endianness.NotApplicable) ||
                    (candidate.Width == 2 && candidate.Endianness == Endianness.NotApplicable) ||
                    candidate.CompatibleRoundingPolicies is null || candidate.RawValues is null || candidate.EngineeringValues is null ||
                    candidate.RawValues.Count < 3 || candidate.RawValues.Count != candidate.EngineeringValues.Count ||
                    candidate.CompatibleRoundingPolicies.Count == 0 || candidate.CompatibleRoundingPolicies.Any(policy => !Enum.IsDefined(policy)) ||
                    candidate.RoundingPolicy is { } rounding && !Enum.IsDefined(rounding))
                    throw new InvalidDataException("Invalid candidate shape, bounds, encoding, or rounding metadata.");
                var expectedWidth = candidate.EncodingType switch
                {
                    ParameterEncodingType.RawU8 or ParameterEncodingType.RawS8 or ParameterEncodingType.LinearU8 or ParameterEncodingType.InverseU8 => 1,
                    ParameterEncodingType.RawU16LittleEndian or ParameterEncodingType.RawU16BigEndian or ParameterEncodingType.LinearU16 or ParameterEncodingType.InverseU16 => 2,
                    _ => 0,
                };
                if (candidate.Width != expectedWidth ||
                    candidate.EncodingType == ParameterEncodingType.RawU16LittleEndian && candidate.Endianness != Endianness.Little ||
                    candidate.EncodingType == ParameterEncodingType.RawU16BigEndian && candidate.Endianness != Endianness.Big)
                    throw new InvalidDataException("Candidate width/endianness does not match its encoding.");
                var numeric = new[] { candidate.Scale, candidate.OffsetConstant, candidate.Numerator, candidate.DenominatorOffset,
                    candidate.MeanAbsoluteError, candidate.MaximumAbsoluteError, candidate.Confidence, candidate.ConversionTolerance };
                if (numeric.Any(value => !double.IsFinite(value)) || candidate.EngineeringValues.Any(value => !double.IsFinite(value)) ||
                    candidate.MeanAbsoluteError < 0 || candidate.MaximumAbsoluteError < 0 || candidate.Confidence is < 0 or > 1 ||
                    candidate.ConversionTolerance < 0 || candidate.ConversionTolerance > 1e-7 ||
                    candidate.HoldoutMaximumAbsoluteError is { } error && (!double.IsFinite(error) || error < 0) ||
                    candidate.HoldoutMeanAbsoluteError is { } meanError && (!double.IsFinite(meanError) || meanError < 0))
                    throw new InvalidDataException("Candidate numeric metadata must be finite and within valid bounds.");
                var rawMin = candidate.EncodingType == ParameterEncodingType.RawS8 ? -128 : 0;
                var rawMax = candidate.EncodingType == ParameterEncodingType.RawS8 ? 127 : candidate.Width == 1 ? 255 : 65535;
                if (candidate.RawValues.Any(value => value < rawMin || value > rawMax) ||
                    candidate.IndependentTrainingPointCount < 0 || candidate.HoldoutPointCount < 0 || candidate.FreeCoefficientCount < 0)
                    throw new InvalidDataException("Candidate raw values or observation counts are out of range.");
                if (candidate.RoundingAssessment is { Domain: { } domain } &&
                    (!double.IsFinite(domain.Minimum) || !double.IsFinite(domain.Maximum) || domain.Minimum > domain.Maximum || string.IsNullOrWhiteSpace(domain.Documentation)))
                    throw new InvalidDataException("Candidate rounding domain is invalid.");
                if (candidate.RoundingAssessment is null || candidate.RoundingAssessment.Policies is null ||
                    !Enum.IsDefined(candidate.RoundingAssessment.Status) || candidate.HoldoutCompatibleRoundingPolicies is null ||
                    candidate.HoldoutCompatibleRoundingPolicies.Any(policy => !Enum.IsDefined(policy)) || candidate.Observations is null ||
                    !Enum.IsDefined(candidate.ValidationLevel))
                    throw new InvalidDataException("Candidate validation evidence is missing.");
                if (candidate.ObservedRange is { } observed && (!double.IsFinite(observed.Minimum) || !double.IsFinite(observed.Maximum) ||
                    observed.Minimum > observed.Maximum || observed.RawMinimum > observed.RawMaximum || observed.RawMinimum < rawMin || observed.RawMaximum > rawMax))
                    throw new InvalidDataException("Candidate observed range is invalid.");
                var assessedPolicies = candidate.HoldoutPointCount > 0 ? candidate.HoldoutCompatibleRoundingPolicies : candidate.CompatibleRoundingPolicies;
                var reassessed = OracleRoundingBehavior.Assess(assessedPolicies, candidate.RoundingAssessment.Domain);
                if (analysis.FormatVersion == "2.0" && (reassessed.Status != candidate.RoundingAssessment.Status ||
                    !reassessed.Policies.SequenceEqual(candidate.RoundingAssessment.Policies)))
                    throw new InvalidDataException("Candidate rounding equivalence was not derived from its policies and domain.");
                if (analysis.FormatVersion == "2.0" && (string.IsNullOrWhiteSpace(candidate.CandidateId) ||
                    candidate.Observations.Count != parameter.CaseCount || candidate.IndependentTrainingPointCount < 3 ||
                    candidate.IndependentTrainingPointCount > parameter.CaseCount || candidate.HoldoutPointCount > parameter.CaseCount))
                    throw new InvalidDataException("Candidate ids, independent point counts, or observation provenance are invalid.");
                foreach (var observation in candidate.Observations)
                {
                    if (observation is null || string.IsNullOrWhiteSpace(observation.ObservationId) || string.IsNullOrWhiteSpace(observation.RomPath) ||
                        !double.IsFinite(observation.RequestedValue) || observation.DisplayedValue is { } displayed && !double.IsFinite(displayed) ||
                        observation.RawValue < rawMin || observation.RawValue > rawMax || !Enum.IsDefined(observation.Role) ||
                        observation.DecodingAbsoluteError is { } decodingError && (!double.IsFinite(decodingError) || decodingError < 0) ||
                        observation.ExactBytePolicies is null || observation.ExactBytePolicies.Any(policy => !Enum.IsDefined(policy)))
                        throw new InvalidDataException("Candidate observation contains invalid numeric values or provenance.");
                    if (observation.RomHash is null) throw new InvalidDataException("Candidate observation hash is missing.");
                    OracleManifestService.ValidateHash(observation.RomHash, "candidate observation");
                    try
                    {
                        if (HexUtilities.Parse(observation.RawHex).Length != candidate.Width)
                            throw new InvalidDataException("Candidate observation raw bytes do not match its width.");
                    }
                    catch (Exception exception) when (exception is ArgumentException or FormatException)
                    {
                        throw new InvalidDataException("Candidate observation bytes are malformed.", exception);
                    }
                }
            }
        }
    }

    internal static IReadOnlyList<OracleBoundFile> BoundFiles(OracleManifest manifest)
    {
        var files = new List<OracleBoundFile>
        {
            new("baseline", manifest.BaselinePath, manifest.BaselineHash),
            new("no-op", manifest.NoOpPath, manifest.NoOpHash),
        };
        if (manifest.IndependentNoOp is { } independent) files.Add(new("independent-no-op", independent.RomPath, independent.RomHash));
        if (manifest.ResavedNoOp is { } resave) files.Add(new("resaved-no-op", resave.RomPath, resave.RomHash));
        files.AddRange(manifest.Cases.Select((item, index) => new OracleBoundFile($"case:{item.ObservationId ?? index.ToString(System.Globalization.CultureInfo.InvariantCulture)}", item.RomPath, item.RomHash)));
        return files;
    }

    private static void CheckSource(string? path, string? expected, string role, ICollection<string> blockers)
    {
        if (path is null) return; // In-memory inputs bind canonical source snapshots instead.
        if (!File.Exists(path)) blockers.Add($"Bound source {role} file is missing: {path}");
        else if (expected is null || FileDigest(path) != expected) throw new InvalidDataException($"Source {role} digest is stale.");
    }

    private static bool SamePath(string left, string right) => string.Equals(Path.GetFullPath(left), Path.GetFullPath(right),
        OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
    private static string ResultDigest(OracleAnalysis analysis) => Digest(JsonSerializer.Serialize(
        analysis with { EvidenceBinding = null, AnalyzedAt = default }, JsonDefaults.Options));
    private static string Digest(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    private static string? FileDigest(string? path) => path is not null && File.Exists(path) ? Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))) : null;
}
