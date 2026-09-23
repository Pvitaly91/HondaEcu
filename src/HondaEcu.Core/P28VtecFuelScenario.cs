using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed record P28VtecFuelInitial(byte LoadIndex, byte Map0RpmIndex, byte Map1RpmIndex,
    ushort LoadFraction, ushort Map0RpmFraction, ushort Map1RpmFraction,
    byte ConsumerFactor013f, ushort ConsumerOutput0140);

/// <summary>Only raw software inputs. There is no event map ID, selector, output or host-computed axis position.</summary>
public sealed record P28VtecFuelCall(int Index, byte RawLoad, byte RawMap0Rpm, byte RawMap1Rpm, P28VtecCall Decision);

/// <summary>One code-owned in-memory edit; no arbitrary offset or width is accepted.</summary>
public sealed record P28VtecFuelMutation(string Kind, string? SlotId, string? MapId, int? Row, int? Column, byte Value)
{
    [JsonIgnore]
    public int Offset => Kind switch
    {
        "vtecThreshold" when SlotId is not null && MapId is null && Row is null && Column is null =>
            P28ThresholdLogic.ResolveSlot(SlotId).Offset,
        "fuelCell" when SlotId is null && MapId is not null && Row is not null && Column is not null =>
            P28FuelMapContract.CellOffset(MapId, Row.Value, Column.Value),
        _ => throw new ArgumentException("Mutation must identify exactly one established VTEC slot or fuel cell."),
    };
}

public sealed class P28VtecFuelScenario
{
    private P28VtecFuelScenario(P28VtecPersistentState vtec, P28VtecFuelInitial fuel,
        IReadOnlyList<P28VtecFuelCall> calls, string provenance, P28VtecFuelMutation? mutation,
        IReadOnlyList<int> traces)
    {
        InitialVtec = vtec; InitialFuel = fuel; Calls = Array.AsReadOnly(calls.ToArray());
        Provenance = provenance; Mutation = mutation; TraceCallIndexes = Array.AsReadOnly(traces.ToArray());
        Digest = P28RpmSerialization.Digest(Artifact());
    }
    public int FormatVersion => 1;
    public string Purpose => "explicit-vtec-fuel-native-chain-software-test";
    public string Provenance { get; }
    public P28VtecPersistentState InitialVtec { get; }
    public P28VtecFuelInitial InitialFuel { get; }
    public IReadOnlyList<P28VtecFuelCall> Calls { get; }
    public P28VtecFuelMutation? Mutation { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public string Digest { get; }

    public static P28VtecFuelScenario Create(P28VtecPersistentState vtec, P28VtecFuelInitial fuel,
        IReadOnlyList<P28VtecFuelCall> calls, string provenance, P28VtecFuelMutation? mutation = null,
        IReadOnlyList<int>? traceCallIndexes = null)
    {
        ArgumentNullException.ThrowIfNull(vtec); ArgumentNullException.ThrowIfNull(fuel); ArgumentNullException.ThrowIfNull(calls);
        if (string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512 || calls.Count is < 1 or > 256 ||
            fuel.LoadIndex > 8 || fuel.Map0RpmIndex > 18 || fuel.Map1RpmIndex > 18)
            throw new ArgumentException("Bounded M2f scenario needs 1..256 calls, valid caches and provenance.");
        for (var i = 0; i < calls.Count; i++)
        {
            var call = calls[i]; var d = call?.Decision;
            if (call is null || d is null || call.Index != i || d.Index != i || d.Context is < 0 or > 1 ||
                d.FastTicks is < 0 or > 32 || d.SlowTicks is < 0 or > 32 || (d.Snapshot011C & 0x20) != 0)
                throw new ArgumentException("Dense events require supported direct caller gates and 0..32 native ticks.");
        }
        var traces = traceCallIndexes ?? [];
        if (traces.Count > 8 || traces.Distinct().Count() != traces.Count || traces.Any(i => i < 0 || i >= calls.Count))
            throw new ArgumentException("At most eight unique in-range trace indexes are allowed.");
        if (mutation is not null) _ = mutation.Offset;
        return new(vtec, fuel, calls, provenance, mutation, traces);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialVtec, InitialFuel, Calls, Mutation, TraceCallIndexes };
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(Artifact(), new JsonSerializerOptions(P28StatefulScenario.Options) { WriteIndented = indented });
    public static P28VtecFuelScenario Parse(string json)
    {
        ArgumentNullException.ThrowIfNull(json);
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("M2f scenario exceeds 1 MiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 12 });
        var root = doc.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "initialVtec", "initialFuel", "calls", "mutation", "traceCallIndexes");
        if (root.GetProperty("formatVersion").GetInt32() != 1 || root.GetProperty("purpose").GetString() != "explicit-vtec-fuel-native-chain-software-test")
            throw new InvalidDataException("Unsupported M2f scenario purpose/version.");
        P28StatefulScenario.StateShape(root.GetProperty("initialVtec"));
        P28AcquisitionScenario.Shape(root.GetProperty("initialFuel"), ["loadIndex", "map0RpmIndex", "map1RpmIndex", "loadFraction", "map0RpmFraction", "map1RpmFraction", "consumerFactor013f", "consumerOutput0140"]);
        foreach (var call in root.GetProperty("calls").EnumerateArray())
        {
            P28AcquisitionScenario.Shape(call, ["index", "rawLoad", "rawMap0Rpm", "rawMap1Rpm", "decision"]);
            P28StatefulScenario.CallShape(call.GetProperty("decision"));
        }
        var edit = root.GetProperty("mutation");
        if (edit.ValueKind != JsonValueKind.Null)
            P28LimiterScenario.Shape(edit, "kind", "slotId", "mapId", "row", "column", "value");
        try
        {
            return Create(root.GetProperty("initialVtec").Deserialize<P28VtecPersistentState>(P28StatefulScenario.Options)!,
                root.GetProperty("initialFuel").Deserialize<P28VtecFuelInitial>(P28StatefulScenario.Options)!,
                root.GetProperty("calls").Deserialize<P28VtecFuelCall[]>(P28StatefulScenario.Options)!,
                root.GetProperty("provenance").GetString()!,
                edit.ValueKind == JsonValueKind.Null ? null : edit.Deserialize<P28VtecFuelMutation>(P28StatefulScenario.Options),
                root.GetProperty("traceCallIndexes").Deserialize<int[]>(P28StatefulScenario.Options)!);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or OverflowException)
        { throw new InvalidDataException("Invalid bounded M2f scenario.", ex); }
    }
}
