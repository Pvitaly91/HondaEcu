using System.Text.Json;

namespace HondaEcu.Core;

public enum OracleCollectionStatus
{
    CollectionIncomplete,
    CandidateAnalysisAvailable,
    HoldoutValidationAvailable,
    CrossEditorComparisonAvailable,
}

public sealed record OracleFileCheck(string Role, string Path, bool Present, bool? HashMatches, string? Error);

public sealed record OracleParameterReadiness(
    string ParameterId,
    int IndependentTrainingPoints,
    int IndependentHoldoutPoints,
    int RepeatedObservations,
    int MissingDisplayedValues,
    int CandidateCount,
    bool HasCandidateConflicts,
    IReadOnlyList<string> Blockers);

public sealed record OraclePreflightReport(
    string FormatVersion,
    string ManifestPath,
    string? ProfileId,
    OracleCollectionStatus Status,
    string M1DataStatus,
    DateTimeOffset CheckedAt,
    IReadOnlyList<OracleFileCheck> Files,
    IReadOnlyList<OracleParameterReadiness> Parameters,
    OracleNoOpEvidence? NoOpEvidence,
    IReadOnlyList<string> ProvenanceBlockers,
    IReadOnlyList<string> Blockers,
    IReadOnlyList<string> Warnings)
{
    public string SafetyStatus => "NotFlashReady";
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));
    public void Save(string path, bool overwrite = false) => AtomicDocument.WriteAllText(path, ToJson(), overwrite);
}

public static class OraclePreflight
{
    /// <summary>Read-only collection audit. Missing, legacy or invalid inputs are reported as blockers, never invented.</summary>
    public static OraclePreflightReport Check(string manifestPath, RomProfile? profile = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(manifestPath);
        var path = Path.GetFullPath(manifestPath);
        var blockers = new List<string>();
        var warnings = new List<string>();
        var files = new List<OracleFileCheck>();
        var parameters = new List<OracleParameterReadiness>();
        OracleManifest? manifest = null;
        try
        {
            manifest = OracleManifest.Load(path);
            files.Add(new("manifest", path, true, null, null));
        }
        catch (Exception exception) when (IsInputProblem(exception))
        {
            files.Add(new("manifest", path, File.Exists(path), null, exception.Message));
            blockers.Add($"Manifest cannot be read or validated: {exception.Message}");
            return Report();
        }

        warnings.AddRange(manifest.MigrationWarnings);
        warnings.Add("Reference tool metadata is user-declared provenance, not authenticated proof of editor authorship.");
        var provenance = OracleProvenance.GetBlockers(manifest);
        blockers.AddRange(provenance);
        var noOp = OracleEvidence.InspectNoOp(manifest);
        blockers.AddRange(noOp.Blockers);
        foreach (var input in OracleEvidence.BoundFiles(manifest))
        {
            try
            {
                var rom = RomImage.Load(input.Path);
                var matches = rom.Hash == input.Hash;
                files.Add(new(input.Role, input.Path, true, matches, matches ? null : "Hash mismatch."));
                if (!matches) blockers.Add($"Hash mismatch for {input.Role}: {input.Path}");
            }
            catch (Exception exception) when (IsInputProblem(exception))
            {
                files.Add(new(input.Role, input.Path, File.Exists(input.Path), null, exception.Message));
                blockers.Add($"Cannot verify {input.Role}: {input.Path}: {exception.Message}");
            }
        }
        if (profile is null) blockers.Add("The referenced profile is unavailable; provide the exact profile to enable candidate analysis.");
        else if (profile.Id != manifest.ProfileId) blockers.Add("The supplied profile id differs from the manifest profile id.");
        else
        {
            var validation = profile.Validate();
            blockers.AddRange(validation.Errors.Select(error => $"Profile: {error}"));
        }
        OracleAnalysis? analysis = null;
        if (profile is not null && profile.Id == manifest.ProfileId && files.All(file => file.Present && file.Error is null))
        {
            try { analysis = OracleAnalyzer.Analyze(manifest, profile); }
            catch (Exception exception) when (IsInputProblem(exception)) { blockers.Add($"Candidate analysis is unavailable: {exception.Message}"); }
        }
        foreach (var group in manifest.Cases.GroupBy(item => item.ParameterId, StringComparer.OrdinalIgnoreCase))
        {
            var cases = group.ToArray();
            var result = analysis?.Parameters.SingleOrDefault(item => item.ParameterId.Equals(group.Key, StringComparison.OrdinalIgnoreCase));
            var training = cases.Where(item => item.Role == OracleObservationRole.Training)
                .Select(item => item.DisplayedValue ?? item.EngineeringValue).Distinct().ToArray();
            var holdout = cases.Where(item => item.Role == OracleObservationRole.Holdout)
                .Select(item => item.DisplayedValue ?? item.EngineeringValue).Distinct().Except(training).Count();
            var repeats = cases.Length - cases.Select(item => (item.EngineeringValue, item.DisplayedValue, item.RomHash)).Distinct().Count();
            var local = new List<string>();
            var independentTraining = result?.IndependentTrainingPointCount ?? training.Length;
            var independentHoldout = result?.IndependentHoldoutPointCount ?? holdout;
            if (independentTraining < 3) local.Add("At least three independent discovery/training points are required.");
            if (independentHoldout == 0) local.Add("Independent holdout observations outside the fitting set are missing; boundary cases must follow the actual formula and editor values.");
            if (cases.Any(item => item.DisplayedValue is null)) local.Add("Displayed values after reopening are missing.");
            if (result is null) local.Add("Candidate analysis has not been completed with verified local files.");
            else
            {
                if (result.Conflicts.Count > 0) local.Add("Conflicting repeated observations require resolution with their provenance.");
                var unrefuted = result.Candidates.Where(candidate => !candidate.HasConflicts &&
                    (!candidate.Observations.Any(item => item.Role == OracleObservationRole.Holdout) ||
                     candidate.HoldoutMaximumAbsoluteError is { } error && error <= candidate.ConversionTolerance &&
                     candidate.HoldoutCompatibleRoundingPolicies.Count > 0)).ToArray();
                var unique = unrefuted.Length == 1 && unrefuted[0].HoldoutExactByteMatch && unrefuted[0].RoundingAssessment.IsEstablished;
                if (!unique) local.Add("A unique independently holdout-validated definition has not been established; alternatives or rounding ambiguity remain.");
                if (unique)
                {
                    var candidate = unrefuted[0];
                    var remaining = result.ActualChangedRanges.SelectMany(range => Enumerable.Range(range.Offset, range.Length))
                        .Where(offset => offset < candidate.Offset || offset >= candidate.Offset + candidate.Width).ToHashSet();
                    if (analysis!.ChecksumEvidenceLevel is ValidationLevel.StaticAnalysisConfirmed or ValidationLevel.BenchConfirmed or ValidationLevel.VehicleConfirmed)
                        remaining.ExceptWith(analysis.ExcludedChecksumRegions.SelectMany(range => Enumerable.Range(range.Offset, range.Length)));
                    if (remaining.Count > 0) local.Add("Changed bytes remain unexplained outside the unique verified definition; declared checksum storage is not automatically verified.");
                }
                if (result.Candidates.Any(candidate => candidate.HoldoutPointCount > 0 && !candidate.HoldoutExactByteMatch))
                    warnings.Add($"{group.Key}: one or more candidate fits fail independent holdout encoded-byte checks.");
            }
            parameters.Add(new(group.Key, independentTraining, independentHoldout, result?.RepeatedObservationCount ?? repeats,
                cases.Count(item => item.DisplayedValue is null), result?.Candidates.Count ?? 0,
                result?.Conflicts.Count > 0 || result?.Candidates.Count > 1, local));
            blockers.AddRange(local.Select(reason => $"{group.Key}: {reason}"));
        }
        if (parameters.Count == 0) blockers.Add("No parameter observations have been collected.");
        var state = OracleCollectionStatus.CollectionIncomplete;
        if (analysis is not null && analysis.Parameters.Any(item => item.Candidates.Count > 0)) state = OracleCollectionStatus.CandidateAnalysisAvailable;
        if (state != OracleCollectionStatus.CollectionIncomplete && parameters.Any(item => item.IndependentHoldoutPoints > 0)) state = OracleCollectionStatus.HoldoutValidationAvailable;
        if (state == OracleCollectionStatus.HoldoutValidationAvailable && blockers.Count == 0)
            state = OracleCollectionStatus.CrossEditorComparisonAvailable;
        return Report(state, noOp, provenance);

        OraclePreflightReport Report(OracleCollectionStatus state = OracleCollectionStatus.CollectionIncomplete,
            OracleNoOpEvidence? noOpEvidence = null, IReadOnlyList<string>? provenanceBlockers = null) =>
            new("2.0", path, manifest?.ProfileId, state,
                files.Any(file => file.Role != "manifest" && file.Present && file.HashMatches == true) ? "LocalDataPresent" : "AwaitingUserFiles",
                DateTimeOffset.UtcNow, files, parameters, noOpEvidence, provenanceBlockers ?? Array.Empty<string>(), blockers, warnings);
    }

    private static bool IsInputProblem(Exception exception) => exception is IOException or InvalidDataException or UnauthorizedAccessException or
        JsonException or InvalidOperationException or ArgumentException or ProfileValidationException;
}
