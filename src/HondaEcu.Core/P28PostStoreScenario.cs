using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

[JsonConverter(typeof(JsonStringEnumConverter<P28PostStoreMutationKind>))]
public enum P28PostStoreMutationKind { FuelCell, Bank0Cut, Bank0Resume, Bank1Cut, Bank1Resume }
public sealed record P28PostStoreMutation(P28PostStoreMutationKind Kind, string? MapId, int? Row, int? Column, ushort Value);
public sealed record P28PostStoreInitial(P28AdaptiveFuelInitial Adaptive, ushort Previous03b4);
public sealed record P28PostStoreCall(P28AdaptiveFuelCall Adaptive, bool Disable125, bool Disable12e);
public sealed class P28PostStoreScenario
{
    public int FormatVersion => 1;
    public string Purpose => "post-store-fuel-native-software-test";
    public string Provenance { get; }
    public P28PostStoreInitial InitialState { get; }
    public IReadOnlyList<P28PostStoreCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28PostStoreMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28PostStoreScenario(P28PostStoreInitial initial, IReadOnlyList<P28PostStoreCall> calls, string provenance,
        IReadOnlyList<int> traces, P28PostStoreMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; TraceCallIndexes = Array.AsReadOnly(traces.ToArray()); Mutation = mutation; }
    public static P28PostStoreScenario Create(P28PostStoreInitial initial, IReadOnlyList<P28PostStoreCall> calls,
        string provenance, IReadOnlyList<int>? traces = null, P28PostStoreMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(calls);
        traces ??= [];
        if (calls.Any(c => c is null || c.Adaptive is null)) throw new ArgumentException("Dense native events required.");
        _ = P28AdaptiveFuelScenario.Create(initial.Adaptive, calls.Select(c => c.Adaptive).ToArray(), provenance, traces);
        if (mutation is not null)
        {
            if (!Enum.IsDefined(mutation.Kind)) throw new ArgumentException("Closed one-field mutation required.");
            if (mutation.Kind == P28PostStoreMutationKind.FuelCell)
            {
                if (mutation.Value > 255 || mutation.Row is null || mutation.Column is null || mutation.MapId is null) throw new ArgumentException("Raw-u8 primary cell required.");
                _ = P28FuelMapContract.CellOffset(mutation.MapId, mutation.Row.Value, mutation.Column.Value);
            }
            else if (mutation.MapId is not null || mutation.Row is not null || mutation.Column is not null) throw new ArgumentException("Adaptive word cannot carry a cell location.");
        }
        return new(initial, calls, provenance, traces, mutation);
    }
    internal P28AdaptiveFuelScenario PrefixScenario => P28AdaptiveFuelScenario.Create(InitialState.Adaptive,
        Calls.Select(c => c.Adaptive).ToArray(), Provenance, TraceCallIndexes);
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28PostStoreScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2p scenario exceeds 256 KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 14 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "post-store-fuel-native-software-test") throw new InvalidDataException("Unsupported M2p version/purpose.");
        P28LimiterScenario.Shape(r.GetProperty("initialState"), "adaptive", "previous03b4");
        foreach (var c in r.GetProperty("calls").EnumerateArray()) P28LimiterScenario.Shape(c, "adaptive", "disable125", "disable12e");
        // Historical closed prefix schema, not an old operation or a second execution.
        var old = JsonSerializer.Serialize(new
        {
            formatVersion = 1,
            purpose = "adaptive-limiter-fuel-native-software-test",
            provenance = r.GetProperty("provenance"),
            initialState = r.GetProperty("initialState").GetProperty("adaptive"),
            calls = r.GetProperty("calls").EnumerateArray().Select(c => c.GetProperty("adaptive")).ToArray(),
            traceCallIndexes = r.GetProperty("traceCallIndexes"),
            mutation = (object?)null
        });
        _ = P28AdaptiveFuelScenario.Parse(old);
        var m = r.GetProperty("mutation");
        if (m.ValueKind != JsonValueKind.Null)
        {
            P28LimiterScenario.Shape(m, "kind", "mapId", "row", "column", "value");
            if (m.GetProperty("kind").GetString() is not ("FuelCell" or "Bank0Cut" or "Bank0Resume" or "Bank1Cut" or "Bank1Resume" or
                "fuel-cell" or "bank0-cut" or "bank0-resume" or "bank1-cut" or "bank1-resume")) throw new InvalidDataException("Closed one-field kind required.");
        }
        return Create(r.GetProperty("initialState").Deserialize<P28PostStoreInitial>(P28StatefulScenario.Options)!,
            r.GetProperty("calls").Deserialize<P28PostStoreCall[]>(P28StatefulScenario.Options)!, r.GetProperty("provenance").GetString()!,
            r.GetProperty("traceCallIndexes").Deserialize<int[]>()!, m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28PostStoreMutation>(P28StatefulScenario.Options));
    }
}
