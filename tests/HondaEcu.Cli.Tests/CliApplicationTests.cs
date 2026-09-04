using System.Reflection;
using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class CliApplicationTests
{
    [Fact]
    public void ExecutableAssembly_IsNamedHondaEcu()
    {
        Assert.Equal("hondaecu", typeof(Program).Assembly.GetName().Name);
    }

    [Fact]
    public async Task NoArguments_ShowsHelp()
    {
        using var workspace = new TemporaryWorkspace();
        var result = await workspace.RunAsync();

        Assert.Equal(CliApplication.Success, result.ExitCode);
        Assert.Contains("Usage: hondaecu", result.Output, StringComparison.Ordinal);
        Assert.Empty(result.Error);
    }

    [Fact]
    public async Task UnknownCommand_ReturnsUsageErrorWithoutStackTrace()
    {
        using var workspace = new TemporaryWorkspace();
        var result = await workspace.RunAsync("explode");

        Assert.Equal(CliApplication.UsageError, result.ExitCode);
        Assert.Contains("Unknown command 'explode'", result.Error, StringComparison.Ordinal);
        Assert.DoesNotContain(" at ", result.Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Inspect_ReportsHashesCountsPreviewAndUnknownIdentity()
    {
        using var workspace = new TemporaryWorkspace();
        var rom = workspace.CreateRom("inspect.dat", bytes =>
        {
            bytes[0] = 0x12;
            bytes[1] = 0xFF;
        });

        var result = await workspace.RunAsync("inspect", rom);

        Assert.Equal(CliApplication.Success, result.ExitCode);
        Assert.Contains("Size: 32768 bytes", result.Output, StringComparison.Ordinal);
        Assert.Contains($"SHA-256: {HashUtilities.Sha256(File.ReadAllBytes(rom))}", result.Output, StringComparison.Ordinal);
        Assert.Contains("CRC32:", result.Output, StringComparison.Ordinal);
        Assert.Contains("0x00 bytes: 32766", result.Output, StringComparison.Ordinal);
        Assert.Contains("Preview: 12ff", result.Output, StringComparison.Ordinal);
        Assert.Contains("Possible profiles: none", result.Output, StringComparison.Ordinal);
        Assert.Contains("file size alone is not an identity", result.Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Diff_JsonExportHonorsMaximumRangesAndReportsPages()
    {
        using var workspace = new TemporaryWorkspace();
        var baseline = workspace.CreateRom("base.dat");
        var modified = workspace.CreateRom("modified.dat", bytes =>
        {
            bytes[1] = 0x11;
            bytes[2] = 0x22;
            bytes[0x101] = 0x33;
        });
        var reportPath = workspace.PathOf("diff.json");

        var result = await workspace.RunAsync(
            "diff", baseline, modified, "--json", "--output", reportPath, "--max-ranges", "1");

        Assert.Equal(CliApplication.Success, result.ExitCode);
        Assert.True(File.Exists(reportPath));
        using var outputJson = JsonDocument.Parse(result.Output);
        var root = outputJson.RootElement;
        Assert.Equal(3, root.GetProperty("differentByteCount").GetInt32());
        Assert.Equal(1, root.GetProperty("ranges").GetArrayLength());
        Assert.True(root.GetProperty("rangesTruncated").GetBoolean());
        Assert.Equal(2, root.GetProperty("pages").GetArrayLength());

        using var fileJson = JsonDocument.Parse(File.ReadAllText(reportPath));
        Assert.Equal(3, fileJson.RootElement.GetProperty("differentByteCount").GetInt32());
    }

    [Fact]
    public async Task ProfileCommands_ListShowAndValidateSyntheticDefinition()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);

        var list = await workspace.RunAsync("profile", "list");
        var show = await workspace.RunAsync("profile", "show", TemporaryWorkspace.ProfileId);
        var validate = await workspace.RunAsync("profile", "validate", workspace.ProfilePath!);

        Assert.Equal(CliApplication.Success, list.ExitCode);
        Assert.Contains(TemporaryWorkspace.ProfileId, list.Output, StringComparison.Ordinal);
        Assert.Equal(CliApplication.Success, show.ExitCode);
        using var profileJson = JsonDocument.Parse(show.Output);
        Assert.Equal(TemporaryWorkspace.ProfileId, profileJson.RootElement.GetProperty("id").GetString());
        Assert.Equal(CliApplication.Success, validate.ExitCode);
        Assert.Contains("is valid", validate.Output, StringComparison.Ordinal);
    }

    [Fact]
    public async Task ProfileValidate_InvalidDefinitionReturnsVerificationFailure()
    {
        using var workspace = new TemporaryWorkspace();
        var invalid = workspace.PathOf("invalid.json");
        await File.WriteAllTextAsync(invalid, "{\"id\":\"incomplete\"}");

        var result = await workspace.RunAsync("profile", "validate", invalid);

        Assert.Equal(CliApplication.VerificationFailed, result.ExitCode);
        Assert.Contains("error:", result.Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task ProfileValidate_RejectsUnknownSchemaProperties()
    {
        using var workspace = new TemporaryWorkspace();
        var invalid = workspace.PathOf("unknown-property.json");
        var json = TemporaryWorkspace.SyntheticProfileJson.Replace(
            "\"schemaVersion\": \"1.0\",",
            "\"schemaVersion\": \"1.0\", \"arbitraryEval\": \"forbidden\",",
            StringComparison.Ordinal);
        await File.WriteAllTextAsync(invalid, json);

        var result = await workspace.RunAsync("profile", "validate", invalid);

        Assert.Equal(CliApplication.VerificationFailed, result.ExitCode);
        Assert.Contains("arbitraryEval", result.Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task ReadAndRoundtrip_DecodeSyntheticParametersWithoutChangingRom()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var rom = workspace.CreateRom("read.dat", bytes =>
        {
            bytes[0x10] = 42;
            bytes[0x11] = 10;
            bytes[0x20] = 0x34;
            bytes[0x21] = 0x12;
            bytes[0x22] = 0x12;
            bytes[0x23] = 0x34;
            bytes[0x30] = 7;
            bytes[0x31] = 8;
        });
        var original = File.ReadAllBytes(rom);

        var read = await workspace.RunAsync("read", rom, "--profile", TemporaryWorkspace.ProfileId);
        var roundtrip = await workspace.RunAsync("roundtrip", rom, "--profile", TemporaryWorkspace.ProfileId);

        Assert.Equal(CliApplication.Success, read.ExitCode);
        Assert.Contains("raw_u8\tvalue=42", read.Output, StringComparison.Ordinal);
        Assert.Contains("linear_u8\tvalue=250", read.Output, StringComparison.Ordinal);
        Assert.Contains("raw_u16_le\tvalue=4660", read.Output, StringComparison.Ordinal);
        Assert.Contains("raw_u16_be\tvalue=4660", read.Output, StringComparison.Ordinal);
        Assert.Contains("test_table[0]\tvalue=7 cells", read.Output, StringComparison.Ordinal);
        Assert.Contains("test_table[1]\tvalue=8 cells", read.Output, StringComparison.Ordinal);
        Assert.Equal(CliApplication.Success, roundtrip.ExitCode);
        Assert.Contains("byte-for-byte identical", roundtrip.Output, StringComparison.Ordinal);
        Assert.Equal(original, File.ReadAllBytes(rom));
    }

    [Fact]
    public async Task Patch_RequiresUnknownAndUnverifiedAcknowledgementsThenWritesReportAtomically()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var input = workspace.CreateRom("input.dat", bytes => bytes[0x10] = 10);
        var original = File.ReadAllBytes(input);

        var unknownOutput = workspace.PathOf("unknown-output.dat");
        var unknownReport = workspace.PathOf("unknown-report.json");
        var unknown = await workspace.RunAsync(
            "patch", input, "--profile", TemporaryWorkspace.ProfileId, "--set", "raw_u8=25",
            "--output", unknownOutput, "--report", unknownReport, "--allow-unverified");
        Assert.Equal(CliApplication.OperationError, unknown.ExitCode);
        Assert.Contains("--confirm-profile", unknown.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(unknownOutput));
        Assert.False(File.Exists(unknownReport));

        var output = workspace.PathOf("output.dat");
        var report = workspace.PathOf("patch.json");
        var patched = await workspace.RunAsync(
            "patch", input, "--profile", TemporaryWorkspace.ProfileId, "--set", "raw_u8=25",
            "--output", output, "--report", report, "--confirm-profile");
        Assert.Equal(CliApplication.OperationError, patched.ExitCode);
        Assert.Contains("unverified", patched.Error, StringComparison.OrdinalIgnoreCase);
        Assert.False(File.Exists(output));
        Assert.False(File.Exists(report));

        patched = await workspace.RunAsync(
            "patch", input, "--profile", TemporaryWorkspace.ProfileId, "--set", "raw_u8=25",
            "--output", output, "--report", report, "--confirm-profile", "--allow-unverified");

        Assert.Equal(CliApplication.Success, patched.ExitCode);
        Assert.Equal(original, File.ReadAllBytes(input));
        Assert.Equal(25, File.ReadAllBytes(output)[0x10]);
        Assert.True(File.Exists(report));
        var patchReport = PatchReport.Load(report);
        Assert.Equal(new[] { 0x10 }, patchReport.ChangedOffsets);
        Assert.Equal("0A", patchReport.Changes.Single().OldHex);
        Assert.Equal("19", patchReport.Changes.Single().NewHex);
        Assert.Equal(FlashReadinessStatus.PcInspectionOnly, patchReport.FlashReadiness);
        Assert.Contains("PC inspection only", patched.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Patch_RefusesInputAsOutputAndDoesNotCreateReport()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var input = workspace.CreateRom("same.dat");
        var report = workspace.PathOf("same.json");

        var result = await workspace.RunAsync(
            "patch", input, "--profile", TemporaryWorkspace.ProfileId, "--set", "raw_u8=2",
            "--output", input, "--report", report, "--confirm-profile", "--allow-unverified");

        Assert.Equal(CliApplication.OperationError, result.ExitCode);
        Assert.Contains("must be different", result.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(report));
    }

    [Fact]
    public async Task Verify_DetectsOutputMutationNotDeclaredByPatchReport()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var input = workspace.CreateRom("verify-input.dat");
        var output = workspace.PathOf("verify-output.dat");
        var report = workspace.PathOf("verify-report.json");
        var patch = await workspace.RunAsync(
            "patch", input, "--profile", TemporaryWorkspace.ProfileId, "--set", "raw_u8=3",
            "--output", output, "--report", report, "--confirm-profile", "--allow-unverified");
        Assert.Equal(CliApplication.Success, patch.ExitCode);

        var valid = await workspace.RunAsync(
            "verify", output, "--profile", TemporaryWorkspace.ProfileId, "--patch-report", report,
            "--baseline", input);
        Assert.Equal(CliApplication.Success, valid.ExitCode);
        Assert.Contains("Verification passed", valid.Output, StringComparison.Ordinal);

        var tampered = File.ReadAllBytes(output);
        tampered[0x200] = 0xA5;
        File.WriteAllBytes(output, tampered);
        var verify = await workspace.RunAsync(
            "verify", output, "--profile", TemporaryWorkspace.ProfileId, "--patch-report", report,
            "--baseline", input);

        Assert.Equal(CliApplication.VerificationFailed, verify.ExitCode);
        Assert.Contains("output-hash-mismatch", verify.Error, StringComparison.Ordinal);
        Assert.Contains("undeclared-change", verify.Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task SyntheticOracleWorkflow_ExportsCandidateButDiscoveryCasesDoNotConfirmEditors()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var baseline = workspace.CreateRom("oracle-base.dat");
        var noOp = workspace.CreateRom("oracle-noop.dat", bytes => bytes[0x40] = 0xA0);
        var cases = new[]
        {
            (Value: 505, Displayed: 510, Raw: (byte)51, Name: "case-nearest-low.dat"),
            (Value: 1006, Displayed: 1010, Raw: (byte)101, Name: "case-nearest-mid.dat"),
            (Value: 1503, Displayed: 1500, Raw: (byte)150, Name: "case-nearest-high.dat"),
        };
        foreach (var item in cases)
        {
            workspace.CreateRom(item.Name, bytes =>
            {
                bytes[0x40] = 0xA0;
                bytes[0x300] = item.Raw;
                bytes[^1] = (byte)(item.Raw + 1); // Excluded from discovery, but still unexplained without checksum evidence.
            });
        }

        var cromeManifest = workspace.PathOf("crome-manifest.json");
        var createCrome = await workspace.RunAsync(
            "oracle", "create-manifest", "--tool", "Crome", "--tool-version", "test-1.0",
            "--profile", TemporaryWorkspace.ProfileId, "--baseline", baseline, "--noop", noOp,
            "--output", cromeManifest, "--plugins-disabled", "--plugin", "none", "--notes", "synthetic");
        Assert.Equal(CliApplication.Success, createCrome.ExitCode);

        foreach (var item in cases)
        {
            var added = await workspace.RunAsync(
                "oracle", "add-case", "--manifest", cromeManifest, "--parameter", "rev_limit_test",
                "--value", item.Value.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "--displayed-value", item.Displayed.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "--rom", workspace.PathOf(item.Name), "--notes", "synthetic case");
            Assert.True(added.ExitCode == CliApplication.Success, added.Error);
            Assert.Contains("reopened display", added.Output, StringComparison.Ordinal);
        }

        Assert.All(OracleManifest.Load(cromeManifest).Cases, item => Assert.NotNull(item.DisplayedValue));

        var cromeAnalysis = workspace.PathOf("crome-analysis.json");
        var analyzed = await workspace.RunAsync(
            "oracle", "analyze", "--manifest", cromeManifest, "--output", cromeAnalysis);
        Assert.Equal(CliApplication.Success, analyzed.ExitCode);
        Assert.Contains("rev_limit_test: 3 case(s)", analyzed.Output, StringComparison.Ordinal);
        var analysis = OracleAnalysis.Load(cromeAnalysis);
        var candidates = analysis.Parameters.Single().Candidates;
        Assert.Contains(candidates, candidate =>
            candidate.Offset == 0x300 && candidate.EncodingType == ParameterEncodingType.LinearU8);
        Assert.DoesNotContain(candidates, candidate => candidate.Offset == 32767);
        Assert.All(candidates, candidate => Assert.Equal(ValidationLevel.OracleObserved, candidate.ValidationLevel));
        Assert.Contains("fitScore=", analyzed.Output, StringComparison.Ordinal);

        var chosen = candidates.Single(candidate => candidate.Offset == 0x300 && candidate.EncodingType == ParameterEncodingType.LinearU8);
        var selectedPath = workspace.PathOf("selected-analysis.json");
        var selected = await workspace.RunAsync("oracle", "analyze", "--manifest", cromeManifest,
            "--output", selectedPath, "--select-candidate", $"rev_limit_test={chosen.CandidateId}",
            "--selection-reason", "Synthetic review preference; not new evidence.");
        Assert.True(selected.ExitCode == CliApplication.Success, selected.Error);
        var selectedAnalysis = OracleAnalysis.Load(selectedPath);
        Assert.Equal(chosen.CandidateId, selectedAnalysis.Parameters.Single().SelectedCandidateId);
        Assert.Equal(candidates.Count, selectedAnalysis.Parameters.Single().Candidates.Count);
        var exportedById = await workspace.RunAsync("oracle", "export-candidate", "--analysis", selectedPath,
            "--candidate-id", chosen.CandidateId);
        Assert.True(exportedById.ExitCode == CliApplication.Success, exportedById.Error);
        using (var byId = JsonDocument.Parse(exportedById.Output))
        {
            Assert.Equal(chosen.CandidateId, byId.RootElement.GetProperty("candidateId").GetString());
            Assert.False(byId.RootElement.GetProperty("writable").GetBoolean());
        }

        var fragmentPath = workspace.PathOf("candidate.json");
        var exported = await workspace.RunAsync(
            "oracle", "export-candidate", "--analysis", cromeAnalysis, "--parameter", "rev_limit_test",
            "--offset", "0x300", "--encoding", "linear-u8", "--output", fragmentPath);
        Assert.Equal(CliApplication.Success, exported.ExitCode);
        using (var fragment = JsonDocument.Parse(File.ReadAllText(fragmentPath)))
        {
            Assert.False(fragment.RootElement.GetProperty("writable").GetBoolean());
            Assert.Equal("oracle-observed", fragment.RootElement.GetProperty("validationLevel").GetString());
        }

        var htsManifest = workspace.PathOf("hts-manifest.json");
        var createHts = await workspace.RunAsync(
            "oracle", "create-manifest", "--tool", "Honda Tuning Suite", "--tool-version", "test-2.0",
            "--profile", TemporaryWorkspace.ProfileId, "--baseline", baseline, "--noop", noOp,
            "--output", htsManifest, "--plugins-disabled");
        Assert.Equal(CliApplication.Success, createHts.ExitCode);
        foreach (var item in cases)
        {
            var added = await workspace.RunAsync(
                "oracle", "add-case", "--manifest", htsManifest, "--parameter", "rev_limit_test",
                "--value", item.Value.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "--displayed-value", item.Displayed.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "--rom", workspace.PathOf(item.Name));
            Assert.True(added.ExitCode == CliApplication.Success, added.Error);
        }

        var comparisonPath = workspace.PathOf("cross-editor.json");
        var compared = await workspace.RunAsync(
            "oracle", "compare", "--crome", cromeManifest, "--hts", htsManifest, "--output", comparisonPath);
        Assert.Equal(CliApplication.Success, compared.ExitCode);
        // Discovery-only fits, alternative widths, and unknown no-op transformations are not confirmation evidence.
        Assert.Contains("All requested parameters confirmed: False", compared.Output, StringComparison.Ordinal);
        using var comparison = JsonDocument.Parse(File.ReadAllText(comparisonPath));
        Assert.True(comparison.RootElement.GetProperty("sameBaseline").GetBoolean());
        Assert.False(comparison.RootElement.GetProperty("isCrossEditorConfirmed").GetBoolean());

        var wrongRole = await workspace.RunAsync(
            "oracle", "compare", "--crome", htsManifest, "--hts", htsManifest,
            "--output", workspace.PathOf("wrong-role.json"));
        Assert.Equal(CliApplication.OperationError, wrongRole.ExitCode);
        Assert.Contains("not crome", wrongRole.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task OraclePreflight_ReportsMissingPrivateFilesWithoutCreatingRoms()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var baseline = workspace.CreateRom("preflight-base.dat");
        var noOp = workspace.CreateRom("preflight-noop.dat");
        var manifest = OracleManifestService.Create("Crome", "synthetic-preflight-1", TemporaryWorkspace.ProfileId,
            baseline, noOp, pluginsDisabled: true);
        var manifestPath = workspace.PathOf("preflight-manifest.json");
        OracleManifestService.Save(manifest, manifestPath);
        File.Delete(baseline);
        File.Delete(noOp);
        var output = workspace.PathOf("preflight.json");

        var result = await workspace.RunAsync("oracle", "preflight", "--manifest", manifestPath, "--output", output);

        Assert.True(result.ExitCode == CliApplication.Success, result.Error);
        Assert.True(File.Exists(output));
        Assert.Contains("collection-incomplete", File.ReadAllText(output), StringComparison.Ordinal);
        Assert.False(File.Exists(baseline));
        Assert.False(File.Exists(noOp));
    }

    [Fact]
    public async Task OracleCollection_PreservesEditionNoOpChecksAndObservationRole()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var baseline = workspace.CreateRom("collection-base.dat");
        var noOp = workspace.CreateRom("collection-noop.dat");
        var independent = workspace.CreateRom("collection-independent-noop.dat");
        var resaved = workspace.CreateRom("collection-resaved-noop.dat");
        var casePath = workspace.CreateRom("collection-holdout.dat", bytes => bytes[0x300] = 40);
        var manifestPath = workspace.PathOf("collection.json");

        var created = await workspace.RunAsync("oracle", "create-manifest", "--tool", "Crome",
            "--tool-version", "synthetic-test-1", "--tool-edition", "synthetic-unit-test",
            "--profile", TemporaryWorkspace.ProfileId, "--baseline", baseline, "--noop", noOp,
            "--independent-noop", independent, "--resaved-noop", resaved, "--plugins-disabled", "--output", manifestPath,
            "--rounding-domain", "synthetic-rpm=0:255", "--domain-evidence", "Synthetic continuous raw-input domain; not Honda evidence.");
        Assert.True(created.ExitCode == CliApplication.Success, created.Error);
        var added = await workspace.RunAsync("oracle", "add-case", "--manifest", manifestPath,
            "--parameter", "synthetic-rpm", "--value", "401", "--displayed-value", "400",
            "--rom", casePath, "--role", "holdout", "--observation-id", "independent-check-1");
        Assert.True(added.ExitCode == CliApplication.Success, added.Error);

        var manifest = OracleManifest.Load(manifestPath);
        Assert.Equal("2.0", manifest.FormatVersion);
        Assert.Equal("synthetic-unit-test", manifest.ToolEdition);
        Assert.Equal(255, manifest.RoundingDomains["synthetic-rpm"].Maximum);
        Assert.Equal(independent, manifest.IndependentNoOp!.RomPath);
        Assert.Equal(resaved, manifest.ResavedNoOp!.RomPath);
        var observation = Assert.Single(manifest.Cases);
        Assert.Equal(OracleObservationRole.Holdout, observation.Role);
        Assert.Equal("independent-check-1", observation.ObservationId);
        Assert.Equal(401, observation.EngineeringValue);
        Assert.Equal(400, observation.DisplayedValue);

        var preflightPath = workspace.PathOf("collection-preflight.json");
        var preflight = await workspace.RunAsync("oracle", "preflight", "--manifest", manifestPath, "--output", preflightPath);
        Assert.True(preflight.ExitCode == CliApplication.Success, preflight.Error);
        Assert.True(File.Exists(preflightPath));
        Assert.Equal(RomImage.Load(casePath).Hash, observation.RomHash);
    }

    [Fact]
    public async Task OraclePreflight_RejectsOutputAtRecordedMissingRomPath()
    {
        using var workspace = new TemporaryWorkspace(withProfile: true);
        var baseline = workspace.CreateRom("protected-base.dat");
        var noOp = workspace.CreateRom("protected-noop.dat");
        var manifest = OracleManifestService.Create("Crome", "synthetic-1", TemporaryWorkspace.ProfileId,
            baseline, noOp, pluginsDisabled: true);
        var manifestPath = workspace.PathOf("protected-manifest.json");
        OracleManifestService.Save(manifest, manifestPath);
        File.Delete(baseline);

        var result = await workspace.RunAsync("oracle", "preflight", "--manifest", manifestPath, "--output", baseline);

        Assert.Equal(CliApplication.UsageError, result.ExitCode);
        Assert.False(File.Exists(baseline));
    }

    private sealed class TemporaryWorkspace : IDisposable
    {
        public const string ProfileId = "synthetic-cli-test";
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-cli-tests-{Guid.NewGuid():N}");

        public TemporaryWorkspace(bool withProfile = false)
        {
            Directory.CreateDirectory(_root);
            DefinitionsPath = Path.Combine(_root, "definitions");
            if (withProfile)
            {
                Directory.CreateDirectory(DefinitionsPath);
                ProfilePath = Path.Combine(DefinitionsPath, "synthetic.json");
                File.WriteAllText(ProfilePath, SyntheticProfileJson);
            }
        }

        public string DefinitionsPath { get; }

        public string? ProfilePath { get; }

        public string PathOf(string name) => Path.Combine(_root, name);

        public string CreateRom(string name, Action<byte[]>? mutate = null)
        {
            var bytes = new byte[32768];
            mutate?.Invoke(bytes);
            var path = PathOf(name);
            File.WriteAllBytes(path, bytes);
            return path;
        }

        public async Task<CliResult> RunAsync(params string[] args)
        {
            using var output = new StringWriter();
            using var error = new StringWriter();
            var application = new CliApplication(output, error, _root, DefinitionsPath);
            var exitCode = await application.RunAsync(args);
            return new CliResult(exitCode, output.ToString(), error.ToString());
        }

        public void Dispose()
        {
            if (Directory.Exists(_root))
            {
                Directory.Delete(_root, recursive: true);
            }
        }

        internal const string SyntheticProfileJson = """
            {
              "schemaVersion": "1.0",
              "id": "synthetic-cli-test",
              "displayName": "Synthetic CLI Test ROM",
              "description": "Generated test-only profile with no Honda data.",
              "revisionScope": "synthetic-test-only",
              "status": "experimental",
              "format": {
                "kind": "raw-binary",
                "exactSize": 32768,
                "headerBytes": 0,
                "paddingAllowed": false,
                "truncationAllowed": false
              },
              "identity": {
                "requiresExplicitConfirmation": true,
                "hashes": [],
                "signatures": []
              },
              "parameters": [
                {
                  "id": "raw_u8",
                  "displayName": "Raw U8",
                  "description": "Synthetic byte.",
                  "offset": 16,
                  "width": 1,
                  "endianness": "not-applicable",
                  "encoding": { "type": "raw-u8" },
                  "units": "raw",
                  "rawRange": { "minimum": 0, "maximum": 255 },
                  "engineeringRange": { "minimum": 0, "maximum": 255 },
                  "roundingPolicy": "nearest",
                  "writable": true,
                  "validationLevel": "public-documentation",
                  "revisionScope": "synthetic-test-only",
                  "sources": ["synthetic-evidence"],
                  "notes": "Test only.",
                  "status": "experimental"
                },
                {
                  "id": "linear_u8",
                  "displayName": "Linear U8",
                  "description": "Synthetic linear byte.",
                  "offset": 17,
                  "width": 1,
                  "endianness": "not-applicable",
                  "encoding": { "type": "linear-u8", "scale": 25, "offset": 0 },
                  "units": "rpm",
                  "rawRange": { "minimum": 0, "maximum": 255 },
                  "engineeringRange": { "minimum": 0, "maximum": 6375 },
                  "roundingPolicy": "nearest",
                  "writable": false,
                  "validationLevel": "public-documentation",
                  "revisionScope": "synthetic-test-only",
                  "sources": ["synthetic-evidence"],
                  "notes": "Test only.",
                  "status": "candidate"
                },
                {
                  "id": "raw_u16_le",
                  "displayName": "Raw U16 LE",
                  "description": "Synthetic little-endian word.",
                  "offset": 32,
                  "width": 2,
                  "endianness": "little",
                  "encoding": { "type": "raw-u16-little-endian" },
                  "units": "raw",
                  "rawRange": { "minimum": 0, "maximum": 65535 },
                  "engineeringRange": { "minimum": 0, "maximum": 65535 },
                  "roundingPolicy": "exact",
                  "writable": false,
                  "validationLevel": "cross-editor-confirmed",
                  "revisionScope": "synthetic-test-only",
                  "sources": ["synthetic-evidence"],
                  "notes": "Test only.",
                  "status": "verified"
                },
                {
                  "id": "raw_u16_be",
                  "displayName": "Raw U16 BE",
                  "description": "Synthetic big-endian word.",
                  "offset": 34,
                  "width": 2,
                  "endianness": "big",
                  "encoding": { "type": "raw-u16-big-endian" },
                  "units": "raw",
                  "rawRange": { "minimum": 0, "maximum": 65535 },
                  "engineeringRange": { "minimum": 0, "maximum": 65535 },
                  "roundingPolicy": "exact",
                  "writable": false,
                  "validationLevel": "cross-editor-confirmed",
                  "revisionScope": "synthetic-test-only",
                  "sources": ["synthetic-evidence"],
                  "notes": "Test only.",
                  "status": "verified"
                }
              ],
              "tables": [
                {
                  "id": "test_table",
                  "displayName": "Synthetic Table",
                  "description": "Two synthetic cells.",
                  "offset": 48,
                  "width": 2,
                  "rows": 1,
                  "columns": 2,
                  "cellWidth": 1,
                  "endianness": "not-applicable",
                  "encoding": { "type": "raw-u8" },
                  "units": "cells",
                  "rawRange": { "minimum": 0, "maximum": 255 },
                  "engineeringRange": { "minimum": 0, "maximum": 255 },
                  "roundingPolicy": "exact",
                  "writable": false,
                  "validationLevel": "cross-editor-confirmed",
                  "revisionScope": "synthetic-test-only",
                  "sources": ["synthetic-evidence"],
                  "notes": "Test only.",
                  "status": "verified"
                }
              ],
              "sources": [
                {
                  "id": "synthetic-evidence",
                  "title": "Synthetic test evidence",
                  "url": "https://example.invalid/hondaecu-synthetic-test",
                  "accessedOn": "2026-09-04",
                  "scope": "synthetic-test-only",
                  "notes": "Contains no OEM data."
                }
              ],
              "checksum": {
                "algorithmId": "unknown",
                "status": "unknown",
                "offset": 32767,
                "length": 1,
                "evidenceLevel": "public-documentation",
                "excludedRegions": [],
                "notes": "No checksum algorithm exists for this synthetic fixture."
              }
            }
            """;
    }

    private sealed record CliResult(int ExitCode, string Output, string Error);
}
