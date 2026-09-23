using System.ComponentModel;
using System.Globalization;
using System.Windows.Media;
using HondaEcu.Core;

namespace HondaEcu.Desktop.ViewModels;

public enum MapDisplayMode { Original, Requested, Delta }
internal sealed record UnifiedCellRawState(string Text, bool Explicit);
internal sealed record UnifiedMapRawState(bool Included, UnifiedCellRawState[] Cells);

public sealed class UnifiedMapCell : INotifyPropertyChanged, IDataErrorInfo
{
    private readonly UnifiedMapDraft _owner;
    private string _text;
    private bool _explicit;

    internal UnifiedMapCell(UnifiedMapDraft owner, int row, int column, int offset, byte original)
    {
        _owner = owner; Row = row; Column = column; Offset = offset; Original = original;
        _text = original.ToString(CultureInfo.InvariantCulture);
    }

    public int Row { get; }
    public int Column { get; }
    public int Offset { get; }
    public string OffsetHex => $"0x{Offset:X4}";
    public byte Original { get; }
    public bool Explicit => _explicit;
    public string Text { get => _text; set => _owner.SetCell(this, value); }
    public int Requested => Parse(Text);
    public int Delta => Requested - Original;
    public bool ByteChanged => TryParse(Text, out var value) && value != Original;
    public string Detail => $"row {Row}, column {Column}; {OffsetHex}; original {Original}; requested {Text}; delta {(TryParse(Text, out var value) ? (value - Original).ToString(CultureInfo.InvariantCulture) : "invalid")}; explicit={Explicit}";
    public Brush HeatBrush
    {
        get
        {
            var raw = _owner.DisplayMode == MapDisplayMode.Original ? Original : TryParse(Text, out var value) ? value : (int)Original;
            if (_owner.DisplayMode == MapDisplayMode.Delta)
            {
                if (!TryParse(Text, out value)) return Brushes.LightPink;
                var delta = value - Original;
                if (delta == 0) return Brushes.WhiteSmoke;
                var channel = (byte)(255 - Math.Min(120, Math.Abs(delta) * 120 / 255));
                return new SolidColorBrush(delta > 0 ? Color.FromRgb(255, channel, channel) : Color.FromRgb(channel, channel, 255));
            }
            return new SolidColorBrush(Color.FromRgb((byte)(245 - raw * 100 / 255), (byte)(248 - raw * 75 / 255), 255));
        }
    }
    public string Error => this[nameof(Text)];
    public string this[string columnName] => TryParse(Text, out _) ? "" : $"row {Row}, column {Column}: raw u8 має бути десятковим цілим 0..255.";
    internal static bool TryParse(string text, out int value) =>
        int.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out value) &&
        text.Length > 0 && text.All(char.IsAsciiDigit) && value is >= 0 and <= 255;
    internal static int Parse(string text) => TryParse(text, out var value) ? value :
        throw new ArgumentException("Порожній або невалідний raw u8; попереднє число не використовується.");
    internal void Assign(string text, bool explicitRequest)
    {
        _text = text; _explicit = explicitRequest;
        PropertyChanged?.Invoke(this, new(""));
    }
    internal void Repaint() => PropertyChanged?.Invoke(this, new(nameof(HeatBrush)));
    public event PropertyChangedEventHandler? PropertyChanged;
}

public sealed class UnifiedMapRow
{
    internal UnifiedMapRow(int index, string axis, IReadOnlyList<UnifiedMapCell> cells)
    { Index = index; Axis = axis; Cells = cells; }
    public int Index { get; }
    public string Axis { get; }
    public IReadOnlyList<UnifiedMapCell> Cells { get; }
}

public sealed class UnifiedMapDraft : INotifyPropertyChanged
{
    private const int HistoryLimit = 100;
    private readonly Action _changed;
    private readonly Func<bool> _editable;
    private readonly Stack<MapSnapshot> _undo = new();
    private readonly Stack<MapSnapshot> _redo = new();
    private bool _included;
    private MapDisplayMode _displayMode;
    private bool _restoring;
    private sealed record CellSnapshot(string Text, bool Explicit);
    private sealed record MapSnapshot(bool Included, CellSnapshot[] Cells);

    public UnifiedMapDraft(string id, RomImage image, Action changed, Func<bool> editable)
    {
        Id = id; _changed = changed; _editable = editable;
        IsFuel = id.StartsWith("map_", StringComparison.Ordinal);
        var bytes = image.ToArray();
        var loadOrigin = IsFuel ? P28FuelMapContract.LoadAxisOrigin : P28IgnitionMapContract.LoadAxisOrigin;
        var rpmOrigin = id.EndsWith("_0", StringComparison.Ordinal) ? P28FuelMapContract.Map0RpmAxisOrigin : P28FuelMapContract.Map1RpmAxisOrigin;
        LoadAxes = Enumerable.Range(0, 10).Select(i => Axis(bytes[loadOrigin + i], i == 9)).ToArray();
        Multipliers = IsFuel ? Enumerable.Range(0, 10).Select(i => (int)bytes[P28FuelMapContract.MetadataOffset(id, i)]).ToArray() : [];
        Cells = Enumerable.Range(0, 20).SelectMany(row => Enumerable.Range(0, 10).Select(column =>
        {
            var offset = IsFuel ? P28FuelMapContract.CellOffset(id, row, column) : P28IgnitionMapContract.CellOffset(id, row, column);
            return new UnifiedMapCell(this, row, column, offset, bytes[offset]);
        })).ToArray();
        Rows = Enumerable.Range(0, 20).Select(row => new UnifiedMapRow(row, Axis(bytes[rpmOrigin + row], row == 19),
            Array.AsReadOnly(Cells.Skip(row * 10).Take(10).ToArray()))).ToArray();
    }
    private static string Axis(byte raw, bool terminal) => terminal && raw == 0 ? "256 — кінцева межа; збережений byte 0" : raw.ToString(CultureInfo.InvariantCulture);
    public string Id { get; }
    public bool IsFuel { get; }
    public IReadOnlyList<string> LoadAxes { get; }
    public IReadOnlyList<int> Multipliers { get; }
    public IReadOnlyList<UnifiedMapCell> Cells { get; }
    public IReadOnlyList<UnifiedMapRow> Rows { get; }
    public bool Included { get => _included; set { if (_included == value || !_editable()) return; Remember(); _included = value; Raise(); } }
    public MapDisplayMode DisplayMode { get => _displayMode; set { if (_displayMode == value) return; _displayMode = value; foreach (var cell in Cells) cell.Repaint(); PropertyChanged?.Invoke(this, new(nameof(DisplayMode))); } }
    public bool CanUndo => _undo.Count != 0;
    public bool CanRedo => _redo.Count != 0;
    public UnifiedMapCell Cell(int row, int column) => Cells[row * 10 + column];
    private MapSnapshot State() => new(_included, Cells.Select(cell => new CellSnapshot(cell.Text, cell.Explicit)).ToArray());
    private void Restore(MapSnapshot state)
    {
        _restoring = true;
        try { _included = state.Included; for (var i = 0; i < Cells.Count; i++) Cells[i].Assign(state.Cells[i].Text, state.Cells[i].Explicit); }
        finally { _restoring = false; }
        Raise();
    }
    private void Remember()
    {
        if (_restoring) return;
        _undo.Push(State());
        if (_undo.Count > HistoryLimit)
        {
            var newest = _undo.ToArray().Take(HistoryLimit).Reverse().ToArray();
            _undo.Clear(); foreach (var item in newest) _undo.Push(item);
        }
        _redo.Clear();
    }
    private void Raise() { PropertyChanged?.Invoke(this, new("")); _changed(); }
    internal void SetCell(UnifiedMapCell cell, string value)
    {
        if (!_editable() || cell.Text == value) return;
        Remember(); cell.Assign(value, true); Raise();
    }
    public void Undo()
    {
        if (!_editable() || !CanUndo) return;
        _redo.Push(State()); Restore(_undo.Pop());
    }
    public void Redo()
    {
        if (!_editable() || !CanRedo) return;
        _undo.Push(State()); Restore(_redo.Pop());
    }
    public void ApplyRect(int row, int column, string tsv)
    {
        if (!_editable()) throw new InvalidOperationException("Map draft is read-only.");
        var lines = tsv.TrimEnd('\r', '\n').Split('\n');
        if (lines.Length == 0 || lines.Length > 20 || row < 0 || row + lines.Length > 20) throw new ArgumentException("TSV виходить за 20 рядків.");
        var values = lines.Select(line => line.TrimEnd('\r').Split('\t')).ToArray();
        var width = values[0].Length;
        if (width == 0 || values.Any(items => items.Length != width) || column < 0 || column + width > 10)
            throw new ArgumentException("TSV має бути прямокутним і вміщуватися в 10 стовпців.");
        var parsed = values.SelectMany(items => items.Select(UnifiedMapCell.Parse)).ToArray();
        Remember();
        for (var r = 0; r < values.Length; r++) for (var c = 0; c < width; c++)
                Cell(row + r, column + c).Assign(parsed[r * width + c].ToString(CultureInfo.InvariantCulture), true);
        Raise();
    }
    public void Fill(int top, int left, int bottom, int right, string raw)
    {
        if (!_editable()) throw new InvalidOperationException("Map draft is read-only.");
        var value = UnifiedMapCell.Parse(raw);
        CheckRect(top, left, bottom, right); Remember();
        for (var row = top; row <= bottom; row++) for (var col = left; col <= right; col++)
                Cell(row, col).Assign(value.ToString(CultureInfo.InvariantCulture), true);
        Raise();
    }
    public void Reset(int top = 0, int left = 0, int bottom = 19, int right = 9)
    {
        if (!_editable()) throw new InvalidOperationException("Map draft is read-only.");
        CheckRect(top, left, bottom, right); Remember();
        for (var row = top; row <= bottom; row++) for (var col = left; col <= right; col++)
            { var cell = Cell(row, col); cell.Assign(cell.Original.ToString(CultureInfo.InvariantCulture), false); }
        Raise();
    }
    private static void CheckRect(int top, int left, int bottom, int right)
    {
        if (top < 0 || bottom >= 20 || left < 0 || right >= 10 || bottom < top || right < left)
            throw new ArgumentOutOfRangeException(nameof(top), "Selection must fit 20×10.");
    }
    public IReadOnlyList<(int Row, int Column, int Value)>? Snapshot()
    {
        if (!Included) return null;
        // Hidden invalid text is still validated when its map is included.
        foreach (var cell in Cells) _ = cell.Requested;
        return Cells.Where(cell => cell.Explicit).Select(cell => (cell.Row, cell.Column, cell.Requested)).ToArray();
    }
    internal UnifiedMapRawState CaptureRaw() => new(_included,
        Cells.Select(cell => new UnifiedCellRawState(cell.Text, cell.Explicit)).ToArray());
    internal void RestoreRaw(UnifiedMapRawState state)
    {
        _included = state.Included;
        for (var i = 0; i < Cells.Count; i++) Cells[i].Assign(state.Cells[i].Text, state.Cells[i].Explicit);
        _undo.Clear(); _redo.Clear(); PropertyChanged?.Invoke(this, new(""));
    }
    public void Apply(IReadOnlyList<(int Row, int Column, int Value)>? values, bool notify = true)
    {
        // The caller parses the entire settings document first. This method is for detached drafts.
        _included = values is not null;
        foreach (var cell in Cells) cell.Assign(cell.Original.ToString(CultureInfo.InvariantCulture), false);
        if (values is not null) foreach (var (row, column, value) in values)
                Cell(row, column).Assign(value.ToString(CultureInfo.InvariantCulture), true);
        _undo.Clear(); _redo.Clear(); if (notify) Raise();
    }
    public event PropertyChangedEventHandler? PropertyChanged;
}
