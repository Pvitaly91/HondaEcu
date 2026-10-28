"""Separate M2cc approval projection over the exact accepted M2cb workflow.

Frozen M2cb policy and pins remain unchanged. The new additions fingerprint
requires independent content review and explicit approval before it is supplied.
"""
from hashlib import sha256
import re

from native_data011f_011b_ownership import ci_contract as inherited

BASE = '8c4d573c7b745a4021d7da4c2b318ac07c800633'
BASE_WORKFLOW_SHA = '36b9da51052fdef6e563b418439a732cc3b905b886cf92bd96512232d30c62b9'
BASE_M2CB_APPROVAL = '6f73d6674d895c1158a7d6573293ccd1850f05a52f986d4ee79da7f7fd8e3cdb'
WORKFLOW = '.github/workflows/build.yml'
HISTORICAL_JOBS = inherited.HISTORICAL_JOBS
historical_condition = inherited.historical_condition
PACKAGE_NAME = 'native_data0217_011f_bridge'

ROUTER_JOB = inherited.ROUTER_JOB.replace(
    'native_data011f_011b_ownership/ci_routing.py', PACKAGE_NAME + '/ci_routing.py').replace(
    '__M2CB_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2CC_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = inherited.STATIC_JOB.replace(
    'validate_native_data011f_011b_ownership.py', 'validate_native_data0217_011f_bridge.py').replace(
    'native_data011f_011b_ownership', PACKAGE_NAME).replace('ownership-static', 'bridge-static').replace(
    'M2cb', 'M2cc').replace('m2cb-static-evidence', 'm2cc-static-evidence').replace(
    'symbolic ownership regressions', 'same-machine bridge regressions')


def _approved_fingerprint(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('ExplicitReviewedM2ccNewSourceFingerprintRequired')
    return value


def workflow_approved_fingerprint(active):
    """Read one explicit literal; never derive a replacement from changed code."""
    if type(active) is not bytes:
        raise ValueError('RawWorkflowBytesRequired')
    matches = re.findall(r'--approved-new-source-fingerprint "([0-9a-f]{64})"',
        active.decode('utf-8', 'strict'))
    if len(matches) != 1:
        raise ValueError('ExactlyOneLiteralReviewedM2ccFingerprintRequired')
    return _approved_fingerprint(matches[0])


def make_workflow(base, approved_new_source_fingerprint):
    approved = _approved_fingerprint(approved_new_source_fingerprint)
    if type(base) is not bytes or sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2cbWorkflowRequired')
    if inherited.workflow_approved_fingerprint(base) != BASE_M2CB_APPROVAL:
        raise ValueError('FrozenM2cbApprovalRequiredAtAcceptedBase')
    old = inherited.ROUTER_JOB.replace(
        '__M2CB_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_M2CB_APPROVAL) + inherited.STATIC_JOB
    if base.count(old.encode('utf-8')) != 1:
        raise ValueError('ExactInheritedResearchRouterAndStaticBlocksRequired')
    new = ROUTER_JOB.replace('__M2CC_APPROVED_NEW_SOURCE_FINGERPRINT__', approved) + STATIC_JOB
    return base.replace(old.encode('utf-8'), new.encode('utf-8'), 1)


def workflow_projection(base, active, approved_new_source_fingerprint):
    if type(active) is not bytes or active != make_workflow(base, approved_new_source_fingerprint):
        raise ValueError('UnreviewedM2ccOrInheritedCiChange')
    return {
        'approvedNewSourceFingerprintSha256': workflow_approved_fingerprint(active),
        'acceptedM2cbBaseSha': BASE, 'acceptedM2cbApprovalUnchanged': True,
        'separateM2ccReviewedProjection': True,
        'historicalJobGroupsPreserved': 9, 'historicalRequiredJobCount': 17,
        'researchOnlyRequiredActualJobCount': 3, 'researchOnlyHistoricalJobsNotRun': 17,
        'historicalDependencySuccessChecksPreserved': True,
        'historicalExecutionStepsPreservedAtAcceptedSources': True,
        'desktopStepsByteExact': True,
        'routerErrorsRequireFullHistoricalQa': True,
        'runtimeOrUnknownChangesRequireFullHistoricalQa': True,
        'researchOnlyLaneIsProductionQaPass': False,
        'duplicateHeavyHistoricalJobsAdded': 0,
        'researchOnlyArtifactsAreCpuObservations': False,
        'workflowAndPayloadRecertificationRequiresExplicitReview': True,
    }
