"""M2cg overlay on the exact accepted M2ce research workflow.

New source rows are frozen, independently reviewed, then explicitly pinned.
The validator never derives or writes approval for changed research source.
"""
from hashlib import sha256
import re

from native_rooted_first_ramtest import ci_contract as inherited

BASE = 'bb781647d553ee321ae9ac75732e06736fb01fbb'
BASE_WORKFLOW_SHA = 'be10f5dd5631d8b5709e50094c5193f7e3e1939591970461e68fd1d795a8cd2b'
BASE_M2CE_APPROVAL = 'e475523217917bb2a9fd69fb135d65419502f60775280acf82840f4146797397'
WORKFLOW = '.github/workflows/build.yml'
HISTORICAL_JOBS = inherited.HISTORICAL_JOBS
historical_condition = inherited.historical_condition
PACKAGE_NAME = 'native_data011b7_zero_source'
ROUTER_JOB = inherited.ROUTER_JOB.replace(
    'native_rooted_first_ramtest/ci_routing.py', PACKAGE_NAME + '/ci_routing.py').replace(
    '__M2CE_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2CG_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = inherited.STATIC_JOB.replace(
    'validate_native_rooted_first_ramtest.py', 'validate_native_data011b7_zero.py').replace(
    'native_rooted_first_ramtest', PACKAGE_NAME).replace('rooted-static', 'zero-source-static').replace(
    'M2ce', 'M2cg').replace('m2ce-static-evidence', 'm2cg-static-evidence').replace(
    'rooted first-RAM-test source regressions', 'DATA011B zero-producer source regressions')


def _approved_fingerprint(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('ExplicitFrozenIndependentlyReviewedM2cgFingerprintRequired')
    return value


def workflow_approved_fingerprint(active):
    if type(active) is not bytes:
        raise ValueError('RawWorkflowBytesRequired')
    matches = re.findall(r'--approved-new-source-fingerprint "([0-9a-f]{64})"', active.decode('utf-8', 'strict'))
    if len(matches) != 1:
        raise ValueError('ExactlyOneLiteralReviewedM2cgFingerprintRequired')
    return _approved_fingerprint(matches[0])


def make_workflow(base, approved_new_source_fingerprint):
    approved = _approved_fingerprint(approved_new_source_fingerprint)
    if type(base) is not bytes or sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2ceWorkflowRequired')
    if inherited.workflow_approved_fingerprint(base) != BASE_M2CE_APPROVAL:
        raise ValueError('FrozenM2ceApprovalRequiredAtAcceptedBase')
    old = inherited.ROUTER_JOB.replace(
        '__M2CE_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_M2CE_APPROVAL) + inherited.STATIC_JOB
    if base.count(old.encode('utf-8')) != 1:
        raise ValueError('ExactInheritedRouterAndStaticBlocksRequired')
    new = ROUTER_JOB.replace('__M2CG_APPROVED_NEW_SOURCE_FINGERPRINT__', approved) + STATIC_JOB
    return base.replace(old.encode('utf-8'), new.encode('utf-8'), 1)


def workflow_projection(base, active, approved_new_source_fingerprint):
    if type(active) is not bytes or active != make_workflow(base, approved_new_source_fingerprint):
        raise ValueError('UnreviewedM2cgOrInheritedCiChange')
    return {'approvedNewSourceFingerprintSha256': workflow_approved_fingerprint(active),
        'acceptedM2ceBaseSha': BASE, 'acceptedM2ceApprovalUnchanged': True,
        'separateM2cgReviewedProjection': True, 'historicalJobGroupsPreserved': 9,
        'historicalRequiredJobCount': 17, 'researchOnlyRequiredActualJobCount': 3,
        'researchOnlyHistoricalJobsNotRun': 17, 'historicalDependencySuccessChecksPreserved': True,
        'historicalExecutionStepsPreservedAtAcceptedSources': True, 'desktopStepsByteExact': True,
        'routerErrorsRequireFullHistoricalQa': True, 'runtimeOrUnknownChangesRequireFullHistoricalQa': True,
        'researchOnlyLaneIsProductionQaPass': False, 'duplicateHeavyHistoricalJobsAdded': 0,
        'researchOnlyArtifactsAreCpuObservations': False,
        'workflowAndPayloadRecertificationRequiresExplicitReview': True}
