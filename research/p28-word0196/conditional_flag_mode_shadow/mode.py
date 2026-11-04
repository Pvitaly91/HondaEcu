"""Structured non-atomic mask switching and source-level consistency checks."""
from .state import reconstruct, validate


def initial_pair(snapshot):
    def body(e):
        # MOV obj,#word is DD-independent; the next L explicitly selects DD1.
        e.literal_word(0x54DD, 0xFA, 0x02A0, 0x54E2)
        e.load_word(0x54E2, 0x54E5, literal=0x2BAB)
        e.store_a(0x54E5, 0xF8, 0x54E7)
        e.store(0x54E7, 0x46, [0], 'Clear', 'Literal')
        e.step(0x54E7, 0x54EA)
        e.literal_word(0x54EA, 0x18, 0, 0x54ED, kind='Clear')
        e.bit(0x54ED, 0x40, 2, 0, 0x54F0)
        e.store_a(0x54F0, 0x1A, 0x54F2)
        return e.finish('InitialPair', 0x54F2)
    return reconstruct(snapshot, 'initial_pair', 0x54DD, body, mode=True)


def _pair_a(e):
    e.load_word(0x3F11, 0x3F14, literal=0x2BAB)
    e.store_a(0x3F14, 0x1A, 0x3F16)
    e.store_a(0x3F16, 0xF8, 0x3F18)
    e.literal_word(0x3F18, 0xFA, 0x02A0, 0x3F1D)
    e.bit(0x3F1D, 0x217, 2, 0, 0x3F20)
    e.step(0x3F20, 0x3F40, 'Jump', True)


def _pair_b(e):
    e.load_word(0x3F25, 0x3F28, literal=0xA9A3)
    e.store_a(0x3F28, 0x1A, 0x3F2A)
    e.store_a(0x3F2A, 0xF8, 0x3F2C)
    e.literal_word(0x3F2C, 0xFA, 0x00A0, 0x3F31)
    e.bit(0x3F31, 0x217, 2, 1, 0x3F34)
    e.require_usp(0x3F34)
    e.bit(0x3F34, 0x125, 7, 0, 0x3F37)
    e.bit(0x3F37, 0x21D, 7, 0, 0x3F3A)
    e.bit(0x3F3A, 0x43, 3, 1, 0x3F3D)
    e.bit(0x3F3D, 0x43, 2, 1, 0x3F40)


def mode_switch(snapshot):
    def body(e):
        e.load_word(0x3EEA, 0x3EEC, address=0xFA)
        e.store_a(0x3EEC, 0x1A, 0x3EEE)
        e.mask_pswh(0x3EEE, 0, 0x3EF1)
        request_b = e.read_bit(0x3EF1, 0x212, 3)
        direct_b = e.branch(0x3EF1, None if request_b is None else request_b == 1, 0x3F22, 0x3EF4)
        if not direct_b:
            old_mode = e.read_bit(0x3EF4, 0x217, 2)
            already_b = e.branch(0x3EF4, None if old_mode is None else old_mode == 1, 0x3F02, 0x3EF7)
            if not already_b:
                e.bit(0x3EF7, 0x19, 7, 0, 0x3EFA)
                skip_aux = e.branch(0x3EFA, None if e.r['zf'] is None else e.r['zf'] == 1, 0x3F02, 0x3EFC)
                if not skip_aux:
                    e.bit(0x3EFC, 0xB6, 7, 1, 0x3EFF)
                    e.bit(0x3EFF, 0xB4, 0, 1, 0x3F02)
            e.mask_pswh(0x3F02, 1, 0x3F05)
            e.require_usp(0x3F05)
            threshold = e.read(0x3F05, 0x1AD)[0]
            e.compare_byte(0x3F05, threshold, 0x29, 0x3F09)
            e.mask_pswh(0x3F09, 0, 0x3F0C)
            direct_b = e.branch(0x3F0C, None if e.r['cf'] is None else e.r['cf'] == 1, 0x3F22, 0x3F0E)
        if direct_b:
            mode_bit = e.read_bit(0x3F22, 0x217, 2)
            no_switch = e.branch(0x3F22, None if mode_bit is None else mode_bit == 1, 0x3F40, 0x3F25)
            if not no_switch:
                _pair_b(e)
            outcome = 'NoSwitch' if no_switch else 'PairB'
        else:
            mode_bit = e.read_bit(0x3F0E, 0x217, 2)
            no_switch = e.branch(0x3F0E, None if mode_bit is None else mode_bit == 0, 0x3F40, 0x3F11)
            if not no_switch:
                _pair_a(e)
            outcome = 'NoSwitch' if no_switch else 'PairA'
        e.mask_pswh(0x3F40, 1, 0x3F43)
        e.load_word(0x3F43, 0x3F45, address=0xF8)
        e.store_a(0x3F45, 0x1A, 0x3F47)
        return e.finish(outcome, 0x3F47)
    return reconstruct(snapshot, 'mode_switch', 0x3EEA, body, mode=True)


def consistency_check(snapshot):
    def body(e):
        e.load_word(0x3E81, 0x3E84, literal=0x2BAB)
        e.literal_word(0x3E84, 0x80, 0x02A0, 0x3E87, kind='PointerStore')
        mode_bit = e.read_bit(0x3E87, 0x217, 2)
        pair_a = e.branch(0x3E87, None if mode_bit is None else mode_bit == 0, 0x3E90, 0x3E8A)
        if not pair_a:
            e.load_word(0x3E8A, 0x3E8D, literal=0xA9A3)
            e.literal_word(0x3E8D, 0x80, 0x00A0, 0x3E90, kind='PointerStore')
        e.compare_word(0x3E90, 0xF8, 0x3E93)
        failed = e.branch(0x3E93, None if e.r['zf'] is None else e.r['zf'] == 0, 0x3EA0, 0x3E95)
        if not failed:
            e.compare_word(0x3E95, 0x1A, 0x3E98)
            failed = e.branch(0x3E98, None if e.r['zf'] is None else e.r['zf'] == 0, 0x3EA0, 0x3E9A)
        if not failed:
            e.load_word(0x3E9A, 0x3E9B, address=0x80)
            e.compare_word(0x3E9B, 0xFA, 0x3E9E)
            consistent = e.branch(0x3E9E, None if e.r['zf'] is None else e.r['zf'] == 1, 0x3EA7, 0x3EA0)
            if consistent:
                return e.finish('Consistent', 0x3EA7)
        e.store(0x3EA0, 0xF5, [0x4F], 'ImmediateStore', 'Literal')
        e.step(0x3EA0, 0x3EA4)
        e.step(0x3EA4, 0x24E0, 'Jump', True)
        return e.finish('Inconsistent', 0x24E0)
    return reconstruct(snapshot, 'consistency_check', 0x3E81, body, mode=True)


def mask_hypotheses(snapshot):
    validate(snapshot)
    memory, mie = snapshot['memory'], snapshot['registers']['mie']
    rows = []
    for name, invert in (('Set1', False), ('Set0', True)):
        values = [None if memory[key] is None else (memory[key] >> 1 & 1) ^ int(invert)
                  for key in ('001A', '00FA', '00F8')]
        gate = 0 if 0 in (values[0], mie) else 1 if values[0] == mie == 1 else None
        rows.append({'hypothesis': name, 'ieRx': values[0], 'faRx': values[1], 'f8Rx': values[2],
                     'mie': mie, 'maskGateCondition': gate, 'actualIrqDelivery': None})
    return {'inputClass': snapshot['inputClass'], 'hypotheses': rows, 'actualHardwareObservation': None,
            'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False}
