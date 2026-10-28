"""Exact additive CI routing; inherited execution gates remain available."""
from hashlib import sha256
import re

BASE = 'f77d2cc1468fe128ba4ad393c3e0a1a5dab423fc'
BASE_WORKFLOW_SHA = '4438339592d0d6a222de40ef58bdd7ef3f0982938d1240a1c7914b300f0a5f29'
WORKFLOW = '.github/workflows/build.yml'
HISTORICAL_JOBS = (
    ('historical-pinned-qa', None),
    ('build-and-test', 'historical-pinned-qa'),
    ('native-entry-continuity', 'build-and-test'),
    ('native-p2-handoff', 'native-entry-continuity'),
    ('native-post-p2-control', 'native-p2-handoff'),
    ('native-below-second-p2', 'native-post-p2-control'),
    ('native-cal-rt-continuity', 'native-below-second-p2'),
    ('native-post-return-selector', 'native-cal-rt-continuity'),
    ('desktop-windows', None),
)

ROUTER_JOB = """
  ci-routing:
    runs-on: ubuntu-latest
    outputs:
      full_qa: ${{ steps.classify.outputs.full_qa }}
      research_only: ${{ steps.classify.outputs.research_only }}
    env:
      PYTHONDONTWRITEBYTECODE: "1"
    steps:
      - name: Checkout exact active source for bounded routing
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Classify exact source changes with full-QA fallback
        id: classify
        shell: bash
        run: |
          python -B research/p28-word0196/native_branch064c/ci_routing.py --expected-head "${{ github.sha }}" --approved-new-source-fingerprint "__M2CA_APPROVED_NEW_SOURCE_FINGERPRINT__" --github-output "$GITHUB_OUTPUT"

"""
STATIC_JOB = """
  branch064c-static:
    needs: ci-routing
    if: ${{ always() && needs.ci-routing.result == 'success' && needs.ci-routing.outputs.research_only == 'true' && needs.ci-routing.outputs.full_qa == 'false' }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    env:
      PYTHONDONTWRITEBYTECODE: "1"
      GIT_CONFIG_COUNT: "1"
      GIT_CONFIG_KEY_0: core.autocrlf
      GIT_CONFIG_VALUE_0: "false"
    steps:
      - name: Checkout exact active M2ca static research source
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Set up Python for static invented calculations only
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: M2ca exact source equality and closed workflow projection
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_branch064c/source_guard.py --expected-head "${{ github.sha }}"
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2ca source provenance and invented static gate regressions without CPU execution
        shell: pwsh
        run: |
          python -B -m unittest discover -s research/p28-word0196/native_branch064c -t research/p28-word0196 -p '*_tests.py'
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2ca invented static canonical calculations not CPU observations
        shell: pwsh
        run: |
          python -B research/p28-word0196/validate_native_branch064c.py --output .tmp/m2ca-static-evidence --expected-head "${{ github.sha }}"
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Verify closed invented static artifact membership
        shell: pwsh
        run: |
          $taskRequired = @('static-canonical.jsonl.gz', 'static-summary.json', 'sourcejoin.json')
          $taskActual = @(Get-ChildItem -LiteralPath '.tmp/m2ca-static-evidence' -Force)
          if ($taskActual.Count -ne 3) { throw 'Unexpected M2ca static artifact membership.' }
          foreach ($taskName in $taskRequired) {
            if (-not (Test-Path -LiteralPath (Join-Path '.tmp/m2ca-static-evidence' $taskName) -PathType Leaf)) { throw 'Missing M2ca static artifact member.' }
          }

      - name: Preserve invented static calculations only not CPU or private ROM evidence
        uses: actions/upload-artifact@v4
        with:
          name: M2ca-invented-static-${{ matrix.os }}
          path: |
            .tmp/m2ca-static-evidence/static-canonical.jsonl.gz
            .tmp/m2ca-static-evidence/static-summary.json
            .tmp/m2ca-static-evidence/sourcejoin.json
          if-no-files-found: error
          retention-days: 14

"""


def historical_condition(predecessor):
    """Router failure/missing output selects full QA, never implicit skip."""
    routing = ("(needs.ci-routing.result != 'success' || "
               "needs.ci-routing.outputs.full_qa != 'false')")
    prior = '' if predecessor is None else " && needs." + predecessor + ".result == 'success'"
    return "    if: ${{ always() && " + routing + prior + " }}\n"


def _routed_historical(base_text):
    result = base_text
    for job, predecessor in HISTORICAL_JOBS:
        marker = '\n  ' + job + ':\n'
        before = marker if predecessor is None else marker + '    needs: ' + predecessor + '\n'
        if result.count(before) != 1:
            raise ValueError('ExactInheritedJobAndDependencyRequired')
        dependencies = 'ci-routing' if predecessor is None else '[ci-routing, ' + predecessor + ']'
        after = marker + '    needs: ' + dependencies + '\n' + historical_condition(predecessor)
        result = result.replace(before, after, 1)
    original = ('      - name: Checkout exact active M2bz source\n'
                '        uses: actions/checkout@v4\n'
                '        with:\n'
                '          fetch-depth: 0\n')
    pinned = ('      - name: Checkout pinned accepted M2bz source\n'
              '        uses: actions/checkout@v4\n'
              '        with:\n'
              '          ref: ' + BASE + '\n'
              '          fetch-depth: 0\n')
    if result.count(original) != 1:
        raise ValueError('ExactInheritedM2bzCheckoutRequired')
    result = result.replace(original, pinned, 1)
    guard = ('python -B research/p28-word0196/native_post_return_selector/'
             'source_guard.py --expected-head "${{ github.sha }}"')
    if result.count(guard) != 1:
        raise ValueError('ExactInheritedM2bzGuardRequired')
    return result.replace(guard, guard.replace('${{ github.sha }}', BASE), 1).replace(
        'Verify active M2bz closed source and seventeen-job CI projection',
        'Verify pinned M2bz source and its unchanged seventeen-job CI projection', 1)


def _approved_fingerprint(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('ExplicitReviewedNewSourceFingerprintRequired')
    return value


def workflow_approved_fingerprint(active):
    """Read the one externally reviewed pin; never derive it from new files."""
    if type(active) is not bytes:
        raise ValueError('RawWorkflowBytesRequired')
    matches = re.findall(
        r'--approved-new-source-fingerprint "([0-9a-f]{64})"',
        active.decode('utf-8', 'strict'))
    if len(matches) != 1:
        raise ValueError('ExactlyOneLiteralReviewedNewSourceFingerprintRequired')
    return _approved_fingerprint(matches[0])


def make_workflow(base, approved_new_source_fingerprint):
    approved = _approved_fingerprint(approved_new_source_fingerprint)
    if type(base) is not bytes or sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2bzWorkflowRequired')
    text = _routed_historical(base.decode('utf-8', 'strict'))
    if text.count('\njobs:\n') != 1:
        raise ValueError('ExactWorkflowJobsBoundaryRequired')
    router = ROUTER_JOB.replace('__M2CA_APPROVED_NEW_SOURCE_FINGERPRINT__', approved)
    return text.replace('\njobs:\n', '\njobs:\n' + router + STATIC_JOB, 1).encode('utf-8')


def workflow_projection(base, active, approved_new_source_fingerprint):
    if type(active) is not bytes or active != make_workflow(base, approved_new_source_fingerprint):
        raise ValueError('UnreviewedHistoricalOrStaticCiChange')
    return {
        'approvedNewSourceFingerprintSha256': workflow_approved_fingerprint(active),
        'historicalJobGroupsPreserved': 9,
        'historicalRequiredJobCount': 17,
        'researchOnlyRequiredActualJobCount': 3,
        'researchOnlyHistoricalJobsNotRun': 17,
        'historicalDependencySuccessChecksPreserved': True,
        'historicalExecutionStepsPreservedAtAcceptedSources': True,
        'desktopStepsByteExact': True,
        'm2bzHistoricalSourceSha': BASE,
        'routerErrorsRequireFullHistoricalQa': True,
        'runtimeOrUnknownChangesRequireFullHistoricalQa': True,
        'researchOnlyLaneIsProductionQaPass': False,
        'duplicateHeavyHistoricalJobsAdded': 0,
        'researchOnlyArtifactsAreCpuObservations': False,
        'workflowAndPayloadRecertificationRequiresExplicitReview': True,
    }
