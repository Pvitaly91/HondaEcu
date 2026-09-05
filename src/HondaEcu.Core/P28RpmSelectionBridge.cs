using System.Numerics;
using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28RpmSelectionBand(string LowerRpm, string UpperRpm, bool LowerInclusive, bool UpperInclusive);

/// <summary>
/// Descriptive, versioned mathematical provenance. Parsing this document grants
/// neither original-parent admission, compensation authority nor export permission.
/// </summary>
public sealed record P28RpmSelectionReport(
    string FormatVersion, string Purpose, bool SyntheticOnly,
    RomHash BaselineHash, string ProfileDigest, string BindingDigest,
    string QuerySnapshotJson, string ScenarioSnapshotJson, string QueryDigest, string ScenarioDigest,
    string AnalysisDigest, string PlannerModelId, string ProducerModelId, string CompactModelId, string PolicyId,
    P28ScalingQuantity RequestedRpm, P28ThresholdSlot Slot, int OriginalRaw, int ChosenRaw, int ConfirmedRaw,
    bool ConditionalAcknowledged, P28RpmSelectionBand TransitionBand, P28RpmSelectionBand MixedRegion,
    string IntervalSemantics, string MinimaxError,
    IReadOnlyList<int> BestRawCandidates, IReadOnlyList<string> PermittedAssumptions, IReadOnlyList<string> UsedAssumptions,
    string RawPlanDigest, string ComposedPlanDigest, string RpmStatus,
    ChecksumStatus NativeChecksumStatus, NativeChecksumExecutionStatus NativeExecutionStatus,
    string HardwareStatus, bool PhysicalRpmAvailable, FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
    public string ComputeDigest() => HashUtilities.Sha256(Encoding.UTF8.GetBytes(ToJson(false)));

    public static P28RpmSelectionReport Parse(string json)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(json);
        if (Encoding.UTF8.GetByteCount(json) > 262144)
            throw new InvalidDataException("RPM selection provenance exceeds 256 KiB.");
        var report = P28RawEditJson.Parse<P28RpmSelectionReport>(json);
        P28RpmSelectionBridge.ValidateShape(report);
        // Freeze caller-independent list storage even for a parsed descriptive artifact.
        return report with
        {
            BestRawCandidates = Array.AsReadOnly(report.BestRawCandidates.ToArray()),
            PermittedAssumptions = Array.AsReadOnly(report.PermittedAssumptions.ToArray()),
            UsedAssumptions = Array.AsReadOnly(report.UsedAssumptions.ToArray()),
        };
    }

    public static P28RpmSelectionReport Load(string path)
    {
        using var input = File.OpenRead(path);
        var bytes = new byte[262145];
        var count = 0;
        while (count < bytes.Length)
        {
            var read = input.Read(bytes, count, bytes.Length - count);
            if (read == 0) break;
            count += read;
        }
        if (count > 262144) throw new InvalidDataException("RPM selection provenance exceeds 256 KiB.");
        return Parse(new UTF8Encoding(false, true).GetString(bytes, 0, count).TrimStart('\uFEFF'));
    }
}

/// <summary>An in-memory M1g preview and its RPM provenance, never a publication capability.</summary>
public sealed class P28RpmSelectionResult
{
    private readonly string selectionJson;
    internal P28RpmSelectionResult(P28RpmSelectionReport selection, P28ChecksumPreservingPreview preview)
    {
        selectionJson = selection.ToJson(false);
        CompositionPreview = preview;
    }
    public P28RpmSelectionReport SelectionReport => P28RpmSelectionReport.Parse(selectionJson);
    public P28ChecksumPreservingPreview CompositionPreview { get; }
}

/// <summary>
/// Reproduces the current mathematical selection, then delegates the entire byte
/// plan and in-memory application to the existing M1g editor. There is no writer here.
/// </summary>
public static class P28RpmSelectionBridge
{
    public const string FormatVersion = "1.0";
    public const string Purpose = "conditional-rpm-selection-to-existing-m1g-plan";
    public const string RpmStatus = "conditional-mathematical-selection-not-physical-rpm";
    public const string IntervalSemantics = "TransitionBand is the closed endpoint hull used by minimax. MixedRegion preserves actual membership: both predicate values occur in a conservative sample envelope, not a measured probability. Outside the normal supported domain, no physical switching conclusion is made.";

    public static P28RpmSelectionResult UseCandidate(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged,
        P28RpmQuery currentQuery, P28RpmPlanningReport preview, int chosenRaw, int confirmedRaw,
        bool conditionalAcknowledged, VerifiedCompensationLocation location, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(location);
        return UseCore(baseline, profile, binding, acknowledged, currentQuery, preview, chosenRaw, confirmedRaw,
            conditionalAcknowledged, location, synthetic: false, cancellationToken);
    }

    internal static P28RpmSelectionResult UseSyntheticCandidate(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged,
        P28RpmQuery currentQuery, P28RpmPlanningReport preview, int chosenRaw, int confirmedRaw,
        bool conditionalAcknowledged, CancellationToken cancellationToken = default) =>
        UseCore(baseline, profile, binding, acknowledged, currentQuery, preview, chosenRaw, confirmedRaw,
            conditionalAcknowledged, null, synthetic: true, cancellationToken);

    /// <summary>
    /// Rechecks current query/model freshness and exact plan association before a
    /// caller saves provenance or uses the unchanged M1g export workflow. This is
    /// not a replacement for M1g original-parent, definition or native-execution checks.
    /// </summary>
    public static void ValidateSelectionAgainstPlan(P28RpmQuery currentQuery, P28RpmSelectionReport selection,
        P28ChecksumPreservingPlan composedPlan, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(currentQuery);
        ArgumentNullException.ThrowIfNull(selection);
        ArgumentNullException.ThrowIfNull(composedPlan);
        cancellationToken.ThrowIfCancellationRequested();
        ValidateShape(selection);
        P28ChecksumPreservingEditor.ValidatePlanShape(composedPlan);
        if (selection.QueryDigest != currentQuery.QueryDigest || selection.ScenarioDigest != currentQuery.ScenarioDigest ||
            selection.PlannerModelId != P28RpmPlanner.ModelId || selection.ProducerModelId != P28ProducerModel.ModelId ||
            selection.CompactModelId != P28CompactModel.ModelId || selection.PolicyId != P28RpmPlanner.PolicyId ||
            selection.RawPlanDigest != P28RawThresholdEditor.ComputePlanDigest(composedPlan.ThresholdPlan) ||
            selection.ComposedPlanDigest != P28ChecksumPreservingEditor.ComputePlanDigest(composedPlan))
            throw new InvalidDataException("RPM selection no longer matches the current query, mathematical model or exact M1g plan.");
        var fresh = P28RpmPlanner.Analyze(currentQuery, cancellationToken);
        var expected = BuildSelection(currentQuery, fresh, composedPlan, selection.ChosenRaw,
            selection.ConfirmedRaw, selection.ConditionalAcknowledged);
        if (!string.Equals(selection.ToJson(false), expected.ToJson(false), StringComparison.Ordinal))
            throw new InvalidDataException("RPM selection is stale, altered or not associated with this exact current query and M1g plan.");
        cancellationToken.ThrowIfCancellationRequested();
    }

    private static P28RpmSelectionResult UseCore(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged,
        P28RpmQuery currentQuery, P28RpmPlanningReport preview, int chosenRaw, int confirmedRaw,
        bool conditionalAcknowledged, VerifiedCompensationLocation? location, bool synthetic, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(currentQuery);
        ArgumentNullException.ThrowIfNull(preview);
        cancellationToken.ThrowIfCancellationRequested();
        RequireConfirmation(chosenRaw, confirmedRaw, conditionalAcknowledged);
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, acknowledged);
        if (baseline.Span[currentQuery.Slot.Offset] != currentQuery.OriginalRaw)
            throw new InvalidDataException("RPM query original raw byte does not match the bound original baseline slot.");
        if (preview.Query.QueryDigest != currentQuery.QueryDigest)
            throw new InvalidDataException("RPM preview does not belong to the current query snapshot.");
        var fresh = P28RpmPlanner.Analyze(currentQuery, cancellationToken);
        if (preview.ComputeDigest() != fresh.ComputeDigest())
            throw new InvalidDataException("RPM preview is stale or altered; recompute after changing the scenario, query, slot, permissions or model.");
        RequireCandidate(fresh, chosenRaw);
        cancellationToken.ThrowIfCancellationRequested();
        var plan = synthetic
            ? P28ChecksumPreservingEditor.CreateSyntheticPlan(baseline, profile, binding, acknowledged, currentQuery.Slot.Id, chosenRaw)
            : P28ChecksumPreservingEditor.CreatePlan(baseline, profile, binding, acknowledged, currentQuery.Slot.Id, chosenRaw, location);
        var applied = synthetic
            ? P28ChecksumPreservingEditor.ApplySynthetic(baseline, profile, binding, plan)
            : P28ChecksumPreservingEditor.Apply(baseline, profile, binding, plan, location);
        var selection = BuildSelection(currentQuery, fresh, applied.Plan, chosenRaw, confirmedRaw, conditionalAcknowledged);
        cancellationToken.ThrowIfCancellationRequested();
        return new(selection, applied);
    }

    private static P28RpmSelectionReport BuildSelection(P28RpmQuery query, P28RpmPlanningReport fresh,
        P28ChecksumPreservingPlan plan, int chosenRaw, int confirmedRaw, bool conditionalAcknowledged)
    {
        RequireConfirmation(chosenRaw, confirmedRaw, conditionalAcknowledged);
        var candidate = RequireCandidate(fresh, chosenRaw);
        if (query.Scenario is null || query.RequestedRpm is null ||
            query.QueryDigest != fresh.Query.QueryDigest ||
            fresh.ModelId != P28RpmPlanner.ModelId || fresh.PolicyId != P28RpmPlanner.PolicyId ||
            fresh.ProducerModelId != P28ProducerModel.ModelId || fresh.CompactModelId != P28CompactModel.ModelId)
            throw new InvalidDataException("RPM selection requires the current complete scenario, request and exact mathematical models.");
        if (plan.ThresholdPlan.SlotId != query.Slot.Id || plan.ThresholdPlan.Offset != query.Slot.Offset ||
            plan.ThresholdPlan.ExpectedOldByte != query.OriginalRaw || plan.ThresholdPlan.NewByte != chosenRaw)
            throw new InvalidDataException("The M1g plan does not represent exactly the selected slot, original raw and confirmed candidate.");
        var band = candidate.TransitionBand!;
        var mixed = candidate.Regions.Single(item => item.State == P28RpmRegionState.Mixed).Interval;
        var report = new P28RpmSelectionReport(FormatVersion, Purpose, plan.SyntheticOnly,
            plan.BaselineHash, plan.ProfileDigest, plan.BindingDigest,
            P28RawEditJson.Serialize(query, false), query.Scenario.ToJson(), query.QueryDigest, query.ScenarioDigest!,
            fresh.ComputeDigest(), fresh.ModelId, fresh.ProducerModelId, fresh.CompactModelId, fresh.PolicyId,
            query.RequestedRpm, query.Slot, query.OriginalRaw, chosenRaw, confirmedRaw, conditionalAcknowledged,
            new(band.Lower, band.Upper!, band.LowerInclusive, band.UpperInclusive),
            new(mixed.Lower, mixed.Upper!, mixed.LowerInclusive, mixed.UpperInclusive), IntervalSemantics, candidate.MinimaxError!,
            Array.AsReadOnly(fresh.BestCandidates.Select(item => (int)item.RawValue).Order().ToArray()),
            Array.AsReadOnly(query.PermittedAssumptions.ToArray()), Array.AsReadOnly(fresh.UsedAssumptions.ToArray()),
            P28RawThresholdEditor.ComputePlanDigest(plan.ThresholdPlan), P28ChecksumPreservingEditor.ComputePlanDigest(plan),
            RpmStatus, ChecksumStatus.Unknown, NativeChecksumExecutionStatus.NotRun, "NotRun", false,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
        ValidateShape(report);
        return report;
    }

    private static P28RpmCandidate RequireCandidate(P28RpmPlanningReport fresh, int chosenRaw)
    {
        var candidate = fresh.Inverse.SingleOrDefault(item => item.RawValue == chosenRaw);
        if (candidate is null || !candidate.SimpleSelectable || !candidate.IsBest ||
            !fresh.BestCandidates.Any(item => item.RawValue == chosenRaw) || candidate.TransitionBand?.Upper is null ||
            candidate.MinimaxError is null || fresh.PhysicalRpmAvailable || fresh.ExecutionStatus != "NotRun" || fresh.HardwareStatus != "NotRun")
            throw new InvalidDataException("Choose an explicitly confirmed member of the complete best-candidate tie set with a finite, eligible transition band.");
        return candidate;
    }

    private static void RequireConfirmation(int chosenRaw, int confirmedRaw, bool conditionalAcknowledged)
    {
        if (chosenRaw is < 0 or > 255 || confirmedRaw is < 0 or > 255)
            throw new ArgumentOutOfRangeException(nameof(chosenRaw), "RPM raw confirmation must be from 0 through 255.");
        if (chosenRaw != confirmedRaw)
            throw new InvalidDataException("The explicitly confirmed raw value differs from the selected candidate.");
        if (!conditionalAcknowledged)
            throw new InvalidOperationException("Explicit acknowledgement of conditional mathematical RPM selection is required.");
    }

    internal static void ValidateShape(P28RpmSelectionReport report)
    {
        P28RawEditJson.ValidateObject(report);
        if (report.FormatVersion != FormatVersion || report.Purpose != Purpose || report.RpmStatus != RpmStatus ||
            report.IntervalSemantics != IntervalSemantics ||
            report.NativeChecksumStatus != ChecksumStatus.Unknown || report.NativeExecutionStatus != NativeChecksumExecutionStatus.NotRun ||
            report.HardwareStatus != "NotRun" || report.PhysicalRpmAvailable ||
            report.FlashReadiness != FlashReadinessStatus.PcInspectionOnly || report.FlashSafety != FlashSafetyStatus.NotFlashReady)
            throw new InvalidDataException("Unsupported RPM selection provenance format or promoted evidence status.");
        RequireConfirmation(report.ChosenRaw, report.ConfirmedRaw, report.ConditionalAcknowledged);
        if (report.OriginalRaw is < 0 or > 255 || !P28ThresholdLogic.GetSlots().Contains(report.Slot) ||
            report.BestRawCandidates.Count is < 1 or > 256 || report.BestRawCandidates.Any(value => value is < 0 or > 255) ||
            !report.BestRawCandidates.SequenceEqual(report.BestRawCandidates.Distinct().Order()) ||
            !report.BestRawCandidates.Contains(report.ChosenRaw))
            throw new InvalidDataException("Invalid selected slot, original raw or complete ordered candidate tie set.");
        string[] digests = [report.ProfileDigest, report.BindingDigest, report.QueryDigest, report.ScenarioDigest,
            report.AnalysisDigest, report.RawPlanDigest, report.ComposedPlanDigest];
        if (digests.Any(value => value.Length != 64 || !value.All(Uri.IsHexDigit)))
            throw new InvalidDataException("RPM provenance digests must be SHA-256 hexadecimal strings.");
        foreach (var assumptions in new[] { report.PermittedAssumptions, report.UsedAssumptions })
            if (assumptions.Count != assumptions.Distinct(StringComparer.Ordinal).Count() ||
                assumptions.Any(value => value is not (P28ProducerModel.AddEr1Assumption or P28RpmPlanner.AddEr3Assumption)))
                throw new InvalidDataException("RPM provenance contains an unknown or duplicate instruction permission.");
        if (report.UsedAssumptions.Except(report.PermittedAssumptions, StringComparer.Ordinal).Any())
            throw new InvalidDataException("RPM provenance used an instruction hypothesis without its exact permission.");
        var lower = ReadCanonicalRational(report.TransitionBand.LowerRpm, false);
        var upper = ReadCanonicalRational(report.TransitionBand.UpperRpm, false);
        _ = ReadCanonicalRational(report.MixedRegion.LowerRpm, false);
        _ = ReadCanonicalRational(report.MixedRegion.UpperRpm, false);
        _ = ReadCanonicalRational(report.MinimaxError, true);
        if (lower.Numerator * upper.Denominator >= upper.Numerator * lower.Denominator ||
            !report.TransitionBand.LowerInclusive || !report.TransitionBand.UpperInclusive ||
            report.MixedRegion.LowerInclusive || report.MixedRegion.UpperInclusive ||
            report.MixedRegion.LowerRpm != report.TransitionBand.LowerRpm || report.MixedRegion.UpperRpm != report.TransitionBand.UpperRpm)
            throw new InvalidDataException("RPM provenance requires an ordered finite open Mixed region and its distinct closed policy hull.");
        foreach (var snapshot in new[] { report.QuerySnapshotJson, report.ScenarioSnapshotJson })
        {
            if (Encoding.UTF8.GetByteCount(snapshot) > 65536)
                throw new InvalidDataException("RPM scenario/query snapshot exceeds 64 KiB.");
            using var document = JsonDocument.Parse(snapshot, new JsonDocumentOptions { MaxDepth = 16 });
            if (document.RootElement.ValueKind != JsonValueKind.Object)
                throw new InvalidDataException("RPM scenario/query snapshot must be a JSON object.");
        }
    }

    private static (BigInteger Numerator, BigInteger Denominator) ReadCanonicalRational(string value, bool allowZero)
    {
        var parts = value.Split('/');
        if (parts.Length != 2 || parts.Any(part => part.Length is < 1 or > 256 || part.Any(character => character is < '0' or > '9')) ||
            !BigInteger.TryParse(parts[0], out var numerator) || !BigInteger.TryParse(parts[1], out var denominator) ||
            numerator < (allowZero ? BigInteger.Zero : BigInteger.One) || denominator <= 0 ||
            BigInteger.GreatestCommonDivisor(numerator, denominator) != 1 || $"{numerator}/{denominator}" != value)
            throw new InvalidDataException("RPM provenance requires normalized exact nonnegative rational values.");
        return (numerator, denominator);
    }
}
