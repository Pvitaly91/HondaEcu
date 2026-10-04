using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed record P28QuartetHandoffInitial(P28PostStoreInitial FuelPrefix, bool Bit012a1);
public sealed record P28QuartetHandoffCall(P28PostStoreCall Prefix, byte Selector013c);
public sealed class P28QuartetHandoffScenario
{
    public int FormatVersion => 1;
    public const string PurposeName = "quartet-scheduled-consumer-test";
    public string Purpose => PurposeName;
    public string Provenance { get; }
    public P28QuartetHandoffInitial InitialState { get; }
    public IReadOnlyList<P28QuartetHandoffCall> Calls { get; }
    public IReadOnlyList<int> TraceEventIndexes { get; }
    public P28PostStoreMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28QuartetHandoffScenario(P28QuartetHandoffInitial initial, IReadOnlyList<P28QuartetHandoffCall> calls, P28PostSelectionCriticalScenario prefix)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); TraceEventIndexes = prefix.TraceCallIndexes; Provenance = prefix.Provenance; Mutation = prefix.Mutation; }
    public static P28QuartetHandoffScenario Create(P28QuartetHandoffInitial initial, IReadOnlyList<P28QuartetHandoffCall> calls, string provenance, IReadOnlyList<int>? traces = null, P28PostStoreMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Any(c => c is null || c.Prefix is null || c.Selector013c > 3)) throw new ArgumentException("Raw selector013c must be in audited safe domain0..3.");
        var prefix = P28PostSelectionCriticalScenario.Create(initial.FuelPrefix, calls.Select(c => c.Prefix).ToArray(), provenance, traces, mutation);
        return new(initial, calls, prefix);
    }
    internal P28PostSelectionCriticalScenario PrefixScenario => P28PostSelectionCriticalScenario.Create(InitialState.FuelPrefix, Calls.Select(c => c.Prefix).ToArray(), Provenance, TraceEventIndexes, Mutation);
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceEventIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28QuartetHandoffScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2x scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 16 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceEventIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2x version/purpose.");
        var initial = r.GetProperty("initialState"); P28LimiterScenario.Shape(initial, "fuelPrefix", "bit012a1");
        foreach (var c in r.GetProperty("calls").EnumerateArray()) P28LimiterScenario.Shape(c, "prefix", "selector013c");
        var prefixJson = JsonSerializer.Serialize(new { formatVersion = 1, purpose = "post-selection-critical-native-software-test", provenance = r.GetProperty("provenance"), initialState = initial.GetProperty("fuelPrefix"), calls = r.GetProperty("calls").EnumerateArray().Select(c => c.GetProperty("prefix")).ToArray(), traceCallIndexes = r.GetProperty("traceEventIndexes"), mutation = r.GetProperty("mutation") });
        var prefix = P28PostSelectionCriticalScenario.Parse(prefixJson);
        return Create(new(prefix.InitialState, initial.GetProperty("bit012a1").GetBoolean()), prefix.Calls.Select((c, i) => new P28QuartetHandoffCall(c, r.GetProperty("calls")[i].GetProperty("selector013c").GetByte())).ToArray(), prefix.Provenance, prefix.TraceCallIndexes, prefix.Mutation);
    }
}
