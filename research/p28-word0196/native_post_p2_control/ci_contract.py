"""Closed eleven-job M2bw projection; prior contracts remain immutable."""
from hashlib import sha256
from native_p2_handoff.ci_contract import M2BV_JOB

BASE = 'b67ea436870fe591f6ae4daca307341806d6f8eb'
BASE_WORKFLOW_SHA = '5671e76fb0c26e5c6fcbe2205b4e0189b49ab01c3de1d16a0bfdfbc9a03fdbfb'
DESKTOP = '\n  desktop-windows:\n'
PINNED_M2BV_JOB = M2BV_JOB.replace('Checkout exact active M2bv source', 'Checkout pinned accepted M2bv source').replace(
    '          fetch-depth: 0\n', '          ref: ' + BASE + '\n          fetch-depth: 0\n', 1).replace(
    '--expected-head "${{ github.sha }}"', '--expected-head "' + BASE + '"').replace(
    'Verify active M2bv closed source and nine-job CI projection',
    'Verify pinned M2bv source and its unchanged nine-job CI projection')

M2BW_JOB = r'''

  native-post-p2-control:
    needs: native-p2-handoff
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
      CARGO_TARGET_DIR: ${{ github.workspace }}/.tmp/m2bw-owned/cargo-target

    steps:
      - name: Checkout exact active M2bw source
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Set up pinned M2bw Rust toolchain
        run: rustup toolchain install 1.85.1 --profile minimal --component rustfmt

      - name: Verify active M2bw closed source and eleven-job CI projection
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_post_p2_control/source_guard.py --expected-head "${{ github.sha }}"
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bw independent P2 oracle ownership admission and resume regressions
        shell: pwsh
        run: |
          python -B -m unittest discover -s research/p28-word0196/native_post_p2_control -t research/p28-word0196 -p '*_tests.py'
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Fetch exact locked M2bw dependencies
        shell: pwsh
        run: |
          cargo +1.85.1 fetch --locked --manifest-path rust/p28-slice-runner/Cargo.toml
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bw current-source default-off and complete old-plus-P2 Rust regressions
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_post_p2_control/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bw-owned/cargo-target --no-default-features
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/native_post_p2_control/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bw-owned/cargo-target --no-default-features --features p28-word0196-post-p2-control
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 fmt --check --manifest-path rust/p28-slice-runner/Cargo.toml
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Build required-feature M2bw P2 runner in owned target
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_post_p2_control/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 build --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bw-owned/cargo-target --no-default-features --features p28-word0196-post-p2-control --bin m2bw-post-p2-control
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bw actual public continuous predecessor algorithm and one-P2 and post-P2 control execution
        shell: pwsh
        run: |
          $taskRunner = '.tmp/m2bw-owned/cargo-target/release/m2bw-post-p2-control'
          if ($IsWindows) { $taskRunner += '.exe' }
          python -B research/p28-word0196/validate_native_post_p2_control.py --public --output .tmp/m2bw-public-evidence --runner $taskRunner
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Verify closed M2bw public artifact membership
        shell: pwsh
        run: |
          $taskRequired = @('canonical.jsonl.gz', 'summary.json', 'pre-runtime-freeze.json', 'sourcejoin.json')
          $taskActual = @(Get-ChildItem -LiteralPath '.tmp/m2bw-public-evidence' -Force)
          if ($taskActual.Count -ne 4) { throw 'Unexpected M2bw artifact membership.' }
          foreach ($taskName in $taskRequired) {
            if (-not (Test-Path -LiteralPath (Join-Path '.tmp/m2bw-public-evidence' $taskName) -PathType Leaf)) { throw 'Missing M2bw artifact member.' }
          }

      - name: Preserve only public invented M2bw canonical evidence
        uses: actions/upload-artifact@v4
        with:
          name: M2bw-public-canonical-${{ matrix.os }}
          path: |
            .tmp/m2bw-public-evidence/canonical.jsonl.gz
            .tmp/m2bw-public-evidence/summary.json
            .tmp/m2bw-public-evidence/pre-runtime-freeze.json
            .tmp/m2bw-public-evidence/sourcejoin.json
          if-no-files-found: error
          retention-days: 14
'''

def make_workflow(base):
    if sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2bvWorkflowRequired')
    text = base.decode('utf-8', 'strict')
    if text.count(M2BV_JOB) != 1 or text.count(DESKTOP) != 1:
        raise ValueError('ClosedM2bvAndDesktopBoundariesRequired')
    return text.replace(M2BV_JOB, PINNED_M2BV_JOB, 1).replace(DESKTOP, M2BW_JOB + DESKTOP, 1).encode('utf-8')

def workflow_projection(base, active):
    if active != make_workflow(base):
        raise ValueError('UnreviewedHistoricalDesktopM2bvOrM2bwCiChange')
    return {'historicalJobsPreservedAtPinnedIdentities': True, 'desktopJobByteExact': True,
        'm2bvCommandsAndCoveragePreservedAtExactAcceptedSource': True, 'm2bvHistoricalSourceSha': BASE,
        'newCurrentDefaultOffAndAllOptInTestsRequired': True, 'requiredActualJobs': 11,
        'requiredTechnicalStepsSkippedOrDisabled': False, 'duplicateHeavyHistoricalJobsAdded': 0}
