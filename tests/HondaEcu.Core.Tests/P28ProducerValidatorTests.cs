using System.Text.Json;

namespace HondaEcu.Core.Tests;

public sealed class P28ProducerValidatorTests
{
    [Fact]
    public void MockStageAccountingRetainsCumulativeConditionalStatusAndSeparatesReadSelectionAndPredicateChange()
    {
        var (baseline, profile, binding, input, plan, patch) = Fixture();
        var response = MockResponse(input, true);
        var report = P28ProducerValidator.Analyze(baseline, profile, binding, [input], [P28ProducerModel.AddEr1Assumption],
            response, patch.Image, plan, patch.Report);
        Assert.False(report.HasFailure);
        Assert.Equal(1, report.Producer.ConditionalMatches);
        Assert.Equal(1, report.ProducerToCompact.ConditionalMatches);
        Assert.Equal(0, report.ProducerToCompact.MatchesWithoutAssumptions);
        Assert.All(report.Threshold, item => Assert.Equal(1, item.Counts.ConditionalMatches));
        Assert.Equal(new[] { P28ProducerModel.AddEr1Assumption }, report.UsedAssumptions);
        Assert.NotNull(report.DerivedComparison);
        Assert.Equal(1, report.DerivedComparison.PlannedSlotReadCases);
        Assert.Equal(1, report.DerivedComparison.PlannedSlotSelectedCases);
        Assert.Equal(1, report.DerivedComparison.ExpectedChangedPredicateCases);
        Assert.Equal(1, report.DerivedComparison.ActualChangedPredicateCases);
        Assert.True(report.DerivedComparison.ExactChangedCaseSet);
        Assert.False(report.PhysicalRpmAvailable);
        Assert.False(report.FullEcuBootPerformed);
        Assert.Equal(FlashSafetyStatus.NotFlashReady, report.FlashSafety);
    }

    [Fact]
    public void MockUnresolvedProducerIsNotPassedAndPreventsBothDownstreamStages()
    {
        var (baseline, profile, binding, input, plan, patch) = Fixture();
        var report = P28ProducerValidator.Analyze(baseline, profile, binding, [input], [], MockResponse(input, false), patch.Image, plan, patch.Report);
        Assert.Equal(1, report.Producer.StoppedUnresolved);
        Assert.Equal(0, report.Producer.MatchesWithoutAssumptions);
        Assert.Equal(1, report.ProducerToCompact.NotRun);
        Assert.All(report.Threshold, item => Assert.Equal(1, item.Counts.NotRun));
        Assert.Equal(0, report.DerivedComparison!.EligiblePairedCases);
        Assert.Empty(report.UsedAssumptions);
    }

    [Fact]
    public void MockUnexpectedGValueIsAMismatchAndLostCumulativeAssumptionIsProtocolFailure()
    {
        var (baseline, profile, binding, input, plan, patch) = Fixture();
        var changed = MockResponse(input, true, mutate: row => row[5]++);
        var mismatch = P28ProducerValidator.Analyze(baseline, profile, binding, [input], [P28ProducerModel.AddEr1Assumption],
            changed, patch.Image, plan, patch.Report);
        Assert.True(mismatch.HasFailure);
        Assert.Equal(1, mismatch.Producer.Mismatches);
        Assert.Equal(1, mismatch.ProducerToCompact.Mismatches);
        var lost = MockResponse(input, true, mutate: row => row[20] = 0);
        var exception = Assert.Throws<SliceProcessException>(() => P28ProducerValidator.Analyze(baseline, profile, binding,
            [input], [P28ProducerModel.AddEr1Assumption], lost, patch.Image, plan, patch.Report));
        Assert.Equal(SliceProcessFailure.Protocol, exception.Failure);
    }

    [Fact]
    public void IncompleteProtocolAndTamperedLineageCannotBecomeSuccessfulProducerReports()
    {
        var (baseline, profile, binding, input, plan, patch) = Fixture();
        var incomplete = new SliceProcessResponse(JsonSerializer.SerializeToElement(new { protocolVersion = 1 }), "");
        Assert.Throws<SliceProcessException>(() => P28ProducerValidator.Analyze(baseline, profile, binding, [input], [], incomplete));
        var tampered = patch.Image.CreateModifiedCopy([new BytePatch(1, [1])]);
        Assert.Throws<InvalidDataException>(() => P28ProducerValidator.Analyze(baseline, profile, binding, [input], [],
            MockResponse(input, false), tampered, plan, patch.Report));
    }

    [Fact]
    public void UnexpectedUnresolvedThresholdFailsEvenWithoutADerivedImage()
    {
        var (baseline, profile, binding, input, _, _) = Fixture();
        var report = P28ProducerValidator.Analyze(baseline, profile, binding, [input], [P28ProducerModel.AddEr1Assumption],
            MockResponse(input, true, includeDerived: false, thresholdUnresolved: true));
        Assert.True(report.HasFailure);
        Assert.Equal(1, report.Threshold[0].Counts.StoppedUnresolved);
        Assert.Null(report.DerivedComparison);
    }

    private static SliceProcessResponse MockResponse(P28ProducerInput input, bool conditional, Action<int[]>? mutate = null,
        bool includeDerived = true, bool thresholdUnresolved = false)
    {
        // Only protocol/comparison accounting is mocked. Actual process tests are separate.
        var row = conditional
            ? new[] { 0, 0, 0, 0x07A5, 70, 3750, 0, 0, 3125, 3125, 3125, 3125, 3125, 3125, 1, 0, 0x0822, 8, 1, 0, 1, 123 }
            : [0, 0, 1, 0x077E, 8, 123, 0x10, 0, 3125, 3125, 3125, 3125, 3125, 3125, 0, 4, -1, 0, -1, -1, 0, 3125];
        mutate?.Invoke(row);
        int[][] threshold = conditional
            ? [[0, 0, 0, 3, 0x6542, 0x6543, 0x6544, 0x6545, 1], [0, 1, 0, 2, 0x6542, 0x6543, 0x6544, 0x6545, 1]]
            : [[0, 0, 4, -1, -1, -1, -1, -1, 0], [0, 1, 4, -1, -1, -1, -1, -1, 0]];
        if (!includeDerived) { threshold = [threshold[0]]; }
        if (thresholdUnresolved)
        {
            foreach (var item in threshold)
            {
                item[2] = 1;
                for (var index = 3; index < 8; index++) { item[index] = -1; }
            }
        }
        using var contracts = JsonDocument.Parse("""
            [{"id":"producer","entryPc":1906,"exitPcs":[1957],"stop":"BeforeInstruction",
              "allowedCodeRanges":[[1906,1957],[31468,31486]],"psw":4353,"lrb":64,"usp":384,
              "instructionBudget":192,"sampleAddresses":[864,866,868,870,872,874],
              "previousTAddress":196,"statusAddresses":[535,561],"codeDataSpacesSeparate":true,
              "interrupts":"NotInjected","peripherals":"Frozen","admission":"ExactInstructionForms"},
             {"id":"producerToCompact","composition":"StagedControlFlowSameCpuRam",
              "fromPc":1957,"toPc":1991,"exitPc":2082,"instructionBudget":128,
              "reseedsCpuOrRam":false,"skippedRange":[1957,1991],"continuousWholeRoutine":false,
              "transferredInputs":["actual DATA00C4","actual DATA0217.4"],"assumptions":"Cumulative"},
             {"id":"composedThreshold","composition":"StagedFreshThresholdSeed",
              "entryPc":4652,"exitPcs":[4717,4737],"allowedCodeRanges":[[4652,4717]],
              "psw":257,"lrb":32,"usp":640,"instructionBudget":128,
              "codeInput":"ActualCompactExecutionOutput","contextPriorEnabled":"ExplicitPerCaseInputs",
              "allowedAssumptions":[],"cumulativeAssumptionsRetained":true}]
            """);
        return new SliceProcessResponse(JsonSerializer.SerializeToElement(new
        {
            protocolVersion = 1,
            operation = "producerBatch",
            runnerVersion = "0.2.0",
            upstreamCommit = P28ByteExecutionValidator.UpstreamCommit,
            localSemanticFixes = new[]
            {
                "word-ror-through-carry-preserves-noncarry-flags", "load-zero-flag-and-dd-contract", "word-srl-preserves-noncarry-flags",
                "bit-operands-use-byte-access", "clr-accumulator-zero-flag", "jrnz-dpl-byte-count", "adcb-r0-immediate-half-carry",
                "inc-x1-half-carry", "indexed-alternate-immediate-displacement", "word-data-access-alignment",
            },
            entryContracts = contracts.RootElement,
            producerRows = new[] { row },
            producerThresholdRows = threshold,
            diagnostics = Array.Empty<object>(),
        }), "");
    }

    private static (RomImage Baseline, RomProfile Profile, P28ExactBaselineBinding Binding, P28ProducerInput Input,
        P28RawThresholdPlan Plan, P28RawThresholdPatchResult Patch) Fixture()
    {
        var baseline = RomImage.FromBytes(new byte[32768]);
        var profile = new RomProfile("p28-304", "Synthetic producer binding", "No OEM data", 32768, "synthetic-only", true, true,
            checksum: new ChecksumDefinition("unknown", ChecksumStatus.Unknown, 0, 0, ValidationLevel.PublicDocumentation));
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768, baseline.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, P28ThresholdLogic.GetSlotId(0, 0, false), 1);
        var patch = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
        var input = P28ProducerModelTests.Input([3125, 3125, 3125, 3125, 3125, 3125]) with { ThresholdEnabled = true };
        return (baseline, profile, binding, input, plan, patch);
    }
}
