"""Independent expected documentary relations, fixed before model invocation.

The source facts were read from complete primary page images and the private
source-bound instruction review. Nothing here imports a production CPU or the
new research calculations. These controls are hypothetical, never observations.
"""
from copy import deepcopy


def reference_primary():
    return {
        'classification': 'ManufacturerSourceQualified',
        'deviceScope': 'RetainedUserBodyMSM66201_207_EditionAndActualEcuUnknown',
        'mapping': {'vectorAddress': 10, 'source': 'SerialReceivingReady',
            'irqBit': 1, 'ieBit': 1, 'requestSymbol': 'RQSRRDY', 'enableSymbol': 'IESRRDY'},
        'iePolarity': {'verdict': 'IEPolarityEvidenceFavorsSet1ButConflictRetained',
            'setOneAuthority': 'Printed165_17_2_2_AndFig17_2_Printed168',
            'setZeroParagraph': 'Printed167_AcceptanceCondition_NotPostEntryIEState',
            'contextResolvesConflict': False, 'manufacturerErratumAcquired': False,
            'actualEcuPolarity': None},
        'receiveSource': {'receiveEndTransfersShiftRegisterToSrbuf': True,
            'sameCompletionGeneratesRxReadyRequest': True,
            'ignoredMultiprocessorMpc0SuppressesBoth': True,
            'contentHeldUntilNextEligibleCompletion': True, 'srbufBits': 8,
            'srbufReadOnly': True, 'shiftRegisterSoftwareAccessible': False, 'actualByte': None},
        'receiverPermit': {'srconAddress': 84, 'srRenBit': 7, 'oneAllowsReception': True,
            'resetSrcon': 0, 'modeChangeRequiresReceiverDisabled': True,
            'synchronousMasterClearsAfterOneFrame': True, 'otherModesAutoClearSrRen': False,
            'actualCurrentSrcon': None},
        'overrun': {'unreadPriorDataSetsNewOverrunCondition': True,
            'newDataStillReplacesSrbuf': True, 'errorBitsStickyUntilSoftwareClear': True,
            'ignoredMpcErrorInteraction': None, 'actualSrstat': None},
        'requestLifecycle': {'servicedFactorClearedDuringMaskableEntry': True,
            'ieRetainedDuringEntry': True, 'mieClearedDuringEntry': True,
            'examplesAllowPendingBeforeLaterEnable': True, 'srbufReadClearsRequest': None,
            'automaticReassertion': None, 'everyReentryRequiresNewReceiveCompletion': None,
            'actualPendingOwner': None, 'actualDeliveryObserved': False},
        'newManufacturerDocuments': 0, 'cpuRomIrqRtiExecutions': 0,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False,
    }


def reference_completion(mode, master, srren, filter_mpc, mpc, prior_unread):
    """Independent finite receive-end truth relation, not a receiver model."""
    if mode not in ('uart_normal', 'uart_multiprocessor',
                    'synchronous_normal', 'synchronous_multiprocessor'):
        raise ValueError('UnsupportedMode')
    if any(type(v) is not bool for v in (master, srren, filter_mpc, prior_unread)):
        raise ValueError('StrictBooleanInputsRequired')
    multi = mode.endswith('_multiprocessor')
    synchronous = mode.startswith('synchronous_')
    if (not synchronous and master) or (not multi and (filter_mpc or mpc is not None)):
        raise ValueError('InapplicableModeField')
    if multi and (type(mpc) is not int or mpc not in (0, 1)):
        raise ValueError('MultiprocessorBitRequired')
    ignored = bool(multi and filter_mpc and mpc == 0) if srren else None
    transferred = (not ignored) if srren else None
    after = not (synchronous and master) if srren else None
    return {
        'classification': 'InventedOnly_ConditionalManufacturerRelation',
        'inputs': {'mode': mode, 'master': master, 'srren': srren,
            'filterMpc': filter_mpc, 'mpc': mpc, 'priorUnread': prior_unread},
        'admitted': srren,
        'refusal': None if srren else 'ReceiverPermitNotEstablished_SRREN0',
        'assumedReceiveEnd': True if srren else None, 'multiprocessIgnored': ignored,
        'srbufTransferExpected': transferred, 'rxReadyRequestExpected': transferred,
        'newOverrunConditionExpected': prior_unread if transferred else None,
        'srstatOerrAfter': None,
        'overrunRule': ('ReceiveEndNotAdmitted' if not srren else
                        'IgnoredMpcErrorInteractionUnspecified' if ignored else
                        'PriorUnreadOnAcceptedReceiveEnd'),
        'receiverPermitAfterFrame': after,
        'nextFrameNeedsReceiverReenable': (not after) if srren else None,
        'srbufValue': None, 'actualPendingOwner': None, 'actualReceiveEvent': None,
        'actualReadId': None, 'actualDeliveryObserved': False,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False,
    }


def reference_mask(mode, polarity):
    """Two documented pairs; enable interpretation remains a hypothesis."""
    if type(mode) is not int or mode not in (0, 1) or type(polarity) is not int or polarity not in (0, 1):
        raise ValueError('ClosedModeAndPolarityRequired')
    return {'modeBit': mode, 'pairId': 'A' if mode == 0 else 'B',
        'F8': 0x2BAB if mode == 0 else 0xA9A3, 'FA': 0x02A0 if mode == 0 else 0x00A0,
        'directIE': 0x2BAB if mode == 0 else 0xA9A3,
        'rxBit': 1, 'rxBodyBit': 0, 'rxTailBit': 1,
        'rxBodyAllowed': polarity == 0, 'rxTailAllowed': polarity == 1,
        'txBit': 2, 'txBitValue': 0, 'txAllowed': polarity == 0,
        'modeMeaning': 'SoftwareDATA0217.2_NotSRCON0054.2', 'polarityIsHypothesis': True,
        'pairQualification': 'ExpectedBy3E81Check_NotCurrentNativePair',
        'currentFAOwner': None, 'currentF8Owner': None, 'currentIEOwner': None,
        'currentStorageGeneration': None, 'actualHardwareApplicabilityEstablished': False,
        'actualDeliveryObserved': False}


def reference_pending(position, collision):
    if position not in ('before54EA', 'after54EA', 'unknown') or type(collision) is not bool:
        raise ValueError('ClosedPendingCutInputsRequired')
    return {'position': position, 'collisionHypothesis': collision,
        'softwareClearPC': 0x54EA, 'softwareClearWidth': 16, 'softwareClearWord': 0x0018,
        'postClearOrderingSatisfied': {'before54EA': False, 'after54EA': True, 'unknown': None}[position],
        'orderingProvesPendingState': False, 'priorPreClearGenerationSufficient': False,
        'currentPendingValue': None, 'currentPendingOwner': None, 'setClearWinner': None,
        'chainAssumedConditional': True, 'actualPendingObserved': False}


def reference_masks():
    """Expected source projection from the independently read mask audit."""
    a, b = (0x2BAB, 0x02A0), (0xA9A3, 0x00A0)
    chains = [
        {'id': 'ModeSwitchA', 'pairId': 'A',
            'pcs': [0x3F11, 0x3F14, 0x3F16, 0x3F18, 0x3F1D, 0x3F20],
            'IEWriterPC': 0x3F14, 'F8WriterPC': 0x3F16, 'FAWriterPC': 0x3F18,
            'modeWriterPC': 0x3F1D, 'modeAfter': 0, 'F8': a[0], 'FA': a[1], 'IE': a[0]},
        {'id': 'ModeSwitchB', 'pairId': 'B',
            'pcs': [0x3F25, 0x3F28, 0x3F2A, 0x3F2C, 0x3F31],
            'IEWriterPC': 0x3F28, 'F8WriterPC': 0x3F2A, 'FAWriterPC': 0x3F2C,
            'modeWriterPC': 0x3F31, 'modeAfter': 1, 'F8': b[0], 'FA': b[1], 'IE': b[0]},
        {'id': 'Initial54DD', 'pairId': 'A',
            'pcs': [0x54DD, 0x54E2, 0x54E5, 0x54E7, 0x54EA, 0x54ED, 0x54F0],
            'FAWriterPC': 0x54DD, 'F8WriterPC': 0x54E5, 'IRQClearPC': 0x54EA,
            'IEWriterPC': 0x54F0, 'modeWriterPC': None, 'modeAfter': None,
            'F8': a[0], 'FA': a[1], 'IE': a[0]},
    ]
    return {'classification': 'SourceQualifiedStaticMaskChronology_NotRuntime',
        'correctedSource': {'profile': 'UserTable17_1', 'vector': 10, 'bit': 1,
            'request': 'RQSRRDY', 'enable': 'IESRRDY', 'actualEcuApplicability': None},
        'words': {'F8': [248, 249], 'FA': [250, 251], 'IE': [26, 27], 'IRQ': [24, 25]},
        'literalChains': chains,
        'modeConsistency': {'selectorPC': 0x3E87, 'selectorAddress': 0x0217, 'selectorBit': 2,
            'expectedMode0': {'F8': a[0], 'IE': a[0], 'FA': a[1]},
            'expectedMode1': {'F8': b[0], 'IE': b[0], 'FA': b[1]},
            'comparisonPCs': [0x3E90, 0x3E95, 0x3E9B], 'successPC': 0x3EA7,
            'failurePCs': [0x3EA0, 0x3EA4], 'closed54DDTo3E81RequiresMode0': True,
            'hardwareSRCONModeMaySubstitute': False},
        'singlePassBranches': {'scope': 'One3EEATo3F45Pass_NoUnaccountedContextOrWriterChange',
            'pairA': 'DATA0212.3=0_and_DATA01AD>=0x29_and_DATA0217.2=1',
            'pairB': '(DATA0212.3=1_or_DATA01AD<0x29)_and_DATA0217.2=0',
            'thresholdReadPC': 0x3F05, 'thresholdAddress': 0x01AD,
            'thresholdSkippedWhen3EF1Taken': True, 'compareCFSourcePC': 0x3F05,
            'cfPreservingMaskPC': 0x3F09, 'conditionalBranchPC': 0x3F0C,
            'cfPreserved': True, 'zfPreserved': False,
            'pairAWrites': [0x3F14, 0x3F16, 0x3F18, 0x3F1D],
            'pairBWrites': [0x3F28, 0x3F2A, 0x3F2C, 0x3F31],
            'mutuallyExclusiveWithinPass': True, 'globallyMutuallyExclusive': False,
            'noSwitchBranches': [0x3F0E, 0x3F22], 'directIEWritePrecedesShadowUpdates': True},
        'pendingGenerationCut': {'clearPC': 0x54EA, 'word': 0x0018, 'width': 16,
            'laterIEWriterPC': 0x54F0,
            'sourceRequirement': 'PostClearOrConcurrentReassertedRQSRRDYGeneration',
            'completedSoftwareClearAssumed': True, 'hardwareAcknowledgeMayBeInferred': False,
            'setClearRacePriority': None, 'actualClearObserved': False},
        'mieWindows': {'preludeFAReadPC': 0x3EEA, 'preludeIEWriterPC': 0x3EEC,
            'preludeMieClearPC': 0x3EEE, 'middleMieSetPC': 0x3F02, 'middleMieClearPC': 0x3F09,
            'tailMieSetPC': 0x3F40, 'tailF8ReadPC': 0x3F43, 'tailIEWriterPC': 0x3F45,
            'tailMieSetPrecedesIECommit': True, 'nmiExcludedByMie0': False,
            'actualNestingHistory': None, 'physicalAcceptanceSubcycle': None},
        'requiredContext': {'zeroPageWordsDependOnLRB': False, 'zeroPageWordsDependOnSCB': False,
            'modeOffOperandsRequirePage': 0x0200, 'thresholdReadRequiresUSP': 0x0180,
            'comparisonCarrier': 'OwnedSCBSelectedX1Bank', 'actualLRB': None,
            'actualUSP': None, 'actualSCB': None, 'listingContextIsNativeObservation': False},
        'retention': {'directShadowWriterCandidates': [0x2569, 0x256B, 0x3F16, 0x3F18,
                0x3F2A, 0x3F2C, 0x54DD, 0x54E5], 'indirectPointerOrLocalAliasesExcluded': False,
            'unknownIrqNmiFrameOverlapExcluded': False, 'equalValuePreservesWriterGeneration': False,
            'currentF8Owner': None, 'currentFAOwner': None, 'currentIEOwner': None,
            'currentPendingOwner': None, 'currentStorageGeneration': None},
        'newOpcodeDiscoveryClaimed': False, 'cpuRomIrqRtiExecutions': 0,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False}


def reference_single():
    """One existing source path, with the newly qualified receive predecessor."""
    return {
        'classification': 'ConditionalSoftwareEffect_InheritedFlagPathWithNewReceivePredecessors',
        'sourceScope': 'CorrectedM2ciRxAuthority_M2cgM2chReviewedInstructionEffects',
        'path': [0x0213, 0x0215, 0x0217, 0x021C, 0x021F, 0x0222, 0x0225,
            0x0255, 0x0256, 0x0258, 0x0259, 0x025B, 0x025D, 0x025F, 0x0260,
            0x0262, 0x0264, 0x0267, 0x0269, 0x026A, 0x026D, 0x026F, 0x0270,
            0x0272, 0x0295, 0x0297, 0x029A, 0x029C],
        'pathIsObservedTrace': False,
        'entry': {'vector': 10, 'pc': 0x0213, 'irqBit': 1, 'request': 'RQSRRDY', 'enable': 'IESRRDY'},
        'requiredRetainedContext': {'modeAddress': 0x0356, 'modeBit': 1, 'modeValue': 1,
            'oldErrorBit': 6, 'oldErrorValue': 0, 'r7': 2, 'r5': 2, 'r2': 4,
            'r6': 'InheritedConditionalHeaderPlusLength_NotHostSeed'},
        'handler': {'pswWriterPC': 0x0217, 'literal': 0x0102, 'fullReadbackEqualsLiteral': False,
            'SCB': 2, 'lrbWriterPC': 0x021C, 'LRB': 0x007E, 'localBank': [0x03F0, 0x03F7], 'pageBase': 0x0300},
        'sourceRead': {'pc': 0x0262, 'address': 0x0055, 'widthBits': 8, 'form': 'LB A, N8',
            'AL': 'F_SymbolicDistinctRead', 'AH': 'RetainedOrdinaryLbSemantics_PhysicalSfUnknown',
            'DD': 0, 'actualValue': None, 'actualReadIdentity': None, 'actualSourceGeneration': None},
        'comparison': {'pc': 0x0264, 'form': 'CMPB r5, #2', 'comparesReceivedByte': False,
            'CF': 0, 'ZF': 1, 'ALPreserved': True, 'AHPreserved': True, 'DD': 0},
        'branch': {'pc': 0x0267, 'form': 'JNE', 'taken': False, 'nextPC': 0x0269},
        'writer': {'pc': 0x0269, 'address': 0x03F3, 'widthBits': 8, 'source': 'ALFrom0262',
            'writesAdjacentByte': False, 'sameValueCreatesFreshStorageGeneration': True,
            'actualWriterObserved': False, 'actualStorageGeneration': None},
        'orderedPersistentEffects': [
            {'pc': 0x0222, 'address': 0x0356, 'widthBits': 8,
                'effect': 'RmwClearBit6_RetainOtherBits', 'sameValueWriteRequired': True},
            {'pc': 0x0269, 'address': 0x03F3, 'widthBits': 8,
                'effect': 'StoreDistinctReadF', 'sameValueWriteRequired': True},
            {'pc': 0x026D, 'address': 0x03F6, 'widthBits': 8,
                'effect': 'R6EqualsPriorR6PlusFModulo256', 'ALPreserved': True},
            {'pc': 0x026F, 'address': 0x03F5, 'widthBits': 8, 'effect': 'IncrementR5From2To3'},
            {'pc': 0x0270, 'address': 0x03F7, 'widthBits': 8,
                'effect': 'WriteR7Equals2', 'sameValueWriteRequired': True}],
        'oddFlagRequiredToReach0269': False,
        'oddFlagMeaning': 'OnlyLater2918_2919ConsumerPredicate_NotExecutedHere',
        'readyBit7SetByThisFlagInvocation': False,
        'tail': {'f8ReadPC': 0x0295, 'mieClearPC': 0x0297, 'ieWriterPC': 0x029A,
            'rtiPC': 0x029C, 'returnPCSource': 'MatchingSavedForegroundPC_Not029C_Not28AE',
            'IEAutomaticallyRestoredByRTI': False, 'pointingRamAutomaticallyRestored': False},
        'preservation': {'selectedTailHasNoFurther03F3Write': True, 'actualFrameSafe': None,
            'actualRtiObserved': False, 'actualForegroundPC': None, 'actualRamRetention': None,
            'current03F3SemanticOwner': None, 'noNextHeaderOrOtherAliasMayBeAssumed': True},
        'runtimeAdmission': 'Blocked'}


def reference_dag():
    rows = [
        ('ApplicableSilicon', 'QualifiedReceiveCompletion', 'User126_128_ActualPartUnknown',
         'ActualSRCON7Permit_ModeClockAndFrameOwner', 'ManufacturerSourceQualified',
         'WrongSfrVariant', 'SpecificEcuSiliconApplicability'),
        ('QualifiedReceiveCompletion', 'SRBUFContentAndRXRequest', 'User128_12_1_5_6',
         'NotIgnoredMultiprocessorMpc0', 'ManufacturerSourceQualified',
         'NextAcceptedCompletionCanReplaceContent', 'ActualReceiveEventAndByte'),
        ('Conditional54EAClear', 'CurrentRQSRRDYPending', 'WordClear54EA_BeforeIE54F0',
         'PostClearOrConcurrentReassertion_NoAssumedSetClearPriority', 'ConditionalSoftwareEffect',
         'LaterClearEntryOrUnknownWriter', 'SourceOwnedPostClearPendingGeneration'),
        ('MaskWriterAndModeHistory', 'CurrentIESRRDY', '3F14_3F28_54F0_3E81ModeCheck',
         'OwnedF8_FA_IEAnd0217_2_NoOverwrite_PolarityQualified', 'ConditionalSoftwareEffect',
         'WordPointerFrameAndOtherIEWriter', 'CurrentIEShadowAndModeOwners'),
        ('PendingAndIE', 'EligibleIRQ000AEntry', 'User164_169_167ConflictRetained',
         'MIE_Priority_Boundary_ApplicableMode', 'ManufacturerSourceQualified',
         'OtherIRQOrNMI', 'ActualPendingEnablePriorityAndBoundary'),
        ('EligibleIRQ000AEntry', 'OneMatchingFrameAndPC0213', 'UserFig17_1_ExactVector000A',
         'OwnedSSP_WritableRetainedWords_NoInvalidOverlap', 'ConditionalSoftwareEffect',
         '03F0_03F7_FrameCanDestroyParserBank', 'ActualFrameCreatorAndSavedForegroundContext'),
        ('PC0213', 'FlagDispatchContext', '0213_0215_0217_021C_0222',
         'FAOwner_LiteralVsReadback_SCB2_LRB007E_Mode1_OldError0', 'ConditionalSoftwareEffect',
         'NestedIRQAfterMIEEnable', 'CurrentContextAndInheritedHeaderLengthOwners'),
        ('FlagDispatchContext', 'DistinctRead0262', '0255_0262_InheritedFlagPath',
         'RetainedR7_2_R5_2_R2_4_ApplicableSRBUFRead', 'ConditionalSoftwareEffect',
         'NewReceiveBeforeReadOrWrongBank', 'ActualSRBUFReadAndCurrentContentGeneration'),
        ('DistinctRead0262', 'Writer0269_DATA03F3', 'CMPBr5_0264_JNE0267_STB0269',
         'NoALMutation_CorrectByteBankAndCompletion', 'ConditionalSoftwareEffect',
         'NestedFrameOrAccumulatorMutation', 'Actual0269WriterGeneration'),
        ('Writer0269_DATA03F3', 'TailAndMatchingRTI029C', '026D_026F_0270_0295_0297_029A_029C',
         'SeparateR3R6R5R7Writes_F8Owner_IntactEntryFrame', 'ConditionalSoftwareEffect',
         'IRQ_NMI_StackAndPointingRegisterAliases', 'ActualMatchingRTIAndFrameRetention'),
        ('TailAndMatchingRTI029C', 'RetainedForegroundSource', 'SavedPC_A_LRB_PSW_SSP_NotHost28AE',
         'NoLaterOverwrite_PhysicalRamMap_OwnedReturnContext', 'ActualNativeGenerationNotEstablished',
         'ForegroundOrNextPacketWriter', 'SameMachineContinuityAndCurrent03F3Owner'),
    ]
    keys = ('from', 'to', 'evidence', 'requires', 'classification', 'aliasRisk', 'firstMissing')
    return [{**dict(zip(keys, row)), 'actualEstablished': False} for row in rows]


def reference_frame(ssp):
    if ssp is None:
        addresses, footprint, after, overlap = [None] * 4, None, None, None
    elif type(ssp) is int and ssp == 0x03F6:
        addresses = [0x03F6, 0x03F4, 0x03F2, 0x03F0]
        footprint, after, overlap = list(range(0x03F0, 0x03F8)), 0x03EE, True
    elif type(ssp) is int and ssp == 0x0500:
        addresses = [0x0500, 0x04FE, 0x04FC, 0x04FA]
        footprint, after, overlap = list(range(0x04FA, 0x0502)), 0x04F8, False
    else:
        raise ValueError('OnlyThreeReviewedReferenceControls')
    return {'classification': 'InventedOnly_OneFrameGeometry_NotActualStack',
        'inventedIncomingSSP': ssp, 'actualIncomingSSP': None,
        'wordRoles': [{'role': role, 'address': address}
                      for role, address in zip(('PC', 'A', 'LRB', 'PSW'), addresses)],
        'footprint': footprint, 'postEntrySSP': after, 'overlapsParserBank': overlap,
        'numericNonOverlapEstablished': overlap is False,
        'physicalWritableFrameEstablished': False, 'safeFrameEstablished': False,
        'rtiPopOrder': ['PSW', 'LRB', 'A', 'PC'], 'actualSavedForegroundPC': None,
        'firstMissingFrameObligation': ('InventedFrameOverlapsParserBank' if overlap
                                      else 'OwnedSSPAndApplicablePhysicalStorage'),
        'runtimeAdmission': 'Blocked'}


def reference_claim():
    return {'source': 'SerialReceivingReady', 'vector': 10, 'irqBit': 1,
        'irqSymbol': 'RQSRRDY', 'ieSymbol': 'IESRRDY',
        'bitAuthority': 'UserTable17_1_NotBorrowedIntoInstructionTable',
        'iePolarity': 'EvidenceFavorsSet1_167ConflictRetained', 'actualPolarityPromoted': False,
        'pendingIsDelivered': False, 'hostIEInjected': False, 'hostMIEInjected': False,
        'actualReceiveCompletion': None, 'historicalByteReusedAsCurrent': False,
        'srbufAddress': 0x0055, 'handlerSCB': 2, 'handlerLRB': 0x007E,
        'frameBytes': 8, 'actualFrameFootprint': None, 'unknownSSPDeclaredSafe': False,
        'unaccountedNmiExcluded': False, 'returnForm': 'RTI', 'actualRestoredPC': None,
        'hostForegroundPC': None, 'crossMachineTransfer': False, 'technicalSSPImported': False,
        'actual03F3Generation': None, 'actualCpuExecutions': 0,
        'oldSourcesRewritten': False, 'newPreservationExceptions': 0}


def negative_claims():
    """Twenty-five requested relation mutations, distinct from metadata counts."""
    edits = [
        ('TX000AReintroduced', {'source': 'SerialTransmittingReady'}),
        ('Bit2UsedForRX', {'irqBit': 2}),
        ('InstructionTableBorrowsUserIESymbol', {'bitAuthority': 'InstructionTableOwnsIESRRDY'}),
        ('Page167ContradictionDiscarded', {'iePolarity': 'Set1WithoutConflict'}),
        ('PolarityHypothesisPromoted', {'actualPolarityPromoted': True}),
        ('PendingTreatedAsDelivered', {'pendingIsDelivered': True}),
        ('HostIEInjection', {'hostIEInjected': True}),
        ('HostMIEInjection', {'hostMIEInjected': True}),
        ('FakeReceiveCompletion', {'actualReceiveCompletion': 'invented-completion'}),
        ('HistoricalByteReused', {'historicalByteReusedAsCurrent': True}),
        ('WrongSRBUFAddress', {'srbufAddress': 0x0054}),
        ('WrongSCBAndLRB', {'handlerSCB': 0, 'handlerLRB': 0x0041}),
        ('WrongFrameWidth', {'frameBytes': 2}),
        ('FrameOverlapsDATA03F3', {'actualFrameFootprint': list(range(0x03F0, 0x03F8))}),
        ('UnknownSSPDeclaredSafe', {'unknownSSPDeclaredSafe': True}),
        ('NMIIgnored', {'unaccountedNmiExcluded': True}),
        ('RTSubstitutedForRTI', {'returnForm': 'RT'}),
        ('RTIInstructionPCUsedAsReturn', {'actualRestoredPC': 0x029C}),
        ('HostPC28AE', {'hostForegroundPC': 0x28AE}),
        ('CrossMachineTransfer', {'crossMachineTransfer': True}),
        ('TechnicalSSP07FEImported', {'technicalSSPImported': 0x07FE}),
        ('Stale03F3Generation', {'actual03F3Generation': 'stale-generation'}),
        ('ActualCpuExecutionClaimed', {'actualCpuExecutions': 1}),
        ('OldSourcesRewritten', {'oldSourcesRewritten': True}),
        ('FourthPreservationException', {'newPreservationExceptions': 1}),
    ]
    return [(label, {**reference_claim(), **edit}) for label, edit in edits]


def reference_authority():
    return {'actualEcuChipIdentified': False, 'actualReceiveEvent': None,
        'currentIEOwner': None, 'currentPendingOwner': None, 'currentMIEOwner': None,
        'actualPriorityEligibility': None, 'actualFrameCreator': None,
        'actualSRBUFRead': None, 'actual0269Writer': None, 'actualRTIReturn': None,
        'actualForegroundRetention': None, 'actualMachineId': None,
        'actualEventOrdinal': None, 'actualWriteOrdinal': None, 'cpuExecutions': 0,
        'romExecutions': 0, 'irqDeliveries': 0, 'rtiExecutions': 0, 'retiredInstructions': 0,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False,
        'statusClasses': ['ManufacturerSourceQualified', 'ConditionalSoftwareEffect',
            'ActualHardwareEventNotObserved', 'ActualNativeGenerationNotEstablished',
            'SameMachineContinuityNotEstablished', 'RuntimeAdmissionBlocked']}


def reference_manufacturer():
    return {'document': 'MSM66201/207 User Manual retained body',
        'archiveSha256': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf',
        'edition': None, 'actualEcuApplicability': None,
        'wholeArchiveIntegrity': 'KnownSevenCrcFailures_NotRepaired',
        'reviewedCleanPrintedSpreads': [[126, 127], [128, 129], [130, 131],
            [164, 165], [166, 167], [168, 169]],
        'receiveRule': '12.1(5)(6)_Printed128',
        'permitRule': '12.1(4)_Printed126_127', 'overrunRule': 'SRSTAT_Bit1_Printed130',
        'iePolarity': 'EvidenceFavorsSet1_165_168_169_With167ConflictRetained',
        'missingPrintedPagesAfterSerial131BeforeRetained148': list(range(132, 148)),
        'exactMissingSectionAllocation': None}


RECEIVE_CASES = [
    ('rx-uart', ('uart_normal', False, True, False, None, False)),
    ('rx-overrun', ('uart_normal', False, True, False, None, True)),
    ('rx-ignored-mpc0', ('uart_multiprocessor', False, True, True, 0, True)),
    ('rx-address-mpc1', ('uart_multiprocessor', False, True, True, 1, False)),
    ('rx-filter-off', ('uart_multiprocessor', False, True, False, 0, False)),
    ('rx-sync-master', ('synchronous_normal', True, True, False, None, False)),
    ('rx-sync-slave', ('synchronous_normal', False, True, False, None, False)),
    ('rx-permit-missing', ('uart_normal', False, False, False, None, False)),
]
MASK_CASES = [('mask-a-set1', (0, 1)), ('mask-b-set1', (1, 1)),
              ('mask-a-set0', (0, 0)), ('mask-b-set0', (1, 0))]
PENDING_CASES = [('pending-before', ('before54EA', False)),
                 ('pending-after', ('after54EA', False)),
                 ('pending-unknown', ('unknown', False)),
                 ('pending-collision', ('unknown', True))]
FRAME_CASES = [('frame-unknown', None), ('frame-bank-overlap', 0x03F6),
               ('frame-mathematical-disjoint', 0x0500)]


def reference_records():
    records = []

    def add(identity, kind, finding):
        records.append({'caseId': identity, 'recordType': kind,
            'classification': 'StaticRxReadySingleInvocationSourceObligations_NotExecution',
            'finding': finding, 'manufacturer': reference_manufacturer(),
            'authority': reference_authority()})

    add('primary', 'SourceQualifiedFindings', reference_primary())
    add('mask-lineage', 'ConditionalSoftwareChronology', reference_masks())
    add('single-flag', 'InheritedPathWithNewReceivePredecessors', reference_single())
    add('proof-dag', 'SourceQualifiedObligations', reference_dag())
    for identity, args in RECEIVE_CASES:
        add(identity, 'InventedReceiveImplication', reference_completion(*args))
    for identity, args in MASK_CASES:
        add(identity, 'InventedPolarityHypothesis', reference_mask(*args))
    for identity, args in PENDING_CASES:
        add(identity, 'InventedPendingOrdering', reference_pending(*args))
    for identity, ssp in FRAME_CASES:
        add(identity, 'InventedSingleFrameGeometry', reference_frame(ssp))
    return deepcopy(records)
