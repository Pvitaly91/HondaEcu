"""Independent source-effect algebra; no new implementation/model imports.

Accepted M2co independent helpers provide only inherited source transformations.
The new byte store, selection, closed-form counter proof and longer conditional
handoffs are separately authored from the source/interface obligations.
"""
from copy import deepcopy
import re

from length_checksum_dataflow.reference_oracle import (
    _Reference, _checked, _header, _length, _checksum, _select, canonical,
)
from .corpus import RETAINED, ROLES, cases

COMMON = ('ActualEcuEquivalenceNotEstablished', 'NativeReentryEdgeNotEstablished',
          'PhysicalSFNotEstablished', 'PeripheralReceiveLifecycleNotEstablished')
EDGES = frozenset((('Header', 'Length'), ('Length', 'Flag'), ('Length', 'Checksum'),
    ('Flag', 'Checksum'), ('Flag', 'Generic'), ('Generic', 'Generic'),
    ('Generic', 'Checksum'), ('Generic', 'Length')))
LABEL = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')


def _constraints(*items):
    return list(dict.fromkeys((*COMMON, *items)))


def _qualified(result):
    result = deepcopy(result)
    result['unresolvedConstraints'] = _constraints(*([] if result['status'] == 'CompleteConditional' else [result['reason']]))
    return result


def _join(r, outcome):
    before = r.read(0x026D, 0x03F6)[0]
    after = r.add_values(before, r.registers['al'])
    r.write(0x026D, 0x03F6, [after], 'RMW', 'DATA03F6+AL')
    r.step(0x026D, 0x026F)
    counter = r.read(0x026F, 0x03F5)[0]
    next_counter = None if counter is None else (counter + 1) % 256
    r.registers.update(zf=None if next_counter is None else int(next_counter == 0),
                       hc=None if counter is None else int(counter % 16 == 15))
    r.write(0x026F, 0x03F5, [next_counter], 'RMW', 'DATA03F5+1')
    r.step(0x026F, 0x0270)
    r.write(0x0270, 0x03F7, [2], 'ImmediateStore', 'Literal')
    r.step(0x0270, 0x0272)
    return r.result(0x0272, outcome)


def _generic(r):
    if r.registers['dd'] != 0:
        return r.outside(0x026C, 'ByteStoreDdContextNotEstablished')
    r.write(0x026C, 0x03F4, [r.registers['al']], 'Store', 'AL')
    r.step(0x026C, 0x026D)
    return _join(r, 'GenericWritten')


def _data(r, required_role=None):
    failure = r.byte_load(0x0262, 0x0055, 0x0264)
    if failure is not None:
        return failure
    counter = r.read(0x0264, 0x03F5)[0]
    r.compare_byte(counter, 2)
    r.step(0x0264, 0x0267)
    generic = None if counter is None else counter != 2
    failure = r.branch(0x0267, generic, 0x026C, 0x0269)
    if failure is not None:
        return failure
    selected = 'Generic' if generic else 'Flag'
    if required_role is not None and required_role != selected:
        return r.outside(0x026C if generic else 0x0269, 'DeclaredRoleDoesNotMatchDataSelection')
    if generic:
        return _generic(r)
    r.write(0x0269, 0x03F3, [r.registers['al']], 'Store', 'AL')
    r.step(0x0269, 0x026A)
    r.step(0x026A, 0x026D, 'Jump', True)
    return _join(r, 'FlagWritten')


def generic_payload_body(snapshot):
    r = _Reference(snapshot, 'generic_payload_body')
    failure = r.admission(0x026C, flag=True)
    return _qualified(failure if failure is not None else _generic(r))


def data_body(snapshot):
    r = _Reference(snapshot, 'data_body')
    failure = r.admission(0x0262, flag=True)
    return _qualified(failure if failure is not None else _data(r))


def dispatch(snapshot):
    r = _Reference(snapshot, 'dispatch')
    failure = r.admission(0x0255, flag=True)
    result = failure if failure is not None else _select(r)
    if result['outcome'] == 'FlagSelected':
        result['outcome'] = 'DataSelected'
    return _qualified(result)


def parser_step(snapshot, stage_id=None, required_role=None):
    name = 'parser_step' if stage_id is None else 'parser_step@' + stage_id
    r = _Reference(snapshot, name)
    failure = r.admission(0x021F, flag=True)
    if failure is not None:
        return _qualified(failure)
    r.read(0x021F, 0x0356)
    mode = r.bit(0x0356, 1)
    failure = r.branch(0x021F, None if mode is None else mode == 0, 0x029D, 0x0222, outside=True)
    if failure is not None:
        return _qualified(failure)
    old_error = r.rmw(0x0222, 0x0356, 6, 0)
    r.step(0x0222, 0x0225)
    failure = r.branch(0x0225, None if old_error is None else old_error == 0, 0x0255, 0x0227)
    if failure is not None:
        return _qualified(failure)
    if old_error != 0:
        return _qualified(r.outside(0x0227, 'UnmodeledBranch'))
    selected = _select(r)
    if selected['status'] != 'CompleteConditional':
        return _qualified(selected)
    role = selected['outcome'].removesuffix('Selected')
    data = role == 'Flag'
    allowed = required_role in ('Flag', 'Generic') if data else required_role == role
    if required_role is not None and not allowed:
        return _qualified(r.outside(selected['boundary'], 'DeclaredRoleDoesNotMatchDispatch'))
    result = _data(r, required_role) if data else {'Header': _header, 'Length': _length, 'Checksum': _checksum}[role](r)
    return _qualified(result)


def counter_route(request):
    if type(request) is not dict or set(request) != {'length', 'maxDataStages'}:
        raise ValueError('ReferenceCounterShape')
    length, bound = request['length'], request['maxDataStages']
    if (length is not None and (type(length) is not int or not 0 <= length <= 255)
            or type(bound) is not int or not 0 <= bound <= 512):
        raise ValueError('ReferenceCounterTypes')
    # First-frontier distance is independently derived, not an emulated loop.
    distance = None if length is None else 255 if length == 2 else (length - 3) % 256
    count = 0 if distance is None else min(distance, bound)
    history = [{'ordinal': index + 1, 'counterBefore': (2 + index) % 256,
                'counterAfter': (3 + index) % 256, 'role': 'Flag' if index == 0 else 'Generic'}
               for index in range(count)]
    order = ['Header', 'Length'] + [row['role'] for row in history]
    counter = (2 + count) % 256
    if length is None:
        status, reason, outcome, pc, reachable = ('IndeterminateBranch', 'UnknownLengthPredicate',
            'IndeterminateLength', 0x0260, None)
        constraints = _constraints(reason)
    elif count < distance:
        status, reason, outcome, pc, reachable = ('OutsideVerifiedScope',
            'SyntheticResourceBound_NotProtocolLimit', 'SyntheticResourceBoundReached', 0x0262, None)
        constraints = _constraints(reason)
    elif length == 2:
        status, reason, outcome, pc, reachable = ('CompleteConditional',
            'VerifiedCounterPriorityRelation', 'LengthReentrySelected', 0x027F, False)
        constraints = _constraints('FixedLengthCompletionBlockedByLengthPriority')
    else:
        status, reason, outcome, pc, reachable = ('CompleteConditional',
            'VerifiedCounterPriorityRelation', 'ChecksumSelected', 0x0284, True)
        order.append('Checksum')
        constraints = _constraints()
    return {'procedure': 'counter_route', 'status': status, 'reason': reason, 'outcome': outcome,
        'length': length, 'maxDataStages': bound, 'initialCounter': 2, 'r7': 2,
        'counterHistory': history, 'stageOrder': order, 'dataStageCount': count,
        'flagStageCount': int(count > 0), 'genericStageCount': max(count - 1, 0),
        'totalStageCount': len(order), 'checksumReachable': reachable,
        'boundary': {'counter': counter, 'sourcePC': pc}, 'reads': [], 'journal': [],
        'unresolvedConstraints': constraints,
        'effectClass': 'ConditionalCounterLengthRelation_NotInstructionExecution',
        'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
        'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}


def _label(value):
    return type(value) is str and LABEL.fullmatch(value) is not None


def _request(request):
    if type(request) is not dict or set(request) != {'stages', 'transfers'}:
        raise ValueError('ReferenceCompositionShape')
    stages, transfers = request['stages'], request['transfers']
    if type(stages) is not list or not 1 <= len(stages) <= 512 or type(transfers) is not list or len(transfers) != len(stages) - 1:
        raise ValueError('ReferenceCompositionCardinality')
    checked, ids, samples = [], set(), set()
    for stage in stages:
        if type(stage) is not dict or set(stage) != {'id', 'role', 'sampleId', 'snapshot'}:
            raise ValueError('ReferenceStageShape')
        if (not _label(stage['id']) or not _label(stage['sampleId']) or type(stage['role']) is not str
                or stage['role'] not in ROLES or stage['id'] in ids or stage['sampleId'] in samples):
            raise ValueError('ReferenceStageIdentity')
        ids.add(stage['id'])
        samples.add(stage['sampleId'])
        checked.append({**stage, 'snapshot': _checked(stage['snapshot'])})
    for transfer in transfers:
        if type(transfer) is not dict or set(transfer) != {'from', 'to', 'relation', 'noInterference', 'retainedGenerations'}:
            raise ValueError('ReferenceTransferShape')
        if (not _label(transfer['from']) or not _label(transfer['to'])
                or type(transfer['relation']) is not str or not transfer['relation']
                or transfer['noInterference'] is not None and type(transfer['noInterference']) is not bool):
            raise ValueError('ReferenceTransferTypes')
        generations = transfer['retainedGenerations']
        if (type(generations) is not dict or set(generations) != set(RETAINED)
                or any(value is not None and (type(value) is not str or not value) for value in generations.values())):
            raise ValueError('ReferenceGenerationMap')
    return checked, deepcopy(transfers)


def compose(request):
    stages, declarations = _request(request)
    evaluated, transfers, rejected, journal, inputs = [], [], [], [], []
    boundaries, branches, unresolved = [], [], list(COMMON)
    initial = stages[0]['snapshot']
    state = {key: deepcopy(initial[key]) for key in ('memory', 'knownBits', 'registers', 'generations')}

    def result(status, reason, stage_id, pc):
        outcome = evaluated[-1]['output']['outcome'] if evaluated else None
        checksum = outcome if outcome in ('ChecksumAccepted', 'ChecksumRejected') else None
        constraints = list(dict.fromkeys(unresolved + ([] if status == 'CompleteConditional' else [reason])
            + ([] if checksum is not None else ['ChecksumNotReachedWithinRequestedSequence'])))
        return {'procedure': 'compose', 'status': status, 'reason': reason,
            'boundary': {'stageId': stage_id, 'sourcePC': pc}, 'stages': deepcopy(evaluated),
            'transfers': deepcopy(transfers), 'journal': deepcopy(journal), 'boundaryInputs': deepcopy(inputs),
            'finalState': deepcopy(state), 'effectClass': 'ConditionalDataflowTransfer_NotNativeExecution',
            'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False,
            'rejectedTransfers': deepcopy(rejected), 'stageBoundaries': deepcopy(boundaries),
            'branchDecisions': deepcopy(branches), 'checksumOutcome': checksum,
            'unresolvedConstraints': constraints}

    if stages[0]['role'] != 'Header':
        return result('OutsideVerifiedScope', 'CompositionRequiresHeaderOrigin', stages[0]['id'], None)
    prefixes = ['ConditionalEffect:parser_step@' + stage['id'] + ':' for stage in stages]
    if any(value is not None and any(value.startswith(prefix) for prefix in prefixes)
           for value in initial['generations'].values()):
        return result('OutsideVerifiedScope', 'GenerationNamespaceCollision', stages[0]['id'], None)
    for index, stage in enumerate(stages):
        supplied = stage['snapshot']
        if index:
            transfer = declarations[index - 1]
            failure = None
            if (transfer['from'] != stages[index - 1]['id'] or transfer['to'] != stage['id']
                    or transfer['relation'] != 'ConditionalPersistentStateHandoff'
                    or (stages[index - 1]['role'], stage['role']) not in EDGES):
                failure = 'MissingVerifiedInterBlockRelation'
            elif transfer['noInterference'] is not True:
                failure = 'NoInterferencePremiseNotEstablished'
            elif transfer['retainedGenerations'] != {key: state['generations'][key] for key in RETAINED}:
                failure = 'WriterLineageNotEstablished'
            else:
                def persistent(value, field):
                    return ({key: bit for key, bit in value[field].items() if key[:4] != '0055'}
                            if field == 'knownBits' else {key: value[field][key] for key in RETAINED})
                if any(persistent(supplied, field) != persistent(state, field)
                       for field in ('memory', 'generations', 'knownBits')):
                    failure = 'PersistentStateOverwritten'
                elif (supplied['inputClass'] != stages[index - 1]['snapshot']['inputClass']
                        or supplied['assumptions'] != stages[index - 1]['snapshot']['assumptions']
                        or supplied['registers']['lrb'] != state['registers']['lrb']):
                    failure = 'IncompatibleHandoffContext'
            if failure is not None:
                rejected.append({'transfer': transfer, 'reason': failure,
                                 'classification': 'RefusedConditionalHandoff_NotRuntimeEvent'})
                return result('OutsideVerifiedScope', failure, stage['id'], None)
            transfers.append({**transfer, 'classification': 'ConditionalPersistentStateHandoff_NotCfgOrNativeContinuity'})
        inputs.append({'stageId': stage['id'], 'sampleId': stage['sampleId'], 'address': 85, 'widthBits': 8,
            'value': supplied['memory']['0055'], 'generation': supplied['generations']['0055'],
            'classification': 'ExplicitSymbolicBoundaryInput_NotPeripheralObservation'})
        local = parser_step(supplied, stage_id=stage['id'], required_role=stage['role'])
        evaluated.append({'id': stage['id'], 'role': stage['role'], 'sampleId': stage['sampleId'], 'output': local})
        state = deepcopy(local['state'])
        unresolved = list(dict.fromkeys(unresolved + local['unresolvedConstraints']))
        boundaries.append({'stageId': stage['id'], 'sourcePC': local['boundary'],
                           'status': local['status'], 'outcome': local['outcome']})
        branches.extend({'stageId': stage['id'], 'pc': step['pc'], 'next': step['next'],
                         'branchTaken': step['branchTaken']} for step in local['steps'] if step['kind'] == 'Branch')
        for event in local['journal']:
            journal.append({'stageId': stage['id'], 'globalOrdinal': len(journal) + 1, 'event': deepcopy(event)})
        if local['status'] != 'CompleteConditional':
            return result(local['status'], local['reason'], stage['id'], local['boundary'])
    return result('CompleteConditional', 'AllRequestedConditionalTransformationsEstablished', stages[-1]['id'], evaluated[-1]['output']['boundary'])


OPERATIONS = {'generic_payload_body': generic_payload_body, 'data_body': data_body,
              'dispatch': dispatch, 'parser_step': parser_step,
              'counter_route': counter_route, 'compose': compose}


def expected_records():
    for case in cases():
        yield {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
               'output': OPERATIONS[case['operation']](case['input'])}


def canonical_bytes():
    return b''.join(canonical(record) for record in expected_records())
