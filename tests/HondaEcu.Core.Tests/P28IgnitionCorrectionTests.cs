using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28IgnitionCorrectionTests
{
    private static P28IgnitionCorrectionInitial Initial(byte factor = 0) =>
        new(new(0, 0, 0, 0, 0, 0, 0xA5, factor, 77), 0,
            0, 0, 31, 32, false, false, false);

    private static P28IgnitionCorrectionScenario Scenario() => P28IgnitionCorrectionScenario.Create(
        Initial(), [new(0, 0, 0, 0, 0, 0, 0), new(1, 0, 255, 255, 0, 255, 0)],
        [0], "Invented raw software correction scenario.");

    [Fact]
    public void ClosedScenarioRejectsResultsModeMasksAndArbitraryWrites()
    {
        var scenario = Scenario();
        Assert.Equal(scenario.Digest, P28IgnitionCorrectionScenario.Parse(scenario.ToJson()).Digest);
        foreach (var mutate in new Action<JsonNode>[]
        {
            node => node["calls"]![0]!["data0248"] = 10,
            node => node["calls"]![0]!["mode0207Bit7"] = true,
            node => node["calls"]![0]!["mapId"] = "ignition_map_1",
            node => node["calls"]![0]!["expectedOutput"] = 13,
            node => node["calls"]![0]!["ram"] = new JsonObject(),
            node => node["calls"]![0]!["index"] = 7,
        })
        {
            var node = JsonNode.Parse(scenario.ToJson())!; mutate(node);
            Assert.Throws<InvalidDataException>(() => P28IgnitionCorrectionScenario.Parse(node.ToJsonString()));
        }
    }

    [Theory]
    [InlineData("0.16.0", "ignitionCorrectionChain")]
    [InlineData("0.17.0", "ignitionSelectorChain")]
    public void M2iCapabilityRejectsWrongVersionOrOperation(string version, string operation)
    {
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(new
        {
            protocolVersion = 1,
            operation,
            runnerVersion = version,
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = Array.Empty<string>(),
        }));
        Assert.Throws<SliceProcessException>(() =>
            SliceRunnerIdentity.Validate(document.RootElement, P28IgnitionCorrectionValidator.Operation));
    }

    [Fact]
    public void IndependentHistoryUsesOwnPrefixAndCorrectionEr3Aliases()
    {
        var model = new P28IgnitionCorrectionModel(P28IgnitionMapTests.InventedImage(), Initial(173));
        var a = model.Step(new(0, 0, 0, 0, 0, 255, 0));
        var b = model.Step(new(1, 0, 255, 255, 0, 0, 0));
        Assert.Equal(0xA5, a.Prefix.Before.Selector0227);
        Assert.Equal(0x85, a.Prefix.SelectorAfterProducer);
        Assert.Equal(a.Prefix.Ignition.After, b.Prefix.Before);
        Assert.Equal(a.Correction.CorrectionAccumulator >= 0x8000, a.Correction.Mode0207Bit7);
        Assert.Equal(b.Correction.CorrectionAccumulator >= 0x8000, b.Correction.Mode0207Bit7);
        Assert.Equal(b.Correction.Result035b, model.Retained.Result035b);
        Assert.Equal(b.Correction.Result024a, model.Retained.Result024a);
    }

    [Fact]
    public void FiniteCorrectionDomainSeparatesByteWrapWordWrapAndBounds()
    {
        var image = P28IgnitionMapTests.InventedImage();
        var cases = 0;
        foreach (var correction in Enumerable.Range(0, 256))
            foreach (var subtract in new[] { 0, 1, 255 })
            {
                var model = new P28IgnitionCorrectionModel(image, Initial());
                var step = model.Step(new(0, 0, 0, 0, 0, (byte)correction, (byte)subtract));
                var result = step.Correction;
                var signed = unchecked((sbyte)correction);
                var er3 = unchecked((ushort)(signed - subtract));
                var wrapped = unchecked((ushort)(result.Base0248 + er3));
                Assert.Equal(er3, result.CorrectionAccumulator);
                Assert.Equal(wrapped, result.CorrectedRaw);
                Assert.Equal(er3 >= 0x8000, result.Mode0207Bit7);
                Assert.InRange(result.BoundedRaw, (byte)0, byte.MaxValue);
                Assert.InRange(result.Result024a, (byte)0, byte.MaxValue);
                cases++;
            }
        Assert.Equal(768, cases); // model audit, not 768 native executions
    }

    [Fact]
    public void EqualFinalNumberDoesNotHideSubstitutedOrMissingNativeReader()
    {
        using var consumer = JsonDocument.Parse("""{"writes":[[584,8,42]]}""");
        using var valid = JsonDocument.Parse("""{"writes":[[587,8,42]],"events":[[4084,4086,0,42,0,0,65536,65536]]}""");
        using var substituted = JsonDocument.Parse("""{"writes":[[587,8,42]],"events":[[4084,4086,0,41,0,0,65536,65536]]}""");
        using var hostStore = JsonDocument.Parse("""{"writes":[[584,8,42]],"events":[[4084,4086,0,42,0,0,65536,65536]]}""");
        Assert.True(P28IgnitionCorrectionValidator.HandoffMatches(consumer.RootElement, valid.RootElement, 42));
        Assert.False(P28IgnitionCorrectionValidator.HandoffMatches(consumer.RootElement, substituted.RootElement, 42));
        Assert.False(P28IgnitionCorrectionValidator.HandoffMatches(consumer.RootElement, hostStore.RootElement, 42));
    }

    [Fact]
    public async Task M2iTransportSeparatesAlreadyCancelledTimeoutAndActiveChildCancellation()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(
            P28IgnitionMapTests.InventedImage(true).ToArray());
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost",
            "bin", new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0",
            "HondaEcu.Slice.TestHost.dll");
        Assert.True(File.Exists(host));
        var marker = Path.Combine(Path.GetTempPath(), $"hondaecu-m2i-active-{Guid.NewGuid():N}.pid");
        Process? child = null;
        try
        {
            using (var cancelled = new CancellationTokenSource())
            {
                cancelled.Cancel();
                await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
                    P28IgnitionCorrectionValidator.ExecuteAsync(image, profile, binding, true, "dotnet",
                        Scenario(), new SliceProcessOptions { Arguments = [host, "pid-sleep", marker] },
                        cancelled.Token));
                Assert.False(File.Exists(marker));
            }
            var timeout = await Assert.ThrowsAsync<SliceProcessException>(() =>
                P28IgnitionCorrectionValidator.ExecuteAsync(image, profile, binding, true, "dotnet",
                    Scenario(), new SliceProcessOptions
                    {
                        Arguments = [host, "timeout"],
                        Timeout = TimeSpan.FromMilliseconds(300)
                    }));
            Assert.Equal(SliceProcessFailure.Timeout, timeout.Failure);
            using var active = new CancellationTokenSource();
            var running = P28IgnitionCorrectionValidator.ExecuteAsync(image, profile, binding, true,
                "dotnet", Scenario(), new SliceProcessOptions
                {
                    Arguments = [host, "pid-sleep", marker],
                    Timeout = TimeSpan.FromSeconds(15)
                }, active.Token);
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(10);
            while (!File.Exists(marker) && DateTime.UtcNow < deadline) await Task.Delay(20);
            Assert.True(File.Exists(marker), "M2i child PID must exist before cancellation.");
            var pid = int.Parse(await File.ReadAllTextAsync(marker), System.Globalization.CultureInfo.InvariantCulture);
            child = Process.GetProcessById(pid);
            Assert.False(child.HasExited);
            Assert.False(running.IsCompleted);
            active.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => running);
            child.Refresh();
            Assert.True(child.HasExited, $"M2i child PID {pid} survived active cancellation.");
        }
        finally
        {
            child?.Dispose();
            // Windows may briefly retain the just-exited child's marker handle.
            for (var attempt = 0; File.Exists(marker) && attempt < 10; attempt++)
            {
                try { File.Delete(marker); }
                catch (IOException) when (attempt < 9) { await Task.Delay(50); }
            }
        }
    }
}
