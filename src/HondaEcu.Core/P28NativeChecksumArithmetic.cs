namespace HondaEcu.Core;

/// <summary>
/// Independent unsigned integer model of the statically recovered fragmented
/// checksum contract. This API neither authenticates a ROM nor executes its code.
/// </summary>
public static class P28NativeChecksumArithmetic
{
    public const int RomSize = 32768;
    public const int BytesPerInvocation = 64;
    public const int InvocationCount = RomSize / BytesPerInvocation;
    public const int GateOffset = 0x60FB;
    public static P28NativeChecksumContract Contract { get; } = new(
        "p28-research-fragmented-sum8-v1", "Exact analyst-bound research baseline and verified M1c child only; not every P28 revision",
        "Unsigned sum of both bytes of every word, reduced modulo 256; no final transform",
        8, 0, 0, null, Array.AsReadOnly(new[] { new ByteRange(0, RomSize) }), [],
        "512 ascending 64-byte blocks; 32 ascending word program reads per invocation. Nonzero final residue also reads control byte 0x60FB.",
        "Little-endian word program reads; both bytes contribute separately to an 8-bit residue",
        BytesPerInvocation, InvocationCount,
        "The actual block counter reaches 512 then resets to zero; no intermediate invocation is full-ROM completion",
        "StaticAnalysisConfirmed within the recorded seeded contract; software comparison is not physical-CPU evidence",
        "Fixed zero residue, not a stored checksum field. The control byte is also covered data; it is not checksum storage or a repair target.");

    public static P28ChecksumArithmetic Calculate(RomImage image)
    {
        ArgumentNullException.ThrowIfNull(image);
        image.ValidateExactSize(RomSize);
        var bytes = image.ToArray();
        var checkpoints = new List<P28ChecksumCheckpoint>(InvocationCount);
        byte sum = 0;
        for (var block = 0; block < InvocationCount; block++)
        {
            var before = sum;
            // Sum bytes directly rather than reproducing the CPU's word/register operations.
            foreach (var value in bytes.AsSpan(block * BytesPerInvocation, BytesPerInvocation))
                sum = unchecked((byte)(sum + value));
            var last = block + 1 == InvocationCount;
            checkpoints.Add(new(block + 1, block, last ? 0 : block + 1, before, last ? (byte)0 : sum, sum));
        }
        return new(sum, 0, sum == 0, RomSize, Contract.Coverage, checkpoints.AsReadOnly(),
            "Arithmetic residue under the declared full-ROM contract. A zero residue alone does not prove the native check is enabled, unaltered, instruction-established or ECU-safe.");
    }
}
