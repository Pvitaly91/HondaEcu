namespace HondaEcu.Core;

// Independent static address classifier for invented fixtures; not executable ISA admission.
internal enum SoftwareAliasDomain { CanAlias, CannotAlias, UnknownDomain }
internal enum SoftwareAddressMode { DirectLowPage, OffPage, LocalRegister, IndexedX1, IndexedX2, IndirectDp, UspRelative, SystemStack }
internal sealed record SoftwareStaticAccess(SoftwareAddressMode Mode, int Operand, int Width,
    int? Lrb = null, int? EstablishedPointer = null);
internal sealed record SoftwareAliasResult(SoftwareAliasDomain Domain, int? EffectiveAddress, string Classification);

internal static class SoftwareBitAccessInventory
{
    internal static SoftwareAliasResult Classify(SoftwareStaticAccess access, int byteAddress)
    {
        if (byteAddress is < 0 or > 65535 || access.Width is not (8 or 16) || access.Lrb is < 0 or > 65535 ||
            access.EstablishedPointer is < 0 or > 65535)
            throw new InvalidDataException("Invalid static addressing facts.");
        if (access.Mode is SoftwareAddressMode.DirectLowPage or SoftwareAddressMode.OffPage && access.Operand is < 0 or > 255)
            throw new InvalidDataException("Not an encoded byte offset.");
        if (access.Mode == SoftwareAddressMode.LocalRegister && access.Operand is < 0 or > 7)
            throw new InvalidDataException("Not a local register offset.");
        if (access.Mode == SoftwareAddressMode.UspRelative && access.Operand is < -128 or > 127)
            throw new InvalidDataException("Not a signed byte displacement.");
        if (access.Mode is SoftwareAddressMode.IndexedX1 or SoftwareAddressMode.IndexedX2 && access.Operand is < 0 or > 65535)
            throw new InvalidDataException("Not an encoded word displacement.");
        int? address = access.Mode switch
        {
            SoftwareAddressMode.DirectLowPage => access.Operand,
            SoftwareAddressMode.OffPage => access.Lrb is null ? null : ((access.Lrb.Value & 0x1FE0) << 3) | access.Operand,
            SoftwareAddressMode.LocalRegister => access.Lrb is null ? null : ((access.Lrb.Value & 0x1FFF) << 3) + access.Operand,
            SoftwareAddressMode.IndexedX1 or SoftwareAddressMode.IndexedX2 or SoftwareAddressMode.UspRelative => access.EstablishedPointer + access.Operand,
            SoftwareAddressMode.IndirectDp or SoftwareAddressMode.SystemStack => access.EstablishedPointer,
            _ => throw new InvalidDataException("Unreviewed addressing mode.")
        };
        if (address is null or < 0 or > 65535) return new(SoftwareAliasDomain.UnknownDomain, null, "IndirectAliasCandidate; domain not proved");
        if (access.Width == 16) address &= ~1;
        var overlap = address <= byteAddress && byteAddress < address + access.Width / 8;
        return new(overlap ? SoftwareAliasDomain.CanAlias : SoftwareAliasDomain.CannotAlias, address,
            overlap ? access.Width == 16 ? "WordOverlapPotentialWriter" : "FullBytePotentialWriter" : "AddressDomainExcludesTrackedByte");
    }

    internal static SoftwareAliasResult ResetSweep(int? first, int? last, int stride, int width, int byteAddress)
    {
        if (stride <= 0 || width is not (8 or 16) || byteAddress is < 0 or > 65535 || first is < 0 or > 65535 || last is < 0 or > 65535)
            throw new InvalidDataException("Invalid sweep domain.");
        if (first is null || last is null) return new(SoftwareAliasDomain.UnknownDomain, null, "ResetOnlyCandidate; unknown sweep bounds");
        var found = false;
        for (long address = first.Value; address <= last.Value; address += stride)
        {
            var aligned = width == 16 ? address & ~1 : address;
            found |= aligned <= byteAddress && byteAddress < aligned + width / 8;
        }
        return new(found ? SoftwareAliasDomain.CanAlias : SoftwareAliasDomain.CannotAlias, null,
            found ? "ResetOnlyCandidate; not current runtime ownership" : "ResetSweepExcludesTrackedByte");
    }
}
