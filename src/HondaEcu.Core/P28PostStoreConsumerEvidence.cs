namespace HondaEcu.Core;

internal sealed record P28PostStoreConsumerOracle(P28FuelAdditiveOracle Machine, IReadOnlyList<int> X1Ends,
    IReadOnlyList<int> ModeEnds, int X1, byte Mode);
// Independent caller/helper/return instruction oracle. It never calls Rust or copies observed arithmetic.
internal static class P28PostStoreConsumerEvidence
{
    internal static P28PostStoreConsumerOracle Build(P28FuelAdditiveOracle prefixExit, ushort word0150,
        ushort source014c, ushort source0144, byte mode012c, int initialX1)
    {
        var a = prefixExit.Accumulator; var psw = prefixExit.Psw; var r0 = prefixExit.Er0; var r1 = prefixExit.Er1;
        var r2 = prefixExit.Er2; var r3 = prefixExit.Er3; var x1 = initialX1; var mode = mode012c;
        var pc = 0x223B; var ssp = 0x7FE; var ret = 0;
        var events = new List<int[]>(); var writes = new List<int[]>(); var accesses = new List<int[]>();
        var reads = new List<int[]>(); var ends = new List<int>(); var regs = new List<int[]>();
        var stacks = new List<int>(); var lengths = new List<int>(); var x1Ends = new List<int>(); var modes = new List<int>();
        bool Flag(int bit) => (psw & bit) != 0;
        void Set(int bit, bool on) => psw = on ? psw | bit : psw & ~bit;
        void Load(int value) { a = value; Set(0x1000, true); Set(0x4000, a == 0); }
        void Compare(int lhs, int rhs) { Set(0x8000, lhs < rhs); Set(0x4000, lhs == rhs); }
        int Read(int address, int width, int value)
        {
            int[] access = [pc, address, width, 0, value]; accesses.Add(access);
            if (address is 0x14C or 0x150 or 0x144 or 0x12C) reads.Add(access);
            return value;
        }
        void Write(int address, int width, int value) { writes.Add([address, width, value]); accesses.Add([pc, address, width, 1, value]); }
        void Ror() { var old = a; a = (a >> 1) | (Flag(0x8000) ? 0x8000 : 0); Set(0x8000, (old & 1) != 0); }
        while (pc != 0x2259)
        {
            if (events.Count >= 48) throw new InvalidOperationException("Consumer oracle escaped finite software-only scope.");
            var oldA = a; var oldPsw = psw; var next = pc + 1; var length = 1; var lhs = 65536; var rhs = 65536;
            void Size(int n) { length = n; next = pc + n; }
            void Branch(bool take, int target) { Size(2); if (take) next = target; }
            switch (pc)
            {
                case 0x223B: Size(2); Load(Read(0x14C, 16, source014c)); break;
                case 0x223D: Size(2); lhs = a; rhs = Read(0x150, 16, word0150); Compare(lhs, rhs); break;
                case 0x223F:
                    Size(3); Read(0x12C, 8, mode); mode = (byte)((mode & ~32) | (Flag(0x8000) ? 32 : 0)); Write(0x12C, 8, mode); break;
                case 0x2242: Branch(!Flag(0x8000), 0x2246); break;
                case 0x2244: Size(2); Load(Read(0x150, 16, word0150)); break;
                case 0x2246: Size(2); Load(a); break; // ACC06 coherent CPU alias, not a RAM read.
                case 0x2248: Branch(Flag(0x4000), 0x2254); break;
                case 0x224A:
                    Size(2); var before = a; var value = Read(0x144, 16, source0144); var sum = a + value; a = sum & 65535;
                    Set(0x8000, sum > 65535); Set(0x4000, a == 0); Set(0x2000, (before & 15) + (value & 15) > 15); break;
                case 0x224C: Branch(!Flag(0x8000), 0x2251); break;
                case 0x224E: Size(3); Load(65535); break;
                case 0x2251: Size(3); ret = next; Write(0x7FE, 16, ret); ssp -= 2; next = 0x5991; break;
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
                case 0x2254: x1 = a; Write(0x88, 16, x1); break;
                case 0x2255: Size(3); if ((Read(0x12C, 8, mode) & 32) == 0) next = 0x2259; break;
                case 0x2258: Load(0); break;
                default: throw new InvalidOperationException($"Unknown consumer PC {pc:X4}.");
            }
            events.Add([pc, next, oldA, a, oldPsw, psw, lhs, rhs]); ends.Add(accesses.Count); regs.Add([r0, r1, r2, r3]);
            stacks.Add(ssp); lengths.Add(length); x1Ends.Add(x1); modes.Add(mode); pc = next;
        }
        var machine = new P28FuelAdditiveOracle(events.AsReadOnly(), writes.AsReadOnly(), reads.AsReadOnly(), accesses.AsReadOnly(),
            ends.AsReadOnly(), regs.AsReadOnly(), stacks.AsReadOnly(), lengths.AsReadOnly(), a, psw, r0, r1, r2, r3, prefixExit.Mode);
        return new(machine, x1Ends.AsReadOnly(), modes.AsReadOnly(), x1, mode);
    }
}
