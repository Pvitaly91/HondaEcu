namespace HondaEcu.Core;

public sealed record P28IgnitionAxisContract(string Id, int Origin, int Count, int IntervalCount,
    string ElementEncoding, string Direction, string TerminalRule);
public sealed record P28IgnitionMapContractRow(string Id, int Origin, int EndInclusive, int Rows, int Columns,
    string CellEncoding, string StorageOrder, string RpmAxisId, string LoadAxisId);

/// <summary>Revision-bound read-only ignition-map layout. It grants no editing, export, checksum, or flash capability.</summary>
public static class P28IgnitionMapContract
{
    public const int Rows = 20, Columns = 10, CellCount = Rows * Columns;
    public const int Map0Origin = 0x72E4, Map1Origin = 0x73AC;
    public const int LoadAxisOrigin = 0x7000, Map0RpmAxisOrigin = 0x7014, Map1RpmAxisOrigin = 0x7028;
    public const int SelectorAddress = 0x227, SelectorMask = 0x20;

    public static IReadOnlyList<P28IgnitionAxisContract> Axes { get; } = Array.AsReadOnly(new[]
    {
        new P28IgnitionAxisContract("load", LoadAxisOrigin, 10, 9, "UnsignedByteRaw", "Ascending",
            "Final zero byte denotes the 256 endpoint after byte subtraction; it is not an ordinary input knot."),
        new P28IgnitionAxisContract("ignition_map_0_rpm", Map0RpmAxisOrigin, 20, 19, "UnsignedByteRaw", "Ascending",
            "Final zero byte denotes the 256 endpoint after byte subtraction; it is not an ordinary input knot."),
        new P28IgnitionAxisContract("ignition_map_1_rpm", Map1RpmAxisOrigin, 20, 19, "UnsignedByteRaw", "Ascending",
            "Final zero byte denotes the 256 endpoint after byte subtraction; it is not an ordinary input knot."),
    });

    public static IReadOnlyList<P28IgnitionMapContractRow> Maps { get; } = Array.AsReadOnly(new[]
    {
        new P28IgnitionMapContractRow("ignition_map_0", Map0Origin, Map0Origin + CellCount - 1, Rows, Columns,
            "UnsignedByteRaw", "RowMajor", "ignition_map_0_rpm", "load"),
        new P28IgnitionMapContractRow("ignition_map_1", Map1Origin, Map1Origin + CellCount - 1, Rows, Columns,
            "UnsignedByteRaw", "RowMajor", "ignition_map_1_rpm", "load"),
    });

    public static P28IgnitionMapContractRow Map(string id) => Maps.SingleOrDefault(map => map.Id == id)
        ?? throw new ArgumentException("Map ID must be ignition_map_0 or ignition_map_1.", nameof(id));

    public static int CellOffset(string mapId, int row, int column)
    {
        var map = Map(mapId);
        if (row is < 0 or >= Rows || column is < 0 or >= Columns)
            throw new ArgumentOutOfRangeException(nameof(row), "Ignition-map coordinates must be inside the established 20x10 grid.");
        return map.Origin + row * Columns + column;
    }
}
