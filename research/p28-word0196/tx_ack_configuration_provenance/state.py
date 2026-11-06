"""Distinct declared intents and symbolic readbacks, with partial software DATA knowledge."""
from copy import deepcopy
from payload_consumer_tail import state as frozen
from stbuf_stcon_transmit_source import state as accepted

Boundary, need, number = frozen.Boundary, frozen.need, frozen.number
slot, label, input_class, formal = accepted.slot, accepted.label, accepted.input_class, accepted.formal
DATA_KEYS = accepted.DATA_KEYS | frozenset(('03CB',))
BIT_FIELDS = frozenset(f'{key}.{bit}' for key in DATA_KEYS for bit in range(8))
READBACK_KEYS = frozenset(('0049', '004A', '0050', '0054'))
ACTUAL_FIELDS = accepted.ACTUAL_FIELDS


def project(snapshot):
    result = {key: deepcopy(snapshot[key]) for key in ('inputClass', 'memory', 'knownBits',
        'registers', 'generations', 'assumptions', 'registerKnownBits', 'configurationIntents')}
    for field in ('memory', 'generations'):
        result[field] = {k: result[field][k] for k in accepted.DATA_KEYS}
    result['knownBits'] = {k: v for k, v in result['knownBits'].items() if k in accepted.BIT_FIELDS}
    return result


def validate(snapshot, producer=False):
    shape = {'inputClass', 'memory', 'knownBits', 'registers', 'generations', 'assumptions',
             'registerKnownBits', 'configurationIntents', 'sfrReadbacks'}
    need(type(snapshot) is dict and set(snapshot) == (shape | {'entry'} if producer else shape),
         'ClosedReaderProducerSnapshotRequired')
    need(type(snapshot['memory']) is dict and set(snapshot['memory']) == DATA_KEYS
         and all(number(v, 255) for v in snapshot['memory'].values()), 'ExplicitFortyNineDataBytesRequired')
    need(type(snapshot['generations']) is dict and set(snapshot['generations']) == DATA_KEYS
         and all(label(v) for v in snapshot['generations'].values()), 'ExplicitFortyNineGenerationsRequired')
    bits = snapshot['knownBits']
    need(type(bits) is dict and set(bits) <= BIT_FIELDS
         and all(type(v) is int and v in (0, 1) for v in bits.values()), 'TypedPartialDataBitsRequired')
    for field, value in bits.items():
        raw = snapshot['memory'][field[:4]]
        need(raw is None or raw >> int(field[-1]) & 1 == value, 'ContradictoryBitKnowledge')
    accepted.validate(project(snapshot))
    need(type(snapshot['sfrReadbacks']) is dict and set(snapshot['sfrReadbacks']) == READBACK_KEYS,
         'FourExplicitSymbolicReadbackSlotsRequired')
    for value in snapshot['sfrReadbacks'].values():
        slot(value)
    if producer:
        need(type(snapshot['entry']) is str and snapshot['entry'] in ('Compare3cb', 'SymbolicCarryTail'),
             'ClosedProducerEntryRequired')


class Effects(frozen.Effects):
    """Mathematical bookkeeping for reviewed source windows, without a CPU instance."""

    def __init__(self, snapshot, procedure, scope, producer=False):
        validate(snapshot, producer)
        super().__init__(accepted.project(project(snapshot)), procedure, scope)
        self.input = deepcopy(snapshot)
        self.state = {k: deepcopy(snapshot[k]) for k in ('memory', 'knownBits', 'registers',
            'generations', 'registerKnownBits', 'configurationIntents', 'sfrReadbacks')}
        self.r = self.state['registers']
        self.specific = (['ConditionalModeProducerNotNativeOwner',
            'ProducerToConfigurationPathNotEstablished', 'Stbuf2995NotPerformed'] if producer else
            ['SuppliedSymbolicReadbacksNotHardwareObservations',
             'NativeConfigurationOwnerNotEstablished', 'Stbuf2995NotPerformed'])

    def admit(self, entry):
        super().admit(entry)
        prefix = 'ConditionalEffect:' + self.procedure + ':'
        if any(v['generation'] is not None and v['generation'].startswith(prefix)
               for name in ('configurationIntents', 'sfrReadbacks') for v in self.input[name].values()):
            self.halt('OutsideVerifiedScope', 'EffectNamespaceAlreadyPresent', entry)

    def step(self, pc, following, kind='Linear', taken=None):
        super().step(pc, following, kind, taken)
        self.steps[-1]['afterRegisters'] = deepcopy(self.r)

    def dp(self, pc, value, following):
        if self.r['scb'] is None:
            self.halt('OutsideVerifiedScope', 'PointerBankNotEstablished', pc)
        self.store(pc, 0x84 + 8 * self.r['scb'], [value & 255, value >> 8],
                   'PointingRegisterWrite', 'Literal')
        self.step(pc, following)

    def symbolic_readback(self, pc, address):
        row = self.state['sfrReadbacks'][f'{address:04X}']
        bits = {f'{address:04X}.{bit}': v for bit, v in row['knownBits'].items()}
        self.reads.append({'pc': pc, 'space': 'SYMBOLIC_SFR_READBACK', 'address': address,
            'widthBits': 8, 'value': row['value'], 'bytes': [row['value']], 'knownBits': bits,
            'generations': [row['generation']], 'accessRole': 'SuppliedReadbackOperand',
            'actualHardwareObservation': None})
        return frozen.candidates(row['value'], bits, f'{address:04X}')

    def compare_values(self, pc, values, literal, following):
        self.r.update(cf=frozen.unique({int(v < literal) for v in values}),
                      zf=frozen.unique({int(v == literal) for v in values}))
        self.step(pc, following)

    def result(self, status, reason, boundary, outcome=None):
        return {**super().result(status, reason, boundary, outcome), **accepted.authority(),
                'stopBoundary': 'STOP_BEFORE_STBUF_2995'}
