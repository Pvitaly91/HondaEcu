using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

internal sealed record P28PostReturnSelectorOracle(List<int[]> Events, List<int[]> Accesses, List<int> AccessEnds, int[] Lengths);
internal static class P28PostReturnSelectorModel
{
    internal static readonly string[] Mnemonics = ["LB A, off N8", "STB A, r0", "ANDB A, #N8", "SBR off N8", "INCB r0", "LB A, r0", "ANDB A, #N8", "STB A, off N8"];
    internal static P28PostReturnSelectorOracle Build(int selector, int entryA, int entryPsw, int byte0128, int initialR0)
    {
        if (selector is < 0 or > 3 || byte0128 is < 0 or > 255 || initialR0 is < 0 or > 255 || (entryPsw & 4096) != 0) throw new InvalidDataException("Unadmitted retained post-return state.");
        var a = entryA; var psw = entryPsw; var r0 = initialR0; var gate = byte0128;
        var events = new List<int[]>(); var accesses = new List<int[]>(); var ends = new List<int>();
        void Flag(int mask, bool set) => psw = set ? psw | mask : psw & ~mask;
        void Load(int value) { a = (a & 0xFF00) | value; Flag(4096, false); Flag(16384, value == 0); }
        var pcs = new[] { 0x063E, 0x0640, 0x0641, 0x0643, 0x0646, 0x0647, 0x0648, 0x064A };
        var lengths = new[] { 2, 1, 2, 3, 1, 1, 2, 2 };
        for (var n = 0; n < pcs.Length; n++)
        {
            var pc = pcs[n]; var oldA = a; var oldPsw = psw;
            void Access(int address, bool write, int value) => accesses.Add([pc, address, 8, write ? 1 : 0, value]);
            switch (pc)
            {
                case 0x063E: Access(0x13C, false, selector); Load(selector); break;
                case 0x0640: r0 = a & 255; Access(0x108, true, r0); break;
                case 0x0641: a &= 0xFF01; Flag(16384, (a & 255) == 0); break;
                case 0x0643: Access(0x128, false, gate); var bit = 1 << (a & 7); Flag(16384, (gate & bit) == 0); gate |= bit; Access(0x128, true, gate); break;
                case 0x0646: Access(0x108, false, r0); Flag(8192, (r0 & 15) == 15); r0 = (r0 + 1) & 255; Flag(16384, r0 == 0); Access(0x108, true, r0); break;
                case 0x0647: Access(0x108, false, r0); Load(r0); break;
                case 0x0648: a &= 0xFF03; Flag(16384, (a & 255) == 0); break;
                case 0x064A: Access(0x13C, true, a & 255); break;
            }
            events.Add([pc, pc + lengths[n], oldA, a, oldPsw, psw, 65536, 65536]); ends.Add(accesses.Count);
        }
        return new(events, accesses, ends, lengths);
    }
    internal static (JsonElement After, int Status, int Steps, int[][] Ram) Validate(JsonElement output, JsonElement before, int selector, int byte0128)
    {
        P28LimiterScenario.Shape(output, "entry", "exit", "stage", "accesses");
        Require(before.GetProperty("pc").GetInt32() == 0x063E && before.GetProperty("lrb").GetInt32() == 0x21 && (before.GetProperty("psw").GetInt32() & 7) == 2 && Equal(output.GetProperty("entry"), before), "Post-return must be actual RT exit without PC/A/r0/PSW/bank/stack seed.");
        P28FuelFactorValidator.ValidateBoundary(before); P28FuelFactorValidator.ValidateBoundary(output.GetProperty("exit"));
        var own = Build(selector, before.GetProperty("accumulator").GetInt32(), before.GetProperty("psw").GetInt32(), byte0128, before.GetProperty("registers")[0].GetInt32());
        var stage = output.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 8, 0, [], null)!; var n = r.Steps;
        Require(n <= 8 && r.Trace.Count == n && r.ProgramReads.Count == 0 && r.UsedAssumptions.Count == 0 && (r.Status != 0 || n == 8), "Incomplete/assumed/timer post-return execution.");
        var events = own.Events.Take(n).ToArray(); var accesses = own.Accesses.Take(n == 0 ? 0 : own.AccessEnds[n - 1]).ToArray();
        Require(Equal(stage.GetProperty("events"), JsonSerializer.SerializeToElement(events)) && Equal(output.GetProperty("accesses"), JsonSerializer.SerializeToElement(accesses)) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(accesses.Where(v => v[3] == 1).Select(v => new[] { v[1], v[2], v[4] }).ToArray())), "Selector arithmetic/old/new/0128/r0/width/address/flags/chronology forged.");
        Require(r.ExecutedInstructionBytes.SequenceEqual(events.SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).Distinct().Order()), "Skipped instruction or execution of064C/caller/timer/IRQ.");
        for (var i = 0; i < n; i++) Require(r.Trace[i].GetProperty("pc").GetInt32() == events[i][0] && r.Trace[i].GetProperty("nextPc").GetInt32() == events[i][1] && r.Trace[i].GetProperty("instruction").GetString() == Mnemonics[i] && r.Trace[i].GetProperty("accumulator").GetInt32() == events[i][3] && r.Trace[i].GetProperty("psw").GetInt32() == events[i][5], "Detached exact-form native trace.");
        var expected = JsonNode.Parse(before.GetRawText())!; var registers = before.GetProperty("registers").EnumerateArray().Select(v => v.GetInt32()).ToArray();
        foreach (var w in accesses.Where(v => v[3] == 1 && v[1] == 0x108)) registers[0] = w[4];
        var psw = n == 0 ? before.GetProperty("psw").GetInt32() : events[^1][5]; var stop = n == 0 ? 0x063E : events[^1][1];
        expected["pc"] = stop; expected["accumulator"] = n == 0 ? before.GetProperty("accumulator").GetInt32() : events[^1][3]; expected["psw"] = psw; expected["dd"] = (psw & 4096) != 0; expected["registers"] = JsonSerializer.SerializeToNode(registers);
        Require(r.StopPc == stop && Equal(output.GetProperty("exit"), JsonSerializer.SerializeToElement(expected)) && stage.GetProperty("sspAfter").GetInt32() == before.GetProperty("ssp").GetInt32(), "Post-return full CPU/pointer/register/SSP continuity forged.");
        return (JsonSerializer.SerializeToElement(expected), r.Status, n, accesses);
    }
}
public sealed record P28PostReturnSelectorCheckpoint(int Index, string ProducerDisposition, string SelectorHandoff,
    int SelectorBefore, int SelectorAfter, P28QuartetGeneration? IncomingGeneration, P28QuartetGeneration? Reader0584Generation,
    P28QuartetGeneration? Reader063eGeneration, P28QuartetGeneration? SelectorGeneration, int? SelectedSlot, int? SelectedAddress,
    P28QuartetGeneration? SelectedQuartetGeneration, bool ProducerCompleted, bool ProducerWriteObserved, bool Wrap3To0,
    int NativeSteps, int Byte0128Before, int Byte0128After, JsonElement After, JsonElement Actual);
internal sealed class P28PostReturnSelectorValidation(byte initial)
{
    internal byte Initial => initial;
    internal readonly List<P28PostReturnSelectorCheckpoint>[] Rows = [[], [], []];
    private readonly int[] _selector = [initial, initial, initial];
    private readonly P28QuartetGeneration?[] _generation = new P28QuartetGeneration?[3];
    private readonly bool[] _completed = new bool[3];
    private readonly string[] _handoff = new string[3];
    private readonly P28QuartetGeneration?[] _reader = new P28QuartetGeneration?[3];
    internal void Start(int p, int i, JsonElement row, P28QuartetHandoffCheckpoint prefix)
    {
        Require(row.GetProperty("selectorBefore").GetInt32() == _selector[p] && Equal(row.GetProperty("incomingSelectorGeneration"), JsonSerializer.SerializeToElement(_generation[p], JsonDefaults.Create())), "Selector source/reseed/stale incoming native generation.");
        var journal = Matrix(prefix.Actual.GetProperty("continuityJournal"), 6, 32768);
        var read = Array.FindIndex(journal, v => v.SequenceEqual(new[] { 1, 0x0584, 0x13C, 8, 0, _selector[p] }));
        Require(!journal.Any(v => v[4] == 1 && v[2] < 0x13D && v[2] + v[3] / 8 > 0x13C), "Host/native overlapping selector writer during event scheduling.");
        _reader[p] = read >= 0 ? _generation[p] : null;
        _handoff[p] = read < 0 ? prefix.Disposition == "NotRun" ? "NotRun" : "NextEventSelectorNotReached" : _generation[p] is null ? "InitialSelectorControl" : prefix.SelectedGeneration is not null && _completed[p] ? "NativeSelectorHandoffStrict" : "NativeSelectorReadWithoutQuartetHandoff";
        Require(Equal(row.GetProperty("reader0584Generation"), JsonSerializer.SerializeToElement(_reader[p], JsonDefaults.Create())) && row.GetProperty("selectorHandoff").GetString() == _handoff[p], "Wrong0584 generation or initial/control misclassified as native handoff.");
        if (_handoff[p] == "NativeSelectorHandoffStrict") Require(_generation[p]!.WriterPc == 0x064A && _generation[p]!.EventIndex < i && prefix.SelectedSlot == _selector[p] && prefix.SelectedAddress == 0x3B6 + 2 * _selector[p], "Correct numeric selector from wrong producer/slot/address.");
    }
    internal (JsonElement After, string Disposition, int[][] Ram) Finish(int p, int i, JsonElement row, JsonElement before, string disposition,
        Dictionary<int, int> ram, Dictionary<int, int> selectorRam, int[] registers, List<int[]> all, P28QuartetHandoffCheckpoint prefix)
    {
        var old = _selector[p]; var incoming = _generation[p]; var old128 = ram[0x128]; var completed = false; var observed = false; var steps = 0; int[][] native = [];
        var output = row.GetProperty("postReturn"); P28QuartetGeneration? reader063 = null;
        if (disposition is "CallReturnStrict" or "CallReturnGateBypass")
        {
            Require(output.ValueKind == JsonValueKind.Object && row.GetProperty("nativeRt").GetProperty("suffix").GetProperty("stage").GetProperty("result").GetProperty("steps").GetInt32() == 1, "Post-return without native RT proof.");
            var result = P28PostReturnSelectorModel.Validate(output, before, old, old128); before = result.After; native = result.Ram; steps = result.Steps;
            if (native.Any(v => v[0] == 0x063E)) reader063 = incoming;
            Require(!all.Any(v => v[0] == 0 && v[4] == 1 && v[2] < 0x13D && v[2] + v[3] / 8 > 0x13C), "Selector overwritten before063E read.");
            var order = all.Count(v => v[4] == 1);
            foreach (var w in native.Where(v => v[3] == 1))
            {
                var g = new P28QuartetGeneration(w[0], i, order++, w[4]); ram[w[1]] = w[4];
                if (w[1] == 0x108) registers[0] = w[4];
                if (w[1] == 0x13C) { Require(w[0] == 0x064A && w[2] == 8, "Wrong native selector producer."); _selector[p] = w[4]; _generation[p] = g; selectorRam[0x13C] = w[4]; observed = true; }
            }
            all.AddRange(native.Select(v => new[] { 0, v[0], v[1], v[2], v[3], v[4] }));
            completed = result.Status == 0;
            disposition = completed ? disposition == "CallReturnStrict" ? "PostReturnSelectorStrict" : "PostReturnSelectorGateBypass" : "SelectorProducerPartial";
        }
        else Require(output.ValueKind == JsonValueKind.Null, "Post-return ran after terminal or without native return.");
        _completed[p] = completed;
        Require(row.GetProperty("selectorAfter").GetInt32() == _selector[p] && Equal(row.GetProperty("selectorGeneration"), JsonSerializer.SerializeToElement(_generation[p], JsonDefaults.Create())) && Equal(row.GetProperty("reader063eGeneration"), JsonSerializer.SerializeToElement(reader063, JsonDefaults.Create())), "Forged selector value/wrap/generation/063E source or partial rollback.");
        Rows[p].Add(new(i, disposition, _handoff[p], old, _selector[p], incoming, _reader[p], reader063, _generation[p], prefix.SelectedSlot, prefix.SelectedAddress, prefix.SelectedGeneration, completed, observed, completed && old == 3 && _selector[p] == 0, steps, old128, ram[0x128], before.Clone(), row.Clone()));
        return (before, disposition, native);
    }
}
