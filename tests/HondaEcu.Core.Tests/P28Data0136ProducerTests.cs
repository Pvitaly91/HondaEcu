using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28Data0136ProducerTests
{
    [Fact]
    public void BlockedModelNeverReturnsAHostDerivedNativeWord()
    {
        var m = P28Data0136ProducerModel.Current;
        Assert.Equal("ProducerNotRun_IRQDependent", m.Status);
        Assert.Null(m.Expected0136);
        Assert.Equal(0, m.NativeWrites);
    }

    // Abstract raw arithmetic only. These are NOT OEM reachability or native witnesses.
    [Theory]
    [InlineData(0, 0, 0, 0)]
    [InlineData(5, 0, 0, 0)]
    [InlineData(6, 0, 0, 1)]
    [InlineData(600, 0, 0, 100)]
    [InlineData(65530, 0, 5, 65535)]
    [InlineData(0, 0, 6, 0)]
    [InlineData(0, 1, 0, 0)]
    [InlineData(0, 1, 1, 10922)]
    public void ModelOnlyUnsignedWrapTruncationAndOverflowClear(int sample, int previous, int counter, int expected)
    {
        var r = P28Data0136ProducerModel.Hypothesize((ushort)sample, (ushort)previous, (byte)counter, true, true, false, false);
        Assert.True(r.WouldWrite);
        Assert.Equal((ushort)expected, r.AbstractWord);
    }

    [Fact]
    public void ModelOnlyCounterConditionalIncrementWrapAndFirstSampleNoWrite()
    {
        var r = P28Data0136ProducerModel.Hypothesize(6, 0, 255, true, true, true, false);
        Assert.Equal((byte)0, r.CounterAfterSample);
        Assert.Equal((ushort)1, r.AbstractWord);
        Assert.Equal((byte)255, P28Data0136ProducerModel.Hypothesize(0x8006, 0, 255, true, true, true, false).CounterAfterSample);
        var held = P28Data0136ProducerModel.Hypothesize(6, 0, 255, false, true, true, false);
        Assert.False(held.WouldWrite); Assert.Null(held.AbstractWord); Assert.Null(held.Dividend);
    }

    [Theory]
    [InlineData(10, 10, false, 0)]
    [InlineData(0, 1, false, 65535)]
    [InlineData(900, 300, false, 600)]
    [InlineData(900, 300, true, 0)]
    public void ModelOnlyDirectDifferenceZeroAndControl(int sample, int previous, bool control, int expected)
    {
        var r = P28Data0136ProducerModel.Hypothesize((ushort)sample, (ushort)previous, 0, true, false, false, control);
        Assert.Equal((ushort)expected, r.AbstractWord); Assert.Null(r.Dividend);
    }

    [Fact]
    public void ModelOnlySourceSweepRepeatChangeAndHeldAreNotNativeCoverage()
    {
        var a = P28Data0136ProducerModel.Hypothesize(600, 0, 0, true, true, false, false);
        Assert.Equal(a, P28Data0136ProducerModel.Hypothesize(600, 0, 0, true, true, false, false));
        Assert.NotEqual(a.AbstractWord, P28Data0136ProducerModel.Hypothesize(1200, 0, 0, true, true, false, false).AbstractWord);
        Assert.Null(P28Data0136ProducerModel.Hypothesize(1200, 0, 0, false, true, false, false).AbstractWord);
        Assert.Null(P28Data0136ProducerModel.Current.Expected0136);
    }

    private static SoftwareWordGeneration G(int pc = 7, int e = 0, int order = 0, ushort value = 321) => new(pc, e, order, value);
    private static SoftwareWordAccess A(int pc, int order, int address, bool write, int value = 321, int width = 16, int e = 0, bool host = false)
        => new(pc, e, order, address, width, write, value, host);
    private static SoftwareWordConsumption C(SoftwareWordGeneration g) => new(19, 0x206, 23, g);
    private static List<SoftwareWordAccess> Good() => [A(7, 0, 0x300, true), A(19, 1, 0x300, false), A(19, 2, 0x206, true), A(23, 3, 0x206, false)];

    [Fact]
    public void InventedProducerConsumerSameGenerationAndCrossEventHeld()
    {
        var p = new SoftwareWordProvenance(0x300);
        Assert.Equal(SoftwareWordLifetime.InitialHistory, p.State); Assert.Null(p.Current);
        p.CheckEvent(0, SoftwareWordLifetime.NativeWritten, [G()], Good(), C(G()));
        var reads = Good().Skip(1).Select(a => a with { EventIndex = 1 }).ToList();
        p.CheckEvent(1, SoftwareWordLifetime.Held, [], reads, C(G()));
        Assert.Equal(SoftwareWordLifetime.Held, p.State); Assert.Equal(G(), p.Current); Assert.Single(p.History);
    }

    [Fact]
    public void InventedSameValueTwoWritersAreDistinctOrderedGenerations()
    {
        var p = new SoftwareWordProvenance(0x300);
        p.CheckEvent(0, SoftwareWordLifetime.NativeWritten, [G(), G(9, order: 1)], [A(7, 0, 0x300, true), A(9, 1, 0x300, true)]);
        p.CheckEvent(1, SoftwareWordLifetime.NativeWritten, [G(7, 1)], [A(7, 0, 0x300, true, e: 1)]);
        Assert.Equal(3, p.History.Count); Assert.Equal(G(7, 1), p.Current);
        Assert.NotEqual(p.History[0], p.History[1]); Assert.NotEqual(p.History[0], p.History[2]);
    }

    [Theory]
    [InlineData("byte-low")]
    [InlineData("byte-high")]
    [InlineData("neighbor-word")]
    [InlineData("host-overwrite")]
    [InlineData("reader-width")]
    [InlineData("stale-writer")]
    [InlineData("stale-event")]
    [InlineData("stale-order")]
    [InlineData("wrong-expected")]
    [InlineData("missing-reader")]
    [InlineData("missing-register-write")]
    [InlineData("missing-divisor-read")]
    [InlineData("late-store")]
    [InlineData("reordered-writers")]
    [InlineData("register-host-write")]
    public void InventedProvenanceForgeriesRejectEvenWhenNumbersMatch(string fault)
    {
        var p = new SoftwareWordProvenance(0x300); var rows = Good(); var expected = G(); var consume = C(G());
        switch (fault)
        {
            case "byte-low": rows[0] = rows[0] with { Width = 8, Value = 65 }; break;
            case "byte-high": rows[0] = rows[0] with { Address = 0x301, Width = 8, Value = 1 }; break;
            case "neighbor-word": rows[0] = rows[0] with { Address = 0x2FF }; break;
            case "host-overwrite": rows[0] = rows[0] with { Host = true }; break;
            case "reader-width": rows[1] = rows[1] with { Width = 8, Value = 65 }; break;
            case "stale-writer": consume = C(G(9)); break;
            case "stale-event": consume = C(G(e: 1)); break;
            case "stale-order": consume = C(G(order: 1)); break;
            case "wrong-expected": expected = G(value: 322); break;
            case "missing-reader": rows.RemoveAt(1); break;
            case "missing-register-write": rows.RemoveAt(2); break;
            case "missing-divisor-read": rows.RemoveAt(3); break;
            case "late-store": rows.Add(A(9, 4, 0x300, true)); break;
            case "reordered-writers": rows.Insert(1, A(9, 0, 0x300, true)); break;
            case "register-host-write": rows[2] = rows[2] with { Host = true }; break;
        }
        Assert.Throws<InvalidDataException>(() => p.CheckEvent(0, SoftwareWordLifetime.NativeWritten, [expected], rows, consume));
        Assert.Null(p.Current); Assert.Empty(p.History);
    }

    [Fact]
    public void InventedPartialCompletedWriteRetainedButFollowingEventsNotRun()
    {
        var p = new SoftwareWordProvenance(0x300);
        p.CheckEvent(0, SoftwareWordLifetime.PartialNativeWritten, [G()], [A(7, 0, 0x300, true)]);
        Assert.Equal(G(), p.Current);
        Assert.Throws<InvalidDataException>(() => p.CheckEvent(1, SoftwareWordLifetime.Held, [], [], C(G())));
        Assert.Throws<InvalidDataException>(() => p.CheckEvent(1, SoftwareWordLifetime.NotRun, [], [A(19, 0, 0x300, false, e: 1)]));
        p.CheckEvent(1, SoftwareWordLifetime.NotRun, [], []);
        Assert.Equal(SoftwareWordLifetime.NotRun, p.State); Assert.Equal(G(), p.Current);
    }

    [Fact]
    public void InventedHeldCannotInventGenerationFromInitialHistory()
    {
        var p = new SoftwareWordProvenance(0x300);
        Assert.Throws<InvalidDataException>(() => p.CheckEvent(0, SoftwareWordLifetime.Held, [], []));
        p.CheckEvent(0, SoftwareWordLifetime.NotRun, [], []);
        Assert.Null(p.Current);
        Assert.Throws<InvalidDataException>(() => p.CheckEvent(1, SoftwareWordLifetime.NativeWritten, [G(e: 1)], [A(7, 0, 0x300, true, e: 1)]));
    }

    [Fact]
    public void InventedCancellationAndTimeoutDoNotPublishGeneration()
    {
        var p = new SoftwareWordProvenance(0x300); using var stop = new CancellationTokenSource(); stop.Cancel();
        Assert.Throws<OperationCanceledException>(() => p.CheckEvent(0, SoftwareWordLifetime.NativeWritten, [G()], Good(), C(G()), stop.Token));
        Assert.Throws<TimeoutException>(() => p.CheckEvent(0, SoftwareWordLifetime.NativeWritten, [G()], Good(), C(G()), deadline: DateTimeOffset.UtcNow.AddMinutes(-1)));
        Assert.Empty(p.History); Assert.Null(p.Current);
        p.CheckEvent(0, SoftwareWordLifetime.NativeWritten, [G()], Good(), C(G()));
    }

    [Fact]
    public void HistoricalSchemaDoesNotSilentlyMigrateToUnestablishedProducer()
    {
        var original = P28DivisionDecisionTests.Scenario();
        Assert.Equal(original.Digest, P28DivisionDecisionScenario.Parse(original.ToJson()).Digest);
        var n = JsonNode.Parse(original.ToJson())!; n["purpose"] = "data0136-producer-native-software-test";
        Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(n.ToJsonString()));
        n = JsonNode.Parse(original.ToJson())!; n["formatVersion"] = 2;
        Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(n.ToJsonString()));
        n = JsonNode.Parse(original.ToJson())!; n["producerReadyValue"] = 321;
        Assert.ThrowsAny<Exception>(() => P28DivisionDecisionScenario.Parse(n.ToJsonString()));
    }
}
