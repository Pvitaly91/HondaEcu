using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed record P28FrozenNoWriteObservation(ushort Tmr2,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] byte? Irqh)
{
    internal void Validate()
    {
        if (Irqh.HasValue != ((Tmr2 & 0x8000) == 0)) throw new ArgumentException("IRQH is required only for low TMR2; no unconsumed/default source.");
    }
}
public sealed record P28FallthroughData0136Call(P28PostStoreCall Prefix, P28FrozenNoWriteObservation ProducerObservation);
public sealed class P28FallthroughData0136Scenario
{
    public const string PurposeName = "native-fallthrough-data0136-caller-test";
    public int FormatVersion => 1;
    public string Purpose => PurposeName;
    internal P28PostReturnSelectorScenario SelectorReference { get; }
    public P28Word0196HandoffInitial InitialState => SelectorReference.InitialState;
    public byte InitialSelector013c => SelectorReference.InitialSelector013c;
    public IReadOnlyList<P28FallthroughData0136Call> Calls { get; }
    public string Provenance => SelectorReference.Provenance;
    public IReadOnlyList<int> TraceEventIndexes => SelectorReference.TraceEventIndexes;
    public P28PostStoreMutation? Mutation => SelectorReference.Mutation;
    public byte P2OutputLatch => SelectorReference.P2OutputLatch;
    public byte Tcon0ArchitecturalSnapshot => SelectorReference.Tcon0ArchitecturalSnapshot;
    public byte TrnsitArchitecturalFlags => SelectorReference.TrnsitArchitecturalFlags;
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28FallthroughData0136Scenario(P28PostReturnSelectorScenario selector, IReadOnlyList<P28FallthroughData0136Call> calls)
    { SelectorReference = selector; Calls = Array.AsReadOnly(calls.ToArray()); }
    public static P28FallthroughData0136Scenario Create(P28PostReturnSelectorScenario selector, IReadOnlyList<P28FrozenNoWriteObservation> observations)
    {
        ArgumentNullException.ThrowIfNull(selector); ArgumentNullException.ThrowIfNull(observations);
        if (observations.Count != selector.Calls.Count || observations.Any(o => o is null)) throw new ArgumentException("One frozen observation per existing dense call required.");
        foreach (var o in observations) o.Validate();
        return new(selector, selector.Calls.Select((c, i) => new P28FallthroughData0136Call(c.Prefix, observations[i])).ToArray());
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, InitialSelector013c, Calls, TraceEventIndexes, Mutation, P2OutputLatch, Tcon0ArchitecturalSnapshot, TrnsitArchitecturalFlags };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28FallthroughData0136Scenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2ag scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 18 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "initialSelector013c", "calls", "traceEventIndexes", "mutation", "p2OutputLatch", "tcon0ArchitecturalSnapshot", "trnsitArchitecturalFlags");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2ag version/purpose.");
        var observations = new List<P28FrozenNoWriteObservation>();
        foreach (var c in r.GetProperty("calls").EnumerateArray())
        {
            P28LimiterScenario.Shape(c, "prefix", "producerObservation"); var o = c.GetProperty("producerObservation");
            var has = o.TryGetProperty("irqh", out var irq); P28LimiterScenario.Shape(o, has ? ["tmr2", "irqh"] : ["tmr2"]);
            observations.Add(new(o.GetProperty("tmr2").GetUInt16(), has ? irq.GetByte() : null));
        }
        var n = JsonNode.Parse(json)!; n["purpose"] = P28PostReturnSelectorScenario.PurposeName;
        foreach (var c in n["calls"]!.AsArray()) c!.AsObject().Remove("producerObservation");
        return Create(P28PostReturnSelectorScenario.Parse(n.ToJsonString()), observations);
    }
}
