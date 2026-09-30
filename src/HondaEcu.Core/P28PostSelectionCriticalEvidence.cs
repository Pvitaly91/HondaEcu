namespace HondaEcu.Core;

internal sealed record P28PostSelectionCriticalOracle(P28FuelAdditiveOracle Machine, IReadOnlyList<int> X1Ends,
    IReadOnlyList<int> IeEnds, IReadOnlyList<int[]> WordEnds, IReadOnlyList<int> ProgramReadEnds,
    IReadOnlyList<int> ProgramReads);
internal static class P28PostSelectionCriticalEvidence
{
    // Exact instruction observations; no executor call, actual result or Rust state is an operand.
    internal static P28PostSelectionCriticalOracle Build(P28PostStoreConsumerOracle prefixExit, ushort current03b4,
        ushort initialIe, ushort restoreIe, byte config60f8, IReadOnlyList<int>? initialWords = null)
    {
        if (config60f8 != 0) throw new InvalidDataException("Alternate configuration is outside unchanged-original M2r scope.");
        var prefix = prefixExit.Machine; var a = prefix.Accumulator; var psw = prefix.Psw;
        var r0 = prefix.Er0; var r1 = prefix.Er1; var r2 = prefix.Er2; var r3 = prefix.Er3;
        var x1 = prefixExit.X1; var ie = (int)initialIe; var pc = 0x2259; var ssp = 0x7FE; var ret = 0;
        var words = initialWords?.ToArray() ?? new int[7];
        if (words.Length != 7 || words.Any(w => w is < 0 or > 65535)) throw new ArgumentException("Seven bounded diagnostic histories required.");
        var events = new List<int[]>(); var writes = new List<int[]>(); var accesses = new List<int[]>(); var reads = new List<int[]>();
        var ends = new List<int>(); var regs = new List<int[]>(); var stacks = new List<int>(); var lengths = new List<int>();
        var x1Ends = new List<int>(); var ieEnds = new List<int>(); var wordEnds = new List<int[]>();
        var programReads = new List<int>(); var programEnds = new List<int>();
        bool Flag(int bit) => (psw & bit) != 0;
        void Set(int bit, bool on) => psw = on ? psw | bit : psw & ~bit;
        void Load(int value) { a = value; Set(0x1000, true); Set(0x4000, a == 0); }
        void Compare(int lhs, int rhs) { Set(0x8000, lhs < rhs); Set(0x4000, lhs == rhs); }
        int Read(int address, int width, int value) { int[] row = [pc, address, width, 0, value]; accesses.Add(row); reads.Add(row); return value; }
        void Write(int address, int width, int value) { writes.Add([address, width, value]); accesses.Add([pc, address, width, 1, value]); }
        void Ror() { var old = a; a = (a >> 1) | (Flag(0x8000) ? 0x8000 : 0); Set(0x8000, (old & 1) != 0); }
        while (pc != 0x22B1)
        {
            if (events.Count >= 48) throw new InvalidOperationException("Critical oracle escaped finite unchanged-original software scope.");
            var oldA = a; var oldPsw = psw; var next = pc + 1; var length = 1; var lhs = 65536; var rhs = 65536;
            void Size(int n) { length = n; next = pc + n; }
            void Branch(bool take, int target) { Size(2); if (take) next = target; }
            switch (pc)
            {
                case 0x2259: Size(5); ie = Read(0x1A, 16, ie) & 0x02A0; Set(0x4000, ie == 0); Write(0x1A, 16, ie); break;
                // PSWH is a coherent CPU alias. Primary explicit operand-mask RMW preserves its remaining represented bits.
                case 0x225E: Size(3); psw &= ~0x100; break;
                case 0x2261: Size(3); words[2] = Read(0x88, 16, x1); Write(0x194, 16, words[2]); break;
                case 0x2264: Size(2); words[0] = a; Write(0x190, 16, a); break;
                case 0x2266: Size(2); words[1] = a; Write(0x192, 16, a); break;
                case 0x2268: Size(3); psw |= 0x100; break;
                case 0x226B: Size(2); Load(Read(0xF8, 16, restoreIe)); break;
                case 0x226D: Size(2); ie = a; Write(0x1A, 16, ie); break;
                case 0x226F: Size(4); programReads.Add(0x60F8); a = (a & 0xFF00) | config60f8; Set(0x4000, config60f8 == 0); break;
                case 0x2273: Branch(Flag(0x4000), 0x229F); break;
                case 0x229F: Read(0x8C, 16, 0x3B4); Load(Read(0x3B4, 16, current03b4)); break;
                case 0x22A0: Size(3); ret = next; Write(0x7FE, 16, ret); ssp -= 2; next = 0x5991; break;
                case 0x5991: Size(4); r0 = 5; Write(0x100, 16, r0); break;
                case 0x5995:
                    Size(2); var product = (uint)a * (uint)Read(0x100, 16, r0); a = (int)(product & 65535); r1 = (int)(product >> 16);
                    Write(0x102, 16, r1); Set(0x4000, product == 0); break;
                case 0x5997:
                case 0x599A:
                    Size(2); Read(0x102, 16, r1); Set(0x8000, (r1 & 1) != 0); r1 >>= 1; Write(0x102, 16, r1); break;
                case 0x5999: case 0x599C: Ror(); break;
                case 0x599D: Size(3); lhs = Read(0x102, 8, r1 & 255); rhs = 0; Compare(lhs, rhs); break;
                case 0x59A0: Branch(Flag(0x4000), 0x59A5); break;
                case 0x59A2: Size(3); Load(65535); break;
                case 0x59A5: ssp += 2; next = Read(0x7FE, 16, ret); break;
                case 0x22A3: Size(2); x1 = 0; Write(0x88, 16, 0); break;
                case 0x22A5:
                case 0x22A8:
                case 0x22AB:
                case 0x22AE:
                    Size(3); Read(0x88, 16, x1); var slot = (pc - 0x22A5) / 3; words[slot + 3] = a; Write(0x3B6 + 2 * slot, 16, a); break;
                default: throw new InvalidOperationException($"Unknown critical PC {pc:X4}; no forced bypass.");
            }
            events.Add([pc, next, oldA, a, oldPsw, psw, lhs, rhs]); ends.Add(accesses.Count); regs.Add([r0, r1, r2, r3]);
            stacks.Add(ssp); lengths.Add(length); x1Ends.Add(x1); ieEnds.Add(ie); wordEnds.Add((int[])words.Clone()); programEnds.Add(programReads.Count); pc = next;
        }
        var machine = new P28FuelAdditiveOracle(events.AsReadOnly(), writes.AsReadOnly(), reads.AsReadOnly(), accesses.AsReadOnly(),
            ends.AsReadOnly(), regs.AsReadOnly(), stacks.AsReadOnly(), lengths.AsReadOnly(), a, psw, r0, r1, r2, r3, prefix.Mode);
        return new(machine, x1Ends.AsReadOnly(), ieEnds.AsReadOnly(), wordEnds.AsReadOnly(), programEnds.AsReadOnly(), programReads.AsReadOnly());
    }
}
