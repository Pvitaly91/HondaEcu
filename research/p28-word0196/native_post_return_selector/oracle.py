"""Independent M2by CAL/RT model plus eight reviewed M2ae state transitions."""
from copy import deepcopy
from hashlib import sha256
from native_cal_rt_continuity import oracle as previous
from . import corpus

_equal,_closed,BASE_ORACLE=previous._equal,previous._closed,previous.BASE_ORACLE
POST_FORM={
    0x063E:(747,'LB A, off N8',2,4,4),0x0640:(2293,'STB A, r0',1,2,2),
    0x0641:(322,'ANDB A, #N8',2,4,4),0x0643:(2172,'SBR off N8',3,9,9),
    0x0646:(668,'INCB r0',1,2,3),0x0647:(739,'LB A, r0',1,2,2),
    0x0648:(322,'ANDB A, #N8',2,4,4),0x064A:(2301,'STB A, off N8',2,4,4)}
FORM={**previous.FORM,**{pc:row[:2] for pc,row in POST_FORM.items()}}
CYCLE_ACCOUNTING={**deepcopy(previous.CYCLE_ACCOUNTING),
    'postReturnInstructions':[{'nativePC':pc,'softwareDiagnosticCounterDelta':row[3],'manufacturerInt':row[4]}
                              for pc,row in POST_FORM.items()],
    'postReturnSoftwareDiagnosticTotal':31,'postReturnManufacturerIntTotal':32,
    'incbR0SoftwareDiagnosticDelta':2,'incbR0ManufacturerInt':3,
    'overallClassification':'DiagnosticCycleTimingEquivalenceNotEstablished'}


def _pc(pc,kind):
    if kind not in ('private','public_fixture'):raise ValueError('ClosedM2bzProgramKindRequired')
    if kind=='public_fixture' and 0x063B<=pc<=0x064C:return corpus.PUBLIC_CALLER+pc-0x063B
    return previous._pc(pc,kind)


def _address(address,kind):
    return corpus.PUBLIC_DATA.get(address,address) if kind=='public_fixture' else address


def diagnostic_snapshot_count(retirements):
    if type(retirements) is not int or retirements!=49:raise ValueError('Exact49PostReturnDiagnosticDomainRequired')
    return 4*retirements+4


def post_return_extent(pc,kind):
    if pc not in POST_FORM or kind not in ('private','public_fixture'):raise ValueError('ClosedEightPostReturnFormsRequired')
    selector,history=_address(0x013C,kind)&255,_address(0x0128,kind)&255
    if pc==0x063E:return bytes((0xF4,selector))
    if pc==0x0640:return bytes((0x88,))
    if pc in (0x0641,0x0648):return bytes((0xD6,1 if pc==0x0641 else 3))
    if pc==0x0643:return bytes((0xC4,history,0x11))
    if pc==0x0646:return bytes((0xA8,))
    if pc==0x0647:return bytes((0x78,))
    return bytes((0xD4,selector))


def _seed_events(case,kind):
    logical,raw,memory=[],[],{}
    wire=corpus.wire_case(case,kind);data=dict(wire['data'])
    selector=_address(0x013C,kind)
    _equal(str(selector) in data,False,'seed/no_duplicate_selector_source')
    data[str(selector)]=case['selector_snapshot']['value']
    seeds=sorted((int(a),8,v) for a,v in data.items())
    for bank,words in enumerate(case['entry']['pointing_banks']):
        seeds.extend((0x80+bank*8+slot*2,16,words[name]) for slot,name in enumerate(('x1','x2','dp','usp')))
    for address,width,value in seeds:
        old=sum(memory.get(address+i,0xA5)<<(8*i) for i in range(width//8));ordinal=len(logical)
        logical.append({'ordinal':ordinal,'phase':'Seed','pc':_pc(corpus.ENTRY_PC,kind),'instruction_index':None,
            'address':address,'width':width,'operation':'Write','requested_value':value,'value':value,'old_value':old,
            'write_ordinal':ordinal,'same_value':value==old,'serviced':True,'refusal':None})
        for i in range(width//8):
            byte,old_byte=value>>(8*i)&255,memory.get(address+i,0xA5)
            raw.append({'ordinal':len(raw),'logical_ordinal':ordinal,'address':address+i,'operation':'Write',
                'requested_value':byte,'value':byte,'old_value':old_byte,'write_ordinal':len(raw),
                'same_value':byte==old_byte,'serviced':True,'refusal':None});memory[address+i]=byte
    _equal((len(logical),len(raw)),(58,90),'seed/closed58_90')
    return logical,raw


def _data_expected(case,expected,kind):
    logical,raw=_seed_events(case,kind);spans=[];raw_writes=len(raw)
    for step in expected['steps']:
        start=len(logical),len(raw)
        for event in step['data_events']:
            ordinal=len(logical)
            logical.append({'ordinal':ordinal,'phase':'Functional',**event,'serviced':True,'refusal':None})
            if step['native_site_identity']=='55CF' and event['address']==6:continue
            for offset in range(event['width']//8):
                writing=event['operation']=='Write';value=event['value']>>(8*offset)&255
                old=event['old_value']>>(8*offset)&255 if writing else None
                raw.append({'ordinal':len(raw),'logical_ordinal':ordinal,'address':event['address']+offset,
                    'operation':event['operation'],'requested_value':value if writing else None,'value':value,'old_value':old,
                    'write_ordinal':raw_writes if writing else None,'same_value':old==value if writing else None,
                    'serviced':True,'refusal':None});raw_writes+=int(writing)
        spans.append({'logical_span':[start[0],len(logical)],'raw_span':[start[1],len(raw)]})
    return logical,raw,spans


def expected_case(case,program_kind='private'):
    corpus.validate_case(case)
    expected=deepcopy(previous.expected_case(corpus.scalar_case(case),program_kind))
    selector=_address(0x013C,program_kind);history=_address(0x0128,program_kind);s=case['selector_snapshot']['value']
    for step in expected['steps']:
        for side in ('before','after'):step[side]['owned_ram'][str(selector)]=s
        for event in step['data_events']:
            if event['write_ordinal'] is not None:event['write_ordinal']+=1
    expected['entry']=deepcopy(expected['steps'][0]['before'])
    current=deepcopy(expected['steps'][-1]['after']);writes=expected['write_count']
    r0_before=current['owned_ram'][str(0x0108)];old_history=current['owned_ram'][str(history)]
    for pc in corpus.POST_PCS:
        row=POST_FORM[pc];before,after=deepcopy(current),deepcopy(current)
        a,psw=before['cpu']['a'],before['full_psw'];events=[]
        def read(address):
            value=before['owned_ram'][str(address)]
            events.append({'pc':_pc(pc,program_kind),'instruction_index':row[0],'address':address,'width':8,
                'operation':'Read','requested_value':None,'value':value,'old_value':None,'write_ordinal':None,'same_value':None})
            return value
        def write(address,value):
            nonlocal writes
            old=before['owned_ram'][str(address)]
            events.append({'pc':_pc(pc,program_kind),'instruction_index':row[0],'address':address,'width':8,
                'operation':'Write','requested_value':value,'value':value,'old_value':old,'write_ordinal':58+writes,'same_value':old==value})
            after['owned_ram'][str(address)]=value;writes+=1
        def set_zf(value):
            nonlocal psw
            psw=psw&~0x4000|int(value==0)<<14
        if pc==0x063E:
            a=a&0xFF00|read(selector);psw&=~0x1000;set_zf(a&255)
        elif pc==0x0640:write(0x0108,a&255)
        elif pc in (0x0641,0x0648):
            a=a&0xFF00|(a&(1 if pc==0x0641 else 3));set_zf(a&255)
        elif pc==0x0643:
            old=read(history);mask=1<<(a&7);write(history,old|mask);set_zf(old&mask)
        elif pc==0x0646:
            old=read(0x0108);value=(old+1)&255;write(0x0108,value);set_zf(value)
            psw=psw&~0x2000|int(old&15==15)<<13
        elif pc==0x0647:
            a=a&0xFF00|read(0x0108);psw&=~0x1000;set_zf(a&255)
        else:write(selector,a&255)
        next_pc=pc+row[2]
        after['full_psw']=psw
        after['cpu'].update(pc=_pc(next_pc,program_kind),a=a,cf=bool(psw&0x8000),zf=bool(psw&0x4000),
            hc=bool(psw&0x2000),dd=bool(psw&0x1000),psw_other=psw&0x0337,
            instructions=before['cpu']['instructions']+1,cycles=before['cpu']['cycles']+row[3])
        index=len(expected['steps'])+1
        expected['steps'].append({'index':index,'native_site_identity':f'{pc:04X}','pc':_pc(pc,program_kind),
            'next_pc':_pc(next_pc,program_kind),'form':'post-return-'+f'{pc:04x}','decoded_index':row[0],
            'mnemonic':row[1],'length':row[2],'branch_taken':None,'before':before,'after':after,'data_events':events})
        for name,value in (('p2_step_snapshots',expected['final_p2']),('control_step_snapshots',expected['control_final'])):
            expected[name].append({'index':index,'before':deepcopy(value),'after':deepcopy(value)})
        current=after
    expected.update(classification='IndependentPostReturnSelectorReference_NoCpuObservation',terminal=current,
        instruction_count=49,stop_before_pc=_pc(0x064C,program_kind),write_count=writes,cycle_accounting=deepcopy(CYCLE_ACCOUNTING),
        selector_initial=s,selector_final=(s+1)&3,initial_selector_generation=None,
        history0128_before=old_history,history0128_after=old_history|1<<(s&1),history0128_selected_bit=s&1,
        local_r0_before=r0_before,local_r0_final=s+1,selector_snapshot=deepcopy(case['selector_snapshot']))
    expected['ordered_data_events']=[deepcopy(e) for step in expected['steps'] for e in step['data_events']]
    expected['logical_read_count']=sum(e['operation']=='Read' for e in expected['ordered_data_events'])
    expected['ram_logical_read_count']=sum(e['operation']=='Read' and e['address']>=128 for e in expected['ordered_data_events'])
    logical,raw,spans=_data_expected(case,expected,program_kind)
    native=[[1 if e['address']==36 else 2 if e['address'] in (64,70) else 0,e['pc'],e['address'],e['width'],
        int(e['operation']=='Write'),e['value']] for e in expected['ordered_data_events'] if e['address']!=6]
    expected['all_native_journal']=native
    for address,name,retired in ((36,'p2',(18,39)),(64,'control',(19,25))):
        journal,generations=[],[]
        for e in logical:
            if e['phase']!='Functional' or e['address']!=address:continue
            linked=[r for r in raw if r['logical_ordinal']==e['ordinal']];_equal(len(linked),1,'peripheral/one_raw_link')
            journal.append({'ordinal':len(journal),'pc':e['pc'],'address':address,'width':8,'operation':e['operation'],
                'value':e['value'],'logical_ordinal':e['ordinal'],'raw_ordinal':linked[0]['ordinal'],'write_ordinal':e['write_ordinal'],
                'native_write_ordinal':e['write_ordinal']-58 if e['write_ordinal'] is not None else None,
                'same_value':e['same_value'],'space':'PeripheralP2' if name=='p2' else 'PeripheralControl'})
            if e['operation']=='Write':generations.append({'machine_id':1,'writer_pc':e['pc'],'retired_instruction':retired[len(generations)],
                'generation_ordinal':len(generations)+1,'native_write_ordinal':e['write_ordinal']-58,
                'logical_write_ordinal':e['write_ordinal'],'raw_write_ordinal':linked[0]['write_ordinal'],'value':e['value']})
        expected['peripheral_'+name+'_journal']=journal;expected[name+'_generations']=generations
        expected[name+'_generation'],expected['second_'+name+'_generation']=generations
    def rows_at(index):
        return logical[slice(*spans[index-1]['logical_span'])],raw[slice(*spans[index-1]['raw_span'])]
    cal,cal_raw=rows_at(1);ret,ret_raw=rows_at(41);frame=deepcopy(expected['stack_frame']);consumed=deepcopy(expected['stack_return'])
    frame.update(logical_ordinal=cal[0]['ordinal'],logical_write_ordinal=cal[0]['write_ordinal'],
        raw_ordinals=[r['ordinal'] for r in cal_raw],raw_write_ordinals=[r['write_ordinal'] for r in cal_raw])
    consumed.update(logical_ordinal=ret[0]['ordinal'],raw_ordinals=[r['ordinal'] for r in ret_raw],consumed_logical_write_ordinal=58)
    consumed['all_native_ordinal']=next(i for i,r in enumerate(native) if r==[0,_pc(0x5688,program_kind),frame['address'],16,0,frame['return_pc']])
    expected['stack_frame'],expected['stack_return'],expected['stack_journal']=frame,consumed,[deepcopy(cal[0]),deepcopy(ret[0])]
    def generation(index,address,label):
        events,bytes_=rows_at(index);e=next(e for e in events if e['operation']=='Write')
        r=next(r for r in bytes_ if r['logical_ordinal']==e['ordinal']);native_row=[0,e['pc'],address,8,1,e['value']]
        return {'machine_id':1,'event_index':0,'writer_pc':e['pc'],'retired_instruction':index,'generation_ordinal':1,
            'address':address,'width':8,'logical_ordinal':e['ordinal'],'logical_write_ordinal':e['write_ordinal'],
            'raw_ordinal':r['ordinal'],'raw_write_ordinal':r['write_ordinal'],'all_native_ordinal':native.index(native_row),
            'native_write_ordinal':e['write_ordinal']-58,'value':e['value'],'source_generation':label}
    reader,reader_raw=rows_at(42);e,r=reader[0],reader_raw[0]
    expected['selector_read']={'machine_id':1,'reader_pc':e['pc'],'retired_instruction':42,'address':selector,'width':8,
        'value':s,'logical_ordinal':e['ordinal'],'raw_ordinal':r['ordinal'],
        'all_native_ordinal':native.index([0,e['pc'],selector,8,0,s]),'source_classification':corpus.SELECTOR_CLASSIFICATION,'native_generation':None}
    expected['selector_generation']=generation(49,selector,'CurrentExecutionNativeSelectorWriter064A')
    expected['history0128_generation']=generation(45,history,'CurrentExecutionNativeHistoryWriter0643')
    expected['history0128_rmw']=rows_at(45)[0]
    return expected


def _decoded(step,kind):
    pc=int(step['native_site_identity'],16)
    if pc not in POST_FORM:return previous._decoded(step,kind)
    row=POST_FORM[pc];n8=0
    if pc in (0x063E,0x064A):n8=_address(0x013C,kind)&255
    elif pc==0x0643:n8=_address(0x0128,kind)&255
    elif pc in (0x0641,0x0648):n8=1 if pc==0x0641 else 3
    return {'index':row[0],'mnemonic':row[1],'len':row[2],'dd_before':step['before']['cpu']['dd'],
        'dd_after':step['after']['cpu']['dd'],'dd_after_option':False if pc in (0x063E,0x0647) else None,
        'cycles':row[3],'n8':n8,'n8_alt':0,'n16':0,'n16_alt':0,'s8':0,'rel8':0,'addr16':0}


def _permissions(expected):
    value=previous._permissions(expected)
    for row in value['writes']:
        if row['access']['address']==_address(0x0128,expected['program_kind']):row['rmw_required']=True
    return value


def public_program_identity():
    parent=previous.public_program_identity();body,_=previous._public_body();hashes=dict(parent['selected_extent_sha256'])
    caller=bytes((0x32,corpus.PUBLIC_BASE&255,corpus.PUBLIC_BASE>>8))
    for pc in corpus.POST_PCS:
        raw=post_return_extent(pc,'public_fixture');caller+=raw;hashes[str(_pc(pc,'public_fixture'))]=sha256(raw).hexdigest()
    _equal((len(caller),len(body),len(hashes)),(17,404,59),'public/independent17_404_59')
    return {'program_base':corpus.PUBLIC_BASE,'program_end_exclusive':corpus.PUBLIC_BASE+404,
        'program_sha256':sha256(caller+body).hexdigest(),'source_binding':None,'selected_extent_sha256':hashes,
        'program_windows':[{'base':base,'end_exclusive':base+len(raw),'sha256':sha256(raw).hexdigest(),'byte_count':len(raw),'role':role}
            for base,raw,role in ((corpus.PUBLIC_CALLER,caller,'CallerCALAndPostReturn'),(corpus.PUBLIC_BASE,body,'CalleeBodyAndRT'))]}


_program_events=previous._program_events


def compare_observation(case, actual, program_kind='private', program_identity=None):
    expected = expected_case(case, program_kind)
    if program_identity is None and program_kind == 'public_fixture':
        program_identity = public_program_identity()
    _closed(program_identity, ('program_base', 'program_end_exclusive', 'program_sha256', 'source_binding', 'selected_extent_sha256', 'program_windows'), 'program')
    _equal(program_identity['program_base'], _pc(corpus.BODY_BASE, program_kind), 'program/base')
    _equal(program_identity['program_end_exclusive'], _pc(0x5688, program_kind)+1, 'program/end')
    _equal(set(program_identity['selected_extent_sha256']), {str(_pc(pc, program_kind)) for pc in FORM}, 'program/closed59')
    windows=program_identity['program_windows']
    _equal([(w['base'],w['end_exclusive'],w['byte_count'],w['role']) for w in windows],
        [(_pc(0x063B,program_kind),_pc(0x064C,program_kind),17,'CallerCALAndPostReturn'),
         (_pc(0x54F5,program_kind),_pc(0x5688,program_kind)+1,404,'CalleeBodyAndRT')],
        'program/exact_two_window_mapping_not_whole_rom_authority')
    for digest in [program_identity['program_sha256'], *program_identity['selected_extent_sha256'].values()]:
        if type(digest) is not str or BASE_ORACLE.SHA.fullmatch(digest) is None:
            raise ValueError('FrozenProgramShaRequired')
    if program_kind == 'public_fixture':
        _equal(program_identity, public_program_identity(), 'program/independent_public_encoding')
    _closed(actual, ('kind', 'case_id', 'family', 'internal_sf', 'accepted', 'error', 'actual_successful_step_returns', 'report'), 'observation')
    for key, value in {'kind': 'post_return_selector_observation', 'case_id': case['case_id'], 'family': case['family'],
        'internal_sf': case['internal_sf'], 'accepted': True, 'error': None, 'actual_successful_step_returns': case['budget']}.items():
        _equal(actual[key], value, 'observation/' + key)
    selector_report = actual['report']
    _closed(selector_report,('prefix','selector_snapshot','initial_selector_generation','selector_initial','selector_final',
        'selector_read','selector_generation','history0128_before','history0128_after','history0128_selected_bit',
        'history0128_rmw','history0128_generation','local_r0_before','local_r0_final','post_return_instruction_retirements',
        'total_instruction_retirements','completed','selector_generation_available_for_future_reader',
        'native_next_event_handoff_verified','branch064c_retired'),'selector_report')
    for key in ('selector_snapshot','initial_selector_generation','selector_initial','selector_final','selector_read',
        'selector_generation','history0128_before','history0128_after','history0128_selected_bit','history0128_rmw',
        'history0128_generation','local_r0_before','local_r0_final'):
        _equal(selector_report[key],expected[key],'selector_report/'+key)
    for key,value in {'post_return_instruction_retirements':8,'total_instruction_retirements':49,'completed':True,
        'selector_generation_available_for_future_reader':True,'native_next_event_handoff_verified':False,'branch064c_retired':False}.items():
        _equal(selector_report[key],value,'selector_report/'+key)
    outer = selector_report['prefix']
    _closed(outer, ('body','program_windows','program_identity','stack_frame','stack_return','stack_journal',
        'frame_status','initial_canary_classification','completed','cal_instruction_retirements',
        'body_instruction_retirements','rt_instruction_retirements','post_return_instruction_retirements','cpu_bus_instances','all_native_journal'),'report')
    for key,value in {'program_windows':program_identity['program_windows'],'program_identity':program_identity['program_sha256'],
        'stack_frame':expected['stack_frame'],'stack_return':expected['stack_return'],'stack_journal':expected['stack_journal'],
        'all_native_journal':expected['all_native_journal'],
        'frame_status':'CallerFrameConsumedByActualRT','initial_canary_classification':'TechnicalPreexistingCanaryNotFrame',
        'completed':True,'cal_instruction_retirements':1,'body_instruction_retirements':39,
        'rt_instruction_retirements':1,'post_return_instruction_retirements':8,'cpu_bus_instances':1}.items():
        _equal(outer[key],value,'report/'+key)
    report = outer['body']
    _closed(report, ('classification', 'source_binding', 'program_node_count', 'path', 'entry', 'current', 'full_psw', 'steps',
        'completed', 'positive_completed', 'boundary_only', 'actual_handoff_observed', 'native_predecessor_retirements',
        'algorithm_retirements', 'stop_before_pc', 'audit', 'p2_snapshot', 'p2_initial', 'p2_final',
        'p2_instruction_retirements', 'peripheral_p2_journal', 'p2_generation', 'ownership', 'p2_step_snapshots', 'control_snapshot', 'control_initial', 'control_final',
        'control_instruction_retirements', 'peripheral_control_journal', 'control_generation', 'control_step_snapshots', 'below_instruction_retirements',
        'p2_generations', 'control_generations', 'second_p2_generation', 'second_control_generation'), 'report')
    fixed = {'classification': corpus.MODE if program_kind == 'private' else 'ExplicitInventedPublicPostReturnSelectorFixture',
        'source_binding': program_identity['source_binding'], 'program_node_count': 59, 'path': case['path'],
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
        **{key: program_identity[key] for key in ('program_base', 'program_end_exclusive')},
        'program_sha256':program_identity['program_windows'][1]['sha256'],
        'data_events': logical, 'raw_data_events': raw, 'data_admission_refusals': [],
        'permissions': _permissions(expected), 'phase': 'Sealed', 'budget': case['budget'],
        'successful_retirements': case['budget'], 'step_calls': case['budget'], 'execution_calls': case['budget'],
        'shared_execution_calls': case['budget'], 'sealed': True, 'terminal_reason': 'OriginalStopBeforeReached',
        'external_exit': None, 'first_fault': None}
    for key, value in fields.items():
        _equal(audit[key], value, 'audit/' + key)
    _equal(audit['diagnostic_events'], [{'ordinal': i, 'kind': 'RawRamSnapshot', 'range': [128, 4096], 'byte_count': 3968}
        for i in range(diagnostic_snapshot_count(case['budget']))], 'audit/diagnostics')
    _program_events(audit['program_events'], list(zip(report['steps'], expected['steps'])), program_identity)
    return {'passed': True, 'expected': expected, 'comparison': {'classification': 'IndependentContinuousPostReturnSelectorAndRetainedFrameGenerationsValidated',
        'firstMismatch': None, 'retirements': case['budget'], 'path': case['path'], 'p2Retirements': 2,
        'oldP2': expected['initial_p2'], 'newP2': expected['final_p2'], 'sameValueP2Write': expected['same_value_p2_write'],
        'finalP2Zf': expected['final_p2_zf'], 'controlRetirements': expected['control_instruction_retirements'], 'belowRetirements': 18,
        'sameValueSecondP2Write': expected['peripheral_p2_journal'][-1]['same_value'],
        'p2Generations': expected['p2_generations'], 'controlGenerations': expected['control_generations'],
        'oldControl': expected['control_initial'], 'newControl': expected['control_final'],
        'sameValueControlWrite': expected['peripheral_control_journal'][-1]['same_value'],
        'initialNativeP2OwnerEstablished': False, 'initialNativeControlOwnerEstablished': False,
        'selectorInitial':expected['selector_initial'],'selectorFinal':expected['selector_final'],
        'selectorGeneration':expected['selector_generation'],'history0128Generation':expected['history0128_generation'],
        'localR0Final':expected['local_r0_final'],'postReturnRetirements':8,'nativeNextEventHandoffVerified':False,
        'physicalExecutionClaimed': False, 'omittedActualFields': []}}
