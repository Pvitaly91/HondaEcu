using System.Text.Json;

namespace HondaEcu.Core;

/// <summary>Explicit compatibility inventory, not executable attestation or a hardware trust anchor.</summary>
internal static class SliceRunnerIdentity
{
    internal const string CurrentVersion = "0.25.0";
    internal const string PostStoreVersion = "0.24.0";
    internal const string AdaptiveFuelVersion = "0.23.0";
    internal const string LimiterFuelVersion = "0.22.0";
    internal const string FuelFactorVersion = "0.21.0";
    internal const string FuelAdditiveVersion = "0.20.0";
    internal const string FuelCalculationVersion = "0.19.0";
    internal const string MetadataCorrectionVersion = "0.18.0";
    internal const string LegacyCorrectionVersion = "0.17.0";
    internal const string SharedVersion = "0.16.0";
    internal const string PreviousVersion = "0.14.0";
    internal const string SelectorVersion = "0.15.0";
    private static readonly string[] LegacyFixes =
    [
        "word-ror-through-carry-preserves-noncarry-flags", "load-zero-flag-and-dd-contract",
        "word-srl-preserves-noncarry-flags", "bit-operands-use-byte-access",
    ];
    private static readonly string[] ProducerFixes =
    [
        .. LegacyFixes, "clr-accumulator-zero-flag", "jrnz-dpl-byte-count", "adcb-r0-immediate-half-carry",
        "inc-x1-half-carry", "indexed-alternate-immediate-displacement", "word-data-access-alignment",
    ];
    private static readonly string[] ChecksumFixes =
    [
        .. ProducerFixes, "byte-add-direct-accumulator-half-carry", "byte-add-r0-accumulator-half-carry", "inc-indexed-x2-half-carry",
    ];
    private static readonly string[] AcquisitionFixes =
    [
        .. ChecksumFixes, "word-sub-direct-updates-half-borrow", "byte-inc-direct-updates-half-carry",
        "byte-sll-accumulator-preserves-noncarry-flags",
    ];
    private static readonly string[] CurrentFixes =
    [
        .. AcquisitionFixes, "byte-clear-accumulator-zero-flag", "stateful-exact-byte-add-sub-half-carry",
        "increment-dp-half-carry", "decrement-indexed-x1-byte-half-borrow",
    ];

    internal static string[] Validate(JsonElement root, string operation)
    {
        var version = root.GetProperty("runnerVersion").GetString();
        if (version == MetadataCorrectionVersion && operation is not ("fuelCalculationChain" or "fuelAdditiveCorrectionChain" or "fuelFactorProductionChain"))
            version = FuelCalculationVersion;
        // M2j changes only the correction capability disclosure/validation.
        // Other operations retain the exact 0.17.0 semantic-fix inventory.
        if (version == LegacyCorrectionVersion && operation is not ("ignitionCorrectionChain" or "fuelCalculationChain" or "fuelAdditiveCorrectionChain" or "fuelFactorProductionChain"))
            version = FuelCalculationVersion;
        if (root.GetProperty("protocolVersion").GetInt32() != 1 || root.GetProperty("operation").GetString() != operation ||
            root.GetProperty("upstreamCommit").GetString() != P28ByteExecutionValidator.UpstreamCommit ||
            version is not ("0.1.0" or "0.2.0" or "0.3.0" or "0.4.0" or "0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation is not ("p28Batch" or "synthetic" or "producerBatch" or "checksumBatch" or "acquisitionSequence" or "statefulVtec" or "integratedCaptureVtec" or "limiterSequence" or "adaptiveLimiter" or "idleTarget" or "idleContexts" or "fuelMapLookup" or "fuelCalculationChain" or "fuelAdditiveCorrectionChain" or "fuelFactorProductionChain" or "limiterFuelGateChain" or "adaptiveLimiterFuelGateChain" or "fuelPostStoreChain" or "fuelPostStoreConsumerChain" or "ignitionMapLookup" or "ignitionSelectorChain" or "ignitionCorrectionChain" or "vtecFuelChain" or "vtecFuelIgnitionChain" or "vtecThresholdPrefix" or "vtecThresholdControl") ||
            operation == "fuelCalculationChain" && version is not (FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "ignitionCorrectionChain" && version is not (FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "vtecFuelChain" && version is not (PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "ignitionSelectorChain" && version is not (SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "vtecFuelIgnitionChain" && version is not (SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "fuelAdditiveCorrectionChain" && version is not (FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "fuelFactorProductionChain" && version is not (FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "limiterFuelGateChain" && version is not (LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "adaptiveLimiterFuelGateChain" && version is not (AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "fuelPostStoreChain" && version is not (PostStoreVersion or CurrentVersion) ||
            operation == "fuelPostStoreConsumerChain" && version != CurrentVersion ||
            operation == "producerBatch" && version == "0.1.0" ||
            operation == "checksumBatch" && version is not ("0.3.0" or "0.4.0" or "0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "acquisitionSequence" && version is not ("0.4.0" or "0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "statefulVtec" && version is not ("0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "integratedCaptureVtec" && version is not ("0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "limiterSequence" && version is not ("0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "adaptiveLimiter" && version is not ("0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "idleTarget" && version is not ("0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "idleContexts" && version is not ("0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "fuelMapLookup" && version is not ("0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation == "ignitionMapLookup" && version is not ("0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ||
            operation is "vtecThresholdPrefix" or "vtecThresholdControl" && version is not ("0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion))
        {
            throw new SliceProcessException(SliceProcessFailure.Protocol,
                "Runner version, operation or protocol differs from the audited compatibility inventory.");
        }
        var expected = version == "0.1.0" ? LegacyFixes : version == "0.2.0" ? ProducerFixes :
            version == "0.3.0" ? ChecksumFixes : version == "0.4.0" ? AcquisitionFixes : (version is "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) ? [.. CurrentFixes, "adaptive-exact-word-add-sub-half-carry", "idle-exact-arithmetic-half-carry"] : version == "0.8.0" ? [.. CurrentFixes, "adaptive-exact-word-add-sub-half-carry"] : CurrentFixes;
        if (version is FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) expected = [.. expected, "word-rol-accumulator-through-carry-preserves-noncarry-flags", "word-add-accumulator-er0-offpage-half-carry"];
        if (version is FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or CurrentVersion) expected = [.. expected, "word-rol-er0-through-carry-preserves-noncarry-flags", "word-sll-accumulator-preserves-noncarry-flags"];
        var fixes = root.GetProperty("localSemanticFixes").EnumerateArray().Select(item => item.GetString()!).ToArray();
        if (!fixes.Order(StringComparer.Ordinal).SequenceEqual(expected.Order(StringComparer.Ordinal)))
        {
            throw new SliceProcessException(SliceProcessFailure.Protocol, "Runner semantic fixes differ from its audited version.");
        }
        return fixes;
    }
}
