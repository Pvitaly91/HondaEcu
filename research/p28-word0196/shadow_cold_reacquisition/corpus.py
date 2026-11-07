"""Invented cases for source-qualified M2cy equivalence and refusals."""

from copy import deepcopy

from indexed_suffix_ie_provenance.corpus import composition_query, post_query, return_query


def _case(case_id, operation, query):
    return {'id': case_id, 'operation': operation, 'input': query}


def _variants(prefix, operation, build, variants):
    for name, changes in variants:
        query = build()
        for path, value in changes.items():
            fields = path.split('.')
            owner = query
            for key in fields[:-1]:
                owner = owner[int(key)] if isinstance(owner, list) else owner[key]
            key = int(fields[-1]) if isinstance(owner, list) else fields[-1]
            owner[key] = deepcopy(value)
        yield _case(f'{prefix}-{name}', operation, query)


def slot(value, generation, bits=None):
    return {'value': value, 'generation': generation,
            'knownBits': {} if bits is None else {str(position): digit for position, digit in bits.items()}}


def shadow_query(writer=0x2710, caller=0x276A):
    word = {0x256B: 0, 0x2710: 0, 0x54DD: 0x02A0, 0x3F18: 0x02A0, 0x3F2C: 0x00A0}[writer]
    generation = 'InventedShadowWord'
    return {
        'inputClass': 'SyntheticTestInput', 'callerPc': caller, 'consumerPc': 0x5CB7,
        'sourceBinding': 'M2cyShadowSourceReviewV1',
        'context': {'origin': 'Cold276A' if caller == 0x276A else 'Independent2B64',
                    'lrb': 0x0041 if caller == 0x276A else None, 'scb': 0 if caller == 0x276A else None,
                    'usp': 0x0180 if caller == 0x276A else None,
                    'data0230Bit3': 0 if caller == 0x276A else None,
                    'oldIrqh4': 1 if caller == 0x276A else None},
        'initialPair': {'address': 0x00FA, 'wordGeneration': generation,
                        'low': slot(word % 256, generation), 'high': slot(word // 256, generation)},
        'writer': {'pc': writer, 'address': 0x00FA, 'dd': 1},
        'requestedGeneration': generation,
        'premises': dict.fromkeys(('ownedColdNon47Entry', 'stableClearContext', 'firstExitBeforeActivePointerAlias',
                                  'ie2759SymbolicHandoff', 'indexedRouteQualified',
                                  'noAsynchronousInterference'), True),
        'exit': {'dp': 0x0098, 'usp': 0x0356},
        'frame': {'callerPc': caller, 'incomingSsp': 0x047E, 'generation': 'InventedIndexedFrame',
                  'memoryApplicable': True, 'integrity': True},
        'events': [], 'claim': 'ConditionalOnly',
    }


def shadow_cases():
    operation = 'data00fa_caller_reaching_definitions'
    for caller in (0x276A, 0x2B64):
        for writer in (0x256B, 0x2710, 0x54DD, 0x3F18, 0x3F2C):
            yield _case(f'shadow-{caller:04X}-{writer:04X}', operation, shadow_query(writer, caller))
    for usp in (0x0150, 0x0151, 0x0180):
        query = shadow_query(caller=0x2B64)
        query['context']['usp'] = usp
        yield _case(f'shadow-2b64-usp-{usp:04x}', operation, query)
    generation = 'InventedShadowWord'
    yield from _variants('shadow', operation, shadow_query, (
        ('f8-substitution', {'initialPair.address': 0xF8}),
        ('wrong-consumer', {'consumerPc': 0x3FF7}),
        ('wrong-writer', {'writer.pc': 0x3FF7}),
        ('word-alignment', {'writer.address': 0x00FB}),
        ('writer-byte-mode', {'writer.dd': 0}),
        ('initial-partial-zero', {'initialPair.high': slot(None, generation, {7: 0})}),
        ('initial-all-bits-zero', {'initialPair.high': slot(None, generation, dict.fromkeys(range(8), 0))}),
        ('initial-nonzero-bit', {'initialPair.high': slot(None, generation, {7: 1})}),
        ('mixed-bytes', {'initialPair.high.generation': 'OtherByteWriter'}),
        ('missing-word-generation', {'initialPair.wordGeneration': None}),
        ('stale-requested-generation', {'requestedGeneration': 'OlderWord'}),
        ('source-context-unknown', {'context.origin': 'Unknown'}),
        ('scb-unowned', {'context.scb': None}),
        ('usp-unowned', {'context.usp': None}),
        ('different-usp', {'context.usp': 0x0419}),
        ('indexed-path-unqualified', {'premises.indexedRouteQualified': None}),
        ('timer-bypass-unproven', {'context.data0230Bit3': None}),
        ('pending-factor-unproven', {'context.oldIrqh4': None}),
        ('first-ie-unqualified', {'premises.ie2759SymbolicHandoff': None}),
        ('possible-async-writer', {'premises.noAsynchronousInterference': False}),
        ('exit-lower-bound', {'exit.dp': 0x0088, 'exit.usp': 0x0098}),
        ('exit-active-pointer-alias', {'exit.dp': 0x0086, 'exit.usp': 0x0098}),
        ('exit-dp-odd', {'exit.dp': 0x0097}),
        ('exit-context-unknown', {'exit.usp': None}),
        ('unbound-stack', {'frame.incomingSsp': None}),
        ('stack-alias-word', {'frame.incomingSsp': 0x00FB}),
        ('stack-control-alias', {'frame.incomingSsp': 0x0005}),
        ('stack-local-alias', {'frame.incomingSsp': 0x020D}),
        ('frame-integrity-unknown', {'frame.integrity': None}),
        ('frame-owner-mismatch', {'frame.callerPc': 0x2B64}),
        ('caller-borrows-cold-context', {'callerPc': 0x2B64}),
        ('native-generation-claim', {'claim': 'NativeOwner'}),
        ('runtime-admission-claim', {'claim': 'RuntimeAdmission'}),
        ('wrong-source-binding', {'sourceBinding': 'InventedBinding'}),
    ))
    for name, kind, address, width, raw, gen, reached in (
        ('same-word-new-writer', 'DirectStore', 0xFA, 16, 0, 'OtherWord', True),
        ('overlapping-odd-word', 'IndirectStore', 0xFB, 16, 0x1500, 'OtherWord', True),
        ('overwrite-low-byte', 'DirectStore', 0xFA, 8, 1, 'OtherLow', True),
        ('overlapping-stack-frame', 'FrameStore', 0xFB, 16, 0x276D, 'OtherFrame', True),
        ('unknown-stack-frame', 'FrameStore', None, 16, 0x276D, 'OtherFrame', True),
        ('unknown-writer', 'UnknownWriter', None, 8, None, 'OtherWriter', None),
        ('never-reached-writer', 'DirectStore', 0xFA, 16, 0x3351, 'OtherWord', False),
        ('disjoint-writer', 'DirectStore', 0xFC, 16, 0x3351, 'OtherWord', True),
        ('duplicate-generation', 'IndirectStore', 0xFC, 16, 0x3351, generation, True),
    ):
        query = shadow_query()
        query['events'].append({'kind': kind, 'writerPc': None, 'address': address, 'widthBits': width,
                                'generation': gen, 'value': raw, 'reached': reached})
        yield _case(f'shadow-{name}', operation, query)
    for label, pc, kind, address, word in (
        ('wrong-direct-writer-destination', 0x256B, 'DirectStore', 0xF8, 0),
        ('wrong-direct-writer-value', 0x3F18, 'DirectStore', 0xFA, 0x02A1),
        ('actual-known-direct-site-competitor', 0x3F2C, 'DirectStore', 0xFA, 0x00A0),
        ('wrong-indirect-clear-form', 0x2710, 'DirectStore', 0xFA, 0),
        ('valid-disjoint-indirect-clear', 0x2710, 'IndirectStore', 0xFC, 0),
    ):
        query = shadow_query()
        query['events'].append({'kind': kind, 'writerPc': pc, 'address': address, 'widthBits': 16,
                                'generation': 'AlternativeBoundSource', 'value': word, 'reached': True})
        yield _case(f'shadow-{label}', operation, query)


def acquisition(identity='First', index=5, prior=None, adcr1h=0xD3, adcr0h=0x9A):
    return {
        'kind': 'Acquisition', 'iterationId': identity, 'p2': None if index is None else index * 32 + 7,
        'adcr1h': adcr1h, 'adcr0h': adcr0h, 'adcr1Generation': f'{identity}:Adc1Store',
        'adcr0Generation': f'{identity}:Adc0Store', 'fromIteration': prior,
        'repeatBranch': True if prior else None, 'return276d': True if prior else None,
        'prefixEstablished': True,
    }


def frame_event(ssp=0x047E, path=True):
    return {'kind': 'Frame', 'callerPc': 0x2777, 'ssp': ssp, 'generation': 'HelperFrame', 'pathEstablished': path}


def store_event(address=0x03CB, width=8, value=0x9A, path=True):
    return {'kind': 'Store', 'address': address, 'widthBits': width, 'value': value,
            'generation': 'OtherWriter', 'pathEstablished': path}


def usp_event(usp=0x0419, dd=0, path=True):
    return {'kind': 'Usp27B2', 'usp': usp, 'uspGeneration': 'SuppliedUsp', 'dd': dd, 'value': 0x9A,
            'generation': 'UspRelativeWriter', 'pathEstablished': path}


def timeline_query(events=None, cb='First:Adc0Store', d1=None):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': 'M2cyIndexedTimelineV1',
            'initial': {'03CB': {'value': 0x9A, 'generation': 'InitialCB', 'iterationId': None},
                        '03D1': {'value': 0x61, 'generation': 'InitialD1', 'iterationId': None}},
            'events': [acquisition()] if events is None else events,
            'requested': {'03CB': cb, '03D1': d1},
            'premises': {'noInterference': True, 'loopExit': True, 'indexedReturn': True, 'helperEntry': True},
            'claim': 'ConditionalOnly'}


def timeline_cases():
    operation = 'cold_adc_generation_timeline'
    for index in range(8):
        cb, d1 = ('First:Adc0Store' if index == 5 else None), ('First:Adc1Store' if index == 3 else None)
        yield _case(f'timeline-index-{index}', operation, timeline_query([acquisition(index=index)], cb, d1))
    for name, first, second, cb, d1 in (
        ('3-then-5', 3, 5, 'Second:Adc0Store', 'First:Adc1Store'),
        ('5-then-3', 5, 3, 'First:Adc0Store', 'Second:Adc1Store'),
        ('same-value-new-index-5', 5, 5, 'Second:Adc0Store', None),
        ('stale-first-index-5', 5, 5, 'First:Adc0Store', None),
        ('index-5-other-index', 5, 7, 'First:Adc0Store', None),
    ):
        events = [acquisition(index=first), acquisition('Second', second, 'First')]
        yield _case(f'timeline-{name}', operation, timeline_query(events, cb, d1))
    for name, event in (
        ('same-value-competing-store', store_event()), ('aligned-frame-cb', frame_event(0x03CB)),
        ('aligned-frame-d1', frame_event(0x03D1)), ('safe-frame', frame_event()),
        ('frame-control-alias', frame_event(0x0005)),
        ('unknown-stack-address', frame_event(None)), ('disjoint-byte', store_event(0x03CC)),
        ('odd-word-store', store_event(0x03CB, 16, 0x9A50)), ('unknown-store-address', store_event(None)),
        ('blocked-external-address', store_event(0x4700)),
        ('uncertain-store-path', store_event(path=None)), ('never-reached-store', store_event(path=False)),
        ('usp0419-alias', usp_event()), ('usp0419-word', usp_event(dd=1)),
        ('usp-unknown', usp_event(None)), ('usp-dd-unknown', usp_event(dd=None)),
        ('usp-disjoint-qualified', usp_event(0x0180)), ('usp-unreached', usp_event(path=False)),
    ):
        yield _case(f'timeline-{name}', operation, timeline_query([acquisition(), event]))
    yield from _variants('timeline', operation, timeline_query, (
        ('no-interference-false', {'premises.noInterference': False}),
        ('no-interference-unknown', {'premises.noInterference': None}),
        ('wrong-source-binding', {'sourceBinding': 'UnboundTimeline'}),
        ('wrong-p2', {'events.0.p2': None}),
        ('unavailable-adc', {'events.0.adcr0h': None}),
        ('fused-generation', {'events.0.adcr0Generation': 'First:Adc1Store'}),
        ('unqualified-prefix', {'events.0.prefixEstablished': None}),
        ('native-owner', {'claim': 'NativeOwner'}),
        ('physical-ADC', {'claim': 'ActualHardware'}),
        ('runtime-admission', {'claim': 'RuntimeAdmission'}),
        ('fake-mode-consumer', {'claim': 'ModeConsumerReached'}),
    ))
    for name, changes in (
        ('missing-indexed-return', {'return276d': None}), ('branch-unknown', {'repeatBranch': None}),
        ('branch-exited', {'repeatBranch': False}), ('wrong-predecessor', {'fromIteration': 'Unrelated'}),
        ('duplicated-iteration-id', {'iterationId': 'First'}),
    ):
        events = [acquisition(), {**acquisition('Second', 3, 'First'), **changes}]
        yield _case(f'timeline-{name}', operation, timeline_query(events))
    yield _case('timeline-indexed-event-after-helper-frame', operation,
                timeline_query([acquisition(), frame_event(), acquisition('Second', 3, 'First')]))
    yield _case('timeline-reversed-cold-source-order', operation,
                timeline_query([acquisition(), usp_event(0x0180), frame_event()]))


def data03d1_query():
    return timeline_query([acquisition(index=3)], None, 'First:Adc1Store')


def data03d1_cases():
    operation = 'data03d1_reaching_definitions'
    yield _case('data03d1-reaches', operation, data03d1_query())
    for name, event in (
        ('helper-frame-overlap', frame_event(0x03D1)), ('helper-frame-retained', frame_event()),
        ('same-value-competitor', store_event(0x03D1, value=0xD3)),
        ('next-index5', acquisition('Second', 5, 'First')),
        ('next-index3', acquisition('Second', 3, 'First')),
        ('writer-after-helper', usp_event()),
    ):
        q = data03d1_query()
        q['events'].append(event)
        yield _case(f'data03d1-{name}', operation, q)
    yield from _variants('data03d1', operation, data03d1_query, (
        ('generation-unknown', {'requested.03D1': None}),
        ('generation-stale', {'requested.03D1': 'OlderAdc1'}),
        ('loop-exit-unbound', {'premises.loopExit': None}),
        ('indexed-return-unbound', {'premises.indexedReturn': None}),
        ('helper-entry-unbound', {'premises.helperEntry': None}),
        ('wrong-source-index', {'events.0.p2': 0xA0}),
        ('operand-unknown', {'events.0.adcr1h': None}),
    ))


def cold_step_query(index=5, caller_p2=0x60):
    composition = composition_query(0x276A)
    prefix = composition['prefixQuery']
    snapshot = prefix['snapshot']
    snapshot['sfrReadbacks']['0024']['value'] = index * 32 + 7
    detached = post_query()
    post_snapshot = detached.pop('snapshot')
    detached.pop('inputClass')
    for key in ('00F8', '00F9'):
        snapshot['memory'][key] = post_snapshot['memory'][key]
        snapshot['generations'][key] = post_snapshot['generations'][key]
    return {'inputClass': prefix['inputClass'], 'iterationId': 'InventedColdFirst', 'prefixQuery': prefix,
            'shadow': composition['shadow'], 'postIe': detached, 'returnQuery': return_query(0x276A),
            'returnHandoff': True, 'callerP2': slot(caller_p2, 'SuppliedColdCallerP2'),
            'counterF7': slot(0x61, 'InventedPriorCounterF7')}


def cold_step_cases():
    operation = 'cold_reacquisition_step'
    for index in range(8):
        yield _case(f'cold-step-acquisition-index-{index}', operation, cold_step_query(index))
    yield _case('cold-step-exit-zero-mask', operation, cold_step_query(caller_p2=0x17))
    yield from _variants('cold-step', operation, cold_step_query, (
        ('p2-known-nonzero-bit', {'callerP2': slot(None, 'SuppliedColdCallerP2', {5: 1})}),
        ('p2-known-zero-mask', {'callerP2': slot(None, 'SuppliedColdCallerP2', {5: 0, 6: 0, 7: 0})}),
        ('p2-branch-unknown', {'callerP2': slot(None, 'SuppliedColdCallerP2', {5: 0})}),
        ('missing-caller-p2', {'callerP2': None}),
        ('unbound-caller-p2-generation', {'callerP2.generation': None}),
        ('unbound-first-ie-crossing', {'postIe': None}),
        ('unbound-second-ie-crossing', {'postIe.secondIeBoundary': None}),
        ('unbound-frame-query', {'returnQuery': None}),
        ('unbound-caller-handoff', {'returnHandoff': None}),
        ('wrong-ordinary-frame', {'returnQuery': return_query(0x2B64)}),
        ('missing-indexed-entry', {'prefixQuery.entryEstablished': None}),
        ('prefix-fault-marker', {'prefixQuery.snapshot.sfrReadbacks.0019.value': 0}),
        ('prefix-timer-frontier', {'prefixQuery.snapshot.memory.0230': 8}),
        ('wrong-shadow-generation', {'shadow.generation': 'WrongFirstGeneration'}),
    ))


def sequence_query(dpl=1, limit=3, caller_p2=0x60, bits=None):
    step = cold_step_query(caller_p2=caller_p2)
    snapshot = step['prefixQuery']['snapshot']
    snapshot['memory']['0084'] = dpl
    snapshot['knownBits'].update({f'0084.{bit}': value for bit, value in (bits or {}).items()})
    return {'inputClass': step['inputClass'], 'step': step, 'maxWaitSteps': limit}


def sequence_cases():
    operation = 'cold_reacquisition_sequence'
    for name, query in (
        ('one-wait', sequence_query()), ('two-waits', sequence_query(2)),
        ('bound-exhausted', sequence_query(5, 2)), ('zero-bound', sequence_query(5, 0)),
        ('dpl-wrap', sequence_query(0, 1)), ('dpl-unknown', sequence_query(None, 4)),
        ('dpl-known-nonzero-after', sequence_query(None, 1, bits={7: 1})),
        ('single-iteration-exit', sequence_query(caller_p2=0)),
    ):
        yield _case(f'cold-sequence-{name}', operation, query)
    yield from _variants('cold-sequence', operation, sequence_query, (
        ('wrong-local-bank', {'step.prefixQuery.snapshot.registers.lrb': 0x0042}),
        ('missing-handoff', {'step.returnHandoff': None}),
        ('no-next-step-after-fault', {'step.prefixQuery.snapshot.sfrReadbacks.0019.value': 0}),
        ('generation-collision', {'step.prefixQuery.snapshot.generations.0084': 'M2cy:2768:InventedColdFirst:1'}),
    ))


def helper_query(adcr1h=0xD3):
    snapshot = composition_query()['prefixQuery']['snapshot']
    generation = 'First:Adc1Store'
    snapshot['memory']['03D1'] = adcr1h
    snapshot['generations']['03D1'] = generation
    return {
        'inputClass': 'SyntheticTestInput', 'snapshot': snapshot, 'invocationId': 'InventedFirstHelper',
        'lineage': timeline_query([acquisition(index=3, adcr1h=adcr1h)], None, generation),
        'entryEstablished': True,
        'thresholds': {'5CDD': 0xB6, '5CE1': 0x1B, '5CE5': 0x45, '5CE9': 0x3D},
        'errorByte': 0x5D,
        'counterF7': {'slot': slot(1, 'M2cy:2773:InventedColdFirst'), 'sourcePc': 0x2773,
                      'firstCall': True, 'noInterference': True,
                      'expectedGeneration': 'M2cy:2773:InventedColdFirst'},
    }


def helper_cases():
    operation = 'helper_5cd9'
    yield _case('helper-first-call-fault', operation, helper_query())
    yield _case('helper-c8-equality', operation, helper_query(adcr1h=0xB6))
    yield _case('helper-c8-less', operation, helper_query(adcr1h=0xB5))
    yield _case('helper-data03d1-unknown', operation, helper_query(adcr1h=None))
    partial = helper_query(adcr1h=None)
    partial['snapshot']['knownBits']['03D1.7'] = 1
    partial['thresholds']['5CDD'] = 0x30
    yield _case('helper-partial-known-greater', operation, partial)
    yield from _variants('helper', operation, helper_query, (
        ('entry-unproven', {'entryEstablished': None}),
        ('unqualified-memory-interference', {'snapshot.assumptions.noInterference': False}),
        ('unknown-ordinary-byte-semantics', {'snapshot.assumptions.ordinaryByteSemantics': None}),
        ('wrong-bank', {'snapshot.registers.scb': 2}),
        ('unknown-bank', {'snapshot.registers.scb': None}),
        ('stale-generation', {'snapshot.generations.03D1': 'OtherAdc1'}),
        ('missing-generation', {'snapshot.generations.03D1': None}),
        ('same-generation-wrong-byte', {'snapshot.memory.03D1': 0xD1}),
        ('lineage-wrong-index', {'lineage.events.0.p2': 0xA0}),
        ('lineage-missing-return', {'lineage.premises.indexedReturn': None}),
        ('lineage-no-interference', {'lineage.premises.noInterference': False}),
        ('unknown-first-comparand', {'thresholds.5CDD': None}),
        ('counter-missing-generation', {'counterF7.slot.generation': None}),
        ('counter-stale-generation', {'counterF7.slot.generation': 'OlderF7Generation'}),
        ('counter-stale-source', {'counterF7.sourcePc': 0x5CF1}),
        ('counter-fabricated-value', {'counterF7.slot.value': 2}),
        ('counter-unknown-value', {'counterF7.slot.value': None}),
        ('counter-unowned', {'counterF7.noInterference': None}),
        ('unknown-error-code-byte', {'errorByte': None}),
    ))


def helper_frame_query(ssp=0x047E):
    frame = return_query(0x276A, ssp)['frameQuery']
    frame.update(sourceBinding='M2cyStatic2777FrameV1', callerPc=0x2777,
                 declaredTarget=0x5CD9, returnPc=0x5CF9)
    frame['frame'].update(low=0x7A, high=0x27, creatorPc=0x2777)
    return {'inputClass': frame['inputClass'], 'frameQuery': frame, 'helperBoundary': 0x5CF9,
            'expectedFrameGeneration': frame['frame']['generation']}


def helper_frame_cases():
    operation = 'rt5cf9_obligations'
    yield _case('helper-frame-matching', operation, helper_frame_query())
    for address in (0x0004, 0x00AE, 0x00F7, 0x00F9, 0x00FB, 0x025A, 0x03CB, 0x03D1, 0x047F):
        yield _case(f'helper-frame-address-{address:04x}', operation, helper_frame_query(address))
    yield from _variants('helper-frame', operation, helper_frame_query, (
        ('fault-not-return', {'helperBoundary': 0x5CF8}),
        ('unreached-helper-boundary', {'helperBoundary': None}),
        ('wrong-frame-source', {'frameQuery.sourceBinding': 'UnboundFrame'}),
        ('wrong-caller', {'frameQuery.callerPc': 0x276A}),
        ('wrong-callee', {'frameQuery.declaredTarget': 0x5C86}),
        ('wrong-return-site', {'frameQuery.returnPc': 0x5CCD}),
        ('wrong-saved-pc', {'frameQuery.frame.low': 0x6D}),
        ('wrong-frame-creator', {'frameQuery.frame.creatorPc': 0x2B64}),
        ('unknown-incoming-ssp', {'frameQuery.incomingSsp': None}),
        ('unbalanced-ssp', {'frameQuery.sspBeforeReturn': 0x047A}),
        ('unknown-frame-generation', {'frameQuery.frame.generation': None}),
        ('unknown-requested-generation', {'expectedFrameGeneration': None}),
        ('stale-generation', {'expectedFrameGeneration': 'OlderHelperFrame'}),
        ('nesting-false', {'frameQuery.premises.balancedNesting': False}),
        ('integrity-unknown', {'frameQuery.premises.frameIntegrity': None}),
        ('interrupt-frame', {'frameQuery.frame.kind': 'Interrupt'}),
        ('fabricated-actual-return', {'frameQuery.claim': 'ActualNativeReturn'}),
        ('host-selected-pc', {'frameQuery.claim': 'HostSelectedReturn'}),
    ))


def cases():
    for group in (shadow_cases, cold_step_cases, sequence_cases, timeline_cases,
                  data03d1_cases, helper_cases, helper_frame_cases):
        yield from group()
