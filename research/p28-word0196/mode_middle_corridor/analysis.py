"""Canonical research records for the corridor and its enclosing composition."""
from copy import deepcopy
import json
from pathlib import Path

from enclosing_caller_return.analysis import AUTHORITY, canonical, validate_authority

from .composition import mode_enclosing_continuation
from .middle_corridor import mode_middle_corridor
from .source_inventory import APPLICABILITY, BASE, SOURCE_IDENTITIES
from .state import need, shape

OPERATIONS = {function.__name__: function for function in (mode_middle_corridor, mode_enclosing_continuation)}
STEP_REGISTERS = ('afterRegisters', 'afterRegisterKnownBits', 'afterPointerState', 'afterX1State',
                  'afterOtherPswKnownBits')
FLAG_FIELDS = ('cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw')


def record(case):
    shape(case, ('id', 'operation', 'input'), 'ClosedCaseRequired')
    name = case['operation']
    need(type(case['id']) is str and bool(case['id']) and type(name) is str and name in OPERATIONS,
         'KnownOperationAndCaseIdentityRequired')
    result = OPERATIONS[name](deepcopy(case['input']))
    authority = {key: result[key] for key in AUTHORITY}
    validate_authority(result)
    state, steps = result['state'], result['steps']
    registers = state.get('registers')
    generations = {
        'data': state.get('generations'),
        'softwareIntents': {key: slot['generation'] for key, slot in state['configurationIntents'].items()}
        if 'configurationIntents' in state else None,
        'suppliedReadbacks': {key: slot['generation'] for key, slot in state['sfrReadbacks'].items()}
        if 'sfrReadbacks' in state else None,
        'writerEvents': [{'ordinal': row['ordinal'], 'before': row.get('beforeGeneration'),
                          'after': row.get('afterGeneration')} for row in result['journal']],
        'reachingDefinitions': state.get('reachingDefinitions'),
    }
    return deepcopy({
        'caseId': case['id'], 'operation': name, 'input': case['input'], 'output': result,
        'sourceScope': result['sourceScope'], 'sourceIdentities': SOURCE_IDENTITIES,
        'evidenceClass': result['effectClass'], 'applicability': APPLICABILITY,
        'sourceEdges': [{'from': row['pc'], 'to': row['next'],
                         'class': 'ConditionalSourcePath' if row['kind'] == 'Branch' else 'ConfirmedStaticCFG'}
                        for row in steps if row['next'] is not None],
        'branchOutcome': [{'pc': row['pc'], 'taken': row['branchTaken'], 'next': row['next']}
                          for row in steps if row['kind'] == 'Branch'],
        'registerState': registers,
        'flags': None if registers is None else {key: registers.get(key) for key in FLAG_FIELDS},
        'registerEffects': [{'pc': row['pc'], **{key: row.get(key) for key in STEP_REGISTERS}}
                            for row in steps],
        'reads': result['reads'], 'orderedWrites': result['journal'],
        'programDependencies': [row for row in result['reads'] if row['space'] == 'PROGRAM'],
        'correlatedPredicates': result.get('correlatedPredicates', []),
        'frameObligations': result.get('frameObligations', []), 'generations': generations,
        'intermediateStates': result['intermediateStates'], 'unresolvedConstraints': result['unresolvedConstraints'],
        'stopBoundary': {'local': result['exactStopBoundary'], 'global': result['stbufStopBoundary']},
        'executionAuthority': authority,
    })


def load_contract():
    contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
    shape(contract, ('schemaVersion', 'milestone', 'baseSha', 'sourceIdentities', 'authority',
                     'operations', 'canonical', 'stopBoundaries', 'scopeClass'), 'ClosedSourceContractRequired')
    need(type(contract['schemaVersion']) is int and contract['schemaVersion'] == 1
         and contract['milestone'] == 'M2cw' and contract['baseSha'] == BASE
         and contract['sourceIdentities'] == SOURCE_IDENTITIES and set(contract['operations']) == set(OPERATIONS)
         and canonical(contract['authority']) == canonical(AUTHORITY), 'ExactSourceContractRequired')
    return contract
