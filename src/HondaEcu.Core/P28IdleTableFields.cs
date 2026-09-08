namespace HondaEcu.Core;

/// <summary>Code-owned numeric mapping, not permission to edit an arbitrary image.</summary>
public static class P28IdleTableFields
{
    public static int Table(int table) => table switch { 0 => 0x68CB, 1 => 0x68E0, _ => throw new ArgumentOutOfRangeException(nameof(table)) };
    public static int AxisOffset(int table, int cell) => cell is >= 0 and < 7 ? Table(table) + 3 * cell : throw new ArgumentOutOfRangeException(nameof(cell));
    public static int ValueOffset(int table, int cell) => AxisOffset(table, cell) + 1;
    public static string FieldId(int table, int cell)
    {
        _ = AxisOffset(table, cell);
        return table == 0 ? $"context-21a0-table-cell-{cell}" : $"context-late-68e0-table-cell-{cell}";
    }
    public static string TableId(int table) => table switch { 0 => "base", 1 => "late", _ => throw new ArgumentOutOfRangeException(nameof(table)) };
}
