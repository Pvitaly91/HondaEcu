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
                "research" => await ResearchAsync(args[1..], cancellationToken).ConfigureAwait(false),
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
        HondaEcu M0.1 ROM inspection and oracle validation harness

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
          oracle create-manifest|add-case|analyze|compare|export-candidate|preflight
          research p28-vtec inspect <rom> --profile p28-304 --output <private-json>
                    [--baseline-binding <private-json>] [--confirm-profile]
                    [--baseline <original-rom> --plan <private-json> --patch-report <private-json>]
          research p28-vtec plan <rom> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --slot <slot-id> --raw-value <0..255>
                    --output <private-plan.json>
          research p28-vtec apply <baseline> --plan <private-json> --baseline-binding <private-json>
                    --confirm-pc-only --output <new-private-rom> --report <private-json>
                    [--profile p28-304] [--confirm-profile]
          research p28-vtec verify <output> --baseline <original> --baseline-binding <private-json>
                    --plan <private-json> --report <private-json> [--output <private-json>]
          research p28-vtec execute-check <baseline> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --runner <rust-executable> --output <private-json>
                    [--allow-assumption oki.add-er3-a] [--derived <child> --plan <private-json> --patch-report <private-json>]
          research p28-vtec checksum-check <baseline> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --output <private-json> [--runner <rust-executable>]
                    [--derived <child> --plan <private-json> --patch-report <private-json>]
          research p28-vtec compensation-check <original> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --output <new-private-json>
                    [--compensation-definition <reviewed-signed-private-json>]
          research p28-vtec checksum-export-plan <original> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --compensation-definition <reviewed-signed-private-json>
                    --output <new-composed-plan.json>
                    [--slot <slot-id> --raw-value <0..255>]
                    [--derived <M1c-child> --plan <M1c-plan> --patch-report <M1c-report>]
                    Choose exactly one threshold request or complete existing M1c lineage.
          research p28-vtec checksum-export-apply <original> --baseline-binding <private-json>
                    --compensation-definition <reviewed-signed-private-json> --plan <composed-plan>
                    --runner <rust-executable> --confirm-pc-only --output <new-private-rom>
                    --saved-plan <new-plan-copy.json> --report <new-export-report.json>
          research p28-vtec checksum-export-verify <output> --baseline <original>
                    --baseline-binding <private-json> --compensation-definition <reviewed-signed-private-json>
                    --plan <composed-plan> --report <export-report> [--output <new-verification.json>]
          research p28-vtec checksum-export-inspect <output> --baseline <original>
                    --baseline-binding <private-json> --compensation-definition <reviewed-signed-private-json>
                    --plan <composed-plan> --report <export-report> --output <new-inspection.json>
          research p28-vtec producer-check <baseline> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --runner <rust-executable> --output <private-json>
                    [--allow-assumption oki.add-er1-a] [--allow-assumption oki.add-er3-a]
                    [--derived <child> --plan <private-json> --patch-report <private-json>] [--scaling <private-json>]
          research p28-vtec rpm-preview <original> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --slot <slot-id> --output <new-private-json>
                    [--scaling <explicit-scenario.json>] [--rpm <N/D> --rpm-provenance <text>]
                    [--allow-assumption oki.add-er1-a] [--allow-assumption oki.add-er3-a]
                    Conditional mathematical selection only; no BIN, runner or export authority.
                    Without scaling, numerical RPM is unavailable. Strict model mode is the default.
          research p28-limiter inspect <baseline> --profile p28-304 --output <new-private-json>
              [--confirm-profile --baseline-binding <private-json>]
          research p28-idle inspect <baseline> --profile p28-304 --output <new-private-json>
              [--confirm-profile --baseline-binding <private-json>]
          research p28-fuel maps-inspect <baseline> --profile p28-304 --output <new-private-json>
              [--confirm-profile --baseline-binding <private-json>]
          research p28-fuel lookup-check <baseline> --profile p28-304 --confirm-profile
              --baseline-binding <private-json> --runner <rust-executable>
              --scenario <private-json> --output <new-private-json>
              Read-only map_0/map_1 raw lookup research; no BIN, physical units or GUI.
          research p28-fuel vtec-chain-check <original> --profile p28-304 --confirm-profile
              --baseline-binding <private-json> --runner <v0.14.0-rust-executable>
              --scenario <bounded-m2f-scenario.json> --output <new-private-json>
              [--allow-assumption oki.subb-a-off-n8-encoding]
              One native decision→selection→lookup→DATA0140 tail; scripted axis caller, no BIN or physical VTEC claim.
          research p28-ignition maps-inspect <baseline> --profile p28-304 --output <new-private-json>
              [--confirm-profile --baseline-binding <private-json>]
          research p28-ignition lookup-check <baseline> --profile p28-304 --confirm-profile
              --baseline-binding <private-json> --runner <rust-executable>
              --scenario <private-json> --output <new-private-json>
              Read-only ignition_map_0/1 raw lookup research; no BIN, degree conversion or GUI.
          research p28-ignition selector-chain-check <original> --profile p28-304 --confirm-profile
              --baseline-binding <private-json> --runner <v0.15.0-rust-executable>
              --scenario <bounded-m2g-scenario.json> --output <new-private-json>
              Native selector production before ignition axes/lookup/DATA0248; no map-ID input or BIN.
          research p28-calibration shared-chain-check <original> --profile p28-304 --confirm-profile
              --baseline-binding <private-json> --runner <v0.16.0-rust-executable>
              --scenario <bounded-m2h-scenario.json> --output <new-private-json>
              [--allow-assumption oki.subb-a-off-n8-encoding]
              One shared axis pass and two native tails; scripted schedule, raw units, no BIN.
          research p28-fuel export <plan|apply|verify|inspect> <image> --profile p28-304 ...
              Explicit 20x10 unsigned numeric cells, one compensation, fresh A/B/C native validation.
          research p28-ignition export <plan|apply|verify|inspect> <image> --profile p28-304 ...
              Explicit primary 20x10 unsigned numeric cells, one compensation, factor-aware A/B/C validation.
          research p28-idle target-check <baseline> --profile p28-304 --confirm-profile
            --baseline-binding <binding.json> --runner <rust-runner> --scenario <idle-scenario.json>
            --output <new-private-validation.json>
          research p28-idle contexts-inspect <baseline> --profile p28-304 --output <new-private-json>
              [--confirm-profile --baseline-binding <private-json>]
          research p28-idle export <plan|apply|verify|inspect> <image> --profile p28-304 ...
          research p28-calibration export <plan|apply|verify|inspect> <image> --profile p28-304 ...
            One original, explicit six-group settings, one compensation; raw PC-only research, not full ECU validation.
            plan: --confirm-profile --baseline-binding <json> --compensation-definition <json>
              --settings <explicit-base-and-late-values-json> --output <new-plan-json>
            apply: same original/binding/location + --plan <json> --runner <exe> --confirm-pc-only
              --output <new-bin> --saved-plan <new-json> --report <new-receipt>
            verify/inspect: --baseline <original> --baseline-binding <json> --compensation-definition <json>
              --plan <saved-plan> --report <receipt> --output <new-result-json>
          research p28-calibration combined-export <plan|apply|verify|inspect> <image> --profile p28-304 ...
            Ten closed basic/fuel/ignition groups from one original; one compensation and one checksum batch.
            Uses the same plan/apply/verify/inspect input roles as above; plan takes the M2e combined settings format.
          research p28-idle contexts-check <baseline> --profile p28-304 --confirm-profile
            --baseline-binding <binding.json> --runner <rust-runner> --scenario <contexts-scenario.json>
            --output <new-private-contexts-validation.json>
          research p28-limiter export plan <original> --profile p28-304 --confirm-profile
              --baseline-binding <binding> --compensation-definition <reviewed-location>
              --cut-raw <integer> --resume-raw <integer> --output <new-plan.json>
          research p28-limiter export apply <original> --profile p28-304 --confirm-profile
              --baseline-binding <binding> --compensation-definition <reviewed-location> --plan <plan>
              --runner <rust-executable> --confirm-pc-only --output <new-private.bin>
              --saved-plan <new-plan-copy.json> --report <new-receipt.json>
          research p28-limiter export verify|inspect <output> --baseline <original> --profile p28-304
              --baseline-binding <binding> --compensation-definition <reviewed-location>
              --plan <saved-plan> --report <receipt> --output <new-verification.json>
              Fixed context only; adaptive tables unchanged. Raw pair policy is not engine safety.
          research p28-limiter check <baseline> --profile p28-304 --confirm-profile
              --baseline-binding <private-json> --runner <rust-executable>
              --scenario <private-limiter-json> --output <new-private-json>
          research p28-limiter adaptive-export <plan|apply|verify|inspect> <image>
          research p28-limiter combined-export <plan|apply|verify|inspect> <image> (--settings <explicit-groups.json> for plan)
            plan: --bank <0|1> --base-cut-raw <integer> --base-resume-raw <integer>
            --profile p28-304 --baseline-binding <binding> --compensation-definition <reviewed-location>
            --output <new-private-json-or-bin>; apply requires --runner and --confirm-pc-only
          research p28-limiter adaptive-check <baseline> --profile p28-304 --confirm-profile
              --baseline-binding <private-json> --runner <rust-executable>
              --scenario <private-adaptive-json> --output <new-private-json>
          research p28-vtec state-check <baseline> --profile p28-304 --confirm-profile
            --baseline-binding <private-json> --runner <rust-executable>
            --scenario <private-json> --output <new-private-json>
            [--allow-assumption oki.subb-a-off-n8-encoding]
            [--derived <child> --plan <plan> --export-report <receipt> --compensation-definition <definition>]
          research p28-vtec chain-check <baseline> --profile p28-304 --confirm-profile
            --baseline-binding <private-json> --runner <rust-executable>
            --scenario <bounded-chain-scenario.json> --output <new-private-json>
            [--allow-assumption oki.add-er1-a] [--allow-assumption oki.add-er3-a]
            [--allow-assumption oki.subb-a-off-n8-encoding]
            [--derived <child> --plan <plan> --export-report <receipt> --compensation-definition <definition>]
            One CPU/RAM history per image; samples/T/Code/prior are never per-event inputs.
          research p28-vtec acquisition-check <baseline> --profile p28-304 --confirm-profile
                    --baseline-binding <private-json> --runner <rust-executable>
                    --scenario <bounded-capture-scenario.json> --output <new-private-json>
                    [--composition acquisition-only|scheduled-g-f-threshold]
                    [--allow-assumption oki.add-er1-a] [--allow-assumption oki.add-er3-a]
                    [--derived <M1g-child> --plan <composed-plan> --export-report <receipt>
                     --compensation-definition <reviewed-signed-private-json>]
                    [--envelope-scaling <M1h-scenario> --envelope-slot <slot-id>
                     --envelope-rpm <N/D> --envelope-rpm-provenance <text>]
                    Persistent seeded execution with explicit peripheral snapshots, not ECU boot or physical RPM.

        ROM outputs are for PC inspection only unless separately validated.
        Exit codes: 0 success, 1 operation error, 2 usage error, 3 verification failure.
        """;

}
