"""Invented queries. No target instruction bytes or private memory values."""
from copy import deepcopy

from cold_return_c8_writer_proof.corpus import acquisition, indexed_event, usp_query, writer_query

FRAME_BINDING = '7e4ba87467d98becfeff774b92bfdf2c3aeca07e88baf7b713fd9aafba14c9f8'
FRAME_SITES = {
    0x276A: (0x5C86, 0x5CCD, FRAME_BINDING),
    0x2777: (0x5CD9, 0x5CF9, 'M2cyStatic2777FrameV1'),
    0x27D0: (0x5F45, 0x60E4, FRAME_BINDING),
}
CLASS = 'SyntheticTestInput'


def frame_query(caller, generation, ssp=0x0401):
    target, rt, source = FRAME_SITES[caller]
    frame = {'address': ssp - ssp % 2, 'creatorPc': caller,
             'savedReturnWord': caller + 3, 'generation': generation}
    return {
        'inputClass': CLASS, 'sourceBinding': source, 'callerPc': caller,
        'declaredTarget': target, 'returnSitePc': rt, 'incomingSsp': ssp,
        'sspBeforeReturn': (ssp - 2) % 65536,
        'frame': {'kind': 'NormalCall', **frame}, 'returnEvidence': dict(frame),
        'boundary': {'kind': 'DetachedNormalFrontier' if caller == 0x2777 else 'ConditionalSourceFrontier',
                     'pc': rt, 'sourceQualified': True, 'evidenceId': 'InventedFrontier'},
        'premises': {'stackMemoryApplicable': True, 'noAsyncInterference': True, 'windowComplete': True},
        'ieHandoffs': {'first5cb9': True if caller == 0x276A else None,
                       'second5ccb': True if caller == 0x276A else None},
        'events': [], 'claim': 'ConditionalOnly',
    }


def _case(identity, operation, query):
    return {'id': identity, 'operation': operation, 'input': deepcopy(query)}


def frame_cases():
    operation = 'helper_rt_frame_lifetime'
    helper = frame_query(0x2777, 'G-helper')
    indexed = frame_query(0x276A, 'G-indexed')
    mode = frame_query(0x27D0, 'G-mode')
    yield _case('frame-detached', operation, helper)
    yield _case('frame-indexed', operation, indexed)
    yield _case('frame-mode', operation, mode)
    for claim in ('NativeReturn', 'ActualExecution', 'ActualHardware'):
        yield _case('frame-claim-' + claim, operation, {**helper, 'claim': claim})
    for key, value, name in (
        ('creatorPc', 0x276A, 'wrong-owner'), ('address', 0x0401, 'unaligned'),
        ('generation', None, 'missing-generation'), ('kind', 'Interrupt', 'rti'),
    ):
        yield _case('frame-' + name, operation, {**helper, 'frame': {**helper['frame'], key: value}})
    for name, kind, pc in (
        ('full', 'ConditionalSourceFrontier', 0x5CF9),
        ('host-pc', 'HostSelected', 0x5CF9),
        ('fault', 'FaultFrontier', 0x5CF8),
        ('wrong-frontier', 'DetachedNormalFrontier', 0x5CCD),
    ):
        yield _case('frame-' + name, operation, {**helper,
                    'boundary': {**helper['boundary'], 'kind': kind, 'pc': pc}})
    for key in ('first5cb9', 'second5ccb'):
        yield _case('frame-ie-' + key, operation, {**indexed,
                    'ieHandoffs': {**indexed['ieHandoffs'], key: None}})
    yield _case('frame-data-alias', operation, frame_query(0x2777, 'G-alias', 0x03CB))
    yield _case('frame-counter-alias', operation, frame_query(0x2777, 'G-alias', 0x00F7))
    write = {'kind': 'Write', 'address': 0x0401, 'widthBits': 8, 'value': 0x27,
             'generation': 'G-write', 'sourceQualified': True}
    yield _case('frame-equal-high-byte-write', operation, {**helper, 'events': [write]})
    yield _case('frame-unknown-write', operation, {**helper, 'events': [{**write, 'address': None}]})
    yield _case('frame-stale-read', operation, {**helper,
                'returnEvidence': {**helper['returnEvidence'], 'generation': 'G-indexed'}})
    nested = {'kind': 'NestedCall', 'creatorPc': 0x1000, 'targetPc': 0x1100,
              'generation': 'G-nested', 'memoryApplicable': True, 'sourceQualified': True}
    returned = {'kind': 'NestedReturn', 'creatorPc': 0x1000, 'savedReturnWord': 0x1003,
                'generation': 'G-nested', 'sourceQualified': True}
    yield _case('frame-balanced-nested', operation, {**helper, 'events': [nested, returned]})
    yield _case('frame-unclosed-nested', operation, {**helper, 'events': [nested]})
    yield _case('frame-nested-wrong-owner', operation, {**helper,
                'events': [nested, {**returned, 'generation': 'G-other'}]})
    yield _case('frame-nested-reused-generation', operation, {**helper,
                'events': [nested, returned, nested]})
    chain = {'inputClass': CLASS, 'frames': [indexed, helper, mode], 'claim': 'ConditionalOnly',
             'handoffs': [
                 {'fromPc': before, 'toPc': after, 'stackContinuity': True,
                  'sourceQualified': True, 'evidenceId': 'InventedHandoff'}
                 for before, after in ((0x276D, 0x2777), (0x277A, 0x27D0))]}
    operation = 'cold_multi_frame_chain'
    yield _case('chain-formal-not-source', operation, chain)
    yield _case('chain-native-claim', operation, {**chain, 'claim': 'NativeReturn'})
    changed = deepcopy(chain)
    changed['handoffs'][1]['sourceQualified'] = None
    yield _case('chain-missing-handoff', operation, changed)
    changed = {**chain, 'frames': [indexed, frame_query(0x2777, 'G-indexed'), mode]}
    yield _case('chain-reused-generation', operation, changed)


def helper_cases():
    ingress = {'inputClass': CLASS, 'sourceBinding': 'M2dbHelperSourceReviewV1', 'claim': 'Inspect'}
    for pc in (0x5CE1, 0x5CE9):
        for transfer in ('EncodedDirect', 'VcalVector', 'OrdinaryIntactReturn', 'UnboundIndirect'):
            yield _case(f'ingress-{pc:04x}-{transfer}', 'helper_ingress_proof',
                        {**ingress, 'entryPc': pc, 'transferClass': transfer})
    ordinary = {**ingress, 'entryPc': 0x5CE9, 'transferClass': 'OrdinaryIntactReturn'}
    for name, changed in (('positive', {'claim': 'AssertIngress'}), ('native', {'claim': 'NativeEnter'}),
                          ('unbound', {'sourceBinding': None}), ('full', {'entryPc': 0x5CD9})):
        yield _case('ingress-' + name, 'helper_ingress_proof', {**ordinary, **changed})

    def flags(pc, cf, zf):
        return {'pc': pc, 'cf': cf, 'zf': zf}

    initial_equal = flags(0x5CDF, 0, 1)
    later_equal = flags(0x5CE7, 0, 1)
    for name, observations in (
        ('all', []),
        ('later-equal', [later_equal]),
        ('later-greater', [flags(0x5CE7, 0, 0)]),
        ('individually-feasible-conflict', [initial_equal, later_equal]),
        ('unknown-is-not-zero', [flags(0x5CE7, None, None)]),
        ('initial-equal', [initial_equal]),
        ('impossible-flags', [flags(0x5CDF, 1, 1)]),
        ('unordered', [later_equal, initial_equal]),
    ):
        yield _case('route-' + name, 'helper_normal_feasibility', {**ingress, 'observations': observations})
    for claim in ('ResolveOr', 'ResolveAnd', 'AssertFullNormal'):
        yield _case('route-' + claim, 'helper_normal_feasibility',
                    {**ingress, 'observations': [], 'claim': claim})


def lineage_cases():
    seed = writer_query(seed=acquisition(adcr0h=0x27))
    fixture = {
        'inputClass': CLASS, 'sourceBinding': 'M2dbHelperWriterFootprintV1', 'writerQuery': seed,
        'requestedGeneration': seed['requestedGeneration'], 'helperScb': 0, 'noInterference': True,
        'data03d1': {'value': 0x27, 'knownBits': {}, 'generation': 'InventedIndex3Slot'},
        'helperFrame': {'incomingSsp': 0x047F, 'creatorPc': 0x2777, 'generation': 'NewHelperFrame',
                        'memoryApplicable': True},
        'claim': 'ConditionalOnly',
    }
    operation = 'data03cb_post_helper_lineage'
    yield _case('lineage-disjoint', operation, fixture)
    for name, ssp in (('same-byte-new-owner', 0x03CB), ('index3-alias', 0x03D1), ('counter-alias', 0x00F7)):
        yield _case('lineage-' + name, operation, {**fixture,
                    'helperFrame': {**fixture['helperFrame'], 'incomingSsp': ssp}})
    for name, changed in (
        ('stale', {'requestedGeneration': 'Stale'}),
        ('unbound-interference', {'noInterference': None}),
        ('mode-claim', {'claim': 'ModeConsumerReached'}),
        ('runtime-claim', {'claim': 'RuntimeAdmission'}),
        ('wrong-frame', {'helperFrame': {**fixture['helperFrame'], 'creatorPc': 0x276A}}),
        ('reused-generation', {'helperFrame': {**fixture['helperFrame'],
                                              'generation': seed['requestedGeneration']}}),
        ('repeat-index3', {'writerQuery': {**seed, 'events': [indexed_event(3)]}}),
        ('repeat-index5', {'writerQuery': {**seed, 'events': [indexed_event(5, 0x27)]}}),
        ('usp-outside-prefix', {'writerQuery': {**seed, 'events': [
            {'kind': 'Usp27B2', 'id': 'InventedUsp', 'proof': usp_query(0x0419)}]}}),
    ):
        yield _case('lineage-' + name, operation, {**fixture, **changed})


def cases():
    yield from helper_cases()
    yield from frame_cases()
    yield from lineage_cases()
