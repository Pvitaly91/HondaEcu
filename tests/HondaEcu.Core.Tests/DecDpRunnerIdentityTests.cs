using System.Text.Json;

namespace HondaEcu.Core.Tests;

/// <summary>Invented version identities and refused opcode82 wire probes, never OEM execution.</summary>
public sealed class DecDpRunnerIdentityTests
{
    private const string SllbFix = "byte-sll-off-page-preserves-noncarry-flags";
    private const string DecDpFix = "word-decrement-dp-half-borrow";

    // Explicit audited 0.40 inventory, independent of the production inventory builder.
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
        // Metadata compatibility is not instruction admission or hardware permission.
        foreach (var operation in ExistingOperations)
            foreach (var version in new[] { "0.40.0", "0.41.0", "0.42.0" })
                yield return [operation, version];
    }

    [Theory]
    [MemberData(nameof(ExistingOperationsAndVersions))]
    public void ExactInventoriesPreserveHistoricalContractsForEveryExistingOperation(string operation, string version)
    {
        var fixes = Fixes(version);
        var root = Identity(version, fixes, operation);
        Assert.Equal(fixes, SliceRunnerIdentity.Validate(root, operation));
        Assert.Equal(version, root.GetProperty("runnerVersion").GetString());
        Assert.Equal(version switch { "0.40.0" => 34, "0.41.0" => 35, "0.42.0" => 36, _ => throw new ArgumentOutOfRangeException(nameof(version)) }, fixes.Length);
        Assert.Equal(fixes.Length, fixes.Distinct(StringComparer.Ordinal).Count());
        Assert.Equal(version != "0.40.0", fixes.Contains(SllbFix, StringComparer.Ordinal));
        Assert.Equal(version == "0.42.0", fixes.Contains(DecDpFix, StringComparer.Ordinal));
    }

    [Theory]
    [InlineData("0.40.0", "0.41.0")]
    [InlineData("0.40.0", "0.42.0")]
    [InlineData("0.41.0", "0.40.0")]
    [InlineData("0.41.0", "0.42.0")]
    [InlineData("0.42.0", "0.40.0")]
    [InlineData("0.42.0", "0.41.0")]
    public void AnotherVersionsInventoryIsRejectedForEveryExistingOperation(string version, string inventoryVersion)
    {
        foreach (var operation in ExistingOperations)
        {
            var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(
                Identity(version, Fixes(inventoryVersion), operation), operation));
            Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
        }
    }

    [Theory]
    [InlineData("0.40.0", "missing")]
    [InlineData("0.41.0", "missing")]
    [InlineData("0.42.0", "missing")]
    [InlineData("0.40.0", "duplicate")]
    [InlineData("0.41.0", "duplicate")]
    [InlineData("0.42.0", "duplicate")]
    [InlineData("0.40.0", "unknown")]
    [InlineData("0.41.0", "unknown")]
    [InlineData("0.42.0", "unknown")]
    [InlineData("0.40.0", "wrong-same-count")]
    [InlineData("0.41.0", "wrong-same-count")]
    [InlineData("0.42.0", "wrong-same-count")]
    public void MissingDuplicateUnknownAndWrongIdentityRemainRejectedForEveryExistingOperation(string version, string mutation)
    {
        var original = Fixes(version);
        string[] changed = mutation switch
        {
            // The last identity is precisely the version's newest audited fix.
            "missing" => original[..^1],
            "duplicate" => [.. original, original[^1]],
            "unknown" => [.. original, "invented-unreviewed-semantic-fix"],
            "wrong-same-count" => [.. original[..^1], "invented-wrong-semantic-fix"],
            _ => throw new ArgumentOutOfRangeException(nameof(mutation)),
        };
        foreach (var operation in ExistingOperations)
        {
            var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(
                Identity(version, changed, operation), operation));
            Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
        }
    }

    [Theory]
    [InlineData("protocol")]
    [InlineData("operation-mismatch")]
    [InlineData("new-operation")]
    [InlineData("upstream")]
    [InlineData("unknown-version")]
    public void DecDpSemanticIdentityCannotRelaxWireIdentityGuards(string guard)
    {
        var fixes = Fixes("0.42.0");
        var root = guard switch
        {
            "protocol" => Identity("0.42.0", fixes, protocolVersion: 2),
            "operation-mismatch" => Identity("0.42.0", fixes, "producerBatch"),
            "new-operation" => Identity("0.42.0", fixes, "inventedDecDpResetOperation"),
            "upstream" => Identity("0.42.0", fixes, upstreamCommit: "invented-unreviewed-upstream"),
            "unknown-version" => Identity("0.43.0", fixes),
            _ => throw new ArgumentOutOfRangeException(nameof(guard)),
        };
        var operation = guard == "new-operation" ? "inventedDecDpResetOperation" : "synthetic";
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(root, operation));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
    }

    [Fact]
    public void NewDecDpIdentityCannotLetHistorical039ClaimTheTail()
    {
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(
            Identity("0.39.0", Fixes("0.42.0"), P28Data0136TailValidator.Operation), P28Data0136TailValidator.Operation));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    [Trait("Category", "RustIntegration")]
    public async Task Actual043RunnerDisclosesTwoCycleFixesButRefusesUnadmittedDecDpBeforeStep(bool dd)
    {
        // Newly invented byte82 at PC0; SCB7 DP is ordinary RAM00BC/D.
        // These seeds are only a generic invented wire-refusal fixture, not ECU history.
        var incomingPsw = 0xEFFF | (dd ? 0x1000 : 0);
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "invented-m2at-dec-dp-wire-refusal", rom = new[] { 0x82 } } },
            scratchPatterns = new[] { 85 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { 1 },
                allowedCodeRanges = new[] { new[] { 0, 1 } },
                psw = incomingPsw,
                lrb = 0x63,
                usp = 0x280,
                instructionBudget = 1,
                dataSeeds = new[] { new[] { 0xBC, 0x10 }, new[] { 0xBD, 0 }, new[] { 0xBA, 0xA6 }, new[] { 0xBB, 0x5C }, new[] { 0x318, 0x6D }, new[] { 0x360, 0xC7 } },
                outputAddresses = new[] { 0xBC, 0xBD, 4, 5, 6, 7, 2, 3, 0, 1, 0xBE, 0xBF, 0xBA, 0xBB, 0x318, 0x360 },
            },
        });
        var root = response.Response;
        Assert.Equal(1, root.GetProperty("protocolVersion").GetInt32());
        Assert.Equal("0.43.0", root.GetProperty("runnerVersion").GetString());
        var inventory = SliceRunnerIdentity.Validate(root, "synthetic");
        Assert.Equal([.. Fixes("0.42.0"), "word-dec-dp-int-cycle-count", "byte-sll-offpage-int-cycle-count"], inventory);
        Assert.Equal(new[] { "word-dec-dp-int-cycle-count", "byte-sll-offpage-int-cycle-count" }, inventory.Except(Fixes("0.42.0"), StringComparer.Ordinal));
        var result = root.GetProperty("syntheticResult");
        Assert.Equal(2, result.GetProperty("status").GetInt32());
        Assert.Equal("unimplemented in reviewed slice subset: DEC DP", result.GetProperty("error").GetString());
        Assert.Empty(result.GetProperty("usedAssumptions").EnumerateArray());
        Assert.Equal(0, result.GetProperty("steps").GetInt32());
        Assert.Equal(0, result.GetProperty("stopPc").GetInt32());
        Assert.Equal(new[] { 0x10, 0, 0xFF, dd ? 0xFF : 0xEF, 85, 85, 0x63, 0, 0xFE, 7, 0x80, 2, 0xA6, 0x5C, 0x6D, 0xC7 },
            result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        Assert.Empty(result.GetProperty("trace").EnumerateArray());
        Assert.Empty(result.GetProperty("programReads").EnumerateArray());
    }

    private static string[] Fixes(string version) => version switch
    {
        "0.40.0" => [.. Historical040Fixes],
        "0.41.0" => [.. Historical040Fixes, SllbFix],
        "0.42.0" => [.. Historical040Fixes, SllbFix, DecDpFix],
        _ => throw new ArgumentOutOfRangeException(nameof(version)),
    };

    private static JsonElement Identity(string version, string[] fixes, string operation = "synthetic",
        int protocolVersion = 1, string upstreamCommit = P28ByteExecutionValidator.UpstreamCommit) =>
        JsonSerializer.SerializeToElement(new { protocolVersion, operation, runnerVersion = version, upstreamCommit, localSemanticFixes = fixes });
}
