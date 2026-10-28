"""Independent finite source-relation evaluator, never a CPU executor.

Inputs are explicitly invented histories. Matching every relation cannot grant
runtime authority or turn any unknown hardware observation into a fact.
"""
from copy import deepcopy
import json
from pathlib import Path

STATIC = 'StaticRootedFirstRamtestProvenance_NotCpuExecution'
RESEARCH = 'CONDITIONAL_ROOT_TO_FIRST_CAL_OBLIGATIONS_REFINED / EXECUTION_BLOCKED'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('ascii')


def evaluate_case(case):
    """Check a single finite invented history; no stepping or memory emulation."""
    c = deepcopy(case)
    root, wdt, ext = c['root'], c['wdt'], c['external']
    ctx, frame, flags, rt = (c[k] for k in ('context', 'frame', 'flags', 'rt'))
    pulse, irq, actual = c['pulses'], c['irq'], c['actual']
    samples = pulse['samples']
    expected_samples = [(selector, phase, level, pc) for selector in (2, 3)
        for phase, level, pc in ((0, 0, 0x2629), (1, 1, 0x2634), (2, 0, 0x263F))]
    observed_samples = [(s['selector'], s['phase'], s['level'], s['readerPC']) for s in samples]
    checks = [
        (root['actualResetClaim'] is False, 'ResetVectorIsNotActualResetEvent'),
        (root['cause'] == 'ExternalRes' and root['vectorAddress'] == 0
            and root['vectorTarget'] == 0x24ED and root['coldSourcesRetained'] is True, 'ResetCauseColdSourceMismatch'),
        (wdt['hardwareSafe'] is None, 'WdtCommandSafetyUnknown'),
        (wdt['readback'] is None, 'WriteOnlyWdtReadbackInvented'),
        (ext['space'] == 'DATA' and ext['address'] == 0x4700, 'DataProgramSourceConfusion'),
        (ext['numericIndependent'] is True and ext['readCompletion'] is None
            and ext['sideEffects'] is None, 'NumericNoninterferenceDoesNotDischargeBus'),
        (c['earlyP4']['forcedNative'] is False and c['earlyP4']['value'] == 0
            and c['earlyP4']['origin'] == 'InventedOnly', 'ForcedP4NativeOutcome'),
        (observed_samples == expected_samples and [s['sequence'] for s in samples] == list(range(1, 7)),
            'PulseSampleOrderMismatch'),
        (len({s['token'] for s in samples}) == 6, 'PulseSampleTokenReused'),
        (pulse['physicalMilliseconds'] is None, 'RetirementRankIsNotMilliseconds'),
        (irq['clearPC'] == 0x261E and irq['clearSequence'] < irq['ownerSequence'] < irq['readerSequence'],
            'StalePendingBeforeClear'),
        (irq['readerPC'] == 0x264B and irq['branchPC'] == 0x264E
            and irq['wordBit'] == 13 and irq['highBit'] == 5 and irq['factor'] == 'PWM1Overflow',
            'WrongIrqFactor'),
        (irq['origin'] == 'InventedOnly', 'HostPendingRejected'),
        (ctx['sspSourcePC'] == 0x24F8 and ctx['ssp'] == 0x047E, 'WrongSspSource'),
        (ctx['scb'] == 0, 'WrongScb'),
        (ctx['lrb'] == 0x0040, 'WrongLrb'),
        (ctx['x1'] == 0x03FA, 'WrongX1'),
        (ctx['effectiveAddress'] == (ctx['x1'] + 0x84) & 0xFFFE == 0x047E, 'WrongEffectiveAddress'),
        (frame['callPC'] == 0x2689 and frame['targetPC'] == 0x5C5C
            and frame['returnPC'] == frame['callPC'] + 3, 'WrongReturnPc'),
        (frame['staleCanary'] is False and frame['creator'] == 'CAL2689/first', 'StaleCanaryNotCurrentCalFrame'),
        (0x5C68 in frame['exchangePCs'], 'MissingFirstExchange'),
        (0x5C6C in frame['exchangePCs'], 'MissingRestoreExchange'),
        (frame['exchangePCs'] == [0x5C68, 0x5C6C]
            and len(set(frame['generationTokens'])) == 3
            and frame['generationTokens'] == ['frameA', 'frameB', 'frameC'], 'StorageGenerationNotFresh'),
        (frame['restoredCreator'] == frame['creator'] and frame['savedAccumulatorToken'] == 'frameA'
            and frame['readerToken'] == 'frameC', 'WrongSemanticCreator'),
        (frame['history'] == ctx['history'] and all(h == ctx['history'] for h in ctx['bindings']),
            'CrossMachineFrame'),
        (ctx['technicalImport'] is False, 'TechnicalSspImport'),
        (c['controls']['ignored'] is False and c['controls']['savedIEWriterPC'] == 0x2569
            and c['controls']['savedIEZeroProducerPC'] == 0x2566, 'IgnoredControlEffects'),
        (flags['logicalFlagsKnown'] is False and flags['hc'] is None, 'LogicalPswFlagsUnknown'),
        (flags['producerPC'] == 0x5C7C and flags['cf'] is False and flags['zf'] is True
            and flags['dd'] is True, 'WrongCmpFlags'),
        (flags['jneNextPC'] == 0x5C80, 'FaultBranchAccepted'),
        (rt['form'] == 'RT' and rt['pc'] == 0x5C80, 'RtiIsNotRt'),
        (rt['entrySource'] == 'ReachedByJne', 'HostSelectedRtEntry'),
        (rt['sspManuallyRepaired'] is False, 'HostSspRepair'),
        (actual == {'cpuExecutions': 0, 'romExecutions': 0, 'machineId': None,
            'instructionIndex': None, 'writeOrdinal': None}, 'ActualObservationFabricated'),
        (c['memory']['actualDevice'] == 'Unknown' and c['memory']['assumedInternal'] is False,
            'UnknownMemoryApplicability'),
        (c['preservation']['historicalExpected'] == c['preservation']['recordedExpected'],
            'HistoricalFingerprintRewritten'),
        (c['approval']['author'] != c['approval']['approver']
            and c['approval']['sourceIdentity'] == c['approval']['approvedIdentity'], 'SourceGuardSelfApproval'),
        (c['precal']['readerPC'] == 0x2682 and c['precal']['readToken'] == 'old047E'
            and c['precal']['value'] is None
            and c['precal']['dpToken'] == 'old047E' and c['precal']['futureFrameSubstitution'] is False,
            'PrecalReadBorrowedFutureFrame'),
        (rt['stopBeforePC'] == 0x268C, 'WrongTerminalBoundary'),
    ]
    first = next((reason for valid, reason in checks if not valid), None)
    return {'valid': first is None, 'firstMissingObligation': first,
        'conditionalTerminalPC': 0x268C if first is None else None,
        'classification': 'InventedOnly_ConditionalObligationsMatch' if first is None else 'InventedOnly_Refused',
        'actualCpuExecutions': 0, 'actualRomExecutions': 0, 'actualMachineId': None,
        'actualInstructionIndex': None, 'actualWriteOrdinal': None,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False}


def admission_dag():
    """Separate source facts and missing authority for each ordered condition."""
    rows = (
        ('root', 0x24ED, [], 'PROGRAM0000_ResetVector', 'Applicable reset transition and silicon'),
        ('wdt', 0x24F4, ['root'], 'CodeOwned3C_WriteOnlyCommand', 'Applicable command acceptance and immediate/deferred effects'),
        ('ssp', 0x24F8, ['wdt'], 'CodeOwned047E_IfReached', 'Actual writer generation and retained DATA0000_0001'),
        ('external', 0x251C, ['ssp'], 'DATA4700_ReadViaDP2519', 'Physical read completion and side effects'),
        ('early-p4', 0x2528, ['external'], 'P4_1_OrdinaryConditionalRead', 'Actual zero observation before configuration'),
        ('ssp-pairs', 0x254F, ['early-p4'], '2531_2533_254D_254F_SameHistory', 'Matching accumulator and accepted restored SSP generations'),
        ('saved-ie', 0x2569, ['ssp-pairs'], 'CLR2566_IE2567_F82569_FA256B', 'Retained zero generation and control applicability'),
        ('config', 0x260B, ['saved-ie'], 'PWMCON0_3E_PWMCON1_7E_P4IO0D_SFFC', 'Applicable accepted retained register writes'),
        ('irq-clear', 0x261E, ['config'], 'CodeOwnedWordClear', 'Actual clear before enabled factor'),
        ('pulses', 0x263F, ['irq-clear'], 'MBR2629_2634_263F_Selectors2Then3', 'Distinct PWM output LOW_HIGH_LOW observations'),
        ('irq-read', 0x264B, ['pulses'], 'IRQH5_PWM1Overflow_RetainedEnable', 'Fresh factor after clear, retained until current read/ack'),
        ('context', 0x267F, ['irq-read'], 'SCB0_LRB0040_X103FA_SSP047E', 'Same rooted context and ordinary accumulator applicability'),
        ('old-word', 0x2682, ['context'], 'Old047EWordToDP', 'Actual read authority/completion; value remains unknown'),
        ('cal', 0x2689, ['old-word'], 'NextPc268C_CurrentFrameCreatorA', 'Actual one-machine CAL and all-write generation linkage'),
        ('restore', 0x5C6C, ['cal'], 'A_SavedAcrossTemporaryB_RestoredFreshC', 'No unaccounted writes or accumulator/control interference'),
        ('rt', 0x5C80, ['restore', 'saved-ie'], 'CMP5C7C_JNE5C7E_CurrentCRead', 'Actual matched RT read; stop before268C'),
    )
    return [{'conditionId': name, 'pc': pc, 'dependsOn': deps, 'source': source,
        'classification': 'StaticSourceCondition_NotObservedNativeProof',
        'knownSoftwareFact': source, 'missingOwnerOrEvent': missing,
        'nativeGenerated': 'ConditionalIfReached_NoActualGenerationObserved',
        'hardwareDependent': True, 'actuallyObserved': False,
        'firstUnresolvedDependency': deps[0] if deps else 'ApplicableResetTransition'}
        for name, pc, deps, source, missing in rows]


def root_frontier():
    return {'sourceRoot': 'PROGRAM0000_ResetVector', 'rootClassification': 'StaticRomDerived_NotResetObserved',
        'resetCause': 'ExternalRES_ApplicabilityUnknown', 'vectorAddress': 0, 'vectorTarget': 0x24ED,
        'otherVectors': [{'vector': 2, 'target': 0x24F4, 'cause': 'BRK'},
            {'vector': 4, 'target': 0x24DC, 'cause': 'WDT_OpcodeTrap'},
            {'vector': 6, 'target': 0x003C, 'cause': 'NMI'},
            {'vector': 0x10, 'target': 0x24D6, 'cause': 'Timer0Overflow_NotReset'}],
        'standardReset': {'ssp': 0xFFFF, 'acc': 0, 'lrb': None, 'pointingRegisters': None,
            'psw': 'ReadOneAndUndefinedRules_NotCpuNewDefaults', 'physicalSf': None},
        'wdtCommandPC': 0x24F4, 'wdtCommandClassification': 'WdtCommandMeaningNotEstablished',
        'missingPrimaryWdtEvidence': ['Exact3CCommandDecoding', 'ImmediateAndDeferredEffects',
            'ControlAcceptance', 'ApplicabilityToActualEcuSilicon'],
        'sspWriterPC': 0x24F8, 'sspValue': 0x047E, 'sspOwner': 'ConditionalCodeOwned_NotNativeObserved',
        'sspExchangePairs': [[0x2531, 0x2533], [0x254D, 0x254F]],
        'externalReadPC': 0x251C, 'externalReadSource': 'DATA4700_NotPROGRAM',
        'externalReadCompletion': None, 'firstMissingObligation': 'ApplicableResetTransition',
        'earliestHardwareControl': 0x24F4, 'earliestUnknownDataOperand': 0x24F1,
        'earliestUnknownExternalDataOperand': 0x251C,
        'earliestNativeFrameCreatorNeeded': 0x2689,
        'nearestFutureSlice': {'entry': 0x267C, 'stopBefore': 0x268C, 'admittedNow': False,
            'entryMustBeReachedThroughSameRootHistory': True, 'hostEntryBypassesRootAllowed': False},
        'admissionDag': admission_dag(),
        'minimalDistinctCuts': ['ApplicableResetAndSilicon', 'Wdt3CControlProgress',
            'ReadableRetainedDataAndSfrControl', 'ExternalDATA4700CompletionAndP4_1',
            'NativeConfiguredPwmOutputSamplesAndFreshPwm1Pending',
            'SourceConsistentScb0Lrb0040Ssp047EAndOld047ERead',
            'NoUnaccountedAsyncEffectsAcrossIeMieChanges', 'MatchedCalSavedTokenFreshRestorationAndRtRead'],
        'nextSmallestEvidenceTask': 'AcquireApplicablePrimaryWdt3CCommandDecodeAndDeferredEffectBefore24F8',
        'newPrimaryAcquisition': False, 'actualNativeInstructionIndex': None,
        'actualAllNativeWriteOrdinal': None, 'actualMachineId': None,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
        'OriginalRomExecutionAdmission': 'Blocked', 'firmwareReady': False}


def canonical_records():
    from .gate_sources import gate_analysis
    from .frame_obligations import frame_analysis
    from .reference_oracle import independent_check, curated_controls, validate_integrated_case
    contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    if contract != {'schemaVersion': 1, 'milestone': 'M2ce', 'classification': STATIC,
            'baseSha': '9e136ccc53712e5b51d623af174abdd5c84763cc',
            'researchClassification': RESEARCH, 'runtimeAdmission': 'Blocked',
            'firmwareReady': False}:
        raise ValueError('ExactStaticM2ceContractRequired')
    gates, frame = gate_analysis(), frame_analysis()
    comparison = independent_check(gates, frame)
    records = [{'caseId': name, 'classification': STATIC, 'data': data,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0}
        for name, data in (('root-and-distinct-frontiers', root_frontier()),
            ('native-configured-gate-sources', gates), ('first-frame-source-cuts', frame),
            ('independent-source-obligation-comparison', comparison))]
    for control in curated_controls():
        case = control['input']
        actual, expected = evaluate_case(case), validate_integrated_case(case)
        if canonical(actual) != canonical(expected):
            raise ValueError('IndependentIntegratedObligationMismatch:' + control['caseId'])
        records.append({'caseId': control['caseId'], 'classification': STATIC,
            'data': {'input': case, 'result': actual, 'independentComparison': 'PASS'},
            'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0})
    return records
