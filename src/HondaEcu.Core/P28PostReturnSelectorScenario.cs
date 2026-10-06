using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed record P28PostReturnSelectorCall(P28PostStoreCall Prefix);
public sealed class P28PostReturnSelectorScenario
{
    public const string PurposeName = "native-post-return-selector-handoff-test";
    public int FormatVersion => 1;
    public string Purpose => PurposeName;
    public string Provenance => BodyReference.Provenance;
    public P28Word0196HandoffInitial InitialState => BodyReference.InitialState;
    public byte InitialSelector013c { get; }
    public IReadOnlyList<P28PostReturnSelectorCall> Calls { get; }
    public IReadOnlyList<int> TraceEventIndexes => BodyReference.TraceEventIndexes;
    public P28PostStoreMutation? Mutation => BodyReference.Mutation;
    public byte P2OutputLatch => BodyReference.P2OutputLatch;
    public byte Tcon0ArchitecturalSnapshot => BodyReference.Tcon0ArchitecturalSnapshot;
    public byte TrnsitArchitecturalFlags => BodyReference.TrnsitArchitecturalFlags;
    // Input-schema reuse only. These internal selector placeholders are neither
    // serialized by M2ae nor expected operands; the validator owns retained RAM.
    internal P28CalRtRoundTripScenario BodyReference { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28PostReturnSelectorScenario(P28CalRtRoundTripScenario body, byte selector, IReadOnlyList<P28PostReturnSelectorCall> calls)
    { BodyReference = body; InitialSelector013c = selector; Calls = Array.AsReadOnly(calls.ToArray()); }
    public static P28PostReturnSelectorScenario Create(P28Word0196HandoffInitial initial, byte initialSelector013c,
        IReadOnlyList<P28PostReturnSelectorCall> calls, byte p2OutputLatch, byte tcon0ArchitecturalSnapshot, byte trnsitArchitecturalFlags,
        string provenance, IReadOnlyList<int>? traces = null, P28PostStoreMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(calls);
        if (initialSelector013c > 3 || calls.Any(c => c is null || c.Prefix is null)) throw new ArgumentException("M2ae admits one initial selector0..3 and prefix-only calls.");
        var software = P28Word0196AlternateScenario.Create(initial, calls.Select(c => new P28QuartetHandoffCall(c.Prefix, 0)).ToArray(), provenance, traces, mutation);
        return new(P28CalRtRoundTripScenario.Create(P28P2LatchScenario.Create(software, p2OutputLatch), tcon0ArchitecturalSnapshot, trnsitArchitecturalFlags), initialSelector013c, calls);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, InitialSelector013c, Calls, TraceEventIndexes, Mutation, P2OutputLatch, Tcon0ArchitecturalSnapshot, TrnsitArchitecturalFlags };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28PostReturnSelectorScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2ae scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 18 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "initialSelector013c", "calls", "traceEventIndexes", "mutation", "p2OutputLatch", "tcon0ArchitecturalSnapshot", "trnsitArchitecturalFlags");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2ae version/purpose.");
        foreach (var c in r.GetProperty("calls").EnumerateArray()) P28LimiterScenario.Shape(c, "prefix");
        var selector = r.GetProperty("initialSelector013c").GetByte();
        var n = JsonNode.Parse(json)!; n.AsObject().Remove("initialSelector013c"); n["purpose"] = P28CalRtRoundTripScenario.PurposeName;
        foreach (var c in n["calls"]!.AsArray()) c!["selector013c"] = 0;
        var body = P28CalRtRoundTripScenario.Parse(n.ToJsonString());
        return Create(body.InitialState, selector, body.Calls.Select(c => new P28PostReturnSelectorCall(c.Prefix)).ToArray(), body.P2OutputLatch, body.Tcon0ArchitecturalSnapshot, body.TrnsitArchitecturalFlags, body.Provenance, body.TraceEventIndexes, body.Mutation);
    }
}
