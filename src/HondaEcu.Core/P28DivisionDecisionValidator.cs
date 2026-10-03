using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.P28FuelAdditiveValidator;
using static HondaEcu.Core.P28LimiterValidator;

namespace HondaEcu.Core;

public sealed record P28DivisionProof(int Current03b4, int HelperResult, int DividendHigh, int DividendLow, int Divisor,
    int QuotientHigh, int QuotientLow, int Remainder, bool DivCf, bool DivZf, bool CmpCf, bool CmpZf,
    bool? JgtDecision, int? FreshCalculationResult);
public sealed record P28DivisionDecisionCheckpoint(int Index, string Disposition, P28DivisionProof? Division,
    P28CommonResultConsumerCheckpoint Native);
public sealed record P28DivisionDecisionSequence(string Image, int ScratchPattern, IReadOnlyList<P28DivisionDecisionCheckpoint> Checkpoints);
public sealed record P28DivisionDecisionComparison(int ScratchPattern, int Index, bool? Controls, int? QuotientA, int? QuotientB,
    string Effect, P28CommonResultConsumerComparison Upstream);
public sealed record P28DivisionDecisionReport(int FormatVersion, string Purpose, RomHash OriginalHash, string ProfileId,
    string ScenarioDigest, string RunnerVersion, P28PostStoreMutation? Mutation, IReadOnlyList<int> ChangedOffsets,
    IReadOnlyList<P28DivisionDecisionSequence> Sequences, IReadOnlyList<P28DivisionDecisionComparison> Comparisons, JsonElement EntryContract)
{
    // This stage cannot succeed until applicable primary JGT evidence is resolved.
    public bool HasFailure => true;
    public string OverallStage => "Blocked/Partial;PrimaryJgtConditionConflict";
    public string HistoricalM2s => "Partial;unchanged";
    public string JgtPredicate => "Unresolved;NoAssumption";
    public string Scope => "Same CPU/RAM M2r->22B1->native helper/DIV/CMP;stop-before233A. DIV0 stop-before2333;no fresh calculation output.";
    public string Readiness => "PcInspectionOnly / NotFlashReady";
    public bool PhysicalRpmAvailable => false;
    public string Units => "raw;physical fuel/time/degrees unavailable";
    public string QuartetConsumer => "NotRun;no scheduler seam";
    public string StrictM2i => "Blocked;unchanged";
    public string GuiR3 => "paused/NotRun";
    public string D1D2InteractiveAcceptance => "NotRun";
    public string HardwareAndFullBoot => "NotRun";
    public string FirmwareOutput => "None;BIN0;bindings0;compensation0;export plans/receipts/tokens0";
    public object Summary => new
    {
        StrictPositiveEvents = 0,
        PositiveDivPrefixes = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Division is not null),
        Dispositions = Sequences.SelectMany(s => s.Checkpoints).GroupBy(c => c.Disposition).ToDictionary(g => g.Key, g => g.Count()),
        CompletedM2rPrefixes = Sequences.SelectMany(s => s.Checkpoints).Count(c => c.Native.PrefixDisposition == "StrictMatch"),
        AbComparisons = Comparisons.Count,
        QuotientWitnesses = Comparisons.Count(c => c.Effect == "QuotientDivergence;JgtNotRun"),
        JgtWitnesses = 0,
        CalculationOutputWitnesses = 0,
        ModelOnlyEvents = 0
    };
}

public static class P28DivisionDecisionValidator
{
    public const string Operation = "fuelDivisionDecisionChain";
    internal static JsonElement ExpectedContracts()
    {
        var c = JsonNode.Parse(P28CommonResultConsumerValidator.ExpectedContracts().GetRawText())!;
        c[0]!["id"] = Operation; c[0]!["isaClosure"] = "Blocked;PrimaryJgtConditionConflict;StopBefore233A";
        c[0]!["jgtPredicate"] = null;
        c[0]!["positiveDivisorPolicy"] = "NativeDIVAndCMPOnly;NoJgtDecisionOrFreshCalculationOutput";
        return JsonSerializer.SerializeToElement(c);
    }
    public static object CreateRequest(RomImage image, P28DivisionDecisionScenario scenario)
    {
        var n = JsonNode.Parse(JsonSerializer.Serialize(P28CommonResultConsumerValidator.CreateRequest(image, scenario.Sources), JsonDefaults.Create()))!;
        n["operation"] = Operation; n[Operation] = n["fuelCommonResultConsumerChain"]!.DeepClone(); n.AsObject().Remove("fuelCommonResultConsumerChain"); return n;
    }
    internal static IReadOnlyList<P28DivisionDecisionSequence> Analyze(RomImage image, P28DivisionDecisionScenario scenario, JsonElement root, string id)
    {
        // Validates M2t identity and contracts before reusing independent M2s machine/history validation.
        // Observations never become model inputs; no response relabel or JSON->RAM execution seam.
        var native = P28CommonResultConsumerValidator.AnalyzeNative(image, scenario.Sources, root, id, Operation, "divisionDecisionSequences", ExpectedContracts());
        return native.Select(s => new P28DivisionDecisionSequence(s.Image, s.ScratchPattern,
            s.Checkpoints.Select(c => Convert(c, root.GetProperty("divisionDecisionSequences")[Array.IndexOf(new[] { 0, 85, 170 }, s.ScratchPattern)].GetProperty("checkpoints")[c.Index])).ToArray())).ToArray();
    }
    internal static P28DivisionDecisionCheckpoint Convert(P28CommonResultConsumerCheckpoint c, JsonElement raw)
    {
        var suffix = raw.GetProperty("commonConsumer");
        var stop = suffix.ValueKind == JsonValueKind.Object ? suffix.GetProperty("stage").GetProperty("result").GetProperty("stopPc").GetInt32() : -1;
        var disposition = c.Disposition switch
        {
            "NotRun" => "NotRun",
            "ExecutionError" => "ExecutionError",
            "BudgetExceeded" => "BudgetExceeded",
            "StrictMatch" => "SoftwareBypassNotCalculation",
            _ when stop == 0x2333 => "ZeroDivisorUnresolved",
            _ when stop == 0x233A => "JgtEvidenceBlocked",
            _ => "PrefixUnresolved"
        };
        var proof = suffix.ValueKind == JsonValueKind.Object ? Proof(suffix) : null;
        Require(disposition != "JgtEvidenceBlocked" || proof is not null, "JGT stop lacks native positive DIV/CMP provenance.");
        return new(c.Index, disposition, proof, c);
    }
    internal static P28DivisionProof? Proof(JsonElement suffix)
    {
        var stage = suffix.GetProperty("stage"); var events = Matrix(stage.GetProperty("events"), 8, 192);
        if (!events.Any(e => e[0] == 0x2333)) return null;
        var accesses = Matrix(suffix.GetProperty("accesses"), 5, 768);
        foreach (var (pc, name) in new[] { (0x232E, "CLR er0"), (0x2330, "MOV er2, off N8"), (0x2333, "DIV"), (0x2335, "JLT rel8"), (0x2337, "CMP A, #N16") })
        {
            var index = Array.FindIndex(events, e => e[0] == pc);
            if (index >= 0) Require(stage.GetProperty("result").GetProperty("trace")[index].GetProperty("instruction").GetString() == name, "Wrong exact DIV prefix instruction form.");
        }
        var div = events.Single(e => e[0] == 0x2333); var cmp = events.SingleOrDefault(e => e[0] == 0x2337);
        // Incomplete execution may have reached DIV but not CMP; it is not a JGT proof.
        if (cmp is null) return null;
        int Access(int pc, int address, int direction) => accesses.Single(a => a[0] == pc && a[1] == address && a[2] == 16 && a[3] == direction)[4];
        Require(Access(0x232E, 0x100, 1) == 0, "er0 must be native-cleared, not an initial precondition.");
        var divisor = Access(0x2330, 0x136, 0);
        Require(divisor > 0 && Access(0x2330, 0x104, 1) == divisor && Access(0x2333, 0x104, 0) == divisor, "Native divisor ownership differs.");
        Require(div[1] == 0x2335 && cmp[1] == 0x233A && cmp[6] == div[3] && cmp[7] == 11, "DIV/CMP operand/PC continuity differs.");
        Require(!events.Any(e => e[0] == 0x233A || e[0] == 0x236A), "Primary-unresolved JGT or fabricated result executed.");
        return new(Access(0x232A, 0x3B4, 0), events.Single(e => e[0] == 0x59A5)[3], Access(0x2333, 0x100, 0), div[2], divisor,
            Access(0x2333, 0x100, 1), div[3], Access(0x2333, 0x102, 1), (div[5] & 0x8000) != 0, (div[5] & 0x4000) != 0,
            (cmp[5] & 0x8000) != 0, (cmp[5] & 0x4000) != 0, null, null);
    }
    public static async Task<P28DivisionDecisionReport> ExecuteAsync(RomImage original, RomProfile profile, P28ExactBaselineBinding binding,
        bool confirmed, string runner, P28DivisionDecisionScenario scenario, SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        P28ByteExecutionValidator.ValidateAdmission(original, profile, binding, confirmed, null);
        P28LimiterInspector.OperandGuard(original); P28FuelMapInspector.LayoutGuard(original);
        Require(original.Span[0x60E5] == 0 && original.Span[0x60F8] == 0, "Unchanged original configuration required.");
        var child = scenario.Mutation is null ? null : P28PostStoreValidator.Mutate(original, scenario.Mutation);
        var images = child is null ? new[] { original } : new[] { original, child };
        var sequences = new List<P28DivisionDecisionSequence>(); JsonElement contract = default; var version = "";
        foreach (var image in images)
        {
            var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(image, scenario), options, cancellationToken).ConfigureAwait(false);
            try
            {
                sequences.AddRange(Analyze(image, scenario, response.Response, ReferenceEquals(image, original) ? "A" : "B"));
                contract = response.Response.GetProperty("entryContracts").Clone(); version = response.Response.GetProperty("runnerVersion").GetString()!;
            }
            catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException or ArgumentException)
            { throw new SliceProcessException(SliceProcessFailure.Protocol, "Malformed M2t native evidence.", e); }
        }
        var comparisons = new List<P28DivisionDecisionComparison>();
        if (child is not null) for (var p = 0; p < 3; p++) for (var i = 0; i < scenario.Calls.Count; i++)
                {
                    var a = sequences[p].Checkpoints[i]; var b = sequences[p + 3].Checkpoints[i];
                    var ok = a.Native.PrefixDisposition == "StrictMatch" && b.Native.PrefixDisposition == "StrictMatch";
                    var adaptive = scenario.Mutation!.Kind != P28PostStoreMutationKind.FuelCell;
                    var af = a.Native.Prefix.Prefix.Prefix.Prefix.Continuation?.Fuel; var bf = b.Native.Prefix.Prefix.Prefix.Prefix.Continuation?.Fuel;
                    bool? controls = !ok ? null : !adaptive || af!.Data0140 == bf!.Data0140 && af.NativeFactor0158 == bf.NativeFactor0158 &&
                        af.Component == bf.Component && af.Correction == bf.Correction && af.Corrected == bf.Corrected && af.Store03b4 == bf.Store03b4 &&
                        a.Native.Prefix.Expected == b.Native.Prefix.Expected && P28LimiterFuelValidator.NumericControlHistory(af.Actual, bf.Actual);
                    var effect = a.Division is null || b.Division is null ? "CalculationNotRun" :
                        a.Division.QuotientLow != b.Division.QuotientLow ? "QuotientDivergence;JgtNotRun" :
                        a.Division.DividendLow != b.Division.DividendLow ? "DivisionTruncation" : "CalculationSame;JgtNotRun";
                    var upstream = new P28CommonResultConsumerComparison(sequences[p].ScratchPattern, i, controls,
                        !ok ? null : a.Native.Prefix.CommonPathWord != b.Native.Prefix.CommonPathWord, a.Native.Prefix.CommonPathWord, b.Native.Prefix.CommonPathWord,
                        a.Native.SoftwareResult13b, b.Native.SoftwareResult13b, "M2t prefix control;JgtNotRun");
                    comparisons.Add(new(sequences[p].ScratchPattern, i, controls, a.Division?.QuotientLow, b.Division?.QuotientLow, effect, upstream));
                }
        IReadOnlyList<int> diff = child is null ? [] : Array.AsReadOnly(Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray());
        return new(1, scenario.Purpose, original.Hash, profile.Id, scenario.Digest, version, scenario.Mutation, diff, sequences.AsReadOnly(), comparisons.AsReadOnly(), contract);
    }
}
