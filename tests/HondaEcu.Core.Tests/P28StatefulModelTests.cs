using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28StatefulModelTests
{
    internal static byte[] Data(byte set = 30, byte clear = 40)
    {
        // Invented tables only, no executable OEM bytes.
        var rom = new byte[32768];
        for (var context = 0; context < 2; context++)
        {
            rom[0x6542 + context * 4] = set; rom[0x6543 + context * 4] = clear;
            rom[0x6544 + context * 4] = 60; rom[0x6545 + context * 4] = 70;
            for (var p = 0; p < 7; p++) { rom[0x654A + context * 14 + p * 2] = (byte)(240 - p * 40); rom[0x654B + context * 14 + p * 2] = 19; }
        }
        return rom;
    }
    internal static P28VtecPersistentState Initial(int prior = 0) => new((byte)(0xA0 | prior << 1), 0x80, 23, 2, 0, 0, 50, 0xA4);
    internal static P28VtecCall Call(byte code = 80, int context = 0) => new(0, code, context, true, 30, 0, 0, 0, 2, 255, 0, 0, 0);

    [Theory]
    [InlineData(0, 0)]
    [InlineData(0, 1)]
    [InlineData(0, 2)]
    [InlineData(0, 3)]
    [InlineData(1, 0)]
    [InlineData(1, 1)]
    [InlineData(1, 2)]
    [InlineData(1, 3)]
    public void AllContextsAndInitialCombinationsRetainTheirOwnPriorAcrossAscendingDescendingAndEquality(int context, int prior)
    {
        var rom = Data(); var model = new P28StatefulModel(rom, Initial(prior)); var previous = prior;
        byte[] inputs = [0, 29, 30, 31, 39, 40, 41, 59, 60, 61, 69, 70, 71, 80, 71, 70, 69, 61, 60, 59, 41, 40, 39, 31, 30, 29, 0];
        foreach (var code in inputs)
        {
            var step = model.Step(Call(code, context), true);
            Assert.Equal(previous, (step.Before.Data0131 >> 1) & 3);
            foreach (var t in step.Thresholds)
            {
                Assert.Equal((previous & 1 << t.Pair) != 0, t.OldState);
                Assert.Equal(rom[t.Offset], t.Threshold); Assert.Equal(code > t.Threshold, t.NewState);
                if (code == t.Threshold) Assert.False(t.NewState);
            }
            previous = (step.After.Data0131 >> 1) & 3;
            Assert.Equal(0xA0, step.After.Data0131 & 0xF8); Assert.Equal(0, step.Status);
        }
    }
    [Theory]
    [InlineData(30, 40, 35, true, false)]
    [InlineData(40, 40, 40, false, false)]
    [InlineData(40, 40, 41, true, true)]
    [InlineData(40, 30, 35, false, true)]
    public void NormalEqualAndReversedPairsDoNotForceDesiredHysteresis(int set, int clear, int code, bool fromSet, bool fromClear)
    {
        var a = new P28StatefulModel(Data((byte)set, (byte)clear), Initial(1));
        var b = new P28StatefulModel(Data((byte)set, (byte)clear), Initial(0));
        Assert.Equal(fromSet, a.Step(Call((byte)code), true).Thresholds[0].NewState);
        Assert.Equal(fromClear, b.Step(Call((byte)code), true).Thresholds[0].NewState);
        if (set > clear)
        {
            var sequence = Enumerable.Range(0, 6).Select(_ => a.Step(Call((byte)code), true).Thresholds[0].NewState).ToArray();
            Assert.Equal(new[] { true, false, true, false, true, false }, sequence);
        }
    }
    [Fact]
    public void ContextChangeAndDisablePreservePriorButDisabledNativePathClearsRequestAndReloadsD8()
    {
        var model = new P28StatefulModel(Data(), Initial());
        var set = model.Step(Call(), true); Assert.True(set.SoftwareRequest);
        var disabled = model.Step(Call() with { Enabled = false }, true);
        Assert.Equal(set.After.Data0131, disabled.After.Data0131); Assert.Equal(set.After.Data0198, disabled.After.Data0198);
        Assert.False(disabled.SoftwareRequest); Assert.False(disabled.SelectionStatus); Assert.Equal(10, disabled.After.Data01D8);
        Assert.Equal(20, disabled.After.Data01DF); // Disabled path does NOT clear hold counter.
        Assert.Single(disabled.Gates.Where(g => g.Outcome is not null)); Assert.All(disabled.Gates.Skip(1), g => Assert.Equal("NotEvaluated", g.Evaluation));
        var enabled = model.Step(Call(35, 1), true);
        Assert.True(enabled.Thresholds[0].OldState); Assert.True(enabled.Thresholds[0].NewState); Assert.Equal(1, enabled.Thresholds[0].Context);
    }
    [Fact]
    public void CountersDecayOnlyUnderExplicitNativeScheduleAndRequestIsNotSelectionStatus()
    {
        var model = new P28StatefulModel(Data(), Initial());
        var first = model.Step(Call(), true); Assert.True(first.SoftwareRequest); Assert.False(first.SelectionStatus);
        var unchanged = model.Step(Call(), true); Assert.Equal(2, unchanged.After.Data01D8); Assert.Empty(unchanged.TickWrites);
        var mature = model.Step(Call() with { FastTicks = 2, SlowTicks = 1 }, true);
        Assert.True(mature.SoftwareRequest); Assert.True(mature.SelectionStatus); Assert.Equal(10, mature.After.Data01D9); Assert.Equal(51, mature.After.Data00F3);
        Assert.Contains(mature.TickWrites, w => w.SequenceEqual(new[] { 0x1DF, 8, 19 }));
        var saturated = new P28StatefulModel(Data(), Initial() with { Data00F3 = 255, Data01D8 = 0, Data01D9 = 0 });
        var step = saturated.Step(Call() with { FastTicks = 32, SlowTicks = 32, Enabled = false });
        Assert.Empty(step.TickWrites); Assert.Equal(255, step.After.Data00F3);
    }
    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    public void OneChangedSoftwareInputBlocksAfterThresholdsAndShortCircuitsLaterGates(int gate)
    {
        var state = Initial(); var call = Call();
        switch (gate)
        {
            case 1: call = call with { Snapshot011A = 4 }; break;
            case 2: call = call with { Snapshot011C = 1 }; break;
            case 3: state = state with { Data00F3 = 49 }; break;
            case 4: call = call with { Raw00D9 = 68 }; break;
        }
        var step = new P28StatefulModel(Data(), state).Step(call, true);
        Assert.All(step.Thresholds, t => Assert.True(t.NewState)); Assert.False(step.SoftwareRequest);
        Assert.Null(step.Gates.Single(g => g.Pc == 0x12C0).Outcome); Assert.Empty(step.UsedAssumptions);
        var pc = gate switch { 1 => 0x1279, 2 => 0x127F, 3 => 0x128D, _ => 0x1293 };
        Assert.NotNull(step.Gates.Single(g => g.Pc == pc).Outcome);
    }
    [Fact]
    public void RawCounterMinimumAllowsAfterCallsAndStrictBoundaryTerminatesAllLaterHistory()
    {
        var model = new P28StatefulModel(Data(), Initial() with { Data00F3 = 48 });
        var first = model.Step(Call() with { SlowTicks = 1 }); Assert.False(first.SoftwareRequest); Assert.Equal(0, first.Status);
        var strict = model.Step(Call() with { SlowTicks = 1 }); Assert.Equal(1, strict.Status); Assert.Equal(0x12B4, strict.StopPc);
        Assert.Null(strict.SoftwareRequest); Assert.Null(strict.Gates.Single(g => g.Pc == 0x12B6).Outcome);
        var stopped = model.Step(Call() with { Enabled = false, SlowTicks = 32 }, true);
        Assert.Equal(4, stopped.Status); Assert.Equal(strict.After, stopped.After); Assert.Empty(stopped.TickWrites);
    }
    [Fact]
    public void InventedNonzeroRomConfigSkipsPrefixGateWithoutChangingRealRomConfiguration()
    {
        var rom = Data(); rom[0x60FA] = 7;
        var step = new P28StatefulModel(rom, Initial()).Step(Call() with { Raw00CC = 0 }, true);
        Assert.True(step.SoftwareRequest); Assert.True(step.Gates.Single(g => g.Pc == 0x1299).Outcome);
        Assert.Equal("NotEvaluated", step.Gates.Single(g => g.Pc == 0x129B).Evaluation);
    }
    [Fact]
    public void BaselineChildHistoriesDivergeNaturallyAndCanRejoin()
    {
        var a = new P28StatefulModel(Data(30, 40), Initial()); var b = new P28StatefulModel(Data(30, 32), Initial());
        var x = a.Step(Call(35), true); var y = b.Step(Call(35), true);
        Assert.NotEqual(x.After, y.After); Assert.NotEqual(x.SoftwareRequest, y.SoftwareRequest);
        x = a.Step(Call(35), true); y = b.Step(Call(35), true); Assert.NotEqual(x.Thresholds[0].OldState, y.Thresholds[0].OldState);
        x = a.Step(Call(0) with { SlowTicks = 32 }, true); y = b.Step(Call(0) with { SlowTicks = 32 }, true);
        Assert.Equal(x.After, y.After);
    }
    [Fact]
    public void ScenarioIsBoundedClosedImmutableAndContainsNoPerCallPersistentReseed()
    {
        var calls = new[] { Call(), Call() with { Index = 1 } }; var traces = new[] { 1 };
        var scenario = P28StatefulScenario.Create(Initial(), calls, "Invented public stimulus", traces);
        calls[0] = Call(99); traces[0] = 0; Assert.Equal(80, scenario.Calls[0].CompactCode); Assert.Equal(1, scenario.TraceCallIndexes[0]);
        Assert.Equal(scenario.Digest, P28StatefulScenario.Parse(scenario.ToJson()).Digest);
        foreach (var name in new[] { "thresholdPriorBits", "data0131", "allowAllUnknown", "rawRpm" })
        {
            var json = JsonNode.Parse(scenario.ToJson())!; json["calls"]![0]![name] = 0;
            Assert.ThrowsAny<Exception>(() => P28StatefulScenario.Parse(json.ToJsonString()));
        }
        Assert.Throws<ArgumentException>(() => P28StatefulScenario.Create(Initial(), [Call() with { FastTicks = 33 }], "invalid"));
        Assert.Throws<ArgumentException>(() => P28StatefulScenario.Create(Initial(), Enumerable.Range(0, 257).Select(i => Call() with { Index = i }).ToArray(), "invalid"));
        Assert.ThrowsAny<Exception>(() => P28StatefulScenario.Parse(scenario.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1, \"formatVersion\": 1", StringComparison.Ordinal)));
    }
}
