using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28IdleContextsTests
{
    [Theory]
    [InlineData(17, true, "BaseLookupNotExecuted")]
    [InlineData(255, true, "CellNotRead")]
    [InlineData(100, true, "CellReadZeroWeight")]
    [InlineData(101, true, "IntegerTruncation")]
    [InlineData(140, true, "TargetAndConsumerChange")]
    [InlineData(140, false, "ReadThenLateSourceReplacement")]
    [InlineData(100, false, "CellReadZeroWeight")]
    public void AbEffectsDistinguishZeroWeightFromTruncationAndLateReplacement(byte x, bool retain, string effect)
    {
        var a = RomImage.FromBytes(Image()); var b = P28IdleInspector.Mutate(a, new("context-21a0-table-cell-2", 1350));
        var initial = Initial() with { Data021a = (byte)(retain ? 1 : 0) };
        var sa = new P28IdleContextsModel(a, initial).Step(new(0, x, 1340, null));
        var sb = new P28IdleContextsModel(b, initial).Step(new(0, x, 1340, null));
        Assert.Equal(effect, P28IdleContextsValidator.ClassifyEffect(sa, sb, sb.ProducerReads.Contains(0x68D2), sa.CurrentBelowTarget != sb.CurrentBelowTarget || sa.ClampedError != sb.ClampedError));
    }
    internal static byte[] Image()
    {
        var b = P28IdleTests.Image(); void W(int a, int n) { b[a] = (byte)n; b[a + 1] = (byte)(n >> 8); }
        // Invented operand/calibration metadata only. Never a reconstructed OEM program.
        W(0x30A3, 0x68E0); W(0x3077, 0x68CB); W(0x307B, 15); W(0x30A7, 0x4321);
        int[] axes = [255, 180, 130, 90, 50, 30, 0], values = [800, 900, 1100, 1300, 1600, 1700, 1900];
        for (var i = 0; i < 7; i++) { b[0x68E0 + 3 * i] = (byte)axes[i]; W(0x68E1 + 3 * i, values[i]); }
        b[0x2FDD] = 18; b[0x2FF0] = 45; b[0x304F] = 43; b[0x305F] = 42;
        W(0x2FE3, 3100); W(0x7D9C, 3200); W(0x300E, 3300); W(0x3055, 3400); W(0x3065, 3500);
        W(0x2FE7, 1100); W(0x7DA0, 1200); W(0x3012, 900); W(0x3059, 700); W(0x3069, 500);
        W(0x2FF7, 40000); W(0x2FFE, 4096); W(0x3006, 4096); b[0x301C] = 9; b[0x3020] = 11; b[0x3036] = 7; b[0x3041] = 11;
        return b;
    }
    internal static P28IdleContextsState Initial() => new(99, 123, 55, 0xE1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    internal static P28IdleContextsScenario Scenario() => P28IdleContextsScenario.Create(Initial(), [new(0, 140, 1340, null), new(1, 140, 1340, null), new(2, 255, 1000, null)], "Invented explicit contexts");
    [Theory]
    [InlineData(0, 3200, 1200, "override-7d9b")]
    [InlineData(17, 3200, 1200, "override-7d9b")]
    [InlineData(18, 3300, 900, "override-300d")]
    [InlineData(20, 3300, 900, "override-300d")]
    [InlineData(21, 3300, 864, "override-300d")]
    [InlineData(44, 3300, 36, "override-300d")]
    [InlineData(45, 2044, 0, "table-68cb")]
    [InlineData(52, 2000, 0, "table-68cb")]
    [InlineData(140, 1333, 0, "table-68cb")]
    public void SourceAndSeparateComponentBoundaries(byte x, int target, int component, string source)
    { var s = new P28IdleContextsModel(RomImage.FromBytes(Image()), Initial()).Step(new(0, x, 1500, null)); Assert.Equal(target, s.FinalTarget); Assert.Equal(component, s.AfterProducer.Raw027a); Assert.Equal(source, s.FinalSource); Assert.Equal(target, s.BaseResult); }
    [Theory]
    [InlineData(4095, "override-300d")]
    [InlineData(4096, "override-7d9b")]
    [InlineData(39999, "override-7d9b")]
    [InlineData(40000, "override-300d")]
    [InlineData(65535, "override-300d")]
    public void UnsignedHistoryIntervalAndEquality(ushort history, string source)
    { var s = new P28IdleContextsModel(RomImage.FromBytes(Image()), Initial() with { Raw0274 = history }).Step(new(0, 22, 1500, null)); Assert.Equal(source, s.FinalSource); Assert.Equal(history, s.After.Raw0274); }
    [Fact]
    public void OverridePriorityCounterStoresAndOnceSeededHistory()
    {
        var image = RomImage.FromBytes(Image()); var initial = Initial() with { Data0217 = 64, Data022a = 16, Data0225 = 2 }; var model = new P28IdleContextsModel(image, initial);
        var first = model.Step(new(0, 22, 1500, null)); Assert.Equal("override-7d9b", first.FinalSource); Assert.Equal(9, first.After.Counter02e8); Assert.Equal(11, first.After.Counter02e9);
        var second = model.Step(new(1, 22, 1500, new(true, true, true, true, true, false, false)));
        Assert.Equal(first.After, second.Before); Assert.Equal(9, second.AfterInputs.Counter02e8); Assert.Equal("override-2fe2", second.FinalSource); Assert.Empty(second.Lookups);
        var third = new P28IdleContextsModel(image, Initial() with { Data0217 = 64, Data0225 = 2, Raw027c = 1 }).Step(new(0, 22, 1500, null));
        Assert.Equal(7, third.After.Counter02e5); Assert.Equal("override-300d", third.FinalSource);
        var e9 = new P28IdleContextsModel(image, Initial() with { Data0217 = 64, Data0225 = 2, Counter02e9 = 1 }).Step(new(0, 22, 1500, null)); Assert.Equal("override-300d", e9.FinalSource);
        var fourth = new P28IdleContextsModel(image, Initial() with { Data0217 = 64, Data0225 = 2 }).Step(new(0, 41, 1500, null)); Assert.Equal(3500, fourth.FinalTarget); Assert.Equal(23, fourth.After.Raw027a);
        var thirdOverride = new P28IdleContextsModel(image, Initial() with { Data0217 = 64, Data0216 = 8, Data0211 = 32 }).Step(new(0, 42, 1500, null)); Assert.Equal(3400, thirdOverride.FinalTarget); Assert.Equal(31, thirdOverride.After.Raw027a);
    }
    [Theory]
    [InlineData(0, 1900)]
    [InlineData(30, 1700)]
    [InlineData(50, 1600)]
    [InlineData(90, 1300)]
    [InlineData(130, 1100)]
    [InlineData(131, 1096)]
    [InlineData(180, 900)]
    [InlineData(255, 800)]
    public void LateLookupOverridesBaseButPreservesSeparateComponent(byte x, int target)
    {
        var s = new P28IdleContextsModel(RomImage.FromBytes(Image()), Initial() with { Data021a = 0 }).Step(new(0, x, 1500, null));
        Assert.Equal("table-68e0", s.FinalSource); Assert.Equal(target, s.FinalTarget); Assert.True(s.Lookups[^1].FinalContribution);
        Assert.All(s.Sources, a => Assert.False(a.FinalContribution)); Assert.All(s.Lookups.Where(l => l.Table == 0x68CB), l => Assert.False(l.FinalContribution));
        Assert.Contains(0x68E0 + 3 * s.Lookups[^1].UpperCell, s.ProducerReads);
    }
    [Fact]
    public void LowBaseLookupCanReplaceImmediateCandidatesAndReadOddLowerRecords()
    {
        var s = new P28IdleContextsModel(RomImage.FromBytes(Image()), Initial() with { Data0217 = 64, Data0216 = 8 }).Step(new(0, 19, 0, null));
        Assert.Equal("table-68cb", s.FinalSource); Assert.Equal(2215, s.FinalTarget); Assert.Equal(2, s.Sources.Count); Assert.All(s.Sources, a => Assert.False(a.FinalContribution));
        Assert.Equal(5, s.Lookups[0].UpperCell); Assert.Equal(6, s.Lookups[0].LowerCell); Assert.Contains(0x68DA, s.ProducerReads); Assert.Contains(0x68DE, s.ProducerReads);
        Assert.Equal(0, s.After.Raw027a); Assert.Null(s.ComponentCalculation);
    }
    [Fact]
    public void MutationReadContributionMaskingAndIndependentImages()
    {
        var a = RomImage.FromBytes(Image()); var b = P28IdleInspector.Mutate(a, new("context-21a0-table-cell-2", 1350));
        foreach (var retain in new[] { true, false })
        {
            var initial = Initial() with { Data021a = (byte)(retain ? 1 : 0) }; var ma = new P28IdleContextsModel(a, initial); var mb = new P28IdleContextsModel(b, initial);
            var sa = ma.Step(new(0, 140, 1340, null)); var sb = mb.Step(new(0, 140, 1340, null)); Assert.Contains(0x68D2, sb.ProducerReads);
            if (retain) { Assert.Equal(1333, sa.FinalTarget); Assert.Equal(1350, sb.FinalTarget); Assert.NotEqual(sa.CurrentBelowTarget, sb.CurrentBelowTarget); }
            else { Assert.Equal(sa.FinalTarget, sb.FinalTarget); Assert.False(sb.Lookups[0].FinalContribution); }
            Assert.Equal(sa.After, ma.Step(new(1, 140, 1340, null)).Before); Assert.Equal(sb.After, mb.Step(new(1, 140, 1340, null)).Before);
            Assert.Equal(ma.Step(new(2, 17, 0, null)).FinalTarget, mb.Step(new(2, 17, 0, null)).FinalTarget);
        }
        Assert.Equal(new[] { 0x68D2 }, Enumerable.Range(0, a.Size).Where(i => a.Span[i] != b.Span[i]));
    }
    [Fact]
    public void M1qSubsetKeepsAllEstablishedObservationsAndGuards()
    {
        var image = RomImage.FromBytes(Image()); var modern = new P28IdleContextsModel(image, Initial()); var old = new P28IdleModel(image, new(99, 123, 55, 0xE1));
        for (var x = 52; x <= 255; x++)
        {
            var a = modern.Step(new(0, (byte)x, 1500, null)); var b = old.Step(new(0, (byte)x, 1500));
            Assert.Equal(b.FinalTarget, a.FinalTarget); Assert.Equal(b.ClampedError, a.ClampedError); Assert.Equal(b.CurrentBelowTarget, a.CurrentBelowTarget); Assert.Equal(b.After.Raw027a, a.After.Raw027a);
            Assert.Equal(JsonSerializer.Serialize(b.ProducerWrites), JsonSerializer.Serialize(a.ProducerWrites)); Assert.Equal(JsonSerializer.Serialize(b.ConsumerWrites), JsonSerializer.Serialize(a.ConsumerWrites)); Assert.Equal(b.ProducerReads, a.ProducerReads); Assert.Equal(b.ConsumerReads, a.ConsumerReads);
        }
        Assert.Throws<ArgumentException>(() => P28IdleScenario.Create(new(1, 2, 3, 1), [new(0, 51, 0)], "Old guard"));
        Assert.Throws<ArgumentException>(() => P28IdleScenario.Create(new(1, 2, 3, 0), [new(0, 52, 0)], "Old guard"));
    }
    [Fact]
    public void MaskedSelectorsPreserveNativeSignAndOtherBits()
    {
        var initial = Initial() with { Data021a = 0xFF, Data0211 = 0xFF, Data0216 = 0xFF, Data0217 = 0xFF, Data0225 = 0xFF, Data022a = 0xFF };
        var s = P28IdleContextsScenario.ApplySelectors(initial, new(false, false, false, false, false, false, false));
        Assert.Equal(0xFE, s.Data021a); Assert.Equal(0xDF, s.Data0211); Assert.Equal(0xF7, s.Data0216); Assert.Equal(0xBF, s.Data0217); Assert.Equal(0xFD, s.Data0225); Assert.Equal(0xCF, s.Data022a);
        Assert.Equal(initial with { Data021a = s.Data021a, Data0211 = s.Data0211, Data0216 = s.Data0216, Data0217 = s.Data0217, Data0225 = s.Data0225, Data022a = s.Data022a }, s);
    }
    [Fact]
    public void ClosedSchemaRequiresInputsAndRejectsReseedingAndUnboundedCalls()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28IdleContextsScenario.Parse(s.ToJson()).Digest);
        foreach (var key in new[] { "target", "raw027a", "errorMagnitude", "counter02e8", "expected", "pc", "data021a" }) { var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]![key] = 0; Assert.Throws<InvalidDataException>(() => P28IdleContextsScenario.Parse(n.ToJsonString())); }
        foreach (var key in new[] { "index", "rawD9", "rawPeriod", "selectors" }) { var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]!.AsObject().Remove(key); Assert.Throws<InvalidDataException>(() => P28IdleContextsScenario.Parse(n.ToJsonString())); }
        var missing = JsonNode.Parse(s.ToJson())!; missing["initialState"]!.AsObject().Remove("counter02e9"); Assert.Throws<InvalidDataException>(() => P28IdleContextsScenario.Parse(missing.ToJsonString()));
        Assert.Throws<ArgumentException>(() => P28IdleContextsScenario.Create(Initial(), Enumerable.Range(0, 65).Select(i => new P28IdleContextsCall(i, 0, 0, null)).ToArray(), "Too many"));
        Assert.Throws<ArgumentException>(() => P28IdleContextsScenario.Create(Initial(), [new(1, 0, 0, null)], "Not dense"));
    }
    [Fact]
    public void InspectionRequiresExactBindingAndDoesNotReinterpretOldReports()
    {
        var (im, p, b) = P28AcquisitionValidatorTests.Fixture(Image()); Assert.Empty(P28IdleContextsInspector.Inspect(im, p, null, true).Cells);
        var r = P28IdleContextsInspector.Inspect(im, p, b, true); Assert.True(r.InterpretationApplied); Assert.Equal(14, r.Cells.Count); Assert.Equal(10, r.Scalars.Count); Assert.False(r.PhysicalRpmAvailable);
        Assert.Equal(7, P28IdleInspector.Inspect(im, p, b, true).Cells.Count);
    }
}
