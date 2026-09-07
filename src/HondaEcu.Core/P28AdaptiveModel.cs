namespace HondaEcu.Core;

public sealed record P28AdaptiveTick(int Address, byte Before, byte After, IReadOnlyList<int[]> Writes, IReadOnlyList<int[]> Branches);
public sealed record P28AdaptiveModelStep(P28AdaptiveState Before, P28AdaptiveState AfterProducer, P28AdaptiveState After,
    int Bank, string Path, IReadOnlyList<int[]> TableReads, IReadOnlyList<int[]> Branches, IReadOnlyList<int[]> ProducerWrites,
    IReadOnlyList<P28AdaptiveTick> Ticks, P28LimiterModelStep Limiter);

/// <summary>Independent word arithmetic and persistent histories; no runner state is an input.</summary>
public sealed class P28AdaptiveModel
{
    private readonly byte[] _rom;
    private readonly P28LimiterModel _limiter;
    private P28AdaptiveState _state;
    public P28AdaptiveModel(ReadOnlySpan<byte> rom, P28AdaptiveState initial)
    {
        if (rom.Length != 32768) throw new ArgumentException("Exact image size required.");
        ArgumentNullException.ThrowIfNull(initial); _rom = rom.ToArray(); _state = initial; _limiter = new(rom, initial.Limiter);
    }
    private ushort W(int address) => P28LimiterInspector.Word(_rom, address);
    public P28AdaptiveModelStep Step(P28AdaptiveCall c)
    {
        ArgumentNullException.ThrowIfNull(c); var before = _state; var ticks = new List<P28AdaptiveTick>();
        for (var kind = 0; kind < 2; kind++)
            for (var i = 0; i < (kind == 0 ? c.TimerTicks : c.CounterTicks); i++)
            {
                var address = kind == 0 ? 0x1D5 : 0x1CE; var old = kind == 0 ? _state.Timer : _state.Counter;
                var value = (byte)Math.Max(0, old - 1);
                ticks.Add(new(address, old, value, old == 0 ? [] : new[] { new[] { address, 8, (int)value } }, new[] { new[] { 0x5BD3, old == 0 ? 0x5BD9 : 0x5BD5 } }));
                _state = kind == 0 ? _state with { Timer = value } : _state with { Counter = value };
            }
        var writes = new List<int[]>(); var reads = new List<int[]>(); var branches = new List<int[]>();
        void Store(int address, int value, int width = 16) => writes.Add([address, width, value]);
        void Branch(int pc, bool taken, int yes, int no) => branches.Add([pc, taken ? yes : no]);
        ushort Read(int pc, int address) { var value = W(address); reads.Add([pc, address, value]); return value; }
        var resumeTable = (int)W(0x487D); var cutTable = (int)W(0x4880);
        Store(0x88, resumeTable); Store(0x8A, cutTable);
        Branch(0x4882, !c.Bank1, 0x488B, 0x4885);
        if (c.Bank1) { resumeTable = W(0x4886); cutTable = W(0x4889); Store(0x88, resumeTable); Store(0x8A, cutTable); }
        var resume = Read(0x488B, resumeTable + 2); Store(0x8C, resume);
        var cut = Read(0x4890, cutTable + 2);
        Branch(0x4894, !c.Reset217, 0x489D, 0x4897);
        string path; var hold = false;
        if (c.Reset217)
        { path = "Reset217"; _state = _state with { Counter = _rom[0x489A] }; Store(0x1CE, _state.Counter, 8); }
        else
        {
            Branch(0x489D, c.Reset214, 0x48E1, 0x48A0);
            if (c.Reset214) path = "Reset214";
            else
            {
                hold = _state.Timer != 0; Branch(0x48A2, hold, 0x48F5, 0x48A4);
                if (hold) path = "TimerHold";
                else
                {
                    _state = _state with { Timer = _rom[0x48A7] }; Store(0x1D5, _state.Timer, 8);
                    Branch(0x48A8, c.Mode212, 0x48B1, 0x48AB);
                    var resetCounter = !c.Mode212 && c.RawD9 >= _rom[0x48AE];
                    if (!c.Mode212) Branch(0x48AF, resetCounter, 0x48C7, 0x48B1);
                    if (!resetCounter) { Branch(0x48B1, !c.Enable223, 0x48C7, 0x48B4); resetCounter = !c.Enable223; }
                    if (resetCounter) { _state = _state with { Counter = _rom[0x48CA] }; Store(0x1CE, _state.Counter, 8); }
                    else Branch(0x48B6, _state.Counter != 0, 0x48CB, 0x48B8);
                    if (resetCounter || _state.Counter != 0)
                    {
                        path = resetCounter ? "CounterResetDecrease" : "CounterPendingDecrease";
                        ushort Down(ushort old, ushort floor, int returnPc)
                        {
                            Store(0x7FE, returnPc); var borrow = old < W(0x5AB9); Branch(0x5ABB, borrow, 0x5AC0, 0x5ABD);
                            var next = unchecked((ushort)(old - W(0x5AB9)));
                            if (!borrow) Branch(0x5ABE, next >= floor, 0x5AC1, 0x5AC0);
                            return borrow || next < floor ? floor : next;
                        }
                        var floor = Read(0x48CB, resumeTable + 2); Store(0x208, floor);
                        resume = Down(_state.Limiter.RamResume, floor, 0x48D6); Store(0x8C, resume);
                        floor = Read(0x48D7, cutTable + 2); Store(0x208, floor);
                        cut = Down(_state.Limiter.RamCut, floor, 0x48E1);
                    }
                    else
                    {
                        path = "AdaptiveBound";
                        ushort Bound(ushort old, int table, int returnPc)
                        {
                            Store(0x7FE, returnPc); var sum = old + W(0x5AC3); var bound = Math.Min(65535, sum);
                            Branch(0x5AC5, sum <= 65535, 0x5ACA, 0x5AC7); Store(0x20E, bound); Store(0x20A, 0);
                            var origin = Read(0x5ACD, table); Store(0x208, origin); var borrow = c.Raw00ce < origin;
                            Branch(0x5AD3, borrow, 0x5ADC, 0x5AD5); var high = 0;
                            if (!borrow)
                            {
                                var delta = c.Raw00ce - origin; Store(0x208, delta);
                                var coefficient = Read(0x5AD6, table + 4); high = (int)((uint)delta * coefficient >> 16); Store(0x20A, high);
                            }
                            var baseWord = Read(0x5ADC, table + 2); var target = unchecked((ushort)(baseWord + high));
                            Branch(0x5AE2, target < bound, 0x5AE5, 0x5AE4);
                            return (ushort)Math.Min(target, bound);
                        }
                        resume = Bound(_state.Limiter.RamResume, resumeTable, 0x48BD); Store(0x8C, resume);
                        Store(0x88, cutTable); cut = Bound(_state.Limiter.RamCut, cutTable, 0x48C5);
                    }
                }
            }
        }
        if (!hold)
        {
            Store(0x1A, _state.Ie & W(0x48E4)); Store(0x1A4, cut); Store(0x1A6, resume); Store(0x1A, _state.RestoreIe);
            _state = _state with { Limiter = _state.Limiter with { RamCut = cut, RamResume = resume }, Ie = _state.RestoreIe };
        }
        var produced = _state;
        _limiter.AcceptModeledAdaptiveWords(_state.Limiter.RamCut, _state.Limiter.RamResume);
        var decision = _limiter.Step(c.Limiter);
        if (decision.Context != "Fixed") decision = decision with { Context = "AdaptiveRam" };
        _state = _state with { Limiter = decision.After };
        return new(before, produced, _state, c.Bank1 ? 1 : 0, path, reads.AsReadOnly(), branches.AsReadOnly(), writes.AsReadOnly(), ticks.AsReadOnly(), decision);
    }
}
