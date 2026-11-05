"""Ten pure reviewed effects, stopping before the byte-store peripheral boundary."""
from copy import deepcopy
from payload_consumer_tail.consumer_model import payload_consumer, SITES as CONSUMER_SITES
from .source_inventory import SITES
from .state import Boundary, Effects, frozen
from .stbuf_obligations import stbuf_boundary_obligations, unknown_query


def body(effects):
    slot = 0x84 + 8 * effects.r['scb']
    effects.store(0x2980, slot, [0x56, 3], 'PointingRegisterWrite', 'Literal')
    effects.step(0x2980, 0x2983)
    effects.pointer_dependency(0x2983)
    effects.bit(0x2983, 0x356, 6, 1, 0x2985)
    effects.store(0x2985, slot, [0xF5, 3], 'PointingRegisterWrite', 'Literal')
    effects.step(0x2985, 0x2988)
    if effects.input['assumptions']['ordinaryByteSemantics'] is not True:
        effects.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', 0x2988)
    effects.set_a_byte('al', {2})
    effects.r.update(dd=0, zf=0)
    effects.step(0x2988, 0x298A)
    effects.pointer_dependency(0x298A)
    effects.store(0x298A, 0x3F5, [effects.r['al']], source='AL', partial=effects.a_partial(0x3F5, ('al',)))
    effects.step(0x298A, 0x298B)
    effects.store(0x298B, slot, [0xF1, 3], 'PointingRegisterWrite', 'Literal')
    effects.step(0x298B, 0x298E)
    effects.load_byte(0x298E, 0x3F1, 0x298F, pointer=True)
    values = {value & 31 for value in effects.a_values('al')}
    effects.set_a_byte('al', values)
    effects.r['zf'] = frozen.unique({int(value == 0) for value in values})
    effects.step(0x298F, 0x2991)
    effects.store(0x2991, slot, [0xF6, 3], 'PointingRegisterWrite', 'Literal')
    effects.step(0x2991, 0x2994)
    effects.pointer_dependency(0x2994)
    effects.store(0x2994, 0x3F6, [effects.r['al']], source='AL', partial=effects.a_partial(0x3F6, ('al',)))
    effects.step(0x2994, 0x2995)
    result = effects.finish('ContinuationPreparedBeforeStbuf', 0x2995)
    result['stbufObligations'] = stbuf_boundary_obligations(unknown_query(effects))
    return result


def run(effects):
    try:
        effects.admit(0x2980)
        if effects.r['scb'] is None:
            effects.halt('OutsideVerifiedScope', 'PointerBankNotEstablished', 0x2980)
        return body(effects)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)


def post_consumer_continuation(snapshot):
    return run(Effects(snapshot, 'post_consumer_continuation', SITES))


def consumer_with_continuation(snapshot):
    prefix = payload_consumer(snapshot)
    if prefix['status'] != 'CompleteConditional' or prefix['boundary'] != 0x2980:
        return {**prefix, 'stbufObligations': None}
    transferred = {**deepcopy(prefix['state']), 'inputClass': snapshot['inputClass'],
                   'assumptions': deepcopy(snapshot['assumptions'])}
    effects = Effects(transferred, 'consumer_with_continuation', set(SITES) | CONSUMER_SITES)
    effects.journal = deepcopy(prefix['journal'])
    effects.reads = deepcopy(prefix['reads'])
    effects.steps = deepcopy(prefix['steps'])
    effects.intermediate = deepcopy(prefix['intermediateStates'])
    if any(g is not None and g.startswith('ConditionalEffect:consumer_with_continuation:')
           for g in snapshot['generations'].values()):
        return effects.result('OutsideVerifiedScope', 'EffectNamespaceAlreadyPresent', 0x2980)
    return run(effects)
