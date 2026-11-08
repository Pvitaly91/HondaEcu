"""Closed invented inputs with frozen M2df reference records for boundary checks."""
from copy import deepcopy

from alternate_parser_response_checksum.corpus import composition_cases, context, snapshot as m2df_snapshot
from alternate_parser_response_checksum.reference_oracle import expected as frozen_expected

FRAGMENT = 'detached_0240_0241_transform'
PROJECTION = 'm2df_candidate_to_detached_0240'
INGRESS = 'epilogue_0244_ingress_comparison'
BASE = 'a9eeb45292a120711bb1adf918385675c2456409'
FINGERPRINT = 'a1c554e17305f199effbc2e3aae2b42ab83081da7e527b4eeeab181faf691e55'
PREMISES = {'cpuProjection': True, 'noInterference': True, 'ordinaryInternalRam': True}


def detached(r5=14, status=2, *, bits=None, registers=None):
    state = {'registers': {'lrb': 0x7E, **(registers or {})},
             'memory': {'03F5': r5, '0356': status},
             'generations': {'03F5': 'InventedCounter', '0356': 'InventedStatus'},
             'knownBits': {} if bits is None else bits,
             'registerGenerations': {}, 'registerKnownBits': {}}
    return {'sourceId': 'M2dgReviewed0240_0241', 'entryPc': 0x0240, 'inputClass': 'SyntheticTestInput',
            'assumptions': {'noInterference': True, 'ordinaryInternalRam': True}, 'state': state}


def frozen_source(case):
    return {'baseSha': BASE, 'sourceFingerprint': FINGERPRINT, 'operation': case['operation'],
            'input': deepcopy(case['input']), 'result': frozen_expected(case)}


def selector_source(**values):
    return frozen_source({'operation': 'alternate_response_selector',
                          'input': {'snapshot': m2df_snapshot(**values), 'context': context()}})


def fragment_cases():
    for name, query in (
        ('minimum', detached(0, 0)),
        ('nibble-edge', detached(15, 63, registers={'cf': 1, 'dd': 1, 'hc': 0})),
        ('wrap-status-same', detached(255, 255, registers={'al': 0, 'ah': 0xAB, 'dd': 0})),
        ('partial-counter', detached(None, 64, bits={'03F5.7': 0, '03F5.0': 1, '03F5.1': 1,
                                                        '03F5.2': 1, '03F5.3': 1})),
        ('partial-status-set', detached(16, None, bits={'0356.6': 1, '0356.3': 0})),
        ('partial-status-clear', detached(16, None, bits={'0356.6': 0, '0356.3': 1})),
        ('unknown-data', detached(None, None)),
        ('partial-a', detached(registers={'al': None, 'ah': 0x80, 'cf': None, 'dd': None, 'scb': None})),
        ('retained-pointer-context', detached(registers={'al': 1, 'ah': 2, 'cf': 1, 'dd': 1,
                                                         'mie': 1, 'otherPsw': 0x0020,
                                                         'usp': 0x0180, 'ssp': 0x047E, 'scb': 7})),
        ('wrong-pc', {**detached(), 'entryPc': 0x0241}),
        ('fake-epilogue-entry', {**detached(), 'entryPc': 0x0244}),
        ('wrong-source', {**detached(), 'sourceId': 'UnreviewedSource'}),
        ('native-claim', {**detached(), 'inputClass': 'ActualNativeObservation'}),
        ('fake-uart', {**detached(), 'actualTxCompletion': True}),
        ('bad-input', None),
        ('wrong-lrb', detached(registers={'lrb': 0x007D})),
        ('unqualified-sfr-page', detached(registers={'lrb': 0})),
        ('unknown-bank', detached(registers={'lrb': None})),
        ('non-byte', detached(256)),
        ('unknown-ram-map', {**detached(), 'assumptions': {'noInterference': True, 'ordinaryInternalRam': None}}),
        ('interference', {**detached(), 'assumptions': {'noInterference': False, 'ordinaryInternalRam': True}}),
        ('fake-width', {**detached(), 'assumptions': {'noInterference': True, 'ordinaryInternalRam': True, 'width': 16}}),
        ('contradictory-status-bits', detached(1, 0, bits={'0356.6': 1})),
    ):
        yield {'id': 'fragment-' + name, 'operation': FRAGMENT, 'input': query}
    for name, slot, generation in (
        ('no-counter-generation', '03F5', None),
        ('no-status-generation', '0356', None),
        ('counter-collision', '03F5', 'M2dg:DATA:0240:1'),
        ('status-collision', '0356', 'M2dg:DATA:0241:2'),
    ):
        query = detached()
        query['state']['generations'][slot] = generation
        yield {'id': 'fragment-' + name, 'operation': FRAGMENT, 'input': query}
    query = detached()
    for key in ('memory', 'generations'):
        del query['state'][key]['0356']
    yield {'id': 'fragment-missing-status-slot', 'operation': FRAGMENT, 'input': query}


def boundary_cases():
    length = selector_source(r5=2, r2=7)
    table = selector_source()
    negated = selector_source(r5=4, r2=4, r6=1)
    unknown_al = selector_source(r5=4, r2=4, r6=None)
    direct = selector_source(r5=5, r2=4)
    composed = {row['id']: frozen_source(row) for row in composition_cases()
                if row['id'] in ('composition-table', 'composition-epilogue', 'composition-old-bit-clear')}
    forged = deepcopy(length)
    forged['result']['prospectiveStbufIntent']['actualWrite'] = True
    fake_tx = deepcopy(length)
    fake_tx['result']['actualTransmission'] = True
    for name, source, premises in (
        ('length', length, PREMISES),
        ('table', table, PREMISES),
        ('negated', negated, PREMISES),
        ('unknown-al', unknown_al, PREMISES),
        ('composed', composed['composition-table'], PREMISES),
        ('wrong-boundary', direct, PREMISES),
        ('missing-alternate', composed['composition-old-bit-clear'], PREMISES),
        ('missing-assumption', length, {**PREMISES, 'cpuProjection': None}),
        ('unsupported-memory', length, {**PREMISES, 'ordinaryInternalRam': False}),
        ('fake-transmit-ready', length, {**PREMISES, 'txReady': True}),
        ('fake-stbuf-write', forged, PREMISES),
        ('fake-transmission', fake_tx, PREMISES),
        ('wrong-source-identity', {**length, 'sourceFingerprint': '0' * 64}, PREMISES),
        ('no-replay-input', {key: value for key, value in length.items() if key != 'input'}, PREMISES),
    ):
        yield {'id': 'projection-' + name, 'operation': PROJECTION,
               'input': {'source': deepcopy(source), 'assumptions': dict(premises)}}
    for name, source, entry in (
        ('distinct', direct, detached(registers={'al': 9, 'ah': 0, 'cf': 1, 'scb': 0})),
        ('equal-al-distinct-path', direct, detached(4, None, bits={'0356.6': 1},
                                                    registers={'al': 5, 'ah': 0, 'cf': 0, 'dd': 0})),
        ('unknown-context', direct, detached(None, None)),
        ('composed-direct', composed['composition-epilogue'], detached()),
        ('wrong-direct-pc', length, detached()),
        ('unproved-detached', direct, {**detached(), 'entryPc': 0x0244}),
        ('fake-direct-history', {**direct, 'result': {**direct['result'], 'journal': [{}]}}, detached()),
    ):
        yield {'id': 'ingress-' + name, 'operation': INGRESS,
               'input': {'source': deepcopy(source), 'detached': entry}}


def cases():
    yield from fragment_cases()
    yield from boundary_cases()
