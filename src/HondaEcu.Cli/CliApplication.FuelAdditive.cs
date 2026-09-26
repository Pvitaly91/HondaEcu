using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28FuelAdditiveChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel additive-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.20.0> --scenario <m2l-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2l requires explicit confirmation and exact baseline binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath }; ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath])))) throw new InvalidDataException("Profile changed while loading M2l inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath])); var scenario = P28FuelAdditiveScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28FuelAdditiveValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot); await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2l image={sequence.Image} scratch={sequence.ScratchPattern:X2} initial selector={scenario.InitialState.Fuel.Selector0127:X2}.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
            {
                var stages = row.Actual.GetProperty("stages");
                var local = stages.GetArrayLength() == 0 ? default(System.Text.Json.JsonElement) : stages[stages.GetArrayLength() - 1];
                if (local.ValueKind == System.Text.Json.JsonValueKind.Undefined)
                    foreach (var name in new[] { "consumer", "lookup", "selection", "loadAxis", "rpmAxes" })
                    { var candidate = row.Actual.GetProperty("prefix").GetProperty(name); if (candidate.ValueKind != System.Text.Json.JsonValueKind.Null) { local = candidate; break; } }
                var stop = local.ValueKind == System.Text.Json.JsonValueKind.Undefined ? "NotRun" : local.GetProperty("result").GetProperty("stopPc").GetInt32().ToString("X4");
                var map = row.SelectedOrigin == P28FuelMapContract.Map0Origin ? "map_0" : row.SelectedOrigin == P28FuelMapContract.Map1Origin ? "map_1" : "NotRun";
                var signed = row.Correction is int word ? unchecked((short)word).ToString() : "NotRun";
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} prefix={row.PrefixDisposition} map={map} origin={row.SelectedOrigin?.ToString("X4") ?? "NotRun"} DATA0140={row.Data0140?.ToString() ?? "NotRun"} retained0158={row.Actual.GetProperty("sourcesAfter").GetProperty("factor0158").GetInt32()} correction-word={row.Correction?.ToString("X4") ?? "NotRun"} signed={signed} scaled-A/er2={row.Component?.ToString() ?? "NotRun"} corrected-A/er3={row.Corrected?.ToString() ?? "NotRun"} stores03A2/03B4={row.Store03a2?.ToString() ?? "NotRun"}/{row.Store03b4?.ToString() ?? "NotRun"} stop={stop}.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("Read-only strict native2194->2204 producer/scaling/XCHG/VCAL4/stores, native helpers and return; 1350->2194 scripted on one CPU/RAM. Gate217A static precondition, bypass NotEvaluated. PcInspectionOnly / NotFlashReady; physical units unknown; strict M2i Blocked; GUI/hardware NotRun; no BIN written.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
