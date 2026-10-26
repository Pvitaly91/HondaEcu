"""Closed thirteen-job M2bx projection; all prior sources/coverage retained."""
from hashlib import sha256
from native_post_p2_control.ci_contract import M2BW_JOB
BASE = '4d99ebcf02016df3dfa0a6d035bb01def4b170cd'
BASE_WORKFLOW_SHA = '84fe8eaaba50268f0afb2acea7da829d7cab7f95c745cc466daae3104a6d9bf6'
DESKTOP = '\n  desktop-windows:\n'
PINNED_M2BW_JOB = M2BW_JOB.replace('Checkout exact active M2bw source', 'Checkout pinned accepted M2bw source').replace(
    '          fetch-depth: 0\n', '          ref: ' + BASE + '\n          fetch-depth: 0\n', 1).replace(
    '--expected-head "${{ github.sha }}"', '--expected-head "' + BASE + '"').replace(
    'Verify active M2bw closed source and eleven-job CI projection',
    'Verify pinned M2bw source and its unchanged eleven-job CI projection')
M2BX_JOB = M2BW_JOB.replace('M2bw', 'M2bx').replace('m2bw', 'm2bx').replace(
    'native-post-p2-control:', 'native-below-second-p2:').replace('needs: native-p2-handoff', 'needs: native-post-p2-control').replace(
    'native_post_p2_control', 'native_below_second_p2').replace('eleven-job', 'thirteen-job').replace(
    'p28-word0196-post-p2-control', 'p28-word0196-below-second-p2-continuity').replace(
    'm2bx-post-p2-control', 'm2bx-below-second-p2').replace(
    'one-P2 and post-P2 control execution', 'two-P2 and Below continuation execution')
def make_workflow(base):
    if sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2bwWorkflowRequired')
    text = base.decode('utf-8', 'strict')
    if text.count(M2BW_JOB) != 1 or text.count(DESKTOP) != 1:
        raise ValueError('ClosedM2bwAndDesktopBoundariesRequired')
    return text.replace(M2BW_JOB, PINNED_M2BW_JOB, 1).replace(DESKTOP, M2BX_JOB + DESKTOP, 1).encode('utf-8')
def workflow_projection(base, active):
    if active != make_workflow(base):
        raise ValueError('UnreviewedHistoricalDesktopM2bwOrM2bxCiChange')
    return {'historicalJobsPreservedAtPinnedIdentities': True, 'desktopJobByteExact': True,
        'm2bwCommandsAndCoveragePreservedAtExactAcceptedSource': True, 'm2bwHistoricalSourceSha': BASE,
        'newCurrentDefaultOffAndAllOptInTestsRequired': True, 'requiredActualJobs': 13,
        'requiredTechnicalStepsSkippedOrDisabled': False, 'duplicateHeavyHistoricalJobsAdded': 0}
