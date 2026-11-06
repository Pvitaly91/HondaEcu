"""Six closed source transformations; canonical records never authorize execution."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tx_ack_configuration_provenance.analysis import load_contract as accepted_contract
from tx_ack_configuration_provenance.state import ACTUAL_FIELDS
from .data03cb_writers import data03cb_indexed_writer
from .mode_producer_extended import mode_producer_extended
from .caller_cfg import configuration_caller, configuration_reader_caller
from .reaching_definitions import data03cb_reaching_definitions
from .cross_block_join import cross_block_source_join
from .primary_sources import APPLICABILITY, BASE, SOURCE_BINDING, DOCUMENTARY_FACT_IDS, UNKNOWN_FACTS
from .source_inventory import NEW_SOURCE_ROWS
from .state import need

OPERATIONS = {f.__name__: f for f in (data03cb_indexed_writer, mode_producer_extended,
    configuration_caller, configuration_reader_caller, data03cb_reaching_definitions, cross_block_source_join)}
CONTRACT_SHA256 = 'd40cfd7ec653ecd07637dc942829473415f38417f3f6b5db24d043fa732547d0'
FUNCTION_FIELDS = {'Inputs', 'Preconditions', 'SourceSites', 'ExactInstructionEffects', 'BranchPredicates',
    'RegisterDependencies', 'AddressSpace', 'MemoryAccessWidth', 'PointerAliases', 'StateTransformation',
    'OrderedEffects', 'Postconditions', 'FrameConditions', 'UnknownSemantics', 'WriterGenerationLineage',
    'StopBoundary', 'Applicability', 'ExecutionAuthority'}


def validate_contract(value):
    need(type(value) is dict, 'SourceContractObjectRequired')
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    need(sha256(raw).hexdigest() == CONTRACT_SHA256, 'ExactReviewedSourceContractRequired')
    need(set(value) == {'schemaVersion', 'milestone', 'baseSha', 'contractClass', 'sourceInventory',
        'instructionEvidence', 'functions', 'sourceBinding', 'documentaryFacts', 'unknownDocumentaryRules',
        'corpus', 'unknownPolicy', 'authority'}, 'ClosedModeCallerContractRequired')
    need(value['schemaVersion'] == 1 and value['milestone'] == 'M2cu' and value['baseSha'] == BASE
         and value['contractClass'] == 'ConditionalSourceReconstruction_NotNativeContinuityOrPeripheralExecutor',
         'ExactM2ctBaseAndStaticScopeRequired')
    need(set(value['functions']) == set(OPERATIONS), 'SixReviewedPureOperationsRequired')
    need(all(set(v) == FUNCTION_FIELDS and v['ExecutionAuthority'] == 'EXECUTION_BLOCKED_NoCpuRomIrqRtiOrPeripheral'
             for v in value['functions'].values()), 'ClosedFormalFunctionContractsRequired')
    expected = accepted_contract()['instructionEvidence'] + NEW_SOURCE_ROWS
    need(value['instructionEvidence'] == expected and len(expected) == 136, 'ExactReviewedSourceRelationsRequired')
    need(value['sourceBinding'] == SOURCE_BINDING, 'ExactSourceProofBindingsRequired')
    need(value['documentaryFacts'] == DOCUMENTARY_FACT_IDS and value['unknownDocumentaryRules'] == UNKNOWN_FACTS,
         'InheritedDocumentaryQualificationsRequired')
    need(value['corpus'] == {'records': 963, 'fullByteEqualityRequired': True, 'canonicalFieldExclusions': []},
         'FrozenIndependentCorpusRequired')
    need(value['authority'] == {'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False,
        'cpuRomIrqRtiExecutions': 0, 'peripheralOperations': 0, 'actualHardwareObservation': None,
        'data03cbNativeOwnerEstablished': False, 'actualNativeContinuityEstablished': False,
        'nativeConfigurationOwnerEstablished': False, 'actualTxReadyObserved': False,
        'physicalEcuApplicabilityEstablished': False, 'certifiedByContractAlone': False,
        'stopBoundary': 'STOP_BEFORE_STBUF_2995'}, 'SourceContractCannotPromoteHardwareAuthority')
    need(all(v is True for v in value['unknownPolicy'].values()), 'UnknownPolicyCannotBeWeakened')
    return value


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))


def evaluate(case):
    need(type(case) is dict and set(case) == {'id', 'operation', 'input'}
         and type(case['id']) is str and bool(case['id']) and type(case['operation']) is str
         and case['operation'] in OPERATIONS, 'ClosedConditionalCaseRequired')
    result = OPERATIONS[case['operation']](case['input'])
    state = result['state']
    generations = {'data': deepcopy(state.get('generations')),
        'softwareIntents': {k: v['generation'] for k, v in state['configurationIntents'].items()} if 'configurationIntents' in state else None,
        'suppliedReadbacks': {k: v['generation'] for k, v in state['sfrReadbacks'].items()} if 'sfrReadbacks' in state else None,
        'writerEvents': [{'ordinal': e['ordinal'], 'before': deepcopy(e.get('beforeGeneration')),
                          'after': deepcopy(e.get('afterGeneration'))} for e in result['journal']],
        'reachingDefinitions': deepcopy(state.get('reachingDefinitions'))}
    return {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
        'output': result, 'sourceScope': deepcopy(result['sourceScope']), 'sourceIdentities': deepcopy(SOURCE_BINDING),
        'evidenceClass': 'StaticRomSoftwareEffect' if case['operation'] in tuple(OPERATIONS)[:4] else 'ConditionalSoftwareRelationship',
        'applicability': APPLICABILITY, 'state': deepcopy(state),
        'branchOutcome': [{'pc': s['pc'], 'taken': s['branchTaken'], 'next': s['next']}
                          for s in result['steps'] if s['kind'] == 'Branch'],
        'reads': deepcopy(result['reads']), 'orderedWrites': deepcopy(result['journal']),
        'generations': generations, 'intermediateStates': deepcopy(result['intermediateStates']),
        'unresolvedConstraints': deepcopy(result['unresolvedConstraints']), 'stopBoundary': result['stopBoundary'],
        'executionAuthority': {k: result[k] for k in (*ACTUAL_FIELDS, 'cpuInstructionRetirements',
            'actualPeripheralOperations', 'executionStatus', 'firmwareReady', 'stbufStopBoundary')}}


def canonical_records():
    from .corpus import cases
    count, seen = load_contract()['corpus']['records'], set()
    for case in cases():
        need(case['id'] not in seen, 'DuplicateCaseIdentity')
        seen.add(case['id'])
        yield evaluate(case)
    need(len(seen) == count, 'ClosedIndependentCorpusCountRequired')
