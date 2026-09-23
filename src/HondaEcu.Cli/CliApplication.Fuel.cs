using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28FuelResearchAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length > 0 && args[0] == "export")
            return await P28FuelMapExportAsync(args[1..], cancellationToken).ConfigureAwait(false);
        if (args.Length > 0 && args[0] == "vtec-chain-check")
            return await P28FuelVtecChainCheckAsync(args[1..], cancellationToken).ConfigureAwait(false);
        if (args.Length == 0 || args[0] is not ("maps-inspect" or "lookup-check"))
            throw new CliUsageException("Usage: hondaecu research p28-fuel <maps-inspect|lookup-check|vtec-chain-check|export> ...");
        var check = args[0] == "lookup-check";
        var command = CommandLine.Parse(args[1..], new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly(check
            ? ["profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output"]
            : ["profile", "confirm-profile", "baseline-binding", "output"]);
        command.RequirePositionals(1, check
            ? "hondaecu research p28-fuel lookup-check <baseline.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <rust-runner> --scenario <scenario.json> --output <new-private-validation.json>"
            : "hondaecu research p28-fuel maps-inspect <baseline.bin> --profile p28-304 [--confirm-profile --baseline-binding <binding.json>] --output <new-private-map-report.json>");
        if (check && !command.HasFlag("confirm-profile")) throw new CliUsageException("Fuel-map native execution requires --confirm-profile and exact binding.");
        string? OptionalPath(string name) => command.Optional(name) is { } value ? ResolvePath(value) : null;
        var baselinePath = ResolvePath(command.Positionals[0]);
        var outputPath = ResolvePath(command.Required("output"));
        var bindingPath = check ? ResolvePath(command.Required("baseline-binding")) : OptionalPath("baseline-binding");
        var runnerPath = check ? ResolvePath(command.Required("runner")) : null;
        var scenarioPath = check ? ResolvePath(command.Required("scenario")) : null;
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var inputPaths = new[] { baselinePath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, inputPaths);
        var snapshot = await Task.Run(() => inputPaths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 1_048_576) : File.ReadAllBytes(path),
            StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) !=
            P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading fuel-map inputs.");
        var baseline = RomImage.FromBytes(snapshot[baselinePath], baselinePath);
        var binding = bindingPath is null ? null : P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        RequireCaptureInputSnapshot(snapshot);
        object report; var failure = false;
        if (check)
        {
            var scenario = P28FuelMapScenario.Parse(utf8.GetString(snapshot[scenarioPath!]));
            var validation = await P28FuelMapValidator.ExecuteAsync(baseline, profile, binding!, true, runnerPath!, scenario,
                cancellationToken: cancellationToken).ConfigureAwait(false);
            report = validation; failure = validation.HasFailure;
            foreach (var image in validation.Images) foreach (var sequence in image.Sequences)
                    await _output.WriteLineAsync($"fuel image={image.Image}, scratch={sequence.ScratchPattern}: calls={sequence.Checkpoints.Count}, strict={sequence.Checkpoints.Count(row => row.Disposition == "StrictMatch")}, other={sequence.Checkpoints.Count(row => row.Disposition != "StrictMatch")}").ConfigureAwait(false);
            await _output.WriteLineAsync($"A/B witnesses={validation.Comparisons.Count(row => row.Witness == true)}; mutation bytes={validation.ChangedOffsets.Count}.").ConfigureAwait(false);
        }
        else
        {
            var inspection = P28FuelMapInspector.Inspect(baseline, profile, binding, command.HasFlag("confirm-profile"));
            report = inspection; failure = binding is not null && !inspection.InterpretationApplied;
            if (inspection.InterpretationApplied)
            {
                foreach (var map in inspection.Maps)
                {
                    await _output.WriteLineAsync($"{map.Id}: {map.Rows}x{map.Columns}, cells 0x{map.Origin:X4}..0x{map.EndInclusive:X4}, column metadata 0x{map.MetadataOrigin:X4}..0x{map.MetadataEndInclusive:X4}").ConfigureAwait(false);
                    await _output.WriteLineAsync($"  first row: {string.Join(' ', map.Cells[0])}").ConfigureAwait(false);
                    await _output.WriteLineAsync($"  last row:  {string.Join(' ', map.Cells[^1])}").ConfigureAwait(false);
                }
                foreach (var axis in inspection.Axes) await _output.WriteLineAsync($"{axis.Id}: {string.Join(' ', axis.RawValues)}").ConfigureAwait(false);
            }
            else await _output.WriteLineAsync("Fuel-map interpretation not applied; general image identity only.").ConfigureAwait(false);
        }
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        await _output.WriteLineAsync("Read-only fuel-map research. PcInspectionOnly / NotFlashReady; physical RPM/MAP/AFR unavailable; GUI r3 paused/NotRun; D1 interactive GUI acceptance NotRun; hardware/full boot NotRun. No BIN written.").ConfigureAwait(false);
        return failure ? VerificationFailed : Success;
    }
}
