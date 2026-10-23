"""Small invented observations and mocked Popen; never load ROM or run Rust."""
from __future__ import annotations

from copy import deepcopy
import gzip
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from original_rom_execution import verify as host
from original_rom_execution import admission
from original_rom_execution.checkpoint import atomic_json, canonical


def source_join(salt="invented"):
    rows = [{"path": "research/invented/oracle.py", "mode": "100644", "bytes": len(salt),
             "sha256": sha256(salt.encode()).hexdigest()}]
    return {"passed": True, "sourceBindings": rows,
            "sourceFingerprintSha256": sha256(canonical(rows)[:-1]).hexdigest()}


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="m2bt-host-invented-")
        self.root = Path(self.temporary.name).resolve()
        self.runner = self.root / "invented-runner.fixture"
        self.runner.write_bytes(b"Not an executable; mocked observations only.\n")
        self.output = self.root / "public-results"
        self.join = source_join()
        self.identity = {"program_base": 0x6000, "program_end_exclusive": 0x6056,
                         "program_sha256": "a" * 64, "source_binding": None,
                         "selected_extent_sha256": {}}
        self.cases = [{"case_id": "invented-" + path, "path": path, "budget": index + 1}
                      for index, path in enumerate("ABCD")]
        self.expected = [{"value": index, "terminal": 0x6056 if index == 0 else 0x6027}
                         for index in range(4)]
        self.calls = []
        self.seen_frozen = []
        self.actual_mutator = lambda value: value
        self.fail_case = None

    def tearDown(self):
        self.temporary.cleanup()

    def compare(self, case, actual, *, program_identity):
        index = "ABCD".index(case["path"])
        if actual["value"] != self.expected[index]["value"]:
            raise ValueError("FirstDifference: PC6002 fieldvalue actual-versus-expected")
        return {"passed": True, "comparison": {"equal": True, "allActualFieldsRetained": True},
                "expected": self.expected[index]}

    def mock_executor(self, runner, program, wire, attempt, active):
        self.calls.append(wire["case_id"])
        self.seen_frozen.append(host.read_json(self.output / "pre-runtime-freeze.json"))
        attempt.mkdir(parents=True, exist_ok=False)
        if wire["case_id"] == self.fail_case:
            raise KeyboardInterrupt("Invented pause, not an execution mismatch")
        ack = {"kind": "program_admitted", "schemaVersion": 1,
               "classification": "ExplicitInventedPublicFixture", "program_sha256": "a" * 64,
               "entry_pc": 0x6000, "program_node_count": 18, "native_generation_ownership": False,
               "physical_sf_known": False, "hardware_validated": False}
        index = "ABCD".index(wire["path"])
        actual = self.actual_mutator({"kind": "invented_observation", "case_id": wire["case_id"],
                                      "value": index, "allExtraInstrumentation": {"retained": True}})
        active(None)
        stdout, stderr = attempt / "stdout.partial", attempt / "stderr.partial"
        stdout.write_bytes(canonical(ack) + canonical(actual))
        stderr.write_bytes(b"")
        transport = {"schemaVersion": 1, "runnerExitCode": 0, "timedOut": False,
                     "stdout": host.file_binding(stdout), "stderr": host.file_binding(stderr),
                     "caseId": wire["case_id"], "oneRunnerProcessOneCase": True}
        atomic_json(attempt / "transport.json", transport)
        return ack, actual, transport

    def engine(self, **updates):
        arguments = {"output": self.output, "runner": self.runner, "source_join": self.join,
                     "source_supplier": lambda: self.join, "cases": deepcopy(self.cases),
                     "wire_cases": deepcopy(self.cases), "expected": deepcopy(self.expected),
                     "program": {"kind": "public_fixture", "schemaVersion": 1},
                     "program_identity": deepcopy(self.identity), "compare": self.compare,
                     "public": True, "executor": self.mock_executor}
        arguments.update(updates)
        return host.VerificationRun(**arguments)

    def test_freeze_precedes_every_mock_observation_and_complete_canonical(self):
        result = self.engine().run()
        self.assertTrue(result["passed"])
        self.assertEqual(result["cases"], 4)
        self.assertEqual(result["newProcessExecutionsThisInvocation"], 4)
        self.assertEqual(set(path.name for path in self.output.iterdir()), host.ARTIFACT_NAMES)
        self.assertEqual(len(self.seen_frozen), 4)
        self.assertTrue(all(value["independentExpected"] == self.expected for value in self.seen_frozen))
        raw = gzip.decompress((self.output / "canonical.jsonl.gz").read_bytes())
        records = [host.strict_json(line) for line in raw.splitlines()]
        self.assertEqual([row["case"]["case_id"] for row in records], self.calls)
        self.assertTrue(all(row["actual"]["allExtraInstrumentation"]["retained"] for row in records))
        self.assertEqual(sha256(raw).hexdigest(), result["canonicalSha256"])
        self.assertEqual(result["canonicalFieldExclusions"], [])
        self.assertEqual(result["originalRomCaseExecutions"], 0)

    def test_completed_resume_revalidates_without_new_execution_or_duplicates(self):
        first = self.engine().run()
        before = (self.output / "canonical.jsonl.gz").read_bytes()
        self.calls.clear()
        resumed = self.engine().run()
        self.assertEqual(self.calls, [])
        self.assertEqual(resumed["resumedCases"], 4)
        self.assertEqual(resumed["newProcessExecutionsThisInvocation"], 0)
        self.assertEqual((self.output / "canonical.jsonl.gz").read_bytes(), before)
        self.assertEqual(resumed["canonicalSha256"], first["canonicalSha256"])

    def test_interrupted_prefix_resumes_only_missing_cases(self):
        self.fail_case = "invented-C"
        with self.assertRaises(KeyboardInterrupt):
            self.engine().run()
        self.assertEqual(self.calls, ["invented-A", "invented-B", "invented-C"])
        self.calls.clear()
        self.fail_case = None
        with patch.object(host, "process_identity", return_value=None):
            result = self.engine().run()
        self.assertEqual(self.calls, ["invented-C", "invented-D"])
        self.assertEqual(result["resumedCases"], 2)

    def test_same_live_controller_blocks_duplicate_execution(self):
        self.fail_case = "invented-A"
        with self.assertRaises(KeyboardInterrupt):
            self.engine().run()
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "SameRuntimeStillActive"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_uncertain_live_process_identity_refused(self):
        saved = {"controller": {"pid": 123, "identityKnown": False}, "child": None}
        with patch.object(host, "process_identity", return_value={"pid": 123, "identityKnown": False}):
            with self.assertRaisesRegex(ValueError, "ActiveRuntimeIdentityUncertain"):
                host.refuse_active(saved)

    def test_known_pid_reuse_does_not_kill_unrelated_process(self):
        saved = {"controller": {"pid": 123, "identityKnown": True, "startIdentity": "old"}}
        with patch.object(host, "process_identity", return_value={"pid": 123, "identityKnown": True, "startIdentity": "new"}):
            host.refuse_active(saved)

    def test_changed_source_fingerprint_refuses_resume(self):
        self.engine().run()
        self.calls.clear()
        changed = source_join("changed")
        with self.assertRaisesRegex(ValueError, "SourceFingerprintChanged"):
            self.engine(source_join=changed, source_supplier=lambda: changed).run()
        self.assertEqual(self.calls, [])

    def test_changed_expected_refuses_resume(self):
        self.engine().run()
        self.calls.clear()
        altered = deepcopy(self.expected)
        altered[0]["value"] = 99
        with self.assertRaisesRegex(ValueError, "ImmutablePreRuntimeFreezeMismatch"):
            self.engine(expected=altered).run()
        self.assertEqual(self.calls, [])

    def test_changed_runner_refuses_resume(self):
        self.engine().run()
        self.calls.clear()
        self.runner.write_bytes(b"Changed, still not executable\n")
        with self.assertRaisesRegex(ValueError, "ImmutablePreRuntimeFreezeMismatch"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_changed_corpus_refuses_resume(self):
        self.engine().run()
        self.calls.clear()
        altered = deepcopy(self.cases)
        altered[0]["budget"] = 99
        with self.assertRaisesRegex(ValueError, "CorpusIdentityChanged"):
            self.engine(cases=altered, wire_cases=altered).run()
        self.assertEqual(self.calls, [])

    def test_first_mismatch_preserves_actual_and_blocks_attestation(self):
        self.actual_mutator = lambda value: {**value, "value": 99}
        with self.assertRaisesRegex(ValueError, "FirstDifference"):
            self.engine().run()
        failure = host.read_json(self.output.parent / (self.output.name + ".state") / "first-mismatch.json")
        self.assertEqual(failure["actual"]["value"], 99)
        self.assertIn("PC6002", failure["detail"])
        self.assertFalse((self.output / "summary.json").exists())
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "PreservedFirstMismatchBlocksPositiveAttestation"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_cached_stdout_mutation_is_not_replaced_by_expected(self):
        engine = self.engine()
        engine.run()
        cached = host.read_json(engine.cache_path(0))
        Path(cached["transport"]["stdout"]["path"]).write_bytes(b"mutated incomplete stdout")
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "ActualTransportEvidenceChanged"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_cache_cannot_manufacture_extra_observation_fields(self):
        engine = self.engine()
        engine.run()
        cached = host.read_json(engine.cache_path(0))
        cached["record"]["actual"]["fabricated"] = True
        cached["recordSha256"] = host.digest(cached["record"])
        engine.cache_path(0).write_bytes(canonical(cached))
        with self.assertRaisesRegex(ValueError, "CanonicalCaseDiffersFromActualRuntimeStdout"):
            self.engine().run()

    def test_truncated_cache_refused_without_rerun(self):
        engine = self.engine()
        engine.run()
        engine.cache_path(0).write_bytes(b'{"record":')
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "IncompleteOrMalformedJson"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_cache_gap_refused_without_duplicate_observations(self):
        engine = self.engine()
        engine.run()
        engine.cache_path(1).unlink()
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "NonprefixCachedObservations"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_completed_counter_without_actual_cache_refused(self):
        engine = self.engine()
        engine.run()
        for index in range(4):
            engine.cache_path(index).unlink()
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "CheckpointCompletedObservationsMissingOrChanged"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_unknown_cached_record_refused(self):
        engine = self.engine()
        engine.run()
        atomic_json(engine.state / "cases" / "extra.json", {"invented": True})
        with self.assertRaisesRegex(ValueError, "UnknownCachedCaseRecord"):
            self.engine().run()

    def test_preexisting_partial_canonical_not_overwritten_or_executed(self):
        self.output.mkdir()
        partial = self.output / "canonical.jsonl.gz"
        partial.write_bytes(b"preserved-invalid-partial")
        with self.assertRaisesRegex(ValueError, "FinalArtifactWithoutCompleteActualObservations"):
            self.engine().run()
        self.assertEqual(partial.read_bytes(), b"preserved-invalid-partial")
        self.assertEqual(self.calls, [])

    def test_unexpected_artifact_directory_file_refused(self):
        self.output.mkdir()
        (self.output / "unexpected.log").write_bytes(b"invented")
        with self.assertRaisesRegex(ValueError, "UnexpectedArtifactDirectoryMember"):
            self.engine().run()
        self.assertEqual(self.calls, [])

    def test_post_runtime_source_change_blocks_summary(self):
        supplied = iter((self.join, source_join("changed")))
        with self.assertRaisesRegex(ValueError, "SourceChangedAcrossRuntime"):
            self.engine(source_supplier=lambda: next(supplied)).run()
        self.assertFalse((self.output / "summary.json").exists())
        self.assertEqual(len(self.calls), 4)

    def test_duplicate_case_ids_refused(self):
        cases = deepcopy(self.cases)
        cases[1]["case_id"] = cases[0]["case_id"]
        with self.assertRaisesRegex(ValueError, "UniqueSafeCaseIdentitiesRequired"):
            self.engine(cases=cases)

    def test_traversal_case_id_refused(self):
        cases = deepcopy(self.cases)
        cases[0]["case_id"] = "../escape"
        with self.assertRaisesRegex(ValueError, "UniqueSafeCaseIdentitiesRequired"):
            self.engine(cases=cases)

    def test_wrong_program_ack_classification_refused(self):
        ack = {"kind": "program_admitted", "schemaVersion": 1, "classification": host.PRIVATE_MODE,
               "program_sha256": "a" * 64, "entry_pc": 0x6000, "program_node_count": 18,
               "native_generation_ownership": False, "physical_sf_known": False, "hardware_validated": False}
        with self.assertRaisesRegex(ValueError, "ProgramSourceIdentityMismatch"):
            host.verify_ack(ack, self.identity, True)

    def test_program_ack_cannot_claim_native_ownership(self):
        ack = {"kind": "program_admitted", "schemaVersion": 1, "classification": "ExplicitInventedPublicFixture",
               "program_sha256": "a" * 64, "entry_pc": 0x6000, "program_node_count": 18,
               "native_generation_ownership": True, "physical_sf_known": False, "hardware_validated": False}
        with self.assertRaisesRegex(ValueError, "ProgramAdmissionPromotedNativeOwnership"):
            host.verify_ack(ack, self.identity, True)

    def test_source_join_fingerprint_must_bind_full_rows(self):
        changed = deepcopy(self.join)
        changed["sourceBindings"][0]["bytes"] += 1
        with self.assertRaisesRegex(ValueError, "SourceJoinFingerprintDoesNotBindRows"):
            host.check_source_join(changed)

    def test_duplicate_json_keys_refused(self):
        with self.assertRaisesRegex(ValueError, "DuplicateJsonKey"):
            host.strict_json(b'{"same":1,"same":1}')

    def test_nonfinite_json_refused(self):
        with self.assertRaisesRegex(ValueError, "NonfiniteJson"):
            host.strict_json(b'{"bad":NaN}')

    def test_atomic_existing_payload_cannot_be_overwritten(self):
        path = self.root / "existing.gz"
        path.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            host.publish_bytes(path, b"replacement")
        self.assertEqual(path.read_bytes(), b"original")

    def test_network_output_refused_without_access(self):
        with self.assertRaisesRegex(ValueError, "LocalOutputRequired"):
            host.local_directory("//invalid-invented-share/output")

    def test_mock_timeout_kills_only_owned_popen(self):
        attempt = self.root / "mock-timeout"
        child = Mock(pid=123, returncode=-1)
        child.communicate.side_effect = [subprocess.TimeoutExpired("invented", 1), (None, None)]
        with patch.object(host.subprocess, "Popen", return_value=child), \
                patch.object(host, "process_identity", return_value={"pid": 123, "identityKnown": False}):
            with self.assertRaisesRegex(ValueError, "OwnedRunnerTimeout"):
                host.execute_case(self.runner, {"kind": "public_fixture"}, {"case_id": "invented"}, attempt, lambda _: None)
        child.kill.assert_called_once_with()
        receipt = host.read_json(attempt / "transport.json")
        self.assertTrue(receipt["timedOut"])
        self.assertTrue((attempt / "stdout.partial").exists())

    def test_checkpoint_callback_failure_reaps_exact_owned_child(self):
        child = Mock(pid=123, returncode=-1)
        child.poll.return_value = None
        with patch.object(host.subprocess, "Popen", return_value=child), \
                patch.object(host, "process_identity", return_value={"pid": 123}), \
                self.assertRaisesRegex(ValueError, "invented callback failure"):
            host.execute_case(self.runner, {"kind": "public_fixture"}, {"case_id": "invented"},
                              self.root / "callback-failure",
                              lambda _: (_ for _ in ()).throw(ValueError("invented callback failure")))
        child.kill.assert_called_once_with()
        child.communicate.assert_called_once_with(timeout=5)

    def test_interruption_reaps_owned_child_without_claiming_observation(self):
        child = Mock(pid=123, returncode=-1)
        child.poll.return_value = None
        child.communicate.side_effect = [KeyboardInterrupt("invented interrupt"), (None, None)]
        attempt = self.root / "interrupted-child"
        with patch.object(host.subprocess, "Popen", return_value=child), \
                patch.object(host, "process_identity", return_value={"pid": 123}), \
                self.assertRaises(KeyboardInterrupt):
            host.execute_case(self.runner, {"kind": "public_fixture"}, {"case_id": "invented"}, attempt, lambda _: None)
        child.kill.assert_called_once_with()
        self.assertFalse((attempt / "transport.json").exists())

    def test_global_checkpoint_retains_exception_and_recovery_evidence(self):
        path = self.root / "global-checkpoint.json"
        ticket = {"path": "invented exception receipt", "bytes": 1, "sha256": "b" * 64}
        original = {"schemaVersion": 1, "milestone": "M2bt", "preservationException": ticket,
                    "completedSteps": ["AuthorizedSingleGeneratedRunnerLossRecorded"],
                    "recoveryResult": "AuthorizedHistoricalGeneratedRunnerLoss_NotRecovered",
                    "rawProtectedDifferences": 1, "authorizedPreservationExceptions": 1,
                    "otherUnauthorizedProtectedDifferences": 0,
                    "ciRunId": 123, "finalPushedSha": "c" * 40}
        atomic_json(path, original)
        self.engine(checkpoint_path=path, preservation_binding=ticket).run()
        actual = host.read_json(path)
        for name in ("preservationException", "recoveryResult", "rawProtectedDifferences",
                     "authorizedPreservationExceptions", "otherUnauthorizedProtectedDifferences", "ciRunId", "finalPushedSha"):
            self.assertEqual(actual[name], original[name])
        self.assertIn("AuthorizedSingleGeneratedRunnerLossRecorded", actual["completedSteps"])
        self.assertEqual(actual["currentPhase"], "ORACLE_COMPARISON")

    def test_global_recorded_active_process_blocks_another_output(self):
        path = self.root / "active-global.json"
        atomic_json(path, {"schemaVersion": 1, "milestone": "M2bt",
                           "activeProcessIdentity": {"controller": {"pid": 123, "identityKnown": False}}})
        with patch.object(host, "process_identity", return_value={"pid": 123, "identityKnown": False}), \
                self.assertRaisesRegex(ValueError, "ActiveRuntimeIdentityUncertain"):
            self.engine(checkpoint_path=path).run()
        self.assertEqual(self.calls, [])

    def test_global_completed_actual_records_cannot_be_replaced_by_different_output(self):
        path = self.root / "completed-global.json"
        atomic_json(path, {"schemaVersion": 1, "milestone": "M2bt",
                           "canonicalRecordHashes": ["a" * 64], "outputDirectory": str(self.root / "another")})
        with self.assertRaisesRegex(ValueError, "ExistingPrivateRuntimeScopeCannotBeReplaced"):
            self.engine(checkpoint_path=path).run()
        self.assertEqual(self.calls, [])

    def test_private_completed_summary_is_not_automatically_rewritten_or_rejected(self):
        invented_rom = self.root / "invented-source.fixture"
        invented_rom.write_bytes(b"invented private source, not OEM")
        self.output.mkdir()
        summary = self.output / "summary.json"
        summary.write_bytes(b'{"existing":true}\n')
        before = summary.read_bytes()
        self.assertEqual(admission.validate_output_directory(self.output, invented_rom), self.output.resolve())
        self.assertEqual(summary.read_bytes(), before)

    def test_private_output_hardlink_to_source_is_refused_even_during_resume(self):
        import os
        invented_rom = self.root / "invented-source.fixture"
        invented_rom.write_bytes(b"invented source, not OEM")
        self.output.mkdir()
        os.link(invented_rom, self.output / "summary.json")
        with self.assertRaisesRegex(ValueError, "OutputWouldOverwriteRom"):
            admission.validate_output_directory(self.output, invented_rom)
        self.assertEqual(invented_rom.read_bytes(), b"invented source, not OEM")

    def invented_preservation_binding_fixture(self):
        # A binding-validator fixture only, never actual permission or evidence.
        scope = self.root / "private/reports/m2bt/authorized-runner-loss"
        scope.mkdir(parents=True)
        prior, current = {"bytes": 16, "sha256": "a" * 64}, {"bytes": 17, "sha256": "b" * 64}
        dependencies = {}
        for name in ("authorizationBinding", "policyReviewBinding", "sourceCapsuleBinding"):
            path = scope / (name + ".fixture")
            path.write_bytes(b"invented binding fixture only")
            dependencies[name] = host.file_binding(path)
        path = scope / "conditions.fixture"
        atomic_json(path, {"allSevenConditionsSatisfiedInDeclaredScope": True,
                           "conditions": [{"number": n, "satisfied": True} for n in range(1, 8)],
                           "historicalExpectedRunnerIdentity": prior, "currentIncidentIdentity": current})
        dependencies["conditionsAuditBinding"] = host.file_binding(path)
        record_path = scope / "AUTHORIZED_EXCEPTION_V1.json"
        record = {"schemaVersion": 1, "milestone": "M2bt", "classification": "AuthorizedHistoricalGeneratedRunnerLoss",
                  "applicable": True, "allSevenConditionsSatisfied": True,
                  "protectedHistoricalIdentityRestored": False, "strictHistoricalPreservationPass": False,
                  "rawProtectedDifferences": 1, "authorizedPreservationExceptions": 1,
                  "otherUnauthorizedProtectedDifferences": 0, "historicalExpectedRebased": False,
                  "exceptionRole": {"path": "rust/p28-slice-runner/target/release/p28-slice-runner.exe",
                                    "expected": prior, "observed": current,
                                    "aliasPaths": ["rust/p28-slice-runner/target/release/deps/p28_slice_runner.exe"]},
                  **dependencies}
        atomic_json(record_path, record)
        ticket = host.file_binding(record_path)
        global_path = self.root / "binding-checkpoint.json"
        atomic_json(global_path, {"schemaVersion": 1, "milestone": "M2bt", "preservationException": ticket})
        return global_path, record_path, record, ticket

    def test_exception_binding_and_all_supporting_receipts_are_checked(self):
        global_path, _, record, ticket = self.invented_preservation_binding_fixture()
        with patch.object(host, "ROOT", self.root):
            self.assertEqual(host.preservation_exception_context(global_path), ticket)
            Path(record["authorizationBinding"]["path"]).write_bytes(b"altered fixture")
            with self.assertRaisesRegex(ValueError, "PreservationExceptionEvidenceChanged"):
                host.preservation_exception_context(global_path)

    def test_missing_applied_exception_is_not_inferred(self):
        path = self.root / "no-exception.json"
        atomic_json(path, {"schemaVersion": 1, "milestone": "M2bt"})
        with self.assertRaisesRegex(ValueError, "AppliedPreservationExceptionBindingRequired"):
            host.preservation_exception_context(path)

    def test_exception_cannot_promote_strict_preservation_or_hide_raw_difference(self):
        global_path, path, record, _ = self.invented_preservation_binding_fixture()
        for changed in ({"strictHistoricalPreservationPass": True}, {"rawProtectedDifferences": 0},
                        {"authorizedPreservationExceptions": True}, {"historicalExpectedRebased": True}):
            with self.subTest(changed=changed):
                path.write_bytes(canonical({**record, **changed}))
                global_path.write_bytes(canonical({"schemaVersion": 1, "milestone": "M2bt",
                                                   "preservationException": host.file_binding(path)}))
                with patch.object(host, "ROOT", self.root), self.assertRaises(ValueError):
                    host.preservation_exception_context(global_path)


if __name__ == "__main__":
    unittest.main()
