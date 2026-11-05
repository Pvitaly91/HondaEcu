"""Conditional DATA state and declared SFR write intents remain distinct types/spaces."""
from copy import deepcopy
from payload_consumer_tail import state as frozen
from post_consumer_continuation.state import validate_register_bits, slot, label, slot_values
from .source_inventory import SFR_KEYS

Boundary, need, number, COMMON = frozen.Boundary, frozen.need, frozen.number, frozen.COMMON
DATA_KEYS = frozen.DATA_KEYS | frozenset(('0208', '0209'))
BIT_FIELDS = frozenset(f'{key}.{bit}' for key in DATA_KEYS for bit in range(8))
ACTUAL_FIELDS = ('actualHardwareObservation', 'actualBufferWrite', 'actualTransmission',
                 'actualTxCompletion', 'actualTxIrqDelivery', 'actualPeripheralClockEvent')


def input_class(value):
    need(type(value) is str and value in frozen.inherited.INPUT_CLASSES, 'ActualHardwareInputNotAdmitted')


def intents(value):
    need(type(value) is dict and set(value) == SFR_KEYS, 'FiveExplicitSoftwareIntentSlotsRequired')
    for entry in value.values():
        slot(entry)


def project(snapshot):
    result = {key: deepcopy(snapshot[key]) for key in (
        'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions')}
    result['memory'] = {k: result['memory'][k] for k in frozen.DATA_KEYS}
    result['generations'] = {k: result['generations'][k] for k in frozen.DATA_KEYS}
    result['knownBits'] = {k: v for k, v in result['knownBits'].items() if k in frozen.BIT_FIELDS}
    return result


def validate(snapshot):
    need(type(snapshot) is dict and set(snapshot) == {'inputClass', 'memory', 'knownBits', 'registers',
        'generations', 'assumptions', 'registerKnownBits', 'configurationIntents'}, 'ClosedConfigurationSnapshotRequired')
    need(type(snapshot['memory']) is dict and set(snapshot['memory']) == DATA_KEYS
         and all(number(v, 255) for v in snapshot['memory'].values()), 'ExplicitFortyEightDataBytesRequired')
    need(type(snapshot['generations']) is dict and set(snapshot['generations']) == DATA_KEYS
         and all(label(v) for v in snapshot['generations'].values()), 'ExplicitFortyEightGenerationsRequired')
    bits = snapshot['knownBits']
    need(type(bits) is dict and set(bits) <= BIT_FIELDS
         and all(type(v) is int and v in (0, 1) for v in bits.values()), 'TypedPartialDataBitsRequired')
    for field, value in bits.items():
        raw = snapshot['memory'][field[:4]]
        need(raw is None or raw >> int(field[-1]) & 1 == value, 'ContradictoryBitKnowledge')
    frozen.validate(project(snapshot))
    validate_register_bits(snapshot['registers'], snapshot['registerKnownBits'])
    intents(snapshot['configurationIntents'])


def authority():
    return {**dict.fromkeys(ACTUAL_FIELDS), 'cpuInstructionRetirements': 0,
            'actualPeripheralOperations': 0, 'executionStatus': 'EXECUTION_BLOCKED',
            'firmwareReady': False, 'stbufStopBoundary': 'STOP_BEFORE_STBUF_2995'}


def formal(procedure, query, state, scope, status, reason, specific, effect_class,
           boundary=0x2995, journal=None, history=None, **extra):
    constraints = [*COMMON, *specific]
    if status != 'CompleteConditional' and reason not in constraints:
        constraints.append(reason)
    return {'procedure': procedure, 'status': status, 'reason': reason, 'boundary': boundary,
        'inputClass': query['inputClass'], 'sourceScope': sorted(scope), 'state': deepcopy(state),
        'reads': [], 'journal': [] if journal is None else journal, 'steps': [],
        'intermediateStates': [] if history is None else history, 'unresolvedConstraints': constraints,
        'effectClass': effect_class, 'stopBoundary': 'STOP_BEFORE_STBUF_2995', **authority(), **extra}


class Effects(frozen.Effects):
    def __init__(self, snapshot, procedure, scope):
        validate(snapshot)
        super().__init__(project(snapshot), procedure, scope)
        self.input = deepcopy(snapshot)
        for key in ('memory', 'knownBits', 'generations', 'registerKnownBits', 'configurationIntents'):
            self.state[key] = deepcopy(snapshot[key])
        self.specific = ['PeripheralConfigurationIntentOnly', 'NativeConfigurationOwnerNotEstablished',
                         'Stbuf2995NotPerformed']

    def admit(self, entry):
        super().admit(entry)
        if any(row['generation'] is not None and row['generation'].startswith('ConditionalEffect:' + self.procedure + ':')
               for row in self.input['configurationIntents'].values()):
            self.halt('OutsideVerifiedScope', 'EffectNamespaceAlreadyPresent', entry)
        if self.r['lrb'] != 0x41:
            self.halt('OutsideVerifiedScope', 'LocalBank0208NotEstablished', entry)

    def literal_byte(self, pc, value, following):
        if self.input['assumptions']['ordinaryByteSemantics'] is not True:
            self.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', pc)
        self.set_a_byte('al', {value})
        self.r.update(dd=0, zf=int(value == 0))
        self.step(pc, following)

    def sfr_intent(self, pc, address, value, following, literal=False):
        key = f'{address:04X}'
        before = deepcopy(self.state['configurationIntents'][key])
        generation = f'ConditionalEffect:{self.procedure}:{pc:04X}:{len(self.journal) + 1}'
        bits = {} if value is not None else {k[-1]: v for k, v in self.state['registerKnownBits'].items()
                                            if k.startswith('AL.')}
        self.state['configurationIntents'][key] = {'value': value, 'knownBits': bits, 'generation': generation}
        self._event(pc, address, [before['value']], [value], 'ImmediateStore' if literal else 'Store',
                    'Literal' if literal else 'AL', 'SOFTWARE_SFR_INTENT', [before['generation']])
        row = self.journal[-1]
        row['sameDeclaredValue'] = row.pop('sameValue')
        row.update(effectClass='StaticRomSfrWriteIntent_NotPerformedIO',
                   knownBitsBefore=before['knownBits'], knownBitsAfter=deepcopy(bits), actualHardwareObservation=None)
        self.step(pc, following)

    def result(self, status, reason, boundary, outcome=None):
        return {**super().result(status, reason, boundary, outcome), **authority(),
                'stopBoundary': 'STOP_BEFORE_DATA4700_288E'}
