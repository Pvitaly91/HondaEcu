"""Independent, static source equations and frozen reference composition for M2da."""

from copy import deepcopy

from cold_return_c8_writer_proof import reference_oracle as accepted
from enclosing_caller_return import reference_oracle as enclosing
from mode_middle_corridor import reference_oracle as mode
from shadow_cold_reacquisition import reference_oracle as cold


BASE = '9d0547a312162a9d2509bf3db1a23a018c5cc008'
SOURCE_IDENTITIES = {
    'm2czBase': BASE,
    'm2czSourceBinding': '68a2ee3219946c178929e365ac7c8ab01feaecc47f4c9533e0b364cd07866c34',
    'primaryIsa': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
}
AUTHORITY = accepted.AUTHORITY
canonical = accepted.canonical
RECORD_FIELDS = ('sourceScope', 'sourceIdentities', 'evidenceClass', 'applicability', 'caller', 'iterations',
                 'state', 'branchOutcome', 'reads', 'orderedWrites', 'generations', 'intermediateStates',
                 'formalObligations', 'unresolvedConstraints', 'stopBoundary')
COMPLETE, UNKNOWN, OUTSIDE = 'CompleteConditional', 'IndeterminateObligation', 'OutsideVerifiedScope'


def _result(scope, status, *, caller=None, iterations=(), state=None, stop=None,
            evidence='ConditionalSourceModel', reads=(), writes=(), generations=None, states=(),
            obligations=(), unresolved=(), branches=(), **details):
    return deepcopy(dict(
        status=status, sourceScope=list(scope), sourceIdentities=SOURCE_IDENTITIES,
        evidenceClass=evidence, applicability='ConditionalSoftwareOnly_HardwareApplicabilityUnestablished',
        caller=caller, iterations=list(iterations), state=state, branchOutcome=list(branches),
        reads=list(reads), orderedWrites=list(writes), generations=generations, intermediateStates=list(states),
        formalObligations=list(obligations), unresolvedConstraints=list(unresolved), stopBoundary=stop,
        **AUTHORITY, **details,
    ))


FRAME_SCOPE = (0x276A, 0x276D, 0x2777, 0x277A, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CF9)
FRAME_GAPS = ('NoNativeIeAuthority', 'NoNativeCallOrReturn')
PHASE_NAMES = ('IndexedLive', 'BetweenCalls', 'HelperLive')
PHASE_STOP = ('STOP_BEFORE_RT_5CCD', 'STOP_BEFORE_CAL_2777', 'STOP_BEFORE_RT_5CF9')


def _frames(events, indexed, helper, used):
    """Walk half-open writes against the live word, where the call owns it."""
    previous = 0
    checked = []
    for event in events:
        phase = PHASE_NAMES.index(event['stage'])
        if phase < previous:
            return OUTSIDE, 'FrameWritePhaseOrderMismatch', previous, checked
        previous = phase
        reaches = event['pathEstablished']
        address = event['address']
        owner = event['generation']
        if reaches is False:
            continue
        if reaches is not True or address is None or owner is None:
            return UNKNOWN, 'CompetingFrameWriteUnqualified', phase, checked
        if owner in used:
            return OUTSIDE, 'FrameWindowGenerationReused', phase, checked
        used.add(owner)
        width = event['widthBits']
        start = address - address % 2 if width == 16 else address
        bytes_written = frozenset(range(start, start + width // 8))
        if bytes_written.intersection((*range(8), *range(0x80, 0xC0), 0x4700)):
            return OUTSIDE, 'FrameWindowControlAlias', phase, checked
        word = (indexed, None, helper)[phase]
        if phase == 2 and word is None:
            return UNKNOWN, 'HelperLiveFrameAddressUnknown', phase, checked
        if word is not None and bytes_written.intersection((word, word + 1)):
            return OUTSIDE, 'LiveFrameGenerationOverwritten', phase, checked
        checked.append(dict(stage=event['stage'], alignedAddress=start, widthBits=width,
                            generation=owner, liveFrameOverlap=False))
    return None, None, None, checked


def cold_frame_generation_chain(query):
    state = dict(formalIndexedPc=None, formalHelperPc=None, sameAlignedAddress=None,
                 indexedAddress=None, helperAddress=None, nativeContinuity=None)
    child = None
    checked = []

    def emit(status, reason, stop):
        return _result(FRAME_SCOPE, status, caller=0x276A, state=state, stop=stop,
                       evidence='StaticFormalSourceObligation', states=checked,
                       generations=child['generations'] if child else None,
                       obligations=child['formalObligations'] if child else (),
                       unresolved=FRAME_GAPS if status == COMPLETE else (*FRAME_GAPS, reason),
                       reason=reason, frozenFrameResult=child)

    if query['claim'] != 'ConditionalOnly':
        return emit(OUTSIDE, 'NonConditionalFrameChainClaim', 'STOP_BEFORE_CAL_276A')
    for key, reason, boundary in (
            ('ie5cb9', 'FirstIeSoftwareHandoffUnestablished', 'STOP_BEFORE_IE_WRITE_5CB9'),
            ('ie5ccb', 'SecondIeSoftwareHandoffUnestablished', 'STOP_BEFORE_IE_WRITE_5CCB')):
        if query[key] is not True:
            return emit(UNKNOWN, reason, boundary)
    child = accepted.cold_return_path_obligations(query['frameQuery'])
    if child['state']['formalIndexedPc'] != 0x276D:
        return emit(child['status'], child['reason'], child['stopBoundary'])
    destinations = {row['pc']: row['address'] for row in child['formalObligations']
                    if row['kind'] == 'FormalCalWordStore'}
    indexed, helper = destinations[0x276A], destinations.get(0x2777)
    state.update(indexedAddress=indexed, helperAddress=helper,
                 sameAlignedAddress=None if helper is None else indexed == helper)
    status, reason, phase, checked = _frames(query['writes'], indexed, helper, set(child['generations'].values()))
    if phase != 0:
        state['formalIndexedPc'] = 0x276D
    if phase is not None:
        return emit(status, reason, PHASE_STOP[phase])
    if child['status'] != COMPLETE:
        return emit(child['status'], child['reason'], child['stopBoundary'])
    state['formalHelperPc'] = 0x277A
    return emit(COMPLETE, 'SeparateFrameGenerationsRetained', PHASE_STOP[2])


GRAPH_SITES = (0x276A, 0x276D, 0x2771, 0x2777, 0x277A, 0x27B2, 0x27D0, 0x5CB4,
               0x5CB7, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CD9, 0x5CDF, 0x5CF9, 0x5F45, 0x60CC)
GRAPH_GAPS = ('C8SourceConflictRetained', 'NormalFullEntryHelperUnbound', 'Native60ccUnbound')
WINDOW_REFUSALS = frozenset(('FrameWritePhaseOrderMismatch', 'CompetingFrameWriteUnqualified',
                            'FrameWindowGenerationReused', 'FrameWindowControlAlias',
                            'HelperLiveFrameAddressUnknown', 'LiveFrameGenerationOverwritten'))


def _source_edges(origin, retained, matched):
    facts = (
        (0x5CB4, 0x5CB7, 'ReachingDefinitionCandidate', 'Index5Writer', None, origin, None,
         None, 'FrozenIndex5Writer' if origin is None else None, 'STOP_BEFORE_IE_WRITE_5CB9'),
        (0x5CCD, 0x276D, 'FormalFrameObligation', 'TwoHypotheticalIeHandoffs', retained, retained,
         'CAL276A', True if matched else None, None if matched else 'ExactIndexedFrame', PHASE_STOP[0]),
        (0x2777, 0x5CD9, 'ConfirmedStaticCFG', 'QualifiedColdExitAndEntry', None, None,
         'CAL2777', None, 'ActualEntryOwner', 'STOP_BEFORE_JGT_5CDF'),
        (0x5CDF, 0x5CF9, 'PrimarySourceConflict', 'IndependentNormalIngress', None, None,
         None, None, 'SourceQualifiedNormalIngress', 'STOP_BEFORE_JGT_5CDF'),
        (0x5CF9, 0x277A, 'FormalFrameObligation', 'NormalHelperFrontier', None, None,
         'CAL2777', None, 'FullEntryNormalPath', PHASE_STOP[2]),
        (0x277A, 0x27B2, 'DetachedConditionalEntry', 'ColdCorridorAndUspOwner', None, None,
         None, None, 'ConnectedHelperReturn', 'STOP_BEFORE_USP_STORE_27B2'),
        (0x27D0, 0x5F45, 'ConfirmedStaticCFG', 'ModeCallTarget', None, None,
         'CAL27D0', None, 'ConnectedColdCorridor', 'STOP_BEFORE_CAL_27D0'),
        (0x5F45, 0x60CC, 'NativeContinuityBlocked', 'ModeBranchAndGeneration', None, None,
         'CAL27D0', None, 'ConnectedModeEntry', 'STOP_BEFORE_UNBOUND_MODE_READ_60CC'),
    )
    fields = ('from', 'to', 'evidenceClass', 'predicate', 'inputGeneration', 'outputGeneration',
              'frameRequirement', 'noInterference', 'missingProof', 'stopBoundary')
    return [dict(zip(fields, fact, strict=True)) for fact in facts]


def cold_normal_mode_source_join(query):
    join = chain = generation = None
    matched = retain = False
    stop = 'STOP_BEFORE_CAL_276A'
    status, reason = OUTSIDE, 'NonConditionalModeJoinClaim'
    if query['claim'] == 'ConditionalOnly':
        join = accepted.cold_caller_mode_source_join(query['joinQuery'])
        step = join['frozenColdResult'] or {}
        acquisition = step.get('frozenAcquisition') or {}
        seed = acquisition.get('frozenPrefixResult') or {}
        stop = join['stopBoundary']
        if seed.get('conditionalData03cbWriterEstablished') is not True:
            status, reason, retain = UNKNOWN, 'Index5WriterUnestablished', True
        else:
            generation = seed['state']['generations']['03CB']
            indexed = step['frozenIndexedFrame'] or {}
            owner = (indexed.get('state') or {}).get('formalReturnedPc')
            if generation != query['requestedGeneration']:
                status, reason = UNKNOWN, 'RequestedColdGenerationUnlinked'
                stop = 'STOP_BEFORE_INDEXED_CONTINUATION_5CB7'
            elif owner != 0x276D:
                status, reason, retain = join['status'], join['reason'], True
            elif query['frameChain'] is None:
                status, reason, stop = UNKNOWN, 'SeparateFrameWindowRequired', PHASE_STOP[0]
            else:
                chain = cold_frame_generation_chain(query['frameChain'])
                if chain['state']['formalIndexedPc'] != 0x276D:
                    status, reason, stop = chain['status'], chain['reason'], chain['stopBoundary']
                elif (chain['frozenFrameResult'] or {}).get('indexedFrameResult') != indexed:
                    status, reason, stop = OUTSIDE, 'IndexedFrameGenerationOrGeometryMismatch', PHASE_STOP[0]
                else:
                    matched = True
                    overlapping = next((event for event in chain['intermediateStates']
                                        if 0x03CB in range(event['alignedAddress'],
                                                          event['alignedAddress'] + event['widthBits'] // 8)), None)
                    if chain['reason'] in WINDOW_REFUSALS:
                        status, reason, limit = chain['status'], chain['reason'], chain['stopBoundary']
                    elif overlapping:
                        status, reason = UNKNOWN, 'FrameWindowWriterReplacesData03cb'
                        limit = PHASE_STOP[PHASE_NAMES.index(overlapping['stage'])]
                    else:
                        status, reason, limit, retain = join['status'], join['reason'], stop, True
                    if limit != PHASE_STOP[2]:
                        stop = limit
    carried = join if retain else {}
    verified = generation if retain and query['requestedGeneration'] == generation else None
    return _result(GRAPH_SITES, status, caller=0x276A, state=carried.get('state'), stop=stop,
                   reads=carried.get('reads', ()), writes=carried.get('orderedWrites', ()),
                   generations=carried.get('generations'), states=carried.get('intermediateStates', ()),
                   branches=carried.get('branchOutcome', ()), obligations=carried.get('formalObligations', ()),
                   iterations=carried.get('iterations', ()), unresolved=(*GRAPH_GAPS, reason), reason=reason,
                   sourceEdges=_source_edges(generation, verified, matched), localWriterGeneration=generation,
                   nativeModeOwner=None, connectedModeRead=False, frozenColdJoin=join, frameChainResult=chain)


HELPER_SOURCE = 'M2daHelperSourceReviewV1'
C8_GAPS = ('ExactC8CorrectionUnbound', 'NativeC8PredicateUnestablished')
HELPER_GAPS = ('NativeHelperEntryUnobserved', 'FullHelperNormalReachUnbound', 'NativeRt5cf9Unobserved')
C8_AUTHORITY_CLASS = dict((source, classification) for source, classification in (
    ('OKI66201Sep1991', 'ExactOpcodePrintedPredicate'),
    ('SameEditionMirror', 'SameManufacturerLineage'),
    ('Chapter3WithoutEdition', 'UnattributedInstructionChapter'),
    ('OKI1998InstructionList', 'ApplicableMnemonicOnly'),
    ('OKIJapanSpec1998', 'DeviceScopeOnly'),
    ('MAC66KNov1993', 'AssemblerMnemonicOnly'),
    ('OKI500S1999', 'DifferentOpcodeComparativeOnly'),
    ('UnauthenticatedErratum', 'UnverifiedSource'),
    ('EmulatorBehavior', 'NonPrimaryObservation'),
))
HELPER_EDGES = {0x5CDF: (0x5CED, 0x5CE1), 0x5CE3: (0x5CF9, 0x5CE5),
                0x5CE7: (0x5CED, 0x5CE9), 0x5CEB: (0x5CF9, 0x5CED)}
COMPARES = frozenset(((0, 0), (0, 1), (1, 0)))
SOURCE_CMP = {0x5CDF: COMPARES - {(0, 0)}, 0x5CE3: COMPARES, 0x5CE7: COMPARES, 0x5CEB: COMPARES}
C8_BRANCHES = (0x5CDF, 0x5CE7)
HYPOTHESES = ('PrintedOr', 'ComparativeAnd')


def _branch_stop(pc, missing):
    if pc not in HELPER_EDGES:
        return missing
    mnemonic = 'JGT' if pc in C8_BRANCHES else 'JGE'
    return f'STOP_BEFORE_{mnemonic}_{pc:04X}'


def c8_primary_evidence_adjudication(query):
    authority = query['sourceIds']
    original = 'OKI66201Sep1991' in authority
    source_classes = [dict(id=item, **{'class': C8_AUTHORITY_CLASS.get(item, 'UnreviewedSource')})
                      for item in authority]
    refusal = cold._first_refusal((
        (query['claim'] == 'NativeExecute', OUTSIDE, 'NativeC8AuthorityForbidden'),
        (bool(set(authority) - C8_AUTHORITY_CLASS.keys()), OUTSIDE, 'UnreviewedC8EvidenceId'),
        (query['claim'] != 'KeepConflict', OUTSIDE, 'C8ResolutionUnsupported'),
        (not original, UNKNOWN, 'ApplicablePrimaryC8SourceMissing'),
    ))
    status, reason = refusal or (COMPLETE, 'PrimaryConflictRetained')
    state = dict(sourceClasses=source_classes, architecturalOpcode=0xC8 if original else None,
                 documentedPredicate='PrintedOr' if original else None,
                 retainedHypotheses=list(HYPOTHESES), resolvedPredicate=None)
    return _result(C8_BRANCHES, status, evidence='DocumentAuthorityReview', state=state,
                   stop='STOP_BEFORE_JGT_5CDF', obligations=('ExactCoreOpcodeAndEdition',
                   'IndependentPredicateAuthority'), unresolved=C8_GAPS, reason=reason)


def _qualified_flags(query, hypothesis):
    pc = query['pc']
    feasible = SOURCE_CMP[pc]
    if hypothesis == 'PrintedOr' and pc != 0x5CDF:
        feasible = frozenset()
    observed = (query['cf'], query['zf'])
    rows = []
    for vector in sorted(feasible):
        if any(given is not None and given != component for given, component in zip(observed, vector, strict=True)):
            continue
        if pc in C8_BRANCHES:
            taken = vector in (accepted.C8_OR if hypothesis == 'PrintedOr' else accepted.C8_AND)
        else:
            taken = vector[0] == 0
        rows.append(dict(cf=vector[0], zf=vector[1], taken=taken, next=HELPER_EDGES[pc][not taken]))
    return dict(hypothesis=hypothesis, rows=rows)


def c8_source_feasibility(query):
    pc = query['pc']
    destinations = (query['target'], query['fallthrough'])
    domains = []
    if query['sourceBinding'] != HELPER_SOURCE:
        status, reason = UNKNOWN, 'ExactFeasibilitySourceRequired'
    elif HELPER_EDGES.get(pc) != destinations:
        status, reason = OUTSIDE, 'FeasibilityBranchIdentityMismatch'
    else:
        selected = HYPOTHESES if query['hypothesis'] == 'Both' else (query['hypothesis'],)
        domains = [_qualified_flags(query, hypothesis) for hypothesis in selected]
        status, reason = ((COMPLETE, 'ReviewedFlagDomain') if any(item['rows'] for item in domains)
                          else (UNKNOWN, 'FlagPairOrIngressUnreachable'))
    flag_inputs = ['CF', 'ZF'] if pc in C8_BRANCHES else ['CF'] if pc in HELPER_EDGES else []
    state = dict(sitePc=pc, domains=domains, comparisonWidthBits=8, flagsRead=flag_inputs,
                 flagsWritten=[], nativeBranchTaken=None, commonFirstC8RouteEstablished=False)
    return _result(HELPER_EDGES, status, evidence='RedactedSourceFlagDomain', state=state,
                   stop=_branch_stop(pc, 'STOP_BEFORE_UNBOUND_HELPER_BRANCH'),
                   obligations=('ExhaustivePrivateByteDomainReview', 'NoChoiceBetweenC8Hypotheses'),
                   unresolved=C8_GAPS, reason=reason)


def helper_normal_entry_provenance(query):
    entry, observed = query['entryPc'], query['predecessorPc']
    predecessor = {0x5CE1: 0x5CDF, 0x5CE9: 0x5CE7}.get(entry)
    reviewed = predecessor is not None and query['sourceBinding'] == HELPER_SOURCE
    status, reason = cold._first_refusal((
        (query['claim'] != 'Inspect', OUTSIDE, 'UnadmittedIngressClaim'),
        (predecessor is None or observed not in (None, predecessor), OUTSIDE, 'EncodedPredecessorMismatch'),
        (not reviewed, UNKNOWN, 'ExactIngressSourceRequired'),
    )) or (UNKNOWN, 'OnlyConflictedEncodedFallthrough')
    state = dict(entryPc=entry, encodedPredecessor=predecessor if reviewed else None,
                 alternateDirectEdges=[] if reviewed else None, reviewedExtents=11499 if reviewed else None,
                 confirmedFullIngress=False, nativeEntry=None)
    return _result((0x5CDF, 0x5CE1, 0x5CE7, 0x5CE9), status, evidence='EncodedIngressReview', state=state,
                   stop=_branch_stop(predecessor, 'STOP_BEFORE_UNBOUND_HELPER_ENTRY'),
                   obligations=('ExcludesOnlyReviewedDirectTargets', 'RequiresSeparateDetachedHandoff'),
                   unresolved=('C8FallthroughUnresolved', 'IndirectAndReturnIngressUnbound'), reason=reason)


def helper_normal_continuation(query):
    entry = query['entry']
    helper = query['helperQuery']
    supplied_entry, supplied_prefix = query['entryHandoff'], query['prefixHandoff']
    projected, child = {}, None
    matrix = []

    def emit(status, reason, stop, detached=False):
        return _result(accepted.HELPER_SCOPE, status, caller=0x2777, state=projected.get('state'), stop=stop,
                       branches=projected.get('branchOutcome', ()), reads=projected.get('reads', ()),
                       writes=projected.get('orderedWrites', ()), states=projected.get('intermediateStates', ()),
                       obligations=projected.get('formalObligations', ()),
                       generations=cold._generation_projection(projected.get('state')),
                       unresolved=HELPER_GAPS, reason=reason, entry=entry, candidatePairs=matrix,
                       detachedNormalFrontier=detached, fullNormalFrontier=False, frozenHelperResult=child)

    if query['sourceBinding'] != HELPER_SOURCE:
        return emit(UNKNOWN, 'ExactHelperContinuitySourceRequired', 'STOP_BEFORE_HELPER_5CD9')
    if entry == 'Full' and any(value is not None for value in (supplied_entry, supplied_prefix)):
        return emit(OUTSIDE, 'DetachedHandoffCannotQualifyFullEntry', 'STOP_BEFORE_HELPER_5CD9')
    if entry == 'Detached5CE1' and supplied_prefix is not None:
        return emit(OUTSIDE, 'SecondStagePremiseOutOfScope', 'STOP_BEFORE_JGT_5CDF')
    child = accepted.helper_5cd9_extended(dict(
        entry='Full' if entry == 'Full' else 'Detached5CE1', helperQuery=helper,
        detachedHandoff={'Full': None, 'Detached5CE1': supplied_entry, 'Detached5CE9': supplied_prefix}[entry],
    ))
    projected = deepcopy(child)
    boundary = child['stopBoundary']
    if entry != 'Detached5CE9':
        return emit(child['status'], child['reason'], boundary, child['detachedNormalFrontier'])
    if boundary != 'STOP_BEFORE_JGT_5CE7' or supplied_entry is not True:
        return emit(UNKNOWN, 'SecondDetachedIngressUnestablished', boundary)
    if all(row['comparativeAnd'] for row in child['branchOutcome'][-1]['candidateRows']):
        return emit(OUTSIDE, 'SecondC8FallthroughContradictsInputDomain', boundary)

    state = projected['state']
    low_bits = {key.partition('.')[2]: value for key, value in state['registerKnownBits'].items()
                if key.startswith('AL.')}
    domain = cold._domain(cold._slot(state['registers']['al'], knowledge=low_bits))
    previous_threshold = helper['thresholds']['5CE5']
    if previous_threshold is not None:
        domain = tuple(value for value in domain if value <= previous_threshold)
    pairs = accepted._compare_options(domain, helper['thresholds']['5CE9'])
    state['registers']['cf'] = cold._agreed(pair[0] for pair in pairs)
    state['registers']['zf'] = cold._agreed(pair[1] for pair in pairs)
    projected['intermediateStates'].append(dict(pc=0x5CE9, state=deepcopy(state)))
    matrix = [dict(cf=carry, zf=zero) for carry, zero in sorted(pairs)]
    taken = cold._agreed(carry == 0 for carry, _ in pairs)
    projected['branchOutcome'].append(dict(pc=0x5CEB, taken=taken, next={True: 0x5CF9, False: 0x5CED}.get(taken)))
    if taken is None:
        return emit('IndeterminateBranch', 'SecondDetachedJgePredicateUnknown', 'STOP_BEFORE_JGE_5CEB')
    if taken:
        return emit(COMPLETE, 'SecondDetachedJgeNormalFrontier', 'STOP_BEFORE_RT_5CF9', True)
    return emit(COMPLETE, 'SecondDetachedJgeErrorFrontier', 'STOP_BEFORE_ERROR_MARKER_5CED')


WINDOW_SOURCE = 'M2daColdModeWindowV1'
WINDOW_SCOPE = (0x277A, 0x279E, 0x27A2, 0x27AE, 0x27B0, 0x27B2, 0x27C5, 0x27CA,
                0x27CC, 0x27CE, 0x27D0, 0x7C0B, 0x7C11)
MODE_SCOPE = (*WINDOW_SCOPE, 0x5F45, 0x60C0, 0x60C9, 0x60CC, 0x60E4)
WINDOW_GAPS = ('NativeHelperReturnUnestablished', 'NativeUspOwnerUnbound', 'NativeModeEntryUnobserved')
MODE_GAPS = ('NativeHelperReturnUnestablished', 'NativeData03cbOwnerUnbound', 'NativeModeReadUnobserved')
WINDOW_OBLIGATIONS = ('IndependentDetached277aEntry', 'CompleteReviewedColdWriterFootprint',
                      'ExplicitUspGenerationAt27b2', 'DisjointOrdinaryModeFrame')
MODE_ENTRY_STOP = 'STOP_BEFORE_MODE_ENTRY_5F45'
MODE_CALL_STOP = 'STOP_BEFORE_CAL_27D0'
MODE_RT_STOP = 'STOP_BEFORE_RT_60E4'


def _early_footprint(event):
    earlier = {'Frame': (0x276A, 0x2777), 'Local': (0x2766,)}
    kind = event.get('kind')
    return event.get('pc') in earlier[kind] if kind in earlier else kind in ('Indexed', 'OffPage', 'Unknown')


def cold_to_mode_intervening_writes(query):
    writer = usp = frame = candidate = carry = usp_owner = address = None
    reads, writes, branches, intermediate = [], [], [], []
    obligations = list(WINDOW_OBLIGATIONS)

    def emit(status, reason, boundary='STOP_BEFORE_DETACHED_277A'):
        ready = status == COMPLETE
        state = dict(candidate=candidate, carriedSlot=carry, frameAddress=address,
                     retainedUspGeneration=usp_owner, conditionalModeCallReady=ready, nativeOwner=None)
        generations = dict(candidate=candidate['generation'] if candidate else None,
                           atModeEntry=carry['generation'] if ready else None,
                           modeFrame=frame['state']['frame']['generation'] if ready else None)
        return _result(WINDOW_SCOPE, status, caller=0x276A, stop=boundary, state=state, reads=reads,
                       writes=writes, branches=branches, states=intermediate, generations=generations,
                       obligations=obligations, unresolved=WINDOW_GAPS if ready else (*WINDOW_GAPS, reason),
                       reason=reason, frozenWriter=writer, frozenUsp=usp, frozenModeFrame=frame)

    if query['claim'] != 'ConditionalOnly':
        return emit(OUTSIDE, 'NonConditionalColdWindowClaim')
    binding = query['sourceBinding']
    if binding != WINDOW_SOURCE:
        return emit(UNKNOWN if binding is None else OUTSIDE, 'ColdWindowSourceBindingUnqualified')
    writer_query = query['writerQuery']
    if any(not _early_footprint(row) for row in writer_query['events']):
        return emit(OUTSIDE, 'WriterEventOutsidePre277aWindow')
    writer = accepted.data03cb_competing_writer_exclusion(writer_query)
    candidate = writer['state']['candidate']
    carry = writer['state']['lastEstablishedSlot']
    if writer['status'] != COMPLETE:
        return emit(writer['status'], writer['reason'])
    if not all(query['premises'][premise] is True for premise in ('detached277a', 'reviewedPath', 'noInterference')):
        return emit(UNKNOWN, 'DetachedColdWindowPremisesUnestablished')

    generations = {row['generation'] for row in writer_query['initialTimeline']['initial'].values()}
    for result in (writer['frozenWriter'], writer):
        generations.update(event['generation'] for event in result['orderedWrites'])
    usp = accepted.usp27b2_alias_proof(query['uspProof'])
    if usp['status'] != COMPLETE:
        return emit(usp['status'], usp['reason'], 'STOP_BEFORE_USP_STORE_27B2')
    event, = usp['orderedWrites']
    byte = event['slot']
    if byte['generation'] in generations:
        return emit(OUTSIDE, 'ColdUspWriterGenerationReused', 'STOP_BEFORE_USP_STORE_27B2')
    generations.add(byte['generation'])
    usp_owner = usp['generations']['usp']
    reads = list(usp['reads'])
    hit = usp['state']['overlap03cb']
    same = byte['value'] == carry['value'] if hit and byte['value'] is not None and carry['value'] is not None else None
    writes.append(dict(event, overlap03cb=hit, sameValue03cb=same))
    if hit:
        carry = dict(byte, writerPc=0x27B2, iterationId=None)
    intermediate.append(dict(pc=0x27B2, carriedSlot=carry))
    if hit:
        return emit(UNKNOWN, 'UspStoreReplacedCandidateGeneration', 'STOP_BEFORE_27B4')

    branches = [dict(pc=site, taken=None, next=None, possibleSuccessors=[target, fallthrough])
                for site, target, fallthrough in ((0x27C5, 0x27CC, 0x27C7), (0x27CA, 0x27CE, 0x27CC))]
    frame_input = query['modeFrame']
    if frame_input['callerPc'] != 0x27D0:
        return emit(OUTSIDE, 'ColdModeFrameCallerMismatch', MODE_CALL_STOP)
    frame = enclosing.call_return_obligations(frame_input)
    address = frame['state']['geometry']['frameAddress']
    obligations += frame['frameObligations']
    refusal = cold._first_refusal((
        (address == 0x03CA, UNKNOWN, 'ModeFrameCouldOverwriteData03cb'),
        (address == 0x4700, OUTSIDE, 'ModeFrameUnsupportedMapping'),
        (frame['status'] != COMPLETE, frame['status'], frame['reason']),
        (frame['state']['frame']['generation'] in generations, OUTSIDE, 'ColdModeFrameGenerationReused'),
    ))
    if refusal:
        return emit(*refusal, MODE_CALL_STOP)
    intermediate.append(dict(pc=0x27D0, carriedSlot=carry))
    return emit(COMPLETE, 'DetachedColdWriterWindowRetained', MODE_CALL_STOP)


def _writes_to_data03cb(event):
    if event['space'] != 'DATA':
        return False
    address, width = event['address'], event['widthBits']
    if address is None or width not in (8, 16):
        return True
    return 0x03CB in range(address, address + width // 8)


def data03cb_to_60cc_source_proof(query):
    window = projection = owner = None

    def emit(status, reason, stop):
        proved = status == COMPLETE
        registers = projection['state']['registers'] if projection else None
        bits = projection['state']['registerKnownBits'] if projection else None
        state = dict(conditionalRead60cc=proved, readGeneration=owner if proved else None,
                     registers=registers, registerKnownBits=bits, nativeOwner=None)
        return _result(MODE_SCOPE, status, caller=0x27D0, stop=stop, state=state,
                       generations=dict(candidate=owner, at60cc=owner if proved else None),
                       reads=projection['reads'] if projection else (), writes=projection['journal'] if projection else (),
                       branches=[event for event in projection['steps'] if event['kind'] == 'Branch'] if projection else (),
                       states=projection['intermediateStates'] if projection else (),
                       obligations=window['formalObligations'] if window else (),
                       unresolved=MODE_GAPS if proved else (*MODE_GAPS, reason), reason=reason,
                       windowResult=window, frozenMode=projection)

    if query['claim'] != 'ConditionalOnly':
        return emit(OUTSIDE, 'NonConditionalData03cbReadClaim', MODE_ENTRY_STOP)
    window = cold_to_mode_intervening_writes(query['windowQuery'])
    if window['status'] != COMPLETE:
        return emit(window['status'], window['reason'], window['stopBoundary'])
    carried = window['state']['carriedSlot']
    owner = carried['generation']
    prefix = query['modeQuery']['prefixQuery']
    if (prefix['callerPc'], prefix['entry']) != (0x27D0, 'From5F45'):
        return emit(OUTSIDE, 'DetachedModeCallerOrEntryMismatch', MODE_ENTRY_STOP)
    if prefix['entryEstablished'] is not True:
        return emit(UNKNOWN, 'DetachedModeEntryUnestablished', MODE_ENTRY_STOP)
    snap = prefix['snapshot']
    usp = query['windowQuery']['uspProof']['currentUsp']['value']
    if [snap['registers'][key] for key in ('lrb', 'scb', 'dd', 'usp')] != [0x0041, 0, 0, usp]:
        return emit(UNKNOWN, 'DetachedModeRegisterHandoffMismatch', MODE_ENTRY_STOP)
    address = window['state']['frameAddress']
    if set(range(address, address + 2)).intersection(int(key, 16) for key in snap['memory']):
        return emit(OUTSIDE, 'DetachedModeFrameAliasesSnapshot', MODE_ENTRY_STOP)
    bits = {key.partition('.')[2]: value for key, value in snap['knownBits'].items() if key.startswith('03CB.')}
    if (snap['memory']['03CB'], snap['generations']['03CB'], bits) != (
            carried['value'], carried['generation'], carried['knownBits']):
        return emit(UNKNOWN, 'ModeEntryData03cbGenerationMismatch', MODE_ENTRY_STOP)

    projection = mode.mode_enclosing_continuation(query['modeQuery'])
    stop = projection['exactStopBoundary']
    observed = [item['value'] for item in projection['reads'] if
                [item[key] for key in ('pc', 'space', 'address', 'widthBits')] == [0x60CC, 'DATA', 0x03CB, 8]]
    if projection['status'] != COMPLETE or stop != MODE_RT_STOP or len(observed) != 1:
        return emit(UNKNOWN, 'Mode60ccReadNotReachedInCompleteScope', stop)
    if (observed != [carried['value']] or projection['state']['generations']['03CB'] != owner
            or any(_writes_to_data03cb(event) for event in projection['journal'])):
        return emit(UNKNOWN, 'FrozenModeWriterOrReadContradiction', stop)
    return emit(COMPLETE, 'DetachedData03cbRead60ccProven', stop)


OPERATIONS = {function.__name__: function for function in (
    c8_primary_evidence_adjudication, c8_source_feasibility, helper_normal_entry_provenance,
    helper_normal_continuation, cold_frame_generation_chain, cold_to_mode_intervening_writes,
    data03cb_to_60cc_source_proof, cold_normal_mode_source_join,
)}


def record(case):
    output = OPERATIONS[case['operation']](case['input'])
    return deepcopy(dict(caseId=case['id'], operation=case['operation'], input=case['input'], output=output,
                         **{key: output[key] for key in RECORD_FIELDS}, sourceApplicability=output['applicability'],
                         executionAuthority={key: output[key] for key in AUTHORITY}))
