using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28IdleState(ushort Target, ushort Raw027a, ushort ErrorMagnitude, byte Data021a);
public sealed record P28IdleCall(int Index, byte RawD9, ushort RawPeriod);
public sealed record P28IdleMutation(string Field, ushort Value);
public sealed class P28IdleScenario
{
    public int FormatVersion => 1;
    public string Purpose => "idle-target-raw-context-test";
    public string Provenance { get; }
    public P28IdleState InitialState { get; }
    public IReadOnlyList<P28IdleCall> Calls { get; }
    public P28IdleMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28IdleScenario(P28IdleState initial, IReadOnlyList<P28IdleCall> calls, string provenance, P28IdleMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; Mutation = mutation; }
    public static P28IdleScenario Create(P28IdleState initial, IReadOnlyList<P28IdleCall> calls, string provenance, P28IdleMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(calls);
        if ((initial.Data021a & 1) == 0 || calls.Count is < 1 or > 64 || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512 ||
            calls.Where((c, i) => c is null || c.Index != i || c.RawD9 < 52).Any())
            throw new ArgumentException("Require persistent 021A.0 set, 1..64 dense calls with rawD9 >= 52 and bounded provenance. Other selector paths are not supported, not clamped.");
        if (mutation is not null) _ = P28IdleInspector.FieldOffset(mutation.Field);
        return new(initial, calls, provenance, mutation);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28IdleScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("Idle scenario exceeds 1 MiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "idle-target-raw-context-test") throw new InvalidDataException("Unsupported idle version/purpose.");
        StateShape(r.GetProperty("initialState"));
        foreach (var c in r.GetProperty("calls").EnumerateArray()) P28LimiterScenario.Shape(c, "index", "rawD9", "rawPeriod");
        var m = r.GetProperty("mutation"); if (m.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(m, "field", "value");
        return Create(r.GetProperty("initialState").Deserialize<P28IdleState>(P28StatefulScenario.Options)!,
            r.GetProperty("calls").Deserialize<P28IdleCall[]>(P28StatefulScenario.Options)!, r.GetProperty("provenance").GetString()!,
            m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28IdleMutation>(P28StatefulScenario.Options));
    }
    internal static void StateShape(JsonElement e) => P28LimiterScenario.Shape(e, "target", "raw027a", "errorMagnitude", "data021a");
}
