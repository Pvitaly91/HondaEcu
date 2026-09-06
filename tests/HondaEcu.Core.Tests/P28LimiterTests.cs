using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28LimiterTests
{
    internal static byte[] Image(ushort cut = 0x1234, ushort resume = 0x1240)
    { var b = new byte[32768]; b[0x1966] = 0x62; b[0x1969] = 0x67; b[0x1967] = (byte)resume; b[0x1968] = (byte)(resume >> 8); b[0x196A] = (byte)cut; b[0x196B] = (byte)(cut >> 8); return b; }
    internal static P28LimiterState Initial(byte prior = 0) => new(prior, 128, 0, 255, 7, 100, 110);
    internal static P28LimiterScenario Scenario() => P28LimiterScenario.Create(Initial(), [new(0, 100, true, false, 254), new(1, 110, false, false, 253)], "Invented software fixture");
    [Theory]
    [InlineData(0, 4659, true)]
    [InlineData(0, 4660, false)]
    [InlineData(0, 4661, false)]
    [InlineData(32, 4671, true)]
    [InlineData(32, 4672, false)]
    [InlineData(32, 4673, false)]
    public void IndependentBoundaryAndEquality(byte prior, ushort raw, bool cut)
    { var s = new P28LimiterModel(Image(), Initial(prior)).Step(new(0, raw, true, false, 254)); Assert.Equal(cut, s.OverspeedRequest); Assert.Equal(cut, s.InhibitBranch); Assert.Equal(cut ? 7 : 20, s.After.Data01D7); Assert.Equal(raw, s.ComparisonLeft); }
    [Fact]
    public void PersistenceContextSwitchAndIndependentInhibit()
    {
        var model = new P28LimiterModel(Image(), Initial());
        var a = model.Step(new(0, 4659, true, false, 254)); var b = model.Step(new(1, 4660, false, true, 253));
        var c = model.Step(new(2, 110, false, false, 252)); var d = model.Step(new(3, 105, false, false, 254));
        Assert.True(a.OverspeedRequest); Assert.True(b.OverspeedRequest); Assert.Equal(4672, b.Threshold);
        Assert.False(c.OverspeedRequest); Assert.Equal(110, c.Threshold); Assert.False(d.OverspeedRequest); Assert.Equal(100, d.Threshold);
        Assert.Equal(252, d.After.Data018F); Assert.Equal(c.After, d.Before); Assert.Equal(20, d.After.Data01D7);
        var independent = new P28LimiterModel(Image(), Initial() with { Data012A = 128 }).Step(new(0, 5000, true, false, 254));
        Assert.False(independent.OverspeedRequest); Assert.True(independent.InhibitBranch); Assert.Empty(independent.ConsumerWrites);
    }
    [Theory]
    [InlineData(100, 110, true, true)]
    [InlineData(100, 100, true, false)]
    [InlineData(110, 100, true, false)]
    public void NormalEqualReversedPairsAreNotSilentlyNormalized(ushort cut, ushort resume, bool first, bool second)
    { var m = new P28LimiterModel(Image(cut, resume), Initial()); var a = m.Step(new(0, 99, true, false, 254)); var b = m.Step(new(1, 105, true, false, 254)); Assert.Equal(first, a.OverspeedRequest); Assert.Equal(second, b.OverspeedRequest); }
    [Theory]
    [InlineData(0, true)]
    [InlineData(65535, false)]
    public void RawEndpointsHaveNoPhysicalRpm(ushort raw, bool request)
    { Assert.Equal(request, new P28LimiterModel(Image(), Initial()).Step(new(0, raw, true, false, 254)).OverspeedRequest); }
    [Fact]
    public void InspectorNeedsExactBindingNotConfirmationAloneAndMutationIsWordOnly()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(Image());
        Assert.False(P28LimiterInspector.Inspect(image, profile, null, true).InterpretationApplied);
        Assert.False(P28LimiterInspector.Inspect(image, profile, binding, false).InterpretationApplied);
        var inspect = P28LimiterInspector.Inspect(image, profile, binding, true); Assert.True(inspect.InterpretationApplied);
        Assert.Equal(4660, inspect.Fields[0].Raw); Assert.Equal(2, inspect.Fields[0].Width);
        var mutation = new P28LimiterMutation("fixed-context-cut", 0xABCD); var b = P28LimiterInspector.Mutate(image, mutation);
        Assert.Equal(0xCD, b.ToArray()[0x196A]); Assert.Equal(0xAB, b.ToArray()[0x196B]); Assert.Equal(Image(), image.ToArray());
        Assert.False(P28LimiterInspector.Inspect(b, profile, binding, true).InterpretationApplied);
        var extra = b.CreateModifiedCopy([new BytePatch(0x196C, [1])]); Assert.Throws<InvalidDataException>(() => P28LimiterInspector.AdmitMutation(image, extra, mutation));
        Assert.Throws<ArgumentException>(() => P28LimiterInspector.Mutate(image, new("fixed-context-cut", 4660)));
        Assert.Throws<ArgumentException>(() => P28LimiterInspector.Mutate(image, new("opcode", 1)));
    }
    [Fact]
    public void BoundedClosedScenarioCannotInjectHistoryExpectedOrPermissions()
    {
        var scenario = Scenario(); Assert.Equal(scenario.Digest, P28LimiterScenario.Parse(scenario.ToJson()).Digest);
        foreach (var key in new[] { "data0124", "expected", "enabled", "allowAssumptions" }) { var n = JsonNode.Parse(scenario.ToJson())!; n["calls"]![0]![key] = 1; Assert.Throws<InvalidDataException>(() => P28LimiterScenario.Parse(n.ToJsonString())); }
        Assert.Throws<ArgumentException>(() => P28LimiterScenario.Create(Initial(), [], "none"));
        Assert.Throws<ArgumentException>(() => P28LimiterScenario.Create(Initial(), [new(1, 1, true, false, 254)], "bad index"));
        Assert.Throws<ArgumentException>(() => P28LimiterScenario.Create(Initial(), [new(0, 1, true, false, 1)], "bad mask"));
        Assert.Throws<ArgumentException>(() => P28LimiterScenario.Create(Initial(), Enumerable.Range(0, 257).Select(i => new P28LimiterCall(i, 1, true, false, 254)).ToArray(), "too long"));
        Assert.Throws<InvalidDataException>(() => P28LimiterScenario.Parse(scenario.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1, \"formatVersion\": 1", StringComparison.Ordinal)));
    }
    [Fact]
    public async Task ActualRustSubprocessStrictStopNullSuffixAndProtocolTampering()
    {
        var bytes = Image(); bytes[0x196C] = 0x09; // Invented constants then unresolved ADD, not ROM implementation.
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(bytes); var scenario = Scenario();
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28LimiterValidator.CreateRequest(image, scenario));
        var report = P28LimiterValidator.Analyze(image, profile, binding, scenario, response);
        Assert.True(report.HasFailure); Assert.All(report.Sequences, s => { Assert.Equal(1, s.Counts.Unresolved); Assert.Equal(1, s.Counts.NotRun); Assert.Equal(0, s.Counts.ConditionalMatches); Assert.Equal(JsonValueKind.Null, s.Checkpoints[0].Actual.GetProperty("overspeedRequest").ValueKind); Assert.Null(s.Checkpoints[1].Expected); });
        foreach (var mutation in new Action<JsonNode>[] {
            n=>n["limiterSequences"]![0]!["checkpoints"]![1]!["overspeedRequest"]=false,
            n=>n["limiterSequences"]![0]!["checkpoints"]![0]!["decision"]!["usedAssumptions"]=new JsonArray("oki.add-er1-a"),
            n=>n["entryContracts"]![0]!["budget"]=999,
            n=>n["runnerVersion"]="0.6.0"})
        { var node = JsonNode.Parse(response.Response.GetRawText())!; mutation(node); Assert.Throws<SliceProcessException>(() => P28LimiterValidator.Analyze(image, profile, binding, scenario, new(JsonSerializer.SerializeToElement(node), ""))); }
        Assert.Equal(bytes, image.ToArray());
    }
    [Fact]
    public async Task ActualInventedConsumerRunsButCannotMasqueradeAsLimiterMatchOrSeedModelHistory()
    {
        var bytes = Image();
        // An invented increment and absolute exit, not the recovered OEM procedure.
        new byte[] { 0xF4, 0x24, 0x86, 1, 0xD4, 0x24, 0x03, 0x38, 0x1A }.CopyTo(bytes, 0x196C);
        new byte[] { 0xF4, 0x8F, 0x86, 2, 0xD4, 0x8F, 0x03, 0x96, 0x55 }.CopyTo(bytes, 0x5585);
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(bytes); var scenario = Scenario();
        var result = await P28LimiterValidator.ExecuteAsync(image, profile, binding, true, ExecutionTestPaths.RustRunner, scenario);
        Assert.True(result.HasFailure);
        Assert.All(result.Sequences, s =>
        {
            Assert.Equal(2, s.Counts.CompletedCalls); Assert.Equal(2, s.Counts.DownstreamAvailable); Assert.Equal(2, s.Counts.Mismatches); Assert.Equal(0, s.Counts.StrictMatches);
            Assert.Equal(1, s.Checkpoints[0].Actual.GetProperty("stateAfter").GetProperty("data0124").GetInt32());
            Assert.Equal(2, s.Checkpoints[1].Actual.GetProperty("stateAfter").GetProperty("data0124").GetInt32());
            Assert.Equal(44, s.Checkpoints[1].Expected!.Before.Data0124);
            Assert.Equal(s.Checkpoints[0].Expected!.After, s.Checkpoints[1].Expected!.Before);
        });
    }
}
