"""Length byte copy and shared modular accumulator/counter join."""
from .state import accumulate_increment, reconstruct


def transform(effects):
    effects.load_byte(0x27F, 0x55, 0x281)
    effects.store(0x281, 0x3F2, [effects.r['al']], source='AL')
    effects.step(0x281, 0x282)
    effects.step(0x282, 0x26D, 'Jump', True)
    accumulate_increment(effects)
    return effects.finish('LengthWritten', 0x272)


def length_body(snapshot):
    return reconstruct(snapshot, 'length_body', 0x27F, transform)
