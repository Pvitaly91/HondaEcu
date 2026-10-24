"""Closed M2bu CI projection; frozen M2bt checks retain their own identities."""
from hashlib import sha256

BASE = '7eb26571d8ee1f849efe5ffa619b0201008b267c'
BASE_WORKFLOW_SHA = 'dac19ecd2ffaf46d19bb1abdd508082d7fecd925cf1e6fba33488a4edf473673'
PROOF_START = '\n      - name: Verify closed CI-only delivery orchestration and immutable runtime source\n'
PROOF_END = '\n      - name: Active M2bt closed source integrity and reviewed opt-in Rust delta\n'
DESKTOP = '\n  desktop-windows:\n'

# This step does not rewrite GITHUB_SHA or run an old whole-source guard at a
# different identity. Its pure documentary projection operates on two actual
# immutable historical Git objects; new M2bu sources get their separate guard.
FROZEN_PROOF = r'''
      - name: Verify frozen M2bt delivery provenance independently of active M2bu
        shell: python
        run: |
          import hashlib
          import json
          import os
          import subprocess
          import textwrap

          def git(*args):
              result = subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, timeout=30)
              if len(result.stdout) > 2097152:
                  raise ValueError("BoundedHistoricalGitMetadataRequired")
              return result.stdout

          historical = "7eb26571d8ee1f849efe5ffa619b0201008b267c"
          runtime = "7de605aae82a873ed5b3fc6ef8604c6549ff8f6c"
          workflow = ".github/workflows/build.yml"
          frozen = git("show", historical + ":" + workflow)
          if hashlib.sha256(frozen).hexdigest() != "dac19ecd2ffaf46d19bb1abdd508082d7fecd925cf1e6fba33488a4edf473673":
              raise ValueError("ExactAcceptedM2btWorkflowRequired")
          text = frozen.decode("utf-8")
          start = text.index("\n      - name: Verify closed CI-only delivery orchestration and immutable runtime source\n")
          end = text.index("\n      - name: Active M2bt closed source integrity and reviewed opt-in Rust delta\n", start)
          body = text[start:end].split("        run: |\n", 1)[1]
          namespace = {"__name__": "frozen_m2bt_projection_only"}
          exec(compile(textwrap.dedent(body), "accepted_m2bt_pure_projection", "exec"), namespace)
          if git("rev-parse", "HEAD").decode().strip() != runtime:
              raise ValueError("ImmutableM2btRuntimeCheckoutRequired")
          if git("rev-list", "--parents", "-n", "1", historical).decode().split() != [historical, runtime]:
              raise ValueError("HistoricalDeliveryParentChanged")
          before, after = namespace["raw_tree"](runtime), namespace["raw_tree"](historical)
          if set(before) != set(after) or [p for p in sorted(before) if before[p] != after[p]] != [workflow.encode()]:
              raise ValueError("FrozenM2btNonWorkflowSourceChanged")
          projection = namespace["validate_workflow"](git("show", runtime + ":" + workflow).decode(), text)
          print(json.dumps({"passed": True, "classification": "HistoricalM2btDeliveryProjection_NotM2buSourceProof",
                            "historicalDeliverySha": historical, "runtimeSourceSha": runtime,
                            "actualCurrentWorkflowHead": os.environ["GITHUB_SHA"],
                            "projection": projection, "originalRomExecuted": False,
                            "firmwareReady": False}, sort_keys=True))
'''

M2BU_JOB = r'''
  native-entry-continuity:
    needs: build-and-test
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
      CARGO_TARGET_DIR: ${{ github.workspace }}/.tmp/m2bu-owned/cargo-target

    steps:
      - name: Checkout exact active M2bu source
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Set up pinned M2bu Rust toolchain
        run: rustup toolchain install 1.85.1 --profile minimal --component rustfmt

      - name: Verify active M2bu closed source and seven-job CI projection
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_entry_continuity/source_guard.py --expected-head "${{ github.sha }}"
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bu independent oracle admission source and resume regressions
        shell: pwsh
        run: |
          python -B -m unittest discover -s research/p28-word0196/native_entry_continuity -t research/p28-word0196 -p '*_tests.py'
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Fetch exact locked M2bu dependencies
        shell: pwsh
        run: |
          cargo +1.85.1 fetch --locked --manifest-path rust/p28-slice-runner/Cargo.toml
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bu current-source default old-admission and new-feature Rust regressions
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_entry_continuity/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bu-owned/cargo-target --no-default-features
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/native_entry_continuity/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bu-owned/cargo-target --no-default-features --features p28-word0196-audit
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/native_entry_continuity/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bu-owned/cargo-target --no-default-features --features p28-word0196-original-rom
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/native_entry_continuity/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bu-owned/cargo-target --no-default-features --features p28-word0196-entry-continuity
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 fmt --check --manifest-path rust/p28-slice-runner/Cargo.toml
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Build required-feature M2bu research runner in owned target
        shell: pwsh
        run: |
          python -B research/p28-word0196/native_entry_continuity/build_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 build --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bu-owned/cargo-target --no-default-features --features p28-word0196-entry-continuity --bin m2bu-entry-continuity
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: M2bu actual public invented continuous production execution
        shell: pwsh
        run: |
          $taskRunner = '.tmp/m2bu-owned/cargo-target/release/m2bu-entry-continuity'
          if ($IsWindows) { $taskRunner += '.exe' }
          python -B research/p28-word0196/validate_native_entry_continuity.py --public --output .tmp/m2bu-public-evidence/positive --runner $taskRunner
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/validate_native_entry_continuity.py --public --branch-controls --output .tmp/m2bu-public-evidence/boundaries --runner $taskRunner
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Verify closed M2bu public artifact membership
        shell: pwsh
        run: |
          $taskRequired = @('canonical.jsonl.gz', 'summary.json', 'pre-runtime-freeze.json', 'sourcejoin.json')
          foreach ($taskMode in @('positive', 'boundaries')) {
            $taskDirectory = Join-Path '.tmp/m2bu-public-evidence' $taskMode
            $taskActual = @(Get-ChildItem -LiteralPath $taskDirectory -Force)
            if ($taskActual.Count -ne 4) { throw 'Unexpected M2bu artifact membership.' }
            foreach ($taskName in $taskRequired) {
              if (-not (Test-Path -LiteralPath (Join-Path $taskDirectory $taskName) -PathType Leaf)) { throw 'Missing M2bu artifact member.' }
            }
          }

      - name: Preserve only public invented M2bu canonical evidence
        uses: actions/upload-artifact@v4
        with:
          name: M2bu-public-canonical-${{ matrix.os }}
          path: |
            .tmp/m2bu-public-evidence/positive/canonical.jsonl.gz
            .tmp/m2bu-public-evidence/positive/summary.json
            .tmp/m2bu-public-evidence/positive/pre-runtime-freeze.json
            .tmp/m2bu-public-evidence/positive/sourcejoin.json
            .tmp/m2bu-public-evidence/boundaries/canonical.jsonl.gz
            .tmp/m2bu-public-evidence/boundaries/summary.json
            .tmp/m2bu-public-evidence/boundaries/pre-runtime-freeze.json
            .tmp/m2bu-public-evidence/boundaries/sourcejoin.json
          if-no-files-found: error
          retention-days: 14
'''


def make_workflow(base):
    if sha256(base).hexdigest() != BASE_WORKFLOW_SHA:
        raise ValueError('ExactAcceptedM2btWorkflowRequired')
    text = base.decode('utf-8', 'strict')
    if text.count(PROOF_START) != 1 or text.count(PROOF_END) != 1 or text.count(DESKTOP) != 1:
        raise ValueError('ClosedHistoricalWorkflowBoundariesRequired')
    start, end = text.index(PROOF_START), text.index(PROOF_END)
    return (text[:start] + FROZEN_PROOF + text[end:]).replace(DESKTOP, M2BU_JOB + DESKTOP, 1).encode('utf-8')


def workflow_projection(base, active):
    if active != make_workflow(base):
        raise ValueError('UnreviewedHistoricalDesktopOrM2buCiChange')
    return {'historicalTwoJobsUnchanged': True, 'desktopJobByteExact': True,
            'm2btCommandsAndRuntimePinsUnchanged': True,
            'm2btProofExplicitlyHistoricalNotNewHead': True,
            'm2buTwoJobsRequireBothM2btJobs': True, 'requiredActualJobs': 7,
            'requiredTechnicalStepsSkippedOrDisabled': False}
