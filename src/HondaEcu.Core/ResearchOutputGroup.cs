namespace HondaEcu.Core;

/// <summary>Shared three-file staging and best-effort rollback. Not power-loss atomicity.</summary>
internal static class ResearchOutputGroup
{
    internal static (string[] Sources, Action Recheck) CaptureInputs(RomImage original, RomProfile profile,
        string profileDigest, IEnumerable<string>? protectedPaths)
    {
        var sources = (protectedPaths ?? []).Concat(new[] { original.SourcePath, profile.SourcePath }.OfType<string>()).ToArray();
        var snapshot = sources.Distinct().ToDictionary(s => s, File.ReadAllBytes);
        void Recheck()
        {
            foreach (var item in snapshot)
                if (!item.Value.AsSpan().SequenceEqual(File.ReadAllBytes(item.Key))) throw new InvalidDataException("Protected input changed before publication.");
            if (original.SourcePath is { } path && !RomImage.Load(path).Span.SequenceEqual(original.Span)) throw new InvalidDataException("Original changed after validation.");
            if (profile.SourcePath is { } pp && P28VtecInspector.ComputeProfileDigest(RomProfile.Load(pp)) != profileDigest) throw new InvalidDataException("Profile changed after validation.");
        }
        return (sources, Recheck);
    }
    internal static T Write<T>(RomImage image, string planJson, string reportJson, string outputPath, string planPath,
        string reportPath, IEnumerable<string> protectedPaths, Action requireCurrentInputs, Func<string[], T> readback,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var destinations = new[] { outputPath, planPath, reportPath }.Select(Path.GetFullPath).ToArray();
        var sources = protectedPaths.ToArray();
        for (var index = 0; index < destinations.Length; index++)
        {
            foreach (var other in destinations.Skip(index + 1).Concat(sources)) AtomicFile.EnsureDifferentPath(destinations[index], other);
            if (File.Exists(destinations[index]) || Directory.Exists(destinations[index]))
                throw new IOException("Each BIN, plan and receipt destination must be a new file.");
        }
        requireCurrentInputs();
        cancellationToken.ThrowIfCancellationRequested();
        AtomicFile.WriteAllText(destinations[1], planJson);
        try
        {
            // After publication begins, finish rollback/readback, not cancellation midway through a group.
            AtomicOutputPair.Write(destinations[0], image.Span, destinations[2], reportJson, overwrite: false);
        }
        catch (Exception publicationError)
        {
            try
            {
                if (File.Exists(destinations[1]) && File.ReadAllText(destinations[1]) == planJson) File.Delete(destinations[1]);
            }
            catch (Exception rollbackError) when (rollbackError is IOException or UnauthorizedAccessException)
            { throw new AggregateException("Publication failed; newly published plan rollback also failed.", publicationError, rollbackError); }
            throw;
        }
        return readback(destinations);
    }
}
