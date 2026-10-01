namespace HondaEcu.Core;

// Invented storage-domain proof only. This is not an actual-ROM scenario or a scheduler admission.
internal sealed record P28CommonStorageGeneration(int EventIndex, int WriterPc, int Address, int Width, int Value, int WriteOrder);
internal sealed record P28CommonStorageRead(int EventIndex, int WriterPc, int ReaderPc, int Address, int Width, int Value, int Slot, int Pointer, int Scale);
internal sealed record P28CommonStorageProbe(IReadOnlyList<P28CommonStorageGeneration> Generations, IReadOnlyList<P28CommonStorageRead> Reads,
    IReadOnlyList<int[]> InterveningWrites, int LoopCount, int PointerStride, int Bank, int EntryPc, IReadOnlyList<int[]> Branches, int Result);
internal static class P28CommonResultStorageModel
{
    internal static P28CommonStorageProbe Build(int eventIndex, IReadOnlyList<int> ownWords)
    {
        if (eventIndex < 0 || ownWords.Count != 4 || ownWords.Any(w => w is < 0 or > 65535)) throw new ArgumentException("Four independent modeled words required.");
        var generations = ownWords.Select((v, i) => new P28CommonStorageGeneration(eventIndex, 0x40 + 3 * i, 0x300 + 2 * i, 16, v, i)).ToArray();
        var reads = ownWords.Select((v, i) => new P28CommonStorageRead(eventIndex, generations[i].WriterPc, 0x80, 0x300 + 2 * i, 16, v, i, 2 * i, 2)).ToArray();
        return new(generations, reads, [], 4, 2, 0x20, 0x70,
            Enumerable.Range(0, 4).Select(i => new[] { 0x88, i == 3 ? 0x90 : 0x80 }).ToArray(), ownWords.Sum() & 65535);
    }
    internal static void Validate(P28CommonStorageProbe own, P28CommonStorageProbe observed)
    {
        void Require(bool condition) { if (!condition) throw new InvalidDataException("Invented storage provenance differs; final equality is insufficient."); }
        Require(own.Generations.Count == 4 && observed.Generations.Count == 4 && own.Reads.Count == 4 && observed.Reads.Count == 4);
        Require(observed.InterveningWrites.Count == 0 && observed.LoopCount == 4 && observed.PointerStride == 2 && observed.Bank == 0x20 && observed.EntryPc == 0x70);
        Require(observed.Generations.SequenceEqual(own.Generations));
        for (var i = 0; i < 4; i++)
        {
            var generation = own.Generations[i]; var read = observed.Reads[i];
            Require(read == own.Reads[i] && read.EventIndex == generation.EventIndex && read.WriterPc == generation.WriterPc &&
                read.Address == generation.Address && read.Width == generation.Width && read.Value == generation.Value && read.Slot == i && read.Pointer == i * 2 && read.Scale == 2);
        }
        Require(observed.Branches.Count == 4 && own.Branches.Count == 4 &&
            observed.Branches.Select((b, i) => b.Length == 2 && own.Branches[i].Length == 2 && b.SequenceEqual(own.Branches[i])).All(equal => equal) && observed.Result == own.Result);
    }
}
