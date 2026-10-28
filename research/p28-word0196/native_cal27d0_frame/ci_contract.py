"""M2cd overlay on the exact accepted M2cc research workflow.

New source rows are frozen, independently reviewed, then explicitly pinned.
The validator never derives or writes approval for changed research source.
"""
from hashlib import sha256
import re

from native_data0217_011f_bridge import ci_contract as inherited

BASE = 'd461861c8a8714d34d66d5933646e4158b6adbc4'
BASE_WORKFLOW_SHA = '6ccb4ce949ee27ddbcac2805be872553d43432f0c2fec036d3b4251ce3ca3745'
BASE_M2CC_APPROVAL = '480c4f3fcc79251d8e98f6c95af91dffc9259b8fff6d4c7cb1f57b0c256d4d20'
WORKFLOW = '.github/workflows/build.yml'
HISTORICAL_JOBS = inherited.HISTORICAL_JOBS
historical_condition = inherited.historical_condition
PACKAGE_NAME = 'native_cal27d0_frame'
ROUTER_JOB = inherited.ROUTER_JOB.replace(
    'native_data0217_011f_bridge/ci_routing.py', PACKAGE_NAME + '/ci_routing.py').replace(
    '__M2CC_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2CD_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = inherited.STATIC_JOB.replace(
    'validate_native_data0217_011f_bridge.py', 'validate_native_cal27d0_frame.py').replace(
    'native_data0217_011f_bridge', PACKAGE_NAME).replace('bridge-static', 'frame-static').replace(
    'M2cc', 'M2cd').replace('m2cc-static-evidence', 'm2cd-static-evidence').replace(
    'same-machine bridge regressions', 'CAL27D0 return-frame regressions')


def _approved_fingerprint(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('ExplicitFrozenIndependentlyReviewedM2cdFingerprintRequired')
    return value


def workflow_approved_fingerprint(active):
    if type(active) is not bytes:
        raise ValueError('RawWorkflowBytesRequired')
    matches = re.findall(r'--approved-new-source-fingerprint "([0-9a-f]{64})"', active.decode('utf-8', 'strict'))
    if len(matches) != 1:
        raise ValueError('ExactlyOneLiteralReviewedM2cdFingerprintRequired')
    return _approved_fingerprint(matches[0])


def make_workflow(base, approved_new_source_fingerprint):
    approved = _approved_fingerprint(approved_new_source_fingerprint)
    if type(base) is not bytes or sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2ccWorkflowRequired')
    if inherited.workflow_approved_fingerprint(base) != BASE_M2CC_APPROVAL:
        raise ValueError('FrozenM2ccApprovalRequiredAtAcceptedBase')
    old = inherited.ROUTER_JOB.replace(
        '__M2CC_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_M2CC_APPROVAL) + inherited.STATIC_JOB
    if base.count(old.encode('utf-8')) != 1:
        raise ValueError('ExactInheritedRouterAndStaticBlocksRequired')
    new = ROUTER_JOB.replace('__M2CD_APPROVED_NEW_SOURCE_FINGERPRINT__', approved) + STATIC_JOB
    return base.replace(old.encode('utf-8'), new.encode('utf-8'), 1)


def workflow_projection(base, active, approved_new_source_fingerprint):
    if type(active) is not bytes or active != make_workflow(base, approved_new_source_fingerprint):
        raise ValueError('UnreviewedM2cdOrInheritedCiChange')
    return {'approvedNewSourceFingerprintSha256': workflow_approved_fingerprint(active),
        'acceptedM2ccBaseSha': BASE, 'acceptedM2ccApprovalUnchanged': True,
        'separateM2cdReviewedProjection': True, 'historicalJobGroupsPreserved': 9,
        'historicalRequiredJobCount': 17, 'researchOnlyRequiredActualJobCount': 3,
        'researchOnlyHistoricalJobsNotRun': 17, 'historicalDependencySuccessChecksPreserved': True,
        'historicalExecutionStepsPreservedAtAcceptedSources': True, 'desktopStepsByteExact': True,
        'routerErrorsRequireFullHistoricalQa': True, 'runtimeOrUnknownChangesRequireFullHistoricalQa': True,
        'researchOnlyLaneIsProductionQaPass': False, 'duplicateHeavyHistoricalJobsAdded': 0,
        'researchOnlyArtifactsAreCpuObservations': False,
        'workflowAndPayloadRecertificationRequiresExplicitReview': True}
