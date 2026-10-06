namespace HondaEcu.Core.Tests;

[Collection(TimingSensitiveTestCollection.Name)]
public sealed class ProcessHandshakeTests
{
    [Fact]
    public async Task CancellationWaitsForReadinessEvenWhenFactoryIsExplicitlyGated()
    {
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var checking = ProcessHandshake.AssertActiveCancellationAsync(async (options, token) =>
        {
            entered.SetResult();
            await release.Task;
            Assert.False(token.IsCancellationRequested, "No elapsed-time cancellation before actual child startup.");
            await SeededSliceProcess.ExchangeAsync("dotnet", new { protocolVersion = 1 }, options, token);
        });
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(checking.IsCompleted);
            release.SetResult();
            await checking;
        }
        finally { release.TrySetResult(); }
    }

    [Fact]
    public async Task EarlySuccessWithoutAChildCannotPassActiveCancellation()
    {
        var error = await Assert.ThrowsAsync<Xunit.Sdk.FailException>(() =>
            ProcessHandshake.AssertActiveCancellationAsync((_, _) => Task.CompletedTask));
        Assert.Contains("before fixture readiness", error.Message);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RequestConsumedReadyCancellationKillsObservedParentAndOptionalDescendant(bool tree)
    {
        // A larger invented transport payload proves READY follows request EOF, not a startup timer.
        await ProcessHandshake.AssertActiveCancellationAsync((options, token) =>
            SeededSliceProcess.ExchangeAsync("dotnet", new { protocolVersion = 1, padding = new string('x', 131072) }, options, token), tree);
    }
}
