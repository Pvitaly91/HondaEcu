using System.Runtime.InteropServices;
using System.Text;

namespace HondaEcu.Core.Tests;

public sealed class RomImageTests
{
    [Fact]
    public void ComputesKnownSha256AndCrc32()
    {
        var image = RomImage.FromBytes(Encoding.ASCII.GetBytes("123456789"));

        Assert.Equal("15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225", image.Hash.Sha256);
        Assert.Equal("CBF43926", image.Hash.Crc32);
        Assert.Equal(9, image.Size);
    }

    [Fact]
    public void OwnsInputAndDoesNotExposeMutableBackingArray()
    {
        var source = new byte[] { 1, 2, 3 };
        var image = RomImage.FromBytes(source);
        source[0] = 99;
        var exported = image.Bytes;
        Assert.True(MemoryMarshal.TryGetArray(exported, out var segment));
        segment.Array![segment.Offset] = 88;

        Assert.Equal(new byte[] { 1, 2, 3 }, image.ToArray());
    }

    [Fact]
    public void ModifiedCopyLeavesOriginalUnchangedAndTracksNewHash()
    {
        var original = RomImage.FromBytes(new byte[] { 1, 2, 3, 4 });
        var modified = original.CreateModifiedCopy(new[] { new BytePatch(1, new byte[] { 9, 8 }) });

        Assert.Equal(new byte[] { 1, 2, 3, 4 }, original.ToArray());
        Assert.Equal(new byte[] { 1, 9, 8, 4 }, modified.ToArray());
        Assert.NotEqual(original.Hash, modified.Hash);
    }

    [Fact]
    public void ModifiedCopyCannotLoseProvenanceAndOverwriteOriginal()
    {
        using var fixture = new SyntheticFixture();
        var path = fixture.WriteRom("input.dat", new byte[] { 1, 2, 3 });
        var modified = RomImage.Load(path).CreateModifiedCopy(new[] { new BytePatch(0, new byte[] { 9 }) });

        Assert.Throws<InvalidOperationException>(() => modified.SaveAsAtomic(path, overwrite: true));
        Assert.Equal(new byte[] { 1, 2, 3 }, File.ReadAllBytes(path));
    }

    [Fact]
    public void RejectsWrongRawSizeWithoutPaddingOrTruncation()
    {
        var image = RomImage.FromBytes(new byte[32767]);

        var exception = Assert.Throws<RomSizeException>(() => image.ValidateExactSize(32768, "synthetic"));
        Assert.Contains("exactly 32768", exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void RefusesToOverwriteInputPath()
    {
        using var fixture = new SyntheticFixture();
        var path = fixture.WriteRom("input.dat", new byte[] { 1, 2, 3 });
        var image = RomImage.Load(path);

        Assert.Throws<InvalidOperationException>(() => image.SaveAsAtomic(path, overwrite: true));
        Assert.Equal(new byte[] { 1, 2, 3 }, File.ReadAllBytes(path));
    }

    [Fact]
    public void AtomicSaveCreatesCompleteNewOutputAndNoTemporaryFile()
    {
        using var fixture = new SyntheticFixture();
        var input = fixture.WriteRom("input.dat", new byte[] { 1, 2, 3 });
        var output = fixture.PathFor("output.dat");
        RomImage.Load(input).SaveAsAtomic(output);

        Assert.Equal(new byte[] { 1, 2, 3 }, File.ReadAllBytes(output));
        Assert.DoesNotContain(Directory.EnumerateFiles(fixture.DirectoryPath), path => path.EndsWith(".tmp", StringComparison.Ordinal));
    }
}
