namespace HondaEcu.Core;

internal sealed record P28CommonResultConsumerOracle(P28FuelAdditiveOracle Machine, IReadOnlyList<int> DpEnds,
    IReadOnlyList<int> ModeEnds, IReadOnlyList<int[]> HistoryEnds, IReadOnlyList<int> ProgramReads,
    IReadOnlyList<int> ProgramReadEnds, int StopPc, int Status);
internal static class P28CommonResultConsumerEvidence
{
    // Primary-reviewed software instructions only. JGT is deliberately not a guessed expected branch.
    internal static P28CommonResultConsumerOracle Build(RomImage image, P28PostSelectionCriticalOracle prefix,
        P28CommonResultConsumerState entry, P28PostStoreCall call, int source125 = 0)
    {
        var source = call.Adaptive.Fuel.Sources; var own = prefix.Machine; var a = own.Accumulator; var psw = own.Psw;
        int[] regs = [own.Er0, own.Er1, own.Er2, own.Er3]; var dp = 0x3B4; var mode = (int)entry.Mode012b;
        var historyB = (int)entry.Byte013b; var historyD = (int)entry.Byte013d; var pc = 0x22B1; var ssp = 0x7FE; var ret = 0;
        var events = new List<int[]>(); var writes = new List<int[]>(); var accesses = new List<int[]>(); var reads = new List<int[]>();
        var ends = new List<int>(); var regEnds = new List<int[]>(); var stacks = new List<int>(); var lengths = new List<int>();
        var dpEnds = new List<int>(); var modes = new List<int>(); var histories = new List<int[]>(); var program = new List<int>(); var programEnds = new List<int>();
        bool Flag(int bit) => (psw & bit) != 0;
        void Set(int bit, bool on) => psw = on ? psw | bit : psw & ~bit;
        void Load(int value, bool word) { a = word ? value : (a & 0xFF00) | value; Set(0x1000, word); Set(0x4000, value == 0); }
        int Read(int address, int width, int value) { var row = new[] { pc, address, width, 0, value }; accesses.Add(row); reads.Add(row); return value; }
        void Write(int address, int width, int value) { writes.Add([address, width, value]); accesses.Add([pc, address, width, 1, value]); }
        int Word(int n) => Read(0x100 + n * 2, 16, regs[n]);
        void StoreWord(int n, int value) { regs[n] = value & 65535; Write(0x100 + n * 2, 16, regs[n]); }
        void StoreR6(int value) { regs[3] = (regs[3] & 0xFF00) | (value & 255); Write(0x106, 8, value & 255); }
        void ModeBit(int bit) { Read(0x12B, 8, mode); mode = (mode & ~bit) | (Flag(0x8000) ? bit : 0); Write(0x12B, 8, mode); }
        void Ror() { var old = a; a = (a >> 1) | (Flag(0x8000) ? 0x8000 : 0); Set(0x8000, (old & 1) != 0); }
        while (pc != 0x236C && pc != 0x233A && !(pc == 0x2333 && entry.Word0136 == 0))
        {
            if (events.Count >= 192) throw new InvalidOperationException("M2s oracle escaped bounded software prefix.");
            var oldA = a; var oldPsw = psw; var next = pc + 1; var length = 1; var lhs = 65536; var rhs = 65536;
            void Size(int n) { length = n; next = pc + n; }
            void Branch(bool take, int target) { Size(2); if (take) next = target; }
            void Compare(int left, int right) { lhs = left; rhs = right; Set(0x8000, left < right); Set(0x4000, left == right); }
            void BitBranch(int address, int value, int bit, int target, bool set = true) { Size(3); if (((Read(address, 8, value) & bit) != 0) == set) next = target; }
            switch (pc)
            {
                case 0x22B1: Size(2); Load(197, false); break;
                case 0x22B3: BitBranch(0x12B, mode, 4, 0x22B8); break;
                case 0x22B6: Size(2); Load(200, false); break;
                case 0x22B8: Size(2); Compare(a & 255, Read(0x133, 8, source.Source0133)); break;
                case 0x22BA: Size(3); ModeBit(4); break;
                case 0x22BD: Size(2); Load(Read(0x13D, 8, historyD), false); break;
                case 0x22BF: Branch(!Flag(0x4000), 0x2318); break;
                case 0x22C1: Size(2); Load(5, false); break;
                case 0x22C3: BitBranch(0x125, source125, 16, 0x2325); break;
                case 0x22C6: Size(2); StoreR6(7); break;
                case 0x22C8: Size(2); Load(Read(0x11A, 16, entry.Word011a), true); break;
                case 0x22CA: Size(3); a &= 0x1034; Set(0x4000, a == 0); break;
                case 0x22CD: Branch(!Flag(0x4000), 0x2327); break;
                case 0x22CF: case 0x22D4: Size(2); StoreR6(6); break;
                case 0x22D1: BitBranch(0x11F, entry.Byte011f, 32, 0x2327); break;
                case 0x22D6: BitBranch(0x12C, entry.Prefix.Mode012c, 32, 0x2327); break;
                case 0x22D9: Size(4); Compare(Read(0xD9, 8, call.Adaptive.RawD9), 46); break;
                case 0x22DD: Branch(!Flag(0x8000), 0x22E4); break;
                case 0x22DF: Size(2); StoreR6(7); break;
                case 0x22E1: BitBranch(0x120, entry.Byte0120, 1, 0x2327); break;
                case 0x22E4: Size(2); dp = 0; Write(0x8C, 16, 0); break;
                case 0x22E6: Size(2); Load(Read(0xD9, 8, call.Adaptive.RawD9), false); break;
                case 0x22E8: Size(2); Compare(a & 255, 174); break;
                case 0x22EA: Branch(Flag(0x8000), 0x22F0); break;
                case 0x22EC:
                    Size(4); var previousDp = Read(0x8C, 16, dp); dp = (previousDp + 3) & 65535; Set(0x8000, previousDp + 3 > 65535); Set(0x4000, dp == 0); Set(0x2000, (previousDp & 15) + 3 > 15); Write(0x8C, 16, dp); break;
                case 0x22F0: Size(2); Load(56, false); break;
                case 0x22F2: BitBranch(0x12B, mode, 2, 0x22F7); break;
                case 0x22F5: Size(2); Load(48, false); break;
                case 0x22F7: Size(3); Compare(Read(0xBE, 8, entry.Byte00be), a & 255); break;
                case 0x22FA: Size(3); ModeBit(2); break;
                case 0x22FD: Size(2); Load(119, false); break;
                case 0x22FF: BitBranch(0x12B, mode, 1, 0x2304); break;
                case 0x2302: Size(2); Load(112, false); break;
                case 0x2304: Size(3); Compare(Read(0xBE, 8, entry.Byte00be), a & 255); break;
                case 0x2307: Size(3); ModeBit(1); break;
                case 0x230A: Branch(!Flag(0x8000), 0x2311); break;
                case 0x230C:
                case 0x2310:
                    var oldDp = Read(0x8C, 16, dp); dp = (dp + 1) & 65535; Set(0x4000, dp == 0); Set(0x2000, (oldDp & 15) == 15); Write(0x8C, 16, dp); break;
                case 0x230D: BitBranch(0x12B, mode, 2, 0x2311, false); break;
                case 0x2311:
                    Size(4); Read(0x8C, 16, dp); if (dp is < 0 or > 5) throw new InvalidOperationException("Native table index escaped0..5.");
                    program.Add(0x6106 + dp); a = (a & 0xFF00) | image.Span[0x6106 + dp]; Set(0x4000, (a & 255) == 0); break;
                case 0x2315: StoreR6(a & 255); break;
                case 0x2316: Size(2); next = 0x2327; break;
                case 0x2318: Size(3); Set(0x8000, (Read(0xB7, 8, entry.Byte00b7) & 1) != 0); break;
                case 0x231B: Branch(!Flag(0x8000), 0x231F); break;
                case 0x231D: Size(2); Load(5, false); break;
                case 0x231F:
                    Size(2); var oldLow = a & 255; var low = (oldLow - 1) & 255; a = (a & 0xFF00) | low; Set(0x8000, oldLow < 1); Set(0x4000, low == 0); Set(0x2000, (oldLow & 15) < 1); break;
                case 0x2321: Size(2); historyD = a & 255; Write(0x13D, 8, historyD); break;
                case 0x2323: Size(2); Load(11, false); break;
                case 0x2325: Size(2); next = 0x236A; break;
                case 0x2327: Size(3); dp = 0x3B4; Write(0x8C, 16, dp); break;
                case 0x232A: Read(0x8C, 16, dp); Load(Read(0x3B4, 16, entry.Prefix.Word03b4), true); break;
                case 0x232B: Size(3); ret = next; Write(0x7FE, 16, ret); ssp -= 2; next = 0x5991; break;
                case 0x232E: Size(2); StoreWord(0, 0); break;
                case 0x2330: Size(3); StoreWord(2, Read(0x136, 16, entry.Word0136)); break;
                case 0x2333:
                    Size(2); var divisor = Word(2); var dividend = ((uint)Word(0) << 16) | (uint)a; var quotient = dividend / (uint)divisor;
                    StoreWord(0, (int)(quotient >> 16)); a = (int)(quotient & 65535); StoreWord(1, (int)(dividend % (uint)divisor)); Set(0x8000, false); Set(0x4000, quotient == 0); break;
                case 0x2335: Branch(Flag(0x8000), 0x2369); break;
                case 0x2337: Size(3); Compare(a, 11); break;
                case 0x2369: a &= 0xFF00; Set(0x1000, false); Set(0x4000, true); break;
                case 0x236A: Size(2); historyB = a & 255; Write(0x13B, 8, historyB); break;
                case 0x5991: Size(4); StoreWord(0, 5); break;
                case 0x5995: Size(2); var product = (uint)a * (uint)Word(0); a = (int)(product & 65535); StoreWord(1, (int)(product >> 16)); Set(0x4000, product == 0); break;
                case 0x5997: case 0x599A: Size(2); var oldWord = Word(1); Set(0x8000, (oldWord & 1) != 0); StoreWord(1, oldWord >> 1); break;
                case 0x5999: case 0x599C: Ror(); break;
                case 0x599D: Size(3); Compare(Read(0x102, 8, regs[1] & 255), 0); break;
                case 0x59A0: Branch(Flag(0x4000), 0x59A5); break;
                case 0x59A2: Size(3); Load(65535, true); break;
                case 0x59A5: ssp += 2; next = Read(0x7FE, 16, ret); break;
                default: throw new InvalidOperationException($"Unreviewed M2s PC{pc:X4}; no fabricated scheduler jump.");
            }
            events.Add([pc, next, oldA, a, oldPsw, psw, lhs, rhs]); ends.Add(accesses.Count); regEnds.Add(regs.ToArray()); stacks.Add(ssp); lengths.Add(length);
            dpEnds.Add(dp); modes.Add(mode); histories.Add([historyB, historyD]); programEnds.Add(program.Count); pc = next;
        }
        var machine = new P28FuelAdditiveOracle(events.AsReadOnly(), writes.AsReadOnly(), reads.AsReadOnly(), accesses.AsReadOnly(), ends.AsReadOnly(), regEnds.AsReadOnly(), stacks.AsReadOnly(), lengths.AsReadOnly(), a, psw, regs[0], regs[1], regs[2], regs[3], (byte)mode);
        return new(machine, dpEnds.AsReadOnly(), modes.AsReadOnly(), histories.AsReadOnly(), program.AsReadOnly(), programEnds.AsReadOnly(), pc, pc == 0x236C ? 0 : 1);
    }
}
