using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class Pre063BCallerProvenanceTests
{
    private static SoftwareBitWrite W(int ordinal, int pc = 0x2345, int eventIndex = 0) => new(pc, eventIndex, ordinal);

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void FirstShiftOwnsBit1ButCannotBootstrapFirstReaderOrReturn(bool bit0)
    {
        var bits = new SoftwareBitProvenance(0x19B, 0); bits.WriteBit(0, bit0, W(0)); var initial = bits.Bit(0).Owner;
        var caller = new PreCallerProvenanceFixture(bits); var frame = caller.Begin(0x1230, 0, 0x700, 5, CallerSourceKind.NativeOwned);
        bits.ShiftLeft(W(11)); Assert.Equal(bit0, bits.Bit(1).Value); Assert.Same(initial, bits.Bit(1).Owner!.Source);
        Assert.Null(bits.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => caller.Reader(bits, 0x2350, null));
        Assert.Throws<InvalidDataException>(() => caller.Return(frame, 0x2360, 0x2360, frame.ReturnPc));
        Assert.Throws<InvalidDataException>(() => caller.Begin(0x1250, 0, 0x700, 5, CallerSourceKind.NativeOwned));
        Assert.Same(frame, caller.Pending); Assert.Equal(1, caller.HypotheticalCalls); Assert.Equal(0, caller.ActualRomExecutions);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void TwoHypotheticalShiftsTransferLineageButAreNotTwoActualCalls(bool bit0)
    {
        var bits = new SoftwareBitProvenance(0x19B, 0); bits.WriteBit(0, bit0, W(0)); var source = bits.Bit(0).Owner;
        bits.ShiftLeft(W(4)); var first = bits.Bit(1).Owner;
        bits.ShiftLeft(W(9, eventIndex: 1)); var second = bits.Bit(2).Owner!;
        Assert.Same(first, second.Source); Assert.Same(source, second.Source!.Source); Assert.Equal(bit0, second.Value);
        Assert.Equal(9, second.Writer.GlobalWriteOrder); Assert.Equal(3, bits.StorageGeneration);
        bits.RequireReader(0x2350, 2, bit0, second);
        Assert.Equal(0, new PreCallerProvenanceFixture().ActualRomExecutions);
        // Algebraic transfer does not provide the first blocked reader or native RT.
    }

    [Fact]
    public void SameValueZeroShiftsAreFreshButFirstBit2IsStillUnknown()
    {
        var bits = new SoftwareBitProvenance(0x19B, 0); bits.WriteBit(0, false, W(0));
        bits.ShiftLeft(W(1)); var first = bits.Bit(1).Owner; Assert.False(bits.Bit(2).Value); Assert.Null(bits.Bit(2).Owner);
        bits.ShiftLeft(W(2)); var second = bits.Bit(2).Owner!;
        Assert.False(second.Value); Assert.Same(first, second.Source); Assert.Equal(3, bits.StorageGeneration);
        Assert.Equal(2, second.Writer.GlobalWriteOrder);
    }

    [Theory]
    [InlineData("alias")]
    [InlineData("byte")]
    [InlineData("word")]
    public void InterveningUnownedEffectInvalidatesSecondShift(string kind)
    {
        var bits = new SoftwareBitProvenance(0x19B, 0); bits.WriteBit(0, false, W(0)); bits.ShiftLeft(W(1));
        if (kind == "alias") bits.UnknownAlias(W(2));
        else if (kind == "byte") bits.WriteByte(0x19B, 0, Enumerable.Repeat(SoftwareBitSource.Unknown(false), 8).ToArray(), W(2));
        else bits.WriteWord(0x19B, 0, Enumerable.Repeat(SoftwareBitSource.Unknown(false), 16).ToArray(), W(2));
        bits.ShiftLeft(W(3)); Assert.Null(bits.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => bits.RequireReader(0x2350, 2, false, null));
    }

    [Theory]
    [InlineData((int)CallerSourceKind.ResetOnly)]
    [InlineData((int)CallerSourceKind.TechnicalOnly)]
    [InlineData((int)CallerSourceKind.Unknown)]
    public void Slot5NumericValueIsNotRuntimeCallerAuthority(int source)
    {
        var caller = new PreCallerProvenanceFixture();
        Assert.Throws<InvalidDataException>(() => caller.Begin(0x1230, 0, 0x700, 5, (CallerSourceKind)source));
        Assert.Null(caller.Pending); Assert.Equal(0, caller.HypotheticalCalls);
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    [InlineData(true, true)]
    public void UnresolvedIrqOrTimerBlocksEvenOwnedToySlot(bool irq, bool timer)
    {
        var caller = new PreCallerProvenanceFixture();
        Assert.Throws<InvalidDataException>(() => caller.Begin(0x1230, 0, 0x700, 5, CallerSourceKind.NativeOwned, irq, timer));
        Assert.Null(caller.Pending); Assert.Equal(0, caller.ActualRomExecutions);
    }

    [Fact]
    public void MissingCallerAndWrongMachineBitWriterCannotAuthorizeReader()
    {
        var bits = new SoftwareBitProvenance(0x19B, 0); bits.WriteBit(2, false, W(0));
        var other = new SoftwareBitProvenance(0x19B, 0); other.WriteBit(2, false, W(0));
        var caller = new PreCallerProvenanceFixture(bits);
        Assert.Throws<InvalidDataException>(() => caller.Reader(bits, 0x2350, bits.Bit(2).Owner));
        caller.Begin(0x1230, 0, 0x700, 5, CallerSourceKind.NativeOwned);
        Assert.Throws<InvalidDataException>(() => caller.Reader(bits, 0x2350, other.Bit(2).Owner));
        Assert.Throws<InvalidDataException>(() => caller.Reader(other, 0x2350, other.Bit(2).Owner));
    }

    [Theory]
    [InlineData("clone")]
    [InlineData("foreign")]
    [InlineData("host")]
    [InlineData("stale")]
    [InlineData("wrongRt")]
    [InlineData("alias")]
    public void CorrectReturnWordDoesNotProveCurrentNativeFrame(string forgery)
    {
        var bits = new SoftwareBitProvenance(0x19B, 0); bits.WriteBit(2, false, W(0));
        var caller = new PreCallerProvenanceFixture(bits); var old = caller.Begin(0x1230, 0, 0x700, 5, CallerSourceKind.NativeOwned);
        caller.Reader(bits, 0x2350, bits.Bit(2).Owner); caller.Return(old, 0x2360, 0x2360, old.ReturnPc);
        var fresh = caller.Begin(0x1230, 1, 0x700, 5, CallerSourceKind.RetainedNative, globalOrder: 31); caller.Reader(bits, 0x2350, bits.Bit(2).Owner);
        var observed = forgery == "clone" ? fresh with { } : forgery == "stale" ? old : forgery == "foreign" ? fresh with { Machine = new object() } : fresh;
        Assert.Throws<InvalidDataException>(() => caller.Return(observed, forgery == "wrongRt" ? 0x2340 : 0x2360,
            0x2360, fresh.ReturnPc, hostShortcut: forgery == "host", unknownAlias: forgery == "alias"));
        Assert.Same(fresh, caller.Pending); Assert.True(fresh.GlobalOrder > old.GlobalOrder);
        Assert.Equal(old.ReturnPc, fresh.ReturnPc); Assert.Equal(0, caller.ActualRomExecutions);
    }

    [Fact]
    public void ConflictingBranchesAreSeparatePathsNotAddressOrderedCalls()
    {
        var paths = PreCallerProvenanceFixture.Paths();
        Assert.Contains(paths, p => p.Contains(0x1230)); Assert.Contains(paths, p => p.Contains(0x1250));
        Assert.DoesNotContain(paths, p => p.Contains(0x1230) && p.Contains(0x1250));
        Assert.Contains(paths, p => !p.Contains(0x1230) && !p.Contains(0x1250));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void PostReturnBit3SetMakesOldBitRbGateSkipLaterCall(bool earlierReturned)
    {
        var bits = new SoftwareBitProvenance(0x12A, 0); bits.WriteBit(3, earlierReturned, W(0));
        var oldBit3 = bits.Bit(3).Value; var zf = !oldBit3;
        bits.WriteBit(3, false, W(1)); Assert.False(bits.Bit(3).Value);
        var jneTaken = !zf; Assert.Equal(earlierReturned, jneTaken);
        Assert.Equal(!earlierReturned, !jneTaken); // Post-RB numeric0 cannot choose the CAL.
    }

    [Theory]
    [InlineData("initial00a2")]
    [InlineData("slot5")]
    [InlineData("perCallSlot")]
    [InlineData("producerIndex")]
    [InlineData("hostPatch00A2")]
    [InlineData("force571F")]
    [InlineData("hostPC0611")]
    [InlineData("hostPC0635")]
    [InlineData("hostReturn0614")]
    [InlineData("hostReturn0638")]
    [InlineData("callerMode")]
    [InlineData("producerMode")]
    [InlineData("mode011f2For0611")]
    [InlineData("mode011f2For0635")]
    [InlineData("old019b1")]
    [InlineData("old019b2")]
    [InlineData("simulateIrqEntry")]
    [InlineData("inferredTimerTick")]
    public void HistoricalScenarioNeverAcceptsNewCallerSlotModeOrReturnSeeds(string field)
    {
        foreach (var key in new[] { "calls", "initialState" })
        {
            var node = JsonNode.Parse(P28Data0136TailTests.Scenario().ToJson())!;
            var target = key == "calls" ? node[key]![0]! : node[key]!;
            target[field] = 5;
            Assert.Throws<InvalidDataException>(() => P28Data0136TailScenario.Parse(node.ToJsonString()));
        }
    }
}
