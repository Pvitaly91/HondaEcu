"""Closed invented IRQ/frame/source relations; never a CPU or IRQ executor.

Coverage is the frozen curated controls and reviewed mutations, not arbitrary
external-input admission. Modeled tokens and values never become native owners.
"""
from copy import deepcopy
import json
from pathlib import Path

STATIC = 'StaticIrq0213FourInvocationProvenance_NotCpuExecution'
RESEARCH = 'CONDITIONAL_FOUR_INVOCATION_STATE_CONTINUITY_ESTABLISHED / EXECUTION_BLOCKED'
ACTUAL = {'branch064FExecuted': False, 'cpuExecutions': 0, 'eventOrdinal': None,
    'irqDeliveries': 0, 'machineId': None, 'parserExecuted': False, 'romExecutions': 0,
    'rtiExecutions': 0, 'srbufPacketObserved': False, 'writeOrdinal': None}
PROFILES = {'UserTable17_1': 'SerialTransmittingReady', 'InstructionTable1_1': 'SerialReceivingReady'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('ascii')


def empty(case_id, reason):
    return {'caseId': case_id, 'valid': reason is None,
        'classification': 'InventedOnly_Refused' if reason else 'InventedOnly_ConditionalFourInvocationRelations',
        'firstMismatch': reason, 'firstMissingObligation': reason or 'ActualSourceProfileAndFourIRQFrameAndReadHistories',
        'sourceProfile': None, 'conditionalCause': None, 'allocationConflictPreserved': True,
        'modeledFrames': [], 'modeledStages': [], 'persistentWriteCount': 0,
        'readyGeneration': None, 'maskBit1Entry': None, 'maskBit1Tail': None, 'mieWindow': None,
        'bufferParities': [], 'conditionalContentChangeGaps': [], 'parserRequirements': None,
        'preservation': None, 'actual': deepcopy(ACTUAL), 'runtimeAdmission': 'Blocked', 'firmwareReady': False}


def frame_words(ssp):
    return [(role, ((ssp - delta) & 0xFFFF) & 0xFFFE)
        for role, delta in (('PC', 0), ('A', 2), ('LRB', 4), ('PSW', 6))]


def evaluate_case(case):
    c = deepcopy(case)
    cid = c.get('caseId') if type(c) is dict else None
    sections = ('actual', 'effects', 'foreground', 'frameContract', 'handler', 'initialRam',
        'irq', 'preservation', 'srbuf', 'stateSources')
    if (type(c) is not dict or any(type(c.get(k)) is not dict for k in sections)
            or c.get('classification') != 'InventedOnly_ConditionalFourInvocationState'
            or type(c.get('frames')) is not list or len(c['frames']) != 4
            or type(c['srbuf'].get('reads')) is not list or len(c['srbuf']['reads']) != 4):
        return empty(cid, 'ClosedCaseShapeRequired')
    try:
        return _evaluate(c, cid)
    except (KeyError, TypeError, IndexError):
        return empty(cid, 'ClosedCaseShapeRequired')


def _evaluate(c, cid):
    q, f, h, s, p, src, fg, effects = (c[k] for k in
        ('irq', 'frameContract', 'handler', 'srbuf', 'preservation', 'stateSources', 'foreground', 'effects'))
    frames, reads, ram0 = c['frames'], s['reads'], c['initialRam']
    if (any(type(r) is not dict or type(r['value']) is not int or not 0 <= r['value'] <= 255 for r in reads)
            or any(type(x) is not dict or type(x['savedContext']) is not dict for x in frames)
            or any(type(ram0[k]) is not int or not 0 <= ram0[k] <= 255
                for k in (*('r' + str(i) for i in range(8)), 'status0356'))):
        return empty(cid, 'ClosedCaseShapeRequired')
    values = [r['value'] for r in reads]
    hh, length, flag, kk = values
    layouts = [frame_words(x['incomingSSP']) if type(x['incomingSSP']) is int
        and 0 <= x['incomingSSP'] <= 0xFFFF else [] for x in frames]
    footprints = [{b for _, a in rows for b in (a, a + 1)} for rows in layouts]
    expected_requirements = [{'r2': None, 'r5': None, 'r7': 0}, {'r2': None, 'r5': 1, 'r7': 2},
        {'r2': 4, 'r5': 2, 'r7': 2}, {'r2': 4, 'r5': 3, 'r7': 2}]
    checks = [
        (q['profile'] in PROFILES and q['cause'] == PROFILES.get(q['profile']), 'TxRxSourceConflated'),
        (q['vector'] == 0x000A and q['entryPC'] == 0x0213, 'Vector000AConfusedWith000E'),
        (s['address'] == 0x0055 and s['name'] == 'SerialReceivingDataBuffer' and s['widthBits'] == 8,
            'SrbufTreatedAsTransmitRegister'),
        (len({r['readId'] for r in reads}) == 4, 'OneSampleReusedFourTimes'),
        (q['pendingImpliesDelivery'] is False, 'PendingTreatedAsDelivery'),
        (all(type(x['creator']) is str and x['creator'].startswith('model:') for x in frames), 'MissingFrameCreator'),
        (f['byteCount'] == 8 and f['entryRoleOrder'] == ['PC', 'A', 'LRB', 'PSW'], 'WrongFrameWidthOrOrder'),
        (f['rtiForm'] == 'RTI', 'RtSubstitutedForRti'),
        (all(x['rtInstructionPC'] == 0x029C and x['returnSource'] == 'MatchingEntrySavedPC'
            for x in frames), 'RtiInstructionAddressUsedAsReturnPC'),
        (f['entrySspDelta'] == -8 and f['rtiSspDelta'] == 8, 'WrongSspArithmetic'),
        (len({x['id'] for x in frames}) == 4 and len({x['creator'] for x in frames}) == 4
            and all(x['rtiConsumer'] == x['creator'] == x['id'] + ':entry' for x in frames), 'CrossInvocationFrameIdentity'),
        (p['unknownNestedEventsIgnored'] is False, 'UnknownNestingIgnored'),
        (fg['scb'] == 0, 'HandlerScbImportedIntoParser'),
        (h['scb'] == 2 and h['lrb'] == 0x007E and h['localBase'] == 0x03F0, 'WrongLocalBankMap'),
        (ram0['r7'] == 0 and src['r7'] == 'ConditionalStartupWord2710FromClr2706', 'FabricatedInitialR7'),
        (c['stageRequirements'] == expected_requirements, 'WrongR5R2Progression'),
        (length == 4, 'Length3CannotWriteFlag'),
        (flag & 1 == 1, 'EvenFlagAccepted'),
        (sum(values) & 255 == 0 and hh == 0x21, 'IncorrectChecksum'),
        (effects['readyWriterPC'] == 0x0290, 'WrongReadyGeneration'),
        (ram0['status0356'] & 2 == 2 and src['mode'] == 'Conditional60D5SourceBitOwner', 'MissingMode0356Bit1'),
        (ram0['status0356'] & 0x40 == 0, 'Error0356Bit6Ignored'),
        (s['completion'] == 'Unknown' and s['receiveCompletionCountClaim'] is None
            and all(r['actualValue'] is None for r in reads), 'InventedSrbufReadCompletion'),
        (p['mapping03F3'] == 'UnknownActualChip_201External_207Internal', 'Assumed03F3Internal'),
        (src['sourceMachine'] == src['retainedMachine'] == c['machine'], 'CrossMachineRamTransfer'),
        (fg['hostPCJump'] is None, 'HostParserPCJump'),
        (fg['default011FZero'] is False, 'Default011FZero'),
        (p['importedHistoricalGeneration'] is None, 'ImportedM2agGeneration'),
        (c['actual']['eventOrdinal'] is None and c['actual']['writeOrdinal'] is None
            and c['actual']['machineId'] is None and src['actualR7Owner'] is None and src['actualModeOwner'] is None
            and all(x['actualCreator'] is None and x['actualRestoredPC'] is None for x in frames), 'FakeNativeOrdinal'),
        (canonical(c['actual']) == canonical(ACTUAL) and q['actualSource'] is None and q['actualPending'] is None
            and q['actualEnabled'] is None and q['actualPriority'] is None
            and all(x['actualCreator'] is None for x in frames), 'CurrentIrqExecutionClaimed'),
        (p['historicalExpected'] == p['recordedExpected'], 'HistoricalFingerprintRewritten'),
        (q['allocationConflictAcknowledged'] is True and q['universalCauseClaim'] is False,
            'UniversalVectorAllocationClaim'),
        (h['sameMaskOwnerAssumed'] is False and h['entryIeOwner'] != h['tailIeOwner'], 'SourceMaskOwnerSplice'),
        (h['mieAfter0217'] == 1 and h['mieClearedAt'] == 0x0297 and h['pswLiteral'] == 0x0102 and h['nestingIgnored'] is False,
            'MieWindowIgnored'),
        (all(not fp.intersection(range(0x03F0, 0x03F8)) for fp in footprints), 'FrameParserBankOverlap'),
        (all(not fp.intersection(range(0x00F8, 0x00FC)) for fp in footprints), 'FrameIeShadowOverlap'),
        (effects['headerSavesOldR1ToR0'] is True, 'HeaderOldR0SaveOmitted'),
        (s['contentChangesBetweenReads'] == [True, True, True]
            and s['storageSemantics'] == 'ConditionalNonDestructiveCurrentBufferHypothesis', 'ParityGapContentFreeze'),
        (f['sfClaim'] == 'UnknownNotAssignedByPrimaryFunction', 'RtiSfZeroAssumed'),
        (all(bool(fp) for fp in footprints), 'UnknownSspCannotBeDeclaredSafe'),
        (all(not fp.intersection(range(0x00C0)) and 0x0356 not in fp for fp in footprints),
            'FrameSfrOrPointingRamOverlap'),
        (f['rtiRestoresIE'] is False, 'RtiDoesNotRestoreIE'),
        (f['rtiRestoresPointingRam'] is False, 'RtiDoesNotRestorePointingRam'),
        (fg['noPrematureParserConsumptionHypothesis'] is True, 'PrematureParserConsumption'),
        (fg['scb'] == 0 and fg['lrb'] == 0x0041 and fg['usp'] == 0x0180 and fg['parserPC'] == 0x28AE,
            'WrongParserContext'),
        ([(r['role'], r['pc'], r['invocationId']) for r in reads]
            == [(role, pc, frames[i]['id']) for i, (role, pc) in enumerate(
                (('H', 0x0277), ('L', 0x027F), ('F', 0x0262), ('K', 0x0284)))], 'WrongReadSiteOrInvocation'),
        (p['foregroundOverwriteIgnored'] is False and p['domain'] == 'ExplicitDisjointAndNoUnaccountedWritesHypothesis'
            and effects['deduplicateSameValueWrites'] is False and h['entryIeSource'] == 0x00FA
            and h['tailIeSource'] == 0x00F8 and (h['entryIeWord'], h['tailIeWord'])
            in ((0x02A0, 0x2BAB), (0x00A0, 0xA9A3)), 'ClosedCaseShapeRequired'),
    ]
    reason = next((reason for passed, reason in checks if not passed), None)
    if reason is not None:
        return empty(cid, reason)
    result = empty(cid, None)
    result.update(sourceProfile=q['profile'], conditionalCause=PROFILES[q['profile']],
        maskBit1Entry=(h['entryIeWord'] >> 1) & 1, maskBit1Tail=(h['tailIeWord'] >> 1) & 1,
        mieWindow={'clearPC': 0x0297, 'entryIEOwner': 'Source00FA',
            'nestedSafety': 'ExplicitNoUnaccountedInterferenceHypothesis_NotObservation',
            'setPC': 0x0217, 'tailIEOwner': 'Source00F8'},
        bufferParities=[v & 1 for v in values], conditionalContentChangeGaps=[True, True, True],
        parserRequirements={'actualReached': False, 'command': 0x21, 'entryPC': 0x28AE,
            'flagBit0': 1, 'lrb': 0x0041, 'modeBit1': 1, 'readyBit7': 1, 'scb': 0, 'usp': 0x0180},
        preservation='ConditionalDisjointAndNoUnaccountedWritesOnly')
    for frame, words in zip(frames, layouts):
        slots = [{'role': role, 'wordAddress': addr, 'byteAddresses': [addr, addr + 1],
            'savedSource': frame['savedContext'][role]} for role, addr in words]
        result['modeledFrames'].append({'invocationId': frame['id'], 'creator': frame['creator'],
            'sspBefore': frame['incomingSSP'], 'sspAfterEntry': (frame['incomingSSP'] - 8) & 65535,
            'sspAfterRti': frame['incomingSSP'], 'entryWordSlots': slots,
            'rtiWordReads': [{'step': i + 1, 'role': slot['role'], 'wordAddress': slot['wordAddress'],
                'savedSource': slot['savedSource']} for i, slot in enumerate(reversed(slots))],
            'restoredContext': deepcopy(frame['savedContext']), 'rtInstructionPC': 0x029C, 'actualRestoredPC': None})
    ram = deepcopy(ram0)
    for i, read in enumerate(reads, 1):
        before, writes = deepcopy(ram), []
        def store(pc, address, key, value, source):
            ram[key] = value & 255
            writes.append({'pc': pc, 'address': address, 'widthBits': 8, 'value': ram[key],
                'storageGeneration': 'model:' + cid + ':i' + str(i) + ':w' + str(len(writes) + 1),
                'semanticSource': source})
        store(0x0222, 0x0356, 'status0356', ram['status0356'] & 0xBF, 'RetainedNeighborOwners')
        value = read['value']; role = read['role']; zf = cf = None
        if role == 'H':
            store(0x0275, 0x03F0, 'r0', ram['r1'], 'OldR1BeforeHeader')
            store(0x0279, 0x03F1, 'r1', value, 'DistinctRead:' + read['readId'])
            store(0x027A, 0x03F6, 'r6', value, 'DistinctRead:' + read['readId'])
            store(0x027B, 0x03F5, 'r5', 1, 'CodeConstant')
            store(0x0270, 0x03F7, 'r7', 2, 'CodeConstant')
        elif role in ('L', 'F'):
            pc, address, key = (0x0281, 0x03F2, 'r2') if role == 'L' else (0x0269, 0x03F3, 'r3')
            store(pc, address, key, value, 'DistinctRead:' + read['readId'])
            store(0x026D, 0x03F6, 'r6', ram['r6'] + value, 'NativeWidth8Arithmetic')
            store(0x026F, 0x03F5, 'r5', ram['r5'] + 1, 'NativeWidth8Arithmetic')
            store(0x0270, 0x03F7, 'r7', 2, 'CodeConstant')
        else:
            total = ram['r6'] + value
            zf, cf = int((total & 255) == 0), int(total > 255)
            store(0x0290, 0x0356, 'status0356', ram['status0356'] | 0x80, 'SB0290')
            result['readyGeneration'] = writes[-1]['storageGeneration']
            store(0x0293, 0x03F7, 'r7', 0, 'CodeConstant')
        result['modeledStages'].append({'role': role, 'invocationId': frames[i - 1]['id'],
            'readId': read['readId'], 'readPC': read['pc'], 'modeledReadValue': value,
            'ramBefore': before, 'ramAfter': deepcopy(ram), 'orderedPersistentWrites': writes,
            'checksumZF': zf, 'checksumCF': cf})
        result['persistentWriteCount'] += len(writes)
    return result


def missing_frontier():
    return {'classification': STATIC, 'researchClassification': RESEARCH,
        'earliestSource': 'ApplicableManufacturerVectorAllocationAndCurrentSilicon',
        'firstEvent': 'CurrentPendingEnableMiePriorityAndSafeMatchingEntryFrame_NotObserved',
        'frame': {'savedRoles': ['PC', 'A', 'LRB', 'PSW'], 'restoredRoles': ['PSW', 'LRB', 'A', 'PC'],
            'actualSSP': None, 'actualSavedPC': None, 'sf': None,
            'overlapCounterexampleSsp': 0x03F6, 'overlapBank': [0x03F0, 0x03F7]},
        'sourceReads': {'dataAddress': 0x0055, 'pcs': [0x0277, 0x027F, 0x0262, 0x0284],
            'actualOwners': [None] * 4, 'receiveCompletions': None, 'txEvents': None},
        'bootstrap': 'CurrentR7OwnerMode60D5BitSourceAndRetainedF8FaMasks_NotHostDefaults',
        'retention': 'PerEntryFrameStatusRmwNestedAndForegroundGenerations_NoPremature28BBConsumption',
        'foreground': 'MatchedSavedPCAndContextPlusGenuinePathTo28AE_NoHostPcAssignment',
        'separateReaderGate': 'CurrentDATA011F3ZeroOwnerBefore064C_Unestablished',
        'actual': deepcopy(ACTUAL), 'runtimeAdmission': 'Blocked', 'firmwareReady': False}


def invocation_obligations(case, result):
    rows = []
    for i, frame in enumerate(case['frames']):
        stage = result['modeledStages'][i] if result['valid'] else None
        rows.append({'invocationIndex': i + 1, 'classification': 'StaticConditionalObligations_NotNativeObservation',
            'vectorAddress': 0x000A, 'irqSource': None, 'conditionalSourceProfile': case['irq']['profile'],
            'irqPendingStatus': None, 'irqEnabledStatus': None, 'irqDeliveryObserved': False,
            'entryPC': 0x0213, 'incomingSSP': None, 'frameFootprint': None, 'frameCreator': None,
            'modeledIncomingSSP': frame['incomingSSP'], 'modeledFrameCreator': frame['creator'],
            'modeledFrameLayout': result['modeledFrames'][i] if result['valid'] else None,
            'savedPCSource': None, 'savedASource': None, 'savedLRBSource': None, 'savedPSWSource': None,
            'handlerSCB': 2, 'handlerLRB': 0x007E, 'srbufReadPC': case['srbuf']['reads'][i]['pc'],
            'srbufValueSource': 'UnknownActualPeripheralByte_SeparateModeledReadIdentity',
            **{'r' + str(k) + 'BeforeAfter': {'actualBefore': None, 'actualAfter': None,
                'modeledBefore': stage['ramBefore']['r' + str(k)] if stage else None,
                'modeledAfter': stage['ramAfter']['r' + str(k)] if stage else None} for k in (1, 2, 3, 5, 6, 7)},
            'mode0356Source': {'actualOwner': None, 'conditionalSource': case['stateSources']['mode']},
            'ready0356Source': {'actualOwner': None, 'modeledLastWriter': 0x0290 if i == 3 and stage else None},
            'rtInstructionPC': 0x029C, 'restoredForegroundPC': None, 'restoredForegroundContext': None,
            'ramRetention': result['preservation'], 'firstMissingObligation': result['firstMissingObligation'],
            'actualMachineId': None, 'actualEventOrdinal': None, 'actualWriteOrdinal': None})
    return rows


def canonical_records():
    from .irq_frame import irq_analysis
    from .invocation_lineage import lineage_analysis
    from .reference_oracle import curated_controls, independent_check, reference_case
    contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    required = {'schemaVersion': 1, 'milestone': 'M2ch', 'classification': STATIC,
        'baseSha': '57f153815d61a44d6c3ce9efdc14c5937e5c4c31', 'researchClassification': RESEARCH,
        'analysisRecords': 4, 'inventedConstraintCases': 44, 'negativeRequirementCategories': 39,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False}
    if canonical(contract) != canonical(required):
        raise ValueError('ExactM2chStaticContractRequired')
    irq, lineage = irq_analysis(), lineage_analysis()
    checked = independent_check(irq, lineage)
    if checked.get('valid') is not True:
        raise ValueError('IndependentStaticSourceProjectionMismatch')
    records = [{'caseId': name, 'classification': STATIC, 'data': value,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0}
        for name, value in (('irq-manufacturer-frame-and-rti', irq),
            ('four-invocation-control-and-persistent-ram', lineage),
            ('minimal-missing-source-frontier', missing_frontier()),
            ('independent-static-source-comparison', checked))]
    for control in curated_controls():
        case = control['input']; actual = evaluate_case(case); expected = reference_case(case)
        if canonical(actual) != canonical(expected):
            raise ValueError('IndependentFourInvocationConstraintMismatch:' + control['caseId'])
        records.append({'caseId': control['caseId'], 'classification': STATIC,
            'data': {'input': case, 'result': actual, 'invocationObligations': invocation_obligations(case, actual),
                'independentComparison': 'PASS'}, 'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0})
    return json.loads(json.dumps(records, ensure_ascii=True, allow_nan=False))
