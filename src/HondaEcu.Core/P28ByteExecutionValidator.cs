using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public enum P28ExecutionCategory
{
    Match,
    ConditionalMatch,
    UnresolvedInstruction,
    UnresolvedModel,
    Mismatch,
    ExecutionError,
    BudgetExceeded,
}

public sealed record P28ExecutionCounts(
    int Total, int CompletedWithoutAssumptions, int ConditionalMatches, int StoppedUnresolved,
    int UnresolvedModel, int Mismatches, int ExecutionErrors, int BudgetExceeded)
{
    public bool HasFailure => Mismatches + ExecutionErrors + BudgetExceeded + UnresolvedModel != 0;
}

public sealed record P28ExecutionIssue(string Slice, int[] InputAndOutput, string Reason);
public sealed record P28ThresholdExecutionSummary(string ImageId, P28ExecutionCounts Counts, int ProgramReadChecks, int DisabledPreservationChecks);
public sealed record P28DerivedExecutionComparison(
    bool VerifiedM1cLineage, int ComparedCases, int ExpectedChangedCases, int ActualChangedCases,
    bool ExactChangedCaseSet, int ChangedByteReadCases, bool ChangedByteActuallyRead);

public sealed record P28ExecutionReport(
    int ProtocolVersion, string RunnerVersion, string UpstreamCommit, IReadOnlyList<string> LocalSemanticFixes,
    string ExecutionKind, string ProfileId, RomHash BaselineHash, RomHash? DerivedHash,
    string ProfileDigest, string BindingDigest, string? PlanDigest,
    IReadOnlyList<JsonElement> EntryContracts, string Mode,
    IReadOnlyList<string> PermittedAssumptions, IReadOnlyList<string> UsedAssumptions,
    IReadOnlyList<int> ScratchPatterns, P28ExecutionCounts Compact,
    IReadOnlyList<P28ThresholdExecutionSummary> Threshold,
    P28DerivedExecutionComparison? DerivedComparison,
    IReadOnlyList<P28ExecutionIssue> Issues, IReadOnlyList<JsonElement> Diagnostics,
    string RunnerDiagnostics, bool HasFailure,
    bool SoftwareInterpreterExecutedActualRomBytes, bool FullEcuBootPerformed,
    bool HardwareExecutionPerformed, bool PhysicalRpmAvailable, string Checksum,
    FlashReadinessStatus FlashReadiness, FlashSafetyStatus FlashSafety,
    IReadOnlyList<string> Limitations);

/// <summary>Compares measured executor outputs; it never executes an instruction or promotes the compact model.</summary>
public static class P28ByteExecutionValidator
{
    public const string UpstreamCommit = "85b30752473ca9979e4ad9b307ea05a30c0b3d1e";
    public const string AddAssumption = "oki.add-er3-a";
    private static readonly int[] Patterns = [0, 85, 170];
    private static readonly string[] ExpectedFixes = ["word-ror-through-carry-preserves-noncarry-flags", "load-zero-flag-and-dd-contract", "word-srl-preserves-noncarry-flags", "bit-operands-use-byte-access"];

    public static void ValidateAdmission(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        RomImage? derived = null, P28RawThresholdPlan? plan = null, P28RawThresholdPatchReport? patchReport = null)
    {
        var inspection = P28VtecInspector.Inspect(baseline, profile, [profile], confirmed, binding);
        if (!inspection.InterpretationApplied || inspection.BaselineBinding.Status != P28BaselineBindingStatus.Matched)
        {
            throw new InvalidDataException("Byte execution requires the unchanged original baseline, matching research binding and explicit profile acknowledgement.");
        }
        var lineageCount = new object?[] { derived, plan, patchReport }.Count(value => value is not null);
        if (lineageCount is not (0 or 3))
        {
            throw new InvalidDataException("Derived execution requires output, original-parent plan and patch report together.");
        }
        if (derived is not null && !P28RawThresholdEditor.Verify(derived, baseline, profile, binding, plan!, patchReport!).IsValid)
        {
            throw new InvalidDataException("Derived execution refused: existing M1c original-parent/plan/report verification failed.");
        }
    }

    public static object CreateRequest(RomImage baseline, RomImage? derived, bool allowAddAssumption)
    {
        var images = new List<object>
        {
            new { id = "baseline", rom = baseline.ToArray().Select(value => (int)value).ToArray() },
        };
        if (derived is not null)
        {
            images.Add(new { id = "derived", rom = derived.ToArray().Select(value => (int)value).ToArray() });
        }
        return new
        {
            protocolVersion = SeededSliceProcess.ProtocolVersion,
            operation = "p28Batch",
            images,
            allowAssumptions = allowAddAssumption ? new[] { AddAssumption } : [],
            scratchPatterns = Patterns,
        };
    }

    public static async Task<P28ExecutionReport> ExecuteAsync(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, bool allowAddAssumption = false,
        RomImage? derived = null, P28RawThresholdPlan? plan = null, P28RawThresholdPatchReport? patchReport = null,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default)
    {
        ValidateAdmission(baseline, profile, binding, confirmed, derived, plan, patchReport);
        var response = await SeededSliceProcess.ExchangeAsync(
            runner, CreateRequest(baseline, derived, allowAddAssumption), options, cancellationToken).ConfigureAwait(false);
        var report = Analyze(baseline, profile, binding, allowAddAssumption, response, derived, plan, patchReport);
        var diagnostics = report.Diagnostics.ToList();
        // Model mismatches are known only after C# comparison. Re-execute at most four
        // of them using the same unchanged image and entry state, never one process per pass.
        foreach (var issue in report.Issues.Where(issue => issue.Reason == nameof(P28ExecutionCategory.Mismatch)).Take(4))
        {
            var compact = issue.Slice == "compact";
            var row = issue.InputAndOutput;
            var pattern = compact ? row[0] : row[1];
            var image = compact || row[0] == 0 ? baseline : derived!;
            var seeds = compact
                ? new[] { new[] { 0xC4, row[1] & 255 }, [0xC5, row[1] >> 8], [0x217, row[2] * 16] }
                : new[] { new[] { 0x133, row[2] }, [0x131, row[4] << 1], [0xCC, 0], [0x11E, (row[3] == 0 ? 8 : 0) | row[5] * 16] };
            var contract = new
            {
                entryPc = compact ? 0x07C7 : 0x122C,
                exitPcs = compact ? new[] { 0x0822 } : [0x126D, 0x1281],
                allowedCodeRanges = compact ? new[] { new[] { 0x07C7, 0x0822 } } : [[0x122C, 0x126D]],
                psw = compact ? 0x1101 : 0x0101,
                lrb = compact ? 0x0040 : 0x0020,
                usp = compact ? 0x0180 : 0x0280,
                instructionBudget = 128,
                dataSeeds = seeds,
                outputAddresses = compact ? new[] { 0x133, 0xB8 } : [0x131],
            };
            try
            {
                var replay = await SeededSliceProcess.ExchangeAsync(runner, new
                {
                    protocolVersion = 1,
                    operation = "synthetic",
                    images = new[] { new { id = "diagnostic-replay", rom = image.ToArray().Select(value => (int)value).ToArray() } },
                    allowAssumptions = compact && allowAddAssumption ? new[] { AddAssumption } : [],
                    scratchPatterns = new[] { pattern },
                    synthetic = contract,
                }, options, cancellationToken).ConfigureAwait(false);
                _ = ValidateIdentity(replay.Response, "synthetic");
                var result = replay.Response.GetProperty("syntheticResult");
                if (result.GetProperty("trace").GetArrayLength() > 128)
                {
                    throw Protocol("Invalid bounded mismatch replay response.");
                }
                var outputs = result.GetProperty("outputs").EnumerateArray().Select(value => value.GetInt32()).ToArray();
                var assumptions = result.GetProperty("usedAssumptions").EnumerateArray().Select(value => value.GetString()).ToArray();
                var expectedAssumptions = compact && row[6] != 0 ? new[] { AddAssumption } : [];
                var consistent = result.GetProperty("status").GetInt32() == 0 && assumptions.SequenceEqual(expectedAssumptions) &&
                    (compact ? outputs.Length == 2 && outputs[0] == row[4] && ((outputs[1] >> 4) & 1) == row[5]
                        : outputs.Length == 1 && ((outputs[0] >> 1) & 3) == row[7]);
                diagnostics.Add(JsonSerializer.SerializeToElement(new
                {
                    purpose = "C#-detected model mismatch; unchanged original-byte replay, not a synthetic-program result",
                    slice = issue.Slice,
                    inputAndOutput = row,
                    replayContract = contract,
                    replayConsistency = consistent,
                    result,
                }, JsonDefaults.Create(false)));
            }
            catch (Exception exception) when (exception is SliceProcessException or JsonException or InvalidOperationException or KeyNotFoundException)
            {
                // Preserve the measured primary mismatch even if a diagnostic subprocess
                // fails. Explicitly record that its trace was not obtained; never call it reproduced.
                diagnostics.Add(JsonSerializer.SerializeToElement(new
                {
                    purpose = "Mismatch diagnostic replay failed; primary batch mismatch is retained",
                    slice = issue.Slice,
                    inputAndOutput = row,
                    replayConsistency = false,
                    traceObtained = false,
                    failure = exception is SliceProcessException processException ? processException.Failure.ToString() : "Protocol",
                }, JsonDefaults.Create(false)));
            }
        }
        return report with { Diagnostics = diagnostics };
    }

    public static P28ExecutionCategory ClassifyCompact(
        ushort raw, bool s, int status, int code, int extraBit, bool assumptionUsed, bool assumptionPermitted)
    {
        if (assumptionUsed && !assumptionPermitted)
        {
            throw Protocol("Runner used an assumption that was not permitted.");
        }
        if (status == 1)
        {
            return P28ExecutionCategory.UnresolvedInstruction;
        }
        if (status == 2)
        {
            return P28ExecutionCategory.ExecutionError;
        }
        if (status == 3)
        {
            return P28ExecutionCategory.BudgetExceeded;
        }
        if (status != 0 || code is < 0 or > 255 || extraBit is < 0 or > 1)
        {
            throw Protocol("Invalid completed compact record.");
        }
        if (assumptionUsed)
        {
            var hypothesis = P28CompactModel.EvaluateHypothesis(raw, s);
            return code == hypothesis.Code && (extraBit != 0) == hypothesis.ExtraBit
                ? P28ExecutionCategory.ConditionalMatch : P28ExecutionCategory.Mismatch;
        }
        var established = P28CompactModel.Evaluate(raw, s);
        if (!established.Resolved)
        {
            return P28ExecutionCategory.UnresolvedModel;
        }
        return code == established.Code && (extraBit != 0) == established.ExtraBit
            ? P28ExecutionCategory.Match : P28ExecutionCategory.Mismatch;
    }

    public static P28ExecutionReport Analyze(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool allowAddAssumption,
        SliceProcessResponse response, RomImage? derived = null,
        P28RawThresholdPlan? plan = null, P28RawThresholdPatchReport? patchReport = null)
    {
        ValidateAdmission(baseline, profile, binding, true, derived, plan, patchReport);
        try
        {
            return AnalyzeCore(baseline, profile, binding, allowAddAssumption, response, derived, plan);
        }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or OverflowException)
        {
            throw Protocol("Malformed or incomplete runner response.", exception);
        }
    }

    private static P28ExecutionReport AnalyzeCore(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool allowAddAssumption,
        SliceProcessResponse response, RomImage? derived, P28RawThresholdPlan? plan)
    {
        var root = response.Response;
        var fixes = ValidateIdentity(root, "p28Batch");
        var contracts = root.GetProperty("entryContracts").EnumerateArray().Select(item => item.Clone()).ToArray();
        if (contracts.Length != 2 || contracts.Any(item => item.ValueKind != JsonValueKind.Object))
        {
            throw Protocol("Both entry contracts must be reported.");
        }
        ValidateContract(contracts[0], true);
        ValidateContract(contracts[1], false);
        var diagnostics = root.GetProperty("diagnostics").EnumerateArray().Select(item => item.Clone()).ToArray();
        if (diagnostics.Length > 128)
        {
            throw Protocol("Runner diagnostics exceed the bounded selected-case contract.");
        }
        foreach (var diagnostic in diagnostics)
        {
            if (diagnostic.GetProperty("result").GetProperty("trace").GetArrayLength() > 128)
            {
                throw Protocol("Selected-case trace exceeds its instruction bound.");
            }
        }
        var compactCounts = new Counter();
        var seenCompact = new bool[Patterns.Length * 2 * 65536];
        var issues = new List<P28ExecutionIssue>();
        var used = false;
        foreach (var element in root.GetProperty("compactRows").EnumerateArray())
        {
            var row = Row(element, 7);
            var pattern = PatternIndex(row[0]);
            RequireRange(row[1], 0, 65535);
            RequireRange(row[2], 0, 1);
            RequireRange(row[3], 0, 3);
            RequireRange(row[6], 0, 1);
            var key = ((pattern * 2) + row[2]) * 65536 + row[1];
            Unique(seenCompact, key);
            var category = ClassifyCompact((ushort)row[1], row[2] != 0, row[3], row[4], row[5], row[6] != 0, allowAddAssumption);
            used |= row[6] != 0;
            compactCounts.Add(category);
            AddIssue(issues, "compact", row, category);
        }
        Complete(seenCompact);

        var images = derived is null ? new[] { baseline } : new[] { baseline, derived };
        var thresholdCounts = images.Select(_ => new Counter()).ToArray();
        var readChecks = new int[images.Length];
        var disabledChecks = new int[images.Length];
        const int casesPerPattern = 256 * 2 * 4 * 2;
        var casesPerImage = Patterns.Length * casesPerPattern;
        var seenThreshold = new bool[images.Length * casesPerImage];
        var measured = Enumerable.Repeat(-1, images.Length * casesPerImage).ToArray();
        var expected = new int[images.Length * casesPerImage];
        var changedByteReads = 0;
        foreach (var element in root.GetProperty("thresholdRows").EnumerateArray())
        {
            var row = Row(element, 12);
            RequireRange(row[0], 0, images.Length - 1);
            var pattern = PatternIndex(row[1]);
            RequireRange(row[2], 0, 255);
            RequireRange(row[3], 0, 1);
            RequireRange(row[4], 0, 3);
            RequireRange(row[5], 0, 1);
            RequireRange(row[6], 0, 3);
            var keyWithinImage = ((((pattern * 256) + row[2]) * 2 + row[3]) * 4 + row[4]) * 2 + row[5];
            var key = row[0] * casesPerImage + keyWithinImage;
            Unique(seenThreshold, key);
            var block = images[row[0]].Span.Slice(P28ThresholdLogic.BlockOffset, P28ThresholdLogic.BlockLength);
            var expectedBits = row[4];
            if (row[5] != 0)
            {
                expectedBits = 0;
                for (var pair = 0; pair < 2; pair++)
                {
                    if (P28ThresholdLogic.EvaluatePair(block, row[3], pair, (row[4] & (1 << pair)) != 0, (byte)row[2]).NewState)
                    {
                        expectedBits |= 1 << pair;
                    }
                }
            }
            expected[key] = expectedBits;
            var category = row[6] switch
            {
                1 => P28ExecutionCategory.UnresolvedInstruction,
                2 => P28ExecutionCategory.ExecutionError,
                3 => P28ExecutionCategory.BudgetExceeded,
                _ => P28ExecutionCategory.Match,
            };
            if (row[6] == 0)
            {
                RequireRange(row[7], 0, 3);
                measured[key] = row[7];
                var readsMatch = true;
                for (var read = 0; read < 4; read++)
                {
                    var address = row[5] == 0 ? -1 : P28ThresholdLogic.BlockOffset + row[3] * 4 + read;
                    readsMatch &= row[8 + read] == address;
                }
                readChecks[row[0]]++;
                if (row[5] == 0)
                {
                    disabledChecks[row[0]]++;
                }
                if (row[0] == 1 && row[5] == 1 && row[8..].Contains(plan!.Offset))
                {
                    changedByteReads++;
                }
                if (row[7] != expectedBits || !readsMatch)
                {
                    category = P28ExecutionCategory.Mismatch;
                }
            }
            thresholdCounts[row[0]].Add(category);
            AddIssue(issues, row[0] == 0 ? "baseline-threshold" : "derived-threshold", row, category);
        }
        Complete(seenThreshold);
        P28DerivedExecutionComparison? comparison = null;
        if (derived is not null)
        {
            var expectedChanged = 0;
            var actualChanged = 0;
            var exact = true;
            for (var key = 0; key < casesPerImage; key++)
            {
                var shouldChange = expected[key] != expected[casesPerImage + key];
                var didChange = measured[key] != measured[casesPerImage + key];
                expectedChanged += shouldChange ? 1 : 0;
                actualChanged += didChange ? 1 : 0;
                exact &= shouldChange == didChange && measured[key] >= 0 && measured[casesPerImage + key] >= 0;
            }
            comparison = new P28DerivedExecutionComparison(true, casesPerImage, expectedChanged, actualChanged,
                exact, changedByteReads, plan!.IsNoOp || changedByteReads > 0);
        }
        var compactSummary = compactCounts.Build();
        var threshold = thresholdCounts.Select((counter, index) => new P28ThresholdExecutionSummary(
            index == 0 ? "baseline" : "derived", counter.Build(), readChecks[index], disabledChecks[index])).ToArray();
        var failed = compactSummary.HasFailure || threshold.Any(item => item.Counts.HasFailure || item.Counts.StoppedUnresolved > 0) ||
            comparison is { ExactChangedCaseSet: false } || comparison is { ChangedByteActuallyRead: false };
        return new P28ExecutionReport(1, "0.1.0", UpstreamCommit, fixes, "SeededRomSlice", profile.Id,
            baseline.Hash, derived?.Hash, P28VtecInspector.ComputeProfileDigest(profile),
            P28RawThresholdEditor.ComputeBindingDigest(binding), plan is null ? null : P28RawThresholdEditor.ComputePlanDigest(plan),
            contracts, allowAddAssumption ? "conditional" : "strict", allowAddAssumption ? [AddAssumption] : [], used ? [AddAssumption] : [],
            Patterns.ToArray(), compactSummary, threshold, comparison, issues, diagnostics, response.Diagnostics, failed,
            true, false, false, false, "not-tested", FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady,
            ["Seeded software instruction execution only; no reset/full ECU boot or hardware execution.",
             "Peripheral/time progression is frozen and interrupts/external events are absent.",
             "ADD agreement is conditional model agreement, not independent confirmation of instruction semantics.",
             "Physical RPM, native checksum validity, external-editor behavior and factory provenance remain unavailable or unverified.",
             "Software state bits are not physical VTEC outputs; production profiles, Oracle evidence and flash readiness are unchanged."]);
    }

    private static int[] Row(JsonElement element, int length)
    {
        if (element.ValueKind != JsonValueKind.Array || element.GetArrayLength() != length)
        {
            throw Protocol("Wrong packed row width.");
        }
        return element.EnumerateArray().Select(value => value.GetInt32()).ToArray();
    }

    private static void ValidateContract(JsonElement contract, bool compact)
    {
        var expected = compact ? JsonNode.Parse("""
            {"id":"compact","entryPc":1991,"exitPcs":[2082],"stop":"BeforeInstruction",
             "allowedCodeRanges":[[1991,2082]],"psw":4353,"lrb":64,"usp":384,"instructionBudget":128,
             "inputs":["DATA00C4 unsigned LE word","DATA0217.4"],"outputs":["DATA0133","DATA00B8.4"],
             "codeDataSpacesSeparate":true,"freshStatePerCase":true,"interrupts":"NotInjected","peripherals":"Frozen"}
            """) : JsonNode.Parse("""
            {"id":"threshold","entryPc":4652,"exitPcs":[4717,4737],"stop":"BeforeInstruction",
             "allowedCodeRanges":[[4652,4717]],"psw":257,"lrb":32,"usp":640,"instructionBudget":128,
             "inputs":["DATA0133 code","DATA011E.3 context","DATA011E.4 enabled","DATA0131.1/.2 prior"],
             "outputs":["DATA0131.1/.2"],"fixedPreconditions":{"DATA00CC":0,"DATA0131bit0":0},
             "allowedProgramDataReads":[25922,25930],"codeDataSpacesSeparate":true,"freshStatePerCase":true,
             "interrupts":"NotInjected","peripherals":"Frozen"}
            """);
        if (!JsonNode.DeepEquals(expected, JsonNode.Parse(contract.GetRawText())))
        {
            throw Protocol("Runner entry contract differs from the reviewed P28 contract.");
        }
    }

    private static string[] ValidateIdentity(JsonElement root, string operation)
    {
        if (root.GetProperty("protocolVersion").GetInt32() != 1 ||
            root.GetProperty("operation").GetString() != operation ||
            root.GetProperty("upstreamCommit").GetString() != UpstreamCommit ||
            root.GetProperty("runnerVersion").GetString() != "0.1.0")
        {
            throw Protocol("Runner identity, operation or protocol version differs from this audited adapter.");
        }
        var fixes = root.GetProperty("localSemanticFixes").EnumerateArray().Select(item => item.GetString()!).ToArray();
        if (!fixes.Order(StringComparer.Ordinal).SequenceEqual(ExpectedFixes.Order(StringComparer.Ordinal)))
        {
            throw Protocol("Audited local semantic fixes must be declared exactly.");
        }
        return fixes;
    }

    private static int PatternIndex(int pattern)
    {
        var index = Array.IndexOf(Patterns, pattern);
        if (index < 0)
        {
            throw Protocol("Unexpected scratch pattern.");
        }
        return index;
    }

    private static void RequireRange(int value, int minimum, int maximum)
    {
        if (value < minimum || value > maximum)
        {
            throw Protocol("Packed field is outside its declared domain.");
        }
    }

    private static void Unique(bool[] seen, int index)
    {
        if (seen[index])
        {
            throw Protocol("Duplicate case in runner response.");
        }
        seen[index] = true;
    }

    private static void Complete(bool[] seen)
    {
        if (seen.Contains(false))
        {
            throw Protocol("Runner response did not cover every required case.");
        }
    }

    private static void AddIssue(List<P28ExecutionIssue> issues, string slice, int[] row, P28ExecutionCategory category)
    {
        if (issues.Count < 64 && category is P28ExecutionCategory.Mismatch or P28ExecutionCategory.ExecutionError or P28ExecutionCategory.BudgetExceeded or P28ExecutionCategory.UnresolvedModel)
        {
            issues.Add(new P28ExecutionIssue(slice, row, category.ToString()));
        }
    }

    private static SliceProcessException Protocol(string message, Exception? inner = null) =>
        new(SliceProcessFailure.Protocol, message, inner);

    private sealed class Counter
    {
        private readonly int[] _counts = new int[Enum.GetValues<P28ExecutionCategory>().Length];
        public void Add(P28ExecutionCategory category) => _counts[(int)category]++;
        public P28ExecutionCounts Build() => new(_counts.Sum(), _counts[0], _counts[1], _counts[2], _counts[3], _counts[4], _counts[5], _counts[6]);
    }
}
