namespace HondaEcu.Core.Tests;

// Invented specification mathematics only. These records are conditional proof
// objects, never Cpu/Bus state, source permissions, or actual native observations.
internal enum SspProvenanceStatus
{
    NativeSSPWriterProvenWithinDomain,
    SSPContinuityConditional,
    SSPContinuityNotEstablished,
    FrameSourceNotEstablished,
    DisjointProvenWithinDomain,
    PossibleAliasUnresolved,
    KnownFrameOverwrite,
    MatchingNativeReturnNotEstablished,
    ConditionalNormalReturn
}

internal sealed record SspDefinition(int WriterPc, int? Value, string SourceIdentity,
    string PathIdentity, string MachineIdentity, SspProvenanceStatus Status, string Frontier)
{
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
    internal bool IsActualNativeSource => false;
}

internal sealed record SspBoundedOperation(string Name, bool ContextEstablished = true,
    bool FootprintDisjointFromSsp = true, bool IsNonStack = true,
    bool NoAsynchronousEntry = true, bool NoUnknownAlias = true);

internal sealed record SspConditionalFrame(SspDefinition Source, int CallPc, int TargetPc,
    int ReturnPc, int Width, int? Address, int? PostCallSsp, string StorageGeneration,
    bool CallReached, bool WriteCompleted, bool EntireAliasDomainEstablished,
    SspProvenanceStatus Status, int LatestStorageWriterPc, string ReturnWordLineage,
    int NormalReturnReaderPc, string CreatorStorageGeneration, int? CurrentStoredWord)
{
    internal int? InternalSfAfter => CallReached && WriteCompleted ? 0 : null;
    internal bool ContextEstablishedAfterFrame => Address is >= 0x80 && EntireAliasDomainEstablished;
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
    internal bool IsActualFrame => false;
}

internal sealed record SspAliasEffects(int? ProjectedFrameAddress, bool? TargetDisjoint,
    bool? OldZeroLineageRetained, bool? NewHighByteBit1, bool? NewHighByteBit2,
    bool? SelectorH, int? Threshold, string? TargetStorageGeneration,
    string? SelectorSourceIdentity, string? SelectorStorageGeneration,
    string? ThresholdSourceIdentity, string? ThresholdStorageGeneration,
    string PathIdentity, string MachineIdentity, SspProvenanceStatus Status)
{
    internal bool IsActualRuntimeOwner => false;
}

internal sealed record SspAuxiliarySources(bool? TargetZeroOwned, string? TargetSourceIdentity,
    string? TargetStorageGeneration, bool? SelectorH, string? SelectorSourceIdentity,
    string? SelectorStorageGeneration, int? Threshold, string? ThresholdSourceIdentity,
    string? ThresholdStorageGeneration, string PathIdentity, string MachineIdentity);

internal sealed record SspReturnWitness(int ReaderPc, int? SspBefore, int? SspAfter,
    int? Address, int Width, int? ReturnWord, int WriterPc, string StorageGeneration,
    string PathIdentity, string MachineIdentity, bool ReturnReached = true,
    bool FrameUnchanged = true, bool StackProgressionBalanced = true,
    bool ListedConditionalInstruction = true, int FrameCreatorPc = 0x276A,
    string ReturnWordLineage = "");

internal sealed record SspOwnedExchange(SspConditionalFrame OriginalFrame,
    SspConditionalFrame PatternFrame, int? SavedWord, string SavedReturnLineage,
    string PathIdentity, string MachineIdentity);

internal sealed record SspConditionalReturn(SspProvenanceStatus Status, int? ReturnPc,
    int? SspAfter, int? InternalSfAfter, bool RetainsCalleeAccumulator,
    bool RetainsCalleeLrb, bool RestoresInterruptContext)
{
    internal bool ActualReturnEstablished => false;
    internal int ActualRomExecutions => 0;
}

internal sealed record SspFlagState(bool Cf, bool Zf, bool Hc, bool Dd, bool Sf);
internal sealed record SspStackFootprint(IReadOnlyList<int> WordAddresses,
    int PostSsp, int ByteWidth);

internal enum PendingFactorPhase { BeforeClear, AfterClearBeforeReader, Unknown }
internal enum PendingFactorSource { DocumentedAdcPossibility, HypotheticalSamePathAdcSet, HostPatch, ImportedMachine }
internal enum PendingProvenanceStatus
{
    SoftwareClearEstablished,
    HardwareSetSpecifiedArchitecturally,
    ExternalPendingEventNotObserved,
    PendingStateConditional,
    PendingStateAtReaderNotEstablished
}

internal sealed record PendingFactor(string SourceIdentity, string PathIdentity,
    string MachineIdentity, PendingFactorPhase Phase, PendingFactorSource Source,
    string ClearIntervalIdentity);
internal sealed record PendingClear(bool? OldBit, bool? Zf, bool? NewBit,
    string ClearIdentity, string PathIdentity, string MachineIdentity,
    PendingProvenanceStatus Status)
{
    internal int? ActualEventIndex => null;
}
internal sealed record PendingAtReader(bool? OldBit, bool? RbZf, bool? NewBit,
    bool SoftwareClearEstablished, bool HardwareSetSpecifiedArchitecturally,
    bool ConditionalFreshSource, string? SourceIdentity, string PathIdentity,
    string MachineIdentity, PendingProvenanceStatus Status)
{
    internal bool HardwareEventObserved => false;
    internal bool PendingStateAtReaderEstablished => false;
    internal bool InterruptDelivered => false;
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
}

internal enum SspHelperRoute { TimerConditional, AdcBodyConditional, FaultBrkConditional, Unknown }
internal sealed record SspHelperDecision(SspHelperRoute Route, int? Difference,
    bool? FreshPendingNecessary, string EarliestDependency)
{
    internal bool NativeRtCompleted => false;
    internal bool SameMachineRuntimeHistoryEstablished => false;
    internal int ActualRomExecutions => 0;
}

internal static class SspAdcPendingFixture
{
    internal static SspDefinition NativeWriter(int writerPc, int value,
        string sourceIdentity, string pathIdentity, string machineIdentity)
    {
        RequireWord(value);
        RequireIdentity(sourceIdentity, pathIdentity, machineIdentity);
        return new(writerPc, value, sourceIdentity, pathIdentity, machineIdentity,
            SspProvenanceStatus.NativeSSPWriterProvenWithinDomain, $"Conditional native writer {writerPc:X4}");
    }

    internal static SspDefinition UnknownSource(string path, string machine) =>
        new(0, null, "SSP source not established", path, machine,
            SspProvenanceStatus.SSPContinuityNotEstablished, "Source not established");

    internal static SspDefinition Preserve(SspDefinition source, SspBoundedOperation operation)
    {
        if (!HasSspProof(source)) return source; // Earliest barrier is monotonic.
        if (!operation.ContextEstablished || !operation.FootprintDisjointFromSsp ||
            !operation.IsNonStack || !operation.NoAsynchronousEntry || !operation.NoUnknownAlias)
            return source with
            {
                Value = null,
                Status = SspProvenanceStatus.SSPContinuityNotEstablished,
                Frontier = $"Stops before {operation.Name}"
            };
        return source with
        {
            Status = SspProvenanceStatus.SSPContinuityConditional,
            Frontier = $"Preserved through {operation.Name}"
        };
    }

    internal static SspConditionalFrame ConditionalCal(SspDefinition source, string generation,
        bool callReached = true, bool writeCompleted = true, bool entireAliasDomainEstablished = true,
        int callPc = 0x276A, int targetPc = 0x5C86, int normalReturnReaderPc = 0x5CCD)
    {
        RequireIdentity(generation);
        var known = HasSspProof(source) && callReached && writeCompleted;
        var address = known ? Even(source.Value!.Value) : (int?)null;
        var post = known ? Wrap(source.Value!.Value - 2) : (int?)null;
        var status = !known ? SspProvenanceStatus.FrameSourceNotEstablished :
            !entireAliasDomainEstablished || address < 0x80 ? SspProvenanceStatus.PossibleAliasUnresolved :
            address == 0x19A ? SspProvenanceStatus.KnownFrameOverwrite :
            SspProvenanceStatus.DisjointProvenWithinDomain;
        // Exact forms are scalar metadata, not OEM bytes or an executable scenario.
        return new(source, callPc, targetPc, Wrap(callPc + 3), 16, address, post,
            generation, callReached, writeCompleted, entireAliasDomainEstablished, status,
            callPc, CalLineage(source, callPc, generation), normalReturnReaderPc,
            generation, known ? Wrap(callPc + 3) : null);
    }

    internal static SspOwnedExchange BeginOwnedExchange(SspConditionalFrame frame,
        int exchangeWriterPc, string patternGeneration)
    {
        RequireIdentity(patternGeneration);
        var sourceKnown = frame.Address is not null && frame.WriteCompleted &&
            frame.CurrentStoredWord == frame.ReturnPc &&
            frame.ReturnWordLineage == CalLineage(frame.Source, frame.CallPc, frame.CreatorStorageGeneration);
        var pattern = frame with
        {
            StorageGeneration = patternGeneration,
            LatestStorageWriterPc = exchangeWriterPc,
            ReturnWordLineage = "Unrelated test-pattern lineage",
            CurrentStoredWord = null
        };
        return new(frame, pattern, sourceKnown ? frame.ReturnPc : null,
            frame.ReturnWordLineage, frame.Source.PathIdentity, frame.Source.MachineIdentity);
    }

    internal static SspConditionalFrame RestoreOwnedExchange(SspOwnedExchange exchange,
        int restoreWriterPc, string restoredGeneration, bool savedAccumulatorLineageEstablished = true)
    {
        RequireIdentity(restoredGeneration);
        var original = exchange.OriginalFrame;
        var restored = savedAccumulatorLineageEstablished && exchange.SavedWord == original.ReturnPc &&
            exchange.SavedReturnLineage == CalLineage(original.Source, original.CallPc, original.CreatorStorageGeneration) &&
            exchange.PatternFrame.CreatorStorageGeneration == original.CreatorStorageGeneration &&
            exchange.PathIdentity == original.Source.PathIdentity && exchange.MachineIdentity == original.Source.MachineIdentity;
        return exchange.PatternFrame with
        {
            StorageGeneration = restoredGeneration,
            LatestStorageWriterPc = restoreWriterPc,
            ReturnWordLineage = restored ? exchange.SavedReturnLineage : "Restored numerical word without CAL lineage",
            CurrentStoredWord = restored ? exchange.SavedWord : null
        };
    }

    internal static SspAliasEffects AnalyzeAliases(SspConditionalFrame frame, SspAuxiliarySources sources)
    {
        RequireAuxiliarySources(sources, frame.Source);
        if (frame.Address is null || !frame.CallReached || !frame.WriteCompleted ||
            !frame.ContextEstablishedAfterFrame || frame.CurrentStoredWord != frame.ReturnPc ||
            frame.ReturnWordLineage != CalLineage(frame.Source, frame.CallPc, frame.CreatorStorageGeneration))
            return new(frame.Address, null, null, null, null, null, null, null,
                null, null, null, null,
                frame.Source.PathIdentity, frame.Source.MachineIdentity,
                frame.Address is null ? SspProvenanceStatus.FrameSourceNotEstablished :
                SspProvenanceStatus.PossibleAliasUnresolved);
        var target = frame.Address == 0x19A;
        var selectorFrame = frame.Address == 0x230;
        var thresholdFrame = frame.Address == 0x25A;
        var h = selectorFrame ? (frame.CurrentStoredWord!.Value & 8) != 0 : sources.SelectorH;
        var threshold = thresholdFrame ? frame.CurrentStoredWord : sources.Threshold;
        var high = frame.CurrentStoredWord!.Value >> 8;
        var frameSource = $"Conditional CAL{frame.CallPc:X4}:{frame.CreatorStorageGeneration}";
        return new(frame.Address, !target, target ? false : sources.TargetZeroOwned, target ? (high & 2) != 0 : null,
            target ? (high & 4) != 0 : null, h, threshold,
            target ? frame.StorageGeneration : sources.TargetStorageGeneration,
            selectorFrame ? frameSource : sources.SelectorSourceIdentity,
            selectorFrame ? frame.StorageGeneration : sources.SelectorStorageGeneration,
            thresholdFrame ? frameSource : sources.ThresholdSourceIdentity,
            thresholdFrame ? frame.StorageGeneration : sources.ThresholdStorageGeneration,
            frame.Source.PathIdentity, frame.Source.MachineIdentity,
            target ? SspProvenanceStatus.KnownFrameOverwrite : SspProvenanceStatus.DisjointProvenWithinDomain);
    }

    internal static SspConditionalReturn MatchNormalReturn(SspConditionalFrame frame,
        SspReturnWitness read)
    {
        var matches = frame.CallReached && frame.WriteCompleted && frame.Address is not null &&
            frame.PostCallSsp is not null && frame.ContextEstablishedAfterFrame && read.ReturnReached &&
            read.FrameUnchanged && read.StackProgressionBalanced && read.ListedConditionalInstruction &&
            read.ReaderPc == frame.NormalReturnReaderPc && read.Address == frame.Address && read.Width == 16 &&
            frame.Width == 16 && read.ReturnWord == frame.ReturnPc && read.WriterPc == frame.LatestStorageWriterPc &&
            read.FrameCreatorPc == frame.CallPc && read.ReturnWordLineage == frame.ReturnWordLineage &&
            frame.CurrentStoredWord == frame.ReturnPc &&
            frame.ReturnWordLineage == CalLineage(frame.Source, frame.CallPc, frame.CreatorStorageGeneration) &&
            read.StorageGeneration == frame.StorageGeneration && read.PathIdentity == frame.Source.PathIdentity &&
            read.MachineIdentity == frame.Source.MachineIdentity && read.SspBefore == frame.PostCallSsp &&
            read.SspAfter == frame.Source.Value && Even(Wrap(read.SspBefore!.Value + 2)) == frame.Address;
        return matches ? new(SspProvenanceStatus.ConditionalNormalReturn, frame.ReturnPc,
            read.SspAfter, 0, true, true, false) :
            new(SspProvenanceStatus.MatchingNativeReturnNotEstablished, null, null, null, false, false, false);
    }

    internal static SspFlagState ApplyCalOrRtFlags(SspFlagState before) => before with { Sf = false };

    internal static SspStackFootprint StackFootprint(int oldSsp, bool interruptFrame)
    {
        RequireWord(oldSsp);
        var words = interruptFrame ? 4 : 1;
        return new(Enumerable.Range(0, words).Select(i => Even(Wrap(oldSsp - 2 * i))).ToArray(),
            Wrap(oldSsp - 2 * words), 2 * words);
    }

    internal static PendingClear ClearIrq4(bool? oldBit, string identity, string path, string machine)
    {
        RequireIdentity(identity, path, machine);
        return new(oldBit, oldBit is null ? null : !oldBit.Value, false, identity, path, machine,
            PendingProvenanceStatus.SoftwareClearEstablished);
    }

    internal static PendingAtReader AnalyzePending(PendingClear clear, PendingFactor? factor,
        bool intervalAndAliasesEstablished = true)
    {
        if (clear.Status != PendingProvenanceStatus.SoftwareClearEstablished || clear.NewBit != false)
            throw new InvalidDataException("A completed conditional software clear is required.");
        if (factor is not null) RequireIdentity(factor.SourceIdentity, factor.ClearIntervalIdentity);
        if (factor is not null && (factor.PathIdentity != clear.PathIdentity ||
            factor.MachineIdentity != clear.MachineIdentity ||
            factor.ClearIntervalIdentity != clear.ClearIdentity ||
            factor.Source is PendingFactorSource.HostPatch or PendingFactorSource.ImportedMachine))
            throw new InvalidDataException("Mixed histories and host/second-machine factors are not provenance.");
        var architectural = factor?.Source is PendingFactorSource.DocumentedAdcPossibility or
            PendingFactorSource.HypotheticalSamePathAdcSet;
        if (!intervalAndAliasesEstablished || factor?.Phase == PendingFactorPhase.Unknown ||
            factor?.Source == PendingFactorSource.DocumentedAdcPossibility)
            return Reader(null, clear, architectural, false, factor?.SourceIdentity,
                factor?.Source == PendingFactorSource.DocumentedAdcPossibility ?
                    PendingProvenanceStatus.HardwareSetSpecifiedArchitecturally :
                    PendingProvenanceStatus.PendingStateAtReaderNotEstablished);
        var fresh = factor?.Phase == PendingFactorPhase.AfterClearBeforeReader &&
            factor.Source == PendingFactorSource.HypotheticalSamePathAdcSet;
        return Reader(fresh, clear, architectural, fresh,
            fresh ? factor!.SourceIdentity : clear.ClearIdentity,
            fresh ? PendingProvenanceStatus.PendingStateConditional : PendingProvenanceStatus.SoftwareClearEstablished);
    }

    internal static SspHelperDecision HelperDecision(SspAliasEffects aliases, int? timerWord,
        PendingAtReader pending, bool correlatedPathEstablished = true)
    {
        if (!correlatedPathEstablished || aliases.PathIdentity != pending.PathIdentity ||
            aliases.MachineIdentity != pending.MachineIdentity)
            throw new InvalidDataException("Mutually exclusive auxiliary/pending histories.");
        if (timerWord is not null) RequireWord(timerWord.Value);
        if (aliases.SelectorH is null || (aliases.SelectorH.Value && aliases.Threshold is null))
            return new(SspHelperRoute.Unknown, null, null, "SSP/auxiliary alias provenance");
        // H0 bypasses the timer/threshold reader entirely. A latent overwritten
        // threshold is not a hardware sample consumed by that listed route.
        var d = aliases.SelectorH.Value && timerWord is int sample && aliases.Threshold is int threshold ?
            ConditionalDifference(sample, threshold) : (int?)null;
        if (aliases.SelectorH.Value && d is null)
            return new(SspHelperRoute.Unknown, null, null, "Timer sample/evolution not established");
        if (aliases.SelectorH.Value && d < 0xC8)
            return new(SspHelperRoute.TimerConditional, d, false, "Timer/control effects and matching native return");
        if (pending.OldBit is null)
            return new(SspHelperRoute.Unknown, d, true,
                "Pending state at RB5CA0 not established");
        return pending.OldBit.Value ?
            new(SspHelperRoute.AdcBodyConditional, d, true,
                "P2/ADC/indexed effects and matching native return") :
            new(SspHelperRoute.FaultBrkConditional, d, true,
                "Fault marker and BRK system-reset effects; no normal RT");
    }

    internal static int? ConditionalP2Index(byte? p2, bool peripheralContextEstablished)
    {
        if (p2 is null || !peripheralContextEstablished) return null;
        // Independent byte algebra, not a fetched hardware sample.
        var swapped = ((p2.Value & 15) << 4) | (p2.Value >> 4);
        return (swapped >> 1) & 7;
    }

    internal static int ConditionalDifference(int timerWord, int threshold)
    {
        RequireWord(timerWord); RequireWord(threshold);
        return Wrap(timerWord - threshold);
    }

    internal static void RequireActualExecution(object conditionalProof, string claimedMachine,
        int? claimedNativeEvent = null, long? claimedNativeOrdinal = null,
        bool hostIrq = false, bool hostReturn = false) =>
        throw new InvalidDataException("Static possibility cannot become actual-ROM/frame/IRQ/return/runtime-owner evidence.");

    private static PendingAtReader Reader(bool? old, PendingClear clear, bool architectural,
        bool fresh, string? identity, PendingProvenanceStatus status) =>
        new(old, old is null ? null : !old.Value, false, true, architectural, fresh,
            identity, clear.PathIdentity, clear.MachineIdentity, status);

    private static bool HasSspProof(SspDefinition source) => source.Value is not null &&
        source.Status is SspProvenanceStatus.NativeSSPWriterProvenWithinDomain or
            SspProvenanceStatus.SSPContinuityConditional;

    private static int Even(int value) => value & 0xFFFE;
    private static int Wrap(int value) => value & 0xFFFF;
    private static string CalLineage(SspDefinition source, int callPc, string creatorGeneration) =>
        $"Conditional CAL{callPc:X4}:{creatorGeneration}:{source.SourceIdentity}:{source.PathIdentity}:{source.MachineIdentity}";
    private static void RequireAuxiliarySources(SspAuxiliarySources sources, SspDefinition ssp)
    {
        if (sources.PathIdentity != ssp.PathIdentity || sources.MachineIdentity != ssp.MachineIdentity)
            throw new InvalidDataException("Independent auxiliary sources belong to a different path/machine.");
        if (sources.TargetZeroOwned is not null) RequireIdentity(sources.TargetSourceIdentity!, sources.TargetStorageGeneration!);
        if (sources.SelectorH is not null) RequireIdentity(sources.SelectorSourceIdentity!, sources.SelectorStorageGeneration!);
        if (sources.Threshold is not null)
        {
            RequireWord(sources.Threshold.Value);
            RequireIdentity(sources.ThresholdSourceIdentity!, sources.ThresholdStorageGeneration!);
        }
    }
    private static void RequireWord(int value)
    {
        if (value is < 0 or > 0xFFFF) throw new InvalidDataException("Not a 16-bit value.");
    }
    private static void RequireIdentity(params string[] identities)
    {
        if (identities.Any(string.IsNullOrWhiteSpace)) throw new InvalidDataException("Missing symbolic source/history identity.");
    }
}
