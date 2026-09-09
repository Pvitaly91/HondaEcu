namespace HondaEcu.Core.Tests;

public sealed class P28BasicDesktopProjectionTests
{
    [Fact]
    public void SettingsSerializationAndRecoveryPreserveEverySelectionAndExplicitNull()
    {
        for (var mask = 0; mask < 64; mask++)
        {
            var s = P28BasicCalibrationExportTests.Settings(mask);
            Assert.Equal(s.ToJson(), P28BasicCalibrationSettings.Parse(s.ToJson()).ToJson());
            var p = P28BasicCalibrationExportTests.Preview(s).Plan;
            Assert.Equal(s.ToJson(), P28BasicCalibrationEditor.GetSettings(p).ToJson());
        }
    }
    [Fact]
    public void GraphProjectionUsesExistingDomainAndPreservesEveryIntegerNode()
    {
        var cells = P28BasicCalibrationExportTests.Preview().Plan.Groups[4].Idle!.Cells;
        foreach (var values in new[] { cells, cells.Select(c => c with { NewValue = c.OldValue }).ToArray() })
        {
            var graph = P28IdleTableEditor.ProjectLookup(values); var domain = P28IdleTableEditor.CheckDomain(values);
            Assert.Equal(256, graph.Count); Assert.Equal(domain.Minimum, graph.Min()); Assert.Equal(domain.Maximum, graph.Max());
            foreach (var cell in values) Assert.Equal(cell.NewValue, graph[cell.Axis]);
        }
        Assert.ThrowsAny<Exception>(() => P28IdleTableEditor.ProjectLookup(cells.Select(c => c with { NewValue = 0 }).ToArray()));
    }
}
