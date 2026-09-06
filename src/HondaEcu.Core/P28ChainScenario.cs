using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28ChainRawInputs(byte Raw00CC, byte Raw00D9, byte Snapshot0119, ushort Snapshot011A,
    byte Snapshot011C, byte Raw0132, byte Raw0199);
public sealed record P28ChainState(P28AcquisitionState Acquisition, P28VtecPersistentState Decision,
    byte Data011E, byte Data00B8, byte Code, P28ChainRawInputs Raw);
public sealed record P28ChainEvent(int Index, ushort Tmr2, byte Irqh, byte Tcon2, int Slot, bool RunDecision,
    int Context, bool Enabled, P28ChainRawInputs Raw, int FastTicks, int SlowTicks);

public sealed class P28ChainScenario
{
    public int FormatVersion => 1;
    public string Purpose => "explicit-integrated-capture-vtec-test-schedule";
    public P28ChainState InitialState { get; }
    public IReadOnlyList<P28ChainEvent> Events { get; }
    public IReadOnlyList<int> TraceEventIndexes { get; }
    public string Provenance { get; }
    public string Digest { get; }
    private P28ChainScenario(P28ChainState initial, IReadOnlyList<P28ChainEvent> events, string provenance, IReadOnlyList<int> traces)
    {
        InitialState = Snapshot(initial); Events = Array.AsReadOnly(events.ToArray()); Provenance = provenance;
        TraceEventIndexes = Array.AsReadOnly(traces.ToArray()); Digest = P28RpmSerialization.Digest(Artifact());
    }
    internal static P28ChainState Snapshot(P28ChainState state)
    {
        ArgumentNullException.ThrowIfNull(state); ArgumentNullException.ThrowIfNull(state.Decision); ArgumentNullException.ThrowIfNull(state.Raw);
        return state with { Acquisition = P28AcquisitionModel.Snapshot(state.Acquisition) };
    }
    public static P28ChainScenario Create(P28ChainState initial, IReadOnlyList<P28ChainEvent> events, string provenance, IReadOnlyList<int>? traces = null)
    {
        ArgumentNullException.ThrowIfNull(events);
        if (events.Count is < 1 or > 256 || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("Integrated schedule requires 1..256 events and 1..512 provenance characters.");
        for (var i = 0; i < events.Count; i++)
        {
            var e = events[i];
            if (e is null || e.Raw is null || e.Index != i || e.Context is < 0 or > 1 || e.Slot is < 0 or > 5 || e.FastTicks is < 0 or > 32 || e.SlowTicks is < 0 or > 32)
                throw new ArgumentException("Invalid bounded event; no samples/T/Code/prior overrides are accepted.");
        }
        traces ??= [];
        if (traces.Count > 8 || traces.Distinct().Count() != traces.Count || traces.Any(i => i < 0 || i >= events.Count))
            throw new ArgumentException("At most eight distinct in-range trace events.");
        return new(initial, events, provenance, traces);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Events, TraceEventIndexes };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public P28ChainScenario ForReplay(int index) => Create(InitialState, Events.Take(index + 1).ToArray(), Provenance, [index]);
    public static P28ChainScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("Integrated scenario exceeds 1 MiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 12 });
        var r = doc.RootElement;
        Shape(r, "formatVersion", "purpose", "provenance", "initialState", "events", "traceEventIndexes");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "explicit-integrated-capture-vtec-test-schedule")
            throw new InvalidDataException("Unsupported integrated scenario version/purpose.");
        StateShape(r.GetProperty("initialState")); foreach (var e in r.GetProperty("events").EnumerateArray()) EventShape(e);
        return Create(r.GetProperty("initialState").Deserialize<P28ChainState>(P28StatefulScenario.Options)!,
            r.GetProperty("events").Deserialize<P28ChainEvent[]>(P28StatefulScenario.Options)!, r.GetProperty("provenance").GetString()!,
            r.GetProperty("traceEventIndexes").Deserialize<int[]>(P28StatefulScenario.Options)!);
    }
    internal static void Shape(JsonElement e, params string[] fields) => P28AcquisitionScenario.Shape(e, fields);
    internal static void RawShape(JsonElement e) => Shape(e, "raw00CC", "raw00D9", "snapshot0119", "snapshot011A", "snapshot011C", "raw0132", "raw0199");
    internal static void EventShape(JsonElement e)
    {
        Shape(e, "index", "tmr2", "irqh", "tcon2", "slot", "runDecision", "context", "enabled", "raw", "fastTicks", "slowTicks"); RawShape(e.GetProperty("raw"));
    }
    internal static void StateShape(JsonElement e)
    {
        Shape(e, "acquisition", "decision", "data011E", "data00B8", "code", "raw");
        Shape(e.GetProperty("acquisition"), "previousTimestamp", "samples", "data0128", "data00AE", "data00B6", "data011F", "previousT", "data0217", "data0231", "data0136");
        P28StatefulScenario.StateShape(e.GetProperty("decision")); RawShape(e.GetProperty("raw"));
    }
}
