"""Six reviewed source effects; reaching the read from026C is not established."""
from .state import Boundary, Effects, unique

SITES = frozenset((0x28D8, 0x28DB, 0x28DC, 0x28DE, 0x297C, 0x297F))


def payload_consumer(snapshot):
    effects = Effects(snapshot, 'payload_consumer', SITES)
    effects.specific = ['Specific026CGenerationReachingConsumerNotEstablished', 'Downstream2980OutsideVerifiedScope']
    try:
        effects.admit(0x28D8)
        if effects.r['scb'] is None:
            effects.halt('OutsideVerifiedScope', 'PointerBankNotEstablished', 0x28D8)
        slot = 0x84 + 8 * effects.r['scb']
        effects.store(0x28D8, slot, [0xF4, 3], 'PointingRegisterWrite', 'Literal')
        effects.step(0x28D8, 0x28DB)
        effects.load_byte(0x28DB, 0x3F4, 0x28DC, pointer=True)
        values = effects.a_values('al')
        effects.set_a_byte('al', {(value + 3) & 255 for value in values})
        effects.r.update(cf=unique({int(value + 3 > 255) for value in values}),
                         zf=unique({int((value + 3) & 255 == 0) for value in values}),
                         hc=unique({int((value & 15) + 3 > 15) for value in values}))
        effects.step(0x28DC, 0x28DE)
        effects.step(0x28DE, 0x297C, 'Jump', True)
        effects.store(0x297C, slot, [0xF2, 3], 'PointingRegisterWrite', 'Literal')
        effects.step(0x297C, 0x297F)
        effects.pointer_dependency(0x297F)
        effects.store(0x297F, 0x3F2, [effects.r['al']], source='AL',
                      partial=effects.a_partial(0x3F2, ('al',)))
        effects.step(0x297F, 0x2980)
        return effects.finish('PayloadReadAddThreeStored', 0x2980)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)
