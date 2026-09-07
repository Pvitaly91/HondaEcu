using static HondaEcu.Core.P28FixedLimiterExecution;

namespace HondaEcu.Core;

internal static class P28FixedExportBatch
{
    internal static async Task<IReadOnlyList<P28FixedLimiterRun>> RunAsync((string Id, RomImage Image)[] images,
        IReadOnlyList<(string Id, P28LimiterScenario Scenario)> scenarios, string runner, int compensationOffset,
        Func<RomImage, P28LimiterScenario, SliceProcessResponse, P28LimiterValidationReport> analyze,
        Action<SliceProcessResponse, string> identity, SliceProcessOptions? options, CancellationToken cancellationToken)
    {
        var limiter = new List<P28FixedLimiterRun>();
        foreach (var item in scenarios)
            foreach (var image in images)
            {
                var response = await SeededSliceProcess.ExchangeAsync(runner, P28LimiterValidator.CreateRequest(image.Image, item.Scenario), options, cancellationToken).ConfigureAwait(false);
                identity(response, P28LimiterValidator.Operation);
                var report = analyze(image.Image, item.Scenario, response);
                if (report.HasFailure) throw new InvalidDataException("Mandatory limiter execution did not strictly complete.");
                foreach (var s in report.Sequences)
                {
                    var outcomes = new List<P28FixedLimiterOutcome>();
                    foreach (var row in s.Checkpoints)
                    {
                        var decision = P28AcquisitionValidator.ParseStage(row.Actual.GetProperty("decision"), 96, 0, [], null)!;
                        if (!P28FixedLimiterEditor.Footprint.All(decision.ExecutedInstructionBytes.Contains) || decision.ProgramReads.Contains(compensationOffset))
                            throw new InvalidDataException("Actual immediate fetch is incomplete or compensation was read.");
                        var expected = row.Expected!;
                        outcomes.Add(new(row.Index, item.Scenario.Calls[row.Index].RawPeriod, expected.Context, expected.Threshold,
                            row.Actual.GetProperty("overspeedRequest").GetBoolean(), (expected.Before.Data012A & 128) != 0,
                            row.Actual.GetProperty("inhibitBranch").GetBoolean(), expected.After.Data018F, expected.After.Data0124, expected.After.RamCut, expected.After.RamResume));
                    }
                    limiter.Add(new(image.Id, image.Image.Hash, item.Id, item.Scenario.Digest, s.ScratchPattern,
                        s.Counts.RequestedCalls, s.Counts.StrictMatches, Digest(s.Checkpoints.Select(c => c.Actual).ToArray()),
                        Digest(s.Checkpoints.Select(c => c.Actual.GetProperty("stateAfter")).ToArray()), true, true, outcomes.AsReadOnly()));
                }
            }
        return limiter.AsReadOnly();
    }
    internal static void RequireRuns((string Id, RomImage Image)[] images,
        IReadOnlyList<(string Id, P28LimiterScenario Scenario)> scenarios, IReadOnlyList<P28FixedLimiterRun> runs)
    {
        if (runs.Count != scenarios.Count * 9) throw new InvalidDataException("Incomplete fixed task corpus.");
        foreach (var scenario in scenarios) foreach (var image in images) foreach (var pattern in new[] { 0, 85, 170 })
                {
                    var found = runs.Where(r => r.ScenarioId == scenario.Id && r.ImageKind == image.Id && r.ScratchPattern == pattern).ToArray();
                    if (found.Length != 1) throw new InvalidDataException("Missing/duplicate fixed task identity.");
                    var r = found[0]; var count = scenario.Scenario.Calls.Count;
                    if (r.ImageHash != image.Image.Hash || r.ScenarioDigest != scenario.Scenario.Digest || r.Requested != count ||
                        r.StrictMatches != count || r.Outcomes.Count != count || !r.OperandFetchVerified || !r.CompensationNotRead ||
                        r.ObservationDigest.Length != 64 || !r.ObservationDigest.All(Uri.IsHexDigit)) throw new InvalidDataException("Invalid fixed task accounting.");
                    var model = new P28LimiterModel(image.Image.Span, scenario.Scenario.InitialState); var states = new List<P28LimiterState>();
                    var expected = scenario.Scenario.Calls.Select(call =>
                    {
                        var s = model.Step(call); states.Add(s.After);
                        return new P28FixedLimiterOutcome(call.Index, call.RawPeriod, s.Context, s.Threshold, s.OverspeedRequest,
                            (s.Before.Data012A & 128) != 0, s.InhibitBranch, s.After.Data018F, s.After.Data0124, s.After.RamCut, s.After.RamResume);
                    }).ToArray();
                    if (!P28LimiterValidator.Equal(expected, r.Outcomes) || r.PersistentStateDigest != Digest(states)) throw new InvalidDataException("Fixed task historical states disagree.");
                }
        ValidateRelations(runs, []);
    }
}
