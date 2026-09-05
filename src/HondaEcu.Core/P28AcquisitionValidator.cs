using System.Text.Json;

namespace HondaEcu.Core;

/// <summary>One bounded process request, independent expected histories, and per-observation comparison.</summary>
public static partial class P28AcquisitionValidator
{
    public const string Operation = "acquisitionSequence";
    public const string AcquisitionOnly = "acquisition-only";
    public const string ScheduledComposition = "scheduled-g-f-threshold";
    public const int MaximumObservations = 1024;
    private static readonly int[] ScratchPatterns = [0, 85, 170];

    /// <summary>Transport data only. This does not admit an original or a composed child.</summary>
    public static object CreateRequest(RomImage baseline, RomImage? derived, P28AcquisitionScenario scenario,
        string composition = AcquisitionOnly, IEnumerable<string>? assumptions = null)
    {
        ValidateScenario(scenario, composition);
        baseline.ValidateExactSize(32768);
        derived?.ValidateExactSize(32768);
        var allowed = P28ProducerValidator.ValidateAssumptions(assumptions ?? []);
        var images = new List<object> { new { id = "baseline", rom = baseline.ToArray().Select(value => (int)value).ToArray() } };
        if (derived is not null) images.Add(new { id = "derived", rom = derived.ToArray().Select(value => (int)value).ToArray() });
        return new
        {
            protocolVersion = SeededSliceProcess.ProtocolVersion,
            operation = Operation,
            images,
            allowAssumptions = allowed,
            scratchPatterns = ScratchPatterns.ToArray(),
            acquisitionSequence = new
            {
                formatVersion = 1,
                composition,
                initialState = P28AcquisitionModel.Snapshot(scenario.InitialState),
                observations = scenario.Observations,
                traceObservationIndexes = scenario.TraceObservationIndexes,
            },
        };
    }

    public static async Task<P28AcquisitionValidationReport> ExecuteAsync(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, bool confirmed,
        string runner, P28AcquisitionScenario scenario, string composition = AcquisitionOnly,
        IEnumerable<string>? assumptions = null, RomImage? derived = null, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default, P28VerifiedChecksumComposition? verifiedComposition = null)
    {
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, confirmed, derived, composition: verifiedComposition);
        var allowed = P28ProducerValidator.ValidateAssumptions(assumptions ?? []);
        var request = CreateRequest(baseline, derived, scenario, composition, allowed);
        var response = await SeededSliceProcess.ExchangeAsync(runner, request, options, cancellationToken).ConfigureAwait(false);
        var report = Analyze(baseline, profile, binding, scenario, response, composition, allowed, derived, verifiedComposition);
        var failure = report.Issues.FirstOrDefault(issue => issue.ObservationIndex >= 0);
        if (failure is null) return report;
        cancellationToken.ThrowIfCancellationRequested();
        var diagnostics = new List<JsonElement>();
        try
        {
            // A capture has history: replay the original initial state and whole prefix,
            // never initialize the model or runner from observed Rust intermediate RAM.
            var replayScenario = scenario.ForReplay(failure.ObservationIndex);
            var replayResponse = await SeededSliceProcess.ExchangeAsync(runner,
                CreateRequest(baseline, derived, replayScenario, composition, allowed), options, cancellationToken).ConfigureAwait(false);
            var replay = Analyze(baseline, profile, binding, replayScenario, replayResponse, composition, allowed, derived, verifiedComposition);
            var reproduced = SameReplayPrefix(report.Sequences, replay.Sequences, failure.ObservationIndex);
            diagnostics.Add(JsonSerializer.SerializeToElement(new
            {
                purpose = "Original initial state and observation-prefix replay; excluded from independent counts",
                lastObservationIndex = failure.ObservationIndex,
                replayConsistent = reproduced,
                witnesses = replay.Sequences.Select(sequence => new
                {
                    sequence.ImageIndex,
                    sequence.ScratchPattern,
                    checkpoint = sequence.Checkpoints[failure.ObservationIndex],
                }).ToArray(),
            }, JsonDefaults.Create(false)));
        }
        catch (Exception exception) when (exception is SliceProcessException or JsonException or InvalidDataException or InvalidOperationException)
        {
            diagnostics.Add(JsonSerializer.SerializeToElement(new
            {
                purpose = "Prefix replay did not complete; primary measured failure retained",
                lastObservationIndex = failure.ObservationIndex,
                replayConsistent = false,
                traceObtained = false,
                failure = exception is SliceProcessException process ? process.Failure.ToString() : "Protocol",
            }, JsonDefaults.Create(false)));
        }
        return report with { ReplayDiagnostics = Freeze(diagnostics) };
    }

    public static P28AcquisitionValidationReport Analyze(
        RomImage baseline, RomProfile profile, P28ExactBaselineBinding binding, P28AcquisitionScenario scenario,
        SliceProcessResponse response, string composition = AcquisitionOnly, IEnumerable<string>? assumptions = null,
        RomImage? derived = null, P28VerifiedChecksumComposition? verifiedComposition = null)
    {
        ValidateScenario(scenario, composition);
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, derived, composition: verifiedComposition);
        var allowed = P28ProducerValidator.ValidateAssumptions(assumptions ?? []);
        try
        {
            return AnalyzeCore(baseline, profile, binding, scenario, response, composition, allowed, derived, verifiedComposition);
        }
        catch (Exception exception) when (exception is JsonException or InvalidOperationException or KeyNotFoundException or
            FormatException or OverflowException or ArgumentOutOfRangeException)
        {
            throw Protocol("Malformed acquisition sequence response.", exception);
        }
    }

    private static void ValidateScenario(P28AcquisitionScenario scenario, string composition)
    {
        ArgumentNullException.ThrowIfNull(scenario);
        if (composition is not (AcquisitionOnly or ScheduledComposition))
            throw new ArgumentException("Choose acquisition-only or explicitly scheduled-g-f-threshold.", nameof(composition));
        _ = P28AcquisitionModel.Snapshot(scenario.InitialState);
        if (scenario.Observations.Count is < 1 or > MaximumObservations || scenario.TraceObservationIndexes.Count > 8 ||
            scenario.TraceObservationIndexes.Distinct().Count() != scenario.TraceObservationIndexes.Count ||
            scenario.TraceObservationIndexes.Any(index => index < 0 || index >= scenario.Observations.Count))
            throw new ArgumentException("Acquisition observations or selected trace indexes exceed the finite contract.");
        for (var index = 0; index < scenario.Observations.Count; index++)
        {
            P28AcquisitionModel.ValidateObservation(scenario.Observations[index]);
            if (scenario.Observations[index].Index != index) throw new ArgumentException("Observation indexes must be contiguous from zero.");
            if (composition == AcquisitionOnly && scenario.Observations[index].Compose)
                throw new ArgumentException("Per-observation composition requires the explicit scheduled composition mode.");
        }
    }

    private static SliceProcessException Protocol(string message, Exception? inner = null) =>
        new(SliceProcessFailure.Protocol, message, inner);

    private static IReadOnlyList<T> Freeze<T>(IEnumerable<T> values) => Array.AsReadOnly(values.ToArray());
}
