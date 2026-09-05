namespace HondaEcu.Core;

/// <summary>
/// A narrow semantic-form/operand guard for the recovered checksum contract,
/// not a decoder, executable OEM fixture, ROM hash database, or authenticity test.
/// Opcode constants are the existing ISA forms; addresses are scoped contract metadata.
/// </summary>
public static class P28ChecksumCodeGuard
{
    public static P28ChecksumCodeAssessment Assess(RomImage image)
    {
        ArgumentNullException.ThrowIfNull(image);
        const string qualification = "Recognized scoped instruction forms, operands and branch targets, plus analyst-declared binding; not factory authentication or full control-flow/hardware proof.";
        if (image.Size != P28NativeChecksumArithmetic.RomSize)
            return new(false, false, NativeChecksumDisposition.UnsupportedRevision, ["Unsupported raw size"], qualification);
        var data = image.ToArray();
        var issues = new List<string>();
        void Require(bool condition, string role) { if (!condition) issues.Add(role); }
        bool Op(int pc, byte value) => data[pc] == value;
        int Word(int pc) => data[pc] | data[pc + 1] << 8;
        bool Pair(int pc, byte prefix, byte operation) => Op(pc, prefix) && Op(pc + 1, operation);
        bool Indexed(int pc, byte prefix, int address, byte operation) =>
            Op(pc, prefix) && Word(pc + 1) == address && Op(pc + 3, operation);
        bool Relative(int pc, byte condition, int target) =>
            Op(pc, condition) && pc + 2 + unchecked((sbyte)data[pc + 1]) == target;

        // Sparse source-contract anchors substantiate the chosen seed and main
        // dispatch context. They do not claim global reachability or execute boot.
        Require(Word(0) == 0x24ED && Word(2) == 0x24F4 && Word(0x2E) == 0x28AE, "reset/break/main-dispatch vector anchors");
        Require(Op(0x24FC, 0x57) && Word(0x24FD) == 0x0010 && Op(0x24FF, 0xB4) && Pair(0x2500, 4, 0x15), "startup local bank and PSW/SCB clear anchors");
        Require(Op(0x26F0, 0x57) && Word(0x26F1) == 0x0010 && Op(0x2706, 0xF9), "local bank and zero accumulator before initialization clear");
        Require(Pair(0x2707, 0xA1, 0x98) && Word(0x2709) == 0x0356 && Op(0x270B, 0x62) && Word(0x270C) == 0x0480,
            "initialization clear covers persistent checksum state");
        Require(Op(0x270E, 0x82) && Op(0x270F, 0x82) && Op(0x2710, 0xD2) && Pair(0x2711, 0x92, 0xC3) && Op(0x2713, 0x86) && Relative(0x2714, 0xC8, 0x270E),
            "descending word clear and local USP lower-bound comparison");
        Require(Op(0x2744, 0x57) && Word(0x2745) == 0x0041 && Pair(0x2754, 0xA1, 0x98) && Word(0x2756) == 0x0180,
            "runtime local bank and user-stack anchors");
        Require(Op(0x28A8, 0xC5) && Pair(0x28A9, 0xF5, 0x15), "initial software status clear");
        Require(Pair(0x299E, 0xF5, 0x9E) && Pair(0x29A0, 0xA6, 5) && Relative(0x29A2, 0xCA, 0x29A6) &&
            Pair(0x29A4, 0xD5, 0x9E) && Relative(0x29AD, 0xCD, 0x29F0), "main counter dispatch anchors");
        Require(Op(0x2B67, 0xD8) && Op(0x2B68, 0x27) && 0x2B6A + unchecked((sbyte)data[0x2B69]) == 0x2B70 &&
            Op(0x2B6A, 0x32) && Word(0x2B6B) == 0x5D0E && Op(0x2B6D, 0x32) && Word(0x2B6E) == 0x5D11,
            "checksum fall-through/caller anchors");

        // Check live input construction, widths and byte-sum loop independently
        // of a convenient final residue. No contiguous firmware byte string is stored.
        Require(Pair(0x2B70, 0x91, 0x15), "entry: CLR X2");
        Require(Indexed(0x2B72, 0xB1, 0x0396, 0x48), "block-index word load into er0");
        Require(Op(0x2B76, 0xF9) && Pair(0x2B77, 0x77, 64) && Pair(0x2B79, 0x90, 0x35) && Op(0x2B7B, 0x50),
            "zero-extended byte 64, unsigned MUL, X1 block address");
        Require(Op(0x2B7C, 0x62) && Word(0x2B7D) == 32, "32-word loop count");
        Require(Indexed(0x2B7F, 0xC1, 0x0398, 0x48), "persistent byte accumulator load");
        Require(Pair(0x2B83, 0x90, 0xA8), "word program-space read through X1");
        Require(Op(0x2B85, 0xC5) && Op(0x2B86, 7) && Op(0x2B87, 0x82) && Pair(0x2B88, 0x20, 0x81),
            "byte-width addition of ACCH then accumulated r0");
        Require(Op(0x2B8A, 0x70) && Op(0x2B8B, 0x70) && Relative(0x2B8C, 0x30, 0x2B83), "ascending two-byte stride and bounded loop");
        Require(Op(0x2B8E, 0x78) && Op(0x2B8F, 0xD1) && Word(0x2B90) == 0x0398, "persistent byte accumulator store");
        Require(Indexed(0x2B92, 0xB1, 0x0396, 0x16), "word block counter increment");
        Require(Indexed(0x2B96, 0xB1, 0x0396, 0xC0) && Word(0x2B9A) == 512 && Relative(0x2B9C, 0xCE, 0x2BB6),
            "completion only after 512 blocks");
        var bodyRecognized = issues.Count == 0;
        Require(Indexed(0x2B9E, 0xB1, 0x0396, 0x15) && Op(0x2BA2, 0x78) && Relative(0x2BA3, 0xC9, 0x2BB6),
            "counter reset and zero-residue decision");
        Require(Indexed(0x2BA5, 0xC1, 0x0398, 0x15), "nonzero-residue accumulator reset");
        Require(Pair(0x2BA9, 0x90, 0x9D) && Word(0x2BAB) == P28NativeChecksumArithmetic.GateOffset && Relative(0x2BAD, 0xCE, 0x2BB6),
            "native control-byte read and conditional failure gate, not a bypass jump");
        Require(Op(0x2BAF, 0xC5) && Op(0x2BB0, 0xF5) && Pair(0x2BB1, 0x98, 0x48) && Op(0x2BB3, 3) && Word(0x2BB4) == 0x24E9,
            "software failure status and failure exit");
        var recognized = issues.Count == 0;
        var enabled = recognized && data[P28NativeChecksumArithmetic.GateOffset] == 0;
        if (recognized && !enabled) issues.Add("The native control byte suppresses nonzero-residue failure; the checksum is not reported Valid even when this image sums to zero.");
        return new(recognized, enabled, !recognized ? bodyRecognized ? NativeChecksumDisposition.DisabledOrAltered : NativeChecksumDisposition.UnsupportedRevision :
            enabled ? NativeChecksumDisposition.Unknown : NativeChecksumDisposition.DisabledOrAltered, issues.AsReadOnly(), qualification);
    }
}
