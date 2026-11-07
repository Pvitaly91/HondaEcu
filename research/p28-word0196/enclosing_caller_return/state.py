"""Closed DATA snapshot and adapters for the accepted M2cu effects."""
from copy import deepcopy

from mode_caller_continuity import state as previous

Boundary, need, number = previous.Boundary, previous.need, previous.number
slot, label, input_class = previous.slot, previous.label, previous.input_class
frozen = previous.frozen
DATA_KEYS = previous.DATA_KEYS | {'0209', '0217', '0219', '0227', '0230'}
READBACK_KEYS = previous.READBACK_KEYS | {'0019'}
STATE_FIELDS = previous.STATE_FIELDS
SNAPSHOT_FIELDS = {'inputClass', 'assumptions', *STATE_FIELDS}
ACTUAL = {'actualCpuExecutions': 0, 'actualCallExecution': None,
          'actualReturnExecution': None, 'actualFramePop': None, 'actualSavedPcObservation': None}
STOP = {0x5CB7: 'STOP_BEFORE_INDEXED_CONTINUATION_5CB7', 0x60E4: 'STOP_BEFORE_RT_60E4',
        0x5C89: 'STOP_BEFORE_TIMER_IE_PATH_5C89',
        0x5CCD: 'STOP_BEFORE_RT_5CCD', 0x2891: 'STOP_BEFORE_EXTERNAL_DATA_READ_2891',
        0x3FB5: 'STOP_BEFORE_BRK_3FB5', 0x3FF9: 'STOP_BEFORE_IE_WRITE_3FF9',
        0x5CD2: 'STOP_BEFORE_BRK_5CD2', 0x2995: 'STOP_BEFORE_STBUF_2995'}


def stop_name(boundary):
    if boundary is None:
        return None
    return STOP.get(boundary, f'STOP_BEFORE_PC_{boundary:04X}')


def shape(value, keys, reason):
    need(type(value) is dict and set(value) == set(keys), reason)


def tri(value):
    return value is None or type(value) is bool


def project(snapshot):
    return {**deepcopy(snapshot),
            'memory': {key: snapshot['memory'][key] for key in previous.DATA_KEYS},
            'generations': {key: snapshot['generations'][key] for key in previous.DATA_KEYS},
            'knownBits': {key: value for key, value in snapshot['knownBits'].items() if key[:4] in previous.DATA_KEYS},
            'sfrReadbacks': {key: deepcopy(snapshot['sfrReadbacks'][key]) for key in previous.READBACK_KEYS}}


def validate(snapshot):
    shape(snapshot, SNAPSHOT_FIELDS, 'ClosedEnclosingSnapshotRequired')
    shape(snapshot['memory'], DATA_KEYS, 'ExplicitEnclosingDataRequired')
    shape(snapshot['generations'], DATA_KEYS, 'ExplicitEnclosingGenerationsRequired')
    shape(snapshot['sfrReadbacks'], READBACK_KEYS, 'ExplicitEnclosingReadbacksRequired')
    need(all(number(v, 255) for v in snapshot['memory'].values()), 'TypedEnclosingDataRequired')
    need(all(label(v) for v in snapshot['generations'].values()), 'TypedEnclosingGenerationsRequired')
    bits = snapshot['knownBits']
    need(type(bits) is dict and all(type(k) is str and len(k) == 6 and k[4] == '.'
         and k[:4] in DATA_KEYS and k[5] in '01234567' and type(v) is int and v in (0, 1)
         for k, v in bits.items()), 'TypedEnclosingKnownBitsRequired')
    for key, value in bits.items():
        raw = snapshot['memory'][key[:4]]
        need(raw is None or (raw >> int(key[5])) & 1 == value, 'ContradictoryBitKnowledge')
    slot(snapshot['sfrReadbacks']['0019'])
    previous.validate(project(snapshot))


class Effects(previous.Effects):
    def __init__(self, snapshot, procedure, scope):
        validate(snapshot)
        super().__init__(project(snapshot), procedure, scope)
        self.input = deepcopy(snapshot)
        self.state = {key: deepcopy(snapshot[key]) for key in STATE_FIELDS}
        self.r = self.state['registers']

    def m2cu_snapshot(self, entry=None):
        snapshot = project(self.snapshot())
        if entry is not None:
            snapshot['entry'] = entry
        return snapshot

    def result(self, status, reason, boundary, outcome=None):
        return {**super().result(status, reason, boundary, outcome), **ACTUAL,
                'exactStopBoundary': stop_name(boundary)}


def formal_result(procedure, input_kind, scope, status, reason, boundary, state, *,
                  children=(), missing=(), edges=(), frame_obligations=()):
    """A formal relation has no performed source reads, writes or stack effects."""
    return {
        'procedure': procedure, 'inputClass': input_kind, 'sourceScope': sorted(set(scope)),
        'status': status, 'reason': reason, 'boundary': boundary, 'outcome': None,
        'exactStopBoundary': stop_name(boundary), 'state': deepcopy(state),
        'reads': [], 'journal': [], 'steps': [], 'intermediateStates': [],
        'inheritedResults': deepcopy(list(children)), 'sourceEdges': deepcopy(list(edges)),
        'frameObligations': deepcopy(list(frame_obligations)), 'unresolvedConstraints': list(missing),
        'effectClass': 'StaticFormalSourceObligation', 'executionStatus': 'EXECUTION_BLOCKED',
        'firmwareReady': False, 'cpuInstructionRetirements': 0, 'actualPeripheralOperations': 0,
        'actualHardwareObservation': None, 'actualBufferWrite': None, 'actualTransmission': None,
        'actualTxCompletion': None, 'actualTxIrqDelivery': None, 'actualPeripheralClockEvent': None,
        'stbufStopBoundary': 'STOP_BEFORE_STBUF_2995', 'stopBoundary': 'STOP_BEFORE_STBUF_2995',
        **ACTUAL,
    }
