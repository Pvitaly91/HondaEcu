using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

/// <summary>Once-only raw software sources and native-counter initial history; no quartet operands.</summary>
public sealed record P28CommonResultConsumerSources(ushort Word011aMask1034, bool Bit011f5, bool Bit0120_0,
    byte Byte00be, bool Bit00b7_0, ushort Word0136, byte History013b, byte History013d);
public sealed record P28CommonResultConsumerInitial(P28PostStoreInitial Prefix, P28CommonResultConsumerSources SoftwareSources);
public sealed class P28CommonResultConsumerScenario
{
    public int FormatVersion => 1;
    public string Purpose => "common-result-consumer-native-software-test";
    public string Provenance { get; }
    public P28CommonResultConsumerInitial InitialState { get; }
    public IReadOnlyList<P28PostStoreCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28PostStoreMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28CommonResultConsumerScenario(P28CommonResultConsumerInitial initial, P28PostSelectionCriticalScenario prefix)
    { InitialState = initial; Calls = prefix.Calls; Provenance = prefix.Provenance; TraceCallIndexes = prefix.TraceCallIndexes; Mutation = prefix.Mutation; }
    public static P28CommonResultConsumerScenario Create(P28CommonResultConsumerInitial initial, IReadOnlyList<P28PostStoreCall> calls,
        string provenance, IReadOnlyList<int>? traces = null, P28PostStoreMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Prefix); ArgumentNullException.ThrowIfNull(initial.SoftwareSources);
        if ((initial.SoftwareSources.Word011aMask1034 & ~0x1034) != 0) throw new ArgumentException("011A source may set only audited mask1034;011B.7 belongs to the existing caller.");
        return new(initial, P28PostSelectionCriticalScenario.Create(initial.Prefix, calls, provenance, traces, mutation));
    }
    internal P28PostSelectionCriticalScenario PrefixScenario => P28PostSelectionCriticalScenario.Create(InitialState.Prefix, Calls, Provenance, TraceCallIndexes, Mutation);
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28CommonResultConsumerScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2s scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 15 }); var root = doc.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "initialState", "calls", "traceCallIndexes", "mutation");
        if (root.GetProperty("formatVersion").GetInt32() != 1 || root.GetProperty("purpose").GetString() != "common-result-consumer-native-software-test") throw new InvalidDataException("Unsupported M2s version/purpose.");
        var initial = root.GetProperty("initialState"); P28LimiterScenario.Shape(initial, "prefix", "softwareSources");
        P28LimiterScenario.Shape(initial.GetProperty("softwareSources"), "word011aMask1034", "bit011f5", "bit0120_0", "byte00be", "bit00b7_0", "word0136", "history013b", "history013d");
        var old = JsonNode.Parse(json)!; old["purpose"] = "post-selection-critical-native-software-test"; old["initialState"] = old["initialState"]!["prefix"]!.DeepClone();
        var prefix = P28PostSelectionCriticalScenario.Parse(old.ToJsonString());
        return Create(initial.Deserialize<P28CommonResultConsumerInitial>(P28StatefulScenario.Options)!, prefix.Calls, prefix.Provenance, prefix.TraceCallIndexes, prefix.Mutation);
    }
}
