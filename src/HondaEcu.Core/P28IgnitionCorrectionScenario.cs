using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28IgnitionCorrectionInitial(P28IgnitionMapState Ignition, byte Source03c7,
    byte Floor024c, byte Bias0249, byte Retained035b, byte Retained024a,
    bool Gate0234Bit5, bool Gate0217Bit0, bool Gate021eBit0);
public sealed record P28IgnitionCorrectionCall(int Index, byte Source03c7, byte RawLoad,
    byte RawMap0Rpm, byte RawMap1Rpm, byte Correction0245, byte Correction0246);

/// <summary>Closed raw software-snapshot schedule; no DATA0248 or expected result is supplied.</summary>
public sealed class P28IgnitionCorrectionScenario
{
    public int FormatVersion => 1;
    public string Purpose => "ignition-correction-chain-raw-software-test";
    public string Provenance { get; }
    public P28IgnitionCorrectionInitial Initial { get; }
    public IReadOnlyList<P28IgnitionCorrectionCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28IgnitionMapMutation? Mutation { get; }
    public bool PermitAddEr3Assumption { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());

    private P28IgnitionCorrectionScenario(P28IgnitionCorrectionInitial initial,
        IReadOnlyList<P28IgnitionCorrectionCall> calls, IReadOnlyList<int> traceCallIndexes,
        string provenance, P28IgnitionMapMutation? mutation, bool permitAddEr3Assumption)
    {
        Initial = initial; Calls = Array.AsReadOnly(calls.ToArray());
        TraceCallIndexes = Array.AsReadOnly(traceCallIndexes.ToArray());
        Provenance = provenance; Mutation = mutation; PermitAddEr3Assumption = permitAddEr3Assumption;
    }

    public static P28IgnitionCorrectionScenario Create(P28IgnitionCorrectionInitial initial,
        IReadOnlyList<P28IgnitionCorrectionCall> calls, IReadOnlyList<int> traceCallIndexes,
        string provenance, P28IgnitionMapMutation? mutation = null, bool permitAddEr3Assumption = false)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Ignition);
        ArgumentNullException.ThrowIfNull(calls); ArgumentNullException.ThrowIfNull(traceCallIndexes);
        if (calls.Count is < 1 or > 64 || calls.Where((call, index) => call is null || call.Index != index).Any())
            throw new ArgumentException("M2i requires 1..64 densely indexed events.");
        if (initial.Ignition.LoadIndex > 8 || initial.Ignition.Map0RpmIndex > 18 || initial.Ignition.Map1RpmIndex > 18)
            throw new ArgumentException("Initial native axis caches are outside their intervals.");
        if (traceCallIndexes.Count > 8 || traceCallIndexes.Any(i => i < 0 || i >= calls.Count) ||
            traceCallIndexes.Distinct().Count() != traceCallIndexes.Count)
            throw new ArgumentException("At most eight unique in-range traces are allowed.");
        if (string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
            throw new ArgumentException("Bounded nonempty raw software provenance is required.");
        if (mutation is not null && mutation.MapId != "ignition_map_0")
            throw new ArgumentException("M2i A/B permits only one code-owned ignition_map_0 cell.");
        if (mutation is not null) _ = P28IgnitionMapContract.CellOffset(mutation.MapId, mutation.Row, mutation.Column);
        return new(initial, calls, traceCallIndexes, provenance, mutation, permitAddEr3Assumption);
    }

    private object Artifact() => new
    {
        FormatVersion,
        Purpose,
        Provenance,
        Initial,
        Calls,
        TraceCallIndexes,
        Mutation,
        PermitAddEr3Assumption
    };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));

    public static P28IgnitionCorrectionScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2i scenario exceeds 256 KiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
        var root = document.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "initial", "calls",
            "traceCallIndexes", "mutation", "permitAddEr3Assumption");
        if (root.GetProperty("formatVersion").GetInt32() != 1 ||
            root.GetProperty("purpose").GetString() != "ignition-correction-chain-raw-software-test")
            throw new InvalidDataException("Unsupported M2i scenario version/purpose.");
        P28LimiterScenario.Shape(root.GetProperty("initial"), "ignition", "source03c7", "floor024c",
            "bias0249", "retained035b", "retained024a", "gate0234Bit5", "gate0217Bit0", "gate021eBit0");
        P28LimiterScenario.Shape(root.GetProperty("initial").GetProperty("ignition"), "loadIndex", "map0RpmIndex",
            "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "selector0227",
            "consumerFactor0247", "consumerOutput0248");
        foreach (var call in root.GetProperty("calls").EnumerateArray())
            P28LimiterScenario.Shape(call, "index", "source03c7", "rawLoad", "rawMap0Rpm",
                "rawMap1Rpm", "correction0245", "correction0246");
        var mutation = root.GetProperty("mutation");
        if (mutation.ValueKind != JsonValueKind.Null)
            P28LimiterScenario.Shape(mutation, "mapId", "row", "column", "value");
        try
        {
            return Create(root.GetProperty("initial").Deserialize<P28IgnitionCorrectionInitial>(P28StatefulScenario.Options)!,
                root.GetProperty("calls").Deserialize<P28IgnitionCorrectionCall[]>(P28StatefulScenario.Options)!,
                root.GetProperty("traceCallIndexes").Deserialize<int[]>(P28StatefulScenario.Options)!,
                root.GetProperty("provenance").GetString()!, mutation.ValueKind == JsonValueKind.Null ? null :
                    mutation.Deserialize<P28IgnitionMapMutation>(P28StatefulScenario.Options),
                root.GetProperty("permitAddEr3Assumption").GetBoolean());
        }
        catch (Exception exception) when (exception is ArgumentException or InvalidOperationException or OverflowException)
        { throw new InvalidDataException("Invalid bounded M2i scenario.", exception); }
    }
}
