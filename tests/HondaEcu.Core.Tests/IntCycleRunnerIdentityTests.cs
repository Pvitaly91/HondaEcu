using System.Text.Json;

namespace HondaEcu.Core.Tests;

/// <summary>Invented identities and before-step wire refusals; accounting never grants admission.</summary>
public sealed class IntCycleRunnerIdentityTests
{
    private const string SllbSemanticFix = "byte-sll-off-page-preserves-noncarry-flags";
    private const string DecDpSemanticFix = "word-decrement-dp-half-borrow";
    private const string DecDpCycleFix = "word-dec-dp-int-cycle-count";
    private const string SllbCycleFix = "byte-sll-offpage-int-cycle-count";

    // Explicit independently reviewed historical inventory, not the production builder.
    private static readonly string[] Historical040Fixes =
    [
        "word-ror-through-carry-preserves-noncarry-flags",
        "load-zero-flag-and-dd-contract",
        "word-srl-preserves-noncarry-flags",
        "bit-operands-use-byte-access",
        "clr-accumulator-zero-flag",
        "jrnz-dpl-byte-count",
        "adcb-r0-immediate-half-carry",
        "inc-x1-half-carry",
        "indexed-alternate-immediate-displacement",
        "word-data-access-alignment",
        "byte-add-direct-accumulator-half-carry",
        "byte-add-r0-accumulator-half-carry",
        "inc-indexed-x2-half-carry",
        "word-sub-direct-updates-half-borrow",
        "byte-inc-direct-updates-half-carry",
        "byte-sll-accumulator-preserves-noncarry-flags",
        "byte-clear-accumulator-zero-flag",
        "stateful-exact-byte-add-sub-half-carry",
        "increment-dp-half-carry",
        "decrement-indexed-x1-byte-half-borrow",
        "adaptive-exact-word-add-sub-half-carry",
        "idle-exact-arithmetic-half-carry",
        "word-rol-accumulator-through-carry-preserves-noncarry-flags",
        "word-add-accumulator-er0-offpage-half-carry",
        "word-rol-er0-through-carry-preserves-noncarry-flags",
        "word-sll-accumulator-preserves-noncarry-flags",
        "word-add-dp-immediate-half-carry",
        "byte-sbc-r0-immediate-half-borrow",
        "word-decrement-x1-half-borrow",
        "word-add-a-indexed-x1-half-carry",
        "byte-rol-off-through-carry-preserves-noncarry-flags",
        "byte-rol-a-through-carry-preserves-noncarry-flags",
        "cal-addr16-rt-clears-internal-stack-flag",
        "byte-incb-r0-half-carry",
    ];

    private static readonly string[] Versions = ["0.40.0", "0.41.0", "0.42.0", "0.43.0"];
    private static readonly string[] ExistingOperations =
    [
        "p28Batch", "synthetic", "producerBatch", "checksumBatch", "acquisitionSequence",
        "statefulVtec", "integratedCaptureVtec", "limiterSequence", "adaptiveLimiter", "idleTarget",
        "idleContexts", "fuelMapLookup", "fuelCalculationChain", "fuelAdditiveCorrectionChain",
        "fuelFactorProductionChain", "limiterFuelGateChain", "adaptiveLimiterFuelGateChain",
        "fuelPostStoreChain", "fuelPostStoreConsumerChain", "fuelPostSelectionCriticalChain",
        "fuelCommonResultConsumerChain", "fuelDivisionDecisionChain", "ignitionMapLookup",
        "ignitionSelectorChain", "ignitionCorrectionChain", "vtecFuelChain", "vtecFuelIgnitionChain",
        "vtecThresholdPrefix", "vtecThresholdControl",
        P28Data0136TechnicalProducerValidator.Operation, P28Data0136HandoffValidator.Operation,
        P28QuartetHandoffValidator.Operation, P28Word0196HandoffValidator.Operation,
        P28Word0196AlternateValidator.Operation, P28P2LatchValidator.Operation,
        P28PostP2ControlValidator.Operation, P28BelowSecondP2Validator.Operation,
        P28CalRtRoundTripValidator.Operation, P28PostReturnSelectorValidator.Operation,
        P28FallthroughData0136Validator.Operation, P28Data0136TailValidator.Operation,
    ];

    public static IEnumerable<object[]> ExistingOperationsAndVersions()
    {
        foreach (var operation in ExistingOperations)
            foreach (var version in Versions)
                yield return [operation, version];
    }

    [Theory]
    [MemberData(nameof(ExistingOperationsAndVersions))]
    public void FourReleasedInventoriesRemainDistinctForEveryExistingOperation(string operation, string version)
    {
        var fixes = Fixes(version);
        var root = Identity(version, fixes, operation);
        Assert.Equal(fixes, SliceRunnerIdentity.Validate(root, operation));
        Assert.Equal(version, root.GetProperty("runnerVersion").GetString());
        Assert.Equal(version switch { "0.40.0" => 34, "0.41.0" => 35, "0.42.0" => 36, "0.43.0" => 38, _ => throw new ArgumentOutOfRangeException(nameof(version)) }, fixes.Length);
        Assert.Equal(fixes.Length, fixes.Distinct(StringComparer.Ordinal).Count());
        Assert.Equal(version != "0.40.0", fixes.Contains(SllbSemanticFix, StringComparer.Ordinal));
        Assert.Equal(version is "0.42.0" or "0.43.0", fixes.Contains(DecDpSemanticFix, StringComparer.Ordinal));
        Assert.Equal(version == "0.43.0", fixes.Contains(DecDpCycleFix, StringComparer.Ordinal));
        Assert.Equal(version == "0.43.0", fixes.Contains(SllbCycleFix, StringComparer.Ordinal));
        if (version == "0.43.0")
            Assert.Equal(new[] { DecDpCycleFix, SllbCycleFix }, fixes.Except(Fixes("0.42.0"), StringComparer.Ordinal));
    }

    public static IEnumerable<object[]> CrossVersionInventories()
    {
        foreach (var version in Versions)
            foreach (var inventoryVersion in Versions.Where(v => v != version))
                yield return [version, inventoryVersion];
    }

    [Theory]
    [MemberData(nameof(CrossVersionInventories))]
    public void CrossVersionInventoryIsRejectedForEveryExistingOperation(string version, string inventoryVersion)
    {
        foreach (var operation in ExistingOperations)
            AssertProtocol(Identity(version, Fixes(inventoryVersion), operation), operation);
    }

    public static IEnumerable<object[]> InventoryMutations()
    {
        foreach (var version in Versions)
            foreach (var mutation in new[] { "missing", "duplicate", "unknown", "wrong-same-count" })
                yield return [version, mutation];
    }

    [Theory]
    [MemberData(nameof(InventoryMutations))]
    public void MissingDuplicateUnknownAndWrongSameCountStayRejected(string version, string mutation)
    {
        var original = Fixes(version);
        string[] changed = mutation switch
        {
            "missing" => original[..^1],
            "duplicate" => [.. original, original[^1]],
            "unknown" => [.. original, "invented-unreviewed-accounting-fix"],
            "wrong-same-count" => [.. original[..^1], "invented-wrong-accounting-fix"],
            _ => throw new ArgumentOutOfRangeException(nameof(mutation)),
        };
        foreach (var operation in ExistingOperations)
            AssertProtocol(Identity(version, changed, operation), operation);
    }

    [Theory]
    [InlineData(DecDpCycleFix, "missing")]
    [InlineData(SllbCycleFix, "missing")]
    [InlineData(DecDpCycleFix, "duplicate")]
    [InlineData(SllbCycleFix, "duplicate")]
    [InlineData(DecDpCycleFix, "unknown-replacement")]
    [InlineData(SllbCycleFix, "unknown-replacement")]
    [InlineData(DecDpCycleFix, "other-cycle-replacement")]
    [InlineData(SllbCycleFix, "other-cycle-replacement")]
    public void EachCurrentCycleIdentityIsIndividuallyRequiredExactlyOnce(string cycleFix, string mutation)
    {
        var original = Fixes("0.43.0");
        var without = original.Where(f => f != cycleFix).ToArray();
        var otherCycleFix = cycleFix == DecDpCycleFix ? SllbCycleFix : DecDpCycleFix;
        string[] changed = mutation switch
        {
            "missing" => without,
            "duplicate" => [.. original, cycleFix],
            "unknown-replacement" => [.. without, "invented-unreviewed-accounting-fix"],
            "other-cycle-replacement" => [.. without, otherCycleFix],
            _ => throw new ArgumentOutOfRangeException(nameof(mutation)),
        };
        foreach (var operation in ExistingOperations)
            AssertProtocol(Identity("0.43.0", changed, operation), operation);
    }

    public static IEnumerable<object[]> WireGuards()
    {
        foreach (var version in Versions)
            foreach (var guard in new[] { "protocol", "operation-mismatch", "new-operation", "upstream", "unknown-version" })
                yield return [version, guard];
    }

    [Theory]
    [MemberData(nameof(WireGuards))]
    public void AccountingIdentityCannotRelaxProtocolOperationUpstreamOrVersion(string version, string guard)
    {
        var fixes = Fixes(version);
        var root = guard switch
        {
            "protocol" => Identity(version, fixes, protocolVersion: 2),
            "operation-mismatch" => Identity(version, fixes, "producerBatch"),
            "new-operation" => Identity(version, fixes, "inventedIntCycleExecutionOperation"),
            "upstream" => Identity(version, fixes, upstreamCommit: "invented-unreviewed-upstream"),
            "unknown-version" => Identity("0.44.0", fixes),
            _ => throw new ArgumentOutOfRangeException(nameof(guard)),
        };
        AssertProtocol(root, guard == "new-operation" ? "inventedIntCycleExecutionOperation" : "synthetic");
    }

    [Theory]
    [InlineData("0.39.0", P28Data0136TailValidator.Operation, "runner0.40.0")]
    [InlineData("0.38.0", P28FallthroughData0136Validator.Operation, "runner0.39.0")]
    [InlineData("0.37.0", P28PostReturnSelectorValidator.Operation, "runner0.38.0")]
    [InlineData("0.36.0", P28CalRtRoundTripValidator.Operation, "runner0.37.0")]
    [InlineData("0.35.0", P28BelowSecondP2Validator.Operation, "runner0.36.0")]
    [InlineData("0.34.0", P28PostP2ControlValidator.Operation, "runner0.35.0")]
    public void CurrentCycleInventoryCannotBypassHistoricalOperationThreshold(string version, string operation, string requiredVersion)
    {
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(Identity(version, Fixes("0.43.0"), operation), operation));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
        Assert.Contains(requiredVersion, error.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("dec-dp", false)]
    [InlineData("dec-dp", true)]
    [InlineData("sllb-offpage", false)]
    [InlineData("sllb-offpage", true)]
    [Trait("Category", "RustIntegration")]
    public async Task CurrentCycleInventoryCannotAdmitEitherExactFormInEitherDdState(string form, bool dd)
    {
        // Newly invented PC0 bytes and ordinary nonaliased RAM. No ECU history.
        var isDecDp = form == "dec-dp";
        var incomingPsw = (isDecDp ? 0xEFFF : 0xEFFB) | (dd ? 0x1000 : 0);
        var rom = isDecDp ? new[] { 0x82 } : new[] { 0xC4, 0xB6, 0xD7 };
        int[][] seeds = isDecDp
            ? [new[] { 0xBC, 0x10 }, new[] { 0xBD, 0 }, new[] { 0xBA, 0xA6 }, new[] { 0xBB, 0x5C }, new[] { 0x318, 0x6D }, new[] { 0x360, 0xC7 }]
            : [new[] { 0x3B5, 0xA6 }, new[] { 0x3B6, 1 }, new[] { 0x3B7, 0x5C }, new[] { 0x318, 0x6D }];
        int[] outputs = isDecDp
            ? [0xBC, 0xBD, 4, 5, 6, 7, 2, 3, 0, 1, 0xBE, 0xBF, 0xBA, 0xBB, 0x318, 0x360]
            : [0x3B5, 0x3B6, 0x3B7, 4, 5, 6, 7, 2, 3, 0x318];
        int[] expectedOutputs = isDecDp
            ? [0x10, 0, 0xFF, dd ? 0xFF : 0xEF, 85, 85, 0x63, 0, 0xFE, 7, 0x80, 2, 0xA6, 0x5C, 0x6D, 0xC7]
            : [0xA6, 1, 0x5C, 0xFB, dd ? 0xFF : 0xEF, 85, 85, 0x63, 0, 0x6D];
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "invented-m2au-" + form + "-strict-wire-refusal", rom } },
            scratchPatterns = new[] { 85 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { rom.Length },
                allowedCodeRanges = new[] { new[] { 0, rom.Length } },
                psw = incomingPsw,
                lrb = 0x63,
                usp = 0x280,
                instructionBudget = 1,
                dataSeeds = seeds,
                outputAddresses = outputs,
            },
        });
        var root = response.Response;
        Assert.Equal(1, root.GetProperty("protocolVersion").GetInt32());
        Assert.Equal("0.43.0", root.GetProperty("runnerVersion").GetString());
        var inventory = SliceRunnerIdentity.Validate(root, "synthetic");
        Assert.Equal(Fixes("0.43.0"), inventory);
        Assert.Equal(new[] { DecDpCycleFix, SllbCycleFix }, inventory.Except(Fixes("0.42.0"), StringComparer.Ordinal));
        var result = root.GetProperty("syntheticResult");
        Assert.Equal(2, result.GetProperty("status").GetInt32());
        Assert.Equal("unimplemented in reviewed slice subset: " + (isDecDp ? "DEC DP" : "SLLB off N8"), result.GetProperty("error").GetString());
        Assert.Empty(result.GetProperty("usedAssumptions").EnumerateArray());
        Assert.Equal(0, result.GetProperty("steps").GetInt32());
        Assert.Equal(0, result.GetProperty("stopPc").GetInt32());
        Assert.Equal(expectedOutputs, result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        Assert.Empty(result.GetProperty("trace").EnumerateArray());
        Assert.Empty(result.GetProperty("programReads").EnumerateArray());
    }

    private static void AssertProtocol(JsonElement root, string operation)
    {
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(root, operation));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
    }

    private static string[] Fixes(string version) => version switch
    {
        "0.40.0" => [.. Historical040Fixes],
        "0.41.0" => [.. Historical040Fixes, SllbSemanticFix],
        "0.42.0" => [.. Historical040Fixes, SllbSemanticFix, DecDpSemanticFix],
        "0.43.0" => [.. Historical040Fixes, SllbSemanticFix, DecDpSemanticFix, DecDpCycleFix, SllbCycleFix],
        _ => throw new ArgumentOutOfRangeException(nameof(version)),
    };

    private static JsonElement Identity(string version, string[] fixes, string operation = "synthetic",
        int protocolVersion = 1, string upstreamCommit = P28ByteExecutionValidator.UpstreamCommit) =>
        JsonSerializer.SerializeToElement(new { protocolVersion, operation, runnerVersion = version, upstreamCommit, localSemanticFixes = fixes });
}
