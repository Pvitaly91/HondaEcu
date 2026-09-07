namespace HondaEcu.Core;

internal static class P28CombinedLimiterCorpus
{
    internal const string Id = "combined-limiter-groups-native-histories-v1";
    internal static IReadOnlyList<(string Id, P28LimiterScenario Scenario)> Fixed(P28CombinedLimiterPlan p) => Create(p)
        .Where(s => s.Id.StartsWith("fixed-inputs", StringComparison.Ordinal)).Select(s => (s.Id,
            P28LimiterScenario.Create(s.Scenario.InitialState.Limiter, s.Scenario.Calls.Select(c => c.Limiter).ToArray(), Id + "/fixed-task/" + s.Id))).ToArray();
    internal static IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> Create(P28CombinedLimiterPlan p)
    {
        var result = new List<(string, P28AdaptiveScenario)>();
        // Reuse both per-bank boundary/path generators, not old plans or child exports.
        for (var bank = 0; bank < 2; bank++)
            foreach (var item in P28AdaptiveBaseCorpus.Create(p.Groups[bank + 1].AdaptiveWords, bank))
            {
                var id = $"bases{bank}/{item.Id}";
                result.Add((id, P28AdaptiveScenario.Create(item.Scenario.InitialState, item.Scenario.Calls, Id + "/" + id)));
            }
        var edges = p.Groups[0].FixedOperands.SelectMany(w => new[] { w.OriginalWord, w.NewWord })
            .SelectMany(w => new[] { w - 1, w, w + 1 }).Where(w => w is >= 0 and <= 65535).Distinct().Order().ToArray();
        foreach (var prior in new byte[] { 0, 32 })
            foreach (var inhibit in new byte[] { 0, 128 })
            {
                var initial = new P28AdaptiveState(new(prior, 128, inhibit, 255, 7, 300, 310), 20, 0, 65535, 43690);
                void Add(string id, IEnumerable<P28AdaptiveCall> calls) => result.Add((id, P28AdaptiveScenario.Create(initial,
                    calls.Select((c, i) => c with { Limiter = c.Limiter with { Index = i } }).ToArray(), Id + "/" + id)));
                P28AdaptiveCall Call(int raw, int context, int bank, bool reset = false) => new(
                    new(0, (ushort)raw, context is 1 or 3, context is 2 or 3, 254), 65535, bank == 1,
                    false, reset, false, true, 0, 0, 0);
                foreach (var context in new[] { 1, 2, 3 })
                    Add($"fixed-inputs{context}-prior{prior}-inhibit{inhibit}", edges.Reverse().Concat(edges).SelectMany(raw => new[] { Call(raw, context, 0), Call(raw, context, 0) }));
                foreach (var reverse in new[] { false, true })
                {
                    // Only the FIRST native producer resets. Bank switches hold and inherit
                    // thresholds/request/counters/masks, then native expiry/decrease/reset evolve them.
                    var banks = reverse ? new[] { 1, 1, 0, 0 } : new[] { 0, 0, 1, 1 };
                    var raw = p.Groups[1].AdaptiveWords[0].NewWord;
                    var calls = new List<P28AdaptiveCall>();
                    for (var round = 0; round < 3; round++)
                        for (var i = 0; i < 4; i++)
                        {
                            var c = Call(i is 0 or 3 ? edges[edges.Length / 2] : raw, i is 0 or 3 ? 3 : 0, banks[i], calls.Count == 0);
                            if (round == 1) c = c with { TimerTicks = 20, CounterTicks = 12 };
                            if (round == 2) c = c with { TimerTicks = 20, Enable223 = false };
                            calls.Add(c);
                        }
                    Add($"cross-context-reverse{reverse}-prior{prior}-inhibit{inhibit}", calls);
                }
            }
        return result.AsReadOnly();
    }
}
