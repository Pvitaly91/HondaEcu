using System.Diagnostics;
using System.IO;
using System.Text.Json;
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
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "THIRD_PARTY_NOTICES.md")) &&
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "docs", "D1_BASIC_CALIBRATION_DESKTOP.md")) &&
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "docs", "M1T_BASIC_CALIBRATION_EXPORT.md")) &&
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "docs", "D2_CALIBRATION_MAPS_DESKTOP.md")) &&
                    File.Exists(Path.Combine(resources.ApplicationDirectory, "docs", "M2E_UNIFIED_CALIBRATION_EXPORT.md")) &&
                    RunnerHasM2eOperations(resources.BundledRunnerPath);
                Shutdown(complete ? 0 : 1);
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or System.Text.Json.JsonException or ArgumentException or System.ComponentModel.Win32Exception)
            {
                Shutdown(1);
            }
            return;
        }

        base.OnStartup(e);
        new MainWindow().Show();
    }

    private static bool RunnerHasM2eOperations(string path)
    {
        if (!File.Exists(path)) return false;
        using var process = new Process();
        process.StartInfo = new ProcessStartInfo(path, "--capabilities")
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = AppContext.BaseDirectory
        };
        process.Start();
        var output = process.StandardOutput.ReadToEndAsync();
        if (!process.WaitForExit(10000)) { process.Kill(true); return false; }
        if (process.ExitCode != 0) return false;
        using var json = JsonDocument.Parse(output.GetAwaiter().GetResult());
        var root = json.RootElement;
        if (root.GetProperty("protocolVersion").GetInt32() != 1) return false;
        var operations = root.GetProperty("operations").EnumerateArray().Select(item => item.GetString()).ToHashSet(StringComparer.Ordinal);
        return new[] { "vtecThresholdPrefix", "vtecThresholdControl", "limiterSequence", "adaptiveLimiter",
            "idleTarget", "fuelMapLookup", "ignitionMapLookup", "checksumBatch" }.All(operations.Contains);
    }
}
