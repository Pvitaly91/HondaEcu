using static HondaEcu.Core.P28FixedLimiterExecution;
using static HondaEcu.Core.P28IdleTableExecution;

namespace HondaEcu.Core;

internal static class P28IdleExportBatch
{
    internal static async Task<IReadOnlyList<P28IdleTableRun>> RunAsync((string Id, RomImage Image)[] images,
        IReadOnlyList<(string Id, P28IdleContextsScenario Scenario)> scenarios, string runner,
        Func<RomImage, P28IdleContextsScenario, SliceProcessResponse, string, P28IdleContextsImageReport> analyze,
        Action<SliceProcessResponse, string> identity, SliceProcessOptions? options, CancellationToken cancellationToken)
    {
        var runs = new List<P28IdleTableRun>();
        foreach (var item in scenarios)
            foreach (var image in images)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var response = await SeededSliceProcess.ExchangeAsync(runner, P28IdleContextsValidator.CreateRequest(image.Image, item.Scenario), options, cancellationToken).ConfigureAwait(false);
                identity(response, P28IdleContextsValidator.Operation);
                var report = analyze(image.Image, item.Scenario, response, image.Id);
                foreach (var s in report.Sequences)
                {
                    if (s.Checkpoints.Any(c => c.Disposition != "StrictMatch")) throw new InvalidDataException($"Mandatory idle batch not strict: {item.Id}/{image.Id}.");
                    var steps = s.Checkpoints.Select(c => c.Expected!).ToArray();
                    runs.Add(new(image.Id, image.Image.Hash, item.Id, item.Scenario.Digest, s.ScratchPattern, item.Scenario.Calls.Count, s.Checkpoints.Count,
                        Digest(s.Checkpoints.Select(c => c.Actual).ToArray()), Digest(steps), Controls(steps), s.Checkpoints.Select(c => Outcome(c.Inputs, c.Expected!)).ToArray()));
                }
            }
        return runs.AsReadOnly();
    }
    internal static void RequireRuns((string Id, RomImage Image)[] images, IReadOnlyList<(string Id, P28IdleContextsScenario Scenario)> scenarios,
        IReadOnlyList<P28IdleTableRun> runs)
    {
        if (runs.Count != scenarios.Count * 9) throw new InvalidDataException("Missing/extra mandatory idle runs.");
        foreach (var item in scenarios)
            foreach (var image in images)
            {
                var model = new P28IdleContextsModel(image.Image, item.Scenario.InitialState);
                var steps = item.Scenario.Calls.Select(model.Step).ToArray();
                var expected = item.Scenario.Calls.Zip(steps).Select(pair => Outcome(pair.First, pair.Second)).ToArray();
                foreach (var pattern in new[] { 0, 85, 170 })
                {
                    var found = runs.Where(r => r.ScenarioId == item.Id && r.ImageKind == image.Id && r.ScratchPattern == pattern).ToArray();
                    if (found.Length != 1) throw new InvalidDataException("Missing/duplicate idle evidence identity.");
                    var r = found[0];
                    if (r.ImageHash != image.Image.Hash || r.ScenarioDigest != item.Scenario.Digest || r.Requested != expected.Length || r.StrictMatches != r.Requested ||
                        r.ObservationDigest.Length != 64 || !r.ObservationDigest.All(Uri.IsHexDigit) || r.ModelDigest != Digest(steps) || r.IndependentControlDigest != Controls(steps) ||
                        !P28LimiterValidator.Equal(r.Outcomes, expected)) throw new InvalidDataException("Forged/stale/incomplete idle history.");
                }
            }
    }
}
