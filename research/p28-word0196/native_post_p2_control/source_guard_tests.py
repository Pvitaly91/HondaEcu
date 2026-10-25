"""Closed current source projection; no build, runtime or historical rewrite."""
from pathlib import Path
import unittest
from . import source_guard as guard


class SourceGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        inventory = guard.tree(cls.root, guard.BASE)
        raw = guard.contents(cls.root, (inventory,))
        cls.base = {name: guard.Blob(mode, raw[oid]) for name, (mode, oid) in inventory.items()}

    def test_accepted_m2bv_git_base_identity(self):
        self.assertEqual(len(self.base), 1011)
        self.assertEqual(guard.fingerprint(guard.rows(self.base)),
            '372ad605911fe7a98fdc9e2c46121d097b411dc1419abd01e6e575e69429cc1a')

    def test_complete_current_source_membership_and_reviewed_deltas(self):
        value = guard.working_source_join(allow_saved_physical=True)
        self.assertTrue(value['passed'])
        self.assertEqual(len(value['sourceBindings']), 1011 + len(guard.NEW_PATHS))
        self.assertEqual(set(value['changedBaselinePaths']), set(guard.REVIEWED_SHARED_DELTAS) | {guard.WORKFLOW})
        self.assertFalse(value['historicalExpectedFingerprintsRewritten'])

    def test_feature_is_default_off_and_all_old_manifest_fields_retained(self):
        actual = (self.root / guard.MANIFEST).read_bytes()
        guard.validate_manifest(self.base[guard.MANIFEST].data, actual)
        for before, after in [(b'default = []', b'default = ["p28-word0196-post-p2-control"]'),
                              (b'["p28-word0196-p2-handoff"]', b'[]'),
                              (b'version = "0.43.0"', b'version = "0.44.0"')]:
            self.assertIn(before, actual)
            with self.assertRaises(ValueError):
                guard.validate_manifest(self.base[guard.MANIFEST].data, actual.replace(before, after, 1))

    def test_closed_new_source_text_and_no_cpu_or_opcode_overlay(self):
        self.assertEqual(len(guard.NEW_PATHS), 27)
        self.assertTrue(all(Path(name).suffix in {'.py', '.json', '.md', '.rs'} for name in guard.NEW_PATHS))
        self.assertNotIn('rust/p28-slice-runner/src/exec.rs', guard.SHARED_PATHS)
        self.assertNotIn('rust/p28-slice-runner/src/decoder.rs', guard.SHARED_PATHS)
        self.assertNotIn('rust/p28-slice-runner/src/cpu.rs', guard.SHARED_PATHS)
        self.assertNotIn('research/p28-word0196/native_p2_handoff/oracle.py', guard.SHARED_PATHS)

    def test_historical_session_1_to_16_constructor_literal_unchanged(self):
        text = self.base['rust/p28-slice-runner/src/audit.rs'].data.decode('utf-8')
        start = text.index('    pub fn new(', text.index('impl Session {'))
        end = text.index('    pub fn seed_byte', start)
        self.assertIn('budget > 16', text[start:end])
        self.assertIn(text[start:end], (self.root / 'rust/p28-slice-runner/src/audit.rs').read_text(encoding='utf-8'))
