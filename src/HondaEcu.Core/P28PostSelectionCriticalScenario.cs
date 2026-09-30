using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

/// <summary>One authoritative M2p initial state and source snapshots; no downstream result inputs.</summary>
public sealed class P28PostSelectionCriticalScenario
{
    public int FormatVersion => 1;
    public string Purpose => "post-selection-critical-native-software-test";
    public string Provenance { get; }
    public P28PostStoreInitial InitialState { get; }
    public IReadOnlyList<P28PostStoreCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28PostStoreMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28PostSelectionCriticalScenario(P28PostStoreConsumerScenario prefix)
    { InitialState = prefix.InitialState; Calls = prefix.Calls; Provenance = prefix.Provenance; TraceCallIndexes = prefix.TraceCallIndexes; Mutation = prefix.Mutation; }
    public static P28PostSelectionCriticalScenario Create(P28PostStoreInitial initial, IReadOnlyList<P28PostStoreCall> calls,
        string provenance, IReadOnlyList<int>? traces = null, P28PostStoreMutation? mutation = null) =>
        new(P28PostStoreConsumerScenario.Create(initial, calls, provenance, traces, mutation));
    internal P28PostStoreConsumerScenario PrefixScenario => P28PostStoreConsumerScenario.Create(InitialState, Calls, Provenance, TraceCallIndexes, Mutation);
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28PostSelectionCriticalScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2r scenario exceeds 256 KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 14 }); var root = doc.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (root.GetProperty("formatVersion").GetInt32() != 1 || root.GetProperty("purpose").GetString() != "post-selection-critical-native-software-test")
            throw new InvalidDataException("Unsupported M2r version/purpose.");
        // The historical parser proves the exact same closed source/initial/mutation schema.
        var old = JsonNode.Parse(json)!; old["purpose"] = "post-store-consumer-native-software-test";
        return new(P28PostStoreConsumerScenario.Parse(old.ToJsonString()));
    }
}
