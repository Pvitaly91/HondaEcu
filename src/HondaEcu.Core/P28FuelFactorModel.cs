namespace HondaEcu.Core;

public sealed record P28FuelFactorProjection(int SelectedBase, int After0166, int After0167, int After0168,
    int After0162, uint IntermediateProduct0160, int Narrowed0160, bool Saturated0160, uint IntermediateProduct015e,
    bool ProducerModeEnabled, int AfterMode, int After015c, uint FinalProduct015a, int NativeFactor0158,
    int HysteresisThreshold, byte HysteresisAfter);

/// <summary>Independent ordered integer projection. Native observations are never expected operands.</summary>
public static class P28FuelFactorModel
{
    public static P28FuelFactorProjection Project(P28FuelFactorSources s, byte producerMode012c, byte producerSelector012f, byte hysteresis0130)
    {
        ArgumentNullException.ThrowIfNull(s);
        var selected = (producerSelector012f & 0x80) != 0 ? s.Source0164 : s.Source0165;
        uint q = (uint)selected << 7;
        if (s.Source0166 != 0) q = q * s.Source0166 >> 8;
        var after166 = (int)q;
        if (s.Source0167 != 0) q = q * s.Source0167 >> 8;
        var after167 = (int)q;
        q = q * (256u + s.Source0168) >> 8; var after168 = (int)q;
        q = q * s.Source0162 >> 16; var after162 = (int)q;
        var product160 = q * s.Source0160;
        q = Math.Min(product160 >> 10, 65535u); var narrowed160 = (int)q;
        var product15e = q * s.Source015e;
        var enabled = (producerMode012c & 0x10) != 0;
        q = enabled ? Math.Min(product15e << 3 >> 16, 65535u) : product15e >> 16;
        var afterMode = (int)q;
        if (enabled) q = q * s.Source015c >> 16;
        var after15c = (int)q; var finalProduct = q * s.Source015a;
        var factor = (int)(finalProduct >> 16);
        var threshold = (hysteresis0130 & 0x40) != 0 ? 0x66 : 0x6A;
        var nextHysteresis = (byte)((hysteresis0130 & ~0x40) | (threshold < s.Source0133 ? 0x40 : 0));
        return new(selected, after166, after167, after168, after162, product160, narrowed160, product160 >> 10 > 65535,
            product15e, enabled, afterMode, after15c, finalProduct, factor, threshold, nextHysteresis);
    }

    /// <summary>Pure downstream analysis conversion, not a scenario input or a host RAM write.</summary>
    public static P28FuelAdditiveSources AdditiveSources(P28FuelFactorSources s, ushort independentlyProducedFactor) =>
        new(independentlyProducedFactor, s.Source0142, s.Source0144, s.Source0146, s.Source0148, s.Source0149, s.Source014a, s.Source014c, s.Counter00f2);
}
