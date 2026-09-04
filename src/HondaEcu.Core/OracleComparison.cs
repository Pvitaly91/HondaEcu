using System.Text.Json;

namespace HondaEcu.Core;

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
    IReadOnlyList<OracleCandidate> CommonCandidates)
{
    public bool UniqueValidatedDefinition { get; init; }
    public bool IsAmbiguous { get; init; }
    public string? SelectedDefinitionId { get; init; }
    public string? SelectionRationale { get; init; }
    public IReadOnlyList<OracleCandidate> CromeAlternatives { get; init; } = Array.Empty<OracleCandidate>();
    public IReadOnlyList<OracleCandidate> HtsAlternatives { get; init; } = Array.Empty<OracleCandidate>();
    public IReadOnlyList<DiffRange> CromeUnexplainedRanges { get; init; } = Array.Empty<DiffRange>();
    public IReadOnlyList<DiffRange> HtsUnexplainedRanges { get; init; } = Array.Empty<DiffRange>();
    public IReadOnlyList<DiffRange> CromeExplainedRanges { get; init; } = Array.Empty<DiffRange>();
    public IReadOnlyList<DiffRange> HtsExplainedRanges { get; init; } = Array.Empty<DiffRange>();
}

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

    public string ProvenanceQualification { get; init; } = "Tool names, versions and editions are user-declared provenance, not authenticated editor output. Synthetic fixtures test algorithms only.";
    public string? CromeToolEdition { get; init; }
    public string? HtsToolEdition { get; init; }
    public bool HasAnyConfirmedParameter => SameBaseline && Parameters.Any(parameter => parameter.ValidationLevel == ValidationLevel.CrossEditorConfirmed);
    public bool AreAllRequestedParametersConfirmed => SameBaseline && Parameters.Count > 0 && Parameters.All(parameter => parameter.ValidationLevel == ValidationLevel.CrossEditorConfirmed);
    public bool AllRequestedParametersConfirmed => AreAllRequestedParametersConfirmed;
    public bool HasUnresolvedParameters => Parameters.Count == 0 || Parameters.Any(parameter => parameter.ValidationLevel != ValidationLevel.CrossEditorConfirmed);
    public bool HasConflicts => Parameters.Any(parameter => parameter.ConflictReasons.Count > 0);
    // The legacy aggregate name now conservatively means the complete requested set.
    public bool IsCrossEditorConfirmed => AreAllRequestedParametersConfirmed;

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
        if (!double.IsFinite(conversionTolerance) || conversionTolerance < 0 || conversionTolerance > 1e-6)
            throw new ArgumentOutOfRangeException(nameof(conversionTolerance), "Conversion comparison tolerance must be finite and within [0, 1e-6]; it is numerical fit comparison, not an ECU accuracy claim.");
        if (OracleProvenance.NormalizeTool(crome.ReferenceTool) == OracleProvenance.NormalizeTool(hts.ReferenceTool))
            throw new InvalidOperationException("Cross-editor comparison requires two different editors; same-tool evidence cannot confirm a parameter.");
        if (!OracleProvenance.IsExpectedTool(crome.ReferenceTool, "crome") || !OracleProvenance.IsExpectedTool(hts.ReferenceTool, "hts"))
            throw new InvalidOperationException("Cross-editor comparison requires Crome and Honda Tuning Suite provenance in their respective inputs.");
        if (!string.Equals(crome.ProfileId, hts.ProfileId, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("Oracle analyses use different ROM profiles.");
        }

        var sameBaseline = crome.BaselineHash == hts.BaselineHash;
        var provenanceBlockers = OracleEvidence.ValidateBinding(crome).Select(reason => $"Crome: {reason}")
            .Concat(OracleEvidence.ValidateBinding(hts).Select(reason => $"HTS: {reason}")).ToList();
        if (crome.EvidenceBinding is not null && hts.EvidenceBinding is not null &&
            crome.EvidenceBinding.ProfileDigest != hts.EvidenceBinding.ProfileDigest)
            provenanceBlockers.Add("Profile semantic digests differ despite matching profile ids.");
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
                          where SameDefinition(first, second, conversionTolerance)
                          select first).Distinct().ToArray();
            var validatedPairs = (from first in leftCandidates
                                  from second in rightCandidates
                                  where SameDefinition(first, second, conversionTolerance) &&
                                      HasSameEstablishedRounding(first, second) && Validated(first) && Validated(second)
                                  select (Left: first, Right: second)).ToArray();
            var viableLeft = leftCandidates.Where(NotRefuted).ToArray();
            var viableRight = rightCandidates.Where(NotRefuted).ToArray();
            var unique = validatedPairs.Length == 1 && viableLeft.Length == 1 && viableRight.Length == 1;
            var chosen = unique ? validatedPairs[0] : default;
            var reasons = new List<string>(provenanceBlockers);
            if (!sameBaseline)
            {
                reasons.Add("Crome and HTS did not use the same baseline ROM hash.");
            }

            if (left is null || right is null)
            {
                reasons.Add("Parameter is missing from one editor analysis.");
            }
            else if (common.Length == 0)
            {
                reasons.Add("No candidate has the same offset, width, endianness, and conversion.");
            }
            if (!unique) reasons.Add("No unique holdout-validated definition: all offset/width/endianness/conversion alternatives remain in the report. Manual candidate selection is not additional evidence.");
            if (left?.Conflicts.Count > 0 || right?.Conflicts.Count > 0) reasons.Add("Conflicting repeated observations remain unresolved.");
            if (viableLeft.Any(candidate => !candidate.RoundingAssessment.IsEstablished) || viableRight.Any(candidate => !candidate.RoundingAssessment.IsEstablished))
                reasons.Add("Rounding evidence includes ambiguous behavior; sample agreement is not a domain proof.");
            var leftResidual = Residual(crome, parameterId, unique ? chosen.Left : null);
            var rightResidual = Residual(hts, parameterId, unique ? chosen.Right : null);
            if (leftResidual.Count > 0) reasons.Add("Crome has unexplained changed bytes outside the unique verified definition (candidate coverage alone does not explain them).");
            if (rightResidual.Count > 0) reasons.Add("HTS has unexplained changed bytes outside the unique verified definition (including any unverified checksum storage changes).");

            var sameOffset = AnyMatch(leftCandidates, rightCandidates, (a, b) => a.Offset == b.Offset);
            var sameWidth = AnyMatch(leftCandidates, rightCandidates, (a, b) => a.Offset == b.Offset && a.Width == b.Width);
            var sameEndian = AnyMatch(leftCandidates, rightCandidates,
                (a, b) => a.Offset == b.Offset && a.Width == b.Width && a.Endianness == b.Endianness);
            var sameConversion = AnyMatch(leftCandidates, rightCandidates,
                (a, b) => a.Offset == b.Offset && a.Width == b.Width && a.Endianness == b.Endianness &&
                    a.EncodingType == b.EncodingType && SameConversion(a, b, conversionTolerance));
            var sameRounding = AnyMatch(leftCandidates, rightCandidates, (a, b) =>
                SameDefinition(a, b, conversionTolerance) && HasSameEstablishedRounding(a, b));
            var hasCommon = common.Length > 0;
            var confirmed = sameBaseline && unique && provenanceBlockers.Count == 0 &&
                left?.Conflicts.Count == 0 && right?.Conflicts.Count == 0 && leftResidual.Count == 0 && rightResidual.Count == 0;
            comparisons.Add(new CrossEditorParameterComparison(parameterId, sameOffset, sameWidth, sameEndian,
                sameConversion, sameRounding, hasCommon,
                confirmed ? ValidationLevel.CrossEditorConfirmed : ValidationLevel.OracleObserved, reasons, common)
            {
                UniqueValidatedDefinition = unique,
                IsAmbiguous = viableLeft.Length > 1 || viableRight.Length > 1 ||
                    viableLeft.Concat(viableRight).Any(candidate => !candidate.RoundingAssessment.IsEstablished),
                SelectedDefinitionId = unique ? chosen.Left.CandidateId : null,
                SelectionRationale = unique ? "This is the only definition in each analysis that survived independent holdout decoding, exact encoded-byte checks, and established rounding behavior; a manual preference was not counted as evidence." : null,
                CromeAlternatives = leftCandidates,
                HtsAlternatives = rightCandidates,
                CromeUnexplainedRanges = leftResidual,
                HtsUnexplainedRanges = rightResidual,
                CromeExplainedRanges = unique ? Explained(crome, parameterId, chosen.Left) : Array.Empty<DiffRange>(),
                HtsExplainedRanges = unique ? Explained(hts, parameterId, chosen.Right) : Array.Empty<DiffRange>(),
            });
        }

        return new CrossEditorReport("2.0", sameBaseline, crome.ProfileId,
            crome.ReferenceTool, crome.ToolVersion, hts.ReferenceTool, hts.ToolVersion,
            DateTimeOffset.UtcNow, comparisons,
            crome.AdditionalChangedRanges, hts.AdditionalChangedRanges)
        {
            CromeObservedChecksumRanges = crome.ObservedChecksumChangedRanges,
            HtsObservedChecksumRanges = hts.ObservedChecksumChangedRanges,
            CromeToolEdition = crome.ToolEdition,
            HtsToolEdition = hts.ToolEdition,
        };
    }

    private static bool SameDefinition(OracleCandidate left, OracleCandidate right, double tolerance) =>
        left.Offset == right.Offset && left.Width == right.Width && left.Endianness == right.Endianness &&
        left.EncodingType == right.EncodingType && SameConversion(left, right, tolerance);

    private static bool HasSameEstablishedRounding(OracleCandidate left, OracleCandidate right)
    {
        if (!left.RoundingAssessment.IsEstablished || !right.RoundingAssessment.IsEstablished) return false;
        var policies = left.RoundingAssessment.Policies.Union(right.RoundingAssessment.Policies).ToArray();
        if (policies.Length == 1) return true;
        var firstDomain = left.RoundingAssessment.Domain;
        var secondDomain = right.RoundingAssessment.Domain;
        if (firstDomain is null || secondDomain is null) return false;
        // A cross-editor claim covers the complete documented domains, not merely their sample overlap.
        var combined = new OracleRoundingDomain(Math.Min(firstDomain.Minimum, secondDomain.Minimum),
            Math.Max(firstDomain.Maximum, secondDomain.Maximum), "Union of both documented admissible domains.");
        return OracleRoundingBehavior.Assess(policies, combined).IsEstablished;
    }

    private static bool Validated(OracleCandidate candidate) => !candidate.HasConflicts &&
        candidate.IndependentTrainingPointCount >= 3 && candidate.HoldoutPointCount > 0 &&
        candidate.TrainingExactByteMatch && candidate.HoldoutExactByteMatch &&
        candidate.HoldoutMaximumAbsoluteError is { } error && error <= candidate.ConversionTolerance &&
        candidate.RoundingAssessment.IsEstablished;

    private static bool NotRefuted(OracleCandidate candidate) => !candidate.HasConflicts &&
        (!candidate.Observations.Any(item => item.Role == OracleObservationRole.Holdout) ||
         candidate.HoldoutMaximumAbsoluteError is { } error && error <= candidate.ConversionTolerance &&
         candidate.HoldoutCompatibleRoundingPolicies.Count > 0);

    private static IReadOnlyList<DiffRange> Explained(OracleAnalysis analysis, string parameterId, OracleCandidate chosen)
    {
        var actual = analysis.Parameters.Single(item => item.ParameterId.Equals(parameterId, StringComparison.OrdinalIgnoreCase)).ActualChangedRanges;
        return Offsets(actual).Where(offset => offset >= chosen.Offset && offset < chosen.Offset + chosen.Width)
            .Distinct().Order().Select(offset => new DiffRange(offset, 1, "", "")).ToArray();
    }

    private static IReadOnlyList<DiffRange> Residual(OracleAnalysis analysis, string parameterId, OracleCandidate? chosen)
    {
        // Recompute parameter-specific changes from the bound manifest. Other parameter series do
        // not count as side effects of this series, and a union of fitted hypotheses explains nothing.
        IEnumerable<int> changed;
        if (analysis.EvidenceBinding is { } binding)
        {
            var manifest = OracleManifest.Parse(binding.ManifestJson);
            if (File.Exists(manifest.NoOpPath) && manifest.Cases.Where(item => item.ParameterId.Equals(parameterId, StringComparison.OrdinalIgnoreCase)).All(item => File.Exists(item.RomPath)))
            {
                var noOp = OracleManifestService.LoadAndVerify(manifest.NoOpPath, manifest.NoOpHash, "no-op");
                changed = manifest.Cases.Where(item => item.ParameterId.Equals(parameterId, StringComparison.OrdinalIgnoreCase))
                    .SelectMany(item => DiffEngine.Compare(noOp, OracleManifestService.LoadAndVerify(item.RomPath, item.RomHash, "case")).Ranges)
                    .SelectMany(range => Enumerable.Range(range.Offset, range.Length)).ToArray();
            }
            else changed = Offsets(analysis.ActualChangedRanges.Concat(analysis.UnexplainedChangedRanges));
        }
        else changed = Offsets(analysis.AdditionalChangedRanges.Concat(analysis.UnexplainedChangedRanges));
        var residual = changed.ToHashSet();
        if (chosen is not null) residual.ExceptWith(Enumerable.Range(chosen.Offset, chosen.Width));
        if (analysis.ChecksumEvidenceLevel is ValidationLevel.StaticAnalysisConfirmed or ValidationLevel.BenchConfirmed or ValidationLevel.VehicleConfirmed)
            residual.ExceptWith(analysis.ExcludedChecksumRegions.SelectMany(range => Enumerable.Range(range.Offset, range.Length)));
        return residual.Order().Select(offset => new DiffRange(offset, 1, "", "")).ToArray();
    }

    private static IEnumerable<int> Offsets(IEnumerable<DiffRange> ranges) => ranges.SelectMany(range => Enumerable.Range(range.Offset, range.Length));

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
