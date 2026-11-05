"""Closed source-qualified reconstruction records, without execution authority."""
from hashlib import sha256
import json
from pathlib import Path

from length_checksum_dataflow.analysis import SITES as INHERITED_SITES, TARGETS
from length_checksum_dataflow.state import require

from .composition import compose
from .counter import counter_route
from .dispatch import dispatch, parser_step
from .payload import data_body, generic_payload_body

OPERATIONS = {'generic_payload_body': generic_payload_body, 'data_body': data_body,
              'dispatch': dispatch, 'parser_step': parser_step,
              'counter_route': counter_route, 'compose': compose}
SITES = INHERITED_SITES | {0x26C}
CONTRACT_SHA256 = '8e189ee76a7538e03151f986428647fa4814ccddb4598f0661b0eac236a9ca11'


def validate_contract(contract):
    try:
        require(type(contract) is dict and set(contract) == {
            'schemaVersion', 'milestone', 'baseSha', 'contractClass', 'sourceInventory',
            'instructionEvidence', 'functions', 'corpus', 'composition', 'unknownPolicy', 'authority'},
            'ClosedSourceQualifiedM2cpContractRequired')
        raw = (json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()
        require(sha256(raw).hexdigest() == CONTRACT_SHA256, 'ExactReviewedSourceContractRequired')
        require(type(contract['schemaVersion']) is int and contract['schemaVersion'] == 1
                and contract['milestone'] == 'M2cp'
                and contract['baseSha'] == 'caf5552e4fc20e9b120726c7aa7822e75ab33aff'
                and contract['contractClass'] == 'ConditionalSoftwareReconstruction_NotCpuExecutor',
                'ExactM2coBaseAndResearchScopeRequired')
        require(set(contract['functions']) == set(OPERATIONS), 'SixPureOperationsRequired')
        required = {'Inputs', 'Preconditions', 'IsaSourceSites', 'BranchPredicates', 'RequiredBankPageContext',
                    'StateTransformation', 'OrderedSideEffects', 'Postconditions', 'FrameConditions',
                    'UnknownPropagation', 'StopBoundaries', 'CompositionRequirements',
                    'ApplicabilityScope', 'ExecutionAuthority'}
        for function in contract['functions'].values():
            require(type(function) is dict and set(function) == required
                    and set(function['IsaSourceSites']) <= SITES
                    and function['ExecutionAuthority'] == 'EXECUTION_BLOCKED_NoCpuRomIrqRti_FirmwareReadyFalse',
                    'FormalSourceQualifiedFunctionContractRequired')
        rows = contract['instructionEvidence']
        require(type(rows) is list and len(rows) == 38 and {row['pc'] for row in rows} == SITES,
                'ThirtyEightUniqueSourceSitesRequired')
        for row in rows:
            require(set(row) == {'pc', 'pcHex', 'form', 'length', 'ddMode', 'successors',
                                 'printedPage', 'primarySource', 'effectScope'}
                    and type(row['pc']) is int and row['pcHex'] == f"{row['pc']:04X}"
                    and type(row['length']) is int and 1 <= row['length'] <= 4
                    and row['successors'] == TARGETS.get(row['pc'], [row['pc'] + row['length']])
                    and row['primarySource'] == 'ISA1991'
                    and row['effectScope'] == 'ConditionalReviewedInstructionEffect_NotDecodedOrRetiredHere',
                    'ExactReviewedInstructionFormAndSuccessorsRequired')
        generic = next(row for row in rows if row['pc'] == 0x26C)
        require(generic['length'] == 1 and generic['ddMode'] == '0' and generic['successors'] == [0x26D],
                'DdZeroByteStoreAt026cRequired')
        authority = contract['authority']
        require(authority['executionStatus'] == 'EXECUTION_BLOCKED' and authority['firmwareReady'] is False
                and type(authority['cpuRomIrqRtiExecutions']) is int and authority['cpuRomIrqRtiExecutions'] == 0
                and authority['actualHardwareObservation'] is None and authority['certifiedByContractAlone'] is False
                and authority['nativeInterBlockContinuity'] is None and authority['actualEcuEquivalence'] is None,
                'ContractCannotPromoteExecutionOrHardwareEquivalence')
        require(contract['composition']['maximumStages'] == 512
                and contract['composition']['resourceLimitIsProtocolLimit'] is False
                and contract['composition']['nativeReentryEdgeEstablished'] is False,
                'SyntheticResourceLimitCannotBecomeProtocolOrNativeAuthority')
        require(all(value is True for value in contract['unknownPolicy'].values()),
                'UnknownAndDdContextPolicyCannotBeWeakened')
        corpus = contract['corpus']
        require(set(corpus) == {'records', 'allInputsExplicitAndInventedOrSymbolic', 'fullByteEqualityRequired'}
                and type(corpus['records']) is int and corpus['records'] > 0
                and corpus['allInputsExplicitAndInventedOrSymbolic'] is True
                and corpus['fullByteEqualityRequired'] is True, 'IndependentDefinitiveCorpusRequired')
        return contract
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('MalformedSourceContract') from error


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))


def evaluate(case):
    require(type(case) is dict and set(case) == {'id', 'operation', 'input'}
            and type(case['id']) is str and bool(case['id'])
            and type(case['operation']) is str and case['operation'] in OPERATIONS,
            'ClosedTypedConditionalCaseRequired')
    return {'caseId': case['id'], 'operation': case['operation'], 'input': case['input'],
            'output': OPERATIONS[case['operation']](case['input'])}


def canonical_records():
    from .corpus import cases
    count = load_contract()['corpus']['records']
    seen = set()
    for case in cases():
        require(case['id'] not in seen, 'DuplicateConditionalCaseIdentity')
        seen.add(case['id'])
        yield evaluate(case)
    require(len(seen) == count, 'ClosedIndependentCorpusRequired')
