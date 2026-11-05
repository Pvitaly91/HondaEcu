"""Invented conditional inputs, not native frames, writers or observations."""
from copy import deepcopy

from generic_payload_multibyte.corpus import fixture as previous_fixture

OLD_ADDRESSES = tuple(previous_fixture()['memory'])
DP_ADDRESSES = tuple(f'{0x84 + bank * 8 + byte:04X}' for bank in range(8) for byte in range(2))
ADDRESSES = tuple(sorted(set(OLD_ADDRESSES) | set(DP_ADDRESSES)))
FRAME_ROLES = ('psw', 'lrb', 'a', 'pc')
PREMISES = ('mappingQualified', 'readable', 'entryWritable', 'frameOwnerEstablished',
            'integrity', 'noControlAlias', 'nestingExcluded', 'nmiExcluded')


def fixture(kind='consumer'):
    role = kind if kind in ('Header', 'Length', 'Flag', 'Generic', 'Checksum') else 'Generic'
    state = previous_fixture(role)
    state['memory'] = {key: state['memory'].get(key) for key in ADDRESSES}
    for key in DP_ADDRESSES:
        state['memory'][key] = None
    state['memory'].update({'03F4': 0x7F, '00F8': 0x34, '00F9': 0x12,
                            '001A': 0xA5, '001B': 0x5A})
    state['knownBits'] = {}
    state['generations'] = {key: 'SyntheticInput:M2cq:' + key for key in ADDRESSES}
    state['registers']['scb'] = 0
    return state


def partial(state, address, bits):
    state['memory'][address] = None
    state['knownBits'] = {key: bit for key, bit in state['knownBits'].items() if key[:4] != address}
    state['knownBits'].update({address + '.' + str(bit): value for bit, value in bits.items()})
    return state


def rti_query(ssp=None, complete=False):
    return {'inputClass': 'SyntheticTestInput', 'ssp': ssp,
        'frameWords': dict(zip(FRAME_ROLES, (0x1003, 0x007E, 0xCAFE, 0x1234))) if complete else dict.fromkeys(FRAME_ROLES),
        'frameGenerations': {key: 'InventedFrame:' + key for key in FRAME_ROLES} if complete else dict.fromkeys(FRAME_ROLES),
        'premises': {**dict.fromkeys(PREMISES, True if complete else None),
                     'matchingEntrySsp': (ssp + 8) % 65536 if complete and ssp is not None else None},
        'executionClaim': False}


def timeline(value=0x7F):
    return {'inputClass': 'SyntheticTestInput', 'initial': {'value': 0x44, 'generation': 'InitialUnbound'},
        'noInterference': True, 'claim': 'ConditionalOnly', 'events': [
            {'kind': 'GenericStore', 'id': 'g1', 'value': value, 'generation': 'G1', 'lrb': 0x7E, 'dd': 0},
            {'kind': 'ConsumerBoundary', 'id': 'c1', 'requestedGeneration': 'G1'},
            {'kind': 'GenericStore', 'id': 'g2', 'value': None if value is None else (value + 1) % 256,
             'generation': 'G2', 'lrb': 0x7E, 'dd': 0},
            {'kind': 'ConsumerBoundary', 'id': 'c2', 'requestedGeneration': 'G2'},
            {'kind': 'GenericStore', 'id': 'g3', 'value': None if value is None else (value + 1) % 256,
             'generation': 'G3', 'lrb': 0x7E, 'dd': 0},
            {'kind': 'ConsumerBoundary', 'id': 'c3', 'requestedGeneration': 'G3'}]}


def cases():
    for byte in range(256):
        value = fixture()
        value['memory']['03F4'] = byte
        yield {'id': f'consumer-all-byte-{byte:02X}', 'operation': 'payload_consumer', 'input': value}
        value = fixture('tail')
        value['memory']['00F8'] = byte
        yield {'id': f'tail-all-low-byte-{byte:02X}', 'operation': 'post_checksum_tail', 'input': value}
        yield {'id': f'last-writer-all-byte-{byte:02X}', 'operation': 'last_writer_at_conditional_boundary', 'input': timeline(byte)}
    for bank in range(8):
        for byte in (0, 1, 2, 3, 127, 128, 254, 255):
            value = fixture()
            value['registers']['scb'] = bank
            value['memory']['03F4'] = byte
            yield {'id': f'consumer-bank-{bank}-{byte:02X}', 'operation': 'payload_consumer', 'input': value}
    for lrb in (None, 0, 0x40, 0xFFFF):
        value = fixture()
        value['registers']['lrb'] = lrb
        yield {'id': 'consumer-unrestricted-lrb-' + str(lrb), 'operation': 'payload_consumer', 'input': value}
    for dd in (0, 1, None):
        value = fixture()
        value['registers']['dd'] = dd
        yield {'id': 'consumer-incoming-dd-' + str(dd), 'operation': 'payload_consumer', 'input': value}
    for scb in (None,):
        value = fixture()
        value['registers']['scb'] = scb
        yield {'id': 'consumer-unknown-bank', 'operation': 'payload_consumer', 'input': value}
    bit_patterns = ({}, {0: 0}, {0: 1}, {7: 0}, {7: 1}, {0: 1, 1: 1, 2: 1, 3: 1},
                    {4: 1, 5: 1, 6: 1, 7: 1}, {bit: 0 for bit in range(8)},
                    {bit: (0xFD >> bit) & 1 for bit in range(8)})
    for index, bits in enumerate(bit_patterns):
        value = partial(fixture(), '03F4', bits)
        yield {'id': f'consumer-partial-{index}', 'operation': 'payload_consumer', 'input': value}
        value = partial(fixture('tail'), '00F8', bits)
        value['memory']['00F9'] = 0
        yield {'id': f'tail-partial-low-{index}', 'operation': 'post_checksum_tail', 'input': value}
        value = partial(fixture('tail'), '00F9', bits)
        value['memory']['00F8'] = 0
        yield {'id': f'tail-partial-high-{index}', 'operation': 'post_checksum_tail', 'input': value}
    for byte in (0, 1, 255):
        value = fixture()
        value['memory'].update({'03F4': byte, '03F2': (byte + 3) % 256, '0084': 0xF4, '0085': 3})
        yield {'id': f'consumer-same-value-writes-{byte}', 'operation': 'payload_consumer', 'input': value}
    value = fixture()
    value['registers']['scb'] = 6
    partial(value, '00B4', {0: 1, 7: 0})
    value['memory']['00B5'] = None
    yield {'id': 'consumer-bank6-partial-control-alias', 'operation': 'payload_consumer', 'input': value}
    for address in ('03F4', '0084', '0085'):
        value = fixture()
        value['generations'][address] = None
        yield {'id': 'consumer-missing-generation-' + address, 'operation': 'payload_consumer', 'input': value}
    for operation, kind in (('payload_consumer', 'consumer'), ('post_checksum_tail', 'tail'), ('parser_step_with_tail', 'Generic')):
        for premise in ('noInterference', 'ordinaryByteSemantics'):
            for answer in (False, None):
                value = fixture(kind)
                value['assumptions'][premise] = answer
                yield {'id': f'{operation}-{premise}-{answer}', 'operation': operation, 'input': value}
        value = fixture(kind)
        value['generations']['03F4'] = 'ConditionalEffect:' + operation + ':0000:1'
        yield {'id': operation + '-namespace', 'operation': operation, 'input': value}
    for name in ('al', 'ah', 'cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw', 'lrb', 'scb', 'usp', 'ssp'):
        value = fixture('tail')
        value['registers'][name] = None
        yield {'id': 'tail-unknown-register-' + name, 'operation': 'post_checksum_tail', 'input': value}
    for address in ('00F8', '00F9'):
        value = fixture('tail')
        value['generations'][address] = None
        yield {'id': 'tail-missing-generation-' + address, 'operation': 'post_checksum_tail', 'input': value}
    value = fixture('tail')
    value['memory'].update({'001A': 0x34, '001B': 0x12})
    yield {'id': 'tail-same-value-ie-word', 'operation': 'post_checksum_tail', 'input': value}
    value = partial(partial(fixture('tail'), '00F8', {}), '00F9', {})
    yield {'id': 'tail-both-shadow-bytes-unknown', 'operation': 'post_checksum_tail', 'input': value}
    value = partial(partial(fixture('tail'), '00F8', {0: 1}), '00F9', {7: 1})
    yield {'id': 'tail-both-shadow-bytes-partial', 'operation': 'post_checksum_tail', 'input': value}
    for role in ('Header', 'Length', 'Flag', 'Generic', 'Checksum'):
        for byte in (0, 1, 2, 127, 128, 255, None):
            value = fixture(role)
            value['memory']['0055'] = byte
            yield {'id': f'parser-tail-{role}-{byte}', 'operation': 'parser_step_with_tail', 'input': value}
    for index, bits in enumerate(bit_patterns):
        value = partial(fixture('Generic'), '00F8', bits)
        value['memory']['00F9'] = 0
        yield {'id': f'parser-tail-partial-f8-{index}', 'operation': 'parser_step_with_tail', 'input': value}
    for address, bit in (('0055', 0), ('03F5', 3), ('03F4', 7), ('00B4', 1)):
        value = partial(fixture('Generic'), address, {bit: 1})
        yield {'id': f'parser-unsupported-partial-{address}', 'operation': 'parser_step_with_tail', 'input': value}
    for address in ('03F7', '03F5', '03F2'):
        value = fixture('Generic')
        value['memory'][address] = None
        yield {'id': 'parser-unknown-predicate-' + address, 'operation': 'parser_step_with_tail', 'input': value}
    for name, raw, bits in (('mode-zero', 0, {}), ('old-error', 0x42, {}),
                            ('unknown-mode', None, {}), ('unknown-error', None, {'0356.1': 1}),
                            ('partial-controls', None, {'0356.1': 1, '0356.6': 0})):
        value = fixture('Generic')
        value['memory']['0356'], value['knownBits'] = raw, bits
        yield {'id': 'parser-tail-status-' + name, 'operation': 'parser_step_with_tail', 'input': value}
    for value in (None, 0, 0x1235):
        state = fixture('Generic')
        state['registers']['ssp'] = value
        yield {'id': 'parser-tail-retained-ssp-' + str(value), 'operation': 'parser_step_with_tail', 'input': state}
    value = partial(fixture('Generic'), '0084', {7: 1})
    yield {'id': 'parser-tail-extra-dp-partial-retained', 'operation': 'parser_step_with_tail', 'input': value}
    value = fixture('Generic')
    value['generations']['0084'] = 'ConditionalEffect:parser_step@M2cqPrefix:026C:2'
    yield {'id': 'parser-tail-prefix-namespace', 'operation': 'parser_step_with_tail', 'input': value}
    value = partial(fixture('Generic'), '0055', {0: 1})
    value['generations']['0084'] = 'ConditionalEffect:parser_step_with_tail:029A:1'
    yield {'id': 'parser-namespace-before-unsupported-partial', 'operation': 'parser_step_with_tail', 'input': value}
    value = partial(fixture('Generic'), '0055', {0: 1})
    value['registers']['lrb'] = None
    yield {'id': 'parser-partial-before-old-context', 'operation': 'parser_step_with_tail', 'input': value}
    for claim in ('Confirmed026CConsumer', 'PayloadArray', 'Fifo', 'ActualExecution'):
        value = timeline()
        value['claim'] = claim
        yield {'id': 'timeline-claim-' + claim, 'operation': 'last_writer_at_conditional_boundary', 'input': value}
    for name in ('unknown-value', 'missing-generation', 'stale-generation', 'wrong-lrb', 'unknown-lrb',
                 'wrong-dd', 'unknown-dd', 'unknown-writer', 'no-interference', 'unknown-interference',
                 'initial-reuse', 'prior-reuse', 'nonoverlap-reuse'):
        value = timeline()
        if name == 'unknown-value':
            value['events'][0]['value'] = None
        elif name == 'missing-generation':
            value['events'][0]['generation'] = None
            value['events'][1]['requestedGeneration'] = None
        elif name == 'stale-generation':
            value['events'][-1]['requestedGeneration'] = 'G2'
        elif name in ('wrong-lrb', 'unknown-lrb'):
            value['events'][2]['lrb'] = None if name == 'unknown-lrb' else 0x40
        elif name in ('wrong-dd', 'unknown-dd'):
            value['events'][2]['dd'] = None if name == 'unknown-dd' else 1
        elif name == 'unknown-writer':
            value['events'].insert(-1, {'kind': 'UnknownWriter', 'id': 'unbound'})
        elif name in ('no-interference', 'unknown-interference'):
            value['noInterference'] = False if name == 'no-interference' else None
        elif name == 'initial-reuse':
            value['events'][0]['generation'] = value['initial']['generation']
        elif name == 'prior-reuse':
            value['events'][4]['generation'] = 'G1'
        else:
            value['events'].insert(0, {'kind': 'AlternateStore', 'id': 'other', 'address': 0x3F3,
                'widthBits': 8, 'value': 0, 'generation': 'G2'})
        yield {'id': 'timeline-' + name, 'operation': 'last_writer_at_conditional_boundary', 'input': value}
    for address in (0x3F3, 0x3F4, 0x3F5, 0x3F6):
        for width in (8, 16):
            for word in (None, 0, 0xA5 if width == 8 else 0xA55A):
                value = timeline()
                value['events'] = [value['events'][0], {'kind': 'AlternateStore', 'id': 'alt',
                    'address': address, 'widthBits': width, 'value': word, 'generation': 'Alternative'},
                    {'kind': 'ConsumerBoundary', 'id': 'observe', 'requestedGeneration': 'Alternative'}]
                yield {'id': f'timeline-alias-{address:04X}-{width}-{word}', 'operation': 'last_writer_at_conditional_boundary', 'input': value}
    value = timeline()
    value['events'] = [{'kind': 'ConsumerBoundary', 'id': 'initial', 'requestedGeneration': 'InitialUnbound'}]
    yield {'id': 'timeline-initial-not-confirmed-generic', 'operation': 'last_writer_at_conditional_boundary', 'input': value}
    value = timeline()
    for event in value['events']:
        event['generation' if event['kind'] == 'GenericStore' else 'requestedGeneration'] = None
    yield {'id': 'timeline-null-labels-repeat-without-owner', 'operation': 'last_writer_at_conditional_boundary', 'input': value}
    value = timeline()
    value['events'][2].update(lrb=0x40, generation='G1')
    yield {'id': 'timeline-context-before-reused-generation', 'operation': 'last_writer_at_conditional_boundary', 'input': value}
    for ssp in (None, 0, 1, 2, 0x07F0, 0xFFFC, 0xFFFE, 0xFFFF):
        for complete in (False, True):
            yield {'id': f'rti-geometry-{ssp}-{complete}', 'operation': 'rti_obligations', 'input': rti_query(ssp, complete)}
    for role in FRAME_ROLES:
        for category in ('frameWords', 'frameGenerations'):
            value = rti_query(0x07F0, True)
            value[category][role] = None
            yield {'id': f'rti-missing-{category}-{role}', 'operation': 'rti_obligations', 'input': value}
    for premise in PREMISES:
        for answer in (None, False):
            value = rti_query(0x07F0, True)
            value['premises'][premise] = answer
            yield {'id': f'rti-premise-{premise}-{answer}', 'operation': 'rti_obligations', 'input': value}
    for entry in (None, 0, 0x07F1, 0xFFFF):
        value = rti_query(0x07F0, True)
        value['premises']['matchingEntrySsp'] = entry
        yield {'id': 'rti-entry-relation-' + str(entry), 'operation': 'rti_obligations', 'input': value}
    for complete in (False, True):
        value = rti_query(0x07F0, complete)
        value['executionClaim'] = True
        yield {'id': 'rti-forbidden-execution-' + str(complete), 'operation': 'rti_obligations', 'input': value}
    value = rti_query(0x16, True)
    value['premises']['noControlAlias'] = False
    yield {'id': 'rti-declared-control-alias-unsafe', 'operation': 'rti_obligations', 'input': value}
