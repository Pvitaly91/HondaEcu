"""Independent golden math plus fabricated comparator inputs; never CPU evidence."""
from copy import deepcopy
import unittest
from . import corpus, oracle


def invented_observation(case):
    expected = oracle.expected_case(case, 'public_fixture')
    identity = oracle.public_program_identity()
    def snapshot(state):
        ram = [0xA5] * 3968
        for address, value in state['owned_ram'].items():
            ram[int(address) - 128] = value
        return {'cpu': deepcopy(state['cpu']), 'ram': ram, 'ram_range': [128, 4096]}
    logical, raw, spans = oracle._data_expected(case, expected, 'public_fixture')
    steps, program = [], []
    for index, item in enumerate(expected['steps']):
        start = len(program)
        for address in range(item['pc'], item['pc'] + item['length']):
            program.append({'ordinal': len(program), 'pc': item['pc'], 'address': address,
                'segment_offset': address - identity['program_base'], 'instruction_offset': address - item['pc'],
                'acquired_purpose': 'ArchitecturalSelectedFetch', 'selection_association': None,
                'selected_length': item['length'], 'serviced': True, 'refusal': None})
        steps.append({'index': index + 1, 'node_identity': f"ClosedSite_{item['pc']:04X}",
            'full_psw_before': item['before']['full_psw'], 'full_psw_after': item['after']['full_psw'],
            'before': snapshot(item['before']), 'after': snapshot(item['after']), 'program_span': [start, len(program)],
            **spans[index], 'outcome': {'pc_before': item['pc'], 'pc_after': item['next_pc'],
                'decoded_index': item['decoded_index'], 'mnemonic': item['mnemonic'], 'len': item['length'],
                'decoded': oracle._decoded(item, 'public_fixture'), 'selected_extent': [item['pc'], item['pc'] + item['length']],
                'selected_extent_sha256': identity['selected_extent_sha256'][str(item['pc'])], 'retired': True, 'external_exit': None}})
    audit = {'entry_pc': 0x6400, 'current_pc': expected['stop_before_pc'],
        **{key: identity[key] for key in ('program_base', 'program_end_exclusive', 'program_sha256')},
        'program_events': program, 'data_events': logical, 'raw_data_events': raw,
        'diagnostic_events': [{'ordinal': i, 'kind': 'RawRamSnapshot', 'range': [128, 4096], 'byte_count': 3968}
            for i in range(oracle.diagnostic_snapshot_count(case['budget']))], 'data_admission_refusals': [],
        'permissions': oracle.BASE_ORACLE._permissions({'steps': expected['steps'][:corpus.previous.BUDGETS[case['path']] - 1]}),
        'phase': 'Sealed', 'budget': case['budget'], 'successful_retirements': case['budget'],
        'step_calls': case['budget'], 'execution_calls': case['budget'], 'shared_execution_calls': case['budget'],
        'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached', 'external_exit': None, 'first_fault': None}
    report = {'classification': 'ExplicitInventedPublicPostP2ControlFixture', 'source_binding': None,
        'program_node_count': 31, 'path': case['path'], 'entry': snapshot(expected['entry']), 'current': snapshot(expected['terminal']),
        'full_psw': expected['terminal']['full_psw'], 'steps': steps, 'completed': True, 'positive_completed': True,
        'boundary_only': False, 'actual_handoff_observed': True, 'native_predecessor_retirements': 6,
        'algorithm_retirements': corpus.previous.BUDGETS[case['path']] - 7, 'stop_before_pc': expected['stop_before_pc'], 'audit': audit,
        'p2_snapshot': deepcopy(case['p2_snapshot']), 'p2_initial': expected['initial_p2'], 'p2_final': expected['final_p2'],
        'p2_instruction_retirements': 1, 'control_snapshot': deepcopy(case['control_snapshot']),
        **{key: deepcopy(expected[key]) for key in ('control_initial', 'control_final', 'control_instruction_retirements',
            'peripheral_control_journal', 'control_generation', 'control_step_snapshots')},
        **{key: deepcopy(expected[key]) for key in
            ('peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots')}}
    return {'kind': 'post_p2_control_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None,
        'actual_successful_step_returns': case['budget'], 'report': report}


class OracleTests(unittest.TestCase):
    def test_sb_old_bit_zf_then_lb_xor_mb_distinct_flag_owners(self):
        seen = set()
        for case in corpus.iter_cases():
            if case['path'] != 'A':
                continue
            expected = oracle.expected_case(case)
            sb, lb, xor, mb = expected['steps'][-4:]
            old = case['control_snapshot']['tcon0']
            self.assertEqual(sb['after']['cpu']['zf'], not bool(old & 4))
            self.assertEqual(expected['control_final'], [old | 4, case['control_snapshot']['trnsit_implemented_flags']])
            value = lb['before']['owned_ram'][str(0x018E)]
            self.assertEqual(lb['after']['cpu']['a'] & 255, value)
            self.assertEqual(lb['after']['cpu']['zf'], value == 0)
            self.assertFalse(lb['after']['cpu']['dd'])
            self.assertEqual(xor['after']['cpu']['a'] & 255, value ^ 255)
            self.assertEqual(xor['after']['cpu']['zf'], value == 255)
            self.assertEqual(mb['after']['cpu']['cf'], bool((value ^ 255) & 128))
            self.assertEqual(mb['after']['cpu']['zf'], xor['after']['cpu']['zf'])
            self.assertEqual([event['operation'] for event in sb['data_events']], ['Read', 'Read', 'Write'])
            self.assertEqual(mb['data_events'][0]['address'], 6)
            self.assertEqual(mb['data_events'][0]['value'], value ^ 255)
            for step in (sb, lb, xor, mb):
                self.assertEqual(step['after']['cpu']['a'] >> 8, step['before']['cpu']['a'] >> 8)
                self.assertEqual(step['after']['cpu']['hc'], step['before']['cpu']['hc'])
            seen.add(sb['after']['cpu']['zf'])
        self.assertEqual(seen, {True, False})

    def test_trnsit_high_bits_are_read_ones_not_storage_and_zf_uses_byte(self):
        seen = set()
        for case in corpus.iter_cases():
            if case['path'] == 'A':
                continue
            expected = oracle.expected_case(case)
            step = expected['steps'][-1]
            initial = case['control_snapshot']['trnsit_implemented_flags']
            self.assertEqual(step['data_events'][0]['value'], 0xF0 | initial)
            self.assertEqual(step['data_events'][1]['value'], (0xF0 | initial) & 0xFB)
            self.assertEqual(expected['control_final'][1], initial & 11)
            self.assertEqual(expected['control_generation']['value'], initial & 11)
            self.assertFalse(step['after']['cpu']['zf'])
            for field in ('a', 'cf', 'hc', 'dd', 'psw_other', 'ssp', 'lrb'):
                self.assertEqual(step['after']['cpu'][field], step['before']['cpu'][field])
            seen.add(initial)
        self.assertEqual(seen, set(range(16)))

    def test_p2_generation_and_ram_preserved_across_closed_control_tail(self):
        for case in corpus.iter_cases():
            expected = oracle.expected_case(case)
            self.assertEqual(expected['p2_generation']['retired_instruction'], corpus.previous.BUDGETS[case['path']])
            self.assertEqual(expected['control_generation']['retired_instruction'], corpus.previous.BUDGETS[case['path']] + 1)
            self.assertEqual(expected['control_generation']['generation_ordinal'], 1)
            self.assertEqual(expected['control_generation']['native_write_ordinal'], 8 if case['path'] == 'D' else 6)
            self.assertEqual(expected['control_generation']['raw_write_ordinal'], 89 if case['path'] == 'D' else 87)
            self.assertEqual(expected['terminal']['owned_ram'], expected['steps'][-1]['before']['owned_ram'])
            self.assertEqual(expected['terminal']['cpu']['pc'], corpus.TERMINALS[case['path']])
            logical, raw, spans = oracle._data_expected(case, expected, 'private')
            self.assertFalse(any(row['address'] == 6 for row in raw))
            if case['path'] == 'A':
                self.assertEqual(spans[-1]['raw_span'][0], spans[-1]['raw_span'][1])
                self.assertEqual(len([row for row in logical if row['address'] == 6]), 1)

    def test_cycles_are_retained_software_fields_with_separate_primary_authority(self):
        self.assertEqual(oracle.CYCLE_ACCOUNTING['softwareDiagnosticCounterDelta'], 6)
        self.assertEqual(oracle.CYCLE_ACCOUNTING['primaryManualIntCycles'], 7)
        self.assertFalse(oracle.CYCLE_ACCOUNTING['timingEquivalenceEstablished'])
        self.assertEqual({row['nativePC']: row['manufacturerInt'] for row in oracle.CYCLE_ACCOUNTING['controlInstructions']},
            {0x5599: 8, 0x55C8: 9, 0x55CB: 4, 0x55CD: 4, 0x55CF: 7})
        self.assertEqual(oracle.public_program_identity()['program_end_exclusive'], 0x64DD)
        self.assertEqual(len(oracle.public_program_identity()['selected_extent_sha256']), 31)

    def test_full_invented_observations_validate_all_fields(self):
        for path in 'ABCD':
            case = next(case for case in corpus.iter_cases() if case['path'] == path)
            self.assertTrue(oracle.compare_observation(case, invented_observation(case), 'public_fixture')['passed'])

    def test_intermediate_flags_alias_journals_generations_and_budget_mutations_refuse(self):
        case = next(corpus.iter_cases())
        original = invented_observation(case)
        mutations = [
            lambda x: x['report']['steps'][-4].update(full_psw_after=x['report']['steps'][-4]['full_psw_after'] ^ 0x4000),
            lambda x: x['report']['steps'][-1]['after']['cpu'].update(cf=not x['report']['steps'][-1]['after']['cpu']['cf']),
            lambda x: x['report']['steps'][-1]['after']['cpu'].update(hc=not x['report']['steps'][-1]['after']['cpu']['hc']),
            lambda x: x['report']['steps'][-1]['after']['cpu'].update(dd=not x['report']['steps'][-1]['after']['cpu']['dd']),
            lambda x: x['report']['steps'][-4]['outcome'].update(pc_after=x['report']['steps'][-4]['outcome']['pc_after'] + 1),
            lambda x: x['report']['peripheral_control_journal'].pop(0),
            lambda x: x['report']['peripheral_control_journal'][-1].update(same_value=True),
            lambda x: x['report']['control_generation'].update(native_write_ordinal=5),
            lambda x: x['report']['control_generation'].update(machine_id=2),
            lambda x: x['report']['p2_generation'].update(retired_instruction=case['budget']),
            lambda x: x['report']['control_step_snapshots'][-4].update(before=[0, 0]),
            lambda x: x['report']['audit']['raw_data_events'].append({'address': 6}),
            lambda x: x['report']['audit'].update(budget=case['budget'] + 1),
            lambda x: x['report'].update(stop_before_pc=0x64DE),
            lambda x: x['report']['audit']['data_events'][-1].update(address=65),
            lambda x: x['report']['steps'][-1]['outcome']['decoded'].update(cycles=6),
            lambda x: x['report'].update(firmwareReady=True),
        ]
        for mutate in mutations:
            actual = deepcopy(original)
            mutate(actual)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                oracle.compare_observation(case, actual, 'public_fixture')

        # Corrupt the actual-observation read value in ALL three linked
        # representations: the comparator must use independently expected F0.
        trnsit_case = next(case for case in corpus.iter_cases() if case['path'] == 'B')
        trnsit_actual = invented_observation(trnsit_case)
        event = trnsit_actual['report']['peripheral_control_journal'][0]
        event['value'] &= 15
        trnsit_actual['report']['audit']['data_events'][event['logical_ordinal']]['value'] &= 15
        trnsit_actual['report']['audit']['raw_data_events'][event['raw_ordinal']]['value'] &= 15
        with self.assertRaises(ValueError):
            oracle.compare_observation(trnsit_case, trnsit_actual, 'public_fixture')
        stored_high_bits = invented_observation(trnsit_case)
        stored_high_bits['report']['control_final'][1] |= 0xF0
        stored_high_bits['report']['control_step_snapshots'][-1]['after'][1] |= 0xF0
        stored_high_bits['report']['control_generation']['value'] |= 0xF0
        with self.assertRaises(ValueError):
            oracle.compare_observation(trnsit_case, stored_high_bits, 'public_fixture')
        # A same-value store leaves state unchanged, but its semantic event and
        # fresh generation must remain. Suppress these actual-observation rows.
        same_case = next(case for case in corpus.iter_cases()
            if case['path'] == 'A' and case['control_snapshot']['tcon0'] == 0x87)
        same_actual = invented_observation(same_case)
        write = same_actual['report']['peripheral_control_journal'][-1]
        self.assertEqual((write['operation'], write['same_value']), ('Write', True))
        same_actual['report']['peripheral_control_journal'].pop()
        same_actual['report']['audit']['data_events'].pop(write['logical_ordinal'])
        same_actual['report']['audit']['raw_data_events'].pop(write['raw_ordinal'])
        same_actual['report']['control_generation'] = None
        with self.assertRaises(ValueError):
            oracle.compare_observation(same_case, same_actual, 'public_fixture')

    def test_consistently_forged_unowned_entry_ram_cannot_define_its_own_oracle(self):
        case = next(corpus.iter_cases())
        actual = invented_observation(case)
        snapshots = [actual['report']['entry'], actual['report']['current']]
        snapshots += [step[which] for step in actual['report']['steps'] for which in ('before', 'after')]
        for snapshot in snapshots:
            snapshot['ram'][0x0300 - 128] ^= 1
        with self.assertRaises(ValueError):
            oracle.compare_observation(case, actual, 'public_fixture')


if __name__ == '__main__':
    unittest.main()
