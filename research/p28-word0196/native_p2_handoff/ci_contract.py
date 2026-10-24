"""Closed M2bv CI projection: preserve seven historical jobs, add two current jobs."""
from hashlib import sha256
from native_entry_continuity.ci_contract import M2BU_JOB

BASE = 'df55bc5d86f85906813a8241608dac542ab4c302'
BASE_WORKFLOW_SHA = '5158cb709a6eff2c4cd1cff3bada183dd245151c5b031a3aa45eeefa06f64d07'
DESKTOP = '\n  desktop-windows:\n'
PINNED_M2BU_JOB = M2BU_JOB.replace(
    'Checkout exact active M2bu source', 'Checkout pinned accepted M2bu source').replace(
    '          fetch-depth: 0\n', '          ref: ' + BASE + '\n          fetch-depth: 0\n', 1).replace(
    '--expected-head "${{ github.sha }}"', '--expected-head "' + BASE + '"').replace(
    'Verify active M2bu closed source and seven-job CI projection',
    'Verify pinned M2bu source and its unchanged seven-job CI projection')

M2BV_JOB = r'''
  native-p2-handoff:
    needs: native-entry-continuity
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    env:
      CARGO_BUILD_JOBS: "1"
      PYTHONDONTWRITEBYTECODE: "1"
      GIT_CONFIG_COUNT: "1"
      GIT_CONFIG_KEY_0: core.autocrlf
      GIT_CONFIG_VALUE_0: "false"
      CARGO_TARGET_DIR: ${{ github.workspace }}/.tmp/m2bv-owned/cargo-target

    steps:
      - name: Checkout exact active M2bv source
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Set up pinned M2bv Rust toolchain
        run: rustup toolchain install 1.85.1 --profile minimal --component rustfmt

      - name: Verify active M2bv closed source and nine-job CI projection
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_p2_handoff/source_guard.py --expected-head "${{ github.sha }}"
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bv independent P2 oracle ownership admission and resume regressions
        shell: pwsh
        run: |
          python -B -m unittest discover -s research/p28-word0196/native_p2_handoff -t research/p28-word0196 -p '*_tests.py'
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Fetch exact locked M2bv dependencies
        shell: pwsh
        run: |
          cargo +1.85.1 fetch --locked --manifest-path rust/p28-slice-runner/Cargo.toml
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bv current-source default-off and complete old-plus-P2 Rust regressions
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_p2_handoff/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bv-owned/cargo-target --no-default-features
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/native_p2_handoff/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bv-owned/cargo-target --no-default-features --features p28-word0196-p2-handoff
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 fmt --check --manifest-path rust/p28-slice-runner/Cargo.toml
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Build required-feature M2bv P2 runner in owned target
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_p2_handoff/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 build --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bv-owned/cargo-target --no-default-features --features p28-word0196-p2-handoff --bin m2bv-p2-handoff
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bv actual public continuous predecessor algorithm and one-P2 execution
        shell: pwsh
        run: |
          $taskRunner = '.tmp/m2bv-owned/cargo-target/release/m2bv-p2-handoff'
          if ($IsWindows) { $taskRunner += '.exe' }
          python -B research/p28-word0196/validate_native_p2_handoff.py --public --output .tmp/m2bv-public-evidence --runner $taskRunner
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Verify closed M2bv public artifact membership
        shell: pwsh
        run: |
          $taskRequired = @('canonical.jsonl.gz', 'summary.json', 'pre-runtime-freeze.json', 'sourcejoin.json')
          $taskActual = @(Get-ChildItem -LiteralPath '.tmp/m2bv-public-evidence' -Force)
          if ($taskActual.Count -ne 4) { throw 'Unexpected M2bv artifact membership.' }
          foreach ($taskName in $taskRequired) {
            if (-not (Test-Path -LiteralPath (Join-Path '.tmp/m2bv-public-evidence' $taskName) -PathType Leaf)) { throw 'Missing M2bv artifact member.' }
          }

      - name: Preserve only public invented M2bv canonical evidence
        uses: actions/upload-artifact@v4
        with:
          name: M2bv-public-canonical-${{ matrix.os }}
          path: |
            .tmp/m2bv-public-evidence/canonical.jsonl.gz
            .tmp/m2bv-public-evidence/summary.json
            .tmp/m2bv-public-evidence/pre-runtime-freeze.json
            .tmp/m2bv-public-evidence/sourcejoin.json
          if-no-files-found: error
          retention-days: 14
'''

def make_workflow(base):
    if sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2buWorkflowRequired')
    text = base.decode('utf-8', 'strict')
    if text.count(M2BU_JOB) != 1 or text.count(DESKTOP) != 1:
        raise ValueError('ClosedM2buAndDesktopBoundariesRequired')
    return text.replace(M2BU_JOB, PINNED_M2BU_JOB, 1).replace(DESKTOP, M2BV_JOB + DESKTOP, 1).encode('utf-8')

def workflow_projection(base, active):
    if active != make_workflow(base):
        raise ValueError('UnreviewedHistoricalDesktopM2buOrM2bvCiChange')
    return {'historicalTwoJobsByteExact': True, 'm2btTwoJobsByteExact': True,
            'desktopJobByteExact': True, 'm2buCommandsAndCoveragePreservedAtExactAcceptedSource': True,
            'm2buHistoricalSourceSha': BASE, 'm2bvTwoCurrentSourceJobsRequireBothM2buJobs': True,
            'newCurrentDefaultOffAndAllOptInTestsRequired': True, 'requiredActualJobs': 9,
            'requiredTechnicalStepsSkippedOrDisabled': False, 'duplicateHeavyHistoricalJobsAdded': 0}
