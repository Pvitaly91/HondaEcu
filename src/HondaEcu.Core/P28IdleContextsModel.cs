namespace HondaEcu.Core;

public sealed record P28IdleSourceObservation(string Source, int OperandAddress, int Value, bool FinalContribution);
public sealed record P28IdleLookupObservation(int Table, int UpperCell, int LowerCell, int UpperAxis, int LowerAxis,
    int UpperValue, int LowerValue, int Distance, int Denominator, int TruncatedDelta, int Value, bool FinalContribution);
public sealed record P28IdleComponentObservation(int Peak, int LowerAxis, int UpperThreshold, int WrappedDistance,
    int? Denominator, int? TruncatedDelta, int Value);
public sealed record P28IdleContextsModelStep(P28IdleContextsState Before, P28IdleContextsState AfterInputs,
    P28IdleContextsState AfterProducer, P28IdleContextsState After, string FinalSource,
    IReadOnlyList<P28IdleSourceObservation> Sources, IReadOnlyList<P28IdleLookupObservation> Lookups,
    P28IdleComponentObservation? ComponentCalculation, int BaseResult, int FinalTarget, bool CurrentBelowTarget,
    int DifferenceModuloWord, int AbsoluteError, int ClampedError,
    IReadOnlyList<int[]> ProducerWrites, IReadOnlyList<int[]> ConsumerWrites, IReadOnlyList<int> ProducerReads,
    IReadOnlyList<int> ConsumerReads, IReadOnlyList<int[]> ProducerBranches, IReadOnlyList<int[]> ConsumerBranches,
    IReadOnlyList<int[]> ProducerComparisons, IReadOnlyList<int[]> ProducerAccumulators);

/// <summary>Code-derived integer source/override model with its own image and history; not a CPU or physical mode model.</summary>
public sealed class P28IdleContextsModel
{
    private readonly byte[] _rom;
    private P28IdleContextsState _state;
    public P28IdleContextsModel(RomImage image, P28IdleContextsState initial)
    { P28IdleContextsInspector.TableGuard(image); _rom = image.ToArray(); _state = initial; }
    private int W(int a) => P28LimiterInspector.Word(_rom, a);
    public P28IdleContextsModelStep Step(P28IdleContextsCall input)
    {
        var before = _state; var state = P28IdleContextsScenario.ApplySelectors(before, input.Selectors); var afterInputs = state;
        var x = (int)input.RawD9; var writes = new List<int[]>(); var reads = new List<int>(); var branches = new List<int[]>();
        var comparisons = new List<int[]>(); var accumulators = new List<int[]>();
        var sources = new List<P28IdleSourceObservation>(); var lookups = new List<P28IdleLookupObservation>();
        var finalBase = (state.Data021a & 1) != 0; var bit216 = (state.Data0216 & 8) != 0; var bit225 = (state.Data0225 & 2) != 0;
        void Store(int a, int value, int width = 16) => writes.Add([a, width, value]);
        bool Branch(int pc, bool condition, int yes, int no) { branches.Add([pc, condition ? yes : no]); return condition; }
        void Cmp(int pc, int lhs, int rhs) => comparisons.Add([pc, lhs, rhs]);
        void Read(int a, int width = 2) { for (var i = 0; i < width; i++) reads.Add(a + i); }
        void Acc(int pc, int a, int b) => accumulators.Add([pc, a, b]);
        // Same reviewed packed-helper integer algebra/ABI as M1q, including its ordered overlapping reads.
        (int Value, int Delta) Interpolate(int upper, int lower, int distance, int denominator)
        {
            var negative = upper < lower; Acc(0x58BA, upper, (upper - lower) & 65535);
            Branch(0x58BB, negative, 0x58BD, 0x58CA);
            if (negative) Store(0x20A, (upper - lower) & 65535);
            var product = Math.Abs(upper - lower) * distance; var delta = product / denominator;
            Acc(negative ? 0x58C0 : 0x58CA, Math.Abs(upper - lower), product & 65535);
            Store(0x20A, product >> 16); Store(0x208, product >> 16);
            Acc(negative ? 0x58C4 : 0x58CE, product & 65535, delta);
            Store(0x208, 0); Store(0x20A, product % denominator);
            var value = lower + (negative ? -delta : delta); Store(0x20E, value); return (value, delta);
        }
        int Lookup(int start, int returnPc, bool contributes)
        {
            Store(0x7FE, returnPc); Read(0x28); var table = start; var cell = 0;
            while (true)
            {
                Read(table + 3, 1);
                // CMPCB compares the actual byte axis with AL (not the full accumulator).
                Cmp(0x5894, x, _rom[table + 3]);
                if (Branch(0x5898, x >= _rom[table + 3], 0x58A1, 0x589A)) break;
                table += 3; cell++; Store(0x88, table);
                if (cell >= 6) throw new InvalidDataException("Contexts lookup escaped the reviewed table.");
            }
            var upperX = (int)_rom[table]; var lowerX = (int)_rom[table + 3]; var upperY = W(table + 1); var lowerY = W(table + 4);
            var distance = x - lowerX; var denominator = upperX - lowerX;
            Store(0x208, x, 8); Read(table); Store(0x20C, W(table)); Read(table + 4); Store(0x20E, lowerY); Read(table + 2);
            Store(0x208, distance, 8); Store(0x20C, denominator, 8); Store(0x209, 0, 8); Store(0x20D, 0, 8);
            var result = Interpolate(upperY, lowerY, distance, denominator);
            lookups.Add(new(start, cell, cell + 1, upperX, lowerX, upperY, lowerY, distance, denominator, result.Delta, result.Value, contributes));
            return result.Value;
        }
        var baseTable = W(0x2FD5); Store(0x208, x, 8); Store(0x88, baseTable); Store(0x8A, W(0x7D8B));
        var r2 = (int)_rom[0x7D8E]; Store(0x20A, r2, 8);
        if (!Branch(0x7D8F, bit216, 0x7D95, 0x7D92)) { r2 = _rom[0x2FDB]; Store(0x20A, r2, 8); }
        var threshold = r2;
        (int Value, int Peak, string Source) Immediate(int operand, int peakOperand, string id)
        { var value = W(operand); var peak = W(peakOperand); Acc(operand - 1, -1, value); Store(0x20E, peak); sources.Add(new(id, operand, value, false)); return (value, peak, id); }
        (int Value, int Peak, string Source) Override1()
        {
            threshold = r2; Store(0x209, threshold, 8); var result = Immediate(0x2FE3, 0x2FE7, "override-2fe2");
            if (!Branch(0x7D98, bit216, 0x7DA2, 0x7D9B)) result = Immediate(0x7D9C, 0x7DA0, "override-7d9b");
            return result;
        }
        (int Value, int Peak, string Source) Override2() => Immediate(0x300E, 0x3012, "override-300d");
        (int Value, int Peak, string Source) BaseLookup()
        { var value = Lookup(baseTable, 0x3070, finalBase); Store(0x20E, 0); return (value, 0, "table-68cb"); }
        (int Value, int Peak, string Source) SelectBase()
        {
            Cmp(0x2FDC, x, _rom[0x2FDD]);
            if (!Branch(0x2FDE, x >= _rom[0x2FDD], 0x2FEC, 0x2FE0)) return Override1();
            Cmp(0x2FEC, x, r2);
            if (Branch(0x2FED, x >= r2, 0x306E, 0x2FEF)) return BaseLookup();
            threshold = _rom[0x2FF0]; Store(0x209, threshold, 8);
            if (!Branch(0x2FF1, (state.Data0217 & 64) != 0, 0x3016, 0x2FF4))
            {
                Cmp(0x2FF4, state.Raw0274, W(0x2FF7));
                if (!Branch(0x2FF9, state.Raw0274 >= W(0x2FF7), 0x300A, 0x2FFB))
                {
                    Cmp(0x2FFB, state.Raw0274, W(0x2FFE)); var limit = W(0x2FFE);
                    if (!Branch(0x3000, bit216, 0x3008, 0x3003)) { limit = W(0x3006); Cmp(0x3003, state.Raw0274, limit); }
                    if (Branch(0x3008, state.Raw0274 >= limit, 0x2FE0, 0x300A)) return Override1();
                }
                Cmp(0x300A, x, threshold); return Branch(0x300B, x >= threshold, 0x306E, 0x300D) ? BaseLookup() : Override2();
            }
            if (!Branch(0x3016, (state.Data022a & 16) == 0, 0x3023, 0x3019))
            {
                state = state with { Counter02e8 = _rom[0x301C], Counter02e9 = _rom[0x3020] };
                Store(0x2E8, state.Counter02e8, 8); Store(0x2E9, state.Counter02e9, 8); return Override1();
            }
            if (!Branch(0x3023, !bit225, 0x302C, 0x3026))
            {
                Cmp(0x3026, state.Counter02e8, _rom[0x3029]);
                if (Branch(0x302A, state.Counter02e8 != _rom[0x3029], 0x2FE0, 0x302C)) return Override1();
            }
            Cmp(0x302C, x, threshold);
            if (Branch(0x302D, x >= threshold, 0x306E, 0x302F)) return BaseLookup();
            if (!Branch(0x3031, state.Raw027c == 0, 0x3037, 0x3033))
            { state = state with { Counter02e5 = _rom[0x3036] }; Store(0x2E5, state.Counter02e5, 8); }
            if (Branch(0x3039, state.Counter02e5 != 0, 0x300D, 0x303B)) return Override2();
            if (!Branch(0x303B, (state.Data022a & 32) == 0, 0x3044, 0x303E))
            { state = state with { Counter02e9 = _rom[0x3041] }; Store(0x2E9, state.Counter02e9, 8); return Override2(); }
            if (!Branch(0x3044, !bit225, 0x304B, 0x3047) && Branch(0x3049, state.Counter02e9 != 0, 0x300D, 0x304B)) return Override2();
            if (!Branch(0x304B, !bit216, 0x305E, 0x304E))
            {
                threshold = _rom[0x304F]; Store(0x209, threshold, 8); Cmp(0x3051, x, threshold);
                if (Branch(0x3052, x >= threshold, 0x306E, 0x3054)) return BaseLookup();
                var candidate = Immediate(0x3055, 0x3059, "override-3054");
                if (Branch(0x305B, (state.Data0211 & 32) != 0, 0x3072, 0x305E)) return candidate;
            }
            threshold = _rom[0x305F]; Store(0x209, threshold, 8); Cmp(0x3061, x, threshold);
            if (Branch(0x3062, x >= threshold, 0x306E, 0x3064)) return BaseLookup();
            var last = Immediate(0x3065, 0x3069, "override-3064");
            return Branch(0x306B, bit225, 0x3072, 0x306E) ? last : BaseLookup();
        }
        var selected = SelectBase(); var baseResult = selected.Value; Store(0x8C, baseResult);
        var component = selected.Peak; P28IdleComponentObservation? componentCalculation = null;
        if (!Branch(0x3074, component == 0, 0x309A, 0x3076))
        {
            var table = W(0x3077); Store(0x88, table); var axisAddress = table + W(0x307B); Read(axisAddress, 1);
            var axis = (int)_rom[axisAddress]; Store(0x20C, axis, 8); var distance = (x - axis) & 255; Store(0x208, distance, 8);
            int? denominator = null; int? delta = null;
            // L A,er3 at3081 replaces ZF: equality of x and axis does NOT take3082 when peak is nonzero.
            if (!Branch(0x3082, x < axis || selected.Peak == 0, 0x309A, 0x3084))
            {
                Store(0x20D, 0, 8); Store(0x209, 0, 8); Cmp(0x3088, threshold, x);
                if (Branch(0x308B, threshold <= x, 0x3099, 0x308D)) component = 0;
                else
                {
                    Store(0x20C, threshold, 8); denominator = (threshold - axis) & 255; Store(0x20C, denominator.Value, 8);
                    if (Branch(0x3091, threshold <= axis, 0x3099, 0x3093)) component = 0;
                    else { Store(0x7FE, 0x3097); var interpolation = Interpolate(0, selected.Peak, distance, denominator.Value); component = interpolation.Value; delta = interpolation.Delta; }
                }
            }
            componentCalculation = new(selected.Peak, axis, threshold, distance, denominator, delta, component);
        }
        Store(0x27A, component); Acc(0x309C, component, baseResult);
        var target = baseResult; var source = selected.Source;
        if (!Branch(0x309D, finalBase, 0x30A9, 0x30A0))
        { var alternate = W(0x30A3); Store(0x88, alternate); target = Lookup(alternate, 0x30A6, true); Store(0x8A, W(0x30A7)); source = "table-68e0"; }
        else if (sources.Count > 0 && sources[^1].Source == selected.Source) sources[^1] = sources[^1] with { FinalContribution = true };
        Store(0x25C, target); var produced = state with { Target = (ushort)target, Raw027a = (ushort)component };
        var current = (int)input.RawPeriod; var borrow = current < target; var absolute = Math.Abs(current - target);
        var signByte = (byte)((state.Data021a & ~16) | (borrow ? 16 : 0));
        var consumerWrites = new List<int[]> { new[] { 0x21A, 8, (int)signByte }, new[] { 0x200, 16, W(0x9E5) } };
        var consumerReads = new List<int>(); var consumerBranches = new List<int[]> { new[] { 0x9E7, borrow ? 0x9E9 : 0x9EE } };
        if (borrow) { consumerWrites.Add([0x7FE, 16, 0x9EA]); consumerReads.AddRange([0x36, 0x37]); consumerWrites.Add([0x200, 16, W(0x9EC)]); }
        var limit = W(borrow ? 0x9EC : 0x9E5); consumerBranches.Add([0x9EF, absolute < limit ? 0x9F2 : 0x9F1]);
        var magnitude = Math.Min(absolute, limit); consumerWrites.Add([0xCA, 16, magnitude]);
        _state = produced with { Data021a = signByte, ErrorMagnitude = (ushort)magnitude };
        return new(before, afterInputs, produced, _state, source, sources.AsReadOnly(), lookups.AsReadOnly(), componentCalculation, baseResult,
            target, borrow, (current - target) & 65535, absolute, magnitude, writes.AsReadOnly(), consumerWrites.AsReadOnly(), reads.AsReadOnly(),
            consumerReads.AsReadOnly(), branches.AsReadOnly(), consumerBranches.AsReadOnly(), comparisons.AsReadOnly(), accumulators.AsReadOnly());
    }
}
