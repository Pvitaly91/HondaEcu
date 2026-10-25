"""Closed CI mutations; no workflow execution or private evidence access."""
from pathlib import Path
import subprocess
import unittest
from . import ci_contract as c


class CiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        cls.before = subprocess.check_output(['git', '-C', str(cls.root), 'show', c.BASE + ':.github/workflows/build.yml'])

    def test_exact_eleven_jobs_with_all_old_coverage_pinned(self):
        actual = (self.root / '.github/workflows/build.yml').read_bytes()
        value = c.workflow_projection(self.before, actual)
        self.assertEqual(value['requiredActualJobs'], 11)
        self.assertEqual(value['duplicateHeavyHistoricalJobsAdded'], 0)
        self.assertFalse(value['requiredTechnicalStepsSkippedOrDisabled'])
        self.assertEqual(actual[actual.index(c.DESKTOP.encode()):], self.before[self.before.index(c.DESKTOP.encode()):])

    def test_semantic_steps_source_pin_and_artifact_membership_are_mandatory(self):
        valid = c.make_workflow(self.before)
        edits = [(b'needs: native-p2-handoff', b'needs: build-and-test'),
                 (b'ref: ' + c.BASE.encode(), b'ref: main'),
                 (b'--features p28-word0196-post-p2-control', b'--features p28-word0196-p2-handoff'),
                 (b'--public --output .tmp/m2bw-public-evidence', b'--output .tmp/m2bw-public-evidence'),
                 (b'if-no-files-found: error', b'if-no-files-found: ignore')]
        for before, after in edits:
            changed = valid.replace(before, after, 1)
            self.assertNotEqual(changed, valid)
            with self.assertRaises(ValueError):
                c.workflow_projection(self.before, changed)
        with self.assertRaises(ValueError):
            c.workflow_projection(self.before, valid + b'\n# unreviewed orchestration change\n')

    def test_wrong_accepted_base_workflow_refused(self):
        with self.assertRaises(ValueError):
            c.make_workflow(self.before + b'\n')
