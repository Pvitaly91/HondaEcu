using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28LimiterState(byte Data0124, byte Data012B, byte Data012A, byte Data018F,
    byte Data01D7, ushort RamCut, ushort RamResume);
public sealed record P28LimiterCall(int Index, ushort RawPeriod, bool P4Bit0, bool Snapshot011bBit7, byte ChannelMask);
public sealed record P28LimiterMutation(string Field, ushort Value);

public sealed class P28LimiterScenario
{
    public int FormatVersion => 1;
    public string Purpose => "isolated-period-limiter-software-test";
    public string Provenance { get; }
    public P28LimiterState InitialState { get; }
    public IReadOnlyList<P28LimiterCall> Calls { get; }
    public P28LimiterMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28LimiterScenario(P28LimiterState initial, IReadOnlyList<P28LimiterCall> calls, string provenance, P28LimiterMutation? mutation)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; Mutation = mutation; }
    public static P28LimiterScenario Create(P28LimiterState initial, IReadOnlyList<P28LimiterCall> calls, string provenance, P28LimiterMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Count is < 1 or > 256 || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512 ||
            calls.Where((c, i) => c is null || c.Index != i || (c.ChannelMask & 0xF0) != 0xF0).Any())
            throw new ArgumentException("Require 1..256 dense calls, software channel masks with high nibble F, and bounded provenance.");
        if (mutation is not null) _ = P28LimiterInspector.FieldOffset(mutation.Field);
        return new(initial, calls, provenance, mutation);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28LimiterScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("Limiter scenario exceeds 1 MiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 }); var r = doc.RootElement;
        Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "isolated-period-limiter-software-test")
            throw new InvalidDataException("Unsupported limiter scenario version/purpose.");
        StateShape(r.GetProperty("initialState"));
        foreach (var c in r.GetProperty("calls").EnumerateArray())
            Shape(c, "index", "rawPeriod", "p4Bit0", "snapshot011bBit7", "channelMask");
        var m = r.GetProperty("mutation"); if (m.ValueKind != JsonValueKind.Null) Shape(m, "field", "value");
        return Create(r.GetProperty("initialState").Deserialize<P28LimiterState>(P28StatefulScenario.Options)!,
            r.GetProperty("calls").Deserialize<P28LimiterCall[]>(P28StatefulScenario.Options)!,
            r.GetProperty("provenance").GetString()!, m.Deserialize<P28LimiterMutation>(P28StatefulScenario.Options));
    }
    internal static void Shape(JsonElement e, params string[] fields)
    {
        if (e.ValueKind != JsonValueKind.Object) throw new InvalidDataException("Limiter object required.");
        var names = e.EnumerateObject().Select(p => p.Name).ToArray();
        if (names.Length != fields.Length || names.Distinct(StringComparer.Ordinal).Count() != names.Length ||
            !names.Order(StringComparer.Ordinal).SequenceEqual(fields.Order(StringComparer.Ordinal)))
            throw new InvalidDataException("Missing, duplicate or unknown limiter fields.");
    }
    internal static void StateShape(JsonElement s) => Shape(s, "data0124", "data012B", "data012A", "data018F", "data01D7", "ramCut", "ramResume");
}
