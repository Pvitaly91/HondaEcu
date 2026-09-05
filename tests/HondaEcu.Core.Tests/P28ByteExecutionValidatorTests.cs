using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class P28ByteExecutionValidatorTests
{
    [Theory]
    [InlineData(0, false, 0, 255, 1, false, false, P28ExecutionCategory.Match)]
    [InlineData(0, false, 0, 255, 0, false, false, P28ExecutionCategory.Mismatch)]
    [InlineData(234, false, 1, -1, -1, false, false, P28ExecutionCategory.UnresolvedInstruction)]
    [InlineData(234, false, 0, 255, 1, false, false, P28ExecutionCategory.UnresolvedModel)]
    [InlineData(0, false, 2, -1, -1, false, false, P28ExecutionCategory.ExecutionError)]
    [InlineData(0, false, 3, -1, -1, false, false, P28ExecutionCategory.BudgetExceeded)]
    public void StructuredStatusesAreNotCollapsedIntoPasses(int raw, bool s, int status, int code, int extra,
        bool used, bool permitted, P28ExecutionCategory expected) =>
        Assert.Equal(expected, P28ByteExecutionValidator.ClassifyCompact((ushort)raw, s, status, code, extra, used, permitted));

    [Fact]
    public void HypothesisAgreementIsOnlyConditionalAndUnusedPermissionDoesNotDowngradeEstablishedMatches()
    {
        var hypothesis = P28CompactModel.EvaluateHypothesis(1000, false);
        Assert.Equal(P28ExecutionCategory.ConditionalMatch, P28ByteExecutionValidator.ClassifyCompact(
            1000, false, 0, hypothesis.Code, hypothesis.ExtraBit ? 1 : 0, true, true));
        Assert.Equal(P28ExecutionCategory.Match, P28ByteExecutionValidator.ClassifyCompact(0, false, 0, 255, 1, false, true));
        Assert.Throws<SliceProcessException>(() => P28ByteExecutionValidator.ClassifyCompact(0, false, 0, 255, 1, true, false));
        Assert.Throws<SliceProcessException>(() => P28ByteExecutionValidator.ClassifyCompact(0, false, 4, 255, 1, false, false));
        Assert.False(P28CompactModel.Evaluate(1000, false).Resolved);
    }

    [Fact]
    public void AdmissionRejectsMissingAcknowledgementWrongBaselineProfileAndIncompleteOrTamperedLineage()
    {
        var (baseline, profile, binding) = Fixture();
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true);
        Assert.Throws<InvalidDataException>(() => P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, false));
        var other = baseline.CreateModifiedCopy([new BytePatch(1, [1])]);
        Assert.Throws<InvalidDataException>(() => P28ByteExecutionValidator.ValidateAdmission(other, profile, binding, true));
        var wrongProfile = new RomProfile("p28-304", "Changed", "Changed profile digest", 32768, "synthetic-only", true, true);
        Assert.Throws<InvalidDataException>(() => P28ByteExecutionValidator.ValidateAdmission(baseline, wrongProfile, binding, true));
        var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, P28ThresholdLogic.GetSlotId(0, 0, false), 1);
        var patch = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
        P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, patch.Image, plan, patch.Report);
        Assert.Throws<InvalidDataException>(() => P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, patch.Image));
        Assert.Throws<InvalidDataException>(() => P28ByteExecutionValidator.ValidateAdmission(baseline, profile, binding, true, other, plan, patch.Report));
        Assert.Equal(P28BaselineBindingStatus.Mismatched, P28VtecInspector.Inspect(patch.Image, profile, [profile], true, binding).BaselineBinding.Status);
        Assert.Equal(binding.RomHash, baseline.Hash);
    }

    [Fact]
    public void BatchRequestContainsActualImmutableImageBytesAndOnlyExplicitAssumptions()
    {
        var (baseline, _, _) = Fixture();
        var original = baseline.ToArray();
        var strict = JsonSerializer.SerializeToElement(P28ByteExecutionValidator.CreateRequest(baseline, null, false));
        Assert.Equal(1, strict.GetProperty("protocolVersion").GetInt32());
        Assert.Equal("p28Batch", strict.GetProperty("operation").GetString());
        Assert.Empty(strict.GetProperty("allowAssumptions").EnumerateArray());
        Assert.Equal(new[] { 0, 85, 170 }, strict.GetProperty("scratchPatterns").EnumerateArray().Select(item => item.GetInt32()));
        Assert.Equal(original.Select(value => (int)value), strict.GetProperty("images")[0].GetProperty("rom").EnumerateArray().Select(item => item.GetInt32()));
        var conditional = JsonSerializer.SerializeToElement(P28ByteExecutionValidator.CreateRequest(baseline, null, true));
        Assert.Equal(P28ByteExecutionValidator.AddAssumption, conditional.GetProperty("allowAssumptions")[0].GetString());
        Assert.Equal(original, baseline.ToArray());
    }

    [Fact]
    public void IncompleteSuccessResponseIsProtocolFailureNotPassedExecution()
    {
        var (baseline, profile, binding) = Fixture();
        var empty = new SliceProcessResponse(JsonSerializer.SerializeToElement(new { protocolVersion = 1 }), "");
        var exception = Assert.Throws<SliceProcessException>(() => P28ByteExecutionValidator.Analyze(baseline, profile, binding, false, empty));
        Assert.Equal(SliceProcessFailure.Protocol, exception.Failure);
    }

    [Fact]
    public void MockBatchAccountingSeparatesUnresolvedAndConditionalAndMeasuresBothDerivedBitsAndReads()
    {
        // This is a response-accounting fixture, not executor or independent instruction evidence.
        var (baseline, profile, binding) = Fixture();
        var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, P28ThresholdLogic.GetSlotId(0, 0, false), 1);
        var patch = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
        foreach (var conditional in new[] { false, true })
        {
            var response = MockResponse(baseline, patch.Image, conditional);
            var report = P28ByteExecutionValidator.Analyze(baseline, profile, binding, conditional, response, patch.Image, plan, patch.Report);
            Assert.False(report.HasFailure);
            Assert.Equal(3 * 2 * 65536, report.Compact.Total);
            Assert.Equal(report.Compact.Total, report.Compact.CompletedWithoutAssumptions + report.Compact.ConditionalMatches + report.Compact.StoppedUnresolved);
            if (conditional)
            {
                Assert.True(report.Compact.ConditionalMatches > 0);
                Assert.Equal(0, report.Compact.StoppedUnresolved);
                Assert.Equal(new[] { P28ByteExecutionValidator.AddAssumption }, report.UsedAssumptions);
            }
            else
            {
                Assert.True(report.Compact.StoppedUnresolved > 0);
                Assert.Equal(0, report.Compact.ConditionalMatches);
                Assert.Empty(report.UsedAssumptions);
            }
            Assert.All(report.Threshold, item =>
            {
                Assert.Equal(12288, item.Counts.CompletedWithoutAssumptions);
                Assert.Equal(12288, item.ProgramReadChecks);
                Assert.Equal(6144, item.DisabledPreservationChecks);
            });
            Assert.NotNull(report.DerivedComparison);
            Assert.True(report.DerivedComparison.ExactChangedCaseSet);
            Assert.True(report.DerivedComparison.ChangedByteActuallyRead);
            Assert.Equal(6, report.DerivedComparison.ExpectedChangedCases);
            Assert.Equal(6, report.DerivedComparison.ActualChangedCases);
            Assert.Equal(3072, report.DerivedComparison.ChangedByteReadCases);
            Assert.Equal("SeededRomSlice", report.ExecutionKind);
            Assert.False(report.HardwareExecutionPerformed);
            Assert.False(report.FullEcuBootPerformed);
            Assert.False(report.PhysicalRpmAvailable);
            Assert.Equal(FlashSafetyStatus.NotFlashReady, report.FlashSafety);
        }
    }

    private static SliceProcessResponse MockResponse(RomImage baseline, RomImage derived, bool conditional)
    {
        var compact = new List<int[]>();
        foreach (var pattern in new[] { 0, 85, 170 })
        {
            for (var s = 0; s < 2; s++)
            {
                for (var raw = 0; raw <= ushort.MaxValue; raw++)
                {
                    var established = P28CompactModel.Evaluate((ushort)raw, s != 0);
                    if (established.Resolved)
                    {
                        compact.Add([pattern, raw, s, 0, established.Code!.Value, established.ExtraBit!.Value ? 1 : 0, 0]);
                    }
                    else if (conditional)
                    {
                        var hypothesis = P28CompactModel.EvaluateHypothesis((ushort)raw, s != 0);
                        compact.Add([pattern, raw, s, 0, hypothesis.Code, hypothesis.ExtraBit ? 1 : 0, 1]);
                    }
                    else
                    {
                        compact.Add([pattern, raw, s, 1, -1, -1, 0]);
                    }
                }
            }
        }
        var threshold = new List<int[]>();
        var images = new[] { baseline.ToArray(), derived.ToArray() };
        for (var image = 0; image < 2; image++)
        {
            foreach (var pattern in new[] { 0, 85, 170 })
            {
                for (var code = 0; code < 256; code++)
                {
                    for (var context = 0; context < 2; context++)
                    {
                        for (var prior = 0; prior < 4; prior++)
                        {
                            for (var enabled = 0; enabled < 2; enabled++)
                            {
                                var start = P28ThresholdLogic.BlockOffset + context * 4;
                                var output = prior;
                                if (enabled != 0)
                                {
                                    output = (code > images[image][start + ((prior & 1) == 0 ? 1 : 0)] ? 1 : 0) |
                                        (code > images[image][start + 2 + ((prior & 2) == 0 ? 1 : 0)] ? 2 : 0);
                                }
                                threshold.Add([image, pattern, code, context, prior, enabled, 0, output,
                                    enabled == 0 ? -1 : start, enabled == 0 ? -1 : start + 1,
                                    enabled == 0 ? -1 : start + 2, enabled == 0 ? -1 : start + 3]);
                            }
                        }
                    }
                }
            }
        }
        using var contracts = JsonDocument.Parse("""
            [{"id":"compact","entryPc":1991,"exitPcs":[2082],"stop":"BeforeInstruction",
              "allowedCodeRanges":[[1991,2082]],"psw":4353,"lrb":64,"usp":384,"instructionBudget":128,
              "inputs":["DATA00C4 unsigned LE word","DATA0217.4"],"outputs":["DATA0133","DATA00B8.4"],
              "codeDataSpacesSeparate":true,"freshStatePerCase":true,"interrupts":"NotInjected","peripherals":"Frozen"},
             {"id":"threshold","entryPc":4652,"exitPcs":[4717,4737],"stop":"BeforeInstruction",
              "allowedCodeRanges":[[4652,4717]],"psw":257,"lrb":32,"usp":640,"instructionBudget":128,
              "inputs":["DATA0133 code","DATA011E.3 context","DATA011E.4 enabled","DATA0131.1/.2 prior"],
              "outputs":["DATA0131.1/.2"],"fixedPreconditions":{"DATA00CC":0,"DATA0131bit0":0},
              "allowedProgramDataReads":[25922,25930],"codeDataSpacesSeparate":true,"freshStatePerCase":true,
              "interrupts":"NotInjected","peripherals":"Frozen"}]
            """);
        return new SliceProcessResponse(JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = "p28Batch",
            runnerVersion = "0.1.0",
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = new[] { "word-ror-through-carry-preserves-noncarry-flags", "load-zero-flag-and-dd-contract", "word-srl-preserves-noncarry-flags", "bit-operands-use-byte-access" },
            entryContracts = contracts.RootElement,
            compactRows = compact,
            thresholdRows = threshold,
            diagnostics = Array.Empty<object>(),
            syntheticResult = (object?)null,
        }), "");
    }

    private static (RomImage, RomProfile, P28ExactBaselineBinding) Fixture()
    {
        var baseline = RomImage.FromBytes(new byte[32768]);
        var profile = new RomProfile("p28-304", "Synthetic execution binding", "No OEM data", 32768, "synthetic-only", true, true,
            checksum: new ChecksumDefinition("unknown", ChecksumStatus.Unknown, 0, 0, ValidationLevel.PublicDocumentation));
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, baseline.Size, baseline.Hash,
            P28VtecInspector.ComputeProfileDigest(profile));
        return (baseline, profile, binding);
    }
}
