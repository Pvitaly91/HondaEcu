"""Two source-qualified DATA transformations, without a CPU or peripheral transition."""
from copy import deepcopy
import re

from .analysis import AUTHORITY

SOURCE_ID = 'M2dgReviewed0240_0241'
ENTRY = 0x0240
BIT_SET = 0x0241
EPILOGUE = 0x0244
ENTRY_FIELDS = {'sourceId', 'entryPc', 'inputClass', 'assumptions', 'state'}
STATE_FIELDS = {'registers', 'memory', 'generations', 'knownBits', 'registerGenerations', 'registerKnownBits'}
REGISTER_WIDTHS = {'al': 8, 'ah': 8, 'cf': 1, 'zf': 1, 'hc': 1, 'dd': 1, 'mie': 1,
                   'otherPsw': 16, 'lrb': 16, 'scb': 3, 'usp': 16, 'ssp': 16}
OBLIGATIONS = ['UnprovedNativeHandoff', 'ActualStbufAcceptanceUnknown', 'PhysicalDataMappingUnknown',
               'TxProgressionUnknown', 'EpilogueEffectsOutsideScope']


def _value(value, width):
    return value is None or type(value) is int and 0 <= value < 1 << width


def _generation(value):
    return value is None or type(value) is str and 0 < len(value) <= 256


def _bits(value, bits):
    return all(value is None or value >> int(bit) & 1 == known for bit, known in bits.items())


def _valid_state(state):
    if type(state) is not dict or set(state) != STATE_FIELDS or any(type(v) is not dict for v in state.values()):
        return False
    registers, memory = state['registers'], state['memory']
    generations, bits = state['generations'], state['knownBits']
    register_generations, register_bits = state['registerGenerations'], state['registerKnownBits']
    if (not set(registers) <= REGISTER_WIDTHS.keys() or not all(_value(v, REGISTER_WIDTHS[k]) for k, v in registers.items())
            or registers.get('otherPsw') is not None and registers['otherPsw'] & 0xF107
            or len(memory) > 512 or not all(type(k) is str and re.fullmatch('[0-9A-F]{4}', k)
                                           and int(k, 16) >= 8 and _value(v, 8) for k, v in memory.items())
            or set(generations) != set(memory) or not all(_generation(v) for v in generations.values())
            or not set(register_generations) <= registers.keys()
            or not all(_generation(v) for v in register_generations.values())
            or not set(register_bits) <= {'al', 'ah'}):
        return False
    for field, bit in bits.items():
        if (type(field) is not str or not re.fullmatch('[0-9A-F]{4}\\.[0-7]', field)
                or field[:4] not in memory or type(bit) is not int or bit not in (0, 1)
                or not _bits(memory[field[:4]], {field[-1]: bit})):
            return False
    if not all(name in registers and type(known) is dict
               and all(type(k) is str and k in '01234567' and len(k) == 1 and type(v) is int and v in (0, 1)
                       for k, v in known.items())
               and _bits(registers[name], known) for name, known in register_bits.items()):
        return False
    scb, usp = registers.get('scb'), registers.get('usp')
    if scb is not None and usp is not None:
        for offset in range(2):
            key = f'{0x86 + 8 * scb + offset:04X}'
            value = usp >> (8 * offset) & 255
            if (memory.get(key) not in (None, value)
                    or not _bits(value, {field[-1]: bit for field, bit in bits.items() if field[:4] == key})):
                return False
    return True


def _entry_reason(snapshot):
    if type(snapshot) is not dict or set(snapshot) != ENTRY_FIELDS:
        return 'ClosedDetachedSnapshotRequired'
    if snapshot['sourceId'] != SOURCE_ID:
        return 'ReviewedSourceIdentityRequired'
    if type(snapshot['entryPc']) is not int or snapshot['entryPc'] != ENTRY:
        return 'ExactDetachedEntry0240Required'
    if snapshot['inputClass'] not in ('SymbolicInput', 'SyntheticTestInput', 'ManufacturerSourceQualifiedState'):
        return 'SymbolicInputClassRequired'
    premises = snapshot['assumptions']
    if (type(premises) is not dict or set(premises) != {'noInterference', 'ordinaryInternalRam'}
            or any(v is not None and type(v) is not bool for v in premises.values())):
        return 'ClosedDetachedPremisesRequired'
    if not _valid_state(snapshot['state']):
        return 'TypedSourceStateRequired'
    if premises['noInterference'] is not True:
        return 'NoInterferencePremiseRequired'
    if snapshot['state']['registers'].get('lrb') != 0x007E:
        return 'ExactReviewedLrb007ERequired'
    if premises['ordinaryInternalRam'] is not True:
        return 'OrdinaryWritableDataPremiseRequired'
    return None


def _result(status, reason, pc, state=None, steps=(), reads=(), journal=()):
    return {'status': status, 'reason': reason, 'stopPc': pc,
            'stopBoundary': 'STOP_BEFORE_EPILOGUE_0244' if pc == EPILOGUE else None,
            'state': state, 'entryKind': 'DetachedSymbolicEntry', 'steps': list(steps),
            'reads': list(reads), 'journal': list(journal), 'unresolved': list(OBLIGATIONS),
            'executionAuthority': dict(AUTHORITY)}


def _common(values):
    return next(iter(values)) if len(values) == 1 else None


def _apply(state, pc, successor, address, increment, steps, reads, journal):
    slot = f'{address:04X}'
    generation = f'M2dg:DATA:{pc:04X}:{len(journal) + 1}'
    flag_generations = {f'M2dg:Flag:{pc:04X}:ZF'}
    if increment:
        flag_generations.add(f'M2dg:Flag:{pc:04X}:HC')
    if slot not in state['memory']:
        return 'RequiredDataSlotMissing'
    before_generation = state['generations'][slot]
    if before_generation is None:
        return 'RequiredDataGenerationMissing'
    if ({generation, *flag_generations} & (set(state['generations'].values())
                                          | set(state['registerGenerations'].values()))):
        return 'WriterGenerationCollision'
    before = state['memory'][slot]
    known = {key[-1]: v for key, v in state['knownBits'].items() if key[:4] == slot}
    possible = [before] if before is not None else [v for v in range(256) if _bits(v, known)]
    if increment:
        after_values = {(v + 1) % 256 for v in possible}
        flags = {'zf': _common({int(v == 0) for v in after_values}),
                 'hc': _common({int((v & 15) == 15) for v in possible})}
        source = 'r5+1'
    else:
        after_values = {v | 0x40 for v in possible}
        flags = {'zf': _common({int(not v & 0x40) for v in possible})}
        source = 'DATA0356.Bit6Set'
    after = _common(after_values)
    registers = state['registers']
    before_flags = {key: registers.get(key) for key in flags}
    registers.update(flags)
    state['registerGenerations'].update({key: f'M2dg:Flag:{pc:04X}:{key.upper()}' for key in flags})
    reads.append({'pc': pc, 'space': 'DATA', 'address': address, 'widthBits': 8, 'value': before,
                  'knownBits': known, 'generation': before_generation, 'kind': 'FunctionalRmwRead'})
    state['memory'][slot] = after
    state['generations'][slot] = generation
    state['knownBits'] = {key: v for key, v in state['knownBits'].items() if key[:4] != slot}
    if after is None:
        for bit in range(8):
            value = _common({v >> bit & 1 for v in after_values})
            if value is not None:
                state['knownBits'][f'{slot}.{bit}'] = value
    journal.append({'ordinal': len(journal) + 1, 'pc': pc, 'space': 'DATA', 'address': address,
                    'widthBits': 8, 'before': before, 'after': after, 'beforeGeneration': before_generation,
                    'afterGeneration': generation, 'valueSource': source, 'kind': 'RMW',
                    'sameValue': False if increment else _common({bool(v & 0x40) for v in possible}),
                    'effectClass': 'ConditionalSoftwareEffect'})
    steps.append({'pc': pc, 'next': successor, 'edge': 'ConfirmedStaticCFG', 'branchPredicate': None,
                  'beforeFlags': before_flags, 'afterFlags': flags, 'state': deepcopy(state)})
    return None


def detached_0240_0241_transform(snapshot):
    """Retain the exact proven prefix when an operand or its generation is absent."""
    reason = _entry_reason(snapshot)
    if reason:
        return _result('RefusedDetachedEntry', reason, ENTRY)
    state = deepcopy(snapshot['state'])
    steps, reads, journal = [], [], []
    # The reviewed r5 alias uses local base (LRB & 1FFF) << 3, while off
    # addressing uses page (LRB & 1FE0) << 3. Neither requires SCB.
    lrb = state['registers']['lrb']
    for pc, successor, address, increment in (
        (ENTRY, BIT_SET, ((lrb & 0x1FFF) << 3) + 5, True),
        (BIT_SET, EPILOGUE, ((lrb & 0x1FE0) << 3) + 0x56, False),
    ):
        reason = _apply(state, pc, successor, address, increment, steps, reads, journal)
        if reason:
            return _result('OutsideVerifiedScope', reason, pc, state, steps, reads, journal)
    return _result('ConditionalSourceArrivalAt0244', None, EPILOGUE, state, steps, reads, journal)
