"""Invented alternate parser inputs, with explicit source generations."""
from copy import deepcopy

from length_checksum_dataflow.corpus import fixture as prefix_fixture


def case(operation, name, query):
    return {'id': name, 'operation': operation, 'input': deepcopy(query)}


def snapshot(r5=1, r2=7, r3=3, r6=0xFC, status=0x42):
    source = prefix_fixture('Flag')
    source['registers']['scb'] = 0
    source['memory'].update({'03F5': r5, '03F2': r2, '03F3': r3, '03F6': r6, '0356': status})
    return source


def context(index=4, pointer=0x0200, byte=4):
    return {
        'data': {'0084': {'value': 0x34, 'generation': 'InventedDpLow'},
                 '0085': {'value': 0x12, 'generation': 'InventedDpHigh'},
                 '0200': {'value': byte, 'generation': 'InventedResponse'}},
        'knownDataBits': {},
        'programWords': [{'address': 0x6E12 + 2 * index, 'value': pointer,
                          'generation': 'InventedProgramWord'}],
        'dataMapping': 'ConditionalStandardInternal201',
    }


def path_cases():
    source = snapshot()
    unknown_scb = {**source, 'registers': {**source['registers'], 'scb': None}}
    old_flags = {**source, 'registers': {**source['registers'], 'zf': None}}
    for name, state, extra in (
        ('r2-selection', snapshot(r5=2, r2=7, r6=0xFA), context()),
        ('r2-same-value', snapshot(r5=2, r2=0, r6=0x80), context()),
        ('table-read', source, context()),
        ('index-wrap', snapshot(r5=1, r3=0xFF), context(index=0)),
        ('pointer-alias', source, context(pointer=0x0084)),
        ('sfr-write-only', source, context(pointer=0x0051)),
        ('sfr-read-sensitive', source, context(pointer=0x0055)),
        ('external-unbound', source, context(pointer=0x0500)),
        ('unknown-pointer', source, context(pointer=None)),
        ('missing-program', source, {**context(), 'programWords': []}),
        ('unknown-mapping', source, {**context(), 'dataMapping': 'Unknown'}),
        ('unknown-scb', unknown_scb, context()),
        ('unknown-r5', snapshot(r5=None), context()),
        ('partial-r5', snapshot(r5=None), {**context(), 'knownDataBits': {'03F5.7': 1}}),
        ('unknown-r6', snapshot(r5=2, r6=None), context()),
        ('equal-length', snapshot(r5=4, r2=4, r6=1), context()),
        ('equal-length-zero', snapshot(r5=4, r2=4, r6=0), context()),
        ('greater-length', snapshot(r5=5, r2=4), context()),
    ):
        yield case('alternate_response_selector', 'path-' + name, {'snapshot': state, 'context': extra})
    for name, entry, state in (
        ('r2-entry', 0x024C, source),
        ('conditional-equal', 0x024F, source),
        ('conditional-not-equal', 0x024F, {**source, 'registers': {**source['registers'], 'zf': 0}}),
        ('unknown-predicate', 0x024F, old_flags),
    ):
        yield case('alternate_auxiliary_024c_0253', 'aux-' + name,
                   {'snapshot': state, 'context': context(), 'entryPc': entry})


def composition_cases():
    unknown_bit = snapshot(status=None)
    unknown_bit['knownBits']['0356.1'] = 1
    partial_taken = snapshot(r5=2, status=None)
    partial_taken['knownBits'].update({'0356.1': 1, '0356.6': 1})
    missing_generation = snapshot()
    missing_generation['generations']['0356'] = None
    wrong_bank = snapshot()
    wrong_bank['registers']['lrb'] = 0x7D
    for name, state, generation, extra in (
        ('table', snapshot(), snapshot()['generations']['0356'], context()),
        ('partial-taken', partial_taken, partial_taken['generations']['0356'], context()),
        ('old-bit-clear', snapshot(status=2), snapshot()['generations']['0356'], context()),
        ('mode-clear', snapshot(status=0x40), snapshot()['generations']['0356'], context()),
        ('unknown-bit', unknown_bit, unknown_bit['generations']['0356'], context()),
        ('wrong-bank', wrong_bank, wrong_bank['generations']['0356'], context()),
        ('wrong-generation', snapshot(), 'InventedWrongGeneration', context()),
        ('unknown-generation', missing_generation, None, context()),
        ('epilogue', snapshot(r5=5, r2=4), snapshot()['generations']['0356'], context()),
        ('blocked-read', snapshot(), snapshot()['generations']['0356'], context(pointer=0x0051)),
    ):
        yield case('alternate_parser_step', 'composition-' + name,
                   {'snapshot': state, 'statusGeneration': generation, 'context': extra})


def checksum_cases():
    for site, operands in ((0x023C, ((0, 0), (0, 1), (255, 1), (15, 1), (255, 255), (None, 4))),
                           (0x0252, ((0, 0), (0, 1), (0, 16), (0, 255), (0, None), (1, 4)))):
        for left, right in operands:
            yield case('alternate_checksum_accumulation', f'checksum-{site:04x}-{left}-{right}',
                       {'site': site, 'left': left, 'right': right})


def addressing_cases():
    raw = {'pc': 0x023B, 'address': 0x0200, 'space': 'DATA', 'widthBits': 8, 'scb': 0, 'lrb': 0x7E,
           'dataMapping': 'ConditionalStandardInternal201'}
    for name, changes in (
        ('ordinary', {}), ('alias-accumulator', {'pc': 0x0231, 'address': 6, 'widthBits': 16}),
        ('wrong-aligned-alias', {'pc': 0x0231, 'address': 7, 'widthBits': 16}),
        ('alias-pointer', {'address': 0x0085}), ('alias-local', {'address': 0x03F6,
          'dataMapping': 'ConditionalStandardInternal207'}), ('unknown-address', {'address': None}),
        ('wrong-space', {'space': 'PROGRAM'}), ('wrong-width', {'widthBits': 16}),
        ('write-only', {'address': 0x0051}), ('sfr-side-effect', {'address': 0x0055}),
        ('potential-sfr', {'address': 0x0033}), ('outside', {'pc': 0x023E}),
        ('unknown-mapping', {'dataMapping': 'Unknown'}), ('external-unbound', {'address': 0x03F6}),
    ):
        yield case('alternate_memory_read_obligations', 'memory-' + name, {**raw, **changes})
    word = {'address': 0x6E1A, 'space': 'PROGRAM', 'widthBits': 16,
            'value': 0x0200, 'generation': 'InventedProgramWord'}
    source = {'indexByte': 4, 'scb': 0, 'lrb': 0x7E, 'programWord': word,
              'dataMapping': 'ConditionalStandardInternal201'}
    for name, changes in (
        ('exact', {}), ('unknown-index', {'indexByte': None}), ('unknown-scb', {'scb': None}),
        ('unknown-lrb', {'lrb': None}), ('missing-word', {'programWord': None}),
        ('wrong-space', {'programWord': {**word, 'space': 'DATA'}}),
        ('wrong-width', {'programWord': {**word, 'widthBits': 8}}),
        ('wrong-address', {'programWord': {**word, 'address': 0x6E1B}}),
        ('unknown-generation', {'programWord': {**word, 'generation': None}}),
        ('unknown-word', {'programWord': {**word, 'value': None}}),
        ('sfr-output', {'programWord': {**word, 'value': 0x0051}}),
    ):
        yield case('program_to_data_address_qualification', 'address-' + name, {**source, **changes})


def cases():
    yield from path_cases()
    yield from composition_cases()
    yield from checksum_cases()
    yield from addressing_cases()
