using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

internal sealed record P28CallerStep(int[] Event, string Form, int Length, int AccessEnd);
internal sealed record P28CallerOracle(JsonElement After, List<P28CallerStep> Steps, List<int[]> All, int[] Memory, string Route, int[] InitialMemory);
internal static class P28FallthroughData0136Model
{
    internal static int[] RetainedMemory(int pattern, JsonElement ownBoundary, Dictionary<int, int> ownedRam, bool fixedSource)
    {
        var ram = Enumerable.Repeat(pattern, 0x800).ToArray();
        foreach (var (a, v) in ownedRam) if (a < ram.Length) ram[a] = v;
        // Existing integrated limiter initialization owns low7=0; adaptive's
        // masked fixedSource application subsequently owns bit7. Not a new source.
        ram[0x11B] = fixedSource ? 128 : 0;
        // These producer histories have no admitted upstream writer; scratch is
        // their explicit existing technical history, not new scenario input.
        foreach (var a in new[] { 0xA2, 0xAE, 0xB6, 0xEE, 0xEF, 0xF0, 0xF1, 0x11F, 0x136, 0x137 }) ram[a] = pattern;
        foreach (var (name, address) in new[] { ("x1", 0x90), ("x2", 0x92), ("dp", 0x94), ("usp", 0x96) }) WriteWord(ram, address, ownBoundary.GetProperty(name).GetInt32());
        var registers = ownBoundary.GetProperty("registers").EnumerateArray().Select(v => v.GetInt32()).ToArray(); Array.Copy(registers, 0, ram, 0x108, 8);
        WriteWord(ram, ownBoundary.GetProperty("ssp").GetInt32(), 0x063E); // independently completed063B frame
        return ram;
    }
    internal static int Word(int[] ram, int a) => ram[a] | ram[a + 1] << 8;
    internal static void WriteWord(int[] ram, int a, int v) { ram[a] = v & 255; ram[a + 1] = v >> 8 & 255; }
    internal static int[] Snapshot(int[] ram) => new (int A, int B)[] { (0x90, 0x98), (0xA2, 0xA3), (0xAE, 0xAF), (0xB6, 0xB7), (0xEE, 0xF2), (0x108, 0x110), (0x11F, 0x120), (0x128, 0x129), (0x136, 0x138), (0x360, 0x36C) }.SelectMany(r => Enumerable.Range(r.A, r.B - r.A)).Select(a => ram[a]).ToArray();
    internal static P28CallerOracle Caller(JsonElement before, int[] initial)
    {
        Require(before.GetProperty("pc").GetInt32() == 0x064C && before.GetProperty("lrb").GetInt32() == 0x21 && !before.GetProperty("dd").GetBoolean() && (before.GetProperty("psw").GetInt32() & 7) == 2, "Caller is not independent actual M2ae exit.");
        var ram = (int[])initial.Clone(); var a = before.GetProperty("accumulator").GetInt32(); var psw = before.GetProperty("psw").GetInt32(); var ssp = before.GetProperty("ssp").GetInt32(); var pc = 0x064C;
        Require((ssp & 1) == 0 && ssp is >= 0x700 and <= 0x7FE, "Unsafe retained caller SSP.");
        var steps = new List<P28CallerStep>(); var all = new List<int[]>(); var route = "FallthroughVia012A0";
        while (pc is not (0x56BE or 0x0657 or 0x0667))
        {
            var oldP = psw; var next = pc; var form = ""; var length = 0;
            void Read(int address, int width = 8) => all.Add([0, pc, address, width, 0, width == 8 ? ram[address] : Word(ram, address)]);
            void Reset(int bit) { var old = ram[0x12A]; Read(0x12A); Read(0x12A); psw = (old & bit) == 0 ? psw | 16384 : psw & ~16384; ram[0x12A] &= ~bit; all.Add([0, pc, 0x12A, 8, 1, ram[0x12A]]); }
            switch (pc)
            {
                case 0x064C: length = 3; form = "JBS off N8.3, rel8"; Read(0x11F); next = (ram[0x11F] & 8) != 0 ? 0x065F : 0x064F; if (next == 0x065F) route = "PrimaryTakenCalSkippedControl"; break;
                case 0x064F: length = 3; form = "JBS off N8.7, rel8"; Read(0x11B); next = (ram[0x11B] & 128) != 0 ? 0x065F : 0x0652; if (next == 0x065F) route = "FallthroughDirectVia011B7"; break;
                case 0x0652: length = 3; form = "RB off N8.0"; Reset(1); next = 0x0655; break;
                case 0x0655: length = 2; form = "JEQ rel8"; next = (psw & 16384) != 0 ? 0x065F : 0x0657; break;
                case 0x065F: length = 3; form = "RB off N8.3"; Reset(8); next = 0x0662; break;
                case 0x0662: length = 2; form = "JNE rel8"; next = (psw & 16384) == 0 ? 0x0667 : 0x0664; break;
                case 0x0664: length = 3; form = "CAL addr16"; WriteWord(ram, ssp, 0x0667); all.Add([0, pc, ssp, 16, 1, 0x0667]); ssp -= 2; next = 0x56BE; break;
                default: throw new InvalidDataException("Unadmitted caller PC.");
            }
            steps.Add(new([pc, next, a, a, oldP, psw, 65536, 65536], form, length, all.Count)); pc = next;
        }
        var after = JsonNode.Parse(before.GetRawText())!; after["pc"] = pc; after["psw"] = psw; after["ssp"] = ssp;
        return new(JsonSerializer.SerializeToElement(after), steps, all, ram, route, (int[])initial.Clone());
    }
    internal static P28CallerOracle NoWrite(JsonElement before, int[] initial, P28FrozenNoWriteObservation o)
    {
        Require(before.GetProperty("pc").GetInt32() == 0x56BE && initial[0x11F] == 0 && initial[0xA2] == 0 && (initial[0x128] & 8) == 0, "Unowned mode/slot or manufactured fresh producer gate.");
        o.Validate(); var ram = (int[])initial.Clone(); var a = before.GetProperty("accumulator").GetInt32(); var psw = before.GetProperty("psw").GetInt32(); var pc = 0x56BE;
        var steps = new List<P28CallerStep>(); var all = new List<int[]>();
        void Flag(int bit, bool value) => psw = value ? psw | bit : psw & ~bit;
        while (pc != 0x5719)
        {
            var oldA = a; var oldP = psw; var next = pc; var length = 0; var form = "";
            int Read(int address, int width = 8) { var v = width == 8 ? ram[address] : Word(ram, address); all.Add([0, pc, address, width, 0, v]); return v; }
            void Write(int address, int width, int value) { if (width == 16) WriteWord(ram, address, value); else ram[address] = value; all.Add([0, pc, address, width, 1, value]); }
            void Load(int value) { a = value; Flag(4096, true); Flag(16384, value == 0); }
            void SetBit(int address, int bit) { var old = Read(address); Flag(16384, (old & bit) == 0); Write(address, 8, Read(address) | bit); }
            switch (pc)
            {
                case 0x56BE: length = 2; form = "L A, N8"; all.Add([3, pc, 0x3A, 16, 0, o.Tmr2]); Load(o.Tmr2); next = 0x56C0; break;
                case 0x56C0: length = 3; form = "JBR off N8.2, rel8"; Read(0x11F); next = 0x56C5; break;
                case 0x56C5: length = 1; form = "ST A, er3"; Write(0x10E, 16, a); next = 0x56C6; break;
                case 0x56C6: length = 3; form = "JBS off N8.7, rel8"; next = (Read(0x10F) & 128) != 0 ? 0x56D4 : 0x56C9; break;
                case 0x56C9: length = 3; form = "MB C, N8.0"; var irq = o.Irqh ?? throw new InvalidDataException("No default IRQH."); all.Add([3, pc, 0x19, 8, 0, irq]); Flag(32768, (irq & 1) != 0); next = 0x56CC; break;
                case 0x56CC: length = 2; form = "JGE rel8"; next = (psw & 32768) == 0 ? 0x56D4 : 0x56CE; break;
                case 0x56CE: length = 3; form = "INCB N8"; var v = Read(0xAE); var inc = (v + 1) & 255; Flag(16384, inc == 0); Flag(8192, (v & 15) == 15); Write(0xAE, 8, inc); next = 0x56D1; break;
                case 0x56D1: length = 3; form = "SB N8.0"; SetBit(0xB6, 1); next = 0x56D4; break;
                case 0x56D4: length = 3; form = "SB off N8.3"; SetBit(0x128, 8); next = 0x56D7; break;
                case 0x56D7: length = 2; form = "JEQ rel8"; Require((psw & 16384) != 0, "NoWrite must use OLD clear bit3."); next = 0x5713; break;
                case 0x5713: length = 1; form = "L A, er3"; Load(Read(0x10E, 16)); next = 0x5714; break;
                case 0x5714: length = 2; form = "ST A, N8"; Write(0xEE, 16, a); next = 0x5716; break;
                case 0x5716: length = 3; form = "CLRB N8"; Write(0xAE, 8, 0); next = 0x5719; break;
                default: throw new InvalidDataException("NoWrite producer expanded to writer/tail.");
            }
            steps.Add(new([pc, next, oldA, a, oldP, psw, 65536, 65536], form, length, all.Count)); pc = next;
        }
        var after = JsonNode.Parse(before.GetRawText())!; after["pc"] = pc; after["accumulator"] = a; after["psw"] = psw; after["dd"] = true; after["registers"] = JsonSerializer.SerializeToNode(ram[0x108..0x110]);
        return new(JsonSerializer.SerializeToElement(after), steps, all, ram, "FirstObservationNoWrite", (int[])initial.Clone());
    }
    internal static (JsonElement After, int Status, int Steps, List<int[]> All, int[] Memory) ValidateSuffix(JsonElement suffix, JsonElement before, P28CallerOracle own, int budget)
    {
        P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses"); Require(Equal(suffix.GetProperty("entry"), before), "Hidden caller/producer PC/PSW/LRB/USP/SSP seed or second machine.");
        P28FuelFactorValidator.ValidateBoundary(before); P28FuelFactorValidator.ValidateBoundary(suffix.GetProperty("exit"));
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter"); var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), budget, 0, [], null)!;
        var n = r.Steps; Require(n <= own.Steps.Count && r.Trace.Count == n && r.ProgramReads.Count == 0 && r.UsedAssumptions.Count == 0 && (r.Status != 0 || n == own.Steps.Count), "Unbounded, assumed, skipped or partial caller/producer claim.");
        var steps = own.Steps.Take(n).ToArray(); var all = own.All.Take(n == 0 ? 0 : steps[^1].AccessEnd).ToList();
        Require(Equal(stage.GetProperty("events"), JsonSerializer.SerializeToElement(steps.Select(s => s.Event).ToArray())) && Equal(suffix.GetProperty("accesses"), JsonSerializer.SerializeToElement(all.Where(v => v[0] == 0).Select(v => v[1..]).ToArray())) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(all.Where(v => v[4] == 1).Select(v => new[] { v[2], v[3], v[5] }).ToArray())), "Caller old-bit/branch/CAL frame/NoWrite RAM widths, flags or order forged.");
        Require(r.ExecutedInstructionBytes.SequenceEqual(steps.SelectMany(s => Enumerable.Range(s.Event[0], s.Length)).Distinct().Order()), "Unadmitted instruction/TRNSIT/5719/tail execution.");
        for (var i = 0; i < n; i++) Require(r.Trace[i].GetProperty("pc").GetInt32() == steps[i].Event[0] && r.Trace[i].GetProperty("nextPc").GetInt32() == steps[i].Event[1] && r.Trace[i].GetProperty("instruction").GetString() == steps[i].Form && r.Trace[i].GetProperty("accumulator").GetInt32() == steps[i].Event[3] && r.Trace[i].GetProperty("psw").GetInt32() == steps[i].Event[5], "Detached native exact-form trace.");
        var expected = JsonNode.Parse(before.GetRawText())!; var memory = (int[])own.InitialMemory.Clone();
        foreach (var w in all.Where(v => v[0] == 0 && v[4] == 1))
            if (w[3] == 16) WriteWord(memory, w[2], w[5]); else memory[w[2]] = w[5];
        if (n == own.Steps.Count) expected = JsonNode.Parse(own.After.GetRawText())!;
        else
        {
            if (n > 0) { expected["pc"] = steps[^1].Event[1]; expected["accumulator"] = steps[^1].Event[3]; expected["psw"] = steps[^1].Event[5]; expected["dd"] = (steps[^1].Event[5] & 4096) != 0; }
            // Partial expected memory is rebuilt by the caller from prefix writes;
            // full model memory is never used to claim partial completion.
            if (all.Any(v => v[1] == 0x0664 && v[4] == 1)) expected["ssp"] = before.GetProperty("ssp").GetInt32() - 2;
            var registers = before.GetProperty("registers").EnumerateArray().Select(v => v.GetInt32()).ToArray();
            foreach (var w in all.Where(v => v[0] == 0 && v[4] == 1)) for (var b = 0; b < w[3] / 8; b++) if (w[2] + b is >= 0x108 and < 0x110) registers[w[2] + b - 0x108] = w[5] >> (8 * b) & 255;
            expected["registers"] = JsonSerializer.SerializeToNode(registers);
        }
        var after = JsonSerializer.SerializeToElement(expected); Require(r.StopPc == after.GetProperty("pc").GetInt32() && Equal(suffix.GetProperty("exit"), after) && stage.GetProperty("sspAfter").GetInt32() == after.GetProperty("ssp").GetInt32(), "Wrong full retained CPU/SSP/pointer/register boundary.");
        return (after, r.Status, n, all, memory);
    }
}
