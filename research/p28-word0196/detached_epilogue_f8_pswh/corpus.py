"""Invented fixtures and frozen independent records from earlier source scopes."""
from copy import deepcopy

from alternate_parser_response_checksum.corpus import context, snapshot as parser_snapshot
from alternate_parser_response_checksum.reference_oracle import expected as m2df_expected
from detached_post_stbuf_0240_0241.corpus import detached as detached_snapshot
from detached_post_stbuf_0240_0241.reference_oracle import expected as m2dg_expected

MODEL = 'detached_epilogue_0244_0246'
ADAPTER = 'epilogue_ingress_adapter'
COMPARE = 'compare_epilogue_ingresses'
PREMISES = {'noInterference': True, 'memoryModel': 'ConditionalDocumentedInternalRam', 'pswhAlias': True}
SHARED = ('InventedCurrentLow', 'InventedCurrentHigh')
DIRECT = 'DirectM2dfIngress'
DETACHED = 'DetachedM2dgIngress'


def slot(value, generation, bits=None):
    return {'value': value, 'generation': generation, 'knownBits': {} if bits is None else bits}


def snapshot(low=0xAB, high=0x2B, *, low_bits=None, high_bits=None, generations=SHARED,
             writer=None, events=(), registers=None, premises=None):
    return {'sourceId': 'M2dhReviewed0244_0246', 'entryPc': 0x0244, 'entryClass': 'DetachedSymbolic0244',
            'assumptions': {**PREMISES, **(premises or {})},
            'registers': {'al': 0x42, 'ah': None, 'cf': 1, 'hc': 1, 'dd': 0, 'zf': 1, 'mie': 1,
                          'otherPsw': 0x0A20, **(registers or {})},
            'registerGenerations': {'al': 'InventedOldAL', 'ah': 'InventedOldAH'},
            'registerKnownBits': {'ah': {'7': 1}},
            'shadow': {'low': slot(low, generations[0], low_bits), 'high': slot(high, generations[1], high_bits),
                       'writer': writer, 'events': list(events)}}


def direct_query(*, r5=5, r2=4, low=0xAB, high=0x2B, generations=SHARED):
    original = parser_snapshot(r5=r5, r2=r2)
    original['memory'].update({'00F8': low, '00F9': high})
    original['generations'].update(dict(zip(('00F8', '00F9'), generations, strict=True)))
    original['registers'].update(cf=0, hc=0, dd=0, mie=1, otherPsw=0x0A20)
    inputs = {'snapshot': original, 'context': context()}
    result = m2df_expected({'operation': 'alternate_response_selector', 'input': inputs})
    return {'source': {'kind': DIRECT, 'baseSha': 'a9eeb45292a120711bb1adf918385675c2456409',
                       'sourceFingerprint': 'a1c554e17305f199effbc2e3aae2b42ab83081da7e527b4eeeab181faf691e55',
                       'input': inputs, 'result': result},
            'assumptions': dict(PREMISES), 'shadowEvidence': {'writer': None, 'events': []}}


def detached_query(*, low=0xAB, high=0x2B, generations=SHARED, status_generation='InventedStatus',
                   include_shadow=True, cf=0):
    original = detached_snapshot(4, 0x40, registers={'al': 5, 'ah': 0, 'cf': cf, 'dd': 0, 'mie': 1,
                                                       'otherPsw': 0x0A20})
    original['state']['generations']['0356'] = status_generation
    if include_shadow:
        original['state']['memory'].update({'00F8': low, '00F9': high})
        original['state']['generations'].update(dict(zip(('00F8', '00F9'), generations, strict=True)))
    result = m2dg_expected({'operation': 'detached_0240_0241_transform', 'input': original})
    return {'source': {'kind': DETACHED, 'baseSha': 'b20f1341219888afd72b950e4a592e18b0e3f02a',
                       'sourceFingerprint': '466c2a69e86de5f56058166d28e6c82e93243caa84f7655a730957d12da98470',
                       'input': original, 'result': result},
            'assumptions': dict(PREMISES), 'shadowEvidence': {'writer': None, 'events': []}}


def write_event(address, width, generation, value):
    return {'address': address, 'widthBits': width, 'generation': generation, 'value': value}


def fragment_cases():
    writer = {'pc': 0x54E5, 'generation': 'InventedPair'}
    pair = ('InventedPair', 'InventedPair')
    for name, value in (
        ('zero', snapshot(0, 0)),
        ('low-ff', snapshot(255, 0)),
        ('high-ff', snapshot(0, 255)),
        ('both-ff', snapshot(255, 255)),
        ('little-endian', snapshot(0x34, 0x12)),
        ('unknown-high', snapshot(0, None)),
        ('nonzero-low-unknown-high', snapshot(0x80, None)),
        ('unknown-low-known-high', snapshot(None, 1)),
        ('partial-nonzero', snapshot(None, None, high_bits={'7': 1})),
        ('partial-all-zero', snapshot(None, 0, low_bits={str(i): 0 for i in range(8)})),
        ('unknown-all', snapshot(None, None)),
        ('mie-already-zero', snapshot(0x80, 0, registers={'mie': 0})),
        ('unknown-mie-other-psw', snapshot(registers={'mie': None, 'otherPsw': None, 'cf': None})),
        ('retained-context', snapshot(registers={'lrb': 0, 'scb': 7, 'usp': 0x0201, 'ssp': 0x047E})),
        ('candidate-qualified', snapshot(generations=pair, writer=writer)),
        ('candidate-stale', snapshot(generations=('InventedPair', 'InventedLaterHigh'), writer=writer)),
        ('unknown-generation', snapshot(generations=(None, 'InventedLaterHigh'), writer=writer)),
        ('candidate-mismatched-value', snapshot(0xAA, 0x2B, generations=pair, writer=writer)),
        ('candidate-unknown-pc', snapshot(generations=pair, writer={'pc': 0x54F0, 'generation': 'InventedPair'})),
        ('odd-word-overlap-same-value', snapshot(generations=pair, writer=writer,
                                              events=[write_event(0xF9, 16, 'InventedLaterPair', 0x2BAB)])),
        ('only-high-overlap', snapshot(generations=pair, writer=writer,
                                       events=[write_event(0xF9, 8, 'InventedLaterHigh', 0x2B)])),
        ('outside-writer', snapshot(generations=pair, writer=writer,
                                     events=[write_event(0xFA, 16, 'InventedOther', 0x02A0)])),
        ('unknown-footprint', snapshot(generations=pair, writer=writer,
                                       events=[write_event(None, 8, None, None)])),
        ('generation-reuse', snapshot(generations=pair, writer=writer,
                                       events=[write_event(0xFA, 16, 'InventedPair', 0)])),
        ('unqualified-ram', snapshot(premises={'memoryModel': 'Unknown'})),
        ('unqualified-alias-after-load', snapshot(premises={'pswhAlias': False})),
        ('interference', snapshot(premises={'noInterference': None})),
        ('invalid-source', {**snapshot(), 'sourceId': 'M2cq0295'}),
        ('invalid-pc', {**snapshot(), 'entryPc': 0x0249}),
        ('invalid-word-byte', snapshot(0x100, 0)),
        ('contradictory-bits', snapshot(0, 0, low_bits={'0': 1})),
        ('load-generation-collision', snapshot(generations=('M2dh:0244:AL', 'InventedHigh'))),
        ('mask-generation-collision', snapshot(generations=('M2dh:0246:MIE', 'InventedHigh'))),
        ('fake-rti', {**snapshot(), 'actualFramePop': True}),
        ('bad-input', None),
    ):
        yield {'id': 'fragment-' + name, 'operation': MODEL, 'input': value}


def ingress_cases():
    direct, detached = direct_query(), detached_query()
    fake = deepcopy(detached)
    fake['source']['result']['executionAuthority']['actualStbufWrite'] = True
    for name, value in (
        ('direct', direct), ('detached', detached),
        ('direct-wrong-branch', direct_query(r5=2)),
        ('missing-shadow', detached_query(include_shadow=False)),
        ('incomplete-detached', detached_query(status_generation=None)),
        ('fake-native', fake),
        ('wrong-fingerprint', {**direct, 'source': {**direct['source'], 'sourceFingerprint': '0' * 64}}),
        ('missing-source', {key: row for key, row in direct.items() if key != 'source'}),
        ('fake-memory-mapping', {**direct, 'assumptions': {**PREMISES, 'physicalMapVerified': True}}),
    ):
        yield {'id': 'adapter-' + name, 'operation': ADAPTER, 'input': value}
    for name, left, right in (
        ('equal-local-distinct-paths', direct, detached),
        ('equal-word-different-generations', direct, detached_query(generations=('OtherLow', 'OtherHigh'))),
        ('different-word', direct, detached_query(high=0x2A)),
        ('conflicting-incoming-carry', direct, detached_query(cf=1)),
        ('unknown-high-byte', direct, detached_query(high=None)),
        ('same-source-kind', direct, direct),
        ('partial-prefix', {**direct, 'assumptions': {**PREMISES, 'pswhAlias': False}}, detached),
        ('overlap-keeps-distinct', direct,
         {**detached, 'shadowEvidence': {'writer': None, 'events': [write_event(0xF9, 16, 'OtherGen', 0x2BAB)]}}),
    ):
        yield {'id': 'compare-' + name, 'operation': COMPARE, 'input': {'direct': left, 'detached': right}}


def cases():
    yield from fragment_cases()
    yield from ingress_cases()
