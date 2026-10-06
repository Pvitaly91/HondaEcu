using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core;

/// <summary>The exact M2ag source schema, with a separate purpose; zero new inputs.</summary>
public sealed class P28Data0136TailScenario
{
    public const string PurposeName = "native-data0136-tail-to-timer-test";
    internal P28FallthroughData0136Scenario Reference { get; }
    public string Purpose => PurposeName;
    public string Digest => P28RpmSerialization.Digest(JsonSerializer.Deserialize<JsonElement>(ToJson()));
    private P28Data0136TailScenario(P28FallthroughData0136Scenario reference) => Reference = reference;
    public static P28Data0136TailScenario Create(P28FallthroughData0136Scenario reference) => new(reference ?? throw new ArgumentNullException(nameof(reference)));
    public string ToJson() { var n = JsonNode.Parse(Reference.ToJson())!; n["purpose"] = PurposeName; return n.ToJsonString(JsonDefaults.Create(true)); }
    public static P28Data0136TailScenario Parse(string json)
    {
        if (System.Text.Encoding.UTF8.GetByteCount(json) > 262_144) throw new InvalidDataException("M2ah scenario exceeds256KiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 18 });
        static void NoDuplicates(JsonElement e)
        {
            if (e.ValueKind == JsonValueKind.Object)
            {
                var names = new HashSet<string>(StringComparer.Ordinal);
                foreach (var field in e.EnumerateObject()) { if (!names.Add(field.Name)) throw new InvalidDataException("Duplicate M2ah field."); NoDuplicates(field.Value); }
            }
            else if (e.ValueKind == JsonValueKind.Array) foreach (var item in e.EnumerateArray()) NoDuplicates(item);
        }
        NoDuplicates(doc.RootElement);
        if (doc.RootElement.GetProperty("purpose").GetString() != PurposeName) throw new InvalidDataException("Unsupported M2ah purpose.");
        var n = JsonNode.Parse(json)!; n["purpose"] = P28FallthroughData0136Scenario.PurposeName;
        return Create(P28FallthroughData0136Scenario.Parse(n.ToJsonString()));
    }
}
