using System.IO;
using System.Windows;
using HondaEcu.Core;
using HondaEcu.Desktop.Services;

namespace HondaEcu.Desktop;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        if (e.Args is ["--check-portable-resources"])
        {
            // Explicit packaging diagnostic: do not create a window, scan for
            // ROMs, run the executable, or imply that this is a GUI smoke test.
            var resources = new DesktopResources();
            try
            {
                var profile = RomProfile.Load(resources.DefaultProfilePath);
                var complete = profile.Id == P28ExactBaselineBinding.RequiredProfileId &&
                    File.Exists(resources.BundledRunnerPath) &&
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "coreclr.dll")) &&
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "PresentationFramework.dll")) &&
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "THIRD_PARTY_NOTICES.md"));
                Shutdown(complete ? 0 : 1);
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or System.Text.Json.JsonException or ArgumentException)
            {
                Shutdown(1);
            }
            return;
        }

        base.OnStartup(e);
        new MainWindow().Show();
    }
}
