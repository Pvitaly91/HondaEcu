namespace HondaEcu.Core;

public sealed record P28FuelAxisContract(string Id, int Origin, int Count, int IntervalCount, string ElementEncoding, string Direction, string TerminalRule);
public sealed record P28FuelMapContractRow(string Id, int Origin, int EndInclusive, int MetadataOrigin, int MetadataEndInclusive,
    int Rows, int Columns, string CellEncoding, string StorageOrder, string RpmAxisId, string LoadAxisId);

/// <summary>Revision-bound read-only layout. It grants no editor, export, checksum, or flash capability.</summary>
public static class P28FuelMapContract
{
    public const int Rows = 20, Columns = 10, CellCount = Rows * Columns;
    public const int Map0Origin = 0x7050, Map1Origin = 0x7122;
    public const int LoadAxisOrigin = 0x7000, Map0RpmAxisOrigin = 0x7014, Map1RpmAxisOrigin = 0x7028;
    public const int SelectorAddress = 0x127, SelectorMask = 0x02;

    public static IReadOnlyList<P28FuelAxisContract> Axes { get; } = Array.AsReadOnly(new[]
    {
        new P28FuelAxisContract("load", LoadAxisOrigin, 10, 9, "UnsignedByteRaw", "Ascending", "Final zero byte denotes the 256 endpoint after byte subtraction."),
        new P28FuelAxisContract("map_0_rpm", Map0RpmAxisOrigin, 20, 19, "UnsignedByteRaw", "Ascending", "Final zero byte denotes the 256 endpoint after byte subtraction."),
        new P28FuelAxisContract("map_1_rpm", Map1RpmAxisOrigin, 20, 19, "UnsignedByteRaw", "Ascending", "Final zero byte denotes the 256 endpoint after byte subtraction."),
    });

    public static IReadOnlyList<P28FuelMapContractRow> Maps { get; } = Array.AsReadOnly(new[]
    {
        new P28FuelMapContractRow("map_0", Map0Origin, Map0Origin + CellCount - 1, Map0Origin + CellCount, Map0Origin + CellCount + Columns - 1,
            Rows, Columns, "UnsignedByte", "RowMajor", "map_0_rpm", "load"),
        new P28FuelMapContractRow("map_1", Map1Origin, Map1Origin + CellCount - 1, Map1Origin + CellCount, Map1Origin + CellCount + Columns - 1,
            Rows, Columns, "UnsignedByte", "RowMajor", "map_1_rpm", "load"),
    });

    public static P28FuelMapContractRow Map(string id) => Maps.SingleOrDefault(map => map.Id == id)
        ?? throw new ArgumentException("Map ID must be map_0 or map_1.", nameof(id));

    public static int CellOffset(string mapId, int row, int column)
    {
        var map = Map(mapId);
        if (row is < 0 or >= Rows || column is < 0 or >= Columns)
            throw new ArgumentOutOfRangeException(nameof(row), "Fuel-map coordinates must be inside the established 20x10 grid.");
        return map.Origin + row * Columns + column;
    }

    public static int MetadataOffset(string mapId, int column)
    {
        var map = Map(mapId);
        if (column is < 0 or >= Columns) throw new ArgumentOutOfRangeException(nameof(column));
        return map.MetadataOrigin + column;
    }
}
