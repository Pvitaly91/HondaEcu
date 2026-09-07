using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28AdaptiveTests
{
    internal static byte[] Image()
    {
        var b = P28LimiterTests.Image(500, 510);
        void Word(int a, int v) { b[a] = (byte)v; b[a + 1] = (byte)(v >> 8); }
        // Invented table/operand data; no native function fixture.
        Word(0x487D, 0x6493); Word(0x4880, 0x6499); Word(0x4886, 0x649F); Word(0x4889, 0x64A5);
        foreach (var (a, origin, value, coefficient) in new[] { (0x6493, 1000, 110, 32768), (0x6499, 1000, 100, 16384), (0x649F, 2000, 210, 16384), (0x64A5, 2000, 200, 8192) })
        { Word(a, origin); Word(a + 2, value); Word(a + 4, coefficient); }
        Word(0x5AB9, 3); Word(0x5AC3, 2); Word(0x48E4, 0x0200); b[0x489A] = 4; b[0x48A7] = 2; b[0x48CA] = 4; b[0x48AE] = 50;
        return b;
    }
    internal static P28AdaptiveState Initial(ushort cut = 100, ushort resume = 110) => new(new(0, 0, 0, 255, 7, cut, resume), 0, 0, 65535, 65535);
    internal static P28AdaptiveCall Call(int i = 0, ushort raw = 100) => new(new(i, raw, false, false, 254), 1100, false, false, false, false, true, 0, 0, 0);
    internal static P28AdaptiveScenario Scenario() => P28AdaptiveScenario.Create(Initial(), [Call(), Call(1)], "Invented software experiment");
    [Fact]
    public void IndependentHistoryBoundHoldTickAndRecovery()
    {
        var m = new P28AdaptiveModel(Image(), Initial());
        var a = m.Step(Call()); var b = m.Step(Call(1)); var c = m.Step(Call(2) with { TimerTicks = 2 });
        Assert.Equal((ushort)102, a.AfterProducer.Limiter.RamCut); Assert.Equal((ushort)112, a.AfterProducer.Limiter.RamResume);
        Assert.Equal("TimerHold", b.Path); Assert.Equal(a.After, b.Before); Assert.Equal(a.AfterProducer.Limiter.RamCut, b.AfterProducer.Limiter.RamCut);
        Assert.Equal(104, c.AfterProducer.Limiter.RamCut); Assert.Equal(114, c.AfterProducer.Limiter.RamResume); Assert.Equal(b.After, c.Before);
        Assert.Equal(new[] { 1, 0 }, c.Ticks.Select(t => (int)t.After));
        var d = m.Step(Call(3) with { Reset217 = true }); Assert.Equal("Reset217", d.Path); Assert.Equal(4, d.After.Counter); Assert.Equal(100, d.AfterProducer.Limiter.RamCut);
        var e = m.Step(Call(4) with { TimerTicks = 2, CounterTicks = 4 }); Assert.Equal("AdaptiveBound", e.Path); Assert.Equal(102, e.AfterProducer.Limiter.RamCut);
    }
    [Fact]
    public void BankSwitchRetainsPreviousWordsUntilNativeReset()
    {
        var m = new P28AdaptiveModel(Image(), Initial()); var a = m.Step(Call()); var b = m.Step(Call(1) with { Bank1 = true });
        Assert.Equal(1, b.Bank); Assert.Equal("TimerHold", b.Path); Assert.Equal(a.After.Limiter.RamCut, b.AfterProducer.Limiter.RamCut);
        Assert.Equal(0x64A1, b.TableReads[0][1]); Assert.Equal(210, b.TableReads[0][2]);
        var c = m.Step(Call(2) with { Bank1 = true, Reset214 = true }); Assert.Equal(200, c.AfterProducer.Limiter.RamCut); Assert.Equal(210, c.AfterProducer.Limiter.RamResume);
    }
    [Theory]
    [InlineData(true, true, 99, "Reset217")]
    [InlineData(false, true, 99, "Reset214")]
    [InlineData(false, false, 49, "AdaptiveBound")]
    [InlineData(false, false, 50, "CounterResetDecrease")]
    [InlineData(false, false, 51, "CounterResetDecrease")]
    public void ResetPriorityAndRawByteEquality(bool reset217, bool reset214, byte rawD9, string path)
    { Assert.Equal(path, new P28AdaptiveModel(Image(), Initial()).Step(Call() with { Reset217 = reset217, Reset214 = reset214, RawD9 = rawD9 }).Path); }
    [Theory]
    [InlineData(0, 100)]
    [InlineData(2, 100)]
    [InlineData(3, 100)]
    [InlineData(102, 100)]
    [InlineData(103, 100)]
    [InlineData(104, 101)]
    [InlineData(65535, 65532)]
    public void DecreaseBorrowFloorEquality(ushort initial, ushort expected)
    { var s = new P28AdaptiveModel(Image(), Initial(initial, initial) with { Counter = 1 }).Step(Call()); Assert.Equal(expected, s.AfterProducer.Limiter.RamCut); Assert.Equal("CounterPendingDecrease", s.Path); }
    [Theory]
    [InlineData(999, 100)]
    [InlineData(1000, 100)]
    [InlineData(1003, 100)]
    [InlineData(1004, 101)]
    [InlineData(1005, 101)]
    [InlineData(65535, 16233)]
    public void RawWordBorrowAndHighProductBoundaries(ushort raw, ushort cut)
    { var s = new P28AdaptiveModel(Image(), Initial(65535, 65535)).Step(Call() with { Raw00ce = raw }); Assert.Equal(cut, s.AfterProducer.Limiter.RamCut); Assert.Equal(raw < 1000 ? 6 : 8, s.TableReads.Count); }
    [Fact]
    public void AdditionWrapAndEqualReversedPairsAreNotNormalized()
    {
        var b = Image(); b[0x649B] = 255; b[0x649C] = 255;
        var s = new P28AdaptiveModel(b, Initial(65535, 65535)).Step(Call() with { Raw00ce = 1004 }); Assert.Equal(0, s.AfterProducer.Limiter.RamCut);
        var m = new P28AdaptiveModel(Image(), Initial(120, 100) with { Timer = 255 });
        var a = m.Step(Call(raw: 110)); var c = m.Step(Call(1, 110)); Assert.True(a.Limiter.OverspeedRequest); Assert.False(c.Limiter.OverspeedRequest); Assert.Equal(120, c.AfterProducer.Limiter.RamCut); Assert.Equal(100, c.AfterProducer.Limiter.RamResume);
        var equal = new P28AdaptiveModel(Image(), Initial(110, 110) with { Timer = 255 }).Step(Call(raw: 110)); Assert.False(equal.Limiter.OverspeedRequest);
    }
    [Theory]
    [InlineData(0, 0)]
    [InlineData(32, 0)]
    [InlineData(0, 128)]
    [InlineData(32, 128)]
    public void FixedRamFixedAndIndependentInhibit(byte prior, byte inhibit)
    {
        var initial = Initial() with { Limiter = Initial().Limiter with { Data0124 = prior, Data012A = inhibit } };
        var m = new P28AdaptiveModel(Image(), initial); var a = m.Step(Call(raw: 499) with { Limiter = Call(raw: 499).Limiter with { P4Bit0 = true } });
        var b = m.Step(Call(1, 200)); var c = m.Step(Call(2, 499) with { Limiter = Call(2, 499).Limiter with { Snapshot011bBit7 = true } });
        Assert.True(a.Limiter.OverspeedRequest); Assert.False(b.Limiter.OverspeedRequest); Assert.Equal(inhibit != 0, b.Limiter.InhibitBranch); Assert.True(c.Limiter.OverspeedRequest);
        Assert.Equal("Fixed", a.Limiter.Context); Assert.Equal(112, b.Limiter.Threshold); Assert.Equal(500, c.Limiter.Threshold);
    }
    [Fact]
    public void ClosedSchemaRejectsReseedingNullsExtraFieldsAndUnboundedSchedule()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28AdaptiveScenario.Parse(s.ToJson()).Digest);
        foreach (var field in new[] { "ramCut", "timer", "expected", "allowAssumptions", "mutation" })
        { var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]![field] = 1; Assert.Throws<InvalidDataException>(() => P28AdaptiveScenario.Parse(n.ToJsonString())); }
        Assert.Throws<ArgumentException>(() => P28AdaptiveScenario.Create(Initial(), [Call() with { TimerTicks = 33 }], "too many"));
        Assert.Throws<ArgumentException>(() => P28AdaptiveScenario.Create(Initial(), Enumerable.Range(0, 65).Select(i => Call(i)).ToArray(), "too many"));
        Assert.Throws<InvalidDataException>(() => P28AdaptiveScenario.Parse(s.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1, \"formatVersion\": 1", StringComparison.Ordinal)));
        Assert.ThrowsAny<Exception>(() => P28AdaptiveScenario.Parse(s.ToJson().Replace("\"limiter\": {", "\"limiter\": null, \"extra\": {", StringComparison.Ordinal)));
    }
    [Fact]
    public async Task ActualSubprocessStrictStopNullSuffixAndResponseTampering()
    {
        var bytes = Image(); bytes[0x487B] = 0x45; bytes[0x487C] = 0x81;
        var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(bytes); var s = Scenario();
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28AdaptiveValidator.CreateRequest(im, s));
        var r = P28AdaptiveValidator.Analyze(im, profile, binding, s, response);
        Assert.True(r.HasFailure); Assert.All(r.Sequences, x => { Assert.Equal(1, x.Counts.Unresolved); Assert.Equal(1, x.Counts.NotRun); Assert.Equal(0, x.Counts.ConditionalMatches); Assert.Null(x.Checkpoints[0].Expected); Assert.Null(x.Checkpoints[0].ActualProducerPath); Assert.Null(x.Checkpoints[1].ActualBank); });
        foreach (var edit in new Action<JsonNode>[] {
            n=>n["runnerVersion"]="0.7.0", n=>n["entryContracts"]![0]!["producerBudget"]=999,
            n=>n["adaptiveSequences"]![0]!["checkpoints"]![1]!["status"]=0,
            n=>n["adaptiveSequences"]![0]!["checkpoints"]![0]!["producer"]!["result"]!["usedAssumptions"]=new JsonArray("oki.add-er1-a") })
        { var n = JsonNode.Parse(response.Response.GetRawText())!; edit(n); Assert.Throws<SliceProcessException>(() => P28AdaptiveValidator.Analyze(im, profile, binding, s, new(JsonSerializer.SerializeToElement(n), ""))); }
        await Assert.ThrowsAsync<InvalidDataException>(() => P28AdaptiveValidator.ExecuteAsync(im, profile, binding, false, "not-launched", s));
        Assert.Equal(bytes, im.ToArray());
    }
    [Fact]
    public async Task InventedExecutionCannotSeedIndependentModelOrMasqueradeAsProof()
    {
        var b = Image();
        new byte[] { 0x03, 0xE1, 0x48 }.CopyTo(b, 0x487B);
        new byte[] { 0xE3, 0x24, 0x86, 16, 0, 0xD3, 0x24, 0x03, 0xF5, 0x48 }.CopyTo(b, 0x48E1);
        new byte[] { 0x03, 0x38, 0x1A }.CopyTo(b, 0x1966); new byte[] { 0x03, 0x96, 0x55 }.CopyTo(b, 0x5585);
        var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(b); var s = Scenario();
        var r = await P28AdaptiveValidator.ExecuteAsync(im, profile, binding, true, ExecutionTestPaths.RustRunner, s);
        Assert.All(r.Sequences, sequence =>
        {
            Assert.Equal(2, sequence.Counts.Mismatches); Assert.Equal(2, sequence.Counts.CompletedCalls);
            Assert.Equal(116, sequence.Checkpoints[0].Actual.GetProperty("stateAfterProducer").GetProperty("limiter").GetProperty("ramCut").GetInt32());
            Assert.Equal(132, sequence.Checkpoints[1].Actual.GetProperty("stateAfterProducer").GetProperty("limiter").GetProperty("ramCut").GetInt32());
            Assert.Equal(sequence.Checkpoints[0].Expected!.After, sequence.Checkpoints[1].Expected!.Before);
            Assert.NotEqual(116, sequence.Checkpoints[1].Expected!.Before.Limiter.RamCut);
        });
    }
}
