"""Independent equations over reviewed sources and accepted M2cu reference functions."""

from copy import deepcopy

from mode_caller_continuity.corpus import (
    ADDRESSES as OLD_DATA, READBACK_KEYS as OLD_READBACKS, MODE_SITES, WRITER_SITES,
)
from mode_caller_continuity.reference_oracle import (
    Reference as AcceptedReference, _snapshot as accepted_snapshot,
    data03cb_indexed_writer as accepted_writer, mode_producer_extended as accepted_mode,
    data03cb_reaching_definitions as accepted_lineage,
)
from native_data0217_011f_bridge.helper_cfg import NODE_ROWS
from payload_consumer_tail.reference_oracle import (
    _bits, _generation, _input_class, _integer, _memory_bits, _zero, canonical,
)
from post_consumer_continuation.reference_oracle import _domain, _slot
from stbuf_stcon_transmit_source.reference_oracle import AUTHORITY as ACCEPTED_AUTHORITY
from tx_ack_configuration_provenance.reference_oracle import _known, _values, _consensus

from .corpus import (
    CALL_IDENTITIES, EXTRA_DATA, FRAME_PREMISES, FRAME_PROOF, INDEXED_PROOF, LINEAGE_PREMISES,
    MODE_PROOF, PROGRAM_ADDRESSES, cases,
)


AUTHORITY = {
    **ACCEPTED_AUTHORITY,
    'actualCpuExecutions': 0, 'actualCallExecution': None, 'actualReturnExecution': None,
    'actualFramePop': None, 'actualSavedPcObservation': None,
}
EXACT_BOUNDARIES = {
    0x5CB7: 'STOP_BEFORE_INDEXED_CONTINUATION_5CB7', 0x60E4: 'STOP_BEFORE_RT_60E4',
    0x5C89: 'STOP_BEFORE_TIMER_IE_PATH_5C89',
    0x5CCD: 'STOP_BEFORE_RT_5CCD', 0x2891: 'STOP_BEFORE_EXTERNAL_DATA_READ_2891',
    0x3FB5: 'STOP_BEFORE_BRK_3FB5', 0x3FF9: 'STOP_BEFORE_IE_WRITE_3FF9',
    0x5CD2: 'STOP_BEFORE_BRK_5CD2', 0x2995: 'STOP_BEFORE_STBUF_2995',
}
FRAME_SCOPE = tuple(sorted((*CALL_IDENTITIES, 0x5CCD, 0x60E4)))
INDEXED_SCOPE = tuple(sorted((*WRITER_SITES, 0x5C86, 0x5CA0, 0x5CA3, 0x5CCE)))
TABLE_SCOPE = tuple(sorted((*MODE_SITES, 0x60C2, 0x60C6, 0x60C7)))
PREFIX_WRITES = (
    (0x5F46, 0x60E6, 0x5F4A, 0x5F4B, 0x216, 4, 0x5F4E),
    (0x5F4E, 0x60E7, 0x5F52, 0x5F53, 0x227, 6, 0x5F56),
    (0x5F5E, 0x60EB, 0x5F62, 0x5F63, 0x219, 3, 0x5F66),
    (0x5F66, 0x60EC, 0x5F6A, 0x5F6B, 0x217, 3, 0x5F6E),
    (0x5F6E, 0x60ED, 0x5F72, 0x5F73, 0x227, 7, 0x5F76),
    (0x5F76, 0x60EE, 0x5F7A, 0x5F7B, 0x216, 1, 0x5F7E),
    (0x5F7E, 0x60F0, 0x5F82, 0x5F83, 0x216, 7, 0x5F86),
    (0x5F8B, 0x60F1, 0x5F8F, 0x5F90, 0x227, 1, 0x5F93),
)
PREFIX_SCOPE = tuple(sorted({site for load, _, shift, store, *_ in PREFIX_WRITES
                            for site in (load, shift, store)}
                           | {0x5F45, 0x5F56, 0x5F86, 0x5F89, 0x5F93, 0x5F96, 0x5F97,
                              0x5F98, 0x5F99, 0x5F9D, 0x7DF4}))
SUFFIX_SCOPE = (0x608F, 0x6092, 0x6094, 0x6098, 0x6099, 0x609B, 0x609C, 0x609F,
                0x60A3, *range(0x60A5, 0x60B4), 0x60B4, 0x60B7, 0x60BA)
ENCLOSING_SCOPE = tuple(sorted(set((*PREFIX_SCOPE, *SUFFIX_SCOPE, *TABLE_SCOPE))))
LINEAGE_SCOPE = (0x276A, 0x276D, 0x27D0, 0x2B64, 0x4069, 0x5C86, 0x5CB4,
                 0x5CB7, 0x5CCD, 0x5F45, 0x60CC, 0x60E4, 0x2869)


def _closed(obj, fields):
    if type(obj) is not dict or obj.keys() != set(fields.split()):
        raise ValueError('ReferenceClosedFields')


def _optional_bool(value):
    if value is not None and type(value) is not bool:
        raise ValueError('ReferenceNullableBool')


def _enum(value, names):
    if type(value) is not str or value not in names:
        raise ValueError('ReferenceEnum')


def _stop(pc):
    return None if pc is None else EXACT_BOUNDARIES.get(pc, f'STOP_BEFORE_PC_{pc:04X}')


def _formal(name, query, scope, status, reason, boundary, state, *,
            missing=(), children=(), edges=(), frames=()):
    return {
        'procedure': name, 'inputClass': query['inputClass'], 'sourceScope': sorted(set(scope)),
        'status': status, 'reason': reason, 'boundary': boundary, 'outcome': None,
        'exactStopBoundary': _stop(boundary), 'state': deepcopy(state),
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [],
        'inheritedResults': deepcopy(list(children)), 'sourceEdges': deepcopy(list(edges)),
        'frameObligations': deepcopy(list(frames)), 'unresolvedConstraints': list(missing),
        'effectClass': 'StaticFormalSourceObligation', 'stopBoundary': 'STOP_BEFORE_STBUF_2995',
        **AUTHORITY,
    }


def _m2cu_projection(snapshot):
    copy = deepcopy(snapshot)
    for field in ('memory', 'generations'):
        copy[field] = {k: copy[field][k] for k in OLD_DATA}
    copy['knownBits'] = {k: v for k, v in copy['knownBits'].items() if k[:4] in OLD_DATA}
    copy['sfrReadbacks'] = {k: copy['sfrReadbacks'][k] for k in OLD_READBACKS}
    return copy


def _check_snapshot(snapshot):
    _closed(snapshot, 'inputClass assumptions memory generations knownBits registers '
            'registerKnownBits configurationIntents sfrReadbacks')
    addresses = set(OLD_DATA).union(EXTRA_DATA)
    for field in ('memory', 'generations'):
        if type(snapshot[field]) is not dict or snapshot[field].keys() != addresses:
            raise ValueError('ReferenceEnclosingDataShape')
    if (not all(_integer(v, 255) for v in snapshot['memory'].values())
            or not all(_generation(v) for v in snapshot['generations'].values())):
        raise ValueError('ReferenceEnclosingDataType')
    if type(snapshot['knownBits']) is not dict:
        raise ValueError('ReferenceEnclosingBits')
    for key, bit in snapshot['knownBits'].items():
        if (type(key) is not str or len(key) != 6 or key[:4] not in addresses
                or key[4] != '.' or key[5] not in '01234567'
                or type(bit) is not int or bit not in (0, 1)):
            raise ValueError('ReferenceEnclosingBitShape')
        raw = snapshot['memory'][key[:4]]
        if raw is not None and (raw >> int(key[5])) & 1 != bit:
            raise ValueError('ReferenceEnclosingBitConflict')
    if (type(snapshot['sfrReadbacks']) is not dict
            or snapshot['sfrReadbacks'].keys() != set(OLD_READBACKS).union({'0019'})):
        raise ValueError('ReferenceEnclosingReadbackShape')
    _slot(snapshot['sfrReadbacks']['0019'])
    return accepted_snapshot(_m2cu_projection(snapshot))


class Reference(AcceptedReference):
    """Carry the extended state through independently calculated effects."""

    def __init__(self, snapshot, procedure, scope, specific=()):
        checked = _check_snapshot(snapshot)
        super().__init__(checked, procedure, sorted(set(scope)), specific)
        self.original = deepcopy(snapshot)
        for field in ('memory', 'generations', 'knownBits', 'sfrReadbacks'):
            self.state[field] = deepcopy(snapshot[field])

    def result(self, boundary, outcome=None, status='CompleteConditional',
               reason='VerifiedSelectedSourcePath'):
        return {**super().result(boundary, outcome, status, reason),
                **AUTHORITY, 'exactStopBoundary': _stop(boundary)}

    def prior_snapshot(self, entry=None):
        value = _m2cu_projection(self.current())
        if entry is not None:
            value['entry'] = entry
        return value

    def clear_irqh_intent(self):
        slot = self.state['sfrReadbacks']['0019']
        values = self.symbolic_read(0x5CA0, 0x19)
        old_bit = _consensus((value >> 4) & 1 for value in values)
        new = _consensus(value & 0xEF for value in values)
        self.registers['zf'] = None if old_bit is None else 1 - old_bit
        raw, ordinal = slot['value'], len(self.journal) + 1
        remaining = {'4': 0, **{k: v for k, v in slot['knownBits'].items() if k != '4'}}
        event = {
            'ordinal': ordinal, 'stageOrdinal': ordinal, 'stage': self.name,
            'pc': 0x5CA0, 'space': 'SOFTWARE_SFR_INTENT', 'address': 0x19, 'widthBits': 8,
            'before': raw, 'after': new, 'beforeBytes': [raw], 'afterBytes': [new],
            'kind': 'BitClear', 'sameDeclaredValue': None if raw is None or new is None else raw == new,
            'beforeGeneration': [slot['generation']],
            'afterGeneration': f'ConditionalEffect:{self.name}:5CA0:{ordinal}',
            'valueSource': 'SuppliedIRQHReadback', 'effectClass': 'StaticRomSfrWriteIntent_NotPerformedIO',
            'selectedBit': 4, 'priorBit': old_bit, 'knownBitsBefore': deepcopy(slot['knownBits']),
            'knownBitsAfter': remaining if new is None else {}, 'actualHardwareObservation': None,
        }
        self.journal.append(event)
        self.intermediate.append({'afterOrdinal': ordinal, 'pc': 0x5CA0,
            'state': deepcopy(self.state), 'stage': self.name, 'stageOrdinal': ordinal})
        return deepcopy(event)


def indexed_acquisition_caller(query):
    _closed(query, 'inputClass callerPc snapshot entryEstablished')
    _input_class(query['inputClass'])
    _optional_bool(query['entryEstablished'])
    pc = query['callerPc']
    if not _integer(pc, 65535):
        raise ValueError('ReferenceIndexedCallerPc')
    snapshot = query['snapshot']
    r = Reference(snapshot, 'indexed_acquisition_caller', INDEXED_SCOPE, (
        'ConditionalCalleeEntryOnly', 'IrqhClearIsSoftwareIntentOnly',
        'IndexedReturnFrameUnresolved', 'PostIndexedSuffixUnreviewed',
    ))
    if query['inputClass'] != snapshot['inputClass']:
        raise ValueError('ReferenceIndexedInputClass')
    caller = None
    intent = None
    selected = None
    establishes_writer = False

    def with_metadata(result):
        return {**result, 'caller': caller, 'irqhClearIntent': intent,
                'selectedIndex': selected, 'conditionalData03cbWriterEstablished': establishes_writer}

    if pc not in (0x276A, 0x2B64):
        return with_metadata(r.outside(None, 'UnreviewedIndexedCaller'))
    caller = {'callerPc': pc, 'calleeTarget': 0x5C86, 'returnSiteCandidate': pc + 3,
              'listedEntryDD': int(pc == 0x276A)}
    if query['entryEstablished'] is not True:
        return with_metadata(r.outside(0x5C86, 'IndexedCalleeEntryNotEstablished'))
    rejected = r.admit(0x5C86)
    if rejected is not None:
        return with_metadata(rejected)
    lrb = r.registers['lrb']
    if lrb is None or lrb & 0x1FE0 != 0x40:
        return with_metadata(r.outside(0x5C86, 'AcquisitionPage0200NotEstablished'))
    r.read(0x5C86, 0x230)
    bit = r.bit(0x230, 3)
    rejected = r.branch_stop(0x5C86, None if bit is None else 1 - bit, 0x5CA0, 0x5C89)
    if rejected is not None:
        return with_metadata(rejected)
    if bit:
        return with_metadata(r.outside(0x5C89, 'TimerAndIePathUnestablished'))
    intent = r.clear_irqh_intent()
    r.step(0x5CA0, 0x5CA3)
    zero = r.registers['zf']
    rejected = r.branch_stop(0x5CA3, zero, 0x5CCE, 0x5CA5)
    if rejected is not None:
        return with_metadata(rejected)
    if zero:
        r.write(0x5CCE, 0x00F5, [0x4A], 'ImmediateStore', 'Literal')
        r.step(0x5CCE, 0x5CD2)
        return with_metadata(r.result(0x5CD2, 'IndexedAcquisitionFaultMarkerStored'))
    child = accepted_writer(r.prior_snapshot())
    r.absorb(child)
    selected = child['selectedIndex']
    establishes_writer = child['conditionalData03cbWriterEstablished']
    return with_metadata(r.result(child['boundary'], child['outcome'], child['status'], child['reason']))


def _alias(address, target):
    named = {0: 'SspSelfAlias', 2: 'LrbAlias', 4: 'PswAlias', 6: 'AccumulatorAlias',
             0x0208: 'LocalR0Alias', 0x0356: 'ModeBitAlias', 0x03CA: 'Data03cbAlias'}
    if address is None:
        return None
    if address in named:
        return named[address]
    if address < 0x0080:
        return 'OtherSfrOrReserved'
    if address < 0x00C0:
        return 'PointingBankAlias'
    if target == 0x5F45 and address == 0x0382:
        return 'ModeWordAlias'
    if target == 0x5F45 and address in (0x020A, 0x0216, 0x0218, 0x0226):
        return 'ModeCalleeDataAlias'
    if target == 0x5C86 and address == 0x0230:
        return 'IndexedGuardAlias'
    if target == 0x5C86 and 0x03C6 <= address <= 0x03D4:
        return 'IndexedCalleeDataAlias'
    return 'OrdinaryDataCandidate'


def call_return_obligations(query):
    _closed(query, 'inputClass sourceBinding callerPc declaredTarget returnPc incomingSsp '
            'sspBeforeReturn frame premises claim')
    _input_class(query['inputClass'])
    _enum(query['claim'], ('ConditionalOnly', 'ActualNativeReturn', 'Execute', 'HostSelectedReturn'))
    binding = query['sourceBinding']
    if binding is not None and type(binding) is not str:
        raise ValueError('ReferenceFrameBindingType')
    for field in ('callerPc', 'declaredTarget', 'returnPc', 'incomingSsp', 'sspBeforeReturn'):
        if not _integer(query[field], 65535):
            raise ValueError('ReferenceFrameWordType')
    frame = query['frame']
    _closed(frame, 'kind address low high creatorPc generation')
    _enum(frame['kind'], ('NormalCall', 'Interrupt'))
    for field, maximum in (('address', 65535), ('creatorPc', 65535), ('low', 255), ('high', 255)):
        if not _integer(frame[field], maximum):
            raise ValueError('ReferenceFrameSlotType')
    if not _generation(frame['generation']):
        raise ValueError('ReferenceFrameGeneration')
    premises = query['premises']
    _closed(premises, ' '.join(FRAME_PREMISES))
    for premise in premises.values():
        _optional_bool(premise)

    caller = query['callerPc']
    identity = CALL_IDENTITIES.get(caller)
    target, candidate, rt = identity if identity else (None, None, None)
    call = None if identity is None else dict(
        callerPc=caller, target=target, length=3, returnCandidatePc=candidate, returnSitePc=rt)
    declared, returned = query['declaredTarget'], query['returnPc']
    matched = identity is not None and binding == FRAME_PROOF and (declared, returned) == (target, rt)
    incoming, before_rt = query['incomingSsp'], query['sspBeforeReturn']
    effective = after_call = read_at = after_rt = saved = None
    edges, frames = [], []
    if matched:
        if incoming is not None:
            effective = incoming // 2 * 2
            after_call = (incoming + 65534) % 65536
        if before_rt is not None:
            after_rt = (before_rt + 2) % 65536
            read_at = after_rt // 2 * 2
        if None not in (frame['low'], frame['high']):
            saved = frame['low'] + 256 * frame['high']
        edges.append({'from': caller, 'to': target, 'class': 'ConfirmedCallTarget'})
        frames = [
            {'kind': 'FormalCalWordStore', 'pc': caller, 'address': effective,
             'widthBits': 16, 'value': candidate},
            {'kind': 'FormalRtWordRead', 'pc': rt, 'address': read_at,
             'widthBits': 16, 'value': saved},
        ]
    alias = _alias(effective, target)
    missing = [key for key in FRAME_PREMISES if premises[key] is not True]
    refusal = [
        (query['claim'] != 'ConditionalOnly', 'OutsideVerifiedScope', 'NonConditionalFrameClaim'),
        (identity is None, 'OutsideVerifiedScope', 'UnreviewedCallSite'),
        (binding is None, 'IndeterminateObligation', 'CallSourceBindingMissing'),
        (binding != FRAME_PROOF, 'OutsideVerifiedScope', 'CallSourceBindingMismatch'),
        (None in (declared, returned), 'IndeterminateObligation', 'CallReturnSiteUnspecified'),
        (not matched, 'OutsideVerifiedScope', 'CallReturnSourceMismatch'),
        (frame['kind'] != 'NormalCall', 'OutsideVerifiedScope', 'InterruptFrameCannotReturnViaRt'),
        (None in (incoming, before_rt), 'IndeterminateObligation', 'StackPointerUnknown'),
        (before_rt != after_call, 'OutsideVerifiedScope', 'UnbalancedStackPointer'),
        (alias != 'OrdinaryDataCandidate', 'OutsideVerifiedScope', 'FrameAliasRequiresIndependentProof'),
        (bool(missing), 'IndeterminateObligation', 'FramePremisesNotEstablished'),
        (any(value is None for value in frame.values()), 'IndeterminateObligation', 'FrameContentsOrOwnerUnknown'),
        ((frame['address'], frame['creatorPc'], saved) != (effective, caller, candidate),
         'OutsideVerifiedScope', 'FrameDoesNotMatchCall'),
    ]
    status, reason = next(((s, why) for failed, s, why in refusal if failed),
                          ('CompleteConditional', 'HypotheticalMatchingFrame'))
    complete = status == 'CompleteConditional'
    constraints = (['ActualNativeFrameOwnershipUnestablished'] if complete else
                   missing if reason == 'FramePremisesNotEstablished' else [reason])
    state = {
        'call': call,
        'geometry': {'frameAddress': effective, 'sspAfterCall': after_call,
                     'returnReadAddress': read_at, 'sspAfterReturn': after_rt, 'savedPc': saved},
        'frame': frame, 'alias': alias, 'formalReturnedPc': candidate if complete else None,
        'nativeFrameOwnerEstablished': False, 'nativeReturnEstablished': False,
    }
    return _formal('call_return_obligations', query, FRAME_SCOPE, status, reason, rt, state,
                   missing=constraints, edges=edges, frames=frames)


def _program_row(row):
    if row is None:
        return
    _closed(row, 'space address widthBits index sourceBinding valueClass slot')
    _enum(row['space'], ('PROGRAM', 'DATA'))
    _enum(row['valueClass'], ('ConditionalSymbolic', 'InventedOnly', 'ClaimedOemByte'))
    if (not _integer(row['address'], 65535) or not _integer(row['index'], 65535)
            or type(row['widthBits']) is not int or row['widthBits'] not in (8, 16)
            or (row['sourceBinding'] is not None and type(row['sourceBinding']) is not str)):
        raise ValueError('ReferenceProgramOperandShape')
    _slot(row['slot'])


def _load_program(r, pc, address, successor, row):
    if row is None or row['sourceBinding'] is None:
        return r.outside(pc, 'ProgramTableSourceUnbound')
    if row['sourceBinding'] != MODE_PROOF:
        return r.outside(pc, 'ProgramTableSourceBindingMismatch')
    if (row['space'], row['widthBits'], row['address']) != ('PROGRAM', 8, address):
        return r.outside(pc, 'ProgramOperandSourceMismatch')
    if row['index'] is not None:
        return r.outside(pc, 'ProgramOperandIsNotIndexed')
    if row['valueClass'] == 'ClaimedOemByte':
        return r.outside(pc, 'OemProgramValueClaimNotAdmitted')
    slot = row['slot']
    raw = slot['value']
    bits = _known(_domain(slot))
    r.reads.append({
        'pc': pc, 'space': 'PROGRAM', 'address': address, 'widthBits': 8,
        'value': raw, 'bytes': [raw],
        'knownBits': {f'{address:04X}.{k}': v for k, v in slot['knownBits'].items()},
        'generations': [slot['generation']], 'accessRole': 'BoundSymbolicProgramOperand',
        'stage': r.name, 'sourceBinding': row['sourceBinding'], 'valueClass': row['valueClass'],
    })
    r.register_byte('al', bits)
    r.registers['zf'] = _zero(bits, 8)
    r.step(pc, successor)
    return None


def _sllb(r, pc, successor):
    if r.registers['dd'] != 0:
        return r.outside(pc, 'Dd0RequiredForAccumulatorByteShift')
    bits = r.register_byte_bits('al')
    r.registers['cf'] = bits.get(7)
    r.register_byte('al', {0: 0, **{bit + 1: value for bit, value in bits.items() if bit != 7}})
    r.step(pc, successor)
    return None


def _carry_write(r, pc, address, bit, successor, pointer=False):
    if pointer:
        r.pointer_read(pc)
    else:
        lrb = r.registers['lrb']
        if lrb is None or lrb & 0x1FE0 != 0x40:
            return r.outside(pc, 'ModePage0200NotEstablished')
    raw = r.read(pc, address)[0]
    carry = r.registers['cf']
    after = None if raw is None or carry is None else (raw & ~(1 << bit)) + (carry << bit)
    knowledge = _memory_bits(r.state, address)
    knowledge.pop(bit, None)
    if carry is not None:
        knowledge[bit] = carry
    partial = {f'{address:04X}.{k}': v for k, v in knowledge.items()} if after is None else None
    r.write(pc, address, [after], 'RMW', f'CarryBitMove:{bit}', partial=partial)
    r.step(pc, successor)
    return None


def _register_store(r, pc, address, successor):
    if r.registers['lrb'] != 0x41:
        return r.outside(pc, 'LocalBank0208NotEstablished')
    value = r.registers['al']
    partial = None if value is not None else {
        f'{address:04X}.{bit}': v for bit, v in r.register_byte_bits('al').items()}
    r.write(pc, address, [value], 'Store', 'AL', partial=partial)
    r.step(pc, successor)
    return None


def _mode_prefix(r, program):
    if r.original['assumptions']['ordinaryByteSemantics'] is not True:
        return r.outside(0x5F45, 'OrdinaryByteSemanticsNotEstablished')
    r.register_byte('al', _bits(0))
    r.registers.update(zf=1, dd=0)
    r.step(0x5F45, 0x5F46)
    for load, address, shift, store, destination, bit, successor in PREFIX_WRITES:
        if load == 0x5F5E:
            r.step(0x5F56, 0x5F5E, 'Jump')
        if load == 0x5F8B:
            rejected = r.pointer_write(0x5F86, 0x0356, 0x5F89)
            if rejected is not None:
                return rejected
            rejected = _carry_write(r, 0x5F89, 0x0356, 0, 0x5F8B, pointer=True)
            if rejected is not None:
                return rejected
        rejected = _load_program(r, load, address, shift, program.get(f'{address:04X}'))
        if rejected is not None:
            return rejected
        rejected = _sllb(r, shift, store)
        if rejected is not None:
            return rejected
        rejected = _carry_write(r, store, destination, bit, successor)
        if rejected is not None:
            return rejected
    rejected = r.pointer_write(0x5F93, 0x03C7, 0x5F96)
    if rejected is not None:
        return rejected
    if r.original['assumptions']['ordinaryByteSemantics'] is not True:
        return r.outside(0x5F96, 'OrdinaryByteSemanticsNotEstablished')
    r.pointer_read(0x5F96)
    r.read(0x5F96, 0x03C7)
    bits = _memory_bits(r.state, 0x03C7)
    r.register_byte('al', bits)
    r.registers.update(zf=_zero(bits, 8), dd=0)
    r.step(0x5F96, 0x5F97)
    rejected = _register_store(r, 0x5F97, 0x0209, 0x5F98)
    if rejected is not None:
        return rejected
    r.registers['cf'] = 0
    r.step(0x5F98, 0x5F99)
    rejected = _load_program(r, 0x5F99, 0x60FB, 0x5F9D, program.get('60FB'))
    if rejected is not None:
        return rejected
    r.step(0x5F9D, 0x7DF4, 'Jump')
    rejected = _register_store(r, 0x7DF4, 0x0208, 0x7DF5)
    return rejected if rejected is not None else r.result(0x7DF5, 'ModeEntryPrefixPreparedLocalR0')


def _mode_producer(r, program):
    first = accepted_mode(r.prior_snapshot('At60BD'))
    r.absorb(first)
    current = first
    if (first['status'], first['reason'], first['boundary']) == (
            'OutsideVerifiedScope', 'ProgramTableSourceNotAdmitted', 0x60C2):
        rejected = _load_program(r, 0x60C2, 0x6105, 0x60C6, program)
        if rejected is not None:
            return rejected
        rejected = _sllb(r, 0x60C6, 0x60C7)
        if rejected is not None:
            return rejected
        r.step(0x60C7, 0x60D2, 'Jump')
        current = accepted_mode(r.prior_snapshot('SymbolicCarryTail'))
        r.absorb(current)
    return r.result(current['boundary'], current['outcome'], current['status'], current['reason'])


def _mode_suffix(r, program):
    if r.registers['dd'] != 0:
        return r.outside(0x608F, 'ModeSuffixDd0NotEstablished')
    if r.registers['lrb'] != 0x41:
        return r.outside(0x608F, 'LocalBank0208NotEstablished')
    r.read(0x608F, 0x0208)
    r.compare(_values(_memory_bits(r.state, 0x0208)), 0)
    r.step(0x608F, 0x6092)
    zero = r.registers['zf']
    rejected = r.branch_stop(0x6092, zero, 0x609B, 0x6094)
    if rejected is not None:
        return rejected
    if not zero:
        rejected = _load_program(r, 0x6094, 0x6104, 0x6098, program.get('6104'))
        if rejected is not None:
            return rejected
        rejected = _sllb(r, 0x6098, 0x6099)
        if rejected is not None:
            return rejected
        r.step(0x6099, 0x60BA, 'Jump')
    else:
        r.registers['cf'] = 0
        r.step(0x609B, 0x609C)
        r.read(0x609C, 0x0217)
        bit = r.bit(0x0217, 6)
        rejected = r.branch_stop(0x609C, bit, 0x60BA, 0x609F)
        if rejected is not None:
            return rejected
        if not bit:
            rejected = _load_program(r, 0x609F, 0x6104, 0x60A3, program.get('6104'))
            if rejected is not None:
                return rejected
            loaded_zero = r.registers['zf']
            rejected = r.branch_stop(0x60A3, loaded_zero, 0x60BA, 0x60A5)
            if rejected is not None:
                return rejected
            if not loaded_zero:
                for pc in range(0x60A5, 0x60B4):
                    r.step(pc, pc + 1)
                rejected = r.pointer_write(0x60B4, 0x03CE, 0x60B7)
                if rejected is not None:
                    return rejected
                r.pointer_read(0x60B7)
                r.read(0x60B7, 0x03CE)
                r.compare(_values(_memory_bits(r.state, 0x03CE)), 0x9A)
                r.step(0x60B7, 0x60BA)
    rejected = _carry_write(r, 0x60BA, 0x0219, 4, 0x60BD)
    return rejected if rejected is not None else _mode_producer(r, program.get('6105'))


def _entry(r, pc, premise):
    if premise is not True:
        status = 'IndeterminateObligation' if premise is None else 'OutsideVerifiedScope'
        return r.result(pc, status=status, reason='DeclaredConditionalEntryNotEstablished')
    return r.admit(pc)


def _check_entry(query):
    _input_class(query['inputClass'])
    _optional_bool(query['entryEstablished'])
    if type(query['snapshot']) is not dict or query['snapshot'].get('inputClass') != query['inputClass']:
        raise ValueError('ReferenceEntryInputClass')


def mode_enclosing_caller(query):
    _closed(query, 'inputClass callerPc snapshot entry entryEstablished program')
    _check_entry(query)
    _enum(query['entry'], ('From5F45', 'At608F'))
    caller = query['callerPc']
    if not _integer(caller, 65535):
        raise ValueError('ReferenceModeCallerPc')
    program = query['program']
    if type(program) is not dict or not program.keys() <= {f'{address:04X}' for address in PROGRAM_ADDRESSES}:
        raise ValueError('ReferenceProgramMapShape')
    for row in program.values():
        _program_row(row)
    r = Reference(query['snapshot'], 'mode_enclosing_caller', ENCLOSING_SCOPE)
    entry = query['entry']
    first = 0x5F45 if entry == 'From5F45' else 0x608F
    context = None
    if entry == 'From5F45' and caller in (0x27D0, 0x4069):
        cold = caller == 0x27D0
        context = {'callerPc': caller, 'target': 0x5F45, 'length': 3, 'candidateReturn': caller + 3,
                   'listedIncomingDd': int(not cold), 'priorSourceBoundary': 0x27CE if cold else 0x4068,
                   'priorContext': 'ConditionalColdRoute' if cold else 'RequiresOwnVCAL3ReturnTo4069'}
    if entry == 'From5F45' and context is None:
        out = r.outside(first, 'UnreviewedModeCaller')
    elif entry == 'At608F' and caller is not None:
        out = r.outside(first, 'CallerHistoryNotEstablishedForDetachedEntry')
    else:
        out = _entry(r, first, query['entryEstablished'])
        if out is None:
            out = _mode_prefix(r, program) if entry == 'From5F45' else _mode_suffix(r, program)
    return {**out, 'entryVariant': entry, 'callerContext': context}


def program_table_path(query):
    _closed(query, 'inputClass snapshot entryEstablished operand')
    _check_entry(query)
    _program_row(query['operand'])
    r = Reference(query['snapshot'], 'program_table_path', TABLE_SCOPE)
    out = _entry(r, 0x60BD, query['entryEstablished'])
    if out is None:
        out = _mode_producer(r, query['operand'])
    return {**out, 'programOperandAddress': 0x6105, 'programOperandIndex': None}


def indexed_to_mode_reaching_definitions(query):
    _closed(query, 'inputClass sourceBinding indexedCallerPc modeCallerPc localLineage '
            'indexedReturn modeIncomingSsp premises claim')
    _input_class(query['inputClass'])
    _enum(query['claim'], ('ConditionalOnly', 'NativeOwner', 'ActualHardware', 'RuntimeAdmission'))
    binding = query['sourceBinding']
    if binding is not None and type(binding) is not str:
        raise ValueError('ReferenceLineageBindingType')
    for field in ('indexedCallerPc', 'modeCallerPc', 'modeIncomingSsp'):
        if not _integer(query[field], 65535):
            raise ValueError('ReferenceLineageWordType')
    premises = query['premises']
    _closed(premises, ' '.join(LINEAGE_PREMISES))
    for value in premises.values():
        _optional_bool(value)
    for field in ('localLineage', 'indexedReturn'):
        if type(query[field]) is not dict or query[field].get('inputClass') != query['inputClass']:
            raise ValueError('ReferenceLineageChildInputClass')
    local = accepted_lineage(query['localLineage'])
    returned = call_return_obligations(query['indexedReturn'])
    indexed, mode = query['indexedCallerPc'], query['modeCallerPc']
    known = indexed in (0x276A, 0x2B64) and mode in (0x27D0, 0x4069)
    cold = (indexed, mode) == (0x276A, 0x27D0)
    edges = []
    if known and binding == INDEXED_PROOF:
        edges = [{'from': start, 'to': end, 'class': label} for start, end, label in (
            (indexed, 0x5C86, 'ConfirmedCallTarget'), (mode, 0x5F45, 'ConfirmedCallTarget'),
            (0x5CB7, 0x5CCD, 'SourceUnbound'),
        )]
        if cold:
            edges.append({'from': 0x276D, 'to': 0x27D0, 'class': 'ReturnFrameDependent',
                          'via': [0x276F, 0x2771, 0x2777, 0x279E, 0x7C0B, 0x7C11,
                                  0x27A2, 0x27B2, 0x27C3]})
        edges.extend([{'from': 0x5CB4, 'to': 0x60CC, 'class': 'ReachingDefinitionCandidate'},
                      {'from': 0x60E4, 'to': 0x2869, 'class': 'SourceUnbound'}])
    sp = query['modeIncomingSsp']
    address = None if sp is None else sp // 2 * 2
    candidate = local['state']['lastSlot']['generation']
    missing = [name for name in LINEAGE_PREMISES if premises[name] is not True]
    end = 0x5CB7
    results = [
        (query['claim'] != 'ConditionalOnly', 'OutsideVerifiedScope', 'NonConditionalLineageClaim', None),
        (not known, 'OutsideVerifiedScope', 'UnreviewedCallerPair', None),
        (binding is None, 'IndeterminateObligation', 'LineageSourceBindingMissing', None),
        (binding != INDEXED_PROOF, 'OutsideVerifiedScope', 'LineageSourceBindingMismatch', None),
        (local['status'] != 'CompleteConditional', local['status'], 'LocalWriterNotRetained', end),
        (query['indexedReturn']['callerPc'] != indexed, 'OutsideVerifiedScope', 'IndexedFrameCallerMismatch', end),
        (returned['status'] != 'CompleteConditional', 'IndeterminateObligation', 'IndexedReturnUnestablished', end),
        (not cold, 'IndeterminateObligation', 'CommonCallerPathUnestablished', end),
        (sp is None, 'IndeterminateObligation', 'ModeFrameAddressUnknown', end),
        (_alias(address, 0x5F45) != 'OrdinaryDataCandidate', 'OutsideVerifiedScope', 'ModeFrameAliasRequiresProof', end),
        (bool(missing), 'IndeterminateObligation', 'LineagePremisesNotEstablished', end),
    ]
    status, reason, stop = next(((state, why, pc) for fails, state, why, pc in results if fails),
                                ('CompleteConditional', 'ConditionalColdWriterGeneration', 0x60CC))
    complete = status == 'CompleteConditional'
    constraints = (['ActualNativeData03cbOwnerUnestablished', 'NativeCallOrderUnobserved'] if complete else
                   missing if reason == 'LineagePremisesNotEstablished' else [reason])
    state = {'candidateGeneration': candidate, 'retainedGeneration': candidate if complete else None,
             'modeFrameAddress': address, 'actualNativeData03cbOwner': None, 'nativeContinuityEstablished': False}
    return _formal('indexed_to_mode_reaching_definitions', query, LINEAGE_SCOPE, status, reason, stop, state,
                   missing=constraints, children=(local, returned), edges=edges)


def callee_clobber_summary(query):
    _closed(query, 'inputClass callerPc phase scb contextEstablished')
    _input_class(query['inputClass'])
    _enum(query['phase'], ('ModeCalleeBeforeRt', 'CallerPreEntry'))
    _optional_bool(query['contextEstablished'])
    caller, bank = query['callerPc'], query['scb']
    if not _integer(caller, 65535) or not _integer(bank, 7):
        raise ValueError('ReferenceCalleeInput')
    registers = ('AL', 'AH', 'A', 'CF', 'ZF', 'HC', 'DD', 'MIE', 'OtherPSW', 'LRB',
                 'SCB', 'X1', 'X2', 'DP', 'USP', 'SSP', 'SoftwareSfrIntents')
    written_data = ('0208', '0209', '020A', '0216', '0217', '0219', '0227', '0356', '0382', '0383')
    retained_data = ('03C7', '03CB', '03CE', '03CF')
    caller_qualified = caller in (0x27D0, 0x4069)
    pre_entry = query['phase'] == 'CallerPreEntry'
    context = query['contextEstablished']
    complete = caller_qualified and not pre_entry and context is True
    unknown = 'UnknownDueToNestedCallee' if caller == 0x4069 and pre_entry else 'UnknownDueToUnreviewedPath'
    state = {
        'callerPc': caller, 'phase': query['phase'], 'registerEffects': dict.fromkeys(registers, unknown),
        'dataEffects': dict.fromkeys((*written_data, *retained_data), unknown), 'dpAliasCandidates': [],
        'undefinedLogicalPswFlags': [], 'nestedCallSites': [] if caller_qualified and not pre_entry else None,
        'unreviewedPreEntryCallee': 0x4068 if caller == 0x4069 and pre_entry else None,
    }
    edges = [{'from': caller, 'to': 0x5F45, 'classification': 'DirectCallTarget'}] if caller_qualified else []
    if not caller_qualified:
        scope, stop, status, reason = (), None, 'OutsideVerifiedScope', 'UnreviewedModeCaller'
    elif pre_entry:
        stop = 0x4068 if caller == 0x4069 else caller
        scope = (0x4068, caller) if caller == 0x4069 else (0x27CE, caller)
        status = 'IndeterminateObligation'
        reason = 'PreEntryCalleeEffectsUnresolved' if caller == 0x4069 else 'PriorCallerContextUnresolved'
    else:
        scope = tuple(row[0] for row in NODE_ROWS)
        if complete:
            stop, status, reason = 0x60E4, 'CompleteConditional', 'ReviewedCalleeClobberFootprints'
        else:
            stop, reason = 0x5F45, 'CalleeContextNotEstablished'
            status = 'IndeterminateObligation' if context is None else 'OutsideVerifiedScope'
    constraints = [reason]
    if complete:
        overwritten = {'AL', 'AH', 'A', 'CF', 'ZF', 'DD', 'OtherPSW', 'DP'}
        state['registerEffects'] = {
            name: 'ProvenOverwritten' if name in overwritten else
            'ConditionallyOverwritten' if name == 'HC' else 'ProvenUnchangedWithinReviewedPath'
            for name in registers
        }
        state['dataEffects'] = {**dict.fromkeys(written_data, 'ProvenOverwritten'),
                                **dict.fromkeys(retained_data, 'ProvenUnchangedWithinReviewedPath')}
        state['dpAliasCandidates'] = [0x84 + 8 * n for n in (range(8) if bank is None else (bank,))]
        state['undefinedLogicalPswFlags'] = ['CF', 'ZF', 'HC']
        constraints = ['NativeCallerEntryAndReturnNotEstablished', 'LogicalPswhFlagCaveatRetained']
    return _formal('callee_clobber_summary', query, scope, status, reason, stop, state,
                   missing=constraints, edges=edges)


OPERATIONS = {operation.__name__: operation for operation in (
    mode_enclosing_caller, program_table_path, callee_clobber_summary, indexed_acquisition_caller,
    call_return_obligations, indexed_to_mode_reaching_definitions,
)}
SOURCE_IDENTITIES = {
    'base': 'a638a0cd0cbb03548f5e17fa7fd075d55fe307b3',
    'frame': FRAME_PROOF, 'mode': MODE_PROOF, 'indexed': INDEXED_PROOF,
}


def evaluate(case):
    return OPERATIONS[case['operation']](deepcopy(case['input']))


def record(case, output=None):
    out = evaluate(case) if output is None else output
    state = out['state']
    generations = {
        'data': deepcopy(state.get('generations')),
        'softwareIntents': {k: v['generation'] for k, v in state['configurationIntents'].items()}
        if 'configurationIntents' in state else None,
        'suppliedReadbacks': {k: v['generation'] for k, v in state['sfrReadbacks'].items()}
        if 'sfrReadbacks' in state else None,
        'writerEvents': [{'ordinal': event['ordinal'], 'before': deepcopy(event.get('beforeGeneration')),
                          'after': deepcopy(event.get('afterGeneration'))} for event in out['journal']],
        'reachingDefinitions': deepcopy(state.get('reachingDefinitions')),
    }
    step_fields = ('afterRegisters', 'afterRegisterKnownBits', 'afterPointerState', 'afterX1State')
    return {
        'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
        'output': deepcopy(out), 'sourceScope': deepcopy(out['sourceScope']),
        'sourceIdentities': deepcopy(SOURCE_IDENTITIES), 'evidenceClass': out['effectClass'],
        'applicability': 'StandardMsm66201_207_Documented_NotEcuApplicable',
        'sourceEdges': deepcopy(out.get('sourceEdges', [])),
        'branchOutcome': [{'pc': s['pc'], 'taken': s['branchTaken'], 'next': s['next']}
                          for s in out['steps'] if s['kind'] == 'Branch'],
        'registerEffects': [{'pc': s['pc'], **{key: deepcopy(s.get(key)) for key in step_fields}}
                            for s in out['steps']],
        'reads': deepcopy(out['reads']), 'orderedWrites': deepcopy(out['journal']),
        'frameObligations': deepcopy(out.get('frameObligations', [])), 'generations': generations,
        'intermediateStates': deepcopy(out['intermediateStates']),
        'unresolvedConstraints': deepcopy(out['unresolvedConstraints']),
        'stopBoundary': {'local': out['exactStopBoundary'], 'global': out['stbufStopBoundary']},
        'executionAuthority': {key: deepcopy(out[key]) for key in AUTHORITY},
    }


def canonical_records():
    for item in cases():
        yield canonical(record(item))
