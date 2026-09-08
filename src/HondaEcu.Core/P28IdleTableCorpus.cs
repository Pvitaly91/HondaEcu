namespace HondaEcu.Core;

internal static class P28IdleTableCorpus
{
    internal const string Id = "idle-table-abc-source-and-consumer-boundaries-v1";
    internal static P28IdleSelectorInputs Selectors(int flags) => new((flags & 1) != 0, (flags & 2) != 0, (flags & 4) != 0,
        (flags & 8) != 0, (flags & 16) != 0, (flags & 32) != 0, (flags & 64) != 0);
    internal static P28IdleContextsState Initial => new(4321, 1234, 765, 0xA0, 0x81, 0x81, 0x81, 0x81, 0x81, 0, 0, 0, 0, 0);
    internal static IReadOnlyList<(string Id, P28IdleContextsScenario Scenario)> Create(P28IdleTablePreview preview)
        => Create(preview.Original, preview.Output, preview.Plan.Tables);
    internal static IReadOnlyList<(string Id, P28IdleContextsScenario Scenario)> Create(RomImage original, RomImage output, IReadOnlyList<P28IdleTableGroup> tables)
    {
        var result = new List<(string, P28IdleContextsScenario)>();
        void Add(string id, P28IdleContextsState initial, IEnumerable<P28IdleContextsCall> calls)
        {
            // Each bounded chunk is explicitly a separate once-seeded sequence, never a hidden reseed within one sequence.
            var chunk = 0;
            foreach (var group in calls.Chunk(64))
            {
                var name = $"{id}/{chunk++}";
                result.Add((name, P28IdleContextsScenario.Create(initial, group.Select((c, i) => c with { Index = i }).ToArray(), Id + "/" + name)));
            }
        }
        foreach (var flags in new[] { 9, 8 })
        {
            var model = new P28IdleContextsModel(original, Initial);
            var calls = Enumerable.Range(0, 256).Select(x =>
            {
                var call = new P28IdleContextsCall(x, (byte)x, 0, Selectors(flags));
                // Old target is an explicit current-period stimulus, not a target RAM write.
                return call with { RawPeriod = (ushort)model.Step(call).FinalTarget };
            }).ToArray();
            Add(flags == 9 ? "base-retained-domain" : "late-domain", Initial, calls);
        }
        var points = tables.SelectMany(t => t.Cells).SelectMany(c => new[] { c.Axis - 1, c.Axis, c.Axis + 1 })
            .Concat(new[] { 0, 1, 21, 22, 23, 39, 40, 41, 45, 46, 47, 48, 49, 50, 51, 52, 53, 111, 120, 145, 254, 255 })
            .Where(x => x is >= 0 and <= 255).Distinct().Order().ToArray();
        foreach (var flags in new[] { 1, 5, 15, 25, 41, 73, 0, 4, 14, 24, 40, 72 })
            Add($"override-flags{flags}", Initial, points.Select(x => new P28IdleContextsCall(0, (byte)x, 1450, Selectors(flags))));
        foreach (var history in new[] { Initial with { Raw0274 = 3327 }, Initial with { Raw0274 = 3328 }, Initial with { Raw0274 = 32767 },
            Initial with { Raw0274 = 32768 }, Initial with { Raw0274 = 65535 }, Initial with { Raw027c = 1 }, Initial with { Raw027c = 65535 },
            Initial with { Counter02e5 = 1 }, Initial with { Counter02e5 = 255 }, Initial with { Counter02e8 = 1 }, Initial with { Counter02e8 = 255 },
            Initial with { Counter02e9 = 1 }, Initial with { Counter02e9 = 255 } })
        {
            var id = $"history-{history.Raw0274}-{history.Raw027c}-{history.Counter02e5}-{history.Counter02e8}-{history.Counter02e9}";
            Add(id, history, new[] { 21, 22, 39, 40, 45, 46, 47, 48, 49, 52 }.SelectMany(x => new[] { 1, 25 }.Select(f => new P28IdleContextsCall(0, (byte)x, 1450, Selectors(f)))));
        }
        // One persistent history across repeated inputs, native counter sets and masked selector changes.
        Add("masked-transitions", Initial, new[] { 9, 9, 8, 8, 41, 9, 25, 73, 9, 1, 5, 15, 25, 9, 8, 9 }
            .Select((f, i) => new P28IdleContextsCall(i, (byte)(i < 4 ? 135 : 40), (ushort)(i % 2 == 0 ? 1450 : 0), Selectors(f))));
        foreach (var flags in new[] { 9, 8, 1, 15, 25 })
        {
            var a = new P28IdleContextsModel(original, Initial); var c = new P28IdleContextsModel(output, Initial);
            var calls = new List<P28IdleContextsCall>();
            foreach (var x in points)
            {
                var seed = new P28IdleContextsCall(0, (byte)x, 0, Selectors(flags)); var old = a.Step(seed).FinalTarget; var value = c.Step(seed).FinalTarget;
                foreach (var current in new[] { old, value }.SelectMany(t => new[] { t - 769, t - 768, t - 767, t - 1, t, t + 1, t + 767, t + 768, t + 769 })
                    .Concat(new[] { 0, 65535 }).Where(n => n is >= 0 and <= 65535).Distinct().Order())
                    calls.Add(seed with { RawPeriod = (ushort)current });
            }
            Add($"consumer-edges-{flags}", Initial, calls);
        }
        return result.AsReadOnly();
    }
}
