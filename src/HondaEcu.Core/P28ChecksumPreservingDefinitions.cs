namespace HondaEcu.Core;

/// <summary>
/// Reviewed code owns authority. No external offset, JSON status, document digest,
/// checkbox, or newly created binding can populate this inventory.
/// </summary>
internal static class P28ChecksumPreservingDefinitions
{
    internal const int SyntheticOffset = 0x7000;
    internal const byte SyntheticOldByte = 192;
    internal const string SyntheticId = "invented-fixed-layout-compensation-v1";
    internal const string SyntheticEvidenceId = "synthetic-definition-source-v1";
    internal const string SyntheticScope = "Fixed invented fixture only; no Honda compensation location, native checksum evidence, machine execution or export authority.";
    internal const string UnavailableReason = "No authenticated reviewed CompensationLocation was supplied for this exact original baseline/profile/binding. A missing definition is not proof that a candidate is unused; no arbitrary offset, checkbox, JSON eligibility claim or zero residue can replace the reviewed authorization.";

    internal static P28VerifiedCompensationLocation Resolve(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool acknowledged, VerifiedCompensationLocation? location = null)
    {
        var availability = P28ChecksumPreservingEditor.GetAvailability(baseline, profile, binding, acknowledged, location);
        if (!availability.IsAvailable || location is null) throw new InvalidDataException(availability.Reason);
        return new(location.DefinitionId, location.DefinitionDigest, location.EvidenceIdentity, location.EvidenceScope,
            location.Offset, location.OriginalByte, baseline.Hash, P28VtecInspector.ComputeProfileDigest(profile),
            P28RawThresholdEditor.ComputeBindingDigest(binding), false, location);
    }

    internal static (RomImage Baseline, RomProfile Profile, P28ExactBaselineBinding Binding) SyntheticFixture()
    {
        var bytes = new byte[P28NativeChecksumArithmetic.RomSize];
        foreach (var slot in P28ThresholdLogic.GetSlots()) bytes[slot.Offset] = P28ChecksumPreservingEditor.SyntheticThresholdValue;
        // Eight invented bytes of 40 plus 192 sum to 512. This is a constructed
        // arithmetic fixture, not bytes translated from a native checksum routine.
        bytes[SyntheticOffset] = SyntheticOldByte;
        var baseline = RomImage.FromBytes(bytes);
        var profile = new RomProfile("p28-304", "Invented checksum composition fixture", "Synthetic only, not a native Honda ROM", 32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, baseline.Size,
            baseline.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        return (baseline, profile, binding);
    }

    internal static P28VerifiedCompensationLocation ResolveSynthetic(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding)
    {
        var fixedFixture = SyntheticFixture();
        if (!baseline.Span.SequenceEqual(fixedFixture.Baseline.Span) ||
            P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(fixedFixture.Profile) ||
            P28RawThresholdEditor.ComputeBindingDigest(binding) != P28RawThresholdEditor.ComputeBindingDigest(fixedFixture.Binding))
            throw new InvalidDataException("Synthetic authority applies only to the complete fixed invented fixture and its exact profile/binding.");
        return new P28VerifiedCompensationLocation(SyntheticId, HashUtilities.Sha256(System.Text.Encoding.UTF8.GetBytes(SyntheticEvidenceId)), SyntheticEvidenceId, SyntheticScope,
            SyntheticOffset, SyntheticOldByte, baseline.Hash, P28VtecInspector.ComputeProfileDigest(profile),
            P28RawThresholdEditor.ComputeBindingDigest(binding), true, null);
    }
}

/// <summary>Internal, immutable capability; serialized plan metadata never constructs this.</summary>
internal sealed record P28VerifiedCompensationLocation(
    string Id, string DefinitionDigest, string EvidenceIdentity, string EvidenceScope, int Offset, byte OriginalByte,
    RomHash BaselineHash, string ProfileDigest, string BindingDigest, bool SyntheticOnly, VerifiedCompensationLocation? Location);
