"""Five bounded source operations; canonical outputs do not grant execution authority."""
from hashlib import sha256
from copy import deepcopy
import json
from pathlib import Path
from post_consumer_continuation.analysis import load_contract as inherited_contract
from .configuration import stcon_configuration, transmit_configuration_hypotheses
from .lineage import stcon_writer_lineage
from .source_inventory import APPLICABILITY, BASE, SOURCE_BINDING, inventory
from .state import ACTUAL_FIELDS, need
from .tx_obligations import tx_lifecycle_obligations, stbuf2995_source_join

OPERATIONS = {'stcon_configuration': stcon_configuration, 'stcon_writer_lineage': stcon_writer_lineage,
    'tx_lifecycle_obligations': tx_lifecycle_obligations, 'stbuf2995_source_join': stbuf2995_source_join,
    'transmit_configuration_hypotheses': transmit_configuration_hypotheses}
CONTRACT_SHA256 = '65588939c90e94506b6004fbb1abe598f77d785cbde36ffeaeba3bae0d821c53'
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
        'corpus', 'unknownPolicy', 'authority'}, 'ClosedTransmitSourceContractRequired')
    need(value['schemaVersion'] == 1 and value['milestone'] == 'M2cs' and value['baseSha'] == BASE
         and value['contractClass'] == 'ConditionalSoftwareAndDocumentarySource_NotPeripheralExecutor',
         'ExactM2crBaseAndStaticScopeRequired')
    need(set(value['functions']) == set(OPERATIONS), 'FivePureOperationsRequired')
    need(all(set(v) == FUNCTION_FIELDS and v['ExecutionAuthority'] == 'EXECUTION_BLOCKED_NoCpuRomIrqRtiOrPeripheral'
             for v in value['functions'].values()), 'ClosedFormalFunctionContractsRequired')
    expected = inherited_contract()['instructionEvidence'] + inventory()
    need(value['instructionEvidence'] == expected and len(expected) == 91, 'ExactNinetyOneReviewedSitesRequired')
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
    nested = state.get('lineage', {})
    intent_slots = state.get('configurationIntents')
    classes = {'stcon_configuration': 'StaticRomSoftwareEffect',
        'stcon_writer_lineage': 'ConditionalSoftwareRelationship',
        'tx_lifecycle_obligations': 'ManufacturerDocumented',
        'stbuf2995_source_join': 'ConditionalSoftwareRelationship',
        'transmit_configuration_hypotheses': 'ConditionalSoftwareRelationship'}
    lineage = {'stateGenerations': deepcopy(state.get('generations')),
        'configurationIntentGenerations': None if intent_slots is None else {
            k: slot['generation'] for k, slot in intent_slots.items()},
        'lastConfigurationSlot': deepcopy(state.get('lastSlot', nested.get('state', {}).get('lastSlot'))),
        'configurationChecks': deepcopy(result.get('configurationChecks', nested.get('configurationChecks'))),
        'orderedWriterGenerations': [{'ordinal': event['ordinal'],
            'before': deepcopy(event['beforeGeneration'] if 'beforeGeneration' in event else
                               [event['beforeSlot']['generation']] if 'beforeSlot' in event else None),
            'after': deepcopy(event['afterGeneration'] if 'afterGeneration' in event else
                              event['afterSlot']['generation'] if 'afterSlot' in event else None)}
            for event in result['journal']]}
    record = {'caseId': case['id'], 'operation': case['operation'], 'input': deepcopy(case['input']),
        'output': result, 'sourceScope': deepcopy(result['sourceScope']), 'evidenceClass': classes[case['operation']],
        'applicability': APPLICABILITY, 'state': deepcopy(state),
        'branchOutcome': [{'pc': step['pc'], 'taken': step['branchTaken'], 'next': step['next']}
                          for step in result['steps'] if step['kind'] == 'Branch'],
        'reads': deepcopy(result['reads']), 'orderedWrites': deepcopy(result['journal']),
        'generationLineage': lineage, 'intermediateStates': deepcopy(result['intermediateStates']),
        'unresolvedConstraints': deepcopy(result['unresolvedConstraints']), 'stopBoundary': result['stopBoundary'],
        'executionAuthority': {key: result[key] for key in (*ACTUAL_FIELDS, 'cpuInstructionRetirements',
            'actualPeripheralOperations', 'executionStatus', 'firmwareReady', 'stbufStopBoundary')}}
    return record


def canonical_records():
    from .corpus import cases
    count, seen = load_contract()['corpus']['records'], set()
    for case in cases():
        need(case['id'] not in seen, 'DuplicateCaseIdentity')
        seen.add(case['id'])
        yield evaluate(case)
    need(len(seen) == count, 'ClosedIndependentCorpusCountRequired')
