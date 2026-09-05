namespace HondaEcu.Core;

/// <summary>Persistent RAM contract, separate from peripheral snapshots and caller scheduling.</summary>
public sealed record P28AcquisitionState(ushort PreviousTimestamp, IReadOnlyList<ushort> Samples,
    byte Data0128, byte Data00AE, byte Data00B6, byte Data011F,
    ushort PreviousT, byte Data0217, byte Data0231, ushort Data0136);

public sealed record P28CaptureObservation(int Index, ushort Tmr2, byte Irqh, byte Tcon2, int Slot,
    bool Compose, int ThresholdContext, int ThresholdPriorBits, bool ThresholdEnabled);

public enum P28AcquisitionDisposition
{
    FirstObservationNoWrite, IntervalWrite, InvalidZeroWrite, UnsupportedMode,
}

public sealed record P28AcquisitionModelResult(P28AcquisitionDisposition Disposition, P28AcquisitionState State,
    IReadOnlyList<int[]> PeripheralAccesses, IReadOnlyList<int[]> SampleWrites, int StopPc,
    ushort? SelectedTimestamp, int SlotIndex);

/// <summary>Independent transition derived from the reviewed normal-mode contract, not Rust outputs.</summary>
public static class P28AcquisitionModel
{
    public const string ModelId = "p28-acquisition-v1";
    public const int EntryPc = 0x56BE;
    public const int StopPc = 0x5719;

    public static P28AcquisitionState Snapshot(P28AcquisitionState state)
    {
        ArgumentNullException.ThrowIfNull(state);
        if (state.Samples is null || state.Samples.Count != 6)
        {
            throw new ArgumentException("Exactly six initial sample words are required.", nameof(state));
        }
        return state with { Samples = Array.AsReadOnly(state.Samples.ToArray()) };
    }

    public static void ValidateObservation(P28CaptureObservation observation)
    {
        ArgumentNullException.ThrowIfNull(observation);
        if (observation.Index is < 0 or >= 1024 || observation.Slot is < 0 or > 5 ||
            observation.ThresholdContext is < 0 or > 1 || observation.ThresholdPriorBits is < 0 or > 3)
        {
            throw new ArgumentException("Observation index, slot or explicit threshold context is outside its bounded domain.", nameof(observation));
        }
    }

    public static P28AcquisitionModelResult Evaluate(P28AcquisitionState previousState, P28CaptureObservation observation)
    {
        var state = Snapshot(previousState);
        ValidateObservation(observation);
        if ((state.Data011F & 4) != 0)
        {
            return new(P28AcquisitionDisposition.UnsupportedMode, state, [], [], EntryPc, null, observation.Slot);
        }

        var reads = new List<int[]> { new[] { 0x003A, 16, 0, (int)observation.Tmr2 } };
        var overflowGuard = state.Data00B6;
        // ST A,er3 aliases DATA010E/010F: bit 010F.7 is the NEW timestamp's high bit.
        if ((observation.Tmr2 & 0x8000) == 0)
        {
            reads.Add([0x0019, 8, 0, observation.Irqh]);
            if ((observation.Irqh & 1) != 0) { overflowGuard |= 1; }
        }

        var writes = new List<int[]>();
        var samples = state.Samples.ToArray();
        var scratch = state.Data0136;
        var disposition = P28AcquisitionDisposition.FirstObservationNoWrite;
        if ((state.Data0128 & 8) != 0)
        {
            reads.Add([0x0042, 8, 0, observation.Tcon2]);
            scratch = (observation.Tcon2 & 4) != 0 ? (ushort)0 : unchecked((ushort)(observation.Tmr2 - state.PreviousTimestamp));
            samples[observation.Slot] = scratch;
            // A store remains a new write even when its value equals the old word.
            writes.Add([0x0360 + 2 * observation.Slot, 16, scratch]);
            disposition = scratch == 0 ? P28AcquisitionDisposition.InvalidZeroWrite : P28AcquisitionDisposition.IntervalWrite;
        }

        state = state with
        {
            PreviousTimestamp = observation.Tmr2,
            Samples = Array.AsReadOnly(samples),
            Data0128 = (byte)(state.Data0128 | 8),
            Data00AE = 0,
            Data00B6 = overflowGuard,
            Data0136 = scratch,
        };
        return new(disposition, state, reads.AsReadOnly(), writes.AsReadOnly(), StopPc, observation.Tmr2, observation.Slot);
    }
}
