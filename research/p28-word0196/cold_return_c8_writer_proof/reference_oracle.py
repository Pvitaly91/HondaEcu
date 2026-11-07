"""Independent M2cz source equations over accepted reference projections."""

from copy import deepcopy
from itertools import product

from indexed_suffix_ie_provenance import reference_oracle as indexed_reference
from shadow_cold_reacquisition import reference_oracle as cold_reference


BASE = '83ffa492a1565d15c4f8b32f180e34e884e431ac'
SOURCE_IDENTITIES = {
    'm2cyBase': BASE,
    'm2cySourceBinding': '76d257b263d8b9226ce28cec4c50109c78f2b037be1959d30a5bff45a2861f83',
    'primaryIsa': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
}
AUTHORITY = cold_reference.AUTHORITY
canonical = cold_reference.canonical
OUTPUT_FIELDS = (
    'sourceScope', 'sourceIdentities', 'evidenceClass', 'applicability', 'caller', 'iterations',
    'state', 'branchOutcome', 'reads', 'orderedWrites', 'generations', 'intermediateStates',
    'formalObligations', 'unresolvedConstraints', 'stopBoundary',
)
OUTSIDE, UNKNOWN, COMPLETE = 'OutsideVerifiedScope', 'IndeterminateObligation', 'CompleteConditional'


def _result(scope, status, *, caller=None, iterations=(), state=None, stop=None,
            evidence='ConditionalSourceModel', reads=(), writes=(), generations=None, states=(),
            obligations=(), unresolved=(), branches=(), **details):
    return deepcopy({
        'status': status, 'sourceScope': list(scope), 'sourceIdentities': SOURCE_IDENTITIES,
        'evidenceClass': evidence, 'applicability': 'ConditionalSoftwareOnly_HardwareApplicabilityUnestablished',
        'caller': caller, 'iterations': list(iterations), 'state': state,
        'branchOutcome': list(branches), 'reads': list(reads), 'orderedWrites': list(writes),
        'generations': generations, 'intermediateStates': list(states), 'formalObligations': list(obligations),
        'unresolvedConstraints': list(unresolved), 'stopBoundary': stop, **AUTHORITY, **details,
    })


def record(case):
    output = OPERATIONS[case['operation']](case['input'])
    return deepcopy({'caseId': case['id'], 'operation': case['operation'], 'input': case['input'], 'output': output,
                     **{key: output[key] for key in OUTPUT_FIELDS},
                     'executionAuthority': {key: output[key] for key in AUTHORITY}})


C8_TARGETS = {0x5CDF: (0x5CED, 0x5CE1), 0x5CE7: (0x5CED, 0x5CE9)}
C8_OR = frozenset(((0, 0), (0, 1), (1, 0)))
C8_AND = frozenset(((0, 0),))
COMPARE_FLAG_PAIRS = frozenset(((0, 0), (0, 1), (1, 0)))
HELPER_SCOPE = (0x5CD9, 0x5CDC, 0x5CDD, 0x5CDF, 0x5CE1, 0x5CE3, 0x5CE5, 0x5CE7,
                0x5CE9, 0x5CEB, 0x5CED, 0x5CEF, 0x5CF1, 0x5CF4, 0x5CF6, 0x5CF8, 0x5CF9)


def _flag_vectors(cf, zf, producer):
    legal = COMPARE_FLAG_PAIRS if producer == 'UnsignedByteCompare' else frozenset(product((0, 1), repeat=2))
    return tuple(pair for pair in sorted(legal) if all(known is None or known == value
                 for known, value in zip((cf, zf), pair, strict=True)))


def _branch_matrix(vectors):
    rows = tuple((pair, pair in C8_OR, pair in C8_AND) for pair in vectors)
    if not rows:
        return 'UnknownPredicate', None, rows
    outcomes = {(printed, comparative) for _, printed, comparative in rows}
    if outcomes == {(True, True)}:
        return 'ConsensusTaken', True, rows
    if outcomes == {(False, False)}:
        return 'ConsensusNotTaken', False, rows
    if all(printed != comparative for printed, comparative in outcomes):
        return 'Disagreement', None, rows
    return 'UnknownPredicate', None, rows


def _row_dicts(rows):
    return [{'cf': flags[0], 'zf': flags[1], 'printedOr': printed, 'comparativeAnd': comparative}
            for flags, printed, comparative in rows]


def c8_branch_consensus(query):
    site = query['pc']
    producer = query['producer']
    vectors = _flag_vectors(query['cf'], query['zf'], producer)
    classification, taken, rows = _branch_matrix(vectors)
    _, _, full_matrix = _branch_matrix(_flag_vectors(None, None, 'ExplicitFlags'))
    targets = (query['target'], query['fallthrough'])
    if query['authority'] != 'OKI_MSM66201_3_66_3_67':
        refusal = (UNKNOWN, 'ApplicablePrimarySourceRequired')
    elif query['conditionCode'] != 0xC8 or targets != C8_TARGETS.get(site):
        refusal = (OUTSIDE, 'C8SourceSiteOrEdgeMismatch')
    elif not rows:
        refusal = (OUTSIDE, 'UnsignedCompareFlagPairImpossible')
    else:
        refusal = None
    if refusal:
        status, reason = refusal
        classification, branches, rows = None, (), ()
    else:
        status = COMPLETE if taken is not None else 'IndeterminateBranch'
        reason = classification
        destination = None if taken is None else targets[0 if taken else 1]
        branches = ({'pc': site, 'taken': taken, 'next': destination},)
    state = {'flagReads': ['CF', 'ZF'], 'flagWrites': [], 'length': 2, 'displacementWidthBits': 8,
             'compareDomain': producer, 'table': _row_dicts(full_matrix), 'candidateRows': _row_dicts(rows)}
    stop = 'STOP_BEFORE_UNBOUND_C8' if site not in C8_TARGETS else f'STOP_BEFORE_JGT_{site:04X}'
    return _result(C8_TARGETS, status, state=state, stop=stop, branches=branches, reason=reason,
                   classification=classification, predicateAuthority='PrimarySourceConflict',
                   unresolved=('NativeC8PredicateUnestablished',))


def _compare_options(domain, threshold):
    less = min(domain) < (255 if threshold is None else threshold)
    equal = threshold is None or threshold in domain
    greater = max(domain) > (0 if threshold is None else threshold)
    return tuple(pair for possible, pair in ((greater, (0, 0)), (equal, (0, 1)), (less, (1, 0))) if possible)


def _detached_fault(helper, state, reads, writes, branches, mark):
    counter = helper['counterF7']
    generations = {pc: f'M2cz:{pc:04X}:{helper["invocationId"]}' for pc in (0x5CEF, 0x5CF1, 0x5CF6)}
    existing = set(cold_reference._generation_projection(state).values())
    if counter:
        existing.add(counter['slot']['generation'])
    if existing.intersection(generations.values()):
        return OUTSIDE, 'HelperGenerationCollision', 'STOP_BEFORE_ERROR_MARKER_5CED'
    marker = helper['errorByte']
    possible = tuple(range(256)) if marker is None else (marker,)
    cold_reference._accumulate_low(state, possible, True)
    mark(0x5CED)
    state['data00af'] = cold_reference._slot(marker, generations[0x5CEF])
    writes.append(cold_reference._effect(0x5CEF, 0x00AF, cold_reference._slot(), state['data00af'],
                                        'ConditionalHelperMarker'))
    mark(0x5CEF)
    if not counter:
        return UNKNOWN, 'FirstCallCounterGenerationUnestablished', 'STOP_BEFORE_DECB_5CF1'
    old_counter = counter['slot']
    evidence = (counter['sourcePc'], counter['firstCall'], counter['noInterference'], old_counter['value'])
    if evidence != (0x2773, True, True, 1) or old_counter['generation'] is None or (
            old_counter['generation'] != counter['expectedGeneration']):
        return UNKNOWN, 'FirstCallCounterGenerationUnestablished', 'STOP_BEFORE_DECB_5CF1'
    reads.append({'pc': 0x5CF1, 'address': 0x00F7, 'widthBits': 8, 'space': 'DATA', 'slot': old_counter})
    state['counterF7'] = cold_reference._slot(0, generations[0x5CF1])
    writes.append(cold_reference._effect(0x5CF1, 0x00F7, old_counter, state['counterF7'],
                                        'ConditionalByteDecrement'))
    state['registers']['zf'] = 1
    state['registers']['hc'] = 0
    mark(0x5CF1)
    branches.append({'pc': 0x5CF4, 'taken': False, 'next': 0x5CF6})
    old_marker = cold_reference._data(state, 0x00F5)
    new_marker = cold_reference._replace_data(state, 0x00F5, possible, generations[0x5CF6])
    writes.append(cold_reference._effect(0x5CF6, 0x00F5, old_marker, new_marker, 'ConditionalHelperMarker'))
    mark(0x5CF6)
    return COMPLETE, 'DetachedFirstCallFaultRoute', 'STOP_BEFORE_BRK_5CF8'


def helper_5cd9_extended(query):
    entry, helper, handoff = (query[key] for key in ('entry', 'helperQuery', 'detachedHandoff'))
    child = cold_reference.helper_5cd9(helper)
    state, branches, reads, writes, stages = (deepcopy(child[key]) for key in (
        'state', 'branchOutcome', 'reads', 'orderedWrites', 'intermediateStates'))
    status, reason, stop = (child[key] for key in ('status', 'reason', 'stopBoundary'))
    classification, normal = None, False

    def mark(pc):
        stages.append({'pc': pc, 'state': deepcopy(state)})

    def project_compare(site, domain):
        candidates = _compare_options(domain, helper['thresholds'][f'{site:04X}'])
        registers = state['registers']
        registers['cf'] = cold_reference._agreed(vector[0] for vector in candidates)
        registers['zf'] = cold_reference._agreed(vector[1] for vector in candidates)
        mark(site)
        return candidates

    if entry == 'Full':
        if handoff is not None:
            status, reason = OUTSIDE, 'DetachedHandoffCannotQualifyFullEntry'
    elif handoff is not True or stop != 'STOP_BEFORE_JGT_5CDF':
        status, reason = UNKNOWN, 'Detached5ce1HandoffUnestablished'
    elif all(outcomes == [True] for outcomes in branches[-1]['hypotheses'].values()):
        status, reason = OUTSIDE, 'DetachedFallthroughContradictsInputDomain'
    else:
        knowledge = {field[3:]: value for field, value in state['registerKnownBits'].items()
                     if field.startswith('AL.')}
        domain = cold_reference._domain(cold_reference._slot(state['registers']['al'], knowledge=knowledge))
        first_options = project_compare(0x5CE1, domain)
        first_branch = cold_reference._agreed(pair[0] == 0 for pair in first_options)
        branches.append({'pc': 0x5CE3, 'taken': first_branch,
                         'next': {True: 0x5CF9, False: 0x5CE5}.get(first_branch)})
        if first_branch is True:
            status, reason, stop = COMPLETE, 'DetachedJgeNormalFrontier', 'STOP_BEFORE_RT_5CF9'
            normal = True
        elif first_branch is None:
            status, reason, stop = 'IndeterminateBranch', 'DetachedJgePredicateUnknown', 'STOP_BEFORE_JGE_5CE3'
        else:
            classification, second_branch, rows = _branch_matrix(project_compare(0x5CE5, domain))
            branches.append({'pc': 0x5CE7, 'taken': second_branch,
                             'next': 0x5CED if second_branch is True else None,
                             'candidateRows': _row_dicts(rows)})
            if second_branch is True:
                status, reason, stop = _detached_fault(helper, state, reads, writes, branches, mark)
            else:
                status, reason, stop = 'IndeterminateBranch', 'SecondC8BranchUnresolved', 'STOP_BEFORE_JGT_5CE7'
    return _result(HELPER_SCOPE, status, caller=0x2777, state=state, stop=stop, reads=reads, writes=writes,
                   branches=branches, states=stages, generations=cold_reference._generation_projection(state),
                   obligations=child['formalObligations'], unresolved=child['unresolvedConstraints'],
                   reason=reason, entry=entry, detachedNormalFrontier=normal, connectedNormalFrontier=False,
                   secondC8Classification=classification, frozenHelper=child)


FRAME_SCOPE = (0x276A, 0x276D, 0x2777, 0x277A, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CF9)
JOIN_SCOPE = (0x276A, 0x276D, 0x276F, 0x2771, 0x2773, 0x2777, 0x277A, 0x27B2, 0x27D0,
              0x5C86, 0x5CB9, 0x5CCB, 0x5CCD, 0x5CD9, 0x5CF8, 0x5CF9, 0x5F45, 0x60CC)
FRAME_GAPS = ('IePolicyAndNativeStackUnbound', 'NativeColdContinuityUnobserved')
JOIN_GAPS = ('NativeIndexedReturnUnobserved', 'NativeHelperReturnUnobserved', 'NativeModeRead60ccUnbound')
JOIN_EDGES = ((0x276A, 0x5C86, 'ConfirmedStaticCFG'), (0x5CCD, 0x276D, 'FormalReturnCandidate'),
              (0x2777, 0x5CD9, 'ConfirmedStaticCFG'), (0x5CF9, 0x277A, 'FormalReturnCandidate'),
              (0x277A, 0x27D0, 'SourceUnbound'), (0x27D0, 0x5F45, 'ConfirmedStaticCFG'))


def cold_return_path_obligations(query):
    index_query, helper_query = query['indexedFrame'], query['helperFrame']
    indexed = indexed_reference.indexed_return_obligations(index_query)
    helper = cold_reference.rt5cf9_obligations(helper_query)
    first, second = index_query['frameQuery'], helper_query['frameQuery']
    first_generation, second_generation = first['frame']['generation'], second['frame']['generation']
    prefix_refusal = cold_reference._first_refusal((
        (query['claim'] != 'ConditionalOnly', OUTSIDE, 'NonConditionalReturnClaim'),
        (first['callerPc'] != 0x276A, OUTSIDE, 'ColdIndexedCallerMismatch'),
        (query['indexedIeBoundary'] is not True, UNKNOWN, 'IndexedIeHandoffUnestablished'),
        (indexed['state']['formalReturnedPc'] != 0x276D, UNKNOWN, 'IndexedFrameUnestablished'),
    ))
    state = {'formalIndexedPc': None if prefix_refusal else 0x276D, 'formalHelperPc': None,
             'sspBetweenCalls': None, 'nativeContinuity': None}
    if prefix_refusal:
        status, reason = prefix_refusal
        stop = 'STOP_BEFORE_RT_5CCD'
    elif helper_query['helperBoundary'] == 0x5CF8:
        status, reason, stop = OUTSIDE, 'FaultCannotReturn', 'STOP_BEFORE_BRK_5CF8'
    else:
        stop = 'STOP_BEFORE_RT_5CF9'
        refusal = cold_reference._first_refusal((
            (query['helperNormalBoundary'] is not True or helper['state']['formalReturnedPc'] != 0x277A,
             UNKNOWN, 'HelperNormalFrameUnestablished'),
            (query['stackContinuity'] is not True, UNKNOWN, 'IntercallStackContinuityUnestablished'),
            (first['incomingSsp'] != second['incomingSsp'], OUTSIDE, 'IntercallStackPointerMismatch'),
            (first_generation == second_generation, OUTSIDE, 'ColdFrameGenerationReused'),
        ))
        status, reason = refusal or (COMPLETE, 'MatchingHypotheticalColdFrames')
        if not refusal:
            state['formalHelperPc'] = 0x277A
            state['sspBetweenCalls'] = first['incomingSsp']
    return _result(FRAME_SCOPE, status, caller=0x276A, state=state, stop=stop,
                   evidence='StaticFormalSourceObligation',
                   obligations=[*indexed['formalObligations'], *helper['formalObligations']],
                   unresolved=FRAME_GAPS if status == COMPLETE else (*FRAME_GAPS, reason),
                   generations={'indexedFrame': first_generation, 'helperFrame': second_generation},
                   reason=reason, indexedFrameResult=indexed, helperFrameResult=helper)


def _helper_join_input(query, state):
    exact_snapshot = {name: state[name] for name in indexed_reference.SNAPSHOT_FIELDS}
    kind = query['inputClass']
    exact_snapshot.update(inputClass=kind, assumptions=query['coldQuery']['prefixQuery']['snapshot']['assumptions'])
    counter = {'slot': state['counterF7'], 'sourcePc': 0x2773, 'firstCall': True, 'noInterference': True,
               'expectedGeneration': state['counterF7']['generation']}
    return dict(query['helperArgs'], inputClass=kind, snapshot=exact_snapshot, entryEstablished=True,
                counterF7=counter)


def cold_caller_mode_source_join(query):
    cold, helper = None, None
    edges = list(JOIN_EDGES)
    status, reason, stop = OUTSIDE, 'NonConditionalModeJoinClaim', 'STOP_BEFORE_CAL_276A'
    if query['claim'] == 'ConditionalOnly':
        cold = cold_reference.cold_reacquisition_step(query['coldQuery'])
        status, reason, stop = (cold[key] for key in ('status', 'reason', 'stopBoundary'))
        if (status, stop) == (COMPLETE, 'STOP_BEFORE_CAL_2777'):
            if query['helperHandoff'] is not True or query['helperArgs'] is None:
                status, reason = UNKNOWN, 'HelperEntryHandoffUnestablished'
            else:
                helper = helper_5cd9_extended({'entry': 'Full', 'detachedHandoff': None,
                                               'helperQuery': _helper_join_input(query, cold['state'])})
                status, reason, stop = (helper[key] for key in ('status', 'reason', 'stopBoundary'))
                edges.append((0x2777, 0x5CD9, 'ConditionalStateHandoff'))
    children = [child for child in (cold, helper) if child is not None]
    sites = set(JOIN_SCOPE)
    for child in children:
        sites.update(child['sourceScope'])
    last = children[-1] if children else {}
    carried = last.get('state') if helper is None else dict(cold['state'], **helper['state'])

    def project(field):
        return sum((child[field] for child in children), [])

    return _result(sorted(sites), status, caller=0x276A, state=carried, stop=stop,
                   reads=project('reads'), writes=project('orderedWrites'), branches=project('branchOutcome'),
                   states=project('intermediateStates'), obligations=project('formalObligations'),
                   generations=cold_reference._generation_projection(carried), iterations=() if cold is None else cold['iterations'],
                   unresolved=(*JOIN_GAPS, reason), reason=reason,
                   sourceEdges=[{'from': source, 'to': target, 'class': classification}
                                for source, target, classification in edges],
                   frozenColdResult=cold, helperResult=helper, modeConsumerReached=False)


DATA03CB, WRITER_BINDING = 0x03CB, 'M2czData03cbSourceV1'
USP_SCOPE = (0x277A, 0x279E, 0x27A2, 0x27AE, 0x27B0, 0x27B2, 0x7C0B, 0x7C11)
USP_GAPS = ('NativeIncomingUspUnbound', 'NativePostHelperPathUnbound')
USP_OBLIGATIONS = ('SeparateFormal277aHandoff', 'QualifiedSymbolicAdcAndSfrContext',
                   'ColdLrb0041AndScb0', 'ExactRetainedUspGeneration', 'SymbolicPrivateImmediateAt27ae')
LOCAL_WIDTHS = {0x2766: 8, 0x27C3: 16, 0x7DF4: 8}
INDIRECT_SITES = (0x2785, 0x27AD, 0x27B9, 0x27BB)
FRAME_SITES = (0x276A, 0x2777, 0x27D0)
LATE_RANK = {pc: i for i, pc in enumerate((0x2777, 0x2785, 0x27AD, 0x27B2, 0x27B9, 0x27BB,
                                           0x27C3, 0x27D0, 0x7DF4))}
WINDOW_SCOPE = tuple(sorted(set(USP_SCOPE) | set(LOCAL_WIDTHS) | set(INDIRECT_SITES) | set(FRAME_SITES)
                            | {0x5CAF, 0x5CB4, 0x5CC2, 0x60CC}))
WINDOW_STOP = 'STOP_BEFORE_UNBOUND_MODE_READ_60CC'
WINDOW_GAPS = ('NoGlobalWriterExclusion', 'NativeData03cbOwnerUnbound', 'ModeConsumer60ccUnbound')
WINDOW_OBLIGATIONS = ('ExactFrozenIndex5Writer', 'OrderedLaterSourceEvents', 'ExcludeUnknownAliasesAndInterference',
                      'SeparateHelperReturnAndModeEntry')


def usp27b2_alias_proof(query):
    start, end, source = (query[field] for field in ('entryUsp', 'currentUsp', 'alRead'))
    write_generation = query['writerGeneration']
    usp, usp_generation = end['value'], end['generation']
    address = None if usp is None else (usp - 78) % 65536
    overlap = None if address is None else address == DATA03CB
    binding = query['sourceBinding']
    refusal = cold_reference._first_refusal((
        (query['claim'] != 'ConditionalOnly', OUTSIDE, 'NonConditionalUspClaim'),
        (binding != WRITER_BINDING, UNKNOWN if binding is None else OUTSIDE, 'UspSourceBindingUnqualified'),
        (query['dd'] == 1, OUTSIDE, 'UspStoreDescriptorMismatch'),
        (None in (usp, usp_generation, start['value'], start['generation'], query['dd']),
         UNKNOWN, 'CurrentUspGenerationUnbound'),
        (start != end, OUTSIDE, 'UspGenerationNotRetained'),
        ((query['lrb'], query['scb']) != (0x0041, 0), UNKNOWN, 'UspCorridorBankContextUnqualified'),
        (any(value is not True for value in query['premises'].values()), UNKNOWN, 'UspCorridorHandoffUnqualified'),
        ((source['sourcePc'], source['address']) != (0x27AE, None), OUTSIDE, 'UspStoreAlSourceMismatch'),
        (None in (source['slot']['generation'], write_generation), UNKNOWN, 'UspStoreGenerationMissing'),
        (write_generation in (usp_generation, source['slot']['generation']), OUTSIDE, 'UspWriterGenerationReused'),
        (address is not None and (address < 0x00C0 or address == 0x4700),
         OUTSIDE, 'UspDestinationOutsideReviewedDataScope'),
    ))
    admitted = refusal is None
    status, reason = refusal or (COMPLETE, 'QualifiedUspByteOverlap' if overlap else 'QualifiedUspByteDisjoint')
    state = {'numericAddressCandidate': address, 'numericOverlapCandidate': overlap,
             'qualifiedAddress': address if admitted else None, 'overlap03cb': overlap if admitted else None,
             'retainedUspGeneration': usp_generation if admitted else None, 'nativeOwner': None,
             'alSourceClass': 'PrivateImmediateAt27AE_SymbolicInput' if admitted else None}
    destination_write = {'pc': 0x27B2, 'address': address, 'widthBits': 8,
                         'slot': dict(source['slot'], generation=write_generation)}
    return _result(USP_SCOPE, status, caller=0x276A, state=state,
                   stop='STOP_BEFORE_27B4' if admitted else 'STOP_BEFORE_USP_STORE_27B2',
                   writes=(destination_write,) if admitted else (),
                   generations={'usp': state['retainedUspGeneration'], 'writer': write_generation if admitted else None},
                   obligations=USP_OBLIGATIONS, unresolved=USP_GAPS if admitted else (*USP_GAPS, reason), reason=reason)


def _writer_effect(pc, address, width, value, generation, *, bits=None, iteration=None, selector=None):
    return {'pc': pc, 'address': address, 'widthBits': width, 'value': value, 'generation': generation,
            'knownBits': {} if bits is None else bits, 'iterationId': iteration, 'selector': selector}


def _possible_writer(event, prior_iteration, seen, usp_proofs):
    kind = event['kind']
    if kind == 'Indexed':
        identity = event['iterationId']
        if identity is None or identity in seen or event['fromIteration'] != prior_iteration:
            return (OUTSIDE, 'IndexedRepeatIdentityMismatch'), None
        if event['returned'] is not True or event['repeat'] is not True:
            return (UNKNOWN, 'IndexedReturnOrRepeatUnestablished'), None
        selector = cold_reference._agreed(value // 32 for value in cold_reference._domain(event['p2']))
        if None in (selector, event['p2']['generation'], event['scb']):
            return (UNKNOWN, 'IndexedSelectorOrBankUnbound'), None
        adcr = event['adcr0h']
        if adcr['generation'] is None:
            return (UNKNOWN, 'Adcr0hSourceGenerationUnbound'), None
        return None, _writer_effect(0x5CB4, 0x03C6 + selector, 8, adcr['value'], event['generation'],
                                    bits=adcr['knownBits'], iteration=identity, selector=selector)
    if kind == 'Usp27B2':
        proof = usp27b2_alias_proof(event['proof'])
        usp_proofs.append(proof)
        if proof['status'] != COMPLETE:
            return (proof['status'], proof['reason']), None
        change, = proof['orderedWrites']
        written = change['slot']
        return None, _writer_effect(change['pc'], change['address'], change['widthBits'], written['value'],
                                    written['generation'], bits=written['knownBits'])
    pc = event['pc']
    allowed = {'Frame': FRAME_SITES, 'Local': LOCAL_WIDTHS, 'OffPage': (0x5CC2,), 'Indirect': INDIRECT_SITES}
    if pc not in allowed[kind]:
        return (OUTSIDE, 'UnreviewedCompetingWriterSite'), None
    if event['pathEstablished'] is False:
        return None, None
    if event['pathEstablished'] is not True:
        return (UNKNOWN, 'CompetingWriterPathUnestablished'), None
    generation = event['generation']
    if kind == 'Frame':
        if event['ssp'] is None or event['memoryApplicable'] is not True:
            return (UNKNOWN, 'FrameAliasOrMappingUnbound'), None
        address = event['ssp'] // 2 * 2
        if address < 0x00C0 or address == 0x4700:
            return (OUTSIDE, 'FrameControlOrUnsupportedAlias'), None
        return None, _writer_effect(pc, address, 16, pc + 3, generation)
    if kind == 'Indirect':
        address = event['address']
        if address is None:
            return (UNKNOWN, 'IndirectAliasUnbound'), None
        if address < 0x00C0 or address in (0x4700, DATA03CB):
            return (OUTSIDE, 'IndirectAddressContradictsReviewedFootprint'), None
        return None, _writer_effect(pc, address, 8, None, generation)
    lrb = event['lrb']
    if lrb is None:
        return (UNKNOWN, 'WriterBankOrPageUnbound'), None
    if kind == 'Local':
        address, width = (lrb % 0x2000) * 8, LOCAL_WIDTHS[pc]
    else:
        address, width = ((lrb % 0x2000) // 32) * 256 + 0x5A, 16
    if address < 0x00C0 or address == 0x4700:
        return (OUTSIDE, 'LocalOrPageControlAlias'), None
    return None, _writer_effect(pc, address, width, None, generation)


def _byte_at(effect, address):
    offset = address - effect['address']
    raw = effect['value']
    return None if raw is None else raw // (256 ** offset) % 256


def data03cb_competing_writer_exclusion(query):
    initial = query['initialTimeline']
    writer, seed, current = None, None, None
    effects, states, iterations, usp_proofs = [], [], [], []

    def finish(status, reason, relation):
        local = None if current is None else current['generation']
        generations = {'candidate': None if seed is None else seed['generation'], 'lastEstablished': local,
                       'retained': local if status == COMPLETE else None}
        return _result(WINDOW_SCOPE, status, caller=0x276A, stop=WINDOW_STOP,
                       state={'localWriterProven': seed is not None, 'candidate': seed,
                              'lastEstablishedSlot': current, 'retention': relation, 'nativeOwner': None},
                       writes=effects, states=states, iterations=iterations, generations=generations,
                       obligations=WINDOW_OBLIGATIONS, unresolved=WINDOW_GAPS if status == COMPLETE else
                       (*WINDOW_GAPS, reason), reason=reason, frozenWriter=writer, uspProofs=usp_proofs)

    binding = query['sourceBinding']
    if query['claim'] != 'ConditionalOnly':
        return finish(OUTSIDE, 'NonConditionalWriterClaim', 'ConflictingWriterEvidence')
    if binding != WRITER_BINDING:
        return finish(UNKNOWN if binding is None else OUTSIDE, 'WriterSourceBindingUnqualified', 'SourcePathUnestablished')
    if [event['kind'] for event in initial['events']] != ['Acquisition']:
        return finish(OUTSIDE, 'OneInitialIndexedAcquisitionRequired', 'ConflictingWriterEvidence')
    writer = cold_reference.cold_adc_generation_timeline(initial)
    prior = writer['state']['lastSlots']['03CB']
    if (writer['status'], prior['writerPc']) != (COMPLETE, 0x5CB4) or prior['generation'] is None:
        return finish(UNKNOWN, 'FrozenIndex5WriterUnestablished', 'MissingGeneration')
    current = seed = dict(prior, knownBits={})
    iterations += writer['iterations']
    latest_iteration = seed['iterationId']
    seen_iterations = {latest_iteration}
    seen_generations = {item['generation'] for item in (*writer['orderedWrites'], *initial['initial'].values())
                        if item['generation'] is not None}
    last_rank = None
    for event in query['events']:
        kind = event['kind']
        if kind == 'Unknown':
            return finish(UNKNOWN, 'PotentialUnknownWriter', 'UnexcludedInterference')
        refusal, potential = _possible_writer(event, latest_iteration, seen_iterations, usp_proofs)
        if refusal:
            status, reason = refusal
            return finish(status, reason, 'UnknownAlias' if status == UNKNOWN else 'ConflictingWriterEvidence')
        if potential is None:
            continue
        pc = potential['pc']
        rank = LATE_RANK.get(pc)
        if last_rank is not None:
            if rank is None:
                return finish(OUTSIDE, 'IndexedWriterAfterColdExit', 'ConflictingWriterEvidence')
            if rank <= last_rank:
                return finish(OUTSIDE, 'WriterSourceOrderMismatch', 'ConflictingWriterEvidence')
        last_rank = rank
        generation = potential['generation']
        if generation is None:
            return finish(UNKNOWN, 'CompetingWriterGenerationMissing', 'MissingGeneration')
        if generation in seen_generations:
            return finish(OUTSIDE, 'CompetingWriterGenerationReused', 'ConflictingWriterEvidence')
        seen_generations.add(generation)
        iteration = potential['iterationId']
        if iteration is not None:
            iterations.append({'iterationId': iteration, 'fromIteration': latest_iteration,
                               'selectedIndex': potential['selector'], 'suppliedP2': event['p2']['value'],
                               'suppliedAdcr0h': potential['value']})
            latest_iteration = iteration
            seen_iterations.add(iteration)
        before = current
        destination = potential['address']
        width = potential['widthBits']
        overlap = DATA03CB in range(destination, destination + width // 8)
        if overlap:
            current = {'value': _byte_at(potential, DATA03CB), 'knownBits': potential['knownBits'],
                       'generation': generation, 'writerPc': pc, 'iterationId': iteration}
        equal = before['value'] == current['value'] if overlap and None not in (
            before['value'], current['value']) else None
        effects.append({'id': event['id'], 'kind': kind, 'pc': pc, 'address': destination,
                        'widthBits': width, 'generation': generation, 'overlap03cb': overlap,
                        'sameValue': equal, 'before': before, 'after': current})
        states.append({'eventId': event['id'], 'lastEstablishedSlot': current})
    requested = query['requestedGeneration']
    if query['noInterference'] is not True:
        return finish(UNKNOWN, 'InterferenceNotExcluded', 'UnexcludedInterference')
    if requested is None:
        return finish(UNKNOWN, 'RequestedGenerationMissing', 'MissingGeneration')
    if requested != seed['generation']:
        return finish(UNKNOWN, 'RequestedGenerationNotTheSeed', 'StaleGeneration')
    if current['generation'] != seed['generation']:
        return finish(UNKNOWN, 'ReviewedWriterReplacedSeed', 'CompetingWriterPresent')
    return finish(COMPLETE, 'ScopedWriterExclusionEstablished',
                  'ConditionalGenerationRetained' if effects else 'ConfirmedLocalNoOverwrite')


def _cold_owner(cold):
    step = cold['frozenColdResult']
    if not step or not step['iterations'] or not step['frozenAcquisition']:
        return None
    prefix = step['frozenAcquisition']['frozenPrefixResult']
    if prefix['selectedIndex'] != 5 or prefix['conditionalData03cbWriterEstablished'] is not True:
        return None
    return (step['iterations'][0]['id'], prefix['state']['memory']['03CB'], prefix['state']['generations']['03CB'])


def data03cb_to_mode_reaching_definitions(query):
    read = query['proposedRead']
    writer, cold = None, None
    linked = False
    boundary = WINDOW_STOP
    if query['claim'] != 'ConditionalOnly':
        status, reason = OUTSIDE, 'NonConditionalModeReadClaim'
    elif (read['pc'], read['address'], read['widthBits']) != (0x60CC, DATA03CB, 8):
        status, reason = OUTSIDE, 'ModeReadSourceIdentityMismatch'
    else:
        writer = data03cb_competing_writer_exclusion(query['writerQuery'])
        candidate = writer['state']['candidate']
        if writer['status'] != COMPLETE:
            status, reason, boundary = (writer[key] for key in ('status', 'reason', 'stopBoundary'))
        elif read['generation'] != candidate['generation']:
            status, reason = UNKNOWN, 'ModeReadGenerationMismatch'
        else:
            cold = cold_caller_mode_source_join(query['coldJoinQuery'])
            linked = _cold_owner(cold) == (candidate['iterationId'], candidate['value'], candidate['generation'])
            boundary = cold['stopBoundary']
            status, reason = UNKNOWN, 'ModeReadSourcePathUnestablished' if linked else 'ColdPrefixWriterGenerationUnlinked'
    state = {'localWriterProven': bool(writer and writer['state']['localWriterProven']),
             'conditionalRetention': bool(writer and writer['status'] == COMPLETE),
             'linkedToColdPrefix': linked, 'conditionalSourcePathTo60cc': False, 'nativeOwnership': None}
    return _result(WINDOW_SCOPE, status, caller=0x276A, state=state, stop=boundary,
                   generations=None if writer is None else writer['generations'],
                   iterations=() if writer is None else writer['iterations'], obligations=WINDOW_OBLIGATIONS,
                   unresolved=(*WINDOW_GAPS, reason), reason=reason, writerResult=writer, coldResult=cold)


OPERATIONS = {function.__name__: function for function in (
    c8_branch_consensus, helper_5cd9_extended, cold_return_path_obligations, cold_caller_mode_source_join,
    usp27b2_alias_proof, data03cb_competing_writer_exclusion, data03cb_to_mode_reaching_definitions,
)}
