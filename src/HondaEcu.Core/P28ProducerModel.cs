namespace HondaEcu.Core;

public enum P28ProducerDisposition
{
    NewValue,
    ZeroSampleFallback,
    QuotientOverflowFallback,
    UnresolvedInstruction,
}

public sealed record P28ProducerInput(
    int CaseId, string Group, int ScratchPattern, IReadOnlyList<ushort> Samples,
    ushort PreviousT, byte PreviousFlags0217, byte PreviousFlags0231,
    int ThresholdContext, int ThresholdPriorBits, bool ThresholdEnabled);

public sealed record P28ProducerModelResult(
    P28ProducerDisposition Disposition, bool Resolved, bool TWritten,
    ushort T, byte Flags0217, byte Flags0231, IReadOnlyList<ushort> Samples,
    uint AccumulatedSum, int ProcessedSamples, IReadOnlyList<string> UsedAssumptions)
{
    public bool S => (Flags0217 & 0x10) != 0;
    public bool FallbackFlag => (Flags0231 & 0x20) != 0;
}

/// <summary>
/// Integer model of the reviewed RAM producer boundary, separate from Rust execution.
/// Six incoming words are summed with 24-bit carry and divided by five, not averaged.
/// The missing word ADD er1,A semantics remain an explicit, distinct hypothesis.
/// </summary>
public static class P28ProducerModel
{
    public const string ModelId = "p28-producer-v1";
    public const string SampleRepresentation = "IntervalDerivedUnsignedWordsNotAbsoluteCaptureTimestamps";
    public const string AddEr1Assumption = "oki.add-er1-a";

    public static P28ProducerModelResult Evaluate(P28ProducerInput input, bool allowAddEr1Assumption = false)
    {
        ArgumentNullException.ThrowIfNull(input);
        if (input.Samples.Count != 6)
        {
            throw new ArgumentException("Producer requires exactly six incoming unsigned sample words.", nameof(input));
        }
        var samples = input.Samples.ToArray();
        var alternative = (input.PreviousFlags0217 & 0x80) != 0;
        uint sum = 0;
        var processed = 0;
        for (var index = 0; index < samples.Length; index++)
        {
            var incoming = samples[index];
            if (!alternative && incoming == 0)
            {
                // The actual early branch rejoins XCHG DATA00C4: it WRITES FFFF.
                // It skips clearing S and sets the fallback bit; old T is not retained.
                return new(P28ProducerDisposition.ZeroSampleFallback, true, true, ushort.MaxValue,
                    input.PreviousFlags0217, (byte)(input.PreviousFlags0231 | 0x20), samples, sum, processed,
                    processed == 0 ? [] : [AddEr1Assumption]);
            }
            if (alternative)
            {
                // Read old value first, replace its RAM slot with one, then add old value.
                samples[index] = 1;
            }
            if (!allowAddEr1Assumption)
            {
                return new(P28ProducerDisposition.UnresolvedInstruction, false, false, input.PreviousT,
                    input.PreviousFlags0217, input.PreviousFlags0231, samples, sum, processed, []);
            }
            sum += incoming;
            processed++;
        }

        // The largest possible sum is 393210 (<2^24); no accumulator wrap occurs
        // anywhere in this six-word domain. DIV truncates the unsigned quotient.
        var quotient = sum / 5U;
        var overflow = quotient > ushort.MaxValue;
        return new(overflow ? P28ProducerDisposition.QuotientOverflowFallback : P28ProducerDisposition.NewValue,
            true, true, overflow ? ushort.MaxValue : (ushort)quotient,
            (byte)(input.PreviousFlags0217 & ~0x10),
            (byte)((input.PreviousFlags0231 & ~0x20) | (overflow ? 0x20 : 0)),
            samples, sum, processed, [AddEr1Assumption]);
    }
}
