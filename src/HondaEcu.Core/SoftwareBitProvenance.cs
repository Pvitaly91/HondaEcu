namespace HondaEcu.Core;

// Independent research model only. Not a CPU/RAM writer, wire contract, operation,
// journal-to-expected adapter, or permission to execute any firmware reader.
internal enum SoftwareBitOrigin
{
    InitialDiagnosticScratch, NativeBitWritten, NativeWholeByteWritten, NativeWholeWordWritten,
    InheritedThroughRmw, ResetDependent, TimerDependent, IrqDependent, PeripheralDependent,
    TechnicalSnapshot, UnknownIndirectAlias, NotEstablished
}

internal sealed record SoftwareBitWrite(int Pc, int EventIndex, int GlobalWriteOrder);
internal sealed record SoftwareBitOwner(object Machine, int Address, int Bit, SoftwareBitWrite Writer,
    bool Value, SoftwareBitOrigin Origin, SoftwareBitOwner? Source = null);
internal sealed record SoftwareBitState(bool Value, SoftwareBitOrigin Origin, SoftwareBitOwner? Owner);
internal sealed record SoftwareBitSource(bool Value, SoftwareBitOrigin Origin, SoftwareBitOwner? Owner = null)
{
    internal static SoftwareBitSource CodeConstant(bool value) => new(value, SoftwareBitOrigin.NativeBitWritten);
    internal static SoftwareBitSource Unknown(bool value) => new(value, SoftwareBitOrigin.NotEstablished);
}

internal sealed class SoftwareBitProvenance
{
    private readonly object machine = new();
    private readonly HashSet<SoftwareBitOwner> issued = new(ReferenceEqualityComparer.Instance);
    private SoftwareBitState[] bits;
    private int lastEvent = -1;
    private int lastOrder = -1;
    internal int Address { get; }
    internal int StorageGeneration { get; private set; }
    internal SoftwareBitState Bit(int bit) => bits[CheckedBit(bit)];

    internal SoftwareBitProvenance(int address, byte diagnosticScratch)
    {
        if (address is < 0 or > 65535) throw new InvalidDataException("Invalid tracked byte.");
        Address = address;
        bits = Enumerable.Range(0, 8).Select(i => new SoftwareBitState((diagnosticScratch & (1 << i)) != 0,
            SoftwareBitOrigin.InitialDiagnosticScratch, null)).ToArray();
    }

    private static int CheckedBit(int bit) => bit is >= 0 and < 8 ? bit : throw new InvalidDataException("Invalid bit.");
    private void Validate(SoftwareBitWrite write)
    {
        if (write.Pc is < 0 or > 65535 || write.EventIndex < 0 || write.EventIndex < lastEvent ||
            write.GlobalWriteOrder < 0 || write.GlobalWriteOrder <= lastOrder)
            throw new InvalidDataException("Invalid/reset native chronology.");
    }
    private void Advance(SoftwareBitWrite write) { lastEvent = write.EventIndex; lastOrder = write.GlobalWriteOrder; }
    private bool Runtime(SoftwareBitOwner? owner) => owner is not null && ReferenceEquals(owner.Machine, machine) &&
        issued.Contains(owner) && owner.Origin is SoftwareBitOrigin.NativeBitWritten or
            SoftwareBitOrigin.NativeWholeByteWritten or SoftwareBitOrigin.NativeWholeWordWritten;
    private SoftwareBitOwner Issue(int bit, bool value, SoftwareBitOrigin origin, SoftwareBitWrite write, SoftwareBitOwner? source = null)
    {
        var owner = new SoftwareBitOwner(machine, Address, bit, write, value, origin, source);
        issued.Add(owner); return owner;
    }

    // SB/RB select one semantic bit even when the storage implementation writes a byte.
    internal void WriteBit(int bit, bool value, SoftwareBitWrite write)
    {
        bit = CheckedBit(bit); Validate(write);
        var next = bits.Select(b => b with { Origin = SoftwareBitOrigin.InheritedThroughRmw }).ToArray();
        next[bit] = new(value, SoftwareBitOrigin.NativeBitWritten, Issue(bit, value, SoftwareBitOrigin.NativeBitWritten, write));
        bits = next; StorageGeneration++; Advance(write);
    }

    internal SoftwareBitSource RetainedSource(int bit)
    {
        var b = Bit(bit);
        return new(b.Value, Runtime(b.Owner) ? b.Owner!.Origin : b.Origin, b.Owner);
    }

    private SoftwareBitState[] Whole(byte value, IReadOnlyList<SoftwareBitSource> sources,
        SoftwareBitOrigin origin, SoftwareBitWrite write)
    {
        if (sources.Count != 8 || sources.Any(s => s is null)) throw new InvalidDataException("Eight independent source bits required.");
        for (var i = 0; i < 8; i++)
        {
            var s = sources[i];
            if (s.Value != ((value & (1 << i)) != 0) || (s.Owner is not null &&
                (!Runtime(s.Owner) || s.Owner.Value != s.Value)))
                throw new InvalidDataException("Wrong value, forged/foreign source, or non-runtime source identity.");
        }
        return sources.Select((s, i) =>
        {
            // A numeric byte does not establish source ownership. Code constants are
            // independently model-authored, never supplied by an actual Rust journal.
            var owned = Runtime(s.Owner) || (s.Owner is null && s.Origin == SoftwareBitOrigin.NativeBitWritten);
            return new SoftwareBitState(s.Value, owned ? origin : s.Origin,
                owned ? Issue(i, s.Value, origin, write, s.Owner) : null);
        }).ToArray();
    }

    internal void WriteByte(int address, byte value, IReadOnlyList<SoftwareBitSource> sources, SoftwareBitWrite write)
    {
        Validate(write);
        if (address is < 0 or > 65535) throw new InvalidDataException("Invalid byte access.");
        if (address == Address) { bits = Whole(value, sources, SoftwareBitOrigin.NativeWholeByteWritten, write); StorageGeneration++; }
        Advance(write);
    }

    internal void WriteWord(int encodedAddress, ushort value, IReadOnlyList<SoftwareBitSource> sources, SoftwareBitWrite write)
    {
        Validate(write);
        if (encodedAddress is < 0 or > 65535 || sources.Count != 16 || sources.Any(s => s is null)) throw new InvalidDataException("Invalid word/source extent.");
        for (var i = 0; i < 16; i++)
        {
            var source = sources[i];
            if (source.Value != ((value & (1 << i)) != 0) || (source.Owner is not null &&
                (!Runtime(source.Owner) || source.Owner.Value != source.Value)))
                throw new InvalidDataException("Malformed word source provenance.");
        }
        var aligned = encodedAddress & ~1; // Architectural data word boundary, not an odd two-byte store.
        if (Address == aligned || Address == aligned + 1)
        {
            var offset = (Address - aligned) * 8;
            bits = Whole((byte)(value >> offset), sources.Skip(offset).Take(8).ToArray(), SoftwareBitOrigin.NativeWholeWordWritten, write);
            StorageGeneration++;
        }
        Advance(write);
    }

    internal void ShiftLeft(SoftwareBitWrite write)
    {
        var sources = new[] { SoftwareBitSource.CodeConstant(false) }
            .Concat(Enumerable.Range(0, 7).Select(RetainedSource)).ToArray();
        var value = (byte)(Enumerable.Range(0, 8).Sum(i => bits[i].Value ? 1 << i : 0) << 1);
        WriteByte(Address, value, sources, write);
    }

    internal void UnknownAlias(SoftwareBitWrite possibleWrite)
    {
        Validate(possibleWrite);
        // A possible write invalidates proof; it is not a proven storage generation/value.
        bits = bits.Select(b => b with { Origin = SoftwareBitOrigin.UnknownIndirectAlias, Owner = null }).ToArray();
        Advance(possibleWrite);
    }

    internal void RequireReader(int readerPc, int bit, bool actualValue, SoftwareBitOwner? expected)
    {
        var state = Bit(bit);
        if (readerPc is < 0 or > 65535 || !Runtime(state.Owner) || expected is null ||
            !ReferenceEquals(state.Owner, expected) || expected.Address != Address || expected.Bit != bit ||
            state.Value != actualValue || expected.Value != actualValue)
            throw new InvalidDataException("Unestablished, stale, wrong-machine, wrong-bit or numerically coincident reader provenance.");
    }
}
