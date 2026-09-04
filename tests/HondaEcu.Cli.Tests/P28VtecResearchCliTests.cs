using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Cli.Tests;

public sealed class P28VtecResearchCliTests
{
    [Fact]
    public async Task MatchedPrivateBindingAndAcknowledgementProduceDeterministicSemanticReport()
    {
        using var workspace = new ResearchWorkspace();
        var input = workspace.CreateRom("candidate.dat", bytes =>
        {
            for (var index = 0; index < P28ThresholdLogic.BlockLength; index++)
            {
                bytes[P28ThresholdLogic.BlockOffset + index] = (byte)(0x20 + index);
            }
        });
        var original = File.ReadAllBytes(input);
        var binding = workspace.CreateBinding("binding.json", input);
        var firstOutput = workspace.PathOf("first-report.json");
        var secondOutput = workspace.PathOf("second-report.json");

        var first = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", binding,
            "--confirm-profile",
            "--output", firstOutput);
        var second = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", binding,
            "--confirm-profile",
            "--output", secondOutput);

        Assert.Equal(CliApplication.Success, first.ExitCode);
        Assert.Equal(CliApplication.Success, second.ExitCode);
        Assert.Equal(original, File.ReadAllBytes(input));
        Assert.Equal(File.ReadAllText(firstOutput), File.ReadAllText(secondOutput));
        Assert.DoesNotContain(RomImage.Load(input).Hash.Sha256, first.Output, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(input, first.Output, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(firstOutput, first.Output, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("analyst-declared", first.Error, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("not flash-ready", first.Error, StringComparison.OrdinalIgnoreCase);

        using var json = JsonDocument.Parse(File.ReadAllText(firstOutput));
        var root = json.RootElement;
        Assert.Equal("p28-vtec-threshold-inspection", root.GetProperty("reportKind").GetString());
        Assert.Equal(P28CompactModel.ModelId, root.GetProperty("modelId").GetString());
        Assert.True(root.GetProperty("profileAcknowledged").GetBoolean());
        Assert.False(root.GetProperty("publicIdentity").GetProperty("isIdentified").GetBoolean());
        Assert.Equal("none", root.GetProperty("publicIdentity").GetProperty("method").GetString());
        Assert.Equal("matched", root.GetProperty("baselineBinding").GetProperty("status").GetString());
        Assert.True(root.GetProperty("interpretationApplied").GetBoolean());
        Assert.Equal("exact-private-baseline-partial-raw-to-compact-research", root.GetProperty("scope").GetString());
        Assert.Contains(
            root.GetProperty("warnings").EnumerateArray(),
            value => value.GetString()!.Contains("partial", StringComparison.OrdinalIgnoreCase));
        Assert.False(root.GetProperty("physicalRpmAvailable").GetBoolean());
        Assert.Equal(JsonValueKind.Null, root.GetProperty("physicalRpmIntervals").ValueKind);
        Assert.Equal("pc-inspection-only", root.GetProperty("flashReadiness").GetString());
        Assert.Equal("not-flash-ready", root.GetProperty("flashSafety").GetString());

        var rawBytes = root.GetProperty("rawWindow").GetProperty("bytes");
        Assert.Equal(P28ThresholdLogic.BlockLength, rawBytes.GetArrayLength());
        Assert.Equal(P28ThresholdLogic.BlockOffset, rawBytes[0].GetProperty("offset").GetInt32());
        Assert.Equal(0x20, rawBytes[0].GetProperty("value").GetByte());

        var contexts = root.GetProperty("contexts");
        Assert.Equal(2, contexts.GetArrayLength());
        Assert.Equal(0, contexts[0].GetProperty("context").GetInt32());
        Assert.True(contexts[0].GetProperty("selectorData011EBit3").GetBoolean());
        Assert.Equal(P28ThresholdLogic.BlockOffset, contexts[0].GetProperty("baseOffset").GetInt32());
        Assert.Equal(1, contexts[1].GetProperty("context").GetInt32());
        Assert.False(contexts[1].GetProperty("selectorData011EBit3").GetBoolean());
        Assert.Equal(P28ThresholdLogic.BlockOffset + 4, contexts[1].GetProperty("baseOffset").GetInt32());
        Assert.Equal(4, contexts[0].GetProperty("slots").GetArrayLength());
        Assert.True(contexts[0].GetProperty("slots")[0].GetProperty("priorState").GetBoolean());
        Assert.Equal(P28ThresholdLogic.BlockOffset, contexts[0].GetProperty("slots")[0].GetProperty("offset").GetInt32());
        Assert.False(contexts[0].GetProperty("slots")[1].GetProperty("priorState").GetBoolean());
        Assert.Equal(P28ThresholdLogic.BlockOffset + 1, contexts[0].GetProperty("slots")[1].GetProperty("offset").GetInt32());

        var stateContract = root.GetProperty("thresholdStateContract");
        Assert.False(stateContract.GetProperty("equalityResult").GetBoolean());
        Assert.True(stateContract.GetProperty("requiredData011EBit4").GetBoolean());
        Assert.Equal("0x0100", stateContract.GetProperty("requiredDataPage").GetString());
        Assert.Equal(0, stateContract.GetProperty("requiredDd").GetInt32());

        var domainSets = root.GetProperty("compactDomains");
        Assert.Equal(2, domainSets.GetArrayLength());
        Assert.False(domainSets[0].GetProperty("data0217Bit4").GetBoolean());
        Assert.True(domainSets[1].GetProperty("data0217Bit4").GetBoolean());
        Assert.Equal(256, domainSets[0].GetProperty("domains").GetArrayLength());
        Assert.Equal(256, domainSets[1].GetProperty("domains").GetArrayLength());
        var unresolvedNormalCode = domainSets[0].GetProperty("domains")[128];
        Assert.Equal(JsonValueKind.Null, unresolvedNormalCode.GetProperty("reachable").ValueKind);
        Assert.Equal(0, unresolvedNormalCode.GetProperty("exactInputs").GetArrayLength());
        Assert.True(unresolvedNormalCode.GetProperty("hypothesisReachable").GetBoolean());
        var unresolvedInputs = unresolvedNormalCode.GetProperty("unresolvedInputs");
        Assert.Single(unresolvedInputs.EnumerateArray());
        Assert.Equal(234, unresolvedInputs[0].GetProperty("startInclusive").GetInt32());
        Assert.Equal(3749, unresolvedInputs[0].GetProperty("endInclusive").GetInt32());
        Assert.Equal("unresolved", unresolvedInputs[0].GetProperty("branch").GetString());
        Assert.DoesNotContain(
            Directory.EnumerateFiles(workspace.RootPath),
            path => path.EndsWith(".tmp", StringComparison.Ordinal));
    }

    [Fact]
    public async Task MissingAcknowledgementOrExactBindingNeverEnablesRevisionSpecificInterpretation()
    {
        using var workspace = new ResearchWorkspace();
        var input = workspace.CreateRom("unknown.dat", bytes => bytes[P28ThresholdLogic.BlockOffset] = 0x5A);
        var original = File.ReadAllBytes(input);
        var matchingBinding = workspace.CreateBinding("matching.json", input);
        var other = workspace.CreateRom("other.dat", bytes => bytes[0] = 0xA5);
        var mismatchingBinding = workspace.CreateBinding("mismatching.json", other);

        var absentOutput = workspace.PathOf("absent.json");
        var absent = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--output", absentOutput);
        Assert.Equal(CliApplication.Success, absent.ExitCode);
        AssertRawOnly(absentOutput, "not-provided", acknowledged: true);

        var unacknowledgedOutput = workspace.PathOf("unacknowledged.json");
        var unacknowledged = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", matchingBinding,
            "--output", unacknowledgedOutput);
        Assert.Equal(CliApplication.Success, unacknowledged.ExitCode);
        AssertRawOnly(unacknowledgedOutput, "matched", acknowledged: false);

        var mismatchOutput = workspace.PathOf("mismatch.json");
        var mismatch = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", mismatchingBinding,
            "--confirm-profile",
            "--output", mismatchOutput);
        Assert.Equal(CliApplication.VerificationFailed, mismatch.ExitCode);
        AssertRawOnly(mismatchOutput, "mismatched", acknowledged: true);
        using (var mismatchJson = JsonDocument.Parse(File.ReadAllText(mismatchOutput)))
        {
            Assert.Contains(
                mismatchJson.RootElement.GetProperty("baselineBinding").GetProperty("mismatchReasons").EnumerateArray(),
                value => value.GetString() == "rom-hash-mismatch");
        }

        Assert.Equal(original, File.ReadAllBytes(input));
        Assert.DoesNotContain(RomImage.Load(input).Hash.Sha256, mismatch.Output, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task WrongSizeAndMalformedBindingFailWithoutCreatingReport()
    {
        using var workspace = new ResearchWorkspace();
        var shortInput = workspace.CreateRom("short.dat", length: P28ExactBaselineBinding.RequiredSize - 1);
        var shortOutput = workspace.PathOf("short-report.json");

        var shortResult = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", shortInput,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--confirm-profile",
            "--output", shortOutput);

        Assert.Equal(CliApplication.OperationError, shortResult.ExitCode);
        Assert.Contains("exactly 32768", shortResult.Error, StringComparison.Ordinal);
        Assert.False(File.Exists(shortOutput));

        var input = workspace.CreateRom("valid-size.dat");
        var validBinding = File.ReadAllText(workspace.CreateBinding("valid-binding.json", input));
        var malformedPath = workspace.PathOf("malformed-binding.json");
        File.WriteAllText(
            malformedPath,
            validBinding.Replace(
                "\"profileDigest\"",
                "\"unexpected\": true, \"profileDigest\"",
                StringComparison.Ordinal));
        var malformedOutput = workspace.PathOf("malformed-report.json");

        var malformedResult = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", malformedPath,
            "--confirm-profile",
            "--output", malformedOutput);

        Assert.Equal(CliApplication.OperationError, malformedResult.ExitCode);
        Assert.Contains("unknown property", malformedResult.Error, StringComparison.OrdinalIgnoreCase);
        Assert.False(File.Exists(malformedOutput));
    }

    [Fact]
    public async Task ChangedProfileDigestCannotUnlockInterpretationForTheSameRom()
    {
        using var workspace = new ResearchWorkspace();
        var input = workspace.CreateRom("profile-digest-input.dat", bytes => bytes[0] = 0xA5);
        var profile = RomProfile.Load(workspace.ProfilePath);
        var digest = P28VtecInspector.ComputeProfileDigest(profile);
        var changedDigest = (digest[0] == '0' ? "1" : "0") + digest[1..];
        var bindingPath = workspace.PathOf("changed-profile-digest-binding.json");
        var binding = new P28ExactBaselineBinding(
            P28ExactBaselineBinding.CurrentFormatVersion,
            P28CompactModel.ModelId,
            P28ExactBaselineBinding.RequiredProfileId,
            P28ExactBaselineBinding.RequiredSize,
            RomImage.Load(input).Hash,
            changedDigest);
        File.WriteAllText(bindingPath, binding.ToJson());
        var originalInput = File.ReadAllBytes(input);
        var originalBinding = File.ReadAllBytes(bindingPath);
        var output = workspace.PathOf("changed-profile-digest-report.json");

        var result = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", bindingPath,
            "--confirm-profile",
            "--output", output);

        Assert.Equal(CliApplication.VerificationFailed, result.ExitCode);
        AssertRawOnly(output, "mismatched", acknowledged: true);
        using (var report = JsonDocument.Parse(File.ReadAllText(output)))
        {
            var assessment = report.RootElement.GetProperty("baselineBinding");
            Assert.True(assessment.GetProperty("romHashMatches").GetBoolean());
            Assert.False(assessment.GetProperty("profileDigestMatches").GetBoolean());
            Assert.Contains(
                assessment.GetProperty("mismatchReasons").EnumerateArray(),
                value => value.GetString() == "profile-digest-mismatch");
        }

        Assert.Equal(originalInput, File.ReadAllBytes(input));
        Assert.Equal(originalBinding, File.ReadAllBytes(bindingPath));
    }

    [Fact]
    public void PrivateBindingParserRejectsDuplicateAndWrongSecurityScope()
    {
        using var workspace = new ResearchWorkspace();
        var input = workspace.CreateRom("binding-input.dat");
        var valid = File.ReadAllText(workspace.CreateBinding("binding.json", input));
        var duplicate = valid.Replace(
            "\"modelId\": \"p28-compact-v1\"",
            "\"modelId\": \"p28-compact-v1\", \"modelId\": \"p28-compact-v1\"",
            StringComparison.Ordinal);
        var wrongModel = valid.Replace(P28CompactModel.ModelId, "different-model", StringComparison.Ordinal);
        var wrongProfile = valid.Replace(
            "\"profileId\": \"p28-304\"",
            "\"profileId\": \"different-profile\"",
            StringComparison.Ordinal);
        var wrongSize = valid.Replace(
            "\"expectedSize\": 32768",
            "\"expectedSize\": 65536",
            StringComparison.Ordinal);

        Assert.Throws<InvalidDataException>(() => P28ExactBaselineBinding.Parse(duplicate));
        Assert.Throws<InvalidDataException>(() => P28ExactBaselineBinding.Parse(wrongModel));
        Assert.Throws<InvalidDataException>(() => P28ExactBaselineBinding.Parse(wrongProfile));
        Assert.Throws<InvalidDataException>(() => P28ExactBaselineBinding.Parse(wrongSize));
    }

    [Fact]
    public async Task ReportCannotOverwriteRomOrPrivateBinding()
    {
        using var workspace = new ResearchWorkspace();
        var input = workspace.CreateRom("protected-input.dat", bytes => bytes[0] = 0xA5);
        var binding = workspace.CreateBinding("protected-binding.json", input);
        var originalInput = File.ReadAllBytes(input);
        var originalBinding = File.ReadAllBytes(binding);

        var overInput = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", binding,
            "--confirm-profile",
            "--output", input);
        var overBinding = await workspace.RunAsync(
            "research", "p28-vtec", "inspect", input,
            "--profile", P28ExactBaselineBinding.RequiredProfileId,
            "--baseline-binding", binding,
            "--confirm-profile",
            "--output", binding);

        Assert.Equal(CliApplication.OperationError, overInput.ExitCode);
        Assert.Equal(CliApplication.OperationError, overBinding.ExitCode);
        Assert.Equal(originalInput, File.ReadAllBytes(input));
        Assert.Equal(originalBinding, File.ReadAllBytes(binding));
    }

    private static void AssertRawOnly(string reportPath, string bindingStatus, bool acknowledged)
    {
        using var json = JsonDocument.Parse(File.ReadAllText(reportPath));
        var root = json.RootElement;
        Assert.Equal("raw-window-only", root.GetProperty("scope").GetString());
        Assert.False(root.GetProperty("interpretationApplied").GetBoolean());
        Assert.Equal(acknowledged, root.GetProperty("profileAcknowledged").GetBoolean());
        Assert.Equal(bindingStatus, root.GetProperty("baselineBinding").GetProperty("status").GetString());
        Assert.False(root.GetProperty("publicIdentity").GetProperty("isIdentified").GetBoolean());
        Assert.Equal(P28ThresholdLogic.BlockLength, root.GetProperty("rawWindow").GetProperty("bytes").GetArrayLength());
        Assert.Equal(0, root.GetProperty("contexts").GetArrayLength());
        Assert.Equal(JsonValueKind.Null, root.GetProperty("thresholdStateContract").ValueKind);
        Assert.Equal(0, root.GetProperty("compactDomains").GetArrayLength());
        Assert.False(root.GetProperty("physicalRpmAvailable").GetBoolean());
        Assert.Equal(JsonValueKind.Null, root.GetProperty("physicalRpmIntervals").ValueKind);
        Assert.Equal("not-flash-ready", root.GetProperty("flashSafety").GetString());
    }

    private sealed class ResearchWorkspace : IDisposable
    {
        private readonly string _root = Path.Combine(Path.GetTempPath(), $"hondaecu-p28-cli-tests-{Guid.NewGuid():N}");

        public ResearchWorkspace()
        {
            Directory.CreateDirectory(_root);
            DefinitionsPath = Path.Combine(_root, "definitions", "p28");
            Directory.CreateDirectory(DefinitionsPath);
            ProfilePath = Path.Combine(DefinitionsPath, "p28-304.experimental.json");
            File.WriteAllText(ProfilePath, SyntheticProfileJson);
        }

        public string RootPath => _root;

        public string DefinitionsPath { get; }

        public string ProfilePath { get; }

        public string PathOf(string name) => Path.Combine(_root, name);

        public string CreateRom(string name, Action<byte[]>? mutate = null, int length = P28ExactBaselineBinding.RequiredSize)
        {
            var bytes = new byte[length];
            mutate?.Invoke(bytes);
            var path = PathOf(name);
            File.WriteAllBytes(path, bytes);
            return path;
        }

        public string CreateBinding(string name, string romPath)
        {
            var profile = RomProfile.Load(ProfilePath);
            var binding = new P28ExactBaselineBinding(
                P28ExactBaselineBinding.CurrentFormatVersion,
                P28CompactModel.ModelId,
                P28ExactBaselineBinding.RequiredProfileId,
                P28ExactBaselineBinding.RequiredSize,
                RomImage.Load(romPath).Hash,
                P28VtecInspector.ComputeProfileDigest(profile));
            var path = PathOf(name);
            File.WriteAllText(path, binding.ToJson());
            return path;
        }

        public async Task<CliResult> RunAsync(params string[] args)
        {
            using var output = new StringWriter();
            using var error = new StringWriter();
            var application = new CliApplication(output, error, _root, Path.Combine(_root, "definitions"));
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

        private const string SyntheticProfileJson = """
            {
              "schemaVersion": "1.0",
              "id": "p28-304",
              "displayName": "Synthetic P28 research-scope test image",
              "description": "Generated test-only profile containing no OEM data.",
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
              "parameters": [],
              "tables": [],
              "sources": [],
              "checksum": {
                "algorithmId": "unknown",
                "status": "unknown",
                "offset": 0,
                "length": 0,
                "evidenceLevel": "public-documentation",
                "excludedRegions": [],
                "notes": "No checksum algorithm is asserted by this synthetic fixture."
              }
            }
            """;
    }

    private sealed record CliResult(int ExitCode, string Output, string Error);
}
