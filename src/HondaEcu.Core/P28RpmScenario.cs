using System.Collections.ObjectModel;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace HondaEcu.Core;

/// <summary>Unverified analyst inputs; never a hardware profile or ROM admission.</summary>
public sealed class P28RpmScenario
{
    private P28RpmScenario(IReadOnlyDictionary<string, P28ScalingQuantity> inputs)
    {
        Quantities = new ReadOnlyDictionary<string, P28ScalingQuantity>(inputs.Where(item => item.Key != "rpm")
            .ToDictionary(item => item.Key, item => item.Value, StringComparer.Ordinal));
        LegacyRequestedRpm = inputs.GetValueOrDefault("rpm");
        Digest = P28RpmSerialization.Digest(new { FormatVersion, Scope, Quantities });
    }

    public int FormatVersion => 1;
    public string Scope => "uniform-normal-intervals";
    public IReadOnlyDictionary<string, P28ScalingQuantity> Quantities { get; }
    public P28ScalingQuantity? LegacyRequestedRpm { get; }
    public string Digest { get; }
    public bool PhysicalRpmAvailable => false;
    public string ConfigurationCompatibility => Quantity("timerClockDivisor").CompareTo(new P28ExactNumber(32, 1)) == 0
        ? "Timer divisor matches the source-reviewed CLK/32 selector only; oscillator, routing, event geometry and hardware identity remain unverified."
        : "Counterfactual scenario: supplied timer divisor differs from the source-reviewed CLK/32 configuration. Mathematical results do not assert that the baseline configures this divisor.";
    public IReadOnlyList<string> UnverifiedHardwareDependencies { get; } = Array.AsReadOnly(new[]
    {
        "Matching board identity and oscillator/clock frequency.",
        "Clock routing, capture wiring and events per crankshaft revolution (not camshaft revolution).",
        "Normal valid acquisition mode, event spacing, overflow behavior and coherent non-stale history.",
        "All supplied source/measurement evidence labels are unverified analyst claims here.",
    });

    public string ToJson(bool indented = true)
    {
        var quantities = Quantities.ToDictionary(item => item.Key, item => item.Value, StringComparer.Ordinal);
        if (LegacyRequestedRpm is not null) { quantities.Add("rpm", LegacyRequestedRpm); }
        return JsonSerializer.Serialize(new { FormatVersion, Scope, Quantities = quantities },
            new JsonSerializerOptions(P28RpmSerialization.Options) { WriteIndented = indented });
    }

    public static P28RpmScenario Parse(string json)
    {
        ArgumentNullException.ThrowIfNull(json);
        if (Encoding.UTF8.GetByteCount(json) > 65536)
        {
            throw new InvalidDataException("Scaling assumptions exceed 64 KiB.");
        }
        using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
        return new(P28PhysicalScaling.ReadScenarioQuantities(document.RootElement, optionalRpm: true));
    }

    public static P28RpmScenario Load(string path)
    {
        using var stream = File.OpenRead(path);
        var buffer = new byte[65537];
        var count = 0;
        while (count < buffer.Length)
        {
            var read = stream.Read(buffer, count, buffer.Length - count);
            if (read == 0) { break; }
            count += read;
        }
        if (count > 65536) { throw new InvalidDataException("Scaling assumptions exceed 64 KiB."); }
        return Parse(new UTF8Encoding(false, true).GetString(buffer, 0, count));
    }

    internal P28ExactNumber Quantity(string name) => P28ExactNumber.From(Quantities[name]);
    internal P28ExactNumber TicksRpmProduct => new P28ExactNumber(60, 1) * Quantity("clockHz") /
        Quantity("timerClockDivisor") * Quantity("eventsPerSample") / Quantity("eventsPerCrankRev");
}

/// <summary>An immutable request; a target override never edits the scenario's legacy query.</summary>
public sealed class P28RpmQuery
{
    private P28RpmQuery(P28RpmScenario? scenario, P28ThresholdSlot slot, byte originalRaw,
        P28ScalingQuantity? requestedRpm, string querySource, IReadOnlyList<string> assumptions)
    {
        Scenario = scenario;
        Slot = slot;
        OriginalRaw = originalRaw;
        RequestedRpm = requestedRpm;
        QuerySource = querySource;
        PermittedAssumptions = Array.AsReadOnly(assumptions.ToArray());
        QueryDigest = P28RpmSerialization.Digest(new { ScenarioDigest, Slot, OriginalRaw, RequestedRpm, QuerySource, PermittedAssumptions });
    }

    public P28RpmScenario? Scenario { get; }
    public string? ScenarioDigest => Scenario?.Digest;
    public P28ThresholdSlot Slot { get; }
    public byte OriginalRaw { get; }
    public P28ScalingQuantity? RequestedRpm { get; }
    public string QuerySource { get; }
    public IReadOnlyList<string> PermittedAssumptions { get; }
    public string QueryDigest { get; }

    public static P28RpmQuery Create(P28RpmScenario? scenario, string slotId, byte originalRaw,
        string? targetRpm = null, string? targetProvenance = null, IReadOnlyList<string>? permittedAssumptions = null)
    {
        var assumptions = (permittedAssumptions ?? []).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal).ToArray();
        if (assumptions.Any(value => value is not (P28ProducerModel.AddEr1Assumption or P28RpmPlanner.AddEr3Assumption)))
        {
            throw new ArgumentException("Only the distinct er1 and er3 arithmetic assumptions are permitted.", nameof(permittedAssumptions));
        }
        P28ScalingQuantity? rpm = scenario?.LegacyRequestedRpm;
        var source = rpm is null ? "NotProvided" : "ExplicitSnapshotOfLegacyScalingRpm";
        if (targetRpm is not null)
        {
            var number = P28ExactNumber.ParseInput(targetRpm);
            if (string.IsNullOrWhiteSpace(targetProvenance) || targetProvenance.Length > 512)
            {
                throw new ArgumentException("An explicit target RPM override requires provenance (1..512 characters).", nameof(targetProvenance));
            }
            rpm = new(number.Numerator.ToString(CultureInfo.InvariantCulture), number.Denominator.ToString(CultureInfo.InvariantCulture),
                "crank-revolutions/minute", targetProvenance, "analyst-supplied");
            source = "ExplicitQueryOverride";
        }
        else if (targetProvenance is not null)
        {
            throw new ArgumentException("Target provenance requires an explicit target RPM.", nameof(targetProvenance));
        }
        return new(scenario, P28ThresholdLogic.ResolveSlot(slotId), originalRaw, rpm, source, assumptions);
    }
}

internal readonly record struct P28ExactNumber : IComparable<P28ExactNumber>
{
    public P28ExactNumber(BigInteger numerator, BigInteger denominator)
    {
        if (denominator <= 0) { throw new ArgumentOutOfRangeException(nameof(denominator)); }
        var gcd = BigInteger.GreatestCommonDivisor(numerator, denominator);
        Numerator = numerator / gcd;
        Denominator = denominator / gcd;
    }
    public BigInteger Numerator { get; }
    public BigInteger Denominator { get; }
    public BigInteger Floor => Numerator / Denominator;
    public BigInteger Ceiling => (Numerator + Denominator - 1) / Denominator;
    public static P28ExactNumber From(P28ScalingQuantity value) => new(BigInteger.Parse(value.Numerator, CultureInfo.InvariantCulture), BigInteger.Parse(value.Denominator, CultureInfo.InvariantCulture));
    public static P28ExactNumber ParseInput(string text)
    {
        var fields = text.Split('/');
        if (fields.Length is < 1 or > 2) { throw new ArgumentException("Target RPM must be a positive integer or numerator/denominator."); }
        BigInteger Read(string field)
        {
            if (field.Length is < 1 or > 13 || field.Any(character => character is < '0' or > '9') ||
                !BigInteger.TryParse(field, NumberStyles.None, CultureInfo.InvariantCulture, out var value) || value <= 0 || value > 1_000_000_000_000L)
            { throw new ArgumentException("Target rational components must be decimal integers from 1 through 1000000000000."); }
            return value;
        }
        return new(Read(fields[0]), fields.Length == 1 ? BigInteger.One : Read(fields[1]));
    }
    public int CompareTo(P28ExactNumber other) => (Numerator * other.Denominator).CompareTo(other.Numerator * Denominator);
    public static P28ExactNumber operator *(P28ExactNumber left, P28ExactNumber right) => new(left.Numerator * right.Numerator, left.Denominator * right.Denominator);
    public static P28ExactNumber operator /(P28ExactNumber left, P28ExactNumber right) => new(left.Numerator * right.Denominator, left.Denominator * right.Numerator);
    public static P28ExactNumber operator -(P28ExactNumber left, P28ExactNumber right) => new(left.Numerator * right.Denominator - right.Numerator * left.Denominator, left.Denominator * right.Denominator);
    public P28ExactNumber Abs() => new(BigInteger.Abs(Numerator), Denominator);
    public override string ToString() => $"{Numerator.ToString(CultureInfo.InvariantCulture)}/{Denominator.ToString(CultureInfo.InvariantCulture)}";
}

internal static class P28RpmSerialization
{
    internal static readonly JsonSerializerOptions Options = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase, WriteIndented = false };
    internal static string Digest<T>(T value) => Convert.ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(value, Options))).ToLowerInvariant();
}
