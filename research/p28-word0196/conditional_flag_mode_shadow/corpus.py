"""Invented explicit inputs, shared without model or expected-value imports."""
from copy import deepcopy

ADDRESSES = ('0018', '0019', '001A', '001B', '0040', '0043', '0046', '0055',
             '0080', '0081', '00B4', '00B6', '00F5', '00F8', '00F9', '00FA',
             '00FB', '0125', '01AD', '0212', '0217', '021D', '0356', '03F0',
             '03F1', '03F2', '03F3', '03F4', '03F5', '03F6', '03F7')


def fixture(kind='flag'):
    if kind not in ('flag', 'mode'):
        raise ValueError('InventedFixtureKindRequired')
    memory = {key: (int(key, 16) * 13 + 7) % 256 for key in ADDRESSES}
    memory.update({'0018': 0x21, '0019': 0x01, '001A': 0xAB, '001B': 0x2B,
                   '0040': 0xA4, '0043': 0x50, '0046': 0x92, '0055': 0x5A,
                   '0080': 0x12, '0081': 0x34, '00B4': 0x10, '00B6': 0x00,
                   '00F5': 0x00, '00F8': 0xAB, '00F9': 0x2B,
                   '00FA': 0xA0, '00FB': 0x02, '0125': 0x80, '01AD': 0x29,
                   '0212': 0xA0, '0217': 0xA0, '021D': 0x80, '0356': 0x02,
                   '03F0': 0x11, '03F1': 0x22, '03F2': 4, '03F3': 0x33,
                   '03F4': 0x44, '03F5': 2, '03F6': 0, '03F7': 2})
    return {'inputClass': 'SyntheticTestInput', 'memory': memory, 'knownBits': {},
            'registers': {'al': 0xA5, 'ah': 0x5A, 'cf': 1, 'zf': 1, 'hc': 1,
                          'dd': 1, 'mie': 0, 'otherPsw': 0x0AF8,
                          'lrb': 0x007E if kind == 'flag' else 0x0040,
                          'scb': 2 if kind == 'flag' else 0, 'usp': 0x0180, 'ssp': None},
            'generations': {key: 'SyntheticInput:' + kind + ':' + key for key in ADDRESSES},
            'assumptions': {'noInterference': True, 'ordinaryByteSemantics': True,
                            'dataMapping': 'ConditionalByteArray'}}


def _bit(snapshot, address, bit, value):
    raw = snapshot['memory'][address]
    snapshot['memory'][address] = (raw & ~(1 << bit)) | (value << bit)


def _word(snapshot, address, value):
    location = int(address, 16) & 0xFFFE
    snapshot['memory'][f'{location:04X}'] = None if value is None else value % 256
    snapshot['memory'][f'{location + 1:04X}'] = None if value is None else value // 256


def cases():
    """Closed deterministic corpus; no case is an actual hardware observation."""
    for flag in range(256):
        for prior in (0, 1, 15, 127, 128, 255):
            state = fixture('flag')
            state['memory']['0055'] = flag
            state['memory']['03F6'] = prior
            yield {'id': f'flag-f{flag:02X}-r6{prior:02X}', 'operation': 'flag_path', 'input': state}

    for value in (0, 1, 3, 255, None):
        state = fixture('flag')
        state['memory']['03F5'] = value
        yield {'id': 'body-r5-' + str(value), 'operation': 'flag_body', 'input': state}

    for field in ('0055', '03F6'):
        state = fixture('flag')
        state['inputClass'] = 'SymbolicInput'
        state['memory'][field] = None
        yield {'id': 'flag-unknown-' + field, 'operation': 'flag_path', 'input': state}
    for register in ('ah', 'otherPsw'):
        state = fixture('flag')
        state['inputClass'] = 'SymbolicInput'
        state['registers'][register] = None
        yield {'id': 'flag-unknown-' + register, 'operation': 'flag_path', 'input': state}
    state = fixture('flag')
    state['memory']['0356'] = None
    state['knownBits'] = {'0356.1': 1, '0356.6': 0, '0356.7': 1}
    yield {'id': 'flag-partial-status-known-control', 'operation': 'flag_path', 'input': state}
    state = fixture('flag')
    state['memory']['0356'] = None
    state['knownBits'] = {'0356.1': 1}
    yield {'id': 'flag-unknown-old-error', 'operation': 'flag_path', 'input': state}
    state = fixture('flag')
    state['memory']['0356'] = None
    yield {'id': 'flag-unknown-mode', 'operation': 'flag_path', 'input': state}
    for lrb in (0x0040, None):
        state = fixture('flag')
        state['registers']['lrb'] = lrb
        yield {'id': 'flag-unsupported-bank-' + str(lrb), 'operation': 'flag_path', 'input': state}
    for assumption in ('ordinaryByteSemantics', 'noInterference'):
        for value in (False, None):
            state = fixture('flag')
            state['assumptions'][assumption] = value
            yield {'id': 'flag-premise-' + assumption + '-' + str(value), 'operation': 'flag_path', 'input': state}
    for address, value, name in (('03F7', 0, 'header'), ('03F5', 1, 'length'),
                                 ('03F5', 3, 'checksum'), ('03F7', None, 'unknown-r7'),
                                 ('03F5', None, 'unknown-r5'), ('03F5', 255, 'prefix-overflow')):
        state = fixture('flag')
        state['memory'][address] = value
        yield {'id': 'flag-dispatch-' + name, 'operation': 'flag_path', 'input': state}
    state = fixture('flag')
    state['memory']['0356'] = 0x82
    state['memory']['03F3'] = state['memory']['0055']
    yield {'id': 'flag-ready-retained-and-same-store', 'operation': 'flag_path', 'input': state}
    state = fixture('flag')
    state['inputClass'] = 'ManufacturerSourceQualifiedState'
    yield {'id': 'flag-source-qualified-assumption', 'operation': 'flag_path', 'input': state}

    for status in (0, 0x40, 0x80, 0xC0, None):
        state = fixture('flag')
        state['memory']['0356'] = status
        yield {'id': 'status-clear-' + str(status), 'operation': 'status_clear', 'input': state}

    for gate in (0, 1):
        for mode in (0, 1):
            for threshold in (0, 0x28, 0x29, 0x2A, 0xFF):
                for irq_high in (0, 1):
                    state = fixture('mode')
                    _bit(state, '0212', 3, gate)
                    _bit(state, '0217', 2, mode)
                    _bit(state, '0019', 7, irq_high)
                    state['memory']['01AD'] = threshold
                    yield {'id': f'mode-g{gate}-m{mode}-t{threshold:02X}-q{irq_high}',
                           'operation': 'mode_switch', 'input': state}

    for gate, mode, usp in ((1, 1, None), (1, 0, None), (0, 1, None), (0, 0, 0x0100)):
        state = fixture('mode')
        _bit(state, '0212', 3, gate)
        _bit(state, '0217', 2, mode)
        state['registers']['usp'] = usp
        yield {'id': f'mode-conditional-usp-{gate}-{mode}-{usp}', 'operation': 'mode_switch', 'input': state}
    for address in ('0212', '0217', '0019', '01AD'):
        state = fixture('mode')
        state['memory'][address] = None
        yield {'id': 'mode-unknown-' + address, 'operation': 'mode_switch', 'input': state}
    state = fixture('mode')
    _bit(state, '0212', 3, 1)
    state['memory']['01AD'] = None
    yield {'id': 'mode-threshold-read-suppressed', 'operation': 'mode_switch', 'input': state}
    for mode in (0, 1):
        state = fixture('mode')
        state['memory']['0212'] = None
        state['memory']['0217'] = None
        state['knownBits'] = {'0212.3': 0 if mode else 1, '0217.2': mode}
        yield {'id': 'mode-partial-control-' + str(mode), 'operation': 'mode_switch', 'input': state}
    for low, high, name in ((0xAB, None, 'partial-nonzero'), (0, None, 'partial-zero'),
                             (None, None, 'unknown'), (0, 0, 'zero')):
        state = fixture('mode')
        state['memory']['00F8'] = low
        state['memory']['00F9'] = high
        yield {'id': 'mode-f8-' + name, 'operation': 'mode_switch', 'input': state}
    state = fixture('mode')
    _word(state, '00FA', None)
    yield {'id': 'mode-unknown-prelude-fa', 'operation': 'mode_switch', 'input': state}
    for key, value in (('lrb', 0x007E), ('lrb', None), ('scb', 6), ('scb', None)):
        state = fixture('mode')
        state['registers'][key] = value
        yield {'id': 'mode-unsupported-' + key + '-' + str(value), 'operation': 'mode_switch', 'input': state}
    state = fixture('mode')
    state['generations'] = {key: None for key in ADDRESSES}
    yield {'id': 'mode-generation-unknown', 'operation': 'mode_switch', 'input': state}
    state = fixture('mode')
    _word(state, '00F8', 0x1234)
    yield {'id': 'mode-no-switch-does-not-repair-mismatched-shadow', 'operation': 'mode_switch', 'input': state}

    for dd in (0, 1, None):
        for mode in (0, 1):
            state = fixture('mode')
            state['registers']['dd'] = dd
            _bit(state, '0217', 2, mode)
            yield {'id': f'initial-dd{dd}-mode{mode}', 'operation': 'initial_pair', 'input': state}
    for bit in (0, 1, None):
        state = fixture('mode')
        state['memory']['0040'] = None
        if bit is not None:
            state['knownBits']['0040.2'] = bit
        yield {'id': 'initial-partial-tcon-' + str(bit), 'operation': 'initial_pair', 'input': state}

    for mode in (0, 1):
        base = fixture('mode')
        _bit(base, '0217', 2, mode)
        _word(base, '001A', 0x2BAB if mode == 0 else 0xA9A3)
        _word(base, '00F8', 0x2BAB if mode == 0 else 0xA9A3)
        _word(base, '00FA', 0x02A0 if mode == 0 else 0x00A0)
        yield {'id': 'check-consistent-' + str(mode), 'operation': 'consistency_check', 'input': deepcopy(base)}
        for address in ('00F8', '001A', '00FA'):
            for variant in ('mismatch', 'unknown', 'partial'):
                state = deepcopy(base)
                if variant == 'mismatch':
                    state['memory'][address] ^= 1
                elif variant == 'unknown':
                    _word(state, address, None)
                else:
                    state['memory'][f'{int(address, 16) + 1:04X}'] = None
                yield {'id': f'check-{mode}-{address}-{variant}', 'operation': 'consistency_check', 'input': state}
        state = deepcopy(base)
        state['generations'] = {key: None for key in ADDRESSES}
        yield {'id': 'check-missing-generations-' + str(mode), 'operation': 'consistency_check', 'input': state}
    state = fixture('mode')
    state['memory']['0217'] = None
    yield {'id': 'check-unknown-mode', 'operation': 'consistency_check', 'input': state}
    state = fixture('mode')
    state['memory']['0217'] = None
    state['knownBits']['0217.2'] = 1
    _word(state, '001A', 0xA9A3)
    _word(state, '00F8', 0xA9A3)
    _word(state, '00FA', 0x00A0)
    yield {'id': 'check-partial-mode-known-bit', 'operation': 'consistency_check', 'input': state}

    for ie in (0, 1, None):
        for fa in (0, 1, None):
            for f8 in (0, 1, None):
                for mie in (0, 1, None):
                    state = fixture('mode')
                    for address, value in (('001A', ie), ('00FA', fa), ('00F8', f8)):
                        _word(state, address, None if value is None else value * 2)
                    state['registers']['mie'] = mie
                    yield {'id': f'polarity-ie{ie}-fa{fa}-f8{f8}-mie{mie}',
                           'operation': 'mask_hypotheses', 'input': state}
    state = fixture('mode')
    state['memory']['001B'] = None
    state['memory']['00FB'] = None
    state['memory']['00F9'] = None
    state['registers']['lrb'] = None
    state['registers']['scb'] = None
    state['assumptions']['noInterference'] = None
    yield {'id': 'polarity-partial-high-bytes-no-context-premise', 'operation': 'mask_hypotheses', 'input': state}
