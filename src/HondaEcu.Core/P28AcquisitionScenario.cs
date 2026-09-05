using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HondaEcu.Core;

/// <summary>Bounded, untrusted test stimulus. It confers no ROM or hardware authority.</summary>
public sealed class P28AcquisitionScenario
{
    private const int MaximumBytes = 1_048_576;
    private static readonly JsonSerializerOptions Options = new(JsonDefaults.Create())
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    private P28AcquisitionScenario(P28AcquisitionState initialState, IReadOnlyList<P28CaptureObservation> observations,
        string provenance, IReadOnlyList<int> traces, P28CaptureTimeline? timeline)
    {
        InitialState = P28AcquisitionModel.Snapshot(initialState);
        Observations = Array.AsReadOnly(observations.ToArray());
        Provenance = provenance;
        TraceObservationIndexes = Array.AsReadOnly(traces.ToArray());
        Timeline = timeline?.Snapshot();
        Timeline?.Validate(Observations);
        Digest = P28RpmSerialization.Digest(Artifact());
    }

    public int FormatVersion => 1;
    public string Purpose => "explicit-capture-observation-stimulus";
    public P28AcquisitionState InitialState { get; }
    public IReadOnlyList<P28CaptureObservation> Observations { get; }
    public IReadOnlyList<int> TraceObservationIndexes { get; }
    public string Provenance { get; }
    public P28CaptureTimeline? Timeline { get; }
    public string Digest { get; }

    public static P28AcquisitionScenario Create(P28AcquisitionState initialState,
        IReadOnlyList<P28CaptureObservation> observations, string provenance,
        IReadOnlyList<int>? traceObservationIndexes = null, P28CaptureTimeline? timeline = null)
    {
        ArgumentNullException.ThrowIfNull(observations);
        if (observations.Count is < 1 or > 1024 || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512)
        {
            throw new ArgumentException("A scenario requires 1..1024 observations and 1..512 characters of explicit provenance.");
        }
        for (var i = 0; i < observations.Count; i++)
        {
            P28AcquisitionModel.ValidateObservation(observations[i]);
            if (observations[i].Index != i) { throw new ArgumentException("Observation indexes must be dense and ordered from zero."); }
        }
        var traces = traceObservationIndexes ?? [];
        if (traces.Count > 8 || traces.Distinct().Count() != traces.Count || traces.Any(index => index < 0 || index >= observations.Count))
        {
            throw new ArgumentException("At most eight unique, in-range trace indexes are allowed.");
        }
        return new(initialState, observations, provenance, traces, timeline);
    }

    public P28AcquisitionScenario ForReplay(int lastObservationIndex)
    {
        if (lastObservationIndex < 0 || lastObservationIndex >= Observations.Count) { throw new ArgumentOutOfRangeException(nameof(lastObservationIndex)); }
        return Create(InitialState, Observations.Take(lastObservationIndex + 1).ToArray(), Provenance,
            [lastObservationIndex], Timeline?.Prefix(lastObservationIndex + 1));
    }

    private Dictionary<string, object> Artifact()
    {
        var artifact = new Dictionary<string, object>(StringComparer.Ordinal)
        {
            ["formatVersion"] = FormatVersion,
            ["purpose"] = Purpose,
            ["provenance"] = Provenance,
            ["initialState"] = InitialState,
            ["observations"] = Observations,
            ["traceObservationIndexes"] = TraceObservationIndexes,
        };
        if (Timeline is not null) { artifact.Add("timeline", Timeline); }
        return artifact;
    }

    public string ToJson(bool indented = true) => JsonSerializer.Serialize(Artifact(), new JsonSerializerOptions(Options) { WriteIndented = indented });

    public static P28AcquisitionScenario Parse(string json)
    {
        ArgumentNullException.ThrowIfNull(json);
        if (Encoding.UTF8.GetByteCount(json) > MaximumBytes) { throw new InvalidDataException("Capture scenario exceeds 1 MiB."); }
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 12 });
        var root = document.RootElement;
        Shape(root, ["formatVersion", "purpose", "provenance", "initialState", "observations", "traceObservationIndexes"], ["timeline"]);
        if (root.GetProperty("formatVersion").GetInt32() != 1 || root.GetProperty("purpose").GetString() != "explicit-capture-observation-stimulus")
        { throw new InvalidDataException("Unsupported capture scenario version or purpose."); }
        Shape(root.GetProperty("initialState"), ["previousTimestamp", "samples", "data0128", "data00AE", "data00B6", "data011F", "previousT", "data0217", "data0231", "data0136"]);
        foreach (var observation in root.GetProperty("observations").EnumerateArray())
        {
            Shape(observation, ["index", "tmr2", "irqh", "tcon2", "slot", "compose", "thresholdContext", "thresholdPriorBits", "thresholdEnabled"]);
        }
        P28CaptureTimeline? timeline = null;
        if (root.TryGetProperty("timeline", out var timelineElement))
        {
            Shape(timelineElement, ["originTicks", "phase", "periods", "quantization", "provenance"]);
            Shape(timelineElement.GetProperty("phase"), ["numerator", "denominator"]);
            foreach (var period in timelineElement.GetProperty("periods").EnumerateArray()) { Shape(period, ["numerator", "denominator"]); }
            timeline = timelineElement.Deserialize<P28CaptureTimeline>(Options) ?? throw new InvalidDataException("Missing timeline.");
        }
        return Create(root.GetProperty("initialState").Deserialize<P28AcquisitionState>(Options)!,
            root.GetProperty("observations").Deserialize<P28CaptureObservation[]>(Options)!,
            root.GetProperty("provenance").GetString()!, root.GetProperty("traceObservationIndexes").Deserialize<int[]>(Options)!, timeline);
    }

    internal static void Shape(JsonElement element, string[] required, string[]? optional = null)
    {
        if (element.ValueKind != JsonValueKind.Object) { throw new InvalidDataException("Capture scenario object required."); }
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in element.EnumerateObject())
        {
            if (!seen.Add(property.Name) || (!required.Contains(property.Name, StringComparer.Ordinal) && !(optional ?? []).Contains(property.Name, StringComparer.Ordinal)) || property.Value.ValueKind == JsonValueKind.Null)
            { throw new InvalidDataException("Duplicate, unknown or null capture scenario field."); }
        }
        if (required.Any(name => !seen.Contains(name))) { throw new InvalidDataException("Missing required capture scenario field."); }
    }

    public static P28AcquisitionScenario Load(string path)
    {
        using var stream = File.OpenRead(path);
        var bytes = new byte[MaximumBytes + 1];
        var count = 0;
        while (count < bytes.Length)
        {
            var read = stream.Read(bytes, count, bytes.Length - count);
            if (read == 0) { break; }
            count += read;
        }
        if (count > MaximumBytes) { throw new InvalidDataException("Capture scenario exceeds 1 MiB."); }
        return Parse(new UTF8Encoding(false, true).GetString(bytes, 0, count));
    }
}
