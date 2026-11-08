"""Invented inputs for M2da, separated from authenticated source bytes."""

from copy import deepcopy
from itertools import product

from cold_return_c8_writer_proof.corpus import (
    extended_query as accepted_helper_query,
    frame_event as accepted_competing_frame,
    indexed_event as accepted_indexed_event,
    return_path_query as accepted_frame_query,
    source_join_query as accepted_join_query,
    usp_query as accepted_usp_query,
    writer_query as accepted_writer_query,
)
from enclosing_caller_return.corpus import frame_query as accepted_mode_frame
from mode_middle_corridor.corpus import continuation_query as accepted_mode_query, entry_query as accepted_mode_entry


INPUT = 'SyntheticTestInput'
HELPER_BINDING = 'M2daHelperSourceReviewV1'
HELPER_EDGES = {0x5CDF: (0x5CED, 0x5CE1), 0x5CE3: (0x5CF9, 0x5CE5),
                0x5CE7: (0x5CED, 0x5CE9), 0x5CEB: (0x5CF9, 0x5CED)}


def _case(identity, operation, query):
    return {'id': identity, 'operation': operation, 'input': query}


def _variants(operation, prefix, base, variants):
    for name, replacements in variants:
        query = deepcopy(base)
        for path, value in replacements.items():
            current = query
            *parents, key = path.split('.')
            for segment in parents:
                current = current[int(segment)] if isinstance(current, list) else current[segment]
            current[int(key) if isinstance(current, list) else key] = deepcopy(value)
        yield _case(f'{prefix}-{name}', operation, query)


def c8_primary_query():
    return {'inputClass': INPUT, 'sourceIds': ['OKI66201Sep1991', 'SameEditionMirror',
            'OKI1998InstructionList', 'OKI500S1999', 'Chapter3WithoutEdition',
            'MAC66KNov1993', 'OKIJapanSpec1998'], 'claim': 'KeepConflict'}


def primary_cases():
    yield from _variants('c8_primary_evidence_adjudication', 'primary', c8_primary_query(), (
        ('deduplicated-and-family', {}),
        ('printed-only', {'sourceIds': ['OKI66201Sep1991']}),
        ('mirror-only', {'sourceIds': ['SameEditionMirror']}),
        ('related-opcode', {'sourceIds': ['OKI500S1999']}),
        ('listing-without-condition', {'sourceIds': ['OKI1998InstructionList']}),
        ('assembler-mnemonic-only', {'sourceIds': ['MAC66KNov1993']}),
        ('device-scope-only', {'sourceIds': ['OKIJapanSpec1998']}),
        ('unattributed-chapter', {'sourceIds': ['Chapter3WithoutEdition']}),
        ('unknown-erratum', {'sourceIds': ['UnauthenticatedErratum']}),
        ('unreviewed-id', {'sourceIds': ['InventedOtherEdition']}),
        ('emulator', {'sourceIds': ['EmulatorBehavior']}),
        ('no-evidence', {'sourceIds': []}),
        ('force-or', {'claim': 'ResolveOr'}),
        ('force-and', {'claim': 'ResolveAnd'}),
        ('execution-claim', {'claim': 'NativeExecute'}),
    ))


def c8_feasibility_query(pc=0x5CDF, cf=None, zf=None, hypothesis='Both'):
    target, fallthrough = HELPER_EDGES[pc]
    return {'inputClass': INPUT, 'sourceBinding': HELPER_BINDING, 'pc': pc,
            'target': target, 'fallthrough': fallthrough, 'cf': cf, 'zf': zf, 'hypothesis': hypothesis}


def feasibility_cases():
    op = 'c8_source_feasibility'
    for pc, cf, zf, hypothesis in product(HELPER_EDGES, (None, 0, 1), (None, 0, 1),
                                          ('Both', 'PrintedOr', 'ComparativeAnd')):
        yield _case(f'feasible-{pc:04x}-{hypothesis}-{cf}-{zf}', op,
                    c8_feasibility_query(pc, cf, zf, hypothesis))
    yield from _variants(op, 'feasible', c8_feasibility_query(), (
        ('missing-source', {'sourceBinding': None}),
        ('wrong-source', {'sourceBinding': 'RelatedFamily500S'}),
        ('wrong-target', {'target': 0x5CF9}),
        ('wrong-fallthrough', {'fallthrough': 0x5CE3}),
        ('unknown-site', {'pc': 0x5CD9}),
    ))


def helper_ingress_query(entry=0x5CE1):
    return {'inputClass': INPUT, 'entryPc': entry, 'predecessorPc': entry - 2,
            'sourceBinding': HELPER_BINDING, 'claim': 'Inspect'}


def ingress_cases():
    op = 'helper_normal_entry_provenance'
    for entry in (0x5CE1, 0x5CE9):
        yield from _variants(op, f'ingress-{entry:04x}', helper_ingress_query(entry), (
            ('exact-c8', {}),
            ('unknown-predecessor', {'predecessorPc': None}),
            ('invented-predecessor', {'predecessorPc': 0x2777}),
            ('missing-binding', {'sourceBinding': None}),
            ('invented-direct-ingress', {'claim': 'AssertAlternate'}),
            ('native-ingress', {'claim': 'NativeEnter'}),
        ))
    yield _case('ingress-unknown-site', op, helper_ingress_query(0x5CF9))


def helper_continuation_query(entry='Detached5CE9', adcr1h=0x51):
    prior = accepted_helper_query(value=adcr1h)['helperQuery']
    prior['thresholds'].update({'5CE1': 0x52, '5CE5': 0x51, '5CE9': 0x51})
    return {'inputClass': INPUT, 'sourceBinding': HELPER_BINDING, 'entry': entry,
            'entryHandoff': True if entry != 'Full' else None,
            'prefixHandoff': True if entry == 'Detached5CE9' else None, 'helperQuery': prior}


def continuation_cases():
    op = 'helper_normal_continuation'
    yield from _variants(op, 'helper-5ce9', helper_continuation_query(), (
        ('equal-jge', {}),
        ('greater-jge', {'helperQuery.thresholds.5CE9': 0x50}),
        ('less-jge', {'helperQuery.thresholds.5CE9': 0x52}),
        ('unknown-jge', {'helperQuery.thresholds.5CE9': None}),
        ('missing-prefix', {'prefixHandoff': None}),
        ('missing-entry', {'entryHandoff': None}),
        ('explicit-refusal', {'entryHandoff': False}),
        ('unproved-source', {'sourceBinding': None}),
        ('first-jge-already-normal', {'helperQuery.thresholds.5CE1': 0x50}),
        ('second-c8-already-taken', {'helperQuery.thresholds.5CE5': 0x50}),
        ('stale-d1', {'helperQuery.snapshot.generations.03D1': 'CompetingD1Generation'}),
        ('f7-unknown-no-fault-write', {'helperQuery.thresholds.5CE9': 0x52,
                                      'helperQuery.counterF7.slot.value': None}),
    ))
    yield _case('helper-5ce9-d1-unknown', op, helper_continuation_query(adcr1h=None))
    yield from _variants(op, 'helper-5ce1', helper_continuation_query('Detached5CE1'), (
        ('frozen-taken', {'helperQuery.thresholds.5CE1': 0x51}),
        ('frozen-not-taken', {}),
        ('missing-entry', {'entryHandoff': None}),
    ))
    yield from _variants(op, 'helper-full', helper_continuation_query('Full'), (
        ('frozen-disagreement', {}),
        ('frozen-fault', {'helperQuery.thresholds.5CDD': 0x50}),
        ('frozen-stale-f7', {'helperQuery.thresholds.5CDD': 0x50,
                            'helperQuery.counterF7.slot.generation': 'StaleFirstCallCounter'}),
        ('refuse-detached-transfer', {'entryHandoff': True}),
    ))


def frame_chain_query():
    return {'inputClass': INPUT, 'frameQuery': accepted_frame_query(), 'ie5cb9': True,
            'ie5ccb': True, 'writes': [], 'claim': 'ConditionalOnly'}


def frame_write(stage='IndexedLive', address=0x047F, width=8, path=True):
    return {'stage': stage, 'address': address, 'widthBits': width,
            'generation': 'InventedInterveningWrite', 'pathEstablished': path}


def frame_chain_cases():
    op = 'cold_frame_generation_chain'
    yield from _variants(op, 'frame', frame_chain_query(), (
        ('two-distinct-generations-same-address', {}),
        ('first-ie-unknown', {'ie5cb9': None}),
        ('second-ie-blocked', {'ie5ccb': False}),
        ('unproved-helper-return', {'frameQuery.helperNormalBoundary': None}),
        ('missing-saved-byte', {'frameQuery.helperFrame.frameQuery.frame.low': None}),
        ('missing-creator', {'frameQuery.indexedFrame.frameQuery.frame.creatorPc': None}),
        ('stale-generation', {'frameQuery.helperFrame.expectedFrameGeneration': 'StaleFrame'}),
        ('unknown-stack-address', {'frameQuery.helperFrame.frameQuery.incomingSsp': None}),
        ('rti-does-not-prove-rt', {'frameQuery.helperFrame.frameQuery.frame.kind': 'Interrupt'}),
        ('mismatched-saved-pc', {'frameQuery.helperFrame.frameQuery.frame.low': 0x6D}),
        ('unbalanced-stack', {'frameQuery.helperFrame.frameQuery.premises.balancedNesting': False}),
        ('indexed-byte-overlap', {'writes': [frame_write()]}),
        ('helper-word-aligned-overlap', {'writes': [frame_write('HelperLive', width=16)]}),
        ('same-address-between-calls', {'writes': [frame_write('BetweenCalls')]}),
        ('unknown-address-live-frame', {'writes': [frame_write(address=None)]}),
        ('unknown-path-live-frame', {'writes': [frame_write(path=None)]}),
        ('skipped-overlap', {'writes': [frame_write(path=False)]}),
        ('nearby-disjoint-byte', {'writes': [frame_write(address=0x0480)]}),
        ('reversed-frame-window', {'writes': [frame_write('HelperLive', 0x0480), frame_write('IndexedLive', 0x0481)]}),
        ('control-alias-write', {'writes': [frame_write(address=0x0004)]}),
        ('register-bank-alias-write', {'writes': [frame_write(address=0x0081, width=16)]}),
        ('intervening-generation-reused', {'writes': [dict(frame_write(address=0x0480), generation=
             accepted_frame_query()['indexedFrame']['frameQuery']['frame']['generation'])]}),
        ('native-return-refused', {'claim': 'NativeReturn'}),
    ))


def cold_graph_query():
    return {'inputClass': INPUT, 'joinQuery': accepted_join_query(), 'frameChain': frame_chain_query(),
            'requestedGeneration': 'ConditionalEffect:data03cb_indexed_writer:5CB4:3',
            'claim': 'ConditionalOnly'}


def cold_graph_cases():
    op = 'cold_normal_mode_source_join'
    yield from _variants(op, 'cold-graph', cold_graph_query(), (
        ('fault-boundary', {}),
        ('disputed-c8', {'joinQuery.helperArgs.thresholds.5CDD': 0xD3}),
        ('ie-blocked', {'joinQuery.coldQuery.postIe': None}),
        ('mode-without-frame-chain', {'frameChain': None}),
        ('frame-write-overlap', {'frameChain.writes': [frame_write()]}),
        ('uncarried-generation', {'requestedGeneration': 'InventedWrongGeneration'}),
        ('no-requested-generation', {'requestedGeneration': None}),
        ('helper-args-unbound', {'joinQuery.helperArgs': None}),
        ('f7-predecessor-unbound', {'joinQuery.helperHandoff': None}),
        ('data03cb-word-overlap', {'frameChain.writes': [frame_write('BetweenCalls', 0x03CB, 16)]}),
        ('later-helper-overlap-cannot-advance', {'frameChain.writes': [frame_write('HelperLive')]}),
        ('non-index-5', {'joinQuery.coldQuery.prefixQuery.snapshot.sfrReadbacks.0024.value': 0x67}),
        ('native-claim-refused', {'claim': 'NativeModeReach'}),
    ))


def cold_mode_window_query(usp=0x0180):
    return {'inputClass': INPUT, 'sourceBinding': 'M2daColdModeWindowV1',
            'writerQuery': accepted_writer_query(), 'uspProof': accepted_usp_query(usp),
            'modeFrame': accepted_mode_frame(),
            'premises': {'detached277a': True, 'reviewedPath': True, 'noInterference': True},
            'claim': 'ConditionalOnly'}


def window_cases():
    op = 'cold_to_mode_intervening_writes'
    yield from _variants(op, 'window', cold_mode_window_query(), (
        ('retained-disjoint-usp', {}),
        ('usp-0419-replaces-same-value', {'uspProof': accepted_usp_query()}),
        ('unbound-usp', {'uspProof': accepted_usp_query(None)}),
        ('usp-changed-generation', {'uspProof.currentUsp.generation': 'DifferentUspGeneration'}),
        ('word-overlap-03ca', {'modeFrame': accepted_mode_frame(ssp=0x03CB)}),
        ('word-overlap-at-earlier-call', {'writerQuery.events': [accepted_competing_frame()]}),
        ('unknown-mode-ssp', {'modeFrame.incomingSsp': None}),
        ('unbalanced-mode-ssp', {'modeFrame.premises.balancedNesting': False}),
        ('wrong-mode-owner', {'modeFrame.frame.creatorPc': 0x2777}),
        ('detached-entry-unproved', {'premises.detached277a': None}),
        ('path-unproved', {'premises.reviewedPath': None}),
        ('interference-unproved', {'premises.noInterference': False}),
        ('unknown-mode-binding', {'sourceBinding': None}),
        ('native-owner-refused', {'claim': 'NativeOwner'}),
        ('later-index-5-overwrites-equal', {'writerQuery.events': [accepted_indexed_event(5)]}),
        ('later-index-3-preserves', {'writerQuery.events': [accepted_indexed_event(3)]}),
    ))


def mode_read_query(prefix=None):
    window = cold_mode_window_query()
    mode = accepted_mode_query(prefix)
    snap = mode['prefixQuery']['snapshot']
    seed = window['writerQuery']['initialTimeline']['events'][0]
    snap['memory']['03CB'] = seed['adcr0h']
    snap['generations']['03CB'] = seed['adcr0Generation']
    return {'inputClass': INPUT, 'windowQuery': window, 'modeQuery': mode, 'claim': 'ConditionalOnly'}


def mode_read_cases():
    op = 'data03cb_to_60cc_source_proof'
    yield from _variants(op, 'mode', mode_read_query(), (
        ('detached-mode-read', {}),
        ('equal-byte-stale-generation', {'modeQuery.prefixQuery.snapshot.generations.03CB': 'StaleEqualByte'}),
        ('different-byte-same-generation', {'modeQuery.prefixQuery.snapshot.memory.03CB': 0x9B}),
        ('bad-caller', {'modeQuery.prefixQuery.callerPc': 0x4069}),
        ('usp-owner-missing', {'modeQuery.prefixQuery.snapshot.registers.usp': None}),
        ('unknown-dd', {'modeQuery.prefixQuery.snapshot.registers.dd': None}),
        ('mode-no-interference-unproved', {'modeQuery.prefixQuery.snapshot.assumptions.noInterference': False}),
        ('overlapping-usp-window', {'windowQuery.uspProof': accepted_usp_query()}),
        ('frame-overlaps-other-mode-snapshot-byte', {'windowQuery.modeFrame': accepted_mode_frame(ssp=0x03CE)}),
        ('native-claim', {'claim': 'ActualHardware'}),
    ))
    yield _case('mode-branch-without-60cc', op, mode_read_query(accepted_mode_entry(r0=1)))


def cases():
    for suite in (primary_cases, feasibility_cases, ingress_cases, continuation_cases,
                  frame_chain_cases, cold_graph_cases, window_cases, mode_read_cases):
        yield from suite()
