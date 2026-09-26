using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28FuelAdditiveSources(ushort Factor0158, ushort Source0142, ushort Source0144,
    ushort Source0146, byte Source0148, byte Source0149, ushort Source014a, ushort Source014c, byte Counter00f2);
public sealed record P28FuelAdditiveCall(int Index, byte RawLoad, byte RawMap0Rpm, byte RawMap1Rpm, P28FuelAdditiveSources Sources);
public sealed record P28FuelAdditiveInitial(P28FuelCalculationInitial Fuel, byte CallerGate0124, byte Mode012b);

public sealed class P28FuelAdditiveScenario
{
    public int FormatVersion => 1;
    public string Purpose => "fuel-additive-native-software-test";
    public string Provenance { get; }
    public P28FuelAdditiveInitial InitialState { get; }
    public IReadOnlyList<P28FuelAdditiveCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28FuelMapMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28FuelAdditiveScenario(P28FuelAdditiveInitial initial, IReadOnlyList<P28FuelAdditiveCall> calls,
        string provenance, IReadOnlyList<int> traces, P28FuelMapMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; TraceCallIndexes = Array.AsReadOnly(traces.ToArray()); Mutation = mutation; }
    public static P28FuelAdditiveScenario Create(P28FuelAdditiveInitial initial, IReadOnlyList<P28FuelAdditiveCall> calls,
        string provenance, IReadOnlyList<int>? traces = null, P28FuelMapMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Fuel); ArgumentNullException.ThrowIfNull(calls);
        traces ??= [];
        if (calls.Any(c => c is null || c.Sources is null)) throw new ArgumentException("Explicit non-null source snapshots required.");
        _ = P28FuelCalculationScenario.Create(initial.Fuel,
            calls.Select(c => new P28FuelCalculationCall(c.Index, c.RawLoad, c.RawMap0Rpm, c.RawMap1Rpm, c.Sources.Factor0158)).ToArray(), provenance, traces, mutation);
        if ((initial.CallerGate0124 & 0x10) != 0 || calls.Any(c => c.Sources.Source0144 > 255))
            throw new ArgumentException("Require compatible gate0124.4=0 and explicit disjoint source snapshots.");
        return new(initial, calls, provenance, traces, mutation);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28FuelAdditiveScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2l scenario exceeds 256 KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 10 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "fuel-additive-native-software-test")
            throw new InvalidDataException("Unsupported M2l scenario version/purpose.");
        var initial = r.GetProperty("initialState"); P28LimiterScenario.Shape(initial, "fuel", "callerGate0124", "mode012b");
        P28LimiterScenario.Shape(initial.GetProperty("fuel"), "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "selector0127", "consumerFactor013f");
        foreach (var c in r.GetProperty("calls").EnumerateArray())
        { P28LimiterScenario.Shape(c, "index", "rawLoad", "rawMap0Rpm", "rawMap1Rpm", "sources"); SourcesShape(c.GetProperty("sources")); }
        var m = r.GetProperty("mutation"); if (m.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(m, "mapId", "row", "column", "value");
        try
        {
            return Create(initial.Deserialize<P28FuelAdditiveInitial>(P28StatefulScenario.Options)!, r.GetProperty("calls").Deserialize<P28FuelAdditiveCall[]>(P28StatefulScenario.Options)!,
            r.GetProperty("provenance").GetString()!, r.GetProperty("traceCallIndexes").Deserialize<int[]>()!, m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28FuelMapMutation>(P28StatefulScenario.Options));
        }
        catch (Exception e) when (e is ArgumentException or OverflowException or InvalidOperationException)
        { throw new InvalidDataException("Invalid M2l source/caller contract.", e); }
    }
    internal static void SourcesShape(JsonElement s) => P28LimiterScenario.Shape(s, "factor0158", "source0142", "source0144", "source0146", "source0148", "source0149", "source014a", "source014c", "counter00f2");
}
