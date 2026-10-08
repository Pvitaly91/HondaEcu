namespace HondaEcu.Core.Tests;

public sealed class SspAdcPendingTests
{
    private const string Path = "invented-cold-first-call-path";
    private const string Machine = "invented-symbolic-machine";

    // Source PC/identity and all histories are invented. No startup SSP seed or
    // executable hardware/ROM scenario is supplied by these specifications.
    private static SspDefinition Source(int value = 0x47E) =>
        SspAdcPendingFixture.NativeWriter(0x1100, value, "invented-native-SSP-writer", Path, Machine);
    private static SspConditionalFrame Frame(int value = 0x47E) =>
        SspAdcPendingFixture.ConditionalCal(Source(value), "invented-frame-generation-A");
    private static SspAuxiliarySources ColdSources() => new(true, "invented-target-zero-writer",
        "invented-target-generation", false, "invented-H-zero-writer", "invented-H-generation",
        0, "invented-threshold-zero-writer", "invented-threshold-generation", Path, Machine);
    private static SspAliasEffects Aliases(SspConditionalFrame frame) =>
        SspAdcPendingFixture.AnalyzeAliases(frame, ColdSources());
    private static SspReturnWitness Read(SspConditionalFrame frame) =>
        new(frame.NormalReturnReaderPc, frame.PostCallSsp, frame.Source.Value, frame.Address, 16, frame.ReturnPc,
            frame.LatestStorageWriterPc, frame.StorageGeneration, frame.Source.PathIdentity, frame.Source.MachineIdentity,
            FrameCreatorPc: frame.CallPc, ReturnWordLineage: frame.ReturnWordLineage);
    private static PendingClear Clear(bool? old = null) =>
        SspAdcPendingFixture.ClearIrq4(old, "invented-clear2763", Path, Machine);
    private static PendingFactor Factor(PendingFactorPhase phase = PendingFactorPhase.AfterClearBeforeReader,
        PendingFactorSource source = PendingFactorSource.HypotheticalSamePathAdcSet) =>
        new("invented-ADC-factor-source", Path, Machine, phase, source, "invented-clear2763");

    [Fact]
    public void IndependentNativeWriterOwnsConditionalSspWithoutActualEventOrOrdinal()
    {
        var source = Source();
        Assert.Equal(0x1100, source.WriterPc); Assert.Equal(0x47E, source.Value);
        Assert.Equal(SspProvenanceStatus.NativeSSPWriterProvenWithinDomain, source.Status);
        Assert.Equal("invented-native-SSP-writer", source.SourceIdentity);
        Assert.Null(source.ActualEventIndex); Assert.Null(source.ActualGlobalWriteOrdinal);
        Assert.False(source.IsActualNativeSource);
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(0x10000)]
    public void NativeWriterRejectsValuesOutsideTheWordDomain(int value) =>
        Assert.Throws<InvalidDataException>(() => Source(value));

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    public void IndependentWriterRequiresAnExplicitSymbolicSourceIdentity(string identity) =>
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.NativeWriter(0x1100, 0x47E, identity, Path, Machine));

    [Fact]
    public void UnknownSspDoesNotAcquireASelectedSafeFrameOrKnownAuxiliaries()
    {
        var frame = SspAdcPendingFixture.ConditionalCal(SspAdcPendingFixture.UnknownSource(Path, Machine), "invented-generation");
        Assert.Null(frame.Address); Assert.Null(frame.PostCallSsp);
        Assert.Equal(SspProvenanceStatus.FrameSourceNotEstablished, frame.Status);
        var aliases = Aliases(frame);
        Assert.Null(aliases.TargetDisjoint); Assert.Null(aliases.OldZeroLineageRetained);
        Assert.Null(aliases.SelectorH); Assert.Null(aliases.Threshold);
        Assert.Null(aliases.NewHighByteBit1); Assert.Null(aliases.NewHighByteBit2);
    }

    [Fact]
    public void BoundedKnownNonStackOperationsPreserveTheSameIndependentSspSource()
    {
        var source = Source();
        foreach (var operation in new[] { "invented-local-byte", "invented-disjoint-word", "invented-branch" })
            source = SspAdcPendingFixture.Preserve(source, new(operation));
        Assert.Equal(0x47E, source.Value); Assert.Equal(0x1100, source.WriterPc);
        Assert.Equal("invented-native-SSP-writer", source.SourceIdentity);
        Assert.Equal(SspProvenanceStatus.SSPContinuityConditional, source.Status);
        Assert.Equal("Preserved through invented-branch", source.Frontier);
    }

    [Theory]
    [InlineData("context")]
    [InlineData("SSP-overlap")]
    [InlineData("stack")]
    [InlineData("async")]
    [InlineData("alias")]
    public void EachContinuityBarrierRemovesKnownSspAndCannotBeLaunderedByLaterDisjointOperations(string barrier)
    {
        SspBoundedOperation operation = barrier switch
        {
            "context" => new("first context barrier", ContextEstablished: false),
            "SSP-overlap" => new("first SSP overlap", FootprintDisjointFromSsp: false),
            "stack" => new("first unresolved stack operation", IsNonStack: false),
            "async" => new("first asynchronous entry", NoAsynchronousEntry: false),
            _ => new("first unknown alias", NoUnknownAlias: false)
        };
        var blocked = SspAdcPendingFixture.Preserve(Source(), operation);
        var after = SspAdcPendingFixture.Preserve(blocked, new("later disjoint operation"));
        after = SspAdcPendingFixture.Preserve(after, new("later unresolved stack", IsNonStack: false));
        Assert.Equal(blocked, after); Assert.Null(after.Value);
        Assert.Equal(SspProvenanceStatus.SSPContinuityNotEstablished, after.Status);
        Assert.Null(SspAdcPendingFixture.ConditionalCal(after, "unproved frame").Address);
    }

    [Theory]
    [InlineData(0x47E, 0x47E, 0x47C)]
    [InlineData(0x47F, 0x47E, 0x47D)]
    [InlineData(0, 0, 0xFFFE)]
    [InlineData(1, 0, 0xFFFF)]
    [InlineData(0xFFFF, 0xFFFE, 0xFFFD)]
    public void ConditionalFrameGeometryProjectsAlignmentAndPointerDifferenceWithoutContextAuthority(int ssp, int address, int post)
    {
        var frame = Frame(ssp);
        Assert.Equal(address, frame.Address); Assert.Equal(post, frame.PostCallSsp);
        Assert.Equal(0x276D, frame.ReturnPc); Assert.Equal(0x5C86, frame.TargetPc);
        Assert.Equal(16, frame.Width); Assert.Equal(0, frame.InternalSfAfter);
        Assert.Null(frame.ActualEventIndex); Assert.Null(frame.ActualGlobalWriteOrdinal); Assert.False(frame.IsActualFrame);
    }

    [Fact]
    public void BalancedConditionalCalRtConsumesTheSameWriterGenerationAndRetainsCalleeContext()
    {
        var frame = Frame();
        var returned = SspAdcPendingFixture.MatchNormalReturn(frame, Read(frame));
        Assert.Equal(SspProvenanceStatus.ConditionalNormalReturn, returned.Status);
        Assert.Equal(0x276D, returned.ReturnPc); Assert.Equal(0x47E, returned.SspAfter);
        Assert.Equal(0, returned.InternalSfAfter); Assert.True(returned.RetainsCalleeAccumulator);
        Assert.True(returned.RetainsCalleeLrb); Assert.False(returned.RestoresInterruptContext);
        Assert.False(returned.ActualReturnEstablished); Assert.Equal(0, returned.ActualRomExecutions);
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(false, false)]
    public void IncompleteOrUnreachedCallCannotCreateMatchingReturnAuthority(bool reached, bool written)
    {
        var frame = SspAdcPendingFixture.ConditionalCal(Source(), "incomplete-generation", reached, written);
        Assert.Null(frame.Address); Assert.Null(frame.PostCallSsp); Assert.Null(frame.InternalSfAfter);
        Assert.Equal(SspProvenanceStatus.MatchingNativeReturnNotEstablished,
            SspAdcPendingFixture.MatchNormalReturn(frame, Read(frame)).Status);
    }

    [Theory]
    [InlineData("missing RT")]
    [InlineData("wrong PC")]
    [InlineData("wrong address")]
    [InlineData("wrong width")]
    [InlineData("wrong return word")]
    [InlineData("wrong writer same value")]
    [InlineData("wrong generation same value")]
    [InlineData("frame overwritten same value")]
    [InlineData("unbalanced SSP")]
    [InlineData("wrong post SSP")]
    [InlineData("wrong restored SSP")]
    [InlineData("other path")]
    [InlineData("other machine")]
    [InlineData("host return")]
    public void MatchingNumericalReturnWordCannotSubstituteForCorrectNativeFrameHistory(string defect)
    {
        var frame = Frame();
        var read = Read(frame);
        read = defect switch
        {
            "missing RT" => read with { ReturnReached = false },
            "wrong PC" => read with { ReaderPc = 0x5CCE },
            "wrong address" => read with { Address = 0x47C },
            "wrong width" => read with { Width = 8 },
            "wrong return word" => read with { ReturnWord = 0x276A },
            "wrong writer same value" => read with { WriterPc = 0x1100 },
            "wrong generation same value" => read with { StorageGeneration = "older-same-276D-generation" },
            "frame overwritten same value" => read with { FrameUnchanged = false },
            "unbalanced SSP" => read with { StackProgressionBalanced = false },
            "wrong post SSP" => read with { SspBefore = 0x47A },
            "wrong restored SSP" => read with { SspAfter = 0x47C },
            "other path" => read with { PathIdentity = "other-path" },
            "other machine" => read with { MachineIdentity = "other-machine" },
            _ => read with { ListedConditionalInstruction = false }
        };
        var returned = SspAdcPendingFixture.MatchNormalReturn(frame, read);
        Assert.Equal(SspProvenanceStatus.MatchingNativeReturnNotEstablished, returned.Status);
        Assert.Null(returned.ReturnPc); Assert.Null(returned.SspAfter); Assert.Null(returned.InternalSfAfter);
        Assert.False(returned.ActualReturnEstablished);
    }

    [Fact]
    public void CalAndNormalRtClearOnlyInternalSfAndDoNotRestorePswOrInterruptSnapshot()
    {
        foreach (var bits in Enumerable.Range(0, 32))
        {
            var before = new SspFlagState((bits & 1) != 0, (bits & 2) != 0, (bits & 4) != 0,
                (bits & 8) != 0, (bits & 16) != 0);
            var after = SspAdcPendingFixture.ApplyCalOrRtFlags(before);
            Assert.Equal(before.Cf, after.Cf); Assert.Equal(before.Zf, after.Zf);
            Assert.Equal(before.Hc, after.Hc); Assert.Equal(before.Dd, after.Dd); Assert.False(after.Sf);
        }
    }

    [Theory]
    [InlineData(0x2689, 0x268C)]
    [InlineData(0x268D, 0x2690)]
    public void OwnedExchangeRestoresCalDerivedWordAsFreshStorageGenerationNotUntouchedOriginal(int callPc, int returnPc)
    {
        var frame = SspAdcPendingFixture.ConditionalCal(Source(), "invented-original-call-generation",
            callPc: callPc, targetPc: 0x5C5C, normalReturnReaderPc: 0x5C80);
        var exchanged = SspAdcPendingFixture.BeginOwnedExchange(frame, 0x5C68, "invented-pattern-generation");
        Assert.Equal(returnPc, exchanged.SavedWord);
        Assert.Equal(SspProvenanceStatus.MatchingNativeReturnNotEstablished,
            SspAdcPendingFixture.MatchNormalReturn(exchanged.PatternFrame, Read(exchanged.PatternFrame)).Status);
        var restored = SspAdcPendingFixture.RestoreOwnedExchange(exchanged, 0x5C6C, "invented-restored-generation");
        Assert.Equal(callPc, restored.CallPc); Assert.Equal(0x5C6C, restored.LatestStorageWriterPc);
        Assert.NotEqual(frame.StorageGeneration, restored.StorageGeneration);
        Assert.Equal(frame.ReturnWordLineage, restored.ReturnWordLineage);
        var result = SspAdcPendingFixture.MatchNormalReturn(restored, Read(restored));
        Assert.Equal(SspProvenanceStatus.ConditionalNormalReturn, result.Status);
        Assert.Equal(returnPc, result.ReturnPc); Assert.False(result.ActualReturnEstablished);
    }

    [Theory]
    [InlineData("unowned accumulator")]
    [InlineData("wrong saved word")]
    [InlineData("wrong saved lineage same value")]
    [InlineData("other saved path")]
    [InlineData("other saved machine")]
    [InlineData("wrong current writer")]
    [InlineData("wrong current generation")]
    [InlineData("wrong original creator")]
    public void ExchangeRestorationNeedsSavedCalLineageAndCurrentRestoringWriterNotMerelySameNumber(string defect)
    {
        var frame = SspAdcPendingFixture.ConditionalCal(Source(), "invented-original-generation",
            callPc: 0x2689, targetPc: 0x5C5C, normalReturnReaderPc: 0x5C80);
        var exchange = SspAdcPendingFixture.BeginOwnedExchange(frame, 0x5C68, "invented-test-pattern");
        exchange = defect switch
        {
            "wrong saved word" => exchange with { SavedWord = 0x268D },
            "wrong saved lineage same value" => exchange with { SavedReturnLineage = "unrelated same-value source" },
            "other saved path" => exchange with { PathIdentity = "other-path" },
            "other saved machine" => exchange with { MachineIdentity = "other-machine" },
            _ => exchange
        };
        var restored = SspAdcPendingFixture.RestoreOwnedExchange(exchange, 0x5C6C, "invented-restoration-generation",
            savedAccumulatorLineageEstablished: defect != "unowned accumulator");
        var read = Read(restored);
        read = defect switch
        {
            "wrong current writer" => read with { WriterPc = 0x5C68 },
            "wrong current generation" => read with { StorageGeneration = frame.StorageGeneration },
            "wrong original creator" => read with { FrameCreatorPc = 0x268D },
            _ => read
        };
        Assert.Equal(SspProvenanceStatus.MatchingNativeReturnNotEstablished,
            SspAdcPendingFixture.MatchNormalReturn(restored, read).Status);
    }

    [Fact]
    public void SavedSameReturnWordFromEarlierCallInstanceCannotRestoreALaterCallInstance()
    {
        var earlier = SspAdcPendingFixture.ConditionalCal(Source(), "earlier-CAL-instance");
        var later = SspAdcPendingFixture.ConditionalCal(Source(), "later-CAL-instance");
        Assert.Equal(earlier.ReturnPc, later.ReturnPc); Assert.NotEqual(earlier.ReturnWordLineage, later.ReturnWordLineage);
        var exchange = SspAdcPendingFixture.BeginOwnedExchange(earlier, 0x1110, "earlier-pattern") with
        {
            OriginalFrame = later,
            PatternFrame = SspAdcPendingFixture.BeginOwnedExchange(later, 0x1110, "later-pattern").PatternFrame
        };
        var restored = SspAdcPendingFixture.RestoreOwnedExchange(exchange, 0x1120, "attempted-old-source-restore");
        Assert.Null(restored.CurrentStoredWord);
        Assert.Equal(SspProvenanceStatus.MatchingNativeReturnNotEstablished,
            SspAdcPendingFixture.MatchNormalReturn(restored, Read(restored)).Status);
    }

    [Theory]
    [InlineData(0x19A)]
    [InlineData(0x230)]
    [InlineData(0x25A)]
    public void PatternOrUnownedRestoreCannotUseLogicalReturnMetadataAsTheCurrentStoredWord(int ssp)
    {
        var frame = Frame(ssp);
        var exchange = SspAdcPendingFixture.BeginOwnedExchange(frame, 0x1110, "invented-unrelated-pattern");
        var unowned = SspAdcPendingFixture.RestoreOwnedExchange(exchange, 0x1120, "unowned-same-number",
            savedAccumulatorLineageEstablished: false);
        foreach (var current in new[] { exchange.PatternFrame, unowned })
        {
            Assert.Equal(0x276D, current.ReturnPc); Assert.Null(current.CurrentStoredWord);
            var effects = Aliases(current);
            Assert.Null(effects.TargetDisjoint); Assert.Null(effects.OldZeroLineageRetained);
            Assert.Null(effects.SelectorH); Assert.Null(effects.Threshold);
            Assert.Null(effects.NewHighByteBit1); Assert.Null(effects.NewHighByteBit2);
        }
    }

    [Theory]
    [InlineData(0x19A)]
    [InlineData(0x19B)]
    public void TargetWordFrameInvalidatesOldZeroLineageAndCreatesNewConditionalHigh27BitSources(int encoded)
    {
        var frame = Frame(encoded);
        var effects = Aliases(frame);
        Assert.Equal(0x19A, effects.ProjectedFrameAddress); Assert.False(effects.TargetDisjoint);
        Assert.False(effects.OldZeroLineageRetained); Assert.True(effects.NewHighByteBit1);
        Assert.True(effects.NewHighByteBit2); Assert.Equal(0x6D, frame.ReturnPc & 255);
        Assert.Equal(0x27, frame.ReturnPc >> 8);
        Assert.Contains(frame.StorageGeneration, effects.TargetStorageGeneration);
        Assert.Equal(SspProvenanceStatus.KnownFrameOverwrite, effects.Status);
        Assert.False(effects.IsActualRuntimeOwner);
    }

    [Theory]
    [InlineData(0x230)]
    [InlineData(0x231)]
    public void AuxiliaryFrameLow6dChangesResetH0ToConditionalFrameInducedH1(int encoded)
    {
        var effects = Aliases(Frame(encoded));
        Assert.True(effects.TargetDisjoint); Assert.True(effects.OldZeroLineageRetained);
        Assert.True(effects.SelectorH); Assert.Equal(0, effects.Threshold);
        Assert.Null(effects.NewHighByteBit1); Assert.Null(effects.NewHighByteBit2);
    }

    [Theory]
    [InlineData(0x25A)]
    [InlineData(0x25B)]
    public void ThresholdFrameChangesWordTo276dWithoutInventingH1(int encoded)
    {
        var effects = Aliases(Frame(encoded));
        Assert.True(effects.TargetDisjoint); Assert.False(effects.SelectorH);
        Assert.Equal(0x276D, effects.Threshold);
        var pending = SspAdcPendingFixture.AnalyzePending(Clear(), null);
        var decision = SspAdcPendingFixture.HelperDecision(effects, 0x100, pending);
        Assert.Equal((0x100 - 0x276D) & 0xFFFF, SspAdcPendingFixture.ConditionalDifference(0x100, effects.Threshold!.Value));
        Assert.Null(decision.Difference); // H0 does not execute this timer read/CMP.
        Assert.Equal(SspHelperRoute.FaultBrkConditional, decision.Route);
    }

    [Fact]
    public void OneAlignedTwoByteFrameCannotOverwriteBothAuxiliaryWords()
    {
        foreach (var encoded in Enumerable.Range(0, 65536))
        {
            var effects = Aliases(Frame(encoded));
            Assert.False(effects.SelectorH == true && effects.Threshold == 0x276D);
        }
    }

    [Theory]
    [InlineData(0x47E)]
    [InlineData(0x19A)]
    [InlineData(0x230)]
    [InlineData(0x25A)]
    public void UnknownEntireAliasContextKeepsEffectsUnknownEvenWithProjectedKnownFrameAddress(int ssp)
    {
        var frame = SspAdcPendingFixture.ConditionalCal(Source(ssp), "known-projection-unknown-domain",
            entireAliasDomainEstablished: false);
        var effects = Aliases(frame);
        Assert.Equal(ssp, effects.ProjectedFrameAddress); Assert.Null(effects.TargetDisjoint);
        Assert.Null(effects.OldZeroLineageRetained); Assert.Null(effects.SelectorH); Assert.Null(effects.Threshold);
        Assert.Null(effects.NewHighByteBit1); Assert.Null(effects.NewHighByteBit2);
        Assert.Equal(SspProvenanceStatus.PossibleAliasUnresolved, effects.Status);
        Assert.Equal(SspProvenanceStatus.MatchingNativeReturnNotEstablished,
            SspAdcPendingFixture.MatchNormalReturn(frame, Read(frame)).Status);
    }

    [Fact]
    public void KnownSspAloneDoesNotOwnIndependentTargetZeroHOrThresholdSources()
    {
        var unknownSources = new SspAuxiliarySources(null, null, null, null, null, null,
            null, null, null, Path, Machine);
        var effects = SspAdcPendingFixture.AnalyzeAliases(Frame(), unknownSources);
        Assert.True(effects.TargetDisjoint); // Footprint geometry only.
        Assert.Null(effects.OldZeroLineageRetained); Assert.Null(effects.TargetStorageGeneration);
        Assert.Null(effects.SelectorH); Assert.Null(effects.SelectorSourceIdentity);
        Assert.Null(effects.SelectorStorageGeneration); Assert.Null(effects.Threshold);
        Assert.Null(effects.ThresholdSourceIdentity); Assert.Null(effects.ThresholdStorageGeneration);
        var decision = SspAdcPendingFixture.HelperDecision(effects, 0,
            SspAdcPendingFixture.AnalyzePending(Clear(), null));
        Assert.Equal(SspHelperRoute.Unknown, decision.Route);
    }

    [Theory]
    [InlineData(false, (int)SspHelperRoute.FaultBrkConditional)]
    [InlineData(true, (int)SspHelperRoute.AdcBodyConditional)]
    public void IndependentlyKnownH0DoesNotRequireUnknownThresholdOrTargetZeroProofForItsListedRoute(bool fresh, int route)
    {
        var independentH0 = ColdSources() with
        {
            TargetZeroOwned = null,
            TargetSourceIdentity = null,
            TargetStorageGeneration = null,
            Threshold = null,
            ThresholdSourceIdentity = null,
            ThresholdStorageGeneration = null
        };
        var effects = SspAdcPendingFixture.AnalyzeAliases(Frame(), independentH0);
        Assert.False(effects.SelectorH); Assert.Equal("invented-H-zero-writer", effects.SelectorSourceIdentity);
        Assert.Null(effects.Threshold); Assert.Null(effects.OldZeroLineageRetained);
        var decision = SspAdcPendingFixture.HelperDecision(effects, null,
            SspAdcPendingFixture.AnalyzePending(Clear(), fresh ? Factor() : null));
        Assert.Equal((SspHelperRoute)route, decision.Route); Assert.Null(decision.Difference);
        Assert.False(decision.NativeRtCompleted);
    }

    [Fact]
    public void IndependentlyKnownH1StillRequiresIndependentThresholdSourceForTimerComparison()
    {
        var h1UnknownThreshold = ColdSources() with
        {
            SelectorH = true,
            SelectorSourceIdentity = "invented-independent-H1-writer",
            Threshold = null,
            ThresholdSourceIdentity = null,
            ThresholdStorageGeneration = null
        };
        var effects = SspAdcPendingFixture.AnalyzeAliases(Frame(), h1UnknownThreshold);
        var decision = SspAdcPendingFixture.HelperDecision(effects, 0,
            SspAdcPendingFixture.AnalyzePending(Clear(), Factor()));
        Assert.Equal(SspHelperRoute.Unknown, decision.Route); Assert.Null(decision.Difference);
    }

    [Theory]
    [InlineData("path")]
    [InlineData("machine")]
    [InlineData("missing H identity")]
    [InlineData("missing threshold generation")]
    public void IndependentAuxiliaryValuesNeedTheirOwnMatchingSourceIdentityGenerationAndHistory(string defect)
    {
        var sources = ColdSources();
        sources = defect switch
        {
            "path" => sources with { PathIdentity = "other-path" },
            "machine" => sources with { MachineIdentity = "other-machine" },
            "missing H identity" => sources with { SelectorSourceIdentity = null },
            _ => sources with { ThresholdStorageGeneration = "" }
        };
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.AnalyzeAliases(Frame(), sources));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    [InlineData(0x7E)]
    [InlineData(0x7F)]
    public void SystemControlFrameFootprintCannotLaunderSspLrbOrPswClobberIntoSafeHelperContext(int encoded)
    {
        var frame = Frame(encoded);
        Assert.Equal(encoded & 0xFFFE, frame.Address); Assert.False(frame.ContextEstablishedAfterFrame);
        Assert.Equal(SspProvenanceStatus.PossibleAliasUnresolved, frame.Status);
        var effects = Aliases(frame);
        Assert.Null(effects.SelectorH); Assert.Null(effects.Threshold); Assert.Null(effects.OldZeroLineageRetained);
        var decision = SspAdcPendingFixture.HelperDecision(effects, null,
            SspAdcPendingFixture.AnalyzePending(Clear(), Factor()));
        Assert.Equal(SspHelperRoute.Unknown, decision.Route);
        Assert.Equal(SspProvenanceStatus.MatchingNativeReturnNotEstablished,
            SspAdcPendingFixture.MatchNormalReturn(frame, Read(frame)).Status);
    }

    [Fact]
    public void ImplicitIrqUsesEightBytesRatherThanOrdinaryCalTwoByteFrame()
    {
        var cal = SspAdcPendingFixture.StackFootprint(0x47E, false);
        var irq = SspAdcPendingFixture.StackFootprint(0x47E, true);
        Assert.Equal(new[] { 0x47E }, cal.WordAddresses); Assert.Equal(0x47C, cal.PostSsp); Assert.Equal(2, cal.ByteWidth);
        Assert.Equal(new[] { 0x47E, 0x47C, 0x47A, 0x478 }, irq.WordAddresses);
        Assert.Equal(0x476, irq.PostSsp); Assert.Equal(8, irq.ByteWidth);
    }

    [Theory]
    [InlineData(0x19A)]
    [InlineData(0x19C)]
    [InlineData(0x19E)]
    [InlineData(0x1A0)]
    public void SingleIrqFrameCanOverlapTargetAtFourDifferentStartingWords(int oldSsp) =>
        Assert.Contains(0x19A, SspAdcPendingFixture.StackFootprint(oldSsp, true).WordAddresses);

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(null, null)]
    public void Irq4ClearReadsOldBitForZfAndLeavesNewBitZero(bool? old, bool? zf)
    {
        var clear = Clear(old);
        Assert.Equal(old, clear.OldBit); Assert.Equal(zf, clear.Zf); Assert.False(clear.NewBit);
        Assert.Equal(PendingProvenanceStatus.SoftwareClearEstablished, clear.Status);
        Assert.Null(clear.ActualEventIndex);
    }

    [Fact]
    public void StalePreClearPendingCannotSupplyThePostClearReader()
    {
        var pending = SspAdcPendingFixture.AnalyzePending(Clear(true), Factor(PendingFactorPhase.BeforeClear));
        Assert.False(pending.OldBit); Assert.True(pending.RbZf); Assert.False(pending.NewBit);
        Assert.False(pending.ConditionalFreshSource); Assert.Equal("invented-clear2763", pending.SourceIdentity);
    }

    [Fact]
    public void HypotheticalFreshPostClearFactorSuppliesOnlyConditionalOldBitAndNoObservedEvent()
    {
        var pending = SspAdcPendingFixture.AnalyzePending(Clear(true), Factor());
        Assert.True(pending.OldBit); Assert.False(pending.RbZf); Assert.False(pending.NewBit);
        Assert.True(pending.ConditionalFreshSource); Assert.True(pending.HardwareSetSpecifiedArchitecturally);
        Assert.False(pending.HardwareEventObserved); Assert.False(pending.PendingStateAtReaderEstablished);
        Assert.False(pending.InterruptDelivered); Assert.Null(pending.ActualEventIndex); Assert.Null(pending.ActualGlobalWriteOrdinal);
    }

    [Fact]
    public void FreshFactorIsBoundToTheExactClearIntervalNotMerelySamePathAndMachine()
    {
        var laterClear = Clear() with { ClearIdentity = "invented-second-clear2763" };
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.AnalyzePending(laterClear, Factor()));
        var rebound = Factor() with { ClearIntervalIdentity = laterClear.ClearIdentity };
        var conditional = SspAdcPendingFixture.AnalyzePending(laterClear, rebound);
        Assert.True(conditional.OldBit); Assert.False(conditional.HardwareEventObserved);
    }

    [Theory]
    [InlineData("missing source")]
    [InlineData("missing clear interval")]
    public void PendingFactorRequiresAnIndependentSourceIdentityAndExactIntervalIdentity(string defect)
    {
        var factor = Factor();
        factor = defect == "missing source" ? factor with { SourceIdentity = "" } :
            factor with { ClearIntervalIdentity = " " };
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.AnalyzePending(Clear(), factor));
    }

    [Fact]
    public void DocumentedPossibleAdcSetWithoutObservedHistoryDoesNotCreateReaderBit()
    {
        var pending = SspAdcPendingFixture.AnalyzePending(Clear(), Factor(source: PendingFactorSource.DocumentedAdcPossibility));
        Assert.Null(pending.OldBit); Assert.Null(pending.RbZf);
        Assert.True(pending.HardwareSetSpecifiedArchitecturally); Assert.False(pending.ConditionalFreshSource);
        Assert.False(pending.HardwareEventObserved); Assert.False(pending.InterruptDelivered);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void UnknownEventPhaseOrIntervalCannotBeConvertedToKnownPending(bool unknownInterval)
    {
        var pending = SspAdcPendingFixture.AnalyzePending(Clear(),
            Factor(unknownInterval ? PendingFactorPhase.AfterClearBeforeReader : PendingFactorPhase.Unknown),
            intervalAndAliasesEstablished: !unknownInterval);
        Assert.Null(pending.OldBit); Assert.Null(pending.RbZf); Assert.False(pending.ConditionalFreshSource);
        Assert.False(pending.HardwareEventObserved);
    }

    [Fact]
    public void IncompleteOrHostChangedClearDoesNotEstablishAnIntervalBeginningAtZero()
    {
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.AnalyzePending(Clear() with { NewBit = true }, null));
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.AnalyzePending(Clear() with
        { Status = PendingProvenanceStatus.PendingStateAtReaderNotEstablished }, null));
    }

    [Fact]
    public void H0WithNoFreshPendingTakesFaultMarkerAndBrkNotNormalRt()
    {
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(Frame()), null,
            SspAdcPendingFixture.AnalyzePending(Clear(), null));
        Assert.Equal(SspHelperRoute.FaultBrkConditional, decision.Route); Assert.True(decision.FreshPendingNecessary);
        Assert.Null(decision.Difference); Assert.Contains("BRK system-reset", decision.EarliestDependency);
        Assert.False(decision.NativeRtCompleted); Assert.Equal(0, decision.ActualRomExecutions);
        Assert.Equal(0x5CCE, 0x5CA3 + 2 + 0x29); Assert.NotEqual(0x5CCD, 0x5CA3 + 2 + 0x29);
    }

    [Fact]
    public void H0FreshPendingIsNecessaryButNotSufficientForP2BodyOrNativeReturn()
    {
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(Frame()), null,
            SspAdcPendingFixture.AnalyzePending(Clear(), Factor()));
        Assert.Equal(SspHelperRoute.AdcBodyConditional, decision.Route); Assert.True(decision.FreshPendingNecessary);
        Assert.Contains("P2/ADC/indexed", decision.EarliestDependency); Assert.False(decision.NativeRtCompleted);
        Assert.False(decision.SameMachineRuntimeHistoryEstablished);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(0xC7)]
    [InlineData(0xC8)]
    [InlineData(0xFFFF)]
    public void H0BypassesTimerAndThresholdRegardlessOfAnOfferedAbstractNumber(int offeredTimer)
    {
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(Frame(0x25A)), offeredTimer,
            SspAdcPendingFixture.AnalyzePending(Clear(), null));
        Assert.Null(decision.Difference); Assert.Equal(SspHelperRoute.FaultBrkConditional, decision.Route);
    }

    [Theory]
    [InlineData(0, (int)SspHelperRoute.TimerConditional)]
    [InlineData(0xC7, (int)SspHelperRoute.TimerConditional)]
    [InlineData(0xC8, (int)SspHelperRoute.FaultBrkConditional)]
    [InlineData(0xFFFF, (int)SspHelperRoute.FaultBrkConditional)]
    public void FrameInducedH1UsesExactUnsignedThresholdAndDoesNotInheritH0PendingNecessity(int timer, int expected)
    {
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(Frame(0x230)), timer,
            SspAdcPendingFixture.AnalyzePending(Clear(), null));
        Assert.Equal((SspHelperRoute)expected, decision.Route); Assert.Equal(timer, decision.Difference);
        Assert.Equal(timer >= 0xC8, decision.FreshPendingNecessary); Assert.False(decision.NativeRtCompleted);
    }

    [Fact]
    public void H1WithoutTimerProvenanceIsUnknownEvenIfPendingCouldBeFresh()
    {
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(Frame(0x230)), null,
            SspAdcPendingFixture.AnalyzePending(Clear(), Factor()));
        Assert.Equal(SspHelperRoute.Unknown, decision.Route); Assert.Null(decision.Difference);
        Assert.Contains("Timer sample", decision.EarliestDependency); Assert.False(decision.NativeRtCompleted);
        Assert.Null(decision.FreshPendingNecessary);
    }

    [Fact]
    public void H1FailedTimerComparisonStillNeedsFreshPendingForItsAdcFallbackRoute()
    {
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(Frame(0x230)), 0xC8,
            SspAdcPendingFixture.AnalyzePending(Clear(), Factor()));
        Assert.Equal(SspHelperRoute.AdcBodyConditional, decision.Route); Assert.True(decision.FreshPendingNecessary);
        Assert.False(decision.NativeRtCompleted);
    }

    [Fact]
    public void UnknownSspHOrPendingCannotChooseAFavorableReturnPath()
    {
        var frame = SspAdcPendingFixture.ConditionalCal(SspAdcPendingFixture.UnknownSource(Path, Machine), "unknown-frame");
        var pending = SspAdcPendingFixture.AnalyzePending(Clear(), Factor(source: PendingFactorSource.DocumentedAdcPossibility));
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(frame), null, pending);
        Assert.Equal(SspHelperRoute.Unknown, decision.Route); Assert.Null(decision.FreshPendingNecessary);
        Assert.Null(decision.Difference); Assert.False(decision.NativeRtCompleted);
    }

    [Fact]
    public void KnownH0ButUnknownPendingKeepsNecessaryEventSeparateFromReaderState()
    {
        var decision = SspAdcPendingFixture.HelperDecision(Aliases(Frame()), null,
            SspAdcPendingFixture.AnalyzePending(Clear(), Factor(PendingFactorPhase.Unknown)));
        Assert.Equal(SspHelperRoute.Unknown, decision.Route); Assert.True(decision.FreshPendingNecessary);
        Assert.Contains("RB5CA0", decision.EarliestDependency);
    }

    [Fact]
    public void AllInventedP2BytesGiveBoundedIndexesWithoutEstablishingAPeripheralRead()
    {
        foreach (var p2 in Enumerable.Range(0, 256))
        {
            var index = SspAdcPendingFixture.ConditionalP2Index((byte)p2, true);
            Assert.Equal((p2 >> 5) & 7, index); Assert.InRange(index!.Value, 0, 7);
            Assert.InRange(0x3CE + index.Value, 0x3CE, 0x3D5);
            Assert.InRange(0x3C6 + index.Value, 0x3C6, 0x3CD);
        }
        Assert.Null(SspAdcPendingFixture.ConditionalP2Index(null, true));
        Assert.Null(SspAdcPendingFixture.ConditionalP2Index(0xE0, false));
    }

    [Theory]
    [InlineData("other-path")]
    [InlineData("other-machine")]
    [InlineData("host-IRQ")]
    [InlineData("imported-factor")]
    public void PendingProvenanceRejectsCrossHistorySecondMachineAndHostInjection(string defect)
    {
        var factor = Factor();
        factor = defect switch
        {
            "other-path" => factor with { PathIdentity = "incompatible-path" },
            "other-machine" => factor with { MachineIdentity = "second-machine" },
            "host-IRQ" => factor with { Source = PendingFactorSource.HostPatch },
            _ => factor with { Source = PendingFactorSource.ImportedMachine }
        };
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.AnalyzePending(Clear(), factor));
    }

    [Theory]
    [InlineData("explicit mixed control-flow")]
    [InlineData("pending from other path")]
    [InlineData("pending from other machine")]
    public void AuxiliaryAndPendingProofsMustBelongToTheSameCorrelatedPath(string defect)
    {
        var aliases = Aliases(Frame());
        var pending = SspAdcPendingFixture.AnalyzePending(Clear(), Factor());
        if (defect == "pending from other path") pending = pending with { PathIdentity = "second-path" };
        if (defect == "pending from other machine") pending = pending with { MachineIdentity = "second-machine" };
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.HelperDecision(aliases, null, pending,
            correlatedPathEstablished: defect != "explicit mixed control-flow"));
    }

    [Theory]
    [InlineData("same-word owner", null, null, false, false)]
    [InlineData("forged-event", 12, null, false, false)]
    [InlineData("forged-global-ordinal", null, 371L, false, false)]
    [InlineData("second-machine", 1, 1L, false, false)]
    [InlineData("host IRQ patch", null, null, true, false)]
    [InlineData("fake RT", null, null, false, true)]
    public void StaticPossibilityCannotBePromotedToActualOwnerEventIrqOrReturn(string machine,
        int? eventIndex, long? ordinal, bool hostIrq, bool hostReturn)
    {
        var frame = Frame();
        var returned = SspAdcPendingFixture.MatchNormalReturn(frame, Read(frame));
        Assert.Throws<InvalidDataException>(() => SspAdcPendingFixture.RequireActualExecution(returned,
            machine, eventIndex, ordinal, hostIrq, hostReturn));
        Assert.False(returned.ActualReturnEstablished); Assert.Null(frame.ActualEventIndex);
        Assert.Null(frame.ActualGlobalWriteOrdinal); Assert.Equal(0, returned.ActualRomExecutions);
    }
}
