using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28IgnitionSelectorInitial(P28IgnitionMapState Ignition, byte Source03c7);
public sealed record P28IgnitionSelectorCall(int Index, byte Source03c7, byte RawLoad,
    byte RawMap0Rpm, byte RawMap1Rpm);

/// <summary>Closed M2g software-snapshot contract. No event can provide a selector or map ID.</summary>
public sealed class P28IgnitionSelectorScenario
{
    public int FormatVersion => 1;
    public string Purpose => "ignition-native-selector-chain-software-test";
    public string Provenance { get; }
    public P28IgnitionSelectorInitial Initial { get; }
    public IReadOnlyList<P28IgnitionSelectorCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28IgnitionMapMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());

    private P28IgnitionSelectorScenario(P28IgnitionSelectorInitial initial,
        IReadOnlyList<P28IgnitionSelectorCall> calls, IReadOnlyList<int> traceCallIndexes,
        string provenance, P28IgnitionMapMutation? mutation)
    {
        Initial = initial; Calls = Array.AsReadOnly(calls.ToArray());
        TraceCallIndexes = Array.AsReadOnly(traceCallIndexes.ToArray());
        Provenance = provenance; Mutation = mutation;
    }

    public static P28IgnitionSelectorScenario Create(P28IgnitionSelectorInitial initial,
        IReadOnlyList<P28IgnitionSelectorCall> calls, IReadOnlyList<int> traceCallIndexes,
        string provenance, P28IgnitionMapMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Ignition);
        ArgumentNullException.ThrowIfNull(calls); ArgumentNullException.ThrowIfNull(traceCallIndexes);
        if (calls.Count is < 1 or > 64 || calls.Where((call, index) => call is null || call.Index != index).Any())
            throw new ArgumentException("M2g requires 1..64 densely indexed raw events.");
        if (initial.Ignition.LoadIndex > 8 || initial.Ignition.Map0RpmIndex > 18 || initial.Ignition.Map1RpmIndex > 18)
            throw new ArgumentException("Initial native axis caches are outside their intervals.");
        if (traceCallIndexes.Count > 8 || traceCallIndexes.Any(i => i < 0 || i >= calls.Count) ||
            traceCallIndexes.Distinct().Count() != traceCallIndexes.Count)
            throw new ArgumentException("At most eight unique in-range trace witnesses are allowed.");
        if (string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("Bounded nonempty software-test provenance is required.");
        if (mutation is not null) _ = P28IgnitionMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        return new(initial, calls, traceCallIndexes, provenance, mutation);
    }

    private object Artifact() => new { FormatVersion, Purpose, Provenance, Initial, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));

    public static P28IgnitionSelectorScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2g scenario exceeds 256 KiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
        var root = document.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "initial", "calls", "traceCallIndexes", "mutation");
        if (root.GetProperty("formatVersion").GetInt32() != 1 ||
            root.GetProperty("purpose").GetString() != "ignition-native-selector-chain-software-test")
            throw new InvalidDataException("Unsupported M2g scenario version/purpose.");
        P28LimiterScenario.Shape(root.GetProperty("initial"), "ignition", "source03c7");
        P28LimiterScenario.Shape(root.GetProperty("initial").GetProperty("ignition"), "loadIndex", "map0RpmIndex",
            "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "selector0227",
            "consumerFactor0247", "consumerOutput0248");
        foreach (var call in root.GetProperty("calls").EnumerateArray())
            P28LimiterScenario.Shape(call, "index", "source03c7", "rawLoad", "rawMap0Rpm", "rawMap1Rpm");
        var mutation = root.GetProperty("mutation");
        if (mutation.ValueKind != JsonValueKind.Null) P28LimiterScenario.Shape(mutation, "mapId", "row", "column", "value");
        try
        {
            return Create(root.GetProperty("initial").Deserialize<P28IgnitionSelectorInitial>(P28StatefulScenario.Options)!,
                root.GetProperty("calls").Deserialize<P28IgnitionSelectorCall[]>(P28StatefulScenario.Options)!,
                root.GetProperty("traceCallIndexes").Deserialize<int[]>(P28StatefulScenario.Options)!,
                root.GetProperty("provenance").GetString()!, mutation.ValueKind == JsonValueKind.Null ? null :
                    mutation.Deserialize<P28IgnitionMapMutation>(P28StatefulScenario.Options));
        }
        catch (Exception exception) when (exception is ArgumentException or InvalidOperationException or OverflowException)
        { throw new InvalidDataException("Invalid bounded M2g scenario.", exception); }
    }
}
