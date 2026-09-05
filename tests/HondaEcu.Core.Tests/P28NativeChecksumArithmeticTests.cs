namespace HondaEcu.Core.Tests;

public sealed class P28NativeChecksumArithmeticTests
{
    [Fact]
    public void ContractIsFullRomZeroResidueWithoutInventedStorageOrExclusions()
    {
        var contract = P28NativeChecksumArithmetic.Contract;
        Assert.Null(contract.StoredChecksumOffset);
        Assert.Empty(contract.ExcludedRanges);
        Assert.Equal(new ByteRange(0, 32768), Assert.Single(contract.Coverage));
        Assert.Equal(0, contract.InitialAccumulator);
        Assert.Equal(0, contract.ExpectedResidue);
        Assert.Equal(512, contract.RequiredInvocations);
        Assert.Equal(64, contract.BytesPerInvocation);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(63)]
    [InlineData(64)]
    [InlineData(32767)]
    public void EveryBoundaryByteIsCovered(int offset)
    {
        var bytes = new byte[32768];
        bytes[offset] = 1;
        var image = RomImage.FromBytes(bytes);
        var result = P28NativeChecksumArithmetic.Calculate(image);
        Assert.Equal((byte)1, result.ComputedResult);
        Assert.False(result.ResidueMatches);
        Assert.Equal(32768, result.CoveredByteCount);
        Assert.Equal(bytes, image.ToArray());
    }

    [Fact]
    public void ModuloWrapAndCompensatingChangesDoNotRequireEveryMutationToFail()
    {
        var bytes = new byte[32768];
        bytes[63] = 255;
        bytes[64] = 1;
        var result = P28NativeChecksumArithmetic.Calculate(RomImage.FromBytes(bytes));
        Assert.True(result.ResidueMatches);
        Assert.Equal((byte)255, result.Checkpoints[0].ComputedByte);
        Assert.Equal((byte)0, result.Checkpoints[1].ComputedByte);
        Assert.Equal(1, result.Checkpoints[0].CounterAfter);
        Assert.Equal(0, result.Checkpoints[^1].CounterAfter);
        Assert.Equal(512, result.Checkpoints.Count);
        Assert.Equal((byte)0, result.Checkpoints[^1].SumAfter);
    }

    [Fact]
    public void WholeWordBothBytesAndControlByteContribute()
    {
        var bytes = new byte[32768];
        bytes[2] = 255;
        bytes[3] = 2;
        bytes[P28NativeChecksumArithmetic.GateOffset] = 3;
        var result = P28NativeChecksumArithmetic.Calculate(RomImage.FromBytes(bytes));
        Assert.Equal((byte)4, result.ComputedResult);
        Assert.Equal((byte)4, result.Checkpoints[^1].ComputedByte);
        Assert.Equal((byte)0, result.Checkpoints[^1].SumAfter);
    }

    [Fact]
    public void WrongSizeIsNotPaddedOrTruncated() => Assert.Throws<RomSizeException>(() =>
        P28NativeChecksumArithmetic.Calculate(RomImage.FromBytes(new byte[32767])));
}
