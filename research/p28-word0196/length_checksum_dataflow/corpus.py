"""Explicit invented inputs and conditional handoff requests, never model output.

The small handoff constructor declares persistent-state premises from the
reviewed Header/Length/Flag algebra. It does not execute a model or receiver.
"""
from copy import deepcopy

from conditional_flag_mode_shadow.corpus import fixture as prior_fixture

ROLES = ('Header', 'Length', 'Flag', 'Checksum')
RETAINED = tuple(key for key in prior_fixture('flag')['memory'] if key != '0055')


def fixture(role='Flag'):
    if role not in ROLES:
        raise ValueError('InventedRoleRequired')
    value = prior_fixture('flag')
    value['generations'] = {key: 'SyntheticInput:M2co:' + key for key in value['memory']}
    value['memory'].update({'03F0': 0x11, '03F1': 0x21, '03F2': 4, '03F3': 2,
                            '03F4': 0x44, '03F5': 2, '03F6': 0x25, '03F7': 2})
    if role == 'Header':
        value['memory'].update({'0055': 0x21, '03F1': 0x77, '03F2': 0x99,
                                '03F5': 0x7F, '03F6': 0xCC, '03F7': 0})
    elif role == 'Length':
        value['memory'].update({'0055': 4, '03F2': 0x99, '03F5': 1, '03F6': 0x21})
    elif role == 'Flag':
        value['memory']['0055'] = 2
    else:
        value['memory'].update({'0055': 0xD9, '03F5': 3, '03F6': 0x27})
    return value


def _sum(a, b):
    return None if a is None or b is None else (a + b) % 256


def _handoff_premise(snapshot, stage_id, role):
    """Construct only next-input value/label premises; not an execution result."""
    value = deepcopy(snapshot)
    memory = value['memory']
    generation = value['generations']
    ordinal = 0

    def supplied_write(pc, address, byte):
        nonlocal ordinal
        ordinal += 1
        memory[address] = byte
        generation[address] = f'ConditionalEffect:parser_step@{stage_id}:{pc:04X}:{ordinal}'
        value['knownBits'] = {k: v for k, v in value['knownBits'].items() if k[:4] != address}

    raw_status = memory['0356']
    prior_bits = deepcopy(value['knownBits'])
    supplied_write(0x0222, '0356', None if raw_status is None else raw_status & 0xBF)
    if raw_status is None:
        value['knownBits'] = prior_bits
        value['knownBits']['0356.6'] = 0
    sample = memory['0055']
    if role == 'Header':
        supplied_write(0x0275, '03F0', memory['03F1'])
        supplied_write(0x0279, '03F1', sample)
        supplied_write(0x027A, '03F6', sample)
        supplied_write(0x027B, '03F5', 1)
        supplied_write(0x0270, '03F7', 2)
    elif role == 'Length':
        supplied_write(0x0281, '03F2', sample)
        supplied_write(0x026D, '03F6', _sum(memory['03F6'], sample))
        supplied_write(0x026F, '03F5', _sum(memory['03F5'], 1))
        supplied_write(0x0270, '03F7', 2)
    elif role == 'Flag':
        supplied_write(0x0269, '03F3', sample)
        supplied_write(0x026D, '03F6', _sum(memory['03F6'], sample))
        supplied_write(0x026F, '03F5', _sum(memory['03F5'], 1))
        supplied_write(0x0270, '03F7', 2)
    else:
        raise ValueError('NoChecksumSuccessorPremiseInCorpus')
    return value


def request(header=0x21, length=4, flag=2, checksum=None, roles=None):
    """Explicit mathematical handoff request; no automatic receive/event source."""
    if roles is None:
        roles = ['Header', 'Length', 'Flag', 'Checksum']
    else:
        roles = list(roles)
    if checksum is None:
        total = None if header is None or length is None or flag is None else (header + length + (0 if roles == ['Header', 'Length', 'Checksum'] else flag)) % 256
        checksum = None if total is None else (-total) % 256
    samples = {'Header': header, 'Length': length, 'Flag': flag, 'Checksum': checksum}
    identifiers = {'Header': 'h', 'Length': 'l', 'Flag': 'f', 'Checksum': 'k'}
    stages, transfers = [], []
    state = fixture('Header')
    for index, role in enumerate(roles):
        if index:
            previous = stages[-1]
            state = _handoff_premise(state, previous['id'], previous['role'])
            # Incoming architectural context is explicit, not an inferred RTI restore.
            state['registers'].update(al=0x40 + index, ah=0x50 + index, cf=index % 2,
                                       zf=(index + 1) % 2, hc=index % 2, dd=index % 2, mie=0)
        stage_id = identifiers[role]
        state['memory']['0055'] = samples[role]
        state['generations']['0055'] = 'ExplicitSymbolicSample:' + stage_id
        stages.append({'id': stage_id, 'role': role, 'sampleId': 'sample_' + stage_id,
                       'snapshot': deepcopy(state)})
        if index:
            transfers.append({'from': stages[index - 1]['id'], 'to': stage_id,
                'relation': 'ConditionalPersistentStateHandoff', 'noInterference': True,
                'retainedGenerations': {key: state['generations'][key] for key in RETAINED}})
    return {'stages': stages, 'transfers': transfers}


def cases():
    for value in range(256):
        state = fixture('Header')
        state['memory']['0055'] = value
        yield {'id': f'header-byte-{value:02X}', 'operation': 'header_body', 'input': state}
    for value in range(256):
        for prior in (0, 255):
            state = fixture('Length')
            state['memory'].update({'0055': value, '03F6': prior})
            yield {'id': f'length-byte-{value:02X}-sum-{prior:02X}', 'operation': 'length_body', 'input': state}
    for count in (0, 1, 15, 127, 255, None):
        state = fixture('Length')
        state['memory'].update({'0055': 15, '03F6': 15, '03F5': count})
        yield {'id': 'length-direct-counter-' + str(count), 'operation': 'length_body', 'input': state}
    for prior in (1, 15, 127, 128):
        for value in (0, 1, 127, 128, 255):
            state = fixture('Length')
            state['memory'].update({'0055': value, '03F6': prior})
            yield {'id': f'length-boundary-{prior:02X}-{value:02X}', 'operation': 'length_body', 'input': state}

    for prior in range(256):
        for correct in (True, False):
            state = fixture('Checksum')
            state['memory'].update({'03F6': prior, '0055': ((-prior) + (0 if correct else 1)) % 256,
                                    '0356': 2 | ((prior % 2) << 7)})
            yield {'id': f'checksum-sum-{prior:02X}-match-{int(correct)}', 'operation': 'checksum_body', 'input': state}
    for header in range(256):
        state = fixture('Checksum')
        state['memory']['03F1'] = header
        yield {'id': f'checksum-header-class-{header:02X}', 'operation': 'checksum_body', 'input': state}
    for ready in (0, 1, None):
        state = fixture('Checksum')
        if ready is None:
            state['memory']['0356'] = None
            state['knownBits'] = {'0356.1': 1, '0356.6': 0}
        else:
            state['memory']['0356'] = 2 | (ready << 7)
        yield {'id': 'checksum-old-ready-' + str(ready), 'operation': 'checksum_body', 'input': state}
    for address in ('0055', '03F6', '03F1'):
        state = fixture('Checksum')
        state['memory'][address] = None
        state['inputClass'] = 'SymbolicInput'
        yield {'id': 'checksum-unknown-' + address, 'operation': 'checksum_body', 'input': state}
    state = fixture('Checksum')
    state['memory']['03F7'] = 0
    yield {'id': 'checksum-same-value-r7-clear', 'operation': 'checksum_body', 'input': state}

    for r7 in (0, 2, None):
        for r5 in (0, 1, 2, 3, 255, None):
            for r2 in (0, 3, 4, 255, None):
                state = fixture('Flag')
                state['memory'].update({'03F7': r7, '03F5': r5, '03F2': r2, '0055': None})
                yield {'id': f'dispatch-r7-{r7}-r5-{r5}-r2-{r2}', 'operation': 'dispatch', 'input': state}
    for role in ROLES:
        for value in (0, 1, 2, 0x7F, 0x80, 0xFF, None):
            state = fixture(role)
            state['memory']['0055'] = value
            yield {'id': f'parser-{role}-{value}', 'operation': 'parser_step', 'input': state}
    for r5 in (0, 2, 3, 255):
        state = fixture('Flag')
        state['memory'].update({'03F5': r5, '03F2': 5})
        yield {'id': f'parser-outside-data-{r5}', 'operation': 'parser_step', 'input': state}
    for name, bits, byte in (('mode-zero', {}, 0), ('old-error', {}, 0x42),
                              ('unknown-mode', {}, None), ('unknown-error', {'0356.1': 1}, None),
                              ('partial-controls', {'0356.1': 1, '0356.6': 0, '0356.7': 1}, None)):
        state = fixture('Header')
        state['memory']['0356'] = byte
        state['knownBits'] = bits
        yield {'id': 'parser-status-' + name, 'operation': 'parser_step', 'input': state}
    for operation, role in (('header_body', 'Header'), ('length_body', 'Length'),
                              ('checksum_body', 'Checksum'), ('dispatch', 'Flag'), ('parser_step', 'Header')):
        for lrb in (None, 0x0040):
            state = fixture(role)
            state['registers']['lrb'] = lrb
            yield {'id': f'context-{operation}-{lrb}', 'operation': operation, 'input': state}
        for assumption in ('ordinaryByteSemantics', 'noInterference'):
            for value in (False, None):
                state = fixture(role)
                state['assumptions'][assumption] = value
                yield {'id': f'premise-{operation}-{assumption}-{value}', 'operation': operation, 'input': state}
    for operation, role in (('header_body', 'Header'), ('length_body', 'Length')):
        for address in ('0055', '03F1', '03F6'):
            state = fixture(role)
            state['memory'][address] = None
            yield {'id': f'unknown-{operation}-{address}', 'operation': operation, 'input': state}
    state = fixture('Header')
    state['memory']['03F0'] = state['memory']['03F1']
    yield {'id': 'header-same-value-old-header-save', 'operation': 'header_body', 'input': state}

    for flag in range(256):
        yield {'id': f'compose-all-flag-{flag:02X}', 'operation': 'compose', 'input': request(flag=flag)}
    for flag in (0, 1, 2, 0x7F, 0x80, 0xFF):
        bad = (-(0x21 + 4 + flag) + 1) % 256
        yield {'id': f'compose-bad-checksum-{flag:02X}', 'operation': 'compose', 'input': request(flag=flag, checksum=bad)}
    for header in (0, 0x1F, 0x20, 0x21, 0x3F, 0x40, 0xFF, None):
        yield {'id': 'compose-header-class-' + str(header), 'operation': 'compose', 'input': request(header=header)}
    for length in (0, 1, 2, 3, 4, 5, 255, None):
        roles = ['Header', 'Length', 'Checksum'] if length == 3 else None
        yield {'id': 'compose-length-' + str(length), 'operation': 'compose', 'input': request(length=length, roles=roles)}
    yield {'id': 'compose-only-header', 'operation': 'compose', 'input': request(roles=['Header'])}
    yield {'id': 'compose-header-length', 'operation': 'compose', 'input': request(roles=['Header', 'Length'])}
    yield {'id': 'compose-unknown-flag', 'operation': 'compose', 'input': request(flag=None)}
    partial = request()
    for stage in partial['stages']:
        stage['snapshot']['memory']['0356'] = None
        stage['snapshot']['knownBits'] = {'0356.1': 1, '0356.6': 0}
    yield {'id': 'compose-partial-status-unknown-ready', 'operation': 'compose', 'input': partial}
    stale = request(checksum=0)
    for stage in stale['stages']:
        stage['snapshot']['memory']['0356'] = 0x82
    yield {'id': 'compose-rejected-checksum-retains-stale-ready', 'operation': 'compose', 'input': stale}
    for name in ('first-role', 'namespace', 'wrong-from', 'wrong-to', 'wrong-relation', 'missing-role-edge',
                 'no-interference', 'unknown-interference', 'missing-writer', 'wrong-lineage',
                 'overwrite-value', 'same-value-overwrite', 'overwrite-bits', 'context-lrb',
                 'context-class', 'context-assumptions', 'declared-role', 'first-prefix-failure'):
        value = request()
        if name == 'first-role':
            value['stages'][0]['role'] = 'Flag'
        elif name == 'namespace':
            value['stages'][0]['snapshot']['generations']['03F0'] = 'ConditionalEffect:parser_step@h:0275:2'
        elif name in ('wrong-from', 'wrong-to'):
            value['transfers'][0]['from' if name == 'wrong-from' else 'to'] = 'other'
        elif name == 'wrong-relation':
            value['transfers'][0]['relation'] = 'UnprovedNativeCfgEdge'
        elif name == 'missing-role-edge':
            value['stages'][1]['role'] = 'Checksum'
        elif name in ('no-interference', 'unknown-interference'):
            value['transfers'][0]['noInterference'] = False if name == 'no-interference' else None
        elif name in ('missing-writer', 'wrong-lineage'):
            value['transfers'][0]['retainedGenerations']['03F6'] = None if name == 'missing-writer' else 'OtherWriter'
        elif name == 'overwrite-value':
            value['stages'][1]['snapshot']['memory']['03F6'] ^= 1
        elif name == 'same-value-overwrite':
            value['stages'][1]['snapshot']['generations']['03F6'] = 'SameValueOtherWriter'
        elif name == 'overwrite-bits':
            value['stages'][1]['snapshot']['knownBits']['0356.7'] = 0
        elif name == 'context-lrb':
            value['stages'][1]['snapshot']['registers']['lrb'] = 0x0040
        elif name == 'context-class':
            value['stages'][1]['snapshot']['inputClass'] = 'SymbolicInput'
        elif name == 'context-assumptions':
            value['stages'][1]['snapshot']['assumptions']['ordinaryByteSemantics'] = False
        elif name == 'declared-role':
            value = request(length=3)
        else:
            value['stages'][0]['snapshot']['assumptions']['ordinaryByteSemantics'] = False
        yield {'id': 'compose-negative-' + name, 'operation': 'compose', 'input': value}
