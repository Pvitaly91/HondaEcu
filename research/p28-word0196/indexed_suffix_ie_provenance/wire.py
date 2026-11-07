"""Closed public wire for the M2cx conditional software models."""
from copy import deepcopy
from types import MappingProxyType

from enclosing_caller_return.analysis import AUTHORITY as INHERITED, canonical

BASE = 'e072dd9cf2ff68bacd3ea8353decae9ff55b7383'
AUTHORITY = MappingProxyType({**INHERITED, **dict.fromkeys((
    'actualHardwareObservation', 'actualIeWrite', 'actualIrqDelivery', 'actualCallExecution',
    'actualReturnExecution', 'actualFramePop', 'actualBufferWrite', 'actualTransmission',
)), 'actualCpuExecutions': 0})
APPLICABILITY = 'ConditionalSoftwareOnly_HardwareApplicabilityUnestablished'
SOURCE_IDENTITIES = MappingProxyType({
    'm2cwBase': BASE,
    'm2cvFrameReview': '7e4ba87467d98becfeff774b92bfdf2c3aeca07e88baf7b713fd9aafba14c9f8',
    'm2cwSourceBinding': '912c5fc8fc26dc06fe21b83c96fc81a17875292b682d1f9d3a812d2926098ae7',
    'primaryIsa': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
})


def result(status, *, source_scope, evidence_class='ConditionalSourceModel', state=None, stop=None,
           reads=(), writes=(), generations=None, intermediate=(), obligations=(), unresolved=(),
           branches=(), **details):
    fixed = {
        'status': status, 'sourceScope': list(source_scope), 'sourceIdentities': dict(SOURCE_IDENTITIES),
        'evidenceClass': evidence_class, 'applicability': APPLICABILITY,
        'state': state, 'branchOutcome': list(branches), 'reads': list(reads),
        'orderedWrites': list(writes), 'generations': generations, 'intermediateStates': list(intermediate),
        'formalObligations': list(obligations), 'unresolvedConstraints': list(unresolved),
        'stopBoundary': stop, **AUTHORITY,
    }
    if set(fixed) & set(details):
        raise ValueError('ReservedOutputField')
    return deepcopy({**fixed, **details})


RECORD_FIELDS = ('sourceScope', 'sourceIdentities', 'evidenceClass', 'applicability', 'state', 'branchOutcome',
                 'reads', 'orderedWrites', 'generations', 'intermediateStates', 'formalObligations',
                 'unresolvedConstraints', 'stopBoundary')
