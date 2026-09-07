using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28AdaptiveState(P28LimiterState Limiter, byte Timer, byte Counter, ushort Ie, ushort RestoreIe);
public sealed record P28AdaptiveCall(P28LimiterCall Limiter, ushort Raw00ce, bool Bank1, bool Reset217, bool Reset214,
    bool Mode212, bool Enable223, byte RawD9, byte TimerTicks, byte CounterTicks);
public sealed class P28AdaptiveScenario
{
    public int FormatVersion => 1;
    public string Purpose => "adaptive-limiter-software-test";
    public string Provenance { get; }
    public P28AdaptiveState InitialState { get; }
    public IReadOnlyList<P28AdaptiveCall> Calls { get; }
    public string Digest => P28RpmSerialization.Digest(Artifact());
    private P28AdaptiveScenario(P28AdaptiveState initial, IReadOnlyList<P28AdaptiveCall> calls, string provenance)
    { InitialState = initial; Calls = Array.AsReadOnly(calls.ToArray()); Provenance = provenance; }
    public static P28AdaptiveScenario Create(P28AdaptiveState initial, IReadOnlyList<P28AdaptiveCall> calls, string provenance)
    {
        ArgumentNullException.ThrowIfNull(initial); ArgumentNullException.ThrowIfNull(initial.Limiter); ArgumentNullException.ThrowIfNull(calls);
        if (calls.Count is < 1 or > 64 || string.IsNullOrWhiteSpace(provenance) || provenance.Length > 512 ||
            calls.Where((c, i) => c is null || c.Limiter is null || c.Limiter.Index != i || (c.Limiter.ChannelMask & 0xF0) != 0xF0 || c.TimerTicks + c.CounterTicks > 32).Any())
            throw new ArgumentException("Require 1..64 dense calls, <=32 native ticks per call, channel masks with high nibble F and bounded provenance.");
        return new(initial, calls, provenance);
    }
    private object Artifact() => new { FormatVersion, Purpose, Provenance, InitialState, Calls };
    public string ToJson() => JsonSerializer.Serialize(Artifact(), JsonDefaults.Create(true));
    public static P28AdaptiveScenario Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > 1_048_576) throw new InvalidDataException("Adaptive scenario exceeds 1 MiB.");
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 }); var r = doc.RootElement;
        P28LimiterScenario.Shape(r, "formatVersion", "purpose", "provenance", "initialState", "calls");
        if (r.GetProperty("formatVersion").GetInt32() != 1 || r.GetProperty("purpose").GetString() != "adaptive-limiter-software-test") throw new InvalidDataException("Unsupported adaptive version/purpose.");
        StateShape(r.GetProperty("initialState"));
        foreach (var c in r.GetProperty("calls").EnumerateArray())
        {
            P28LimiterScenario.Shape(c, "limiter", "raw00ce", "bank1", "reset217", "reset214", "mode212", "enable223", "rawD9", "timerTicks", "counterTicks");
            P28LimiterScenario.Shape(c.GetProperty("limiter"), "index", "rawPeriod", "p4Bit0", "snapshot011bBit7", "channelMask");
        }
        return Create(r.GetProperty("initialState").Deserialize<P28AdaptiveState>(P28StatefulScenario.Options)!,
            r.GetProperty("calls").Deserialize<P28AdaptiveCall[]>(P28StatefulScenario.Options)!, r.GetProperty("provenance").GetString()!);
    }
    internal static void StateShape(JsonElement e)
    { P28LimiterScenario.Shape(e, "limiter", "timer", "counter", "ie", "restoreIe"); P28LimiterScenario.StateShape(e.GetProperty("limiter")); }
}
