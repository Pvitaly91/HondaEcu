using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28DivisionDecisionTests
{
    internal static P28DivisionDecisionScenario Scenario()
    {
        var s = P28CommonResultConsumerTests.Scenario();
        return P28DivisionDecisionScenario.Create(s.InitialState, s.Calls, "Invented M2t source storage;no native JGT claim", [0]);
    }
    [Theory]
    [InlineData("dividend")]
    [InlineData("quotient")]
    [InlineData("remainder")]
    [InlineData("cf")]
    [InlineData("zf")]
    [InlineData("jgtOutcome")]
    [InlineData("data013bResult")]
    [InlineData("a")]
    [InlineData("er0")]
    [InlineData("er1")]
    [InlineData("er2")]
    [InlineData("pc")]
    [InlineData("ram")]
    [InlineData("formula")]
    [InlineData("branchTarget")]
    public void NoReadyOperandsResultsFlagsOrPerEventDivisor(string key)
    {
        foreach (var location in new[] { "calls", "softwareSources" })
        {
            var n = JsonNode.Parse(Scenario().ToJson())!;
            (location == "calls" ? n["calls"]![0]! : n["initialState"]!["softwareSources"]!)[key] = 1;
            Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(n.ToJsonString()));
        }
    }
    [Fact]
    public void ClosedScenarioIdentityAndDuplicateHandlingAreIndependentOfHistoricalM2s()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28DivisionDecisionScenario.Parse(s.ToJson()).Digest);
        Assert.ThrowsAny<Exception>(() => P28CommonResultConsumerScenario.Parse(s.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(P28CommonResultConsumerTests.Scenario().ToJson()));
        Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(s.ToJson().Replace("\"word0136\": 1", "\"word0136\": 1, \"word0136\": 2", StringComparison.Ordinal)));
        var n = JsonNode.Parse(s.ToJson())!; n["formatVersion"] = 2; Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(n.ToJsonString()));
        n = JsonNode.Parse(s.ToJson())!; n["calls"]![0]!["word0136"] = 2; Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(n.ToJsonString()));
    }
    private static (P28CommonResultConsumerOracle Own, JsonElement Fixture) Positive(int current = 700, int divisor = 37)
    {
        var (own, fixture) = P28CommonResultConsumerTests.Oracle(0, false, divisor, currentWord: current);
        var n = JsonNode.Parse(fixture.GetRawText())!;
        foreach (var (pc, name) in new[] { (0x232E, "CLR er0"), (0x2330, "MOV er2, off N8"), (0x2333, "DIV"), (0x2335, "JLT rel8"), (0x2337, "CMP A, #N16") })
        {
            var index = own.Machine.Events.ToList().FindIndex(e => e[0] == pc); n["stage"]!["result"]!["trace"]![index]!["instruction"] = name;
        }
        return (own, JsonSerializer.SerializeToElement(n));
    }
    [Theory]
    [InlineData(8, 1, 10)]
    [InlineData(9, 1, 11)]
    [InlineData(10, 1, 12)]
    [InlineData(700, 2, 437)]
    [InlineData(700, 37, 23)]
    [InlineData(700, 65535, 0)]
    public void ModelOnlyDivProofIsNotActualRomReachabilityOrStrictJgtClosure(int current, int divisor, int quotient)
    {
        var (own, good) = Positive(current, divisor);
        Assert.Equal(1, P28CommonResultConsumerValidator.ValidateSuffix(good, good.GetProperty("entry"), own).Status);
        var proof = P28DivisionDecisionValidator.Proof(good)!;
        Assert.Equal(quotient, proof.QuotientLow); Assert.Equal(0, proof.DividendHigh); Assert.Equal(0, proof.QuotientHigh);
        Assert.Equal(proof.DividendLow % divisor, proof.Remainder); Assert.False(proof.DivCf); Assert.Equal(quotient == 0, proof.DivZf);
        Assert.Equal(quotient < 11, proof.CmpCf); Assert.Equal(quotient == 11, proof.CmpZf);
        Assert.Null(proof.JgtDecision); Assert.Null(proof.FreshCalculationResult);
    }
    [Theory]
    [InlineData("host-quotient")]
    [InlineData("host-remainder")]
    [InlineData("host-er2")]
    [InlineData("missing232E")]
    [InlineData("wrong-divisor-width")]
    [InlineData("DIVB")]
    [InlineData("wrong-quotient-high")]
    [InlineData("wrong-quotient-low")]
    [InlineData("wrong-remainder-register")]
    [InlineData("wrong-div-CF")]
    [InlineData("wrong-ZF")]
    [InlineData("swapped-CMP")]
    [InlineData("forged-flags")]
    [InlineData("wrong-JGT-predicate")]
    [InlineData("right-result-wrong-branch")]
    [InlineData("PC-reset2333")]
    [InlineData("PC-reset233A")]
    [InlineData("hidden-assumption")]
    [InlineData("fake-continuation-div0")]
    public void RejectsCalculationProvenanceForgeriesEvenWithoutChangingFinalResult(string fault)
    {
        var (own, good) = Positive(); var n = JsonNode.Parse(good.GetRawText())!;
        var ev = own.Machine.Events.ToList(); var acc = own.Machine.Accesses.ToList();
        var div = ev.FindIndex(e => e[0] == 0x2333); var cmp = ev.FindIndex(e => e[0] == 0x2337);
        switch (fault)
        {
            case "host-quotient": n["hostQuotient"] = 23; break;
            case "host-remainder": n["hostRemainder"] = 24; break;
            case "host-er2": n["accesses"]!.AsArray().Add(new JsonArray(0, 0x104, 16, 1, 37)); break;
            case "missing232E": n["stage"]!["events"]!.AsArray().RemoveAt(ev.FindIndex(e => e[0] == 0x232E)); break;
            case "wrong-divisor-width": n["accesses"]![acc.FindIndex(a => a[0] == 0x2330 && a[3] == 0)]![2] = 8; break;
            case "DIVB": n["stage"]!["result"]!["trace"]![div]!["instruction"] = "DIVB"; break;
            case "wrong-quotient-high": n["accesses"]![acc.FindIndex(a => a[0] == 0x2333 && a[1] == 0x100 && a[3] == 1)]![4] = 1; break;
            case "wrong-quotient-low": n["stage"]!["events"]![div]![3] = 24; break;
            case "wrong-remainder-register": n["accesses"]![acc.FindIndex(a => a[0] == 0x2333 && a[1] == 0x102 && a[3] == 1)]![1] = 0x106; break;
            case "wrong-div-CF": n["stage"]!["events"]![div]![5] = ev[div][5] ^ 0x8000; break;
            case "wrong-ZF": n["stage"]!["events"]![div]![5] = ev[div][5] ^ 0x4000; break;
            case "swapped-CMP": n["stage"]!["events"]![cmp]![6] = 11; n["stage"]!["events"]![cmp]![7] = 23; break;
            case "forged-flags": n["exit"]!["psw"] = ev[cmp][5] ^ 0xC000; break;
            case "wrong-JGT-predicate": n["jgtPredicate"] = "OR"; break;
            case "right-result-wrong-branch": n["stage"]!["events"]![cmp]![1] = 0x2369; break;
            case "PC-reset2333": n["entry"]!["pc"] = 0x2333; break;
            case "PC-reset233A": n["entry"]!["pc"] = 0x233A; break;
            case "hidden-assumption": n["stage"]!["result"]!["usedAssumptions"] = new JsonArray("jgt-or"); break;
            case "fake-continuation-div0": own = P28CommonResultConsumerTests.Oracle(0, false, 0).Own; break;
        }
        Assert.ThrowsAny<Exception>(() =>
        {
            var forged = JsonSerializer.SerializeToElement(n);
            P28CommonResultConsumerValidator.ValidateSuffix(forged, good.GetProperty("entry"), own);
            P28DivisionDecisionValidator.Proof(forged);
        });
    }
    [Fact]
    public async Task OwnExecuteSeparatesTimeoutAndActiveCancellationWithoutOutput()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28AdaptiveFuelTests.Image());
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) };
        var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => P28DivisionDecisionValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options));
        Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
        using var cancelled = new CancellationTokenSource(); cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28DivisionDecisionValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options, cancelled.Token));
        var marker = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".pid");
        using var active = new CancellationTokenSource(); Process? child = null;
        try
        {
            var running = P28DivisionDecisionValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(),
                options with { Arguments = [host, "pid-sleep", marker], Timeout = TimeSpan.FromSeconds(15) }, active.Token);
            int? pid = null; var limit = Stopwatch.StartNew();
            while (limit.Elapsed < TimeSpan.FromSeconds(8))
            {
                if (File.Exists(marker)) { try { if (int.TryParse(await File.ReadAllTextAsync(marker), out var value) && value > 0) { pid = value; break; } } catch (IOException) { } }
                await Task.Delay(20);
            }
            Assert.True(pid.HasValue, "Active M2t child must publish its PID before cancellation.");
            child = Process.GetProcessById(pid.Value); Assert.False(child.HasExited);
            active.Cancel(); await Assert.ThrowsAnyAsync<OperationCanceledException>(() => running);
            await child.WaitForExitAsync(); Assert.True(child.HasExited);
        }
        finally
        {
            active.Cancel(); if (child is not null) { if (!child.HasExited) child.Kill(entireProcessTree: true); child.Dispose(); }
            for (var i = 0; File.Exists(marker) && i < 10; i++) { try { File.Delete(marker); } catch (IOException) when (i < 9) { await Task.Delay(50); } }
        }
    }
    [Fact]
    public async Task RealInventedProcessRefusesHistoricalIdentityWrongTaskAndTerminalChanges()
    {
        var s = Scenario(); var image = RomImage.FromBytes(P28AdaptiveFuelTests.Image());
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28DivisionDecisionValidator.CreateRequest(image, s));
        var seq = P28DivisionDecisionValidator.Analyze(image, s, response.Response, "A");
        Assert.All(seq, x => { Assert.Equal("PrefixUnresolved", x.Checkpoints[0].Disposition); Assert.Equal("NotRun", x.Checkpoints[1].Disposition); Assert.Null(x.Checkpoints[0].Division); });
        foreach (var edit in new Action<JsonNode>[] {
            n => n["runnerVersion"] = "0.27.0", n => n["operation"] = "fuelCommonResultConsumerChain",
            n => n["entryContracts"]![0]!["jgtPredicate"] = "AND",
            n => n["divisionDecisionSequences"]![0]!["checkpoints"]![0]!["softwareResult13b"] = 91,
            n => n["divisionDecisionSequences"]![0]!["checkpoints"]![1]!["stateAfter"]!["word0136"] = 99,
            n => n["divisionDecisionSequences"]![0]!["checkpoints"]![1]!["commonConsumer"] = new JsonObject()
        }) { var n = JsonNode.Parse(response.Response.GetRawText())!; edit(n); Assert.ThrowsAny<Exception>(() => P28DivisionDecisionValidator.Analyze(image, s, JsonSerializer.SerializeToElement(n), "A")); }
        var request = JsonNode.Parse(JsonSerializer.Serialize(P28DivisionDecisionValidator.CreateRequest(image, s), JsonDefaults.Create()))!;
        request["operation"] = "fuelCommonResultConsumerChain";
        await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, request));
    }
}
