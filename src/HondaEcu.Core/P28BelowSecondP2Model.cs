using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28BelowSecondP2Checkpoint(int Index, string Disposition, P28QuartetGeneration? Generation0196,
    int? SelectedSlot, int? SelectedAddress, P28QuartetGeneration? SelectedGeneration,
    int? IncomingA, int? IncomingPsw, int? OutgoingRolA, int? OutgoingRolPsw,
    int? SecondP2Old, int? SecondP2New, P28QuartetGeneration? IncomingP2Generation, P28QuartetGeneration? OutgoingP2Generation,
    int FinalP2Latch, int FinalTcon0, P28QuartetGeneration? IncomingTcon0Generation, P28QuartetGeneration? FinalTcon0Generation,
    int NativeSteps, int RamWrites, int Tcon0Reads, int SecondP2Reads, int SecondP2Writes, int StopPc);
internal sealed record P28BelowOracle(List<int[]> Events, List<int> Lengths, List<int[]> All, List<int> AccessEnds);
internal static class P28BelowSecondP2Model
{
    internal static readonly string[] Mnemonics = ["ROLB A", "STB A, off N8", "RB N8.2", "L A, #N16", "SJ rel8", "ST A, off N8", "L A, #N16", "ST A, off N8", "J addr16", "ST A, off N8", "L A, off N8", "JNE rel8", "LB A, off N8", "SJ rel8", "ORB A, off N8", "ANDB A, #N8", "ORB N8, A", "RB off N8.7"];
    // Independently specified formulas, not a shared Rust rotate/executor helper.
    internal static P28BelowOracle Build(int a, int psw, int latch, int tcon0, int byte012a)
    {
        if ((psw & 0x1000) != 0 || (tcon0 & ~12) != 0x83 || (tcon0 & 4) == 0) throw new InvalidDataException("Expected native DD0/55C8 TCON generation.");
        var events = new List<int[]>(); var lengths = new List<int>(); var all = new List<int[]>(); var ends = new List<int>();
        void Step(int pc, int next, int length, int na, int np, params int[][] accesses)
        { events.Add([pc, next, a, na, psw, np, 65536, 65536]); lengths.Add(length); all.AddRange(accesses); ends.Add(all.Count); a = na; psw = np; }
        int Z(int v) => v == 0 ? psw | 0x4000 : psw & ~0x4000;
        var al = a & 255; var rol = (al * 2 + ((psw & 0x8000) != 0 ? 1 : 0)) & 255;
        Step(0x55D2, 0x55D3, 1, (a & 0xFF00) | rol, (psw & ~0x8000) | ((al & 128) != 0 ? 0x8000 : 0));
        Step(0x55D3, 0x55D5, 2, a, psw, [0, 0x55D3, 0x116, 8, 1, rol]);
        Step(0x55D5, 0x55D8, 3, a, psw & ~0x4000, [2, 0x55D5, 0x40, 8, 0, tcon0], [2, 0x55D5, 0x40, 8, 0, tcon0], [2, 0x55D5, 0x40, 8, 1, tcon0 & ~4]);
        Step(0x55D8, 0x55DB, 3, 1, Z(1) | 0x1000);
        Step(0x55DB, 0x562C, 2, a, psw);
        Step(0x562C, 0x562E, 2, a, psw, [0, 0x562C, 0x110, 16, 1, 1]);
        Step(0x562E, 0x5631, 3, 1, Z(1) | 0x1000);
        Step(0x5631, 0x5633, 2, a, psw, [0, 0x5631, 0x112, 16, 1, 1]);
        Step(0x5633, 0x565D, 3, a, psw);
        Step(0x565D, 0x565F, 2, a, psw, [0, 0x565D, 0x114, 16, 1, 1]);
        Step(0x565F, 0x5661, 2, 1, Z(1) | 0x1000, [0, 0x565F, 0x110, 16, 0, 1]);
        Step(0x5661, 0x5671, 2, a, psw);
        Step(0x5671, 0x5673, 2, rol, Z(rol) & ~0x1000, [0, 0x5671, 0x116, 8, 0, rol]);
        Step(0x5673, 0x567E, 2, a, psw);
        var mask = rol | 15; Step(0x567E, 0x5680, 2, mask, Z(mask), [0, 0x567E, 0x18F, 8, 0, 15]);
        Step(0x5680, 0x5682, 2, 15, Z(15));
        var value = latch | 15; Step(0x5682, 0x5685, 3, a, Z(value), [1, 0x5682, 0x24, 8, 0, latch], [1, 0x5682, 0x24, 8, 1, value]);
        Step(0x5685, 0x5688, 3, a, (byte012a & 128) == 0 ? psw | 0x4000 : psw & ~0x4000,
            [0, 0x5685, 0x12A, 8, 0, byte012a], [0, 0x5685, 0x12A, 8, 0, byte012a], [0, 0x5685, 0x12A, 8, 1, byte012a & ~128]);
        return new(events, lengths, all, ends);
    }
    internal static (JsonElement After, int Status, int Steps, int[][] All) ValidateOutput(JsonElement output, JsonElement before, int latch, int tcon0, int byte012a)
    {
        P28LimiterScenario.Shape(output, "suffix", "peripheralAccesses", "controlAccesses"); var s = output.GetProperty("suffix");
        P28LimiterScenario.Shape(s, "entry", "exit", "stage", "accesses");
        Require(before.GetProperty("pc").GetInt32() == 0x55D2 && Equal(s.GetProperty("entry"), before), "Hidden55D2 PC/A/CF/frame seed or second machine.");
        P28FuelFactorValidator.ValidateBoundary(before); P28FuelFactorValidator.ValidateBoundary(s.GetProperty("exit"));
        var own = Build(before.GetProperty("accumulator").GetInt32(), before.GetProperty("psw").GetInt32(), latch, tcon0, byte012a);
        var stage = s.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 18, 0, [], null)!; var n = r.Steps;
        Require(n <= 18 && r.Trace.Count == n && r.ProgramReads.Count == 0 && r.UsedAssumptions.Count == 0, "Timer/IRQ/frame/assumption or unbounded continuation.");
        var events = own.Events.Take(n).ToArray(); var all = own.All.Take(n == 0 ? 0 : own.AccessEnds[n - 1]).ToArray();
        Require(Equal(stage.GetProperty("events"), JsonSerializer.SerializeToElement(events)), "Incorrect ROL/A/AH/CF/DD/PSW/branch or skipped instruction.");
        foreach (var (key, kind) in new[] { ("peripheralAccesses", 1), ("controlAccesses", 2) }) Require(Equal(output.GetProperty(key), JsonSerializer.SerializeToElement(all.Where(v => v[0] == kind).Select(v => v[1..]).ToArray())), "Wrong native peripheral PC/width/read/write/value/order.");
        Require(Equal(s.GetProperty("accesses"), JsonSerializer.SerializeToElement(all.Where(v => v[0] == 0).Select(v => v[1..]).ToArray())), "Unowned RAM or SFR masquerading as RAM.");
        Require(Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(all.Where(v => v[4] == 1).Select(v => new[] { v[2], v[3], v[5] }).ToArray())), "Missing/extra/reordered/same-value native write.");
        var stop = n == 0 ? 0x55D2 : events[^1][1]; Require(r.StopPc == stop && (r.Status != 0 || n == 18), "Incomplete prefix claimed strict second P2.");
        Require(r.ExecutedInstructionBytes.SequenceEqual(events.SelectMany((e, j) => Enumerable.Range(e[0], own.Lengths[j])).Distinct().Order()), "Execution outside exact extents or RT5688.");
        for (var j = 0; j < n; j++) Require(r.Trace[j].GetProperty("pc").GetInt32() == events[j][0] && r.Trace[j].GetProperty("nextPc").GetInt32() == events[j][1] && r.Trace[j].GetProperty("instruction").GetString() == Mnemonics[j] && r.Trace[j].GetProperty("accumulator").GetInt32() == events[j][3] && r.Trace[j].GetProperty("psw").GetInt32() == events[j][5], "Detached native continuation trace/form.");
        var expected = JsonNode.Parse(before.GetRawText())!; var psw = n == 0 ? own.Events[0][4] : events[^1][5];
        expected["pc"] = stop; expected["accumulator"] = n == 0 ? own.Events[0][2] : events[^1][3]; expected["psw"] = psw; expected["dd"] = (psw & 4096) != 0;
        Require(Equal(s.GetProperty("exit"), JsonSerializer.SerializeToElement(expected)) && stage.GetProperty("sspAfter").GetInt32() == before.GetProperty("ssp").GetInt32(), "Hidden pointer/register/machine/return frame.");
        return (JsonSerializer.SerializeToElement(expected), r.Status, n, all);
    }
}
internal sealed class P28BelowSecondP2Validation
{
    internal readonly List<P28BelowSecondP2Checkpoint>[] Rows = [[], [], []];
    internal (JsonElement After, string Disposition, int[][] Ram) Finish(int p, int i, JsonElement row, JsonElement before, string disposition,
        Dictionary<int, int> ram, P28QuartetHandoffCheckpoint prefix, List<int[]> native,
        P28P2LatchValidation p2, P28PostP2ControlValidation control)
    {
        var first = p2.Rows[p][i]; var c = control.Rows[p][i]; var latch = first.NewLatch; var tcon = c.Tcon0After;
        var pg = first.Generation; var tg = c.Tcon0Generation; var incomingP = pg; var incomingT = tg;
        var all = new List<int[]>(); var output = row.GetProperty("below"); int? a = null, psw = null, rolA = null, rolPsw = null, old = null, value = null; var steps = 0;
        // Independently checked RAM chronology plus the separately verified SFR
        // stages are merged at their real stage positions, not sorted by PC.
        all.AddRange(Matrix(prefix.Actual.GetProperty("continuityJournal"), 6, 32768).Where(v => v[0] == 1).Select(v => new[] { 0, v[1], v[2], v[3], v[4], v[5] }));
        var controlRam = c.InstructionPc == 0x55C8 && row.GetProperty("control").ValueKind == JsonValueKind.Object ? row.GetProperty("control").GetProperty("suffix").GetProperty("accesses").GetArrayLength() : 0;
        all.AddRange(native.Take(native.Count - controlRam).Select(v => new[] { 0, v[0], v[1], v[2], v[3], v[4] }));
        if (row.GetProperty("p2").ValueKind == JsonValueKind.Object) all.AddRange(Matrix(row.GetProperty("p2").GetProperty("peripheralAccesses"), 5, 2).Select(v => new[] { 1, v[0], v[1], v[2], v[3], v[4] }));
        if (row.GetProperty("control").ValueKind == JsonValueKind.Object) all.AddRange(Matrix(row.GetProperty("control").GetProperty("controlAccesses"), 5, 3).Select(v => new[] { 2, v[0], v[1], v[2], v[3], v[4] }));
        all.AddRange(native.Skip(native.Count - controlRam).Select(v => new[] { 0, v[0], v[1], v[2], v[3], v[4] }));
        int[][] ownRam = [];
        if (disposition is "PostP2ControlStrict" or "PostP2ControlGateBypass" && c.InstructionPc == 0x55C8)
        {
            Require(pg?.WriterPc == 0x55C5 && pg.EventIndex == i && tg?.WriterPc == 0x55C8 && tg.EventIndex == i && prefix.ResultGeneration is not null && output.ValueKind == JsonValueKind.Object, "Missing current G0196/G1/TCON0 proof.");
            a = before.GetProperty("accumulator").GetInt32(); psw = before.GetProperty("psw").GetInt32();
            var result = P28BelowSecondP2Model.ValidateOutput(output, before, latch, tcon, ram[0x12A]); steps = result.Steps;
            if (steps > 0) { var own = P28BelowSecondP2Model.Build(a.Value, psw.Value, latch, tcon, ram[0x12A]); rolA = own.Events[0][3]; rolPsw = own.Events[0][5]; }
            var order = all.Count(v => v[4] == 1);
            foreach (var w in result.All.Where(v => v[4] == 1))
            {
                var g = new P28QuartetGeneration(w[1], i, order++, w[5]);
                if (w[0] == 1) { old = latch; value = w[5]; latch = value.Value; pg = g; }
                else if (w[0] == 2) { tcon = w[5]; tg = g; }
                else for (var b = 0; b < w[3] / 8; b++) ram[w[2] + b] = w[5] >> (8 * b) & 255;
            }
            ownRam = result.All.Where(v => v[0] == 0).Select(v => v[1..]).ToArray(); all.AddRange(result.All); before = result.After;
            disposition = result.Status switch { 0 => disposition == "PostP2ControlStrict" ? "BelowSecondP2Strict" : "BelowSecondP2GateBypass", 3 => "BudgetExceeded", 2 => "ExecutionError", _ => "BelowContinuationPartial" };
        }
        else Require(output.ValueKind == JsonValueKind.Null, "Below continuation ran after terminal or on non-below path.");
        Require(Equal(row.GetProperty("allNativeJournal"), JsonSerializer.SerializeToElement(all)), "Event-wide RAM/P2/control chronology forged or host reseed.");
        Require(row.GetProperty("secondP2After").GetInt32() == latch && Equal(row.GetProperty("secondP2Generation"), JsonSerializer.SerializeToElement(pg, JsonDefaults.Create())) && row.GetProperty("finalTcon0").GetInt32() == tcon && Equal(row.GetProperty("finalTcon0Generation"), JsonSerializer.SerializeToElement(tg, JsonDefaults.Create())), "Stale G1/fake G2/TCON generation/host reseed.");
        p2.RetainBelow(p, latch, pg); control.RetainBelow(p, tcon, tg);
        var completed = disposition is "BelowSecondP2Strict" or "BelowSecondP2GateBypass";
        // Partial execution retains actual storage/generations without claiming
        // a completed second-P2 semantic result, even if its write already ran.
        Rows[p].Add(new(i, disposition, output.ValueKind == JsonValueKind.Null ? null : prefix.ResultGeneration, prefix.SelectedSlot, prefix.SelectedAddress, prefix.SelectedGeneration,
            a, psw, rolA, rolPsw, completed ? old : null, completed ? value : null, incomingP, completed ? pg : null, latch, tcon, incomingT, tg, steps,
            ownRam.Count(v => v[3] == 1), steps < 3 ? 0 : 2, value is null ? 0 : 1, value is null ? 0 : 1, before.GetProperty("pc").GetInt32()));
        return (before, disposition, ownRam);
    }
}
