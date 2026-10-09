namespace HondaEcu.Core.Tests;

// Invented documentary acceptance policy, not a watchdog, reset, timer, or CPU
// model. No method loads source files/ROMs, constructs Cpu/Bus, or executes code.
internal enum WdtEvidenceFamily { Unknown, Msm66201, Msm66207, BothStandardParts, OtherFamily }
internal enum WdtEvidenceOwner { Unknown, Manufacturer, ThirdParty }
internal enum WdtEvidenceKind { Unknown, HardwareManual, SpecificationSheet, InstructionManual, PeripheralApplicationNote, HistoricalHtmlReference }
internal enum WdtEvidenceVerdict { PolicyMatchesOnly, EvidenceIncomplete, EvidenceRejected, PreflightBlocked }
internal enum WdtEvidenceUse
{
    DocumentaryCommand, WriteOnlyReadback, ResetStoppedAsCommandMeaning,
    HostElapsedTime, DocumentedCyclesAsPhysicalTime, HardwareEventAsCodeOwned, ActualContinuation, Cal2689Preflight
}
internal enum WdtEvidenceEffect { Unknown, Immediate, Delayed }
internal enum WdtEvidenceCause { Unknown, ExternalRes, PowerOn, Brk, Watchdog, OpcodeTrap, Nmi }
internal enum WdtEvidenceHistoryOrigin { Unknown, PrimaryDocumentOnly, HardwareObservationClaim, TechnicalConstructor, HostPcSeed }

internal sealed record WdtChapter4Document(string? DocumentId, string? Title,
    WdtEvidenceOwner Owner, WdtEvidenceKind Kind, WdtEvidenceFamily Family,
    string? EditionRevision, bool? RevisionVerified, string? DocumentaryLineage,
    bool? RawBytesAvailable, string? RawSha256, bool? IntegrityVerified,
    string? FullDocumentVisualIdentity, bool? FullRelevantPagesReviewed,
    bool? HardwareChapter4Complete, bool? RecoveredPages, bool? RecoveredPageLineageVerified,
    bool? ExactCommand3cDescribed, string? ExactCommandLocator, bool? WdtPeripheralCompatibilityEstablished,
    int? WdtRegisterAddress, int? CommandByte, int? WriteWidthBytes, bool? WriteOnlyEstablished);

internal sealed record WdtChapter4Result(WdtEvidenceVerdict Verdict, string Classification,
    int? InventedDocumentarySourceCount = null)
{
    internal string EvidenceDomain => "InventedOnly";
    internal int ActualRomExecutions => 0;
    internal int SyntheticRomExecutions => 0;
    internal bool ActualRuntimePermission => false;
    internal bool ActualResetTransitionObserved => false;
    internal bool ActualNative24f8Observed => false;
    internal bool ActualCal2689Observed => false;
    internal bool HardwareSafeReachingEstablished => false;
    internal string ActualHardwareHistory => "ActualHardwareHistoryNotEstablished";
    internal int? ActualEventIndex => null;
    internal long? ActualGlobalWriteOrdinal => null;
}

internal sealed record WdtChapter4Context(bool? ExactEcuDeviceVerified,
    bool? ExactEcuRevisionVerified, bool? ResetReleaseHistoryEstablished,
    bool? ClockEstablished, WdtEvidenceEffect DocumentedEffect,
    bool? EffectSourceEstablished, WdtEvidenceHistoryOrigin HistoryOrigin);

internal sealed record WdtChapter4ArchivePage(bool? RawContainerAvailable, string? RawContainerSha256,
    bool? WholeArchiveIntegrityVerified, bool? MemberCrcVerified,
    bool? CompletePageReviewed, bool? PrintedPageAssociationVerified);

internal static class WdtChapter4EvidenceFixture
{
    internal static WdtChapter4Result ReviewDocument(WdtChapter4Document? document, WdtEvidenceFamily target)
    {
        if (document is null || target is not (WdtEvidenceFamily.Msm66201 or WdtEvidenceFamily.Msm66207))
            return Incomplete("DeviceApplicabilityConditional");
        if (!Enum.IsDefined(document.Owner) || !Enum.IsDefined(document.Kind) || !Enum.IsDefined(document.Family))
            return Rejected("InvalidDocumentaryIdentity");
        if (document.RawBytesAvailable != true || !IsDigest(document.RawSha256))
            return Incomplete("SearchIndexOnly");
        if (document.IntegrityVerified != true)
            return Incomplete("PrimarySourceIntegrityNotEstablished");
        if (document.Kind == WdtEvidenceKind.HistoricalHtmlReference)
            return Incomplete("ArchivalReferenceOnlyManualBytesNotAcquired");
        if (document.Kind == WdtEvidenceKind.Unknown)
            return Incomplete("PrimaryDocumentTypeNotEstablished");
        if (document.Owner != WdtEvidenceOwner.Manufacturer)
            return Incomplete("SecondaryEvidenceOnly");
        if (string.IsNullOrWhiteSpace(document.DocumentId) || string.IsNullOrWhiteSpace(document.Title) ||
            string.IsNullOrWhiteSpace(document.DocumentaryLineage))
            return Incomplete("PrimaryDocumentIdentityNotEstablished");
        if (document.RecoveredPages is null)
            return Incomplete("AcquisitionOriginNotEstablished");
        if (document.RecoveredPages == true && document.RecoveredPageLineageVerified != true)
            return Rejected("RecoveredPagesWithoutTrustedLineage");
        if (string.IsNullOrWhiteSpace(document.EditionRevision) || document.RevisionVerified != true)
            return Incomplete(document.RecoveredPages == true ?
                "RecoveredPagesRevisionUnverified" : "EditionRevisionNotEstablished");
        if (document.Family == WdtEvidenceFamily.Unknown)
            return Incomplete("DeviceApplicabilityConditional");
        if (document.Family != target && document.Family != WdtEvidenceFamily.BothStandardParts)
            return Incomplete("ManufacturerCrossFamilyLeadOnly");
        if (document.FullRelevantPagesReviewed != true || !IsDigest(document.FullDocumentVisualIdentity))
            return Incomplete("FullPageReviewNotEstablished");
        return Matches(document.Kind == WdtEvidenceKind.HardwareManual && document.HardwareChapter4Complete == true ?
            "CompleteDocumentPolicyMatchesOnly" : "PrimaryDocumentAcquiredButNonDecisive");
    }

    internal static WdtChapter4Result ReviewCommand(WdtChapter4Document? document, WdtEvidenceFamily target)
    {
        var acquired = ReviewDocument(document, target);
        if (acquired.Verdict != WdtEvidenceVerdict.PolicyMatchesOnly) return acquired;
        // A CPU instruction manual or the mere word "watchdog" is not an
        // applicable peripheral command definition. Completeness alone is not
        // sufficient; a verified partial manufacturer source can be decisive.
        if (document!.Kind is not (WdtEvidenceKind.HardwareManual or WdtEvidenceKind.SpecificationSheet or
            WdtEvidenceKind.PeripheralApplicationNote) || document.WdtPeripheralCompatibilityEstablished != true ||
            document.ExactCommand3cDescribed != true || string.IsNullOrWhiteSpace(document.ExactCommandLocator))
            return Incomplete("WdtCommandMeaningNotEstablished");
        if (document.WdtRegisterAddress != 0x11 || document.CommandByte != 0x3C || document.WriteWidthBytes != 1 ||
            document.WriteOnlyEstablished != true)
            return Incomplete("ExactWdtCommandFormNotEstablished");
        return Matches("ApplicablePrimaryCommandPolicyMatchesOnly");
    }

    internal static WdtChapter4Result ReviewArchivePage(WdtChapter4ArchivePage? page)
    {
        if (page is null || page.RawContainerAvailable != true || !IsDigest(page.RawContainerSha256))
            return Incomplete("RawArchiveNotAcquired");
        if (page.MemberCrcVerified != true)
            return Rejected("CorruptOrUnverifiedArchiveMember");
        if (page.CompletePageReviewed != true || page.PrintedPageAssociationVerified != true)
            return Incomplete("PrintedPageAssociationNotEstablished");
        // A sound member can document its own printed-page association while
        // another member is corrupt. This neither repairs raw bytes nor grants
        // integrity, completeness, edition, or command authority to the manual.
        return Matches(page.WholeArchiveIntegrityVerified == true ? "ReadablePageAssociationPolicyMatchesOnly" :
            "ReadablePageAssociationOnlyWholeArchiveIntegrityNotEstablished");
    }

    internal static WdtChapter4Result ReviewMissingPages(bool? BoundaryPagesVerified,
        bool? RecoveredRawPageBytes, bool? CompleteRecoveredPagesReviewed, bool? RecoveredSectionIdentityVerified)
    {
        if (BoundaryPagesVerified != true) return Incomplete("MissingPrintedRangeNotEstablished");
        if (RecoveredRawPageBytes != true)
            return Incomplete("MissingPrintedRangeKnownContentsNotRecovered");
        if (CompleteRecoveredPagesReviewed != true || RecoveredSectionIdentityVerified != true)
            return Incomplete("RecoveredPageContentsNotEstablished");
        return Matches("RecoveredPageAssociationPolicyMatchesOnly");
    }

    internal static WdtChapter4Result CompareDocuments(WdtChapter4Document? left, WdtChapter4Document? right,
        WdtEvidenceFamily target)
    {
        var first = ReviewDocument(left, target);
        var second = ReviewDocument(right, target);
        if (first.Verdict != WdtEvidenceVerdict.PolicyMatchesOnly) return first;
        if (second.Verdict != WdtEvidenceVerdict.PolicyMatchesOnly) return second;
        var sameIdentity = left!.DocumentId == right!.DocumentId;
        if (sameIdentity && left.EditionRevision != right.EditionRevision)
            return Rejected("DocumentRevisionConflictUnresolved");
        var sameBytes = string.Equals(left.RawSha256, right.RawSha256, StringComparison.OrdinalIgnoreCase);
        var sameVisual = string.Equals(left.FullDocumentVisualIdentity, right.FullDocumentVisualIdentity,
            StringComparison.OrdinalIgnoreCase);
        if (sameBytes && (!sameVisual || left.Family != right.Family || left.EditionRevision != right.EditionRevision))
            return Rejected("ByteIdentityWithConflictingDocumentMetadata");
        if (sameVisual && (left.Family != right.Family || left.EditionRevision != right.EditionRevision ||
            left.DocumentId != right.DocumentId || left.Kind != right.Kind || left.Title != right.Title))
            return Rejected("VisualIdentityWithConflictingDocumentMetadata");
        if (sameBytes && sameVisual) return Matches("ByteAndVisualDuplicateDocument", 1);
        if (sameVisual && left.EditionRevision == right.EditionRevision)
            return Matches("VisualMirrorOfSameDocument", 1);
        if (sameIdentity || left.DocumentaryLineage == right.DocumentaryLineage)
            return Matches("SharedDocumentaryLineageNotIndependent", 1);
        return Matches("DistinctInventedDocumentarySources", 2);
    }

    internal static WdtChapter4Result UseEvidence(WdtChapter4Document? document, WdtEvidenceFamily target,
        WdtEvidenceUse use, bool? WriteOnlyEstablished = null)
    {
        if (!Enum.IsDefined(use)) return Rejected("InvalidEvidenceUse");
        // None of these alternative claims can manufacture the missing exact
        // command definition, physical history, or a runtime admission.
        return use switch
        {
            WdtEvidenceUse.DocumentaryCommand => ReviewCommand(document, target),
            WdtEvidenceUse.WriteOnlyReadback => WriteOnlyEstablished == true ?
                Rejected("WriteOnlyReadbackCannotConfirmCommand") : Incomplete("RegisterAccessSemanticsNotEstablished"),
            WdtEvidenceUse.ResetStoppedAsCommandMeaning => Rejected("ResetStoppedDoesNotDecode3c"),
            WdtEvidenceUse.HostElapsedTime => Rejected("HostTimeIsNotHardwareClockEvidence"),
            WdtEvidenceUse.DocumentedCyclesAsPhysicalTime => Rejected("DocumentedCyclesAreNotPhysicalTime"),
            WdtEvidenceUse.HardwareEventAsCodeOwned => Rejected("ExternalHardwareEventIsNotCodeOwned"),
            WdtEvidenceUse.Cal2689Preflight => Blocked("FalseCal2689PreflightRejected"),
            _ => Blocked("ActualHardwareHistoryNotEstablished")
        };
    }

    internal static WdtChapter4Result ReviewContinuation(WdtChapter4Document? document, WdtEvidenceFamily target,
        WdtChapter4Context? context, WdtEvidenceEffect claimedEffect)
    {
        var command = ReviewCommand(document, target);
        if (command.Verdict != WdtEvidenceVerdict.PolicyMatchesOnly) return command;
        if (context is null || !Enum.IsDefined(context.DocumentedEffect) || !Enum.IsDefined(claimedEffect) ||
            !Enum.IsDefined(context.HistoryOrigin))
            return Incomplete("EffectScopeNotEstablished");
        if (context.HistoryOrigin is WdtEvidenceHistoryOrigin.TechnicalConstructor or WdtEvidenceHistoryOrigin.HostPcSeed)
            return Rejected("TechnicalStateCannotBecomeActualResetHistory");
        if (context.DocumentedEffect == WdtEvidenceEffect.Unknown || context.EffectSourceEstablished != true)
            return Incomplete("EffectScopeNotEstablished");
        if (claimedEffect == WdtEvidenceEffect.Unknown || context.DocumentedEffect != claimedEffect)
            return Rejected("ImmediateAndDelayedEffectsAreNotInterchangeable");
        if (context.ExactEcuDeviceVerified != true || context.ExactEcuRevisionVerified != true)
            return Blocked("DeviceApplicabilityConditional");
        if (context.ClockEstablished != true) return Blocked("HardwareClockDependent");
        if (context.ResetReleaseHistoryEstablished != true) return Blocked("ResetReleaseHistoryNotEstablished");
        // Even all-true invented hypotheses are not hardware observations.
        return Blocked("ActualHardwareHistoryNotEstablished");
    }

    internal static WdtChapter4Result ReviewResetCause(WdtEvidenceCause cause, WdtEvidenceCause documentedCause,
        int? documentedVectorWordAddress, bool? DefaultsTransferredFromOtherCause,
        bool? PowerOnResQualificationEstablished = null)
    {
        if (!Enum.IsDefined(cause) || !Enum.IsDefined(documentedCause) || cause == WdtEvidenceCause.Unknown ||
            documentedCause == WdtEvidenceCause.Unknown || documentedVectorWordAddress is null)
            return Incomplete("ResetCauseEvidenceNotEstablished");
        if (DefaultsTransferredFromOtherCause != false)
            return Rejected("ResetDefaultsCannotBeTransferredAcrossCauses");
        if (cause == WdtEvidenceCause.PowerOn && PowerOnResQualificationEstablished != true)
            return Incomplete("SupplyRiseDoesNotEstablishQualifiedRes");
        if (cause != documentedCause)
            return Rejected("ResetCauseEvidenceMismatch");
        var expected = cause switch
        {
            WdtEvidenceCause.ExternalRes or WdtEvidenceCause.PowerOn => 0,
            WdtEvidenceCause.Brk => 2,
            WdtEvidenceCause.Watchdog or WdtEvidenceCause.OpcodeTrap => 4,
            WdtEvidenceCause.Nmi => 6,
            _ => -1
        };
        return documentedVectorWordAddress == expected ? Matches(cause == WdtEvidenceCause.Nmi ?
            "InterruptCausePolicyMatchesOnly" : "ResetCausePolicyMatchesOnly") :
            Rejected("CauseAndVectorEvidenceMismatch");
    }

    private static bool IsDigest(string? value) => value is { Length: 64 } && value.All(Uri.IsHexDigit);
    private static WdtChapter4Result Matches(string classification, int? count = null) =>
        new(WdtEvidenceVerdict.PolicyMatchesOnly, classification, count);
    private static WdtChapter4Result Incomplete(string classification) =>
        new(WdtEvidenceVerdict.EvidenceIncomplete, classification);
    private static WdtChapter4Result Rejected(string classification) =>
        new(WdtEvidenceVerdict.EvidenceRejected, classification);
    private static WdtChapter4Result Blocked(string classification) =>
        new(WdtEvidenceVerdict.PreflightBlocked, classification);
}
