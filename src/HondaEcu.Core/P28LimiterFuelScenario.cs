using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

[JsonConverter(typeof(JsonStringEnumConverter<P28LimiterFuelMutationKind>))]
public enum P28LimiterFuelMutationKind { FixedCut, FixedResume, FuelCell }
public sealed record P28LimiterFuelMutation(P28LimiterFuelMutationKind Kind, ushort Value, string? MapId, int? Row, int? Column);
public sealed record P28LimiterFuelInitial(P28FuelCalculationInitial Fuel, byte Data0124, byte Data012b, byte Data01d7,
    byte ProducerMode012c, byte ProducerSelector012f, byte Hysteresis0130);
public sealed record P28LimiterFuelCall(int Index, ushort RawPeriod, byte RawLoad, byte RawMap0Rpm, byte RawMap1Rpm, P28FuelFactorSources Sources)
{
    internal P28FuelFactorCall Fuel => new(Index, RawLoad, RawMap0Rpm, RawMap1Rpm, Sources);
}
/// <summary>One authoritative shared initial state. Fixed caller context is code owned.</summary>
public sealed class P28LimiterFuelScenario
{
    public int FormatVersion => 1;
    public string Purpose => "limiter-fuel-gate-native-software-test";
    public string Provenance { get; }
    public P28LimiterFuelInitial InitialState { get; }
    public IReadOnlyList<P28LimiterFuelCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28LimiterFuelMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28LimiterFuelScenario(P28LimiterFuelInitial initial, IReadOnlyList<P28LimiterFuelCall> calls, string provenance,
        IReadOnlyList<int> traces, P28LimiterFuelMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; TraceCallIndexes = Array.AsReadOnly(traces.ToArray()); Mutation = mutation; }
    public static P28LimiterFuelScenario Create(P28LimiterFuelInitial initial, IReadOnlyList<P28LimiterFuelCall> calls, string provenance,
        IReadOnlyList<int>? traces = null, P28LimiterFuelMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Any(c => c is null)) throw new ArgumentException("Dense non-null events required.");
        traces ??= [];
        // Reuse closed source/cache domains. This pure adapter is not a native initializer;
        // initial bit4 remains accepted here because the native limiter clears it.
        _ = P28FuelFactorScenario.Create(new(initial.Fuel, (byte)(initial.Data0124 & ~16), initial.Data012b,
            initial.ProducerMode012c, initial.ProducerSelector012f, initial.Hysteresis0130), calls.Select(c => c.Fuel).ToArray(), provenance, traces);
        if (mutation is not null)
        {
            if (!Enum.IsDefined(mutation.Kind)) throw new ArgumentException("Unknown one-field mutation kind.");
            if (mutation.Kind == P28LimiterFuelMutationKind.FuelCell)
            {
                if (mutation.Value > 255 || mutation.MapId is null || mutation.Row is null || mutation.Column is null) throw new ArgumentException("Require one fuel cell.");
                _ = P28FuelMapContract.CellOffset(mutation.MapId, mutation.Row.Value, mutation.Column.Value);
            }
            else if (mutation.MapId is not null || mutation.Row is not null || mutation.Column is not null) throw new ArgumentException("Fixed operand mutation cannot include cell coordinates.");
        }
        return new(initial, calls, provenance, traces, mutation);
    }
    internal P28FuelFactorScenario NumericScenario(int? count = null) => P28FuelFactorScenario.Create(new(InitialState.Fuel,
        (byte)(InitialState.Data0124 & ~16), InitialState.Data012b, InitialState.ProducerMode012c, InitialState.ProducerSelector012f, InitialState.Hysteresis0130),
        Calls.Take(count ?? Calls.Count).Select(c => c.Fuel).ToArray(), Provenance, TraceCallIndexes.Where(i => i < (count ?? Calls.Count)).ToArray());
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28LimiterFuelScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2n scenario exceeds 256 KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 10 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "limiter-fuel-gate-native-software-test") throw new InvalidDataException("Unsupported M2n version/purpose.");
        var initial = r.GetProperty("initialState"); P28LimiterScenario.Shape(initial, "fuel", "data0124", "data012b", "data01d7", "producerMode012c", "producerSelector012f", "hysteresis0130");
        P28LimiterScenario.Shape(initial.GetProperty("fuel"), "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "selector0127", "consumerFactor013f");
        foreach (var c in r.GetProperty("calls").EnumerateArray()) { P28LimiterScenario.Shape(c, "index", "rawPeriod", "rawLoad", "rawMap0Rpm", "rawMap1Rpm", "sources"); P28FuelFactorScenario.SourcesShape(c.GetProperty("sources")); }
        var m = r.GetProperty("mutation"); if (m.ValueKind != JsonValueKind.Null)
        {
            P28LimiterScenario.Shape(m, "kind", "value", "mapId", "row", "column");
            if (m.GetProperty("kind").GetString() is not ("FixedCut" or "FixedResume" or "FuelCell" or "fixed-cut" or "fixed-resume" or "fuel-cell")) throw new InvalidDataException("Closed mutation kind required.");
        }
        return Create(initial.Deserialize<P28LimiterFuelInitial>(P28StatefulScenario.Options)!, r.GetProperty("calls").Deserialize<P28LimiterFuelCall[]>(P28StatefulScenario.Options)!,
            r.GetProperty("provenance").GetString()!, r.GetProperty("traceCallIndexes").Deserialize<int[]>()!, m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28LimiterFuelMutation>(P28StatefulScenario.Options));
    }
}
