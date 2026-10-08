using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class Jgt2714PrimarySemanticsTests
{
    [Theory]
    [InlineData(false, false, true, true)]
    [InlineData(false, true, true, false)]
    [InlineData(true, false, true, false)]
    [InlineData(true, true, false, false)]
    public void AllFourFlagStatesKeepTheTwoHypothesesSeparate(bool cf, bool zf, bool printed, bool executor)
    {
        var flags = new ResearchFlags(cf, zf, true, true);
        Assert.Equal(printed, JgtStaticResearchFixture.Predicate(JgtHypothesis.HypotheticalPrintedOR, flags));
        Assert.Equal(executor, JgtStaticResearchFixture.Predicate(JgtHypothesis.HypotheticalExecutorAND, flags));
    }

    [Theory]
    [InlineData(0x358, 0x356, false, false)]
    [InlineData(0x356, 0x356, false, true)]
    [InlineData(0x354, 0x356, true, false)]
    [InlineData(0, 0xFFFF, true, false)]
    [InlineData(0xFFFF, 0, false, false)]
    [InlineData(0x8000, 0x7FFF, false, false)]
    [InlineData(0x7FFF, 0x8000, true, false)]
    public void WordCmpUsesUnsignedLeftMinusRightBorrowAndEquality(int left, int right, bool cf, bool zf)
    {
        foreach (var hc in new[] { false, true })
            foreach (var dd in new[] { false, true })
            {
                var result = JgtStaticResearchFixture.Compare16((ushort)left, (ushort)right, new(!cf, !zf, hc, dd));
                Assert.Equal(cf, result.Cf); Assert.Equal(zf, result.Zf);
                Assert.Equal(hc, result.Hc); Assert.Equal(dd, result.Dd); Assert.False(result.Cf && result.Zf);
            }
    }

    [Fact]
    public void EqualityOutcomeConflictIsNotResolvedByConsistency()
    {
        var equality = JgtStaticResearchFixture.Compare16(0x356, 0x356, new(true, false, true, true));
        Assert.False(equality.Cf); Assert.True(equality.Zf);
        Assert.True(JgtStaticResearchFixture.Predicate(JgtHypothesis.HypotheticalPrintedOR, equality));
        Assert.False(JgtStaticResearchFixture.Predicate(JgtHypothesis.HypotheticalExecutorAND, equality));
        Assert.True(equality.Cf || equality.Zf); // LE also true: documentary inconsistency, not silicon truth.
    }

    [Fact]
    public void ImpossibleCmpFlagCombinationIsNotSmuggledInAsLoopExit()
    {
        foreach (var right in new ushort[] { 0, 1, 0x356, 0xFFFF })
            for (var left = 0; left <= 0xFFFF; left++)
            {
                var flags = JgtStaticResearchFixture.Compare16((ushort)left, right, new(true, true, false, true));
                Assert.False(flags.Cf && flags.Zf);
                Assert.True(JgtStaticResearchFixture.Predicate(JgtHypothesis.HypotheticalPrintedOR, flags));
            }
    }

    [Theory]
    [InlineData(0x46, 500, 371, 0x354)]
    [InlineData(0x47, 457, 328, 0x2FE)]
    public void AndHypothesisAloneConfirmsFirstEqualityAndConditionalSecondPass(int marker, int count, int targetNumber, int secondStart)
    {
        var result = JgtStaticResearchFixture.Analyze(JgtHypothesis.HypotheticalExecutorAND, (byte)marker, new());
        Assert.True(result.ExitReached); Assert.Equal(count, result.Stores.Count);
        Assert.Equal(149, result.PassExitStoreNumbers[0]); Assert.Equal(0x356, result.Stores[148].Address);
        Assert.True(result.Stores[148].Compare.Zf); Assert.False(result.Stores[148].Compare.Cf); Assert.False(result.Stores[148].Taken);
        Assert.Equal(secondStart, result.Stores[149].Address); Assert.Equal(0x98, result.Stores[^1].Address);
        Assert.Equal(0x19A, result.Stores[targetNumber - 1].Address); Assert.Equal(targetNumber, result.Stores.Single(s => s.Address == 0x19A).Number);
        Assert.Equal("ConditionalStaticProof", result.Evidence); Assert.Equal(0, result.ActualRomExecutions);
    }

    [Theory]
    [InlineData(0x46)]
    [InlineData(0x47)]
    public void PrintedOrDoesNotExitAtEqualityAndStopsBeforeActiveUspAlias(int marker)
    {
        var result = JgtStaticResearchFixture.Analyze(JgtHypothesis.HypotheticalPrintedOR, (byte)marker, new());
        Assert.False(result.ExitReached); Assert.Empty(result.PassExitStoreNumbers); Assert.Equal(508, result.Stores.Count);
        Assert.True(result.Stores[148].Compare.Zf); Assert.True(result.Stores[148].Taken);
        Assert.Equal(371, result.Stores.Single(s => s.Address == 0x19A).Number);
        Assert.Equal(0x88, result.Stores[^1].Address); Assert.Equal("BeforeActiveUspAlias", result.Boundary);
    }

    [Fact]
    public void OpaqueJgtBothEdgesGuaranteeColdTargetButNotTermination()
    {
        var stores = JgtStaticResearchFixture.TargetPrefixForOpaqueJgt(0x46, new());
        Assert.Equal(371, stores.Count); Assert.Equal(0x47E, stores[0]); Assert.Equal(0x19A, stores[^1]);
        for (var i = 1; i < stores.Count; i++) Assert.Equal(stores[i - 1] - 2, stores[i]);
        Assert.DoesNotContain(0x98, stores); // Target prefix is not a loop-exit proof.
    }

    [Fact]
    public void WarmOpaqueNotTakenAt02feCanRepeatInsteadOfReachingTarget()
    {
        Assert.Throws<InvalidDataException>(() => JgtStaticResearchFixture.TargetPrefixForOpaqueJgt(0x47, new()));
        ushort dp = 0x300;
        for (var i = 0; i < 3; i++)
        {
            dp = JgtStaticResearchFixture.TwoDecrements(dp); Assert.Equal(0x2FE, dp);
            Assert.True(dp > 0x98); dp = 0x300; // Hypothetical false-GT warm reset edge, not a host/runtime branch.
        }
    }

    [Theory]
    [InlineData(0, 0xFFFE)]
    [InlineData(1, 0xFFFF)]
    [InlineData(0x480, 0x47E)]
    public void TwoWordDecrementsHaveExplicit16BitWrap(int before, int after) =>
        Assert.Equal((ushort)after, JgtStaticResearchFixture.TwoDecrements((ushort)before));

    [Fact]
    public void RegisterBackedSelfAliasCannotBeIgnoredInWrapChronology()
    {
        ushort usp = 0x356, dp = 0x86;
        usp = 0; // Abstract word zero store at activeUSP slot0086.
        Assert.Equal((ushort)0, usp);
        dp = 0x84; dp = 0; // Store at activeDP slot0084 changes the pointer itself.
        Assert.Equal((ushort)0xFFFE, JgtStaticResearchFixture.TwoDecrements(dp));
        Assert.NotEqual((ushort)0x82, JgtStaticResearchFixture.TwoDecrements(dp));
    }

    [Theory]
    [InlineData(0x10, 0, true)]
    [InlineData(0x10, 1, false)]
    [InlineData(0x21, 0, false)]
    public void Off0086MatchesActiveUspOnlyInTheDeclaredPageAndScb(int lrb, int scb, bool same) =>
        Assert.Equal(same, JgtStaticResearchFixture.Off86IsActiveUsp(lrb, scb));

    [Theory]
    [InlineData("LRB")]
    [InlineData("SCB")]
    [InlineData("DD")]
    [InlineData("unownedUSP")]
    [InlineData("unownedMarker")]
    [InlineData("alias")]
    [InlineData("async")]
    [InlineData("storage")]
    public void MissingContextCannotBecomeAProvenNativeInitialization(string missing)
    {
        var context = missing switch
        {
            "LRB" => new LoopResearchContext(Lrb: null),
            "SCB" => new LoopResearchContext(Scb: null),
            "DD" => new LoopResearchContext(Dd: null),
            "unownedUSP" => new LoopResearchContext(NativeUspSource: false),
            "unownedMarker" => new LoopResearchContext(NativeMarkerSource: false),
            "alias" => new LoopResearchContext(UnknownAlias: true),
            "async" => new LoopResearchContext(StableContext: false),
            _ => new LoopResearchContext(ValidWordStorage: false)
        };
        Assert.Throws<InvalidDataException>(() => JgtStaticResearchFixture.Analyze(JgtHypothesis.HypotheticalExecutorAND, 0x46, context));
        Assert.Throws<InvalidDataException>(() => JgtStaticResearchFixture.TargetPrefixForOpaqueJgt(0x46, context));
    }

    [Theory]
    [InlineData((int)JgtHypothesis.HypotheticalPrintedOR)]
    [InlineData((int)JgtHypothesis.HypotheticalExecutorAND)]
    public void EveryHypotheticalResultRejectsPromotionToActualExecution(int hypothesis)
    {
        var result = JgtStaticResearchFixture.Analyze((JgtHypothesis)hypothesis, 0x46, new());
        Assert.Throws<InvalidDataException>(result.RequireActualExecution); Assert.Equal(0, result.ActualRomExecutions);
        Assert.Throws<InvalidDataException>(() => JgtStaticResearchFixture.Predicate((JgtHypothesis)99, new(false, true, false, true)));
    }

    [Theory]
    [InlineData("sameBytes")]
    [InlineData("sameVisuals")]
    [InlineData("otherCore")]
    [InlineData("emulator")]
    [InlineData("mnemonicOnly")]
    public void DuplicateOrCrossFamilyOrNonPrimarySourceDoesNotResolveConflict(string kind)
    {
        var original = new DocumentaryWitness("scan-A", "page-A", "nX-8/200", true, true);
        var candidate = kind switch
        {
            "sameBytes" => original with { VisualIdentity = "other-render" },
            "sameVisuals" => original with { Identity = "other-compression" },
            "otherCore" => new("vendor-500S", "page-500S", "nX-8/500S", true, true, true),
            "emulator" => new("third-party", "derived", "nX-8/200", false, true),
            _ => new DocumentaryWitness("independent-vendor-list", "list-page", "nX-8/200", true, false)
        };
        Assert.False(JgtStaticResearchFixture.CanResolvePrimary(candidate, original));
    }

    [Theory]
    [InlineData("jgtPredicate")]
    [InlineData("assumeGtAnd")]
    [InlineData("jgt2714Branch")]
    [InlineData("primaryGtResolved")]
    [InlineData("cfAt2714")]
    [InlineData("zfAt2714")]
    [InlineData("resetCompleted")]
    [InlineData("force2710")]
    [InlineData("initialUSP0356")]
    [InlineData("nativeZeroOwner")]
    public void HistoricalScenarioRejectsPredicateFlagResetAndOwnerInjection(string field)
    {
        foreach (var level in new[] { "initialState", "calls" })
        {
            var node = JsonNode.Parse(P28Data0136TailTests.Scenario().ToJson())!;
            (level == "calls" ? node[level]![0]! : node[level]!)[field] = 0;
            Assert.Throws<InvalidDataException>(() => P28Data0136TailScenario.Parse(node.ToJsonString()));
        }
    }
}
