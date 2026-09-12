using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28IgnitionMapProcessTests
{
    [Theory]
    [InlineData("0.12.0", "ignitionMapLookup")]
    [InlineData("0.13.0", "fuelMapLookup")]
    public void IgnitionCapabilityRejectsWrongVersionOrTask(string version, string operation)
    {
        using var document = JsonDocument.Parse(JsonSerializer.Serialize(new
        {
            protocolVersion = 1,
            operation,
            runnerVersion = version,
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = Array.Empty<string>(),
        }));
        Assert.Throws<SliceProcessException>(() => SliceRunnerIdentity.Validate(document.RootElement, "ignitionMapLookup"));
    }

    [Fact]
    public async Task IgnitionUsesBoundedTransportTimeoutAndCancellation()
    {
        var (image, profile, binding) = P28AcquisitionValidatorTests.Fixture(P28IgnitionMapTests.InventedImage(true).ToArray());
        var scenario = P28IgnitionMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 0, 0),
            [new(0, "ignition_map_0", 1, 2, 3)], "Invented transport test.");
        var configuration = new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin",
            configuration, "net8.0", "HondaEcu.Slice.TestHost.dll");
        Assert.True(File.Exists(host));
        var options = new SliceProcessOptions { Arguments = [host, "timeout"], Timeout = TimeSpan.FromMilliseconds(500) };
        var exception = await Assert.ThrowsAsync<SliceProcessException>(() =>
            P28IgnitionMapValidator.ExecuteAsync(image, profile, binding, true, "dotnet", scenario, options));
        Assert.Equal(SliceProcessFailure.Timeout, exception.Failure);
        using var cancellation = new CancellationTokenSource(500);
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28IgnitionMapValidator.ExecuteAsync(image, profile,
            binding, true, "dotnet", scenario, options with { Timeout = TimeSpan.FromSeconds(15) }, cancellation.Token));
    }
}
