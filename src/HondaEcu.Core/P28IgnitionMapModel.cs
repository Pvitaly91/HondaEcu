namespace HondaEcu.Core;

public sealed record P28IgnitionAxisPosition(string AxisId, int Raw, int IndexBefore, int Index, int LowerKnot,
    int UpperKnot, int Numerator, int Denominator, int QuotientQ16, int FractionBefore, int Fraction,
    IReadOnlyList<int> OrderedProgramReads);
public sealed record P28IgnitionMapOperands(IReadOnlyList<int> CellAddresses, IReadOnlyList<int> CellValues,
    int TopColumnResult, int BottomColumnResult, int LookupResult, long TopProduct, long BottomProduct,
    long FinalProduct, IReadOnlyList<int> OrderedProgramReads);
public sealed record P28IgnitionConsumerObservation(int RawFactor, long Product, bool ScalingExecuted, int Output);
public sealed record P28IgnitionMapModelStep(P28IgnitionMapState Before, P28IgnitionMapState AfterInputs,
    P28IgnitionMapState After, P28IgnitionAxisPosition Map0Rpm, P28IgnitionAxisPosition Map1Rpm,
    P28IgnitionAxisPosition Load, string SelectedMap, int SelectedOrigin, P28IgnitionMapOperands Operands,
    P28IgnitionConsumerObservation Consumer);

/// <summary>Independent ignition lookup model with private ROM bytes and persistent native cache history.</summary>
public sealed class P28IgnitionMapModel
{
    private readonly byte[] _rom;
    private P28IgnitionMapState _state;

    public P28IgnitionMapModel(RomImage image, P28IgnitionMapState initialState)
    { _rom = image.ToArray(); _state = initialState; }

    public P28IgnitionMapModelStep Step(P28IgnitionMapCall call)
    {
        var before = _state;
        var selector = (byte)((before.Selector0227 & ~P28IgnitionMapContract.SelectorMask) |
            (call.MapId == "ignition_map_1" ? P28IgnitionMapContract.SelectorMask : 0));
        var afterInputs = before with { Selector0227 = selector };
        var map0 = Position("ignition_map_0_rpm", P28IgnitionMapContract.Map0RpmAxisOrigin, 20,
            call.RawMap0Rpm, before.Map0RpmIndex, before.Map0RpmFraction);
        // Native 0A32..0A38 substitutes DATA0238 for the second-axis input while context bit 5 is set.
        var map1Raw = (selector & P28IgnitionMapContract.SelectorMask) == 0 ? call.RawMap1Rpm : call.RawMap0Rpm;
        var map1 = Position("ignition_map_1_rpm", P28IgnitionMapContract.Map1RpmAxisOrigin, 20,
            map1Raw, before.Map1RpmIndex, before.Map1RpmFraction);
        var load = Position("load", P28IgnitionMapContract.LoadAxisOrigin, 10, call.RawLoad,
            before.LoadIndex, before.LoadFraction);
        var selectedMap = (selector & P28IgnitionMapContract.SelectorMask) == 0 ? "ignition_map_0" : "ignition_map_1";
        var map = P28IgnitionMapContract.Map(selectedMap);
        var rpm = selectedMap == "ignition_map_0" ? map0 : map1;
        var operands = Lookup(map, load, rpm);
        var consumer = Consume(operands.LookupResult, before.ConsumerFactor0247);
        _state = afterInputs with
        {
            LoadIndex = (byte)load.Index,
            Map0RpmIndex = (byte)map0.Index,
            Map1RpmIndex = (byte)map1.Index,
            LoadFraction = (ushort)load.Fraction,
            Map0RpmFraction = (ushort)map0.Fraction,
            Map1RpmFraction = (ushort)map1.Fraction,
            ConsumerOutput0248 = (byte)consumer.Output,
        };
        return new(before, afterInputs, _state, map0, map1, load, selectedMap, map.Origin, operands, consumer);
    }

    private P28IgnitionAxisPosition Position(string id, int origin, int count, int raw, int cachedIndex, int priorFraction)
    {
        var max = count - 2; var index = Math.Min(cachedIndex, max); var reads = new List<int>();
        while (true)
        {
            index++; reads.Add(origin + index); var next = _rom[origin + index];
            if (next == 0 || next > raw) break;
        }
        while (true)
        {
            index--; reads.Add(origin + index);
            if (raw >= _rom[origin + index]) break;
            if (index == 0) throw new InvalidDataException($"{id} native search escaped below its first knot.");
        }
        reads.Add(origin + index); reads.Add(origin + index + 1);
        var lower = _rom[origin + index]; var upperByte = _rom[origin + index + 1];
        var denominator = (byte)(upperByte - lower);
        if (denominator == 0) throw new InvalidDataException($"{id} selected a zero-width interval.");
        var numerator = (byte)(raw - lower); var quotient = (int)(((long)numerator << 16) / denominator);
        return new(id, raw, cachedIndex, index, lower, upperByte == 0 && index == max ? 256 : upperByte,
            numerator, denominator, quotient, priorFraction, quotient, reads.AsReadOnly());
    }

    private P28IgnitionMapOperands Lookup(P28IgnitionMapContractRow map, P28IgnitionAxisPosition load,
        P28IgnitionAxisPosition rpm)
    {
        var topLeft = P28IgnitionMapContract.CellOffset(map.Id, rpm.Index, load.Index);
        var addresses = new[] { topLeft, topLeft + 1, topLeft + P28IgnitionMapContract.Columns,
            topLeft + P28IgnitionMapContract.Columns + 1 };
        var cells = addresses.Select(address => (int)_rom[address]).ToArray();
        var topProduct = (long)Math.Abs(cells[1] - cells[0]) * (ushort)load.Fraction;
        var bottomProduct = (long)Math.Abs(cells[3] - cells[2]) * (ushort)load.Fraction;
        var top = Interpolate(cells[0], cells[1], load.Fraction);
        var bottom = Interpolate(cells[2], cells[3], load.Fraction);
        var finalProduct = (long)Math.Abs(bottom - top) * (ushort)rpm.Fraction;
        var lookup = Interpolate(top, bottom, rpm.Fraction);
        return new(Array.AsReadOnly(addresses), Array.AsReadOnly(cells), top, bottom, lookup, topProduct,
            bottomProduct, finalProduct, Array.AsReadOnly(addresses));
    }

    internal static int Interpolate(int lower, int upper, int weightQ16)
    {
        var delta = (int)(((long)Math.Abs(upper - lower) * (ushort)weightQ16) >> 16);
        return upper < lower ? lower - delta : lower + delta;
    }

    internal static P28IgnitionConsumerObservation Consume(int lookupResult, int rawFactor)
    {
        var product = (long)(byte)lookupResult * (byte)rawFactor;
        return new(rawFactor, product, rawFactor != 0, rawFactor == 0 ? lookupResult : (int)(product >> 8));
    }
}
