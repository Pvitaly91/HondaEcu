"""Partial-byte knowledge and shared logical effects, never CPU memory access."""
from copy import deepcopy

from conditional_flag_mode_shadow import state as inherited

Boundary = inherited.Boundary
need = inherited.need
number = inherited.number
DP_ADDRESSES = frozenset(0x84 + 8 * bank + byte for bank in range(8) for byte in range(2))
ADDRESSES = tuple(sorted(set(inherited.ADDRESSES) | DP_ADDRESSES))
DATA_KEYS = frozenset(f'{address:04X}' for address in ADDRESSES)
BIT_FIELDS = frozenset(f'{key}.{bit}' for key in DATA_KEYS for bit in range(8))
COMMON = ('ActualEcuEquivalenceNotEstablished', 'Native026CToConsumerContinuityNotEstablished',
          'PhysicalSFNotEstablished', 'PeripheralLifecycleNotEstablished', 'ActualRtiExecutionNotRun')


def project(snapshot):
    return {**deepcopy(snapshot),
        'memory': {k: snapshot['memory'][k] for k in inherited.DATA_KEYS},
        'generations': {k: snapshot['generations'][k] for k in inherited.DATA_KEYS},
        'knownBits': {k: v for k, v in snapshot['knownBits'].items() if k in inherited.BIT_FIELDS}}


def validate(snapshot):
    need(type(snapshot) is dict and set(snapshot) == {
        'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions'},
        'ClosedExtendedSnapshotRequired')
    need(type(snapshot['memory']) is dict and set(snapshot['memory']) == DATA_KEYS
         and all(number(v, 255) for v in snapshot['memory'].values()), 'ExplicitFortySixBytesRequired')
    need(type(snapshot['generations']) is dict and set(snapshot['generations']) == DATA_KEYS
         and all(v is None or type(v) is str and bool(v) for v in snapshot['generations'].values()),
         'ExplicitFortySixGenerationsRequired')
    bits = snapshot['knownBits']
    need(type(bits) is dict and set(bits) <= BIT_FIELDS
         and all(type(v) is int and v in (0, 1) for v in bits.values()), 'TypedPartialBitsRequired')
    for field, value in bits.items():
        key, bit = field.split('.')
        need(snapshot['memory'][key] is None or snapshot['memory'][key] >> int(bit) & 1 == value,
             'ContradictoryBitKnowledge')
    inherited.validate(project(snapshot))
    return snapshot


def candidates(raw, bits, key):
    if raw is not None:
        return frozenset((raw,))
    specified = [(int(field[-1]), value) for field, value in bits.items() if field.startswith(key + '.')]
    return frozenset(value for value in range(256)
                     if all(value >> bit & 1 == setting for bit, setting in specified))


def unique(values):
    return next(iter(values)) if len(values) == 1 else None


def bit_consensus(values, key):
    return {f'{key}.{bit}': next(iter(settings)) for bit in range(8)
            if len(settings := {value >> bit & 1 for value in values}) == 1}


def register_bits(registers):
    result = {}
    for key in ('al', 'ah'):
        if registers[key] is not None:
            result.update(bit_consensus((registers[key],), key.upper()))
    return result


def pointer_view(state):
    scb = state['registers']['scb']
    if scb is None:
        return {'dataAddress': None, 'value': None, 'knownBits': {}}
    address = 0x84 + 8 * scb
    parts = [candidates(state['memory'][f'{address + byte:04X}'], state['knownBits'],
                        f'{address + byte:04X}') for byte in range(2)]
    values = [unique(part) for part in parts]
    known = {}
    for byte, part in enumerate(parts):
        known.update({f'DP.{byte * 8 + int(k[-1])}': v for k, v in bit_consensus(part, 'x').items()})
    value = None if None in values else values[0] | values[1] << 8
    return {'dataAddress': address, 'value': value, 'knownBits': known}


def expand_state(state, original):
    return {'memory': {**original['memory'], **state['memory']},
        'knownBits': {**{k: v for k, v in original['knownBits'].items()
                        if k not in inherited.BIT_FIELDS}, **state['knownBits']},
        'registers': deepcopy(state['registers']),
        'generations': {**original['generations'], **state['generations']},
        'registerKnownBits': register_bits(state['registers'])}


class Effects(inherited.Effects):
    """Extend frozen bookkeeping for partial words and eight DP alias banks."""

    def __init__(self, snapshot, procedure, scope):
        validate(snapshot)
        super().__init__(project(snapshot), procedure)
        self.input = deepcopy(snapshot)
        self.state = {key: deepcopy(snapshot[key]) for key in ('memory', 'knownBits', 'registers', 'generations')}
        self.r = self.state['registers']
        self.state['registerKnownBits'] = register_bits(self.r)
        self.scope = sorted(scope)
        self.specific = []

    def admit(self, entry, extra_namespaces=()):
        if self.input['assumptions']['noInterference'] is not True:
            self.halt('OutsideVerifiedScope', 'NoInterferencePremiseNotEstablished', entry)
        names = (self.procedure, *extra_namespaces)
        if any(g is not None and any(g.startswith('ConditionalEffect:' + n + ':') for n in names)
               for g in self.input['generations'].values()):
            self.halt('OutsideVerifiedScope', 'EffectNamespaceAlreadyPresent', entry)

    def read(self, pc, address, width=8):
        parts = super().read(pc, address, width)
        effective = address & 0xFFFE if width == 16 else address
        self.reads[-1].update(generations=[self.state['generations'][f'{effective + byte:04X}']
                                         for byte in range(width // 8)], accessRole='FunctionalOperand')
        return parts

    def pointer_dependency(self, pc):
        address = 0x84 + 8 * self.r['scb']
        self.read(pc, address, 16)
        self.reads[-1].update(space='ARCHITECTURAL_ADDRESS_DEPENDENCY', accessRole='PointingRegisterAlias')

    def step(self, pc, following, kind='Linear', taken=None):
        super().step(pc, following, kind, taken)
        self.steps[-1].update(afterRegisterKnownBits=deepcopy(self.state['registerKnownBits']),
                              afterPointerState=pointer_view(self.state))

    def set_a_byte(self, key, values):
        self.r[key] = unique(values)
        self.state['registerKnownBits'] = {k: v for k, v in self.state['registerKnownBits'].items()
                                           if not k.startswith(key.upper() + '.')}
        self.state['registerKnownBits'].update(bit_consensus(values, key.upper()))

    def a_values(self, key):
        return candidates(self.r[key], self.state['registerKnownBits'], key.upper())

    def a_partial(self, address, keys):
        return {f'{address + byte:04X}.{field[-1]}': value for byte, key in enumerate(keys)
                for field, value in self.state['registerKnownBits'].items() if field.startswith(key.upper() + '.')}

    def load_byte(self, pc, address, following, pointer=False):
        if self.input['assumptions']['ordinaryByteSemantics'] is not True:
            self.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', pc)
        if pointer:
            self.pointer_dependency(pc)
        self.read(pc, address)
        values = candidates(self.state['memory'][f'{address:04X}'], self.state['knownBits'], f'{address:04X}')
        self.set_a_byte('al', values)
        self.r.update(dd=0, zf=unique({int(value == 0) for value in values}))
        self.step(pc, following)

    def load_word(self, pc, following, address=None, literal=None):
        need(address is not None and literal is None, 'ClosedTailWordSourceRequired')
        self.read(pc, address, 16)
        parts = [candidates(self.state['memory'][f'{address + byte:04X}'], self.state['knownBits'],
                            f'{address + byte:04X}') for byte in range(2)]
        for key, part in zip(('al', 'ah'), parts):
            self.set_a_byte(key, part)
        zero = 0 if any(0 not in part for part in parts) else 1 if all(part == {0} for part in parts) else None
        self.r.update(dd=1, zf=zero)
        self.step(pc, following)

    def store(self, pc, address, parts, kind='Store', source='A', preserve_bits=False, partial=None):
        address = address & 0xFFFE if len(parts) == 2 else address
        keys = [f'{address + byte:04X}' for byte in range(len(parts))]
        before = [self.state['memory'][key] for key in keys]
        generations = [self.state['generations'][key] for key in keys]
        for key, part in zip(keys, parts):
            self.state['memory'][key] = part
            if part is not None or not preserve_bits or partial is not None:
                self.state['knownBits'] = {k: v for k, v in self.state['knownBits'].items() if k[:4] != key}
            if part is None and partial is not None:
                self.state['knownBits'].update({k: v for k, v in partial.items() if k[:4] == key})
        self._event(pc, address, before, parts, kind, source, 'DATA', generations)

    def mask_pswh(self, pc, mie, following):
        super().mask_pswh(pc, mie, following)
        self.reads[-1].update(generations=[None], accessRole='RegisterOperand')

    def result(self, status, reason, boundary, outcome=None):
        result = super().result(status, reason, boundary, outcome)
        constraints = list(COMMON) + self.specific
        if status != 'CompleteConditional' and reason not in constraints:
            constraints.append(reason)
        return {**result, 'sourceScope': self.scope, 'pointerState': pointer_view(self.state),
                'unresolvedConstraints': constraints, 'rtiObligations': None}
