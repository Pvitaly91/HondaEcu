using System.Text.Json;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

internal sealed record P28FuelFactorOracle(IReadOnlyList<int[]> Events, IReadOnlyList<int[]> Writes,
    IReadOnlyList<int[]> SourceReads, IReadOnlyList<int[]> Accesses, IReadOnlyList<int> AccessEnds,
    IReadOnlyList<int> WriteEnds, IReadOnlyList<int[]> RegisterEnds, IReadOnlyList<int> Lengths,
    int Accumulator, int Psw, int Er0, int Er1, int Er2, int Er3, byte Hysteresis);

/// <summary>Independent per-instruction producer path from own sources and caller state, not observed factor/register outputs.</summary>
internal static class P28FuelFactorEvidence
{
    internal static P28FuelFactorOracle Build(P28FuelFactorSources s, byte producerMode012c, byte producerSelector012f,
        byte hysteresis0130, int entryA, int entryPsw, int initialEr0, int initialEr1, int initialEr2, int initialEr3)
    {
        var pc = 0x1F43; var a = entryA; var psw = entryPsw; int[] registers = [initialEr0, initialEr1, initialEr2, initialEr3];
        var events = new List<int[]>(); var writes = new List<int[]>(); var sourceReads = new List<int[]>(); var accesses = new List<int[]>();
        var accessEnds = new List<int>(); var writeEnds = new List<int>(); var registerEnds = new List<int[]>(); var lengths = new List<int>();
        bool Flag(int bit) => (psw & bit) != 0;
        void SetFlag(int bit, bool value) => psw = value ? psw | bit : psw & ~bit;
        void Load(int value, bool word) { a = word ? value : (a & 0xFF00) | value; SetFlag(0x1000, word); SetFlag(0x4000, value == 0); }
        int Read(int address, int width, int value, bool source = false)
        { var row = new[] { pc, address, width, 0, value }; accesses.Add(row); if (source) sourceReads.Add(row); return value; }
        void Write(int address, int width, int value) { writes.Add([address, width, value]); accesses.Add([pc, address, width, 1, value]); }
        int Word(int n) => Read(0x100 + n * 2, 16, registers[n]);
        int Byte(int n) => Read(0x100 + n, 8, (registers[n / 2] >> ((n & 1) * 8)) & 255);
        void WriteWord(int n, int value) { registers[n] = value & 65535; Write(0x100 + n * 2, 16, registers[n]); }
        void WriteByte(int n, int value)
        { var shift = (n & 1) * 8; registers[n / 2] = (registers[n / 2] & ~(255 << shift)) | ((value & 255) << shift); Write(0x100 + n, 8, value & 255); }
        void Multiply() { var product = (uint)a * (uint)Word(0); a = (int)(product & 65535); WriteWord(1, (int)(product >> 16)); SetFlag(0x4000, product == 0); }
        void ShiftRightWord(int n) { var old = Word(n); SetFlag(0x8000, (old & 1) != 0); WriteWord(n, old >> 1); }
        void RotateRightA() { var old = a; a = (a >> 1) | (Flag(0x8000) ? 32768 : 0); SetFlag(0x8000, (old & 1) != 0); }
        void ShiftLeftA() { var old = a; a = (a << 1) & 65535; SetFlag(0x8000, (old & 32768) != 0); }
        void RotateLeftWord(int n) { var old = Word(n); var next = ((old << 1) | (Flag(0x8000) ? 1 : 0)) & 65535; SetFlag(0x8000, (old & 32768) != 0); WriteWord(n, next); }
        while (pc != 0x1FB7)
        {
            if (events.Count >= 96) throw new InvalidOperationException("Independent M2m producer oracle exceeded its finite path.");
            var beforeA = a; var beforePsw = psw; var next = pc + 1; var length = 1; var lhs = 65536; var rhs = 65536;
            void Size(int n) { length = n; next = pc + n; }
            void Branch(bool take, int destination) { Size(2); if (take) next = destination; }
            switch (pc)
            {
                case 0x1F43: Size(2); Load(Read(0x164, 8, s.Source0164, true), false); break;
                case 0x1F45: Size(3); if ((Read(0x12F, 8, producerSelector012f, true) & 0x80) != 0) next = 0x1F4A; break;
                case 0x1F48: Size(2); Load(Read(0x165, 8, s.Source0165, true), false); break;
                case 0x1F4A: WriteByte(1, a & 255); break;
                case 0x1F4B: Size(2); WriteByte(0, 0); break;
                case 0x1F4D: Size(2); ShiftRightWord(0); break;
                case 0x1F4F: Size(2); Load(Read(0x166, 8, s.Source0166, true), false); break;
                case 0x1F51: Branch(Flag(0x4000), 0x1F5A); break;
                case 0x1F53: case 0x1F5E: Size(2); a = ((a & 255) << 8) | (a & 255); break;
                case 0x1F55: case 0x1F60: a &= 0xFF00; SetFlag(0x1000, false); SetFlag(0x4000, true); break;
                case 0x1F56: case 0x1F61: case 0x1F6B: case 0x1F74: case 0x1F7A: case 0x1F90: case 0x1FAC: case 0x1FB2: Size(2); Multiply(); break;
                case 0x1F58: case 0x1F63: case 0x1F76: case 0x1F92: case 0x1FAE: Size(2); WriteWord(0, Word(1)); break;
                case 0x1F5A: Size(2); Load(Read(0x167, 8, s.Source0167, true), false); break;
                case 0x1F5C: Branch(Flag(0x4000), 0x1F65); break;
                case 0x1F65: Size(4); a = 0x100 | (a & 255); break;
                case 0x1F69: Size(2); Load(Read(0x168, 8, s.Source0168, true), false); break;
                case 0x1F6D: case 0x1F82: Size(2); WriteByte(1, Byte(2)); break;
                case 0x1F6F: case 0x1F84: Size(3); WriteByte(0, a >> 8); break;
                case 0x1F72: Size(2); Load(Read(0x162, 16, s.Source0162, true), true); break;
                case 0x1F78: Size(2); Load(Read(0x160, 16, s.Source0160, true), true); break;
                case 0x1F7C: case 0x1F7F: Size(2); ShiftRightWord(1); break;
                case 0x1F7E: case 0x1F81: RotateRightA(); break;
                case 0x1F87: Load(Byte(3), false); break;
                case 0x1F88: Branch(Flag(0x4000), 0x1F8E); break;
                case 0x1F8A: case 0x1FA6: Size(4); WriteWord(0, 65535); break;
                case 0x1F8E: Size(2); Load(Read(0x15E, 16, s.Source015e, true), true); break;
                case 0x1F94: Size(3); if ((Read(0x12C, 8, producerMode012c, true) & 0x10) == 0) next = 0x1FB0; break;
                case 0x1F97: case 0x1F9C: case 0x1FA1: ShiftLeftA(); break;
                case 0x1F98: case 0x1F9D: case 0x1FA2: Size(2); RotateLeftWord(0); break;
                case 0x1F9A: case 0x1F9F: Branch(Flag(0x8000), 0x1FA6); break;
                case 0x1FA4: Branch(!Flag(0x8000), 0x1FAA); break;
                case 0x1FAA: Size(2); Load(Read(0x15C, 16, s.Source015c, true), true); break;
                case 0x1FB0: Size(2); Load(Read(0x15A, 16, s.Source015a, true), true); break;
                case 0x1FB4: Size(3); next = 0x7A99; break;
                case 0x7A99: Size(3); Write(0x158, 16, Word(1)); break;
                case 0x7A9C: Size(2); Load(0x66, false); break;
                case 0x7A9E: Size(3); if ((Read(0x130, 8, hysteresis0130, true) & 0x40) != 0) next = 0x7AA3; break;
                case 0x7AA1: Size(2); Load(0x6A, false); break;
                case 0x7AA3: Size(2); lhs = a & 255; rhs = Read(0x133, 8, s.Source0133, true); SetFlag(0x8000, lhs < rhs); SetFlag(0x4000, lhs == rhs); break;
                case 0x7AA5: Size(3); Read(0x130, 8, hysteresis0130); hysteresis0130 = (byte)((hysteresis0130 & ~0x40) | (Flag(0x8000) ? 0x40 : 0)); Write(0x130, 8, hysteresis0130); break;
                case 0x7AA8: Size(3); next = 0x1FB7; break;
                default: throw new InvalidOperationException($"Unmodelled M2m producer path {pc:X4}.");
            }
            events.Add([pc, next, beforeA, a, beforePsw, psw, lhs, rhs]); accessEnds.Add(accesses.Count); writeEnds.Add(writes.Count); registerEnds.Add(registers.ToArray()); lengths.Add(length); pc = next;
        }
        return new(events.AsReadOnly(), writes.AsReadOnly(), sourceReads.AsReadOnly(), accesses.AsReadOnly(), accessEnds.AsReadOnly(), writeEnds.AsReadOnly(), registerEnds.AsReadOnly(), lengths.AsReadOnly(), a, psw,
            registers[0], registers[1], registers[2], registers[3], hysteresis0130);
    }
    internal static void RequireEventPrefix(JsonElement stage, P28FuelFactorOracle own)
    {
        var rows = stage.GetProperty("events"); Require(rows.GetArrayLength() <= own.Events.Count, "Extra M2m native producer instructions.");
        for (var i = 0; i < rows.GetArrayLength(); i++) Require(rows[i].EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(own.Events[i]), "M2m own-source operand/flag/control-flow oracle differs.");
    }
}
