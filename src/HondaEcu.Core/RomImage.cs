using System.Security.Cryptography;

namespace HondaEcu.Core;

public sealed class RomImage
{
    private readonly byte[] _bytes;

    private RomImage(byte[] bytes, string? sourcePath)
    {
        _bytes = bytes;
        SourcePath = sourcePath;
        Hash = RomHash.Compute(bytes);
    }

    public int Size => _bytes.Length;

    public RomHash Hash { get; }

    public string? SourcePath { get; }

    // A defensive copy prevents callers from recovering and mutating the private backing array via
    // MemoryMarshal.TryGetArray. Core code uses the internal span to avoid redundant copies.
    public ReadOnlyMemory<byte> Bytes => _bytes.ToArray();

    internal ReadOnlySpan<byte> Span => _bytes;

    public static RomImage Load(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        var fullPath = Path.GetFullPath(path);
        return new RomImage(File.ReadAllBytes(fullPath), fullPath);
    }

    public static RomImage FromBytes(ReadOnlySpan<byte> bytes, string? sourcePath = null) =>
        new(bytes.ToArray(), sourcePath is null ? null : Path.GetFullPath(sourcePath));

    public void ValidateExactSize(int expectedSize, string? profileId = null)
    {
        if (Size != expectedSize)
        {
            var context = profileId is null ? "selected profile" : $"profile '{profileId}'";
            throw new RomSizeException($"Raw ROM size is {Size} bytes; {context} requires exactly {expectedSize} bytes. Padding and truncation are not allowed.");
        }
    }

    public RomImage CreateModifiedCopy(IEnumerable<BytePatch> patches)
    {
        ArgumentNullException.ThrowIfNull(patches);
        var copy = (byte[])_bytes.Clone();
        foreach (var patch in patches)
        {
            if (patch.Offset < 0 || patch.Offset > copy.Length - patch.Bytes.Count)
            {
                throw new ArgumentOutOfRangeException(nameof(patches), $"Patch at 0x{patch.Offset:X} extends beyond the ROM.");
            }

            patch.CopyTo(copy.AsSpan(patch.Offset));
        }

        // Preserve provenance so a modified image cannot later be saved over the input by losing its path.
        return new RomImage(copy, SourcePath);
    }

    public void SaveAsAtomic(string outputPath, bool overwrite = false) =>
        AtomicFile.WriteAllBytes(outputPath, _bytes, SourcePath, overwrite);

    public byte[] ToArray() => (byte[])_bytes.Clone();
}

public sealed record BytePatch
{
    private readonly byte[] _bytes;

    public BytePatch(int offset, ReadOnlySpan<byte> bytes)
    {
        Offset = offset;
        _bytes = bytes.ToArray();
    }

    public int Offset { get; }

    public IReadOnlyList<byte> Bytes => Array.AsReadOnly(_bytes);

    internal void CopyTo(Span<byte> destination) => _bytes.CopyTo(destination);
}

public static class HashUtilities
{
    public static string Sha256(ReadOnlySpan<byte> bytes) =>
        Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    public static string Crc32(ReadOnlySpan<byte> bytes)
    {
        uint crc = uint.MaxValue;
        foreach (var value in bytes)
        {
            crc ^= value;
            for (var bit = 0; bit < 8; bit++)
            {
                crc = (crc >> 1) ^ (0xEDB88320U & (uint)-(int)(crc & 1));
            }
        }

        return (~crc).ToString("X8", System.Globalization.CultureInfo.InvariantCulture);
    }
}

public static class AtomicFile
{
    public static void WriteAllBytes(string outputPath, ReadOnlySpan<byte> contents, string? forbiddenInputPath = null, bool overwrite = false)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(outputPath);
        var destination = Path.GetFullPath(outputPath);
        EnsureDifferentPath(destination, forbiddenInputPath);
        var directory = Path.GetDirectoryName(destination) ?? Directory.GetCurrentDirectory();
        Directory.CreateDirectory(directory);
        if (overwrite)
        {
            throw new NotSupportedException("HondaEcu output is immutable-by-path: overwriting an existing file is not supported.");
        }

        if (File.Exists(destination))
        {
            throw new IOException($"Output file already exists: {destination}");
        }

        var temporary = Path.Combine(directory, $".{Path.GetFileName(destination)}.{Guid.NewGuid():N}.tmp");
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
            {
                stream.Write(contents);
                stream.Flush(flushToDisk: true);
            }

            File.Move(temporary, destination);
        }
        finally
        {
            if (File.Exists(temporary))
            {
                File.Delete(temporary);
            }
        }
    }

    public static void WriteAllText(string outputPath, string contents, bool overwrite = false)
    {
        ArgumentNullException.ThrowIfNull(contents);
        WriteAllBytes(outputPath, System.Text.Encoding.UTF8.GetBytes(contents), null, overwrite);
    }

    public static void EnsureDifferentPath(string outputPath, string? inputPath)
    {
        if (inputPath is null)
        {
            return;
        }

        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (string.Equals(Path.GetFullPath(outputPath), Path.GetFullPath(inputPath), comparison))
        {
            throw new InvalidOperationException("Input and output paths must be different; an input ROM is never overwritten in place.");
        }
    }
}

public sealed class RomSizeException : IOException
{
    public RomSizeException(string message)
        : base(message)
    {
    }
}
