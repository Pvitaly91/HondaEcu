using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class SoftwareBitProvenanceTests
{
    private static SoftwareBitWrite W(int order, int pc = 0x3456, int eventIndex = 0) => new(pc, eventIndex, order);
    private static SoftwareBitSource[] Code(ushort value, int width = 8) => Enumerable.Range(0, width)
        .Select(i => SoftwareBitSource.CodeConstant((value & (1 << i)) != 0)).ToArray();

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void InventedRbOrSbBit0NeverBecomesBit2Producer(bool set)
    {
        var model = new SoftwareBitProvenance(0x019B, 0x55);
        model.WriteBit(2, true, W(0)); var owner = model.Bit(2).Owner;
        model.WriteBit(0, set, W(1, 0x4567));
        Assert.Equal(2, model.StorageGeneration); Assert.Same(owner, model.Bit(2).Owner);
        Assert.Equal(SoftwareBitOrigin.InheritedThroughRmw, model.Bit(2).Origin);
        Assert.Equal(0, model.Bit(0).Owner!.Bit); Assert.Equal(1, model.Bit(0).Owner!.Writer.GlobalWriteOrder);
        model.RequireReader(0x5678, 2, true, owner);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void NativeBit2WriteIsFreshEvenWhenNumericValueIsUnchanged(bool value)
    {
        var model = new SoftwareBitProvenance(0x019B, value ? (byte)4 : (byte)0);
        model.WriteBit(2, value, W(0)); var old = model.Bit(2).Owner;
        model.WriteBit(2, value, W(8, eventIndex: 1)); var fresh = model.Bit(2).Owner;
        Assert.NotSame(old, fresh); Assert.Equal(2, model.StorageGeneration);
        Assert.Equal(8, fresh!.Writer.GlobalWriteOrder); Assert.Equal(1, fresh.Writer.EventIndex);
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, value, old));
        model.RequireReader(0x5678, 2, value, fresh);
        Assert.Throws<InvalidDataException>(() => model.WriteBit(2, value, W(0, eventIndex: 2)));
        Assert.Same(fresh, model.Bit(2).Owner);
    }

    [Fact]
    public void OwnedWholeByteSourceCreatesOwnerButUnknownSourceInvalidatesIt()
    {
        var model = new SoftwareBitProvenance(0x019B, 0);
        model.WriteByte(0x019B, 4, Code(4), W(0)); var owned = model.Bit(2).Owner;
        Assert.Equal(SoftwareBitOrigin.NativeWholeByteWritten, owned!.Origin);
        model.RequireReader(0x5678, 2, true, owned);
        model.WriteByte(0x019B, 4, Enumerable.Range(0, 8).Select(i => SoftwareBitSource.Unknown(i == 2)).ToArray(), W(1));
        Assert.Equal(2, model.StorageGeneration); Assert.True(model.Bit(2).Value); Assert.Null(model.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, true, owned));
    }

    [Theory]
    [InlineData(0x019A)]
    [InlineData(0x019B)]
    public void WordAlignmentUses019A019BNot019B019C(int encodedAddress)
    {
        var model = new SoftwareBitProvenance(0x019B, 0);
        model.WriteWord(encodedAddress, 0x0400, Code(0x0400, 16), W(0));
        var owner = model.Bit(2).Owner;
        Assert.True(model.Bit(2).Value); Assert.Equal(SoftwareBitOrigin.NativeWholeWordWritten, owner!.Origin);
        model.RequireReader(0x5678, 2, true, owner);
        model.WriteByte(0x019A, 255, Code(255), W(1)); Assert.Same(owner, model.Bit(2).Owner);
        model.WriteWord(0x019C, 0, Code(0, 16), W(2)); Assert.Same(owner, model.Bit(2).Owner);
        Assert.Equal(1, model.StorageGeneration);
    }

    [Fact]
    public void UnknownAliasInvalidatesProofDespiteUnchangedDiagnosticValue()
    {
        var model = new SoftwareBitProvenance(0x019B, 0); model.WriteBit(2, false, W(0)); var owner = model.Bit(2).Owner;
        model.UnknownAlias(W(1)); Assert.False(model.Bit(2).Value); Assert.Equal(1, model.StorageGeneration);
        Assert.Equal(SoftwareBitOrigin.UnknownIndirectAlias, model.Bit(2).Origin);
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, false, owner));
        model.WriteBit(0, false, W(2)); Assert.Null(model.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, false, owner));
    }

    [Fact]
    public void EqualFieldsWrongWriterCloneAndSecondMachineCannotSupplyIdentity()
    {
        var model = new SoftwareBitProvenance(0x019B, 0); model.WriteBit(2, true, W(0)); var owner = model.Bit(2).Owner!;
        var other = new SoftwareBitProvenance(0x019B, 0); other.WriteBit(2, true, W(0));
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, true, other.Bit(2).Owner));
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, true, owner with { }));
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, true, owner with { Writer = W(0, 0x2345) }));
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 1, true, owner));
        var forged = Code(4); forged[2] = new(true, owner.Origin, owner with { });
        Assert.Throws<InvalidDataException>(() => model.WriteByte(0x019B, 4, forged, W(1)));
        Assert.Equal(1, model.StorageGeneration); Assert.Same(owner, model.Bit(2).Owner);
    }

    [Theory]
    [InlineData((int)SoftwareBitOrigin.InitialDiagnosticScratch)]
    [InlineData((int)SoftwareBitOrigin.ResetDependent)]
    [InlineData((int)SoftwareBitOrigin.TimerDependent)]
    [InlineData((int)SoftwareBitOrigin.IrqDependent)]
    [InlineData((int)SoftwareBitOrigin.PeripheralDependent)]
    [InlineData((int)SoftwareBitOrigin.TechnicalSnapshot)]
    public void NonRuntimeNumericSourcesNeverAuthorizeReader(int originValue)
    {
        var model = new SoftwareBitProvenance(0x019B, 0);
        model.WriteByte(0x019B, 0, Enumerable.Repeat(new SoftwareBitSource(false, (SoftwareBitOrigin)originValue), 8).ToArray(), W(0));
        Assert.Null(model.Bit(2).Owner);
        Assert.Throws<InvalidDataException>(() => model.RequireReader(0x5678, 2, false, null));
    }

    [Fact]
    public void ShiftDependsOnSourceBit1NotOldNumericBit2OrBit0StorageGeneration()
    {
        var model = new SoftwareBitProvenance(0x019B, 0);
        model.WriteBit(0, true, W(0)); var source = model.Bit(0).Owner;
        model.ShiftLeft(W(1)); Assert.True(model.Bit(1).Value); Assert.Same(source, model.Bit(1).Owner!.Source);
        Assert.Null(model.Bit(2).Owner); // Old bit1 was diagnostic scratch, even though numeric0 is known.
        model.WriteBit(0, false, W(2)); model.ShiftLeft(W(3));
        var secondShift = model.Bit(2).Owner!; Assert.True(secondShift.Value);
        Assert.Same(source, secondShift.Source!.Source);
        model.RequireReader(0x5678, 2, true, secondShift);
        // This is invented model chronology, not a replayed enclosing firmware caller.
    }

    [Theory]
    [InlineData("initial019b2")]
    [InlineData("perEvent019b2")]
    [InlineData("branch5722")]
    [InlineData("expectedBranch")]
    [InlineData("hostWrite019B")]
    [InlineData("hostWrite019AWord")]
    [InlineData("fakeOwnerGeneration")]
    [InlineData("resetDefaultAsOwner")]
    [InlineData("rbBit0AsBit2Owner")]
    [InlineData("ownerSnapshot")]
    [InlineData("hostPC5722")]
    [InlineData("hostPC5725")]
    [InlineData("hostPC5733")]
    [InlineData("secondMachine")]
    [InlineData("serializedHandoff")]
    public void HistoricalM2ahClosedSchemaStillRejectsOwnerAndBranchInjections(string field)
    {
        foreach (var level in new[] { "initialState", "calls" })
        {
            var node = JsonNode.Parse(P28Data0136TailTests.Scenario().ToJson())!;
            var target = level == "calls" ? node[level]![0]! : node[level]!;
            target[field] = 0;
            Assert.Throws<InvalidDataException>(() => P28Data0136TailScenario.Parse(node.ToJsonString()));
        }
    }
}
