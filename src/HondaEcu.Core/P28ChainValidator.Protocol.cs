using System.Text.Json;

namespace HondaEcu.Core;

public static partial class P28ChainValidator
{
    internal static JsonElement EntryContracts() => JsonSerializer.SerializeToElement(new object[] { new {
        id = Operation, version = 1, initialState = "OncePerImageScratchSequence",
        schedule = new[] { "ScriptedInputs", "Acquisition", "NativeCounterBodies", "ScheduledG", "ScheduledF", "ScheduledDecision" },
        boundaries = new[] { new[] { 0x56BE, 0x5719 }, new[] { 0x5BD0, 0x5BD9 }, new[] { 0x3CEB, 0x3CF3 }, new[] { 0x0772, 0x07A5 }, new[] { 0x07C7, 0x0822 }, new[] { 0x122C, 0x12FC } },
        budgets = new[] { 128, 4, 4, 192, 128, 512 }, entryLrb = new[] { 0x21, 0x20, 0x20, 0x40, 0x40, 0x20 },
        entryPsw = new[] { 0x1102, 0x0101, 0x0101, 0x1101, 0x1101, 0x0101 }, entryUsp = new[] { 0x280, 0x280, 0x280, 0x180, 0x180, 0x280 },
        sspInitial = 0x7FE, sspReseed = false, data011EMask = 24, stageInputs = "NativeSamplesToGToTAndSToFToCodeToPersistentDecision",
        captureScope = "AcquisitionOnly", p1Scope = "DecisionOnlyLatchAlwaysRetained", p1Mode = "AllOutputDataRegisterOnlyNoExternalBus",
        tickUnits = "NativeBodyCallsNotMilliseconds", permissions = Permissions, terminalStop = "NoLaterStagesOrEventsOrInputs", traceLimit = 128,
        physicalRpmAvailable = false, hardwareFullBoot = "NotRun", guiR3 = "paused/NotRun"
    } }, JsonDefaults.Create(false));

    private static P28ChainObservedStage ParseStage(JsonElement e, IReadOnlyList<string> allowed)
    {
        Shape(e, "id", "status", "stateBefore", "stateAtEntry", "stateAfter", "architectureBefore", "architectureAtEntry", "architectureAfter",
            "execution", "nativeWrites", "peripheralAccesses", "gateEvents", "tickRuns", "cumulativeAssumptions");
        var id = e.GetProperty("id").GetString()!; if (!StageIds.Contains(id)) throw Protocol("Unknown stage.");
        var (budget, permission) = id switch
        {
            "G" => (192, Permissions[0]),
            "F" => (128, Permissions[1]),
            "Decision" => (512, Permissions[2]),
            "Acquisition" => (128, (string?)null),
            _ => (512, null)
        };
        var writes = Matrix(e, "nativeWrites", 3, 1024);
        if (writes.Any(w => w[0] > 4095 || w[1] is not (8 or 16) || w[2] > (w[1] == 8 ? 255 : 65535))) throw Protocol("Invalid native store.");
        return new(id, Int(e, "status", 0, 5), State(e.GetProperty("stateBefore")), State(e.GetProperty("stateAtEntry")), State(e.GetProperty("stateAfter")),
            Architecture(e.GetProperty("architectureBefore")), Architecture(e.GetProperty("architectureAtEntry")), Architecture(e.GetProperty("architectureAfter")),
            P28AcquisitionValidator.ParseStage(e.GetProperty("execution"), budget, 0, allowed, permission), writes,
            Matrix(e, "peripheralAccesses", 4, 128), Matrix(e, "gateEvents", 8, 32), Matrix(e, "tickRuns", 7, 128), Assumptions(e, "cumulativeAssumptions", allowed));
    }
    private static P28ChainState State(JsonElement e)
    { P28ChainScenario.StateShape(e); return P28ChainScenario.Snapshot(e.Deserialize<P28ChainState>(P28StatefulScenario.Options)!); }
    private static P28ChainArchitecture Architecture(JsonElement e)
    {
        Shape(e, "pc", "accumulator", "lrb", "psw", "ssp", "banks", "pointing", "stackWord");
        var a = e.Deserialize<P28ChainArchitecture>(P28StatefulScenario.Options)!;
        if (a.Banks.Count != 24 || a.Pointing.Count != 16) throw Protocol("Architecture snapshot size differs."); return a;
    }
    private static void Shape(JsonElement e, params string[] names)
    {
        if (e.ValueKind != JsonValueKind.Object || !e.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal).SequenceEqual(names.Order(StringComparer.Ordinal)))
            throw Protocol("Missing, unknown or duplicate response fields.");
    }
    private static int Int(JsonElement e, string name, int min, int max)
    { var v = e.GetProperty(name).GetInt32(); if (v < min || v > max) throw Protocol("Integer out of bounds."); return v; }
    private static bool? Bool(JsonElement e, string name) => e.GetProperty(name).Deserialize<bool?>();
    private static IReadOnlyList<int> Integers(JsonElement e, string name, int min, int max, int count, bool exact = false)
    {
        var a = e.GetProperty(name); if (a.GetArrayLength() > count || exact && a.GetArrayLength() != count) throw Protocol("Array bound differs.");
        var values = a.EnumerateArray().Select(v => v.GetInt32()).ToArray();
        if (values.Any(v => v < min || v > max)) throw Protocol("Array integer out of bounds."); return Array.AsReadOnly(values);
    }
    private static IReadOnlyList<int[]> Matrix(JsonElement e, string name, int width, int maximum)
    {
        var a = e.GetProperty(name); if (a.GetArrayLength() > maximum) throw Protocol("Journal bound exceeded.");
        return Array.AsReadOnly(a.EnumerateArray().Select(row =>
        {
            if (row.GetArrayLength() != width) throw Protocol("Journal width differs."); var values = row.EnumerateArray().Select(v => v.GetInt32()).ToArray();
            if (values.Any(v => v is < 0 or > 65536)) throw Protocol("Journal integer out of bounds."); return values;
        }).ToArray());
    }
    private static IReadOnlyList<string> Assumptions(JsonElement e, string name, IReadOnlyList<string> allowed)
    {
        var a = e.GetProperty(name).Deserialize<string[]>()!;
        if (a.Length > 3 || a.Distinct(StringComparer.Ordinal).Count() != a.Length || a.Any(v => !allowed.Contains(v)) || !a.SequenceEqual(a.Order(StringComparer.Ordinal)))
            throw Protocol("Invalid cumulative assumption history."); return Array.AsReadOnly(a);
    }
    private static readonly int[] PersistentBytes = [0x22, 0xAE, 0xB6, 0xB8, 0xC4, 0xC5, 0xCC, 0xD9, 0xEE, 0xEF, 0xF3,
        0x119, 0x11A, 0x11B, 0x11C, 0x11E, 0x11F, 0x127, 0x128, 0x131, 0x132, 0x133, 0x136, 0x137, 0x198, 0x199,
        0x1D8, 0x1D9, 0x1DF, 0x217, 0x231, 0x360, 0x361, 0x362, 0x363, 0x364, 0x365, 0x366, 0x367, 0x368, 0x369, 0x36A, 0x36B];
    private static bool TouchesPersistent(int[] write) => Enumerable.Range(write[0], write[1] / 8).Any(PersistentBytes.Contains);
    private static int[][] Ranges(string id) => id switch
    {
        "Acquisition" => [[0x56BE, 0x56DF], [0x5701, 0x5719]],
        "G" => [[0x0772, 0x07A5], [0x7AEC, 0x7AFE]],
        "F" => [[0x07C7, 0x0822]],
        "Decision" => [[0x122C, 0x12FC], [0x5839, 0x586E]],
        _ => [[0x5BD0, 0x5BD9], [0x3CEB, 0x3CF3]],
    };
    private static void ValidateExecution(P28ChainObservedStage stage, P28ChainEvent input, bool traceAllowed)
    {
        if (stage.Execution is not { } e)
        {
            if (stage.Status is not (4 or 5) || stage.Status == 5 && (stage.Id != "Acquisition" || (stage.StateBefore.Acquisition.Data011F & 4) == 0) ||
                stage.NativeWrites.Count != 0 || stage.TickRuns.Count != 0 || stage.PeripheralAccesses.Count != 0 || stage.GateEvents.Count != 0 ||
                !Equal(stage.StateBefore, stage.StateAfter) || !Equal(stage.ArchitectureBefore, stage.ArchitectureAtEntry) || !Equal(stage.ArchitectureBefore, stage.ArchitectureAfter))
                throw Protocol("NotRun/refused mode fabricated execution or state.");
            return;
        }
        if (stage.Status == 4 || stage.Status != e.Status && !(stage.Status == 5 && e.Status == 1) ||
            e.Status == 0 && (e.Steps == 0 || e.Error is not null || e.ExecutedInstructionBytes.Count == 0) ||
            e.Status != 0 && string.IsNullOrWhiteSpace(e.Error) ||
            e.Steps == 0 && e.ExecutedInstructionBytes.Count != 0 || e.ExecutedInstructionBytes.Any(pc => !Ranges(stage.Id).Any(r => pc >= r[0] && pc < r[1])) ||
            !traceAllowed && e.Trace.Count != 0 || e.Trace.Count > Math.Min(128, e.Steps)) throw Protocol("Execution extents/status/trace contract differs.");
        if (stage.Id != "Decision" && (e.ProgramReads.Count != 0 || stage.GateEvents.Count != 0) ||
            stage.Id == "Decision" && e.ProgramReads.Any(a => a is not (>= 0x6542 and < 0x6566) && a != 0x60FA)) throw Protocol("Stage program-data/gate scope differs.");
        if (stage.Id != "Acquisition" && stage.PeripheralAccesses.Count != 0) throw Protocol("Frozen capture escaped acquisition scope.");
        if (stage.Id is "G" or "F" or "Decision")
        {
            var pc = stage.Id == "G" ? 0x077E : stage.Id == "F" ? 0x07F8 : 0x12B4;
            if ((e.UsedAssumptions.Count == 1) != (e.ExecutedInstructionBytes.Contains(pc) && e.ExecutedInstructionBytes.Contains(pc + 1)))
                throw Protocol("Assumption use disagrees with executed exact-form extent.");
        }
        foreach (var w in stage.NativeWrites.Where(w => !TouchesPersistent(w)))
            foreach (var a in Enumerable.Range(w[0], w[1] / 8))
                if (!(a is >= 0x88 and < 0x98 || a is >= 0x100 and < 0x110 || a is >= 0x200 and < 0x208 || a is >= 0x7FE and < 0x800))
                    throw Protocol("Unaccounted native memory write outside persistent/register/stack ownership.");
        if (stage.Id != "NativeCounterBodies")
        { if (stage.TickRuns.Count != 0) throw Protocol("Ticks in an unrelated stage."); return; }
        var schedule = new List<(int Entry, int Target, int Exit)>();
        for (var i = 0; i < input.FastTicks; i++) { schedule.Add((0x5BD0, 0x1D8, 0x5BD9)); schedule.Add((0x5BD0, 0x1D9, 0x5BD9)); }
        for (var i = 0; i < input.SlowTicks; i++) { schedule.Add((0x5BD0, 0x1DF, 0x5BD9)); schedule.Add((0x3CEB, 0xF3, 0x3CF3)); }
        if (stage.TickRuns.Count == 0 || stage.TickRuns.Count > schedule.Count || e.Status == 0 && stage.TickRuns.Count != schedule.Count || e.Steps != stage.TickRuns.Sum(r => r[4]))
            throw Protocol("Native counter denominator differs.");
        for (var i = 0; i < stage.TickRuns.Count; i++)
        {
            var r = stage.TickRuns[i]; var s = schedule[i];
            if (r[0] != s.Entry || r[1] != s.Target || r[4] > 4 || r[3] > 5 || r[3] == 4 || r[3] == 3 && r[4] != 4 ||
                r[3] == 0 && (r[2] != s.Exit || r[4] < 2 || r[5] != r[6]) || i < stage.TickRuns.Count - 1 && r[3] != 0)
                throw Protocol("Native body target/exit/budget/stack differs.");
        }
    }
}
