"""Independent abstract reference from reviewed source rules, never CPU output.

This module imports only the shared invented input corpus. It neither imports
the implementation under test nor reads its contract or results.
"""
from copy import deepcopy
import json

from .corpus import ADDRESSES, cases

BIT_FIELDS = frozenset(('0019.7', '0040.2', '0043.2', '0043.3', '00B4.0', '00B6.7',
    '0125.7', '0212.3', '0217.2', '021D.7', '0356.1', '0356.6', '0356.7'))
REGISTERS = frozenset(('al', 'ah', 'cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw', 'lrb', 'scb', 'usp', 'ssp'))
SHOWN = ('al', 'ah', 'cf', 'zf', 'hc', 'dd', 'mie')


def _optional_integer(value, maximum):
    return value is None or type(value) is int and 0 <= value <= maximum


def _checked(snapshot):
    if type(snapshot) is not dict or set(snapshot) != {'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions'}:
        raise ValueError('ReferenceSnapshotShape')
    if snapshot['inputClass'] not in ('SyntheticTestInput', 'SymbolicInput', 'ManufacturerSourceQualifiedState'):
        raise ValueError('ReferenceInputClass')
    memory, bits, regs, gens, assumptions = (snapshot[k] for k in ('memory', 'knownBits', 'registers', 'generations', 'assumptions'))
    if type(memory) is not dict or set(memory) != set(ADDRESSES) or not all(_optional_integer(v, 255) for v in memory.values()):
        raise ValueError('ReferenceMemoryShape')
    if type(gens) is not dict or set(gens) != set(ADDRESSES) or not all(v is None or type(v) is str and bool(v) for v in gens.values()):
        raise ValueError('ReferenceGenerationShape')
    if type(bits) is not dict or not set(bits) <= BIT_FIELDS:
        raise ValueError('ReferenceKnownBitShape')
    for key, value in bits.items():
        if type(value) is not int or value not in (0, 1):
            raise ValueError('ReferenceKnownBitType')
        raw = memory[key[:4]]
        if raw is not None and ((raw >> int(key[-1])) & 1) != value:
            raise ValueError('ReferenceContradictoryKnownBit')
    if type(regs) is not dict or set(regs) != REGISTERS:
        raise ValueError('ReferenceRegisterShape')
    bounds = {'al': 255, 'ah': 255, 'cf': 1, 'zf': 1, 'hc': 1, 'dd': 1, 'mie': 1,
              'otherPsw': 65535, 'lrb': 65535, 'scb': 7, 'usp': 65535, 'ssp': 65535}
    if any(not _optional_integer(regs[key], bound) for key, bound in bounds.items()):
        raise ValueError('ReferenceRegisterType')
    if regs['otherPsw'] is not None and regs['otherPsw'] & 0xF107:
        raise ValueError('ReferenceOtherPswMask')
    if (type(assumptions) is not dict or set(assumptions) != {'noInterference', 'ordinaryByteSemantics', 'dataMapping'}
            or any(v is not None and type(v) is not bool for v in (assumptions['noInterference'], assumptions['ordinaryByteSemantics']))
            or assumptions['dataMapping'] != 'ConditionalByteArray'):
        raise ValueError('ReferenceAssumptions')
    return deepcopy(snapshot)


def _whole(values):
    return None if any(v is None for v in values) else sum(v << (8 * n) for n, v in enumerate(values))


def _zero(value):
    return None if value is None else int(value == 0)


def _both(a, b):
    if a == 0 or b == 0:
        return 0
    return 1 if a == b == 1 else None


class _Reference:
    def __init__(self, snapshot, procedure):
        original = _checked(snapshot)
        self.original = original
        self.name = procedure
        self.state = {key: deepcopy(original[key]) for key in ('memory', 'knownBits', 'registers', 'generations')}
        self.journal, self.reads, self.steps, self.intermediate = [], [], [], []

    @property
    def registers(self):
        return self.state['registers']

    def result(self, boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        return {'procedure': self.name, 'status': status, 'reason': reason, 'boundary': boundary,
                'outcome': outcome, 'inputClass': self.original['inputClass'],
                'assumptions': deepcopy(self.original['assumptions']), 'state': deepcopy(self.state),
                'journal': deepcopy(self.journal), 'reads': deepcopy(self.reads), 'steps': deepcopy(self.steps),
                'intermediateStates': deepcopy(self.intermediate), 'effectClass': 'ConditionalRomEffect',
                'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
                'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}

    def outside(self, boundary, reason):
        return self.result(boundary, status='OutsideVerifiedScope', reason=reason)

    def admission(self, entry, flag=False):
        if self.original['assumptions']['noInterference'] is not True:
            return self.outside(entry, 'NoInterferencePremiseNotEstablished')
        if self.registers['lrb'] != (0x007E if flag else 0x0040) or not flag and self.registers['scb'] != 0:
            return self.outside(entry, 'UnsupportedContext')
        return None

    def step(self, pc, successor, kind='Linear', taken=None):
        self.steps.append({'pc': pc, 'next': successor, 'kind': kind, 'branchTaken': taken,
                           'afterRegisters': {key: self.registers[key] for key in SHOWN}})

    def branch(self, pc, predicate, yes, no, outside=False):
        destination = None if predicate is None else yes if predicate else no
        self.step(pc, destination, 'Branch', None if predicate is None else bool(predicate))
        if predicate is None:
            return self.result(pc, status='IndeterminateBranch', reason='UnknownBranchPredicate')
        if outside and predicate:
            return self.outside(destination, 'UnmodeledBranch')
        return None

    def bit(self, address, bit):
        name = f'{address:04X}'
        value = self.state['memory'][name]
        return self.state['knownBits'].get(name + '.' + str(bit)) if value is None else (value >> bit) & 1

    def read(self, pc, address, width=8):
        address = address if width == 8 else address & 0xFFFE
        names = [f'{address + i:04X}' for i in range(width // 8)]
        values = [self.state['memory'][key] for key in names]
        self.reads.append({'pc': pc, 'space': 'DATA', 'address': address, 'widthBits': width,
            'value': _whole(values), 'bytes': values,
            'knownBits': {key: value for key, value in self.state['knownBits'].items() if key[:4] in names}})
        return values

    def _packed_pswh(self):
        r = self.registers
        if any(r[key] is None for key in ('otherPsw', 'mie', 'dd', 'hc', 'zf', 'cf')):
            return None
        return ((r['otherPsw'] >> 8) & 0x0E) | r['mie'] | r['dd'] * 16 | r['hc'] * 32 | r['zf'] * 64 | r['cf'] * 128

    def write(self, pc, address, values, kind, source, register_before=None):
        width = len(values) * 8
        register = kind == 'RegisterMask'
        space = 'REGISTER' if register else 'DATA'
        address = address if width == 8 else address & 0xFFFE
        names = [f'{address + i:04X}' for i in range(len(values))]
        before = [register_before] if register else [self.state['memory'][key] for key in names]
        generations = [None] if register else [self.state['generations'][key] for key in names]
        number = len(self.journal) + 1
        generation = f'ConditionalEffect:{self.name}:{pc:04X}:{number}'
        if not register:
            for name, value in zip(names, values):
                self.state['memory'][name] = value
                self.state['generations'][name] = generation
                self.state['knownBits'] = {k: v for k, v in self.state['knownBits'].items() if k[:4] != name}
        old, new = _whole(before), _whole(values)
        self.journal.append({'ordinal': number, 'pc': pc, 'space': space, 'address': address,
            'widthBits': width, 'before': old, 'after': new, 'beforeBytes': before, 'afterBytes': list(values),
            'kind': kind, 'sameValue': None if old is None or new is None else old == new,
            'beforeGeneration': generations, 'afterGeneration': generation, 'valueSource': source,
            'effectClass': 'ConditionalRomEffect'})
        self.intermediate.append({'afterOrdinal': number, 'pc': pc, 'state': deepcopy(self.state)})

    def rmw(self, pc, address, bit, set_to):
        self.read(pc, address)
        old_bit = self.bit(address, bit)
        before_bits = deepcopy(self.state['knownBits'])
        raw = self.state['memory'][f'{address:04X}']
        after = None if raw is None else (raw | (1 << bit)) if set_to else (raw & ~(1 << bit))
        self.registers['zf'] = None if old_bit is None else 1 - old_bit
        self.write(pc, address, [after], 'RMW', ('BitSet:' if set_to else 'BitClear:') + str(bit))
        if raw is None:
            self.state['knownBits'] = before_bits
            self.state['knownBits'][f'{address:04X}.{bit}'] = set_to
            self.intermediate[-1]['state'] = deepcopy(self.state)
        return old_bit

    def pswh(self, pc, mie):
        before = self._packed_pswh()
        knowledge = {'0005.' + str(bit): self.registers[key]
                     for key, bit in (('mie', 0), ('dd', 4), ('hc', 5), ('zf', 6), ('cf', 7))
                     if self.registers[key] is not None}
        self.reads.append({'pc': pc, 'space': 'REGISTER', 'address': 5, 'widthBits': 8,
                           'value': before, 'bytes': [before], 'knownBits': knowledge})
        self.registers['mie'], self.registers['zf'] = mie, None
        self.write(pc, 5, [self._packed_pswh()], 'RegisterMask', 'PSWH|01' if mie else 'PSWH&FE', register_before=before)

    def byte_load(self, pc, address, successor):
        if self.original['assumptions']['ordinaryByteSemantics'] is not True:
            return self.outside(pc, 'OrdinaryByteSemanticsNotEstablished')
        value = self.read(pc, address)[0]
        self.registers.update(al=value, dd=0, zf=_zero(value))
        self.step(pc, successor)
        return None

    def literal_word(self, pc, value, successor):
        self.registers.update(al=value % 256, ah=value // 256, dd=1, zf=int(value == 0))
        self.step(pc, successor)

    def word_load(self, pc, address, successor):
        lo, hi = self.read(pc, address, 16)
        zf = 0 if any(v is not None and v != 0 for v in (lo, hi)) else 1 if lo == hi == 0 else None
        self.registers.update(al=lo, ah=hi, dd=1, zf=zf)
        self.step(pc, successor)

    def compare_byte(self, left, right):
        self.registers.update(cf=None if left is None or right is None else int(left < right),
                              zf=None if left is None or right is None else int(left == right))

    def compare_word(self, pc, address, successor):
        actual = _whole(self.read(pc, address, 16))
        expected = _whole([self.registers['al'], self.registers['ah']])
        self.compare_byte(expected, actual)
        self.step(pc, successor)

    def add_values(self, left, right):
        if left is None or right is None:
            self.registers.update(cf=None, zf=None, hc=None)
            return None
        total = left + right
        self.registers.update(cf=int(total >= 256), zf=int(total % 256 == 0),
                              hc=int((left % 16) + (right % 16) >= 16))
        return total % 256


def _flag_body(reference):
    r = reference
    stopped = r.byte_load(0x0262, 0x0055, 0x0264)
    if stopped is not None:
        return stopped
    value = r.read(0x0264, 0x03F5)[0]
    r.compare_byte(value, 2)
    r.step(0x0264, 0x0267)
    stopped = r.branch(0x0267, None if value is None else value != 2, 0x026C, 0x0269, outside=True)
    if stopped is not None:
        return stopped
    r.write(0x0269, 0x03F3, [r.registers['al']], 'Store', 'AL')
    r.step(0x0269, 0x026A)
    r.step(0x026A, 0x026D, 'Jump', True)
    prior = r.read(0x026D, 0x03F6)[0]
    result = r.add_values(prior, r.registers['al'])
    r.write(0x026D, 0x03F6, [result], 'RMW', 'DATA03F6+AL')
    r.step(0x026D, 0x026F)
    count = r.read(0x026F, 0x03F5)[0]
    new_count = None if count is None else (count + 1) % 256
    r.registers.update(zf=_zero(new_count), hc=None if count is None else int(count % 16 == 15))
    r.write(0x026F, 0x03F5, [new_count], 'RMW', 'DATA03F5+1')
    r.step(0x026F, 0x0270)
    r.write(0x0270, 0x03F7, [2], 'ImmediateStore', 'Literal')
    r.step(0x0270, 0x0272)
    return r.result(0x0272, 'FlagWritten')


def status_clear(snapshot):
    r = _Reference(snapshot, 'status_clear')
    refusal = r.admission(0x0222, flag=True)
    if refusal is not None:
        return refusal
    r.rmw(0x0222, 0x0356, 6, 0)
    r.step(0x0222, 0x0225)
    return r.result(0x0225, 'StatusCleared')


def flag_body(snapshot):
    r = _Reference(snapshot, 'flag_body')
    refusal = r.admission(0x0262, flag=True)
    return refusal if refusal is not None else _flag_body(r)


def flag_path(snapshot):
    r = _Reference(snapshot, 'flag_path')
    stopped = r.admission(0x021F, flag=True)
    if stopped is not None:
        return stopped
    r.read(0x021F, 0x0356)
    mode = r.bit(0x0356, 1)
    stopped = r.branch(0x021F, None if mode is None else mode == 0, 0x029D, 0x0222, outside=True)
    if stopped is not None:
        return stopped
    old_error = r.rmw(0x0222, 0x0356, 6, 0)
    r.step(0x0222, 0x0225)
    predicate = None if old_error is None else old_error == 0
    stopped = r.branch(0x0225, predicate, 0x0255, 0x0227)
    if stopped is not None:
        return stopped
    if predicate is False:
        return r.outside(0x0227, 'UnmodeledBranch')
    stopped = r.byte_load(0x0255, 0x03F7, 0x0256)
    if stopped is not None:
        return stopped
    stopped = r.branch(0x0256, None if r.registers['zf'] is None else bool(r.registers['zf']), 0x0275, 0x0258, outside=True)
    if stopped is not None:
        return stopped
    stopped = r.byte_load(0x0258, 0x03F5, 0x0259)
    if stopped is not None:
        return stopped
    r.compare_byte(r.registers['al'], 1)
    r.step(0x0259, 0x025B)
    stopped = r.branch(0x025B, None if r.registers['zf'] is None else bool(r.registers['zf']), 0x027F, 0x025D, outside=True)
    if stopped is not None:
        return stopped
    r.registers['al'] = r.add_values(r.registers['al'], 1)
    r.step(0x025D, 0x025F)
    length = r.read(0x025F, 0x03F2)[0]
    r.compare_byte(r.registers['al'], length)
    r.step(0x025F, 0x0260)
    stopped = r.branch(0x0260, None if r.registers['zf'] is None else bool(r.registers['zf']), 0x0284, 0x0262, outside=True)
    return stopped if stopped is not None else _flag_body(r)


def initial_pair(snapshot):
    r = _Reference(snapshot, 'initial_pair')
    stopped = r.admission(0x54DD)
    if stopped is not None:
        return stopped
    r.write(0x54DD, 0x00FA, [0xA0, 0x02], 'ImmediateStore', 'Literal')
    r.step(0x54DD, 0x54E2)
    r.literal_word(0x54E2, 0x2BAB, 0x54E5)
    r.write(0x54E5, 0x00F8, [r.registers['al'], r.registers['ah']], 'Store', 'A')
    r.step(0x54E5, 0x54E7)
    r.write(0x54E7, 0x0046, [0], 'Clear', 'Literal')
    r.step(0x54E7, 0x54EA)
    r.write(0x54EA, 0x0018, [0, 0], 'Clear', 'Literal')
    r.step(0x54EA, 0x54ED)
    r.rmw(0x54ED, 0x0040, 2, 0)
    r.step(0x54ED, 0x54F0)
    r.write(0x54F0, 0x001A, [r.registers['al'], r.registers['ah']], 'Store', 'A')
    r.step(0x54F0, 0x54F2)
    return r.result(0x54F2, 'InitialPair')


def mode_switch(snapshot):
    r = _Reference(snapshot, 'mode_switch')
    stopped = r.admission(0x3EEA)
    if stopped is not None:
        return stopped
    r.word_load(0x3EEA, 0x00FA, 0x3EEC)
    r.write(0x3EEC, 0x001A, [r.registers['al'], r.registers['ah']], 'Store', 'A')
    r.step(0x3EEC, 0x3EEE)
    r.pswh(0x3EEE, 0)
    r.step(0x3EEE, 0x3EF1)
    r.read(0x3EF1, 0x0212)
    gate = r.bit(0x0212, 3)
    stopped = r.branch(0x3EF1, gate, 0x3F22, 0x3EF4)
    if stopped is not None:
        return stopped
    choose_b = gate == 1
    if gate == 0:
        r.read(0x3EF4, 0x0217)
        mode = r.bit(0x0217, 2)
        stopped = r.branch(0x3EF4, mode, 0x3F02, 0x3EF7)
        if stopped is not None:
            return stopped
        if mode == 0:
            old_irq = r.rmw(0x3EF7, 0x0019, 7, 0)
            r.step(0x3EF7, 0x3EFA)
            stopped = r.branch(0x3EFA, None if old_irq is None else old_irq == 0, 0x3F02, 0x3EFC)
            if stopped is not None:
                return stopped
            if old_irq == 1:
                r.rmw(0x3EFC, 0x00B6, 7, 1)
                r.step(0x3EFC, 0x3EFF)
                r.rmw(0x3EFF, 0x00B4, 0, 1)
                r.step(0x3EFF, 0x3F02)
        r.pswh(0x3F02, 1)
        r.step(0x3F02, 0x3F05)
        if r.registers['usp'] != 0x0180:
            return r.outside(0x3F05, 'NamedUSPAddressNotEstablished')
        threshold = r.read(0x3F05, 0x01AD)[0]
        r.compare_byte(threshold, 0x29)
        r.step(0x3F05, 0x3F09)
        r.pswh(0x3F09, 0)
        r.step(0x3F09, 0x3F0C)
        stopped = r.branch(0x3F0C, r.registers['cf'], 0x3F22, 0x3F0E)
        if stopped is not None:
            return stopped
        choose_b = r.registers['cf'] == 1
    if choose_b:
        r.read(0x3F22, 0x0217)
        mode = r.bit(0x0217, 2)
        stopped = r.branch(0x3F22, mode, 0x3F40, 0x3F25)
        if stopped is not None:
            return stopped
        if mode == 0:
            r.literal_word(0x3F25, 0xA9A3, 0x3F28)
            r.write(0x3F28, 0x001A, [0xA3, 0xA9], 'Store', 'A')
            r.step(0x3F28, 0x3F2A)
            r.write(0x3F2A, 0x00F8, [0xA3, 0xA9], 'Store', 'A')
            r.step(0x3F2A, 0x3F2C)
            r.write(0x3F2C, 0x00FA, [0xA0, 0], 'ImmediateStore', 'Literal')
            r.step(0x3F2C, 0x3F31)
            r.rmw(0x3F31, 0x0217, 2, 1)
            r.step(0x3F31, 0x3F34)
            if r.registers['usp'] != 0x0180:
                return r.outside(0x3F34, 'NamedUSPAddressNotEstablished')
            r.rmw(0x3F34, 0x0125, 7, 0)
            r.step(0x3F34, 0x3F37)
            r.rmw(0x3F37, 0x021D, 7, 0)
            r.step(0x3F37, 0x3F3A)
            r.rmw(0x3F3A, 0x0043, 3, 1)
            r.step(0x3F3A, 0x3F3D)
            r.rmw(0x3F3D, 0x0043, 2, 1)
            r.step(0x3F3D, 0x3F40)
            outcome = 'PairB'
        else:
            outcome = 'NoSwitch'
    else:
        r.read(0x3F0E, 0x0217)
        mode = r.bit(0x0217, 2)
        stopped = r.branch(0x3F0E, None if mode is None else mode == 0, 0x3F40, 0x3F11)
        if stopped is not None:
            return stopped
        if mode == 1:
            r.literal_word(0x3F11, 0x2BAB, 0x3F14)
            r.write(0x3F14, 0x001A, [0xAB, 0x2B], 'Store', 'A')
            r.step(0x3F14, 0x3F16)
            r.write(0x3F16, 0x00F8, [0xAB, 0x2B], 'Store', 'A')
            r.step(0x3F16, 0x3F18)
            r.write(0x3F18, 0x00FA, [0xA0, 0x02], 'ImmediateStore', 'Literal')
            r.step(0x3F18, 0x3F1D)
            r.rmw(0x3F1D, 0x0217, 2, 0)
            r.step(0x3F1D, 0x3F20)
            r.step(0x3F20, 0x3F40, 'Jump', True)
            outcome = 'PairA'
        else:
            outcome = 'NoSwitch'
    r.pswh(0x3F40, 1)
    r.step(0x3F40, 0x3F43)
    r.word_load(0x3F43, 0x00F8, 0x3F45)
    r.write(0x3F45, 0x001A, [r.registers['al'], r.registers['ah']], 'Store', 'A')
    r.step(0x3F45, 0x3F47)
    return r.result(0x3F47, outcome)


def consistency_check(snapshot):
    r = _Reference(snapshot, 'consistency_check')
    stopped = r.admission(0x3E81)
    if stopped is not None:
        return stopped
    r.literal_word(0x3E81, 0x2BAB, 0x3E84)
    r.write(0x3E84, 0x0080, [0xA0, 0x02], 'PointerStore', 'Literal')
    r.step(0x3E84, 0x3E87)
    r.read(0x3E87, 0x0217)
    mode = r.bit(0x0217, 2)
    stopped = r.branch(0x3E87, None if mode is None else mode == 0, 0x3E90, 0x3E8A)
    if stopped is not None:
        return stopped
    if mode == 1:
        r.literal_word(0x3E8A, 0xA9A3, 0x3E8D)
        r.write(0x3E8D, 0x0080, [0xA0, 0], 'PointerStore', 'Literal')
        r.step(0x3E8D, 0x3E90)
    failed = False
    for compare_pc, address, branch_pc, next_pc in ((0x3E90, 0x00F8, 0x3E93, 0x3E95),
                                                   (0x3E95, 0x001A, 0x3E98, 0x3E9A)):
        r.compare_word(compare_pc, address, branch_pc)
        different = None if r.registers['zf'] is None else r.registers['zf'] == 0
        stopped = r.branch(branch_pc, different, 0x3EA0, next_pc)
        if stopped is not None:
            return stopped
        if different:
            failed = True
            break
    if not failed:
        r.word_load(0x3E9A, 0x0080, 0x3E9B)
        r.compare_word(0x3E9B, 0x00FA, 0x3E9E)
        equal = None if r.registers['zf'] is None else r.registers['zf'] == 1
        stopped = r.branch(0x3E9E, equal, 0x3EA7, 0x3EA0)
        if stopped is not None:
            return stopped
        if equal:
            return r.result(0x3EA7, 'Consistent')
    r.write(0x3EA0, 0x00F5, [0x4F], 'ImmediateStore', 'Literal')
    r.step(0x3EA0, 0x3EA4)
    r.step(0x3EA4, 0x24E0, 'Jump', True)
    return r.result(0x24E0, 'Inconsistent')


def mask_hypotheses(snapshot):
    value = _checked(snapshot)
    rows = []
    bits = [None if value['memory'][key] is None else (value['memory'][key] // 2) % 2
            for key in ('001A', '00FA', '00F8')]
    mie = value['registers']['mie']
    for label, enabled in (('Set1', 1), ('Set0', 0)):
        interpreted = [None if bit is None else int(bit == enabled) for bit in bits]
        rows.append({'hypothesis': label, 'ieRx': interpreted[0], 'faRx': interpreted[1],
                     'f8Rx': interpreted[2], 'mie': mie, 'maskGateCondition': _both(interpreted[0], mie),
                     'actualIrqDelivery': None})
    return {'inputClass': value['inputClass'], 'hypotheses': rows, 'actualHardwareObservation': None,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}


OPERATIONS = {'status_clear': status_clear, 'flag_body': flag_body, 'flag_path': flag_path,
              'initial_pair': initial_pair, 'mode_switch': mode_switch,
              'consistency_check': consistency_check, 'mask_hypotheses': mask_hypotheses}


def expected_records():
    for case in cases():
        yield {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
               'output': OPERATIONS[case['operation']](case['input'])}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii') + b'\n'


def canonical_bytes():
    return b''.join(canonical(row) for row in expected_records())
