"""Structured conditional Flag algorithm over explicit source-qualified inputs."""
from .state import reconstruct


def _body(e):
    e.load_byte(0x262, 0x55, 0x264)
    r5 = e.read(0x264, 0x3F5)[0]
    e.compare_byte(0x264, r5, 2, 0x267)
    if e.branch(0x267, None if e.r['zf'] is None else e.r['zf'] == 0, 0x26C, 0x269):
        e.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x26C)
    e.store(0x269, 0x3F3, [e.r['al']], source='AL')
    e.step(0x269, 0x26A)
    e.step(0x26A, 0x26D, 'Jump', True)
    previous, value = e.read(0x26D, 0x3F6)[0], e.r['al']
    if previous is None or value is None:
        result = carry = zero = half = None
    else:
        result = (previous + value) & 255
        carry = int(previous + value > 255)
        zero = int(result == 0)
        half = int((previous & 15) + (value & 15) > 15)
    e.r.update(cf=carry, zf=zero, hc=half)
    e.store(0x26D, 0x3F6, [result], 'RMW', 'DATA03F6+AL')
    e.step(0x26D, 0x26F)
    previous = e.read(0x26F, 0x3F5)[0]
    # The selected CMP/JNE branch fixes r5=2. The following increment owns ZF/HC.
    e.r.update(zf=0, hc=0)
    e.store(0x26F, 0x3F5, [previous + 1], 'RMW', 'DATA03F5+1')
    e.step(0x26F, 0x270)
    e.store(0x270, 0x3F7, [2], 'ImmediateStore', 'Literal')
    e.step(0x270, 0x272)
    return e.finish('FlagWritten', 0x272)


def status_clear(snapshot):
    def body(e):
        e.bit(0x222, 0x356, 6, 0, 0x225)
        return e.finish('StatusCleared', 0x225)
    return reconstruct(snapshot, 'status_clear', 0x222, body)


def flag_body(snapshot):
    return reconstruct(snapshot, 'flag_body', 0x262, _body)


def flag_path(snapshot):
    def body(e):
        bit = e.read_bit(0x21F, 0x356, 1)
        if e.branch(0x21F, None if bit is None else bit == 0, 0x29D, 0x222):
            e.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x29D)
        e.bit(0x222, 0x356, 6, 0, 0x225)
        if not e.branch(0x225, None if e.r['zf'] is None else e.r['zf'] == 1, 0x255, 0x227):
            e.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x227)
        e.load_byte(0x255, 0x3F7, 0x256)
        if e.branch(0x256, None if e.r['zf'] is None else e.r['zf'] == 1, 0x275, 0x258):
            e.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x275)
        e.load_byte(0x258, 0x3F5, 0x259)
        e.compare_byte(0x259, e.r['al'], 1, 0x25B)
        if e.branch(0x25B, None if e.r['zf'] is None else e.r['zf'] == 1, 0x27F, 0x25D):
            e.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x27F)
        previous = e.r['al']
        if previous is None:
            e.r.update(al=None, cf=None, zf=None, hc=None)
        else:
            value = (previous + 1) & 255
            e.r.update(al=value, cf=int(previous == 255), zf=int(value == 0), hc=int(previous & 15 == 15))
        e.step(0x25D, 0x25F)
        r2 = e.read(0x25F, 0x3F2)[0]
        e.compare_byte(0x25F, e.r['al'], r2, 0x260)
        if e.branch(0x260, None if e.r['zf'] is None else e.r['zf'] == 1, 0x284, 0x262):
            e.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x284)
        return _body(e)
    return reconstruct(snapshot, 'flag_path', 0x21F, body)
