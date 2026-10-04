namespace HondaEcu.Core;

internal static class P28Word0196AlternateModel
{
    // Independent primary-ISA model. The generation value comes from the C#
    // upstream history, never from a Rust compare observation.
    internal static P28Word0196Oracle Build(int value, int entryA, int entryPsw, Dictionary<int, int> history)
    {
        var ram = new Dictionary<int, int>(history); var a = entryA; var psw = entryPsw; var pc = 0x556F;
        var events = new List<int[]>(); var accesses = new List<int[]>(); var ends = new List<int>(); var lengths = new List<int>();
        bool F(int mask) => (psw & mask) != 0;
        void Flag(int mask, bool yes) => psw = yes ? psw | mask : psw & ~mask;
        int Read(int address) { var v = ram[address]; accesses.Add([pc, address, 8, 0, v]); return v; }
        void Write(int address, int v) { accesses.Add([pc, address, 8, 1, v]); ram[address] = v; }
        void Load(int v) { a = (a & 0xFF00) | v; Flag(0x1000, false); Flag(0x4000, v == 0); }
        while (pc is not (0x5596 or 0x55C5))
        {
            if (events.Count >= 18) throw new InvalidOperationException("Software alternate budget exceeded.");
            var ba = a; var bp = psw; var lhs = 65536; var rhs = 65536; var next = pc + 1; var length = 1;
            void Size(int n) { length = n; next = pc + n; }
            switch (pc)
            {
                case 0x556F: Size(2); Load(Read(0x18E)); break;
                case 0x5571: var lo = a & 255; a = (a & 0xFF00) | ((lo << 1) & 255); Flag(0x8000, (lo & 128) != 0); Flag(0x1000, false); break;
                case 0x5572: Size(3); var old = Read(0x18E); var rotated = ((old << 1) | (F(0x8000) ? 1 : 0)) & 255; Flag(0x8000, (old & 128) != 0); Write(0x18E, rotated); break;
                case 0x5575: Load(Read(0x108)); break;
                case 0x5576: Size(2); var mask = Read(0x18E); a = (a & 0xFF00) | ((a & 255) & mask); Flag(0x4000, (a & 255) == 0); break;
                case 0x5578: Size(5); accesses.Add([pc, 0x196, 16, 0, value]); lhs = value; rhs = 192; Flag(0x8000, value < 192); Flag(0x4000, value == 192); break;
                case 0x557D: Size(2); if (F(0x8000)) next = 0x55BF; break;
                case 0x557F: Size(3); Write(0x109, Read(0x117)); break;
                case 0x5582: Size(3); var v117 = Read(0x117) & (a & 255); Write(0x117, v117); Flag(0x4000, v117 == 0); break;
                case 0x5585: Size(3); if ((Read(0x12A) & 128) != 0) next = 0x5592; break;
                case 0x5588: Size(3); if ((Read(0x124) & 32) != 0) next = 0x5592; break;
                case 0x558B: Size(3); var v18f = Read(0x18F) & (a & 255); Write(0x18F, v18f); Flag(0x4000, v18f == 0); break;
                case 0x558E: Size(4); var v12a = Read(0x12A) | 1; Write(0x12A, v12a); Flag(0x4000, v12a == 0); break;
                case 0x5592: Size(2); Load(Read(0x18F)); break;
                case 0x5594: Size(2); a |= 240; Flag(0x4000, (a & 255) == 0); break;
                case 0x55BF: Size(2); Load(15); break;
                case 0x55C1: Size(2); Write(0x117, a & 255); break;
                case 0x55C3: Size(2); Write(0x18F, a & 255); break;
                default: throw new InvalidOperationException($"Unadmitted alternate PC{pc:X4}.");
            }
            events.Add([pc, next, ba, a, bp, psw, lhs, rhs]); ends.Add(accesses.Count); lengths.Add(length); pc = next;
        }
        return new(events, accesses, ends, lengths, pc, a, psw);
    }
}
