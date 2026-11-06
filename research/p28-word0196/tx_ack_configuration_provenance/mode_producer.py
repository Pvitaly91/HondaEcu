"""Two conditional source entries for DATA0356.1; no claimed native producer owner."""
from .state import Effects, Boundary, frozen

PRODUCER_SITES = (0x60C9, 0x60CC, 0x60CF, 0x60D2, 0x60D5)


def mode_bit1_producer(snapshot):
    effects = Effects(snapshot, 'mode_bit1_producer', PRODUCER_SITES, producer=True)
    try:
        compare = snapshot['entry'] == 'Compare3cb'
        effects.admit(0x60C9 if compare else 0x60D2)
        if compare:
            effects.dp(0x60C9, 0x3CB, 0x60CC)
            effects.pointer_dependency(0x60CC)
            effects.read(0x60CC, 0x3CB)
            values = frozen.candidates(effects.state['memory']['03CB'], effects.state['knownBits'], '03CB')
            effects.compare_values(0x60CC, values, 0x80, 0x60CF)
            before = effects.pswh_byte()
            known = {f'0005.{bit}': effects.r[key] for key, bit in (
                ('mie', 0), ('dd', 4), ('hc', 5), ('zf', 6), ('cf', 7)) if effects.r[key] is not None}
            effects.reads.append({'pc': 0x60CF, 'space': 'REGISTER', 'address': 5, 'widthBits': 8,
                'value': before, 'bytes': [before], 'knownBits': known,
                'generations': [None], 'accessRole': 'RegisterOperand'})
            effects.r.update(cf=None if effects.r['cf'] is None else 1 - effects.r['cf'], zf=None)
            effects.specific.append('PswhSelfDestinationZfPrecedenceNotEstablished')
            effects._event(0x60CF, 5, [before], [effects.pswh_byte()], 'RegisterXor', 'PSWH^80', 'REGISTER', [None])
            effects.step(0x60CF, 0x60D2)
        effects.dp(0x60D2, 0x356, 0x60D5)
        effects.pointer_dependency(0x60D5)
        effects.read(0x60D5, 0x356)
        raw = effects.state['memory']['0356']
        values = frozen.candidates(raw, effects.state['knownBits'], '0356')
        carry = effects.r['cf']
        carries = (0, 1) if carry is None else (carry,)
        new_values = {v & 0xFD | c << 1 for v in values for c in carries}
        after = None if raw is None or carry is None else raw & 0xFD | carry << 1
        partial = frozen.bit_consensus(new_values, '0356') if after is None else {}
        effects.store(0x60D5, 0x356, [after], 'RMW', 'CarryBitMove:1', partial=partial)
        effects.step(0x60D5, 0x60D7)
        return effects.finish('ConditionalModeBit1Written', 0x60D7)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)
