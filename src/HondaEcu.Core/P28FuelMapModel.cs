namespace HondaEcu.Core;

public sealed record P28FuelAxisPosition(string AxisId, int Raw, int IndexBefore, int Index, int LowerKnot, int UpperKnot,
    int Numerator, int Denominator, int QuotientQ16, int FractionBefore, int Fraction,
    IReadOnlyList<int> OrderedProgramReads);
public sealed record P28FuelMapOperands(IReadOnlyList<int> CellAddresses, IReadOnlyList<int> CellValues,
    IReadOnlyList<int> MultiplierAddresses, IReadOnlyList<int> Multipliers, IReadOnlyList<int> ScaledCells,
    int TopColumnResult, int BottomColumnResult, int LookupResult, IReadOnlyList<int> OrderedProgramReads);
public sealed record P28FuelConsumerObservation(int GateByte, bool CorrectionExecuted, int RawFactor, int FactorWord, long Product, int Shifted, bool Saturated, int Output);
public sealed record P28FuelMapModelStep(P28FuelMapState Before, P28FuelMapState AfterInputs, P28FuelMapState After,
    P28FuelAxisPosition Map0Rpm, P28FuelAxisPosition Map1Rpm, P28FuelAxisPosition Load, string SelectedMap, int SelectedOrigin,
    P28FuelMapOperands Operands, P28FuelConsumerObservation Consumer);

/// <summary>Independent integer model with its own ROM bytes and persistent axis-cache history.</summary>
public sealed class P28FuelMapModel
{
    private readonly byte[] _rom;
    private P28FuelMapState _state;

    public P28FuelMapModel(RomImage image, P28FuelMapState initialState)
    {
        _rom = image.ToArray();
        _state = initialState;
    }

    public P28FuelMapModelStep Step(P28FuelMapCall call)
    {
        var before = _state;
        var selector = (byte)((before.Selector0127 & ~2) | (call.MapId == "map_1" ? 2 : 0));
        var afterInputs = before with { Selector0127 = selector };
        var map0 = Position("map_0_rpm", P28FuelMapContract.Map0RpmAxisOrigin, 20, call.RawMap0Rpm,
            before.Map0RpmIndex, before.Map0RpmFraction);
        var map1 = Position("map_1_rpm", P28FuelMapContract.Map1RpmAxisOrigin, 20, call.RawMap1Rpm,
            before.Map1RpmIndex, before.Map1RpmFraction);
        var load = Position("load", P28FuelMapContract.LoadAxisOrigin, 10, call.RawLoad, before.LoadIndex, before.LoadFraction);
        var selectedMap = (selector & 2) == 0 ? "map_0" : "map_1";
        var selected = P28FuelMapContract.Map(selectedMap);
        var rpm = selectedMap == "map_0" ? map0 : map1;
        var operands = Lookup(selected, load, rpm);
        var consumer = Consume(operands.LookupResult, before.ConsumerFactor013f, _rom[0x60E5]);
        _state = afterInputs with
        {
            LoadIndex = (byte)load.Index,
            Map0RpmIndex = (byte)map0.Index,
            Map1RpmIndex = (byte)map1.Index,
            LoadFraction = (ushort)load.Fraction,
            Map0RpmFraction = (ushort)map0.Fraction,
            Map1RpmFraction = (ushort)map1.Fraction,
            ConsumerOutput0140 = (ushort)consumer.Output,
        };
        return new(before, afterInputs, _state, map0, map1, load, selectedMap, selected.Origin, operands, consumer);
    }

    private P28FuelAxisPosition Position(string id, int origin, int count, int raw, int cachedIndex, int priorFraction)
    {
        var max = count - 2;
        var index = Math.Min(cachedIndex, max);
        var reads = new List<int>();
        while (true)
        {
            index++;
            reads.Add(origin + index);
            var next = _rom[origin + index];
            if (next == 0 || next > raw) break;
        }
        while (true)
        {
            index--;
            reads.Add(origin + index);
            if (raw >= _rom[origin + index]) break;
            if (index == 0) throw new InvalidDataException($"{id} native search escaped below its first knot.");
        }
        reads.Add(origin + index);
        reads.Add(origin + index + 1);
        var lower = _rom[origin + index];
        var upperByte = _rom[origin + index + 1];
        var denominator = (byte)(upperByte - lower);
        if (denominator == 0) throw new InvalidDataException($"{id} selected a zero-width interval.");
        var numerator = (byte)(raw - lower);
        var quotient = (int)(((long)numerator << 16) / denominator);
        var fraction = quotient;
        return new(id, raw, cachedIndex, index, lower, upperByte == 0 && index == max ? 256 : upperByte,
            numerator, denominator, quotient, priorFraction, fraction, reads.AsReadOnly());
    }

    private P28FuelMapOperands Lookup(P28FuelMapContractRow map, P28FuelAxisPosition load, P28FuelAxisPosition rpm)
    {
        var topLeft = P28FuelMapContract.CellOffset(map.Id, rpm.Index, load.Index);
        var topRight = topLeft + 1;
        var bottomLeft = topLeft + P28FuelMapContract.Columns;
        var bottomRight = bottomLeft + 1;
        var multiplierLeft = P28FuelMapContract.MetadataOffset(map.Id, load.Index);
        var multiplierRight = multiplierLeft + 1;
        var cellAddresses = new[] { topLeft, topRight, bottomLeft, bottomRight };
        var cells = cellAddresses.Select(address => (int)_rom[address]).ToArray();
        var multiplierAddresses = new[] { multiplierLeft, multiplierRight };
        var multipliers = multiplierAddresses.Select(address => (int)_rom[address]).ToArray();
        var scaled = new[] { cells[0] * multipliers[0], cells[1] * multipliers[1], cells[2] * multipliers[0], cells[3] * multipliers[1] };
        var top = Interpolate(scaled[0], scaled[1], load.Fraction);
        var bottom = Interpolate(scaled[2], scaled[3], load.Fraction);
        var result = Interpolate(top, bottom, rpm.Fraction);
        // Native order: metadata word, top-row word, next-row word, then the caller's 60E5 byte.
        var reads = new[] { multiplierLeft, multiplierRight, topLeft, topRight, bottomLeft, bottomRight, 0x60E5 };
        return new(Array.AsReadOnly(cellAddresses), Array.AsReadOnly(cells), Array.AsReadOnly(multiplierAddresses),
            Array.AsReadOnly(multipliers), Array.AsReadOnly(scaled), top, bottom, result, Array.AsReadOnly(reads));
    }

    internal static int Interpolate(int lower, int upper, int weightQ16)
    {
        var delta = (int)(((long)Math.Abs(upper - lower) * (ushort)weightQ16) >> 16);
        return upper < lower ? lower - delta : lower + delta;
    }

    internal static P28FuelConsumerObservation Consume(int lookupResult, int rawFactor, int gateByte)
    {
        var factorWord = rawFactor | (rawFactor < 0x80 ? 0x0200 : 0x0100);
        var product = (long)(ushort)lookupResult * factorWord;
        var shifted = (int)(product >> 9);
        var saturated = shifted > ushort.MaxValue;
        var executed = gateByte != 0;
        return new(gateByte, executed, rawFactor, factorWord, product, shifted, saturated,
            executed ? saturated ? ushort.MaxValue : shifted : lookupResult);
    }
}
