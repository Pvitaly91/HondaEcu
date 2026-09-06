using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28ChainModelTests
{
    internal static P28ChainState Initial() => new(new(0, new ushort[6], 0, 0, 0xA0, 0xA0, 0x1357, 0x20, 0xA0, 0xBEEF),
        P28StatefulModelTests.Initial(), 0xA1, 0xA5, 0x5A, new(30, 0, 2, 0, 0, 255, 0));
    internal static P28ChainEvent Event(int i = 0) => new(i, (ushort)(1000 + 324 * i), 0, 0, (i + 5) % 6, i >= 6,
        0, true, Initial().Raw, 0, 0);
    internal static P28ChainScenario Scenario() => P28ChainScenario.Create(Initial(), Enumerable.Range(0, 9).Select(Event).ToArray(),
        "Invented initial inputs and table-only model test; not actual ROM execution");

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void OwnHistoryWarmupProducesCodeAndRetainsPriorLatchAndCounters(int prior)
    {
        var initial = Initial() with { Decision = P28StatefulModelTests.Initial(prior) };
        var model = new P28ChainModel(P28StatefulModelTests.Data(), initial, P28ChainValidator.Permissions);
        P28ChainExpectedEvent? previous = null;
        for (var i = 0; i < 9; i++)
        {
            var e = model.Step(Event(i));
            Assert.True(P28ChainValidator.Equal(previous?.After ?? initial, e.Before));
            Assert.Equal(initial.Decision, e.Stages[0].After.Decision);
            Assert.Equal(0xA0, e.After.Acquisition.Data011F); Assert.Equal(0xA1, e.After.Data011E & ~24);
            if (i == 0) { Assert.All(e.After.Acquisition.Samples, s => Assert.Equal(0, s)); Assert.Equal(0xBEEF, e.After.Acquisition.Data0136); }
            else Assert.Equal(324, e.Stages[0].After.Acquisition.Samples[(i + 5) % 6]);
            if (i >= 6)
            {
                Assert.Equal(388, e.Stages[2].After.Acquisition.PreviousT); Assert.Equal(205, e.Stages[3].After.Code);
                Assert.Equal(205, e.Stages[4].Before.Code); Assert.Equal(255, e.Stages[3].After.Raw.Raw0132);
                Assert.Contains(e.Stages[3].PersistentWrites, w => w.SequenceEqual(new[] { 0x133, 8, 205 }));
                Assert.DoesNotContain(e.CallerWrites, w => w[0] == 0x133 || w[0] == 0xC4 || w[0] == 0x131 || w[0] == 0x22);
                Assert.Equal(e.Before.Decision.Data0131, e.Stages[4].Before.Decision.Data0131);
                Assert.Equal(e.Stages[4].After.Decision, model.State.Decision);
            }
            initial = initial with { Decision = e.After.Decision }; previous = e;
        }
    }

    [Theory]
    [InlineData(0, "G", 0x077E)]
    [InlineData(1, "F", 0x07F8)]
    [InlineData(2, "Decision", 0x12B4)]
    [InlineData(3, "", 0)]
    public void SeparatePermissionsStopAtFirstReachedFormAndTaintLaterEvents(int count, string id, int pc)
    {
        var model = new P28ChainModel(P28StatefulModelTests.Data(), Initial(), P28ChainValidator.Permissions.Take(count));
        P28ChainExpectedEvent e = null!;
        for (var i = 0; i <= 6; i++) e = model.Step(Event(i));
        if (count < 3)
        {
            var stopped = Assert.Single(e.Stages.Where(s => s.Status == 1)); Assert.Equal(id, stopped.Id); Assert.Equal(pc, stopped.StopPc);
            var next = model.Step(Event(7) with { Raw = Initial().Raw with { Raw00CC = 99 } });
            Assert.All(next.Stages, s => Assert.Equal(4, s.Status)); Assert.Null(next.SoftwareRequest);
            Assert.Empty(next.CallerWrites); Assert.True(P28ChainValidator.Equal(e.After, next.After));
        }
        else
        {
            Assert.NotNull(e.SoftwareRequest); var next = model.Step(Event(7) with { RunDecision = false });
            Assert.Equal(3, next.Stages[0].CumulativeAssumptions.Count); Assert.Empty(next.Stages[0].UsedAssumptions);
        }
        Assert.Equal(count, e.Stages[^1].CumulativeAssumptions.Count);
    }

    [Fact]
    public void NativeCounterModelRunsEvenOnCaptureOnlyScheduleAndSaturatesWithoutReseeding()
    {
        var state = Initial() with { Decision = new(0xA6, 0x86, 77, 2, 1, 3, 254, 0xA5) };
        var model = new P28ChainModel(P28StatefulModelTests.Data(), state, []);
        var e = model.Step(Event() with { FastTicks = 1, SlowTicks = 2 });
        Assert.Equal(state.Decision with { Data01D8 = 1, Data01D9 = 0, Data01DF = 1, Data00F3 = 255 }, e.After.Decision);
        Assert.Equal(5, e.Stages[1].PersistentWrites.Count); // F3 reaches 255 on the first body; second body performs no store.
        var next = model.Step(Event(1) with { FastTicks = 32, SlowTicks = 32 });
        Assert.Equal(state.Decision with { Data01D8 = 0, Data01D9 = 0, Data01DF = 0, Data00F3 = 255 }, next.After.Decision);
        Assert.Equal(2, next.Stages[1].PersistentWrites.Count); Assert.Null(next.SoftwareRequest);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void AlternateGSlotStoresAndOverlappingFieldsHaveIndependentSideEffects(bool allowed)
    {
        var state = Initial() with { Acquisition = Initial().Acquisition with { Data0217 = 0xB0, Samples = new ushort[] { 101, 102, 103, 104, 105, 106 } } };
        var model = new P28ChainModel(P28StatefulModelTests.Data(), state, allowed ? P28ChainValidator.Permissions : []);
        var result = model.Step(Event() with { RunDecision = true, Raw = state.Raw with { Snapshot011A = 0xABCD, Raw0132 = 0x73 } });
        var g = result.Stages[2];
        Assert.Equal(allowed ? 6 : 1, g.PersistentWrites.Count(w => w[0] >= 0x360));
        Assert.All(g.After.Acquisition.Samples.Take(allowed ? 6 : 1), s => Assert.Equal(1, s));
        Assert.Equal(0xA0, result.After.Acquisition.Data011F); Assert.Equal(0xABCD, result.After.Raw.Snapshot011A);
        Assert.Equal(0x73, result.After.Raw.Raw0132); Assert.Equal(allowed ? 0 : 1, g.Status);
    }

    [Fact]
    public void ScenarioIsClosedBoundedAndFrozenAndReplayStartsAtOriginalInitialState()
    {
        var samples = new ushort[6]; var s = P28ChainScenario.Create(Initial() with { Acquisition = Initial().Acquisition with { Samples = samples } }, [Event()], "fixture");
        samples[0] = 17; Assert.Equal(0, s.InitialState.Acquisition.Samples[0]);
        Assert.Equal(s.Digest, P28ChainScenario.Parse(s.ToJson()).Digest);
        foreach (var field in new[] { "compactCode", "code", "samples", "T", "thresholdPriorBits", "p1OutputData" })
        {
            var node = JsonNode.Parse(s.ToJson())!; node["events"]![0]![field] = 0;
            Assert.ThrowsAny<Exception>(() => P28ChainScenario.Parse(node.ToJsonString()));
        }
        foreach (var e in new[] { Event() with { Slot = 6 }, Event() with { Context = 2 }, Event() with { FastTicks = 33 }, Event() with { Index = 1 }, Event() with { Raw = null! } })
            Assert.Throws<ArgumentException>(() => P28ChainScenario.Create(Initial(), [e], "fixture"));
        Assert.Throws<ArgumentException>(() => P28ChainScenario.Create(Initial(), [], "fixture"));
        Assert.Throws<ArgumentException>(() => P28ChainScenario.Create(Initial(), Enumerable.Range(0, 257).Select(Event).ToArray(), "fixture"));
        Assert.Throws<ArgumentException>(() => P28ChainScenario.Create(Initial(), [Event()], "fixture", [0, 0]));
        var replay = Scenario().ForReplay(7); Assert.Equal(8, replay.Events.Count); Assert.Equal(new[] { 7 }, replay.TraceEventIndexes);
        Assert.True(P28ChainValidator.Equal(Initial(), replay.InitialState));
    }
}
