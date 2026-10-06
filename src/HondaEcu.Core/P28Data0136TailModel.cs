using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

internal static class P28Data0136TailModel
{
    internal static P28CallerOracle Prefix(JsonElement before)
    {
        Require(before.GetProperty("pc").GetInt32() == 0x5719 && before.GetProperty("dd").GetBoolean() && before.GetProperty("lrb").GetInt32() == 0x21 && (before.GetProperty("psw").GetInt32() & 7) == 2, "Tail not independent native M2ag exit.");
        var a = before.GetProperty("accumulator").GetInt32(); var old = before.GetProperty("psw").GetInt32();
        // Retained00A2=0 is explicitly owned in the existing M2ag domain.
        // No19B.2 value, observed branch or scratch-backed pointer enters this formula.
        var psw = (old & ~0xC000) | 0x8000; // byte0-5: borrow1,zero0; HC/DD unchanged
        var all = new List<int[]> { new[] { 0, 0x5719, 0xA2, 8, 0, 0 } };
        var steps = new List<P28CallerStep> {
            new([0x5719,0x571D,a,a,old,psw,0,5],"CMPB N'8, #N8",4,1),
            new([0x571D,0x5722,a,a,psw,psw,65536,65536],"JNE rel8",2,1) };
        var n = JsonNode.Parse(before.GetRawText())!; n["pc"] = 0x5722; n["psw"] = psw;
        var memory = new int[0x800];
        return new(JsonSerializer.SerializeToElement(n), steps, all, memory, "STOPBeforeUnowned019BBit2", (int[])memory.Clone());
    }
}

public sealed record P28Data0136TailCheckpoint(int Index, string Disposition, bool NativeEntry5719,
    int TailSteps, int FinalPc, P28NativeCallFrame? PendingFrame, JsonElement? Entry, JsonElement After,
    int? Retained0136, string ReaderClassification, int NewPeripheralReads, JsonElement? Actual);

internal sealed class P28Data0136TailValidation
{
    internal readonly List<P28Data0136TailCheckpoint>[] Rows = [[], [], []];
    internal (JsonElement After, string Disposition, int[][] Ram) Finish(int p, int i, JsonElement row,
        JsonElement before, string disposition, P28FallthroughData0136Checkpoint caller, List<int[]> all)
    {
        var entered = disposition is "NativeFallthroughCallerProducerNoWriteStrict" or "GateBypassFallthroughProducerControl";
        var present = row.TryGetProperty("softwareTail", out var tail); var steps = 0; JsonElement? entry = null;
        if (entered)
        {
            Require(present && tail.ValueKind == JsonValueKind.Object && caller.Frame is not null && caller.History0136.HasValue, "Missing actual tail/native frame/retained history.");
            P28LimiterScenario.Shape(tail, "suffix", "pendingFrame", "frameWordBefore", "frameWordAfter", "retained0136Before", "retained0136After", "diagnostic019b", "liveInClassification", "disposition");
            entry = before.Clone(); var own = P28Data0136TailModel.Prefix(before);
            var result = P28FallthroughData0136Model.ValidateSuffix(tail.GetProperty("suffix"), before, own, 2);
            Require(Equal(tail.GetProperty("pendingFrame"), JsonSerializer.SerializeToElement(caller.Frame, JsonDefaults.Create())) && tail.GetProperty("frameWordBefore").GetInt32() == caller.Frame!.ReturnPc && tail.GetProperty("frameWordAfter").GetInt32() == caller.Frame.ReturnPc, "Tail popped/rewrote/faked pending frame.");
            Require(tail.GetProperty("retained0136Before").GetInt32() == caller.History0136 && tail.GetProperty("retained0136After").GetInt32() == caller.History0136, "Retained0136 replaced or fake fresh generation.");
            Require(tail.GetProperty("diagnostic019b").GetInt32() == (new[] { 0, 85, 170 }[p] & ~1) && tail.GetProperty("liveInClassification").GetString() == "019BBit2Unowned;DiagnosticScratchOnly;STOPBefore5722", "Scratch neighbor promoted to semantic bit owner.");
            Require(result.All.All(v => v[0] == 0 && v[1] == 0x5719 && v[2] == 0xA2 && v[3] == 8 && v[4] == 0 && v[5] == 0), "Unexpected live-in/timer/stack/0136/write access.");
            var label = result.Status == 0 ? "TailLiveInBlocked" : "TailExecutionPartial";
            Require(tail.GetProperty("disposition").GetString() == label, "False tail timer completion.");
            disposition = result.Status == 0 ? disposition == "NativeFallthroughCallerProducerNoWriteStrict" ? "TailLiveInBlocked" : "TailLiveInBlockedGateControl" : "TailExecutionPartial";
            before = result.After; steps = result.Steps; all.AddRange(result.All);
        }
        else Require(!present, "Tail/input ran without NoWrite completion or after terminal.");
        Rows[p].Add(new(i, disposition, entered, steps, before.GetProperty("pc").GetInt32(), caller.Frame, entry, before.Clone(), caller.History0136, "NoData0136Read;RetainedHistoryNotFresh", 0, present ? tail.Clone() : null));
        return (before, disposition, entered && steps > 0 ? [[0x5719, 0xA2, 8, 0, 0]] : []);
    }
}
