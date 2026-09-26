using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28FuelFactorChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output");
        command.RequirePositionals(1, "hondaecu research p28-fuel factor-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner-0.21.0> --scenario <m2m-scenario.json> --output <new-private-report.json>");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2m requires explicit confirmation and exact baseline binding.");
        var originalPath = ResolvePath(command.Positionals[0]); var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner")); var scenarioPath = ResolvePath(command.Required("scenario")); var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 262_144) : File.ReadAllBytes(path), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2m inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28FuelFactorScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28FuelFactorValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            await _output.WriteLineAsync($"M2m image={sequence.Image} scratch={sequence.ScratchPattern:X2} initial selector={scenario.InitialState.Fuel.Selector0127:X2}.").ConfigureAwait(false);
            foreach (var row in sequence.Checkpoints)
            {
                var actual = row.Actual;
                var factorStage = actual.TryGetProperty("factorStage", out var stage) ? stage : default;
                var stages = actual.GetProperty("stages");
                var tail = stages.GetArrayLength() == 0 ? default : stages[stages.GetArrayLength() - 1];
                var prefixStage = default(JsonElement);
                foreach (var name in new[] { "consumer", "lookup", "selection", "loadAxis", "rpmAxes" })
                {
                    var candidate = actual.GetProperty("prefix").GetProperty(name);
                    if (candidate.ValueKind != JsonValueKind.Null) { prefixStage = candidate; break; }
                }
                static string NativeStop(JsonElement native) => native.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null
                    ? "NotRun" : native.GetProperty("result").GetProperty("stopPc").GetInt32().ToString("X4");
                var map = row.SelectedOrigin == P28FuelMapContract.Map0Origin ? "map_0" : row.SelectedOrigin == P28FuelMapContract.Map1Origin ? "map_1" : "NotRun";
                var signed = row.Correction is int word ? unchecked((short)word).ToString() : "NotRun";
                var sources = JsonSerializer.Serialize(actual.GetProperty("sourcesAfter"));
                await _output.WriteLineAsync($"  event={row.Index} {row.Disposition} prefix={row.PrefixDisposition} map={map} origin={row.SelectedOrigin?.ToString("X4") ?? "NotRun"} " +
                    $"DATA0140={row.Data0140?.ToString() ?? "NotRun"} raw-sources(after)={sources} " +
                    $"native0158={row.NativeFactor0158?.ToString() ?? "NotRun"} 0158-before/after={row.Factor0158Before?.ToString() ?? "NotRun"}/{row.Factor0158After?.ToString() ?? "NotRun"} provenance={row.FactorProvenance} " +
                    $"correction-word={row.Correction?.ToString("X4") ?? "NotRun"} signed={signed} scaled-A/er2={row.Component?.ToString() ?? "NotRun"} corrected-A/er3={row.Corrected?.ToString() ?? "NotRun"} " +
                    $"stores03A2/03B4={row.Store03a2?.ToString() ?? "NotRun"}/{row.Store03b4?.ToString() ?? "NotRun"} prefix-native-stop={NativeStop(prefixStage)} factor-native-stop={NativeStop(factorStage)} tail-native-stop={NativeStop(tail)}.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("Read-only native DATA0158 producer before actual reader21DD on one CPU/RAM; source snapshots and routine scheduling are scripted, not a recovered main loop. Continuous M2l2194->2204 includes M2k scaling, XCHG/VCAL4/helpers/RT and software stores; no enter/reset at21DB/21F2. Held is not established for the supported producer path. PcInspectionOnly / NotFlashReady; physical units unavailable; strict M2i Blocked; GUI/hardware/full boot NotRun; no BIN written.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
