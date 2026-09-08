using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28IdleContextsState(ushort Target, ushort Raw027a, ushort ErrorMagnitude,
    byte Data021a, byte Data0211, byte Data0216, byte Data0217, byte Data0225, byte Data022a,
    ushort Raw0274, ushort Raw027c, byte Counter02e5, byte Counter02e8, byte Counter02e9);
public sealed record P28IdleSelectorInputs(bool Data021aBit0, bool Data0211Bit5, bool Data0216Bit3,
    bool Data0217Bit6, bool Data0225Bit1, bool Data022aBit4, bool Data022aBit5);
public sealed record P28IdleContextsCall(int Index, byte RawD9, ushort RawPeriod, P28IdleSelectorInputs? Selectors);
public sealed class P28IdleContextsScenario
{
    public int FormatVersion => 1;
    public string Purpose => "idle-target-contexts-software-test";
    public string Provenance { get; }
    public P28IdleContextsState InitialState { get; }
    public IReadOnlyList<P28IdleContextsCall> Calls { get; }
    public P28IdleMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28IdleContextsScenario(P28IdleContextsState state, IReadOnlyList<P28IdleContextsCall> calls, string provenance, P28IdleMutation? mutation)
    { InitialState = state; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; Mutation = mutation; }
    public static P28IdleContextsScenario Create(P28IdleContextsState state, IReadOnlyList<P28IdleContextsCall> calls, string provenance, P28IdleMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(state); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Count is < 1 or > 64 || calls.Where((c, i) => c is null || c.Index != i).Any() || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("Require 1..64 dense calls and bounded explicit software provenance.");
        if (mutation is not null) _ = P28IdleInspector.FieldOffset(mutation.Field);
        return new(state, calls, provenance, mutation);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28IdleContextsScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("Contexts scenario exceeds 1 MiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "idle-target-contexts-software-test") throw new InvalidDataException("Unsupported contexts version/purpose.");
        StateShape(r.GetProperty("initialState"));
        foreach (var c in r.GetProperty("calls").EnumerateArray())
        {
            P28LimiterScenario.Shape(c, "index", "rawD9", "rawPeriod", "selectors"); var u = c.GetProperty("selectors");
            if (u.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(u, "data021aBit0", "data0211Bit5", "data0216Bit3", "data0217Bit6", "data0225Bit1", "data022aBit4", "data022aBit5");
        }
        var m = r.GetProperty("mutation"); if (m.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(m, "field", "value");
        return Create(r.GetProperty("initialState").Deserialize<P28IdleContextsState>(P28StatefulScenario.Options)!, r.GetProperty("calls").Deserialize<P28IdleContextsCall[]>(P28StatefulScenario.Options)!, r.GetProperty("provenance").GetString()!, m.ValueKind == JsonValueKind.Null ? null : m.Deserialize<P28IdleMutation>(P28StatefulScenario.Options));
    }
    internal static void StateShape(JsonElement e) => P28LimiterScenario.Shape(e, "target", "raw027a", "errorMagnitude", "data021a", "data0211", "data0216", "data0217", "data0225", "data022a", "raw0274", "raw027c", "counter02e5", "counter02e8", "counter02e9");
    internal static P28IdleContextsState ApplySelectors(P28IdleContextsState state, P28IdleSelectorInputs? u)
    {
        if (u is null) return state;
        static byte Mask(byte value, int mask, bool on) => (byte)((value & ~mask) | (on ? mask : 0));
        return state with
        {
            Data021a = Mask(state.Data021a, 1, u.Data021aBit0),
            Data0211 = Mask(state.Data0211, 32, u.Data0211Bit5),
            Data0216 = Mask(state.Data0216, 8, u.Data0216Bit3),
            Data0217 = Mask(state.Data0217, 64, u.Data0217Bit6),
            Data0225 = Mask(state.Data0225, 2, u.Data0225Bit1),
            Data022a = Mask(Mask(state.Data022a, 16, u.Data022aBit4), 32, u.Data022aBit5)
        };
    }
}
