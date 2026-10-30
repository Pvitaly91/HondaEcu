"""Routing regressions use raw source maps; no historical tests or CPU run."""
import unittest
import re
from unittest.mock import patch

from original_rom_boundary.source_guard import Blob, contents, tree
from ecu_rom_provenance import ci


class SourceRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inventory = tree(ci.ROOT, ci.BASE)
        data = contents(ci.ROOT, (inventory,))
        cls.base = {n: Blob(mode, data[oid]) for n, (mode, oid) in inventory.items()}
        cls.current = dict(cls.base)
        for name in ci.NEW_PATHS:
            cls.current[name] = Blob('100644', (ci.ROOT / name).read_bytes())
        cls.pin = ci.new_fingerprint(cls.current)
        cls.current[ci.WORKFLOW] = Blob('100644', ci.make_workflow(cls.base[ci.WORKFLOW].data, cls.pin))

    def test_exact_approved_refinement_selects_only_static_lane(self):
        result = ci.classify(self.base, self.current, self.pin)
        self.assertIs(result['full_qa'], False)
        self.assertIs(result['research_only'], True)
        self.assertEqual(ci.projection(self.base, self.current, self.pin)['unchangedBaseFiles'], 1262)

    def test_mutation_of_each_new_source_requires_new_approval(self):
        for name in sorted(ci.NEW_PATHS):
            with self.subTest(path=name):
                changed = {**self.current, name: Blob('100644', self.current[name].data + b'\n')}
                self.assertIs(ci.classify(self.base, changed, self.pin)['full_qa'], True)

    def test_runtime_old_or_unknown_source_cannot_bypass_full_qa(self):
        for name in ('rust/p28-slice-runner/src/exec.rs',
                     'research/p28-word0196/native_irq0213_four_invocations/reference_oracle.py',
                     'research/p28-word0196/ecu_rom_provenance/unreviewed.py'):
            with self.subTest(path=name):
                changed = {**self.current, name: Blob('100644', b'changed')}
                self.assertIs(ci.classify(self.base, changed, self.pin)['full_qa'], True)

    def test_missing_source_or_wrong_base_falls_back(self):
        changed = dict(self.current)
        del changed[next(iter(ci.NEW_PATHS))]
        self.assertIs(ci.classify(self.base, changed, self.pin)['full_qa'], True)
        self.assertIs(ci.classify({}, self.current, self.pin)['full_qa'], True)

    def test_historical_steps_are_byte_exact_and_old_pin_is_frozen(self):
        old = self.base[ci.WORKFLOW].data
        active = self.current[ci.WORKFLOW].data
        marker = b'  historical-pinned-qa:'
        self.assertEqual(old[old.index(marker):], active[active.index(marker):])
        self.assertEqual(ci.inherited.approval(old), ci.BASE_APPROVAL)
        self.assertEqual(ci.approval(active), self.pin)

    def test_unreviewed_workflow_timeout_or_conditions_rejected(self):
        for mutation in (b'\n# unreviewed\n', b'\n  extra-job: {}\n'):
            changed = {**self.current, ci.WORKFLOW: Blob('100644', self.current[ci.WORKFLOW].data + mutation)}
            self.assertIs(ci.classify(self.base, changed, self.pin)['full_qa'], True)

    def test_output_cannot_overwrite_source_or_existing_evidence(self):
        for value in (ci.ROOT, ci.ROOT / 'private/reports/m2cm',
                      ci.ROOT / 'research/p28-word0196/ecu_rom_provenance'):
            with self.subTest(path=value), self.assertRaises(ValueError):
                ci.validate_output(value)

    def test_wrong_head_rejected_without_runtime(self):
        with self.assertRaises(ValueError):
            ci.git_maps(expected_head='0' * 40)

    def test_output_parent_traversal_cannot_leave_owned_directory(self):
        with self.assertRaises(ValueError):
            ci.validate_output(ci.ROOT / 'private/reports/m2cm/../../escape')

    def test_report_control_root_is_reserved_in_clean_ci_without_private_data(self):
        with patch.object(ci.Path, 'exists', return_value=False), self.assertRaisesRegex(
                ValueError, 'ReportControlRootReservedEvenWhenAbsent'):
            ci.validate_output(ci.ROOT / 'private/reports/m2cm')

    def test_workflow_canonical_step_invokes_the_actual_allowed_entry(self):
        entry = 'research/p28-word0196/validate_ecu_rom_provenance.py'
        commands = re.findall(rb'python -B (research/\S+\.py) --output ',
                              self.current[ci.WORKFLOW].data)
        self.assertEqual(commands, [entry.encode()])
        self.assertIn(entry, ci.NEW_PATHS)
        self.assertTrue((ci.ROOT / entry).is_file())


if __name__ == '__main__':
    unittest.main()
