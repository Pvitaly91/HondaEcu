"""Thirty-two invented technical snapshots; never native startup evidence."""
from collections import Counter
from copy import deepcopy

from native_p2_handoff import corpus as previous

MODE = 'OriginalRomBytes_TechnicalPostP2ControlExecution'
PUBLIC_MODE = 'PublicSyntheticPostP2ControlRegression'
PROVENANCE = previous.PROVENANCE
CONTROL_PROVENANCE = 'TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration'
ENTRY_PC = 0x54F5
PUBLIC_BASE = 0x6400
PUBLIC_PC_DELTA = PUBLIC_BASE - ENTRY_PC
BUDGETS = {'A': 21, 'B': 20, 'C': 21, 'D': 23}
TERMINALS = {'A': 0x55D2, 'B': 0x559D, 'C': 0x559D, 'D': 0x559D}
P2_PCS = previous.P2_PCS
CONTROL_PCS = {'A': 0x55C8, 'B': 0x5599, 'C': 0x5599, 'D': 0x5599}
INVENTORY, PUBLIC_DATA = previous.INVENTORY, previous.PUBLIC_DATA
UNKNOWN_SF = deepcopy(previous.UNKNOWN_SF)


def scalar_case(case):
    result = deepcopy(case)
    result.pop('control_snapshot', None)
    result['mode'] = previous.MODE
    result['budget'] = previous.BUDGETS.get(result.get('path'))
    return result


def validate_case(case):
    fields = {'kind', 'case_id', 'family', 'mode', 'source_classification', 'native_input_claimed',
              'entry', 'data', 'path', 'internal_sf', 'budget', 'p2_snapshot', 'control_snapshot'}
    if type(case) is not dict or set(case) != fields or case['mode'] != MODE:
        raise ValueError('ClosedM2bwTechnicalCaseRequired')
    if (case['path'] not in BUDGETS or type(case['budget']) is not int
            or case['budget'] != BUDGETS[case['path']]):
        raise ValueError('ExactPostP2ControlPathAndBudgetRequired')
    previous.validate_case(scalar_case(case))
    control = case['control_snapshot']
    if (type(control) is not dict or set(control) != {'tcon0', 'trnsit_implemented_flags', 'provenance'}
            or type(control['tcon0']) is not int or control['tcon0'] not in (0x83, 0x87, 0x8B, 0x8F)
            or type(control['trnsit_implemented_flags']) is not int
            or not 0 <= control['trnsit_implemented_flags'] <= 15
            or control['provenance'] != CONTROL_PROVENANCE):
        raise ValueError('StoppedTechnicalControlSnapshotRequired')
    return True


def iter_cases():
    patterns = {'A': (0, 1, 4, 5, 8, 9, 14, 15), 'B': (0, 1, 4, 5, 8, 9, 14, 15),
                'C': (2, 3, 6, 7, 10, 11, 12, 13), 'D': (0, 3, 4, 7, 8, 11, 12, 15)}
    for index, original in enumerate(previous.iter_cases()):
        case = deepcopy(original)
        position = index % 8
        if case['path'] == 'A':
            case['data'][str(0x018E)] = (0, 0x7F, 0x80, 0xFF)[position // 2]
        case.update(case_id=case['case_id'].replace('m2bv-', 'm2bw-', 1),
            family='post-p2-control-dd-hc-sf', mode=MODE, budget=BUDGETS[case['path']],
            control_snapshot={'tcon0': (0x83, 0x87, 0x8B, 0x8F)[position // 2],
                'trnsit_implemented_flags': patterns[case['path']][position],
                'provenance': CONTROL_PROVENANCE})
        validate_case(case)
        yield case


def wire_case(case, program_kind='private'):
    validate_case(case)
    if program_kind not in ('private', 'public_fixture'):
        raise ValueError('ClosedM2bwProgramKindRequired')
    result = previous.wire_case(scalar_case(case), program_kind)
    result['budget'] = case['budget']
    result['control_snapshot'] = deepcopy(case['control_snapshot'])
    return result


def coverage(cases=None):
    cases = list(iter_cases()) if cases is None else list(cases)
    for case in cases:
        validate_case(case)
    return {'cases': len(cases), 'paths': dict(Counter(case['path'] for case in cases)),
        'retirements': sum(case['budget'] for case in cases),
        'tcon0Values': sorted({case['control_snapshot']['tcon0'] for case in cases}),
        'trnsitFlags': sorted({case['control_snapshot']['trnsit_implemented_flags'] for case in cases}),
        'initialP2Values': sorted({case['p2_snapshot']['value'] for case in cases}),
        'incomingFlagVectors': previous.coverage([scalar_case(case) for case in cases])['incomingFlagVectors'],
        'scbs': sorted({case['entry']['scb'] for case in cases}),
        'physicalSfKnown': False, 'initialNativeP2OwnerEstablished': False,
        'initialNativeControlOwnerEstablished': False}
