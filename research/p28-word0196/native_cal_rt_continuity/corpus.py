"""Sixteen technical call-site entries; old stack bytes are never ready frames."""
from collections import Counter
from copy import deepcopy
from native_below_second_p2 import corpus as previous

MODE = 'OriginalRomBytes_TechnicalCalRtFrameContinuity'
PUBLIC_MODE = 'PublicSyntheticCalRtFrameContinuityRegression'
PROVENANCE, CONTROL_PROVENANCE = previous.PROVENANCE, previous.CONTROL_PROVENANCE
UNKNOWN_SF, PUBLIC_DATA = deepcopy(previous.UNKNOWN_SF), dict(previous.PUBLIC_DATA)
ENTRY_PC, BODY_BASE, RETURN_PC = 0x063B, 0x54F5, 0x063E
PUBLIC_CALLER, PUBLIC_BASE, PUBLIC_RETURN = 0x2000, 0x6400, 0x2003
PUBLIC_PC_DELTA = PUBLIC_BASE - BODY_BASE
STACK_SLOTS = (0x0702, 0x0720, 0x07FC, 0x07FE)
INVENTORY = previous.INVENTORY
BUDGETS, TERMINALS = {'A': 41}, {'A': RETURN_PC}
CANARY_PROVENANCE = 'TechnicalPreCallCanary_NotCallFrame'
DATA0196_OWNER = 'TechnicalSeed_NoNativeProducerInThisSession'


def scalar_case(case):
    """Original inputs only, for unchanged historical mathematical validation."""
    result = deepcopy(case)
    result.pop('stack_canary', None)
    result['mode'], result['budget'] = previous.MODE, 39
    result['entry']['pc'] = BODY_BASE
    for address in (case['entry']['ssp'], case['entry']['ssp'] + 1):
        result['data'].pop(str(address), None)
    return result


def body_case(case):
    """Independent post-CAL reference projection, never an actual-state import."""
    validate_case(case)
    result = scalar_case(case)
    result['entry']['ssp'] -= 2
    result['internal_sf'] = False
    return result


def validate_case(case):
    if type(case) is not dict or case.get('mode') != MODE or case.get('budget') != 41 or case.get('path') != 'A':
        raise ValueError('ClosedCalRt41TechnicalCaseRequired')
    entry, canary = case.get('entry', {}), case.get('stack_canary', {})
    ssp = entry.get('ssp')
    if type(ssp) is not int or ssp not in STACK_SLOTS or entry.get('pc') != ENTRY_PC:
        raise ValueError('EvenInventoriedNonWrappingPreCallSspRequired')
    if (type(canary) is not dict or set(canary) != {'address','width','value','provenance'}
            or canary['address'] != ssp or canary['width'] != 16 or type(canary['value']) is not int
            or not 0 <= canary['value'] <= 65535 or canary['provenance'] != CANARY_PROVENANCE):
        raise ValueError('ExplicitOldStackCanaryWithoutFrameAuthorityRequired')
    if (type(case.get('data')) is not dict or set(case['data']) != {str(a) for a in (*INVENTORY, ssp, ssp + 1)}
            or case['data'][str(ssp)] != canary['value'] & 255
            or case['data'][str(ssp + 1)] != canary['value'] >> 8):
        raise ValueError('TwoExactPreCallCanaryByteSeedsRequired')
    previous.validate_case(scalar_case(case))
    return True


def iter_cases():
    words = (0x0000, 0xFFFF, 0xA55A, RETURN_PC, 0x1357, 0x2468, RETURN_PC, 0x5AA5)
    for index, source in enumerate(previous.iter_cases()):
        case = deepcopy(source)
        group = index // 2
        ssp, value = STACK_SLOTS[group % 4], words[group]
        case.update(case_id=f'm2by-a-{group:02d}-sf{int(case["internal_sf"])}',
                    family='technical-cal-rt-even-ssp-fresh-frame', mode=MODE, budget=41)
        case['entry'].update(pc=ENTRY_PC, ssp=ssp)
        case['stack_canary'] = {'address': ssp, 'width': 16, 'value': value, 'provenance': CANARY_PROVENANCE}
        case['data'].update({str(ssp): value & 255, str(ssp + 1): value >> 8})
        validate_case(case)
        yield case


def wire_case(case, program_kind='private'):
    validate_case(case)
    if program_kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2byProgramKindRequired')
    result = previous.wire_case(scalar_case(case), program_kind)
    result['budget'], result['entry']['pc'] = 41, PUBLIC_CALLER if program_kind == 'public_fixture' else ENTRY_PC
    ssp, value = case['entry']['ssp'], case['stack_canary']['value']
    # A prior equal word remains only a canary in either address domain.
    if program_kind == 'public_fixture' and value == RETURN_PC:
        value = PUBLIC_RETURN
    result['data'].update({str(ssp): value & 255, str(ssp + 1): value >> 8})
    return result


def coverage(cases=None):
    cases = list(iter_cases()) if cases is None else list(cases)
    for case in cases:
        validate_case(case)
    return {'cases': len(cases), 'paths': dict(Counter(c['path'] for c in cases)),
        'retirements': sum(c['budget'] for c in cases), 'ssps': sorted({c['entry']['ssp'] for c in cases}),
        'preexistingEqualReturnCanaries': sum(c['stack_canary']['value'] == RETURN_PC for c in cases),
        'hostSfVariants': sorted({c['internal_sf'] for c in cases}), 'physicalSfKnown': False,
        'initialDATA0196Owner': DATA0196_OWNER, 'strictNativeCallerSchedulerEstablished': False}
