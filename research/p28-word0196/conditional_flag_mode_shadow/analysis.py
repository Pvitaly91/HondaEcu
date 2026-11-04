"""Evaluate only the closed conditional software corpus, without target execution."""
import json
from pathlib import Path

from .flag import flag_body, flag_path, status_clear
from .mode import consistency_check, initial_pair, mask_hypotheses, mode_switch

OPERATIONS = {'flag_body': flag_body, 'flag_path': flag_path, 'status_clear': status_clear,
              'initial_pair': initial_pair, 'mode_switch': mode_switch,
              'consistency_check': consistency_check, 'mask_hypotheses': mask_hypotheses}


def validate_contract(contract):
    if (type(contract) is not dict or set(contract) != {'schemaVersion', 'milestone', 'baseSha',
            'contractClass', 'sourceInventory', 'instructionEvidence', 'functions', 'corpus', 'unknownPolicy', 'authority'}
            or type(contract.get('schemaVersion')) is not int or contract['schemaVersion'] != 1
            or contract.get('milestone') != 'M2cn'
            or contract.get('baseSha') != 'bd00992a55d89be84ea797b12d38223996dcb999'
            or set(contract.get('functions', {})) != set(OPERATIONS)):
        raise ValueError('ClosedSourceQualifiedM2cnContractRequired')
    authority = contract['authority']
    if (type(authority) is not dict or set(authority) != {'executionStatus', 'firmwareReady',
            'actualHardwareObservation', 'cpuRomIrqRtiExecutions', 'certifiedByContractAlone',
            'physicalSF', 'physicalEcuIdentity', 'actualFrameSafety', 'rxAckReassertion', 'iePolarity'}
            or authority.get('executionStatus') != 'EXECUTION_BLOCKED'
            or authority.get('firmwareReady') is not False
            or authority.get('actualHardwareObservation') is not None
            or type(authority.get('cpuRomIrqRtiExecutions')) is not int
            or authority['cpuRomIrqRtiExecutions'] != 0
            or authority.get('certifiedByContractAlone') is not False
            or any(authority[k] is not None for k in ('physicalSF', 'physicalEcuIdentity', 'actualFrameSafety'))
            or authority['rxAckReassertion'] != 'Unknown' or authority['iePolarity'] != 'SourceConflictRetained'):
        raise ValueError('SoftwareContractCannotAdmitHardwareExecution')
    sites = contract['instructionEvidence']
    if (type(sites) is not list or len(sites) != 73 or any(type(row) is not dict for row in sites)
            or len({row.get('pc') for row in sites}) != 73):
        raise ValueError('SeventyThreeUniqueSourceSitesRequired')
    fields = {'pc', 'pcHex', 'form', 'length', 'primarySource', 'printedPage', 'effectScope', 'privateOriginalAndListingFence'}
    for row in sites:
        if (set(row) != fields or type(row['pc']) is not int or not 0 <= row['pc'] <= 65535
                or row['pcHex'] != f"{row['pc']:04X}" or row['primarySource'] != 'ISA1991'
                or type(row['length']) is not int or not 1 <= row['length'] <= 5
                or not all(type(row[k]) is str and row[k] for k in ('form', 'printedPage'))
                or row['effectScope'] != 'ConditionalReviewedInstructionEffect_NotDecodedOrRetiredHere'
                or row['privateOriginalAndListingFence'] != 'VerifiedLocally_NotRepublished'):
            raise ValueError('InstructionPrimaryScopeAndIdentityRequired')
    if any(contract['unknownPolicy'].get(key) is not True for key in (
            'nullMeansUnknown', 'unknownBranchDoesNotSelectPath', 'sameValueUnknownWithoutWholeKnownValues',
            'sameValueWritesNeverRemoved')):
        raise ValueError('UnknownAndOrderedEffectPolicyCannotBeWeakened')
    if contract['corpus'] != {'records': 1744, 'fullFlagFValues': 256,
            'r6BoundaryValues': [0, 1, 15, 127, 128, 255],
            'allInputsExplicitAndInventedOrSymbolic': True, 'firstMismatchRequired': True}:
        raise ValueError('ClosedIndependentCorpusRequired')
    return contract


def load_contract():
    try:
        return validate_contract(json.loads(Path(__file__).with_name('contract.json').read_bytes()))
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('MalformedSourceContract') from error


def evaluate(case):
    if (type(case) is not dict or set(case) != {'id', 'operation', 'input'}
            or type(case['id']) is not str or not case['id']
            or type(case['operation']) is not str or case['operation'] not in OPERATIONS):
        raise ValueError('ClosedTypedConditionalCaseRequired')
    return {'caseId': case['id'], 'operation': case['operation'], 'input': case['input'],
            'output': OPERATIONS[case['operation']](case['input'])}


def canonical_records():
    from .corpus import cases
    load_contract()
    seen = set()
    for case in cases():
        if case['id'] in seen:
            raise ValueError('DuplicateConditionalCaseIdentity')
        seen.add(case['id'])
        yield evaluate(case)
    if len(seen) != 1744:
        raise ValueError('Closed1744CaseCorpusRequired')
