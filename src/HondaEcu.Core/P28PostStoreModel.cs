namespace HondaEcu.Core;

public sealed record P28PostStoreProjection(int Previous, int Current, int Result, string Reason);
public static class P28PostStoreModel
{
    public static P28PostStoreProjection Project(ushort previous, ushort current, bool disable125, bool disable12e,
        byte source0133, ushort source014c)
    {
        if (disable125) return new(previous, current, 0, "Disabled125");
        if (disable12e) return new(previous, current, 0, "Disabled12e");
        if (source0133 >= 160) return new(previous, current, 0, "Source0133");
        if (source014c != 0) return new(previous, current, 0, "Source014c");
        if (current < previous) return new(previous, current, 0, "UnsignedBorrow");
        var delta = current - previous;
        return new(previous, current, delta < 250 ? 0 : Math.Min(delta, 2000), delta < 250 ? "Below250" : delta < 2000 ? "Rise" : "Clamp2000");
    }
}
// Each image owns an independent model, ROM copy, axis/adaptive/shared-mode and previous-result history.
// Arithmetic expected operands never come from Rust observations.
internal sealed class P28PostStorePrefixModel
{
    private readonly P28AdaptiveModel _adaptive;
    private readonly P28FuelMapModel _map;
    private readonly P28AdaptiveFuelInitial _initial;
    private byte _mode, _hysteresis;
    internal P28PostStorePrefixModel(RomImage image, P28AdaptiveFuelScenario s)
    {
        _initial = s.InitialState; _adaptive = new(image.Span, s.ModelInitial);
        var f = _initial.Joint.Fuel;
        _map = new(image, new(f.LoadIndex, f.Map0RpmIndex, f.Map1RpmIndex, f.LoadFraction, f.Map0RpmFraction,
            f.Map1RpmFraction, f.Selector0127, f.ConsumerFactor013f, 0));
        _mode = _initial.Joint.Data012b; _hysteresis = _initial.Joint.Hysteresis0130;
    }
    internal (P28FuelAdditiveProjection Numeric, P28FuelAdditiveOracle Exit) Step(P28AdaptiveFuelCall c, ushort previous, byte? producerMode012c = null)
    {
        _adaptive.AcceptModeledFuelByte(_mode); _ = _adaptive.StepProduction(c.Adaptive);
        var d = _adaptive.StepDecision(c.Fuel.RawPeriod, c.FixedSource); _mode = d.After.Data012B;
        var f = _initial.Joint.Fuel;
        var lookup = _map.StepFromNativeSelector(new(c.Fuel.Index, c.Fuel.RawLoad, c.Fuel.RawMap0Rpm, c.Fuel.RawMap1Rpm), f.Selector0127).Consumer.Output;
        var factor = P28FuelFactorModel.Project(c.Fuel.Sources, producerMode012c ?? _initial.Joint.ProducerMode012c, _initial.Joint.ProducerSelector012f, _hysteresis);
        _hysteresis = factor.HysteresisAfter;
        var sources = P28FuelFactorModel.AdditiveSources(c.Fuel.Sources, (ushort)factor.NativeFactor0158);
        var numeric = P28FuelAdditiveModel.Project((ushort)lookup, sources, _mode, d.After.Data0124);
        var o = P28FuelAdditiveEvidence.Build(0, (ushort)lookup, sources, _mode, d.After.Data0124, lookup, 0x0DC9, 0, 0, 0, 0, previous);
        for (var n = 1; n < 3; n++) o = P28FuelAdditiveEvidence.Build(n, (ushort)lookup, sources, _mode, d.After.Data0124,
            o.Accumulator, o.Psw, o.Er0, o.Er1, o.Er2, o.Er3, previous);
        _mode = numeric.ModeAfter; _adaptive.AcceptModeledFuelByte(_mode);
        return (numeric, o);
    }
    internal ushort ModeledIe => _adaptive.ModeledIe;
    internal void AcceptModeledIe(ushort value) => _adaptive.AcceptModeledIe(value);
    internal void AcceptModeledFuelByte(byte value) => _mode = value;
}
