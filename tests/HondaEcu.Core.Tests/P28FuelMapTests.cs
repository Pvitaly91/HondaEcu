using System.Text.Json.Nodes;
using HondaEcu.Core;

namespace HondaEcu.Core.Tests;

public sealed class P28FuelMapTests
{
    [Fact]
    public void GeometryIsRowMajorAndEachContextOwnsItsRpmAxis()
    {
        var image = InventedImage();
        var state = new P28FuelMapState(7, 16, 2, 123, 456, 789, 0, 255, 99);
        var model = new P28FuelMapModel(image, state);
        var first = model.Step(new(0, "map_0", 60, 80, 30));
        Assert.Equal(3, first.Load.Index);
        Assert.Equal(8, first.Map0Rpm.Index);
        Assert.Equal(3, first.Map1Rpm.Index);
        Assert.Equal(0, first.Load.Fraction);
        Assert.Equal(P28FuelMapContract.Map0Origin + 8 * 10 + 3, first.Operands.CellAddresses[0]);
        Assert.Equal(Cell(0, 8, 3) * 4, first.Operands.LookupResult);

        var second = model.Step(new(1, "map_1", 100, 20, 150));
        Assert.Equal(P28FuelMapContract.Map1Origin, second.SelectedOrigin);
        Assert.Equal(15, second.Map1Rpm.Index);
        Assert.Equal(P28FuelMapContract.Map1Origin + 15 * 10 + 5, second.Operands.CellAddresses[0]);
        Assert.Equal(Cell(1, 15, 5) * 6, second.Operands.LookupResult);

        var repeatedAfterSwitch = model.Step(new(2, "map_0", 60, 80, 30));
        Assert.Equal(first.Operands.LookupResult, repeatedAfterSwitch.Operands.LookupResult);
        Assert.Equal(first.Load.Index, repeatedAfterSwitch.Load.Index);
        Assert.Equal(first.Map0Rpm.Index, repeatedAfterSwitch.Map0Rpm.Index);
        Assert.Equal(second.After, repeatedAfterSwitch.Before);
    }

    [Fact]
    public void FixedPointUsesSequentialDirectionalTruncation()
    {
        Assert.Equal(100, P28FuelMapModel.Interpolate(100, 101, 32767));
        Assert.Equal(99, P28FuelMapModel.Interpolate(100, 98, 32768));
        var top = P28FuelMapModel.Interpolate(11, 18, 21845);
        var bottom = P28FuelMapModel.Interpolate(30, 44, 21845);
        var sequential = P28FuelMapModel.Interpolate(top, bottom, 32768);
        Assert.Equal(23, sequential);
        Assert.NotEqual((int)Math.Floor(((11 * 2d / 3 + 18d / 3) + (30 * 2d / 3 + 44d / 3)) / 2), sequential);
    }

    [Fact]
    public void AxisSentinelCoversFinalIntervalWithoutHostClamp()
    {
        var model = new P28FuelMapModel(InventedImage(), new(0, 0, 0, 0, 0, 0, 0, 1, 0));
        var row = model.Step(new(0, "map_1", 255, 255, 255));
        Assert.Equal(8, row.Load.Index);
        Assert.Equal(18, row.Map0Rpm.Index);
        Assert.Equal(18, row.Map1Rpm.Index);
        Assert.Equal(256, row.Load.UpperKnot);
        Assert.Equal(61440, row.Load.Fraction);
        Assert.InRange(row.Map1Rpm.Fraction, 1, 65535);
    }

    [Fact]
    public void MutationIsExactlyOneCodeOwnedCell()
    {
        var original = InventedImage(withLayoutGuard: true);
        var mutation = new P28FuelMapMutation("map_1", 19, 9, 201);
        var child = P28FuelMapInspector.Mutate(original, mutation);
        var changed = Enumerable.Range(0, original.Size).Where(index => original.Bytes.Span[index] != child.Bytes.Span[index]).ToArray();
        Assert.Equal([P28FuelMapContract.Map1Origin + 199], changed);
        Assert.Equal(201, child.Bytes.Span[changed[0]]);
        Assert.Throws<ArgumentException>(() => P28FuelMapInspector.Mutate(original,
            new("map_1", 19, 9, original.Bytes.Span[P28FuelMapContract.Map1Origin + 199])));
        Assert.Throws<ArgumentOutOfRangeException>(() => P28FuelMapContract.CellOffset("map_0", 20, 0));
    }

    [Fact]
    public void ScenarioRejectsExpectedOutputsArbitraryOffsetsAndMalformedShape()
    {
        var scenario = P28FuelMapScenario.Create(new(0, 0, 0, 0, 0, 0, 0, 1, 0),
            [new(0, "map_0", 1, 2, 3)], "Invented bounded unit test.", new("map_0", 0, 0, 4));
        Assert.Equal(scenario.Digest, P28FuelMapScenario.Parse(scenario.ToJson()).Digest);
        foreach (var edit in new Action<JsonNode>[]
        {
            node => node["calls"]![0]!["expectedOutput"] = 1,
            node => node["mutation"]!["offset"] = 0x7050,
            node => node["initialState"]!["ram"] = new JsonObject(),
            node => node["calls"]![0]!["mapId"] = "map_2",
            node => node["calls"]![0]!["index"] = 7,
        })
        {
            var node = JsonNode.Parse(scenario.ToJson())!; edit(node);
            Assert.Throws<InvalidDataException>(() => P28FuelMapScenario.Parse(node.ToJsonString()));
        }
    }

    [Fact]
    public void UnknownImageNeverReceivesRevisionSpecificMapData()
    {
        var profile = RomProfile.Load(Path.Combine(ExecutionTestPaths.RepositoryRoot, "definitions", "p28", "p28-304.experimental.json"));
        var report = P28FuelMapInspector.Inspect(RomImage.FromBytes(new byte[32768]), profile, null, true);
        Assert.False(report.InterpretationApplied);
        Assert.Empty(report.Maps);
        Assert.Empty(report.Axes);
        Assert.False(report.PhysicalRpmAvailable);
    }

    private static int Cell(int map, int row, int column) => 1 + map * 20 + row * 3 + column;

    private static RomImage InventedImage(bool withLayoutGuard = false)
    {
        var bytes = new byte[32768];
        var load = new byte[] { 0, 20, 40, 60, 80, 100, 120, 140, 240, 0 };
        var rpm0 = Enumerable.Range(0, 19).Select(value => (byte)(value * 20 / 2)).Append((byte)0).ToArray();
        var rpm1 = Enumerable.Range(0, 19).Select(value => (byte)(value * 10)).Append((byte)0).ToArray();
        load.CopyTo(bytes, P28FuelMapContract.LoadAxisOrigin);
        rpm0.CopyTo(bytes, P28FuelMapContract.Map0RpmAxisOrigin);
        rpm1.CopyTo(bytes, P28FuelMapContract.Map1RpmAxisOrigin);
        for (var map = 0; map < 2; map++)
        {
            var definition = P28FuelMapContract.Map($"map_{map}");
            for (var row = 0; row < 20; row++) for (var column = 0; column < 10; column++)
                    bytes[definition.Origin + row * 10 + column] = (byte)Cell(map, row, column);
            for (var column = 0; column < 10; column++) bytes[definition.MetadataOrigin + column] = (byte)(column + 1);
        }
        bytes[0x60E5] = 0;
        if (withLayoutGuard)
        {
            bytes[0x0A0C] = 0x60; bytes[0x0A0D] = 0x14; bytes[0x0A0E] = 0x70;
            bytes[0x0A24] = 0x60; bytes[0x0A25] = 0x28; bytes[0x0A26] = 0x70;
            bytes[0x0A65] = 0x60; bytes[0x0A66] = 0x00; bytes[0x0A67] = 0x70;
            bytes[0x12FC] = 0x98; bytes[0x12FD] = 10; bytes[0x12FE] = 0x99; bytes[0x12FF] = 20;
            bytes[0x130C] = 0x60; bytes[0x130D] = 0x22; bytes[0x130E] = 0x71;
            bytes[0x1323] = 0x60; bytes[0x1324] = 0x50; bytes[0x1325] = 0x70;
            bytes[0x131A] = 0xE9; bytes[0x131B] = 0x27;
            bytes[0x12DF] = 0xC4; bytes[0x12E0] = 0x27; bytes[0x12E1] = 0x09;
            bytes[0x12F9] = 0xC4; bytes[0x12FA] = 0x27; bytes[0x12FB] = 0x19;
        }
        return RomImage.FromBytes(bytes);
    }
}
