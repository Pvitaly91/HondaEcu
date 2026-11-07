"""Fixed-address PROGRAM operands for the reviewed mode paths."""
from mode_caller_continuity.mode_producer_extended import MODE_SITES, mode_producer_extended

from .state import Boundary, Effects, frozen, input_class, need, number, shape, slot, tri

PROGRAM_PROOF = 'cceb30cdcd17f7b0bd44ad7d120d46f4b922c3bd3ceb6a0919e576c4ce3fc9d2'
PROGRAM_KEYS = frozenset(('60E6', '60E7', '60EB', '60EC', '60ED', '60EE', '60F0', '60F1', '60FB', '6104', '6105'))
TABLE_SITES = tuple(sorted((*MODE_SITES, 0x60C2, 0x60C6, 0x60C7)))


def validate_operand(operand):
    if operand is None:
        return
    shape(operand, ('space', 'address', 'widthBits', 'index', 'sourceBinding', 'valueClass', 'slot'),
          'ClosedProgramOperandRequired')
    need(type(operand['space']) is str and operand['space'] in ('PROGRAM', 'DATA')
         and number(operand['address'], 0xFFFF) and number(operand['index'], 0xFFFF)
         and type(operand['widthBits']) is int and operand['widthBits'] in (8, 16)
         and (operand['sourceBinding'] is None or type(operand['sourceBinding']) is str)
         and type(operand['valueClass']) is str
         and operand['valueClass'] in ('ConditionalSymbolic', 'InventedOnly', 'ClaimedOemByte'),
         'TypedProgramOperandRequired')
    slot(operand['slot'])


def validate_program(program):
    need(type(program) is dict and set(program) <= PROGRAM_KEYS, 'ClosedProgramOperandMapRequired')
    for operand in program.values():
        need(operand is not None, 'ExplicitProgramOperandRequired')
        validate_operand(operand)


def require_entry(effects, established, pc):
    if established is not True:
        status = 'IndeterminateObligation' if established is None else 'OutsideVerifiedScope'
        effects.halt(status, 'DeclaredConditionalEntryNotEstablished', pc)
    effects.admit(pc)


def load_program(effects, pc, address, following, operand):
    if operand is None or operand['sourceBinding'] is None:
        effects.halt('OutsideVerifiedScope', 'ProgramTableSourceUnbound', pc)
    if operand['sourceBinding'] != PROGRAM_PROOF:
        effects.halt('OutsideVerifiedScope', 'ProgramTableSourceBindingMismatch', pc)
    if operand['space'] != 'PROGRAM' or operand['widthBits'] != 8 or operand['address'] != address:
        effects.halt('OutsideVerifiedScope', 'ProgramOperandSourceMismatch', pc)
    if operand['index'] is not None:
        effects.halt('OutsideVerifiedScope', 'ProgramOperandIsNotIndexed', pc)
    if operand['valueClass'] == 'ClaimedOemByte':
        effects.halt('OutsideVerifiedScope', 'OemProgramValueClaimNotAdmitted', pc)

    key = f'{address:04X}'
    data = operand['slot']
    bits = {f'{key}.{bit}': value for bit, value in data['knownBits'].items()}
    effects.reads.append({'pc': pc, 'space': 'PROGRAM', 'address': address, 'widthBits': 8,
        'value': data['value'], 'bytes': [data['value']], 'knownBits': bits,
        'generations': [data['generation']], 'accessRole': 'BoundSymbolicProgramOperand',
        'stage': effects.procedure, 'sourceBinding': PROGRAM_PROOF, 'valueClass': operand['valueClass']})
    values = frozen.candidates(data['value'], bits, key)
    effects.set_a_byte('al', values)
    effects.r['zf'] = frozen.unique({int(value == 0) for value in values})
    effects.step(pc, following)


def shift_left_byte(effects, pc, following):
    if effects.r['dd'] != 0:
        effects.halt('OutsideVerifiedScope', 'Dd0RequiredForAccumulatorByteShift', pc)
    values = effects.a_values('al')
    effects.r['cf'] = frozen.unique({value >> 7 for value in values})
    effects.set_a_byte('al', {(value << 1) & 0xFF for value in values})
    effects.step(pc, following)


def mode_tail(effects, operand):
    """Reuse the accepted dispatcher up to its exact nonzero-route frontier."""
    child = mode_producer_extended(effects.m2cu_snapshot('At60BD'))
    effects.absorb(child)
    if (child['status'], child['reason'], child['boundary']) == (
            'OutsideVerifiedScope', 'ProgramTableSourceNotAdmitted', 0x60C2):
        load_program(effects, 0x60C2, 0x6105, 0x60C6, operand)
        shift_left_byte(effects, 0x60C6, 0x60C7)
        effects.step(0x60C7, 0x60D2, 'Jump')
        child = mode_producer_extended(effects.m2cu_snapshot('SymbolicCarryTail'))
        effects.absorb(child)
    return effects.result(child['status'], child['reason'], child['boundary'], child['outcome'])


def program_table_path(query):
    shape(query, ('inputClass', 'snapshot', 'entryEstablished', 'operand'), 'ClosedProgramTableQueryRequired')
    input_class(query['inputClass'])
    need(tri(query['entryEstablished']), 'TypedConditionalEntryRequired')
    validate_operand(query['operand'])
    effects = Effects(query['snapshot'], 'program_table_path', TABLE_SITES)
    need(query['inputClass'] == query['snapshot']['inputClass'], 'MatchingInputClassRequired')
    try:
        require_entry(effects, query['entryEstablished'], 0x60BD)
        result = mode_tail(effects, query['operand'])
    except Boundary as stopped:
        result = effects.result(stopped.status, stopped.reason, stopped.pc)
    return {**result, 'programOperandAddress': 0x6105, 'programOperandIndex': None}
