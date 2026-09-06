using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public static partial class P28AcquisitionValidator
{
    // Instruction boundaries and named contracts only, not OEM instruction bytes.
    internal static JsonElement ExpectedEntryContracts() => JsonSerializer.SerializeToElement(new object[]
    {
        new { id = "acquisition", entryPc = 0x56BE, exitPcs = new[] { 0x5719 }, stop = "BeforeInstruction",
            allowedCodeRanges = new[] { new[] { 0x56BE, 0x56DF }, new[] { 0x5701, 0x5719 } },
            psw = 0x1102, lrb = 0x21, usp = 0x280, ssp = 0x7FE, instructionBudget = 128,
            sspQualification = "TechnicalSeedUnusedBySliceNotRecoveredCallerStack", mode = "DATA011F.2ClearOnly",
            unsupportedMode = "RefuseBeforeFetch", peripheralReads = new[] { new[] { 0x3A, 16 }, new[] { 0x19, 8 }, new[] { 0x42, 8 } },
            peripheralWrites = Array.Empty<int>(), readEffects = "NondestructiveFrozenSnapshotNoNewEventNoInterrupt",
            programDataReads = Array.Empty<int>(), admission = "ExactInstructionForms",
            sampleAddresses = new[] { 0x360, 0x362, 0x364, 0x366, 0x368, 0x36A }, slotIndex = "ExplicitCallerInputDATA00A2",
            selectedTimestampAddress = 0x10E, independentData010FStimulus = false, stateReset = "OncePerImageAndScratchSequence",
            callEntryReset = new[] { "PC", "PSW", "LRB", "USP", "DATA00A2" }, sampleWriteJournal = "ActualArchitecturalStoresIncludingSameValue",
            instructionExtents = "AdmittedExecutedInstructionsOnly", interrupts = "NotInjected", timeAdvancement = "None" },
        new { id = "acquisitionToProducer", composition = "ScheduledSameCpuRam", entryPc = 0x0772, exitPcs = new[] { 0x07A5 },
            allowedCodeRanges = new[] { new[] { 0x0772, 0x07A5 }, new[] { 0x7AEC, 0x7AFE } }, psw = 0x1101, lrb = 0x40, usp = 0x180,
            instructionBudget = 192, callEntryReset = new[] { "PC", "PSW", "LRB", "USP" }, sampleAndHistoryReseeding = false,
            peripheralObservations = "Unavailable", allowedAssumptions = new[] { "oki.add-er1-a" }, interrupts = "NotInjected" },
        new { id = "sequenceProducerToCompact", composition = "ScheduledSameCpuRam", fromPc = 0x07A5, entryPc = 0x07C7,
            exitPcs = new[] { 0x0822 }, allowedCodeRanges = new[] { new[] { 0x07C7, 0x0822 } }, psw = 0x1101, lrb = 0x40, usp = 0x180,
            instructionBudget = 128, callEntryReset = new[] { "PC", "PSW", "LRB", "USP" }, skippedRange = new[] { 0x07A5, 0x07C7 },
            continuousWholeRoutine = false, inputs = "ActualGState", peripheralObservations = "Unavailable",
            allowedAssumptions = new[] { "oki.add-er3-a" } },
        new { id = "sequenceThreshold", composition = "ScheduledSameCpuRam", entryPc = 0x122C, exitPcs = new[] { 0x126D, 0x1281 },
            allowedCodeRanges = new[] { new[] { 0x122C, 0x126D } }, psw = 0x0101, lrb = 0x20, usp = 0x280, instructionBudget = 128,
            callEntryReset = new[] { "PC", "PSW", "LRB", "USP", "DATA011E.3/.4", "DATA0131.1/.2" },
            initialOnlyPreconditions = new Dictionary<string, int> { ["DATA00CC"] = 0, ["DATA0131bit0"] = 0 },
            laterThresholdCalls = "PreservePrefixSideEffectsAndUnrelatedBits",
            codeInput = "ActualFStateDATA0133", allowedProgramDataReads = new[] { 0x6542, 0x654A },
            allowedAssumptions = Array.Empty<string>(), peripheralObservations = "Unavailable",
            contextSchedule = "HarnessDeclaredNotMeasuredMainLoopOrHysteresis", assumptions = "CumulativeAcrossStagesAndObservations",
            failure = "AbortRemainingSequence" },
    });

    private static P28AcquisitionCheckpoint ParseCheckpoint(JsonElement element, int index, IReadOnlyList<string> allowed)
    {
        Shape(element, "observationIndex", "selectedTimestamp", "slotIndex", "acquisition", "g", "f", "threshold",
            "stateAfterComposition", "cumulativeAssumptions", "everWrittenMask", "slotWriteCounts");
        if (Int(element, "observationIndex", 0, 1023) != index) throw Protocol("Checkpoint indexes are not complete and ordered.");
        var acquisition = element.GetProperty("acquisition");
        Shape(acquisition, "status", "disposition", "steps", "stopPc", "peripheralAccesses", "sampleWrites", "stateAfter",
            "programReads", "usedAssumptions", "executedInstructionBytes", "trace", "error");
        var observed = new P28AcquisitionObservedStep(Int(acquisition, "status", 0, 4),
            acquisition.GetProperty("disposition").GetString() ?? throw Protocol("Missing acquisition disposition."),
            Int(acquisition, "steps", 0, 128), Int(acquisition, "stopPc", 0, 65535),
            Matrix(acquisition, "peripheralAccesses", 4, 128), Matrix(acquisition, "sampleWrites", 3, 128),
            ParseState(acquisition.GetProperty("stateAfter")), Integers(acquisition, "programReads", 0, 32767, 512),
            Assumptions(acquisition, "usedAssumptions", allowed), Extents(acquisition), Traces(acquisition), Error(acquisition));
        if (observed.UsedAssumptions.Count != 0) throw Protocol("Acquisition cannot consume either ADD permission.");
        return new(index, NullableInt(element, "selectedTimestamp", 65535) is int timestamp ? (ushort)timestamp : null,
            NullableInt(element, "slotIndex", 255), observed,
            ParseStage(element.GetProperty("g"), 192, 16, allowed, P28ProducerModel.AddEr1Assumption),
            ParseStage(element.GetProperty("f"), 128, 2, allowed, P28ByteExecutionValidator.AddAssumption),
            ParseStage(element.GetProperty("threshold"), 128, 1, allowed, null),
            ParseState(element.GetProperty("stateAfterComposition")), Assumptions(element, "cumulativeAssumptions", allowed),
            Int(element, "everWrittenMask", 0, 63), Integers(element, "slotWriteCounts", 0, 131072, 6, exact: true));
    }

    internal static P28AcquisitionStageResult? ParseStage(JsonElement element, int budget, int outputs,
        IReadOnlyList<string> allowed, string? permitted)
    {
        if (element.ValueKind == JsonValueKind.Null) return null;
        Shape(element, "status", "usedAssumptions", "steps", "stopPc", "outputs", "programReads", "trace", "error", "executedInstructionBytes");
        var used = Assumptions(element, "usedAssumptions", allowed);
        if (used.Any(value => value != permitted)) throw Protocol("Stage used an assumption belonging to another instruction.");
        return new(Int(element, "status", 0, 3), used, Int(element, "steps", 0, budget), Int(element, "stopPc", 0, 65535),
            Integers(element, "outputs", 0, 255, outputs, exact: true), Integers(element, "programReads", 0, 32767, 512),
            Extents(element), Traces(element), Error(element));
    }

    private static P28AcquisitionState ParseState(JsonElement element)
    {
        Shape(element, "previousTimestamp", "samples", "data0128", "data00AE", "data00B6", "data011F",
            "previousT", "data0217", "data0231", "data0136");
        return new((ushort)Int(element, "previousTimestamp", 0, 65535),
            Freeze(Integers(element, "samples", 0, 65535, 6, exact: true).Select(value => (ushort)value)),
            (byte)Int(element, "data0128", 0, 255), (byte)Int(element, "data00AE", 0, 255), (byte)Int(element, "data00B6", 0, 255),
            (byte)Int(element, "data011F", 0, 255), (ushort)Int(element, "previousT", 0, 65535),
            (byte)Int(element, "data0217", 0, 255), (byte)Int(element, "data0231", 0, 255), (ushort)Int(element, "data0136", 0, 65535));
    }

    private static void Shape(JsonElement element, params string[] fields)
    {
        if (element.ValueKind != JsonValueKind.Object) throw Protocol("Response object required.");
        var actual = element.EnumerateObject().Select(property => property.Name).ToArray();
        if (actual.Length != fields.Length || actual.Distinct(StringComparer.Ordinal).Count() != actual.Length ||
            !actual.Order(StringComparer.Ordinal).SequenceEqual(fields.Order(StringComparer.Ordinal)))
            throw Protocol("Response fields are missing, unknown or duplicated.");
    }

    private static int Int(JsonElement element, string name, int min, int max)
    {
        var result = element.GetProperty(name).GetInt32();
        if (result < min || result > max) throw Protocol("Response integer is outside the bounded contract.");
        return result;
    }
    private static int? NullableInt(JsonElement element, string name, int max) =>
        element.GetProperty(name).ValueKind == JsonValueKind.Null ? null : Int(element, name, 0, max);
    private static IReadOnlyList<int> Integers(JsonElement element, string name, int min, int max, int count, bool exact = false)
    {
        var array = element.GetProperty(name);
        if (array.GetArrayLength() > count || exact && array.GetArrayLength() != count) throw Protocol("Response array length differs from the bounded contract.");
        var values = array.EnumerateArray().Select(item => item.GetInt32()).ToArray();
        if (values.Any(value => value < min || value > max)) throw Protocol("Response array value is out of range.");
        return Freeze(values);
    }
    private static IReadOnlyList<int[]> Matrix(JsonElement element, string name, int width, int max)
    {
        var array = element.GetProperty(name);
        if (array.GetArrayLength() > max) throw Protocol("Access journal exceeds the instruction budget.");
        return Freeze(array.EnumerateArray().Select(row =>
        {
            if (row.GetArrayLength() != width) throw Protocol("Access journal row width is invalid.");
            var values = row.EnumerateArray().Select(item => item.GetInt32()).ToArray();
            if (values.Any(value => value < 0 || value > 65535)) throw Protocol("Access journal value is out of range.");
            return values;
        }));
    }
    private static IReadOnlyList<int> Extents(JsonElement element)
    {
        var values = Integers(element, "executedInstructionBytes", 0, 32767, 1024);
        if (!values.SequenceEqual(values.Distinct().Order())) throw Protocol("Executed instruction extents must be sorted and unique.");
        return values;
    }
    private static IReadOnlyList<string> Assumptions(JsonElement element, string name, IReadOnlyList<string> allowed)
    {
        var array = element.GetProperty(name);
        if (array.GetArrayLength() > 2) throw Protocol("Assumption list exceeds the reviewed set.");
        var values = array.EnumerateArray().Select(item => item.GetString() ?? throw Protocol("Null assumption.")).ToArray();
        if (values.Distinct(StringComparer.Ordinal).Count() != values.Length || values.Any(value => !allowed.Contains(value)))
            throw Protocol("Unpermitted or duplicate assumption reported.");
        return Freeze(values);
    }
    private static IReadOnlyList<JsonElement> Traces(JsonElement element)
    {
        var array = element.GetProperty("trace");
        if (array.GetArrayLength() > 128) throw Protocol("Trace exceeds its independent witness budget.");
        foreach (var row in array.EnumerateArray())
        {
            Shape(row, "pc", "nextPc", "instruction", "psw", "accumulator");
            foreach (var name in new[] { "pc", "nextPc", "psw", "accumulator" }) _ = Int(row, name, 0, 65535);
            if (row.GetProperty("instruction").GetString() is not string instruction || instruction.Length > 256)
                throw Protocol("Invalid bounded trace instruction.");
        }
        return Freeze(array.EnumerateArray().Select(item => item.Clone()));
    }
    private static string? Error(JsonElement element)
    {
        var value = element.GetProperty("error");
        if (value.ValueKind == JsonValueKind.Null) return null;
        var text = value.GetString() ?? throw Protocol("Invalid error.");
        if (text.Length > 2048) throw Protocol("Error text exceeds bound.");
        return text;
    }
    private static bool JsonEqual<T>(T first, T second) => JsonNode.DeepEquals(JsonSerializer.SerializeToNode(first, JsonDefaults.Create(false)),
        JsonSerializer.SerializeToNode(second, JsonDefaults.Create(false)));
}
