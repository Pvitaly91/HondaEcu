namespace HondaEcu.Core;

public sealed record P28LimiterDecisionStep(P28LimiterState Before, P28LimiterState After, string Context,
    int? OperandOffset, ushort Threshold, ushort ComparisonLeft, ushort ComparisonRight, bool OverspeedRequest,
    IReadOnlyList<int[]> DecisionWrites);

public sealed record P28LimiterModelStep(P28LimiterState Before, P28LimiterState After, string Context,
    int? OperandOffset, ushort Threshold, ushort ComparisonLeft, ushort ComparisonRight, bool OverspeedRequest,
    bool InhibitBranch, byte ConsumerAccumulator, IReadOnlyList<int[]> DecisionWrites, IReadOnlyList<int[]> ConsumerWrites,
    int DecisionExit, int ConsumerExit);

/// <summary>Independent persistent contract model; never receives observed Rust history.</summary>
public sealed class P28LimiterModel
{
    private readonly ushort _cut, _resume;
    private P28LimiterState _state;
    public P28LimiterModel(ReadOnlySpan<byte> rom, P28LimiterState initial)
    {
        ArgumentNullException.ThrowIfNull(initial);
        if (rom.Length != 32768) throw new ArgumentException("Exact 32 KiB image required.");
        _cut = P28LimiterInspector.Word(rom, P28LimiterInspector.FieldOffset(P28LimiterInspector.CutId));
        _resume = P28LimiterInspector.Word(rom, P28LimiterInspector.FieldOffset(P28LimiterInspector.ResumeId)); _state = initial;
    }
    public P28LimiterModelStep Step(P28LimiterCall input)
    {
        ArgumentNullException.ThrowIfNull(input);
        if ((input.ChannelMask & 0xF0) != 0xF0) throw new ArgumentException("Software channel mask required.");
        var decision = StepDecision(input.RawPeriod, input.P4Bit0, input.Snapshot011bBit7);
        var before = decision.Before; var request = decision.OverspeedRequest;
        var inhibit = request || (before.Data012A & 128) != 0; var consumer = new List<int[]>();
        if (!inhibit)
        {
            _state = _state with { Data018F = (byte)(before.Data018F & input.ChannelMask), Data012A = (byte)(before.Data012A | 1) };
            consumer.Add([0x18F, 8, _state.Data018F]); consumer.Add([0x12A, 8, _state.Data012A]);
        }
        return new(before, _state, decision.Context, decision.OperandOffset, decision.Threshold, decision.ComparisonLeft,
            decision.ComparisonRight, request, inhibit, (byte)(_state.Data018F | 0xF0), decision.DecisionWrites, consumer.AsReadOnly(), 0x1A38, 0x5596);
    }
    /// <summary>Decision only. No channel accumulator, mask consumer,018F/012A changes.</summary>
    public P28LimiterDecisionStep StepDecision(ushort rawPeriod, bool p4Bit0, bool snapshot011bBit7)
    {
        var before = _state; var prior = (before.Data0124 & 32) != 0;
        var fixedContext = p4Bit0 || snapshot011bBit7;
        var threshold = fixedContext ? prior ? _resume : _cut : prior ? before.RamResume : before.RamCut;
        var request = rawPeriod < threshold;
        var writes = new List<int[]> { new[] { 0x8C, 16, (int)_resume } };
        if (!fixedContext) writes.Add([0x8C, 16, before.RamResume]);
        var bits = (int)before.Data0124;
        void Bits(int mask, bool set) { bits = set ? bits | mask : bits & ~mask; writes.Add([0x124, 8, bits]); }
        if (!request) { writes.Add([0x1D7, 8, 20]); _state = _state with { Data01D7 = 20 }; }
        Bits(4, request); Bits(32, request); Bits(16, false);
        writes.Add([0x12B, 8, before.Data012B & 127]);
        Bits(8, request || (before.Data012B & 128) != 0);
        _state = _state with { Data0124 = (byte)bits, Data012B = (byte)(before.Data012B & 127) };
        return new(before, _state, fixedContext ? "Fixed" : "InitialRamSnapshot", fixedContext ? P28LimiterInspector.FieldOffset(prior ? P28LimiterInspector.ResumeId : P28LimiterInspector.CutId) : null,
            threshold, rawPeriod, threshold, request, writes.AsReadOnly());
    }
    // Accepts only the composition model's own additive byte, never native observations.
    internal void AcceptModeledFuelByte(byte data012b) => _state = _state with { Data012B = data012b };
    internal P28LimiterState ModeledState => _state;
    // Used only by the independent producer model; never accepts observed Rust state.
    internal void AcceptModeledAdaptiveWords(ushort cut, ushort resume) => _state = _state with { RamCut = cut, RamResume = resume };
}
