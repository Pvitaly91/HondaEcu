"""Static SSP predecessor obligations; never a CPU history or stack seed.

The earlier source and exchange/RAM-test proofs are reused under their original
conditions.  New caller/second-helper facts narrow the continuation to27D0.
All native event identities remain absent; return-summary edges are obligations.
"""
from copy import deepcopy

STATIC = 'StaticCalRtFrameProvenance_NotCpuExecution'
SOURCE_STATUS = 'SspContinuityConditional'


def _event(label, pc, form, before, after, **extra):
    return {
        'modelEventId': label, 'sourcePC': pc, 'form': form,
        'sourceClassification': 'StaticRomDerived_Conditional_NotObservedNative',
        'incomingSSP': before, 'conditionalSspAfter': after,
        'incomingSspOwner': 'Conditional24F8Lineage_NotCurrentMachineWitness',
        'sourceLineagePreserved': 'OnlyIfTheSpecificEventAndItsObligationsComplete',
        'actualInstructionIndex': None, 'actualNativeWriteOrdinal': None,
        'actualMachineId': None, **extra,
    }


def _call(pc, target, return_pc, rt, **extra):
    return _event('conditional-call-' + format(pc, '04X'), pc, 'CAL addr16', 0x047E, 0x047C,
        callerPC=pc, calleeEntryPC=target, requiredReturnPC=return_pc,
        frameAddress=0x047E, frameWidth=16, sspAfterCAL=0x047C,
        frameCreator='ThisSpecificConditionalCAL_NotAnEarlierInvocation',
        rtConsumerPC=rt, rtReadAddress=0x047E, sspAfterRT=0x047E,
        conditionalReturnedPC=return_pc, actualReturnObserved=False,
        returnSummaryIsNativeCompletion=False, **extra)


def prior_2777_helper():
    """Closed listed helper; branch predicates are not favourable host choices."""
    rows = (
        (0x5CD9, 'MOV DP, #N16', (0x5CDC,)),
        (0x5CDC, 'LB A, [DP]', (0x5CDD,)),
        (0x5CDD, 'CMPB A, #N8', (0x5CDF,)),
        (0x5CDF, 'JGT rel8', (0x5CE1, 0x5CED)),
        (0x5CE1, 'CMPB A, #N8', (0x5CE3,)),
        (0x5CE3, 'JGE rel8', (0x5CE5, 0x5CF9)),
        (0x5CE5, 'CMPB A, #N8', (0x5CE7,)),
        (0x5CE7, 'JGT rel8', (0x5CE9, 0x5CED)),
        (0x5CE9, 'CMPB A, #N8', (0x5CEB,)),
        (0x5CEB, 'JGE rel8', (0x5CED, 0x5CF9)),
        (0x5CED, 'LB A, #N8', (0x5CEF,)),
        (0x5CEF, 'STB A, N8', (0x5CF1,)),
        (0x5CF1, 'DECB N8', (0x5CF4,)),
        (0x5CF4, 'JNE rel8', (0x5CF6, 0x5CF9)),
        (0x5CF6, 'STB A, N8', (0x5CF8,)),
        (0x5CF8, 'BRK', ()),
        (0x5CF9, 'RT', ()),
    )
    return {
        'entry': 0x5CD9, 'normalReturn': 0x5CF9, 'faultExit': 0x5CF8,
        'nodes': [{'pc': pc, 'form': form, 'edges': list(edges)} for pc, form, edges in rows],
        'nodeCount': 17, 'nestedCallSites': [], 'explicitSspWriters': [],
        'explicitLrbWriters': [], 'explicitPswlWriters': [], 'explicitUspWriters': [],
        'sourceRead': {'pc': 0x5CDC, 'address': 0x03D1, 'width': 8,
            'owner': 'CurrentNativeGenerationNotEstablished',
            'candidateEarlierWriter': 0x5CAF,
            'candidateCondition': 'PriorADCBodyWithP2DerivedIndex3AndOwnedADCR1H',
            'coldClearZeroAloneProvesSuccessfulReturn': False},
        'normalReturnPredicates': [
            {'path': 'upper', 'requiredEdges': [[0x5CDF, 0x5CE1], [0x5CE3, 0x5CF9]],
             'source': 'Same5CDCByteAndNativeComparisons5CDD_5CE1',
             'c8PrimaryConflictStillBlocksUnqualifiedSemantics': True},
            {'path': 'middle', 'requiredEdges': [[0x5CDF, 0x5CE1], [0x5CE3, 0x5CE5],
                [0x5CE7, 0x5CE9], [0x5CEB, 0x5CF9]],
             'source': 'Same5CDCByteAndNativeComparisons5CDD_5CE1_5CE5_5CE9',
             'c8PrimaryConflictStillBlocksUnqualifiedSemantics': True},
        ],
        'errorRoute': {'entry': 0x5CED, 'counterSourcePC': 0x2773,
            'counterAddress': 0x00F7, 'conditionalIncomingCounter': 1,
            'decrementPC': 0x5CF1, 'counterAfter': 0,
            'requiredBranch': [0x5CF4, 0x5CF6], 'faultPC': 0x5CF8,
            'qualification': 'FirstReachedCall_AfterRetained2773_NoAliasOrAsyncMutation',
            'hostChosenNonzeroCounterMaySupplyReturn': False},
        'nonframeWritesIn047EContext': [
            {'pc': 0x5CEF, 'address': 0x00AF, 'width': 8},
            {'pc': 0x5CF1, 'address': 0x00F7, 'width': 8},
            {'pc': 0x5CF6, 'address': 0x00F5, 'width': 8},
        ],
        'c8Resolution': 'PrimaryConflictUnresolved_NotChangedByM2cd',
        'actualReturnObserved': False,
    }


def reviewed_ssp_lineage():
    """Independent source candidates and exact missing return/context links."""
    events = [
        _event('code-owned-source-24F8', 0x24F8, 'MOV SSP, #N16', None, 0x047E,
            requiredReach='GenuineApplicableColdEntry_NotMerelyResetVector'),
        _event('exchange-2531', 0x2531, 'XCHG A, SSP', 0x047E, 0x5555,
            savedSource='SameExchangePlacesOldSSPInA', requiredDD=1),
        _event('restore-2533', 0x2533, 'XCHG A, SSP', 0x5555, 0x047E,
            source='SavedAFrom2531_NotNumericalCoincidence', requiredDD=1),
        _event('exchange-254D', 0x254D, 'XCHG A, SSP', 0x047E, 0xAAAA,
            savedSource='SameExchangePlacesOldSSPInA', requiredDD=1),
        _event('restore-254F', 0x254F, 'XCHG A, SSP', 0xAAAA, 0x047E,
            source='SavedAFrom254D_NotNumericalCoincidence', requiredDD=1),
        _call(0x2689, 0x5C5C, 0x268C, 0x5C80,
            firstMissing='FirstGenuineRamTestCallExchangeRestoreAndReturnNotObserved',
            specialFrameWrites=[0x5C68, 0x5C6C],
            restoration='FreshStorageGenerationWithThisCallsRetainedSemanticCreator'),
        _call(0x268D, 0x5C5C, 0x2690, 0x5C80,
            firstMissing='Genuine2689ReturnThenOwnSecondCALFrameAndRestoration',
            specialFrameWrites=[0x5C68, 0x5C6C],
            restoration='DifferentCALAndGeneration_From2689'),
        _call(0x276A, 0x5C86, 0x276D, 0x5CCD,
            firstMissing='OwnedADCOrTimerReturnPredicate_ApplicablePeripheralEffectsAndIntactOwnFrame',
            mayRepeat='P2Read276D_And276F_JNE2771CanReturnTo2766AndCAL276A',
            successfulRepetitionsKnown=False),
        _call(0x2777, 0x5CD9, 0x277A, 0x5CF9,
            firstMissing='OwnedDATA03D1AndUnresolvedC8DependentReturnRoute',
            firstCallCounterSource=0x2773),
        _call(0x27D0, 0x5F45, 0x27D3, 0x60E4,
            firstMissing='CompletePreviousSpecificReturnsAndCurrentSSPFrameOwnership',
            sourceIsActualIncomingSsp=False),
    ]
    return deepcopy({
        'schemaVersion': 1, 'milestone': 'M2cd', 'classification': STATIC,
        'candidateSource': {'pc': 0x24F8, 'value': 0x047E,
            'source': 'CodeOwnedImmediate_IfWriterGenuinelyReached',
            'status': SOURCE_STATUS, 'actualIncomingSsp': None,
            'actualIncomingSspOwner': None, 'runtimeSeedAdmitted': False},
        'explicitNamedWritersInFrozenListedInventory': [0x24F8, 0x2531, 0x2533, 0x254D, 0x254F],
        'explicitNamedWriterInventoryIsGlobalAliasExclusion': False,
        'events': events,
        'exchangeRequirements': ['SameA_SSP_DD1_NonStackAccumulatorContext',
            'AdjacentExchangePairCompletes', 'NoAsyncOrAliasMutationBetweenPair',
            'FreshRegisterGenerationRetainsSavedSource'],
        'ramTestLoop': {'sourceX1PC': 0x267F, 'x1First': 0x03FA, 'decrementPC': 0x2690,
            'decrement': 2, 'conditionalIterations': 510, 'callsPerIteration': [0x2689, 0x268D],
            'indexedBase': 0x0084, 'firstIndexedWord': 0x047E, 'lastIndexedWord': 0x0084,
            'firstIterationFrameIsTemporarilyOverwritten': True,
            'originalStorageGenerationSurvivesUnchanged': False,
            'matchingRestoredFrameSemanticCreatorRequired': True,
            'rankDependsOnC8': False, 'actualIterations': 0,
            'allCallsCannotBeAssumedBalancedFromCfgEdges': True},
        'coldRoute': {'markerWriter': 0x24ED, 'status': 'ConditionalColdEntry_NotObservedReset',
            'source24F8DominatesOnlyBoundedRootedGraph': True,
            'markerGate': 0x269D, 'requiredMarkerClass': 'RetainedColdMarker_Not47',
            'requiredEdge': [0x269D, 0x26F0],
            'excludedOptionalCalls': [0x26A7, 0x26AF, 0x26B2, 0x26B5, 0x26D3, 0x26DC, 0x26E9],
            'excludedUnknownPointerStore': 0x26BA,
            'noncoldOrUnlistedEntryMayBorrowThisProof': False,
            'ramClearLoop': {'sourceDP': 0x270B, 'writer': 0x2710,
                'opaqueC8': 0x2714, 'exitPredicate': 0x271A, 'exitPC': 0x272A,
                'status': 'InheritedCorrelatedFirstExitDomain_NotActualTermination',
                'lowerKnownWriteBoundary': 0x0084,
                'proposedFFFFOrFFFEWriteAdmitted': False}},
        'earliestPrerequisites': {
            'actualRoot': 'ApplicableResetOrIndependentReachingHistoryBefore24ED',
            'firstControlEffect': {'pc': 0x24F4, 'source': 'ApplicableWDTResetClockBehavior'},
            'firstExplicitExternalRead': {'pc': 0x251C, 'address': 0x4700, 'space': 'DATA'},
            'earlyPhysicalOutcome': {'pc': 0x2528, 'source': 'P4Bit1RequiredLow'},
            'pulseControl': {'pcs': [0x262C, 0x2637, 0x2642], 'source': 'P4Bits2Then3LowHighLow'},
            'freshPendingGate': {'pc': 0x264E, 'source': 'IRQHBit5FreshSince261E_NotHostPending'},
            'firstUnobservedMatchedCall': 0x2689,
            'firstPostRamTestCall': 0x276A,
            'newLaterNarrowReturnDependency': 0x2777},
        'prior2777Helper': prior_2777_helper(),
        'producerContext': {
            'lrbSourcePC': 0x2744, 'conditionalLrb': 0x0041,
            'conditionalPage': 0x0200, 'conditionalLocalBank': 0x0208,
            'scbSourcePC': 0x24FF, 'conditionalScb': 0,
            'scbRestorationPCs': [0x2572, 0x2574, 0x257C, 0x257E],
            'uspSourcePC': 0x2754, 'conditionalUsp': 0x0180,
            'noExplicitLrbOrPswlOrUspWriterInSelectedLaterCallees': True,
            'finalDpSourcePC': 0x27B6, 'finalDpIncrementPC': 0x27BA,
            'conditionalDpBefore27D0': 0x0373,
            'x1Value': None, 'x1Owner': 'PriorADCSelectorHistoryOrEarlierRetainedContextRequired',
            'x2Value': None, 'x2Owner': 'RamTestPatternRetentionConditional_NotImportedSnapshot',
            'localAccumulatorPrefix': [0x27BC, 0x27C4, 0x27C5, 0x27C7, 0x27C8, 0x27CA, 0x27CC, 0x27CE],
            'conditionalCF': 1, 'conditionalZF': 0, 'conditionalDD': 0,
            'aValue': 'PrivatelyDerivedCodeValue_NotNativeObservation',
            'fullIncomingPSW': None, 'physicalSF': None,
            'sourceConditions': ['EverySpecificPriorCallAndReturnCompletes',
                'ColdSCB0RestoredAndRetained', 'NoAsyncOrUnknownArchitectureAliasMutation',
                'ApplicableSfrReadWriteEffects', 'NonStackAccumulatorWhereRequired'],
            'receiverScb2MayBeImported': False,
            'laterExternalReads': [0x276D, 0x277A, 0x277E, 0x2789, 0x278F, 0x27A4]},
        'memoryApplicability047E': {'standardMSM66201': 'ExternalDataMappingRequired',
            'standardMSM66207': 'DocumentedInternalRamRegion_ActualDeviceStillUnestablished',
            'actualASICOrBoardMappingEstablished': False, 'physicalStackSafetyEstablished': False},
        'sspMutationDomainsStillRequired': ['CAL_SCAL_VCAL_RT_RTI', 'PUSHS_POPS',
            'IndirectOrRegisterAliasesTo0000_0001', 'IRQ_NMI_TrapFrames', 'BRK_Reset',
            'UnlistedComputedOrDifferentEntryHistory'],
        'nativeIncomingSspEstablished': False, 'actualCpuExecutions': 0,
        'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
        'irqInjected': False, 'firmwareReady': False,
    })


def analyze_ssp_lineage():
    value = reviewed_ssp_lineage()
    return {
        'classification': STATIC, 'sourceStatus': SOURCE_STATUS,
        'closestIndependentExplicitSource': 0x24F8, 'conditionalCandidate': 0x047E,
        'incomingSspOwner': None, 'actualIncomingSSP': None,
        'firstMissingActualPrerequisite': value['earliestPrerequisites']['actualRoot'],
        'firstMissingSpecificMatchedCall': 0x2689,
        'newRequiredReturn': {'caller': 0x2777, 'target': 0x5CD9, 'rt': 0x5CF9,
            'returnPc': 0x277A, 'sourceReadPc': 0x5CDC, 'sourceAddress': 0x03D1,
            'c8Predicates': [0x5CDF, 0x5CE7], 'primaryConflictResolved': False},
        'laterCallerContextConditional': value['producerContext'],
        'simpleBalancedCallCountingEstablishesNativeSsp': False,
        'actualNativeFrameOrdinals': None, 'actualNativeEvents': [],
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
        'actualRetiredInstructions': 0, 'firmwareReady': False,
    }
