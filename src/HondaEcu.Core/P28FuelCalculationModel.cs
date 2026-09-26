namespace HondaEcu.Core;

public sealed record P28FuelCalculationProjection(int Source0140, int Factor0158, ulong Product,
    int LowWord, int HighWord, int ShiftedLowWord, int ShiftedHighWord, int NarrowedWord, bool Saturated, int Output);

/// <summary>Independent wide arithmetic; caller supplies the independent prefix model's own output.</summary>
public static class P28FuelCalculationModel
{
    public static P28FuelCalculationProjection Project(ushort source, ushort factor)
    {
        var product = (ulong)source * factor;
        var shifted = product >> 1;
        var narrowed = (int)((product >> 9) & ushort.MaxValue);
        var saturated = (product >> 25) != 0;
        return new(source, factor, product, (int)(product & ushort.MaxValue), (int)(product >> 16),
            (int)(shifted & ushort.MaxValue), (int)(shifted >> 16), narrowed, saturated,
            saturated ? ushort.MaxValue : narrowed);
    }
}
