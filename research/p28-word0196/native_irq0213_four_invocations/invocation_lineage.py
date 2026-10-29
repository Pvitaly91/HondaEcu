"""Static four-invocation RAM obligations; no CPU, serial or interrupt model.

All values below are conditional source relations. They are not initialized RAM,
hardware events, execution observations or permission to create an IRQ frame.
"""

STATIC = 'StaticIRQ0213FourInvocationRelations_NotCpuOrPeripheralExecution'


def _effect(pc, address, width, role, value_source, bit=None):
    return {'pc': pc, 'addressSpace': 'DATA', 'address': address, 'widthBits': width,
        'bit': bit, 'role': role, 'conditionalValueSource': value_source,
        'sameValueWriteIdentityMustBeRetained': True, 'actualValue': None,
        'actualSourceOwner': None, 'actualStorageGeneration': None,
        'actualNativeInstructionIndex': None, 'actualAllNativeWriteOrdinal': None}


def lineage_analysis():
    """Project reviewed source/retention cuts without invoking target code."""
    prefix = [
        _effect(0x0215, 0x001A, 16, 'IEWord', 'CurrentWord00FA_00FB_Read0213'),
        _effect(0x0217, 0x0004, 16, 'PSWWrittenLiteral', 'CodeLiteral0102_NotFullReadback'),
        _effect(0x021C, 0x0002, 16, 'LRBWord', 'CodeLiteral007E'),
        _effect(0x0222, 0x0356, 8, 'BitReadClearRmw', 'OldBit6Read_ThenBit6Zero', 6),
    ]
    tail = [
        _effect(0x0297, 0x0005, 8, 'PSWHRmw', 'CurrentPSWH_AND_FE_ConditionalMIE0'),
        _effect(0x029A, 0x001A, 16, 'IEWord', 'CurrentWord00F8_00F9_Read0295'),
    ]
    stage_writes = {
        'H': [
            _effect(0x0275, 0x03F0, 8, 'LocalR0', 'Previous03F1BeforeFreshRead0277'),
            _effect(0x0279, 0x03F1, 8, 'LocalR1', 'DistinctRead0277_H'),
            _effect(0x027A, 0x03F6, 8, 'LocalR6', 'SameAL_H_FromRead0277'),
            _effect(0x027B, 0x03F5, 8, 'LocalR5', 'CodeConstant1'),
            _effect(0x0270, 0x03F7, 8, 'LocalR7', 'CodeConstant2'),
        ],
        'L': [
            _effect(0x0281, 0x03F2, 8, 'LocalR2', 'DistinctRead027F_L'),
            _effect(0x026D, 0x03F6, 8, 'LocalR6Rmw', '(RetainedH+CurrentL)mod256'),
            _effect(0x026F, 0x03F5, 8, 'LocalR5Rmw', 'Retained1Plus1_Equals2'),
            _effect(0x0270, 0x03F7, 8, 'LocalR7', 'CodeConstant2_SameValueFreshWrite'),
        ],
        'F': [
            _effect(0x0269, 0x03F3, 8, 'LocalR3', 'DistinctRead0262_F'),
            _effect(0x026D, 0x03F6, 8, 'LocalR6Rmw', '(RetainedHPlusL+CurrentF)mod256'),
            _effect(0x026F, 0x03F5, 8, 'LocalR5Rmw', 'Retained2Plus1_Equals3'),
            _effect(0x0270, 0x03F7, 8, 'LocalR7', 'CodeConstant2_SameValueFreshWrite'),
        ],
        'K': [
            _effect(0x0290, 0x0356, 8, 'ReadyBitSetRmw', 'CodeValueOneAfterAcceptedChecksumAndHeaderClass', 7),
            _effect(0x0293, 0x03F7, 8, 'LocalR7', 'CodeZeroAfterAcceptedPacket'),
        ],
    }
    before = {
        'H': {'r0': None, 'r1': 'PreviousHeaderUnknown', 'r2': None, 'r3': None,
            'r4': None, 'r5': None, 'r6': None, 'r7': 0},
        'L': {'r0': 'PreviousHeaderUnknown', 'r1': 'H', 'r2': None, 'r3': None,
            'r4': None, 'r5': 1, 'r6': 'H', 'r7': 2},
        'F': {'r0': 'PreviousHeaderUnknown', 'r1': 'H', 'r2': 4, 'r3': None,
            'r4': None, 'r5': 2, 'r6': '(H+L)mod256', 'r7': 2},
        'K': {'r0': 'PreviousHeaderUnknown', 'r1': 'H', 'r2': 4, 'r3': 'F',
            'r4': None, 'r5': 3, 'r6': '(H+L+F)mod256', 'r7': 2},
    }
    after = {'H': before['L'], 'L': before['F'], 'F': before['K'], 'K': before['K'] | {'r7': 0}}
    reads = {'H': 0x0277, 'L': 0x027F, 'F': 0x0262, 'K': 0x0284}
    accumulator_pcs = {
        'H': [0x0213, 0x0255, 0x0277, 0x0295],
        'L': [0x0213, 0x0255, 0x0258, 0x027F, 0x0295],
        'F': [0x0213, 0x0255, 0x0258, 0x025D, 0x0262, 0x0295],
        'K': [0x0213, 0x0255, 0x0258, 0x025D, 0x0284, 0x0286, 0x0289, 0x028A, 0x0295],
    }
    invocations = []
    for index, stage in enumerate(('H', 'L', 'F', 'K'), 1):
        invocations.append({'invocationIndex': index, 'stage': stage,
            'indexRole': 'SymbolicObligation_NotActualEventIndex', 'entryPC': 0x0213,
            'frameCreator': 'RequiredDistinctIRQEntry_' + stage,
            'srbufReadPC': reads[stage], 'srbufValueSource': 'DistinctApplicableDATA0055Read_' + stage,
            'conditionalBeforeLocalRAM': before[stage], 'conditionalAfterLocalRAM': after[stage],
            'orderedDataAndContextEffects': prefix + stage_writes[stage] + tail,
            'accumulatorWritePCs': accumulator_pcs[stage],
            'accumulatorAndFlagsRole': 'ReachedArchitecturalEffects_ThenRequireMatchingSavedFrameRestoration',
            'status0356': {'requiredModeBit1': 1, 'requiredOldBit6At0222': 0,
                'bit6AfterReadClear': 0, 'readyBit7AfterStage': 1 if stage == 'K' else 'RetainedPriorBit7',
                'statusByteWriterPCs': [0x0222, 0x0290] if stage == 'K' else [0x0222],
                'sameValueBitClearCreatesFreshStorageGeneration': True,
                'neighborBitSemanticRetention': 'OrdinaryApplicableMemoryAndNoAliasOnly'},
            'rtiInstructionPC': 0x029C, 'savedForegroundPC': None, 'restoredForegroundPC': None,
            'incomingSSP': None, 'actualFrameCreator': None, 'actualSRBUFReadIdentity': None,
            'actualSourceOwner': None, 'actualStorageGeneration': None,
            'ramRetention': 'ConditionalNoEntryFrameHandlerNestedOrForegroundOverlap',
            'actualNativeEventIndex': None, 'actualAllNativeWriteOrdinal': None})
    return {'classification': STATIC,
        'sourceReferences': ['M2cgFourReadAndCommandPrefix', 'M2awArchitecturalContext',
            'M2apSavedIE_ShadowWords', 'M2ccAndM2cdHelperAndForegroundCallers'],
        'newRelations': ['OldHeader0275SideWrite', 'PerEntry0222StatusStorageGeneration',
            'PerInvocationMaskAndMIEChronology', 'Mode0AndErrorAlternativePathCuts',
            'PartialReadyAndPostReadyOverwriteCuts', 'FrameRestoreVersusPersistentRAM'],
        'inheritedNotNew': ['FourReadPathAlgebra', 'GenericEightByteIRQGeometry',
            'InitialR7AndModeWriterCandidates', 'CLR291BZeroStores'],
        'actualIrqSource': None,
        'conditionalIrqProfile': 'UserTable17_1SerialTransmittingReady_WordBit1_Vector000A',
        'sourceAllocationConflict': 'InstructionTable1_1Vector000AReceivingReady_ActualProfileUnknown',
        'handlerContext': {'scb': 2, 'lrb': 0x007E, 'page': 0x0300,
            'localBytes': list(range(0x03F0, 0x03F8)), 'selectedPRRAMBytes': list(range(0x0090, 0x0098)),
            'actualIncomingRAM': None, 'positivePathExplicitPointingWrites': [],
            'positivePathChangesDP_X1_X2_USPByExplicitInstruction': False,
            'physicalMappedWritableRetainedRam': None,
            'standard201LocalRamNature': 'ExternalDATA', 'standard207LocalRamNature': 'InternalDATA',
            'actualSiliconAndAccumulatorStackApplicability': None},
        'invocations': invocations,
        'maskAndMieChronology': {'entrySourceWord': 0x00FA, 'entrySourceBytes': [0x00FA, 0x00FB], 'entryReadPC': 0x0213,
            'entryIEWriterPC': 0x0215, 'mieLiteralWriterPC': 0x0217, 'conditionalMIE': 1,
            'nestedEntryObligationInterval': [0x0217, 0x0297],
            'tailSourceWord': 0x00F8, 'tailSourceBytes': [0x00F8, 0x00F9], 'tailReadPC': 0x0295,
            'mieClearPC': 0x0297, 'tailIEWriterPC': 0x029A,
            'literalPairs': [
                {'F8WriterPC': 0x3F16, 'FAWriterPC': 0x3F18, 'F8': 0x2BAB, 'FA': 0x02A0},
                {'F8WriterPC': 0x3F2A, 'FAWriterPC': 0x3F2C, 'F8': 0xA9A3, 'FA': 0x00A0},
                {'F8WriterPC': 0x54E5, 'FAWriterPC': 0x54DD, 'F8': 0x2BAB, 'FA': 0x02A0}],
            'conditionalKnownPairsBodyBit1': 0, 'conditionalKnownPairsTailBit1': 1,
            'bit1Role': 'ConditionalUserProfileTxSlot_NotActualSourceIdentification',
            'earlyZeroShadowWriters': [0x2569, 0x256B], 'earlyZeroEnablesBit1': False,
            'currentShadowOwners': None, 'currentShadowOwnerEquality': None,
            'applicableIESideEffectsAndActualNestedEntries': None},
        'alternativePathCuts': {'modeReaderPC': 0x021F, 'modeBit1ZeroTarget': 0x029D,
            'modeZeroSelectedFootprints': {'directStatusAddress': 0x0056,
                'statusReadClearPCs': [0x029E, 0x02A5], 'extraSRBUFReadPC': 0x02AE,
                'dpWrites': [0x02B0, 0x02C2], 'possibleIndirectReadPC': 0x02B7,
                'transmitBufferWriterPC': 0x02BE, 'epilogueEntry': 0x0244,
                'rtiInstructionPC': 0x024B},
            'oldErrorBit6One': {'readClearPC': 0x0222, 'branchPC': 0x0225,
                'bodyPC': 0x0227, 'possibleDPWrites': [0x0237, 0x023A],
                'possibleLocalWriters': [0x023C, 0x0240], 'transmitBufferWriterPC': 0x023E,
                'statusBit6SetPC': 0x0241, 'rtiInstructionPC': 0x024B},
            'completeAlternateProtocolEmulated': False, 'actualSFRReadEffects': None},
        'initialR7': {'actualOwner': None, 'resetRAMValue': None,
            'priorClearPC': 0x0293, 'priorClearRequiresPreviousAcceptedPacket': True,
            'prior0293AloneIsIndependentBootstrap': False,
            'conditionalStartup': {'zeroSourcePC': 0x2706, 'wordWriterPC': 0x2710,
                'requiredDP': 0x03F6, 'wordFootprint': [0x03F6, 0x03F7]},
            'startupReachingAndRetentionToFirstIrq': None},
        'modeSource': {'writerPC': 0x60D5, 'pointerWriterPC': 0x60D2,
            'address': 0x0356, 'bit': 1, 'requiredConditionalValue': 1,
            'helperColdLocalR0Address': 0x0208, 'headerLocalR0Address': 0x03F0,
            'predicatePCs': [0x60BD, 0x60C0],
            'nonzeroHelperR0': {'programReadPC': 0x60C2, 'programAddress': 0x6105,
                'shiftPC': 0x60C6, 'sourceBit': 7},
            'zeroHelperR0': {'dataPointerPC': 0x60C9, 'dataAddress': 0x03CB,
                'comparePC': 0x60CC, 'invertCarryPC': 0x60CF, 'sourceBit': 7},
            'differentLocalR0RolesMayShareAnOwnerWithoutProof': False, 'actualModeOwner': None},
        'readyRetention': {'readyWriterPC': 0x0290, 'H_L_FDoNotClearReadyBit7': True,
            'beforeChecksumRequirement': 'OwnedReady0OrNoForeground28BBConsumptionOfPartialPacket',
            'afterChecksumRequirement': 'NoRelevantOverwriteOrNextHeaderBeforeCurrentParserReads',
            'actualInitialReadyOwner': None, 'actualNoEarlyConsumerProof': None},
        'rtiAndForeground': {'instructionPC': 0x029C, 'restorationOrder': ['PSW', 'LRB', 'A', 'PC'],
            'perInvocationSavedForegroundContexts': None,
            'restoredPCSource': 'ThatInvocationMatchingFrame_Not029C_NotHost28AE',
            'notImplicitlyRestored': ['IE', 'Local03F0_03F7', 'Status0356', 'PRRAM'],
            'foregroundCandidateVcalPCs': [0x4068, 0x4165], 'callee': 0x28AE,
            'vcalFrameAndLegalForegroundReachRequired': True,
            'parserSCB': 0, 'parserLRB': 0x0041, 'parserUSP': 0x0180,
            'handlerContextMayBeImported': False, 'actualForegroundHandoff': None},
        'nonOverlapRequirements': ['DistinctMatchingFourWordFramesAndUnmodifiedSSPLineage',
            'FrameWritesDoNotClobber03F0_03F7_0356_00F8_00FBOrControlSources',
            'NoMappedRegisterOrPeripheralStackSelfAlias', 'NoUnknownNestedNmiOrForegroundWrite',
            'SameValueStoresStillHaveDistinctWriterGenerations',
            'SeparateOwnerAndRetentionAtEveryModeReadyAndParserRead'],
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualIRQDeliveries': 0,
        'actualRetiredInstructions': 0, 'actualMachineId': None, 'actualNativeInstructionIndex': None,
        'actualAllNativeWriteOrdinal': None, 'runtimeAdmission': 'Blocked', 'firmwareReady': False}
