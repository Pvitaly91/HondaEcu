"""Adjudicate documented branch authorities and carry the detached helper state."""
from copy import deepcopy
from types import MappingProxyType

from cold_return_c8_writer_proof.c8_helper import helper_5cd9_extended
from enclosing_caller_return.state import frozen, input_class, label, need, number, shape, tri
from shadow_cold_reacquisition.cold_reacquisition import projected_generations
from shadow_cold_reacquisition.helper_5cd9 import HELPER_SCOPE

from .wire import result

SOURCE = 'M2daHelperSourceReviewV1'
COMPLETE = 'CompleteConditional'
UNKNOWN = 'IndeterminateObligation'
OUTSIDE = 'OutsideVerifiedScope'
PREDICATES = ('PrintedOr', 'ComparativeAnd')
SOURCE_CLASSES = MappingProxyType({
    'OKI66201Sep1991': 'ExactOpcodePrintedPredicate',
    'SameEditionMirror': 'SameManufacturerLineage',
    'Chapter3WithoutEdition': 'UnattributedInstructionChapter',
    'OKI1998InstructionList': 'ApplicableMnemonicOnly',
    'OKIJapanSpec1998': 'DeviceScopeOnly',
    'MAC66KNov1993': 'AssemblerMnemonicOnly',
    'OKI500S1999': 'DifferentOpcodeComparativeOnly',
    'UnauthenticatedErratum': 'UnverifiedSource',
    'EmulatorBehavior': 'NonPrimaryObservation',
})
C8_GAPS = ('ExactC8CorrectionUnbound', 'NativeC8PredicateUnestablished')
INGRESS_GAPS = ('C8FallthroughUnresolved', 'IndirectAndReturnIngressUnbound')
HELPER_GAPS = ('NativeHelperEntryUnobserved', 'FullHelperNormalReachUnbound', 'NativeRt5cf9Unobserved')
SITES = MappingProxyType({
    0x5CDF: (0x5CED, 0x5CE1), 0x5CE3: (0x5CF9, 0x5CE5),
    0x5CE7: (0x5CED, 0x5CE9), 0x5CEB: (0x5CF9, 0x5CED),
})
BOUNDARIES = MappingProxyType({
    0x5CDF: 'STOP_BEFORE_JGT_5CDF', 0x5CE3: 'STOP_BEFORE_JGE_5CE3',
    0x5CE7: 'STOP_BEFORE_JGT_5CE7', 0x5CEB: 'STOP_BEFORE_JGE_5CEB',
})
C8_SITES = (0x5CDF, 0x5CE7)
ALL_COMPARE_PAIRS = ((0, 0), (0, 1), (1, 0))
FIRST_COMPARE_PAIRS = ((0, 1), (1, 0))
ENTRIES = MappingProxyType({'Full': 0x5CD9, 'Detached5CE1': 0x5CE1, 'Detached5CE9': 0x5CE9})


def c8_primary_evidence_adjudication(query):
    """Keep exact documented wording separate from authority to resolve C8."""
    shape(query, ('inputClass', 'sourceIds', 'claim'), 'ClosedPrimaryC8EvidenceQueryRequired')
    input_class(query['inputClass'])
    ids, claim = query['sourceIds'], query['claim']
    need(type(ids) is list and len(ids) <= len(SOURCE_CLASSES)
         and all(type(item) is str and label(item) for item in ids) and len(set(ids)) == len(ids),
         'BoundedDistinctC8SourceIdsRequired')
    need(claim in ('KeepConflict', 'ResolveOr', 'ResolveAnd', 'NativeExecute'), 'TypedC8AuthorityClaimRequired')
    exact = 'OKI66201Sep1991' in ids
    state = {'sourceClasses': [{'id': item, 'class': SOURCE_CLASSES.get(item, 'UnreviewedSource')}
                               for item in ids],
             'architecturalOpcode': 0xC8 if exact else None,
             'documentedPredicate': 'PrintedOr' if exact else None,
             'retainedHypotheses': list(PREDICATES), 'resolvedPredicate': None}
    if claim == 'NativeExecute':
        status, reason = OUTSIDE, 'NativeC8AuthorityForbidden'
    elif any(item not in SOURCE_CLASSES for item in ids):
        status, reason = OUTSIDE, 'UnreviewedC8EvidenceId'
    elif claim != 'KeepConflict':
        status, reason = OUTSIDE, 'C8ResolutionUnsupported'
    elif not exact:
        status, reason = UNKNOWN, 'ApplicablePrimaryC8SourceMissing'
    else:
        status, reason = COMPLETE, 'PrimaryConflictRetained'
    return result(status, source_scope=C8_SITES, evidence_class='DocumentAuthorityReview', state=state,
                  stop=BOUNDARIES[0x5CDF], obligations=('ExactCoreOpcodeAndEdition', 'IndependentPredicateAuthority'),
                  unresolved=C8_GAPS, reason=reason)


def _flag_domain(pc, hypothesis):
    if pc == 0x5CDF:
        return FIRST_COMPARE_PAIRS
    if hypothesis == 'PrintedOr':
        return ()
    return ALL_COMPARE_PAIRS


def _takes(pc, hypothesis, cf, zf):
    if pc not in C8_SITES:
        return cf == 0
    if hypothesis == 'PrintedOr':
        return cf == 0 or zf == 0
    return cf == 0 and zf == 0


def c8_source_feasibility(query):
    """Filter reviewed feasible flag domains without releasing their source operands."""
    shape(query, ('inputClass', 'sourceBinding', 'pc', 'target', 'fallthrough', 'cf', 'zf', 'hypothesis'),
          'ClosedSourceFeasibilityQueryRequired')
    input_class(query['inputClass'])
    pc, target, fallthrough = (query[name] for name in ('pc', 'target', 'fallthrough'))
    cf, zf, hypothesis = query['cf'], query['zf'], query['hypothesis']
    need(all(number(value, 0xFFFF) for value in (pc, target, fallthrough)) and number(cf, 1) and number(zf, 1)
         and label(query['sourceBinding']) and hypothesis in (*PREDICATES, 'Both'), 'TypedSourceFeasibilityRequired')
    domains = []
    if query['sourceBinding'] != SOURCE:
        status, reason = UNKNOWN, 'ExactFeasibilitySourceRequired'
    elif SITES.get(pc) != (target, fallthrough):
        status, reason = OUTSIDE, 'FeasibilityBranchIdentityMismatch'
    else:
        for variant in PREDICATES if hypothesis == 'Both' else (hypothesis,):
            rows = []
            for carry, zero in _flag_domain(pc, variant):
                if (cf is None or carry == cf) and (zf is None or zero == zf):
                    taken = _takes(pc, variant, carry, zero)
                    rows.append({'cf': carry, 'zf': zero, 'taken': taken, 'next': target if taken else fallthrough})
            domains.append({'hypothesis': variant, 'rows': rows})
        if any(domain['rows'] for domain in domains):
            status, reason = COMPLETE, 'ReviewedFlagDomain'
        else:
            status, reason = UNKNOWN, 'FlagPairOrIngressUnreachable'
    state = {'sitePc': pc, 'domains': domains, 'comparisonWidthBits': 8,
             'flagsRead': ['CF', 'ZF'] if pc in C8_SITES else ['CF'] if pc in SITES else [],
             'flagsWritten': [], 'nativeBranchTaken': None, 'commonFirstC8RouteEstablished': False}
    return result(status, source_scope=tuple(SITES), evidence_class='RedactedSourceFlagDomain', state=state,
                  stop=BOUNDARIES.get(pc, 'STOP_BEFORE_UNBOUND_HELPER_BRANCH'),
                  obligations=('ExhaustivePrivateByteDomainReview', 'NoChoiceBetweenC8Hypotheses'),
                  unresolved=C8_GAPS, reason=reason)


def helper_normal_entry_provenance(query):
    """Expose the sole reviewed encoded ingress to each detached compare."""
    shape(query, ('inputClass', 'entryPc', 'predecessorPc', 'sourceBinding', 'claim'),
          'ClosedHelperIngressQueryRequired')
    input_class(query['inputClass'])
    entry, predecessor = query['entryPc'], query['predecessorPc']
    need(number(entry, 0xFFFF) and number(predecessor, 0xFFFF) and label(query['sourceBinding'])
         and query['claim'] in ('Inspect', 'NativeEnter', 'AssertAlternate'), 'TypedHelperIngressRequired')
    expected = entry - 2 if entry in (0x5CE1, 0x5CE9) else None
    reviewed = expected is not None and query['sourceBinding'] == SOURCE
    if query['claim'] != 'Inspect':
        status, reason = OUTSIDE, 'UnadmittedIngressClaim'
    elif expected is None or (predecessor is not None and predecessor != expected):
        status, reason = OUTSIDE, 'EncodedPredecessorMismatch'
    elif not reviewed:
        status, reason = UNKNOWN, 'ExactIngressSourceRequired'
    else:
        status, reason = UNKNOWN, 'OnlyConflictedEncodedFallthrough'
    state = {'entryPc': entry, 'encodedPredecessor': expected if reviewed else None,
             'alternateDirectEdges': [] if reviewed else None,
             'reviewedExtents': 11499 if reviewed else None,
             'confirmedFullIngress': False, 'nativeEntry': None}
    return result(status, source_scope=(0x5CDF, 0x5CE1, 0x5CE7, 0x5CE9), evidence_class='EncodedIngressReview',
                  state=state, stop=BOUNDARIES.get(expected, 'STOP_BEFORE_UNBOUND_HELPER_ENTRY'),
                  obligations=('ExcludesOnlyReviewedDirectTargets', 'RequiresSeparateDetachedHandoff'),
                  unresolved=INGRESS_GAPS, reason=reason)


def helper_normal_continuation(query):
    """Carry the exact prefix across only explicitly detached software frontiers."""
    shape(query, ('inputClass', 'sourceBinding', 'entry', 'entryHandoff', 'prefixHandoff', 'helperQuery'),
          'ClosedNormalHelperQueryRequired')
    input_class(query['inputClass'])
    entry = query['entry']
    entry_handoff, prefix_handoff = query['entryHandoff'], query['prefixHandoff']
    child_query = query['helperQuery']
    need(type(entry) is str and entry in ENTRIES and label(query['sourceBinding'])
         and tri(entry_handoff) and tri(prefix_handoff) and type(child_query) is dict
         and child_query.get('inputClass') == query['inputClass'], 'TypedNormalHelperQueryRequired')
    child = state = None
    branches, reads, writes, states, obligations = [], [], [], [], []
    candidate_pairs = []

    def finish(status, reason, stop, *, normal=False):
        return result(status, source_scope=HELPER_SCOPE, caller=0x2777,
                      state=state, stop=stop, branches=branches, reads=reads, writes=writes,
                      intermediate=states, obligations=obligations, generations=projected_generations(state),
                      unresolved=HELPER_GAPS, reason=reason, entry=entry, candidatePairs=candidate_pairs,
                      detachedNormalFrontier=normal, fullNormalFrontier=False, frozenHelperResult=child)

    if query['sourceBinding'] != SOURCE:
        return finish(UNKNOWN, 'ExactHelperContinuitySourceRequired', 'STOP_BEFORE_HELPER_5CD9')
    if entry == 'Full' and (entry_handoff is not None or prefix_handoff is not None):
        return finish(OUTSIDE, 'DetachedHandoffCannotQualifyFullEntry', 'STOP_BEFORE_HELPER_5CD9')
    if entry == 'Detached5CE1' and prefix_handoff is not None:
        return finish(OUTSIDE, 'SecondStagePremiseOutOfScope', 'STOP_BEFORE_JGT_5CDF')
    child_entry = 'Full' if entry == 'Full' else 'Detached5CE1'
    handoff = None if entry == 'Full' else entry_handoff if entry == 'Detached5CE1' else prefix_handoff
    child = helper_5cd9_extended({'entry': child_entry, 'detachedHandoff': handoff, 'helperQuery': child_query})
    state = deepcopy(child['state'])
    branches, reads, writes, states, obligations = (deepcopy(child[name]) for name in (
        'branchOutcome', 'reads', 'orderedWrites', 'intermediateStates', 'formalObligations'))
    boundary = child['stopBoundary']
    if entry != 'Detached5CE9':
        return finish(child['status'], child['reason'], boundary, normal=child['detachedNormalFrontier'])
    if boundary != 'STOP_BEFORE_JGT_5CE7' or entry_handoff is not True:
        return finish(UNKNOWN, 'SecondDetachedIngressUnestablished', boundary)
    if not any(row['comparativeAnd'] is False for row in branches[-1]['candidateRows']):
        return finish(OUTSIDE, 'SecondC8FallthroughContradictsInputDomain', boundary)

    # This is a conditional AL domain, not a register write or a chosen C8
    # outcome. All observed register and writer identities come from the child.
    values = frozen.candidates(state['registers']['al'], state['registerKnownBits'], 'AL')
    previous_comparand = child_query['thresholds']['5CE5']
    if previous_comparand is not None:
        values = {value for value in values if value <= previous_comparand}
    right = child_query['thresholds']['5CE9']
    comparands = range(256) if right is None else (right,)
    pairs = {(int(left < rhs), int(left == rhs)) for left in values for rhs in comparands}
    state['registers'].update(cf=frozen.unique({cf for cf, _ in pairs}), zf=frozen.unique({zf for _, zf in pairs}))
    states.append({'pc': 0x5CE9, 'state': deepcopy(state)})
    candidate_pairs = [{'cf': cf, 'zf': zf} for cf, zf in sorted(pairs)]
    taken = frozen.unique({cf == 0 for cf, _ in pairs})
    branches.append({'pc': 0x5CEB, 'taken': taken,
                     'next': None if taken is None else 0x5CF9 if taken else 0x5CED})
    if taken is None:
        return finish('IndeterminateBranch', 'SecondDetachedJgePredicateUnknown', BOUNDARIES[0x5CEB])
    if taken:
        return finish(COMPLETE, 'SecondDetachedJgeNormalFrontier', 'STOP_BEFORE_RT_5CF9', normal=True)
    return finish(COMPLETE, 'SecondDetachedJgeErrorFrontier', 'STOP_BEFORE_ERROR_MARKER_5CED')
