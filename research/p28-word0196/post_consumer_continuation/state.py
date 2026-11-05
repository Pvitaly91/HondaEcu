"""Preserve explicit partial accumulator knowledge across the frozen consumer edge."""
from copy import deepcopy
from payload_consumer_tail import state as frozen

Boundary, need, number = frozen.Boundary, frozen.need, frozen.number
COMMON = frozen.COMMON
SLOTS = frozenset(('03F2', '03F4'))
REG_BITS = frozenset(f'{r}.{b}' for r in ('AL', 'AH') for b in range(8))


def label(value):
    return value is None or type(value) is str and bool(value)


def validate_register_bits(registers, bits):
    need(type(bits) is dict and set(bits) <= REG_BITS
         and all(type(v) is int and v in (0, 1) for v in bits.values()), 'TypedRegisterKnowledgeRequired')
    for key, value in bits.items():
        raw = registers[key[:2].lower()]
        need(raw is None or raw >> int(key[-1]) & 1 == value, 'TypedRegisterKnowledgeRequired')


def project(snapshot):
    return {key: deepcopy(value) for key, value in snapshot.items() if key != 'registerKnownBits'}


def validate(snapshot):
    need(type(snapshot) is dict and set(snapshot) == {
        'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions', 'registerKnownBits'},
        'ClosedContinuationSnapshotRequired')
    frozen.validate(project(snapshot))
    validate_register_bits(snapshot['registers'], snapshot['registerKnownBits'])


def slot(value):
    need(type(value) is dict and set(value) == {'value', 'knownBits', 'generation'}
         and number(value['value'], 255) and label(value['generation']), 'TypedConditionalSlotRequired')
    bits = value['knownBits']
    need(type(bits) is dict and set(bits) <= {str(b) for b in range(8)}
         and all(type(v) is int and v in (0, 1) for v in bits.values()), 'TypedSlotBitsRequired')
    need(all(value['value'] is None or value['value'] >> int(k) & 1 == v for k, v in bits.items()),
         'ContradictorySlotBits')
    return value


def slot_values(value):
    return frozen.candidates(value['value'], {'x.' + k: v for k, v in value['knownBits'].items()}, 'x')


class Effects(frozen.Effects):
    """Only the input adapter differs; all DATA alias/journal rules remain frozen."""

    def __init__(self, snapshot, procedure, scope):
        validate(snapshot)
        super().__init__(project(snapshot), procedure, scope)
        self.input = deepcopy(snapshot)
        self.state['registerKnownBits'] = deepcopy(snapshot['registerKnownBits'])
        self.specific = ['Stbuf2995NotPerformed', 'PeripheralEquivalenceNotEstablished']

    def result(self, status, reason, boundary, outcome=None):
        return {**super().result(status, reason, boundary, outcome), 'stbufObligations': None}
