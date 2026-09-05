using System.Globalization;
using System.Numerics;
using System.Text.Json;

namespace HondaEcu.Core;

public sealed record P28ScalingQuantity(string Numerator, string Denominator, string Unit, string Provenance, string Evidence);
public sealed record P28ScalingPreview(string TimerHz, string RequestedRpm, string IdealTicksPerSample,
    string FloorTicks, string CeilingTicks, IReadOnlyList<ushort> PossibleT, string Scope);
public sealed record P28ScalingAnalysis(string Status, bool PhysicalRpmAvailable, string SymbolicRelationship,
    IReadOnlyList<string> UnresolvedDependencies, IReadOnlyDictionary<string, P28ScalingQuantity>? AnalystInputs,
    P28ScalingPreview? Preview, IReadOnlyList<string> Assumptions)
{
    public IReadOnlyList<string> SourceDerivedConfiguration { get; } =
    [
        "Candidate ROM initializes TCON2 to 0x82 at PC25CC and sets RUN bit4 at PC2615: configured value 0x92, excluding hardware-managed flags.",
        "MSM66201/207 user manual pp81-91: mode C capture, falling edge TM2IO/P3.6, clock selector100=TBC3=CLK/32; timer2 has no external timer-clock input. This identifies configured register behavior, not board identity or oscillator frequency.",
        "Normal acquisition subtracts the previous selected timestamp in00EE from current TMR2, invalidates via TCERR, and writes one interval slot; alternate acquisition uses saved TM2 and overflow accounting, divides by six and fills all slots. Neither acquisition path is executed by this RAM-only slice.",
    ];
}

/// <summary>Explicit dimensional calculation, never a profile or hardware identity assertion.</summary>
public static class P28PhysicalScaling
{
    private const string Relationship = "timerHz = clockHz / timerClockDivisor; ticksPerSample = 60 * timerHz * eventsPerSample / (rpm * eventsPerCrankRev); normal valid G = floor(sum(six interval words)/5), saturated to 65535; zero sample writes fallback 65535. No universal inverse RPM(T).";
    private static readonly string[] Unknowns =
    [
        "Board revision and oscillator/external clock frequency are not established for this archive candidate.",
        "Clock routing, capture-edge wiring and events per crankshaft revolution need matching hardware evidence; cam revolutions are not crank revolutions.",
        "Acquisition mode, overflow handling, event accumulation and sample history must match the selected steady normal-interval scope.",
        "oki.add-er1-a remains a software arithmetic hypothesis; software tests are not physical measurements.",
    ];

    public static P28ScalingAnalysis Analyze(string? scalingPath)
    {
        if (scalingPath is null)
        {
            return new("unavailable-symbolic-only", false, Relationship, Unknowns, null, null, []);
        }
        using var stream = File.OpenRead(scalingPath);
        if (stream.Length > 65536)
        {
            throw new InvalidDataException("Scaling assumptions exceed 64 KiB.");
        }
        // Enforce the bound on bytes actually read, including a concurrently grown file.
        var bytes = new byte[65537];
        var count = 0;
        while (count < bytes.Length)
        {
            var read = stream.Read(bytes, count, bytes.Length - count);
            if (read == 0)
            {
                break;
            }
            count += read;
        }
        if (count > 65536)
        {
            throw new InvalidDataException("Scaling assumptions exceed 64 KiB.");
        }
        using var document = JsonDocument.Parse(bytes.AsMemory(0, count), new JsonDocumentOptions { MaxDepth = 8 });
        return AnalyzeDocument(document.RootElement);
    }

    public static P28ScalingAnalysis AnalyzeDocument(JsonElement root)
    {
        var inputs = ReadScenarioQuantities(root, optionalRpm: false);
        Rational Read(string key)
        {
            var value = inputs[key];
            return new(BigInteger.Parse(value.Numerator, CultureInfo.InvariantCulture), BigInteger.Parse(value.Denominator, CultureInfo.InvariantCulture));
        }
        var clock = Read("clockHz");
        var divisor = Read("timerClockDivisor");
        var events = Read("eventsPerCrankRev");
        var sample = Read("eventsPerSample");
        var rpm = Read("rpm");
        var timer = clock / divisor;
        var ticks = new Rational(60, 1) * timer * sample / (rpm * events);
        var floor = ticks.Numerator / ticks.Denominator;
        var ceiling = (ticks.Numerator + ticks.Denominator - 1) / ticks.Denominator;
        var possible = new SortedSet<ushort>();
        // Normal capture's TCERR invalidates FFFF-or-more, even though a raw
        // ushort can represent FFFF and the software-only G tests include it.
        if (ceiling < ushort.MaxValue)
        {
            for (var highCount = 0; highCount <= 6; highCount++)
            {
                // Conservative quantization envelope, not a claim all phase combinations
                // are dynamically reachable. With any zero, normal G takes its fallback.
                var zero = floor == 0 && highCount < 6;
                var sum = floor * (6 - highCount) + ceiling * highCount;
                possible.Add(zero ? ushort.MaxValue : (ushort)BigInteger.Min(sum / 5, ushort.MaxValue));
            }
        }
        var preview = new P28ScalingPreview(timer.ToString(), rpm.ToString(), ticks.ToString(),
            floor.ToString(CultureInfo.InvariantCulture), ceiling.ToString(CultureInfo.InvariantCulture), possible.ToArray(),
            ceiling >= ushort.MaxValue
                ? "At or beyond normal capture's TCERR FFFF-or-more boundary; no valid-capture, wrap or overflow behavior is invented, so T preview is unavailable."
                : "Conditional steady normal acquisition with six interval words in floor/ceiling tick envelope; arbitrary phase combinations are a conservative superset, not measured RPM. Excludes aggregate-divide-by-six acquisition, stale history and producer alternative mode.");
        return new("conditional-analyst-preview", false, Relationship, Unknowns, inputs, preview,
            ["All supplied quantities and their claimed provenance are unverified analyst inputs, not a trusted profile or measured board identity.",
             "oki.add-er1-a arithmetic hypothesis is used for this mathematical preview only; it grants no byte-execution permission.",
             "Uniform normal interval mode, defined event spacing, no capture overflow/invalid interval, and no mixed-history samples."]);
    }

    // M1h consumes the same strict unit/provenance parser but separates the optional
    // legacy RPM query from the four scenario quantities. M1e still requires RPM.
    internal static IReadOnlyDictionary<string, P28ScalingQuantity> ReadScenarioQuantities(JsonElement root, bool optionalRpm)
    {
        ExactProperties(root, "formatVersion", "scope", "quantities");
        if (root.GetProperty("formatVersion").ValueKind != JsonValueKind.Number ||
            !root.GetProperty("formatVersion").TryGetInt32(out var version) || version != 1 ||
            Text(root.GetProperty("scope")) != "uniform-normal-intervals")
        {
            throw new InvalidDataException("Scaling requires formatVersion 1 and scope uniform-normal-intervals.");
        }
        var quantities = root.GetProperty("quantities");
        if (quantities.ValueKind != JsonValueKind.Object)
        {
            throw new InvalidDataException("Scaling quantities require a JSON object.");
        }
        if (optionalRpm && !quantities.TryGetProperty("rpm", out _))
        {
            ExactProperties(quantities, "clockHz", "timerClockDivisor", "eventsPerCrankRev", "eventsPerSample");
        }
        else
        {
            ExactProperties(quantities, "clockHz", "timerClockDivisor", "eventsPerCrankRev", "eventsPerSample", "rpm");
        }
        var inputs = new Dictionary<string, P28ScalingQuantity>(StringComparer.Ordinal);
        Read("clockHz", "Hz");
        Read("timerClockDivisor", "1");
        Read("eventsPerCrankRev", "events/crank-revolution");
        Read("eventsPerSample", "events/sample");
        if (quantities.TryGetProperty("rpm", out _))
        {
            Read("rpm", "crank-revolutions/minute");
        }
        return new System.Collections.ObjectModel.ReadOnlyDictionary<string, P28ScalingQuantity>(inputs);

        void Read(string key, string unit)
        {
            var element = quantities.GetProperty(key);
            ExactProperties(element, "numerator", "denominator", "unit", "provenance", "evidence");
            var numerator = PositiveInteger(element.GetProperty("numerator"));
            var denominator = PositiveInteger(element.GetProperty("denominator"));
            if (Text(element.GetProperty("unit")) != unit)
            {
                throw new InvalidDataException($"Scaling {key} requires unit {unit}.");
            }
            var provenance = Text(element.GetProperty("provenance"));
            var evidence = Text(element.GetProperty("evidence"));
            if (evidence is not ("analyst-supplied" or "source-derived-claim" or "hardware-measurement-claim"))
            {
                throw new InvalidDataException("Scaling evidence must be an explicit analyst input or unverified source/measurement claim.");
            }
            inputs.Add(key, new(numerator.ToString(CultureInfo.InvariantCulture), denominator.ToString(CultureInfo.InvariantCulture), unit, provenance, evidence));
        }
    }

    private static BigInteger PositiveInteger(JsonElement value)
    {
        var text = Text(value);
        if (text.Length > 13 || text.Any(character => character is < '0' or > '9') ||
            !BigInteger.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out var number) || number <= 0 || number > 1_000_000_000_000L)
        {
            throw new InvalidDataException("Scaling rational components must be decimal strings from 1 through 1000000000000.");
        }
        return number;
    }

    private static string Text(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(value.GetString()) || value.GetString()!.Length > 512)
        {
            throw new InvalidDataException("Scaling string value is missing, empty or too long.");
        }
        return value.GetString()!;
    }

    private static void ExactProperties(JsonElement value, params string[] names)
    {
        if (value.ValueKind != JsonValueKind.Object)
        {
            throw new InvalidDataException("Scaling requires a JSON object.");
        }
        var actual = value.EnumerateObject().Select(property => property.Name).ToArray();
        if (actual.Length != names.Length || actual.Distinct(StringComparer.Ordinal).Count() != names.Length ||
            actual.Except(names, StringComparer.Ordinal).Any())
        {
            throw new InvalidDataException("Scaling contains missing, duplicate or unknown properties.");
        }
    }

    private readonly record struct Rational
    {
        public Rational(BigInteger numerator, BigInteger denominator)
        {
            var gcd = BigInteger.GreatestCommonDivisor(numerator, denominator);
            Numerator = numerator / gcd;
            Denominator = denominator / gcd;
        }
        public BigInteger Numerator { get; }
        public BigInteger Denominator { get; }
        public static Rational operator *(Rational left, Rational right) => new(left.Numerator * right.Numerator, left.Denominator * right.Denominator);
        public static Rational operator /(Rational left, Rational right) => new(left.Numerator * right.Denominator, left.Denominator * right.Numerator);
        public override string ToString() => $"{Numerator.ToString(CultureInfo.InvariantCulture)}/{Denominator.ToString(CultureInfo.InvariantCulture)}";
    }
}
