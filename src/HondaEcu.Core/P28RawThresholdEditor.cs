using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed record P28PredicateRow(byte CompactCode, bool Before, bool After);

public sealed record P28SlotSelectionProof(
    string SlotId, int ComparedCodeCount, bool IsEditedSelection,
    bool ThresholdByteUnchanged, bool PredicateResultsUnchanged);

public sealed record P28PairOrientation(byte PriorClearThreshold, byte PriorSetThreshold, string Relation);

public sealed record P28PredicateImpact(
    string Predicate, bool EqualityResult, int ComparedCodeCount,
    IReadOnlyList<P28PredicateRow> Rows, IReadOnlyList<int> ChangedCompactCodes,
    IReadOnlyList<P28SlotSelectionProof> Selections,
    P28PairOrientation BeforePair, P28PairOrientation AfterPair, string Qualification);

public sealed record P28RawEditEvidence(
    string ThresholdPredicate, string CompactModel, string PhysicalRpm,
    string OriginalBinExecution, string EditorChecks, string HardwareChecks, string FactoryProvenance);

public sealed record P28RawThresholdPlan(
    string FormatVersion, string Purpose, string ModelId, string ProfileId, int Size,
    RomHash BaselineHash, string ProfileDigest, string BindingDigest, bool ProfileAcknowledged,
    string SlotId, int Context, int Pair, bool PriorState, int Offset,
    byte ExpectedOldByte, byte NewByte, IReadOnlyList<int> ExpectedChangedOffsets, bool IsNoOp,
    P28PredicateImpact PredicateImpact, P28RawEditEvidence Evidence, ChecksumStatus ChecksumStatus,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);

    public static P28RawThresholdPlan Parse(string json)
    {
        var plan = P28RawEditJson.Parse<P28RawThresholdPlan>(json);
        P28RawThresholdEditor.ValidatePlanShape(plan);
        return plan;
    }

    public static P28RawThresholdPlan Load(string path) => Parse(File.ReadAllText(path));
}

public sealed record P28RawByteDiff(int Offset, byte OldByte, byte NewByte);

public sealed record P28RawThresholdPatchReport(
    string FormatVersion, string Purpose, string ModelId, string ProfileId, int Size,
    RomHash BaselineHash, RomHash OutputHash, string ProfileDigest, string BindingDigest, string PlanDigest,
    string SlotId, int Offset, byte OldByte, byte NewByte,
    IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28RawByteDiff> Diff, int ChangedByteCount,
    bool IsNoOp, bool ReverseRestoresBaseline, P28PredicateImpact PredicateImpact,
    P28RawEditEvidence Evidence, ChecksumStatus ChecksumStatus,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);

    public static P28RawThresholdPatchReport Parse(string json)
    {
        var report = P28RawEditJson.Parse<P28RawThresholdPatchReport>(json);
        P28RawThresholdEditor.ValidateReportShape(report);
        return report;
    }

    public static P28RawThresholdPatchReport Load(string path) => Parse(File.ReadAllText(path));
}

/// <summary>Created only by validated Apply. Keeps the parent snapshot for pre-write revalidation.</summary>
public sealed class P28RawThresholdPatchResult
{
    internal P28RawThresholdPatchResult(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28RawThresholdPlan plan, RomImage image, P28RawThresholdPatchReport report)
    {
        Baseline = baseline;
        Profile = profile;
        Binding = binding;
        Plan = plan;
        Image = image;
        Report = report;
    }

    internal RomImage Baseline { get; }
    internal RomProfile Profile { get; }
    internal P28ExactBaselineBinding Binding { get; }
    internal P28RawThresholdPlan Plan { get; }
    public RomImage Image { get; }
    public P28RawThresholdPatchReport Report { get; }
}

public sealed record P28RawThresholdVerificationReport(
    bool IsValid, IReadOnlyList<VerificationIssue> Issues, RomHash BaselineHash, RomHash OutputHash,
    string SlotId, int? Offset, byte? ReadbackByte, bool ReverseRestoresBaseline,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
}

public sealed record P28DerivedThresholdInspectionReport(
    bool VerifiedLineage, P28RawThresholdVerificationReport Verification,
    P28VtecInspectionReport OutputInspection, IReadOnlyList<P28ThresholdContextReport> DerivedContexts,
    bool PhysicalRpmAvailable, FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
}

/// <summary>
/// One-step, one-slot raw-byte research edits. Never changes public profile writability,
/// computes physical RPM, repairs a checksum, or certifies an image for an ECU.
/// </summary>
public static class P28RawThresholdEditor
{
    public const string FormatVersion = "1.0";
    public const string Purpose = "pc-only-one-slot-raw-threshold-research";

    public static string ComputeBindingDigest(P28ExactBaselineBinding binding)
    {
        ArgumentNullException.ThrowIfNull(binding);
        return HashUtilities.Sha256(Encoding.UTF8.GetBytes(binding.ToJson(false)));
    }

    public static string ComputePlanDigest(P28RawThresholdPlan plan)
    {
        ArgumentNullException.ThrowIfNull(plan);
        return HashUtilities.Sha256(Encoding.UTF8.GetBytes(plan.ToJson(false)));
    }

    public static P28RawThresholdPlan CreatePlan(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        bool acknowledged, string slotId, int rawValue)
    {
        if (!acknowledged)
        {
            throw new InvalidOperationException("Explicit profile acknowledgement is required to plan a raw edit.");
        }

        ValidateBaseline(baseline, profile, binding);
        if (rawValue is < byte.MinValue or > byte.MaxValue)
        {
            throw new ArgumentOutOfRangeException(nameof(rawValue), "Raw threshold must be an integer from 0 through 255.");
        }

        var slot = P28ThresholdLogic.ResolveSlot(slotId);
        var oldByte = baseline.Span[slot.Offset];
        var newByte = checked((byte)rawValue);
        return new P28RawThresholdPlan(
            FormatVersion, Purpose, P28CompactModel.ModelId, profile.Id, baseline.Size,
            baseline.Hash, P28VtecInspector.ComputeProfileDigest(profile), ComputeBindingDigest(binding), true,
            slot.Id, slot.Context, slot.Pair, slot.PriorState, slot.Offset, oldByte, newByte,
            ReadOnly(oldByte == newByte ? Array.Empty<int>() : new[] { slot.Offset }), oldByte == newByte,
            ComparePredicates(baseline, slot, newByte), Evidence(), ChecksumStatus.Unknown,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    public static P28RawThresholdPatchResult Apply(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, P28RawThresholdPlan plan)
    {
        ArgumentNullException.ThrowIfNull(plan);
        ValidatePlanShape(plan);
        var expected = CreatePlan(baseline, profile, binding, plan.ProfileAcknowledged, plan.SlotId, plan.NewByte);
        RequireSame(plan, expected, "Plan metadata does not reproduce from the supplied parent, profile and binding.");

        var output = baseline.CreateModifiedCopy(new[] { new BytePatch(expected.Offset, new[] { expected.NewByte }) });
        var report = Measure(baseline, output, expected);
        return new P28RawThresholdPatchResult(baseline, profile, binding, expected, output, report);
    }

    public static P28RawThresholdVerificationReport Verify(
        RomImage output, RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28RawThresholdPlan plan, P28RawThresholdPatchReport report)
    {
        ArgumentNullException.ThrowIfNull(output);
        ArgumentNullException.ThrowIfNull(baseline);
        var issues = new List<VerificationIssue>();
        int? offset = null;
        byte? readback = null;
        var reversed = false;
        try
        {
            ArgumentNullException.ThrowIfNull(report);
            ValidateReportShape(report);
            var expected = Apply(baseline, profile, binding, plan);
            output.ValidateExactSize(baseline.Size);
            offset = expected.Report.Offset;
            readback = output.Span[offset.Value];
            var measured = Measure(baseline, output, expected.Plan);
            reversed = measured.ReverseRestoresBaseline;
            RequireSame(measured, expected.Report, "Output does not equal the exact declared single-slot transformation.");
            RequireSame(report, measured, "Patch report does not equal independently measured output evidence.");
        }
        catch (Exception exception) when (InputProblem(exception))
        {
            issues.Add(new VerificationIssue("raw-threshold-lineage-invalid", exception.Message));
        }

        return new P28RawThresholdVerificationReport(
            issues.Count == 0, issues.AsReadOnly(), baseline.Hash, output.Hash,
            plan?.SlotId ?? "unavailable", offset, readback, reversed,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    public static P28DerivedThresholdInspectionReport InspectDerived(
        RomImage output, RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28RawThresholdPlan plan, P28RawThresholdPatchReport report)
    {
        var verification = Verify(output, baseline, profile, binding, plan, report);
        // Deliberately keep the original binding: a changed output must show Mismatched.
        var inspection = P28VtecInspector.Inspect(output, profile, new[] { profile }, true, binding);
        var contexts = verification.IsValid ? BuildDerivedContexts(output) : Array.Empty<P28ThresholdContextReport>();
        return new P28DerivedThresholdInspectionReport(
            verification.IsValid, verification, inspection, contexts, false,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    /// <summary>
    /// Uses the existing staged two-file publication with best-effort rollback, not an OS
    /// transaction. No existing path is overwritten. The result is reverified before writing.
    /// </summary>
    public static void WriteAtomic(
        P28RawThresholdPatchResult result, string outputPath, string reportPath,
        IEnumerable<string>? protectedPaths = null)
    {
        ArgumentNullException.ThrowIfNull(result);
        ArgumentException.ThrowIfNullOrWhiteSpace(outputPath);
        ArgumentException.ThrowIfNullOrWhiteSpace(reportPath);
        var verification = Verify(result.Image, result.Baseline, result.Profile, result.Binding, result.Plan, result.Report);
        if (!verification.IsValid)
        {
            throw new InvalidDataException("Raw patch result failed pre-write verification.");
        }

        var output = Path.GetFullPath(outputPath);
        var report = Path.GetFullPath(reportPath);
        AtomicFile.EnsureDifferentPath(output, report);
        foreach (var path in (protectedPaths ?? Array.Empty<string>()).Concat(new[]
        {
            result.Baseline.SourcePath, result.Profile.SourcePath,
        }.OfType<string>()))
        {
            AtomicFile.EnsureDifferentPath(output, path);
            AtomicFile.EnsureDifferentPath(report, path);
        }

        AtomicOutputPair.Write(output, result.Image.Span, report, result.Report.ToJson(), overwrite: false);
    }

    internal static void ValidatePlanShape(P28RawThresholdPlan plan)
    {
        P28RawEditJson.ValidateObject(plan);
        ValidateCommon(plan.FormatVersion, plan.Purpose, plan.ModelId, plan.ProfileId, plan.Size,
            plan.BaselineHash, plan.ProfileDigest, plan.BindingDigest, plan.ChecksumStatus,
            plan.FlashReadiness, plan.FlashSafety);
        var slot = P28ThresholdLogic.ResolveSlot(plan.SlotId);
        if (!plan.ProfileAcknowledged || plan.Offset != slot.Offset || plan.Context != slot.Context ||
            plan.Pair != slot.Pair || plan.PriorState != slot.PriorState ||
            plan.IsNoOp != (plan.ExpectedOldByte == plan.NewByte) ||
            !plan.ExpectedChangedOffsets.SequenceEqual(plan.IsNoOp ? Array.Empty<int>() : new[] { slot.Offset }))
        {
            throw new InvalidDataException("Plan slot, acknowledgement, no-op, or expected-offset metadata is invalid.");
        }
    }

    internal static void ValidateReportShape(P28RawThresholdPatchReport report)
    {
        P28RawEditJson.ValidateObject(report);
        ValidateCommon(report.FormatVersion, report.Purpose, report.ModelId, report.ProfileId, report.Size,
            report.BaselineHash, report.ProfileDigest, report.BindingDigest, report.ChecksumStatus,
            report.FlashReadiness, report.FlashSafety);
        ValidateHash(report.OutputHash);
        ValidateDigest(report.PlanDigest);
        var slot = P28ThresholdLogic.ResolveSlot(report.SlotId);
        if (report.Offset != slot.Offset || !report.ReverseRestoresBaseline ||
            report.IsNoOp != (report.OldByte == report.NewByte) ||
            report.ChangedByteCount != (report.IsNoOp ? 0 : 1) ||
            !report.ChangedOffsets.SequenceEqual(report.IsNoOp ? Array.Empty<int>() : new[] { slot.Offset }) ||
            !report.Diff.SequenceEqual(report.IsNoOp ? Array.Empty<P28RawByteDiff>() :
                new[] { new P28RawByteDiff(slot.Offset, report.OldByte, report.NewByte) }))
        {
            throw new InvalidDataException("Report slot, diff, no-op, or reverse-proof metadata is invalid.");
        }
    }

    private static void ValidateBaseline(RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding)
    {
        ArgumentNullException.ThrowIfNull(baseline);
        ArgumentNullException.ThrowIfNull(profile);
        ArgumentNullException.ThrowIfNull(binding);
        baseline.ValidateExactSize(P28ExactBaselineBinding.RequiredSize);
        var validation = profile.Validate();
        if (!validation.IsValid)
        {
            throw new ProfileValidationException(validation.Errors);
        }

        if (profile.Id != P28ExactBaselineBinding.RequiredProfileId || profile.ExpectedSize != baseline.Size ||
            binding.FormatVersion != P28ExactBaselineBinding.CurrentFormatVersion ||
            binding.ModelId != P28CompactModel.ModelId || binding.ProfileId != profile.Id || binding.ExpectedSize != baseline.Size ||
            !string.Equals(binding.RomHash.Sha256, baseline.Hash.Sha256, StringComparison.OrdinalIgnoreCase) ||
            !string.Equals(binding.RomHash.Crc32, baseline.Hash.Crc32, StringComparison.OrdinalIgnoreCase) ||
            !string.Equals(binding.ProfileDigest, P28VtecInspector.ComputeProfileDigest(profile), StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException("An exact matching original research baseline, profile and model binding is required.");
        }
    }

    private static void ValidateCommon(
        string version, string purpose, string model, string profile, int size, RomHash hash,
        string profileDigest, string bindingDigest, ChecksumStatus checksum,
        FlashReadinessStatus readiness, FlashSafetyStatus safety)
    {
        if (version != FormatVersion || purpose != Purpose || model != P28CompactModel.ModelId ||
            profile != P28ExactBaselineBinding.RequiredProfileId || size != P28ExactBaselineBinding.RequiredSize ||
            checksum != ChecksumStatus.Unknown || readiness != FlashReadinessStatus.PcInspectionOnly ||
            safety != FlashSafetyStatus.NotFlashReady)
        {
            throw new InvalidDataException("Unsupported raw-edit version, scope, size, model, checksum or safety metadata.");
        }

        ValidateHash(hash);
        ValidateDigest(profileDigest);
        ValidateDigest(bindingDigest);
    }

    private static void ValidateHash(RomHash hash)
    {
        ArgumentNullException.ThrowIfNull(hash);
        ValidateDigest(hash.Sha256);
        if (hash.Crc32.Length != 8 || !hash.Crc32.All(Uri.IsHexDigit))
        {
            throw new InvalidDataException("Malformed CRC32.");
        }
    }

    private static void ValidateDigest(string digest)
    {
        if (digest.Length != 64 || !digest.All(Uri.IsHexDigit))
        {
            throw new InvalidDataException("Malformed SHA-256 digest.");
        }
    }

    private static P28RawThresholdPatchReport Measure(RomImage baseline, RomImage output, P28RawThresholdPlan plan)
    {
        output.ValidateExactSize(baseline.Size);
        var changed = new List<int>();
        var diff = new List<P28RawByteDiff>();
        for (var offset = 0; offset < baseline.Size; offset++)
        {
            if (baseline.Span[offset] != output.Span[offset])
            {
                changed.Add(offset);
                diff.Add(new P28RawByteDiff(offset, baseline.Span[offset], output.Span[offset]));
            }
        }

        if (!changed.SequenceEqual(plan.ExpectedChangedOffsets) ||
            baseline.Span[plan.Offset] != plan.ExpectedOldByte || output.Span[plan.Offset] != plan.NewByte)
        {
            throw new InvalidDataException("Full image diff or slot readback differs from the declared raw edit.");
        }

        var reversed = output.ToArray();
        reversed[plan.Offset] = plan.ExpectedOldByte;
        var reverseMatches = reversed.AsSpan().SequenceEqual(baseline.Span);
        if (!reverseMatches)
        {
            throw new InvalidDataException("In-memory reverse restoration did not reproduce the complete baseline.");
        }

        return new P28RawThresholdPatchReport(
            FormatVersion, Purpose, plan.ModelId, plan.ProfileId, baseline.Size, baseline.Hash, output.Hash,
            plan.ProfileDigest, plan.BindingDigest, ComputePlanDigest(plan), plan.SlotId, plan.Offset,
            plan.ExpectedOldByte, plan.NewByte, changed.AsReadOnly(), diff.AsReadOnly(), changed.Count,
            changed.Count == 0, reverseMatches,
            ComparePredicates(baseline, P28ThresholdLogic.ResolveSlot(plan.SlotId), output.Span[plan.Offset]),
            Evidence(), ChecksumStatus.Unknown, FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    private static P28PredicateImpact ComparePredicates(RomImage baseline, P28ThresholdSlot edited, byte newByte)
    {
        var oldByte = baseline.Span[edited.Offset];
        var rows = Enumerable.Range(0, 256).Select(code => new P28PredicateRow((byte)code,
            P28ThresholdLogic.Evaluate(oldByte, (byte)code), P28ThresholdLogic.Evaluate(newByte, (byte)code))).ToArray();
        var selections = new List<P28SlotSelectionProof>();
        foreach (var slot in P28ThresholdLogic.GetSlots())
        {
            var before = baseline.Span[slot.Offset];
            var after = slot.Id == edited.Id ? newByte : before;
            var unchanged = Enumerable.Range(0, 256).All(code =>
                P28ThresholdLogic.Evaluate(before, (byte)code) == P28ThresholdLogic.Evaluate(after, (byte)code));
            selections.Add(new P28SlotSelectionProof(slot.Id, 256, slot.Id == edited.Id, before == after, unchanged));
        }

        var clearOffset = P28ThresholdLogic.ThresholdOffset(edited.Context, edited.Pair, false);
        var setOffset = P28ThresholdLogic.ThresholdOffset(edited.Context, edited.Pair, true);
        return new P28PredicateImpact(
            "compactCode > selectedThreshold (unsigned byte)", false, 256, ReadOnly(rows),
            ReadOnly(rows.Where(row => row.Before != row.After).Select(row => (int)row.CompactCode).ToArray()),
            selections.AsReadOnly(), Pair(baseline.Span[clearOffset], baseline.Span[setOffset]),
            Pair(clearOffset == edited.Offset ? newByte : baseline.Span[clearOffset],
                setOffset == edited.Offset ? newByte : baseline.Span[setOffset]),
            "One-step comparisons use identical incoming state; subsequent trajectories may differ. Equal/reversed pairs are literal, never normalized or certified engine-safe.");
    }

    private static P28PairOrientation Pair(byte clear, byte set) => new(clear, set,
        clear == set ? "equal" : clear > set ? "prior-clear-greater-than-prior-set" : "prior-clear-less-than-prior-set");

    private static P28RawEditEvidence Evidence() => new(
        "Established scoped unsigned-byte predicate and neutral slot selection; file/predicate checks are not ECU validation.",
        "Partial established edge paths; raw inputs 234..3749 remain unresolved and EvaluateHypothesis remains conditional.",
        "Unresolved; no RPM conversion or inverse selection.", "Not run", "Not run", "Not run",
        "Unverified archive provenance; private hash binding is not factory authentication. Checksum is unknown and untouched; the derived file may fail the ECU's native integrity check.");

    internal static IReadOnlyList<P28ThresholdContextReport> BuildDerivedContexts(RomImage output) =>
        ReadOnly(P28ThresholdLogic.GetSlots().GroupBy(slot => slot.Context).Select(group =>
            new P28ThresholdContextReport($"context_{group.Key}", group.Key,
                P28ThresholdLogic.SelectContext(true) == group.Key, group.Min(slot => slot.Offset),
                ReadOnly(group.Select(slot => new P28ThresholdSlotReport(slot.Id, slot.Context, slot.Pair,
                    slot.PriorState, slot.Offset, output.Span[slot.Offset])).ToArray()))).ToArray());

    private static IReadOnlyList<T> ReadOnly<T>(T[] values) => Array.AsReadOnly(values);

    private static void RequireSame<T>(T actual, T expected, string message)
    {
        if (!string.Equals(P28RawEditJson.Serialize(actual, false), P28RawEditJson.Serialize(expected, false), StringComparison.Ordinal))
        {
            throw new InvalidDataException(message);
        }
    }

    private static bool InputProblem(Exception exception) => exception is
        ArgumentException or InvalidDataException or InvalidOperationException or JsonException or IOException or OverflowException;
}

/// <summary>Small closed-shape JSON reader, scoped only to these research artifacts.</summary>
internal static class P28RawEditJson
{
    public static string Serialize<T>(T value, bool indented) => JsonSerializer.Serialize(value, JsonDefaults.Create(indented));

    public static T Parse<T>(string json)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(json);
        using var document = JsonDocument.Parse(json);
        ValidateShape(document.RootElement, typeof(T));
        return JsonSerializer.Deserialize<T>(json, JsonDefaults.Create()) ?? throw new InvalidDataException("Empty raw-edit artifact.");
    }

    public static void ValidateObject<T>(T value)
    {
        ArgumentNullException.ThrowIfNull(value);
        using var document = JsonDocument.Parse(Serialize(value, false));
        ValidateShape(document.RootElement, typeof(T));
    }

    private static void ValidateShape(JsonElement element, Type type)
    {
        if (element.ValueKind == JsonValueKind.Null)
        {
            throw new InvalidDataException("Null raw-edit fields or array items are not allowed.");
        }

        if (type == typeof(string))
        {
            if (element.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(element.GetString()))
            {
                throw new InvalidDataException("Raw-edit string fields must be nonempty strings.");
            }
            return;
        }

        if (type == typeof(int) || type == typeof(byte))
        {
            if (element.ValueKind != JsonValueKind.Number || !element.TryGetInt32(out var number) ||
                (type == typeof(byte) && number is < 0 or > 255))
            {
                throw new InvalidDataException("Raw-edit numeric fields must be in-range integers.");
            }
            return;
        }

        if (type == typeof(bool))
        {
            if (element.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
            {
                throw new InvalidDataException("Raw-edit Boolean field required.");
            }
            return;
        }

        if (type.IsEnum)
        {
            if (element.ValueKind != JsonValueKind.String)
            {
                throw new InvalidDataException("Raw-edit enum must use its declared text form.");
            }
            return;
        }

        if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(IReadOnlyList<>))
        {
            if (element.ValueKind != JsonValueKind.Array)
            {
                throw new InvalidDataException("Raw-edit array field required.");
            }
            foreach (var item in element.EnumerateArray())
            {
                ValidateShape(item, type.GetGenericArguments()[0]);
            }
            return;
        }

        if (element.ValueKind != JsonValueKind.Object)
        {
            throw new InvalidDataException("Raw-edit object field required.");
        }
        var properties = type.GetProperties(BindingFlags.Public | BindingFlags.Instance)
            .Where(property => property.GetCustomAttribute<JsonIgnoreAttribute>() is null)
            .ToDictionary(property => JsonNamingPolicy.CamelCase.ConvertName(property.Name), StringComparer.Ordinal);
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in element.EnumerateObject())
        {
            if (!seen.Add(property.Name) || !properties.TryGetValue(property.Name, out var definition))
            {
                throw new InvalidDataException("Duplicate or unknown raw-edit property.");
            }
            ValidateShape(property.Value, definition.PropertyType);
        }
        if (seen.Count != properties.Count)
        {
            throw new InvalidDataException("Missing required raw-edit property.");
        }
    }
}
