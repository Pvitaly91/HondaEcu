using System.Diagnostics;

namespace HondaEcu.Core.Tests;

public sealed class SeededSliceProcessTests
{
    [Theory]
    [InlineData("version", SliceProcessFailure.Protocol)]
    [InlineData("duplicate", SliceProcessFailure.Protocol)]
    [InlineData("malformed", SliceProcessFailure.Protocol)]
    [InlineData("empty", SliceProcessFailure.Protocol)]
    [InlineData("crash", SliceProcessFailure.Crash)]
    [InlineData("timeout", SliceProcessFailure.Timeout)]
    [InlineData("stdout-limit", SliceProcessFailure.ResponseLimit)]
    [InlineData("stderr-limit", SliceProcessFailure.DiagnosticsLimit)]
    public async Task MockProcessFailuresAreDistinctAndBounded(string scenario, SliceProcessFailure expected)
    {
        var options = HostOptions(scenario) with
        {
            Timeout = scenario == "timeout" ? TimeSpan.FromMilliseconds(500) : TimeSpan.FromSeconds(15),
            MaximumResponseBytes = 1024,
            MaximumDiagnosticBytes = 1024,
        };
        var exception = await Assert.ThrowsAsync<SliceProcessException>(() =>
            SeededSliceProcess.ExchangeAsync("dotnet", new { protocolVersion = 1 }, options));
        Assert.Equal(expected, exception.Failure);
    }

    [Fact]
    public async Task MockExitZeroStillRequiresStructuredVersionedJsonAndArgumentsAreNotShellParsed()
    {
        var literal = "spaces ; & \" quotes $variable";
        var options = HostOptions("arguments");
        options = options with { Arguments = options.Arguments.Append(literal).ToArray() };
        var result = await SeededSliceProcess.ExchangeAsync("dotnet", new { protocolVersion = 1 }, options);
        Assert.Equal(literal, result.Response.GetProperty("arguments")[0].GetString());
        Assert.Empty(result.Diagnostics);
    }

    [Fact]
    public async Task CallerCancellationTerminatesTheMockChildAndIsNotReportedAsAMismatch()
    {
        using var cancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(500));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            SeededSliceProcess.ExchangeAsync("dotnet", new { protocolVersion = 1 }, HostOptions("timeout"), cancellation.Token));
    }

    [Fact]
    public async Task AlreadyCancelledRequestNeverStartsAChild()
    {
        var marker = Path.Combine(Path.GetTempPath(), $"hondaecu-m2h-never-started-{Guid.NewGuid():N}.pid");
        try
        {
            using var cancellation = new CancellationTokenSource();
            cancellation.Cancel();
            var options = HostOptions("pid-sleep") with { Arguments = [.. HostOptions("pid-sleep").Arguments, marker] };
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
                SeededSliceProcess.ExchangeAsync("dotnet", new { protocolVersion = 1 }, options, cancellation.Token));
            Assert.False(File.Exists(marker));
        }
        finally { if (File.Exists(marker)) File.Delete(marker); }
    }

    [Fact]
    public async Task ActiveCancellationKillsObservedChildProcessTree()
    {
        var marker = Path.Combine(Path.GetTempPath(), $"hondaecu-m2h-active-{Guid.NewGuid():N}.pid");
        Process? child = null;
        using var cancellation = new CancellationTokenSource();
        try
        {
            var options = HostOptions("pid-sleep") with { Arguments = [.. HostOptions("pid-sleep").Arguments, marker] };
            var running = SeededSliceProcess.ExchangeAsync("dotnet", new { protocolVersion = 1 }, options, cancellation.Token);
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(10);
            while (!File.Exists(marker) && DateTime.UtcNow < deadline) await Task.Delay(20);
            Assert.True(File.Exists(marker), "The child must publish its PID before cancellation.");
            var pid = int.Parse(await File.ReadAllTextAsync(marker), System.Globalization.CultureInfo.InvariantCulture);
            child = Process.GetProcessById(pid);
            Assert.False(child.HasExited);
            Assert.False(running.IsCompleted);
            cancellation.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => running);
            child.Refresh();
            Assert.True(child.HasExited, $"Child PID {pid} survived cancellation.");
        }
        finally
        {
            cancellation.Cancel();
            child?.Dispose();
            if (File.Exists(marker)) File.Delete(marker);
        }
    }

    [Fact]
    public async Task MissingExecutableIsStartFailure()
    {
        var exception = await Assert.ThrowsAsync<SliceProcessException>(() =>
            SeededSliceProcess.ExchangeAsync(Path.Combine(Path.GetTempPath(), $"absent-{Guid.NewGuid():N}"), new { protocolVersion = 1 }));
        Assert.Equal(SliceProcessFailure.Start, exception.Failure);
    }

    [Fact]
    public async Task UnserializableRequestCannotLeaveTheMockChildRunning()
    {
        var exception = await Assert.ThrowsAsync<SliceProcessException>(() =>
            SeededSliceProcess.ExchangeAsync("dotnet", new { callback = (Action)(() => { }) }, HostOptions("timeout")));
        Assert.Equal(SliceProcessFailure.Protocol, exception.Failure);
    }

    private static SliceProcessOptions HostOptions(string scenario)
    {
        var configuration = new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;
        var host = Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin", configuration, "net8.0", "HondaEcu.Slice.TestHost.dll");
        Assert.True(File.Exists(host), "Transport fixture must be built; absence is not a passing test.");
        return new SliceProcessOptions { Arguments = [host, scenario], Timeout = TimeSpan.FromSeconds(15) };
    }
}

internal static class ExecutionTestPaths
{
    public static string RepositoryRoot
    {
        get
        {
            for (var directory = new DirectoryInfo(AppContext.BaseDirectory); directory is not null; directory = directory.Parent)
            {
                if (File.Exists(Path.Combine(directory.FullName, "Directory.Build.props")))
                {
                    return directory.FullName;
                }
            }
            throw new DirectoryNotFoundException("Repository root not found for required execution tests.");
        }
    }

    public static string RustRunner
    {
        get
        {
            var path = Environment.GetEnvironmentVariable("HONDAECU_SLICE_RUNNER") ?? Path.Combine(
                RepositoryRoot, "rust", "p28-slice-runner", "target", "release", OperatingSystem.IsWindows() ? "p28-slice-runner.exe" : "p28-slice-runner");
            Assert.True(File.Exists(path), "Real Rust integration was not run: build the release Rust runner first or set HONDAECU_SLICE_RUNNER. This test never silently skips.");
            return path;
        }
    }
}
