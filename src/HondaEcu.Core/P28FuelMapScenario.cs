using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28FuelMapState(byte LoadIndex, byte Map0RpmIndex, byte Map1RpmIndex, ushort LoadFraction,
    ushort Map0RpmFraction, ushort Map1RpmFraction, byte Selector0127, byte ConsumerFactor013f, ushort ConsumerOutput0140);
public sealed record P28FuelMapCall(int Index, string MapId, byte RawLoad, byte RawMap0Rpm, byte RawMap1Rpm);
public sealed record P28FuelMapMutation(string MapId, int Row, int Column, byte Value);

public sealed class P28FuelMapScenario
{
    public int FormatVersion => 1;
    public string Purpose => "fuel-map-native-lookup-software-test";
    public string Provenance { get; }
    public P28FuelMapState InitialState { get; }
    public IReadOnlyList<P28FuelMapCall> Calls { get; }
    public P28FuelMapMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28FuelMapScenario(P28FuelMapState initial, IReadOnlyList<P28FuelMapCall> calls, string provenance, P28FuelMapMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; Mutation = mutation; }

    public static P28FuelMapScenario Create(P28FuelMapState initial, IReadOnlyList<P28FuelMapCall> calls, string provenance, P28FuelMapMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Count is < 1 or > 512 || calls.Where((call, index) => call is null || call.Index != index || call.MapId is not ("map_0" or "map_1")).Any())
            throw new ArgumentException("Require 1..512 dense calls with code-owned map_0/map_1 IDs.");
        if (initial.LoadIndex > 8 || initial.Map0RpmIndex > 18 || initial.Map1RpmIndex > 18 || (initial.Selector0127 & ~2) != 0)
            throw new ArgumentException("Initial caches or selector are outside the bounded native contract.");
        if (string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("A bounded non-empty software-test provenance is required.");
        if (mutation is not null) _ = P28FuelMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        return new(initial, calls, provenance, mutation);
    }

    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));

    public static P28FuelMapScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("Fuel-map scenario exceeds 1 MiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
        var root = document.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "initialState", "calls", "mutation");
        if (root.GetProperty("formatVersion").GetInt32() != 1 || root.GetProperty("purpose").GetString() != "fuel-map-native-lookup-software-test")
            throw new InvalidDataException("Unsupported fuel-map scenario version/purpose.");
        P28LimiterScenario.Shape(root.GetProperty("initialState"), "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction",
            "map0RpmFraction", "map1RpmFraction", "selector0127", "consumerFactor013f", "consumerOutput0140");
        foreach (var call in root.GetProperty("calls").EnumerateArray())
            P28LimiterScenario.Shape(call, "index", "mapId", "rawLoad", "rawMap0Rpm", "rawMap1Rpm");
        var mutation = root.GetProperty("mutation");
        if (mutation.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(mutation, "mapId", "row", "column", "value");
        try
        {
            return Create(root.GetProperty("initialState").Deserialize<P28FuelMapState>(P28StatefulScenario.Options)!,
                root.GetProperty("calls").Deserialize<P28FuelMapCall[]>(P28StatefulScenario.Options)!, root.GetProperty("provenance").GetString()!,
                mutation.ValueKind == JsonValueKind.Null ? null : mutation.Deserialize<P28FuelMapMutation>(P28StatefulScenario.Options));
        }
        catch (Exception exception) when (exception is ArgumentException or InvalidOperationException or OverflowException)
        {
            throw new InvalidDataException("Invalid bounded fuel-map scenario.", exception);
        }
    }
}
