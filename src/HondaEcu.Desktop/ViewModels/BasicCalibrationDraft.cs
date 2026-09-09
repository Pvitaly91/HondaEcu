using System.ComponentModel;
using System.Globalization;
using HondaEcu.Core;

namespace HondaEcu.Desktop.ViewModels;

public sealed class BasicRawField : INotifyPropertyChanged, IDataErrorInfo
{
    private string _text;
    private readonly Action _changed;
    private readonly Func<bool> _editable;
    public BasicRawField(string id, int original, int? axis, Action changed, Func<bool> editable)
    { Id = id; Original = original; Axis = axis; _text = original.ToString(CultureInfo.InvariantCulture); _changed = changed; _editable = editable; }
    public string Id { get; }
    public int Original { get; }
    public int? Axis { get; }
    public string Text
    {
        get => _text;
        set { if (_text == value || !_editable()) return; _text = value; PropertyChanged?.Invoke(this, new(nameof(Text))); _changed(); }
    }
    public int Number() => int.TryParse(Text, NumberStyles.None, CultureInfo.InvariantCulture, out var n) && Text.All(char.IsAsciiDigit)
        ? n : throw new ArgumentException($"{Id}: введіть десяткове ціле raw; порожній/невалідний текст не є попереднім значенням.");
    public string Error => this[nameof(Text)];
    public string this[string columnName] { get { try { _ = Number(); return ""; } catch (ArgumentException e) { return e.Message; } } }
    public event PropertyChangedEventHandler? PropertyChanged;
}

public sealed class BasicDraftGroup : INotifyPropertyChanged
{
    private bool _included;
    private readonly Action _changed;
    private readonly Func<bool> _editable;
    public BasicDraftGroup(string id, string title, IEnumerable<(string Id, int Value, int? Axis)> fields, Action changed, Func<bool> editable)
    {
        Id = id; Title = title; _changed = changed; _editable = editable;
        Fields = fields.Select(f => new BasicRawField(f.Id, f.Value, f.Axis, changed, editable)).ToArray();
        ResetCommand = new(Reset, editable);
    }
    public string Id { get; }
    public string Title { get; }
    public IReadOnlyList<BasicRawField> Fields { get; }
    public bool Included { get => _included; set { if (_included == value || !_editable()) return; _included = value; PropertyChanged?.Invoke(this, new(nameof(Included))); _changed(); } }
    public RelayCommand ResetCommand { get; }
    public void Reset() { if (!_editable()) return; foreach (var f in Fields) f.Text = f.Original.ToString(CultureInfo.InvariantCulture); Included = false; }
    public event PropertyChangedEventHandler? PropertyChanged;
}

/// <summary>Text-only draft; no bytes, compensation, admission or publication authority.</summary>
public sealed class BasicCalibrationDraft : INotifyPropertyChanged
{
    private readonly Action _changed;
    private readonly Func<bool> _editable;
    private readonly int[] _vtecOriginal;
    private string _slot;
    public BasicCalibrationDraft(IReadOnlyList<int> vtec, IEnumerable<BasicDraftGroup> otherGroups, Action changed, Func<bool> editable)
    {
        _changed = changed; _editable = editable; _vtecOriginal = vtec.ToArray(); _slot = Slots[0].Id;
        Vtec = MakeVtec(); Groups = new[] { Vtec }.Concat(otherGroups).ToArray();
    }
    public IReadOnlyList<P28ThresholdSlot> Slots { get; } = P28ThresholdLogic.GetSlots();
    public string SelectedSlot
    {
        get => _slot;
        set
        {
            if (_slot == value || !_editable()) return;
            _ = P28ThresholdLogic.ResolveSlot(value);
            var included = Vtec.Included; _slot = value; Vtec = MakeVtec(); Vtec.Included = included;
            Groups = new[] { Vtec }.Concat(Groups.Skip(1)).ToArray();
            PropertyChanged?.Invoke(this, new("")); _changed();
        }
    }
    public string SlotExplanation { get { var s = P28ThresholdLogic.ResolveSlot(_slot); return $"context={s.Context}, pair={s.Pair}, prior={s.PriorState}. Не фізичні VTEC ON/OFF."; } }
    public BasicDraftGroup Vtec { get; private set; }
    public IReadOnlyList<BasicDraftGroup> Groups { get; private set; }
    private BasicDraftGroup MakeVtec() => new("vtec", "VTEC — один threshold code (raw)",
        [("threshold", _vtecOriginal[Slots.ToList().FindIndex(s => s.Id == _slot)], null)], _changed, _editable);
    public P28BasicCalibrationSettings Snapshot()
    {
        int[]? N(int i) => Groups[i].Included ? Groups[i].Fields.Select(f => f.Number()).ToArray() : null;
        var v = N(0); var f = N(1); var a = N(2); var b = N(3);
        // The existing parser remains the final shape/value-policy boundary.
        var settings = new P28BasicCalibrationSettings(v is null ? null : new(SelectedSlot, v[0]),
            f is null ? null : new(f[0], f[1]), a is null ? null : new(a[0], a[1]), b is null ? null : new(b[0], b[1]), N(4), N(5));
        return P28BasicCalibrationSettings.Parse(settings.ToJson());
    }
    public void Apply(P28BasicCalibrationSettings settings)
    {
        // Caller builds a detached draft after full parse/domain validation, then swaps it atomically.
        if (settings.Vtec is { } v) SelectedSlot = v.Slot;
        int[]?[] values = [settings.Vtec is { } s ? [s.RawValue] : null,
            settings.Limiter.Fixed is { } f ? [f.CutRaw, f.ResumeRaw] : null,
            settings.Limiter.Bank0 is { } a ? [a.BaseCutRaw, a.BaseResumeRaw] : null,
            settings.Limiter.Bank1 is { } b ? [b.BaseCutRaw, b.BaseResumeRaw] : null,
            settings.Idle.BaseTable?.ToArray(), settings.Idle.LateTable?.ToArray()];
        for (var i = 0; i < 6; i++)
        {
            Groups[i].Included = values[i] is not null;
            if (values[i] is { } row) for (var n = 0; n < row.Length; n++) Groups[i].Fields[n].Text = row[n].ToString(CultureInfo.InvariantCulture);
        }
    }
    public static BasicCalibrationDraft FromFields(IReadOnlyList<P28BasicCalibrationGroup> groups, Action changed, Func<bool> editable)
    {
        string[] titles = ["Fixed — raw period cut/resume", "Bank0 — raw bases cut/resume", "Bank1 — raw bases cut/resume", "Base idle — raw target period", "Late replacement — raw target period"];
        var others = groups.Skip(1).Select((g, i) => new BasicDraftGroup(g.Id, titles[i],
            g.Limiter is { } l ? l.FixedOperands.Select(f => (f.FieldId, f.OriginalWord, (int?)null))
                .Concat(l.AdaptiveWords.Select(w => (w.FieldId, w.OldWord, (int?)null))) : g.Idle!.Cells.Select(c => (c.FieldId, c.OldValue, (int?)c.Axis)), changed, editable));
        return new(groups[0].Vtec!.OriginalBytes.Select(b => (int)b).ToArray(), others, changed, editable);
    }
    public static BasicCalibrationDraft Demo(Action changed, Func<bool> editable)
    {
        int[] axes = [255, 210, 165, 120, 75, 30, 0];
        BasicDraftGroup Pair(string id, int a, int b) => new(id, id + " — raw", [("cut", a, null), ("resume", b, null)], changed, editable);
        BasicDraftGroup Table(string id, int start) => new(id, id + " — raw target period", Enumerable.Range(0, 7).Select(i => ($"cell {i}", start + i * 100, (int?)axes[i])), changed, editable);
        return new([20, 35, 50, 65, 80, 95, 110, 125], [Pair("fixed", 400, 440), Pair("bank0", 200, 230), Pair("bank1", 240, 280), Table("baseTable", 1000), Table("lateTable", 1200)], changed, editable);
    }
    public event PropertyChangedEventHandler? PropertyChanged;
}
