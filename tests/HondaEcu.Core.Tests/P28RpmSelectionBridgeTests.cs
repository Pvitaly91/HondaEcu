using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28RpmSelectionBridgeTests
{
    private static readonly Lazy<(P28RpmQuery Query, P28RpmPlanningReport Preview)> Shared = new(() =>
    {
        var query = Query();
        return (query, P28RpmPlanner.Analyze(query));
    });

    [Fact]
    public void ConfirmedBestCandidateUsesOnlyExistingM1gTwoByteCompositionAndSeparateEvidence()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var (query, preview) = Shared.Value;
        var chosen = preview.BestCandidates[0].RawValue;
        var before = baseline.ToArray();
        var sourceSnapshot = query.Scenario!.ToJson();
        var result = P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true,
            query, preview, chosen, chosen, true);
        var independentM1g = P28ChecksumPreservingEditor.CreateSyntheticPreview(query.Slot.Id, chosen);
        Assert.Equal(independentM1g.Plan.ToJson(), result.CompositionPreview.Plan.ToJson());
        Assert.Equal(independentM1g.Image.ToArray(), result.CompositionPreview.Image.ToArray());
        Assert.Equal(new[] { query.Slot.Offset, P28ChecksumPreservingDefinitions.SyntheticOffset },
            result.CompositionPreview.Report.Diff.Select(item => item.Offset));
        Assert.Equal(2, result.CompositionPreview.Report.ChangedByteCount);
        Assert.Equal(before, baseline.ToArray());
        Assert.Equal(sourceSnapshot, query.Scenario.ToJson());

        var selection = result.SelectionReport;
        Assert.Equal(chosen, selection.ChosenRaw);
        Assert.Equal(chosen, selection.ConfirmedRaw);
        Assert.Equal(preview.ComputeDigest(), selection.AnalysisDigest);
        Assert.Equal(query.QueryDigest, selection.QueryDigest);
        Assert.Equal(query.ScenarioDigest, selection.ScenarioDigest);
        Assert.Equal(query.Slot, selection.Slot);
        Assert.Equal(query.RequestedRpm, selection.RequestedRpm);
        Assert.Equal(P28ProducerModel.ModelId, selection.ProducerModelId);
        Assert.Equal(P28CompactModel.ModelId, selection.CompactModelId);
        Assert.Equal(P28RawThresholdEditor.ComputePlanDigest(result.CompositionPreview.Plan.ThresholdPlan), selection.RawPlanDigest);
        Assert.Equal(P28ChecksumPreservingEditor.ComputePlanDigest(result.CompositionPreview.Plan), selection.ComposedPlanDigest);
        Assert.Equal(preview.BestCandidates.Select(item => (int)item.RawValue).Order(), selection.BestRawCandidates);
        Assert.Equal(preview.UsedAssumptions, selection.UsedAssumptions);
        Assert.True(selection.TransitionBand.LowerInclusive);
        Assert.True(selection.TransitionBand.UpperInclusive);
        Assert.False(selection.MixedRegion.LowerInclusive);
        Assert.False(selection.MixedRegion.UpperInclusive);
        Assert.Equal(selection.TransitionBand.LowerRpm, selection.MixedRegion.LowerRpm);
        Assert.Equal(selection.TransitionBand.UpperRpm, selection.MixedRegion.UpperRpm);
        Assert.Contains("not a measured probability", selection.IntervalSemantics, StringComparison.Ordinal);
        Assert.True(selection.SyntheticOnly);
        Assert.Equal(ChecksumStatus.Unknown, selection.NativeChecksumStatus);
        Assert.Equal(NativeChecksumExecutionStatus.NotRun, selection.NativeExecutionStatus);
        Assert.Equal("NotRun", selection.HardwareStatus);
        Assert.False(selection.PhysicalRpmAvailable);
        Assert.Equal(FlashReadinessStatus.PcInspectionOnly, selection.FlashReadiness);
        Assert.Equal(FlashSafetyStatus.NotFlashReady, selection.FlashSafety);
        P28RpmSelectionBridge.ValidateSelectionAgainstPlan(query, selection, result.CompositionPreview.Plan);
    }

    [Fact]
    public void SelectionRoundTripsButRemainsDescriptiveAndListStorageIsFrozen()
    {
        var result = Select();
        var original = result.SelectionReport;
        var restored = P28RpmSelectionReport.Parse(original.ToJson());
        Assert.Equal(original.ToJson(false), restored.ToJson(false));
        Assert.Equal(original.ComputeDigest(), restored.ComputeDigest());
        Assert.Throws<NotSupportedException>(() => ((IList<int>)restored.BestRawCandidates)[0] = 0);
        Assert.Throws<NotSupportedException>(() => ((IList<string>)restored.UsedAssumptions)[0] = "forged");
        var altered = original with { ChosenRaw = 0 };
        Assert.NotEqual(original.ToJson(), altered.ToJson());
        Assert.Equal(original.ToJson(), result.SelectionReport.ToJson());
    }

    [Fact]
    public void EveryExactlyTiedBestRawRequiresItsOwnExplicitChoiceAndIsRetainedInProvenance()
    {
        // Independent construction: midpoint of the outer endpoints K/200 and
        // K/155 for the two adjacent candidate bands, with invented K=6000000.
        var query = Query(target: "1065000/31");
        var preview = P28RpmPlanner.Analyze(query);
        Assert.Equal(new byte[] { 253, 254 }, preview.BestCandidates.Select(item => item.RawValue));
        Assert.All(preview.BestCandidates, item => Assert.Equal("135000/31", item.MinimaxError));
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        foreach (var raw in new[] { 253, 254 })
        {
            var result = P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true,
                query, preview, raw, raw, true);
            Assert.Equal(raw, result.SelectionReport.ChosenRaw);
            Assert.Equal(new[] { 253, 254 }, result.SelectionReport.BestRawCandidates);
            Assert.Equal(raw, result.CompositionPreview.Plan.ThresholdPlan.NewByte);
        }
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public void RawAndConditionalDisclosureRequireSeparateExplicitConfirmation(bool matchingRaw, bool conditional)
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var (query, preview) = Shared.Value;
        var chosen = preview.BestCandidates[0].RawValue;
        Assert.ThrowsAny<Exception>(() => P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true,
            query, preview, chosen, matchingRaw ? chosen : (chosen + 1) % 256, conditional));
    }

    [Fact]
    public void NonBestRawAndTamperedPreviewCannotBorrowValidQueryOrPermission()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var (query, preview) = Shared.Value;
        var chosen = preview.BestCandidates[0].RawValue;
        var other = preview.Inverse.First(item => item.SimpleSelectable && !item.IsBest).RawValue;
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true,
            query, preview, other, other, true));
        var forged = preview with { BestCandidates = [preview.Inverse[other] with { IsBest = true }] };
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true,
            query, forged, chosen, chosen, true));
    }

    [Fact]
    public void ScenarioTargetSlotOriginalByteAndPermissionChangesInvalidatePreviousPreview()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var (_, preview) = Shared.Value;
        var chosen = preview.BestCandidates[0].RawValue;
        P28RpmQuery[] changed =
        [
            Query(target: "39999"),
            Query(scenario: Scenario("3200001")),
            Query(slot: P28ThresholdLogic.GetSlots()[1].Id),
            Query(originalRaw: 41),
            Query(permissions: [P28ProducerModel.AddEr1Assumption]),
        ];
        foreach (var query in changed)
            Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true,
                query, preview, chosen, chosen, true));
    }

    [Fact]
    public void SaveAssociationRejectsStaleQueryModelPolicyIntervalSnapshotAndPlan()
    {
        var result = Select();
        var selection = result.SelectionReport;
        var plan = result.CompositionPreview.Plan;
        var query = Shared.Value.Query;
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.ValidateSelectionAgainstPlan(Query(target: "39999"), selection, plan));
        var otherPlan = P28ChecksumPreservingEditor.CreateSyntheticPreview(query.Slot.Id, selection.ChosenRaw - 1).Plan;
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.ValidateSelectionAgainstPlan(query, selection, otherPlan));
        P28RpmSelectionReport[] edits =
        [
            selection with { PlannerModelId = "different-planner" },
            selection with { ProducerModelId = "different-G" },
            selection with { CompactModelId = "different-F" },
            selection with { PolicyId = "different-policy" },
            selection with { RawPlanDigest = new string('0', 64) },
            selection with { ComposedPlanDigest = new string('0', 64) },
            selection with { TransitionBand = selection.TransitionBand with { LowerInclusive = !selection.TransitionBand.LowerInclusive } },
            selection with { MinimaxError = "0/1" },
            selection with { QuerySnapshotJson = "{}" },
            selection with { ScenarioSnapshotJson = "{}" },
        ];
        foreach (var edit in edits)
            Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.ValidateSelectionAgainstPlan(query, edit, plan));
    }

    [Fact]
    public void ParseRejectsPromotionUnknownDuplicateMissingNullAndOversizedArtifacts()
    {
        var json = Select().SelectionReport.ToJson(false);
        Action<JsonObject>[] edits =
        [
            node => node["formatVersion"] = "99.0",
            node => node["nativeChecksumStatus"] = "valid",
            node => node["physicalRpmAvailable"] = true,
            node => node["hardwareStatus"] = "Measured",
            node => node["queryDigest"] = null,
            node => node.Remove("composedPlanDigest"),
            node => node["arbitraryOffset"] = 32767,
            node => node["confirmedRaw"] = -1,
            node => node["usedAssumptions"] = new JsonArray("allow-all-unknown"),
            node => node["transitionBand"]!["lowerRpm"] = "2/2",
        ];
        foreach (var edit in edits)
        {
            var node = JsonNode.Parse(json)!.AsObject();
            edit(node);
            Assert.ThrowsAny<Exception>(() => P28RpmSelectionReport.Parse(node.ToJsonString()));
        }
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionReport.Parse(json.Replace("\"formatVersion\":\"1.0\"",
            "\"formatVersion\":\"1.0\",\"formatVersion\":\"1.0\"", StringComparison.Ordinal)));
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionReport.Parse("{\"oversized\":\"" + new string('x', 262145) + "\"}"));
    }

    [Fact]
    public void NoPublicSyntheticAdmissionAndNoMissingAcknowledgementOrChangedParentBypass()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var (query, preview) = Shared.Value;
        var raw = preview.BestCandidates[0].RawValue;
        Assert.Throws<ArgumentNullException>(() => P28RpmSelectionBridge.UseCandidate(baseline, profile, binding, true,
            query, preview, raw, raw, true, null!));
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, false,
            query, preview, raw, raw, true));
        var changed = baseline.CreateModifiedCopy([new BytePatch(0x7100, new byte[] { 1 })]);
        Assert.Throws<InvalidDataException>(() => P28RpmSelectionBridge.UseSyntheticCandidate(changed, profile, binding, true,
            query, preview, raw, raw, true));
    }

    [Fact]
    public void FileReaderBoundsBytesBeforeParsingAndRejectsMalformedUtf8()
    {
        var path = Path.Combine(Path.GetTempPath(), $"rpm-selection-{Guid.NewGuid():N}.json");
        try
        {
            var report = Select().SelectionReport;
            File.WriteAllText(path, report.ToJson());
            Assert.Equal(report.ComputeDigest(), P28RpmSelectionReport.Load(path).ComputeDigest());
            File.WriteAllBytes(path, new byte[262145]);
            Assert.Throws<InvalidDataException>(() => P28RpmSelectionReport.Load(path));
            File.WriteAllBytes(path, new byte[] { 0xff, 0xff });
            Assert.Throws<System.Text.DecoderFallbackException>(() => P28RpmSelectionReport.Load(path));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void CancelledJobsCannotReturnSelectionOrValidateSaveAssociation()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var (query, preview) = Shared.Value;
        var raw = preview.BestCandidates[0].RawValue;
        var token = new CancellationToken(canceled: true);
        Assert.Throws<OperationCanceledException>(() => P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true,
            query, preview, raw, raw, true, token));
        var selected = Select();
        Assert.Throws<OperationCanceledException>(() => P28RpmSelectionBridge.ValidateSelectionAgainstPlan(query,
            selected.SelectionReport, selected.CompositionPreview.Plan, token));
    }

    private static P28RpmSelectionResult Select()
    {
        var (baseline, profile, binding) = P28ChecksumPreservingDefinitions.SyntheticFixture();
        var (query, preview) = Shared.Value;
        var chosen = preview.BestCandidates[0].RawValue;
        return P28RpmSelectionBridge.UseSyntheticCandidate(baseline, profile, binding, true, query, preview, chosen, chosen, true);
    }

    private static P28RpmQuery Query(string target = "40000", P28RpmScenario? scenario = null, string? slot = null,
        byte originalRaw = 40, IReadOnlyList<string>? permissions = null) => P28RpmQuery.Create(scenario ?? Scenario(),
            slot ?? P28ThresholdLogic.GetSlots()[0].Id, originalRaw, target, "Invented mathematical query, not Honda hardware",
            permissions ?? [P28ProducerModel.AddEr1Assumption, P28RpmPlanner.AddEr3Assumption]);

    private static P28RpmScenario Scenario(string clock = "3200000")
    {
        static object Quantity(string numerator, string unit) => new
        {
            numerator,
            denominator = "1",
            unit,
            provenance = "Invented explicit test scenario, not a measured Honda configuration",
            evidence = "analyst-supplied",
        };
        return P28RpmScenario.Parse(JsonSerializer.Serialize(new
        {
            formatVersion = 1,
            scope = "uniform-normal-intervals",
            quantities = new
            {
                clockHz = Quantity(clock, "Hz"),
                timerClockDivisor = Quantity("32", "1"),
                eventsPerCrankRev = Quantity("1", "events/crank-revolution"),
                eventsPerSample = Quantity("1", "events/sample"),
                rpm = Quantity("3000", "crank-revolutions/minute"),
            },
        }));
    }
}
