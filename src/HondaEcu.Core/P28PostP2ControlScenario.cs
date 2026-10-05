using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

public sealed class P28PostP2ControlScenario
{
    public const string PurposeName = "post-p2-control-register-test";
    public int FormatVersion => 1;
    public string Purpose => PurposeName;
    public string Provenance => P2.Provenance;
    public P28Word0196HandoffInitial InitialState => P2.InitialState;
    public IReadOnlyList<P28QuartetHandoffCall> Calls => P2.Calls;
    public IReadOnlyList<int> TraceEventIndexes => P2.TraceEventIndexes;
    public P28PostStoreMutation? Mutation => P2.Mutation;
    public byte P2OutputLatch => P2.P2OutputLatch;
    public byte Tcon0ArchitecturalSnapshot { get; }
    public byte TrnsitArchitecturalFlags { get; }
    internal P28P2LatchScenario P2 { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28PostP2ControlScenario(P28P2LatchScenario p2, byte tcon0, byte flags)
    { P2 = p2; Tcon0ArchitecturalSnapshot = tcon0; TrnsitArchitecturalFlags = flags; }
    public static P28PostP2ControlScenario Create(P28P2LatchScenario p2, byte tcon0ArchitecturalSnapshot, byte trnsitArchitecturalFlags)
    {
        ArgumentNullException.ThrowIfNull(p2);
        if ((tcon0ArchitecturalSnapshot & ~0x0C) != 0x83 || trnsitArchitecturalFlags > 15)
            throw new InvalidDataException("M2ab admits only stopped realtime-output TCON0 (83/87/8B/8F) and TRNSIT flags0..15.");
        return new(p2, tcon0ArchitecturalSnapshot, trnsitArchitecturalFlags);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceEventIndexes, Mutation, P2OutputLatch, Tcon0ArchitecturalSnapshot, TrnsitArchitecturalFlags };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28PostP2ControlScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2ab scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 18 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceEventIndexes", "mutation", "p2OutputLatch", "tcon0ArchitecturalSnapshot", "trnsitArchitecturalFlags");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2ab version/purpose.");
        var n = JsonNode.Parse(json)!; n.AsObject().Remove("tcon0ArchitecturalSnapshot"); n.AsObject().Remove("trnsitArchitecturalFlags"); n["purpose"] = P28P2LatchScenario.PurposeName;
        return Create(P28P2LatchScenario.Parse(n.ToJsonString()), r.GetProperty("tcon0ArchitecturalSnapshot").GetByte(), r.GetProperty("trnsitArchitecturalFlags").GetByte());
    }
}
