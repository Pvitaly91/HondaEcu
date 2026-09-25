namespace HondaEcu.Core;

public sealed record P28IgnitionCorrectionObservation(byte Base0248, sbyte SignedCorrection0245,
    byte Subtrahend0246, ushort CorrectionAccumulator, ushort CorrectedRaw, bool AddCarry,
    bool Mode0207Bit7, bool BoundBranchTaken, byte BoundedRaw, byte Floor024c,
    byte AfterFloor, bool Gate0234Bit5Before, bool Gate0234Bit5After,
    bool Gate0217Bit1, bool ClearedByGate, byte Result035b,
    byte Bias0249, bool BiasOverflow, byte Result024a);
public sealed record P28IgnitionCorrectionModelStep(P28IgnitionSelectorModelStep Prefix,
    P28IgnitionCorrectionObservation Correction);

/// <summary>Independent prefix ROM bytes and persistent software-state history.</summary>
public sealed class P28IgnitionCorrectionModel
{
    private readonly P28IgnitionSelectorModel _prefix;
    private readonly P28IgnitionCorrectionInitial _initial;
    private bool _gate0234Bit5;
    private byte _retained035b;
    private byte _retained024a;

    public P28IgnitionCorrectionModel(RomImage image, P28IgnitionCorrectionInitial initial)
    {
        _prefix = new P28IgnitionSelectorModel(image,
            new P28IgnitionSelectorInitial(initial.Ignition, initial.Source03c7));
        _initial = initial; _gate0234Bit5 = initial.Gate0234Bit5;
        _retained035b = initial.Retained035b; _retained024a = initial.Retained024a;
    }

    public (byte Result035b, byte Result024a) Retained => (_retained035b, _retained024a);

    public P28IgnitionCorrectionModelStep Step(P28IgnitionCorrectionCall call)
    {
        var prefix = _prefix.Step(new P28IgnitionSelectorCall(call.Index, call.Source03c7,
            call.RawLoad, call.RawMap0Rpm, call.RawMap1Rpm));
        var base0248 = prefix.Ignition.After.ConsumerOutput0248;
        // 0F85 clears er3. EXTND sign-extends 0245; 0246 is then subtracted
        // as an unsigned byte from the 16-bit object. ADD A,er3 wraps before
        // the following carry test or comparison, never as a wide final clamp.
        var signed = unchecked((sbyte)call.Correction0245);
        var er3 = unchecked((ushort)(signed - call.Correction0246));
        var wide = (int)base0248 + er3;
        var corrected = unchecked((ushort)wide);
        var carry = wide > ushort.MaxValue;
        // DATA0207 is banked r7. Selection previously fills er3 with RPM
        // fraction, but 0F85 clears er3 and 0FEC/0FF1 replace it. At 0FFA
        // bit7 is the sign bit of this native correction accumulator.
        var mode0207Bit7 = (er3 & 0x8000) != 0;
        var boundBranch = mode0207Bit7 ? carry : corrected < 255;
        var bounded = mode0207Bit7
            ? (byte)(carry ? corrected & 255 : 0)
            : (byte)(boundBranch ? corrected & 255 : 255);
        var beforeGate = _gate0234Bit5;
        var threshold = beforeGate ? 0x40 : 0x4D;
        _gate0234Bit5 = threshold < call.RawMap0Rpm;
        var afterFloor = Math.Max(bounded, _initial.Floor024c);
        var gate0217Bit1 = !_initial.Gate0217Bit0 && afterFloor == 0;
        var clear = _initial.Gate021eBit0 || gate0217Bit1;
        _retained035b = (byte)(clear ? 0 : afterFloor);
        var sum = _retained035b + _initial.Bias0249;
        var biasOverflow = !clear && sum > 255;
        _retained024a = (byte)(clear ? 0 : biasOverflow ? 255 : sum);
        return new(prefix, new(base0248, signed, call.Correction0246, er3, corrected,
            carry, mode0207Bit7, boundBranch, bounded, _initial.Floor024c,
            (byte)afterFloor, beforeGate, _gate0234Bit5, gate0217Bit1, clear,
            _retained035b, _initial.Bias0249, biasOverflow, _retained024a));
    }
}
