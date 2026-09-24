using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed record P28SharedAxes(byte IgnitionLoadIndex, byte FuelLoadIndex, byte Map0RpmIndex, byte Map1RpmIndex,
    ushort IgnitionLoadFraction, ushort FuelLoadFraction, ushort Map0RpmFraction, ushort Map1RpmFraction);
public sealed record P28SharedState(P28VtecPersistentState Vtec, P28SharedAxes Axes, byte Selector0227,
    byte Factor0247, byte Output0248, byte Factor013f, ushort Output0140, byte Source03c7);
public sealed record P28SharedCall(int Index, byte Source03c7, byte RawLoad, byte RawMap0Rpm,
    byte RawMap1Rpm, P28VtecCall Decision);

public sealed record P28SharedMutation(string Kind, string? SlotId, string? MapId, int? Row, int? Column, byte Value)
{
    [JsonIgnore]
    public int Offset => Kind switch
    {
        "vtecThreshold" when SlotId is not null && MapId is null && Row is null && Column is null =>
            P28ThresholdLogic.ResolveSlot(SlotId).Offset,
        "fuelCell" when SlotId is null && MapId is not null && Row is not null && Column is not null =>
            P28FuelMapContract.CellOffset(MapId, Row.Value, Column.Value),
        "ignitionCell" when SlotId is null && MapId == "ignition_map_0" && Row is not null && Column is not null =>
            P28IgnitionMapContract.CellOffset(MapId, Row.Value, Column.Value),
        _ => throw new ArgumentException("M2h mutation must identify one code-owned threshold, fuel cell, or reachable ignition cell."),
    };
}

/// <summary>One shared axis state, one raw software-input set, no map/selector injection.</summary>
public sealed class P28SharedCalibrationScenario
{
    public int FormatVersion => 1;
    public string Purpose => "shared-axis-vtec-fuel-ignition-software-test";
    public string Provenance { get; }
    public P28SharedState Initial { get; }
    public IReadOnlyList<P28SharedCall> Calls { get; }
    public IReadOnlyList<int> TraceCallIndexes { get; }
    public P28SharedMutation? Mutation { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());

    private P28SharedCalibrationScenario(P28SharedState initial, IReadOnlyList<P28SharedCall> calls,
        IReadOnlyList<int> traces, string provenance, P28SharedMutation? mutation)
    { Initial = initial; Calls = Array.AsReadOnly(calls.ToArray()); TraceCallIndexes = Array.AsReadOnly(traces.ToArray());
        Provenance = provenance; Mutation = mutation; }

    public static P28SharedCalibrationScenario Create(P28SharedState initial, IReadOnlyList<P28SharedCall> calls,
        IReadOnlyList<int> traces, string provenance, P28SharedMutation? mutation = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Vtec);
        ArgumentNullException.ThrowIfNull(initial.Axes); ArgumentNullException.ThrowIfNull(calls);
        ArgumentNullException.ThrowIfNull(traces);
        if (string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512 || calls.Count is < 1 or > 64 ||
            initial.Axes.IgnitionLoadIndex > 8 || initial.Axes.FuelLoadIndex > 8 ||
            initial.Axes.Map0RpmIndex > 18 || initial.Axes.Map1RpmIndex > 18)
            throw new ArgumentException("M2h requires 1..64 dense events, bounded initial caches and provenance.");
        for (var i = 0; i < calls.Count; i++)
        {
            var call = calls[i]; var d = call?.Decision;
            if (call is null || d is null || call.Index != i || d.Index != i || d.Context is < 0 or > 1 ||
                d.FastTicks is < 0 or > 32 || d.SlowTicks is < 0 or > 32 || (d.Snapshot011C & 0x20) != 0)
                throw new ArgumentException("M2h events require one raw axis snapshot and supported bounded VTEC inputs.");
        }
        if (traces.Count > 8 || traces.Any(i => i < 0 || i >= calls.Count) || traces.Distinct().Count() != traces.Count)
            throw new ArgumentException("At most eight unique in-range trace witnesses are allowed.");
        if (mutation is not null) _ = mutation.Offset;
        return new(initial, calls, traces, provenance, mutation);
    }

    private object Artifact() => new { FormatVersion, Purpose, Provenance, Initial, Calls, TraceCallIndexes, Mutation };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));

    public static P28SharedCalibrationScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2h scenario exceeds 256 KiB.");
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 12 });
        var root = document.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "initial", "calls", "traceCallIndexes", "mutation");
        if (root.GetProperty("formatVersion").GetInt32() != 1 || root.GetProperty("purpose").GetString() !=
            "shared-axis-vtec-fuel-ignition-software-test")
            throw new InvalidDataException("Unsupported M2h scenario version/purpose.");
        P28LimiterScenario.Shape(root.GetProperty("initial"), "vtec", "axes", "selector0227", "factor0247", "output0248",
            "factor013f", "output0140", "source03c7");
        P28StatefulScenario.StateShape(root.GetProperty("initial").GetProperty("vtec"));
        P28LimiterScenario.Shape(root.GetProperty("initial").GetProperty("axes"), "ignitionLoadIndex", "fuelLoadIndex",
            "map0RpmIndex", "map1RpmIndex", "ignitionLoadFraction", "fuelLoadFraction", "map0RpmFraction", "map1RpmFraction");
        foreach (var call in root.GetProperty("calls").EnumerateArray())
        {
            P28LimiterScenario.Shape(call, "index", "source03c7", "rawLoad", "rawMap0Rpm", "rawMap1Rpm", "decision");
            P28StatefulScenario.CallShape(call.GetProperty("decision"));
        }
        var edit = root.GetProperty("mutation");
        if (edit.ValueKind != JsonValueKind.Null)
            P28LimiterScenario.Shape(edit, "kind", "slotId", "mapId", "row", "column", "value");
        try
        {
            return Create(root.GetProperty("initial").Deserialize<P28SharedState>(P28StatefulScenario.Options)!,
                root.GetProperty("calls").Deserialize<P28SharedCall[]>(P28StatefulScenario.Options)!,
                root.GetProperty("traceCallIndexes").Deserialize<int[]>(P28StatefulScenario.Options)!,
                root.GetProperty("provenance").GetString()!, edit.ValueKind == JsonValueKind.Null ? null :
                    edit.Deserialize<P28SharedMutation>(P28StatefulScenario.Options));
        }
        catch (Exception exception) when (exception is ArgumentException or InvalidOperationException or OverflowException)
        { throw new InvalidDataException("Invalid bounded M2h scenario.", exception); }
    }
}
