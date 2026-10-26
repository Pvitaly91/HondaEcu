"""Closed fifteen-job M2by projection; thirteen prior jobs retain pinned coverage."""
from hashlib import sha256
from native_below_second_p2.ci_contract import M2BX_JOB
BASE = '832b7c382076a8a441e48d2d19917aa43118eb37'
BASE_WORKFLOW_SHA = '3e90751ae6b36656d88a1ed38fb6ecbca86c8dabd84862272d553b5cdd76676c'
DESKTOP = '\n  desktop-windows:\n'
PINNED_M2BX_JOB = M2BX_JOB.replace('Checkout exact active M2bx source','Checkout pinned accepted M2bx source').replace(
    '          fetch-depth: 0\n','          ref: '+BASE+'\n          fetch-depth: 0\n',1).replace(
    '--expected-head "${{ github.sha }}"','--expected-head "'+BASE+'"').replace(
    'Verify active M2bx closed source and thirteen-job CI projection',
    'Verify pinned M2bx source and its unchanged thirteen-job CI projection')
M2BY_JOB = M2BX_JOB.replace('M2bx','M2by').replace('m2bx','m2by').replace(
    'native-below-second-p2:','native-cal-rt-continuity:').replace('needs: native-post-p2-control','needs: native-below-second-p2').replace(
    'native_below_second_p2','native_cal_rt_continuity').replace('thirteen-job','fifteen-job').replace(
    'p28-word0196-below-second-p2-continuity','p28-word0196-cal-rt-continuity').replace(
    'm2by-below-second-p2','m2by-cal-rt-continuity').replace(
    'two-P2 and Below continuation execution','CAL-body-RT frame continuity execution')

def make_workflow(base):
    if sha256(base).hexdigest()!=BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2bxWorkflowRequired')
    text=base.decode('utf-8','strict')
    if text.count(M2BX_JOB)!=1 or text.count(DESKTOP)!=1:
        raise ValueError('ClosedM2bxAndDesktopBoundariesRequired')
    return text.replace(M2BX_JOB,PINNED_M2BX_JOB,1).replace(DESKTOP,M2BY_JOB+DESKTOP,1).encode('utf-8')

def workflow_projection(base,active):
    if active!=make_workflow(base):
        raise ValueError('UnreviewedHistoricalDesktopM2bxOrM2byCiChange')
    return {'historicalJobsPreservedAtPinnedIdentities':True,'desktopJobByteExact':True,
        'm2bxCommandsAndCoveragePreservedAtExactAcceptedSource':True,'m2bxHistoricalSourceSha':BASE,
        'newCurrentDefaultOffAndAllOptInTestsRequired':True,'requiredActualJobs':15,
        'requiredTechnicalStepsSkippedOrDisabled':False,'duplicateHeavyHistoricalJobsAdded':0}
