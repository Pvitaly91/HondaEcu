using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28ChecksumPreservingEditorTests
{
    [Fact]
    public void All65536OldByteResiduePairsFollowIndependentModuloArithmetic()
    {
        var comparisons = 0;
        for (var original = 0; original <= 255; original++)
            for (var residue = 0; residue <= 255; residue++)
            {
                var expected = (original + 256 - residue) % 256;
                var actual = P28ChecksumPreservingEditor.ComputeCompensation((byte)original, (byte)residue);
                Assert.Equal(expected, actual);
                Assert.Equal(0, (residue + actual - original + 256) % 256);
                comparisons++;
            }
        Assert.Equal(65536, comparisons);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(39)]
    [InlineData(40)]
    [InlineData(41)]
    [InlineData(254)]
    [InlineData(255)]
    public void AllEightSlotsHaveExactTwoByteOrNoOpDiffAndPreserveIntermediatePredicates(int raw)
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var before = baseline.ToArray();
        foreach (var slot in P28ThresholdLogic.GetSlots())
        {
            var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(slot.Id, raw);
            var plan = preview.Plan;
            var report = preview.Report;
            var noOp = raw == 40;
            Assert.True(plan.SyntheticOnly);
            Assert.Equal(P28RawThresholdEditor.FormatVersion, plan.ThresholdPlan.FormatVersion);
            Assert.Equal(noOp ? 0 : 2, report.ChangedByteCount);
            Assert.Equal(noOp, plan.IsNoOp);
            Assert.Equal(noOp, report.IsNoOp);
            Assert.Equal((40 + 256 - raw) % 256, (plan.Compensation.NewByte + 256 - 192) % 256);
            Assert.Equal((byte)((raw + 256 - 40) % 256), plan.IntermediateResidue);
            Assert.Equal((byte)0, plan.BaselineResidue);
            Assert.Equal((byte)0, plan.FinalResidue);
            Assert.Equal(0, preview.Image.ToArray().Sum(value => (int)value) % 256);
            Assert.Equal(plan.IntermediateResidue, preview.Intermediate.ToArray().Sum(value => (int)value) % 256);
            Assert.Equal(noOp ? Array.Empty<int>() : new[] { slot.Offset, 0x7000 }, report.Diff.Select(item => item.Offset));
            Assert.Equal(report.Diff, plan.ExpectedDiff);
            var actualBytes = preview.Image.ToArray();
            for (var offset = 0; offset < before.Length; offset++)
                Assert.Equal(offset == slot.Offset ? (byte)raw : offset == 0x7000 ? plan.Compensation.NewByte : before[offset], actualBytes[offset]);
            var intermediateBytes = preview.Intermediate.ToArray();
            foreach (var selection in P28ThresholdLogic.GetSlots())
                for (var code = 0; code <= 255; code++)
                {
                    var intermediateValue = intermediateBytes[selection.Offset];
                    var finalValue = actualBytes[selection.Offset];
                    Assert.Equal(code > intermediateValue, P28ThresholdLogic.Evaluate(finalValue, (byte)code));
                    Assert.Equal(selection.Id == slot.Id ? code > raw : code > 40, code > finalValue);
                }
            Assert.True(report.ThresholdOnlyBehaviorPreserved);
            Assert.True(report.ReverseRestoresBaseline);
            Assert.Equal(ChecksumStatus.Unknown, report.NativeChecksumStatus);
            Assert.Equal(NativeChecksumExecutionStatus.NotRun, report.ExecutionStatus);
            Assert.Equal(FlashReadinessStatus.PcInspectionOnly, report.FlashReadiness);
            Assert.Equal(FlashSafetyStatus.NotFlashReady, report.FlashSafety);
            Assert.Contains("no Honda", report.EvidenceScope, StringComparison.OrdinalIgnoreCase);
            Assert.True(P28ChecksumPreservingEditor.VerifySynthetic(preview.Image, baseline, profile, binding, plan, report).IsValid);

            var rawIntermediate = P28RawThresholdEditor.Apply(baseline, profile, binding, plan.ThresholdPlan);
            Assert.Equal(rawIntermediate.Image.Hash, preview.Intermediate.Hash);
            Assert.True(P28RawThresholdEditor.Verify(preview.Intermediate, baseline, profile, binding, plan.ThresholdPlan, rawIntermediate.Report).IsValid);
            Assert.Equal(noOp, P28RawThresholdEditor.Verify(preview.Image, baseline, profile, binding, plan.ThresholdPlan, rawIntermediate.Report).IsValid);
        }
        Assert.Equal(before, baseline.ToArray());
    }

    [Fact]
    public void PlanAndReportRoundTripDeterministicallyAndReverseRestorationUsesOriginalParent()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(Slot, 255);
        var plan = P28ChecksumPreservingPlan.Parse(preview.Plan.ToJson());
        var report = P28ChecksumPreservingReport.Parse(preview.Report.ToJson());
        Assert.Equal(preview.Plan.ToJson(), plan.ToJson());
        Assert.Equal(preview.Report.ToJson(), report.ToJson());
        Assert.Equal(P28ChecksumPreservingEditor.ComputePlanDigest(preview.Plan), P28ChecksumPreservingEditor.ComputePlanDigest(plan));
        Assert.Equal(preview.Report.ToJson(), P28ChecksumPreservingEditor.ApplySynthetic(baseline, profile, binding, plan).Report.ToJson());
        var reverse = preview.Image.ToArray();
        reverse[plan.ThresholdPlan.Offset] = plan.ThresholdPlan.ExpectedOldByte;
        reverse[plan.Compensation.Offset] = plan.Compensation.OldByte;
        Assert.Equal(baseline.ToArray(), reverse);
        Assert.True(P28ChecksumPreservingEditor.VerifySynthetic(preview.Image, baseline, profile, binding, plan, report).IsValid);
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ApplySynthetic(preview.Image, profile, binding, plan));
        var rebound = Bind(preview.Image, profile);
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.ApplySynthetic(preview.Image, profile, rebound, plan));
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(256)]
    [InlineData(int.MaxValue)]
    public void OutOfRangeThresholdRequestsAreNeverWrapped(int raw) =>
        Assert.Throws<ArgumentOutOfRangeException>(() => P28ChecksumPreservingEditor.CreateSyntheticPreview(Slot, raw));

    [Fact]
    public void FixedSyntheticAuthorityCannotBeReusedForAnotherImageProfileOrBinding()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var changed = baseline.CreateModifiedCopy([new BytePatch(0x7100, new byte[] { 1 })]);
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.CreateSyntheticPlan(changed, profile,
            Bind(changed, profile), true, Slot, 41));
        var differentProfile = new RomProfile("p28-304", "Different synthetic profile", "Different", 32768, "Synthetic", true, true);
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.CreateSyntheticPlan(baseline, differentProfile,
            Bind(baseline, differentProfile), true, Slot, 41));
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.CreateSyntheticPlan(baseline, profile,
            new P28ExactBaselineBinding(2, binding.ModelId, binding.ProfileId, binding.ExpectedSize, binding.RomHash, binding.ProfileDigest), true, Slot, 41));
        Assert.Throws<InvalidOperationException>(() => P28ChecksumPreservingEditor.CreateSyntheticPlan(baseline, profile, binding, false, Slot, 41));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(0x2B70)]
    [InlineData(0x2BAD)]
    [InlineData(0x60FB)]
    [InlineData(0x6542)]
    [InlineData(0x6543)]
    [InlineData(0x6544)]
    [InlineData(0x6545)]
    [InlineData(0x6546)]
    [InlineData(0x6547)]
    [InlineData(0x6548)]
    [InlineData(0x6549)]
    [InlineData(32768)]
    public void ForbiddenCompensationOverlapCannotBecomeAPlan(int offset)
    {
        var plan = P28ChecksumPreservingEditor.CreateSyntheticPreview(Slot, 41).Plan;
        var forged = plan with { Compensation = plan.Compensation with { Offset = offset } };
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingPlan.Parse(forged.ToJson()));
    }

    [Fact]
    public void SelfConsistentForgedDefinitionOldByteFormulaResiduesAndDigestsAreRejected()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(Slot, 41);
        var plan = preview.Plan;
        var alternate = plan.Compensation with { Offset = 0x7001, OldByte = 1, NewByte = 0 };
        P28ChecksumPreservingPlan[] forgeries =
        [
            plan with { CompensationDefinitionId = "candidateUnused" },
            plan with { CompensationEvidenceIdentity = new string('a', 64) },
            plan with { Compensation = plan.Compensation with { FormulaId = "arbitrary-repair" } },
            plan with { Compensation = alternate, ExpectedDiff = [plan.ExpectedDiff[0], new(alternate.Offset, alternate.OldByte, alternate.NewByte)] },
            plan with { Compensation = plan.Compensation with { OldByte = 193, NewByte = 192 }, ExpectedDiff = [plan.ExpectedDiff[0], new(0x7000, 193, 192)] },
            plan with { IntermediateResidue = 2, Compensation = plan.Compensation with { NewByte = 190 }, ExpectedDiff = [plan.ExpectedDiff[0], new(0x7000, 192, 190)] },
            plan with { ProfileDigest = new string('b', 64) },
            plan with { BindingDigest = new string('c', 64) },
            plan with { ThresholdPlan = plan.ThresholdPlan with { ExpectedOldByte = 39 } },
            plan with { NativeChecksumStatus = ChecksumStatus.Valid },
            plan with { ExecutionStatus = NativeChecksumExecutionStatus.Match },
            plan with { SyntheticOnly = false },
        ];
        foreach (var forged in forgeries)
        {
            Assert.ThrowsAny<Exception>(() => P28ChecksumPreservingEditor.ApplySynthetic(baseline, profile, binding, forged));
            Assert.False(P28ChecksumPreservingEditor.VerifySynthetic(preview.Image, baseline, profile, binding, forged, preview.Report).IsValid);
        }
    }

    [Fact]
    public void ExtraChangesEvenWithZeroSumAndForgedOutputReportsFailIndependentVerification()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(Slot, 41);
        var changed = preview.Image.CreateModifiedCopy([new BytePatch(0x7100, new byte[] { 1, 255 })]);
        Assert.Equal(0, changed.ToArray().Sum(value => (int)value) % 256);
        var forged = preview.Report with { OutputHash = changed.Hash };
        Assert.False(P28ChecksumPreservingEditor.VerifySynthetic(changed, baseline, profile, binding, preview.Plan, forged).IsValid);
        P28ChecksumPreservingReport[] reports =
        [
            preview.Report with { PlanDigest = new string('0', 64) },
            preview.Report with { BaselineHash = preview.Image.Hash },
            preview.Report with { CompensationEvidenceIdentity = "forged" },
            preview.Report with { ReverseRestoresBaseline = false },
            preview.Report with { Diff = [preview.Report.Diff[0]] },
            preview.Report with { NativeChecksumStatus = ChecksumStatus.Valid },
            preview.Report with { ExecutionStatus = NativeChecksumExecutionStatus.Match },
        ];
        foreach (var report in reports)
            Assert.False(P28ChecksumPreservingEditor.VerifySynthetic(preview.Image, baseline, profile, binding, preview.Plan, report).IsValid);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void ClosedJsonShapeRejectsUnknownMissingDuplicateNullAndUnsupportedFields(bool isPlan)
    {
        var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(Slot, 41);
        var json = isPlan ? preview.Plan.ToJson() : preview.Report.ToJson();
        Action<string> parse = text => { if (isPlan) _ = P28ChecksumPreservingPlan.Parse(text); else _ = P28ChecksumPreservingReport.Parse(text); };
        Action<JsonObject>[] edits =
        [
            node => node["formatVersion"] = "99.0",
            node => node.Remove("isNoOp"),
            node => node["evidenceScope"] = null,
            node => node["arbitraryOffset"] = 32767,
            node => node["syntheticOnly"] = false,
            node => node["nativeChecksumStatus"] = "valid",
            node => node["finalResidue"] = 0.1,
            node => node[isPlan ? "expectedDiff" : "diff"]![0]!["extra"] = true,
        ];
        foreach (var edit in edits)
        {
            var node = JsonNode.Parse(json)!.AsObject(); edit(node);
            Assert.ThrowsAny<Exception>(() => parse(node.ToJsonString()));
        }
        Assert.Throws<InvalidDataException>(() => parse(json.Replace("\"isNoOp\": false", "\"isNoOp\": false, \"isNoOp\": false", StringComparison.Ordinal)));
        if (isPlan)
        {
            var node = JsonNode.Parse(json)!.AsObject(); node["thresholdPlan"]!["extra"] = false;
            Assert.Throws<InvalidDataException>(() => parse(node.ToJsonString()));
        }
    }

    [Fact]
    public void PublicProductionPathsCannotPromoteSyntheticEvidenceOrNonzeroParent()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var preview = P28ChecksumPreservingEditor.CreateSyntheticPreview(Slot, 41);
        var status = P28ChecksumPreservingEditor.GetAvailability(baseline, profile, binding, true);
        Assert.False(status.IsAvailable);
        Assert.Equal("rejected-checksum-contract", status.Status);
        Assert.Null(status.Offset);
        Assert.Null(status.DefinitionId);
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.CreatePlan(baseline, profile, binding, true, Slot, 41));
        Assert.Throws<InvalidDataException>(() => P28ChecksumPreservingEditor.Apply(baseline, profile, binding, preview.Plan));
        Assert.False(P28ChecksumPreservingEditor.Verify(preview.Image, baseline, profile, binding, preview.Plan, preview.Report).IsValid);
        var badParent = baseline.CreateModifiedCopy([new BytePatch(0x7100, new byte[] { 1 })]);
        var badStatus = P28ChecksumPreservingEditor.GetAvailability(badParent, profile, Bind(badParent, profile), true);
        Assert.Equal("rejected-nonzero-parent", badStatus.Status);
        Assert.False(badStatus.IsAvailable);
        Assert.Equal("rejected-original-binding", P28ChecksumPreservingEditor.GetAvailability(baseline, profile, binding, false).Status);
    }

    private static string Slot => P28ThresholdLogic.GetSlots()[0].Id;
    private static P28ExactBaselineBinding Bind(RomImage image, RomProfile profile) => new(1, P28CompactModel.ModelId,
        profile.Id, image.Size, image.Hash, P28VtecInspector.ComputeProfileDigest(profile));
}
