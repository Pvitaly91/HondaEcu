"""Separate M2cb research projection over the exact accepted M2ca workflow.

Frozen M2ca approval/policy remain untouched. A new additions-only approval is
reviewed independently and supplied explicitly; it is never inferred here.
"""
from hashlib import sha256
import re

from native_branch064c import ci_contract as inherited

BASE = '2e327d2ade8d419180f1088cb277a306accbab4f'
BASE_WORKFLOW_SHA = '3d9a88ae2f3e30f9765f963754d418ca12334d93b8881412f067de7c5f558fa1'
BASE_M2CA_APPROVAL = 'f6d6ca2c1d91a840c68d9cda001ebb7944bf14bcc4ebb68824e6bc7a3adf2ab0'
WORKFLOW = '.github/workflows/build.yml'
HISTORICAL_JOBS = inherited.HISTORICAL_JOBS
historical_condition = inherited.historical_condition
PACKAGE_NAME = 'native_data011f_011b_ownership'

ROUTER_JOB = inherited.ROUTER_JOB.replace(
    'native_branch064c/ci_routing.py', PACKAGE_NAME + '/ci_routing.py').replace(
    '__M2CA_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2CB_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = inherited.STATIC_JOB.replace(
    'validate_native_branch064c.py', 'validate_native_data011f_011b_ownership.py').replace(
    'native_branch064c', PACKAGE_NAME).replace('branch064c-static', 'ownership-static').replace(
    'M2ca', 'M2cb').replace('m2ca-static-evidence', 'm2cb-static-evidence').replace(
    'static gate regressions', 'symbolic ownership regressions')


def _approved_fingerprint(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('ExplicitReviewedM2cbNewSourceFingerprintRequired')
    return value


def workflow_approved_fingerprint(active):
    """One literal approval in the reviewed workflow; not a self-derived value."""
    if type(active) is not bytes:
        raise ValueError('RawWorkflowBytesRequired')
    matches = re.findall(r'--approved-new-source-fingerprint "([0-9a-f]{64})"',
                         active.decode('utf-8', 'strict'))
    if len(matches) != 1:
        raise ValueError('ExactlyOneLiteralReviewedM2cbFingerprintRequired')
    return _approved_fingerprint(matches[0])


def make_workflow(base, approved_new_source_fingerprint):
    approved = _approved_fingerprint(approved_new_source_fingerprint)
    if type(base) is not bytes or sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2caWorkflowRequired')
    if inherited.workflow_approved_fingerprint(base) != BASE_M2CA_APPROVAL:
        raise ValueError('FrozenM2caApprovalRequiredAtAcceptedBase')
    old = inherited.ROUTER_JOB.replace(
        '__M2CA_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_M2CA_APPROVAL) + inherited.STATIC_JOB
    if base.count(old.encode('utf-8')) != 1:
        raise ValueError('ExactInheritedResearchRouterAndStaticBlocksRequired')
    new = ROUTER_JOB.replace('__M2CB_APPROVED_NEW_SOURCE_FINGERPRINT__', approved) + STATIC_JOB
    return base.replace(old.encode('utf-8'), new.encode('utf-8'), 1)


def workflow_projection(base, active, approved_new_source_fingerprint):
    if type(active) is not bytes or active != make_workflow(base, approved_new_source_fingerprint):
        raise ValueError('UnreviewedM2cbOrInheritedCiChange')
    return {
        'approvedNewSourceFingerprintSha256': workflow_approved_fingerprint(active),
        'acceptedM2caBaseSha': BASE, 'acceptedM2caApprovalUnchanged': True,
        'separateM2cbReviewedProjection': True,
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
