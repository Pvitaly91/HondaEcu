namespace HondaEcu.Core.Tests;

public sealed class ResetWdtExternal4700Tests
{
    private static Reset4700Wdt Wdt() => new(0x11, 1, 0x3C, true,
        Reset4700WdtCommand.MeaningNotEstablished, false, true, null, null);
    private static Reset4700NativeAddress NativeAddress() =>
        new(0x2519, 0x4700, 0x251C, Reset4700Space.Data, 1, "invented-native-MOVDP2519", true, false);
    private static Reset4700TaintDomain Domain() => new(true, true, true, true, true, true, true, true);
    private static Reset4700Preflight Hypothesis() => new(Reset4700Origin.InventedSpecification,
        true, true, true, true, true, true, true, true, true, true, true, true);

    [Theory]
    [InlineData((int)Reset4700Cause.PowerOn, 0, 0x24ED, true)]
    [InlineData((int)Reset4700Cause.ExternalRes, 0, 0x24ED, true)]
    [InlineData((int)Reset4700Cause.Brk, 2, 0x24F4, true)]
    [InlineData((int)Reset4700Cause.Watchdog, 4, 0x24DC, true)]
    [InlineData((int)Reset4700Cause.OpcodeTrap, 4, 0x24DC, true)]
    [InlineData((int)Reset4700Cause.Nmi, 6, 0x003C, false)]
    public void EventVectorsRemainSeparatedWithoutClaimingAnActualTransition(int cause, int wordAddress,
        int targetPc, bool reset)
    {
        var vector = ResetWdtExternal4700Fixture.Vector((Reset4700Cause)cause, true);
        Assert.Equal(wordAddress, vector.ProgramWordAddress); Assert.Equal(targetPc, vector.TargetPc);
        Assert.Equal(reset, vector.IsReset);
        Assert.Equal("ResetVectorStructurallyEstablished", vector.Evidence.Classification);
        Assert.False(vector.Evidence.ActualResetTransitionObserved); Assert.False(vector.Evidence.ExecutionPermitted);
    }

    [Theory]
    [InlineData(999)]
    [InlineData(-1)]
    public void UndefinedEventCannotAcquireAResetVector(int cause)
    {
        var result = ResetWdtExternal4700Fixture.Vector((Reset4700Cause)cause);
        Assert.Null(result.ProgramWordAddress); Assert.Null(result.TargetPc);
        Assert.Equal(Reset4700Verdict.UnknownSource, result.Evidence.Verdict);
    }

    [Fact]
    public void BrkCannotBorrowColdMarkerAndBitClearMerelyBecauseLaterInstructionsConverge()
    {
        var powerOn = ResetWdtExternal4700Fixture.Vector(Reset4700Cause.PowerOn, true);
        var brk = ResetWdtExternal4700Fixture.Vector(Reset4700Cause.Brk);
        Assert.Contains("RES-qualified", powerOn.EventClass);
        Assert.NotEqual(powerOn.ProgramWordAddress, brk.ProgramWordAddress);
        Assert.NotEqual(powerOn.TargetPc, brk.TargetPc);
        Assert.False(brk.Evidence.RootedNativeHistoryEstablished);
    }

    [Fact]
    public void ProgramVectorWordZeroIsNotTheDataSpaceSspRegisterAtZero()
    {
        Assert.Equal(Reset4700Region.Program, ResetWdtExternal4700Fixture.Memory(
            Reset4700Variant.Msm66201, Reset4700Space.Program, 0, 2));
        Assert.Equal(Reset4700Region.RegisterArea, ResetWdtExternal4700Fixture.Memory(
            Reset4700Variant.Msm66201, Reset4700Space.Data, 0, 2));
        var vector = ResetWdtExternal4700Fixture.Vector(Reset4700Cause.ExternalRes);
        var ssp = ResetWdtExternal4700Fixture.StandardResetField("SSP", Reset4700Variant.Msm66201);
        Assert.Equal(0, vector.ProgramWordAddress); Assert.Equal(0xFFFF, ssp.Value);
        Assert.NotEqual(vector.TargetPc, ssp.Value);
    }

    [Theory]
    [InlineData("SSP", 0xFFFF)]
    [InlineData("ACC", 0)]
    [InlineData("PSWL readback", 0xC8)]
    [InlineData("PSWH readback", 0x0C)]
    [InlineData("CF", 0)]
    [InlineData("ZF", 0)]
    [InlineData("HC", 0)]
    [InlineData("DD", 0)]
    [InlineData("SCB", 0)]
    [InlineData("PSW bit8", 0)]
    public void ManufacturerResetProjectionIsKnownButNotActualMachineState(string fieldName, int expected)
    {
        var field = ResetWdtExternal4700Fixture.StandardResetField(fieldName, Reset4700Variant.Msm66201);
        Assert.Equal(Reset4700StateKind.ManufacturerDefinedResetValue, field.Kind);
        Assert.Equal(expected, field.Value);
        var result = ResetWdtExternal4700Fixture.CheckField(field);
        Assert.Equal(Reset4700Verdict.SpecificationMatches, result.Verdict);
        Assert.False(result.ActualMachineStateObserved); Assert.Equal(0, result.ActualRomExecutions);
    }

    [Fact]
    public void ArchitecturalResetSspDoesNotProvideTheLaterNative047eWriter()
    {
        var reset = ResetWdtExternal4700Fixture.StandardResetField("SSP", Reset4700Variant.Msm66201);
        Assert.Equal(0xFFFF, reset.Value); Assert.NotEqual(0x047E, reset.Value);
        var forged = reset with { Value = 0x047E };
        Assert.Equal(Reset4700Verdict.InvalidProvenance, ResetWdtExternal4700Fixture.CheckField(forged).Verdict);
        Assert.False(ResetWdtExternal4700Fixture.CheckField(reset).RootedNativeHistoryEstablished);
    }

    [Theory]
    [InlineData("LRB", (int)Reset4700StateKind.UndefinedAfterReset)]
    [InlineData("SF", (int)Reset4700StateKind.NotSpecified)]
    [InlineData("External DATA4700", (int)Reset4700StateKind.NotSpecified)]
    public void UndefinedOrUnspecifiedFieldsStayUnknownRatherThanBecomingZero(string name, int kind)
    {
        var field = ResetWdtExternal4700Fixture.StandardResetField(name, Reset4700Variant.Msm66201);
        Assert.Equal((Reset4700StateKind)kind, field.Kind); Assert.Null(field.Value);
        Assert.Equal(Reset4700Verdict.UnknownSource, ResetWdtExternal4700Fixture.CheckField(field).Verdict);
        Assert.Equal(Reset4700Verdict.InvalidProvenance,
            ResetWdtExternal4700Fixture.CheckField(field with { Value = 0 }).Verdict);
    }

    [Theory]
    [InlineData((int)Reset4700Origin.HostSeed)]
    [InlineData((int)Reset4700Origin.GenericConstructor)]
    [InlineData((int)Reset4700Origin.ImportedState)]
    public void HostOrConstructorValuesCannotBecomeManufacturerResetProvenance(int origin)
    {
        var field = ResetWdtExternal4700Fixture.StandardResetField("ACC", Reset4700Variant.Msm66201);
        var result = ResetWdtExternal4700Fixture.CheckField(field with { Origin = (Reset4700Origin)origin });
        Assert.Equal(Reset4700Verdict.InvalidProvenance, result.Verdict);
        Assert.Equal("HostResetStateRejected", result.Classification);
    }

    [Fact]
    public void UndefinedLrbCannotBeRelabeledDefinedOrPreservedByAnInventedAssertion()
    {
        var lrb = ResetWdtExternal4700Fixture.StandardResetField("LRB", Reset4700Variant.Msm66201);
        foreach (var kind in new[] { Reset4700StateKind.ManufacturerDefinedResetValue,
            Reset4700StateKind.ManufacturerDefinedPreservedValue })
        {
            Assert.Equal(Reset4700Verdict.InvalidProvenance,
                ResetWdtExternal4700Fixture.CheckField(lrb with { Kind = kind, Value = 0 }).Verdict);
        }
    }

    [Fact]
    public void PowerOnWithoutAnExplicitQualifiedResSequenceCannotAcquireTheResetVector()
    {
        foreach (var qualified in new bool?[] { null, false })
        {
            var result = ResetWdtExternal4700Fixture.Vector(Reset4700Cause.PowerOn, qualified);
            Assert.Null(result.ProgramWordAddress); Assert.Null(result.TargetPc);
            Assert.Equal(Reset4700Verdict.UnknownSource, result.Evidence.Verdict);
            Assert.False(result.Evidence.ActualResetTransitionObserved);
        }
    }

    [Theory]
    [InlineData(0x10)]
    [InlineData(0x1555)]
    public void ConditionalLrbRetentionNeedsAnIndependentPriorValueRatherThanAResetZero(int prior)
    {
        var preserved = ResetWdtExternal4700Fixture.ConditionalLrbPreservation(prior,
            "invented-independent-prior-LRB", true, true);
        Assert.Equal(prior, preserved.Before); Assert.Equal(prior, preserved.After);
        Assert.Equal(Reset4700StateKind.ManufacturerDefinedPreservedValue, preserved.Kind);
        Assert.Equal(Reset4700Verdict.SpecificationMatches, preserved.Evidence.Verdict);
        Assert.False(preserved.Evidence.ActualMachineStateObserved);
        Assert.False(preserved.Evidence.ExecutionPermitted);
    }

    [Theory]
    [InlineData(0x2000)]
    [InlineData(0xABCD)]
    [InlineData(0xFFFF)]
    public void LrbRetentionCannotPreserveNonexistentUpperBitsAsValidReadback(int invalidPrior)
    {
        var result = ResetWdtExternal4700Fixture.ConditionalLrbPreservation(invalidPrior,
            "invented-prior", true, true);
        Assert.Null(result.After);
        Assert.Equal(Reset4700Verdict.InvalidProvenance, result.Evidence.Verdict);
        Assert.Equal("InvalidLrbReadbackProjection", result.Evidence.Classification);
    }

    [Theory]
    [InlineData("unknown prior")]
    [InlineData("missing source")]
    [InlineData("document applicability")]
    [InlineData("prior continuity")]
    [InlineData("host prior")]
    public void UndefinedOrUnsupportedPriorLrbCannotBecomeKnownByCallingItPreserved(string missing)
    {
        var result = ResetWdtExternal4700Fixture.ConditionalLrbPreservation(
            missing == "unknown prior" ? null : 0x10,
            missing == "missing source" ? null : "invented-prior",
            missing == "document applicability" ? null : true,
            missing == "prior continuity" ? null : true,
            missing == "host prior" ? Reset4700Origin.HostSeed : Reset4700Origin.InventedSpecification);
        Assert.Null(result.After);
        Assert.NotEqual(Reset4700Verdict.SpecificationMatches, result.Evidence.Verdict);
    }

    [Theory]
    [InlineData("LRB", 0)]
    [InlineData("SSP", 0x7FE)]
    [InlineData("ACC", 0x5555)]
    public void ConvenientGenericInitializerCannotReplaceExactResetSpecification(string fieldName, int value)
    {
        var canonical = ResetWdtExternal4700Fixture.StandardResetField(fieldName, Reset4700Variant.Msm66201);
        Assert.Equal(Reset4700Verdict.InvalidProvenance,
            ResetWdtExternal4700Fixture.CheckField(canonical with { Value = value }).Verdict);
    }

    [Theory]
    [InlineData(0, 0, 0x0CC8)]
    [InlineData(0xFFFF, 0xF337, 0xFFFF)]
    [InlineData(0x0CC8, 0, 0x0CC8)]
    [InlineData(0x1234, 0x1234, 0x1EFC)]
    public void ReservedReadOnePswBitsAreNotWritableStoredResetBits(int written, int writable, int readback)
    {
        var projection = ResetWdtExternal4700Fixture.PswReadback(written, null);
        Assert.Equal(writable, projection.WritableBits); Assert.Equal(readback, projection.Readback);
        Assert.Equal(0, projection.WritableBits & 0x0CC8);
        Assert.Equal(0x0CC8, projection.Readback & 0x0CC8);
        Assert.Null(projection.InternalSf);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void WritablePswClearDoesNotWriteIndependentInternalSf(bool sf)
    {
        var cleared = ResetWdtExternal4700Fixture.PswReadback(0, sf);
        Assert.Equal(0, cleared.WritableBits); Assert.Equal(0x0CC8, cleared.Readback);
        Assert.Equal(sf, cleared.InternalSf);
    }

    [Fact]
    public void WdtIsAnExactByteWriteOnlyCommandNotARamEcho()
    {
        var wdt = Wdt();
        Assert.Equal(0x11, wdt.Address); Assert.Equal(1, wdt.WidthBytes);
        Assert.True(wdt.WriteOnly); Assert.True(wdt.ResetStoppedPrimaryEstablished);
        Assert.Null(ResetWdtExternal4700Fixture.WdtReadback(wdt));
        var result = ResetWdtExternal4700Fixture.WdtWrite(wdt);
        Assert.Equal(Reset4700Verdict.UnknownSource, result.Verdict);
        Assert.Equal("WdtCommandMeaningNotEstablished", result.Classification);
    }

    [Theory]
    [InlineData((int)Reset4700WdtCommand.Start)]
    [InlineData((int)Reset4700WdtCommand.Stop)]
    [InlineData((int)Reset4700WdtCommand.RestartCounter)]
    public void ExactCommand3cCannotBeGuessedFromTheStoppedResetState(int meaning)
    {
        foreach (var claimedPrimary in new bool?[] { null, false, true })
        {
            var result = ResetWdtExternal4700Fixture.WdtWrite(Wdt() with
            {
                Meaning = (Reset4700WdtCommand)meaning,
                CommandPrimaryEstablished = claimedPrimary
            });
            Assert.Equal(Reset4700Verdict.InvalidProvenance, result.Verdict);
            Assert.Equal("UnsupportedWdtCommandGuess", result.Classification);
        }
    }

    [Theory]
    [InlineData("wrong address")]
    [InlineData("word width")]
    [InlineData("unknown command")]
    [InlineData("RAM echo")]
    [InlineData("host source")]
    public void IncorrectWdtFormOrAuthorityCannotBorrowTheNativeByteWrite(string defect)
    {
        var wdt = defect switch
        {
            "wrong address" => Wdt() with { Address = 0x10 },
            "word width" => Wdt() with { WidthBytes = 2 },
            "unknown command" => Wdt() with { Command = null },
            "RAM echo" => Wdt() with { WriteOnly = false },
            _ => Wdt() with { Origin = Reset4700Origin.HostSeed }
        };
        Assert.Equal(Reset4700Verdict.InvalidProvenance, ResetWdtExternal4700Fixture.WdtWrite(wdt).Verdict);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(1000)]
    public void InstructionCountOrHostTicksCannotManufactureWatchdogClockProgress(int ticks)
    {
        var result = ResetWdtExternal4700Fixture.WdtHardwareContinuation(Wdt(), true, null, ticks);
        Assert.Equal(Reset4700Verdict.InvalidProvenance, result.Verdict);
        Assert.Equal("UnsupportedWdtTimerProgress", result.Classification);
    }

    [Fact]
    public void UnspecifiedCommandAndClockPreventHardwareSafeContinuationToTheSspWriter()
    {
        var result = ResetWdtExternal4700Fixture.WdtHardwareContinuation(Wdt(), true, null);
        Assert.Equal(Reset4700Verdict.UnknownSource, result.Verdict);
        Assert.False(result.RootedNativeHistoryEstablished); Assert.False(result.ExecutionPermitted);
    }

    [Theory]
    [InlineData((int)Reset4700Variant.Msm66201, 0x27F, (int)Reset4700Region.InternalRam)]
    [InlineData((int)Reset4700Variant.Msm66201, 0x280, (int)Reset4700Region.ExternalData)]
    [InlineData((int)Reset4700Variant.Msm66P201, 0x27F, (int)Reset4700Region.InternalRam)]
    [InlineData((int)Reset4700Variant.Msm66P201, 0x280, (int)Reset4700Region.ExternalData)]
    [InlineData((int)Reset4700Variant.Msm66207, 0x47F, (int)Reset4700Region.InternalRam)]
    [InlineData((int)Reset4700Variant.Msm66207, 0x480, (int)Reset4700Region.ExternalData)]
    [InlineData((int)Reset4700Variant.Msm66P207, 0x47F, (int)Reset4700Region.InternalRam)]
    [InlineData((int)Reset4700Variant.Msm66P207, 0x480, (int)Reset4700Region.ExternalData)]
    public void VariantSpecificInternalExternalBoundaryIsNotSharedByAnalogy(int variant, int address, int region)
    {
        Assert.Equal((Reset4700Region)region,
            ResetWdtExternal4700Fixture.Memory((Reset4700Variant)variant, Reset4700Space.Data, address));
    }

    [Theory]
    [InlineData((int)Reset4700Variant.Msm66201, (int)Reset4700Region.ExternalData)]
    [InlineData((int)Reset4700Variant.Msm66207, (int)Reset4700Region.InternalRam)]
    public void FirstStackWord047eHasDifferentStandardVariantMapping(int variant, int region)
    {
        Assert.Equal((Reset4700Region)region, ResetWdtExternal4700Fixture.Memory(
            (Reset4700Variant)variant, Reset4700Space.Data, 0x47E, 2));
    }

    [Theory]
    [InlineData((int)Reset4700Variant.Msm66201)]
    [InlineData((int)Reset4700Variant.Msm66207)]
    public void Data4700IsExternalButProgram4700IsASeparateAddressSpace(int variant)
    {
        Assert.Equal(Reset4700Region.ExternalData, ResetWdtExternal4700Fixture.Memory(
            (Reset4700Variant)variant, Reset4700Space.Data, 0x4700));
        Assert.Equal(Reset4700Region.Program, ResetWdtExternal4700Fixture.Memory(
            (Reset4700Variant)variant, Reset4700Space.Program, 0x4700));
    }

    [Theory]
    [InlineData((int)Reset4700Variant.UnknownEcu)]
    [InlineData(999)]
    [InlineData(-1)]
    public void UnknownOrWrongChipCannotAcquireAStandardVariantMemoryMap(int variant)
    {
        Assert.Equal(Reset4700Region.Unknown, ResetWdtExternal4700Fixture.Memory(
            (Reset4700Variant)variant, Reset4700Space.Data, 0x47E, 2));
    }

    [Theory]
    [InlineData((int)Reset4700Variant.Msm66201, 0x27F)]
    [InlineData((int)Reset4700Variant.Msm66207, 0x47F)]
    public void WordAcrossInternalExternalBoundaryIsNotOneEstablishedRamObject(int variant, int address)
    {
        Assert.Equal(Reset4700Region.Unknown, ResetWdtExternal4700Fixture.Memory(
            (Reset4700Variant)variant, Reset4700Space.Data, address, 2));
    }

    [Fact]
    public void ManufacturerResetFieldsRemainConditionalForAnUnidentifiedEcu()
    {
        var field = ResetWdtExternal4700Fixture.StandardResetField("SSP", Reset4700Variant.UnknownEcu);
        var result = ResetWdtExternal4700Fixture.CheckField(field);
        Assert.Equal(Reset4700Verdict.UnknownSource, result.Verdict);
        Assert.Equal("DeviceApplicabilityConditional", result.Classification);
        Assert.False(result.ActualMachineStateObserved);
    }

    [Fact]
    public void NativeMovDpAndDataByteLoadEstablishOnlyArchitecturalEffectiveAddress()
    {
        var result = ResetWdtExternal4700Fixture.NativeData4700(NativeAddress());
        Assert.Equal(Reset4700Verdict.SpecificationMatches, result.Verdict);
        Assert.Equal("ExternalDataAddressEstablished", result.Classification);
        Assert.Contains("BoardDecodeNotEstablished", result.Barrier);
        Assert.Contains("ExternalReadValueUnknown", result.Barrier);
        Assert.False(result.ExecutionPermitted);
    }

    [Theory]
    [InlineData("wrong writer")]
    [InlineData("wrong reader")]
    [InlineData("wrong effective address")]
    [InlineData("program source")]
    [InlineData("word load")]
    [InlineData("host DP")]
    [InlineData("missing source")]
    [InlineData("unknown context")]
    [InlineData("unknown DP")]
    [InlineData("stack SF")]
    [InlineData("unknown SF")]
    public void ExternalAddressAuthorityRequiresExactNativeSourceAndDataByteForm(string defect)
    {
        var address = defect switch
        {
            "wrong writer" => NativeAddress() with { WriterPc = 0x2682 },
            "wrong reader" => NativeAddress() with { ReaderPc = 0x5C74 },
            "wrong effective address" => NativeAddress() with { Dp = 0x047E },
            "program source" => NativeAddress() with { Space = Reset4700Space.Program },
            "word load" => NativeAddress() with { WidthBytes = 2 },
            "host DP" => NativeAddress() with { Origin = Reset4700Origin.HostSeed },
            "missing source" => NativeAddress() with { Source = null },
            "unknown context" => NativeAddress() with { RetainedAddressing = null },
            "stack SF" => NativeAddress() with { InternalSf = true },
            "unknown SF" => NativeAddress() with { InternalSf = null },
            _ => NativeAddress() with { Dp = null }
        };
        Assert.NotEqual(Reset4700Verdict.SpecificationMatches,
            ResetWdtExternal4700Fixture.NativeData4700(address).Verdict);
    }

    [Fact]
    public void SymbolicUnknownReadRemainsUnknownWhileOnlyItsBitZeroTaintsB7BitZero()
    {
        var slice = ResetWdtExternal4700Fixture.SymbolicB7AfterMb(Domain());
        Assert.Null(slice.ActualExternalByte);
        Assert.Equal(2, slice.KnownMask); Assert.Equal(0, slice.KnownValue);
        Assert.Equal(1, slice.ExternalValueMask); Assert.Equal(0xFC, slice.PriorRamMask);
        Assert.Equal("InventedOnly", slice.EvidenceDomain);
    }

    [Fact]
    public void All256ExternalValuesAndAll256PriorRamBytesLeaveJbsBitOneClear()
    {
        for (var external = 0; external <= 0xFF; external++)
        {
            for (var oldRam = 0; oldRam <= 0xFF; oldRam++)
            {
                // Independent mask identity, not a runner-derived expectation.
                var expected = (oldRam & 0xFC) | (external & 1);
                var result = ResetWdtExternal4700Fixture.ProjectNumericByte(external, oldRam);
                Assert.Equal(expected, result.AfterMb251E);
                Assert.Equal(oldRam & 0xFC, result.AfterMb251E & 0xFC);
                Assert.Equal(external & 1, result.AfterMb251E & 1);
                Assert.Equal(0, result.AfterMb251E & 2);
                Assert.False(result.Jbs2521Taken); Assert.Equal(0x2524, result.NextPc);
            }
        }
        Assert.Equal("ValueNoninterferenceProvenWithinDomain",
            ResetWdtExternal4700Fixture.ValueNoninterference(Domain(), 0x2524).Classification);
    }

    [Fact]
    public void ByteLoadShiftAndBitMoveDoNotInventHighAccumulatorOrArithmeticFlagValues()
    {
        for (var value = 0; value <= 0xFF; value++)
        {
            var load = ResetWdtExternal4700Fixture.ByteLoadProjection(value, null, null, null, false);
            Assert.Equal(value, load.Al); Assert.Null(load.Ah);
            Assert.False(load.Dd); Assert.Equal(value == 0, load.Zf);
            Assert.Null(load.Cf); Assert.Null(load.Hc);
            var shift = ResetWdtExternal4700Fixture.ShiftRightProjection(load.Al, load.Zf, load.Hc, load.Dd);
            Assert.Equal(value / 2, shift.Al); Assert.Equal(value % 2 == 1, shift.Cf);
            Assert.Equal(load.Zf, shift.Zf); Assert.Null(shift.Hc); Assert.False(shift.Dd);
        }
    }

    [Theory]
    [InlineData(0)]
    [InlineData(0xA5)]
    [InlineData(0xFF)]
    public void ByteLoadRetainsIndependentlyKnownHighByteWithoutCallingItExternalReadData(int high)
    {
        var load = ResetWdtExternal4700Fixture.ByteLoadProjection(0x42, high, true, false, false);
        Assert.Equal(high, load.Ah); Assert.True(load.Cf); Assert.False(load.Hc);
    }

    [Theory]
    [InlineData("DP source")]
    [InlineData("exact ISA")]
    [InlineData("native clear")]
    [InlineData("RAM context")]
    [InlineData("intervening bit writer")]
    [InlineData("asynchronous context")]
    [InlineData("slice completeness")]
    [InlineData("nonstack SF")]
    public void ValueNoninterferenceFailsClosedWhenAnyRequiredNumericDomainIsMissing(string missing)
    {
        foreach (var value in new bool?[] { null, false })
        {
            var domain = missing switch
            {
                "DP source" => Domain() with { NativeDp2519 = value },
                "exact ISA" => Domain() with { ExactByteIsa = value },
                "native clear" => Domain() with { NativeBit1Clear24F1 = value },
                "RAM context" => Domain() with { RetainedB7Addressing = value },
                "intervening bit writer" => Domain() with { NoInterveningBit1Write = value },
                "asynchronous context" => Domain() with { NoAsyncContextChange = value },
                "nonstack SF" => Domain() with { NonstackSfEstablished = value },
                _ => Domain() with { NumericSliceComplete = value }
            };
            Assert.Equal(Reset4700Verdict.UnknownSource,
                ResetWdtExternal4700Fixture.ValueNoninterference(domain, 0x2524).Verdict);
        }
    }

    [Fact]
    public void UnknownOrWordDdCannotBorrowTheByteShiftProjection()
    {
        foreach (var dd in new bool?[] { null, true })
        {
            Assert.Throws<InvalidDataException>(() =>
                ResetWdtExternal4700Fixture.ShiftRightProjection(0x81, false, null, dd));
        }
    }

    [Fact]
    public void PswClearCannotSupplyTheUnspecifiedSfRequiredByTheDataPointerLoad()
    {
        foreach (var sf in new bool?[] { null, true })
        {
            Assert.Throws<InvalidDataException>(() =>
                ResetWdtExternal4700Fixture.ByteLoadProjection(0x81, null, null, null, sf));
        }
    }

    [Theory]
    [InlineData(0x2528)]
    [InlineData(0x2689)]
    [InlineData(0x2759)]
    public void NarrowJbsProofCannotPromoteUntestedLaterControlOrBootHistory(int checkpoint)
    {
        var result = ResetWdtExternal4700Fixture.ValueNoninterference(Domain(), checkpoint);
        Assert.Equal(Reset4700Verdict.UnknownSource, result.Verdict);
        Assert.Equal("NumericDomainNotAuditedBeyond2524", result.Classification);
    }

    [Fact]
    public void NumericNoninterferenceDoesNotEraseUnknownBoardReadEffects()
    {
        var domain = Domain();
        Assert.Equal(Reset4700Verdict.SpecificationMatches,
            ResetWdtExternal4700Fixture.ValueNoninterference(domain, 0x2524).Verdict);
        var hardware = ResetWdtExternal4700Fixture.WholeHardwareContinuation(domain, null);
        Assert.Equal(Reset4700Verdict.PreflightBlocked, hardware.Verdict);
        Assert.Equal("ExternalReadSideEffectsUnknown", hardware.Classification);
        Assert.Equal(Reset4700Verdict.InvalidProvenance,
            ResetWdtExternal4700Fixture.WholeHardwareContinuation(domain, null, true).Verdict);
    }

    [Fact]
    public void SuppliedInventedBoardAndReadHypothesesStillAreNotActualMachineObservations()
    {
        var domain = Domain() with { BoardDecodeEstablished = true, ReadSideEffectsEstablished = true };
        var result = ResetWdtExternal4700Fixture.WholeHardwareContinuation(domain, true);
        Assert.Equal(Reset4700Verdict.PreflightBlocked, result.Verdict);
        Assert.Equal("RuntimeReadNotObserved", result.Classification);
        Assert.False(result.ExecutionPermitted);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void NativeCodeOwnedBitOverwriteKillsOnlyTheSelectedUnknownDependency(bool value)
    {
        var slice = ResetWdtExternal4700Fixture.SymbolicB7AfterMb(Domain());
        var changed = ResetWdtExternal4700Fixture.OverwriteBit(slice, 0, value, true);
        Assert.Equal(0, changed.ExternalValueMask); Assert.Equal(3, changed.KnownMask);
        Assert.Equal(value ? 1 : 0, changed.KnownValue); Assert.Equal(0xFC, changed.PriorRamMask);
        Assert.Null(changed.ActualExternalByte);
    }

    [Fact]
    public void UnsupportedUnknownBitOverwriteCannotBecomeAnOwnedConstant()
    {
        var slice = ResetWdtExternal4700Fixture.SymbolicB7AfterMb(Domain());
        var unknown = ResetWdtExternal4700Fixture.OverwriteBit(slice, 0, false, false);
        Assert.Equal(0, unknown.KnownMask & 1); Assert.Equal(1, unknown.ExternalValueMask & 1);
        Assert.Equal(1, unknown.PriorRamMask & 1);
    }

    [Fact]
    public void LaterNativeWordLoadAndOwnedCompareKillNumericAccumulatorAndCarryTaintConditionally()
    {
        for (var value = 0; value <= 0xFF; value++)
        {
            var shift = ResetWdtExternal4700Fixture.ShiftRightProjection(value, value == 0, null, false);
            var owned = ResetWdtExternal4700Fixture.CodeOwnedWordLoad252E(true, shift.Cf, shift.Hc, false);
            Assert.Equal(0x5555, owned.A); Assert.True(owned.Dd); Assert.False(owned.Zf);
            Assert.Equal(shift.Cf, owned.Cf); Assert.Null(owned.Hc);
            var compared = ResetWdtExternal4700Fixture.CodeOwnedEqualCompare2535(owned.A, 0x5555);
            Assert.False(compared.Cf); Assert.True(compared.Zf);
        }
        Assert.Throws<InvalidDataException>(() =>
            ResetWdtExternal4700Fixture.CodeOwnedWordLoad252E(false, null, null, false));
        foreach (var sf in new bool?[] { null, true })
        {
            Assert.Throws<InvalidDataException>(() =>
                ResetWdtExternal4700Fixture.CodeOwnedWordLoad252E(true, null, null, sf));
        }
    }

    [Theory]
    [InlineData(false, "252E")]
    [InlineData(true, "252B")]
    public void P4BitOneIsAnIndependentValueDependentPredicateNotTheExternalDataByte(bool bit, string branch)
    {
        var predicate = new Reset4700ExternalPredicate("P4.1 at2528", bit,
            Reset4700Origin.InventedSpecification, true);
        var result = ResetWdtExternal4700Fixture.ExternalControl(predicate);
        Assert.Equal(Reset4700Verdict.SpecificationMatches, result.Verdict);
        Assert.Equal("ValueDependentControlGate", result.Classification);
        Assert.Contains(branch, result.Barrier);
        Assert.False(result.ActualMachineStateObserved); Assert.False(result.ExecutionPermitted);
    }

    [Theory]
    [InlineData("P4.1 at2528")]
    [InlineData("PWM IRQH.5 at264B")]
    public void FakeHostPinSamplesOrPendingBitsCannotSupplyExternalPredicateAuthority(string signal)
    {
        foreach (var fakeValue in new[] { false, true })
        {
            var predicate = new Reset4700ExternalPredicate(signal, fakeValue,
                Reset4700Origin.HostSeed, true, true);
            var result = ResetWdtExternal4700Fixture.ExternalControl(predicate);
            Assert.Equal(Reset4700Verdict.InvalidProvenance, result.Verdict);
            Assert.Equal("InjectedExternalPredicateRejected", result.Classification);
            Assert.False(result.ExecutionPermitted);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void PendingComparisonHypothesisRequiresSameHistoryAfterTheNativeIrqClear(bool oldPending)
    {
        var fresh = new Reset4700ExternalPredicate("PWM IRQH.5 at264B", oldPending,
            Reset4700Origin.InventedSpecification, true, true);
        var result = ResetWdtExternal4700Fixture.ExternalControl(fresh);
        Assert.Equal(Reset4700Verdict.SpecificationMatches, result.Verdict);
        Assert.Contains(oldPending ? "ZF0" : "ZF1", result.Barrier);
        foreach (var retainedHistory in new bool?[] { null, false })
        {
            Assert.Equal(Reset4700Verdict.UnknownSource, ResetWdtExternal4700Fixture.ExternalControl(
                fresh with { SameHistoryAfterClear261E = retainedHistory }).Verdict);
        }
        Assert.False(result.ActualMachineStateObserved);
    }

    [Theory]
    [InlineData("P4.1 at2528")]
    [InlineData("PWM IRQH.5 at264B")]
    public void UnknownPinOrPendingStateCannotUseAConvenientDefaultZero(string signal)
    {
        var unknown = new Reset4700ExternalPredicate(signal, null,
            Reset4700Origin.InventedSpecification, true, true);
        Assert.Equal(Reset4700Verdict.UnknownSource,
            ResetWdtExternal4700Fixture.ExternalControl(unknown).Verdict);
    }

    [Theory]
    [InlineData("device")]
    [InlineData("reset")]
    [InlineData("prefix")]
    [InlineData("WDT")]
    [InlineData("read effects")]
    [InlineData("P4")]
    [InlineData("PWM IRQ")]
    [InlineData("ISA")]
    [InlineData("same machine")]
    [InlineData("native frame")]
    [InlineData("admission")]
    [InlineData("mechanism")]
    public void EveryMandatoryPreflightAuthorityRejectsFalseAndUnknown(string missing)
    {
        foreach (var value in new bool?[] { null, false })
        {
            var preflight = missing switch
            {
                "device" => Hypothesis() with { ExactDeviceRevision = value },
                "reset" => Hypothesis() with { ActualResetHistory = value },
                "prefix" => Hypothesis() with { RootedPrefix = value },
                "WDT" => Hypothesis() with { WdtEffects = value },
                "read effects" => Hypothesis() with { ExternalReadEffects = value },
                "P4" => Hypothesis() with { P4Waveform = value },
                "PWM IRQ" => Hypothesis() with { FreshPwmIrq = value },
                "ISA" => Hypothesis() with { ExactIsa = value },
                "same machine" => Hypothesis() with { SameMachineHistory = value },
                "native frame" => Hypothesis() with { NativeFrame = value },
                "admission" => Hypothesis() with { ExistingAdmission = value },
                _ => Hypothesis() with { SafeMechanism = value }
            };
            var result = ResetWdtExternal4700Fixture.CheckPreflight(preflight);
            Assert.Equal(Reset4700Verdict.PreflightBlocked, result.Verdict);
            Assert.Equal("RootedNativeExecutionPreflightBlocked", result.Classification);
            Assert.False(result.ExecutionPermitted);
        }
    }

    [Theory]
    [InlineData((int)Reset4700Origin.HostSeed)]
    [InlineData((int)Reset4700Origin.GenericConstructor)]
    [InlineData((int)Reset4700Origin.ImportedState)]
    public void AConvenientHostOrSyntheticRootCannotClaimActualResetHistory(int origin)
    {
        var result = ResetWdtExternal4700Fixture.CheckPreflight(Hypothesis() with { Origin = (Reset4700Origin)origin });
        Assert.Equal(Reset4700Verdict.InvalidProvenance, result.Verdict);
        Assert.Equal("HostOrSyntheticRootRejected", result.Classification);
    }

    [Theory]
    [InlineData("fake P4 waveform")]
    [InlineData("fake fresh IRQH.5")]
    [InlineData("actual reset")]
    [InlineData("actual CAL2689")]
    [InlineData("restored SSP047E")]
    [InlineData("full boot")]
    [InlineData("M2aq promoted")]
    public void EvenCompleteInventedPolicyCannotPromoteAnyActualOrHistoricalObservation(string claim)
    {
        var result = ResetWdtExternal4700Fixture.CheckPreflight(Hypothesis());
        Assert.Equal(Reset4700Verdict.SpecificationMatches, result.Verdict);
        Assert.Throws<InvalidDataException>(() => ResetWdtExternal4700Fixture.RequireActualClaim(result, claim));
        Assert.Equal("InventedOnly", result.EvidenceDomain);
        Assert.Equal(0, result.ActualRomExecutions); Assert.Equal(0, result.SyntheticRomExecutions);
        Assert.False(result.ActualResetTransitionObserved); Assert.False(result.ActualMachineStateObserved);
        Assert.False(result.ActualCal2689Observed); Assert.False(result.RootedNativeHistoryEstablished);
        Assert.False(result.ExecutionPermitted); Assert.False(result.FullBootEstablished);
        Assert.Null(result.ActualEventIndex); Assert.Null(result.ActualGlobalWriteOrdinal);
    }
}
