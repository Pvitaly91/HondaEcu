using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed record P28ProducerStageCounts(
    int Total, int MatchesWithoutAssumptions, int ConditionalMatches, int StoppedUnresolved,
    int Mismatches, int ExecutionErrors, int BudgetExceeded, int NotRun, int UnresolvedModel)
{
    public bool HasFailure => Mismatches + ExecutionErrors + BudgetExceeded + UnresolvedModel != 0;
}

public sealed record P28ProducerComparisonIssue(int CaseId, string Stage, string Category, int[] ObservedRow);
public sealed record P28ProducerThresholdSummary(string ImageId, P28ProducerStageCounts Counts,
    int ProgramReadChecks, int DisabledPreservationChecks);
public sealed record P28ProducerDerivedSummary(
    bool VerifiedM1cLineage, int EligiblePairedCases, int ExpectedChangedPredicateCases,
    int ActualChangedPredicateCases, bool ExactChangedCaseSet, int PlannedSlotReadCases,
    int PlannedSlotSelectedCases, string ReadSelectionQualification)
{
    public bool VerifiedCompositionLineage { get; init; }
}
public sealed record P28ProducerExample(
    P28ProducerInput Input, P28ProducerModelResult Model, int[] ProducerAndCompactExecution,
    IReadOnlyList<int[]> ThresholdExecution);

public sealed record P28ProducerExecutionReport(
    int ProtocolVersion, string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string ExecutionKind, string ModelId, string SampleRepresentation, string InputPhysicalReachability, string CaseSetVersion, uint RandomSeed,
    string ProfileId, RomHash BaselineHash, RomHash? DerivedHash, string ProfileDigest,
    string BindingDigest, string? PlanDigest, IReadOnlyList<JsonElement> EntryContracts,
    string Mode, IReadOnlyList<string> PermittedAssumptions, IReadOnlyList<string> UsedAssumptions,
    IReadOnlyDictionary<string, int> AssumptionUseCaseCounts,
    IReadOnlyDictionary<string, int> CaseGroups, P28ProducerStageCounts Producer,
    P28ProducerStageCounts ProducerToCompact, IReadOnlyList<P28ProducerThresholdSummary> Threshold,
    P28ProducerDerivedSummary? DerivedComparison, IReadOnlyDictionary<string, int> ProducerDispositions,
    IReadOnlyList<P28ProducerExample> SelectedExamples, IReadOnlyList<P28ProducerComparisonIssue> Issues,
    IReadOnlyList<JsonElement> Diagnostics, JsonElement? Scaling,
    bool HasFailure, bool PhysicalRpmAvailable, bool HardwareExecutionPerformed, bool FullEcuBootPerformed,
    string Checksum, FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety,
    IReadOnlyList<string> Limitations);

/// <summary>One finite batch compares independent integer G with measured G, then measured same-RAM G→F.</summary>
public static class P28ProducerValidator
{
    public static IReadOnlyList<string> ValidateAssumptions(IEnumerable<string> assumptions)
    {
        var values = assumptions.ToArray();
        if (values.Distinct(StringComparer.Ordinal).Count() != values.Length ||
            values.Any(value => value is not (P28ProducerModel.AddEr1Assumption or P28ByteExecutionValidator.AddAssumption)))
        {
            throw new ArgumentException("Producer execution accepts each of oki.add-er1-a and oki.add-er3-a at most once; neither permits other instruction forms.", nameof(assumptions));
        }
        return values.Order(StringComparer.Ordinal).ToArray();
    }

    public static object CreateRequest(RomImage baseline, RomImage? derived,
        IReadOnlyList<P28ProducerInput> cases, IEnumerable<string> assumptions)
    {
        ValidateCases(cases);
        var allowed = ValidateAssumptions(assumptions);
        var images = new List<object> { new { id = "baseline", rom = baseline.ToArray().Select(value => (int)value).ToArray() } };
        if (derived is not null)
        {
            images.Add(new { id = "derived", rom = derived.ToArray().Select(value => (int)value).ToArray() });
        }
        return new
        {
            protocolVersion = 1,
            operation = "producerBatch",
            images,
            allowAssumptions = allowed,
            scratchPatterns = new[] { 0, 85, 170 },
            producerCases = cases.Select(P28ProducerCases.Pack).ToArray(),
        };
    }

    public static async Task<P28ProducerExecutionReport> ExecuteAsync(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, IEnumerable<string> assumptions, RomImage? derived = null,
        P28RawThresholdPlan? plan = null, P28RawThresholdPatchReport? patchReport = null,
        JsonElement? scaling = null, SliceProcessOptions? options = null, CancellationToken cancellationToken = default,
        P28VerifiedChecksumComposition? composition = null)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, confirmed, derived, plan, patchReport, composition);
        var allowed = ValidateAssumptions(assumptions);
        var cases = P28ProducerCases.Create();
        var response = await SeededSliceProcess.ExchangeAsync(runner, CreateRequest(baseline, derived, cases, allowed), options, cancellationToken)
            .ConfigureAwait(false);
        var report = Analyze(baseline, profile, binding, cases, allowed, response, derived, plan, patchReport, scaling, composition);
        var replayIds = report.Issues.Select(issue => issue.CaseId).Distinct().Take(4).ToArray();
        if (replayIds.Length == 0) { return report; }
        var diagnostics = report.Diagnostics.ToList();
        try
        {
            var replayCases = replayIds.Select((id, index) => cases[id] with { CaseId = index }).ToArray();
            var replayResponse = await SeededSliceProcess.ExchangeAsync(runner,
                CreateRequest(baseline, derived, replayCases, allowed), options, cancellationToken).ConfigureAwait(false);
            var replay = Analyze(baseline, profile, binding, replayCases, allowed, replayResponse, derived, plan, patchReport, scaling, composition);
            var consistent = replayIds.Select((id, index) =>
            {
                var original = report.SelectedExamples.First(example => example.Input.CaseId == id);
                var rerun = replay.SelectedExamples.First(example => example.Input.CaseId == index);
                return original.ProducerAndCompactExecution.Skip(1).SequenceEqual(rerun.ProducerAndCompactExecution.Skip(1)) &&
                    original.ThresholdExecution.Zip(rerun.ThresholdExecution).All(pair => pair.First.Skip(1).SequenceEqual(pair.Second.Skip(1)));
            }).All(value => value);
            diagnostics.Add(JsonSerializer.SerializeToElement(new
            {
                purpose = "Bounded replay of measured failures; excluded from independent case counts",
                originalCaseIds = replayIds,
                replayConsistency = consistent,
                replayDiagnostics = replay.Diagnostics,
            }, JsonDefaults.Create(false)));
        }
        catch (Exception exception) when (exception is SliceProcessException or JsonException or InvalidOperationException or KeyNotFoundException)
        {
            diagnostics.Add(JsonSerializer.SerializeToElement(new
            {
                purpose = "Failure replay did not complete; primary measured failure report retained",
                originalCaseIds = replayIds,
                replayConsistency = false,
                traceObtained = false,
                failure = exception is SliceProcessException process ? process.Failure.ToString() : "Protocol",
            }, JsonDefaults.Create(false)));
        }
        return report with { Diagnostics = diagnostics };
    }

    public static P28ProducerExecutionReport Analyze(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        IReadOnlyList<P28ProducerInput> cases, IEnumerable<string> assumptions, SliceProcessResponse response,
        RomImage? derived = null, P28RawThresholdPlan? plan = null, P28RawThresholdPatchReport? patchReport = null,
        JsonElement? scaling = null, P28VerifiedChecksumComposition? composition = null)
    {
        ValidateCases(cases);
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, derived, plan, patchReport, composition);
        try
        {
            var result = AnalyzeCore(baseline, profile, binding, cases, ValidateAssumptions(assumptions), response, derived, composition?.Plan.ThresholdPlan ?? plan, scaling);
            return composition is null ? result : result with
            {
                PlanDigest = P28ChecksumPreservingEditor.ComputePlanDigest(composition.Plan),
                DerivedComparison = result.DerivedComparison! with { VerifiedM1cLineage = false, VerifiedCompositionLineage = true },
            };
        }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException)
        {
            throw Protocol("Malformed producer response.", exception);
        }
    }

    private static P28ProducerExecutionReport AnalyzeCore(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding,
        IReadOnlyList<P28ProducerInput> cases, IReadOnlyList<string> allowed, SliceProcessResponse response,
        RomImage? derived, P28RawThresholdPlan? plan, JsonElement? scaling)
    {
        var root = response.Response;
        var fixes = SliceRunnerIdentity.Validate(root, "producerBatch");
        var runnerVersion = root.GetProperty("runnerVersion").GetString()!;
        var contracts = root.GetProperty("entryContracts").EnumerateArray().Select(item => item.Clone()).ToArray();
        if (contracts.Length != 3)
        {
            throw Protocol("Producer entry and staged composition contracts are required.");
        }
        ValidateContracts(contracts);
        var diagnostics = root.GetProperty("diagnostics").EnumerateArray().Select(item => item.Clone()).ToArray();
        if (diagnostics.Length > 128)
        {
            throw Protocol("Producer diagnostic count exceeds its bound.");
        }
        foreach (var diagnostic in diagnostics)
        {
            if (diagnostic.GetProperty("result").GetProperty("trace").GetArrayLength() > 128)
            {
                throw Protocol("Producer diagnostic trace exceeds its instruction bound.");
            }
        }
        var allowG = allowed.Contains(P28ProducerModel.AddEr1Assumption);
        var allowF = allowed.Contains(P28ByteExecutionValidator.AddAssumption);
        var permittedMask = (allowG ? 1 : 0) | (allowF ? 2 : 0);
        var gCounts = new Counter();
        var fCounts = new Counter();
        var issues = new List<P28ProducerComparisonIssue>();
        var seen = new bool[cases.Count];
        var measured = new int[cases.Count][];
        var model = new P28ProducerModelResult[cases.Count];
        var dispositions = new Dictionary<string, int>(StringComparer.Ordinal);
        var usedMask = 0;
        var producerAssumptionCases = 0;
        var compactAssumptionCases = 0;
        foreach (var element in root.GetProperty("producerRows").EnumerateArray())
        {
            var row = Row(element, 22);
            Range(row[0], 0, cases.Count - 1);
            Unique(seen, row[0]);
            var input = cases[row[0]];
            if (input.CaseId != row[0] || input.ScratchPattern != row[1])
            {
                throw Protocol("Producer case identity or scratch pattern differs from the request.");
            }
            Range(row[2], 0, 3);
            Range(row[3], 0, 65535);
            Range(row[4], 0, 192);
            Range(row[5], 0, 65535);
            Range(row[6], 0, 255);
            Range(row[7], 0, 255);
            foreach (var value in row[8..14]) { Range(value, 0, 65535); }
            Range(row[14], 0, 1);
            Range(row[15], 0, 4);
            Range(row[17], 0, 128);
            Range(row[20], 0, 3);
            Range(row[21], 0, 65535);
            if ((row[14] & ~permittedMask) != 0 || (row[20] & ~permittedMask) != 0 || (row[20] & row[14]) != row[14])
            {
                throw Protocol("Producer/composition assumptions were unpermitted or lost during state transfer.");
            }
            var expected = P28ProducerModel.Evaluate(input, allowG);
            model[row[0]] = expected;
            measured[row[0]] = row;
            usedMask |= row[14] | row[20];
            producerAssumptionCases += (row[14] & 1) != 0 ? 1 : 0;
            compactAssumptionCases += (row[20] & 2) != 0 ? 1 : 0;
            var gCategory = StatusCategory(row[2]);
            if (row[2] == 0)
            {
                if (!expected.Resolved)
                {
                    gCategory = Category.UnresolvedModel;
                }
                else
                {
                    var match = row[3] == 0x07A5 && row[5] == expected.T && row[6] == expected.Flags0217 &&
                        row[7] == expected.Flags0231 && row[8..14].SequenceEqual(expected.Samples.Select(value => (int)value)) &&
                        row[21] == input.PreviousT && row[14] == (expected.UsedAssumptions.Count == 0 ? 0 : 1);
                    gCategory = match ? row[14] == 0 ? Category.Match : Category.ConditionalMatch : Category.Mismatch;
                    var disposition = match ? expected.Disposition.ToString() : "MismatchNotClassified";
                    dispositions[disposition] = dispositions.GetValueOrDefault(disposition) + 1;
                }
            }
            else if (row[2] == 1 && row[3] == 0x077E && (!expected.Resolved || !allowG))
            {
                // These are before-ADD observations, not a passed producer result.
                if (row[5] != input.PreviousT || row[6] != input.PreviousFlags0217 || row[7] != input.PreviousFlags0231 ||
                    !row[8..14].SequenceEqual(expected.Samples.Select(value => (int)value)))
                {
                    gCategory = Category.Mismatch;
                }
            }
            gCounts.Add(gCategory);
            AddIssue(issues, input.CaseId, "producer", gCategory, row);
            Category fCategory;
            if (row[2] != 0)
            {
                if (row[15] != 4)
                {
                    throw Protocol("Compact stage ran despite an incomplete producer.");
                }
                fCategory = Category.NotRun;
            }
            else
            {
                if (row[15] == 4)
                {
                    throw Protocol("Compact stage was omitted after a completed producer.");
                }
                var compact = P28ByteExecutionValidator.ClassifyCompact((ushort)row[5], (row[6] & 0x10) != 0,
                    row[15], row[18], row[19], (row[20] & 2) != 0, allowF);
                fCategory = Convert(compact);
                if (fCategory == Category.Match && row[20] != 0)
                {
                    fCategory = Category.ConditionalMatch;
                }
                if (row[15] == 0 && row[16] != 0x0822)
                {
                    fCategory = Category.Mismatch;
                }
                if (gCategory is Category.Mismatch or Category.UnresolvedModel && row[15] == 0)
                {
                    fCategory = Category.Mismatch;
                }
            }
            fCounts.Add(fCategory);
            AddIssue(issues, input.CaseId, "producer-to-compact", fCategory, row);
        }
        Complete(seen);

        var images = derived is null ? new[] { baseline } : new[] { baseline, derived };
        var thresholdCounts = images.Select(_ => new Counter()).ToArray();
        var readChecks = new int[images.Length];
        var disabledChecks = new int[images.Length];
        var seenThreshold = new bool[cases.Count * images.Length];
        var thresholdRows = new int[cases.Count * images.Length][];
        var outputs = Enumerable.Repeat(-1, cases.Count * images.Length).ToArray();
        var predicted = Enumerable.Repeat(-1, cases.Count * images.Length).ToArray();
        var slotReads = 0;
        var slotSelections = 0;
        foreach (var element in root.GetProperty("producerThresholdRows").EnumerateArray())
        {
            var row = Row(element, 9);
            Range(row[0], 0, cases.Count - 1);
            Range(row[1], 0, images.Length - 1);
            Range(row[2], 0, 4);
            var key = row[0] * images.Length + row[1];
            Unique(seenThreshold, key);
            thresholdRows[key] = row;
            var input = cases[row[0]];
            var producer = measured[row[0]];
            if (row[8] != producer[20])
            {
                throw Protocol("Threshold stage changed or discarded cumulative assumptions.");
            }
            var category = StatusCategory(row[2]);
            if (producer[15] != 0)
            {
                if (row[2] != 4)
                {
                    throw Protocol("Threshold stage ran without a completed actual compact output.");
                }
            }
            else if (row[2] == 4)
            {
                throw Protocol("Threshold stage was omitted despite a completed compact output.");
            }
            else if (row[2] == 0)
            {
                Range(row[3], 0, 3);
                var expectedBits = ThresholdBits(images[row[1]], input, (byte)producer[18]);
                predicted[key] = expectedBits;
                outputs[key] = row[3];
                var readsMatch = true;
                for (var read = 0; read < 4; read++)
                {
                    readsMatch &= row[4 + read] == (input.ThresholdEnabled ? P28ThresholdLogic.BlockOffset + input.ThresholdContext * 4 + read : -1);
                }
                readChecks[row[1]]++;
                if (!input.ThresholdEnabled) { disabledChecks[row[1]]++; }
                category = row[3] == expectedBits && readsMatch
                    ? row[8] == 0 ? Category.Match : Category.ConditionalMatch : Category.Mismatch;
                if (row[1] == 1 && input.ThresholdEnabled)
                {
                    slotReads += row[4..8].Contains(plan!.Offset) ? 1 : 0;
                    var chosen = Enumerable.Range(0, 2).Select(pair => P28ThresholdLogic.ThresholdOffset(input.ThresholdContext, pair,
                        (input.ThresholdPriorBits & (1 << pair)) != 0));
                    slotSelections += chosen.Contains(plan!.Offset) ? 1 : 0;
                }
            }
            thresholdCounts[row[1]].Add(category);
            AddIssue(issues, input.CaseId, row[1] == 0 ? "baseline-threshold" : "derived-threshold", category, row,
                unexpectedUnresolved: category == Category.Unresolved);
        }
        Complete(seenThreshold);
        P28ProducerDerivedSummary? derivedSummary = null;
        if (derived is not null)
        {
            var eligible = 0;
            var expectedChanged = 0;
            var actualChanged = 0;
            var exact = true;
            for (var caseId = 0; caseId < cases.Count; caseId++)
            {
                if (measured[caseId][15] != 0) { continue; }
                eligible++;
                var key = caseId * 2;
                var expectedChange = predicted[key] != predicted[key + 1];
                var actualChange = outputs[key] != outputs[key + 1];
                expectedChanged += expectedChange ? 1 : 0;
                actualChanged += actualChange ? 1 : 0;
                exact &= expectedChange == actualChange && outputs[key] >= 0 && outputs[key + 1] >= 0;
            }
            derivedSummary = new(true, eligible, expectedChanged, actualChanged, exact, slotReads, slotSelections,
                "Reading a LC word, selecting its edited byte, and changing a one-step predicate are three separately counted events.");
        }
        var gSummary = gCounts.Build();
        var fSummary = fCounts.Build();
        var threshold = thresholdCounts.Select((counter, index) => new P28ProducerThresholdSummary(index == 0 ? "baseline" : "derived",
            counter.Build(), readChecks[index], disabledChecks[index])).ToArray();
        var selectedIds = cases.Where(input => input.CaseId < 4 || input.CaseId is 65535 or 65536 or 131071 ||
            input.Group is "CarryAndDivisionBoundary" or "ZeroPositionAndPreviousState").Take(20).Select(input => input.CaseId)
            .Concat(issues.Take(16).Select(issue => issue.CaseId)).Distinct().ToArray();
        var examples = selectedIds.Select(id => new P28ProducerExample(cases[id], model[id], measured[id],
            Enumerable.Range(0, images.Length).Select(index => thresholdRows[id * images.Length + index]).ToArray())).ToArray();
        var used = new List<string>();
        if ((usedMask & 1) != 0) { used.Add(P28ProducerModel.AddEr1Assumption); }
        if ((usedMask & 2) != 0) { used.Add(P28ByteExecutionValidator.AddAssumption); }
        return new(1, runnerVersion, P28ByteExecutionValidator.UpstreamCommit, fixes, "SeededRomSlice", P28ProducerModel.ModelId,
            P28ProducerModel.SampleRepresentation, "NotEstablished",
            P28ProducerCases.Version, P28ProducerCases.RandomSeed, profile.Id, baseline.Hash, derived?.Hash,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding),
            plan is null ? null : P28RawThresholdEditor.ComputePlanDigest(plan), contracts,
            allowed.Count == 0 ? "strict" : "conditional", allowed, used,
            new Dictionary<string, int>(StringComparer.Ordinal)
            {
                [P28ProducerModel.AddEr1Assumption] = producerAssumptionCases,
                [P28ByteExecutionValidator.AddAssumption] = compactAssumptionCases,
            },
            cases.GroupBy(input => input.Group).ToDictionary(group => group.Key, group => group.Count(), StringComparer.Ordinal),
            gSummary, fSummary, threshold, derivedSummary, dispositions, examples, issues, diagnostics, scaling,
            gSummary.HasFailure || fSummary.HasFailure || threshold.Any(item => item.Counts.HasFailure || item.Counts.StoppedUnresolved > 0) || derivedSummary is { ExactChangedCaseSet: false },
            false, false, false, "not-tested", FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady,
            ["The finite raw-word case set is not an exhaustive six-word domain and may contain physically unreachable inputs.",
             "G executes unchanged bytes from RAM samples after capture; no timer, IRQ, reset, peripheral progression or full ECU boot is modeled.",
             "Sample words are interval-derived by the separately inspected acquisition path, not absolute timestamps. Acquisition mode DATA011F.2 is distinct from producer mode DATA0217.7 and is not executed here.",
             "G→F preserves CPU/RAM and explicitly stages PC from 07A5 to 07C7, omitting the separate history/delta bridge.",
             "Threshold is a staged fresh snapshot receiving actual F Code and explicit context/prior/enable inputs, not later physical output gates.",
             "Initialization-like seeds do not execute initialization; an early zero writes FFFF, while unresolved-before-ADD retains the old T.",
             "Word ADD er1,A and er3,A remain separately permitted tool-documented hypotheses; model agreement is not hardware proof.",
             "Physical clock/event scaling has no implicit defaults; any scaling preview is conditional and never changes flash readiness."]);
    }

    private static int ThresholdBits(RomImage image, P28ProducerInput input, byte code)
    {
        if (!input.ThresholdEnabled) { return input.ThresholdPriorBits; }
        var result = 0;
        for (var pair = 0; pair < 2; pair++)
        {
            if (P28ThresholdLogic.EvaluatePair(image.Span.Slice(P28ThresholdLogic.BlockOffset, 8), input.ThresholdContext, pair,
                (input.ThresholdPriorBits & (1 << pair)) != 0, code).NewState)
            {
                result |= 1 << pair;
            }
        }
        return result;
    }

    private static void ValidateCases(IReadOnlyList<P28ProducerInput> cases)
    {
        if (cases.Count is < 1 or > 200000)
        {
            throw new ArgumentException("Producer batch requires 1..200000 explicit cases.", nameof(cases));
        }
        for (var index = 0; index < cases.Count; index++)
        {
            var input = cases[index];
            if (input.CaseId != index || input.Samples.Count != 6 || input.ScratchPattern is not (0 or 85 or 170) ||
                input.ThresholdContext is < 0 or > 1 || input.ThresholdPriorBits is < 0 or > 3)
            {
                throw new ArgumentException("Producer cases must have contiguous IDs and valid explicit sample, scratch and threshold domains.", nameof(cases));
            }
        }
    }

    private static void ValidateContracts(IReadOnlyList<JsonElement> contracts)
    {
        var expected = JsonNode.Parse("""
            [{"id":"producer","entryPc":1906,"exitPcs":[1957],"stop":"BeforeInstruction",
              "allowedCodeRanges":[[1906,1957],[31468,31486]],"psw":4353,"lrb":64,"usp":384,
              "instructionBudget":192,"sampleAddresses":[864,866,868,870,872,874],
              "previousTAddress":196,"statusAddresses":[535,561],"codeDataSpacesSeparate":true,
              "interrupts":"NotInjected","peripherals":"Frozen","admission":"ExactInstructionForms"},
             {"id":"producerToCompact","composition":"StagedControlFlowSameCpuRam",
              "fromPc":1957,"toPc":1991,"exitPc":2082,"instructionBudget":128,
              "reseedsCpuOrRam":false,"skippedRange":[1957,1991],"continuousWholeRoutine":false,
              "transferredInputs":["actual DATA00C4","actual DATA0217.4"],"assumptions":"Cumulative"},
             {"id":"composedThreshold","composition":"StagedFreshThresholdSeed",
              "entryPc":4652,"exitPcs":[4717,4737],"allowedCodeRanges":[[4652,4717]],
              "psw":257,"lrb":32,"usp":640,"instructionBudget":128,
              "codeInput":"ActualCompactExecutionOutput","contextPriorEnabled":"ExplicitPerCaseInputs",
              "allowedAssumptions":[],"cumulativeAssumptionsRetained":true}]
            """);
        var actual = JsonSerializer.SerializeToNode(contracts);
        if (!JsonNode.DeepEquals(expected, actual))
        {
            throw Protocol("Producer entry or composition contract differs from the independently reviewed boundaries.");
        }
    }

    private enum Category { Match, ConditionalMatch, Unresolved, Mismatch, Error, Budget, NotRun, UnresolvedModel }
    private static Category StatusCategory(int status) => status switch
    {
        0 => Category.Match,
        1 => Category.Unresolved,
        2 => Category.Error,
        3 => Category.Budget,
        4 => Category.NotRun,
        _ => throw Protocol("Unknown producer status."),
    };
    private static Category Convert(P28ExecutionCategory category) => category switch
    {
        P28ExecutionCategory.Match => Category.Match,
        P28ExecutionCategory.ConditionalMatch => Category.ConditionalMatch,
        P28ExecutionCategory.UnresolvedInstruction => Category.Unresolved,
        P28ExecutionCategory.Mismatch => Category.Mismatch,
        P28ExecutionCategory.ExecutionError => Category.Error,
        P28ExecutionCategory.BudgetExceeded => Category.Budget,
        _ => Category.UnresolvedModel,
    };
    private sealed class Counter
    {
        private readonly int[] _counts = new int[8];
        public void Add(Category category) => _counts[(int)category]++;
        public P28ProducerStageCounts Build() => new(_counts.Sum(), _counts[0], _counts[1], _counts[2], _counts[3], _counts[4], _counts[5], _counts[6], _counts[7]);
    }
    private static void AddIssue(List<P28ProducerComparisonIssue> issues, int id, string stage, Category category, int[] row, bool unexpectedUnresolved = false)
    {
        if (issues.Count < 64 && (unexpectedUnresolved || category is Category.Mismatch or Category.Error or Category.Budget or Category.UnresolvedModel))
        {
            issues.Add(new(id, stage, category.ToString(), row));
        }
    }
    private static int[] Row(JsonElement element, int width)
    {
        if (element.GetArrayLength() != width) { throw Protocol("Incorrect producer packed-row width."); }
        return element.EnumerateArray().Select(item => item.GetInt32()).ToArray();
    }
    private static void Range(int value, int minimum, int maximum)
    {
        if (value < minimum || value > maximum) { throw Protocol("Producer row field outside its declared domain."); }
    }
    private static void Unique(bool[] seen, int key)
    {
        if (seen[key]) { throw Protocol("Duplicate producer case."); }
        seen[key] = true;
    }
    private static void Complete(bool[] seen)
    {
        if (seen.Contains(false)) { throw Protocol("Producer response omitted requested cases."); }
    }
    private static SliceProcessException Protocol(string message, Exception? inner = null) => new(SliceProcessFailure.Protocol, message, inner);
}
