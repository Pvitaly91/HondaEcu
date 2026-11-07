"""Closed canonical result shared by M2cz research functions."""
from copy import deepcopy
from types import MappingProxyType

from shadow_cold_reacquisition.wire import AUTHORITY, canonical

BASE = '83ffa492a1565d15c4f8b32f180e34e884e431ac'
APPLICABILITY = 'ConditionalSoftwareOnly_HardwareApplicabilityUnestablished'
SOURCE_IDENTITIES = MappingProxyType({
    'm2cyBase': BASE,
    'm2cySourceBinding': '76d257b263d8b9226ce28cec4c50109c78f2b037be1959d30a5bff45a2861f83',
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
