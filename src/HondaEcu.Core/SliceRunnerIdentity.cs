using System.Text.Json;

namespace HondaEcu.Core;

/// <summary>Explicit compatibility inventory, not executable attestation or a hardware trust anchor.</summary>
internal static class SliceRunnerIdentity
{
    internal const string CurrentVersion = "0.31.0";
    internal const string HandoffVersion = "0.30.0";
    internal const string NativeProducerVersion = "0.29.0";
    internal const string CommonResultConsumerVersion = "0.27.0";
    internal const string DivisionDecisionVersion = "0.28.0";
    internal const string PostSelectionCriticalVersion = "0.26.0";
    internal const string PostStoreConsumerVersion = "0.25.0";
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
        var actualOperation = operation;
        var quartetVersion = version == CurrentVersion;
        if (operation == P28QuartetHandoffValidator.Operation && !quartetVersion)
            throw new SliceProcessException(SliceProcessFailure.Protocol, "M2x requires runner0.31.0; historical runners cannot execute this operation.");
        if (operation == P28QuartetHandoffValidator.Operation) operation = P28Data0136HandoffValidator.Operation;
        if (quartetVersion) version = HandoffVersion;
        if (operation == P28Data0136HandoffValidator.Operation && version != HandoffVersion)
            throw new SliceProcessException(SliceProcessFailure.Protocol, "M2w requires runner0.30.0; historical runners cannot execute this operation.");
        if (version == HandoffVersion) version = NativeProducerVersion;
        if (operation == P28Data0136HandoffValidator.Operation) operation = P28Data0136TechnicalProducerValidator.Operation;
        var nativeProducerVersion = version == NativeProducerVersion;
        if (operation == P28Data0136TechnicalProducerValidator.Operation && !nativeProducerVersion)
            throw new SliceProcessException(SliceProcessFailure.Protocol, "M2v requires runner0.29.0; historical runners cannot execute this operation.");
        // Real identity is checked below. Internal inventory selection only reuses
        // the base capability list; no response/execution/report is relabelled.
        if (nativeProducerVersion) version = DivisionDecisionVersion;
        if (operation == P28Data0136TechnicalProducerValidator.Operation) operation = "acquisitionSequence";
        // M2t has the same semantic-fix inventory, not a new JGT semantic fix.
        if (operation == P28DivisionDecisionValidator.Operation && version != DivisionDecisionVersion)
            throw new SliceProcessException(SliceProcessFailure.Protocol, "M2t requires runner0.28.0; historical runner0.27.0 cannot execute this operation.");
        if (version == DivisionDecisionVersion) version = CommonResultConsumerVersion;
        if (version == MetadataCorrectionVersion && operation is not ("fuelCalculationChain" or "fuelAdditiveCorrectionChain" or "fuelFactorProductionChain"))
            version = FuelCalculationVersion;
        // M2j changes only the correction capability disclosure/validation.
        // Other operations retain the exact 0.17.0 semantic-fix inventory.
        if (version == LegacyCorrectionVersion && operation is not ("ignitionCorrectionChain" or "fuelCalculationChain" or "fuelAdditiveCorrectionChain" or "fuelFactorProductionChain"))
            version = FuelCalculationVersion;
        if (root.GetProperty("protocolVersion").GetInt32() != 1 || root.GetProperty("operation").GetString() != actualOperation ||
            root.GetProperty("upstreamCommit").GetString() != P28ByteExecutionValidator.UpstreamCommit ||
            version is not ("0.1.0" or "0.2.0" or "0.3.0" or "0.4.0" or "0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation is not ("p28Batch" or "synthetic" or "producerBatch" or "checksumBatch" or "acquisitionSequence" or "statefulVtec" or "integratedCaptureVtec" or "limiterSequence" or "adaptiveLimiter" or "idleTarget" or "idleContexts" or "fuelMapLookup" or "fuelCalculationChain" or "fuelAdditiveCorrectionChain" or "fuelFactorProductionChain" or "limiterFuelGateChain" or "adaptiveLimiterFuelGateChain" or "fuelPostStoreChain" or "fuelPostStoreConsumerChain" or "fuelPostSelectionCriticalChain" or "fuelCommonResultConsumerChain" or "fuelDivisionDecisionChain" or "ignitionMapLookup" or "ignitionSelectorChain" or "ignitionCorrectionChain" or "vtecFuelChain" or "vtecFuelIgnitionChain" or "vtecThresholdPrefix" or "vtecThresholdControl") ||
            operation == "fuelCalculationChain" && version is not (FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "ignitionCorrectionChain" && version is not (FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "vtecFuelChain" && version is not (PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "ignitionSelectorChain" && version is not (SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "vtecFuelIgnitionChain" && version is not (SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "fuelAdditiveCorrectionChain" && version is not (FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "fuelFactorProductionChain" && version is not (FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "limiterFuelGateChain" && version is not (LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "adaptiveLimiterFuelGateChain" && version is not (AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "fuelPostStoreChain" && version is not (PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "fuelPostStoreConsumerChain" && version is not (PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "fuelPostSelectionCriticalChain" && version is not (PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "fuelCommonResultConsumerChain" && version != CommonResultConsumerVersion ||
            operation == "producerBatch" && version == "0.1.0" ||
            operation == "checksumBatch" && version is not ("0.3.0" or "0.4.0" or "0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "acquisitionSequence" && version is not ("0.4.0" or "0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "statefulVtec" && version is not ("0.5.0" or "0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "integratedCaptureVtec" && version is not ("0.6.0" or "0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "limiterSequence" && version is not ("0.7.0" or "0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "adaptiveLimiter" && version is not ("0.8.0" or "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "idleTarget" && version is not ("0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "idleContexts" && version is not ("0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "fuelMapLookup" && version is not ("0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation == "ignitionMapLookup" && version is not ("0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ||
            operation is "vtecThresholdPrefix" or "vtecThresholdControl" && version is not ("0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion))
        {
            throw new SliceProcessException(SliceProcessFailure.Protocol,
                "Runner version, operation or protocol differs from the audited compatibility inventory.");
        }
        var expected = version == "0.1.0" ? LegacyFixes : version == "0.2.0" ? ProducerFixes :
            version == "0.3.0" ? ChecksumFixes : version == "0.4.0" ? AcquisitionFixes : (version is "0.9.0" or "0.10.0" or "0.11.0" or "0.12.0" or "0.13.0" or PreviousVersion or SelectorVersion or SharedVersion or FuelCalculationVersion or FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) ? [.. CurrentFixes, "adaptive-exact-word-add-sub-half-carry", "idle-exact-arithmetic-half-carry"] : version == "0.8.0" ? [.. CurrentFixes, "adaptive-exact-word-add-sub-half-carry"] : CurrentFixes;
        if (version is FuelAdditiveVersion or FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) expected = [.. expected, "word-rol-accumulator-through-carry-preserves-noncarry-flags", "word-add-accumulator-er0-offpage-half-carry"];
        if (version is FuelFactorVersion or LimiterFuelVersion or AdaptiveFuelVersion or PostStoreVersion or PostStoreConsumerVersion or PostSelectionCriticalVersion or CommonResultConsumerVersion) expected = [.. expected, "word-rol-er0-through-carry-preserves-noncarry-flags", "word-sll-accumulator-preserves-noncarry-flags"];
        if (version == CommonResultConsumerVersion) expected = [.. expected, "word-add-dp-immediate-half-carry"];
        if (nativeProducerVersion) expected = [.. expected, "byte-sbc-r0-immediate-half-borrow", "word-decrement-x1-half-borrow"];
        if (quartetVersion) expected = [.. expected, "word-add-a-indexed-x1-half-carry"];
        var fixes = root.GetProperty("localSemanticFixes").EnumerateArray().Select(item => item.GetString()!).ToArray();
        if (!fixes.Order(StringComparer.Ordinal).SequenceEqual(expected.Order(StringComparer.Ordinal)))
        {
            throw new SliceProcessException(SliceProcessFailure.Protocol, "Runner semantic fixes differ from its audited version.");
        }
        return fixes;
    }
}
