"""Independent golden math and fabricated comparator inputs; zero CPU execution."""
from copy import deepcopy
import unittest
from . import corpus,oracle


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
                'segment_offset': address - next(w['base'] for w in identity['program_windows'] if w['base']<=address<w['end_exclusive']), 'instruction_offset': address - item['pc'],
                'acquired_purpose': 'ArchitecturalSelectedFetch', 'selection_association': None,
                'selected_length': item['length'], 'serviced': True, 'refusal': None})
        steps.append({'index': index + 1, 'node_identity': f"ClosedSite_{item['pc']:04X}",
            'full_psw_before': item['before']['full_psw'], 'full_psw_after': item['after']['full_psw'],
            'before': snapshot(item['before']), 'after': snapshot(item['after']), 'program_span': [start, len(program)],
            **spans[index], 'outcome': {'pc_before': item['pc'], 'pc_after': item['next_pc'],
                'decoded_index': item['decoded_index'], 'mnemonic': item['mnemonic'], 'len': item['length'],
                'decoded': oracle._decoded(item, 'public_fixture'), 'selected_extent': [item['pc'], item['pc'] + item['length']],
                'selected_extent_sha256': identity['selected_extent_sha256'][str(item['pc'])], 'retired': True, 'external_exit': None}})
    audit = {'entry_pc': corpus.PUBLIC_CALLER, 'current_pc': expected['stop_before_pc'],
        **{key: identity[key] for key in ('program_base', 'program_end_exclusive')},
        'program_sha256':identity['program_windows'][1]['sha256'],
        'program_events': program, 'data_events': logical, 'raw_data_events': raw,
        'diagnostic_events': [{'ordinal': i, 'kind': 'RawRamSnapshot', 'range': [128, 4096], 'byte_count': 3968}
            for i in range(oracle.diagnostic_snapshot_count(case['budget']))], 'data_admission_refusals': [],
        'permissions': oracle._permissions(expected),
        'phase': 'Sealed', 'budget': case['budget'], 'successful_retirements': case['budget'],
        'step_calls': case['budget'], 'execution_calls': case['budget'], 'shared_execution_calls': case['budget'],
        'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached', 'external_exit': None, 'first_fault': None}
    report = {'classification': 'ExplicitInventedPublicCalRtFrameContinuityFixture', 'source_binding': None,
        'program_node_count': 51, 'path': case['path'], 'entry': snapshot(expected['entry']), 'current': snapshot(expected['terminal']),
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
    outer={'body':report,'program_windows':identity['program_windows'],'program_identity':identity['program_sha256'],
        **{key:deepcopy(expected[key]) for key in ('stack_frame','stack_return','stack_journal','all_native_journal')},
        'frame_status':'CallerFrameConsumedByActualRT','initial_canary_classification':'TechnicalPreexistingCanaryNotFrame',
        'completed':True,'cal_instruction_retirements':1,'body_instruction_retirements':39,'rt_instruction_retirements':1,
        'post_return_instruction_retirements':0,'cpu_bus_instances':1}
    return {'kind': 'cal_rt_continuity_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None,
        'actual_successful_step_returns': case['budget'], 'report': outer}


class OracleTests(unittest.TestCase):
    def test_cal_word_uses_old_ssp_le_and_rt_increment_before_read(self):
        for kind in ('private','public_fixture'):
            for case in corpus.iter_cases():
                e=oracle.expected_case(case,kind); cal,rt=e['steps'][0],e['steps'][-1]
                ssp=case['entry']['ssp']; ret=corpus.PUBLIC_RETURN if kind=='public_fixture' else corpus.RETURN_PC
                self.assertEqual((len(e['steps']),e['instruction_count']),(41,41))
                self.assertEqual((cal['before']['cpu']['ssp'],cal['after']['cpu']['ssp']),(ssp,ssp-2))
                self.assertEqual((rt['before']['cpu']['ssp'],rt['after']['cpu']['ssp']),(ssp-2,ssp))
                self.assertEqual([cal['after']['owned_ram'][str(ssp+i)] for i in (0,1)],[ret & 255,ret >> 8])
                self.assertEqual((cal['data_events'][0]['address'],rt['data_events'][0]['address']),(ssp,ssp))
                self.assertEqual(rt['next_pc'],ret)
                self.assertEqual((cal['after']['cpu']['sf'],rt['after']['cpu']['sf']),(False,False))
                for step in (cal,rt):
                    for field in ('a','lrb'):
                        self.assertEqual(step['before']['cpu'][field],step['after']['cpu'][field])
                    self.assertEqual(step['before']['full_psw'],step['after']['full_psw'])
                self.assertEqual((e['stack_frame']['native_write_ordinal'],e['stack_frame']['logical_write_ordinal']),(0,57))
                self.assertEqual(e['stack_frame']['raw_write_ordinals'],[89,90])
                self.assertEqual([g['native_write_ordinal'] for g in e['p2_generations']],[6,13])
                self.assertEqual(len([r for r in e['all_native_journal'] if r[4]==1]),15)
                self.assertEqual(e['all_native_journal'][-1],[0,rt['pc'],ssp,16,0,ret])

    def test_equal_preexisting_word_requires_fresh_writer(self):
        cases=[c for c in corpus.iter_cases() if c['stack_canary']['value']==corpus.RETURN_PC]
        self.assertEqual(len(cases),4)
        for case in cases:
            e=oracle.expected_case(case)
            self.assertTrue(e['stack_frame']['same_value'])
            self.assertEqual(e['stack_frame']['generation_ordinal'],1)
            self.assertEqual(e['stack_frame']['source_generation'],'CurrentExecutionCAL')
            self.assertEqual(e['stack_return']['consumed_writer_pc'],0x063B)

    def test_two_independent_public_windows_never_include_return(self):
        i=oracle.public_program_identity(); windows=i['program_windows']
        self.assertEqual([(w['base'],w['byte_count']) for w in windows],[(0x2000,3),(0x6400,404)])
        self.assertEqual(len(i['selected_extent_sha256']),51)
        self.assertNotIn(str(0x2003),i['selected_extent_sha256'])

    def test_full_independent_comparator_accepts_fabricated_schema_only(self):
        case=next(corpus.iter_cases())
        result=oracle.compare_observation(case,invented_observation(case),'public_fixture')
        self.assertTrue(result['passed']); self.assertEqual(result['comparison']['omittedActualFields'],[])

    def test_thirty_two_semantic_actual_mutations_refused(self):
        case=next(corpus.iter_cases()); good=invented_observation(case)
        paths=[
          ('actual_successful_step_returns',),('report','completed'),('report','cpu_bus_instances'),
          ('report','cal_instruction_retirements'),('report','body_instruction_retirements'),('report','rt_instruction_retirements'),
          ('report','post_return_instruction_retirements'),('report','stack_frame','writer_pc'),
          ('report','stack_frame','machine_id'),('report','stack_frame','address'),('report','stack_frame','width'),
          ('report','stack_frame','return_pc'),('report','stack_frame','logical_write_ordinal'),
          ('report','stack_frame','native_write_ordinal'),('report','stack_frame','generation_ordinal'),
          ('report','stack_frame','all_native_ordinal'),('report','stack_return','consumer_pc'),
          ('report','stack_return','ssp_before'),('report','stack_return','ssp_after'),
          ('report','stack_return','consumed_writer_pc'),('report','stack_return','consumed_logical_write_ordinal'),
          ('report','body','stop_before_pc'),('report','body','full_psw'),
          ('report','body','audit','budget'),('report','body','audit','execution_calls'),
          ('report','body','steps',0,'after','cpu','ssp'),('report','body','steps',0,'after','cpu','a'),
          ('report','body','steps',0,'after','cpu','lrb'),('report','body','steps',0,'after','cpu','sf'),
          ('report','body','steps',40,'after','cpu','ssp'),('report','body','steps',40,'after','cpu','pc'),
          ('report','body','steps',40,'after','cpu','a')]
        self.assertEqual(len(paths),32)
        for path in paths:
            changed=deepcopy(good); node=changed
            for key in path[:-1]: node=node[key]
            old=node[path[-1]]; node[path[-1]]=not old if type(old) is bool else old+1
            with self.subTest(path=path),self.assertRaises(ValueError):
                oracle.compare_observation(case,changed,'public_fixture')


    def test_nine_additional_actual_journal_and_restore_mutations_refused(self):
        # Separate from the documented32 mutations and actual Rust refusals.
        case=next(corpus.iter_cases());good=invented_observation(case)
        names=('reversed_raw_write_ordinals','reversed_raw_event_ordinals','wrong_little_endian_cal_value',
            'missing_actual_cal_writer','same_value_intervening_native_writer','fake_rt_psw_restore',
            'wrong_retained_rt_lrb','wrong_rt_internal_sf','reordered_raw_cal_bytes')
        for name in names:
            changed=deepcopy(good);report=changed['report'];body=report['body'];rt=body['steps'][-1]
            if name=='reversed_raw_write_ordinals':report['stack_frame']['raw_write_ordinals'].reverse()
            elif name=='reversed_raw_event_ordinals':report['stack_frame']['raw_ordinals'].reverse()
            elif name=='wrong_little_endian_cal_value':
                v=report['stack_journal'][0]['value'];report['stack_journal'][0]['value']=(v & 255)<<8 | v>>8
            elif name=='missing_actual_cal_writer':
                body['audit']['data_events'].pop(report['stack_frame']['logical_ordinal'])
            elif name=='same_value_intervening_native_writer':
                row=deepcopy(report['all_native_journal'][0]);row[1]=corpus.PUBLIC_BASE
                report['all_native_journal'].insert(-1,row)
            elif name=='fake_rt_psw_restore':
                restored=body['steps'][0]['full_psw_before']
                rt['full_psw_after']=restored if restored!=rt['full_psw_after'] else restored ^ 0x8000
            elif name=='wrong_retained_rt_lrb':rt['after']['cpu']['lrb']^=1
            elif name=='wrong_rt_internal_sf':rt['after']['cpu']['sf']=True
            elif name=='reordered_raw_cal_bytes':
                raw=body['audit']['raw_data_events'];a,b=report['stack_frame']['raw_ordinals'];raw[a],raw[b]=raw[b],raw[a]
            self.assertNotEqual(changed,good)
            with self.subTest(mutation=name),self.assertRaises(ValueError):
                oracle.compare_observation(case,changed,'public_fixture')


    def test_partial_frame_at1_or40_steps_cannot_be_promoted_to_positive(self):
        case=next(corpus.iter_cases());good=invented_observation(case)
        for count in (1,40):
            partial=deepcopy(good);report=partial['report'];body=report['body']
            partial['actual_successful_step_returns']=count
            report['completed']=True;partial['accepted']=True
            report['body_instruction_retirements']=count-1;report['rt_instruction_retirements']=0
            report['stack_return']=None;report['stack_journal']=report['stack_journal'][:1]
            report['frame_status']='CallerFrameEstablishedPendingReturn'
            body['steps']=body['steps'][:count];body['current']=deepcopy(body['steps'][-1]['after'])
            body['completed']=body['positive_completed']=True
            for field in ('successful_retirements','step_calls','execution_calls','shared_execution_calls'):
                body['audit'][field]=count
            self.assertIsNotNone(report['stack_frame']);self.assertIsNone(report['stack_return'])
            self.assertEqual(body['current']['cpu']['ssp'],case['entry']['ssp']-2)
            with self.subTest(completedSteps=count),self.assertRaises(ValueError):
                oracle.compare_observation(case,partial,'public_fixture')
