"""Independent invented frame arithmetic and lineage reference.

This implementation reads neither the frame model nor its classifications. Its
only shared factual input is the independently reviewed raw write inventory.
Model identities are deliberately unrelated to actual native event ordinals.
"""
from copy import deepcopy


_CONDITIONS = ('reached24ED', 'source24F8', 'exchange2531_2533',
    'exchange254D_254F', 'ram2689', 'ram268D', 'cal276A', 'cal2777', 'context27BC')
_EARLIER_RETURNS = {'ram2689', 'ram268D', 'cal276A', 'cal2777'}
_WRITERS = {'Write', 'SameValueWrite'}
_UNCERTAIN_WRITERS = {'UnknownIndirect', 'NestedIrq'}


def _require(condition, reason):
    if condition is not True:
        raise ValueError(reason)


def _unsigned(value, limit=65535):
    return type(value) is int and 0 <= value <= limit


def _model_id(value):
    return type(value) is str and value.startswith('model:') and 6 < len(value) <= 160


def _object(value, keys, reason):
    _require(type(value) is dict and set(value) == set(keys), reason)


def reference_geometry(incoming_ssp):
    """Pure word geometry, distinct from control-alias architectural effects."""
    _require(_unsigned(incoming_ssp), 'OracleUnsigned16SSPRequired')
    half_word = incoming_ssp // 2
    down = (incoming_ssp + 65534) % 65536
    up = (down + 2) % 65536
    next_pc = 0x27D0 + 3
    return {'incomingSSP': incoming_ssp, 'frameAddress': half_word * 2,
        'frameWidth': 16, 'returnWord': next_pc,
        'frameBytes': [next_pc % 256, next_pc // 256],
        'arithmeticSspAfterCAL': down, 'arithmeticSspAfterRT': up,
        'arithmeticRtReadAddress': (up // 2) * 2}


def _input(case, inventory):
    _object(case, ('caseId', 'classification', 'machineId', 'incomingSSP', 'source',
        'context', 'call', 'helper', 'events', 'consumer'), 'OracleClosedCaseRequired')
    _require(type(case['caseId']) is str and 0 < len(case['caseId']) <= 128, 'OracleCaseIdentityRequired')
    _require(case['classification'] == 'InventedOnly_FrameSpecification', 'OracleInventedScopeRequired')
    _require(_model_id(case['machineId']), 'OracleInventedMachineRequired')
    s = case['incomingSSP']
    _require(s is None or _unsigned(s), 'OracleUnknownOrUnsigned16SSPRequired')
    source = case['source']
    _object(source, ('kind', 'ownerId', 'conditions'), 'OracleClosedSourceRequired')
    _require(source['kind'] in ('Conditional24F8', 'InventedHostOnly', 'Unknown'), 'OracleSourceKindRequired')
    _require(source['ownerId'] is None if source['kind'] == 'Unknown'
        else _model_id(source['ownerId']), 'OracleExplicitSourceOwnerRequired')
    _require(source['kind'] != 'Conditional24F8' or s == 0x047E, 'OracleConditional24F8MustUse047E')
    conditions = source['conditions']
    _object(conditions, _CONDITIONS, 'OracleClosedSourceConditionsRequired')
    _require(all(v is None or type(v) is bool for v in conditions.values()), 'OracleTriStateConditionsRequired')
    context = case['context']
    _object(context, ('page', 'local', 'usp', 'scb', 'accumulatorMode', 'mapping',
        'asyncHistory'), 'OracleClosedContextRequired')
    _require(all(type(context[k]) is int and context[k] == value
        for k, value in (('page', 0x0200), ('local', 0x0208), ('usp', 0x0180))),
        'OracleReviewedProducerAddressingRequired')
    _require(context['scb'] is None or _unsigned(context['scb'], 7), 'OracleUnknownOrThreeBitSCBRequired')
    if source['kind'] == 'Conditional24F8' and all(value is True for value in conditions.values()):
        _require(type(context['scb']) is int and context['scb'] == 0,
            'OracleCompleteColdSourceRequiresItsOwnSCB0')
    _require(context['accumulatorMode'] in ('ExplicitOrdinaryInvented', 'Unknown'), 'OracleAccumulatorModeRequired')
    _require(context['mapping'] in ('InventedWritableRetainedData', 'UnknownAsic'), 'OracleMappingQualificationRequired')
    _require(context['asyncHistory'] in ('ExplicitNoAsyncHypothesis', 'Unknown'), 'OracleAsyncQualificationRequired')
    call = case['call']
    _object(call, ('pc', 'length', 'target', 'returnPc', 'creator'), 'OracleClosedCallRequired')
    _require(all(type(call[k]) is int and call[k] == value for k, value in (
        ('pc', 0x27D0), ('length', 3), ('target', 0x5F45), ('returnPc', 0x27D3))),
        'OracleExactCAL27D0Required')
    _require(_model_id(call['creator']), 'OracleModelCALCreatorRequired')
    reserved_rt_id = 'model:' + case['caseId'] + ':RT60E4'
    _require(call['creator'] != reserved_rt_id, 'OracleDistinctCALAndRTIdentitiesRequired')
    helper = case['helper']
    _object(helper, ('normalReturn', 'finalA', 'programBit'), 'OracleClosedHelperHypothesesRequired')
    _require(helper['normalReturn'] in ('AssumedReviewedPredicates', 'UnknownPredicate', 'Interrupted'),
        'OracleHelperReturnQualificationRequired')
    _require(type(helper['finalA']) is int and helper['finalA'] in (0x0500, 0x0700)
        and _unsigned(helper['programBit'], 1), 'OracleInventedHelperValuesRequired')
    events = case['events']
    _require(type(events) is list and len(events) <= 8, 'OracleBoundedModelEventsRequired')
    ids = {call['creator'], reserved_rt_id}
    for event in events:
        _object(event, ('eventId', 'machine', 'kind', 'pc', 'address', 'widthBytes', 'value'),
            'OracleClosedModelEventRequired')
        _require(_model_id(event['eventId']) and event['eventId'] not in ids, 'OracleUniqueModelEventIdentityRequired')
        ids.add(event['eventId'])
        _require(event['machine'] == case['machineId'], 'OracleCrossMachineEventRefused')
        _require(type(event['kind']) is str and event['kind'] in _WRITERS | _UNCERTAIN_WRITERS | {'HostReseed'}, 'OracleModelEventKindRequired')
        _require(_unsigned(event['pc']) and type(event['widthBytes']) is int
            and event['widthBytes'] in (1, 2), 'OracleTypedWriteFootprintRequired')
        _require(event['address'] is None or _unsigned(event['address']), 'OracleUnknownOrWordAddressRequired')
        _require(event['value'] is None or _unsigned(event['value'], 256 ** event['widthBytes'] - 1),
            'OracleWriteValueFitsWidthRequired')
        if event['kind'] in _WRITERS:
            _require(event['address'] is not None and event['value'] is not None, 'OracleConcreteWriteRequired')
    consumer = case['consumer']
    _object(consumer, ('pc', 'form', 'creator', 'machine'), 'OracleClosedRTConsumerRequired')
    _require(type(consumer['pc']) is int and consumer['pc'] == 0x60E4
        and consumer['form'] == 'RT', 'OracleExactRT60E4Required')
    _require(_model_id(consumer['creator']) and consumer['machine'] == case['machineId'],
        'OracleSameModelMachineConsumerRequired')
    _require(type(inventory) in (list, tuple), 'OracleReviewedRawWriteInventoryRequired')
    required = {'pc', 'widthBytes', 'mustBeforeNormalRt', 'addressesByScb', 'effect', 'valueSource'}
    for row in inventory:
        _require(type(row) is dict and required <= set(row), 'OracleRawWriteFactsRequired')
        _require(_unsigned(row['pc']) and type(row['widthBytes']) is int and row['widthBytes'] in (1, 2)
            and type(row['mustBeforeNormalRt']) is bool, 'OracleTypedRawWriteFactsRequired')
        _require(type(row['addressesByScb']) in (list, tuple) and len(row['addressesByScb']) == 8
            and all(_unsigned(a) for a in row['addressesByScb']), 'OracleEightSCBAddressFactsRequired')
        _require(type(row['effect']) is str and type(row['valueSource']) is str, 'OracleWriteEffectSourceRequired')


def _bytes(address, width):
    if address is None:
        return None
    start = 2 * (address // 2) if width == 2 else address
    return tuple((start + offset) % 65536 for offset in range(width))


def reference_case(case, inventory):
    _input(case, inventory)
    s, source, context = case['incomingSSP'], case['source'], case['context']
    call, helper, consumer = case['call'], case['helper'], case['consumer']
    geo = None if s is None else reference_geometry(s)
    frame = None if geo is None else geo['frameAddress']
    frame_bytes = None if frame is None else set((frame, frame + 1))
    first_condition = next((name for name in _CONDITIONS if source['conditions'][name] is not True), None)
    if source['kind'] == 'Conditional24F8':
        source_class = ('SspCodeOwnedUnderExplicitConditions' if first_condition is None
            else 'ReturnPathBlockedByEarlierCaller' if first_condition in _EARLIER_RETURNS
            else 'IncomingSspNotEstablished')
    elif source['kind'] == 'InventedHostOnly':
        source_class = 'InventedSsp_NotNativeOwner'
    else:
        source_class = 'IncomingSspNotEstablished'
    overlaps = []
    if frame_bytes is not None:
        banks = range(8) if context['scb'] is None else (context['scb'],)
        for row in inventory:
            addresses = [row['addressesByScb'][bank] for bank in banks]
            intersects = [bool(frame_bytes.intersection(_bytes(a, row['widthBytes']))) for a in addresses]
            if any(intersects):
                first_address = next(a for a, hit in zip(addresses, intersects) if hit)
                overlaps.append((row, all(intersects) and row['mustBeforeNormalRt'],
                    2 * (first_address // 2) if row['widthBytes'] == 2 else first_address))
    must = sorted({row['pc'] for row, certain, _ in overlaps if certain})
    may = [pc for pc in sorted({row['pc'] for row, certain, _ in overlaps if not certain}) if pc not in must]
    definite_events, control_events = [], []
    model_events = [{'eventId': call['creator'], 'kind': 'CAL', 'pc': 0x27D0,
        'address': frame, 'widthBytes': 2, 'value': 0x27D3, 'generationRole': 'CALCreator'}]
    for event in case['events']:
        address_bytes = _bytes(event['address'], event['widthBytes'])
        overlap = frame_bytes is not None and address_bytes is not None and bool(frame_bytes.intersection(address_bytes))
        if event['kind'] == 'HostReseed':
            role = 'ForbiddenHostReseed'
        elif event['kind'] in _UNCERTAIN_WRITERS or frame is None:
            role = 'UnknownWrite'
        elif overlap:
            role = 'OverlappingFreshGeneration'
        else:
            role = 'NonOverlappingWrite'
        if event['kind'] in _WRITERS and overlap:
            definite_events.append(event)
        if event['kind'] in _WRITERS and address_bytes is not None:
            for start, register in ((0, 'SSP'), (2, 'LRB'), (4, 'PSW')):
                if set((start, start + 1)).intersection(address_bytes):
                    control_events.append((event, register))
                    break
        projected = {key: deepcopy(event[key]) for key in ('eventId', 'kind', 'pc', 'address', 'widthBytes', 'value')}
        projected['address'] = None if address_bytes is None else address_bytes[0]
        model_events.append(projected | {'generationRole': role})
    classification, missing = 'MatchingRTConditional', None
    alias, generation = 'ProvedDisjointWithinReviewedSoftwareContext', 'CALFrameGenerationRetainedConditionally'
    candidate = write_address = write_width = write_value = write_kind = None
    if frame is None:
        classification, missing = 'IncomingSspNotEstablished', 'IncomingSSPAndOwner'
        alias, generation = 'UnresolvedAlias', 'IncomingSspNotEstablished'
    elif frame in (0, 2, 4):
        register = {0: 'SSP', 2: 'LRB', 4: 'PSW'}[frame]
        classification, missing = 'FrameMayBeClobbered', 'CALControlAlias:' + register
        alias, generation = 'ArchitecturalControlAlias', 'ContextAliasAtCAL'
    elif frame == 6 or must:
        classification, missing = 'FrameDefinitelyClobbered', 'MandatoryHelperFrameOverwrite'
        alias, generation, write_kind = ('AccumulatorAlias' if frame == 6 else 'MustOverlap'), 'ReplacedByHelperWrite', 'MustWrite'
        if frame == 6:
            candidate, write_address, write_width, write_value = 0x5F45, 6, 8, 0
        else:
            chosen, _, address = next(x for x in overlaps if x[1] and x[0]['pc'] == must[0])
            candidate, write_address, write_width = chosen['pc'], address, chosen['widthBytes'] * 8
            if frame == 0x0382:
                write_value = helper['finalA']
    elif may:
        classification, missing = 'FrameMayBeClobbered', 'ConditionalHelperFrameOverwrite'
        alias, generation, write_kind = 'MayOverlap', 'MayBeReplaced', 'MayWrite'
        chosen, _, address = next(x for x in overlaps if not x[1] and x[0]['pc'] == may[0])
        candidate, write_address, write_width = chosen['pc'], address, chosen['widthBytes'] * 8
    elif definite_events:
        event = definite_events[0]
        classification, missing = 'FrameDefinitelyClobbered', 'ModelEventFrameOverwrite'
        alias, generation, write_kind = 'ModelEventOverlap', 'ReplacedByModelEvent', 'MustWrite'
        candidate, write_address, write_width, write_value = (
            event['pc'], _bytes(event['address'], event['widthBytes'])[0], event['widthBytes'] * 8, event['value'])
    elif any(e['kind'] == 'HostReseed' for e in case['events']):
        classification, missing = 'FrameMayBeClobbered', 'HostReseedAfterCALForbidden'
    elif control_events:
        event, register = control_events[0]
        classification, missing = 'FrameMayBeClobbered', 'ModelControlRegisterWrite:' + register
        alias, generation, write_kind = 'UnresolvedAlias', 'MayBeReplaced', 'MustWrite'
        candidate, write_address, write_width, write_value = (
            event['pc'], _bytes(event['address'], event['widthBytes'])[0], event['widthBytes'] * 8, event['value'])
    elif any(e['kind'] in _UNCERTAIN_WRITERS for e in case['events']) or context['asyncHistory'] == 'Unknown':
        classification, missing = 'FrameIntegrityConditionalOnUnknownAliases', 'UnaccountedIndirectOrAsynchronousWrite'
        alias, generation = 'UnresolvedAlias', 'MayBeReplaced'
    elif helper['normalReturn'] != 'AssumedReviewedPredicates':
        classification, missing = 'MatchingRTConditional', ('InterruptedHelper' if helper['normalReturn'] == 'Interrupted'
            else 'UnprovedHelperReturnPredicates')
    elif source['kind'] == 'Conditional24F8' and first_condition is not None:
        classification, missing = source_class, 'SourceCondition:' + first_condition
    elif source['kind'] == 'Unknown':
        classification, missing = 'IncomingSspNotEstablished', 'IncomingSspOwner'
    elif context['accumulatorMode'] == 'Unknown':
        classification, missing = 'FrameIntegrityConditionalOnUnknownAliases', 'AccumulatorStackMode'
        alias, generation = 'UnresolvedAlias', 'MayBeReplaced'
    elif consumer['creator'] != call['creator']:
        classification, missing = 'MatchingRTConditional', 'WrongFrameCreator'
    elif context['mapping'] == 'UnknownAsic':
        classification, missing = 'FrameDisjointWithinReviewedSoftwareDomain', 'ApplicableAsicWritableRetainedFrameMemory'
    after_cal = None if geo is None or frame == 0 else geo['arithmeticSspAfterCAL']
    can_resolve_rt = (geo is not None and generation == 'CALFrameGenerationRetainedConditionally'
        and helper['normalReturn'] == 'AssumedReviewedPredicates' and consumer['creator'] == call['creator'])
    after_rt = geo['arithmeticSspAfterRT'] if can_resolve_rt else None
    rt_address = geo['arithmeticRtReadAddress'] if can_resolve_rt else None
    returned_pc = (0x27D3 if can_resolve_rt and missing in (None, 'ApplicableAsicWritableRetainedFrameMemory') else None)
    if returned_pc is not None:
        model_events.append({'eventId': 'model:' + case['caseId'] + ':RT60E4', 'kind': 'RT',
            'pc': 0x60E4, 'address': rt_address, 'widthBytes': 2, 'value': 0x27D3,
            'generationRole': 'ConditionalRTConsumer'})
    collisions = {
        0x0216: 'CALChanges0216_0217_SourceOwnerThenHelperRmwReplacesGeneration',
        0x011E: 'CALChanges011E_011F_TargetOwnership_NotFutureCopyProof',
        0x0212: 'CALChanges0212_0213_NeighborBufferOwnership',
        0x011A: 'CALChanges011A_011B_SourceOwnership_Not011BReaderOwner',
    }
    return {
        'classification': classification,
        'sourcePC': 0x24F8 if source['kind'] == 'Conditional24F8' else None,
        'sourceClassification': source_class, 'incomingSSP': s, 'incomingSspOwner': source['ownerId'],
        'callerPC': 0x27D0, 'calleeEntryPC': 0x5F45, 'requiredReturnPC': 0x27D3,
        'frameAddress': frame, 'frameWidth': 16, 'frameBytes': [0xD3, 0x27],
        'sspAfterCAL': after_cal, 'frameCreator': call['creator'],
        'candidateOverwritePC': candidate, 'writeAddress': write_address,
        'writeWidth': write_width, 'writeValue': write_value, 'mustOrMayWrite': write_kind,
        'aliasClassification': alias, 'frameGenerationStatus': generation,
        'rtConsumerPC': 0x60E4, 'rtReadAddress': rt_address, 'sspAfterRT': after_rt,
        'conditionalReturnedPC': returned_pc,
        'callerContextRequirements': deepcopy(context) | {'scope': 'ExplicitInventedConditions_NotNativeContext'},
        'firstMissingObligation': missing,
        'nativeFirstMissingObligation': 'ActualCAL27D0FrameAndRT60E4ReadNotObserved',
        'mustOverlapPCs': must, 'mayOverlapPCs': may, 'modelEvents': model_events,
        'sourceBufferEffect': collisions.get(frame, 'NoSelectedBufferCollision'),
        'producerBitEffects': {
            'scope': 'ConditionalHelperEffect_NotExecuted',
            'programSource': 'InventedProgramBit_NotOriginalByte',
            'programBit': helper['programBit'], 'producerPC': 0x5F6B,
            'sourceAddress': 0x0217, 'bitIndex': 3,
            'conditionalBitAfter5F6B': helper['programBit'],
            'conditionalBitAfter6039': helper['programBit'],
            'selectedSemanticCreator': 'model:' + case['caseId'] + ':5F6B',
            'producerStorageGeneration': 'model:' + case['caseId'] + ':5F6B:byte',
            'laterStorageGeneration': 'model:' + case['caseId'] + ':6039:byte',
            'laterRmwPC': 0x6039, 'wholeByteValue': None,
            'ahRule': 'RetainedByCLRB_LCB_SLLB_ThenLateWordLoadsReplaceA',
            'actualNativeInstructionIndex': None, 'actualNativeWriteOrdinal': None,
        },
        'registerEffects': {
            'calWritesA': frame == 6, 'aAfterCal': 0x27D3 if frame == 6 else None,
            'firstClrbA': 0x2700 if frame == 6 else None,
            'conditionalFinalA': helper['finalA'], 'sspControlAlias': frame == 0,
            'lrbControlAlias': frame == 2, 'pswControlAlias': frame == 4,
            'physicalSf': 'UnresolvedPrimaryApplicability', 'flagsRetainedByCALForm': True,
            'flagsRetainedInPresenceOfPswFrameAlias': frame != 4,
        },
        'helperTermination': {'normalReturn': helper['normalReturn'], 'actualObserved': False,
            'pathCountsAreRetirements': False},
        'actualNativeInstructionIndex': None, 'actualLogicalWriteOrdinal': None,
        'actualRawByteWriteOrdinals': None, 'actualAllNativeWriteOrdinal': None,
        'actualCpuExecutions': 0, 'actualOriginalRomExecutions': 0,
        'actualRetiredInstructions': 0, 'runtimeAdmissionGranted': False,
        'firmwareReady': False,
    }
