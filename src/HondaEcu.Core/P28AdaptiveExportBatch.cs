using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

// Shared strict process/receipt plumbing; callers own admission, corpus and semantic relations.
internal static class P28AdaptiveExportBatch
{
    internal static async Task<IReadOnlyList<P28AdaptiveBaseRun>> RunAsync((string Id, RomImage Image)[] images,
        IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> scenarios, string runner,
        Func<RomImage, P28AdaptiveScenario, SliceProcessResponse, P28AdaptiveValidationReport> analyze,
        Action<SliceProcessResponse, string> identity, bool requireOperandFetch,
        SliceProcessOptions? options, CancellationToken cancellationToken)
    {
        var runs = new List<P28AdaptiveBaseRun>();
        foreach (var item in scenarios)
            foreach (var image in images)
            {
                var response = await SeededSliceProcess.ExchangeAsync(runner, P28AdaptiveValidator.CreateRequest(image.Image, item.Scenario), options, cancellationToken).ConfigureAwait(false);
                identity(response, P28AdaptiveValidator.Operation);
                var report = analyze(image.Image, item.Scenario, response);
                if (report.HasFailure) throw new InvalidDataException($"Mandatory adaptive batch did not strictly complete: {item.Id}/{image.Id}.");
                foreach (var s in report.Sequences)
                {
                    // M1m validates actual LC addresses/values, state, ordered writes, tick effects,
                    // branches, exits, stack and critical section against each image's own model.
                    // Its exact code/data ranges exclude the compensation byte; no permissions added.
                    if (requireOperandFetch)
                        foreach (var row in s.Checkpoints)
                        {
                            var decision = P28AcquisitionValidator.ParseStage(row.Actual.GetProperty("limiter").GetProperty("decision"), 96, 0, [], null)!;
                            if (!P28FixedLimiterEditor.Footprint.All(decision.ExecutedInstructionBytes.Contains))
                                throw new InvalidDataException("Incomplete actual fixed operand fetch.");
                        }
                    var outcomes = s.Checkpoints.Select(r => P28AdaptiveBaseExecution.Outcome(r.Inputs, r.Expected!)).ToArray();
                    runs.Add(new(image.Id, image.Image.Hash, item.Id, item.Scenario.Digest, s.ScratchPattern,
                        s.Counts.RequestedCalls, s.Counts.StrictMatches, Digest(s.Checkpoints.Select(c => c.Actual).ToArray()), outcomes));
                }
            }
        return runs.AsReadOnly();
    }
    internal static void RequireRuns((string Id, RomImage Image)[] images,
        IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> scenarios, IReadOnlyList<P28AdaptiveBaseRun> runs)
    {
        if (runs.Count != scenarios.Count * 9) throw new InvalidDataException("Missing/extra mandatory adaptive runs.");
        foreach (var scenario in scenarios)
            foreach (var image in images)
                foreach (var pattern in new[] { 0, 85, 170 })
                {
                    var found = runs.Where(r => r.ScenarioId == scenario.Id && r.ImageKind == image.Id && r.ScratchPattern == pattern).ToArray();
                    if (found.Length != 1) throw new InvalidDataException("Duplicate/missing adaptive evidence identity.");
                    var r = found[0];
                    if (r.ImageHash != image.Image.Hash || r.ScenarioDigest != scenario.Scenario.Digest || r.Requested != scenario.Scenario.Calls.Count ||
                        r.StrictMatches != r.Requested || r.Outcomes.Count != r.Requested || r.ObservationDigest.Length != 64 || !r.ObservationDigest.All(Uri.IsHexDigit))
                        throw new InvalidDataException("Invalid adaptive execution accounting.");
                    var model = new P28AdaptiveModel(image.Image.Span, scenario.Scenario.InitialState);
                    var expected = scenario.Scenario.Calls.Select(call => P28AdaptiveBaseExecution.Outcome(call, model.Step(call))).ToArray();
                    if (!P28LimiterValidator.Equal(r.Outcomes, expected)) throw new InvalidDataException("Receipt history disagrees with independently rederived state machine.");
                }
    }
}
