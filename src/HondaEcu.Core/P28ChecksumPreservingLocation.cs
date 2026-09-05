using System.Security.Cryptography;
using System.Text;

namespace HondaEcu.Core;

public sealed record P28CompensationLocationPayload(
    string FormatVersion, string Purpose, string CandidateContractId, string DefinitionId,
    RomHash BaselineHash, string ProfileDigest, string BindingDigest, int Offset, byte OriginalByte,
    string EvidenceIdentity, string EvidenceScope, IReadOnlyList<string> VerifiedConsumers,
    IReadOnlyList<string> Limitations, bool EligibleForResearchExport,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
}

public sealed record P28CompensationLocationDocument(P28CompensationLocationPayload Payload, string SignatureBase64)
{
    public string ToJson(bool indented = true) => P28RawEditJson.Serialize(this, indented);
}

/// <summary>
/// Authentication of a particular reviewed scope, not proof that the signed
/// analysis is true, factory authentication, or hardware/flash authorization.
/// Only the pinned review-key verifier can construct this public capability.
/// </summary>
public sealed class VerifiedCompensationLocation
{
    private const string PublicKeySpki = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAERTiREDUXEoe2CRo0GK4PXiJug4sJFR46tMLHYaFH9Pr4dH8hcYSdFzJuNbXaHhQgePwpx8IEH0db/i0J9Q87mg==";
    public const string DocumentVersion = "1.0";
    public const string DocumentPurpose = "reviewed-pc-only-compensation-location";
    public const string CandidateContract = "p28-research-tail-byte-7fff-v1";
    internal P28CompensationLocationPayload Payload { get; }
    public string DefinitionId => Payload.DefinitionId;
    public string EvidenceIdentity => Payload.EvidenceIdentity;
    public string EvidenceScope => Payload.EvidenceScope;
    public int Offset => Payload.Offset;
    public byte OriginalByte => Payload.OriginalByte;
    public string DefinitionDigest { get; }
    public IReadOnlyList<string> VerifiedConsumers => Payload.VerifiedConsumers;
    public IReadOnlyList<string> Limitations => Payload.Limitations;

    private VerifiedCompensationLocation(P28CompensationLocationPayload payload)
    {
        Payload = payload with
        {
            VerifiedConsumers = Array.AsReadOnly(payload.VerifiedConsumers.ToArray()),
            Limitations = Array.AsReadOnly(payload.Limitations.ToArray()),
        };
        DefinitionDigest = HashUtilities.Sha256(Encoding.UTF8.GetBytes(Payload.ToJson(false)));
    }

    internal static VerifiedCompensationLocation Parse(string json)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(json);
        if (Encoding.UTF8.GetByteCount(json) > 65536) throw new InvalidDataException("Compensation definition exceeds 64 KiB.");
        var document = P28RawEditJson.Parse<P28CompensationLocationDocument>(json);
        var payload = document.Payload;
        if (payload.FormatVersion != DocumentVersion || payload.Purpose != DocumentPurpose ||
            payload.CandidateContractId != CandidateContract || payload.Offset != 0x7FFF ||
            !payload.EligibleForResearchExport || payload.FlashReadiness != FlashReadinessStatus.PcInspectionOnly ||
            payload.FlashSafety != FlashSafetyStatus.NotFlashReady || payload.VerifiedConsumers.Count == 0 || payload.Limitations.Count == 0 ||
            !Digest(payload.BaselineHash.Sha256) || !Digest(payload.ProfileDigest) || !Digest(payload.BindingDigest) ||
            payload.BaselineHash.Crc32.Length != 8 || !payload.BaselineHash.Crc32.All(Uri.IsHexDigit))
            throw new InvalidDataException("Unsupported, ineligible or malformed reviewed compensation definition.");
        byte[] signature;
        try { signature = Convert.FromBase64String(document.SignatureBase64); }
        catch (FormatException exception) { throw new InvalidDataException("Malformed compensation signature.", exception); }
        if (signature.Length != 64) throw new InvalidDataException("Compensation signature must be fixed IEEE P1363 P-256 length.");
        using var verifier = ECDsa.Create();
        verifier.ImportSubjectPublicKeyInfo(Convert.FromBase64String(PublicKeySpki), out _);
        if (!verifier.VerifyData(Encoding.UTF8.GetBytes(payload.ToJson(false)), signature, HashAlgorithmName.SHA256,
                DSASignatureFormat.IeeeP1363FixedFieldConcatenation))
            throw new InvalidDataException("Compensation definition is not authenticated by the pinned review key; a binding, digest or JSON eligibility claim is not authorization.");
        return new(payload);
    }

    private static bool Digest(string value) => value.Length == 64 && value.All(Uri.IsHexDigit);
}
