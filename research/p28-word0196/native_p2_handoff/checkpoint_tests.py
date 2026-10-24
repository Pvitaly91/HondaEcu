"""Invented checkpoint fixtures only; no CPU or private evidence is accessed."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from native_p2_handoff import checkpoint as c


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name).resolve() / "state.json"
        self.value = {"milestone": "M2bv", "schemaVersion": 1,
                      "sourceFingerprint": "a" * 64, "corpusSha256": "b" * 64}

    def test_roundtrip_and_source_corpus_binding(self):
        c.atomic_json(self.path, self.value)
        self.assertEqual(c.read_checkpoint(self.path, fingerprint="a" * 64, corpus_sha256="b" * 64), self.value)
        for kwargs in ({"fingerprint": "c" * 64}, {"corpus_sha256": "c" * 64}):
            with self.subTest(kwargs=kwargs), self.assertRaises(c.CheckpointError):
                c.read_checkpoint(self.path, **kwargs)

    def test_milestone_and_schema_are_not_relabelled(self):
        for changes in ({"milestone": "M2bt"}, {"schemaVersion": True}, {"schemaVersion": 2}):
            with self.subTest(changes=changes):
                c.atomic_json(self.path, {**self.value, **changes}, replace=self.path.exists())
                with self.assertRaises(c.CheckpointError):
                    c.read_checkpoint(self.path)

    def test_immutable_receipt_is_not_overwritten(self):
        c.atomic_json(self.path, self.value)
        with self.assertRaises(OSError):
            c.atomic_json(self.path, {**self.value, "changed": True})
        self.assertEqual(c.read_checkpoint(self.path), self.value)

    def test_partial_and_duplicate_and_nonfinite_metadata_refused(self):
        for raw in (b'{"milestone":', b'{"milestone":"M2bv","milestone":"M2bv"}\n',
                    b'{"schemaVersion":NaN}\n', b'{}'):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                with self.assertRaises(c.CheckpointError):
                    c.read_checkpoint(self.path)

    def test_only_explicit_checkpoint_replacement(self):
        c.atomic_json(self.path, self.value)
        changed = {**self.value, "phase": "IMPLEMENTATION"}
        c.atomic_json(self.path, changed, replace=True)
        self.assertEqual(c.read_checkpoint(self.path), changed)

    def test_unc_url_and_traversal_refused_before_any_filesystem_probe(self):
        for path in ('\\\\invented.invalid\\share\\state.json', '//invented.invalid/share/state.json',
                     'https://invented.invalid/state.json', 'file:///invented/state.json',
                     str(self.path.parent / '..' / 'outside.json')):
            with self.subTest(path=path), patch('os.lstat', side_effect=AssertionError('filesystem probe forbidden')), \
                 patch.object(Path, 'lstat', side_effect=AssertionError('filesystem probe forbidden')):
                with self.assertRaises(c.CheckpointError):
                    c.read_checkpoint(path)
                with self.assertRaises(c.CheckpointError):
                    c.atomic_json(path, self.value)


if __name__ == "__main__":
    unittest.main()
