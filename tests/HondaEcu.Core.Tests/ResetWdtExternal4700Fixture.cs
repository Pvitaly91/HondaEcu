namespace HondaEcu.Core.Tests;

// Independent invented specification algebra. These types never instantiate a
// Cpu/Bus, load a ROM, provide a runtime input, or authorize native execution.
internal enum Reset4700Cause { PowerOn, ExternalRes, Brk, Watchdog, OpcodeTrap, Nmi }
internal enum Reset4700Variant { Msm66201, Msm66P201, Msm66207, Msm66P207, UnknownEcu }
internal enum Reset4700Verdict { SpecificationMatches, SpecificationMismatch, UnknownSource, InvalidProvenance, PreflightBlocked }
internal enum Reset4700StateKind
{
    ManufacturerDefinedResetValue, ManufacturerDefinedPreservedValue, UndefinedAfterReset,
    RevisionDependent, ExternalHardwareDependent, NotSpecified
}
internal enum Reset4700Origin { InventedSpecification, HostSeed, GenericConstructor, ImportedState }
internal enum Reset4700Space { Data, Program }
internal enum Reset4700Region { RegisterArea, Sfr, InternalRam, ExternalData, Program, Unknown }
internal enum Reset4700WdtCommand { MeaningNotEstablished, Start, Stop, RestartCounter }

internal sealed record Reset4700Result(Reset4700Verdict Verdict, string Classification, string Barrier = "")
{
    internal string EvidenceDomain => "InventedOnly";
    internal int ActualRomExecutions => 0;
    internal int SyntheticRomExecutions => 0;
    internal bool ActualResetTransitionObserved => false;
    internal bool ActualMachineStateObserved => false;
    internal bool RootedNativeHistoryEstablished => false;
    internal bool ExecutionPermitted => false;
    internal bool ActualCal2689Observed => false;
    internal bool FullBootEstablished => false;
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
}

internal sealed record Reset4700Vector(int? ProgramWordAddress, int? TargetPc, bool IsReset,
    string EventClass, Reset4700Result Evidence);
internal sealed record Reset4700Field(string Name, Reset4700StateKind Kind, int? Value,
    int WidthBits, string Source, bool DeviceApplicable, Reset4700Origin Origin = Reset4700Origin.InventedSpecification);
internal sealed record Reset4700Psw(int WritableBits, int Readback, bool? InternalSf);
internal sealed record Reset4700Preservation(int? Before, int? After,
    Reset4700StateKind Kind, Reset4700Result Evidence);
internal sealed record Reset4700Wdt(int Address, int WidthBytes, int? Command,
    bool? WriteOnly, Reset4700WdtCommand Meaning, bool? CommandPrimaryEstablished,
    bool? ResetStoppedPrimaryEstablished, bool? RuntimeClockEstablished,
    bool? ResetHistoryEstablished, Reset4700Origin Origin = Reset4700Origin.InventedSpecification);
internal sealed record Reset4700NativeAddress(int WriterPc, int? Dp, int ReaderPc,
    Reset4700Space Space, int WidthBytes, string? Source,
    bool? RetainedAddressing, bool? InternalSf,
    Reset4700Origin Origin = Reset4700Origin.InventedSpecification);

// Masks express dependencies, not a guessed numeric value for an unknown read.
internal sealed record Reset4700BitSlice(int KnownMask, int KnownValue,
    int ExternalValueMask, int PriorRamMask)
{
    internal string EvidenceDomain => "InventedOnly";
    internal int? ActualExternalByte => null;
}
internal sealed record Reset4700TaintDomain(bool? NativeDp2519, bool? ExactByteIsa,
    bool? NativeBit1Clear24F1, bool? RetainedB7Addressing, bool? NoInterveningBit1Write,
    bool? NoAsyncContextChange, bool? NumericSliceComplete, bool? NonstackSfEstablished,
    bool? ReadSideEffectsEstablished = null, bool? BoardDecodeEstablished = null);
internal sealed record Reset4700Projection(int AfterClear24F1, int AfterMb251E,
    bool SrLbCarry, int ShiftedAl, bool Jbs2521Taken, int NextPc);
internal sealed record Reset4700Preflight(Reset4700Origin Origin,
    bool? ExactDeviceRevision, bool? ActualResetHistory, bool? RootedPrefix,
    bool? WdtEffects, bool? ExternalReadEffects, bool? P4Waveform,
    bool? FreshPwmIrq, bool? ExactIsa, bool? SameMachineHistory, bool? NativeFrame,
    bool? ExistingAdmission, bool? SafeMechanism);
internal sealed record Reset4700ExternalPredicate(string Signal, bool? Value,
    Reset4700Origin Origin, bool? NativeReaderEstablished,
    bool? SameHistoryAfterClear261E = null);

internal static class ResetWdtExternal4700Fixture
{
    internal static Reset4700Vector Vector(Reset4700Cause cause, bool? powerOnResQualified = null)
    {
        if (cause == Reset4700Cause.PowerOn && powerOnResQualified != true)
            return new(null, null, false, "Power-on RES qualification missing",
                Result(Reset4700Verdict.UnknownSource, "PowerOnResetArchitectureNotEstablished"));
        var vector = cause switch
        {
            // Power-on here means a hardware-qualified RES sequence, not an
            // invented internal power-on detector or an observed ECU event.
            Reset4700Cause.PowerOn => (0, 0x24ED, true, "RES-qualified power-on"),
            Reset4700Cause.ExternalRes => (0, 0x24ED, true, "RES"),
            Reset4700Cause.Brk => (2, 0x24F4, true, "BRK"),
            Reset4700Cause.Watchdog => (4, 0x24DC, true, "WDT"),
            Reset4700Cause.OpcodeTrap => (4, 0x24DC, true, "OpcodeTrap"),
            Reset4700Cause.Nmi => (6, 0x003C, false, "NMI"),
            _ => (-1, -1, false, "Unknown")
        };
        return vector.Item1 < 0 ? new(null, null, false, vector.Item4,
            Result(Reset4700Verdict.UnknownSource, "ResetVectorNotEstablished")) :
            new(vector.Item1, vector.Item2, vector.Item3, vector.Item4,
                Result(Reset4700Verdict.SpecificationMatches, "ResetVectorStructurallyEstablished"));
    }

    internal static Reset4700Field StandardResetField(string name, Reset4700Variant variant)
    {
        var applicable = Enum.IsDefined(variant) && variant != Reset4700Variant.UnknownEcu;
        var definition = name switch
        {
            "SSP" => (Reset4700StateKind.ManufacturerDefinedResetValue, (int?)0xFFFF, 16),
            "ACC" => (Reset4700StateKind.ManufacturerDefinedResetValue, (int?)0, 16),
            "PSWL readback" => (Reset4700StateKind.ManufacturerDefinedResetValue, (int?)0xC8, 8),
            "PSWH readback" => (Reset4700StateKind.ManufacturerDefinedResetValue, (int?)0x0C, 8),
            // The specification's MIP label and user's-manual MIE label differ;
            // this model establishes bit8 reset0, not new priority semantics.
            "CF" or "ZF" or "HC" or "DD" or "PSW bit8" =>
                (Reset4700StateKind.ManufacturerDefinedResetValue, (int?)0, 1),
            "SCB" => (Reset4700StateKind.ManufacturerDefinedResetValue, (int?)0, 3),
            "LRB" => (Reset4700StateKind.UndefinedAfterReset, (int?)null, 16),
            "SF" => (Reset4700StateKind.NotSpecified, (int?)null, 1),
            _ => (Reset4700StateKind.NotSpecified, (int?)null, 16)
        };
        return new(name, definition.Item1, definition.Item2, definition.Item3,
            "Invented standard RES-qualified reset projection of E2E1027-27-Y4 page10", applicable);
    }

    internal static Reset4700Preservation ConditionalLrbPreservation(int? independentlyKnownPrior,
        string? priorSource, bool? applicableRetentionDocument, bool? priorHistoryRetained,
        Reset4700Origin origin = Reset4700Origin.InventedSpecification)
    {
        if (independentlyKnownPrior is int word) RequireWord(word);
        if (origin != Reset4700Origin.InventedSpecification)
            return new(independentlyKnownPrior, null, Reset4700StateKind.ManufacturerDefinedPreservedValue,
                Result(Reset4700Verdict.InvalidProvenance, "HostPriorLrbRejected"));
        // LRB is a13-bit register; the nonexistent upper3 bits always read0.
        // Undefined postreset content is not permission to preserve an invalid
        // full16-bit readback projection from an invented prior state.
        if (independentlyKnownPrior > 0x1FFF)
            return new(independentlyKnownPrior, null, Reset4700StateKind.ManufacturerDefinedPreservedValue,
                Result(Reset4700Verdict.InvalidProvenance, "InvalidLrbReadbackProjection"));
        var known = independentlyKnownPrior is not null && !string.IsNullOrWhiteSpace(priorSource) &&
            applicableRetentionDocument == true && priorHistoryRetained == true;
        return new(independentlyKnownPrior, known ? independentlyKnownPrior : null,
            Reset4700StateKind.ManufacturerDefinedPreservedValue,
            Result(known ? Reset4700Verdict.SpecificationMatches : Reset4700Verdict.UnknownSource,
                "ConditionalLrbPreservationOnly",
                "User-manual retention is conditional; specification's undefined LRB cannot become reset zero"));
    }

    internal static Reset4700Result CheckField(Reset4700Field field)
    {
        if (!Enum.IsDefined(field.Kind) || !Enum.IsDefined(field.Origin) ||
            string.IsNullOrWhiteSpace(field.Name) || string.IsNullOrWhiteSpace(field.Source) ||
            field.WidthBits is not (1 or 3 or 8 or 16))
            return Result(Reset4700Verdict.InvalidProvenance, "ResetSourceInvalid");
        if (field.Origin != Reset4700Origin.InventedSpecification)
            return Result(Reset4700Verdict.InvalidProvenance, "HostResetStateRejected");
        if (!field.DeviceApplicable)
            return Result(Reset4700Verdict.UnknownSource, "DeviceApplicabilityConditional");
        var canonical = StandardResetField(field.Name, Reset4700Variant.Msm66201);
        if (field.Kind != canonical.Kind || field.WidthBits != canonical.WidthBits ||
            (canonical.Value is not null && field.Value != canonical.Value))
            return Result(Reset4700Verdict.InvalidProvenance, "ResetSpecificationDoesNotMatch");
        if (field.Kind is Reset4700StateKind.UndefinedAfterReset or Reset4700StateKind.NotSpecified or
            Reset4700StateKind.ExternalHardwareDependent or Reset4700StateKind.RevisionDependent)
            return Result(field.Value is null ? Reset4700Verdict.UnknownSource : Reset4700Verdict.InvalidProvenance,
                field.Kind.ToString(), "Undefined/unspecified state cannot be filled with a convenient value");
        if (field.Value is null || field.Value < 0 || field.Value >= (1 << field.WidthBits))
            return Result(Reset4700Verdict.UnknownSource, "ResetValueOrPreservedHistoryMissing");
        return Result(Reset4700Verdict.SpecificationMatches, field.Kind.ToString());
    }

    internal static Reset4700Psw PswReadback(int written, bool? internalSf)
    {
        RequireWord(written);
        // Read-one bits 0CC8 are not writable storage. SF is separate internal
        // state and cannot be inferred from the writable PSW clear.
        var writable = written & 0xF337;
        return new(writable, writable | 0x0CC8, internalSf);
    }

    internal static Reset4700Result WdtWrite(Reset4700Wdt wdt)
    {
        if (!Enum.IsDefined(wdt.Meaning) || wdt.Origin != Reset4700Origin.InventedSpecification ||
            wdt.Address != 0x11 || wdt.WidthBytes != 1 || wdt.Command != 0x3C || wdt.WriteOnly != true)
            return Result(Reset4700Verdict.InvalidProvenance, "ExactWdtWriteAuthorityMissing");
        // No applicable primary meaning for3C is sealed in this milestone's
        // model. A supplied true boolean cannot manufacture that authority.
        if (wdt.Meaning != Reset4700WdtCommand.MeaningNotEstablished || wdt.CommandPrimaryEstablished == true)
            return Result(Reset4700Verdict.InvalidProvenance, "UnsupportedWdtCommandGuess");
        return Result(Reset4700Verdict.UnknownSource, "WdtCommandMeaningNotEstablished",
            "WdtExternalEffectsNotEstablished; stopped reset state does not specify the later3C command");
    }

    internal static int? WdtReadback(Reset4700Wdt _) => null;

    internal static Reset4700Result WdtHardwareContinuation(Reset4700Wdt wdt,
        bool? NoImmediateControlTransition, bool? ActualClockResetHistory, int? HostElapsedTicks = null)
    {
        if (HostElapsedTicks is not null)
            return Result(Reset4700Verdict.InvalidProvenance, "UnsupportedWdtTimerProgress");
        // Invented immediate-continuation/clock booleans cannot supply the
        // missing applicable3C command semantics or actual hardware history.
        return WdtWrite(wdt);
    }

    internal static Reset4700Region Memory(Reset4700Variant variant, Reset4700Space space,
        int address, int widthBytes = 1)
    {
        RequireWord(address);
        if (widthBytes is not (1 or 2)) throw new ArgumentOutOfRangeException(nameof(widthBytes));
        if (!Enum.IsDefined(variant) || !Enum.IsDefined(space) || variant == Reset4700Variant.UnknownEcu)
            return Reset4700Region.Unknown;
        if (space == Reset4700Space.Program) return Reset4700Region.Program;
        if (address + widthBytes > 0x10000) return Reset4700Region.Unknown;
        var end = address + widthBytes - 1;
        if (address <= 7 && end <= 7) return Reset4700Region.RegisterArea;
        if (address >= 8 && end <= 0x7F) return Reset4700Region.Sfr;
        var lastInternal = variant is Reset4700Variant.Msm66201 or Reset4700Variant.Msm66P201 ? 0x27F : 0x47F;
        if (address >= 0x80 && end <= lastInternal) return Reset4700Region.InternalRam;
        if (address > lastInternal) return Reset4700Region.ExternalData;
        return Reset4700Region.Unknown; // A cross-boundary word is not one established object.
    }

    internal static Reset4700Result NativeData4700(Reset4700NativeAddress source)
    {
        if (source.Origin != Reset4700Origin.InventedSpecification ||
            string.IsNullOrWhiteSpace(source.Source))
            return Result(Reset4700Verdict.InvalidProvenance, "NativeDpSourceMissing");
        if (source.Dp is null || source.RetainedAddressing != true || source.InternalSf != false)
            return Result(Reset4700Verdict.UnknownSource, "AliasOrContextUnknown");
        return source.WriterPc == 0x2519 && source.Dp == 0x4700 && source.ReaderPc == 0x251C &&
            source.Space == Reset4700Space.Data && source.WidthBytes == 1 ?
            Result(Reset4700Verdict.SpecificationMatches, "ExternalDataAddressEstablished",
                "BoardDecodeNotEstablished / ExternalReadValueUnknown / RuntimeReadNotObserved") :
            Result(Reset4700Verdict.SpecificationMismatch, "WrongData4700FormOrSource");
    }

    internal static Reset4700BitSlice SymbolicB7AfterMb(Reset4700TaintDomain domain)
    {
        if (!NumericDomain(domain)) return new(0, 0, 0xFF, 0xFF);
        // RB24F1 clears bit1; SRLB transfers external bit0 into CF; MB251E
        // changes only bit0. Old bits2..7 stay old, not zero-filled.
        return new(0x02, 0, 0x01, 0xFC);
    }

    internal static Reset4700Projection ProjectNumericByte(int inventedExternalByte, int inventedOldB7)
    {
        RequireByte(inventedExternalByte); RequireByte(inventedOldB7);
        var cleared = inventedOldB7 & 0xFD;
        var carry = (inventedExternalByte & 1) != 0;
        var stored = (cleared & 0xFE) | (carry ? 1 : 0);
        var taken = (stored & 2) != 0;
        return new(cleared, stored, carry, inventedExternalByte >> 1, taken, taken ? 0x2528 : 0x2524);
    }

    internal static (int Al, int? Ah, bool Dd, bool Zf, bool? Cf, bool? Hc) ByteLoadProjection(
        int inventedByte, int? oldAh, bool? oldCf, bool? oldHc, bool? internalSf)
    {
        if (internalSf != false) throw new InvalidDataException("LB [DP] requires a separately established nonstack SF0 context");
        RequireByte(inventedByte);
        if (oldAh is int high) RequireByte(high);
        return (inventedByte, oldAh, false, inventedByte == 0, oldCf, oldHc);
    }

    internal static (int Al, bool Cf, bool Zf, bool? Hc, bool Dd) ShiftRightProjection(
        int inventedAl, bool incomingZf, bool? incomingHc, bool? incomingDd)
    {
        if (incomingDd != false) throw new InvalidDataException("Byte SRLB projection requires an independently known DD0 context");
        RequireByte(inventedAl);
        return (inventedAl >> 1, (inventedAl & 1) != 0, incomingZf, incomingHc, false);
    }

    internal static (int A, bool Dd, bool Zf, bool? Cf, bool? Hc) CodeOwnedWordLoad252E(
        bool nativeReached, bool? oldCf, bool? oldHc, bool? internalSf)
    {
        if (!nativeReached) throw new InvalidDataException("L252E source requires its own reaching hypothesis");
        if (internalSf != false) throw new InvalidDataException("L252E requires a separately established nonstack SF0 context");
        return (0x5555, true, false, oldCf, oldHc);
    }

    internal static (bool Cf, bool Zf) CodeOwnedEqualCompare2535(int independentlyOwnedLeft,
        int independentlyOwnedRight)
    {
        RequireWord(independentlyOwnedLeft); RequireWord(independentlyOwnedRight);
        return (independentlyOwnedLeft < independentlyOwnedRight,
            independentlyOwnedLeft == independentlyOwnedRight);
    }

    internal static Reset4700Result ValueNoninterference(Reset4700TaintDomain domain, int checkpointPc)
    {
        if (!NumericDomain(domain)) return Result(Reset4700Verdict.UnknownSource, "AliasOrContextUnknown");
        if (checkpointPc != 0x2524)
            return Result(Reset4700Verdict.UnknownSource, "NumericDomainNotAuditedBeyond2524");
        var slice = SymbolicB7AfterMb(domain);
        return (slice.KnownMask & 2) != 0 && (slice.KnownValue & 2) == 0 &&
            (slice.ExternalValueMask & 2) == 0 ?
            Result(Reset4700Verdict.SpecificationMatches, "ValueNoninterferenceProvenWithinDomain",
                "JBS2521 falls through2524; ExternalReadSideEffectsUnknown remains separate") :
            Result(Reset4700Verdict.SpecificationMismatch, "ValueDependentControlGate");
    }

    internal static Reset4700BitSlice OverwriteBit(Reset4700BitSlice old, int bit,
        bool? codeValue, bool nativeSourceEstablished)
    {
        if (bit is < 0 or > 7) throw new ArgumentOutOfRangeException(nameof(bit));
        var mask = 1 << bit;
        return codeValue is null || !nativeSourceEstablished ? old with
        {
            KnownMask = old.KnownMask & ~mask,
            KnownValue = old.KnownValue & ~mask,
            PriorRamMask = old.PriorRamMask | mask
        } : old with
        {
            KnownMask = old.KnownMask | mask,
            KnownValue = (old.KnownValue & ~mask) | (codeValue.Value ? mask : 0),
            ExternalValueMask = old.ExternalValueMask & ~mask,
            PriorRamMask = old.PriorRamMask & ~mask
        };
    }

    internal static Reset4700Result WholeHardwareContinuation(Reset4700TaintDomain domain,
        bool? ActualReadObserved, bool? NumericProofClaimedAsNoSideEffects = null)
    {
        if (NumericProofClaimedAsNoSideEffects == true)
            return Result(Reset4700Verdict.InvalidProvenance, "ValueProofCannotEraseHiddenReadEffects");
        if (domain.BoardDecodeEstablished != true || domain.ReadSideEffectsEstablished != true)
            return Result(Reset4700Verdict.PreflightBlocked, "ExternalReadSideEffectsUnknown");
        return Result(Reset4700Verdict.PreflightBlocked, "RuntimeReadNotObserved",
            ActualReadObserved == true ? "An invented observation is not actual machine history" : "Actual read history missing");
    }

    internal static Reset4700Result ExternalControl(Reset4700ExternalPredicate predicate)
    {
        if (predicate.Origin != Reset4700Origin.InventedSpecification)
            return Result(Reset4700Verdict.InvalidProvenance, "InjectedExternalPredicateRejected");
        if (predicate.NativeReaderEstablished != true || predicate.Value is null)
            return Result(Reset4700Verdict.UnknownSource, "ExternalPredicateNotEstablished");
        if (predicate.Signal == "P4.1 at2528")
            return Result(Reset4700Verdict.SpecificationMatches, "ValueDependentControlGate",
                predicate.Value.Value ? "Invented P4.1 value1 selects252B, not the RAM-test path" :
                    "Invented P4.1 value0 selects252E; no actual pin observation supplied");
        if (predicate.Signal != "PWM IRQH.5 at264B" || predicate.SameHistoryAfterClear261E != true)
            return Result(Reset4700Verdict.UnknownSource, "FreshExternalPendingHistoryMissing");
        return Result(Reset4700Verdict.SpecificationMatches, "ValueDependentControlGate",
            predicate.Value.Value ? "Invented old pending1 yieldsZF0 and JNE264E" :
                "Invented old pending0 yieldsZF1 and fault2650");
    }

    internal static Reset4700Result CheckPreflight(Reset4700Preflight preflight)
    {
        if (preflight.Origin != Reset4700Origin.InventedSpecification)
            return Result(Reset4700Verdict.InvalidProvenance, "HostOrSyntheticRootRejected");
        var obligations = new (string Name, bool? Established)[]
        {
            ("Exact device/revision applicability", preflight.ExactDeviceRevision),
            ("Actual reset transition/history", preflight.ActualResetHistory),
            ("Rooted native prefix", preflight.RootedPrefix),
            ("Applicable WDT clock/reset effects", preflight.WdtEffects),
            ("External DATA read effects", preflight.ExternalReadEffects),
            ("P4 waveform observations", preflight.P4Waveform),
            ("Fresh PWM pending factor", preflight.FreshPwmIrq),
            ("Exact admitted ISA", preflight.ExactIsa),
            ("Same-machine history", preflight.SameMachineHistory),
            ("Native CAL2689 frame", preflight.NativeFrame),
            ("Existing runtime admission", preflight.ExistingAdmission),
            ("Safe lawful mechanism", preflight.SafeMechanism)
        };
        var missing = obligations.FirstOrDefault(o => o.Established != true);
        return missing.Name is not null ? Result(Reset4700Verdict.PreflightBlocked,
            "RootedNativeExecutionPreflightBlocked", missing.Name) :
            Result(Reset4700Verdict.SpecificationMatches, "InventedPolicyMatchesOnly",
                "InventedOnly cannot establish actual reset, native CAL, or execution permission");
    }

    internal static void RequireActualClaim(Reset4700Result result, string claim) =>
        throw new InvalidDataException($"{result.EvidenceDomain} cannot establish {claim}");

    private static bool NumericDomain(Reset4700TaintDomain domain) => domain.NativeDp2519 == true &&
        domain.ExactByteIsa == true && domain.NativeBit1Clear24F1 == true &&
        domain.RetainedB7Addressing == true && domain.NoInterveningBit1Write == true &&
        domain.NoAsyncContextChange == true && domain.NumericSliceComplete == true &&
        domain.NonstackSfEstablished == true;
    private static Reset4700Result Result(Reset4700Verdict verdict, string classification, string barrier = "") =>
        new(verdict, classification, barrier);
    private static void RequireByte(int value)
    {
        if (value is < 0 or > 0xFF) throw new ArgumentOutOfRangeException(nameof(value));
    }
    private static void RequireWord(int value)
    {
        if (value is < 0 or > 0xFFFF) throw new ArgumentOutOfRangeException(nameof(value));
    }
}
