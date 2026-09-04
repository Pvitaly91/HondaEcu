namespace HondaEcu.Core.Tests;

public sealed class P28ThresholdLogicTests
{
    // Deliberately invented, distinct values. This is not an OEM threshold block.
    private static byte[] SyntheticBlock() => new byte[] { 20, 30, 40, 50, 60, 70, 80, 90 };

    [Theory]
    [InlineData(true, 0)]
    [InlineData(false, 1)]
    public void SelectContextUsesExplicitSelectorPolarity(bool selector, int expectedContext)
    {
        Assert.Equal(expectedContext, P28ThresholdLogic.SelectContext(selector));
    }

    [Theory]
    [InlineData(0, 0, false, 0x6543, 30)]
    [InlineData(0, 0, true, 0x6542, 20)]
    [InlineData(0, 1, false, 0x6545, 50)]
    [InlineData(0, 1, true, 0x6544, 40)]
    [InlineData(1, 0, false, 0x6547, 70)]
    [InlineData(1, 0, true, 0x6546, 60)]
    [InlineData(1, 1, false, 0x6549, 90)]
    [InlineData(1, 1, true, 0x6548, 80)]
    public void EveryContextPairAndPriorStateSelectsExactOffset(
        int context, int pair, bool priorState, int expectedOffset, byte expectedThreshold)
    {
        Assert.Equal(expectedOffset, P28ThresholdLogic.ThresholdOffset(context, pair, priorState));

        var transition = P28ThresholdLogic.EvaluatePair(SyntheticBlock(), context, pair, priorState, expectedThreshold);

        Assert.Equal(context, transition.Context);
        Assert.Equal(pair, transition.Pair);
        Assert.Equal(priorState, transition.PriorState);
        Assert.Equal(expectedOffset, transition.Offset);
        Assert.Equal(expectedThreshold, transition.Threshold);
        Assert.Equal(expectedThreshold, transition.CompactCode);
        Assert.False(transition.NewState);
    }

    [Fact]
    public void PredicateMatchesUnsignedSubtractionBorrowForEveryBytePair()
    {
        for (var threshold = 0; threshold <= byte.MaxValue; threshold++)
        {
            for (var compactCode = 0; compactCode <= byte.MaxValue; compactCode++)
            {
                // An independent widened subtraction cannot wrap; its negative result
                // is the unsigned byte subtraction's borrow. Equality never borrows.
                var borrow = threshold - compactCode < 0;

                Assert.Equal(borrow, P28ThresholdLogic.Evaluate((byte)threshold, (byte)compactCode));
            }
        }
    }

    [Theory]
    [InlineData(0, 0, false)]
    [InlineData(0, 1, true)]
    [InlineData(254, 253, false)]
    [InlineData(254, 254, false)]
    [InlineData(254, 255, true)]
    [InlineData(255, 0, false)]
    [InlineData(255, 254, false)]
    [InlineData(255, 255, false)]
    public void PredicateIsStrictAtEqualityAndByteExtremes(byte threshold, byte compactCode, bool expected)
    {
        Assert.Equal(expected, P28ThresholdLogic.Evaluate(threshold, compactCode));
    }

    [Fact]
    public void BothPairsUseTheirOwnPriorBitForAllContextsAndStateCombinations()
    {
        var block = SyntheticBlock();
        var original = (byte[])block.Clone();

        for (var context = 0; context < 2; context++)
        {
            for (var priorBits = 0; priorBits < 4; priorBits++)
            {
                var priorPair0 = (priorBits & 1) != 0;
                var priorPair1 = (priorBits & 2) != 0;
                var threshold0 = block[(context * 4) + (priorPair0 ? 0 : 1)];
                var threshold1 = block[(context * 4) + 2 + (priorPair1 ? 0 : 1)];

                for (var code = 0; code <= byte.MaxValue; code++)
                {
                    var first = P28ThresholdLogic.EvaluatePair(block, context, 0, priorPair0, (byte)code);
                    var second = P28ThresholdLogic.EvaluatePair(block, context, 1, priorPair1, (byte)code);

                    Assert.Equal(threshold0, first.Threshold);
                    Assert.Equal(threshold1, second.Threshold);
                    Assert.Equal(threshold0 - code < 0, first.NewState);
                    Assert.Equal(threshold1 - code < 0, second.NewState);
                    Assert.Equal(priorPair0, first.PriorState);
                    Assert.Equal(priorPair1, second.PriorState);
                    Assert.Equal((byte)code, first.CompactCode);
                    Assert.Equal((byte)code, second.CompactCode);
                }
            }
        }

        Assert.Equal(original, block);
    }

    [Fact]
    public void PriorStateSequenceRetainsStateBetweenDistinctSyntheticThresholds()
    {
        var block = SyntheticBlock();
        byte[] codes = { 30, 31, 21, 20, 30, 31 };
        bool[] expectedStates = { false, true, true, false, false, true };
        byte[] expectedThresholds = { 30, 30, 20, 20, 30, 30 };
        var state = false;

        for (var index = 0; index < codes.Length; index++)
        {
            var transition = P28ThresholdLogic.EvaluatePair(block, 0, 0, state, codes[index]);

            Assert.Equal(expectedThresholds[index], transition.Threshold);
            Assert.Equal(expectedStates[index], transition.NewState);
            state = transition.NewState;
        }
    }

    [Fact]
    public void ReversedThresholdPairIsEvaluatedLiterallyWithoutReorderingOrSmoothing()
    {
        byte[] block = { 30, 20, 70, 60, 110, 100, 150, 140 };
        var state = false;

        for (var index = 0; index < 6; index++)
        {
            var transition = P28ThresholdLogic.EvaluatePair(block, 0, 0, state, 25);

            Assert.Equal(state ? (byte)30 : (byte)20, transition.Threshold);
            Assert.Equal(!state, transition.NewState);
            state = transition.NewState;
        }
    }

    [Theory]
    [InlineData(0)]
    [InlineData(37)]
    [InlineData(255)]
    public void EqualPairThresholdsHaveNoHiddenPriorStateEffect(byte threshold)
    {
        var block = Enumerable.Repeat(threshold, 8).ToArray();

        for (var context = 0; context < 2; context++)
        {
            for (var pair = 0; pair < 2; pair++)
            {
                for (var code = 0; code <= byte.MaxValue; code++)
                {
                    var fromClear = P28ThresholdLogic.EvaluatePair(block, context, pair, false, (byte)code);
                    var fromSet = P28ThresholdLogic.EvaluatePair(block, context, pair, true, (byte)code);

                    Assert.Equal(fromClear.NewState, fromSet.NewState);
                    Assert.Equal(threshold - code < 0, fromClear.NewState);
                }
            }
        }
    }

    [Theory]
    [InlineData(-1, 0, "context")]
    [InlineData(2, 0, "context")]
    [InlineData(int.MinValue, 0, "context")]
    [InlineData(int.MaxValue, 0, "context")]
    [InlineData(0, -1, "pair")]
    [InlineData(0, 2, "pair")]
    [InlineData(1, int.MinValue, "pair")]
    [InlineData(1, int.MaxValue, "pair")]
    public void RejectsInvalidContextAndPairWithoutWrappingOffsets(int context, int pair, string parameter)
    {
        foreach (var priorState in new[] { false, true })
        {
            var offsetException = Assert.Throws<ArgumentOutOfRangeException>(() =>
                P28ThresholdLogic.ThresholdOffset(context, pair, priorState));
            var evaluationException = Assert.Throws<ArgumentOutOfRangeException>(() =>
                P28ThresholdLogic.EvaluatePair(SyntheticBlock(), context, pair, priorState, 0));

            Assert.Equal(parameter, offsetException.ParamName);
            Assert.Equal(parameter, evaluationException.ParamName);
        }
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(7)]
    [InlineData(9)]
    [InlineData(32768)]
    public void RequiresAnExactEightByteBlock(int length)
    {
        var block = new byte[length];

        var exception = Assert.Throws<ArgumentException>(() =>
            P28ThresholdLogic.EvaluatePair(block, 0, 0, false, 0));

        Assert.Equal("block8", exception.ParamName);
    }
}
