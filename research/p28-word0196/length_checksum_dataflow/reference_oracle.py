"""Independent structured reference for M2co, without new model imports.

Frozen M2cn reference primitives supply only its accepted snapshot, journal and
Flag arithmetic. New Header/Length/Checksum control and handoffs are authored
from reviewed M2co source contracts. Shared corpus inputs are declared premises.
"""
from copy import deepcopy
import re

from conditional_flag_mode_shadow.reference_oracle import (
    _Reference, _checked, _flag_body, canonical,
)
from .corpus import RETAINED, cases

ROLES = frozenset(('Header', 'Length', 'Flag', 'Checksum'))
EDGES = frozenset((('Header', 'Length'), ('Length', 'Flag'), ('Length', 'Checksum'), ('Flag', 'Checksum')))
LABEL = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')


def _header(r):
    prior = r.read(0x0275, 0x03F1)[0]
    r.write(0x0275, 0x03F0, [prior], 'Store', 'DATA03F1')
    r.step(0x0275, 0x0277)
    failure = r.byte_load(0x0277, 0x0055, 0x0279)
    if failure is not None:
        return failure
    r.write(0x0279, 0x03F1, [r.registers['al']], 'Store', 'AL')
    r.step(0x0279, 0x027A)
    r.write(0x027A, 0x03F6, [r.registers['al']], 'Store', 'AL')
    r.step(0x027A, 0x027B)
    r.write(0x027B, 0x03F5, [1], 'ImmediateStore', 'Literal')
    r.step(0x027B, 0x027D)
    r.step(0x027D, 0x0270, 'Jump', True)
    r.write(0x0270, 0x03F7, [2], 'ImmediateStore', 'Literal')
    r.step(0x0270, 0x0272)
    return r.result(0x0272, 'HeaderWritten')


def _length(r):
    failure = r.byte_load(0x027F, 0x0055, 0x0281)
    if failure is not None:
        return failure
    r.write(0x0281, 0x03F2, [r.registers['al']], 'Store', 'AL')
    r.step(0x0281, 0x0282)
    r.step(0x0282, 0x026D, 'Jump', True)
    prior = r.read(0x026D, 0x03F6)[0]
    value = r.add_values(prior, r.registers['al'])
    r.write(0x026D, 0x03F6, [value], 'RMW', 'DATA03F6+AL')
    r.step(0x026D, 0x026F)
    count = r.read(0x026F, 0x03F5)[0]
    after = None if count is None else (count + 1) % 256
    r.registers.update(zf=None if after is None else int(after == 0),
                       hc=None if count is None else int(count % 16 == 15))
    r.write(0x026F, 0x03F5, [after], 'RMW', 'DATA03F5+1')
    r.step(0x026F, 0x0270)
    r.write(0x0270, 0x03F7, [2], 'ImmediateStore', 'Literal')
    r.step(0x0270, 0x0272)
    return r.result(0x0272, 'LengthWritten')


def _checksum_rejected(r):
    r.write(0x0270, 0x03F7, [2], 'ImmediateStore', 'Literal')
    r.step(0x0270, 0x0272)
    return r.result(0x0272, 'ChecksumRejected')


def _checksum(r):
    failure = r.byte_load(0x0284, 0x0055, 0x0286)
    if failure is not None:
        return failure
    prior = r.read(0x0286, 0x03F6)[0]
    r.registers['al'] = r.add_values(r.registers['al'], prior)
    r.step(0x0286, 0x0287)
    nonzero = None if r.registers['zf'] is None else r.registers['zf'] == 0
    failure = r.branch(0x0287, nonzero, 0x0270, 0x0289)
    if failure is not None:
        return failure
    if nonzero:
        return _checksum_rejected(r)
    failure = r.byte_load(0x0289, 0x03F1, 0x028A)
    if failure is not None:
        return failure
    header_class = None if r.registers['al'] is None else r.registers['al'] & 0xE0
    r.registers.update(al=header_class, zf=None if header_class is None else int(header_class == 0))
    r.step(0x028A, 0x028C)
    r.compare_byte(header_class, 0x20)
    r.step(0x028C, 0x028E)
    wrong_class = None if r.registers['zf'] is None else r.registers['zf'] == 0
    failure = r.branch(0x028E, wrong_class, 0x0270, 0x0290)
    if failure is not None:
        return failure
    if wrong_class:
        return _checksum_rejected(r)
    r.rmw(0x0290, 0x0356, 7, 1)
    r.step(0x0290, 0x0293)
    r.write(0x0293, 0x03F7, [0], 'ImmediateStore', 'Literal')
    r.step(0x0293, 0x0295)
    return r.result(0x0295, 'ChecksumAccepted')


def header_body(snapshot):
    r = _Reference(snapshot, 'header_body')
    failure = r.admission(0x0275, flag=True)
    return failure if failure is not None else _header(r)


def length_body(snapshot):
    r = _Reference(snapshot, 'length_body')
    failure = r.admission(0x027F, flag=True)
    return failure if failure is not None else _length(r)


def checksum_body(snapshot):
    r = _Reference(snapshot, 'checksum_body')
    failure = r.admission(0x0284, flag=True)
    return failure if failure is not None else _checksum(r)


def _select(r):
    failure = r.byte_load(0x0255, 0x03F7, 0x0256)
    if failure is not None:
        return failure
    is_header = None if r.registers['zf'] is None else r.registers['zf'] == 1
    failure = r.branch(0x0256, is_header, 0x0275, 0x0258)
    if failure is not None:
        return failure
    if is_header:
        return r.result(0x0275, 'HeaderSelected')
    failure = r.byte_load(0x0258, 0x03F5, 0x0259)
    if failure is not None:
        return failure
    r.compare_byte(r.registers['al'], 1)
    r.step(0x0259, 0x025B)
    is_length = None if r.registers['zf'] is None else r.registers['zf'] == 1
    failure = r.branch(0x025B, is_length, 0x027F, 0x025D)
    if failure is not None:
        return failure
    if is_length:
        return r.result(0x027F, 'LengthSelected')
    r.registers['al'] = r.add_values(r.registers['al'], 1)
    r.step(0x025D, 0x025F)
    count = r.read(0x025F, 0x03F2)[0]
    r.compare_byte(r.registers['al'], count)
    r.step(0x025F, 0x0260)
    is_checksum = None if r.registers['zf'] is None else r.registers['zf'] == 1
    failure = r.branch(0x0260, is_checksum, 0x0284, 0x0262)
    if failure is not None:
        return failure
    return r.result(0x0284 if is_checksum else 0x0262, 'ChecksumSelected' if is_checksum else 'FlagSelected')


def dispatch(snapshot):
    r = _Reference(snapshot, 'dispatch')
    failure = r.admission(0x0255, flag=True)
    return failure if failure is not None else _select(r)


def _parser(snapshot, procedure, declared_role=None):
    r = _Reference(snapshot, procedure)
    failure = r.admission(0x021F, flag=True)
    if failure is not None:
        return failure
    r.read(0x021F, 0x0356)
    mode = r.bit(0x0356, 1)
    failure = r.branch(0x021F, None if mode is None else mode == 0, 0x029D, 0x0222, outside=True)
    if failure is not None:
        return failure
    error = r.rmw(0x0222, 0x0356, 6, 0)
    r.step(0x0222, 0x0225)
    clear = None if error is None else error == 0
    failure = r.branch(0x0225, clear, 0x0255, 0x0227)
    if failure is not None:
        return failure
    if clear is False:
        return r.outside(0x0227, 'UnmodeledBranch')
    selected = _select(r)
    if selected['status'] != 'CompleteConditional':
        return selected
    role = selected['outcome'].removesuffix('Selected')
    if declared_role is not None and role != declared_role:
        return r.outside(selected['boundary'], 'DeclaredRoleDoesNotMatchDispatch')
    return {'Header': _header, 'Length': _length, 'Flag': _flag_body, 'Checksum': _checksum}[role](r)


def parser_step(snapshot):
    return _parser(snapshot, 'parser_step')


def _label(value):
    return type(value) is str and LABEL.fullmatch(value) is not None


def _request(request):
    if type(request) is not dict or set(request) != {'stages', 'transfers'}:
        raise ValueError('ReferenceCompositionShape')
    stages, transfers = request['stages'], request['transfers']
    if type(stages) is not list or not 1 <= len(stages) <= 4 or type(transfers) is not list or len(transfers) != len(stages) - 1:
        raise ValueError('ReferenceCompositionCardinality')
    checked, ids, samples = [], set(), set()
    for item in stages:
        if type(item) is not dict or set(item) != {'id', 'role', 'sampleId', 'snapshot'}:
            raise ValueError('ReferenceStageShape')
        if (not _label(item['id']) or not _label(item['sampleId']) or type(item['role']) is not str
                or item['role'] not in ROLES or item['id'] in ids or item['sampleId'] in samples):
            raise ValueError('ReferenceStageIdentity')
        ids.add(item['id'])
        samples.add(item['sampleId'])
        checked.append({**item, 'snapshot': _checked(item['snapshot'])})
    for item in transfers:
        if type(item) is not dict or set(item) != {'from', 'to', 'relation', 'noInterference', 'retainedGenerations'}:
            raise ValueError('ReferenceTransferShape')
        if (not _label(item['from']) or not _label(item['to'])
                or type(item['relation']) is not str or not item['relation']
                or item['noInterference'] is not None and type(item['noInterference']) is not bool):
            raise ValueError('ReferenceTransferTypes')
        generations = item['retainedGenerations']
        if (type(generations) is not dict or set(generations) != set(RETAINED)
                or any(v is not None and (type(v) is not str or not v) for v in generations.values())):
            raise ValueError('ReferenceTransferGenerationMap')
    return checked, deepcopy(transfers)


def compose(request):
    stages, declarations = _request(request)
    outputs, transfers, journal, boundary_inputs = [], [], [], []
    initial = stages[0]['snapshot']
    current = {key: deepcopy(initial[key]) for key in ('memory', 'knownBits', 'registers', 'generations')}

    def result(status, reason, stage_id, pc):
        return {'procedure': 'compose', 'status': status, 'reason': reason,
            'boundary': {'stageId': stage_id, 'sourcePC': pc}, 'stages': deepcopy(outputs),
            'transfers': deepcopy(transfers), 'journal': deepcopy(journal),
            'boundaryInputs': deepcopy(boundary_inputs), 'finalState': deepcopy(current),
            'effectClass': 'ConditionalDataflowTransfer_NotNativeExecution',
            'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}

    if stages[0]['role'] != 'Header':
        return result('OutsideVerifiedScope', 'CompositionRequiresHeaderOrigin', stages[0]['id'], None)
    prefixes = ['ConditionalEffect:parser_step@' + stage['id'] + ':' for stage in stages]
    if any(value is not None and any(value.startswith(prefix) for prefix in prefixes)
           for value in initial['generations'].values()):
        return result('OutsideVerifiedScope', 'GenerationNamespaceCollision', stages[0]['id'], None)
    previous = None
    for index, stage in enumerate(stages):
        supplied = stage['snapshot']
        if index:
            declaration = declarations[index - 1]
            if (declaration['from'] != stages[index - 1]['id'] or declaration['to'] != stage['id']
                    or declaration['relation'] != 'ConditionalPersistentStateHandoff'
                    or (stages[index - 1]['role'], stage['role']) not in EDGES):
                return result('OutsideVerifiedScope', 'MissingVerifiedInterBlockRelation', stage['id'], None)
            if declaration['noInterference'] is not True:
                return result('OutsideVerifiedScope', 'NoInterferencePremiseNotEstablished', stage['id'], None)
            if previous['status'] != 'CompleteConditional':
                return result(previous['status'], previous['reason'], stages[index - 1]['id'], previous['boundary'])
            prior_generations = {key: current['generations'][key] for key in RETAINED}
            if declaration['retainedGenerations'] != prior_generations:
                return result('OutsideVerifiedScope', 'WriterLineageNotEstablished', stage['id'], None)
            def persistent(snapshot, field):
                if field == 'knownBits':
                    return {key: value for key, value in snapshot[field].items() if key[:4] != '0055'}
                return {key: snapshot[field][key] for key in RETAINED}
            if any(persistent(supplied, field) != persistent(current, field)
                   for field in ('memory', 'generations', 'knownBits')):
                return result('OutsideVerifiedScope', 'PersistentStateOverwritten', stage['id'], None)
            if (supplied['inputClass'] != stages[index - 1]['snapshot']['inputClass']
                    or supplied['assumptions'] != stages[index - 1]['snapshot']['assumptions']
                    or supplied['registers']['lrb'] != current['registers']['lrb']):
                return result('OutsideVerifiedScope', 'IncompatibleHandoffContext', stage['id'], None)
            transfers.append({**declaration,
                'classification': 'ConditionalPersistentStateHandoff_NotCfgOrNativeContinuity'})
        boundary_inputs.append({'stageId': stage['id'], 'sampleId': stage['sampleId'],
            'address': 85, 'widthBits': 8, 'value': supplied['memory']['0055'],
            'generation': supplied['generations']['0055'],
            'classification': 'ExplicitSymbolicBoundaryInput_NotPeripheralObservation'})
        local = _parser(supplied, 'parser_step@' + stage['id'], stage['role'])
        outputs.append({'id': stage['id'], 'role': stage['role'], 'sampleId': stage['sampleId'], 'output': local})
        current = deepcopy(local['state'])
        for event in local['journal']:
            journal.append({'stageId': stage['id'], 'globalOrdinal': len(journal) + 1, 'event': deepcopy(event)})
        previous = local
        if local['status'] != 'CompleteConditional':
            return result(local['status'], local['reason'], stage['id'], local['boundary'])
    return result('CompleteConditional', 'AllRequestedConditionalTransformationsEstablished', stages[-1]['id'], previous['boundary'])


OPERATIONS = {'header_body': header_body, 'length_body': length_body,
              'checksum_body': checksum_body, 'dispatch': dispatch,
              'parser_step': parser_step, 'compose': compose}


def expected_records():
    for case in cases():
        yield {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
               'output': OPERATIONS[case['operation']](case['input'])}


def canonical_bytes():
    return b''.join(canonical(record) for record in expected_records())
