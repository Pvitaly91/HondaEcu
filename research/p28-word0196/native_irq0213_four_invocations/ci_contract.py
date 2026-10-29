"""Separate reviewed M2ch overlay; inherited M2cg approval remains frozen."""
from hashlib import sha256
import re

from native_data011b7_zero_source import ci_contract as inherited

BASE = '57f153815d61a44d6c3ce9efdc14c5937e5c4c31'
BASE_WORKFLOW_SHA = '35a6ec7ef5db145712e34650ddc1040f63da68091b172dae1d7bac2c4ef0efaa'
BASE_M2CG_APPROVAL = 'af83421f34362637e8b0af910e4f98989556763b6248b9a1f6a27443d7120df8'
WORKFLOW = '.github/workflows/build.yml'
HISTORICAL_JOBS = inherited.HISTORICAL_JOBS
historical_condition = inherited.historical_condition
PACKAGE_NAME = 'native_irq0213_four_invocations'
ROUTER_JOB = inherited.ROUTER_JOB.replace(
    'native_data011b7_zero_source/ci_routing.py', PACKAGE_NAME + '/ci_routing.py').replace(
    '__M2CG_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2CH_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = inherited.STATIC_JOB.replace(
    'validate_native_data011b7_zero.py', 'validate_native_irq0213_four_invocations.py').replace(
    'native_data011b7_zero_source', PACKAGE_NAME).replace('zero-source-static', 'irq-frame-static').replace(
    'M2cg', 'M2ch').replace('m2cg-static-evidence', 'm2ch-static-evidence').replace(
    'DATA011B zero-producer source regressions', 'IRQ0213 frame and four-invocation source regressions')


def _approved_fingerprint(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('ExplicitFrozenIndependentlyReviewedM2chFingerprintRequired')
    return value


def workflow_approved_fingerprint(active):
    if type(active) is not bytes:
        raise ValueError('RawWorkflowBytesRequired')
    matches = re.findall(r'--approved-new-source-fingerprint "([0-9a-f]{64})"', active.decode('utf-8', 'strict'))
    if len(matches) != 1:
        raise ValueError('ExactlyOneLiteralReviewedM2chFingerprintRequired')
    return _approved_fingerprint(matches[0])


def make_workflow(base, approved_new_source_fingerprint):
    approved = _approved_fingerprint(approved_new_source_fingerprint)
    if type(base) is not bytes or sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2cgWorkflowRequired')
    if inherited.workflow_approved_fingerprint(base) != BASE_M2CG_APPROVAL:
        raise ValueError('FrozenM2cgApprovalRequiredAtAcceptedBase')
    old = inherited.ROUTER_JOB.replace(
        '__M2CG_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_M2CG_APPROVAL) + inherited.STATIC_JOB
    if base.count(old.encode('utf-8')) != 1:
        raise ValueError('ExactInheritedRouterAndStaticBlocksRequired')
    new = ROUTER_JOB.replace('__M2CH_APPROVED_NEW_SOURCE_FINGERPRINT__', approved) + STATIC_JOB
    return base.replace(old.encode('utf-8'), new.encode('utf-8'), 1)


def workflow_projection(base, active, approved_new_source_fingerprint):
    if type(active) is not bytes or active != make_workflow(base, approved_new_source_fingerprint):
        raise ValueError('UnreviewedM2chOrInheritedCiChange')
    return {'approvedNewSourceFingerprintSha256': workflow_approved_fingerprint(active),
        'acceptedM2cgBaseSha': BASE, 'acceptedM2cgApprovalUnchanged': True,
        'separateM2chReviewedProjection': True, 'historicalJobGroupsPreserved': 9,
        'historicalRequiredJobCount': 17, 'researchOnlyRequiredActualJobCount': 3,
        'researchOnlyHistoricalJobsNotRun': 17, 'historicalDependencySuccessChecksPreserved': True,
        'historicalExecutionStepsPreservedAtAcceptedSources': True, 'desktopStepsByteExact': True,
        'routerErrorsRequireFullHistoricalQa': True, 'runtimeOrUnknownChangesRequireFullHistoricalQa': True,
        'researchOnlyLaneIsProductionQaPass': False, 'duplicateHeavyHistoricalJobsAdded': 0,
        'researchOnlyArtifactsAreCpuObservations': False,
        'workflowAndPayloadRecertificationRequiresExplicitReview': True}
