namespace HondaEcu.Core;

// Static research only. Not a scenario, acquisition contract, or executable oracle.
// Hypotheses deliberately cannot become a NativeWritten result or ready RAM input.
internal static class P28Data0136ProducerModel
{
    internal sealed record Availability(string Status, ushort? Expected0136, int NativeWrites);
    internal sealed record Hypothesis(bool WouldWrite, ushort? AbstractWord, byte CounterAfterSample, uint? Dividend);

    internal static Availability Current => new("ProducerNotRun_IRQDependent", null, 0);

    // Raw abstract sources, NOT admitted hardware snapshots. No Rust observations input.
    internal static Hypothesis Hypothesize(ushort sample, ushort previous, byte counter,
        bool priorSamplePresent, bool dividedMode, bool pendingBit, bool timerControlBit)
    {
        var nextCounter = unchecked((byte)(counter + (sample < 0x8000 && pendingBit ? 1 : 0)));
        if (!priorSamplePresent) return new(false, null, nextCounter, null);
        var delta = unchecked((ushort)(sample - previous));
        if (!dividedMode) return new(true, timerControlBit ? (ushort)0 : delta, nextCounter, null);
        var high = unchecked((byte)(nextCounter - (sample < previous ? 1 : 0)));
        var dividend = ((uint)high << 16) | delta;
        var quotient = dividend / 6;
        return new(true, quotient <= ushort.MaxValue ? (ushort)quotient : (ushort)0, nextCounter, dividend);
    }
}
