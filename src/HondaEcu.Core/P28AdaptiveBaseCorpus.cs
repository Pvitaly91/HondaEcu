namespace HondaEcu.Core;

internal static class P28AdaptiveBaseCorpus
{
    internal const string Id = "single-bank-base-producer-limiter-abc-v1";
    internal static IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> Create(P28AdaptiveBasePlan p) => Create(p.Words, p.RequestedPair.Bank);
    internal static IReadOnlyList<(string Id, P28AdaptiveScenario Scenario)> Create(IReadOnlyList<P28AdaptiveBaseWord> words, int selectedBank)
    {
        var scenarios = new List<(string, P28AdaptiveScenario)>();
        var edges = words.SelectMany(w => new[] { w.OldWord, w.NewWord }).SelectMany(w => new[] { w - 1, w, w + 1 }).Where(x => x is >= 0 and <= 65535).Distinct().Order().ToArray();
        var rawEdges = new SortedSet<int> { 0, 65535 };
        foreach (var w in words)
        {
            foreach (var x in new[] { w.Origin - 1, w.Origin, w.Origin + 1 }) if (x is >= 0 and <= 65535) rawEdges.Add(x);
            if (w.Coefficient != 0)
                foreach (var high in new[] { 1, 2 })
                {
                    var edge = w.Origin + (int)(((long)high * 65536 + w.Coefficient - 1) / w.Coefficient);
                    foreach (var x in new[] { edge - 1, edge, edge + 1 }) if (x is >= 0 and <= 65535) rawEdges.Add(x);
                }
        }
        P28AdaptiveState Initial(byte prior, byte inhibit, int cut = 300, int resume = 310, byte timer = 0, byte counter = 0) =>
            new(new(prior, 128, inhibit, 255, 7, (ushort)cut, (ushort)resume), timer, counter, 65535, 43690);
        void Add(string id, P28AdaptiveState initial, IEnumerable<P28AdaptiveCall> calls)
        {
            var dense = calls.Select((c, i) => c with { Limiter = c.Limiter with { Index = i } }).ToArray();
            scenarios.Add((id, P28AdaptiveScenario.Create(initial, dense, Id + "/" + id)));
        }
        P28AdaptiveCall Call(int bank, int raw = 300, int x = 65535, byte ticks = 20) =>
            new(new(0, (ushort)raw, false, false, 254), (ushort)x, bank == 1, false, false, false, true, 0, ticks, 0);
        foreach (var bank in new[] { selectedBank, 1 - selectedBank })
            foreach (var prior in new byte[] { 0, 32 })
                foreach (var inhibit in new byte[] { 0, 128 })
                {
                    var prefix = bank == selectedBank ? "edited" : "untouched";
                    foreach (var context in new[] { "ram", "fixed-p4", "fixed-011b" })
                    {
                        // Reset before each crossing is a native producer operation, never host RAM reseeding.
                        var calls = edges.Reverse().Concat(edges).Select((raw, i) =>
                        {
                            var c = Call(bank, raw, ticks: 0) with { Reset217 = i % 2 == 0, Reset214 = true };
                            return c with { Limiter = c.Limiter with { P4Bit0 = context == "fixed-p4", Snapshot011bBit7 = context == "fixed-011b" } };
                        }).ToList();
                        calls.Add(Call(bank, ticks: 0)); // hold even though bases are read
                        calls.Add(Call(bank, ticks: 20) with { CounterTicks = 12 }); // actual hold expiry/update
                        calls.Add(Call(bank, x: 0)); // target decrease
                        calls.Add(Call(bank) with { Enable223 = false });
                        calls.Add(Call(bank, ticks: 0));
                        // Keep fixed-only controls genuinely fixed during subsequent producer paths too.
                        calls = calls.Select(c => c with { Limiter = c.Limiter with { P4Bit0 = context == "fixed-p4", Snapshot011bBit7 = context == "fixed-011b" } }).ToList();
                        Add($"{prefix}-{context}-prior{prior}-inhibit{inhibit}", Initial(prior, inhibit, timer: 20), calls);
                    }
                    var history = new[] {
                        Call(bank, ticks: 0) with { Reset217 = true, Reset214 = true },
                        Call(1-bank, ticks: 0), Call(1-bank) with { CounterTicks = 12 },
                        Call(bank), Call(bank) with { RawD9 = 68 }, Call(bank) with { Mode212 = true, CounterTicks = 12 },
                        Call(bank) with { Mode212 = true, Enable223 = false }, Call(bank, ticks: 0),
                        Call(bank) with { CounterTicks = 12 }, Call(bank, x: 0),
                        Call(1-bank) with { Reset214 = true }, Call(bank),
                    };
                    history[2] = history[2] with { Limiter = history[2].Limiter with { P4Bit0 = true } };
                    history[3] = history[3] with { Limiter = history[3].Limiter with { Snapshot011bBit7 = true } };
                    Add($"switch-from{bank}-prior{prior}-inhibit{inhibit}", Initial(prior, inhibit, timer: 20), history);
                    // Target crossings after a real adaptive update (not reset or injected RAM).
                    // Plan arithmetic determines external test inputs only; M1m independently
                    // models every image and the runner must perform every LC/store itself.
                    var targets = words.SelectMany(w => new[] { w.OldWord, w.NewWord }
                        .Select(b => b + (int)((long)(65535 - w.Origin) * w.Coefficient / 65536)))
                        .SelectMany(t => new[] { t - 1, t, t + 1 }).Where(t => t is >= 0 and <= 65535).Distinct().Order().ToArray();
                    Add($"target-crossings-bank{bank}-prior{prior}-inhibit{inhibit}", Initial(prior, inhibit, 65535, 65535),
                        targets.Reverse().Concat(targets).Select(raw => Call(bank, raw)));
                }
        foreach (var bank in new[] { 0, 1 })
        {
            var previous = words.SelectMany(w => new[] { w.OldWord, w.NewWord }).SelectMany(w => new[] { w + 36, w + 37, w + 38 })
                .Concat(new[] { 0, 36, 37, 65511, 65512, 65535 }).Where(x => x is >= 0 and <= 65535).Distinct();
            foreach (var old in previous)
                Add($"decrease-bank{bank}-previous{old}", Initial(0, 0, old, old, counter: 1),
                    new[] { Call(bank, ticks: 0), Call(bank, ticks: 0), Call(bank) });
            foreach (var old in new[] { 0, 65511, 65512, 65535 })
                Add($"adaptive-bank{bank}-previous{old}", Initial(32, 128, old, old),
                    rawEdges.Concat(rawEdges.Reverse()).Select(x => Call(bank, x: x)));
        }
        return scenarios.AsReadOnly();
    }
}
