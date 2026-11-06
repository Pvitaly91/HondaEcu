"""Five closed conditional operations; canonical calculations grant no execution authority."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from stbuf_stcon_transmit_source.analysis import load_contract as accepted_contract
from .reader_cfg import tx_configuration_reader
from .mode_producer import mode_bit1_producer
from .reaching_definitions import tx_configuration_reaching_definitions
from .tx_ack_rules import tx_ack_documentary_obligations
from .source_join import stbuf2995_configuration_provenance
from .primary_sources import APPLICABILITY, BASE, SOURCE_BINDING, inventory
from .state import ACTUAL_FIELDS, need

OPERATIONS = {'tx_configuration_reader': tx_configuration_reader,
    'mode_bit1_producer': mode_bit1_producer,
    'tx_configuration_reaching_definitions': tx_configuration_reaching_definitions,
    'tx_ack_documentary_obligations': tx_ack_documentary_obligations,
    'stbuf2995_configuration_provenance': stbuf2995_configuration_provenance}
CONTRACT_SHA256 = '2f70810878510a39854fd28d8e7e6ae4f2daf5aaebc848d72e15343ae886541d'
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
        'corpus', 'unknownPolicy', 'authority'}, 'ClosedAckConfigurationContractRequired')
    need(value['schemaVersion'] == 1 and value['milestone'] == 'M2ct' and value['baseSha'] == BASE
         and value['contractClass'] == 'ConditionalSoftwareAndDocumentarySource_NotPeripheralExecutor',
         'ExactM2csBaseAndStaticScopeRequired')
    need(set(value['functions']) == set(OPERATIONS), 'FivePureOperationsRequired')
    need(all(set(v) == FUNCTION_FIELDS and v['ExecutionAuthority'] == 'EXECUTION_BLOCKED_NoCpuRomIrqRtiOrPeripheral'
             for v in value['functions'].values()), 'ClosedFormalFunctionContractsRequired')
    expected = accepted_contract()['instructionEvidence'] + inventory()
    need(value['instructionEvidence'] == expected and len(expected) == 111, 'ExactReviewedInstructionRelationsRequired')
    need(value['sourceBinding'] == SOURCE_BINDING, 'ExactSourceProofBindingsRequired')
    need(type(value['corpus']['records']) is int and value['corpus']['records'] > 0
         and value['corpus']['fullByteEqualityRequired'] is True, 'FrozenIndependentCorpusRequired')
    need(value['authority'] == {'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False,
        'cpuRomIrqRtiExecutions': 0, 'peripheralOperations': 0, 'actualHardwareObservation': None,
        'nativeConfigurationOwnerEstablished': False, 'actualTxReadyObserved': False,
        'physicalEcuApplicabilityEstablished': False, 'certifiedByContractAlone': False},
        'SourceContractCannotPromoteHardwareAuthority')
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
    classes = {'tx_configuration_reader': 'StaticRomSoftwareEffect', 'mode_bit1_producer': 'StaticRomSoftwareEffect',
        'tx_configuration_reaching_definitions': 'ConditionalSoftwareRelationship',
        'tx_ack_documentary_obligations': 'ManufacturerDocumented',
        'stbuf2995_configuration_provenance': 'ConditionalSoftwareRelationship'}
    generations = {'data': deepcopy(state.get('generations')),
        'softwareIntents': {k: v['generation'] for k, v in state['configurationIntents'].items()} if 'configurationIntents' in state else None,
        'suppliedReadbacks': {k: v['generation'] for k, v in state['sfrReadbacks'].items()} if 'sfrReadbacks' in state else None,
        'writerEvents': [{'ordinal': e['ordinal'], 'before': deepcopy(e.get('beforeGeneration')),
                          'after': deepcopy(e.get('afterGeneration'))} for e in result['journal']],
        'reachingDefinitions': deepcopy(state.get('reachingDefinitions'))}
    return {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
        'output': result, 'sourceScope': deepcopy(result['sourceScope']), 'evidenceClass': classes[case['operation']],
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
