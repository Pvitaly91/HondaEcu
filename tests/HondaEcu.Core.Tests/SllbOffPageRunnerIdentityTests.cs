using System.Text.Json;

namespace HondaEcu.Core.Tests;

/// <summary>Invented identity fixtures and one invented decoded subprocess probe; no OEM execution.</summary>
public sealed class SllbOffPageRunnerIdentityTests
{
    private const string NewFix = "byte-sll-off-page-preserves-noncarry-flags";
    // Explicit historical inventory, independent of the production inventory builder.
    private static readonly string[] HistoricalFixes =
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

    public static IEnumerable<object[]> ExistingOperationsAndVersions()
    {
        // Identity compatibility is not instruction admission or a claim that these tasks execute here.
        string[] operations =
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
        foreach (var operation in operations)
            foreach (var version in new[] { "0.40.0", "0.41.0" })
                yield return [operation, version];
    }

    [Theory]
    [MemberData(nameof(ExistingOperationsAndVersions))]
    public void ExistingOperationInventoriesRemainDistinctAndExact(string operation, string version)
    {
        var fixes = Fixes(version);
        var root = Identity(version, fixes, operation);
        Assert.Equal(fixes, SliceRunnerIdentity.Validate(root, operation));
        Assert.Equal(version, root.GetProperty("runnerVersion").GetString());
        Assert.Equal(version == "0.41.0" ? 35 : 34, fixes.Length);
        Assert.Equal(fixes.Length, fixes.Distinct(StringComparer.Ordinal).Count());
        Assert.Equal(version == "0.41.0", fixes.Contains(NewFix, StringComparer.Ordinal));
    }

    [Theory]
    [InlineData("0.40.0", "0.41.0")]
    [InlineData("0.41.0", "0.40.0")]
    public void VersionCannotClaimTheOtherSemanticInventory(string version, string inventoryVersion)
    {
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(
            Identity(version, Fixes(inventoryVersion)), "synthetic"));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
    }

    [Theory]
    [InlineData("0.40.0", "missing")]
    [InlineData("0.41.0", "missing")]
    [InlineData("0.40.0", "duplicate")]
    [InlineData("0.41.0", "duplicate")]
    [InlineData("0.40.0", "unknown")]
    [InlineData("0.41.0", "unknown")]
    public void MissingDuplicateOrUnknownIdentityIsRejected(string version, string mutation)
    {
        var original = Fixes(version);
        string[] changed = mutation switch
        {
            "missing" => original[1..],
            "duplicate" => [.. original, original[0]],
            "unknown" => [.. original, "invented-unreviewed-semantic-fix"],
            _ => throw new ArgumentOutOfRangeException(nameof(mutation)),
        };
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(
            Identity(version, changed), "synthetic"));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
    }

    [Theory]
    [InlineData("protocol")]
    [InlineData("operation-mismatch")]
    [InlineData("new-operation")]
    [InlineData("upstream")]
    [InlineData("version")]
    public void SemanticFixDoesNotRelaxExistingWireIdentityGuards(string guard)
    {
        var fixes = Fixes("0.41.0");
        var root = guard switch
        {
            "protocol" => Identity("0.41.0", fixes, protocolVersion: 2),
            "operation-mismatch" => Identity("0.41.0", fixes, "producerBatch"),
            "new-operation" => Identity("0.41.0", fixes, "inventedSllbOffPageOperation"),
            "upstream" => Identity("0.41.0", fixes, upstreamCommit: "invented-unreviewed-upstream"),
            "version" => Identity("0.42.0", fixes),
            _ => throw new ArgumentOutOfRangeException(nameof(guard)),
        };
        var operation = guard == "new-operation" ? "inventedSllbOffPageOperation" : "synthetic";
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(root, operation));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
    }

    [Fact]
    public void NewSemanticIdentityDoesNotAllowHistorical039ToClaimTheTail()
    {
        var error = Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(
            Identity("0.39.0", Fixes("0.41.0"), P28Data0136TailValidator.Operation), P28Data0136TailValidator.Operation));
        Assert.Equal(SliceProcessFailure.Protocol, error.Failure);
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task Actual041RunnerDisclosesOnlyTheNewFixButStillRefusesUnadmittedOffPageSllb()
    {
        // Invented C4 B6 D7 at PC0, LRB0063 -> RAM03B6. No ECU caller provenance.
        // The unchanged generic synthetic policy refuses this exact form.
        // Real step() ISA coverage lives in Rust, not a widened wire admission.
        const int incomingPsw = 0xFFFB;
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "invented-m2an-sllb-offpage-probe", rom = new[] { 0xC4, 0xB6, 0xD7 } } },
            scratchPatterns = new[] { 85 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { 3 },
                allowedCodeRanges = new[] { new[] { 0, 3 } },
                psw = incomingPsw,
                lrb = 0x63,
                usp = 0x280,
                instructionBudget = 1,
                dataSeeds = new[] { new[] { 0x3B5, 0xA6 }, new[] { 0x3B6, 1 }, new[] { 0x3B7, 0x5C }, new[] { 0x318, 0x6D } },
                outputAddresses = new[] { 0x3B5, 0x3B6, 0x3B7, 4, 5, 6, 7, 2, 3, 0x318 },
            },
        });
        var root = response.Response;
        Assert.Equal(1, root.GetProperty("protocolVersion").GetInt32());
        Assert.Equal("0.41.0", root.GetProperty("runnerVersion").GetString());
        var inventory = SliceRunnerIdentity.Validate(root, "synthetic");
        Assert.Equal(Fixes("0.41.0"), inventory);
        Assert.Equal(new[] { NewFix }, inventory.Except(HistoricalFixes, StringComparer.Ordinal));
        var result = root.GetProperty("syntheticResult");
        Assert.Equal(2, result.GetProperty("status").GetInt32());
        Assert.Equal("unimplemented in reviewed slice subset: SLLB off N8", result.GetProperty("error").GetString());
        Assert.Empty(result.GetProperty("usedAssumptions").EnumerateArray());
        Assert.Equal(0, result.GetProperty("steps").GetInt32());
        Assert.Equal(0, result.GetProperty("stopPc").GetInt32());
        Assert.Equal(new[] { 0xA6, 1, 0x5C, 0xFB, 0xFF, 85, 85, 0x63, 0, 0x6D },
            result.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        Assert.Empty(result.GetProperty("trace").EnumerateArray());
        Assert.Empty(result.GetProperty("programReads").EnumerateArray());
    }

    private static string[] Fixes(string version) => version == "0.41.0" ? [.. HistoricalFixes, NewFix] : [.. HistoricalFixes];

    private static JsonElement Identity(string version, string[] fixes, string operation = "synthetic",
        int protocolVersion = 1, string upstreamCommit = P28ByteExecutionValidator.UpstreamCommit) =>
        JsonSerializer.SerializeToElement(new { protocolVersion, operation, runnerVersion = version, upstreamCommit, localSemanticFixes = fixes });
}
