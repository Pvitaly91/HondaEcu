"""Finite invented inputs. None are native RAM or peripheral observations."""
from copy import deepcopy

from tx_ack_configuration_provenance.corpus import fixture as parent_fixture, slot, partial_slot, register_partial
from payload_consumer_tail.corpus import partial
from post_consumer_continuation.corpus import stbuf_query
from stbuf_stcon_transmit_source.corpus import CONFIG_SITES as PARENT_CONFIG_SITES
from tx_ack_configuration_provenance.corpus import READER_SITES as PARENT_READER_SITES
from .primary_sources import SOURCE_BINDING

OLD_ADDRESSES = tuple(sorted(parent_fixture()['memory']))
ADDRESSES = tuple(sorted(set(OLD_ADDRESSES) | {f'{a:04X}' for a in range(0x3C6, 0x3D6)}
    | {f'{0x80 + 8 * bank + part:04X}' for bank in range(8) for part in range(2)}
    | {'02CD', '0216', '0382', '0383'}))
READBACK_KEYS = ('0024', '0049', '004A', '0050', '0054', '0058', '0061', '0063')
WRITER_SITES = (0x5CA5, 0x5CA7, 0x5CA8, 0x5CA9, 0x5CAB, 0x5CAC, 0x5CAD, 0x5CAF, 0x5CB2, 0x5CB4)
MODE_SITES = (0x60BD, 0x60C0, 0x60C9, 0x60CC, 0x60CF, 0x60D2, 0x60D5, 0x60D7, 0x60DA, 0x60DD, 0x60E0, 0x60E3)
CONFIG_SITES = tuple(sorted((*PARENT_CONFIG_SITES, 0x2869, 0x288E)))
READER_SITES = tuple(sorted((*PARENT_READER_SITES, 0x3FCC, 0x3FCE, 0x3FD0, 0x3FD2, 0x3FB1, 0x3FF7)))
REACHING_SITES = tuple(sorted((0x5CB4, 0x60C9, 0x60CC, 0x276A, 0x27D0, 0x2710)))
JOIN_SITES = tuple(sorted(set((*WRITER_SITES, *MODE_SITES, *CONFIG_SITES, *READER_SITES, 0x2995))))
ENTRIES = ('At60BD', 'Compare3cb', 'SymbolicCarryTail')
PATHS = ('WriterLocalEffect', 'WriterWindowRetention', 'WriterTo60C9', 'Caller276ATo27D0', 'ResetTo60C9')
STAGES = ('IndexedWriter', 'ModeProducer', 'ConfigurationCaller', 'ReaderCaller')


def fixture(entry=None):
    q = parent_fixture()
    for key in ADDRESSES:
        q['memory'].setdefault(key, 0)
    q['memory'].update({'0208': 0, '0216': 0})
    q['generations'] = {key: 'InventedM2cu:' + key for key in ADDRESSES}
    for key, byte in (('0024', 0xA0), ('0058', 0x10), ('0061', 0x80), ('0063', 0x55)):
        q['sfrReadbacks'][key] = slot(byte, 'Supplied:' + key)
    if entry is not None:
        q['entry'] = entry
    return q


def indexed_event(generation='AdcSample1'):
    return {'kind': 'IndexedWriter', 'id': 'sample', 'sourcePc': 0x5CB4,
        'p2': slot(0xA0, 'P2Sample'), 'adcr0h': slot(0x80, 'Adc0Sample'),
        'generation': generation, 'scb': 0}


def reaching_query(path='WriterLocalEffect'):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'initial': slot(0x80, 'InitialData03cb'), 'events': [indexed_event()], 'path': path,
        'entryGeneration': 'AdcSample1', 'requestedGeneration': 'AdcSample1',
        'noInterference': True, 'claim': 'ConditionalOnly'}


def join_query():
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'snapshot': fixture(), 'modeEntry': 'At60BD', 'stageOrder': list(STAGES),
        'handoffs': {'writerToMode': True, 'modeToConfiguration': True, 'configurationToReader': True},
        'noInterference': True, 'stbufQuery': stbuf_query(True), 'claim': 'ConditionalOnly'}


def cases():
    for byte in range(256):
        q = fixture(); q['sfrReadbacks']['0024']['value'] = byte
        yield {'id': f'indexed-p2-{byte:02X}', 'operation': 'data03cb_indexed_writer', 'input': q}
        q = fixture('At60BD'); q['memory']['03CB'] = byte
        yield {'id': f'mode-03cb-{byte:02X}', 'operation': 'mode_producer_extended', 'input': q}
        q = fixture(); q['sfrReadbacks']['0058']['value'] = byte
        yield {'id': f'reader-adscan-{byte:02X}', 'operation': 'configuration_reader_caller', 'input': q}
    operations = ('data03cb_indexed_writer', 'mode_producer_extended', 'configuration_caller', 'configuration_reader_caller')
    for op in operations:
        for bank in (*range(8), None):
            q = fixture('At60BD' if op == 'mode_producer_extended' else None); q['registers']['scb'] = bank
            yield {'id': f'{op}-bank-{bank}', 'operation': op, 'input': q}
        for assumption in ('noInterference', 'ordinaryByteSemantics'):
            for value in (False, None):
                q = fixture('At60BD' if op == 'mode_producer_extended' else None); q['assumptions'][assumption] = value
                yield {'id': f'{op}-{assumption}-{value}', 'operation': op, 'input': q}
        q = fixture('At60BD' if op == 'mode_producer_extended' else None)
        q['sfrReadbacks']['0063']['generation'] = 'ConditionalEffect:' + op + ':0000:1'
        yield {'id': f'{op}-namespace', 'operation': op, 'input': q}
    patterns = ({}, {7: 0}, {7: 1}, {5: 1, 6: 0, 7: 1}, {4: 1, 5: 1, 6: 0, 7: 1}, {bit: (0x80 >> bit) & 1 for bit in range(8)})
    for n, bits in enumerate(patterns):
        for address in ('0024', '0061', '0063'):
            q = fixture(); partial_slot(q['sfrReadbacks'][address], bits)
            yield {'id': f'indexed-partial-{address}-{n}', 'operation': 'data03cb_indexed_writer', 'input': q}
        q = partial(fixture('At60BD'), '03CB', bits)
        yield {'id': f'mode-partial03cb-{n}', 'operation': 'mode_producer_extended', 'input': q}
    for entry in ENTRIES:
        for carry in (0, 1, None):
            for dd in (0, 1, None):
                q = fixture(entry); q['registers'].update(cf=carry, dd=dd)
                yield {'id': f'mode-{entry}-cf{carry}-dd{dd}', 'operation': 'mode_producer_extended', 'input': q}
        for lrb in (None, 0, 0x40, 0x41, 0x5F):
            q = fixture(entry); q['registers']['lrb'] = lrb
            yield {'id': f'mode-{entry}-lrb{lrb}', 'operation': 'mode_producer_extended', 'input': q}
    for value in (1, 0xFF, None):
        q = fixture('At60BD'); q['memory']['0208'] = value
        yield {'id': f'mode-r0-{value}', 'operation': 'mode_producer_extended', 'input': q}
    for value in (0, 8, None):
        q = fixture('Compare3cb'); q['memory']['0216'] = value
        yield {'id': f'mode-suffix-bit3-{value}', 'operation': 'mode_producer_extended', 'input': q}
    for value in (0, 2, None):
        q = fixture(); q['memory']['0356'] = value
        yield {'id': f'config-guard-{value}', 'operation': 'configuration_caller', 'input': q}
    for key in ('004A', '0050', '0054', '0049', '0058'):
        for byte in (0, None):
            q = fixture(); q['sfrReadbacks'][key]['value'] = byte
            yield {'id': f'reader-short-{key}-{byte}', 'operation': 'configuration_reader_caller', 'input': q}
    for value in (None, 0xFA, 0):
        q = fixture(); q['memory']['00FA'] = value; q['memory']['00FB'] = None if value is None else 0
        yield {'id': f'reader-word-{value}', 'operation': 'configuration_reader_caller', 'input': q}
    for path in PATHS:
        yield {'id': 'reaching-' + path, 'operation': 'data03cb_reaching_definitions', 'input': reaching_query(path)}
    for field in ('entryGeneration', 'requestedGeneration', 'noInterference', 'sourceBinding'):
        for value in (None,):
            q = reaching_query(); q[field] = value
            yield {'id': 'reaching-missing-' + field, 'operation': 'data03cb_reaching_definitions', 'input': q}
    for field in ('entryGeneration', 'requestedGeneration'):
        q = reaching_query(); q[field] = 'Stale'
        yield {'id': 'reaching-stale-' + field, 'operation': 'data03cb_reaching_definitions', 'input': q}
    for address, width, byte in ((0x3CB, 8, 0x80), (0x3CA, 16, 0x8077), (0x3CB, 16, 0x8077), (0x3CC, 16, 0x80), (None, 8, 0)):
        q = reaching_query(); q['events'].append({'kind': 'AlternateStore', 'id': 'alternate', 'address': address, 'widthBits': width, 'value': byte, 'generation': 'Alternate2'})
        yield {'id': f'reaching-alternate-{address}-{width}', 'operation': 'data03cb_reaching_definitions', 'input': q}
    for key, value in (('sourcePc', None), ('sourcePc', 0x5CAF), ('scb', None), ('generation', 'InitialData03cb')):
        q = reaching_query(); q['events'][0][key] = value
        yield {'id': f'reaching-badwriter-{key}-{value}', 'operation': 'data03cb_reaching_definitions', 'input': q}
    q = reaching_query(); partial_slot(q['events'][0]['p2'], {})
    yield {'id': 'reaching-unknown-index', 'operation': 'data03cb_reaching_definitions', 'input': q}
    q = reaching_query(); q['events'].append({'kind': 'UnknownWriter', 'id': 'unknown'})
    yield {'id': 'reaching-unknown-writer', 'operation': 'data03cb_reaching_definitions', 'input': q}
    q = reaching_query(); q['events'] = []
    yield {'id': 'reaching-no-writer', 'operation': 'data03cb_reaching_definitions', 'input': q}
    for key in ('writerToMode', 'modeToConfiguration', 'configurationToReader'):
        for value in (False, None):
            q = join_query(); q['handoffs'][key] = value
            yield {'id': f'join-handoff-{key}-{value}', 'operation': 'cross_block_source_join', 'input': q}
    for byte in (0, 0x7F, 0x80, 0xFF, None):
        q = join_query(); q['snapshot']['sfrReadbacks']['0061']['value'] = byte
        yield {'id': f'join-adc-{byte}', 'operation': 'cross_block_source_join', 'input': q}
    q = join_query(); q['snapshot']['sfrReadbacks']['0024']['value'] = 0
    yield {'id': 'join-wrong-index', 'operation': 'cross_block_source_join', 'input': q}
    q = join_query(); q['stageOrder'].reverse()
    yield {'id': 'join-wrong-order', 'operation': 'cross_block_source_join', 'input': q}
    for claim in ('ActualBufferWrite', 'IRQ'):
        q = join_query(); q['stbufQuery']['claim'] = claim
        yield {'id': 'join-nested-' + claim, 'operation': 'cross_block_source_join', 'input': q}
    q = join_query(); q['stbufQuery']['premises'] = {key: None for key in q['stbufQuery']['premises']}
    yield {'id': 'join-unknown-peripheral-premises', 'operation': 'cross_block_source_join', 'input': q}
    for operation, factory in (('data03cb_reaching_definitions', reaching_query), ('cross_block_source_join', join_query)):
        for claim in ('NativeOwner', 'ActualHardware', 'RuntimeAdmission'):
            q = factory(); q['claim'] = claim
            yield {'id': f'{operation}-claim-{claim}', 'operation': operation, 'input': q}
        for binding in (None, {}, {**SOURCE_BINDING, 'base': 'Wrong'}):
            q = factory(); q['sourceBinding'] = binding
            yield {'id': f'{operation}-binding-{len(str(binding))}', 'operation': operation, 'input': q}
