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
                "Usage: hondaecu oracle <create-manifest|add-case|analyze|compare|export-candidate> ...");
        }

        return args[0] switch
        {
            "create-manifest" => await OracleCreateManifestAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "add-case" => await OracleAddCaseAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "analyze" => await OracleAnalyzeAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "compare" => await OracleCompareAsync(args[1..], cancellationToken).ConfigureAwait(false),
            "export-candidate" => await OracleExportCandidateAsync(args[1..], cancellationToken).ConfigureAwait(false),
            _ => throw new CliUsageException($"Unknown oracle command '{args[0]}'."),
        };
    }

    private async Task<int> OracleCreateManifestAsync(string[] args, CancellationToken cancellationToken)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal) { "plugins-disabled" };
        var command = CommandLine.Parse(args, flags);
        command.EnsureOnly(
            "tool", "tool-version", "profile", "baseline", "noop", "output", "plugin", "plugins-disabled", "notes");
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
            command.Optional("notes"));
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
        command.EnsureOnly("manifest", "parameter", "value", "rom", "notes", "displayed-value");
        command.RequirePositionals(
            0,
            "hondaecu oracle add-case --manifest <json> --parameter <id> --value <number> --rom <rom> [--notes <text>] [--displayed-value <number>]");

        var manifestPath = ResolvePath(command.Required("manifest"));
        var value = ParseNumber(command.Required("value"), "Oracle case value");
        var displayedValueText = command.Optional("displayed-value");
        double? displayedValue = displayedValueText is null
            ? null
            : ParseNumber(displayedValueText, "Displayed oracle value");
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
                displayedValue),
            cancellationToken).ConfigureAwait(false);
        await Task.Run(
            () => OracleManifestService.Save(updated, manifestPath, overwrite: true),
            cancellationToken).ConfigureAwait(false);

        var added = updated.Cases[^1];
        var displayed = added.DisplayedValue is null
            ? string.Empty
            : $", reopened display={added.DisplayedValue.Value.ToString("G17", CultureInfo.InvariantCulture)}";
        await _output.WriteLineAsync(
            $"Added case {added.ParameterId}: requested={added.EngineeringValue.ToString("G17", CultureInfo.InvariantCulture)}{displayed}; SHA-256 {added.RomHash.Sha256}.")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Case diff ranges: {added.DiffRanges.Count}").ConfigureAwait(false);
        return Success;
    }

    private async Task<int> OracleAnalyzeAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("manifest", "output");
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
        command.EnsureOnly("crome", "hts", "output");
        command.RequirePositionals(
            0,
            "hondaecu oracle compare --crome <manifest.json> --hts <manifest.json> --output <json>");

        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var crome = await LoadVerifiedManifestAnalysisAsync(
            ResolvePath(command.Required("crome")), catalog, "crome", cancellationToken).ConfigureAwait(false);
        var hts = await LoadVerifiedManifestAnalysisAsync(
            ResolvePath(command.Required("hts")), catalog, "hts", cancellationToken).ConfigureAwait(false);
        var comparison = CrossEditorComparer.Compare(crome, hts);
        var outputPath = ResolvePath(command.Required("output"));
        await Task.Run(
            () => comparison.Save(outputPath),
            cancellationToken).ConfigureAwait(false);

        await _output.WriteLineAsync($"Same baseline: {comparison.SameBaseline}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Cross-editor confirmed candidate: {comparison.IsCrossEditorConfirmed}")
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
        command.EnsureOnly("analysis", "parameter", "offset", "encoding", "type", "output");
        command.RequirePositionals(
            0,
            "hondaecu oracle export-candidate --analysis <json> --parameter <id> --offset <offset> --encoding <type> [--output <fragment.json>]");

        var encoding = command.Optional("encoding");
        var typeAlias = command.Optional("type");
        if (encoding is not null && typeAlias is not null)
        {
            throw new CliUsageException("Use only one of '--encoding' and '--type'.");
        }

        var typeText = encoding ?? typeAlias ?? throw new CliUsageException("Missing required option '--encoding'.");
        var offset = ParseRomOffset(command.Required("offset"));
        var type = ParseEncodingType(typeText);
        var analysis = await Task.Run(
            () => OracleAnalysis.Load(ResolvePath(command.Required("analysis"))),
            cancellationToken).ConfigureAwait(false);
        var fragment = OracleAnalyzer.ExportCandidate(analysis, command.Required("parameter"), offset, type);
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
        if (!IsExpectedOracleTool(manifest.ReferenceTool, expectedTool))
        {
            throw new InvalidDataException(
                $"The --{expectedTool} manifest identifies reference tool '{manifest.ReferenceTool}', not {expectedTool}.");
        }

        return await Task.Run(
            () => OracleAnalyzer.Analyze(manifest, catalog.Get(manifest.ProfileId)),
            cancellationToken).ConfigureAwait(false);
    }

    private static bool IsExpectedOracleTool(string actual, string expected)
    {
        var normalized = new string(actual.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());
        return expected == "crome"
            ? normalized is "crome" or "cromepro"
            : normalized is "hts" or "hondatuningsuite";
    }

    private async Task WriteOracleAnalysisSummaryAsync(OracleAnalysis analysis)
    {
        await _output.WriteLineAsync($"No-op normalization ranges: {analysis.NoOpNormalizationRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Excluded checksum regions: {analysis.ExcludedChecksumRegions.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Observed checksum-change ranges: {analysis.ObservedChecksumChangedRanges.Count}")
            .ConfigureAwait(false);
        await _output.WriteLineAsync($"Additional non-candidate ranges: {analysis.AdditionalChangedRanges.Count}")
            .ConfigureAwait(false);
        foreach (var parameter in analysis.Parameters)
        {
            await _output.WriteLineAsync(
                $"{parameter.ParameterId}: {parameter.CaseCount} case(s), {parameter.Candidates.Count} candidate(s)")
                .ConfigureAwait(false);
            foreach (var candidate in parameter.Candidates)
            {
                await _output.WriteLineAsync(string.Create(
                    CultureInfo.InvariantCulture,
                    $"  offset=0x{candidate.Offset:X4} width={candidate.Width} encoding={Kebab(candidate.EncodingType)} endian={Kebab(candidate.Endianness)} scale={candidate.Scale:G17} constant={candidate.OffsetConstant:G17} numerator={candidate.Numerator:G17} denominatorOffset={candidate.DenominatorOffset:G17} rounding={Kebab(candidate.RoundingPolicy)} confidence={candidate.Confidence:F6} meanError={candidate.MeanAbsoluteError:G6} maxError={candidate.MaximumAbsoluteError:G6}"))
                    .ConfigureAwait(false);
            }

            foreach (var warning in parameter.Warnings)
            {
                await _error.WriteLineAsync($"warning: {parameter.ParameterId}: {warning}").ConfigureAwait(false);
            }
        }
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
