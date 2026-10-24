"""Actual frozen public workflow projection and meaningful non-execution mutations."""
import ast
from pathlib import Path
import subprocess
import textwrap
import unittest

from native_entry_continuity import ci_contract as ci


class CiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[3]
        cls.base = subprocess.check_output(['git', 'show', ci.BASE + ':.github/workflows/build.yml'], cwd=root, timeout=30)
        cls.active = ci.make_workflow(cls.base)

    def test_exact_seven_jobs_retain_historical_and_desktop_commands(self):
        result = ci.workflow_projection(self.base, self.active)
        self.assertEqual(result['requiredActualJobs'], 7)
        self.assertTrue(result['desktopJobByteExact'])
        self.assertTrue(result['m2btCommandsAndRuntimePinsUnchanged'])
        self.assertFalse(result['requiredTechnicalStepsSkippedOrDisabled'])

    def test_frozen_python_proof_is_inert_syntax_without_github_template_substitution(self):
        body = ci.FROZEN_PROOF.split('        run: |\n', 1)[1]
        ast.parse(textwrap.dedent(body))
        self.assertNotIn('$' + '{{', body)
        self.assertNotIn('os.environ["GITHUB_SHA"] =', body)
        self.assertNotIn('namespace["main"]', body)

    def test_meaningful_workflow_mutations_are_all_refused(self):
        changes = (
            (b'    needs: build-and-test\n', b'    needs: historical-pinned-qa\n'),
            (b'    needs: historical-pinned-qa\n', b'    if: always()\n'),
            (b'      fail-fast: false\n', b'      fail-fast: true\n'),
            (b'      CARGO_BUILD_JOBS: "1"\n', b'      CARGO_BUILD_JOBS: "2"\n'),
            (b'      - name: M2bu independent oracle admission source and resume regressions\n',
             b'      - name: M2bu independent oracle admission source and resume regressions\n        if: false\n'),
            (b'--target-dir .tmp/m2bu-owned/cargo-target', b'--target-dir rust/p28-slice-runner/target'),
            (b'--features p28-word0196-entry-continuity', b'--features p28-word0196-original-rom'),
            (b'--public --branch-controls', b'--public'),
            (b'--bin m2bu-entry-continuity', b'--bin m2bt-original-rom'),
            (b'if-no-files-found: error', b'if-no-files-found: warn'),
            (b'--no-default-features', b'--no-default-features --lib'),
            (b'          path: |\n', b'          continue-on-error: true\n          path: |\n'),
            (b'          historical = "7eb26571d8ee1f849efe5ffa619b0201008b267c"', b'          historical = os.environ["GITHUB_SHA"]'),
        )
        for before, after in changes:
            with self.subTest(before=before):
                self.assertIn(before, self.active)
                mutated = self.active.replace(before, after, 1)
                self.assertNotEqual(mutated, self.active)
                with self.assertRaises(ValueError):
                    ci.workflow_projection(self.base, mutated)

    def test_unrelated_or_wrong_base_workflow_refused(self):
        with self.assertRaises(ValueError):
            ci.make_workflow(self.base + b'\n')
        with self.assertRaises(ValueError):
            ci.workflow_projection(self.base, self.active.replace(b'  desktop-windows:', b'  disabled-desktop:'))


if __name__ == '__main__':
    unittest.main()
