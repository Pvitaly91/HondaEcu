using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

// Independent expected instruction observations from software sources and the
// independent lookup model. No Rust value is fed back as an expected operand.
internal sealed record P28FuelAdditiveOracle(IReadOnlyList<int[]> Events, IReadOnlyList<int[]> Writes,
    IReadOnlyList<int[]> SourceReads, IReadOnlyList<int[]> Accesses, IReadOnlyList<int> AccessEnds, IReadOnlyList<int[]> RegisterEnds, IReadOnlyList<int> StackEnds, IReadOnlyList<int> Lengths, int Accumulator, int Psw, int Er0, int Er1, int Er2, int Er3, byte Mode);
internal static class P28FuelAdditiveEvidence
{
    internal static P28FuelAdditiveOracle Build(int stage, ushort lookup, P28FuelAdditiveSources s,
        byte mode, byte gate, int entryA, int entryPsw, int initialEr0, int initialEr1, int initialEr2, int initialEr3, int previousStore)
    {
        var pc = stage == 0 ? 0x2194 : stage == 1 ? 0x21DB : 0x21F2;
        var stop = stage == 0 ? 0x21DB : stage == 1 ? 0x21F2 : 0x2204;
        var a = entryA; var psw = entryPsw; var r0 = initialEr0; var r1 = initialEr1; var r2 = initialEr2; var r3 = initialEr3;
        var ret = 0; var dp = 0; var ssp = 0x7FE; var events = new List<int[]>(); var writes = new List<int[]>(); var reads = new List<int[]>(); var accesses = new List<int[]>(); var accessEnds = new List<int>(); var registerEnds = new List<int[]>(); var stackEnds = new List<int>(); var lengths = new List<int>();
        bool Flag(int bit) => (psw & bit) != 0;
        void FlagSet(int bit, bool value) => psw = value ? psw | bit : psw & ~bit;
        void Load(int value, bool word) { a = word ? value : (a & 0xFF00) | value; FlagSet(0x1000, word); FlagSet(0x4000, value == 0); }
        void Add(int value) { var old = a; var wide = a + value; a = wide & 65535; FlagSet(0x8000, wide > 65535); FlagSet(0x4000, a == 0); FlagSet(0x2000, (old & 15) + (value & 15) > 15); }
        void Compare(int x, int y) { FlagSet(0x8000, x < y); FlagSet(0x4000, x == y); }
        void Rol() { var old = a; a = ((a << 1) | (Flag(0x8000) ? 1 : 0)) & 65535; FlagSet(0x8000, (old & 0x8000) != 0); }
        void Ror() { var old = a; a = (a >> 1) | (Flag(0x8000) ? 0x8000 : 0); FlagSet(0x8000, (old & 1) != 0); }
        void Write(int address, int width, int value) { writes.Add([address, width, value]); accesses.Add([pc, address, width, 1, value]); }
        int NativeRead(int address, int width, int value) { accesses.Add([pc, address, width, 0, value]); return value; }
        int Read(int address, int width, int value) { reads.Add([pc, address, width, 0, value]); return NativeRead(address, width, value); }
        while (pc != stop)
        {
            if (events.Count >= 128) throw new InvalidOperationException("Independent M2l oracle exceeded its finite path.");
            var beforeA = a; var beforePsw = psw; var next = pc + 1; var length = 1; var lhs = 65536; var rhs = 65536;
            void Size(int size) { length = size; next = pc + size; }
            void Branch(bool take, int destination) { Size(2); if (take) next = destination; }
            switch (pc)
            {
                case 0x2194: Size(2); Load(Read(0x142, 16, s.Source0142), true); break;
                case 0x2196: Size(3); if ((NativeRead(0x12B, 8, mode) & 8) == 0) next = 0x21A5; break;
                case 0x2199: Size(4); lhs = Read(0xF2, 8, s.Counter00f2); rhs = 4; Compare(lhs, rhs); break;
                case 0x219D: Size(3); NativeRead(0x12B, 8, mode); mode = (byte)((mode & ~8) | (Flag(0x8000) ? 8 : 0)); Write(0x12B, 8, mode); break;
                case 0x21A0: Size(3); Add(100); break;
                case 0x21A3: case 0x21A7: case 0x21AB: Branch(Flag(0x8000), 0x21B1); break;
                case 0x21A5: Size(2); Add(Read(0x144, 16, s.Source0144)); break;
                case 0x21A9: Size(2); Add(Read(0x14A, 16, s.Source014a)); break;
                case 0x21AD: Size(2); Add(Read(0x14C, 16, s.Source014c)); break;
                case 0x21AF: Branch(!Flag(0x8000), 0x21B4); break;
                case 0x21B1: Size(3); Load(65535, true); break;
                case 0x21B4: r0 = a; Write(0x100, 16, r0); break;
                case 0x21B5: Size(2); Load(Read(0x148, 8, s.Source0148), false); break;
                case 0x21B7: case 0x21C0: a = unchecked((ushort)(short)(sbyte)(a & 255)); FlagSet(0x1000, true); break;
                case 0x21B8: Size(3); r3 = Read(0x146, 16, s.Source0146); Write(0x106, 16, r3); break;
                case 0x21BB: case 0x21C1: Size(3); ret = next; Write(0x7FE, 16, ret); ssp -= 2; next = 0x596C; break;
                case 0x21BE: Size(2); Load(Read(0x149, 8, s.Source0149), false); break;
                case 0x21C4: case 0x21D1: Size(3); lhs = a; rhs = 32768; Compare(lhs, rhs); break;
                case 0x21C7: Branch(!Flag(0x8000), 0x21CE); break;
                case 0x21C9: case 0x21CE: Add(NativeRead(0x100, 16, r0)); break;
                case 0x21CA: Branch(!Flag(0x8000), 0x21D1); break;
                case 0x21CC: Size(2); next = 0x21D6; break;
                case 0x21CF: Branch(!Flag(0x8000), 0x21D9); break;
                case 0x21D4: Branch(Flag(0x8000), 0x21D9); break;
                case 0x21D6: Size(3); Load(32767, true); break;
                case 0x21D9: r3 = a; Write(0x106, 16, r3); break;
                case 0x21DA: Write(0x8A, 16, a); break;
                case 0x596C: case 0x5975: case 0x5986: case 0x5958: Rol(); break;
                case 0x596D: Branch(Flag(0x8000), 0x5980); break;
                case 0x596F: case 0x5980: case 0x598E: case 0x595B: case 0x5962: Ror(); break;
                case 0x5970: case 0x5981: Size(2); FlagSet(0x8000, (NativeRead(0x107, 8, r3 >> 8) & 0x80) != 0); break;
                case 0x5972: Branch(Flag(0x8000), 0x597D); break;
                case 0x5983: Branch(!Flag(0x8000), 0x597D); break;
                case 0x5974: case 0x597D: case 0x5985: case 0x595C: case 0x5963: Add(NativeRead(0x106, 16, r3)); break;
                case 0x5976: Branch(!Flag(0x8000), 0x598E); break;
                case 0x5987: Branch(Flag(0x8000), 0x598E); break;
                case 0x5978: Size(3); Load(32767, true); break;
                case 0x5989: Size(3); Load(32768, true); break;
                case 0x597B: case 0x597E: case 0x598C: case 0x598F: case 0x5960: case 0x5969: r3 = a; Write(0x106, 16, r3); break;
                case 0x597C: case 0x597F: case 0x598D: case 0x5990: case 0x5961: case 0x596A: ssp += 2; next = NativeRead(0x7FE, 16, ret); break;
                case 0x21DB: Size(2); Load(Read(0x140, 16, lookup), true); break;
                case 0x21DD: Size(3); r0 = Read(0x158, 16, s.Factor0158); Write(0x100, 16, r0); break;
                case 0x21E0: Size(2); var product = (ulong)a * (uint)NativeRead(0x100, 16, r0); a = (int)(product & 65535); r1 = (int)(product >> 16); Write(0x102, 16, r1); FlagSet(0x4000, product == 0); break;
                case 0x21E2: Size(2); NativeRead(0x102, 16, r1); FlagSet(0x8000, (r1 & 1) != 0); r1 >>= 1; Write(0x102, 16, r1); break;
                case 0x21E4: Ror(); break;
                case 0x21E5: Load(NativeRead(0x102, 8, r1 & 255), false); break;
                case 0x21E6: Size(2); Load(a, true); break;
                case 0x21E8: a = (a >> 8) | ((a & 255) << 8); break;
                case 0x21E9: Size(3); lhs = NativeRead(0x103, 8, r1 >> 8); rhs = 0; Compare(lhs, rhs); break;
                case 0x21EC: Branch(Flag(0x4000), 0x21F1); break;
                case 0x21EE: Size(3); Load(65535, true); break;
                case 0x21F1: r2 = a; Write(0x104, 16, r2); break;
                case 0x21F2: Size(2); var old = a; a = NativeRead(0x106, 16, r3); r3 = old; Write(0x106, 16, r3); break;
                case 0x21F4: ret = next; Write(0x7FE, 16, ret); ssp -= 2; next = 0x5958; break;
                case 0x5959: Branch(!Flag(0x8000), 0x5962); break;
                case 0x595D: Branch(Flag(0x8000), 0x5960); break;
                case 0x595F: case 0x21F8: Load(0, true); break;
                case 0x5964: Branch(!Flag(0x8000), 0x5969); break;
                case 0x5966: Size(3); Load(65535, true); break;
                case 0x21F5: Size(3); if ((NativeRead(0x124, 8, gate) & 0x20) == 0) next = 0x21F9; break;
                case 0x21F9: Size(3); dp = 0x3A2; Write(0x8C, 16, dp); break;
                case 0x21FC: NativeRead(0x8C, 16, dp); Write(dp, 16, a); break;
                case 0x21FD: Load(NativeRead(0x106, 16, r3), true); break;
                case 0x21FE: Size(3); dp = 0x3B4; Write(0x8C, 16, dp); break;
                case 0x2201: Size(2); NativeRead(0x8C, 16, dp); r0 = NativeRead(0x3B4, 16, previousStore); Write(0x100, 16, r0); break;
                case 0x2203: NativeRead(0x8C, 16, dp); Write(dp, 16, a); break;
                default: throw new InvalidOperationException($"Unmodelled M2l path {pc:X4}.");
            }
            events.Add([pc, next, beforeA, a, beforePsw, psw, lhs, rhs]); accessEnds.Add(accesses.Count); registerEnds.Add([r0, r1, r2, r3]); stackEnds.Add(ssp); lengths.Add(length); pc = next;
        }
        return new(events.AsReadOnly(), writes.AsReadOnly(), reads.AsReadOnly(), accesses.AsReadOnly(), accessEnds.AsReadOnly(), registerEnds.AsReadOnly(), stackEnds.AsReadOnly(), lengths.AsReadOnly(), a, psw, r0, r1, r2, r3, mode);
    }
    internal static void RequireEventPrefix(JsonElement stage, P28FuelAdditiveOracle own)
    {
        var rows = stage.GetProperty("events"); Require(rows.GetArrayLength() <= own.Events.Count, "Extra M2l native instructions.");
        for (var i = 0; i < rows.GetArrayLength(); i++) Require(rows[i].EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(own.Events[i]), "M2l own-source operand/flag/control-flow oracle differs.");
    }
}
