using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28IdleTableExportTests
{
    internal static P28IdleTablePreview Preview(P28IdleTableSettings? settings = null, byte[]? bytes = null)
    {
        bytes ??= P28IdleContextsTests.Image(); bytes[0x6000] = 0; bytes[0x6000] = unchecked((byte)-bytes.Sum(x => (int)x));
        var image = RomImage.FromBytes(bytes); var profile = new RomProfile("p28-304", "Invented idle arithmetic", "Synthetic, not admission", 32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768, image.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        settings ??= new([1000, 1150, 1349, 1600, 2000, 2200, 2500], null);
        var (b, c, comp) = P28IdleTableEditor.Compose(image, settings); var diff = P28FixedLimiterEditor.Diff(image, c);
        var p = new P28IdleTablePlan(1, P28IdleTableEditor.Purpose, P28IdleTableEditor.ContractId, image.Hash, image.Size, profile.Id,
            P28VtecInspector.ComputeProfileDigest(profile), P28RawThresholdEditor.ComputeBindingDigest(binding), P28IdleTableEditor.Describe(image, settings),
            "invented-not-authority", new string('a', 64), "invented", "invented bounded scope", P28IdleTableEditor.EditAudit, comp, 0,
            P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash, diff, diff.Length == 0, P28IdleTableEditor.Scope,
            P28NativeChecksumArithmetic.Contract.Id, false, P28IdleTableEditor.Readiness);
        return new(image, profile, binding, null!, b, c, p);
    }
    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void ExplicitSelectionsProtectEveryOtherByte(int mask)
    {
        var p = Preview(new((mask & 1) != 0 ? [1010, 1150, 1349, 1600, 2000, 2200, 2499] : null,
            (mask & 2) != 0 ? [810, 900, 1116, 1300, 1600, 1700, 1900] : null));
        Assert.Equal(p.Plan.ToJson(false), P28IdleTablePlan.Parse(p.Plan.ToJson()).ToJson(false));
        var allowed = P28IdleTableEditor.CellBytes(p.Plan.Tables.Where(t => t.Requested)).Select(d => d.Offset).Append(0x7FFF).ToHashSet();
        for (var i = 0; i < 32768; i++) if (!allowed.Contains(i)) Assert.Equal(p.Original.Bytes.Span[i], p.Output.Bytes.Span[i]);
        Assert.InRange(p.Plan.ExpectedDiff.Count, 0, 29); Assert.Equal(0, P28NativeChecksumArithmetic.Calculate(p.Output).ComputedResult);
        Assert.Equal(mask == 0, p.Plan.IsNoOp);
        Assert.All(p.Plan.Tables.Where(t => t.Requested), t => Assert.Equal(256, Assert.Single(t.DomainChecks).CheckedInputs));
    }
    [Theory]
    [InlineData(0, 0)]
    [InlineData(0, 1)]
    [InlineData(0, 2)]
    [InlineData(0, 3)]
    [InlineData(0, 4)]
    [InlineData(0, 5)]
    [InlineData(0, 6)]
    [InlineData(1, 0)]
    [InlineData(1, 1)]
    [InlineData(1, 2)]
    [InlineData(1, 3)]
    [InlineData(1, 4)]
    [InlineData(1, 5)]
    [InlineData(1, 6)]
    public void AllFourteenWordsUseDisjointUnalignedCodeOwnedOffsets(int table, int cell)
    {
        var original = Preview(new(null, null)); var values = original.Plan.Tables[table].Cells.Select(c => c.OldValue).ToArray(); values[cell]++;
        var p = Preview(new(table == 0 ? values : null, table == 1 ? values : null));
        var offset = (table == 0 ? 0x68CC : 0x68E1) + 3 * cell;
        Assert.Equal(offset, P28IdleTableFields.ValueOffset(table, cell));
        Assert.All(p.Plan.ExpectedDiff, d => Assert.Contains(d.Offset, new[] { offset, offset + 1, 0x7FFF }));
        Assert.Equal(values[cell], P28LimiterInspector.Word(p.Output.Span, offset));
        foreach (var axis in p.Plan.Tables.SelectMany(t => t.Cells).Select(c => c.AxisOffset)) Assert.Equal(p.Original.Span[axis], p.Output.Span[axis]);
    }
    [Fact]
    public void FullMaximumFootprintAndExplicitUnchangedRequestedTable()
    {
        var p = Preview(new([65534, 65534, 65534, 65534, 65534, 65534, 65534], [65534, 65534, 65534, 65534, 65534, 65534, 65534]));
        Assert.Equal(29, p.Plan.ExpectedDiff.Count);
        var noop = Preview(new([1000, 1150, 1333, 1600, 2000, 2200, 2500], null));
        Assert.True(noop.Plan.Tables[0].Requested); Assert.False(noop.Plan.Tables[0].EffectivelyChanged); Assert.True(noop.Plan.IsNoOp); Assert.Empty(noop.Plan.ExpectedDiff);
        var snapshot = p.Plan; ((IList<byte>)snapshot.Tables[0].Cells[0].NewBytes)[0] ^= 1;
        Assert.NotEqual(snapshot.ToJson(false), p.Plan.ToJson(false));
        var array = new[] { 1, 2, 3, 4, 5, 6, 7 }; var settings = new P28IdleTableSettings(array, null); array[0] = 65535; Assert.Equal(1, settings.BaseTable![0]);
    }
    [Theory]
    [InlineData(0)]
    [InlineData(65535)]
    [InlineData(-1)]
    [InlineData(65536)]
    public void PolicyIsExplicitWithoutClampOrRpm(int value) => Assert.Throws<ArgumentException>(() => new P28IdleTableSettings([value, 2, 3, 4, 5, 6, 7], null));
    [Fact]
    public void FullDomainAllowsBothDirectionsPlateausAndExtremes()
    {
        var p = Preview(new([1, 65534, 32768, 32768, 1, 65534, 1], [65534, 1, 1, 65534, 1, 65534, 1]));
        foreach (var t in p.Plan.Tables)
        {
            var d = Assert.Single(t.DomainChecks); Assert.True(d.BoundsAndNodesVerified); Assert.Equal(1, d.Minimum); Assert.Equal(65534, d.Maximum);
            Assert.InRange(d.MaximumProduct, 1, 65533 * 255);
        }
        Assert.Contains("Plateau", p.Plan.Tables[0].DomainChecks[0].SegmentDirections);
        var first = p.Plan.Tables[0].Cells.Select(c => c with { Axis = c.Index == 1 ? 255 : c.Axis }).ToArray();
        Assert.Throws<ArgumentException>(() => P28IdleTableEditor.CheckDomain(first));
    }
    [Fact]
    public void WordCarryAndCrossTableCancellationUseEncodedBytes()
    {
        var bytes = P28IdleContextsTests.Image(); bytes[0x68CC] = 255; bytes[0x68CD] = 0; bytes[0x68E1] = 255; bytes[0x68E2] = 0;
        var p = Preview(new([256, 1150, 1333, 1600, 2000, 2200, 2500], [253, 900, 1100, 1300, 1600, 1700, 1900]), bytes);
        Assert.Equal(0, p.Plan.ResidueB); Assert.Equal(p.Plan.Compensation.OldByte, p.Plan.Compensation.NewByte); Assert.Equal(3, p.Plan.ExpectedDiff.Count);
        Assert.Equal(p.Intermediate.ToArray(), p.Output.ToArray());
    }
    [Fact]
    public void SettingsAreRequiredClosedAndOrderIndependent()
    {
        const string json = """{"formatVersion":1,"purpose":"explicit-idle-table-values","baseTable":[1,2,3,4,5,6,7],"lateTable":null}""";
        var a = P28IdleTableSettings.Parse(json); var b = P28IdleTableSettings.Parse("""{"lateTable":null,"baseTable":[1,2,3,4,5,6,7],"purpose":"explicit-idle-table-values","formatVersion":1}""");
        Assert.Equal(Preview(a).Plan.ToJson(false), Preview(b).Plan.ToJson(false));
        foreach (var wrong in new[] { json.Replace(",\"lateTable\":null", ""), json.Replace("\"lateTable\":null", "\"lateTable\":null,\"lateTable\":null"),
            json.Replace("[1,2,3,4,5,6,7]", "[1,2,3]"), json.Replace("[1,2,3,4,5,6,7]", "[1,2,3,4,5,6,7,8]"),
            json.Replace("[1,2", "[1.0,2"), json.Replace("[1,2", "[1e0,2"), json.Replace("[1,2", "[null,2"), json.Replace("\"lateTable\":null", "\"offset\":26828,\"lateTable\":null") })
            Assert.ThrowsAny<Exception>(() => P28IdleTableSettings.Parse(wrong));
    }
    [Fact]
    public void ForgedSerializedPolicyOffsetsAxesAndResiduesNeverAuthorize()
    {
        var p = Preview().Plan;
        foreach (var edit in new Action<JsonNode>[] { n => n["formatVersion"] = 2, n => n["purpose"] = "pc-only-combined-limiter-checksum-preserving-export",
            n => n["tables"]![0]!["cells"]![0]!["valueOffset"] = 0x68DA, n => n["tables"]![0]!["domainChecks"]![0]!["maximum"] = 1,
            n => n["residueC"] = 1, n => n["compensation"]!["offset"] = 0x60FB, n => n["tables"]![0]!["effectivelyChanged"] = false,
            n => n["isNoOp"] = true, n => n["physicalRpmAvailable"] = true, n => n["outputHash"]!["sha256"] = "Pass" })
        { var n = JsonNode.Parse(p.ToJson())!; edit(n); Assert.ThrowsAny<Exception>(() => P28IdleTablePlan.Parse(n.ToJsonString())); }
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterPlan.Parse(p.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28FixedLimiterPlan.Parse(p.ToJson()));
        Assert.ThrowsAny<Exception>(() => P28IdleTablePlan.Parse(p.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1,\"formatVersion\": 1")));
        Assert.Throws<InvalidDataException>(() => P28IdleTablePlan.Parse(new string(' ', 65537)));
        Assert.Throws<InvalidDataException>(() => P28IdleTableReceipt.Parse(new string(' ', P28IdleTableReceipt.MaximumJsonBytes + 1)));
        Assert.Empty(typeof(P28VerifiedIdleTableExport).GetConstructors());
    }
    [Fact]
    public void CorpusCoversLiveLowLookupLateDomainKnotsAndNativeOwnedHistory()
    {
        var p = Preview(); var corpus = P28IdleTableCorpus.Create(p);
        foreach (var prefix in new[] { "base-retained-domain", "late-domain" }) Assert.Equal(Enumerable.Range(0, 256), corpus.Where(s => s.Id.StartsWith(prefix, StringComparison.Ordinal)).SelectMany(s => s.Scenario.Calls).Select(c => (int)c.RawD9));
        Assert.All(corpus, s => { Assert.InRange(s.Scenario.Calls.Count, 1, 64); Assert.Null(s.Scenario.Mutation); });
        var initial = P28IdleTableCorpus.Initial; var m = new P28IdleContextsModel(p.Intermediate, initial);
        var low = m.Step(new(0, 22, 1500, P28IdleTableCorpus.Selectors(9))); Assert.Contains(low.Lookups, l => l.Table == 0x68CB); Assert.Equal(low.FinalTarget, low.AfterProducer.Target);
        var late = m.Step(new(1, 140, 1340, P28IdleTableCorpus.Selectors(8))); Assert.Equal(low.After, late.Before); Assert.Equal("table-68e0", late.FinalSource);
        Assert.Contains(late.Lookups, l => l.Table == 0x68CB && !l.FinalContribution); Assert.Equal(initial.Raw0274, late.After.Raw0274);
        var current = new P28IdleContextsModel(p.Original, initial).Step(new(0, 140, 1341, P28IdleTableCorpus.Selectors(9)));
        var edited = new P28IdleContextsModel(p.Output, initial).Step(new(0, 140, 1341, P28IdleTableCorpus.Selectors(9)));
        Assert.Equal(8, current.ClampedError); Assert.Equal(8, edited.ClampedError); Assert.NotEqual(current.CurrentBelowTarget, edited.CurrentBelowTarget);
    }
    [Fact]
    public async Task RealSubprocessCannotPromoteToyOrForeignImageToExportEvidence()
    {
        var p = Preview(); var scenario = P28IdleContextsTests.Scenario();
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28IdleContextsValidator.CreateRequest(p.Intermediate, scenario));
        var report = P28IdleTableExecution.AnalyzeCompositionImage(p, p.Intermediate, scenario, response, "B");
        Assert.Contains(report.Sequences.SelectMany(s => s.Checkpoints), c => c.Disposition != "StrictMatch");
        var foreign = p.Intermediate.CreateModifiedCopy([new BytePatch(0x6001, [1]), new BytePatch(0x6002, [255])]);
        Assert.Equal(P28NativeChecksumArithmetic.Calculate(p.Intermediate).ComputedResult, P28NativeChecksumArithmetic.Calculate(foreign).ComputedResult);
        Assert.Throws<InvalidDataException>(() => P28IdleTableExecution.AnalyzeCompositionImage(p, foreign, scenario, response, "B"));
        foreach (var address in new[] { 0x68DA, 0x68F2, 0x68F5, 0x2FD5, 0x2FE3, 0x2FE7, 0x6542, 0x1967, 0x60FB })
        { var image = p.Intermediate.CreateModifiedCopy([new BytePatch(address, [(byte)(p.Intermediate.Span[address] ^ 1)])]); Assert.Throws<InvalidDataException>(() => P28IdleTableExecution.AnalyzeCompositionImage(p, image, scenario, response, "B")); }
        using var ct = new CancellationTokenSource(); ct.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28IdleTableExecution.ValidateAsync(p, "missing", cancellationToken: ct.Token));
        await Assert.ThrowsAnyAsync<Exception>(() => P28IdleTableExecution.ValidateAsync(p, "missing"));
    }
    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void ModelRelationsCellEffectsAndNestedSnapshotsAreNotNativeAuthority(int selection)
    {
        var p = Preview(new((selection & 1) != 0 ? [1000, 1150, 1349, 1600, 2000, 2200, 2484] : null,
            (selection & 2) != 0 ? [816, 900, 1116, 1300, 1600, 1700, 1900] : null));
        var scenarios = P28IdleTableCorpus.Create(p); var runs = new List<P28IdleTableRun>();
        foreach (var s in scenarios) foreach (var image in P28IdleTableExecution.Images(p))
            {
                var model = new P28IdleContextsModel(image.Image, s.Scenario.InitialState); var steps = s.Scenario.Calls.Select(model.Step).ToArray();
                var outcomes = s.Scenario.Calls.Zip(steps).Select(pair => P28IdleTableExecution.Outcome(pair.First, pair.Second)).ToArray();
                // Deliberately invented observation digest, one scratch only, no runner claim.
                runs.Add(new(image.Id, image.Image.Hash, s.Id, s.Scenario.Digest, 0, steps.Length, steps.Length, new string('a', 64),
                    P28FixedLimiterExecution.Digest(steps), P28IdleTableExecution.Controls(steps), outcomes));
            }
        P28IdleTableExecution.Relations(runs); var witnesses = P28IdleTableExecution.Witnesses(p.Plan, runs);
        Assert.Equal(p.Plan.Tables.Count(t => t.EffectivelyChanged), witnesses.Count);
        var effects = P28IdleTableExecution.Effects(p, scenarios, runs);
        Assert.All(p.Plan.Tables.SelectMany(t => t.Cells).Where(c => c.OldValue != c.NewValue), c => Assert.Contains(effects, e => e.FieldId == c.FieldId));
        Assert.Contains(effects, e => e.Effect == "CellNotRead"); Assert.Contains(effects, e => e.Effect == "ZeroWeight");
        if ((selection & 1) != 0) { Assert.Contains(effects, e => e.Effect == "LookupNotExecuted"); Assert.Contains(effects, e => e.Effect == "LateReplacement"); }
        var altered = runs.ToArray(); altered[1] = altered[1] with { ObservationDigest = new string('b', 64) };
        Assert.Throws<InvalidDataException>(() => P28IdleTableExecution.Relations(altered));
        var e = new P28IdleTableEvidence("invented", "invented", [], p.Plan.Digest(), P28IdleTableCorpus.Id, runs, [], witnesses, effects, true, true, true);
        var token = new P28VerifiedIdleTableExport(p, e); var exposed = token.Evidence;
        var row = exposed.Runs.First(r => r.Outcomes.Any(o => o.Lookups.Count > 0)); var outcome = row.Outcomes.First(o => o.Lookups.Count > 0);
        ((IList<P28IdleLookupObservation>)outcome.Lookups)[0] = outcome.Lookups[0] with { Value = 7 };
        Assert.DoesNotContain(token.Evidence.Runs.SelectMany(r => r.Outcomes).SelectMany(o => o.Lookups), l => l.Value == 7);
        Assert.ThrowsAny<Exception>(() => P28IdleTableExecution.RequireEvidence(p, e));
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedIdleTableExport>("{\"pass\":true}"));
        using var ct = new CancellationTokenSource(); ct.Cancel();
        Assert.ThrowsAny<OperationCanceledException>(() => P28IdleTableWriter.Save(token, "unused.bin", "unused-plan.json", "unused-receipt.json", cancellationToken: ct.Token));
        var receipt = new P28IdleTableReceipt(1, P28IdleTableReceipt.ReceiptPurpose, p.Plan.Digest(), p.Original.Hash, p.Output.Hash, p.Plan.ProfileDigest,
            p.Plan.BindingDigest, p.Plan.LocationDigest, p.Plan.Tables, p.Plan.ExpectedDiff, e, P28FixedLimiterReceipt.HistoricalScope, P28IdleTableEditor.Readiness);
        Assert.ThrowsAny<Exception>(() => P28IdleTableWriter.Verify(p.Output, p.Original, p.Profile, p.Binding, p.Location, p.Plan, receipt));
        Assert.ThrowsAny<Exception>(() => P28IdleTableReceipt.Parse(receipt.ToJson().Replace("\"formatVersion\":1", "\"formatVersion\":1,\"formatVersion\":1")));
        Assert.ThrowsAny<Exception>(() => P28CombinedLimiterReceipt.Parse(receipt.ToJson()));
    }
}
