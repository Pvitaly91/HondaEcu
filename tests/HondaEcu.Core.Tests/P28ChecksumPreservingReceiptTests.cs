using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28ChecksumPreservingReceiptTests
{
    [Fact]
    public void HistoricalReceiptShapeCannotAcceptForgedAccountingOrActAsPublicationAuthority()
    {
        // Fabricated accounting DTO only. This is NOT an execution test, admitted
        // native lineage, or a claim that the synthetic program is a Honda ROM.
        var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(P28ThresholdLogic.GetSlots()[0].Id, 41);
        var composition = preview.Report with { SyntheticOnly = false, CompensationDefinitionId = "invented-receipt-accounting-only" };
        var observations = new[] { "baseline", "derived" }.SelectMany(kind => new[] { 0, 85, 170 }.Select(pattern =>
            new P28ChecksumExportObservation(kind, kind == "baseline" ? composition.BaselineHash : composition.OutputHash,
                pattern, NativeChecksumExecutionStatus.Match, true, 0, "ResidueZero", 512, 104963, 32768, true, true, []))).ToArray();
        var receipt = new P28ChecksumPreservingExportReport("1.0", P28ChecksumPreservingExportReport.ReportPurpose,
            composition, "0.3.0", P28ByteExecutionValidator.UpstreamCommit, Fixes, observations,
            P28ChecksumPreservingExportReport.HistoricalScope);
        Assert.Equal(receipt.ToJson(), P28ChecksumPreservingExportReport.Parse(receipt.ToJson()).ToJson());
        Assert.Empty(typeof(P28VerifiedChecksumExport).GetConstructors());
        Action<JsonObject>[] changes =
        [
            root => root["runnerVersion"] = "0.2.0",
            root => root["upstreamCommit"] = new string('a', 40),
            root => root["localSemanticFixes"] = new JsonArray(),
            root => root["observations"]![0]!["scratchPattern"] = 1,
            root => root["observations"]![0]!["steps"] = 1,
            root => root["observations"]![0]!["invocations"] = 511,
            root => root["observations"]![0]!["programReadCount"] = 32767,
            root => root["observations"]![0]!["computedResult"] = 1,
            root => root["observations"]![0]!["decision"] = "NonzeroResidueBypassed",
            root => root["observations"]![0]!["usedAssumptions"] = new JsonArray("oki.add-er1-a"),
            root => root["observations"]![0]!["coverageMatches"] = false,
            root => root["observations"]![0]!["extra"] = true,
            root => root["compositionReport"]!["planDigest"] = "not-a-digest",
        ];
        foreach (var change in changes)
        {
            var node = JsonNode.Parse(receipt.ToJson())!.AsObject(); change(node);
            Assert.ThrowsAny<Exception>(() => P28ChecksumPreservingExportReport.Parse(node.ToJsonString()));
        }
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualUnrelatedToyReadsBothChangedDataBytesAndDistinguishesAFromBAndC()
    {
        // Newly authored seven-byte toy folds one LC word into r0. Its two data
        // bytes are invented; this is not the native 512-invocation ROM procedure.
        async Task<JsonElement> Run(int threshold, int compensation)
        {
            var image = new int[0x122];
            new[] { 0x90, 0xA8, 0xC5, 7, 0x82, 0x20, 0x81 }.CopyTo(image, 0);
            image[0x120] = threshold; image[0x121] = compensation;
            var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
            {
                protocolVersion = 1,
                operation = "checksumSynthetic",
                images = new[] { new { id = "invented-pair", rom = image } },
                allowAssumptions = Array.Empty<string>(),
                scratchPatterns = new[] { 170 },
                synthetic = new
                {
                    entryPc = 0,
                    exitPcs = new[] { 7 },
                    allowedCodeRanges = new[] { new[] { 0, 7 } },
                    psw = 0x100,
                    lrb = 0x41,
                    usp = 0x180,
                    instructionBudget = 8,
                    dataSeeds = new[] { new[] { 0x80, 0x20 }, [0x81, 1], [0x208, 0], [0x120, 99], [0x121, 88] },
                    outputAddresses = new[] { 0x208 },
                },
            });
            var result = response.Response.GetProperty("syntheticResult");
            Assert.Equal(0, result.GetProperty("status").GetInt32());
            Assert.Empty(result.GetProperty("usedAssumptions").EnumerateArray());
            Assert.Equal(new[] { 0x120, 0x121 }, result.GetProperty("programReads").EnumerateArray().Select(item => item.GetInt32()));
            return result.Clone();
        }
        var a = await Run(40, 216);
        var b = await Run(41, 216);
        var c = await Run(41, P28ChecksumPreservingEditor.ComputeCompensation(216, 1));
        Assert.Equal(0, a.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(1, b.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(0, c.GetProperty("outputs")[0].GetInt32());
    }

    private static readonly string[] Fixes =
    [
        "word-ror-through-carry-preserves-noncarry-flags", "load-zero-flag-and-dd-contract",
        "word-srl-preserves-noncarry-flags", "bit-operands-use-byte-access", "clr-accumulator-zero-flag",
        "jrnz-dpl-byte-count", "adcb-r0-immediate-half-carry", "inc-x1-half-carry",
        "indexed-alternate-immediate-displacement", "word-data-access-alignment",
        "byte-add-direct-accumulator-half-carry", "byte-add-r0-accumulator-half-carry", "inc-indexed-x2-half-carry",
    ];
}
