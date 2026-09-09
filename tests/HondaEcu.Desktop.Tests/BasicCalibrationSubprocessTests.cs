using System.IO;
using System.Text.Json;
using HondaEcu.Core;

namespace HondaEcu.Desktop.Tests;

/// <summary>Real child process probes, not mocked Desktop jobs or Honda execution.</summary>
public sealed class BasicCalibrationSubprocessTests
{
    private static string Runner
    {
        get
        {
            for (var d = new DirectoryInfo(AppContext.BaseDirectory); d is not null; d = d.Parent)
                if (File.Exists(Path.Combine(d.FullName, "Directory.Build.props")))
                {
                    var path = Path.Combine(d.FullName, "rust", "p28-slice-runner", "target", "release", "p28-slice-runner.exe");
                    Assert.True(File.Exists(path), "Build the pinned Rust runner; missing integration is not a silent skip."); return path;
                }
            throw new DirectoryNotFoundException("Test repository not found.");
        }
    }
    [Fact, Trait("Category", "RealRustSubprocess")]
    public async Task RealBoundedAdapterRunsInventedProgramAndReportsOperationAndVersion()
    {
        // Independently authored byte move/store probe, no OEM program.
        var response = await SeededSliceProcess.ExchangeAsync(Runner, new
        {
            protocolVersion = 1,
            operation = "synthetic",
            images = new[] { new { id = "desktop-invented-probe", rom = new[] { 0x77, 73, 0xD5, 0xC4 } } },
            allowAssumptions = Array.Empty<string>(),
            scratchPatterns = new[] { 85 },
            synthetic = new
            {
                entryPc = 0,
                exitPcs = new[] { 4 },
                allowedCodeRanges = new[] { new[] { 0, 4 } },
                psw = 0x0101,
                lrb = 0x40,
                usp = 0x180,
                instructionBudget = 8,
                dataSeeds = Array.Empty<int[]>(),
                outputAddresses = new[] { 0xC4 }
            }
        });
        Assert.Equal("synthetic", response.Response.GetProperty("operation").GetString());
        Assert.Equal("0.11.0", response.Response.GetProperty("runnerVersion").GetString());
        var r = response.Response.GetProperty("syntheticResult"); Assert.Equal(0, r.GetProperty("status").GetInt32());
        Assert.Equal(73, r.GetProperty("outputs")[0].GetInt32());
    }
    [Fact, Trait("Category", "RealRustSubprocess")]
    public async Task MissingExecutableCannotBeReportedAsValidation()
    {
        var e = await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync(Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".exe"), new { protocolVersion = 1 }));
        Assert.Equal(SliceProcessFailure.Start, e.Failure);
    }
    [Fact, Trait("Category", "RealRustSubprocess")]
    public async Task RealRunnerRejectsWrongOperationAndProtocol()
    {
        foreach (var request in new[] { new { protocolVersion = 2, operation = "vtecThresholdPrefix" }, new { protocolVersion = 1, operation = "not-an-operation" } })
            await Assert.ThrowsAsync<SliceProcessException>(() => SeededSliceProcess.ExchangeAsync(Runner, request));
    }
}
