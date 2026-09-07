using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28FixedLimiterExportTests
{
    internal static (RomImage Image, RomProfile Profile, P28ExactBaselineBinding Binding) Fixture(int cut = 255, int resume = 700, byte compensation = 3)
    {
        var bytes = new byte[32768]; bytes[0x1966] = 0x62; bytes[0x1969] = 0x67;
        bytes[0x1967] = (byte)resume; bytes[0x1968] = (byte)(resume >> 8);
        bytes[0x196A] = (byte)cut; bytes[0x196B] = (byte)(cut >> 8); bytes[0x7FFF] = compensation;
        bytes[0x6000] = unchecked((byte)-bytes.Sum(b => (int)b));
        var image = RomImage.FromBytes(bytes);
        var profile = new RomProfile("p28-304", "Invented limiter arithmetic", "No OEM code or native authority", 32768, "Synthetic", true, true);
        return (image, profile, new(1, P28CompactModel.ModelId, profile.Id, 32768, image.Hash, P28VtecInspector.ComputeProfileDigest(profile)));
    }
    internal static P28FixedLimiterPlan Plan(P28FixedLimiterPair? requested = null)
    {
        var f = Fixture(); var pair = requested ?? new(256, 701);
        var (b, c, compensation) = P28FixedLimiterEditor.ComposeOperands(f.Image, pair, 0x7FFF);
        P28FixedLimiterOperand Op(string id, int offset, int old, int value) => new(id, offset, 2, "LittleEndianUnsignedWordImmediate", old, value,
            new byte[] { (byte)old, (byte)(old >> 8) }, new byte[] { (byte)value, (byte)(value >> 8) });
        var diff = P28FixedLimiterEditor.Diff(f.Image, c);
        return new(1, P28FixedLimiterEditor.Purpose, P28FixedLimiterEditor.ContractId, 1, f.Image.Hash, 32768, f.Profile.Id,
            P28VtecInspector.ComputeProfileDigest(f.Profile), P28RawThresholdEditor.ComputeBindingDigest(f.Binding), pair,
            new[] { Op("fixed-context-cut", 0x196A, 255, pair.CutRaw), Op("fixed-context-resume", 0x1967, 700, pair.ResumeRaw) },
            "invented-not-authority", new string('a', 64), "invented-evidence", "Invented scope only", P28FixedLimiterEditor.LocationApplicability,
            compensation, 0, (byte)(b.Bytes.ToArray().Sum(x => (int)x) % 256), 0, b.Hash, c.Hash, diff, diff.Length == 0,
            P28FixedLimiterEditor.PairPolicy, P28FixedLimiterEditor.Scope, P28NativeChecksumArithmetic.Contract.Id, false, P28FixedLimiterEditor.Readiness);
    }
    [Theory]
    [InlineData(256, 700, 2, 3)]
    [InlineData(255, 701, 1, 2)]
    [InlineData(256, 701, 3, 4)]
    [InlineData(255, 700, 0, 0)]
    public void PairEncodingUsesActualByteSumAndVariableDiff(int cut, int resume, int residue, int differences)
    {
        var f = Fixture(); var before = f.Image.ToArray();
        var result = P28FixedLimiterEditor.ComposeOperands(f.Image, new(cut, resume), 0x7FFF);
        Assert.Equal((byte)(cut & 255), result.B.Bytes.Span[0x196A]); Assert.Equal((byte)(cut >> 8), result.B.Bytes.Span[0x196B]);
        Assert.Equal((byte)(resume & 255), result.B.Bytes.Span[0x1967]); Assert.Equal((byte)(resume >> 8), result.B.Bytes.Span[0x1968]);
        Assert.Equal(residue, result.B.Bytes.ToArray().Sum(x => (int)x) % 256);
        Assert.Equal(unchecked((byte)(3 - residue)), result.C.Bytes.Span[0x7FFF]);
        Assert.Equal(0, result.C.Bytes.ToArray().Sum(x => (int)x) % 256);
        Assert.Equal(differences, P28FixedLimiterEditor.Diff(f.Image, result.C).Length);
        Assert.Equal(0x67, result.C.Bytes.Span[0x1969]); Assert.Equal(before, f.Image.ToArray());
        Assert.Equal(Plan(new(cut, resume)).ToJson(false), P28FixedLimiterPlan.Parse(Plan(new(cut, resume)).ToJson()).ToJson(false));
    }
    [Fact]
    public void NontrivialWordChangeCanHaveZeroByteSumAndNoCompensationChange()
    {
        var f = Fixture(255, 700); var result = P28FixedLimiterEditor.ComposeOperands(f.Image, new(510, 700), 0x7FFF);
        Assert.Equal(255, 510 - 255); Assert.Equal(0, result.B.Bytes.ToArray().Sum(x => (int)x) % 256);
        Assert.Equal(3, result.C.Bytes.Span[0x7FFF]); Assert.Equal(2, P28FixedLimiterEditor.Diff(f.Image, result.C).Length);
        Assert.False(Plan(new(510, 700)).IsNoOp);
    }
    [Fact]
    public void CompensationWrapAndHighByteChangeAreNotWordDeltaArithmetic()
    {
        var f = Fixture(255, 700, 0); var r = P28FixedLimiterEditor.ComposeOperands(f.Image, new(256, 700), 0x7FFF);
        Assert.Equal(254, r.C.Bytes.Span[0x7FFF]); Assert.Equal(0, r.C.Bytes.ToArray().Sum(x => (int)x) % 256);
        var high = P28FixedLimiterEditor.ComposeOperands(Fixture(1, 1000).Image, new(257, 1000), 0x7FFF);
        Assert.Equal(1, high.B.Bytes.Span[0x196A]); Assert.Equal(1, high.B.Bytes.Span[0x196B]);
    }
    [Fact]
    public void BothWordCarriesUseAllFourOperandsButNeverTheInterveningOpcode()
    {
        var f = Fixture(255, 767);
        var result = P28FixedLimiterEditor.ComposeOperands(f.Image, new(256, 768), 0x7FFF);
        Assert.Equal(4, result.B.Bytes.ToArray().Sum(b => (int)b) % 256);
        Assert.Equal(255, result.Compensation.NewByte);
        Assert.Equal(new[] { 0x1967, 0x1968, 0x196A, 0x196B, 0x7FFF }, P28FixedLimiterEditor.Diff(f.Image, result.C).Select(d => d.Offset));
        Assert.Equal(0x67, result.C.Bytes.Span[0x1969]);
    }
    [Theory]
    [InlineData(0, 2)]
    [InlineData(2, 2)]
    [InlineData(3, 2)]
    [InlineData(1, 65535)]
    [InlineData(-1, 5)]
    [InlineData(1, 65536)]
    public void PairPolicyNeverClampsSwapsOrAdmitsSentinels(int cut, int resume) =>
        Assert.Throws<ArgumentException>(() => P28FixedLimiterEditor.ComposeOperands(Fixture().Image, new(cut, resume), 0x7FFF));
    [Fact]
    public void FullDiffRejectsOpcodeOrZeroSumExtraChanges()
    {
        var f = Fixture(); var valid = P28FixedLimiterEditor.ComposeOperands(f.Image, new(256, 701), 0x7FFF).C;
        foreach (var image in new[] { valid.CreateModifiedCopy([new(0x1969, new byte[] { 0x66 })]),
            valid.CreateModifiedCopy([new(0x6100, new byte[] { 1, 255 })]) })
            Assert.Throws<InvalidDataException>(() => P28FixedLimiterEditor.RequireFootprint(f.Image, image, 0x7FFF));
        Assert.DoesNotContain(0x1969, P28FixedLimiterEditor.Footprint);
    }
    [Fact]
    public void PlanParserRejectsUnknownMissingDuplicateOffsetsEncodedValuesAndSafetyClaims()
    {
        var p = Plan();
        foreach (var change in new Action<JsonNode>[] {
            n=>n["unknown"]=1, n=>n.AsObject().Remove("bindingDigest"), n=>n["contractVersion"]=2,
            n=>n["operands"]![0]!["offset"]=0x1969, n=>n["operands"]![0]!["newBytes"]![0]=55,
            n=>n["requestedPair"]!["cutRaw"]=0, n=>n["residueC"]=1, n=>n["scope"]="all contexts",
            n=>n["readiness"]="FlashReady", n=>n["physicalRpmAvailable"]=true, n=>n["originalHash"]!["sha256"]="stale",
            n=>n["compensation"]!["offset"]=0x7000, n=>n["compensation"]!["newByte"]=255,
            n=>n["expectedDiff"]=new JsonArray(), n=>n["purpose"]=P28ChecksumPreservingEditor.Purpose })
        { var n = JsonNode.Parse(p.ToJson())!; change(n); Assert.ThrowsAny<Exception>(() => P28FixedLimiterPlan.Parse(n.ToJsonString())); }
        Assert.ThrowsAny<Exception>(() => P28FixedLimiterPlan.Parse(p.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1, \"formatVersion\": 1", StringComparison.Ordinal)));
        Assert.ThrowsAny<Exception>(() => P28FixedLimiterPlan.Parse(p.ToJson().Replace("\"cutRaw\": 256", "\"cutRaw\": 256.5", StringComparison.Ordinal)));
        Assert.ThrowsAny<Exception>(() => P28ChecksumPreservingPlan.Parse(p.ToJson()));
    }
    [Fact]
    public void MandatoryCorpusHasBothPriorStatesContextsInhibitsAndOverflowSafeBoundaries()
    {
        var p = Plan(new(1, 65534)); var s = P28FixedLimiterExecution.LimiterScenarios(p);
        Assert.Equal(16, s.Count); Assert.Equal(new[] { 0, 32 }, s.Select(x => (int)x.Scenario.InitialState.Data0124).Distinct().Order());
        Assert.Equal(new[] { 0, 128 }, s.Select(x => (int)x.Scenario.InitialState.Data012A).Distinct().Order());
        Assert.Contains(0, P28FixedLimiterExecution.Boundaries(p)); Assert.Contains(65535, P28FixedLimiterExecution.Boundaries(p));
        Assert.All(s, x => { Assert.Null(x.Scenario.Mutation); Assert.InRange(x.Scenario.Calls.Count, 1, 256); });
        Assert.Equal(8, P28FixedLimiterExecution.AdaptiveScenarios().Count);
    }
    [Fact]
    public async Task UnknownBaselineOrForgedInternalCapabilityCannotExportAndCollectionsAreDefensive()
    {
        var f = Fixture(); var plan = Plan(); var composed = P28FixedLimiterEditor.ComposeOperands(f.Image, plan.RequestedPair, 0x7FFF);
        var preview = new P28FixedLimiterPreview(f.Image, f.Profile, f.Binding, null!, composed.B, composed.C, plan);
        var exposed = preview.Plan; Assert.IsAssignableFrom<IList<P28FixedLimiterOperand>>(exposed.Operands)[0] = exposed.Operands[0] with { NewWord = 99 };
        Assert.Equal(256, preview.Plan.Operands[0].NewWord);
        var report = new P28FixedLimiterEvidence("0.8.0", "invented", [], plan.Digest(), P28FixedLimiterExecution.CorpusId, [], [], [], true, true, true);
        var token = new P28VerifiedFixedLimiterExport(preview, report);
        Assert.Empty(typeof(P28VerifiedFixedLimiterExport).GetConstructors()); Assert.Empty(typeof(P28FixedLimiterPreview).GetConstructors());
        Assert.Throws<InvalidDataException>(() => P28FixedLimiterWriter.Revalidate(token));
        await Assert.ThrowsAsync<InvalidDataException>(() => P28FixedLimiterExecution.ValidateAsync(preview, "missing-runner"));
        using var c = new CancellationTokenSource(); c.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28FixedLimiterExecution.ValidateAsync(preview, "missing", cancellationToken: c.Token));
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedFixedLimiterExport>("{\"pass\":true}"));
    }
    [Fact]
    public async Task ActualRustSubprocessCannotPromoteInventedProgramOrMalformedResponseToExport()
    {
        var f = Fixture(); var p = Plan(); var composed = P28FixedLimiterEditor.ComposeOperands(f.Image, p.RequestedPair, 0x7FFF);
        var preview = new P28FixedLimiterPreview(f.Image, f.Profile, f.Binding, null!, composed.B, composed.C, p);
        var scenario = P28FixedLimiterExecution.LimiterScenarios(p)[0].Scenario;
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, P28LimiterValidator.CreateRequest(f.Image, scenario));
        var result = P28LimiterValidator.AnalyzeExportImage(preview, f.Image, scenario, response);
        Assert.True(result.HasFailure); Assert.All(result.Sequences, s => Assert.Equal(scenario.Calls.Count - 1, s.Counts.NotRun));
        var n = JsonNode.Parse(response.Response.GetRawText())!; n["limiterSequences"] = new JsonArray();
        Assert.ThrowsAny<Exception>(() => P28LimiterValidator.AnalyzeExportImage(preview, f.Image, scenario, new(JsonSerializer.SerializeToElement(n), "")));
        var checksum = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner,
            P28NativeChecksumVerifier.CreateRequest(new[] { ("A", f.Image), ("B", composed.B), ("C", composed.C) }));
        Assert.Throws<InvalidDataException>(() => P28FixedLimiterExecution.CompareChecksum(new[] { ("A", f.Image), ("B", composed.B), ("C", composed.C) }, checksum));
    }
    [Fact]
    public void SharedWriterNewPathsCancellationRollbackAndReadbackFailure()
    {
        var root = Path.Combine(Path.GetTempPath(), "hondaecu-m1n-writer-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(root);
        try
        {
            var a = Path.Combine(root, "out.dat"); var b = Path.Combine(root, "plan.json"); var c = Path.Combine(root, "receipt.json");
            var image = RomImage.FromBytes(new byte[] { 1, 2, 3 });
            using var canceled = new CancellationTokenSource(); canceled.Cancel();
            Assert.ThrowsAny<OperationCanceledException>(() => ResearchOutputGroup.Write(image, "plan", "receipt", a, b, c, [], () => { }, _ => true, canceled.Token));
            Assert.Empty(Directory.GetFiles(root));
            Assert.Throws<InvalidOperationException>(() => ResearchOutputGroup.Write(image, "plan", "receipt", a, b, a, [], () => { }, _ => true, default));
            Assert.Throws<InvalidDataException>(() => ResearchOutputGroup.Write(image, "plan", "receipt", a, b, c, [], () => throw new InvalidDataException("stale"), _ => true, default));
            Assert.Empty(Directory.GetFiles(root));
            var blocker = Path.Combine(root, "blocker"); File.WriteAllText(blocker, "preserve");
            Assert.ThrowsAny<IOException>(() => ResearchOutputGroup.Write(image, "plan", "receipt", Path.Combine(blocker, "out.dat"), b, c, [], () => { }, _ => true, default));
            Assert.False(File.Exists(b)); Assert.False(File.Exists(c)); Assert.Equal("preserve", File.ReadAllText(blocker));
            Assert.Throws<InvalidDataException>(() => ResearchOutputGroup.Write<bool>(image, "plan", "receipt", a, b, c, [], () => { }, _ => throw new InvalidDataException("readback failure"), default));
            Assert.Equal(new byte[] { 1, 2, 3 }, File.ReadAllBytes(a)); Assert.Equal("plan", File.ReadAllText(b)); Assert.Equal("receipt", File.ReadAllText(c));
            Assert.Throws<IOException>(() => ResearchOutputGroup.Write(image, "plan", "receipt", a, b, c, [], () => { }, _ => true, default));
        }
        finally { Directory.Delete(root, true); }
    }
}
