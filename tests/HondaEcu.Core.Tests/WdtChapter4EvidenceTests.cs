namespace HondaEcu.Core.Tests;

public sealed class WdtChapter4EvidenceTests
{
    // Every identifier, digest, page claim, and context below is invented. No
    // candidate represents an acquired manufacturer document or an ECU event.
    private static WdtChapter4Document Candidate() => new("invented-document", "Invented hardware manual",
        WdtEvidenceOwner.Manufacturer, WdtEvidenceKind.HardwareManual, WdtEvidenceFamily.BothStandardParts,
        "invented-edition", true, "invented-archive-lineage", true, new string('a', 64), true,
        new string('b', 64), true, true, false, false, true, "invented Chapter4/table", true, 0x11, 0x3C, 1, true);

    private static WdtChapter4Context Context() => new(true, true, true, true, WdtEvidenceEffect.Immediate, true,
        WdtEvidenceHistoryOrigin.PrimaryDocumentOnly);

    [Fact]
    public void CompleteApplicableHypothesisMatchesOnlyTheInventedDocumentaryPolicy()
    {
        foreach (var family in new[] { WdtEvidenceFamily.Msm66201, WdtEvidenceFamily.Msm66207 })
        {
            var result = WdtChapter4EvidenceFixture.ReviewCommand(Candidate(), family);
            Assert.Equal(WdtEvidenceVerdict.PolicyMatchesOnly, result.Verdict);
            Assert.Equal("ApplicablePrimaryCommandPolicyMatchesOnly", result.Classification);
            AssertNoActualAuthority(result);
        }
    }

    [Fact]
    public void CompleteManualContainingWatchdogWithoutExactDefinitionRemainsNondecisive()
    {
        var document = Candidate() with { ExactCommand3cDescribed = false, ExactCommandLocator = null };
        Assert.Equal("CompleteDocumentPolicyMatchesOnly",
            WdtChapter4EvidenceFixture.ReviewDocument(document, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("WdtCommandMeaningNotEstablished",
            WdtChapter4EvidenceFixture.ReviewCommand(document, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void IncompleteArchiveDoesNotBecomeCompleteFromAnExactFilenameOrResetTable()
    {
        var document = Candidate() with { HardwareChapter4Complete = false, ExactCommand3cDescribed = null };
        Assert.Equal("PrimaryDocumentAcquiredButNonDecisive",
            WdtChapter4EvidenceFixture.ReviewDocument(document, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal(WdtEvidenceVerdict.EvidenceIncomplete,
            WdtChapter4EvidenceFixture.ReviewCommand(document, WdtEvidenceFamily.Msm66201).Verdict);
    }

    [Fact]
    public void TrustedExactRecoveredPageCanMatchPolicyWithoutInventingTheRestOfChapter()
    {
        var document = Candidate() with
        {
            HardwareChapter4Complete = false,
            RecoveredPages = true,
            RecoveredPageLineageVerified = true
        };
        Assert.Equal("PrimaryDocumentAcquiredButNonDecisive",
            WdtChapter4EvidenceFixture.ReviewDocument(document, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal(WdtEvidenceVerdict.PolicyMatchesOnly,
            WdtChapter4EvidenceFixture.ReviewCommand(document, WdtEvidenceFamily.Msm66201).Verdict);
    }

    [Fact]
    public void IndexOrSnippetWithoutActualBytesIsNotAcquiredPrimaryEvidence()
    {
        foreach (var available in new bool?[] { null, false })
        {
            var result = WdtChapter4EvidenceFixture.ReviewCommand(Candidate() with { RawBytesAvailable = available },
                WdtEvidenceFamily.Msm66201);
            Assert.Equal("SearchIndexOnly", result.Classification);
            AssertNoActualAuthority(result);
        }
        Assert.Equal("SearchIndexOnly", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { RawSha256 = "search-snippet" }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("ArchivalReferenceOnlyManualBytesNotAcquired", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Kind = WdtEvidenceKind.HistoricalHtmlReference },
            WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void ReadableMemberOfDamagedArchiveProvesOnlyItsOwnPageAssociationNotWholeManualIntegrity()
    {
        var page = new WdtChapter4ArchivePage(true, new string('a', 64), false, true, true, true);
        var result = WdtChapter4EvidenceFixture.ReviewArchivePage(page);
        Assert.Equal("ReadablePageAssociationOnlyWholeArchiveIntegrityNotEstablished", result.Classification);
        Assert.Equal(WdtEvidenceVerdict.PolicyMatchesOnly, result.Verdict);
        AssertNoActualAuthority(result);
        Assert.Equal("PrimarySourceIntegrityNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { IntegrityVerified = false }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("CorruptOrUnverifiedArchiveMember", WdtChapter4EvidenceFixture.ReviewArchivePage(
            page with { MemberCrcVerified = false }).Classification);
    }

    [Fact]
    public void VerifiedGapBoundariesDoNotRecoverContentsOrMakeEveryMissingPageAWatchdogPage()
    {
        Assert.Equal("MissingPrintedRangeKnownContentsNotRecovered",
            WdtChapter4EvidenceFixture.ReviewMissingPages(true, false, false, false).Classification);
        Assert.Equal("RecoveredPageContentsNotEstablished",
            WdtChapter4EvidenceFixture.ReviewMissingPages(true, true, true, null).Classification);
        Assert.Equal("RecoveredPageAssociationPolicyMatchesOnly",
            WdtChapter4EvidenceFixture.ReviewMissingPages(true, true, true, true).Classification);
        AssertNoActualAuthority(WdtChapter4EvidenceFixture.ReviewMissingPages(true, true, true, true));
    }

    [Fact]
    public void HashAndOcrTextCannotSubstituteForIntegrityAndFullPageVisualReview()
    {
        Assert.Equal("PrimarySourceIntegrityNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { IntegrityVerified = null }, WdtEvidenceFamily.Msm66201).Classification);
        foreach (var document in new[] { Candidate() with { FullRelevantPagesReviewed = false },
            Candidate() with { FullDocumentVisualIdentity = null } })
            Assert.Equal("FullPageReviewNotEstablished",
                WdtChapter4EvidenceFixture.ReviewCommand(document, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void RecoveredPagesNeedTrustedDocumentIdentityAndVerifiedRevision()
    {
        var recovered = Candidate() with { RecoveredPages = true };
        Assert.Equal("RecoveredPagesWithoutTrustedLineage", WdtChapter4EvidenceFixture.ReviewCommand(
            recovered, WdtEvidenceFamily.Msm66201).Classification);
        recovered = recovered with { RecoveredPageLineageVerified = true, RevisionVerified = null };
        Assert.Equal("RecoveredPagesRevisionUnverified", WdtChapter4EvidenceFixture.ReviewCommand(
            recovered, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("PrimaryDocumentIdentityNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            recovered with { DocumentaryLineage = null }, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void ExactCommandClaimNeedsVerifiedEditionAndAnExactSourceLocator()
    {
        Assert.Equal("EditionRevisionNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { EditionRevision = null }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("WdtCommandMeaningNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { ExactCommandLocator = " " }, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void ACommandClaimAtAnotherRegisterOrWithAnotherByteWidthDoesNotDecodeTheExactWrite()
    {
        foreach (var document in new[] { Candidate() with { WdtRegisterAddress = 0x10 },
            Candidate() with { CommandByte = 0xC3 }, Candidate() with { WriteWidthBytes = 2 },
            Candidate() with { WriteOnlyEstablished = null } })
            Assert.Equal("ExactWdtCommandFormNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
                document, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void ManufacturerOwnedCrossFamilyThreeCIsALeadNotPeripheralCompatibility()
    {
        Assert.Equal("ManufacturerCrossFamilyLeadOnly", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Family = WdtEvidenceFamily.OtherFamily }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("WdtCommandMeaningNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { WdtPeripheralCompatibilityEstablished = false }, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void Standard201CoverageDoesNotAcquireStandard207Applicability()
    {
        var document = Candidate() with { Family = WdtEvidenceFamily.Msm66201 };
        Assert.Equal(WdtEvidenceVerdict.PolicyMatchesOnly,
            WdtChapter4EvidenceFixture.ReviewCommand(document, WdtEvidenceFamily.Msm66201).Verdict);
        Assert.Equal("ManufacturerCrossFamilyLeadOnly",
            WdtChapter4EvidenceFixture.ReviewCommand(document, WdtEvidenceFamily.Msm66207).Classification);
    }

    [Fact]
    public void ThirdPartyDescriptionAndCpuInstructionManualAreNotPeripheralCommandProof()
    {
        Assert.Equal("SecondaryEvidenceOnly", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Owner = WdtEvidenceOwner.ThirdParty }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("WdtCommandMeaningNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Kind = WdtEvidenceKind.InstructionManual }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal(WdtEvidenceVerdict.PolicyMatchesOnly, WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Kind = WdtEvidenceKind.PeripheralApplicationNote }, WdtEvidenceFamily.Msm66201).Verdict);
    }

    [Fact]
    public void NullUnknownAndMalformedIdentitiesFailClosed()
    {
        Assert.Equal(WdtEvidenceVerdict.EvidenceIncomplete,
            WdtChapter4EvidenceFixture.ReviewCommand(null, WdtEvidenceFamily.Msm66201).Verdict);
        Assert.Equal(WdtEvidenceVerdict.EvidenceIncomplete,
            WdtChapter4EvidenceFixture.ReviewCommand(Candidate(), WdtEvidenceFamily.Unknown).Verdict);
        Assert.Equal(WdtEvidenceVerdict.EvidenceRejected, WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Kind = (WdtEvidenceKind)999 }, WdtEvidenceFamily.Msm66201).Verdict);
        Assert.Equal("DeviceApplicabilityConditional", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Family = WdtEvidenceFamily.Unknown }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("PrimaryDocumentTypeNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { Kind = WdtEvidenceKind.Unknown }, WdtEvidenceFamily.Msm66201).Classification);
        Assert.Equal("AcquisitionOriginNotEstablished", WdtChapter4EvidenceFixture.ReviewCommand(
            Candidate() with { RecoveredPages = null }, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void ByteAndVisualIdenticalMirrorsAreOneDocumentNotIndependentConfirmations()
    {
        var mirror = Candidate() with { DocumentaryLineage = "invented-other-mirror-url" };
        var result = WdtChapter4EvidenceFixture.CompareDocuments(Candidate(), mirror, WdtEvidenceFamily.Msm66201);
        Assert.Equal("ByteAndVisualDuplicateDocument", result.Classification);
        Assert.Equal(1, result.InventedDocumentarySourceCount);
        AssertNoActualAuthority(result);
    }

    [Fact]
    public void DifferentContainerBytesWithIdenticalFullPageVisualsAreStillOneDocument()
    {
        var mirror = Candidate() with
        {
            RawSha256 = new string('c', 64),
            DocumentaryLineage = "invented-repackaged-mirror"
        };
        var result = WdtChapter4EvidenceFixture.CompareDocuments(Candidate(), mirror, WdtEvidenceFamily.Msm66201);
        Assert.Equal("VisualMirrorOfSameDocument", result.Classification);
        Assert.Equal(1, result.InventedDocumentarySourceCount);
    }

    [Fact]
    public void IdenticalFullPageVisualsWithConflictingIdentityCannotBecomeIndependentRevisionVotes()
    {
        var recontainered = Candidate() with
        {
            RawSha256 = new string('c', 64),
            DocumentaryLineage = "invented-other-wrapper"
        };
        foreach (var document in new[]
        {
            recontainered with { DocumentId = "invented-different-id", EditionRevision = "invented-other-edition" },
            recontainered with { Family = WdtEvidenceFamily.Msm66201 },
            recontainered with { Kind = WdtEvidenceKind.SpecificationSheet },
            recontainered with { Title = "Invented different document title" }
        })
        {
            var result = WdtChapter4EvidenceFixture.CompareDocuments(Candidate(), document, WdtEvidenceFamily.Msm66201);
            Assert.Equal("VisualIdentityWithConflictingDocumentMetadata", result.Classification);
            Assert.Equal(WdtEvidenceVerdict.EvidenceRejected, result.Verdict);
            Assert.Null(result.InventedDocumentarySourceCount);
        }
    }

    [Fact]
    public void SameBytesWithConflictingVisualOrDeviceMetadataCannotBeCreditedTwice()
    {
        foreach (var mirror in new[] { Candidate() with { FullDocumentVisualIdentity = new string('d', 64) },
            Candidate() with { Family = WdtEvidenceFamily.Msm66201 } })
            Assert.Equal("ByteIdentityWithConflictingDocumentMetadata",
                WdtChapter4EvidenceFixture.CompareDocuments(Candidate(), mirror, WdtEvidenceFamily.Msm66201).Classification);
    }

    [Fact]
    public void ConflictingRevisionsOfTheSameDocumentAreNotResolvedByChoosingTheFavorableCopy()
    {
        var revision = Candidate() with
        {
            EditionRevision = "invented-other-edition",
            RawSha256 = new string('c', 64),
            FullDocumentVisualIdentity = new string('d', 64)
        };
        var result = WdtChapter4EvidenceFixture.CompareDocuments(Candidate(), revision, WdtEvidenceFamily.Msm66201);
        Assert.Equal("DocumentRevisionConflictUnresolved", result.Classification);
        Assert.Equal(WdtEvidenceVerdict.EvidenceRejected, result.Verdict);
        Assert.Null(result.InventedDocumentarySourceCount);
    }

    [Fact]
    public void SharedLineageIsNotIndependentEvenWhenFileAndVisualHashesDiffer()
    {
        var copy = Candidate() with
        {
            DocumentId = "invented-rescan-id",
            RawSha256 = new string('c', 64),
            FullDocumentVisualIdentity = new string('d', 64)
        };
        Assert.Equal("SharedDocumentaryLineageNotIndependent", WdtChapter4EvidenceFixture.CompareDocuments(
            Candidate(), copy, WdtEvidenceFamily.Msm66201).Classification);
        copy = copy with { DocumentaryLineage = "invented-independent-original" };
        Assert.Equal(2, WdtChapter4EvidenceFixture.CompareDocuments(Candidate(), copy,
            WdtEvidenceFamily.Msm66201).InventedDocumentarySourceCount);
    }

    [Fact]
    public void WriteOnlyReadbackCannotConfirmThatACommandWasAcceptedOrExecuted()
    {
        var result = WdtChapter4EvidenceFixture.UseEvidence(Candidate(), WdtEvidenceFamily.Msm66201,
            WdtEvidenceUse.WriteOnlyReadback, true);
        Assert.Equal("WriteOnlyReadbackCannotConfirmCommand", result.Classification);
        AssertNoActualAuthority(result);
        Assert.Equal("RegisterAccessSemanticsNotEstablished", WdtChapter4EvidenceFixture.UseEvidence(
            Candidate(), WdtEvidenceFamily.Msm66201, WdtEvidenceUse.WriteOnlyReadback).Classification);
    }

    [Fact]
    public void StoppedResetStateDoesNotDecodeTheLaterThreeCWrite()
    {
        Assert.Equal("ResetStoppedDoesNotDecode3c", WdtChapter4EvidenceFixture.UseEvidence(Candidate(),
            WdtEvidenceFamily.Msm66201, WdtEvidenceUse.ResetStoppedAsCommandMeaning).Classification);
    }

    [Fact]
    public void HostTimeAndDocumentedCyclesCannotSupplyPhysicalClockOrHardwareEventOwnership()
    {
        var expectations = new[]
        {
            (WdtEvidenceUse.HostElapsedTime, "HostTimeIsNotHardwareClockEvidence"),
            (WdtEvidenceUse.DocumentedCyclesAsPhysicalTime, "DocumentedCyclesAreNotPhysicalTime"),
            (WdtEvidenceUse.HardwareEventAsCodeOwned, "ExternalHardwareEventIsNotCodeOwned")
        };
        foreach (var (use, classification) in expectations)
        {
            var result = WdtChapter4EvidenceFixture.UseEvidence(Candidate(), WdtEvidenceFamily.Msm66201, use);
            Assert.Equal(classification, result.Classification);
            Assert.Equal(WdtEvidenceVerdict.EvidenceRejected, result.Verdict);
        }
    }

    [Fact]
    public void DelayedEffectEvidenceCannotAssertAnImmediateCpuOrResetEffect()
    {
        var delayed = Context() with { DocumentedEffect = WdtEvidenceEffect.Delayed };
        Assert.Equal("ImmediateAndDelayedEffectsAreNotInterchangeable", WdtChapter4EvidenceFixture.ReviewContinuation(
            Candidate(), WdtEvidenceFamily.Msm66201, delayed, WdtEvidenceEffect.Immediate).Classification);
        Assert.Equal("EffectScopeNotEstablished", WdtChapter4EvidenceFixture.ReviewContinuation(Candidate(),
            WdtEvidenceFamily.Msm66201, Context() with { EffectSourceEstablished = null },
            WdtEvidenceEffect.Immediate).Classification);
    }

    [Fact]
    public void StandardPartDocumentDoesNotVerifyTheActualEcuDeviceMaskOrBoard()
    {
        foreach (var context in new[] { Context() with { ExactEcuDeviceVerified = null },
            Context() with { ExactEcuRevisionVerified = false } })
            Assert.Equal("DeviceApplicabilityConditional", WdtChapter4EvidenceFixture.ReviewContinuation(
                Candidate(), WdtEvidenceFamily.Msm66201, context, WdtEvidenceEffect.Immediate).Classification);
    }

    [Fact]
    public void UnknownOscillatorAndResetReleaseHistoryRemainSeparateMandatoryDependencies()
    {
        Assert.Equal("HardwareClockDependent", WdtChapter4EvidenceFixture.ReviewContinuation(Candidate(),
            WdtEvidenceFamily.Msm66201, Context() with { ClockEstablished = null },
            WdtEvidenceEffect.Immediate).Classification);
        Assert.Equal("ResetReleaseHistoryNotEstablished", WdtChapter4EvidenceFixture.ReviewContinuation(Candidate(),
            WdtEvidenceFamily.Msm66201, Context() with { ResetReleaseHistoryEstablished = false },
            WdtEvidenceEffect.Immediate).Classification);
    }

    [Fact]
    public void DocumentedCommandEvenWithAllInventedContextHypothesesIsNotAnActualContinuation()
    {
        var result = WdtChapter4EvidenceFixture.ReviewContinuation(Candidate(), WdtEvidenceFamily.Msm66201,
            Context(), WdtEvidenceEffect.Immediate);
        Assert.Equal(WdtEvidenceVerdict.PreflightBlocked, result.Verdict);
        Assert.Equal("ActualHardwareHistoryNotEstablished", result.Classification);
        AssertNoActualAuthority(result);
        foreach (var origin in new[] { WdtEvidenceHistoryOrigin.TechnicalConstructor, WdtEvidenceHistoryOrigin.HostPcSeed })
            Assert.Equal("TechnicalStateCannotBecomeActualResetHistory", WdtChapter4EvidenceFixture.ReviewContinuation(
                Candidate(), WdtEvidenceFamily.Msm66201, Context() with { HistoryOrigin = origin },
                WdtEvidenceEffect.Immediate).Classification);
    }

    [Fact]
    public void ResetCauseVectorAndDefaultsCannotBeBorrowedFromAnotherCause()
    {
        foreach (var (cause, vector) in new[] { (WdtEvidenceCause.ExternalRes, 0), (WdtEvidenceCause.Brk, 2),
            (WdtEvidenceCause.Watchdog, 4), (WdtEvidenceCause.OpcodeTrap, 4), (WdtEvidenceCause.Nmi, 6) })
        {
            var result = WdtChapter4EvidenceFixture.ReviewResetCause(cause, cause, vector, false);
            Assert.Equal(WdtEvidenceVerdict.PolicyMatchesOnly, result.Verdict);
            Assert.Equal(cause == WdtEvidenceCause.Nmi ? "InterruptCausePolicyMatchesOnly" :
                "ResetCausePolicyMatchesOnly", result.Classification);
            AssertNoActualAuthority(result);
        }
        Assert.Equal("ResetCauseEvidenceMismatch", WdtChapter4EvidenceFixture.ReviewResetCause(
            WdtEvidenceCause.ExternalRes, WdtEvidenceCause.Brk, 2, false).Classification);
        Assert.Equal("CauseAndVectorEvidenceMismatch", WdtChapter4EvidenceFixture.ReviewResetCause(
            WdtEvidenceCause.Watchdog, WdtEvidenceCause.Watchdog, 0, false).Classification);
        Assert.Equal("ResetDefaultsCannotBeTransferredAcrossCauses", WdtChapter4EvidenceFixture.ReviewResetCause(
            WdtEvidenceCause.Brk, WdtEvidenceCause.Brk, 2, true).Classification);
    }

    [Fact]
    public void SupplyRiseAloneDoesNotEstablishAQualifiedExternalResSequence()
    {
        Assert.Equal("SupplyRiseDoesNotEstablishQualifiedRes", WdtChapter4EvidenceFixture.ReviewResetCause(
            WdtEvidenceCause.PowerOn, WdtEvidenceCause.PowerOn, 0, false).Classification);
        var qualifiedHypothesis = WdtChapter4EvidenceFixture.ReviewResetCause(
            WdtEvidenceCause.PowerOn, WdtEvidenceCause.PowerOn, 0, false, true);
        Assert.Equal(WdtEvidenceVerdict.PolicyMatchesOnly, qualifiedHypothesis.Verdict);
        AssertNoActualAuthority(qualifiedHypothesis);
    }

    [Fact]
    public void DocumentarySuccessCannotEnableCal2689Preflight()
    {
        var result = WdtChapter4EvidenceFixture.UseEvidence(Candidate(), WdtEvidenceFamily.Msm66201,
            WdtEvidenceUse.Cal2689Preflight);
        Assert.Equal("FalseCal2689PreflightRejected", result.Classification);
        Assert.Equal(WdtEvidenceVerdict.PreflightBlocked, result.Verdict);
        AssertNoActualAuthority(result);
        Assert.Equal("ActualHardwareHistoryNotEstablished", WdtChapter4EvidenceFixture.UseEvidence(Candidate(),
            WdtEvidenceFamily.Msm66201, WdtEvidenceUse.ActualContinuation).Classification);
    }

    private static void AssertNoActualAuthority(WdtChapter4Result result)
    {
        Assert.Equal("InventedOnly", result.EvidenceDomain);
        Assert.Equal(0, result.ActualRomExecutions); Assert.Equal(0, result.SyntheticRomExecutions);
        Assert.False(result.ActualRuntimePermission); Assert.False(result.ActualResetTransitionObserved);
        Assert.False(result.ActualNative24f8Observed); Assert.False(result.ActualCal2689Observed);
        Assert.False(result.HardwareSafeReachingEstablished);
        Assert.Equal("ActualHardwareHistoryNotEstablished", result.ActualHardwareHistory);
        Assert.Null(result.ActualEventIndex); Assert.Null(result.ActualGlobalWriteOrdinal);
    }
}
