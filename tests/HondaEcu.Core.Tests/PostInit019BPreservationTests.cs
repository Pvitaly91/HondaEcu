namespace HondaEcu.Core.Tests;

public sealed class PostInit019BPreservationTests
{
    // All generic ownership effects below use invented source/storage addresses.
    private static PostInitBitOwner Source(int bit = 1) =>
        PostInit019BPreservationFixture.WordZeroSource(0x1100, 0x2A0, bit);

    [Theory]
    [InlineData(1, 9)]
    [InlineData(2, 10)]
    public void IndependentWordZeroDefinesExactHighByteBitWithoutActualOrdinal(int bit, int wordBit)
    {
        var owner = Source(bit);
        Assert.Equal(0x1100, owner.SourcePc); Assert.Equal(0x2A1, owner.StorageAddress);
        Assert.Equal(bit, owner.Bit); Assert.Equal(16, owner.SourceStorageWidth);
        Assert.Contains($"WordBit{wordBit}", owner.SourceLineage);
        Assert.NotEmpty(owner.PathConditions); Assert.NotEmpty(owner.PreservationInterval);
        Assert.False(owner.NumericValue); Assert.Null(owner.ActualEventIndex);
        Assert.Null(owner.ActualGlobalWriteOrdinal); Assert.False(owner.IsActualRuntimeOwner);
        Assert.Equal(PostInitPreservationStatus.CurrentRuntimeOwnerNotEstablished, owner.RuntimeStatus);
        Assert.Equal(PostInitPreservationStatus.ConditionalCodeOwnedStore, owner.Status);
    }

    [Fact]
    public void StaticSourceCandidateDoesNotClaimAReachedStoreOrKnownCurrentBit()
    {
        var candidate = PostInit019BPreservationFixture.SourceCandidate(0x1100, 0x2A0, 1);
        Assert.Equal(PostInitPreservationStatus.StaticSourceCandidate, candidate.Status);
        Assert.Null(candidate.NumericValue); Assert.Equal("No reached source store", candidate.PreservationInterval);
        Assert.False(candidate.IsActualRuntimeOwner);
    }

    [Theory]
    [InlineData((int)PostInitPreservationStatus.StaticSourceCandidate)]
    [InlineData((int)PostInitPreservationStatus.InvalidatedByKnownWrite)]
    [InlineData((int)PostInitPreservationStatus.PossibleAliasUnresolved)]
    [InlineData((int)PostInitPreservationStatus.ExternalEffectBoundary)]
    public void LaterDisjointWriteCannotLaunderAnUnprovedOrInvalidatedSource(int status)
    {
        var blocked = Source() with
        {
            Status = (PostInitPreservationStatus)status,
            PreservationInterval = "Earlier proof already stopped"
        };
        var after = PostInit019BPreservationFixture.ApplyKnownWrite(blocked, 0x300, 8, "later-disjoint");
        Assert.Equal(blocked.Status, after.Status); Assert.Equal(blocked.PreservationInterval, after.PreservationInterval);
    }

    [Theory]
    [InlineData((int)PostInitPreservationStatus.StaticSourceCandidate)]
    [InlineData((int)PostInitPreservationStatus.InvalidatedByKnownWrite)]
    [InlineData((int)PostInitPreservationStatus.PossibleAliasUnresolved)]
    [InlineData((int)PostInitPreservationStatus.ExternalEffectBoundary)]
    public void LaterAliasAndExternalBoundaryCannotReplaceTheEarliestStoppedFrontier(int status)
    {
        var earliest = Source() with
        {
            Status = (PostInitPreservationStatus)status,
            PreservationInterval = "Earlier proof already stopped"
        };
        var later = PostInit019BPreservationFixture.CrossBoundary(
            PostInit019BPreservationFixture.PossibleAlias(earliest, "later alias"), "later external effect");
        Assert.Equal(earliest.Status, later.Status); Assert.Equal(earliest.PreservationInterval, later.PreservationInterval);
    }

    [Fact]
    public void FirstAliasOrExternalEffectKeepsItsFrontierAcrossTheLaterHazardChain()
    {
        var alias = PostInit019BPreservationFixture.PossibleAlias(Source(), "first alias");
        var afterAlias = PostInit019BPreservationFixture.CrossBoundary(
            PostInit019BPreservationFixture.PossibleAlias(alias, "second alias"), "later external effect");
        Assert.Equal(alias.Status, afterAlias.Status); Assert.Equal(alias.PreservationInterval, afterAlias.PreservationInterval);
        var external = PostInit019BPreservationFixture.CrossBoundary(Source(), "first external effect");
        var afterExternal = PostInit019BPreservationFixture.PossibleAlias(
            PostInit019BPreservationFixture.CrossBoundary(external, "second external effect"), "later alias");
        Assert.Equal(external.Status, afterExternal.Status); Assert.Equal(external.PreservationInterval, afterExternal.PreservationInterval);
    }

    [Theory]
    [InlineData(1, false)]
    [InlineData(1, true)]
    [InlineData(2, false)]
    [InlineData(2, true)]
    public void Bit0ReadModifyWriteRetainsEachIndependentBitLineage(int bit, bool bit0)
    {
        var old = Source(bit);
        var after = PostInit019BPreservationFixture.ApplyKnownWrite(old, 0x2A1, 8,
            "invented-bit0-RMW", 0, bit0);
        Assert.Equal(PostInitPreservationStatus.PreservedWithinAuditedDomain, after.Status);
        Assert.Equal(old.SourceLineage, after.SourceLineage); Assert.False(after.NumericValue);
        Assert.NotEqual(old.SymbolicStorageGeneration, after.SymbolicStorageGeneration);
    }

    [Theory]
    [InlineData(0x2A0)]
    [InlineData(0x2A1)]
    public void DataWordEncodingAlignsAndInvalidatesBothOverlappedOwners(int encodedAddress)
    {
        foreach (var bit in new[] { 1, 2 })
        {
            var after = PostInit019BPreservationFixture.ApplyKnownWrite(Source(bit), encodedAddress,
                16, "invented-word-overwrite");
            Assert.Equal(PostInitPreservationStatus.InvalidatedByKnownWrite, after.Status);
        }
    }

    [Theory]
    [InlineData(8)]
    [InlineData(16)]
    public void SameValueCompleteWriteCreatesFreshStorageGenerationNotRetainedOldOwner(int width)
    {
        var old = Source();
        var after = PostInit019BPreservationFixture.ApplyKnownWrite(old, width == 8 ? 0x2A1 : 0x2A0,
            width, "invented-same-value-zero", writtenBit: false);
        Assert.False(after.NumericValue); Assert.Equal(old.SourceLineage, after.SourceLineage);
        Assert.Equal(PostInitPreservationStatus.InvalidatedByKnownWrite, after.Status);
        Assert.NotEqual(old.SymbolicStorageGeneration, after.SymbolicStorageGeneration);
        var repeated = PostInit019BPreservationFixture.ApplyKnownWrite(after, width == 8 ? 0x2A1 : 0x2A0,
            width, "invented-same-value-zero", writtenBit: false);
        Assert.NotEqual(after.SymbolicStorageGeneration, repeated.SymbolicStorageGeneration);
        Assert.Equal(PostInitPreservationStatus.InvalidatedByKnownWrite, repeated.Status);
        var fresh = PostInit019BPreservationFixture.WordZeroSource(0x1110, 0x2A0, 1);
        Assert.NotEqual(old.SourcePc, fresh.SourcePc); Assert.NotEqual(old.SourceLineage, fresh.SourceLineage);
    }

    [Theory]
    [InlineData(0x29F, 8)]
    [InlineData(0x2A0, 8)]
    [InlineData(0x2A2, 16)]
    public void KnownDisjointByteAndWordFootprintsRetainSource(int address, int width)
    {
        var old = Source();
        var after = PostInit019BPreservationFixture.ApplyKnownWrite(old, address, width, "invented-disjoint");
        Assert.Equal(PostInitPreservationStatus.PreservedWithinAuditedDomain, after.Status);
        Assert.Equal(old.SymbolicStorageGeneration, after.SymbolicStorageGeneration);
    }

    [Fact]
    public void PossibleAliasStopsProofWithoutClaimingAnObservedOverwrite()
    {
        var old = Source();
        var after = PostInit019BPreservationFixture.PossibleAlias(old, "unknown indexed target");
        Assert.Equal(PostInitPreservationStatus.PossibleAliasUnresolved, after.Status);
        Assert.Equal(old.SymbolicStorageGeneration, after.SymbolicStorageGeneration);
        Assert.Equal(old.NumericValue, after.NumericValue); Assert.Null(after.ActualEventIndex);
    }

    [Theory]
    [InlineData(null, (int)PostInitPreservationStatus.PossibleAliasUnresolved)]
    [InlineData(2, (int)PostInitPreservationStatus.InvalidatedByKnownWrite)]
    [InlineData(3, (int)PostInitPreservationStatus.PreservedWithinAuditedDomain)]
    public void SameOffsetNeedsActualPageContextForConditionalAlias(int? page, int status)
    {
        var after = PostInit019BPreservationFixture.ApplyPageByteWrite(Source(), page, 0xA1);
        Assert.Equal((PostInitPreservationStatus)status, after.Status);
    }

    [Theory]
    [InlineData(null, (int)PostInitPreservationStatus.PossibleAliasUnresolved)]
    [InlineData(0x2A0, (int)PostInitPreservationStatus.InvalidatedByKnownWrite)]
    [InlineData(0x700, (int)PostInitPreservationStatus.PreservedWithinAuditedDomain)]
    public void NativeCallFrameRequiresAddressIdentityRatherThanSelectedSafeStack(int? oldSsp, int status)
    {
        var after = PostInit019BPreservationFixture.ApplyCallFrame(Source(), oldSsp);
        Assert.Equal((PostInitPreservationStatus)status, after.Status);
        Assert.Null(after.ActualGlobalWriteOrdinal);
    }

    [Theory]
    [InlineData(0x2A1, (int)PostInitPreservationStatus.InvalidatedByKnownWrite)]
    [InlineData(0x701, (int)PostInitPreservationStatus.PreservedWithinAuditedDomain)]
    [InlineData(0, (int)PostInitPreservationStatus.PreservedWithinAuditedDomain)]
    [InlineData(1, (int)PostInitPreservationStatus.PreservedWithinAuditedDomain)]
    [InlineData(0xFFFE, (int)PostInitPreservationStatus.PreservedWithinAuditedDomain)]
    [InlineData(0xFFFF, (int)PostInitPreservationStatus.PreservedWithinAuditedDomain)]
    public void ConditionalFrameFootprintAlignsKnown16BitAddressWithoutProvingNativeValidity(int encoded, int status)
    {
        var frame = PostInit019BPreservationFixture.ApplyCallFrame(Source(), encoded);
        var ordinarySystemWord = PostInit019BPreservationFixture.ApplyKnownWrite(Source(), encoded, 16, "independent-word");
        Assert.Equal((PostInitPreservationStatus)status, frame.Status); Assert.Equal(ordinarySystemWord.Status, frame.Status);
        var helperEncoded = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(encoded, false, true);
        var helperEven = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(encoded & 0xFFFE, false, true);
        Assert.Equal(helperEven, helperEncoded); Assert.False(helperEncoded.NormalReturnEstablished);
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(0x10000)]
    public void ConditionalFrameFootprintRejectsNon16BitAddresses(int address)
    {
        Assert.Throws<InvalidDataException>(() => PostInit019BPreservationFixture.ApplyCallFrame(Source(), address));
        Assert.Throws<InvalidDataException>(() => PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(address, false, true));
        Assert.Throws<InvalidDataException>(() => PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(address, false, false));
    }

    [Fact]
    public void OpaqueTailRetainsEveryKnownPostTargetWordFootprintAndBothEdges()
    {
        var audit = PostInit019BPreservationFixture.AnalyzeOpaqueTail(new());
        var addresses = audit.States.Select(s => s.PhysicalStoreAddress).Distinct().ToArray();
        var independentlySpecified = Enumerable.Range(0, 140).Select(i => 0x19A - 2 * i).ToArray();
        Assert.Equal(independentlySpecified, addresses);
        Assert.All(addresses.Skip(1), a => Assert.True(a + 1 < 0x19A));
        foreach (var bit in new[] { 1, 2 })
        {
            var owner = PostInit019BPreservationFixture.WordZeroSource(0x1100, 0x19A, bit);
            foreach (var address in addresses.Skip(1))
                owner = PostInit019BPreservationFixture.ApplyKnownWrite(owner, address, 16, "abstract-posttarget-word");
            Assert.Equal(PostInitPreservationStatus.PreservedWithinAuditedDomain, owner.Status);
            Assert.False(owner.NumericValue); Assert.Equal(0x1100, owner.SourcePc);
            Assert.Null(owner.ActualGlobalWriteOrdinal);
        }
        Assert.All(audit.States, state =>
        {
            Assert.Equal(2, audit.Edges.Count(e => e.State == state));
            Assert.Contains(audit.Edges, e => e.State == state && e.Taken);
            Assert.Contains(audit.Edges, e => e.State == state && !e.Taken);
            Assert.False(state.Cf && state.Zf);
        });
        Assert.Equal("ConditionalStaticProof", audit.Classification); Assert.Equal(0, audit.ActualRomExecutions);
    }

    [Fact]
    public void ConditionalFirstExitHasExactlyTheCorrelatedReachingPairsNotTermination()
    {
        var audit = PostInit019BPreservationFixture.AnalyzeOpaqueTail(new());
        var expected = Enumerable.Range(0, 9).SelectMany(i => new[]
            { (0x98 - 2 * i, 0x356), (0x98 - 2 * i, 0x98) })
            .Concat(new[] { (0x86, 0), (0, 0) }).OrderBy(p => p.Item1).ThenBy(p => p.Item2).ToArray();
        var actual = audit.Exits.Select(s => (s.Dp, s.Usp)).Distinct()
            .OrderBy(p => p.Dp).ThenBy(p => p.Usp).ToArray();
        Assert.Equal(expected, actual);
        Assert.All(audit.Exits, s => PostInit019BPreservationFixture.RequireCorrelatedExit(audit, s));
        Assert.Contains(audit.Edges, e => e.Taken && e.State.Dp == 0x98 && !e.Exit272A);
    }

    [Fact]
    public void ActivePointerSelfStoresChangeComparedValuesWithoutWritingSavedR3()
    {
        var audit = PostInit019BPreservationFixture.AnalyzeOpaqueTail(new());
        Assert.All(audit.States.Where(s => s.PhysicalStoreAddress == 0x86), s =>
        { Assert.Equal(0x86, s.Dp); Assert.Equal(0, s.Usp); Assert.False(s.Cf); Assert.False(s.Zf); });
        Assert.All(audit.States.Where(s => s.PhysicalStoreAddress == 0x84), s =>
        { Assert.Equal(0, s.Dp); Assert.Equal(0, s.Usp); Assert.True(s.Zf); Assert.Equal(0x84, s.HcSourcePhysicalStore); });
        Assert.All(audit.Edges.Where(e => e.State.PhysicalStoreAddress == 0x84 && e.Taken),
            e => Assert.Equal(0xFFFE, e.NextPhysicalStore));
        Assert.DoesNotContain(audit.States, s => s.PhysicalStoreAddress == 0x82);
        Assert.DoesNotContain(audit.States, s => s.PhysicalStoreAddress == 0xFFFE);
        Assert.Equal(0xFFFE, audit.FirstUnverifiedProposedStore);
    }

    [Theory]
    [InlineData("pointer")]
    [InlineData("history")]
    [InlineData("flags")]
    [InlineData("hc-source")]
    public void MutuallyExclusivePathComponentsCannotBeSplicedIntoAnExit(string splice)
    {
        var audit = PostInit019BPreservationFixture.AnalyzeOpaqueTail(new());
        var valid = audit.Exits.First(s => s.PhysicalStoreAddress == 0x88 && s.Usp == 0x356);
        var bad = splice switch
        {
            "pointer" => valid with { Usp = 0 },
            "history" => valid with { History = PostInitHistory.PriorFallthroughAbove0098 },
            "flags" => valid with { Cf = false, Zf = true },
            _ => valid with { HcSourcePhysicalStore = 0x84 }
        };
        Assert.Throws<InvalidDataException>(() => PostInit019BPreservationFixture.RequireCorrelatedExit(audit, bad));
    }

    [Theory]
    [InlineData("source")]
    [InlineData("page")]
    [InlineData("scb")]
    [InlineData("dd")]
    [InlineData("stack-mode")]
    [InlineData("marker")]
    [InlineData("async")]
    [InlineData("memory")]
    [InlineData("alias")]
    public void EachUnprovedDomainDependencyStopsTheOpaquePreservationTheorem(string missing)
    {
        PostInitLoopDomain domain = missing switch
        {
            "source" => new PostInitLoopDomain(SourceReached: false),
            "page" => new(Lrb: null),
            "scb" => new(Scb: null),
            "dd" => new(WordAccumulator: false),
            "stack-mode" => new(NonStackAccumulator: false),
            "marker" => new(OwnedNon47Marker: false),
            "async" => new(StableContext: false),
            "memory" => new(ValidFixedWordDomain: false),
            _ => new(UnknownAlias: true)
        };
        Assert.Throws<InvalidDataException>(() => PostInit019BPreservationFixture.AnalyzeOpaqueTail(domain));
    }

    [Fact]
    public void InventedStartupWritesRetainSourceUntilFirstExternalEffectBoundary()
    {
        var owner = Source();
        foreach (var address in new[] { 0x120, 0x360, 0x71, 0x302, 0x180, 0x391, 0x240, 0x87 })
            owner = PostInit019BPreservationFixture.ApplyKnownWrite(owner, address, 8, "invented-startup-write");
        Assert.Equal(PostInitPreservationStatus.PreservedWithinAuditedDomain, owner.Status);
        var boundary = PostInit019BPreservationFixture.CrossBoundary(owner, "ST IE2759 external/control effects");
        Assert.Equal(PostInitPreservationStatus.ExternalEffectBoundary, boundary.Status);
        Assert.False(boundary.NumericValue); Assert.False(boundary.IsActualRuntimeOwner);
    }

    [Theory]
    [InlineData(0x230, 296)]
    [InlineData(0x25A, 275)]
    [InlineData(0x19A, 371)]
    public void AuxiliaryZeroPositionsAreConditionalStaticCountsNeverActualWriteOrdinals(int address, int position)
    {
        Assert.Equal(position, PostInit019BPreservationFixture.StaticClearPosition(address));
        Assert.Null(Source().ActualGlobalWriteOrdinal);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void SelectorBit3ZeroSurvivesEitherBit5CarryWrite(bool carry)
    {
        var after = PostInit019BPreservationFixture.WriteSelectedBit(0, 5, carry);
        Assert.Equal(carry ? 0x20 : 0, after); Assert.Equal(0, after & 8);
    }

    [Fact]
    public void ConditionalInheritedNativeFrame47ePreservesTargetAndAuxiliaryZeroSources()
    {
        var abstractReturnWord = 0x276D; // Abstract CAL form arithmetic, not an inserted frame.
        Assert.Equal(0x276A + 3, abstractReturnWord);
        Assert.Equal(0x47C, 0x47E - 2); Assert.Equal(0x47E, 0x47C + 2);
        var summary = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(0x47E, false, true);
        Assert.True(summary.TargetFrameDisjoint); Assert.False(summary.SelectorBit3);
        Assert.True(summary.ThresholdStillZero); Assert.False(summary.NormalReturnEstablished);
    }

    [Theory]
    [InlineData(0x230, true, true)]
    [InlineData(0x231, true, true)]
    [InlineData(0x25A, false, false)]
    [InlineData(0x25B, false, false)]
    public void TargetDisjointFrameCanInvalidateOneAuxiliarySourceButNotBoth(int frame, bool selector, bool thresholdZero)
    {
        var summary = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(frame, false, true);
        Assert.True(summary.TargetFrameDisjoint); Assert.Equal(selector, summary.SelectorBit3);
        Assert.Equal(thresholdZero, summary.ThresholdStillZero);
        Assert.False(summary.NormalReturnEstablished);
    }

    [Theory]
    [InlineData(null, true)]
    [InlineData(0x47E, false)]
    public void UnknownFrameOrAliasDomainKeepsAllAuxiliaryProofFieldsUnknown(int? frame, bool aliasesEstablished)
    {
        var unknown = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(frame, false, aliasesEstablished);
        Assert.Equal("PossibleAliasUnresolved", unknown.Boundary);
        Assert.Null(unknown.SelectorBit3); Assert.Null(unknown.ThresholdStillZero);
        Assert.Null(unknown.TargetFrameDisjoint); Assert.Null(unknown.FreshFactorNecessary);
        Assert.False(unknown.NormalReturnEstablished);
    }

    [Fact]
    public void KnownAlignedTargetFrameInvalidatesPreservationForEitherEncodedLowBit()
    {
        foreach (var encoded in new[] { 0x19A, 0x19B })
        {
            var target = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(encoded, false, true);
            Assert.Equal("InvalidatedByKnownWrite", target.Boundary); Assert.False(target.TargetFrameDisjoint);
        }
    }

    [Fact]
    public void NoFreshExternalIrqFactorAfterCallerClearTakesFaultNotRt()
    {
        var summary = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(0x47E, false, true);
        Assert.False(summary.SelectorBit3); Assert.True(summary.FreshFactorNecessary);
        Assert.Equal("ConditionalFault5CCE_BRK_NotRT", summary.Boundary);
        Assert.Equal(0x5CCE, 0x5CA3 + 2 + 0x29); // Exact signed relative arithmetic.
        Assert.NotEqual(0x5CCD, 0x5CA3 + 2 + 0x29);
        Assert.False(summary.NormalReturnEstablished); Assert.Equal(0, summary.ActualRomExecutions);
    }

    [Fact]
    public void FreshFactorAloneDoesNotProveReturnInterruptDeliveryOrMachineHistory()
    {
        var summary = PostInit019BPreservationFixture.AnalyzeCorrelatedFirstHelper(0x47E, true, true);
        Assert.True(summary.FreshFactorNecessary);
        Assert.Equal("FreshFactorNecessaryNotSufficientForNativeReturn", summary.Boundary);
        Assert.False(summary.NormalReturnEstablished); Assert.False(summary.InterruptDeliveryEstablished);
        Assert.False(summary.SameMachineReaderHistoryEstablished);
    }

    [Theory]
    [InlineData(false, false, false, false, "ControlFlowNotEstablished")]
    [InlineData(false, false, false, true, "ControlFlowNotEstablished")]
    [InlineData(false, false, true, false, "ControlFlowNotEstablished")]
    [InlineData(false, false, true, true, "ControlFlowNotEstablished")]
    [InlineData(false, true, false, false, "ExternalInterruptDeliveryRequired")]
    [InlineData(false, true, false, true, "ExternalInterruptDeliveryRequired")]
    [InlineData(false, true, true, false, "ExternalInterruptDeliveryRequired")]
    [InlineData(false, true, true, true, "ExternalInterruptDeliveryRequired")]
    [InlineData(true, false, false, false, "FrameContextNotEstablished")]
    [InlineData(true, false, false, true, "FrameContextNotEstablished")]
    [InlineData(true, false, true, false, "ActualSameMachineHistoryNotEstablished")]
    [InlineData(true, false, true, true, "SourcePreservationConditional")]
    [InlineData(true, true, false, false, "ExternalInterruptDeliveryRequired")]
    [InlineData(true, true, false, true, "ExternalInterruptDeliveryRequired")]
    [InlineData(true, true, true, false, "ExternalInterruptDeliveryRequired")]
    [InlineData(true, true, true, true, "ExternalInterruptDeliveryRequired")]
    public void StaticHandoffMapSeparatesSoftwareEdgeDeliveryFrameAndIdentity(bool software,
        bool external, bool frame, bool machine, string expected) =>
        Assert.Equal(expected, PostInit019BPreservationFixture.ClassifyHandoff(software, external, frame, machine));

    [Theory]
    [InlineData("synthetic-reset-to-ISR", null, null)]
    [InlineData("different-machine", 9, 371L)]
    [InlineData("claimed-M2ah-machine", null, 371L)]
    [InlineData("known-numeric-zero", 371, null)]
    public void StaticZeroCannotBePromotedToActualM2ahOwnerUsingInventedIdentityOrOrdinal(
        string machine, int? eventIndex, long? ordinal)
    {
        Assert.Throws<InvalidDataException>(() => PostInit019BPreservationFixture.RequireActualRuntimeOwner(
            Source(), machine, eventIndex, ordinal));
        Assert.Null(Source().ActualEventIndex); Assert.Null(Source().ActualGlobalWriteOrdinal);
    }

    [Theory]
    [InlineData("CAL/RT not established")]
    [InlineData("peripheral update unknown")]
    [InlineData("implicit interrupt frame possible overlap")]
    [InlineData("nested IRQ context/page change")]
    public void UnresolvedContinuationNeverExtendsStaticPreservationIntoFirstReader(string missing)
    {
        var owner = PostInit019BPreservationFixture.CrossBoundary(Source(2), missing);
        Assert.Equal(PostInitPreservationStatus.ExternalEffectBoundary, owner.Status);
        Assert.Throws<InvalidDataException>(() => PostInit019BPreservationFixture.RequireActualRuntimeOwner(owner, "same-name-not-history"));
    }
}
