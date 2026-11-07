"""Conditional mode reconstruction between the accepted prefix and suffix."""
from copy import deepcopy
import json

from enclosing_caller_return.mode_caller import mode_enclosing_caller
from enclosing_caller_return.program_table import shift_left_byte, validate_operand

from .corridor_cfg import CORRIDOR_SCOPE, ENTRY, NODES, STOP, branch_targets, following
from .source_inventory import SOURCE_IDENTITIES
from .state import Boundary, Effects, frozen, input_class, label, need, shape, snapshot_from_child

PROCEDURE = 'mode_middle_corridor'
PROGRAM_PROOF = SOURCE_IDENTITIES['corridor']
PROGRAM_KEYS = frozenset(('60E8', '60E9', '60EA', '60F2', '60F3', '60FB', '60FC', '60FD', '60FE', '60FF',
                          '6100', '6101', '6102', '6103', '7BA4', '7BA5', '7BA6', '7E02'))


def validate_program(program):
    need(type(program) is dict and set(program) <= PROGRAM_KEYS, 'ClosedProgramOperandMapRequired')
    for operand in program.values():
        need(operand is not None, 'ExplicitProgramOperandRequired')
        validate_operand(operand)


def _operand_refusal(row, address):
    if row is None or row['sourceBinding'] is None:
        return 'ProgramTableSourceUnbound'
    if row['sourceBinding'] != PROGRAM_PROOF:
        return 'ProgramTableSourceBindingMismatch'
    if (row['space'], row['widthBits'], row['address']) != ('PROGRAM', 8, address):
        return 'ProgramOperandSourceMismatch'
    if row['index'] is not None:
        return 'ProgramOperandIsNotIndexed'
    if row['valueClass'] == 'ClaimedOemByte':
        return 'OemProgramValueClaimNotAdmitted'
    if row['slot']['generation'] is None:
        return 'ProgramOperandGenerationUnbound'
    return None


class Corridor(Effects):
    def __init__(self, prefix_query, prefix, program):
        super().__init__(snapshot_from_child(prefix_query['snapshot'], prefix), PROCEDURE, CORRIDOR_SCOPE)
        self.program = program
        self.prefix = prefix
        self.prefix_program = prefix_query['program'].get('60FB')
        self.specific.extend(('ModeMiddleCorridorStaticOnly', 'NativeCallReturnUnestablished'))
        self.predicates = []
        self.pswh_dataflow = []
        self.r0_lineage = None
        self.f0_generation = None
        self.latch_generation = None

    def result(self, status, reason, boundary, outcome=None):
        if self.r0_lineage is not None:
            self.r0_lineage['retainedAtBoundary'] = self.r0_lineage['generation'] == self.state['generations']['0208']
        return {**super().result(status, reason, boundary, outcome), 'prefixResult': deepcopy(self.prefix),
                'correlatedPredicates': self.predicates, 'r0Lineage': self.r0_lineage,
                'pswhDataflow': self.pswh_dataflow}

    def prepare(self, source_binding):
        self.admit(ENTRY)
        if source_binding != PROGRAM_PROOF:
            reason = 'MiddleCorridorSourceUnbound' if source_binding is None else 'MiddleCorridorSourceBindingMismatch'
            self.halt('OutsideVerifiedScope', reason, ENTRY)
        if self.r['dd'] != 0:
            self.halt('OutsideVerifiedScope', 'ModeMiddleCorridorDd0NotEstablished', ENTRY)
        if self.r['lrb'] != 0x41:
            self.halt('OutsideVerifiedScope', 'LocalBank0208NotEstablished', ENTRY)
        generation = self.prefix_program['slot']['generation']
        if generation is None:
            self.halt('OutsideVerifiedScope', 'RetainedProgram60FBGenerationUnbound', ENTRY)
        repeated = self.program.get('60FB')
        if repeated is not None and (_operand_refusal(repeated, 0x60FB)
                                     or repeated['slot'] != self.prefix_program['slot']):
            self.halt('OutsideVerifiedScope', 'RetainedProgram60FBMismatch', ENTRY)
        self.r0_lineage = {'address': 0x0208, 'writerPc': 0x7DF4,
                           'generation': self.state['generations']['0208'], 'programAddress': 0x60FB,
                           'programGeneration': generation, 'retainedAtBoundary': True}

    def step(self, pc, next_pc, kind='Linear', taken=None):
        expected = self.steps[-1]['next'] if self.steps else ENTRY
        need(pc == expected and pc in NODES and (next_pc in NODES[pc][2]
             or (next_pc is None and kind == 'Branch' and taken is None)), 'CorridorSourceEdgeMismatch')
        super().step(pc, next_pc, kind, taken)

    def linear(self, *pcs):
        for pc in pcs:
            kind = 'Jump' if NODES[pc][0].startswith(('J ', 'SJ ')) else 'Linear'
            self.step(pc, following(pc), kind)

    def program_generation(self, address):
        if address == 0x60FB:
            return self.prefix_program['slot']['generation']
        return self.program[f'{address:04X}']['slot']['generation']

    def load_program(self, pc, address):
        key = f'{address:04X}'
        row = self.program.get(key)
        reason = _operand_refusal(row, address)
        if reason is not None:
            self.halt('OutsideVerifiedScope', reason, pc)
        data = row['slot']
        bits = {f'{key}.{bit}': value for bit, value in data['knownBits'].items()}
        self.reads.append({'pc': pc, 'space': 'PROGRAM', 'address': address, 'widthBits': 8,
                           'value': data['value'], 'bytes': [data['value']], 'knownBits': bits,
                           'generations': [data['generation']], 'accessRole': 'BoundSymbolicProgramOperand',
                           'stage': self.procedure, 'sourceBinding': PROGRAM_PROOF, 'valueClass': row['valueClass']})
        values = frozen.candidates(data['value'], bits, key)
        self.set_a_byte('al', values)
        self.r['zf'] = frozen.unique({int(value == 0) for value in values})
        self.linear(pc)

    def shift(self, *pcs):
        for pc in pcs:
            shift_left_byte(self, pc, following(pc))

    def load_shift(self, load_pc, address, shift_pc):
        self.load_program(load_pc, address)
        self.shift(shift_pc)

    def get_values(self, address):
        key = f'{address:04X}'
        return frozen.candidates(self.state['memory'][key], self.state['knownBits'], key)

    def load_data(self, pc, address, *, pointer=False):
        self.load_byte(pc, address, following(pc), pointer=pointer)

    def store_al(self, pc, address):
        self.store(pc, address, [self.r['al']], 'Store', 'AL', partial=self.a_partial(address, ('al',)))
        self.linear(pc)

    def store_values(self, pc, address, values, kind, source):
        known = frozen.bit_consensus(values, f'{address:04X}')
        self.store(pc, address, [frozen.unique(values)], kind, source, partial=known)
        self.linear(pc)

    def set_carry(self, pc, value):
        self.r['cf'] = value
        self.linear(pc)

    def load_carry(self, pc, address, bit):
        self.set_carry(pc, self.read_bit(pc, address, bit))

    def store_carry(self, pc, address, bit):
        self.read(pc, address)
        key = f'{address:04X}'
        raw = self.state['memory'][key]
        carry = self.r['cf']
        mask = 1 << bit
        if raw is not None and carry is not None:
            value, partial = (raw & ~mask) | (carry << bit), None
        else:
            values = {(old & ~mask) | (chosen << bit) for old in self.get_values(address)
                      for chosen in ((0, 1) if carry is None else (carry,))}
            value, partial = None, frozen.bit_consensus(values, key)
        self.store(pc, address, [value], 'RMW', f'CarryBitMove:{bit}', partial=partial)
        self.linear(pc)

    def predicate(self, pc, value, true_value, space, address, bit, generation, source_pc):
        taken = None if value is None else value == true_value
        self.predicates.append({'pc': pc, 'sourceSpace': space, 'sourceAddress': address, 'sourceBit': bit,
                                'sourceGeneration': generation, 'sourcePc': source_pc, 'value': value,
                                'taken': taken})
        return self.branch(pc, taken, *branch_targets(pc))

    def zero_predicate(self, pc, operand_address, producer):
        true_value = int(NODES[pc][0].startswith('JEQ '))
        return self.predicate(pc, self.r['zf'], true_value, 'PROGRAM', operand_address, None,
                              self.program_generation(operand_address), producer)

    def test_r0(self, compare, branch):
        self.read(compare, 0x0208)
        self.compare_values(compare, self.get_values(0x0208), 0, following(compare))
        return self.zero_predicate(branch, 0x60FB, compare)

    def psw_known(self, address):
        other = {int(bit): value for bit, value in self.state['otherPswKnownBits'].items()}
        if address == 4:
            known = {bit: value for bit, value in other.items() if bit < 8}
            if self.r['scb'] is not None:
                known.update({bit: (self.r['scb'] >> bit) & 1 for bit in range(3)})
            return known
        known = {bit - 8: value for bit, value in other.items() if bit >= 8}
        for bit, field in ((0, 'mie'), (4, 'dd'), (5, 'hc'), (6, 'zf'), (7, 'cf')):
            if self.r[field] is not None:
                known[bit] = self.r[field]
        return known

    @staticmethod
    def pack_byte(known):
        return sum(value << bit for bit, value in known.items()) if len(known) == 8 else None

    def psw_read(self, pc, address, generation):
        known = self.psw_known(address)
        value = self.pack_byte(known)
        self.reads.append({'pc': pc, 'space': 'REGISTER', 'address': address, 'widthBits': 8,
                           'value': value, 'bytes': [value], 'knownBits': {f'{address:04X}.{k}': v for k, v in known.items()},
                           'generations': [generation], 'accessRole': 'RegisterOperand', 'stage': self.procedure})
        return value

    def psw_write(self, pc, address, old, generation, kind, source):
        value = self.pack_byte(self.psw_known(address))
        self._event(pc, address, [old], [value], kind, source, 'REGISTER', [generation])
        return self.journal[-1]['afterGeneration']

    def flags(self):
        return {name: self.r[name] for name in ('cf', 'zf', 'hc')}

    def psw_trace(self, pc, kind, before, prior, generation):
        self.pswh_dataflow.append({'pc': pc, 'kind': kind, 'beforeFlags': before, 'afterFlags': self.flags(),
                                  'priorF0': prior, 'valueF0': self.f0_value(), 'generation': generation})
        self.linear(pc)

    def xor_pswh(self, pc):
        before, prior = self.flags(), self.f0_value()
        old = self.psw_read(pc, 5, None)
        # The primary PSW rule leaves CF/ZF/HC undefined for this write.
        self.r.update(cf=None, zf=None, hc=None)
        generation = self.psw_write(pc, 5, old, None, 'RegisterXor', 'PSWH^80')
        self.psw_trace(pc, 'XorPswhUnknownFlags', before, prior, generation)

    def store_f0(self, pc, *, clear=False):
        before, prior = self.flags(), self.f0_value()
        old = self.psw_read(pc, 4, self.f0_generation)
        if clear:
            self.r['zf'] = None if prior is None else 1 - prior
            value, kind, source, trace = 0, 'RegisterBitClear', 'BitClear:4', 'ClearF0'
        else:
            value, kind, source, trace = self.r['cf'], 'RegisterBitMove', 'CarryBitMove:4', 'StoreF0'
        self.set_f0(value)
        self.f0_generation = self.psw_write(pc, 4, old, self.f0_generation, kind, source)
        self.psw_trace(pc, trace, before, prior, self.f0_generation)

    def load_f0(self, pc):
        before, prior = self.flags(), self.f0_value()
        self.psw_read(pc, 4, self.f0_generation)
        self.r['cf'] = prior
        self.psw_trace(pc, 'LoadF0', before, prior, self.f0_generation)

    def entry_select(self):
        if self.zero_predicate(0x7DF5, 0x60FB, 0x5F99):
            self.load_shift(0x7DFA, 0x7E02, 0x7DFE)
            self.linear(0x7DFF)
        else:
            self.linear(0x7DF7)
            self.load_program(0x5FA0, 0x60EA)
            if not self.zero_predicate(0x5FA4, 0x60EA, 0x5FA0):
                self.load_data(0x5FA6, 0x0209)
                self.shift(0x5FA7, 0x5FA8)
                self.read(0x5FA9, 0x0209)
                values = {value & 0x80 for value in self.get_values(0x0209)}
                self.r['zf'] = frozen.unique({int(value == 0) for value in values})
                self.store_values(0x5FA9, 0x0209, values, 'RMW', 'ANDB:80')
        self.store_carry(0x5FAC, 0x0227, 5)

    def load_local_r2(self):
        self.dp(0x5FAF, 0x03CF, following(0x5FAF))
        self.load_data(0x5FB2, 0x03CF, pointer=True)
        self.store_al(0x5FB3, 0x020A)
        self.load_program(0x5FB4, 0x60EA)
        if not self.zero_predicate(0x5FB8, 0x60EA, 0x5FB4):
            self.read(0x5FBA, 0x020A)
            values = self.get_values(0x020A)
            self.r['cf'] = frozen.unique({value >> 7 for value in values})
            self.store_values(0x5FBA, 0x020A, {(value << 1) & 255 for value in values}, 'RMW', 'SLLB')
            self.store_values(0x5FBC, 0x020A, {0x80}, 'ImmediateStore', 'Literal')
            self.read(0x5FBE, 0x020A)
            carry = self.r['cf']
            values = self.get_values(0x020A)
            self.r['cf'] = frozen.unique({value & 1 for value in values})
            self.store_values(0x5FBE, 0x020A, {(value >> 1) | (bit << 7) for value in values
                                               for bit in ((0, 1) if carry is None else (carry,))},
                              'RMW', 'RORB')
        self.load_data(0x5FC0, 0x020A)

    def latch_selector(self):
        zero = self.test_r0(0x5FC1, 0x5FC4)
        if not zero:
            self.load_program(0x5FC6, 0x60FC)
        self.shift(0x5FCA)
        self.linear(0x5FCB)
        self.store_carry(0x7B45, 0x0216, 3)
        space, address, generation = ('DATA', 0x03CF, self.state['generations']['03CF']) if zero else (
            'PROGRAM', 0x60FC, self.program_generation(0x60FC))
        if not self.predicate(0x7B48, self.r['cf'], 0, space, address, 7, generation, 0x5FCA):
            self.load_shift(0x7B4A, 0x7BA6, 0x7B4E)
        self.store_carry(0x7B4F, 0x0227, 0)
        self.latch_generation = self.state['generations']['0227']
        self.linear(0x7B52)

    def select_bit_two(self):
        if not self.test_r0(0x5FCE, 0x5FD1):
            self.load_shift(0x5FD3, 0x60FD, 0x5FD7)
            self.linear(0x5FD8)
        else:
            self.select_zero_r0_bit_two()
        self.store_carry(0x5FE7, 0x0216, 2)

    def select_zero_r0_bit_two(self):
        self.linear(0x5FDA)
        self.set_carry(0x7B55, 1)
        self.load_program(0x7B56, 0x7BA4)
        if not self.zero_predicate(0x7B5A, 0x7BA4, 0x7B56):
            self.set_carry(0x7B5C, 0)
            self.load_program(0x7B5D, 0x60F2)
            if not self.zero_predicate(0x7B61, 0x60F2, 0x7B5D):
                self.set_carry(0x7B63, 1)
                self.load_program(0x7B64, 0x7BA5)
                if not self.zero_predicate(0x7B68, 0x7BA5, 0x7B64):
                    self.linear(0x7B6A)
                    self.load_data(0x5FE1, 0x020A)
                    self.shift(0x5FE2, 0x5FE3)
                    self.xor_pswh(0x5FE4)
                    return
        self.linear(0x7B6D)

    def select_bit_zero_and_six(self):
        if self.test_r0(0x5FEA, 0x5FED):
            self.linear(0x5FF6)
            self.set_carry(0x7B70, 1)
            self.load_program(0x7B71, 0x7BA5)
            if self.zero_predicate(0x7B75, 0x7BA5, 0x7B71):
                self.linear(0x7B7D)
            else:
                self.load_data(0x7B77, 0x020A)
                self.shift(0x7B78, 0x7B79)
                self.linear(0x7B7A)
                self.xor_pswh(0x5FF9)
        else:
            self.load_shift(0x5FEF, 0x60FE, 0x5FF3)
            self.linear(0x5FF4)
        self.linear(0x5FFC)
        self.store_carry(0x7B80, 0x0216, 0)
        self.load_shift(0x7B83, 0x60E8, 0x7B87)
        self.load_program(0x7B88, 0x60F3)
        if not self.zero_predicate(0x7B8C, 0x60F3, 0x7B88):
            self.load_carry(0x7B8E, 0x0216, 0)
            self.xor_pswh(0x7B91)
        self.store_carry(0x7B94, 0x0216, 6)
        self.linear(0x7B97)

    def propagate_f0(self):
        if self.test_r0(0x5FFF, 0x6002):
            self.load_carry(0x600B, 0x0216, 2)
            self.load_program(0x600E, 0x60F2)
            if not self.zero_predicate(0x6012, 0x60F2, 0x600E):
                self.load_data(0x6014, 0x0209)
                self.shift(0x6015)
                self.xor_pswh(0x6016)
        else:
            self.load_shift(0x6004, 0x60FF, 0x6008)
            self.linear(0x6009)
        self.store_f0(0x6019)
        direct = self.test_r0(0x601B, 0x601E)
        if not direct:
            self.load_program(0x6020, 0x60EA)
        if direct or not self.zero_predicate(0x6024, 0x60EA, 0x6020):
            self.load_shift(0x6026, 0x60E9, 0x602A)
            self.linear(0x602B)
        else:
            self.store_f0(0x602D, clear=True)
            self.load_data(0x602F, 0x0209)
            self.shift(0x6030)
            self.xor_pswh(0x6031)
        self.store_carry(0x6034, 0x0227, 4)
        self.load_f0(0x6037)
        self.store_carry(0x6039, 0x0217, 6)

    def final_selectors(self):
        if self.test_r0(0x603C, 0x603F):
            self.set_carry(0x6048, 0)
            self.load_program(0x6049, 0x60F2)
            if not self.zero_predicate(0x604D, 0x60F2, 0x6049):
                self.load_data(0x604F, 0x0209)
                self.shift(0x6050)
        else:
            self.load_shift(0x6041, 0x6100, 0x6045)
            self.linear(0x6046)
        self.store_carry(0x6051, 0x0216, 5)
        if self.test_r0(0x6054, 0x6057):
            self.load_data(0x6060, 0x0209)
            self.shift(0x6061, 0x6062)
        else:
            self.load_shift(0x6059, 0x6101, 0x605D)
            self.linear(0x605E)
        self.store_f0(0x6063)
        if self.test_r0(0x6065, 0x6068):
            self.set_carry(0x6071, 0)
            self.load_program(0x6072, 0x60F3)
            if not self.zero_predicate(0x6076, 0x60F3, 0x6072):
                self.set_carry(0x6078, 1)
                self.linear(0x6079, 0x607A)
        else:
            self.load_shift(0x606A, 0x6102, 0x606E)
            self.linear(0x606F)
        self.store_carry(0x607B, 0x0227, 3)
        if self.test_r0(0x607E, 0x6081):
            self.load_f0(0x608A)
        else:
            self.load_shift(0x6083, 0x6103, 0x6087)
            self.linear(0x6088)
        self.linear(0x608C)
        latch = self.read_bit(0x7B9A, 0x0227, 0)
        if not self.predicate(0x7B9A, latch, 0, 'DATA', 0x0227, 0, self.latch_generation, 0x7B4F):
            self.set_carry(0x7B9D, 1)
        self.store_carry(0x7B9E, 0x0227, 2)
        self.linear(0x7BA1)


def corridor_from_prefix(prefix_query, prefix, program, source_binding):
    """Compose with a trusted return from the frozen M2cv From5F45 model."""
    effects = Corridor(prefix_query, prefix, program)
    if (prefix['status'], prefix['boundary']) != ('CompleteConditional', ENTRY):
        return effects.result(prefix['status'], prefix['reason'], prefix['boundary'], prefix['outcome'])
    try:
        effects.prepare(source_binding)
        effects.entry_select()
        effects.load_local_r2()
        effects.latch_selector()
        effects.select_bit_two()
        effects.select_bit_zero_and_six()
        effects.propagate_f0()
        effects.final_selectors()
        return effects.finish('ModeMiddleCorridorPreparedSuffix', STOP)
    except Boundary as stopped:
        return effects.result(stopped.status, stopped.reason, stopped.pc)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def mode_middle_corridor(query):
    shape(query, ('inputClass', 'prefixQuery', 'prefix', 'program', 'sourceBinding'),
          'ClosedModeMiddleCorridorQueryRequired')
    input_class(query['inputClass'])
    prefix_query = query['prefixQuery']
    shape(prefix_query, ('inputClass', 'callerPc', 'snapshot', 'entry', 'entryEstablished', 'program'),
          'ClosedModePrefixQueryRequired')
    need(prefix_query['entry'] == 'From5F45' and prefix_query['inputClass'] == query['inputClass'],
         'MatchingFrom5f45PrefixRequired')
    need(type(query['prefix']) is dict, 'FrozenPrefixOutputRequired')
    need(label(query['sourceBinding']), 'TypedCorridorSourceBindingRequired')
    program = query['program']
    validate_program(program)
    prefix = mode_enclosing_caller(prefix_query)
    if _canonical(query['prefix']) != _canonical(prefix):
        effects = Corridor(prefix_query, prefix, program)
        return effects.result('OutsideVerifiedScope', 'FrozenPrefixOutputMismatch', ENTRY)
    return corridor_from_prefix(prefix_query, prefix, program, query['sourceBinding'])
