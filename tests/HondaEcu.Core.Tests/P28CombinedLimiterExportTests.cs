using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28CombinedLimiterExportTests
{
    internal static P28CombinedLimiterSettings Settings(int mask = 7) => new((mask & 1) != 0 ? new(901, 931) : null,
        (mask & 2) != 0 ? new(256, 701) : null, (mask & 4) != 0 ? new(260, 705) : null);
    internal static P28CombinedLimiterPreview Preview(P28CombinedLimiterSettings? settings = null)
    {
        var f = P28AdaptiveBaseExportTests.Fixture(); var s = settings ?? Settings();
        var (b, c, comp) = P28CombinedLimiterEditor.Compose(f.Image, s); var diff = P28FixedLimiterEditor.Diff(f.Image, c);
        var p = new P28CombinedLimiterPlan(1, P28CombinedLimiterEditor.Purpose, P28CombinedLimiterEditor.ContractId,
            f.Image.Hash, 32768, f.Profile.Id, P28VtecInspector.ComputeProfileDigest(f.Profile), P28RawThresholdEditor.ComputeBindingDigest(f.Binding),
            P28CombinedLimiterEditor.Describe(f.Image, s), "invented-not-authority", new string('a', 64), "invented", "invented bounded scope",
            P28CombinedLimiterEditor.EditAudit, comp, 0, P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash, diff,
            diff.Length == 0, P28CombinedLimiterEditor.Scope, P28NativeChecksumArithmetic.Contract.Id, false, P28AdaptiveBaseEditor.Readiness);
        return new(f.Image, f.Profile, f.Binding, null!, b, c, p);
    }
    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    [InlineData(6)]
    [InlineData(7)]
    public void AllSelectionsHaveExactDisjointFootprintsAndOneCompensation(int mask)
    {
        var p = Preview(Settings(mask)); var plan = p.Plan; var before = p.Original.ToArray();
        Assert.Equal(plan.ToJson(false), P28CombinedLimiterPlan.Parse(plan.ToJson()).ToJson(false));
        Assert.Equal(new[] { "fixed", "bank0", "bank1" }, plan.Groups.Select(g => g.Id));
        for (var i = 0; i < 3; i++) Assert.Equal((mask & (1 << i)) != 0, plan.Groups[i].Requested);
        var allowed = P28CombinedLimiterEditor.WordBytes(plan.Groups.Where(g => g.Requested)).Select(d => d.Offset).Append(0x7FFF).ToHashSet();
        for (var i = 0; i < before.Length; i++) if (!allowed.Contains(i)) Assert.Equal(before[i], p.Output.Bytes.Span[i]);
        Assert.InRange(plan.ExpectedDiff.Count, 1, 13); Assert.Equal(0, P28NativeChecksumArithmetic.Calculate(p.Output).ComputedResult);
        Assert.Equal(before, p.Original.ToArray());
        Assert.Equal(unchecked((byte)(plan.Compensation.OldByte - plan.ResidueB)), plan.Compensation.NewByte);
        foreach (var d in plan.Groups.SelectMany(g => g.DomainChecks)) Assert.Equal(65536, d.CheckedInputs);
    }
    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(4)]
    public void SingleGroupFirmwareMatchesExistingMechanism(int mask)
    {
        var s = Settings(mask); var p = Preview(s);
        var old = mask == 1 ? P28FixedLimiterEditor.ComposeOperands(p.Original, s.Fixed!, 0x7FFF).C :
            P28AdaptiveBaseEditor.Compose(p.Original, new(mask == 2 ? 0 : 1,
                (s.Bank0 ?? s.Bank1)!.BaseCutRaw, (s.Bank0 ?? s.Bank1)!.BaseResumeRaw)).C;
        Assert.Equal(old.ToArray(), p.Output.ToArray());
    }
    [Fact]
    public void ExplicitNoopGroupDoesNotSynchronizeOrGrantExtraBytes()
    {
        var f = P28AdaptiveBaseExportTests.Fixture(); var same = P28FixedLimiterEditor.ReadPair(f.Image);
        var p = Preview(new(same, new(256, 701), null)).Plan;
        Assert.True(p.Groups[0].Requested); Assert.False(p.Groups[0].EffectivelyChanged); Assert.False(p.Groups[2].Requested);
        Assert.DoesNotContain(p.ExpectedDiff, d => P28FixedLimiterEditor.Footprint.Contains(d.Offset) || P28AdaptiveBaseEditor.Footprint(1).Contains(d.Offset));
        var noop = Preview(new(same, new(255, 700), new(255, 700)));
        Assert.True(noop.Plan.IsNoOp); Assert.Empty(noop.Plan.ExpectedDiff); Assert.Equal(noop.Original.ToArray(), noop.Output.ToArray());
        Assert.Throws<ArgumentException>(() => Preview(new(null, null, null)));
    }
    [Fact]
    public void CrossGroupCarryAndCancellationUseBytesNotWordDeltas()
    {
        // bank0 00FF->0100 contributes +2; bank1 00FF->00FD contributes -2.
        var p = Preview(new(null, new(256, 700), new(253, 700)));
        Assert.Equal(0, p.Plan.ResidueB); Assert.Equal(p.Plan.Compensation.OldByte, p.Plan.Compensation.NewByte);
        Assert.Equal(3, p.Plan.ExpectedDiff.Count); Assert.Equal(p.Intermediate.ToArray(), p.Output.ToArray());
    }
    [Fact]
    public void MaximumThirteenByteDiffStillProtectsEveryInterveningByte()
    {
        var p = Preview(new(new(1023, 1279), new(512, 1024), new(768, 1280)));
        Assert.Equal(13, p.Plan.ExpectedDiff.Count);
        foreach (var offset in new[] { 0x1969, 0x6493, 0x6497, 0x6499, 0x649D, 0x649F, 0x64A3, 0x64A5, 0x64A9, 0x64AA, 0x60FB })
            Assert.Equal(p.Original.Bytes.Span[offset], p.Output.Bytes.Span[offset]);
    }
    [Theory]
    [InlineData(0, 2)]
    [InlineData(2, 2)]
    [InlineData(3, 2)]
    [InlineData(1, 65535)]
    [InlineData(-1, 3)]
    [InlineData(65535, 65536)]
    public void EveryRequestedGroupReusesPairPolicy(int cut, int resume)
    {
        Assert.Throws<ArgumentException>(() => Preview(new(new(cut, resume), null, null)));
        Assert.Throws<ArgumentException>(() => Preview(new(null, new(cut, resume), null)));
        Assert.Throws<ArgumentException>(() => Preview(new(null, null, new(cut, resume))));
    }
    [Fact]
    public void DomainPolicyIsPerRequestedBankNotCrossGroupOrdering()
    {
        Assert.Throws<ArgumentException>(() => Preview(new(null, new(65000, 65534), null)));
        Assert.Throws<ArgumentException>(() => Preview(new(null, null, new(65000, 65534))));
        Assert.False(Preview(new(new(1, 2), new(256, 701), new(260, 705))).Plan.IsNoOp);
    }
    internal const string ValidSettings = """
        {"formatVersion":1,"purpose":"explicit-limiter-group-selection","fixed":{"cutRaw":901,"resumeRaw":931},"bank0":{"baseCutRaw":256,"baseResumeRaw":701},"bank1":null}
        """;
    [Fact]
    public void SettingsAreClosedExplicitAndOrderIndependent()
    {
        var s = P28CombinedLimiterSettings.Parse(ValidSettings);
        var reordered = """{"bank1":null,"bank0":{"baseResumeRaw":701,"baseCutRaw":256},"fixed":{"resumeRaw":931,"cutRaw":901},"purpose":"explicit-limiter-group-selection","formatVersion":1}""";
        Assert.Equal(Preview(s).Plan.ToJson(false), Preview(P28CombinedLimiterSettings.Parse(reordered)).Plan.ToJson(false));
        foreach (var json in new[] {
            ValidSettings.Replace("901", "901.0"), ValidSettings.Replace("901", "9.01e2"), ValidSettings.Replace("901", "\"901\""),
            ValidSettings.Replace("901", "-1"), ValidSettings.Replace("901", "999999999999999"), ValidSettings.Replace("\"bank1\":null", "\"bank1\":null,\"bank1\":null"),
            ValidSettings.Replace(",\"bank1\":null", ""), ValidSettings.Replace("\"cutRaw\":901,", ""), ValidSettings.Replace("\"bank1\":null", "\"bank2\":null"),
            ValidSettings.Replace("\"bank1\":null", "\"bank1\":{}"), ValidSettings.Replace("\"cutRaw\":901", "\"cutRaw\":901,\"offset\":1") })
            Assert.ThrowsAny<Exception>(() => P28CombinedLimiterSettings.Parse(json));
    }
    [Fact]
    public void PlanRefusesForgedMappingsNoopFlagsDomainsAndMixedTypes()
    {
        var p = Preview().Plan;
        foreach (var edit in new Action<JsonNode>[] {
            n=>n["unknown"]=0, n=>n.AsObject().Remove("locationScope"), n=>n["contractId"]=P28AdaptiveBaseEditor.ContractId,
            n=>n["groups"]![1]!["id"]="bank1", n=>n["groups"]![0]!["requested"]=false, n=>n["groups"]![0]!["effectivelyChanged"]=false,
            n=>n["groups"]![0]!["fixedOperands"]![0]!["offset"]=0x1969,
            n=>n["groups"]![1]!["adaptiveWords"]![0]!["offset"]=0x64A9,
            n=>n["groups"]![1]!["adaptiveWords"]![0]!["newBytes"]![0]=7,
            n=>n["groups"]![2]!["domainChecks"]![0]!["checkedInputs"]=1,
            n=>n["groups"]![2]!["domainChecks"]![0]!["maximumCutTarget"]=0,
            n=>n["compensation"]!["offset"]=0x7000, n=>n["residueB"]=0, n=>n["residueC"]=1,
            n=>n["physicalRpmAvailable"]=true, n=>n["isNoOp"]=true,
            n=>n["expectedDiff"]!.AsArray().Add(new JsonObject { ["offset"]=0x6200,["oldByte"]=0,["newByte"]=1 }) })
        { var n = JsonNode.Parse(p.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28CombinedLimiterPlan.Parse(n.ToJsonString())); }
        Assert.ThrowsAny<Exception>(() => P28AdaptiveBasePlan.Parse(p.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28FixedLimiterPlan.Parse(p.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28ChecksumPreservingPlan.Parse(p.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterPlan.Parse(P28AdaptiveBaseExportTests.Plan().ToJson()));
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterPlan.Parse(p.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1, \"formatVersion\": 1", StringComparison.Ordinal)));
    }
    [Fact]
    public void CorpusCoversBothInputsIndependentInhibitAndUnreseededSwitches()
    {
        var p = Preview(); var corpus = P28CombinedLimiterCorpus.Create(p.Plan);
        Assert.All(corpus, s => Assert.InRange(s.Scenario.Calls.Count, 1, 64));
        Assert.Equal(corpus.Count, corpus.Select(s => s.Id).Distinct().Count());
        foreach (var prior in new[] { 0, 32 }) foreach (var inhibit in new[] { 0, 128 }) foreach (var context in new[] { 1, 2, 3 })
                    Assert.Contains(corpus, s => s.Id == $"fixed-inputs{context}-prior{prior}-inhibit{inhibit}");
        var scenario = corpus.Single(s => s.Id == "cross-context-reverseFalse-prior0-inhibit0").Scenario;
        Assert.True(scenario.Calls[0].Reset214); Assert.All(scenario.Calls.Skip(1), c => Assert.False(c.Reset214 || c.Reset217));
        var a = new P28AdaptiveModel(p.Original.Bytes.Span, scenario.InitialState); var c = new P28AdaptiveModel(p.Output.Bytes.Span, scenario.InitialState);
        var firstA = a.Step(scenario.Calls[0]); var firstC = c.Step(scenario.Calls[0]);
        Assert.NotEqual(firstA.AfterProducer.Limiter.RamCut, firstC.AfterProducer.Limiter.RamCut);
        a.Step(scenario.Calls[1]); c.Step(scenario.Calls[1]);
        var bankA = a.Step(scenario.Calls[2]); var bankC = c.Step(scenario.Calls[2]);
        Assert.Equal(1, bankC.Bank); Assert.Equal("TimerHold", bankC.Path);
        Assert.Equal(firstA.AfterProducer.Limiter.RamCut, bankA.AfterProducer.Limiter.RamCut);
        Assert.Equal(firstC.AfterProducer.Limiter.RamCut, bankC.AfterProducer.Limiter.RamCut);
    }
    [Fact]
    public async Task ForgedCapabilityMissingRunnerAndCancellationNeverAuthorizeSave()
    {
        var p = Preview(); var plan = p.Plan; ((IList<byte>)plan.Groups[1].AdaptiveWords[0].NewBytes)[0] = 99;
        Assert.Equal(0, p.Plan.Groups[1].AdaptiveWords[0].NewBytes[0]);
        var e = new P28CombinedLimiterEvidence("0.8.0", "invented", [], p.Plan.Digest(), P28CombinedLimiterCorpus.Id, [], [], [], [], true, true, true);
        var token = new P28VerifiedCombinedLimiterExport(p, e);
        Assert.Empty(typeof(P28VerifiedCombinedLimiterExport).GetConstructors());
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedCombinedLimiterExport>("{\"pass\":true}"));
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterExecution.RequireEvidence(p, e));
        await Assert.ThrowsAsync<InvalidDataException>(() => P28CombinedLimiterExecution.ValidateAsync(p, "missing"));
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28CombinedLimiterExecution.ValidateAsync(p, "missing", cancellationToken: cancellation.Token));
        Assert.ThrowsAny<OperationCanceledException>(() => P28CombinedLimiterWriter.Save(token, "unused.bin", "unused-plan.json", "unused-receipt.json", cancellationToken: cancellation.Token));
    }
    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    [InlineData(6)]
    [InlineData(7)]
    public void IndependentModelControlsAndWitnessCoverageAreNotNativeAuthority(int mask)
    {
        var p = Preview(Settings(mask)); var scenarios = P28CombinedLimiterCorpus.Create(p.Plan);
        var runs = new List<P28AdaptiveBaseRun>();
        foreach (var s in scenarios) foreach (var image in new[] { ("A", p.Original), ("B", p.Intermediate), ("C", p.Output) })
            {
                var model = new P28AdaptiveModel(image.Item2.Bytes.Span, s.Scenario.InitialState);
                var outcomes = s.Scenario.Calls.Select(c => P28AdaptiveBaseExecution.Outcome(c, model.Step(c))).ToArray();
                // Invented descriptive model rows ONLY; deliberately no runner identity/capability.
                runs.Add(new(image.Item1, image.Item2.Hash, s.Id, s.Scenario.Digest, 0, outcomes.Length, outcomes.Length, new string('a', 64), outcomes));
            }
        P28CombinedLimiterExecution.Relations(p.Plan, scenarios, runs);
        var witnesses = P28CombinedLimiterExecution.Witnesses(p.Plan, scenarios, runs);
        Assert.Equal(p.Plan.Groups.Count(g => g.EffectivelyChanged), witnesses.Count);
        var changed = runs.ToArray(); var bIndex = Array.FindIndex(changed, r => r.ImageKind == "B");
        changed[bIndex] = changed[bIndex] with { ObservationDigest = new string('b', 64) };
        Assert.Throws<InvalidDataException>(() => P28CombinedLimiterExecution.Relations(p.Plan, scenarios, changed));
        Assert.Throws<InvalidDataException>(() => P28AdaptiveExportBatch.RequireRuns([("A", p.Original), ("B", p.Intermediate), ("C", p.Output)], scenarios, runs)); // missing scratch cases
        var row = runs[0];
        var evidence = new P28CombinedLimiterEvidence("invented", "invented", [], p.Plan.Digest(), P28CombinedLimiterCorpus.Id, [row], [], [], witnesses, true, true, true);
        var token = new P28VerifiedCombinedLimiterExport(p, evidence); var exposed = token.Evidence;
        ((IList<P28AdaptiveBaseRead>)exposed.Runs[0].Outcomes[0].TableReads)[0] = new(0, 0, 0);
        Assert.Equal(row.Outcomes[0].TableReads[0], token.Evidence.Runs[0].Outcomes[0].TableReads[0]);
        var receipt = new P28CombinedLimiterReceipt(1, P28CombinedLimiterReceipt.ReceiptPurpose, p.Plan.Digest(), p.Original.Hash, p.Output.Hash,
            p.Plan.ProfileDigest, p.Plan.BindingDigest, p.Plan.LocationDigest, p.Plan.Groups, p.Plan.ExpectedDiff, evidence,
            P28FixedLimiterReceipt.HistoricalScope, P28AdaptiveBaseEditor.Readiness);
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterWriter.Verify(p.Output, p.Original, p.Profile, p.Binding, p.Location, p.Plan, receipt));
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterReceipt.Parse(receipt.ToJson().Replace("\"formatVersion\":1", "\"formatVersion\":1,\"formatVersion\":1", StringComparison.Ordinal)));
        Assert.ThrowsAny<Exception>(() => P28AdaptiveBaseReceipt.Parse(receipt.ToJson()));
    }
    [Fact]
    public async Task ActualRustCombinedBytesPreserveNativeHandoffButSyntheticMismatchCannotPass()
    {
        var fixture = Preview(); var bytes = fixture.Original.ToArray();
        // Tiny invented LC/store program, NOT the recovered OEM producer.
        new byte[] { 0x03, 0xE1, 0x48 }.CopyTo(bytes, 0x487B);
        new byte[] { 0x60, 0x9B, 0x64, 0x90, 0xA9, 0, 0, 0xD3, 0x24, 0x03, 0xF5, 0x48 }.CopyTo(bytes, 0x48E1);
        bytes[0x1966] = 0x62; bytes[0x1969] = 0x67;
        new byte[] { 0x03, 0x38, 0x1A }.CopyTo(bytes, 0x196C); new byte[] { 0x03, 0x96, 0x55 }.CopyTo(bytes, 0x5585);
        var original = RomImage.FromBytes(bytes); var composition = P28CombinedLimiterEditor.Compose(original, Settings());
        var p = new P28CombinedLimiterPreview(original, fixture.Profile, fixture.Binding, null!, composition.B, composition.C, fixture.Plan);
        var s = P28AdaptiveScenario.Create(P28AdaptiveTests.Initial(), [P28AdaptiveTests.Call(), P28AdaptiveTests.Call(1)], "Invented combined LC and native RAM handoff");
        foreach (var image in new[] { original, composition.B, composition.C })
        {
            var raw = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28AdaptiveValidator.CreateRequest(image, s));
            var report = P28AdaptiveValidator.AnalyzeExportImage(p, image, s, raw);
            Assert.True(report.HasFailure);
            foreach (var sequence in report.Sequences)
            {
                Assert.Equal(2, sequence.Counts.CompletedCalls);
                Assert.Equal(image == original ? 255 : 256, sequence.Checkpoints[0].Actual.GetProperty("stateAfterProducer").GetProperty("limiter").GetProperty("ramCut").GetInt32());
                Assert.Equal(sequence.Checkpoints[0].Actual.GetProperty("stateAfter").GetRawText(), sequence.Checkpoints[1].Actual.GetProperty("stateBefore").GetRawText());
            }
        }
        await Assert.ThrowsAsync<InvalidDataException>(() => P28AdaptiveExportBatch.RunAsync([("A", original), ("B", composition.B), ("C", composition.C)],
            [("synthetic-mismatch", s)], ExecutionTestPaths.RustRunner, (image, scenario, response) => P28AdaptiveValidator.AnalyzeExportImage(p, image, scenario, response),
            (_, _) => { }, true, null, CancellationToken.None));
    }
}
