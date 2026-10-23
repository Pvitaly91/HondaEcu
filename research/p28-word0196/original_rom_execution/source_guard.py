"""Closed M2bt Git-source join; no ROM loading or CPU execution.

Historical M2br and M2bs gates execute at their own exact commits. This guard
checks the final active tree separately, including the reviewed opt-in Rust
delta. Historical compiled results are not execution of that changed delta.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tomllib

sys.dont_write_bytecode = True
_OLD_PATH = Path(__file__).resolve().parents[1] / "original_rom_boundary/source_guard.py"
_SPEC = importlib.util.spec_from_file_location("_m2bt_frozen_raw_git_guard", _OLD_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("FrozenPublicRawGitGuardUnavailable")
_OLD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _OLD
_SPEC.loader.exec_module(_OLD)
Blob, GuardError = _OLD.Blob, _OLD.GuardError
canonical, need, safe_name = _OLD.canonical, _OLD.need, _OLD.safe_name
git, tree, contents = _OLD.git, _OLD.tree, _OLD.contents

BASE = "4196153c6bcda3da5b164db752a8be4011c4e598"
BASE_SOURCE_COUNT = 934
BASE_SOURCE_FINGERPRINT = "68832cce916aa9b1fb2571d38f8498434da70b38432812cdc89650bd32a6c677"
BASE_WORKFLOW_SHA256 = "0bb0f1a3dc3ec724a686070014554079960faabedee244df3eee25a027f4bf67"
WORKFLOW = ".github/workflows/build.yml"
MANIFEST = "rust/p28-slice-runner/Cargo.toml"
FEATURE = "p28-word0196-original-rom"
BIN_NAME = "m2bt-original-rom"
BIN_PATH = "src/bin/m2bt_original_rom.rs"
PACKAGE = "research/p28-word0196/original_rom_execution/"
NEW_PATHS = frozenset(PACKAGE + name for name in (
    "__init__.py", "admission.py", "binding.py", "build_guard.py", "build_guard_tests.py",
    "checkpoint.py", "checkpoint_tests.py", "contract_validation.py", "contract_validation_tests.py", "oracle.py",
    "oracle_tests.py", "corpus.py", "contract.json", "verify.py",
    "verify_tests.py", "source_guard.py", "source_guard_tests.py",
)) | frozenset({
    "AGENTS.md", "research/p28-word0196/validate_original_rom_execution.py",
    "docs/M2BT_WORD0196_BOUNDED_ORIGINAL_ROM_EXECUTION.md",
    "rust/p28-slice-runner/src/audit_original_rom.rs",
    "rust/p28-slice-runner/src/audit_original_rom_tests.rs",
    "rust/p28-slice-runner/src/bin/m2bt_original_rom.rs",
})
RUST_DELTA_PATHS = frozenset({
    MANIFEST, "rust/p28-slice-runner/src/audit.rs",
    "rust/p28-slice-runner/src/audit_bus.rs",
})
# Exact reviewed default-off admission/lifecycle delta, not new arithmetic.
# Any later formatting or source edit requires a new explicit review/binding.
REVIEWED_OLD_DELTAS: dict[str, tuple[str, str]] = {
    MANIFEST: ("6bcc89513a94869f3a3309b8a3b3e3a75b9b1da71a26db0a77499c34a11d2bcd",
               "a895447460b84337dd78f255c4e0b1fbce3c240f26bf6afbf3721b1311d735a4"),
    "rust/p28-slice-runner/src/audit.rs": (
        "64bf04b29d6030c73100cf40de5c14fb2516a95b5b2219127bfd69ca4f4d346f",
        "15e5e78bda5db28146daae2df3f7417999af05d6074506730f74498079acf7e1"),
    "rust/p28-slice-runner/src/audit_bus.rs": (
        "2231a33e4c5b1f09614864365e9bde1fd23943ba3c5172adeee99cc9b2542646",
        "e020d4ecf0e91538924980bd3e0a192da8e01dd2131350024ccdf77eac3871f7"),
}
CI_TARGET = Path(".tmp/m2bt-owned/cargo-target")
CI_TARGET_MARKER = ".m2bt-public-ci-target.json"
FROZEN_M2BS_STEPS = _OLD.ACTIVE_STEPS
PINNED_M2BS_STEPS = FROZEN_M2BS_STEPS.replace(
    'ref: ${{ github.sha }}', 'ref: ' + BASE,
).replace('--expected-head "${{ github.sha }}"', '--expected-head "' + BASE + '"')
DESKTOP_MARKER = _OLD.DESKTOP_MARKER
ACTIVE_STEPS = """
      - name: Switch same checkout to active M2bt source after pinned M2bs gates
        uses: actions/checkout@v4
        with:
          ref: ${{ github.sha }}
          clean: false
          fetch-depth: 0
          persist-credentials: false

      - name: Active M2bt closed source integrity and reviewed opt-in Rust delta
        shell: pwsh
        run: |
          $taskJoin = python -B research/p28-word0196/original_rom_execution/source_guard.py --expected-head "${{ github.sha }}"
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          New-Item -ItemType Directory -Force -Path .tmp/m2bt-public-evidence | Out-Null
          [IO.File]::WriteAllText((Join-Path $PWD '.tmp/m2bt-public-evidence/sourcejoin.json'), ($taskJoin -join "`n") + "`n", [Text.UTF8Encoding]::new($false))

      - name: Active M2bt public synthetic admission oracle permissions and resume regressions
        shell: pwsh
        run: |
          python -B -m unittest discover -s research/p28-word0196/original_rom_execution -t research/p28-word0196 -p '*_tests.py'
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Active Rust default old-audit and M2bt opt-in feature regression suites
        shell: pwsh
        env:
          CARGO_TARGET_DIR: ${{ github.workspace }}/.tmp/m2bt-owned/cargo-target
        run: |
          python -B research/p28-word0196/original_rom_execution/source_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bt-owned/cargo-target --no-default-features
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/original_rom_execution/source_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bt-owned/cargo-target --no-default-features --features p28-word0196-audit
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          python -B research/p28-word0196/original_rom_execution/source_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 test --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bt-owned/cargo-target --no-default-features --features p28-word0196-original-rom
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 fmt --check --manifest-path rust/p28-slice-runner/Cargo.toml
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Build active required-feature M2bt public research runner
        shell: pwsh
        env:
          CARGO_TARGET_DIR: ${{ github.workspace }}/.tmp/m2bt-owned/cargo-target
        run: |
          python -B research/p28-word0196/original_rom_execution/source_guard.py --ci-cargo-preflight
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          cargo +1.85.1 build --release --locked --offline --jobs 1 --manifest-path rust/p28-slice-runner/Cargo.toml --target-dir .tmp/m2bt-owned/cargo-target --no-default-features --features p28-word0196-original-rom --bin m2bt-original-rom
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Active M2bt public invented production execution and deterministic canonical evidence
        shell: pwsh
        run: |
          $taskRunner = '.tmp/m2bt-owned/cargo-target/release/m2bt-original-rom'
          if ($IsWindows) { $taskRunner += '.exe' }
          python -B research/p28-word0196/validate_original_rom_execution.py --public --output .tmp/m2bt-public-evidence --runner $taskRunner
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Verify closed M2bt public canonical artifact membership
        shell: pwsh
        run: |
          $taskRequired = @('canonical.jsonl.gz', 'summary.json', 'pre-runtime-freeze.json', 'sourcejoin.json')
          $taskActual = @(Get-ChildItem -LiteralPath .tmp/m2bt-public-evidence -Force)
          if ($taskActual.Count -ne $taskRequired.Count) { throw 'Unexpected M2bt public artifact membership.' }
          foreach ($taskName in $taskRequired) {
            if (-not (Test-Path -LiteralPath (Join-Path '.tmp/m2bt-public-evidence' $taskName) -PathType Leaf)) { throw ('Missing M2bt public evidence: ' + $taskName) }
          }

      - name: Preserve M2bt public invented canonical evidence only
        uses: actions/upload-artifact@v4
        with:
          name: M2bt-public-canonical-${{ matrix.os }}
          path: |
            .tmp/m2bt-public-evidence/canonical.jsonl.gz
            .tmp/m2bt-public-evidence/summary.json
            .tmp/m2bt-public-evidence/pre-runtime-freeze.json
            .tmp/m2bt-public-evidence/sourcejoin.json
          if-no-files-found: error
          retention-days: 3
"""


def workflow_projection(base: bytes, active: bytes) -> dict:
    original = base.decode("utf-8", "strict")
    current = active.decode("utf-8", "strict")
    need(original.count(FROZEN_M2BS_STEPS) == 1, "ExactFrozenM2bsOrchestrationRequired")
    need(current.count(PINNED_M2BS_STEPS) == 1 and current.count(ACTIVE_STEPS) == 1,
         "ExactThreePhaseOrchestrationRequired")
    need(original.count(DESKTOP_MARKER) == current.count(DESKTOP_MARKER) == 1,
         "ExactDesktopJobBoundaryRequired")
    before, desktop = current.split(DESKTOP_MARKER, 1)
    need(before.endswith(ACTIVE_STEPS), "ActiveM2btStepsMustFollowEveryPinnedGate")
    restored = before[:-len(ACTIVE_STEPS)].replace(PINNED_M2BS_STEPS, FROZEN_M2BS_STEPS, 1)
    need(restored + DESKTOP_MARKER + desktop == original, "HistoricalWorkflowOrDesktopCheckChanged")
    return {"allHistoricalCommandBodiesPreserved": True, "desktopJobByteExact": True,
            "sameCheckoutThreePhases": True, "pinnedM2brSha": _OLD.BASE,
            "pinnedM2bsSha": BASE, "activeSourceGuardBeforePublicTests": True}


def manifest_projection(base: bytes, active: bytes) -> dict:
    old, new = (tomllib.loads(raw.decode("utf-8", "strict")) for raw in (base, active))
    need(type(new.get("features")) is dict and type(old.get("features")) is dict,
         "ClosedFeatureTablesRequired")
    need(new.get("features", {}).get("default") == [], "NewFeatureMustRemainDefaultOff")
    need(new["features"].get(FEATURE) == ["p28-word0196-audit"], "NewFeatureMustRequireExistingAudit")
    restored = dict(new)
    restored["features"] = dict(new["features"])
    del restored["features"][FEATURE]
    need(type(restored.get("bin")) is list, "ResearchBinaryTableRequired")
    bins = list(restored["bin"])
    required = {"name": BIN_NAME, "path": BIN_PATH, "required-features": [FEATURE]}
    need(bins.count(required) == 1, "ResearchBinaryMustRequireNewFeature")
    bins.remove(required)
    if bins or "bin" in old:
        restored["bin"] = bins
    else:
        del restored["bin"]
    need(restored == old, "UnrelatedCargoManifestContractChanged")
    return {"newFeature": FEATURE, "defaultOff": True,
            "existingAuditDependency": True, "requiredFeatureBinary": BIN_NAME,
            "packageVersionDependenciesProfilesAndOldFeaturesRetained": True}


def compare_trees(base: dict[str, Blob], active: dict[str, Blob], *,
                  reviewed_deltas: dict[str, tuple[str, str]] | None = None) -> dict:
    need(type(base) is dict and type(active) is dict and WORKFLOW in base,
         "CompleteSourceTreeMappingsRequired")
    for name, blob in (*base.items(), *active.items()):
        need(safe_name(name) and isinstance(blob, Blob) and blob.mode in ("100644", "100755")
             and type(blob.data) is bytes, "ClosedRegularSourceTree")
    need(set(base) <= set(active), "HistoricalSourceDeleted")
    added = set(active) - set(base)
    need(not any(name.startswith(("private/", "artifacts/")) or
                 PurePosixPath(name).suffix.lower() in _OLD.FORBIDDEN_SUFFIXES or
                 name.endswith(".gpr.bak") for name in added), "PrivateOrBinaryArtifactAdded")
    need(added == NEW_PATHS, "UnknownOrMissingM2btSourcePath")
    deltas = REVIEWED_OLD_DELTAS if reviewed_deltas is None else reviewed_deltas
    need(type(deltas) is dict and set(deltas) == RUST_DELTA_PATHS,
         "ExactReviewedOptInDeltaBindingsRequired")
    authorized = []
    for name in sorted(base):
        need(active[name].mode == base[name].mode, "HistoricalSourceModeChanged:" + name)
        if name == WORKFLOW:
            continue
        if name in RUST_DELTA_PATHS:
            pair = deltas[name]
            need(type(pair) is tuple and len(pair) == 2 and all(
                type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None
                for value in pair), "ReviewedOptInDeltaNotFrozen:" + name)
            actual = (sha256(base[name].data).hexdigest(), sha256(active[name].data).hexdigest())
            need(actual == pair and pair[0] != pair[1], "UnreviewedOptInRustDelta:" + name)
            authorized.append({"path": name, "beforeSha256": pair[0], "afterSha256": pair[1]})
        else:
            need(active[name] == base[name], "HistoricalOrProductionInputChanged:" + name)
    need(RUST_DELTA_PATHS <= set(base), "ReviewedOptInBaseSourcesMissing")
    workflow = workflow_projection(base[WORKFLOW].data, active[WORKFLOW].data)
    feature = manifest_projection(base[MANIFEST].data, active[MANIFEST].data)
    python_paths = []
    for name in sorted(NEW_PATHS):
        blob = active[name]
        need(blob.mode == "100644" and b"\x00" not in blob.data,
             "NewResearchSourceMustBeNonexecutableText:" + name)
        text = blob.data.decode("utf-8", "strict")
        if name.endswith(".py"):
            compile(text, name, "exec", dont_inherit=True)
            python_paths.append(name)
    rows = [{"path": name, "mode": blob.mode, "bytes": len(blob.data),
             "sha256": sha256(blob.data).hexdigest()} for name, blob in sorted(active.items())]
    return {"passed": True, "classification": "SourceJoin_NotCpuExecutionOrPrivateRomProof",
            "baseSourceCount": len(base), "unchangedBaseFiles": len(base) - len(RUST_DELTA_PATHS) - 1,
            "authorizedOldOptInRustDeltas": authorized, "workflow": workflow, "feature": feature,
            "newPublicPaths": sorted(added), "sourceBindings": rows,
            "sourceFingerprintSha256": sha256(canonical(rows)).hexdigest(),
            "newPythonSyntaxChecks": python_paths, "historicalCompiledResultsAreActiveExecution": False,
            "changedRustInputsRequireActiveQa": True, "originalRomVerificationByThisGuard": False,
            "privateContentPrivacyAttestationByThisGuard": False, "targetCpuExecutions": 0,
            "firmwareReady": False}


def verify_git(root: Path, expected_head: str) -> dict:
    need(re.fullmatch(r"[0-9a-f]{40}", expected_head) is not None, "ExplicitExactActiveShaRequired")
    head = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    need(head == expected_head and head != BASE, "WrongActiveM2btSha")
    git(root, "merge-base", "--is-ancestor", BASE, head)
    base, active = tree(root, BASE), tree(root, head)
    need(len(base) == BASE_SOURCE_COUNT, "ExactM2bsSourceMembership")
    data = contents(root, (base, active))
    base_files = {name: Blob(mode, data[oid]) for name, (mode, oid) in base.items()}
    active_files = {name: Blob(mode, data[oid]) for name, (mode, oid) in active.items()}
    base_rows = [{"path": name, "mode": blob.mode, "bytes": len(blob.data),
                  "sha256": sha256(blob.data).hexdigest()} for name, blob in sorted(base_files.items())]
    need(sha256(canonical(base_rows)).hexdigest() == BASE_SOURCE_FINGERPRINT,
         "ExactFrozenM2bsSourceFingerprintRequired")
    need(sha256(base_files[WORKFLOW].data).hexdigest() == BASE_WORKFLOW_SHA256,
         "ExactFrozenM2bsWorkflowSource")
    result = compare_trees(base_files, active_files)
    for name, blob in active_files.items():
        path = root / name
        need(not path.is_symlink() and path.resolve() == path and path.is_file(), "PhysicalSourcePathRequired")
        with path.open("rb") as stream:
            need(stream.read(_OLD.MAX_BLOB_BYTES + 1) == blob.data,
                 "WorkingTreeSourceDiffersFromCommittedBlob:" + name)
    need(git(root, "rev-parse", "HEAD").decode("ascii").strip() == head, "ActiveHeadChangedDuringGuard")
    result.update({"schemaVersion": 1, "milestone": "M2bt", "exactBase": BASE,
                   "activeSha": head, "gitRawBlobComparison": True,
                   "physicalWorkingTreeMatchesCommittedSources": True,
                   "historicalQaSourceShas": [_OLD.BASE, BASE], "networkOrGitMutations": 0})
    return result


def _no_reparse(path: Path) -> None:
    need(path.is_absolute() and ".." not in path.parts, "AbsoluteCiSourcePathRequired")
    for node in reversed((path, *path.parents)):
        if not os.path.lexists(node):
            continue
        info = node.lstat()
        need(not stat.S_ISLNK(info.st_mode)
             and not bool(getattr(info, "st_file_attributes", 0) & 0x400),
             "CiTargetReparsePointRejected")


def ci_cargo_preflight(root: Path, environment: dict[str, str] | None = None) -> dict:
    """Fresh public CI routing only, not the private historical-runner fence.

    Never adopts a nonempty target without this exact CI ownership marker. The
    local controller uses the stronger build_guard and its external receipt.
    Only the owned target is walked; no historical/cache inventory is made.
    """
    environment = dict(os.environ if environment is None else environment)
    need(environment.get("GITHUB_ACTIONS") == "true", "PublicCiContextRequired")
    head = environment.get("GITHUB_SHA", "")
    need(re.fullmatch(r"[0-9a-f]{40}", head) is not None, "ExactPublicCiShaRequired")
    root = Path(os.path.abspath(root))
    target = root / CI_TARGET
    legacy = root / "rust/p28-slice-runner/target"
    for node in (root, target, legacy):
        _no_reparse(node)
    need(target != legacy and target not in legacy.parents and legacy not in target.parents,
         "CiHistoricalTargetOverlap")
    supplied = environment.get("CARGO_TARGET_DIR", "")
    need(bool(supplied) and Path(os.path.abspath(supplied)) == target,
         "ExactCiCargoTargetEnvironmentRequired")
    need(root.is_dir(), "CiSourceRootMissing")
    marker = target / CI_TARGET_MARKER
    expected = {"schemaVersion": 1, "classification": "M2btPublicCiOwnedCargoTarget",
                "repository": str(root), "target": str(target), "activeSha": head}
    if target.exists():
        need(target.is_dir(), "CiTargetMustBeDirectory")
        if marker.exists():
            _no_reparse(marker)
            need(marker.is_file() and marker.read_bytes() == canonical(expected),
                 "CiTargetOwnershipMismatch")
        else:
            need(not any(target.iterdir()), "CiUnownedNonemptyTargetRejected")
    else:
        target.mkdir(parents=True, exist_ok=False)
    if not marker.exists():
        with marker.open("xb") as stream:
            stream.write(canonical(expected))
    # Check actual generated entries too: Cargo must not follow a target-local
    # junction or symlink into a historical output tree on a later suite.
    for directory, directories, files in os.walk(target, followlinks=False):
        for name in directories + files:
            _no_reparse(Path(directory) / name)
    _no_reparse(target)
    need(marker.read_bytes() == canonical(expected), "CiTargetOwnerChangedDuringCheck")
    return {"passed": True, "classification": "PublicCiOutputRoutingOnly_NotPrivatePreservationPass",
            "activeSha": head, "target": str(target), "explicitTargetDirRequiredForEveryCargoBuildOrTest": True,
            "historicalTargetOverlap": False, "targetReparsePoints": 0,
            "historicalRunnerPreservationAttested": False, "privateInputsRequired": False,
            "cargoInvocations": 0, "cpuExecutions": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--expected-head")
    mode.add_argument("--ci-cargo-preflight", action="store_true")
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[3]
        result = ci_cargo_preflight(root) if args.ci_cargo_preflight else verify_git(root, args.expected_head)
    except (ValueError, OSError, SyntaxError, subprocess.SubprocessError) as error:
        print(canonical({"milestone": "M2bt", "passed": False,
                         "diagnosticClass": type(error).__name__,
                         "rule": str(error) if isinstance(error, GuardError) else "SourceInputReadOrSyntaxFailure",
                         "originalRomVerificationByThisGuard": False}).decode("ascii"))
        return 1
    print(canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
