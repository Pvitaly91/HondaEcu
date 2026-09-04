using System.Globalization;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> OracleAsync(string[] args, CancellationToken cancellationToken)
    {
        if (args.Length == 0)
        {
            throw new CliUsageException(
                "Usage: hondaecu oracle <create-manifest|add-case|analyze|compare|export-candidate|preflight> ...");
        }

        return args[0] switch
        {
            "create-manifest" => await OracleCreateManifestAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "add-case" => await OracleAddCaseAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "analyze" => await OracleAnalyzeAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "compare" => await OracleCompareAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "export-candidate" => await OracleExportCandidateAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "preflight" => await OraclePreflightAsync(args[1..], cancellationToken).ConfigureAwait(false),
            _ => throw new CliUsageException($"Unknown oracle command '{args[0]}'."),
        };
    }

    private async Task<int> OracleCreateManifestAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal) { "plugins-disabled" };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly(
            "tool", "tool-version", "tool-edition", "profile", "baseline", "noop", "output", "plugin", "plugins-disabled", "notes",
            "independent-noop", "resaved-noop", "transformation-profile", "rounding-domain", "domain-evidence");
        command.RequirePositionals(
            0,
            "hondaecu oracle create-manifest --tool <name> --tool-version <version> --profile <id> --baseline <rom> --noop <rom> --output <json> [--plugins-disabled] [--plugin <name>]");

        var profileId = command.Required("profile");
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(profileId);
        var baselinePath = ResolvePath(command.Required("baseline"));
        var noOpPath = ResolvePath(command.Required("noop"));
        var baseline = await Task.Run(() => RomImage.Load(baselinePath), cancellationToken).ConfigureAwait(false);
        var noOp = await Task.Run(() => RomImage.Load(noOpPath), cancellationToken).ConfigureAwait(false);
        baseline.ValidateExactSize(profile.ExpectedSize, profile.Id);
        noOp.ValidateExactSize(profile.ExpectedSize, profile.Id);

        var manifest = OracleManifestService.Create(
            command.Required("tool"),
            command.Required("tool-version"),
            profile.Id,
            baselinePath,
            noOpPath,
            command.HasFlag("plugins-disabled"),
            command.Many("plugin"),
            command.Optional("notes"),
            toolEdition: command.Optional("tool-edition"),
            independentNoOpPath: command.Optional("independent-noop") is { } independent ? ResolvePath(independent) : null,
            resavedNoOpPath: command.Optional("resaved-noop") is { } resaved ? ResolvePath(resaved) : null,
            transformationProfileId: command.Optional("transformation-profile"));
        var domains = command.Many("rounding-domain");
        if (domains.Count > 0)
        {
            var documentation = command.Required("domain-evidence");
            var parsedDomains = new Dictionary<string, OracleRoundingDomain>(StringComparer.OrdinalIgnoreCase);
            foreach (var domain in domains)
            {
                var parts = domain.Split('=', 2);
                var limits = parts.Length == 2 ? parts[1].Split(':', 2) : Array.Empty<string>();
                if (parts.Length != 2 || string.IsNullOrWhiteSpace(parts[0]) || limits.Length != 2)
                {
                    throw new CliUsageException("Use '--rounding-domain parameter=minimum:maximum' for the continuous unrounded raw-input domain.");
                }
                var minimum = ParseNumber(limits[0], "Rounding-domain minimum");
                var maximum = ParseNumber(limits[1], "Rounding-domain maximum");
                if (minimum > maximum || !parsedDomains.TryAdd(parts[0], new OracleRoundingDomain(minimum, maximum, documentation)))
                {
                    throw new CliUsageException("Rounding domain must have ordered bounds and each parameter may be specified only once.");
                }
            }
            manifest = manifest with { RoundingDomains = parsedDomains };
        }
        var outputPath = ResolvePath(command.Required("output"));
        await Task.Run(
            () => OracleManifestService.Save(manifest, outputPath),
            cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync($"Oracle manifest: {outputPath}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Baseline SHA-256: {manifest.BaselineHash.Sha256}").ConfigureAwait(false);
        await _output.WriteLineAsync($"No-op SHA-256: {manifest.NoOpHash.Sha256}").ConfigureAwait(false);
        await _output.WriteLineAsync($"No-op normalization ranges: {manifest.NoOpNormalizationRanges.Count}")
            .ConfigureAwait(false);
        return Success;
    }

    private async Task<int> OracleAddCaseAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("manifest", "parameter", "value", "rom", "notes", "displayed-value", "role", "observation-id");
        command.RequirePositionals(
            0,
            "hondaecu oracle add-case --manifest <json> --parameter <id> --value <number> --rom <rom> [--notes <text>] [--displayed-value <number>]");

        var manifestPath = ResolvePath(command.Required("manifest"));
        var value = ParseNumber(command.Required("value"), "Oracle case value");
        var displayedValueText = command.Optional("displayed-value");
        double? displayedValue = displayedValueText is null
            ? null
            : ParseNumber(displayedValueText, "Displayed oracle value");
        var role = command.Optional("role") switch
        {
            null or "training" => OracleObservationRole.Training,
            "holdout" => OracleObservationRole.Holdout,
            _ => throw new CliUsageException("Oracle observation '--role' must be training or holdout."),
        };
        var manifest = await Task.Run(
            () => OracleManifest.Load(manifestPath),
            cancellationToken).ConfigureAwait(false);
        var updated = await Task.Run(
            () => OracleManifestService.AddCase(
                manifest,
                command.Required("parameter"),
                value,
                ResolvePath(command.Required("rom")),
                command.Optional("notes"),
                displayedValue,
                role: role,
                observationId: command.Optional("observation-id")),
            cancellationToken).ConfigureAwait(false);
        await Task.Run(
            () => OracleManifestService.Save(updated, manifestPath, overwrite: true),
            cancellationToken).ConfigureAwait(false);

        var added = updated.Cases[^1];
        var displayed = added.DisplayedValue is null
            ? string.Empty
            : $", reopened display={added.DisplayedValue.Value.ToString("G17", CultureInfo.InvariantCulture)}";
        await _output.WriteLineAsync(
            $"Added case {added.ParameterId}: requested={added.EngineeringValue.ToString("G17", CultureInfo.InvariantCulture)}{displayed}; role={Kebab(added.Role)}, observation={added.ObservationId}; SHA-256 {added.RomHash.Sha256}.")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Case diff ranges: {added.DiffRanges.Count}").ConfigureAwait(false);
        return Success;
    }

    private async Task<int> OracleAnalyzeAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("manifest", "output", "select-candidate", "selection-reason");
        command.RequirePositionals(
            0,
            "hondaecu oracle analyze --manifest <json> --output <analysis.json>");

        var manifest = await Task.Run(
            () => OracleManifest.Load(ResolvePath(command.Required("manifest"))),
            cancellationToken).ConfigureAwait(false);
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(manifest.ProfileId);
        var analysis = await Task.Run(
            () => OracleAnalyzer.Analyze(manifest, profile),
            cancellationToken).ConfigureAwait(false);
        analysis = ApplyOracleSelections(analysis, command.Many("select-candidate"), command.Optional("selection-reason"));
        var outputPath = ResolvePath(command.Required("output"));
        await Task.Run(
            () => analysis.Save(outputPath),
            cancellationToken).ConfigureAwait(false);

        await WriteOracleAnalysisSummaryAsync(analysis).ConfigureAwait(false);
        await _output.WriteLineAsync($"Oracle analysis: {outputPath}").ConfigureAwait(false);
        return Success;
    }

    private async Task<int> OracleCompareAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("crome", "hts", "output", "crome-candidate", "hts-candidate", "selection-reason");
        command.RequirePositionals(
            0,
            "hondaecu oracle compare --crome <manifest.json> --hts <manifest.json> --output <json>");

        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var crome = await LoadVerifiedManifestAnalysisAsync(
            ResolvePath(command.Required("crome")), catalog, "crome", cancellationToken).ConfigureAwait(false);
        var hts = await LoadVerifiedManifestAnalysisAsync(
            ResolvePath(command.Required("hts")), catalog, "hts", cancellationToken).ConfigureAwait(false);
        crome = ApplyOracleSelections(crome, command.Many("crome-candidate"), command.Optional("selection-reason"));
        hts = ApplyOracleSelections(hts, command.Many("hts-candidate"), command.Optional("selection-reason"));
        var comparison = CrossEditorComparer.Compare(crome, hts);
        var outputPath = ResolvePath(command.Required("output"));
        await Task.Run(
            () => comparison.Save(outputPath),
            cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync($"Same baseline: {comparison.SameBaseline}").ConfigureAwait(false);
        await _output.WriteLineAsync($"At least one confirmed parameter: {comparison.HasAnyConfirmedParameter}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"All requested parameters confirmed: {comparison.AllRequestedParametersConfirmed}")
            .ConfigureAwait(false);
        foreach (var parameter in comparison.Parameters)
        {
            await _output.WriteLineAsync(
                $"{parameter.ParameterId}: offset={parameter.SameOffset}, width={parameter.SameWidth}, endian={parameter.SameEndianness}, conversion={parameter.SameConversion}, rounding={parameter.SameRounding}, common={parameter.HasCommonCandidate}")
                .ConfigureAwait(false);
            foreach (var reason in parameter.ConflictReasons)
            {
                await _output.WriteLineAsync($"  conflict: {reason}").ConfigureAwait(false);
            }
        }

        await _output.WriteLineAsync($"Crome additional ranges: {comparison.CromeAdditionalRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"HTS additional ranges: {comparison.HtsAdditionalRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Crome observed checksum ranges: {comparison.CromeObservedChecksumRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"HTS observed checksum ranges: {comparison.HtsObservedChecksumRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Cross-editor report: {outputPath}").ConfigureAwait(false);
        return Success;
    }

    private async Task<int> OracleExportCandidateAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("analysis", "parameter", "offset", "encoding", "type", "output", "candidate-id");
        command.RequirePositionals(
            0,
            "hondaecu oracle export-candidate --analysis <json> --candidate-id <id> [--output <fragment.json>] (legacy selector: --parameter <id> --offset <offset> --encoding <type>)");

        var encoding = command.Optional("encoding");
        var typeAlias = command.Optional("type");
        if (encoding is not null && typeAlias is not null)
        {
            throw new CliUsageException("Use only one of '--encoding' and '--type'.");
        }

        var candidateId = command.Optional("candidate-id");
        if (candidateId is not null && (encoding is not null || typeAlias is not null || command.Optional("offset") is not null || command.Optional("parameter") is not null))
        {
            throw new CliUsageException("Use '--candidate-id' alone, or the legacy '--parameter --offset --encoding' selector.");
        }
        var analysis = await Task.Run(
            () => OracleAnalysis.Load(ResolvePath(command.Required("analysis"))),
            cancellationToken).ConfigureAwait(false);
        var fragment = candidateId is not null
            ? OracleAnalyzer.ExportCandidate(analysis, candidateId)
            : OracleAnalyzer.ExportCandidate(analysis, command.Required("parameter"), ParseRomOffset(command.Required("offset")),
                ParseEncodingType(encoding ?? typeAlias ?? throw new CliUsageException("Missing required option '--encoding'.")));
        var output = command.Optional("output");
        if (output is null)
        {
            await _output.WriteLineAsync(fragment).ConfigureAwait(false);
        }
        else
        {
            var outputPath = ResolvePath(output);
            await Task.Run(
                () => AtomicFile.WriteAllText(outputPath, fragment),
                cancellationToken).ConfigureAwait(false);
            await _output.WriteLineAsync($"Candidate fragment: {outputPath}").ConfigureAwait(false);
        }

        return Success;
    }

    private static async Task<OracleAnalysis> LoadVerifiedManifestAnalysisAsync(
        string path,
        ProfileCatalog catalog,
        string expectedTool,
        CancellationToken cancellationToken)
    {
        var manifest = await Task.Run(() => OracleManifest.Load(path), cancellationToken).ConfigureAwait(false);
        if (!OracleProvenance.IsExpectedTool(manifest.ReferenceTool, expectedTool))
        {
            throw new InvalidDataException(
                $"The --{expectedTool} manifest identifies reference tool '{manifest.ReferenceTool}', not {expectedTool}.");
        }

        return await Task.Run(
            () => OracleAnalyzer.Analyze(manifest, catalog.Get(manifest.ProfileId)),
            cancellationToken).ConfigureAwait(false);
    }

    private async Task WriteOracleAnalysisSummaryAsync(OracleAnalysis analysis)
    {
        await _output.WriteLineAsync($"No-op normalization ranges: {analysis.NoOpNormalizationRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Excluded checksum regions: {analysis.ExcludedChecksumRegions.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Observed checksum-change ranges: {analysis.ObservedChecksumChangedRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Actually changed ranges: {analysis.ActualChangedRanges.Count}; hypothesis coverage: {analysis.CandidateHypothesisRanges.Count}; explained: {analysis.ExplainedChangedRanges.Count}; unexplained: {analysis.UnexplainedChangedRanges.Count}")
            .ConfigureAwait(false);
        foreach (var parameter in analysis.Parameters)
        {
            await _output.WriteLineAsync(
                $"{parameter.ParameterId}: {parameter.CaseCount} case(s), {parameter.Candidates.Count} candidate(s); independent training={parameter.IndependentTrainingPointCount}, holdout={parameter.IndependentHoldoutPointCount}, repeats={parameter.RepeatedObservationCount}")
                .ConfigureAwait(false);
            foreach (var candidate in parameter.Candidates)
            {
                await _output.WriteLineAsync(string.Create(
                    CultureInfo.InvariantCulture,
                    $"  id={candidate.CandidateId} offset=0x{candidate.Offset:X4} width={candidate.Width} encoding={Kebab(candidate.EncodingType)} endian={Kebab(candidate.Endianness)} scale={candidate.Scale:G17} constant={candidate.OffsetConstant:G17} numerator={candidate.Numerator:G17} denominatorOffset={candidate.DenominatorOffset:G17} rounding={(candidate.RoundingPolicy is { } rounding ? Kebab(rounding) : "unresolved")} compatible=[{string.Join(',', candidate.CompatibleRoundingPolicies.Select(policy => Kebab(policy)))}] fitScore={candidate.FitScore:F6} freeCoefficients={candidate.FreeCoefficientCount} trainingMaxError={candidate.TrainingMaximumAbsoluteError:G6} holdoutMaxError={candidate.HoldoutMaximumAbsoluteError:G6} holdoutExactBytes={candidate.HoldoutExactByteMatch}"))
                    .ConfigureAwait(false);
                await _output.WriteLineAsync($"    {candidate.ExtrapolationWarning}").ConfigureAwait(false);
            }

            foreach (var warning in parameter.Warnings)
            {
                await _error.WriteLineAsync($"warning: {parameter.ParameterId}: {warning}").ConfigureAwait(false);
            }
        }
    }

    private static OracleAnalysis ApplyOracleSelections(OracleAnalysis analysis, IReadOnlyList<string> selections, string? rationale)
    {
        if (selections.Count > 0 && string.IsNullOrWhiteSpace(rationale))
        {
            throw new CliUsageException("Candidate selection requires '--selection-reason'; selection alone adds no evidence.");
        }
        var selectedParameters = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var selection in selections)
        {
            var parts = selection.Split('=', 2);
            if (parts.Length != 2 || string.IsNullOrWhiteSpace(parts[0]) || string.IsNullOrWhiteSpace(parts[1]) || !selectedParameters.Add(parts[0]))
            {
                throw new CliUsageException("Specify each candidate once as 'parameter=candidate-id'.");
            }
            analysis = OracleAnalyzer.SelectCandidate(analysis, parts[0], parts[1], rationale!);
        }
        return analysis;
    }

    private static int ParseRomOffset(string text)
    {
        var style = NumberStyles.Integer;
        var value = text;
        if (text.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
        {
            style = NumberStyles.AllowHexSpecifier;
            value = text[2..];
        }

        if (!int.TryParse(value, style, CultureInfo.InvariantCulture, out var offset) || offset < 0)
        {
            throw new CliUsageException($"Invalid ROM offset '{text}'.");
        }

        return offset;
    }

    private static ParameterEncodingType ParseEncodingType(string text)
    {
        var normalized = new string(text.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());
        foreach (var value in Enum.GetValues<ParameterEncodingType>())
        {
            var candidate = new string(value.ToString().Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());
            if (candidate == normalized)
            {
                return value;
            }
        }

        throw new CliUsageException($"Unsupported encoding type '{text}'.");
    }
}
