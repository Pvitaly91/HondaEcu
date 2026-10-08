namespace HondaEcu.Core.Tests;

public sealed class C8EqualityEvidenceTests
{
    [Theory]
    [InlineData("duplicateBytes")]
    [InlineData("duplicateVisuals")]
    [InlineData("crossFamily")]
    [InlineData("wrongOpcode")]
    [InlineData("unverifiedRevision")]
    [InlineData("emulatorOnly")]
    [InlineData("unknownNativeCmpFlags")]
    [InlineData("selectedResultWithoutBranchTrace")]
    [InlineData("missingMachineIdentity")]
    [InlineData("vendorOldTableQuoteOnly")]
    [InlineData("wrongConditionComparison")]
    [InlineData("hostFlags")]
    [InlineData("unverifiedSiliconClaimedActualRom")]
    [InlineData("expectedFromExistingExecutor")]
    public void RequiredNegativeEvidenceCasesCannotResolveThePrimaryConflict(string failure)
    {
        var record = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        var document = C8EvidenceClassificationFixture.InventedDeclaration(C8EvidenceKind.PrimaryCorrection, false);
        var witness = failure switch
        {
            "duplicateBytes" => document with { ContentIdentity = C8EvidenceClassificationFixture.OriginalContentIdentity },
            "duplicateVisuals" => document with { VisualIdentity = C8EvidenceClassificationFixture.OriginalVisualIdentity },
            "crossFamily" => record with { Applicability = C8Applicability.AssemblyFamilySimilarity },
            "wrongOpcode" => record with { InstructionBytes = [0xF0, 0x04] },
            "unverifiedRevision" => record with { RevisionVerified = false },
            "emulatorOnly" => record with { EmulatorOnly = true },
            "unknownNativeCmpFlags" => ReplaceEquality(record, record.Observations[1] with { Cf = null, Zf = null }),
            "selectedResultWithoutBranchTrace" => ReplaceEquality(record, record.Observations[1] with { BranchTraceRecorded = false }),
            "missingMachineIdentity" => record with { MachineIdentity = "" },
            "vendorOldTableQuoteOnly" => C8EvidenceClassificationFixture.InventedDeclaration(C8EvidenceKind.VendorResponse, false)
                with
            { QuotesOldTableOnly = true, VendorSiliconConfirmed = false },
            "wrongConditionComparison" => record with { Condition = "GE" },
            "hostFlags" => ReplaceEquality(record, record.Observations[1] with { FlagProvenance = C8FlagProvenance.HostFlags }),
            "unverifiedSiliconClaimedActualRom" => record with { RecordingProvenanceVerified = false, ClaimsActualRomExecution = true },
            "expectedFromExistingExecutor" => record with { ExpectedFromExistingExecutor = true },
            _ => throw new InvalidDataException("Unknown negative fixture.")
        };
        var result = C8EvidenceClassificationFixture.Classify(witness);
        Assert.Equal(failure == "emulatorOnly" ? C8EvidenceClassification.SecondaryEvidenceOnly : C8EvidenceClassification.PrimaryConflictUnresolved,
            result.Classification);
        Assert.Equal(C8ReportedPredicate.NotEstablished, result.ReportedPredicate);
        Assert.False(string.IsNullOrWhiteSpace(result.Reason));
        Assert.Equal(0, result.ActualRomExecutions);
        Assert.Throws<InvalidDataException>(result.RequireActualRomExecution);
    }

    [Theory]
    [InlineData(false, (int)C8ReportedPredicate.ReportedAnd)]
    [InlineData(true, (int)C8ReportedPredicate.ReportedOr)]
    public void ExplicitPrimaryCorrectionIsDocumentaryClarificationNotVendorSiliconConfirmation(bool taken, int predicate)
    {
        var result = C8EvidenceClassificationFixture.Classify(
            C8EvidenceClassificationFixture.InventedDeclaration(C8EvidenceKind.PrimaryCorrection, taken));
        Assert.Equal(C8EvidenceClassification.PrimaryDocumentClarification, result.Classification);
        Assert.Equal((C8ReportedPredicate)predicate, result.ReportedPredicate);
        Assert.Equal(0, result.ActualRomExecutions);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void ScopedVendorSiliconStatementIsSeparateFromThePrintedFormula(bool taken)
    {
        var witness = C8EvidenceClassificationFixture.InventedDeclaration(C8EvidenceKind.VendorResponse, taken);
        var result = C8EvidenceClassificationFixture.Classify(witness);
        Assert.Equal(C8EvidenceClassification.VendorConfirmed, result.Classification);
        Assert.Equal(taken ? C8ReportedPredicate.ReportedOr : C8ReportedPredicate.ReportedAnd, result.ReportedPredicate);
        Assert.Equal(C8EvidenceClassification.PrimaryConflictUnresolved,
            C8EvidenceClassificationFixture.Classify(witness with { VendorSiliconConfirmed = false }).Classification);
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public void NativeThreeCaseRecordsNeedExactDeviceOrIndependentExactC8Applicability(bool taken, bool compatibleOtherChip)
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(taken);
        if (compatibleOtherChip) witness = witness with
        {
            Applicability = C8Applicability.IndependentExactC8Compatibility,
            ApplicabilityEvidenceIdentity = "invented-independent-exact-C8-applicability-proof"
        };
        var result = C8EvidenceClassificationFixture.Classify(witness);
        Assert.Equal(C8EvidenceClassification.IndependentCompatibleSiliconConfirmed, result.Classification);
        Assert.Equal(taken ? C8ReportedPredicate.ReportedOr : C8ReportedPredicate.ReportedAnd, result.ReportedPredicate);
        Assert.Equal("InventedEvidencePolicyOnly", result.Scope);
        Assert.Equal(0, result.ActualRomExecutions);
        Assert.Throws<InvalidDataException>(result.RequireActualRomExecution);
    }

    [Theory]
    [InlineData(false, 0xFFFF, 0x0000)]
    [InlineData(true, 0xFFFF, 0x0000)]
    [InlineData(false, 0x0100, 0x00FE)]
    [InlineData(true, 0x0100, 0x00FE)]
    public void NonadjacentAndBoundaryOperandsStillFormTheSameThreeNativeCmpControls(bool taken, int greaterLeft, int greaterRight)
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(taken);
        witness = witness with
        {
            Observations =
            [
                witness.Observations[0] with { Left = (ushort)greaterLeft, Right = (ushort)greaterRight },
                witness.Observations[1] with { Left = (ushort)greaterRight, Right = (ushort)greaterRight },
                witness.Observations[2] with { Left = (ushort)greaterRight, Right = (ushort)greaterLeft }
            ]
        };
        var result = C8EvidenceClassificationFixture.Classify(witness);
        Assert.Equal(C8EvidenceClassification.IndependentCompatibleSiliconConfirmed, result.Classification);
        Assert.Equal(taken ? C8ReportedPredicate.ReportedOr : C8ReportedPredicate.ReportedAnd, result.ReportedPredicate);
        Assert.Equal(0, result.ActualRomExecutions);
    }

    [Theory]
    [InlineData((int)C8EvidenceKind.VendorResponse)]
    [InlineData((int)C8EvidenceKind.PrimaryCorrection)]
    [InlineData((int)C8EvidenceKind.SiliconRecord)]
    public void UnauthenticatedSourceNeverInheritsAuthorityFromItsClaimedKind(int kind)
    {
        var witness = kind == (int)C8EvidenceKind.SiliconRecord
            ? C8EvidenceClassificationFixture.InventedSiliconRecord(false)
            : C8EvidenceClassificationFixture.InventedDeclaration((C8EvidenceKind)kind, false);
        AssertUnresolved(witness with { SourceAuthenticated = false });
        AssertUnresolved(witness with { IndependentContent = false });
    }

    [Theory]
    [InlineData("unknownApplicability")]
    [InlineData("otherCore")]
    [InlineData("unverifiedApplicability")]
    [InlineData("missingExactCompatibilityProof")]
    public void CompatibilityClaimsNeedMoreThanInstructionNamingOrAssemblyFamilySimilarity(string failure)
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        AssertUnresolved(failure switch
        {
            "unknownApplicability" => witness with { Applicability = C8Applicability.Unknown },
            "otherCore" => witness with { Applicability = C8Applicability.OtherCore },
            "unverifiedApplicability" => witness with { ApplicabilityVerified = false },
            _ => witness with { Applicability = C8Applicability.IndependentExactC8Compatibility, ApplicabilityEvidenceIdentity = "" }
        });
    }

    [Theory]
    [InlineData("unknownCmpInstruction")]
    [InlineData("changedFlags")]
    [InlineData("operandFlagMismatch")]
    [InlineData("wrongTraceOpcode")]
    [InlineData("wrongTraceCondition")]
    [InlineData("wrongDisplacement")]
    [InlineData("wrongDestination")]
    [InlineData("unverifiedDestination")]
    [InlineData("unverifiedBytes")]
    public void NativeEqualityObservationMustRetainCmpFlagsAndAnIndependentlyVerifiedC8BranchTrace(string failure)
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        var equality = witness.Observations[1];
        equality = failure switch
        {
            "unknownCmpInstruction" => equality with { CmpInstructionAndOperandsVerified = false },
            "changedFlags" => equality with { FlagsUnchanged = false },
            "operandFlagMismatch" => equality with { Cf = true, Zf = false },
            "wrongTraceOpcode" => equality with { Opcode = 0xF0 },
            "wrongTraceCondition" => equality with { Condition = "LE" },
            "wrongDisplacement" => equality with { Displacement = 0x05 },
            "wrongDestination" => equality with { ObservedNextPc = 0x1206 },
            "unverifiedDestination" => equality with { DestinationIndependentlyVerified = false },
            _ => equality with { BinaryBytesVerified = false }
        };
        AssertUnresolved(ReplaceEquality(witness, equality));
    }

    [Theory]
    [InlineData("unverifiedMachineIdentity")]
    [InlineData("missingRevision")]
    [InlineData("missingTime")]
    [InlineData("invalidTime")]
    [InlineData("missingMethod")]
    [InlineData("missingRawRecord")]
    [InlineData("unverifiedRecordProvenance")]
    [InlineData("uncontrolledBinary")]
    public void PhysicalRecordProvenanceIsRequiredEvenWhenItsSelectedOutcomesLookPlausible(string failure)
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        AssertUnresolved(failure switch
        {
            "unverifiedMachineIdentity" => witness with { MachineIdentityVerified = false },
            "missingRevision" => witness with { Revision = "" },
            "missingTime" => witness with { CapturedUtc = "" },
            "invalidTime" => witness with { CapturedUtc = "invented-not-a-timestampZ" },
            "missingMethod" => witness with { CaptureMethod = "" },
            "missingRawRecord" => witness with { RawRecordIdentity = "" },
            "unverifiedRecordProvenance" => witness with { RecordingProvenanceVerified = false },
            _ => witness with { BinaryControlVerified = false }
        });
    }

    [Fact]
    public void DifferentCaseBinariesRequirePreciselyVerifiedControlledDifferences()
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        witness = ReplaceEquality(witness, witness.Observations[1] with { BinaryIdentity = "invented-probe-binary-B" });
        AssertUnresolved(witness);
        Assert.Equal(C8EvidenceClassification.IndependentCompatibleSiliconConfirmed,
            C8EvidenceClassificationFixture.Classify(witness with { ControlledDifferencesVerified = true }).Classification);
    }

    [Fact]
    public void GreaterControlAloneCannotDistinguishTheDisputedFormulas()
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        AssertUnresolved(witness with { Observations = [witness.Observations[0]] });
    }

    [Theory]
    [InlineData((int)C8EvidenceKind.VendorResponse)]
    [InlineData((int)C8EvidenceKind.PrimaryCorrection)]
    public void DocumentaryDeclarationsNeedBothEqualityAndLessInsteadOfAnUnspecifiedGtName(int kind)
    {
        var witness = C8EvidenceClassificationFixture.InventedDeclaration((C8EvidenceKind)kind, false);
        AssertUnresolved(witness with { ReportedEqualityTaken = null });
        AssertUnresolved(witness with { ReportedLessTaken = null });
        AssertUnresolved(witness with { ReportedEqualityTaken = true, ReportedLessTaken = false });
    }

    [Fact]
    public void ContradictoryEqualityTracesCannotBeResolvedBySelectingTheDesiredObservation()
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        var oppositeEquality = witness.Observations[1] with { ObservedTaken = true, ObservedNextPc = 0x1206 };
        AssertUnresolved(witness with { Observations = [.. witness.Observations, oppositeEquality] });
    }

    [Fact]
    public void ContradictorySameRelationTracesCannotHideBehindDifferentOperandDistances()
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        var oppositeGreater = witness.Observations[0] with
        {
            Left = 0x33,
            ObservedTaken = false,
            ObservedNextPc = 0x1202
        };
        var oppositeLess = witness.Observations[2] with
        {
            Left = 0x20,
            ObservedTaken = true,
            ObservedNextPc = 0x1206
        };
        AssertUnresolved(witness with { Observations = [.. witness.Observations, oppositeGreater] });
        AssertUnresolved(witness with { Observations = [.. witness.Observations, oppositeLess] });
    }

    [Fact]
    public void MixedEqualityAndLessOrFailedGreaterControlRemainUnresolved()
    {
        var witness = C8EvidenceClassificationFixture.InventedSiliconRecord(false);
        AssertUnresolved(ReplaceEquality(witness, witness.Observations[1] with { ObservedTaken = true, ObservedNextPc = 0x1206 }));
        AssertUnresolved(witness with { Observations = [witness.Observations[0] with { ObservedTaken = false, ObservedNextPc = 0x1202 }, .. witness.Observations.Skip(1)] });
    }

    [Theory]
    [InlineData(0x1200, 0x04, 0x1206)]
    [InlineData(0x1200, 0xFC, 0x11FE)]
    [InlineData(0x1200, 0x7F, 0x1281)]
    [InlineData(0x1200, 0x80, 0x1182)]
    [InlineData(0xFFFF, 0x00, 0x0001)]
    [InlineData(0x0000, 0xFC, 0xFFFE)]
    public void AbstractRelativeTargetUsesSignedRel8AndPcPlusTwo(int pc, int displacement, int target) =>
        Assert.Equal((ushort)target, C8EvidenceClassificationFixture.RelativeTarget((ushort)pc, (byte)displacement));

    [Fact]
    public void CompleteInquiryDraftDoesNotImplySendingARequestOrReceivingAResponse()
    {
        var result = C8EvidenceClassificationFixture.Classify(new() { Kind = C8EvidenceKind.InquiryDraft, InquiryDraftComplete = true });
        Assert.Equal(C8EvidenceClassification.InquiryDraftReady, result.Classification);
        Assert.Equal(C8ReportedPredicate.NotEstablished, result.ReportedPredicate);
        Assert.Equal(0, result.ActualRomExecutions);
        Assert.Throws<InvalidDataException>(result.RequireActualRomExecution);
        AssertUnresolved(new() { Kind = C8EvidenceKind.InquiryDraft });
    }

    [Fact]
    public void OrdinarySecondarySourceHasNoNativeValidationAuthority()
    {
        var result = C8EvidenceClassificationFixture.Classify(new() { Kind = C8EvidenceKind.Secondary });
        Assert.Equal(C8EvidenceClassification.SecondaryEvidenceOnly, result.Classification);
        Assert.Equal(C8ReportedPredicate.NotEstablished, result.ReportedPredicate);
        Assert.Equal(0, result.ActualRomExecutions);
    }

    [Fact]
    public void EmptyOrUnknownEvidenceKindFailsClosed()
    {
        AssertUnresolved(new());
        AssertUnresolved(C8EvidenceClassificationFixture.InventedSiliconRecord(false) with { Kind = (C8EvidenceKind)99 });
    }

    private static C8EvidenceWitness ReplaceEquality(C8EvidenceWitness witness, C8BranchObservation equality) =>
        witness with { Observations = [witness.Observations[0], equality, witness.Observations[2]] };

    private static void AssertUnresolved(C8EvidenceWitness witness)
    {
        var result = C8EvidenceClassificationFixture.Classify(witness);
        Assert.Equal(C8EvidenceClassification.PrimaryConflictUnresolved, result.Classification);
        Assert.Equal(C8ReportedPredicate.NotEstablished, result.ReportedPredicate);
        Assert.Equal(0, result.ActualRomExecutions);
        Assert.Throws<InvalidDataException>(result.RequireActualRomExecution);
    }
}
