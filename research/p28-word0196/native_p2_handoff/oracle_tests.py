"""Independent math and explicitly fabricated comparator fixtures; no CPU.

The fixture below is invented validation input, never runtime evidence. Golden
arithmetic/context assertions are separate from structural mutation checks.
"""
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
        'permissions': oracle.previous.previous._permissions({'steps': expected['steps'][:-1]}),
        'phase': 'Sealed', 'budget': case['budget'], 'successful_retirements': case['budget'],
        'step_calls': case['budget'], 'execution_calls': case['budget'], 'shared_execution_calls': case['budget'],
        'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached', 'external_exit': None, 'first_fault': None}
    report = {'classification': 'ExplicitInventedPublicP2HandoffFixture', 'source_binding': None,
        'program_node_count': 26, 'path': case['path'], 'entry': snapshot(expected['entry']), 'current': snapshot(expected['terminal']),
        'full_psw': expected['terminal']['full_psw'], 'steps': steps, 'completed': True, 'positive_completed': True,
        'boundary_only': False, 'actual_handoff_observed': True, 'native_predecessor_retirements': 6,
        'algorithm_retirements': case['budget'] - 7, 'stop_before_pc': expected['stop_before_pc'], 'audit': audit,
        'p2_snapshot': deepcopy(case['p2_snapshot']), 'p2_initial': expected['initial_p2'], 'p2_final': expected['final_p2'],
        'p2_instruction_retirements': 1, **{key: deepcopy(expected[key]) for key in
            ('peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots')}}
    return {'kind': 'p2_handoff_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None,
        'actual_successful_step_returns': case['budget'], 'report': report}


class OracleTests(unittest.TestCase):
    def test_explicit_diagnostic6_and_primary7_are_separate_authorities(self):
        self.assertEqual(oracle.CYCLE_ACCOUNTING, {
            'softwareDiagnosticCounterDelta': 6, 'primaryManualIntCycles': 7,
            'classification': 'UserApprovedDiagnosticAccounting_NotManufacturerTimingEquivalence',
            'basis': 'RetainedHistoricalFallbackTwoPerInstructionByte_ThreeByteForm',
            'semanticOrCanonicalFieldsOmitted': [], 'timingEquivalenceEstablished': False, 'physicalTimeClaimed': False})
        for path in 'ABCD':
            case = next(case for case in corpus.iter_cases() if case['path'] == path)
            expected = oracle.expected_case(case)
            p2 = expected['steps'][-1]
            self.assertEqual(expected['cycle_accounting'], oracle.CYCLE_ACCOUNTING)
            self.assertEqual(p2['after']['cpu']['cycles'] - p2['before']['cpu']['cycles'], 6)
            self.assertEqual(oracle._decoded(p2, 'private')['cycles'], 6)

    def test_or_golden_values_and_and_zero_samevalue_controls(self):
        cases = list(corpus.iter_cases())
        a_cases = [case for case in cases if case['path'] == 'A']
        self.assertEqual([oracle.expected_case(case)['final_p2'] for case in a_cases], [15, 15, 255, 255, 175, 175, 15, 15])
        for case in cases:
            expected = oracle.expected_case(case)
            terminal, prior = expected['terminal'], expected['steps'][-1]['before']
            self.assertEqual(terminal['cpu']['a'] >> 8, case['data'][str(0x0197)])
            self.assertEqual(terminal['owned_ram'], prior['owned_ram'])
            self.assertEqual(terminal['full_psw'] & ~0x4000, prior['full_psw'] & ~0x4000)
            self.assertEqual(terminal['cpu']['a'], prior['cpu']['a'])
            self.assertEqual(terminal['cpu']['dd'], False)
            self.assertEqual(terminal['cpu']['pc'], corpus.TERMINALS[case['path']])
            self.assertEqual(expected['p2_generation']['native_write_ordinal'], 7 if case['path'] == 'D' else 5)
            self.assertEqual(expected['p2_generation']['raw_write_ordinal'], 88 if case['path'] == 'D' else 86)
            if case['path'] != 'A' and case['p2_snapshot']['value'] in (0, 240):
                self.assertTrue(expected['same_value_p2_write'])
        self.assertEqual(sum(oracle.expected_case(case)['final_p2_zf'] for case in cases), 6)

    def test_public_26_nodes_domain_and_no_double_pc_translation(self):
        identity = oracle.public_program_identity()
        self.assertEqual(identity['program_base'], 0x6400)
        self.assertEqual(identity['program_end_exclusive'], 0x64D3)
        self.assertEqual(len(identity['selected_extent_sha256']), 26)
        self.assertIsNone(identity['source_binding'])
        for path in 'ABCD':
            case = next(case for case in corpus.iter_cases() if case['path'] == path)
            expected = oracle.expected_case(case, 'public_fixture')
            self.assertEqual(expected['entry']['cpu']['pc'], 0x6400)
            self.assertEqual(expected['steps'][0]['pc'], 0x6400)
            self.assertEqual(expected['ordered_data_events'][0]['pc'], 0x6400)
            self.assertEqual(expected['terminal']['cpu']['pc'], 0x64D3 if path == 'A' else 0x64A4)

    def test_complete_invented_observations_and_functional_peripheral_counts(self):
        for path in 'ABCD':
            case = next(case for case in corpus.iter_cases() if case['path'] == path)
            actual = invented_observation(case)
            compared = oracle.compare_observation(case, actual, 'public_fixture')
            self.assertTrue(compared['passed'])
            events = actual['report']['audit']['data_events']
            self.assertFalse(any(row['address'] == 36 for row in events[:48]))
            self.assertEqual([row['operation'] for row in events if row['address'] == 36], ['Read', 'Write'])
            self.assertEqual(len(actual['report']['peripheral_p2_journal']), 2)
            self.assertNotIn(36, actual['report']['audit']['permissions']['raw_reads'])

    def test_semantic_state_context_journal_and_generation_mutations_refused(self):
        case = next(corpus.iter_cases())
        original = invented_observation(case)
        mutations = [
            (('report', 'p2_initial'), 165), (('report', 'p2_final'), 0),
            (('report', 'p2_instruction_retirements'), 2), (('report', 'stop_before_pc'), 0x64D0),
            (('report', 'p2_generation', 'machine_id'), 2), (('report', 'p2_generation', 'generation_ordinal'), 0),
            (('report', 'p2_generation', 'native_write_ordinal'), 0), (('report', 'p2_generation', 'raw_write_ordinal'), 80),
            (('report', 'ownership', 'P2InitialNativeOwner'), 'ObservedNative'),
            (('report', 'ownership', 'PhysicalP2Owner'), 'Established'),
            (('report', 'current', 'cpu', 'a'), 0), (('report', 'current', 'cpu', 'cf'), False),
            (('report', 'current', 'cpu', 'hc'), True), (('report', 'current', 'cpu', 'dd'), True),
            (('report', 'current', 'cpu', 'zf'), True), (('report', 'current', 'cpu', 'lrb'), 0),
            (('report', 'audit', 'shared_execution_calls'), 0), (('report', 'audit', 'sealed'), False)]
        for path, value in mutations:
            changed = deepcopy(original); target = changed
            for field in path[:-1]:
                target = target[field]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                oracle.compare_observation(case, changed, 'public_fixture')
        for field in ('peripheral_p2_journal', 'p2_step_snapshots'):
            changed = deepcopy(original); changed['report'][field].pop()
            with self.subTest(field=field), self.assertRaises(ValueError):
                oracle.compare_observation(case, changed, 'public_fixture')

    def test_samevalue_write_must_still_create_a_generation(self):
        case = next(case for case in corpus.iter_cases() if case['path'] == 'B' and case['p2_snapshot']['value'] == 0)
        actual = invented_observation(case)
        self.assertTrue(oracle.compare_observation(case, actual, 'public_fixture')['comparison']['sameValueP2Write'])
        for change in ('remove', 'flag', 'old'):
            altered = deepcopy(actual)
            if change == 'remove':
                altered['report']['p2_generation'] = None
            elif change == 'flag':
                altered['report']['peripheral_p2_journal'][1]['same_value'] = False
            else:
                altered['report']['audit']['data_events'][-1]['old_value'] = 165
            with self.subTest(change=change), self.assertRaises(ValueError):
                oracle.compare_observation(case, altered, 'public_fixture')


if __name__ == '__main__':
    unittest.main()
