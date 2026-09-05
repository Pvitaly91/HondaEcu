using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28ChecksumPreservingLocationTests
{
    [Fact]
    public void PinnedKeyAuthenticatesInventedFixtureButDoesNotGiveItNativeAlgorithmEvidence()
    {
        // Signed offline by the reviewer. Every hash below belongs to invented
        // data/profile/binding, never an OEM input or a private research artifact.
        var location = P28ChecksumPreservingEditor.ParseLocation(SignedInventedFixture);
        Assert.Equal("invented-signature-only-v1", location.DefinitionId);
        Assert.Equal(0x7FFF, location.Offset);
        Assert.Equal((byte)0, location.OriginalByte);
        var baseline = RomImage.FromBytes(new byte[32768]);
        Assert.Equal("c35020473aed1b4642cd726cad727b63fff2824ad68cedd7ffb73c7cbd890479", baseline.Hash.Sha256);
        var profile = new RomProfile("p28-304", "Independent synthetic profile", "No native code", 32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, baseline.Size, baseline.Hash,
            P28VtecInspector.ComputeProfileDigest(profile));
        var availability = P28ChecksumPreservingEditor.GetAvailability(baseline, profile, binding, true, location);
        Assert.False(availability.IsAvailable);
        Assert.Equal("rejected-checksum-contract", availability.Status);
        var tampered = JsonNode.Parse(SignedInventedFixture)!.AsObject();
        tampered["payload"]!["originalByte"] = 1;
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ParseLocation(tampered.ToJsonString()));
        tampered = JsonNode.Parse(SignedInventedFixture)!.AsObject();
        tampered["payload"]!["evidenceScope"] = "Replaced conclusion with an invented permission";
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ParseLocation(tampered.ToJsonString()));
    }

    [Fact]
    public void ACallerCreatedEligibilityClaimAndFreshSigningKeyCannotMintAuthority()
    {
        var payload = Payload();
        using var unrelatedIssuer = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var signature = unrelatedIssuer.SignData(Encoding.UTF8.GetBytes(payload.ToJson(false)), HashAlgorithmName.SHA256,
            DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
        var document = new P28CompensationLocationDocument(payload, Convert.ToBase64String(signature));
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ParseLocation(document.ToJson()));
        Assert.Empty(typeof(VerifiedCompensationLocation).GetConstructors());
        Assert.Empty(typeof(P28VerifiedChecksumComposition).GetConstructors());
        Assert.Empty(typeof(P28VerifiedChecksumExport).GetConstructors());
    }

    [Fact]
    public void LocationParserRejectsUnknownDuplicateOversizeAndNoneligibleDefinitions()
    {
        var document = new P28CompensationLocationDocument(Payload(), Convert.ToBase64String(new byte[64]));
        Action<JsonObject>[] edits =
        [
            root => root["extra"] = false,
            root => root["payload"]!["offset"] = 0x7FFE,
            root => root["payload"]!["offset"] = 0x7000,
            root => root["payload"]!["eligibleForResearchExport"] = false,
            root => root["payload"]!["formatVersion"] = "2.0",
            root => root["payload"]!["candidateContractId"] = "candidateUnused",
            root => root["payload"]!["bindingDigest"] = "not-a-digest",
            root => root["payload"]!["limitations"] = new JsonArray(),
            root => root["payload"]!["verifiedConsumers"] = new JsonArray(),
            root => root["payload"]!["evidenceScope"] = null,
            root => root["signatureBase64"] = Convert.ToBase64String(new byte[63]),
            root => root["signatureBase64"] = "not_base64",
        ];
        foreach (var edit in edits)
        {
            var root = JsonNode.Parse(document.ToJson())!.AsObject(); edit(root);
            Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ParseLocation(root.ToJsonString()));
        }
        var duplicate = document.ToJson().Replace("\"eligibleForResearchExport\": true", "\"eligibleForResearchExport\": true, \"eligibleForResearchExport\": true", StringComparison.Ordinal);
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ParseLocation(duplicate));
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ParseLocation(document.ToJson() + new string(' ', 65536)));
        var directory = Path.Combine(Path.GetTempPath(), $"hondaecu-location-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var path = Path.Combine(directory, "oversized.json");
            File.WriteAllText(path, new string(' ', 65537));
            Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.LoadLocation(path));
        }
        finally { Directory.Delete(directory, true); }
    }

    [Fact]
    public async Task CancellationBeforeWorkCannotBecomeAnExecutionOrPublicationCapability()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(P28ThresholdLogic.GetSlots()[0].Id, 41);
        // Deliberately unadmitted internal test object, never a public authorization path.
        var unadmitted = new P28VerifiedChecksumComposition(baseline, profile, binding, preview.Image, preview.Plan, preview.Report, null!);
        using var canceled = new CancellationTokenSource(); canceled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28ChecksumPreservingExecution.ValidateForExportAsync(unadmitted,
            "missing-runner", cancellationToken: canceled.Token));
        await Assert.ThrowsAsync<InvalidDataException>(() => P28ChecksumPreservingExecution.ValidateForExportAsync(unadmitted, "missing-runner"));
        Assert.False(preview.Report.ExecutionStatus == NativeChecksumExecutionStatus.Match);
        Assert.Equal(ChecksumStatus.Unknown, preview.Report.NativeChecksumStatus);
    }

    private static P28CompensationLocationPayload Payload()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        return new(VerifiedCompensationLocation.DocumentVersion, VerifiedCompensationLocation.DocumentPurpose,
            VerifiedCompensationLocation.CandidateContract, "invented-signature-test-only", baseline.Hash,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), 0x7FFF, 0,
            "invented-evidence-only", "Authentication test only; no native Honda evidence or real export permission.",
            ["Fixed invented data consumer"], ["Not hardware evidence"], true,
            FlashReadinessStatus.PcInspectionOnly, FlashSafetyStatus.NotFlashReady);
    }

    private const string SignedInventedFixture = """
        {
          "payload": {
            "formatVersion": "1.0",
            "purpose": "reviewed-pc-only-compensation-location",
            "candidateContractId": "p28-research-tail-byte-7fff-v1",
            "definitionId": "invented-signature-only-v1",
            "baselineHash": {
              "sha256": "c35020473aed1b4642cd726cad727b63fff2824ad68cedd7ffb73c7cbd890479",
              "crc32": "011FFCA6"
            },
            "profileDigest": "cc43fb6c8f4311a0cd585ec1e7cba00eadf6ffac14b4dfd5cce4dae30d5d260d",
            "bindingDigest": "db8eea247f77cdb33e57d685bcb81c108e8599556791560a754fc5189399d476",
            "offset": 32767,
            "originalByte": 0,
            "evidenceIdentity": "synthetic-signature-fixture-only",
            "evidenceScope": "Invented all-zero signature fixture only; not native authority, CodeGuard must reject this image.",
            "verifiedConsumers": [
              "Invented fixture, no native code or data-consumer claim"
            ],
            "limitations": [
              "Not globally unused ROM or FactoryChecksumStorage.",
              "No full DD-flow proof, full ECU boot, hardware memory-map or vehicle behavior validation.",
              "Excludes arbitrary PC/register/RAM/stack corruption, hardware faults and unmodeled external code/memory modes.",
              "Static review and signature are distinct: signature authenticates review provenance, not its truth. Dynamic slice evidence is supplementary and separately reported.",
              "M1d/M1e ADD assumptions remain independent. PcInspectionOnly / NotFlashReady."
            ],
            "eligibleForResearchExport": true,
            "flashReadiness": "pc-inspection-only",
            "flashSafety": "not-flash-ready"
          },
          "signatureBase64": "N2qwsHrVe4zGBzZAMZyGj3UPqJPBZLWSJMwtaBt5w\u002BuLzhlTE24\u002Bq8m0KNayoB8YYQ6Ftxzi8Wu5gGMf8OkTNg=="
        }
        """;
}
