"""Independent M2bu mathematics plus one manufacturer-defined P2 byte RMW.

No actual observation supplies expected AL, flags, P2 storage or generation.
The frozen old oracle is used only for expected math and neutral exact-field
validators; its closed execution acceptance and source guards are not changed.
"""
from copy import deepcopy
from hashlib import sha256

import independent_encoder as encoder
from original_rom_boundary.decode import decode_extent
from native_entry_continuity import oracle as previous
from . import corpus

P2_FORM = {0x5596: (350, 'ANDB N8, A', 'andb-zero-a'),
           0x55C5: (1647, 'ORB N8, A', 'orb-zero-a')}
FORM = {**previous.FORM, **{pc: row[:2] for pc, row in P2_FORM.items()}}
_equal, _closed = previous._equal, previous._closed
CYCLE_ACCOUNTING = {
    'softwareDiagnosticCounterDelta': 6,
    'primaryManualIntCycles': 7,
    'classification': 'UserApprovedDiagnosticAccounting_NotManufacturerTimingEquivalence',
    'basis': 'RetainedHistoricalFallbackTwoPerInstructionByte_ThreeByteForm',
    'semanticOrCanonicalFieldsOmitted': [],
    'timingEquivalenceEstablished': False,
    'physicalTimeClaimed': False}


def _pc(pc, kind):
    return pc + (corpus.PUBLIC_PC_DELTA if kind == 'public_fixture' else 0)


def diagnostic_snapshot_count(retirements):
    if type(retirements) is not int or retirements not in corpus.BUDGETS.values():
        raise ValueError('ClosedM2bvDiagnosticRetirementDomain')
    return 4 * retirements + 4


def ownership(pc):
    return {'P2InitialSource': 'TechnicalArchitecturalSnapshot', 'P2InitialNativeOwner': 'NotEstablished',
        'P2RmwWriter': 'ActualProductionInstruction', 'P2RmwWriterPC': pc,
        'P2FinalGeneration': 'VerifiedWithinTechnicalSession', 'PhysicalP2Owner': 'NotEstablished',
        'PhysicalOutputEffect': 'NotObserved'}


def _prefix_expected(case, kind):
    expected = deepcopy(previous.expected_case(corpus.scalar_case(case), kind))
    if kind == 'public_fixture':
        delta = corpus.PUBLIC_BASE - previous.corpus.PUBLIC_BASE
        expected['stop_before_pc'] += delta
        for step in expected['steps']:
            step['pc'] += delta; step['next_pc'] += delta
            step['before']['cpu']['pc'] += delta; step['after']['cpu']['pc'] += delta
            for event in step['data_events']:
                event['pc'] += delta
        # The old result aliases top-level entry/terminal and event dictionaries
        # to its trace. Rebuild these views, rather than translating them twice.
        expected['entry'] = deepcopy(expected['steps'][0]['before'])
        expected['terminal'] = deepcopy(expected['steps'][-1]['after'])
        expected['ordered_data_events'] = [deepcopy(event) for step in expected['steps'] for event in step['data_events']]
    return expected


def expected_case(case, program_kind='private'):
    corpus.validate_case(case)
    if program_kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2bvProgramKindRequired')
    expected = _prefix_expected(case, program_kind)
    before = deepcopy(expected['terminal'])
    native_pc = corpus.P2_PCS[case['path']]
    pc, stop = _pc(native_pc, program_kind), _pc(corpus.TERMINALS[case['path']], program_kind)
    _equal(before['cpu']['pc'], pc, 'independent/P2_reached_from_predecessors')
    old, a, psw = case['p2_snapshot']['value'], before['cpu']['a'], before['full_psw']
    value = (old | (a & 255)) if case['path'] == 'A' else (old & (a & 255))
    after = deepcopy(before)
    after['full_psw'] = (psw & ~0x4000) | (int(value == 0) << 14)
    # The user approved retaining the historical software fallback counter.
    # The primary manual's INT7 row is a separate authority: this diagnostic6
    # is compared exactly, without claiming manufacturer timing equivalence.
    after['cpu'].update(pc=stop, zf=value == 0,
                        cycles=before['cpu']['cycles'] + CYCLE_ACCOUNTING['softwareDiagnosticCounterDelta'],
                        instructions=before['cpu']['instructions'] + 1)
    ram_writes = expected['write_count']
    raw_ram_write_bytes = sum(event['width'] // 8 for event in expected['ordered_data_events'] if event['operation'] == 'Write')
    events = [
        {'pc': pc, 'instruction_index': P2_FORM[native_pc][0], 'address': 36, 'width': 8,
         'operation': 'Read', 'requested_value': None, 'value': old, 'old_value': None,
         'write_ordinal': None, 'same_value': None},
        {'pc': pc, 'instruction_index': P2_FORM[native_pc][0], 'address': 36, 'width': 8,
         'operation': 'Write', 'requested_value': value, 'value': value, 'old_value': old,
         'write_ordinal': 48 + ram_writes, 'same_value': value == old}]
    expected['steps'].append({'index': case['budget'], 'native_site_identity': f'{native_pc:04X}',
        'pc': pc, 'next_pc': stop, 'form': P2_FORM[native_pc][2], 'decoded_index': P2_FORM[native_pc][0],
        'mnemonic': P2_FORM[native_pc][1], 'length': 3, 'branch_taken': None,
        'before': before, 'after': after, 'data_events': events})
    expected['ordered_data_events'].extend(events)
    expected.update(classification='IndependentNativeP2HandoffReference_NoCpuObservation', terminal=after,
        instruction_count=case['budget'], ram_write_count=ram_writes,
        ram_logical_read_count=expected['logical_read_count'], write_count=ram_writes + 1,
        logical_read_count=expected['logical_read_count'] + 1, stop_before_pc=stop,
        initial_p2=old, final_p2=value, same_value_p2_write=value == old, final_p2_zf=value == 0,
        cycle_accounting=deepcopy(CYCLE_ACCOUNTING),
        p2_instruction_retirements=1, ownership=ownership(pc),
        initial_p2_provenance=corpus.PROVENANCE, initial_native_p2_owner='NotEstablished')
    logical, raw, spans = _data_expected(case, expected, program_kind)
    first_logical, first_raw = spans[-1]['logical_span'][0], spans[-1]['raw_span'][0]
    expected['peripheral_p2_journal'] = [
        {'ordinal': 0, 'pc': pc, 'address': 36, 'width': 8, 'operation': 'Read', 'value': old,
         'logical_ordinal': first_logical, 'raw_ordinal': first_raw, 'write_ordinal': None,
         'native_write_ordinal': None, 'same_value': None, 'space': 'PeripheralP2'},
        {'ordinal': 1, 'pc': pc, 'address': 36, 'width': 8, 'operation': 'Write', 'value': value,
         'logical_ordinal': first_logical + 1, 'raw_ordinal': first_raw + 1,
         'write_ordinal': 48 + ram_writes, 'native_write_ordinal': ram_writes,
         'same_value': value == old, 'space': 'PeripheralP2'}]
    expected['p2_generation'] = {'machine_id': 1, 'writer_pc': pc, 'retired_instruction': case['budget'],
        'generation_ordinal': 1, 'native_write_ordinal': ram_writes,
        'logical_write_ordinal': 48 + ram_writes, 'raw_write_ordinal': 80 + raw_ram_write_bytes, 'value': value}
    expected['p2_step_snapshots'] = [{'index': index + 1, 'before': old,
        'after': value if index + 1 == case['budget'] else old} for index in range(case['budget'])]
    _equal(logical[-1]['old_value'], old, 'P2_old_is_peripheral_storage_not_RAM24')
    _equal(raw[-1]['write_ordinal'], expected['p2_generation']['raw_write_ordinal'], 'P2_raw_native_write_counter')
    return expected


def _data_expected(case, expected, kind):
    # Reuse arithmetic journal expansion only. P2 remains a separate peripheral
    # storage operation linked to its actual DATA service rows, never RAM seed.
    logical, raw, spans = previous._data_expected(corpus.scalar_case(case), expected, kind)
    if kind == 'public_fixture':
        for event in logical[:48]:
            event['pc'] = corpus.PUBLIC_BASE
    return logical, raw, spans


def _p2_encoding(native_pc):
    raw = bytes((0xC5, 0x24, 0xE1 if native_pc == 0x55C5 else 0xD1))
    for dd in (0, 1):
        decoded = decode_extent(raw, _pc(native_pc, 'public_fixture'), dd)
        _equal(decoded['formId'], P2_FORM[native_pc][2], 'manufacturer/P2_public_form')
        _equal(decoded['length'], 3, 'manufacturer/P2_public_length')
    return raw


def public_program_identity():
    """Transient independent211-byte invented fixture; never return a payload."""
    payload, hashes = bytearray([0xA5] * 211), {}
    for pc in previous.corpus.PREFIX:
        raw = previous._public_prefix_extent(pc)
        for dd in ((1,) if pc == 0x54FC else (0, 1)):
            _equal(decode_extent(raw, _pc(pc, 'public_fixture'), dd)['formId'], previous.PREFIX_FORM[pc][2], 'public/predecessor_form')
        offset = pc - corpus.ENTRY_PC
        payload[offset:offset + len(raw)] = raw
        hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    earlier = previous.previous
    for request in earlier._public_requests():
        native_pc = request.origin_pc - earlier.corpus.PUBLIC_PC_DELTA
        operands = tuple(encoder.TargetPC16(item.value - earlier.corpus.PUBLIC_PC_DELTA + corpus.PUBLIC_PC_DELTA)
            if type(item) is encoder.TargetPC16 else item for item in request.typed_operands)
        translated = encoder.EncoderRequest(request.reviewed_form_id, operands, request.incoming_dd, _pc(native_pc, 'public_fixture'))
        encoded = encoder.encode_instruction(translated)
        if type(encoded) is not encoder.EncodedInstruction:
            raise ValueError('IndependentInventedP2PrefixEncodingRefused')
        offset = native_pc - corpus.ENTRY_PC
        payload[offset:offset + encoded.length] = encoded.encoded_bytes
        hashes[str(_pc(native_pc, 'public_fixture'))] = sha256(encoded.encoded_bytes).hexdigest()
    for pc in P2_FORM:
        raw = _p2_encoding(pc); offset = pc - corpus.ENTRY_PC
        payload[offset:offset + 3] = raw
        hashes[str(_pc(pc, 'public_fixture'))] = sha256(raw).hexdigest()
    return {'program_base': corpus.PUBLIC_BASE, 'program_end_exclusive': corpus.PUBLIC_BASE + 211,
        'program_sha256': sha256(payload).hexdigest(), 'source_binding': None, 'selected_extent_sha256': hashes}


def _decoded(step, kind):
    pc = int(step['native_site_identity'], 16)
    if pc not in P2_FORM:
        return previous._decoded(step, kind)
    return {'index': P2_FORM[pc][0], 'mnemonic': P2_FORM[pc][1], 'len': 3,
        'dd_before': step['before']['cpu']['dd'], 'dd_after': step['after']['cpu']['dd'],
        'dd_after_option': None, 'cycles': CYCLE_ACCOUNTING['softwareDiagnosticCounterDelta'], 'n8': 36, 'n8_alt': 0, 'n16': 0,
        'n16_alt': 0, 's8': 0, 'rel8': 0, 'addr16': 0}


def compare_observation(case, actual, program_kind='private', program_identity=None):
    expected = expected_case(case, program_kind)
    if program_identity is None and program_kind == 'public_fixture':
        program_identity = public_program_identity()
    _closed(program_identity, ('program_base', 'program_end_exclusive', 'program_sha256', 'source_binding', 'selected_extent_sha256'), 'program')
    _equal(program_identity['program_base'], _pc(corpus.ENTRY_PC, program_kind), 'program/base')
    _equal(program_identity['program_end_exclusive'], _pc(0x55C8, program_kind), 'program/end')
    _equal(set(program_identity['selected_extent_sha256']), {str(_pc(pc, program_kind)) for pc in FORM}, 'program/closed26')
    for digest in [program_identity['program_sha256'], *program_identity['selected_extent_sha256'].values()]:
        if type(digest) is not str or previous.previous.SHA.fullmatch(digest) is None:
            raise ValueError('FrozenProgramShaRequired')
    if program_kind == 'public_fixture':
        _equal(program_identity, public_program_identity(), 'program/independent_public_encoding')
    _closed(actual, ('kind', 'case_id', 'family', 'internal_sf', 'accepted', 'error', 'actual_successful_step_returns', 'report'), 'observation')
    for key, value in {'kind': 'p2_handoff_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None, 'actual_successful_step_returns': case['budget']}.items():
        _equal(actual[key], value, 'observation/' + key)
    report = actual['report']
    _closed(report, ('classification', 'source_binding', 'program_node_count', 'path', 'entry', 'current', 'full_psw', 'steps',
        'completed', 'positive_completed', 'boundary_only', 'actual_handoff_observed', 'native_predecessor_retirements',
        'algorithm_retirements', 'stop_before_pc', 'audit', 'p2_snapshot', 'p2_initial', 'p2_final',
        'p2_instruction_retirements', 'peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots'), 'report')
    fixed = {'classification': corpus.MODE if program_kind == 'private' else 'ExplicitInventedPublicP2HandoffFixture',
        'source_binding': program_identity['source_binding'], 'program_node_count': 26, 'path': case['path'],
        'full_psw': expected['terminal']['full_psw'], 'completed': True, 'positive_completed': True, 'boundary_only': False,
        'actual_handoff_observed': True, 'native_predecessor_retirements': 6,
        'algorithm_retirements': case['budget'] - 7, 'stop_before_pc': expected['stop_before_pc'],
        'p2_snapshot': case['p2_snapshot'], 'p2_initial': expected['initial_p2'], 'p2_final': expected['final_p2'],
        'p2_instruction_retirements': 1, **{key: expected[key] for key in ('peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots')}}
    for key, value in fixed.items():
        _equal(report[key], value, 'report/' + key)
    if type(report['steps']) is not list or len(report['steps']) != case['budget']:
        raise ValueError('ExactP2HandoffStepRecordsRequired')
    ram = report['entry']['ram']
    for label, obligation in (('entry', expected['entry']), ('current', expected['terminal'])):
        previous.previous._snapshot(report[label], obligation, ram, label)
    logical, raw, spans = _data_expected(case, expected, program_kind)
    for index, (step, obligation) in enumerate(zip(report['steps'], expected['steps'])):
        _closed(step, ('index', 'node_identity', 'full_psw_before', 'full_psw_after', 'before', 'after', 'outcome',
                      'program_span', 'logical_span', 'raw_span'), 'step')
        _equal(step['index'], index + 1, 'step/index')
        _equal(step['node_identity'], f"ClosedSite_{obligation['pc']:04X}", 'step/node_identity')
        for which in ('before', 'after'):
            previous.previous._snapshot(step[which], obligation[which], ram, f'step/{index}/{which}')
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
        'permissions': previous.previous._permissions({'steps': expected['steps'][:-1]}), 'phase': 'Sealed', 'budget': case['budget'],
        'successful_retirements': case['budget'], 'step_calls': case['budget'], 'execution_calls': case['budget'],
        'shared_execution_calls': case['budget'], 'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached',
        'external_exit': None, 'first_fault': None}
    for key, value in fields.items():
        _equal(audit[key], value, 'audit/' + key)
    _equal(audit['diagnostic_events'], [{'ordinal': i, 'kind': 'RawRamSnapshot', 'range': [128, 4096], 'byte_count': 3968}
        for i in range(diagnostic_snapshot_count(case['budget']))], 'audit/diagnostics')
    previous.previous._program_events(audit['program_events'], list(zip(report['steps'], expected['steps'])), program_identity)
    return {'passed': True, 'expected': expected, 'comparison': {'classification': 'IndependentContinuousP2StateAndOrderedGenerationValidated',
        'firstMismatch': None, 'retirements': case['budget'], 'path': case['path'], 'p2Retirements': 1,
        'oldP2': expected['initial_p2'], 'newP2': expected['final_p2'], 'sameValueP2Write': expected['same_value_p2_write'],
        'finalP2Zf': expected['final_p2_zf'], 'initialNativeP2OwnerEstablished': False, 'physicalExecutionClaimed': False, 'omittedActualFields': []}}
