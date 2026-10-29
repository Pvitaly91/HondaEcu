"""M2cg source relations and invented policy mutations; no CPU or ROM reads."""
from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from original_rom_boundary.source_guard import Blob, contents, tree
from . import ci_contract as contract
from . import ci_projection as projection
from . import ci_routing as routing


class CiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[3]
        inventory = tree(cls.root, contract.BASE)
        data = contents(cls.root, (inventory,))
        cls.base = {name: Blob(mode, data[oid]) for name, (mode, oid) in inventory.items()}
        cls.old_workflow = cls.base[contract.WORKFLOW].data
        # These invented additions test source-policy relations independently of
        # the real code's separately reviewed approval, which is never derived here.
        cls.current = dict(cls.base)
        for name in projection.NEW_PATHS:
            raw = b'{}\n' if name.endswith('.json') else b'# Invented policy fixture only.\n'
            cls.current[name] = Blob('100644', raw)
        cls.approved = projection.new_source_fingerprint(cls.current)
        cls.current[contract.WORKFLOW] = Blob('100644', contract.make_workflow(
            cls.old_workflow, cls.approved))

    def assert_full(self, current, base=None, approved=None):
        value = projection.classify_changes(self.base if base is None else base,
            current, self.approved if approved is None else approved)
        self.assertIs(value['full_qa'], True)
        self.assertIs(value['research_only'], False)
        self.assertEqual(value['targetCpuExecutions'], 0)
        self.assertEqual(value['historicalJobsPerformedByRouter'], 0)

    def test_exact_fourteen_additions_and_complete_m2ce_raw_base(self):
        value = projection.research_projection(self.base, self.current, self.approved)
        self.assertEqual(len(self.base), 1195)
        self.assertEqual(len(projection.NEW_PATHS), 14)
        self.assertEqual(len(value['sourceBindings']), 1209)
        self.assertEqual(value['unchangedBaseFiles'], 1194)
        self.assertEqual(value['onlyChangedBasePath'], contract.WORKFLOW)
        routed = projection.classify_changes(self.base, self.current, self.approved)
        self.assertIs(routed['research_only'], True)
        self.assertIs(routed['full_qa'], False)
        self.assertEqual(routed['sourceFingerprintSha256'], value['sourceFingerprintSha256'])

    def test_historical_conditions_and_steps_remain_exact_and_truthful(self):
        active = self.current[contract.WORKFLOW].data
        value = contract.workflow_projection(self.old_workflow, active, self.approved)
        self.assertEqual(value['historicalRequiredJobCount'], 17)
        self.assertEqual(value['researchOnlyRequiredActualJobCount'], 3)
        self.assertEqual(value['researchOnlyHistoricalJobsNotRun'], 17)
        self.assertIs(value['researchOnlyLaneIsProductionQaPass'], False)
        self.assertIs(value['researchOnlyArtifactsAreCpuObservations'], False)
        self.assertIs(value['acceptedM2ceApprovalUnchanged'], True)
        old_blocks = (contract.inherited.ROUTER_JOB.replace(
            '__M2CE_APPROVED_NEW_SOURCE_FINGERPRINT__', contract.BASE_M2CE_APPROVAL)
            + contract.inherited.STATIC_JOB).encode()
        new_blocks = (contract.ROUTER_JOB.replace(
            '__M2CG_APPROVED_NEW_SOURCE_FINGERPRINT__', self.approved)
            + contract.STATIC_JOB).encode()
        self.assertEqual(self.old_workflow.replace(old_blocks, b''), active.replace(new_blocks, b''))
        text = active.decode()
        for job, predecessor in contract.HISTORICAL_JOBS:
            expected = contract.historical_condition(predecessor)
            deps = 'ci-routing' if predecessor is None else '[ci-routing, ' + predecessor + ']'
            self.assertIn('\n  ' + job + ':\n    needs: ' + deps + '\n' + expected, text)
            self.assertIn("needs.ci-routing.result != 'success' ||", expected)
            self.assertIn("needs.ci-routing.outputs.full_qa != 'false'", expected)

    def test_runtime_old_research_contract_dependency_and_tests_force_full(self):
        for name in ('rust/p28-slice-runner/src/exec.rs', 'rust/p28-slice-runner/src/bus.rs',
                     'rust/p28-slice-runner/Cargo.toml', 'rust/p28-slice-runner/Cargo.lock',
                     'HondaEcu.Windows.sln', 'AGENTS.md',
                     'research/p28-word0196/native_branch064c/ci_contract.py',
                     'research/p28-word0196/native_branch064c/source_guard.py',
                     'research/p28-word0196/native_data011f_011b_ownership/ci_contract.py',
                     'research/p28-word0196/native_data011f_011b_ownership/source_guard.py',
                     'research/p28-word0196/native_post_return_selector/contract.json'):
            with self.subTest(path=name):
                current = dict(self.current)
                current[name] = Blob(self.base[name].mode, self.base[name].data + b'\n# mutation\n')
                self.assert_full(current)

    def test_unknown_missing_deleted_and_renamed_paths_force_full(self):
        variants = []
        current = dict(self.current); current['docs/unreviewed.txt'] = Blob('100644', b'new'); variants.append(current)
        current = dict(self.current); current.pop('AGENTS.md'); variants.append(current)
        current = dict(self.current); current['docs/renamed.md'] = current.pop('AGENTS.md'); variants.append(current)
        current = dict(self.current); current.pop(projection.PACKAGE + 'contract.json'); variants.append(current)
        current = dict(self.current); current[projection.PACKAGE + 'runtime.py'] = Blob('100644', b'pass'); variants.append(current)
        for index, current in enumerate(variants):
            with self.subTest(mutation=index):
                self.assert_full(current)

    def test_changed_new_runtime_source_never_self_approves_from_new_hash(self):
        current = dict(self.current)
        name = projection.PACKAGE + 'producer_prefix.py'
        current[name] = Blob('100644', current[name].data + b'\nimport subprocess\nsubprocess.run(["invented-cpu"])\n')
        self.assert_full(current)
        observed = projection.new_source_fingerprint(current)
        self.assertNotEqual(observed, self.approved)
        # Supplying a freshly computed hash cannot recertify the unchanged policy.
        self.assert_full(current, approved=observed)

    def test_wrong_complete_base_identity_and_frozen_approval_fail_closed(self):
        base = dict(self.base); base['AGENTS.md'] = Blob('100644', base['AGENTS.md'].data + b'\n')
        self.assert_full(self.current, base=base)
        base = dict(self.base); base.pop('AGENTS.md')
        self.assert_full(self.current, base=base)
        with self.assertRaises(ValueError):
            contract.make_workflow(self.old_workflow + b'\n', self.approved)
        self.assertEqual(contract.inherited.workflow_approved_fingerprint(self.old_workflow),
                         contract.BASE_M2CE_APPROVAL)
        self.assertEqual(sha256(self.old_workflow).hexdigest(), contract.BASE_WORKFLOW_SHA)

    def test_workflow_steps_conditions_artifacts_and_pins_are_not_relaxed(self):
        valid = self.current[contract.WORKFLOW].data
        for old, new in (
            (b'needs: [ci-routing, native-p2-handoff]', b'needs: [ci-routing, build-and-test]'),
            (b'ref: f77d2cc1468fe128ba4ad393c3e0a1a5dab423fc', b'ref: main'),
            (b"needs.ci-routing.result != 'success' || ", b''),
            (b"needs.historical-pinned-qa.result == 'success'", b'true'),
            (b'cargo +1.85.1 test --release', b'echo skipped-test --release'),
            (b'if-no-files-found: error', b'if-no-files-found: ignore'),
            (b'static-canonical.jsonl.gz', b'runtime-canonical.jsonl.gz'),
            (b'--expected-head "', b'--unchecked-head "'),
        ):
            with self.subTest(relation=old):
                altered = valid.replace(old, new, 1)
                self.assertNotEqual(altered, valid)
                with self.assertRaises(ValueError):
                    contract.workflow_projection(self.old_workflow, altered, self.approved)
                current = dict(self.current); current[contract.WORKFLOW] = Blob('100644', altered)
                self.assert_full(current)

    def test_missing_wrong_duplicate_and_pending_approvals_refuse(self):
        for approved in ('', '0' * 64, self.approved.upper(), '__M2CG_APPROVAL_PENDING_REVIEW__'):
            with self.subTest(pin=approved):
                self.assert_full(self.current, approved=approved)
        valid = self.current[contract.WORKFLOW].data
        pin = ('--approved-new-source-fingerprint "' + self.approved + '"').encode()
        for altered in (valid.replace(pin, b'', 1), valid + b'\n# ' + pin + b'\n'):
            with self.assertRaises(ValueError):
                contract.workflow_approved_fingerprint(altered)
            current = dict(self.current); current[contract.WORKFLOW] = Blob('100644', altered)
            self.assert_full(current)

    def test_small_regular_parseable_new_text_required_even_under_matching_pin(self):
        name = projection.PACKAGE + 'ci_routing.py'
        for changed in (Blob('100755', b'pass\n'), Blob('120000', b'target'), Blob('100644', b''),
                        Blob('100644', b'\xff'), Blob('100644', b'\0pass'),
                        Blob('100644', b'def broken(:\n'), Blob('100644', b'#' * (2 * 1024 * 1024 + 1))):
            with self.subTest(mode=changed.mode, size=len(changed.data)):
                current = dict(self.current); current[name] = changed
                approved = projection.new_source_fingerprint(current)
                current[contract.WORKFLOW] = Blob('100644', contract.make_workflow(self.old_workflow, approved))
                self.assert_full(current, approved=approved)
        for raw in (b'{"bad":NaN}', b'[]', b'{'):
            current = dict(self.current); current[projection.PACKAGE + 'contract.json'] = Blob('100644', raw)
            approved = projection.new_source_fingerprint(current)
            current[contract.WORKFLOW] = Blob('100644', contract.make_workflow(self.old_workflow, approved))
            self.assert_full(current, approved=approved)

    def test_router_read_failures_and_invalid_decisions_select_full_without_work(self):
        with patch.object(routing, 'git', side_effect=OSError('InventedReadFailure')) as reader:
            value = routing.classify_git(self.root, '1' * 40, self.approved)
        self.assertIs(value['full_qa'], True)
        self.assertIs(value['research_only'], False)
        self.assertEqual(value['reason'], 'RoutingError_FullHistoricalQaRequired')
        self.assertEqual(reader.call_count, 1)
        self.assert_full(None)
        for decision in ({}, {'full_qa': True, 'research_only': True},
                         {'full_qa': False, 'research_only': False}, {'full_qa': 0, 'research_only': 1}):
            with self.assertRaises(ValueError):
                routing.output_text(decision)
        full = projection.full_qa_decision('InventedControl')
        self.assertEqual(routing.output_text(full), 'full_qa=true\nresearch_only=false\n')
        static = deepcopy(full); static.update(full_qa=False, research_only=True)
        self.assertEqual(routing.output_text(static), 'full_qa=false\nresearch_only=true\n')

    def test_reused_output_writer_only_appends_exact_existing_github_owned_file(self):
        decision = projection.full_qa_decision('InventedOutputControl')
        with tempfile.TemporaryDirectory() as directory:
            owner = Path(directory).resolve() / 'github-output'
            owner.write_bytes(b'')
            other = Path(directory).resolve() / 'other'
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(owner)}):
                with self.assertRaises(ValueError):
                    routing.write_github_output(other, decision)
                self.assertFalse(other.exists())
                routing.write_github_output(owner, decision)
                self.assertEqual(owner.read_bytes(), b'full_qa=true\nresearch_only=false\n')
            missing = Path(directory).resolve() / 'missing'
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(missing)}):
                with self.assertRaises(FileNotFoundError):
                    routing.write_github_output(missing, decision)
            self.assertFalse(missing.exists())

    def test_actual_final_source_requires_independently_reviewed_literal_approval(self):
        from .source_guard import working_source_join
        value = working_source_join(self.root, allow_saved_physical=True)
        self.assertEqual(value['milestone'], 'M2cg')
        self.assertEqual(len(value['sourceBindings']), 1209)
        self.assertEqual(len(value['newPaths']), 14)
        self.assertIs(value['literalNewSourceApprovalVerified'], True)
        self.assertEqual(value['workflowApprovedNewSourceFingerprintSha256'],
                         value['currentNewSourceFingerprintSha256'])
        self.assertIs(value['historicalExpectedFingerprintsRewritten'], False)
        self.assertIs(value['originalBranchExecutionAdmitted'], False)


if __name__ == '__main__':
    unittest.main()
