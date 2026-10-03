using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed record P28Data0136HandoffProducerInitial(ushort Previous00ee, byte Counter00ae, byte Data00b6, byte Data0128, IReadOnlyList<ushort> Samples);
public sealed record P28Data0136HandoffSources(ushort Word011aMask1034, bool Bit0120_0, byte Byte00be, bool Bit00b7_0, byte History013b, byte History013d);
public sealed record P28Data0136HandoffInitial(P28Data0136HandoffProducerInitial Producer, byte Data011f, P28PostStoreInitial FuelPrefix, P28Data0136HandoffSources SoftwareSources);

/// <summary>One initial owner per address. No ready DATA0136, er2, arithmetic or generation setter.</summary>
public sealed class P28Data0136HandoffScenario
{
    private static readonly JsonSerializerOptions Options = new(JsonDefaults.Create()) { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    public const string PurposeName = "data0136-scheduled-division-handoff-test";
    public int FormatVersion => 1;
    public string Purpose => PurposeName;
    public string Provenance { get; }
    public P28Data0136HandoffInitial UnifiedInitialState { get; }
    public IReadOnlyList<P28Data0136TechnicalObservation> ProducerObservations { get; }
    public IReadOnlyList<P28PostStoreCall> FuelCalls { get; }
    public IReadOnlyList<int> TraceEventIndexes { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28Data0136HandoffScenario(P28Data0136HandoffInitial initial, IReadOnlyList<P28Data0136TechnicalObservation> observations, P28PostSelectionCriticalScenario fuel)
    {
        UnifiedInitialState = initial with { Producer = initial.Producer with { Samples = Array.AsReadOnly(initial.Producer.Samples.ToArray()) } };
        ProducerObservations = Array.AsReadOnly(observations.ToArray()); FuelCalls = fuel.Calls; TraceEventIndexes = fuel.TraceCallIndexes; Provenance = fuel.Provenance;
    }
    public static P28Data0136HandoffScenario Create(P28Data0136HandoffInitial initial, IReadOnlyList<P28Data0136TechnicalObservation> observations,
        IReadOnlyList<P28PostStoreCall> calls, string provenance, IReadOnlyList<int>? traces = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Producer); ArgumentNullException.ThrowIfNull(initial.SoftwareSources);
        ArgumentNullException.ThrowIfNull(observations); ArgumentNullException.ThrowIfNull(calls);
        if (observations.Count != calls.Count || calls.Count is < 1 or > 64 || (initial.SoftwareSources.Word011aMask1034 & ~0x1034) != 0)
            throw new ArgumentException("M2w requires dense paired1..64 events and a single011F owner.");
        _ = P28Data0136TechnicalProducerScenario.Create(TechnicalInitial(initial, 0), observations, provenance, traces);
        return new(initial, observations, P28PostSelectionCriticalScenario.Create(initial.FuelPrefix, calls, provenance, traces));
    }
    internal static P28Data0136TechnicalInitialState TechnicalInitial(P28Data0136HandoffInitial s, int pattern) =>
        new(s.Producer.Previous00ee, s.Producer.Counter00ae, s.Producer.Data00b6, s.Data011f, s.Producer.Data0128, (ushort)(pattern * 257), s.Producer.Samples);
    // Independent model adapter ONLY; never supplied to Rust or a second execution machine.
    internal P28CommonResultConsumerScenario ModelScenario(int pattern, IReadOnlyList<P28PostStoreCall>? calls = null)
    {
        var s = UnifiedInitialState.SoftwareSources;
        return P28CommonResultConsumerScenario.Create(new(UnifiedInitialState.FuelPrefix,
            new(s.Word011aMask1034, (UnifiedInitialState.Data011f & 32) != 0, s.Bit0120_0, s.Byte00be, s.Bit00b7_0, (ushort)(pattern * 257), s.History013b, s.History013d)),
            calls ?? FuelCalls, Provenance);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, UnifiedInitialState, ProducerObservations, FuelCalls, TraceEventIndexes };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), new JsonSerializerOptions(Options) { WriteIndented = true });
    public static P28Data0136HandoffScenario Parse(string json)
    {
        ArgumentNullException.ThrowIfNull(json);
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2w scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 15 }); var root = doc.RootElement;
        P28LimiterScenario.Shape(root, "formatVersion", "purpose", "provenance", "unifiedInitialState", "producerObservations", "fuelCalls", "traceEventIndexes");
        if (root.GetProperty("formatVersion").GetInt32() != 1 || root.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2w purpose/version.");
        var initial = root.GetProperty("unifiedInitialState");
        P28LimiterScenario.Shape(initial, "producer", "data011f", "fuelPrefix", "softwareSources");
        P28LimiterScenario.Shape(initial.GetProperty("producer"), "previous00ee", "counter00ae", "data00b6", "data0128", "samples");
        P28LimiterScenario.Shape(initial.GetProperty("softwareSources"), "word011aMask1034", "bit0120_0", "byte00be", "bit00b7_0", "history013b", "history013d");
        foreach (var o in root.GetProperty("producerObservations").EnumerateArray()) P28AcquisitionScenario.Shape(o, ["index", "tmr2", "irqh", "tcon2", "slot"], ["source00f0"]);
        var fuel = new JsonObject
        {
            ["formatVersion"] = 1,
            ["purpose"] = "post-selection-critical-native-software-test",
            ["provenance"] = root.GetProperty("provenance").GetString(),
            ["initialState"] = JsonNode.Parse(initial.GetProperty("fuelPrefix").GetRawText()),
            ["calls"] = JsonNode.Parse(root.GetProperty("fuelCalls").GetRawText()),
            ["traceCallIndexes"] = JsonNode.Parse(root.GetProperty("traceEventIndexes").GetRawText()),
            ["mutation"] = null
        };
        var prefix = P28PostSelectionCriticalScenario.Parse(fuel.ToJsonString());
        return Create(initial.Deserialize<P28Data0136HandoffInitial>(Options)!, root.GetProperty("producerObservations").Deserialize<P28Data0136TechnicalObservation[]>(Options)!, prefix.Calls, prefix.Provenance, prefix.TraceCallIndexes);
    }
}
