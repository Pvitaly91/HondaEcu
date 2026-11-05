"""Independent source-effect reference; never imports the new implementation."""
from copy import deepcopy
import re

from conditional_flag_mode_shadow.reference_oracle import (
    _Reference as PriorReference, _checked as prior_checked, BIT_FIELDS,
)
from generic_payload_multibyte.reference_oracle import parser_step as previous_parser
from .corpus import ADDRESSES, OLD_ADDRESSES, FRAME_ROLES, PREMISES, cases, rti_query

COMMON = ('ActualEcuEquivalenceNotEstablished', 'Native026CToConsumerContinuityNotEstablished',
          'PhysicalSFNotEstablished', 'PeripheralLifecycleNotEstablished', 'ActualRtiExecutionNotRun')
CONSUMER_SCOPE = (0x28D8, 0x28DB, 0x28DC, 0x28DE, 0x297C, 0x297F)
TAIL_SCOPE = (0x0295, 0x0297, 0x029A)
PARSER_SCOPE = tuple(sorted((0x021F, 0x0222, 0x0225, 0x0255, 0x0256, 0x0258, 0x0259,
    0x025B, 0x025D, 0x025F, 0x0260, 0x0262, 0x0264, 0x0267, 0x0269, 0x026A,
    0x026C, 0x026D, 0x026F, 0x0270, 0x0272, 0x0275, 0x0277, 0x0279, 0x027A,
    0x027B, 0x027D, 0x027F, 0x0281, 0x0282, 0x0284, 0x0286, 0x0287, 0x0289,
    0x028A, 0x028C, 0x028E, 0x0290, 0x0293, 0x0295, 0x0297, 0x029A)))
LABEL = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')
TIMELINE_CLASS = 'ConditionalBoundaryTimeline_NotCpuObservations'


def canonical(value):
    import json
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def _integer(value, maximum):
    return value is None or type(value) is int and 0 <= value <= maximum


def _generation(value):
    return value is None or type(value) is str and bool(value)


def _input_class(value):
    if value not in ('SyntheticTestInput', 'SymbolicInput', 'ManufacturerSourceQualifiedState'):
        raise ValueError('ReferenceInputClass')


def _project(snapshot):
    value = deepcopy(snapshot)
    value['memory'] = {key: value['memory'][key] for key in OLD_ADDRESSES}
    value['generations'] = {key: value['generations'][key] for key in OLD_ADDRESSES}
    value['knownBits'] = {key: bit for key, bit in value['knownBits'].items() if key in BIT_FIELDS}
    return value


def _checked(snapshot):
    if type(snapshot) is not dict or set(snapshot) != {'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions'}:
        raise ValueError('ReferenceSnapshotShape')
    if type(snapshot['memory']) is not dict or set(snapshot['memory']) != set(ADDRESSES) or any(not _integer(v, 255) for v in snapshot['memory'].values()):
        raise ValueError('ReferenceMemoryShape')
    if type(snapshot['generations']) is not dict or set(snapshot['generations']) != set(ADDRESSES) or any(not _generation(v) for v in snapshot['generations'].values()):
        raise ValueError('ReferenceGenerationShape')
    if type(snapshot['knownBits']) is not dict:
        raise ValueError('ReferenceKnownBitsShape')
    for key, bit in snapshot['knownBits'].items():
        if (type(key) is not str or len(key) != 6 or key[:4] not in ADDRESSES
                or key[4] != '.' or key[5] not in '01234567' or type(bit) is not int or bit not in (0, 1)):
            raise ValueError('ReferenceKnownBitType')
        raw = snapshot['memory'][key[:4]]
        if raw is not None and ((raw >> int(key[5])) & 1) != bit:
            raise ValueError('ReferenceContradictoryKnownBit')
    prior_checked(_project(snapshot))
    return deepcopy(snapshot)


def _bits(value, width=8):
    return {} if value is None else {bit: (value >> bit) & 1 for bit in range(width)}


def _scalar(bits, width=8):
    return sum(bits[bit] << bit for bit in range(width)) if len(bits) == width else None


def _zero(bits, width):
    return 0 if 1 in bits.values() else 1 if len(bits) == width else None


def _register_bits(registers):
    return {name.upper() + '.' + str(bit): value for name in ('al', 'ah') for bit, value in _bits(registers[name]).items()}


def _word(values):
    return None if any(value is None for value in values) else sum(value << (index * 8) for index, value in enumerate(values))


def _memory_bits(state, address):
    name = f'{address:04X}'
    raw = state['memory'][name]
    return _bits(raw) if raw is not None else {int(key[-1]): value for key, value in state['knownBits'].items() if key[:4] == name}


def _pointer(state):
    bank = state['registers']['scb']
    if bank is None:
        return {'dataAddress': None, 'value': None, 'knownBits': {}}
    address = 0x84 + bank * 8
    bits = {bit + index * 8: value for index in range(2)
            for bit, value in _memory_bits(state, address + index).items()}
    return {'dataAddress': address, 'value': _scalar(bits, 16),
            'knownBits': {'DP.' + str(bit): value for bit, value in bits.items()}}


class Reference(PriorReference):
    def __init__(self, snapshot, procedure, scope, specific=()):
        original = _checked(snapshot)
        super().__init__(_project(original), procedure)
        self.original = original
        self.state = {key: deepcopy(original[key]) for key in ('memory', 'knownBits', 'registers', 'generations')}
        self.state['registerKnownBits'] = _register_bits(self.registers)
        self.scope = list(scope)
        self.specific = list(specific)
        self.rti = None

    def result(self, boundary, outcome=None, status='CompleteConditional', reason='VerifiedSelectedSourcePath'):
        value = super().result(boundary, outcome, status, reason)
        value.update(sourceScope=self.scope[:], pointerState=_pointer(self.state), rtiObligations=deepcopy(self.rti),
            unresolvedConstraints=list(dict.fromkeys([*COMMON, *self.specific,
                *([] if status == 'CompleteConditional' else [reason])])))
        return value

    def guard(self, entry, prefix=False):
        if self.original['assumptions']['noInterference'] is not True:
            return self.outside(entry, 'NoInterferencePremiseNotEstablished')
        prefixes = ['ConditionalEffect:' + self.name + ':']
        if prefix:
            prefixes.append('ConditionalEffect:parser_step@M2cqPrefix:')
        if any(label is not None and any(label.startswith(p) for p in prefixes)
               for label in self.state['generations'].values()):
            return self.outside(entry, 'EffectNamespaceAlreadyPresent')
        return None

    def step(self, pc, successor, kind='Linear', taken=None):
        super().step(pc, successor, kind, taken)
        self.steps[-1].update(afterRegisterKnownBits=deepcopy(self.state['registerKnownBits']),
                              afterPointerState=_pointer(self.state))

    def read(self, pc, address, width=8, space='DATA', role='FunctionalOperand'):
        address = address if width == 8 else address & 0xFFFE
        names = [f'{address + index:04X}' for index in range(width // 8)]
        values = [self.state['memory'][key] for key in names]
        self.reads.append({'pc': pc, 'space': space, 'address': address, 'widthBits': width,
            'value': _word(values), 'bytes': values,
            'knownBits': {key: bit for key, bit in self.state['knownBits'].items() if key[:4] in names},
            'generations': [self.state['generations'][key] for key in names], 'accessRole': role})
        return values

    def write(self, pc, address, values, kind, source, register_before=None, partial=None):
        super().write(pc, address, values, kind, source, register_before)
        if partial:
            for key, bit in partial.items():
                if self.state['memory'][key[:4]] is None:
                    self.state['knownBits'][key] = bit
            self.intermediate[-1]['state'] = deepcopy(self.state)

    def register_byte(self, name, bits):
        self.registers[name] = _scalar(bits)
        upper = name.upper() + '.'
        self.state['registerKnownBits'] = {key: value for key, value in self.state['registerKnownBits'].items() if not key.startswith(upper)}
        self.state['registerKnownBits'].update({upper + str(bit): value for bit, value in bits.items()})

    def register_byte_bits(self, name):
        prefix = name.upper() + '.'
        return {int(key[-1]): value for key, value in self.state['registerKnownBits'].items() if key.startswith(prefix)}

    def store_a(self, pc, address, word=False):
        names = ('al', 'ah') if word else ('al',)
        values = [self.registers[name] for name in names]
        partial = {f'{address + index:04X}.{bit}': value for index, name in enumerate(names)
                   if values[index] is None for bit, value in self.register_byte_bits(name).items()}
        self.write(pc, address, values, 'Store', 'A' if word else 'AL', partial=partial)

    def load_word(self, pc, address, successor):
        self.read(pc, address, 16)
        combined = {}
        for index, name in enumerate(('al', 'ah')):
            bits = _memory_bits(self.state, address + index)
            self.register_byte(name, bits)
            combined.update({index * 8 + bit: value for bit, value in bits.items()})
        self.registers.update(dd=1, zf=_zero(combined, 16))
        self.step(pc, successor)

    def clear_mie(self):
        before = self._packed_pswh()
        knowledge = {'0005.' + str(bit): self.registers[key]
                     for key, bit in (('mie', 0), ('dd', 4), ('hc', 5), ('zf', 6), ('cf', 7))
                     if self.registers[key] is not None}
        self.reads.append({'pc': 0x0297, 'space': 'REGISTER', 'address': 5, 'widthBits': 8,
            'value': before, 'bytes': [before], 'knownBits': knowledge,
            'generations': [None], 'accessRole': 'RegisterOperand'})
        self.registers.update(mie=0, zf=None)
        self.write(0x0297, 5, [self._packed_pswh()], 'RegisterMask', 'PSWH&FE', register_before=before)


def payload_consumer(snapshot):
    r = Reference(snapshot, 'payload_consumer', CONSUMER_SCOPE,
        ('Specific026CGenerationReachingConsumerNotEstablished', 'Downstream2980OutsideVerifiedScope'))
    failure = r.guard(0x28D8)
    if failure is not None:
        return failure
    bank = r.registers['scb']
    if bank is None:
        return r.outside(0x28D8, 'PointerBankNotEstablished')
    pointer_address = 0x84 + bank * 8
    r.write(0x28D8, pointer_address, [0xF4, 3], 'PointingRegisterWrite', 'Literal')
    r.step(0x28D8, 0x28DB)
    if r.original['assumptions']['ordinaryByteSemantics'] is not True:
        return r.outside(0x28DB, 'OrdinaryByteSemanticsNotEstablished')
    r.read(0x28DB, pointer_address, 16, 'ARCHITECTURAL_ADDRESS_DEPENDENCY', 'PointingRegisterAlias')
    r.read(0x28DB, 0x03F4)
    bits = _memory_bits(r.state, 0x03F4)
    r.register_byte('al', bits)
    r.registers.update(dd=0, zf=_zero(bits, 8))
    r.step(0x28DB, 0x28DC)
    domain = [value for value in range(256) if all((value >> bit) & 1 == knowledge for bit, knowledge in bits.items())]
    results = [(value + 3) % 256 for value in domain]
    output_bits = {bit: (results[0] >> bit) & 1 for bit in range(8)
                   if len({(value >> bit) & 1 for value in results}) == 1}
    r.register_byte('al', output_bits)
    for name, observations in (('cf', [int(value + 3 > 255) for value in domain]),
                               ('zf', [int(value == 0) for value in results]),
                               ('hc', [int((value & 15) + 3 > 15) for value in domain])):
        r.registers[name] = observations[0] if len(set(observations)) == 1 else None
    r.step(0x28DC, 0x28DE)
    r.step(0x28DE, 0x297C, 'Jump', True)
    r.write(0x297C, pointer_address, [0xF2, 3], 'PointingRegisterWrite', 'Literal')
    r.step(0x297C, 0x297F)
    r.read(0x297F, pointer_address, 16, 'ARCHITECTURAL_ADDRESS_DEPENDENCY', 'PointingRegisterAlias')
    r.store_a(0x297F, 0x03F2)
    r.step(0x297F, 0x2980)
    return r.result(0x2980, 'PayloadReadAddThreeStored')


def _tail(r):
    r.specific = ['PswhSelfDestinationZfOrderNotEstablished']
    if any(r.state['generations'][key] is None for key in ('00F8', '00F9')):
        r.specific.append('F8GenerationNotEstablished')
    r.load_word(0x0295, 0x00F8, 0x0297)
    r.clear_mie()
    r.step(0x0297, 0x029A)
    r.store_a(0x029A, 0x001A, word=True)
    r.step(0x029A, 0x029C)
    query = rti_query(r.registers['ssp'])
    query['inputClass'] = r.original['inputClass']
    r.rti = rti_obligations(query)
    return r.result(0x029C, 'PreRtiTailSpecified')


def post_checksum_tail(snapshot):
    r = Reference(snapshot, 'post_checksum_tail', TAIL_SCOPE, ['PswhSelfDestinationZfOrderNotEstablished'])
    if any(r.state['generations'][key] is None for key in ('00F8', '00F9')):
        r.specific.append('F8GenerationNotEstablished')
    failure = r.guard(0x0295)
    return failure if failure is not None else _tail(r)


def _expanded(state, original):
    full = {key: deepcopy(original[key]) for key in ('memory', 'knownBits', 'registers', 'generations')}
    full['memory'].update(state['memory'])
    full['generations'].update(state['generations'])
    full['registers'] = deepcopy(state['registers'])
    full['knownBits'] = {key: value for key, value in original['knownBits'].items() if key not in BIT_FIELDS}
    full['knownBits'].update(state['knownBits'])
    full['registerKnownBits'] = _register_bits(full['registers'])
    return full


def parser_step_with_tail(snapshot):
    r = Reference(snapshot, 'parser_step_with_tail', PARSER_SCOPE)
    failure = r.guard(0x021F, prefix=True)
    if failure is not None:
        return failure
    if any(key not in BIT_FIELDS and key[:4] in OLD_ADDRESSES and key[:4] not in ('00F8', '00F9') for key in snapshot['knownBits']):
        return r.outside(0x021F, 'UnsupportedPartialParserKnowledge')
    prefix = previous_parser(_project(snapshot), stage_id='M2cqPrefix')
    r.journal = deepcopy(prefix['journal'])
    r.intermediate = [{'afterOrdinal': item['afterOrdinal'], 'pc': item['pc'],
                       'state': _expanded(item['state'], snapshot)} for item in prefix['intermediateStates']]
    tracked = deepcopy(r.state)
    remaining = list(enumerate(prefix['reads']))
    for step in prefix['steps']:
        pc = step['pc']
        selected = [(index, read) for index, read in remaining if read['pc'] == pc]
        for index, read in selected:
            row = deepcopy(read)
            row['generations'] = [tracked['generations'][f"{row['address'] + byte:04X}"] for byte in range(row['widthBits'] // 8)]
            row['accessRole'] = 'FunctionalOperand'
            r.reads.append(row)
        remaining = [(index, read) for index, read in remaining if all(index != chosen for chosen, _ in selected)]
        for event in prefix['journal']:
            if event['pc'] == pc:
                tracked = deepcopy(r.intermediate[event['ordinal'] - 1]['state'])
        row = deepcopy(step)
        row['afterRegisterKnownBits'] = _register_bits(step['afterRegisters'])
        row['afterPointerState'] = _pointer(tracked)
        r.steps.append(row)
    assert not remaining
    r.state = _expanded(prefix['state'], snapshot)
    if prefix['status'] != 'CompleteConditional' or prefix['boundary'] not in (0x0272, 0x0295):
        return r.result(prefix['boundary'], prefix['outcome'], prefix['status'], prefix['reason'])
    if prefix['boundary'] == 0x0272:
        r.step(0x0272, 0x0295, 'Jump', True)
    return _tail(r)


def _label(value):
    return type(value) is str and LABEL.fullmatch(value) is not None


def _timeline_checked(query):
    if type(query) is not dict or set(query) != {'inputClass', 'initial', 'events', 'noInterference', 'claim'}:
        raise ValueError('ReferenceTimelineShape')
    _input_class(query['inputClass'])
    if type(query['initial']) is not dict or set(query['initial']) != {'value', 'generation'} or not _integer(query['initial']['value'], 255) or not _generation(query['initial']['generation']):
        raise ValueError('ReferenceInitialWriter')
    if query['noInterference'] is not None and type(query['noInterference']) is not bool:
        raise ValueError('ReferenceTimelinePremise')
    if query['claim'] not in ('ConditionalOnly', 'Confirmed026CConsumer', 'PayloadArray', 'Fifo', 'ActualExecution'):
        raise ValueError('ReferenceTimelineClaim')
    if type(query['events']) is not list or not 1 <= len(query['events']) <= 32:
        raise ValueError('ReferenceTimelineBound')
    ids = set()
    shapes = {'GenericStore': {'kind', 'id', 'value', 'generation', 'lrb', 'dd'},
              'AlternateStore': {'kind', 'id', 'address', 'widthBits', 'value', 'generation'},
              'UnknownWriter': {'kind', 'id'}, 'ConsumerBoundary': {'kind', 'id', 'requestedGeneration'}}
    for item in query['events']:
        if type(item) is not dict or type(item.get('kind')) is not str or item['kind'] not in shapes or set(item) != shapes[item['kind']]:
            raise ValueError('ReferenceTimelineEventShape')
        if not _label(item['id']) or item['id'] in ids:
            raise ValueError('ReferenceTimelineEventId')
        ids.add(item['id'])
        kind = item['kind']
        if kind == 'GenericStore' and (not _integer(item['value'], 255) or not _generation(item['generation']) or not _integer(item['lrb'], 65535) or not _integer(item['dd'], 1)):
            raise ValueError('ReferenceGenericStoreType')
        if kind == 'AlternateStore' and (type(item['address']) is not int or item['address'] not in (0x3F3, 0x3F4, 0x3F5, 0x3F6) or type(item['widthBits']) is not int or item['widthBits'] not in (8, 16) or not _integer(item['value'], (1 << item['widthBits']) - 1) or not _generation(item['generation'])):
            raise ValueError('ReferenceAlternateStoreType')
        if kind == 'ConsumerBoundary' and not _generation(item['requestedGeneration']):
            raise ValueError('ReferenceRequestedGenerationType')
    return deepcopy(query)


def last_writer_at_conditional_boundary(query):
    value = _timeline_checked(query)
    state = {'lastValue': value['initial']['value'], 'lastGeneration': value['initial']['generation'], 'lastKind': 'InitialUnbound'}
    journal, reads, history = [], [], []
    labels = set() if state['lastGeneration'] is None else {state['lastGeneration']}

    def result(status='CompleteConditional', reason='ConditionalTimelineOnly', boundary=None):
        return {'procedure': 'last_writer_at_conditional_boundary', 'status': status, 'reason': reason,
            'boundary': boundary, 'inputClass': value['inputClass'], 'state': deepcopy(state),
            'journal': deepcopy(journal), 'reads': deepcopy(reads), 'intermediateStates': deepcopy(history),
            'sourceScope': [0x026C, 0x28DB],
            'unresolvedConstraints': [*COMMON, 'NativeCfgEdge026CTo28DBNotEstablished', 'OnlyLastSlotModeled_NotArrayOrFifo',
                                     *([] if status == 'CompleteConditional' else [reason])],
            'effectClass': TIMELINE_CLASS, 'actualHardwareObservation': None, 'cpuInstructionRetirements': 0,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}

    if value['claim'] != 'ConditionalOnly':
        return result('OutsideVerifiedScope', 'UnestablishedAuthorityClaim')
    for index, event in enumerate(value['events']):
        kind = event['kind']
        if kind == 'GenericStore' and (event['lrb'] != 0x7E or event['dd'] != 0):
            return result('OutsideVerifiedScope', 'ProducerContextNotEstablished', index)
        if kind in ('GenericStore', 'AlternateStore'):
            generation = event['generation']
            if generation is not None and generation in labels:
                return result('OutsideVerifiedScope', 'WriterGenerationReused', index)
            if generation is not None:
                labels.add(generation)
        if kind == 'ConsumerBoundary':
            relation = ('InterferenceNotExcluded' if value['noInterference'] is not True else
                        'UnknownInterveningWriter' if state['lastKind'] == 'UnknownWriter' else
                        'MissingProducerGeneration' if state['lastGeneration'] is None else
                        'StaleOrUnboundRequestedGeneration' if event['requestedGeneration'] != state['lastGeneration'] else
                        'AlternateWriterNot026C' if state['lastKind'] != 'GenericStore' else 'ConditionalLastWriterAtBoundary')
            reads.append({'eventId': event['id'], 'sourcePc': 0x28DB, 'address': 0x3F4, 'widthBits': 8,
                'value': state['lastValue'], 'generation': state['lastGeneration'],
                'requestedGeneration': event['requestedGeneration'], 'relation': relation,
                'effectClass': 'ConditionalBoundaryObservation_NotCpuRead'})
        else:
            before, old_generation = state['lastValue'], state['lastGeneration']
            if kind == 'UnknownWriter':
                address = width = declared = overlap = same = None
                state.update(lastValue=None, lastGeneration=None, lastKind=kind)
            else:
                address = 0x3F4 if kind == 'GenericStore' else event['address'] & (0xFFFF if event['widthBits'] == 8 else 0xFFFE)
                width = 8 if kind == 'GenericStore' else event['widthBits']
                declared = event['value']
                overlap = address <= 0x3F4 < address + width // 8
                if overlap:
                    after = None if declared is None else (declared >> ((0x3F4 - address) * 8)) & 255
                    state.update(lastValue=after, lastGeneration=event['generation'], lastKind=kind)
                same = before == state['lastValue'] if overlap and before is not None and state['lastValue'] is not None else None
            journal.append({'ordinal': len(journal) + 1, 'eventId': event['id'], 'kind': kind,
                'sourcePc': 0x026C if kind == 'GenericStore' else None, 'address': address, 'widthBits': width,
                'declaredValue': declared, 'beforeTrackedByte': before, 'afterTrackedByte': state['lastValue'],
                'beforeGeneration': old_generation, 'afterGeneration': state['lastGeneration'],
                'targetOverlap': overlap, 'sameTrackedByteValue': same, 'effectClass': TIMELINE_CLASS})
        history.append({'eventId': event['id'], 'eventIndex': index, 'state': deepcopy(state)})
    return result()


def _rti_checked(query):
    if type(query) is not dict or set(query) != {'inputClass', 'ssp', 'frameWords', 'frameGenerations', 'premises', 'executionClaim'}:
        raise ValueError('ReferenceRtiShape')
    _input_class(query['inputClass'])
    if not _integer(query['ssp'], 65535) or type(query['executionClaim']) is not bool:
        raise ValueError('ReferenceRtiType')
    if type(query['frameWords']) is not dict or set(query['frameWords']) != set(FRAME_ROLES) or any(not _integer(value, 65535) for value in query['frameWords'].values()):
        raise ValueError('ReferenceFrameWords')
    if type(query['frameGenerations']) is not dict or set(query['frameGenerations']) != set(FRAME_ROLES) or any(not _generation(value) for value in query['frameGenerations'].values()):
        raise ValueError('ReferenceFrameGenerations')
    if type(query['premises']) is not dict or set(query['premises']) != {*PREMISES, 'matchingEntrySsp'}:
        raise ValueError('ReferenceRtiPremises')
    if any(query['premises'][key] is not None and type(query['premises'][key]) is not bool for key in PREMISES) or not _integer(query['premises']['matchingEntrySsp'], 65535):
        raise ValueError('ReferenceRtiPremiseTypes')
    return deepcopy(query)


def rti_obligations(query):
    value = _rti_checked(query)
    t, entry = value['ssp'], value['premises']['matchingEntrySsp']
    missing, obligations = [], []
    if t is None:
        missing.append('UnknownSsp')
    if entry is None:
        missing.append('MatchingEntryFrameNotEstablished')
    if t is not None and t % 2:
        missing.append('OddSspPhysicalSafetyNotEstablished')
    for ordinal, role in enumerate(FRAME_ROLES, 1):
        number = None if t is None else (t + ordinal * 2) % 65536
        obligations.append({'ordinal': ordinal, 'role': role, 'numericSspAfterIncrement': number,
            'effectiveWordAddress': None if number is None else number & 0xFFFE,
            'widthBits': 16, 'value': value['frameWords'][role], 'generation': value['frameGenerations'][role],
            'kind': 'Obligation_NotPerformedRead'})
        if value['frameWords'][role] is None:
            missing.append('FrameWordUnknown:' + role)
        if value['frameGenerations'][role] is None:
            missing.append('FrameGenerationUnknown:' + role)
    for key in PREMISES:
        if value['premises'][key] is None:
            missing.append('PremiseUnknown:' + key)
    if value['executionClaim']:
        status, reason = 'OutsideVerifiedScope', 'ActualRtiExecutionNotAuthorized'
        missing, obligations = [], []
        restores = dict.fromkeys((*FRAME_ROLES, 'ssp', 'scb'))
    else:
        restores = {**value['frameWords'], 'ssp': None if t is None else (t + 8) % 65536,
                    'scb': None if value['frameWords']['psw'] is None else value['frameWords']['psw'] & 7}
        if t is not None and entry is not None and t != (entry - 8) % 65536:
            status, reason = 'OutsideVerifiedScope', 'MatchingEntryFrameMismatch'
        elif any(value['premises'][key] is False for key in PREMISES):
            status, reason = 'OutsideVerifiedScope', 'DeclaredFramePremiseFalse'
        elif missing:
            status, reason = 'IndeterminateObligation', 'FrameObligationsNotEstablished'
        else:
            status, reason = 'CompleteConditional', 'HypotheticalFrameObligationsSpecified'
    return {'procedure': 'rti_obligations', 'status': status, 'reason': reason, 'boundary': 0x029C,
        'inputClass': value['inputClass'], 'sourceScope': [0x029C],
        'state': {'hypotheticalRestores': restores, 'numericSspUnrounded': True,
            'byteBusOrder': 'NotEstablished', 'sfAssignment': 'NotEstablished', 'ieRestoredByRti': False,
            'pointingRegisterRamRestored': False, 'parserRamRestored': False,
            'premisesAreConditionalNotObserved': True, 'actualReturnObservation': None},
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [], 'obligationReads': obligations,
        'missingPremises': missing, 'unresolvedConstraints': [*COMMON,
            'ActualFrameAndSspOwnershipNotEstablished', 'PhysicalStackSafetyNotEstablished',
            'NmiNotExcludedByMieClear', 'RtiDoesNotRestoreIeOrPrRam', 'NoIndependentSfAssignmentSpecified',
            *([] if status == 'CompleteConditional' else [reason])],
        'effectClass': 'ArchitecturalObligationsOnly_NotRtiExecution', 'actualHardwareObservation': None,
        'cpuInstructionRetirements': 0, 'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}


OPERATIONS = {'payload_consumer': payload_consumer, 'post_checksum_tail': post_checksum_tail,
    'parser_step_with_tail': parser_step_with_tail,
    'last_writer_at_conditional_boundary': last_writer_at_conditional_boundary, 'rti_obligations': rti_obligations}


def expected_records():
    for case in cases():
        yield {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
               'output': OPERATIONS[case['operation']](case['input'])}
