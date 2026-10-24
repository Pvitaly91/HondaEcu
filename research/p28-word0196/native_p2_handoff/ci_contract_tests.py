"""Closed CI source/coverage mutations without workflow runs or CPU execution."""
from pathlib import Path
import subprocess
import unittest
from native_p2_handoff import ci_contract as c

class CiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        cls.before = subprocess.check_output(['git', '-C', str(cls.root), 'show', c.BASE + ':.github/workflows/build.yml'])

    def test_expected_nine_jobs_and_immutable_historical_coverage(self):
        current = (self.root / '.github/workflows/build.yml').read_bytes()
        p = c.workflow_projection(self.before, current)
        self.assertEqual(p['requiredActualJobs'], 9)
        self.assertEqual(p['duplicateHeavyHistoricalJobsAdded'], 0)
        self.assertFalse(p['requiredTechnicalStepsSkippedOrDisabled'])
        self.assertEqual(current[current.index(c.DESKTOP.encode()):], self.before[self.before.index(c.DESKTOP.encode()):])

    def test_semantic_coverage_and_pin_mutations_refused(self):
        valid = c.make_workflow(self.before)
        mutations = [
            valid.replace(b'needs: native-entry-continuity', b'needs: build-and-test', 1),
            valid.replace(b'ref: ' + c.BASE.encode(), b'ref: main', 1),
            valid.replace(b'--features p28-word0196-p2-handoff', b'--features p28-word0196-entry-continuity', 1),
            valid.replace(b'--public --output .tmp/m2bv-public-evidence', b'--output .tmp/m2bv-public-evidence', 1),
            valid.replace(b'if-no-files-found: error', b'if-no-files-found: ignore', 1),
            valid + b'\n# unreviewed orchestration change\n']
        for bad in mutations:
            self.assertNotEqual(bad, valid)
            with self.assertRaises(ValueError):
                c.workflow_projection(self.before, bad)

    def test_wrong_historical_workflow_identity_refused(self):
        with self.assertRaises(ValueError):
            c.make_workflow(self.before + b'\n')

if __name__ == '__main__':
    unittest.main()
