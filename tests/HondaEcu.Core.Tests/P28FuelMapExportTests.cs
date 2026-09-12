using System.Text.Json;
using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28FuelMapExportTests
{
    internal static P28FuelMapExportPreview Preview(P28FuelMapExportSettings? settings = null, byte[]? source = null)
    {
        var bytes = source ?? Image();
        bytes[0x6000] = 0; bytes[0x6000] = unchecked((byte)-bytes.Sum(value => (int)value));
        var original = RomImage.FromBytes(bytes); var profile = new RomProfile("p28-304", "Invented fuel map",
            "Synthetic arithmetic only", 32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, 32768, original.Hash,
            P28VtecInspector.ComputeProfileDigest(profile));
        settings ??= new([new(0, 0, original.Span[P28FuelMapContract.Map0Origin] + 1)], null);
        var (b, c, compensation) = P28FuelMapExportEditor.Compose(original, settings);
        var diff = P28FixedLimiterEditor.Diff(original, c);
        var plan = new P28FuelMapExportPlan(1, P28FuelMapExportEditor.Purpose, P28FuelMapExportEditor.ContractId,
            original.Hash, original.Size, profile.Id, P28VtecInspector.ComputeProfileDigest(profile),
            P28RawThresholdEditor.ComputeBindingDigest(binding), P28FuelMapExportEditor.Describe(original, settings, b),
            P28FuelMapExportEditor.Immutable(original), "invented-not-authority", new string('a', 64), "invented",
            "invented bounded scope", P28FuelMapExportEditor.EditAudit, compensation, 0,
            P28NativeChecksumArithmetic.Calculate(b).ComputedResult, 0, b.Hash, c.Hash, diff, diff.Length == 0,
            P28FuelMapExportEditor.Scope, P28NativeChecksumArithmetic.Contract.Id, false, P28FuelMapExportEditor.Readiness);
        P28FuelMapExportEditor.Shape(plan);
        return new(original, profile, binding, null!, b, c, plan);
    }

    [Fact]
    public void SettingsAreClosedCanonicalAndPreserveNullVersusEmpty()
    {
        const string json = """{"formatVersion":1,"purpose":"explicit-fuel-map-cell-values","map_0":[{"row":2,"column":3,"rawValue":9},{"row":0,"column":1,"rawValue":8}],"map_1":[]}""";
        var settings = P28FuelMapExportSettings.Parse(json);
        Assert.Equal([(0, 1, 8), (2, 3, 9)], settings.Map0!.Select(cell => (cell.Row, cell.Column, cell.RawValue)));
        Assert.NotNull(settings.Map1); Assert.Empty(settings.Map1!);
        Assert.Null(P28FuelMapExportSettings.Parse(json.Replace("\"map_1\":[]", "\"map_1\":null")).Map1);
        foreach (var invalid in new[]
        {
            json.Replace(",\"map_1\":[]", ""), json.Replace("\"map_1\":[]", "\"map_1\":[],\"map_1\":[]"),
            json.Replace("\"rawValue\":9", "\"rawValue\":9.0"), json.Replace("\"rawValue\":9", "\"rawValue\":256"),
            json.Replace("\"row\":2", "\"row\":20"), json.Replace("{\"row\":0,\"column\":1,\"rawValue\":8}", "{\"row\":2,\"column\":3,\"rawValue\":8}"),
            json.Replace("\"rawValue\":9", "\"rawValue\":9,\"offset\":28763"), json.Replace("\"purpose\":\"explicit-fuel-map-cell-values\"", "\"purpose\":\"percent\"")
        }) Assert.ThrowsAny<Exception>(() => P28FuelMapExportSettings.Parse(invalid));
    }

    [Fact]
    public void AllFourHundredCoordinatesHaveExactRowMajorFootprint()
    {
        var bytes = Image();
        var map0 = Enumerable.Range(0, 200).Select(index => new P28FuelMapCellSetting(index / 10, index % 10,
            bytes[P28FuelMapContract.Map0Origin + index] + 1)).ToArray();
        var map1 = Enumerable.Range(0, 200).Select(index => new P28FuelMapCellSetting(index / 10, index % 10,
            bytes[P28FuelMapContract.Map1Origin + index] + 1)).ToArray();
        var preview = Preview(new(map0, map1), bytes);
        Assert.Equal(400, preview.Plan.Maps.Sum(map => map.RequestedCellCount));
        Assert.Equal(400, preview.Plan.Maps.Sum(map => map.ChangedCellCount));
        Assert.InRange(preview.Plan.ExpectedDiff.Count, 400, 401);
        Assert.Equal(0, P28NativeChecksumArithmetic.Calculate(preview.Output).ComputedResult);
        var allowed = Enumerable.Range(P28FuelMapContract.Map0Origin, 200)
            .Concat(Enumerable.Range(P28FuelMapContract.Map1Origin, 200)).Append(0x7FFF).ToHashSet();
        for (var offset = 0; offset < 32768; offset++) if (!allowed.Contains(offset))
                Assert.Equal(preview.Original.Span[offset], preview.Output.Span[offset]);
        foreach (var map in preview.Plan.Maps)
            for (var index = 0; index < 200; index++)
                Assert.Equal(P28FuelMapContract.CellOffset(map.MapId, index / 10, index % 10), map.Cells[index].Offset);
    }

    [Fact]
    public void FullFiniteDomainUsesWideSequentialArithmeticAndSentinel()
    {
        var bytes = Image(); var map = P28FuelMapContract.Map("map_0");
        for (var index = 0; index < 200; index++) bytes[map.Origin + index] = (byte)(index % 2 == 0 ? 0 : 255);
        for (var column = 0; column < 10; column++) bytes[map.MetadataOrigin + column] = 255;
        bytes[0x6000] = 0; bytes[0x6000] = unchecked((byte)-bytes.Sum(value => (int)value));
        var image = RomImage.FromBytes(bytes); var audit = P28FuelMapExportEditor.AuditDomain(image, image, map);
        Assert.Equal(65536, audit.CheckedInputPairs); Assert.Equal(65025, audit.MaximumScaledCell);
        Assert.True(audit.MaximumInterpolationProduct > int.MaxValue);
        Assert.True(audit.SequentialFixedPointVerified); Assert.True(audit.WideIntermediatesVerified); Assert.True(audit.Sentinel256Verified);
        Assert.Equal(65536, audit.EqualResults); Assert.Equal(0, audit.ChangedResults);
        var projection = P28FuelMapModel.ProjectNumeric(image.Span, "map_0", 255, 255);
        Assert.Equal(18, projection.RpmIndex); Assert.Equal(8, projection.LoadIndex);
    }

    [Fact]
    public void MeaningfulZeroResidueCompositionDoesNotInventCompensationDiff()
    {
        var preview = Preview(new([new(0, 0, 2)], [new(0, 0, 0)]));
        Assert.Equal(0, preview.Plan.ResidueB); Assert.Equal(0, preview.Plan.ResidueC);
        Assert.Equal(preview.Plan.Compensation.OldByte, preview.Plan.Compensation.NewByte);
        Assert.Equal(2, preview.Plan.ExpectedDiff.Count); Assert.Equal(preview.Intermediate.ToArray(), preview.Output.ToArray());
        Assert.All(preview.Plan.ExpectedDiff, diff => Assert.Contains(diff.Offset,
            new[] { P28FuelMapContract.Map0Origin, P28FuelMapContract.Map1Origin }));
    }

    [Fact]
    public async Task ExplicitEmptySelectionIsRequestedNoOpButCannotBecomeCapability()
    {
        var preview = Preview(new([], null));
        Assert.True(preview.Plan.Maps[0].Requested); Assert.False(preview.Plan.Maps[0].EffectivelyChanged);
        Assert.False(preview.Plan.Maps[1].Requested); Assert.True(preview.Plan.IsNoOp); Assert.Empty(preview.Plan.ExpectedDiff);
        Assert.Empty(typeof(P28VerifiedFuelMapExport).GetConstructors());
        using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => P28FuelMapExportExecution.ValidateAsync(preview, "missing", cancellationToken: cancellation.Token));
    }

    [Fact]
    public void ForgedPlanOffsetsDomainsResiduesAndPolicyAreRejected()
    {
        var plan = Preview().Plan;
        foreach (var edit in new Action<JsonNode>[]
        {
            node => node["contractId"] = "raw-patch", node => node["maps"]![0]!["cells"]![0]!["offset"] = 0x7000,
            node => node["maps"]![0]!["cells"]![0]!["multiplierOffset"] = 0x700A,
            node => node["maps"]![0]!["domainAudit"]!["checkedInputPairs"] = 255,
            node => node["maps"]![0]!["requested"] = false, node => node["compensation"]!["offset"] = 0x60FB,
            node => node["residueC"] = 1, node => node["physicalUnitsAvailable"] = true,
            node => node["expectedDiff"]![0]!["offset"] = 0x7014, node => node["isNoOp"] = true
        })
        {
            var node = JsonNode.Parse(plan.ToJson())!; edit(node);
            Assert.ThrowsAny<Exception>(() => P28FuelMapExportPlan.Parse(node.ToJsonString()));
        }
        Assert.ThrowsAny<Exception>(() => P28FuelMapExportPlan.Parse(plan.ToJson().Replace("\"formatVersion\": 1", "\"formatVersion\": 1,\"formatVersion\": 1")));
        Assert.Throws<InvalidDataException>(() => P28FuelMapExportPlan.Parse(new string(' ', P28FuelMapExportPlan.MaximumBytes + 1)));
        Assert.Throws<InvalidDataException>(() => P28FuelMapExportReceipt.Parse(new string(' ', P28FuelMapExportReceipt.MaximumJsonBytes + 1)));
    }

    [Fact]
    public void MandatoryCorpusCoversAllRectanglesCellsHistoryAndPerCellEffects()
    {
        var preview = Preview(new([new(0, 0, 9), new(19, 9, 7)], [new(8, 4, 201)]));
        var scenario = P28FuelMapExportCorpus.Create(preview);
        Assert.Equal(P28FuelMapExportCorpus.RectangleCorners, scenario.Calls.Take(P28FuelMapExportCorpus.RectangleCorners).Count());
        Assert.InRange(scenario.Calls.Count, 400, 512); Assert.Null(scenario.Mutation);
        foreach (var mapId in new[] { "map_0", "map_1" })
        {
            var read = new HashSet<int>(); var model = new P28FuelMapModel(preview.Original, scenario.InitialState);
            foreach (var call in scenario.Calls) { var step = model.Step(call); if (call.MapId == mapId) read.UnionWith(step.Operands.CellAddresses); }
            Assert.Equal(200, read.Count(address => address >= P28FuelMapContract.Map(mapId).Origin && address <= P28FuelMapContract.Map(mapId).EndInclusive));
        }
        var runs = new List<P28FuelMapExportRun>();
        foreach (var image in P28FuelMapExportExecution.Images(preview)) foreach (var pattern in new[] { 0, 85, 170 })
            {
                var model = new P28FuelMapModel(image.Image, scenario.InitialState);
                var outcomes = scenario.Calls.Select(call =>
                {
                    var step = model.Step(call); var rpm = call.MapId == "map_0" ? call.RawMap0Rpm : call.RawMap1Rpm;
                    var position = call.MapId == "map_0" ? step.Map0Rpm : step.Map1Rpm;
                    return new P28FuelMapExportOutcome(call.Index, call.MapId, call.RawLoad, rpm, step.Load.Index, position.Index,
                        step.Operands.LookupResult, step.Consumer.Output, step.Operands.CellAddresses);
                }).ToArray();
                runs.Add(new(image.Id, image.Image.Hash, scenario.Digest, pattern, outcomes.Length, outcomes.Length,
                    new string('a', 64), P28FixedLimiterExecution.Digest(outcomes), $"control-{pattern}", outcomes));
            }
        P28FuelMapExportExecution.ValidateRelations(runs);
        var effects = P28FuelMapExportExecution.Effects(preview, scenario, runs);
        Assert.Equal(3, effects.Length); Assert.All(effects, effect => Assert.True(effect.CorpusReadCount > 0));
        Assert.All(effects, effect => Assert.Contains(effect.Effect, new[] { "IsolatedLookupEffect", "ReadMaskedByWeightOrSequentialTruncation" }));
        var witnesses = P28FuelMapExportExecution.Witnesses(preview, runs);
        Assert.Equal(preview.Plan.Maps.Count(map => map.DomainAudit.ChangedResults > 0), witnesses.Length);
        var evidence = new P28FuelMapExportEvidence("0.12.0", "invented", [], preview.Plan.Digest(),
            P28FuelMapExportCorpus.Id, scenario.Digest, scenario.Calls.Count, P28FuelMapExportCorpus.RectangleCorners,
            runs, [], effects, witnesses, true, true, true, true);
        var token = new P28VerifiedFuelMapExport(preview, evidence); var exposed = token.Evidence;
        ((IList<P28FuelMapExportOutcome>)exposed.Runs[0].Outcomes)[0] = exposed.Runs[0].Outcomes[0] with { LookupResult = -1 };
        Assert.NotEqual(-1, token.Evidence.Runs[0].Outcomes[0].LookupResult);
        Assert.ThrowsAny<Exception>(() => P28FuelMapExportExecution.RequireEvidence(preview, evidence));
        Assert.ThrowsAny<Exception>(() => JsonSerializer.Deserialize<P28VerifiedFuelMapExport>("{\"nativeValidationComplete\":true}"));
    }

    [Fact, Trait("Category", "RustIntegration")]
    public async Task ActualRustSubprocessRunsInventedProgramReadMultiplyAndStore()
    {
        async Task<JsonElement> Run(int rawCell)
        {
            var program = new int[0x122];
            new[] { 0x90, 0xA8, 0x90, 0x35 }.CopyTo(program, 0);
            program[0x120] = rawCell;
            var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
            {
                protocolVersion = 1,
                operation = "checksumSynthetic",
                images = new[] { new { id = "invented-fuel-cell-times-column-multiplier", rom = program } },
                allowAssumptions = Array.Empty<string>(),
                scratchPatterns = new[] { 85 },
                synthetic = new
                {
                    entryPc = 0,
                    exitPcs = new[] { 4 },
                    allowedCodeRanges = new[] { new[] { 0, 4 } },
                    psw = 0x0100,
                    lrb = 0x41,
                    usp = 0x180,
                    instructionBudget = 8,
                    dataSeeds = new[] { new[] { 0x80, 0x20 }, new[] { 0x81, 1 }, new[] { 0x208, 9 }, new[] { 0x209, 0 } },
                    outputAddresses = new[] { 4, 5 }
                }
            });
            Assert.Equal(SliceRunnerIdentity.CurrentVersion, response.Response.GetProperty("runnerVersion").GetString());
            return response.Response.GetProperty("syntheticResult").Clone();
        }
        var first = await Run(17); var second = await Run(18);
        Assert.True(first.GetProperty("status").GetInt32() == 0, first.ToString());
        Assert.Equal(153, first.GetProperty("trace")[1].GetProperty("accumulator").GetInt32());
        Assert.Equal(162, second.GetProperty("trace")[1].GetProperty("accumulator").GetInt32());
        Assert.Equal(new[] { 0x120, 0x121 }, first.GetProperty("programReads").EnumerateArray().Select(value => value.GetInt32()));
    }

    internal static byte[] Image()
    {
        var bytes = new byte[32768];
        new byte[] { 0, 20, 40, 60, 80, 100, 120, 140, 240, 0 }.CopyTo(bytes, P28FuelMapContract.LoadAxisOrigin);
        Enumerable.Range(0, 19).Select(index => (byte)(index * 10)).Append((byte)0).ToArray().CopyTo(bytes, P28FuelMapContract.Map0RpmAxisOrigin);
        Enumerable.Range(0, 19).Select(index => (byte)(index * 11)).Append((byte)0).ToArray().CopyTo(bytes, P28FuelMapContract.Map1RpmAxisOrigin);
        foreach (var map in P28FuelMapContract.Maps)
        {
            for (var index = 0; index < 200; index++) bytes[map.Origin + index] = (byte)(1 + index % 200);
            for (var column = 0; column < 10; column++) bytes[map.MetadataOrigin + column] = (byte)(column + 1);
        }
        bytes[0x0A0C] = 0x60; bytes[0x0A0D] = 0x14; bytes[0x0A0E] = 0x70;
        bytes[0x0A24] = 0x60; bytes[0x0A25] = 0x28; bytes[0x0A26] = 0x70;
        bytes[0x0A65] = 0x60; bytes[0x0A66] = 0x00; bytes[0x0A67] = 0x70;
        bytes[0x12FC] = 0x98; bytes[0x12FD] = 10; bytes[0x12FE] = 0x99; bytes[0x12FF] = 20;
        bytes[0x130C] = 0x60; bytes[0x130D] = 0x22; bytes[0x130E] = 0x71;
        bytes[0x1323] = 0x60; bytes[0x1324] = 0x50; bytes[0x1325] = 0x70;
        bytes[0x131A] = 0xE9; bytes[0x131B] = 0x27;
        bytes[0x12DF] = 0xC4; bytes[0x12E0] = 0x27; bytes[0x12E1] = 0x09;
        bytes[0x12F9] = 0xC4; bytes[0x12FA] = 0x27; bytes[0x12FB] = 0x19;
        bytes[0x60E5] = 0;
        return bytes;
    }
}
