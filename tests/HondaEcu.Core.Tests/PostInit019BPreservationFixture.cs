namespace HondaEcu.Core.Tests;

// Isolated specification mathematics. No CPU/Bus, operation, firmware bytes,
// observation-derived expected result, actual event, or global native ordinal.
internal enum PostInitPreservationStatus
{
    StaticSourceCandidate,
    ConditionalCodeOwnedStore,
    PreservedWithinAuditedDomain,
    InvalidatedByKnownWrite,
    PossibleAliasUnresolved,
    ExternalEffectBoundary,
    CurrentRuntimeOwnerNotEstablished
}

internal sealed record PostInitBitOwner(int SourcePc, int StorageAddress, int Bit,
    int SourceStorageWidth, string SourceLineage, string PathConditions,
    string PreservationInterval, string SymbolicStorageGeneration,
    PostInitPreservationStatus Status, bool? NumericValue = false)
{
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
    internal bool IsActualRuntimeOwner => false;
    internal PostInitPreservationStatus RuntimeStatus => PostInitPreservationStatus.CurrentRuntimeOwnerNotEstablished;
}

internal sealed record PostInitLoopDomain(bool SourceReached = true, int? Lrb = 0x10,
    int? Scb = 0, bool WordAccumulator = true, bool NonStackAccumulator = true,
    bool OwnedNon47Marker = true, bool StableContext = true,
    bool ValidFixedWordDomain = true, bool UnknownAlias = false);
internal enum PostInitHistory { AllPriorOpaqueTaken, PriorFallthroughAbove0098 }
internal sealed record PostInitOpaqueState(int PhysicalStoreAddress, int Dp, int Usp,
    bool Cf, bool Zf, int HcSourcePhysicalStore, PostInitHistory History);
internal sealed record PostInitOpaqueEdge(PostInitOpaqueState State, bool Taken,
    bool Exit272A, int? NextPhysicalStore, int NextUsp, PostInitHistory NextHistory);
internal sealed record PostInitLoopAudit(IReadOnlyList<PostInitOpaqueState> States,
    IReadOnlyList<PostInitOpaqueEdge> Edges, IReadOnlyList<PostInitOpaqueState> Exits)
{
    internal int ActualRomExecutions => 0;
    internal string Classification => "ConditionalStaticProof";
    internal int FirstUnverifiedProposedStore => 0xFFFE;
}

internal sealed record PostInitHelperSummary(bool? SelectorBit3, bool? ThresholdStillZero,
    bool? TargetFrameDisjoint, bool? FreshFactorNecessary, string Boundary)
{
    internal bool NormalReturnEstablished => false;
    internal bool InterruptDeliveryEstablished => false;
    internal bool SameMachineReaderHistoryEstablished => false;
    internal int ActualRomExecutions => 0;
}

internal static class PostInit019BPreservationFixture
{
    internal static PostInitBitOwner SourceCandidate(int sourcePc, int wordAddress, int highByteBit) =>
        WordZeroSource(sourcePc, wordAddress, highByteBit) with
        {
            Status = PostInitPreservationStatus.StaticSourceCandidate,
            NumericValue = null,
            PathConditions = "Source reach not established",
            PreservationInterval = "No reached source store"
        };

    internal static PostInitBitOwner WordZeroSource(int sourcePc, int wordAddress, int highByteBit)
    {
        RequireAddress(wordAddress);
        if ((wordAddress & 1) != 0 || highByteBit is not (1 or 2))
            throw new InvalidDataException("An aligned word source and exact high-byte bit are required.");
        return new(sourcePc, wordAddress + 1, highByteBit, 16,
            $"IndependentWordZeroAt{sourcePc:X4}:WordBit{8 + highByteBit}",
            "Reached source; native word zero; fixed address/context; no unknown effects",
            $"Source{sourcePc:X4} through source store", "symbolic-source-generation",
            PostInitPreservationStatus.ConditionalCodeOwnedStore);
    }

    internal static PostInitBitOwner ApplyKnownWrite(PostInitBitOwner owner, int encodedAddress,
        int width, string writer, int? selectedBit = null, bool? writtenBit = null)
    {
        RequireAddress(encodedAddress);
        if (width is not (8 or 16) || selectedBit is < 0 or > 7 ||
            (selectedBit is not null && width != 8))
            throw new InvalidDataException("Unknown storage form.");
        var start = width == 16 ? encodedAddress & 0xFFFE : encodedAddress;
        var overlaps = owner.StorageAddress >= start && owner.StorageAddress < start + width / 8;
        var writesOwnedBit = overlaps && (selectedBit is null || selectedBit == owner.Bit);
        var retentionProved = owner.Status is PostInitPreservationStatus.ConditionalCodeOwnedStore or
            PostInitPreservationStatus.PreservedWithinAuditedDomain;
        return owner with
        {
            Status = writesOwnedBit ? PostInitPreservationStatus.InvalidatedByKnownWrite :
                retentionProved ? PostInitPreservationStatus.PreservedWithinAuditedDomain : owner.Status,
            NumericValue = writesOwnedBit ? writtenBit : owner.NumericValue,
            SymbolicStorageGeneration = overlaps ? $"{owner.SymbolicStorageGeneration}->fresh:{writer}" : owner.SymbolicStorageGeneration,
            PreservationInterval = writesOwnedBit ? $"Stops before {writer}" :
                retentionProved ? $"Preserved through {writer}" : owner.PreservationInterval
        };
    }

    internal static PostInitBitOwner PossibleAlias(PostInitBitOwner owner, string reason) =>
        RetentionProved(owner) ? owner with
        {
            Status = PostInitPreservationStatus.PossibleAliasUnresolved,
            PreservationInterval = $"Stops before unresolved {reason}"
        } : owner;

    internal static PostInitBitOwner ApplyPageByteWrite(PostInitBitOwner owner, int? page, byte offset)
    {
        if (page is null) return PossibleAlias(owner, "page-context write");
        if (page is < 0 or > 255) throw new InvalidDataException("Invalid page.");
        return ApplyKnownWrite(owner, (page.Value << 8) | offset, 8, "conditional-page-byte");
    }

    internal static PostInitBitOwner ApplyCallFrame(PostInitBitOwner owner, int? oldSsp)
    {
        if (oldSsp is null) return PossibleAlias(owner, "native CAL frame address");
        RequireAddress(oldSsp.Value);
        // Pure conditional system-word footprint: encoded odd addresses align
        // to the preceding even address. Frame identity/balance is NOT proved.
        return ApplyKnownWrite(owner, oldSsp.Value, 16, "conditional-native-CAL-frame");
    }

    internal static PostInitBitOwner CrossBoundary(PostInitBitOwner owner, string boundary) =>
        RetentionProved(owner) ? owner with
        {
            Status = PostInitPreservationStatus.ExternalEffectBoundary,
            PreservationInterval = $"Stops before {boundary}"
        } : owner;

    internal static void RequireActualRuntimeOwner(PostInitBitOwner owner, string claimedMachine,
        int? claimedEvent = null, long? claimedOrdinal = null) =>
        throw new InvalidDataException("Static lineage/numeric zero cannot establish actual same-machine runtime ownership.");

    internal static void RequireLoopDomain(PostInitLoopDomain domain)
    {
        if (!domain.SourceReached || domain.Lrb != 0x10 || domain.Scb != 0 ||
            !domain.WordAccumulator || !domain.NonStackAccumulator || !domain.OwnedNon47Marker ||
            !domain.StableContext || !domain.ValidFixedWordDomain || domain.UnknownAlias)
            throw new InvalidDataException("Unproved target source, memory, or correlated native context.");
    }

    internal static PostInitLoopAudit AnalyzeOpaqueTail(PostInitLoopDomain domain)
    {
        RequireLoopDomain(domain);
        var heads = new HashSet<(int Usp, PostInitHistory History)>
        {
            (0x356, PostInitHistory.AllPriorOpaqueTaken),
            (0x98, PostInitHistory.PriorFallthroughAbove0098)
        };
        var states = new List<PostInitOpaqueState>();
        var edges = new List<PostInitOpaqueEdge>();
        var exits = new List<PostInitOpaqueState>();
        for (var physical = 0x19A; physical >= 0x84; physical -= 2)
        {
            var next = new HashSet<(int Usp, PostInitHistory History)>();
            foreach (var head in heads.OrderBy(h => h.Usp).ThenBy(h => h.History))
            {
                var dp = physical == 0x84 ? 0 : physical;
                var usp = physical == 0x86 ? 0 : head.Usp;
                var state = new PostInitOpaqueState(physical, dp, usp,
                    dp < usp, dp == usp, physical, head.History);
                states.Add(state);
                var nextStore = (dp - 2) & 0xFFFF;
                edges.Add(new(state, true, false, nextStore, usp, head.History));
                if (physical != 0x84) next.Add((usp, head.History));
                if (dp <= 0x98)
                {
                    exits.Add(state);
                    edges.Add(new(state, false, true, null, usp, head.History));
                }
                else
                {
                    // Native JLE false -> USP0098 -> owned r3!=47 JNE backedge.
                    edges.Add(new(state, false, false, nextStore, 0x98,
                        PostInitHistory.PriorFallthroughAbove0098));
                    next.Add((0x98, PostInitHistory.PriorFallthroughAbove0098));
                }
            }
            heads = next;
        }
        return new(states, edges, exits);
    }

    internal static void RequireCorrelatedExit(PostInitLoopAudit audit, PostInitOpaqueState proposed)
    {
        if (!audit.Exits.Contains(proposed))
            throw new InvalidDataException("A mixed, stale, or non-exit correlated state is not a reaching witness.");
    }

    internal static int StaticClearPosition(int wordAddress)
    {
        if ((wordAddress & 1) != 0 || wordAddress is < 0x19A or > 0x47E)
            throw new InvalidDataException("Address outside proved conditional prefix.");
        return (0x480 - wordAddress) / 2; // Static position, NEVER actual machine write ordinal.
    }

    internal static byte WriteSelectedBit(byte old, int bit, bool carry)
    {
        if (bit is < 0 or > 7) throw new InvalidDataException("Invalid bit.");
        return (byte)((old & ~(1 << bit)) | (carry ? 1 << bit : 0));
    }

    internal static PostInitHelperSummary AnalyzeCorrelatedFirstHelper(int? frameAddress,
        bool freshExternalFactor, bool entireAliasDomainEstablished)
    {
        if (frameAddress is not null) RequireAddress(frameAddress.Value);
        if (frameAddress is null || !entireAliasDomainEstablished)
            return new(null, null, null, null, "PossibleAliasUnresolved");
        var ea = frameAddress.Value & 0xFFFE;
        var targetDisjoint = ea != 0x19A;
        // CAL276A returns276D. A frame at0230 changes selector bit3 via low6D;
        // a frame at025A changes threshold only. These are exclusive aliases.
        var selector = ea == 0x230 && (0x6D & (1 << 3)) != 0;
        var thresholdZero = ea != 0x25A;
        if (!targetDisjoint) return new(selector, thresholdZero, false, false, "InvalidatedByKnownWrite");
        if (selector) return new(true, thresholdZero, true, false, "ConditionalTimerRouteRequiresPeripheralAndNativeReturnProof");
        // Caller RB2763 clears IRQ4. With no fresh external update, helper RB
        // observes OLD0, sets ZF1; JEQ5CA3 goes to5CCE (fault), not RT5CCD.
        return new(false, thresholdZero, true, true, freshExternalFactor ?
            "FreshFactorNecessaryNotSufficientForNativeReturn" : "ConditionalFault5CCE_BRK_NotRT");
    }

    internal static string ClassifyHandoff(bool softwareEdgeKnown, bool externalDeliveryRequired,
        bool frameEstablished, bool sameMachineHistoryEstablished)
    {
        if (externalDeliveryRequired) return "ExternalInterruptDeliveryRequired";
        if (!softwareEdgeKnown) return "ControlFlowNotEstablished";
        if (!frameEstablished) return "FrameContextNotEstablished";
        if (!sameMachineHistoryEstablished) return "ActualSameMachineHistoryNotEstablished";
        return "SourcePreservationConditional"; // Still only a static dependency classification.
    }

    private static bool RetentionProved(PostInitBitOwner owner) =>
        owner.Status is PostInitPreservationStatus.ConditionalCodeOwnedStore or
            PostInitPreservationStatus.PreservedWithinAuditedDomain;

    private static void RequireAddress(int address)
    {
        if (address is < 0 or > 65535) throw new InvalidDataException("Invalid data address.");
    }
}
