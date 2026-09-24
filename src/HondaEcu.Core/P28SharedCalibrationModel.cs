namespace HondaEcu.Core;

public sealed record P28SharedAxisPosition(string Id, int Raw, int IndexBefore, int Index, int FractionBefore,
    int Fraction, IReadOnlyList<int> ProgramReads);
public sealed record P28SharedModelStep(P28SharedState Before, P28SharedState AfterInputs,
    P28SharedState AfterTicks, IReadOnlyList<int[]> TickWrites, P28SharedState AfterProducer,
    P28SharedState AfterAxis, P28SharedState AfterIgnition,
    P28SharedState After, P28SharedAxisPosition Map0Rpm, P28SharedAxisPosition Map1Rpm,
    P28SharedAxisPosition IgnitionLoad, P28SharedAxisPosition FuelLoad,
    IReadOnlyList<int> ProducerProgramReads, IReadOnlyList<int> ProducerPath,
    int IgnitionOrigin, IReadOnlyList<int> IgnitionCellAddresses, IReadOnlyList<int> IgnitionCells,
    int IgnitionTop, int IgnitionBottom, int IgnitionLookup, P28IgnitionConsumerObservation IgnitionConsumer,
    P28StatefulModelStep Decision, int? FuelOrigin, IReadOnlyList<int>? FuelProgramReads,
    int? FuelLookup, P28FuelConsumerObservation? FuelConsumer);

/// <summary>One independent ROM and one persistent shared RPM-cache history for both consumers.</summary>
public sealed class P28SharedCalibrationModel
{
    private readonly byte[] _rom;
    private readonly P28StatefulModel _vtec;
    private P28SharedState _state;

    public P28SharedCalibrationModel(RomImage image, P28SharedState initial)
    {
        _rom = image.ToArray(); _state = initial;
        _vtec = new P28StatefulModel(image.Span, initial.Vtec);
    }
    public P28SharedState State => _state;

    public P28SharedModelStep Step(P28SharedCall call, bool allowSubb)
    {
        var before = _state;
        var afterInputs = before with { Source03c7 = call.Source03c7 };
        var tickWrites = _vtec.AdvanceCounters(call.Decision.FastTicks, call.Decision.SlowTicks);
        var afterTicks = afterInputs with { Vtec = _vtec.State };
        if (_rom[0x60FB] != 0 || _rom[0x60EA] != 0 || _rom[0x7E02] != 0)
            throw new InvalidDataException("M2h model requires exact bound selector configuration.");
        var afterProducer = afterTicks with { Selector0227 = (byte)(afterTicks.Selector0227 & ~0x20) };
        var a = before.Axes;
        var rpm0 = Position("map0-rpm", P28IgnitionMapContract.Map0RpmAxisOrigin, 20,
            call.RawMap0Rpm, a.Map0RpmIndex, a.Map0RpmFraction);
        var rpm1 = Position("map1-rpm", P28IgnitionMapContract.Map1RpmAxisOrigin, 20,
            call.RawMap1Rpm, a.Map1RpmIndex, a.Map1RpmFraction);
        var ignitionLoad = Position("ignition-load", P28IgnitionMapContract.LoadAxisOrigin, 10,
            call.RawLoad, a.IgnitionLoadIndex, a.IgnitionLoadFraction);
        var fuelLoad = Position("fuel-load", P28FuelMapContract.LoadAxisOrigin, 10,
            call.RawLoad, a.FuelLoadIndex, a.FuelLoadFraction);
        var afterAxis = afterProducer with
        {
            Axes = new P28SharedAxes((byte)ignitionLoad.Index,
            (byte)fuelLoad.Index, (byte)rpm0.Index, (byte)rpm1.Index,
            (ushort)ignitionLoad.Fraction, (ushort)fuelLoad.Fraction,
            (ushort)rpm0.Fraction, (ushort)rpm1.Fraction)
        };
        var ignitionMap = P28IgnitionMapContract.Map("ignition_map_0");
        var ignitionBase = P28IgnitionMapContract.CellOffset(ignitionMap.Id, rpm0.Index, ignitionLoad.Index);
        var ignitionAddresses = new[] { ignitionBase, ignitionBase + 1,
            ignitionBase + P28IgnitionMapContract.Columns, ignitionBase + P28IgnitionMapContract.Columns + 1 };
        var ignitionCells = ignitionAddresses.Select(p => (int)_rom[p]).ToArray();
        var ignitionTop = P28IgnitionMapModel.Interpolate(ignitionCells[0], ignitionCells[1], ignitionLoad.Fraction);
        var ignitionBottom = P28IgnitionMapModel.Interpolate(ignitionCells[2], ignitionCells[3], ignitionLoad.Fraction);
        var ignitionLookup = P28IgnitionMapModel.Interpolate(ignitionTop, ignitionBottom, rpm0.Fraction);
        var ignitionConsumer = P28IgnitionMapModel.Consume(ignitionLookup, afterAxis.Factor0247);
        var afterIgnition = afterAxis with { Output0248 = (byte)ignitionConsumer.Output };
        var decision = _vtec.Step(call.Decision with { FastTicks = 0, SlowTicks = 0 }, allowSubb);
        var afterDecision = afterIgnition with { Vtec = decision.After };
        int? fuelOrigin = null; IReadOnlyList<int>? fuelReads = null; int? fuelLookup = null;
        P28FuelConsumerObservation? fuelConsumer = null;
        if (decision.Status == 0)
        {
            var mapId = (decision.After.Data0127 & 2) == 0 ? "map_0" : "map_1";
            var selected = P28FuelMapContract.Map(mapId);
            var rpm = mapId == "map_0" ? rpm0 : rpm1;
            var baseCell = P28FuelMapContract.CellOffset(mapId, rpm.Index, fuelLoad.Index);
            var cells = new[] { (int)_rom[baseCell], (int)_rom[baseCell + 1],
                (int)_rom[baseCell + P28FuelMapContract.Columns],
                (int)_rom[baseCell + P28FuelMapContract.Columns + 1] };
            var metadata = P28FuelMapContract.MetadataOffset(mapId, fuelLoad.Index);
            var m0 = _rom[metadata]; var m1 = _rom[metadata + 1];
            var top = P28FuelMapModel.Interpolate(cells[0] * m0, cells[1] * m1, fuelLoad.Fraction);
            var bottom = P28FuelMapModel.Interpolate(cells[2] * m0, cells[3] * m1, fuelLoad.Fraction);
            fuelLookup = P28FuelMapModel.Interpolate(top, bottom, rpm.Fraction);
            fuelReads = Array.AsReadOnly(new[] { metadata, metadata + 1, baseCell, baseCell + 1,
                baseCell + P28FuelMapContract.Columns, baseCell + P28FuelMapContract.Columns + 1, 0x60E5 });
            fuelConsumer = P28FuelMapModel.Consume(fuelLookup.Value, afterDecision.Factor013f, _rom[0x60E5]);
            fuelOrigin = selected.Origin;
            afterDecision = afterDecision with { Output0140 = (ushort)fuelConsumer.Output };
        }
        _state = afterDecision;
        return new(before, afterInputs, afterTicks, tickWrites, afterProducer, afterAxis, afterIgnition, afterDecision,
            rpm0, rpm1, ignitionLoad, fuelLoad, [0x60FB, 0x60EA],
            [0x5F93, 0x5F96, 0x5F97, 0x5F98, 0x5F99, 0x5F9D, 0x7DF4, 0x7DF5, 0x7DF7,
                0x5FA0, 0x5FA4, 0x5FAC], ignitionMap.Origin,
            Array.AsReadOnly(ignitionAddresses), Array.AsReadOnly(ignitionCells),
            ignitionTop, ignitionBottom, ignitionLookup, ignitionConsumer,
            decision, fuelOrigin, fuelReads, fuelLookup, fuelConsumer);
    }

    private P28SharedAxisPosition Position(string id, int origin, int count, int raw, int cached, int priorFraction)
    {
        var max = count - 2; var index = Math.Min(cached, max); var reads = new List<int>();
        while (true)
        {
            index++; reads.Add(origin + index);
            var next = _rom[origin + index];
            if (next == 0 || next > raw) break;
        }
        while (true)
        {
            index--; reads.Add(origin + index);
            if (raw >= _rom[origin + index]) break;
            if (index == 0) throw new InvalidDataException($"{id} escaped its first knot.");
        }
        reads.Add(origin + index); reads.Add(origin + index + 1);
        var lower = _rom[origin + index]; var upper = _rom[origin + index + 1];
        var denominator = (byte)(upper - lower);
        if (denominator == 0) throw new InvalidDataException($"{id} selected a zero-width interval.");
        var fraction = (int)(((long)(byte)(raw - lower) << 16) / denominator);
        return new(id, raw, cached, index, priorFraction, fraction, reads.AsReadOnly());
    }
}
