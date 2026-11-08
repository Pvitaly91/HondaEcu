"""Source-bounded detached ingress exclusions and correlated helper branches."""

from enclosing_caller_return.state import input_class, label, need, number, shape


SOURCE = 'M2dbHelperSourceReviewV1'
ENTRIES = {0x5CE1: 0x5CDF, 0x5CE9: 0x5CE7}
BRANCHES = {
    0x5CDF: (0x5CED, 0x5CE1),
    0x5CE3: (0x5CF9, 0x5CE5),
    0x5CE7: (0x5CED, 0x5CE9),
    0x5CEB: (0x5CF9, 0x5CED),
}
SITES = tuple(BRANCHES)
LESS, EQUAL, GREATER = (1, 0), (0, 1), (0, 0)

# Distinct branch-flag signatures, with operand bytes and class cardinalities
# omitted. All comparisons on one route use the same immutable AL input.
SIGNATURES = {
    'PrintedOr': ((EQUAL,), (LESS,)),
    'ComparativeAnd': (
        (EQUAL, GREATER),
        (LESS, GREATER),
        (LESS, EQUAL),
        (LESS, LESS, GREATER),
        (LESS, LESS, EQUAL, GREATER),
        (LESS, LESS, LESS, GREATER),
        (LESS, LESS, LESS, EQUAL),
        (LESS, LESS, LESS, LESS),
    ),
}


def helper_ingress_proof(query):
    """Exclude fixed VCAL and intact ordinary-return ingress into detached sites."""
    shape(query, ('inputClass', 'sourceBinding', 'entryPc', 'transferClass', 'claim'),
          'ClosedHelperIngressQueryRequired')
    input_class(query['inputClass'])
    entry = query['entryPc']
    transfer = query['transferClass']
    need(number(entry, 0xFFFF) and label(query['sourceBinding'])
         and transfer in ('EncodedDirect', 'VcalVector', 'OrdinaryIntactReturn', 'UnboundIndirect')
         and query['claim'] in ('Inspect', 'AssertIngress', 'NativeEnter'), 'TypedHelperIngressQueryRequired')
    predecessor = ENTRIES.get(entry)
    stop = None if predecessor is None else f'STOP_BEFORE_C8_{predecessor:04X}'
    result = {
        'entryPc': entry, 'transferClass': transfer, 'encodedPredecessor': None,
        'exclusionEstablished': None, 'examinedVectorWords': None,
        'savedContinuationCandidates': None, 'nativeIngress': None,
        'stopBoundary': stop, 'status': 'OutsideVerifiedScope', 'reason': 'DetachedEntryRequired',
    }
    if predecessor is None:
        return result
    if query['claim'] != 'Inspect':
        return {**result, 'reason': 'PositiveOrNativeIngressClaimNotAdmitted'}
    if query['sourceBinding'] != SOURCE:
        return {**result, 'status': 'IndeterminateObligation', 'reason': 'HelperSourceBindingRequired'}
    result['encodedPredecessor'] = predecessor
    if transfer == 'VcalVector':
        return {**result, 'status': 'CompleteConditional', 'reason': 'FixedVcalTableExcludesEntry',
                'exclusionEstablished': True, 'examinedVectorWords': 8}
    if transfer == 'OrdinaryIntactReturn':
        return {**result, 'status': 'CompleteConditional', 'reason': 'NoReviewedCallEndsAtEntry',
                'exclusionEstablished': True, 'savedContinuationCandidates': 0}
    reason = ('EncodedC8FallthroughUnresolved' if transfer == 'EncodedDirect'
              else 'UnboundIndirectIngressUnresolved')
    return {**result, 'status': 'IndeterminateObligation', 'reason': reason}


def _route(interpretation, signature):
    branch_flags = []
    for pc, (cf, zf) in zip(SITES, signature):
        target, fallthrough = BRANCHES[pc]
        if pc in (0x5CE3, 0x5CEB):
            taken = cf == 0
        elif interpretation == 'PrintedOr':
            taken = cf == 0 or zf == 0
        else:
            taken = cf == 0 and zf == 0
        branch_flags.append({'pc': pc, 'cf': cf, 'zf': zf, 'taken': taken,
                             'nextPc': target if taken else fallthrough})
    frontier = branch_flags[-1]['nextPc']
    return {'branchFlags': branch_flags, 'frontier': (
        'STOP_BEFORE_RT_5CF9' if frontier == 0x5CF9 else 'STOP_BEFORE_ERROR_MARKER_5CED')}


def _consistent(signature, observations):
    for item in observations:
        site = SITES.index(item['pc'])
        if site >= len(signature):
            return False
        if any(item[key] is not None and item[key] != value
               for key, value in zip(('cf', 'zf'), signature[site])):
            return False
    return True


def helper_normal_feasibility(query):
    """Intersect ordered flag observations with source-qualified same-AL routes."""
    shape(query, ('inputClass', 'sourceBinding', 'observations', 'claim'), 'ClosedHelperFeasibilityQueryRequired')
    input_class(query['inputClass'])
    observations = query['observations']
    need(label(query['sourceBinding']) and query['claim'] in ('Inspect', 'ResolveOr', 'ResolveAnd', 'AssertFullNormal')
         and type(observations) is list and len(observations) <= len(SITES), 'TypedHelperFeasibilityQueryRequired')
    for item in observations:
        shape(item, ('pc', 'cf', 'zf'), 'ClosedHelperFlagObservationRequired')
        need(number(item['pc'], 0xFFFF) and number(item['cf'], 1) and number(item['zf'], 1),
             'TypedHelperFlagObservationRequired')
    observed_sites = [item['pc'] for item in observations]
    result = {
        'firstUnresolvedBranchPc': 0x5CDF, 'hypotheses': [], 'fullNormalProven': False,
        'nativeBranchTaken': None, 'stopBoundary': 'STOP_BEFORE_C8_5CDF',
        'status': 'OutsideVerifiedScope', 'reason': 'OrderedUniqueReviewedBranchObservationsRequired',
    }
    if observed_sites != [pc for pc in SITES if pc in observed_sites]:
        return result
    if query['claim'] != 'Inspect':
        return {**result, 'reason': 'C8OrFullNormalClaimNotAdmitted'}
    if query['sourceBinding'] != SOURCE:
        return {**result, 'status': 'IndeterminateObligation', 'reason': 'HelperSourceBindingRequired'}
    hypotheses = [
        {'interpretation': interpretation, 'routes': [_route(interpretation, signature) for signature in signatures
                                                     if _consistent(signature, observations)]}
        for interpretation, signatures in SIGNATURES.items()
    ]
    if not any(hypothesis['routes'] for hypothesis in hypotheses):
        return {**result, 'hypotheses': hypotheses, 'reason': 'NoCorrelatedSourceRoute'}
    return {**result, 'hypotheses': hypotheses, 'status': 'IndeterminateBranch',
            'reason': 'C8PrimaryConflictUnresolved'}
