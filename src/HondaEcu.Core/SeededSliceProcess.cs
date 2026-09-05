using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public enum SliceProcessFailure { Start, Crash, Protocol, ResponseLimit, DiagnosticsLimit, Timeout }

public sealed class SliceProcessException : IOException
{
    public SliceProcessException(SliceProcessFailure failure, string message, Exception? inner = null)
        : base(message, inner) => Failure = failure;

    public SliceProcessFailure Failure { get; }
}

public sealed record SliceProcessOptions
{
    public TimeSpan Timeout { get; init; } = TimeSpan.FromMinutes(5);
    public int MaximumResponseBytes { get; init; } = 64 * 1024 * 1024;
    public int MaximumDiagnosticBytes { get; init; } = 64 * 1024;
    public IReadOnlyList<string> Arguments { get; init; } = [];
}

public sealed record SliceProcessResponse(JsonElement Response, string Diagnostics);

/// <summary>A bounded, one-request/one-response transport; exit zero is not a validation result.</summary>
public static class SeededSliceProcess
{
    public const int ProtocolVersion = 1;

    public static async Task<SliceProcessResponse> ExchangeAsync(
        string executable, object request, SliceProcessOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(executable);
        ArgumentNullException.ThrowIfNull(request);
        options ??= new SliceProcessOptions();
        if (options.Timeout <= TimeSpan.Zero || options.MaximumResponseBytes <= 0 || options.MaximumDiagnosticBytes <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(options));
        }

        var start = new ProcessStartInfo
        {
            FileName = executable,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        foreach (var argument in options.Arguments)
        {
            start.ArgumentList.Add(argument);
        }

        using var process = new Process { StartInfo = start };
        try
        {
            if (!process.Start())
            {
                throw new InvalidOperationException("Process start returned false.");
            }
        }
        catch (Exception exception) when (exception is System.ComponentModel.Win32Exception or InvalidOperationException)
        {
            throw new SliceProcessException(SliceProcessFailure.Start, "Slice runner could not be started.", exception);
        }

        using var timeout = new CancellationTokenSource(options.Timeout);
        using var ioFailure = new CancellationTokenSource();
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeout.Token, ioFailure.Token);
        var token = linked.Token;
        SliceProcessException? streamFailure = null;
        async Task<byte[]> ReadAsync(Stream stream, int limit, SliceProcessFailure failure)
        {
            using var buffer = new MemoryStream();
            var block = new byte[8192];
            while (true)
            {
                var count = await stream.ReadAsync(block, token).ConfigureAwait(false);
                if (count == 0)
                {
                    return buffer.ToArray();
                }
                if (buffer.Length + count > limit)
                {
                    streamFailure = new SliceProcessException(failure, "Slice runner exceeded a configured stream-size limit.");
                    ioFailure.Cancel();
                    throw streamFailure;
                }
                buffer.Write(block, 0, count);
            }
        }

        async Task SendAsync()
        {
            try
            {
                await JsonSerializer.SerializeAsync(process.StandardInput.BaseStream, request, JsonDefaults.Create(false), token)
                    .ConfigureAwait(false);
                await process.StandardInput.BaseStream.FlushAsync(token).ConfigureAwait(false);
                process.StandardInput.Close();
            }
            catch (Exception exception) when (exception is not OperationCanceledException)
            {
                streamFailure = new SliceProcessException(exception is IOException ? SliceProcessFailure.Crash : SliceProcessFailure.Protocol,
                    "Slice runner request could not be transmitted.", exception);
                ioFailure.Cancel();
                throw;
            }
        }

        var stdout = ReadAsync(process.StandardOutput.BaseStream, options.MaximumResponseBytes, SliceProcessFailure.ResponseLimit);
        var stderr = ReadAsync(process.StandardError.BaseStream, options.MaximumDiagnosticBytes, SliceProcessFailure.DiagnosticsLimit);
        try
        {
            await Task.WhenAll(stdout, stderr, SendAsync(), process.WaitForExitAsync(token)).ConfigureAwait(false);
        }
        catch (Exception exception) when (exception is OperationCanceledException or IOException)
        {
            await KillAsync(process).ConfigureAwait(false);
            cancellationToken.ThrowIfCancellationRequested();
            if (streamFailure is not null)
            {
                throw streamFailure;
            }
            if (timeout.IsCancellationRequested)
            {
                throw new SliceProcessException(SliceProcessFailure.Timeout, "Slice runner exceeded its time limit.");
            }
            throw new SliceProcessException(SliceProcessFailure.Crash, "Slice runner communication failed.", exception);
        }
        catch (Exception exception)
        {
            await KillAsync(process).ConfigureAwait(false);
            throw streamFailure ?? new SliceProcessException(SliceProcessFailure.Protocol, "Slice runner request failed.", exception);
        }

        if (process.ExitCode != 0)
        {
            throw new SliceProcessException(SliceProcessFailure.Crash, $"Slice runner exited with nonzero code {process.ExitCode}.");
        }
        try
        {
            var utf8 = new UTF8Encoding(false, true);
            using var document = JsonDocument.Parse(utf8.GetString(await stdout.ConfigureAwait(false)),
                new JsonDocumentOptions { MaxDepth = 64 });
            var root = document.RootElement;
            RejectDuplicates(root);
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("protocolVersion", out var version) ||
                !version.TryGetInt32(out var value) || value != ProtocolVersion)
            {
                throw new JsonException("Unsupported or missing protocol version.");
            }
            return new SliceProcessResponse(root.Clone(), utf8.GetString(await stderr.ConfigureAwait(false)));
        }
        catch (Exception exception) when (exception is JsonException or DecoderFallbackException or InvalidOperationException)
        {
            throw new SliceProcessException(SliceProcessFailure.Protocol, "Slice runner did not return one valid supported JSON response.", exception);
        }
    }

    private static void RejectDuplicates(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name))
                {
                    throw new JsonException("Duplicate JSON response property.");
                }
                RejectDuplicates(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in element.EnumerateArray())
            {
                RejectDuplicates(item);
            }
        }
    }

    private static async Task KillAsync(Process process)
    {
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
            }
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(5));
            await process.WaitForExitAsync(deadline.Token).ConfigureAwait(false);
        }
        catch (Exception exception) when (exception is InvalidOperationException or System.ComponentModel.Win32Exception or OperationCanceledException)
        {
            // The primary failure remains actionable; do not hide it behind shutdown races.
        }
    }
}
