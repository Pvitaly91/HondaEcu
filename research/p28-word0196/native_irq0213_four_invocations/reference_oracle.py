"""Independent finite IRQ/frame and persistent-RAM constraints, never execution.

Expected values come from reviewed manufacturer functions and original source
extents. Four symbolic invocations neither deliver interrupts nor create SRBUF
contents. Actual owners, frames, return PCs and hardware applicability stay unknown.
"""
from copy import deepcopy


STATIC = 'StaticIrq0213FrameObligations_NotCpuExecution'
REASONS = (
    'TxRxSourceConflated', 'Vector000AConfusedWith000E', 'SrbufTreatedAsTransmitRegister',
    'OneSampleReusedFourTimes', 'PendingTreatedAsDelivery', 'MissingFrameCreator',
    'WrongFrameWidthOrOrder', 'RtSubstitutedForRti', 'RtiInstructionAddressUsedAsReturnPC',
    'WrongSspArithmetic', 'CrossInvocationFrameIdentity', 'UnknownNestingIgnored',
    'HandlerScbImportedIntoParser', 'WrongLocalBankMap', 'FabricatedInitialR7',
    'WrongR5R2Progression', 'Length3CannotWriteFlag', 'EvenFlagAccepted', 'IncorrectChecksum',
    'WrongReadyGeneration', 'MissingMode0356Bit1', 'Error0356Bit6Ignored',
    'InventedSrbufReadCompletion', 'Assumed03F3Internal', 'CrossMachineRamTransfer',
    'HostParserPCJump', 'Default011FZero', 'ImportedM2agGeneration', 'FakeNativeOrdinal',
    'CurrentIrqExecutionClaimed', 'HistoricalFingerprintRewritten',
    'UniversalVectorAllocationClaim', 'SourceMaskOwnerSplice', 'MieWindowIgnored',
    'FrameParserBankOverlap', 'FrameIeShadowOverlap', 'HeaderOldR0SaveOmitted',
    'ParityGapContentFreeze', 'RtiSfZeroAssumed',
)
PROFILES = {'UserTable17_1': 'SerialTransmittingReady',
    'InstructionTable1_1': 'SerialReceivingReady'}
READ_SITES = [('H', 0x0277), ('L', 0x027F), ('F', 0x0262), ('K', 0x0284)]
STAGE_REQUIREMENTS = [
    {'r7': 0, 'r5': None, 'r2': None}, {'r7': 2, 'r5': 1, 'r2': None},
    {'r7': 2, 'r5': 2, 'r2': 4}, {'r7': 2, 'r5': 3, 'r2': 4},
]
ACTUAL = {'cpuExecutions': 0, 'romExecutions': 0, 'irqDeliveries': 0, 'rtiExecutions': 0,
    'machineId': None, 'eventOrdinal': None, 'writeOrdinal': None, 'srbufPacketObserved': False,
    'parserExecuted': False, 'branch064FExecuted': False}


def _int(value):
    return type(value) is int


def reviewed_case(case_id='positive-user-f01', profile='UserTable17_1', flag=1,
                  ssp=0x047E, status=2, entry_ie=0x02A0, tail_ie=0x2BAB):
    """One complete invented conditional witness; not a native admission record."""
    frames = []
    for index in range(1, 5):
        identity = f'model:{case_id}:irq{index}'
        frames.append({'id': identity, 'creator': identity + ':entry',
            'rtiConsumer': identity + ':entry', 'incomingSSP': ssp,
            'savedContext': {role: identity + ':saved' + role for role in ('PC', 'A', 'LRB', 'PSW')},
            'returnSource': 'MatchingEntrySavedPC', 'rtInstructionPC': 0x029C,
            'actualCreator': None, 'actualRestoredPC': None})
    values = [0x21, 4, flag, (-(0x21 + 4 + flag)) % 256]
    reads = [{'role': role, 'pc': pc, 'value': values[index],
        'readId': f'model:{case_id}:read{role}', 'invocationId': frames[index]['id'], 'actualValue': None}
        for index, (role, pc) in enumerate(READ_SITES)]
    return {'caseId': case_id, 'classification': 'InventedOnly_ConditionalFourInvocationState',
        'machine': 'model:' + case_id,
        'irq': {'profile': profile, 'cause': PROFILES[profile], 'vector': 0x000A, 'entryPC': 0x0213,
            'allocationConflictAcknowledged': True, 'universalCauseClaim': False,
            'pendingImpliesDelivery': False, 'actualSource': None, 'actualPending': None,
            'actualEnabled': None, 'actualPriority': None},
        'srbuf': {'address': 0x0055, 'name': 'SerialReceivingDataBuffer', 'widthBits': 8,
            'completion': 'Unknown', 'storageSemantics': 'ConditionalNonDestructiveCurrentBufferHypothesis',
            'contentChangesBetweenReads': [True, True, True], 'receiveCompletionCountClaim': None,
            'reads': reads},
        'frames': frames,
        'frameContract': {'byteCount': 8, 'entryRoleOrder': ['PC', 'A', 'LRB', 'PSW'],
            'entrySspDelta': -8, 'rtiSspDelta': 8, 'rtiForm': 'RTI',
            'sfClaim': 'UnknownNotAssignedByPrimaryFunction', 'rtiRestoresIE': False,
            'rtiRestoresPointingRam': False},
        'handler': {'scb': 2, 'lrb': 0x007E, 'localBase': 0x03F0, 'pswLiteral': 0x0102,
            'mieAfter0217': 1, 'mieClearedAt': 0x0297, 'entryIeSource': 0x00FA,
            'tailIeSource': 0x00F8, 'entryIeWord': entry_ie, 'tailIeWord': tail_ie,
            'entryIeOwner': 'model:FA-owner', 'tailIeOwner': 'model:F8-owner',
            'sameMaskOwnerAssumed': False, 'nestingIgnored': False},
        'initialRam': {'r0': 0x66, 'r1': 0x77, 'r2': 0x88, 'r3': 0x99, 'r4': 0xAA,
            'r5': 0xBB, 'r6': 0xCC, 'r7': 0, 'status0356': status},
        'stateSources': {'r7': 'ConditionalStartupWord2710FromClr2706',
            'mode': 'Conditional60D5SourceBitOwner', 'sourceMachine': 'model:' + case_id,
            'retainedMachine': 'model:' + case_id, 'actualR7Owner': None, 'actualModeOwner': None},
        'stageRequirements': deepcopy(STAGE_REQUIREMENTS),
        'effects': {'readyWriterPC': 0x0290, 'headerSavesOldR1ToR0': True,
            'deduplicateSameValueWrites': False},
        'preservation': {'domain': 'ExplicitDisjointAndNoUnaccountedWritesHypothesis',
            'unknownNestedEventsIgnored': False, 'foregroundOverwriteIgnored': False,
            'mapping03F3': 'UnknownActualChip_201External_207Internal',
            'importedHistoricalGeneration': None, 'historicalExpected': 'model:old-sha',
            'recordedExpected': 'model:old-sha'},
        'foreground': {'parserPC': 0x28AE, 'scb': 0, 'lrb': 0x0041, 'usp': 0x0180,
            'hostPCJump': None, 'default011FZero': False,
            'noPrematureParserConsumptionHypothesis': True},
        'actual': deepcopy(ACTUAL)}


def curated_controls():
    positives = (
        ('positive-user-f01', 'UserTable17_1', 1, 0x047E, 2, 0x02A0, 0x2BAB),
        ('positive-isa-f81', 'InstructionTable1_1', 129, 0x047E, 0x82, 0x02A0, 0x2BAB),
        ('positive-user-fdb-oddssp', 'UserTable17_1', 219, 0x047F, 2, 0x00A0, 0xA9A3),
        ('positive-isa-fff', 'InstructionTable1_1', 255, 0x0490, 0x0A, 0x02A0, 0x2BAB),
        ('positive-user-f03', 'UserTable17_1', 3, 0x04A0, 0x12, 0x00A0, 0xA9A3),
    )
    cases = [{'caseId': args[0], 'input': reviewed_case(*args)} for args in positives]
    for index, reason in enumerate(REASONS):
        cid = 'negative-' + reason
        c = reviewed_case(cid)
        if index == 0:
            c['irq']['cause'] = 'SerialReceivingReady'
        elif index == 1:
            c['irq']['vector'] = 0x000E
        elif index == 2:
            c['srbuf']['name'] = 'SerialTransmittingDataBuffer'
        elif index == 3:
            c['srbuf']['reads'][1]['readId'] = c['srbuf']['reads'][0]['readId']
        elif index == 4:
            c['irq']['pendingImpliesDelivery'] = True
        elif index == 5:
            c['frames'][0]['creator'] = None
        elif index == 6:
            c['frameContract']['byteCount'] = 2
        elif index == 7:
            c['frameContract']['rtiForm'] = 'RT'
        elif index == 8:
            c['frames'][0]['returnSource'] = 'RtiInstructionAddress'
        elif index == 9:
            c['frameContract']['entrySspDelta'] = -6
        elif index == 10:
            c['frames'][1]['rtiConsumer'] = c['frames'][0]['creator']
        elif index == 11:
            c['preservation']['unknownNestedEventsIgnored'] = True
        elif index == 12:
            c['foreground']['scb'] = 2
        elif index == 13:
            c['handler']['localBase'] = 0x0100
        elif index == 14:
            c['stateSources']['r7'] = 'HostSeedNative'
        elif index == 15:
            c['stageRequirements'][1]['r5'] = 2
        elif index in (16, 17):
            c['srbuf']['reads'][1 if index == 16 else 2]['value'] = 3 if index == 16 else 2
            values = [row['value'] for row in c['srbuf']['reads']]
            c['srbuf']['reads'][3]['value'] = (-sum(values[:3])) % 256
        elif index == 18:
            c['srbuf']['reads'][3]['value'] ^= 1
        elif index == 19:
            c['effects']['readyWriterPC'] = 0x0293
        elif index == 20:
            c['initialRam']['status0356'] &= ~2
        elif index == 21:
            c['initialRam']['status0356'] |= 0x40
        elif index == 22:
            c['srbuf']['completion'] = 'ObservedNativeComplete'
        elif index == 23:
            c['preservation']['mapping03F3'] = 'AlwaysInternal'
        elif index == 24:
            c['stateSources']['retainedMachine'] = 'model:other-machine'
        elif index == 25:
            c['foreground']['hostPCJump'] = 0x28AE
        elif index == 26:
            c['foreground']['default011FZero'] = True
        elif index == 27:
            c['preservation']['importedHistoricalGeneration'] = 'M2ag_fixedSource'
        elif index == 28:
            c['actual']['writeOrdinal'] = 1
        elif index == 29:
            c['actual']['irqDeliveries'] = 4
        elif index == 30:
            c['preservation']['recordedExpected'] = 'model:changed-sha'
        elif index == 31:
            c['irq']['universalCauseClaim'] = True
        elif index == 32:
            c['handler']['sameMaskOwnerAssumed'] = True
        elif index == 33:
            c['handler']['mieAfter0217'] = 0
        elif index == 34:
            c['frames'][0]['incomingSSP'] = 0x03F6
        elif index == 35:
            c['frames'][0]['incomingSSP'] = 0x00FA
        elif index == 36:
            c['effects']['headerSavesOldR1ToR0'] = False
        elif index == 37:
            c['srbuf']['contentChangesBetweenReads'] = [False, False, False]
        elif index == 38:
            c['frameContract']['sfClaim'] = 'ClearedTo0ByRTI'
        cases.append({'caseId': cid, 'input': c})
    return cases


def _shape(c):
    if type(c) is not dict:
        return False
    required = reviewed_case()
    groups = ('irq', 'srbuf', 'frameContract', 'handler', 'initialRam',
        'stateSources', 'effects', 'preservation', 'foreground', 'actual')
    if not required.keys() <= c.keys() or any(type(c[key]) is not dict
            or not required[key].keys() <= c[key].keys() for key in groups):
        return False
    if type(c['frames']) is not list or len(c['frames']) != 4:
        return False
    for frame in c['frames']:
        if (type(frame) is not dict or not required['frames'][0].keys() <= frame.keys()
                or type(frame['savedContext']) is not dict
                or set(frame['savedContext']) != {'PC', 'A', 'LRB', 'PSW'}):
            return False
    reads = c['srbuf']['reads']
    return (type(reads) is list and len(reads) == 4
        and all(type(row) is dict and required['srbuf']['reads'][0].keys() <= row.keys()
            and _int(row['value']) and 0 <= row['value'] <= 255 for row in reads)
        and all(_int(value) and 0 <= value <= 255 for value in c['initialRam'].values()))


def _footprint(ssp):
    if not _int(ssp) or not 0 <= ssp <= 0xFFFF:
        return None
    return {((ssp - offset) & 0xFFFE) + byte for offset in (0, 2, 4, 6) for byte in (0, 1)}


def _reason(c):
    if not _shape(c):
        return 'ClosedCaseShapeRequired'
    q, s, f, h, ram, owners, p, fg = (c[key] for key in
        ('irq', 'srbuf', 'frameContract', 'handler', 'initialRam', 'stateSources', 'preservation', 'foreground'))
    frames, reads = c['frames'], s['reads']
    footprints = [_footprint(row['incomingSSP']) for row in frames]
    values = [row['value'] for row in reads]
    actual = c['actual']
    conditions = (
        q['profile'] not in PROFILES or q['cause'] != PROFILES.get(q['profile']),
        q['vector'] != 0x000A or q['entryPC'] != 0x0213,
        s['address'] != 0x0055 or s['name'] != 'SerialReceivingDataBuffer' or s['widthBits'] != 8,
        len({row['readId'] for row in reads}) != 4,
        q['pendingImpliesDelivery'] is not False,
        any(not isinstance(row['creator'], str) or not row['creator'].startswith('model:') for row in frames),
        f['byteCount'] != 8 or f['entryRoleOrder'] != ['PC', 'A', 'LRB', 'PSW'],
        f['rtiForm'] != 'RTI',
        any(row['returnSource'] != 'MatchingEntrySavedPC' or row['rtInstructionPC'] != 0x029C for row in frames),
        f['entrySspDelta'] != -8 or f['rtiSspDelta'] != 8,
        len({row['id'] for row in frames}) != 4 or any(row['creator'] != row['id'] + ':entry'
            or row['rtiConsumer'] != row['creator'] for row in frames),
        p['unknownNestedEventsIgnored'] is not False,
        fg['scb'] != 0,
        h['scb'] != 2 or h['lrb'] != 0x007E or h['localBase'] != 0x03F0,
        ram['r7'] != 0 or owners['r7'] != 'ConditionalStartupWord2710FromClr2706',
        c['stageRequirements'] != STAGE_REQUIREMENTS,
        values[1] != 4,
        not values[2] & 1,
        sum(values) % 256 != 0 or values[0] != 0x21,
        c['effects']['readyWriterPC'] != 0x0290,
        not ram['status0356'] & 2 or owners['mode'] != 'Conditional60D5SourceBitOwner',
        bool(ram['status0356'] & 0x40),
        s['completion'] != 'Unknown' or s['receiveCompletionCountClaim'] is not None
            or any(row['actualValue'] is not None for row in reads),
        p['mapping03F3'] != 'UnknownActualChip_201External_207Internal',
        owners['sourceMachine'] != c['machine'] or owners['retainedMachine'] != c['machine'],
        fg['hostPCJump'] is not None,
        fg['default011FZero'] is not False,
        p['importedHistoricalGeneration'] is not None,
        any(actual[key] is not None for key in ('machineId', 'eventOrdinal', 'writeOrdinal'))
            or any(row['actualCreator'] is not None or row['actualRestoredPC'] is not None for row in frames)
            or owners['actualR7Owner'] is not None or owners['actualModeOwner'] is not None,
        not _equal(actual, ACTUAL) or any(q[key] is not None for key in
            ('actualSource', 'actualPending', 'actualEnabled', 'actualPriority')),
        p['historicalExpected'] != p['recordedExpected'],
        q['allocationConflictAcknowledged'] is not True or q['universalCauseClaim'] is not False,
        h['sameMaskOwnerAssumed'] is not False or h['entryIeOwner'] == h['tailIeOwner'],
        h['pswLiteral'] != 0x0102 or h['mieAfter0217'] != 1 or h['mieClearedAt'] != 0x0297
            or h['nestingIgnored'] is not False,
        any(fp is not None and bool(fp & set(range(0x03F0, 0x03F8))) for fp in footprints),
        any(fp is not None and bool(fp & set(range(0x00F8, 0x00FC))) for fp in footprints),
        c['effects']['headerSavesOldR1ToR0'] is not True,
        s['storageSemantics'] != 'ConditionalNonDestructiveCurrentBufferHypothesis'
            or s['contentChangesBetweenReads'] != [True, True, True],
        f['sfClaim'] != 'UnknownNotAssignedByPrimaryFunction',
    )
    for name, failed in zip(REASONS, conditions):
        if failed:
            return name
    if any(fp is None for fp in footprints):
        return 'UnknownSspCannotBeDeclaredSafe'
    forbidden = set(range(0x00C0)) | {0x0356}
    if any(fp & forbidden for fp in footprints):
        return 'FrameSfrOrPointingRamOverlap'
    if f['rtiRestoresIE'] is not False:
        return 'RtiDoesNotRestoreIE'
    if f['rtiRestoresPointingRam'] is not False:
        return 'RtiDoesNotRestorePointingRam'
    if fg['noPrematureParserConsumptionHypothesis'] is not True:
        return 'PrematureParserConsumption'
    if (fg['parserPC'], fg['lrb'], fg['usp']) != (0x28AE, 0x0041, 0x0180):
        return 'WrongParserContext'
    if ([(row['role'], row['pc']) for row in reads] != READ_SITES
            or [row['invocationId'] for row in reads] != [row['id'] for row in frames]):
        return 'WrongReadSiteOrInvocation'
    if (c['classification'] != 'InventedOnly_ConditionalFourInvocationState'
            or p['domain'] != 'ExplicitDisjointAndNoUnaccountedWritesHypothesis'
            or p['foregroundOverwriteIgnored'] is not False
            or c['effects']['deduplicateSameValueWrites'] is not False
            or (h['entryIeSource'], h['tailIeSource']) != (0x00FA, 0x00F8)
            or (h['entryIeWord'], h['tailIeWord']) not in ((0x02A0, 0x2BAB), (0x00A0, 0xA9A3))):
        return 'ClosedCaseShapeRequired'
    return None


def _empty(case_id, reason):
    return {'caseId': case_id, 'valid': reason is None,
        'classification': 'InventedOnly_Refused' if reason else 'InventedOnly_ConditionalFourInvocationRelations',
        'firstMismatch': reason,
        'firstMissingObligation': reason or 'ActualSourceProfileAndFourIRQFrameAndReadHistories',
        'sourceProfile': None, 'conditionalCause': None, 'allocationConflictPreserved': True,
        'modeledFrames': [], 'modeledStages': [], 'persistentWriteCount': 0,
        'readyGeneration': None, 'maskBit1Entry': None, 'maskBit1Tail': None, 'mieWindow': None,
        'bufferParities': [], 'conditionalContentChangeGaps': [], 'parserRequirements': None,
        'preservation': None, 'actual': deepcopy(ACTUAL), 'runtimeAdmission': 'Blocked', 'firmwareReady': False}


def reference_case(c):
    """Finite source equations only; no target fetch, register or peripheral model."""
    reason = _reason(c)
    result = _empty(c.get('caseId') if type(c) is dict else None, reason)
    if reason:
        return result
    frames = []
    for row in c['frames']:
        ssp = row['incomingSSP']
        slots = [{'role': role, 'wordAddress': (ssp - offset) & 0xFFFE,
            'byteAddresses': [(ssp - offset) & 0xFFFE, ((ssp - offset) & 0xFFFE) + 1],
            'savedSource': row['savedContext'][role]}
            for role, offset in (('PC', 0), ('A', 2), ('LRB', 4), ('PSW', 6))]
        reads = [{'step': step, 'role': slot['role'], 'wordAddress': slot['wordAddress'],
            'savedSource': slot['savedSource']} for step, slot in enumerate(reversed(slots), 1)]
        frames.append({'invocationId': row['id'], 'creator': row['creator'], 'sspBefore': ssp,
            'sspAfterEntry': (ssp - 8) & 0xFFFF, 'sspAfterRti': ssp, 'entryWordSlots': slots,
            'rtiWordReads': reads, 'restoredContext': deepcopy(row['savedContext']),
            'rtInstructionPC': 0x029C, 'actualRestoredPC': None})
    ram = deepcopy(c['initialRam'])
    stages = []
    for index, read in enumerate(c['srbuf']['reads'], 1):
        before = deepcopy(ram)
        writes = []

        def store(pc, address, value, semantic):
            key = 'status0356' if address == 0x0356 else 'r' + str(address - 0x03F0)
            ram[key] = value
            writes.append({'pc': pc, 'address': address, 'widthBits': 8, 'value': value,
                'storageGeneration': f'model:{c["caseId"]}:i{index}:w{len(writes) + 1}',
                'semanticSource': semantic})

        store(0x0222, 0x0356, ram['status0356'] & ~0x40, 'RetainedNeighborOwners')
        value = read['value']
        source = 'DistinctRead:' + read['readId']
        zf, cf = None, None
        if read['role'] == 'H':
            store(0x0275, 0x03F0, ram['r1'], 'OldR1BeforeHeader')
            store(0x0279, 0x03F1, value, source)
            store(0x027A, 0x03F6, value, source)
            store(0x027B, 0x03F5, 1, 'CodeConstant')
            store(0x0270, 0x03F7, 2, 'CodeConstant')
        elif read['role'] in ('L', 'F'):
            store(0x0281 if read['role'] == 'L' else 0x0269,
                0x03F2 if read['role'] == 'L' else 0x03F3, value, source)
            store(0x026D, 0x03F6, (ram['r6'] + value) % 256, 'NativeWidth8Arithmetic')
            store(0x026F, 0x03F5, (ram['r5'] + 1) % 256, 'NativeWidth8Arithmetic')
            store(0x0270, 0x03F7, 2, 'CodeConstant')
        else:
            checksum = ram['r6'] + value
            zf, cf = int(checksum % 256 == 0), int(checksum >= 256)
            store(0x0290, 0x0356, ram['status0356'] | 0x80, 'SB0290')
            store(0x0293, 0x03F7, 0, 'CodeConstant')
        stages.append({'role': read['role'], 'invocationId': read['invocationId'],
            'readId': read['readId'], 'readPC': read['pc'], 'modeledReadValue': value,
            'ramBefore': before, 'ramAfter': deepcopy(ram), 'orderedPersistentWrites': writes,
            'checksumZF': zf, 'checksumCF': cf})
    result.update(sourceProfile=c['irq']['profile'], conditionalCause=PROFILES[c['irq']['profile']],
        modeledFrames=frames, modeledStages=stages, persistentWriteCount=sum(len(row['orderedPersistentWrites']) for row in stages),
        readyGeneration=f'model:{c["caseId"]}:i4:w2', maskBit1Entry=(c['handler']['entryIeWord'] >> 1) & 1,
        maskBit1Tail=(c['handler']['tailIeWord'] >> 1) & 1,
        mieWindow={'setPC': 0x0217, 'clearPC': 0x0297, 'entryIEOwner': 'Source00FA',
            'tailIEOwner': 'Source00F8', 'nestedSafety': 'ExplicitNoUnaccountedInterferenceHypothesis_NotObservation'},
        bufferParities=[row['value'] & 1 for row in c['srbuf']['reads']],
        conditionalContentChangeGaps=[True, True, True],
        parserRequirements={'entryPC': 0x28AE, 'scb': 0, 'lrb': 0x0041, 'usp': 0x0180,
            'command': 0x21, 'flagBit0': 1, 'modeBit1': 1, 'readyBit7': 1, 'actualReached': False},
        preservation='ConditionalDisjointAndNoUnaccountedWritesOnly')
    return result


def _at(value, path):
    try:
        for key in path:
            value = value[key]
        return value
    except (KeyError, TypeError, IndexError):
        return {'missingPath': list(path)}


def _equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_equal(left[key], right[key]) for key in left)
    if type(left) in (list, tuple):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    return left == right


def independent_check(irq, lineage):
    """Literal primary/source projections fixed before reading new model output."""
    irq_expected = (
        (('classification',), STATIC), (('sourceProfiles', 'actualSource'), None),
        (('sourceProfiles', 'actualSourceClassification'), 'SourceAllocationConflictOrRevisionApplicabilityUnknown'),
        (('sourceProfiles', 'selectedConditionalProfile'), 'UserTable17_1_TxReady'),
        (('frameContract', 'entryRoleOffsets'), [['PC', 0], ['A', -2], ['LRB', -4], ['PSW', -6]]),
        (('frameContract', 'wordCount'), 4), (('frameContract', 'byteCount'), 8),
        (('frameContract', 'physicalByteWriteOrder'), None), (('frameContract', 'physicalByteReadOrder'), None),
        (('rtiContract', 'instructionPC'), 0x029C),
        (('rtiContract', 'order'), ['PSW', 'LRB', 'A', 'PC']),
        (('rtiContract', 'perWordOperation'), 'IncrementSSPBy2_ThenReadAlignedWord'),
        (('rtiContract', 'totalSspIncrement'), 8),
        (('rtiContract', 'instructionPCIsRestoredReturnPC'), False),
        (('rtiContract', 'restoredForegroundPC'), None),
        (('rtiContract', 'sfAssignmentInRTIFunction'), None),
        (('rtiContract', 'ordinaryRtSf0MayBeImported'), False),
        (('handlerMaskControls', 'entryMaskSourceWord'), 0x00FA),
        (('handlerMaskControls', 'tailMaskSourceWord'), 0x00F8),
        (('handlerMaskControls', 'conditionalHandlerSCB'), 2),
        (('handlerMaskControls', 'conditionalMIEAfterLiteral'), 1),
        (('actualNative', 'actualCpuExecutions'), 0),
        (('actualNative', 'actualOriginalRomExecutions'), 0),
        (('actualNative', 'actualIRQDeliveries'), 0),
        (('actualNative', 'actualRetiredInstructions'), 0),
        (('actualNative', 'actualMachineId'), None),
        (('actualNative', 'actualNativeInstructionIndex'), None),
        (('actualNative', 'actualAllNativeWriteOrdinal'), None),
        (('actualNative', 'actualFrameCreator'), None),
        (('actualNative', 'actualSourceOwnersEstablished'), False),
        (('actualNative', 'actualParser28AEExecuted'), False),
        (('runtimeAdmission',), 'Blocked'), (('firmwareReady',), False),
    )
    lineage_expected = (
        (('actualIrqSource',), None), (('handlerContext', 'scb'), 2),
        (('handlerContext', 'lrb'), 0x007E), (('handlerContext', 'page'), 0x0300),
        (('handlerContext', 'localBytes'), list(range(0x03F0, 0x03F8))),
        (('maskAndMieChronology', 'entrySourceWord'), 0x00FA),
        (('maskAndMieChronology', 'entryReadPC'), 0x0213),
        (('maskAndMieChronology', 'entryIEWriterPC'), 0x0215),
        (('maskAndMieChronology', 'mieLiteralWriterPC'), 0x0217),
        (('maskAndMieChronology', 'conditionalMIE'), 1),
        (('maskAndMieChronology', 'tailSourceWord'), 0x00F8),
        (('maskAndMieChronology', 'tailReadPC'), 0x0295),
        (('maskAndMieChronology', 'mieClearPC'), 0x0297),
        (('maskAndMieChronology', 'tailIEWriterPC'), 0x029A),
        (('maskAndMieChronology', 'conditionalKnownPairsBodyBit1'), 0),
        (('maskAndMieChronology', 'conditionalKnownPairsTailBit1'), 1),
        (('readyRetention', 'readyWriterPC'), 0x0290),
        (('readyRetention', 'H_L_FDoNotClearReadyBit7'), True),
        (('readyRetention', 'actualInitialReadyOwner'), None),
        (('readyRetention', 'actualNoEarlyConsumerProof'), None),
        (('rtiAndForeground', 'instructionPC'), 0x029C),
        (('rtiAndForeground', 'restorationOrder'), ['PSW', 'LRB', 'A', 'PC']),
        (('rtiAndForeground', 'parserSCB'), 0), (('rtiAndForeground', 'parserLRB'), 0x0041),
        (('rtiAndForeground', 'parserUSP'), 0x0180),
        (('rtiAndForeground', 'handlerContextMayBeImported'), False),
        (('actualCpuExecutions',), 0), (('actualOriginalRomExecutions',), 0),
        (('actualIRQDeliveries',), 0), (('actualRetiredInstructions',), 0),
        (('actualMachineId',), None), (('actualNativeInstructionIndex',), None),
        (('actualAllNativeWriteOrdinal',), None),
        (('runtimeAdmission',), 'Blocked'), (('firmwareReady',), False),
    )
    mismatches = []
    for prefix, document, expected in (('irq', irq, irq_expected), ('lineage', lineage, lineage_expected)):
        for path, value in expected:
            actual = _at(document, path)
            if not _equal(actual, value):
                mismatches.append({'field': prefix + '.' + '.'.join(path), 'expected': value, 'actual': actual})
    invocations = lineage.get('invocations', [])
    projection = [(row.get('srbufReadPC'), row.get('rtiInstructionPC'), row.get('incomingSSP'),
        row.get('actualFrameCreator'), row.get('actualSourceOwner'), row.get('actualStorageGeneration')) for row in invocations]
    expected_projection = [(pc, 0x029C, None, None, None, None) for _, pc in READ_SITES]
    if not _equal(projection, expected_projection):
        mismatches.append({'field': 'lineage.invocations.read-rti-unknowns', 'expected': expected_projection, 'actual': projection})
    expected_writers = [
        [(0x0222, 0x0356), (0x0275, 0x03F0), (0x0279, 0x03F1), (0x027A, 0x03F6), (0x027B, 0x03F5), (0x0270, 0x03F7)],
        [(0x0222, 0x0356), (0x0281, 0x03F2), (0x026D, 0x03F6), (0x026F, 0x03F5), (0x0270, 0x03F7)],
        [(0x0222, 0x0356), (0x0269, 0x03F3), (0x026D, 0x03F6), (0x026F, 0x03F5), (0x0270, 0x03F7)],
        [(0x0222, 0x0356), (0x0290, 0x0356), (0x0293, 0x03F7)],
    ]
    local_targets = set(range(0x03F0, 0x03F8)) | {0x0356}
    actual_writers = [[(effect.get('pc'), effect.get('address'))
        for effect in row.get('orderedDataAndContextEffects', [])
        if effect.get('address') in local_targets] for row in invocations]
    if not _equal(actual_writers, expected_writers):
        mismatches.append({'field': 'lineage.invocations.selected-persistent-write-order',
            'expected': expected_writers, 'actual': actual_writers})
    return {'valid': not mismatches, 'firstMismatch': mismatches[0] if mismatches else None,
        'mismatches': mismatches, 'comparedFactCount': len(irq_expected) + len(lineage_expected) + 2,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualIRQDeliveries': 0,
        'runtimeAdmission': 'Blocked', 'firmwareReady': False}
