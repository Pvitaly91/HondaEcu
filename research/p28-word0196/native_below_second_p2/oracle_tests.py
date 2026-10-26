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
        'permissions': oracle._permissions(expected),
        'phase': 'Sealed', 'budget': case['budget'], 'successful_retirements': case['budget'],
        'step_calls': case['budget'], 'execution_calls': case['budget'], 'shared_execution_calls': case['budget'],
        'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached', 'external_exit': None, 'first_fault': None}
    report = {'classification': 'ExplicitInventedPublicBelowSecondP2Fixture', 'source_binding': None,
        'program_node_count': 49, 'path': case['path'], 'entry': snapshot(expected['entry']), 'current': snapshot(expected['terminal']),
        'full_psw': expected['terminal']['full_psw'], 'steps': steps, 'completed': True, 'positive_completed': True,
        'boundary_only': False, 'actual_handoff_observed': True, 'native_predecessor_retirements': 6,
        'algorithm_retirements': 10, 'stop_before_pc': expected['stop_before_pc'], 'audit': audit,
        'p2_snapshot': deepcopy(case['p2_snapshot']), 'p2_initial': expected['initial_p2'], 'p2_final': expected['final_p2'],
        'p2_instruction_retirements': 2, 'control_snapshot': deepcopy(case['control_snapshot']),
        **{key: deepcopy(expected[key]) for key in ('control_initial', 'control_final', 'control_instruction_retirements',
            'peripheral_control_journal', 'control_generation', 'control_step_snapshots')},
        **{key: deepcopy(expected[key]) for key in
            ('peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots', 'below_instruction_retirements',
             'p2_generations', 'control_generations', 'second_p2_generation', 'second_control_generation')}}
    return {'kind': 'below_second_p2_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None,
        'actual_successful_step_returns': case['budget'], 'report': report}



class OracleTests(unittest.TestCase):
    def test_exact39_sequence_word_owners_and_native_jne(self):
        for case in corpus.iter_cases():
            e = oracle.expected_case(case)
            self.assertEqual(e['instruction_count'], 39)
            self.assertEqual([int(s['native_site_identity'], 16) for s in e['steps'][21:]], list(corpus.DOWNSTREAM))
            self.assertEqual(e['steps'][32]['branch_taken'], True)
            self.assertEqual(e['steps'][32]['before']['cpu']['a'], 1)
            self.assertFalse(e['steps'][32]['before']['cpu']['zf'])
            for pc, address in ((0x562C, 0x0110), (0x5631, 0x0112), (0x565D, 0x0114)):
                s = next(s for s in e['steps'] if s['native_site_identity'] == f'{pc:04X}')
                self.assertEqual(s['before']['owned_ram'][str(address)], 0xA5)
                self.assertEqual(s['data_events'][0]['width'], 16)
                self.assertEqual(s['data_events'][0]['value'], 1)
                self.assertEqual([s['after']['owned_ram'][str(address+i)] for i in (0,1)], [1,0])

    def test_actual_reachable_rol_pair_and_all_noncarry_retention(self):
        seen = set()
        for case in corpus.iter_cases():
            e = oracle.expected_case(case)
            s = e['steps'][21]
            x = case['data'][str(0x018E)]
            t = (~(((x << 1) | (x >> 7)) & 255)) & 255
            self.assertEqual(s['before']['cpu']['a'], t)
            self.assertEqual(s['before']['cpu']['cf'], bool(t & 128))
            self.assertEqual(s['after']['cpu']['a'], ((t << 1) | (t >> 7)) & 255)
            self.assertEqual(s['after']['cpu']['cf'], bool(t & 128))
            self.assertEqual(s['before']['full_psw'] & 0x7FFF, s['after']['full_psw'] & 0x7FFF)
            self.assertEqual(s['after']['cpu']['a'] >> 8, 0)
            seen.add(s['before']['cpu']['cf'])
        self.assertEqual(seen, {False, True})

    def test_two_tcon_generations_preserve_storage_and_exact_read_order(self):
        for case in corpus.iter_cases():
            e = oracle.expected_case(case)
            initial = case['control_snapshot']['tcon0']
            self.assertEqual([g['value'] for g in e['control_generations']], [initial | 4, initial & 251])
            self.assertEqual([g['native_write_ordinal'] for g in e['control_generations']], [6,8])
            self.assertEqual([g['writer_pc'] for g in e['control_generations']], [0x55C8,0x55D5])
            self.assertEqual([x['operation'] for x in e['peripheral_control_journal']], ['Read','Read','Write']*2)
            self.assertFalse(e['steps'][23]['after']['cpu']['zf'])
            self.assertEqual(e['peripheral_control_journal'][3]['value'], initial | 4)

    def test_second_p2_is_same_value_but_fresh_actual_writer(self):
        for case in corpus.iter_cases():
            e = oracle.expected_case(case)
            journal = e['peripheral_p2_journal']
            self.assertEqual([g['writer_pc'] for g in e['p2_generations']], [0x55C5,0x5682])
            self.assertEqual([g['generation_ordinal'] for g in e['p2_generations']], [1,2])
            self.assertEqual([g['native_write_ordinal'] for g in e['p2_generations']], [5,12])
            self.assertEqual([g['logical_write_ordinal'] for g in e['p2_generations']], [60,67])
            self.assertEqual([g['raw_write_ordinal'] for g in e['p2_generations']], [93,103])
            self.assertEqual(journal[1]['value'], journal[2]['value'])
            self.assertEqual(journal[2]['value'], journal[3]['value'])
            self.assertTrue(journal[3]['same_value'])
            self.assertEqual(e['steps'][37]['before']['cpu']['a'] & 255, 15)
            self.assertFalse(e['steps'][37]['after']['cpu']['zf'])

    def test_terminal_bit_clear_and_context_retention(self):
        for case in corpus.iter_cases():
            e = oracle.expected_case(case)
            last = e['steps'][-1]
            self.assertEqual(e['terminal']['cpu']['pc'], 0x5688)
            self.assertEqual(last['after']['owned_ram'][str(0x012A)], case['data'][str(0x012A)] & 127)
            self.assertEqual(last['after']['cpu']['zf'], not bool(case['data'][str(0x012A)] & 128))
            self.assertEqual(last['before']['full_psw'] & ~0x4000, last['after']['full_psw'] & ~0x4000)
            self.assertEqual(e['terminal']['cpu']['ssp'], case['entry']['ssp'])
            self.assertEqual(sum(x['softwareDiagnosticCounterDelta'] for x in oracle.CYCLE_ACCOUNTING['belowInstructions']),101)
            self.assertEqual(sum(x['manufacturerInt'] for x in oracle.CYCLE_ACCOUNTING['belowInstructions']),102)

    def test_complete_public_comparison_accepts_only_full_independent_structure(self):
        for case in list(corpus.iter_cases())[::4]:
            actual = invented_observation(case)
            value = oracle.compare_observation(case, actual, 'public_fixture')
            self.assertTrue(value['passed'])
            self.assertEqual(value['comparison']['omittedActualFields'], [])
            self.assertFalse(value['comparison']['physicalExecutionClaimed'])

    def test_functional_state_branch_word_and_generation_mutations_refuse(self):
        case = next(corpus.iter_cases())
        base = invented_observation(case)
        changes = [
            (('report','steps',21,'after','cpu','cf'), True),
            (('report','steps',21,'after','cpu','dd'), True),
            (('report','steps',21,'after','cpu','hc'), True),
            (('report','steps',21,'after','cpu','a'), 0x1234),
            (('report','steps',21,'full_psw_after'), 0),
            (('report','steps',23,'before','cpu','a'), 99),
            (('report','steps',23,'outcome','pc_after'), 0x6593),
            (('report','steps',32,'outcome','pc_after'), 0x656E),
            (('report','steps',32,'outcome','decoded','dd_before'), False),
            (('report','steps',37,'before','cpu','a'), 1),
            (('report','peripheral_p2_journal',2,'value'), 0),
            (('report','peripheral_p2_journal',3,'same_value'), False),
            (('report','p2_generations',1,'generation_ordinal'), 1),
            (('report','second_p2_generation','native_write_ordinal'), 5),
            (('report','control_generations',1,'generation_ordinal'), 1),
            (('report','second_control_generation','value'), 0x87),
            (('report','control_step_snapshots',23,'before',0), 0x83),
            (('report','stop_before_pc'), 0x6594),
            (('report','audit','shared_execution_calls'), 40),
            (('report','steps',38,'outcome','retired'), False)]
        for path, changed in changes:
            actual = deepcopy(base); target = actual
            for part in path[:-1]: target = target[part]
            # Each mutation must actually change the fabricated observation.
            if target[path[-1]] == changed:
                changed = not changed if type(changed) is bool else changed ^ 1
            target[path[-1]] = changed
            with self.subTest(path=path), self.assertRaises(ValueError):
                oracle.compare_observation(case, actual, 'public_fixture')

    def test_second_same_value_write_cannot_be_dropped_or_reuse_g1(self):
        case = next(corpus.iter_cases()); base = invented_observation(case)
        for change in ('drop','stale','order','extra'):
            actual = deepcopy(base); report = actual['report']
            if change == 'drop':
                write = report['peripheral_p2_journal'].pop()
                report['audit']['data_events'].pop(write['logical_ordinal'])
                report['audit']['raw_data_events'].pop(write['raw_ordinal'])
            elif change == 'stale':
                report['second_p2_generation'] = deepcopy(report['p2_generation'])
                report['p2_generations'][1] = deepcopy(report['p2_generation'])
            elif change == 'order':
                report['peripheral_p2_journal'][3]['native_write_ordinal'] = 5
            else:
                report['peripheral_control_journal'].append(deepcopy(report['peripheral_control_journal'][-1]))
            with self.subTest(change=change), self.assertRaises(ValueError):
                oracle.compare_observation(case, actual, 'public_fixture')

    def test_unowned_ram_cannot_define_its_own_expected_frame(self):
        case = next(corpus.iter_cases()); actual = invented_observation(case)
        snapshots=[actual['report']['entry'],actual['report']['current']]
        snapshots += [step[side] for step in actual['report']['steps'] for side in ('before','after')]
        for snapshot in snapshots: snapshot['ram'][0x0300-128] ^= 1
        with self.assertRaises(ValueError): oracle.compare_observation(case,actual,'public_fixture')

    def test_word_raw_byte_relation_and_terminal_extra_retirement_refuse(self):
        case = next(corpus.iter_cases()); base = invented_observation(case)
        changed = deepcopy(base)
        row = next(x for x in changed['report']['audit']['raw_data_events'] if x['address']==0x0112 and x['operation']=='Write' and x['logical_ordinal']>=55)
        row['value'] ^= 1
        with self.assertRaises(ValueError): oracle.compare_observation(case,changed,'public_fixture')
        changed=deepcopy(base);changed['report']['steps'].append(deepcopy(changed['report']['steps'][-1]));changed['actual_successful_step_returns']=40
        with self.assertRaises(ValueError): oracle.compare_observation(case,changed,'public_fixture')

if __name__ == '__main__':
    unittest.main()
