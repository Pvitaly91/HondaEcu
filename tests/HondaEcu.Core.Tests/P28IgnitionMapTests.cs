using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28IgnitionMapTests
{
    [Fact]
    public void AsymmetricGeometryIsRowMajorAndContextOneUsesNativeInputOverride()
    {
        var model = new P28IgnitionMapModel(InventedImage(), new(7, 16, 2, 123, 456, 789, 0, 0, 99));
        var first = model.Step(new(0, "ignition_map_0", 60, 80, 30));
        Assert.Equal(3, first.Load.Index); Assert.Equal(8, first.Map0Rpm.Index); Assert.Equal(3, first.Map1Rpm.Index);
        Assert.Equal(P28IgnitionMapContract.Map0Origin + 8 * 10 + 3, first.Operands.CellAddresses[0]);
        Assert.Equal(Cell(0, 8, 3), first.Operands.LookupResult);

        var second = model.Step(new(1, "ignition_map_1", 100, 150, 20));
        Assert.Equal(P28IgnitionMapContract.Map1Origin, second.SelectedOrigin);
        Assert.Equal(15, second.Map0Rpm.Index);
        Assert.Equal(15, second.Map1Rpm.Index); // 0A35 overrides DATA00C2 with DATA0238 when DATA0227.5 is set.
        Assert.Equal(P28IgnitionMapContract.Map1Origin + 15 * 10 + 5, second.Operands.CellAddresses[0]);
        Assert.Equal(Cell(1, 15, 5), second.Operands.LookupResult);

        var repeated = model.Step(new(2, "ignition_map_0", 60, 80, 30));
        Assert.Equal(first.Operands.LookupResult, repeated.Operands.LookupResult);
        Assert.Equal(second.After, repeated.Before);
    }

    [Fact]
    public void ArithmeticUsesDirectUnsignedCellsAndSequentialDirectionalTruncation()
    {
        Assert.Equal(100, P28IgnitionMapModel.Interpolate(100, 101, 32767));
        Assert.Equal(99, P28IgnitionMapModel.Interpolate(100, 98, 32768));
        var top = P28IgnitionMapModel.Interpolate(11, 18, 21845);
        var bottom = P28IgnitionMapModel.Interpolate(30, 44, 21845);
        Assert.Equal(23, P28IgnitionMapModel.Interpolate(top, bottom, 32768));
        Assert.Equal(127, P28IgnitionMapModel.Consume(255, 128).Output);
        Assert.Equal(255, P28IgnitionMapModel.Consume(255, 0).Output);
    }

    [Fact]
    public void FinalSentinelCoversLastIntervalsWithoutHostClamp()
    {
        var row = new P28IgnitionMapModel(InventedImage(), new(0, 0, 0, 0, 0, 0, 0, 0, 0))
            .Step(new(0, "ignition_map_1", 255, 255, 3));
        Assert.Equal(8, row.Load.Index); Assert.Equal(18, row.Map0Rpm.Index); Assert.Equal(18, row.Map1Rpm.Index);
        Assert.Equal(256, row.Load.UpperKnot); Assert.Equal(61440, row.Load.Fraction);
    }

    [Fact]
    public void MutationIsExactlyOneCodeOwnedUnsignedCell()
    {
        var original = InventedImage(true); var mutation = new P28IgnitionMapMutation("ignition_map_1", 19, 9, 201);
        var child = P28IgnitionMapInspector.Mutate(original, mutation);
        var changed = Enumerable.Range(0, original.Size).Where(i => original.Span[i] != child.Span[i]).ToArray();
        Assert.Equal([P28IgnitionMapContract.Map1Origin + 199], changed);
        Assert.Throws<ArgumentException>(() => P28IgnitionMapInspector.Mutate(original,
            new("ignition_map_1", 19, 9, original.Span[changed[0]])));
        Assert.Throws<ArgumentOutOfRangeException>(() => P28IgnitionMapContract.CellOffset("ignition_map_0", 0, 10));
    }

    [Fact]
    public void ScenarioIsClosedBoundedAndRejectsExpectedOrOffsetInjection()
    {
        var scenario = P28IgnitionMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 0, 0),
            [new(0, "ignition_map_0", 1, 2, 3)], "Invented bounded test.",
            new("ignition_map_0", 0, 0, 4));
        Assert.Equal(scenario.Digest, P28IgnitionMapScenario.Parse(scenario.ToJson()).Digest);
        foreach (var edit in new Action<JsonNode>[]
        {
            node => node["calls"]![0]!["expectedOutput"] = 1,
            node => node["mutation"]!["offset"] = 0x72E4,
            node => node["initialState"]!["ram"] = new JsonObject(),
            node => node["calls"]![0]!["mapId"] = "map_0",
            node => node["calls"]![0]!["index"] = 7,
        })
        {
            var node = JsonNode.Parse(scenario.ToJson())!; edit(node);
            Assert.Throws<InvalidDataException>(() => P28IgnitionMapScenario.Parse(node.ToJsonString()));
        }
    }

    [Fact]
    public void UnknownImageNeverReceivesRevisionSpecificIgnitionData()
    {
        var profile = RomProfile.Load(Path.Combine(ExecutionTestPaths.RepositoryRoot, "definitions", "p28", "p28-304.experimental.json"));
        var report = P28IgnitionMapInspector.Inspect(RomImage.FromBytes(new byte[32768]), profile, null, true);
        Assert.False(report.InterpretationApplied); Assert.Empty(report.Maps); Assert.Empty(report.Axes);
        Assert.False(report.PhysicalRpmAvailable); Assert.Equal("None", report.FirmwareOutput);
    }

    [Fact]
    public void SelectorUpdatesOnlyBitFiveAndPreservesOnceSeededNeighborBits()
    {
        var model = new P28IgnitionMapModel(InventedImage(), new(0, 0, 0, 0, 0, 0, 0x85, 0, 0));
        var high = model.Step(new(0, "ignition_map_1", 1, 2, 3));
        Assert.Equal(0x85, high.AfterInputs.Selector0227 & ~P28IgnitionMapContract.SelectorMask);
        Assert.Equal(0xA5, high.AfterInputs.Selector0227);
        var low = model.Step(new(1, "ignition_map_0", 1, 2, 3));
        Assert.Equal(0x85, low.AfterInputs.Selector0227);
    }

    private static int Cell(int map, int row, int column) => 1 + map * 30 + row * 3 + column;

    internal static RomImage InventedImage(bool guard = false)
    {
        var bytes = new byte[32768];
        new byte[] { 0, 20, 40, 60, 80, 100, 120, 140, 240, 0 }.CopyTo(bytes, P28IgnitionMapContract.LoadAxisOrigin);
        Enumerable.Range(0, 19).Select(i => (byte)(i * 10)).Append((byte)0).ToArray()
            .CopyTo(bytes, P28IgnitionMapContract.Map0RpmAxisOrigin);
        Enumerable.Range(0, 19).Select(i => (byte)(i * 10)).Append((byte)0).ToArray()
            .CopyTo(bytes, P28IgnitionMapContract.Map1RpmAxisOrigin);
        for (var map = 0; map < 2; map++) for (var row = 0; row < 20; row++) for (var column = 0; column < 10; column++)
                    bytes[(map == 0 ? P28IgnitionMapContract.Map0Origin : P28IgnitionMapContract.Map1Origin) + row * 10 + column] =
                        (byte)Cell(map, row, column);
        if (guard)
        {
            bytes[0x0A0C] = 0x60; bytes[0x0A0D] = 0x14; bytes[0x0A0E] = 0x70;
            bytes[0x0A24] = 0x60; bytes[0x0A25] = 0x28; bytes[0x0A26] = 0x70;
            bytes[0x0A50] = 0x60; bytes[0x0A51] = 0x00; bytes[0x0A52] = 0x70;
            bytes[0x0B67] = 0x98; bytes[0x0B68] = 10; bytes[0x0B69] = 0x99; bytes[0x0B6A] = 20;
            bytes[0x0B71] = 0xED; bytes[0x0B72] = 0x27;
            bytes[0x0B7A] = 0x60; bytes[0x0B7B] = 0xE4; bytes[0x0B7C] = 0x72;
            bytes[0x0B91] = 0x60; bytes[0x0B92] = 0xAC; bytes[0x0B93] = 0x73;
            bytes[0x0BAF] = 0xA3; bytes[0x0BB0] = 0x0D; bytes[0x0BB1] = 0x32; bytes[0x0BB2] = 0xE4; bytes[0x0BB3] = 0x59;
            bytes[0x0BD2] = 0xD4; bytes[0x0BD3] = 0x48;
        }
        return RomImage.FromBytes(bytes);
    }
}
