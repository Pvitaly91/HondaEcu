using System.Text;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

/// <summary>Closed M2t source contract; sole DATA0136 field is reused, not duplicated.</summary>
public sealed class P28DivisionDecisionScenario
{
    public const string ScenarioPurpose = "division-decision-native-software-test";
    public int FormatVersion => 1;
    public string Purpose => ScenarioPurpose;
    public string Provenance => Sources.Provenance;
    public P28CommonResultConsumerInitial InitialState => Sources.InitialState;
    public IReadOnlyList<P28PostStoreCall> Calls => Sources.Calls;
    public IReadOnlyList<int> TraceCallIndexes => Sources.TraceCallIndexes;
    public P28PostStoreMutation? Mutation => Sources.Mutation;
    public string Digest => P28RpmSerialization.Digest(JsonNode.Parse(ToJson())!);
    internal P28CommonResultConsumerScenario Sources { get; }
    private P28DivisionDecisionScenario(P28CommonResultConsumerScenario sources) => Sources = sources;
    public static P28DivisionDecisionScenario Create(P28CommonResultConsumerInitial initial, IReadOnlyList<P28PostStoreCall> calls,
        string provenance, IReadOnlyList<int>? traces = null, P28PostStoreMutation? mutation = null)
        => new(P28CommonResultConsumerScenario.Create(initial, calls, provenance, traces, mutation));
    public string ToJson()
    {
        var n = JsonNode.Parse(Sources.ToJson())!; n["purpose"] = Purpose; return n.ToJsonString(JsonDefaults.Create(true));
    }
    public static P28DivisionDecisionScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2t scenario exceeds256KiB.");
        var n = JsonNode.Parse(json, documentOptions: new() { MaxDepth = 15 })!;
        if (n["purpose"]?.GetValue<string>() != ScenarioPurpose) throw new InvalidDataException("Unsupported M2t purpose.");
        // Validate original JSON before changing purpose so duplicate fields cannot be normalized away.
        var historical = json.Replace("\"" + ScenarioPurpose + "\"", "\"common-result-consumer-native-software-test\"", StringComparison.Ordinal);
        return new(P28CommonResultConsumerScenario.Parse(historical));
    }
}
