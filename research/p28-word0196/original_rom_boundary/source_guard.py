"""Public M2bs source guard; no ROM input, execution, writes, or Git mutations.

The historical matrix gates run on the exact M2br commit. This guard runs only
after the same CI checkout switches to the active M2bs commit. It establishes
unchanged production inputs, not a new execution of those compiled inputs.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = "2657bb8ae3add410e693d988bac7ccf5cece7f50"
BASE_SOURCE_COUNT = 920
WORKFLOW = ".github/workflows/build.yml"
BASE_WORKFLOW_SHA256 = "16f72e40d2a2c7a8c3f8fb2f2417f5572a64cbe5d33914ec9c8f249d7c861760"
PACKAGE = "research/p28-word0196/original_rom_boundary/"
NEW_PATHS = frozenset(
    PACKAGE + name for name in (
        "__init__.py", "decode.py", "decode_tests.py", "context.py",
        "context_tests.py", "historical.py", "historical_tests.py", "verify.py",
        "verify_tests.py", "source_guard.py", "source_guard_tests.py", "contract.json",
    )
) | frozenset({
    "research/p28-word0196/validate_original_rom_boundary.py",
    "docs/M2BS_ORIGINAL_ROM_BOUNDARY_NATIVE_CONTEXT.md",
})
FORBIDDEN_SUFFIXES = frozenset({
    ".bin", ".rom", ".hex", ".eep", ".dump", ".gzf", ".rep", ".gpr",
    ".db", ".trace", ".exe", ".dll", ".pdb", ".zip", ".obj", ".o",
})
ORIGINAL_CHECKOUT = """    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
"""
HISTORICAL_CHECKOUT = """    steps:
      - name: Historical M2br QA on exact 2657bb8 source
        uses: actions/checkout@v4
        with:
          ref: 2657bb8ae3add410e693d988bac7ccf5cece7f50
          fetch-depth: 0
"""
ACTIVE_STEPS = """
      - name: Switch same checkout to active M2bs source after all historical gates
        uses: actions/checkout@v4
        with:
          ref: ${{ github.sha }}
          clean: false
          fetch-depth: 0
          persist-credentials: false

      - name: Active M2bs source integrity and unchanged production input guard
        shell: pwsh
        run: |
          python -B research/p28-word0196/original_rom_boundary/source_guard.py --expected-head "${{ github.sha }}"
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

      - name: Active M2bs public synthetic boundary and negative regressions
        shell: pwsh
        run: |
          python -B -m unittest discover -s research/p28-word0196/original_rom_boundary -p '*_tests.py'
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
"""
DESKTOP_MARKER = "\n  desktop-windows:"
MAX_TREE_BYTES = 2 * 1024 * 1024
MAX_BLOB_BYTES = 32 * 1024 * 1024
MAX_ALL_BYTES = 128 * 1024 * 1024


class GuardError(ValueError):
    """Controlled public-safe diagnostic; arbitrary exception values are private."""


def need(condition: bool, reason: str) -> None:
    if condition is not True:
        raise GuardError(reason)


@dataclass(frozen=True)
class Blob:
    mode: str
    data: bytes


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def safe_name(name: str) -> bool:
    return (type(name) is str and bool(name) and "\\" not in name and ":" not in name
            and not name.startswith("/") and "\x00" not in name
            and PurePosixPath(name).as_posix() == name
            and all(part not in ("", ".", "..") for part in name.split("/")))


def workflow_projection(base: bytes, active: bytes) -> dict:
    """Check the literal orchestration delta; no YAML/runtime interpretation."""
    original = base.decode("utf-8", "strict")
    current = active.decode("utf-8", "strict")
    need(original.count(ORIGINAL_CHECKOUT) == 1, "OriginalFirstCheckoutMissing")
    need(current.count(HISTORICAL_CHECKOUT) == 1 and current.count(ACTIVE_STEPS) == 1,
         "ExactTwoCheckoutOrchestrationRequired")
    need(original.count(DESKTOP_MARKER) == current.count(DESKTOP_MARKER) == 1,
         "ExactDesktopJobBoundaryRequired")
    before_desktop, desktop = current.split(DESKTOP_MARKER, 1)
    need(before_desktop.endswith(ACTIVE_STEPS), "ActiveStepsMustFollowEveryHistoricalGate")
    historical = before_desktop[:-len(ACTIVE_STEPS)]
    restored = historical.replace(HISTORICAL_CHECKOUT, ORIGINAL_CHECKOUT, 1) + DESKTOP_MARKER + desktop
    need(restored == original, "HistoricalWorkflowOrDesktopCheckChanged")
    return {"allHistoricalStepsPreserved": True, "desktopJobByteExact": True,
            "sameCheckoutOnly": True, "activeSourceGuardBeforePublicTests": True}


def compare_trees(base: dict[str, Blob], active: dict[str, Blob]) -> dict:
    """Pure invented-testable comparison; actual Git provenance is joined below."""
    need(type(base) is dict and type(active) is dict and WORKFLOW in base,
         "CompleteSourceTreeMappingsRequired")
    for name, blob in (*base.items(), *active.items()):
        need(safe_name(name) and isinstance(blob, Blob) and blob.mode in ("100644", "100755")
             and type(blob.data) is bytes, "ClosedRegularSourceTree")
    need(set(base) <= set(active), "HistoricalSourceDeleted")
    added = set(active) - set(base)
    need(not any(name.startswith(("private/", "artifacts/")) or
                 PurePosixPath(name).suffix.lower() in FORBIDDEN_SUFFIXES or
                 name.endswith(".gpr.bak") for name in added), "PrivateOrBinaryArtifactAdded")
    need(added == NEW_PATHS, "UnknownOrMissingM2bsSourcePath")
    for name in sorted(base):
        if name != WORKFLOW:
            need(active[name] == base[name], "HistoricalOrProductionInputChanged:" + name)
    need(active[WORKFLOW].mode == base[WORKFLOW].mode, "WorkflowModeChanged")
    policy = workflow_projection(base[WORKFLOW].data, active[WORKFLOW].data)
    python_paths = []
    for name in sorted(NEW_PATHS):
        data = active[name].data
        need(active[name].mode == "100644" and b"\x00" not in data,
             "NewResearchSourceMustBeNonexecutableText:" + name)
        text = data.decode("utf-8", "strict")
        if name.endswith(".py"):
            compile(text, name, "exec", dont_inherit=True)
            python_paths.append(name)
    rows = [{"path": name, "mode": blob.mode, "bytes": len(blob.data),
             "sha256": sha256(blob.data).hexdigest()} for name, blob in sorted(active.items())]
    return {"passed": True, "classification": "SourceInputEquality_NotNewProductionExecutionOrNativeRomProof",
            "baseSourceCount": len(base), "unchangedBaseFiles": len(base) - 1,
            "onlyChangedBasePath": WORKFLOW, "newPublicPaths": sorted(added),
            "sourceFingerprintSha256": sha256(canonical(rows)).hexdigest(),
            "sourceBindings": rows, "newPythonSyntaxChecks": python_paths,
            "unchangedProductionInputsOnly": True, "historicalCompiledResultsAreActiveExecution": False,
            "workflow": policy, "originalRomVerificationByThisGuard": False,
            "targetCpuExecutions": 0, "firmwareReady": False}


def git(root: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    need(not any(os.environ.get(key) for key in (
        "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES")), "UnexpectedGitRepositoryOverride")
    environment = os.environ.copy()
    environment["GIT_NO_LAZY_FETCH"] = "1"
    result = subprocess.run(["git", "--no-optional-locks", "--no-replace-objects", "-C", str(root),
                             *arguments], input=input_bytes, capture_output=True, check=False,
                            timeout=60, env=environment)
    need(result.returncode == 0, "ReadOnlyGitCommandFailed")
    return result.stdout


def tree(root: Path, revision: str) -> dict[str, tuple[str, str]]:
    raw = git(root, "ls-tree", "-rz", "--full-tree", revision)
    need(len(raw) <= MAX_TREE_BYTES and raw.endswith(b"\x00"), "BoundedCompleteGitTree")
    result = {}
    for row in raw[:-1].split(b"\x00"):
        header, path = row.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split(" ")
        name = path.decode("utf-8", "strict")
        need(safe_name(name) and name not in result and mode in ("100644", "100755")
             and kind == "blob" and re.fullmatch(r"[0-9a-f]{40}", oid) is not None,
             "ClosedRawGitBlobInventory")
        result[name] = (mode, oid)
    return result


def contents(root: Path, inventories: tuple[dict[str, tuple[str, str]], ...]) -> dict[str, bytes]:
    oids = sorted({oid for inventory in inventories for _, oid in inventory.values()})
    sizes = git(root, "cat-file", "--batch-check", input_bytes="".join(oid + "\n" for oid in oids).encode("ascii"))
    size_rows = sizes.decode("ascii").splitlines()
    need(len(size_rows) == len(oids), "CompleteGitBlobSizePreflight")
    total = 0
    for expected, row in zip(oids, size_rows):
        oid, kind, size = row.split(" ")
        need(oid == expected and kind == "blob" and size.isdecimal()
             and 0 <= int(size) <= MAX_BLOB_BYTES, "BoundedGitSourceBlob")
        total += int(size)
    need(total <= MAX_ALL_BYTES, "BoundedAllSelectedSourceBytes")
    raw = git(root, "cat-file", "--batch", input_bytes="".join(oid + "\n" for oid in oids).encode("ascii"))
    need(len(raw) <= MAX_ALL_BYTES + len(oids) * 128, "BoundedRawGitBlobStream")
    result, offset = {}, 0
    for expected in oids:
        end = raw.index(b"\n", offset)
        oid, kind, size = raw[offset:end].decode("ascii").split(" ")
        length = int(size)
        need(oid == expected and kind == "blob" and 0 <= length <= MAX_BLOB_BYTES,
             "ExactRawGitBlobHeader")
        offset = end + 1
        result[oid] = raw[offset:offset + length]
        need(len(result[oid]) == length and raw[offset + length:offset + length + 1] == b"\n",
             "CompleteRawGitBlobBytes")
        offset += length + 1
    need(offset == len(raw), "FullGitBlobStreamConsumed")
    return result


def verify_git(root: Path, expected_head: str) -> dict:
    need(re.fullmatch(r"[0-9a-f]{40}", expected_head) is not None, "ExplicitExactActiveShaRequired")
    head = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    need(head == expected_head and head != BASE, "WrongActiveM2bsSha")
    git(root, "merge-base", "--is-ancestor", BASE, head)
    base, active = tree(root, BASE), tree(root, head)
    need(len(base) == BASE_SOURCE_COUNT, "ExactM2brSourceMembership")
    data = contents(root, (base, active))
    base_files = {name: Blob(mode, data[oid]) for name, (mode, oid) in base.items()}
    active_files = {name: Blob(mode, data[oid]) for name, (mode, oid) in active.items()}
    need(sha256(base_files[WORKFLOW].data).hexdigest() == BASE_WORKFLOW_SHA256,
         "ExactFrozenM2brWorkflowSource")
    result = compare_trees(base_files, active_files)
    for name, blob in active_files.items():
        path = root / name
        need(not path.is_symlink() and path.resolve() == path and path.is_file(), "PhysicalSourcePathRequired")
        with path.open("rb") as stream:
            need(stream.read(MAX_BLOB_BYTES + 1) == blob.data, "WorkingTreeSourceDiffersFromCommittedBlob:" + name)
    need(git(root, "rev-parse", "HEAD").decode("ascii").strip() == head, "ActiveHeadChangedDuringGuard")
    result.update({"schemaVersion": 1, "milestone": "M2bs", "exactBase": BASE,
                   "activeSha": head, "gitRawBlobComparison": True,
                   "physicalWorkingTreeMatchesCommittedSources": True,
                   "historicalQaSourceSha": BASE, "networkOrGitMutations": 0})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    try:
        result = verify_git(Path(__file__).resolve().parents[3], args.expected_head)
    except (ValueError, OSError, SyntaxError, subprocess.SubprocessError) as error:
        print(canonical({"milestone": "M2bs", "passed": False,
                         "diagnosticClass": type(error).__name__,
                         "rule": str(error) if isinstance(error, GuardError) else "SourceInputReadOrSyntaxFailure",
                         "originalRomVerificationByThisGuard": False}).decode("ascii"))
        return 1
    print(canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
