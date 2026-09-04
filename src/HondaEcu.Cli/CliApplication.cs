namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    public const int Success = 0;
    public const int OperationError = 1;
    public const int UsageError = 2;
    public const int VerificationFailed = 3;

    private readonly TextWriter _output;
    private readonly TextWriter _error;
    private readonly string _workingDirectory;
    private readonly string? _definitionsDirectory;

    public CliApplication(
        TextWriter output,
        TextWriter error,
        string? workingDirectory = null,
        string? definitionsDirectory = null)
    {
        _output = output ?? throw new ArgumentNullException(nameof(output));
        _error = error ?? throw new ArgumentNullException(nameof(error));
        _workingDirectory = Path.GetFullPath(workingDirectory ?? Environment.CurrentDirectory);
        _definitionsDirectory = definitionsDirectory is null ? null : Path.GetFullPath(definitionsDirectory, _workingDirectory);
    }

    public async Task<int> RunAsync(string[] args, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(args);

        if (args.Length == 0 || args[0] is "help" or "--help" or "-h")
        {
            await _output.WriteLineAsync(HelpText).ConfigureAwait(false);
            return Success;
        }

        try
        {
            return args[0] switch
            {
                "inspect" => await InspectAsync(args[1..], cancellationToken).ConfigureAwait(false),
                "diff" => await DiffAsync(args[1..], cancellationToken).ConfigureAwait(false),
                "profile" => await ProfileAsync(args[1..], cancellationToken).ConfigureAwait(false),
                "read" => await ReadAsync(args[1..], cancellationToken).ConfigureAwait(false),
                "patch" => await PatchAsync(args[1..], cancellationToken).ConfigureAwait(false),
                "roundtrip" => await RoundtripAsync(args[1..], cancellationToken).ConfigureAwait(false),
                "verify" => await VerifyAsync(args[1..], cancellationToken).ConfigureAwait(false),
                "oracle" => await OracleAsync(args[1..], cancellationToken).ConfigureAwait(false),
                _ => throw new CliUsageException($"Unknown command '{args[0]}'. Run 'hondaecu help' for usage."),
            };
        }
        catch (CliUsageException exception)
        {
            await _error.WriteLineAsync($"error: {exception.Message}").ConfigureAwait(false);
            return UsageError;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            await _error.WriteLineAsync("error: Operation cancelled.").ConfigureAwait(false);
            return OperationError;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or InvalidDataException or ArgumentException or InvalidOperationException or NotSupportedException or System.Text.Json.JsonException)
        {
            await _error.WriteLineAsync($"error: {exception.Message}").ConfigureAwait(false);
            return OperationError;
        }
        catch (Exception exception)
        {
            await _error.WriteLineAsync($"error: {exception.Message}").ConfigureAwait(false);
            return OperationError;
        }
    }

    private const string HelpText = """
        HondaEcu M0 ROM inspection and validation harness

        Usage: hondaecu <command> [arguments] [options]

        Commands:
          inspect <rom>                         Inspect a raw ROM image
          diff <base> <modified> [--json] [--output <json>] [--max-ranges <N>]
                                                 Compare ROM images byte by byte
          profile list|show|validate            Inspect ROM profile definitions
          read <rom> --profile <id>             Decode profile parameters
          patch <rom> --profile <id> --set <id=value> --output <rom> --report <json>
                    [--allow-unverified] [--confirm-profile]
          roundtrip <rom> --profile <id>        Prove decode/encode byte identity
          verify <rom> --profile <id> --patch-report <json>
          oracle create-manifest|add-case|analyze|compare|export-candidate

        ROM outputs are for PC inspection only unless separately validated.
        Exit codes: 0 success, 1 operation error, 2 usage error, 3 verification failure.
        """;

}
