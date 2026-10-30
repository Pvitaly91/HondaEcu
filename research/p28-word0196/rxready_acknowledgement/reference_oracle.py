"""Independent documentary expectations; no research-model or CPU imports.

Source-derived facts and explicitly unknown relations were frozen before the
M2ck analysis model was invoked. These are expected static claims, not target
execution observations or a receiver state machine.
"""

from copy import deepcopy


# The final item in every tuple is documentary provenance, not live authority.
_FINDINGS = (
    ("source-user", "SourceFinding", "IncompleteBody_EditionUnknown_SevenCrcFailures", ("UserIncomplete",)),
    ("source-isa", "SourceFinding", "FirstEdition_September1991_InstructionManual_NotPeripheralAckAuthority", ("ISA1991",)),
    ("source-japanese", "SourceFinding", "J2E1027-27-Y3_January1998_Specification_NotUserManual", ("JapaneseY3",)),
    ("source-english", "SourceFinding", "E2E1027-27-Y4_January1998_KnownEditionMirror_NotUserManual", ("EnglishY4",)),
    ("source-databook", "SourceFinding", "FifthEdition_June1990_PreliminaryDeviceSpecifications_NotUserManual", ("DataBook1990",)),
    ("source-oldspec", "SourceFinding", "Preliminary66201Specification_DocumentWideEditionUnknown_NotErratum", ("OldSpec66201",)),
    ("limit-index", "AuthorityLimit", "IndexAndFilenameAreLocators_NotPrimarySemanticEvidence", ("SearchIndexes",)),
    ("limit-crossfamily", "AuthorityLimit", "CoreAssemblyCompatibilityDoesNotEstablishPeripheralEquivalence", ("ISA1991", "CrossFamilyLocators")),
    ("rx-generation", "ManufacturerSourceQualified", "EligibleCompletionTransfersSRBUFAndGeneratesRXRequest_SourceQualified", ("UserIncomplete",)),
    ("mpc-filter", "ManufacturerSourceQualified", "FilterEnabledMpc0_NoNewSRBUF_NoNewRXRequest_SourceQualified", ("UserIncomplete",)),
    ("overrun-replacement", "ManufacturerSourceQualified", "UnreadMayBeReplaced_NewOverrunNotFinalStickyStatus_SourceQualified", ("UserIncomplete",)),
    ("receiver-permit", "ManufacturerSourceQualified", "SRREN1Permits_ModeChangeRequires0_SyncMasterAutoClearAfterFrame_SourceQualified", ("UserIncomplete",)),
    ("error-request-suppression", "UnknownRelation", "MERR_PERR_FERR_RequestSuppressionUnknown", ("UserIncomplete",)),
    ("srbuf-read-ack", "UnknownRelation", "ReadAcknowledgementUnknown_BothReadClearAndNoSideEffectUnsupported", ("UserIncomplete", "EnglishY4", "JapaneseY3")),
    ("entry-generic-ack", "ManufacturerSourceQualified", "ServicedIRQCleared_MIECleared_IERetained_SourceQualified", ("UserIncomplete",)),
    ("entry-rx-ack", "ConditionalSourceJoin", "RXBit1GenericEntryAckJoinConditional_NotActualIRQ", ("UserIncomplete", "ISA1991")),
    ("reassert-without-completion", "UnknownRelation", "AutomaticReassertionWithoutNewCompletionUnknown", ("UserIncomplete",)),
    ("pending-enable", "ManufacturerSourceQualified", "RequestGenerationDistinctFromDelivery_NotUnlimitedLifetimeProof", ("UserIncomplete",)),
    ("collision-priority", "UnknownRelation", "HardwareSet_SoftwareClear_EntryAck_Read_NewCompletionPriorityUnknown", ("UserIncomplete",)),
    ("ie-polarity", "SourceConflict", "EvidenceFavorsSet1_165_168_169_With167ConflictRetained", ("UserIncomplete",)),
    ("software-clear54ea", "StaticConditional", "Completed54EAClearCutsPreclearGeneration_PostclearOrConcurrentOwnerNeeded", ("M2cjStatic", "UserIncomplete")),
    ("mask-writers", "StaticConditional", "54F0_3F14_3F28_WritersStatic_CurrentIE_MIE_OwnersUnknown", ("M2cjStatic",)),
    ("read0262", "StaticConditional", "0262ByteReadSRBUF0055_NotObserved", ("M2cjStatic", "UserIncomplete")),
    ("compare0264", "StaticConditional", "0264ComparesR5With2_NotReceivedF", ("M2cjStatic",)),
    ("store0269", "StaticConditional", "0269StoresALTo03F3_NoOddFRequirement_NotObserved", ("M2cjStatic",)),
    ("return029c", "StaticConditional", "029CReturnsMatchingSavedForegroundPC_NotHost28AE_NotObserved", ("M2cjStatic", "ISA1991", "UserIncomplete")),
    ("frame-safety", "UnknownNativeContext", "EightByteFrameRequiresOwnedSSPAndPhysicalSafety_Unknown", ("M2cjStatic", "UserIncomplete")),
    ("authority-execution", "RuntimeAuthorityExcluded", "ExecutionBlocked_NoCPU_ROM_IRQ_RTI_FirmwareReadyFalse", ("M2ckScope",)),
)


def expected_records():
    """Return the full fixed documentary stream, including unknown fields."""
    return [
        {
            "recordId": "m2ck-" + topic,
            "recordClass": record_class,
            "topic": topic,
            "conclusion": conclusion,
            "sourceIds": list(sources),
            "actualObservation": None,
            "executionBlocked": True,
            "firmwareReady": False,
        }
        for topic, record_class, conclusion, sources in _FINDINGS
    ]


def expected_claims():
    return {topic: conclusion for topic, _, conclusion, _ in _FINDINGS}


def expected_document_identities():
    """Independent raw identities, not a claim of complete document authority."""
    return deepcopy({
        "UserIncomplete": {"sha256": "f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf", "bytes": 16203609, "documentId": None},
        "ISA1991": {"sha256": "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271", "bytes": 4563117, "documentId": None},
        "JapaneseY3": {"sha256": "9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a", "bytes": 602102, "documentId": "J2E1027-27-Y3"},
        "EnglishY4": {"sha256": "247913724eb291e20c869d42ba40363268fba415ab787b7c843e2a094533f0fe", "bytes": 589158, "documentId": "E2E1027-27-Y4"},
        "DataBook1990": {"sha256": "88aae3b11782ae1b8bfea0f112b81c342232a98ed75e39b6aac6ea3ad5f54e82", "bytes": 25444912, "documentId": None},
        "OldSpec66201": {"sha256": "2d538a3d80c45df662bb7cd6ed8282b252173d42022d7ca54bc34639f8b519eb", "bytes": 644783, "documentId": None},
    })


# Every value changes an evidence relation or physical/runtime assertion. None
# is merely a renamed case or a cosmetic metadata spelling.
REFUSED_HYPOTHESES = (
    ("srbuf-read-ack", True),
    ("srbuf-read-ack", False),
    ("srbuf-read-ack", "ReadClearsRQSRRDY"),
    ("srbuf-read-ack", "ReadNeverClearsRQSRRDY"),
    ("entry-generic-ack", "EntryClearsEveryPendingFactor"),
    ("entry-rx-ack", "NativeRXIRQObserved"),
    ("reassert-without-completion", "UnreadBufferAutomaticallyReasserts"),
    ("reassert-without-completion", "FreshCompletionIsAlwaysRequiredForReentry"),
    ("error-request-suppression", "MERRSuppressesEveryRXRequest"),
    ("error-request-suppression", "PERRSuppressesEveryRXRequest"),
    ("error-request-suppression", "FERRSuppressesEveryRXRequest"),
    ("collision-priority", "HardwareSetAlwaysWins"),
    ("collision-priority", "SoftwareClearAlwaysWins"),
    ("collision-priority", "SRBUFReadAlwaysPrecedesEntryAcknowledgement"),
    ("collision-priority", "NewCompletionAlwaysOverridesAcknowledgement"),
    ("ie-polarity", "IE1VerifiedForActualEcu"),
    ("ie-polarity", "IE0VerifiedForActualEcu"),
    ("ie-polarity", "Page167DescribesPostEntryIEClear"),
    ("receiver-permit", "ResetSRREN0ProvesCurrentReceiverDisabled"),
    ("mpc-filter", "EveryReceiveCompletionGeneratesRequest"),
    ("overrun-replacement", "UnreadBufferCannotBeReplaced"),
    ("overrun-replacement", "NoNewOverrunImpliesFinalOERR0"),
    ("pending-enable", "IEWriteGeneratesRXRequest"),
    ("pending-enable", "RequestBeforeEnableProvesUnlimitedLifetime"),
    ("software-clear54ea", "PreclearGenerationAloneSurvivesCompleted54EA"),
    ("software-clear54ea", "CurrentPendingOwnerEstablished"),
    ("mask-writers", "StaticMaskLiteralProvesCurrentIEAndMIEOwner"),
    ("read0262", "ActualCurrentSRBUFReadObserved"),
    ("compare0264", "CMPBComparesReceivedFWith2"),
    ("store0269", "OnlyOddFCanReach0269"),
    ("return029c", "RTIRestoresHost28AE"),
    ("return029c", "029CIsTheSavedForegroundPC"),
    ("frame-safety", "UnknownSSPIsPhysicallySafe"),
    ("frame-safety", "NumericDisjointnessProvesPhysicalStackSafety"),
    ("limit-index", "NoSearchHitProvesDocumentDoesNotExist"),
    ("limit-crossfamily", "SameAssemblyCoreProvesSamePeripheral"),
    ("authority-execution", "FirmwareReady=true"),
    ("authority-execution", "StaticCanonicalIsActualECUTrace"),
)
