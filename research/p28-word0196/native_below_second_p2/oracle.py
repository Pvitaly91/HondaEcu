"""Independent 39-boundary source/manufacturer model, never a CPU executor."""
from copy import deepcopy
from hashlib import sha256
import independent_encoder as encoder
from native_post_p2_control import oracle as previous
from . import corpus

_equal, _closed, BASE_ORACLE = previous._equal, previous._closed, previous.BASE_ORACLE
TAIL_FORM = {
    0x55D2: (1851, 'ROLB A', 'rolb-a', 1, 2),
    0x55D3: (2301, 'STB A, off N8', 'stb-a-page', 2, 4),
    0x55D5: (1779, 'RB N8.2', 'rb-zero-bit2', 3, 9),
    0x55D8: (724, 'L A, #N16', 'l-a-imm16', 3, 6),
    0x55DB: (2180, 'SJ rel8', 'sj-rel8', 2, 8),
    0x562C: (2287, 'ST A, off N8', 'st-a-page', 2, 4),
    0x562E: (724, 'L A, #N16', 'l-a-imm16', 3, 6),
    0x5631: (2287, 'ST A, off N8', 'st-a-page', 2, 4),
    0x5633: (684, 'J addr16', 'j-direct16', 3, 7),
    0x565D: (2287, 'ST A, off N8', 'st-a-page', 2, 4),
    0x565F: (732, 'L A, off N8', 'l-a-page', 2, 4),
    0x5661: (718, 'JNE rel8', 'jne-rel8', 2, 8),
    0x5671: (747, 'LB A, off N8', 'lb-a-page', 2, 4),
    0x5673: (2180, 'SJ rel8', 'sj-rel8', 2, 8),
    0x567E: (1630, 'ORB A, off N8', 'orb-a-page', 2, 4),
    0x5680: (322, 'ANDB A, #N8', 'andb-a-imm8', 2, 4),
    0x5682: (1647, 'ORB N8, A', 'orb-zero-a', 3, 6),
    0x5685: (1776, 'RB off N8.7', 'rb-page-bit7', 3, 9),
}
FORM = {**previous.FORM, **{pc: row[:2] for pc, row in TAIL_FORM.items()}}
SUCCESSORS = {pc: (corpus.DOWNSTREAM[index + 1] if index + 1 < 18 else 0x5688)
              for index, pc in enumerate(corpus.DOWNSTREAM)}
CYCLE_ACCOUNTING = {**deepcopy(previous.CYCLE_ACCOUNTING),
    'belowInstructions': [{'nativePC': pc, 'softwareDiagnosticCounterDelta': row[4],
        'manufacturerInt': 7 if pc == 0x5682 else row[4]} for pc, row in TAIL_FORM.items()],
    'belowSoftwareDiagnosticTotal': 101, 'belowManufacturerIntTotal': 102,
    'secondP2SoftwareDiagnosticDelta': 6, 'secondP2ManufacturerInt': 7,
    'overallClassification': 'DiagnosticCycleTimingEquivalenceNotEstablished'}


def _pc(pc, kind):
    return previous._pc(pc, kind)


def _address(address, kind):
    return corpus.PUBLIC_DATA.get(address, address) if kind == 'public_fixture' else address


def diagnostic_snapshot_count(retirements):
    if type(retirements) is not int or retirements != 39:
        raise ValueError('ExactBelow39DiagnosticDomainRequired')
    return 4 * retirements + 4


def downstream_extent(pc, kind):
    if kind not in ('private', 'public_fixture') or pc not in TAIL_FORM:
        raise ValueError('ClosedEighteenBelowEncodingCellsRequired')
    address = {0x55D3: 0x0116, 0x562C: 0x0110, 0x5631: 0x0112, 0x565D: 0x0114,
               0x565F: 0x0110, 0x5671: 0x0116, 0x567E: 0x018F, 0x5685: 0x012A}
    if pc == 0x55D2:
        return bytes((0x33,))
    if pc == 0x55D5:
        return bytes((0xC5, 0x40, 0x0A))
    if pc in (0x55D8, 0x562E):
        return bytes((0x67, 1, 0))
    if pc in (0x55DB, 0x5661, 0x5673):
        return bytes((0xCE if pc == 0x5661 else 0xCB, SUCCESSORS[pc] - pc - 2))
    if pc == 0x5633:
        target = _pc(0x565D, kind)
        return bytes((3, target & 255, target >> 8))
    if pc == 0x5680:
        return bytes((0xD6, 15))
    if pc == 0x5682:
        return bytes((0xC5, 0x24, 0xE1))
    opcode = 0xD4 if pc in (0x55D3, 0x562C, 0x5631, 0x565D) else 0xE4 if pc == 0x565F else 0xF4 if pc == 0x5671 else 0xE7 if pc == 0x567E else 0xC4
    raw = bytes((opcode, _address(address[pc], kind) & 255))
    return raw + bytes((0x0F,)) if pc == 0x5685 else raw


def _seed_events(case, kind):
    logical, raw, memory = [], [], {}
    seeds = sorted((int(address), 8, value) for address, value in corpus.wire_case(case, kind)['data'].items())
    for bank, words in enumerate(case['entry']['pointing_banks']):
        seeds.extend((0x80 + bank * 8 + slot * 2, 16, words[name])
            for slot, name in enumerate(('x1', 'x2', 'dp', 'usp')))
    for address, width, value in seeds:
        old = sum(memory.get(address + i, 0xA5) << (8 * i) for i in range(width // 8))
        ordinal = len(logical)
        logical.append({'ordinal': ordinal, 'phase': 'Seed', 'pc': _pc(corpus.ENTRY_PC, kind), 'instruction_index': None,
            'address': address, 'width': width, 'operation': 'Write', 'requested_value': value, 'value': value,
            'old_value': old, 'write_ordinal': ordinal, 'same_value': value == old, 'serviced': True, 'refusal': None})
        for i in range(width // 8):
            byte, old_byte = value >> (8 * i) & 255, memory.get(address + i, 0xA5)
            raw.append({'ordinal': len(raw), 'logical_ordinal': ordinal, 'address': address + i, 'operation': 'Write',
                'requested_value': byte, 'value': byte, 'old_value': old_byte, 'write_ordinal': len(raw),
                'same_value': byte == old_byte, 'serviced': True, 'refusal': None})
            memory[address + i] = byte
    _equal((len(logical), len(raw)), (55, 87), 'seed/new_separate_55_87')
    return logical, raw


def _data_expected(case, expected, kind):
    logical, raw = _seed_events(case, kind)
    spans, raw_writes = [], len(raw)
    for step in expected['steps']:
        start = len(logical), len(raw)
        for event in step['data_events']:
            ordinal = len(logical)
            logical.append({'ordinal': ordinal, 'phase': 'Functional', **event, 'serviced': True, 'refusal': None})
            if step['native_site_identity'] == '55CF' and event['address'] == 6:
                continue
            for offset in range(event['width'] // 8):
                writing = event['operation'] == 'Write'
                value = event['value'] >> (8 * offset) & 255
                old = event['old_value'] >> (8 * offset) & 255 if writing else None
                raw.append({'ordinal': len(raw), 'logical_ordinal': ordinal, 'address': event['address'] + offset,
                    'operation': event['operation'], 'requested_value': value if writing else None,
                    'value': value, 'old_value': old, 'write_ordinal': raw_writes if writing else None,
                    'same_value': old == value if writing else None, 'serviced': True, 'refusal': None})
                raw_writes += int(writing)
        spans.append({'logical_span': [start[0], len(logical)], 'raw_span': [start[1], len(raw)]})
    return logical, raw, spans


def expected_case(case, program_kind='private'):
    corpus.validate_case(case)
    if program_kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2bxProgramKindRequired')
    expected = deepcopy(previous.expected_case(corpus.scalar_case(case), program_kind))
    # Old mathematical model remains unchanged. Extend only the new input frame
    # and new setup ordinals; no observed state is used to repair expectations.
    for step in expected['steps']:
        for side in ('before', 'after'):
            step[side]['owned_ram'].update({str(address): 0xA5 for address in corpus.NEW_CANARIES})
        for event in step['data_events']:
            if event['write_ordinal'] is not None:
                event['write_ordinal'] += 7
    expected['entry'] = deepcopy(expected['steps'][0]['before'])
    current = deepcopy(expected['steps'][-1]['after'])
    memory = current['owned_ram']
    write_count = expected['write_count']
    control = expected['control_final'][:]
    p2 = expected['final_p2']
    controls = deepcopy(expected['control_step_snapshots'])
    p2s = deepcopy(expected['p2_step_snapshots'])
    for pc in corpus.DOWNSTREAM:
        row = TAIL_FORM[pc]
        _equal(current['cpu']['pc'], _pc(pc, program_kind), 'independent/native_next_pc')
        before, after = deepcopy(current), deepcopy(current)
        a, psw = before['cpu']['a'], before['full_psw']
        events, branch = [], None
        old_control, old_p2 = control[:], p2
        def read(address, width=8):
            mapped = _address(address, program_kind)
            value = sum(before['owned_ram'][str(mapped + i)] << (8 * i) for i in range(width // 8))
            events.append({'pc': _pc(pc, program_kind), 'instruction_index': row[0], 'address': mapped,
                'width': width, 'operation': 'Read', 'requested_value': None, 'value': value,
                'old_value': None, 'write_ordinal': None, 'same_value': None})
            return value
        def write(address, value, width=8, *, peripheral=None):
            nonlocal write_count
            mapped = _address(address, program_kind)
            old = peripheral if peripheral is not None else sum(before['owned_ram'][str(mapped + i)] << (8 * i) for i in range(width // 8))
            events.append({'pc': _pc(pc, program_kind), 'instruction_index': row[0], 'address': mapped,
                'width': width, 'operation': 'Write', 'requested_value': value, 'value': value,
                'old_value': old, 'write_ordinal': 55 + write_count, 'same_value': old == value})
            if peripheral is None:
                for i in range(width // 8):
                    after['owned_ram'][str(mapped + i)] = value >> (8 * i) & 255
            write_count += 1
        def zf(value):
            nonlocal psw
            psw = psw & ~0x4000 | int(value == 0) << 14
        if pc == 0x55D2:
            old = a & 255
            a = a & 0xFF00 | ((old << 1) | int(bool(psw & 0x8000))) & 255
            psw = psw & ~0x8000 | (old >> 7) << 15
        elif pc == 0x55D3:
            write(0x0116, a & 255)
        elif pc == 0x55D5:
            old = control[0]
            events.extend(previous._event(_pc(pc, program_kind), row[0], 64, 'Read', old) for _ in range(2))
            zf(old & 4)
            control[0] = old & 0xFB
            write(64, control[0], peripheral=old)
        elif pc in (0x55D8, 0x562E):
            a = 1; psw |= 0x1000; zf(a)
        elif pc in (0x562C, 0x5631, 0x565D):
            write({0x562C: 0x0110, 0x5631: 0x0112, 0x565D: 0x0114}[pc], a, 16)
        elif pc == 0x565F:
            a = read(0x0110, 16); psw |= 0x1000; zf(a)
        elif pc == 0x5661:
            branch = not bool(psw & 0x4000)
            _equal(branch, True, 'independent/native_store_forces_JNE')
        elif pc == 0x5671:
            a = a & 0xFF00 | read(0x0116); psw &= ~0x1000; zf(a & 255)
        elif pc == 0x567E:
            a |= read(0x018F); zf(a & 255)
        elif pc == 0x5680:
            a = a & 0xFF00 | (a & 15); zf(a & 255)
        elif pc == 0x5682:
            _equal(a & 255, 15, 'independent/native_mask_yields_0F')
            events.append(previous._event(_pc(pc, program_kind), row[0], 36, 'Read', p2))
            p2 |= a & 255; write(36, p2, peripheral=old_p2); zf(p2)
        elif pc == 0x5685:
            old = read(0x012A); read(0x012A); zf(old & 128); write(0x012A, old & 127)
        after['full_psw'] = psw
        after['cpu'].update(pc=_pc(SUCCESSORS[pc], program_kind), a=a, cf=bool(psw & 0x8000),
            zf=bool(psw & 0x4000), hc=bool(psw & 0x2000), dd=bool(psw & 0x1000), psw_other=psw & 0x0337,
            instructions=before['cpu']['instructions'] + 1, cycles=before['cpu']['cycles'] + row[4])
        index = len(expected['steps']) + 1
        expected['steps'].append({'index': index, 'native_site_identity': f'{pc:04X}', 'pc': _pc(pc, program_kind),
            'next_pc': after['cpu']['pc'], 'form': row[2], 'decoded_index': row[0], 'mnemonic': row[1],
            'length': row[3], 'branch_taken': branch, 'before': before, 'after': after, 'data_events': events})
        controls.append({'index': index, 'before': old_control, 'after': control[:]})
        p2s.append({'index': index, 'before': old_p2, 'after': p2})
        current = after
    expected.update(classification='IndependentNativeBelowSecondP2Reference_NoCpuObservation', terminal=current,
        instruction_count=39, stop_before_pc=_pc(0x5688, program_kind), write_count=write_count,
        control_final=control, final_p2=p2, control_instruction_retirements=4, below_instruction_retirements=18,
        p2_instruction_retirements=2, control_step_snapshots=controls, p2_step_snapshots=p2s,
        cycle_accounting=deepcopy(CYCLE_ACCOUNTING))
    expected['ordered_data_events'] = [deepcopy(event) for step in expected['steps'] for event in step['data_events']]
    expected['logical_read_count'] = sum(event['operation'] == 'Read' for event in expected['ordered_data_events'])
    expected['ram_logical_read_count'] = sum(event['operation'] == 'Read' and event['address'] >= 128 for event in expected['ordered_data_events'])
    logical, raw, _ = _data_expected(case, expected, program_kind)
    for address, name, retired in ((36, 'p2', (17, 38)), (64, 'control', (18, 24))):
        journal, generations = [], []
        for event in logical:
            if event['phase'] != 'Functional' or event['address'] != address:
                continue
            linked = [item for item in raw if item['logical_ordinal'] == event['ordinal']]
            _equal(len(linked), 1, 'peripheral/one_raw_link')
            journal.append({'ordinal': len(journal), 'pc': event['pc'], 'address': address, 'width': 8,
                'operation': event['operation'], 'value': event['value'], 'logical_ordinal': event['ordinal'],
                'raw_ordinal': linked[0]['ordinal'], 'write_ordinal': event['write_ordinal'],
                'native_write_ordinal': event['write_ordinal'] - 55 if event['write_ordinal'] is not None else None,
                'same_value': event['same_value'], 'space': 'PeripheralP2' if name == 'p2' else 'PeripheralControl'})
            if event['operation'] == 'Write':
                generations.append({'machine_id': 1, 'writer_pc': event['pc'], 'retired_instruction': retired[len(generations)],
                    'generation_ordinal': len(generations) + 1, 'native_write_ordinal': event['write_ordinal'] - 55,
                    'logical_write_ordinal': event['write_ordinal'], 'raw_write_ordinal': linked[0]['write_ordinal'], 'value': event['value']})
        _equal(len(generations), 2, 'peripheral/two_actual_writer_identities')
        expected['peripheral_' + name + '_journal'] = journal
        expected[name + '_generation'] = generations[0]
        expected[name + '_generations'] = generations
        expected['second_' + name + '_generation'] = generations[1]
    return expected


def _decoded(step, kind):
    pc = int(step['native_site_identity'], 16)
    if pc not in TAIL_FORM:
        return previous._decoded(step, kind)
    n8 = n16 = addr16 = rel8 = 0
    addresses = {0x55D3: 0x0116, 0x562C: 0x0110, 0x5631: 0x0112, 0x565D: 0x0114,
                 0x565F: 0x0110, 0x5671: 0x0116, 0x567E: 0x018F, 0x5685: 0x012A}
    if pc in addresses: n8 = _address(addresses[pc], kind) & 255
    if pc == 0x55D5: n8 = 64
    if pc == 0x5682: n8 = 36
    if pc == 0x5680: n8 = 15
    if pc in (0x55D8, 0x562E): n16 = 1
    if pc == 0x5633: addr16 = _pc(0x565D, kind)
    if pc in (0x55DB, 0x5661, 0x5673): rel8 = SUCCESSORS[pc] - pc - step['length']
    return {'index': step['decoded_index'], 'mnemonic': step['mnemonic'], 'len': step['length'],
        'dd_before': step['before']['cpu']['dd'], 'dd_after': step['after']['cpu']['dd'],
        'dd_after_option': True if pc in (0x55D8, 0x562E, 0x565F) else False if pc == 0x5671 else None,
        'cycles': 4 if pc == 0x5661 else TAIL_FORM[pc][4], 'n8': n8, 'n8_alt': 0, 'n16': n16,
        'n16_alt': 0, 's8': 0, 'rel8': rel8, 'addr16': addr16}


def _permissions(expected):
    # SFRs/AL aliases use separately sealed capabilities, never generic RAM rights.
    ram = {'steps': [{**step, 'data_events': [event for event in step['data_events'] if event['address'] >= 128]}
                     for step in expected['steps']]}
    value = BASE_ORACLE._permissions(ram)
    for row in value['writes']:
        if row['access']['address'] == _address(0x012A, expected['program_kind']):
            row['rmw_required'] = True
    return value


def public_program_identity():
    """Independently composed403-byte invented segment; never read ROM bytes."""
    payload, hashes = bytearray([0xA5] * 403), {}
    for pc in previous.previous.previous.corpus.PREFIX:
        raw = previous.previous.previous._public_prefix_extent(pc)
        offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw
        hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    earlier = previous.previous.previous.previous
    for request in earlier._public_requests():
        pc = request.origin_pc - earlier.corpus.PUBLIC_PC_DELTA
        operands = tuple(encoder.TargetPC16(item.value - earlier.corpus.PUBLIC_PC_DELTA + corpus.PUBLIC_PC_DELTA)
            if type(item) is encoder.TargetPC16 else item for item in request.typed_operands)
        value = encoder.encode_instruction(encoder.EncoderRequest(request.reviewed_form_id, operands,
            request.incoming_dd, _pc(pc, 'public_fixture')))
        if type(value) is not encoder.EncodedInstruction:
            raise ValueError('IndependentPublicPrefixEncodingRefused')
        raw = value.encoded_bytes; offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    for pc in previous.previous.P2_FORM:
        raw = previous.previous._p2_encoding(pc); offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    for pc in previous.CONTROL_FORM:
        raw = previous.control_extent(pc, 'public_fixture'); offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    for pc in TAIL_FORM:
        raw = downstream_extent(pc, 'public_fixture'); offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw; hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    _equal(len(hashes), 49, 'public/closed49')
    return {'program_base': corpus.PUBLIC_BASE, 'program_end_exclusive': corpus.PUBLIC_BASE + 403,
        'program_sha256': sha256(payload).hexdigest(), 'source_binding': None, 'selected_extent_sha256': hashes}


def compare_observation(case, actual, program_kind='private', program_identity=None):
    expected = expected_case(case, program_kind)
    if program_identity is None and program_kind == 'public_fixture':
        program_identity = public_program_identity()
    _closed(program_identity, ('program_base', 'program_end_exclusive', 'program_sha256', 'source_binding', 'selected_extent_sha256'), 'program')
    _equal(program_identity['program_base'], _pc(corpus.ENTRY_PC, program_kind), 'program/base')
    _equal(program_identity['program_end_exclusive'], _pc(0x5688, program_kind), 'program/end')
    _equal(set(program_identity['selected_extent_sha256']), {str(_pc(pc, program_kind)) for pc in FORM}, 'program/closed49')
    for digest in [program_identity['program_sha256'], *program_identity['selected_extent_sha256'].values()]:
        if type(digest) is not str or BASE_ORACLE.SHA.fullmatch(digest) is None:
            raise ValueError('FrozenProgramShaRequired')
    if program_kind == 'public_fixture':
        _equal(program_identity, public_program_identity(), 'program/independent_public_encoding')
    _closed(actual, ('kind', 'case_id', 'family', 'internal_sf', 'accepted', 'error', 'actual_successful_step_returns', 'report'), 'observation')
    for key, value in {'kind': 'below_second_p2_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None, 'actual_successful_step_returns': case['budget']}.items():
        _equal(actual[key], value, 'observation/' + key)
    report = actual['report']
    _closed(report, ('classification', 'source_binding', 'program_node_count', 'path', 'entry', 'current', 'full_psw', 'steps',
        'completed', 'positive_completed', 'boundary_only', 'actual_handoff_observed', 'native_predecessor_retirements',
        'algorithm_retirements', 'stop_before_pc', 'audit', 'p2_snapshot', 'p2_initial', 'p2_final',
        'p2_instruction_retirements', 'peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots', 'control_snapshot', 'control_initial', 'control_final',
        'control_instruction_retirements', 'peripheral_control_journal', 'control_generation', 'control_step_snapshots', 'below_instruction_retirements',
        'p2_generations', 'control_generations', 'second_p2_generation', 'second_control_generation'), 'report')
    fixed = {'classification': corpus.MODE if program_kind == 'private' else 'ExplicitInventedPublicBelowSecondP2Fixture',
        'source_binding': program_identity['source_binding'], 'program_node_count': 49, 'path': case['path'],
        'full_psw': expected['terminal']['full_psw'], 'completed': True, 'positive_completed': True, 'boundary_only': False,
        'actual_handoff_observed': True, 'native_predecessor_retirements': 6,
        'algorithm_retirements': 10, 'stop_before_pc': expected['stop_before_pc'],
        'p2_snapshot': case['p2_snapshot'], 'p2_initial': expected['initial_p2'], 'p2_final': expected['final_p2'],
        'p2_instruction_retirements': 2, 'control_snapshot': case['control_snapshot'],
        **{key: expected[key] for key in ('control_initial', 'control_final', 'control_instruction_retirements',
            'peripheral_control_journal', 'control_generation', 'control_step_snapshots')},
        **{key: expected[key] for key in ('peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots',
            'below_instruction_retirements', 'p2_generations', 'control_generations', 'second_p2_generation', 'second_control_generation')}}
    for key, value in fixed.items():
        _equal(report[key], value, 'report/' + key)
    if type(report['steps']) is not list or len(report['steps']) != case['budget']:
        raise ValueError('ExactP2HandoffStepRecordsRequired')
    # Explicit reviewed technical Bus canary, not actual output as an oracle.
    ram = [0xA5] * 3968
    for address, value in expected['entry']['owned_ram'].items():
        ram[int(address) - 128] = value
    for label, obligation in (('entry', expected['entry']), ('current', expected['terminal'])):
        BASE_ORACLE._snapshot(report[label], obligation, ram, label)
    logical, raw, spans = _data_expected(case, expected, program_kind)
    for index, (step, obligation) in enumerate(zip(report['steps'], expected['steps'])):
        _closed(step, ('index', 'node_identity', 'full_psw_before', 'full_psw_after', 'before', 'after', 'outcome',
                      'program_span', 'logical_span', 'raw_span'), 'step')
        _equal(step['index'], index + 1, 'step/index')
        _equal(step['node_identity'], f"ClosedSite_{obligation['pc']:04X}", 'step/node_identity')
        for which in ('before', 'after'):
            BASE_ORACLE._snapshot(step[which], obligation[which], ram, f'step/{index}/{which}')
            _equal(step['full_psw_' + which], obligation[which]['full_psw'], 'step/psw_' + which)
        for field in ('logical_span', 'raw_span'):
            _equal(step[field], spans[index][field], 'step/' + field)
        outcome = {'pc_before': obligation['pc'], 'pc_after': obligation['next_pc'], 'decoded_index': obligation['decoded_index'],
            'mnemonic': obligation['mnemonic'], 'len': obligation['length'], 'decoded': _decoded(obligation, program_kind),
            'selected_extent': [obligation['pc'], obligation['pc'] + obligation['length']],
            'selected_extent_sha256': program_identity['selected_extent_sha256'][str(obligation['pc'])], 'retired': True, 'external_exit': None}
        _equal(step['outcome'], outcome, 'step/outcome')
    audit = report['audit']
    _closed(audit, ('entry_pc', 'current_pc', 'program_base', 'program_end_exclusive', 'program_sha256', 'program_events',
        'data_events', 'raw_data_events', 'diagnostic_events', 'data_admission_refusals', 'permissions', 'phase', 'budget',
        'successful_retirements', 'step_calls', 'execution_calls', 'shared_execution_calls', 'sealed', 'terminal_reason', 'external_exit', 'first_fault'), 'audit')
    fields = {'entry_pc': _pc(corpus.ENTRY_PC, program_kind), 'current_pc': expected['stop_before_pc'],
        **{key: program_identity[key] for key in ('program_base', 'program_end_exclusive', 'program_sha256')},
        'data_events': logical, 'raw_data_events': raw, 'data_admission_refusals': [],
        'permissions': _permissions(expected), 'phase': 'Sealed', 'budget': case['budget'],
        'successful_retirements': case['budget'], 'step_calls': case['budget'], 'execution_calls': case['budget'],
        'shared_execution_calls': case['budget'], 'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached',
        'external_exit': None, 'first_fault': None}
    for key, value in fields.items():
        _equal(audit[key], value, 'audit/' + key)
    _equal(audit['diagnostic_events'], [{'ordinal': i, 'kind': 'RawRamSnapshot', 'range': [128, 4096], 'byte_count': 3968}
        for i in range(diagnostic_snapshot_count(case['budget']))], 'audit/diagnostics')
    BASE_ORACLE._program_events(audit['program_events'], list(zip(report['steps'], expected['steps'])), program_identity)
    return {'passed': True, 'expected': expected, 'comparison': {'classification': 'IndependentContinuousBelowSecondP2StateAndOrderedGenerationsValidated',
        'firstMismatch': None, 'retirements': case['budget'], 'path': case['path'], 'p2Retirements': 2,
        'oldP2': expected['initial_p2'], 'newP2': expected['final_p2'], 'sameValueP2Write': expected['same_value_p2_write'],
        'finalP2Zf': expected['final_p2_zf'], 'controlRetirements': expected['control_instruction_retirements'], 'belowRetirements': 18,
        'sameValueSecondP2Write': expected['peripheral_p2_journal'][-1]['same_value'],
        'p2Generations': expected['p2_generations'], 'controlGenerations': expected['control_generations'],
        'oldControl': expected['control_initial'], 'newControl': expected['control_final'],
        'sameValueControlWrite': expected['peripheral_control_journal'][-1]['same_value'],
        'initialNativeP2OwnerEstablished': False, 'initialNativeControlOwnerEstablished': False,
        'physicalExecutionClaimed': False, 'omittedActualFields': []}}
