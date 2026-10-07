namespace HondaEcu.Core.Tests;

// Invented static witnesses only. No Cpu/Bus, wire inputs, runtime operation,
// journal adaptation or output-to-M2ah integration. An accepted static proof
// is never evidence of an actual initialized firmware machine.
internal enum BootstrapEdgeKind { Literal, PossibleAlias, ReturnSummary, PriorUnprovedReader, IrqTransition }
internal sealed record BootstrapEdge(int From, int To, BootstrapEdgeKind Kind = BootstrapEdgeKind.Literal);
internal sealed record BootstrapPath(int Entry, int Source, int Reader, IReadOnlyList<BootstrapEdge> Edges)
{
    private HashSet<int> Reach(int entry, int? avoided = null, bool reverse = false)
    {
        var seen = new HashSet<int>(); var queue = new Queue<int>(); queue.Enqueue(entry);
        while (queue.TryDequeue(out var node))
        {
            if (node == avoided || !seen.Add(node)) continue;
            if (seen.Count > 256) throw new InvalidDataException("Unbounded static graph.");
            foreach (var edge in Edges)
                if ((reverse ? edge.To : edge.From) == node)
                    queue.Enqueue(reverse ? edge.From : edge.To);
        }
        return seen;
    }

    internal void RequireContinuity()
    {
        var entered = Reach(Entry); var reachesReader = Reach(Reader, reverse: true);
        if (!entered.Contains(Source) || !entered.Contains(Reader) || Reach(Entry, Source).Contains(Reader))
            throw new InvalidDataException("Missing source, unreachable reader or initialization bypass.");
        if (Edges.Any(e => entered.Contains(e.From) && reachesReader.Contains(e.To) && e.Kind != BootstrapEdgeKind.Literal))
            throw new InvalidDataException("Unresolved alias, conditional return, circular bootstrap or IRQ transition.");
    }
}

internal sealed class BootstrapContinuityFixture(byte diagnosticValue = 0)
{
    internal const int Address = 0x219B;
    internal SoftwareBitProvenance Bits { get; } = new(Address, diagnosticValue);
    private readonly Dictionary<SoftwareBitOwner, int> roots = new(ReferenceEqualityComparer.Instance);
    internal int ActualRomExecutions => 0;
    internal bool CurrentRuntimeOwnerEstablished => false;

    internal void InitializationWord(int encodedAddress, ushort codeValue, SoftwareBitWrite write, int sourceNode)
    {
        var sources = Enumerable.Range(0, 16).Select(i => SoftwareBitSource.CodeConstant((codeValue & (1 << i)) != 0)).ToArray();
        Bits.WriteWord(encodedAddress, codeValue, sources, write);
        for (var bit = 0; bit < 8; bit++)
            if (Bits.Bit(bit).Owner is { } owner && ReferenceEquals(owner.Writer, write)) roots.Add(owner, sourceNode);
    }

    internal void ResetReference(byte numericValue, SoftwareBitWrite write) => Bits.WriteByte(Address, numericValue,
        Enumerable.Range(0, 8).Select(i => new SoftwareBitSource((numericValue & (1 << i)) != 0, SoftwareBitOrigin.ResetDependent)).ToArray(), write);

    internal void RequireStaticReader(int bit, SoftwareBitOwner? owner, BootstrapPath path)
    {
        path.RequireContinuity();
        var root = owner;
        while (root?.Source is not null) root = root.Source;
        if (root is null || !roots.TryGetValue(root, out var source) || source != path.Source)
            throw new InvalidDataException("Wrong source domain or unproved independent initialization.");
        Bits.RequireReader(path.Reader, bit, Bits.Bit(bit).Value, owner);
    }

    internal static (byte Value, bool Cf, bool Zf, bool Hc, bool Dd) OffObjectShiftSpecification(
        byte value, bool zf, bool hc, bool dd) => ((byte)(value << 1), (value & 0x80) != 0, zf, hc, dd);
}
