"""Closed M2bv local Cargo routing; immutable M2bt policies are not patched.

Only generic reviewed environment/toolchain/build-surface checks are reused.
The new target, ownership, commands and complete29-runner input set are separate.
This is an orchestration guard, not an OS sandbox or original-ROM admission.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import os
from pathlib import Path
import secrets
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from original_rom_execution import build_guard as prior

BuildGuardError = prior.BuildGuardError
need, canonical, no_reparse, overlaps, identity = prior.need, prior.canonical, prior.no_reparse, prior.overlaps, prior.identity
TARGET_RELATIVE = Path(".tmp/m2bv-owned/cargo-target")
OWNER_NAME = ".m2bv-target-owner.json"
FEATURE = "p28-word0196-p2-handoff"
TEST_FILTER = "audit::p2_handoff::tests"
HISTORICAL_PHASES = ("m2an", "m2ao", "m2ap", "m2aq", "m2ar", "m2as", "m2at", "m2au",
                     "m2av", "m2aw", "m2ax", "m2ay", "m2az", "m2ba", "m2bb", "m2bc",
                     "m2bd", "m2be", "m2bf", "m2bg", "m2bh", "m2bi")


def protected_paths(repository):
    repository = no_reparse(Path(repository))
    relatives = [*prior.PROTECTED_RELATIVE,
        *(f".tmp/{phase}-cargo-target/release/p28-slice-runner.exe" for phase in HISTORICAL_PHASES),
        ".tmp/m2bt-owned/cargo-target/release/p28-slice-runner.exe",
        ".tmp/m2bt-owned/cargo-target/release/m2bt-original-rom.exe",
        ".tmp/m2bu-owned/cargo-target/release/p28-slice-runner.exe",
        ".tmp/m2bu-owned/cargo-target/release/m2bt-original-rom.exe",
        ".tmp/m2bu-owned/cargo-target/release/m2bu-entry-continuity.exe"]
    return tuple(no_reparse(repository / path) for path in relatives)


def _paths(repository, manifest):
    repository, manifest = no_reparse(Path(repository)), no_reparse(Path(manifest))
    target = no_reparse(repository / TARGET_RELATIVE)
    need(repository.is_dir() and manifest.is_file()
         and manifest == repository / "rust/p28-slice-runner/Cargo.toml", "ExactSourcePathsRequired")
    need(not overlaps(target, manifest.parent), "SourceTargetOverlap")
    for old in (repository / "rust/p28-slice-runner/target", repository / ".tmp/m2bt-owned", repository / ".tmp/m2bu-owned"):
        need(not overlaps(target, no_reparse(old)), "HistoricalTargetOverlap")
    protected = protected_paths(repository)
    need(len(protected) == len(set(protected)) == 29 and all(not overlaps(target, path) for path in protected),
         "ClosedTwentyNineProtectedPathsRequired")
    return repository, manifest, target, protected


def _protected(protected, bindings):
    need(type(bindings) in (list, tuple) and len(bindings) == 29
         and all(type(row) is dict and set(row) == {"path", "bytes", "sha256"} for row in bindings)
         and {row["path"] for row in bindings} == {str(path) for path in protected}, "CompleteProtectedBindingSetRequired")
    observed = [identity(path) for path in protected]
    need({row["path"]: row for row in observed} == {row["path"]: row for row in bindings}, "ProtectedCurrentIdentityChanged")
    return observed


def prepare_target(repository, manifest, protected_bindings):
    repository, manifest, target, protected = _paths(repository, manifest)
    before = _protected(protected, protected_bindings)
    need(not os.path.lexists(target) and target.parent.is_dir(), "FreshExplicitM2bvOwnedTargetRequired")
    owner = {"schemaVersion": 1, "scope": "M2bvIsolatedCargoTarget", "repository": str(repository),
             "target": str(target), "nonce": secrets.token_hex(32), "protectedAtCreation": before}
    target.mkdir()
    with (target / OWNER_NAME).open("xb") as stream:
        stream.write(canonical(owner)); stream.flush(); os.fsync(stream.fileno())
    need(_protected(protected, protected_bindings) == before, "ProtectedChangedDuringTargetPreparation")
    return owner


def check_owner(repository, target, ownership, protected):
    need(type(ownership) is dict and set(ownership) == {"schemaVersion", "scope", "repository", "target", "nonce", "protectedAtCreation"}
         and ownership["schemaVersion"] == 1 and ownership["scope"] == "M2bvIsolatedCargoTarget"
         and ownership["repository"] == str(repository) and ownership["target"] == str(target), "M2bvOwnershipIdentityRequired")
    need(type(ownership["nonce"]) is str and len(ownership["nonce"]) == 64
         and all(value in "0123456789abcdef" for value in ownership["nonce"]), "M2bvOwnershipNonceRequired")
    marker = no_reparse(target / OWNER_NAME)
    need(target.is_dir() and marker.is_file() and prior.strict_json(marker.read_bytes()) == ownership, "ExternalM2bvOwnershipReceiptMismatch")
    protected_nodes = {(path.stat().st_dev, path.stat().st_ino) for path in protected}
    for directory, dirs, files in os.walk(target, followlinks=False):
        for name in dirs + files:
            node = no_reparse(Path(directory) / name)
            info = node.stat()
            need((info.st_dev, info.st_ino) not in protected_nodes, "ProtectedHardlinkInM2bvTarget")


def check_command(command, manifest, target):
    need(len(command) >= 3 and Path(command[0]).name.lower() in {"cargo", "cargo.exe"}
         and command[1] == "+1.85.1" and command[2] in {"test", "build"}, "ClosedM2bvCargoCommandRequired")
    values, flags, filters = {}, set(), []
    arguments = iter(command[3:])
    for item in arguments:
        if item in {"--manifest-path", "--target-dir", "--features", "--bin", "--jobs"}:
            need(item not in values, "DuplicateCargoOption")
            values[item] = next(arguments, None)
            need(values[item] is not None, "CargoOptionValueMissing")
        elif item in {"--release", "--locked", "--offline", "--no-default-features", "--lib"}:
            need(item not in flags, "DuplicateCargoOption")
            flags.add(item)
        elif item == TEST_FILTER:
            need(not filters, "DuplicateCargoTestFilter")
            filters.append(item)
        else:
            raise BuildGuardError("UnreviewedM2bvCargoArgument")
    need({"--release", "--locked", "--offline", "--no-default-features"} <= flags
         and values.get("--jobs") == "1", "PinnedOfflineSingleJobDefaultOffRequired")
    need("--manifest-path" in values and no_reparse(Path(values["--manifest-path"])) == manifest
         and "--target-dir" in values and no_reparse(Path(values["--target-dir"])) == target, "ExplicitM2bvManifestAndTargetRequired")
    need(values.get("--features") in {None, "p28-word0196-audit", "p28-word0196-original-rom", "p28-word0196-entry-continuity", FEATURE}, "UnreviewedM2bvFeature")
    if command[2] == "test":
        need("--bin" not in values and (not filters or ("--lib" in flags and values.get("--features") == FEATURE)), "ClosedM2bvTestSelectionRequired")
        need("--lib" not in flags or bool(filters), "FullSuiteCannotBeSilentlyFilteredToLibrary")
    else:
        need(not filters and "--lib" not in flags and values.get("--bin") in {None, "m2bv-p2-handoff"}
             and ("--bin" not in values or values.get("--features") == FEATURE), "ClosedM2bvBuildSelectionRequired")


def preflight(repository, manifest, ownership, command, cargo_home, expected_manifest_sha256,
              expected_lock_sha256, protected_bindings, environment=None):
    repository, manifest, target, protected = _paths(repository, manifest)
    before = _protected(protected, protected_bindings)
    check_owner(repository, target, ownership, protected)
    need(ownership["protectedAtCreation"] == before, "M2bvOwnershipProtectedBindingChanged")
    check_command(command, manifest, target)
    environment = dict(os.environ if environment is None else environment)
    need(bool(environment.get("CARGO_TARGET_DIR")) and no_reparse(Path(environment["CARGO_TARGET_DIR"])) == target,
         "ExplicitM2bvTargetEnvironmentRequired")
    prior.check_environment(environment, target)
    need(bool(environment.get("CARGO_HOME")) and no_reparse(Path(environment["CARGO_HOME"])) == no_reparse(Path(cargo_home)),
         "ExplicitReviewedCargoHomeRequired")
    need(sha256(manifest.read_bytes()).hexdigest() == expected_manifest_sha256
         and sha256(manifest.with_name("Cargo.lock").read_bytes()).hexdigest() == expected_lock_sha256, "ExactManifestLockIdentityRequired")
    toolchain = prior.review_toolchain(no_reparse(Path(cargo_home)), environment, command)
    surface = prior.review_build_surface(repository, manifest, no_reparse(Path(cargo_home)))
    return {"schemaVersion": 1, "classification": "M2bvOwnedBuildRouting_NotRomAdmissionOrHistoricalStrictPass",
            "repository": str(repository), "target": str(target), "command": list(command),
            "ownershipSha256": sha256(canonical(ownership)).hexdigest(), "protectedCurrentBefore": before,
            "manifestSha256": expected_manifest_sha256, "lockSha256": expected_lock_sha256,
            "toolchain": toolchain, "buildSurface": surface, "doesNotAuthorizeCpuOrRomExecution": True}


def guarded_execute(*, spawn, **arguments):
    checked = dict(arguments)
    checked["environment"] = dict(os.environ if arguments.get("environment") is None else arguments["environment"])
    before = preflight(**checked)
    command = list(before["command"])
    command[0] = before["toolchain"]["proxy"]["path"]
    try:
        return spawn(command, cwd=before["repository"], env=dict(checked["environment"]))
    finally:
        need(preflight(**checked) == before, "M2bvBuildInputsOrProtectedDataChanged")


def ci_cargo_preflight(repository, environment=None):
    """Fresh public routing only; never claims a private29-runner fence PASS."""
    import re
    repository = no_reparse(Path(repository))
    environment = dict(os.environ if environment is None else environment)
    need(environment.get("GITHUB_ACTIONS") == "true"
         and re.fullmatch(r"[0-9a-f]{40}", environment.get("GITHUB_SHA", "")) is not None,
         "ExplicitPublicCiIdentityRequired")
    target = no_reparse(repository / TARGET_RELATIVE)
    need(bool(environment.get("CARGO_TARGET_DIR"))
         and no_reparse(Path(environment["CARGO_TARGET_DIR"])) == target, "ExactPublicCiM2bvTargetEnvironmentRequired")
    for old in (repository / "rust/p28-slice-runner/target", repository / ".tmp/m2bt-owned", repository / ".tmp/m2bu-owned"):
        need(not overlaps(target, no_reparse(old)), "PublicCiHistoricalTargetOverlap")
    expected = {"schemaVersion": 1, "classification": "M2bvPublicCiOwnedCargoTarget",
                "repository": str(repository), "target": str(target), "activeSha": environment["GITHUB_SHA"]}
    marker = no_reparse(target / ".m2bv-public-ci-target.json")
    if target.exists():
        need(target.is_dir(), "PublicCiTargetMustBeDirectory")
        if marker.exists():
            need(marker.is_file() and marker.read_bytes() == canonical(expected), "PublicCiM2bvOwnerMismatch")
        else:
            need(not any(target.iterdir()), "PublicCiUnownedNonemptyTargetRejected")
    else:
        target.mkdir(parents=True, exist_ok=False)
    if not marker.exists():
        with marker.open("xb") as stream:
            stream.write(canonical(expected)); stream.flush(); os.fsync(stream.fileno())
    for directory, dirs, files in os.walk(target, followlinks=False):
        for name in dirs + files:
            no_reparse(Path(directory) / name)
    need(marker.read_bytes() == canonical(expected), "PublicCiM2bvOwnerChanged")
    return {"passed": True, "classification": "PublicCiM2bvRoutingOnly_NotPrivatePreservationPass",
            "activeSha": environment["GITHUB_SHA"], "target": str(target),
            "explicitTargetDirRequired": True, "privateProtectedComparisonClaimed": False,
            "cargoInvocations": 0, "cpuRomExecutions": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-cargo-preflight", action="store_true", required=True)
    parser.parse_args()
    import json
    print(json.dumps(ci_cargo_preflight(Path(__file__).resolve().parents[3]), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
