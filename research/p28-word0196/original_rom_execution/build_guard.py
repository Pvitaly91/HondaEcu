"""M2bt local Cargo output-routing preflight; no Cargo invocation on import/CLI.

This is a closed orchestration guard, not an OS sandbox or evidence of recovery.
The caller separately authenticates the source revision and restoration policy.
An external ownership receipt must be retained in the recovery checkpoint. A
matching target marker alone never establishes ownership after RESUME.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import sys
import tomllib
from typing import Callable, Mapping, Sequence

sys.dont_write_bytecode = True
TARGET_RELATIVE = Path(".tmp/m2bt-owned/cargo-target")
OWNER_NAME = ".m2bt-target-owner.json"
ORIGINAL_TEST_FILTER = "audit::original_rom::tests"
PROTECTED_RELATIVE = (
    "rust/p28-slice-runner/target/release/p28-slice-runner.exe",
    "rust/p28-slice-runner/target/release/deps/p28_slice_runner.exe",
)
# Full sources were reviewed: quote/serde/serde_json emit configuration and
# query rustc; proc-macro2's only writes/removal are OUT_DIR/probe. No arbitrary
# new build script is admitted merely because it appears in Cargo.lock.
REVIEWED_BUILD_SCRIPTS = frozenset({
    "baeb20b52f6b536be8657a566591a507bb2e34a45cf8baa42b135510a0c3c729",
    "cd6808c02e476b09a520105e2c6f6d325cccb1ecd542cbbcc836a0ae6f6fb0f1",
    "8bce1d4e3594972da27e54bac89058e1a73024205535d58008f7d0db5c4b4461",
    "1630d0bbfc936b0975d840cec5cfb5910d861b6afeeeeabe11000a2c202d571d",
})


class BuildGuardError(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise BuildGuardError(code)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def strict_json(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "DuplicateReceiptKey")
            result[key] = value
        return result
    need(len(data) <= 65536, "ReceiptTooLarge")
    value = json.loads(data, object_pairs_hook=pairs)
    need(isinstance(value, dict), "ReceiptObjectRequired")
    return value


def identity(path: Path) -> dict:
    need(path.is_file(), "ProtectedFileMissing")
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha256(data).hexdigest()}


def no_reparse(path: Path) -> Path:
    """Inspect existing ancestors before resolve; junctions are not ordinary dirs."""
    need(path.is_absolute() and ".." not in path.parts, "AbsoluteNonTraversalPathRequired")
    for item in reversed((path, *path.parents)):
        if not os.path.lexists(item):
            continue
        info = item.lstat()
        need(not stat.S_ISLNK(info.st_mode), "SymlinkPathRejected")
        need(not getattr(info, "st_file_attributes", 0) & 0x400, "ReparsePointRejected")
    return path.resolve(strict=False)


def overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def paths(repository: Path, target: Path, manifest: Path, extra_protected: Sequence[Path] = ()) -> tuple:
    repository = no_reparse(repository)
    target = no_reparse(target)
    manifest = no_reparse(manifest)
    need(repository.is_dir() and manifest.is_file(), "SourcePathsMissing")
    need(target == repository / TARGET_RELATIVE, "WrongOwnedTarget")
    need(repository in manifest.parents, "SourceOutsideRepository")
    need(not overlaps(target, manifest.parent), "SourceTargetOverlap")
    protected = tuple(dict.fromkeys(no_reparse(repository / p) for p in PROTECTED_RELATIVE))
    protected += tuple(no_reparse(p) for p in extra_protected if no_reparse(p) not in protected)
    need(all(not overlaps(target, p) for p in protected), "ProtectedTargetOverlap")
    need(all(not overlaps(manifest.parent, p) or p in (repository / PROTECTED_RELATIVE[0], repository / PROTECTED_RELATIVE[1])
             for p in protected), "UnexpectedSourceProtectedOverlap")
    # The standard crate may contain its protected old target; it is never the
    # output destination and the command must always name the separate target.
    return repository, target, manifest, protected


def prepare_target(repository: Path, manifest: Path, extra_protected: Sequence[Path] = ()) -> dict:
    repository, target, _, protected = paths(repository, repository / TARGET_RELATIVE, manifest, extra_protected)
    need(not os.path.lexists(target), "ExistingUnownedTargetRejected")
    need(target.parent.is_dir(), "ExplicitOwnedParentRequired")
    before = [identity(p) for p in protected]
    record = {"schemaVersion": 1, "scope": "M2btIsolatedCargoTarget", "repository": str(repository),
              "target": str(target), "nonce": secrets.token_hex(32), "protectedAtCreation": before}
    target.mkdir()  # Exclusive: never adopt, empty, delete, or clean an old directory.
    with (target / OWNER_NAME).open("xb") as stream:
        stream.write(canonical(record))
        stream.flush()
        os.fsync(stream.fileno())
    need(before == [identity(p) for p in protected], "ProtectedMutationDuringPreparation")
    return record


def check_owner(repository: Path, target: Path, ownership: dict, protected: Sequence[Path]) -> None:
    need(set(ownership) == {"schemaVersion", "scope", "repository", "target", "nonce", "protectedAtCreation"},
         "OwnershipReceiptSchemaRejected")
    need(ownership["schemaVersion"] == 1 and ownership["scope"] == "M2btIsolatedCargoTarget"
         and ownership["repository"] == str(repository) and ownership["target"] == str(target),
         "OwnershipReceiptIdentityRejected")
    nonce = ownership["nonce"]
    need(isinstance(nonce, str) and len(nonce) == 64 and all(c in "0123456789abcdef" for c in nonce),
         "OwnershipNonceRejected")
    need(target.is_dir(), "OwnedTargetMissing")
    marker = no_reparse(target / OWNER_NAME)
    need(marker.is_file() and strict_json(marker.read_bytes()) == ownership, "OwnershipMarkerMismatch")
    protected_nodes = {(p.stat().st_dev, p.stat().st_ino) for p in protected}
    # Only the newly owned target is inspected, not historical storage/cache.
    for root, directories, files in os.walk(target, followlinks=False):
        for name in directories + files:
            item = no_reparse(Path(root) / name)
            info = item.stat()
            need((info.st_dev, info.st_ino) not in protected_nodes, "ProtectedHardlinkInTarget")


def check_environment(environment: Mapping[str, str], target: Path) -> None:
    routing = {"CARGO_TARGET_DIR", "CARGO_BUILD_TARGET_DIR"}
    exact_denied = {"RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTDOCFLAGS", "RUSTC", "RUSTDOC",
                    "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTC_BOOTSTRAP", "RUSTC_STAGE",
                    "OUT_DIR", "CARGO_BUILD_BUILD_DIR", "CARGO_BUILD_TARGET", "CARGO_INSTALL_ROOT",
                    "LINK", "_LINK_", "CL", "_CL_", "RUSTUP_DIST_SERVER", "RUSTUP_UPDATE_ROOT"}
    for key, value in environment.items():
        key = key.upper()
        if not value:
            continue
        if key in routing:
            need(no_reparse(Path(value)) == target, "ConflictingCargoTargetEnvironment")
        elif key in exact_denied or key.startswith(("CARGO_TARGET_", "CARGO_ALIAS_", "CARGO_BUILD_RUST", "CARGO_PROFILE_")):
            raise BuildGuardError("UnreviewedBuildEnvironment:" + key)


def review_toolchain(cargo_home: Path, environment: Mapping[str, str], command: Sequence[str]) -> dict:
    need(bool(environment.get("RUSTUP_HOME")), "ExplicitRustupHomeRequired")
    rustup_home = no_reparse(Path(environment["RUSTUP_HOME"]))
    need(sys.platform in {"win32", "linux"}, "UnreviewedBuildHost")
    triple = "x86_64-pc-windows-msvc" if sys.platform == "win32" else "x86_64-unknown-linux-gnu"
    suffix = ".exe" if sys.platform == "win32" else ""
    need(environment.get("RUSTUP_TOOLCHAIN", "1.85.1") in {"1.85.1", "1.85.1-" + triple},
         "ConflictingRustupToolchain")
    toolchain = no_reparse(rustup_home / ("toolchains/1.85.1-" + triple))
    rustc, cargo = toolchain / ("bin/rustc" + suffix), toolchain / ("bin/cargo" + suffix)
    proxy = no_reparse(cargo_home / ("bin/cargo" + suffix))
    requested = command[0]
    resolved = requested if Path(requested).is_absolute() else shutil.which(requested, path=environment.get("PATH", ""))
    need(resolved is not None and no_reparse(Path(resolved)) == proxy, "UnreviewedCargoExecutable")
    distribution = no_reparse(toolchain / "lib/rustlib/multirust-channel-manifest.toml")
    need(distribution.is_file(), "PinnedToolchainManifestMissing")
    manifest = tomllib.loads(distribution.read_text(encoding="utf-8"))
    need(manifest.get("pkg", {}).get("rustc", {}).get("version") == "1.85.1 (4eb161250 2025-03-15)",
         "PinnedToolchainVersionMismatch")
    return {"currentHostTriple": triple, "historicalEnvironmentIdentityClaimed": False,
            "rustupHome": str(rustup_home), "proxy": identity(proxy),
            "rustc": identity(no_reparse(rustc)), "cargo": identity(no_reparse(cargo)),
            "distributionManifest": identity(distribution)}


def check_command(command: Sequence[str], manifest: Path, target: Path) -> None:
    need(len(command) >= 3 and Path(command[0]).name.lower() in {"cargo", "cargo.exe"}
         and command[1] == "+1.85.1" and command[2] in {"test", "build"}, "ClosedCargoCommandRequired")
    values, flags, filters = {}, set(), []
    items = iter(command[3:])
    for item in items:
        if item in {"--manifest-path", "--target-dir", "--bin", "--features", "--jobs"}:
            need(item not in values, "DuplicateCargoOption")
            value = next(items, None)
            need(value is not None, "CargoOptionValueMissing")
            values[item] = value
        elif item in {"--release", "--locked", "--offline", "--lib", "--no-default-features"}:
            need(item not in flags, "DuplicateCargoOption")
            flags.add(item)
        elif item == ORIGINAL_TEST_FILTER:
            need(not filters, "DuplicateCargoTestFilter")
            filters.append(item)
        else:
            raise BuildGuardError("UnreviewedCargoArgument")
    need({"--release", "--locked", "--offline"} <= flags, "PinnedOfflineReleaseRequired")
    need("--manifest-path" in values and no_reparse(Path(values["--manifest-path"])) == manifest,
         "ExplicitExactManifestRequired")
    need("--target-dir" in values and no_reparse(Path(values["--target-dir"])) == target,
         "ExplicitOwnedTargetRequired")
    need(values.get("--jobs", "1") == "1", "SingleJobRequired")
    need(values.get("--features") in {None, "p28-word0196-audit", "p28-word0196-original-rom"},
         "UnreviewedCargoFeatures")
    if command[2] == "test":
        need("--bin" not in values, "ClosedTestSelectionRequired")
        # Full default/old-audit/new-feature suites are safe only because the
        # exact owned output target has already been required. One named library
        # filter supports the initial nine-test M2bt phase; no arbitrary filters
        # or test-harness output switches are accepted.
        need(not filters or ("--lib" in flags and values.get("--features") == "p28-word0196-original-rom"),
             "ClosedOriginalLibraryFilterRequired")
    else:
        need(not filters and "--lib" not in flags and values.get("--bin") in {None, "m2bt-original-rom"},
             "ClosedBuildSelectionRequired")


def configuration_candidates(repository: Path, manifest: Path, cargo_home: Path) -> list[Path]:
    candidates = set()
    for start in (repository, manifest.parent):
        for directory in (start, *start.parents):
            candidates.update((directory / ".cargo/config", directory / ".cargo/config.toml"))
    candidates.update((cargo_home / "config", cargo_home / "config.toml"))
    return sorted(candidates, key=str)


def review_build_surface(repository: Path, manifest: Path, cargo_home: Path) -> dict:
    for start in (repository, manifest.parent):
        for directory in (start, *start.parents):
            candidate = no_reparse(directory / "Cargo.toml")
            need(candidate == manifest or not candidate.exists(), "UnreviewedAncestorCargoManifest")
    config_paths = configuration_candidates(repository, manifest, cargo_home)
    for path in config_paths:
        no_reparse(path)
        need(not path.exists(), "UnreviewedCargoConfiguration")
    package = tomllib.loads(manifest.read_text(encoding="utf-8"))
    need("workspace" not in package and "patch" not in package and "replace" not in package,
         "UnreviewedWorkspaceOrReplacement")
    need(package.get("package", {}).get("build") in (None, False)
         and not (manifest.parent / "build.rs").exists(), "ProjectBuildScriptRejected")
    for section in ("dependencies", "build-dependencies", "dev-dependencies"):
        for dependency in package.get(section, {}).values():
            need(not isinstance(dependency, dict) or not ({"path", "git"} & set(dependency)),
                 "UnreviewedDependencySource")
    lock = tomllib.loads(manifest.with_name("Cargo.lock").read_text(encoding="utf-8"))
    scripts = []
    for item in lock.get("package", []):
        if "source" not in item:
            need(item["name"] == package["package"]["name"], "UnreviewedLocalDependency")
            continue
        need(item["source"] == "registry+https://github.com/rust-lang/crates.io-index", "UnreviewedRegistry")
        roots = list((cargo_home / "registry/src").glob("*/" + item["name"] + "-" + item["version"]))
        need(len(roots) == 1, "LockedDependencyCacheMissingOrAmbiguous")
        root = no_reparse(roots[0])
        dependency = tomllib.loads((root / "Cargo.toml").read_text(encoding="utf-8"))
        script = dependency.get("package", {}).get("build")
        if script is None and (root / "build.rs").exists():
            script = "build.rs"
        if script is False or script is None:
            continue
        need(script == "build.rs", "CustomDependencyBuildPathRejected")
        script_path = no_reparse(root / script)
        digest = sha256(script_path.read_bytes()).hexdigest()
        need(digest in REVIEWED_BUILD_SCRIPTS, "UnreviewedDependencyBuildScript")
        scripts.append({"package": item["name"], "version": item["version"], "sha256": digest,
                        "outputScope": "CargoOutDirOnlyOrNoWrites"})
    return {"configurationFilesPresent": [], "projectBuildScript": None, "dependencyBuildScripts": scripts}


def preflight(repository: Path, manifest: Path, ownership: dict, command: Sequence[str],
              cargo_home: Path, expected_manifest_sha256: str, expected_lock_sha256: str,
              environment: Mapping[str, str] | None = None, extra_protected: Sequence[Path] = ()) -> dict:
    repository, target, manifest, protected = paths(repository, repository / TARGET_RELATIVE, manifest, extra_protected)
    check_owner(repository, target, ownership, protected)
    check_command(command, manifest, target)
    environment = os.environ if environment is None else environment
    check_environment(environment, target)
    need(bool(environment.get("CARGO_HOME"))
         and no_reparse(Path(environment["CARGO_HOME"])) == no_reparse(cargo_home),
         "ExplicitReviewedCargoHomeRequired")
    need(sha256(manifest.read_bytes()).hexdigest() == expected_manifest_sha256, "ManifestIdentityMismatch")
    need(sha256(manifest.with_name("Cargo.lock").read_bytes()).hexdigest() == expected_lock_sha256,
         "LockIdentityMismatch")
    toolchain = review_toolchain(no_reparse(cargo_home), environment, command)
    surface = review_build_surface(repository, manifest, no_reparse(cargo_home))
    return {"schemaVersion": 1, "classification": "IsolatedBuildRoutingPreflight_NotHistoricalPreservationPass",
            "repository": str(repository), "target": str(target), "manifest": str(manifest), "command": list(command),
            "ownershipSha256": sha256(canonical(ownership)).hexdigest(),
            "manifestSha256": expected_manifest_sha256, "lockSha256": expected_lock_sha256,
            "protectedCurrentBefore": [identity(p) for p in protected], "buildSurface": surface,
            "toolchain": toolchain,
            "doesNotAuthorizeCpuOrRomExecution": True}


def guarded_execute(*, spawn: Callable, **arguments):
    """Explicit caller-supplied execution only; tests use a non-executing spy.

    Caller authorization and historic-source authenticity are separate gates.
    Even an exception must not hide a changed protected identity.
    """
    checked = dict(arguments)
    supplied_environment = arguments.get("environment")
    checked["environment"] = dict(os.environ if supplied_environment is None else supplied_environment)
    receipt = preflight(**checked)
    try:
        command = list(receipt["command"])
        command[0] = receipt["toolchain"]["proxy"]["path"]
        return spawn(command, cwd=receipt["repository"], env=dict(checked["environment"]))
    finally:
        after = preflight(**checked)
        need(after == receipt, "BuildInputsOrProtectedIdentityChanged")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prepare-target", action="store_true")
    parser.add_argument("--ownership-receipt", type=Path)
    parser.add_argument("--cargo-home", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--lock-sha256")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.prepare_target:
        need(not args.command and args.ownership_receipt is None, "PreparationOnly")
        result = prepare_target(args.repository, args.manifest)
    else:
        need(args.ownership_receipt is not None and args.cargo_home is not None
             and args.manifest_sha256 and args.lock_sha256, "PreflightArgumentsMissing")
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        result = preflight(args.repository, args.manifest, strict_json(args.ownership_receipt.read_bytes()), command,
                           args.cargo_home, args.manifest_sha256, args.lock_sha256)
    sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildGuardError, OSError, ValueError) as error:
        raise SystemExit("M2bt build preflight refused: " + str(error))
