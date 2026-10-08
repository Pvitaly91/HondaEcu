namespace HondaEcu.Core.Tests;

// Independent invented specification algebra only. None of these objects is a
// Cpu/Bus, a ROM execution record, an admission grant, or actual native evidence.
internal enum FirstRamEntry
{
    ActualResetEntryEstablished,
    RootedSoftwarePrefixEstablished,
    ConditionalCallerEntry,
    TechnicalHarnessEntry,
    NotEstablished
}

internal enum FirstRamModelVerdict
{
    SpecificationMatches,
    SpecificationMismatch,
    UnknownSource,
    InvalidProvenance,
    ExecutionPreflightBlocked
}

internal enum FirstRamOrigin { InventedCodeOwnedHypothesis, HostSeed, ImportedState }

internal sealed record FirstRamMachine(string Cpu, string Bus, string Path);
internal sealed record FirstRamWord(int? Value, int WriterPc, string? Source,
    string? Generation, FirstRamMachine Machine, FirstRamOrigin Origin = FirstRamOrigin.InventedCodeOwnedHypothesis,
    int? SourceWriterPc = null);
internal sealed record FirstRamContext(int? Lrb, int? Scb, bool? Dd, bool? Sf,
    bool? NoAsynchronousMutation, bool? RamMappingEstablished);
internal sealed record FirstRamSspExchange(FirstRamWord Original, FirstRamWord Temporary,
    int? SavedWord, string? SavedLineage, int FirstPc, int RestorePc, string PairIdentity,
    bool AdjacentPairEstablished);
internal sealed record FirstRamCreator(int CallPc, int TargetPc, int ReturnPc,
    string Invocation, string Source, FirstRamMachine Machine, string EventIdentity);
internal sealed record FirstRamFrame(FirstRamWord SspSource, FirstRamWord Pattern,
    FirstRamWord Index, FirstRamCreator Creator, int? Address, int? PostSsp,
    string Generation, string ReturnLineage, FirstRamModelVerdict Verdict)
{
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
    internal bool NativeCallFrameCreated => false;
}

// ModelOrdinal orders ALL writes in the supplied invented ledger, not only
// writes to the return slot. It is explicitly NOT a native global ordinal.
internal sealed record FirstRamWrite(long ModelOrdinal, int ModelEventIndex,
    int WriterPc, int Address, int WidthBytes, int? Value, string Generation,
    string? PreviousGeneration, string SourceLineage, FirstRamCreator Creator,
    FirstRamOrigin Origin = FirstRamOrigin.InventedCodeOwnedHypothesis)
{
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
}

internal sealed record FirstRamJournal(IReadOnlyList<FirstRamWrite> Writes,
    bool CompleteAllWritesHypothesis, FirstRamMachine Machine);
internal sealed record FirstRamSavedAccumulator(int? Value, string Lineage,
    string SourceGeneration, int ReaderPc, FirstRamCreator Creator,
    FirstRamMachine Machine);
internal sealed record FirstRamComparison(int? Left, int? Right, bool? Cf, bool? Zf,
    int ProducerPc, string? LeftSource, string? RightSource, FirstRamMachine Machine,
    bool SourcesEstablished, bool NoInterveningFlagWriter,
    string? LeftStorageGeneration = null, string? RightStorageGeneration = null);
internal sealed record FirstRamReturnRead(int ReaderPc, int ModelEventIndex,
    int? SspBefore, int? SspAfter, int? Address, int WidthBytes, int? Word,
    string Generation, int WriterPc, string Lineage, FirstRamCreator Creator,
    FirstRamMachine Machine, bool Reached, bool NativeInstructionHypothesis);
internal sealed record FirstRamModelResult(FirstRamModelVerdict Verdict, string Barrier,
    int? ReturnPc = null, int? RestoredSsp = null)
{
    internal string EvidenceDomain => "InventedOnly";
    internal int ActualRomExecutions => 0;
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
    internal bool MatchingNativeReturnObserved => false;
    internal bool BoundedSameMachineRoundtripEstablished => false;
    internal bool FullBootEstablished => false;
    internal bool ExecutionPermitted => false;
}

internal sealed record FirstRamPreflight(FirstRamEntry Entry,
    bool? OriginalRomBinding, bool? RootContext, bool? EarlySelftests,
    bool? NativeSources, bool? PeripheralSources, bool? InstructionAdmission,
    bool? BoundedRanges, bool? InstructionBudget, bool? OneCpuBus,
    bool? TraceContinuity, bool? AllWriteJournal, bool? FrameSourceReader,
    bool? TerminalStop268C, bool? SafeReadOnlyMechanism)
{
    internal string EvidenceDomain => "InventedOnly";
}

internal static class FirstRamTestProvenanceFixture
{
    internal static FirstRamSspExchange BeginSspExchange(FirstRamWord oldSsp,
        int pattern, int firstPc, int restorePc, string pairIdentity,
        bool adjacentPairEstablished = true)
    {
        RequireWord(pattern);
        RequireIdentity(pairIdentity);
        var known = Owned(oldSsp);
        var temporary = new FirstRamWord(pattern, firstPc, $"invented-pattern:{pairIdentity}",
            $"invented-temporary:{pairIdentity}", oldSsp.Machine);
        var exactPair = (firstPc, restorePc, pattern) is (0x2531, 0x2533, 0x5555) or
            (0x254D, 0x254F, 0xAAAA);
        return new(oldSsp, temporary, known ? oldSsp.Value : null,
            known ? oldSsp.Source : null, firstPc, restorePc, pairIdentity, adjacentPairEstablished && exactPair);
    }

    internal static FirstRamWord RestoreSsp(FirstRamSspExchange exchange,
        FirstRamMachine machine, bool restoreReached = true, bool noInterruption = true,
        bool savedAccumulatorUnchanged = true, int? restorePc = null)
    {
        var restoredGeneration = $"invented-restored:{exchange.PairIdentity}";
        var established = Owned(exchange.Original) && restoreReached && noInterruption &&
            savedAccumulatorUnchanged && exchange.AdjacentPairEstablished &&
            machine == exchange.Original.Machine && machine == exchange.Temporary.Machine &&
            (restorePc ?? exchange.RestorePc) == exchange.RestorePc &&
            exchange.SavedWord == exchange.Original.Value && exchange.SavedLineage == exchange.Original.Source &&
            exchange.Temporary.WriterPc == exchange.FirstPc &&
            exchange.Temporary.Origin == FirstRamOrigin.InventedCodeOwnedHypothesis &&
            restoredGeneration != exchange.Original.Generation && restoredGeneration != exchange.Temporary.Generation;
        return new(established ? exchange.SavedWord : null, exchange.RestorePc,
            established ? exchange.SavedLineage : null,
            established ? restoredGeneration : null, machine,
            SourceWriterPc: established ? exchange.Original.SourceWriterPc : null);
    }

    internal static FirstRamFrame FirstCall(FirstRamWord ssp, FirstRamWord pattern,
        FirstRamWord index, FirstRamContext context, FirstRamCreator creator,
        string generation)
    {
        RequireIdentity(generation, creator.Invocation, creator.Source, creator.EventIdentity);
        var known = Owned(ssp) && Owned(pattern) && Owned(index);
        var same = ssp.Machine == creator.Machine && pattern.Machine == creator.Machine &&
            index.Machine == creator.Machine;
        var domain = context.Lrb == 0x40 && context.Scb == 0 && context.Dd == true &&
            context.Sf == false && context.NoAsynchronousMutation == true &&
            context.RamMappingEstablished == true;
        var exact = creator.CallPc == 0x2689 && creator.TargetPc == 0x5C5C &&
            creator.ReturnPc == 0x268C && ssp.Value == 0x47E &&
            ssp.SourceWriterPc == 0x24F8 && ssp.WriterPc is 0x24F8 or 0x2533 or 0x254F &&
            creator.Source == ssp.Source && pattern.Value == 0x5555 &&
            pattern.WriterPc == 0x2686 && pattern.SourceWriterPc == 0x2686 &&
            index.Value == 0x3FA && index.WriterPc == 0x267F && index.SourceWriterPc == 0x267F;
        var verdict = !known ? FirstRamModelVerdict.UnknownSource :
            !same ? FirstRamModelVerdict.InvalidProvenance :
            !domain || !exact ? FirstRamModelVerdict.SpecificationMismatch :
            FirstRamModelVerdict.SpecificationMatches;
        return new(ssp, pattern, index, creator,
            verdict == FirstRamModelVerdict.SpecificationMatches ? Even(ssp.Value!.Value) : null,
            verdict == FirstRamModelVerdict.SpecificationMatches ? Wrap(ssp.Value!.Value - 2) : null,
            generation, Lineage(creator), verdict);
    }

    internal static int IndexedWordAddress(int baseAddress, int index)
    {
        RequireWord(baseAddress); RequireWord(index);
        return Even(Wrap(baseAddress + index));
    }

    internal static FirstRamSavedAccumulator SaveAtExchange(FirstRamFrame frame,
        FirstRamWrite original, FirstRamWrite overwrite)
    {
        var valid = frame.Verdict == FirstRamModelVerdict.SpecificationMatches &&
            CalWriteMatches(frame, original) && PatternWriteMatches(frame, original, overwrite);
        return new(valid ? original.Value : null, valid ? frame.ReturnLineage : "Unestablished",
            original.Generation, 0x5C68, frame.Creator, frame.Creator.Machine);
    }

    internal static FirstRamComparison Compare(int? left, int? right,
        string? leftSource, string? rightSource, FirstRamMachine machine,
        bool sourcesEstablished = true, int producerPc = 0x5C7C,
        bool noInterveningFlagWriter = true, string? leftStorageGeneration = null,
        string? rightStorageGeneration = null)
    {
        if (left is int l) RequireWord(l);
        if (right is int r) RequireWord(r);
        var known = left is not null && right is not null && sourcesEstablished &&
            !string.IsNullOrWhiteSpace(leftSource) && !string.IsNullOrWhiteSpace(rightSource);
        return new(left, right, known ? left < right : null, known ? left == right : null,
            producerPc, leftSource, rightSource, machine, known, noInterveningFlagWriter,
            leftStorageGeneration, rightStorageGeneration);
    }

    internal static int? NextAfterJne(FirstRamComparison comparison)
    {
        if (!comparison.SourcesEstablished || comparison.ProducerPc != 0x5C7C ||
            !comparison.NoInterveningFlagWriter || comparison.Left is null || comparison.Right is null ||
            string.IsNullOrWhiteSpace(comparison.LeftSource) || string.IsNullOrWhiteSpace(comparison.RightSource) ||
            comparison.Zf is null ||
            comparison.Cf != (comparison.Left < comparison.Right) ||
            comparison.Zf != (comparison.Left == comparison.Right)) return null;
        return comparison.Zf.Value ? 0x5C80 : 0x5C81;
    }

    internal static FirstRamModelResult CheckRoundtrip(FirstRamFrame frame,
        FirstRamJournal journal, FirstRamSavedAccumulator saved,
        FirstRamComparison comparison, FirstRamReturnRead read)
    {
        if (frame.Verdict != FirstRamModelVerdict.SpecificationMatches)
            return new(frame.Verdict, "Independent SSP/pattern/index/context source");
        if (!JournalMatches(journal, frame.Creator))
            return new(FirstRamModelVerdict.InvalidProvenance, "Complete invented ALL-write journal continuity");
        if (journal.Writes.Any(w => OverlapsWord(w, 0x80) || OverlapsWord(w, 2) ||
            (w.Address <= 4 && w.Address + w.WidthBytes > 4)))
            return new(FirstRamModelVerdict.InvalidProvenance, "Retained X1/LRB/SCB context");
        var sspWrites = journal.Writes.Where(w => OverlapsWord(w, 0)).ToArray();
        if (sspWrites.Length != 1 || sspWrites[0].WriterPc != 0x2689 ||
            sspWrites[0].Value != frame.PostSsp || sspWrites[0].WidthBytes != 2 ||
            sspWrites[0].PreviousGeneration != frame.SspSource.Generation)
            return new(FirstRamModelVerdict.InvalidProvenance, "CAL SSP progression/no intervening stack writer");
        var slot = journal.Writes.Where(w => OverlapsWord(w, frame.Address!.Value)).ToArray();
        if (slot.Length != 3 || !CalWriteMatches(frame, slot[0]) ||
            !PatternWriteMatches(frame, slot[0], slot[1]))
            return new(FirstRamModelVerdict.InvalidProvenance, "CAL/overwrite creator and generations");
        var restored = slot[2];
        if (saved.Value != frame.Creator.ReturnPc || saved.Lineage != frame.ReturnLineage ||
            saved.SourceGeneration != slot[0].Generation || saved.ReaderPc != 0x5C68 ||
            saved.Creator != frame.Creator || saved.Machine != frame.Creator.Machine ||
            restored.WriterPc != 0x5C6C || restored.WidthBytes != 2 ||
            restored.Value != saved.Value || restored.PreviousGeneration != slot[1].Generation ||
            restored.SourceLineage != saved.Lineage || restored.Creator != frame.Creator ||
            restored.Generation == slot[0].Generation || restored.Generation == slot[1].Generation)
            return new(FirstRamModelVerdict.InvalidProvenance, "Fresh restore with exact saved CAL lineage");
        var accumulatorWrites = journal.Writes.Where(w => OverlapsWord(w, 6)).ToArray();
        var x2Writes = journal.Writes.Where(w => OverlapsWord(w, 0x82)).ToArray();
        var localWrites = journal.Writes.Where(w => OverlapsWord(w, 0x206)).ToArray();
        if (accumulatorWrites.Length != 2 || x2Writes.Length != 1 || localWrites.Length != 1 ||
            slot[0].ModelEventIndex != sspWrites[0].ModelEventIndex ||
            slot[0].ModelOrdinal >= sspWrites[0].ModelOrdinal ||
            sspWrites[0].ModelOrdinal >= x2Writes[0].ModelOrdinal ||
            x2Writes[0].ModelEventIndex <= sspWrites[0].ModelEventIndex ||
            slot[1].ModelEventIndex <= x2Writes[0].ModelEventIndex ||
            accumulatorWrites[0].ModelEventIndex != slot[1].ModelEventIndex ||
            restored.ModelEventIndex <= slot[1].ModelEventIndex ||
            accumulatorWrites[1].ModelEventIndex != restored.ModelEventIndex ||
            localWrites[0].ModelEventIndex <= restored.ModelEventIndex ||
            accumulatorWrites[0].WriterPc != 0x5C68 || accumulatorWrites[0].WidthBytes != 2 ||
            accumulatorWrites[0].Value != saved.Value || accumulatorWrites[0].SourceLineage != saved.Lineage ||
            accumulatorWrites[0].PreviousGeneration != frame.Pattern.Generation ||
            accumulatorWrites[0].ModelOrdinal <= slot[1].ModelOrdinal ||
            accumulatorWrites[0].ModelOrdinal >= restored.ModelOrdinal ||
            accumulatorWrites[1].WriterPc != 0x5C6C || accumulatorWrites[1].WidthBytes != 2 ||
            accumulatorWrites[1].Value != frame.Pattern.Value ||
            accumulatorWrites[1].PreviousGeneration != accumulatorWrites[0].Generation ||
            accumulatorWrites[1].SourceLineage != frame.Pattern.Source ||
            accumulatorWrites[1].ModelOrdinal <= restored.ModelOrdinal ||
            x2Writes[0].WriterPc != 0x5C5C || x2Writes[0].WidthBytes != 2 ||
            x2Writes[0].Value != frame.Pattern.Value || x2Writes[0].SourceLineage != "invented-MOVX2-5C5C" ||
            x2Writes[0].ModelOrdinal >= slot[1].ModelOrdinal ||
            localWrites[0].WriterPc != 0x5C70 || localWrites[0].WidthBytes != 2 ||
            localWrites[0].Value != frame.Pattern.Value ||
            localWrites[0].SourceLineage != "invented-ST5C70/L5C7B" ||
            localWrites[0].ModelOrdinal <= accumulatorWrites[1].ModelOrdinal)
            return new(FirstRamModelVerdict.InvalidProvenance, "Accumulator/X2/local pattern transfer generations");
        if (comparison.Machine != frame.Creator.Machine || comparison.Left != frame.Pattern.Value ||
            comparison.Right != frame.Pattern.Value || comparison.LeftSource != "invented-ST5C70/L5C7B" ||
            comparison.RightSource != "invented-MOVX2-5C5C" ||
            comparison.LeftStorageGeneration != localWrites[0].Generation ||
            comparison.RightStorageGeneration != x2Writes[0].Generation || NextAfterJne(comparison) != 0x5C80)
            return new(FirstRamModelVerdict.SpecificationMismatch, "Owned CMP5C7C/JNE5C7E outcome");
        foreach (var pswh in journal.Writes.Where(w => w.Address == 5))
        {
            var clear = pswh.WriterPc == 0x5C65 && (pswh.Value!.Value & 1) == 0 &&
                pswh.SourceLineage == "invented-MIE-clear5C65" &&
                pswh.ModelOrdinal > x2Writes[0].ModelOrdinal && pswh.ModelOrdinal < slot[1].ModelOrdinal &&
                pswh.ModelEventIndex > x2Writes[0].ModelEventIndex && pswh.ModelEventIndex < slot[1].ModelEventIndex;
            var set = pswh.WriterPc == 0x5C71 && (pswh.Value!.Value & 1) != 0 &&
                pswh.SourceLineage == "invented-MIE-set5C71" &&
                pswh.ModelOrdinal > localWrites[0].ModelOrdinal && pswh.ModelEventIndex > localWrites[0].ModelEventIndex;
            // These are raw byte values presented by the logical write, not
            // writable-bit projections. The two nonexistent PSWH bits read1
            // and survive the exact FE/01 logical masks before storage filtering.
            if (pswh.WidthBytes != 1 || (pswh.Value!.Value & 0x10) == 0 ||
                (pswh.Value.Value & 0x0C) != 0x0C || (!clear && !set))
                return new(FirstRamModelVerdict.InvalidProvenance, "Owned DD-preserving MIE edits only");
        }
        var lastWriter = slot[^1];
        var matches = read.Reached && read.NativeInstructionHypothesis && read.ReaderPc == 0x5C80 &&
            read.ModelEventIndex > journal.Writes[^1].ModelEventIndex &&
            read.SspBefore == frame.PostSsp && read.SspAfter == frame.SspSource.Value &&
            Even(Wrap(read.SspBefore!.Value + 2)) == frame.Address &&
            read.Address == frame.Address && read.WidthBytes == 2 && read.Word == frame.Creator.ReturnPc &&
            read.Generation == lastWriter.Generation && read.WriterPc == lastWriter.WriterPc &&
            read.Lineage == frame.ReturnLineage && read.Creator == frame.Creator &&
            read.Machine == frame.Creator.Machine;
        return matches ? new(FirstRamModelVerdict.SpecificationMatches,
            "Invented CAL/restore/RT specification matches; no native observation", read.Word, read.SspAfter) :
            new(FirstRamModelVerdict.InvalidProvenance, "Matching current RT reader/frame/SSP identity");
    }

    internal static FirstRamModelResult CheckPreflight(FirstRamPreflight preflight)
    {
        // This is only a fail-closed policy test. Even a fully supplied invented
        // hypothesis cannot authorize actual ROM execution or claim actual root.
        if (!Enum.IsDefined(preflight.Entry) || preflight.Entry is FirstRamEntry.TechnicalHarnessEntry or
            FirstRamEntry.ConditionalCallerEntry or FirstRamEntry.NotEstablished)
            return new(FirstRamModelVerdict.ExecutionPreflightBlocked, "Actual/rooted caller entry not established");
        var obligations = new (string Name, bool? Established)[]
        {
            ("Original ROM/baseline binding", preflight.OriginalRomBinding),
            ("Root reaching context", preflight.RootContext),
            ("Early selftest history", preflight.EarlySelftests),
            ("Native A/X1/X2/SSP sources", preflight.NativeSources),
            ("RAM/SFR/peripheral sources", preflight.PeripheralSources),
            ("Instruction/branch admission", preflight.InstructionAdmission),
            ("Exact bounded PC ranges", preflight.BoundedRanges),
            ("Instruction budget", preflight.InstructionBudget),
            ("One CPU/Bus", preflight.OneCpuBus),
            ("Trace continuity", preflight.TraceContinuity),
            ("ALL-write journal continuity", preflight.AllWriteJournal),
            ("Frame source/reader lineage", preflight.FrameSourceReader),
            ("Terminal stop268C", preflight.TerminalStop268C),
            ("Existing safe read-only mechanism", preflight.SafeReadOnlyMechanism)
        };
        var missing = obligations.FirstOrDefault(o => o.Established != true);
        return missing.Name is not null ? new(FirstRamModelVerdict.ExecutionPreflightBlocked, missing.Name) :
            new(FirstRamModelVerdict.SpecificationMatches,
                "Hypothetical policy obligations match only; InventedOnly cannot grant actual preflight PASS");
    }

    internal static void RequireActualObservation(object inventedModel, string requestedStatus) =>
        throw new InvalidDataException("InventedOnly cannot establish actual source, return, same-machine history, fullboot, or historical status promotion.");

    private static bool JournalMatches(FirstRamJournal journal, FirstRamCreator creator)
    {
        if (!journal.CompleteAllWritesHypothesis || journal.Machine != creator.Machine || journal.Writes.Count < 3)
            return false;
        long priorOrdinal = 0;
        var priorEvent = -1;
        var generations = new HashSet<string>(StringComparer.Ordinal);
        foreach (var write in journal.Writes)
        {
            if (write.ModelOrdinal != priorOrdinal + 1 || write.ModelEventIndex < priorEvent ||
                write.Creator != creator || write.Origin != FirstRamOrigin.InventedCodeOwnedHypothesis ||
                write.WidthBytes is not (1 or 2) || write.Address is < 0 or > 0xFFFF ||
                (write.WidthBytes == 2 && (write.Address & 1) != 0) ||
                write.Value is null or < 0 || write.Value > (write.WidthBytes == 1 ? 255 : 65535) ||
                string.IsNullOrWhiteSpace(write.Generation) || string.IsNullOrWhiteSpace(write.SourceLineage) ||
                !generations.Add(write.Generation)) return false;
            priorOrdinal = write.ModelOrdinal;
            priorEvent = write.ModelEventIndex;
        }
        return true;
    }

    private static bool CalWriteMatches(FirstRamFrame frame, FirstRamWrite write) =>
        write.WriterPc == 0x2689 && write.Address == frame.Address && write.WidthBytes == 2 &&
        write.Value == 0x268C && write.Generation == frame.Generation &&
        write.Creator == frame.Creator && write.SourceLineage == frame.ReturnLineage;

    private static bool PatternWriteMatches(FirstRamFrame frame, FirstRamWrite original,
        FirstRamWrite overwrite) => overwrite.WriterPc == 0x5C68 && overwrite.Address == frame.Address &&
        overwrite.WidthBytes == 2 && overwrite.Value == frame.Pattern.Value &&
        overwrite.PreviousGeneration == original.Generation && overwrite.Generation != original.Generation &&
        overwrite.Creator == frame.Creator && overwrite.SourceLineage == frame.Pattern.Source;

    private static bool OverlapsWord(FirstRamWrite write, int wordAddress) =>
        write.Address <= wordAddress + 1 && write.Address + write.WidthBytes > wordAddress;

    private static bool Owned(FirstRamWord word) => word.Value is >= 0 and <= 0xFFFF &&
        word.Origin == FirstRamOrigin.InventedCodeOwnedHypothesis &&
        !string.IsNullOrWhiteSpace(word.Source) && !string.IsNullOrWhiteSpace(word.Generation) &&
        !string.IsNullOrWhiteSpace(word.Machine.Cpu) && !string.IsNullOrWhiteSpace(word.Machine.Bus) &&
        !string.IsNullOrWhiteSpace(word.Machine.Path);

    private static string Lineage(FirstRamCreator creator) =>
        $"invented-CAL:{creator.CallPc:X4}/{creator.Invocation}/{creator.Source}/{creator.Machine}";

    private static int Even(int value) => value & 0xFFFE;
    private static int Wrap(int value) => value & 0xFFFF;
    private static void RequireWord(int value)
    {
        if (value is < 0 or > 0xFFFF) throw new ArgumentOutOfRangeException(nameof(value));
    }
    private static void RequireIdentity(params string[] identities)
    {
        if (identities.Any(string.IsNullOrWhiteSpace))
            throw new InvalidDataException("Independent invented source/generation/instance identities are required.");
    }
}
