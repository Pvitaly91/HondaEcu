"""Conditional first-CAL source cuts, not a CPU evaluator or native journal.

M2ap/M2aq already established the twenty forms and exchange restoration.  The
new graph separates the earlier unknown word retained in DP from the later CAL
creator, and numeric overwrites from still-required IE/control authority.
"""

STATIC = 'StaticRootedFirstRamtestProvenance_NotCpuExecution'


def _instruction(pc, form, length, effect):
    return {'pc': pc, 'form': form, 'length': length, 'conditionalEffect': effect,
        'actualInstructionIndex': None, 'actualMachineId': None,
        'actualNativeWriteOrdinal': None}


def _node(label, pc, action, address, value, source, previous, output, creator):
    return {'modelEventId': 'model:' + label, 'pc': pc, 'action': action,
        'address': address, 'widthBits': 16, 'value': value, 'sourceToken': source,
        'previousToken': previous, 'outputToken': output, 'semanticCreator': creator,
        'actualInstructionIndex': None, 'actualMachineId': None,
        'actualNativeWriteOrdinal': None}


def frame_analysis():
    """Return static expected dependencies; no input is executed or admitted."""
    unknown = 'model:Prior047E_UnknownSource'
    pattern = 'model:Pattern2686'
    creator = 'model:CAL2689_Frame268C_ConditionalCreator'
    gen_a, gen_b, gen_c = 'model:FrameA', 'model:FrameB', 'model:FrameC'
    saved = 'model:SavedAFromFrameA'
    return {
        'classification': STATIC,
        'inheritedSources': [
            {'path': 'docs/M2AQ_FIRST_RAMTEST_CAL_RT_PROVENANCE.md',
             'sha256': 'e6fe8af00c39f518e8fd103475baddacecb56159fec5dd5a3472bb90e99b114e',
             'role': 'InheritedExact20ContractAndCurrentCreatorRestoration'},
            {'path': 'docs/M2AP_SSP_ADC_PENDING_PROVENANCE.md',
             'sha256': '115e4d434ad744cd905b49538b01ca7ea2fd28092762b8be31994db4440e10da',
             'role': 'InheritedConditionalSspSourceAndExchangeProof_NotNewRankProof'},
            {'path': 'docs/M2AR_RESET_WDT_EXTERNAL4700_PROVENANCE.md',
             'sha256': 'adad751978bb60883d9874f83587bd3f12509b30bcc78fa5dfa854ce3a654036',
             'role': 'InheritedNumericNoninterferenceDoesNotEstablishExternalEffects'},
            {'path': 'docs/M2CD_CAL27D0_RT60E4_FRAME_PROVENANCE.md',
             'sha256': 'b4ca685640f24ed5a56a090830501675add17f2447cda20b993464562c467ac7',
             'role': 'ArchitectureAndPhysicalCaveats_NotLaterCallerContextOrNoOverwriteRule'},
            {'path': 'tests/HondaEcu.Core.Tests/FirstRamTestProvenanceFixture.cs',
             'sha256': '1e9a0afd5a00c1b28e697482451f1dede8e98ff545b1851f9e41657fc047f80d',
             'role': 'InheritedInventedCreatorAndAllWriteJournalRequirements'},
        ],
        'context': {
            'lrb': 0x0040, 'pageBase': 0x0200, 'localBase': 0x0200,
            'scb': 0, 'scbSourcePc': 0x24FF,
            'scbRestorationPairs': [[0x2572, 0x2574], [0x257C, 0x257E]],
            'x1': 0x03FA, 'x1Storage': [0x0080, 0x0081],
            'x2Storage': [0x0082, 0x0083], 'dpStorage': [0x0084, 0x0085],
            'er3Storage': [0x0206, 0x0207], 'sspSourcePc': 0x24F8,
            'requiredIncomingSsp': 0x047E,
            'requiredOrdinaryAccumulatorMode': 'SeparateUnobservedApplicabilityCondition_NotPswClear',
            'actualNativeContextEstablished': False,
        },
        'instructionInventory': [
            _instruction(0x267C, 'MOV LRB, #N16', 3, 'Own0040_Page0200_Local0200_NotSCB'),
            _instruction(0x267F, 'MOV X1, #N16', 3, 'Own03FA_InRetainedSCB0Bank'),
            _instruction(0x2682, 'MOV DP, N16[X1]', 4, 'ReadOld047EToDP_BeforeCurrentCAL'),
            _instruction(0x2686, 'L A, #N16', 3, 'OwnA5555_DD1_ZF0_RetainCF_HC'),
            _instruction(0x2689, 'CAL addr16', 3, 'Own268CAt047E_SSP047C_Target5C5C'),
            _instruction(0x5C5C, 'MOV X2, A', 1, 'OwnX25555_NotDPDependent'),
            _instruction(0x5C5D, 'SB off N8.7', 3, 'Set0230Bit7_PreserveUnknownNeighbors'),
            _instruction(0x5C60, 'AND N8, #N16', 5, 'IE_RMW02A0_ControlAuthorityRequired'),
            _instruction(0x5C65, 'ANDB PSWH, #N8', 3, 'ClearMIE_RetainDD_LogicalPswFlagCaveat'),
            _instruction(0x5C68, 'XCHG A, N16[X1]', 4, 'FrameB5555_SaveCurrentCAL268CInA'),
            _instruction(0x5C6C, 'XCHG A, N16[X1]', 4, 'FrameCFresh268C_FromSavedCurrentCreator_A5555'),
            _instruction(0x5C70, 'ST A, er3', 1, 'Own0206Word5555_NotFirstFrameAlias'),
            _instruction(0x5C71, 'ORB PSWH, #N8', 3, 'SetMIE_RetainDD_ControlAndFlagCaveats'),
            _instruction(0x5C74, 'L A, N8', 2, 'ReadRetained00F8_NotHostDefault'),
            _instruction(0x5C76, 'ST A, N8', 2, 'WriteIEFromCurrent00F8_ControlEffectsNotDischarged'),
            _instruction(0x5C78, 'RB off N8.7', 3, 'OldSelectedBit1_GivesZF0_ClearOnlyBit7'),
            _instruction(0x5C7B, 'L A, er3', 1, 'ReadCurrent0206Pattern_A5555_DD1_ZF0'),
            _instruction(0x5C7C, 'CMP A, X2', 2, 'Current5555Equality_OwnCF0_ZF1_RetainHC_DD'),
            _instruction(0x5C7E, 'JNE rel8', 2, 'CurrentCMP_ZF1_NotTaken_To5C80'),
            _instruction(0x5C80, 'RT', 1, 'SSPPlus2_ThenReadFrameC_PC268C_StopBefore268C'),
        ],
        'symbolicChronology': [
            _node('OldWordRead', 0x2682, 'ReadOldWordIntoDP', 0x047E, None,
                  unknown, None, 'model:DPFromPrior047E', None),
            _node('CalFrameA', 0x2689, 'ConditionalFrameStore', 0x047E, 0x268C,
                  'model:NativeNextPc268C', unknown, gen_a, creator),
            _node('CalSsp', 0x2689, 'ConditionalSspDecrement', 0, 0x047C,
                  'model:RestoredSsp24F8', 'model:RestoredSsp24F8', 'model:PostCalSsp', None),
            _node('X2Pattern', 0x5C5C, 'ConditionalPatternStore', 0x0082, 0x5555,
                  pattern, None, 'model:X2Pattern', pattern),
            _node('FrameB', 0x5C68, 'ExchangeTemporaryFrameStore', 0x047E, 0x5555,
                  pattern, gen_a, gen_b, pattern),
            _node('SavedA', 0x5C68, 'ExchangeSavesCurrentFrameInA', 6, 0x268C,
                  gen_a, pattern, saved, creator),
            _node('FrameC', 0x5C6C, 'ExchangeFreshFrameRestoration', 0x047E, 0x268C,
                  saved, gen_b, gen_c, creator),
            _node('RecoveredA', 0x5C6C, 'ExchangeRecoversPatternInA', 6, 0x5555,
                  gen_b, saved, 'model:RecoveredPattern', pattern),
            _node('LocalPattern', 0x5C70, 'ConditionalLocalStore', 0x0206, 0x5555,
                  'model:RecoveredPattern', None, 'model:Er3Pattern', pattern),
            _node('PatternReload', 0x5C7B, 'ConditionalAccumulatorReload', 6, 0x5555,
                  'model:Er3Pattern', 'model:AFromSavedIe', 'model:CmpLeftPattern', pattern),
            _node('RtReader', 0x5C80, 'ConditionalRead_NotWriteGeneration', 0x047E, 0x268C,
                  gen_c, gen_c, 'model:ConditionalPc268C', creator),
        ],
        'sourceCuts': {
            'priorWord': {'readPc': 0x2682, 'readAddress': 0x047E,
                'destination': [0x0084, 0x0085], 'sourceToken': unknown,
                'laterFrameKillPc': 0x2689,
                'terminalDependentFields': ['dp', 'DATA0084_0085'],
                'terminalIndependentProjection': ['pc', 'ssp', 'a', 'dd', 'cf', 'zf', 'frameSemanticCreator'],
                'numericIndependenceRemovesReadAuthority': False},
            'savedIe': {'sourceWriterPc': 0x2569, 'loadPc': 0x5C74,
                'controlWriterPcs': [0x5C60, 0x5C65, 0x5C71, 0x5C76],
                'accumulatorKillPc': 0x5C7B,
                'controlEffectsDischargedByAccumulatorKill': False},
        },
        'obligations': {
            'context': 'OneRootedConditionalHistory_NoCrossMachineOrLater0041ContextSplice',
            'savedIe': 'CLR2566_ST2567IE_ST2569F8_ST256BFA_AllRetained_NoAliasOrAsyncMutation',
            'exchange': 'SameWordEA047E_SameWidth16_SameX1_DD1_NoInterveningAccumulatorMutation',
            'frame': 'Current2689Creator_AInterrupted_BTemporary_CFreshRestore_RtReadsC',
            'allWriteJournal': 'Required_NotProducedBySelectedStaticDependencyNodes',
            'writeOrder': 'PreserveAllWritesAndSameValueWrites_NotOnlyFrameStores',
            'control': 'ApplicableIE_MIE_PswReadMasks_NoUnaccountedNmiResetOrAsyncMutation',
            'flags': 'LogicalOperationsOnPSW_DoNotSupplyCmpFlags_HCRemainsUnknown',
            'sf': 'InheritedPrimaryApplicabilityConflict_PhysicalSFNotEstablished_NoHostDefault',
        },
        'terminalProjection': {
            'pc': 0x268C, 'ssp': 0x047E, 'a': 0x5555,
            'dd': 1, 'cf': 0, 'zf': 1, 'hc': None,
            'mie': 1, 'scb': 0, 'lrb': 0x0040,
            'dp': {'classification': 'SourceValueUnknown', 'sourceReadPC': 0x2682,
                   'sourceToken': unknown, 'value': None},
            'frameToken': gen_c, 'frameSemanticCreator': creator,
            'otherPsw': 'OnlyUnmodifiedFieldsRetained_ReservedReadMasksApply_NotCallerSnapshot',
            'flagByte0230': 'Bit7Cleared_UnknownNeighborBitsPreserved',
            'wholeStateIndependentOfPriorWord': False,
        },
        'physicalApplicability': {
            'frame': [0x047E, 0x047F], 'widthBits': 16, 'byteOrder': 'LittleEndian',
            'wordAddress': '2*floor(SSP/2)_Unsigned16Arithmetic',
            'standard66201': 'ExternalDATA_RequiresApplicableMappingAndCompletion',
            'standard66207': 'DocumentedInternalDATA_NotActualEcuIdentification',
            'actualAsicEstablished': False, 'actualFrameMemorySuitable': False,
            'softwareNumericRestorationEstablishesHardwareSafeRestoration': False,
        },
        'runtimeExclusions': {
            'OriginalRomExecutionAdmission': 'Blocked', 'actualNativeFrameDependency': 'NotObserved',
            'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
            'actualRetiredInstructions': 0, 'actualMachineId': None,
            'actualNativeInstructionIndex': None, 'actualAllNativeWriteOrdinal': None,
            'actualRawByteWriteOrdinals': None, 'actualNativeReadLinkage': None,
            'actualNativeReturnObserved': False, 'stopBefore268C': True,
            'secondCal268DExecuted': False, 'firmwareReady': False,
        },
    }
