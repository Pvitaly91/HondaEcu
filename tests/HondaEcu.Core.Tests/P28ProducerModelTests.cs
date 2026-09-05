using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class P28ProducerModelTests
{
    [Fact]
    public void FirstZeroWritesFallbackInsteadOfPreservingOldTAndPreservesIncomingS()
    {
        foreach (var s in new[] { false, true })
        {
            var input = Input([0, 100, 100, 100, 100, 100], s: s);
            var result = P28ProducerModel.Evaluate(input);
            Assert.True(result.Resolved);
            Assert.True(result.TWritten);
            Assert.Equal(ushort.MaxValue, result.T);
            Assert.Equal(s, result.S);
            Assert.True(result.FallbackFlag);
            Assert.Equal(P28ProducerDisposition.ZeroSampleFallback, result.Disposition);
            Assert.Empty(result.UsedAssumptions);
            Assert.Equal(input.Samples, result.Samples);
        }
    }

    [Fact]
    public void StrictStopsBeforeFirstUnconfirmedAddAndDoesNotCallItPreservationEvidenceForACompletedProducer()
    {
        var input = Input([1, 2, 3, 4, 5, 6]);
        var result = P28ProducerModel.Evaluate(input);
        Assert.False(result.Resolved);
        Assert.False(result.TWritten);
        Assert.Equal(input.PreviousT, result.T);
        Assert.Equal(input.PreviousFlags0217, result.Flags0217);
        Assert.Equal(input.PreviousFlags0231, result.Flags0231);
        Assert.Equal(P28ProducerDisposition.UnresolvedInstruction, result.Disposition);
        Assert.Empty(result.UsedAssumptions);
    }

    [Fact]
    public void AlternativeWritesSampleOneBeforeStrictAddStopButAddsTheOldValueWhenPermitted()
    {
        var input = Input([0, 1, 2, 3, 4, 5], alternative: true);
        var strict = P28ProducerModel.Evaluate(input);
        Assert.False(strict.Resolved);
        Assert.Equal(new ushort[] { 1, 1, 2, 3, 4, 5 }, strict.Samples);
        Assert.Equal(input.PreviousT, strict.T);
        var conditional = P28ProducerModel.Evaluate(input, true);
        Assert.Equal((ushort)3, conditional.T);
        Assert.Equal(15U, conditional.AccumulatedSum);
        Assert.Equal(Enumerable.Repeat((ushort)1, 6), conditional.Samples);
        Assert.False(conditional.S);
        Assert.False(conditional.FallbackFlag);
        Assert.Equal(new[] { P28ProducerModel.AddEr1Assumption }, conditional.UsedAssumptions);
        Assert.Equal(new ushort[] { 0, 1, 2, 3, 4, 5 }, input.Samples);
    }

    [Fact]
    public void SixEqualIncomingWordsAreDividedByFiveNotAveraged()
    {
        var result = P28ProducerModel.Evaluate(Input([1000, 1000, 1000, 1000, 1000, 1000]), true);
        Assert.Equal(6000U, result.AccumulatedSum);
        Assert.Equal((ushort)1200, result.T);
        Assert.Equal(6, result.ProcessedSamples);
    }

    [Theory]
    [InlineData(4, 65535, false)]
    [InlineData(5, 65535, true)]
    [InlineData(65535, 65535, true)]
    public void UnsignedCarryAndTruncatedQuotientDistinguishValidFFFFFromOverflowFallback(int last, int expectedT, bool fallback)
    {
        var result = P28ProducerModel.Evaluate(Input([65535, 65535, 65535, 65535, 65535, (ushort)last]), true);
        Assert.Equal((ushort)expectedT, result.T);
        Assert.Equal(fallback, result.FallbackFlag);
        Assert.False(result.S);
        Assert.Equal(327675U + (uint)last, result.AccumulatedSum);
        Assert.Equal(fallback ? P28ProducerDisposition.QuotientOverflowFallback : P28ProducerDisposition.NewValue, result.Disposition);
        var carry = P28ProducerModel.Evaluate(Input([65535, 1, 1, 1, 1, 1]), true);
        Assert.Equal((ushort)13108, carry.T);
    }

    [Fact]
    public void EveryZeroPositionHasExplicitProcessedPrefixAndFallbackStatus()
    {
        for (var position = 0; position < 6; position++)
        {
            var samples = Enumerable.Repeat((ushort)100, 6).ToArray();
            samples[position] = 0;
            var result = P28ProducerModel.Evaluate(Input(samples), true);
            Assert.Equal(ushort.MaxValue, result.T);
            Assert.Equal(position, result.ProcessedSamples);
            Assert.Equal((uint)(position * 100), result.AccumulatedSum);
            Assert.Equal(position == 0 ? 0 : 1, result.UsedAssumptions.Count);
        }
    }

    [Fact]
    public void RepeatedAlternativeSnapshotDependsOnMutatedSampleHistory()
    {
        var firstInput = Input([1000, 1000, 1000, 1000, 1000, 1000], alternative: true);
        var first = P28ProducerModel.Evaluate(firstInput, true);
        var next = P28ProducerModel.Evaluate(firstInput with
        {
            Samples = first.Samples,
            PreviousT = first.T,
            PreviousFlags0217 = first.Flags0217,
            PreviousFlags0231 = first.Flags0231,
        }, true);
        Assert.Equal((ushort)1200, first.T);
        Assert.Equal((ushort)1, next.T);
        Assert.NotEqual(first.T, next.T);
    }

    [Fact]
    public void DistinctAssumptionsHaveNoGlobalUnknownPermissionAndPacketsContainOnlyInputs()
    {
        Assert.Throws<ArgumentException>(() => P28ProducerValidator.ValidateAssumptions(["all"]));
        Assert.Throws<ArgumentException>(() => P28ProducerValidator.ValidateAssumptions([P28ProducerModel.AddEr1Assumption, P28ProducerModel.AddEr1Assumption]));
        var input = Input([1, 2, 3, 4, 5, 6]);
        var request = JsonSerializer.SerializeToElement(P28ProducerValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), null,
            [input], [P28ByteExecutionValidator.AddAssumption]));
        Assert.Equal("producerBatch", request.GetProperty("operation").GetString());
        Assert.Equal(14, request.GetProperty("producerCases")[0].GetArrayLength());
        Assert.Equal(P28ByteExecutionValidator.AddAssumption, request.GetProperty("allowAssumptions")[0].GetString());
        Assert.False(P28ProducerModel.Evaluate(input).Resolved);
        Assert.False(request.TryGetProperty("expected", out _));
    }

    [Fact]
    public void FiniteCaseSetIsDeterministicAndDoesNotPretendToExhaustSixWordInputs()
    {
        var first = P28ProducerCases.Create();
        var second = P28ProducerCases.Create();
        Assert.Equal(131072 + 672 + 186 + 2048, first.Count);
        Assert.Equal(65536, first.Count(input => input.Group == "UniformIntervalWordsNormal"));
        Assert.Equal(65536, first.Count(input => input.Group == "UniformIntervalWordsAlternative"));
        Assert.Equal(2048, first.Count(input => input.Group == "DeterministicRawRandom"));
        for (var index = 0; index < first.Count; index++)
        {
            Assert.Equal(index, first[index].CaseId);
            Assert.Equal(P28ProducerCases.Pack(first[index]), P28ProducerCases.Pack(second[index]));
        }
        Assert.Throws<ArgumentException>(() => P28ProducerModel.Evaluate(Input([1, 2, 3])));
        Assert.Equal("IntervalDerivedUnsignedWordsNotAbsoluteCaptureTimestamps", P28ProducerModel.SampleRepresentation);
    }

    internal static P28ProducerInput Input(ushort[] samples, bool alternative = false, bool s = true) =>
        new(0, "SyntheticModelBoundary", 0, Array.AsReadOnly(samples), 123, (byte)((alternative ? 0x80 : 0) | (s ? 0x10 : 0)),
            0, 0, 0, false);
}
