namespace HondaEcu.Core;

public sealed record P28FuelAxisInspection(string Id, int Origin, int Count, int IntervalCount, string ElementEncoding,
    string Direction, string TerminalRule, IReadOnlyList<int> RawValues);
public sealed record P28FuelMapInspection(string Id, int Origin, int EndInclusive, int MetadataOrigin, int MetadataEndInclusive,
    int Rows, int Columns, string CellEncoding, string StorageOrder, string AddressFormula, string RpmAxisId, string LoadAxisId,
    IReadOnlyList<IReadOnlyList<int>> Cells, IReadOnlyList<int> ColumnMultipliers);
public sealed record P28FuelMapsInspection(int FormatVersion, RomHash ImageHash, int Size, bool InterpretationApplied, string Binding,
    IReadOnlyList<P28FuelAxisInspection> Axes, IReadOnlyList<P28FuelMapInspection> Maps, IReadOnlyList<string> Selection,
    IReadOnlyList<string> LookupBoundary, IReadOnlyList<string> ConsumerBoundary, IReadOnlyList<string> Unknowns)
{
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1InteractiveGuiAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None";
}

public static class P28FuelMapInspector
{
    internal static void LayoutGuard(RomImage image)
    {
        image.ValidateExactSize(32768);
        var b = image.Span;
        static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
        Require(b[0x0A0C] == 0x60 && P28LimiterInspector.Word(b, 0x0A0D) == P28FuelMapContract.Map0RpmAxisOrigin, "map_0 RPM-axis pointer construction differs.");
        Require(b[0x0A24] == 0x60 && P28LimiterInspector.Word(b, 0x0A25) == P28FuelMapContract.Map1RpmAxisOrigin, "map_1 RPM-axis pointer construction differs.");
        Require(b[0x0A65] == 0x60 && P28LimiterInspector.Word(b, 0x0A66) == P28FuelMapContract.LoadAxisOrigin, "load-axis pointer construction differs.");
        Require(b[0x12FC] == 0x98 && b[0x12FD] == P28FuelMapContract.Columns && b[0x12FE] == 0x99 && b[0x12FF] == P28FuelMapContract.Rows, "Native map dimensions differ.");
        Require(b[0x130C] == 0x60 && P28LimiterInspector.Word(b, 0x130D) == P28FuelMapContract.Map1Origin, "map_1 pointer selection differs.");
        Require(b[0x1323] == 0x60 && P28LimiterInspector.Word(b, 0x1324) == P28FuelMapContract.Map0Origin, "map_0 pointer selection differs.");
        Require(b[0x131A] == 0xE9 && b[0x131B] == 0x27, "DATA0127.1 selector reader differs.");
        Require(b[0x12DF] == 0xC4 && b[0x12E0] == 0x27 && b[0x12E1] == 0x09 && b[0x12F9] == 0xC4 && b[0x12FA] == 0x27 && b[0x12FB] == 0x19,
            "Static DATA0127.1 clear/set writers differ.");
        foreach (var axis in P28FuelMapContract.Axes)
        {
            Require(b[axis.Origin] == 0 && b[axis.Origin + axis.Count - 1] == 0, $"{axis.Id} endpoints differ.");
            for (var i = 1; i < axis.Count - 1; i++) Require(b[axis.Origin + i] > b[axis.Origin + i - 1], $"{axis.Id} is not strictly ascending before its terminal sentinel.");
        }
    }

    public static P28FuelMapsInspection Inspect(RomImage image, RomProfile profile, P28ExactBaselineBinding? binding, bool confirmed)
    {
        var matched = confirmed && binding is not null && image.Size == binding.ExpectedSize && image.Hash == binding.RomHash &&
            profile.Id == binding.ProfileId && string.Equals(P28VtecInspector.ComputeProfileDigest(profile), binding.ProfileDigest, StringComparison.OrdinalIgnoreCase);
        if (!matched)
            return new(1, image.Hash, image.Size, false, binding is null ? "NotProvided" : "UnconfirmedOrMismatched", [], [], [], [], [],
                ["General image data only. Exact research binding and explicit profile confirmation are required; no candidate region is decoded."]);
        P28ByteExecutionValidator.ValidateAdmission(image, profile, binding!, true, null);
        LayoutGuard(image);
        var axes = P28FuelMapContract.Axes.Select(axis => new P28FuelAxisInspection(axis.Id, axis.Origin, axis.Count, axis.IntervalCount,
            axis.ElementEncoding, axis.Direction, axis.TerminalRule, Array.AsReadOnly(image.Span.Slice(axis.Origin, axis.Count).ToArray().Select(value => (int)value).ToArray()))).ToArray();
        var maps = P28FuelMapContract.Maps.Select(map =>
        {
            var rows = Enumerable.Range(0, map.Rows).Select(row => (IReadOnlyList<int>)Array.AsReadOnly(
                image.Span.Slice(map.Origin + row * map.Columns, map.Columns).ToArray().Select(value => (int)value).ToArray())).ToArray();
            var metadata = image.Span.Slice(map.MetadataOrigin, map.Columns).ToArray().Select(value => (int)value).ToArray();
            return new P28FuelMapInspection(map.Id, map.Origin, map.EndInclusive, map.MetadataOrigin, map.MetadataEndInclusive, map.Rows, map.Columns,
                map.CellEncoding, map.StorageOrder, $"0x{map.Origin:X4} + row*10 + column", map.RpmAxisId, map.LoadAxisId,
                Array.AsReadOnly(rows), Array.AsReadOnly(metadata));
        }).ToArray();
        return new(1, image.Hash, image.Size, true, "MatchedExactResearchParentNotFactoryAuthentication", Array.AsReadOnly(axes), Array.AsReadOnly(maps),
            ["DATA0127.1 clear selects map_0; set selects map_1 at 131A. Static writers: clear at 12DF, set at 12F9.",
             "Selection is a software-bit relationship only. It is not proof of a physical cam/VTEC state.",
             "Direct path additionally constrains DATA011C.5 and DATA0121.6 clear; the harness does not execute their upstream writers."],
            ["Raw inputs run native axis helper 59B2..59E3; map selection runs 12FC..133F; lookup runs 59E4..5A45.",
             "Cells are unsigned bytes. Each is multiplied by its unsigned per-column metadata byte; two column interpolations precede one row interpolation.",
             "Interpolation uses the high word of unsigned 16x16 multiplication, so every step truncates independently."],
            ["Lookup result in ER2 is moved to A at 1347 and stored as unsigned word DATA0140 at 134E. The exact original's zero program byte at 60E5 leaves ZF set, so JEQ skips optional 5A55 correction.",
             "If the revision-bound 60E5 gate were nonzero, 5A55 would multiply by a word formed from DATA013F and a code-selected high byte, shift right by nine, and saturate to FFFF; that conditional path is not claimed as an actual-original execution witness.",
             "DATA0140 is later a numeric multiplication operand at 14ED/14F0 and 21DB/21E0; the boundary proves a fuel-related software intermediate, not an electrical pulse or delivered AFR."],
            ["Physical RPM/MAP units and cell fuel units/percent remain unknown.",
             "Axis fractions are full Q16 words: DIV leaves DD=1, so the caller's shared D3 opcode performs a word store; the following LB returns DD to byte mode before the cache-index store.",
             "Physical selector reachability, scheduler/IRQ behavior, electrical injector output, full boot, engine response and AFR are NotRun."]);
    }

    internal static RomImage Mutate(RomImage parent, P28FuelMapMutation mutation)
    {
        LayoutGuard(parent);
        var offset = P28FuelMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        if (parent.Span[offset] == mutation.Value) throw new ArgumentException("Mutation must change the selected numeric cell.");
        var child = parent.CreateModifiedCopy([new BytePatch(offset, [mutation.Value])]);
        AdmitMutation(parent, child, mutation);
        return child;
    }

    internal static void AdmitMutation(RomImage parent, RomImage child, P28FuelMapMutation mutation)
    {
        LayoutGuard(parent); LayoutGuard(child);
        var offset = P28FuelMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        if (child.Span[offset] != mutation.Value || parent.Span[offset] == mutation.Value) throw new InvalidDataException("Invalid one-cell mutation.");
        for (var i = 0; i < parent.Size; i++) if (i != offset && parent.Span[i] != child.Span[i]) throw new InvalidDataException("Extra difference outside the selected cell.");
    }
}
