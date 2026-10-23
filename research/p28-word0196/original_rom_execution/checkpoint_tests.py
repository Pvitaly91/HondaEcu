"""Invented, small atomic publication and source-bound resume regressions."""
import json
from pathlib import Path
import tempfile
import unittest

if __package__:
    from .checkpoint import CheckpointError, atomic_json, canonical, read_checkpoint
else:  # Preserve direct-script invocation as well as package discovery.
    from checkpoint import CheckpointError, atomic_json, canonical, read_checkpoint


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[3] / ".tmp"
        scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="m2bt-checkpoint-", dir=scratch)
        self.path = Path(self.temporary.name) / "checkpoint.json"
        self.value = {"schemaVersion": 1, "milestone": "M2bt",
                      "sourceFingerprint": "invented-source", "corpusSha256": "invented-corpus",
                      "lastCompletedCaseId": None, "canonicalRecordHashes": []}

    def tearDown(self):
        self.temporary.cleanup()

    def test_complete_atomic_canonical_publication(self):
        binding = atomic_json(self.path, self.value)
        self.assertEqual(self.path.read_bytes(), canonical(self.value))
        self.assertEqual(binding["bytes"], len(self.path.read_bytes()))
        self.assertEqual(read_checkpoint(self.path), self.value)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_immutable_output_cannot_be_replaced(self):
        atomic_json(self.path, self.value)
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            atomic_json(self.path, {**self.value, "lastCompletedCaseId": "invented-001"})
        self.assertEqual(self.path.read_bytes(), before)

    def test_explicit_mutable_checkpoint_replacement(self):
        atomic_json(self.path, self.value)
        changed = {**self.value, "lastCompletedCaseId": "invented-001"}
        atomic_json(self.path, changed, replace=True)
        self.assertEqual(read_checkpoint(self.path), changed)

    def test_changed_source_refused(self):
        atomic_json(self.path, self.value)
        with self.assertRaisesRegex(CheckpointError, "SourceFingerprintChanged"):
            read_checkpoint(self.path, fingerprint="other-source")

    def test_changed_corpus_refused(self):
        atomic_json(self.path, self.value)
        with self.assertRaisesRegex(CheckpointError, "CorpusIdentityChanged"):
            read_checkpoint(self.path, corpus_sha256="other-corpus")

    def test_truncated_checkpoint_refused(self):
        self.path.write_bytes(b'{"schemaVersion":1,')
        with self.assertRaisesRegex(CheckpointError, "IncompleteCheckpoint"):
            read_checkpoint(self.path)

    def test_noncanonical_checkpoint_refused(self):
        self.path.write_text(json.dumps(self.value, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(CheckpointError, "NoncanonicalCheckpoint"):
            read_checkpoint(self.path)

    def test_duplicate_keys_refused(self):
        self.path.write_bytes(b'{"schemaVersion":1,"milestone":"M2bt","milestone":"M2bt"}\n')
        with self.assertRaisesRegex(CheckpointError, "NoncanonicalCheckpoint"):
            read_checkpoint(self.path)

    def test_wrong_milestone_refused(self):
        atomic_json(self.path, {**self.value, "milestone": "Other"})
        with self.assertRaisesRegex(CheckpointError, "WrongCheckpointIdentity"):
            read_checkpoint(self.path)

    def test_nonfinite_values_refused_before_publication(self):
        with self.assertRaises(ValueError):
            atomic_json(self.path, {"bad": float("nan")})
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
