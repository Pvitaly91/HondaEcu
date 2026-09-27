using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

[JsonConverter(typeof(JsonStringEnumConverter<P28AdaptiveFuelMutationKind>))]
public enum P28AdaptiveFuelMutationKind { Bank0Cut, Bank0Resume, Bank1Cut, Bank1Resume }
public sealed record P28AdaptiveFuelMutation(P28AdaptiveFuelMutationKind Kind, ushort Value);
public sealed record P28AdaptiveFuelInitial(P28LimiterFuelInitial Joint, ushort RamCut, ushort RamResume,
    byte Timer, byte Counter, ushort Ie, ushort RestoreIe);
public sealed record P28AdaptiveFuelCall(P28LimiterFuelCall Fuel, ushort Raw00ce, byte RawD9, bool Bank1,
    bool Reset217, bool Reset214, bool Mode212, bool Enable223, bool FixedSource, byte TimerTicks, byte CounterTicks)
{
    internal P28AdaptiveCall Adaptive => new(new(Fuel.Index, Fuel.RawPeriod, false, FixedSource, 255),
        Raw00ce, Bank1, Reset217, Reset214, Mode212, Enable223, RawD9, TimerTicks, CounterTicks);
}
/// <summary>One authoritative history; no per-event produced thresholds, request, factor or output.</summary>
public sealed class P28AdaptiveFuelScenario
{
    public int FormatVersion => 1;
    public string Purpose => "adaptive-limiter-fuel-native-software-test";
    public string Provenance { get; }
    public P28AdaptiveFuelInitial InitialState { get; }
    public IReadOnlyList<P28AdaptiveFuelCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28AdaptiveFuelMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28AdaptiveFuelScenario(P28AdaptiveFuelInitial initial, IReadOnlyList<P28AdaptiveFuelCall> calls,
        string provenance, IReadOnlyList<int> traces, P28AdaptiveFuelMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; TraceCallIndexes = Array.AsReadOnly(traces.ToArray()); Mutation = mutation; }
    public static P28AdaptiveFuelScenario Create(P28AdaptiveFuelInitial initial, IReadOnlyList<P28AdaptiveFuelCall> calls,
        string provenance, IReadOnlyList<int>? traces = null, P28AdaptiveFuelMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Joint); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Any(c => c is null || c.Fuel is null || c.TimerTicks + c.CounterTicks > 32))
            throw new ArgumentException("Dense events and <=32 combined native ticks required.");
        traces ??= [];
        _ = P28LimiterFuelScenario.Create(initial.Joint, calls.Select(c => c.Fuel).ToArray(), provenance, traces);
        if (mutation is not null && !Enum.IsDefined(mutation.Kind)) throw new ArgumentException("Closed adaptive word mutation required.");
        return new(initial, calls, provenance, traces, mutation);
    }
    internal P28LimiterFuelScenario JointScenario(int count) => P28LimiterFuelScenario.Create(InitialState.Joint,
        Calls.Take(count).Select(c => c.Fuel).ToArray(), Provenance, TraceCallIndexes.Where(i => i < count).ToArray());
    internal P28AdaptiveState ModelInitial => new(new(InitialState.Joint.Data0124, InitialState.Joint.Data012b, 0, 0,
        InitialState.Joint.Data01d7, InitialState.RamCut, InitialState.RamResume), InitialState.Timer, InitialState.Counter, InitialState.Ie, InitialState.RestoreIe);
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28AdaptiveFuelScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2o scenario exceeds 256 KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 12 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "adaptive-limiter-fuel-native-software-test")
            throw new InvalidDataException("Unsupported M2o version/purpose.");
        var initial = r.GetProperty("initialState"); P28LimiterScenario.Shape(initial, "joint", "ramCut", "ramResume", "timer", "counter", "ie", "restoreIe");
        var joint = initial.GetProperty("joint"); P28LimiterScenario.Shape(joint, "fuel", "data0124", "data012b", "data01d7", "producerMode012c", "producerSelector012f", "hysteresis0130");
        P28LimiterScenario.Shape(joint.GetProperty("fuel"), "loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "selector0127", "consumerFactor013f");
        foreach (var c in r.GetProperty("calls").EnumerateArray())
        {
            P28LimiterScenario.Shape(c, "fuel", "raw00ce", "rawD9", "bank1", "reset217", "reset214", "mode212", "enable223", "fixedSource", "timerTicks", "counterTicks");
            var f = c.GetProperty("fuel"); P28LimiterScenario.Shape(f, "index", "rawPeriod", "rawLoad", "rawMap0Rpm", "rawMap1Rpm", "sources"); P28FuelFactorScenario.SourcesShape(f.GetProperty("sources"));
        }
        var m = r.GetProperty("mutation"); if (m.ValueKind != JsonValueKind.Null)
        {
            P28LimiterScenario.Shape(m, "kind", "value");
            if (m.GetProperty("kind").GetString() is not ("Bank0Cut" or "Bank0Resume" or "Bank1Cut" or "Bank1Resume" or "bank0-cut" or "bank0-resume" or "bank1-cut" or "bank1-resume"))
                throw new InvalidDataException("Closed code-owned adaptive word required.");
        }
        return Create(initial.Deserialize<P28AdaptiveFuelInitial>(P28StatefulScenario.Options)!, r.GetProperty("calls").Deserialize<P28AdaptiveFuelCall[]>(P28StatefulScenario.Options)!,
            r.GetProperty("provenance").GetString()!, r.GetProperty("traceCallIndexes").Deserialize<int[]>()!, m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28AdaptiveFuelMutation>(P28StatefulScenario.Options));
    }
}
