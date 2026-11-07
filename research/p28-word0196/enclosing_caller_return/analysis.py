"""Project complete conditional effects to the public canonical wire."""
from copy import deepcopy
import json
from pathlib import Path

from .call_return_obligations import call_return_obligations
from .callee_effects import callee_clobber_summary
from .indexed_caller import indexed_acquisition_caller
from .mode_caller import mode_enclosing_caller
from .program_table import program_table_path
from .reaching_definitions import indexed_to_mode_reaching_definitions
from .source_inventory import APPLICABILITY, BASE, SOURCE_IDENTITIES
from .state import ACTUAL, need, shape
from tx_ack_configuration_provenance.state import ACTUAL_FIELDS

OPERATIONS = {function.__name__: function for function in (
    mode_enclosing_caller, program_table_path, callee_clobber_summary, indexed_acquisition_caller,
    call_return_obligations, indexed_to_mode_reaching_definitions,
)}
AUTHORITY = {**dict.fromkeys(ACTUAL_FIELDS), **ACTUAL, 'cpuInstructionRetirements': 0,
             'actualPeripheralOperations': 0, 'executionStatus': 'EXECUTION_BLOCKED',
             'firmwareReady': False, 'stbufStopBoundary': 'STOP_BEFORE_STBUF_2995'}
REGISTER_FIELDS = ('afterRegisters', 'afterRegisterKnownBits', 'afterPointerState', 'afterX1State')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def validate_authority(value):
    """Reject promoted observations anywhere in a result, including retained children."""
    if type(value) is dict:
        for key, item in value.items():
            if key in AUTHORITY:
                expected = AUTHORITY[key]
                need(type(item) is type(expected) and item == expected, 'UnadmittedExecutionAuthority')
            validate_authority(item)
    elif type(value) is list:
        for item in value:
            validate_authority(item)


def record(case):
    shape(case, ('id', 'operation', 'input'), 'ClosedCaseRequired')
    name = case['operation']
    need(type(case['id']) is str and bool(case['id']) and type(name) is str and name in OPERATIONS,
         'KnownOperationAndCaseIdentityRequired')
    result = OPERATIONS[name](deepcopy(case['input']))
    authority = {key: result[key] for key in AUTHORITY}
    validate_authority(result)
    state = result['state']
    generations = {
        'data': state.get('generations'),
        'softwareIntents': {key: row['generation'] for key, row in state['configurationIntents'].items()}
        if 'configurationIntents' in state else None,
        'suppliedReadbacks': {key: row['generation'] for key, row in state['sfrReadbacks'].items()}
        if 'sfrReadbacks' in state else None,
        'writerEvents': [{'ordinal': row['ordinal'], 'before': row.get('beforeGeneration'),
                          'after': row.get('afterGeneration')} for row in result['journal']],
        'reachingDefinitions': state.get('reachingDefinitions'),
    }
    return deepcopy({
        'caseId': case['id'], 'operation': name, 'input': case['input'], 'output': result,
        'sourceScope': result['sourceScope'], 'sourceIdentities': SOURCE_IDENTITIES,
        'evidenceClass': result['effectClass'], 'applicability': APPLICABILITY,
        'sourceEdges': result.get('sourceEdges', []),
        'branchOutcome': [{'pc': row['pc'], 'taken': row['branchTaken'], 'next': row['next']}
                          for row in result['steps'] if row['kind'] == 'Branch'],
        'registerEffects': [{'pc': row['pc'], **{field: row.get(field) for field in REGISTER_FIELDS}}
                            for row in result['steps']],
        'reads': result['reads'], 'orderedWrites': result['journal'],
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
         and contract['milestone'] == 'M2cv' and contract['baseSha'] == BASE
         and contract['sourceIdentities'] == SOURCE_IDENTITIES and set(contract['operations']) == set(OPERATIONS)
         and canonical(contract['authority']) == canonical(AUTHORITY), 'ExactSourceContractRequired')
    return contract
