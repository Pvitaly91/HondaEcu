"""Closed invented frame relations, separate from native machine observations.

Geometry does not grant an applicable writable memory map. Control-register
aliases are checked before applying ordinary stack arithmetic to architecture.
Raw helper footprints are independently source-reviewed static facts, not a
CPU journal. The reference oracle implements its own arithmetic and overlap.
"""
from copy import deepcopy

CONDITIONS = ('reached24ED', 'source24F8', 'exchange2531_2533',
    'exchange254D_254F', 'ram2689', 'ram268D', 'cal276A', 'cal2777', 'context27BC')
EARLIER_CALLS = frozenset(('ram2689', 'ram268D', 'cal276A', 'cal2777'))


def require(value, reason):
    if value is not True:
        raise ValueError(reason)


def uint(value, limit=65535):
    return type(value) is int and 0 <= value <= limit


def model_id(value):
    return type(value) is str and value.startswith('model:') and 6 < len(value) <= 160


def validate(case):
    require(type(case) is dict and set(case) == {'caseId', 'classification', 'machineId',
        'incomingSSP', 'source', 'context', 'call', 'helper', 'events', 'consumer'}, 'ClosedInventedFrameCaseRequired')
    require(case['classification'] == 'InventedOnly_FrameSpecification'
        and type(case['caseId']) is str and 0 < len(case['caseId']) <= 128
        and model_id(case['machineId']), 'NoNativeRuntimeCaseOrMachineImport')
    s = case['incomingSSP']
    require(s is None or uint(s), 'UnknownOrUnsigned16SspRequired')
    source = case['source']
    require(type(source) is dict and set(source) == {'kind', 'ownerId', 'conditions'}, 'ClosedSourceRequired')
    require(source['kind'] in ('Conditional24F8', 'InventedHostOnly', 'Unknown'), 'ClosedSspSourceKindsRequired')
    require(source['ownerId'] is None if source['kind'] == 'Unknown' else model_id(source['ownerId']),
        'NoInventedOwnerPromotionToNative')
    require(source['kind'] != 'Conditional24F8' or s == 0x047E, 'Literal24F8CannotSupplyDifferentSsp')
    require(type(source['conditions']) is dict and set(source['conditions']) == set(CONDITIONS)
        and all(v is None or type(v) is bool for v in source['conditions'].values()), 'ExplicitConditionalSourceHistoryRequired')
    ctx = case['context']
    require(type(ctx) is dict and set(ctx) == {'page', 'local', 'usp', 'scb', 'accumulatorMode', 'mapping', 'asyncHistory'},
        'ClosedProducerContextRequired')
    require(all(type(ctx[k]) is int and ctx[k] == v for k, v in (('page', 0x0200), ('local', 0x0208), ('usp', 0x0180))),
        'ProducerContextCannotBorrowReceiverState')
    require(ctx['scb'] is None or uint(ctx['scb'], 7), 'UnknownOrThreeBitScbRequired')
    if source['kind'] == 'Conditional24F8' and all(source['conditions'][key] is True for key in CONDITIONS):
        require(type(ctx['scb']) is int and ctx['scb'] == 0, 'CompleteColdSourceRequiresOwnedScb0')
    require(ctx['accumulatorMode'] in ('ExplicitOrdinaryInvented', 'Unknown')
        and ctx['mapping'] in ('InventedWritableRetainedData', 'UnknownAsic')
        and ctx['asyncHistory'] in ('ExplicitNoAsyncHypothesis', 'Unknown'), 'ExplicitInventedApplicabilityRequired')
    call = case['call']
    require(type(call) is dict and set(call) == {'pc', 'length', 'target', 'returnPc', 'creator'}
        and all(type(call[k]) is int and call[k] == v for k, v in (
            ('pc', 0x27D0), ('length', 3), ('target', 0x5F45), ('returnPc', 0x27D3)))
        and model_id(call['creator']) and call['creator'] != 'model:' + case['caseId'] + ':RT60E4',
        'ExactCAL27D0FormAndModelCreatorRequired')
    helper = case['helper']
    require(type(helper) is dict and set(helper) == {'normalReturn', 'finalA', 'programBit'}
        and helper['normalReturn'] in ('AssumedReviewedPredicates', 'UnknownPredicate', 'Interrupted')
        and type(helper['finalA']) is int and helper['finalA'] in (0x0500, 0x0700)
        and uint(helper['programBit'], 1), 'ClosedConditionalHelperRequired')
    events = case['events']
    require(type(events) is list and len(events) <= 8, 'BoundedModelWritesRequired')
    ids = {call['creator'], 'model:' + case['caseId'] + ':RT60E4'}
    for event in events:
        require(type(event) is dict and set(event) == {'eventId', 'machine', 'kind', 'pc', 'address', 'widthBytes', 'value'},
            'ClosedModelEventRequired')
        require(model_id(event['eventId']) and event['eventId'] not in ids, 'UniqueModelEventRequired')
        ids.add(event['eventId'])
        require(event['machine'] == case['machineId'], 'CrossMachineFrameImportRefused')
        require(event['kind'] in ('Write', 'SameValueWrite', 'HostReseed', 'UnknownIndirect', 'NestedIrq')
            and uint(event['pc']) and type(event['widthBytes']) is int and event['widthBytes'] in (1, 2), 'TypedModelWriteRequired')
        require(event['address'] is None or uint(event['address']), 'UnknownAddressIsNotZero')
        require(event['value'] is None or uint(event['value'], 256 ** event['widthBytes'] - 1), 'WidthBoundedModelValueRequired')
        require(event['kind'] not in ('Write', 'SameValueWrite') or event['address'] is not None and event['value'] is not None,
            'ConcreteInventedWritesNeedConcreteValues')
    read = case['consumer']
    require(type(read) is dict and set(read) == {'pc', 'form', 'creator', 'machine'}
        and type(read['pc']) is int and read['pc'] == 0x60E4 and read['form'] == 'RT'
        and model_id(read['creator']) and read['machine'] == case['machineId'], 'MatchingOrdinaryRTScopeRequired')


def geometry(s):
    require(uint(s), 'Unsigned16SspRequired')
    frame = s & 0xFFFE
    after = (s - 2) & 0xFFFF
    return {'incomingSSP': s, 'frameAddress': frame, 'frameWidth': 16,
        'returnWord': 0x27D0 + 3, 'frameBytes': [0xD3, 0x27],
        'arithmeticSspAfterCAL': after, 'arithmeticSspAfterRT': (after + 2) & 0xFFFF,
        'arithmeticRtReadAddress': ((after + 2) & 0xFFFF) & 0xFFFE}


def footprint(address, width):
    if address is None:
        return None
    base = address & 0xFFFE if width == 2 else address
    return frozenset((base + offset) & 0xFFFF for offset in range(width))


def evaluate(case, inventory=None):
    validate(case)
    if inventory is None:
        from native_cal27d0_frame.helper_frame import reviewed_write_inventory
        inventory = reviewed_write_inventory()
    require(type(inventory) is list, 'ReviewedInventoryRequired')
    s, ctx, source, helper = (case[k] for k in ('incomingSSP', 'context', 'source', 'helper'))
    f = None if s is None else s & 0xFFFE
    frame = footprint(f, 2)
    banks = list(range(8)) if ctx['scb'] is None else [ctx['scb']]
    must, may, matching = [], [], {}
    for row in inventory:
        require(type(row) is dict and {'pc', 'widthBytes', 'mustBeforeNormalRt', 'addressesByScb', 'effect', 'valueSource'} <= set(row),
            'CompleteReviewedWriteRowRequired')
        require(uint(row['pc']) and type(row['widthBytes']) is int and row['widthBytes'] in (1, 2)
            and type(row['mustBeforeNormalRt']) is bool and type(row['addressesByScb']) is list
            and len(row['addressesByScb']) == 8 and all(uint(a) for a in row['addressesByScb']), 'TypedReviewedFootprintRequired')
        if frame is None:
            continue
        overlaps = [bool(frame & footprint(row['addressesByScb'][bank], row['widthBytes'])) for bank in banks]
        if any(overlaps):
            address = next(row['addressesByScb'][bank] for bank, overlap in zip(banks, overlaps) if overlap)
            category = must if row['mustBeforeNormalRt'] and all(overlaps) else may
            category.append(row['pc'])
            matching.setdefault(row['pc'], (address, row['widthBytes']))
    must, may = sorted(set(must)), sorted(set(may) - set(must))
    absent = next((key for key in CONDITIONS if source['conditions'][key] is not True), None)
    if source['kind'] == 'Conditional24F8':
        source_class = ('SspCodeOwnedUnderExplicitConditions' if absent is None else
            'ReturnPathBlockedByEarlierCaller' if absent in EARLIER_CALLS else 'IncomingSspNotEstablished')
    else:
        source_class = 'InventedSsp_NotNativeOwner' if source['kind'] == 'InventedHostOnly' else 'IncomingSspNotEstablished'
    out = {'classification': 'MatchingRTConditional', 'sourcePC': 0x24F8 if source['kind'] == 'Conditional24F8' else None,
        'sourceClassification': source_class, 'incomingSSP': s, 'incomingSspOwner': source['ownerId'],
        'callerPC': 0x27D0, 'calleeEntryPC': 0x5F45, 'requiredReturnPC': 0x27D3,
        'frameAddress': f, 'frameWidth': 16, 'frameBytes': [0xD3, 0x27],
        'sspAfterCAL': None if s is None else (s - 2) & 0xFFFF,
        'frameCreator': case['call']['creator'], 'candidateOverwritePC': None,
        'writeAddress': None, 'writeWidth': None, 'writeValue': None, 'mustOrMayWrite': None,
        'aliasClassification': 'ProvedDisjointWithinReviewedSoftwareContext',
        'frameGenerationStatus': 'CALFrameGenerationRetainedConditionally',
        'rtConsumerPC': 0x60E4, 'rtReadAddress': None, 'sspAfterRT': None, 'conditionalReturnedPC': None,
        'callerContextRequirements': {**deepcopy(ctx), 'scope': 'ExplicitInventedConditions_NotNativeContext'},
        'firstMissingObligation': None, 'nativeFirstMissingObligation': 'ActualCAL27D0FrameAndRT60E4ReadNotObserved',
        'mustOverlapPCs': must, 'mayOverlapPCs': may, 'modelEvents': [],
        'producerBitEffects': {'scope': 'ConditionalHelperEffect_NotExecuted',
            'programSource': 'InventedProgramBit_NotOriginalByte', 'programBit': helper['programBit'],
            'producerPC': 0x5F6B, 'sourceAddress': 0x0217, 'bitIndex': 3,
            'conditionalBitAfter5F6B': helper['programBit'], 'conditionalBitAfter6039': helper['programBit'],
            'selectedSemanticCreator': 'model:' + case['caseId'] + ':5F6B',
            'producerStorageGeneration': 'model:' + case['caseId'] + ':5F6B:byte',
            'laterStorageGeneration': 'model:' + case['caseId'] + ':6039:byte',
            'laterRmwPC': 0x6039, 'wholeByteValue': None,
            'ahRule': 'RetainedByCLRB_LCB_SLLB_ThenLateWordLoadsReplaceA',
            'actualNativeInstructionIndex': None, 'actualNativeWriteOrdinal': None},
        'sourceBufferEffect': {0x0216: 'CALChanges0216_0217_SourceOwnerThenHelperRmwReplacesGeneration',
            0x011E: 'CALChanges011E_011F_TargetOwnership_NotFutureCopyProof',
            0x0212: 'CALChanges0212_0213_NeighborBufferOwnership',
            0x011A: 'CALChanges011A_011B_SourceOwnership_Not011BReaderOwner'}.get(f, 'NoSelectedBufferCollision'),
        'registerEffects': {'calWritesA': f == 6, 'aAfterCal': 0x27D3 if f == 6 else None,
            'firstClrbA': 0x2700 if f == 6 else None, 'conditionalFinalA': helper['finalA'],
            'sspControlAlias': f == 0, 'lrbControlAlias': f == 2, 'pswControlAlias': f == 4,
            'physicalSf': 'UnresolvedPrimaryApplicability', 'flagsRetainedByCALForm': True,
            'flagsRetainedInPresenceOfPswFrameAlias': f != 4},
        'helperTermination': {'normalReturn': helper['normalReturn'], 'actualObserved': False, 'pathCountsAreRetirements': False},
        'actualNativeInstructionIndex': None, 'actualLogicalWriteOrdinal': None,
        'actualRawByteWriteOrdinals': None, 'actualAllNativeWriteOrdinal': None,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
        'runtimeAdmissionGranted': False, 'firmwareReady': False}
    out['modelEvents'].append({'eventId': case['call']['creator'], 'kind': 'CAL', 'pc': 0x27D0,
        'address': f, 'widthBytes': 2, 'value': 0x27D3, 'generationRole': 'CALCreator'})
    injected, control_writes = [], []
    for event in case['events']:
        touched = footprint(event['address'], event['widthBytes'])
        overlap = frame is not None and touched is not None and bool(frame & touched)
        role = ('ForbiddenHostReseed' if event['kind'] == 'HostReseed' else
            'UnknownWrite' if frame is None or touched is None or event['kind'] in ('UnknownIndirect', 'NestedIrq') else
            'OverlappingFreshGeneration' if overlap else 'NonOverlappingWrite')
        effective = None if event['address'] is None else event['address'] & 0xFFFE if event['widthBytes'] == 2 else event['address']
        out['modelEvents'].append({'eventId': event['eventId'], 'kind': event['kind'], 'pc': event['pc'],
            'address': effective, 'widthBytes': event['widthBytes'], 'value': event['value'], 'generationRole': role})
        if overlap and event['kind'] in ('Write', 'SameValueWrite'):
            injected.append(event)
        if touched is not None and event['kind'] in ('Write', 'SameValueWrite'):
            for address, name in ((0, 'SSP'), (2, 'LRB'), (4, 'PSW')):
                if touched & footprint(address, 2):
                    control_writes.append((event, name))
                    break
    def block(classification, missing, alias=None, generation=None):
        out.update(classification=classification, firstMissingObligation=missing)
        if alias is not None:
            out['aliasClassification'] = alias
        if generation is not None:
            out['frameGenerationStatus'] = generation
    if s is None:
        block('IncomingSspNotEstablished', 'IncomingSSPAndOwner', 'UnresolvedAlias', 'IncomingSspNotEstablished')
    elif f in (0, 2, 4):
        block('FrameMayBeClobbered', 'CALControlAlias:' + {0: 'SSP', 2: 'LRB', 4: 'PSW'}[f],
            'ArchitecturalControlAlias', 'ContextAliasAtCAL')
        if f == 0:
            out['sspAfterCAL'] = None
    elif f == 6 or must:
        block('FrameDefinitelyClobbered', 'MandatoryHelperFrameOverwrite',
            'AccumulatorAlias' if f == 6 else 'MustOverlap', 'ReplacedByHelperWrite')
        pc = 0x5F45 if f == 6 else 0x60E3 if f == 0x0382 else must[0]
        address, width = matching[pc]
        out.update(candidateOverwritePC=pc, writeAddress=address, writeWidth=width * 8,
            writeValue=0 if f == 6 else helper['finalA'] if f == 0x0382 else None, mustOrMayWrite='MustWrite')
    elif may:
        block('FrameMayBeClobbered', 'ConditionalHelperFrameOverwrite', 'MayOverlap', 'MayBeReplaced')
        address, width = matching[may[0]]
        out.update(candidateOverwritePC=may[0], writeAddress=address, writeWidth=width * 8, mustOrMayWrite='MayWrite')
    elif injected:
        block('FrameDefinitelyClobbered', 'ModelEventFrameOverwrite', 'ModelEventOverlap', 'ReplacedByModelEvent')
        event = injected[0]
        effective = event['address'] & 0xFFFE if event['widthBytes'] == 2 else event['address']
        out.update(candidateOverwritePC=event['pc'], writeAddress=effective,
            writeWidth=event['widthBytes'] * 8, writeValue=event['value'], mustOrMayWrite='MustWrite')
    elif any(event['kind'] == 'HostReseed' for event in case['events']):
        block('FrameMayBeClobbered', 'HostReseedAfterCALForbidden')
    elif control_writes:
        event, role = control_writes[0]
        block('FrameMayBeClobbered', 'ModelControlRegisterWrite:' + role, 'UnresolvedAlias', 'MayBeReplaced')
        effective = event['address'] & 0xFFFE if event['widthBytes'] == 2 else event['address']
        out.update(candidateOverwritePC=event['pc'], writeAddress=effective,
            writeWidth=event['widthBytes'] * 8, writeValue=event['value'], mustOrMayWrite='MustWrite')
    elif ctx['asyncHistory'] == 'Unknown' or any(event['kind'] in ('UnknownIndirect', 'NestedIrq') for event in case['events']):
        block('FrameIntegrityConditionalOnUnknownAliases', 'UnaccountedIndirectOrAsynchronousWrite', 'UnresolvedAlias', 'MayBeReplaced')
    elif helper['normalReturn'] != 'AssumedReviewedPredicates':
        block('MatchingRTConditional', 'InterruptedHelper' if helper['normalReturn'] == 'Interrupted' else 'UnprovedHelperReturnPredicates')
    elif source['kind'] == 'Conditional24F8' and absent is not None:
        block(source_class, 'SourceCondition:' + absent)
    elif source['kind'] == 'Unknown':
        block('IncomingSspNotEstablished', 'IncomingSspOwner')
    elif ctx['accumulatorMode'] == 'Unknown':
        block('FrameIntegrityConditionalOnUnknownAliases', 'AccumulatorStackMode', 'UnresolvedAlias', 'MayBeReplaced')
    elif case['consumer']['creator'] != case['call']['creator']:
        block('MatchingRTConditional', 'WrongFrameCreator')
    elif ctx['mapping'] == 'UnknownAsic':
        block('FrameDisjointWithinReviewedSoftwareDomain', 'ApplicableAsicWritableRetainedFrameMemory')
    intact = out['frameGenerationStatus'] == 'CALFrameGenerationRetainedConditionally'
    ready = intact and helper['normalReturn'] == 'AssumedReviewedPredicates' and case['consumer']['creator'] == case['call']['creator']
    if ready:
        out['sspAfterRT'], out['rtReadAddress'] = s, f
        if out['firstMissingObligation'] in (None, 'ApplicableAsicWritableRetainedFrameMemory'):
            out['conditionalReturnedPC'] = 0x27D3
            out['modelEvents'].append({'eventId': 'model:' + case['caseId'] + ':RT60E4', 'kind': 'RT',
                'pc': 0x60E4, 'address': f, 'widthBytes': 2, 'value': 0x27D3, 'generationRole': 'ConditionalRTConsumer'})
    return out
