namespace HondaEcu.Core;

public sealed record P28IdleModelStep(P28IdleState Before, P28IdleState AfterProducer, P28IdleState After, int UpperCell, int LowerCell,
    int UpperAxis, int LowerAxis, int UpperValue, int LowerValue, int FractionNumerator, int FractionDenominator, int TruncatedDelta,
    int FinalTarget, bool CurrentBelowTarget, int DifferenceModuloWord, int AbsoluteError, int ClampedError,
    IReadOnlyList<int[]> ProducerWrites, IReadOnlyList<int[]> ConsumerWrites, IReadOnlyList<int> ProducerReads,
    IReadOnlyList<int> ConsumerReads, IReadOnlyList<int[]> ProducerBranches, IReadOnlyList<int[]> ConsumerBranches);

/// <summary>Separate image and history; integer interpolation and unsigned error, not an RPM codec or CPU.</summary>
public sealed class P28IdleModel
{
    private readonly byte[] _rom;
    private P28IdleState _state;
    public P28IdleModel(RomImage image, P28IdleState initial)
    { P28IdleInspector.TableGuard(image); _rom = image.ToArray(); _state = initial; }
    private int W(int a) => P28LimiterInspector.Word(_rom, a);
    public P28IdleModelStep Step(P28IdleCall input)
    {
        if (input.RawD9 < 52 || (_state.Data021a & 1) == 0) throw new ArgumentException("Outside established idle raw context.");
        var before = _state; var x = input.RawD9; var writes = new List<int[]>(); var reads = new List<int>(); var branches = new List<int[]>();
        void Store(int a, int v, int width = 16) => writes.Add([a, width, v]);
        void Branch(int a, int next) => branches.Add([a, next]);
        void Read(int a, int width = 2) { for (var i = 0; i < width; i++) reads.Add(a + i); }
        var table = W(0x2FD5); Store(0x208, x, 8); Store(0x88, table); Store(0x8A, W(0x7D8B)); Store(0x20A, _rom[0x7D8E], 8);
        Branch(0x7D8F, 0x7D92); Store(0x20A, _rom[0x2FDB], 8); Branch(0x2FDE, 0x2FEC); Branch(0x2FED, 0x306E);
        Store(0x7FE, 0x3070); Read(0x28);
        var cell = 0;
        while (true)
        {
            Read(table + 3, 1); var found = x >= _rom[table + 3]; Branch(0x5898, found ? 0x58A1 : 0x589A);
            if (found) break;
            table += 3; cell++; Store(0x88, table);
            if (cell >= 6) throw new InvalidDataException("Target interpolation escaped reviewed table.");
        }
        var upperX = (int)_rom[table]; var lowerX = (int)_rom[table + 3]; var upperY = W(table + 1); var lowerY = W(table + 4);
        var distance = x - lowerX; var denominator = upperX - lowerX;
        Store(0x208, x, 8); Read(table); Store(0x20C, W(table)); Read(table + 4); Store(0x20E, lowerY); Read(table + 2);
        Store(0x208, distance, 8); Store(0x20C, denominator, 8); Store(0x209, 0, 8); Store(0x20D, 0, 8);
        var negative = upperY < lowerY; Branch(0x58BB, negative ? 0x58BD : 0x58CA);
        if (negative) Store(0x20A, (upperY - lowerY) & 65535);
        var product = Math.Abs(upperY - lowerY) * distance; var delta = product / denominator;
        Store(0x20A, product >> 16); Store(0x208, product >> 16); Store(0x208, 0); Store(0x20A, product % denominator);
        var target = lowerY + (negative ? -delta : delta); Store(0x20E, target);
        Store(0x20E, 0); Store(0x8C, target); Branch(0x3074, 0x309A); Store(0x27A, 0); Branch(0x309D, 0x30A9); Store(0x25C, target);
        var produced = before with { Target = (ushort)target, Raw027a = 0 };
        var consumerWrites = new List<int[]>(); var consumerReads = new List<int>(); var consumerBranches = new List<int[]>();
        var current = (int)input.RawPeriod; var borrow = current < target; var absolute = Math.Abs(current - target);
        var signByte = (byte)((before.Data021a & ~16) | (borrow ? 16 : 0));
        consumerWrites.Add([0x21A, 8, signByte]); consumerWrites.Add([0x200, 16, W(0x9E5)]);
        consumerBranches.Add([0x9E7, borrow ? 0x9E9 : 0x9EE]);
        if (borrow) { consumerWrites.Add([0x7FE, 16, 0x9EA]); consumerReads.AddRange([0x36, 0x37]); consumerWrites.Add([0x200, 16, W(0x9EC)]); }
        var limit = W(borrow ? 0x9EC : 0x9E5); consumerBranches.Add([0x9EF, absolute < limit ? 0x9F2 : 0x9F1]);
        var magnitude = Math.Min(absolute, limit); consumerWrites.Add([0xCA, 16, magnitude]);
        _state = produced with { Data021a = signByte, ErrorMagnitude = (ushort)magnitude };
        return new(before, produced, _state, cell, cell + 1, upperX, lowerX, upperY, lowerY, distance, denominator, delta,
            target, borrow, (current - target) & 65535, absolute, magnitude, writes.AsReadOnly(), consumerWrites.AsReadOnly(),
            reads.AsReadOnly(), consumerReads.AsReadOnly(), branches.AsReadOnly(), consumerBranches.AsReadOnly());
    }
}
