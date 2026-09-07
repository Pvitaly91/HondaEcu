using HondaEcu.Core;

namespace HondaEcu.Cli;

public sealed partial class CliApplication
{
    private sealed record ResearchExportInputs(RomImage Original, RomProfile Profile, P28ExactBaselineBinding Binding,
        VerifiedCompensationLocation Location, string[] Paths, Dictionary<string, byte[]> Snapshot)
    {
        public string Text(string path) => new System.Text.UTF8Encoding(false, true).GetString(Snapshot[path]);
        public void Recheck() => RequireCaptureInputSnapshot(Snapshot);
    }
    private async Task<ResearchExportInputs> CaptureResearchExportAsync(string profileId, string originalPath, string imagePath,
        string bindingPath, string locationPath, string? planPath, string? runnerPath, string? inputReceipt,
        string[] destinations, string[] extraInputs, int receiptLimit, CancellationToken cancellationToken)
    {
        var profile = (await Task.Run(LoadProfileCatalog, cancellationToken).ConfigureAwait(false)).Get(profileId);
        var inputs = new[] { originalPath, imagePath, bindingPath, locationPath, planPath, runnerPath, inputReceipt, profile.SourcePath }.OfType<string>().Concat(extraInputs).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        foreach (var destination in destinations) ProtectNewResearchDestination(destination, inputs);
        for (var i = 0; i < destinations.Length; i++)
            foreach (var other in destinations.Skip(i + 1)) AtomicFile.EnsureDifferentPath(destinations[i], other);
        var snapshot = await Task.Run(() => inputs.ToDictionary(p => p, p => ReadBoundedCaptureInput(p, p == inputReceipt ? receiptLimit : p == runnerPath ? 64 * 1024 * 1024 : 1024 * 1024), StringComparer.OrdinalIgnoreCase), cancellationToken).ConfigureAwait(false);
        var utf8 = new System.Text.UTF8Encoding(false, true);
        if (profile.SourcePath is { } pp && P28VtecInspector.ComputeProfileDigest(profile) != P28VtecInspector.ComputeProfileDigest(RomProfile.Parse(utf8.GetString(snapshot[pp]))))
            throw new InvalidDataException("Profile changed while loading export inputs.");
        var original = RomImage.FromBytes(snapshot[originalPath], originalPath);
        var binding = P28ExactBaselineBinding.Load(bindingPath);
        var location = P28ChecksumPreservingEditor.ParseLocation(utf8.GetString(snapshot[locationPath]).TrimStart('\uFEFF'));
        RequireCaptureInputSnapshot(snapshot);
        return new(original, profile, binding, location, inputs, snapshot);
    }
}
