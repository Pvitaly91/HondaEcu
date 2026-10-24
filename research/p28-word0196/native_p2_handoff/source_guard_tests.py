"""Source-policy checks; no CPU/build, arbitrary code evaluation or private ROM."""
from copy import deepcopy
from pathlib import Path
import unittest

from native_p2_handoff import source_guard as guard


class SourceGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        inventory = guard.tree(cls.root, guard.BASE)
        raw = guard.contents(cls.root, (inventory,))
        cls.base = {name: guard.Blob(mode, raw[oid]) for name, (mode, oid) in inventory.items()}

    def test_raw_accepted_base_source_identity(self):
        self.assertEqual(len(self.base), 983)
        self.assertEqual(guard.fingerprint(guard.rows(self.base)), guard.BASE_FINGERPRINT)

    def test_full_current_closed_source_join(self):
        value = guard.working_source_join(allow_saved_physical=True)
        self.assertTrue(value['passed'])
        self.assertEqual(len(value['sourceBindings']), 983 + len(guard.NEW_PATHS))
        self.assertFalse(value['historicalExpectedFingerprintsRewritten'])
        self.assertEqual(set(value['changedBaselinePaths']), {
            guard.WORKFLOW, guard.MANIFEST, 'rust/p28-slice-runner/src/audit.rs',
            'rust/p28-slice-runner/src/audit_bus.rs', 'rust/p28-slice-runner/src/bus.rs',
            'rust/p28-slice-runner/src/audit_entry_continuity.rs'})

    def test_manifest_preserves_default_and_all_old_features(self):
        current = (self.root / guard.MANIFEST).read_bytes()
        guard.validate_manifest(self.base[guard.MANIFEST].data, current)
        for before, after in ((b'default = []', b'default = ["p28-word0196-p2-handoff"]'),
                              (b'["p28-word0196-entry-continuity"]', b'[]'),
                              (b'version = "0.43.0"', b'version = "0.44.0"')):
            self.assertIn(before, current)
            with self.assertRaises(ValueError):
                guard.validate_manifest(self.base[guard.MANIFEST].data, current.replace(before, after, 1))

    def test_new_membership_is_explicit_and_has_no_payload_extensions(self):
        self.assertEqual(len(guard.NEW_PATHS), 28)
        self.assertTrue(all(Path(name).suffix in {'.py', '.json', '.md', '.rs'} for name in guard.NEW_PATHS))
        self.assertNotIn('rust/p28-slice-runner/src/exec.rs', guard.SHARED_PATHS)
        self.assertIn('rust/p28-slice-runner/src/audit_bus.rs', guard.SHARED_PATHS)
        self.assertNotIn('rust/p28-slice-runner/src/cpu.rs', guard.SHARED_PATHS)
        self.assertNotIn('research/p28-word0196/original_rom_execution/oracle.py', guard.SHARED_PATHS)

    def test_legacy_constructor_literal_body_is_preserved(self):
        name = 'rust/p28-slice-runner/src/audit.rs'
        original = self.base[name].data.decode()
        start = original.index('    pub fn new(', original.index('impl Session {'))
        end = original.index('    pub fn seed_byte', start)
        self.assertIn(original[start:end], (self.root / name).read_text(encoding='utf-8'))
        self.assertIn('budget > 16', original[start:end])


if __name__ == '__main__':
    unittest.main()
