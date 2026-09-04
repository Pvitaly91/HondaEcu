using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28RawThresholdEditorTests
{
    [Theory]
    [InlineData(0)]
    [InlineData(255)]
    public void AllEightSlotsProduceOneByteCopiesAndExactOneStepPredicateEvidence(int rawValue)
    {
        var baseline = Baseline();
        var original = baseline.ToArray();
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var slots = P28ThresholdLogic.GetSlots();
        Assert.Equal(8, slots.Count);
        Assert.Equal(Enumerable.Range(0x6542, 8), slots.Select(slot => slot.Offset).Order());

        foreach (var slot in slots)
        {
            var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, slot.Id, rawValue);
            var applied = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
            Assert.Equal(slot.Context, plan.Context);
            Assert.Equal(slot.Pair, plan.Pair);
            Assert.Equal(slot.PriorState, plan.PriorState);
            Assert.Equal(slot.Offset, plan.Offset);
            Assert.Equal(new[] { slot.Offset }, plan.ExpectedChangedOffsets);
            Assert.False(plan.IsNoOp);
            Assert.Equal(1, applied.Report.ChangedByteCount);
            Assert.Equal(new[] { new P28RawByteDiff(slot.Offset, original[slot.Offset], (byte)rawValue) }, applied.Report.Diff);
            Assert.True(applied.Report.ReverseRestoresBaseline);
            Assert.Equal(ChecksumStatus.Unknown, applied.Report.ChecksumStatus);
            Assert.Equal(FlashReadinessStatus.PcInspectionOnly, applied.Report.FlashReadiness);
            Assert.Equal(FlashSafetyStatus.NotFlashReady, applied.Report.FlashSafety);
            Assert.Equal(256, applied.Report.PredicateImpact.Rows.Count);
            for (var code = 0; code < 256; code++)
            {
                var row = applied.Report.PredicateImpact.Rows[code];
                Assert.Equal((byte)code, row.CompactCode);
                Assert.Equal(code > original[slot.Offset], row.Before);
                Assert.Equal(code > rawValue, row.After);
            }
            Assert.False(applied.Report.PredicateImpact.Rows[rawValue].After);
            Assert.False(applied.Report.PredicateImpact.Rows[original[slot.Offset]].Before);
            Assert.Equal(Enumerable.Range(0, 256).Where(code => (code > original[slot.Offset]) != (code > rawValue)),
                applied.Report.PredicateImpact.ChangedCompactCodes);
            Assert.Equal(7, applied.Report.PredicateImpact.Selections.Count(selection => !selection.IsEditedSelection));
            Assert.All(applied.Report.PredicateImpact.Selections.Where(selection => !selection.IsEditedSelection), selection =>
            {
                Assert.True(selection.ThresholdByteUnchanged);
                Assert.True(selection.PredicateResultsUnchanged);
                Assert.Equal(256, selection.ComparedCodeCount);
            });
            var output = applied.Image.ToArray();
            for (var offset = 0; offset < output.Length; offset++)
            {
                Assert.Equal(offset == slot.Offset ? (byte)rawValue : original[offset], output[offset]);
            }
            var verification = P28RawThresholdEditor.Verify(applied.Image, baseline, profile, binding, plan, applied.Report);
            Assert.True(verification.IsValid);
            Assert.Equal((byte)rawValue, verification.ReadbackByte);
            Assert.True(verification.ReverseRestoresBaseline);
        }

        Assert.Equal(original, baseline.ToArray());
        Assert.Empty(profile.Hashes);
        Assert.Empty(profile.Parameters);
    }

    [Fact]
    public void NoOpIsExplicitAndDeterministicWithEmptyDiffAndPredicateChangeSet()
    {
        var baseline = Baseline();
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var slot = P28ThresholdLogic.GetSlots()[0];
        var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, slot.Id, baseline.ToArray()[slot.Offset]);
        var copy = P28RawThresholdPlan.Parse(plan.ToJson());
        var first = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
        var second = P28RawThresholdEditor.Apply(baseline, profile, binding, copy);

        Assert.True(plan.IsNoOp);
        Assert.Empty(plan.ExpectedChangedOffsets);
        Assert.Empty(plan.PredicateImpact.ChangedCompactCodes);
        Assert.All(plan.PredicateImpact.Selections, selection => Assert.True(selection.PredicateResultsUnchanged));
        Assert.Equal(baseline.Hash, first.Image.Hash);
        Assert.Empty(first.Report.Diff);
        Assert.Empty(first.Report.ChangedOffsets);
        Assert.Equal(0, first.Report.ChangedByteCount);
        Assert.Equal(first.Report.ToJson(), second.Report.ToJson());
        Assert.Equal(first.Report.ToJson(), P28RawThresholdPatchReport.Parse(first.Report.ToJson()).ToJson());
        Assert.Equal(P28RawThresholdEditor.ComputePlanDigest(plan), P28RawThresholdEditor.ComputePlanDigest(copy));
        Assert.DoesNotContain("createdAt", plan.ToJson(), StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("sourcePath", first.Report.ToJson(), StringComparison.OrdinalIgnoreCase);
        Assert.True(P28RawThresholdEditor.Verify(first.Image, baseline, profile, binding, copy, first.Report).IsValid);
    }

    [Theory]
    [InlineData(20, "equal")]
    [InlineData(10, "prior-clear-less-than-prior-set")]
    [InlineData(40, "prior-clear-greater-than-prior-set")]
    public void EqualAndReversedPairsAreReportedWithoutNormalization(int raw, string relation)
    {
        var baseline = Baseline();
        var profile = Profile();
        var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, Binding(baseline, profile), true,
            P28ThresholdLogic.GetSlotId(0, 0, false), raw);

        Assert.Equal("prior-clear-greater-than-prior-set", plan.PredicateImpact.BeforePair.Relation);
        Assert.Equal(relation, plan.PredicateImpact.AfterPair.Relation);
        Assert.Equal((byte)raw, plan.PredicateImpact.AfterPair.PriorClearThreshold);
        Assert.Equal((byte)20, plan.PredicateImpact.AfterPair.PriorSetThreshold);
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(256)]
    [InlineData(int.MinValue)]
    [InlineData(int.MaxValue)]
    public void PlanningRejectsOutOfRangeRawValues(int value)
    {
        var baseline = Baseline();
        var profile = Profile();
        Assert.Throws<ArgumentOutOfRangeException>(() => P28RawThresholdEditor.CreatePlan(
            baseline, profile, Binding(baseline, profile), true, P28ThresholdLogic.GetSlots()[0].Id, value));
    }

    [Fact]
    public void PlanningRequiresAcknowledgedExactOriginalBindingAndCorrectSize()
    {
        var baseline = Baseline();
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var slot = P28ThresholdLogic.GetSlots()[0].Id;
        Assert.Throws<InvalidOperationException>(() => P28RawThresholdEditor.CreatePlan(baseline, profile, binding, false, slot, 0));
        Assert.Throws<ArgumentNullException>(() => P28RawThresholdEditor.CreatePlan(baseline, profile, null!, true, slot, 0));
        Assert.Throws<ArgumentException>(() => P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, "0x6542", 0));
        Assert.Throws<RomSizeException>(() => P28RawThresholdEditor.CreatePlan(RomImage.FromBytes(new byte[32767]), profile, binding, true, slot, 0));
        var different = baseline.CreateModifiedCopy(new[] { new BytePatch(0, new byte[] { 123 }) });
        Assert.Throws<InvalidDataException>(() => P28RawThresholdEditor.CreatePlan(different, profile, binding, true, slot, 0));
        Assert.Throws<InvalidDataException>(() => P28RawThresholdEditor.CreatePlan(baseline, Profile("changed-profile"), binding, true, slot, 0));
    }

    [Fact]
    public void ApplyRederivesEveryTrustedPlanFieldIncludingPredicateAndEvidence()
    {
        var baseline = Baseline();
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var plan = Plan(baseline, profile, binding);
        var forgedPlans = new[]
        {
            plan with { FormatVersion = "2.0" },
            plan with { ModelId = "invented-model" },
            plan with { ProfileId = "different-profile" },
            plan with { ProfileDigest = new string('a', 64) },
            plan with { BindingDigest = new string('b', 64) },
            plan with { BaselineHash = baseline.Hash with { Sha256 = new string('c', 64) } },
            plan with { ExpectedOldByte = 19 },
            plan with { Offset = 0 },
            plan with { SlotId = P28ThresholdLogic.GetSlots()[1].Id },
            plan with { ExpectedChangedOffsets = new[] { plan.Offset, 0 } },
            plan with { ProfileAcknowledged = false },
            plan with { IsNoOp = true },
            plan with { PredicateImpact = plan.PredicateImpact with { EqualityResult = true } },
            plan with { Evidence = plan.Evidence with { PhysicalRpm = "Validated RPM" } },
            plan with { FlashReadiness = FlashReadinessStatus.BenchValidated },
            plan with { ExpectedChangedOffsets = null! },
        };
        foreach (var forged in forgedPlans)
        {
            Assert.ThrowsAny<Exception>(() => P28RawThresholdEditor.Apply(baseline, profile, binding, forged));
        }
        Assert.Throws<InvalidDataException>(() => P28RawThresholdEditor.Apply(baseline, Profile("new-profile-revision"), binding, plan));
        Assert.Throws<InvalidDataException>(() => P28RawThresholdEditor.Apply(baseline, profile,
            new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, baseline.Size, baseline.Hash, new string('d', 64)), plan));
    }

    [Fact]
    public void VerificationRejectsUndeclaredDiffWrongOutputAndResealedReportClaims()
    {
        var baseline = Baseline();
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var plan = Plan(baseline, profile, binding);
        var result = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
        var corrupted = result.Image.CreateModifiedCopy(new[] { new BytePatch(0, new byte[] { 122 }) });
        Assert.False(P28RawThresholdEditor.Verify(corrupted, baseline, profile, binding, plan, result.Report).IsValid);
        Assert.False(P28RawThresholdEditor.Verify(baseline, baseline, profile, binding, plan, result.Report).IsValid);
        Assert.False(P28RawThresholdEditor.Verify(RomImage.FromBytes(new byte[1]), baseline, profile, binding, plan, result.Report).IsValid);
        var reports = new[]
        {
            result.Report with { OutputHash = corrupted.Hash },
            result.Report with { PlanDigest = new string('a', 64) },
            result.Report with { ProfileDigest = new string('b', 64) },
            result.Report with { BindingDigest = new string('c', 64) },
            result.Report with { OldByte = 19 },
            result.Report with { NewByte = 1 },
            result.Report with { ChangedOffsets = new[] { 0, plan.Offset } },
            result.Report with { Diff = Array.Empty<P28RawByteDiff>() },
            result.Report with { ReverseRestoresBaseline = false },
            result.Report with { PredicateImpact = result.Report.PredicateImpact with { ChangedCompactCodes = Array.Empty<int>() } },
            result.Report with { Evidence = result.Report.Evidence with { HardwareChecks = "Passed" } },
        };
        foreach (var forged in reports)
        {
            var check = P28RawThresholdEditor.Verify(result.Image, baseline, profile, binding, plan, forged);
            Assert.False(check.IsValid);
            Assert.NotEmpty(check.Issues);
        }

        var alteredParent = baseline.CreateModifiedCopy(new[] { new BytePatch(1, new byte[] { 121 }) });
        Assert.False(P28RawThresholdEditor.Verify(result.Image, alteredParent, profile, binding, plan, result.Report).IsValid);
        // An analyst can declare a new hash, but cannot reuse this original one-step plan/report
        // with that substituted parent. No output binding is produced by this workflow.
        Assert.False(P28RawThresholdEditor.Verify(result.Image, result.Image, profile,
            Binding(result.Image, profile), plan, result.Report).IsValid);
    }

    [Fact]
    public void DerivedInspectionRequiresLineageAndKeepsOriginalBindingMismatchVisible()
    {
        var baseline = Baseline();
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var plan = Plan(baseline, profile, binding);
        var result = P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
        var derived = P28RawThresholdEditor.InspectDerived(result.Image, baseline, profile, binding, plan, result.Report);

        Assert.True(derived.VerifiedLineage);
        Assert.Equal(P28BaselineBindingStatus.Mismatched, derived.OutputInspection.BaselineBinding.Status);
        Assert.False(derived.OutputInspection.InterpretationApplied);
        Assert.False(derived.PhysicalRpmAvailable);
        Assert.Equal(8, derived.DerivedContexts.Sum(context => context.Slots.Count));
        Assert.Equal((byte)0, derived.DerivedContexts.SelectMany(context => context.Slots).Single(slot => slot.Id == plan.SlotId).Threshold);
        var invalid = P28RawThresholdEditor.InspectDerived(result.Image, baseline, profile, binding, plan,
            result.Report with { PlanDigest = new string('a', 64) });
        Assert.False(invalid.VerifiedLineage);
        Assert.Empty(invalid.DerivedContexts);
    }

    [Fact]
    public void StrictPlanAndReportReadersRejectMissingDefaultValuedFieldsAndNestedMalformedData()
    {
        var baseline = Baseline();
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var plan = Plan(baseline, profile, binding);
        var report = P28RawThresholdEditor.Apply(baseline, profile, binding, plan).Report;
        foreach (var json in new[] { plan.ToJson(), report.ToJson() })
        {
            var isPlan = json.Contains("expectedOldByte", StringComparison.Ordinal);
            Action<string> parse = text => { if (isPlan) { _ = P28RawThresholdPlan.Parse(text); } else { _ = P28RawThresholdPatchReport.Parse(text); } };
            Assert.ThrowsAny<Exception>(() => parse("null"));
            Assert.ThrowsAny<Exception>(() => parse("{"));
            Assert.ThrowsAny<Exception>(() => parse("{\"formatVersion\":\"1.0\"," + json[1..]));
            foreach (var mutate in new Action<JsonObject>[]
            {
                value => value.Remove("isNoOp"),
                value => value.Remove("offset"),
                value => value["newByte"] = null,
                value => value["newByte"] = 0.5,
                value => value["newByte"] = "1",
                value => value["newByte"] = -1,
                value => value["newByte"] = 256,
                value => value["formatVersion"] = "2.0",
                value => value["extra"] = false,
                value => value["baselineHash"]!["sha256"] = new string('g', 64),
                value => value["predicateImpact"]!["equalityResult"] = null,
                value => value["predicateImpact"]!.AsObject().Remove("equalityResult"),
                value => value["predicateImpact"]!["rows"]![0] = null,
                value => value["predicateImpact"]!["rows"]![0]!["extra"] = false,
            })
            {
                var edited = JsonNode.Parse(json)!.AsObject();
                mutate(edited);
                Assert.ThrowsAny<Exception>(() => parse(edited.ToJsonString()));
            }
        }
    }

    [Fact]
    public void PairWriterProtectsSourcesAndRollsBackIfSecondPublicationFails()
    {
        using var workspace = new SyntheticFixture();
        var baselinePath = workspace.WriteRom("original.dat", Baseline().ToArray());
        var baseline = RomImage.Load(baselinePath);
        var profile = Profile();
        var binding = Binding(baseline, profile);
        var result = P28RawThresholdEditor.Apply(baseline, profile, binding, Plan(baseline, profile, binding));
        var inputBefore = File.ReadAllBytes(baselinePath);
        var protectedPath = workspace.PathFor("binding.json");
        File.WriteAllText(protectedPath, binding.ToJson());
        Assert.Throws<InvalidOperationException>(() => P28RawThresholdEditor.WriteAtomic(result, baselinePath, workspace.PathFor("blocked.json")));
        Assert.Throws<InvalidOperationException>(() => P28RawThresholdEditor.WriteAtomic(result, workspace.PathFor("blocked.dat"), protectedPath, new[] { protectedPath }));

        var directoryAsOutput = workspace.PathFor("existing-directory");
        Directory.CreateDirectory(directoryAsOutput);
        var rollbackReport = workspace.PathFor("rolled-back.json");
        var publicationFailure = Record.Exception(() => P28RawThresholdEditor.WriteAtomic(result, directoryAsOutput, rollbackReport));
        Assert.True(publicationFailure is IOException or UnauthorizedAccessException);
        Assert.False(File.Exists(rollbackReport));
        Assert.Empty(Directory.GetFiles(workspace.DirectoryPath, "*.tmp", SearchOption.AllDirectories));

        var outputPath = workspace.PathFor("output.dat");
        var reportPath = workspace.PathFor("report.json");
        P28RawThresholdEditor.WriteAtomic(result, outputPath, reportPath, new[] { baselinePath, protectedPath });
        Assert.Equal(result.Image.Hash, RomImage.Load(outputPath).Hash);
        Assert.Equal(result.Report.ToJson(), File.ReadAllText(reportPath));
        Assert.Throws<IOException>(() => P28RawThresholdEditor.WriteAtomic(result, outputPath, workspace.PathFor("second-report.json")));
        Assert.False(File.Exists(workspace.PathFor("second-report.json")));
        Assert.Equal(inputBefore, File.ReadAllBytes(baselinePath));
    }

    private static RomImage Baseline()
    {
        var bytes = SyntheticFixture.Bytes();
        new byte[] { 20, 30, 40, 50, 60, 70, 80, 90 }.CopyTo(bytes, P28ThresholdLogic.BlockOffset);
        return RomImage.FromBytes(bytes);
    }

    private static RomProfile Profile(string revision = "synthetic-research-only") =>
        new("p28-304", "Synthetic raw threshold fixture", "Contains no OEM data", 32768, revision, true, true,
            checksum: new ChecksumDefinition("unknown", ChecksumStatus.Unknown, 0, 0, ValidationLevel.PublicDocumentation));

    private static P28ExactBaselineBinding Binding(RomImage image, RomProfile profile) =>
        new(1, P28CompactModel.ModelId, profile.Id, image.Size, image.Hash, P28VtecInspector.ComputeProfileDigest(profile));

    private static P28RawThresholdPlan Plan(RomImage image, RomProfile profile, P28ExactBaselineBinding binding) =>
        P28RawThresholdEditor.CreatePlan(image, profile, binding, true, P28ThresholdLogic.GetSlotId(0, 0, true), 0);
}
