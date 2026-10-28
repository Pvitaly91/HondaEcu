"""M2ce overlay on the exact accepted M2cd research workflow.

New source rows are frozen, independently reviewed, then explicitly pinned.
The validator never derives or writes approval for changed research source.
"""
from hashlib import sha256
import re

from native_cal27d0_frame import ci_contract as inherited

BASE = '9e136ccc53712e5b51d623af174abdd5c84763cc'
BASE_WORKFLOW_SHA = '8aa6a369daadd6eee1bf0a8920390112e7d46cda228b1f65d05c597853ef4b73'
BASE_M2CD_APPROVAL = '432fb58ed7478fd98e60a44963e97ae566b8e21fa5f70e090c1749d693621568'
WORKFLOW = '.github/workflows/build.yml'
HISTORICAL_JOBS = inherited.HISTORICAL_JOBS
historical_condition = inherited.historical_condition
PACKAGE_NAME = 'native_rooted_first_ramtest'
ROUTER_JOB = inherited.ROUTER_JOB.replace(
    'native_cal27d0_frame/ci_routing.py', PACKAGE_NAME + '/ci_routing.py').replace(
    '__M2CD_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2CE_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = inherited.STATIC_JOB.replace(
    'validate_native_cal27d0_frame.py', 'validate_native_rooted_first_ramtest.py').replace(
    'native_cal27d0_frame', PACKAGE_NAME).replace('frame-static', 'rooted-static').replace(
    'M2cd', 'M2ce').replace('m2cd-static-evidence', 'm2ce-static-evidence').replace(
    'CAL27D0 return-frame regressions', 'rooted first-RAM-test source regressions')


def _approved_fingerprint(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('ExplicitFrozenIndependentlyReviewedM2ceFingerprintRequired')
    return value


def workflow_approved_fingerprint(active):
    if type(active) is not bytes:
        raise ValueError('RawWorkflowBytesRequired')
    matches = re.findall(r'--approved-new-source-fingerprint "([0-9a-f]{64})"', active.decode('utf-8', 'strict'))
    if len(matches) != 1:
        raise ValueError('ExactlyOneLiteralReviewedM2ceFingerprintRequired')
    return _approved_fingerprint(matches[0])


def make_workflow(base, approved_new_source_fingerprint):
    approved = _approved_fingerprint(approved_new_source_fingerprint)
    if type(base) is not bytes or sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2cdWorkflowRequired')
    if inherited.workflow_approved_fingerprint(base) != BASE_M2CD_APPROVAL:
        raise ValueError('FrozenM2cdApprovalRequiredAtAcceptedBase')
    old = inherited.ROUTER_JOB.replace(
        '__M2CD_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_M2CD_APPROVAL) + inherited.STATIC_JOB
    if base.count(old.encode('utf-8')) != 1:
        raise ValueError('ExactInheritedRouterAndStaticBlocksRequired')
    new = ROUTER_JOB.replace('__M2CE_APPROVED_NEW_SOURCE_FINGERPRINT__', approved) + STATIC_JOB
    return base.replace(old.encode('utf-8'), new.encode('utf-8'), 1)


def workflow_projection(base, active, approved_new_source_fingerprint):
    if type(active) is not bytes or active != make_workflow(base, approved_new_source_fingerprint):
        raise ValueError('UnreviewedM2ceOrInheritedCiChange')
    return {'approvedNewSourceFingerprintSha256': workflow_approved_fingerprint(active),
        'acceptedM2cdBaseSha': BASE, 'acceptedM2cdApprovalUnchanged': True,
        'separateM2ceReviewedProjection': True, 'historicalJobGroupsPreserved': 9,
        'historicalRequiredJobCount': 17, 'researchOnlyRequiredActualJobCount': 3,
        'researchOnlyHistoricalJobsNotRun': 17, 'historicalDependencySuccessChecksPreserved': True,
        'historicalExecutionStepsPreservedAtAcceptedSources': True, 'desktopStepsByteExact': True,
        'routerErrorsRequireFullHistoricalQa': True, 'runtimeOrUnknownChangesRequireFullHistoricalQa': True,
        'researchOnlyLaneIsProductionQaPass': False, 'duplicateHeavyHistoricalJobsAdded': 0,
        'researchOnlyArtifactsAreCpuObservations': False,
        'workflowAndPayloadRecertificationRequiresExplicitReview': True}
