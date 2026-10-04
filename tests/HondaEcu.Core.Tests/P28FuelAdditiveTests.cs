using System.Text.Json;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28FuelAdditiveTests
{
    private static P28FuelAdditiveSources Source(int signed = 0, int b1 = 0, int b2 = 0, int unsigned = 0, int factor = 512) => new((ushort)factor, (ushort)unsigned, 0, unchecked((ushort)signed), unchecked((byte)b1), unchecked((byte)b2), 0, 0, 0);
    internal static P28FuelAdditiveScenario Scenario() => P28FuelAdditiveScenario.Create(new(new(0, 0, 0, 0, 0, 0, 0xA5, 0), 0, 8),
        [new(0, 0, 0, 0, Source(-100)), new(1, 255, 255, 255, Source(-100))], "Invented software snapshots", [0]);
    [Fact]
    public void ClosedScenarioRejectsReadyCarriersOverlapsGatesAndUnboundedEvents()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28FuelAdditiveScenario.Parse(s.ToJson()).Digest);
        foreach (var change in new Action<JsonNode>[] {
            n=>n["calls"]![0]!["sources"]!["er3"]=1, n=>n["calls"]![0]!["sources"]!["x2"]=1,
            n=>n["calls"]![0]!["sources"]!["data0140"]=1,n=>n["calls"]![0]!["sources"]!["source0145"]=1,
            n=>n["calls"]![0]!["sources"]!["source0148"]=256,n=>n["calls"]![0]!["sources"]!["source0146"]=-1,
            n=>n["calls"]![0]!["sources"]!["source0144"]=256,
            n=>n["calls"]![0]!["expectedCorrection"]=1,n=>n["calls"]![0]!["mapId"]="map_1",
            n=>n["calls"]![0]!["pc"]=0x21F2,n=>n["calls"]![0]!["psw"]=0,
            n=>n["initialState"]!["callerGate0124"]=16,n=>n["initialState"]!["fuel"]!["consumerOutput0140"]=1,
            n=>n["formatVersion"]=2,n=>n["purpose"]="fuel-calculation-native-software-test",
            n=>n["calls"]![1]!["index"]=0,n=>n["traceCallIndexes"]=new JsonArray(0,0),n=>n["calls"]![0]!["sources"]=null })
        { var n = JsonNode.Parse(s.ToJson())!; change(n); Assert.ThrowsAny<Exception>(() => P28FuelAdditiveScenario.Parse(n.ToJsonString())); }
        Assert.Throws<ArgumentException>(() => P28FuelAdditiveScenario.Create(s.InitialState, Enumerable.Range(0, 65).Select(i => new P28FuelAdditiveCall(i, 0, 0, 0, Source())).ToArray(), "too many"));
        var request = JsonSerializer.SerializeToElement(P28FuelAdditiveValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Empty(request.GetProperty("allowAssumptions").EnumerateArray()); Assert.False(request.GetProperty("fuelAdditiveCorrectionChain").GetProperty("calls")[0].TryGetProperty("selector0127", out _));
    }
    [Fact]
    public void StagedSignedSaturationAndApplicationAreSeparateFromM2kSaturation()
    {
        var negative = P28FuelAdditiveModel.Project(65535, Source(-100, factor: 65535), 0, 0);
        Assert.True(negative.Scaling.Saturated); Assert.Equal(65435, negative.Corrected); // NOT clamp(wide product + correction)
        Assert.Equal(0, P28FuelAdditiveModel.Project(99, Source(-100), 0, 0).Corrected);
        Assert.Equal(0, P28FuelAdditiveModel.Project(100, Source(-100), 0, 0).Corrected);
        Assert.Equal(1, P28FuelAdditiveModel.Project(101, Source(-100), 0, 0).Corrected);
        Assert.Equal(65534, P28FuelAdditiveModel.Project(65534, Source(), 0, 0).Corrected);
        Assert.Equal(65535, P28FuelAdditiveModel.Project(65534, Source(1), 0, 0).Corrected);
        Assert.Equal(65535, P28FuelAdditiveModel.Project(65534, Source(2), 0, 0).Corrected);
        var staged = P28FuelAdditiveModel.Project(0, Source(32767, 127, -128), 0, 0);
        Assert.Equal(32639, staged.Correction); Assert.NotEqual(Math.Clamp(32767 + 127 - 128, -32768, 32767), staged.Correction);
        var gate = P28FuelAdditiveModel.Project(100, Source(20), 0, 32); Assert.Equal(0, gate.Store03a2); Assert.Equal(120, gate.Store03b4);
    }
    [Fact]
    public void FiniteSignedWordByteModelAuditIsNotNativeCoverage()
    {
        var count = 0;
        for (var signed = -32768; signed <= 32767; signed++) foreach (var delta in new[] { -128, -1, 0, 1, 127 })
            {
                var p = P28FuelAdditiveModel.Project(1234, Source(signed, delta), 0, 0);
                var expected = Math.Clamp(signed + delta, -32768, 32767); Assert.Equal(expected, p.SignedFirst); Assert.Equal(expected, p.Correction);
                Assert.Equal(Math.Clamp(1234 + expected, 0, 65535), p.Corrected); count++;
            }
        Assert.Equal(327680, count);
    }
    [Fact]
    public void IndependentInstructionPathsAgreeWithWideModelIncludingModeHistory()
    {
        foreach (var signed in new[] { -32768, -32767, -129, -128, -1, 0, 1, 127, 128, 32766, 32767 })
            foreach (var delta in new[] { -128, -1, 0, 1, 127 }) foreach (var unsigned in new[] { 0, 1, 99, 100, 32767, 65535 })
                    foreach (var mode in new byte[] { 0xA5, 0xAD })
                    {
                        var s = Source(signed, delta, -delta % 128, unsigned); var p = P28FuelAdditiveModel.Project(1234, s, mode, 0);
                        var producer = P28FuelAdditiveEvidence.Build(0, 1234, s, mode, 0, 1234, 0x0DC9, 123, 456, 789, 234, 999);
                        Assert.Equal(p.CorrectionWord, producer.Er3); Assert.Equal(p.ModeAfter, producer.Mode);
                        var scaling = P28FuelAdditiveEvidence.Build(1, 1234, s, mode, 0, producer.Accumulator, producer.Psw, producer.Er0, producer.Er1, producer.Er2, producer.Er3, 999);
                        Assert.Equal(p.CorrectionWord, scaling.Er3); Assert.Equal(p.Scaling.Output, scaling.Accumulator); Assert.Equal(p.Scaling.Output, scaling.Er2);
                        var app = P28FuelAdditiveEvidence.Build(2, 1234, s, mode, 0, scaling.Accumulator, scaling.Psw, scaling.Er0, scaling.Er1, scaling.Er2, scaling.Er3, 999);
                        Assert.Equal(p.Corrected, app.Accumulator); Assert.Equal(p.Scaling.Output, app.Er2); Assert.Equal(p.Corrected, app.Er3); Assert.Equal(999, app.Er0);
                        Assert.Equal(p.CorrectionWord, app.Events[0][3]); Assert.Equal(0x5958, app.Events[1][1]); Assert.Contains(app.Events, e => e[1] == 0x21F5);
                    }
        var first = Source(-100) with { Counter00f2 = 4 }; var a = P28FuelAdditiveModel.Project(100, first, 8, 0); var b = P28FuelAdditiveModel.Project(100, first, a.ModeAfter, 0);
        Assert.Equal(0, a.Correction); Assert.Equal(-100, b.Correction); Assert.Equal(0, a.ModeAfter);
    }
    [Fact]
    public void SameResultCannotHideForgedOperandsFlagsXchgOrReturn()
    {
        var s = Source(-100); var own = P28FuelAdditiveEvidence.Build(2, 1000, s, 0, 0, 1000, 0x5DC9, 512, 0, 1000, 65436, 77);
        var good = JsonSerializer.SerializeToElement(new { events = own.Events }); P28FuelAdditiveEvidence.RequireEventPrefix(good, own);
        foreach (var (index, field) in new[] { (0, 2), (0, 3), (1, 1), (2, 4), (own.Events.Count - 1, 3) })
        {
            var forged = JsonNode.Parse(good.GetRawText())!; forged["events"]![index]![field] = forged["events"]![index]![field]!.GetValue<int>() ^ 1;
            Assert.Throws<SliceProcessException>(() => P28FuelAdditiveEvidence.RequireEventPrefix(JsonSerializer.SerializeToElement(forged), own));
        }
    }
    [Fact]
    public void NativeSeamsRejectHostCarrierAndFlagReseeding()
    {
        var b = JsonSerializer.SerializeToNode(new { pc = 0x1350, accumulator = 123, psw = 0x5DC9, dd = true, lrb = 0x20, usp = 0x280, ssp = 0x7FE, x1 = 42, x2 = 0, dp = 357, registers = new[] { 1, 2, 3, 4, 5, 6, 7, 8 } })!;
        var entry = b.DeepClone(); entry["pc"] = 0x2194; entry["psw"] = 0x0DC9; entry["dd"] = false;
        var produced = entry.DeepClone(); produced["pc"] = 0x21DB; produced["x2"] = 65436;
        var row = new JsonObject
        {
            ["handoff1350"] = b.DeepClone(),
            ["tailBoundaries"] = new JsonArray(b.DeepClone(), b.DeepClone(), b.DeepClone(), b.DeepClone(), b.DeepClone()),
            ["boundaries"] = new JsonArray(entry.DeepClone(), produced.DeepClone(), produced.DeepClone(), produced.DeepClone()),
            ["hostTransitionWrites"] = JsonNode.Parse(P28FuelAdditiveValidator.ExpectedContracts()[0].GetProperty("hostTransitionWrites").GetRawText())
        };
        P28FuelAdditiveValidator.ValidateSeams(JsonSerializer.SerializeToElement(row));
        foreach (var key in new[] { "x2", "accumulator", "psw", "lrb", "ssp" })
        { var forged = row.DeepClone(); forged["boundaries"]![2]![key] = forged["boundaries"]![2]![key]!.GetValue<int>() ^ 1; Assert.Throws<SliceProcessException>(() => P28FuelAdditiveValidator.ValidateSeams(JsonSerializer.SerializeToElement(forged))); }
        row["boundaries"]![0]!["registers"]![6] = 99; Assert.Throws<SliceProcessException>(() => P28FuelAdditiveValidator.ValidateSeams(JsonSerializer.SerializeToElement(row)));
    }
    [Theory]
    [InlineData("0.19.0", "fuelAdditiveCorrectionChain")]
    [InlineData("0.20.0", "fuelCalculationChain")]
    [InlineData("0.20.0", "fuelAdditiveCorrectionChain")]
    public void CapabilityRejectsOldWrongTaskAndForgedFixes(string version, string operation)
    {
        var root = JsonSerializer.SerializeToElement(new { protocolVersion = 1, operation, runnerVersion = version, upstreamCommit = P28ByteExecutionValidator.UpstreamCommit, localSemanticFixes = Array.Empty<string>() });
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(root, P28FuelAdditiveValidator.Operation));
    }
    [Fact]
    public async Task NewOperationUsesBoundedTimeoutAndCancellation()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28IgnitionMapTests.InventedImage(true).ToArray());
        // Reuse a fully invented fuel layout admitted by its own exact test binding.
        var bytes = image.ToArray(); bytes[0x0A65] = 0x60; bytes[0x0A66] = 0; bytes[0x0A67] = 0x70;
        bytes[0x12FC] = 0x98; bytes[0x12FD] = 10; bytes[0x12FE] = 0x99; bytes[0x12FF] = 20; bytes[0x130C] = 0x60; bytes[0x130D] = 0x22; bytes[0x130E] = 0x71; bytes[0x1323] = 0x60; bytes[0x1324] = 0x50; bytes[0x1325] = 0x70;
        bytes[0x60E5] = 0; bytes[0x60F8] = 0;
        bytes[0x131A] = 0xE9; bytes[0x131B] = 0x27;
        bytes[0x12DF] = 0xC4; bytes[0x12E0] = 0x27; bytes[0x12E1] = 0x09; bytes[0x12F9] = 0xC4; bytes[0x12FA] = 0x27; bytes[0x12FB] = 0x19;
        (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(bytes);
        var configuration = new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", configuration, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(500) };
        var e = await Assert.ThrowsAsync<SliceProcessException>(() => P28FuelAdditiveValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options)); Assert.Equal(SliceProcessFailure.Timeout, e.Failure);
        using var cancellation = new CancellationTokenSource(500); await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28FuelAdditiveValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options with { Timeout = TimeSpan.FromSeconds(15) }, cancellation.Token));
    }
    [Fact]
    public async Task InventedNativeProductionVcalReturnAndConsumptionUseRealSubprocess()
    {
        // Newly composed program, no OEM routine: native7 and40*3, XCHG, ADD helper, word consumers.
        var main = new byte[] {0x67,5,0,0x86,2,0,0x8B,0x51,0x67,3,0,0x88,0x67,40,0,0x90,0x35,0x8A,0x47,0x10,0x14,
            0x62,0x60,3,0xD2,0x36,0x62,0x62,3,0xD2};
        var rom = new byte[256]; main.CopyTo(rom, 0x40); rom[0x30] = 0x80; rom[0x31] = 0; rom[0x80] = 0x0B; rom[0x81] = 1;
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "synthetic", rom = rom.Select(v => (int)v).ToArray() } },
            scratchPatterns = new[] { 170 },
            allowAssumptions = Array.Empty<string>(),
            synthetic = new { entryPc = 0x40, exitPcs = new[] { 0x40 + main.Length }, allowedCodeRanges = new[] { new[] { 0x40, 0x40 + main.Length }, new[] { 0x80, 0x82 } }, psw = 0x0101, lrb = 0x20, usp = 0x280, instructionBudget = 32, dataSeeds = Array.Empty<int[]>(), outputAddresses = new[] { 0x360, 0x361, 0x362, 0x363, 0x8A, 0x8B, 0x104, 0x105, 0x106, 0x107, 0x7FE, 0x7FF } }
        });
        var r = response.Response.GetProperty("syntheticResult"); Assert.Equal("0.31.0", response.Response.GetProperty("runnerVersion").GetString()); Assert.Equal(0, r.GetProperty("status").GetInt32());
        Assert.Equal(new[] { 127, 0, 120, 0, 7, 0, 120, 0, 120, 0, 0x55, 0 }, r.GetProperty("outputs").EnumerateArray().Select(v => v.GetInt32()));
        var trace = r.GetProperty("trace").EnumerateArray().ToArray(); Assert.Contains(trace, e => e.GetProperty("pc").GetInt32() == 0x54 && e.GetProperty("nextPc").GetInt32() == 0x80);
        Assert.Contains(trace, e => e.GetProperty("pc").GetInt32() == 0x81 && e.GetProperty("nextPc").GetInt32() == 0x55);
        Assert.Contains(trace, e => e.GetProperty("pc").GetInt32() == 0x58 && e.GetProperty("accumulator").GetInt32() == 127);
    }
}
