"""Explicit invented byte inputs and source-qualified handoff premises.

The constructors declare mathematical input relations; they never call a model,
receiver, CPU, oracle or checksum validator. Long routes are bounded fixtures.
"""
from copy import deepcopy

from length_checksum_dataflow.corpus import (
    _handoff_premise as prior_premise, fixture as prior_fixture,
)

ROLES = ('Header', 'Length', 'Flag', 'Generic', 'Checksum')
RETAINED = tuple(key for key in prior_fixture()['memory'] if key != '0055')


def fixture(role='Generic'):
    if role not in ROLES:
        raise ValueError('InventedRoleRequired')
    state = prior_fixture('Flag' if role == 'Generic' else role)
    state['generations'] = {key: 'SyntheticInput:M2cp:' + key for key in state['memory']}
    if role == 'Generic':
        state['memory'].update({'0055': 0x7F, '03F2': 5, '03F5': 3, '03F6': 0x28})
        state['registers'].update(al=0x7F, dd=0)
    return state


def _sum(*values):
    return None if any(value is None for value in values) else sum(values) % 256


def _premise(snapshot, stage_id, role):
    if role != 'Generic':
        return prior_premise(snapshot, stage_id, role)
    value = deepcopy(snapshot)
    memory, generations = value['memory'], value['generations']
    original_bits = deepcopy(value['knownBits'])
    raw = memory['0356']
    writes = ((0x0222, '0356', None if raw is None else raw & 0xBF),
              (0x026C, '03F4', memory['0055']),
              (0x026D, '03F6', _sum(memory['03F6'], memory['0055'])),
              (0x026F, '03F5', _sum(memory['03F5'], 1)),
              (0x0270, '03F7', 2))
    for ordinal, (pc, address, byte) in enumerate(writes, 1):
        memory[address] = byte
        generations[address] = f'ConditionalEffect:parser_step@{stage_id}:{pc:04X}:{ordinal}'
        value['knownBits'] = {key: bit for key, bit in value['knownBits'].items() if key[:4] != address}
    if raw is None:
        value['knownBits'] = {**original_bits, '0356.6': 0}
    return value


def sequence(length=5, header=0x21, data=None, checksum='auto', reentry_length=None):
    """Invented explicit sequence, not an inferred native packet or receive loop."""
    distance = 1 if length is None else 255 if length == 2 else (length - 3) % 256
    data = [(0x11 + 37 * index) % 256 for index in range(distance)] if data is None else list(data)
    if len(data) != distance:
        raise ValueError('ExactInventedDataInventoryRequired')
    specs = [('Header', header), ('Length', length)]
    specs.extend(('Flag' if index == 0 else 'Generic', byte) for index, byte in enumerate(data))
    if length == 2 and reentry_length is not None:
        specs.append(('Length', reentry_length))
    include_checksum = length is not None and (length != 2 or reentry_length == 3)
    if include_checksum:
        total = _sum(header, length, *data, *([] if length != 2 else [reentry_length]))
        byte = None if total is None else (-total) % 256
        specs.append(('Checksum', byte if checksum == 'auto' else checksum))
    state = fixture('Header')
    stages, transfers, counts = [], [], {}
    stems = {'Header': 'h', 'Length': 'l', 'Flag': 'f', 'Generic': 'p', 'Checksum': 'k'}
    for index, (role, byte) in enumerate(specs):
        if index:
            prior = stages[-1]
            state = _premise(state, prior['id'], prior['role'])
            # Each incoming register context is explicitly supplied, never restored by RTI.
            state['registers'].update(al=(0x40 + index) % 256, ah=(0x70 + index) % 256,
                cf=index % 2, zf=(index + 1) % 2, hc=index % 2,
                dd=None if index % 3 == 0 else index % 2, mie=index % 2)
        number = counts.get(role, 0)
        counts[role] = number + 1
        stage_id = ('p' + f'{number:03d}') if role == 'Generic' else stems[role] + (str(number + 1) if number else '')
        state['memory']['0055'] = byte
        state['generations']['0055'] = 'ExplicitSymbolicSample:' + stage_id
        stages.append({'id': stage_id, 'role': role, 'sampleId': 'sample_' + stage_id,
                       'snapshot': deepcopy(state)})
        if index:
            transfers.append({'from': stages[index - 1]['id'], 'to': stage_id,
                'relation': 'ConditionalPersistentStateHandoff', 'noInterference': True,
                'retainedGenerations': {key: state['generations'][key] for key in RETAINED}})
    return {'stages': stages, 'transfers': transfers}


def cases():
    for byte in range(256):
        for prior in (0, 255):
            value = fixture()
            value['registers']['al'] = byte
            value['memory'].update({'0055': byte ^ 0xFF, '03F6': prior})
            yield {'id': f'direct-byte-{byte:02X}-sum-{prior:02X}', 'operation': 'generic_payload_body', 'input': value}
        for counter in (2, 3):
            value = fixture('Generic')
            value['memory'].update({'0055': byte, '03F5': counter, '03F6': 255})
            value['registers'].update(al=byte ^ 0xFF, dd=1)
            yield {'id': f'data-byte-{byte:02X}-counter-{counter}', 'operation': 'data_body', 'input': value}
    for operation in ('generic_payload_body', 'data_body'):
        for counter in (0, 1, 2, 3, 4, 15, 254, 255, None):
            for byte in (0, 1, 2, 3, 127, 128, 254, 255, None):
                value = fixture()
                value['registers']['al'] = byte
                value['memory'].update({'0055': byte, '03F5': counter, '03F6': 15})
                yield {'id': f'{operation}-boundary-{counter}-{byte}', 'operation': operation, 'input': value}
    for operation in ('generic_payload_body', 'data_body', 'dispatch', 'parser_step'):
        for dd in (0, 1, None):
            value = fixture()
            value['registers']['dd'] = dd
            yield {'id': f'{operation}-incoming-dd-{dd}', 'operation': operation, 'input': value}
        for name in ('ordinaryByteSemantics', 'noInterference'):
            for premise in (False, None):
                value = fixture()
                value['assumptions'][name] = premise
                yield {'id': f'{operation}-{name}-{premise}', 'operation': operation, 'input': value}
        for lrb in (0x0040, None):
            value = fixture()
            value['registers']['lrb'] = lrb
            yield {'id': f'{operation}-lrb-{lrb}', 'operation': operation, 'input': value}
    for operation in ('generic_payload_body', 'data_body'):
        for address in ('03F4', '03F5', '03F6'):
            value = fixture()
            value['memory'][address] = None
            yield {'id': f'{operation}-unknown-{address}', 'operation': operation, 'input': value}
        value = fixture()
        value['memory']['03F4'] = value['registers']['al']
        yield {'id': operation + '-same-value-generic-store', 'operation': operation, 'input': value}
    for r7 in (0, 2, None):
        for r5 in (0, 1, 2, 3, 4, 254, 255, None):
            for r2 in (0, 2, 3, 4, 5, None):
                value = fixture()
                value['memory'].update({'03F7': r7, '03F5': r5, '03F2': r2, '0055': None})
                yield {'id': f'dispatch-{r7}-{r5}-{r2}', 'operation': 'dispatch', 'input': value}
    for role in ROLES:
        for byte in (0, 1, 2, 127, 128, 255, None):
            value = fixture(role)
            value['memory']['0055'] = byte
            yield {'id': f'parser-{role}-{byte}', 'operation': 'parser_step', 'input': value}
    for name, byte, bits in (('mode-zero', 0, {}), ('old-error', 0x42, {}),
                             ('unknown-mode', None, {}), ('unknown-error', None, {'0356.1': 1}),
                             ('partial-controls', None, {'0356.1': 1, '0356.6': 0})):
        value = fixture()
        value['memory']['0356'], value['knownBits'] = byte, bits
        yield {'id': 'parser-status-' + name, 'operation': 'parser_step', 'input': value}
    for length in range(256):
        yield {'id': f'counter-all-length-{length:02X}', 'operation': 'counter_route',
               'input': {'length': length, 'maxDataStages': 512}}
    for length in (0, 1, 2, 3, 4, 5, 8, 255):
        distance = 255 if length == 2 else (length - 3) % 256
        for bound in sorted({0, 1, max(0, distance - 1), distance, distance + 1}):
            yield {'id': f'counter-resource-{length}-{bound}', 'operation': 'counter_route',
                   'input': {'length': length, 'maxDataStages': bound}}
    for bound in (0, 1, 512):
        yield {'id': f'counter-unknown-length-{bound}', 'operation': 'counter_route',
               'input': {'length': None, 'maxDataStages': bound}}
    for byte in range(256):
        yield {'id': f'compose-all-generic-{byte:02X}', 'operation': 'compose',
               'input': sequence(data=[2, byte])}
    for length in range(3, 9):
        count = length - 3
        for pattern in ('zero', 'edges', 'mixed'):
            data = ([0] * count if pattern == 'zero' else
                    [[0, 255, 128, 127, 1][i % 5] for i in range(count)] if pattern == 'edges' else
                    [(0x11 + 37 * i) % 256 for i in range(count)])
            yield {'id': f'compose-short-{length}-{pattern}', 'operation': 'compose',
                   'input': sequence(length=length, data=data)}
    for length in (255, 0, 1):
        yield {'id': f'compose-long-length-{length}', 'operation': 'compose', 'input': sequence(length=length)}
    yield {'id': 'compose-long-length2-reentry3-checksum', 'operation': 'compose', 'input': sequence(length=2, reentry_length=3)}
    for name, value in (('unknown-length', sequence(length=None)), ('unknown-header', sequence(header=None)),
                         ('unknown-flag', sequence(data=[None, 1])), ('unknown-generic', sequence(data=[2, None])),
                         ('unknown-checksum', sequence(checksum=None)), ('bad-checksum', sequence(checksum=0)),
                         ('bad-header-class', sequence(header=0x40)), ('full-header-class', sequence(header=0x3F))):
        yield {'id': 'compose-' + name, 'operation': 'compose', 'input': value}
    partial = sequence()
    for stage in partial['stages']:
        stage['snapshot']['memory']['0356'] = None
        stage['snapshot']['knownBits'] = {'0356.1': 1, '0356.6': 0}
    yield {'id': 'compose-partial-ready-unknown', 'operation': 'compose', 'input': partial}
    for length in (3, 5, 8):
        value = sequence(length=length)
        value['stages'], value['transfers'] = value['stages'][:-1], value['transfers'][:-1]
        yield {'id': f'compose-prefix-without-checksum-{length}', 'operation': 'compose', 'input': value}
    for name in ('first-role', 'namespace', 'wrong-from', 'wrong-to', 'wrong-relation', 'no-interference',
                 'unknown-interference', 'missing-writer', 'wrong-lineage', 'overwrite-value',
                 'same-value-other-writer', 'overwrite-bits', 'context-lrb', 'context-class',
                 'context-assumptions', 'premature-checksum', 'wrong-subrole', 'unknown-input-owner',
                 'first-mode-exit', 'second-error-exit'):
        value = sequence(length=6)
        if name == 'first-role':
            value['stages'][0]['role'] = 'Generic'
        elif name == 'namespace':
            value['stages'][0]['snapshot']['generations']['03F4'] = 'ConditionalEffect:parser_step@p000:026C:2'
        elif name in ('wrong-from', 'wrong-to'):
            value['transfers'][2]['from' if name == 'wrong-from' else 'to'] = 'other'
        elif name == 'wrong-relation':
            value['transfers'][2]['relation'] = 'NativeReceiveReentry'
        elif name in ('no-interference', 'unknown-interference'):
            value['transfers'][2]['noInterference'] = False if name == 'no-interference' else None
        elif name in ('missing-writer', 'wrong-lineage'):
            value['transfers'][2]['retainedGenerations']['03F6'] = None if name == 'missing-writer' else 'OtherWriter'
        elif name == 'overwrite-value':
            value['stages'][3]['snapshot']['memory']['03F6'] ^= 1
        elif name == 'same-value-other-writer':
            value['stages'][3]['snapshot']['generations']['03F6'] = 'SameValueOtherWriter'
        elif name == 'overwrite-bits':
            value['stages'][3]['snapshot']['knownBits']['0356.7'] = 0
        elif name == 'context-lrb':
            value['stages'][3]['snapshot']['registers']['lrb'] = None
        elif name == 'context-class':
            value['stages'][3]['snapshot']['inputClass'] = 'SymbolicInput'
        elif name == 'context-assumptions':
            value['stages'][3]['snapshot']['assumptions']['ordinaryByteSemantics'] = None
        elif name == 'premature-checksum':
            value['stages'][3]['role'] = 'Checksum'
        elif name == 'wrong-subrole':
            value['stages'][3]['role'] = 'Flag'
        elif name == 'unknown-input-owner':
            value['stages'][3]['snapshot']['generations']['0055'] = None
        elif name == 'first-mode-exit':
            value['stages'][0]['snapshot']['memory']['0356'] = 0
        else:
            value['stages'][1]['snapshot']['memory']['0356'] = 0x42
        yield {'id': 'compose-negative-' + name, 'operation': 'compose', 'input': value}
