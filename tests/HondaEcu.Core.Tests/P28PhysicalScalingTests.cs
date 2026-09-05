using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28PhysicalScalingTests
{
    [Fact]
    public void NoFileHasNoDefaultsOrNumericalPreview()
    {
        var analysis = P28PhysicalScaling.Analyze(null);
        Assert.False(analysis.PhysicalRpmAvailable);
        Assert.Null(analysis.Preview);
        Assert.Null(analysis.AnalystInputs);
        Assert.Equal("unavailable-symbolic-only", analysis.Status);
    }

    [Fact]
    public void ExplicitRationalUnitsProduceConditionalQuantizationEnvelope()
    {
        var analysis = Analyze(Input());
        Assert.False(analysis.PhysicalRpmAvailable);
        Assert.Equal("conditional-analyst-preview", analysis.Status);
        Assert.Equal("50000/1", analysis.Preview!.TimerHz);
        Assert.Equal("1000/3", analysis.Preview.IdealTicksPerSample);
        Assert.Equal("333", analysis.Preview.FloorTicks);
        Assert.Equal("334", analysis.Preview.CeilingTicks);
        Assert.Equal(new ushort[] { 399, 400 }, analysis.Preview.PossibleT);
        Assert.Equal(5, analysis.AnalystInputs!.Count);
        Assert.Contains(analysis.Assumptions, value => value.Contains("oki.add-er1-a", StringComparison.Ordinal));
    }

    [Fact]
    public void ZeroQuantizedSamplesUseFallbackAndOutOfRangeDoesNotInventWrap()
    {
        var input = Input();
        input["quantities"]!["rpm"]!["numerator"] = "6000000";
        Assert.Contains(ushort.MaxValue, Analyze(input).Preview!.PossibleT);
        input["quantities"]!["rpm"]!["numerator"] = "1";
        Assert.Empty(Analyze(input).Preview!.PossibleT);
    }

    [Fact]
    public void ExactIntegerTicksHaveOneResultAndWrongVersionTypesFailCleanly()
    {
        var input = Input();
        input["quantities"]!["rpm"]!["numerator"] = "1000";
        Assert.Equal(new ushort[] { 1200 }, Analyze(input).Preview!.PossibleT);
        input["formatVersion"] = "1";
        Assert.Throws<InvalidDataException>(() => Analyze(input));
        input["formatVersion"] = null;
        Assert.Throws<InvalidDataException>(() => Analyze(input));
    }

    [Fact]
    public void PhysicalPreviewDoesNotTreatTcErrBoundaryAsValidRawWord()
    {
        var input = Input();
        input["quantities"]!["rpm"]!["numerator"] = "1000000";
        input["quantities"]!["rpm"]!["denominator"] = "65535";
        var boundary = Analyze(input).Preview!;
        Assert.Equal("65535", boundary.CeilingTicks);
        Assert.Empty(boundary.PossibleT);
        Assert.Contains("TCERR", boundary.Scope, StringComparison.Ordinal);
        input["quantities"]!["rpm"]!["denominator"] = "65534";
        Assert.Equal(new ushort[] { ushort.MaxValue }, Analyze(input).Preview!.PossibleT);
    }

    [Fact]
    public void FileReaderRefusesOversizeAndExcessiveDepth()
    {
        var path = Path.Combine(Path.GetTempPath(), $"scaling-{Guid.NewGuid():N}.json");
        try
        {
            File.WriteAllText(path, new string(' ', 65537));
            Assert.Throws<InvalidDataException>(() => P28PhysicalScaling.Analyze(path));
            File.WriteAllText(path, new string('[', 10) + "1" + new string(']', 10));
            Assert.ThrowsAny<JsonException>(() => P28PhysicalScaling.Analyze(path));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Theory]
    [InlineData("denominator", "0")]
    [InlineData("numerator", "-1")]
    [InlineData("numerator", "1.5")]
    [InlineData("numerator", "1000000000001")]
    [InlineData("unit", "MHz")]
    [InlineData("provenance", "")]
    [InlineData("evidence", "confirmed")]
    public void RejectsMalformedOrImplicitConversions(string property, string value)
    {
        var input = Input();
        input["quantities"]!["clockHz"]![property] = value;
        Assert.Throws<InvalidDataException>(() => Analyze(input));
    }

    [Fact]
    public void MissingUnknownDuplicateAndWrongTypesAreRefused()
    {
        var input = Input();
        input["quantities"]!.AsObject().Remove("eventsPerCrankRev");
        Assert.Throws<InvalidDataException>(() => Analyze(input));
        input = Input();
        input["typicalHardware"] = true;
        Assert.Throws<InvalidDataException>(() => Analyze(input));
        using var duplicate = JsonDocument.Parse(Input().ToJsonString().Replace("\"formatVersion\":1", "\"formatVersion\":1,\"formatVersion\":1", StringComparison.Ordinal));
        Assert.Throws<InvalidDataException>(() => P28PhysicalScaling.AnalyzeDocument(duplicate.RootElement));
        input = Input();
        input["quantities"]!["clockHz"]!["numerator"] = 100;
        Assert.Throws<InvalidDataException>(() => Analyze(input));
    }

    private static P28ScalingAnalysis Analyze(JsonObject input)
    {
        using var document = JsonDocument.Parse(input.ToJsonString());
        return P28PhysicalScaling.AnalyzeDocument(document.RootElement);
    }

    private static JsonObject Input() => new()
    {
        ["formatVersion"] = 1,
        ["scope"] = "uniform-normal-intervals",
        ["quantities"] = new JsonObject
        {
            ["clockHz"] = Quantity("1000000", "Hz"),
            ["timerClockDivisor"] = Quantity("20", "1"),
            ["eventsPerCrankRev"] = Quantity("3", "events/crank-revolution"),
            ["eventsPerSample"] = Quantity("1", "events/sample"),
            ["rpm"] = Quantity("3000", "crank-revolutions/minute"),
        },
    };

    private static JsonObject Quantity(string numerator, string unit) => new()
    {
        ["numerator"] = numerator,
        ["denominator"] = "1",
        ["unit"] = unit,
        ["provenance"] = "Invented dimensional test, not P28 hardware",
        ["evidence"] = "analyst-supplied",
    };
}
