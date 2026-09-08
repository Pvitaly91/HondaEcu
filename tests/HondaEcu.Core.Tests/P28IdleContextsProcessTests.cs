using System.Text.Json;
using System.Text.Json.Nodes;
using static HondaEcu.Core.Tests.P28IdleContextsTests;
namespace HondaEcu.Core.Tests;
public sealed class P28IdleContextsProcessTests
{
    [Fact]
    public async Task BudgetKeepsFullEventsBeyondTracePrefixAndNullTerminalOutputs()
    {
        var bytes = Image(); new byte[] { 0x03, 0xD1, 0x2F }.CopyTo(bytes, 0x2FD1);
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(bytes);
        var report = await P28IdleContextsValidator.ExecuteAsync(image, profile, binding, true, ExecutionTestPaths.RustRunner, Scenario());
        foreach (var sequence in report.Images[0].Sequences)
        {
            var row = sequence.Checkpoints[0]; Assert.Equal("BudgetExceeded", row.Disposition); Assert.Null(row.ActualFinalTarget);
            var stage = row.Actual.GetProperty("producer"); Assert.Equal(256, stage.GetProperty("events").GetArrayLength());
            Assert.Equal(128, stage.GetProperty("result").GetProperty("trace").GetArrayLength());
            Assert.Equal("NotRun", sequence.Checkpoints[1].Disposition); Assert.Null(sequence.Checkpoints[1].Expected);
        }
    }
    [Fact]
    public async Task RealRustNativeHandoffPersistsButToyCannotMasqueradeAsRecoveredModel()
    {
        var b = Image(); new byte[] { 0x03, 0x94, 0x58 }.CopyTo(b, 0x2FD1);
        new byte[] { 0xE4, 0x5C, 0x86, 1, 0, 0xD4, 0x5C, 0x03, 0xAB, 0x30 }.CopyTo(b, 0x5894);
        new byte[] { 0xE4, 0x5C, 0xD5, 0xCA, 0x03, 0xF4, 0x09 }.CopyTo(b, 0x9DC);
        var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(b); var s = Scenario(); var r = await P28IdleContextsValidator.ExecuteAsync(im, profile, binding, true, ExecutionTestPaths.RustRunner, s);
        Assert.All(r.Images[0].Sequences, seq => { for (var i = 0; i < 3; i++) { var row = seq.Checkpoints[i]; Assert.Equal("Mismatch", row.Disposition); Assert.Equal(100 + i, row.ActualFinalTarget); Assert.Equal(100 + i, row.ActualError); Assert.NotNull(row.Expected); if (i > 0) Assert.Equal(seq.Checkpoints[i - 1].Expected!.After, row.Expected!.Before); } });
        Assert.Equal(b, im.ToArray());
    }
    [Fact]
    public async Task RealRustStrictUnresolvedHasNullTargetsAndTerminalSuffixAndRejectsTampering()
    {
        var b = Image(); b[0x2FD1] = 0x45; b[0x2FD2] = 0x81; var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(b); var s = Scenario();
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28IdleContextsValidator.CreateRequest(im, s));
        var r = P28IdleContextsValidator.AnalyzeImage(im, s, response, "A"); Assert.All(r.Sequences, seq => { Assert.Equal("Unresolved", seq.Checkpoints[0].Disposition); Assert.Null(seq.Checkpoints[0].ActualFinalTarget); Assert.Equal("NotRun", seq.Checkpoints[1].Disposition); Assert.Null(seq.Checkpoints[1].ActualError); });
        foreach (var edit in new Action<JsonNode>[] { n => n["runnerVersion"] = "0.8.0", n => n["entryContracts"]![0]!["budget"] = 129, n => n["idleContextSequences"]![0]!["checkpoints"]![1]!["actualTarget"] = 0, n => n["idleContextSequences"]![0]!["checkpoints"]![0]!["producer"]!["result"]!["usedAssumptions"] = new JsonArray("oki.add-er1-a") })
        {
            var n = JsonNode.Parse(response.Response.GetRawText())!; edit(n); Assert.Throws<SliceProcessException>(() => P28IdleContextsValidator.AnalyzeImage(im, s, new(JsonSerializer.SerializeToElement(n), ""), "A"));
        }
        await Assert.ThrowsAsync<InvalidDataException>(() => P28IdleContextsValidator.ExecuteAsync(im, profile, binding, false, "not-launched", s));
    }
    [Fact]
    public async Task IdleUsesBoundedTransportTimeoutAndCancellation()
    {
        var (im, profile, binding) = P28AcquisitionValidatorTests.Fixture(Image()); var configuration = new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", configuration, "net8.0", "HondaEcu.Slice.TestHost.dll"); Assert.True(File.Exists(host));
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(500) };
        var ex = await Assert.ThrowsAsync<SliceProcessException>(() => P28IdleContextsValidator.ExecuteAsync(im, profile, binding, true, "dotnet", Scenario(), options)); Assert.Equal(SliceProcessFailure.Timeout, ex.Failure);
        using var ct = new CancellationTokenSource(500); await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28IdleContextsValidator.ExecuteAsync(im, profile, binding, true, "dotnet", Scenario(), options with { Timeout = TimeSpan.FromSeconds(15) }, ct.Token));
    }
}
