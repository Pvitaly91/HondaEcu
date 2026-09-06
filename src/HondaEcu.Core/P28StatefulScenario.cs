using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed record P28VtecPersistentState(byte Data0131, byte Data0127, byte Data0198,
    byte Data01D8, byte Data01D9, byte Data01DF, byte Data00F3, byte P1OutputData);

/// <summary>Software snapshots, not measured sensors. Ticks count explicit native body invocations.</summary>
public sealed record P28VtecCall(int Index, byte CompactCode, int Context, bool Enabled,
    byte Raw00CC, byte Raw00D9, ushort Snapshot011A, byte Snapshot011C, byte Snapshot0119,
    byte Raw0132, byte Raw0199, int FastTicks, int SlowTicks);

public sealed class P28StatefulScenario
{
    internal static readonly JsonSerializerOptions Options = new(JsonDefaults.Create(false))
    { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    private P28StatefulScenario(P28VtecPersistentState state, IReadOnlyList<P28VtecCall> calls, string provenance, IReadOnlyList<int> traces)
    {
        InitialState = state; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance;
        TraceCallIndexes = Array.AsReadOnly(traces.ToArray()); Digest = P28RpmSerialization.Digest(Artifact());
    }
    public int FormatVersion => 1;
    public string Purpose => "explicit-stateful-vtec-software-stimulus";
    public P28VtecPersistentState InitialState { get; }
    public IReadOnlyList<P28VtecCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public string Provenance { get; }
    public string Digest { get; }

    public static P28StatefulScenario Create(P28VtecPersistentState state, IReadOnlyList<P28VtecCall> calls,
        string provenance, IReadOnlyList<int>? traceCallIndexes = null)
    {
        ArgumentNullException.ThrowIfNull(state); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Count is < 1 or > 256 || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("Stateful stimulus requires 1..256 calls and 1..512 characters of provenance.");
        for (var i = 0; i < calls.Count; i++)
        {
            var call = calls[i];
            if (call is null || call.Index != i || call.Context is < 0 or > 1 || call.FastTicks is < 0 or > 32 || call.SlowTicks is < 0 or > 32)
                throw new ArgumentException("Calls must be dense from zero, context 0/1, with 0..32 ticks of each explicitly scheduled native group.");
        }
        var traces = traceCallIndexes ?? [];
        if (traces.Count > 8 || traces.Distinct().Count() != traces.Count || traces.Any(i => i < 0 || i >= calls.Count))
            throw new ArgumentException("At most eight unique in-range trace witnesses are allowed.");
        return new(state, calls, provenance, traces);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes };
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(Artifact(), new JsonSerializerOptions(Options) { WriteIndented = indented });
    public P28StatefulScenario ForReplay(int index) => Create(InitialState, Calls.Take(index + 1).ToArray(), Provenance, [index]);
    public static P28StatefulScenario Parse(string json)
    {
        ArgumentNullException.ThrowIfNull(json);
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("Stateful scenario exceeds 1 MiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 12 });
        var r = doc.RootElement;
        P28AcquisitionScenario.Shape(r, ["formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes"]);
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "explicit-stateful-vtec-software-stimulus")
            throw new InvalidDataException("Unsupported stateful scenario purpose/version.");
        StateShape(r.GetProperty("initialState"));
        foreach (var c in r.GetProperty("calls").EnumerateArray()) CallShape(c);
        return Create(r.GetProperty("initialState").Deserialize<P28VtecPersistentState>(Options)!,
            r.GetProperty("calls").Deserialize<P28VtecCall[]>(Options)!, r.GetProperty("provenance").GetString()!,
            r.GetProperty("traceCallIndexes").Deserialize<int[]>(Options)!);
    }
    internal static void StateShape(JsonElement e) => P28AcquisitionScenario.Shape(e,
        ["data0131", "data0127", "data0198", "data01D8", "data01D9", "data01DF", "data00F3", "p1OutputData"]);
    internal static void CallShape(JsonElement e) => P28AcquisitionScenario.Shape(e,
        ["index", "compactCode", "context", "enabled", "raw00CC", "raw00D9", "snapshot011A", "snapshot011C", "snapshot0119", "raw0132", "raw0199", "fastTicks", "slowTicks"]);
}
