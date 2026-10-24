"""Thirty-two independent technical states; one P2 snapshot before entry.

The frozen M2bu corpus supplies scalar predecessor/algorithm conditions only.
It does not supply a CPU observation, initial P2 owner or hardware port mode.
"""
from collections import Counter
from copy import deepcopy

from native_entry_continuity import corpus as previous

MODE = 'OriginalRomBytes_TechnicalP2HandoffExecution'
PUBLIC_MODE = 'PublicSyntheticP2HandoffRegression'
PROVENANCE = 'TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration'
ENTRY_PC = 0x54F5
PUBLIC_BASE = 0x6400
PUBLIC_PC_DELTA = PUBLIC_BASE - ENTRY_PC
BUDGETS = {'A': 17, 'B': 19, 'C': 20, 'D': 22}
TERMINALS = {'A': 0x55C8, 'B': 0x5599, 'C': 0x5599, 'D': 0x5599}
P2_PCS = {'A': 0x55C5, 'B': 0x5596, 'C': 0x5596, 'D': 0x5596}
INVENTORY = previous.INVENTORY
PUBLIC_DATA = previous.PUBLIC_DATA
UNKNOWN_SF = deepcopy(previous.UNKNOWN_SF)


def scalar_case(case):
    """Pure expected-input adapter, never an actual CPU or P2 handoff."""
    result = deepcopy(case)
    result.pop('p2_snapshot', None)
    result['mode'] = previous.MODE
    result['budget'] = previous.BUDGETS.get(result.get('path'))
    return result


def validate_case(case):
    fields = {'kind', 'case_id', 'family', 'mode', 'source_classification', 'native_input_claimed',
              'entry', 'data', 'path', 'internal_sf', 'budget', 'p2_snapshot'}
    if type(case) is not dict or set(case) != fields or case['mode'] != MODE:
        raise ValueError('ClosedM2bvTechnicalCaseRequired')
    if case['path'] not in BUDGETS or type(case['budget']) is not int or case['budget'] != BUDGETS[case['path']]:
        raise ValueError('ExactPositiveP2HandoffPathAndBudgetRequired')
    previous.validate_case(scalar_case(case))
    snapshot = case['p2_snapshot']
    if (type(snapshot) is not dict or set(snapshot) != {'value', 'p2io', 'p2sf', 'provenance'}
            or type(snapshot['value']) is not int or not 0 <= snapshot['value'] <= 255
            or type(snapshot['p2io']) is not int or snapshot['p2io'] != 255
            or type(snapshot['p2sf']) is not int or snapshot['p2sf'] != 7
            or snapshot['provenance'] != PROVENANCE):
        raise ValueError('ReviewedPrimaryOutputModeAndTechnicalP2SnapshotRequired')
    return True


def iter_cases():
    for index, original in enumerate(previous.iter_cases()):
        case = deepcopy(original)
        base_index = (index % 8) // 2
        latch = (0x00, 0xFF, 0xA5, 0x0F if case['path'] == 'A' else 0xF0)[base_index]
        case.update(case_id=case['case_id'].replace('m2bu-', 'm2bv-', 1), family='p2-dd-hc-sf',
                    mode=MODE, budget=BUDGETS[case['path']],
                    p2_snapshot={'value': latch, 'p2io': 255, 'p2sf': 7, 'provenance': PROVENANCE})
        validate_case(case)
        yield case


def wire_case(case, program_kind='private'):
    validate_case(case)
    if program_kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2bvProgramKindRequired')
    result = previous.wire_case(scalar_case(case), program_kind)
    result['budget'] = case['budget']
    result['p2_snapshot'] = deepcopy(case['p2_snapshot'])
    if program_kind == 'public_fixture':
        result['entry']['pc'] = PUBLIC_BASE
    return result


def coverage(cases=None):
    cases = list(iter_cases()) if cases is None else list(cases)
    for case in cases:
        validate_case(case)
    return {'cases': len(cases), 'paths': dict(Counter(case['path'] for case in cases)),
        'retirements': sum(case['budget'] for case in cases),
        'initialP2Values': sorted({case['p2_snapshot']['value'] for case in cases}),
        'incomingFlagVectors': previous.coverage([scalar_case(case) for case in cases])['incomingFlagVectors'],
        'scbs': sorted({case['entry']['scb'] for case in cases}),
        'words': sorted({previous.word0196(case) for case in cases}),
        'physicalSfKnown': False, 'initialNativeP2OwnerEstablished': False}
