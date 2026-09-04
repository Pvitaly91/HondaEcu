using System.Buffers.Binary;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

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
    RoundingPolicy? RoundingPolicy,
    IReadOnlyList<RoundingPolicy> CompatibleRoundingPolicies,
    double MeanAbsoluteError,
    double MaximumAbsoluteError,
    double Confidence,
    IReadOnlyList<long> RawValues,
    IReadOnlyList<double> EngineeringValues,
    ValidationLevel ValidationLevel = ValidationLevel.OracleObserved)
{
    public string CandidateId { get; init; } = string.Empty;
    public RoundingPolicy? SelectedRoundingPolicy => RoundingPolicy;
    public OracleRoundingAssessment RoundingAssessment { get; init; } = OracleRoundingBehavior.Assess(Array.Empty<RoundingPolicy>(), null);
    public IReadOnlyList<RoundingPolicy> HoldoutCompatibleRoundingPolicies { get; init; } = Array.Empty<RoundingPolicy>();
    // Confidence remains a serialized 1.0 compatibility alias. Neither field is a probability.
    public double FitScore => Confidence;
    public int IndependentTrainingPointCount { get; init; }
    public int HoldoutPointCount { get; init; }
    public int FreeCoefficientCount { get; init; }
    public double TrainingMaximumAbsoluteError => MaximumAbsoluteError;
    public double TrainingMeanAbsoluteError => MeanAbsoluteError;
    public double? HoldoutMaximumAbsoluteError { get; init; }
    public double? HoldoutMeanAbsoluteError { get; init; }
    public double ConversionTolerance { get; init; }
    public bool TrainingExactByteMatch { get; init; }
    public bool HoldoutExactByteMatch { get; init; }
    public bool HasConflicts { get; init; }
    public OracleObservedRange? ObservedRange { get; init; }
    public string ExtrapolationWarning { get; init; } = "No behavior outside the independent training observations is established.";
    public IReadOnlyList<OracleObservation> Observations { get; init; } = Array.Empty<OracleObservation>();
}

public sealed record OracleObservedRange(double Minimum, double Maximum, long RawMinimum, long RawMaximum);

public sealed record OracleObservation(
    string ObservationId,
    string RomPath,
    RomHash RomHash,
    double RequestedValue,
    double? DisplayedValue,
    long RawValue,
    string RawHex,
    OracleObservationRole Role,
    bool IndependentPoint,
    double? DecodingAbsoluteError,
    IReadOnlyList<RoundingPolicy> ExactBytePolicies);

public sealed record OracleObservationConflict(
    double RequestedValue,
    IReadOnlyList<string> ObservationIds,
    IReadOnlyList<string> RomPaths,
    IReadOnlyList<RomHash> RomHashes,
    string Reason);

public sealed record OracleParameterAnalysis(
    string ParameterId,
    int CaseCount,
    IReadOnlyList<OracleCandidate> Candidates,
    IReadOnlyList<string> Warnings)
{
    public IReadOnlyList<OracleObservationConflict> Conflicts { get; init; } = Array.Empty<OracleObservationConflict>();
    public int IndependentTrainingPointCount { get; init; }
    public int IndependentHoldoutPointCount { get; init; }
    public int RepeatedObservationCount { get; init; }
    public string? SelectedCandidateId { get; init; }
    public string? SelectionRationale { get; init; }
    public IReadOnlyList<DiffRange> ActualChangedRanges { get; init; } = Array.Empty<DiffRange>();
}

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
    public IReadOnlyList<DiffRange> ActualChangedRanges { get; init; } = Array.Empty<DiffRange>();
    public IReadOnlyList<DiffRange> CandidateHypothesisRanges { get; init; } = Array.Empty<DiffRange>();
    public IReadOnlyList<DiffRange> ExplainedChangedRanges { get; init; } = Array.Empty<DiffRange>();
    public IReadOnlyList<DiffRange> UnexplainedChangedRanges { get; init; } = Array.Empty<DiffRange>();
    public ValidationLevel ChecksumEvidenceLevel { get; init; } = ValidationLevel.PublicDocumentation;
    public OracleEvidenceBinding? EvidenceBinding { get; init; }
    public OracleNoOpEvidence? NoOpEvidence { get; init; }
    public string? ToolEdition { get; init; }
    public IReadOnlyList<string> MigrationWarnings { get; init; } = Array.Empty<string>();

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));

    public static OracleAnalysis Parse(string json)
    {
        json = NormalizeFitScoreAlias(json);
        var analysis = JsonSerializer.Deserialize<OracleAnalysis>(json, JsonDefaults.Options) ??
            throw new JsonException("Oracle analysis is empty.");
        OracleAnalyzer.ValidateAnalysis(analysis);
        if (analysis.FormatVersion == "1.0")
        {
            analysis = analysis with
            {
                MigrationWarnings = new[] { "Legacy 1.0 analysis has no independent holdout or integrity binding; reanalyze its source manifest. Confidence means fit score, not probability." },
                Parameters = analysis.Parameters.Select(parameter => parameter with
                {
                    Candidates = parameter.Candidates.Select(candidate => candidate with
                    {
                        RoundingPolicy = candidate.CompatibleRoundingPolicies.Count == 1 ? candidate.CompatibleRoundingPolicies[0] : null,
                        RoundingAssessment = OracleRoundingBehavior.Assess(candidate.CompatibleRoundingPolicies, null),
                    }).ToArray(),
                }).ToArray(),
            };
        }

        OracleAnalyzer.ValidateAnalysis(analysis);
        return analysis;
    }

    private static string NormalizeFitScoreAlias(string json)
    {
        var root = JsonNode.Parse(json);
        if (root is not JsonObject rootObject)
        {
            throw new JsonException("Oracle analysis must be a JSON object.");
        }

        static KeyValuePair<string, JsonNode?> Property(JsonObject obj, string name) =>
            obj.FirstOrDefault(item => item.Key.Equals(name, StringComparison.OrdinalIgnoreCase));

        if (Property(rootObject, "parameters").Value is JsonArray parameters)
        {
            foreach (var parameter in parameters.OfType<JsonObject>())
            {
                if (Property(parameter, "candidates").Value is not JsonArray candidates)
                {
                    continue;
                }

                foreach (var candidate in candidates.OfType<JsonObject>())
                {
                    var fit = Property(candidate, "fitScore");
                    var confidence = Property(candidate, "confidence");
                    if (fit.Value is not null)
                    {
                        if (fit.Value is not JsonValue scoreValue || !scoreValue.TryGetValue<double>(out var score) || !double.IsFinite(score))
                        {
                            throw new InvalidDataException("fitScore must be a finite number.");
                        }

                        if (confidence.Value is not null)
                        {
                            if (confidence.Value is not JsonValue aliasValue || !aliasValue.TryGetValue<double>(out var alias) || score != alias)
                            {
                                throw new InvalidDataException("fitScore and its legacy confidence alias disagree.");
                            }
                        }
                        else
                        {
                            candidate["confidence"] = score;
                        }
                    }
                }
            }
        }

        return rootObject.ToJsonString();
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
        var profileValidation = profile.Validate();
        if (!profileValidation.IsValid)
        {
            throw new ProfileValidationException(profileValidation.Errors);
        }

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
        foreach (var extraNoOp in new[] { manifest.IndependentNoOp, manifest.ResavedNoOp }.OfType<OracleFileEvidence>())
        {
            OracleManifestService.LoadAndVerify(extraNoOp.RomPath, extraNoOp.RomHash, "additional no-op")
                .ValidateExactSize(profile.ExpectedSize, profile.Id);
        }

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

            var trainingValues = cases.Where(item => item.Role == OracleObservationRole.Training)
                .Select(item => item.DisplayedValue ?? item.EngineeringValue).ToHashSet();
            var holdoutValues = cases.Where(item => item.Role == OracleObservationRole.Holdout)
                .Select(item => item.DisplayedValue ?? item.EngineeringValue).Distinct().Except(trainingValues).ToArray();
            var repeatedCount = cases.Length - cases.Select(item => (item.EngineeringValue, item.DisplayedValue, item.RomHash)).Distinct().Count();
            var conflicts = FindConflicts(cases);
            if (conflicts.Count > 0)
            {
                warnings.Add("Conflicting repeated requests were retained with their provenance. They cannot confirm a definition.");
            }

            if (trainingValues.Count < 3)
            {
                warnings.Add("At least three independent training values are required. Repeated and holdout observations do not add fitting points.");
            }

            if (cases.Any(item => item.DisplayedValue is null))
            {
                warnings.Add("Some reopened displayed values are missing; requested values are a provisional fitting fallback, not independent displayed-value evidence.");
            }

            if (holdoutValues.Length == 0)
            {
                warnings.Add("No independent holdout point is available. Perfect training fit is candidate evidence only.");
            }

            var changedOffsets = images.SelectMany(image => ExpandOffsets(DiffEngine.Compare(noOp, image).Ranges)).ToHashSet();
            var parameterActualRanges = ToRanges(changedOffsets);
            changedOffsets.ExceptWith(excludedOffsets);
            var domain = manifest.RoundingDomains.FirstOrDefault(item => string.Equals(item.Key, group.Key, StringComparison.OrdinalIgnoreCase)).Value;
            var candidates = FindCandidates(group.Key, cases, images, noOp, changedOffsets, excludedOffsets, domain, conflicts.Count > 0);
            if (candidates.Count == 0)
            {
                warnings.Add("No supported raw, linear, or inverse candidate fit the independent training observations.");
            }

            foreach (var candidate in candidates)
            {
                candidateOffsets.UnionWith(Enumerable.Range(candidate.Offset, candidate.Width));
            }

            analyses.Add(new OracleParameterAnalysis(group.Key, cases.Length, candidates, warnings)
            {
                Conflicts = conflicts,
                IndependentTrainingPointCount = trainingValues.Count,
                IndependentHoldoutPointCount = holdoutValues.Length,
                RepeatedObservationCount = repeatedCount,
                ActualChangedRanges = parameterActualRanges,
            });
        }

        // A hypothesis is not an explanation: only the comparer may explain one uniquely
        // validated definition. Declared checksum storage is kept separately, with its evidence.
        var residualOffsets = allObservedOffsets.Except(excludedOffsets);
        var additional = ToRanges(residualOffsets);
        var observedChecksum = ToRanges(allObservedOffsets.Intersect(excludedOffsets));
        var analysis = new OracleAnalysis("2.0", manifest.ReferenceTool, manifest.ToolVersion, profile.Id,
            baseline.Hash, noOp.Hash, DateTimeOffset.UtcNow, actualNormalization,
            checksumRegions, additional, analyses)
        {
            ObservedChecksumChangedRanges = observedChecksum,
            ActualChangedRanges = ToRanges(allObservedOffsets),
            CandidateHypothesisRanges = ToRanges(allObservedOffsets.Intersect(candidateOffsets)),
            UnexplainedChangedRanges = ToRanges(allObservedOffsets),
            ChecksumEvidenceLevel = profile.Checksum?.EvidenceLevel ?? ValidationLevel.PublicDocumentation,
            EvidenceBinding = OracleEvidence.Bind(manifest, profile),
            NoOpEvidence = OracleEvidence.InspectNoOp(manifest),
            ToolEdition = manifest.ToolEdition,
            MigrationWarnings = manifest.FormatVersion == "1.0"
                ? new[] { "Legacy manifest observations default to training; add explicit holdout roles and edition provenance. Confidence is a legacy alias for fitScore." }
                : Array.Empty<string>(),
        };
        return OracleEvidence.Seal(analysis);
    }

    internal static void ValidateAnalysis(OracleAnalysis analysis)
    {
        ArgumentNullException.ThrowIfNull(analysis);
        if (analysis.FormatVersion is not ("1.0" or "2.0") ||
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

        OracleEvidence.ValidateAnalysisMetadata(analysis);
    }

    public static string ExportCandidate(OracleAnalysis analysis, string parameterId, int offset, ParameterEncodingType type)
    {
        ArgumentNullException.ThrowIfNull(analysis);
        var matches = analysis.Parameters
            .FirstOrDefault(parameter => string.Equals(parameter.ParameterId, parameterId, StringComparison.OrdinalIgnoreCase))?
            .Candidates.Where(item => item.Offset == offset && item.EncodingType == type).ToArray() ?? Array.Empty<OracleCandidate>();
        if (matches.Length == 0)
        {
            throw new KeyNotFoundException("Requested oracle candidate was not found.");
        }

        if (matches.Length != 1)
        {
            throw new InvalidOperationException("Offset and encoding identify several alternatives. Export by candidate ID to preserve the intended width and endianness.");
        }

        return ExportCandidate(analysis, matches[0].CandidateId);
    }

    public static string ExportCandidate(OracleAnalysis analysis, string candidateId)
    {
        ValidateAnalysis(analysis);
        if (analysis.EvidenceBinding is null)
        {
            throw new InvalidDataException("Legacy candidate export requires reanalysis of the source manifest to bind current file and profile evidence.");
        }

        _ = OracleEvidence.ValidateBinding(analysis);
        var matches = analysis.Parameters.SelectMany(parameter => parameter.Candidates).Where(candidate => candidate.CandidateId == candidateId).ToArray();
        var candidate = matches.Length == 1 ? matches[0] : throw new KeyNotFoundException("A unique candidate ID is required.");
        var fragment = new
        {
            formatVersion = "2.0",
            artifactKind = "oracle-candidate-review",
            id = candidate.ParameterId,
            candidateId = candidate.CandidateId,
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
            roundingPolicy = candidate.SelectedRoundingPolicy,
            compatibleRoundingPolicies = candidate.CompatibleRoundingPolicies,
            holdoutCompatibleRoundingPolicies = candidate.HoldoutCompatibleRoundingPolicies,
            roundingAssessment = candidate.RoundingAssessment,
            fitScore = candidate.FitScore,
            independentTrainingPointCount = candidate.IndependentTrainingPointCount,
            holdoutPointCount = candidate.HoldoutPointCount,
            freeCoefficientCount = candidate.FreeCoefficientCount,
            trainingMaximumAbsoluteError = candidate.TrainingMaximumAbsoluteError,
            holdoutMaximumAbsoluteError = candidate.HoldoutMaximumAbsoluteError,
            holdoutExactByteMatch = candidate.HoldoutExactByteMatch,
            extrapolationWarning = candidate.ExtrapolationWarning,
            writable = false,
            validationLevel = ValidationLevel.OracleObserved,
            revisionScope = $"{analysis.ProfileId}; oracle candidate only",
            sources = new[] { "oracle-manifest-review-required" },
            notes = "This read-only review artifact preserves unresolved alternatives and is not a loadable production profile definition. Review provenance and independent holdout/boundary cases before profile inclusion.",
            status = ParameterStatus.Candidate,
        };
        return JsonSerializer.Serialize(fragment, JsonDefaults.Options);
    }

    public static OracleAnalysis SelectCandidate(OracleAnalysis analysis, string parameterId, string candidateId, string rationale)
    {
        ValidateAnalysis(analysis);
        _ = OracleEvidence.ValidateBinding(analysis);
        ArgumentException.ThrowIfNullOrWhiteSpace(rationale);
        var parameter = analysis.Parameters.Single(item => string.Equals(item.ParameterId, parameterId, StringComparison.OrdinalIgnoreCase));
        if (!parameter.Candidates.Any(candidate => candidate.CandidateId == candidateId))
        {
            throw new KeyNotFoundException("Selected candidate does not belong to the requested parameter.");
        }

        return OracleEvidence.Seal(analysis with
        {
            Parameters = analysis.Parameters.Select(item => item == parameter
                ? item with { SelectedCandidateId = candidateId, SelectionRationale = rationale }
                : item).ToArray(),
        });
    }

    private static IReadOnlyList<OracleCandidate> FindCandidates(
        string parameterId,
        IReadOnlyList<OracleCase> cases,
        IReadOnlyList<RomImage> images,
        RomImage noOp,
        IReadOnlySet<int> changedOffsets,
        IReadOnlySet<int> excludedOffsets,
        OracleRoundingDomain? domain,
        bool hasConflicts)
    {
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

        return result.OrderByDescending(candidate => candidate.FitScore)
            .ThenBy(candidate => candidate.Offset).ThenBy(candidate => candidate.EncodingType).ToArray();

        void AddForWidth(int offset, int width, bool signed, Endianness endianness)
        {
            if (offset < 0 || offset > noOp.Size - width || Enumerable.Range(offset, width).Any(excludedOffsets.Contains) ||
                !tested.Add((offset, width, signed, endianness)))
            {
                return;
            }

            var raw = images.Select(image => ReadRaw(image.Span, offset, width, signed, endianness)).ToArray();
            var displayed = cases.Select(item => item.DisplayedValue ?? item.EngineeringValue).ToArray();
            var training = Enumerable.Range(0, cases.Count).Where(index => cases[index].Role == OracleObservationRole.Training).ToArray();
            // Deduplicate coefficient-fitting points only. Every case remains in the observations
            // and requested-value rounding checks, including quantization and repeated saves.
            var fitting = training.DistinctBy(index => (raw[index], displayed[index])).ToArray();
            if (fitting.Length < 3 || fitting.Select(index => raw[index]).Distinct().Count() < 3 ||
                !IsMonotonic(fitting.Select(index => raw[index]).ToArray(), fitting.Select(index => displayed[index]).ToArray()))
            {
                return;
            }

            var fitRaw = fitting.Select(index => raw[index]).ToArray();
            var fitValues = fitting.Select(index => displayed[index]).ToArray();
            var rawType = width == 1
                ? signed ? ParameterEncodingType.RawS8 : ParameterEncodingType.RawU8
                : endianness == Endianness.Little ? ParameterEncodingType.RawU16LittleEndian : ParameterEncodingType.RawU16BigEndian;
            Add(rawType, 1, 0, 1, 0, 0);
            if (!signed && TryFitLine(fitRaw.Select(value => (double)value).ToArray(), fitValues, out var scale, out var addend) &&
                Math.Abs(scale) >= 1e-12)
            {
                Add(width == 1 ? ParameterEncodingType.LinearU8 : ParameterEncodingType.LinearU16, scale, addend, 1, 0, 2);
            }

            if (!signed && TryFitInverse(fitRaw, fitValues, out var numerator, out var denominatorOffset, out var engineeringOffset) &&
                Math.Abs(numerator) >= 1e-12)
            {
                Add(width == 1 ? ParameterEncodingType.InverseU8 : ParameterEncodingType.InverseU16,
                    1, engineeringOffset, numerator, denominatorOffset, 3);
            }

            void Add(ParameterEncodingType type, double scale, double offsetConstant, double numerator, double denominatorOffset, int freeCoefficients)
            {
                double Decode(long value) => type switch
                {
                    ParameterEncodingType.LinearU8 or ParameterEncodingType.LinearU16 => value * scale + offsetConstant,
                    ParameterEncodingType.InverseU8 or ParameterEncodingType.InverseU16 => numerator / (value + denominatorOffset) + offsetConstant,
                    _ => value,
                };
                double Encode(double value) => type switch
                {
                    ParameterEncodingType.LinearU8 or ParameterEncodingType.LinearU16 => (value - offsetConstant) / scale,
                    ParameterEncodingType.InverseU8 or ParameterEncodingType.InverseU16 => numerator / (value - offsetConstant) - denominatorOffset,
                    _ => value,
                };

                var trainErrors = fitting.Select(index => Math.Abs(Decode(raw[index]) - displayed[index])).ToArray();
                // Numerical tolerance is deliberately explicit and small. It is not an editor/RPM
                // tolerance: users with rounded display values need an independently documented model.
                const double conversionTolerance = 1e-7;
                if (trainErrors.Any(error => !double.IsFinite(error) || error > conversionTolerance))
                {
                    return;
                }

                var rawPredictions = cases.Select(item => Encode(item.EngineeringValue)).ToArray();
                var compatible = CompatibleRounding(training.Select(index => raw[index]).ToArray(),
                    training.Select(index => rawPredictions[index]).ToArray());
                if (compatible.Count == 0)
                {
                    return;
                }

                var trainingKeys = fitting.Select(index => (raw[index], displayed[index])).ToHashSet();
                var trainingRequests = training.Select(index => cases[index].EngineeringValue).ToHashSet();
                var holdout = Enumerable.Range(0, cases.Count).Where(index => cases[index].Role == OracleObservationRole.Holdout).ToArray();
                var independentHoldout = holdout.Where(index => !trainingKeys.Contains((raw[index], displayed[index])) &&
                    !trainingRequests.Contains(cases[index].EngineeringValue))
                    .DistinctBy(index => (raw[index], displayed[index])).ToArray();
                var holdoutCompatible = holdout.Length == 0 ? Array.Empty<RoundingPolicy>() :
                    compatible.Where(policy => holdout.All(index => Matches(raw[index], rawPredictions[index], policy))).ToArray();
                var applicablePolicies = independentHoldout.Length > 0 ? holdoutCompatible : compatible;
                var assessedDomain = domain;
                if (domain is not null && rawPredictions.Any(value => !double.IsFinite(value) || value < domain.Minimum || value > domain.Maximum))
                {
                    // A declared domain contradicted by a used observation cannot establish behavior.
                    assessedDomain = null;
                }

                var rounding = OracleRoundingBehavior.Assess(applicablePolicies, assessedDomain);
                var holdoutErrors = holdout.Select(index => Math.Abs(Decode(raw[index]) - displayed[index])).ToArray();
                var holdoutFinite = holdoutErrors.Length > 0 && holdoutErrors.All(double.IsFinite);
                var independentIndices = fitting.Concat(independentHoldout).ToHashSet();
                var observations = Enumerable.Range(0, cases.Count).Select(index => new OracleObservation(
                    ObservationId(cases[index], index), cases[index].RomPath, cases[index].RomHash,
                    cases[index].EngineeringValue, cases[index].DisplayedValue, raw[index],
                    HexUtilities.Format(images[index].Span.Slice(offset, width)), cases[index].Role,
                    independentIndices.Contains(index),
                    double.IsFinite(Decode(raw[index])) ? Math.Abs(Decode(raw[index]) - displayed[index]) : null,
                    compatible.Where(policy => Matches(raw[index], rawPredictions[index], policy)).ToArray())).ToArray();
                var maximum = trainErrors.Max();
                var fitScore = Math.Clamp(1 - maximum / Math.Max(1, fitValues.Max() - fitValues.Min()), 0, 1);
                var idText = string.Join("|", parameterId.ToLowerInvariant(), offset, width, type, endianness,
                    scale.ToString("R", CultureInfo.InvariantCulture), offsetConstant.ToString("R", CultureInfo.InvariantCulture),
                    numerator.ToString("R", CultureInfo.InvariantCulture), denominatorOffset.ToString("R", CultureInfo.InvariantCulture));
                result.Add(new OracleCandidate(parameterId, offset, width, type, endianness, scale, offsetConstant,
                    numerator, denominatorOffset, rounding.Policies.Count == 1 ? rounding.Policies[0] : null,
                    compatible, trainErrors.Average(), maximum, fitScore, raw, displayed)
                {
                    CandidateId = HashUtilities.Sha256(Encoding.UTF8.GetBytes(idText)),
                    RoundingAssessment = rounding,
                    HoldoutCompatibleRoundingPolicies = holdoutCompatible,
                    IndependentTrainingPointCount = fitting.Length,
                    HoldoutPointCount = independentHoldout.Length,
                    FreeCoefficientCount = freeCoefficients,
                    HoldoutMaximumAbsoluteError = holdoutFinite ? holdoutErrors.Max() : null,
                    HoldoutMeanAbsoluteError = holdoutFinite ? holdoutErrors.Average() : null,
                    ConversionTolerance = conversionTolerance,
                    TrainingExactByteMatch = true,
                    HoldoutExactByteMatch = independentHoldout.Length > 0 && holdoutCompatible.Length > 0,
                    HasConflicts = hasConflicts,
                    ObservedRange = new OracleObservedRange(fitValues.Min(), fitValues.Max(), fitRaw.Min(), fitRaw.Max()),
                    ExtrapolationWarning = freeCoefficients >= fitting.Length
                        ? "The training points do not outnumber free coefficients. An exact fit may interpolate noise; independent holdouts and boundaries are required. Extrapolation is unproven."
                        : "Only the observed training range and explicitly checked holdout bytes were tested. Extrapolation is unproven.",
                    Observations = observations,
                });
            }
        }
    }

    private static IReadOnlyList<OracleObservationConflict> FindConflicts(IReadOnlyList<OracleCase> cases) =>
        cases.Select((item, index) => (Case: item, Index: index)).GroupBy(item => item.Case.EngineeringValue)
            .Where(group => group.Select(item => (item.Case.RomHash, item.Case.DisplayedValue)).Distinct().Count() > 1)
            .Select(group => new OracleObservationConflict(group.Key,
                group.Select(item => ObservationId(item.Case, item.Index)).ToArray(),
                group.Select(item => item.Case.RomPath).ToArray(),
                group.Select(item => item.Case.RomHash).ToArray(),
                "The same requested value produced different ROM bytes or reopened values. No averaging or provenance removal was performed.")).ToArray();

    private static string ObservationId(OracleCase item, int index) => item.ObservationId ?? $"case-{index + 1}";

    private static IReadOnlyList<RoundingPolicy> CompatibleRounding(IReadOnlyList<long> actual, IReadOnlyList<double> predicted) =>
        Enum.GetValues<RoundingPolicy>().Where(policy => actual.Zip(predicted, (raw, value) => Matches(raw, value, policy)).All(value => value)).ToArray();

    private static bool Matches(long actual, double predicted, RoundingPolicy policy)
    {
        if (!double.IsFinite(predicted))
        {
            return false;
        }

        // Match the codec's rounding semantics directly. Snapping near-integer inputs would
        // silently change Floor/Ceiling at precisely the boundaries the holdouts must test.
        return OracleRoundingBehavior.Round(predicted, policy) == actual;
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
            if (pairs[index].Engineering == pairs[index - 1].Engineering && pairs[index].Raw != pairs[index - 1].Raw)
            {
                return false;
            }

            increasing &= pairs[index].Raw >= pairs[index - 1].Raw;
            decreasing &= pairs[index].Raw <= pairs[index - 1].Raw;
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
