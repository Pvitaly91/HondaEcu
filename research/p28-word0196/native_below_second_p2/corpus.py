"""Sixteen closed technical Below entries; no ready downstream state."""
from collections import Counter
from copy import deepcopy

from native_post_p2_control import corpus as previous

MODE = 'OriginalRomBytes_TechnicalBelowSecondP2Execution'
PUBLIC_MODE = 'PublicSyntheticBelowSecondP2Regression'
PROVENANCE, CONTROL_PROVENANCE = previous.PROVENANCE, previous.CONTROL_PROVENANCE
ENTRY_PC, PUBLIC_BASE, PUBLIC_PC_DELTA = previous.ENTRY_PC, previous.PUBLIC_BASE, previous.PUBLIC_PC_DELTA
NEW_CANARIES = tuple(range(0x0110, 0x0117))
INVENTORY = tuple(sorted((*previous.INVENTORY, *NEW_CANARIES)))
PUBLIC_DATA = dict(previous.PUBLIC_DATA)
UNKNOWN_SF = deepcopy(previous.UNKNOWN_SF)
BUDGETS, TERMINALS = {'A': 39}, {'A': 0x5688}
P2_PCS, CONTROL_PCS = {'A': 0x55C5}, {'A': 0x55C8}
DOWNSTREAM = (0x55D2, 0x55D3, 0x55D5, 0x55D8, 0x55DB, 0x562C, 0x562E,
              0x5631, 0x5633, 0x565D, 0x565F, 0x5661, 0x5671, 0x5673,
              0x567E, 0x5680, 0x5682, 0x5685)


def scalar_case(case):
    """Independent expected-input projection only; never actual-state transfer."""
    value = deepcopy(case)
    value['mode'], value['budget'] = previous.MODE, previous.BUDGETS['A']
    for address in NEW_CANARIES:
        value['data'].pop(str(address), None)
    return value


def validate_case(case):
    if (type(case) is not dict or case.get('mode') != MODE or case.get('path') != 'A'
            or type(case.get('budget')) is not int or case['budget'] != 39
            or type(case.get('data')) is not dict
            or set(case['data']) != {str(address) for address in INVENTORY}
            or any(type(case['data'][str(address)]) is not int or case['data'][str(address)] != 0xA5
                   for address in NEW_CANARIES)):
        raise ValueError('ClosedBelow39WithSevenExplicitUnownedCanariesRequired')
    previous.validate_case(scalar_case(case))
    if (case['data'][str(0x0196)] | case['data'][str(0x0197)] << 8) >= 0xC0:
        raise ValueError('BelowWordOnly_NoNotBelowExtension')
    return True


def iter_cases():
    basis = next(previous.iter_cases())
    words = (0, 1, 0x3F, 0x7F, 0x80, 0xBE, 0xBF, 2)
    latches = (0, 255, 0xA5, 0x0F, 0x80, 0x55, 0xAA, 0xF0)
    initial18e = (0, 255, 0x7F, 0x80, 0x3F, 0x40, 0x7E, 0x81)
    for index in range(8):
        for sf in (False, True):
            case = deepcopy(basis)
            entry = case['entry']
            cf, hc, dd = bool(index & 1), bool(index & 2), bool(index & 4)
            zf = bool(index & 1)
            other = (entry['psw'] & 0x0330) | 0x0CC8 | index
            psw = other | int(cf) << 15 | int(zf) << 14 | int(hc) << 13 | int(dd) << 12
            entry.update(psw=psw, cf=cf, zf=zf, hc=hc, dd=dd, other_psw=psw & 0x0FFF, scb=index)
            case.update(case_id=f'm2bx-a-{index:02d}-sf{int(sf)}', family='below-two-p2-dd-cf-hc-sf',
                        mode=MODE, budget=39, internal_sf=sf)
            for address in NEW_CANARIES:
                case['data'][str(address)] = 0xA5
            case['data'][str(0x0196)] = words[index]
            case['data'][str(0x0197)] = 0
            case['data'][str(0x018E)] = initial18e[index]
            case['data'][str(0x012A)] = (case['data'][str(0x012A)] & 0x7F) | (int(index & 1 != 0) << 7)
            case['p2_snapshot']['value'] = latches[index]
            case['control_snapshot'].update(tcon0=(0x83, 0x87, 0x8B, 0x8F)[index % 4], trnsit_implemented_flags=index)
            validate_case(case)
            yield case


def wire_case(case, program_kind='private'):
    validate_case(case)
    if program_kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2bxProgramKindRequired')
    value = previous.wire_case(scalar_case(case), program_kind)
    value['budget'] = 39
    value['data'].update({str(address): 0xA5 for address in NEW_CANARIES})
    return value


def coverage(cases=None):
    cases = list(iter_cases()) if cases is None else list(cases)
    for case in cases:
        validate_case(case)
    return {'cases': len(cases), 'paths': dict(Counter(case['path'] for case in cases)),
        'retirements': sum(case['budget'] for case in cases),
        'tcon0Values': sorted({case['control_snapshot']['tcon0'] for case in cases}),
        'trnsitFlags': sorted({case['control_snapshot']['trnsit_implemented_flags'] for case in cases}),
        'initialP2Values': sorted({case['p2_snapshot']['value'] for case in cases}),
        'words': sorted({case['data'][str(0x0196)] | case['data'][str(0x0197)] << 8 for case in cases}),
        'incomingFlagVectors': sorted({tuple(int(case['entry'][name]) for name in ('cf', 'zf', 'hc', 'dd')) for case in cases}),
        'scbs': sorted({case['entry']['scb'] for case in cases}),
        'physicalSfKnown': False, 'initialNativeP2OwnerEstablished': False, 'initialNativeControlOwnerEstablished': False}
