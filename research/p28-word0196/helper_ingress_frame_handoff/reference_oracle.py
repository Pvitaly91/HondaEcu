"""Independent documentary expectations for the fixed, invented M2db corpus."""
from cold_return_c8_writer_proof.reference_oracle import data03cb_competing_writer_exclusion as old_writer

from .corpus import FRAME_SITES

OK, WAIT, REFUSE = 'CompleteConditional', 'IndeterminateObligation', 'OutsideVerifiedScope'


def _ingress(case):
    q = case['input']
    pc, transfer = q['entryPc'], q['transferClass']
    predecessor = pc - 2 if pc in (0x5CE1, 0x5CE9) else None
    result = dict(entryPc=pc, transferClass=transfer, encodedPredecessor=None,
                  exclusionEstablished=None, examinedVectorWords=None, savedContinuationCandidates=None,
                  nativeIngress=None, stopBoundary=f'STOP_BEFORE_C8_{predecessor:04X}' if predecessor else None)
    mapping = {
        'EncodedDirect': (WAIT, 'EncodedC8FallthroughUnresolved', {}),
        'UnboundIndirect': (WAIT, 'UnboundIndirectIngressUnresolved', {}),
        'VcalVector': (OK, 'FixedVcalTableExcludesEntry',
                       {'exclusionEstablished': True, 'examinedVectorWords': 8}),
        'OrdinaryIntactReturn': (OK, 'NoReviewedCallEndsAtEntry',
                                 {'exclusionEstablished': True, 'savedContinuationCandidates': 0}),
    }
    special = {
        'ingress-positive': (REFUSE, 'PositiveOrNativeIngressClaimNotAdmitted'),
        'ingress-native': (REFUSE, 'PositiveOrNativeIngressClaimNotAdmitted'),
        'ingress-unbound': (WAIT, 'HelperSourceBindingRequired'),
        'ingress-full': (REFUSE, 'DetachedEntryRequired'),
    }
    if case['id'] in special:
        status, reason = special[case['id']]
    else:
        status, reason, fields = mapping[transfer]
        result.update(fields, encodedPredecessor=predecessor)
    return dict(result, status=status, reason=reason)


# Each row lists the ordered reviewed successor identities and comparison
# classes from the source audit. The reference makes no C8 predicate call.
ROUTE_TABLE = (
    (('E', 0x5CED),),
    (('L', 0x5CED),),
    (('E', 0x5CE1), ('G', 0x5CF9)),
    (('L', 0x5CE1), ('G', 0x5CF9)),
    (('L', 0x5CE1), ('E', 0x5CF9)),
    (('L', 0x5CE1), ('L', 0x5CE5), ('G', 0x5CED)),
    (('L', 0x5CE1), ('L', 0x5CE5), ('E', 0x5CE9), ('G', 0x5CF9)),
    (('L', 0x5CE1), ('L', 0x5CE5), ('L', 0x5CE9), ('G', 0x5CF9)),
    (('L', 0x5CE1), ('L', 0x5CE5), ('L', 0x5CE9), ('E', 0x5CF9)),
    (('L', 0x5CE1), ('L', 0x5CE5), ('L', 0x5CE9), ('L', 0x5CED)),
)


def _route(row):
    flags = [
        {'pc': pc, 'cf': int(compare == 'L'), 'zf': int(compare == 'E'),
         'taken': next_pc != pc + 2, 'nextPc': next_pc}
        for pc, (compare, next_pc) in zip((0x5CDF, 0x5CE3, 0x5CE7, 0x5CEB), row)
    ]
    frontier = 'STOP_BEFORE_RT_5CF9' if row[-1][1] == 0x5CF9 else 'STOP_BEFORE_ERROR_MARKER_5CED'
    return {'branchFlags': flags, 'frontier': frontier}


def _feasibility(case):
    name = case['id'].removeprefix('route-')
    selected = {
        'all': tuple(range(10)), 'later-equal': (6,), 'later-greater': (5,),
        'individually-feasible-conflict': (), 'unknown-is-not-zero': (5, 6, 7, 8, 9),
        'initial-equal': (0, 2), 'impossible-flags': (),
    }
    hypotheses = []
    if name in selected:
        rows = selected[name]
        hypotheses = [
            {'interpretation': 'PrintedOr', 'routes': [_route(ROUTE_TABLE[i]) for i in rows if i < 2]},
            {'interpretation': 'ComparativeAnd', 'routes': [_route(ROUTE_TABLE[i]) for i in rows if i >= 2]},
        ]
        status, reason = (('IndeterminateBranch', 'C8PrimaryConflictUnresolved') if rows else
                          (REFUSE, 'NoCorrelatedSourceRoute'))
    else:
        status = REFUSE
        reason = ('OrderedUniqueReviewedBranchObservationsRequired' if name == 'unordered'
                  else 'C8OrFullNormalClaimNotAdmitted')
    return dict(firstUnresolvedBranchPc=0x5CDF, hypotheses=hypotheses, fullNormalProven=False,
                nativeBranchTaken=None, stopBoundary='STOP_BEFORE_C8_5CDF', status=status, reason=reason)


FRAME_GAPS = [
    'NativeFrameOwnerUnestablished', 'ActualCallReturnAndFramePopNotPerformed',
    'DeviceMemoryAndPhysicalSfApplicabilityRemainConditional',
    'SourceIngressAndHardwareInterferenceNotProvedByFormalEvents',
]
FRAME_CLASS = 'FormalCalRtLifetimeOnly_NotSourceIngressOrNativeReturn'
FRAME_FAILURES = {
    'wrong-owner': (REFUSE, 'FrameCreatorOrSavedWordMismatch', 'before', None),
    'unaligned': (REFUSE, 'AlignedFrameAddressMismatch', 'before', None),
    'missing-generation': (WAIT, 'FrameCreatorWordOrGenerationUnknown', 'before', None),
    'rti': (REFUSE, 'InterruptFrameIsNotOrdinaryCalRt', 'before', None),
    'full': (WAIT, 'FullHelperNormalIngressUnestablished', 'ready', 'STOP_BEFORE_JGT_5CDF'),
    'host-pc': (REFUSE, 'HostSelectedPcIsNotReturnFrontier', 'ready', None),
    'fault': (REFUSE, 'FaultFrontierCannotReturn', 'ready', 'STOP_BEFORE_BRK_5CF8'),
    'wrong-frontier': (REFUSE, 'ReturnFrontierSiteMismatch', 'ready', None),
    'ie-first5cb9': (WAIT, 'FirstIeSoftwareHandoffUnestablished', 'ready', 'STOP_BEFORE_IE_WRITE_5CB9'),
    'ie-second5ccb': (WAIT, 'SecondIeSoftwareHandoffUnestablished', 'ready', 'STOP_BEFORE_IE_WRITE_5CCB'),
    'data-alias': (REFUSE, 'FrameAliasNotExcluded', 'before', None),
    'counter-alias': (REFUSE, 'FrameAliasNotExcluded', 'before', None),
    'equal-high-byte-write': (REFUSE, 'LiveFrameGenerationOverwritten', 'overwrite', None),
    'unknown-write': (WAIT, 'WriterAddressUnknown', 'unknown', None),
    'stale-read': (REFUSE, 'ReturnReadCreatorWordOrGenerationMismatch', 'ready', None),
    'unclosed-nested': (REFUSE, 'UnclosedNestedFrame', 'nested-unclosed', None),
    'nested-wrong-owner': (REFUSE, 'NestedReturnLifoOwnerMismatch', 'nested-live', None),
    'nested-reused-generation': (REFUSE, 'FormalGenerationReused', 'nested-returned', None),
}


def _frame(q, name):
    caller = q['callerPc']
    target, rt, _ = FRAME_SITES[caller]
    sp = q['incomingSsp']
    aligned = (sp // 2) * 2
    pre = (sp - 2) % 65536
    restore = (q['sspBeforeReturn'] + 2) % 65536
    word = caller + 3
    gen = q['frame']['generation']
    stop = f'STOP_BEFORE_RT_{rt:04X}'
    geometry = dict(incomingSsp=sp, frameAddress=aligned, sspAfterCall=pre,
                    sspBeforeReturn=q['sspBeforeReturn'], returnReadAddress=(restore // 2) * 2,
                    sspAfterReturn=restore, savedReturnWord=q['frame']['savedReturnWord'], candidateReturnPc=word)
    status, reason, phase, boundary_stop = FRAME_FAILURES.get(
        name, (OK, 'FormalLifetimeConstraintsSatisfied', 'complete', None))
    if name.startswith('claim-'):
        status, reason, phase = REFUSE, 'NonConditionalFrameLifetimeClaim', 'before'
    log, live = [], []
    retained, balanced, formal_pc, current = None, None, None, pre
    if phase != 'before':
        log.append(dict(kind='FormalCalCreate', creatorPc=caller, address=aligned, savedReturnWord=word,
                        generation=gen, sspBefore=sp, sspAfter=pre))
        live = [gen]
        retained = phase not in ('overwrite', 'unknown')
        if phase == 'unknown':
            retained = None
    if phase == 'overwrite':
        log.append(dict(kind='FormalWrite', ordinal=0, address=0x0401, widthBits=8,
                        generation='G-write', overlappedGenerations=[gen],
                        equalValueDoesNotPreserveGeneration=True))
    if phase.startswith('nested-') or name == 'balanced-nested':
        address = pre - pre % 2
        current = pre - 2
        live.append('G-nested')
        log.append(dict(kind='FormalNestedCalCreate', ordinal=0, creatorPc=0x1000, targetPc=0x1100,
                        address=address, savedReturnWord=0x1003, generation='G-nested',
                        sspBefore=pre, sspAfter=current, encodedSourceEdgeEstablished=False))
        if phase == 'nested-returned' or name == 'balanced-nested':
            log.append(dict(kind='FormalNestedLifetimeClose', ordinal=1, generation='G-nested',
                            address=address, candidateReturnPc=0x1003, sspBefore=current, sspAfter=pre))
            live = [gen]
            current = pre
    if phase in ('complete', 'ready'):
        balanced = True
    elif phase == 'nested-unclosed':
        balanced = False
    if phase == 'complete':
        log.append(dict(kind='FormalLifetimeClose', generation=gen, address=aligned, candidateReturnPc=word,
                        sspBefore=pre, sspAfter=restore, frontierClass=q['boundary']['kind'], actualFramePop=None))
        live, formal_pc, current = [], word, restore
    alias = {0x03CA: 'Data03cbAlias', 0x00F6: 'HelperInputOrFaultAlias'}.get(aligned, 'OrdinaryDataCandidate')
    state = dict(symbolicSsp=current, liveFrameGenerations=live, frameGenerationRetained=retained,
                 balancedNesting=balanced, formalReturnedPc=formal_pc, lifetimeClosedConditionally=status == OK)
    return dict(procedure='helper_rt_frame_lifetime', classification=FRAME_CLASS, status=status, reason=reason,
                sourceBinding=q['sourceBinding'], callerPc=caller, calleeEntryPc=target, returnSitePc=rt,
                geometry=geometry, frameGeneration=gen, frameAlias=alias, state=state, formalEvents=log,
                boundary=q['boundary'], stopBoundary=boundary_stop or stop,
                unresolvedConstraints=FRAME_GAPS + ([] if status == OK else [reason]),
                formalConstraintsSatisfied=status == OK, sourcePathEstablished=False,
                sourceChainEstablished=False, nativeFrameOwnerEstablished=False, actualFramePop=None)


def _chain(case):
    name = case['id']
    fixtures = case['input']['frames']
    results = [_frame(frame, name) for frame in fixtures]
    relations = []
    missing = 'FullHelper5CD9ToDetachedRT5CF9'
    status, reason = WAIT, 'FullHelperIngressStillUnestablished'
    if name == 'chain-native-claim':
        status, reason = REFUSE, 'NonConditionalMultiFrameClaim'
    elif name == 'chain-reused-generation':
        status, reason = REFUSE, 'SequentialFrameGenerationReused'
    else:
        for index, (source, target) in enumerate(((0x276D, 0x2777), (0x277A, 0x27D0))):
            relations.append(dict(fromPc=source, toPc=target, sameAlignedSlot=True,
                                  oldGeneration=results[index]['frameGeneration'],
                                  newGeneration=results[index + 1]['frameGeneration'],
                                  priorLifetimeClosedConditionally=True, stackPointerMatches=True,
                                  suppliedHandoffQualified=name != 'chain-missing-handoff' or index == 0,
                                  sourceConnectionEstablished=False))
        if name == 'chain-missing-handoff':
            reason, missing = 'IntercallHandoffPremiseUnestablished', 'Intercall_277A_27D0'
    satisfied = name == 'chain-formal-not-source'
    return dict(procedure='cold_multi_frame_chain', classification=FRAME_CLASS, status=status, reason=reason,
                frameResults=results, pairwiseRelations=relations, formalSequenceConstraintsSatisfied=satisfied,
                firstMissingHandoff=missing, sourceChainEstablished=False, nativeFrameOwnerEstablished=False,
                actualFramePop=None, unresolvedConstraints=['C8PrimaryConflictUnresolved',
                    'FullHelperNormalIngressUnestablished', *FRAME_GAPS],
                stopBoundary='STOP_BEFORE_JGT_5CDF' if satisfied else 'STOP_BEFORE_CAL_276A')


def _lineage(case):
    name, q = case['id'].removeprefix('lineage-'), case['input']
    omissions = {
        'mode-claim': 'NonConditionalPostHelperClaim',
        'runtime-claim': 'NonConditionalPostHelperClaim',
        'usp-outside-prefix': 'WriterEventOutsidePreHelperWindow',
    }
    failures = {
        'stale': (WAIT, 'RequestedPostHelperGenerationUnlinked'),
        'unbound-interference': (WAIT, 'HelperMappingOrInterferenceUnestablished'),
        'wrong-frame': (REFUSE, 'WrongProspectiveHelperFrameCreator'),
        'reused-generation': (REFUSE, 'ProspectiveHelperFrameGenerationReused'),
        'same-byte-new-owner': (WAIT, 'ProspectiveHelperFrameReownsData03cb'),
        'index3-alias': (WAIT, 'ProspectiveHelperFrameReownsData03d1'),
        'counter-alias': (REFUSE, 'CounterAliasCannotPreserveCandidateReturn'),
    }
    writer = None if name in omissions else old_writer(q['writerQuery'])
    candidate = None if writer is None else writer['state']['candidate']
    state = dict(candidateGeneration=None if candidate is None else candidate['generation'],
                 data03cbAfterFormalCall=None, data03d1AfterFormalCall=None, sameValue03cbFrameWrite=None,
                 sameValue03d1FrameWrite=None, formalFrame=None, counterFrameHazard=None,
                 conditionalHelperBodyRetainedGeneration=None, selectedHelperFrontier=None,
                 connectedModeRead=False, nativeOwner=None)
    status, reason = OK, 'HelperBodyFootprintPreservesData03cbGeneration'
    if name in omissions:
        status, reason = REFUSE, omissions[name]
    elif name == 'repeat-index5':
        status, reason = writer['status'], writer['reason']
    elif name in failures:
        status, reason = failures[name]
    if name in ('disjoint', 'repeat-index3', 'same-byte-new-owner', 'index3-alias', 'counter-alias'):
        frame = q['helperFrame']
        gen = frame['generation']
        addr = frame['incomingSsp'] // 2 * 2
        state.update(formalFrame=dict(creatorPc=0x2777, address=addr, widthBits=16,
                     returnCandidate=0x277A, generation=gen, effectClass='FormalWriteOnly'),
                     data03cbAfterFormalCall=candidate, data03d1AfterFormalCall=q['data03d1'])
        high = dict(value=0x27, knownBits={}, generation=gen)
        if name == 'same-byte-new-owner':
            state.update(data03cbAfterFormalCall=dict(high, writerPc=0x2777, iterationId=None),
                         sameValue03cbFrameWrite=True)
        elif name == 'index3-alias':
            state.update(data03d1AfterFormalCall=high, sameValue03d1FrameWrite=True)
        elif name == 'counter-alias':
            state['counterFrameHazard'] = dict(counterAddress=0xF7, savedHighBefore=0x27,
                decrementHighCandidate=0x26, incrementHighCandidate=0x28, nonzeroUnderBothUpdates=True,
                originalReturnWordPreserved=False, requiresAdmittedFaultArm=True)
        else:
            state['conditionalHelperBodyRetainedGeneration'] = candidate['generation']
    return dict(status=status, reason=reason, sourceScope=[
                    0x2777, 0x5CB4, 0x5CD9, 0x5CDC, 0x5CDF, 0x5CEF, 0x5CF1, 0x5CF4, 0x5CF6, 0x5CF8, 0x5CF9],
                stopBoundary='STOP_BEFORE_HELPER_5CD9' if status == OK else 'STOP_BEFORE_CAL_2777', state=state,
                bodyWriteScope='SelectedScb0ConditionalDataMapping',
                bodyWriterFootprints=[dict(pc=pc, address=address, widthBits=width) for pc, address, width in
                    ((0x5CD9, 0x84, 16), (0x5CEF, 0xAF, 8), (0x5CF1, 0xF7, 8), (0x5CF6, 0xF5, 8))],
                possibleStaticTermini=['STOP_BEFORE_BRK_5CF8', 'STOP_BEFORE_RT_5CF9'],
                unresolvedConstraints=['PrimaryC8ConflictUnresolved', 'FullHelperNormalIngressUnestablished',
                                       'NativeModeRead60ccUnbound'] + ([] if status == OK else [reason]),
                frozenWriter=writer)


def expected(case):
    return {
        'helper_ingress_proof': _ingress,
        'helper_normal_feasibility': _feasibility,
        'helper_rt_frame_lifetime': lambda item: _frame(item['input'], item['id'].removeprefix('frame-')),
        'cold_multi_frame_chain': _chain,
        'data03cb_post_helper_lineage': _lineage,
    }[case['operation']](case)
