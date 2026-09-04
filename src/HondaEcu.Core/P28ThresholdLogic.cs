namespace HondaEcu.Core;

public sealed record ThresholdTransition(
    int Context,
    int Pair,
    bool PriorState,
    int Offset,
    byte Threshold,
    byte CompactCode,
    bool NewState);

/// <summary>
/// Pure threshold update, conditional on reaching the analyzed enabled path. Does not model
/// later permissions, timers, peripheral writes, initialization, or physical VTEC activation.
/// </summary>
public static class P28ThresholdLogic
{
    public const int BlockOffset = 0x6542;
    public const int BlockLength = 8;

    // Neutral context numbering follows ascending ROM location, NOT selector-bit value.
    public static int SelectContext(bool data011EBit3) => data011EBit3 ? 0 : 1;

    public static int ThresholdOffset(int context, int pair, bool priorState)
    {
        if (context is < 0 or > 1)
        {
            throw new ArgumentOutOfRangeException(nameof(context));
        }

        if (pair is < 0 or > 1)
        {
            throw new ArgumentOutOfRangeException(nameof(pair));
        }

        // A word program read places the even-address byte in AL. Prior set uses AL;
        // prior clear selects ACCH, the next (odd-address) byte.
        return BlockOffset + (context * 4) + (pair * 2) + (priorState ? 0 : 1);
    }

    public static bool Evaluate(byte threshold, byte compactCode) => compactCode > threshold;

    public static ThresholdTransition EvaluatePair(
        ReadOnlySpan<byte> block8, int context, int pair, bool priorState, byte compactCode)
    {
        if (block8.Length != BlockLength)
        {
            throw new ArgumentException("Threshold block must contain exactly eight bytes.", nameof(block8));
        }

        var offset = ThresholdOffset(context, pair, priorState);
        var threshold = block8[offset - BlockOffset];
        return new(context, pair, priorState, offset, threshold, compactCode, Evaluate(threshold, compactCode));
    }
}
