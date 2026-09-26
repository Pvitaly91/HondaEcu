using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28FuelCalculationInitial(byte LoadIndex, byte Map0RpmIndex, byte Map1RpmIndex,
    ushort LoadFraction, ushort Map0RpmFraction, ushort Map1RpmFraction, byte Selector0127, byte ConsumerFactor013f)
{
    internal P28FuelMapState Fuel => new(LoadIndex, Map0RpmIndex, Map1RpmIndex, LoadFraction,
        Map0RpmFraction, Map1RpmFraction, Selector0127, ConsumerFactor013f, 0);
}
public sealed record P28FuelCalculationCall(int Index, byte RawLoad, byte RawMap0Rpm, byte RawMap1Rpm, ushort Factor0158);

public sealed class P28FuelCalculationScenario
{
    public int FormatVersion => 1;
    public string Purpose => "fuel-calculation-native-software-test";
    public string Provenance { get; }
    public P28FuelCalculationInitial InitialState { get; }
    public IReadOnlyList<P28FuelCalculationCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28FuelMapMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28FuelCalculationScenario(P28FuelCalculationInitial initial, IReadOnlyList<P28FuelCalculationCall> calls,
        string provenance, IReadOnlyList<int> traces, P28FuelMapMutation? mutation)
    {
        InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance;
        TraceCallIndexes = Array.AsReadOnly(traces.ToArray()); Mutation = mutation;
    }

    public static P28FuelCalculationScenario Create(P28FuelCalculationInitial initial,
        IReadOnlyList<P28FuelCalculationCall> calls, string provenance, IReadOnlyList<int>? traces = null,
        P28FuelMapMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(calls);
        traces ??= [];
        if (calls.Count is < 1 or > 64 || calls.Where((c, i) => c is null || c.Index != i).Any() ||
            traces.Count > 8 || traces.Distinct().Count() != traces.Count || traces.Any(i => i < 0 || i >= calls.Count) ||
            initial.LoadIndex > 8 || initial.Map0RpmIndex > 18 || initial.Map1RpmIndex > 18 ||
            string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("Require bounded dense raw events, caches and provenance.");
        if (mutation is not null) _ = P28FuelMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        return new(initial, calls, provenance, traces, mutation);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28FuelCalculationScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2k scenario exceeds 256 KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
        var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "fuel-calculation-native-software-test")
            throw new InvalidDataException("Unsupported M2k scenario version/purpose.");
        P28LimiterScenario.Shape(r.GetProperty("initialState"), "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction",
            "map0RpmFraction", "map1RpmFraction", "selector0127", "consumerFactor013f");
        foreach (var c in r.GetProperty("calls").EnumerateArray())
            P28LimiterScenario.Shape(c, "index", "rawLoad", "rawMap0Rpm", "rawMap1Rpm", "factor0158");
        var m = r.GetProperty("mutation");
        if (m.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(m, "mapId", "row", "column", "value");
        try
        {
            return Create(r.GetProperty("initialState").Deserialize<P28FuelCalculationInitial>(P28StatefulScenario.Options)!,
            r.GetProperty("calls").Deserialize<P28FuelCalculationCall[]>(P28StatefulScenario.Options)!,
            r.GetProperty("provenance").GetString()!, r.GetProperty("traceCallIndexes").Deserialize<int[]>()!,
            m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28FuelMapMutation>(P28StatefulScenario.Options));
        }
        catch (Exception e) when (e is ArgumentException or OverflowException or InvalidOperationException)
        { throw new InvalidDataException("Invalid M2k raw software contract.", e); }
    }
}
