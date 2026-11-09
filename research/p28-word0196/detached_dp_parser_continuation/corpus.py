"""Invented inputs for independent proof of the two qualified source operations."""
from copy import deepcopy

TRANSFORM = 'detached_02b0_02b2_transform'
QUALIFY = 'indirect_data_address_qualification'
MAP_201 = 'ConditionalStandardInternal201'
MAP_207 = 'ConditionalStandardInternal207'


def snapshot(a16=0x03F4, *, scb=0, backing_bank=None, scb_bits=None, al=None, ah=None,
             reg_bits=None, registers=None, old_dp=0x1234, mapping=MAP_207, data=None):
    if a16 is not None:
        al, ah = a16 & 255, a16 >> 8
    bank = (scb if scb is not None else 0) if backing_bank is None else backing_bank
    base = 0x0084 + 8 * bank
    memory = {'03F4': 0x31, '03F5': 0x12, '035C': 0xA2, '0200': 0x98, '0201': 0x43, **(data or {}),
              f'{base:04X}': None if old_dp is None else old_dp & 255,
              f'{base+1:04X}': None if old_dp is None else old_dp >> 8}
    state = {'registers': {'al': al, 'ah': ah, 'dd': None, 'cf': 1, 'hc': 1, 'zf': None,
                           'lrb': 0x007E, 'scb': scb, **(registers or {})},
             'memory': memory, 'generations': {key: 'InventedData:' + key for key in memory},
             'knownBits': {}, 'registerGenerations': {'al': 'InventedAL', 'ah': 'InventedAH'},
             'registerKnownBits': {} if reg_bits is None else deepcopy(reg_bits)}
    return {'sourceId': 'M2djReviewedDetachedDp', 'entryPc': 0x02B0, 'entryClass': 'DetachedSymbolicEntry02B0',
            'inputClass': 'SyntheticTestInput', 'a16': a16, 'scbKnownBits': scb_bits or {},
            'assumptions': {'noInterference': True, 'dataMapping': mapping}, 'state': state}


def qualification(address=0x03F4, *, pc=0x02B7, scb=0, mapping=MAP_207, data=None):
    entry = snapshot(scb=scb, old_dp=address, mapping=mapping, data=data)
    base = 0x0084 + 8 * (0 if scb is None else scb)
    state = entry['state']
    return {'pc': pc, 'space': 'DATA', 'widthBits': 16 if pc == 0x02B7 else 8, 'state': state,
            'assumptions': entry['assumptions'], 'interveningWrites': [],
            'expectedDpGenerations': [state['generations'][f'{base + i:04X}'] for i in range(2)]}


def _put(case, section, name, value):
    return {'operation': case, 'id': section + '-' + name, 'input': deepcopy(value)}


def cases():
    a_from_word = snapshot(0x0201)
    a_from_word['state']['registers'].update(al=None, ah=None)
    contradictory = snapshot()
    contradictory['state']['registers']['ah'] = 1
    missing_accumulator = snapshot()
    del missing_accumulator['state']['registerGenerations']['ah']
    missing_dp = snapshot()
    del missing_dp['state']['memory']['0085']
    del missing_dp['state']['generations']['0085']
    missing_dp_generation = snapshot()
    missing_dp_generation['state']['generations']['0085'] = None
    collision = snapshot()
    collision['state']['generations']['0084'] = 'M2dj:02B0:DP.LOW'
    stale_second = snapshot(0)
    stale_second['state']['generations']['0084'] = 'M2dj:02C2:DP.HIGH'
    partial_value = snapshot(0x0200, data={'0200': None, '0201': 0})
    partial_value['state']['knownBits']['0200.4'] = 1
    for name, value in (
        ('even-local-alias', snapshot()),
        ('even-ordinary', snapshot(0x0200)),
        ('odd-byte', snapshot(0x0201)),
        ('zero-remap', snapshot(0)),
        ('zero-external-201', snapshot(0, mapping=MAP_201)),
        ('odd-srbuf', snapshot(0x0055, data={'0055': 0x3C})),
        ('odd-stbuf', snapshot(0x0051, data={'0051': 0x3C})),
        ('word-contains-srbuf', snapshot(0x0054)),
        ('external-word', snapshot(0xFFFE)),
        ('odd-ffff', snapshot(0xFFFF)),
        ('word-self-alias', snapshot(0x0084)),
        ('same-value-write', snapshot(0x0200, old_dp=0x0200)),
        ('different-bank', snapshot(0x0200, scb=7)),
        ('resolved-scb-bits', snapshot(0x0200, scb=None, backing_bank=5, scb_bits={'0': 1, '1': 0, '2': 1})),
        ('unknown-scb', snapshot(scb=None)),
        ('partial-scb', snapshot(scb=None, scb_bits={'0': 1})),
        ('conflicting-scb', snapshot(scb=0, scb_bits={'1': 1})),
        ('a16-refines-halves', a_from_word),
        ('contradictory-a16', contradictory),
        ('unknown-word-zero', snapshot(None, al=0, ah=None)),
        ('known-nonzero-unknown-carry', snapshot(None, ah=3, reg_bits={'al': {'1': 1}})),
        ('partial-even-unknown-target', snapshot(None, ah=3, reg_bits={'al': {'0': 0, '1': 1}})),
        ('partial-source-value', partial_value),
        ('dd0-fixed-word-form', snapshot(registers={'dd': 0})),
        ('dd1-fixed-word-form', snapshot(registers={'dd': 1})),
        ('missing-a-generation', missing_accumulator),
        ('missing-dp-slot', missing_dp),
        ('missing-dp-generation', missing_dp_generation),
        ('initial-generation-collision', collision),
        ('later-generation-collision', stale_second),
        ('wrong-source', {**snapshot(), 'sourceId': 'InventedUnreviewed'}),
        ('wrong-pc', {**snapshot(), 'entryPc': 0x02AE}),
        ('fake-native-class', {**snapshot(), 'inputClass': 'ActualHardwareObservation'}),
        ('unknown-mapping', snapshot(mapping='Unknown')),
        ('fake-srbuf', {**snapshot(), 'actualSrbufRead': True}),
        ('bad-input', None),
    ):
        yield _put(TRANSFORM, 'transform', name, value)
    aligned_partial = qualification(None)
    aligned_partial['state']['memory']['0085'] = 0x02
    aligned_partial['state']['knownBits'].update({f'0084.{bit}': 0 for bit in range(1, 8)})
    missing_target_generation = qualification()
    missing_target_generation['state']['generations']['03F5'] = None
    stale_bank = qualification(scb=7)
    stale_bank['expectedDpGenerations'] = qualification()['expectedDpGenerations']
    for name, value in (
        ('ordinary-word', qualification(0x0200)),
        ('odd-word-aligned', qualification(0x0201)),
        ('odd-byte-unaligned', qualification(0x0201, pc=0x02C5)),
        ('partial-word-alignment-consensus', aligned_partial),
        ('word-ffff-no-wrap', qualification(0xFFFF)),
        ('byte-ffff-no-wrap', qualification(0xFFFF, pc=0x02C5)),
        ('local-alias', qualification()),
        ('external-201', qualification(mapping=MAP_201)),
        ('shadow', qualification(0x00F8, data={'00F8': 1, '00F9': 2})),
        ('unknown-pointer', qualification(None)),
        ('unknown-bank', qualification(scb=None)),
        ('write-only-pair', qualification(0x0050)),
        ('read-sensitive-pair', qualification(0x0055)),
        ('potential-sfr', qualification(0x0056, pc=0x02C5)),
        ('architecture-alias-unqualified', qualification(0x0006)),
        ('memory-missing', qualification(0x0204)),
        ('target-generation-missing', missing_target_generation),
        ('wrong-bank-generation', stale_bank),
        ('no-dp-generation', {**qualification(), 'expectedDpGenerations': [None, 'InventedData:0085']}),
        ('wrong-space', {**qualification(), 'space': 'PROGRAM'}),
        ('wrong-width', {**qualification(), 'widthBits': 8}),
        ('wrong-pc', {**qualification(), 'pc': 0x02B1}),
        ('overflow-writer', {**qualification(), 'interveningWrites': [{'address': 0x10000, 'widthBits': 8,
                                                                       'generation': 'OutOfRange'}]}),
        ('same-value-dp-writer', {**qualification(), 'interveningWrites': [{'address': 0x0085, 'widthBits': 16,
                                                                           'generation': 'InventedData:0085'}]}),
        ('overlapping-target-word', {**qualification(), 'interveningWrites': [{'address': 0x03F5, 'widthBits': 16,
                                                                               'generation': 'LaterWord'}]}),
        ('unknown-indirect-writer', {**qualification(), 'interveningWrites': [{'address': None, 'widthBits': 8,
                                                                               'generation': 'UnknownWriter'}]}),
        ('disjoint-writer', {**qualification(), 'interveningWrites': [{'address': 0x0310, 'widthBits': 8,
                                                                       'generation': 'Disjoint'}]}),
        ('bad-input', None),
    ):
        yield _put(QUALIFY, 'qualification', name, value)
