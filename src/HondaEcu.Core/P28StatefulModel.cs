namespace HondaEcu.Core;

public sealed record P28VtecGate(int Pc, string Id, bool? Outcome, int? Left = null, int? Right = null)
{
    public string Evaluation => Outcome is null ? "NotEvaluated" : Outcome.Value ? "True" : "False";
}
public sealed record P28VtecThresholdSelection(int Pair, int Context, int Offset, byte Threshold, bool OldState, bool NewState);
public sealed record P28StatefulModelStep(P28VtecPersistentState Before, P28VtecPersistentState AtEntry, P28VtecPersistentState After,
    IReadOnlyList<int[]> TickWrites, IReadOnlyList<int[]> DecisionWrites, IReadOnlyList<P28VtecGate> Gates,
    IReadOnlyList<P28VtecThresholdSelection> Thresholds, int Status, int StopPc, IReadOnlyList<string> UsedAssumptions,
    bool? SoftwareRequest, bool? SelectionStatus, string? Unresolved, IReadOnlyList<int> ExecutedGatePcs);

/// <summary>Independent persistent software model. It never consumes intermediate runner RAM.</summary>
public sealed class P28StatefulModel
{
    public const string SubbOffAssumption = "oki.subb-a-off-n8-encoding";
    public const int EntryPc = 0x122C;
    public const int ExitPc = 0x12FC;
    private readonly byte[] _rom;
    private P28VtecPersistentState _state;
    private bool _stopped;
    public P28StatefulModel(ReadOnlySpan<byte> rom, P28VtecPersistentState initial)
    {
        if (rom.Length != 32768) throw new ArgumentException("Exact 32 KiB image required.", nameof(rom));
        ArgumentNullException.ThrowIfNull(initial); _rom = rom.ToArray(); _state = initial;
    }
    public P28VtecPersistentState State => _state;
    internal IReadOnlyList<int[]> AdvanceCounters(int fastTicks, int slowTicks)
    {
        if (_stopped || fastTicks is < 0 or > 32 || slowTicks is < 0 or > 32)
            throw new InvalidOperationException("Invalid or stopped native counter schedule.");
        var writes = new List<int[]>();
        void Store(int address, byte value)
        {
            writes.Add([address, 8, value]);
            _state = address switch
            {
                0x1D8 => _state with { Data01D8 = value },
                0x1D9 => _state with { Data01D9 = value },
                0x1DF => _state with { Data01DF = value },
                0xF3 => _state with { Data00F3 = value },
                _ => throw new InvalidOperationException("Unknown counter."),
            };
        }
        void Decrement(int address, byte value) { if (value != 0) Store(address, (byte)(value - 1)); }
        for (var i = 0; i < fastTicks; i++) { Decrement(0x1D8, _state.Data01D8); Decrement(0x1D9, _state.Data01D9); }
        for (var i = 0; i < slowTicks; i++)
        { Decrement(0x1DF, _state.Data01DF); if (_state.Data00F3 != 255) Store(0xF3, (byte)(_state.Data00F3 + 1)); }
        return writes.AsReadOnly();
    }
    internal static readonly (int Pc, string Id, int Length)[] GateDefinitions =
    [
        (0x122C,"disabled-path",3), (0x1233,"prefix-prior-set",3), (0x123A,"prefix-context-0",3),
        (0x123E,"raw00CC-above-prefix",0), (0x124A,"table-context-0",3), (0x1257,"pair-0-prior-set",3),
        (0x125C,"code-above-pair-0",0), (0x1263,"pair-1-prior-set",3), (0x1268,"code-above-pair-1",0),
        (0x1279,"snapshot011A-mask-nonzero",2), (0x127F,"snapshot011C-mask-zero",2),
        (0x1289,"counter00F3-below-minimum",0), (0x128D,"counter00F3-block-branch",2),
        (0x128F,"raw00D9-below-limit",0), (0x1293,"raw00D9-block-branch",2), (0x1299,"rom60FA-nonzero",2),
        (0x129B,"prefix-clear-block",3), (0x129E,"context-1-path",3), (0x12A1,"snapshot0119-bit5-skip-pair0",3),
        (0x12A4,"pair-0-set-path",3), (0x12A7,"selection-status-set-path",3), (0x12B6,"derived-minus-raw-borrow",2),
        (0x12B8,"request-clear-path",3), (0x12BD,"request-margin-no-borrow",2), (0x12C0,"raw0132-above-adjusted",0),
        (0x12C2,"adjusted-comparison-branch",2), (0x12C4,"pair-1-set-reload",3), (0x12C9,"hold-counter-nonzero",2),
        (0x12D4,"clear-path-feedback-bit1-set",3), (0x12D9,"counter01D9-nonzero",2),
        (0x12EE,"request-path-feedback-bit1-clear",3), (0x12F3,"counter01D8-nonzero",2),
    ];

    public P28StatefulModelStep Step(P28VtecCall input, bool allowSubbOffEncoding = false)
    {
        _ = P28StatefulScenario.Create(_state, [input with { Index = 0 }], "model call validation");
        var before = _state;
        var atEntry = before;
        var ticks = new List<int[]>(); var writes = new List<int[]>(); var gates = new Dictionary<int, P28VtecGate>();
        var gateOrder = new List<int>();
        var thresholds = new List<P28VtecThresholdSelection>(); var used = new List<string>();
        if (_stopped) return Finish(4, EntryPc, "Previous terminal stop; no inputs or schedule applied.");
        ticks.AddRange(AdvanceCounters(input.FastTicks, input.SlowTicks));
        atEntry = _state;
        if (Gate(0x122C, !input.Enabled)) { SetBit(0x22, 1, false); goto ClearRequest; }
        var oldPrefix = Gate(0x1233, (_state.Data0131 & 1) != 0);
        var context0 = Gate(0x123A, input.Context == 0);
        var prefix = context0 ? oldPrefix ? 5 : 10 : oldPrefix ? 20 : 25;
        SetBit(0x131, 0, Compare(0x123E, prefix, input.Raw00CC));
        Gate(0x124A, context0);
        for (var pair = 0; pair < 2; pair++)
        {
            var old = (_state.Data0131 & (2 << pair)) != 0;
            Gate(pair == 0 ? 0x1257 : 0x1263, old);
            var offset = P28ThresholdLogic.ThresholdOffset(input.Context, pair, old);
            var threshold = _rom[offset];
            var next = Compare(pair == 0 ? 0x125C : 0x1268, threshold, input.CompactCode);
            thresholds.Add(new(pair, input.Context, offset, threshold, old, next)); SetBit(0x131, pair + 1, next);
        }
        var interpolation = Interpolate(input.Context, input.CompactCode);
        if (interpolation is null) return Finish(1, 0x5839, "Interpolation table is not a bounded descending nonzero-divisor domain.");
        Store(0x198, interpolation.Value, writes);
        if (Gate(0x1279, (input.Snapshot011A & 0xC0BC) != 0)) { SetBit(0x22, 1, false); goto ClearRequest; }
        if (!Gate(0x127F, (input.Snapshot011C & 0x31) == 0)) { SetBit(0x22, 1, false); goto ClearRequest; }
        SetBit(0x22, 1, true);
        var f3Below = Compare(0x1289, _state.Data00F3, 50);
        if (Gate(0x128D, f3Below)) goto ClearRequest;
        var d9Below = Compare(0x128F, input.Raw00D9, 68);
        if (Gate(0x1293, !d9Below)) goto ClearRequest;
        if (!Gate(0x1299, _rom[0x60FA] != 0) && Gate(0x129B, (_state.Data0131 & 1) == 0)) goto ClearRequest;
        if (!Gate(0x129E, input.Context == 1) && Gate(0x12A1, (input.Snapshot0119 & 32) != 0)) goto SelectionPath;
        if (Gate(0x12A4, (_state.Data0131 & 2) != 0)) goto AdjustedPath;
        SelectionPath:
        if (Gate(0x12A7, (_state.Data0127 & 2) != 0)) goto ClearHold;
        ClearRequest:
        SetBit(0x22, 0, false); SetBit(0x127, 2, false); goto ReloadD8;
    AdjustedPath:
        if (!allowSubbOffEncoding) return Finish(1, 0x12B4, SubbOffAssumption);
        used.Add(SubbOffAssumption);
        var adjusted = _state.Data0198 - input.Raw0199;
        if (Gate(0x12B6, adjusted < 0)) adjusted = 0;
        else if (!Gate(0x12B8, (_state.Data0127 & 4) == 0))
        { adjusted -= 8; if (!Gate(0x12BD, adjusted >= 0)) adjusted = 0; }
        var above = Compare(0x12C0, adjusted, input.Raw0132);
        if (Gate(0x12C2, above) || Gate(0x12C4, (_state.Data0131 & 4) != 0))
        { Store(0x1DF, 20, writes); goto SetRequest; }
        if (Gate(0x12C9, _state.Data01DF != 0)) goto SetRequest;
        ClearHold:
        Store(0x1DF, 0, writes); SetBit(0x22, 0, false); SetBit(0x127, 2, false);
        if (Gate(0x12D4, (input.Snapshot0119 & 2) != 0)) goto FeedbackSet;
        D9Path:
        if (Gate(0x12D9, _state.Data01D9 != 0)) goto SetSelection;
        ReloadD8:
        Store(0x1D8, 10, writes);
    ClearSelection:
        SetBit(0x127, 1, false); return Finish(0, ExitPc, null);
    SetRequest:
        SetBit(0x22, 0, true); SetBit(0x127, 2, true);
        if (Gate(0x12EE, (input.Snapshot0119 & 2) == 0)) goto D9Path;
        FeedbackSet:
        if (Gate(0x12F3, _state.Data01D8 != 0)) goto ClearSelection;
        Store(0x1D9, 10, writes);
    SetSelection:
        SetBit(0x127, 1, true); return Finish(0, ExitPc, null);

        bool Gate(int pc, bool outcome, int? left = null, int? right = null)
        { gates.Add(pc, new(pc, GateDefinitions.Single(g => g.Pc == pc).Id, outcome, left, right)); gateOrder.Add(pc); return outcome; }
        bool Compare(int pc, int left, int right) => Gate(pc, left < right, left, right);
        void SetBit(int address, int bit, bool value)
        {
            var old = address == 0x22 ? _state.P1OutputData : address == 0x131 ? _state.Data0131 : _state.Data0127;
            Store(address, (old & ~(1 << bit)) | (value ? 1 << bit : 0), writes);
        }
        void Store(int address, int value, List<int[]> journal)
        {
            var b = checked((byte)value); journal.Add([address, 8, b]);
            _state = address switch
            {
                0x131 => _state with { Data0131 = b },
                0x127 => _state with { Data0127 = b },
                0x198 => _state with { Data0198 = b },
                0x1D8 => _state with { Data01D8 = b },
                0x1D9 => _state with { Data01D9 = b },
                0x1DF => _state with { Data01DF = b },
                0xF3 => _state with { Data00F3 = b },
                0x22 => _state with { P1OutputData = b },
                _ => throw new InvalidOperationException(),
            };
        }
        P28StatefulModelStep Finish(int status, int pc, string? unresolved)
        {
            if (status != 0) _stopped = true;
            return new(before, atEntry, _state, ticks.AsReadOnly(), writes.AsReadOnly(),
                Array.AsReadOnly(GateDefinitions.Select(g => gates.GetValueOrDefault(g.Pc) ?? new(g.Pc, g.Id, null)).ToArray()),
                thresholds.AsReadOnly(), status, pc, used.AsReadOnly(), status == 0 ? (_state.P1OutputData & 1) != 0 : null,
                status == 0 ? (_state.Data0127 & 2) != 0 : null, unresolved, gateOrder.AsReadOnly());
        }
    }

    private byte? Interpolate(int context, byte code)
    {
        var start = context == 0 ? 0x654A : 0x6558;
        for (var i = 0; i < 6; i++)
        {
            var at = start + i * 2;
            var nextKey = _rom[at + 2];
            if (code < nextKey) continue;
            var divisor = unchecked((byte)(_rom[at] - nextKey));
            if (divisor == 0) return null;
            var difference = _rom[at + 1] - _rom[at + 3];
            var product = Math.Abs(difference) * unchecked((byte)(code - nextKey));
            return unchecked((byte)(_rom[at + 3] + Math.Sign(difference) * (product / divisor)));
        }
        return null;
    }
}
