"""Reviewed CAL/RT architecture metadata, never a CPU or an execution oracle.

Private primary-page and original-extent bindings live outside public source.
The ordinary arithmetic contract does not grant a control-register alias safe
stack semantics, a physical RAM map, a native SSP owner, or a matching return.
"""


def semantics_contract():
    return {
        'classification': 'StaticCalRtFrameProvenance_NotCpuExecution',
        'primaryInstructionManual': {
            'name': 'OKI MSM66201 Instruction Manual',
            'edition': 'First_September1991',
            'calPrintedPage': '3-29', 'rtPrintedPage': '3-125',
            'wordBoundaryPrintedPages': ['1-17', '1-18'],
            'littleEndianPrintedPage': '1-5',
            'applicability': 'NamedStandardArchitecture_NotCustomerAsicIdentity',
        },
        'cal': {
            'callerPC': 0x27D0, 'form': 'CAL addr16', 'length': 3,
            'calleeEntryPC': 0x5F45, 'requiredReturnPC': 0x27D3,
            'documentedOperationOrder': [
                'WordAtSSP_AssignedNextPC', 'SSP_DecrementedBy2',
                'DocumentedSF_Cleared', 'PC_AssignedEncodedTarget',
            ],
            'ordinaryFrameAddress': '2*floor(incomingSSP/2)',
            'ordinarySspAfterCAL': '(incomingSSP-2) modulo65536',
            'frameWidth': 16, 'byteOrder': 'LittleEndian',
            'ordinaryFrameBytesDerivedFromNextPC': [0xD3, 0x27],
            'flagsIntrinsicToInstruction': 'CF_ZF_HC_DD_Retained',
            'frameStoreMayChangeAliasedContext': True,
        },
        'rt': {
            'rtConsumerPC': 0x60E4, 'form': 'RT', 'length': 1,
            'documentedOperationOrder': [
                'SSP_IncrementedBy2', 'PC_ReadFromWordAtUpdatedSSP',
                'DocumentedSF_Cleared',
            ],
            'ordinaryRtReadAddress': '2*floor(((sspBeforeRT+2)modulo65536)/2)',
            'conditionalReturnedPC': 0x27D3,
            'restoredSspRequires': 'NoUnaccountedSSPMutationSinceMatchingCAL',
            'retainedState': 'CalleeA_LRB_ArchitecturalPSW_NoCallerSnapshotRestore',
            'rtiInterchangeable': False,
            'numericPcEqualityEstablishesFrameCreator': False,
        },
        'alignment': {
            'wordEffectiveAddressLsb': 0,
            'oddSSPGloballyRejectedByManufacturerEvidence': False,
            'strictEvenTechnicalAdmissionIsGlobalHardwareRule': False,
            'registerSspParityAndEffectiveAddressParityAreDistinct': True,
            'arithmeticDomain': 'Unsigned16_Modulo65536',
            'arithmeticFormulaOverridesSspSelfAliasSideEffect': False,
        },
        'sf': {
            'instructionManualFunction': 'CAL_and_RT_PrintSFclear',
            'mac66kThird1993PrintedPage': '4-116',
            'mac66kStatement': 'StackFlagOnlyOnNx8_300',
            'combinedClassification': 'InheritedPrimaryApplicabilityConflictUnresolved',
            'physicalStorageMeaningEstablished': False,
            'sfIsOrdinaryPSWBit': False,
            'hostBooleanIsPhysicalWitness': False,
            'accumulatorStackModeMayBeDefaulted': False,
        },
        'generation': {
            'requiredCreatorPC': 0x27D0, 'requiredConsumerPC': 0x60E4,
            'sameValueStoreCreatesNewGeneration': True,
            'preexistingNumericReturnWordSuppliesCreator': False,
            'uninterruptedStorageRequiredForThisProducerFrameProof': True,
            'explicitEarlierRestorationProofMayBeBorrowedFromOtherCaller': False,
            'actualNativeInstructionIndex': None,
            'actualNativeLogicalWriteOrdinal': None,
            'actualNativeRawByteWriteOrdinals': None,
            'actualNativeAllWriteOrdinal': None,
            'actualNativeReadLinkage': None,
        },
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
        'actualRetiredInstructions': 0, 'firmwareReady': False,
    }


def architecture_aliases():
    """Word-store hazards, independent of a chosen numeric safe SSP fixture."""
    return [
        {'start': 0x0000, 'endExclusive': 0x0002, 'role': 'SSP',
         'effect': 'FrameStoreAliasesItsOwnStackPointer',
         'ordinaryPostCalArithmeticAdmitted': False,
         'returnFeasibility': 'UnresolvedSelfAliasCaptureAndUpdateSemantics'},
        {'start': 0x0002, 'endExclusive': 0x0004, 'role': 'LRB',
         'effect': 'FrameStoreChangesPageAndLocalBankContext',
         'readUpperThreeBits': 'ZeroOnReviewedStandardDevice',
         'returnFeasibility': 'CannotAssumeUnchangedProducerAddressing'},
        {'start': 0x0004, 'endExclusive': 0x0006, 'role': 'PSW',
         'effect': 'FrameStoreCanChangeFlagsAndSCB',
         'standardReservedReadOneBits': [3, 6, 7, 10, 11],
         'returnFeasibility': 'CannotAssumeRawWordReadbackOrRetainedContext'},
        {'start': 0x0006, 'endExclusive': 0x0008, 'role': 'A',
         'effect': 'CALFrameStoreSetsA27D3BeforeHelperEntry',
         'mandatoryNextHelperEffect': 'CLRB5F45ChangesAL',
         'returnFeasibility': 'FrameDefinitelyClobberedInReviewedNormalReturnDomain'},
        {'start': 0x0080, 'endExclusive': 0x00C0, 'role': 'SCBSelectedPointingStorage',
         'wordRolesWithinEachEightByteBank': ['X1', 'X2', 'DP', 'USP'],
         'effect': 'FrameMayChangeCurrentOrOtherPointerBank',
         'returnFeasibility': 'NeedsExactSCBAndSubsequentAddressDependencies'},
        {'start': 0x0008, 'endExclusive': 0x0080, 'role': 'OtherSFRorReservedControl',
         'effect': 'PerDeviceAccessWidthAndSideEffectsMustBeEstablished',
         'returnFeasibility': 'NotAdmittedAsGenericWritableRam'},
    ]


def memory_applicability():
    return {
        'classification': 'DocumentedStandardDeviceMap_NotActualAsicMap',
        'addressSpaces': 'PROGRAM_and_DATA_AreDistinct16BitSpaces',
        'candidateFrame': [0x047E, 0x047F],
        'MSM66201': {
            'internalDataRam': [0x0080, 0x027F],
            'candidate047E': 'ExternalDataMemory',
        },
        'MSM66207': {
            'internalDataRamIncludingPointingStorage': [0x0080, 0x047F],
            'candidate047E': 'DocumentedStandardInternalRam',
        },
        'sourceQualifications': [
            'IncompleteUserManualBodyNamesMSM66201And66207_CoverEditionRevisionMissing',
            'E2E1027_27_Y4_ConfirmsStandardRegisterRolesAndDeviceRamSizes',
            'NoCustomerAsicIdentityOrBoardMapFollowsFromCodeUsing047E',
        ],
        'actualAsicMemoryApplicabilityEstablished': False,
        'actual047EWritableAndRetainedEstablished': False,
        'softwareDisjointnessProvesPhysicalStackSafety': False,
        'documentedResetSsp': 0xFFFF,
        'documentedResetProvesObservedProducerSsp': False,
        'technical07FEor07E0IsProducerSource': False,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
        'firmwareReady': False,
    }
