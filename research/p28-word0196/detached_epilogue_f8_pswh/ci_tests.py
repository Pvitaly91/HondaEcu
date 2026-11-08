"""Regression checks for the finite M2dh overlay and fail-closed routing."""
import unittest

from . import ci


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        head = ci.prior.git(ci.ROOT, 'rev-parse', 'HEAD').decode().strip()
        cls.base, _ = ci.git_maps(head)
        cls.active = {**cls.base, **{name: ci.prior.Blob('100644', (ci.ROOT / name).read_bytes())
                                   for name in ci.NEW_PATHS}}
        cls.pin = ci.new_fingerprint(cls.active)
        cls.workflow = ci.make_workflow(cls.base[ci.WORKFLOW].data, cls.pin)
        cls.active[ci.WORKFLOW] = ci.prior.Blob('100644', cls.workflow)

    def refused(self, active, pin=None):
        result = ci.classify(self.base, active, self.pin if pin is None else pin)
        self.assertIs(result['full_qa'], True)
        self.assertIs(result['research_only'], False)
        self.assertEqual(result['historicalRequiredJobCount'], 17)

    def test_exact_overlay_selects_three_job_static_lane(self):
        projection = ci.projection(self.base, self.active, self.pin)
        self.assertEqual(len(projection['sourceBindings']), ci.BASE_COUNT + len(ci.NEW_PATHS))
        self.assertEqual(projection['unchangedBaseFiles'], ci.BASE_COUNT - 1)
        self.assertIs(ci.classify(self.base, self.active, self.pin)['research_only'], True)
        marker = b'  historical-pinned-qa:'
        old = self.base[ci.WORKFLOW].data
        self.assertEqual(self.workflow[self.workflow.index(marker):], old[old.index(marker):])
        self.assertIn(b'  detached-epilogue-static:', self.workflow)
        self.assertIn(b'validate_detached_epilogue_f8_pswh.py --output .tmp/m2dh-static-evidence', self.workflow)

    def test_frozen_parent_changes_force_historical_qa(self):
        for path in ('analysis.py', 'fragment.py', 'composition.py', 'contract.json', 'reference_oracle.py'):
            name = ci.parent.PACKAGE + path
            old = self.active[name]
            with self.subTest(path=path):
                self.refused({**self.active, name: ci.prior.Blob(old.mode, old.data + b'\n')})

    def test_unreviewed_sources_or_wrong_pin_force_historical_qa(self):
        self.refused(self.active, '0' * 64)
        self.refused({**self.active, ci.PACKAGE + 'unknown.py': ci.prior.Blob('100644', b'pass\n')})
        for name in (ci.PACKAGE + 'epilogue.py', ci.PACKAGE + 'contract.json'):
            with self.subTest(name=name):
                self.refused({**self.active, name: ci.prior.Blob('100644', b'changed\n')})
                self.refused({path: blob for path, blob in self.active.items() if path != name})

    def test_unreviewed_workflow_cannot_change_historical_branch(self):
        modified = self.workflow.replace(b'  historical-pinned-qa:', b'  bypass-historical:', 1)
        self.refused({**self.active, ci.WORKFLOW: ci.prior.Blob('100644', modified)})

    def test_production_source_change_forces_historical_qa(self):
        name = 'rust/p28-slice-runner/src/exec.rs'
        source = self.active[name]
        self.refused({**self.active, name: ci.prior.Blob(source.mode, source.data + b'\n')})

    def test_arbitrary_output_location_is_refused(self):
        for destination in (ci.ROOT, ci.ROOT / 'private/reports/m2dh', ci.ROOT / 'docs'):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                ci.output_directory(destination)

    def test_router_pin_is_unique_and_literal(self):
        self.assertEqual(ci.prior.approval(self.workflow), self.pin)
        for bad in ('', None, 'G' * 64):
            with self.subTest(pin=bad), self.assertRaises(ValueError):
                ci.make_workflow(self.base[ci.WORKFLOW].data, bad)
