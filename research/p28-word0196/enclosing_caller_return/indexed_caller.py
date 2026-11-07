"""Conditional entry to the indexed acquisition, without executing CAL or RT."""

from copy import deepcopy

from mode_caller_continuity.data03cb_writers import WRITER_SITES, data03cb_indexed_writer

from .state import Boundary, Effects, need


ENTRY = 0x5C86
IRQH = 0x0019
CALLER_ENTRY_DD = {0x276A: 1, 0x2B64: 0}
SCOPE = tuple(sorted((ENTRY, 0x5CA0, 0x5CA3, 0x5CCE, *WRITER_SITES)))


def _clear_irqh_intent(effects):
    """Evaluate the documented old-bit predicate using the supplied operand."""
    pc = 0x5CA0
    before = effects.state['sfrReadbacks']['0019']
    possible = effects.symbolic_readback(pc, IRQH)
    old_bits = {(value >> 4) & 1 for value in possible}
    old_bit = next(iter(old_bits)) if len(old_bits) == 1 else None
    cleared_bytes = {value & 0xEF for value in possible}
    cleared = next(iter(cleared_bytes)) if len(cleared_bytes) == 1 else None
    cleared_bits = {} if cleared is not None else {**before['knownBits'], '4': 0}
    effects.r['zf'] = None if old_bit is None else 1 - old_bit

    effects._event(pc, IRQH, [before['value']], [cleared], 'BitClear',
                   'SuppliedIRQHReadback', 'SOFTWARE_SFR_INTENT', [before['generation']])
    event = effects.journal[-1]
    event['sameDeclaredValue'] = event.pop('sameValue')
    event.update(effectClass='StaticRomSfrWriteIntent_NotPerformedIO', selectedBit=4,
                 priorBit=old_bit, knownBitsBefore=deepcopy(before['knownBits']),
                 knownBitsAfter=cleared_bits, actualHardwareObservation=None)
    effects.step(pc, 0x5CA3)
    return deepcopy(event)


def indexed_acquisition_caller(query):
    """Model the page-qualified, timer-bypass route to the frozen writer or fault marker."""
    need(type(query) is dict and set(query) == {'inputClass', 'callerPc', 'snapshot', 'entryEstablished'},
         'ClosedIndexedCallerQueryRequired')
    caller_pc = query['callerPc']
    need(type(caller_pc) is int and 0 <= caller_pc <= 0xFFFF, 'TypedIndexedCallerPcRequired')
    entry = query['entryEstablished']
    need(entry is None or type(entry) is bool, 'TypedIndexedEntryPremiseRequired')
    effects = Effects(query['snapshot'], 'indexed_acquisition_caller', SCOPE)
    need(type(query['inputClass']) is str and query['inputClass'] == effects.input['inputClass'],
         'InputClassMustMatchSnapshot')
    effects.specific.extend(('ConditionalCalleeEntryOnly', 'IrqhClearIsSoftwareIntentOnly',
                             'IndexedReturnFrameUnresolved', 'PostIndexedSuffixUnreviewed'))
    caller = None if caller_pc not in CALLER_ENTRY_DD else {
        'callerPc': caller_pc, 'calleeTarget': ENTRY, 'returnSiteCandidate': caller_pc + 3,
        'listedEntryDD': CALLER_ENTRY_DD[caller_pc]}
    intent = child = None
    try:
        if caller is None:
            effects.halt('OutsideVerifiedScope', 'UnreviewedIndexedCaller', None)
        if entry is not True:
            effects.halt('OutsideVerifiedScope', 'IndexedCalleeEntryNotEstablished', ENTRY)
        effects.admit(ENTRY)
        lrb = effects.r['lrb']
        if lrb is None or lrb & 0x1FE0 != 0x0040:
            effects.halt('OutsideVerifiedScope', 'AcquisitionPage0200NotEstablished', ENTRY)
        flag = effects.read_bit(ENTRY, 0x0230, 3)
        if not effects.branch(ENTRY, None if flag is None else flag == 0, 0x5CA0, 0x5C89):
            effects.halt('OutsideVerifiedScope', 'TimerAndIePathUnestablished', 0x5C89)

        intent = _clear_irqh_intent(effects)
        zf = effects.r['zf']
        if effects.branch(0x5CA3, None if zf is None else zf == 1, 0x5CCE, 0x5CA5):
            effects.store(0x5CCE, 0x00F5, [0x4A], 'ImmediateStore', 'Literal')
            effects.step(0x5CCE, 0x5CD2)
            result = effects.finish('IndexedAcquisitionFaultMarkerStored', 0x5CD2)
        else:
            child = data03cb_indexed_writer(effects.m2cu_snapshot())
            effects.absorb(child)
            result = effects.result(child['status'], child['reason'], child['boundary'], child['outcome'])
    except Boundary as boundary:
        result = effects.result(boundary.status, boundary.reason, boundary.pc)

    return {**result, 'caller': caller, 'irqhClearIntent': intent,
            'selectedIndex': None if child is None else child['selectedIndex'],
            'conditionalData03cbWriterEstablished': child is not None and child['conditionalData03cbWriterEstablished']}
