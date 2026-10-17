"""Version-aware source transition. No compiler, decoder or CPU is invoked."""
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess
import tomllib

BASE = "1ceec589ee8586727fb16a39fd15875444d6feab"
RESEARCH = "research/p28-word0196/"
MANIFEST = RESEARCH + "production_optin_source_manifest.json"
CONTRACT = RESEARCH + "production_optin_capabilities_contract.json"
MODIFIED = frozenset((".github/workflows/build.yml", "rust/p28-slice-runner/Cargo.toml",
                      "rust/p28-slice-runner/src/lib.rs", "rust/p28-slice-runner/src/bus.rs",
                      "rust/p28-slice-runner/src/exec.rs", "rust/p28-slice-runner/src/decoder.rs"))

# Exact immutable, independently audited source representations. These are not
# generic newline normalization rules and do not modify either source tree.
REPRESENTATIONS = {
    "src/HondaEcu.Cli/HondaEcu.Cli.csproj": (
        695, "b5e9372b53d8836656780a395a17584d50df0007d128b37815874afd19fb561d",
        705, "2ad76dfce17ac60cb5ce90dfaff6cd0170d9c54b7784850fd27e819a9a3bacc2",
        23, (0, 1, 12, 13, 14, 15, 16, 20, 21, 22)),
    "src/HondaEcu.Core/HondaEcu.Core.csproj": (
        209, "b540adba501c839ec1d75143e106dfb9dd5593d9ff7cdd036af82c25c9387053",
        218, "e151f959964eb450a5b86b72765e3f9c505645fa9516eae485743d2b43911c8e",
        9, tuple(range(9))),
    "tests/HondaEcu.Cli.Tests/HondaEcu.Cli.Tests.csproj": (
        839, "e9868bd94f0fcfd57b3efefd967a23717318a6087b80145d238fbd74288330a4",
        867, "7b0bfab120eb271a0cd67a0ec2f850c00881a21b3a47b681023e8b225bd032a7",
        28, tuple(range(28))),
}


def representation_specifications():
    return [{"path": path, "classification": "ExactDeclaredCarriageReturnInsertionsOnly",
             "committedGitIdentity": {"path": path, "bytes": values[0], "sha256": values[1]},
             "originalProtectedFilesystemIdentity": {"path": path, "bytes": values[2], "sha256": values[3]},
             "canonicalLfCount": values[4], "carriageReturnInsertionBeforeLfOrdinals": list(values[5]),
             "carriageReturnInsertionCount": len(values[5]),
             "transformation": "Insert0DImmediatelyBeforeExactZeroBasedLfOrdinals",
             "noOtherByteChanges": True} for path, values in sorted(REPRESENTATIONS.items())]


def committed_git_inventory(root):
    result = subprocess.run(["git", "-C", str(root), "ls-tree", "-rz", "--full-tree", BASE],
                            capture_output=True, check=False)
    require(result.returncode == 0, "ReadOnlyCommittedGitInventoryFailed")
    rows = {}
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split()
        relative = name.decode("utf-8")
        require(kind == "blob" and mode in ("100644", "100755") and relative not in rows,
                "RegularUniqueCommittedSourceBlobRequired")
        actual = identity(root, relative)
        raw = (Path(root) / relative).read_bytes()
        header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
        observed = sha1(header + raw).hexdigest() if len(object_id) == 40 else sha256(header + raw).hexdigest()
        require(observed == object_id, "CheckoutMustEqualExactCommittedGitBlob:" + relative)
        require(actual == {"path": relative, "bytes": len(raw), "sha256": sha256(raw).hexdigest()},
                "CommittedSourceChangedDuringRead:" + relative)
        rows[relative] = actual
    require(len(rows) == 851, "Exact851CommittedGitBlobsRequired")
    return rows


def reconstruct_protected_representation(raw, row):
    require(raw.count(b"\n") == row["canonicalLfCount"] and b"\r" not in raw,
            "ExactCanonicalLfSourceRequired:" + row["path"])
    ordinals = set(row["carriageReturnInsertionBeforeLfOrdinals"])
    expected = bytearray()
    ordinal = 0
    for byte in raw:
        if byte == 10:
            if ordinal in ordinals:
                expected.append(13)
            ordinal += 1
        expected.append(byte)
    return bytes(expected)


def verify_representation_bytes(baseline, declared):
    require(declared == representation_specifications(), "OnlyExactThreeImmutableRepresentationDeclarationsAllowed")
    for row in declared:
        path = row["path"]
        require(path.endswith(".csproj") and path not in MODIFIED, "RepresentationMayNotWidenProductionChangeScope")
        raw = (Path(baseline) / path).read_bytes()
        require(identity(baseline, path) == row["committedGitIdentity"]
                and raw.count(b"\n") == row["canonicalLfCount"] and b"\r" not in raw,
                "ExactCanonicalRepresentationSourceRequired:" + path)
        expected = reconstruct_protected_representation(raw, row)
        require({"path": path, "bytes": len(expected), "sha256": sha256(expected).hexdigest()}
                == row["originalProtectedFilesystemIdentity"],
                "ExactCarriageReturnInsertionProofFailed:" + path)
    return {row["path"]: row for row in declared}


def historical_representation_pin_audit(baseline, historical_paths):
    # Check all committed public JSON binding objects/maps and every literal old
    # protected hash in all851 files. A match is a blocker, not an edited pin.
    variants = representation_specifications()
    variant_paths = set(REPRESENTATIONS)
    forbidden_hashes = {row["originalProtectedFilesystemIdentity"]["sha256"] for row in variants}
    hits = []
    documents = 0
    def inspect(document, value, field="$"):
        if isinstance(value, dict):
            if isinstance(value.get("path"), str) and value["path"] in variant_paths and isinstance(value.get("sha256"), str):
                hits.append({"document": document, "field": field, "path": value["path"]})
            for key, child in value.items():
                if key in variant_paths and isinstance(child, str) and len(child) == 64:
                    hits.append({"document": document, "field": field + "." + key, "path": key})
                inspect(document, child, field + "." + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect(document, child, field + "[" + str(index) + "]")
    for relative in sorted(historical_paths):
        raw = (Path(baseline) / relative).read_bytes()
        if relative.endswith(".json"):
            inspect(relative, json.loads(raw))
            documents += 1
        for digest in forbidden_hashes:
            if digest.encode("ascii") in raw.lower():
                hits.append({"document": relative, "literalProtectedHash": digest})
    require(not hits, "HistoricalSourcePinsIntersectRepresentationVariants:" + repr(hits))
    return {"historicalSourcesInspected": len(historical_paths), "historicalJsonDocumentsInspected": documents,
            "structuredAndLiteralPinHits": hits, "historicalValidatorsActuallyRun": False}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def identity(root, relative):
    root = Path(root).resolve()
    path = root / relative
    require(type(relative) is str and not Path(relative).is_absolute() and ".." not in Path(relative).parts,
            "CanonicalRelativeSourcePathRequired")
    require(not path.is_symlink() and path.resolve().is_relative_to(root) and path.is_file(),
            "RegularContainedSourceRequired:" + relative)
    value = path.read_bytes()
    return {"path": relative, "bytes": len(value), "sha256": sha256(value).hexdigest()}


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    require(result.returncode == 0, "ReadOnlyGitFailed:" + " ".join(args))
    return result.stdout.decode("utf-8").strip()


def semantic_body_proof(active, baseline):
    old = (baseline / "rust/p28-slice-runner/src/exec.rs").read_bytes().decode("utf-8")
    new = (active / "rust/p28-slice-runner/src/exec.rs").read_bytes().decode("utf-8")
    def instruction_body(text):
        return text[text.index("pub struct Exec<'a>"):text.index("/// Fetch, decode and execute one instruction at PC.")]
    old_body, new_body = instruction_body(old), instruction_body(new)
    require(old_body == new_body, "ProductionInstructionSemanticBodyChanged_NotAccepted")
    # The complete preexisting post-decode tail is shared, not copied dispatch.
    old_tail = old[old.index("    // PC advances past the instruction before execution"):
                   old.index("\n#[cfg(test)]", old.index("pub fn step("))]
    new_tail = new[new.index("    // PC advances past the instruction before execution"):
                   new.index("\n#[cfg(test)]", new.index("pub fn step("))]
    require(old_tail == new_tail, "SharedProductionExecutionTailChanged_NotAccepted")
    return {"instructionSemanticBodyByteEqual": True,
            "semanticBodySha256": sha256(old_body.encode("utf-8")).hexdigest(),
            "postDecodeTailByteEqual": True,
            "postDecodeTailSha256": sha256(old_tail.encode("utf-8")).hexdigest(),
            "reuse": "SameProductionExecRunAndExecuteDecoded_NoResearchInstructionDispatch"}


def source_checks(active, baseline):
    active, baseline = Path(active).resolve(), Path(baseline).resolve()
    require(active != baseline and git(baseline, "rev-parse", "HEAD") == BASE,
            "SeparateExactHistoricalM2boCheckoutRequired")
    require(git(baseline, "diff", "--name-only") == "" and git(baseline, "diff", "--cached", "--name-only") == "",
            "HistoricalTrackedSourcesMustStayImmutable")
    git(active, "merge-base", "--is-ancestor", BASE, "HEAD")
    manifest = json.loads((active / MANIFEST).read_text(encoding="utf-8"))
    contract = json.loads((active / CONTRACT).read_text(encoding="utf-8"))
    require(manifest["milestone"] == contract["milestone"] == "M2bp"
            and manifest["exactHistoricalBase"] == contract["exactHistoricalBase"] == BASE,
            "ExactVersionTransitionRequired")
    require(contract["sourceManifest"] == identity(active, MANIFEST), "ContractManifestIdentityMismatch")
    old_rows = manifest["historicalBaselineSources"]
    require(len(old_rows) == len({row["path"] for row in old_rows}) == 851,
            "CompleteExact851HistoricalSourcesRequired")
    old_index = {row["path"]: row for row in old_rows}
    require(set(git(baseline, "ls-files").splitlines()) == set(old_index), "HistoricalTrackedInventoryMismatch")
    require(manifest["historicalBaselineSourceRole"] == "ExactCommittedGitBlobBytes_AtExactHistoricalBase"
            and manifest["localProtectedFilesystemSourceRole"] == "OriginalProtectedLocalBeforeBytes_NotCanonicalGitAlias"
            and manifest["representationVariantPolicy"] == "OnlyThreeDeclaredImmutableCsprojRepresentations_NoNormalizationWrites",
            "ExplicitImmutableIdentityRolesRequired")
    require(committed_git_inventory(baseline) == old_index, "EveryHistoricalSourceMustMatchActualExactGitBlob")
    local_rows = manifest["localProtectedFilesystemSources"]
    require(len(local_rows) == len({row["path"] for row in local_rows}) == 851
            and {row["path"] for row in local_rows} == set(old_index), "SeparateCompleteLocalProtected851Required")
    local_index = {row["path"]: row for row in local_rows}
    variants = verify_representation_bytes(baseline, manifest["representationVariants"])
    for relative, old_row in old_index.items():
        if relative in variants:
            require(old_row == variants[relative]["committedGitIdentity"]
                    and local_index[relative] == variants[relative]["originalProtectedFilesystemIdentity"],
                    "ExactDeclaredDualIdentityMismatch:" + relative)
        else:
            require(local_index[relative] == old_row, "UndeclaredSourceRepresentationVariant:" + relative)
    pin_audit = historical_representation_pin_audit(baseline, old_index)
    changed = {row["path"]: row for row in manifest["authorizedModifiedFiles"]}
    require(set(changed) == MODIFIED, "OnlyReviewedNarrowProductionAndWorkflowTransitionAllowed")
    for relative, old_row in old_index.items():
        actual = identity(active, relative)
        if relative in changed:
            change = changed[relative]
            require(change["old"] == old_row == local_index[relative] and change["new"] == actual
                    and change["changedFunctions"] and change["authorizedReason"]
                    and change["semanticImpactClassification"], "IncompleteVersionedSourceChange:" + relative)
        elif relative in variants:
            # An exact closed pair, not "normalize whatever is present". Both
            # byte identities and the fixed insertion proof are independently
            # pinned above. This supports the untouched local host and Git CI.
            require(actual in (old_row, local_index[relative]),
                    "ActiveRepresentationOutsideExactImmutablePair:" + relative)
            canonical_raw = (baseline / relative).read_bytes()
            active_raw = (active / relative).read_bytes()
            require(active_raw == (canonical_raw if actual == old_row else
                    reconstruct_protected_representation(canonical_raw, variants[relative])),
                    "ActualActiveBytesDifferFromDeclaredRepresentation:" + relative)
        else:
            require(actual == old_row, "UnrelatedHistoricalPublicSourceChanged:" + relative)
    new_paths = manifest["newPublicPaths"]
    require(len(new_paths) == len(set(new_paths)) and not (set(new_paths) & set(old_index)),
            "GenuinelyNewClosedSourceInventoryRequired")
    require(manifest["identityCycleExclusions"] == [MANIFEST, CONTRACT], "OnlyExplicitSelfCycleExclusionsAllowed")
    expected_new = set(new_paths) - {MANIFEST, CONTRACT}
    new_rows = manifest["newSourceBindings"]
    require({row["path"] for row in new_rows} == expected_new and len(new_rows) == len(expected_new),
            "AllNewSourceBindingsRequired")
    for row in new_rows:
        require(identity(active, row["path"]) == row, "NewActiveSourceIdentityMismatch:" + row["path"])
    package = tomllib.loads((active / "rust/p28-slice-runner/Cargo.toml").read_text(encoding="utf-8"))
    require(package["package"]["version"] == "0.43.0" and package["features"]["default"] == []
            and package["features"]["p28-word0196-audit"] == [], "DefaultDisabledNarrowFeatureRequired")
    old_contract = json.loads((baseline / (RESEARCH + "production_exec_parity_contract.json")).read_text(encoding="utf-8"))
    conflicts = [row["path"] for row in old_contract["sourceBindings"] if identity(active, row["path"]) != row]
    pinned_paths = {row["path"] for row in old_contract["sourceBindings"]}
    expected_conflicts = MODIFIED & pinned_paths
    require(expected_conflicts == {"rust/p28-slice-runner/src/" + name for name in
                                   ("bus.rs", "decoder.rs", "exec.rs", "lib.rs")}
            and set(conflicts) == expected_conflicts,
            "ExpectedOldSourcePinConflictMustBePreciselyClassified")
    proof = semantic_body_proof(active, baseline)
    # The old Desktop lifecycle/timeout/assertions and all old research files
    # were already checked byte-for-byte above. No new JSON can promote runtime.
    return {"passed": True, "classification": "ProductionSourceBindingsVersioned_StaticAuditOnly",
            "exactHistoricalBase": BASE, "historicalSources": len(old_rows),
            "historicalBaselineSourceRole": manifest["historicalBaselineSourceRole"],
            "localProtectedFilesystemSourceRole": manifest["localProtectedFilesystemSourceRole"],
            "representationVariantPolicy": manifest["representationVariantPolicy"],
            "representationVariants": manifest["representationVariants"],
            "separateLocalProtectedSourceCount": len(local_rows),
            "historicalRepresentationPinAudit": pin_audit,
            "oldSourcePinConflictClassification": "OldSourcePinConflictExpectedAfterVersionTransition",
            "expectedOldPinConflicts": conflicts, "authorizedModifiedFiles": manifest["authorizedModifiedFiles"],
            "newSourceBindings": new_rows, "manifest": identity(active, MANIFEST),
            "contract": identity(active, CONTRACT), "semanticBodyProof": proof,
            "historicalPinnedBaselineQa": "RequiresSeparateActualUnchangedValidators",
            "activeDefaultModeQa": "RequiresActualCompiledDefaultDifferentialAndFullSuites",
            "activeOptInCapabilityQa": "RequiresActualRuntimeAndIndependentOracle",
            "cpuExecutions": 0, "fullProductionCompositeExecutions": 0,
            "firmwareReady": False}, contract
