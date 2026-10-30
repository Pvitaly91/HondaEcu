"""Qualified documentary relations, not a receiver, IRQ latch or scheduler.

The retained User body has no authenticated edition or actual ECU applicability.
Printed126-130 supply receiver/content rules;164-169 supply separate IRQ rules.
Invented controls calculate implications without generating a byte or an event.
"""

MODES = frozenset((
    'uart_normal', 'uart_multiprocessor',
    'synchronous_normal', 'synchronous_multiprocessor',
))


def primary_findings():
    """Source-qualified facts and explicit unknowns; old sources stay frozen."""
    return {
        'classification': 'ManufacturerSourceQualified',
        'deviceScope': 'RetainedUserBodyMSM66201_207_EditionAndActualEcuUnknown',
        'mapping': {
            'vectorAddress': 10, 'source': 'SerialReceivingReady',
            'irqBit': 1, 'ieBit': 1, 'requestSymbol': 'RQSRRDY',
            'enableSymbol': 'IESRRDY',
        },
        'iePolarity': {
            'verdict': 'IEPolarityEvidenceFavorsSet1ButConflictRetained',
            'setOneAuthority': 'Printed165_17_2_2_AndFig17_2_Printed168',
            'setZeroParagraph': 'Printed167_AcceptanceCondition_NotPostEntryIEState',
            'contextResolvesConflict': False, 'manufacturerErratumAcquired': False,
            'actualEcuPolarity': None,
        },
        'receiveSource': {
            'receiveEndTransfersShiftRegisterToSrbuf': True,
            'sameCompletionGeneratesRxReadyRequest': True,
            'ignoredMultiprocessorMpc0SuppressesBoth': True,
            'contentHeldUntilNextEligibleCompletion': True,
            'srbufBits': 8, 'srbufReadOnly': True,
            'shiftRegisterSoftwareAccessible': False, 'actualByte': None,
        },
        'receiverPermit': {
            'srconAddress': 84, 'srRenBit': 7, 'oneAllowsReception': True,
            'resetSrcon': 0, 'modeChangeRequiresReceiverDisabled': True,
            'synchronousMasterClearsAfterOneFrame': True,
            'otherModesAutoClearSrRen': False, 'actualCurrentSrcon': None,
        },
        'overrun': {
            'unreadPriorDataSetsNewOverrunCondition': True,
            'newDataStillReplacesSrbuf': True,
            'errorBitsStickyUntilSoftwareClear': True,
            'ignoredMpcErrorInteraction': None, 'actualSrstat': None,
        },
        'requestLifecycle': {
            'servicedFactorClearedDuringMaskableEntry': True,
            'ieRetainedDuringEntry': True, 'mieClearedDuringEntry': True,
            'examplesAllowPendingBeforeLaterEnable': True,
            'srbufReadClearsRequest': None, 'automaticReassertion': None,
            'everyReentryRequiresNewReceiveCompletion': None,
            'actualPendingOwner': None, 'actualDeliveryObserved': False,
        },
        'newManufacturerDocuments': 0, 'cpuRomIrqRtiExecutions': 0,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False,
    }


def completion_relation(mode, master, srren, filter_mpc, mpc, prior_unread):
    """One assumed completed frame, with no actual peripheral observation.

    Normal-mode MPC/filter controls are not silently interpreted as that mode's
    data-length bits. Missing multiprocessor MPC refuses the bounded control.
    A new overrun condition is distinct from a sticky SRSTAT bit's final value.
    """
    if (type(mode) is not str or mode not in MODES
            or any(type(v) is not bool for v in (master, srren, filter_mpc, prior_unread))):
        raise ValueError('ClosedTechnicalReceiveInputsRequired')
    synchronous = mode.startswith('synchronous_')
    multiprocessor = mode.endswith('_multiprocessor')
    if ((not synchronous and master)
            or (not multiprocessor and (filter_mpc or mpc is not None))
            or (multiprocessor and (type(mpc) is not int or mpc not in (0, 1)))):
        raise ValueError('ModeSpecificReceiveInputsRequired')
    result = {
        'classification': 'InventedOnly_ConditionalManufacturerRelation',
        'inputs': {'mode': mode, 'master': master, 'srren': srren,
                   'filterMpc': filter_mpc, 'mpc': mpc, 'priorUnread': prior_unread},
        'admitted': False, 'refusal': 'ReceiverPermitNotEstablished_SRREN0',
        'assumedReceiveEnd': None, 'multiprocessIgnored': None,
        'srbufTransferExpected': None, 'rxReadyRequestExpected': None,
        'newOverrunConditionExpected': None, 'srstatOerrAfter': None,
        'overrunRule': 'ReceiveEndNotAdmitted',
        'receiverPermitAfterFrame': None, 'nextFrameNeedsReceiverReenable': None,
        'srbufValue': None, 'actualPendingOwner': None, 'actualReceiveEvent': None,
        'actualReadId': None, 'actualDeliveryObserved': False,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False,
    }
    if not srren:
        return result
    ignored = multiprocessor and filter_mpc and mpc == 0
    auto_disable = synchronous and master
    result.update(
        admitted=True, refusal=None, assumedReceiveEnd=True,
        multiprocessIgnored=ignored, srbufTransferExpected=not ignored,
        rxReadyRequestExpected=not ignored,
        newOverrunConditionExpected=None if ignored else prior_unread,
        overrunRule=('IgnoredMpcErrorInteractionUnspecified' if ignored
                     else 'PriorUnreadOnAcceptedReceiveEnd'),
        receiverPermitAfterFrame=not auto_disable,
        nextFrameNeedsReceiverReenable=auto_disable,
    )
    return result
