"""Explicit partial software state and ordered effects, without hardware authority."""
from copy import deepcopy

ADDRESSES = (0x18, 0x19, 0x1A, 0x1B, 0x40, 0x43, 0x46, 0x55, 0x80, 0x81,
             0xB4, 0xB6, 0xF5, 0xF8, 0xF9, 0xFA, 0xFB, 0x125, 0x1AD, 0x212,
             0x217, 0x21D, 0x356, *range(0x3F0, 0x3F8))
DATA_KEYS = frozenset(f'{a:04X}' for a in ADDRESSES)
BIT_FIELDS = frozenset(('0019.7', '0040.2', '0043.2', '0043.3', '00B4.0', '00B6.7',
    '0125.7', '0212.3', '0217.2', '021D.7', '0356.1', '0356.6', '0356.7'))
REGISTERS = frozenset(('al', 'ah', 'cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw', 'lrb', 'scb', 'usp', 'ssp'))
OBSERVED = ('al', 'ah', 'cf', 'zf', 'hc', 'dd', 'mie')
INPUT_CLASSES = frozenset(('SyntheticTestInput', 'SymbolicInput', 'ManufacturerSourceQualifiedState'))


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def number(value, maximum):
    return value is None or type(value) is int and 0 <= value <= maximum


def validate(snapshot):
    need(type(snapshot) is dict and set(snapshot) == {
        'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions'}, 'ClosedConditionalSnapshotRequired')
    need(type(snapshot['inputClass']) is str and snapshot['inputClass'] in INPUT_CLASSES,
         'ActualHardwareInputNotAdmitted')
    memory, bits, registers = snapshot['memory'], snapshot['knownBits'], snapshot['registers']
    need(type(memory) is dict and set(memory) == DATA_KEYS and all(number(v, 255) for v in memory.values()),
         'ExplicitTypedThirtyOneByteScopeRequired')
    need(type(bits) is dict and set(bits) <= BIT_FIELDS and all(type(v) is int and v in (0, 1) for v in bits.values()),
         'TypedQualifiedPartialBitsRequired')
    for field, value in bits.items():
        address, bit = field.split('.')
        need(memory[address] is None or memory[address] >> int(bit) & 1 == value, 'ContradictoryBitKnowledge')
    need(type(registers) is dict and set(registers) == REGISTERS, 'ExplicitArchitecturalInputsRequired')
    for name in REGISTERS:
        maximum = 255 if name in ('al', 'ah') else 7 if name == 'scb' else 65535 if name in ('otherPsw', 'lrb', 'usp', 'ssp') else 1
        need(number(registers[name], maximum), 'TypedRegisterOrUnknownRequired')
    need(registers['otherPsw'] is None or registers['otherPsw'] & 0xF107 == 0,
         'OtherPswCannotAliasNamedFlagsOrScb')
    generations = snapshot['generations']
    need(type(generations) is dict and set(generations) == DATA_KEYS
         and all(v is None or type(v) is str and bool(v) for v in generations.values()), 'TypedInputGenerationLabelsRequired')
    assumptions = snapshot['assumptions']
    need(type(assumptions) is dict and set(assumptions) == {'noInterference', 'ordinaryByteSemantics', 'dataMapping'}
         and all(v is None or type(v) is bool for k, v in assumptions.items() if k != 'dataMapping')
         and assumptions['dataMapping'] == 'ConditionalByteArray', 'ConditionalAssumptionsNotNativeProof')
    return snapshot


def word(parts):
    return None if any(v is None for v in parts) else parts[0] | parts[1] << 8


def zero(parts):
    if any(v is not None and v != 0 for v in parts):
        return 0
    return 1 if all(v == 0 for v in parts) else None


class Boundary(Exception):
    def __init__(self, status, reason, pc):
        self.status, self.reason, self.pc = status, reason, pc


class Effects:
    """Bookkeeping for mathematical functions; never fetches or decodes instructions."""

    def __init__(self, snapshot, procedure):
        validate(snapshot)
        self.input = deepcopy(snapshot)
        self.state = {key: deepcopy(snapshot[key]) for key in ('memory', 'knownBits', 'registers', 'generations')}
        self.r = self.state['registers']
        self.procedure = procedure
        self.journal, self.reads, self.steps, self.intermediate = [], [], [], []

    def halt(self, status, reason, pc):
        raise Boundary(status, reason, pc)

    def admit(self, entry, mode=False):
        if self.input['assumptions']['noInterference'] is not True:
            self.halt('OutsideVerifiedScope', 'NoInterferencePremiseNotEstablished', entry)
        if self.r['lrb'] != (0x40 if mode else 0x7E) or mode and self.r['scb'] != 0:
            self.halt('OutsideVerifiedScope', 'UnsupportedContext', entry)

    def require_usp(self, pc):
        if self.r['usp'] != 0x180:
            self.halt('OutsideVerifiedScope', 'NamedUSPAddressNotEstablished', pc)

    def step(self, pc, following, kind='Linear', taken=None):
        self.steps.append({'pc': pc, 'next': following, 'kind': kind, 'branchTaken': taken,
                           'afterRegisters': {k: self.r[k] for k in OBSERVED}})

    def branch(self, pc, condition, yes, no):
        need(condition is None or type(condition) is bool, 'BooleanOrUnknownPredicateRequired')
        self.step(pc, None if condition is None else yes if condition else no, 'Branch', condition)
        if condition is None:
            self.halt('IndeterminateBranch', 'UnknownBranchPredicate', pc)
        return condition

    def read(self, pc, address, width=8):
        address = address & 0xFFFE if width == 16 else address
        keys = [f'{address + i:04X}' for i in range(width // 8)]
        parts = [self.state['memory'][key] for key in keys]
        self.reads.append({'pc': pc, 'space': 'DATA', 'address': address, 'widthBits': width,
            'value': word(parts) if width == 16 else parts[0], 'bytes': parts,
            'knownBits': {k: v for k, v in self.state['knownBits'].items() if k[:4] in keys}})
        return parts

    def bit_value(self, address, bit):
        raw = self.state['memory'][f'{address:04X}']
        return self.state['knownBits'].get(f'{address:04X}.{bit}') if raw is None else raw >> bit & 1

    def read_bit(self, pc, address, bit):
        self.read(pc, address)
        return self.bit_value(address, bit)

    def _event(self, pc, address, before, after, kind, source, space, generations):
        width = 8 * len(after)
        old, new = (word(v) if width == 16 else v[0] for v in (before, after))
        ordinal = len(self.journal) + 1
        generation = f'ConditionalEffect:{self.procedure}:{pc:04X}:{ordinal}'
        self.journal.append({'ordinal': ordinal, 'pc': pc, 'space': space, 'address': address,
            'widthBits': width, 'before': old, 'after': new, 'beforeBytes': before, 'afterBytes': after,
            'kind': kind, 'sameValue': old == new if old is not None and new is not None else None,
            'beforeGeneration': generations, 'afterGeneration': generation, 'valueSource': source,
            'effectClass': 'ConditionalRomEffect'})
        if space == 'DATA':
            for i in range(len(after)):
                self.state['generations'][f'{address + i:04X}'] = generation
        self.intermediate.append({'afterOrdinal': ordinal, 'pc': pc, 'state': deepcopy(self.state)})

    def store(self, pc, address, parts, kind='Store', source='A', preserve_bits=False):
        address = address & 0xFFFE if len(parts) == 2 else address
        keys = [f'{address + i:04X}' for i in range(len(parts))]
        before = [self.state['memory'][k] for k in keys]
        generations = [self.state['generations'][k] for k in keys]
        for key, part in zip(keys, parts):
            self.state['memory'][key] = part
            if part is not None or not preserve_bits:
                self.state['knownBits'] = {k: v for k, v in self.state['knownBits'].items() if k[:4] != key}
        self._event(pc, address, before, parts, kind, source, 'DATA', generations)

    def bit(self, pc, address, bit, setting, following):
        self.read(pc, address)
        old = self.bit_value(address, bit)
        raw = self.state['memory'][f'{address:04X}']
        self.r['zf'] = None if old is None else int(old == 0)
        new = None if raw is None else raw | (1 << bit) if setting else raw & ~(1 << bit)
        if new is None:
            self.state['knownBits'][f'{address:04X}.{bit}'] = setting
        self.store(pc, address, [new], 'RMW', f'BitSet:{bit}' if setting else f'BitClear:{bit}', preserve_bits=True)
        self.step(pc, following)

    def load_byte(self, pc, address, following):
        if self.input['assumptions']['ordinaryByteSemantics'] is not True:
            self.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', pc)
        value = self.read(pc, address)[0]
        self.r.update(al=value, dd=0, zf=None if value is None else int(value == 0))
        self.step(pc, following)

    def load_word(self, pc, following, address=None, literal=None):
        parts = self.read(pc, address, 16) if address is not None else [literal & 255, literal >> 8]
        self.r.update(al=parts[0], ah=parts[1], dd=1, zf=zero(parts))
        self.step(pc, following)

    def compare_byte(self, pc, left, right, following):
        self.r.update(cf=None if left is None or right is None else int(left < right),
                      zf=None if left is None or right is None else int(left == right))
        self.step(pc, following)

    def compare_word(self, pc, address, following):
        right = word(self.read(pc, address, 16))
        left = word([self.r['al'], self.r['ah']])
        self.r.update(cf=None if left is None or right is None else int(left < right),
                      zf=None if left is None or right is None else int(left == right))
        self.step(pc, following)

    def store_a(self, pc, address, following):
        self.store(pc, address, [self.r['al'], self.r['ah']])
        self.step(pc, following)

    def literal_word(self, pc, address, value, following, kind='ImmediateStore'):
        self.store(pc, address, [value & 255, value >> 8], kind, 'Literal')
        self.step(pc, following)

    def pswh_byte(self):
        if self.r['otherPsw'] is None or any(self.r[k] is None for k in ('cf', 'zf', 'hc', 'dd', 'mie')):
            return None
        return ((self.r['otherPsw'] >> 8) & 0x0E) | sum(self.r[k] << bit for k, bit in (
            ('mie', 0), ('dd', 4), ('hc', 5), ('zf', 6), ('cf', 7)))

    def mask_pswh(self, pc, mie, following):
        before = self.pswh_byte()
        known = {f'0005.{bit}': self.r[key] for key, bit in (
            ('mie', 0), ('dd', 4), ('hc', 5), ('zf', 6), ('cf', 7)) if self.r[key] is not None}
        self.reads.append({'pc': pc, 'space': 'REGISTER', 'address': 5, 'widthBits': 8,
                           'value': before, 'bytes': [before], 'knownBits': known})
        self.r.update(mie=mie, zf=None)
        self._event(pc, 5, [before], [self.pswh_byte()], 'RegisterMask', 'PSWH|01' if mie else 'PSWH&FE', 'REGISTER', [None])
        self.step(pc, following)

    def finish(self, outcome, boundary):
        return self.result('CompleteConditional', 'VerifiedSelectedSourcePath', boundary, outcome)

    def result(self, status, reason, boundary, outcome=None):
        return {'procedure': self.procedure, 'status': status, 'reason': reason, 'boundary': boundary,
            'outcome': outcome, 'inputClass': self.input['inputClass'], 'assumptions': self.input['assumptions'],
            'state': self.state, 'journal': self.journal, 'reads': self.reads, 'steps': self.steps,
            'intermediateStates': self.intermediate, 'effectClass': 'ConditionalRomEffect',
            'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}


def reconstruct(snapshot, procedure, entry, body, mode=False):
    effects = Effects(snapshot, procedure)
    try:
        effects.admit(entry, mode)
        return body(effects)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)
