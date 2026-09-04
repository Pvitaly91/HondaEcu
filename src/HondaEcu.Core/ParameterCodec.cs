using System.Buffers.Binary;

namespace HondaEcu.Core;

public static class ParameterCodec
{
    public static int? RequiredWidth(ParameterEncodingType type) => type switch
    {
        ParameterEncodingType.RawU8 or ParameterEncodingType.RawS8 or
        ParameterEncodingType.LinearU8 or ParameterEncodingType.InverseU8 => 1,
        ParameterEncodingType.RawU16LittleEndian or ParameterEncodingType.RawU16BigEndian or
        ParameterEncodingType.LinearU16 or ParameterEncodingType.InverseU16 => 2,
        ParameterEncodingType.LookupTable or ParameterEncodingType.Unsupported => null,
        _ => throw new ArgumentOutOfRangeException(nameof(type)),
    };

    public static ParameterValue Decode(ScalarParameterDefinition definition, ReadOnlySpan<byte> romBytes)
    {
        ArgumentNullException.ThrowIfNull(definition);
        EnsureBounds(definition.Offset, definition.Width, romBytes.Length);
        if (definition.Encoding.Type == ParameterEncodingType.Unsupported)
        {
            throw new NotSupportedException($"Parameter '{definition.Id}' has Unsupported encoding and cannot be decoded.");
        }

        var bytes = romBytes.Slice(definition.Offset, definition.Width);
        var raw = ReadRaw(definition.Encoding.Type, definition.Endianness, bytes);
        var engineering = DecodeEngineering(definition.Encoding, raw);
        if (!double.IsFinite(engineering))
        {
            throw new ParameterEncodingException($"Parameter '{definition.Id}' decoded to a non-finite value.");
        }

        return new ParameterValue(definition.Id, engineering, raw, HexUtilities.Format(bytes), definition.Offset,
            definition.ValidationLevel, definition.Writable);
    }

    public static byte[] Encode(ScalarParameterDefinition definition, double engineeringValue)
    {
        ArgumentNullException.ThrowIfNull(definition);
        return EncodeCore(definition, engineeringValue, validateRanges: true);
    }

    public static IReadOnlyList<ParameterValue> DecodeTable(TableParameterDefinition definition, ReadOnlySpan<byte> romBytes)
    {
        ArgumentNullException.ThrowIfNull(definition);
        EnsureBounds(definition.Offset, definition.Width, romBytes.Length);
        var values = new List<ParameterValue>(definition.Rows * definition.Columns);
        for (var cell = 0; cell < definition.Rows * definition.Columns; cell++)
        {
            var scalar = AsCell(definition, cell);
            values.Add(Decode(scalar, romBytes));
        }

        return values;
    }

    public static byte[] EncodeTable(TableParameterDefinition definition, IReadOnlyList<double> engineeringValues)
    {
        ArgumentNullException.ThrowIfNull(definition);
        ArgumentNullException.ThrowIfNull(engineeringValues);
        var cellCount = checked(definition.Rows * definition.Columns);
        if (engineeringValues.Count != cellCount)
        {
            throw new ArgumentException($"Table '{definition.Id}' requires exactly {cellCount} values.", nameof(engineeringValues));
        }

        var result = new byte[definition.Width];
        for (var cell = 0; cell < cellCount; cell++)
        {
            var scalar = AsCell(definition, cell) with { };
            var encoded = Encode(scalar, engineeringValues[cell]);
            encoded.CopyTo(result, cell * definition.CellWidth);
        }

        return result;
    }

    internal static byte[] Reencode(ScalarParameterDefinition definition, ParameterValue decoded) =>
        EncodeCore(definition, decoded.EngineeringValue, validateRanges: false);

    private static byte[] EncodeCore(ScalarParameterDefinition definition, double engineeringValue, bool validateRanges)
    {
        if (definition.Encoding.Type == ParameterEncodingType.Unsupported)
        {
            throw new NotSupportedException($"Parameter '{definition.Id}' has Unsupported encoding and cannot be encoded.");
        }

        if (!double.IsFinite(engineeringValue))
        {
            throw new ParameterValueOutOfRangeException($"Parameter '{definition.Id}' requires a finite value.");
        }

        if (validateRanges && (engineeringValue < definition.EngineeringMinimum || engineeringValue > definition.EngineeringMaximum))
        {
            throw new ParameterValueOutOfRangeException(
                $"Value {engineeringValue} for '{definition.Id}' is outside engineering range [{definition.EngineeringMinimum}, {definition.EngineeringMaximum}].");
        }

        var unrounded = definition.Encoding.Type == ParameterEncodingType.LookupTable
            ? LookupRaw(definition.Encoding.Values, engineeringValue, definition.RoundingPolicy)
            : EncodeEngineering(definition.Encoding, engineeringValue);
        var rounded = ApplyRounding(unrounded, definition.RoundingPolicy);
        if (validateRanges && (rounded < definition.RawMinimum || rounded > definition.RawMaximum))
        {
            throw new ParameterValueOutOfRangeException(
                $"Encoded raw value {rounded} for '{definition.Id}' is outside raw range [{definition.RawMinimum}, {definition.RawMaximum}].");
        }

        return WriteRaw(definition.Encoding.Type, definition.Endianness, rounded, definition.Encoding.Values.Count, definition.Width);
    }

    private static long ReadRaw(ParameterEncodingType type, Endianness endianness, ReadOnlySpan<byte> bytes) => type switch
    {
        ParameterEncodingType.RawU8 or ParameterEncodingType.LinearU8 or ParameterEncodingType.InverseU8 or
            ParameterEncodingType.LookupTable when bytes.Length == 1 => bytes[0],
        ParameterEncodingType.RawS8 => unchecked((sbyte)bytes[0]),
        ParameterEncodingType.RawU16LittleEndian => BinaryPrimitives.ReadUInt16LittleEndian(bytes),
        ParameterEncodingType.RawU16BigEndian => BinaryPrimitives.ReadUInt16BigEndian(bytes),
        ParameterEncodingType.LinearU16 or ParameterEncodingType.InverseU16 or ParameterEncodingType.LookupTable
            when bytes.Length == 2 && endianness == Endianness.Little => BinaryPrimitives.ReadUInt16LittleEndian(bytes),
        ParameterEncodingType.LinearU16 or ParameterEncodingType.InverseU16 or ParameterEncodingType.LookupTable
            when bytes.Length == 2 && endianness == Endianness.Big => BinaryPrimitives.ReadUInt16BigEndian(bytes),
        _ => throw new ParameterEncodingException($"Encoding {type}, width {bytes.Length}, and endianness {endianness} are incompatible."),
    };

    private static double DecodeEngineering(ParameterEncoding encoding, long raw) => encoding.Type switch
    {
        ParameterEncodingType.RawU8 or ParameterEncodingType.RawS8 or
            ParameterEncodingType.RawU16LittleEndian or ParameterEncodingType.RawU16BigEndian => raw,
        ParameterEncodingType.LinearU8 or ParameterEncodingType.LinearU16 => (raw * encoding.Scale) + encoding.Offset,
        ParameterEncodingType.InverseU8 or ParameterEncodingType.InverseU16 =>
            encoding.Numerator / (raw + encoding.DenominatorOffset) + encoding.Offset,
        ParameterEncodingType.LookupTable when raw >= 0 && raw < encoding.Values.Count => encoding.Values[(int)raw],
        ParameterEncodingType.LookupTable => throw new ParameterEncodingException($"Lookup-table raw index {raw} is outside its values array."),
        ParameterEncodingType.Unsupported => throw new NotSupportedException("Unsupported encoding cannot be decoded."),
        _ => throw new ArgumentOutOfRangeException(nameof(encoding)),
    };

    private static double EncodeEngineering(ParameterEncoding encoding, double engineering) => encoding.Type switch
    {
        ParameterEncodingType.RawU8 or ParameterEncodingType.RawS8 or
            ParameterEncodingType.RawU16LittleEndian or ParameterEncodingType.RawU16BigEndian => engineering,
        ParameterEncodingType.LinearU8 or ParameterEncodingType.LinearU16 => (engineering - encoding.Offset) / encoding.Scale,
        ParameterEncodingType.InverseU8 or ParameterEncodingType.InverseU16 when engineering != encoding.Offset =>
            (encoding.Numerator / (engineering - encoding.Offset)) - encoding.DenominatorOffset,
        ParameterEncodingType.InverseU8 or ParameterEncodingType.InverseU16 =>
            throw new ParameterEncodingException("Inverse encoding is singular at its engineering offset."),
        ParameterEncodingType.LookupTable => throw new InvalidOperationException("Lookup encoding requires a declared rounding policy."),
        ParameterEncodingType.Unsupported => throw new NotSupportedException("Unsupported encoding cannot be encoded."),
        _ => throw new ArgumentOutOfRangeException(nameof(encoding)),
    };

    private static double LookupRaw(IReadOnlyList<double> values, double engineering, RoundingPolicy roundingPolicy)
    {
        if (values.Count == 0)
        {
            throw new ParameterEncodingException("Lookup-table encoding has no values.");
        }

        if (roundingPolicy == RoundingPolicy.Exact)
        {
            for (var index = 0; index < values.Count; index++)
            {
                if (Math.Abs(values[index] - engineering) <= 1e-9)
                {
                    return index;
                }
            }

            throw new ParameterEncodingException($"Value {engineering} is not present in the lookup table.");
        }

        if (roundingPolicy != RoundingPolicy.Nearest)
        {
            throw new ParameterEncodingException("Lookup-table encoding supports only Exact or Nearest rounding.");
        }

        var bestIndex = 0;
        var bestDistance = Math.Abs(values[0] - engineering);
        for (var index = 1; index < values.Count; index++)
        {
            var distance = Math.Abs(values[index] - engineering);
            if (distance < bestDistance)
            {
                bestDistance = distance;
                bestIndex = index;
            }
        }

        return bestIndex;
    }

    private static long ApplyRounding(double value, RoundingPolicy policy)
    {
        if (!double.IsFinite(value) || value < long.MinValue || value > long.MaxValue)
        {
            throw new ParameterValueOutOfRangeException($"Raw encoded value {value} cannot be represented as an integer.");
        }

        var rounded = policy switch
        {
            RoundingPolicy.Exact when Math.Abs(value - Math.Round(value)) <= 1e-9 => Math.Round(value),
            RoundingPolicy.Exact => throw new ParameterEncodingException($"Exact rounding required, but encoded value {value} is fractional."),
            RoundingPolicy.Nearest => Math.Round(value, MidpointRounding.AwayFromZero),
            RoundingPolicy.ToEven => Math.Round(value, MidpointRounding.ToEven),
            RoundingPolicy.Floor => Math.Floor(value),
            RoundingPolicy.Ceiling => Math.Ceiling(value),
            RoundingPolicy.Truncate => Math.Truncate(value),
            _ => throw new ArgumentOutOfRangeException(nameof(policy)),
        };
        return checked((long)rounded);
    }

    private static byte[] WriteRaw(ParameterEncodingType type, Endianness endianness, long raw, int lookupCount, int width)
    {
        switch (type)
        {
            case ParameterEncodingType.RawS8:
                if (raw is < sbyte.MinValue or > sbyte.MaxValue)
                {
                    throw new ParameterValueOutOfRangeException($"Raw signed-byte value {raw} is outside [-128, 127].");
                }

                return new[] { unchecked((byte)(sbyte)raw) };
            case ParameterEncodingType.RawU8:
            case ParameterEncodingType.LinearU8:
            case ParameterEncodingType.InverseU8:
                EnsureUnsigned(raw, byte.MaxValue);
                return new[] { (byte)raw };
            case ParameterEncodingType.LookupTable when width == 1 && lookupCount <= 256:
                EnsureUnsigned(raw, Math.Min(byte.MaxValue, lookupCount - 1));
                return new[] { (byte)raw };
            case ParameterEncodingType.RawU16LittleEndian:
                return WriteUInt16(raw, littleEndian: true);
            case ParameterEncodingType.RawU16BigEndian:
                return WriteUInt16(raw, littleEndian: false);
            case ParameterEncodingType.LinearU16:
            case ParameterEncodingType.InverseU16:
            case ParameterEncodingType.LookupTable when width == 2:
                return endianness switch
                {
                    Endianness.Little => WriteUInt16(raw, littleEndian: true),
                    Endianness.Big => WriteUInt16(raw, littleEndian: false),
                    _ => throw new ParameterEncodingException($"Encoding {type} requires explicit little or big endianness."),
                };
            default:
                throw new NotSupportedException($"Encoding {type} cannot be written.");
        }
    }

    private static byte[] WriteUInt16(long raw, bool littleEndian)
    {
        EnsureUnsigned(raw, ushort.MaxValue);
        var bytes = new byte[2];
        if (littleEndian)
        {
            BinaryPrimitives.WriteUInt16LittleEndian(bytes, (ushort)raw);
        }
        else
        {
            BinaryPrimitives.WriteUInt16BigEndian(bytes, (ushort)raw);
        }

        return bytes;
    }

    private static void EnsureUnsigned(long value, long maximum)
    {
        if (value < 0 || value > maximum)
        {
            throw new ParameterValueOutOfRangeException($"Raw value {value} is outside [0, {maximum}].");
        }
    }

    private static void EnsureBounds(int offset, int width, int available)
    {
        if (offset < 0 || width <= 0 || offset > available - width)
        {
            throw new ArgumentOutOfRangeException(nameof(offset), "Parameter bytes are outside the supplied ROM.");
        }
    }

    private static ScalarParameterDefinition AsCell(TableParameterDefinition definition, int cell) =>
        new($"{definition.Id}[{cell}]", definition.DisplayName, definition.Description,
            checked(definition.Offset + (cell * definition.CellWidth)), definition.CellWidth, definition.Endianness,
            definition.Encoding, definition.Units, definition.RawMinimum, definition.RawMaximum,
            definition.EngineeringMinimum, definition.EngineeringMaximum, definition.RoundingPolicy, definition.Writable,
            definition.ValidationLevel, definition.RevisionScope, definition.Sources, definition.Notes, definition.Status);
}

public static class RomParameterReader
{
    public static IReadOnlyList<ParameterValue> ReadAll(RomImage image, RomProfile profile)
    {
        ArgumentNullException.ThrowIfNull(image);
        ArgumentNullException.ThrowIfNull(profile);
        image.ValidateExactSize(profile.ExpectedSize, profile.Id);
        var scalars = profile.Parameters
            .Where(parameter => parameter.Encoding.Type != ParameterEncodingType.Unsupported)
            .Select(parameter => ParameterCodec.Decode(parameter, image.Span))
            .ToList();
        foreach (var table in profile.Tables.Where(table => table.Encoding.Type != ParameterEncodingType.Unsupported))
        {
            scalars.AddRange(ParameterCodec.DecodeTable(table, image.Span));
        }

        return scalars;
    }
}

public static class RomRoundTripEngine
{
    public static RomImage RoundTrip(RomImage image, RomProfile profile)
    {
        ArgumentNullException.ThrowIfNull(image);
        ArgumentNullException.ThrowIfNull(profile);
        image.ValidateExactSize(profile.ExpectedSize, profile.Id);
        var patches = new List<BytePatch>();
        foreach (var parameter in profile.Parameters.Where(item => item.Encoding.Type != ParameterEncodingType.Unsupported))
        {
            var decoded = ParameterCodec.Decode(parameter, image.Span);
            var encoded = ParameterCodec.Reencode(parameter, decoded);
            var original = image.Span.Slice(parameter.Offset, parameter.Width);
            if (!original.SequenceEqual(encoded))
            {
                throw new ParameterEncodingException(
                    $"Round-trip for '{parameter.Id}' changed {HexUtilities.Format(original)} to {HexUtilities.Format(encoded)}.");
            }

            patches.Add(new BytePatch(parameter.Offset, encoded));
        }

        foreach (var table in profile.Tables.Where(item => item.Encoding.Type != ParameterEncodingType.Unsupported))
        {
            var decoded = ParameterCodec.DecodeTable(table, image.Span);
            var encoded = ParameterCodec.EncodeTable(table, decoded.Select(value => value.EngineeringValue).ToArray());
            var original = image.Span.Slice(table.Offset, table.Width);
            if (!original.SequenceEqual(encoded))
            {
                throw new ParameterEncodingException(
                    $"Round-trip for table '{table.Id}' changed {HexUtilities.Format(original)} to {HexUtilities.Format(encoded)}.");
            }

            patches.Add(new BytePatch(table.Offset, encoded));
        }

        return image.CreateModifiedCopy(patches);
    }
}

public sealed class ParameterEncodingException : Exception
{
    public ParameterEncodingException(string message)
        : base(message)
    {
    }
}

public sealed class ParameterValueOutOfRangeException : ArgumentOutOfRangeException
{
    public ParameterValueOutOfRangeException(string message)
        : base(paramName: null, message)
    {
    }
}
