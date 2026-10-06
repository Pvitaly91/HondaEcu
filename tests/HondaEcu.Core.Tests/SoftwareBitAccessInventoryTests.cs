namespace HondaEcu.Core.Tests;

public sealed class SoftwareBitAccessInventoryTests
{
    [Fact]
    public void InventedStaticProgramCoversDirectPageWordIndexedIndirectAndResetDomains()
    {
        var program = new[]
        {
            new SoftwareStaticAccess(SoftwareAddressMode.DirectLowPage, 0x9B, 8),
            new SoftwareStaticAccess(SoftwareAddressMode.OffPage, 0x9B, 8, Lrb: 0x21),
            new SoftwareStaticAccess(SoftwareAddressMode.OffPage, 0x9A, 16, Lrb: 0x21),
            new SoftwareStaticAccess(SoftwareAddressMode.IndexedX1, 0x180, 8),
            new SoftwareStaticAccess(SoftwareAddressMode.IndirectDp, 0, 16)
        };
        var results = program.Select(a => SoftwareBitAccessInventory.Classify(a, 0x019B)).ToArray();
        Assert.Equal(new[] { SoftwareAliasDomain.CannotAlias, SoftwareAliasDomain.CanAlias, SoftwareAliasDomain.CanAlias,
            SoftwareAliasDomain.UnknownDomain, SoftwareAliasDomain.UnknownDomain }, results.Select(r => r.Domain));
        Assert.Equal(0x019B, results[1].EffectiveAddress); Assert.Equal(0x019A, results[2].EffectiveAddress);
        Assert.Equal("WordOverlapPotentialWriter", results[2].Classification);
        var reset = SoftwareBitAccessInventory.ResetSweep(0x100, 0x200, 2, 16, 0x019B);
        Assert.Equal(SoftwareAliasDomain.CanAlias, reset.Domain); Assert.Contains("ResetOnlyCandidate", reset.Classification);
    }

    [Theory]
    [InlineData(0x20, (int)SoftwareAliasDomain.CanAlias)]
    [InlineData(0x21, (int)SoftwareAliasDomain.CanAlias)]
    [InlineData(0x40, (int)SoftwareAliasDomain.CannotAlias)]
    public void OffPageUsesLrbPageBitsNotTextLabelOrRegisterBankOffset(int lrb, int domain)
    {
        Assert.Equal((SoftwareAliasDomain)domain, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.OffPage, 0x9B, 8, Lrb: lrb), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.UnknownDomain, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.OffPage, 0x9B, 8), 0x019B).Domain);
    }

    [Theory]
    [InlineData(0x019A)]
    [InlineData(0x019B)]
    public void OddWordAddressStillOverlapsUpperByte019B(int pointer)
    {
        var result = SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.IndirectDp, 0, 16, EstablishedPointer: pointer), 0x019B);
        Assert.Equal(SoftwareAliasDomain.CanAlias, result.Domain); Assert.Equal(0x019A, result.EffectiveAddress);
    }

    [Fact]
    public void LocalRegisterAndStackAliasesAreNotAssumedHarmless()
    {
        Assert.Equal(SoftwareAliasDomain.CanAlias, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.LocalRegister, 3, 8, Lrb: 0x33), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.UnknownDomain, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.LocalRegister, 3, 8), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.UnknownDomain, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.SystemStack, 0, 16), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.CannotAlias, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.SystemStack, 0, 16, EstablishedPointer: 0x700), 0x019B).Domain);
    }

    [Fact]
    public void OnlyEstablishedPointerDomainsCanExcludeIndexedAndUspAliases()
    {
        Assert.Equal(SoftwareAliasDomain.CanAlias, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.IndexedX2, 0x180, 8, EstablishedPointer: 0x1B), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.UnknownDomain, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.IndexedX2, 0x180, 8), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.CanAlias, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.UspRelative, -1, 8, EstablishedPointer: 0x19C), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.UnknownDomain, SoftwareBitAccessInventory.Classify(new(SoftwareAddressMode.UspRelative, -1, 8), 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.UnknownDomain, SoftwareBitAccessInventory.ResetSweep(null, 0x200, 2, 16, 0x019B).Domain);
        Assert.Equal(SoftwareAliasDomain.CannotAlias, SoftwareBitAccessInventory.ResetSweep(0x200, 0x300, 2, 16, 0x019B).Domain);
    }
}
