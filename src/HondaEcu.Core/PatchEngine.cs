using System.Text.Json;

namespace HondaEcu.Core;

public sealed record ParameterAssignment(string ParameterId, double Value);

public sealed record PatchPlan(string ProfileId, IReadOnlyList<ParameterAssignment> Assignments, bool AllowUnverified = false)
{
    public static PatchPlan Create(string profileId, IEnumerable<ParameterAssignment> assignments, bool allowUnverified = false) =>
        new(profileId, Array.AsReadOnly(assignments.ToArray()), allowUnverified);
}

public sealed record PatchReport(
    string FormatVersion,
    DateTimeOffset CreatedAt,
    string ProfileId,
    RomIdentificationMethod IdentificationMethod,
    string? InputPath,
    RomHash InputHash,
    RomHash OutputHash,
    int Size,
    IReadOnlyList<ParameterChange> Changes,
    IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<DiffRange> DiffRanges,
    bool AllowUnverified,
    ChecksumStatus ChecksumStatusBefore,
    ChecksumStatus ChecksumStatusAfter,
    string ChecksumBytesBefore,
    string ChecksumBytesAfter,
    string ChecksumAlgorithmId,
    ValidationLevel ChecksumEvidenceLevel,
    FlashReadinessStatus FlashReadiness)
{
    public bool IsFlashReady => false;

    public FlashSafetyStatus FlashSafety => FlashSafetyStatus.NotFlashReady;

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));

    public static PatchReport Parse(string json)
    {
        var report = JsonSerializer.Deserialize<PatchReport>(json, JsonDefaults.Options) ??
            throw new JsonException("Patch report is empty.");
        if (string.IsNullOrWhiteSpace(report.FormatVersion) || string.IsNullOrWhiteSpace(report.ProfileId) ||
            report.InputHash is null || report.OutputHash is null || report.Changes is null ||
            report.ChangedOffsets is null || report.DiffRanges is null || report.Changes.Any(change =>
                change is null || change.Before is null || change.After is null || change.OldHex is null || change.NewHex is null))
        {
            throw new JsonException("Patch report is missing required fields.");
        }

        return report;
    }

    public static PatchReport Load(string path) => Parse(File.ReadAllText(path));
}

public sealed record PatchResult(RomImage Image, PatchReport Report);

public static class PatchEngine
{
    public static PatchResult Apply(RomImage input, RomProfile profile, PatchPlan plan, RomIdentity identity)
    {
        ArgumentNullException.ThrowIfNull(input);
        ArgumentNullException.ThrowIfNull(profile);
        ArgumentNullException.ThrowIfNull(plan);
        ArgumentNullException.ThrowIfNull(identity);
        input.ValidateExactSize(profile.ExpectedSize, profile.Id);
        if (!string.Equals(plan.ProfileId, profile.Id, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"Patch plan profile '{plan.ProfileId}' does not match '{profile.Id}'.");
        }

        if (!identity.IsIdentified || !string.Equals(identity.ProfileId, profile.Id, StringComparison.OrdinalIgnoreCase))
        {
            throw new UnknownRomException(
                "The input ROM is unknown. Select the profile explicitly and pass the resulting ExplicitOverride identity to acknowledge the risk.");
        }

        if (identity.Method is not (RomIdentificationMethod.Sha256 or RomIdentificationMethod.Signature or RomIdentificationMethod.ExplicitOverride))
        {
            throw new UnknownRomException("An identified ROM must use a supported hash, signature, or explicit-profile evidence method.");
        }

        if (identity.Method is RomIdentificationMethod.Sha256 or RomIdentificationMethod.Signature)
        {
            var independentlyIdentified = RomIdentifier.Identify(input, new[] { profile });
            if (!independentlyIdentified.IsIdentified || independentlyIdentified.Method != identity.Method)
            {
                throw new UnknownRomException("The supplied ROM identity evidence could not be reproduced.");
            }
        }

        var duplicate = plan.Assignments.GroupBy(assignment => assignment.ParameterId, StringComparer.OrdinalIgnoreCase)
            .FirstOrDefault(group => group.Count() > 1);
        if (duplicate is not null)
        {
            throw new InvalidOperationException($"Parameter '{duplicate.Key}' is assigned more than once.");
        }

        var occupied = new HashSet<int>();
        var patches = new List<BytePatch>();
        var pending = new List<(ScalarParameterDefinition Definition, double Requested, ParameterValue Before, byte[] Encoded)>();
        foreach (var assignment in plan.Assignments)
        {
            var definition = profile.GetParameter(assignment.ParameterId);
            if (!definition.Writable)
            {
                throw new ParameterNotWritableException($"Parameter '{definition.Id}' is read-only in profile '{profile.Id}'.");
            }

            if (definition.RequiresUnverifiedWriteOverride && !plan.AllowUnverified)
            {
                throw new UnverifiedParameterException(
                    $"Parameter '{definition.Id}' is only {definition.ValidationLevel}; pass an explicit unverified-write override to patch it.");
            }

            if (definition.ValidationLevel == ValidationLevel.Disproved)
            {
                throw new ParameterNotWritableException($"Parameter '{definition.Id}' has been disproved and cannot be written.");
            }

            for (var offset = definition.Offset; offset < definition.Offset + definition.Width; offset++)
            {
                if (!occupied.Add(offset))
                {
                    throw new InvalidOperationException($"Patch parameters overlap at ROM offset 0x{offset:X}.");
                }
            }

            var before = ParameterCodec.Decode(definition, input.Span);
            var encoded = ParameterCodec.Encode(definition, assignment.Value);
            patches.Add(new BytePatch(definition.Offset, encoded));
            pending.Add((definition, assignment.Value, before, encoded));
        }

        var output = input.CreateModifiedCopy(patches);
        var changes = pending.Select(item =>
        {
            var after = ParameterCodec.Decode(item.Definition, output.Span);
            return new ParameterChange(item.Definition.Id, item.Requested, item.Before, after, item.Definition.Offset,
                item.Before.RawHex, HexUtilities.Format(item.Encoded));
        }).Where(change => !string.Equals(change.OldHex, change.NewHex, StringComparison.OrdinalIgnoreCase)).ToArray();
        var diff = DiffEngine.Compare(input, output);
        var checksumBefore = ChecksumEngine.Evaluate(input, profile.Checksum);
        var checksumAfter = ChecksumEngine.Evaluate(output, profile.Checksum);
        var changedOffsets = ExpandOffsets(diff.Ranges).ToArray();
        var readiness = DetermineReadiness(changes, checksumAfter);
        var report = new PatchReport(
            "1.0",
            DateTimeOffset.UtcNow,
            profile.Id,
            identity.Method,
            input.SourcePath,
            input.Hash,
            output.Hash,
            output.Size,
            changes,
            changedOffsets,
            diff.Ranges,
            plan.AllowUnverified,
            checksumBefore.Status,
            checksumAfter.Status,
            checksumBefore.Bytes,
            checksumAfter.Bytes,
            checksumAfter.AlgorithmId,
            checksumAfter.EvidenceLevel,
            readiness);
        return new PatchResult(output, report);
    }

    public static void WriteAtomic(PatchResult result, string outputPath, string reportPath, bool overwrite = false)
    {
        ArgumentNullException.ThrowIfNull(result);
        ArgumentException.ThrowIfNullOrWhiteSpace(outputPath);
        ArgumentException.ThrowIfNullOrWhiteSpace(reportPath);
        var output = Path.GetFullPath(outputPath);
        var report = Path.GetFullPath(reportPath);
        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (string.Equals(output, report, comparison))
        {
            throw new InvalidOperationException("ROM output and patch-report paths must be different.");
        }

        AtomicFile.EnsureDifferentPath(output, result.Report.InputPath);
        AtomicFile.EnsureDifferentPath(report, result.Report.InputPath);
        AtomicOutputPair.Write(output, result.Image.Span, report, result.Report.ToJson(), overwrite);
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

    private static FlashReadinessStatus DetermineReadiness(
        IReadOnlyList<ParameterChange> changes,
        ChecksumEvaluation checksum)
    {
        if (checksum.Status is ChecksumStatus.Unknown or ChecksumStatus.Invalid)
        {
            return FlashReadinessStatus.PcInspectionOnly;
        }

        return changes.Count > 0 && changes.All(change => change.After.ValidationLevel == ValidationLevel.CrossEditorConfirmed)
            ? FlashReadinessStatus.CrossEditorValidated
            : FlashReadinessStatus.PcInspectionOnly;
    }
}

public static class ChecksumEngine
{
    public static ChecksumEvaluation Evaluate(RomImage image, ChecksumDefinition? definition)
    {
        ArgumentNullException.ThrowIfNull(image);
        if (definition is null)
        {
            return new ChecksumEvaluation(ChecksumStatus.Unknown, string.Empty, "unknown", ValidationLevel.PublicDocumentation);
        }

        var bytes = definition.Length > 0 && definition.Offset >= 0 && definition.Offset <= image.Size - definition.Length
            ? HexUtilities.Format(image.Span.Slice(definition.Offset, definition.Length))
            : string.Empty;

        // M0 deliberately does not invent or bypass a P28 checksum algorithm. Even a profile claiming a
        // status cannot make an unimplemented algorithm valid.
        return new ChecksumEvaluation(
            definition.Status == ChecksumStatus.NotApplicable ? ChecksumStatus.NotApplicable : ChecksumStatus.Unknown,
            bytes,
            definition.AlgorithmId,
            definition.EvidenceLevel);
    }
}

public sealed record VerificationIssue(string Code, string Message, int? Offset = null);

public sealed record VerificationReport(
    bool IsValid,
    string ProfileId,
    RomHash OutputHash,
    IReadOnlyList<VerificationIssue> Issues,
    DiffReport? ActualDiff,
    FlashReadinessStatus FlashReadiness)
{
    public bool IsFlashReady => false;

    public FlashSafetyStatus FlashSafety => FlashSafetyStatus.NotFlashReady;

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(this, JsonDefaults.Create(indented));
}

public static class PatchVerifier
{
    public static VerificationReport Verify(
        RomImage output,
        RomProfile profile,
        PatchReport report,
        RomImage? baseline = null)
    {
        ArgumentNullException.ThrowIfNull(output);
        ArgumentNullException.ThrowIfNull(profile);
        ArgumentNullException.ThrowIfNull(report);
        var issues = new List<VerificationIssue>();
        if (report.InputHash is null || report.OutputHash is null || report.Changes is null ||
            report.ChangedOffsets is null || report.DiffRanges is null)
        {
            issues.Add(new VerificationIssue("missing-report-field", "Patch report is missing one or more required hashes or collections."));
        }

        if (!string.Equals(report.FormatVersion, "1.0", StringComparison.Ordinal))
        {
            issues.Add(new VerificationIssue("unsupported-report-version", $"Patch report formatVersion '{report.FormatVersion}' is unsupported."));
        }

        if (!string.Equals(report.ProfileId, profile.Id, StringComparison.OrdinalIgnoreCase))
        {
            issues.Add(new VerificationIssue("profile-mismatch", $"Patch report profile '{report.ProfileId}' does not match '{profile.Id}'."));
        }

        if (report.IdentificationMethod is not (RomIdentificationMethod.Sha256 or RomIdentificationMethod.Signature or RomIdentificationMethod.ExplicitOverride))
        {
            issues.Add(new VerificationIssue("invalid-identification-method",
                "Patch report does not record a supported hash, signature, or explicit profile confirmation method."));
        }

        if (output.Size != profile.ExpectedSize || output.Size != report.Size)
        {
            issues.Add(new VerificationIssue("size-mismatch", "Output size does not match the profile and patch report."));
        }

        if (output.Hash != report.OutputHash)
        {
            issues.Add(new VerificationIssue("output-hash-mismatch", "Output SHA-256 or CRC32 does not match the patch report."));
        }

        var declaredOffsets = (report.ChangedOffsets ?? Array.Empty<int>()).ToHashSet();
        if (declaredOffsets.Count != (report.ChangedOffsets?.Count ?? 0) || declaredOffsets.Any(offset => offset < 0 || offset >= output.Size))
        {
            issues.Add(new VerificationIssue("invalid-declared-offsets", "ChangedOffsets contains duplicates or out-of-bounds offsets."));
        }

        var rangeOffsets = ValidateAndExpandRanges(report.DiffRanges, output.Size, issues);
        if (!rangeOffsets.SetEquals(declaredOffsets))
        {
            issues.Add(new VerificationIssue("report-diff-inconsistent", "ChangedOffsets and DiffRanges do not describe the same bytes."));
        }

        var allowedOffsets = new HashSet<int>();
        var changes = report.Changes ?? Array.Empty<ParameterChange>();
        foreach (var duplicate in changes
            .Where(change => change is not null)
            .GroupBy(change => change.ParameterId ?? string.Empty, StringComparer.OrdinalIgnoreCase)
            .Where(group => group.Count() > 1))
        {
            issues.Add(new VerificationIssue("duplicate-parameter-change",
                $"Parameter '{duplicate.Key}' appears more than once in the patch report."));
        }

        foreach (var change in changes)
        {
            if (change is null)
            {
                issues.Add(new VerificationIssue("null-change", "Patch report contains a null change entry."));
                continue;
            }

            if (change.Before is null || change.After is null)
            {
                issues.Add(new VerificationIssue("malformed-change",
                    $"Change '{change.ParameterId}' is missing Before or After metadata.", change.Offset));
                continue;
            }

            ScalarParameterDefinition definition;
            try
            {
                definition = profile.GetParameter(change.ParameterId);
            }
            catch (KeyNotFoundException)
            {
                issues.Add(new VerificationIssue("unknown-parameter", $"Report names unknown parameter '{change.ParameterId}'.", change.Offset));
                continue;
            }

            if (!definition.Writable || definition.ValidationLevel == ValidationLevel.Disproved)
            {
                issues.Add(new VerificationIssue("parameter-not-writable", $"Report changes read-only or disproved parameter '{definition.Id}'.", definition.Offset));
                continue;
            }

            if (definition.RequiresUnverifiedWriteOverride && !report.AllowUnverified)
            {
                issues.Add(new VerificationIssue("unverified-override-missing", $"Report lacks the explicit unverified-write acknowledgement for '{definition.Id}'.", definition.Offset));
                continue;
            }

            if (change.Offset != definition.Offset)
            {
                issues.Add(new VerificationIssue("offset-mismatch", $"Reported offset for '{change.ParameterId}' differs from the profile.", change.Offset));
                continue;
            }

            byte[] statedOld;
            byte[] statedNew;
            try
            {
                statedOld = HexUtilities.Parse(change.OldHex);
                statedNew = HexUtilities.Parse(change.NewHex);
            }
            catch (Exception exception) when (exception is FormatException or ArgumentException)
            {
                issues.Add(new VerificationIssue("invalid-change-hex", exception.Message, change.Offset));
                continue;
            }

            if (statedOld.Length != definition.Width || statedNew.Length != definition.Width)
            {
                issues.Add(new VerificationIssue("change-width-mismatch", $"Reported byte width for '{change.ParameterId}' differs from the profile.", change.Offset));
                continue;
            }

            if (!string.Equals(change.Before.ParameterId, definition.Id, StringComparison.OrdinalIgnoreCase) ||
                !string.Equals(change.After.ParameterId, definition.Id, StringComparison.OrdinalIgnoreCase) ||
                change.Before.Offset != definition.Offset || change.After.Offset != definition.Offset ||
                !string.Equals(change.Before.RawHex, change.OldHex, StringComparison.OrdinalIgnoreCase) ||
                !string.Equals(change.After.RawHex, change.NewHex, StringComparison.OrdinalIgnoreCase))
            {
                issues.Add(new VerificationIssue("change-metadata-mismatch", $"Before/after metadata for '{definition.Id}' is inconsistent.", definition.Offset));
            }

            try
            {
                var requestedBytes = ParameterCodec.Encode(definition, change.RequestedValue);
                if (!requestedBytes.AsSpan().SequenceEqual(statedNew))
                {
                    issues.Add(new VerificationIssue("requested-value-mismatch", $"Requested engineering value for '{definition.Id}' does not encode to NewHex.", definition.Offset));
                }
            }
            catch (Exception exception) when (exception is ParameterEncodingException or ParameterValueOutOfRangeException or NotSupportedException)
            {
                issues.Add(new VerificationIssue("requested-value-invalid", exception.Message, definition.Offset));
            }

            for (var offset = definition.Offset; offset < definition.Offset + definition.Width; offset++)
            {
                allowedOffsets.Add(offset);
            }

            var actualHex = HexUtilities.Format(output.Span.Slice(definition.Offset, definition.Width));
            if (!string.Equals(actualHex, change.NewHex, StringComparison.OrdinalIgnoreCase))
            {
                issues.Add(new VerificationIssue("declared-byte-mismatch", $"Output bytes for '{change.ParameterId}' do not match the report.", definition.Offset));
            }

            try
            {
                var decoded = ParameterCodec.Decode(definition, output.Span);
                if (!ParameterValuesEquivalent(decoded, change.After))
                {
                    issues.Add(new VerificationIssue("after-value-mismatch", $"Decoded output value for '{definition.Id}' differs from report After metadata.", definition.Offset));
                }

                if (decoded.RawValue < definition.RawMinimum || decoded.RawValue > definition.RawMaximum ||
                    decoded.EngineeringValue < definition.EngineeringMinimum || decoded.EngineeringValue > definition.EngineeringMaximum)
                {
                    issues.Add(new VerificationIssue("value-out-of-range", $"Output value for '{definition.Id}' is outside the profile range.", definition.Offset));
                }
            }
            catch (Exception exception) when (exception is ParameterEncodingException or NotSupportedException)
            {
                issues.Add(new VerificationIssue("decode-failed", exception.Message, definition.Offset));
            }
        }

        foreach (var offset in declaredOffsets.Except(allowedOffsets).Order())
        {
            issues.Add(new VerificationIssue("unowned-declared-change",
                $"Offset 0x{offset:X} is not owned by a reported parameter or permitted checksum region.", offset));
        }

        baseline ??= TryLoadBaseline(report.InputPath);
        DiffReport? actualDiff = null;
        if (baseline is null)
        {
            issues.Add(new VerificationIssue("baseline-unavailable",
                "The baseline ROM is unavailable, so undeclared byte changes cannot be independently checked."));
        }
        else
        {
            if (baseline.Hash != report.InputHash)
            {
                issues.Add(new VerificationIssue("input-hash-mismatch", "Baseline ROM does not match the report input hash."));
            }

            if (report.IdentificationMethod is RomIdentificationMethod.Sha256 or RomIdentificationMethod.Signature)
            {
                var actualIdentity = RomIdentifier.Identify(baseline, new[] { profile });
                if (!actualIdentity.IsIdentified || actualIdentity.Method != report.IdentificationMethod)
                {
                    issues.Add(new VerificationIssue("identity-evidence-mismatch", "Baseline does not reproduce the report's identification method."));
                }
            }

            actualDiff = DiffEngine.Compare(baseline, output);
            var actualOffsets = ExpandOffsets(actualDiff.Ranges).ToHashSet();
            foreach (var offset in actualOffsets.Except(declaredOffsets).Order())
            {
                issues.Add(new VerificationIssue("undeclared-change", $"Offset 0x{offset:X} changed but was not declared.", offset));
            }

            foreach (var offset in declaredOffsets.Except(actualOffsets).Order())
            {
                issues.Add(new VerificationIssue("missing-declared-change", $"Declared offset 0x{offset:X} did not actually change.", offset));
            }


            if (!actualDiff.Ranges.SequenceEqual(report.DiffRanges ?? Array.Empty<DiffRange>()))
            {
                issues.Add(new VerificationIssue("reported-diff-mismatch", "Patch report diff ranges do not match the independent byte diff."));
            }

            foreach (var change in changes)
            {
                if (change is null || change.Before is null || change.After is null ||
                    change.OldHex is null || change.NewHex is null)
                {
                    continue;
                }

                if (change.Offset >= 0 && change.Offset <= baseline.Size - (change.OldHex.Length / 2))
                {
                    var oldHex = HexUtilities.Format(baseline.Span.Slice(change.Offset, change.OldHex.Length / 2));
                    if (!string.Equals(oldHex, change.OldHex, StringComparison.OrdinalIgnoreCase))
                    {
                        issues.Add(new VerificationIssue("old-byte-mismatch", $"Baseline bytes for '{change.ParameterId}' do not match the report.", change.Offset));
                    }

                    try
                    {
                        var definition = profile.GetParameter(change.ParameterId);
                        var decodedBefore = ParameterCodec.Decode(definition, baseline.Span);
                        if (!ParameterValuesEquivalent(decodedBefore, change.Before))
                        {
                            issues.Add(new VerificationIssue("before-value-mismatch", $"Decoded baseline value for '{definition.Id}' differs from report Before metadata.", definition.Offset));
                        }
                    }
                    catch (KeyNotFoundException)
                    {
                        // Already reported while validating changes.
                    }
                }
            }
        }

        var checksum = ChecksumEngine.Evaluate(output, profile.Checksum);
        if (checksum.Status != report.ChecksumStatusAfter ||
            !string.Equals(checksum.Bytes, report.ChecksumBytesAfter, StringComparison.OrdinalIgnoreCase) ||
            !string.Equals(checksum.AlgorithmId, report.ChecksumAlgorithmId, StringComparison.Ordinal) ||
            checksum.EvidenceLevel != report.ChecksumEvidenceLevel)
        {
            issues.Add(new VerificationIssue("checksum-report-mismatch", "Current checksum assessment differs from the patch report."));
        }

        if (baseline is not null)
        {
            var checksumBefore = ChecksumEngine.Evaluate(baseline, profile.Checksum);
            if (checksumBefore.Status != report.ChecksumStatusBefore ||
                !string.Equals(checksumBefore.Bytes, report.ChecksumBytesBefore, StringComparison.OrdinalIgnoreCase))
            {
                issues.Add(new VerificationIssue("checksum-before-mismatch", "Baseline checksum assessment differs from the patch report."));
            }
        }

        var readiness = RecomputeReadiness(profile, changes, checksum);
        if (report.FlashReadiness != readiness || report.FlashReadiness >= FlashReadinessStatus.BenchCandidate)
        {
            issues.Add(new VerificationIssue("invalid-flash-readiness", "Patch report flash readiness is not supported by the current evidence."));
            readiness = FlashReadinessStatus.PcInspectionOnly;
        }

        if (issues.Count > 0)
        {
            readiness = FlashReadinessStatus.PcInspectionOnly;
        }

        return new VerificationReport(issues.Count == 0, profile.Id, output.Hash, issues, actualDiff, readiness);
    }

    private static RomImage? TryLoadBaseline(string? path) =>
        path is not null && File.Exists(path) ? RomImage.Load(path) : null;

    private static FlashReadinessStatus RecomputeReadiness(
        RomProfile profile,
        IReadOnlyList<ParameterChange> changes,
        ChecksumEvaluation checksum)
    {
        if (checksum.Status is ChecksumStatus.Unknown or ChecksumStatus.Invalid)
        {
            return FlashReadinessStatus.PcInspectionOnly;
        }

        return changes.Count > 0 && changes.All(change => change is not null &&
            profile.Parameters.FirstOrDefault(parameter => string.Equals(parameter.Id, change.ParameterId, StringComparison.OrdinalIgnoreCase))
                ?.ValidationLevel == ValidationLevel.CrossEditorConfirmed)
            ? FlashReadinessStatus.CrossEditorValidated
            : FlashReadinessStatus.PcInspectionOnly;
    }

    private static bool ParameterValuesEquivalent(ParameterValue actual, ParameterValue reported) =>
        string.Equals(actual.ParameterId, reported.ParameterId, StringComparison.OrdinalIgnoreCase) &&
        actual.Offset == reported.Offset && actual.RawValue == reported.RawValue &&
        string.Equals(actual.RawHex, reported.RawHex, StringComparison.OrdinalIgnoreCase) &&
        NearlyEqual(actual.EngineeringValue, reported.EngineeringValue) &&
        actual.ValidationLevel == reported.ValidationLevel && actual.Writable == reported.Writable;

    private static bool NearlyEqual(double left, double right) =>
        Math.Abs(left - right) <= 1e-9 * Math.Max(1, Math.Max(Math.Abs(left), Math.Abs(right)));

    private static HashSet<int> ValidateAndExpandRanges(
        IReadOnlyList<DiffRange>? ranges,
        int size,
        ICollection<VerificationIssue> issues)
    {
        var offsets = new HashSet<int>();
        var previousEnd = -2;
        foreach (var range in ranges ?? Array.Empty<DiffRange>())
        {
            if (range is null || range.Offset < 0 || range.Length <= 0 || range.Offset > size - range.Length)
            {
                issues.Add(new VerificationIssue("invalid-diff-range", "Patch report contains a null or out-of-bounds diff range."));
                continue;
            }

            if (range.Offset <= previousEnd + 1)
            {
                issues.Add(new VerificationIssue("noncanonical-diff-ranges", "Diff ranges overlap, touch, or are not sorted."));
            }

            try
            {
                if (HexUtilities.Parse(range.OldHex).Length != range.Length || HexUtilities.Parse(range.NewHex).Length != range.Length)
                {
                    issues.Add(new VerificationIssue("diff-range-width-mismatch", "Diff range hex length does not match its length.", range.Offset));
                }
            }
            catch (Exception exception) when (exception is FormatException or ArgumentException)
            {
                issues.Add(new VerificationIssue("invalid-diff-range-hex", exception.Message, range.Offset));
            }

            for (var offset = range.Offset; offset < range.Offset + range.Length; offset++)
            {
                offsets.Add(offset);
            }

            previousEnd = range.EndOffset;
        }

        return offsets;
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
}

internal static class AtomicOutputPair
{
    public static void Write(string outputPath, ReadOnlySpan<byte> outputBytes, string reportPath, string reportJson, bool overwrite)
    {
        if (overwrite)
        {
            throw new NotSupportedException("HondaEcu never overwrites an existing ROM or patch report.");
        }

        var outputDirectory = Path.GetDirectoryName(outputPath) ?? Directory.GetCurrentDirectory();
        var reportDirectory = Path.GetDirectoryName(reportPath) ?? Directory.GetCurrentDirectory();
        Directory.CreateDirectory(outputDirectory);
        Directory.CreateDirectory(reportDirectory);
        if (File.Exists(outputPath) || File.Exists(reportPath))
        {
            throw new IOException("Output ROM and patch report must both be new files unless overwrite is explicitly enabled.");
        }

        var outputTemporary = Path.Combine(outputDirectory, $".{Path.GetFileName(outputPath)}.{Guid.NewGuid():N}.tmp");
        var reportTemporary = Path.Combine(reportDirectory, $".{Path.GetFileName(reportPath)}.{Guid.NewGuid():N}.tmp");
        var reportMoved = false;
        try
        {
            WriteTemporary(outputTemporary, outputBytes);
            WriteTemporary(reportTemporary, System.Text.Encoding.UTF8.GetBytes(reportJson));
            File.Move(reportTemporary, reportPath);
            reportMoved = true;
            File.Move(outputTemporary, outputPath);
        }
        catch
        {
            if (reportMoved && File.Exists(reportPath))
            {
                File.Delete(reportPath);
            }

            throw;
        }
        finally
        {
            if (File.Exists(outputTemporary))
            {
                File.Delete(outputTemporary);
            }

            if (File.Exists(reportTemporary))
            {
                File.Delete(reportTemporary);
            }
        }
    }

    private static void WriteTemporary(string path, ReadOnlySpan<byte> contents)
    {
        using var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough);
        stream.Write(contents);
        stream.Flush(flushToDisk: true);
    }
}

public sealed class UnknownRomException : InvalidOperationException
{
    public UnknownRomException(string message)
        : base(message)
    {
    }
}

public sealed class ParameterNotWritableException : InvalidOperationException
{
    public ParameterNotWritableException(string message)
        : base(message)
    {
    }
}

public sealed class UnverifiedParameterException : InvalidOperationException
{
    public UnverifiedParameterException(string message)
        : base(message)
    {
    }
}
