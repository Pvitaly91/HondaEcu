namespace HondaEcu.Core;

internal sealed record P28LimiterDecisionOracle(IReadOnlyList<int[]> Events, IReadOnlyList<int[]> Writes, IReadOnlyList<int[]> Accesses,
    IReadOnlyList<int> AccessEnds, IReadOnlyList<int> WriteEnds, IReadOnlyList<int[]> StateEnds, IReadOnlyList<int> Lengths,
    int Accumulator, int Psw, int Dp);

/// <summary>Independent fixed-context per-PC oracle from own ROM/raw snapshots/shared history.</summary>
internal static class P28LimiterDecisionEvidence
{
    internal static P28LimiterDecisionOracle Build(RomImage image, P28LimiterState initial, ushort rawPeriod, int initialA)
    {
        var cut = P28LimiterInspector.Word(image.Span, 0x196A); var resume = P28LimiterInspector.Word(image.Span, 0x1967);
        var pc = 0x1966; var a = initialA; var psw = 0x0DC9; var dp = 0; var gate = (int)initial.Data0124; var mode = (int)initial.Data012B; var counter = (int)initial.Data01D7;
        var events = new List<int[]>(); var writes = new List<int[]>(); var accesses = new List<int[]>(); var accessEnds = new List<int>(); var writeEnds = new List<int>(); var states = new List<int[]>(); var lengths = new List<int>();
        bool Flag(int mask) => (psw & mask) != 0;
        void FlagSet(int mask, bool on) => psw = on ? psw | mask : psw & ~mask;
        void Load(int value, bool word) { a = word ? value : (a & 0xFF00) | value; FlagSet(0x1000, word); FlagSet(0x4000, value == 0); }
        int Read(int address, int width, int value) { accesses.Add([pc, address, width, 0, value]); return value; }
        void Write(int address, int width, int value) { accesses.Add([pc, address, width, 1, value]); writes.Add([address, width, value]); }
        void GateBit(int mask, bool on, bool zeroFlag = false)
        {
            if (zeroFlag) FlagSet(0x4000, (Read(0x124, 8, gate) & mask) == 0);
            Read(0x124, 8, gate); gate = on ? gate | mask : gate & ~mask; Write(0x124, 8, gate);
        }
        while (pc != 0x1A38)
        {
            if (events.Count >= 40) throw new InvalidOperationException("Fixed decision oracle escaped its bounded path.");
            var beforeA = a; var beforePsw = psw; var length = 1; var next = pc + 1; var lhs = 65536; var rhs = 65536;
            void Size(int n) { length = n; next = pc + n; }
            switch (pc)
            {
                case 0x1966: Size(3); dp = resume; Write(0x8C, 16, dp); break;
                case 0x1969: Size(3); Load(cut, true); break;
                case 0x196C: Size(3); FlagSet(0x8000, false); break; // frozen P4.0=0 SFR observation, not general RAM
                case 0x196F: Size(2); break;
                case 0x1971: Size(3); Read(0x11B, 8, 128); next = 0x1979; break;
                case 0x1979: Size(3); if ((Read(0x124, 8, gate) & 32) == 0) next = 0x197D; break;
                case 0x197C: Load(Read(0x8C, 16, dp), true); break;
                case 0x197D: Size(3); lhs = Read(0xC4, 16, rawPeriod); rhs = a; FlagSet(0x8000, lhs < rhs); FlagSet(0x4000, lhs == rhs); break;
                case 0x1980: Size(2); if (Flag(0x8000)) next = 0x19AC; break;
                case 0x1982: Size(3); Read(0x121, 8, 128); next = 0x19C2; break;
                case 0x19AC: Size(2); FlagSet(0x4000, (psw & 32) == 0); psw |= 32; break;
                case 0x19AE: Size(2); next = 0x1A1E; break;
                case 0x19C2: Size(2); Load(20, false); break;
                case 0x19C4: Size(2); counter = a & 255; Write(0x1D7, 8, counter); break;
                case 0x19C6: Size(3); GateBit(4, false, true); break;
                case 0x19C9: Size(2); next = 0x1A21; break;
                case 0x1A1E: Size(3); GateBit(4, true, true); break;
                case 0x1A21: Size(2); FlagSet(0x8000, (psw & 32) != 0); break;
                case 0x1A23: Size(3); GateBit(32, Flag(0x8000)); break;
                case 0x1A26: Size(2); FlagSet(0x8000, (psw & 16) != 0); break;
                case 0x1A28: Size(3); GateBit(16, Flag(0x8000)); break;
                case 0x1A2B: FlagSet(0x8000, false); break;
                case 0x1A2C: Size(3); FlagSet(0x4000, (Read(0x12B, 8, mode) & 128) == 0); Read(0x12B, 8, mode); mode &= 127; Write(0x12B, 8, mode); break;
                case 0x1A2F: Size(3); if ((Read(0x124, 8, gate) & 4) != 0) next = 0x1A34; break;
                case 0x1A32: Size(2); if (Flag(0x4000)) next = 0x1A35; break;
                case 0x1A34: FlagSet(0x8000, true); break;
                case 0x1A35: Size(3); GateBit(8, Flag(0x8000)); break;
                default: throw new InvalidOperationException("Unmodelled fixed decision PC.");
            }
            events.Add([pc, next, beforeA, a, beforePsw, psw, lhs, rhs]); accessEnds.Add(accesses.Count); writeEnds.Add(writes.Count); states.Add([gate, mode, counter]); lengths.Add(length); pc = next;
        }
        return new(events.AsReadOnly(), writes.AsReadOnly(), accesses.AsReadOnly(), accessEnds.AsReadOnly(), writeEnds.AsReadOnly(), states.AsReadOnly(), lengths.AsReadOnly(), a, psw, dp);
    }
}
