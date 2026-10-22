"""Invented source trees only; no ROM, subprocess, checkout, or source mutation."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import source_guard
from source_guard import (ACTIVE_STEPS, Blob, DESKTOP_MARKER, HISTORICAL_CHECKOUT,
                          NEW_PATHS, ORIGINAL_CHECKOUT, WORKFLOW, compare_trees,
                          contents, workflow_projection)


def trees():
    original = ("name: invented\n" + ORIGINAL_CHECKOUT +
                "\n      - name: Invented historical gate\n        run: true\n" +
                DESKTOP_MARKER + "\n    steps:\n      - run: invented-desktop\n")
    active = original.replace(ORIGINAL_CHECKOUT, HISTORICAL_CHECKOUT).replace(
        DESKTOP_MARKER, ACTIVE_STEPS + DESKTOP_MARKER)
    base = {WORKFLOW: Blob("100644", original.encode()),
            "src/invented.cs": Blob("100644", b"// invented immutable input\n"),
            "rust/invented.rs": Blob("100644", b"// invented immutable input\n")}
    current = {**base, WORKFLOW: Blob("100644", active.encode())}
    for name in NEW_PATHS:
        current[name] = Blob("100644", b"pass\n" if name.endswith(".py") else b"invented\n")
    return base, current


class SourceGuardTests(unittest.TestCase):
    def refusal(self, base, active, rule):
        with self.assertRaisesRegex(ValueError, rule):
            compare_trees(base, active)

    def test_invented_closed_source_tree_and_fingerprint(self):
        base, active = trees()
        result = compare_trees(base, active)
        self.assertTrue(result["passed"])
        self.assertEqual(len(NEW_PATHS), 14)
        self.assertEqual(result["unchangedBaseFiles"], 2)
        self.assertEqual(result["newPublicPaths"], sorted(NEW_PATHS))
        self.assertEqual(result["sourceFingerprintSha256"], compare_trees(base, active)["sourceFingerprintSha256"])
        self.assertFalse(result["historicalCompiledResultsAreActiveExecution"])
        self.assertFalse(result["originalRomVerificationByThisGuard"])

    def test_changed_old_production_bytes_refused(self):
        base, active = trees()
        active["src/invented.cs"] = Blob("100644", b"// changed\n")
        self.refusal(base, active, "HistoricalOrProductionInputChanged")

    def test_changed_old_mode_refused(self):
        base, active = trees()
        active["rust/invented.rs"] = Blob("100755", active["rust/invented.rs"].data)
        self.refusal(base, active, "HistoricalOrProductionInputChanged")

    def test_deleted_old_source_refused(self):
        base, active = trees()
        del active["src/invented.cs"]
        self.refusal(base, active, "HistoricalSourceDeleted")

    def test_unknown_new_source_refused(self):
        base, active = trees()
        active["research/unreviewed.py"] = Blob("100644", b"pass\n")
        self.refusal(base, active, "UnknownOrMissingM2bsSourcePath")

    def test_missing_new_source_refused(self):
        base, active = trees()
        del active[sorted(NEW_PATHS)[0]]
        self.refusal(base, active, "UnknownOrMissingM2bsSourcePath")

    def test_private_file_refused(self):
        base, active = trees()
        active["private/invented.json"] = Blob("100644", b"{}\n")
        self.refusal(base, active, "PrivateOrBinaryArtifactAdded")

    def test_target_binary_refused(self):
        base, active = trees()
        active["invented.bin"] = Blob("100644", b"invented")
        self.refusal(base, active, "PrivateOrBinaryArtifactAdded")

    def test_new_executable_mode_refused(self):
        base, active = trees()
        name = next(n for n in NEW_PATHS if n.endswith(".py"))
        active[name] = Blob("100755", active[name].data)
        self.refusal(base, active, "NewResearchSourceMustBeNonexecutableText")

    def test_new_nul_source_refused(self):
        base, active = trees()
        active[next(n for n in NEW_PATHS if n.endswith(".py"))] = Blob("100644", b"pass\x00\n")
        self.refusal(base, active, "NewResearchSourceMustBeNonexecutableText")

    def test_new_python_syntax_error_refused(self):
        base, active = trees()
        active[next(n for n in NEW_PATHS if n.endswith(".py"))] = Blob("100644", b"def broken(:\n")
        with self.assertRaises(SyntaxError):
            compare_trees(base, active)

    def test_python_is_compiled_but_not_executed(self):
        base, active = trees()
        active[next(n for n in NEW_PATHS if n.endswith(".py"))] = Blob("100644", b"raise RuntimeError('must not run')\n")
        self.assertTrue(compare_trees(base, active)["passed"])

    def test_old_gate_removed_refused(self):
        base, active = trees()
        active[WORKFLOW] = Blob("100644", active[WORKFLOW].data.replace(b"        run: true\n", b""))
        self.refusal(base, active, "HistoricalWorkflowOrDesktopCheckChanged")

    def test_desktop_job_changed_refused(self):
        base, active = trees()
        active[WORKFLOW] = Blob("100644", active[WORKFLOW].data.replace(b"invented-desktop", b"changed-desktop"))
        self.refusal(base, active, "HistoricalWorkflowOrDesktopCheckChanged")

    def test_active_checkout_not_last_refused(self):
        base, active = trees()
        active[WORKFLOW] = Blob("100644", active[WORKFLOW].data.replace(
            ACTIVE_STEPS.encode(), ACTIVE_STEPS.encode() + b"\n      - run: extra\n"))
        self.refusal(base, active, "ActiveStepsMustFollowEveryHistoricalGate")

    def test_active_clean_true_refused(self):
        base, active = trees()
        active[WORKFLOW] = Blob("100644", active[WORKFLOW].data.replace(b"clean: false", b"clean: true"))
        self.refusal(base, active, "ExactTwoCheckoutOrchestrationRequired")

    def test_public_tests_skip_refused(self):
        base, active = trees()
        active[WORKFLOW] = Blob("100644", active[WORKFLOW].data.replace(
            b"      - name: Active M2bs public synthetic", b"      - if: false\n        name: Active M2bs public synthetic"))
        self.refusal(base, active, "ExactTwoCheckoutOrchestrationRequired")

    def test_workflow_mode_change_refused(self):
        base, active = trees()
        active[WORKFLOW] = Blob("100755", active[WORKFLOW].data)
        self.refusal(base, active, "WorkflowModeChanged")

    def test_raw_workflow_literal_projection(self):
        base, active = trees()
        proof = workflow_projection(base[WORKFLOW].data, active[WORKFLOW].data)
        self.assertTrue(proof["allHistoricalStepsPreserved"])
        self.assertTrue(proof["desktopJobByteExact"])

    def test_reparse_style_git_mode_refused(self):
        base, active = trees()
        name = next(n for n in NEW_PATHS if n.endswith(".py"))
        active[name] = Blob("120000", b"invented-target")
        self.refusal(base, active, "ClosedRegularSourceTree")

    def test_noncanonical_tree_path_refused(self):
        base, active = trees()
        active["research/../unexpected.py"] = Blob("100644", b"pass\n")
        self.refusal(base, active, "ClosedRegularSourceTree")

    def test_fingerprint_changes_with_new_source(self):
        base, active = trees()
        before = compare_trees(base, active)["sourceFingerprintSha256"]
        name = next(n for n in NEW_PATHS if n.endswith(".py"))
        active[name] = Blob("100644", b"# invented change\npass\n")
        self.assertNotEqual(before, compare_trees(base, active)["sourceFingerprintSha256"])

    def test_invented_raw_git_batch_reader(self):
        oid = "a" * 40
        inventory = {"invented.txt": ("100644", oid)}
        header = (oid + " blob 3\n").encode()
        with patch.object(source_guard, "git", side_effect=[header, header + b"abc\n"]) as mocked:
            self.assertEqual(contents(Path("invented"), (inventory,)), {oid: b"abc"})
        self.assertEqual(mocked.call_count, 2)
        self.assertIn("--batch-check", mocked.call_args_list[0].args)
        self.assertIn("--batch", mocked.call_args_list[1].args)

    def test_invented_git_size_preflight_refuses_oversized_blob(self):
        oid = "a" * 40
        inventory = {"invented.txt": ("100644", oid)}
        header = (oid + " blob " + str(source_guard.MAX_BLOB_BYTES + 1) + "\n").encode()
        with patch.object(source_guard, "git", return_value=header) as mocked:
            with self.assertRaisesRegex(ValueError, "BoundedGitSourceBlob"):
                contents(Path("invented"), (inventory,))
        self.assertEqual(mocked.call_count, 1)

    def test_invented_git_raw_stream_missing_terminator_refused(self):
        oid = "a" * 40
        inventory = {"invented.txt": ("100644", oid)}
        header = (oid + " blob 3\n").encode()
        with patch.object(source_guard, "git", side_effect=[header, header + b"abc"]):
            with self.assertRaisesRegex(ValueError, "CompleteRawGitBlobBytes"):
                contents(Path("invented"), (inventory,))

    def test_invented_git_raw_stream_extra_bytes_refused(self):
        oid = "a" * 40
        inventory = {"invented.txt": ("100644", oid)}
        header = (oid + " blob 3\n").encode()
        with patch.object(source_guard, "git", side_effect=[header, header + b"abc\nextra"]):
            with self.assertRaisesRegex(ValueError, "FullGitBlobStreamConsumed"):
                contents(Path("invented"), (inventory,))


if __name__ == "__main__":
    unittest.main()
