"""Source-bound five-operation witness records, not CPU execution evidence."""
from hashlib import sha256
import json
from pathlib import Path

from .consumer_model import payload_consumer
from .consumer_search import search_inventory
from .rti_obligations import rti_obligations
from .state import need
from .tail import parser_step_with_tail, post_checksum_tail
from .writer_lineage import last_writer_at_conditional_boundary

OPERATIONS = {'payload_consumer': payload_consumer, 'post_checksum_tail': post_checksum_tail,
              'parser_step_with_tail': parser_step_with_tail,
              'last_writer_at_conditional_boundary': last_writer_at_conditional_boundary,
              'rti_obligations': rti_obligations}
CONTRACT_SHA256 = 'f7f5a52aa441f78339be0cd83ded427f6c460f4e200ed6f96405fe5dbce52272'


def validate_contract(contract):
    need(type(contract) is dict, 'SourceContractObjectRequired')
    raw = (json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False) + '\n').encode('ascii')
    need(sha256(raw).hexdigest() == CONTRACT_SHA256, 'ExactReviewedSourceContractRequired')
    need(set(contract) == {'schemaVersion', 'milestone', 'baseSha', 'contractClass', 'sourceInventory',
        'instructionEvidence', 'functions', 'consumerSearch', 'corpus', 'unknownPolicy', 'authority'},
        'ClosedConsumerTailContractRequired')
    need(contract['schemaVersion'] == 1 and contract['milestone'] == 'M2cq'
         and contract['baseSha'] == 'a6f765ee2a3ac180d1a4c9687238db5aa923956c'
         and contract['contractClass'] == 'ConditionalSoftwareReconstruction_NotCpuExecutor',
         'ExactM2cpBaseAndStaticScopeRequired')
    need(set(contract['functions']) == set(OPERATIONS), 'FivePureOperationsRequired')
    required = {'Inputs', 'Preconditions', 'SourceSites', 'AccessWidth', 'BranchPredicates',
        'RegisterEffects', 'OrderedWrites', 'Postconditions', 'FrameConditions', 'StopBoundary',
        'UnknownSemantics', 'WriterLineage', 'Applicability', 'ExecutionAuthority'}
    need(all(set(value) == required and value['ExecutionAuthority'] == 'EXECUTION_BLOCKED_NoCpuRomIrqRti'
             for value in contract['functions'].values()), 'ClosedFormalFunctionContractsRequired')
    need(contract['consumerSearch'] == search_inventory(), 'StaticReviewedSearchInventoryRequired')
    rows = contract['instructionEvidence']
    need(type(rows) is list and len(rows) == 49 and len({row['pc'] for row in rows}) == 49,
         'FortyNineClosedSourceSitesRequired')
    sites = {row['pc'] for row in rows}
    need(all(set(function['SourceSites']) <= sites for function in contract['functions'].values()),
         'FunctionOutsideReviewedSourceInventory')
    need(type(contract['corpus']['records']) is int and contract['corpus']['records'] > 0
         and contract['corpus']['fullByteEqualityRequired'] is True, 'FrozenIndependentCorpusRequired')
    authority = contract['authority']
    need(authority['executionStatus'] == 'EXECUTION_BLOCKED' and authority['firmwareReady'] is False
         and authority['cpuRomIrqRtiExecutions'] == 0 and authority['actualHardwareObservation'] is None
         and authority['specific026CReachingDefinitionEstablished'] is False
         and authority['actualFrameOrReturnObserved'] is False
         and authority['certifiedByContractAlone'] is False, 'ContractCannotPromoteNativeAuthority')
    need(all(value is True for value in contract['unknownPolicy'].values()), 'UnknownPolicyCannotBeWeakened')
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
