namespace HondaEcu.Core;

// A research-only journal guard for invented tests. No public operation/schema;
// no ability to seed CPU/RAM, schedule an IRQ, or infer an expected word from actual.
internal enum SoftwareWordLifetime { InitialHistory, NativeWritten, Held, PartialNativeWritten, NotRun }
internal sealed record SoftwareWordGeneration(int WriterPc, int EventIndex, int WriteOrder, ushort Value);
internal sealed record SoftwareWordAccess(int Pc, int EventIndex, int Order, int Address, int Width,
    bool Write, int Value, bool Host = false);
internal sealed record SoftwareWordConsumption(int ReaderPc, int RegisterAddress, int DivPc,
    SoftwareWordGeneration Generation);

internal sealed class SoftwareWordProvenance(int address)
{
    private readonly List<SoftwareWordGeneration> history = [];
    private int nextEvent;
    private bool terminal;
    internal SoftwareWordLifetime State { get; private set; } = SoftwareWordLifetime.InitialHistory;
    internal SoftwareWordGeneration? Current => history.LastOrDefault();
    internal IReadOnlyList<SoftwareWordGeneration> History => history.AsReadOnly();

    // Expected generations must be authored by an independent model, not this journal.
    // Transactional validation prevents malformed evidence from poisoning retained history.
    internal void CheckEvent(int eventIndex, SoftwareWordLifetime disposition,
        IReadOnlyList<SoftwareWordGeneration> expectedWrites, IReadOnlyList<SoftwareWordAccess> accesses,
        SoftwareWordConsumption? consumption = null, CancellationToken cancellationToken = default,
        DateTimeOffset? deadline = null)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (deadline is not null && DateTimeOffset.UtcNow >= deadline) throw new TimeoutException("Journal check deadline exceeded.");
        if (address < 0 || address > 65534 || (address & 1) != 0 || eventIndex != nextEvent)
            throw new InvalidDataException("Invalid storage or event order.");
        if (disposition == SoftwareWordLifetime.InitialHistory ||
            (terminal && disposition != SoftwareWordLifetime.NotRun) ||
            (disposition == SoftwareWordLifetime.NotRun && (accesses.Count != 0 || expectedWrites.Count != 0 || consumption is not null)))
            throw new InvalidDataException("Terminal events cannot execute or accept inputs.");
        var found = new List<SoftwareWordGeneration>();
        var candidate = Current;
        var phase = 0;
        var previousOrder = -1;
        foreach (var a in accesses)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (deadline is not null && DateTimeOffset.UtcNow >= deadline) throw new TimeoutException("Journal check deadline exceeded.");
            if (a.EventIndex != eventIndex || a.Order <= previousOrder || a.Pc < 0 || a.Pc > 65535 ||
                a.Address < 0 || a.Address + a.Width / 8 > 65536 || a.Width is not (8 or 16) ||
                a.Value < 0 || a.Value > (a.Width == 8 ? 255 : 65535))
                throw new InvalidDataException("Malformed access order/width/value.");
            previousOrder = a.Order;
            var overlap = a.Address < address + 2 && a.Address + a.Width / 8 > address;
            if (overlap)
            {
                if (a.Host || a.Address != address || a.Width != 16)
                    throw new InvalidDataException("Host or partial-byte software-word access.");
                if (a.Write)
                {
                    if (phase != 0) throw new InvalidDataException("Generation changed during consumption.");
                    candidate = new(a.Pc, eventIndex, a.Order, (ushort)a.Value);
                    found.Add(candidate);
                }
                else
                {
                    if (consumption is null || phase != 0 || a.Pc != consumption.ReaderPc || candidate is null ||
                        candidate != consumption.Generation || a.Value != candidate.Value)
                        throw new InvalidDataException("Missing or stale reader generation.");
                    phase = 1;
                }
            }
            else if (consumption is not null && a.Address < consumption.RegisterAddress + 2 &&
                a.Address + a.Width / 8 > consumption.RegisterAddress)
            {
                if (a.Host || a.Width != 16 || a.Address != consumption.RegisterAddress || candidate is null || a.Value != candidate.Value)
                    throw new InvalidDataException("Invalid native register transfer.");
                if (phase == 1 && a.Write && a.Pc == consumption.ReaderPc) phase = 2;
                else if (phase == 2 && !a.Write && a.Pc == consumption.DivPc) phase = 3;
                else throw new InvalidDataException("Missing, overwritten or reordered divisor transfer.");
            }
        }
        if (!found.SequenceEqual(expectedWrites) || (consumption is not null && phase != 3) ||
            (disposition == SoftwareWordLifetime.NativeWritten && found.Count == 0) ||
            (disposition == SoftwareWordLifetime.Held && (found.Count != 0 || candidate is null)) ||
            (disposition == SoftwareWordLifetime.PartialNativeWritten && (found.Count == 0 || consumption is not null)))
            throw new InvalidDataException("Independent writes/disposition/consumption mismatch.");
        cancellationToken.ThrowIfCancellationRequested();
        history.AddRange(found);
        State = disposition;
        terminal |= disposition is SoftwareWordLifetime.PartialNativeWritten or SoftwareWordLifetime.NotRun;
        nextEvent++;
    }
}
