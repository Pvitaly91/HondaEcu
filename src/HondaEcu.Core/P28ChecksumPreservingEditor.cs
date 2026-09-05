using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

/// <summary>
/// A narrow, two-change composition over unchanged M1c planning. No generic
/// checksum repair, public arbitrary-offset authorization, writer or native-execution claim.
/// </summary>
public static class P28ChecksumPreservingEditor
{
    public const string FormatVersion = "1.0";
    public const string Purpose = "pc-only-checksum-preserving-threshold-composition";
    public const string FormulaId = "old-byte-minus-intermediate-residue-modulo-256";
    public const byte SyntheticThresholdValue = 40;

    /// <summary>Pure byte arithmetic only; it grants no location or ROM authority.</summary>
    public static byte ComputeCompensation(byte oldByte, byte intermediateResidue) =>
        unchecked((byte)(oldByte - intermediateResidue));

    public static string ComputePlanDigest(P28ChecksumPreservingPlan plan) =>
        HashUtilities.Sha256(Encoding.UTF8.GetBytes(plan.ToJson(false)));

    public static VerifiedCompensationLocation ParseLocation(string json) => VerifiedCompensationLocation.Parse(json);
    public static VerifiedCompensationLocation LoadLocation(string path)
    {
        using var input = File.OpenRead(path);
        var bytes = new byte[65537];
        var count = 0;
        while (count < bytes.Length)
        {
            var read = input.Read(bytes, count, bytes.Length - count);
            if (read == 0) break;
            count += read;
        }
        if (count > 65536) throw new InvalidDataException("Compensation definition exceeds 64 KiB.");
        return ParseLocation(Encoding.UTF8.GetString(bytes, 0, count).TrimStart('\uFEFF'));
    }

    public static P28CompensationAvailability GetAvailability(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged, VerifiedCompensationLocation? location = null)
    {
        const string scope = "Exact original research baseline with enabled/unaltered native checksum plus a separately reviewed non-interference definition; not factory authentication or ECU safety.";
        P28CompensationAvailability Unavailable(string status, string reason) =>
            new(status, false, null, null, reason, scope, FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
        try
        {
            P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, acknowledged);
            var arithmetic = P28NativeChecksumArithmetic.Calculate(baseline);
            if (!arithmetic.ResidueMatches) return Unavailable("rejected-nonzero-parent", "The original baseline has nonzero residue; this workflow must not conceal unknown changes.");
            var code = P28ChecksumCodeGuard.Assess(baseline);
            if (!code.ContractRecognized || !code.GateEnabled)
                return Unavailable("rejected-checksum-contract", $"Native checksum is unsupported, altered or disabled: {string.Join("; ", code.Issues)}");
            if (location is null) return Unavailable("unresolved-compensation-location", P28ChecksumPreservingDefinitions.UnavailableReason);
            var payload = location.Payload;
            if (payload.BaselineHash != baseline.Hash || payload.ProfileDigest != P28VtecInspector.ComputeProfileDigest(profile) ||
                payload.BindingDigest != P28RawThresholdEditor.ComputeBindingDigest(binding) || baseline.Span[payload.Offset] != payload.OriginalByte)
                return Unavailable("rejected-stale-compensation-definition", "The authenticated definition does not bind this exact original baseline/profile/binding or original compensation byte.");
            return new("reviewed-scope-available", true, location.DefinitionId, location.Offset,
                "Authenticated manual-review definition matches the exact original input. Signature authenticates the recorded audit, not its truth, factory provenance or ECU safety.",
                location.EvidenceScope, FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
        }
        catch (Exception exception) when (InputProblem(exception))
        {
            return Unavailable("rejected-original-binding", exception.Message);
        }
    }

    public static P28ChecksumPreservingPlan CreatePlan(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged,
        string slotId, int rawValue, VerifiedCompensationLocation? location = null)
    {
        var definition = P28ChecksumPreservingDefinitions.Resolve(baseline, profile, binding, acknowledged, location);
        return CreatePlanCore(baseline, profile, binding, acknowledged, slotId, rawValue, definition);
    }

    public static P28ChecksumPreservingPreview Apply(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, P28ChecksumPreservingPlan plan, VerifiedCompensationLocation? location = null)
    {
        ArgumentNullException.ThrowIfNull(plan);
        var definition = P28ChecksumPreservingDefinitions.Resolve(baseline, profile, binding, plan.ThresholdPlan.ProfileAcknowledged, location);
        return ApplyCore(baseline, profile, binding, plan, definition);
    }

    public static P28ChecksumPreservingVerification Verify(
        RomImage output, RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28ChecksumPreservingPlan plan, P28ChecksumPreservingReport report, VerifiedCompensationLocation? location = null) =>
        VerifyCore(output, baseline, profile, binding, plan, report, synthetic: false, location);

    public static P28VerifiedChecksumComposition Admit(
        RomImage output, RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28ChecksumPreservingPlan plan, P28ChecksumPreservingReport report, VerifiedCompensationLocation location)
    {
        var verification = Verify(output, baseline, profile, binding, plan, report, location);
        if (!verification.IsValid || plan.SyntheticOnly)
            throw new InvalidDataException($"Composed child admission refused: {string.Join("; ", verification.Issues.Select(issue => issue.Message))}");
        return new(baseline, profile, binding, output, plan, report, location);
    }

    public static P28ChecksumPreservingInspectionReport InspectDerived(P28VerifiedChecksumComposition composition)
    {
        ValidateAdmittedChild(composition, composition.Baseline, composition.Profile, composition.Binding, composition.Image);
        var verification = Verify(composition.Image, composition.Baseline, composition.Profile, composition.Binding,
            composition.Plan, composition.Report, composition.Location);
        var inspection = P28VtecInspector.Inspect(composition.Image, composition.Profile, [composition.Profile], true, composition.Binding);
        return new(verification, inspection, P28RawThresholdEditor.BuildDerivedContexts(composition.Image),
            false, FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    internal static void ValidateAdmittedChild(P28VerifiedChecksumComposition composition, RomImage baseline,
        RomProfile profile, P28ExactBaselineBinding binding, RomImage? output)
    {
        ArgumentNullException.ThrowIfNull(composition);
        if (output is null || !output.Span.SequenceEqual(composition.Image.Span) ||
            !baseline.Span.SequenceEqual(composition.Baseline.Span) ||
            !Verify(output, baseline, profile, binding, composition.Plan, composition.Report, composition.Location).IsValid)
            throw new InvalidDataException("The composed child does not reproduce from this exact original parent, reviewed definition and complete composition lineage.");
    }

    /// <summary>Fixed invented data only; does not admit any caller-supplied ROM.</summary>
    public static P28ChecksumPreservingPreview CreateSyntheticPreview(string slotId, int rawValue)
    {
        var fixture = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var definition = P28ChecksumPreservingDefinitions.ResolveSynthetic(fixture.Baseline, fixture.Profile, fixture.Binding);
        var plan = CreatePlanCore(fixture.Baseline, fixture.Profile, fixture.Binding, true, slotId, rawValue, definition);
        return ApplyCore(fixture.Baseline, fixture.Profile, fixture.Binding, plan, definition);
    }

    internal static P28ChecksumPreservingPlan CreateSyntheticPlan(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged, string slotId, int rawValue) =>
        CreatePlanCore(baseline, profile, binding, acknowledged, slotId, rawValue,
            P28ChecksumPreservingDefinitions.ResolveSynthetic(baseline, profile, binding));

    internal static P28ChecksumPreservingPreview ApplySynthetic(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, P28ChecksumPreservingPlan plan) =>
        ApplyCore(baseline, profile, binding, plan, P28ChecksumPreservingDefinitions.ResolveSynthetic(baseline, profile, binding));

    internal static P28ChecksumPreservingVerification VerifySynthetic(
        RomImage output, RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28ChecksumPreservingPlan plan, P28ChecksumPreservingReport report) =>
        VerifyCore(output, baseline, profile, binding, plan, report, synthetic: true);

    private static P28ChecksumPreservingPlan CreatePlanCore(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged,
        string slotId, int rawValue, P28VerifiedCompensationLocation definition)
    {
        ValidateDefinition(baseline, profile, binding, definition);
        var thresholdPlan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, acknowledged, slotId, rawValue);
        var intermediate = P28RawThresholdEditor.Apply(baseline, profile, binding, thresholdPlan);
        var initial = P28NativeChecksumArithmetic.Calculate(baseline).ComputedResult;
        if (initial != 0) throw new InvalidDataException("Checksum-preserving composition requires an unchanged zero-residue original parent.");
        var residue = P28NativeChecksumArithmetic.Calculate(intermediate.Image).ComputedResult;
        var compensation = new P28ComputedCompensation(definition.Offset, definition.OriginalByte,
            thresholdPlan.IsNoOp ? definition.OriginalByte : ComputeCompensation(definition.OriginalByte, residue), FormulaId);
        var final = intermediate.Image.CreateModifiedCopy([new BytePatch(compensation.Offset, new[] { compensation.NewByte })]);
        var finalResidue = P28NativeChecksumArithmetic.Calculate(final).ComputedResult;
        if (finalResidue != 0) throw new InvalidDataException("The computed composition did not preserve zero residue.");
        var expectedDiff = thresholdPlan.IsNoOp ? Array.Empty<P28RawByteDiff>() : new[]
        {
            new P28RawByteDiff(thresholdPlan.Offset, thresholdPlan.ExpectedOldByte, thresholdPlan.NewByte),
            new P28RawByteDiff(compensation.Offset, compensation.OldByte, compensation.NewByte),
        }.OrderBy(item => item.Offset).ToArray();
        return new(FormatVersion, Purpose, definition.SyntheticOnly, baseline.Hash, thresholdPlan.ProfileDigest, thresholdPlan.BindingDigest,
            thresholdPlan, definition.Id, definition.DefinitionDigest, definition.EvidenceIdentity, definition.EvidenceScope, compensation,
            Array.AsReadOnly(expectedDiff), thresholdPlan.IsNoOp, initial, residue, finalResidue,
            P28NativeChecksumArithmetic.Contract.Id, ChecksumStatus.Unknown, NativeChecksumExecutionStatus.NotRun,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    private static P28ChecksumPreservingPreview ApplyCore(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28ChecksumPreservingPlan plan, P28VerifiedCompensationLocation definition)
    {
        ValidatePlanShape(plan);
        var expected = CreatePlanCore(baseline, profile, binding, plan.ThresholdPlan.ProfileAcknowledged,
            plan.ThresholdPlan.SlotId, plan.ThresholdPlan.NewByte, definition);
        RequireSame(plan, expected, "Composition plan does not reproduce from the original parent and reviewed definition.");
        var intermediate = P28RawThresholdEditor.Apply(baseline, profile, binding, expected.ThresholdPlan);
        var image = intermediate.Image.CreateModifiedCopy([new BytePatch(definition.Offset, new[] { expected.Compensation.NewByte })]);
        return new(expected, intermediate.Image, image, Measure(baseline, intermediate.Image, image, expected));
    }

    private static P28ChecksumPreservingVerification VerifyCore(
        RomImage output, RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        P28ChecksumPreservingPlan plan, P28ChecksumPreservingReport report, bool synthetic, VerifiedCompensationLocation? location = null)
    {
        ArgumentNullException.ThrowIfNull(output);
        ArgumentNullException.ThrowIfNull(baseline);
        var issues = new List<VerificationIssue>();
        var reverse = false;
        var behavior = false;
        try
        {
            ValidatePlanShape(plan);
            ValidateReportShape(report);
            var expected = synthetic ? ApplySynthetic(baseline, profile, binding, plan) : Apply(baseline, profile, binding, plan, location);
            var measured = Measure(baseline, expected.Intermediate, output, expected.Plan);
            reverse = measured.ReverseRestoresBaseline;
            behavior = measured.ThresholdOnlyBehaviorPreserved;
            RequireSame(measured, expected.Report, "Complete output bytes differ from the exact reproduced composition.");
            RequireSame(report, measured, "Composition report differs from independently measured bytes and evidence.");
        }
        catch (Exception exception) when (InputProblem(exception))
        {
            issues.Add(new("checksum-composition-invalid", exception.Message));
        }
        return new(issues.Count == 0, issues.AsReadOnly(), baseline.Hash, output.Hash, reverse, behavior,
            synthetic ? P28ChecksumPreservingDefinitions.SyntheticScope : location?.EvidenceScope ?? P28ChecksumPreservingDefinitions.UnavailableReason,
            ChecksumStatus.Unknown, NativeChecksumExecutionStatus.NotRun, FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    private static P28ChecksumPreservingReport Measure(
        RomImage baseline, RomImage intermediate, RomImage output, P28ChecksumPreservingPlan plan)
    {
        output.ValidateExactSize(baseline.Size);
        var diff = new List<P28RawByteDiff>();
        for (var offset = 0; offset < baseline.Size; offset++)
            if (baseline.Span[offset] != output.Span[offset]) diff.Add(new(offset, baseline.Span[offset], output.Span[offset]));
        if (!diff.SequenceEqual(plan.ExpectedDiff)) throw new InvalidDataException("Full output diff differs from exactly the declared threshold and computed compensation.");
        var reverse = output.ToArray();
        reverse[plan.ThresholdPlan.Offset] = plan.ThresholdPlan.ExpectedOldByte;
        reverse[plan.Compensation.Offset] = plan.Compensation.OldByte;
        var reverseMatches = reverse.AsSpan().SequenceEqual(baseline.Span);
        if (!reverseMatches) throw new InvalidDataException("Restoring the two old bytes did not reproduce the full original baseline.");
        // Reuse the established threshold block, not checksum-zero as a behavior proof.
        var preserved = intermediate.Span.Slice(P28ThresholdLogic.BlockOffset, P28ThresholdLogic.BlockLength)
            .SequenceEqual(output.Span.Slice(P28ThresholdLogic.BlockOffset, P28ThresholdLogic.BlockLength));
        if (!preserved) throw new InvalidDataException("Compensation changed another active threshold byte.");
        var final = P28NativeChecksumArithmetic.Calculate(output).ComputedResult;
        if (final != 0) throw new InvalidDataException("Full output arithmetic has nonzero residue.");
        return new(FormatVersion, Purpose, plan.SyntheticOnly, baseline.Hash, intermediate.Hash, output.Hash,
            plan.ProfileDigest, plan.BindingDigest, ComputePlanDigest(plan), plan.CompensationDefinitionId, plan.CompensationDefinitionDigest,
            plan.CompensationEvidenceIdentity, plan.EvidenceScope, diff.AsReadOnly(), diff.Count, diff.Count == 0,
            P28NativeChecksumArithmetic.Calculate(baseline).ComputedResult,
            P28NativeChecksumArithmetic.Calculate(intermediate).ComputedResult, final, reverseMatches, preserved,
            plan.ThresholdPlan.PredicateImpact, plan.ChecksumContractId, ChecksumStatus.Unknown, NativeChecksumExecutionStatus.NotRun,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    private static void ValidateDefinition(RomImage baseline, RomProfile profile,
        P28ExactBaselineBinding binding, P28VerifiedCompensationLocation definition)
    {
        // Rebind even a non-deserializable capability on every use.
        var expected = definition.SyntheticOnly ? P28ChecksumPreservingDefinitions.ResolveSynthetic(baseline, profile, binding) :
            P28ChecksumPreservingDefinitions.Resolve(baseline, profile, binding, true, definition.Location);
        if (definition != expected) throw new InvalidDataException("Unrecognized or stale compensation definition.");
        ValidateOffset(definition.Offset);
        if (baseline.Span[definition.Offset] != definition.OriginalByte)
            throw new InvalidDataException("Compensation old byte differs from the reviewed definition.");
    }

    internal static void ValidatePlanShape(P28ChecksumPreservingPlan plan)
    {
        P28RawEditJson.ValidateObject(plan);
        ValidateCommon(plan.FormatVersion, plan.Purpose, plan.SyntheticOnly, plan.ChecksumContractId,
            plan.NativeChecksumStatus, plan.ExecutionStatus, plan.FlashReadiness, plan.FlashSafety);
        P28RawThresholdEditor.ValidatePlanShape(plan.ThresholdPlan);
        ValidateOffset(plan.Compensation.Offset);
        if (plan.Compensation.FormulaId != FormulaId || plan.BaselineResidue != 0 || plan.FinalResidue != 0 ||
            !plan.SyntheticOnly && plan.Compensation.Offset != 0x7FFF ||
            plan.SyntheticOnly != (plan.CompensationDefinitionId == P28ChecksumPreservingDefinitions.SyntheticId) ||
            plan.IsNoOp != plan.ThresholdPlan.IsNoOp || plan.BaselineHash != plan.ThresholdPlan.BaselineHash ||
            plan.ProfileDigest != plan.ThresholdPlan.ProfileDigest || plan.BindingDigest != plan.ThresholdPlan.BindingDigest ||
            plan.Compensation.NewByte != ComputeCompensation(plan.Compensation.OldByte, plan.IntermediateResidue) ||
            plan.IsNoOp != (plan.IntermediateResidue == 0) ||
            plan.CompensationDefinitionDigest.Length != 64 || !plan.CompensationDefinitionDigest.All(Uri.IsHexDigit) ||
            plan.SyntheticOnly && (plan.CompensationDefinitionId != P28ChecksumPreservingDefinitions.SyntheticId ||
                plan.CompensationEvidenceIdentity != P28ChecksumPreservingDefinitions.SyntheticEvidenceId ||
                plan.EvidenceScope != P28ChecksumPreservingDefinitions.SyntheticScope))
            throw new InvalidDataException("Unsupported or inconsistent composition metadata.");
        var expected = plan.IsNoOp ? Array.Empty<P28RawByteDiff>() : new[]
        {
            new P28RawByteDiff(plan.ThresholdPlan.Offset, plan.ThresholdPlan.ExpectedOldByte, plan.ThresholdPlan.NewByte),
            new P28RawByteDiff(plan.Compensation.Offset, plan.Compensation.OldByte, plan.Compensation.NewByte),
        }.OrderBy(item => item.Offset).ToArray();
        if (!plan.ExpectedDiff.SequenceEqual(expected)) throw new InvalidDataException("Composition must describe exactly zero or two distinct byte changes.");
    }

    internal static void ValidateReportShape(P28ChecksumPreservingReport report)
    {
        P28RawEditJson.ValidateObject(report);
        ValidateCommon(report.FormatVersion, report.Purpose, report.SyntheticOnly, report.ChecksumContractId,
            report.NativeChecksumStatus, report.ExecutionStatus, report.FlashReadiness, report.FlashSafety);
        foreach (var hash in new[] { report.BaselineHash, report.IntermediateHash, report.OutputHash })
            if (!IsDigest(hash.Sha256) || hash.Crc32.Length != 8 || !hash.Crc32.All(Uri.IsHexDigit))
                throw new InvalidDataException("Malformed composition report image identity.");
        if (new[] { report.ProfileDigest, report.BindingDigest, report.PlanDigest, report.CompensationDefinitionDigest }.Any(value => !IsDigest(value)))
            throw new InvalidDataException("Malformed composition report artifact digest.");
        if (report.BaselineResidue != 0 || report.FinalResidue != 0 || !report.ReverseRestoresBaseline ||
            report.SyntheticOnly != (report.CompensationDefinitionId == P28ChecksumPreservingDefinitions.SyntheticId) ||
            report.IsNoOp != (report.IntermediateResidue == 0) ||
            !report.ThresholdOnlyBehaviorPreserved || report.ChangedByteCount != (report.IsNoOp ? 0 : 2) ||
            report.Diff.Count != report.ChangedByteCount || report.Diff.Any(item => item.OldByte == item.NewByte || item.Offset is < 0 or >= 32768) ||
            !report.Diff.Select(item => item.Offset).SequenceEqual(report.Diff.Select(item => item.Offset).Distinct().Order()))
            throw new InvalidDataException("Invalid composition report diff, residue, no-op or reverse proof.");
    }

    private static void ValidateCommon(string version, string purpose, bool synthetic, string contract,
        ChecksumStatus checksum, NativeChecksumExecutionStatus execution, FlashReadinessStatus readiness, FlashSafetyStatus safety)
    {
        if (version != FormatVersion || purpose != Purpose || contract != P28NativeChecksumArithmetic.Contract.Id ||
            checksum != ChecksumStatus.Unknown || execution != NativeChecksumExecutionStatus.NotRun ||
            readiness != FlashReadinessStatus.PcInspectionOnly || safety != FlashSafetyStatus.NotFlashReady)
            throw new InvalidDataException("Unsupported composition version, scope, execution or safety metadata.");
    }

    private static void ValidateOffset(int offset)
    {
        if (offset is < 0x40 or >= P28NativeChecksumArithmetic.RomSize ||
            offset >= 0x2B70 && offset < 0x2BB6 || offset == P28NativeChecksumArithmetic.GateOffset ||
            P28ThresholdLogic.GetSlots().Any(slot => slot.Offset == offset))
            throw new InvalidDataException("Compensation overlaps a vector, checksum code/gate, active threshold or invalid address.");
    }

    private static void RequireSame<T>(T actual, T expected, string message)
    {
        if (P28RawEditJson.Serialize(actual, false) != P28RawEditJson.Serialize(expected, false)) throw new InvalidDataException(message);
    }
    private static bool IsDigest(string value) => value.Length == 64 && value.All(Uri.IsHexDigit);
    private static bool InputProblem(Exception exception) => exception is ArgumentException or InvalidDataException or
        InvalidOperationException or JsonException or IOException or OverflowException;
}
