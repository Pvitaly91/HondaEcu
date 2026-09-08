namespace HondaEcu.Core;

public sealed record P28IdleScalarSource(string Id, int Offset, int Width, int RawValue, int Reader, string Role);
public sealed record P28IdleContextsInspection(int FormatVersion, RomHash ImageHash, int Size, bool InterpretationApplied,
    string Binding, IReadOnlyList<P28IdleCell> Cells, IReadOnlyList<P28IdleScalarSource> Scalars, IReadOnlyList<string> Scope)
{
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
}
public static class P28IdleContextsInspector
{
    internal static void TableGuard(RomImage image)
    {
        P28IdleInspector.TableGuard(image);
        if (P28LimiterInspector.Word(image.Span, 0x30A3) != 0x68E0 || P28LimiterInspector.Word(image.Span, 0x3077) != 0x68CB)
            throw new InvalidDataException("Unexpected contexts table pointer.");
        for (var i = 0; i < 6; i++) if (image.Span[0x68E0 + 3 * i] <= image.Span[0x68E0 + 3 * (i + 1)])
                throw new InvalidDataException("Alternative target axis must descend.");
        if (image.Span[0x68E0] != 255 || image.Span[0x68F2] != 0) throw new InvalidDataException("Alternative table byte domain missing.");
    }
    public static P28IdleContextsInspection Inspect(RomImage image, RomProfile profile, P28ExactBaselineBinding? binding, bool confirmed)
    {
        var old = P28IdleInspector.Inspect(image, profile, binding, confirmed);
        if (!old.InterpretationApplied) return new(1, image.Hash, image.Size, false, old.Binding, [], [], ["General image data only; exact binding and confirmation required."]);
        TableGuard(image); var cells = new List<P28IdleCell>();
        foreach (var table in new[] { 0, 1 }) for (var i = 0; i < 7; i++)
            {
                var a = P28IdleTableFields.AxisOffset(table, i);
                cells.Add(new(P28IdleTableFields.FieldId(table, i), a, image.Span[a], P28IdleTableFields.ValueOffset(table, i),
                    P28LimiterInspector.Word(image.Span, a + 1), table == 0 ? "Base lookup only when low-domain guards permit; may be replaced by late lookup" : "Late lookup when scripted 021A.0 is clear; rawD9 0..255"));
            }
        var scalars = new List<P28IdleScalarSource>();
        foreach (var a in new[] { 0x2FE3, 0x7D9C, 0x300E, 0x3055, 0x3065 })
            scalars.Add(new($"immediate-{a - 1:x4}", a, 16, P28LimiterInspector.Word(image.Span, a), a - 1, "Unsigned little-endian instruction operand; candidate base target, not program-data read or final-contribution proof"));
        foreach (var a in new[] { 0x2FE7, 0x7DA0, 0x3012, 0x3059, 0x3069 })
            scalars.Add(new($"component-peak-{a - 2:x4}", a, 16, P28LimiterInspector.Word(image.Span, a), a - 2, "Separate 027A peak; never added to target inside boundary"));
        return new(1, image.Hash, image.Size, true, old.Binding, cells.AsReadOnly(), scalars.AsReadOnly(),
            ["Independent M1r contexts contract; old inspect/target-check remain M1q.",
             "Producer 2FD1..30AB, hooks 7D8A..7DA5 and helper 5894..58D3; stop before30AB. Consumer09DC..09F4 plus negate59A6..59AD.",
             "Seven unsigned packed byte-axis/u16LE records in each table; same native helper with odd/overlapping word reads and integer floor magnitude.",
             "Order: caller hook, low-domain/history checks, lookup or immediate candidate, separate027A, then late021A.0-clear alternative lookup, then final025C.",
             "First-table axis40 is a component boundary and may participate in base lookup; node0 participates as a lower knot for reachable low lookup, but producer rawD9<22 bypasses base lookup.",
             "Selectors are masked scripted upstream inputs, not native mode transitions. Counter/correction history seed once; included producer may set counters; no decrement service or time inference.",
             "Every completed path stores a fresh target; no retained/hold outcome found here. 027A persists separately and is not an additive correction of025C.",
             "Physical reachability of software snapshots unknown. Regulator/PWM, scheduler, capture/G, physical RPM, GUI and hardware excluded. No writable authority is added."]);
    }
}
