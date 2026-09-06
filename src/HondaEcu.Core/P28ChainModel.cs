namespace HondaEcu.Core;

public sealed record P28ChainExpectedStage(string Id, int Status, int? StopPc, P28ChainState Before, P28ChainState After,
    IReadOnlyList<int[]> PersistentWrites, IReadOnlyList<int[]> PeripheralAccesses, IReadOnlyList<string> UsedAssumptions,
    IReadOnlyList<string> CumulativeAssumptions, P28StatefulModelStep? Decision = null, string? Disposition = null);
public sealed record P28ChainExpectedEvent(P28ChainState Before, P28ChainState AfterInputs, IReadOnlyList<int[]> CallerWrites,
    IReadOnlyList<P28ChainExpectedStage> Stages, P28ChainState After, bool? SoftwareRequest, bool? RequestMirror, bool? SelectionStatus);

/// <summary>Composition of existing models on independent persistent state; never accepts runner checkpoints.</summary>
public sealed class P28ChainModel
{
    private P28ChainState _state;
    private readonly P28StatefulModel _decision;
    private readonly HashSet<string> _allowed;
    private readonly HashSet<string> _cumulative = new(StringComparer.Ordinal);
    private bool _stopped;
    public P28ChainState State => _state;
    public P28ChainModel(ReadOnlySpan<byte> rom, P28ChainState initial, IEnumerable<string> allowed)
    { _state = P28ChainScenario.Snapshot(initial); _decision = new(rom, initial.Decision); _allowed = new(allowed, StringComparer.Ordinal); }

    internal static IReadOnlyList<int[]> CallerWrites(P28ChainState previous, P28ChainEvent e) => new int[][]
    {
        [0xCC,8,e.Raw.Raw00CC], [0xD9,8,e.Raw.Raw00D9], [0x119,8,e.Raw.Snapshot0119], [0x11A,16,e.Raw.Snapshot011A],
        [0x11C,8,e.Raw.Snapshot011C], [0x132,8,e.Raw.Raw0132], [0x199,8,e.Raw.Raw0199],
        [0x11E,8,(previous.Data011E & ~24) | (e.Context == 0 ? 8 : 0) | (e.Enabled ? 16 : 0)],
    };
    public P28ChainExpectedEvent Step(P28ChainEvent e)
    {
        _ = P28ChainScenario.Create(_state, [e with { Index = 0 }], "model event validation");
        var before = _state;
        var caller = _stopped ? [] : CallerWrites(_state, e);
        if (!_stopped) _state = _state with { Raw = e.Raw, Data011E = (byte)caller[^1][2] };
        var afterInputs = _state; var stages = new List<P28ChainExpectedStage>();
        bool? request = null, mirror = null, selection = null;
        foreach (var id in new[] { "Acquisition", "NativeCounterBodies", "G", "F", "Decision" })
        {
            var old = _state; var writes = new List<int[]>(); var peripheral = new List<int[]>();
            var used = new List<string>(); var status = 4; int? pc = null; P28StatefulModelStep? decision = null; string? disposition = null;
            if (!_stopped && (id is "Acquisition" or "NativeCounterBodies" || e.RunDecision))
            {
                status = 0;
                if (id == "Acquisition")
                {
                    var a = _state.Acquisition;
                    var result = P28AcquisitionModel.Evaluate(a, new(e.Index, e.Tmr2, e.Irqh, e.Tcon2, e.Slot, false, 0, 0, false));
                    disposition = result.Disposition.ToString(); pc = result.StopPc;
                    if (result.Disposition == P28AcquisitionDisposition.UnsupportedMode) { status = 5; pc = null; }
                    else
                    {
                        peripheral.AddRange(result.PeripheralAccesses);
                        if ((e.Tmr2 & 0x8000) == 0 && (e.Irqh & 1) != 0)
                        { writes.Add([0xAE, 8, unchecked((byte)(a.Data00AE + 1))]); writes.Add([0xB6, 8, a.Data00B6 | 1]); }
                        writes.Add([0x128, 8, a.Data0128 | 8]);
                        if ((a.Data0128 & 8) != 0) { writes.Add([0x136, 16, result.State.Data0136]); writes.AddRange(result.SampleWrites); }
                        writes.Add([0xEE, 16, e.Tmr2]); writes.Add([0xAE, 8, 0]);
                        _state = _state with { Acquisition = result.State };
                    }
                }
                else if (id == "NativeCounterBodies")
                {
                    if (e.FastTicks + e.SlowTicks == 0) status = 4;
                    else { writes.AddRange(_decision.AdvanceCounters(e.FastTicks, e.SlowTicks)); _state = _state with { Decision = _decision.State }; pc = e.SlowTicks > 0 ? 0x3CF3 : 0x5BD9; }
                }
                else if (id == "G")
                {
                    var a = _state.Acquisition;
                    var g = P28ProducerModel.Evaluate(new(e.Index, "IndependentIntegratedHistory", 0, a.Samples, a.PreviousT, a.Data0217, a.Data0231, 0, 0, false),
                        _allowed.Contains(P28ProducerModel.AddEr1Assumption));
                    disposition = g.Disposition.ToString(); status = g.Resolved ? 0 : 1; pc = g.Resolved ? 0x07A5 : 0x077E;
                    used.AddRange(g.UsedAssumptions);
                    if ((a.Data0217 & 0x80) != 0)
                        for (var i = 0; i < g.ProcessedSamples + (g.Resolved ? 0 : 1); i++) writes.Add([0x360 + 2 * i, 16, 1]);
                    if (g.Resolved)
                    {
                        if (g.Disposition != P28ProducerDisposition.ZeroSampleFallback)
                        { writes.Add([0x217, 8, a.Data0217 & ~16]); writes.Add([0x231, 8, a.Data0231 & ~32]); }
                        if (g.FallbackFlag) writes.Add([0x231, 8, g.Flags0231]);
                        writes.Add([0xC4, 16, g.T]);
                    }
                    _state = _state with { Acquisition = P28AcquisitionModel.Snapshot(a with { Samples = g.Samples, PreviousT = g.T, Data0217 = g.Flags0217, Data0231 = g.Flags0231 }) };
                }
                else if (id == "F")
                {
                    var a = _state.Acquisition; var f = P28CompactModel.Evaluate(a.PreviousT, (a.Data0217 & 16) != 0);
                    if (!f.Resolved && _allowed.Contains(P28ByteExecutionValidator.AddAssumption))
                    {
                        var h = P28CompactModel.EvaluateHypothesis(a.PreviousT, (a.Data0217 & 16) != 0);
                        f = new(h.Code, h.ExtraBit, h.Branch, true); used.Add(P28ByteExecutionValidator.AddAssumption);
                    }
                    disposition = f.Branch.ToString(); status = f.Resolved ? 0 : 1; pc = f.Resolved ? 0x0822 : 0x07F8;
                    if (f.Resolved)
                    {
                        _state = _state with { Code = f.Code!.Value, Data00B8 = (byte)((_state.Data00B8 & ~16) | (f.ExtraBit!.Value ? 16 : 0)) };
                        writes.Add([0xB8, 8, _state.Data00B8]); writes.Add([0x133, 8, _state.Code]);
                    }
                }
                else
                {
                    var r = _state.Raw;
                    decision = _decision.Step(new(e.Index, _state.Code, (_state.Data011E & 8) != 0 ? 0 : 1, (_state.Data011E & 16) != 0,
                        r.Raw00CC, r.Raw00D9, r.Snapshot011A, r.Snapshot011C, r.Snapshot0119, r.Raw0132, r.Raw0199, 0, 0), _allowed.Contains(P28StatefulModel.SubbOffAssumption));
                    status = decision.Status; pc = decision.StopPc; used.AddRange(decision.UsedAssumptions); writes.AddRange(decision.DecisionWrites);
                    _state = _state with { Decision = decision.After };
                    if (status == 0) { request = decision.SoftwareRequest; mirror = (_state.Decision.Data0127 & 4) != 0; selection = decision.SelectionStatus; }
                }
                if (status is 1 or 2 or 3 or 5) _stopped = true;
            }
            _cumulative.UnionWith(used);
            stages.Add(new(id, status, pc, old, _state, writes.AsReadOnly(), peripheral.AsReadOnly(), used.AsReadOnly(), _cumulative.Order(StringComparer.Ordinal).ToArray(), decision, disposition));
        }
        return new(before, afterInputs, caller, stages.AsReadOnly(), _state, request, mirror, selection);
    }
}
