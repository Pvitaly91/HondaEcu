"""Closed seventeen-job projection; prior fifteen jobs retain pinned coverage."""
from hashlib import sha256
from native_cal_rt_continuity.ci_contract import M2BY_JOB
BASE = '82c34c0465a5d92ce5cc30f2daf47f24174a10d5'
BASE_WORKFLOW_SHA = 'c0633c0e032048e0b9f276a4a253e955d72263f380c042bf91e760b8299a8aea'
DESKTOP = '\n  desktop-windows:\n'
PINNED_M2BY_JOB = M2BY_JOB.replace('Checkout exact active M2by source','Checkout pinned accepted M2by source').replace(
    '          fetch-depth: 0\n','          ref: '+BASE+'\n          fetch-depth: 0\n',1).replace(
    '--expected-head "${{ github.sha }}"','--expected-head "'+BASE+'"').replace(
    'Verify active M2by closed source and fifteen-job CI projection',
    'Verify pinned M2by source and its unchanged fifteen-job CI projection')
M2BZ_JOB = M2BY_JOB.replace('M2by','M2bz').replace('m2by','m2bz').replace(
    'native-cal-rt-continuity:','native-post-return-selector:').replace('needs: native-below-second-p2','needs: native-cal-rt-continuity').replace(
    'native_cal_rt_continuity','native_post_return_selector').replace('fifteen-job','seventeen-job').replace(
    'p28-word0196-cal-rt-continuity','p28-word0196-post-return-selector-continuity').replace(
    'm2bz-cal-rt-continuity','m2bz-post-return-selector').replace(
    'CAL-body-RT frame continuity execution','CAL-body-RT plus eight post-return selector instructions execution')

def make_workflow(base):
    if sha256(base).hexdigest()!=BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2byWorkflowRequired')
    text=base.decode('utf-8','strict')
    if text.count(M2BY_JOB)!=1 or text.count(DESKTOP)!=1:
        raise ValueError('ClosedM2byAndDesktopBoundariesRequired')
    return text.replace(M2BY_JOB,PINNED_M2BY_JOB,1).replace(DESKTOP,M2BZ_JOB+DESKTOP,1).encode('utf-8')

def workflow_projection(base,active):
    if active!=make_workflow(base):
        raise ValueError('UnreviewedHistoricalDesktopM2byOrM2bzCiChange')
    return {'historicalJobsPreservedAtPinnedIdentities':True,'desktopJobByteExact':True,
        'm2byCommandsAndCoveragePreservedAtExactAcceptedSource':True,'m2byHistoricalSourceSha':BASE,
        'newCurrentDefaultOffAndAllOptInTestsRequired':True,'requiredActualJobs':17,
        'requiredTechnicalStepsSkippedOrDisabled':False,'duplicateHeavyHistoricalJobsAdded':0}
