namespace HondaEcu.Core.Tests;

public sealed class FirstRamTestProvenanceTests
{
    private static FirstRamMachine Machine() => new("invented-cpu-A", "invented-bus-A", "invented-path-A");
    private static FirstRamWord Word(int? value, int pc, string source, string generation) =>
        new(value, pc, source, generation, Machine(), SourceWriterPc: pc);
    private static FirstRamWord Ssp() => Word(0x47E, 0x24F8, "invented-SSP-source24F8", "invented-SSP-gen0");
    private static FirstRamWord Pattern() => Word(0x5555, 0x2686, "invented-pattern2686", "invented-A-gen0");
    private static FirstRamWord Index() => Word(0x3FA, 0x267F, "invented-X1-source267F", "invented-X1-gen0");
    private static FirstRamContext Context() => new(0x40, 0, true, false, true, true);
    private static FirstRamCreator Creator() =>
        new(0x2689, 0x5C5C, 0x268C, "invented-first-call-A", Ssp().Source!, Machine(), "invented-event-A");
    private static FirstRamFrame Frame() =>
        FirstRamTestProvenanceFixture.FirstCall(Ssp(), Pattern(), Index(), Context(), Creator(), "invented-frame-genA");

    private static FirstRamJournal Journal(FirstRamFrame frame)
    {
        // Closed toy ledger, NOT an OEM trace or a claimed native write count.
        // Its nonframe writes demonstrate that frame-only ordinal resets fail.
        var c = frame.Creator;
        return new(new FirstRamWrite[]
        {
            new(1, 0, 0x2689, 0x47E, 2, 0x268C, frame.Generation, "invented-prior-unknown-RAM", frame.ReturnLineage, c),
            new(2, 0, 0x2689, 0, 2, 0x47C, "invented-SSP-gen1", frame.SspSource.Generation, "invented-SSP-minus2", c),
            new(3, 1, 0x5C5C, 0x82, 2, 0x5555, "invented-X2-gen1", "invented-prior-X2", "invented-MOVX2-5C5C", c),
            new(4, 2, 0x5C68, 0x47E, 2, 0x5555, "invented-frame-genB", frame.Generation, frame.Pattern.Source!, c),
            new(5, 2, 0x5C68, 6, 2, 0x268C, "invented-A-saved", frame.Pattern.Generation, frame.ReturnLineage, c),
            new(6, 3, 0x5C6C, 0x47E, 2, 0x268C, "invented-frame-genC", "invented-frame-genB", frame.ReturnLineage, c),
            new(7, 3, 0x5C6C, 6, 2, 0x5555, "invented-A-restored-pattern", "invented-A-saved", frame.Pattern.Source!, c),
            new(8, 4, 0x5C70, 0x206, 2, 0x5555, "invented-er3-pattern", "invented-prior-er3", "invented-ST5C70/L5C7B", c)
        }, true, Machine());
    }

    private static FirstRamSavedAccumulator Saved(FirstRamFrame frame, FirstRamJournal journal) =>
        FirstRamTestProvenanceFixture.SaveAtExchange(frame, journal.Writes[0], journal.Writes[3]);
    private static FirstRamComparison Comparison() => FirstRamTestProvenanceFixture.Compare(
        0x5555, 0x5555, "invented-ST5C70/L5C7B", "invented-MOVX2-5C5C", Machine(),
        leftStorageGeneration: "invented-er3-pattern", rightStorageGeneration: "invented-X2-gen1");
    private static FirstRamReturnRead Read(FirstRamFrame frame) =>
        new(0x5C80, 5, 0x47C, 0x47E, 0x47E, 2, 0x268C, "invented-frame-genC", 0x5C6C,
            frame.ReturnLineage, frame.Creator, Machine(), true, true);
    private static FirstRamModelResult Check(FirstRamFrame frame, FirstRamJournal journal,
        FirstRamSavedAccumulator? saved = null, FirstRamComparison? comparison = null,
        FirstRamReturnRead? read = null) => FirstRamTestProvenanceFixture.CheckRoundtrip(
            frame, journal, saved ?? Saved(frame, journal), comparison ?? Comparison(), read ?? Read(frame));
    private static FirstRamJournal Replace(FirstRamJournal journal, int index, FirstRamWrite write) =>
        journal with { Writes = journal.Writes.Select((w, i) => i == index ? write : w).ToArray() };
    private static FirstRamPreflight CompleteHypothesis() => new(FirstRamEntry.RootedSoftwarePrefixEstablished,
        true, true, true, true, true, true, true, true, true, true, true, true, true, true);

    [Fact]
    public void IndependentlyOwnedSsp047EDefinitionIsAnInventedHypothesisNotActualRoot()
    {
        var ssp = Ssp();
        Assert.Equal(0x24F8, ssp.WriterPc); Assert.Equal(0x24F8, ssp.SourceWriterPc);
        Assert.Equal(0x47E, ssp.Value); Assert.Equal(FirstRamOrigin.InventedCodeOwnedHypothesis, ssp.Origin);
        var frame = Frame();
        Assert.Equal(FirstRamModelVerdict.SpecificationMatches, frame.Verdict);
        Assert.False(frame.NativeCallFrameCreated); Assert.Null(frame.ActualEventIndex);
        Assert.Null(frame.ActualGlobalWriteOrdinal);
    }

    [Theory]
    [InlineData(0x5555, 0x2531, 0x2533)]
    [InlineData(0xAAAA, 0x254D, 0x254F)]
    public void AdjacentSspExchangeRestoresLineageIntoAFreshGeneration(int pattern, int first, int restore)
    {
        var original = Ssp();
        var exchange = FirstRamTestProvenanceFixture.BeginSspExchange(original, pattern, first, restore, "invented-pair");
        Assert.Equal(pattern, exchange.Temporary.Value); Assert.Equal(0x47E, exchange.SavedWord);
        var restored = FirstRamTestProvenanceFixture.RestoreSsp(exchange, Machine());
        Assert.Equal(0x47E, restored.Value); Assert.Equal(original.Source, restored.Source);
        Assert.Equal(original.SourceWriterPc, restored.SourceWriterPc); Assert.Equal(restore, restored.WriterPc);
        Assert.NotEqual(original.Generation, restored.Generation);
        Assert.NotEqual(exchange.Temporary.Generation, restored.Generation);
    }

    [Fact]
    public void BothSspPairsPreserveTheSameDefinitionButNotTheSameStorageGeneration()
    {
        var one = FirstRamTestProvenanceFixture.RestoreSsp(
            FirstRamTestProvenanceFixture.BeginSspExchange(Ssp(), 0x5555, 0x2531, 0x2533, "pair1"), Machine());
        var two = FirstRamTestProvenanceFixture.RestoreSsp(
            FirstRamTestProvenanceFixture.BeginSspExchange(one, 0xAAAA, 0x254D, 0x254F, "pair2"), Machine());
        Assert.Equal(0x47E, two.Value); Assert.Equal(Ssp().Source, two.Source);
        Assert.Equal(0x24F8, two.SourceWriterPc); Assert.NotEqual(one.Generation, two.Generation);
        var frame = FirstRamTestProvenanceFixture.FirstCall(two, Pattern(), Index(), Context(), Creator(), "frame-after-pairs");
        Assert.Equal(FirstRamModelVerdict.SpecificationMatches, frame.Verdict);
    }

    [Theory]
    [InlineData("original")]
    [InlineData("temporary")]
    public void RestoredSspGenerationMustBeFreshEvenWhenInventedNamesCollide(string collision)
    {
        var original = collision == "original" ? Ssp() with { Generation = "invented-restored:pair" } : Ssp();
        var exchange = FirstRamTestProvenanceFixture.BeginSspExchange(original, 0x5555, 0x2531, 0x2533, "pair");
        if (collision == "temporary") exchange = exchange with
        {
            Temporary = exchange.Temporary with { Generation = "invented-restored:pair" }
        };
        var restored = FirstRamTestProvenanceFixture.RestoreSsp(exchange, Machine());
        Assert.Null(restored.Value); Assert.Null(restored.Source); Assert.Null(restored.Generation);
    }

    [Fact]
    public void RestorationOfUnknownPriorSspDoesNotCreateAnOwnedSource()
    {
        var unknown = Ssp() with { Value = null, Source = null, Generation = null, SourceWriterPc = null };
        var exchange = FirstRamTestProvenanceFixture.BeginSspExchange(unknown, 0x5555, 0x2531, 0x2533, "unknown-pair");
        Assert.Null(exchange.SavedWord); Assert.Null(exchange.SavedLineage);
        var restored = FirstRamTestProvenanceFixture.RestoreSsp(exchange, Machine());
        Assert.Null(restored.Value); Assert.Null(restored.Source); Assert.Null(restored.Generation);
        Assert.Null(restored.SourceWriterPc);
    }

    [Theory]
    [InlineData("missing restore")]
    [InlineData("interrupted")]
    [InlineData("saved A changed")]
    [InlineData("wrong restore PC")]
    [InlineData("other CPU")]
    [InlineData("other bus")]
    [InlineData("other path")]
    [InlineData("not adjacent")]
    [InlineData("wrong pair")]
    public void IncompleteOrMixedSspPairCannotRestoreProvenance(string defect)
    {
        var exchange = FirstRamTestProvenanceFixture.BeginSspExchange(Ssp(), 0x5555,
            defect == "wrong pair" ? 0x2530 : 0x2531, 0x2533, "pair",
            adjacentPairEstablished: defect != "not adjacent");
        var machine = defect switch
        {
            "other CPU" => Machine() with { Cpu = "cpu-B" },
            "other bus" => Machine() with { Bus = "bus-B" },
            "other path" => Machine() with { Path = "path-B" },
            _ => Machine()
        };
        var restored = FirstRamTestProvenanceFixture.RestoreSsp(exchange, machine,
            restoreReached: defect != "missing restore", noInterruption: defect != "interrupted",
            savedAccumulatorUnchanged: defect != "saved A changed",
            restorePc: defect == "wrong restore PC" ? 0x2534 : null);
        Assert.Null(restored.Value); Assert.Null(restored.Source); Assert.Null(restored.Generation);
    }

    [Fact]
    public void FirstCallSpecificationDerivesIndexedFrameAndReturnWithoutJournalInputs()
    {
        var frame = Frame();
        Assert.Equal(0x47E, FirstRamTestProvenanceFixture.IndexedWordAddress(0x84, 0x3FA));
        Assert.Equal(0x47E, frame.Address); Assert.Equal(0x47C, frame.PostSsp);
        Assert.Equal(0x2689 + 3, frame.Creator.ReturnPc); Assert.Equal(0x268C, frame.Creator.ReturnPc);
        Assert.Equal(0x5C5C, frame.Creator.TargetPc);
        Assert.Equal(0x5555, frame.Pattern.Value); Assert.Equal(0x3FA, frame.Index.Value);
    }

    [Theory]
    [InlineData(0x84, 0x3FA, 0x47E)]
    [InlineData(0x85, 0x3FA, 0x47E)]
    [InlineData(0xFFFF, 2, 0)]
    [InlineData(0, 0xFFFF, 0xFFFE)]
    public void WordIndexedAlgebraWrapsThenAlignsDownWithoutEstablishingMapping(int basis, int index, int expected) =>
        Assert.Equal(expected, FirstRamTestProvenanceFixture.IndexedWordAddress(basis, index));

    [Theory]
    [InlineData("SSP")]
    [InlineData("A")]
    [InlineData("X1")]
    public void EachMandatoryOperandNeedsItsOwnIndependentSource(string missing)
    {
        var ssp = Ssp(); var pattern = Pattern(); var index = Index();
        if (missing == "SSP") ssp = ssp with { Source = null };
        if (missing == "A") pattern = pattern with { Generation = null };
        if (missing == "X1") index = index with { Value = null };
        var frame = FirstRamTestProvenanceFixture.FirstCall(ssp, pattern, index, Context(), Creator(), "unknown-input");
        Assert.Equal(FirstRamModelVerdict.UnknownSource, frame.Verdict);
        Assert.Null(frame.Address); Assert.Null(frame.PostSsp);
    }

    [Theory]
    [InlineData("host SSP")]
    [InlineData("imported A")]
    [InlineData("wrong SSP definition")]
    [InlineData("wrong pattern producer")]
    [InlineData("wrong index producer")]
    [InlineData("wrong SSP value")]
    [InlineData("wrong pattern value")]
    [InlineData("wrong index value")]
    public void ConvenientNumericOperandsCannotReplaceCodeOwnedFirstCallSources(string defect)
    {
        var ssp = Ssp(); var pattern = Pattern(); var index = Index();
        switch (defect)
        {
            case "host SSP": ssp = ssp with { Origin = FirstRamOrigin.HostSeed }; break;
            case "imported A": pattern = pattern with { Origin = FirstRamOrigin.ImportedState }; break;
            case "wrong SSP definition": ssp = ssp with { SourceWriterPc = 0x24F7 }; break;
            case "wrong pattern producer": pattern = pattern with { WriterPc = 0x2685 }; break;
            case "wrong index producer": index = index with { SourceWriterPc = 0x267E }; break;
            case "wrong SSP value": ssp = ssp with { Value = 0x7FE }; break;
            case "wrong pattern value": pattern = pattern with { Value = 0xAAAA }; break;
            default: index = index with { Value = 0x3F8 }; break;
        }
        var frame = FirstRamTestProvenanceFixture.FirstCall(ssp, pattern, index, Context(), Creator(), "wrong-source");
        Assert.NotEqual(FirstRamModelVerdict.SpecificationMatches, frame.Verdict); Assert.Null(frame.Address);
    }

    [Theory]
    [InlineData("page")]
    [InlineData("SCB")]
    [InlineData("DD")]
    [InlineData("SF")]
    [InlineData("async")]
    [InlineData("RAM")]
    public void UnknownOrWrongContextCannotAssertFirstIndexedFrameAlias(string defect)
    {
        var context = defect switch
        {
            "page" => Context() with { Lrb = null },
            "SCB" => Context() with { Scb = 1 },
            "DD" => Context() with { Dd = null },
            "SF" => Context() with { Sf = true },
            "async" => Context() with { NoAsynchronousMutation = null },
            _ => Context() with { RamMappingEstablished = false }
        };
        var frame = FirstRamTestProvenanceFixture.FirstCall(Ssp(), Pattern(), Index(), context, Creator(), "wrong-context");
        Assert.Equal(FirstRamModelVerdict.SpecificationMismatch, frame.Verdict); Assert.Null(frame.Address);
    }

    [Fact]
    public void TemporaryOverwriteAndFreshRestorePreserveSemanticCreatorNotOriginalStorageGeneration()
    {
        var frame = Frame(); var journal = Journal(frame); var saved = Saved(frame, journal);
        var writes = journal.Writes.Where(w => w.Address == 0x47E).ToArray();
        Assert.Equal(new[] { 0x2689, 0x5C68, 0x5C6C }, writes.Select(w => w.WriterPc));
        Assert.Equal(new int?[] { 0x268C, 0x5555, 0x268C }, writes.Select(w => w.Value));
        Assert.Equal(3, writes.Select(w => w.Generation).Distinct().Count());
        Assert.Equal(writes[0].Generation, writes[1].PreviousGeneration);
        Assert.Equal(writes[1].Generation, writes[2].PreviousGeneration);
        Assert.Equal(frame.ReturnLineage, saved.Lineage); Assert.Equal(0x268C, saved.Value);
        Assert.Equal(frame.ReturnLineage, writes[2].SourceLineage);
        Assert.All(writes, w => Assert.Equal(frame.Creator, w.Creator));
        Assert.Equal(FirstRamModelVerdict.SpecificationMatches, Check(frame, journal).Verdict);
    }

    [Theory]
    [InlineData("stale generation")]
    [InlineData("forged host frame")]
    [InlineData("wrong CAL writer")]
    [InlineData("wrong overwrite writer")]
    [InlineData("wrong restore writer")]
    [InlineData("wrong previous generation")]
    [InlineData("wrong return word")]
    [InlineData("wrong restored lineage")]
    [InlineData("wrong width")]
    [InlineData("wrong address")]
    [InlineData("unknown restore word")]
    public void FrameNumbersAloneCannotEstablishItsCreatorOrFreshRestore(string defect)
    {
        var frame = Frame(); var journal = Journal(frame); var index = 5;
        var write = journal.Writes[index];
        switch (defect)
        {
            case "stale generation": write = write with { Generation = frame.Generation }; break;
            case "forged host frame": index = 0; write = journal.Writes[0] with { Origin = FirstRamOrigin.HostSeed }; break;
            case "wrong CAL writer": index = 0; write = journal.Writes[0] with { WriterPc = 0x268D }; break;
            case "wrong overwrite writer": index = 3; write = journal.Writes[3] with { WriterPc = 0x5C67 }; break;
            case "wrong restore writer": write = write with { WriterPc = 0x5C6D }; break;
            case "wrong previous generation": write = write with { PreviousGeneration = frame.Generation }; break;
            case "wrong return word": write = write with { Value = 0x2690 }; break;
            case "wrong restored lineage": write = write with { SourceLineage = "numeric-value-only" }; break;
            case "wrong width": write = write with { WidthBytes = 1 }; break;
            case "wrong address": write = write with { Address = 0x47C }; break;
            default: write = write with { Value = null }; break;
        }
        Assert.NotEqual(FirstRamModelVerdict.SpecificationMatches, Check(frame, Replace(journal, index, write)).Verdict);
    }

    [Theory]
    [InlineData("other invocation")]
    [InlineData("other CAL PC")]
    [InlineData("other source")]
    [InlineData("other event")]
    [InlineData("other CPU")]
    [InlineData("other bus")]
    [InlineData("other path")]
    public void MatchingNumericReturnFromAnotherCreatorEventOrMachineIsNotCurrentFrame(string defect)
    {
        var frame = Frame(); var journal = Journal(frame); var c = frame.Creator;
        c = defect switch
        {
            "other invocation" => c with { Invocation = "second-call-same-PC" },
            "other CAL PC" => c with { CallPc = 0x268D },
            "other source" => c with { Source = "other-source24F8" },
            "other event" => c with { EventIdentity = "other-event" },
            "other CPU" => c with { Machine = c.Machine with { Cpu = "cpu-B" } },
            "other bus" => c with { Machine = c.Machine with { Bus = "bus-B" } },
            _ => c with { Machine = c.Machine with { Path = "path-B" } }
        };
        var changed = Replace(journal, 5, journal.Writes[5] with { Creator = c });
        Assert.Equal(0x268C, changed.Writes[5].Value);
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance, Check(frame, changed).Verdict);
    }

    [Theory]
    [InlineData("value")]
    [InlineData("lineage")]
    [InlineData("generation")]
    [InlineData("reader PC")]
    [InlineData("creator")]
    [InlineData("CPU")]
    [InlineData("bus")]
    public void SavedAccumulatorMustBeTheExactNativeExchangeHypothesisNotAHostRepair(string defect)
    {
        var frame = Frame(); var journal = Journal(frame); var saved = Saved(frame, journal);
        saved = defect switch
        {
            "value" => saved with { Value = 0x2690 },
            "lineage" => saved with { Lineage = "host-numeric268C" },
            "generation" => saved with { SourceGeneration = "other-frame-genA" },
            "reader PC" => saved with { ReaderPc = 0x5C6C },
            "creator" => saved with { Creator = frame.Creator with { Invocation = "other" } },
            "CPU" => saved with { Machine = Machine() with { Cpu = "other" } },
            _ => saved with { Machine = Machine() with { Bus = "other" } }
        };
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance, Check(frame, journal, saved: saved).Verdict);
    }

    [Theory]
    [InlineData("saved accumulator value")]
    [InlineData("saved accumulator lineage")]
    [InlineData("restored pattern value")]
    [InlineData("restored pattern previous generation")]
    [InlineData("X2 value")]
    [InlineData("X2 writer")]
    [InlineData("local pattern value")]
    [InlineData("local pattern writer")]
    public void AllPatternAndSavedAccumulatorStorageTransfersNeedIndependentMatchingWriters(string defect)
    {
        var frame = Frame(); var journal = Journal(frame);
        var index = defect.StartsWith("saved", StringComparison.Ordinal) ? 4 :
            defect.StartsWith("restored", StringComparison.Ordinal) ? 6 :
            defect.StartsWith("X2", StringComparison.Ordinal) ? 2 : 7;
        var write = journal.Writes[index];
        write = defect switch
        {
            "saved accumulator lineage" => write with { SourceLineage = "same-number-no-lineage" },
            "restored pattern previous generation" => write with { PreviousGeneration = "other-A-generation" },
            "X2 writer" or "local pattern writer" => write with { WriterPc = 0x5C67 },
            _ => write with { Value = 0x1111 }
        };
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance, Check(frame, Replace(journal, index, write)).Verdict);
    }

    [Theory]
    [InlineData("left")]
    [InlineData("right")]
    public void EqualPatternNumbersCannotBorrowStaleComparisonOperandGenerations(string stale)
    {
        var comparison = Comparison();
        comparison = stale == "left" ? comparison with { LeftStorageGeneration = "stale-er3" } :
            comparison with { RightStorageGeneration = "stale-X2" };
        Assert.Equal(FirstRamModelVerdict.SpecificationMismatch, Check(Frame(), Journal(Frame()), comparison: comparison).Verdict);
    }

    [Theory]
    [InlineData("reset at overwrite")]
    [InlineData("reset at restore")]
    [InlineData("duplicate ordinal")]
    [InlineData("missing ordinal")]
    [InlineData("negative ordinal")]
    [InlineData("reverse event")]
    [InlineData("incomplete ALL-write journal")]
    [InlineData("duplicate generation")]
    public void GlobalInventedWriteOrderingCannotResetBetweenFrameEvents(string defect)
    {
        var frame = Frame(); var journal = Journal(frame);
        var index = defect == "reset at overwrite" ? 3 : 5;
        var write = journal.Writes[index];
        write = defect switch
        {
            "reset at overwrite" or "reset at restore" => write with { ModelOrdinal = 1 },
            "duplicate ordinal" => write with { ModelOrdinal = 5 },
            "missing ordinal" => write with { ModelOrdinal = 7 },
            "negative ordinal" => write with { ModelOrdinal = -1 },
            "reverse event" => write with { ModelEventIndex = 1 },
            "duplicate generation" => write with { Generation = "invented-X2-gen1" },
            _ => write
        };
        journal = defect == "incomplete ALL-write journal" ? journal with { CompleteAllWritesHypothesis = false } :
            Replace(journal, index, write);
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance, Check(frame, journal).Verdict);
    }

    [Fact]
    public void NonframeWritesParticipateInOneInventedOrdinalStreamButDoNotBecomeNativeOrdinals()
    {
        var frame = Frame(); var journal = Journal(frame);
        Assert.Equal(Enumerable.Range(1, 8).Select(i => (long)i), journal.Writes.Select(w => w.ModelOrdinal));
        Assert.Equal(new long[] { 1, 4, 6 }, journal.Writes.Where(w => w.Address == 0x47E).Select(w => w.ModelOrdinal));
        Assert.All(journal.Writes, write =>
        {
            Assert.Null(write.ActualEventIndex); Assert.Null(write.ActualGlobalWriteOrdinal);
        });
        Assert.False(Check(frame, journal).BoundedSameMachineRoundtripEstablished);
    }

    [Theory]
    [InlineData("X2 before CAL")]
    [InlineData("SSP after restore")]
    [InlineData("CAL and SSP different events")]
    [InlineData("SSP before CAL frame")]
    public void ContiguousSortedLedgerCannotSubstituteForCalCreatorAndStackProgressionChronology(string defect)
    {
        var frame = Frame(); var journal = Journal(frame);
        var order = defect switch
        {
            "X2 before CAL" => new[] { 2, 0, 1, 3, 4, 5, 6, 7 },
            "SSP after restore" => new[] { 0, 2, 3, 4, 5, 6, 1, 7 },
            "SSP before CAL frame" => new[] { 1, 0, 2, 3, 4, 5, 6, 7 },
            _ => new[] { 0, 1, 2, 3, 4, 5, 6, 7 }
        };
        // All cases retain contiguous ordinals and nondecreasing events. The
        // first two also retain a common CAL frame/SSP event deliberately.
        var writes = order.Select((original, i) => journal.Writes[original] with
        {
            ModelOrdinal = i + 1,
            ModelEventIndex = defect == "CAL and SSP different events" ? i : 0
        }).ToArray();
        Assert.Equal(Enumerable.Range(1, 8).Select(i => (long)i), writes.Select(w => w.ModelOrdinal));
        Assert.True(writes.Zip(writes.Skip(1)).All(pair => pair.First.ModelEventIndex <= pair.Second.ModelEventIndex));
        var read = Read(frame) with { ModelEventIndex = 9 };
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance,
            Check(frame, journal with { Writes = writes }, saved: Saved(frame, journal), read: read).Verdict);
    }

    [Theory]
    [InlineData("saved A exchange event")]
    [InlineData("restored A exchange event")]
    [InlineData("same event for distinct instructions")]
    public void SortedEventsMustStillBindEachExchangePairToItsExactInstructionEvent(string defect)
    {
        var frame = Frame(); var journal = Journal(frame);
        var writes = journal.Writes.Select((w, i) => w with
        {
            ModelEventIndex = defect switch
            {
                "saved A exchange event" when i == 4 => 3,
                "restored A exchange event" when i == 6 => 4,
                "same event for distinct instructions" => 0,
                _ => w.ModelEventIndex
            }
        }).ToArray();
        Assert.True(writes.Zip(writes.Skip(1)).All(pair => pair.First.ModelEventIndex <= pair.Second.ModelEventIndex));
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance,
            Check(frame, journal with { Writes = writes }, saved: Saved(frame, journal)).Verdict);
    }

    [Theory]
    [InlineData("missing RT")]
    [InlineData("host return")]
    [InlineData("wrong RT PC")]
    [InlineData("wrong SSP before")]
    [InlineData("wrong SSP restored")]
    [InlineData("stale frame read")]
    [InlineData("wrong current writer")]
    [InlineData("wrong creator")]
    [InlineData("wrong CPU")]
    [InlineData("wrong bus")]
    [InlineData("wrong width")]
    [InlineData("wrong address")]
    [InlineData("wrong event order")]
    public void NativeReturnHypothesisRequiresTheCurrentRestoredGenerationAndBalancedSsp(string defect)
    {
        var frame = Frame(); var journal = Journal(frame); var read = Read(frame);
        read = defect switch
        {
            "missing RT" => read with { Reached = false },
            "host return" => read with { NativeInstructionHypothesis = false },
            "wrong RT PC" => read with { ReaderPc = 0x5CCD },
            "wrong SSP before" => read with { SspBefore = 0x47A },
            "wrong SSP restored" => read with { SspAfter = 0x47C },
            "stale frame read" => read with { Generation = frame.Generation },
            "wrong current writer" => read with { WriterPc = 0x2689 },
            "wrong creator" => read with { Creator = frame.Creator with { Invocation = "other-call" } },
            "wrong CPU" => read with { Machine = Machine() with { Cpu = "CPU-B" } },
            "wrong bus" => read with { Machine = Machine() with { Bus = "BUS-B" } },
            "wrong width" => read with { WidthBytes = 1 },
            "wrong address" => read with { Address = 0x47C },
            _ => read with { ModelEventIndex = 2 }
        };
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance, Check(frame, journal, read: read).Verdict);
    }

    [Fact]
    public void UnexpectedStackWriterInvalidatesTheCallProgressionEvenWithCorrectFinalReturnNumber()
    {
        var frame = Frame(); var journal = Journal(frame);
        var writes = journal.Writes.Append(new FirstRamWrite(9, 4, 0x5C79, 0, 2, 0x47C,
            "invented-extra-stack-write", "invented-SSP-gen1", "unowned-stack-history", frame.Creator)).ToArray();
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance, Check(frame, journal with { Writes = writes }).Verdict);
    }

    [Theory]
    [InlineData(0x47F)]
    [InlineData(1)]
    [InlineData(7)]
    [InlineData(0x83)]
    [InlineData(0x207)]
    public void ByteWritesToHighHalvesCannotHideBehindWordStartAddressChecks(int address)
    {
        var frame = Frame(); var journal = Journal(frame);
        var writes = journal.Writes.Append(new FirstRamWrite(9, 4, 0x5C79, address, 1, 0,
            "invented-high-byte-alias", "invented-overlapped-word", "unowned-byte-write", frame.Creator)).ToArray();
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance, Check(frame, journal with { Writes = writes }).Verdict);
    }

    [Theory]
    [InlineData(0x80)]
    [InlineData(0x81)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    public void ExtraIndexOrContextByteWritesCannotKeepBorrowingTheCallerEffectiveAddress(int address)
    {
        var frame = Frame(); var journal = Journal(frame);
        var writes = journal.Writes.Select((w, i) => w with { ModelOrdinal = i >= 3 ? i + 2 : i + 1 }).ToList();
        writes.Insert(3, new FirstRamWrite(4, 1, 0x5C67, address, 1, 1,
            "invented-context-clobber", "invented-prior-context", "unowned-context-write", frame.Creator));
        Assert.True(writes.Zip(writes.Skip(1)).All(pair => pair.First.ModelOrdinal < pair.Second.ModelOrdinal));
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance,
            Check(frame, journal with { Writes = writes }, saved: Saved(frame, journal)).Verdict);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void ExactOwnedMieEditsPreserveDdWithoutInventingTheirArithmeticFlags(bool set)
    {
        var frame = Frame(); var journal = Journal(frame);
        var writes = journal.Writes.Select(w => w with { ModelEventIndex = w.ModelEventIndex * 10 }).ToList();
        var insert = set ? 8 : 3;
        writes.Insert(insert, new FirstRamWrite(0, set ? 45 : 15, set ? 0x5C71 : 0x5C65, 5, 1,
            set ? 0x1D : 0x1C, "invented-owned-PSWH-edit", "invented-prior-PSWH",
            set ? "invented-MIE-set5C71" : "invented-MIE-clear5C65", frame.Creator));
        writes = writes.Select((w, i) => w with { ModelOrdinal = i + 1 }).ToList();
        Assert.Equal(FirstRamModelVerdict.SpecificationMatches,
            Check(frame, journal with { Writes = writes }, saved: Saved(frame, journal),
                read: Read(frame) with { ModelEventIndex = 50 }).Verdict);
    }

    [Theory]
    [InlineData("unknown writer")]
    [InlineData("DD clear")]
    [InlineData("wrong MIE")]
    [InlineData("unowned source")]
    [InlineData("wrong causal position")]
    [InlineData("read-one bits lost")]
    public void PswhWritesCannotClearDdOrBorrowExactMieProducerAuthority(string defect)
    {
        var frame = Frame(); var journal = Journal(frame);
        var writes = journal.Writes.Select(w => w with { ModelEventIndex = w.ModelEventIndex * 10 }).ToList();
        var write = new FirstRamWrite(0, defect == "wrong causal position" ? 45 : 15,
            defect == "unknown writer" ? 0x5C67 : 0x5C65, 5, 1,
            defect == "DD clear" ? 0x0C : defect == "wrong MIE" ? 0x1D :
                defect == "read-one bits lost" ? 0x10 : 0x1C,
            "invented-bad-PSWH-edit", "invented-prior-PSWH",
            defect == "unowned source" ? "forged-source" : "invented-MIE-clear5C65", frame.Creator);
        writes.Insert(defect == "wrong causal position" ? 8 : 3, write);
        writes = writes.Select((w, i) => w with { ModelOrdinal = i + 1 }).ToList();
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance,
            Check(frame, journal with { Writes = writes }, saved: Saved(frame, journal),
                read: Read(frame) with { ModelEventIndex = 50 }).Verdict);
    }

    [Theory]
    [InlineData(0x5555, 0x5555, false, true, 0x5C80)]
    [InlineData(0xAAAA, 0xAAAA, false, true, 0x5C80)]
    [InlineData(0, 1, true, false, 0x5C81)]
    [InlineData(0xFFFF, 0, false, false, 0x5C81)]
    public void OwnedWordComparisonDerivesBorrowEqualityAndJneFaultOrFallthrough(int left, int right,
        bool cf, bool zf, int next)
    {
        var comparison = FirstRamTestProvenanceFixture.Compare(left, right, "left-source", "right-source", Machine());
        Assert.Equal(cf, comparison.Cf); Assert.Equal(zf, comparison.Zf);
        Assert.Equal(next, FirstRamTestProvenanceFixture.NextAfterJne(comparison));
    }

    [Theory]
    [InlineData("unknown left")]
    [InlineData("unknown right")]
    [InlineData("missing source")]
    [InlineData("invalid producer")]
    [InlineData("intervening flag writer")]
    [InlineData("host ZF")]
    [InlineData("host CF")]
    public void ComparisonAndJneCannotUseUnknownSourcesOrHostFlags(string defect)
    {
        var comparison = Comparison();
        comparison = defect switch
        {
            "unknown left" => FirstRamTestProvenanceFixture.Compare(null, 0x5555, "l", "r", Machine()),
            "unknown right" => FirstRamTestProvenanceFixture.Compare(0x5555, null, "l", "r", Machine()),
            "missing source" => FirstRamTestProvenanceFixture.Compare(0x5555, 0x5555, null, "r", Machine()),
            "invalid producer" => comparison with { ProducerPc = 0x2714 },
            "intervening flag writer" => comparison with { NoInterveningFlagWriter = false },
            "host ZF" => comparison with { Zf = false },
            _ => comparison with { Cf = true }
        };
        Assert.Null(FirstRamTestProvenanceFixture.NextAfterJne(comparison));
        Assert.Equal(FirstRamModelVerdict.SpecificationMismatch, Check(Frame(), Journal(Frame()), comparison: comparison).Verdict);
    }

    [Fact]
    public void FailedPatternComparisonDoesNotBorrowAReachedRtWitness()
    {
        var frame = Frame(); var failed = FirstRamTestProvenanceFixture.Compare(
            0x5554, 0x5555, "invented-ST5C70/L5C7B", "invented-MOVX2-5C5C", Machine());
        Assert.Equal(0x5C81, FirstRamTestProvenanceFixture.NextAfterJne(failed));
        var result = Check(frame, Journal(frame), comparison: failed);
        Assert.Equal(FirstRamModelVerdict.SpecificationMismatch, result.Verdict);
        Assert.Null(result.ReturnPc); Assert.False(result.MatchingNativeReturnObserved);
    }

    [Theory]
    [InlineData("unknown numeric operands")]
    [InlineData("empty source identity")]
    public void AClaimedSourcesEstablishedBooleanCannotLaunderUnknownComparisonInputs(string defect)
    {
        var comparison = defect == "unknown numeric operands" ? Comparison() with
        {
            Left = null,
            Right = null,
            Cf = false,
            Zf = true,
            SourcesEstablished = true
        } : Comparison() with { LeftSource = "", SourcesEstablished = true };
        Assert.Null(FirstRamTestProvenanceFixture.NextAfterJne(comparison));
        Assert.Equal(FirstRamModelVerdict.SpecificationMismatch, Check(Frame(), Journal(Frame()), comparison: comparison).Verdict);
    }

    [Theory]
    [InlineData((int)FirstRamEntry.TechnicalHarnessEntry)]
    [InlineData((int)FirstRamEntry.ConditionalCallerEntry)]
    [InlineData((int)FirstRamEntry.NotEstablished)]
    [InlineData(999)]
    [InlineData(-1)]
    public void TechnicalOrConditionalEntryCannotBecomeActualRootBySupplyingConvenientInputs(int entry)
    {
        var result = FirstRamTestProvenanceFixture.CheckPreflight(CompleteHypothesis() with { Entry = (FirstRamEntry)entry });
        Assert.Equal(FirstRamModelVerdict.ExecutionPreflightBlocked, result.Verdict);
        Assert.Contains("caller entry", result.Barrier); Assert.False(result.ExecutionPermitted);
    }

    [Theory]
    [InlineData((int)FirstRamEntry.ActualResetEntryEstablished)]
    [InlineData((int)FirstRamEntry.RootedSoftwarePrefixEstablished)]
    public void EvenFullySuppliedHypotheticalRootPolicyCannotGrantActualPreflightPass(int entry)
    {
        var result = FirstRamTestProvenanceFixture.CheckPreflight(CompleteHypothesis() with { Entry = (FirstRamEntry)entry });
        Assert.Equal(FirstRamModelVerdict.SpecificationMatches, result.Verdict);
        Assert.Equal("InventedOnly", result.EvidenceDomain); Assert.False(result.ExecutionPermitted);
        Assert.Contains("cannot grant actual preflight PASS", result.Barrier);
        Assert.Equal(0, result.ActualRomExecutions); Assert.False(result.BoundedSameMachineRoundtripEstablished);
    }

    [Theory]
    [InlineData("ROM")]
    [InlineData("root")]
    [InlineData("early selftest")]
    [InlineData("native sources")]
    [InlineData("peripheral")]
    [InlineData("admission")]
    [InlineData("ranges")]
    [InlineData("budget")]
    [InlineData("CPU/Bus")]
    [InlineData("trace")]
    [InlineData("ALL journal")]
    [InlineData("frame")]
    [InlineData("terminal")]
    [InlineData("mechanism")]
    public void EveryMandatoryPreflightInputFailsClosedWhenUnknownOrFalse(string missing)
    {
        foreach (var value in new bool?[] { null, false })
        {
            var preflight = missing switch
            {
                "ROM" => CompleteHypothesis() with { OriginalRomBinding = value },
                "root" => CompleteHypothesis() with { RootContext = value },
                "early selftest" => CompleteHypothesis() with { EarlySelftests = value },
                "native sources" => CompleteHypothesis() with { NativeSources = value },
                "peripheral" => CompleteHypothesis() with { PeripheralSources = value },
                "admission" => CompleteHypothesis() with { InstructionAdmission = value },
                "ranges" => CompleteHypothesis() with { BoundedRanges = value },
                "budget" => CompleteHypothesis() with { InstructionBudget = value },
                "CPU/Bus" => CompleteHypothesis() with { OneCpuBus = value },
                "trace" => CompleteHypothesis() with { TraceContinuity = value },
                "ALL journal" => CompleteHypothesis() with { AllWriteJournal = value },
                "frame" => CompleteHypothesis() with { FrameSourceReader = value },
                "terminal" => CompleteHypothesis() with { TerminalStop268C = value },
                _ => CompleteHypothesis() with { SafeReadOnlyMechanism = value }
            };
            var result = FirstRamTestProvenanceFixture.CheckPreflight(preflight);
            Assert.Equal(FirstRamModelVerdict.ExecutionPreflightBlocked, result.Verdict);
            Assert.False(result.ExecutionPermitted); Assert.Equal(0, result.ActualRomExecutions);
        }
    }

    [Fact]
    public void EarliestRootOrSelftestBarrierCannotBeHiddenByLaterSuccessfulFrameAlgebra()
    {
        var rootMissing = CompleteHypothesis() with { RootContext = null, EarlySelftests = null, InstructionAdmission = null };
        Assert.Equal("Root reaching context", FirstRamTestProvenanceFixture.CheckPreflight(rootMissing).Barrier);
        var earlyMissing = rootMissing with { RootContext = true };
        Assert.Equal("Early selftest history", FirstRamTestProvenanceFixture.CheckPreflight(earlyMissing).Barrier);
        var invented = Check(Frame(), Journal(Frame()));
        Assert.Equal(FirstRamModelVerdict.SpecificationMatches, invented.Verdict);
        Assert.False(invented.BoundedSameMachineRoundtripEstablished);
    }

    [Fact]
    public void SecondCalCreatorHas2690AndCannotCopyOrPromoteTheFirstReturn()
    {
        var first = Frame();
        var second = first.Creator with { CallPc = 0x268D, ReturnPc = 0x268D + 3, Invocation = "invented-second-call" };
        Assert.Equal(0x2690, second.ReturnPc); Assert.NotEqual(first.Creator, second);
        var journal = Journal(first);
        Assert.Equal(FirstRamModelVerdict.InvalidProvenance,
            Check(first, journal, read: Read(first) with { Creator = second }).Verdict);
        var notFirst = FirstRamTestProvenanceFixture.FirstCall(Ssp(), Pattern(), Index(), Context(), second, "second-frame");
        Assert.Equal(FirstRamModelVerdict.SpecificationMismatch, notFirst.Verdict);
        Assert.False(notFirst.NativeCallFrameCreated);
    }

    [Theory]
    [InlineData("BoundedSameMachineRoundtripEstablished")]
    [InlineData("MatchingNativeReturnObserved")]
    [InlineData("ActualResetEntryEstablished")]
    [InlineData("fullboot")]
    [InlineData("M2ap promoted")]
    [InlineData("DATA019B semantic owner")]
    [InlineData("RT5CCD")]
    [InlineData("RT5801")]
    [InlineData("IRQ delivered")]
    [InlineData("all 510 iterations")]
    public void InventedFirstCallSpecificationCannotPromoteAnyActualOrHistoricalStatus(string requested)
    {
        var result = Check(Frame(), Journal(Frame()));
        Assert.Equal(FirstRamModelVerdict.SpecificationMatches, result.Verdict);
        Assert.Throws<InvalidDataException>(() => FirstRamTestProvenanceFixture.RequireActualObservation(result, requested));
        Assert.Equal("InventedOnly", result.EvidenceDomain); Assert.Equal(0, result.ActualRomExecutions);
        Assert.Null(result.ActualEventIndex); Assert.Null(result.ActualGlobalWriteOrdinal);
        Assert.False(result.MatchingNativeReturnObserved); Assert.False(result.BoundedSameMachineRoundtripEstablished);
        Assert.False(result.FullBootEstablished); Assert.False(result.ExecutionPermitted);
    }
}
