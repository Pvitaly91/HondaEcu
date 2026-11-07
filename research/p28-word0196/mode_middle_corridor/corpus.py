"""Finite invented operands for the mode corridor and immutable composition."""

from copy import deepcopy

from enclosing_caller_return.corpus import MODE_PROOF, case, mode_query, program_operand
from enclosing_caller_return.reference_oracle import mode_enclosing_caller as accepted_prefix
from mode_caller_continuity.corpus import partial, partial_slot


MIDDLE_PROGRAM = (
    0x60E8, 0x60E9, 0x60EA, 0x60F2, 0x60F3, 0x60FC, 0x60FD, 0x60FE,
    0x60FF, 0x6100, 0x6101, 0x6102, 0x6103, 0x7BA4, 0x7BA5, 0x7BA6, 0x7E02,
)
MIDDLE_PROOF = 'a3aa10a1014d8a2de963b1a287709515325482f6ffc306175d66ec1210a53864'


def entry_query(r0=0, caller=0x27D0, bank=0, data03cf=0, data03c7=0):
    """Use only invented prefix data and accepted M2cv operand identity."""
    query = mode_query(MODE_PROOF, caller=caller)
    query['program']['60FB']['slot']['value'] = r0
    query['snapshot']['registers']['scb'] = bank
    query['snapshot']['memory'].update({'03CF': data03cf, '03C7': data03c7})
    return query


def operands(binding=MIDDLE_PROOF, default=1, **overrides):
    result = {f'{address:04X}': program_operand(address, default, binding) for address in MIDDLE_PROGRAM}
    for address, byte in overrides.items():
        result[address]['slot']['value'] = byte
    return result


def continuation_query(prefix=None, program=None, source_binding=None):
    return {
        'inputClass': 'SyntheticTestInput',
        'prefixQuery': entry_query() if prefix is None else prefix,
        'program': operands(MIDDLE_PROOF, **{'60F2': 0}) if program is None else program,
        'sourceBinding': MIDDLE_PROOF if source_binding is None else source_binding,
    }


def middle_query(prefix=None, program=None):
    query = continuation_query(prefix, program)
    query['prefix'] = accepted_prefix(query['prefixQuery'])
    return query


def _covered_paths():
    """Vary independent inputs while each reused PROGRAM address has one slot."""
    for cf_data in (0, 0x80):
        for data_latch in (0, 0x80):
            yield f'carry-{cf_data:02X}-{data_latch:02X}', entry_query(data03cf=cf_data), operands(
                MIDDLE_PROOF, **{'60F2': 0, '7BA6': data_latch})
    for ea in (0, 1):
        for f2 in (0, 1):
            yield f'correlated-program-{ea}-{f2}', entry_query(data03cf=0x80, data03c7=0xE0), operands(
                MIDDLE_PROOF, **{'60EA': ea, '60F2': f2, '7BA6': 0x80})
    for a4, f2, a5 in ((0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)):
        yield f'out-of-line-{a4}-{f2}-{a5}', entry_query(data03cf=0xC0, data03c7=0x80), operands(
            MIDDLE_PROOF, **{'7BA4': a4, '60F2': f2, '7BA5': a5})
    for cf_code in (0, 0x80):
        for f3 in (0, 1):
            yield f'nonzero-{cf_code:02X}-{f3}', entry_query(1, 0x4069, 6), operands(
                MIDDLE_PROOF, **{'60FC': cf_code, '60F3': f3, '7BA6': 0x80})
    yield 'zero-f3-short-circuit', entry_query(), operands(MIDDLE_PROOF, **{'60F2': 0, '60F3': 0})


def corridor_cases():
    operation = 'mode_middle_corridor'
    for suffix, prefix, program in _covered_paths():
        yield case('middle-' + suffix, operation, middle_query(prefix, program))
    for value, bits in ((None, {}), (None, {7: 0}), (None, {7: 1}), (None, {bit: 0 for bit in range(8)})):
        prefix = entry_query(value)
        partial_slot(prefix['program']['60FB']['slot'], bits)
        yield case('middle-r0-partial-' + str(len(bits)) + '-' + str(bits.get(7)), operation,
                   middle_query(prefix))
    for bits in ({}, {7: 0}, {7: 1}):
        prefix = entry_query()
        prefix['snapshot'] = partial(prefix['snapshot'], '03CF', bits)
        program = operands(MIDDLE_PROOF, **{'60F2': 0})
        partial_slot(program['7BA6']['slot'], {7: 1})
        yield case('middle-data03cf-' + str(bits.get(7)), operation, middle_query(prefix, program))
    for field, value in (
        ('address', 0x60EB), ('space', 'DATA'), ('widthBits', 16), ('index', 1),
        ('sourceBinding', 'InventedWrongSource'), ('sourceBinding', None),
        ('valueClass', 'ClaimedOemByte'),
    ):
        query = middle_query()
        query['program']['60EA'][field] = value
        yield case(f'middle-operand-{field}-{value}', operation, query)
    for bits in ({}, {7: 1}, {bit: 0 for bit in range(8)}):
        query = middle_query()
        partial_slot(query['program']['60EA']['slot'], bits)
        yield case(f'middle-program-partial-{len(bits)}', operation, query)
    query = middle_query()
    query['program']['60EA']['slot']['generation'] = None
    yield case('middle-program-missing-generation', operation, query)
    query = middle_query()
    del query['program']['60EA']
    yield case('middle-program-missing-operand', operation, query)
    for field, value in (('boundary', 0x608F), ('actualReturnExecution', True),
                         ('journal', []), ('intermediateStates', [])):
        query = middle_query()
        query['prefix'][field] = value
        yield case(f'middle-forged-prefix-{field}', operation, query)
    query = middle_query()
    query['prefix']['state']['generations']['0208'] = 'InventedEarlierR0'
    yield case('middle-forged-r0-generation', operation, query)
    query = middle_query()
    query['prefix']['state']['registers']['al'] = 0xFF
    yield case('middle-reseed-accumulator', operation, query)
    for binding in (None, 'InventedWrongCorridor'):
        query = middle_query()
        query['sourceBinding'] = binding
        yield case(f'middle-source-binding-{binding}', operation, query)
    for variant in ('same', 'stale-generation', 'changed-byte'):
        query = middle_query()
        slot = deepcopy(query['prefixQuery']['program']['60FB']['slot'])
        if variant == 'stale-generation':
            slot['generation'] = 'InventedStale60FB'
        elif variant == 'changed-byte':
            slot['value'] ^= 1
        query['program']['60FB'] = program_operand(0x60FB, None, MIDDLE_PROOF)
        query['program']['60FB']['slot'] = slot
        yield case('middle-retained-program-60FB-' + variant, operation, query)
    prefix = entry_query()
    prefix['program']['60FB']['slot']['generation'] = None
    yield case('middle-retained-program-60FB-unbound-generation', operation, middle_query(prefix))
    prefix = entry_query(bank=None)
    yield case('middle-frozen-prefix-refusal', operation, middle_query(prefix))


def continuation_cases():
    operation = 'mode_enclosing_continuation'
    for suffix, prefix, program in _covered_paths():
        yield case('join-' + suffix, operation, continuation_query(prefix, program))
    for assumption in ('ordinaryByteSemantics', 'noInterference'):
        for premise in (False, None):
            prefix = entry_query()
            prefix['snapshot']['assumptions'][assumption] = premise
            yield case(f'join-prefix-{assumption}-{premise}', operation, continuation_query(prefix))
    for bank in (None, 1, 3, 7):
        yield case(f'join-bank-{bank}', operation, continuation_query(entry_query(1, bank=bank)))
    for lrb in (None, 0x40, 0x62):
        prefix = entry_query()
        prefix['snapshot']['registers']['lrb'] = lrb
        yield case(f'join-lrb-{lrb}', operation, continuation_query(prefix))
    for boundary_operand in ('60EA', '60F2', '7BA4'):
        query = continuation_query()
        del query['program'][boundary_operand]
        yield case(f'join-missing-{boundary_operand}', operation, query)
    for binding in (None, 'InventedWrongCorridor'):
        query = continuation_query()
        query['sourceBinding'] = binding
        yield case(f'join-source-binding-{binding}', operation, query)
    for suffix_address in ('6104', '6105'):
        prefix = entry_query(1)
        del prefix['program'][suffix_address]
        yield case(f'join-missing-suffix-{suffix_address}', operation, continuation_query(prefix))
    query = continuation_query(entry_query(data03cf=None))
    yield case('join-unknown-middle-branch', operation, query)
    query = continuation_query()
    query['prefixQuery']['snapshot']['generations']['03CB'] = 'ConditionalEffect:mode_enclosing_suffix:0000:1'
    yield case('join-suffix-namespace-collision', operation, query)


def cases():
    yield from corridor_cases()
    yield from continuation_cases()
