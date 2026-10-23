"""Invented Git trees only; no ROM reads, Rust execution, or Git subprocesses."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

_PATH = Path(__file__).with_name("source_guard.py")
_SPEC = importlib.util.spec_from_file_location("_m2bt_source_guard_test_target", _PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("OwnedSourceGuardUnavailable")
guard = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = guard
_SPEC.loader.exec_module(guard)
Blob = guard.Blob

OLD_MANIFEST = b'''[package]
name = "invented"
version = "0.43.0"
[features]
default = []
p28-word0196-audit = []
[dependencies]
'''
NEW_MANIFEST = OLD_MANIFEST.replace(b"[dependencies]", b'''p28-word0196-original-rom = ["p28-word0196-audit"]
[[bin]]
name = "m2bt-original-rom"
path = "src/bin/m2bt_original_rom.rs"
required-features = ["p28-word0196-original-rom"]
[dependencies]''')


def digest(data):
    return sha256(data).hexdigest()


def trees():
    original = ("name: invented\n" + guard._OLD.HISTORICAL_CHECKOUT +
                "\n      - name: Invented historical gate\n        run: true\n" +
                guard.FROZEN_M2BS_STEPS + guard.DESKTOP_MARKER +
                "\n    steps:\n      - run: invented-desktop\n")
    active_workflow = original.replace(guard.FROZEN_M2BS_STEPS, guard.PINNED_M2BS_STEPS).replace(
        guard.DESKTOP_MARKER, guard.ACTIVE_STEPS + guard.DESKTOP_MARKER)
    base = {guard.WORKFLOW: Blob("100644", original.encode()),
            guard.MANIFEST: Blob("100644", OLD_MANIFEST),
            "src/invented.cs": Blob("100644", b"// invented immutable source\n")}
    for name in guard.RUST_DELTA_PATHS - {guard.MANIFEST}:
        base[name] = Blob("100644", b"// invented original opt-in source\n")
    active = dict(base)
    active[guard.WORKFLOW] = Blob("100644", active_workflow.encode())
    active[guard.MANIFEST] = Blob("100644", NEW_MANIFEST)
    for name in guard.RUST_DELTA_PATHS - {guard.MANIFEST}:
        active[name] = Blob("100644", b"// invented reviewed opt-in delta\n")
    for name in guard.NEW_PATHS:
        active[name] = Blob("100644", b"pass\n" if name.endswith(".py") else b"invented public text\n")
    pairs = {name: (digest(base[name].data), digest(active[name].data)) for name in guard.RUST_DELTA_PATHS}
    return base, active, pairs


class SourceGuardTests(unittest.TestCase):
    def refusal(self, base, active, pairs, rule):
        with self.assertRaisesRegex(ValueError, rule):
            guard.compare_trees(base, active, reviewed_deltas=pairs)

    def test_closed_tree_fingerprint_and_authority_split(self):
        base, active, pairs = trees()
        result = guard.compare_trees(base, active, reviewed_deltas=pairs)
        self.assertTrue(result["passed"])
        self.assertEqual(result["newPublicPaths"], sorted(guard.NEW_PATHS))
        self.assertEqual(result["unchangedBaseFiles"], 1)
        self.assertEqual(len(result["authorizedOldOptInRustDeltas"]), 3)
        self.assertEqual(len(result["sourceBindings"]), len(active))
        self.assertEqual(result["sourceFingerprintSha256"],
                         guard.compare_trees(base, active, reviewed_deltas=pairs)["sourceFingerprintSha256"])
        self.assertFalse(result["historicalCompiledResultsAreActiveExecution"])
        self.assertFalse(result["originalRomVerificationByThisGuard"])
        self.assertFalse(result["privateContentPrivacyAttestationByThisGuard"])
        self.assertTrue(result["changedRustInputsRequireActiveQa"])
        self.assertEqual(result["targetCpuExecutions"], 0)

    def test_missing_reviewed_bindings_no_development_fallback(self):
        base, active, _ = trees()
        with patch.object(guard, "REVIEWED_OLD_DELTAS", {}):
            with self.assertRaisesRegex(ValueError, "ExactReviewedOptInDeltaBindingsRequired"):
                guard.compare_trees(base, active)

    def test_reviewed_delta_missing_path_refused(self):
        base, active, pairs = trees()
        del pairs[guard.MANIFEST]
        self.refusal(base, active, pairs, "ExactReviewedOptInDeltaBindingsRequired")

    def test_extra_reviewed_old_path_refused(self):
        base, active, pairs = trees()
        pairs["src/invented.cs"] = ("a" * 64, "b" * 64)
        self.refusal(base, active, pairs, "ExactReviewedOptInDeltaBindingsRequired")

    def test_unfrozen_delta_refused(self):
        base, active, pairs = trees()
        pairs[guard.MANIFEST] = ("UNFROZEN", "UNFROZEN")
        self.refusal(base, active, pairs, "ReviewedOptInDeltaNotFrozen")

    def test_unreviewed_optin_edit_refused(self):
        base, active, pairs = trees()
        name = sorted(guard.RUST_DELTA_PATHS - {guard.MANIFEST})[0]
        active[name] = Blob("100644", b"// additional unreviewed delta\n")
        self.refusal(base, active, pairs, "UnreviewedOptInRustDelta")

    def test_wrong_base_delta_identity_refused(self):
        base, active, pairs = trees()
        pairs[guard.MANIFEST] = ("a" * 64, pairs[guard.MANIFEST][1])
        self.refusal(base, active, pairs, "UnreviewedOptInRustDelta")

    def test_non_delta_review_refused(self):
        base, active, pairs = trees()
        name = sorted(guard.RUST_DELTA_PATHS - {guard.MANIFEST})[0]
        active[name] = base[name]
        pairs[name] = (digest(base[name].data), digest(base[name].data))
        self.refusal(base, active, pairs, "UnreviewedOptInRustDelta")

    def test_other_old_source_change_refused(self):
        base, active, pairs = trees()
        active["src/invented.cs"] = Blob("100644", b"// changed\n")
        self.refusal(base, active, pairs, "HistoricalOrProductionInputChanged")

    def test_old_mode_change_refused(self):
        base, active, pairs = trees()
        name = sorted(guard.RUST_DELTA_PATHS)[0]
        active[name] = Blob("100755", active[name].data)
        self.refusal(base, active, pairs, "HistoricalSourceModeChanged")

    def test_old_source_deleted_refused(self):
        base, active, pairs = trees()
        del active["src/invented.cs"]
        self.refusal(base, active, pairs, "HistoricalSourceDeleted")

    def test_new_path_missing_refused(self):
        base, active, pairs = trees()
        del active["AGENTS.md"]
        self.refusal(base, active, pairs, "UnknownOrMissingM2btSourcePath")

    def test_new_unknown_path_refused(self):
        base, active, pairs = trees()
        active["research/unknown.py"] = Blob("100644", b"pass\n")
        self.refusal(base, active, pairs, "UnknownOrMissingM2btSourcePath")

    def test_private_path_refused(self):
        base, active, pairs = trees()
        active["private/invented.json"] = Blob("100644", b"{}\n")
        self.refusal(base, active, pairs, "PrivateOrBinaryArtifactAdded")

    def test_binary_firmware_path_refused(self):
        base, active, pairs = trees()
        active["invented.bin"] = Blob("100644", b"invented")
        self.refusal(base, active, pairs, "PrivateOrBinaryArtifactAdded")

    def test_new_executable_mode_refused(self):
        base, active, pairs = trees()
        name = guard.PACKAGE + "oracle.py"
        active[name] = Blob("100755", active[name].data)
        self.refusal(base, active, pairs, "NewResearchSourceMustBeNonexecutableText")

    def test_symlink_mode_refused(self):
        base, active, pairs = trees()
        active["AGENTS.md"] = Blob("120000", b"invented-target")
        self.refusal(base, active, pairs, "ClosedRegularSourceTree")

    def test_noncanonical_source_path_refused(self):
        base, active, pairs = trees()
        active["research/../unexpected.py"] = Blob("100644", b"pass\n")
        self.refusal(base, active, pairs, "ClosedRegularSourceTree")

    def test_new_nul_text_refused(self):
        base, active, pairs = trees()
        active["AGENTS.md"] = Blob("100644", b"invented\x00")
        self.refusal(base, active, pairs, "NewResearchSourceMustBeNonexecutableText")

    def test_new_invalid_utf8_refused(self):
        base, active, pairs = trees()
        active["AGENTS.md"] = Blob("100644", b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            guard.compare_trees(base, active, reviewed_deltas=pairs)

    def test_python_syntax_error_refused(self):
        base, active, pairs = trees()
        active[guard.PACKAGE + "oracle.py"] = Blob("100644", b"def invalid(:\n")
        with self.assertRaises(SyntaxError):
            guard.compare_trees(base, active, reviewed_deltas=pairs)

    def test_python_not_executed(self):
        base, active, pairs = trees()
        active[guard.PACKAGE + "oracle.py"] = Blob("100644", b"raise RuntimeError('not executed')\n")
        self.assertTrue(guard.compare_trees(base, active, reviewed_deltas=pairs)["passed"])

    def test_exact_three_phase_projection(self):
        base, active, _ = trees()
        result = guard.workflow_projection(base[guard.WORKFLOW].data, active[guard.WORKFLOW].data)
        self.assertTrue(result["allHistoricalCommandBodiesPreserved"])
        self.assertTrue(result["desktopJobByteExact"])
        self.assertEqual(result["pinnedM2bsSha"], guard.BASE)

    def test_m2bs_expected_head_not_active_sha(self):
        base, active, pairs = trees()
        data = active[guard.WORKFLOW].data.replace(
            ('--expected-head "' + guard.BASE + '"').encode(), b'--expected-head "${{ github.sha }}"')
        active[guard.WORKFLOW] = Blob("100644", data)
        self.refusal(base, active, pairs, "ExactThreePhaseOrchestrationRequired")

    def test_m2bs_checkout_not_active_sha(self):
        base, active, pairs = trees()
        data = active[guard.WORKFLOW].data.replace(('ref: ' + guard.BASE).encode(), b'ref: ${{ github.sha }}')
        active[guard.WORKFLOW] = Blob("100644", data)
        self.refusal(base, active, pairs, "ExactThreePhaseOrchestrationRequired")

    def test_historical_gate_body_changed_refused(self):
        base, active, pairs = trees()
        active[guard.WORKFLOW] = Blob("100644", active[guard.WORKFLOW].data.replace(b"        run: true\n", b""))
        self.refusal(base, active, pairs, "HistoricalWorkflowOrDesktopCheckChanged")

    def test_desktop_job_changed_refused(self):
        base, active, pairs = trees()
        active[guard.WORKFLOW] = Blob("100644", active[guard.WORKFLOW].data.replace(b"invented-desktop", b"changed-desktop"))
        self.refusal(base, active, pairs, "HistoricalWorkflowOrDesktopCheckChanged")

    def test_extra_gate_after_active_block_refused(self):
        base, active, pairs = trees()
        data = active[guard.WORKFLOW].data.replace(guard.ACTIVE_STEPS.encode(), guard.ACTIVE_STEPS.encode() + b"\n      - run: extra\n")
        active[guard.WORKFLOW] = Blob("100644", data)
        self.refusal(base, active, pairs, "ActiveM2btStepsMustFollowEveryPinnedGate")

    def test_removed_active_suite_refused(self):
        base, active, pairs = trees()
        data = active[guard.WORKFLOW].data.replace(b"          cargo +1.85.1 fmt --check", b"          # cargo +1.85.1 fmt --check")
        active[guard.WORKFLOW] = Blob("100644", data)
        self.refusal(base, active, pairs, "ExactThreePhaseOrchestrationRequired")

    def test_artifact_directory_glob_refused(self):
        base, active, pairs = trees()
        data = active[guard.WORKFLOW].data.replace(b".tmp/m2bt-public-evidence/canonical.jsonl.gz", b".tmp/m2bt-public-evidence/**")
        active[guard.WORKFLOW] = Blob("100644", data)
        self.refusal(base, active, pairs, "ExactThreePhaseOrchestrationRequired")

    def test_cargo_feature_default_off(self):
        proof = guard.manifest_projection(OLD_MANIFEST, NEW_MANIFEST)
        self.assertTrue(proof["defaultOff"])
        self.assertTrue(proof["existingAuditDependency"])

    def test_feature_table_missing_refused(self):
        with self.assertRaisesRegex(ValueError, "ClosedFeatureTablesRequired"):
            guard.manifest_projection(OLD_MANIFEST, b'[package]\nname = "invented"\n')

    def test_required_binary_table_missing_refused(self):
        data = OLD_MANIFEST.replace(b"[dependencies]", b'p28-word0196-original-rom = ["p28-word0196-audit"]\n[dependencies]')
        with self.assertRaisesRegex(ValueError, "ResearchBinaryTableRequired"):
            guard.manifest_projection(OLD_MANIFEST, data)

    def test_default_feature_enabled_refused(self):
        data = NEW_MANIFEST.replace(b"default = []", b'default = ["p28-word0196-original-rom"]')
        with self.assertRaisesRegex(ValueError, "NewFeatureMustRemainDefaultOff"):
            guard.manifest_projection(OLD_MANIFEST, data)

    def test_audit_dependency_removed_refused(self):
        data = NEW_MANIFEST.replace(b'p28-word0196-original-rom = ["p28-word0196-audit"]', b'p28-word0196-original-rom = []')
        with self.assertRaisesRegex(ValueError, "NewFeatureMustRequireExistingAudit"):
            guard.manifest_projection(OLD_MANIFEST, data)

    def test_binary_not_required_feature_refused(self):
        data = NEW_MANIFEST.replace(b'required-features = ["p28-word0196-original-rom"]\n', b"")
        with self.assertRaisesRegex(ValueError, "ResearchBinaryMustRequireNewFeature"):
            guard.manifest_projection(OLD_MANIFEST, data)

    def test_version_change_refused(self):
        with self.assertRaisesRegex(ValueError, "UnrelatedCargoManifestContractChanged"):
            guard.manifest_projection(OLD_MANIFEST, NEW_MANIFEST.replace(b"0.43.0", b"0.44.0"))

    def test_dependency_change_refused(self):
        with self.assertRaisesRegex(ValueError, "UnrelatedCargoManifestContractChanged"):
            guard.manifest_projection(OLD_MANIFEST, NEW_MANIFEST + b'unknown = "1"\n')

    def test_new_source_changes_fingerprint(self):
        base, active, pairs = trees()
        before = guard.compare_trees(base, active, reviewed_deltas=pairs)["sourceFingerprintSha256"]
        active["AGENTS.md"] = Blob("100644", b"invented changed policy\n")
        self.assertNotEqual(before, guard.compare_trees(base, active, reviewed_deltas=pairs)["sourceFingerprintSha256"])


class CiOutputRoutingTests(unittest.TestCase):
    def setUp(self):
        self.owned = tempfile.TemporaryDirectory(prefix="m2bt-ci-routing-invented-")
        self.addCleanup(self.owned.cleanup)
        self.root = Path(self.owned.name).resolve()
        self.target = self.root / guard.CI_TARGET
        self.environment = {"GITHUB_ACTIONS": "true", "GITHUB_SHA": "1" * 40,
                            "CARGO_TARGET_DIR": str(self.target)}

    def test_fresh_ci_target_marker_and_reuse(self):
        receipt = guard.ci_cargo_preflight(self.root, self.environment)
        self.assertTrue(receipt["passed"])
        self.assertTrue((self.target / guard.CI_TARGET_MARKER).is_file())
        self.assertEqual(receipt, guard.ci_cargo_preflight(self.root, self.environment))
        self.assertFalse(receipt["historicalRunnerPreservationAttested"])
        self.assertEqual(receipt["cargoInvocations"], 0)

    def test_not_a_local_build_guard_fallback(self):
        self.environment["GITHUB_ACTIONS"] = "false"
        with self.assertRaisesRegex(ValueError, "PublicCiContextRequired"):
            guard.ci_cargo_preflight(self.root, self.environment)
        self.assertFalse(self.target.exists())

    def test_exact_sha_required(self):
        self.environment["GITHUB_SHA"] = "branch-name"
        with self.assertRaisesRegex(ValueError, "ExactPublicCiShaRequired"):
            guard.ci_cargo_preflight(self.root, self.environment)

    def test_conflicting_environment_target_rejected(self):
        self.environment["CARGO_TARGET_DIR"] = str(self.root / "rust/p28-slice-runner/target")
        with self.assertRaisesRegex(ValueError, "ExactCiCargoTargetEnvironmentRequired"):
            guard.ci_cargo_preflight(self.root, self.environment)
        self.assertFalse(self.target.exists())

    def test_nonempty_unowned_target_not_adopted(self):
        self.target.mkdir(parents=True)
        (self.target / "invented.txt").write_text("not owned", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "CiUnownedNonemptyTargetRejected"):
            guard.ci_cargo_preflight(self.root, self.environment)

    def test_changed_marker_rejected(self):
        guard.ci_cargo_preflight(self.root, self.environment)
        (self.target / guard.CI_TARGET_MARKER).write_bytes(b"{}\n")
        with self.assertRaisesRegex(ValueError, "CiTargetOwnershipMismatch"):
            guard.ci_cargo_preflight(self.root, self.environment)

    def test_later_sha_cannot_adopt_marker(self):
        guard.ci_cargo_preflight(self.root, self.environment)
        self.environment["GITHUB_SHA"] = "2" * 40
        with self.assertRaisesRegex(ValueError, "CiTargetOwnershipMismatch"):
            guard.ci_cargo_preflight(self.root, self.environment)

    def test_mocked_reparse_target_rejected(self):
        self.target.mkdir(parents=True)
        original = Path.lstat
        def observed(path):
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400) \
                if path == self.target else original(path)
        with patch.object(Path, "lstat", observed):
            with self.assertRaisesRegex(ValueError, "CiTargetReparsePointRejected"):
                guard.ci_cargo_preflight(self.root, self.environment)

    def test_all_new_ci_cargo_commands_keep_full_coverage_and_isolated_target(self):
        commands = [line.strip() for line in guard.ACTIVE_STEPS.splitlines()
                    if line.strip().startswith("cargo +1.85.1")]
        builds = [line for line in commands if " test " in line or " build " in line]
        self.assertEqual(len(builds), 4)
        self.assertEqual(sum(" test " in line for line in builds), 3)
        for command in builds:
            self.assertIn("--target-dir .tmp/m2bt-owned/cargo-target", command)
            self.assertNotIn("--lib", command)
        self.assertEqual(guard.ACTIVE_STEPS.count("--ci-cargo-preflight"), 4)
        self.assertEqual(guard.ACTIVE_STEPS.count("CARGO_TARGET_DIR:"), 2)


if __name__ == "__main__":
    unittest.main()
