namespace HondaEcu.Core;

internal sealed record P28Data0136TechnicalStep(int[] Event, string Form, int Length, int[] RamAfter, int AccessEnd, int WriteEnd, int PeripheralEnd);
internal sealed record P28Data0136TechnicalOracle(IReadOnlyList<P28Data0136TechnicalStep> Steps, IReadOnlyList<int[]> Accesses,
    IReadOnlyList<int[]> Writes, IReadOnlyList<int[]> PeripheralReads, int[] RamBefore, int[] EntryRam, int EntryA, int[] SourceApplications,
    int SelectedSample, uint? Dividend, string ZeroCause);

/// <summary>Own persistent memory, arithmetic, flags and per-instruction evidence from declared sources ONLY.</summary>
internal sealed class P28Data0136TechnicalProducerModel
{
    internal static readonly int[] RamAddresses = new (int A, int B)[] { (0x90,0x98), (0xA2,0xA3), (0xAE,0xAF), (0xB6,0xB7), (0xEE,0xF2),
        (0x108,0x110), (0x11F,0x120), (0x128,0x129), (0x136,0x138), (0x360,0x36C) }.SelectMany(r => Enumerable.Range(r.A, r.B - r.A)).ToArray();
    private readonly int[] _ram = new int[0x400];
    internal int A { get; private set; }
    internal int Psw { get; private set; } = 0x1DCA;
    internal int Pc { get; private set; } = 0x56BE;
    internal int Word(int address) => _ram[address] | (_ram[address + 1] << 8);
    internal int[] Snapshot() => RamAddresses.Select(a => _ram[a]).ToArray();
    private void SeedWord(int address, int value) { _ram[address] = value & 255; _ram[address + 1] = value >> 8; }
    internal P28Data0136TechnicalProducerModel(P28Data0136TechnicalInitialState s, int scratch)
    {
        Array.Fill(_ram, scratch); A = scratch * 257; SeedWord(0x96, 0x280); SeedWord(0xEE, s.Previous00ee); SeedWord(0x136, s.History0136);
        _ram[0xAE] = s.Counter00ae; _ram[0xB6] = s.Data00b6; _ram[0x11F] = s.Data011f; _ram[0x128] = s.Data0128;
        for (var i = 0; i < 6; i++) SeedWord(0x360 + i * 2, s.Samples[i]);
    }
    internal P28Data0136TechnicalOracle Run(P28Data0136TechnicalObservation o, int maximumSteps = 128)
    {
        var before = Snapshot(); Psw = 0x1DCA; Pc = 0x56BE; SeedWord(0x96, 0x280); _ram[0xA2] = o.Slot;
        if (o.Source00f0 is ushort source) SeedWord(0xF0, source);
        var entry = Snapshot(); var entryA = A;
        int[] applications = o.Source00f0 is ushort f0 ? [0xA2, 8, o.Slot, 0xF0, 16, f0] : [0xA2, 8, o.Slot];
        var events = new List<P28Data0136TechnicalStep>(); var accesses = new List<int[]>(); var writes = new List<int[]>(); var peripheral = new List<int[]>();
        var selected = o.Source00f0 ?? o.Tmr2; uint? dividend = null; var zeroCause = "None";
        bool Flag(int bit) => (Psw & bit) != 0;
        void Set(int bit, bool value) => Psw = value ? Psw | bit : Psw & ~bit;
        void Load(int value, bool word) { A = word ? value : (A & 0xFF00) | value; Set(0x1000, word); Set(0x4000, value == 0); }
        int Read(int address, int width) { var v = width == 16 ? Word(address) : _ram[address]; accesses.Add([Pc, address, width, 0, v]); return v; }
        void Write(int address, int width, int value) { if (width == 16) SeedWord(address, value); else _ram[address] = value & 255; accesses.Add([Pc, address, width, 1, value]); writes.Add([address, width, value]); }
        int Peripheral(int address, int width, int value) { peripheral.Add([address, width, 0, value]); return value; }
        void TestSet(int address, int mask) { var old = Read(address, 8); Set(0x4000, (old & mask) == 0); Write(address, 8, Read(address, 8) | mask); }
        while (Pc != 0x5719 && events.Count < maximumSteps)
        {
            var a = A; var psw = Psw; var next = Pc + 1; var length = 1; var form = ""; var lhs = 65536; var rhs = 65536;
            void Size(int n, string name) { length = n; next = Pc + n; form = name; }
            void Branch(bool take, int dest, string name) { Size(2, name); if (take) next = dest; }
            switch (Pc)
            {
                case 0x56BE: Size(2, "L A, N8"); Load(Peripheral(0x3A, 16, o.Tmr2), true); break;
                case 0x56C0: Size(3, "JBR off N8.2, rel8"); if ((Read(0x11F, 8) & 4) == 0) next = 0x56C5; break;
                case 0x56C3: Size(2, "L A, N8"); Load(Read(0xF0, 16), true); break;
                case 0x56C5: form = "ST A, er3"; Write(0x10E, 16, A); break;
                case 0x56C6: Size(3, "JBS off N8.7, rel8"); if ((Read(0x10F, 8) & 128) != 0) next = 0x56D4; break;
                case 0x56C9: Size(3, "MB C, N8.0"); Set(0x8000, (Peripheral(0x19, 8, o.Irqh) & 1) != 0); break;
                case 0x56CC: Branch(!Flag(0x8000), 0x56D4, "JGE rel8"); break;
                case 0x56CE: Size(3, "INCB N8"); var old = Read(0xAE, 8); var inc = (old + 1) & 255; Set(0x4000, inc == 0); Set(0x2000, (old & 15) == 15); Write(0xAE, 8, inc); break;
                case 0x56D1: Size(3, "SB N8.0"); TestSet(0xB6, 1); break;
                case 0x56D4: Size(3, "SB off N8.3"); TestSet(0x128, 8); break;
                case 0x56D7: Branch(Flag(0x4000), 0x5713, "JEQ rel8"); break;
                case 0x56D9: Size(3, "SUB A, N8"); var p = Read(0xEE, 16); A = (a - p) & 65535; Set(0x8000, a < p); Set(0x4000, A == 0); Set(0x2000, (a & 15) < (p & 15)); if (A == 0) zeroCause = "EqualDeltaZero"; break;
                case 0x56DC: Size(3, "JBR off N8.2, rel8"); if ((Read(0x11F, 8) & 4) == 0) next = 0x5701; break;
                case 0x56DF: Size(2, "CLRB r1"); Write(0x109, 8, 0); break;
                case 0x56E1: Size(3, "MOVB r0, N8"); Write(0x108, 8, Read(0xAE, 8)); break;
                case 0x56E4: Size(3, "SBCB r0, #N8"); var c = Read(0x108, 8); var borrow = Flag(0x8000) ? 1 : 0; var high = (c - borrow) & 255; Set(0x8000, c < borrow); Set(0x4000, high == 0); Set(0x2000, (c & 15) < borrow); Write(0x108, 8, high); break;
                case 0x56E7: Size(4, "MOV er2, #N16"); Write(0x10C, 16, 6); break;
                case 0x56EB: Size(2, "DIV"); var divisor = Read(0x10C, 16); var upper = Read(0x108, 16); dividend = ((uint)upper << 16) | (uint)A; var q = dividend.Value / (uint)divisor; Write(0x108, 16, (int)(q >> 16)); A = (int)(q & 65535); Write(0x10A, 16, (int)(dividend.Value % (uint)divisor)); Set(0x8000, false); Set(0x4000, q == 0); zeroCause = q > 65535 ? "OverflowToZero" : q == 0 ? "DividendBelowSix" : "None"; break;
                case 0x56ED: Size(3, "CMPB r0, #N8"); lhs = Read(0x108, 8); rhs = 0; Set(0x8000, false); Set(0x4000, lhs == 0); break;
                case 0x56F0: Branch(Flag(0x4000), 0x56F3, "JEQ rel8"); break;
                case 0x56F2: case 0x5706: form = "CLR A"; A = 0; Set(0x1000, true); Set(0x4000, true); break;
                case 0x56F3: case 0x5707: Size(2, "ST A, off N8"); Write(0x136, 16, A); break;
                case 0x56F5: Size(3, "MOV X1, #N16"); Write(0x90, 16, 12); break;
                case 0x56F8: case 0x56F9: form = "DEC X1"; var x = Read(0x90, 16); var dec = (x - 1) & 65535; Set(0x4000, dec == 0); Set(0x2000, (x & 15) == 0); Write(0x90, 16, dec); break;
                case 0x56FA: Size(3, "ST A, N16[X1]"); Write(0x360 + Read(0x90, 16), 16, A); break;
                case 0x56FD: Branch(!Flag(0x4000), 0x56F8, "JNE rel8"); break;
                case 0x56FF: Size(2, "SJ rel8"); next = 0x5713; break;
                case 0x5701: Size(3, "MB C, N8.2"); Set(0x8000, (Peripheral(0x42, 8, o.Tcon2) & 4) != 0); if (Flag(0x8000)) zeroCause = "ControlForcedZero"; break;
                case 0x5704: Branch(!Flag(0x8000), 0x5707, "JGE rel8"); break;
                case 0x5709: Size(2, "LB A, N8"); Load(Read(0xA2, 8), false); break;
                case 0x570B: form = "SLLB A"; Set(0x8000, (A & 128) != 0); A = (A & 0xFF00) | ((A << 1) & 255); break;
                case 0x570C: form = "EXTND"; A = (ushort)(short)(sbyte)(A & 255); Set(0x1000, true); break;
                case 0x570D: form = "MOV X1, A"; Write(0x90, 16, A); break;
                case 0x570E: Size(2, "L A, off N8"); Load(Read(0x136, 16), true); break;
                case 0x5710: Size(3, "ST A, N16[X1]"); Write(0x360 + Read(0x90, 16), 16, A); break;
                case 0x5713: form = "L A, er3"; Load(Read(0x10E, 16), true); break;
                case 0x5714: Size(2, "ST A, N8"); Write(0xEE, 16, A); break;
                case 0x5716: Size(3, "CLRB N8"); Write(0xAE, 8, 0); break;
                default: throw new InvalidOperationException($"Unmodelled M2v PC{Pc:X4}.");
            }
            events.Add(new([Pc, next, a, A, psw, Psw, lhs, rhs], form, length, Snapshot(), accesses.Count, writes.Count, peripheral.Count)); Pc = next;
        }
        return new(events.AsReadOnly(), accesses.AsReadOnly(), writes.AsReadOnly(), peripheral.AsReadOnly(), before, entry, entryA, applications, selected, dividend, zeroCause);
    }
}
