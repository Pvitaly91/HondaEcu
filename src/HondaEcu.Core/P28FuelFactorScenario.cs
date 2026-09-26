using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28FuelFactorSources(ushort Source015a, ushort Source015c, byte Source015e,
    ushort Source0160, ushort Source0162, byte Source0164, byte Source0165, byte Source0166,
    byte Source0167, byte Source0168, byte Source0133, ushort Source0142, ushort Source0144,
    ushort Source0146, byte Source0148, byte Source0149, ushort Source014a, ushort Source014c, byte Counter00f2);
public sealed record P28FuelFactorCall(int Index, byte RawLoad, byte RawMap0Rpm, byte RawMap1Rpm, P28FuelFactorSources Sources);
public sealed record P28FuelFactorInitial(P28FuelCalculationInitial Fuel, byte CallerGate0124, byte Mode012b,
    byte ProducerMode012c, byte ProducerSelector012f, byte Hysteresis0130);

/// <summary>Closed upstream snapshots only; native-produced words and register carriers are not inputs.</summary>
public sealed class P28FuelFactorScenario
{
    public int FormatVersion => 1;
    public string Purpose => "fuel-factor-native-software-test";
    public string Provenance { get; }
    public P28FuelFactorInitial InitialState { get; }
    public IReadOnlyList<P28FuelFactorCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28FuelMapMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28FuelFactorScenario(P28FuelFactorInitial initial, IReadOnlyList<P28FuelFactorCall> calls,
        string provenance, IReadOnlyList<int> traces, P28FuelMapMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; TraceCallIndexes = Array.AsReadOnly(traces.ToArray()); Mutation = mutation; }
    public static P28FuelFactorScenario Create(P28FuelFactorInitial initial, IReadOnlyList<P28FuelFactorCall> calls,
        string provenance, IReadOnlyList<int>? traces = null, P28FuelMapMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Fuel); ArgumentNullException.ThrowIfNull(calls);
        traces ??= [];
        if (calls.Count is < 1 or > 64 || calls.Where((c, i) => c is null || c.Sources is null || c.Index != i || c.Sources.Source0144 > 255).Any() ||
            traces.Count > 8 || traces.Distinct().Count() != traces.Count || traces.Any(i => i < 0 || i >= calls.Count) ||
            initial.Fuel.LoadIndex > 8 || initial.Fuel.Map0RpmIndex > 18 || initial.Fuel.Map1RpmIndex > 18 ||
            (initial.CallerGate0124 & 0x10) != 0 || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("Require bounded dense upstream snapshots, once-only compatible gates and provenance.");
        if (mutation is not null) _ = P28FuelMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        return new(initial, calls, provenance, traces, mutation);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28FuelFactorScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2m scenario exceeds 256 KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 10 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "fuel-factor-native-software-test")
            throw new InvalidDataException("Unsupported M2m scenario version/purpose.");
        var initial = r.GetProperty("initialState"); P28LimiterScenario.Shape(initial, "fuel", "callerGate0124", "mode012b", "producerMode012c", "producerSelector012f", "hysteresis0130");
        P28LimiterScenario.Shape(initial.GetProperty("fuel"), "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "selector0127", "consumerFactor013f");
        foreach (var c in r.GetProperty("calls").EnumerateArray())
        { P28LimiterScenario.Shape(c, "index", "rawLoad", "rawMap0Rpm", "rawMap1Rpm", "sources"); SourcesShape(c.GetProperty("sources")); }
        var m = r.GetProperty("mutation"); if (m.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(m, "mapId", "row", "column", "value");
        try
        {
            return Create(initial.Deserialize<P28FuelFactorInitial>(P28StatefulScenario.Options)!, r.GetProperty("calls").Deserialize<P28FuelFactorCall[]>(P28StatefulScenario.Options)!,
                r.GetProperty("provenance").GetString()!, r.GetProperty("traceCallIndexes").Deserialize<int[]>()!, m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28FuelMapMutation>(P28StatefulScenario.Options));
        }
        catch (Exception e) when (e is ArgumentException or OverflowException or InvalidOperationException)
        { throw new InvalidDataException("Invalid M2m upstream source/caller contract.", e); }
    }
    internal static void SourcesShape(JsonElement s) => P28LimiterScenario.Shape(s, "source015a", "source015c", "source015e", "source0160", "source0162", "source0164", "source0165",
        "source0166", "source0167", "source0168", "source0133", "source0142", "source0144", "source0146", "source0148", "source0149", "source014a", "source014c", "counter00f2");
}
