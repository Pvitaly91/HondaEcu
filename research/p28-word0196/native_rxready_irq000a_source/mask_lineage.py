"""Source-qualified IE shadow chronology, not a pending latch or CPU model."""


def mask_profile(software_mode_bit, ie_polarity):
    """Expected pairs at the 3E81 check; no current native owner is supplied."""
    if (type(software_mode_bit) is not int or software_mode_bit not in (0, 1)
            or type(ie_polarity) is not int or ie_polarity not in (0, 1)):
        raise ValueError('ClosedSoftwareModeAndPolarityHypothesesRequired')
    f8, fa = (0x2BAB, 0x02A0) if software_mode_bit == 0 else (0xA9A3, 0x00A0)
    return {
        'modeBit': software_mode_bit, 'pairId': 'A' if software_mode_bit == 0 else 'B',
        'F8': f8, 'FA': fa, 'directIE': f8, 'rxBit': 1,
        'rxBodyBit': (fa >> 1) & 1, 'rxTailBit': (f8 >> 1) & 1,
        'rxBodyAllowed': ((fa >> 1) & 1) == ie_polarity,
        'rxTailAllowed': ((f8 >> 1) & 1) == ie_polarity,
        'txBit': 2, 'txBitValue': (f8 >> 2) & 1,
        'txAllowed': ((f8 >> 2) & 1) == ie_polarity,
        'modeMeaning': 'SoftwareDATA0217.2_NotSRCON0054.2',
        'pairQualification': 'ExpectedBy3E81Check_NotCurrentNativePair',
        'polarityIsHypothesis': True,
        'currentFAOwner': None, 'currentF8Owner': None,
        'currentIEOwner': None, 'currentStorageGeneration': None,
        'actualHardwareApplicabilityEstablished': False,
        'actualDeliveryObserved': False,
    }


def pending_cut(position, collision):
    """One assumed software-clear chain; no hardware set/clear winner inferred."""
    if (type(position) is not str or position not in ('before54EA', 'after54EA', 'unknown')
            or type(collision) is not bool):
        raise ValueError('ClosedPendingPositionAndCollisionHypothesisRequired')
    ordering = {'before54EA': False, 'after54EA': True, 'unknown': None}
    return {
        'position': position, 'collisionHypothesis': collision,
        'softwareClearPC': 0x54EA, 'softwareClearWord': 0x0018,
        'softwareClearWidth': 16, 'chainAssumedConditional': True,
        'postClearOrderingSatisfied': ordering[position],
        'orderingProvesPendingState': False,
        'priorPreClearGenerationSufficient': False,
        'currentPendingValue': None, 'currentPendingOwner': None,
        'setClearWinner': None, 'actualPendingObserved': False,
    }


def mask_findings():
    """Reviewed new joins over existing instruction extents, without execution."""
    return {
        'classification': 'SourceQualifiedStaticMaskChronology_NotRuntime',
        'correctedSource': {
            'profile': 'UserTable17_1', 'vector': 0x000A, 'bit': 1,
            'request': 'RQSRRDY', 'enable': 'IESRRDY',
            'actualEcuApplicability': None,
        },
        'words': {'F8': [0x00F8, 0x00F9], 'FA': [0x00FA, 0x00FB],
                  'IE': [0x001A, 0x001B], 'IRQ': [0x0018, 0x0019]},
        'literalChains': [
            {'id': 'ModeSwitchA', 'pairId': 'A',
             'pcs': [0x3F11, 0x3F14, 0x3F16, 0x3F18, 0x3F1D, 0x3F20],
             'IEWriterPC': 0x3F14, 'F8WriterPC': 0x3F16, 'FAWriterPC': 0x3F18,
             'modeWriterPC': 0x3F1D, 'modeAfter': 0,
             'F8': 0x2BAB, 'FA': 0x02A0, 'IE': 0x2BAB},
            {'id': 'ModeSwitchB', 'pairId': 'B',
             'pcs': [0x3F25, 0x3F28, 0x3F2A, 0x3F2C, 0x3F31],
             'IEWriterPC': 0x3F28, 'F8WriterPC': 0x3F2A, 'FAWriterPC': 0x3F2C,
             'modeWriterPC': 0x3F31, 'modeAfter': 1,
             'F8': 0xA9A3, 'FA': 0x00A0, 'IE': 0xA9A3},
            {'id': 'Initial54DD', 'pairId': 'A',
             'pcs': [0x54DD, 0x54E2, 0x54E5, 0x54E7, 0x54EA, 0x54ED, 0x54F0],
             'FAWriterPC': 0x54DD, 'F8WriterPC': 0x54E5, 'IRQClearPC': 0x54EA,
             'IEWriterPC': 0x54F0, 'modeWriterPC': None, 'modeAfter': None,
             'F8': 0x2BAB, 'FA': 0x02A0, 'IE': 0x2BAB},
        ],
        'modeConsistency': {
            'selectorPC': 0x3E87, 'selectorAddress': 0x0217, 'selectorBit': 2,
            'expectedMode0': {'F8': 0x2BAB, 'IE': 0x2BAB, 'FA': 0x02A0},
            'expectedMode1': {'F8': 0xA9A3, 'IE': 0xA9A3, 'FA': 0x00A0},
            'comparisonPCs': [0x3E90, 0x3E95, 0x3E9B],
            'successPC': 0x3EA7, 'failurePCs': [0x3EA0, 0x3EA4],
            'closed54DDTo3E81RequiresMode0': True,
            'hardwareSRCONModeMaySubstitute': False,
        },
        'singlePassBranches': {
            'scope': 'One3EEATo3F45Pass_NoUnaccountedContextOrWriterChange',
            'pairA': 'DATA0212.3=0_and_DATA01AD>=0x29_and_DATA0217.2=1',
            'pairB': '(DATA0212.3=1_or_DATA01AD<0x29)_and_DATA0217.2=0',
            'thresholdReadPC': 0x3F05, 'thresholdAddress': 0x01AD,
            'thresholdSkippedWhen3EF1Taken': True,
            'compareCFSourcePC': 0x3F05, 'cfPreservingMaskPC': 0x3F09,
            'conditionalBranchPC': 0x3F0C, 'cfPreserved': True, 'zfPreserved': False,
            'pairAWrites': [0x3F14, 0x3F16, 0x3F18, 0x3F1D],
            'pairBWrites': [0x3F28, 0x3F2A, 0x3F2C, 0x3F31],
            'mutuallyExclusiveWithinPass': True, 'globallyMutuallyExclusive': False,
            'noSwitchBranches': [0x3F0E, 0x3F22],
            'directIEWritePrecedesShadowUpdates': True,
        },
        'pendingGenerationCut': {
            'clearPC': 0x54EA, 'word': 0x0018, 'width': 16,
            'laterIEWriterPC': 0x54F0,
            'sourceRequirement': 'PostClearOrConcurrentReassertedRQSRRDYGeneration',
            'completedSoftwareClearAssumed': True,
            'hardwareAcknowledgeMayBeInferred': False,
            'setClearRacePriority': None, 'actualClearObserved': False,
        },
        'mieWindows': {
            'preludeFAReadPC': 0x3EEA, 'preludeIEWriterPC': 0x3EEC,
            'preludeMieClearPC': 0x3EEE,
            'middleMieSetPC': 0x3F02, 'middleMieClearPC': 0x3F09,
            'tailMieSetPC': 0x3F40, 'tailF8ReadPC': 0x3F43,
            'tailIEWriterPC': 0x3F45, 'tailMieSetPrecedesIECommit': True,
            'nmiExcludedByMie0': False, 'actualNestingHistory': None,
            'physicalAcceptanceSubcycle': None,
        },
        'requiredContext': {
            'zeroPageWordsDependOnLRB': False, 'zeroPageWordsDependOnSCB': False,
            'modeOffOperandsRequirePage': 0x0200, 'thresholdReadRequiresUSP': 0x0180,
            'comparisonCarrier': 'OwnedSCBSelectedX1Bank',
            'actualLRB': None, 'actualUSP': None, 'actualSCB': None,
            'listingContextIsNativeObservation': False,
        },
        'retention': {
            'directShadowWriterCandidates': [0x2569, 0x256B, 0x3F16, 0x3F18,
                                           0x3F2A, 0x3F2C, 0x54DD, 0x54E5],
            'indirectPointerOrLocalAliasesExcluded': False,
            'unknownIrqNmiFrameOverlapExcluded': False,
            'equalValuePreservesWriterGeneration': False,
            'currentF8Owner': None, 'currentFAOwner': None,
            'currentIEOwner': None, 'currentPendingOwner': None,
            'currentStorageGeneration': None,
        },
        'newOpcodeDiscoveryClaimed': False,
        'cpuRomIrqRtiExecutions': 0, 'runtimeAdmission': 'Blocked',
        'firmwareReady': False,
    }
