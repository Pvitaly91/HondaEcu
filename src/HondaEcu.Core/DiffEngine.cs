using System.Text.Json;

namespace HondaEcu.Core;

public sealed record DiffRange(int Offset, int Length, string OldHex, string NewHex)
{
    public int EndOffset => checked(Offset + Length - 1);
}

public sealed record PageDiffStatistic(int Page, int Offset, int ChangedByteCount);

public sealed record DiffReport(
    RomHash BaseHash,
    RomHash ModifiedHash,
    int BaseSize,
    int ModifiedSize,
    int DifferentByteCount,
    int? FirstDifferentOffset,
    int? LastDifferentOffset,
    IReadOnlyList<DiffRange> Ranges,
    IReadOnlyList<PageDiffStatistic> Pages,
    bool RangesTruncated)
{
    public string ToJson(bool indented = true) =>
        JsonSerializer.Serialize(this, JsonDefaults.Create(indented));
}

public static class DiffEngine
{
    public const int DefaultPageSize = 0x100;

    public static DiffReport Compare(RomImage baseline, RomImage modified, int? maxRanges = null, int pageSize = DefaultPageSize)
    {
        ArgumentNullException.ThrowIfNull(baseline);
        ArgumentNullException.ThrowIfNull(modified);
        if (maxRanges is < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(maxRanges));
        }

        if (pageSize <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(pageSize));
        }

        var oldBytes = baseline.Span;
        var newBytes = modified.Span;
        var length = Math.Max(oldBytes.Length, newBytes.Length);
        var completeRanges = new List<DiffRange>();
        var pageCounts = new SortedDictionary<int, int>();
        int? first = null;
        int? last = null;
        var changed = 0;
        var index = 0;
        while (index < length)
        {
            if (EqualAt(oldBytes, newBytes, index))
            {
                index++;
                continue;
            }

            var start = index;
            while (index < length && !EqualAt(oldBytes, newBytes, index))
            {
                first ??= index;
                last = index;
                changed++;
                var page = index / pageSize;
                pageCounts[page] = pageCounts.GetValueOrDefault(page) + 1;
                index++;
            }

            var rangeLength = index - start;
            var oldAvailable = Math.Max(0, Math.Min(rangeLength, oldBytes.Length - start));
            var newAvailable = Math.Max(0, Math.Min(rangeLength, newBytes.Length - start));
            completeRanges.Add(new DiffRange(
                start,
                rangeLength,
                oldAvailable == 0 ? string.Empty : HexUtilities.Format(oldBytes.Slice(start, oldAvailable)),
                newAvailable == 0 ? string.Empty : HexUtilities.Format(newBytes.Slice(start, newAvailable))));
        }

        var take = maxRanges ?? completeRanges.Count;
        var ranges = completeRanges.Take(take).ToArray();
        var pages = pageCounts.Select(pair => new PageDiffStatistic(pair.Key, pair.Key * pageSize, pair.Value)).ToArray();
        return new DiffReport(baseline.Hash, modified.Hash, baseline.Size, modified.Size, changed, first, last,
            ranges, pages, completeRanges.Count > ranges.Length);
    }

    public static DiffReport CompareFiles(string baselinePath, string modifiedPath, int? maxRanges = null, int pageSize = DefaultPageSize) =>
        Compare(RomImage.Load(baselinePath), RomImage.Load(modifiedPath), maxRanges, pageSize);

    private static bool EqualAt(ReadOnlySpan<byte> baseline, ReadOnlySpan<byte> modified, int offset) =>
        offset < baseline.Length && offset < modified.Length && baseline[offset] == modified[offset];
}
