using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

public sealed record P28Data0136TechnicalInitialState(ushort Previous00ee, byte Counter00ae, byte Data00b6,
    byte Data011f, byte Data0128, ushort History0136, IReadOnlyList<ushort> Samples);
public sealed record P28Data0136TechnicalObservation(int Index, ushort Tmr2, byte Irqh, byte Tcon2, byte Slot,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] ushort? Source00f0 = null);

/// <summary>Closed storage-domain stimulus; no per-event output, flags, writer, mode or arbitrary RAM.</summary>
public sealed class P28Data0136TechnicalProducerScenario
{
    private static readonly JsonSerializerOptions Options = new(JsonDefaults.Create()) { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    public const string PurposeName = "data0136-native-technical-producer-test";
    public int FormatVersion => 1;
    public string Purpose => PurposeName;
    public P28Data0136TechnicalInitialState InitialState { get; }
    public IReadOnlyList<P28Data0136TechnicalObservation> Observations { get; }
    public IReadOnlyList<int> TraceObservationIndexes { get; }
    public string Provenance { get; }
    public string Digest { get; }
    private P28Data0136TechnicalProducerScenario(P28Data0136TechnicalInitialState s, IReadOnlyList<P28Data0136TechnicalObservation> observations, string provenance, IReadOnlyList<int> traces)
    {
        InitialState = s with { Samples = Array.AsReadOnly(s.Samples.ToArray()) };
        Observations = Array.AsReadOnly(observations.ToArray()); TraceObservationIndexes = Array.AsReadOnly(traces.ToArray());
        Provenance = provenance; Digest = P28RpmSerialization.Digest(Artifact());
    }
    public static P28Data0136TechnicalProducerScenario Create(P28Data0136TechnicalInitialState initial,
        IReadOnlyList<P28Data0136TechnicalObservation> observations, string provenance, IReadOnlyList<int>? traces = null)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(observations);
        traces ??= [];
        if (initial.Samples is null || initial.Samples.Count != 6 || observations.Count is < 1 or > 256 ||
            string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512 || traces.Count > 8 || traces.Distinct().Count() != traces.Count ||
            traces.Any(i => i < 0 || i >= observations.Count) || observations.Select((o, i) => o is null || o.Index != i || o.Slot > 5 ||
                o.Source00f0.HasValue != ((initial.Data011f & 4) != 0)).Any(invalid => invalid))
            throw new ArgumentException("Invalid closed M2v scenario: mode1 requires explicit word00F0; mode0 forbids it.");
        return new(initial, observations, provenance, traces);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Observations, TraceObservationIndexes };
    public string ToJson(bool indented = true) => JsonSerializer.Serialize(Artifact(), new JsonSerializerOptions(Options) { WriteIndented = indented });
    public static P28Data0136TechnicalProducerScenario Parse(string json)
    {
        ArgumentNullException.ThrowIfNull(json);
        if (Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2v scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 12 }); var r = doc.RootElement;
        P28AcquisitionScenario.Shape(r, ["formatVersion", "purpose", "provenance", "initialState", "observations", "traceObservationIndexes"]);
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2v scenario purpose/version.");
        P28AcquisitionScenario.Shape(r.GetProperty("initialState"), ["previous00ee", "counter00ae", "data00b6", "data011f", "data0128", "history0136", "samples"]);
        foreach (var o in r.GetProperty("observations").EnumerateArray()) P28AcquisitionScenario.Shape(o, ["index", "tmr2", "irqh", "tcon2", "slot"], ["source00f0"]);
        return Create(r.GetProperty("initialState").Deserialize<P28Data0136TechnicalInitialState>(Options)!,
            r.GetProperty("observations").Deserialize<P28Data0136TechnicalObservation[]>(Options)!, r.GetProperty("provenance").GetString()!, r.GetProperty("traceObservationIndexes").Deserialize<int[]>(Options)!);
    }
}
