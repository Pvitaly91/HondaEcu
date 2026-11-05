"""Bounded invented software declarations; never current peripheral state."""
from copy import deepcopy

from post_consumer_continuation.corpus import fixture as prior_fixture, stbuf_query
from payload_consumer_tail.corpus import partial

SFR_KEYS = ('0048', '0049', '004A', '0050', '0054')
CONFIG_SITES = (0x286D, 0x286F, 0x2871, 0x2873, 0x2876, 0x2878, 0x287A,
    0x287C, 0x287E, 0x2880, 0x2882, 0x2884, 0x2888, 0x2889, 0x288B, 0x288C)
READER_SITES = (0x3FD4, 0x3FD7, 0x3FD9, 0x3FDB, 0x3FDD, 0x3FDF, 0x3FE1,
    0x3FE3, 0x3FE5, 0x3FE7, 0x3FE9, 0x3FEB, 0x3FEF, 0x3FF1, 0x3FF5)
SOURCE_BINDING = {'baseSha': '312a0b48542330a782c71d517d07f23480caf158',
    'writerProofSha256': '045d23a9cd466098bca05cb1c4bf9446466d2d85ea84963d9bef6e00c9d85437',
    'primaryProofSha256': 'a1229666d2a2e21cb6e26db3e418c0eb0d6833545c597a1b5b3a0da3ac83fcc0',
    'irqProofSha256': '0942c6be80c73993fd90777fa20998cc081d8dc7601cce5b1c79a1259d4e3064'}


def slot(value=None, generation='DeclaredInitial'):
    return {'value': value, 'knownBits': {}, 'generation': generation}


def slots(known=False):
    values = (0xDF, 0xDF, 0x12, 0x1C, 0x8C) if known else (None,) * 5
    return {key: slot(value, 'DeclaredInitial:' + key) for key, value in zip(SFR_KEYS, values)}


def fixture():
    value = prior_fixture()
    value['registers']['lrb'] = 0x41
    value['memory'].update({'0208': None, '0209': None, '0356': 2})
    value['generations'] = {key: 'InventedM2cs:' + key for key in value['memory']}
    value['configurationIntents'] = slots()
    return value


def hypotheses_query():
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'configurationIntents': slots(True), 'claim': 'DocumentaryOnly'}


def lineage_query(path='Bit1Set'):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'initial': slot(None, 'DeclaredBefore'), 'events': [
            {'kind': 'ConfigIntent', 'id': 'config', 'path': path,
             'value': 0x1C if path == 'Bit1Set' else 0x31, 'generation': 'Config1', 'dd': 0},
            {'kind': 'Boundary', 'id': 'boundary', 'requestedGeneration': 'Config1'}],
        'noInterference': True, 'claim': 'ConditionalOnly'}


def lifecycle_query(situation='IdleWrite'):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'situation': situation, 'applicability': 'QualifiedStandardProfile', 'claim': 'DocumentaryOnly'}


def join_query():
    configuration = hypotheses_query()
    configuration['configurationIntents']['0050'] = slot(0x1C, 'Config1')
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'configurationQuery': configuration, 'lineageQuery': lineage_query(),
        'lifecycleQuery': lifecycle_query(), 'stbufQuery': stbuf_query(True), 'claim': 'ConditionalOnly'}


def partial_slot(value, bits):
    value.update(value=None, knownBits={str(bit): known for bit, known in bits.items()})
    return value


def cases():
    for byte in range(256):
        value = fixture(); value['memory']['0356'] = byte
        yield {'id': f'configuration-status-{byte:02X}', 'operation': 'stcon_configuration', 'input': value}
        for key in ('004A', '0050'):
            query = hypotheses_query(); query['configurationIntents'][key]['value'] = byte
            yield {'id': f'hypotheses-{key}-{byte:02X}', 'operation': 'transmit_configuration_hypotheses', 'input': query}
    for mode in range(4):
        for receiving in (0, 1):
            query = hypotheses_query(); query['configurationIntents']['0054']['value'] = mode | (receiving << 7)
            yield {'id': f'hypotheses-srcon-mode-{mode}-{receiving}', 'operation': 'transmit_configuration_hypotheses', 'input': query}
    for bank in range(8):
        for bit in (0, 1):
            value = fixture(); value['registers']['scb'] = bank; value['memory']['0356'] = bit << 1
            yield {'id': f'configuration-bank-{bank}-{bit}', 'operation': 'stcon_configuration', 'input': value}
    for key in fixture()['registers']:
        value = fixture(); value['registers'][key] = None
        if key in ('al', 'ah'):
            value['registerKnownBits'] = {name: bit for name, bit in value['registerKnownBits'].items() if not name.startswith(key.upper() + '.')}
        yield {'id': 'configuration-unknown-register-' + key, 'operation': 'stcon_configuration', 'input': value}
    for lrb in (0, 0x40, 0x7E, 0x2041, 0xFFFF):
        value = fixture(); value['registers']['lrb'] = lrb
        yield {'id': f'configuration-wrong-lrb-{lrb}', 'operation': 'stcon_configuration', 'input': value}
    for assumption in ('noInterference', 'ordinaryByteSemantics'):
        for answer in (None, False):
            value = fixture(); value['assumptions'][assumption] = answer
            yield {'id': f'configuration-premise-{assumption}-{answer}', 'operation': 'stcon_configuration', 'input': value}
    patterns = ({}, {0: 0}, {1: 0}, {1: 1}, {7: 1}, {5: 1, 6: 1},
                {bit: 0 for bit in range(8)}, {bit: 1 for bit in range(8)})
    for index, bits in enumerate(patterns):
        value = partial(fixture(), '0356', bits)
        yield {'id': f'configuration-status-partial-{index}', 'operation': 'stcon_configuration', 'input': value}
        for key in SFR_KEYS:
            query = hypotheses_query(); partial_slot(query['configurationIntents'][key], bits)
            yield {'id': f'hypotheses-partial-{key}-{index}', 'operation': 'transmit_configuration_hypotheses', 'input': query}
    for name in ('AL', 'AH'):
        for bits in ({}, {0: 1}, {bit: (0xA5 >> bit) & 1 for bit in range(8)}):
            value = fixture(); value['registers'][name.lower()] = None
            value['registerKnownBits'] = {key: bit for key, bit in value['registerKnownBits'].items() if not key.startswith(name + '.')}
            value['registerKnownBits'].update({name + '.' + str(bit): known for bit, known in bits.items()})
            yield {'id': f'configuration-register-partial-{name}-{len(bits)}', 'operation': 'stcon_configuration', 'input': value}
    for path in ('Bit1Set', 'Bit1Clear'):
        value = fixture(); value['memory']['0356'] = 2 if path == 'Bit1Set' else 0
        values = (0xDF, 0xDF, 0x12, 0x1C, 0x8C) if path == 'Bit1Set' else (0xFB, 0xFB, 0x12, 0x31, 0xA1)
        value['configurationIntents'] = {key: slot(byte, 'DeclaredBefore:' + key) for key, byte in zip(SFR_KEYS, values)}
        yield {'id': 'configuration-same-declared-' + path, 'operation': 'stcon_configuration', 'input': value}
        yield {'id': 'lineage-path-' + path, 'operation': 'stcon_writer_lineage', 'input': lineage_query(path)}
    for key in ('0208', '0209', '0084', '0356'):
        value = fixture(); value['generations'][key] = 'ConditionalEffect:stcon_configuration:0000:1'
        yield {'id': 'configuration-existing-namespace-' + key, 'operation': 'stcon_configuration', 'input': value}
    value = fixture(); value['configurationIntents']['0050']['generation'] = 'ConditionalEffect:stcon_configuration:0000:1'
    yield {'id': 'configuration-existing-intent-namespace', 'operation': 'stcon_configuration', 'input': value}
    value = fixture(); value['registers']['scb'] = 6
    partial(value, '00B4', {0: 1}); partial(value, '00B5', {7: 1})
    yield {'id': 'configuration-bank6-partial-alias', 'operation': 'stcon_configuration', 'input': value}
    for key in ('0208', '0209', '0356'):
        value = fixture(); value['generations'][key] = None
        yield {'id': 'configuration-missing-generation-' + key, 'operation': 'stcon_configuration', 'input': value}
    for code, bits in (('combined-mode', {1: 1}), ('divisor512', {7: 1, 6: 1})):
        query = hypotheses_query(); partial_slot(query['configurationIntents']['004A'], bits)
        yield {'id': 'hypotheses-consensus-' + code, 'operation': 'transmit_configuration_hypotheses', 'input': query}
    for key, values in (('0048', (0, 0xDF, 0xFB, None)), ('0049', (0, 0xDF, 0xFB, None))):
        for byte in values:
            query = hypotheses_query(); query['configurationIntents'][key]['value'] = byte
            yield {'id': f'hypotheses-reload-equality-{key}-{byte}', 'operation': 'transmit_configuration_hypotheses', 'input': query}
    for claim in ('ActualEcuApplicable', 'ActualOwner', 'ActualReady', 'Rx000ATx'):
        query = hypotheses_query(); query['claim'] = claim
        yield {'id': 'hypotheses-claim-' + claim, 'operation': 'transmit_configuration_hypotheses', 'input': query}
    for situation in ('IdleWrite', 'BusyWrite', 'Completion', 'ModeChange', 'Acknowledge', 'Reassertion', 'Collision'):
        for applicability in ('QualifiedStandardProfile', 'UnknownActualEcu', 'ActualEcuVerified'):
            query = lifecycle_query(situation); query['applicability'] = applicability
            yield {'id': f'lifecycle-{situation}-{applicability}', 'operation': 'tx_lifecycle_obligations', 'input': query}
    for claim in ('ActualTx', 'Fifo', 'TxCompleteIrq', 'AckByWrite', 'Rx000ATx'):
        query = lifecycle_query(); query['claim'] = claim
        yield {'id': 'lifecycle-claim-' + claim, 'operation': 'tx_lifecycle_obligations', 'input': query}
    for operation, maker in (('transmit_configuration_hypotheses', hypotheses_query), ('tx_lifecycle_obligations', lifecycle_query), ('stcon_writer_lineage', lineage_query), ('stbuf2995_source_join', join_query)):
        for index, binding in enumerate((None, {}, {**SOURCE_BINDING, 'baseSha': '0' * 40})):
            query = maker(); query['sourceBinding'] = binding
            yield {'id': f'{operation}-source-{index}', 'operation': operation, 'input': query}
    for change in ('value', 'unknown-value', 'dd1', 'dd-unknown', 'missing-generation', 'stale', 'unknown-writer', 'initial-reused', 'prior-reused', 'no-check'):
        query = lineage_query()
        if change == 'value': query['events'][0]['value'] = 0x1D
        elif change == 'unknown-value': query['events'][0]['value'] = None
        elif change == 'dd1': query['events'][0]['dd'] = 1
        elif change == 'dd-unknown': query['events'][0]['dd'] = None
        elif change == 'missing-generation': query['events'][0]['generation'] = None
        elif change == 'stale': query['events'][-1]['requestedGeneration'] = 'Earlier'
        elif change == 'unknown-writer': query['events'].insert(1, {'kind': 'UnknownWriter', 'id': 'interference'})
        elif change == 'initial-reused': query['events'][0]['generation'] = query['initial']['generation']
        elif change == 'prior-reused': query['events'].insert(1, {'kind': 'ConfigIntent', 'id': 'again', 'path': 'Bit1Set', 'value': 0x1C, 'generation': 'Config1', 'dd': 0})
        else: query['events'] = query['events'][:1]
        yield {'id': 'lineage-control-' + change, 'operation': 'stcon_writer_lineage', 'input': query}
    for address, width in ((0x4F, 8), (0x4F, 16), (0x50, 8), (0x50, 16), (0x51, 8), (0x51, 16), (0x52, 16), (0x54, 8)):
        query = lineage_query()
        query['events'].insert(1, {'kind': 'AlternateIntent', 'id': 'alternate', 'address': address, 'widthBits': width, 'value': 0xABCD if width == 16 else 0x1C, 'generation': 'Alternate', 'dd': int(width == 16)})
        yield {'id': f'lineage-alternate-{address:04X}-{width}', 'operation': 'stcon_writer_lineage', 'input': query}
    for claim in ('NativeOwner', 'ActualTx', 'ResetOwner', 'Rx000ATx'):
        query = lineage_query(); query['claim'] = claim
        yield {'id': 'lineage-claim-' + claim, 'operation': 'stcon_writer_lineage', 'input': query}
    for answer in (False, None):
        query = lineage_query(); query['noInterference'] = answer
        yield {'id': 'lineage-interference-' + str(answer), 'operation': 'stcon_writer_lineage', 'input': query}
    for raw in (0x1C, None):
        query = lineage_query()
        query['events'].insert(1, {'kind': 'AlternateIntent', 'id': 'alternate-current', 'address': 0x50,
            'widthBits': 8, 'value': raw, 'generation': 'Alternate', 'dd': 0})
        query['events'][-1]['requestedGeneration'] = 'Alternate'
        yield {'id': 'lineage-requested-alternate-' + str(raw), 'operation': 'stcon_writer_lineage', 'input': query}
    query = lineage_query()
    query['events'].insert(1, {'kind': 'ConfigIntent', 'id': 'same-declared-new-label', 'path': 'Bit1Set',
        'value': 0x1C, 'generation': 'Config2', 'dd': 0})
    query['events'][-1]['requestedGeneration'] = 'Config2'
    yield {'id': 'lineage-repeated-same-value-distinct-generations', 'operation': 'stcon_writer_lineage', 'input': query}
    query = lineage_query(); query['initial'] = slot(0x1C, 'DeclaredBefore')
    yield {'id': 'lineage-same-declared-new-generation', 'operation': 'stcon_writer_lineage', 'input': query}
    query = lineage_query(); query['events'].insert(1, {'kind': 'AlternateIntent', 'id': 'not-overlap', 'address': 0x54, 'widthBits': 8, 'value': 0, 'generation': 'UnusedLabel', 'dd': 0})
    query['events'].insert(2, {'kind': 'ConfigIntent', 'id': 'reuse-not-overlap', 'path': 'Bit1Set', 'value': 0x1C, 'generation': 'UnusedLabel', 'dd': 0})
    yield {'id': 'lineage-nonoverlap-label-still-reserved', 'operation': 'stcon_writer_lineage', 'input': query}
    yield {'id': 'join-all-conditional-hypotheses', 'operation': 'stbuf2995_source_join', 'input': join_query()}
    for change in ('config-raw', 'config-bits', 'config-generation', 'lineage-stale', 'lineage-missing', 'lineage-no-check', 'lineage-false', 'stbuf-unknown-hardware', 'stbuf-dd1', 'stbuf-unknown-al', 'stbuf-actual', 'lifecycle-actual', 'configuration-actual'):
        query = join_query()
        if change == 'config-raw': query['configurationQuery']['configurationIntents']['0050']['value'] = 0x31
        elif change == 'config-bits': query['configurationQuery']['configurationIntents']['0050']['knownBits'] = {'0': 0}
        elif change == 'config-generation': query['configurationQuery']['configurationIntents']['0050']['generation'] = 'Unrelated'
        elif change == 'lineage-stale': query['lineageQuery']['events'][-1]['requestedGeneration'] = 'Earlier'
        elif change == 'lineage-missing': query['lineageQuery']['events'][0]['generation'] = None
        elif change == 'lineage-no-check': query['lineageQuery']['events'].pop()
        elif change == 'lineage-false': query['lineageQuery']['noInterference'] = False
        elif change == 'stbuf-unknown-hardware': query['stbufQuery'] = stbuf_query()
        elif change == 'stbuf-dd1': query['stbufQuery']['dd'] = 1
        elif change == 'stbuf-unknown-al': query['stbufQuery']['prospectiveAL']['value'] = None
        elif change == 'stbuf-actual': query['stbufQuery']['claim'] = 'ActualTransmit'
        elif change == 'lifecycle-actual': query['lifecycleQuery']['applicability'] = 'ActualEcuVerified'
        else: query['configurationQuery']['claim'] = 'ActualOwner'
        yield {'id': 'join-control-' + change, 'operation': 'stbuf2995_source_join', 'input': query}
    for nested in ('configurationQuery', 'lineageQuery', 'lifecycleQuery'):
        query = join_query(); query[nested]['sourceBinding'] = None
        yield {'id': 'join-nested-source-' + nested, 'operation': 'stbuf2995_source_join', 'input': query}
    query = join_query(); query['configurationQuery']['configurationIntents']['0050']['generation'] = None
    query['lineageQuery']['events'][0]['generation'] = None
    query['lineageQuery']['events'][-1]['requestedGeneration'] = None
    yield {'id': 'join-matching-missing-generations-never-native', 'operation': 'stbuf2995_source_join', 'input': query}
    for claim in ('ActualTx', 'NativeOwner', 'RuntimeAdmission'):
        query = join_query(); query['claim'] = claim
        yield {'id': 'join-claim-' + claim, 'operation': 'stbuf2995_source_join', 'input': query}
    for input_class in ('SymbolicInput', 'ManufacturerSourceQualifiedState'):
        for operation, maker in (('stcon_configuration', fixture), ('stcon_writer_lineage', lineage_query),
            ('transmit_configuration_hypotheses', hypotheses_query), ('tx_lifecycle_obligations', lifecycle_query),
            ('stbuf2995_source_join', join_query)):
            query = maker(); query['inputClass'] = input_class
            if operation == 'stbuf2995_source_join':
                for nested in ('configurationQuery', 'lineageQuery', 'lifecycleQuery', 'stbufQuery'):
                    query[nested]['inputClass'] = input_class
            yield {'id': f'input-class-{operation}-{input_class}', 'operation': operation, 'input': query}
