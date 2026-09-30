namespace HondaEcu.Core;

// Independent instruction-level post-store oracle; exact integer operations, no executor calls.
internal static class P28PostStoreEvidence
{
    internal static P28FuelAdditiveOracle Build(P28FuelAdditiveOracle prefix, byte source125, byte source12e,
        byte source133, ushort source14c)
    {
        var a = prefix.Accumulator; var psw = prefix.Psw; var r0 = prefix.Er0; var r1 = prefix.Er1;
        var r2 = prefix.Er2; var r3 = prefix.Er3; var pc = 0x2204;
        var events = new List<int[]>(); var writes = new List<int[]>(); var accesses = new List<int[]>();
        var reads = new List<int[]>(); var ends = new List<int>(); var regs = new List<int[]>(); var lengths = new List<int>();
        bool Flag(int bit) => (psw & bit) != 0;
        void Set(int bit, bool on) => psw = on ? psw | bit : psw & ~bit;
        void Load(int v) { a = v; Set(0x1000, true); Set(0x4000, a == 0); }
        void Compare(int x, int y) { Set(0x8000, x < y); Set(0x4000, x == y); }
        int Read(int address, int width, int value)
        {
            int[] access = [pc, address, width, 0, value]; accesses.Add(access);
            if (address is 0x125 or 0x12E or 0x133 or 0x14C) reads.Add(access);
            return value;
        }
        void Write(int address, int width, int value) { writes.Add([address, width, value]); accesses.Add([pc, address, width, 1, value]); }
        while (pc != 0x223B)
        {
            if (events.Count >= 48) throw new InvalidOperationException("Post-store oracle escaped finite scope.");
            var oldA = a; var oldPsw = psw; var next = pc + 1; var length = 1; var lhs = 65536; var rhs = 65536;
            void Size(int n) { length = n; next = pc + n; }
            void Branch(bool take, int to) { Size(2); if (take) next = to; }
            switch (pc)
            {
                case 0x2204: Size(3); if ((Read(0x125, 8, source125) & 16) != 0) next = 0x221F; break;
                case 0x2207: Size(3); if ((Read(0x12E, 8, source12e) & 16) != 0) next = 0x221F; break;
                case 0x220A: Size(4); lhs = Read(0x133, 8, source133); rhs = 160; Compare(lhs, rhs); break;
                case 0x220E: Branch(!Flag(0x8000), 0x221F); break;
                case 0x2210: Size(5); lhs = Read(0x14C, 16, source14c); rhs = 0; Compare(lhs, rhs); break;
                case 0x2215: Branch(!Flag(0x4000), 0x221F); break;
                case 0x2217:
                    var v = Read(0x100, 16, r0); var before = a; a = (a - v) & 65535;
                    Set(0x8000, before < v); Set(0x4000, a == 0); Set(0x2000, (before & 15) < (v & 15)); break;
                case 0x2218: Branch(Flag(0x8000), 0x221F); break;
                case 0x221A: Size(3); lhs = a; rhs = 250; Compare(lhs, rhs); break;
                case 0x221D: Branch(!Flag(0x8000), 0x2222); break;
                case 0x221F: case 0x222A: Load(0); break;
                case 0x2220: Size(2); next = 0x2239; break;
                case 0x2222: Size(4); r0 = 2000; Write(0x100, 16, r0); break;
                case 0x2226: lhs = a; rhs = Read(0x100, 16, r0); Compare(lhs, rhs); break;
                case 0x2227: Branch(!Flag(0x8000), 0x222A); break;
                case 0x2229: r0 = a; Write(0x100, 16, r0); break;
                case 0x222B: Size(4); a = (a & 255) | 0x8000; break; // CPU ACCH alias, flags/DD unchanged; no RAM shadow.
                case 0x222F:
                    Size(2); var product = (uint)a * (uint)Read(0x100, 16, r0);
                    a = (int)(product & 65535); r1 = (int)(product >> 16);
                    Write(0x102, 16, r1); Set(0x4000, product == 0); break;
                case 0x2231: var carry = (a & 0x8000) != 0; a = (a << 1) & 65535; Set(0x8000, carry); break;
                case 0x2232: Load(Read(0x102, 16, r1)); break;
                case 0x2233:
                    var top = (a & 0x8000) != 0; a = ((a << 1) | (Flag(0x8000) ? 1 : 0)) & 65535; Set(0x8000, top); break;
                case 0x2234: Branch(!Flag(0x8000), 0x2239); break;
                case 0x2236: Size(3); Load(65535); break;
                case 0x2239: Size(2); Write(0x150, 16, a); break;
                default: throw new InvalidOperationException($"Unknown post-store PC {pc:X4}.");
            }
            events.Add([pc, next, oldA, a, oldPsw, psw, lhs, rhs]); ends.Add(accesses.Count);
            regs.Add([r0, r1, r2, r3]); lengths.Add(length); pc = next;
        }
        return new(events.AsReadOnly(), writes.AsReadOnly(), reads.AsReadOnly(), accesses.AsReadOnly(), ends.AsReadOnly(),
            regs.AsReadOnly(), events.Select(_ => 0x7FE).ToArray(), lengths.AsReadOnly(), a, psw, r0, r1, r2, r3, prefix.Mode);
    }
}
