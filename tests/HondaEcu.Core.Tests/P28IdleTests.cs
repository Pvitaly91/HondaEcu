using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28IdleTests
{
    internal static byte[] Image()
    {
        var b = new byte[32768]; void W(int a, int value) { b[a] = (byte)value; b[a + 1] = (byte)(value >> 8); }
        // Invented calibration/ISA operand metadata, not an OEM program/corpus.
        int[] axes = [255, 190, 140, 100, 52, 20, 0], values = [1000, 1150, 1333, 1600, 2000, 2200, 2500];
        for (var i = 0; i < 7; i++) { b[0x68CB + 3 * i] = (byte)axes[i]; W(0x68CC + 3 * i, values[i]); }
        W(0x2FD5, 0x68CB); W(0x7D8B, 0x1234); b[0x7D8E] = 52; b[0x2FDB] = 52; W(0x9E5, 768); W(0x9EC, 768);
        return b;
    }
    internal static P28IdleState Initial() => new(99, 123, 55, 0xE1);
    internal static P28IdleScenario Scenario(P28IdleMutation? mutation = null) => P28IdleScenario.Create(Initial(), [new(0, 140, 1340), new(1, 140, 1340), new(2, 255, 1000)], "Invented isolated software inputs", mutation);
    [Theory]
    [InlineData(52, 2000)]
    [InlineData(100, 1600)]
    [InlineData(110, 1534)]
    [InlineData(140, 1333)]
    [InlineData(141, 1330)]
    [InlineData(190, 1150)]
    [InlineData(255, 1000)]
    public void PackedWordTableAndDirectionalIntegerTruncation(byte x, int target)
    {
        var image = RomImage.FromBytes(Image()); var step = new P28IdleModel(image, Initial()).Step(new(0, x, 1500));
        Assert.Equal(target, step.FinalTarget); Assert.Equal(target, step.AfterProducer.Target); Assert.Equal(0, step.AfterProducer.Raw027a);
        Assert.Equal(Initial().ErrorMagnitude, step.AfterProducer.ErrorMagnitude); Assert.Equal(Initial().Data021a, step.AfterProducer.Data021a);
    }
    [Theory]
    [InlineData(0, true, 768)]
    [InlineData(565, true, 768)]
    [InlineData(566, true, 767)]
    [InlineData(1332, true, 1)]
    [InlineData(1333, false, 0)]
    [InlineData(1334, false, 1)]
    [InlineData(2100, false, 767)]
    [InlineData(2101, false, 768)]
    [InlineData(2102, false, 768)]
    [InlineData(65535, false, 768)]
    public void UnsignedPeriodEqualitySignAndBothClampEdges(ushort current, bool sign, int magnitude)
    { var s = new P28IdleModel(RomImage.FromBytes(Image()), Initial()).Step(new(0, 140, current)); Assert.Equal(sign, s.CurrentBelowTarget); Assert.Equal(magnitude, s.ClampedError); Assert.Equal((current - 1333) & 65535, s.DifferenceModuloWord); Assert.Equal(Initial().Data021a & ~16, s.After.Data021a & ~16); }
    [Fact]
    public void HistoriesRepeatAndCrossBothDirectionsWithoutReseeding()
    {
        var m = new P28IdleModel(RomImage.FromBytes(Image()), Initial()); P28IdleState previous = Initial();
        foreach (var current in new ushort[] { 1332, 1333, 1334, 1333, 1332, 1332 }) { var s = m.Step(new(0, 140, current)); Assert.Equal(previous, s.Before); previous = s.After; }
        Assert.Equal(1333, previous.Target); Assert.Equal(1, previous.ErrorMagnitude); Assert.True((previous.Data021a & 16) != 0);
    }
    [Fact]
    public void RisingAndFlatNumericCellsAndExtremeWordsUseIntegerArithmetic()
    {
        var b = Image(); b[0x68D2] = 0xFF; b[0x68D3] = 0xFF; b[0x68D5] = 0; b[0x68D6] = 0;
        var s = new P28IdleModel(RomImage.FromBytes(b), Initial()).Step(new(0, 120, 0)); Assert.Equal(32767, s.FinalTarget);
        b[0x68D2] = 0; b[0x68D3] = 0; s = new P28IdleModel(RomImage.FromBytes(b), Initial()).Step(new(0, 120, 0)); Assert.Equal(0, s.FinalTarget); Assert.False(s.CurrentBelowTarget);
    }
    [Fact]
    public void OneNumericMutationOwnImageModelsAndUnaffectedIntervals()
    {
        var a = RomImage.FromBytes(Image()); var mutation = new P28IdleMutation("context-21a0-table-cell-2", 1350); var b = P28IdleInspector.Mutate(a, mutation);
        Assert.Equal(1333, P28LimiterInspector.Word(a.Span, 0x68D2)); Assert.Equal(1350, P28LimiterInspector.Word(b.Span, 0x68D2));
        var ma = new P28IdleModel(a, Initial()); var mb = new P28IdleModel(b, Initial()); var sa = ma.Step(new(0, 140, 1340)); var sb = mb.Step(new(0, 140, 1340));
        Assert.False(sa.CurrentBelowTarget); Assert.True(sb.CurrentBelowTarget); Assert.Equal(1333, sa.FinalTarget); Assert.Equal(1350, sb.FinalTarget);
        Assert.NotEqual(ma.Step(new(1, 140, 1340)).Before.Target, mb.Step(new(1, 140, 1340)).Before.Target);
        Assert.Equal(ma.Step(new(2, 255, 1000)).FinalTarget, mb.Step(new(2, 255, 1000)).FinalTarget);
        Assert.Throws<ArgumentException>(() => P28IdleInspector.Mutate(a, new("offset-26834", 123)));
        foreach (var offset in new[] { 0x2FD1, 0x2FD5, 0x68D1, 0x68D5, 0x7FFF })
        {
            var bad = b.CreateModifiedCopy([new BytePatch(offset, [(byte)(b.Span[offset] ^ 1)])]); Assert.Throws<InvalidDataException>(() => P28IdleInspector.AdmitMutation(a, bad, mutation));
        }
        Assert.Throws<InvalidDataException>(() => P28IdleInspector.Mutate(a, new(mutation.Field, 1333)));
    }
    [Fact]
    public void ClosedBoundedSchemaRejectsMissingNullsDuplicatesAndInternalOverrides()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28IdleScenario.Parse(s.ToJson()).Digest);
        foreach (var key in new[] { "target", "expected", "data021a", "counter", "offset" }) { var n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]![key] = 1; Assert.Throws<InvalidDataException>(() => P28IdleScenario.Parse(n.ToJsonString())); }
        foreach (var key in new[] { "index", "rawD9", "rawPeriod" }) foreach (var remove in new[] { false, true }) { var n = JsonNode.Parse(s.ToJson())!; if (remove) n["calls"]![0]!.AsObject().Remove(key); else n["calls"]![0]![key] = null; Assert.ThrowsAny<Exception>(() => P28IdleScenario.Parse(n.ToJsonString())); }
        Assert.Throws<ArgumentException>(() => P28IdleScenario.Create(Initial(), [new(0, 51, 123)], "outside supported path"));
        Assert.Throws<ArgumentException>(() => P28IdleScenario.Create(Initial() with { Data021a = 0 }, [new(0, 52, 123)], "other context"));
        Assert.Throws<ArgumentException>(() => P28IdleScenario.Create(Initial(), Enumerable.Range(0, 65).Select(i => new P28IdleCall(i, 52, 123)).ToArray(), "too many"));
        Assert.Throws<InvalidDataException>(() => P28IdleScenario.Parse(s.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1, \"formatVersion\": 1", StringComparison.Ordinal)));
    }
    [Fact]
    public void InspectorNeverUsesConfirmationAloneAndSeparatesTargetFromCommand()
    {
        var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(Image()); var r = P28IdleInspector.Inspect(im, profile, null, true); Assert.False(r.InterpretationApplied); Assert.Empty(r.Cells);
        r = P28IdleInspector.Inspect(im, profile, binding, true); Assert.True(r.InterpretationApplied); Assert.Equal(7, r.Cells.Count); Assert.Equal(0x68D2, r.Cells[2].ValueOffset); Assert.Equal(1333, r.Cells[2].RawValue); Assert.False(r.PhysicalRpmAvailable);
        Assert.Contains(r.Evidence, x => x.Contains("distinct", StringComparison.Ordinal));
        var other = im.CreateModifiedCopy([new BytePatch(300, [1])]); Assert.False(P28IdleInspector.Inspect(other, profile, binding, true).InterpretationApplied);
    }
    [Fact]
    public async Task RealRustNativeHandoffPersistsButToyCannotMasqueradeAsRecoveredModel()
    {
        var b = Image(); new byte[] { 0x03, 0x94, 0x58 }.CopyTo(b, 0x2FD1);
        new byte[] { 0xE4, 0x5C, 0x86, 1, 0, 0xD4, 0x5C, 0x03, 0xAB, 0x30 }.CopyTo(b, 0x5894);
        new byte[] { 0xE4, 0x5C, 0xD5, 0xCA, 0x03, 0xF4, 0x09 }.CopyTo(b, 0x9DC);
        var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(b); var s = Scenario(); var r = await P28IdleValidator.ExecuteAsync(im, profile, binding, true, ExecutionTestPaths.RustRunner, s);
        Assert.All(r.Images[0].Sequences, seq => { for (var i = 0; i < 3; i++) { var row = seq.Checkpoints[i]; Assert.Equal("Mismatch", row.Disposition); Assert.Equal(100 + i, row.ActualFinalTarget); Assert.Equal(100 + i, row.ActualError); Assert.NotNull(row.Expected); if (i > 0) Assert.Equal(seq.Checkpoints[i - 1].Expected!.After, row.Expected!.Before); } });
        Assert.Equal(b, im.ToArray());
    }
    [Fact]
    public async Task RealRustStrictUnresolvedHasNullTargetsAndTerminalSuffixAndRejectsTampering()
    {
        var b = Image(); b[0x2FD1] = 0x45; b[0x2FD2] = 0x81; var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(b); var s = Scenario();
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28IdleValidator.CreateRequest(im, s));
        var r = P28IdleValidator.AnalyzeImage(im, s, response, "A"); Assert.All(r.Sequences, seq => { Assert.Equal("Unresolved", seq.Checkpoints[0].Disposition); Assert.Null(seq.Checkpoints[0].ActualFinalTarget); Assert.Equal("NotRun", seq.Checkpoints[1].Disposition); Assert.Null(seq.Checkpoints[1].ActualError); });
        foreach (var edit in new Action<JsonNode>[] { n => n["runnerVersion"] = "0.8.0", n => n["entryContracts"]![0]!["budget"] = 129, n => n["idleSequences"]![0]!["checkpoints"]![1]!["actualTarget"] = 0, n => n["idleSequences"]![0]!["checkpoints"]![0]!["producer"]!["result"]!["usedAssumptions"] = new JsonArray("oki.add-er1-a") })
        {
            var n = JsonNode.Parse(response.Response.GetRawText())!; edit(n); Assert.Throws<SliceProcessException>(() => P28IdleValidator.AnalyzeImage(im, s, new(JsonSerializer.SerializeToElement(n), ""), "A"));
        }
        await Assert.ThrowsAsync<InvalidDataException>(() => P28IdleValidator.ExecuteAsync(im, profile, binding, false, "not-launched", s));
    }
    [Fact]
    public async Task IdleUsesBoundedTransportTimeoutAndCancellation()
    {
        var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(Image()); var configuration = new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", configuration, "net8.0", "HondaEcu.Slice.TestHost.dll"); Assert.True(File.Exists(host));
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(500) };
        var ex = await Assert.ThrowsAsync<SliceProcessException>(() => P28IdleValidator.ExecuteAsync(im, profile, binding, true, "dotnet", Scenario(), options)); Assert.Equal(SliceProcessFailure.Timeout, ex.Failure);
        using var ct = new CancellationTokenSource(500); await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28IdleValidator.ExecuteAsync(im, profile, binding, true, "dotnet", Scenario(), options with { Timeout = TimeSpan.FromSeconds(15) }, ct.Token));
    }
}
