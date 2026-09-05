using System.IO;

namespace HondaEcu.Desktop.Services;

/// <summary>No current-directory, repository, private-file, network, or PATH discovery.</summary>
public sealed class DesktopResources
{
    public DesktopResources(string? applicationDirectory = null)
    {
        ApplicationDirectory = Path.GetFullPath(applicationDirectory ?? AppContext.BaseDirectory);
    }

    public string ApplicationDirectory { get; }
    public string DefinitionsDirectory => Path.Combine(ApplicationDirectory, "definitions");
    public string DefaultProfilePath => Path.Combine(DefinitionsDirectory, "p28", "p28-304.experimental.json");
    public string BundledRunnerPath => Path.Combine(ApplicationDirectory, "tools", "p28-slice-runner.exe");
}
