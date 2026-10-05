using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28PostP2ControlCheckpoint(int Index, string Disposition, string Branch, int? InstructionPc,
    int Tcon0Before, int Tcon0After, int TrnsitFlagsBefore, int TrnsitFlagsAfter,
    P28QuartetGeneration? IncomingTcon0Generation, P28QuartetGeneration? Tcon0Generation,
    P28QuartetGeneration? IncomingTrnsitGeneration, P28QuartetGeneration? TrnsitGeneration,
    P28QuartetGeneration? P2Generation, int P2FinalLatch, P28QuartetGeneration? Generation0196, int StopPc,
    int NativeControlReads, int NativeControlWrites, string InitialSource);
internal sealed record P28PostP2Oracle(IReadOnlyList<int[]> Events, int[] Lengths, int[][] ControlAccesses, int[][] RamAccesses, int Tcon0After, int TrnsitFlagsAfter);
internal static class P28PostP2ControlModel
{
    internal static P28PostP2Oracle Build(int pc, int a, int psw, int tcon0, int flags, int byte018e)
    {
        if ((tcon0 & ~0x0C) != 0x83 || flags is < 0 or > 15 || byte018e is < 0 or > 255) throw new InvalidDataException("Unadmitted control domain.");
        var events = new List<int[]>();
        void Step(int from, int to, int nextA, int nextPsw) { events.Add([from, to, a, nextA, psw, nextPsw, 65536, 65536]); a = nextA; psw = nextPsw; }
        int Z(int value) => value == 0 ? psw | 0x4000 : psw & ~0x4000;
        if (pc == 0x5599)
        {
            var read = flags | 0xF0; var write = read & 0xFB;
            Step(pc, 0x559D, a, Z(write));
            return new(events, [4], [[pc, 0x46, 8, 0, read], [pc, 0x46, 8, 1, write]], [], tcon0, flags & ~4);
        }
        if (pc != 0x55C8) throw new InvalidDataException("Control entry must be the actual P2 exit.");
        Step(pc, 0x55CB, a, (tcon0 & 4) == 0 ? psw | 0x4000 : psw & ~0x4000);
        Step(0x55CB, 0x55CD, (a & 0xFF00) | byte018e, Z(byte018e) & ~0x1000);
        var xor = (a & 255) ^ 255; Step(0x55CD, 0x55CF, (a & 0xFF00) | xor, Z(xor));
        Step(0x55CF, 0x55D2, a, (a & 128) != 0 ? psw | 0x8000 : psw & ~0x8000);
        // The existing executor reads the bit, then re-reads its byte for RMW.
        // This is admitted only in the explicitly stopped, no-transfer domain.
        return new(events, [3, 2, 2, 3], [[pc, 0x40, 8, 0, tcon0], [pc, 0x40, 8, 0, tcon0], [pc, 0x40, 8, 1, tcon0 | 4]],
            [[0x55CB, 0x18E, 8, 0, byte018e]], tcon0 | 4, flags);
    }
    internal static (JsonElement After, int[][] Control, int[][] Ram, int Status) ValidateOutput(JsonElement output, JsonElement before, int tcon0, int flags, int byte018e)
    {
        P28LimiterScenario.Shape(output, "suffix", "controlAccesses"); var s = output.GetProperty("suffix"); P28LimiterScenario.Shape(s, "entry", "exit", "stage", "accesses");
        Require(Equal(s.GetProperty("entry"), before), "Control PC shortcut/second machine/hidden boundary seed.");
        P28FuelFactorValidator.ValidateBoundary(before); P28FuelFactorValidator.ValidateBoundary(s.GetProperty("exit"));
        var pc = before.GetProperty("pc").GetInt32(); var a = before.GetProperty("accumulator").GetInt32(); var psw = before.GetProperty("psw").GetInt32();
        var own = Build(pc, a, psw, tcon0, flags, byte018e); var stage = s.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 4, 0, [], null)!; var n = r.Steps;
        Require(n <= own.Events.Count && r.Trace.Count == n && r.ProgramReads.Count == 0 && r.UsedAssumptions.Count == 0, "Unbounded control/timer/IRQ/assumption.");
        var events = own.Events.Take(n).ToArray(); Require(Equal(stage.GetProperty("events"), JsonSerializer.SerializeToElement(events)), "Incorrect native control flags/A/DD/branch.");
        var control = n == 0 ? Array.Empty<int[]>() : own.ControlAccesses; var ram = pc == 0x55C8 && n >= 2 ? own.RamAccesses : [];
        Require(Equal(output.GetProperty("controlAccesses"), JsonSerializer.SerializeToElement(control)), "Wrong native SFR PC/address/width/read/write/reserved bits/side effect.");
        Require(Equal(s.GetProperty("accesses"), JsonSerializer.SerializeToElement(ram)), "Control disguised as RAM/P2 or unexpected timer read.");
        Require(Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(control.Where(v => v[3] == 1).Select(v => new[] { v[1], v[2], v[4] }).ToArray())), "Missing native same-value control store.");
        var stop = n == 0 ? pc : events[^1][1]; Require(r.StopPc == stop && (r.Status != 0 || n == own.Events.Count), "Incomplete control claimed validated.");
        Require(r.ExecutedInstructionBytes.SequenceEqual(events.SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).Distinct().Order()), "Control execution escaped reviewed prefix.");
        for (var i = 0; i < n; i++) Require(r.Trace[i].GetProperty("pc").GetInt32() == events[i][0] && r.Trace[i].GetProperty("nextPc").GetInt32() == events[i][1] && r.Trace[i].GetProperty("accumulator").GetInt32() == events[i][3] && r.Trace[i].GetProperty("psw").GetInt32() == events[i][5], "Detached control trace.");
        var expected = JsonNode.Parse(before.GetRawText())!; expected["pc"] = stop; expected["accumulator"] = n == 0 ? a : events[^1][3]; expected["psw"] = n == 0 ? psw : events[^1][5]; expected["dd"] = ((n == 0 ? psw : events[^1][5]) & 0x1000) != 0;
        Require(Equal(s.GetProperty("exit"), JsonSerializer.SerializeToElement(expected)) && stage.GetProperty("sspAfter").GetInt32() == before.GetProperty("ssp").GetInt32(), "Hidden control bank/pointer/frame/host state.");
        return (JsonSerializer.SerializeToElement(expected), control, ram, r.Status);
    }
}
internal sealed class P28PostP2ControlValidation(P28PostP2ControlScenario scenario)
{
    private readonly int[] _tcon0 = [scenario.Tcon0ArchitecturalSnapshot, scenario.Tcon0ArchitecturalSnapshot, scenario.Tcon0ArchitecturalSnapshot];
    private readonly int[] _flags = [scenario.TrnsitArchitecturalFlags, scenario.TrnsitArchitecturalFlags, scenario.TrnsitArchitecturalFlags];
    private readonly P28QuartetGeneration?[] _tgen = new P28QuartetGeneration?[3], _rgen = new P28QuartetGeneration?[3];
    internal readonly List<P28PostP2ControlCheckpoint>[] Rows = [[], [], []];
    internal void RetainBelow(int p, int value, P28QuartetGeneration? generation) { _tcon0[p] = value; _tgen[p] = generation; }
    internal (JsonElement After, string Disposition, int[][] Ram) Finish(int p, int i, JsonElement row, JsonElement before, P28QuartetGeneration? g, string disposition, int byte018e, P28P2LatchCheckpoint p2)
    {
        Require(Equal(row.GetProperty("controlBefore"), JsonSerializer.SerializeToElement(new[] { _tcon0[p], _flags[p] })) && Equal(row.GetProperty("incomingTcon0Generation"), JsonSerializer.SerializeToElement(_tgen[p], JsonDefaults.Create())) && Equal(row.GetProperty("incomingTrnsitGeneration"), JsonSerializer.SerializeToElement(_rgen[p], JsonDefaults.Create())), "Per-event control reseed/stale equal-value generation.");
        var oldT = _tcon0[p]; var oldR = _flags[p]; var incomingT = _tgen[p]; var incomingR = _rgen[p]; var output = row.GetProperty("control"); int? pc = null; int[][] accesses = [], ram = [];
        if (disposition is "QuartetDerivedP2LatchStrict" or "GateBypassP2LatchControl")
        {
            Require(g is not null && p2.Generation?.EventIndex == i && output.ValueKind == JsonValueKind.Object, "Control without current native P2/0196 generation.");
            pc = before.GetProperty("pc").GetInt32(); var validated = P28PostP2ControlModel.ValidateOutput(output, before, oldT, oldR, byte018e); before = validated.After; accesses = validated.Control; ram = validated.Ram;
            // This prefix has no new RAM writes: next ordinal is independently
            // validated P2 generation + one, not an observed control ordinal.
            foreach (var w in accesses.Where(v => v[3] == 1))
            {
                var generation = new P28QuartetGeneration(w[0], i, p2.Generation!.WriteOrder + 1, w[4]);
                if (w[1] == 0x40) { _tcon0[p] = w[4]; _tgen[p] = generation; } else { _flags[p] = w[4] & 15; _rgen[p] = generation; }
            }
            disposition = validated.Status switch { 0 => disposition == "QuartetDerivedP2LatchStrict" ? "PostP2ControlStrict" : "PostP2ControlGateBypass", 3 => "BudgetExceeded", 2 => "ExecutionError", _ => "ControlPartial" };
        }
        else Require(output.ValueKind == JsonValueKind.Null, "Control ran after incomplete/no-fresh upstream.");
        Require(Equal(row.GetProperty("controlAfter"), JsonSerializer.SerializeToElement(new[] { _tcon0[p], _flags[p] })) && Equal(row.GetProperty("tcon0Generation"), JsonSerializer.SerializeToElement(_tgen[p], JsonDefaults.Create())) && Equal(row.GetProperty("trnsitGeneration"), JsonSerializer.SerializeToElement(_rgen[p], JsonDefaults.Create())), "Host overwrite/forged control generation/storage.");
        Rows[p].Add(new(i, disposition, pc == 0x5599 ? "PostP2NotBelowPath" : pc == 0x55C8 ? "PostP2BelowPath" : "NotRun", pc, oldT, _tcon0[p], oldR, _flags[p], incomingT, _tgen[p], incomingR, _rgen[p], p2.Generation, p2.NewLatch, pc is null ? null : g, before.GetProperty("pc").GetInt32(), accesses.Count(v => v[3] == 0), accesses.Count(v => v[3] == 1), "RawArchitecturalSnapshot;OnceOnly;NotResetOrBoot"));
        return (before, disposition, ram);
    }
}
