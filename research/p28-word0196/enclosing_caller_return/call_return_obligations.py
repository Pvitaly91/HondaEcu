"""Ordinary CAL and RT proof obligations, with hypothetical frame contents."""
from .state import formal_result, input_class, label, need, number, shape, tri

FRAME_SOURCE = '7e4ba87467d98becfeff774b92bfdf2c3aeca07e88baf7b713fd9aafba14c9f8'
CALL_SITES = {
    0x276A: (0x5C86, 0x5CCD),
    0x2B64: (0x5C86, 0x5CCD),
    0x27D0: (0x5F45, 0x60E4),
    0x4069: (0x5F45, 0x60E4),
}
SCOPE = (*CALL_SITES, 0x5CCD, 0x60E4)
PREMISES = ('matchingEntryReturn', 'stackMemoryApplicable', 'balancedNesting', 'frameIntegrity', 'noAliasInterference')
FIELDS = ('inputClass', 'sourceBinding', 'callerPc', 'declaredTarget', 'returnPc',
          'incomingSsp', 'sspBeforeReturn', 'frame', 'premises', 'claim')


def frame_alias(address, mode):
    if address is None:
        return None
    special = {0: 'SspSelfAlias', 2: 'LrbAlias', 4: 'PswAlias', 6: 'AccumulatorAlias',
               0x03CA: 'Data03cbAlias', 0x0356: 'ModeBitAlias', 0x0208: 'LocalR0Alias'}
    if address in special:
        return special[address]
    if address < 0x80:
        return 'OtherSfrOrReserved'
    if address < 0xC0:
        return 'PointingBankAlias'
    if mode and address == 0x0382:
        return 'ModeWordAlias'
    if mode and address in (0x020A, 0x0216, 0x0218, 0x0226):
        return 'ModeCalleeDataAlias'
    if not mode and address == 0x0230:
        return 'IndexedGuardAlias'
    if not mode and 0x03C6 <= address <= 0x03D4:
        return 'IndexedCalleeDataAlias'
    return 'OrdinaryDataCandidate'


def validate(query):
    shape(query, FIELDS, 'ClosedCallReturnQueryRequired')
    input_class(query['inputClass'])
    need(label(query['sourceBinding']), 'TypedCallSourceBindingRequired')
    need(all(number(query[name], 0xFFFF) for name in
             ('callerPc', 'declaredTarget', 'returnPc', 'incomingSsp', 'sspBeforeReturn')),
         'TypedCallReturnWordsRequired')
    frame = query['frame']
    shape(frame, ('kind', 'address', 'low', 'high', 'creatorPc', 'generation'), 'ClosedFrameRequired')
    need(type(frame['kind']) is str and frame['kind'] in ('NormalCall', 'Interrupt')
         and number(frame['address'], 0xFFFF) and number(frame['creatorPc'], 0xFFFF)
         and number(frame['low'], 255) and number(frame['high'], 255) and label(frame['generation']),
         'TypedFrameRequired')
    shape(query['premises'], PREMISES, 'ClosedFramePremisesRequired')
    need(all(tri(value) for value in query['premises'].values()), 'TypedFramePremisesRequired')
    need(type(query['claim']) is str and query['claim'] in
         ('ConditionalOnly', 'ActualNativeReturn', 'Execute', 'HostSelectedReturn'), 'ClosedFrameClaimRequired')


def call_return_obligations(query):
    validate(query)
    pc, frame = query['callerPc'], query['frame']
    sites = CALL_SITES.get(pc)
    call = None if sites is None else {
        'callerPc': pc, 'target': sites[0], 'length': 3, 'returnCandidatePc': (pc + 3) & 0xFFFF,
        'returnSitePc': sites[1],
    }
    bound = (call is not None and query['sourceBinding'] == FRAME_SOURCE
             and query['declaredTarget'] == call['target'] and query['returnPc'] == call['returnSitePc'])
    geometry = dict.fromkeys(('frameAddress', 'sspAfterCall', 'returnReadAddress', 'sspAfterReturn', 'savedPc'))
    obligations, edges = [], []
    if bound:
        initial, final = query['incomingSsp'], query['sspBeforeReturn']
        if initial is not None:
            geometry.update(frameAddress=initial & 0xFFFE, sspAfterCall=(initial - 2) & 0xFFFF)
        if final is not None:
            after = (final + 2) & 0xFFFF
            geometry.update(returnReadAddress=after & 0xFFFE, sspAfterReturn=after)
        if frame['low'] is not None and frame['high'] is not None:
            geometry['savedPc'] = frame['low'] | (frame['high'] << 8)
        edges.append({'from': pc, 'to': call['target'], 'class': 'ConfirmedCallTarget'})
        obligations.extend((
            {'kind': 'FormalCalWordStore', 'pc': pc, 'address': geometry['frameAddress'],
             'widthBits': 16, 'value': call['returnCandidatePc']},
            {'kind': 'FormalRtWordRead', 'pc': call['returnSitePc'], 'address': geometry['returnReadAddress'],
             'widthBits': 16, 'value': geometry['savedPc']},
        ))
    alias = frame_alias(geometry['frameAddress'], bool(call and call['target'] == 0x5F45))
    missing = [key for key in PREMISES if query['premises'][key] is not True]
    outside, obligation = 'OutsideVerifiedScope', 'IndeterminateObligation'
    if query['claim'] != 'ConditionalOnly':
        status, reason = outside, 'NonConditionalFrameClaim'
    elif call is None:
        status, reason = outside, 'UnreviewedCallSite'
    elif query['sourceBinding'] is None:
        status, reason = obligation, 'CallSourceBindingMissing'
    elif query['sourceBinding'] != FRAME_SOURCE:
        status, reason = outside, 'CallSourceBindingMismatch'
    elif None in (query['declaredTarget'], query['returnPc']):
        status, reason = obligation, 'CallReturnSiteUnspecified'
    elif not bound:
        status, reason = outside, 'CallReturnSourceMismatch'
    elif frame['kind'] != 'NormalCall':
        status, reason = outside, 'InterruptFrameCannotReturnViaRt'
    elif None in (query['incomingSsp'], query['sspBeforeReturn']):
        status, reason = obligation, 'StackPointerUnknown'
    elif query['sspBeforeReturn'] != geometry['sspAfterCall']:
        status, reason = outside, 'UnbalancedStackPointer'
    elif alias != 'OrdinaryDataCandidate':
        status, reason = outside, 'FrameAliasRequiresIndependentProof'
    elif missing:
        status, reason = obligation, 'FramePremisesNotEstablished'
    elif None in (frame['address'], frame['creatorPc'], frame['generation'], geometry['savedPc']):
        status, reason = obligation, 'FrameContentsOrOwnerUnknown'
    elif (frame['address'] != geometry['frameAddress'] or frame['creatorPc'] != pc
          or geometry['savedPc'] != call['returnCandidatePc']):
        status, reason = outside, 'FrameDoesNotMatchCall'
    else:
        status, reason = 'CompleteConditional', 'HypotheticalMatchingFrame'
    complete = status == 'CompleteConditional'
    unresolved = (['ActualNativeFrameOwnershipUnestablished'] if complete else
                  missing if reason == 'FramePremisesNotEstablished' else [reason])
    state = {'call': call, 'geometry': geometry, 'frame': frame, 'alias': alias,
             'formalReturnedPc': call['returnCandidatePc'] if complete else None,
             'nativeFrameOwnerEstablished': False, 'nativeReturnEstablished': False}
    return formal_result('call_return_obligations', query['inputClass'], SCOPE, status, reason,
                         call['returnSitePc'] if call else None, state, missing=unresolved,
                         edges=edges, frame_obligations=obligations)
