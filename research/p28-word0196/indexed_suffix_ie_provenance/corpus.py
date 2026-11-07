"""Invented source-qualified cases for the indexed acquisition suffix."""

from copy import deepcopy

from enclosing_caller_return.corpus import (
    fixture as indexed_snapshot, frame_query as accepted_frame_query, indexed_query,
)


def _case(case_id, operation, query):
    return {'id': case_id, 'operation': operation, 'input': query}


def _variants(name, operation, build, alternatives):
    for label, changes in alternatives:
        query = build()
        for path, value in changes.items():
            parent = query
            for key in path.split('.')[:-1]:
                parent = parent[key]
            parent[path.rsplit('.', 1)[-1]] = deepcopy(value)
        yield _case(f'{name}-{label}', operation, query)


def _symbolic_data(snapshot, address, value, bits=None):
    key = f'{address:04X}'
    snapshot['memory'][key] = value
    current = snapshot['knownBits']
    for field in tuple(current):
        if field.startswith(f'{key}.'):
            del current[field]
    if bits:
        current.update({f'{key}.{bit}': knowledge for bit, knowledge in bits.items()})


def slot(value, generation, bits=None):
    return {'value': value, 'generation': generation,
            'knownBits': {} if bits is None else {str(bit): knowledge for bit, knowledge in bits.items()}}


def shadow_query(address=0xFA, low=0x12, high=0xE7, low_bits=None, high_bits=None, source=None):
    generation = f'InventedShadow:{address:04X}'
    return {
        'inputClass': 'SyntheticTestInput', 'address': address, 'sourcePc': source,
        'generation': generation, 'low': slot(low, generation, low_bits), 'high': slot(high, generation, high_bits),
        'mappingEstablished': True, 'noInterference': True, 'events': [], 'claim': 'ConditionalOnly',
    }


def pre_query(low=0x12, high=0xE7, low_bits=None, high_bits=None):
    snapshot = indexed_snapshot()
    shadow = shadow_query(low=low, high=high, low_bits=low_bits, high_bits=high_bits)
    _symbolic_data(snapshot, 0xFA, low, low_bits)
    _symbolic_data(snapshot, 0xFB, high, high_bits)
    snapshot['generations'].update(dict.fromkeys(('00FA', '00FB'), shadow['generation']))
    return {'inputClass': 'SyntheticTestInput', 'snapshot': snapshot, 'shadow': shadow}


def pre_cases():
    operation = 'indexed_suffix_pre_ie'
    for name, low, high, low_bits, high_bits in (
        ('known', 0x12, 0xE7, None, None),
        ('zero', 0, 0, None, None),
        ('low-one', 1, 0, None, None),
        ('high-one', 0, 1, None, None),
        ('unknown', None, None, None, None),
        ('high-partial-nonzero', 0, None, None, {7: 1}),
        ('low-partial-nonzero', None, 0, {5: 1}, None),
        ('high-partial-unknown', 0, None, None, {7: 0}),
        ('low-partial-unknown', None, 0, {5: 0}, None),
        ('full-knowledge-zero', None, None, dict.fromkeys(range(8), 0), dict.fromkeys(range(8), 0)),
    ):
        yield _case(f'pre-{name}', operation, pre_query(low, high, low_bits, high_bits))
    for dd in (0, 1, None):
        for cf, hc in ((0, 1), (1, 0), (None, None)):
            query = pre_query()
            query['snapshot']['registers'].update(dd=dd, cf=cf, hc=hc)
            yield _case(f'pre-dd-{dd}-cf-{cf}', operation, query)
    yield from _variants('pre', operation, pre_query, (
        ('shadow-f8', {'shadow.address': 0xF8}),
        ('missing-low-gen', {'shadow.low.generation': None}),
        ('missing-high-gen', {'shadow.high.generation': None}),
        ('stale-low-gen', {'shadow.low.generation': 'StaleLow'}),
        ('stale-high-gen', {'shadow.high.generation': 'StaleHigh'}),
        ('state-generation-missing', {'snapshot.generations.00FB': None}),
        ('unbound-shadow-value', {'shadow.high.value': 0x11}),
        ('no-interference-unknown', {'shadow.noInterference': None}),
        ('physical-shadow-claim', {'shadow.claim': 'NativeOwner'}),
    ))


def lineage_cases():
    operation = 'data00fa_shadow_lineage'
    for site, low, high in ((0x256B, 0, 0), (0x3F18, 0xA0, 2), (0x3F2C, 0xA0, 0), (0x54DD, 0xA0, 2)):
        yield _case(f'lineage-writer-{site:04X}', operation, shadow_query(low=low, high=high, source=site))
    for label, query in (
        ('symbolic', shadow_query()),
        ('unknown', shadow_query(low=None, high=None)),
        ('partial-high-nonzero', shadow_query(low=None, high=None, high_bits={4: 1})),
        ('partial-low-unknown', shadow_query(low=None, high=None, low_bits={4: 0})),
        ('partial-known-writer', shadow_query(low=0xA0, high=None, source=0x54DD)),
        ('wrong-writer-value', shadow_query(low=0xA0, high=0, source=0x54DD)),
    ):
        yield _case(f'lineage-{label}', operation, query)
    event = {'address': 0xFA, 'widthBits': 16, 'generation': 'LaterWord'}
    yield from _variants('lineage', operation, shadow_query, (
        ('wrong-slot', {'address': 0xF8}),
        ('mapping-unsupported', {'mappingEstablished': False}),
        ('mapping-unknown', {'mappingEstablished': None}),
        ('unreviewed-reader-as-writer', {'sourcePc': 0x3FF7}),
        ('generation-missing', {'generation': None}),
        ('generation-stale', {'high.generation': 'StaleShadow'}),
        ('overlap-word', {'events': [event]}),
        ('overlap-high-byte', {'events': [{**event, 'address': 0xFB, 'widthBits': 8}]}),
        ('nonoverlap-f8', {'events': [{**event, 'address': 0xF8}]}),
        ('generation-reused', {'events': [{**event, 'generation': shadow_query()['generation']}]}),
        ('address-unknown', {'events': [{**event, 'address': None}]}),
        ('possible-interference', {'noInterference': False}),
        ('native-claim', {'claim': 'NativeOwner'}),
    ))


def retention_query():
    generation = 'InventedIndexed5'
    return {
        'inputClass': 'SyntheticTestInput', 'selectedIndex': 5, 'writerPc': 0x5CB4,
        'entry': slot(0x67, generation), 'observed': slot(0x67, generation),
        'requestedGeneration': generation, 'page': 0x0200, 'events': [],
        'noInterference': True, 'claim': 'ConditionalOnly',
    }


def retention_cases():
    operation = 'data03cb_suffix_retention'
    event = {'kind': 'DirectStore', 'address': 0x03CB, 'widthBits': 8,
             'value': 0x67, 'generation': 'InventedLaterWrite'}
    yield _case('retention-index-5', operation, retention_query())
    yield from _variants('retention', operation, retention_query, (
        ('other-index', {'selectedIndex': 4}),
        ('unknown-index', {'selectedIndex': None}),
        ('other-writer', {'writerPc': 0x60CC}),
        ('missing-writer', {'writerPc': None}),
        ('stale-generation', {'requestedGeneration': 'StaleWriter'}),
        ('changed-generation', {'observed.generation': 'InventedLaterWrite'}),
        ('missing-generation', {'observed.generation': None}),
        ('same-generation-new-value', {'observed.value': 0x11}),
        ('same-generation-conflicting-bit', {'observed.value': None, 'observed.knownBits': {'0': 0}}),
        ('same-generation-unknown-value', {'observed.value': None}),
        ('same-value-overwrite', {'events': [event]}),
        ('different-value-overwrite', {'events': [{**event, 'value': 0x10}]}),
        ('indirect-overlap', {'events': [{**event, 'kind': 'IndirectStore', 'address': 0x03CA,
                                          'widthBits': 16, 'value': 0x6711}]}),
        ('frame-overlap', {'events': [{**event, 'kind': 'FrameStore', 'address': 0x03CA,
                                       'widthBits': 16, 'value': 0x5678}]}),
        ('repeat-acquisition', {'events': [{**event, 'kind': 'IndexedAcquisition'}]}),
        ('competing-word-disjoint', {'events': [{**event, 'kind': 'IndirectStore', 'address': 0x035A,
                                                 'widthBits': 16, 'value': 0x6711}]}),
        ('unknown-interference', {'noInterference': None}),
        ('unknown-writer', {'events': [{**event, 'kind': 'UnknownWriter', 'address': None, 'value': None}]}),
        ('reused-generation', {'events': [{**event, 'generation': 'InventedIndexed5'}]}),
        ('unresolved-page', {'page': None}),
        ('unaligned-page', {'page': 0x0201}),
        ('native-claim', {'claim': 'NativeOwner'}),
    ))


def return_query(caller=0x276A, ssp=0x047E):
    frame = accepted_frame_query(caller, ssp)
    return {
        'inputClass': frame['inputClass'], 'frameQuery': frame, 'postIeBoundary': 0x5CCD,
        'expectedFrameGeneration': frame['frame']['generation'],
        'additionalPremises': {'noInterveningFrameWrites': True, 'noSuffixFrameAlias': True},
    }


def return_cases():
    operation = 'indexed_return_obligations'
    for caller in (0x276A, 0x2B64):
        yield _case(f'return-caller-{caller:04X}', operation, return_query(caller))
    for address in (0x0004, 0x00F8, 0x00FA, 0x025A, 0x03CA):
        yield _case(f'return-frame-alias-{address:04X}', operation, return_query(ssp=address))
    yield _case('return-unreviewed-caller', operation, return_query(0x27D0))
    yield from _variants('return', operation, return_query, (
        ('wrong-rt-site', {'frameQuery.returnPc': 0x5CF9}),
        ('wrong-saved-pc', {'frameQuery.frame.low': 0xF0}),
        ('wrong-frame-owner', {'frameQuery.frame.creatorPc': 0x2B64}),
        ('ssp-unknown', {'frameQuery.sspBeforeReturn': None}),
        ('frame-generation-missing', {'frameQuery.frame.generation': None}),
        ('expected-generation-missing', {'expectedFrameGeneration': None}),
        ('stale-frame-generation', {'expectedFrameGeneration': 'StaleFrame'}),
        ('unbalanced-ssp', {'frameQuery.sspBeforeReturn': 0x0478}),
        ('unbalanced-nesting', {'frameQuery.premises.balancedNesting': False}),
        ('integrity-unknown', {'frameQuery.premises.frameIntegrity': None}),
        ('frame-interference', {'additionalPremises.noInterveningFrameWrites': False}),
        ('suffix-alias-unknown', {'additionalPremises.noSuffixFrameAlias': None}),
        ('interrupt-frame', {'frameQuery.frame.kind': 'Interrupt'}),
        ('fake-actual-return', {'frameQuery.claim': 'ActualNativeReturn'}),
        ('host-selected-return', {'frameQuery.claim': 'HostSelectedReturn'}),
        ('unreached-rt', {'postIeBoundary': 0x5CCB}),
    ))


def composition_query(caller=0x276A):
    pre = pre_query()
    prefix = indexed_query(caller)
    prefix['snapshot'] = pre['snapshot']
    return {'inputClass': pre['inputClass'], 'prefixQuery': prefix, 'shadow': pre['shadow']}


def composition_cases():
    operation = 'indexed_suffix_composition'
    for caller in (0x276A, 0x2B64):
        yield _case(f'composition-caller-{caller:04X}', operation, composition_query(caller))
    yield from _variants('composition', operation, composition_query, (
        ('missing-entry', {'prefixQuery.entryEstablished': None}),
        ('unknown-predicate', {'prefixQuery.snapshot.memory.0230': None}),
        ('guard-timer-frontier', {'prefixQuery.snapshot.memory.0230': 8}),
        ('irqh-fault-marker', {'prefixQuery.snapshot.sfrReadbacks.0019.value': 0}),
        ('shadow-stale', {'shadow.generation': 'WrongFrozenGeneration'}),
        ('shadow-reseed-refused', {'shadow.high.value': 0x11}),
    ))


def ie_query():
    snapshot = indexed_snapshot()
    snapshot['registers'].update(al=0x42, ah=0xCE, dd=1)
    snapshot['registerKnownBits'] = {
        key: value for key, value in snapshot['registerKnownBits'].items()
        if not key.startswith(('AL.', 'AH.'))
    }
    return {
        'inputClass': 'SyntheticTestInput', 'snapshot': snapshot,
        'descriptor': {'address': 0x1A, 'width': 16, 'source': 'A'}, 'attempt': 'Intent',
        'polarity': 'Unresolved',
        'hardwarePremises': dict.fromkeys(('mcuApplicability', 'ieOwner', 'physicalSf', 'mieState',
                                           'pendingGenerations', 'frameAndNesting')),
    }


def ie_cases():
    operation = 'ie5cb9_boundary_obligations'
    yield _case('ie-intent', operation, ie_query())
    query = ie_query()
    query['snapshot']['registers'].update(al=None, ah=None, mie=None)
    query['snapshot']['registerKnownBits']['AH.7'] = 1
    yield _case('ie-partial-a', operation, query)
    yield from _variants('ie', operation, ie_query, (
        ('unknown-a', {'snapshot.registers.al': None, 'snapshot.registers.ah': None}),
        ('dd-zero', {'snapshot.registers.dd': 0}),
        ('dd-unknown', {'snapshot.registers.dd': None}),
        ('byte-store-refused', {'descriptor.width': 8}),
        ('wrong-source', {'descriptor.source': 'AL'}),
        ('odd-address', {'descriptor.address': 0x1B}),
        ('ram-alias', {'descriptor.address': 0xFA}),
        ('polarity-conflict-set1', {'polarity': 'Set1'}),
        ('polarity-conflict-set0', {'polarity': 'Set0'}),
        ('physical-ie-write', {'attempt': 'ActualIeWrite'}),
        ('irq-delivery', {'attempt': 'ActualIrqDelivery'}),
        ('all-premises-true', {'hardwarePremises': dict.fromkeys(ie_query()['hardwarePremises'], True)}),
    ))


def operand(address, width, value, bits=None, generation='InventedOperand'):
    return {'address': address, 'widthBits': width, 'value': value,
            'knownBits': {} if bits is None else {str(bit): knowledge for bit, knowledge in bits.items()},
            'generation': generation, 'evidenceClass': 'SuppliedSymbolic'}


def post_query(p2=0xDB, tm2=0x7603, p2_bits=None, tm2_bits=None):
    snapshot = indexed_snapshot()
    shadow = shadow_query(0xF8, 0x43, 0x19)
    _symbolic_data(snapshot, 0xF8, 0x43)
    _symbolic_data(snapshot, 0xF9, 0x19)
    snapshot['generations'].update(dict.fromkeys(('00F8', '00F9'), shadow['generation']))
    return {
        'inputClass': 'SyntheticTestInput', 'snapshot': snapshot, 'entry': 'HypotheticalPostIe5CBB',
        'p2': operand(0x24, 8, p2, p2_bits, 'InventedP2'),
        'tm2': operand(0x38, 16, tm2, tm2_bits, 'InventedTm2'),
        'shadow': shadow, 'offPage': {'025A': slot(0x33, 'Prior025A'), '025B': slot(0x67, 'Prior025B')},
        'secondIeBoundary': True,
    }


def post_cases():
    operation = 'indexed_suffix_post_ie'
    for label, query in (
        ('ordinary', post_query()),
        ('p2-carry-before', post_query(p2=0xDF)),
        ('p2-carry-wrap', post_query(p2=0xE0)),
        ('p2-carry-after', post_query(p2=0xE1)),
        ('p2-unknown', post_query(p2=None)),
        ('p2-partial-carry', post_query(p2=None, p2_bits={7: 1, 6: 1, 5: 1})),
        ('p2-partial-no-carry', post_query(p2=None, p2_bits={6: 0})),
        ('tm2-unknown', post_query(tm2=None)),
        ('tm2-partial', post_query(tm2=None, tm2_bits={1: 1, 12: 0})),
        ('tm2-same-value', post_query(tm2=0x6733)),
    ):
        yield _case(f'post-{label}', operation, query)
    known_f8 = post_query()
    known_f8['shadow'] = shadow_query(0xF8, 0, 0, source=0x2569)
    for address in (0xF8, 0xF9):
        _symbolic_data(known_f8['snapshot'], address, 0)
    yield _case('post-f8-reviewed-init', operation, known_f8)
    unknown_f8 = post_query()
    unknown_f8['shadow'] = shadow_query(0xF8, None, None, low_bits={2: 0}, high_bits={7: 1})
    _symbolic_data(unknown_f8['snapshot'], 0xF8, None, {2: 0})
    _symbolic_data(unknown_f8['snapshot'], 0xF9, None, {7: 1})
    yield _case('post-f8-partial', operation, unknown_f8)
    yield from _variants('post', operation, post_query, (
        ('entry-unadmitted', {'entry': 'Unadmitted'}),
        ('interference-unadmitted', {'snapshot.assumptions.noInterference': None}),
        ('p2-missing', {'p2': None}),
        ('p2-generation-missing', {'p2.generation': None}),
        ('p2-hardware-claim', {'p2.evidenceClass': 'ActualHardwareObservation'}),
        ('p2-word-refused', {'p2.widthBits': 16}),
        ('tm2-missing', {'tm2': None}),
        ('tm2-generation-missing', {'tm2.generation': None}),
        ('tm2-hardware-claim', {'tm2.evidenceClass': 'ActualHardwareObservation'}),
        ('tm2-byte-refused', {'tm2.widthBits': 8, 'tm2.value': 0x03}),
        ('tm2-odd-address', {'tm2.address': 0x39}),
        ('tm2-generation-distinct', {'tm2.generation': 'M2cx.5CC2.1',
                                     'offPage.025A.generation': 'M2cx.5CC2.2'}),
        ('page-unknown', {'snapshot.registers.lrb': None}),
        ('page-unreviewed', {'snapshot.registers.lrb': 0x0060}),
        ('shadow-fa-refused', {'shadow.address': 0xFA}),
        ('shadow-stale', {'shadow.low.generation': 'StaleF8'}),
        ('ie-boundary-unknown', {'secondIeBoundary': None}),
        ('ie-boundary-denied', {'secondIeBoundary': False}),
        ('pswh-partial', {'snapshot.registers.dd': None, 'snapshot.registers.mie': None,
                           'snapshot.registers.cf': None, 'snapshot.registers.hc': 1}),
    ))


def cases():
    for suite in (lineage_cases, pre_cases, ie_cases, post_cases, retention_cases, return_cases, composition_cases):
        yield from suite()
