using System.Text.Json;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28CallerNativeWrite(int WriterPc, int Address, int Width, int OldValue, int Value, P28QuartetGeneration Generation);
public sealed record P28FallthroughData0136Checkpoint(int Index, string Disposition, string CallerRoute, int CallerSteps,
    bool NativeEntry064c, bool NativeCalExecuted, bool ProducerCompleted, P28NativeCallFrame? Frame,
    JsonElement? ProducerEntryAbi, int? Slot00a2, int? Byte011f, int? Byte011b, int? Byte012aBeforeCaller,
    int? Byte0128BeforeProducer, int? Byte0128AfterProducer, int? Previous00eeBefore, int? Previous00eeAfter,
    int? Counter00aeBefore, int? Counter00aeAfter, int? Byte00b6Before, int? Byte00b6After,
    int? History0136, int Tmr2Reads, int IrqhReads, int Tcon2Reads, int ProducerSteps,
    IReadOnlyList<P28CallerNativeWrite> NativeWrites, JsonElement After, JsonElement Actual);

internal sealed class P28FallthroughData0136Validation(P28FallthroughData0136Scenario scenario)
{
    internal readonly List<P28FallthroughData0136Checkpoint>[] Rows = [[], [], []];
    private readonly P28NativeCallFrame?[] _frames = new P28NativeCallFrame?[3];
    internal (JsonElement After, string Disposition, int[][] Ram) Finish(int p, int i, JsonElement row, JsonElement before,
        string disposition, Dictionary<int, int> ram, int[] registers, List<int[]> all)
    {
        var output = row.GetProperty("caller"); var producer = row.GetProperty("producer");
        var entered = disposition is "PostReturnSelectorStrict" or "PostReturnSelectorGateBypass";
        var strictUpstream = disposition == "PostReturnSelectorStrict";
        var native = new List<int[]>(); var writes = new List<P28CallerNativeWrite>(); var callerSteps = 0; var producerSteps = 0;
        var called = false; var completed = false; var route = "NotRun"; var admission = "NotRun";
        JsonElement? entry = null; int? slot = null, byteF = null, byteB = null, old12a = null, old128 = null, new128 = null, oldEe = null, newEe = null, oldAe = null, newAe = null, oldB6 = null, newB6 = null, history = null;
        var timerReads = 0; var irqReads = 0; var tconReads = 0;
        if (entered)
        {
            Require(output.ValueKind == JsonValueKind.Object, "Actual M2ae completion lacks caller suffix.");
            P28LimiterScenario.Shape(output, "suffix", "sfBefore", "sfAfter");
            Require(!output.GetProperty("sfBefore").GetBoolean() && !output.GetProperty("sfAfter").GetBoolean(), "NativeRT/CAL internal SF continuity differs.");
            var pattern = new[] { 0, 85, 170 }[p];
            var initial = P28FallthroughData0136Model.RetainedMemory(pattern, before, ram, scenario.Calls[i].Prefix.Adaptive.FixedSource);
            slot = initial[0xA2]; byteF = initial[0x11F]; byteB = initial[0x11B]; old12a = initial[0x12A];
            var own = P28FallthroughData0136Model.Caller(before, initial);
            var result = P28FallthroughData0136Model.ValidateSuffix(output.GetProperty("suffix"), before, own, 7);
            callerSteps = result.Steps;
            var steps = own.Steps.Take(callerSteps).ToArray();
            route = steps.FirstOrDefault()?.Event[1] == 0x065F ? "PrimaryTakenCalSkippedControl" : steps.Any(s => s.Event[0] == 0x064F && s.Event[1] == 0x065F) ? "FallthroughDirectVia011B7" : "FallthroughVia012A0";
            var order = all.Count(v => v[4] == 1); var memory = (int[])initial.Clone();
            void Apply(List<int[]> effects)
            {
                foreach (var w in effects.Where(v => v[4] == 1))
                {
                    Require(w[0] == 0, "Frozen observations cannot write.");
                    var old = w[3] == 16 ? P28FallthroughData0136Model.Word(memory, w[2]) : memory[w[2]];
                    var gen = new P28QuartetGeneration(w[1], i, order++, w[5]); writes.Add(new(w[1], w[2], w[3], old, w[5], gen));
                    if (w[3] == 16) P28FallthroughData0136Model.WriteWord(memory, w[2], w[5]); else memory[w[2]] = w[5];
                    if (w[1] == 0x0664)
                    {
                        Require(w[2] == before.GetProperty("ssp").GetInt32() && w[3] == 16 && w[5] == 0x0667, "Wrong native second frame.");
                        _frames[p] = new(0x0664, i, w[2], 16, 0x0667, gen.WriteOrder); called = true;
                    }
                }
                native.AddRange(effects); all.AddRange(effects);
            }
            Apply(result.All); before = result.After;
            disposition = result.Status != 0 ? "CallerSuffixPartial" : before.GetProperty("pc").GetInt32() == 0x0657 ? "CallerTrnsitBoundaryControl" : before.GetProperty("pc").GetInt32() == 0x0667 ? "CallerCalSkippedControl" : "NativeProducerCallEstablished";
            if (called && result.Status == 0)
            {
                entry = before.Clone();
                admission = (memory[0x11F] & 4) != 0 || memory[0xA2] != 0 ? "ProducerEntryModeSlotBlockedControl" : (memory[0x128] & 8) != 0 ? "ProducerEntryFreshGateBlocked" : "Mode0RetainedSlot0FirstObservation";
                if (admission == "Mode0RetainedSlot0FirstObservation")
                {
                    Require(producer.ValueKind == JsonValueKind.Object, "Native CAL entry lacks bounded in-state producer.");
                    P28LimiterScenario.Shape(producer, "suffix", "ramBefore", "ramAfter", "peripheralAccesses", "frozenObservation");
                    var o = scenario.Calls[i].ProducerObservation;
                    Require(Equal(producer.GetProperty("frozenObservation"), JsonSerializer.SerializeToElement(o, JsonDefaults.Create())) && Equal(producer.GetProperty("ramBefore"), JsonSerializer.SerializeToElement(P28FallthroughData0136Model.Snapshot(memory))), "Producer snapshot/technical initializer/slot/source injection.");
                    old128 = memory[0x128]; oldEe = P28FallthroughData0136Model.Word(memory, 0xEE); oldAe = memory[0xAE]; oldB6 = memory[0xB6]; history = P28FallthroughData0136Model.Word(memory, 0x136);
                    var body = P28FallthroughData0136Model.NoWrite(before, memory, o);
                    var next = P28FallthroughData0136Model.ValidateSuffix(producer.GetProperty("suffix"), before, body, 128);
                    Require(Equal(producer.GetProperty("peripheralAccesses"), JsonSerializer.SerializeToElement(next.All.Where(v => v[0] == 3).Select(v => v[1..]).ToArray())), "Mandatory TMR2/conditional IRQH/width/PC/order/default-TCON2 forged.");
                    Apply(next.All); before = next.After; producerSteps = next.Steps; completed = next.Status == 0;
                    Require(Equal(producer.GetProperty("ramAfter"), JsonSerializer.SerializeToElement(P28FallthroughData0136Model.Snapshot(memory))), "NoWrite RAM/slot/sample/history retention forged.");
                    Require(P28FallthroughData0136Model.Word(memory, 0x136) == history && Enumerable.Range(0x360, 12).All(a => memory[a] == initial[a]), "Retained0136/sample memory relabelled as produced.");
                    new128 = memory[0x128]; newEe = P28FallthroughData0136Model.Word(memory, 0xEE); newAe = memory[0xAE]; newB6 = memory[0xB6];
                    timerReads = next.All.Count(v => v[0] == 3 && v[2] == 0x3A); irqReads = next.All.Count(v => v[0] == 3 && v[2] == 0x19); tconReads = next.All.Count(v => v[0] == 3 && v[2] == 0x42);
                    disposition = completed ? strictUpstream ? "NativeFallthroughCallerProducerNoWriteStrict" : "GateBypassFallthroughProducerControl" : "ProducerBodyPartial";
                }
                else { Require(producer.ValueKind == JsonValueKind.Null, "Unsafe mode/slot/fresh-gate body executed."); disposition = "ProducerEntryBlockedControl"; }
            }
            else Require(producer.ValueKind == JsonValueKind.Null, "Producer ran without completed native CAL.");
            Require(native.All(v => v[2] != 0x46) && !native.Any(v => v[0] == 0 && v[4] == 1 && v[2] <= 0x137 && v[2] + v[3] / 8 > 0x136), "TRNSIT or fabricated fresh0136 effect.");
            if (_frames[p] is { } frame) Require(before.GetProperty("ssp").GetInt32() == frame.StackAddress - 2 && P28FallthroughData0136Model.Word(memory, frame.StackAddress) == frame.ReturnPc, "Producer frame popped/overwritten/SSP repaired.");
            ram[0x12A] = memory[0x12A]; ram[0x128] = memory[0x128];
            Array.Copy(memory, 0x108, registers, 0, 8);
        }
        else Require(output.ValueKind == JsonValueKind.Null && producer.ValueKind == JsonValueKind.Null, "Caller/observation ran after terminal or without native M2ae completion.");
        Require(row.GetProperty("callerRoute").GetString() == route && row.GetProperty("producerAdmission").GetString() == admission, "Forged caller route/mode/slot/ABI admission.");
        Require(Equal(row.GetProperty("producerCallFrame"), JsonSerializer.SerializeToElement(_frames[p], JsonDefaults.Create())) && Equal(row.GetProperty("pendingReturnWord"), JsonSerializer.SerializeToElement(_frames[p]?.ReturnPc)), "Missing/stale0667 frame or hidden stack cleanup.");
        Rows[p].Add(new(i, disposition, route, callerSteps, entered, called, completed, _frames[p], entry, slot, byteF, byteB, old12a, old128, new128, oldEe, newEe, oldAe, newAe, oldB6, newB6, history, timerReads, irqReads, tconReads, producerSteps, writes, before.Clone(), row.Clone()));
        return (before, disposition, native.Where(v => v[0] == 0).Select(v => v[1..]).ToArray());
    }
}
