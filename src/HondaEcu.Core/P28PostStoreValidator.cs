using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28PostStoreCheckpoint(int Index, string Disposition, string PrefixDisposition, string PreviousProvenance,
    int? PreviousGeneration, P28PostStoreProjection? Expected, int? Result0150, P28AdaptiveFuelCheckpoint Prefix, JsonElement Actual);
public sealed record P28PostStoreSequence(string Image, int ScratchPattern, IReadOnlyList<P28PostStoreCheckpoint> Checkpoints);
public sealed record P28PostStoreComparison(int ScratchPattern, int Index, int? CurrentA, int? CurrentB,
    int? ResultA, int? ResultB, bool? PrefixGateDiverged, bool? SuffixDiverged, bool? Controls, string Effect);
public sealed record P28PostStoreReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId, string ScenarioDigest,
    string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets, IReadOnlyList<P28PostStoreSequence> Sequences,
    IReadOnlyList<P28PostStoreComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Disposition == "StrictMatch"),
        NativeTickInvocations = Sequences.SelectMany(s => s.Checkpoints).Sum(c => c.Prefix.NativeTicks),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        SuffixReasons = Sequences.SelectMany(s => s.Checkpoints).Where(c => c.Expected is not null).GroupBy(c => c.Expected!.Reason).ToDictionary(g => g.Key, g => g.Count()),
        NumericalWitnesses = Comparisons.Count(c => c.SuffixDiverged == true)
    };
    public string Scope => "Native post-store2204..223B on the same CPU/RAM; output0150, next static reader223D NotEvaluated. Earlier entries scripted; not ECU scheduler.";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time/degrees unavailable";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; one-field B in memory; no BIN/export/compensation/binding/receipt/token";
}
public static class P28PostStoreValidator
{
    public const string Operation = "fuelPostStoreChain";
    public static object CreateRequest(RomImage image, P28PostStoreScenario s)
    {
        var old = JsonSerializer.SerializeToElement(P28AdaptiveFuelValidator.CreateRequest(image, s.PrefixScenario), JsonDefaults.Create());
        return new
        {
            protocolVersion = 1,
            operation = Operation,
            images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
            scratchPatterns = new[] { 0, 85, 170 },
            allowAssumptions = Array.Empty<string>(),
            fuelPostStoreChain = new
            {
                formatVersion = 1,
                initialState = new { adaptive = old.GetProperty("adaptiveLimiterFuelGateChain").GetProperty("initialState"), s.InitialState.Previous03b4 },
                s.Calls,
                s.TraceCallIndexes
            }
        };
    }
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixContract = P28AdaptiveFuelValidator.ExpectedContracts()[0],
        nativeContinuation = new[] { 0x2204, 0x223B }, softwareOutput = new[] { 0x2239, 0x150, 16 },
        nextReader = new[] { 0x223D, 0x150, 16 }, sourceMasks = new[] { new[] { 0x125, 16 }, new[] { 0x12E, 16 } },
        initialHistory = "Declared previous03B4 once; subsequent history native store2203",
        assumptions = Array.Empty<string>(), physicalRpmAvailable = false, stop = "BeforeInstruction223B" } });
    internal static RomImage Mutate(RomImage original, P28PostStoreMutation m)
    {
        if (m.Kind != P28PostStoreMutationKind.FuelCell)
            return P28AdaptiveFuelValidator.Mutate(original, new(Enum.Parse<P28AdaptiveFuelMutationKind>(m.Kind.ToString()), m.Value));
        var cell = new P28FuelMapMutation(m.MapId!, m.Row!.Value, m.Column!.Value, checked((byte)m.Value));
        var offset = P28FuelMapContract.CellOffset(cell.MapId, cell.Row, cell.Column);
        Require(Math.Abs(m.Value - original.Span[offset]) is >= 1 and <= 8, "M2p cell change must be nonzero and at most8 raw counts.");
        return P28FuelMapInspector.Mutate(original, cell);
    }
    public static async Task<P28PostStoreReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28PostStoreScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : Mutate(original, scenario.Mutation);
        var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28PostStoreSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try
            {
                sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B"));
                contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!;
            }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2p native evidence.", e); }
        }
        var comparisons = new List<P28PostStoreComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i];
                    var ok = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    var adaptive = scenario.Mutation!.Kind != P28PostStoreMutationKind.FuelCell;
                    bool? controls = !ok ? null : !adaptive ||
                        a.Prefix.Continuation!.Fuel!.Corrected == b.Prefix.Continuation!.Fuel!.Corrected &&
                        a.Prefix.Continuation.Fuel.NativeFactor0158 == b.Prefix.Continuation.Fuel.NativeFactor0158 &&
                        a.Expected!.Previous == b.Expected!.Previous && a.Result0150 == b.Result0150;
                    bool? gate = !ok ? null : a.Prefix.GateTaken != b.Prefix.GateTaken;
                    bool? changed = !ok ? null : a.Result0150 != b.Result0150;
                    comparisons.Add(new(sequences[p].ScratchPattern, i, a.Expected?.Current, b.Expected?.Current, a.Result0150, b.Result0150,
                        gate, changed, controls, !ok ? "Incomplete" : changed == true ? "NativeNumericalWitness" : gate == true ? "03A2GateOnly; suffix uses ungated carrier" : "EqualOutput; inspect native reads/generations"));
                }
        IReadOnlyList<int> diff = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, diff, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }
    internal static IReadOnlyList<P28PostStoreSequence> Analyze(RomImage image, P28PostStoreScenario s, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts",
            "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "postStoreSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2p contract differs.");
        foreach (var k in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(k).GetArrayLength() == 0, "Foreign rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty("postStoreSequences"); Require(seq.GetArrayLength() == 3, "Scratch count differs.");
        var prefixView = JsonSerializer.SerializeToElement(new
        {
            runnerVersion = root.GetProperty("runnerVersion"),
            upstreamCommit = root.GetProperty("upstreamCommit"),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            adaptiveFuelSequences = seq.EnumerateArray().Select(p => new
            {
                scratchPattern = p.GetProperty("scratchPattern"),
                checkpoints = p.GetProperty("checkpoints").EnumerateArray().Select(c => c.GetProperty("prefix")).ToArray()
            }).ToArray()
        });
        var prefixes = P28AdaptiveFuelValidator.AnalyzeEvidence(image, s.PrefixScenario, prefixView, id, s.InitialState.Previous03b4,
            (p, i) => seq[p].GetProperty("checkpoints")[i].GetProperty("status").GetInt32() != 0);
        var reports = new List<P28PostStoreSequence>();
        for (var p = 0; p < 3; p++)
        {
            P28LimiterScenario.Shape(seq[p], "scratchPattern", "checkpoints");
            var pattern = new[] { 0, 85, 170 }[p]; Require(seq[p].GetProperty("scratchPattern").GetInt32() == pattern, "Scratch order differs.");
            var rows = seq[p].GetProperty("checkpoints"); Require(rows.GetArrayLength() == s.Calls.Count, "Dense rows required.");
            var model = new P28PostStorePrefixModel(image, s.PrefixScenario); var previous = s.InitialState.Previous03b4;
            int? generation = null; var retained = 0; var sources = new[] { pattern, pattern }; var stopped = false; var list = new List<P28PostStoreCheckpoint>();
            for (var i = 0; i < s.Calls.Count; i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "prefix", "sourceBytesBefore", "sourceBytesAfter", "snapshotWrites",
                    "word0150Before", "word0150After", "suffix", "postStoreWord0150");
                Require(row.GetProperty("index").GetInt32() == i && row.GetProperty("sourceBytesBefore").EnumerateArray().Select(v => v.GetInt32()).SequenceEqual(sources) &&
                    row.GetProperty("word0150Before").GetInt32() == retained, "New source/output history reseeded.");
                var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4, "Wrong whole-event status.");
                var prefix = prefixes[p].Checkpoints[i]; var suffix = row.GetProperty("suffix"); P28PostStoreProjection? expected = null;
                var provenance = generation.HasValue ? "NativeWritten" : "InitialHistory"; var oldGeneration = generation;
                if (stopped) Require(status == 4 && row.GetProperty("snapshotWrites").GetArrayLength() == 0 && suffix.ValueKind == JsonValueKind.Null, "Terminal event ran snapshots/suffix.");
                else
                {
                    var c = s.Calls[i]; sources = new[] { (sources[0] & ~16) | (c.Disable125 ? 16 : 0), (sources[1] & ~16) | (c.Disable12e ? 16 : 0) };
                    Require(Equal(row.GetProperty("snapshotWrites"), JsonSerializer.SerializeToElement(new[] { new[] { 0x125, 8, sources[0] }, new[] { 0x12E, 8, sources[1] } })), "Hidden/neighbor-overwriting snapshot.");
                    if (prefix.Disposition == "StrictMatch")
                    {
                        Require(suffix.ValueKind == JsonValueKind.Object, "Completed prefix lacks native continuation.");
                        var own = model.Step(c.Adaptive, previous);
                        expected = P28PostStoreModel.Project(previous, (ushort)own.Numeric.Corrected, c.Disable125, c.Disable12e, c.Adaptive.Fuel.Sources.Source0133, c.Adaptive.Fuel.Sources.Source014c);
                        var end = row.GetProperty("prefix").GetProperty("joint").GetProperty("fuel").GetProperty("boundaries");
                        var entry = end[end.GetArrayLength() - 1];
                        Require(Word(entry, 0) == previous && entry.GetProperty("accumulator").GetInt32() == own.Numeric.Corrected &&
                            Word(entry, 1) == own.Exit.Er1 && Word(entry, 2) == own.Numeric.Scaling.Output && Word(entry, 3) == own.Numeric.Corrected &&
                            entry.GetProperty("psw").GetInt32() == own.Exit.Psw, "2204 independent old/current/register/flag generation differs.");
                        var oracle = P28PostStoreEvidence.Build(own.Exit, (byte)sources[0], (byte)sources[1], c.Adaptive.Fuel.Sources.Source0133, c.Adaptive.Fuel.Sources.Source014c);
                        var native = ValidateSuffix(suffix, entry, oracle);
                        Require(status == native.Status && (native.Status != 0 || oracle.Accumulator == expected.Result), "Whole-event/arithmetic differs.");
                        foreach (var w in oracle.Accesses.Take(native.Steps == 0 ? 0 : oracle.AccessEnds[native.Steps - 1]).Where(w => w[3] == 1 && w[1] == 0x150)) retained = w[4];
                        previous = (ushort)own.Numeric.Store03b4; generation = i; // own model only, including same-value native stores.
                    }
                    else Require(suffix.ValueKind == JsonValueKind.Null && status == row.GetProperty("prefix").GetProperty("status").GetInt32(), "Suffix ran after incomplete prefix.");
                }
                Require(row.GetProperty("sourceBytesAfter").EnumerateArray().Select(v => v.GetInt32()).SequenceEqual(sources) &&
                    row.GetProperty("word0150After").GetInt32() == retained, "Native suffix source/output history differs.");
                Require(status == 0 ? row.GetProperty("postStoreWord0150").GetInt32() == retained : row.GetProperty("postStoreWord0150").ValueKind == JsonValueKind.Null, "Partial/retained output presented as fresh.");
                var disposition = status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                list.Add(new(i, disposition, prefix.Disposition, provenance, oldGeneration, expected, status == 0 ? retained : null, prefix,
                    ReportRow(row, s.TraceCallIndexes.Contains(i))));
                stopped |= status != 0;
            }
            reports.Add(new(id, pattern, list.AsReadOnly()));
        }
        return reports.AsReadOnly();
    }
    internal static P28AcquisitionStageResult ValidateSuffix(JsonElement suffix, JsonElement prefixExit, P28FuelAdditiveOracle own)
    {
        P28LimiterScenario.Shape(suffix, "entry", "exit", "stage", "accesses");
        var entry = suffix.GetProperty("entry"); var exit = suffix.GetProperty("exit");
        P28FuelFactorValidator.ValidateBoundary(entry); P28FuelFactorValidator.ValidateBoundary(exit);
        Require(Equal(entry, prefixExit) && entry.GetProperty("pc").GetInt32() == 0x2204, "Extra enter/reset/reload on2204.");
        var stage = suffix.GetProperty("stage"); P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter");
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 48, 0, [], null)!;
        var events = Matrix(stage.GetProperty("events"), 8, 48); var accesses = Matrix(suffix.GetProperty("accesses"), 5, 192);
        P28FuelAdditiveEvidence.RequireEventPrefix(stage, own);
        Require(events.Length == r.Steps && r.Trace.Count == r.Steps && (r.Status != 0 || events.Length == own.Events.Count), "Missing suffix native instructions.");
        P28FuelCalculationValidator.ValidateEventContinuity(events, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(),
            exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        for (var n = 0; n < events.Length; n++) Require(r.Trace[n].GetProperty("pc").GetInt32() == events[n][0] && r.Trace[n].GetProperty("nextPc").GetInt32() == events[n][1] &&
            r.Trace[n].GetProperty("accumulator").GetInt32() == events[n][3] && r.Trace[n].GetProperty("psw").GetInt32() == events[n][5], "Trace contradicts event flags.");
        var count = events.Length == 0 ? 0 : own.AccessEnds[events.Length - 1];
        var writes = own.Accesses.Take(count).Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray();
        Require(Equal(accesses, own.Accesses.Take(count).ToArray()) && Equal(stage.GetProperty("writes"), JsonSerializer.SerializeToElement(writes)), "Wrong native source/register/width/ordered writes.");
        var extents = own.Events.Take(events.Length).SelectMany((e, n) => Enumerable.Range(e[0], own.Lengths[n])).Distinct().Order().ToArray();
        Require(r.ExecutedInstructionBytes.SequenceEqual(extents) && r.StopPc == (events.Length == 0 ? 0x2204 : events[^1][1]) &&
            exit.GetProperty("pc").GetInt32() == r.StopPc && (r.Status != 0 || r.StopPc == 0x223B), "Wrong extent/exit.");
        Require(r.UsedAssumptions.Count == 0 && r.ProgramReads.Count == 0, "Foreign permission/program read.");
        var regs = events.Length == 0 ? Enumerable.Range(0, 4).Select(n => Word(entry, n)).ToArray() : own.RegisterEnds[events.Length - 1];
        Require(Enumerable.Range(0, 4).All(n => Word(exit, n) == regs[n]), "Intentional er0/er1 clobbers or retained er2/er3 forged.");
        foreach (var k in new[] { "lrb", "x1", "x2", "dp", "usp", "ssp" }) Require(Equal(entry.GetProperty(k), exit.GetProperty(k)), "Suffix clobbered a retained carrier/bank/stack.");
        Require(stage.GetProperty("sspAfter").GetInt32() == 0x7FE && exit.GetProperty("ssp").GetInt32() == 0x7FE, "Stack unbalanced.");
        return r;
    }
    private static JsonElement ReportRow(JsonElement row, bool trace)
    {
        if (trace) return row.Clone();
        var n = JsonNode.Parse(row.GetRawText())!;
        void Strip(JsonNode? v)
        {
            if (v is JsonObject o) foreach (var k in o.ToArray()) { if (k.Key == "trace") o[k.Key] = new JsonArray(); else Strip(k.Value); }
            else if (v is JsonArray a) foreach (var child in a) Strip(child);
        }
        Strip(n); return JsonSerializer.SerializeToElement(n);
    }
}
