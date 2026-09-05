using System.Globalization;
using System.Numerics;

namespace HondaEcu.Core;

public sealed record P28CaptureRational(long Numerator, long Denominator)
{
    internal P28ExactNumber Exact()
    {
        if (Numerator is < 0 or > 1_000_000_000_000 || Denominator is < 1 or > 1_000_000)
        { throw new ArgumentException("Tick rational requires numerator 0..10^12 and denominator 1..10^6."); }
        return new(Numerator, Denominator);
    }
}

public sealed record P28CaptureTimelinePoint(int ObservationIndex, string ExtendedTick, string? ElapsedTicks,
    bool LowWordWrapped, string IntervalScope, bool SuppliedTcerr, bool SuppliedOverflowPending,
    string FlagQualification);

/// <summary>Exact synthetic source: floor(origin + phase + sum(periods)), then modulo 65536.</summary>
public sealed record P28CaptureTimeline(string OriginTicks, P28CaptureRational Phase,
    IReadOnlyList<P28CaptureRational> Periods, string Quantization, string Provenance)
{
    public const string FloorQuantization = "floor-exact-rational-then-modulo-65536";

    internal P28CaptureTimeline Snapshot()
    {
        if (Phase is null || Periods is null || Periods.Any(period => period is null))
        { throw new ArgumentException("Explicit phase and period values are required."); }
        return this with { Periods = Array.AsReadOnly(Periods.ToArray()) };
    }

    internal P28CaptureTimeline Prefix(int count) => this with { Periods = Array.AsReadOnly(Periods.Take(count - 1).ToArray()) };

    public IReadOnlyList<string> ExtendedTicks()
    {
        if (OriginTicks is null || OriginTicks.Length is < 1 or > 13 || OriginTicks.Any(c => c is < '0' or > '9') ||
            !BigInteger.TryParse(OriginTicks, NumberStyles.None, CultureInfo.InvariantCulture, out var origin) || origin > 1_000_000_000_000L ||
            Quantization != FloorQuantization || string.IsNullOrWhiteSpace(Provenance) || Provenance.Length > 512 ||
            Periods is null || Periods.Count > 1023 || Phase is null)
        { throw new ArgumentException("Malformed or unbounded exact capture timeline."); }
        var phase = Phase.Exact();
        if (phase.CompareTo(new(1, 1)) >= 0) { throw new ArgumentException("Phase must be in [0,1) ticks; supply integer offset as originTicks."); }
        var current = new P28ExactNumber(origin * phase.Denominator + phase.Numerator, phase.Denominator);
        var result = new List<string> { current.Floor.ToString(CultureInfo.InvariantCulture) };
        foreach (var period in Periods)
        {
            ArgumentNullException.ThrowIfNull(period);
            var delta = period.Exact();
            current = new(current.Numerator * delta.Denominator + delta.Numerator * current.Denominator,
                current.Denominator * delta.Denominator);
            if (current.Denominator.GetBitLength() > 4096) { throw new ArgumentException("Combined exact timeline denominator exceeds 4096 bits."); }
            result.Add(current.Floor.ToString(CultureInfo.InvariantCulture));
        }
        return result.AsReadOnly();
    }

    internal void Validate(IReadOnlyList<P28CaptureObservation> observations)
    {
        var ticks = ExtendedTicks();
        if (ticks.Count != observations.Count) { throw new ArgumentException("One period per transition is required."); }
        for (var index = 0; index < ticks.Count; index++)
        {
            if ((ushort)(BigInteger.Parse(ticks[index], CultureInfo.InvariantCulture) % 65536) != observations[index].Tmr2)
            { throw new ArgumentException("Declared exact timeline contradicts a supplied TMR2 word."); }
        }
    }

    public IReadOnlyList<P28CaptureTimelinePoint> Describe(IReadOnlyList<P28CaptureObservation> observations)
    {
        Validate(observations);
        var ticks = ExtendedTicks().Select(value => BigInteger.Parse(value, CultureInfo.InvariantCulture)).ToArray();
        var result = new List<P28CaptureTimelinePoint>();
        for (var index = 0; index < ticks.Length; index++)
        {
            var observation = observations[index];
            var tcerr = (observation.Tcon2 & 4) != 0;
            var delta = index == 0 ? (BigInteger?)null : ticks[index] - ticks[index - 1];
            var scope = delta is null ? "NoExtendedPrehistory" : delta >= 65535 ? "LongIntervalAtLeastFFFF" : delta == 0 ? "ZeroTickInterval" : "ShortPositiveInterval";
            var qualification = delta is null ? "First snapshot flags supplied without extended prehistory." :
                tcerr == (delta >= 65535) ? "Supplied TCERR agrees with the documented long-interval condition in this synthetic source; no IRQ race claim." :
                "Supplied TCERR differs from this idealized long-interval condition: forced/unverified snapshot, not physical ECU reachability evidence.";
            result.Add(new(index, ticks[index].ToString(CultureInfo.InvariantCulture), delta?.ToString(CultureInfo.InvariantCulture),
                index > 0 && ticks[index] / 65536 > ticks[index - 1] / 65536, scope, tcerr,
                (observation.Irqh & 1) != 0, qualification));
        }
        return result.AsReadOnly();
    }

    /// <summary>Slots, compose points and flags remain explicit caller-supplied schedules.</summary>
    public IReadOnlyList<P28CaptureObservation> Generate(Func<int, ushort, P28CaptureObservation> schedule)
    {
        ArgumentNullException.ThrowIfNull(schedule);
        var ticks = ExtendedTicks();
        var observations = ticks.Select((value, index) => schedule(index,
            (ushort)(BigInteger.Parse(value, CultureInfo.InvariantCulture) % 65536))).ToArray();
        for (var i = 0; i < observations.Length; i++)
        {
            P28AcquisitionModel.ValidateObservation(observations[i]);
            if (observations[i].Index != i) { throw new ArgumentException("Schedule must preserve dense observation indexes."); }
        }
        Validate(observations);
        return Array.AsReadOnly(observations);
    }
}
