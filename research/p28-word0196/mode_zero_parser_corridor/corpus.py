"""Invented typed cases for the bounded parser prefix and independent suffixes."""
from copy import deepcopy

from length_checksum_dataflow.corpus import fixture

CORRIDOR = 'mode_zero_corridor_029d'
SUFFIX = 'mode_zero_detached_suffix'
COMPOSE = 'mode_zero_parser_step'


def detached(registers=None):
    return {'sourceId': 'M2diReviewedModeZero', 'entryPc': 0x029D, 'entryClass': 'DetachedEntry029D',
            'assumptions': {'noInterference': True},
            'state': {'registers': {'al': 0x35, 'ah': 0xA6, 'dd': 1, 'cf': 1, 'hc': 1, 'zf': 0,
                                    **(registers or {})},
                      'registerGenerations': {'al': 'InventedAL', 'ah': 'InventedAH', 'zf': 'InventedZF'},
                      'registerKnownBits': {}, 'memory': {'0356': 0x40},
                      'generations': {'0356': 'InventedModeStatus'}, 'knownBits': {}}}


def suffix(pc=0x02A8, old=1, al=0xFE, ah=0x42, *, al_bits=None, registers=None):
    value = detached({'al': al, 'ah': ah, 'dd': 0, 'zf': None if old is None else 1 - old,
                      **(registers or {})})
    value.update(entryPc=pc, entryClass='DetachedPostRbEntry',
                 statusHypothesis={'sourcePc': 0x029E if pc == 0x02A1 else 0x02A5,
                                   'bit': 3 if pc == 0x02A1 else 2,
                                   'value': old, 'generation': 'InventedPriorSrstatBit'})
    if al_bits is not None:
        value['state']['registerKnownBits']['al'] = dict(al_bits)
    return value


def parser(status=0x40, *, bits=None, role='Flag', registers=None, mapping='ConditionalStandardInternal207'):
    original = fixture(role)
    original['memory']['0356'] = status
    original['knownBits'] = {**{key: value for key, value in original['knownBits'].items()
                               if not key.startswith('0356.')}, **(bits or {})}
    original['registers'].update(registers or {})
    return {'sourceId': 'M2diReviewedModeZero', 'snapshot': original,
            'statusGeneration': original['generations']['0356'], 'memoryModel': mapping}


def _case(op, group, name, query):
    return {'operation': op, 'id': group + '-' + name, 'input': deepcopy(query)}


def cases():
    collision = detached()
    collision['state']['registerGenerations']['al'] = 'M2di:029D:AL'
    synthetic_status = detached()
    synthetic_status['state']['memory']['0056'] = 0xFF
    synthetic_status['state']['generations']['0056'] = 'InventedByteNotSrstatAuthority'
    for name, query in (
        ('known', detached()),
        ('unknown-context', detached({'al': None, 'ah': None, 'cf': None, 'dd': None, 'lrb': None, 'scb': None})),
        ('different-lrb', detached({'lrb': 0, 'scb': 7, 'ssp': 0x047E})),
        ('fake-status-byte', synthetic_status),
        ('conflicting-generation', collision),
        ('wrong-pc', {**detached(), 'entryPc': 0x0295}),
        ('wrong-source', {**detached(), 'sourceId': 'InventedSource'}),
        ('fake-confirmed-ingress', {**detached(), 'entryClass': 'ConfirmedEntryFrom021F'}),
        ('unqualified-interference', {**detached(), 'assumptions': {'noInterference': None}}),
        ('bad-input', None),
    ):
        yield _case(CORRIDOR, 'corridor', name, query)
    missing_generation = suffix()
    missing_generation['statusHypothesis']['generation'] = None
    missing_zf_generation = suffix()
    del missing_zf_generation['state']['registerGenerations']['zf']
    missing_al_generation = suffix()
    del missing_al_generation['state']['registerGenerations']['al']
    add_collision = suffix()
    add_collision['state']['registerGenerations']['al'] = 'M2di:02AA:AL'
    store_collision = suffix(old=0)
    store_collision['state']['registerGenerations']['ah'] = 'M2di:02AC:AH'
    aliased_memory = suffix(old=0)
    aliased_memory['state']['memory']['0007'] = 2
    aliased_memory['state']['generations']['0007'] = 'InventedDuplicateAh'
    for name, query in (
        ('first-taken', suffix(0x02A1, 0, 7)),
        ('first-add-min', suffix(0x02A1, 1, 0)),
        ('first-add-wrap', suffix(0x02A1, 1, 255)),
        ('first-add-nibble', suffix(0x02A1, 1, 15)),
        ('first-unknown-bit', suffix(0x02A1, None)),
        ('second-taken-same-value', suffix(old=0, al=0x42, ah=0x42)),
        ('second-add-wrap', suffix(al=254)),
        ('second-add-carry', suffix(al=255)),
        ('second-add-partial', suffix(al=None, al_bits={'0': 0, '1': 0, '2': 0})),
        ('second-store-partial', suffix(old=0, al=None, al_bits={'0': 0, '7': 1})),
        ('second-store-unknown', suffix(old=0, al=None, ah=None)),
        ('second-unknown-zf', suffix(registers={'zf': None})),
        ('missing-status-generation', missing_generation),
        ('missing-zf-generation', missing_zf_generation),
        ('missing-al-generation', missing_al_generation),
        ('add-dd1', suffix(registers={'dd': 1})),
        ('store-unknown-dd', suffix(old=0, registers={'dd': None})),
        ('contradictory-zf', suffix(registers={'zf': 1})),
        ('add-generation-collision', add_collision),
        ('alias-generation-collision', store_collision),
        ('alias-memory-duplication', aliased_memory),
        ('fake-srbuf-observation', {**suffix(), 'actualReceivedByte': 0x37}),
        ('wrong-post-rb-pc', {**suffix(), 'entryPc': 0x28AE}),
        ('wrong-old-bit', {**suffix(), 'statusHypothesis': {**suffix()['statusHypothesis'], 'bit': 3}}),
    ):
        yield _case(SUFFIX, 'suffix', name, query)
    missing_status = parser()
    missing_status['snapshot']['generations']['0356'] = None
    for name, query in (
        ('zero-bit6-set', parser(0x40)),
        ('zero-bit6-clear', parser(0)),
        ('zero-partial-bit6-unknown', parser(None, bits={'0356.1': 0})),
        ('zero-partial-bit6-set', parser(None, bits={'0356.1': 0, '0356.6': 1})),
        ('unknown-bit1', parser(None, bits={'0356.6': 1})),
        ('ordinary-header', parser(2, role='Header')),
        ('ordinary-flag', parser(2)),
        ('ordinary-alternate', parser(0x42)),
        ('missing-generation', missing_status),
        ('stale-generation', {**parser(), 'statusGeneration': 'InventedStaleStatus'}),
        ('wrong-generation-type', {**parser(), 'statusGeneration': 7}),
        ('unknown-lrb', parser(registers={'lrb': None})),
        ('wrong-lrb', parser(registers={'lrb': 0})),
        ('wrong-mapping', parser(mapping='ConditionalStandardInternal201')),
        ('wrong-source', {**parser(), 'sourceId': 'ForgedM2co'}),
        ('fake-execution', {**parser(), 'actualIrqDelivery': True}),
    ):
        yield _case(COMPOSE, 'compose', name, query)
