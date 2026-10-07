namespace HondaEcu.Core.Tests;

// Invented test-only feasibility scaffolding. No CPU/Bus, operation, host-PC
// scheduling or actual-ROM execution; source/frame witnesses are synthetic.
internal enum CallerSourceKind { NativeOwned, RetainedNative, ResetOnly, TechnicalOnly, Unknown }
internal sealed record ToyCallerFrame(object Machine, int WriterPc, int Event, int Address,
    int Width, int ReturnPc, int GlobalOrder);

internal sealed class PreCallerProvenanceFixture(SoftwareBitProvenance? machineBits = null)
{
    private readonly object machine = new();
    private readonly SoftwareBitProvenance expectedBits = machineBits ?? new(0x19B, 0);
    private int lastOrder = -1;
    private int lastEvent = -1;
    private bool readerProved;
    internal ToyCallerFrame? Pending { get; private set; }
    internal int HypotheticalCalls { get; private set; }
    internal int ActualRomExecutions => 0;

    internal ToyCallerFrame Begin(int callPc, int eventIndex, int stackAddress, int slot,
        CallerSourceKind source, bool irqEntryUnknown = false, bool timerUnknown = false, int globalOrder = 10)
    {
        if (Pending is not null || callPc is < 0 or > 65532 || eventIndex < 0 || eventIndex < lastEvent || globalOrder <= lastOrder || stackAddress is < 2 or > 65534 ||
            (stackAddress & 1) != 0 || slot != 5 || source is not (CallerSourceKind.NativeOwned or CallerSourceKind.RetainedNative) ||
            irqEntryUnknown || timerUnknown)
            throw new InvalidDataException("Unproved caller/slot/IRQ/timer or previous native return.");
        Pending = new(machine, callPc, eventIndex, stackAddress, 16, callPc + 3, globalOrder);
        lastOrder = globalOrder; lastEvent = eventIndex;
        readerProved = false; HypotheticalCalls++; return Pending;
    }

    internal void Reader(SoftwareBitProvenance bits, int readerPc, SoftwareBitOwner? owner)
    {
        if (Pending is null || !ReferenceEquals(bits, expectedBits)) throw new InvalidDataException("No native caller frame or wrong machine history.");
        bits.RequireReader(readerPc, 2, bits.Bit(2).Value, owner); readerProved = true;
    }

    internal void Return(ToyCallerFrame? observed, int readerPc, int expectedRtPc, int word,
        bool hostShortcut = false, bool unknownAlias = false)
    {
        var frame = Pending;
        if (frame is null || !readerProved || observed is null || !ReferenceEquals(observed, frame) ||
            !ReferenceEquals(observed.Machine, machine) || observed.Width != 16 || readerPc != expectedRtPc ||
            word != frame.ReturnPc || hostShortcut || unknownAlias)
            throw new InvalidDataException("Missing/stale/foreign frame, unproved first reader, alias, or host return.");
        Pending = null;
    }

    // Generic invented fork: one call then join; branch alternatives are not a call sequence.
    internal static IReadOnlyList<int[]> Paths()
    {
        var graph = new Dictionary<int, int[]>
        {
            [0x1200] = [0x1230, 0x1250, 0x1270],
            [0x1230] = [0x1233],
            [0x1233] = [0x1280],
            [0x1250] = [0x1253],
            [0x1253] = [0x1280],
            [0x1270] = [0x1280],
            [0x1280] = []
        };
        var result = new List<int[]>();
        void Visit(int pc, List<int> path)
        {
            if (path.Count >= 16 || path.Contains(pc) || !graph.ContainsKey(pc))
                throw new InvalidDataException("Unknown/cyclic graph cannot become a completed caller sequence.");
            var next = new List<int>(path) { pc };
            if (graph[pc].Length == 0) result.Add(next.ToArray());
            else foreach (var edge in graph[pc]) Visit(edge, next);
        }
        Visit(0x1200, []); return result;
    }
}
