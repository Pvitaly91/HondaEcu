"""Invented finite inputs, separated from hardware observations and expected values."""
from copy import deepcopy

from stbuf_stcon_transmit_source.corpus import fixture as old_fixture, lineage_query
from post_consumer_continuation.corpus import stbuf_query
from payload_consumer_tail.corpus import partial

READER_SITES = (0x3FD4, 0x3FD7, 0x3FD9, 0x3FDB, 0x3FDD, 0x3FDF, 0x3FE1,
    0x3FE3, 0x3FE5, 0x3FE7, 0x3FE9, 0x3FEB, 0x3FEF, 0x3FF1, 0x3FF5)
PRODUCER_SITES = (0x60C9, 0x60CC, 0x60CF, 0x60D2, 0x60D5)
READBACK_KEYS = ('0049', '004A', '0050', '0054')
SOURCE_BINDING = {'baseSha': '659b236a82bbea92d32666df7a1042106c5bb603',
    'readerProofSha256': '8459e8badba71c23936977958ce63acc77f5300a92a7e4174471f022d65df17c',
    'producerProofSha256': '8360d42b1de2ce884f8464bb6d8574503b7f8e1c96a0c0328463f4ccdfb86d67',
    'reachingProofSha256': 'aeb2484a5948ea6e70f0a2d01aaae6bcd71aa7c4dfa9b08f36b2524773d6a032',
    'primaryProofSha256': 'c7aacc0a97991c80d9690853c134a18f483181fe56e9813c366c19d80a7498d6'}
RULE_KEYS = ('TX_READY_REQUEST_AT_UART_START', 'GENERIC_QUALIFIED_INTERRUPT_ENTRY_ACK',
    'STBUF_WRITE_ACK', 'TX_REQUEST_READ_ACK', 'AUTOMATIC_REASSERT_WITHOUT_NEW_DATA',
    'ACTIVE_PREVIOUS_AND_BUFFERED_NEXT', 'FULL_HOLDING_BUFFER_THIRD_WRITE',
    'HARDWARE_SET_SOFTWARE_CLEAR_PRIORITY', 'TX_MODE_CHANGE_DURING_TRANSFER',
    'CLOCK_RELOAD_CHANGE_DURING_TRANSFER', 'SEPARATE_TX_COMPLETE_INTERRUPT',
    'STANDARD_RESET_DESCRIPTORS', 'CURRENT_NATIVE_READY_OR_RESET_STATE', 'IE_POLARITY')
PATHS = ('ConfigurationSuffix', 'ReaderWindow', 'ProducerToConfiguration',
         'ConfigurationTo2995', 'ReaderTo2995')


def slot(value=None, generation='SuppliedSymbolic'):
    return {'value': value, 'knownBits': {}, 'generation': generation}


def fixture(entry=None):
    value = old_fixture()
    value['memory']['03CB'] = 0x80
    value['generations'] = {key: 'InventedM2ct:' + key for key in value['memory']}
    value['sfrReadbacks'] = {key: slot(byte, 'Supplied:' + key) for key, byte in
        zip(READBACK_KEYS, (0xDF, 0x1E, 0x1C, 0x8C))}
    if entry is not None:
        value['entry'] = entry
    return value


def reaching_query(path='ConfigurationSuffix'):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'timelineQuery': lineage_query(), 'path': path, 'entryGeneration': 'Config1',
        'requestedGeneration': 'Config1', 'noInterference': True, 'claim': 'ConditionalOnly'}


def ack_query(rule='STBUF_WRITE_ACK'):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'rule': rule, 'applicability': 'QualifiedStandardProfile', 'claim': 'DocumentaryOnly'}


def join_query():
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'readerQuery': fixture(), 'producerQuery': fixture('Compare3cb'),
        'reachingQuery': reaching_query(), 'ackQuery': ack_query(),
        'stbufQuery': stbuf_query(True), 'claim': 'ConditionalOnly'}


def partial_slot(value, bits):
    value.update(value=None, knownBits={str(key): bit for key, bit in bits.items()})
    return value


def register_partial(value, name, bits):
    value['registers'][name.lower()] = None
    value['registerKnownBits'] = {key: bit for key, bit in value['registerKnownBits'].items()
                                if not key.startswith(name + '.')}
    value['registerKnownBits'].update({name + '.' + str(key): bit for key, bit in bits.items()})
    return value


def cases():
    for byte in range(256):
        for key in READBACK_KEYS:
            value = fixture(); value['sfrReadbacks'][key]['value'] = byte
            yield {'id': f'reader-{key}-{byte:02X}', 'operation': 'tx_configuration_reader', 'input': value}
        value = fixture('Compare3cb'); value['memory']['03CB'] = byte
        yield {'id': f'producer-cmp-{byte:02X}', 'operation': 'mode_bit1_producer', 'input': value}
        value = fixture('SymbolicCarryTail'); value['memory']['0356'] = byte
        value['registers']['cf'] = byte & 1
        yield {'id': f'producer-move-status-{byte:02X}', 'operation': 'mode_bit1_producer', 'input': value}
    patterns = ({}, {0: 0}, {0: 1}, {1: 0}, {1: 1}, {7: 0}, {7: 1},
        {bit: 0 for bit in range(8)}, {bit: (0x80 >> bit) & 1 for bit in range(8)},
        {bit: (0x1E >> bit) & 1 for bit in range(8)})
    for index, bits in enumerate(patterns):
        for key in READBACK_KEYS:
            value = fixture(); partial_slot(value['sfrReadbacks'][key], bits)
            yield {'id': f'reader-partial-{key}-{index}', 'operation': 'tx_configuration_reader', 'input': value}
        for entry, address in (('Compare3cb', '03CB'), ('Compare3cb', '0356'), ('SymbolicCarryTail', '0356')):
            value = partial(fixture(entry), address, bits)
            yield {'id': f'producer-partial-{entry}-{address}-{index}', 'operation': 'mode_bit1_producer', 'input': value}
    for byte in (0, 1, 2, 3, 0xFC, 0xFD, 0xFE, 0xFF, None):
        value = fixture(); value['memory']['0356'] = byte
        yield {'id': f'reader-guard-{byte}', 'operation': 'tx_configuration_reader', 'input': value}
    for bit in (0, 1):
        value = partial(fixture(), '0356', {1: bit})
        yield {'id': f'reader-partial-guard-{bit}', 'operation': 'tx_configuration_reader', 'input': value}
    for operation, entries in (('tx_configuration_reader', (None,)),
                               ('mode_bit1_producer', ('Compare3cb', 'SymbolicCarryTail'))):
        for entry in entries:
            for bank in (*range(8), None):
                value = fixture(entry); value['registers']['scb'] = bank
                yield {'id': f'{operation}-bank-{entry}-{bank}', 'operation': operation, 'input': value}
            for register in fixture()['registers']:
                value = fixture(entry); value['registers'][register] = None
                if register in ('al', 'ah'): register_partial(value, register.upper(), {})
                yield {'id': f'{operation}-unknown-{entry}-{register}', 'operation': operation, 'input': value}
            for lrb in (0, 0x40, 0x7E, 0x2041, 0xFFFF):
                value = fixture(entry); value['registers']['lrb'] = lrb
                yield {'id': f'{operation}-retained-lrb-{entry}-{lrb}', 'operation': operation, 'input': value}
            for assumption in ('noInterference', 'ordinaryByteSemantics'):
                for answer in (False, None):
                    value = fixture(entry); value['assumptions'][assumption] = answer
                    yield {'id': f'{operation}-premise-{entry}-{assumption}-{answer}', 'operation': operation, 'input': value}
            for area, address in (('generations', '0084'), ('generations', '0356'),
                                  ('configurationIntents', '0050'), ('sfrReadbacks', '004A')):
                value = fixture(entry); label = 'ConditionalEffect:' + operation + ':0000:1'
                if area == 'generations': value[area][address] = label
                else: value[area][address]['generation'] = label
                yield {'id': f'{operation}-namespace-{entry}-{area}-{address}', 'operation': operation, 'input': value}
            for name in ('AL', 'AH'):
                for index, bits in enumerate(({}, {0: 1}, {bit: (0xA5 >> bit) & 1 for bit in range(8)})):
                    value = register_partial(fixture(entry), name, bits)
                    yield {'id': f'{operation}-partial-{entry}-{name}-{index}', 'operation': operation, 'input': value}
    for cf in (0, 1, None):
        for zf in (0, 1, None):
            value = fixture('SymbolicCarryTail'); value['registers'].update(cf=cf, zf=zf)
            yield {'id': f'producer-tail-flags-{cf}-{zf}', 'operation': 'mode_bit1_producer', 'input': value}
    for bit in (0, 1):
        value = fixture(); value['memory']['0356'] = 0
        value['assumptions']['ordinaryByteSemantics'] = False
        value['registers']['dd'] = bit
        value['sfrReadbacks'] = {key: slot(None) for key in READBACK_KEYS}
        yield {'id': f'reader-bypass-no-byte-premise-dd{bit}', 'operation': 'tx_configuration_reader', 'input': value}
    value = fixture(); value['registers']['scb'] = 6
    partial(value, '00B4', {0: 1}); partial(value, '00B5', {7: 0})
    yield {'id': 'reader-bank6-partial-alias-overwritten', 'operation': 'tx_configuration_reader', 'input': value}
    value = fixture('SymbolicCarryTail'); value['memory']['0356'] = 2; value['registers']['cf'] = 1
    yield {'id': 'producer-same-value-generation-not-deduplicated', 'operation': 'mode_bit1_producer', 'input': value}
    value = fixture('Compare3cb'); value['configurationIntents']['0050']['value'] = 0x31
    value['sfrReadbacks']['0050']['value'] = 0x1C
    yield {'id': 'producer-separate-intents-readbacks', 'operation': 'mode_bit1_producer', 'input': value}
    for path in PATHS:
        yield {'id': 'reaching-path-' + path, 'operation': 'tx_configuration_reaching_definitions', 'input': reaching_query(path)}
    for change in ('entry-none', 'requested-none', 'current-none', 'entry-replaced', 'requested-stale',
        'unknown-writer', 'competing', 'timeline-refused', 'query-no-interference', 'query-unknown-interference',
        'timeline-no-interference', 'timeline-unknown-interference', 'no-boundary', 'two-same-value-generations'):
        value = reaching_query(); timeline = value['timelineQuery']
        if change == 'entry-none': value['entryGeneration'] = None
        elif change == 'requested-none': value['requestedGeneration'] = None
        elif change == 'current-none': timeline['events'][0]['generation'] = None; timeline['events'] = timeline['events'][:1]
        elif change == 'entry-replaced': value['entryGeneration'] = 'Earlier'
        elif change == 'requested-stale': value['requestedGeneration'] = 'Earlier'
        elif change == 'unknown-writer': timeline['events'] = [{'kind': 'UnknownWriter', 'id': 'interferer'}]
        elif change == 'competing':
            timeline['events'] = [{'kind': 'AlternateIntent', 'id': 'other', 'address': 0x50,
                'widthBits': 8, 'value': 0x1C, 'generation': 'Other', 'dd': 0}]
        elif change == 'timeline-refused': timeline['claim'] = 'NativeOwner'
        elif change == 'query-no-interference': value['noInterference'] = False
        elif change == 'query-unknown-interference': value['noInterference'] = None
        elif change == 'timeline-no-interference': timeline['noInterference'] = False
        elif change == 'timeline-unknown-interference': timeline['noInterference'] = None
        elif change == 'no-boundary': timeline['events'] = timeline['events'][:1]
        else:
            timeline['events'].insert(1, {'kind': 'ConfigIntent', 'id': 'later', 'path': 'Bit1Set', 'value': 0x1C, 'generation': 'Config2', 'dd': 0})
            timeline['events'][-1]['requestedGeneration'] = 'Config2'
            value['entryGeneration'] = value['requestedGeneration'] = 'Config2'
        yield {'id': 'reaching-control-' + change, 'operation': 'tx_configuration_reaching_definitions', 'input': value}
    for rule in RULE_KEYS:
        for applicability in ('QualifiedStandardProfile', 'UnknownActualEcu', 'ActualEcuVerified'):
            value = ack_query(rule); value['applicability'] = applicability
            yield {'id': f'ack-rule-{rule}-{applicability}', 'operation': 'tx_ack_documentary_obligations', 'input': value}
    for operation, maker, claims in (
        ('tx_ack_documentary_obligations', ack_query, ('ActualAck', 'ActualTx', 'Fifo', 'TxCompleteIrq', 'RuntimeAdmission')),
        ('tx_configuration_reaching_definitions', reaching_query, ('NativeOwner', 'ActualTx')),
        ('stbuf2995_configuration_provenance', join_query, ('NativeOwner', 'ActualTx', 'RuntimeAdmission'))):
        for claim in claims:
            value = maker(); value['claim'] = claim
            yield {'id': f'{operation}-claim-{claim}', 'operation': operation, 'input': value}
        for index, source in enumerate((None, {}, {**SOURCE_BINDING, 'baseSha': '0' * 40},
                                        {**SOURCE_BINDING, 'producerProofSha256': False})):
            value = maker(); value['sourceBinding'] = source
            yield {'id': f'{operation}-binding-{index}', 'operation': operation, 'input': value}
    yield {'id': 'join-all-conditional-still-missing-edge', 'operation': 'stbuf2995_configuration_provenance', 'input': join_query()}
    for change in ('reader-refused', 'reader-unknown-guard', 'producer-refused', 'producer-unknown-carry',
                   'reaching-stale', 'reaching-missing-path', 'ack-actual', 'stbuf-actual', 'stbuf-unknown', 'independent-nested-states'):
        value = join_query()
        if change == 'reader-refused': value['readerQuery']['assumptions']['ordinaryByteSemantics'] = False
        elif change == 'reader-unknown-guard': value['readerQuery']['memory']['0356'] = None
        elif change == 'producer-refused': value['producerQuery']['registers']['scb'] = None
        elif change == 'producer-unknown-carry': value['producerQuery'] = fixture('SymbolicCarryTail'); value['producerQuery']['registers']['cf'] = None
        elif change == 'reaching-stale': value['reachingQuery']['requestedGeneration'] = 'Old'
        elif change == 'reaching-missing-path': value['reachingQuery']['path'] = 'ConfigurationTo2995'
        elif change == 'ack-actual': value['ackQuery']['claim'] = 'ActualAck'
        elif change == 'stbuf-actual': value['stbufQuery']['claim'] = 'ActualBufferWrite'
        elif change == 'stbuf-unknown': value['stbufQuery']['premises'] = dict.fromkeys(value['stbufQuery']['premises'])
        else:
            value['readerQuery']['memory']['0356'] = 0
            value['producerQuery']['memory']['0356'] = 0xFF
            value['readerQuery']['configurationIntents']['0050']['value'] = 0x31
        yield {'id': 'join-control-' + change, 'operation': 'stbuf2995_configuration_provenance', 'input': value}
