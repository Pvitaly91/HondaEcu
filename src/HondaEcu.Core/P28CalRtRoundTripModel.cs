using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28NativeCallFrame(int WriterPc, int EventIndex, int StackAddress, int Width, int ReturnPc, int WriteOrder);
public sealed record P28CalRtRoundTripCheckpoint(int Index, string Disposition, string FrameSource, P28NativeCallFrame? Frame,
    int? SspBeforeCal, int? SspAfterCal, int? SspBeforeRt, int? SspAfterRt, bool SameFrame, bool SspBalanced,
    JsonElement? BeforeRt, JsonElement AfterReturnOrStop, JsonElement Actual);

/// <summary>Owns the return word and SSP arithmetic; observations are compared, never used as expected stack input.</summary>
internal sealed class P28CalRtRoundTripValidation
{
    internal readonly List<P28CalRtRoundTripCheckpoint>[] Rows = [[], [], []];
    private readonly P28NativeCallFrame?[] _frames = new P28NativeCallFrame?[3];
    internal JsonElement Start(int p, int i, JsonElement row, JsonElement before, P28QuartetHandoffCheckpoint prefix, List<int[]> native)
    {
        Require(_frames[p] is null && before.GetProperty("pc").GetInt32() == 0x05ED, "Unconsumed frame or detached scheduler seam.");
        var ssp = before.GetProperty("ssp").GetInt32();
        Require(ssp is >= 0x700 and <= 0x7FE && (ssp & 1) == 0, "System stack collision, alignment, overflow or underflow.");
        const int callPc = 0x063B; const int length = 3;
        var frame = new P28NativeCallFrame(callPc, i, ssp, 16, callPc + length,
            Matrix(prefix.Actual.GetProperty("continuityJournal"), 6, 32768).Count(v => v[0] == 1 && v[4] == 1));
        Require(Equal(row.GetProperty("callFrame"), JsonSerializer.SerializeToElement(frame, JsonDefaults.Create())), "Wrong/stale/host-seeded native call frame identity.");
        var entry = JsonNode.Parse(before.GetRawText())!; entry["pc"] = callPc;
        var write = new[] { callPc, ssp, 16, 1, frame.ReturnPc };
        var result = ValidateInstruction(row.GetProperty("nativeCal"), JsonSerializer.SerializeToElement(entry), frame, true);
        Require(result.Status == 0, "CAL instruction/frame not established.");
        _frames[p] = frame; native.Add(write);
        return result.After;
    }
    internal (JsonElement After, string Disposition, int[][] Ram) Finish(int p, int i, JsonElement row, JsonElement before, string disposition, List<int[]> all)
    {
        var frame = _frames[p]; var stack = new List<int[]>(); int[][] reads = [];
        var rt = row.GetProperty("nativeRt"); JsonElement? beforeRt = null;
        var balanced = false; var same = false; int? beforeSsp = null, afterSsp = null;
        if (frame is not null)
        {
            stack.Add([frame.WriterPc, frame.StackAddress, 16, 1, frame.ReturnPc]);
            // Every native RAM access in the unchanged interval is independently
            // validated by the existing callee models. No equal-value overwrite.
            var frameIndex = all.FindIndex(v => v[0] == 0 && v[1] == frame.WriterPc && v[2] == frame.StackAddress && v[3] == 16 && v[4] == 1 && v[5] == frame.ReturnPc);
            Require(frameIndex >= 0 && all.Take(frameIndex).Count(v => v[4] == 1) == frame.WriteOrder
                && all.Skip(frameIndex).Count(v => v[0] == 0 && v[2] < frame.StackAddress + 2 && v[2] + v[3] / 8 > frame.StackAddress) == 1,
                "Native frame collision/extra stack read or overwrite before RT.");
            if (disposition is "BelowSecondP2Strict" or "BelowSecondP2GateBypass")
            {
                Require(before.GetProperty("pc").GetInt32() == 0x5688 && before.GetProperty("ssp").GetInt32() == frame.StackAddress - 2, "Callee changed retained SSP.");
                beforeRt = before; beforeSsp = frame.StackAddress - 2;
                var result = ValidateInstruction(rt, before, frame, false); before = result.After;
                if (result.Status == 0)
                {
                    reads = [[0x5688, frame.StackAddress, 16, 0, frame.ReturnPc]]; stack.AddRange(reads);
                    all.AddRange(reads.Select(v => new[] { 0, v[0], v[1], v[2], v[3], v[4] }));
                    same = true; afterSsp = frame.StackAddress; balanced = true;
                    disposition = disposition == "BelowSecondP2Strict" ? "CallReturnStrict" : "CallReturnGateBypass";
                }
                else disposition = "CallerFramePartial";
            }
            else { Require(rt.ValueKind == JsonValueKind.Null, "RT ran on non-below/partial body."); disposition = "CallerFramePartial"; }
        }
        else Require(row.GetProperty("nativeCal").ValueKind == JsonValueKind.Null && rt.ValueKind == JsonValueKind.Null && row.GetProperty("callFrame").ValueKind == JsonValueKind.Null, "RT without CAL or frame inserted after terminal.");
        Require(Equal(row.GetProperty("stackJournal"), JsonSerializer.SerializeToElement(stack)), "Host diagnostic read/stale word/wrong width/address masquerades as native CAL/RT.");
        Rows[p].Add(new(i, disposition, frame is null ? "NotEstablished" : "NativeCAL063B", frame,
            frame?.StackAddress, frame is null ? null : frame.StackAddress - 2, beforeSsp, afterSsp, same, balanced, beforeRt, before.Clone(), row.Clone()));
        _frames[p] = null; // Validation bookkeeping only; partial native SSP remains untouched.
        return (before, disposition, reads);
    }
    internal static (JsonElement After, int Status) ValidateInstruction(JsonElement output, JsonElement before, P28NativeCallFrame frame, bool call)
    {
        P28LimiterScenario.Shape(output, "suffix", "sfBefore", "sfAfter");
        // The complete upstream/body admit no STACK-mode instruction. SF is a
        // separately owned internal flag initialized to A-mode, not a PSW bit.
        Require(!output.GetProperty("sfBefore").GetBoolean() && !output.GetProperty("sfAfter").GetBoolean(), "Wrong internal SF/A-mode; PSW reserved bit is not SF.");
        var suffix = output.GetProperty("suffix"); P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses");
        P28FuelFactorValidator.ValidateBoundary(before); P28FuelFactorValidator.ValidateBoundary(suffix.GetProperty("exit"));
        Require(Equal(suffix.GetProperty("entry"), before), "Hidden PC/A/PSW/LRB/SCB/SSP/pointer/register seed.");
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var result = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 1, 0, [], null)!;
        var pc = call ? 0x063B : 0x5688; var length = call ? 3 : 1; var target = call ? 0x54F5 : 0x063B + 3;
        Require(before.GetProperty("pc").GetInt32() == pc && frame.WriterPc == 0x063B && frame.Width == 16 && frame.ReturnPc == 0x063B + 3
            && frame.StackAddress is >= 0x700 and <= 0x7FE && (frame.StackAddress & 1) == 0
            && before.GetProperty("ssp").GetInt32() == frame.StackAddress - (call ? 0 : 2), "Unpaired RT, wrong stack bounds/address/width or target.");
        var n = result.Steps;
        Require(result.Trace.Count == n && result.ProgramReads.Count == 0 && result.UsedAssumptions.Count == 0 && n <= 1 && (result.Status != 0 || n == 1), "Incomplete/fake native instruction or unadmitted execution.");
        var a = before.GetProperty("accumulator").GetInt32(); var psw = before.GetProperty("psw").GetInt32();
        int[][] events = n == 0 ? [] : [[pc, target, a, a, psw, psw, 65536, 65536]];
        int[][] accesses = n == 0 ? [] : [[pc, frame.StackAddress, 16, call ? 1 : 0, frame.ReturnPc]];
        Require(Equal(stage.GetProperty("events"), JsonSerializer.SerializeToElement(events))
            && Equal(suffix.GetProperty("accesses"), JsonSerializer.SerializeToElement(accesses))
            && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(accesses.Where(v => v[3] == 1).Select(v => new[] { v[1], v[2], v[4] }).ToArray())), "CAL/RT native frame access/order/flags forged.");
        Require(result.ExecutedInstructionBytes.SequenceEqual(n == 0 ? [] : Enumerable.Range(pc, length)), "Wrong instruction extent; execution at063E or RTI.");
        if (n == 1)
        {
            var t = result.Trace[0]; Require(t.GetProperty("pc").GetInt32() == pc && t.GetProperty("nextPc").GetInt32() == target
                && t.GetProperty("instruction").GetString() == (call ? "CAL addr16" : "RT") && t.GetProperty("accumulator").GetInt32() == a && t.GetProperty("psw").GetInt32() == psw, "Wrong CAL form/RT target or accidental RTI restoration.");
        }
        var expected = JsonNode.Parse(before.GetRawText())!;
        expected["pc"] = n == 0 ? pc : target; expected["ssp"] = before.GetProperty("ssp").GetInt32() + (n == 0 ? 0 : call ? -2 : 2);
        Require(result.StopPc == expected["pc"]!.GetValue<int>() && stage.GetProperty("sspAfter").GetInt32() == expected["ssp"]!.GetValue<int>()
            && Equal(suffix.GetProperty("exit"), JsonSerializer.SerializeToElement(expected)), "Unbalanced SSP or forged complete CPU state; RT pops PC only.");
        return (JsonSerializer.SerializeToElement(expected), result.Status);
    }
}
