namespace HondaEcu.Core;

public sealed record P28IgnitionAxisInspection(string Id, int Origin, int Count, int IntervalCount, string ElementEncoding,
    string Direction, string TerminalRule, IReadOnlyList<int> RawValues);
public sealed record P28IgnitionMapInspection(string Id, int Origin, int EndInclusive, int Rows, int Columns,
    string CellEncoding, string StorageOrder, string AddressFormula, string RpmAxisId, string LoadAxisId,
    IReadOnlyList<IReadOnlyList<int>> Cells);
public sealed record P28IgnitionMapsInspection(int FormatVersion, RomHash ImageHash, int Size, bool InterpretationApplied,
    string Binding, IReadOnlyList<P28IgnitionAxisInspection> Axes, IReadOnlyList<P28IgnitionMapInspection> Maps,
    IReadOnlyList<string> ConfirmedClaims, IReadOnlyList<string> Selection, IReadOnlyList<string> LookupBoundary,
    IReadOnlyList<string> ConsumerBoundary, IReadOnlyList<string> ExcludedNeighbors, IReadOnlyList<string> Unknowns)
{
    public bool PhysicalRpmAvailable => false;
    public string AngleUnits => "raw / physical degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string D1InteractiveGuiAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None";
}

public static class P28IgnitionMapInspector
{
    public static void LayoutGuard(RomImage image)
    {
        image.ValidateExactSize(32768);
        var b = image.Span;
        static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
        Require(b[0x0A0C] == 0x60 && P28LimiterInspector.Word(b, 0x0A0D) == P28IgnitionMapContract.Map0RpmAxisOrigin,
            "ignition_map_0 RPM-axis pointer differs.");
        Require(b[0x0A24] == 0x60 && P28LimiterInspector.Word(b, 0x0A25) == P28IgnitionMapContract.Map1RpmAxisOrigin,
            "ignition_map_1 RPM-axis pointer differs.");
        Require(b[0x0A50] == 0x60 && P28LimiterInspector.Word(b, 0x0A51) == P28IgnitionMapContract.LoadAxisOrigin,
            "Ignition load-axis pointer differs.");
        Require(b[0x0B67] == 0x98 && b[0x0B68] == P28IgnitionMapContract.Columns &&
            b[0x0B69] == 0x99 && b[0x0B6A] == P28IgnitionMapContract.Rows, "Native ignition-map dimensions differ.");
        Require(b[0x0B71] == 0xED && b[0x0B72] == 0x27, "DATA0227.5 selector reader differs.");
        Require(b[0x0B7A] == 0x60 && P28LimiterInspector.Word(b, 0x0B7B) == P28IgnitionMapContract.Map0Origin,
            "ignition_map_0 pointer differs.");
        Require(b[0x0B91] == 0x60 && P28LimiterInspector.Word(b, 0x0B92) == P28IgnitionMapContract.Map1Origin,
            "ignition_map_1 pointer differs.");
        Require(b[0x0BAF] == 0xA3 && b[0x0BB0] == 0x0D && b[0x0BB1] == 0x32 &&
            P28LimiterInspector.Word(b, 0x0BB2) == 0x59E4, "Ignition lookup ABI differs.");
        Require(b[0x0BD2] == 0xD4 && b[0x0BD3] == 0x48, "DATA0248 consumer store differs.");
        foreach (var axis in P28IgnitionMapContract.Axes)
        {
            Require(b[axis.Origin] == 0 && b[axis.Origin + axis.Count - 1] == 0, $"{axis.Id} endpoints differ.");
            for (var i = 1; i < axis.Count - 1; i++)
                Require(b[axis.Origin + i] > b[axis.Origin + i - 1], $"{axis.Id} is not ascending before its terminal sentinel.");
        }
    }

    public static P28IgnitionMapsInspection Inspect(RomImage image, RomProfile profile, P28ExactBaselineBinding? binding, bool confirmed)
    {
        var matched = confirmed && binding is not null && image.Size == binding.ExpectedSize && image.Hash == binding.RomHash &&
            profile.Id == binding.ProfileId && string.Equals(P28VtecInspector.ComputeProfileDigest(profile), binding.ProfileDigest, StringComparison.OrdinalIgnoreCase);
        if (!matched)
            return new(1, image.Hash, image.Size, false, binding is null ? "NotProvided" : "UnconfirmedOrMismatched", [], [], [], [], [], [], [],
                ["General image data only. Exact research binding and explicit profile confirmation are required; candidate regions are not decoded."]);
        P28ByteExecutionValidator.ValidateAdmission(image, profile, binding!, true, null);
        LayoutGuard(image);
        var axes = P28IgnitionMapContract.Axes.Select(axis => new P28IgnitionAxisInspection(axis.Id, axis.Origin, axis.Count,
            axis.IntervalCount, axis.ElementEncoding, axis.Direction, axis.TerminalRule,
            Array.AsReadOnly(image.Span.Slice(axis.Origin, axis.Count).ToArray().Select(value => (int)value).ToArray()))).ToArray();
        var maps = P28IgnitionMapContract.Maps.Select(map =>
        {
            var rows = Enumerable.Range(0, map.Rows).Select(row => (IReadOnlyList<int>)Array.AsReadOnly(
                image.Span.Slice(map.Origin + row * map.Columns, map.Columns).ToArray().Select(value => (int)value).ToArray())).ToArray();
            return new P28IgnitionMapInspection(map.Id, map.Origin, map.EndInclusive, map.Rows, map.Columns, map.CellEncoding,
                map.StorageOrder, $"0x{map.Origin:X4} + row*10 + column", map.RpmAxisId, map.LoadAxisId, Array.AsReadOnly(rows));
        }).ToArray();
        return new(1, image.Hash, image.Size, true, "MatchedExactResearchParentNotFactoryAuthentication", Array.AsReadOnly(axes), Array.AsReadOnly(maps),
            ["0B67/0B69 pass 10 columns and 20 rows to helper 59E4; its r3*10 row stride and word reads establish row-major 20x10 unsigned-byte cells.",
             "The direct caller loads 72E4 or 73AC into X1. Its PSWL.5 clear entry uses constant 0101, so no per-column metadata is read.",
             "The 7000 load and 7014/7028 RPM axes are shared ROM data with fuel, but ignition owns separate load cache/fraction DATA01BB/DATA01BE."],
            ["DATA0227.5 clear selects ignition_map_0; set selects ignition_map_1. The harness updates only mask 20 and preserves adjacent bits.",
             "The selected context always uses DATA0238 as its raw RPM input; when bit 5 is set, the native producer also substitutes DATA0238 for the 7028 axis.",
             "Fixed direct-path gates: DATA021D.4, DATA0214.5, DATA021F.1 and DATA0219.6 clear. This is a scripted caller scope, not an ECU main loop or physical cam/VTEC claim."],
            ["Native producers execute 0A0C..0A61 and axis helper 59B2..59E3. Native source selection executes 0B64..0BAE.",
             "Lookup executes 0BAF..0BB3 plus 59E4..5A45. Two column interpolations precede one row interpolation; each unsigned Q16 multiply takes its high word and truncates independently."],
            ["The immediate consumer executes 0BB4..0BD3 on the same CPU/RAM and stores one byte in DATA0248.",
             "DATA0247 zero retains the raw lookup byte; otherwise the stored byte is the high byte of unsigned lookup*DATA0247.",
             "DATA0248 is statically read at 0FF4 as the base operand of a corrected/clamped ignition-related calculation. That downstream stage is static-only in M2c."],
            ["7474 and 74E2 are distinct alternate 11-row pointer targets selected by other gates; they are not metadata and are outside the confirmed direct primary-map scope.",
             "The bytes immediately after 73AB begin ignition_map_1. No bytes following either primary 200-byte footprint are treated as multipliers."],
            ["Physical RPM/load scaling, raw-cell-to-degree conversion, delivered spark timing, dwell, driver transitions, scheduler/IRQ reachability and full boot remain unavailable/NotRun.",
             "The static chain after DATA0248 includes corrections and output scheduling, so the primary cell, lookup byte, corrected timing and dwell/driver values are not conflated."]);
    }

    internal static RomImage Mutate(RomImage parent, P28IgnitionMapMutation mutation)
    {
        LayoutGuard(parent);
        var offset = P28IgnitionMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        if (parent.Span[offset] == mutation.Value) throw new ArgumentException("Mutation must change the selected numeric cell.");
        var child = parent.CreateModifiedCopy([new BytePatch(offset, [mutation.Value])]);
        AdmitMutation(parent, child, mutation);
        return child;
    }

    internal static void AdmitMutation(RomImage parent, RomImage child, P28IgnitionMapMutation mutation)
    {
        LayoutGuard(parent); LayoutGuard(child);
        var offset = P28IgnitionMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        if (child.Span[offset] != mutation.Value || parent.Span[offset] == mutation.Value) throw new InvalidDataException("Invalid one-cell ignition mutation.");
        for (var i = 0; i < parent.Size; i++) if (i != offset && parent.Span[i] != child.Span[i])
                throw new InvalidDataException("Extra difference outside the selected ignition cell.");
    }
}
