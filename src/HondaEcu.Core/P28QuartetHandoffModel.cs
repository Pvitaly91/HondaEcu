namespace HondaEcu.Core;

public sealed record P28QuartetSelection(int Selector013c, int X1, int SelectedSlot, int SelectedAddress, int CompanionAddress);
public static class P28QuartetHandoffModel
{
    public static P28QuartetSelection Select(byte selector013c)
    {
        if (selector013c > 3) throw new ArgumentOutOfRangeException(nameof(selector013c), "Outside audited safe selector domain.");
        var shifted = (byte)(selector013c << 1); var x1 = unchecked((ushort)(short)(sbyte)shifted);
        return new(selector013c, x1, selector013c, 0x3B6 + x1, 0x3BE + x1);
    }
    public static ushort Result(ushort selected, ushort companion) => (ushort)Math.Min(selected + companion, 65535);
}
internal sealed record P28QuartetOracle(IReadOnlyList<int[]> Events, IReadOnlyList<int[]> Accesses, IReadOnlyList<int> AccessEnds, IReadOnlyList<int> Lengths, IReadOnlyList<int[]> PointerEnds, int Stop, int A, int Psw);
internal static class P28QuartetHandoffEvidence
{
    // Independently specified primary-ISA observations. No decoded OEM byte fixture or Rust values.
    internal static P28QuartetOracle Build(int entryA, byte selector, byte gate0124, byte control0125, byte byte012a, IReadOnlyList<int> quartet, Dictionary<int, int> ram)
    {
        var mapping = P28QuartetHandoffModel.Select(selector); var pc = 0x584; var a = entryA; var psw = 0x1DCA;
        var events = new List<int[]>(); var accesses = new List<int[]>(); var ends = new List<int>(); var lengths = new List<int>(); var pointers = new List<int[]>();
        bool F(int mask) => (psw & mask) != 0;
        void Flag(int mask, bool yes) => psw = yes ? psw | mask : psw & ~mask;
        int Read(int address, int width, int value) { accesses.Add([pc, address, width, 0, value]); return value; }
        void Write(int address, int width, int value) { accesses.Add([pc, address, width, 1, value]); ram[address] = value; }
        void Load(int value, bool word) { a = word ? value : (a & 0xFF00) | value; Flag(0x1000, word); Flag(0x4000, value == 0); }
        while (pc is not (0x5ED or 0x5AF))
        {
            if (events.Count >= 40) throw new InvalidOperationException("Bounded consumer model exceeded40 instructions.");
            var ba = a; var bp = psw; var next = pc + 1; var length = 1;
            void Size(int n) { length = n; next = pc + n; }
            switch (pc)
            {
                case 0x584: Size(2); Load(Read(0x13C, 8, selector), false); break;
                case 0x586: var lo = a & 255; Flag(0x8000, (lo & 128) != 0); a = (a & 0xFF00) | ((lo << 1) & 255); break;
                case 0x587: a = unchecked((ushort)(short)(sbyte)(a & 255)); Flag(0x1000, true); break;
                case 0x588: Write(0x90, 16, a); break;
                case 0x589: Size(3); if ((Read(0x125, 8, control0125) & 16) != 0) next = 0x5AF; break;
                case 0x58C: case 0x5D8: Load(0, true); break;
                case 0x58D: Write(0x92, 16, a); break;
                case 0x58E: case 0x591: case 0x594: case 0x597: Size(3); Read(0x92, 16, ram[0x92]); Write(0x3BE + ((pc - 0x58E) / 3) * 2, 16, a); break;
                case 0x59A: Load(0, false); break;
                case 0x59B: Size(2); Write(0x19D, 8, a & 255); break;
                case 0x59D: Size(3); next = 0x7DEF; break;
                case 0x7DEF: Size(2); Write(0x19F, 8, a & 255); break;
                case 0x7DF1: Size(3); next = 0x5D5; break;
                case 0x5D5: Size(3); var old = Read(0x19B, 8, ram[0x19B]); Flag(0x4000, (old & 1) == 0); Read(0x19B, 8, old); Write(0x19B, 8, old & ~1); break;
                case 0x5D9: Size(3); if ((Read(0x124, 8, gate0124) & 16) != 0) next = 0x5EB; break;
                case 0x5DC: Size(3); if ((Read(0x12A, 8, byte012a) & 2) != 0) next = 0x5EB; break;
                case 0x5DF: Size(3); Read(0x90, 16, mapping.X1); Load(Read(mapping.SelectedAddress, 16, quartet[mapping.SelectedSlot]), true); break;
                case 0x5E2: Size(4); Read(0x90, 16, mapping.X1); var operand = Read(mapping.CompanionAddress, 16, ram[mapping.CompanionAddress]); var sum = a + operand; Flag(0x2000, (a & 15) + (operand & 15) > 15); a = sum & 65535; Flag(0x8000, sum > 65535); Flag(0x4000, a == 0); break;
                case 0x5E6: Size(2); if (!F(0x8000)) next = 0x5EB; break;
                case 0x5E8: Size(3); Load(65535, true); break;
                case 0x5EB: Size(2); Write(0x196, 16, a); break;
                default: throw new InvalidOperationException($"Unknown consumer model PC{pc:X4}.");
            }
            events.Add([pc, next, ba, a, bp, psw, 65536, 65536]); lengths.Add(length); ends.Add(accesses.Count); pointers.Add([ram[0x90], ram[0x92]]); pc = next;
        }
        return new(events, accesses, ends, lengths, pointers, pc, a, psw);
    }
}
