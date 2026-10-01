namespace HondaEcu.Core;

internal sealed record P28CommonResultConsumerState(P28PostSelectionCriticalState Prefix, byte Mode012b,
    ushort Word011a, byte Byte011f, byte Byte0120, byte Byte00be, byte Byte00b7, ushort Word0136, byte Byte013b, byte Byte013d);
internal sealed record P28CommonResultConsumerOwn(P28PostSelectionCriticalOwn Prefix,
    P28CommonResultConsumerState Before, P28CommonResultConsumerState Entry, P28CommonResultConsumerState After,
    P28CommonResultConsumerOracle Oracle);

// Each image owns its own ROM, all prefix models and persistent software storage.
internal sealed class P28CommonResultConsumerHistory
{
    private readonly RomImage _image;
    private readonly P28PostSelectionCriticalHistory _prefix;
    private readonly int _source125Neighbors;
    private P28CommonResultConsumerState _state;
    internal P28CommonResultConsumerHistory(RomImage image, P28CommonResultConsumerScenario scenario, int pattern)
    {
        _image = image; _prefix = new(image, scenario.PrefixScenario, pattern); _source125Neighbors = pattern & ~16; var s = scenario.InitialState.SoftwareSources;
        _state = new(_prefix.ModeledState, scenario.InitialState.Prefix.Adaptive.Joint.Data012b,
            (ushort)((pattern & ~0x1034) | s.Word011aMask1034),
            (byte)((pattern & ~32) | (s.Bit011f5 ? 32 : 0)), (byte)(s.Bit0120_0 ? 1 : 0), s.Byte00be,
            (byte)((pattern & ~1) | (s.Bit00b7_0 ? 1 : 0)), s.Word0136, s.History013b, s.History013d);
    }
    internal P28CommonResultConsumerOwn Step(P28PostStoreCall call)
    {
        var before = _state; var prefix = _prefix.Step(call, before.Mode012b);
        var entry = before with
        {
            Prefix = prefix.After,
            Mode012b = prefix.Prefix.PrefixMode012b,
            Word011a = (ushort)((before.Word011a & ~0x8000) | (call.Adaptive.FixedSource ? 0x8000 : 0))
        };
        var oracle = P28CommonResultConsumerEvidence.Build(_image, prefix.Oracle, entry, call, _source125Neighbors | (call.Disable125 ? 16 : 0));
        _state = entry with { Mode012b = (byte)oracle.ModeEnds[^1], Byte013b = (byte)oracle.HistoryEnds[^1][0], Byte013d = (byte)oracle.HistoryEnds[^1][1] };
        return new(prefix, before, entry, _state, oracle);
    }
}
