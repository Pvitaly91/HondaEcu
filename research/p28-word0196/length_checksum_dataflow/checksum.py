"""Verified local checksum sum/class guards, without a packet or receiver claim."""
from .state import arithmetic, reconstruct, write_r7


def transform(effects):
    effects.load_byte(0x284, 0x55, 0x286)
    operand = effects.read(0x286, 0x3F6)[0]
    effects.r.update(arithmetic(effects.r['al'], operand))
    effects.step(0x286, 0x287)
    if effects.branch(0x287, None if effects.r['zf'] is None else effects.r['zf'] == 0, 0x270, 0x289):
        write_r7(effects)
        return effects.finish('ChecksumRejected', 0x272)
    effects.load_byte(0x289, 0x3F1, 0x28A)
    value = None if effects.r['al'] is None else effects.r['al'] & 0xE0
    effects.r.update(al=value, zf=None if value is None else int(value == 0))
    effects.step(0x28A, 0x28C)
    effects.compare_byte(0x28C, value, 0x20, 0x28E)
    if effects.branch(0x28E, None if effects.r['zf'] is None else effects.r['zf'] == 0, 0x270, 0x290):
        write_r7(effects)
        return effects.finish('ChecksumRejected', 0x272)
    effects.bit(0x290, 0x356, 7, 1, 0x293)
    effects.store(0x293, 0x3F7, [0], 'ImmediateStore', 'Literal')
    effects.step(0x293, 0x295)
    return effects.finish('ChecksumAccepted', 0x295)


def checksum_body(snapshot):
    return reconstruct(snapshot, 'checksum_body', 0x284, transform)
