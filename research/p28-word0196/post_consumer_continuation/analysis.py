"""Four source-bound operations with full deterministic records; no execution admission."""
from hashlib import sha256
import json
from pathlib import Path
from payload_consumer_tail.analysis import load_contract as inherited_contract
from .continuation import post_consumer_continuation, consumer_with_continuation
from .lineage import continuation_lineage
from .source_inventory import BASE, SOURCE_BINDING, inventory
from .state import need
from .stbuf_obligations import stbuf_boundary_obligations

OPERATIONS = {'post_consumer_continuation': post_consumer_continuation,
              'consumer_with_continuation': consumer_with_continuation,
              'stbuf_boundary_obligations': stbuf_boundary_obligations,
              'continuation_lineage': continuation_lineage}
CONTRACT_SHA256 = '10139e105b8cc7f9db860b9c4a79edcc142cd34d0e854f7c0fa979663fd04eec'
FIELDS = {'Inputs', 'Preconditions', 'SourceSites', 'ExactInstructionEffects', 'BranchPredicates',
          'RegisterDependencies', 'AddressSpace', 'MemoryAccessWidth', 'PointerAliases',
          'StateTransformation', 'OrderedEffects', 'Postconditions', 'FrameConditions',
          'UnknownSemantics', 'WriterGenerationLineage', 'StopBoundary', 'Applicability', 'ExecutionAuthority'}


def validate_contract(contract):
    need(type(contract) is dict, 'SourceContractObjectRequired')
    raw = (json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False) + '\n').encode('ascii')
    need(sha256(raw).hexdigest() == CONTRACT_SHA256, 'ExactReviewedSourceContractRequired')
    need(set(contract) == {'schemaVersion', 'milestone', 'baseSha', 'contractClass', 'sourceInventory',
        'instructionEvidence', 'functions', 'sourceBinding', 'corpus', 'unknownPolicy', 'authority'},
        'ClosedContinuationContractRequired')
    need(contract['schemaVersion'] == 1 and contract['milestone'] == 'M2cr' and contract['baseSha'] == BASE
         and contract['contractClass'] == 'ConditionalSoftwareReconstruction_NotCpuExecutor',
         'ExactM2cqBaseAndStaticScopeRequired')
    need(set(contract['functions']) == set(OPERATIONS), 'FourPureOperationsRequired')
    need(all(set(v) == FIELDS and v['ExecutionAuthority'] == 'EXECUTION_BLOCKED_NoCpuRomIrqRtiOrPeripheral'
             for v in contract['functions'].values()), 'ClosedFormalFunctionContractsRequired')
    expected = inherited_contract()['instructionEvidence'] + inventory()
    need(contract['instructionEvidence'] == expected and len(expected) == 60, 'ExactSixtySourceSitesRequired')
    need(contract['sourceBinding'] == SOURCE_BINDING, 'ExactStaticSourceBindingRequired')
    need(type(contract['corpus']['records']) is int and contract['corpus']['records'] > 0
         and contract['corpus']['fullByteEqualityRequired'] is True, 'FrozenIndependentCorpusRequired')
    authority = contract['authority']
    need(authority == {'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False,
         'cpuRomIrqRtiExecutions': 0, 'actualHardwareObservation': None, 'peripheralOperations': 0,
         'specific026CReachingDefinitionEstablished': False, 'peripheralEquivalenceEstablished': False,
         'actualEcuEquivalenceEstablished': False, 'certifiedByContractAlone': False},
         'ContractCannotPromoteNativeOrPeripheralAuthority')
    need(all(v is True for v in contract['unknownPolicy'].values()), 'UnknownPolicyCannotBeWeakened')
    return contract


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))


def evaluate(case):
    need(type(case) is dict and set(case) == {'id', 'operation', 'input'}
         and type(case['id']) is str and bool(case['id'])
         and type(case['operation']) is str and case['operation'] in OPERATIONS, 'ClosedConditionalCaseRequired')
    return {'caseId': case['id'], 'operation': case['operation'], 'input': case['input'],
            'output': OPERATIONS[case['operation']](case['input'])}


def canonical_records():
    from .corpus import cases
    count = load_contract()['corpus']['records']
    seen = set()
    for case in cases():
        need(case['id'] not in seen, 'DuplicateCaseIdentity')
        seen.add(case['id'])
        yield evaluate(case)
    need(len(seen) == count, 'ClosedIndependentCorpusCountRequired')
