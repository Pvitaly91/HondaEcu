using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public enum P28BaselineBindingStatus
{
    NotProvided,
    Matched,
    Mismatched,
}

/// <summary>
/// Private, analyst-declared binding to one exact research input. This is deliberately separate
/// from public ROM identities and does not authenticate a factory ECU revision or provenance.
/// </summary>
public sealed record P28ExactBaselineBinding
{
    public const int CurrentFormatVersion = 1;
    public const string RequiredProfileId = "p28-304";
    public const int RequiredSize = 32768;

    public P28ExactBaselineBinding(
        int formatVersion,
        string modelId,
        string profileId,
        int expectedSize,
        RomHash romHash,
        string profileDigest)
    {
        if (formatVersion != CurrentFormatVersion)
        {
            throw new InvalidDataException($"P28 baseline binding formatVersion must be {CurrentFormatVersion}.");
        }

        if (!string.Equals(modelId, P28CompactModel.ModelId, StringComparison.Ordinal))
        {
            throw new InvalidDataException($"P28 baseline binding modelId must be '{P28CompactModel.ModelId}'.");
        }

        if (!string.Equals(profileId, RequiredProfileId, StringComparison.Ordinal))
        {
            throw new InvalidDataException($"P28 baseline binding profileId must be '{RequiredProfileId}'.");
        }

        if (expectedSize != RequiredSize)
        {
            throw new InvalidDataException($"P28 baseline binding expectedSize must be {RequiredSize}.");
        }

        ArgumentNullException.ThrowIfNull(romHash);
        ValidateHex(romHash.Sha256, 64, "romHash.sha256");
        ValidateHex(romHash.Crc32, 8, "romHash.crc32");
        ValidateHex(profileDigest, 64, "profileDigest");

        FormatVersion = formatVersion;
        ModelId = modelId;
        ProfileId = profileId;
        ExpectedSize = expectedSize;
        RomHash = new RomHash(romHash.Sha256.ToLowerInvariant(), romHash.Crc32.ToUpperInvariant());
        ProfileDigest = profileDigest.ToLowerInvariant();
    }

    public int FormatVersion { get; }

    public string ModelId { get; }

    public string ProfileId { get; }

    public int ExpectedSize { get; }

    public RomHash RomHash { get; }

    public string ProfileDigest { get; }

    public string ToJson(bool indented = true) =>
        JsonSerializer.Serialize(this, JsonDefaults.Create(indented));

    public static P28ExactBaselineBinding Load(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        return Parse(File.ReadAllText(path));
    }

    public static P28ExactBaselineBinding Parse(string json)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(json);
        using var document = JsonDocument.Parse(json);
        var root = document.RootElement;
        EnsureExactProperties(
            root,
            "P28 baseline binding",
            "formatVersion",
            "modelId",
            "profileId",
            "expectedSize",
            "romHash",
            "profileDigest");

        var hashElement = root.GetProperty("romHash");
        EnsureExactProperties(hashElement, "P28 baseline binding romHash", "sha256", "crc32");

        return new P28ExactBaselineBinding(
            RequiredInt(root, "formatVersion"),
            RequiredString(root, "modelId"),
            RequiredString(root, "profileId"),
            RequiredInt(root, "expectedSize"),
            new RomHash(RequiredString(hashElement, "sha256"), RequiredString(hashElement, "crc32")),
            RequiredString(root, "profileDigest"));
    }

    private static void EnsureExactProperties(JsonElement element, string role, params string[] required)
    {
        if (element.ValueKind != JsonValueKind.Object)
        {
            throw new InvalidDataException($"{role} must be a JSON object.");
        }

        var allowed = required.ToHashSet(StringComparer.Ordinal);
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in element.EnumerateObject())
        {
            if (!seen.Add(property.Name))
            {
                throw new InvalidDataException($"{role} contains duplicate property '{property.Name}'.");
            }

            if (!allowed.Contains(property.Name))
            {
                throw new InvalidDataException($"{role} contains unknown property '{property.Name}'.");
            }
        }

        var missing = required.FirstOrDefault(name => !seen.Contains(name));
        if (missing is not null)
        {
            throw new InvalidDataException($"{role} is missing required property '{missing}'.");
        }
    }

    private static string RequiredString(JsonElement element, string name)
    {
        var property = element.GetProperty(name);
        if (property.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(property.GetString()))
        {
            throw new InvalidDataException($"P28 baseline binding property '{name}' must be a non-empty string.");
        }

        return property.GetString()!;
    }

    private static int RequiredInt(JsonElement element, string name)
    {
        var property = element.GetProperty(name);
        if (property.ValueKind != JsonValueKind.Number || !property.TryGetInt32(out var value))
        {
            throw new InvalidDataException($"P28 baseline binding property '{name}' must be a 32-bit integer.");
        }

        return value;
    }

    private static void ValidateHex(string value, int length, string name)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Length != length || !value.All(Uri.IsHexDigit))
        {
            throw new InvalidDataException(
                $"P28 baseline binding {name} must contain exactly {length} hexadecimal characters.");
        }
    }
}

public sealed record P28InspectionInput(int Size, RomHash Hash);

public sealed record P28RawByte(int Offset, byte Value, string RawHex);

public sealed record P28RawWindow(int Offset, int Length, IReadOnlyList<P28RawByte> Bytes);

public sealed record P28BaselineBindingAssessment(
    bool Provided,
    P28BaselineBindingStatus Status,
    bool? RomHashMatches,
    bool? ProfileDigestMatches,
    IReadOnlyList<string> MismatchReasons,
    string Qualification);

public sealed record P28ThresholdSlotReport(
    string Id,
    int Context,
    int Pair,
    bool PriorState,
    int Offset,
    byte Threshold);

public sealed record P28ThresholdContextReport(
    string Id,
    int Context,
    bool SelectorData011EBit3,
    int BaseOffset,
    IReadOnlyList<P28ThresholdSlotReport> Slots);

public sealed record P28ThresholdStateContract(
    string CompactCodeSource,
    string Predicate,
    bool EqualityResult,
    bool RequiredData011EBit4,
    string RequiredDataPage,
    int RequiredDd,
    string GateTrueBehavior,
    string GateFalseBehavior);

public sealed record P28CompactDomainSet(
    bool Data0217Bit4,
    IReadOnlyList<P28CodeDomain> Domains);

public sealed record P28PhysicalRpmInterval(
    double Start,
    double End,
    bool StartInclusive,
    bool EndInclusive);

public sealed record P28VtecInspectionReport(
    string FormatVersion,
    string ReportKind,
    string ModelId,
    string ProfileId,
    string ProfileDigest,
    P28InspectionInput Input,
    RomIdentity PublicIdentity,
    bool ProfileAcknowledged,
    P28BaselineBindingAssessment BaselineBinding,
    string Scope,
    bool InterpretationApplied,
    P28RawWindow RawWindow,
    IReadOnlyList<P28ThresholdContextReport> Contexts,
    P28ThresholdStateContract? ThresholdStateContract,
    IReadOnlyList<P28CompactDomainSet> CompactDomains,
    bool PhysicalRpmAvailable,
    IReadOnlyList<P28PhysicalRpmInterval>? PhysicalRpmIntervals,
    IReadOnlyList<string> UnresolvedFindings,
    IReadOnlyList<string> Warnings,
    FlashReadinessStatus FlashReadiness,
    FlashSafetyStatus FlashSafety)
{
    public string ToJson(bool indented = true) =>
        JsonSerializer.Serialize(this, JsonDefaults.Create(indented));
}

/// <summary>
/// Read-only inspector for one exact private research baseline. Raw bytes remain available for
/// an unbound image, but revision-specific semantics require both a matching private binding and
/// explicit profile acknowledgement.
/// </summary>
public static class P28VtecInspector
{
    public const string ReportFormatVersion = "1.0";
    public const string ReportKind = "p28-vtec-threshold-inspection";

    private static readonly Lazy<IReadOnlyList<P28CompactDomainSet>> DomainSets = new(
        () => Array.AsReadOnly(new[]
        {
            new P28CompactDomainSet(false, P28CompactModel.GetAllDomains(false)),
            new P28CompactDomainSet(true, P28CompactModel.GetAllDomains(true)),
        }));

    public static string ComputeProfileDigest(RomProfile profile)
    {
        ArgumentNullException.ThrowIfNull(profile);
        var canonical = JsonSerializer.Serialize(profile, JsonDefaults.Options);
        return HashUtilities.Sha256(Encoding.UTF8.GetBytes(canonical));
    }

    public static P28VtecInspectionReport Inspect(
        RomImage image,
        RomProfile profile,
        IEnumerable<RomProfile> profiles,
        bool profileAcknowledged,
        P28ExactBaselineBinding? binding = null)
    {
        ArgumentNullException.ThrowIfNull(image);
        ArgumentNullException.ThrowIfNull(profile);
        ArgumentNullException.ThrowIfNull(profiles);
        if (!string.Equals(profile.Id, P28ExactBaselineBinding.RequiredProfileId, StringComparison.Ordinal) ||
            profile.ExpectedSize != P28ExactBaselineBinding.RequiredSize)
        {
            throw new InvalidOperationException(
                $"The {P28CompactModel.ModelId} inspector requires profile '{P28ExactBaselineBinding.RequiredProfileId}' " +
                $"with exact size {P28ExactBaselineBinding.RequiredSize}.");
        }

        image.ValidateExactSize(P28ExactBaselineBinding.RequiredSize, profile.Id);
        var profileList = profiles.ToArray();
        if (!profileList.Any(item => string.Equals(item.Id, profile.Id, StringComparison.OrdinalIgnoreCase)))
        {
            throw new InvalidOperationException("The selected P28 profile is not present in the supplied profile catalog.");
        }

        var publicIdentity = RomIdentifier.Identify(image, profileList);
        var profileDigest = ComputeProfileDigest(profile);
        var assessment = AssessBinding(image, profileDigest, binding);
        var interpretationApplied = assessment.Status == P28BaselineBindingStatus.Matched && profileAcknowledged;
        var rawWindow = ReadRawWindow(image);

        var contexts = interpretationApplied
            ? BuildContexts(rawWindow)
            : Array.Empty<P28ThresholdContextReport>();
        var stateContract = interpretationApplied ? BuildStateContract() : null;
        var domains = interpretationApplied ? DomainSets.Value : Array.Empty<P28CompactDomainSet>();

        var unresolved = new List<string>
        {
            "The producer of DATA 0x00C4 and its physical-RPM scale remain unresolved.",
            "The compact-code arithmetic path for raw inputs 234 through 3749 remains unresolved because the 16-bit ADD obj,A operation has not been independently established; any values for that interval are conditional hypothesis output, not verified ROM behavior.",
            "The reset/edge case with DATA 0x00C4 equal to 0xFFFF and DATA 0x0133 equal to zero is outside the modeled F(rawInput, DATA 0x0217.4) slice.",
            "The archive candidate's native factory revision and original ECU provenance remain unresolved.",
        };
        if (!interpretationApplied)
        {
            unresolved.Add("Revision-specific threshold, predicate, and compact-domain interpretation was not applied.");
        }

        var warnings = new List<string>
        {
            "A private exact-byte binding is an analyst declaration. A match proves only that these exact bytes were inspected; it does not authenticate a factory ECU revision or create a trusted public identity.",
            "The raw-to-compact model is partial: established edge branches are reported separately from conditional normal-path hypothesis output.",
            "This model represents a statically analyzed arithmetic slice; it is not original BIN execution, independent editor validation, emulator validation, or hardware validation.",
            "This report is read-only, PC-inspection-only, and not flash-ready.",
        };
        if (!publicIdentity.IsIdentified)
        {
            warnings.Add("The input is not identified by a trusted public hash or signature.");
        }

        if (assessment.Status == P28BaselineBindingStatus.NotProvided)
        {
            warnings.Add("No private exact-baseline binding was provided; only the neutral raw byte window is reported.");
        }
        else if (assessment.Status == P28BaselineBindingStatus.Mismatched)
        {
            warnings.Add("The private exact-baseline binding does not match the current input/profile; only the neutral raw byte window is reported.");
        }

        if (!profileAcknowledged)
        {
            warnings.Add("The selected profile was not explicitly acknowledged; --confirm-profile is required before revision-specific interpretation.");
        }

        return new P28VtecInspectionReport(
            ReportFormatVersion,
            ReportKind,
            P28CompactModel.ModelId,
            profile.Id,
            profileDigest,
            new P28InspectionInput(image.Size, image.Hash),
            publicIdentity,
            profileAcknowledged,
            assessment,
            interpretationApplied ? "exact-private-baseline-partial-raw-to-compact-research" : "raw-window-only",
            interpretationApplied,
            rawWindow,
            contexts,
            stateContract,
            domains,
            false,
            null,
            unresolved.AsReadOnly(),
            warnings.AsReadOnly(),
            FlashReadinessStatus.PcInspectionOnly,
            FlashSafetyStatus.NotFlashReady);
    }

    private static P28BaselineBindingAssessment AssessBinding(
        RomImage image,
        string profileDigest,
        P28ExactBaselineBinding? binding)
    {
        const string qualification =
            "Analyst-declared private exact-byte research binding; not factory authentication or a public trusted identity.";
        if (binding is null)
        {
            return new P28BaselineBindingAssessment(
                false,
                P28BaselineBindingStatus.NotProvided,
                null,
                null,
                Array.Empty<string>(),
                qualification);
        }

        var romMatches = HashEquals(image.Hash, binding.RomHash);
        var profileMatches = string.Equals(profileDigest, binding.ProfileDigest, StringComparison.OrdinalIgnoreCase);
        var reasons = new List<string>();
        if (!romMatches)
        {
            reasons.Add("rom-hash-mismatch");
        }

        if (!profileMatches)
        {
            reasons.Add("profile-digest-mismatch");
        }

        return new P28BaselineBindingAssessment(
            true,
            reasons.Count == 0 ? P28BaselineBindingStatus.Matched : P28BaselineBindingStatus.Mismatched,
            romMatches,
            profileMatches,
            reasons.AsReadOnly(),
            qualification);
    }

    private static bool HashEquals(RomHash left, RomHash right) =>
        string.Equals(left.Sha256, right.Sha256, StringComparison.OrdinalIgnoreCase) &&
        string.Equals(left.Crc32, right.Crc32, StringComparison.OrdinalIgnoreCase);

    private static P28RawWindow ReadRawWindow(RomImage image)
    {
        var bytes = image.Span.Slice(P28ThresholdLogic.BlockOffset, P28ThresholdLogic.BlockLength);
        var values = new P28RawByte[bytes.Length];
        for (var index = 0; index < bytes.Length; index++)
        {
            values[index] = new P28RawByte(
                P28ThresholdLogic.BlockOffset + index,
                bytes[index],
                bytes[index].ToString("X2", System.Globalization.CultureInfo.InvariantCulture));
        }

        return new P28RawWindow(
            P28ThresholdLogic.BlockOffset,
            P28ThresholdLogic.BlockLength,
            Array.AsReadOnly(values));
    }

    private static IReadOnlyList<P28ThresholdContextReport> BuildContexts(P28RawWindow rawWindow)
    {
        var rawByOffset = rawWindow.Bytes.ToDictionary(item => item.Offset, item => item.Value);
        var contexts = new List<P28ThresholdContextReport>();
        foreach (var selector in new[] { true, false })
        {
            var context = P28ThresholdLogic.SelectContext(selector);
            var slots = new List<P28ThresholdSlotReport>();
            for (var pair = 0; pair < 2; pair++)
            {
                // Prior-state true selects the even byte; false selects the following odd byte.
                foreach (var priorState in new[] { true, false })
                {
                    var offset = P28ThresholdLogic.ThresholdOffset(context, pair, priorState);
                    slots.Add(new P28ThresholdSlotReport(
                        $"context_{context}.pair_{pair}.state_{(priorState ? 1 : 0)}_threshold",
                        context,
                        pair,
                        priorState,
                        offset,
                        rawByOffset[offset]));
                }
            }

            contexts.Add(new P28ThresholdContextReport(
                $"context_{context}",
                context,
                selector,
                P28ThresholdLogic.BlockOffset + (context * 4),
                slots.AsReadOnly()));
        }

        return contexts.AsReadOnly();
    }

    private static P28ThresholdStateContract BuildStateContract() =>
        new(
            "DATA 0x0133 (unsigned byte compact code)",
            "compactCode > threshold (unsigned byte comparison)",
            P28ThresholdLogic.Evaluate(0x80, 0x80),
            true,
            "0x0100",
            0,
            "The selected prior-state bit is updated to the predicate result.",
            "No threshold-state update occurs when the gate is false.");
}
