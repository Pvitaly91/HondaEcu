using System.Diagnostics;
using System.Globalization;
using System.IO.Pipes;

namespace HondaEcu.Core.Tests;

/// <summary>Test-only readiness protocol. Cancellation is never inferred from elapsed time.</summary>
internal static class ProcessHandshake
{
    private static async Task AwaitSignalAsync(Task signal, Task running)
    {
        if (await Task.WhenAny(signal, running).ConfigureAwait(false) == running && !signal.IsCompleted)
        {
            await running.ConfigureAwait(false);
            Assert.Fail("The operation completed before fixture readiness; this is not active cancellation.");
        }
        await signal.ConfigureAwait(false);
    }

    private static async Task<string?> ReadSignalAsync(Task<string?> signal, Task running)
    {
        await AwaitSignalAsync(signal, running).ConfigureAwait(false);
        return await signal.ConfigureAwait(false);
    }

    internal static string HostPath => Path.Combine(ExecutionTestPaths.RepositoryRoot, "tests", "HondaEcu.Slice.TestHost", "bin",
        new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name, "net8.0", "HondaEcu.Slice.TestHost.dll");

    internal static async Task AssertActiveCancellationAsync(Func<SliceProcessOptions, CancellationToken, Task> exchange, bool processTree = false)
    {
        Assert.True(File.Exists(HostPath), "Transport fixture must be built.");
        var name = "hondaecu-ready-" + Guid.NewGuid().ToString("N");
        using var pipe = new NamedPipeServerStream(name, PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
        using var active = new CancellationTokenSource();
        using var readiness = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        Task? running = null; Process? parent = null; Process? descendant = null;
        try
        {
            var connected = pipe.WaitForConnectionAsync(readiness.Token);
            running = exchange(new SliceProcessOptions { Arguments = [HostPath, "ready-wait", name, processTree ? "tree" : "single"], Timeout = TimeSpan.FromSeconds(15) }, active.Token);
            await AwaitSignalAsync(connected, running).ConfigureAwait(false);
            using var reader = new StreamReader(pipe, leaveOpen: true);
            var started = (await ReadSignalAsync(reader.ReadLineAsync(readiness.Token).AsTask(), running).ConfigureAwait(false))?.Split(' ');
            Assert.NotNull(started); Assert.Equal(2, started.Length); Assert.Equal("START", started[0]);
            parent = Process.GetProcessById(int.Parse(started[1], CultureInfo.InvariantCulture));
            var ready = (await ReadSignalAsync(reader.ReadLineAsync(readiness.Token).AsTask(), running).ConfigureAwait(false))?.Split(' ');
            Assert.NotNull(ready); Assert.Equal(3, ready.Length); Assert.Equal("READY", ready[0]);
            Assert.Equal(parent.Id, int.Parse(ready[1], CultureInfo.InvariantCulture));
            var childPid = int.Parse(ready[2], CultureInfo.InvariantCulture);
            if (processTree) { Assert.True(childPid > 0); descendant = Process.GetProcessById(childPid); Assert.False(descendant.HasExited); }
            else Assert.Equal(0, childPid);
            Assert.False(parent.HasExited); Assert.False(running.IsCompleted, "Transport must still be active after request-consumed readiness.");
            active.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => running).ConfigureAwait(false);
            using var exited = new CancellationTokenSource(TimeSpan.FromSeconds(5));
            await parent.WaitForExitAsync(exited.Token).ConfigureAwait(false); Assert.True(parent.HasExited);
            if (descendant is not null) { await descendant.WaitForExitAsync(exited.Token).ConfigureAwait(false); Assert.True(descendant.HasExited, "Observed descendant survived process-tree cancellation."); }
        }
        finally
        {
            active.Cancel();
            if (running is not null)
            {
                try { await running.ConfigureAwait(false); }
                catch (Exception) { /* Cleanup only: assertions above still determine pass/failure. */ }
            }
            foreach (var process in new[] { parent, descendant }.OfType<Process>())
            {
                if (!process.HasExited) { process.Kill(entireProcessTree: true); await process.WaitForExitAsync().ConfigureAwait(false); }
                process.Dispose();
            }
        }
    }
}
