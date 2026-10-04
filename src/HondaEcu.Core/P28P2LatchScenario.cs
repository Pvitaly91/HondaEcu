using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed class P28P2LatchScenario
{
    public const string PurposeName = "p2-output-latch-handoff-test";
    public int FormatVersion => 1;
    public string Purpose => PurposeName;
    public string Provenance => Software.Provenance;
    public P28Word0196HandoffInitial InitialState => Software.InitialState;
    public IReadOnlyList<P28QuartetHandoffCall> Calls => Software.Calls;
    public IReadOnlyList<int> TraceEventIndexes => Software.TraceEventIndexes;
    public P28PostStoreMutation? Mutation => Software.Mutation;
    public byte P2OutputLatch { get; }
    internal P28Word0196AlternateScenario Software { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28P2LatchScenario(P28Word0196AlternateScenario software, byte latch) { Software = software; P2OutputLatch = latch; }
    public static P28P2LatchScenario Create(P28Word0196AlternateScenario software, byte p2OutputLatch)
    { ArgumentNullException.ThrowIfNull(software); return new(software, p2OutputLatch); }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceEventIndexes, Mutation, P2OutputLatch };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28P2LatchScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2aa scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 18 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceEventIndexes", "mutation", "p2OutputLatch");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2aa version/purpose.");
        var latch = r.GetProperty("p2OutputLatch").GetByte();
        var n = JsonNode.Parse(json)!; n.AsObject().Remove("p2OutputLatch"); n["purpose"] = P28Word0196AlternateScenario.PurposeName;
        return Create(P28Word0196AlternateScenario.Parse(n.ToJsonString()), latch);
    }
}
