using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28P2LatchCheckpoint(int Index, string Disposition, int OldLatch, int NewLatch, int? InstructionPc, int? SourceAl,
    P28QuartetGeneration? IncomingGeneration, P28QuartetGeneration? Generation, P28QuartetGeneration? Consumer0196Generation,
    string ArchitecturalSource, string ElectricalEffect);
internal static class P28P2LatchModel
{
    internal static (int Value, int Psw) Compute(int pc, int oldLatch, int a, int psw)
    {
        if (pc is not (0x5596 or 0x55C5) || oldLatch is < 0 or > 255) throw new InvalidDataException("Unadmitted P2 byte effect.");
        var v = pc == 0x5596 ? oldLatch & (a & 255) : oldLatch | (a & 255);
        return (v, v == 0 ? psw | 0x4000 : psw & ~0x4000);
    }
    internal static JsonElement ValidateOutput(JsonElement output, JsonElement before, int oldLatch, out int? newLatch)
    {
        P28LimiterScenario.Shape(output, "suffix", "peripheralAccesses"); var s = output.GetProperty("suffix");
        P28LimiterScenario.Shape(s, "entry", "exit", "stage", "accesses"); var pc = before.GetProperty("pc").GetInt32();
        var a = before.GetProperty("accumulator").GetInt32(); var psw = before.GetProperty("psw").GetInt32();
        var own = Compute(pc, oldLatch, a, psw);
        Require(Equal(s.GetProperty("entry"), before), "P2 PC shortcut/hidden state/second machine.");
        P28FuelFactorValidator.ValidateBoundary(s.GetProperty("entry")); P28FuelFactorValidator.ValidateBoundary(s.GetProperty("exit"));
        var stage = s.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 1, 0, [], null)!;
        Require(r.Steps is 0 or 1 && r.Trace.Count == r.Steps && r.ProgramReads.Count == 0 && r.UsedAssumptions.Count == 0, "Unbounded P2/timer/frame.");
        Require(s.GetProperty("accesses").GetArrayLength() == 0, "P2 disguised as RAM or neighboring SFR.");
        var events = r.Steps == 0 ? Array.Empty<int[]>() : new[] { new[] { pc, pc + 3, a, a, psw, own.Psw, 65536, 65536 } };
        Require(Equal(stage.GetProperty("events"), JsonSerializer.SerializeToElement(events)), "P2 operation/A/flags/branch forged.");
        var accesses = r.Steps == 0 ? Array.Empty<int[]>() : new[] { new[] { pc, 0x24, 8, 0, oldLatch }, new[] { pc, 0x24, 8, 1, own.Value } };
        Require(Equal(output.GetProperty("peripheralAccesses"), JsonSerializer.SerializeToElement(accesses)), "Missing native P2 RMW read/write/order/old/new or wrong width/address.");
        var writes = r.Steps == 0 ? Array.Empty<int[]>() : new[] { new[] { 0x24, 8, own.Value } };
        Require(Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(writes)), "Missing same-value P2 write.");
        Require(r.Status != 0 || r.Steps == 1, "Incomplete P2 claimed Validated.");
        Require(r.StopPc == pc + r.Steps * 3 && r.ExecutedInstructionBytes.SequenceEqual(r.Steps == 0 ? [] : Enumerable.Range(pc, 3)), "Wrong P2 extent or downstream continuation.");
        if (r.Steps == 1) { var t = r.Trace[0]; Require(t.GetProperty("pc").GetInt32() == pc && t.GetProperty("nextPc").GetInt32() == pc + 3 && t.GetProperty("accumulator").GetInt32() == a && t.GetProperty("psw").GetInt32() == own.Psw, "Detached P2 native trace."); }
        var expected = JsonNode.Parse(before.GetRawText())!; expected["pc"] = r.StopPc; expected["psw"] = r.Steps == 1 ? own.Psw : psw;
        Require(Equal(s.GetProperty("exit"), JsonSerializer.SerializeToElement(expected)) && stage.GetProperty("sspAfter").GetInt32() == before.GetProperty("ssp").GetInt32(), "Hidden P2 boundary seed/frame/register.");
        newLatch = r.Steps == 1 ? own.Value : null; return s.GetProperty("exit");
    }
}
internal sealed class P28P2LatchValidation(byte initial)
{
    private readonly int[] _latch = [initial, initial, initial];
    private readonly P28QuartetGeneration?[] _generation = new P28QuartetGeneration?[3];
    internal readonly List<P28P2LatchCheckpoint>[] Rows = [[], [], []];
    internal (JsonElement After, string Disposition) Finish(int p, int i, JsonElement row, JsonElement before, P28QuartetGeneration? g, string disposition)
    {
        Require(row.GetProperty("p2Before").GetInt32() == _latch[p] && Equal(row.GetProperty("incomingP2Generation"), JsonSerializer.SerializeToElement(_generation[p], JsonDefaults.Create())), "Per-event P2 reseed or stale equal-value generation.");
        var old = _latch[p]; var incoming = _generation[p]; var output = row.GetProperty("p2"); int? pc = null, al = null;
        if (disposition is "QuartetDerived0196AlternateStrict" or "GateBypass0196AlternateStrict")
        {
            Require(g is not null && output.ValueKind == JsonValueKind.Object, "P2 result without current0196 native proof.");
            pc = before.GetProperty("pc").GetInt32(); al = before.GetProperty("accumulator").GetInt32() & 255;
            before = P28P2LatchModel.ValidateOutput(output, before, old, out var next);
            if (next is { } value)
            {
                // Peripheral write is separate from RAM journal but its identity
                // uses the next ALL-native event write ordinal, not value equality.
                var order = Matrix(row.GetProperty("continuityJournal"), 6, 32768).Count(v => v[0] == 1 && v[4] == 1);
                _generation[p] = new(pc.Value, i, order, value); _latch[p] = value;
            }
            var status = output.GetProperty("suffix").GetProperty("stage").GetProperty("result").GetProperty("status").GetInt32();
            disposition = status == 0 ? disposition == "QuartetDerived0196AlternateStrict" ? "QuartetDerivedP2LatchStrict" : "GateBypassP2LatchControl" : status == 3 ? "BudgetExceeded" : status == 2 ? "ExecutionError" : "P2InstructionPartial";
        }
        else { Require(output.ValueKind == JsonValueKind.Null, "P2 ran after incomplete/no-fresh upstream."); if (disposition == "0196AlternatePartial") disposition = "UpstreamPartial"; }
        Require(row.GetProperty("p2After").GetInt32() == _latch[p] && Equal(row.GetProperty("p2Generation"), JsonSerializer.SerializeToElement(_generation[p], JsonDefaults.Create())), "Host P2 overwrite/forged generation/final latch.");
        Rows[p].Add(new(i, disposition, old, _latch[p], pc, al, incoming, _generation[p], pc is null ? null : g, incoming is null ? "InitialArchitecturalSnapshot" : "RetainedNativeGeneration", "NotModeled"));
        return (before, disposition);
    }
}
