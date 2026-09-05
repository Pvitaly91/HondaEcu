using System.Text.Json;

namespace HondaEcu.Core;

/// <summary>Explicit compatibility inventory, not executable attestation or a hardware trust anchor.</summary>
internal static class SliceRunnerIdentity
{
    internal const string CurrentVersion = "0.2.0";
    private static readonly string[] LegacyFixes =
    [
        "word-ror-through-carry-preserves-noncarry-flags", "load-zero-flag-and-dd-contract",
        "word-srl-preserves-noncarry-flags", "bit-operands-use-byte-access",
    ];
    private static readonly string[] CurrentFixes =
    [
        .. LegacyFixes, "clr-accumulator-zero-flag", "jrnz-dpl-byte-count", "adcb-r0-immediate-half-carry",
        "inc-x1-half-carry", "indexed-alternate-immediate-displacement", "word-data-access-alignment",
    ];

    internal static string[] Validate(JsonElement root, string operation)
    {
        var version = root.GetProperty("runnerVersion").GetString();
        if (root.GetProperty("protocolVersion").GetInt32() != 1 || root.GetProperty("operation").GetString() != operation ||
            root.GetProperty("upstreamCommit").GetString() != P28ByteExecutionValidator.UpstreamCommit ||
            version is not ("0.1.0" or CurrentVersion) || operation == "producerBatch" && version != CurrentVersion)
        {
            throw new SliceProcessException(SliceProcessFailure.Protocol,
                "Runner version, operation or protocol differs from the audited compatibility inventory.");
        }
        var expected = version == "0.1.0" ? LegacyFixes : CurrentFixes;
        var fixes = root.GetProperty("localSemanticFixes").EnumerateArray().Select(item => item.GetString()!).ToArray();
        if (!fixes.Order(StringComparer.Ordinal).SequenceEqual(expected.Order(StringComparer.Ordinal)))
        {
            throw new SliceProcessException(SliceProcessFailure.Protocol, "Runner semantic fixes differ from its audited version.");
        }
        return fixes;
    }
}
