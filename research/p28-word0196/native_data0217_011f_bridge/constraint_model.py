"""Invented relational timeline solver, never a CPU or native execution trace.

The three producer effects are exact conditional architectural relationships.
Other helper instructions are represented by separately verified CFG and return
obligations, not by host reconstruction of a whole helper register trace.
Selected-bit semantic provenance and byte storage generations are independent.
"""
from copy import deepcopy

INVENTED = 'InventedOnly_StaticBridge'
STATIC = 'StaticSameMachineBridgeFeasibility_NotCpuExecution'
CALLERS = (0x27D0, 0x4069)
ROOTS = (0x0379, 0x03ED)
EVENT_FIELDS = {
    'call': {'pc', 'returnPc', 'frameWord'},
    'producer': {'pc', 'programAddress', 'sourceSpace', 'sourceBit', 'shift', 'dd', 'page', 'hostCf'},
    'retainedRmw': {'pc', 'bit', 'value'},
    'return': {'pc', 'returnPc', 'frameCallerPc', 'frameOrdinal'},
    'external': {'receiver', 'evidence', 'actualDelivery'},
    'copy': {'loadPc', 'writerPc', 'sourceWord', 'targetWord', 'width', 'endian', 'accumulatorMutated'},
    'reader': {'pc', 'address', 'bit', 'actualRead'},
    'overwriteBuffer': {'pc', 'address', 'bitValue'},
    'overwriteTarget': {'pc', 'address', 'bitValue'},
    'unknownAlias': {'target'}, 'overlapFrame': {'address', 'value'},
}


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def integer(value, limit=65535):
    return type(value) is int and 0 <= value <= limit


def validate(case):
    need(type(case) is dict and set(case) == {'caseId', 'machineId', 'classification', 'callerPc', 'copyRoot',
        'programByte', 'previousProgramByte', 'sourceIdentity', 'incoming', 'context', 'hypotheses', 'events'}, 'ClosedInventedCaseRequired')
    need(case['classification'] == INVENTED and type(case['caseId']) is str and 0 < len(case['caseId']) <= 128,
        'InventedScopeRequired')
    need(type(case['machineId']) is str and case['machineId'].startswith('invented:') and len(case['machineId']) <= 128,
        'NoHistoricalMachineImport')
    need(type(case['callerPc']) is int and case['callerPc'] in CALLERS
        and type(case['copyRoot']) is int and case['copyRoot'] in ROOTS, 'ClosedCallerAndReceiverRequired')
    need(integer(case['programByte'], 255) and integer(case['previousProgramByte'], 255), 'InventedProgramBytesRequired')
    need(case['sourceIdentity'] is None or type(case['sourceIdentity']) is str
        and case['sourceIdentity'].startswith('invented:') and len(case['sourceIdentity']) <= 128, 'NoPrivateOriginalProgramFixture')
    state = case['incoming']
    need(type(state) is dict and set(state) == {'ah', 'hc', 'otherPsw', 'dd', 'ssp', 'bufferByte', 'targetByte'}, 'ClosedInventedIncomingState')
    need(integer(state['ah'], 255) and integer(state['hc'], 1) and integer(state['dd'], 1)
        and integer(state['otherPsw']) and integer(state['ssp'], 65534) and state['ssp'] % 2 == 0,
        'TypedInventedArchitectureRequired')
    need(all(state[key] is None or integer(state[key], 255) for key in ('bufferByte', 'targetByte')), 'UnknownNeighborsRemainUnknown')
    ctx = case['context']
    need(type(ctx) is dict and set(ctx) == {'producerPage', 'copyLrb', 'copyUsp', 'copyScb', 'sourceHistory',
        'context012A', 'earlierCalls', 'old012ABit3'}, 'ClosedAddressAndHistoryContextRequired')
    need(all(type(ctx[key]) is int and ctx[key] == value for key, value in (
        ('producerPage', 0x0200), ('copyLrb', 0x0021), ('copyUsp', 0x0280), ('copyScb', 2))), 'ExactAddressContextRequired')
    need(all(type(ctx[key]) is str and 0 < len(ctx[key]) <= 128 for key in ('sourceHistory', 'context012A')),
        'ExplicitHistoryIdentityRequired')
    need(type(ctx['earlierCalls']) is list and len(ctx['earlierCalls']) <= 2
        and all(type(pc) is int and pc in (0x0611, 0x0635) for pc in ctx['earlierCalls'])
        and integer(ctx['old012ABit3'], 1), 'BoundedEarlierCallerContextRequired')
    hypotheses = case['hypotheses']
    need(type(hypotheses) is dict and set(hypotheses) == {'helperPredicatesSatisfied', 'aliasesDisjoint',
        'irqFrameAssumedSafe', 'receiverPredicatesSatisfied'}, 'ClosedExplicitHypothesesRequired')
    need(hypotheses['helperPredicatesSatisfied'] is None or type(hypotheses['helperPredicatesSatisfied']) is bool,
        'UnknownHelperPredicatesMustRemainUnknown')
    need(all(type(hypotheses[key]) is bool for key in ('aliasesDisjoint', 'irqFrameAssumedSafe', 'receiverPredicatesSatisfied')),
        'TypedConditionalHypothesesRequired')
    need(type(case['events']) is list and 1 <= len(case['events']) <= 20, 'BoundedTimelineRequired')
    for index, event in enumerate(case['events']):
        need(type(event) is dict and event.get('kind') in EVENT_FIELDS
            and set(event) == EVENT_FIELDS[event['kind']] | {'kind', 'machine', 'ordinal'}, 'ClosedRelationalEventRequired')
        need(event['machine'] == case['machineId'], 'CrossMachineGenerationImportRefused')
        need(type(event['ordinal']) is int and event['ordinal'] == index + 1, 'FabricatedSymbolicOrdinalRefused')
        kind = event['kind']
        if kind == 'call':
            need(type(event['pc']) is int and event['pc'] == case['callerPc']
                and event['returnPc'] == event['frameWord'] == case['callerPc'] + 3
                and type(event['frameWord']) is int, 'CalculatedCallerFrameRequired')
        elif kind == 'producer':
            need(event['pc'] == 0x5F6B and event['programAddress'] == 0x60EC and event['sourceSpace'] == 'PROGRAM'
                and event['sourceBit'] == 7 and event['shift'] == 'SLLB A' and event['dd'] == 0
                and event['page'] == 0x0200 and event['hostCf'] is None
                and all(type(event[k]) is int for k in ('pc', 'programAddress', 'sourceBit', 'dd', 'page')),
                'ExactProgramShiftCarryAndMbRelationshipRequired')
        elif kind == 'retainedRmw':
            need(event['pc'] == 0x6039 and event['bit'] == 6 and integer(event['value'], 1), 'ExactRetaining6039RmwRequired')
        elif kind == 'return':
            need(event['pc'] == 0x60E4 and all(integer(event[k]) for k in ('pc', 'returnPc', 'frameCallerPc', 'frameOrdinal')),
                'TypedMatchingReturnObligationRequired')
        elif kind == 'external':
            need(event['receiver'] in ROOTS and event['evidence'] in ('ExplicitAssumptionOnly', 'Missing', 'ListedSoftwareEdge')
                and event['actualDelivery'] is False, 'NoActualOrFabricatedIrqDelivery')
        elif kind == 'copy':
            pair = (0x5C33, 0x5C35) if case['copyRoot'] == 0x0379 else (0x0406, 0x0408)
            need((event['loadPc'], event['writerPc']) == pair and event['sourceWord'] == 0x0216
                and event['targetWord'] == 0x011E and event['width'] == 16 and event['endian'] == 'little'
                and type(event['accumulatorMutated']) is bool
                and all(type(event[k]) is int for k in ('loadPc', 'writerPc', 'sourceWord', 'targetWord', 'width')),
                'ExactReceiverLoadWordCopyAndEndianRequired')
        elif kind == 'reader':
            need(event['pc'] == 0x064C and event['address'] == 0x011F and event['bit'] == 3
                and event['actualRead'] is False, 'OnlyStatic064CSelectedBitPredicateAllowed')
        elif kind in ('overwriteBuffer', 'overwriteTarget'):
            need(integer(event['pc']) and event['address'] == (0x0217 if kind == 'overwriteBuffer' else 0x011F)
                and (event['bitValue'] is None or integer(event['bitValue'], 1)), 'TypedInventedOverwriteRequired')
        elif kind == 'unknownAlias':
            need(event['target'] in ('source', 'target', 'frame', 'all'), 'ClosedAliasScopeRequired')
        else:
            need(integer(event['address'], 65534) and event['address'] % 2 == 0 and integer(event['value']),
                'AlignedInventedFrameOverlapRequired')


def architecture(case):
    state = case['incoming']; previous, byte = case['previousProgramByte'], case['programByte']
    common = {'ah': state['ah'], 'hc': state['hc'], 'dd': 0, 'otherPsw': state['otherPsw']}
    entry = {**common, 'al': 0, 'cf': None, 'zf': 1}
    before = {**common, 'al': previous << 1 & 255, 'cf': previous >> 7, 'zf': int(previous == 0)}
    load = {**before, 'al': byte, 'zf': int(byte == 0)}
    shift = {**load, 'al': byte << 1 & 255, 'cf': byte >> 7}
    return {'entryCLRB': entry, 'beforeLCB': before, 'afterLCB': load,
        'afterShift': shift, 'afterMB': deepcopy(shift)}


def cell(value):
    return {'bitValue': None if value is None else value >> 3 & 1, 'owner': 'OwnerUnknown',
        'token': None, 'semanticOrdinal': None, 'storageOrdinal': None, 'byteValue': value}


def solve(case):
    validate(case)
    source, target = cell(case['incoming']['bufferByte']), cell(case['incoming']['targetByte'])
    frame = {'callPc': case['callerPc'], 'expectedReturnPc': case['callerPc'] + 3,
        'address': case['incoming']['ssp'] & ~1, 'createdOrdinal': None, 'storageOrdinal': None,
        'validReturn': False, 'restoredSsp': None}
    external = {'evidence': None, 'receiver': case['copyRoot'],
        'vector': 0x0026 if case['copyRoot'] == 0x0379 else 0x000E,
        'irqBit': 15 if case['copyRoot'] == 0x0379 else 3, 'actualDelivery': False, 'softwareEdgeEstablished': False}
    violations, trace = set(), []
    counter = 0; live = False; pristine = False; frame_word = None
    producer_seen = False; retained_seen = False; any_retained_seen = False; copy_seen = False; alias_seen = False
    external_count = 0; reader_count = 0; return_count = 0; copy_before_external = False

    def affect_frame(address, value):
        nonlocal pristine, frame_word
        if live and address == frame['address'] + 1:
            pristine = False; frame['storageOrdinal'] = counter
            frame_word = None if value is None or frame_word is None else (frame_word & 255) | value << 8

    def word_effect(address, value):
        for destination, word_address in ((source, 0x0216), (target, 0x011E)):
            if address == word_address:
                destination.update(bitValue=value >> 11 & 1, owner='OwnerUnknown', token=None,
                    semanticOrdinal=None, storageOrdinal=counter, byteValue=value >> 8)

    for event in case['events']:
        kind = event['kind']
        if kind == 'call':
            if frame['createdOrdinal'] is not None:
                violations.add('MultipleCallsInSingleInvocation')
            counter += 1; frame.update(createdOrdinal=event['ordinal'], storageOrdinal=counter,
                validReturn=False, restoredSsp=None)
            live, pristine, frame_word = True, True, event['frameWord']
            word_effect(frame['address'], frame_word)
        elif kind == 'producer':
            if not live:
                violations.add('ProducerOutsideCall')
            if producer_seen:
                violations.add('ProducerRepeatedInAcyclicHelper')
            producer_seen = True; retained_seen = False; counter += 1; bit = case['programByte'] >> 7
            source.update(bitValue=bit, owner='OwnerConditional' if case['sourceIdentity'] is not None else 'OwnerUnknown',
                token=case['sourceIdentity'], semanticOrdinal=counter if case['sourceIdentity'] is not None else None,
                storageOrdinal=counter, byteValue=None if source['byteValue'] is None else (source['byteValue'] & ~8) | bit << 3)
            affect_frame(0x0217, source['byteValue'])
        elif kind == 'retainedRmw':
            if not producer_seen:
                violations.add('6039BeforeProducer')
            if any_retained_seen:
                violations.add('6039RepeatedInAcyclicHelper')
            any_retained_seen = True
            retained_seen = producer_seen; counter += 1
            source['storageOrdinal'] = counter
            if source['byteValue'] is not None:
                source['byteValue'] = (source['byteValue'] & ~64) | event['value'] << 6
            affect_frame(0x0217, source['byteValue'])
        elif kind == 'return':
            return_count += 1
            if return_count > 1:
                violations.add('ReturnRepeatedInSingleInvocation')
            if not producer_seen:
                violations.add('MandatoryProducerBypassed')
            if not retained_seen:
                violations.add('Mandatory6039Bypassed')
            # A mandatory helper store changes this particular frame to0500
            # or0700. Neither is a valid return for either reviewed caller.
            # This is a static contradiction, not an invented CPU write log.
            if frame['address'] in (0x0006, 0x0382):
                violations.add('MandatoryAccumulatorWritesOverwriteReturnFrame'
                    if frame['address'] == 0x0006 else 'MandatoryFinalStoreOverwritesReturnFrame')
                pristine = False; frame_word = None; frame['storageOrdinal'] = None
            valid = (live and pristine and frame_word == frame['expectedReturnPc']
                and event['returnPc'] == frame['expectedReturnPc']
                and event['frameCallerPc'] == case['callerPc'] and event['frameOrdinal'] == frame['createdOrdinal'])
            frame['validReturn'] = bool(valid); frame['restoredSsp'] = case['incoming']['ssp'] if valid else None
            live = False
        elif kind == 'external':
            external_count += 1
            if not frame['validReturn']:
                violations.add('ExternalBeforeMatchingReturn')
            if copy_seen or reader_count:
                violations.add('ExternalAfterCopyOrReader')
            if external_count > 1:
                violations.add('ExternalRepeatedInSingleReceiverInvocation')
            external['evidence'] = event['evidence']
            external['receiver'] = event['receiver']
            if event['receiver'] != case['copyRoot']:
                violations.add('CrossRootExternalSplice')
            if event['evidence'] == 'ListedSoftwareEdge':
                violations.add('IrqSynthesizedFromListedEdge')
        elif kind == 'copy':
            if external_count == 0:
                copy_before_external = True
            if copy_seen:
                violations.add('CopyRepeatedInSingleReceiverInvocation')
            if not producer_seen:
                violations.add('CopyBeforeProducer')
            if not frame['validReturn']:
                violations.add('CopyBeforeMatchingReturn')
            if event['accumulatorMutated']:
                violations.add('CopyAccumulatorMutated')
            counter += 1; target = deepcopy(source); target['storageOrdinal'] = counter; copy_seen = True
            affect_frame(0x011F, target['byteValue'])
        elif kind == 'reader':
            reader_count += 1
            if reader_count > 1:
                violations.add('ReaderRepeatedInSingleReceiverInvocation')
            if not copy_seen:
                violations.add('ReaderBeforeCopy')
        elif kind in ('overwriteBuffer', 'overwriteTarget'):
            counter += 1; destination = source if kind == 'overwriteBuffer' else target
            destination.update(bitValue=event['bitValue'], owner='OwnerUnknown', token=None,
                semanticOrdinal=None, storageOrdinal=counter, byteValue=None)
            affect_frame(event['address'], None)
        elif kind == 'unknownAlias':
            alias_seen = True
            for destination, label, address in ((source, 'source', 0x0217), (target, 'target', 0x011F)):
                if event['target'] in (label, 'all'):
                    destination.update(cell(None))
                    if live and address == frame['address'] + 1:
                        pristine = False; frame_word = None; frame['storageOrdinal'] = None
            if live and event['target'] in ('frame', 'all'):
                pristine = False; frame_word = None; frame['storageOrdinal'] = None
        else:
            counter += 1; word_effect(event['address'], event['value'])
            if live and event['address'] == frame['address']:
                pristine = False; frame_word = event['value']; frame['storageOrdinal'] = counter
        trace.append({'ordinal': event['ordinal'], 'kind': kind,
            'sourceBit': source['bitValue'], 'sourceOwner': source['owner'], 'sourceStorageOrdinal': source['storageOrdinal'],
            'targetBit': target['bitValue'], 'targetOwner': target['owner'], 'targetStorageOrdinal': target['storageOrdinal'],
            'frameLive': live, 'frameStorageOrdinal': frame['storageOrdinal'], 'frameMatch': frame['validReturn']})
    ctx, assumptions = case['context'], case['hypotheses']
    if reader_count == 0:
        violations.add('MissingReaderRelation')
    if external_count > 0 and copy_before_external:
        violations.add('CopyBeforeExternalBoundary')
    if ctx['sourceHistory'] != ctx['context012A']:
        violations.add('Incompatible012AHistory')
    if len(ctx['earlierCalls']) > 1:
        violations.add('MutuallyExclusiveEarlierCallsCombined')
    if ctx['old012ABit3'] != int(bool(ctx['earlierCalls'])):
        violations.add('Wrong012ABit3Context')
    if assumptions['helperPredicatesSatisfied'] is False:
        violations.add('HelperPredicatesContradicted')
    if assumptions['receiverPredicatesSatisfied'] is False:
        violations.add('ReceiverPredicatesContradicted')
    if violations:
        result = 'UnsatisfiableWithinReviewedCFG'
    elif not frame['validReturn'] or not assumptions['irqFrameAssumedSafe']:
        result = 'BlockedByMissingReturnFrame'
    elif assumptions['helperPredicatesSatisfied'] is None:
        result = 'UnknownOutsideReviewedScope'
    elif external['evidence'] != 'ExplicitAssumptionOnly':
        result = 'BlockedByExternalInterruptDelivery'
    elif (not assumptions['aliasesDisjoint'] or alias_seen
            or frame['address'] < 0x00C0 or 0x0200 <= frame['address'] < 0x0300
            or frame['address'] == 0x0356):
        result = 'BlockedByAliasUncertainty'
    elif target['owner'] == 'OwnerUnknown' or target['bitValue'] is None:
        result = 'BlockedBySourceOwner'
    else:
        result = 'SatisfiableUnderExplicitAssumptions'
    return {'caseId': case['caseId'], 'classification': STATIC, 'machineId': case['machineId'],
        'callerPc': case['callerPc'], 'copyRoot': case['copyRoot'], 'registerEffects': architecture(case),
        'frame': frame, 'source': source, 'target': target, 'external': external, 'trace': trace,
        'violations': sorted(violations), 'solverResult': result,
        'selectedBitSemanticLineage': 'SelectedBitSemanticLineageEstablishedUnderExplicitAssumptions'
            if result == 'SatisfiableUnderExplicitAssumptions' else 'ConditionalSelectedBitLineage_NotIntegrated',
        'wholeByteClassification': 'WholeByteValueNotFullyOwned', 'actualByteReadAdmitted': False,
        'nextReader': 0x064F if target['bitValue'] == 0 else None,
        'conditionalStopBefore': (0x0667 if ctx['old012ABit3'] else 0x0664) if target['bitValue'] == 1 else None,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
        'nativeEventIndexes': [], 'nativeWriteOrdinals': [], 'firmwareReady': False}
