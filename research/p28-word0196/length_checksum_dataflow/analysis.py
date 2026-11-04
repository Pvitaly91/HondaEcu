"""Closed typed reconstruction cases and deterministic complete result records."""
import json
from hashlib import sha256
from pathlib import Path

from .checksum import checksum_body
from .dataflow import compose
from .dispatch import dispatch, parser_step
from .header import header_body
from .length import length_body

CASE_COUNT = 2034

OPERATIONS = {'header_body': header_body, 'length_body': length_body,
              'checksum_body': checksum_body, 'dispatch': dispatch,
              'parser_step': parser_step, 'compose': compose}
CONTRACT_SHA256 = '8234aed3d9f45788551671b7d2eb6b453bc0fbda1130ceb3ae2c8501b86d6994'
SITES = frozenset((0x21F, 0x222, 0x225, 0x255, 0x256, 0x258, 0x259, 0x25B,
    0x25D, 0x25F, 0x260, 0x262, 0x264, 0x267, 0x269, 0x26A, 0x26D, 0x26F,
    0x270, 0x275, 0x277, 0x279, 0x27A, 0x27B, 0x27D, 0x27F, 0x281, 0x282,
    0x284, 0x286, 0x287, 0x289, 0x28A, 0x28C, 0x28E, 0x290, 0x293))
TARGETS = {0x21F: [0x29D, 0x222], 0x225: [0x255, 0x227], 0x256: [0x275, 0x258],
           0x25B: [0x27F, 0x25D], 0x260: [0x284, 0x262], 0x267: [0x26C, 0x269],
           0x26A: [0x26D], 0x27D: [0x270], 0x282: [0x26D],
           0x287: [0x270, 0x289], 0x28E: [0x270, 0x290]}


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def validate_contract(contract):
    try:
        need(type(contract) is dict and set(contract) == {
            'schemaVersion', 'milestone', 'baseSha', 'contractClass', 'sourceInventory',
            'instructionEvidence', 'functions', 'corpus', 'composition', 'unknownPolicy', 'authority'},
            'ClosedSourceQualifiedM2coContractRequired')
        raw = (json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()
        need(sha256(raw).hexdigest() == CONTRACT_SHA256, 'ExactSourceQualifiedContractRequired')
        need(type(contract['schemaVersion']) is int and contract['schemaVersion'] == 1
             and contract['milestone'] == 'M2co'
             and contract['baseSha'] == 'eb4fed49ccea39e8b08ea116d84aafa8da026956'
             and contract['contractClass'] == 'ConditionalSoftwareReconstruction_NotCpuExecutor',
             'ExactM2cnBaseAndResearchScopeRequired')
        authority = {'executionStatus': 'EXECUTION_BLOCKED', 'firmwareReady': False,
            'actualHardwareObservation': None, 'cpuRomIrqRtiExecutions': 0,
            'certifiedByContractAlone': False, 'physicalSF': None, 'actualFrameSafety': None,
            'rxAckReassertion': 'Unknown', 'iePolarity': 'SourceConflictRetained',
            'nativeInterBlockContinuity': None, 'serialPacketFraming': None}
        need(contract['authority'] == authority
             and type(contract['authority']['cpuRomIrqRtiExecutions']) is int
             and contract['authority']['firmwareReady'] is False
             and contract['authority']['certifiedByContractAlone'] is False,
             'SoftwareContractCannotAdmitExecutionOrNativeOwnership')
        fields = {'InputDomain', 'Preconditions', 'SourceSites', 'BranchPredicates', 'StateTransformation',
                  'OrderedEffects', 'Postconditions', 'FrameConditions', 'UnknownSemantics',
                  'Applicability', 'StopBoundary', 'ExecutionAuthority'}
        need(type(contract['functions']) is dict and set(contract['functions']) == set(OPERATIONS),
             'SixClosedPureFunctionsRequired')
        for function in contract['functions'].values():
            need(type(function) is dict and set(function) == fields
                 and type(function['SourceSites']) is list and set(function['SourceSites']) <= SITES
                 and function['ExecutionAuthority'] == 'EXECUTION_BLOCKED_NoCpuRomIrqRti_FirmwareReadyFalse',
                 'FormalTypedFunctionContractRequired')
        rows = contract['instructionEvidence']
        need(type(rows) is list and len(rows) == 37 and {r['pc'] for r in rows} == SITES,
             'ThirtySevenUniqueSourceSitesRequired')
        for row in rows:
            need(set(row) == {'pc', 'pcHex', 'form', 'length', 'printedPage', 'primarySource', 'effectScope', 'successors'}
                 and type(row['pc']) is int and row['pcHex'] == f"{row['pc']:04X}"
                 and type(row['length']) is int and 1 <= row['length'] <= 4
                 and type(row['form']) is str and bool(row['form'])
                 and type(row['printedPage']) is str and bool(row['printedPage'])
                 and row['primarySource'] == 'ISA1991'
                 and row['effectScope'] == 'ConditionalReviewedInstructionEffect_NotDecodedOrRetiredHere'
                 and row['successors'] == TARGETS.get(row['pc'], [row['pc'] + row['length']]),
                 'ExactReviewedFormsAndCfgTargetsRequired')
        need(contract['composition'] == {
            'allowedEdges': [['Header', 'Length'], ['Length', 'Flag'], ['Length', 'Checksum'], ['Flag', 'Checksum']],
            'maximumStages': 4, 'firstRole': 'Header', 'nativeReentryEdgeEstablished': False,
            'handoffRelation': 'ConditionalPersistentStateHandoff', 'new0055IsSuppliedSnapshotInputNotWrite': True},
            'ConditionalHandoffCannotCreateNativeCfgEdge')
        need(type(contract['unknownPolicy']) is dict and set(contract['unknownPolicy']) == {
            'nullMeansUnknown', 'sameValueWritesNeverRemoved', 'unknownBranchDoesNotSelectPath',
            'arithmeticConservativelyUnknown', 'missingGenerationNotNativeOwner', 'partialRmwPreservesNeighbors'}
             and all(value is True for value in contract['unknownPolicy'].values()), 'UnknownPolicyCannotBeWeakened')
        need(contract['corpus'] == {'records': CASE_COUNT, 'allInputsExplicitAndInventedOrSymbolic': True,
             'fullByteEqualityRequired': True}, 'IndependentFrozenCorpusRequired')
        return contract
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('MalformedSourceContract') from error


def load_contract():
    return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))


def evaluate(case):
    need(type(case) is dict and set(case) == {'id', 'operation', 'input'}
         and type(case['id']) is str and bool(case['id'])
         and type(case['operation']) is str and case['operation'] in OPERATIONS,
         'ClosedTypedConditionalCaseRequired')
    return {'caseId': case['id'], 'operation': case['operation'], 'input': case['input'],
            'output': OPERATIONS[case['operation']](case['input'])}


def canonical_records():
    from .corpus import cases
    load_contract()
    seen = set()
    for case in cases():
        need(case['id'] not in seen, 'DuplicateConditionalCaseIdentity')
        seen.add(case['id'])
        yield evaluate(case)
    need(len(seen) == CASE_COUNT, 'ClosedFrozenCorpusRequired')
