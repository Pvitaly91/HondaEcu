using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28FuelFactorCheckpoint(int Index, string Disposition, string PrefixDisposition, int? SelectedOrigin,
    int? Data0140, int? NativeFactor0158, int? Factor0158Before, int? Factor0158After, string FactorProvenance,
    int? Correction, int? Component, int? Corrected, int? Store03a2, int? Store03b4,
    P28FuelFactorProjection? Expected, IReadOnlyList<string> Differences, JsonElement Actual);
public sealed record P28FuelFactorSequence(string Image, int ScratchPattern, IReadOnlyList<P28FuelFactorCheckpoint> Checkpoints);
public sealed record P28FuelFactorComparison(int ScratchPattern, int Index, bool? CellRead, bool? Controls,
    int? Data0140A, int? Data0140B, int? FactorA, int? FactorB, int? ComponentA, int? ComponentB,
    int? CorrectedA, int? CorrectedB, bool? Witness, string Effect);
public sealed record P28FuelFactorReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, P28FuelMapMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28FuelFactorSequence> Sequences, IReadOnlyList<P28FuelFactorComparison> Comparisons, JsonElement EntryContract)
{
    public bool HasFailure => Sequences.SelectMany(s => s.Checkpoints).Any(c => c.Disposition != "StrictMatch") || Comparisons.Any(c => c.Controls == false);
    public object Summary => new
    {
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        NativeEvents = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Corrected is not null),
        NativeFactorWrites = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.FactorProvenance == "Written"),
        Witnesses = Comparisons.Count(c => c.Witness == true),
        Effects = Comparisons.GroupBy(c => c.Effect).ToDictionary(g => g.Key, g => g.Count())
    };
    public string CallerBoundary => "1350->1F43 and1FB7->2194 scripted ABI; factor detour native; 2194->2204 native; stop-before2204";
    public string FactorOwnership => "Code-owned diagnostic scratch0158, then fresh native word7A99 before native reader21DD; no established hold path";
    public string ReachableFactorDomain => "012C.4 clear:0..253; set:0..2037; upper015F is code-owned zero";
    public string NotEvaluated => "Full source producers, boot/scheduler, producer x8 overflow clamp, component saturation and application upper clamp (unreachable in this closed original domain)";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw; physical fuel/time units and degrees unavailable";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public string StrictM2i => "Blocked on47 81; unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None; optional one-cell B exists in memory only";
}

public static class P28FuelFactorValidator
{
    public const string Operation = "fuelFactorProductionChain";
    public static object CreateRequest(RomImage image, P28FuelFactorScenario s) => new
    {
        protocolVersion = 1,
        operation = Operation,
        images = new[] { new { id = "baseline", rom = image.ToArray().Select(b => (int)b).ToArray() } },
        scratchPatterns = new[] { 0, 85, 170 },
        allowAssumptions = Array.Empty<string>(),
        fuelFactorProductionChain = new
        {
            formatVersion = 1,
            initialState = s.InitialState.Fuel.Fuel,
            s.InitialState.CallerGate0124,
            s.InitialState.Mode012b,
            s.InitialState.ProducerMode012c,
            s.InitialState.ProducerSelector012f,
            s.InitialState.Hysteresis0130,
            s.Calls,
            s.TraceCallIndexes
        }
    };
    internal static JsonElement ExpectedContracts() => JsonSerializer.SerializeToElement(new[] { new {
        id = Operation, formatVersion = 1, prefixEntries = new[] { 0x0A0C, 0x0A62, 0x12FC }, continuousFuelTail = new[] { 0x12FC, 0x1350 },
        scriptedHandoffs = new[] { new[] { 0x1350, 0x1F43 }, new[] { 0x1FB7, 0x2194 } }, nativeFactorTail = new[] { 0x1F43, 0x1FB7 },
        factorCodeRanges = new[] { new[] { 0x1F43, 0x1FB7 }, new[] { 0x7A99, 0x7AAB } }, factorDetours = new[] { new[] { 0x1FB4, 0x7A99 }, new[] { 0x7AA8, 0x1FB7 } }, factorBudget = 128,
        nativeAdditiveTail = new[] { 0x2194, 0x2204 }, checkpoints = new[] { 0x21DB, 0x21F2 }, lrb = 0x20, psw = 0x0101, usp = 0x280, ssp = 0x7FE,
        hostTransitionWrites = new[] { new[] { 2, 16, 0x20 }, new[] { 4, 16, 0x0101 }, new[] { 0x8E, 16, 0x280 } },
        factorSourceWords = new[] { 0x15A, 0x15C, 0x160, 0x162 }, factorSourceBytes = new[] { 0x15E, 0x164, 0x165, 0x166, 0x167, 0x168, 0x133 },
        upper015f = "CodeOwnedZeroOnce; no recovered high-byte producer", initial0158 = "CodeOwnedDiagnosticScratchWord; never an input or produced value",
        producerModeMask = new[] { 0x12C, 16 }, producerSelectorMask = new[] { 0x12F, 128 }, nativeHysteresisMask = new[] { 0x130, 64 },
        source0144Mask = 255, upper0145 = "CodeOwnedZero; no recovered high-byte producer", nativeModeMask = new[] { 0x12B, 8 }, gate217A = "StaticPrecondition; bypass NotEvaluated",
        nativeSources = new[] { new[] { 0x134E, 0x140, 16 }, new[] { 0x7A99, 0x158, 16 } }, nativeReaders = new[] { new[] { 0x21DB, 0x140, 16 }, new[] { 0x21DD, 0x158, 16 } },
        softwareStores = new[] { 0x3A2, 0x3B4 }, helpers = new[] { new[] { 0x596C, 0x5991 }, new[] { 0x5958, 0x596B } },
        vector4 = new[] { 0x30, 0x5958, 0x21F5 }, stackRange = new[] { 0x7FE, 0x800 }, initialSelectorOnly = true,
        holdPaths = "None in supported closed producer", traceLimit = 8, assumptions = Array.Empty<string>(), units = "raw; physical units unknown" } });

    public static async Task<P28FuelFactorReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28FuelFactorScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null); P28FuelMapInspector.LayoutGuard(original);
        if (original.Span[0x60E5] != 0 || original.Span[0x60F8] != 0) throw new InvalidDataException("M2m requires unchanged exact-original helper/reader configuration.");
        var child = scenario.Mutation is null ? null : P28FuelMapInspector.Mutate(original, scenario.Mutation);
        if (child is not null) P28FuelMapInspector.AdmitMutation(original, child, scenario.Mutation!);
        var sequences = new List<P28FuelFactorSequence>(); JsonElement contract = default; string version = "";
        foreach (var image in child is null ? new[] { original } : new[] { original, child })
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try { sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B")); contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!; }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2m native evidence.", e); }
        }
        var comparisons = new List<P28FuelFactorComparison>();
        if (child is not null)
        {
            var offset = P28FuelMapContract.CellOffset(scenario.Mutation!.MapId, scenario.Mutation.Row, scenario.Mutation.Column);
            for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i]; var comparable = a.Disposition == "StrictMatch" && b.Disposition == "StrictMatch";
                    bool? read = comparable ? b.Actual.GetProperty("prefix").GetProperty("lookup").GetProperty("result").GetProperty("programReads").EnumerateArray().Any(n => n.GetInt32() == offset) : null;
                    bool? controls = comparable ? a.SelectedOrigin == b.SelectedOrigin && a.NativeFactor0158 == b.NativeFactor0158 && a.Correction == b.Correction &&
                        Equal(a.Actual.GetProperty("sourcesAfter"), b.Actual.GetProperty("sourcesAfter")) && Equal(a.Actual.GetProperty("modeAfter"), b.Actual.GetProperty("modeAfter")) &&
                        Equal(a.Actual.GetProperty("hysteresisAfter"), b.Actual.GetProperty("hysteresisAfter")) && Equal(a.Actual.GetProperty("prefix").GetProperty("position"), b.Actual.GetProperty("prefix").GetProperty("position")) : null;
                    bool? witness = comparable ? read == true && controls == true && a.Data0140 != b.Data0140 && a.Component != b.Component && a.Corrected != b.Corrected && a.Store03b4 != b.Store03b4 : null;
                    var effect = !comparable ? "NotComparable" : controls == false ? "ControlMismatch" : read != true ? "CellNotRead" : a.Data0140 == b.Data0140 ? "ReadMaskedBefore0140" :
                        a.Component == b.Component ? (a.NativeFactor0158 == 0 ? "M2kZeroFactor" : "M2kTruncation") : a.Corrected == b.Corrected ? "ApplicationLowerClamp" : "NativeCorrectedStoresChanged";
                    comparisons.Add(new(sequences[p].ScratchPattern, i, read, controls, a.Data0140, b.Data0140, a.NativeFactor0158, b.NativeFactor0158, a.Component, b.Component, a.Corrected, b.Corrected, witness, effect));
                }
        }
        IReadOnlyList<int> changed = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, "fuel-factor-native-software-test", original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, changed, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }

    internal static IReadOnlyList<P28FuelFactorSequence> Analyze(RomImage image, P28FuelFactorScenario scenario, JsonElement root, string id)
    {
        P28LimiterScenario.Shape(root, "protocolVersion", "operation", "runnerVersion", "upstreamCommit", "localSemanticFixes", "entryContracts", "compactRows", "thresholdRows", "diagnostics", "syntheticResult", "fuelFactorSequences");
        _ = SliceRunnerIdentity.Validate(root, Operation); Require(Equal(root.GetProperty("entryContracts"), ExpectedContracts()), "M2m entry/ownership contract differs.");
        foreach (var key in new[] { "compactRows", "thresholdRows", "diagnostics" }) Require(root.GetProperty(key).GetArrayLength() == 0, "Foreign M2m rows.");
        Require(root.GetProperty("syntheticResult").ValueKind == JsonValueKind.Null, "Foreign synthetic result.");
        var seq = root.GetProperty("fuelFactorSequences"); Require(seq.GetArrayLength() == 3, "M2m scratch count differs.");
        var count = seq[0].GetProperty("checkpoints").EnumerateArray().Count(r => r.GetProperty("prefix").GetProperty("status").GetInt32() != 4);
        Require(count > 0, "Missing attempted native prefix.");
        var map = (scenario.InitialState.Fuel.Selector0127 & 2) == 0 ? "map_0" : "map_1";
        // Pure numeric/history adapter of the attempted native prefix; no old top-level run or second CPU.
        var prefixScenario = P28FuelMapScenario.FixedSelectorPrefix(scenario.InitialState.Fuel.Fuel,
            scenario.Calls.Take(count).Select(c => new P28FuelMapCall(c.Index, map, c.RawLoad, c.RawMap0Rpm, c.RawMap1Rpm)).ToArray());
        var view = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = P28FuelMapValidator.Operation,
            runnerVersion = root.GetProperty("runnerVersion").GetString(),
            upstreamCommit = root.GetProperty("upstreamCommit").GetString(),
            localSemanticFixes = root.GetProperty("localSemanticFixes"),
            entryContracts = P28FuelMapValidator.ExpectedContracts(),
            compactRows = Array.Empty<int>(),
            thresholdRows = Array.Empty<int>(),
            diagnostics = Array.Empty<int>(),
            syntheticResult = (object?)null,
            fuelMapSequences = seq.EnumerateArray().Select(s => new { scratchPattern = s.GetProperty("scratchPattern").GetInt32(), checkpoints = s.GetProperty("checkpoints").EnumerateArray().Take(count).Select(r => r.GetProperty("prefix")).ToArray() }).ToArray()
        });
        var prefixes = P28FuelMapValidator.AnalyzeImage(image, prefixScenario, new(view, ""), id);
        var result = new List<P28FuelFactorSequence>();
        for (var p = 0; p < 3; p++)
        {
            var s = seq[p]; P28LimiterScenario.Shape(s, "scratchPattern", "callerGate0124", "producerMode012c", "producerSelector012f", "checkpoints"); var pattern = new[] { 0, 85, 170 }[p];
            Require(s.GetProperty("scratchPattern").GetInt32() == pattern && s.GetProperty("callerGate0124").GetByte() == scenario.InitialState.CallerGate0124 &&
                s.GetProperty("producerMode012c").GetByte() == scenario.InitialState.ProducerMode012c && s.GetProperty("producerSelector012f").GetByte() == scenario.InitialState.ProducerSelector012f, "M2m once-only gates/scratch differs.");
            var rows = s.GetProperty("checkpoints"); Require(rows.GetArrayLength() == scenario.Calls.Count, "M2m event count differs.");
            var reports = new List<P28FuelFactorCheckpoint>(); var stopped = false; var mode = scenario.InitialState.Mode012b; var hysteresis = scenario.InitialState.Hysteresis0130;
            var sources = new P28FuelFactorSources(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0); var factor = pattern * 257;
            int[] stores = [pattern * 257, pattern * 257]; JsonElement previous = default;
            for (var i = 0; i < rows.GetArrayLength(); i++)
            {
                var row = rows[i]; P28LimiterScenario.Shape(row, "index", "status", "input", "prefix", "tailBoundaries", "handoff1350", "factorEntry", "factorStage", "factorExit", "transitionToFactorWrites", "transitionToAdditiveWrites",
                    "boundaries", "stages", "accesses", "inputWrites", "sourcesBefore", "sourcesAfter", "factor0158Before", "factor0158After", "nativeFactor0158", "factorProvenance", "modeBefore", "modeAfter", "hysteresisBefore", "hysteresisAfter",
                    "storesBefore", "storesAfter", "correction", "component", "corrected", "store03a2", "store03b4");
                var prefix = row.GetProperty("prefix"); var stages = row.GetProperty("stages"); var boundaries = row.GetProperty("boundaries"); var fs = row.GetProperty("factorStage");
                var status = row.GetProperty("status").GetInt32(); Require(status is >= 0 and <= 4 && row.GetProperty("index").GetInt32() == i, "M2m index/status differs.");
                Require(Equal(row.GetProperty("sourcesBefore"), JsonSerializer.SerializeToElement(sources, JsonDefaults.Create())) && row.GetProperty("modeBefore").GetByte() == mode &&
                    row.GetProperty("hysteresisBefore").GetByte() == hysteresis && row.GetProperty("factor0158Before").GetInt32() == factor &&
                    row.GetProperty("storesBefore").EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(stores), "M2m history was reseeded.");
                if (previous.ValueKind != JsonValueKind.Undefined) Require(Equal(prefix.GetProperty("stateBefore"), previous), "M2m retained fuel history reset.");
                var differences = new List<string>(); P28FuelFactorProjection? expected = null; int? origin = null; int? lookup = null; var disposition = "NotRun"; var provenance = "NotRun";
                var accesses = Matrix(row.GetProperty("accesses"), 5, 4096); Require(accesses.All(a => a[0] <= 65535 && a[1] < 4096 && a[2] is 8 or 16 && a[3] is 0 or 1 && a[4] < (a[2] == 8 ? 256 : 65536)), "Malformed native M2m access.");
                ValidateInputWrites(row.GetProperty("inputWrites"), scenario.Calls[i], !stopped);
                ValidateCombinedAccesses(prefix, fs, stages, accesses);
                if (stopped)
                {
                    Require(status == 4 && row.GetProperty("input").ValueKind == JsonValueKind.Null && prefix.GetProperty("status").GetInt32() == 4 && accesses.Length == 0 && Equal(prefix.GetProperty("stateBefore"), prefix.GetProperty("stateAfter")), "M2m terminal suffix executed.");
                    foreach (var key in new[] { "stateAfterInputs", "rpmAxes", "loadAxis", "selection", "lookup", "consumer", "selectedOrigin", "position", "lookupResult", "consumerOutput" }) Require(prefix.GetProperty(key).ValueKind == JsonValueKind.Null, "Terminal prefix executed.");
                    Require(row.GetProperty("tailBoundaries").GetArrayLength() == 0 && row.GetProperty("handoff1350").ValueKind == JsonValueKind.Null, "Terminal prefix seam executed.");
                }
                else
                {
                    Require(i < count && Equal(row.GetProperty("input"), JsonSerializer.SerializeToElement(scenario.Calls[i], JsonDefaults.Create())), "M2m input differs."); sources = scenario.Calls[i].Sources;
                    var ownPrefix = prefixes.Sequences[p].Checkpoints[i]; differences.AddRange(ownPrefix.Differences); disposition = ownPrefix.Disposition; origin = ownPrefix.ActualSelectedOrigin; lookup = ownPrefix.ActualConsumerOutput;
                    if (ownPrefix.Disposition == "StrictMatch")
                    {
                        Require(fs.ValueKind == JsonValueKind.Object, "Completed prefix has no attempted native factor producer."); ValidateSeams(row);
                        var ownLookup = (ushort)ownPrefix.Expected!.Consumer.Output; var entry = row.GetProperty("factorEntry"); var exit = row.GetProperty("factorExit");
                        Require(entry.GetProperty("accumulator").GetInt32() == ownLookup, "Native prefix A not its independently produced lookup.");
                        expected = P28FuelFactorModel.Project(sources, scenario.InitialState.ProducerMode012c, scenario.InitialState.ProducerSelector012f, hysteresis);
                        var oracle = P28FuelFactorEvidence.Build(sources, scenario.InitialState.ProducerMode012c, scenario.InitialState.ProducerSelector012f, hysteresis,
                            ownLookup, 0x0DC9, Word(entry, 0), Word(entry, 1), Word(entry, 2), Word(entry, 3));
                        var fr = ValidateFactorStage(fs, entry, exit, oracle, accesses);
                        foreach (var write in Matrix(fs.GetProperty("writes"), 3, 128))
                        {
                            if (write[0] == 0x158 && write[1] == 16) { factor = write[2]; provenance = "PartialWritten"; }
                            if (write[0] == 0x158 && write[1] == 8) { factor = (factor & 0xFF00) | write[2]; provenance = "PartialWritten"; }
                            if (write[0] == 0x130) hysteresis = (byte)write[2];
                        }
                        if (fr.Status == 0)
                        {
                            Require(oracle.Er1 == expected.NativeFactor0158 && oracle.Hysteresis == expected.HysteresisAfter && factor == expected.NativeFactor0158 && hysteresis == expected.HysteresisAfter && Nullable(row, "nativeFactor0158") == factor, "Independent native factor/hysteresis differs.");
                            provenance = "Written"; Require(stages.GetArrayLength() is >= 1 and <= 3 && boundaries.GetArrayLength() == stages.GetArrayLength() * 2, "Missing/unbounded additive stages.");
                            var additiveSources = P28FuelFactorModel.AdditiveSources(sources, (ushort)expected.NativeFactor0158);
                            var additive = P28FuelAdditiveModel.Project(ownLookup, additiveSources, mode, scenario.InitialState.CallerGate0124);
                            var b = boundaries[0]; var tailOracle = P28FuelAdditiveEvidence.Build(0, ownLookup, additiveSources, mode, scenario.InitialState.CallerGate0124,
                                oracle.Accumulator, 0x0DC9, oracle.Er0, oracle.Er1, oracle.Er2, oracle.Er3, stores[1]);
                            for (var n = 0; n < stages.GetArrayLength(); n++)
                            {
                                if (n > 0) tailOracle = P28FuelAdditiveEvidence.Build(n, ownLookup, additiveSources, mode, scenario.InitialState.CallerGate0124,
                                    tailOracle.Accumulator, tailOracle.Psw, tailOracle.Er0, tailOracle.Er1, tailOracle.Er2, tailOracle.Er3, stores[1]);
                                var sr = ValidateStage(stages[n], boundaries[n * 2], boundaries[n * 2 + 1], n, tailOracle, accesses);
                                Require(sr.Status != 0 || sr.Error is null, "Successful additive stage has an execution error.");
                                var accessCount = sr.Steps == 0 ? 0 : tailOracle.AccessEnds[sr.Steps - 1];
                                foreach (var write in tailOracle.Accesses.Take(accessCount).Where(a => a[3] == 1))
                                { if (write[1] == 0x12B) mode = (byte)write[4]; if (write[1] == 0x3A2) stores[0] = write[4]; if (write[1] == 0x3B4) stores[1] = write[4]; }
                                Require(sr.Status == 0 || n == stages.GetArrayLength() - 1, "Suffix executed after incomplete additive stage.");
                                if (sr.Status == 0)
                                {
                                    var end = boundaries[n * 2 + 1]; Require(end.GetProperty("accumulator").GetInt32() == tailOracle.Accumulator && end.GetProperty("psw").GetInt32() == tailOracle.Psw &&
                                        Word(end, 0) == tailOracle.Er0 && Word(end, 1) == tailOracle.Er1 && Word(end, 2) == tailOracle.Er2 && Word(end, 3) == tailOracle.Er3, "Additive native aliases/registers differ.");
                                    Require(end.GetProperty("x1").GetInt32() == b.GetProperty("x1").GetInt32() && end.GetProperty("x2").GetInt32() == additive.CorrectionWord && end.GetProperty("dp").GetInt32() == (n == 2 ? 0x3B4 : b.GetProperty("dp").GetInt32()), "Additive pointer/correction lifetime differs.");
                                    if (n == 0) Require(Nullable(row, "correction") == additive.CorrectionWord && tailOracle.Mode == additive.ModeAfter, "Native correction differs.");
                                    if (n == 1) P28FuelCalculationValidator.ValidateNumbers(stages[n], accesses, end, additive.Scaling, Nullable(row, "component"), tailOracle.Psw & 0x2000);
                                    if (n == 2) Require(Nullable(row, "corrected") == additive.Corrected && Nullable(row, "store03a2") == additive.Store03a2 && Nullable(row, "store03b4") == additive.Store03b4 && tailOracle.Er2 == additive.Scaling.Output, "Native application/stores differ.");
                                }
                            }
                            Require(status == stages[stages.GetArrayLength() - 1].GetProperty("result").GetProperty("status").GetInt32() && (status != 0 || stages.GetArrayLength() == 3), "M2m overall additive status differs.");
                        }
                        else Require(status == fr.Status, "M2m overall factor status differs.");
                        var factorReader = accesses.Any(a => a[0] == 0x21DD && a[3] == 0);
                        var lookupReader = accesses.Any(a => a[0] == 0x21DB && a[3] == 0);
                        Require(P28FuelCalculationValidator.HandoffMatches(accesses, ownLookup, lookupReader), "0140 native generation/word handoff differs.");
                        Require(fr.Status != 0 || FactorHandoffMatches(accesses, expected.NativeFactor0158, factorReader), "0158 native generation/word handoff differs.");
                    }
                    else Require(status == prefix.GetProperty("status").GetInt32() && fs.ValueKind == JsonValueKind.Null && row.GetProperty("handoff1350").ValueKind == JsonValueKind.Null && row.GetProperty("tailBoundaries").GetArrayLength() <= 5, "Factor executed after incomplete prefix.");
                }
                Require(Equal(row.GetProperty("sourcesAfter"), JsonSerializer.SerializeToElement(sources, JsonDefaults.Create())) && row.GetProperty("modeAfter").GetByte() == mode && row.GetProperty("hysteresisAfter").GetByte() == hysteresis &&
                    row.GetProperty("factor0158After").GetInt32() == factor && row.GetProperty("storesAfter").EnumerateArray().Select(n => n.GetInt32()).SequenceEqual(stores) && row.GetProperty("factorProvenance").GetString() == provenance, "M2m native-owned/source/history state differs.");
                if (fs.ValueKind == JsonValueKind.Null)
                    Require(row.GetProperty("factorEntry").ValueKind == JsonValueKind.Null && row.GetProperty("factorExit").ValueKind == JsonValueKind.Null && row.GetProperty("transitionToFactorWrites").GetArrayLength() == 0, "Nonexecuted factor seam was forged.");
                if (provenance != "Written")
                    Require(Nullable(row, "nativeFactor0158") is null && stages.GetArrayLength() == 0 && boundaries.GetArrayLength() == 0 && row.GetProperty("transitionToAdditiveWrites").GetArrayLength() == 0, "Consumer ran after incomplete/retained factor.");
                for (var n = 0; n < 3; n++) if (stages.GetArrayLength() <= n || stages[n].GetProperty("result").GetProperty("status").GetInt32() != 0)
                        foreach (var key in n == 0 ? new[] { "correction" } : n == 1 ? new[] { "component" } : new[] { "corrected", "store03a2", "store03b4" }) Require(Nullable(row, key) is null, "Stale/nonexecuted additive output.");
                Require(accesses.Where(a => a[3] == 1 && a[1] < 0x15A && a[1] + a[2] / 8 > 0x158).All(a => a[0] == 0x7A99 && a[1] == 0x158), "Foreign native write overlaps factor0158.");
                var final = differences.Count > 0 ? "Mismatch" : status switch { 0 => "StrictMatch", 1 => "Unresolved", 2 => "ExecutionError", 3 => "BudgetExceeded", _ => "NotRun" };
                reports.Add(new(i, final, disposition, origin, lookup, Nullable(row, "nativeFactor0158"), row.GetProperty("factor0158Before").GetInt32(), factor, provenance,
                    Nullable(row, "correction"), Nullable(row, "component"), Nullable(row, "corrected"), Nullable(row, "store03a2"), Nullable(row, "store03b4"), expected, differences.AsReadOnly(), ReportRow(row, scenario.TraceCallIndexes.Contains(i))));
                stopped |= status != 0; previous = prefix.GetProperty("stateAfter");
            }
            result.Add(new(id, pattern, reports.AsReadOnly()));
        }
        return result.AsReadOnly();
    }

    internal static void ValidateInputWrites(JsonElement writes, P28FuelFactorCall c, bool executed)
    {
        var s = c.Sources;
        int[][] expected = !executed ? [] : [ [0x238, 8, c.RawMap0Rpm], [0xC2, 8, c.RawMap1Rpm], [0xBF, 8, c.RawLoad],
            [0x15A, 16, s.Source015a], [0x15C, 16, s.Source015c], [0x160, 16, s.Source0160], [0x162, 16, s.Source0162],
            [0x15E, 8, s.Source015e], [0x164, 8, s.Source0164], [0x165, 8, s.Source0165], [0x166, 8, s.Source0166], [0x167, 8, s.Source0167], [0x168, 8, s.Source0168], [0x133, 8, s.Source0133],
            [0x142, 16, s.Source0142], [0x144, 16, s.Source0144], [0x146, 16, s.Source0146], [0x14A, 16, s.Source014a], [0x14C, 16, s.Source014c], [0x148, 8, s.Source0148], [0x149, 8, s.Source0149], [0xF2, 8, s.Counter00f2] ];
        Require(Matrix(writes, 3, 32).SelectMany(v => v).SequenceEqual(expected.SelectMany(v => v)), "Hidden source setter, factor byte overwrite or host carrier input.");
    }
    internal static bool FactorHandoffMatches(int[][] accesses, int factor, bool readerExecuted)
    {
        var writes = accesses.Select((a, i) => (a, i)).Where(x => x.a[3] == 1 && x.a[1] < 0x15A && x.a[1] + x.a[2] / 8 > 0x158).ToArray();
        var reads = accesses.Select((a, i) => (a, i)).Where(x => x.a[0] == 0x21DD && x.a[3] == 0).ToArray();
        return writes.Length == 1 && writes[0].a.SequenceEqual(new[] { 0x7A99, 0x158, 16, 1, factor }) && reads.Length == (readerExecuted ? 1 : 0) &&
            (!readerExecuted || reads[0].i > writes[0].i && reads[0].a.SequenceEqual(new[] { 0x21DD, 0x158, 16, 0, factor }));
    }
    internal static void ValidateCombinedAccesses(JsonElement prefix, JsonElement factorStage, JsonElement stages, int[][] accesses)
    {
        var executed = new List<JsonElement>();
        foreach (var key in new[] { "rpmAxes", "loadAxis", "selection", "lookup", "consumer" })
            if (prefix.GetProperty(key).ValueKind != JsonValueKind.Null) executed.Add(prefix.GetProperty(key));
        if (factorStage.ValueKind != JsonValueKind.Null) executed.Add(factorStage);
        executed.AddRange(stages.EnumerateArray());
        var events = executed.SelectMany(s => Matrix(s.GetProperty("events"), 8, 384)).ToArray();
        var rank = 0;
        foreach (var access in accesses)
        {
            while (rank < events.Length && events[rank][0] != access[0]) rank++;
            Require(rank < events.Length, "Foreign or reordered combined native access PC.");
        }
        var writes = executed.SelectMany(s => Matrix(s.GetProperty("writes"), 3, 384)).ToArray();
        Require(accesses.Where(a => a[3] == 1).SelectMany(a => new[] { a[1], a[2], a[4] }).SequenceEqual(writes.SelectMany(a => a)), "Combined native writes do not belong to the executed stages.");
    }
    internal static void ValidateSeams(JsonElement row)
    {
        var tails = row.GetProperty("tailBoundaries"); var h = row.GetProperty("handoff1350"); var entry = row.GetProperty("factorEntry"); var exit = row.GetProperty("factorExit"); var b = row.GetProperty("boundaries");
        Require(tails.GetArrayLength() == 5 && Equal(tails[0], tails[1]) && Equal(tails[2], tails[3]) && Equal(tails[4], h), "Native12FC..1350 tail reset.");
        var consumer = row.GetProperty("prefix").GetProperty("consumer"); var events = Matrix(consumer.GetProperty("events"), 8, 64);
        Require(events.Length > 0 && h.GetProperty("accumulator").GetInt32() == events[^1][3] && h.GetProperty("psw").GetInt32() == events[^1][5] &&
            h.GetProperty("ssp").GetInt32() == consumer.GetProperty("sspAfter").GetInt32() && h.GetProperty("lrb").GetInt32() == 0x20 && h.GetProperty("usp").GetInt32() == 0x280, "Prefix handoff contradicts its native final event/bank/stack.");
        Require(h.GetProperty("pc").GetInt32() == 0x1350 && entry.GetProperty("pc").GetInt32() == 0x1F43, "Factor scripted entry differs.");
        ValidateScripted(h, entry); Require(Equal(row.GetProperty("transitionToFactorWrites"), ExpectedContracts()[0].GetProperty("hostTransitionWrites")), "Hidden factor ABI writes.");
        if (b.GetArrayLength() > 0)
        {
            Require(exit.GetProperty("pc").GetInt32() == 0x1FB7 && b[0].GetProperty("pc").GetInt32() == 0x2194, "Additive scripted entry differs.");
            ValidateScripted(exit, b[0]); Require(Equal(row.GetProperty("transitionToAdditiveWrites"), ExpectedContracts()[0].GetProperty("hostTransitionWrites")), "Hidden additive ABI writes.");
            for (var n = 2; n < b.GetArrayLength(); n += 2) Require(Equal(b[n - 1], b[n]), "Producer/scaling/application seam reset.");
        }
        foreach (var boundary in tails.EnumerateArray().Concat(new[] { entry, exit }).Concat(b.EnumerateArray())) ValidateBoundary(boundary);
    }
    private static void ValidateScripted(JsonElement before, JsonElement after)
    {
        Require(after.GetProperty("psw").GetInt32() == 0x0DC9 && after.GetProperty("lrb").GetInt32() == 0x20 && after.GetProperty("usp").GetInt32() == 0x280 && after.GetProperty("ssp").GetInt32() == 0x7FE, "Scripted ABI/bank differs.");
        foreach (var key in new[] { "accumulator", "x1", "x2", "dp", "ssp", "registers" }) Require(Equal(before.GetProperty(key), after.GetProperty(key)), "Host injected/reset native carriers.");
    }
    private static void ValidateBoundary(JsonElement b)
    {
        P28LimiterScenario.Shape(b, "pc", "accumulator", "psw", "dd", "lrb", "x1", "x2", "dp", "usp", "ssp", "registers");
        foreach (var key in new[] { "pc", "accumulator", "psw", "lrb", "x1", "x2", "dp", "usp", "ssp" }) Require(b.GetProperty(key).GetInt32() is >= 0 and <= 65535, "Boundary word outside architectural domain.");
        Require(b.GetProperty("dd").GetBoolean() == ((b.GetProperty("psw").GetInt32() & 0x1000) != 0), "Boundary DD contradicts PSW."); _ = Word(b, 3);
    }
    internal static P28AcquisitionStageResult ValidateFactorStage(JsonElement stage, JsonElement entry, JsonElement exit, P28FuelFactorOracle own, int[][] accesses)
    {
        P28LimiterScenario.Shape(stage, "result", "writes", "events", "sspAfter"); ValidateBoundary(entry); ValidateBoundary(exit);
        var r = P28AcquisitionValidator.ParseStage(stage.GetProperty("result"), 128, 0, [], null)!; var events = Matrix(stage.GetProperty("events"), 8, 128); var writes = Matrix(stage.GetProperty("writes"), 3, 128);
        Require(r.Status != 0 || r.Error is null, "Successful factor stage has an execution error.");
        P28FuelFactorEvidence.RequireEventPrefix(stage, own); Require(events.Length == r.Steps && r.Trace.Count == r.Steps && (r.Status != 0 || events.Length == own.Events.Count), "Missing factor native events.");
        P28FuelCalculationValidator.ValidateEventContinuity(events, entry.GetProperty("accumulator").GetInt32(), entry.GetProperty("psw").GetInt32(), exit.GetProperty("accumulator").GetInt32(), exit.GetProperty("psw").GetInt32());
        for (var i = 0; i < events.Length; i++) Require(r.Trace[i].GetProperty("pc").GetInt32() == events[i][0] && r.Trace[i].GetProperty("nextPc").GetInt32() == events[i][1] && r.Trace[i].GetProperty("accumulator").GetInt32() == events[i][3] && r.Trace[i].GetProperty("psw").GetInt32() == events[i][5], "Factor trace contradicts journal.");
        var extents = own.Events.Take(events.Length).SelectMany((e, i) => Enumerable.Range(e[0], own.Lengths[i])).Distinct().Order().ToArray();
        Require(r.ExecutedInstructionBytes.SequenceEqual(extents) && r.StopPc == (events.Length == 0 ? 0x1F43 : events[^1][1]) && exit.GetProperty("pc").GetInt32() == r.StopPc && (r.Status != 0 || r.StopPc == 0x1FB7), "Factor path extent/exit differs.");
        var accessCount = events.Length == 0 ? 0 : own.AccessEnds[events.Length - 1]; var writeCount = events.Length == 0 ? 0 : own.WriteEnds[events.Length - 1];
        var pcs = events.Select(e => e[0]).ToHashSet(); var native = accesses.Where(a => pcs.Contains(a[0])).ToArray();
        // A bounded bus can retain the low byte of a faulting word store. It is not a fresh word or a successful producer.
        var partial = r.Status == 2 && events.Length > 0 && events[^1][0] == 0x7A99 && native.Length == accessCount && native[^1].SequenceEqual(new[] { 0x7A99, 0x158, 8, 1, own.Er1 & 255 });
        var expectedAccesses = own.Accesses.Take(accessCount).Select(a => a.ToArray()).ToArray(); var expectedWrites = own.Writes.Take(writeCount).Select(w => w.ToArray()).ToArray();
        if (partial) { expectedAccesses[^1] = [0x7A99, 0x158, 8, 1, own.Er1 & 255]; expectedWrites[^1] = [0x158, 8, own.Er1 & 255]; }
        Require(native.SelectMany(v => v).SequenceEqual(expectedAccesses.SelectMany(v => v)) && writes.SelectMany(v => v).SequenceEqual(expectedWrites.SelectMany(v => v)), "Factor full ordered native source/register/store journal differs.");
        var endRegisters = events.Length == 0 ? Enumerable.Range(0, 4).Select(i => Word(entry, i)).ToArray() : own.RegisterEnds[events.Length - 1];
        Require(Enumerable.Range(0, 4).All(i => Word(exit, i) == endRegisters[i]) && r.UsedAssumptions.Count == 0 && r.ProgramReads.Count == 0, "Factor aliases/assumptions/program reads differ.");
        foreach (var key in new[] { "x1", "x2", "dp" }) Require(Equal(entry.GetProperty(key), exit.GetProperty(key)), "Factor changed an untouched pointer.");
        Require(entry.GetProperty("lrb").GetInt32() == 0x20 && entry.GetProperty("psw").GetInt32() == 0x0DC9 && entry.GetProperty("pc").GetInt32() == 0x1F43 &&
            exit.GetProperty("lrb").GetInt32() == 0x20 && exit.GetProperty("usp").GetInt32() == 0x280 && entry.GetProperty("usp").GetInt32() == 0x280 &&
            entry.GetProperty("ssp").GetInt32() == 0x7FE && exit.GetProperty("ssp").GetInt32() == 0x7FE && stage.GetProperty("sspAfter").GetInt32() == 0x7FE, "Factor bank/DD/stack differs.");
        return r;
    }
    private static int? Nullable(JsonElement r, string key) => r.GetProperty(key).ValueKind == JsonValueKind.Null ? null : r.GetProperty(key).GetInt32();
    private static JsonElement ReportRow(JsonElement row, bool trace)
    {
        if (trace) return row.Clone(); var node = JsonNode.Parse(row.GetRawText())!;
        foreach (var name in new[] { "rpmAxes", "loadAxis", "selection", "lookup", "consumer" }) if (node["prefix"]?[name]?["result"] is JsonObject p) p["trace"] = new JsonArray();
        if (node["factorStage"]?["result"] is JsonObject f) f["trace"] = new JsonArray(); foreach (var stage in node["stages"]!.AsArray()) stage!["result"]!["trace"] = new JsonArray();
        return JsonSerializer.SerializeToElement(node);
    }
}
