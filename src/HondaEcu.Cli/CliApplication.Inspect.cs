using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private async Task<int> InspectAsync(string[] args, CancellationToken cancellationToken)
    {
        var command = CommandLine.Parse(args);
        command.EnsureOnly();
        command.RequirePositionals(1, "hondaecu inspect <rom>");

        var image = await Task.Run(
            () => RomImage.Load(ResolvePath(command.Positionals[0])),
            cancellationToken).ConfigureAwait(false);
        var bytes = image.ToArray();
        var zeroCount = 0;
        var erasedCount = 0;
        foreach (var value in bytes)
        {
            zeroCount += value == 0 ? 1 : 0;
            erasedCount += value == byte.MaxValue ? 1 : 0;
        }

        IReadOnlyList<RomProfile> possibleProfiles;
        try
        {
            possibleProfiles = RomIdentifier.FindPossibleProfiles(image, LoadProfileCatalog().Profiles);
        }
        catch (InvalidOperationException)
        {
            possibleProfiles = [];
        }

        await _output.WriteLineAsync($"Size: {image.Size} bytes").ConfigureAwait(false);
        await _output.WriteLineAsync($"SHA-256: {image.Hash.Sha256}").ConfigureAwait(false);
        await _output.WriteLineAsync($"CRC32: {image.Hash.Crc32}").ConfigureAwait(false);
        await _output.WriteLineAsync($"0x00 bytes: {zeroCount}").ConfigureAwait(false);
        await _output.WriteLineAsync($"0xFF bytes: {erasedCount}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Preview: {Hex(bytes.AsSpan(0, Math.Min(32, bytes.Length)))}").ConfigureAwait(false);
        await _output.WriteLineAsync($"Possible profiles: {(possibleProfiles.Count == 0 ? "none" : string.Join(", ", possibleProfiles.Select(profile => profile.Id)))}")
            .ConfigureAwait(false);

        if (possibleProfiles.Count == 0)
        {
            await _error.WriteLineAsync(
                "warning: ROM is not identified by a trusted hash or signature; file size alone is not an identity.")
                .ConfigureAwait(false);
        }

        return Success;
    }
}
