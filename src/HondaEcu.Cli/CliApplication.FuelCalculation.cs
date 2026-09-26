using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28FuelCalculationChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel calculation-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.19.0> --scenario <m2k-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2k requires explicit confirmation and exact baseline binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2k inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath])); var scenario = P28FuelCalculationScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28FuelCalculationValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2k image={sequence.Image} scratch={sequence.ScratchPattern:X2}, initial context={scenario.InitialState.Selector0127:X2}.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
            {
                var downstream = row.Actual.GetProperty("downstream");
                var local = downstream;
                if (local.ValueKind == System.Text.Json.JsonValueKind.Null)
                    foreach (var name in new[] { "consumer", "lookup", "selection", "loadAxis", "rpmAxes" })
                    {
                        var candidate = row.Actual.GetProperty("prefix").GetProperty(name);
                        if (candidate.ValueKind != System.Text.Json.JsonValueKind.Null) { local = candidate; break; }
                    }
                var stop = local.ValueKind == System.Text.Json.JsonValueKind.Null ? "NotRun" : local.GetProperty("result").GetProperty("stopPc").GetInt32().ToString("X4");
                int? narrowed = null;
                if (downstream.ValueKind != System.Text.Json.JsonValueKind.Null)
                    foreach (var e in downstream.GetProperty("events").EnumerateArray()) if (e[0].GetInt32() == 0x21E8) narrowed = e[3].GetInt32();
                var map = row.SelectedOrigin == P28FuelMapContract.Map0Origin ? "map_0" : row.SelectedOrigin == P28FuelMapContract.Map1Origin ? "map_1" : "NotRun";
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} prefix={row.PrefixDisposition} map={map} origin={row.SelectedOrigin?.ToString("X4") ?? "NotRun"} lookup={row.Lookup?.ToString() ?? "NotRun"} " +
                    $"DATA0140={row.Data0140?.ToString() ?? "NotRun"} read0140={row.NativeRead0140?.ToString() ?? "NotRun"} factor0158={row.Factor0158?.ToString() ?? "NotRun"} " +
                    $"product={row.Product?.ToString() ?? "NotRun"} narrowed={narrowed?.ToString() ?? "NotRun"} er2={row.Output?.ToString() ?? "NotRun"} stop={stop}.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("Read-only strict fuel numeric fragment; 1350→21DB is scripted on the same CPU/RAM. er2 is a raw scaled component; reader227A static-only. PcInspectionOnly / NotFlashReady; physical units unknown; GUI/hardware NotRun. No BIN written. Strict M2i remains Blocked.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
