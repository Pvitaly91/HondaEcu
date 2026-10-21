"""M2br four-version source transition; never target execution or admission.

The canonical source proof uses explicitly declared committed-content roles.
Actual local filesystem representations are separately protected byte-for-byte;
only the three historical, literal XML byte pairs have two accepted roles.
This is not a newline-normalization permission or a runtime oracle.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tomllib

import production_composite_analysis as bq
import production_optin_analysis as bp

BASE = "d5431f446d1951ee311aedc7961139ba28224a9f"
PINNED_BP = "ecc32ea7b65020075f8403a4d4c81cdce4d0f0ad"
PINNED_BO = "1ceec589ee8586727fb16a39fd15875444d6feab"
BRANCH = "codex/p28-word0196-synthetic-handoff-continuation-m2br"
RESEARCH = "research/p28-word0196/"
MANIFEST = RESEARCH + "production_transfer_source_manifest.json"
CONTRACT = RESEARCH + "production_transfer_contract.json"
ALLOWED_MODIFIED = frozenset((
    ".github/workflows/build.yml",
    "rust/p28-slice-runner/src/audit.rs",
    "rust/p28-slice-runner/src/audit_bus.rs",
    "rust/p28-slice-runner/src/audit_composite.rs",
))
REQUIRED_NEW_PRODUCTION = frozenset((
    "rust/p28-slice-runner/src/audit_transfer.rs",
    "rust/p28-slice-runner/src/audit_transfer_tests.rs",
))
UNCHANGED_ENGINE = (
    "rust/p28-slice-runner/src/cpu.rs", "rust/p28-slice-runner/src/bus.rs",
    "rust/p28-slice-runner/src/decoder.rs", "rust/p28-slice-runner/src/full_decoder.rs",
    "rust/p28-slice-runner/src/exec.rs", "rust/p28-slice-runner/src/operand.rs",
    "rust/p28-slice-runner/src/audit_sha256.rs", "rust/p28-slice-runner/src/audit_tests.rs",
    "rust/p28-slice-runner/src/audit_composite_tests.rs", "rust/p28-slice-runner/src/lib.rs",
    "rust/p28-slice-runner/src/runner.rs", "rust/p28-slice-runner/src/protocol.rs",
    "rust/p28-slice-runner/src/main.rs", "rust/p28-slice-runner/Cargo.toml",
    "rust/p28-slice-runner/Cargo.lock",
)
require = bp.require
identity = bp.identity


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def git(root, *arguments):
    child = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *arguments],
                           stdin=subprocess.DEVNULL, capture_output=True, check=False)
    require(child.returncode == 0 and len(child.stdout) <= 8 * 1024**2
            and len(child.stderr) <= 1024**2, "BoundedReadOnlyGit:" + " ".join(arguments))
    return child.stdout.decode("utf-8", "strict").rstrip("\r\n")


def shared_checked_step(raw):
    start = raw.index(b"    fn checked_step(")
    end = raw.index(b"\n    pub fn report(", start)
    return raw[start:end]


def source_checks(active, pinned_bq, pinned_bp, legacy_bo):
    active, pinned_bq, pinned_bp, legacy_bo = (Path(p).resolve() for p in
                                             (active, pinned_bq, pinned_bp, legacy_bo))
    require(len({active, pinned_bq, pinned_bp, legacy_bo}) == 4, "FourDistinctImmutableVersionRoles")
    bq_rows = bq.exact_checkout(pinned_bq, BASE, 898)
    bp_rows = bq.exact_checkout(pinned_bp, PINNED_BP, 874)
    bo_rows = bq.exact_checkout(legacy_bo, PINNED_BO, 851)
    bq_proof, _ = bq.source_checks(pinned_bq, pinned_bp, legacy_bo)
    git(active, "merge-base", "--is-ancestor", BASE, "HEAD")
    manifest = json.loads((active / MANIFEST).read_bytes())
    contract = json.loads((active / CONTRACT).read_bytes())
    require(manifest["milestone"] == contract["milestone"] == "M2br"
            and manifest["exactBase"] == contract["exactBase"] == BASE
            and manifest["exactM2bp"] == PINNED_BP and manifest["exactM2bo"] == PINNED_BO,
            "FourExplicitPinnedVersions_NoHistoricalAliases")
    require(manifest["pinnedM2bqSources"] == bq_rows and manifest["pinnedM2bpSources"] == bp_rows
            and manifest["pinnedM2boSources"] == bo_rows, "Complete898_874_851PinnedSourceBindings")
    require(contract["sourceManifest"] == identity(active, MANIFEST)
            and manifest["identityCycleExclusions"] == [MANIFEST, CONTRACT], "OnlyTwoExplicitIdentityCycleExclusions")
    variants = {row["path"]: row for row in bp.representation_specifications()}
    require(manifest["representationVariants"] == bp.representation_specifications(), "ThreeHistoricalLiteralXmlPairsOnly")
    old = {row["path"]: row for row in bq_rows}
    changes = {row["path"]: row for row in manifest["authorizedModifiedFiles"]}
    require(set(changes) <= ALLOWED_MODIFIED and len(changes) == len(manifest["authorizedModifiedFiles"])
            and {".github/workflows/build.yml", "rust/p28-slice-runner/src/audit.rs",
                 "rust/p28-slice-runner/src/audit_bus.rs"} <= set(changes), "ClosedMinimalOptInChangeScope")
    committed_roles = []
    for name, before in sorted(old.items()):
        actual = identity(active, name)
        if name in changes:
            row = changes[name]
            require(row["old"] == before and row["new"] == actual and row["authorizedReason"]
                    and row["changedFunctions"] and row["semanticImpactClassification"],
                    "ExactAuthorizedOldNewFunctionImpact:" + name)
            committed_roles.append(actual)
        elif name in variants:
            pair = variants[name]
            require(actual in (pair["committedGitIdentity"], pair["originalProtectedFilesystemIdentity"]),
                    "NoGeneralXmlNormalization:" + name)
            pinned_bytes = (pinned_bq / name).read_bytes()
            require((active / name).read_bytes() in
                    (pinned_bytes, bp.reconstruct_protected_representation(pinned_bytes, pair)),
                    "ExactThreeLiteralByteRelations:" + name)
            # Both fixed representation identities are retained in the manifest.
            # This row has a declared COMMITTED role, not the local raw-file role.
            committed_roles.append(pair["committedGitIdentity"])
        else:
            require(actual == before, "HistoricalSourceOrOracleModified:" + name)
            committed_roles.append(actual)
    new_paths = manifest["newPublicPaths"]
    require(len(new_paths) == len(set(new_paths)) and not set(new_paths) & set(old)
            and REQUIRED_NEW_PRODUCTION <= set(new_paths), "ClosedGenuinelyNewTransferPaths")
    for name in new_paths:
        require(type(name) is str and name == Path(name).as_posix() and ".." not in Path(name).parts
                and name.startswith((RESEARCH + "production_transfer_", RESEARCH + "validate_production_transfer.py",
                                     RESEARCH + "rust-production-transfer/", "docs/M2BR_",
                                     "rust/p28-slice-runner/src/audit_transfer"))
                and Path(name).suffix in (".py", ".rs", ".json", ".md", ".toml", ".lock"),
                "NarrowNewResearchAndOptInSourcePath:" + name)
    bindings = manifest["newSourceBindings"]
    require(len(bindings) == len(new_paths) - 2 and {row["path"] for row in bindings}
            == set(new_paths) - {MANIFEST, CONTRACT}, "EveryNewSourceBoundBeforeRuntime")
    for row in bindings:
        require(identity(active, row["path"]) == row, "NewSourceChanged:" + row["path"])
    tracked = set(git(active, "ls-files").splitlines())
    untracked = {name for name in git(active, "ls-files", "--others", "--exclude-standard").splitlines()
                 if name.startswith((RESEARCH, "docs/", "rust/", ".github/"))}
    require(tracked | untracked == set(old) | set(new_paths), "NoUndeclaredPublicMembership")
    package = tomllib.loads((active / "rust/p28-slice-runner/Cargo.toml").read_text(encoding="utf-8"))
    require(package["package"]["version"] == "0.43.0" and package["features"]["default"] == []
            and package["features"]["p28-word0196-audit"] == [], "RunnerAndDefaultOffFeaturePreserved")
    for name in UNCHANGED_ENGINE:
        require(identity(active, name) == old[name], "ProductionInstructionEngineOrLegacyTestsChanged:" + name)
    original_checked = shared_checked_step((pinned_bq / "rust/p28-slice-runner/src/audit.rs").read_bytes())
    current_checked = shared_checked_step((active / "rust/p28-slice-runner/src/audit.rs").read_bytes())
    require(original_checked == current_checked, "EntireSharedCheckedDecoderExecBodyByteExact")
    old_desktop = (pinned_bq / ".github/workflows/build.yml").read_bytes().split(b"\n  desktop-windows:", 1)
    new_desktop = (active / ".github/workflows/build.yml").read_bytes().split(b"\n  desktop-windows:", 1)
    require(len(old_desktop) == len(new_desktop) == 2 and old_desktop[1] == new_desktop[1],
            "EntireDesktopJobUnchanged_NoTimeoutOrAssertionOrOptionBChange")
    committed_roles.extend(bindings)
    committed_roles.extend((identity(active, MANIFEST), identity(active, CONTRACT)))
    require(len(committed_roles) == len(old) + len(new_paths)
            and len({row["path"] for row in committed_roles}) == len(committed_roles),
            "CompleteCurrentCommittedContentRolesIncludingBothCycleExcludedSources")
    return {"milestone": "M2br", "passed": True,
            "classification": "StaticFourVersionSourceTransition_NotCpuExecutionOrQaAcceptance",
            "exactBase": BASE, "exactM2bp": PINNED_BP, "exactM2bo": PINNED_BO,
            "pinnedM2bqProof": bq_proof, "pinnedM2bqSources": bq_rows,
            "pinnedM2bpSources": bp_rows, "pinnedM2boSources": bo_rows,
            "authorizedModifiedFiles": manifest["authorizedModifiedFiles"], "activeNewSourceBindings": bindings,
            "activeCommittedContentRoles": sorted(committed_roles, key=lambda row: row["path"]),
            "activePublicSourceCount": len(old) + len(new_paths), "representationVariants": list(variants.values()),
            "physicalRepresentationAuditRole": "SeparatelyBoundFullProtectedFilesystem_NotCanonicalHostMetadata",
            "sourceRoleSelectionDeclaredBeforeRuntime": True, "normalizationWrites": 0,
            "manifest": identity(active, MANIFEST), "contract": identity(active, CONTRACT),
            "sharedCheckedStepSha256": sha256(current_checked).hexdigest(),
            "legacyEngineFilesByteExact": list(UNCHANGED_ENGINE), "desktopJobByteExact": True,
            "sourceScopes": ["HistoricalPinnedBaselineQA", "ActiveTreeDefaultModeQA",
                             "ActiveTreeOneStepCompatibility", "ProductionCompositeCompatibilityQA",
                             "ProductionSyntheticTransferQA"],
            "oldSourcePinsModified": False, "targetCpuExecutions": 0, "firmwareReady": False}, contract
