namespace HondaEcu.Core;

public sealed record P28IdleCell(string Id, int AxisOffset, byte RawAxis, int ValueOffset, ushort RawValue, string ExecutionDomain);
public sealed record P28IdleInspection(int FormatVersion, RomHash ImageHash, int Size, bool InterpretationApplied, string Binding,
    IReadOnlyList<P28IdleCell> Cells, IReadOnlyList<string> Evidence, IReadOnlyList<string> Dependencies)
{
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
}
public static class P28IdleInspector
{
    internal const int Table = 0x68CB;
    internal static int FieldOffset(string field) => field == "context-21a0-table-cell-2" ? Table + 7 : throw new ArgumentException("Only the reviewed numeric cell 2 is admitted for in-memory research.");
    internal static void TableGuard(RomImage image)
    {
        image.ValidateExactSize(32768);
        if (P28LimiterInspector.Word(image.Span, 0x2FD5) != Table) throw new InvalidDataException("Unexpected target table pointer.");
        for (var i = 0; i < 6; i++)
            if (image.Span[Table + 3 * i] <= image.Span[Table + 3 * (i + 1)]) throw new InvalidDataException("Target axis must be strictly descending.");
        if (image.Span[Table] != 255 || image.Span[Table + 18] != 0 || image.Span[Table + 12] != 52)
            throw new InvalidDataException("Target table does not cover the established raw/context domain.");
    }
    public static P28IdleInspection Inspect(RomImage image, RomProfile profile, P28ExactBaselineBinding? binding, bool confirmed)
    {
        var matched = confirmed && binding is not null && image.Size == binding.ExpectedSize && image.Hash == binding.RomHash && profile.Id == binding.ProfileId &&
            string.Equals(P28VtecInspector.ComputeProfileDigest(profile), binding.ProfileDigest, StringComparison.OrdinalIgnoreCase);
        if (!matched) return new(1, image.Hash, image.Size, false, binding is null ? "NotProvided" : "UnconfirmedOrMismatched", [], [],
            ["General image data only. Confirmation alone grants no revision-specific interpretation."]);
        P28ByteExecutionValidator.ValidateAdmission(image, profile, binding!, true, null); TableGuard(image);
        var cells = Enumerable.Range(0, 7).Select(i => new P28IdleCell($"context-21a0-table-cell-{i}", Table + 3 * i,
            image.Span[Table + 3 * i], Table + 3 * i + 1, P28LimiterInspector.Word(image.Span, Table + 3 * i + 1), i <= 4 ? "Selected path: rawD9 >= 52" : "NotEvaluated in selected path")).ToArray();
        return new(1, image.Hash, image.Size, true, "MatchedExactResearchParentNotFactoryAuthentication", cells,
            ["Desired period word 025C is distinct from current 00C4, error 00CA, controller history 0288/028C and command 0260/025E.",
             "2FD1 selects table 68CB, rawD9 >= 52 bypasses low-domain overrides; 306F calls 5894; 309A writes separate 027A=0; 309D with persistent 021A.0 set retains computed target; 30A9 is a WORD store (DD=1), despite the listing heuristic label.",
             "Seven packed records: unsigned byte axis then unsigned little-endian word; strictly descending axis. Helper selects the first lower knot <= raw input, then lowerY +/- floor(abs(upperY-lowerY)*(x-lowerX)/(upperX-lowerX)). No double/nearest rounding.",
             "09DE subtracts target from current period unsigned, retains borrow at 021A.4 and writes min(abs(current-target),768) to 00CA. Equality gives sign=false, magnitude=0; no deadband here.",
             "Static regulation link: 359F/35A4/35A6 multiply 00CA by program gain, 35A9 uses its sign; 35B0..35E5 update accumulated 0288/028C. Later 3770/3778 produce a separate command. This is a speed-control reference, not duty, mode threshold or a lone anti-stall comparison."],
            ["Only rawD9 >= 52, 021A.0 set and caller 0216.3 clear are executed. No physical temperature, A/C or transmission labels are inferred.",
             "Other table 68E0 and low-domain immediate overrides/corrections are not supported. Inputs outside this selected context are refused, not modeled as clamped target values.",
             "Harness supplies current raw period and rawD9, not capture/G/F. It stages producer then immediate error consumer without executing the intervening scheduler or downstream regulator/PWM.",
             "Target is overwritten each supported call; no target filter, target counter or target hold exists on this selected path. Initial target/error/history are seed-once values, never per-call overrides.",
             "Static software idle-regulator identification is not electrical IACV proof or physical speed stabilization. Hardware/full boot/GUI remain NotRun; physicalRpmAvailable=false."]);
    }
    internal static RomImage Mutate(RomImage original, P28IdleMutation mutation)
    {
        TableGuard(original); var offset = FieldOffset(mutation.Field);
        var b = original.CreateModifiedCopy([new BytePatch(offset, [(byte)mutation.Value, (byte)(mutation.Value >> 8)])]);
        AdmitMutation(original, b, mutation); return b;
    }
    internal static void AdmitMutation(RomImage original, RomImage image, P28IdleMutation mutation)
    {
        TableGuard(original); TableGuard(image); var offset = FieldOffset(mutation.Field);
        if (P28LimiterInspector.Word(original.Span, offset) == mutation.Value || P28LimiterInspector.Word(image.Span, offset) != mutation.Value)
            throw new InvalidDataException("Mutation must change exactly the named numeric cell.");
        for (var i = 0; i < original.Size; i++) if ((i < offset || i >= offset + 2) && original.Span[i] != image.Span[i])
                throw new InvalidDataException("Extra diff: opcode, pointer, selector, axis and other cells must remain byte-identical.");
    }
}
