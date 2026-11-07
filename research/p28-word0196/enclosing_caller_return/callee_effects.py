"""Conditional clobber footprint of the retained 5F45 graph before RT60E4."""
from native_data0217_011f_bridge.helper_cfg import NODE_ROWS

from .mode_caller import CALLER_CONTEXTS
from .state import formal_result, input_class, need, number, shape, tri

REGISTERS = ('AL', 'AH', 'A', 'CF', 'ZF', 'HC', 'DD', 'MIE', 'OtherPSW', 'LRB', 'SCB',
             'X1', 'X2', 'DP', 'USP', 'SSP', 'SoftwareSfrIntents')
DATA_WRITTEN = ('0208', '0209', '020A', '0216', '0217', '0219', '0227', '0356', '0382', '0383')
DATA_READ_ONLY = ('03C7', '03CB', '03CE', '03CF')
GRAPH_SCOPE = tuple(pc for pc, _, _, _ in NODE_ROWS)
OVERWRITTEN = 'ProvenOverwritten'
UNCHANGED = 'ProvenUnchangedWithinReviewedPath'
UNREVIEWED = 'UnknownDueToUnreviewedPath'
NESTED = 'UnknownDueToNestedCallee'
REGISTER_WRITTEN = frozenset(('AL', 'AH', 'A', 'CF', 'ZF', 'DD', 'OtherPSW', 'DP'))


def callee_clobber_summary(query):
    """The positive premise includes normal path completion and excluded aliases."""
    shape(query, ('inputClass', 'callerPc', 'phase', 'scb', 'contextEstablished'), 'ClosedCalleeClobberQueryRequired')
    input_class(query['inputClass'])
    caller_pc, phase, scb, context = (query[key] for key in ('callerPc', 'phase', 'scb', 'contextEstablished'))
    need(number(caller_pc, 0xFFFF) and number(scb, 7) and tri(context)
         and type(phase) is str and phase in ('ModeCalleeBeforeRt', 'CallerPreEntry'), 'TypedCalleeClobberContextRequired')
    state = {'callerPc': caller_pc, 'phase': phase,
        'registerEffects': dict.fromkeys(REGISTERS, UNREVIEWED),
        'dataEffects': dict.fromkeys((*DATA_WRITTEN, *DATA_READ_ONLY), UNREVIEWED),
        'dpAliasCandidates': [], 'undefinedLogicalPswFlags': [],
        'nestedCallSites': None, 'unreviewedPreEntryCallee': None}

    if caller_pc not in CALLER_CONTEXTS:
        scope, edges, boundary = (), (), None
        status, reason = 'OutsideVerifiedScope', 'UnreviewedModeCaller'
    else:
        edges = ({'from': caller_pc, 'to': 0x5F45, 'classification': 'DirectCallTarget'},)
        if phase == 'CallerPreEntry':
            status = 'IndeterminateObligation'
            if caller_pc == 0x4069:
                scope, boundary = (0x4068, 0x4069), 0x4068
                reason = 'PreEntryCalleeEffectsUnresolved'
                state['unreviewedPreEntryCallee'] = 0x4068
                state['registerEffects'] = dict.fromkeys(REGISTERS, NESTED)
                state['dataEffects'] = dict.fromkeys((*DATA_WRITTEN, *DATA_READ_ONLY), NESTED)
            else:
                scope, boundary = (0x27CE, 0x27D0), 0x27D0
                reason = 'PriorCallerContextUnresolved'
        else:
            scope = GRAPH_SCOPE
            state['nestedCallSites'] = []
            if context is not True:
                status = 'IndeterminateObligation' if context is None else 'OutsideVerifiedScope'
                reason, boundary = 'CalleeContextNotEstablished', 0x5F45
            else:
                status, reason, boundary = 'CompleteConditional', 'ReviewedCalleeClobberFootprints', 0x60E4
                state['registerEffects'] = {name: OVERWRITTEN if name in REGISTER_WRITTEN else UNCHANGED
                                            for name in REGISTERS}
                state['registerEffects']['HC'] = 'ConditionallyOverwritten'
                state['dataEffects'] = {**dict.fromkeys(DATA_WRITTEN, OVERWRITTEN),
                                        **dict.fromkeys(DATA_READ_ONLY, UNCHANGED)}
                banks = range(8) if scb is None else (scb,)
                state['dpAliasCandidates'] = [0x84 + 8 * bank for bank in banks]
                state['undefinedLogicalPswFlags'] = ['CF', 'ZF', 'HC']
    missing = ('NativeCallerEntryAndReturnNotEstablished', 'LogicalPswhFlagCaveatRetained') if (
        status == 'CompleteConditional') else (reason,)
    return formal_result('callee_clobber_summary', query['inputClass'], scope, status, reason, boundary, state,
                         edges=edges, missing=missing)
