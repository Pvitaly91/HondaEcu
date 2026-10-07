using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class Data019BBootstrapProvenanceTests
{
    private static SoftwareBitWrite W(int order, int pc = 0x4560, int eventIndex = 0) => new(pc, eventIndex, order);
    private static BootstrapPath Path(BootstrapEdgeKind kind = BootstrapEdgeKind.Literal) =>
        new(0x1200, 0x1210, 0x1230, [new(0x1200, 0x1210), new(0x1210, 0x1220, kind), new(0x1220, 0x1230)]);

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void IndependentOldBit1TransfersToBit2WithoutPriorReader(bool bit1)
    {
        var model = new BootstrapContinuityFixture();
        model.InitializationWord(0x219A, bit1 ? (ushort)0x0200 : (ushort)0, W(0), 0x1210);
        var independent = model.Bits.Bit(1).Owner;
        model.Bits.ShiftLeft(W(1)); var transferred = model.Bits.Bit(2).Owner!;
        Assert.Same(independent, transferred.Source); Assert.Equal(bit1, transferred.Value);
        model.RequireStaticReader(2, transferred, Path());
        Assert.False(model.CurrentRuntimeOwnerEstablished); Assert.Equal(0, model.ActualRomExecutions);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void NoShiftRouteUsesIndependentBit2NotStorageNumber(bool bit2)
    {
        var model = new BootstrapContinuityFixture();
        model.InitializationWord(0x219A, bit2 ? (ushort)0x0400 : (ushort)0, W(0), 0x1210);
        var owner = model.Bits.Bit(2).Owner;
        model.RequireStaticReader(2, owner, Path()); Assert.Equal(1, model.Bits.StorageGeneration);
        Assert.False(model.CurrentRuntimeOwnerEstablished);
    }

    [Fact]
    public void KnownBit0StillCannotBootstrapUnknownOldBit1()
    {
        var model = new BootstrapContinuityFixture(); model.Bits.WriteBit(0, true, W(0));
        model.Bits.ShiftLeft(W(1)); Assert.NotNull(model.Bits.Bit(1).Owner); Assert.Null(model.Bits.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, null, Path()));
    }

    [Fact]
    public void ResetValueReferenceDoesNotProveSourceToReaderContinuity()
    {
        var model = new BootstrapContinuityFixture(); model.ResetReference(0, W(0));
        Assert.False(model.Bits.Bit(2).Value); Assert.Null(model.Bits.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, null, Path()));
    }

    [Fact]
    public void CircularEarlierReaderCannotJustifyItsOwnInitializationSource()
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(0), 0x1210);
        var circular = new BootstrapPath(0x1200, 0x1210, 0x1230,
            [new(0x1200, 0x1220), new(0x1220, 0x1210, BootstrapEdgeKind.PriorUnprovedReader),
             new(0x1210, 0x1220), new(0x1210, 0x1230)]);
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, model.Bits.Bit(2).Owner, circular));
        Assert.Equal(0, model.ActualRomExecutions);
    }

    [Theory]
    [InlineData(0x5500)]
    [InlineData(0xAA00)]
    public void TemporaryTestPatternCannotOwnRestoredUnknownPriorWord(int pattern)
    {
        var model = new BootstrapContinuityFixture(4);
        var oldSources = Enumerable.Range(0, 16).Select(i => SoftwareBitSource.Unknown(i == 10)).ToArray();
        model.InitializationWord(0x219A, (ushort)pattern, W(0), 0x1210); var temporary = model.Bits.Bit(2).Owner;
        model.Bits.WriteWord(0x219A, 0x0400, oldSources, W(1));
        Assert.Equal(2, model.Bits.StorageGeneration); Assert.True(model.Bits.Bit(2).Value); Assert.Null(model.Bits.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, temporary, Path()));
    }

    [Theory]
    [InlineData("possibleAlias")]
    [InlineData("sameNumericUnknownOverwrite")]
    public void IndependentInitializationCanBeInvalidated(string effect)
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(0), 0x1210);
        var owner = model.Bits.Bit(2).Owner;
        if (effect == "possibleAlias") model.Bits.UnknownAlias(W(1));
        else model.Bits.WriteByte(0x219B, 0, Enumerable.Repeat(SoftwareBitSource.Unknown(false), 8).ToArray(), W(1));
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, owner, Path()));
        Assert.Equal(effect == "possibleAlias" ? 1 : 2, model.Bits.StorageGeneration); // Possible alias is not an observed write.
    }

    [Fact]
    public void SameValueInitializationIsFreshButStillOnlyStatic()
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(0), 0x1210);
        var old = model.Bits.Bit(2).Owner;
        model.InitializationWord(0x219A, 0, W(7, eventIndex: 1), 0x1210); var fresh = model.Bits.Bit(2).Owner;
        Assert.NotSame(old, fresh); Assert.Equal(2, model.Bits.StorageGeneration);
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, old, Path()));
        model.RequireStaticReader(2, fresh, Path()); Assert.Equal(0, model.ActualRomExecutions);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Bit0RmwPreservesIndependentBit1AndBit2(bool bit0)
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0x0600, W(0), 0x1210);
        var bit1 = model.Bits.Bit(1).Owner; var bit2 = model.Bits.Bit(2).Owner;
        model.Bits.WriteBit(0, bit0, W(1));
        Assert.Same(bit1, model.Bits.Bit(1).Owner); Assert.Same(bit2, model.Bits.Bit(2).Owner);
        model.RequireStaticReader(1, bit1, Path()); model.RequireStaticReader(2, bit2, Path());
    }

    [Theory]
    [InlineData(0x219A)]
    [InlineData(0x219B)]
    public void DataWordAlignmentOwnsUpperByteButNotNextPair(int encodedAddress)
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(encodedAddress, 0x0600, W(0), 0x1210);
        Assert.True(model.Bits.Bit(1).Value); Assert.True(model.Bits.Bit(2).Value); var owner = model.Bits.Bit(2).Owner;
        model.InitializationWord(0x219C, 0, W(1), 0x1210); Assert.Same(owner, model.Bits.Bit(2).Owner);
        model.RequireStaticReader(2, owner, Path());
    }

    [Theory]
    [InlineData(0x21, 0x019B)]
    [InlineData(0x41, 0x029B)]
    public void ConditionalPageCopyCannotBorrowListingContextAsRuntime(int lrb, int address)
    {
        var classified = SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.OffPage, 0x9B, 8, Lrb: lrb), 0x019B);
        Assert.Equal(address, classified.EffectiveAddress);
        Assert.Equal(address == 0x019B ? SoftwareAliasDomain.CanAlias : SoftwareAliasDomain.CannotAlias, classified.Domain);
        Assert.Equal(SoftwareAliasDomain.UnknownDomain, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.OffPage, 0x9B, 8), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.CanAlias, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.LocalRegister, 3, 8, Lrb: 0x33), 0x019B).Domain);
    }

    [Fact]
    public void AlternateEntryBypassingInitializationDefeatsDominance()
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(0), 0x1210);
        var path = Path(); path = path with { Edges = path.Edges.Concat([new BootstrapEdge(0x1200, 0x1230)]).ToArray() };
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, model.Bits.Bit(2).Owner, path));
    }

    [Theory]
    [InlineData((int)BootstrapEdgeKind.PossibleAlias)]
    [InlineData((int)BootstrapEdgeKind.ReturnSummary)]
    [InlineData((int)BootstrapEdgeKind.PriorUnprovedReader)]
    [InlineData((int)BootstrapEdgeKind.IrqTransition)]
    public void UnprovedContinuationsCannotBecomeFirstReaderHistory(int kind)
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(0), 0x1210);
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, model.Bits.Bit(2).Owner, Path((BootstrapEdgeKind)kind)));
        Assert.False(model.CurrentRuntimeOwnerEstablished); Assert.Equal(0, model.ActualRomExecutions);
    }

    [Fact]
    public void HazardOnDeadPathDoesNotInvalidateExplicitStaticDomain()
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(0), 0x1210);
        var path = Path(); path = path with { Edges = path.Edges.Concat([new BootstrapEdge(0x1200, 0x1290, BootstrapEdgeKind.PossibleAlias)]).ToArray() };
        model.RequireStaticReader(2, model.Bits.Bit(2).Owner, path);
    }

    [Theory]
    [InlineData("otherMachine")]
    [InlineData("clone")]
    [InlineData("writer")]
    [InlineData("event")]
    [InlineData("ordinal")]
    public void NumericCoincidenceDoesNotTransferSourceIdentity(string forgery)
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(0), 0x1210);
        var owner = model.Bits.Bit(2).Owner!;
        var other = new BootstrapContinuityFixture(); other.InitializationWord(0x219A, 0, W(0), 0x1210);
        var fake = forgery switch
        {
            "otherMachine" => other.Bits.Bit(2).Owner,
            "writer" => owner with { Writer = W(0, 0x4570) },
            "event" => owner with { Writer = W(0, eventIndex: 1) },
            "ordinal" => owner with { Writer = W(1) },
            _ => owner with { }
        };
        Assert.Throws<InvalidDataException>(() => model.RequireStaticReader(2, fake, Path()));
    }

    [Fact]
    public void EventAndGlobalOrderCannotResetAcrossSourceWrites()
    {
        var model = new BootstrapContinuityFixture(); model.InitializationWord(0x219A, 0, W(20, eventIndex: 2), 0x1210);
        var owner = model.Bits.Bit(2).Owner;
        Assert.Throws<InvalidDataException>(() => model.InitializationWord(0x219A, 0, W(21, eventIndex: 1), 0x1210));
        Assert.Throws<InvalidDataException>(() => model.InitializationWord(0x219A, 0, W(0, eventIndex: 3), 0x1210));
        Assert.Same(owner, model.Bits.Bit(2).Owner);
    }

    [Theory]
    [InlineData(0, false, false, false)]
    [InlineData(1, true, true, true)]
    [InlineData(0x80, false, true, false)]
    [InlineData(0xFF, true, false, true)]
    public void PrimaryOffObjectSllbSpecificationRetainsZfHcAndDd(int value, bool zf, bool hc, bool dd)
    {
        var expected = BootstrapContinuityFixture.OffObjectShiftSpecification((byte)value, zf, hc, dd);
        Assert.Equal((byte)(value << 1), expected.Value); Assert.Equal((value & 0x80) != 0, expected.Cf);
        Assert.Equal(zf, expected.Zf); Assert.Equal(hc, expected.Hc); Assert.Equal(dd, expected.Dd);
        // Specification test only; not acceptance of the known generic Rust discrepancy.
    }

    [Theory]
    [InlineData("initial019b1")]
    [InlineData("initial019b2")]
    [InlineData("nativeInitializationSnapshot")]
    [InlineData("first5722Branch")]
    [InlineData("bootstrapOwnerHandoff")]
    [InlineData("resetToIrqContinuity")]
    public void ClosedHistoricalScenarioDoesNotAcceptBootstrapRepairFields(string field)
    {
        foreach (var level in new[] { "initialState", "calls" })
        {
            var node = JsonNode.Parse(P28Data0136TailTests.Scenario().ToJson())!;
            (level == "calls" ? node[level]![0]! : node[level]!)[field] = 0;
            Assert.Throws<InvalidDataException>(() => P28Data0136TailScenario.Parse(node.ToJsonString()));
        }
    }
}
