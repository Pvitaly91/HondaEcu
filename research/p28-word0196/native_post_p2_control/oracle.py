"""Independent M2bv mathematics and manufacturer-defined post-P2 effects.

No production CPU result, ROM payload or actual trace supplies expected values.
Software diagnostic counts are a separately pinned source-level observation
contract; they are never promoted to physical ECU time.
"""
from copy import deepcopy
from hashlib import sha256

import independent_encoder as encoder
from native_p2_handoff import oracle as previous
from . import corpus

# Opaque decoder indices identify the retained integration forms only; the
# arithmetic/flags below come from primary ISA3-27/70/77/127/175 and M2ab.
CONTROL_FORM = {
    0x5599: (382, "ANDB N'8, #N8", 'andb-zero-imm8', 4, 8),
    0x55C8: (1994, 'SB N8.2', 'sb-zero-bit2', 3, 9),
    0x55CB: (747, 'LB A, off N8', 'lb-a-page', 2, 4),
    0x55CD: (2557, 'XORB A, #N8', 'xorb-a-imm8', 2, 4),
    0x55CF: (894, 'MB C, N8.7', 'mb-c-zero-bit7', 3, 7),
}
FORM = {**previous.FORM, **{pc: row[:2] for pc, row in CONTROL_FORM.items()}}
_equal, _closed = previous._equal, previous._closed
BASE_ORACLE = previous.previous.previous
CYCLE_ACCOUNTING = {**deepcopy(previous.CYCLE_ACCOUNTING),
    'controlInstructions': [{'nativePC': pc, 'softwareDiagnosticCounterDelta': row[4],
        'manufacturerInt': row[4]} for pc, row in sorted(CONTROL_FORM.items())],
    'overallClassification': 'DiagnosticCycleTimingEquivalenceNotEstablished'}


def _pc(pc, kind):
    return pc + (corpus.PUBLIC_PC_DELTA if kind == 'public_fixture' else 0)


def _address(address, kind):
    return corpus.PUBLIC_DATA.get(address, address) if kind == 'public_fixture' else address


def diagnostic_snapshot_count(retirements):
    if type(retirements) is not int or retirements not in corpus.BUDGETS.values():
        raise ValueError('ClosedM2bwDiagnosticRetirementDomain')
    return 4 * retirements + 4


def control_extent(pc, kind):
    """Independently typed manufacturer code cells and explicit operands."""
    choices = {0x5599: bytes((0xC5, 0x46, 0xD0, 0xFB)),
        0x55C8: bytes((0xC5, 0x40, 0x1A)),
        0x55CB: bytes((0xF4, _address(0x018E, kind) & 255)),
        0x55CD: bytes((0xF6, 0xFF)), 0x55CF: bytes((0xC5, 0x06, 0x2F))}
    if kind not in ('private', 'public_fixture') or pc not in choices:
        raise ValueError('ClosedFiveControlFormEncodingRequired')
    return choices[pc]


def _event(pc, decoded_index, address, operation, value, old=None, ordinal=None):
    writing = operation == 'Write'
    return {'pc': pc, 'instruction_index': decoded_index, 'address': address, 'width': 8,
        'operation': operation, 'requested_value': value if writing else None, 'value': value,
        'old_value': old if writing else None, 'write_ordinal': ordinal if writing else None,
        'same_value': value == old if writing else None}


def _data_expected(case, expected, kind):
    ram_case = previous.corpus.scalar_case(corpus.scalar_case(case))
    logical, raw = previous.previous._seed_events(ram_case, kind)
    if kind == 'public_fixture':
        for event in logical:
            event['pc'] = corpus.PUBLIC_BASE
    spans, raw_writes = [], len(raw)
    for step in expected['steps']:
        start = len(logical), len(raw)
        for event in step['data_events']:
            ordinal = len(logical)
            logical.append({'ordinal': ordinal, 'phase': 'Functional', **event, 'serviced': True, 'refusal': None})
            # ACC006 is a CPU-owned logical alias, not a physical RAM byte.
            if step['native_site_identity'] == '55CF' and event['address'] == 6:
                continue
            for offset in range(event['width'] // 8):
                writing = event['operation'] == 'Write'
                value = event['value'] >> (8 * offset) & 255
                old = event['old_value'] >> (8 * offset) & 255 if writing else None
                raw.append({'ordinal': len(raw), 'logical_ordinal': ordinal,
                    'address': event['address'] + offset, 'operation': event['operation'],
                    'requested_value': value if writing else None, 'value': value, 'old_value': old,
                    'write_ordinal': raw_writes if writing else None, 'same_value': old == value if writing else None,
                    'serviced': True, 'refusal': None})
                raw_writes += int(writing)
        spans.append({'logical_span': [start[0], len(logical)], 'raw_span': [start[1], len(raw)]})
    return logical, raw, spans


def expected_case(case, program_kind='private'):
    corpus.validate_case(case)
    if program_kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2bwProgramKindRequired')
    expected = deepcopy(previous.expected_case(corpus.scalar_case(case), program_kind))
    prefix_budget = corpus.previous.BUDGETS[case['path']]
    control = case['control_snapshot']
    current = deepcopy(expected['terminal'])
    storage = [control['tcon0'], control['trnsit_implemented_flags']]
    control_snapshots = [{'index': index + 1, 'before': storage[:], 'after': storage[:]}
        for index in range(prefix_budget)]
    tail = (0x55C8, 0x55CB, 0x55CD, 0x55CF) if case['path'] == 'A' else (0x5599,)
    write_count = expected['write_count']
    initial_storage = storage[:]
    for native_pc in tail:
        row = CONTROL_FORM[native_pc]
        pc, next_pc = _pc(native_pc, program_kind), _pc(native_pc + row[3], program_kind)
        _equal(current['cpu']['pc'], pc, 'independent/continuous_control_pc')
        before, after = deepcopy(current), deepcopy(current)
        old_storage = storage[:]
        a, psw = before['cpu']['a'], before['full_psw']
        events = []
        if native_pc == 0x55C8:
            old, value = storage[0], storage[0] | 4
            events = [_event(pc, row[0], 64, 'Read', old), _event(pc, row[0], 64, 'Read', old),
                _event(pc, row[0], 64, 'Write', value, old, 48 + write_count)]
            psw = psw & ~0x4000 | (int(not old & 4) << 14)
            storage[0] = value
            write_count += 1
        elif native_pc == 0x5599:
            old = 0xF0 | storage[1]
            value = old & 0xFB
            events = [_event(pc, row[0], 70, 'Read', old),
                _event(pc, row[0], 70, 'Write', value, old, 48 + write_count)]
            psw = psw & ~0x4000 | (int(value == 0) << 14)
            storage[1] = value & 15
            write_count += 1
        elif native_pc == 0x55CB:
            address = _address(0x018E, program_kind)
            value = before['owned_ram'][str(address)]
            events = [_event(pc, row[0], address, 'Read', value)]
            a = a & 0xFF00 | value
            psw = psw & ~(0x4000 | 0x1000) | (int(value == 0) << 14)
        elif native_pc == 0x55CD:
            a ^= 255
            psw = psw & ~0x4000 | (int(a & 255 == 0) << 14)
        else:
            events = [_event(pc, row[0], 6, 'Read', a & 255)]
            psw = psw & ~0x8000 | ((a & 0x80) << 8)
        after['full_psw'] = psw
        after['cpu'].update(a=a, cf=bool(psw & 0x8000), zf=bool(psw & 0x4000),
            hc=bool(psw & 0x2000), dd=bool(psw & 0x1000), psw_other=psw & 0x0337,
            pc=next_pc, instructions=before['cpu']['instructions'] + 1,
            cycles=before['cpu']['cycles'] + row[4])
        index = len(expected['steps']) + 1
        expected['steps'].append({'index': index, 'native_site_identity': f'{native_pc:04X}',
            'pc': pc, 'next_pc': next_pc, 'form': row[2], 'decoded_index': row[0],
            'mnemonic': row[1], 'length': row[3], 'branch_taken': None,
            'before': before, 'after': after, 'data_events': events})
        expected['ordered_data_events'].extend(events)
        control_snapshots.append({'index': index, 'before': old_storage, 'after': storage[:]})
        current = after
    _equal(len(expected['steps']), case['budget'], 'independent/exact_control_budget')
    expected.update(classification='IndependentNativePostP2ControlReference_NoCpuObservation', terminal=current,
        instruction_count=case['budget'], stop_before_pc=current['cpu']['pc'], write_count=write_count,
        logical_read_count=sum(event['operation'] == 'Read' for event in expected['ordered_data_events']),
        ram_logical_read_count=expected['ram_logical_read_count'] + int(case['path'] == 'A'),
        control_initial=initial_storage, control_final=storage[:], control_instruction_retirements=len(tail),
        control_step_snapshots=control_snapshots, cycle_accounting=deepcopy(CYCLE_ACCOUNTING))
    expected['p2_step_snapshots'].extend({'index': index, 'before': expected['final_p2'], 'after': expected['final_p2']}
        for index in range(prefix_budget + 1, case['budget'] + 1))
    logical, raw, _ = _data_expected(case, expected, program_kind)
    controlled = [event for event in logical if event['phase'] == 'Functional' and event['address'] in (64, 70)]
    journal = []
    for event in controlled:
        linked = [row for row in raw if row['logical_ordinal'] == event['ordinal']]
        _equal(len(linked), 1, 'control/one_actual_raw_link')
        journal.append({'ordinal': len(journal), 'pc': event['pc'], 'address': event['address'], 'width': 8,
            'operation': event['operation'], 'value': event['value'], 'logical_ordinal': event['ordinal'],
            'raw_ordinal': linked[0]['ordinal'], 'write_ordinal': event['write_ordinal'],
            'native_write_ordinal': event['write_ordinal'] - 48 if event['write_ordinal'] is not None else None,
            'same_value': event['same_value'], 'space': 'PeripheralControl'})
    write = next(event for event in journal if event['operation'] == 'Write')
    raw_write = raw[write['raw_ordinal']]
    expected['peripheral_control_journal'] = journal
    expected['control_generation'] = {'machine_id': 1, 'writer_pc': write['pc'],
        'retired_instruction': prefix_budget + 1, 'generation_ordinal': 1,
        'native_write_ordinal': write['native_write_ordinal'], 'logical_write_ordinal': write['write_ordinal'],
        'raw_write_ordinal': raw_write['write_ordinal'], 'value': storage[0] if case['path'] == 'A' else storage[1]}
    return expected


def _decoded(step, kind):
    pc = int(step['native_site_identity'], 16)
    if pc not in CONTROL_FORM:
        return previous._decoded(step, kind)
    n8 = {0x5599: 251, 0x55C8: 64, 0x55CB: _address(0x018E, kind) & 255,
          0x55CD: 255, 0x55CF: 6}[pc]
    return {'index': step['decoded_index'], 'mnemonic': step['mnemonic'], 'len': step['length'],
        'dd_before': step['before']['cpu']['dd'], 'dd_after': step['after']['cpu']['dd'],
        'dd_after_option': False if pc == 0x55CB else None, 'cycles': CONTROL_FORM[pc][4],
        'n8': n8, 'n8_alt': 70 if pc == 0x5599 else 0, 'n16': 0, 'n16_alt': 0,
        's8': 0, 'rel8': 0, 'addr16': 0}


def public_program_identity():
    """Transient221-byte independently invented encoding, never ROM input."""
    payload, hashes = bytearray([0xA5] * 221), {}
    for pc in previous.previous.corpus.PREFIX:
        raw = previous.previous._public_prefix_extent(pc)
        offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw
        hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    earlier = previous.previous.previous
    for request in earlier._public_requests():
        native_pc = request.origin_pc - earlier.corpus.PUBLIC_PC_DELTA
        operands = tuple(encoder.TargetPC16(item.value - earlier.corpus.PUBLIC_PC_DELTA + corpus.PUBLIC_PC_DELTA)
            if type(item) is encoder.TargetPC16 else item for item in request.typed_operands)
        translated = encoder.EncoderRequest(request.reviewed_form_id, operands, request.incoming_dd, _pc(native_pc, 'public_fixture'))
        encoded = encoder.encode_instruction(translated)
        if type(encoded) is not encoder.EncodedInstruction:
            raise ValueError('IndependentInventedPostP2PrefixEncodingRefused')
        offset = native_pc - corpus.ENTRY_PC
        payload[offset:offset + encoded.length] = encoded.encoded_bytes
        hashes[str(_pc(native_pc, 'public_fixture'))] = sha256(encoded.encoded_bytes).hexdigest()
    for pc in previous.P2_FORM:
        raw = previous._p2_encoding(pc)
        offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw
        hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    for pc in CONTROL_FORM:
        raw = control_extent(pc, 'public_fixture')
        offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw
        hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    return {'program_base': corpus.PUBLIC_BASE, 'program_end_exclusive': corpus.PUBLIC_BASE + 221,
        'program_sha256': sha256(payload).hexdigest(), 'source_binding': None, 'selected_extent_sha256': hashes}


def compare_observation(case, actual, program_kind='private', program_identity=None):
    expected = expected_case(case, program_kind)
    if program_identity is None and program_kind == 'public_fixture':
        program_identity = public_program_identity()
    _closed(program_identity, ('program_base', 'program_end_exclusive', 'program_sha256', 'source_binding', 'selected_extent_sha256'), 'program')
    _equal(program_identity['program_base'], _pc(corpus.ENTRY_PC, program_kind), 'program/base')
    _equal(program_identity['program_end_exclusive'], _pc(0x55D2, program_kind), 'program/end')
    _equal(set(program_identity['selected_extent_sha256']), {str(_pc(pc, program_kind)) for pc in FORM}, 'program/closed31')
    for digest in [program_identity['program_sha256'], *program_identity['selected_extent_sha256'].values()]:
        if type(digest) is not str or BASE_ORACLE.SHA.fullmatch(digest) is None:
            raise ValueError('FrozenProgramShaRequired')
    if program_kind == 'public_fixture':
        _equal(program_identity, public_program_identity(), 'program/independent_public_encoding')
    _closed(actual, ('kind', 'case_id', 'family', 'internal_sf', 'accepted', 'error', 'actual_successful_step_returns', 'report'), 'observation')
    for key, value in {'kind': 'post_p2_control_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None, 'actual_successful_step_returns': case['budget']}.items():
        _equal(actual[key], value, 'observation/' + key)
    report = actual['report']
    _closed(report, ('classification', 'source_binding', 'program_node_count', 'path', 'entry', 'current', 'full_psw', 'steps',
        'completed', 'positive_completed', 'boundary_only', 'actual_handoff_observed', 'native_predecessor_retirements',
        'algorithm_retirements', 'stop_before_pc', 'audit', 'p2_snapshot', 'p2_initial', 'p2_final',
        'p2_instruction_retirements', 'peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots', 'control_snapshot', 'control_initial', 'control_final',
        'control_instruction_retirements', 'peripheral_control_journal', 'control_generation', 'control_step_snapshots'), 'report')
    fixed = {'classification': corpus.MODE if program_kind == 'private' else 'ExplicitInventedPublicPostP2ControlFixture',
        'source_binding': program_identity['source_binding'], 'program_node_count': 31, 'path': case['path'],
        'full_psw': expected['terminal']['full_psw'], 'completed': True, 'positive_completed': True, 'boundary_only': False,
        'actual_handoff_observed': True, 'native_predecessor_retirements': 6,
        'algorithm_retirements': corpus.previous.BUDGETS[case['path']] - 7, 'stop_before_pc': expected['stop_before_pc'],
        'p2_snapshot': case['p2_snapshot'], 'p2_initial': expected['initial_p2'], 'p2_final': expected['final_p2'],
        'p2_instruction_retirements': 1, 'control_snapshot': case['control_snapshot'],
        **{key: expected[key] for key in ('control_initial', 'control_final', 'control_instruction_retirements',
            'peripheral_control_journal', 'control_generation', 'control_step_snapshots')},
        **{key: expected[key] for key in ('peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots')}}
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
        'permissions': BASE_ORACLE._permissions({'steps': expected['steps'][:corpus.previous.BUDGETS[case['path']] - 1]}), 'phase': 'Sealed', 'budget': case['budget'],
        'successful_retirements': case['budget'], 'step_calls': case['budget'], 'execution_calls': case['budget'],
        'shared_execution_calls': case['budget'], 'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached',
        'external_exit': None, 'first_fault': None}
    for key, value in fields.items():
        _equal(audit[key], value, 'audit/' + key)
    _equal(audit['diagnostic_events'], [{'ordinal': i, 'kind': 'RawRamSnapshot', 'range': [128, 4096], 'byte_count': 3968}
        for i in range(diagnostic_snapshot_count(case['budget']))], 'audit/diagnostics')
    BASE_ORACLE._program_events(audit['program_events'], list(zip(report['steps'], expected['steps'])), program_identity)
    return {'passed': True, 'expected': expected, 'comparison': {'classification': 'IndependentContinuousPostP2StateAndOrderedGenerationsValidated',
        'firstMismatch': None, 'retirements': case['budget'], 'path': case['path'], 'p2Retirements': 1,
        'oldP2': expected['initial_p2'], 'newP2': expected['final_p2'], 'sameValueP2Write': expected['same_value_p2_write'],
        'finalP2Zf': expected['final_p2_zf'], 'controlRetirements': expected['control_instruction_retirements'],
        'oldControl': expected['control_initial'], 'newControl': expected['control_final'],
        'sameValueControlWrite': expected['peripheral_control_journal'][-1]['same_value'],
        'initialNativeP2OwnerEstablished': False, 'initialNativeControlOwnerEstablished': False,
        'physicalExecutionClaimed': False, 'omittedActualFields': []}}
