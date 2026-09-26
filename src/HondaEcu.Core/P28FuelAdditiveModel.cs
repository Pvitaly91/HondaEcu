namespace HondaEcu.Core;

public sealed record P28FuelAdditiveProjection(int UnsignedBase, int SignedFirst, int SignedSecond, int Correction,
    int CorrectionWord, byte ModeAfter, P28FuelCalculationProjection Scaling, int Corrected, int Store03a2, int Store03b4);

/// <summary>Independent staged wide arithmetic; no actual native intermediates are model inputs.</summary>
public static class P28FuelAdditiveModel
{
    public static P28FuelAdditiveProjection Project(ushort ownLookup, P28FuelAdditiveSources s, byte mode, byte gate)
    {
        var baseValue = (uint)s.Source0142;
        if ((mode & 8) != 0) { baseValue = Math.Min(baseValue + 100u, 65535u); mode = (byte)((mode & ~8) | (s.Counter00f2 < 4 ? 8 : 0)); }
        baseValue = Math.Min(baseValue + s.Source0144, 65535u);
        baseValue = Math.Min(baseValue + s.Source014a, 65535u);
        baseValue = Math.Min(baseValue + s.Source014c, 65535u);
        var first = Math.Clamp((int)unchecked((short)s.Source0146) + unchecked((sbyte)s.Source0148), -32768, 32767);
        var second = Math.Clamp(first + unchecked((sbyte)s.Source0149), -32768, 32767);
        var correction = Math.Min(second + (int)baseValue, 32767);
        var scaling = P28FuelCalculationModel.Project(ownLookup, s.Factor0158);
        var corrected = Math.Clamp(scaling.Output + correction, 0, 65535);
        return new((int)baseValue, first, second, correction, unchecked((ushort)correction), mode, scaling, corrected,
            (gate & 0x20) != 0 ? 0 : corrected, corrected);
    }
}
