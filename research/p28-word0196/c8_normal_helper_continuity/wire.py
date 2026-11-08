"""Canonical M2da result wire with inherited execution restrictions."""
from copy import deepcopy
from types import MappingProxyType

from cold_return_c8_writer_proof.wire import AUTHORITY, canonical

BASE = '9d0547a312162a9d2509bf3db1a23a018c5cc008'
APPLICABILITY = 'ConditionalSoftwareOnly_HardwareApplicabilityUnestablished'
SOURCE_IDENTITIES = MappingProxyType({
    'm2czBase': BASE,
    'm2czSourceBinding': '68a2ee3219946c178929e365ac7c8ab01feaecc47f4c9533e0b364cd07866c34',
    'primaryIsa': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
})
RECORD_FIELDS = ('sourceScope', 'sourceIdentities', 'evidenceClass', 'applicability', 'caller', 'iterations',
                 'state', 'branchOutcome', 'reads', 'orderedWrites', 'generations', 'intermediateStates',
                 'formalObligations', 'unresolvedConstraints', 'stopBoundary')


def result(status, *, source_scope, evidence_class='ConditionalSourceModel', state=None, stop=None,
           reads=(), writes=(), generations=None, intermediate=(), obligations=(), unresolved=(),
           branches=(), caller=None, iterations=(), **details):
    fixed = {'status': status, 'sourceScope': list(source_scope), 'sourceIdentities': dict(SOURCE_IDENTITIES),
             'evidenceClass': evidence_class, 'applicability': APPLICABILITY, 'caller': caller,
             'iterations': list(iterations), 'state': state, 'branchOutcome': list(branches),
             'reads': list(reads), 'orderedWrites': list(writes), 'generations': generations,
             'intermediateStates': list(intermediate), 'formalObligations': list(obligations),
             'unresolvedConstraints': list(unresolved), 'stopBoundary': stop, **AUTHORITY}
    if set(fixed) & set(details):
        raise ValueError('ReservedOutputField')
    return deepcopy({**fixed, **details})
