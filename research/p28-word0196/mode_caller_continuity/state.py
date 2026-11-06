"""Extended partial DATA and immutable adapters to the accepted source models."""
from copy import deepcopy
from tx_ack_configuration_provenance import state as parent
from stbuf_stcon_transmit_source import state as configuration_state

Boundary, need, number = parent.Boundary, parent.need, parent.number
slot, label, input_class = parent.slot, parent.label, parent.input_class
frozen = parent.frozen
DATA_KEYS = parent.DATA_KEYS | frozenset(f'{a:04X}' for a in range(0x3C6, 0x3D6)) | frozenset(
    f'{0x80 + bank * 8 + byte:04X}' for bank in range(8) for byte in range(2)) | frozenset(('02CD', '0216', '0382', '0383'))
BIT_FIELDS = frozenset(f'{key}.{bit}' for key in DATA_KEYS for bit in range(8))
READBACK_KEYS = frozenset(('0024', '0049', '004A', '0050', '0054', '0058', '0061', '0063'))
STATE_FIELDS = ('memory', 'knownBits', 'registers', 'generations', 'registerKnownBits', 'configurationIntents', 'sfrReadbacks')
SHARED = ('ConditionalSourceReconstructionOnly', 'ActualNativeContinuityNotEstablished', 'Stbuf2995NotPerformed')
MODE_ENTRIES = ('At60BD', 'Compare3cb', 'SymbolicCarryTail')


def project(snapshot, configuration=False):
    keys = configuration_state.DATA_KEYS if configuration else parent.DATA_KEYS
    result = {name: deepcopy(snapshot[name]) for name in ('inputClass', 'memory', 'knownBits', 'registers',
        'generations', 'assumptions', 'registerKnownBits', 'configurationIntents')}
    for field in ('memory', 'generations'):
        result[field] = {key: result[field][key] for key in keys}
    result['knownBits'] = {key: value for key, value in result['knownBits'].items() if key[:4] in keys}
    if not configuration:
        result['sfrReadbacks'] = {key: deepcopy(snapshot['sfrReadbacks'][key]) for key in parent.READBACK_KEYS}
    return result


def validate(snapshot, mode=False):
    fields = {'inputClass', 'assumptions', *STATE_FIELDS}
    need(type(snapshot) is dict and set(snapshot) == (fields | {'entry'} if mode else fields), 'ClosedModeCallerSnapshotRequired')
    need(type(snapshot['memory']) is dict and set(snapshot['memory']) == DATA_KEYS
         and all(number(v, 255) for v in snapshot['memory'].values()), 'ExplicitEightyTwoBytesRequired')
    need(type(snapshot['generations']) is dict and set(snapshot['generations']) == DATA_KEYS
         and all(label(v) for v in snapshot['generations'].values()), 'ExplicitEightyTwoGenerationsRequired')
    bits = snapshot['knownBits']
    need(type(bits) is dict and set(bits) <= BIT_FIELDS
         and all(type(v) is int and v in (0, 1) for v in bits.values()), 'TypedPartialDataBitsRequired')
    for field, value in bits.items():
        raw = snapshot['memory'][field[:4]]
        need(raw is None or raw >> int(field[-1]) & 1 == value, 'ContradictoryBitKnowledge')
    need(type(snapshot['sfrReadbacks']) is dict and set(snapshot['sfrReadbacks']) == READBACK_KEYS,
         'EightExplicitSymbolicReadbackSlotsRequired')
    for value in snapshot['sfrReadbacks'].values():
        slot(value)
    parent.validate(project(snapshot))
    if mode:
        need(type(snapshot['entry']) is str and snapshot['entry'] in MODE_ENTRIES, 'ClosedExtendedModeEntryRequired')


def x1_view(state):
    bank = state['registers']['scb']
    if bank is None:
        return {'dataAddress': None, 'value': None, 'knownBits': {}}
    address = 0x80 + bank * 8
    parts = [frozen.candidates(state['memory'][f'{address + byte:04X}'], state['knownBits'], f'{address + byte:04X}') for byte in range(2)]
    raw = [frozen.unique(part) for part in parts]
    bits = {f'X1.{byte * 8 + int(key[-1])}': value for byte, part in enumerate(parts)
            for key, value in frozen.bit_consensus(part, 'x').items()}
    return {'dataAddress': address, 'value': None if None in raw else raw[0] | raw[1] << 8, 'knownBits': bits}


def expand(before, child):
    state = deepcopy(before)
    addresses = set(child['memory'])
    state['memory'].update(deepcopy(child['memory']))
    state['generations'].update(deepcopy(child['generations']))
    state['knownBits'] = {**{k: v for k, v in state['knownBits'].items() if k[:4] not in addresses}, **deepcopy(child['knownBits'])}
    for key in ('registers', 'registerKnownBits', 'configurationIntents'):
        if key in child:
            state[key] = deepcopy(child[key])
    state['sfrReadbacks'].update(deepcopy(child.get('sfrReadbacks', {})))
    return state


class Effects(parent.Effects):
    def __init__(self, snapshot, procedure, scope, mode=False):
        validate(snapshot, mode)
        super().__init__(project(snapshot), procedure, scope)
        self.input = deepcopy(snapshot)
        self.state = {key: deepcopy(snapshot[key]) for key in STATE_FIELDS}
        self.r = self.state['registers']
        self.specific = list(SHARED)
        self.inherited = []

    def read(self, pc, address, width=8):
        result = super().read(pc, address, width)
        self.reads[-1]['stage'] = self.procedure
        return result

    def symbolic_readback(self, pc, address):
        result = super().symbolic_readback(pc, address)
        self.reads[-1]['stage'] = self.procedure
        return result

    def step(self, pc, following, kind='Linear', taken=None):
        super().step(pc, following, kind, taken)
        self.steps[-1].update(stage=self.procedure, afterX1State=x1_view(self.state))

    def _event(self, *args):
        super()._event(*args)
        ordinal = self.journal[-1]['ordinal']
        self.journal[-1].update(stage=self.procedure, stageOrdinal=ordinal)
        self.intermediate[-1].update(stage=self.procedure, stageOrdinal=ordinal)

    def snapshot(self, entry=None):
        result = {'inputClass': self.input['inputClass'], 'assumptions': deepcopy(self.input['assumptions']),
                  **{key: deepcopy(self.state[key]) for key in STATE_FIELDS}}
        if entry is not None:
            result['entry'] = entry
        return result

    def absorb(self, child):
        before, offset = deepcopy(self.state), len(self.journal)
        stage = child['procedure']
        self.inherited.append(deepcopy(child))
        for event in child['journal']:
            self.journal.append({**deepcopy(event), 'ordinal': offset + event['ordinal'],
                                 'stage': stage, 'stageOrdinal': event['ordinal']})
        for event in child['intermediateStates']:
            self.intermediate.append({**deepcopy(event), 'afterOrdinal': offset + event['afterOrdinal'],
                'stage': stage, 'stageOrdinal': event['afterOrdinal'], 'state': expand(before, event['state'])})
        for event in child['reads']:
            self.reads.append({**deepcopy(event), 'stage': stage})
        for event in child['steps']:
            self.steps.append({**deepcopy(event), 'stage': stage,
                'afterRegisters': {**before['registers'], **deepcopy(event['afterRegisters'])},
                'afterX1State': deepcopy(event['afterX1State']) if 'afterX1State' in event else x1_view(before)})
        self.state = expand(before, child['state'])
        self.r = self.state['registers']
        for reason in child['unresolvedConstraints']:
            if reason not in (*frozen.COMMON, *self.specific):
                self.specific.append(reason)

    def byte_load_symbol(self, pc, address, following):
        if self.input['assumptions']['ordinaryByteSemantics'] is not True:
            self.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', pc)
        values = self.symbolic_readback(pc, address)
        self.set_a_byte('al', values)
        self.r.update(dd=0, zf=frozen.unique({int(v == 0) for v in values}))
        self.step(pc, following)

    def literal_a_word(self, pc, value, following):
        self.set_a_byte('al', {value & 255})
        self.set_a_byte('ah', {value >> 8})
        self.r.update(dd=1, zf=int(value == 0))
        self.step(pc, following)

    def result(self, status, reason, boundary, outcome=None):
        return {**super().result(status, reason, boundary, outcome),
                'x1State': x1_view(self.state), 'inheritedResults': deepcopy(self.inherited)}
