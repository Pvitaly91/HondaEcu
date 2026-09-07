using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28AdaptiveBaseExportTests
{
    internal static (RomImage Image, RomProfile Profile, P28ExactBaselineBinding Binding) Fixture()
    {
        var b = P28AdaptiveTests.Image();
        void W(int a, int v) { b[a] = (byte)v; b[a + 1] = (byte)(v >> 8); }
        foreach (var a in new[] { 0x6493, 0x649F }) { W(a, 1000); W(a + 2, 700); W(a + 4, 3); }
        foreach (var a in new[] { 0x6499, 0x64A5 }) { W(a, 1000); W(a + 2, 255); W(a + 4, 2); }
        b[0x6000] = unchecked((byte)-b.Sum(x => (int)x));
        var image = RomImage.FromBytes(b);
        var profile = new RomProfile("p28-304", "Invented adaptive arithmetic", "Synthetic, not native authority", 32768, "Synthetic", true, true);
        return (image, profile, new(1, P28CompactModel.ModelId, profile.Id, 32768, image.Hash, P28VtecInspector.ComputeProfileDigest(profile)));
    }
    internal static P28AdaptiveBasePlan Plan(P28AdaptiveBasePair? requested = null)
    {
        var f = Fixture(); var pair = requested ?? new(0, 256, 701);
        var (b, c, comp) = P28AdaptiveBaseEditor.Compose(f.Image, pair);
        var words = P28AdaptiveBaseEditor.Describe(f.Image, pair); var diff = P28FixedLimiterEditor.Diff(f.Image, c);
        return new(1, P28AdaptiveBaseEditor.Purpose, P28AdaptiveBaseEditor.ContractId, f.Image.Hash, 32768, f.Profile.Id,
            P28VtecInspector.ComputeProfileDigest(f.Profile), P28RawThresholdEditor.ComputeBindingDigest(f.Binding), pair, words,
            P28AdaptiveBaseEditor.CheckDomain(words), "invented-not-authority", new string('a', 64), "invented", "invented scope",
            P28AdaptiveBaseEditor.EditAudit, comp, 0, (byte)(b.ToArray().Sum(x => (int)x) % 256), 0, b.Hash, c.Hash, diff,
            diff.Length == 0, P28AdaptiveBaseEditor.Policy, P28AdaptiveBaseEditor.Scope, P28NativeChecksumArithmetic.Contract.Id, false, P28AdaptiveBaseEditor.Readiness);
    }
    private static P28AdaptiveBasePreview Preview(P28AdaptiveBasePlan p)
    {
        var f = Fixture(); var r = P28AdaptiveBaseEditor.Compose(f.Image, p.RequestedPair);
        return new(f.Image, f.Profile, f.Binding, null!, r.B, r.C, p);
    }
    [Theory]
    [InlineData(0, 256, 700, 2, 3)]
    [InlineData(1, 256, 700, 2, 3)]
    [InlineData(0, 255, 701, 1, 2)]
    [InlineData(1, 255, 701, 1, 2)]
    [InlineData(0, 256, 701, 3, 4)]
    [InlineData(1, 256, 701, 3, 4)]
    [InlineData(0, 255, 700, 0, 0)]
    [InlineData(1, 255, 700, 0, 0)]
    [InlineData(0, 510, 700, 0, 2)]
    [InlineData(1, 510, 700, 0, 2)]
    [InlineData(0, 256, 768, 71, 5)]
    [InlineData(1, 256, 768, 71, 5)]
    public void ExactOddProgramWordsCarryAndVariableDiff(int bank, int cut, int resume, int residue, int count)
    {
        var f = Fixture(); var original = f.Image.ToArray(); var p = Plan(new(bank, cut, resume)); var v = Preview(p);
        var ca = bank == 0 ? 0x649B : 0x64A7; var ra = bank == 0 ? 0x6495 : 0x64A1;
        Assert.Equal((byte)cut, v.Output.Bytes.Span[ca]); Assert.Equal((byte)(cut >> 8), v.Output.Bytes.Span[ca + 1]);
        Assert.Equal((byte)resume, v.Output.Bytes.Span[ra]); Assert.Equal((byte)(resume >> 8), v.Output.Bytes.Span[ra + 1]);
        Assert.Equal(residue, v.Intermediate.ToArray().Sum(x => (int)x) % 256); Assert.Equal(0, v.Output.ToArray().Sum(x => (int)x) % 256);
        Assert.Equal(count, p.ExpectedDiff.Count); Assert.Equal(original, f.Image.ToArray());
        for (var i = 0; i < original.Length; i++) if (i != ca && i != ca + 1 && i != ra && i != ra + 1 && i != 0x7FFF) Assert.Equal(original[i], v.Output.Bytes.Span[i]);
        Assert.Equal(p.ToJson(false), P28AdaptiveBasePlan.Parse(p.ToJson()).ToJson(false));
        Assert.Equal(new[] { $"adaptive-bank-{bank}-base-cut", $"adaptive-bank-{bank}-base-resume" }, p.Words.Select(w => w.FieldId));
    }
    [Theory]
    [InlineData(-1, 1, 2)]
    [InlineData(2, 1, 2)]
    [InlineData(0, 0, 2)]
    [InlineData(0, 2, 2)]
    [InlineData(0, 3, 2)]
    [InlineData(0, 1, 65535)]
    [InlineData(0, 1, 65536)]
    [InlineData(0, -1, 2)]
    public void ExplicitBankAndPairPolicy(int bank, int cut, int resume) =>
        Assert.Throws<ArgumentException>(() => P28AdaptiveBaseEditor.Compose(Fixture().Image, new(bank, cut, resume)));
    [Fact]
    public void DomainChecksEnumerateAllInputsWithoutChangingModuloModel()
    {
        var p = Plan(); Assert.Equal(65536, p.Domain.CheckedInputs);
        // At x=65535, invented origin1000: floor(64535*2/65536)=1 and *3=2.
        Assert.Equal(257, p.Domain.MaximumCutTarget); Assert.Equal(703, p.Domain.MaximumResumeTarget); Assert.Equal(445, p.Domain.MinimumTargetGap);
        Assert.Throws<ArgumentException>(() => P28AdaptiveBaseEditor.Compose(Fixture().Image, new(0, 65000, 65534)));
        var f = Fixture(); var b = f.Image.CreateModifiedCopy([new(0x649D, new byte[] { 255, 255 })]);
        Assert.Throws<ArgumentException>(() => P28AdaptiveBaseEditor.Compose(b, new(0, 255, 700))); // ordered bases but crossing targets
        var wrap = P28AdaptiveTests.Image(); wrap[0x649B] = 255; wrap[0x649C] = 255;
        Assert.Equal(0, new P28AdaptiveModel(wrap, P28AdaptiveTests.Initial(65535, 65535)).Step(P28AdaptiveTests.Call() with { Raw00ce = 1004 }).AfterProducer.Limiter.RamCut);
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    public void FullDiffGuardsAllCoefficientsOriginsOtherBankAndFixedWords(int bank)
    {
        var f = Fixture(); var c = P28AdaptiveBaseEditor.Compose(f.Image, new(bank, 256, 701)).C;
        foreach (var offset in new[] { 0x6493, 0x6497, 0x6499, 0x649D, 0x649F, 0x64A3, 0x64A5, 0x64A9, 0x64AA, 0x1967, 0x196A,
            bank == 0 ? 0x64A7 : 0x649B })
            Assert.Throws<InvalidDataException>(() => P28AdaptiveBaseEditor.RequireFootprint(f.Image, c.CreateModifiedCopy([new(offset, new[] { (byte)(c.Bytes.Span[offset] ^ 1) })]), bank));
        Assert.Throws<InvalidDataException>(() => P28AdaptiveBaseEditor.RequireFootprint(f.Image, c.CreateModifiedCopy([new(0x6200, new byte[] { 1, 255 })]), bank));
        var altered = f.Image.CreateModifiedCopy([new(0x487D, new byte[] { 0 })]);
        Assert.Throws<InvalidDataException>(() => P28AdaptiveBaseEditor.MappingGuard(altered));
    }
    [Fact]
    public void ParserRefusesOffsetsBankContextPolicyAndMixedLineage()
    {
        var p = Plan();
        foreach (var edit in new Action<JsonNode>[] {
            n=>n["unknown"]=1, n=>n.AsObject().Remove("bindingDigest"), n=>n["formatVersion"]=2,
            n=>n["requestedPair"]!["bank"]=1, n=>n["words"]![0]!["offset"]=0x64A9,
            n=>n["words"]![0]!["coefficientOffset"]=0x6495, n=>n["words"]![0]!["newBytes"]![0]=7,
            n=>n["domain"]!["maximumCutTarget"]=0, n=>n["domain"]!["checkedInputs"]=1,
            n=>n["purpose"]=P28FixedLimiterEditor.Purpose, n=>n["purpose"]=P28ChecksumPreservingEditor.Purpose,
            n=>n["residueC"]=1, n=>n["physicalRpmAvailable"]=true, n=>n["compensation"]!["offset"]=0x7000 })
        { var n = JsonNode.Parse(p.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28AdaptiveBasePlan.Parse(n.ToJsonString())); }
        Assert.ThrowsAny<Exception>(() => P28FixedLimiterPlan.Parse(p.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28ChecksumPreservingPlan.Parse(p.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28AdaptiveBasePlan.Parse(p.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1, \"formatVersion\": 1", StringComparison.Ordinal)));
    }
    [Fact]
    public void PlanAndCapabilityDoNotExposeMutableAliasesOrInventAuthority()
    {
        var p = Plan(); var v = Preview(p); var copy = v.Plan;
        ((IList<P28AdaptiveBaseWord>)copy.Words)[0] = copy.Words[0] with { NewWord = 99 };
        Assert.Equal(256, v.Plan.Words[0].NewWord);
        var evidence = new P28AdaptiveBaseEvidence("0.8.0", "invented", [], p.Digest(), P28AdaptiveBaseCorpus.Id, [], [], true, true, true, true);
        var token = new P28VerifiedAdaptiveBaseExport(v, evidence);
        Assert.Empty(typeof(P28VerifiedAdaptiveBaseExport).GetConstructors()); Assert.Empty(typeof(P28AdaptiveBasePreview).GetConstructors());
        Assert.Throws<InvalidDataException>(() => P28AdaptiveBaseWriter.Revalidate(token));
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedAdaptiveBaseExport>("{\"pass\":true}"));
        var scenario = P28AdaptiveBaseCorpus.Create(p)[0].Scenario;
        var model = new P28AdaptiveModel(Fixture().Image.Bytes.Span, scenario.InitialState);
        var outcome = P28AdaptiveBaseExecution.Outcome(scenario.Calls[0], model.Step(scenario.Calls[0]));
        var row = new P28AdaptiveBaseRun("A", p.OriginalHash, "invented", scenario.Digest, 0, 1, 1, new string('a', 64), new[] { outcome });
        var fullToken = new P28VerifiedAdaptiveBaseExport(v, evidence with { Runs = new[] { row } });
        Assert.Equal(outcome.Produced, fullToken.Evidence.Runs[0].Outcomes[0].Produced);
        Assert.Equal(outcome.TableReads[0], fullToken.Evidence.Runs[0].Outcomes[0].TableReads[0]);
        var mutable = fullToken.Evidence;
        ((IList<P28AdaptiveBaseRead>)mutable.Runs[0].Outcomes[0].TableReads)[0] = new(0, 0, 0);
        Assert.Equal(outcome.TableReads[0], fullToken.Evidence.Runs[0].Outcomes[0].TableReads[0]);
    }
    [Fact]
    public void CorpusKeepsNativeResetHoldAndSwitchedBankHistoriesSeparate()
    {
        var p = Plan(); var v = Preview(p); var corpus = P28AdaptiveBaseCorpus.Create(p);
        Assert.All(corpus, s => Assert.InRange(s.Scenario.Calls.Count, 1, 64));
        Assert.Contains(corpus, s => s.Id.StartsWith("untouched-ram", StringComparison.Ordinal));
        var scenario = corpus.Single(s => s.Id == "switch-from0-prior0-inhibit0").Scenario;
        var a = new P28AdaptiveModel(Fixture().Image.Bytes.Span, scenario.InitialState);
        var c = new P28AdaptiveModel(v.Output.Bytes.Span, scenario.InitialState);
        var x = a.Step(scenario.Calls[0]); var y = c.Step(scenario.Calls[0]);
        Assert.Equal(255, x.AfterProducer.Limiter.RamCut); Assert.Equal(256, y.AfterProducer.Limiter.RamCut);
        Assert.Contains(y.TableReads, r => r[1] == 0x649B && r[2] == 256);
        x = a.Step(scenario.Calls[1]); y = c.Step(scenario.Calls[1]);
        Assert.Equal("TimerHold", y.Path); Assert.Equal(1, y.Bank);
        Assert.Equal(255, x.AfterProducer.Limiter.RamCut); Assert.Equal(256, y.AfterProducer.Limiter.RamCut);
        Assert.Equal(255, y.TableReads.Single(r => r[1] == 0x64A7)[2]); // old bank1 base read but not stored
        foreach (var s in corpus.Where(s => s.Id.StartsWith("edited-fixed-", StringComparison.Ordinal)))
        {
            var ma = new P28AdaptiveModel(Fixture().Image.Bytes.Span, s.Scenario.InitialState); var mc = new P28AdaptiveModel(v.Output.Bytes.Span, s.Scenario.InitialState);
            foreach (var call in s.Scenario.Calls)
            { var la = ma.Step(call).Limiter; var lc = mc.Step(call).Limiter; Assert.Equal(la.Threshold, lc.Threshold); Assert.Equal(la.OverspeedRequest, lc.OverspeedRequest); Assert.Equal(la.InhibitBranch, lc.InhibitBranch); }
        }
    }
    [Fact]
    public async Task ActualSyntheticSubprocessReadsEditedOddBaseAndRetainsNativeStoresButCannotExport()
    {
        var f = Fixture(); var bytes = f.Image.ToArray();
        // Invented short LC/store program, not a reconstructed producer. It intentionally mismatches M1m.
        new byte[] { 0x03, 0xE1, 0x48 }.CopyTo(bytes, 0x487B);
        new byte[] { 0x60, 0x9B, 0x64, 0x90, 0xA9, 0, 0, 0xD3, 0x24, 0x03, 0xF5, 0x48 }.CopyTo(bytes, 0x48E1);
        new byte[] { 0x03, 0x38, 0x1A }.CopyTo(bytes, 0x1966); new byte[] { 0x03, 0x96, 0x55 }.CopyTo(bytes, 0x5585);
        var original = RomImage.FromBytes(bytes); var changed = original.CreateModifiedCopy([new(0x649B, new byte[] { 0, 1 })]);
        var scenario = P28AdaptiveScenario.Create(P28AdaptiveTests.Initial(), [P28AdaptiveTests.Call(), P28AdaptiveTests.Call(1)], "Invented LC/stateful handoff");
        foreach (var image in new[] { original, changed })
        {
            var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, f.Profile.Id, 32768, image.Hash, P28VtecInspector.ComputeProfileDigest(f.Profile));
            var response = await P28AdaptiveValidator.ExecuteAsync(image, f.Profile, binding, true, ExecutionTestPaths.RustRunner, scenario);
            Assert.True(response.HasFailure);
            Assert.All(response.Sequences, s =>
            {
                Assert.Equal(2, s.Counts.CompletedCalls);
                Assert.Equal(image == original ? 255 : 256, s.Checkpoints[0].Actual.GetProperty("stateAfterProducer").GetProperty("limiter").GetProperty("ramCut").GetInt32());
                Assert.Contains(s.Checkpoints[0].ActualTableReads, r => r[1] == 0x649B);
                Assert.Equal(s.Checkpoints[0].Actual.GetProperty("stateAfter").GetRawText(), s.Checkpoints[1].Actual.GetProperty("stateBefore").GetRawText());
            });
        }
        var preview = Preview(Plan());
        await Assert.ThrowsAsync<InvalidDataException>(() => P28AdaptiveBaseExecution.ValidateAsync(preview, "missing"));
        using var canceled = new CancellationTokenSource(); canceled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28AdaptiveBaseExecution.ValidateAsync(preview, "missing", cancellationToken: canceled.Token));
    }
}
