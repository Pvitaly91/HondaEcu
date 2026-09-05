using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

/// <summary>Read-only research verifier; calculations never depend on runner output.</summary>
public static class P28NativeChecksumVerifier
{
    private static readonly int[] Patterns = [0, 85, 170];

    public static IReadOnlyList<string> ValidateAssumptions(IEnumerable<string>? assumptions)
    {
        var allowed = (assumptions ?? []).ToArray();
        if (allowed.Length != 0) throw new ArgumentException("The audited checksum task permits no instruction assumptions. The er1/er3 permissions do not apply.", nameof(assumptions));
        return Array.Empty<string>();
    }

    public static object CreateRequest(IReadOnlyList<(string Id, RomImage Image)> images)
    {
        if (images.Count is < 1 or > 32 || images.Select(item => item.Id).Distinct(StringComparer.Ordinal).Count() != images.Count ||
            images.Any(item => string.IsNullOrWhiteSpace(item.Id) || item.Id.Length > 64 ||
                item.Id.Any(character => !char.IsAsciiLetterOrDigit(character) && character is not ('-' or '_' or '.')) ||
                item.Image.Size != P28NativeChecksumArithmetic.RomSize))
            throw new ArgumentException("Checksum transport requires 1–32 uniquely named 32768-byte images.", nameof(images));
        return new
        {
            protocolVersion = 1,
            operation = "checksumBatch",
            images = images.Select(item => new { id = item.Id, rom = item.Image.ToArray().Select(value => (int)value).ToArray() }).ToArray(),
            allowAssumptions = Array.Empty<string>(),
            scratchPatterns = Patterns,
        };
    }

    public static async Task<P28NativeChecksumReport> CheckAsync(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string? runner = null, IEnumerable<string>? assumptions = null, RomImage? derived = null,
        P28RawThresholdPlan? plan = null, P28RawThresholdPatchReport? patchReport = null,
        SliceProcessOptions? options = null, CancellationToken cancellationToken = default,
        P28VerifiedChecksumComposition? composition = null)
    {
        cancellationToken.ThrowIfCancellationRequested();
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, confirmed, derived, plan, patchReport, composition);
        _ = ValidateAssumptions(assumptions);
        var inputs = new List<(string Id, RomImage Image)> { ("baseline", baseline) };
        if (derived is not null) inputs.Add(("derived", derived));
        var calculations = inputs.Select(item => P28NativeChecksumArithmetic.Calculate(item.Image)).ToArray();
        var assessments = inputs.Select(item => P28ChecksumCodeGuard.Assess(item.Image)).ToArray();
        SliceProcessResponse? response = null;
        string? transportFailure = null;
        var runnerAvailable = !string.IsNullOrWhiteSpace(runner) && File.Exists(runner);
        if (runnerAvailable && assessments.All(item => item.ContractRecognized))
        {
            try
            {
                response = await SeededSliceProcess.ExchangeAsync(runner!, CreateRequest(inputs), options, cancellationToken).ConfigureAwait(false);
            }
            catch (SliceProcessException exception) { transportFailure = $"{exception.Failure}: {exception.Message}"; }
        }
        var executions = new List<P28ChecksumExecution[]>();
        var contracts = Array.Empty<JsonElement>();
        var fixes = Array.Empty<string>();
        string? runnerVersion = null;
        string? upstream = null;
        if (response is not null)
        {
            try
            {
                fixes = SliceRunnerIdentity.Validate(response.Response, "checksumBatch");
                runnerVersion = response.Response.GetProperty("runnerVersion").GetString();
                upstream = response.Response.GetProperty("upstreamCommit").GetString();
                contracts = ValidateEntryContract(response.Response);
                var rows = response.Response.GetProperty("checksumCases").EnumerateArray().ToArray();
                if (rows.Length != inputs.Count * Patterns.Length) throw Protocol("Checksum response must contain every image/scratch case exactly once.");
                var seen = new HashSet<(int Image, int Pattern)>();
                foreach (var row in rows)
                {
                    var imageIndex = Int(row, "imageIndex", 0, inputs.Count - 1);
                    var pattern = Int(row, "scratchPattern", 0, 255);
                    if (!Patterns.Contains(pattern) || !seen.Add((imageIndex, pattern))) throw Protocol("Unexpected or duplicate checksum image/pattern.");
                }
                for (var index = 0; index < inputs.Count; index++)
                    executions.Add(Patterns.Select(pattern => CompareExecution(inputs[index].Image,
                        rows.Single(row => row.GetProperty("imageIndex").GetInt32() == index && row.GetProperty("scratchPattern").GetInt32() == pattern))).ToArray());
            }
            catch (Exception exception) when (exception is SliceProcessException or JsonException or KeyNotFoundException or InvalidOperationException or FormatException or OverflowException)
            {
                transportFailure = $"Protocol: {exception.Message}";
                executions.Clear();
            }
        }
        if (executions.Count == 0)
        {
            foreach (var assessment in assessments)
            {
                var reason = transportFailure ?? (!assessment.ContractRecognized ? "Native code contract unrecognized/altered; no scoped execution admitted." :
                    !runnerAvailable ? "Runner missing or not selected. Arithmetic was calculated; byte execution was not run." : "Execution was not admitted for this image set.");
                executions.Add(Patterns.Select(pattern => new P28ChecksumExecution(pattern,
                    transportFailure is null ? NativeChecksumExecutionStatus.NotRun : NativeChecksumExecutionStatus.ExecutionError,
                    false, null, null, 0, 0, null, 0, [], false, false, [], [], reason)).ToArray());
            }
        }
        var cases = inputs.Select((item, index) =>
        {
            var (disposition, status, reason) = Decide(assessments[index], calculations[index], executions[index]);
            return new P28NativeChecksumCaseReport(item.Id, item.Id == "baseline" ? "OriginalResearchBaseline" : composition is null ? "VerifiedM1cChild" : "VerifiedChecksumCompositionChild",
                item.Image.Hash, [], assessments[index], calculations[index], executions[index], disposition, status, reason);
        }).ToArray();
        var all = executions.SelectMany(items => items).ToArray();
        int Count(NativeChecksumExecutionStatus status) => all.Count(item => item.Status == status);
        var counts = new P28ChecksumExecutionCounts(all.Length, Count(NativeChecksumExecutionStatus.Match),
            Count(NativeChecksumExecutionStatus.ConditionalMatch), Count(NativeChecksumExecutionStatus.UnresolvedInstruction) + Count(NativeChecksumExecutionStatus.Incomplete),
            Count(NativeChecksumExecutionStatus.Mismatch), Count(NativeChecksumExecutionStatus.ExecutionError),
            Count(NativeChecksumExecutionStatus.BudgetExceeded), Count(NativeChecksumExecutionStatus.NotRun));
        return new(1, "ScopedNativeRomChecksum", P28NativeChecksumArithmetic.Contract, profile.Id, baseline.Hash, derived?.Hash,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding),
            composition is not null ? P28ChecksumPreservingEditor.ComputePlanDigest(composition.Plan) : plan is null ? null : P28RawThresholdEditor.ComputePlanDigest(plan), derived is not null, "strict", [], [],
            runnerVersion, upstream, fixes, contracts, cases, counts,
            counts.Mismatches + counts.ExecutionErrors + counts.BudgetExceeded != 0 || cases.Any(item => item.ChecksumStatus == ChecksumStatus.Invalid),
            assessments.All(item => item.ContractRecognized)
                ? P28NativeChecksumArithmetic.Contract.Evidence
                : "Unresolved/Unsupported for this input: native initialization or code contract was not recognized. Arithmetic applies the documented research model hypothetically; it does not assign a native algorithm to this ROM.",
            transportFailure ?? response?.Diagnostics ?? "", false, false, false,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady,
            ["Seeded checksum progression, not full ECU boot or execution of scheduler/startup/peripherals.",
             "A scoped arithmetic Valid result is not factory provenance, physical-CPU validation, flash readiness or permission to repair.",
             "Private research binding declares an exact input/profile only; it is not a trusted revision identity.",
             composition is null ? "No checksum field, exclusion, repair, bypass, compensating storage or new patch chain is introduced." :
                "This read-only verifier performs no repair or bypass. The separately admitted original-parent composition contains an explicit computed compensation byte under its reviewed scope; no factory checksum-storage claim is made."]);
    }

    public static (NativeChecksumDisposition Disposition, ChecksumStatus Status, string Reason) Decide(
        P28ChecksumCodeAssessment code, P28ChecksumArithmetic arithmetic, IReadOnlyList<P28ChecksumExecution> execution)
    {
        if (!code.ContractRecognized || !code.GateEnabled)
            return (code.Disposition, ChecksumStatus.Unknown, "Native checksum is unsupported, altered or disabled; the arithmetic residue is not promoted to Valid.");
        if (execution.Any(item => item.Status is not (NativeChecksumExecutionStatus.Match or NativeChecksumExecutionStatus.NotRun)))
            return (NativeChecksumDisposition.Unresolved, ChecksumStatus.Unknown,
                "Unresolved, conditional, incomplete, mismatched or failed byte execution cannot establish unconditional native Valid/Invalid.");
        return arithmetic.ResidueMatches
            ? (NativeChecksumDisposition.Valid, ChecksumStatus.Valid, "Zero residue under the recognized, enabled scoped contract. Execution evidence is reported separately; NotFlashReady remains.")
            : (NativeChecksumDisposition.Invalid, ChecksumStatus.Invalid, "Nonzero residue under the recognized, enabled scoped contract. No checksum repair was attempted.");
    }

    /// <summary>
    /// Low-level measured-vs-integer comparison for controlled synthetic/private memory
    /// experiments. This does not admit a ROM revision or assign ChecksumStatus.Valid.
    /// </summary>
    public static P28ChecksumExecution CompareExecution(RomImage image, JsonElement row)
    {
        try
        {
            var model = P28NativeChecksumArithmetic.Calculate(image);
            var status = Int(row, "status", 0, 3);
            var pattern = Int(row, "scratchPattern", 0, 255);
            var complete = row.GetProperty("completed").GetBoolean();
            var invocations = Int(row, "invocations", 0, 512);
            var steps = Int(row, "steps", 0, 131072);
            var stopPc = Int(row, "stopPc", 0, 65535);
            var residue = Int(row, "residue", -1, 255);
            var counter = Int(row, "counter", 0, 65535);
            var accumulatedByte = Int(row, "accumulatedByte", 0, 255);
            var statusByte = Int(row, "statusByte", 0, 255);
            var decision = row.GetProperty("decision").GetString();
            var assumptions = row.GetProperty("usedAssumptions").EnumerateArray().Select(item => item.GetString()!).ToArray();
            if (assumptions.Length != 0) throw Protocol("Checksum execution used an assumption: no instruction permission is defined for this task.");
            var trace = row.GetProperty("trace").EnumerateArray().Select(item => item.Clone()).ToArray();
            if (trace.Length > 128) throw Protocol("Checksum trace is not bounded.");
            var reads = ReadRuns(row.GetProperty("programReadRuns"));
            var readCount = Int(row, "programReadCount", 0, 32769);
            if (reads.Length != readCount) throw Protocol("Program-read runs do not reproduce the reported read count.");
            var coverage = Coverage(reads);
            var reportedCoverage = row.GetProperty("coverageRanges").EnumerateArray().Select(pair =>
            {
                var values = pair.EnumerateArray().Select(value => value.GetInt32()).ToArray();
                if (values.Length != 2 || values[0] < 0 || values[1] > 32768 || values[0] >= values[1]) throw Protocol("Malformed coverage range.");
                return new ByteRange(values[0], values[1] - values[0]);
            }).ToArray();
            if (!reportedCoverage.SequenceEqual(coverage)) throw Protocol("Unique coverage differs from actual ordered reads.");
            var expectedDecision = model.ResidueMatches ? "ResidueZero" : image.Bytes.Span[P28NativeChecksumArithmetic.GateOffset] != 0 ? "NonzeroResidueBypassed" : "NonzeroResidueFailure";
            var expectedReads = Enumerable.Range(0, 32768).Concat(model.ResidueMatches ? [] : new[] { P28NativeChecksumArithmetic.GateOffset }).ToArray();
            var expectedExit = expectedDecision == "NonzeroResidueFailure" ? 0x24E9 : 0x2BB6;
            var checkpoints = row.GetProperty("checkpoints").EnumerateArray().ToArray();
            if (checkpoints.Length > 512) throw Protocol("Too many checksum checkpoints.");
            var statesMatch = true;
            var checkpointReads = new List<int>();
            var checkpointSteps = 0;
            for (var index = 0; index < checkpoints.Length; index++)
            {
                var measured = checkpoints[index];
                var expected = model.Checkpoints[index];
                var actualReads = ReadRuns(measured.GetProperty("programReadRuns"), 65);
                var expectedBlockReads = Enumerable.Range(index * 64, 64).Concat(index == 511 && !model.ResidueMatches ? new[] { P28NativeChecksumArithmetic.GateOffset } : []).ToArray();
                statesMatch &= Int(measured, "invocation", 1, 512) == expected.Invocation &&
                    Int(measured, "counterBefore", 0, 65535) == expected.CounterBefore && Int(measured, "counterAfter", 0, 65535) == expected.CounterAfter &&
                    Int(measured, "sumBefore", 0, 255) == expected.SumBefore && Int(measured, "sumAfter", 0, 255) == expected.SumAfter &&
                    Int(measured, "computedByte", 0, 255) == expected.ComputedByte &&
                    Int(measured, "exitPc", 0, 65535) == (index == 511 ? expectedExit : 0x2BB6) && actualReads.SequenceEqual(expectedBlockReads) &&
                    Int(measured, "programReadCount", 0, 65) == actualReads.Length;
                var measuredSteps = Int(measured, "steps", 1, 256);
                statesMatch &= measuredSteps == (index == 511 ? expectedDecision == "ResidueZero" ? 208 : expectedDecision == "NonzeroResidueBypassed" ? 211 : 213 : 205);
                checkpointSteps += measuredSteps;
                checkpointReads.AddRange(actualReads);
            }
            var coverageMatches = complete && reads.SequenceEqual(expectedReads);
            NativeChecksumExecutionStatus category;
            if (status == 1) category = NativeChecksumExecutionStatus.UnresolvedInstruction;
            else if (status == 2) category = NativeChecksumExecutionStatus.ExecutionError;
            else if (status == 3) category = NativeChecksumExecutionStatus.BudgetExceeded;
            else if (!complete) category = NativeChecksumExecutionStatus.Incomplete;
            else
            {
                var matched = invocations == 512 && checkpoints.Length == 512 && residue == model.ComputedResult &&
                    counter == 0 && accumulatedByte == 0 && stopPc == expectedExit && decision == expectedDecision &&
                    statusByte == (expectedDecision == "NonzeroResidueFailure" ? 0x48 : 0) &&
                    coverageMatches && statesMatch && checkpointSteps == steps && checkpointReads.SequenceEqual(reads);
                category = matched ? NativeChecksumExecutionStatus.Match : NativeChecksumExecutionStatus.Mismatch;
            }
            if (status != 0 && complete || !complete && residue != -1) throw Protocol("Incomplete checksum execution claimed a completed residue.");
            return new(pattern, category, complete, complete ? residue : null, decision, invocations, steps, stopPc,
                readCount, coverage, coverageMatches, complete && checkpoints.Length == 512 && statesMatch, assumptions, trace,
                category == NativeChecksumExecutionStatus.Match ? "Integer residue, decision, all 512 intermediate states and exact ordered coverage agree." :
                    row.TryGetProperty("error", out var error) && error.ValueKind == JsonValueKind.String ? error.GetString()! : "Execution is incomplete, unresolved or differs from the independent contract.");
        }
        catch (Exception exception) when (exception is JsonException or KeyNotFoundException or InvalidOperationException or FormatException or OverflowException)
        {
            throw Protocol("Malformed checksum case response.", exception);
        }
    }

    private static JsonElement[] ValidateEntryContract(JsonElement root)
    {
        var contracts = root.GetProperty("entryContracts").EnumerateArray().Select(item => item.Clone()).ToArray();
        if (contracts.Length != 1 || contracts[0].ValueKind != JsonValueKind.Object) throw Protocol("One checksum entry contract is required.");
        // Exact contract identity is checked in addition to protocol/runner version.
        var expected = new
        {
            id = "checksum",
            entryPc = 0x2B70,
            exitPcs = new[] { 0x2BB6, 0x24E9 },
            stop = "BeforeInstruction",
            allowedCodeRanges = new[] { new[] { 0x2B70, 0x2BB6 } },
            psw = 0x0100,
            lrb = 0x0041,
            usp = 0x0180,
            ssp = 0x047E,
            initialState = new { counterAddress = 0x396, counter = 0, sumAddress = 0x398, sum = 0, statusAddress = 0xF5, status = 0 },
            allowedDataRanges = new[] { new[] { 6, 8 }, [0x80, 0x88], [0xF5, 0xF6], [0x208, 0x20C], [0x396, 0x399] },
            allowedProgramDataReads = new[] { 0, 32768 },
            instructionBudgetPerInvocation = 256,
            maximumInvocations = 512,
            maximumTotalInstructions = 131072,
            bytesPerInvocation = 64,
            programReadOrder = "AscendingBytesWithinLittleEndianWords",
            readRuns = "StartAndLengthIncludingRepeats",
            controlReadAddress = 0x60FB,
            completion = "512 completed invocations, exact scan coverage and actual counter reset",
            statePreservedAcrossInvocations = true,
            reentry = "Only PC is staged to entry; no RAM or register reseeding",
            initialization = "Seeded snapshot grounded in startup clear, not executed reset",
            codeDataSpacesSeparate = true,
            interrupts = "NotInjected",
            peripherals = "Frozen",
            permittedAssumptions = Array.Empty<string>(),
        };
        if (!JsonNode.DeepEquals(JsonSerializer.SerializeToNode(expected, JsonDefaults.Create(false)), JsonNode.Parse(contracts[0].GetRawText())))
            throw Protocol("Unexpected checksum entry contract.");
        return contracts;
    }

    private static int Int(JsonElement row, string property, int minimum, int maximum)
    {
        var value = row.GetProperty(property).GetInt32();
        if (value < minimum || value > maximum) throw Protocol($"Checksum field {property} is outside the bounded contract.");
        return value;
    }

    private static int[] ReadRuns(JsonElement element, int maximum = 32769)
    {
        if (element.ValueKind != JsonValueKind.Array || element.GetArrayLength() > maximum) throw Protocol("Unbounded program-read runs.");
        var result = new List<int>();
        foreach (var pair in element.EnumerateArray())
        {
            var values = pair.EnumerateArray().Select(value => value.GetInt32()).ToArray();
            if (values.Length != 2 || values[0] < 0 || values[1] <= 0 || values[0] + (long)values[1] > 32768 || result.Count + (long)values[1] > maximum)
                throw Protocol("Malformed or excessive program-read run.");
            result.AddRange(Enumerable.Range(values[0], values[1]));
        }
        return result.ToArray();
    }

    private static ByteRange[] Coverage(IEnumerable<int> reads)
    {
        var sorted = reads.Distinct().Order().ToArray();
        var result = new List<ByteRange>();
        for (var index = 0; index < sorted.Length;)
        {
            var start = sorted[index++];
            var end = start + 1;
            while (index < sorted.Length && sorted[index] == end) { index++; end++; }
            result.Add(new(start, end - start));
        }
        return result.ToArray();
    }

    private static SliceProcessException Protocol(string message, Exception? inner = null) => new(SliceProcessFailure.Protocol, message, inner);
}
