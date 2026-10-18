"""M2bq three-tree source transition. Pure source checks, no target execution."""
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess
import tomllib

import production_optin_analysis as prior

BASE = "ecc32ea7b65020075f8403a4d4c81cdce4d0f0ad"
LEGACY = "1ceec589ee8586727fb16a39fd15875444d6feab"
RESEARCH = "research/p28-word0196/"
MANIFEST = RESEARCH + "production_composite_source_manifest.json"
CONTRACT = RESEARCH + "production_composite_contract.json"
MODIFIED = frozenset((".github/workflows/build.yml",
                      "rust/p28-slice-runner/src/audit.rs",
                      "rust/p28-slice-runner/src/audit_bus.rs"))
REQUIRED_NEW_PRODUCTION = frozenset(("rust/p28-slice-runner/src/audit_composite.rs",
                                   "rust/p28-slice-runner/src/audit_composite_tests.rs"))
EXPECTED_SEMANTICS = "0b374098144ee1aada6fa3d4e31abb40dd2949fcfed1dadd50a5a523809bbbfa"
EXPECTED_TAIL = "bb66e0f9f769408aa7fdb12e04f73d6a9f3f82d428e6d1954767e816a651b918"
require = prior.require
identity = prior.identity
git = prior.git


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def exact_checkout(root, revision, count):
    root = Path(root).resolve()
    require(git(root, "rev-parse", "HEAD") == revision, "WrongPinnedCheckout:" + revision)
    require(git(root, "diff", "--name-only") == "" and
            git(root, "diff", "--cached", "--name-only") == "", "DirtyPinnedTrackedTree")
    result = subprocess.run(["git", "-C", str(root), "ls-tree", "-rz", "--full-tree", revision],
                            capture_output=True, check=False)
    require(result.returncode == 0, "PinnedGitBlobInventoryFailed")
    rows = []
    for value in result.stdout.split(b"\0"):
        if not value:
            continue
        metadata, raw_name = value.split(b"\t", 1)
        mode, kind, digest = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8")
        require(mode in ("100644", "100755") and kind == "blob", "OnlyRegularPinnedBlobs")
        raw = (root / name).read_bytes()
        header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
        require(sha1(header + raw).hexdigest() == digest, "PinnedBytesNotActualCommittedBlob:" + name)
        rows.append(identity(root, name))
    require(len(rows) == count and len({row["path"] for row in rows}) == count,
            "ExactPinnedTrackedCountRequired:" + str(count))
    return sorted(rows, key=lambda row: row["path"])


def source_checks(active, pinned, legacy):
    active, pinned, legacy = (Path(value).resolve() for value in (active, pinned, legacy))
    require(len({active, pinned, legacy}) == 3, "ThreeDistinctSourceTreesRequired")
    pinned_rows = exact_checkout(pinned, BASE, 874)
    legacy_rows = exact_checkout(legacy, LEGACY, 851)
    # The original validator still checks its actual exact source tree. It is
    # not patched or pointed at the new active tree with mutable hash aliases.
    pinned_proof, _ = prior.source_checks(pinned, legacy)
    git(active, "merge-base", "--is-ancestor", BASE, "HEAD")
    manifest = json.loads((active / MANIFEST).read_bytes())
    contract = json.loads((active / CONTRACT).read_bytes())
    require(manifest["milestone"] == contract["milestone"] == "M2bq"
            and manifest["exactBase"] == contract["exactBase"] == BASE
            and manifest["exactM2bo"] == LEGACY, "ThreeExplicitImmutableVersionRolesRequired")
    require(manifest["pinnedM2bpSources"] == pinned_rows
            and manifest["pinnedM2boSources"] == legacy_rows, "FullPinnedSourceBindingsRequired")
    require(contract["sourceManifest"] == identity(active, MANIFEST), "NewManifestContractBinding")
    require(manifest["identityCycleExclusions"] == [MANIFEST, CONTRACT], "OnlyTwoSelfCycleExclusions")
    variants = {row["path"]: row for row in prior.representation_specifications()}
    require(manifest["representationVariants"] == prior.representation_specifications(),
            "OnlyOriginalThreeExactXmlRepresentations")
    changes = {row["path"]: row for row in manifest["authorizedModifiedFiles"]}
    require(set(changes) == MODIFIED and len(changes) == len(manifest["authorizedModifiedFiles"]),
            "OnlyTwoAuditComponentsAndWorkflowMayChange")
    old = {row["path"]: row for row in pinned_rows}
    for name, expected in old.items():
        actual = identity(active, name)
        if name in changes:
            row = changes[name]
            require(row["old"] == expected and row["new"] == actual
                    and row["authorizedReason"] and row["changedFunctions"]
                    and row["semanticImpactClassification"], "ExactNewSourceTransitionRequired:" + name)
        elif name in variants:
            pair = variants[name]
            require(actual in (pair["committedGitIdentity"], pair["originalProtectedFilesystemIdentity"]),
                    "UndeclaredXmlRepresentation:" + name)
            raw = (pinned / name).read_bytes()
            require((active / name).read_bytes() in
                    (raw, prior.reconstruct_protected_representation(raw, pair)),
                    "ExactXmlByteRelationRequired:" + name)
        else:
            require(actual == expected, "HistoricalM2bpSourceModified:" + name)
    paths = manifest["newPublicPaths"]
    require(len(paths) == len(set(paths)) and not set(paths) & set(old), "ClosedGenuinelyNewPathsRequired")
    require(REQUIRED_NEW_PRODUCTION <= set(paths), "NewClosedCompositeComponentsRequired")
    for name in paths:
        require(name.startswith((RESEARCH, "docs/", "rust/p28-slice-runner/src/audit_composite"))
                and name == Path(name).as_posix() and ".." not in Path(name).parts
                and Path(name).suffix in (".rs", ".py", ".json", ".md", ".toml", ".lock"),
                "NarrowPublicSourcePathRequired:" + name)
    bindings = manifest["newSourceBindings"]
    require(len(bindings) == len(paths) - 2
            and {row["path"] for row in bindings} == set(paths) - {MANIFEST, CONTRACT},
            "CompleteNewSourceBindingsRequired")
    for row in bindings:
        require(identity(active, row["path"]) == row, "NewSourceChanged:" + row["path"])
    actual_new = {name for name in git(active, "ls-files", "--others", "--exclude-standard").splitlines()
                  if name.startswith((RESEARCH, "docs/", "rust/", ".github/"))}
    tracked = set(git(active, "ls-files").splitlines())
    require(tracked | actual_new == set(old) | set(paths),
            "NoUndeclaredTrackedOrResearchPublicSourceMembership")
    package = tomllib.loads((active / "rust/p28-slice-runner/Cargo.toml").read_text(encoding="utf-8"))
    require(package["package"]["version"] == "0.43.0" and package["features"]["default"] == []
            and package["features"]["p28-word0196-audit"] == [], "UnchangedDefaultOffFeatureAndRunner")
    proof = prior.semantic_body_proof(active, legacy)
    require(proof["semanticBodySha256"] == EXPECTED_SEMANTICS
            and proof["postDecodeTailSha256"] == EXPECTED_TAIL,
            "SharedProductionInstructionBodyMustRemainExact")
    # Comparing the full unchanged exec file with M2bp is stronger than a
    # selectively extracted instruction body for this particular transition.
    require(identity(active, "rust/p28-slice-runner/src/exec.rs") ==
            identity(pinned, "rust/p28-slice-runner/src/exec.rs"), "M2bpFullExecFileMustStayExact")
    old_desktop = (pinned / ".github/workflows/build.yml").read_bytes().split(b"\n  desktop-windows:", 1)
    new_desktop = (active / ".github/workflows/build.yml").read_bytes().split(b"\n  desktop-windows:", 1)
    require(len(old_desktop) == len(new_desktop) == 2 and old_desktop[1] == new_desktop[1],
            "EntireDesktopJobUnchangedIncludingTimeoutAssertionsAndCleanup")
    return {"milestone": "M2bq", "passed": True, "classification": "StaticThreeVersionSourceTransition_NotRuntimeQA",
            "exactBase": BASE, "exactM2bo": LEGACY, "pinnedM2bpProof": pinned_proof,
            "pinnedM2bpSources": pinned_rows, "pinnedM2boSources": legacy_rows,
            "authorizedModifiedFiles": manifest["authorizedModifiedFiles"],
            "activeNewSourceBindings": bindings, "manifest": identity(active, MANIFEST),
            "contract": identity(active, CONTRACT), "semanticBodyProof": proof,
            "untrackedOutsideSourcePrefixes": "SeparateFullProtectedAndPrivacyGate_NotClaimedByThisStaticCheck",
            "oldSourcePinsModified": False, "productionCompositeExecutions": 0,
            "firmwareReady": False}, contract
