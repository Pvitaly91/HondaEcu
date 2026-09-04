using System.Globalization;
using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> ReadAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("profile");
        command.RequirePositionals(1, "hondaecu read <rom> --profile <id>");
        var profileId = command.Required("profile");
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(profileId);
        var image = await Task.Run(
            () => RomImage.Load(ResolvePath(command.Positionals[0])),
            cancellationToken).ConfigureAwait(false);

        image.ValidateExactSize(profile.ExpectedSize, profile.Id);
        var values = RomParameterReader.ReadAll(image, profile);
        if (values.Count == 0)
        {
            await _output.WriteLineAsync(
                $"No safely decodable parameters are available in profile '{profile.Id}'.")
                .ConfigureAwait(false);
            return Success;
        }

        foreach (var value in values)
        {
            var units = FindUnits(profile, value.ParameterId);
            var access = value.Writable ? "writable" : "read-only";
            await _output.WriteLineAsync(string.Create(
                CultureInfo.InvariantCulture,
                $"{value.ParameterId}\tvalue={value.EngineeringValue:G17} {units}\traw={value.RawValue} (0x{value.RawHex})\toffset=0x{value.Offset:X}\t{Kebab(value.ValidationLevel)}\t{access}"))
                .ConfigureAwait(false);
        }

        return Success;
    }

    private async Task<int> RoundtripAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly("profile");
        command.RequirePositionals(1, "hondaecu roundtrip <rom> --profile <id>");
        var profileId = command.Required("profile");
        var catalog = await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false);
        var profile = catalog.Get(profileId);
        var image = await Task.Run(
            () => RomImage.Load(ResolvePath(command.Positionals[0])),
            cancellationToken).ConfigureAwait(false);

        var roundTripped = RomRoundTripEngine.RoundTrip(image, profile);
        if (!image.Bytes.Span.SequenceEqual(roundTripped.Bytes.Span))
        {
            await _error.WriteLineAsync("error: Round-trip output differs from the input ROM.").ConfigureAwait(false);
            return VerificationFailed;
        }

        var valueCount = profile.Parameters.Count(parameter => parameter.Encoding.Type != ParameterEncodingType.Unsupported) +
            profile.Tables.Where(table => table.Encoding.Type != ParameterEncodingType.Unsupported)
                .Sum(table => checked(table.Rows * table.Columns));
        await _output.WriteLineAsync(
            $"Round-trip passed: {valueCount} value(s), byte-for-byte identical, SHA-256 {image.Hash.Sha256}.")
            .ConfigureAwait(false);
        return Success;
    }

    private static string FindUnits(RomProfile profile, string valueId)
    {
        var scalar = profile.Parameters.FirstOrDefault(
            parameter => string.Equals(parameter.Id, valueId, StringComparison.OrdinalIgnoreCase));
        if (scalar is not null)
        {
            return scalar.Units;
        }

        var bracket = valueId.IndexOf('[', StringComparison.Ordinal);
        var tableId = bracket < 0 ? valueId : valueId[..bracket];
        return profile.Tables.FirstOrDefault(
            table => string.Equals(table.Id, tableId, StringComparison.OrdinalIgnoreCase))?.Units ?? "raw";
    }
}
