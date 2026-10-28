"""Closed source predicate for the explicitly bounded blocked-research CI lane."""
import ast
from hashlib import sha256
import json

from original_rom_boundary.source_guard import Blob, canonical, safe_name
from native_data0217_011f_bridge.ci_contract import BASE, WORKFLOW, workflow_projection

BASE_SOURCE_COUNT = 1150
BASE_FINGERPRINT = 'cc6d2297ef3ef05ecb774ca734c16e6a2b50a83614476c31040dcf082467f84e'
PACKAGE = 'research/p28-word0196/native_data0217_011f_bridge/'
NEW_PATHS = frozenset(PACKAGE + name for name in (
    '__init__.py', 'contract.json', 'helper_cfg.py', 'bridge_reachability.py',
    'constraint_model.py', 'reference_oracle.py', 'bridge_tests.py', 'analysis.py',
    'source_guard.py', 'ci_contract.py', 'ci_projection.py', 'ci_routing.py',
    'ci_contract_tests.py',
)) | frozenset({
    'research/p28-word0196/validate_native_data0217_011f_bridge.py',
    'docs/M2CC_DATA0217_011F_SAME_MACHINE_BRIDGE.md',
})


def source_rows(blobs):
    return [{'path': name, 'mode': blob.mode, 'bytes': len(blob.data),
             'sha256': sha256(blob.data).hexdigest()} for name, blob in sorted(blobs.items())]


def new_source_fingerprint(current):
    """Fifteen new sources only; the separately reviewed workflow is excluded."""
    return sha256(canonical(source_rows({name: current[name] for name in NEW_PATHS}))).hexdigest()


def _valid_source_maps(base, current):
    if type(base) is not dict or type(current) is not dict:
        raise ValueError('CompleteSourceMappingsRequired')
    for name, blob in (*base.items(), *current.items()):
        if (not safe_name(name) or not isinstance(blob, Blob)
                or blob.mode not in ('100644', '100755') or type(blob.data) is not bytes):
            raise ValueError('RegularRawGitSourceBlobsRequired')
    if (len(base) != BASE_SOURCE_COUNT
            or sha256(canonical(source_rows(base))).hexdigest() != BASE_FINGERPRINT):
        raise ValueError('ExactAcceptedM2cb1150SourceRequired')


def _new_text_source(name, blob):
    if blob.mode != '100644' or not 0 < len(blob.data) <= 2 * 1024 * 1024 or b'\0' in blob.data:
        raise ValueError('BoundedNewResearchTextRequired')
    text = blob.data.decode('utf-8', 'strict')
    if name.endswith('.py'):
        ast.parse(text, filename=name)
    elif name.endswith('.json'):
        def reject_constant(_value):
            raise ValueError('NonfiniteResearchContractRefused')
        value = json.loads(text, parse_constant=reject_constant)
        if type(value) is not dict:
            raise ValueError('ResearchContractObjectRequired')


def research_projection(base, current, approved_new_source_fingerprint):
    """Exact finite additions plus one workflow-only orchestration overlay."""
    _valid_source_maps(base, current)
    if set(current) != set(base) | NEW_PATHS or set(base) & NEW_PATHS:
        raise ValueError('ExactFifteenNewResearchPathsRequired')
    if WORKFLOW not in base or current[WORKFLOW].mode != base[WORKFLOW].mode:
        raise ValueError('HistoricalWorkflowModeRequired')
    for name, previous in base.items():
        if name != WORKFLOW and current[name] != previous:
            raise ValueError('InheritedSourceChangedRequiresFullQa')
    actual_new_fingerprint = new_source_fingerprint(current)
    if actual_new_fingerprint != approved_new_source_fingerprint:
        raise ValueError('NewSourcesDifferFromExplicitWorkflowReviewPin')
    policy = workflow_projection(
        base[WORKFLOW].data, current[WORKFLOW].data, approved_new_source_fingerprint)
    for name in sorted(NEW_PATHS):
        _new_text_source(name, current[name])
    rows = source_rows(current)
    return {
        'classification': 'StaticBridgeResearchProjection_NotCpuOrHistoricalQaPass',
        'passed': True, 'exactBase': BASE, 'baseSourceCount': BASE_SOURCE_COUNT,
        'unchangedBaseFiles': BASE_SOURCE_COUNT - 1, 'onlyChangedBasePath': WORKFLOW,
        'newPublicPaths': sorted(NEW_PATHS), 'sourceBindings': rows,
        'approvedNewSourceFingerprintSha256': approved_new_source_fingerprint,
        'sourceFingerprintSha256': sha256(canonical(rows)).hexdigest(),
        'workflow': policy, 'targetCpuExecutions': 0, 'firmwareReady': False,
    }


def full_qa_decision(reason):
    return {
        'classification': 'CiRouting_NotExecutionOrHistoricalQaEvidence',
        'full_qa': True, 'research_only': False, 'reason': reason,
        'historicalRequiredJobCount': 17, 'researchOnlyRequiredActualJobCount': 3,
        'historicalJobsPerformedByRouter': 0, 'targetCpuExecutions': 0,
        'firmwareReady': False,
    }


def classify_changes(base, current, approved_new_source_fingerprint):
    """Any error, old-source change or unknown path selects all inherited QA."""
    try:
        projection = research_projection(base, current, approved_new_source_fingerprint)
    except Exception:
        return full_qa_decision('OutsideClosedResearchProjection_FullHistoricalQaRequired')
    return {
        **full_qa_decision('ExactBlockedResearchProjection_ExplicitUserBoundedScope'),
        'full_qa': False, 'research_only': True,
        'sourceFingerprintSha256': projection['sourceFingerprintSha256'],
        'approvedNewSourceFingerprintSha256': projection['approvedNewSourceFingerprintSha256'],
        'unchangedBaseFiles': projection['unchangedBaseFiles'],
        'newPublicPaths': projection['newPublicPaths'],
    }
