"""Bounded 5F45 source entry prefix and separately qualified 608F suffix."""
from copy import deepcopy

from native_data0217_011f_bridge.helper_cfg import NODE_ROWS

from .program_table import TABLE_SITES, load_program, mode_tail, require_entry, shift_left_byte, validate_program
from .state import Boundary, Effects, frozen, input_class, need, number, shape, tri

CALLER_CONTEXTS = {
    0x27D0: {'callerPc': 0x27D0, 'target': 0x5F45, 'length': 3, 'candidateReturn': 0x27D3,
             'listedIncomingDd': 0, 'priorSourceBoundary': 0x27CE, 'priorContext': 'ConditionalColdRoute'},
    0x4069: {'callerPc': 0x4069, 'target': 0x5F45, 'length': 3, 'candidateReturn': 0x406C,
             'listedIncomingDd': 1, 'priorSourceBoundary': 0x4068, 'priorContext': 'RequiresOwnVCAL3ReturnTo4069'},
}
PREFIX_SITES = tuple(pc for pc, _, _, _ in NODE_ROWS if 0x5F45 <= pc <= 0x5F9D) + (0x7DF4,)
SUFFIX_SITES = tuple(pc for pc, _, _, _ in NODE_ROWS if 0x608F <= pc <= 0x60BA)
SOURCE_SITES = tuple(sorted((*PREFIX_SITES, *SUFFIX_SITES, *TABLE_SITES)))


def _local_bank(effects, pc):
    if effects.r['lrb'] != 0x41:
        effects.halt('OutsideVerifiedScope', 'LocalBank0208NotEstablished', pc)


def _move_carry(effects, pc, address, bit, following, *, off_page=True):
    if off_page:
        lrb = effects.r['lrb']
        if lrb is None or lrb & 0x1FE0 != 0x40:
            effects.halt('OutsideVerifiedScope', 'ModePage0200NotEstablished', pc)
    else:
        effects.pointer_dependency(pc)
    effects.read(pc, address)
    key = f'{address:04X}'
    raw = effects.state['memory'][key]
    carry = effects.r['cf']
    mask = 1 << bit
    if raw is not None and carry is not None:
        after, known = (raw & ~mask) | (carry << bit), {}
    else:
        after = None
        old = frozen.candidates(raw, effects.state['knownBits'], key)
        carries = (0, 1) if carry is None else (carry,)
        values = {(value & ~mask) | (chosen << bit) for value in old for chosen in carries}
        known = frozen.bit_consensus(values, key)
    effects.store(pc, address, [after], 'RMW', f'CarryBitMove:{bit}', partial=known)
    effects.step(pc, following)


def _store_al(effects, pc, address, following):
    _local_bank(effects, pc)
    effects.store(pc, address, [effects.r['al']], 'Store', 'AL', partial=effects.a_partial(address, ('al',)))
    effects.step(pc, following)


def _load(effects, program, pc, address, following):
    load_program(effects, pc, address, following, program.get(f'{address:04X}'))


def _load_shift_and_move(effects, program, rows):
    for load, operand, shift, move, address, bit, following in rows:
        _load(effects, program, load, operand, shift)
        shift_left_byte(effects, shift, move)
        _move_carry(effects, move, address, bit, following)


def _entry_prefix(effects, program):
    if effects.input['assumptions']['ordinaryByteSemantics'] is not True:
        effects.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', 0x5F45)
    effects.set_a_byte('al', {0})
    effects.r.update(zf=1, dd=0)
    effects.step(0x5F45, 0x5F46)
    _load_shift_and_move(effects, program, (
        (0x5F46, 0x60E6, 0x5F4A, 0x5F4B, 0x0216, 4, 0x5F4E),
        (0x5F4E, 0x60E7, 0x5F52, 0x5F53, 0x0227, 6, 0x5F56),
    ))
    effects.step(0x5F56, 0x5F5E, 'Jump')
    _load_shift_and_move(effects, program, (
        (0x5F5E, 0x60EB, 0x5F62, 0x5F63, 0x0219, 3, 0x5F66),
        (0x5F66, 0x60EC, 0x5F6A, 0x5F6B, 0x0217, 3, 0x5F6E),
        (0x5F6E, 0x60ED, 0x5F72, 0x5F73, 0x0227, 7, 0x5F76),
        (0x5F76, 0x60EE, 0x5F7A, 0x5F7B, 0x0216, 1, 0x5F7E),
        (0x5F7E, 0x60F0, 0x5F82, 0x5F83, 0x0216, 7, 0x5F86),
    ))
    effects.dp(0x5F86, 0x0356, 0x5F89)
    _move_carry(effects, 0x5F89, 0x0356, 0, 0x5F8B, off_page=False)
    _load_shift_and_move(effects, program, (
        (0x5F8B, 0x60F1, 0x5F8F, 0x5F90, 0x0227, 1, 0x5F93),
    ))
    effects.dp(0x5F93, 0x03C7, 0x5F96)
    effects.load_byte(0x5F96, 0x03C7, 0x5F97, pointer=True)
    _store_al(effects, 0x5F97, 0x0209, 0x5F98)
    effects.r['cf'] = 0
    effects.step(0x5F98, 0x5F99)
    _load(effects, program, 0x5F99, 0x60FB, 0x5F9D)
    effects.step(0x5F9D, 0x7DF4, 'Jump')
    _store_al(effects, 0x7DF4, 0x0208, 0x7DF5)
    return effects.finish('ModeEntryPrefixPreparedLocalR0', 0x7DF5)


def _compare(effects, pc, address, literal, following, *, pointer=False):
    if pointer:
        effects.pointer_dependency(pc)
    effects.read(pc, address)
    key = f'{address:04X}'
    values = frozen.candidates(effects.state['memory'][key], effects.state['knownBits'], key)
    effects.compare_values(pc, values, literal, following)


def _equals(effects, pc, yes, no):
    zero = effects.r['zf']
    return effects.branch(pc, None if zero is None else zero == 1, yes, no)


def _zero_r0_suffix(effects, program):
    effects.r['cf'] = 0
    effects.step(0x609B, 0x609C)
    bit = effects.read_bit(0x609C, 0x0217, 6)
    if effects.branch(0x609C, None if bit is None else bit == 1, 0x60BA, 0x609F):
        return
    _load(effects, program, 0x609F, 0x6104, 0x60A3)
    if _equals(effects, 0x60A3, 0x60BA, 0x60A5):
        return
    for pc in range(0x60A5, 0x60B4):
        effects.step(pc, pc + 1)
    effects.dp(0x60B4, 0x03CE, 0x60B7)
    _compare(effects, 0x60B7, 0x03CE, 0x9A, 0x60BA, pointer=True)


def _detached_suffix(effects, program):
    if effects.r['dd'] != 0:
        effects.halt('OutsideVerifiedScope', 'ModeSuffixDd0NotEstablished', 0x608F)
    _local_bank(effects, 0x608F)
    _compare(effects, 0x608F, 0x0208, 0, 0x6092)
    if _equals(effects, 0x6092, 0x609B, 0x6094):
        _zero_r0_suffix(effects, program)
    else:
        _load(effects, program, 0x6094, 0x6104, 0x6098)
        shift_left_byte(effects, 0x6098, 0x6099)
        effects.step(0x6099, 0x60BA, 'Jump')
    _move_carry(effects, 0x60BA, 0x0219, 4, 0x60BD)
    return mode_tail(effects, program.get('6105'))


def mode_enclosing_caller(query):
    shape(query, ('inputClass', 'callerPc', 'snapshot', 'entry', 'entryEstablished', 'program'),
          'ClosedModeEnclosingQueryRequired')
    input_class(query['inputClass'])
    need(number(query['callerPc'], 0xFFFF) and tri(query['entryEstablished'])
         and type(query['entry']) is str and query['entry'] in ('From5F45', 'At608F'),
         'TypedModeCallerEntryRequired')
    validate_program(query['program'])
    effects = Effects(query['snapshot'], 'mode_enclosing_caller', SOURCE_SITES)
    need(query['inputClass'] == query['snapshot']['inputClass'], 'MatchingInputClassRequired')
    caller_pc = query['callerPc']
    from_entry = query['entry'] == 'From5F45'
    caller = deepcopy(CALLER_CONTEXTS.get(caller_pc)) if from_entry else None
    try:
        if from_entry:
            if caller is None:
                effects.halt('OutsideVerifiedScope', 'UnreviewedModeCaller', 0x5F45)
            require_entry(effects, query['entryEstablished'], 0x5F45)
            result = _entry_prefix(effects, query['program'])
        else:
            if caller_pc is not None:
                effects.halt('OutsideVerifiedScope', 'CallerHistoryNotEstablishedForDetachedEntry', 0x608F)
            require_entry(effects, query['entryEstablished'], 0x608F)
            result = _detached_suffix(effects, query['program'])
    except Boundary as stopped:
        result = effects.result(stopped.status, stopped.reason, stopped.pc)
    return {**result, 'entryVariant': query['entry'], 'callerContext': caller}
