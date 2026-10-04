using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28QuartetHandoffTests
{
    internal static P28QuartetHandoffScenario Scenario()
    {
        var old = P28PostSelectionCriticalTests.Scenario();
        return P28QuartetHandoffScenario.Create(new(old.InitialState, false), old.Calls.Select((c, i) => new P28QuartetHandoffCall(c, (byte)(i % 4))).ToArray(), "Invented software-only model sources;no OEM bytes", [0]);
    }
    [Fact]
    public void ClosedScenarioAndRequestContainNoReadyQuartetOrResult()
    {
        var s = Scenario(); Assert.Equal(s.Digest, P28QuartetHandoffScenario.Parse(s.ToJson()).Digest);
        var r = JsonSerializer.SerializeToElement(P28QuartetHandoffValidator.CreateRequest(RomImage.FromBytes(new byte[32768]), s), JsonDefaults.Create());
        Assert.Equal(P28QuartetHandoffValidator.Operation, r.GetProperty("operation").GetString()); Assert.False(r.GetProperty("quartetConsumerHandoff").GetProperty("initialState").TryGetProperty("word0196", out _));
    }
    [Theory]
    [InlineData("quartet")]
    [InlineData("03B6")]
    [InlineData("word0196")]
    [InlineData("x1")]
    [InlineData("selectedAddress")]
    [InlineData("selectedValue")]
    [InlineData("sum")]
    [InlineData("pc")]
    [InlineData("ram")]
    [InlineData("branch")]
    [InlineData("companionWords03be")]
    [InlineData("injectorIndex")]
    [InlineData("machine")]
    [InlineData("irqFrame")]
    public void ReadyFieldsAndHiddenOwnersAreRefused(string field)
    {
        var n = JsonNode.Parse(Scenario().ToJson())!; n["calls"]![0]![field] = 1; Assert.ThrowsAny<Exception>(() => P28QuartetHandoffScenario.Parse(n.ToJsonString()));
        n = JsonNode.Parse(Scenario().ToJson())!; n["initialState"]![field] = 1; Assert.ThrowsAny<Exception>(() => P28QuartetHandoffScenario.Parse(n.ToJsonString()));
    }
    [Theory]
    [InlineData(4)]
    [InlineData(64)]
    [InlineData(128)]
    [InlineData(255)]
    public void UnsafeIndexAndSignedOrOverflowDomainsRefused(int value)
    { Assert.ThrowsAny<Exception>(() => P28QuartetHandoffModel.Select((byte)value)); var n = JsonNode.Parse(Scenario().ToJson())!; n["calls"]![0]!["selector013c"] = value; Assert.ThrowsAny<Exception>(() => P28QuartetHandoffScenario.Parse(n.ToJsonString())); }
    [Theory]
    [InlineData(0, 0x3B6, 0x3BE)]
    [InlineData(1, 0x3B8, 0x3C0)]
    [InlineData(2, 0x3BA, 0x3C2)]
    [InlineData(3, 0x3BC, 0x3C4)]
    public void InventedDifferentAndEqualQuartetsProveAddressesNotJustNumbers(int selector, int address, int companion)
    {
        var m = P28QuartetHandoffModel.Select((byte)selector); Assert.Equal(address, m.SelectedAddress); Assert.Equal(companion, m.CompanionAddress); Assert.Equal(2 * selector, m.X1);
        foreach (var words in new[] { new[] { 17, 258, 4097, 65530 }, new[] { 321, 321, 321, 321 } })
        { var o = Oracle(selector, words); var read = o.Accesses.Single(a => a[0] == 0x5DF && a[1] == address); Assert.Equal(words[selector], read[4]); Assert.Equal(words[selector], o.A); Assert.Equal(0x5ED, o.Stop); }
        Assert.Equal((ushort)65535, P28QuartetHandoffModel.Result(65530, 99)); Assert.Equal((ushort)321, P28QuartetHandoffModel.Result(321, 0));
    }
    private static Dictionary<int, int> Ram() => new() { [0x90] = 85 * 257, [0x92] = 85 * 257, [0x19B] = 85, [0x19D] = 85, [0x19F] = 85, [0x196] = 321, [0x3BE] = 99, [0x3C0] = 123, [0x3C2] = 456, [0x3C4] = 65535 };
    private static P28QuartetOracle Oracle(int selector = 0, int[]? words = null) => P28QuartetHandoffEvidence.Build(1234, (byte)selector, 0, 0, 0, words ?? [321, 321, 321, 321], Ram());
    [Fact]
    public void AlternatePartialAndGatesDoNotPretendToReadQuartet()
    {
        var partial = P28QuartetHandoffEvidence.Build(1234, 3, 0, 16, 0, [1, 2, 3, 4], Ram()); Assert.Equal(0x5AF, partial.Stop); Assert.DoesNotContain(partial.Accesses, a => a[0] == 0x5DF || a[1] == 0x196);
        foreach (var gate in new[] { (16, 0), (0, 2) }) { var o = P28QuartetHandoffEvidence.Build(1234, 3, (byte)gate.Item1, 0, (byte)gate.Item2, [1, 2, 3, 4], Ram()); Assert.Equal(0, o.A); Assert.Contains(o.Accesses, a => a[0] == 0x5EB && a[1] == 0x196 && a[3] == 1); Assert.DoesNotContain(o.Accesses, a => a[0] == 0x5DF); }
    }
    private static JsonNode Ledger()
    {
        var native = new[] { new[] { 0x22A5, 0x3B6, 16, 1, 321 }, new[] { 0x22A8, 0x3B8, 16, 1, 321 }, new[] { 0x22AB, 0x3BA, 16, 1, 321 }, new[] { 0x22AE, 0x3BC, 16, 1, 321 }, new[] { 0x5DF, 0x90, 16, 0, 0 }, new[] { 0x5DF, 0x3B6, 16, 0, 321 } };
        return JsonSerializer.SerializeToNode(new { index = 1, machineId = 1, continuityJournal = native.Select(a => new[] { 1 }.Concat(a).ToArray()).ToArray() })!;
    }
    private static void Check(JsonNode n, P28QuartetGeneration? g = null)
    {
        var expected = new[] { new[] { 0x22A5, 0x3B6, 16, 1, 321 }, new[] { 0x22A8, 0x3B8, 16, 1, 321 }, new[] { 0x22AB, 0x3BA, 16, 1, 321 }, new[] { 0x22AE, 0x3BC, 16, 1, 321 }, new[] { 0x5DF, 0x90, 16, 0, 0 }, new[] { 0x5DF, 0x3B6, 16, 0, 321 } };
        P28QuartetHandoffValidator.ValidateJournal(JsonSerializer.SerializeToElement(n), expected, [], 0x3B6, g ?? new(0x22A5, 1, 0, 321));
    }
    [Theory]
    [InlineData("second-machine")]
    [InlineData("host-quartet")]
    [InlineData("host-x1")]
    [InlineData("host0196")]
    [InlineData("stale")]
    [InlineData("neighbor-generation")]
    [InlineData("wrong-slot")]
    [InlineData("wrong-width")]
    [InlineData("hidden-rewrite")]
    [InlineData("forged-address")]
    [InlineData("second-reader")]
    [InlineData("wrong-order")]
    public void EqualNumbersCannotHideProvenanceForgeries(string fault)
    {
        var n = Ledger(); Check(n); var j = n["continuityJournal"]!.AsArray();
        switch (fault)
        {
            case "second-machine": n["machineId"] = 2; break;
            case "stale": Assert.ThrowsAny<Exception>(() => Check(n, new(0x22A5, 0, 0, 321))); return;
            case "neighbor-generation": Assert.ThrowsAny<Exception>(() => Check(n, new(0x22A8, 1, 1, 321))); return;
            case "host-quartet": j.Insert(4, new JsonArray(0, 65536, 0x3B6, 16, 1, 321)); break;
            case "host-x1": j.Insert(4, new JsonArray(0, 65536, 0x90, 16, 1, 0)); break;
            case "host0196": j.Add(new JsonArray(0, 65536, 0x196, 16, 1, 321)); break;
            case "wrong-width": j[5]![3] = 8; break;
            case "wrong-slot": case "forged-address": j[5]![2] = 0x3B8; break;
            case "hidden-rewrite": j.Insert(4, new JsonArray(1, 123, 0x3B7, 8, 1, 1)); break;
            case "second-reader": j.Add(j[5]!.DeepClone()); break;
            case "wrong-order": var copy = j[0]!.DeepClone(); j.RemoveAt(0); j.Insert(1, copy); break;
        }
        Assert.ThrowsAny<Exception>(() => Check(n));
    }
    [Fact]
    public void OldRunnerInventoryCannotExecuteQuartetOperation()
    {
        var root = JsonSerializer.SerializeToElement(new { runnerVersion = "0.30.0" }); Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(root, P28QuartetHandoffValidator.Operation));
    }
    private static JsonNode ConsumerFixture(P28QuartetOracle own, int count = -1)
    {
        if (count < 0) count = own.Events.Count; var e = own.Events.Take(count).ToArray(); var a = own.Accesses.Take(own.AccessEnds[count - 1]).ToArray(); var ptr = own.PointerEnds[count - 1];
        object Boundary(int pc, int value, int psw, int x1, int x2) => new { pc, accumulator = value, psw, dd = (psw & 0x1000) != 0, lrb = 0x21, x1, x2, dp = 85 * 257, usp = 85 * 257, ssp = 0x7FE, registers = Enumerable.Repeat(85, 8).ToArray() };
        return JsonSerializer.SerializeToNode(new
        {
            entry = Boundary(0x584, 1234, 0x1DCA, 85 * 257, 85 * 257),
            exit = Boundary(e[^1][1], e[^1][3], e[^1][5], ptr[0], ptr[1]),
            accesses = a,
            stage = new
            {
                events = e,
                writes = a.Where(a => a[3] == 1).Select(a => new[] { a[1], a[2], a[4] }).ToArray(),
                sspAfter = 0x7FE,
                result = new { status = count == own.Events.Count ? 0 : 1, usedAssumptions = Array.Empty<string>(), steps = count, stopPc = e[^1][1], outputs = Array.Empty<int>(), programReads = Array.Empty<int>(), trace = e.Select(e => new { pc = e[0], nextPc = e[1], instruction = "invented model observation", psw = e[5], accumulator = e[3] }).ToArray(), error = count == own.Events.Count ? null : "invented partial", executedInstructionBytes = e.SelectMany((e, n) => Enumerable.Range(e[0], own.Lengths[n])).Distinct().Order().ToArray() }
            }
        })!;
    }
    private static void CheckConsumer(JsonNode n, P28QuartetOracle own) => P28QuartetHandoffValidator.ValidateConsumer(JsonSerializer.SerializeToElement(n), JsonSerializer.SerializeToElement(new { pc = 0x22B1, accumulator = 1234 }), own, Ram(), 85);
    [Theory]
    [InlineData("wrong-slot")]
    [InlineData("wrong-width")]
    [InlineData("companion-index")]
    [InlineData("companion-width")]
    [InlineData("swap-operands")]
    [InlineData("wrong-arithmetic")]
    [InlineData("wrong-flags")]
    [InlineData("host-x1")]
    [InlineData("fake-frame")]
    [InlineData("rti")]
    [InlineData("false-completion")]
    [InlineData("hidden-rewrite")]
    [InlineData("wrong-entry")]
    public void Correct0196CannotHideWrongNativePath(string fault)
    {
        var own = Oracle(); var n = ConsumerFixture(own); CheckConsumer(n, own); var a = n["accesses"]!.AsArray(); var selected = a.Single(a => a![0]!.GetValue<int>() == 0x5DF && a[1]!.GetValue<int>() == 0x3B6)!; var companion = a.Single(a => a![0]!.GetValue<int>() == 0x5E2 && a[1]!.GetValue<int>() == 0x3BE)!;
        switch (fault)
        {
            case "wrong-slot": selected[1] = 0x3B8; break;
            case "wrong-width": selected[2] = 8; break;
            case "companion-index": companion[1] = 0x3C0; break;
            case "companion-width": companion[2] = 8; break;
            case "swap-operands": selected[4] = 0; companion[4] = 321; break;
            case "wrong-arithmetic": n["stage"]!["events"]![21]![3] = 320; break;
            case "wrong-flags": n["stage"]!["events"]![21]![5] = 0x3DCA; break;
            case "host-x1": n["entry"]!["x1"] = 0; break;
            case "fake-frame": n["entry"]!["ssp"] = 0x7F6; break;
            case "rti": n["stage"]!["result"]!["executedInstructionBytes"]!.AsArray().Add(0x600); break;
            case "false-completion": n = ConsumerFixture(own, 5); n["stage"]!["result"]!["status"] = 0; break;
            case "hidden-rewrite": a.Add(new JsonArray(0x5E2, 0x3B6, 16, 1, 321)); break;
            case "wrong-entry": n["entry"]!["pc"] = 0x5DF; break;
        }
        Assert.ThrowsAny<Exception>(() => CheckConsumer(n, own));
    }
    [Fact]
    public void PartialPrefixOfConsumerRetainsOnlyCompletedNativeWrites()
    {
        var own = Oracle(); foreach (var count in new[] { 5, 8, 14, 22 }) { var n = ConsumerFixture(own, count); CheckConsumer(n, own); Assert.DoesNotContain(n["accesses"]!.AsArray(), a => a![0]!.GetValue<int>() == 0x5EB); }
    }
    [Fact]
    public async Task QuartetValidatorTimeoutAndCancellationAreDistinct()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28AdaptiveFuelTests.Image());
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(300) };
        var timeout = await Assert.ThrowsAsync<SliceProcessException>(() => P28QuartetHandoffValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options)); Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
        using var cancel = new CancellationTokenSource(); cancel.Cancel(); await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28QuartetHandoffValidator.ExecuteAsync(image, profile, binding, true, "dotnet", Scenario(), options, cancel.Token));
    }
}
