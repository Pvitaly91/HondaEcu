namespace HondaEcu.Core.Tests;

public sealed class P28DesktopCopyWriterTests
{
    [Fact]
    public void PublishesThreeNewFilesAndIndependentlyReloadsTheirLineage()
    {
        using var fixture = new SyntheticFixture();
        var result = Result(fixture);
        var output = fixture.PathFor("child.dat");
        var plan = fixture.PathFor("plan.json");
        var report = fixture.PathFor("report.json");
        Assert.True(P28DesktopCopyWriter.Save(result, output, plan, report).IsValid);
        Assert.True(P28DesktopCopyWriter.VerifySavedCopy(result, output, plan, report).IsValid);

        // Independent re-read detects unplanned bytes even though the original
        // in-memory result remains valid.
        var bytes = File.ReadAllBytes(output);
        bytes[0] ^= 1;
        File.WriteAllBytes(output, bytes);
        Assert.False(P28DesktopCopyWriter.VerifySavedCopy(result, output, plan, report).IsValid);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    public void RefusesEveryExistingOrProtectedDestinationBeforePublishingAnything(int index)
    {
        using var fixture = new SyntheticFixture();
        var result = Result(fixture);
        var paths = new[] { fixture.PathFor("child.dat"), fixture.PathFor("plan.json"), fixture.PathFor("report.json") };
        Assert.Throws<InvalidOperationException>(() => P28DesktopCopyWriter.Save(result,
            paths[0], paths[1], paths[2], [paths[index]]));
        Assert.All(paths, path => Assert.False(File.Exists(path)));
        File.WriteAllText(paths[index], "existing user file");
        Assert.Throws<IOException>(() => P28DesktopCopyWriter.Save(result, paths[0], paths[1], paths[2]));
        Assert.Equal("existing user file", File.ReadAllText(paths[index]));
        Assert.All(paths.Where((_, position) => position != index), path => Assert.False(File.Exists(path)));
    }

    [Fact]
    public void RefusesAliasedDestinationsAndOriginalSource()
    {
        using var fixture = new SyntheticFixture();
        var result = Result(fixture);
        var output = fixture.PathFor("child.dat");
        var report = fixture.PathFor("report.json");
        Assert.Throws<InvalidOperationException>(() => P28DesktopCopyWriter.Save(result, output, output, report));
        Assert.Throws<InvalidOperationException>(() => P28DesktopCopyWriter.Save(result, output, fixture.PathFor("original.dat"), report));
        Assert.False(File.Exists(output));
        Assert.False(File.Exists(report));
    }

    [Fact]
    public void PairPublicationFailureRollsBackOnlyTheNewPlan()
    {
        using var fixture = new SyntheticFixture();
        var result = Result(fixture);
        var parentFile = fixture.PathFor("not-a-directory");
        File.WriteAllText(parentFile, "preserved");
        var output = Path.Combine(parentFile, "child.dat");
        var plan = fixture.PathFor("plan.json");
        var report = fixture.PathFor("report.json");
        Assert.ThrowsAny<IOException>(() => P28DesktopCopyWriter.Save(result, output, plan, report));
        Assert.False(File.Exists(plan));
        Assert.False(File.Exists(report));
        Assert.Equal("preserved", File.ReadAllText(parentFile));
        Assert.Empty(Directory.GetFiles(fixture.DirectoryPath, "*.tmp", SearchOption.AllDirectories));
    }

    [Fact]
    public void ReadbackDetectsOriginalParentChangedOnDiskAndMalformedPlan()
    {
        using var fixture = new SyntheticFixture();
        var result = Result(fixture);
        var output = fixture.PathFor("child.dat");
        var plan = fixture.PathFor("plan.json");
        var report = fixture.PathFor("report.json");
        Assert.True(P28DesktopCopyWriter.Save(result, output, plan, report).IsValid);
        var parent = fixture.PathFor("original.dat");
        var bytes = File.ReadAllBytes(parent);
        bytes[0] ^= 1;
        File.WriteAllBytes(parent, bytes);
        Assert.False(P28DesktopCopyWriter.VerifySavedCopy(result, output, plan, report).IsValid);
        File.WriteAllText(plan, "{}");
        Assert.ThrowsAny<Exception>(() => P28DesktopCopyWriter.VerifySavedCopy(result, output, plan, report));
    }

    private static P28RawThresholdPatchResult Result(SyntheticFixture fixture)
    {
        var path = fixture.WriteRom("original.dat", SyntheticFixture.Bytes());
        var baseline = RomImage.Load(path);
        var profile = new RomProfile("p28-304", "Synthetic only", "Invented test fixture", 32768,
            "synthetic", true, true, checksum: new ChecksumDefinition("unknown", ChecksumStatus.Unknown, 0, 0,
                ValidationLevel.PublicDocumentation));
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, baseline.Size,
            baseline.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        var plan = P28RawThresholdEditor.CreatePlan(baseline, profile, binding, true, P28ThresholdLogic.GetSlots()[0].Id, 128);
        return P28RawThresholdEditor.Apply(baseline, profile, binding, plan);
    }
}
