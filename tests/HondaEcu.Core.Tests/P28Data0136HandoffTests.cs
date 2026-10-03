using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28Data0136HandoffTests
{
    internal static P28Data0136HandoffScenario Scenario(bool mode1 = false)
    {
        var old = P28PostSelectionCriticalTests.Scenario();
        return P28Data0136HandoffScenario.Create(new(new(0, 0, 164, 8, [11, 22, 33, 44, 55, 66]), mode1 ? (byte)164 : (byte)160, old.InitialState, new(0, false, 200, false, 91, 0)),
            [new(0, 12, 0, 0, 0, mode1 ? (ushort)12 : null), new(1, 24, 0, 0, 5, mode1 ? (ushort)24 : null)], old.Calls, "Invented model-only pairing; no OEM bytes", [0]);
    }
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void ClosedUnifiedSchemaAndRequestHaveNoReadyWordAndOne011fOwner(bool mode1)
    {
        var s = Scenario(mode1); Assert.Equal(s.Digest, P28Data0136HandoffScenario.Parse(s.ToJson()).Digest);
        var request = JsonSerializer.SerializeToElement(P28Data0136HandoffValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal(P28Data0136HandoffValidator.Operation, request.GetProperty("operation").GetString());
        var initial = request.GetProperty("data0136DivisionHandoff").GetProperty("unifiedInitialState");
        Assert.False(initial.GetProperty("producer").TryGetProperty("history0136", out _)); Assert.False(initial.GetProperty("softwareSources").TryGetProperty("word0136", out _));
        var producer = new P28Data0136TechnicalProducerModel(P28Data0136HandoffScenario.TechnicalInitial(s.UnifiedInitialState, 85), 85);
        var model = new P28CommonResultConsumerHistory(RomImage.FromBytes(P28AdaptiveFuelTests.Image()), s.ModelScenario(85), 85);
        var a = producer.Run(s.ProducerObservations[0]); model.AcceptModeledProducerGeneration((ushort)producer.Word(0x136), s.UnifiedInitialState.Data011f);
        Assert.Equal(mode1 ? 2 : 12, model.ModeledState.Word0136); Assert.Equal(s.UnifiedInitialState.Data011f, model.ModeledState.Byte011f);
        var b = producer.Run(s.ProducerObservations[1]); Assert.Equal(a.Writes.Single(w => w[0] == 0x136)[2], b.Writes.Single(w => w[0] == 0x136)[2]);
    }
    [Theory]
    [InlineData("word0136")]
    [InlineData("data0136")]
    [InlineData("history0136")]
    [InlineData("er2")]
    [InlineData("dividend")]
    [InlineData("quotient")]
    [InlineData("remainder")]
    [InlineData("jgtDecision")]
    [InlineData("writerPc")]
    [InlineData("generation")]
    [InlineData("pc")]
    [InlineData("ram")]
    [InlineData("branch")]
    [InlineData("formula")]
    [InlineData("data011f")]
    [InlineData("data0128")]
    [InlineData("counter00ae")]
    public void RejectReadyResultsAliasesAndPerEventOwners(string field)
    {
        foreach (var path in new[] { "producerObservations", "fuelCalls" }) { var n = JsonNode.Parse(Scenario().ToJson())!; n[path]![0]![field] = 1; Assert.ThrowsAny<Exception>(() => P28Data0136HandoffScenario.Parse(n.ToJsonString())); }
        var initial = JsonNode.Parse(Scenario().ToJson())!; initial["unifiedInitialState"]!["softwareSources"]![field] = 1; Assert.ThrowsAny<Exception>(() => P28Data0136HandoffScenario.Parse(initial.ToJsonString()));
    }
    [Fact]
    public void PairingBoundsDuplicatesAndModeSourcesAreClosed()
    {
        var s = Scenario(); Assert.Throws<ArgumentException>(() => P28Data0136HandoffScenario.Create(s.UnifiedInitialState, s.ProducerObservations.Take(1).ToArray(), s.FuelCalls, s.Provenance));
        var n = JsonNode.Parse(s.ToJson())!; n["unifiedInitialState"]!["data011f"] = 164; Assert.ThrowsAny<Exception>(() => P28Data0136HandoffScenario.Parse(n.ToJsonString()));
        Assert.ThrowsAny<Exception>(() => P28Data0136HandoffScenario.Parse(s.ToJson().Replace("\"data011f\": 160", "\"data011f\": 160, \"data011f\": 164", StringComparison.Ordinal)));
        n = JsonNode.Parse(s.ToJson())!; n["traceEventIndexes"] = new JsonArray(0, 0); Assert.ThrowsAny<Exception>(() => P28Data0136HandoffScenario.Parse(n.ToJsonString()));
    }
    private static JsonNode Ledger(int value = 12)
    {
        // Fabricated protocol guard data, not native ROM execution or a public firmware fixture.
        return JsonSerializer.SerializeToNode(new
        {
            index = 1,
            machineId = 1,
            producer = new { accesses = new[] { new[] { 0x5707, 0x136, 16, 1, value } } },
            fuelPrefix = (object?)null,
            calculation = new { accesses = (value == 0 ? new[] { new[] { 0x2330, 0x136, 16, 0, value }, new[] { 0x2330, 0x104, 16, 1, value } } : new[] { new[] { 0x2330, 0x136, 16, 0, value }, new[] { 0x2330, 0x104, 16, 1, value }, new[] { 0x2333, 0x104, 16, 0, value } }) },
            continuityJournal = (value == 0 ? new[] { new[] { 0, 65536, 0x96, 16, 1, 0x280 }, new[] { 0, 65536, 0xA2, 8, 1, 0 }, new[] { 1, 0x5707, 0x136, 16, 1, value }, new[] { 1, 0x2330, 0x136, 16, 0, value }, new[] { 1, 0x2330, 0x104, 16, 1, value } } :
                new[] { new[] { 0, 65536, 0x96, 16, 1, 0x280 }, new[] { 0, 65536, 0xA2, 8, 1, 0 }, new[] { 1, 0x5707, 0x136, 16, 1, value }, new[] { 1, 0x2330, 0x136, 16, 0, value }, new[] { 1, 0x2330, 0x104, 16, 1, value }, new[] { 1, 0x2333, 0x104, 16, 0, value } })
        })!;
    }
    private static void Check(JsonNode n, P28Data0136Generation? consumed = null, int value = 12)
    {
        var g = new P28Data0136Generation(0x5707, 1, 0, value);
        P28Data0136HandoffValidator.ValidateContinuity(JsonSerializer.SerializeToElement(n), g, consumed ?? g, new(1, 12, 0, 0, 0), false);
    }
    [Fact]
    public void SameValueNewGenerationAndZeroAreSuccessfulProvenanceNotCalculationCompletion() { Check(Ledger()); Check(Ledger(0), value: 0); }
    [Theory]
    [InlineData("second-machine")]
    [InlineData("host-word")]
    [InlineData("host-low-byte")]
    [InlineData("host-high-byte")]
    [InlineData("overlap-word")]
    [InlineData("wrong-writer")]
    [InlineData("stale-same-value")]
    [InlineData("byte-reader")]
    [InlineData("er2-width")]
    [InlineData("er2-overwrite")]
    [InlineData("hidden-initializer")]
    [InlineData("011f-rewrite")]
    [InlineData("mode-change")]
    [InlineData("missing-producer-journal")]
    [InlineData("injected-divisor")]
    [InlineData("zero-div")]
    [InlineData("positive-jgt")]
    [InlineData("reordered-journal")]
    public void FullJournalRejectsProvenanceForgeriesEvenWithCorrectValue(string fault)
    {
        var value = fault == "zero-div" ? 0 : 12; var n = Ledger(value); Check(n, value: value); var j = n["continuityJournal"]!.AsArray();
        switch (fault)
        {
            case "second-machine": n["machineId"] = 2; break;
            case "stale-same-value": Assert.ThrowsAny<Exception>(() => Check(n, new(0x5707, 0, 0, 12))); return;
            case "host-word": j.Insert(3, new JsonArray(0, 65536, 0x136, 16, 1, 12)); break;
            case "host-low-byte": j.Insert(3, new JsonArray(0, 65536, 0x136, 8, 1, 12)); break;
            case "host-high-byte": j.Insert(3, new JsonArray(0, 65536, 0x137, 8, 1, 0)); break;
            case "overlap-word": j.Insert(3, new JsonArray(1, 0x180, 0x135, 16, 1, 12)); break;
            case "wrong-writer": n["producer"]!["accesses"]![0]![0] = 0x56F3; j[2]![1] = 0x56F3; break;
            case "byte-reader": n["calculation"]!["accesses"]![0]![2] = 8; j[3]![3] = 8; break;
            case "er2-width": n["calculation"]!["accesses"]![1]![2] = 8; j[4]![3] = 8; break;
            case "er2-overwrite": j.Insert(5, new JsonArray(0, 65536, 0x104, 16, 1, 12)); break;
            case "hidden-initializer": j.Insert(3, new JsonArray(0, 65536, 0x350, 8, 1, 85)); break;
            case "011f-rewrite": case "mode-change": j.Insert(3, new JsonArray(0, 65536, 0x11F, 8, 1, 160)); break;
            case "missing-producer-journal": n["producer"]!["accesses"] = new JsonArray(); j.RemoveAt(2); break;
            case "injected-divisor": n["calculation"]!["accesses"]![2]![4] = 13; j[5]![5] = 13; break;
            case "zero-div": n["calculation"]!["accesses"]!.AsArray().Add(new JsonArray(0x2333, 0x104, 16, 0, 0)); j.Add(new JsonArray(1, 0x2333, 0x104, 16, 0, 0)); break;
            case "positive-jgt": n["calculation"]!["accesses"]!.AsArray().Add(new JsonArray(0x233A, 0x104, 16, 0, 12)); j.Add(new JsonArray(1, 0x233A, 0x104, 16, 0, 12)); break;
            case "reordered-journal": var copy = j[2]!.DeepClone(); j.RemoveAt(2); j.Add(copy); break;
        }
        Assert.ThrowsAny<Exception>(() => Check(n, value: value));
    }
    [Theory]
    [InlineData("quotient")]
    [InlineData("injected-divisor")]
    [InlineData("zero-div")]
    [InlineData("jgt")]
    public void ReusedIndependentCalculationOracleRejectsArithmeticAndBranchForgeries(string fault)
    {
        var (own, good) = P28CommonResultConsumerTests.Oracle(0, false, fault == "zero-div" ? 0 : 12); var n = JsonNode.Parse(good.GetRawText())!;
        Assert.Equal(1, P28CommonResultConsumerValidator.ValidateSuffix(good, good.GetProperty("entry"), own).Status);
        if (fault == "quotient") n["exit"]!["accumulator"] = 7;
        else if (fault == "injected-divisor") n["accesses"]!.AsArray().Single(a => a![0]!.GetValue<int>() == 0x2333 && a[1]!.GetValue<int>() == 0x104)![4] = 13;
        else { n["stage"]!["events"]!.AsArray().Add(new JsonArray(fault == "zero-div" ? 0x2333 : 0x233A, 0x233D, 0, 0, 0, 0)); n["stage"]!["result"]!["steps"] = own.Machine.Events.Count + 1; }
        Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerValidator.ValidateSuffix(JsonSerializer.SerializeToElement(n), good.GetProperty("entry"), own));
    }
    [Fact]
    public async Task UnsupportedInventedProducerIsTerminalAndNoDownstreamOrInputsRun()
    {
        var s = Scenario(); var image = RomImage.FromBytes(new byte[32768]); var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28Data0136HandoffValidator.CreateRequest(image, s));
        var report = P28Data0136HandoffValidator.Analyze(image, "invented", s, response.Response); Assert.True(report.HasFailure); Assert.Equal("Partial", report.TechnicalScheduledHandoff);
        foreach (var seq in report.Sequences) { Assert.Equal("ProducerPartial", seq.Checkpoints[0].Disposition); Assert.Equal("NotRun", seq.Checkpoints[1].Disposition); Assert.Null(seq.Checkpoints[0].ReaderGeneration); }
        foreach (var edit in new Action<JsonNode>[] {n=>n["runnerVersion"]="0.29.0",n=>n["data0136HandoffSequences"]![0]!["machineInstances"]=2,
            n=>n["data0136HandoffSequences"]![0]!["checkpoints"]![1]!["canaries"]![0]=1,n=>n["data0136HandoffSequences"]![0]!["checkpoints"]![1]!["continuityJournal"]=new JsonArray(new JsonArray(0,65536,0xA2,8,1,5))})
        {
            var n = JsonNode.Parse(response.Response.GetRawText())!; edit(n); Assert.ThrowsAny<Exception>(() => P28Data0136HandoffValidator.Analyze(image, "invented", s, JsonSerializer.SerializeToElement(n)));
        }
    }
    [Fact]
    public async Task TimeoutAndCancellationCannotPublishAnExecutedHandoff()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28AdaptiveFuelTests.Image());
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) };
        var ex = await Assert.ThrowsAsync<SliceProcessException>(() => P28Data0136HandoffValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options)); Assert.Equal(SliceProcessFailure.Timeout, ex.Failure);
        using var cancel = new CancellationTokenSource(); cancel.Cancel(); await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28Data0136HandoffValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options, cancel.Token));
    }
}
