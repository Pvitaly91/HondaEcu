using System.Buffers.Binary;

namespace HondaEcu.Core;

public sealed record P28LimiterField(string Id, int Offset, int Width, ushort Raw, string Storage, string Rule);
public sealed record P28LimiterInspection(int FormatVersion, RomHash ImageHash, int Size, bool InterpretationApplied,
    string Binding, IReadOnlyList<P28LimiterField> Fields, IReadOnlyList<string> Evidence, IReadOnlyList<string> Dependencies)
{
    public bool PhysicalRpmAvailable => false;
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string GuiR3 => "paused/NotRun";
    public string HardwareAndFullBoot => "NotRun";
}

/// <summary>Read-only exact-parent interpretation. No editor/export permission is issued.</summary>
public static class P28LimiterInspector
{
    internal static int FieldOffset(string id) => id switch
    {
        "fixed-context-cut" => 0x196A,
        "fixed-context-resume" => 0x1967,
        _ => throw new ArgumentException("Only the two established fixed-context word immediate fields are admitted for in-memory research."),
    };
    internal static ushort Word(ReadOnlySpan<byte> b, int offset) => BinaryPrimitives.ReadUInt16LittleEndian(b.Slice(offset, 2));
    internal static void OperandGuard(RomImage image)
    {
        image.ValidateExactSize(32768);
        // ISA encoding tags only, not an OEM function/corpus. Binding authorizes
        // the exact parent; B admission below protects every non-operand byte.
        if (image.Span[0x1966] != 0x62 || image.Span[0x1969] != 0x67)
            throw new InvalidDataException("Established MOV DP,#word / L A,#word operand footprints are absent.");
    }
    public static P28LimiterInspection Inspect(RomImage image, RomProfile profile, P28ExactBaselineBinding? binding, bool confirmed)
    {
        var matched = confirmed && binding is not null && image.Size == binding.ExpectedSize &&
            image.Hash == binding.RomHash && profile.Id == binding.ProfileId &&
            string.Equals(P28VtecInspector.ComputeProfileDigest(profile), binding.ProfileDigest, StringComparison.OrdinalIgnoreCase);
        if (!matched) return new(1, image.Hash, image.Size, false, binding is null ? "NotProvided" : "UnconfirmedOrMismatched", [], [],
            ["General raw overview only; --confirm-profile alone cannot decode a revision."]);
        P28ByteExecutionValidator.ValidateAdmission(image, profile, binding!, true, null); OperandGuard(image);
        var fields = new List<P28LimiterField>
        {
            new("fixed-context-cut", 0x196A, 2, Word(image.Span, 0x196A), "LittleEndianUnsignedWordImmediate", "0124.5 clear; P4.0 or 011B.7 set"),
            new("fixed-context-resume", 0x1967, 2, Word(image.Span, 0x1967), "LittleEndianUnsignedWordImmediate", "0124.5 set; P4.0 or 011B.7 set"),
        };
        foreach (var (id, offset) in new[] { ("bank-0-base-resume", 0x6495), ("bank-0-base-cut", 0x649B), ("bank-1-base-resume", 0x64A1), ("bank-1-base-cut", 0x64A7) })
            fields.Add(new(id, offset, 2, Word(image.Span, offset), "LittleEndianUnsignedProgramData", "Adaptive producer 487B..48F5; not a directly editable fixed threshold"));
        return new(1, image.Hash, image.Size, true, "MatchedExactResearchParentNotFactoryAuthentication", fields.AsReadOnly(),
            ["00C4/00C5 is the unsigned period word produced at 07A2; lower normal period represents higher speed.",
             "1966..197D selects fixed immediates or RAM 01A4/01A6, using previous 0124.5; 197D tests rawPeriod < selected word. Equality clears overspeed.",
             "1980 -> 19AC -> 1A1E/1A23 sets shared cut bit2 and overspeed bit5. 1930..1A38 also contains distinct decel/fault/other cut routes.",
             "5588 tests 0124.5 and skips 558B (AND 018F,A), preventing new channel enable. 5585 independently skips for 012A.7. Boundary before P2 write at 5596.",
             "2373/237F Code flags also throttle software work at 0725; those alone are not the engine overspeed limiter.",
             "48E9/48EC write adaptive RAM words; 4882 selects two table contexts, 4894/489D reset paths, 48A2 timer gate, 5AB8 decay, 5AC2 DATA00CE-dependent adjustment; physical calibration unestablished."],
            ["Isolated check enters 1966 after earlier gates, with 0121.7=1 and cleared PSWL.4/5; no claim to execute all decel/fault paths.",
             "Adaptive threshold producer and its timer writers are statically traced, not executed here. RAM words are explicit once-only initial software snapshots.",
             "018F is a persistent mask, not an injectorActive boolean. Skip does not undo earlier mask writes; surrounding scheduler, P2 electrical polarity, IRQ/time and pulses are NotRun.",
             "Normal period domain is distinct from raw 0 / FFFF producer fallback; neither is converted to physical RPM."]);
    }
    internal static RomImage Mutate(RomImage parent, P28LimiterMutation mutation)
    {
        OperandGuard(parent); var offset = FieldOffset(mutation.Field);
        if (Word(parent.Span, offset) == mutation.Value) throw new ArgumentException("Mutation must change the selected field.");
        var child = parent.CreateModifiedCopy([new BytePatch(offset, [(byte)mutation.Value, (byte)(mutation.Value >> 8)])]);
        AdmitMutation(parent, child, mutation); return child;
    }
    internal static void AdmitMutation(RomImage parent, RomImage child, P28LimiterMutation mutation)
    {
        OperandGuard(parent); OperandGuard(child); var offset = FieldOffset(mutation.Field);
        if (Word(child.Span, offset) != mutation.Value || Word(parent.Span, offset) == mutation.Value)
            throw new InvalidDataException("Invalid word mutation value.");
        for (var i = 0; i < parent.Size; i++)
            if ((i < offset || i >= offset + 2) && parent.Span[i] != child.Span[i]) throw new InvalidDataException("Extra byte difference outside the established operand.");
    }
}
