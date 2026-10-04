using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed class P28Word0196AlternateScenario
{
    public int FormatVersion => 1;
    public const string PurposeName = "word0196-software-alternate-test";
    public string Purpose => PurposeName;
    public string Provenance { get; }
    public P28Word0196HandoffInitial InitialState { get; }
    public IReadOnlyList<P28QuartetHandoffCall> Calls { get; }
    public IReadOnlyList<int> TraceEventIndexes { get; }
    public P28PostStoreMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28Word0196AlternateScenario(P28Word0196HandoffInitial initial, P28QuartetHandoffScenario prefix)
    { InitialState = initial; Calls = prefix.Calls; TraceEventIndexes = prefix.TraceEventIndexes; Provenance = prefix.Provenance; Mutation = prefix.Mutation; }
    public static P28Word0196AlternateScenario Create(P28Word0196HandoffInitial initial, IReadOnlyList<P28QuartetHandoffCall> calls, string provenance, IReadOnlyList<int>? traces = null, P28PostStoreMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.QuartetPrefix);
        return new(initial, P28QuartetHandoffScenario.Create(initial.QuartetPrefix, calls, provenance, traces, mutation));
    }
    internal P28QuartetHandoffScenario PrefixScenario => P28QuartetHandoffScenario.Create(InitialState.QuartetPrefix, Calls, Provenance, TraceEventIndexes, Mutation);
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceEventIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28Word0196AlternateScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2z scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 18 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceEventIndexes", "mutation");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2z version/purpose.");
        var initial = r.GetProperty("initialState"); P28LimiterScenario.Shape(initial, "quartetPrefix", "bit0128_2", "byte0117");
        var prefix = P28QuartetHandoffScenario.Parse(JsonSerializer.Serialize(new { formatVersion = 1, purpose = P28QuartetHandoffScenario.PurposeName, provenance = r.GetProperty("provenance"), initialState = initial.GetProperty("quartetPrefix"), calls = r.GetProperty("calls"), traceEventIndexes = r.GetProperty("traceEventIndexes"), mutation = r.GetProperty("mutation") }));
        return Create(new(prefix.InitialState, initial.GetProperty("bit0128_2").GetBoolean(), initial.GetProperty("byte0117").GetByte()), prefix.Calls, prefix.Provenance, prefix.TraceEventIndexes, prefix.Mutation);
    }
}
