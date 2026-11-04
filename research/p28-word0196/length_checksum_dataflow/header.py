"""Header-derived source transformation including the old-r1 write prefix."""
from .state import reconstruct, write_r7


def transform(effects):
    old = effects.read(0x275, 0x3F1)[0]
    effects.store(0x275, 0x3F0, [old], source='DATA03F1')
    effects.step(0x275, 0x277)
    effects.load_byte(0x277, 0x55, 0x279)
    effects.store(0x279, 0x3F1, [effects.r['al']], source='AL')
    effects.step(0x279, 0x27A)
    effects.store(0x27A, 0x3F6, [effects.r['al']], source='AL')
    effects.step(0x27A, 0x27B)
    effects.store(0x27B, 0x3F5, [1], 'ImmediateStore', 'Literal')
    effects.step(0x27B, 0x27D)
    effects.step(0x27D, 0x270, 'Jump', True)
    write_r7(effects)
    return effects.finish('HeaderWritten', 0x272)


def header_body(snapshot):
    return reconstruct(snapshot, 'header_body', 0x275, transform)
