"""Independent source equations and immutable M2cv reference composition."""

from copy import deepcopy

from enclosing_caller_return import reference_oracle as accepted
from native_data0217_011f_bridge.helper_cfg import NODE_ROWS
from payload_consumer_tail.reference_oracle import _bits, _memory_bits, _zero, canonical
from post_consumer_continuation.reference_oracle import _domain
from tx_ack_configuration_provenance.reference_oracle import _consensus, _known, _values

from .corpus import MIDDLE_PROGRAM, MIDDLE_PROOF, cases


# The accepted graph supplies instruction boundaries. The operand groups below
# are transcribed separately from the authenticated retained listing.
_NODES = {pc: (form, length, successors) for pc, form, length, successors in NODE_ROWS}


def _reachable():
    seen = set()
    remaining = [0x7DF5]
    while remaining:
        pc = remaining.pop()
        if pc == 0x608F or pc in seen:
            continue
        seen.add(pc)
        remaining.extend(_NODES[pc][2])
    return tuple(sorted(seen))


CORRIDOR_SCOPE = _reachable()
PROGRAM_AT = {
    0x5FA0: 0x60EA, 0x5FB4: 0x60EA, 0x5FC6: 0x60FC, 0x5FD3: 0x60FD,
    0x5FEF: 0x60FE, 0x6004: 0x60FF, 0x600E: 0x60F2, 0x6020: 0x60EA,
    0x6026: 0x60E9, 0x6041: 0x6100, 0x6049: 0x60F2, 0x6059: 0x6101,
    0x606A: 0x6102, 0x6072: 0x60F3, 0x6083: 0x6103, 0x7B4A: 0x7BA6,
    0x7B56: 0x7BA4, 0x7B5D: 0x60F2, 0x7B64: 0x7BA5, 0x7B71: 0x7BA5,
    0x7B83: 0x60E8, 0x7B88: 0x60F3, 0x7DFA: 0x7E02,
}
LOCAL_LOAD = {0x5FA6: 0x0209, 0x5FC0: 0x020A, 0x5FE1: 0x020A,
              0x6014: 0x0209, 0x602F: 0x0209, 0x604F: 0x0209,
              0x6060: 0x0209, 0x7B77: 0x020A}
CARRY_DESTINATIONS = {
    0x5FAC: (0x0227, 5), 0x5FE7: (0x0216, 2), 0x6034: (0x0227, 4),
    0x6039: (0x0217, 6), 0x6051: (0x0216, 5), 0x607B: (0x0227, 3),
    0x7B45: (0x0216, 3), 0x7B4F: (0x0227, 0), 0x7B80: (0x0216, 0),
    0x7B94: (0x0216, 6), 0x7B9E: (0x0227, 2),
}
CARRY_SOURCES = {0x600B: (0x0216, 2), 0x7B8E: (0x0216, 0)}
PSW_BITS = (3, 4, 5, 6, 7, 9, 10, 11)


def _other_psw(registers):
    value = registers['otherPsw']
    return {} if value is None else {str(bit): (value >> bit) & 1 for bit in PSW_BITS}


def _expanded_child(value, held):
    """Keep a child result's exact slots and fill only adapter-owned state."""
    from mode_caller_continuity.reference_oracle import _expand

    projected = _expand(value, held)
    projected['otherPswKnownBits'] = deepcopy(value.get('otherPswKnownBits',
        _other_psw(value['registers']) if value['registers']['otherPsw'] is not None
        else held['otherPswKnownBits']))
    return projected


class Reference(accepted.Reference):
    def __init__(self, snapshot, procedure, scope, specific=()):
        super().__init__(snapshot, procedure, scope, specific)
        self.state['memory']['020A'] = None
        self.state['generations']['020A'] = None
        self.state['otherPswKnownBits'] = _other_psw(self.registers)

    def current(self, entry=None):
        snapshot = super().current(entry)
        snapshot['memory'].pop('020A')
        snapshot['generations'].pop('020A')
        snapshot['knownBits'] = {key: bit for key, bit in snapshot['knownBits'].items()
                                 if not key.startswith('020A.')}
        snapshot.pop('otherPswKnownBits')
        return snapshot

    def step(self, *args, **kwargs):
        super().step(*args, **kwargs)
        self.steps[-1]['afterOtherPswKnownBits'] = deepcopy(self.state['otherPswKnownBits'])

    def absorb(self, child):
        held, step_start, event_start = deepcopy(self.state), len(self.steps), len(self.intermediate)
        super().absorb(child)
        self.state = _expanded_child(child['state'], held)
        for entry, original in zip(self.intermediate[event_start:], child['intermediateStates']):
            entry['state'] = _expanded_child(original['state'], held)
        for entry, original in zip(self.steps[step_start:], child['steps']):
            after = original['afterRegisters']
            entry['afterOtherPswKnownBits'] = deepcopy(original.get(
                'afterOtherPswKnownBits',
                _other_psw(after) if after['otherPsw'] is not None else held['otherPswKnownBits']))

    def set_f0(self, value):
        bits = self.state['otherPswKnownBits']
        if value is None:
            bits.pop('4', None)
        else:
            bits['4'] = value
        self.registers['otherPsw'] = (
            sum(bits[str(bit)] << bit for bit in PSW_BITS) if len(bits) == len(PSW_BITS) else None)


def _data_store(r, pc, address, possibilities, kind, source):
    bits = _known(possibilities)
    raw = _consensus(possibilities)
    partial = {f'{address:04X}.{key}': bit for key, bit in bits.items()} if raw is None else None
    r.write(pc, address, [raw], kind, source, partial=partial)


def _data_load(r, pc, address, pointer=False):
    if pointer:
        r.pointer_read(pc)
    r.read(pc, address)
    bits = _memory_bits(r.state, address)
    r.register_byte('al', bits)
    r.registers.update(dd=0, zf=_zero(bits, 8))


def _shift_accumulator(r):
    possibilities = _values(r.register_byte_bits('al'))
    r.registers['cf'] = _consensus(value >> 7 for value in possibilities)
    r.register_byte('al', _known((value * 2) % 256 for value in possibilities))


def _program_read(r, pc, address, row):
    slot = row['slot']
    r.reads.append({'pc': pc, 'space': 'PROGRAM', 'address': address, 'widthBits': 8,
        'value': slot['value'], 'bytes': [slot['value']],
        'knownBits': {f'{address:04X}.{key}': bit for key, bit in slot['knownBits'].items()},
        'generations': [slot['generation']], 'accessRole': 'BoundSymbolicProgramOperand',
        'stage': r.name, 'sourceBinding': row['sourceBinding'], 'valueClass': row['valueClass']})
    bits = _known(_domain(slot))
    r.register_byte('al', bits)
    r.registers['zf'] = _zero(bits, 8)


def _carry_store(r, pc, address, bit):
    raw = r.read(pc, address)[0]
    knowledge = _memory_bits(r.state, address)
    cf = r.registers['cf']
    after = None if raw is None or cf is None else (raw & ~(1 << bit)) | (cf << bit)
    knowledge.pop(bit, None)
    if cf is not None:
        knowledge[bit] = cf
    partial = {f'{address:04X}.{key}': value for key, value in knowledge.items()} if after is None else None
    r.write(pc, address, [after], 'RMW', f'CarryBitMove:{bit}', partial=partial)


def _flags(r):
    return {name: r.registers[name] for name in ('cf', 'zf', 'hc')}


def _pack(bits):
    return sum(bits[i] << i for i in range(8)) if len(bits) == 8 else None


def _psw_knowledge(r, address):
    regs, other = r.registers, r.state['otherPswKnownBits']
    if address == 4:
        known = {int(bit): value for bit, value in other.items() if int(bit) < 8}
        if regs['scb'] is not None:
            known.update(_bits(regs['scb'], 3))
    else:
        known = {int(bit) - 8: value for bit, value in other.items() if int(bit) >= 8}
        for bit, field in ((0, 'mie'), (4, 'dd'), (5, 'hc'), (6, 'zf'), (7, 'cf')):
            if regs[field] is not None:
                known[bit] = regs[field]
    return known


def _psw_read(r, pc, address, generation):
    knowledge = _psw_knowledge(r, address)
    value = _pack(knowledge)
    r.reads.append({'pc': pc, 'space': 'REGISTER', 'address': address, 'widthBits': 8,
        'value': value, 'bytes': [value],
        'knownBits': {f'{address:04X}.{bit}': v for bit, v in knowledge.items()},
        'generations': [generation], 'accessRole': 'RegisterOperand', 'stage': r.name})
    return value


def _psw_store(r, pc, address, old, generation, kind, source):
    raw = _pack(_psw_knowledge(r, address))
    ordinal = len(r.journal) + 1
    label = f'ConditionalEffect:{r.name}:{pc:04X}:{ordinal}'
    r.journal.append({'ordinal': ordinal, 'stageOrdinal': ordinal, 'stage': r.name,
        'pc': pc, 'space': 'REGISTER', 'address': address, 'widthBits': 8,
        'before': old, 'after': raw, 'beforeBytes': [old], 'afterBytes': [raw],
        'kind': kind, 'sameValue': None if old is None or raw is None else old == raw,
        'beforeGeneration': [generation], 'afterGeneration': label,
        'valueSource': source, 'effectClass': 'ConditionalRomEffect'})
    r.intermediate.append({'afterOrdinal': ordinal, 'pc': pc, 'state': deepcopy(r.state),
                           'stage': r.name, 'stageOrdinal': ordinal})
    return label


def _psw_operation(r, pc, form, f0_generation):
    before = _flags(r)
    f0 = r.state['otherPswKnownBits'].get('4')
    if form == 'XORB PSWH, #N8':
        value = _psw_read(r, pc, 5, None)
        r.registers.update(cf=None, zf=None, hc=None)
        generation = _psw_store(r, pc, 5, value, None, 'RegisterXor', 'PSWH^80')
        kind = 'XorPswhUnknownFlags'
    else:
        value = _psw_read(r, pc, 4, f0_generation)
        if form == 'MB C, PSWL.4':
            r.registers['cf'] = f0
            generation, kind = f0_generation, 'LoadF0'
        elif form == 'RB PSWL.4':
            r.registers['zf'] = None if f0 is None else 1 - f0
            r.set_f0(0)
            generation = f0_generation = _psw_store(
                r, pc, 4, value, f0_generation, 'RegisterBitClear', 'BitClear:4')
            kind = 'ClearF0'
        elif form == 'MB PSWL.4, C':
            r.set_f0(r.registers['cf'])
            generation = f0_generation = _psw_store(
                r, pc, 4, value, f0_generation, 'RegisterBitMove', 'CarryBitMove:4')
            kind = 'StoreF0'
        else:
            raise ValueError('ReferenceUnreviewedPswOperation')
    trace = {'pc': pc, 'kind': kind, 'beforeFlags': before, 'afterFlags': _flags(r),
        'priorF0': f0, 'valueF0': r.state['otherPswKnownBits'].get('4'), 'generation': generation}
    return trace, f0_generation


def _r2_operation(r, pc, form):
    if form == 'MOVB r2, #N8':
        _data_store(r, pc, 0x020A, {0x80}, 'ImmediateStore', 'Literal')
        return
    r.read(pc, 0x020A)
    before = _values(_memory_bits(r.state, 0x020A))
    if form == 'SLLB r2':
        result = {(value << 1) & 255 for value in before}
        r.registers['cf'] = _consensus(value >> 7 for value in before)
        _data_store(r, pc, 0x020A, result, 'RMW', 'SLLB')
    elif form == 'RORB r2':
        carry = r.registers['cf']
        result = {(value >> 1) | (bit << 7) for value in before
                  for bit in ((0, 1) if carry is None else (carry,))}
        r.registers['cf'] = _consensus(value & 1 for value in before)
        _data_store(r, pc, 0x020A, result, 'RMW', 'RORB')
    else:
        raise ValueError('ReferenceUnreviewedR2Operation')


def _data_effect(r, pc, form):
    if pc in LOCAL_LOAD:
        _data_load(r, pc, LOCAL_LOAD[pc])
    elif pc == 0x5FB2:
        _data_load(r, pc, 0x03CF, pointer=True)
    elif pc == 0x5FB3:
        r.store_a(pc, 0x020A)
    elif pc == 0x5FA9:
        r.read(pc, 0x0209)
        result = {value & 0x80 for value in _values(_memory_bits(r.state, 0x0209))}
        r.registers['zf'] = _zero(_known(result), 8)
        _data_store(r, pc, 0x0209, result, 'RMW', 'ANDB:80')
    elif pc in CARRY_DESTINATIONS:
        _carry_store(r, pc, *CARRY_DESTINATIONS[pc])
    elif pc in CARRY_SOURCES:
        address, bit = CARRY_SOURCES[pc]
        r.read(pc, address)
        r.registers['cf'] = r.bit(address, bit)
    elif form in ('SLLB r2', 'RORB r2', 'MOVB r2, #N8'):
        _r2_operation(r, pc, form)
    else:
        raise ValueError(f'ReferenceUnreviewedDataEffect:{pc:04X}')


def _check_middle_query(query, compose=False):
    fields = 'inputClass prefixQuery program sourceBinding'
    accepted._closed(query, fields if compose else fields + ' prefix')
    accepted._input_class(query['inputClass'])
    accepted._closed(query['prefixQuery'], 'inputClass callerPc snapshot entry entryEstablished program')
    if (query['prefixQuery']['entry'] != 'From5F45'
            or query['inputClass'] != query['prefixQuery']['inputClass']
            or query['sourceBinding'] is not None and type(query['sourceBinding']) is not str):
        raise ValueError('ReferenceQualifiedMiddleQuery')
    program = query['program']
    allowed = {f'{address:04X}' for address in (*MIDDLE_PROGRAM, 0x60FB)}
    if type(program) is not dict or program.keys() - allowed:
        raise ValueError('ReferenceMiddleProgramShape')
    for row in program.values():
        accepted._program_row(row)


def _program_refusal(row, address):
    if row is None or row['sourceBinding'] is None:
        return 'ProgramTableSourceUnbound'
    if row['sourceBinding'] != MIDDLE_PROOF:
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


def _origin(space, address, bit, generation, pc):
    return {'sourceSpace': space, 'sourceAddress': address, 'sourceBit': bit,
            'sourceGeneration': generation, 'sourcePc': pc}


def _mode_region(r, query, r0_lineage):
    """Apply a finite set of reviewed source equations, with no dynamic decode."""
    program = query['program']
    zf_origin = _origin('PROGRAM', 0x60FB, None, r0_lineage['programGeneration'], 0x5F99)
    pswh_trace, correlations = [], []
    f0_generation, latch_generation = None, None
    pc = 0x7DF5
    while pc != 0x608F:
        form, _, successors = _NODES[pc]
        if form in ('JEQ rel8', 'JNE rel8', 'JGE rel8', 'JBR off N8.0, rel8'):
            if form == 'JBR off N8.0, rel8':
                r.read(pc, 0x0227)
                value = r.bit(0x0227, 0)
                origin = _origin('DATA', 0x0227, 0, latch_generation, 0x7B4F)
            elif form == 'JGE rel8':
                value = r.registers['cf']
                if _zero(_memory_bits(r.state, 0x0208), 8) == 1:
                    origin = _origin('DATA', 0x03CF, 7, r.state['generations']['03CF'], 0x5FCA)
                else:
                    origin = _origin('PROGRAM', 0x60FC, 7, program['60FC']['slot']['generation'], 0x5FCA)
            else:
                value = r.registers['zf']
                origin = zf_origin
            expected = int(form == 'JEQ rel8')
            taken = None if value is None else value == expected
            following = None if taken is None else successors[1] if taken else successors[0]
            correlations.append({'pc': pc, **origin, 'value': value, 'taken': taken})
            r.step(pc, following, 'Branch', taken)
            if following is None:
                return r.result(pc, status='IndeterminateBranch', reason='UnknownBranchPredicate'), correlations, pswh_trace
            pc = following
            continue

        successor, = successors
        if pc in PROGRAM_AT:
            address = PROGRAM_AT[pc]
            row = program.get(f'{address:04X}')
            refusal = _program_refusal(row, address)
            if refusal is not None:
                return r.outside(pc, refusal), correlations, pswh_trace
            _program_read(r, pc, address, row)
            zf_origin = _origin('PROGRAM', address, None, row['slot']['generation'], pc)
        elif form == 'CMPB r0, #N8':
            r.read(pc, 0x0208)
            r.registers.update(cf=0, zf=_zero(_memory_bits(r.state, 0x0208), 8))
            zf_origin = _origin('PROGRAM', 0x60FB, None, r0_lineage['programGeneration'], pc)
        elif form == 'SLLB A':
            _shift_accumulator(r)
        elif form == 'MOV DP, #N16':
            bank = r.registers['scb']
            if bank is None:
                return r.outside(pc, 'PointerBankNotEstablished'), correlations, pswh_trace
            r.write(pc, 0x84 + bank * 8, [0xCF, 3], 'PointingRegisterWrite', 'Literal')
        elif form in ('RC', 'SC'):
            r.registers['cf'] = int(form == 'SC')
        elif form in ('XORB PSWH, #N8', 'MB C, PSWL.4', 'RB PSWL.4', 'MB PSWL.4, C'):
            event, f0_generation = _psw_operation(r, pc, form, f0_generation)
            pswh_trace.append(event)
        elif form not in ('NOP', 'SJ rel8', 'J addr16'):
            _data_effect(r, pc, form)
            if pc == 0x7B4F:
                latch_generation = r.journal[-1]['afterGeneration']
        r.step(pc, successor, 'Jump' if form in ('SJ rel8', 'J addr16') else 'Linear')
        pc = successor
    return r.result(0x608F, 'ModeMiddleCorridorPreparedSuffix'), correlations, pswh_trace


def mode_middle_corridor(query):
    _check_middle_query(query)
    prefix_query = query['prefixQuery']
    prefix = accepted.mode_enclosing_caller(prefix_query)
    snapshot = {'inputClass': query['inputClass'], 'assumptions': prefix['assumptions'], **prefix['state']}
    r = Reference(snapshot, 'mode_middle_corridor', CORRIDOR_SCOPE,
                  ('ModeMiddleCorridorStaticOnly', 'NativeCallReturnUnestablished'))
    lineage, correlations, pswh_trace = None, [], []

    def result(value):
        return {**value, 'prefixResult': deepcopy(prefix), 'r0Lineage': deepcopy(lineage),
                'correlatedPredicates': correlations, 'pswhDataflow': pswh_trace}

    if canonical(prefix) != canonical(query['prefix']):
        return result(r.outside(0x7DF5, 'FrozenPrefixOutputMismatch'))
    if prefix['status'] != 'CompleteConditional' or prefix['boundary'] != 0x7DF5:
        return result(r.result(prefix['boundary'], prefix['outcome'], prefix['status'], prefix['reason']))
    refusal = r.admit(0x7DF5)
    if refusal is not None:
        return result(refusal)
    if query['sourceBinding'] is None:
        return result(r.outside(0x7DF5, 'MiddleCorridorSourceUnbound'))
    if query['sourceBinding'] != MIDDLE_PROOF:
        return result(r.outside(0x7DF5, 'MiddleCorridorSourceBindingMismatch'))
    if r.registers['dd'] != 0:
        return result(r.outside(0x7DF5, 'ModeMiddleCorridorDd0NotEstablished'))
    if r.registers['lrb'] != 0x41:
        return result(r.outside(0x7DF5, 'LocalBank0208NotEstablished'))

    producer = prefix_query['program']['60FB']['slot']
    if producer['generation'] is None:
        return result(r.outside(0x7DF5, 'RetainedProgram60FBGenerationUnbound'))
    duplicate = query['program'].get('60FB')
    if duplicate is not None and (_program_refusal(duplicate, 0x60FB)
                                  or canonical(duplicate['slot']) != canonical(producer)):
        return result(r.outside(0x7DF5, 'RetainedProgram60FBMismatch'))
    lineage = {'address': 0x0208, 'writerPc': 0x7DF4, 'generation': r.state['generations']['0208'],
               'programAddress': 0x60FB, 'programGeneration': producer['generation'],
               'retainedAtBoundary': True}
    output, correlations, pswh_trace = _mode_region(r, query, lineage)
    lineage['retainedAtBoundary'] = r.state['generations']['0208'] == lineage['generation']
    return result(output)


def mode_enclosing_continuation(query):
    _check_middle_query(query, compose=True)
    initial = query['prefixQuery']
    prefix = accepted.mode_enclosing_caller(initial)
    r = Reference(initial['snapshot'], 'mode_enclosing_continuation',
                  (*accepted.ENCLOSING_SCOPE, *CORRIDOR_SCOPE))
    boundaries = []
    correlations, lineage = [], None

    def add(stage, child):
        r.absorb(child)
        boundaries.append({'stage': stage, 'status': child['status'], 'boundary': child['boundary']})

    add('Prefix', prefix)
    final = prefix
    complete = False
    if prefix['status'] == 'CompleteConditional' and prefix['boundary'] == 0x7DF5:
        middle = mode_middle_corridor({**query, 'prefix': prefix})
        add('Middle', middle)
        correlations, lineage = middle['correlatedPredicates'], middle['r0Lineage']
        final = middle
        if middle['status'] == 'CompleteConditional' and middle['boundary'] == 0x608F:
            suffix_model = accepted.Reference(r.current(), 'mode_enclosing_suffix',
                                              (*accepted.SUFFIX_SCOPE, *accepted.TABLE_SCOPE))
            suffix = accepted._entry(suffix_model, 0x608F, True)
            if suffix is None:
                suffix = accepted._mode_suffix(suffix_model, initial['program'])
            suffix = {**suffix, 'entryVariant': 'At608F', 'callerContext': None}
            add('Suffix', suffix)
            final = suffix
            complete = suffix['status'] == 'CompleteConditional' and suffix['boundary'] == 0x60E4
    return {**r.result(final['boundary'], final['outcome'], final['status'], final['reason']),
            'stageBoundaries': boundaries, 'compositionEstablished': complete,
            'correlatedPredicates': deepcopy(correlations), 'r0Lineage': deepcopy(lineage)}


AUTHORITY = deepcopy(accepted.AUTHORITY)
OPERATIONS = {function.__name__: function for function in (mode_middle_corridor, mode_enclosing_continuation)}
SOURCE_IDENTITIES = {
    'base': '150ada6ed6fd66d9d8105f1ac74853b072824249',
    'modePrefix': accepted.SOURCE_IDENTITIES['mode'],
    'corridor': MIDDLE_PROOF,
    'dataflow': 'bd0dfc5e1719d6d974c35671582d5e5fe13bd60d3dec1a7a6ba6071ee6fd381f',
}


def evaluate(case):
    return OPERATIONS[case['operation']](deepcopy(case['input']))


def record(case):
    output = evaluate(case)
    envelope = accepted.record(case, output)
    regs = output['state'].get('registers')
    envelope.update(
        sourceIdentities=deepcopy(SOURCE_IDENTITIES),
        registerState=deepcopy(regs),
        flags=None if regs is None else {key: regs[key] for key in ('cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw')},
        programDependencies=[deepcopy(row) for row in output['reads'] if row['space'] == 'PROGRAM'],
        correlatedPredicates=deepcopy(output.get('correlatedPredicates', [])),
        sourceEdges=[{'from': row['pc'], 'to': row['next'],
                      'class': 'ConditionalSourcePath' if row['kind'] == 'Branch' else 'ConfirmedStaticCFG'}
                     for row in output['steps'] if row['next'] is not None],
    )
    for step, projected in zip(output['steps'], envelope['registerEffects']):
        projected['afterOtherPswKnownBits'] = deepcopy(step.get('afterOtherPswKnownBits'))
    return envelope


def canonical_records():
    for case in cases():
        yield canonical(record(case))
