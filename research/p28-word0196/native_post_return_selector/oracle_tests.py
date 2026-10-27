"""Independent golden state and fabricated comparator inputs; no CPU invocation."""
from collections import Counter
from copy import deepcopy
import unittest
from native_cal_rt_continuity import oracle as parent
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
    report = {'classification': 'ExplicitInventedPublicPostReturnSelectorFixture', 'source_binding': None,
        'program_node_count': 59, 'path': case['path'], 'entry': snapshot(expected['entry']), 'current': snapshot(expected['terminal']),
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
        'post_return_instruction_retirements':8,'cpu_bus_instances':1}
    selector_report={'prefix':outer,**{key:deepcopy(expected[key]) for key in (
        'selector_snapshot','initial_selector_generation','selector_initial','selector_final','selector_read','selector_generation',
        'history0128_before','history0128_after','history0128_selected_bit','history0128_rmw','history0128_generation',
        'local_r0_before','local_r0_final')},'post_return_instruction_retirements':8,'total_instruction_retirements':49,
        'completed':True,'selector_generation_available_for_future_reader':True,'native_next_event_handoff_verified':False,'branch064c_retired':False}
    return {'kind': 'post_return_selector_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None,
        'actual_successful_step_returns': case['budget'], 'report': selector_report}


class OracleTests(unittest.TestCase):
    def test_independent49_states_four_transitions_and_intermediate_flags(self):
        for kind in ('private','public_fixture'):
            transitions=Counter()
            for case in corpus.iter_cases():
                s=case['selector_snapshot']['value'];e=oracle.expected_case(case,kind);tail=e['steps'][41:]
                self.assertEqual((len(e['steps']),e['instruction_count']),(49,49))
                self.assertEqual([int(x['native_site_identity'],16) for x in tail],list(corpus.POST_PCS))
                self.assertEqual(e['terminal']['cpu']['pc'],0x2011 if kind=='public_fixture' else 0x064C)
                self.assertEqual((e['selector_final'],e['local_r0_final']),((s+1)&3,s+1))
                transitions[f"{s}->{e['selector_final']}"]+=1
                self.assertEqual([x['after']['cpu']['a']&255 for x in tail],[s,s,s&1,s&1,s&1,s+1,(s+1)&3,(s+1)&3])
                b=e['history0128_before'];bit=1<<(s&1)
                self.assertEqual([x['after']['cpu']['zf'] for x in tail],
                    [s==0,s==0,s&1==0,b&bit==0,False,False,s==3,s==3])
                self.assertFalse(tail[4]['after']['cpu']['hc'])
                self.assertEqual(e['history0128_after'],b|bit)
                self.assertEqual(e['history0128_after']&~bit,b&~bit)
                self.assertEqual(e['selector_generation']['native_write_ordinal'],18)
                self.assertEqual(e['selector_generation']['logical_write_ordinal'],76)
                self.assertEqual(e['selector_generation']['raw_write_ordinal'],113)
                self.assertEqual(e['history0128_generation']['native_write_ordinal'],16)
                self.assertIsNone(e['selector_read']['native_generation'])
                self.assertIsNone(e['initial_selector_generation'])
                for x in tail:
                    for field in ('ssp','lrb','sf','cf'):
                        self.assertEqual(x['before']['cpu'][field],x['after']['cpu'][field])
                    self.assertEqual(x['before']['cpu']['a']>>8,x['after']['cpu']['a']>>8)
                    self.assertEqual(x['before']['owned_ram'][str(0x0109)],x['after']['owned_ram'][str(0x0109)])
            self.assertEqual(transitions,{'0->1':4,'1->2':4,'2->3':4,'3->0':4})

    def test_first41_cpu_states_and_retained_generations_preserve_parent(self):
        for case in corpus.iter_cases():
            for kind in ('private','public_fixture'):
                old=parent.expected_case(corpus.scalar_case(case),kind);new=oracle.expected_case(case,kind)
                for before,after in zip(old['steps'],new['steps'][:41]):
                    for side in ('before','after'):
                        self.assertEqual(before[side]['cpu'],after[side]['cpu'])
                        self.assertEqual(before[side]['full_psw'],after[side]['full_psw'])
                        for address,value in before[side]['owned_ram'].items():self.assertEqual(after[side]['owned_ram'][address],value)
                self.assertEqual(new['stack_frame']['logical_write_ordinal'],58)
                self.assertEqual(new['stack_frame']['raw_write_ordinals'],[90,91])
                self.assertEqual(new['stack_return']['retired_instruction'],41)
                self.assertEqual(new['terminal']['cpu']['ssp'],case['entry']['ssp'])
                for name in ('p2','control'):
                    for oldg,newg in zip(old[name+'_generations'],new[name+'_generations']):
                        for k in ('writer_pc','native_write_ordinal','retired_instruction','value'):
                            self.assertEqual(oldg[k],newg[k])
                        self.assertEqual(oldg['logical_write_ordinal']+1,newg['logical_write_ordinal'])
                        self.assertEqual(oldg['raw_write_ordinal']+1,newg['raw_write_ordinal'])

    def test_independent_public_geometry_and_diagnostic_authority_split(self):
        p=oracle.public_program_identity()
        self.assertEqual([(w['base'],w['byte_count']) for w in p['program_windows']],[(0x2000,17),(0x6400,404)])
        self.assertEqual(len(p['selected_extent_sha256']),59);self.assertNotIn(str(0x2011),p['selected_extent_sha256'])
        self.assertEqual(sum(len(oracle.post_return_extent(pc,'public_fixture')) for pc in corpus.POST_PCS),14)
        c=oracle.CYCLE_ACCOUNTING
        self.assertEqual((c['postReturnSoftwareDiagnosticTotal'],c['postReturnManufacturerIntTotal']),(31,32))
        self.assertEqual((c['incbR0SoftwareDiagnosticDelta'],c['incbR0ManufacturerInt']),(2,3))
        self.assertEqual(c['overallClassification'],'DiagnosticCycleTimingEquivalenceNotEstablished')

    def test_fabricated49_observation_schema_has_full_comparator_coverage(self):
        case=next(corpus.iter_cases());value=oracle.compare_observation(case,invented_observation(case),'public_fixture')
        self.assertTrue(value['passed']);self.assertEqual(value['comparison']['omittedActualFields'],[])

    def test_meaningful_selector_frame_context_and_authority_mutations_refused(self):
        case=next(corpus.iter_cases());good=invented_observation(case)
        paths=[('actual_successful_step_returns',),('report','selector_initial'),('report','selector_final'),
          ('report','selector_read','reader_pc'),('report','selector_read','value'),('report','selector_read','retired_instruction'),
          ('report','selector_generation','writer_pc'),('report','selector_generation','retired_instruction'),
          ('report','selector_generation','native_write_ordinal'),('report','selector_generation','logical_write_ordinal'),
          ('report','selector_generation','raw_write_ordinal'),('report','selector_generation','event_index'),
          ('report','selector_generation','generation_ordinal'),('report','history0128_after'),('report','history0128_selected_bit'),
          ('report','history0128_generation','writer_pc'),('report','history0128_generation','value'),('report','local_r0_final'),
          ('report','post_return_instruction_retirements'),('report','total_instruction_retirements'),
          ('report','native_next_event_handoff_verified'),('report','branch064c_retired'),
          ('report','prefix','stack_frame','machine_id'),('report','prefix','stack_frame','logical_write_ordinal'),
          ('report','prefix','stack_return','consumed_writer_pc'),('report','prefix','stack_return','ssp_after'),
          ('report','prefix','body','stop_before_pc'),('report','prefix','body','steps',45,'after','cpu','hc'),
          ('report','prefix','body','steps',45,'after','cpu','zf'),('report','prefix','body','steps',48,'after','cpu','ssp'),
          ('report','prefix','body','steps',48,'after','cpu','lrb'),('report','prefix','body','steps',48,'after','cpu','a'),
          ('report','prefix','body','p2_generations',1,'native_write_ordinal'),
          ('report','prefix','body','control_generations',1,'native_write_ordinal')]
        for path in paths:
            changed=deepcopy(good);node=changed
            for k in path[:-1]:node=node[k]
            value=node[path[-1]];node[path[-1]]=not value if type(value) is bool else value+1
            with self.subTest(path=path),self.assertRaises(ValueError):oracle.compare_observation(case,changed,'public_fixture')

    def test_missing_initial_generation_and_rmw_neighbor_or_order_forgery_refused(self):
        case=next(corpus.iter_cases());good=invented_observation(case)
        for name in ('imported_initial_generation','missing_selector_writer','stale_cal','raw_frame_order','sbr_neighbor',
                     'sbr_read_write_order','wrong_local_read','same_value_frame_overwrite','fetch_branch064c'):
            value=deepcopy(good);r=value['report'];p=r['prefix'];b=p['body']
            if name=='imported_initial_generation':r['initial_selector_generation']=deepcopy(r['selector_generation'])
            elif name=='missing_selector_writer':r['selector_generation']=None
            elif name=='stale_cal':p['stack_frame']['source_generation']='HistoricalM2aeFrame'
            elif name=='raw_frame_order':p['stack_frame']['raw_write_ordinals'].reverse()
            elif name=='sbr_neighbor':r['history0128_after']^=4
            elif name=='sbr_read_write_order':r['history0128_rmw'].reverse()
            elif name=='wrong_local_read':
                e=next(x for x in b['audit']['data_events'] if x['pc']==0x200C and x['operation']=='Read');e['value']^=1
            elif name=='same_value_frame_overwrite':p['all_native_journal'].insert(-1,deepcopy(p['all_native_journal'][0]))
            else:
                e=deepcopy(b['audit']['program_events'][-1]);e['pc']=e['address']=0x2011;b['audit']['program_events'].append(e)
            self.assertNotEqual(value,good)
            with self.subTest(name=name),self.assertRaises(ValueError):oracle.compare_observation(case,value,'public_fixture')

    def test_partial_41_or48_steps_cannot_be_promoted_to_completed_selector(self):
        case=next(corpus.iter_cases());good=invented_observation(case)
        for count in (41,48):
            value=deepcopy(good);r=value['report'];b=r['prefix']['body']
            value['actual_successful_step_returns']=count;r['total_instruction_retirements']=count
            r['post_return_instruction_retirements']=count-41;r['selector_generation']=None
            r['completed']=value['accepted']=True;b['steps']=b['steps'][:count];b['current']=deepcopy(b['steps'][-1]['after'])
            self.assertIsNotNone(r['prefix']['stack_return']);self.assertIsNone(r['selector_generation'])
            with self.subTest(count=count),self.assertRaises(ValueError):oracle.compare_observation(case,value,'public_fixture')


    def test_wrong_selector_wrap_three_to_zero_actual_observation_refused(self):
        case=next(c for c in corpus.iter_cases() if c['selector_snapshot']['value']==3)
        actual=invented_observation(case);report=actual['report'];body=report['prefix']['body']
        self.assertEqual((report['selector_initial'],report['selector_final']),(3,0))
        # Fabricate a meaningful unmasked4 result in the observed output,
        # native generation and final AL/RAM, while frozen expectations stay0.
        report['selector_final']=4;report['selector_generation']['value']=4
        for snapshot in (body['current'],body['steps'][-1]['after']):
            snapshot['cpu']['a']=snapshot['cpu']['a']&0xFF00|4
            snapshot['ram'][0x0140-snapshot['ram_range'][0]]=4
        write=next(e for e in body['audit']['data_events'] if e['pc']==0x200F and e['operation']=='Write')
        write['value']=write['requested_value']=4
        raw=next(e for e in body['audit']['raw_data_events'] if e['logical_ordinal']==write['ordinal'])
        raw['value']=raw['requested_value']=4
        with self.assertRaises(ValueError):oracle.compare_observation(case,actual,'public_fixture')
