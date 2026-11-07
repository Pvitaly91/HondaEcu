"""Unified DATA and partial OtherPSW adapters for the accepted M2cv models."""
from copy import deepcopy

from enclosing_caller_return import state as accepted

Boundary, need, number = accepted.Boundary, accepted.need, accepted.number
slot, label, input_class = accepted.slot, accepted.label, accepted.input_class
shape, tri, frozen = accepted.shape, accepted.tri, accepted.frozen
formal_result, stop_name = accepted.formal_result, accepted.stop_name
STOP = {**accepted.STOP, 0x7DF5: 'STOP_BEFORE_PC_7DF5', 0x608F: 'STOP_BEFORE_PC_608F'}
DATA_KEYS = accepted.DATA_KEYS | {'020A'}
STATE_FIELDS = accepted.STATE_FIELDS
OTHER_PSW_BITS = (3, 4, 5, 6, 7, 9, 10, 11)


def psw_bits(raw):
    return {} if raw is None else {str(bit): (raw >> bit) & 1 for bit in OTHER_PSW_BITS}


def expand_snapshot(old):
    result = deepcopy(old)
    result['memory'].setdefault('020A', None)
    result['generations'].setdefault('020A', None)
    return result


def project(snapshot):
    result = deepcopy(snapshot)
    result['memory'].pop('020A')
    result['generations'].pop('020A')
    result['knownBits'] = {key: value for key, value in result['knownBits'].items() if key[:4] != '020A'}
    return result


def snapshot_from_child(initial, child):
    """Use the exact returned state and represent the newly tracked r2 as unknown."""
    return expand_snapshot({'inputClass': initial['inputClass'], 'assumptions': initial['assumptions'],
                            **{key: child['state'][key] for key in STATE_FIELDS}})


def validate(snapshot):
    shape(snapshot, accepted.SNAPSHOT_FIELDS, 'ClosedCorridorSnapshotRequired')
    shape(snapshot['memory'], DATA_KEYS, 'ExplicitCorridorDataRequired')
    shape(snapshot['generations'], DATA_KEYS, 'ExplicitCorridorGenerationsRequired')
    raw = snapshot['memory']['020A']
    need(number(raw, 255) and label(snapshot['generations']['020A']), 'TypedLocalR2Required')
    bits = snapshot['knownBits']
    need(type(bits) is dict and all(type(key) is str for key in bits), 'TypedCorridorKnownBitsRequired')
    for key, value in bits.items():
        if key[:4] == '020A':
            need(len(key) == 6 and key[4] == '.' and key[5] in '01234567'
                 and type(value) is int and value in (0, 1), 'TypedLocalR2BitRequired')
            need(raw is None or ((raw >> int(key[5])) & 1) == value, 'ContradictoryBitKnowledge')
    accepted.validate(project(snapshot))


class Effects(accepted.Effects):
    def __init__(self, snapshot, procedure, scope):
        validate(snapshot)
        super().__init__(project(snapshot), procedure, scope)
        self.input = deepcopy(snapshot)
        self.state = {key: deepcopy(snapshot[key]) for key in STATE_FIELDS}
        self.r = self.state['registers']
        self.state['otherPswKnownBits'] = psw_bits(self.r['otherPsw'])

    def m2cv_snapshot(self):
        return project(self.snapshot())

    def f0_value(self):
        return self.state['otherPswKnownBits'].get('4')

    def set_f0(self, value):
        need(number(value, 1), 'TypedF0Required')
        bits = self.state['otherPswKnownBits']
        if value is None:
            bits.pop('4', None)
        else:
            bits['4'] = value
        self.r['otherPsw'] = (sum(bits[str(bit)] << bit for bit in OTHER_PSW_BITS)
                              if len(bits) == len(OTHER_PSW_BITS) else None)

    def step(self, pc, following, kind='Linear', taken=None):
        super().step(pc, following, kind, taken)
        self.steps[-1]['afterOtherPswKnownBits'] = deepcopy(self.state['otherPswKnownBits'])

    @staticmethod
    def child_psw_bits(value, raw, before):
        if 'otherPswKnownBits' in value:
            return deepcopy(value['otherPswKnownBits'])
        return deepcopy(before) if raw is None else psw_bits(raw)

    def absorb(self, child):
        previous_bits = deepcopy(self.state['otherPswKnownBits'])
        history_start, step_start = len(self.intermediate), len(self.steps)
        super().absorb(child)
        self.state['otherPswKnownBits'] = self.child_psw_bits(child['state'], self.r['otherPsw'], previous_bits)
        for source, item in zip(child['intermediateStates'], self.intermediate[history_start:]):
            child_state = source['state']
            raw = child_state['registers'].get('otherPsw')
            item['state']['otherPswKnownBits'] = self.child_psw_bits(child_state, raw, previous_bits)
        for source, item in zip(child['steps'], self.steps[step_start:]):
            raw = item['afterRegisters']['otherPsw']
            if 'afterOtherPswKnownBits' in source:
                item['afterOtherPswKnownBits'] = deepcopy(source['afterOtherPswKnownBits'])
            else:
                item['afterOtherPswKnownBits'] = deepcopy(previous_bits) if raw is None else psw_bits(raw)
