using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28BasicCalibrationExportTests
{
    internal static P28BasicCalibrationSettings Settings(int mask = 63, int slot = 0) => new(
        (mask & 1) != 0 ? new(P28ThresholdLogic.GetSlots()[slot].Id, 204) : null,
        (mask & 2) != 0 ? new(1023, 1279) : null, (mask & 4) != 0 ? new(512, 1024) : null,
        (mask & 8) != 0 ? new(768, 1280) : null, (mask & 16) != 0 ? Enumerable.Repeat(65534, 7).ToArray() : null,
        (mask & 32) != 0 ? Enumerable.Repeat(65534, 7).ToArray() : null);
    internal static P28BasicCalibrationPreview Preview(P28BasicCalibrationSettings? settings = null)
    {
        // Combine invented metadata fixtures, never OEM programs or private admission.
        var bytes = P28IdleContextsTests.Image(); var limiter = P28AdaptiveBaseExportTests.Fixture().Image;
        foreach (var a in P28FixedLimiterEditor.Footprint.Concat(Enumerable.Range(0x6493, 24))) bytes[a] = limiter.Span[a];
        bytes[0x6000] = 0; bytes[0x6000] = unchecked((byte)-bytes.Sum(b => (int)b));
        var original = RomImage.FromBytes(bytes); var profile = new RomProfile("p28-304", "Invented basic metadata", "Not admission", 32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768, original.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        var s = settings ?? Settings(); var (b, c, comp) = P28BasicCalibrationEditor.Compose(original, s); var diff = P28FixedLimiterEditor.Diff(original, c);
        var p = new P28BasicCalibrationPlan(1, P28BasicCalibrationEditor.Purpose, P28BasicCalibrationEditor.ContractId, original.Hash, original.Size,
            profile.Id, P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), P28BasicCalibrationEditor.Describe(original, s),
            "invented-not-authority", new string('a', 64), "invented", "invented", P28BasicCalibrationEditor.EditAudit, comp, 0,
            P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash, diff, diff.Length == 0,
            P28BasicCalibrationEditor.Scopes, P28NativeChecksumArithmetic.Contract.Id, false, P28IdleTableEditor.Readiness);
        return new(original, profile, binding, null!, b, c, p);
    }
    public static IEnumerable<object[]> Selections => Enumerable.Range(1, 63).Select(n => new object[] { n });
    [Theory, MemberData(nameof(Selections))]
    public void AllSixtyThreeSelectionsHaveExactMappingFootprint(int mask)
    {
        var p = Preview(Settings(mask)); var plan = p.Plan;
        Assert.Equal(plan.ToJson(false), P28BasicCalibrationPlan.Parse(plan.ToJson()).ToJson(false));
        for (var i = 0; i < 6; i++) Assert.Equal((mask & (1 << i)) != 0, plan.Groups[i].Requested);
        var diff = P28BasicCalibrationEditor.FieldBytes(plan.Groups).Where(d => d.OldByte != d.NewByte).Select(d => d.Offset).Append(0x7FFF).ToHashSet();
        for (var i = 0; i < p.Original.Size; i++) if (!diff.Contains(i)) Assert.Equal(p.Original.Span[i], p.Output.Span[i]);
        Assert.InRange(plan.ExpectedDiff.Count, 1, 42); Assert.Equal(0, P28NativeChecksumArithmetic.Calculate(p.Output).ComputedResult);
        Assert.All(P28BasicCalibrationEditor.LimiterGroups(plan).SelectMany(g => g.DomainChecks), d => Assert.Equal(65536, d.CheckedInputs));
        Assert.All(P28BasicCalibrationEditor.IdleGroups(plan).SelectMany(g => g.DomainChecks), d => Assert.Equal(256, d.CheckedInputs));
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    [InlineData(6)]
    [InlineData(7)]
    public void ExactlyOneOfEightMappedSlotsCanChange(int slot)
    {
        var p = Preview(Settings(63, slot)); var v = p.Plan.Groups[0].Vtec!;
        Assert.Equal(P28ThresholdLogic.GetSlots()[slot], v.Slot);
        foreach (var s in P28ThresholdLogic.GetSlots().Where(s => s != v.Slot)) Assert.Equal(p.Original.Span[s.Offset], p.Output.Span[s.Offset]);
        Assert.Equal(42, p.Plan.ExpectedDiff.Count);
    }
    [Fact]
    public void NullAndExplicitNoopDoNotSyncOrPublish()
    {
        var p = Preview(Settings(0)); Assert.True(p.Plan.IsNoOp); Assert.Empty(p.Plan.ExpectedDiff);
        var s = new P28BasicCalibrationSettings(new(P28ThresholdLogic.GetSlots()[0].Id, p.Original.Span[P28ThresholdLogic.GetSlots()[0].Offset]),
            P28FixedLimiterEditor.ReadPair(p.Original), null, null, p.Plan.Groups[4].Idle!.Cells.Select(c => c.OldValue).ToArray(), null);
        var noop = Preview(s); Assert.True(noop.Plan.IsNoOp); Assert.Equal(3, noop.Plan.Groups.Count(g => g.Requested));
        Assert.All(noop.Plan.Groups, g => Assert.False(g.EffectivelyChanged));
        Assert.Throws<ArgumentException>(() => P28CombinedLimiterSettings.Parse("""{"formatVersion":1,"purpose":"explicit-limiter-group-selection","fixed":null,"bank0":null,"bank1":null}"""));
    }
    [Fact]
    public void FamilyOnlyFirmwareMatchesExistingArithmetic()
    {
        foreach (var mask in new[] { 1, 14, 48 })
        {
            var s = Settings(mask); var p = Preview(s); RomImage c;
            if (mask == 14) c = P28CombinedLimiterEditor.Compose(p.Original, s.Limiter).C;
            else if (mask == 48) c = P28IdleTableEditor.Compose(p.Original, s.Idle).C;
            else
            {
                var slot = P28ThresholdLogic.ResolveSlot(s.Vtec!.Slot);
                var b = p.Original.CreateModifiedCopy([new BytePatch(slot.Offset, [(byte)s.Vtec.RawValue])]);
                c = b.CreateModifiedCopy([new BytePatch(0x7FFF, [P28ChecksumPreservingEditor.ComputeCompensation(p.Original.Span[0x7FFF], P28NativeChecksumArithmetic.Calculate(b).ComputedResult)])]);
            }
            Assert.Equal(c.ToArray(), p.Output.ToArray());
        }
    }
    [Fact]
    public void WordCarryAndCrossFamilyCancellationLeaveCompensationUnchanged()
    {
        var p = Preview(new(new(P28ThresholdLogic.GetSlots()[0].Id, 254), null, new(256, 700), null, null, null));
        Assert.Equal(0, p.Plan.ResidueB); Assert.Equal(p.Plan.Compensation.OldByte, p.Plan.Compensation.NewByte);
        Assert.Equal(3, p.Plan.ExpectedDiff.Count); Assert.Equal(p.Intermediate.ToArray(), p.Output.ToArray());
    }
    [Fact]
    public void ClosedSettingsBoundsAndNoImplicitRules()
    {
        const string json = """{"formatVersion":1,"purpose":"explicit-basic-calibration-selection","vtec":null,"fixed":null,"bank0":null,"bank1":null,"baseTable":null,"lateTable":null}""";
        Assert.True(Preview(P28BasicCalibrationSettings.Parse(json)).Plan.IsNoOp);
        foreach (var wrong in new[] { json.Replace(",\"vtec\":null", ""), json.Replace("\"vtec\":null", "\"vtec\":null,\"vtec\":null"),
            json.Replace("\"vtec\":null", "\"vtec\":{\"slot\":\"bad\",\"rawValue\":1}"), json.Replace("\"fixed\":null", "\"fixed\":{\"cutRaw\":1}"),
            json.Replace("\"bank0\":null", "\"bank0\":{\"baseCutRaw\":2,\"baseResumeRaw\":2}"),
            json.Replace("\"baseTable\":null", "\"baseTable\":[1,2,3,4,5,6]"), json.Replace("\"baseTable\":null", "\"baseTable\":[1.0,2,3,4,5,6,7]"),
            json.Replace("\"lateTable\":null", "\"lateTable\":[1e0,2,3,4,5,6,7]"), json.Replace("\"lateTable\":null", "\"offset\":1,\"lateTable\":null") })
            Assert.ThrowsAny<Exception>(() => P28BasicCalibrationSettings.Parse(wrong));
        Assert.Throws<InvalidDataException>(() => P28BasicCalibrationSettings.Parse(new string(' ', 4097)));
        Assert.Throws<InvalidDataException>(() => P28BasicCalibrationPlan.Parse(new string(' ', P28BasicCalibrationPlan.MaximumBytes + 1)));
        Assert.Throws<ArgumentException>(() => new P28BasicCalibrationSettings(new(P28ThresholdLogic.GetSlots()[0].Id, 256), null, null, null, null, null));
    }
    [Fact]
    public void NoOldFormatsOrSerializedCapabilityOrNestedAlias()
    {
        var p = Preview(); var plan = p.Plan;
        Assert.ThrowsAny<Exception>(() => P28IdleTablePlan.Parse(plan.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterPlan.Parse(plan.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28BasicCalibrationPlan.Parse(P28IdleTableExportTests.Preview().Plan.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28BasicCalibrationReceipt.Parse("{\"pass\":true}"));
        Assert.Empty(typeof(P28VerifiedBasicCalibrationExport).GetConstructors());
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedBasicCalibrationExport>("{}"));
        ((IList<byte>)plan.Groups[0].Vtec!.NewBytes)[0] ^= 1;
        Assert.NotEqual(plan.ToJson(false), p.Plan.ToJson(false));
        var values = Enumerable.Repeat(50, 7).ToArray(); var s = new P28BasicCalibrationSettings(null, null, null, null, values, null);
        values[0] = 0; Assert.Equal(50, s.Idle.BaseTable![0]);
        foreach (var mutate in new Action<JsonNode>[] { n => n["formatVersion"] = 2, n => n["physicalRpmAvailable"] = true,
            n => n["groups"]![0]!["vtec"]!["slot"]!["offset"] = 0x1969, n => n["residueC"] = 1, n => n["isNoOp"] = true,
            n => n["groups"]![1]!["requested"] = false, n => n["compensation"]!["offset"] = 0x60FB })
        { var n = JsonNode.Parse(p.Plan.ToJson())!; mutate(n); Assert.ThrowsAny<Exception>(() => P28BasicCalibrationPlan.Parse(n.ToJsonString())); }
    }
    [Fact]
    public async Task RealSubprocessDispatchUsesWholeCombinedImagesAndCannotPromoteInventedProgram()
    {
        var p = Preview(); var request = JsonSerializer.SerializeToElement(P28BasicVtecBatch.Request(p));
        Assert.Equal("vtecThresholdPrefix", request.GetProperty("operation").GetString()); Assert.Empty(request.GetProperty("allowAssumptions").EnumerateArray());
        for (var i = 0; i < 3; i++) Assert.Equal(p.Images[i].Image.ToArray().Select(b => (int)b), request.GetProperty("images")[i].GetProperty("rom").EnumerateArray().Select(v => v.GetInt32()));
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28BasicVtecBatch.Request(p));
        Assert.Equal(SliceRunnerIdentity.CurrentVersion, response.Response.GetProperty("runnerVersion").GetString());
        Assert.Empty(response.Response.GetProperty("compactRows").EnumerateArray()); Assert.Single(response.Response.GetProperty("entryContracts").EnumerateArray());
        Assert.Equal(36864, response.Response.GetProperty("thresholdRows").GetArrayLength());
        Assert.ThrowsAny<Exception>(() => P28BasicVtecBatch.Analyze(p, response));
        var foreign = p.Output.CreateModifiedCopy([new BytePatch(0x6001, [1]), new BytePatch(0x6002, [255])]);
        Assert.Throws<InvalidDataException>(() => p.RequireImage(foreign));
        var limiter = P28BasicCalibrationCorpus.Fixed(p.Plan)[0].Scenario;
        var lr = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28LimiterValidator.CreateRequest(p.Intermediate, limiter));
        Assert.True(P28LimiterValidator.AnalyzeExportImage(p, p.Intermediate, limiter, lr).HasFailure);
        var adaptive = P28BasicCalibrationCorpus.Adaptive(p.Plan)[0].Scenario;
        var ar = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28AdaptiveValidator.CreateRequest(p.Output, adaptive));
        Assert.True(P28AdaptiveValidator.AnalyzeExportImage(p, p.Output, adaptive, ar).HasFailure);
        var idle = P28BasicCalibrationCorpus.Idle(p)[0].Scenario;
        var ir = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28IdleContextsValidator.CreateRequest(p.Output, idle));
        Assert.Contains(P28IdleContextsValidator.AnalyzeImage(p.Output, idle, ir, "C").Sequences.SelectMany(s => s.Checkpoints), c => c.Disposition != "StrictMatch");
        using var ct = new CancellationTokenSource(); ct.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28BasicCalibrationExecution.ValidateAsync(p, "missing", cancellationToken: ct.Token));
    }
    [Fact]
    public void ChangedFamiliesUseEntireExistingCorporaUnchangedFamiliesUseControls()
    {
        var p = Preview(); var unchanged = Preview(Settings(0));
        Assert.Equal(P28CombinedLimiterCorpus.Create(P28BasicCalibrationEditor.LimiterGroups(p.Plan)).Select(s => s.Scenario.Digest), P28BasicCalibrationCorpus.Adaptive(p.Plan).Select(s => s.Scenario.Digest));
        Assert.Equal(P28IdleTableCorpus.Create(p.Original, p.Output, P28BasicCalibrationEditor.IdleGroups(p.Plan)).Select(s => s.Scenario.Digest), P28BasicCalibrationCorpus.Idle(p).Select(s => s.Scenario.Digest));
        Assert.True(P28BasicCalibrationCorpus.Adaptive(unchanged.Plan).Count < P28BasicCalibrationCorpus.Adaptive(p.Plan).Count);
        Assert.Single(P28BasicCalibrationCorpus.Idle(unchanged)); Assert.Equal(3, P28BasicVtecBatch.Codes(false).Length);
    }
    [Fact]
    public void MissingEvidenceSectionsAndNestedAliasNeverBecomeFreshAuthority()
    {
        var p = Preview();
        var e = new P28BasicCalibrationEvidence("invented", "invented", [], p.Plan.Digest(),
            new("vtecThresholdPrefix", P28BasicVtecBatch.FullId, p.Images.Select(i => i.Image.Hash).ToArray(), [new[] { 1, 2, 3 }], 1, 1, []),
            new(P28CombinedLimiterCorpus.Id, [], [], []), new(P28IdleTableCorpus.Id, [], [], []), [], "NotRun", "NotRun");
        var token = new P28VerifiedBasicCalibrationExport(p, e); var exposed = token.Evidence;
        ((IList<int>)exposed.VtecThresholdPrefix.Rows[0])[0] = 99;
        Assert.Equal(1, token.Evidence.VtecThresholdPrefix.Rows[0][0]);
        Assert.ThrowsAny<Exception>(() => P28BasicCalibrationExecution.RequireEvidence(p, e));
        foreach (var name in new[] { "vtecThresholdPrefix", "limiterAdaptive", "idle", "checksum" })
        {
            var n = JsonNode.Parse(P28RawEditJson.Serialize(e, false))!.AsObject(); n.Remove(name);
            Assert.Throws<InvalidDataException>(() => P28RawEditJson.Parse<P28BasicCalibrationEvidence>(n.ToJsonString()));
        }
        var receipt = new P28BasicCalibrationReceipt(1, P28BasicCalibrationReceipt.ReceiptPurpose, p.Plan.ContractId, p.Plan.Digest(),
            p.Original.Hash, p.Output.Hash, p.Plan.LocationDigest, e, P28FixedLimiterReceipt.HistoricalScope, p.Plan.Readiness);
        Assert.ThrowsAny<Exception>(() => P28IdleTableReceipt.Parse(receipt.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterReceipt.Parse(receipt.ToJson()));
        using var ct = new CancellationTokenSource(); ct.Cancel();
        Assert.ThrowsAny<OperationCanceledException>(() => P28BasicCalibrationWriter.Save(token, "unused.dat", "unused-plan.json", "unused-receipt.json", cancellationToken: ct.Token));
    }
    [Fact]
    public void BasicArtifactsUseSharedCancellationRollbackAndFailedReadbackSemantics()
    {
        var root = Path.Combine(Path.GetTempPath(), "honda-basic-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(root);
        try
        {
            var p = Preview(); var bin = Path.Combine(root, "out.dat"); var plan = Path.Combine(root, "plan.json"); var receipt = Path.Combine(root, "receipt.json");
            using var ct = new CancellationTokenSource(); ct.Cancel();
            Assert.ThrowsAny<OperationCanceledException>(() => ResearchOutputGroup.Write(p.Output, p.Plan.ToJson(), "invented", bin, plan, receipt, [], () => { }, _ => true, ct.Token));
            Assert.Empty(Directory.GetFiles(root));
            var blocker = Path.Combine(root, "parent-file"); File.WriteAllText(blocker, "preserve");
            Assert.ThrowsAny<IOException>(() => ResearchOutputGroup.Write(p.Output, p.Plan.ToJson(), "invented", Path.Combine(blocker, "out.dat"), plan, receipt, [], () => { }, _ => true, default));
            Assert.False(File.Exists(plan)); Assert.False(File.Exists(receipt)); Assert.Equal("preserve", File.ReadAllText(blocker));
            Assert.Throws<InvalidDataException>(() => ResearchOutputGroup.Write<bool>(p.Output, p.Plan.ToJson(), "invented", bin, plan, receipt, [], () => { }, _ => throw new InvalidDataException("readback failed"), default));
            Assert.True(File.Exists(bin)); Assert.True(File.Exists(plan)); Assert.True(File.Exists(receipt)); // retained diagnostics, not success
        }
        finally { Directory.Delete(root, true); }
    }
}
