"""Invented inputs for the M2cz source contracts and negative controls."""

from copy import deepcopy
from itertools import product

from indexed_suffix_ie_provenance.corpus import return_query as indexed_frame_query
from shadow_cold_reacquisition.corpus import (
    acquisition, cold_step_query, helper_frame_query, helper_query, slot, timeline_query,
)


INPUT = 'SyntheticTestInput'


def _case(identity, operation, query):
    return {'id': identity, 'operation': operation, 'input': query}


def _variants(operation, prefix, base, variants):
    for name, replacements in variants:
        query = deepcopy(base)
        for path, value in replacements.items():
            target = query
            parts = path.split('.')
            for part in parts[:-1]:
                target = target[int(part)] if type(target) is list else target[part]
            key = int(parts[-1]) if type(target) is list else parts[-1]
            target[key] = deepcopy(value)
        yield _case(prefix + '-' + name, operation, query)


def c8_query(pc=0x5CDF, cf=0, zf=0, producer='UnsignedByteCompare'):
    return {'inputClass': INPUT, 'pc': pc, 'conditionCode': 0xC8,
            'target': 0x5CED, 'fallthrough': 0x5CE1 if pc == 0x5CDF else 0x5CE9,
            'authority': 'OKI_MSM66201_3_66_3_67', 'cf': cf, 'zf': zf, 'producer': producer}


def c8_cases():
    operation = 'c8_branch_consensus'
    for pc, producer, cf, zf in product((0x5CDF, 0x5CE7), ('ExplicitFlags', 'UnsignedByteCompare'),
                                        (0, 1, None), (0, 1, None)):
        label = f'c8-{pc:04x}-{producer.lower()}-cf{cf}-zf{zf}'
        yield _case(label, operation, c8_query(pc, cf, zf, producer))
    yield from _variants(operation, 'c8', c8_query(), (
        ('missing-primary', {'authority': None}),
        ('emulator-is-not-primary', {'authority': 'ExistingEmulator'}),
        ('incorrect-condition-code', {'conditionCode': 0xC7}),
        ('incorrect-target', {'target': 0x5CF9}),
        ('incorrect-fallthrough', {'fallthrough': 0x5CE3}),
        ('wrong-pc', {'pc': 0x5CE3}),
    ))


def extended_query(entry='Full', value=0xD3, detached=None):
    return {'entry': entry, 'helperQuery': helper_query(adcr1h=value), 'detachedHandoff': detached}


def helper_cases():
    operation = 'helper_5cd9_extended'
    yield from _variants(operation, 'helper-full', extended_query(), (
        ('qualified-fault', {}),
        ('stale-d1', {'helperQuery.snapshot.generations.03D1': 'DifferentD1Generation'}),
        ('no-indexed-return', {'helperQuery.lineage.premises.indexedReturn': None}),
        ('entry-unknown', {'helperQuery.entryEstablished': None}),
        ('f7-known-zero', {'helperQuery.counterF7.slot.value': 0}),
        ('f7-unknown', {'helperQuery.counterF7.slot.value': None}),
        ('f7-same-value-replaced', {'helperQuery.counterF7.slot.generation': 'NewWriteSameValue'}),
        ('f7-no-interference-unknown', {'helperQuery.counterF7.noInterference': None}),
        ('f7-missing-source', {'helperQuery.counterF7.sourcePc': None}),
        ('f7-missing-entire-slot', {'helperQuery.counterF7': None}),
    ))
    for name, value in (('first-equality', 0xB6), ('first-less', 0xB5), ('first-unknown', None)):
        yield _case('helper-full-' + name, operation, extended_query(value=value))
    detached = extended_query('Detached5CE1', value=0xB6, detached=True)
    yield from _variants(operation, 'helper-detached', detached, (
        ('jge-normal-frontier', {}),
        ('missing-handoff', {'detachedHandoff': None}),
        ('negative-handoff', {'detachedHandoff': False}),
        ('jge-unknown', {'helperQuery.thresholds.5CE1': None}),
        ('second-c8-equality', {'helperQuery.thresholds.5CE1': 0xC0, 'helperQuery.thresholds.5CE5': 0xB6}),
        ('second-c8-less', {'helperQuery.thresholds.5CE1': 0xC0, 'helperQuery.thresholds.5CE5': 0xD0}),
        ('second-c8-taken-fault', {'helperQuery.thresholds.5CE1': 0xC0}),
        ('second-c8-taken-stale-f7', {'helperQuery.thresholds.5CE1': 0xC0,
                                    'helperQuery.counterF7.slot.generation': 'SameValueNewCounter'}),
    ))
    yield _case('helper-detached-cannot-cross-taken-first-c8', operation,
                extended_query('Detached5CE1', value=0xD3, detached=True))
    partial = extended_query('Detached5CE1', value=None, detached=True)
    partial['helperQuery']['snapshot']['knownBits']['03D1.7'] = 1
    yield _case('helper-detached-partial-d1', operation, partial)


def return_path_query():
    helper = helper_frame_query()
    helper['expectedFrameGeneration'] = helper['frameQuery']['frame']['generation'] = 'IndependentHelperFrame'
    return {'inputClass': INPUT, 'indexedFrame': indexed_frame_query(), 'helperFrame': helper,
            'indexedIeBoundary': True, 'helperNormalBoundary': True,
            'stackContinuity': True, 'claim': 'ConditionalOnly'}


def return_path_cases():
    yield from _variants('cold_return_path_obligations', 'return-path', return_path_query(), (
        ('exact-hypothetical-frames', {}),
        ('ie-unqualified', {'indexedIeBoundary': None}),
        ('ie-blocked', {'indexedIeBoundary': False}),
        ('helper-frontier-unbound', {'helperNormalBoundary': None}),
        ('stack-continuity-unknown', {'stackContinuity': None}),
        ('indexed-ssp-missing', {'indexedFrame.frameQuery.incomingSsp': None}),
        ('indexed-fake-return', {'indexedFrame.frameQuery.frame.low': 0x7A}),
        ('helper-fake-return', {'helperFrame.frameQuery.frame.low': 0x6D}),
        ('helper-unaligned-frame', {'helperFrame.frameQuery.frame.address': 0x047F}),
        ('helper-stale-frame', {'helperFrame.expectedFrameGeneration': 'OlderHelperFrame'}),
        ('helper-fault', {'helperFrame.helperBoundary': 0x5CF8}),
        ('helper-interrupt-frame', {'helperFrame.frameQuery.frame.kind': 'Interrupt'}),
        ('helper-unbalanced', {'helperFrame.frameQuery.premises.balancedNesting': False}),
        ('reused-frame-generation', {'helperFrame.frameQuery.frame.generation':
             indexed_frame_query()['frameQuery']['frame']['generation'], 'helperFrame.expectedFrameGeneration':
             indexed_frame_query()['frameQuery']['frame']['generation']}),
        ('intercall-ssp-mismatch', {'helperFrame': helper_frame_query(0x0480)}),
        ('indexed-control-alias', {'indexedFrame': indexed_frame_query(ssp=0x0004)}),
        ('helper-aligned-data-alias', {'helperFrame': helper_frame_query(0x03CB)}),
        ('native-claim', {'claim': 'NativeReturn'}),
    ))


def source_join_query():
    first = acquisition(identity='First', index=3, adcr1h=0xD3)
    second = acquisition(identity='Second', index=5, prior='First')
    d1 = first['adcr1Generation']
    cold = cold_step_query(index=5, caller_p2=0x17)
    snapshot = cold['prefixQuery']['snapshot']
    snapshot['memory']['03D1'] = first['adcr1h']
    snapshot['generations']['03D1'] = d1
    source = helper_query()
    return {'inputClass': INPUT, 'coldQuery': cold, 'helperHandoff': True, 'claim': 'ConditionalOnly',
            'helperArgs': {'invocationId': source['invocationId'],
                           'lineage': timeline_query([first, second], None, d1),
                           'thresholds': source['thresholds'], 'errorByte': source['errorByte']}}


def source_join_cases():
    yield from _variants('cold_caller_mode_source_join', 'source-join', source_join_query(), (
        ('conditional-first-fault', {}),
        ('helper-handoff-unbound', {'helperHandoff': None}),
        ('helper-handoff-false', {'helperHandoff': False}),
        ('helper-args-missing', {'helperArgs': None}),
        ('ie-blocked', {'coldQuery.postIe': None}),
        ('return-unbound', {'coldQuery.returnHandoff': None}),
        ('repeat-selected', {'coldQuery.callerP2.value': 0xE0}),
        ('selector-unknown', {'coldQuery.callerP2.value': None, 'coldQuery.callerP2.knownBits': {}}),
        ('disputed-c8', {'helperArgs.thresholds.5CDD': 0xD3}),
        ('unknown-c8', {'helperArgs.thresholds.5CDD': None}),
        ('bad-d1-generation', {'helperArgs.lineage.requested.03D1': 'OtherD1Generation'}),
        ('native-claim', {'claim': 'NativeModeReach'}),
    ))


def usp_query(usp=0x0419):
    context = {'value': usp, 'generation': 'RetainedOrdinaryUsp'}
    return {'inputClass': INPUT, 'sourceBinding': 'M2czData03cbSourceV1', 'entryUsp': dict(context),
            'currentUsp': dict(context), 'lrb': 0x0041, 'scb': 0, 'dd': 0,
            'alRead': {'sourcePc': 0x27AE, 'address': None, 'slot': slot(0x9A, 'SymbolicImmediate27AE')},
            'writerGeneration': 'HypotheticalUspByteWrite',
            'premises': {'hypotheticalReturn': True, 'symbolicSfr': True, 'dataMapping': True, 'noInterference': True},
            'claim': 'ConditionalOnly'}


def usp_cases():
    operation = 'usp27b2_alias_proof'
    for label, usp in (('overlap', 0x0419), ('disjoint', 0x0180), ('nearby', 0x0418),
                       ('wrap', 0x0010), ('control-alias', 0x004E), ('hardware-frontier', 0x474E)):
        yield _case('usp-' + label, operation, usp_query(usp))
    yield from _variants(operation, 'usp', usp_query(), (
        ('unknown-current-value', {'currentUsp.value': None}),
        ('unknown-current-owner', {'currentUsp.generation': None}),
        ('changed-value', {'currentUsp.value': 0x0180}),
        ('same-value-different-generation', {'currentUsp.generation': 'ChangedUsp'}),
        ('word-descriptor', {'dd': 1}),
        ('unknown-dd', {'dd': None}),
        ('wrong-bank', {'scb': 3}),
        ('unknown-lrb', {'lrb': None}),
        ('return-unbound', {'premises.hypotheticalReturn': None}),
        ('mapping-false', {'premises.dataMapping': False}),
        ('interference-unknown', {'premises.noInterference': None}),
        ('wrong-al-source', {'alRead.sourcePc': 0x27B0}),
        ('unadmitted-data-read', {'alRead.address': 0x00A0}),
        ('unknown-al-generation', {'alRead.slot.generation': None}),
        ('partial-al', {'alRead.slot.value': None, 'alRead.slot.knownBits': {'7': 1}}),
        ('writer-generation-reused', {'writerGeneration': 'RetainedOrdinaryUsp'}),
        ('missing-binding', {'sourceBinding': None}),
        ('native-claim', {'claim': 'NativeOwner'}),
    ))


def indexed_event(index=3, value=0x9A, identity='Second', previous='First'):
    return {'kind': 'Indexed', 'id': 'Repeat' + identity, 'iterationId': identity, 'fromIteration': previous,
            'p2': slot(index << 5, 'SymbolicPort' + identity), 'adcr0h': slot(value, 'SymbolicAdc' + identity),
            'scb': 0, 'generation': 'LaterAdcStore' + identity, 'returned': True, 'repeat': True}


def frame_event(ssp=0x03CB, pc=0x2777, generation='OrdinaryFrameStore'):
    return {'kind': 'Frame', 'id': 'FrameEvent', 'pc': pc, 'ssp': ssp, 'generation': generation,
            'pathEstablished': True, 'memoryApplicable': True}


def mapped_event(kind, pc, **context):
    return {'kind': kind, 'id': kind + 'Source', 'pc': pc, 'generation': kind + 'QualifiedWrite',
            'pathEstablished': True, **context}


def writer_query(events=(), *, seed=None):
    seed = acquisition() if seed is None else seed
    generation = seed['adcr0Generation']
    return {'inputClass': INPUT, 'sourceBinding': 'M2czData03cbSourceV1',
            'initialTimeline': timeline_query([seed], generation), 'requestedGeneration': generation,
            'events': list(events), 'noInterference': True, 'claim': 'ConditionalOnly'}


def writer_cases():
    operation = 'data03cb_competing_writer_exclusion'
    repeated = indexed_event(5)
    first = acquisition(index=5, adcr0h=0x27)
    good_usp = {'kind': 'Usp27B2', 'id': 'UspEvent', 'proof': usp_query()}
    for label, query in (
        ('seed-only', writer_query()),
        ('index-3-retains', writer_query([indexed_event()])),
        ('same-value-index-5-replaces', writer_query([repeated])),
        ('changed-value-index-5-replaces', writer_query([indexed_event(5, 0xC4)])),
        ('later-3-then-5', writer_query([indexed_event(3), indexed_event(5, identity='Third', previous='Second')])),
        ('initial-index-3-unbound', writer_query(seed=acquisition(index=3))),
        ('word-03ca-overwrites', writer_query([frame_event()])),
        ('word-03ca-equal-byte-replaces', writer_query([frame_event()], seed=first)),
        ('unknown-frame-ssp', writer_query([frame_event(None)])),
        ('ordinary-frame-disjoint', writer_query([frame_event(0x047F)])),
        ('control-frame', writer_query([frame_event(0x0004)])),
        ('usp-overlap', writer_query([good_usp])),
        ('usp-disjoint', writer_query([{'kind': 'Usp27B2', 'id': 'UspEvent', 'proof': usp_query(0x0180)}])),
        ('unknown-usp', writer_query([{'kind': 'Usp27B2', 'id': 'UspEvent', 'proof': usp_query(None)}])),
        ('local-word-disjoint', writer_query([mapped_event('Local', 0x27C3, lrb=0x0079)])),
        ('local-bank-unknown', writer_query([mapped_event('Local', 0x27C3, lrb=None)])),
        ('offpage-word-disjoint', writer_query([mapped_event('OffPage', 0x5CC2, lrb=0x0060)])),
        ('indirect-known-disjoint', writer_query([mapped_event('Indirect', 0x27AD, address=0x0356)])),
        ('unknown-indirect', writer_query([mapped_event('Indirect', 0x27AD, address=None)])),
        ('indirect-contradicts-proof', writer_query([mapped_event('Indirect', 0x27AD, address=0x03CB)])),
        ('unknown-asynchronous', writer_query([{'kind': 'Unknown', 'id': 'Unexcluded'}])),
        ('after-cold-exit-repeat', writer_query([frame_event(0x047E), indexed_event()])),
        ('late-source-order-reversed', writer_query([mapped_event('Local', 0x27C3, lrb=0x0041), good_usp])),
    ):
        yield _case('writer-' + label, operation, query)
    yield from _variants(operation, 'writer', writer_query([indexed_event()]), (
        ('repeat-unknown-selector', {'events.0.p2.value': None}),
        ('repeat-known-selector-bits', {'events.0.p2.value': None, 'events.0.p2.knownBits': {'7': 0, '6': 1, '5': 1}}),
        ('repeat-unknown-p2-owner', {'events.0.p2.generation': None}),
        ('repeat-unknown-scb', {'events.0.scb': None}),
        ('repeat-unknown-adc-owner', {'events.0.adcr0h.generation': None}),
        ('repeat-unknown-return', {'events.0.returned': None}),
        ('repeat-missing-link', {'events.0.fromIteration': None}),
        ('repeat-reused-iteration', {'events.0.iterationId': 'First'}),
        ('repeat-reused-generation', {'events.0.generation': acquisition()['adcr0Generation']}),
        ('repeat-no-generation', {'events.0.generation': None}),
        ('requested-stale-generation', {'requestedGeneration': 'OlderAdcStore'}),
        ('requested-missing-generation', {'requestedGeneration': None}),
        ('interference-unqualified', {'noInterference': False}),
        ('binding-unqualified', {'sourceBinding': None}),
        ('native-writer-claim', {'claim': 'ActualHardware'}),
    ))


def mode_query():
    cold = source_join_query()
    seed = acquisition(identity=cold['coldQuery']['iterationId'], index=5, adcr0h=0x80)
    seed['adcr0Generation'] = 'ConditionalEffect:data03cb_indexed_writer:5CB4:3'
    generation = seed['adcr0Generation']
    return {'inputClass': INPUT, 'writerQuery': writer_query(seed=seed), 'coldJoinQuery': cold,
            'proposedRead': {'pc': 0x60CC, 'address': 0x03CB, 'widthBits': 8, 'generation': generation},
            'claim': 'ConditionalOnly'}


def mode_cases():
    yield from _variants('data03cb_to_mode_reaching_definitions', 'mode', mode_query(), (
        ('linked-but-fault', {}),
        ('linked-but-ie-blocked', {'coldJoinQuery.coldQuery.postIe': None}),
        ('linked-but-return-unbound', {'coldJoinQuery.coldQuery.returnHandoff': None}),
        ('linked-but-c8-conflict', {'coldJoinQuery.helperArgs.thresholds.5CDD': 0xD3}),
        ('different-seed-value', {'writerQuery.initialTimeline.events.0.adcr0h': 0x61}),
        ('different-iteration', {'writerQuery.initialTimeline.events.0.iterationId': 'DifferentIteration'}),
        ('prefilled-slot-with-no-indexed-write', {
            'writerQuery.initialTimeline.events.0.adcr0Generation': 'PrefilledMatchingSlot',
            'writerQuery.initialTimeline.requested.03CB': 'PrefilledMatchingSlot',
            'writerQuery.requestedGeneration': 'PrefilledMatchingSlot',
            'proposedRead.generation': 'PrefilledMatchingSlot',
            'coldJoinQuery.coldQuery.prefixQuery.snapshot.generations.03CB': 'PrefilledMatchingSlot',
            'coldJoinQuery.coldQuery.prefixQuery.snapshot.memory.03CB': 0x80,
            'coldJoinQuery.coldQuery.prefixQuery.snapshot.registers.scb': None,
        }),
        ('incorrect-read-site', {'proposedRead.pc': 0x27D0}),
        ('incorrect-read-width', {'proposedRead.widthBits': 16}),
        ('incorrect-read-generation', {'proposedRead.generation': 'OlderModeSeed'}),
        ('competing-word-frame', {'writerQuery.events': [frame_event()]}),
        ('native-mode-read-claim', {'claim': 'ModeConsumerReached'}),
    ))


def cases():
    for suite in (c8_cases, helper_cases, return_path_cases, source_join_cases, usp_cases, writer_cases, mode_cases):
        yield from suite()
