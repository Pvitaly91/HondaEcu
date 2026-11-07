"""Closed, public-safe M2cy result projection."""
from copy import deepcopy
from types import MappingProxyType

from indexed_suffix_ie_provenance.wire import AUTHORITY, canonical

BASE = '9786bdfe136741e3930e7d4088bdc28565ee7f08'
APPLICABILITY = 'ConditionalSoftwareOnly_HardwareApplicabilityUnestablished'
SOURCE_IDENTITIES = MappingProxyType({
    'm2cxBase': BASE,
    'm2cxSourceBinding': 'ab376194f261c60a47ab4881849abed3cd2e25a4a680c603ef900012098e9ff7',
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
