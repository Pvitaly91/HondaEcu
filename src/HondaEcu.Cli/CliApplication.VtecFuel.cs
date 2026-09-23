using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> P28FuelVtecChainCheckAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args, new HashSet<string>(StringComparer.Ordinal) { "confirm-profile" });
        command.EnsureOnly("profile", "confirm-profile", "baseline-binding", "runner", "scenario", "output", "allow-assumption");
        command.RequirePositionals(1, "hondaecu research p28-fuel vtec-chain-check <original.bin> --profile p28-304 --confirm-profile --baseline-binding <binding.json> --runner <runner> --scenario <m2f-scenario.json> --output <new-private-report.json> [--allow-assumption oki.subb-a-off-n8-encoding]");
        if (!command.HasFlag("confirm-profile")) throw new CliUsageException("M2f requires explicit profile confirmation and exact binding.");
        IReadOnlyList<string> assumptions;
        try { assumptions = P28VtecFuelValidator.ValidateAssumptions(command.Many("allow-assumption")); }
        catch (ArgumentException e) { throw new CliUsageException(e.Message); }
        var originalPath = ResolvePath(command.Positionals[0]);
        var bindingPath = ResolvePath(command.Required("baseline-binding"));
        var runnerPath = ResolvePath(command.Required("runner"));
        var scenarioPath = ResolvePath(command.Required("scenario"));
        var outputPath = ResolvePath(command.Required("output"));
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(command.Required("profile"));
        var paths = new[] { originalPath, bindingPath, runnerPath, scenarioPath, profile.SourcePath };
        ProtectNewResearchDestination(outputPath, paths);
        var snapshot = await Task.Run(() => paths.OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase).ToDictionary(path => path,
            path => string.Equals(path, scenarioPath, StringComparison.OrdinalIgnoreCase) ? ReadBoundedCaptureInput(path, 1_048_576) : File.ReadAllBytes(path),
            StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } profilePath && P28VtecInspector.ComputeProfileDigest(profile) !=
            P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[profilePath]))))
            throw new InvalidDataException("Profile changed while loading M2f inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Parse(utf8.GetString(snapshot[bindingPath]));
        var scenario = P28VtecFuelScenario.Parse(utf8.GetString(snapshot[scenarioPath]));
        RequireCaptureInputSnapshot(snapshot);
        var report = await P28VtecFuelValidator.ExecuteAsync(original, profile, binding, true, runnerPath, scenario,
            assumptions, cancellationToken: cancellationToken).ConfigureAwait(false);
        RequireCaptureInputSnapshot(snapshot);
        await WriteJsonFileAsync(outputPath, report, cancellationToken).ConfigureAwait(false);
        foreach (var sequence in report.Sequences)
        {
            var rows = sequence.Checkpoints;
            await _output.WriteLineAsync($"M2f image={sequence.ImageIndex} scratch={sequence.ScratchPattern:X2}: " +
                $"strict={rows.Count(row => row.Disposition == "StrictMatch")}, conditional={rows.Count(row => row.Disposition == "ConditionalMatch")}, " +
                $"unresolved={rows.Count(row => row.Disposition == "Unresolved")}, NotRun={rows.Count(row => row.Disposition == "NotRun")}; " +
                $"selector transitions={rows.Count(row => row.Status == 0 && row.SelectorBefore != row.Selector0127)}.").ConfigureAwait(false);
            foreach (var row in rows)
            {
                if (row.Status != 0)
                {
                    await _output.WriteLineAsync($"  event={row.Index}: {row.Disposition}; fuel lookup/consumer NotRun; " +
                        (row.Disposition == "NotRun" ? "no next-event inputs applied." : "stopped before the fuel tail.")).ConfigureAwait(false);
                    continue;
                }
                var call = scenario.Calls[row.Index];
                await _output.WriteLineAsync($"  event={row.Index}: raw load/rpm0/rpm1={call.RawLoad}/{call.RawMap0Rpm}/{call.RawMap1Rpm}, " +
                    $"compact={call.Decision.CompactCode}, feedback0119={call.Decision.Snapshot0119}, " +
                    $"native ticks fast/slow={call.Decision.FastTicks}/{call.Decision.SlowTicks}; " +
                    $"P1 request={row.RequestP1}, mirror0127.2={row.RequestMirror0127}, " +
                    $"selector0127.1={row.Selector0127}, actual map={row.SelectedMap}, lookup={row.Lookup}, " +
                    $"DATA0140={row.Data0140}, consumerChanged={row.ConsumerChanged}; {row.Disposition}; {row.SelectorCause}.").ConfigureAwait(false);
            }
        }
        await _output.WriteLineAsync("M2f read-only native decision→fuel tail; scripted axis/counter caller, no physical VTEC/RPM/MAP/AFR or full boot. PcInspectionOnly / NotFlashReady. GUI and hardware NotRun. No BIN written.").ConfigureAwait(false);
        return report.HasFailure ? VerificationFailed : Success;
    }
}
