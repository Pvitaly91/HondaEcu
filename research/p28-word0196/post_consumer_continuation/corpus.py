"""Finite invented inputs; no native execution, frame or transmitter owner."""
from copy import deepcopy

from payload_consumer_tail.corpus import fixture as parent_fixture, partial

SITES = (0x2980, 0x2983, 0x2985, 0x2988, 0x298A, 0x298B, 0x298E, 0x298F, 0x2991, 0x2994)
PREMISES = ('deviceApplicability', 'physicalByteAccessAndSf', 'accessMapping',
    'peripheralOwnership', 'transmitterReady', 'clockResetStconGeneration',
    'serialConfiguration', 'peripheralInterferenceExcluded', 'acceptanceSemantics',
    'irqAckCollisionSemantics')
SOURCE_BINDING = {'baseSha': 'ac4086aec3cea32d0e76d6732d9998cbd75bbb28',
    'continuationSourceSha256': 'c9bccc09dc1fa95bc3f1ea4c7e382a1b74982214bacbe905b45a6a8e5ca65379',
    'stbufSourceSha256': 'f436ca49a8e0491e78ac307425cb28893095a4dda8b0d8837c689ca7050d732c',
    'manualSha256': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
    'entry': 0x2980, 'stop': 0x2995, 'sites': list(SITES),
    'boundaryForm': 'STB A,N8', 'boundaryLength': 2, 'boundaryAddress': 0x51, 'boundaryDD': 0}


def fixture(composed=False):
    value = parent_fixture()
    value['memory'].update({'03F1': 0x21, '0356': 2, '03F5': 2, '03F6': 1})
    value['generations'] = {key: 'InventedM2cr:' + key for key in value['memory']}
    if not composed:
        value['registerKnownBits'] = {name.upper() + '.' + str(bit): (raw >> bit) & 1
            for name in ('al', 'ah') if (raw := value['registers'][name]) is not None
            for bit in range(8)}
    return value


def register_partial(value, name, bits):
    value['registers'][name] = None
    prefix = name.upper() + '.'
    value['registerKnownBits'] = {key: bit for key, bit in value['registerKnownBits'].items()
                                if not key.startswith(prefix)}
    value['registerKnownBits'].update({prefix + str(key): bit for key, bit in bits.items()})
    return value


def slot(value=0x44, generation='InventedGeneration'):
    return {'value': value, 'knownBits': {}, 'generation': generation}


def lineage_query():
    before = {'03F2': slot(0x82, 'Consumer297F'), '03F4': slot(0x7F, 'ConditionalG')}
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'before': before, 'after': deepcopy(before),
        'requestedGenerations': {key: value['generation'] for key, value in before.items()},
        'noInterference': True, 'claim': 'ConditionalRetentionOnly'}


def stbuf_query(complete=False):
    return {'inputClass': 'SyntheticTestInput', 'sourceBinding': deepcopy(SOURCE_BINDING),
        'pc': 0x2995, 'dd': 0, 'prospectiveAL': slot(1, 'ConditionalAl298F'),
        'softwareReached': True, 'softwareNoInterference': True,
        'premises': dict.fromkeys(PREMISES, True if complete else None), 'claim': 'ObligationsOnly'}


def cases():
    for byte in range(256):
        value = fixture()
        value['memory']['03F1'] = byte
        yield {'id': f'continuation-H-{byte:02X}', 'operation': 'post_consumer_continuation', 'input': value}
        value = fixture(True)
        value['memory']['03F4'] = byte
        value['registers']['scb'] = byte % 8
        yield {'id': f'composed-G-{byte:02X}', 'operation': 'consumer_with_continuation', 'input': value}
        value = fixture()
        value['memory']['0356'] = byte
        yield {'id': f'continuation-status-{byte:02X}', 'operation': 'post_consumer_continuation', 'input': value}
    for bank in range(8):
        for byte in (0, 1, 0x7F, 0x80, 0xFE, 0xFF):
            value = fixture()
            value['registers']['scb'] = bank
            value['registers']['al'] = byte
            value['registerKnownBits'] = {key: bit for key, bit in value['registerKnownBits'].items()
                                          if key.startswith('AH.')}
            yield {'id': f'continuation-bank-{bank}-AL-{byte:02X}', 'operation': 'post_consumer_continuation', 'input': value}
    patterns = ({}, {0: 0}, {0: 1}, {4: 1}, {7: 1}, {0: 0, 1: 0, 2: 0, 3: 0, 4: 0},
                {bit: 0 for bit in range(8)}, {bit: 1 for bit in range(8)}, {1: 1, 3: 0, 6: 1})
    for index, bits in enumerate(patterns):
        for composed in (False, True):
            value = partial(fixture(composed), '03F1', bits)
            yield {'id': f'H-partial-{composed}-{index}', 'operation': 'consumer_with_continuation' if composed else 'post_consumer_continuation', 'input': value}
        value = partial(fixture(True), '03F4', bits)
        yield {'id': f'G-partial-composed-{index}', 'operation': 'consumer_with_continuation', 'input': value}
        value = partial(fixture(), '0356', bits)
        yield {'id': f'status-partial-{index}', 'operation': 'post_consumer_continuation', 'input': value}
        for name in ('al', 'ah'):
            value = register_partial(fixture(), name, bits)
            yield {'id': f'register-partial-{name}-{index}', 'operation': 'post_consumer_continuation', 'input': value}
    for name in fixture()['registers']:
        value = fixture()
        value['registers'][name] = None
        if name in ('al', 'ah'):
            register_partial(value, name, {})
        yield {'id': 'unknown-register-' + name, 'operation': 'post_consumer_continuation', 'input': value}
    for dd in (0, 1, None):
        value = fixture()
        value['registers']['dd'] = dd
        yield {'id': 'incoming-dd-' + str(dd), 'operation': 'post_consumer_continuation', 'input': value}
    for lrb in (None, 0, 0x7E, 0xFFFF):
        value = fixture()
        value['registers']['lrb'] = lrb
        yield {'id': 'unrestricted-lrb-' + str(lrb), 'operation': 'post_consumer_continuation', 'input': value}
    for address in ('0356', '03F1', '03F2', '03F4', '03F5', '03F6', '0084', '0085'):
        for composed in (False, True):
            value = fixture(composed)
            value['generations'][address] = None
            yield {'id': f'missing-generation-{composed}-{address}', 'operation': 'consumer_with_continuation' if composed else 'post_consumer_continuation', 'input': value}
    for composed in (False, True):
        operation = 'consumer_with_continuation' if composed else 'post_consumer_continuation'
        for address in ('03F2', '03F4'):
            for byte in (0, 255, None):
                value = fixture(composed)
                value['memory'][address] = byte
                yield {'id': f'frame-byte-{composed}-{address}-{byte}', 'operation': operation, 'input': value}
        for premise in ('noInterference', 'ordinaryByteSemantics'):
            for answer in (False, None):
                value = fixture(composed)
                value['assumptions'][premise] = answer
                yield {'id': f'premise-{composed}-{premise}-{answer}', 'operation': operation, 'input': value}
        for input_class in ('SyntheticTestInput', 'SymbolicInput', 'ManufacturerSourceQualifiedState'):
            value = fixture(composed)
            value['inputClass'] = input_class
            yield {'id': f'input-class-{composed}-{input_class}', 'operation': operation, 'input': value}
        value = fixture(composed)
        value['generations']['03F1'] = 'ConditionalEffect:' + operation + ':0000:1'
        yield {'id': f'namespace-{operation}', 'operation': operation, 'input': value}
    value = fixture(True)
    value['generations']['03F4'] = 'ConditionalEffect:payload_consumer:0000:1'
    yield {'id': 'namespace-parent-consumer', 'operation': 'consumer_with_continuation', 'input': value}
    value = fixture(True)
    value['registers']['scb'] = None
    yield {'id': 'composed-unknown-scb', 'operation': 'consumer_with_continuation', 'input': value}
    for bank, address in ((0, '0084'), (0, '03F2'), (6, '00B4')):
        value = fixture(True)
        value['registers']['scb'] = bank
        value['generations'][address] = 'ConditionalEffect:consumer_with_continuation:0000:1'
        yield {'id': f'namespace-original-overwritten-{bank}-{address}', 'operation': 'consumer_with_continuation', 'input': value}
    value = fixture()
    value['registers']['scb'] = 6
    partial(value, '00B4', {0: 1, 7: 0})
    partial(value, '00B5', {3: 1})
    yield {'id': 'bank6-partial-pointer', 'operation': 'post_consumer_continuation', 'input': value}
    value = fixture()
    value['registerKnownBits'] = {'AL.0': value['registers']['al'] & 1}
    yield {'id': 'known-scalar-subset-register-bits', 'operation': 'post_consumer_continuation', 'input': value}
    for address in ('03F2', '03F4'):
        for byte in (0, 1, 0x7F, 0x80, 0xFF, None):
            query = lineage_query()
            query['before'][address]['value'] = byte
            query['after'][address]['value'] = byte
            yield {'id': f'lineage-byte-{address}-{byte}', 'operation': 'continuation_lineage', 'input': query}
        for change in ('value', 'generation', 'missing-before', 'missing-after', 'missing-request', 'stale', 'knowledge', 'same-domain'):
            query = lineage_query()
            if change == 'value':
                query['after'][address]['value'] ^= 1
            elif change == 'generation':
                query['after'][address]['generation'] = 'OtherWriter'
            elif change == 'missing-before':
                query['before'][address]['generation'] = None
            elif change == 'missing-after':
                query['after'][address]['generation'] = None
            elif change == 'missing-request':
                query['requestedGenerations'][address] = None
            elif change == 'stale':
                query['requestedGenerations'][address] = 'StaleWriter'
            elif change == 'knowledge':
                query['before'][address].update(value=None, knownBits={})
                query['after'][address].update(value=None, knownBits={'0': 0})
            else:
                byte = query['before'][address]['value']
                query['after'][address].update(value=None, knownBits={str(bit): (byte >> bit) & 1 for bit in range(8)})
            yield {'id': f'lineage-{address}-{change}', 'operation': 'continuation_lineage', 'input': query}
    for claim in ('ParserLength', 'ContinuationReadsF2', 'Native026COwner', 'ActualTransmit'):
        query = lineage_query(); query['claim'] = claim
        yield {'id': 'lineage-claim-' + claim, 'operation': 'continuation_lineage', 'input': query}
    for answer in (False, None):
        query = lineage_query(); query['noInterference'] = answer
        yield {'id': 'lineage-no-interference-' + str(answer), 'operation': 'continuation_lineage', 'input': query}
    for binding in (None, {}, {'entry': 0x2981}):
        query = lineage_query(); query['sourceBinding'] = binding
        yield {'id': 'lineage-binding-' + str(binding), 'operation': 'continuation_lineage', 'input': query}
    yield {'id': 'lineage-qualified-retention', 'operation': 'continuation_lineage', 'input': lineage_query()}
    query = lineage_query()
    query['after']['03F2']['knownBits'] = {'0': query['after']['03F2']['value'] & 1}
    yield {'id': 'lineage-same-raw-different-explicit-map', 'operation': 'continuation_lineage', 'input': query}
    yield {'id': 'stbuf-hardware-unknown', 'operation': 'stbuf_boundary_obligations', 'input': stbuf_query()}
    yield {'id': 'stbuf-all-hypothetical', 'operation': 'stbuf_boundary_obligations', 'input': stbuf_query(True)}
    for premise in PREMISES:
        for answer in (None, False):
            query = stbuf_query(True); query['premises'][premise] = answer
            yield {'id': f'stbuf-premise-{premise}-{answer}', 'operation': 'stbuf_boundary_obligations', 'input': query}
    for claim in ('ActualBufferWrite', 'ActualTransmit', 'TxComplete', 'IRQ', 'CpuExecution'):
        query = stbuf_query(True); query['claim'] = claim
        yield {'id': 'stbuf-claim-' + claim, 'operation': 'stbuf_boundary_obligations', 'input': query}
    for binding in (None, {}, {'entry': 0x2981}):
        query = stbuf_query(True); query['sourceBinding'] = binding
        yield {'id': 'stbuf-binding-' + str(binding), 'operation': 'stbuf_boundary_obligations', 'input': query}
    for field, values in (('pc', (None, 0x2994, 0x2997)), ('dd', (None, 1)),
                          ('softwareReached', (None, False)), ('softwareNoInterference', (None, False))):
        for value in values:
            query = stbuf_query(True); query[field] = value
            yield {'id': f'stbuf-field-{field}-{value}', 'operation': 'stbuf_boundary_obligations', 'input': query}
    for byte in (0, 1, 0x7F, 0x80, 0xFE, 0xFF, None):
        query = stbuf_query(True); query['prospectiveAL']['value'] = byte
        yield {'id': f'stbuf-operand-{byte}', 'operation': 'stbuf_boundary_obligations', 'input': query}
    for index, bits in enumerate(patterns):
        query = stbuf_query(True)
        query['prospectiveAL'].update(value=None, knownBits={str(bit): value for bit, value in bits.items()})
        yield {'id': f'stbuf-partial-{index}', 'operation': 'stbuf_boundary_obligations', 'input': query}
    query = stbuf_query(True); query['prospectiveAL']['generation'] = None
    yield {'id': 'stbuf-missing-generation', 'operation': 'stbuf_boundary_obligations', 'input': query}
    query = stbuf_query(); query.update(pc=None, dd=None, softwareReached=None, softwareNoInterference=None)
    query['prospectiveAL'].update(value=None, generation=None)
    yield {'id': 'stbuf-all-unknown-obligations', 'operation': 'stbuf_boundary_obligations', 'input': query}
    for key, bad in (('boundaryDD', False), ('entry', float(0x2980))):
        for operation, maker in (('continuation_lineage', lineage_query), ('stbuf_boundary_obligations', stbuf_query)):
            query = maker()
            query['sourceBinding'][key] = bad
            yield {'id': f'strict-source-type-{operation}-{key}', 'operation': operation, 'input': query}
    for key, bad in (('manualSha256', '0' * 64), ('sites', [0x2980, 0x2995])):
        query = stbuf_query(True)
        query['sourceBinding'][key] = bad
        yield {'id': 'stbuf-altered-source-' + key, 'operation': 'stbuf_boundary_obligations', 'input': query}
